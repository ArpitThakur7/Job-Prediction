import test from 'node:test';
import assert from 'node:assert/strict';
import { request } from 'node:http';
import { join } from 'node:path';
import { checkRequest, corsHeaders, isInside, allowedOrigins } from '../../engine/lib/request-guard.mjs';
import { server } from '../../engine/server.mjs';

const origins = new Set(['http://localhost:3000']);

test('allows loopback requests without an Origin (curl, server-side proxy)', () => {
  assert.deepEqual(checkRequest({ host: '127.0.0.1:4173' }, origins), { ok: true, origin: null });
  assert.equal(checkRequest({ host: 'localhost:4173' }, origins).ok, true);
  assert.equal(checkRequest({ host: '[::1]:4173' }, origins).ok, true);
});

test('allows the frontend origin', () => {
  const v = checkRequest({ host: '127.0.0.1:4173', origin: 'http://localhost:3000' }, origins);
  assert.deepEqual(v, { ok: true, origin: 'http://localhost:3000' });
});

test('refuses other websites', () => {
  const v = checkRequest({ host: '127.0.0.1:4173', origin: 'https://evil.example' }, origins);
  assert.equal(v.ok, false);
  assert.equal(v.status, 403);
  // "null" origin comes from sandboxed iframes and file:// pages
  assert.equal(checkRequest({ host: '127.0.0.1:4173', origin: 'null' }, origins).ok, false);
});

test('refuses non-loopback Host headers (DNS rebinding)', () => {
  const v = checkRequest({ host: 'evil.example:4173' }, origins);
  assert.equal(v.ok, false);
  assert.equal(v.status, 421);
  assert.equal(checkRequest({ host: '127.0.0.1.evil.example' }, origins).ok, false);
});

test('CORS headers echo only an approved origin, never "*"', () => {
  assert.deepEqual(corsHeaders(null), {});
  const h = corsHeaders('http://localhost:3000');
  assert.equal(h['Access-Control-Allow-Origin'], 'http://localhost:3000');
  assert.equal(h.Vary, 'Origin');
});

test('SALVO_ALLOWED_ORIGINS overrides the default list', () => {
  const set = allowedOrigins({ SALVO_ALLOWED_ORIGINS: 'http://a.test:3000/, http://b.test' });
  assert.deepEqual([...set], ['http://a.test:3000', 'http://b.test']);
});

test('isInside rejects sibling directories that share a prefix', () => {
  const dir = join('data', 'generated');
  assert.equal(isInside(dir, join(dir, 'acme', 'resume.pdf')), true);
  assert.equal(isInside(dir, join('data', 'generated-evil', 'x.pdf')), false);
  assert.equal(isInside(dir, join(dir, '..', '.env')), false);
});

// --- Against the real server ------------------------------------------------

const PORT = 4175;
let srv;
test.before(() => new Promise((r) => (srv = server.listen(PORT, '127.0.0.1', r))));
test.after(() => new Promise((r) => srv.close(r)));

function call(path, { method = 'GET', headers = {}, body } = {}) {
  return new Promise((resolve, reject) => {
    const req = request({ host: '127.0.0.1', port: PORT, path, method, headers }, (res) => {
      let data = '';
      res.on('data', (c) => (data += c));
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: data }));
    });
    req.on('error', reject);
    if (body) req.write(body);
    req.end();
  });
}

test('server refuses a write from another website', async () => {
  const res = await call('/api/resume', {
    method: 'PUT',
    headers: { Origin: 'https://evil.example', 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: 'pwned' }),
  });
  assert.equal(res.status, 403);
  assert.equal(res.headers['access-control-allow-origin'], undefined);
});

test('server refuses a rebinding Host', async () => {
  const res = await call('/api/profile', { headers: { Host: `attacker.example:${PORT}` } });
  assert.equal(res.status, 421);
});

test('server answers the frontend with its exact origin', async () => {
  const res = await call('/api/health', { headers: { Origin: 'http://localhost:3000' } });
  assert.equal(res.status, 200);
  assert.equal(res.headers['access-control-allow-origin'], 'http://localhost:3000');
});

test('server download route refuses paths outside data/generated', async () => {
  const res = await call(`/api/files/download?path=${encodeURIComponent('data/generated-evil/x.pdf')}`);
  assert.equal(res.status, 403);
});

test('server errors do not leak stack traces', async () => {
  const res = await call('/api/scoring', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{not json',
  });
  assert.ok(!res.body.includes('at '), 'response should not contain a stack trace');
});
