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
