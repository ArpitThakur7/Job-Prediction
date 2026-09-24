import { existsSync } from 'node:fs';
import { readFile, writeFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import ExcelJS from 'exceljs';
import { Store } from './interface.mjs';
import { ROOT } from '../config.mjs';
import { COLUMNS, USER_OWNED, STATUS_VALUES, STATUS_FILL, TRACKED_SHEETS } from '../sheet-columns.mjs';

const DEFAULT_XLSX_PATH = join(ROOT, 'data/applications.xlsx');
const LOG_HEADERS = ['Date', 'Tracked', 'Discovered', 'Prepared', 'Applied', 'Interview', 'Rejected'];

function sanitizeCell(val) {
  if (typeof val === 'string' && /^[=+\-@]/.test(val)) {
    return `'${val}`;
  }
  return val;
}

function cellValue(cell) {
  const v = cell.value;
  if (v && typeof v === 'object' && 'text' in v) {
    return { value: v.text, link: v.hyperlink || null };
  }
  return { value: v ?? '', link: null };
}

export class XlsxStore extends Store {
  constructor(filePath = DEFAULT_XLSX_PATH) {
    super();
    this.filePath = resolve(filePath);
  }

  async readWorkbook() {
    const workbook = new ExcelJS.Workbook();
    if (existsSync(this.filePath)) {
      await workbook.xlsx.readFile(this.filePath);
    }
    return workbook;
  }

  async writeWorkbook(workbook) {
    try {
      await workbook.xlsx.writeFile(this.filePath);
    } catch (err) {
      if (err.code === 'EBUSY') {
        const customErr = new Error('applications.xlsx is currently open in another program. Please close it and retry.');
        customErr.code = 'EBUSY';
        customErr.status = 409;
        throw customErr;
      }
      throw err;
    }
  }

  readSheetRows(sheet) {
    if (!sheet) return [];
    const headers = [];
    sheet.getRow(1).eachCell((cell, col) => {
      headers[col] = COLUMNS.find((c) => c.header === cell.value)?.key;
    });

    const rows = [];
    sheet.eachRow((row, rowNumber) => {
      if (rowNumber === 1) return;
      const record = {};
      row.eachCell({ includeEmpty: true }, (cell, col) => {
        const key = headers[col];
        if (!key) return;
        const { value, link } = cellValue(cell);
        if (link && (key === 'resumeFile' || key === 'coverFile')) {
          try {
            record[key] = fileURLToPath(link);
            record[`${key}Link`] = link;
            return;
          } catch {
            // keep value
          }
        }
        record[key] = value;
        if (link) record[`${key}Link`] = link;
      });
      if (record.url) rows.push(record);
    });
    return rows;
  }

  async loadApplications(sheetName) {
    const workbook = await this.readWorkbook();
    if (sheetName) {
      return this.readSheetRows(workbook.getWorksheet(sheetName));
    }
    const sheets = {};
    for (const name of TRACKED_SHEETS) {
      sheets[name] = this.readSheetRows(workbook.getWorksheet(name));
    }
    return sheets;
  }

  findRowByUrl(sheet, url) {
    if (!sheet) return null;
    const headers = [];
    sheet.getRow(1).eachCell((cell, col) => {
      headers[col] = COLUMNS.find((c) => c.header === cell.value)?.key;
    });
    const urlCol = headers.indexOf('url');
    if (urlCol === -1) return null;

    let found = null;
    sheet.eachRow((row, rowNumber) => {
      if (rowNumber === 1 || found) return;
      const cell = row.getCell(urlCol);
      const v = cell.value;
      const text = v && typeof v === 'object' && 'text' in v ? v.text : v;
      if (String(text).trim() === String(url).trim()) {
        found = row;
      }
    });
    return found;
  }

  async patchRow(url, field, value, sheetName = 'Applications') {
    if (!url || !field) {
      throw new Error('url and field are required');
    }
    if (!USER_OWNED.has(field)) {
      throw new Error(`field "${field}" is not user-editable (editable: ${[...USER_OWNED].join(', ')})`);
    }
    if (field === 'status' && !STATUS_VALUES.includes(value)) {
      throw new Error(`invalid status "${value}". Expected one of: ${STATUS_VALUES.join(', ')}`);
    }

    const workbook = await this.readWorkbook();
    let sheet = workbook.getWorksheet('Applications');
    let row = this.findRowByUrl(sheet, url);
    if (!row && sheetName !== 'Applications') {
      sheet = workbook.getWorksheet(sheetName);
      row = this.findRowByUrl(sheet, url);
    }
    if (!row || !sheet) {
      throw new Error(`Row with url "${url}" not found in sheet`);
    }

    const col = COLUMNS.findIndex((c) => c.key === field) + 1;
    row.getCell(col).value = sanitizeCell(value);

    if (field === 'status') {
      const fill = STATUS_FILL[String(value).toLowerCase()];
      if (fill) {
        row.getCell(col).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: fill } };
      }
    }

    await this.writeWorkbook(workbook);
    return { ok: true, sheet: sheet.name, url, field, value };
  }

  async getDailyLog() {
    const workbook = await this.readWorkbook();
    const sheet = workbook.getWorksheet('Daily Log');
    if (!sheet) return [];
    const rows = [];
    sheet.eachRow((row, rowNumber) => {
      if (rowNumber === 1) return;
      const d = row.getCell(1).value;
      rows.push({
        date: d instanceof Date ? d.toISOString().slice(0, 10) : String(d ?? ''),
        tracked: Number(row.getCell(2).value) || 0,
        discovered: Number(row.getCell(3).value) || 0,
        prepared: Number(row.getCell(4).value) || 0,
        applied: Number(row.getCell(5).value) || 0,
        interview: Number(row.getCell(6).value) || 0,
        rejected: Number(row.getCell(7).value) || 0,
      });
    });
    return rows;
  }

  writeDailyLog(workbook, records) {
    let sheet = workbook.getWorksheet('Daily Log');
    if (!sheet) {
      sheet = workbook.addWorksheet('Daily Log');
      sheet.addRow(LOG_HEADERS);
      sheet.getRow(1).font = { bold: true };
      LOG_HEADERS.forEach((_, i) => { sheet.getColumn(i + 1).width = i === 0 ? 12 : 11; });
    }

    const count = (s) => records.filter((r) => String(r.status).toLowerCase() === s).length;
    const stamp = new Date().toISOString().slice(0, 10);
    const entry = {
      date: stamp,
      tracked: records.length,
      discovered: count('discovered'),
      prepared: count('prepared'),
      applied: count('applied'),
      interview: count('interview'),
      rejected: count('rejected'),
    };
    const values = [
      entry.date, entry.tracked, entry.discovered,
      entry.prepared, entry.applied, entry.interview, entry.rejected,
    ];

    let target = null;
    sheet.eachRow((row, n) => {
      if (n === 1) return;
      const d = row.getCell(1).value;
      const asString = d instanceof Date ? d.toISOString().slice(0, 10) : String(d);
      if (asString === stamp) target = row;
    });

    if (target) {
      values.forEach((v, i) => { target.getCell(i + 1).value = v; });
    } else {
      sheet.addRow(values);
    }
    return entry;
  }

  writeSheet(workbook, records, sheetName = 'Applications') {
    const old = workbook.getWorksheet(sheetName);
    if (old) workbook.removeWorksheet(old.id);

    const sheet = workbook.addWorksheet(sheetName, {
      views: [{ state: 'frozen', ySplit: 1 }],
    });
    sheet.columns = COLUMNS;

    const header = sheet.getRow(1);
    header.font = { bold: true, color: { argb: 'FFFFFFFF' } };
    header.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF2C3E50' } };
    header.alignment = { vertical: 'middle' };
    header.height = 20;

    const order = { interview: 0, offer: 1, applied: 2, prepared: 3, discovered: 4, rejected: 5, closed: 6 };
    records.sort((a, b) => {
      const s = (order[a.status] ?? 9) - (order[b.status] ?? 9);
      return s !== 0 ? s : (Number(b.score) || 0) - (Number(a.score) || 0);
    });

    for (const record of records) {
      const sanitizedRecord = {};
      for (const [k, v] of Object.entries(record)) {
        sanitizedRecord[k] = sanitizeCell(v);
      }
      const row = sheet.addRow(sanitizedRecord);
      const fill = STATUS_FILL[String(record.status).toLowerCase()];
      if (fill) {
        row.getCell('status').fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: fill } };
      }
      const urlCell = row.getCell('url');
      if (record.url) {
        urlCell.value = { text: record.url, hyperlink: record.url };
        urlCell.font = { color: { argb: 'FF0563C1' }, underline: true };
      }
      for (const [field, label] of [['resumeFile', 'Open'], ['coverFile', 'Open']]) {
        if (!record[field]) continue;
        const cell = row.getCell(field);
        try {
          cell.value = { text: label, hyperlink: pathToFileURL(record[field]).href };
          cell.font = { color: { argb: 'FF0563C1' }, underline: true };
        } catch {
          cell.value = record[field];
        }
      }
      row.getCell('title').alignment = { wrapText: false };
    }

    sheet.autoFilter = { from: 'A1', to: { row: 1, column: COLUMNS.length } };
    return sheet;
  }

  async mergeScannedJobs(jobs, sheetName = 'Applications', options = {}) {
    const workbook = await this.readWorkbook();
    const existingRows = new Map();
    const sheet = workbook.getWorksheet(sheetName);
    if (sheet) {
      for (const row of this.readSheetRows(sheet)) {
        if (row.url) existingRows.set(row.url, row);
      }
    }

    const stamp = new Date().toISOString().slice(0, 10);
    let added = 0;
    let updated = 0;

    const records = new Map(existingRows);
    for (const job of jobs || []) {
      if (!job.url) continue;
      const existing = existingRows.get(job.url);
      if (!existing) {
        added++;
        records.set(job.url, {
          status: 'discovered',
          company: job.company || '',
          title: job.title || '',
          score: job.score ?? 0,
          location: job.location || '',
          source: job.source || '',
          resumeFile: '',
          coverFile: '',
          atsMatch: '',
          firstSeen: stamp,
          lastSeen: stamp,
          appliedOn: '',
          notes: Array.isArray(job.reasons) ? job.reasons.join('; ') : (job.notes || ''),
          url: job.url,
        });
      } else {
        updated++;
        // PRESERVE user-owned columns
        const merged = {
          ...existing,
          company: job.company || existing.company,
          title: job.title || existing.title,
          score: job.score ?? existing.score,
          location: job.location || existing.location,
          source: job.source || existing.source,
          lastSeen: stamp,
        };
        for (const key of USER_OWNED) {
          if (existing[key] !== undefined && existing[key] !== null && existing[key] !== '') {
            merged[key] = existing[key];
          }
        }
        records.set(job.url, merged);
      }
    }

    const list = [...records.values()];
    this.writeSheet(workbook, list, sheetName);
    this.writeDailyLog(workbook, list);
    await this.writeWorkbook(workbook);

    return { added, updated, total: list.length };
  }

  async export(format = 'xlsx', sheetName = 'Applications') {
    const workbook = await this.readWorkbook();
    if (format === 'xlsx') {
      return await workbook.xlsx.writeBuffer();
    }
    if (format === 'csv') {
      const sheet = workbook.getWorksheet(sheetName) || workbook.worksheets[0];
      if (!sheet) return '';
      const lines = [];
      sheet.eachRow((row) => {
        const values = [];
        row.eachCell({ includeEmpty: true }, (cell) => {
          const { value } = cellValue(cell);
          const str = String(value ?? '').replace(/"/g, '""');
          values.push(`"${str}"`);
        });
        lines.push(values.join(','));
      });
      return lines.join('\n');
    }
    throw new Error(`Unsupported export format: ${format}`);
  }
}
