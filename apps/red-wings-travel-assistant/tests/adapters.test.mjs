import test from 'node:test';
import assert from 'node:assert/strict';
import { loadConfig } from '../src/config.mjs';
import { LiveSchedules, loadSnapshot } from '../src/schedules.mjs';
import { DirectAgentAdapter } from '../src/agent.mjs';
import { fetchJson, Gate, allowedEndpoint } from '../src/network.mjs';

const snapshot = await loadSnapshot();
const origin = snapshot.airports.find(a => a.iata === 'KUF');
const destination = snapshot.airports.find(a => a.iata === 'SVX');
const input = { origin, destination, dates: ['2026-12-08'] };
const config = loadConfig({ SCHEDULE_MODE: 'live', YANDEX_RASP_API_KEY: 'test-only-key' });
const answer = () => ({ search: { date: '2026-12-08', from: { code: origin.code }, to: { code: destination.code } }, pagination: { offset: 0, total: 1, limit: 100 }, segments: [{
  thread: { carrier: { code: 617, codes: { iata: 'WZ' } }, number: 'WZ 1034', transport_type: 'plane' },
  from: { code: origin.code }, to: { code: destination.code }, has_transfers: false,
  departure: '2026-12-08T08:00:00+04:00', arrival: '2026-12-08T10:40:00+05:00',
}] });
const live = (payload, fetchImpl) => new LiveSchedules(config, { now: () => new Date('2026-11-13T00:00:00Z'), fetchImpl: fetchImpl || (async () => new Response(JSON.stringify(payload))) });

test('live query uses fixed host, station IDs, no transfers, header auth and single attempt', async () => {
  let calls = 0;
  const result = await live(null, async (url, options) => {
    calls++;
    assert.equal(url.hostname, 'api.rasp.yandex-net.ru');
    assert.equal(url.searchParams.get('date'), '2026-12-08');
    assert.equal(url.searchParams.get('transfers'), 'false');
    assert.equal(url.searchParams.get('from'), origin.code);
    assert.equal(url.searchParams.has('apikey'), false);
    assert.equal(options.headers.Authorization, 'test-only-key');
    assert.equal(options.redirect, 'error');
    return new Response(JSON.stringify(answer()));
  }).search(input);
  assert.equal(calls, 1);
  assert.equal(result.flights.length, 1);
  assert.equal(result.complete, true);
  assert.equal(result.checked_at, '2026-11-13T00:00:00.000Z');
  assert.equal(result.flights[0].price, null);
});

test('invalid/stale source envelope is connector failure; truncated and unusable dated data are incomplete', async () => {
  for (const mutate of [a => { a.search.date = '2026-12-09'; }, a => { a.search.from.code = 'bad'; }, a => { a.segments = null; }]) {
    const value = answer(); mutate(value);
    await assert.rejects(live(value).search(input), { code: 'invalid_schedule_response' });
  }
  const partial = answer(); partial.pagination.total = 101;
  assert.equal((await live(partial).search(input)).complete, false);
  const noTimezone = answer(); noTimezone.segments[0].departure = '2026-12-08T08:00:00';
  const result = await live(noTimezone).search(input);
  assert.equal(result.complete, false);
  assert.equal(result.flights.length, 0);
  const otherDate = answer(); otherDate.segments[0].departure = '2026-12-09T08:00:00+04:00';
  assert.equal((await live(otherDate).search(input)).flights.length, 0);
  const spoof = answer(); spoof.segments[0].thread.carrier.code = 26;
  assert.equal((await live(spoof).search(input)).flights.length, 0);
});

test('allowed hosts are exact HTTPS hosts; redirects cannot forward auth', async () => {
  for (const url of ['http://api-ai.mai.ru/', 'https://api-ai.mai.ru.evil.test/', 'https://user:pass@api-ai.mai.ru/', 'https://127.0.0.1/', 'https://api-ai.mai.ru:444/']) assert.throws(() => allowedEndpoint(url, ['api-ai.mai.ru']));
  let calls = 0;
  await assert.rejects(fetchJson('https://evil.test/', { hosts: ['api-ai.mai.ru'], fetchImpl: () => { calls++; } }), { code: 'disallowed_endpoint' });
  assert.equal(calls, 0);
});

test('POST timeout, network rejection, 500 and malformed responses never retry or expose secrets', async () => {
  for (const impl of [
    async () => { throw new Error('private address message test-only-secret'); },
    async () => new Response('{"key":"test-only-secret"}', { status: 500 }),
    async () => new Response('not-json test-only-secret'),
    async (_url, { signal }) => new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(new Error('test-only-secret')), { once: true })),
  ]) {
    let calls = 0;
    await assert.rejects(fetchJson('https://api-ai.mai.ru/v1/chat/completions', { hosts: ['api-ai.mai.ru'], method: 'POST', timeout: 20,
      fetchImpl: (...args) => { calls++; return impl(...args); } }), error => error.indeterminate === true && !error.message.includes('test-only-secret'));
    assert.equal(calls, 1);
  }
});

test('response size cap and concurrency gate release after failure', async () => {
  await assert.rejects(fetchJson('https://api-ai.mai.ru/v1/chat/completions', { hosts: ['api-ai.mai.ru'], maxBytes: 10, fetchImpl: async () => new Response('x'.repeat(30)) }), { code: 'response_too_large' });
  const gate = new Gate(1);
  let release;
  const pending = gate.run(() => new Promise(resolve => { release = resolve; }));
  await assert.rejects(gate.run(async () => {}), { code: 'busy' });
  release(); await pending;
  await gate.run(async () => {});
});

const agentInput = { request: { mode: 'trip', preference: 'balanced', message: 'private-user-text', origin_address: 'private-address' }, plan: { variants: [{}], data_mode: 'snapshot' } };
const agentConfig = loadConfig({ ENABLE_LLM: 'true', MAI_API_KEY: 'test-only-key', MAI_MODEL: 'test-only-model', MAI_PROTOCOL: 'openai-chat-completions' });

test('generation disabled by default and exact model/protocol must be configured', async () => {
  let calls = 0;
  const fetchImpl = async () => { calls++; throw new Error(); };
  const disabled = new DirectAgentAdapter(loadConfig({}), { fetchImpl });
  assert.equal((await disabled.explain(agentInput)).status, 'disabled');
  const missing = new DirectAgentAdapter(loadConfig({ ENABLE_LLM: 'true', MAI_API_KEY: 'test-only-key' }), { fetchImpl });
  assert.equal((await missing.explain(agentInput)).status, 'not_configured');
  assert.equal(calls, 0);
});

test('agent never receives addresses/free text, and only provided fact IDs become displayed text', async () => {
  const adapter = new DirectAgentAdapter(agentConfig, { fetchImpl: async (_url, options) => {
    assert(!options.body.includes('private-user-text'));
    assert(!options.body.includes('private-address'));
    const body = JSON.parse(options.body);
    assert.equal(body.model, 'test-only-model');
    assert.equal(body.tools, undefined);
    return new Response(JSON.stringify({ choices: [{ finish_reason: 'stop', message: { content: '{"fact_ids":["source","price"]}' } }] }));
  } });
  const result = await adapter.explain(agentInput);
  assert.equal(result.status, 'ok');
  assert.match(result.text, /сохранённый снимок/);
});

test('invented flight/URL/text from model is rejected; route data survives agent failure', async () => {
  let calls = 0;
  const adapter = new DirectAgentAdapter(agentConfig, { fetchImpl: async () => {
    calls++;
    return new Response(JSON.stringify({ choices: [{ finish_reason: 'stop', message: { content: '{"fact_ids":["buy https://evil.test WZ 9999 for 0 RUB"]}' } }] }));
  } });
  const result = await adapter.explain(agentInput);
  assert.equal(result.status, 'indeterminate');
  assert.equal(result.retry_performed, false);
  assert.equal(calls, 1);
  assert(!result.text.includes('evil.test'));
});
