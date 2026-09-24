import { createServer } from 'node:http';
import { readFile, writeFile, readdir, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join, resolve, dirname, basename, extname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';
import { ROOT, loadProfile, loadBoards, loadYaml } from './lib/config.mjs';
import { XlsxStore } from './lib/store/xlsx-store.mjs';
import { loadProviders, resolveProvider } from './providers/_registry.mjs';
import { fetchAllJobs } from './lib/discover.mjs';
import { applyFilters } from './lib/filter.mjs';
import { scoreJobCombined } from './lib/scoring.mjs';
import { buildSystemPrompt, finalizeTailoredJob, tailorForJob } from './tailor.mjs';
import { chromium } from 'playwright';
import * as greenhouseFiller from './lib/ats/greenhouse.mjs';
import * as ashbyFiller from './lib/ats/ashby.mjs';
import * as leverFiller from './lib/ats/lever.mjs';
import * as genericFiller from './lib/ats/generic.mjs';
import yaml from 'js-yaml';
import 'dotenv/config';

const PORT = Number(process.env.SALVO_ENGINE_PORT || process.env.DASHBOARD_PORT || 4173);
const STORE = new XlsxStore(join(ROOT, 'data/applications.xlsx'));
const GENERATED_DIR = resolve(join(ROOT, 'data/generated'));

// Active background scan tasks and SSE listeners
const activeScans = new Map();
let scanCounter = 0;

function sendCors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
}

function sendJson(res, status, data) {
  sendCors(res);
  const payload = JSON.stringify(data);
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(payload),
  });
  res.end(payload);
}

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', (chunk) => (body += chunk));
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (err) {
        reject(err);
      }
    });
    req.on('error', reject);
  });
}

function detectAtsHandler(url) {
  try {
    const host = new URL(url).hostname;
    if (/(^|\.)greenhouse\.io$/.test(host)) return { name: 'greenhouse', handler: greenhouseFiller };
    if (/(^|\.)ashbyhq\.com$/.test(host)) return { name: 'ashby', handler: ashbyFiller };
    if (/(^|\.)lever\.co$/.test(host)) return { name: 'lever', handler: leverFiller };
  } catch {}
  return { name: 'generic', handler: genericFiller };
}

// ---------------------------------------------------------------------------
// Route Handlers
// ---------------------------------------------------------------------------

// Track the currently running scan to prevent duplicate concurrent scans
let activeScanId = null;

async function handleHealth(res) {
  let excelOk = false;
  try {
    await STORE.readWorkbook();
    excelOk = true;
  } catch {}

  const providers = await loadProviders();

  sendJson(res, 200, {
    status: 'online',
    engine: 'salvo-core',
    version: '0.1.0',
    port: PORT,
    providersCount: providers.size,
    excelStoreConnected: excelOk,
    playwrightAvailable: true,
    activeScanId,
    timestamp: new Date().toISOString(),
  });
}

async function handleScan(req, res) {
  // Scan deduplication: reject if a scan is already running
  if (activeScanId) {
    const existing = activeScans.get(activeScanId);
    if (existing && existing.status === 'running') {
      return sendJson(res, 409, {
        error: 'A scan is already in progress.',
        activeScanId,
        status: existing.status,
        currentSource: existing.currentSource,
      });
    }
  }

  const body = await readJsonBody(req);
  const mode = body.mode === 'india' ? 'india' : 'global';
  const scanId = `scan_${Date.now()}_${++scanCounter}`;
  activeScanId = scanId;

  const scanState = {
    id: scanId,
    mode,
    status: 'running',
    progress: 0,
    currentSource: '',
    jobsFound: 0,
    clients: new Set(),
    logs: [],
  };
  activeScans.set(scanId, scanState);

  // Run scan in background
  (async () => {
    try {
      const [profile, boards] = await Promise.all([loadProfile(), loadBoards()]);
      const entries = [...(boards.job_boards || []), ...(boards.tracked_companies || [])];

      const broadcast = (data) => {
        const payload = `data: ${JSON.stringify(data)}\n\n`;
        for (const client of scanState.clients) {
          try { client.write(payload); } catch {}
        }
      };

      broadcast({ type: 'start', mode, totalSources: entries.length });

      const allJobs = [];
      let completedSources = 0;

      for (const entry of entries) {
        scanState.currentSource = entry.name;
        broadcast({
          type: 'source',
          source: entry.name,
          completed: completedSources,
          total: entries.length,
          jobsCount: allJobs.length,
        });

        try {
          const resolved = await resolveProvider(entry);
          if (resolved?.provider) {
            const jobs = await resolved.provider.fetch(entry, {});
            if (Array.isArray(jobs)) allJobs.push(...jobs);
          }
        } catch (err) {
          scanState.logs.push(`Failed ${entry.name}: ${err.message}`);
        }
        completedSources++;
      }

      broadcast({ type: 'filtering', rawCount: allJobs.length });
      const { jobs: deduped } = await fetchAllJobs(boards, { log: false });
      const { jobs: filtered, stats } = applyFilters(deduped, profile);

      // Score combined with ML signal
      const scoredJobs = [];
      for (const j of filtered) {
        const scored = await scoreJobCombined(j, profile);
        scoredJobs.push({ ...j, ...scored });
      }
      scoredJobs.sort((a, b) => b.combinedScore - a.combinedScore);

      // Save pipeline file
      const outPath = join(ROOT, mode === 'india' ? 'data/pipeline-india.json' : 'data/pipeline.json');
      await mkdir(dirname(outPath), { recursive: true });
      await writeFile(outPath, JSON.stringify({ scannedAt: new Date().toISOString(), stats, jobs: scoredJobs }, null, 2));

      // Merge into applications.xlsx tracker
      const sheetName = mode === 'india' ? 'India Market' : 'Applications';
      await STORE.mergeScannedJobs(scoredJobs, sheetName);

      scanState.status = 'completed';
      scanState.jobsFound = scoredJobs.length;
      activeScanId = null;
      broadcast({ type: 'done', scanId, stats, totalJobs: scoredJobs.length });

      for (const client of scanState.clients) {
        try { client.end(); } catch {}
      }
    } catch (err) {
      scanState.status = 'failed';
      scanState.error = err.message;
      activeScanId = null;
      for (const client of scanState.clients) {
        try {
          client.write(`data: ${JSON.stringify({ type: 'error', error: err.message })}\n\n`);
          client.end();
        } catch {}
      }
    }
  })();

  sendJson(res, 202, { scanId, mode, status: 'started' });
}

function handleScanStream(req, res, scanId) {
  const scan = activeScans.get(scanId);
  if (!scan) return sendJson(res, 404, { error: 'Scan ID not found' });

  sendCors(res);
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
  });
  res.write(`data: ${JSON.stringify({ type: 'connected', scanId, status: scan.status })}\n\n`);
  scan.clients.add(res);

  req.on('close', () => scan.clients.delete(res));
}

async function handleGetJobs(url, res) {
  const mode = url.searchParams.get('mode') === 'india' ? 'india' : 'global';
  const query = (url.searchParams.get('query') || '').toLowerCase();
  const source = url.searchParams.get('source') || '';
  const minScore = Number(url.searchParams.get('minScore') || 0);
  const page = Math.max(1, Number(url.searchParams.get('page') || 1));
  const limit = Math.max(1, Math.min(100, Number(url.searchParams.get('limit') || 25)));

  const path = join(ROOT, mode === 'india' ? 'data/pipeline-india.json' : 'data/pipeline.json');
  if (!existsSync(path)) {
    return sendJson(res, 200, { jobs: [], total: 0, scannedAt: null, message: 'No scan has been run yet' });
  }

  const pipeline = JSON.parse(await readFile(path, 'utf8'));
  let jobs = pipeline.jobs || [];

  if (query) {
    jobs = jobs.filter((j) =>
      String(j.title).toLowerCase().includes(query) ||
      String(j.company).toLowerCase().includes(query) ||
      String(j.location).toLowerCase().includes(query) ||
      String(j.description).toLowerCase().includes(query)
    );
  }

  if (source) {
    jobs = jobs.filter((j) => String(j.source || j.ats).toLowerCase() === source.toLowerCase());
  }

  if (minScore > 0) {
    jobs = jobs.filter((j) => (j.combinedScore ?? j.score ?? 0) >= minScore);
  }

  const total = jobs.length;
  const start = (page - 1) * limit;
  const paginated = jobs.slice(start, start + limit);

  sendJson(res, 200, {
    jobs: paginated,
    total,
    page,
    limit,
    totalPages: Math.ceil(total / limit),
    scannedAt: pipeline.scannedAt,
    stats: pipeline.stats,
  });
}

async function handleGetJobById(jobIdOrUrl, res) {
  const decoded = decodeURIComponent(jobIdOrUrl);
  const paths = [join(ROOT, 'data/pipeline.json'), join(ROOT, 'data/pipeline-india.json')];

  for (const path of paths) {
    if (!existsSync(path)) continue;
    const pipeline = JSON.parse(await readFile(path, 'utf8'));
    const job = (pipeline.jobs || []).find((j) => j.url === decoded || String(j.id) === decoded);
    if (job) return sendJson(res, 200, { job });
  }

  sendJson(res, 404, { error: 'Job not found' });
}

async function handleTailor(req, res, jobUrl) {
  const body = await readJsonBody(req);
  const mode = body.mode || 'api'; // 'api' | 'manual'
  const decoded = decodeURIComponent(jobUrl);

  const paths = [join(ROOT, 'data/pipeline.json'), join(ROOT, 'data/pipeline-india.json')];
  let job = null;
  for (const p of paths) {
    if (!existsSync(p)) continue;
    const pipeline = JSON.parse(await readFile(p, 'utf8'));
    job = (pipeline.jobs || []).find((j) => j.url === decoded);
    if (job) break;
  }
  if (!job) {
    job = {
      url: decoded,
      company: body.company || 'Unknown',
      title: body.title || 'Software Engineer',
      description: body.description || '',
    };
  }

  if (mode === 'manual' && !body.manualJson) {
    const { systemPrompt, jdText } = await buildSystemPrompt(job);
    return sendJson(res, 200, {
      mode: 'manual',
      status: 'prompt_ready',
      systemPrompt,
      jdText,
      instructions: 'Copy this prompt into any AI chat session, then paste back the structured JSON response.',
    });
  }

  try {
    let meta;
    if (mode === 'manual' && body.manualJson) {
      meta = await finalizeTailoredJob(job, body.manualJson);
    } else {
      meta = await tailorForJob(job);
    }
    sendJson(res, 200, { ok: true, meta });
  } catch (err) {
    sendJson(res, 500, { error: err.message });
  }
}

async function handlePrep(req, res, jobUrl) {
  const body = await readJsonBody(req);
  if (!body.confirm) {
    return sendJson(res, 400, { error: 'Confirmation required. Assisted prep launches a local browser window and never submits automatically.' });
  }

  const decoded = decodeURIComponent(jobUrl);
  const paths = [join(ROOT, 'data/pipeline.json'), join(ROOT, 'data/pipeline-india.json')];
  let job = null;
  for (const p of paths) {
    if (!existsSync(p)) continue;
    const pipeline = JSON.parse(await readFile(p, 'utf8'));
    job = (pipeline.jobs || []).find((j) => j.url === decoded);
    if (job) break;
  }
  if (!job) job = { url: decoded, company: 'Company', title: 'Role' };

  // Find tailored resume
  let meta = null;
  if (existsSync(GENERATED_DIR)) {
    const dirs = await readdir(GENERATED_DIR);
    for (const d of dirs) {
      const metaPath = join(GENERATED_DIR, d, 'meta.json');
      if (!existsSync(metaPath)) continue;
      try {
        const m = JSON.parse(await readFile(metaPath, 'utf8'));
        if (m.url === decoded) { meta = m; break; }
      } catch {}
    }
  }

  const { name: atsName, handler } = detectAtsHandler(job.url);
  const applyUrl = atsName === 'ashby' && handler.applicationUrl ? handler.applicationUrl(job.url) : job.url;

  try {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();
    await page.goto(applyUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(1500);

    const profile = await loadProfile();
    const resumePath = meta?.resumePdfPath;
    const coverPath = meta?.coverPdfPath;

    const { filled, needsReview } = await handler.fill(page, {
      profile,
      resumePath,
      coverLetterPath: coverPath,
    });

    // Mark as prepared in spreadsheet
    try {
      await STORE.patchRow(job.url, 'status', 'prepared');
    } catch {}

    sendJson(res, 200, {
      ok: true,
      ats: atsName,
      applyUrl,
      filled,
      needsReview,
      notice: 'The browser is open for your review. Complete custom questions and click Submit yourself!',
    });
  } catch (err) {
    sendJson(res, 500, { error: `Playwright prep failed: ${err.message}` });
  }
}

async function handleProfile(req, res) {
  const profilePath = join(ROOT, 'config/profile.yaml');
  if (req.method === 'GET') {
    const profile = await loadProfile();
    return sendJson(res, 200, { profile });
  }
  if (req.method === 'PUT') {
    const body = await readJsonBody(req);
    await writeFile(profilePath, yaml.dump(body.profile || body), 'utf8');
    return sendJson(res, 200, { ok: true, message: 'Profile updated' });
  }
}

async function handlePortfolio(req, res) {
  const portfolioPath = join(ROOT, 'config/portfolio.yaml');
  if (req.method === 'GET') {
    const portfolio = await loadYaml('config/portfolio.yaml');
    return sendJson(res, 200, { portfolio });
  }
  if (req.method === 'PUT') {
    const body = await readJsonBody(req);
    await writeFile(portfolioPath, yaml.dump(body.portfolio || body), 'utf8');
    return sendJson(res, 200, { ok: true, message: 'Portfolio facts updated' });
  }
}

async function handleResume(req, res) {
  const resumePath = join(ROOT, 'data/resume/resume.md');
  if (req.method === 'GET') {
    const content = existsSync(resumePath) ? await readFile(resumePath, 'utf8') : '';
    return sendJson(res, 200, { content });
  }
  if (req.method === 'PUT') {
    const body = await readJsonBody(req);
    await mkdir(dirname(resumePath), { recursive: true });
    await writeFile(resumePath, body.content || '', 'utf8');
    return sendJson(res, 200, { ok: true, message: 'Master resume updated' });
  }
}

async function handleApplications(req, res, url) {
  if (req.method === 'GET') {
    const exportFmt = url.searchParams.get('format');
    if (exportFmt) {
      const buffer = await STORE.export(exportFmt);
      sendCors(res);
      res.writeHead(200, {
        'Content-Type': exportFmt === 'xlsx' ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' : 'text/csv',
        'Content-Disposition': `attachment; filename="applications.${exportFmt}"`,
      });
      return res.end(buffer);
    }

    const sheets = await STORE.loadApplications();
    const dailyLog = await STORE.getDailyLog();
    return sendJson(res, 200, { sheets, dailyLog });
  }

  if (req.method === 'PATCH') {
    const body = await readJsonBody(req);
    const { url: jobUrl, field, value, sheet } = body;
    try {
      const result = await STORE.patchRow(jobUrl, field, value, sheet || 'Applications');
      return sendJson(res, 200, result);
    } catch (err) {
      return sendJson(res, err.status || 400, { error: err.message });
    }
  }
}

async function handleDownload(url, res) {
  const filePath = url.searchParams.get('path');
  if (!filePath) return sendJson(res, 400, { error: 'Path parameter required' });

  const resolved = resolve(filePath);
  if (!resolved.startsWith(GENERATED_DIR)) {
    return sendJson(res, 403, { error: 'Refusing to access files outside data/generated' });
  }
  if (!existsSync(resolved)) {
    return sendJson(res, 404, { error: 'File not found' });
  }

  const data = await readFile(resolved);
  sendCors(res);
  res.writeHead(200, {
    'Content-Type': 'application/pdf',
    'Content-Disposition': `attachment; filename="${basename(resolved)}"`,
    'Content-Length': data.length,
  });
  res.end(data);
}

async function handleProviderHealth(res) {
  const providers = await loadProviders();
  const results = [];

  for (const [name, provider] of providers) {
    const start = Date.now();
    let status = 'unknown';
    let latency = null;
    let error = null;

    try {
      // Simple check: providers with detect() or fetch() capability
      if (typeof provider.detect === 'function') {
        status = 'available';
      }
      latency = Date.now() - start;
    } catch (err) {
      status = 'error';
      error = err.message;
      latency = Date.now() - start;
    }

    results.push({ name, status, latency, error });
  }

  sendJson(res, 200, {
    providers: results,
    total: results.length,
    healthy: results.filter((p) => p.status === 'available').length,
    timestamp: new Date().toISOString(),
  });
}

// ---------------------------------------------------------------------------
// Server Entry
// ---------------------------------------------------------------------------

const server = createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);

  if (req.method === 'OPTIONS') {
    sendCors(res);
    res.writeHead(204);
    return res.end();
  }

  try {
    if (url.pathname === '/api/health') return await handleHealth(res);
    if (url.pathname === '/api/scan' && req.method === 'POST') return await handleScan(req, res);
    if (url.pathname.startsWith('/api/scan/') && url.pathname.endsWith('/stream')) {
      const scanId = url.pathname.split('/')[3];
      return handleScanStream(req, res, scanId);
    }
    if (url.pathname === '/api/providers/health' && req.method === 'GET') return await handleProviderHealth(res);
    if (url.pathname === '/api/jobs' && req.method === 'GET') return await handleGetJobs(url, res);
    if (url.pathname.startsWith('/api/jobs/') && !url.pathname.endsWith('/tailor') && !url.pathname.endsWith('/prep')) {
      const id = url.pathname.replace('/api/jobs/', '');
      return await handleGetJobById(id, res);
    }
    if (url.pathname.startsWith('/api/jobs/') && url.pathname.endsWith('/tailor') && req.method === 'POST') {
      const jobUrl = url.pathname.replace('/api/jobs/', '').replace('/tailor', '');
      return await handleTailor(req, res, jobUrl);
    }
    if (url.pathname.startsWith('/api/jobs/') && url.pathname.endsWith('/prep') && req.method === 'POST') {
      const jobUrl = url.pathname.replace('/api/jobs/', '').replace('/prep', '');
      return await handlePrep(req, res, jobUrl);
    }
    if (url.pathname === '/api/profile') return await handleProfile(req, res);
    if (url.pathname === '/api/portfolio') return await handlePortfolio(req, res);
    if (url.pathname === '/api/resume') return await handleResume(req, res);
    if (url.pathname === '/api/applications') return await handleApplications(req, res, url);
    if (url.pathname === '/api/files/download') return await handleDownload(url, res);

    sendJson(res, 404, { error: 'Route not found' });
  } catch (err) {
    sendJson(res, 500, { error: err.message, stack: err.stack });
  }
});

if (process.argv[1] && process.argv[1].endsWith('server.mjs')) {
  server.listen(PORT, '127.0.0.1', () => {
    console.log(`[Salvo Engine] Server listening on http://127.0.0.1:${PORT}`);
  });
}

export { server };
