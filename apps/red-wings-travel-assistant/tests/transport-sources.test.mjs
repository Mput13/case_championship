import test from 'node:test';
import assert from 'node:assert/strict';
import { YandexTransportSource, normalizeTransportSegment, normalizeTransportChain } from '../src/transport-sources.mjs';
const bus = { has_transfers: false, from: { code: 's100', title: 'Автовокзал A' }, to: { code: 's200', title: 'Автовокзал B' }, departure: '2026-12-11T07:00:00+05:00', arrival: '2026-12-11T12:00:00+05:00', thread: { uid: 'source-thread', number: '561', transport_type: 'bus', carrier: { title: 'Test carrier' } } };
test('a concrete bus segment preserves stops, offset, number and source; no fare is invented', () => {
  const row = normalizeTransportSegment(bus, '2026-11-13T13:00:00Z');
  assert.equal(row.mode, 'bus'); assert.equal(row.origin, 'Автовокзал A'); assert.equal(row.number, '561');
  assert.equal(row.duration_minutes, 300); assert.equal(row.evidence_status, 'dated'); assert.equal(row.price, null);
  assert.equal(normalizeTransportSegment({ ...bus, arrival: null }, '').duration_minutes, null);
});
test('missing key and exhausted turn budget make zero external requests', async () => {
  let calls = 0; const fetchImpl = () => { calls++; throw new Error('Must not fetch'); };
  const missing = await new YandexTransportSource({}, { fetchImpl }).search({ from: 's100', to: 's200', date: '2026-12-11', budget: { remaining: 4 } });
  assert.equal(missing.status, 'key_required');
  const capped = await new YandexTransportSource({ yandexKey: 'test-only' }, { fetchImpl }).search({ from: 's100', to: 's200', budget: { remaining: 0 } });
  assert.equal(capped.status, 'request_budget_exhausted'); assert.equal(calls, 0);
});
test('calendar discovery has no invented date and keeps header-only auth; one transport GET consumes one slot', async () => {
  let calls = 0; const budget = { remaining: 2 };
  const source = new YandexTransportSource({ yandexKey: 'test-only' }, { fetchImpl: async (url, options) => {
    calls++; assert.equal(url.hostname, 'api.rasp.yandex-net.ru'); assert(!url.searchParams.has('date')); assert(!url.searchParams.has('apikey'));
    assert.equal(options.headers.Authorization, 'test-only'); assert.equal(url.searchParams.get('add_days_mask'), 'true');
    return new Response(JSON.stringify({ search: { from: { code: 's100' }, to: { code: 's200' } }, pagination: { offset: 0, total: 1 }, segments: [{ ...bus, departure: null, arrival: null, days: 'пятница' }] }));
  } });
  const result = await source.search({ from: 's100', to: 's200', modes: ['bus'], budget });
  assert.equal(calls, 1); assert.equal(budget.remaining, 1); assert.equal(result.calendar_query, true);
  assert.deepEqual(result.checked_dates, []); assert.equal(result.legs[0].departure, null); assert.equal(result.legs[0].evidence_status, 'published_pattern');
});
test('upstream failures stay unknown and cannot turn into no routes or cached results', async () => {
  let calls = 0;
  const source = new YandexTransportSource({ yandexKey: 'test-only' }, { fetchImpl: async () => { calls++; return new Response('{}', { status: 429 }); } });
  const result = await source.search({ from: 's100', to: 's200', date: '2026-12-11', budget: { remaining: 2 } });
  assert.equal(result.status, 'upstream_unavailable'); assert.equal(result.complete, false); assert.equal(calls, 1);
});

// Offline fixture with the live details schema: transport from/to are cities,
// while the journey bounds and is_transfer records identify physical stations.
const station = (code, title = code) => ({ code, title, type: 'station' });
const chainFixture = () => ({ has_transfers: true, departure_from: station('s100'), arrival_to: station('s300'),
  departure: '2026-12-11T07:00:00+05:00', arrival: '2026-12-11T14:00:00+05:00', details: [
    { ...bus, has_transfers: undefined, from: { code: 'c100' }, to: { code: 'c200' }, thread: { ...bus.thread, transport_type: 'train' } },
    { is_transfer: true, duration: 1800, transfer_point: { code: 'c200' }, transfer_from: station('s200'), transfer_to: station('s200') },
    { ...bus, has_transfers: undefined, from: { code: 'c200' }, to: { code: 'c300' }, departure: '2026-12-11T12:30:00+05:00', arrival: '2026-12-11T14:00:00+05:00',
      thread: { ...bus.thread, uid: 'second-train', number: '45', transport_type: 'train' } },
  ] });
test('composite details resolve each real train and same-station wait without a synthetic ground leg', () => {
  const chain = normalizeTransportChain(chainFixture(), '2026-11-13T13:00:00Z', { date: '2026-12-11' });
  assert.deepEqual(chain.legs.map(l => [l.from, l.to, l.mode]), [['s100', 's200', 'train'], ['s200', 's300', 'train']]);
  assert.deepEqual(chain.legs.map(l => l.source_detail_index), [0, 2]);
  assert.equal(chain.gaps.length, 0); assert.equal(chain.legs[0].arrival, bus.arrival);
  assert(chain.legs.every(l => l.price === null && l.source_query_date === '2026-12-11' && l.links.some(link => link.url === chain.source_url)));
});
test('different physical nodes retain a gap; missing or conflicting station details reject a chain', () => {
  const changed = chainFixture(); changed.details[1].transfer_to = station('s201');
  const chain = normalizeTransportChain(changed, '', { date: '2026-12-11' });
  assert.equal(chain.legs[1].from, 's201');
  assert.deepEqual(chain.gaps.map(g => [g.from, g.to]), [['s200', 's201']]);
  delete changed.details[1].transfer_to;
  assert.equal(normalizeTransportChain(changed, '', { date: '2026-12-11' }), null);
  const conflict = chainFixture(); conflict.details[0].to = station('s999');
  assert.equal(normalizeTransportChain(conflict, '', { date: '2026-12-11' }), null);
  const missing = chainFixture(); missing.details.splice(1, 1);
  assert.equal(normalizeTransportChain(missing, '', { date: '2026-12-11' }), null);
});
test('calendars, unsupported legs and impossible UTC chronology cannot create composite dated proof', () => {
  assert.equal(normalizeTransportChain(chainFixture(), ''), null);
  assert.equal(normalizeTransportChain({ ...bus, from: { code: 'c100' } }, '', { date: '2026-12-11' }), null);
  const missing = chainFixture(); missing.details[0].departure = null;
  assert.equal(normalizeTransportChain(missing, '', { date: '2026-12-11' }), null);
  const unsupported = chainFixture(); unsupported.details[2].thread.transport_type = 'plane';
  assert.equal(normalizeTransportChain(unsupported, '', { date: '2026-12-11' }), null);
  const utc = chainFixture(); utc.details[2].departure = '2026-12-11T13:00:00+08:00';
  assert.equal(normalizeTransportChain(utc, '', { date: '2026-12-11' }), null);
});
test('searchChains makes one transfers=true GET under the same budget and leaves direct search compatible', async () => {
  const calls = [], budget = { remaining: 2 };
  const source = new YandexTransportSource({ yandexKey: 'test-only' }, { fetchImpl: async (url, options) => {
    calls.push(url); assert(!url.searchParams.has('apikey')); assert.equal(options.headers.Authorization, 'test-only');
    return new Response(JSON.stringify({ search: { from: { code: 's100' }, to: { code: 's300' }, date: '2026-12-11' },
      pagination: { offset: 0, total: 1 }, segments: [chainFixture()] }));
  } });
  const query = { from: 's100', to: 's300', date: '2026-12-11', budget };
  const composite = await source.searchChains(query), direct = await source.search(query);
  assert.equal(calls[0].searchParams.get('transfers'), 'true'); assert.equal(calls[1].searchParams.get('transfers'), 'false');
  assert.equal(budget.remaining, 0); assert.equal(composite.chains.length, 1); assert.equal(composite.complete, true);
  assert.deepEqual(composite.legs, []); assert.deepEqual(direct.legs, []); assert.equal(direct.complete, false);
  assert.equal((await source.searchChains(query)).status, 'request_budget_exhausted'); assert.equal(calls.length, 2);
});
test('composite errors and unparsed records preserve incomplete upstream coverage', async () => {
  for (const payload of [null, { search: {}, segments: [] }, {
    search: { from: { code: 's100' }, to: { code: 's300' }, date: '2026-12-11' },
    pagination: { offset: 0, total: 1 }, segments: [{ has_transfers: true, details: [] }],
  }]) {
    let calls = 0;
    const source = new YandexTransportSource({ yandexKey: 'test-only' }, { fetchImpl: async () => {
      calls++; return new Response(JSON.stringify(payload), { status: payload === null ? 503 : 200 });
    } });
    const result = await source.searchChains({ from: 's100', to: 's300', date: '2026-12-11', budget: { remaining: 1 } });
    assert.equal(calls, 1); assert.equal(result.complete, false); assert.deepEqual(result.chains, []);
    if (payload === null || !payload.search.from) assert.equal(result.status, 'upstream_unavailable');
  }
});
test('composite lookup requires a date and calendar search cannot promote returned timestamps', async () => {
  let calls = 0;
  const source = new YandexTransportSource({ yandexKey: 'test-only' }, { fetchImpl: async () => {
    calls++; return new Response(JSON.stringify({ search: { from: { code: 's100' }, to: { code: 's200' } },
      pagination: { offset: 0, total: 1 }, segments: [bus] }));
  } });
  await assert.rejects(source.searchChains({ from: 's100', to: 's200', budget: { remaining: 1 } }), { code: 'invalid_transport_query' });
  assert.equal(calls, 0);
  const calendar = await source.search({ from: 's100', to: 's200', budget: { remaining: 1 } });
  assert.equal(calendar.legs[0].evidence_status, 'published_pattern'); assert.deepEqual(calendar.checked_dates, []);
});
