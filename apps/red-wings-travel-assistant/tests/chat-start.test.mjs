import test from 'node:test';
import assert from 'node:assert/strict';
import { once } from 'node:events';
import { createChatService } from '../src/chat-service.mjs';
import { loadDemoCatalogue } from '../src/demo-catalogue.mjs';
import { processUsage } from '../src/chat-provider.mjs';
import { normalizeJourneyGraph, validateCorridor } from '../src/journey-graph.mjs';
import { createServer } from '../server.mjs';
import { InputError } from '../src/validation.mjs';
import { fixtureConfig, fixtureNow, fixtureTrip, fixtureGraph, respond, call, say } from './journey-fixtures.test.mjs';

const demoCatalogue = await loadDemoCatalogue();
const form = { origin_id: 'c1', destination_id: 'c2', date_from: '2026-12-01', date_to: '2027-01-15',
  flight_option_id: 'known-flight', origin_address: 'Ленина 109' };
const trip = () => ({ ...fixtureTrip(), selected_flight: { number: 'WZ 90001', date: '2026-12-01', leg_id: 'rw' } });
const plan = () => ({ ...validateCorridor(normalizeJourneyGraph(fixtureGraph()), ['bus', 'rw', 'coach'], trip()), id: 'server-initial-plan', summary: 'Поездка с автобусом до рейса.' });
const fakeControls = {
  async normalizeForm(body, { signal }) {
    assert(!signal.aborted);
    if (body.origin_id !== 'c1' || body.destination_id !== 'c2' || (body.flight_option_id && body.flight_option_id !== 'known-flight')) throw new InputError('Unknown ID');
    return trip();
  },
  async suggest(q, { signal }) { assert.equal(q, 'Сам'); assert(!signal.aborted); return { status: 'ok', places: [{ id: 'c1', title: 'Самара' }] }; },
  async flightOptions(q, { signal }) { assert.deepEqual(q, { from: 'c1', date: '2026-12-01' }); assert(!signal.aborted); return { status: 'ok', flights: [{ id: 'known-flight', number: 'WZ 90001' }] }; },
};
const search = async () => ({ status: 'ok', plans: [plan()], sources: [{ name: 'SYNTHETIC', url: 'https://fixture.invalid/timetable' }] });
const make = options => createChatService({ config: fixtureConfig, demoCatalogue, controls: fakeControls, journeySearch: search, ...options });
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };

test('form without wishes searches once without a model, and Pi continues with stored flight, address, cards and sources', async () => {
  let modelCalls = 0, searches = 0;
  const before = processUsage().calls;
  const service = make({ journeySearch: async (value, { signal }) => {
    searches++; assert(!signal.aborted); assert.equal(value.selected_flight.leg_id, 'rw');
    value.origin.city = 'mutated callback copy'; return search();
  }, provider(model, context) {
    modelCalls++; assert.equal(model.id, fixtureConfig.maiModel);
    const state = JSON.stringify(context);
    assert.match(state, /server-initial-plan/); assert.match(state, /Ленина 109/); assert.match(state, /WZ 90001/);
    assert.match(state, /fixture.invalid\/timetable/); assert.match(state, /2027-01-15/);
    assert.equal(context.messages.filter(m => m.role === 'assistant').length, 0);
    return respond(model, [say('В карточке сохранён автобус до выбранного рейса.')]);
  } });
  const result = await service.initialForm(form);
  assert.equal(result.reply_origin, 'planner'); assert.equal(result.status, 'ok');
  assert.equal(result.plans[0].id, 'server-initial-plan'); assert.equal(result.trip.origin.city, 'Ханты-Мансийск');
  assert(!('usage' in result)); assert.equal(processUsage().calls, before); assert.equal(modelCalls, 0); assert.equal(searches, 1);
  const reply = await service.handle({ session_id: result.session_id, message: 'Какой транспорт до рейса?' });
  assert.equal(reply.session_id, result.session_id); assert.equal(reply.reply_origin, 'llm');
  assert.equal(reply.usage.model_calls, 1); assert.equal(modelCalls, 1); assert.equal(searches, 1);
});

test('wishes are processed by one ordinary Pi turn before the first search, and subsequent history is retained', async () => {
  let calls = 0, searches = 0;
  const service = make({ journeySearch: async value => {
    searches++; assert.equal(value.constraints.allow_taxi, false); assert.equal(value.constraints.allow_overnight, false);
    assert.equal(value.origin.address, 'Ленина 109'); assert.equal(value.selected_flight.number, 'WZ 90001'); return search();
  }, provider(model, context) {
    calls++; const state = JSON.stringify(context);
    if (calls === 1) {
      assert.equal(searches, 0); assert.match(state, /Без такси/); assert.match(state, /2027-01-15/);
      return respond(model, [call('update_trip', { constraints: { allow_taxi: false, allow_overnight: false } }), call('find_journey_options')]);
    }
    if (calls === 2) { assert.equal(searches, 1); assert.match(state, /server-initial-plan/); }
    else { assert.match(state, /Без такси/); assert.match(state, /Ночёвка исключена/); }
    return respond(model, [say('Ночёвка исключена. Сохранил вариант с автобусом.')]);
  } });
  const initial = await service.initialForm({ ...form, wishes: 'Без такси\nи без ночёвки.' });
  assert.equal(initial.reply_origin, 'llm'); assert.equal(initial.usage.model_calls, 2); assert.equal(searches, 1);
  assert.equal(initial.trip.constraints.allow_taxi, false); assert.equal(initial.trip.constraints.allow_overnight, false);
  assert(!('wishes' in initial.trip));
  const next = await service.handle({ session_id: initial.session_id, message: 'Напомни ограничения' });
  assert.equal(next.session_id, initial.session_id); assert.equal(calls, 3); assert.equal(searches, 1);
});

test('all four demos seed locally with no model or search and preserve factual context for the real Pi followup', async () => {
  let calls = 0, searches = 0, expected;
  const service = make({ journeySearch: async () => { searches++; throw new Error('unexpected search'); },
    provider(model, context) {
      calls++; const state = JSON.stringify(context);
      assert(state.includes(expected.trip.origin.city)); assert(state.includes(expected.result.plans[0].id));
      assert(state.includes(expected.result.plans[0].legs[0].source_name));
      assert.equal(model.id, fixtureConfig.maiModel);
      assert.equal(context.messages.filter(m => m.role === 'assistant').length, 0);
      return respond(model, [say('Обсудим сохранённый вариант.')]);
    } });
  for (const { id } of demoCatalogue.list().demos) {
    expected = demoCatalogue.get(id); const before = calls, usage = processUsage().calls;
    const seeded = await service.preparedDemo({ id });
    assert.equal(seeded.reply_origin, 'prepared'); assert.equal(seeded.demo.id, id); assert.equal(seeded.demo.checked_at, expected.checked_at);
    assert.equal(seeded.demo.data_mode, expected.data_mode); assert.deepEqual(seeded.trip, expected.trip);
    assert(!('usage' in seeded)); assert(!/не ответ LLM/iu.test(seeded.reply));
    assert.equal(calls, before); assert.equal(processUsage().calls, usage); assert.equal(searches, 0);
    const next = await service.handle({ session_id: seeded.session_id, message: 'Объясни этот вариант' });
    assert.equal(next.session_id, seeded.session_id); assert.equal(next.reply_origin, 'llm');
    assert.equal(next.usage.model_calls, 1); assert.equal(calls, before + 1); assert.equal(searches, 0);
  }
});

test('forged form/demo IDs, arbitrary history, overlong wishes and server configuration are rejected without dispatch', async () => {
  let calls = 0;
  const service = make({ provider() { calls++; throw new Error('must not run'); } });
  for (const input of [
    { ...form, history: [] }, { ...form, session_id: 'forged' }, { ...form, maiKeyFile: '/secret' },
    { ...form, flight_option_id: 'forged' }, { ...form, origin_id: '../../secret' },
    { ...form, wishes: 'x'.repeat(2001) }, { ...form, wishes: {} },
  ]) assert.equal((await service.initialForm(input)).error_code, 'invalid_form');
  for (const input of [{ id: '../feeder-flight' }, { id: 'constructor' }, { id: 'feeder-flight', trip: trip() }, { id: 'feeder-flight', session_id: 'forged' }]) {
    assert.equal((await service.preparedDemo(input)).error_code, 'demo_not_found');
  }
  assert.equal(calls, 0);
});

test('seeded sessions use the existing capacity, busy lock, eviction and TTL for both entry paths', async () => {
  let time = fixtureNow.getTime(); const entered = deferred(), release = deferred();
  const service = make({ config: { ...fixtureConfig, chatMaxSessions: 1, chatSessionTTLms: 100, chatNow: () => new Date(time) },
    async provider(model) { entered.resolve(); await release.promise; return respond(model, [say('Готово.')]); } });
  const seeded = await service.preparedDemo({ id: 'feeder-flight' });
  const pending = service.handle({ session_id: seeded.session_id, message: 'Обсудим' });
  await entered.promise; time += 101;
  assert.equal((await service.handle({ session_id: seeded.session_id, message: 'ещё' })).error_code, 'session_busy');
  assert.equal((await service.preparedDemo({ id: 'arrival-train' })).error_code, 'sessions_full');
  assert.equal((await service.initialForm(form)).error_code, 'sessions_full');
  release.resolve(); await pending;
  const fresh = await service.initialForm(form);
  assert(fresh.session_id); assert.notEqual(fresh.session_id, seeded.session_id);
  assert.equal((await service.handle({ session_id: seeded.session_id, message: 'старый' })).error_code, 'session_expired');
  time += 101;
  assert.equal((await service.handle({ session_id: fresh.session_id, message: 'истёк' })).error_code, 'session_expired');
});

test('pending initial search reserves capacity and abort ignores a late callback result', async () => {
  const entered = deferred(), release = deferred(); const controller = new AbortController();
  const service = make({ config: { ...fixtureConfig, chatMaxSessions: 1 }, journeySearch: async () => { entered.resolve(); return release.promise; },
    provider(model, context) { assert(!JSON.stringify(context).includes('server-initial-plan')); return respond(model, [say('Поиск был отменён.')]); } });
  const pending = service.initialForm(form, { signal: controller.signal });
  await entered.promise;
  assert.equal((await service.preparedDemo({ id: 'arrival-train' })).error_code, 'sessions_full');
  controller.abort(); const aborted = await pending;
  assert.equal(aborted.error_code, 'aborted'); assert.deepEqual(aborted.plans, []);
  release.resolve(await search());
  const next = await service.handle({ session_id: aborted.session_id, message: 'Что сохранилось?' });
  assert.deepEqual(next.plans, []); assert.equal(next.trip.selected_flight.number, 'WZ 90001');
});

test('initial form deadline frees its reservation even if controls ignore cancellation', async () => {
  const service = make({ config: { ...fixtureConfig, chatFormTimeoutMs: 100, chatMaxSessions: 1 },
    controls: { ...fakeControls, normalizeForm: () => new Promise(() => {}) } });
  assert.equal((await service.initialForm(form)).error_code, 'timeout');
  assert((await service.preparedDemo({ id: 'arrival-train' })).session_id);
});

test('wishes retain their session when normalization takes longer than the idle TTL', async () => {
  let time = fixtureNow.getTime();
  const service = make({ config: { ...fixtureConfig, chatSessionTTLms: 100, chatNow: () => new Date(time) },
    controls: { ...fakeControls, async normalizeForm() { time += 101; return trip(); } },
    provider(model) { return respond(model, [say('Учёл пожелание.')]); } });
  const result = await service.initialForm({ ...form, wishes: 'Без такси' });
  assert.equal(result.reply_origin, 'llm'); assert.equal(result.error_code, undefined); assert(result.session_id);
});

async function httpServer(t, chatService, overrides = {}) {
  const server = await createServer({ snapshot: {}, schedules: { mode: 'snapshot' }, agent: { health: () => ({}) }, chatService,
    config: { scheduleMode: 'snapshot', maxConcurrentPlans: 1, maxBodyBytes: 8192, ...overrides } });
  server.listen(0, '127.0.0.1'); await once(server, 'listening');
  t.after(() => new Promise(resolve => { server.closeAllConnections(); server.close(resolve); }));
  return `http://127.0.0.1:${server.address().port}`;
}
const post = (base, path, body, headers = {}) => fetch(base + path, { method: 'POST', headers: { 'Content-Type': 'application/json', ...headers }, body: JSON.stringify(body) });

test('HTTP exposes manifest, controls, start and demo with same-origin and body checks and no server configuration', async t => {
  const service = make({ config: { ...fixtureConfig, maiKeyFile: '/never-read-private-path' }, provider() { throw new Error('unexpected'); } });
  const base = await httpServer(t, service);
  const manifest = await (await fetch(base + '/api/demos')).json(); assert.equal(manifest.demos.length, 4);
  const versionedManifest = await (await fetch(base + '/api-v2/demos')).json(); assert.deepEqual(versionedManifest, manifest);
  const places = await (await fetch(base + '/api/places?q=%D0%A1%D0%B0%D0%BC')).json(); assert.equal(places.places[0].id, 'c1');
  const flights = await (await fetch(base + '/api/flights?from=c1&date=2026-12-01')).json(); assert.equal(flights.flights[0].id, 'known-flight');
  const seeded = await (await post(base, '/api/chat/demo', { id: 'feeder-flight' })).json(); assert.equal(seeded.reply_origin, 'prepared');
  const planned = await (await post(base, '/api/chat/start', form)).json(); assert.equal(planned.reply_origin, 'planner');
  assert(!JSON.stringify({ manifest, places, flights, seeded, planned }).includes('/never-read-private-path'));
  for (const path of ['/api/chat/start', '/api/chat/demo']) {
    assert.equal((await post(base, path, form, { Origin: 'https://other.invalid' })).status, 403);
    assert.equal((await post(base, path, { value: 'x'.repeat(17000) })).status, 413);
    assert.equal((await post(base, path, form, { 'Content-Type': 'text/plain' })).status, 415);
  }
  assert.equal((await fetch(base + '/api/places?q=x&q=y')).status, 400);
  assert.equal((await fetch(base + '/api/flights?from=c1&date=2026-12-01&cachePath=/secret')).status, 400);
  assert.equal((await fetch(base + '/api/places?q=test', { headers: { 'Sec-Fetch-Site': 'cross-site' } })).status, 403);
  assert.equal((await post(base, '/api/chat/demo?id=feeder-flight', { id: 'feeder-flight' })).status, 400);
});

test('more than 30 audience seeds and local suggestions work while the heavy search slot is occupied', async t => {
  const entered = deferred(), release = deferred();
  const service = make({ journeySearch: async () => { entered.resolve(); await release.promise; return search(); } });
  const base = await httpServer(t, service);
  const first = post(base, '/api/chat/start', form); await entered.promise;
  assert.equal((await post(base, '/api/chat/start', form)).status, 429);
  const responses = await Promise.all(Array.from({ length: 40 }, () => post(base, '/api/chat/demo', { id: 'feeder-flight' })));
  assert(responses.every(r => r.status === 200));
  const seeds = await Promise.all(responses.map(r => r.json()));
  assert.equal(new Set(seeds.map(s => s.session_id)).size, 40); assert(seeds.every(s => !s.usage));
  assert.equal((await fetch(base + '/api/places?q=%D0%A1%D0%B0%D0%BC')).status, 200);
  assert.equal((await fetch(base + '/api/flights?from=c1&date=2026-12-01')).status, 429);
  release.resolve(); assert.equal((await first).status, 200);
});

test('wishes never trigger search when the model is disabled or its process budget is exhausted', async () => {
  let searches = 0;
  for (const [extra, code] of [[{ llmEnabled: false }, 'disabled'], [{ maxLLMCalls: 0 }, 'process_call_budget']]) {
    const service = make({ config: { ...fixtureConfig, ...extra }, journeySearch: async () => { searches++; return search(); } });
    const result = await service.initialForm({ ...form, wishes: 'Без такси' });
    assert.equal(result.error_code, code); assert.equal(result.trip.origin.city, 'Ханты-Мансийск'); assert.deepEqual(result.plans, []);
  }
  assert.equal(searches, 0);
});

// Last: the process-wide indeterminate hold intentionally cannot be reset.
test('indeterminate Pi usage after a seed is held without retries; a second seed cannot bypass it', async () => {
  let calls = 0, searches = 0;
  const service = make({ journeySearch: async () => { searches++; return search(); },
    provider(model) { calls++; return respond(model, [say('Ответ без квитанции.')], { usage: null }); } });
  const seeded = await service.preparedDemo({ id: 'feeder-flight' });
  const unknown = await service.handle({ session_id: seeded.session_id, message: 'Обсудим' });
  assert.equal(unknown.error_code, 'usage_unknown'); assert.equal(unknown.usage.status, 'unknown');
  assert.equal(unknown.retry_performed, false); assert.equal(calls, 1);
  const other = await service.preparedDemo({ id: 'arrival-train' }); assert.equal(other.reply_origin, 'prepared');
  assert.equal((await service.handle({ session_id: other.session_id, message: 'Обсудим' })).error_code, 'usage_unknown_hold');
  assert.equal((await service.initialForm({ ...form, wishes: 'Без такси' })).error_code, 'usage_unknown_hold');
  assert.equal(calls, 1); assert.equal(searches, 0);
});
