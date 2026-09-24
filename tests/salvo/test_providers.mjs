import test from 'node:test';
import assert from 'node:assert/strict';
import { loadProviders, resolveProvider } from '../../engine/providers/_registry.mjs';
import { dedupe } from '../../engine/lib/filter.mjs';

test('Provider registry auto-discovers all providers', async () => {
  const providers = await loadProviders();
  assert.ok(providers.size >= 8, `Expected at least 8 providers, got ${providers.size}`);

  const requiredIds = ['greenhouse', 'lever', 'ashby', 'remoteok', 'remotive', 'hn-hiring', 'unstop'];
  for (const id of requiredIds) {
    assert.ok(providers.has(id), `Missing provider: ${id}`);
    const p = providers.get(id);
    assert.equal(p.id, id);
    assert.equal(typeof p.fetch, 'function', `Provider ${id} fetch must be a function`);
    assert.equal(typeof p.detect, 'function', `Provider ${id} detect must be a function`);
  }
});

test('resolveProvider detects ATS patterns correctly', async () => {
  const gh = await resolveProvider({ name: 'GitLab', slug: 'gitlab', careers_url: 'https://job-boards.greenhouse.io/gitlab' });
  assert.equal(gh?.provider?.id, 'greenhouse');

  const ash = await resolveProvider({ name: 'Linear', slug: 'linear', careers_url: 'https://jobs.ashbyhq.com/linear' });
  assert.equal(ash?.provider?.id, 'ashby');

  const lev = await resolveProvider({ name: 'Figma', slug: 'figma', careers_url: 'https://jobs.lever.co/figma' });
  assert.equal(lev?.provider?.id, 'lever');

  const rok = await resolveProvider({ name: 'RemoteOK Feed', provider: 'remoteok' });
  assert.equal(rok?.provider?.id, 'remoteok');
});

test('dedupe removes duplicate URLs while retaining richest description', () => {
  const jobs = [
    { url: 'https://job.test/1', title: 'SWE 1', company: 'Acme', description: 'short' },
    { url: 'https://job.test/1', title: 'SWE 1 Full', company: 'Acme', description: 'detailed description with requirements and benefits' },
    { url: 'https://job.test/2', title: 'SWE 2', company: 'Beta', description: 'desc 2' },
  ];

  const deduped = dedupe(jobs);
  assert.equal(deduped.length, 2);
  const j1 = deduped.find((j) => j.url === 'https://job.test/1');
  assert.equal(j1.description, 'detailed description with requirements and benefits');
});
