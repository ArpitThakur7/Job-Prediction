/**
 * Abstract Store interface for Salvo application data persistence.
 *
 * Implementations must satisfy:
 * - Applications data retrieval and filtering.
 * - Non-destructive row patching (updating user-owned fields: status, notes, appliedOn).
 * - Safe non-destructive merging on re-scan (never overwrite user edits).
 * - Daily metric tracking for funnel analytics.
 * - Data export (XLSX, CSV).
 */

export class Store {
  /**
   * Load all applications across tracked sheets.
   * @param {string} [sheetName]
   * @returns {Promise<Array<Record<string, any>>>}
   */
  async loadApplications(sheetName) {
    throw new Error('Method loadApplications() must be implemented');
  }

  /**
   * Patch a single user-owned field in a row identified by job URL.
   * @param {string} url - Canonical job URL
   * @param {string} field - Field to update ('status' | 'notes' | 'appliedOn')
   * @param {any} value - New value
   * @param {string} [sheetName] - Target sheet
   * @returns {Promise<{ ok: boolean, sheet: string }>}
   */
  async patchRow(url, field, value, sheetName) {
    throw new Error('Method patchRow() must be implemented');
  }

  /**
   * Merge newly scanned jobs into storage without overwriting user notes or statuses.
   * @param {Array<Record<string, any>>} jobs
   * @param {string} sheetName
   * @param {object} [options]
   * @returns {Promise<{ added: number, updated: number, pruned: number, total: number }>}
   */
  async mergeScannedJobs(jobs, sheetName, options) {
    throw new Error('Method mergeScannedJobs() must be implemented');
  }

  /**
   * Read daily logging historical metrics for funnel analytics.
   * @returns {Promise<Array<{ date: string, tracked: number, discovered: number, prepared: number, applied: number, interview: number, rejected: number }>>}
   */
  async getDailyLog() {
    throw new Error('Method getDailyLog() must be implemented');
  }

  /**
   * Export the tracking records as an XLSX buffer or CSV string.
   * @param {'xlsx' | 'csv'} format
   * @param {string} [sheetName]
   * @returns {Promise<Buffer | string>}
   */
  async export(format, sheetName) {
    throw new Error('Method export() must be implemented');
  }
}
