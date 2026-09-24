import test from 'node:test';
import assert from 'node:assert/strict';
import { server } from '../../engine/server.mjs';

const PORT = 4174; // Use test port
let testServer;

test.before(async () => {
  await new Promise((resolve) => {
    testServer = server.listen(PORT, '127.0.0.1', () => resolve());
  });
});

test.after(async () => {
  await new Promise((resolve) => testServer.close(() => resolve()));
});

test('GET /api/health returns online status and providers count', async () => {
  const res = await fetch(`http://127.0.0.1:${PORT}/api/health`);
  assert.equal(res.status, 200);
  const data = await res.json();
  assert.equal(data.status, 'online');
  assert.equal(data.engine, 'salvo-core');
  assert.ok(data.providersCount >= 8);
});

test('GET /api/profile returns current target and preferences', async () => {
  const res = await fetch(`http://127.0.0.1:${PORT}/api/profile`);
  assert.equal(res.status, 200);
  const data = await res.json();
  assert.ok(data.profile);
  assert.ok(Array.isArray(data.profile.target?.titles));
});

test('GET /api/applications returns spreadsheet sheets and daily log', async () => {
  const res = await fetch(`http://127.0.0.1:${PORT}/api/applications`);
  assert.equal(res.status, 200);
  const data = await res.json();
  assert.ok(data.sheets);
  assert.ok(Array.isArray(data.dailyLog));
});

test('GET /api/providers/health returns health status of registered providers', async () => {
  const res = await fetch(`http://127.0.0.1:${PORT}/api/providers/health`);
  assert.equal(res.status, 200);
  const data = await res.json();
  assert.ok(data.providers);
  assert.ok(Array.isArray(data.providers));
  assert.ok(data.providers.length >= 8);
  assert.equal(typeof data.healthy, 'number');
  assert.equal(typeof data.total, 'number');
});

test('GET and POST /api/scoring reads and updates scoring config', async () => {
  const getRes = await fetch(`http://127.0.0.1:${PORT}/api/scoring`);
  assert.equal(getRes.status, 200);
  const data = await getRes.json();
  assert.ok(data.scoring);
  assert.equal(typeof data.scoring.weights?.relevance, 'number');
  assert.equal(typeof data.scoring.weights?.prediction, 'number');

  const postRes = await fetch(`http://127.0.0.1:${PORT}/api/scoring`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      scoring: {
        weights: { relevance: 0.65, prediction: 0.35 },
        thresholds: { apply_min: 70, high_confidence: 85, max_per_company: 3 },
      },
    }),
  });
  assert.equal(postRes.status, 200);
  const postData = await postRes.json();
  assert.ok(postData.ok);

  // Restore defaults
  await fetch(`http://127.0.0.1:${PORT}/api/scoring`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      scoring: {
        weights: { relevance: 0.60, prediction: 0.40 },
        thresholds: { apply_min: 65, high_confidence: 80, max_per_company: 3 },
      },
    }),
  });
});


