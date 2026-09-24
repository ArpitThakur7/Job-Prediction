import test from 'node:test';
import assert from 'node:assert/strict';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { unlinkSync, existsSync } from 'node:fs';
import { XlsxStore } from '../../engine/lib/store/xlsx-store.mjs';

test('XlsxStore non-destructive merge preserves user-owned columns', async () => {
  const tempPath = join(tmpdir(), `test-apps-${Date.now()}.xlsx`);
  const store = new XlsxStore(tempPath);

  try {
    // 1. Initial scan adds 2 jobs
    const initialJobs = [
      { url: 'https://job.test/1', title: 'Frontend Engineer', company: 'Alpha', score: 85, location: 'Remote', source: 'greenhouse', reasons: ['stack: react'] },
      { url: 'https://job.test/2', title: 'Backend Engineer', company: 'Beta', score: 78, location: 'Global', source: 'ashby', reasons: ['stack: node'] },
    ];

    const res1 = await store.mergeScannedJobs(initialJobs, 'Applications');
    assert.equal(res1.added, 2);

    let apps = await store.loadApplications('Applications');
    assert.equal(apps.length, 2);
    const app1 = apps.find((a) => a.url === 'https://job.test/1');
    assert.equal(app1.status, 'discovered');

    // 2. User edits job 1 in dashboard / Excel: marks status 'applied', adds notes
    await store.patchRow('https://job.test/1', 'status', 'applied', 'Applications');
    await store.patchRow('https://job.test/1', 'notes', 'Referral from Alice', 'Applications');

    // 3. User attempts to patch protected non-user-owned field (must fail)
    await assert.rejects(
      async () => {
        await store.patchRow('https://job.test/1', 'company', 'Malicious Rename', 'Applications');
      },
      /not user-editable/
    );

    // 4. Re-scan occurs: job 1 score changes, job 3 is newly discovered
    const rescannedJobs = [
      { url: 'https://job.test/1', title: 'Frontend Engineer', company: 'Alpha', score: 92, location: 'Remote', source: 'greenhouse', reasons: ['stack: react, typescript'] },
      { url: 'https://job.test/3', title: 'Fullstack Dev', company: 'Gamma', score: 88, location: 'Remote', source: 'lever', reasons: ['title match'] },
    ];

    const res2 = await store.mergeScannedJobs(rescannedJobs, 'Applications');
    assert.equal(res2.added, 1);
    assert.equal(res2.updated, 1);

    apps = await store.loadApplications('Applications');
    assert.equal(apps.length, 3);

    const recheck1 = apps.find((a) => a.url === 'https://job.test/1');
    // Golden Rule Check: Status and Notes MUST be preserved!
    assert.equal(recheck1.status, 'applied', 'Status must remain "applied" and not be overwritten to "discovered"');
    assert.equal(recheck1.notes, 'Referral from Alice', 'User notes must be strictly preserved');
    // Non-user-owned fields (score) updated cleanly
    assert.equal(recheck1.score, 92, 'Score must be refreshed');

    // 5. Test export to CSV
    const csv = await store.export('csv', 'Applications');
    assert.ok(csv.includes('Alpha'));
    assert.ok(csv.includes('Referral from Alice'));

    // 6. Test Daily Log
    const dailyLog = await store.getDailyLog();
    assert.ok(dailyLog.length >= 1);
    assert.equal(dailyLog[0].tracked, 3);
  } finally {
    if (existsSync(tempPath)) {
      try { unlinkSync(tempPath); } catch {}
    }
  }
});
