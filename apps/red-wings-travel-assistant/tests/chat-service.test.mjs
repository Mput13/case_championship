import test from 'node:test';
import assert from 'node:assert/strict';
import { createChatService } from '../src/chat-service.mjs';
import { normalizeJourneyGraph, validateCorridor } from '../src/journey-graph.mjs';
import { fixtureConfig, fixtureNow, fixtureGraph, fixtureTrip, tripPatch, respond, call, say } from './journey-fixtures.test.mjs';

test('real free model text and server-held tool history: ambiguity, broad window, no taxi, later departure, fixed flight', async () => {
  const replies = [
    [call('update_trip', { ...tripPatch, date_range: { ...tripPatch.date_range, meaning: 'unknown' } })],
    [say('Правильно понимаю: это окно выезда или 1 декабря туда, 15 января обратно?')],
    [call('update_trip', { date_range: { meaning: 'departure_window' } }), call('find_journey_options')],
    [say('Сохранил всё окно. В тестовом источнике есть связка с автобусом; стоимость относится к двум пассажирам.')],
    [call('update_trip', { constraints: { allow_taxi: false } }), call('find_journey_options')],
    [say('Варианты с такси исключены. Остался автобусный подъезд к рейсу.')],
    [say('Насколько позже сможете выехать: назовите дату и время?')],
    [call('update_trip', { selected_flight: { number: 'WZ 90001', date: '2026-12-01' } }), call('find_journey_options')],
    [say('Сохранил ваш WZ 90001 и запрет такси. Базовый путь показан только для сравнения.')],
  ];
  let index = 0;
  const service = createChatService({ config: { ...fixtureConfig, journeyGraph: fixtureGraph() }, provider(model, context, options) {
    assert.equal(options.maxRetries, 0); assert.equal(options.maxTokens, 4096);
    if (index === 2) { assert.match(JSON.stringify(context), /это окно выезда/); assert.match(JSON.stringify(context), /meaning/); }
    return respond(model, replies[index++]);
  } });
  let result = await service.handle({ message: 'Ханты-Мансийск, Ленина 109 → Миасс; 1 декабря — 15 января' });
  const id = result.session_id;
  assert.equal(result.status, 'needs_input'); assert.equal(result.plans.length, 0); assert.match(result.reply, /окно выезда или/);
  result = await service.handle({ session_id: id, message: 'Это окно выезда. Едут двое.' });
  assert.equal(result.trip.date_range.to, '2027-01-15'); assert(result.plans.some(p => p.requires_red_wings));
  assert(result.plans.some(p => !p.requires_red_wings)); assert.match(result.reply, /Сохранил всё окно/);
  result = await service.handle({ session_id: id, message: 'Без такси' });
  assert.equal(result.trip.constraints.allow_taxi, false); assert(result.plans.every(p => !p.legs.some(l => l.mode === 'taxi')));
  result = await service.handle({ session_id: id, message: 'Выеду позже' });
  assert.match(result.reply, /дату и время/); assert.equal(result.trip.constraints.departure_after, null);
  result = await service.handle({ session_id: id, message: 'Уже есть WZ 90001 на 1 декабря' });
  assert.equal(result.trip.selected_flight.number, 'WZ 90001'); assert.equal(result.trip.origin.address, 'Ленина 109');
  assert.equal(result.trip.constraints.allow_taxi, false); assert.equal(index, replies.length);
  assert(!JSON.stringify(result).includes('fact_ids'));
});

test('general live search and place resolution are injected, preserve external cards even without local graph', async () => {
  const plan = validateCorridor(normalizeJourneyGraph(fixtureGraph()), ['bus', 'rw', 'coach'], fixtureTrip());
  plan.id = 'external-server-card'; plan.summary = 'Checked by injected search';
  plan.legs[0].published_calendar = ['RAW_CALENDAR_'.repeat(5000)];
  let count = 0, searchCalls = 0, resolveCalls = 0;
  const service = createChatService({ config: fixtureConfig,
    async resolvePlaces(query, { signal }) { resolveCalls++; assert.equal(query, 'Ханты-Мансийск'); assert(!signal.aborted);
      return { places: [{ id: 'c-test', title: 'Ханты-Мансийск', region: 'Test region' }] }; },
    async journeySearch(trip, { signal }) { searchCalls++; assert.equal(trip.date_range.to, '2027-01-15'); assert(!signal.aborted);
      trip.origin.city = 'mutating a callback copy cannot mutate session';
      return { status: 'ok', plans: [plan], sources: [{ name: 'General search', url: 'https://fixture.invalid/search' }], scope: 'general-live' }; },
    provider(model, context) {
      count++;
      if (count === 1) return respond(model, [call('resolve_places', { query: 'Ханты-Мансийск' }), call('update_trip', tripPatch), call('find_journey_options')]);
      assert.match(JSON.stringify(context), /external-server-card/);
      assert(!JSON.stringify(context).includes('RAW_CALENDAR_'));
      return respond(model, [say('Нашёл путь общим поиском. Источник: https://fixture.invalid/search')]);
    } });
  const result = await service.handle({ message: 'Найди поездку с Red Wings' });
  assert.equal(result.status, 'ok'); assert.equal(searchCalls, 1); assert.equal(resolveCalls, 1);
  assert.deepEqual(result.plans, [plan]); assert.equal(result.trip.origin.city, 'Ханты-Мансийск');
  assert(result.sources.some(s => s.url === 'https://fixture.invalid/search'));
  assert.match(result.reply, /https:\/\/fixture.invalid\/search/);
});

test('no client-controlled history, tools, provider paths or model URLs', async () => {
  let calls = 0;
  const service = createChatService({ config: fixtureConfig, provider(model) { calls++; return respond(model, [say('Ссылка https://attacker.invalid/secret не проверена.')]); } });
  for (const extra of [{ history: [] }, { messages: [] }, { assistant: 'override' }, { tools: [] }, { maiKeyFile: '/tmp/key' }]) {
    const r = await service.handle({ message: 'hi', ...extra }); assert.equal(r.error_code, 'invalid_request');
  }
  assert.equal(calls, 0);
  const result = await service.handle({ message: 'обычный запрос' });
  assert(!result.reply.includes('https://attacker')); assert.equal(calls, 1);
});

test('session lock rejects concurrent input; TTL removes old history; total sessions are bounded', async () => {
  let now = fixtureNow.getTime(), release, calls = 0;
  const waiting = new Promise(resolve => { release = resolve; });
  const service = createChatService({ config: { ...fixtureConfig, chatNow: () => new Date(now), chatSessionTTLms: 100, chatMaxSessions: 1 },
    async provider(model) { calls++; if (calls === 2) await waiting; return respond(model, [say('Уточните дату.')]); } });
  const first = await service.handle({ message: 'hello' });
  const pending = service.handle({ session_id: first.session_id, message: 'second' });
  await new Promise(resolve => setImmediate(resolve));
  const busy = await service.handle({ session_id: first.session_id, message: 'third' });
  assert.equal(busy.error_code, 'session_busy'); assert.equal(calls, 2);
  assert.equal((await service.handle({ message: 'another session' })).error_code, 'sessions_full');
  release(); await pending; now += 101;
  assert.equal((await service.handle({ session_id: first.session_id, message: 'expired' })).error_code, 'session_expired');
  const next = await service.handle({ message: 'new' }); assert.notEqual(next.session_id, first.session_id);
});

test('whole-turn history bound keeps recent dialogue and persistent trip while pruning old text', async () => {
  let calls = 0, latestContext;
  const service = createChatService({ config: { ...fixtureConfig, chatHistoryTurns: 1 }, provider(model, context) {
    latestContext = JSON.stringify(context); calls++;
    return respond(model, calls === 1 ? [call('update_trip', tripPatch)] : [say(`ответ ${calls}`)]);
  } });
  const first = await service.handle({ message: 'UNIQUE_OLD_MESSAGE' });
  await service.handle({ session_id: first.session_id, message: 'second-message' });
  const result = await service.handle({ session_id: first.session_id, message: 'third-message' });
  assert(!latestContext.includes('UNIQUE_OLD_MESSAGE')); assert(latestContext.includes('second-message'));
  assert.equal(result.trip.origin.address, 'Ленина 109'); assert(latestContext.includes('2027-01-15'));
});

test('seven pair-day query cap never shortens the user window and normalizes only adapter observations', async () => {
  let modelCalls = 0, searches = 0;
  const days = Array.from({ length: 7 }, (_, i) => `2026-12-0${i + 1}`);
  const service = createChatService({ config: { ...fixtureConfig, journeyGraph: fixtureGraph() },
    schedules: { mode: 'snapshot', async search({ dates }) { searches++; assert.deepEqual(dates, days);
      return { flights: [], complete: true, sources: [], missing_dates: [], coverage_note: 'Test-only seven days' }; } },
    provider(model, context) {
      modelCalls++;
      if (modelCalls === 1) return respond(model, [call('update_trip', tripPatch),
        call('query_flights', { from_node: 'hma', to_node: 'svx', dates: days }, 'q1'),
        call('query_flights', { from_node: 'hma', to_node: 'svx', dates: ['2026-12-08'] }, 'q2')]);
      assert.match(JSON.stringify(context), /schedule_query_budget/);
      return respond(model, [say('Проверены только семь дат; остальные даты окна ещё не исследованы.')]);
    } });
  const result = await service.handle({ message: 'Поищи во всём окне' });
  assert.equal(searches, 1); assert.equal(result.usage.schedule_pair_days, 7); assert.equal(result.trip.date_range.to, '2027-01-15');
});

test('callback failure never falls back to static cards or leaks provider exception text', async () => {
  let calls = 0;
  const service = createChatService({ config: { ...fixtureConfig, journeyGraph: fixtureGraph() },
    journeySearch: async () => { throw new Error('private-credential-in-adapter-error'); },
    provider(model) { return respond(model, ++calls === 1 ? [call('update_trip', tripPatch), call('find_journey_options')] : [say('Источник не ответил; данных для сравнения нет.')]); } });
  const result = await service.handle({ message: 'Найди путь' });
  assert.equal(result.status, 'partial'); assert.deepEqual(result.plans, []);
  assert(!JSON.stringify(result).includes('private-credential'));
});

test('tool allowlist rejects unknown functions and unknown patch keys before any execution', async () => {
  for (const tool of [call('shell', { command: 'whoami' }), call('update_trip', { origin: { city: 'Казань', url: 'https://evil.invalid' } })]) {
    let calls = 0;
    const service = createChatService({ config: fixtureConfig, provider(model) { calls++; return respond(model, [tool]); } });
    const result = await service.handle({ message: 'do it' });
    assert.equal(calls, 1); assert.equal(result.error_code, 'tool_rejected'); assert.equal(result.trip.origin, null); assert.deepEqual(result.tool_events, []);
  }
});

test('three spec examples and scenario callback preserve 2028 mode without active-network claims', async () => {
  let calls = 0;
  const scenarioPatch = { ...tripPatch, network_mode: 'scenario_2027_2028', ground_preference: 'smart_transfer',
    date_range: { from: '2028-07-01', to: '2028-07-31', meaning: 'departure_window' } };
  const plan = validateCorridor(normalizeJourneyGraph(fixtureGraph()), ['bus', 'rw', 'coach'], fixtureTrip());
  // Explicitly convert the synthetic fixture into a scenario input, not a real flight.
  plan.network_mode = 'scenario_2027_2028'; plan.legs.forEach(l => {
    l.network_mode = 'scenario_2027_2028';
    l.departure = l.departure.replace('2026-12-01', '2028-07-01');
    l.arrival = l.arrival.replace('2026-12-01', '2028-07-01');
  });
  const service = createChatService({ config: fixtureConfig,
    journeySearch: async trip => { assert.equal(trip.network_mode, 'scenario_2027_2028'); return { status: 'ok', plans: [plan] }; },
    provider(model) { return respond(model, ++calls === 1 ? [call('update_trip', scenarioPatch), call('find_journey_options')] : [say('Это сценарий 2028 года. Умный трансфер — концепт без бронирования.')]); } });
  const examples = service.examples().examples;
  assert(examples.some(e => /Выхино/.test(e.message))); assert(examples.some(e => /Ленина 109/.test(e.message)));
  assert(examples.some(e => /Нижнего Тагила/.test(e.message)));
  const scenario = examples.find(e => /Ольхон/.test(e.message)); assert(scenario);
  const result = await service.handle({ message: scenario.message });
  assert.equal(result.trip.date_range.to, '2028-07-31'); assert.equal(result.trip.ground_preference, 'smart_transfer');
  assert.equal(result.plans[0].status, 'candidate'); assert.equal(result.plans[0].total_price, null);
  assert.match(result.plans[0].network_label, /Сценарный режим/);
});

test('external current/scenario mixing is rejected and callback cannot replace a selected flight', async () => {
  for (const violation of ['mode', 'selected']) {
    let calls = 0;
    const plan = validateCorridor(normalizeJourneyGraph(fixtureGraph()), ['bus', 'rw', 'coach'], fixtureTrip());
    if (violation === 'mode') plan.network_mode = 'scenario_2027_2028';
    const patch = violation === 'selected' ? { ...tripPatch, selected_flight: { number: 'WZ 99999', date: '2026-12-01' } } : tripPatch;
    const service = createChatService({ config: fixtureConfig, journeySearch: async () => ({ status: 'ok', plans: [plan] }),
      provider(model) { return respond(model, ++calls === 1 ? [call('update_trip', patch), call('find_journey_options')] : [say('По этим условиям подтверждённого пути нет.')]); } });
    const result = await service.handle({ message: 'Поиск' });
    assert.deepEqual(result.plans, []); assert.equal(result.status, 'partial');
  }
});
