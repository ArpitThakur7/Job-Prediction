import { Store } from './interface.mjs';

/**
 * DbStore: Optional MongoDB adapter for mirroring tracked applications into MongoDB.
 *
 * Adheres to Salvo's philosophy: applications.xlsx remains the canonical source of truth,
 * while DbStore provides optional query acceleration and integration with host analytics.
 */
export class DbStore extends Store {
  constructor(mongoClient = null, dbName = 'job_ai', collectionName = 'salvo_applications') {
    super();
    this.mongoClient = mongoClient;
    this.dbName = dbName;
    this.collectionName = collectionName;
  }

  getCollection() {
    if (!this.mongoClient) return null;
    return this.mongoClient.db(this.dbName).collection(this.collectionName);
  }

  async loadApplications(sheetName = 'Applications') {
    const col = this.getCollection();
    if (!col) return [];
    return await col.find({ sheet: sheetName }).toArray();
  }

  async patchRow(url, field, value, sheetName = 'Applications') {
    const col = this.getCollection();
    if (!col) return { ok: false, detail: 'MongoDB not connected' };
    const res = await col.updateOne(
      { url, sheet: sheetName },
      { $set: { [field]: value, updatedAt: new Date() } }
    );
    return { ok: res.acknowledged, sheet: sheetName, url, field, value };
  }

  async mergeScannedJobs(jobs, sheetName = 'Applications', options = {}) {
    const col = this.getCollection();
    if (!col) return { added: 0, updated: 0, total: 0 };

    let added = 0;
    let updated = 0;
    const now = new Date();

    for (const job of jobs || []) {
      if (!job.url) continue;
      const res = await col.updateOne(
        { url: job.url, sheet: sheetName },
        {
          $set: {
            company: job.company,
            title: job.title,
            score: job.score,
            location: job.location,
            source: job.source,
            lastSeen: now,
          },
          $setOnInsert: {
            status: 'discovered',
            firstSeen: now,
            notes: (job.reasons || []).join('; '),
            appliedOn: '',
            resumeFile: '',
            coverFile: '',
          },
        },
        { upsert: true }
      );
      if (res.upsertedCount > 0) added++;
      else if (res.modifiedCount > 0) updated++;
    }

    const total = await col.countDocuments({ sheet: sheetName });
    return { added, updated, total };
  }

  async getDailyLog() {
    const col = this.getCollection();
    if (!col) return [];
    // Query aggregated daily metrics if available
    return [];
  }

  async export(format = 'csv', sheetName = 'Applications') {
    throw new Error('Export is handled canonically by XlsxStore');
  }
}
