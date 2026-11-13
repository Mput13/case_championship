import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { once } from 'node:events';
import { mkdtemp, writeFile, mkdir, symlink, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createServer } from '../server.mjs';
import { loadConfig } from '../src/config.mjs';
import { loadSnapshot } from '../src/schedules.mjs';

const snapshot = await loadSnapshot();
const request = { mode: 'trip', origin: 'Самара', destination: 'Екатеринбург', date_from: '2026-12-08', date_to: '2026-12-08', preference: 'balanced' };
async function start(t, overrides = {}) {
  const server = await createServer({ config: loadConfig({ PORT: '0', MAI_API_KEY: 'server-test-secret' }), snapshot, ...overrides });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  t.after(() => new Promise(resolve => { server.closeAllConnections(); server.close(resolve); }));
  return `http://127.0.0.1:${server.address().port}`;
}
const post = (base, body = request, extra = {}) => fetch(`${base}/api/plan`, { method: 'POST', headers: { 'Content-Type': 'application/json', ...extra }, body: JSON.stringify(body) });

test('HTTP health, examples and plan follow contract without credentials or unverified model', async t => {
  const base = await start(t);
  const health = await (await fetch(`${base}/api/health`)).json();
  assert.equal(health.status, 'ok');
  assert.equal(health.schedule_mode, 'snapshot');
  assert.equal(health.model_configured, false);
  assert(!JSON.stringify(health).includes('server-test-secret'));
  const examples = await (await fetch(`${base}/api/examples`)).json();
  assert(examples.examples.length >= 4);
  const response = await post(base);
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('cache-control'), 'no-store');
  const result = await response.json();
  assert.equal(result.status, 'ok');
  assert.equal(result.assistant.status, 'disabled');
  assert(result.variants[0].legs.some(l => l.carrier_code === 617));
});

test('HTTP rejects large/invalid bodies, invalid range, cross-origin requests and unsupported methods', async t => {
  const base = await start(t);
  assert.equal((await post(base, { ...request, message: 'x'.repeat(9000) })).status, 413);
  assert.equal((await post(base, request, { 'Content-Type': 'text/plain' })).status, 415);
  assert.equal((await post(base, request, { Origin: 'https://attacker.example' })).status, 403);
  assert.equal((await post(base, request, { Origin: base })).status, 200);
  assert.equal((await post(base, { ...request, date_to: '2026-12-16' })).status, 400);
  assert.equal((await fetch(`${base}/api/plan`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{' })).status, 400);
  assert.equal((await fetch(`${base}/api/plan?date=2026-12-08`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })).status, 400);
  assert.equal((await fetch(`${base}/api/plan`)).status, 404);
});

test('chunked bodies are capped even without Content-Length and return 413', async t => {
  const base = await start(t);
  const response = await new Promise((resolve, reject) => {
    const req = http.request(`${base}/api/plan`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Transfer-Encoding': 'chunked' } }, res => {
      res.resume(); res.on('end', () => resolve(res.statusCode));
    });
    req.on('error', reject);
    req.write('x'.repeat(9000)); req.end();
  });
  assert.equal(response, 413);
});

test('HTTP concurrency is bounded while an upstream request is pending', async t => {
  let release, entered;
  const started = new Promise(resolve => { entered = resolve; });
  const pending = new Promise(resolve => { release = resolve; });
  const schedules = { mode: 'live', search: async () => { entered(); await pending; return { flights: [], complete: true, sources: [], checked_at: null, coverage_note: 'Test fixture' }; } };
  const config = { ...loadConfig({ PORT: '0' }), maxConcurrentPlans: 1 };
  const base = await start(t, { config, schedules });
  const first = post(base);
  await started;
  assert.equal((await post(base)).status, 429);
  release();
  assert.equal((await first).status, 200);
});

test('static files are confined to public, including symlinks; no source/env exposure', async t => {
  const dir = await mkdtemp(join(tmpdir(), 'rw-server-test-'));
  t.after(() => rm(dir, { recursive: true, force: true }));
  const publicRoot = join(dir, 'public');
  await mkdir(publicRoot);
  await writeFile(join(publicRoot, 'index.html'), '<!doctype html><title>fixture</title>');
  await writeFile(join(dir, 'secret.json'), '{"secret":"do-not-serve"}');
  await symlink(join(dir, 'secret.json'), join(publicRoot, 'outside.json'));
  const base = await start(t, { publicRoot });
  assert.equal((await fetch(base)).status, 200);
  for (const path of ['/outside.json', '/.env', '/src/config.mjs', '/%2e%2e%2fsecret.json', '/..%5csecret.json']) assert.equal((await fetch(base + path)).status, 404, path);
});

test('upstream unknown error bodies and address/message details never escape API', async t => {
  const schedules = { mode: 'live', search: async () => { throw new Error('private address text server-test-secret'); } };
  const base = await start(t, { schedules });
  const response = await post(base);
  assert.equal(response.status, 502);
  const text = await response.text();
  assert(!text.includes('server-test-secret'));
  assert(!text.includes('private address'));
  assert.equal(JSON.parse(text).status, 'error');
});
