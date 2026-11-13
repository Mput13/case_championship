import test from 'node:test';
import assert from 'node:assert/strict';
import { createJourneySearch } from '../src/multimodal-search.mjs';
import { acceptJourneyResult } from '../src/chat-callbacks.mjs';

// Entirely injected offline schedules. These are not claims about real services.
const checked = '2026-11-13T12:00:00Z';
const a = { id: 's10', title: 'Аэропорт Альфа', type: 'airport', city_id: 'c10', city: 'Альфа', lat: 57, lon: 60 };
const b = { id: 's20', title: 'Аэропорт Бета', type: 'airport', city_id: 'c20', city: 'Бета', lat: 56, lon: 61 };
const oStation = { id: 's1', title: 'Город А, вокзал', type: 'train_station' };
const dStation = { id: 's2', title: 'Город Б, автовокзал', type: 'bus_station' };
const origin = { id: 'c1', title: 'Город А', region: 'Северная область', lat: 57.4, lon: 60, stations: [oStation] };
const destination = { id: 'c2', title: 'Город Б', region: 'Южная область', lat: 55.6, lon: 61, stations: [dStation] };
const trip = (patch = {}) => ({ origin: { city: 'Город А, Северная область' }, destination: { city: 'Город Б, Южная область' },
  network_mode: 'current', date_range: { from: '2026-12-04', to: '2026-12-04', meaning: 'departure_window' }, constraints: {}, ...patch });
const segment = (id, mode, from, to, departure, arrival, extra = {}) => ({ id, mode, from, to, origin: from === 's1' ? oStation.title : from === a.id ? a.title : from === b.id ? b.title : from,
  destination: to === 's2' ? dStation.title : to === a.id ? a.title : to === b.id ? b.title : to,
  departure, arrival, evidence_status: 'dated', number: id, price: 999, source_name: 'Offline fixture', checked_at: checked,
  source_url: `https://rasp.yandex.ru/thread/${id}/`, links: [{ label: 'Источник участка', url: `https://rasp.yandex.ru/thread/${id}/` }], ...extra });
const flight = (date = '2026-12-04', extra = {}) => segment(`wz-${date}`, 'plane', a.id, b.id, `${date}T12:00:00+05:00`, `${date}T14:00:00+05:00`, { carrier_iata: 'WZ', carrier_code: 617, number: 'WZ 777', ...extra });
const feeder = (date = '2026-12-04', extra = {}) => segment(`feeder-${date}`, 'train', 's1', a.id, `${date}T06:00:00+05:00`, `${date}T09:30:00+05:00`, extra);
const onward = (date = '2026-12-04', extra = {}) => segment(`onward-${date}`, 'bus', b.id, 's2', `${date}T15:00:00+05:00`, `${date}T17:00:00+05:00`, extra);
const envelope = (segments = [], extra = {}) => ({ status: 'ok', complete: true, segments, checked_at: checked, ...extra });
function placeIndex({ originAirports = [a], destinationAirports = [b], ambiguous = false } = {}) {
  const resolveCalls = [], airportCalls = [];
  const cities = [origin, destination, { id: 'c10', title: 'Альфа', stations: [a] }, { id: 'c20', title: 'Бета', stations: [b] }];
  return { resolveCalls, airportCalls,
    async resolve(query, { signal } = {}) {
      assert(!signal?.aborted); resolveCalls.push(query);
      if (ambiguous && query.includes('Город А')) return { status: 'ambiguous', places: [origin, { ...origin, id: 'c3', region: 'Другая область', stations: [] }] };
      const value = cities.find(p => query === p.id || query === p.title || query === `${p.title}, ${p.region}`);
      return { status: value ? 'ok' : 'not_found', places: value ? [value] : [] };
    },
    async nearbyAirports(place, options) { airportCalls.push({ id: place.id, ...options }); return place.id === origin.id ? originAirports : place.id === destination.id ? destinationAirports : place.stations.filter(s => s.type === 'airport'); },
    getStation(id) { return [...originAirports, ...destinationAirports, oStation, dStation].find(s => s.id === id); },
  };
}
function transport(handler, scheduleHandler) {
  const calls = [];
  return { calls,
    async search(query) { calls.push({ kind: 'search', ...query, budget: { ...query.budget } }); assert(query.budget.remaining > 0); query.budget.remaining--; return handler(query) ?? envelope(); },
    async schedule(query) {
      calls.push({ kind: 'schedule', ...query, budget: { ...query.budget } }); assert(query.budget.remaining > 0); query.budget.remaining--;
      return scheduleHandler?.(query) ?? envelope([], { departures: query.station === a.id ? [{ from: a.id, origin: a.title, destination_query: 'Бета', number: 'WZ 777', carrier_code: 617, carrier_iata: 'WZ', departure: '12:00', arrival: null, published_days: 'пятница' }] : [] });
    },
  };
}
function usual(query) {
  if (query.from === a.id && query.to === b.id) return envelope([flight(query.date)]);
  if (query.from === origin.id && query.to === a.id) return envelope([feeder(query.date)]);
  if (query.from === b.id && query.to === destination.id) return envelope([onward(query.date)]);
  return envelope();
}

test('generic cities resolve with regions; a dated feeder/WZ/onward chain is verified', async () => {
  const places = placeIndex(), source = transport(usual);
  const result = await createJourneySearch({ source, places }).search(trip());
  const plan = result.plans.find(p => p.requires_red_wings);
  assert.equal(plan.status, 'verified');
  assert.deepEqual(plan.legs.map(l => l.mode), ['train', 'plane', 'bus']);
  assert.equal(plan.total_duration_minutes, 660);
  assert.deepEqual(plan.connections.map(c => c.minimum_minutes), [120, 60]);
  assert.deepEqual(places.resolveCalls.slice(0, 2), ['Город А, Северная область', 'Город Б, Южная область']);
  assert(places.resolveCalls.includes('Бета'));
  assert.equal(source.calls.find(c => c.kind === 'schedule').date, '2026-12-04');
  assert.equal(source.calls.filter(c => c.from === a.id && c.to === b.id).length, 1);
  assert(acceptJourneyResult(result, trip()));
});

test('a feeder arriving at the airport node does not acquire a city detour or transfer', async () => {
  let transferCalls = 0;
  const source = transport(usual);
  const result = await createJourneySearch({ source, places: placeIndex(), transfer() { transferCalls++; throw new Error('no physical gap'); } }).search(trip());
  const plan = result.plans.find(p => p.requires_red_wings);
  assert.equal(transferCalls, 0);
  assert.equal(plan.legs[0].to, a.id);
  assert(!source.calls.some(c => c.from === origin.id && c.to === a.city_id));
  assert.equal(plan.gaps.length, 0);
});

test('a named bus stop at an airport is retained, but its distinct node needs a physical transition', async () => {
  const source = transport(q => q.from === origin.id && q.to === a.id ? envelope([feeder(q.date, { mode: 'bus', to: 's11', destination: 'Автокасса аэропорта Альфа', to_city_id: 'c10' })]) : usual(q));
  const missing = await createJourneySearch({ source, places: placeIndex() }).search(trip());
  const partial = missing.plans.find(p => p.requires_red_wings);
  assert.equal(partial.status, 'partial'); assert.equal(partial.total_duration_minutes, null);
  assert.equal(partial.legs[0].to, 's11');
  assert(partial.gaps.some(g => g.kind === 'transfer'));
  assert(!source.calls.some(c => c.from === origin.id && c.to === a.city_id));

  const transitions = [];
  const complete = await createJourneySearch({ source: transport(q => q.from === origin.id && q.to === a.id ? envelope([feeder(q.date, { mode: 'bus', to: 's11', destination: 'Автокасса аэропорта Альфа', to_city_id: 'c10' })]) : usual(q)), places: placeIndex(),
    async transfer(q) {
      transitions.push(q);
      return segment('terminal-walk', 'walk', q.from.id, q.to.id, '2026-12-04T09:30:00+05:00', '2026-12-04T09:40:00+05:00');
    },
  }).search(trip());
  assert.equal(transitions.length, 1); assert.equal(transitions[0].from.id, 's11'); assert.equal(transitions[0].to.id, a.id);
  assert.equal(complete.plans.find(p => p.requires_red_wings).status, 'verified');
});

test('city-station feeder and onward transitions use the callback with post-flight buffer', async () => {
  const transfers = [];
  const source = transport(q => {
    if (q.from === origin.id && q.to === a.id) return envelope();
    if (q.from === origin.id && q.to === a.city_id) return envelope([feeder(q.date, { to: 's12', destination: 'Альфа, вокзал', to_city_id: 'c10' })]);
    if (q.from === b.id && q.to === destination.id) return envelope();
    if (q.from === b.city_id && q.to === destination.id) return envelope([onward(q.date, { from: 's22', origin: 'Бета, вокзал', from_city_id: 'c20', departure: `${q.date}T16:00:00+05:00` })]);
    return usual(q);
  });
  const result = await createJourneySearch({ source, places: placeIndex(), async transfer(q) {
    transfers.push(q);
    return segment(`transfer-${q.from.id}`, 'bus', q.from.id, q.to.id, q.notBefore, new Date(Date.parse(q.notBefore) + 20 * 60000).toISOString());
  } }).search(trip());
  const plan = result.plans.find(p => p.requires_red_wings);
  assert.equal(plan.status, 'verified'); assert.equal(plan.legs.length, 5);
  assert.equal(Date.parse(transfers.find(q => q.from.id === b.id).notBefore), Date.parse(flight().arrival) + 60 * 60000);
});

test('a 90-minute feeder connection fails the 120-minute pre-flight buffer', async () => {
  const source = transport(q => q.from === origin.id && q.to === a.id ? envelope([feeder(q.date, { arrival: `${q.date}T10:30:00+05:00` })]) : usual(q));
  const result = await createJourneySearch({ source, places: placeIndex() }).search(trip());
  assert(!result.plans.some(p => p.status === 'verified' && p.requires_red_wings));
  assert(!result.plans.some(p => p.legs.some(l => l.id.startsWith('feeder-'))));
  assert(result.coverage.excluded.connection_too_short > 0);
  assert(!result.plans.some(p => p.requires_red_wings));
});

test('UTC offsets, not clock-face subtraction, determine connection feasibility', async () => {
  const source = transport(q => q.from === origin.id && q.to === a.id ? envelope([feeder(q.date, { departure: `${q.date}T06:00:00+03:00`, arrival: `${q.date}T09:00:00+03:00` })]) : usual(q));
  // 09:00+03 is 06:00Z, 12:00+05 is 07:00Z: only sixty minutes.
  const result = await createJourneySearch({ source, places: placeIndex() }).search(trip());
  assert(result.coverage.excluded.connection_too_short > 0);
  assert(!result.plans.some(p => p.requires_red_wings && p.status === 'verified'));
});

test('post-flight transfer duration is additional to the sixty-minute arrival buffer', async () => {
  const source = transport(q => q.from === b.id && q.to === destination.id ? (q.date === '2026-12-04' ? envelope([onward(q.date, { from: 's22', from_city_id: b.city_id, departure: `${q.date}T15:10:00+05:00` })]) : envelope()) : usual(q));
  const result = await createJourneySearch({ source, places: placeIndex(), async transfer(q) {
    return segment('long-transfer', 'taxi', q.from.id, q.to.id, q.notBefore, new Date(Date.parse(q.notBefore) + 30 * 60000).toISOString());
  } }).search(trip());
  assert(!result.plans.some(p => p.requires_red_wings && p.status === 'verified'));
  assert(result.coverage.excluded.connection_too_short > 0);
});

test('estimated physical transitions stay partial, and cannot rescue an impossible connection', async () => {
  const make = arrival => transport(q => q.from === origin.id && q.to === a.id ? envelope([feeder(q.date, { to: 's12', to_city_id: a.city_id, arrival: `${q.date}T${arrival}:00+05:00` })]) : usual(q));
  const transfer = async q => segment('estimated', 'taxi', q.from.id, q.to.id, null, null, { duration_minutes: 45, evidence_status: 'indicative' });
  const partial = await createJourneySearch({ source: make('09:00'), places: placeIndex(), transfer }).search(trip());
  assert.equal(partial.plans.find(p => p.requires_red_wings).status, 'partial');
  assert.equal(partial.plans.find(p => p.requires_red_wings).total_duration_minutes, null);
  const impossible = await createJourneySearch({ source: make('09:30'), places: placeIndex(), transfer }).search(trip());
  assert(impossible.coverage.excluded.connection_too_short > 0);
  assert(!impossible.plans.some(p => p.legs.some(l => l.id === 'estimated')));
});

test('upstream and budget exhaustion mean unknown, never a claim of no route', async () => {
  const source = transport(() => envelope(), () => envelope([], { status: 'upstream_unavailable', complete: false }));
  const result = await createJourneySearch({ source, places: placeIndex(), config: { maxRequests: 2 } }).search(trip());
  assert.equal(result.status, 'partial'); assert.equal(result.coverage.complete, false);
  assert.equal(result.coverage.request_budget.used, 2); assert.equal(result.coverage.request_budget.exhausted, true);
  assert.equal(source.calls.length, 2);
  assert(result.missing_data.some(m => m.includes('upstream_unavailable')));
  assert(result.missing_data.some(m => m.includes('не доказывают отсутствие')));
  assert(result.missing_data.some(m => m.includes('неизвестными')));
});

test('an adapter that ignores budget mutations still cannot exceed the cap', async () => {
  let count = 0;
  const source = { async search() { count++; return envelope(); }, async schedule() { count++; return envelope(); } };
  const result = await createJourneySearch({ source, places: placeIndex(), config: { maxRequests: 1 } }).search(trip());
  assert.equal(count, 1); assert.equal(result.coverage.request_budget.used, 1);
});

test('long windows use calendar-guided samples and dated flight validation, not a day-by-day loop', async () => {
  const source = transport(usual), places = placeIndex();
  const range = { from: '2026-12-01', to: '2027-01-15', meaning: 'departure_window' };
  const result = await createJourneySearch({ source, places }).search(trip({ date_range: range }));
  assert.deepEqual(result.coverage.requested_window, range);
  assert.equal(result.coverage.window_days, 46);
  assert(source.calls.length <= 24);
  const datedFlights = source.calls.filter(c => c.kind === 'search' && c.from === a.id && c.to === b.id);
  assert(datedFlights.length >= 1 && datedFlights.length <= 3);
  assert(datedFlights.every(q => new Date(`${q.date}T00:00:00Z`).getUTCDay() === 5));
  assert(datedFlights.some(q => q.date === '2027-01-15'));
  assert(result.missing_data.some(m => m.includes('выборка дат')));
  assert.equal(result.coverage.exhaustive, false);
  assert(result.plans.filter(p => p.requires_red_wings).every(p => p.legs.find(l => l.mode === 'plane').evidence_status === 'dated'));
});

test('five nearby airports are researched; a fourth airport with WZ is not silently lost', async () => {
  const closer = [3, 4, 5].map((n, i) => ({ id: `s${n}0`, title: `Ближний аэропорт ${n}`, type: 'airport', city_id: `c${n}0`, lat: origin.lat - i * 0.05, lon: origin.lon }));
  const places = placeIndex({ originAirports: [...closer, a] }), source = transport(usual);
  const result = await createJourneySearch({ source, places }).search(trip());
  assert.equal(places.airportCalls.find(q => q.id === origin.id).limit, 5);
  assert.equal(source.calls.filter(q => q.kind === 'schedule').length, 4);
  assert(result.plans.some(p => p.requires_red_wings && p.status === 'verified'));
});

test('long and overnight waits are explicit and an overnight prohibition is respected', async () => {
  const handler = q => q.from === b.id && q.to === destination.id ? (q.date === '2026-12-05' ? envelope([onward(q.date, { departure: '2026-12-05T07:00:00+05:00', arrival: '2026-12-05T09:00:00+05:00' })]) : envelope()) : usual(q);
  const result = await createJourneySearch({ source: transport(handler), places: placeIndex() }).search(trip());
  const plan = result.plans.find(p => p.requires_red_wings);
  assert.equal(plan.status, 'verified'); assert(plan.warnings.some(w => w.includes('следующего дня')));
  assert.equal(plan.total_duration_minutes, 1620);
  const blocked = await createJourneySearch({ source: transport(handler), places: placeIndex() }).search(trip({ constraints: { allow_overnight: false } }));
  assert(!blocked.plans.some(p => p.requires_red_wings && p.status === 'verified'));
});

test('station-specific provenance and official RW booking links survive; fares remain unknown', async () => {
  const result = await createJourneySearch({ source: transport(usual), places: placeIndex() }).search(trip());
  const plan = result.plans.find(p => p.requires_red_wings);
  for (const l of plan.legs) { assert.equal(l.price, null); assert(l.links.some(v => v.url === l.source_url)); }
  assert(plan.legs.find(l => l.mode === 'plane').links.some(v => v.url === 'https://flyredwings.com/booking/'));
  assert(result.sources.some(s => s.url === feeder().source_url));
  assert(result.sources.some(s => s.url === flight().source_url));
  assert.equal(plan.total_price, null);
});

test('a non-airport destination needs a real onward; a supplied address stays a gap', async () => {
  const noOnward = await createJourneySearch({ source: transport(q => q.from === b.id || q.from === b.city_id ? envelope() : usual(q)), places: placeIndex() }).search(trip());
  assert(!noOnward.plans.some(p => p.requires_red_wings));
  assert(noOnward.coverage.excluded.no_feasible_onward > 0);
  const withAddress = await createJourneySearch({ source: transport(usual), places: placeIndex() }).search(trip({ origin: { city: 'Город А, Северная область', address: 'Улица Примерная, 7' } }));
  const addressed = withAddress.plans.find(p => p.requires_red_wings);
  assert.equal(addressed.status, 'partial'); assert(addressed.gaps.some(g => g.kind === 'first_mile'));
  assert.equal(addressed.recommendation.status, 'needs_validation');
  assert(addressed.warnings.some(w => w.includes('Не покупайте')));
  assert.deepEqual(addressed.legs.map(l => l.mode), ['train', 'plane', 'bus']);
});

test('ground comparisons stay visible while other-airline flights never enter passenger plans', async () => {
  const source = transport(q => {
    if (q.from === origin.id && q.to === destination.id) return envelope([segment('direct', 'train', 's1', 's2', `${q.date}T07:00:00+05:00`, `${q.date}T12:00:00+05:00`)]);
    if (q.from === a.id && q.to === b.id) return envelope([flight(q.date), flight(q.date, { id: `other-${q.date}`, carrier_code: 99, carrier_iata: 'XX', number: 'XX 1' })]);
    return usual(q);
  });
  const result = await createJourneySearch({ source, places: placeIndex() }).search(trip());
  assert.equal(result.plans.filter(p => !p.requires_red_wings).length, 1);
  assert.deepEqual(new Set(result.plans.filter(p => !p.requires_red_wings).map(p => p.variant)), new Set(['all_transport_direct']));
  assert.equal(result.plans.find(p => p.requires_red_wings).reasonableness.status, 'detour');
  assert(result.plans.filter(p => !p.requires_red_wings).every(p => !p.legs.some(l => l.carrier_iata === 'WZ')));
  assert(result.plans.every(p => p.legs.every(l => l.mode !== 'plane' || l.carrier_iata === 'WZ' && l.carrier_code === 617)));
});

test('partial chains and different terminal endpoints cannot establish a detour comparison', async () => {
  const source = transport(q => {
    if (q.from === origin.id && q.to === destination.id) return envelope([segment('direct', 'train', 's9', 's2', `${q.date}T07:00:00+05:00`, `${q.date}T12:00:00+05:00`)]);
    return usual(q);
  });
  const result = await createJourneySearch({ source, places: placeIndex() }).search(trip());
  assert.equal(result.plans.find(p => p.requires_red_wings).reasonableness.status, 'unknown');
});

test('departure-window meaning and ambiguous regions require input, not addresses or taxi choices', async () => {
  const source = transport(usual);
  const unknown = await createJourneySearch({ source, places: placeIndex() }).search(trip({ date_range: { from: '2026-12-01', to: '2027-01-15', meaning: 'unknown' } }));
  assert.equal(unknown.status, 'needs_input'); assert.deepEqual(unknown.missing_fields, ['date_range.meaning']); assert.equal(source.calls.length, 0);
  const ambiguous = await createJourneySearch({ source, places: placeIndex({ ambiguous: true }) }).search(trip());
  assert.equal(ambiguous.status, 'needs_input'); assert.equal(source.calls.length, 0); assert.equal(ambiguous.place_choices.origin.places.length, 2);
});

test('calendar hints with no dated flight never become flight plans; marketing numbers alone are insufficient', async () => {
  const source = transport(() => envelope());
  const result = await createJourneySearch({ source, places: placeIndex() }).search(trip());
  assert(!result.plans.some(p => p.requires_red_wings));
  const fakeCarrier = transport(usual, () => envelope([], { departures: [{ destination_query: 'Бета', number: 'WZ 777', carrier_iata: 'XX', carrier_code: 99, published_days: 'ежедневно' }] }));
  const fake = await createJourneySearch({ source: fakeCarrier, places: placeIndex() }).search(trip());
  assert.equal(fake.coverage.calendar_routes.length, 0);
});

test('legs envelopes are supported and cancellation propagates without an external retry', async () => {
  const source = transport(q => { const { segments, ...rest } = usual(q); return { ...rest, legs: segments }; });
  const result = await createJourneySearch({ source, places: placeIndex() }).search(trip());
  assert(result.plans.some(p => p.requires_red_wings && p.status === 'verified'));
  const controller = new AbortController(); let calls = 0;
  const cancelled = createJourneySearch({ places: placeIndex(), source: {
    async search() { throw new Error('unexpected'); },
    async schedule() { calls++; controller.abort(); throw new Error('stopped'); },
  } });
  await assert.rejects(cancelled.search(trip(), { signal: controller.signal }), { name: 'AbortError' });
  assert.equal(calls, 1);
});

test('airport access stops are discovered and queried by their real station ids before a city fallback', async () => {
  const stop = { id: 's11', title: 'Альфа, автокасса Аэропорт', type: 'bus_station', transport_type: 'bus', lat: a.lat + 0.0001, lon: a.lon };
  const source = transport(q => {
    if (q.from === origin.id && q.to === a.id) return envelope();
    if (q.from === origin.id && q.to === stop.id) return envelope([feeder(q.date, { mode: 'bus', to: stop.id, destination: stop.title })]);
    return usual(q);
  });
  source.nearestStations = async q => { source.calls.push({ kind: 'nearestStations', ...q }); q.budget.remaining--; return { status: 'ok', complete: true, stations: [stop] }; };
  const transitions = [];
  const result = await createJourneySearch({ source, places: placeIndex(), async transfer(q) {
    transitions.push(q);
    return segment('short-walk', 'walk', q.from.id, q.to.id, '2026-12-04T09:30:00+05:00', '2026-12-04T09:35:00+05:00');
  } }).search(trip());
  assert.equal(result.plans.find(p => p.requires_red_wings).status, 'verified');
  assert(source.calls.some(c => c.kind === 'nearestStations'));
  assert(source.calls.some(c => c.from === origin.id && c.to === stop.id));
  assert(!source.calls.some(c => c.from === origin.id && c.to === a.city_id));
  assert.equal(transitions[0].from.lat, stop.lat);
  assert.equal(transitions[0].from.lon, stop.lon);
});

test('complete convenient connections outrank long waits without changing their evidence status', async () => {
  const source = transport(q => q.from === origin.id && q.to === a.id ? envelope([
    feeder(q.date, { id: 'very-early', arrival: `${q.date}T05:00:00+05:00`, departure: `${q.date}T01:00:00+05:00` }),
    feeder(q.date, { id: 'convenient' }),
  ]) : usual(q));
  const result = await createJourneySearch({ source, places: placeIndex() }).search(trip());
  const plans = result.plans.filter(p => p.requires_red_wings);
  assert.equal(plans.length, 2); assert(plans.every(p => p.status === 'verified'));
  assert.equal(plans[0].legs[0].id, 'convenient'); assert.equal(plans[0].recommendation.status, 'schedule_checked');
  assert.equal(plans[1].connection_quality.long_wait_count, 1);
  assert.equal(plans[1].recommendation.status, 'inconvenient');
  assert(plans[1].warnings.some(w => w.includes('Длительное ожидание')));
});

test('an unknown feeder response preserves only a partial candidate, not a purchase recommendation', async () => {
  const source = transport(q => q.from === origin.id ? envelope([], { status: 'upstream_unavailable', complete: false }) : usual(q));
  const result = await createJourneySearch({ source, places: placeIndex() }).search(trip());
  const plan = result.plans.find(p => p.requires_red_wings);
  assert.equal(plan.status, 'partial'); assert.equal(plan.total_duration_minutes, null);
  assert.equal(plan.recommendation.status, 'needs_validation');
  assert(plan.warnings.some(w => w.includes('Не покупайте')));
  assert(plan.gaps.some(g => g.kind === 'feeder'));
});

test('separate region and place_id fields are honored; scenario search makes no transport requests', async () => {
  const places = placeIndex(), source = transport(usual);
  await createJourneySearch({ source, places }).search(trip({ origin: { city: 'Город А', region: 'Северная область' }, destination: { city: 'Город Б', place_id: 'c2' } }));
  assert(places.resolveCalls.includes('Город А, Северная область')); assert(places.resolveCalls.includes('c2'));
  const scenarioSource = transport(usual);
  const result = await createJourneySearch({ source: scenarioSource, places: placeIndex() }).search(trip({ network_mode: 'scenario_2027_2028' }));
  assert.equal(result.status, 'partial'); assert.equal(result.plans.length, 0); assert.equal(scenarioSource.calls.length, 0);
});

test('public-only preference excludes taxi transitions even when taxis were not explicitly forbidden', async () => {
  const source = transport(q => q.from === origin.id && q.to === a.id ? envelope([feeder(q.date, { to: 's12', to_city_id: a.city_id })]) : usual(q));
  const result = await createJourneySearch({ source, places: placeIndex(), async transfer(q) {
    return segment('taxi', 'taxi', q.from.id, q.to.id, q.notBefore, new Date(Date.parse(q.notBefore) + 10 * 60000).toISOString());
  } }).search(trip({ ground_preference: 'public' }));
  assert(!result.plans.some(p => p.legs.some(l => l.mode === 'taxi')));
  assert(result.coverage.excluded.mode_excluded > 0);
});

test('a preserved flight number is not replaced, and known duration survives unknown fares', async () => {
  const result = await createJourneySearch({ source: transport(usual), places: placeIndex() }).search(trip({ selected_flight: { number: 'WZ 999', date: '2026-12-04' } }));
  assert(!result.plans.some(p => p.requires_red_wings));
  const budget = await createJourneySearch({ source: transport(usual), places: placeIndex() }).search(trip({ constraints: { max_budget: 5000 } }));
  const plan = budget.plans.find(p => p.requires_red_wings);
  assert.equal(plan.status, 'partial'); assert.equal(plan.total_price, null); assert.equal(plan.total_duration_minutes, 660);
});

test('a selected flight uses its dated board instead of losing it in a truncated undated calendar', async () => {
  const source = transport(usual, q => envelope([], { complete: true, departures: q.station === a.id && q.date === '2026-12-04'
    ? [{ from: a.id, destination_query: 'Бета', carrier_iata: 'WZ', carrier_code: 617, mode: 'plane', number: 'WZ 777' }] : [] }));
  const result = await createJourneySearch({ source, places: placeIndex() }).search(trip({ selected_flight: { number: 'WZ 777', date: '2026-12-04' } }));
  assert(result.plans.some(p => p.requires_red_wings && p.legs.some(l => l.number === 'WZ 777')));
  assert(source.calls.filter(c => c.kind === 'schedule').every(c => c.date === '2026-12-04'));
});

test('a known transfer that leaves before the post-flight buffer is excluded, not relabeled unknown', async () => {
  const source = transport(q => q.from === b.id && q.to === destination.id ? (q.date === '2026-12-04' ? envelope([onward(q.date, { from: 's22', from_city_id: b.city_id, departure: '2026-12-04T16:00:00+05:00' })]) : envelope()) : usual(q));
  const result = await createJourneySearch({ source, places: placeIndex(), async transfer(q) {
    return segment('too-early-transfer', 'bus', q.from.id, q.to.id, '2026-12-04T14:30:00+05:00', '2026-12-04T14:50:00+05:00');
  } }).search(trip());
  assert(!result.plans.some(p => p.requires_red_wings));
  assert(result.coverage.excluded.connection_too_short > 0);
  assert(result.coverage.transfers.some(t => t.status === 'connection_too_short'));
});

test('an unidentified or conflicting airline cannot be described as a baseline without RW', async () => {
  const source = transport(q => q.from === a.id && q.to === b.id ? envelope([
    flight(q.date), flight(q.date, { id: 'carrier-unknown', carrier_code: null, carrier_iata: null }),
    flight(q.date, { id: 'carrier-conflict', carrier_code: 99, carrier_iata: 'WZ' }),
  ]) : usual(q));
  const result = await createJourneySearch({ source, places: placeIndex() }).search(trip());
  assert(!result.plans.some(p => !p.requires_red_wings));
  assert(result.plans.every(p => p.legs.every(l => l.mode !== 'plane' || l.carrier_iata === 'WZ' && l.carrier_code === 617)));
});

test('a flight with both municipal access legs unknown is coverage, not a proposed journey', async () => {
  const ownA = { ...a, city_id: origin.id }, ownB = { ...b, city_id: destination.id };
  const p1 = { ...origin, stations: [ownA] }, p2 = { ...destination, stations: [ownB] };
  const places = {
    async resolve(q) { const p = q.includes('Город А') || q === origin.id ? p1 : q === 'Бета' || q.includes('Город Б') || q === destination.id ? p2 : null; return { status: p ? 'ok' : 'not_found', places: p ? [p] : [] }; },
    async nearbyAirports(p) { return p.id === p1.id ? [ownA] : [ownB]; },
    async getStation(id) { return [ownA, ownB].find(s => s.id === id); },
  };
  const source = transport(q => q.from === a.id && q.to === b.id ? envelope([flight(q.date)]) : envelope());
  const result = await createJourneySearch({ source, places }).search(trip());
  const plan = result.plans.find(p => p.requires_red_wings);
  assert.equal(plan, undefined);
  assert(result.coverage.excluded.flight_only_with_missing_surface > 0);
  assert(result.missing_data.some(m => m.includes('подъезда')));
  assert(result.missing_data.some(m => m.includes('продолжения пути')));
});

function compositeSource({ gap = false, mutate, error = false } = {}) {
  const source = transport(q => q.from === origin.id && q.to === a.id ? envelope() : usual(q));
  source.searchChains = async q => {
    source.calls.push({ kind: 'searchChains', ...q, budget: { ...q.budget } }); q.budget.remaining--;
    if (error) return { status: 'upstream_unavailable', complete: false, chains: [] };
    if (q.from !== origin.id || q.to !== a.id) return { status: 'ok', complete: true, chains: [] };
    const legs = [segment('first-train', 'train', 's1', 's15', `${q.date}T06:00:00+05:00`, `${q.date}T07:00:00+05:00`),
      segment('second-train', 'train', gap ? 's16' : 's15', a.id, `${q.date}T07:30:00+05:00`, `${q.date}T09:30:00+05:00`)];
    mutate?.(legs);
    return { status: 'ok', complete: true, chains: [{ legs, gaps: [] }], checked_at: checked };
  };
  return source;
}
test('generic two-train feeder uses every real leg and preserves same-node connection checks', async () => {
  const source = compositeSource();
  const result = await createJourneySearch({ source, places: placeIndex() }).search(trip());
  const plan = result.plans.find(p => p.requires_red_wings);
  assert.equal(plan.status, 'verified');
  assert.deepEqual(plan.legs.map(l => l.mode), ['train', 'train', 'plane', 'bus']);
  assert.deepEqual(plan.connections.map(c => c.minimum_minutes), [0, 120, 60]);
  assert.equal(plan.connections[0].available_minutes, 30);
  assert.equal(plan.total_duration_minutes, 660);
  assert(plan.sources.some(s => s.url.endsWith('/second-train/')));
  assert.equal(result.coverage.chain_requests.used, 2); // feeder plus an empty baseline comparison
  assert(result.coverage.request_budget.used <= 24);
  const firstComposite = source.calls.findIndex(q => q.kind === 'searchChains');
  assert(source.calls.slice(0, firstComposite).some(q => q.kind === 'search' && q.from === origin.id && q.to === a.id));
  assert(acceptJourneyResult(result, trip()));
});
test('a composite never replaces an already usable direct feeder', async () => {
  const source = transport(usual), compositeQueries = [];
  source.searchChains = async q => { compositeQueries.push(q); q.budget.remaining--; return { status: 'ok', complete: true, chains: [] }; };
  const result = await createJourneySearch({ source, places: placeIndex() }).search(trip());
  assert(result.plans.some(p => p.requires_red_wings && p.status === 'verified'));
  assert(!compositeQueries.some(q => q.to === a.id || q.from === b.id));
});
test('a partial city-station fallback does not block a connected two-train route to the airport', async () => {
  const source = compositeSource(), originalSearch = source.search;
  source.search = async q => {
    const response = await originalSearch(q);
    return q.from === origin.id && q.to === a.city_id ? envelope([segment('city-only', 'train', 's1', 's19',
      `${q.date}T06:00:00+05:00`, `${q.date}T09:00:00+05:00`, { to_city_id: a.city_id })]) : response;
  };
  const places = placeIndex(), originalStation = places.getStation;
  places.getStation = id => id === 's19' ? { id, title: 'Вокзал Альфы', city_id: a.city_id, type: 'train_station' } : originalStation(id);
  const result = await createJourneySearch({ source, places }).search(trip());
  const best = result.plans.find(p => p.requires_red_wings);
  assert.equal(best.status, 'verified');
  assert(best.legs.some(l => l.id === 'second-train'));
  assert.equal(best.gaps.length, 0);
});
test('a second flight reuses a composite response after the composite GET cap is reached', async () => {
  const source = compositeSource(), direct = source.search;
  source.search = async q => {
    const answer = await direct(q);
    if (q.from === a.id && q.to === b.id) answer.segments.push(flight(q.date, { id: 'second-flight', number: 'WZ 778' }));
    return answer;
  };
  const result = await createJourneySearch({ source, places: placeIndex(), config: { maxChainRequests: 1 } }).search(trip());
  assert.equal(source.calls.filter(q => q.kind === 'searchChains').length, 1);
  assert.equal(result.plans.filter(p => p.requires_red_wings && p.status === 'verified').length, 2);
});
test('different stations inside a composite stay an explicit partial gap without a callback', async () => {
  const result = await createJourneySearch({ source: compositeSource({ gap: true }), places: placeIndex() }).search(trip());
  const plan = result.plans.find(p => p.requires_red_wings);
  assert.equal(plan.status, 'partial'); assert.equal(plan.total_duration_minutes, null);
  assert(plan.gaps.some(g => g.from === 's15' && g.to === 's16'));
  assert.equal(plan.connections[0].status, 'unknown');
  assert.equal(plan.legs.length, 4);
});
test('a real internal station move is inserted and its time must fit the next train', async () => {
  const run = duration => createJourneySearch({ source: compositeSource({ gap: true }), places: placeIndex(),
    async transfer(q) { return segment('station-move', 'walk', q.from.id, q.to.id, q.notBefore, new Date(Date.parse(q.notBefore) + duration * 60000).toISOString()); },
  }).search(trip());
  const fits = await run(15), plan = fits.plans.find(p => p.requires_red_wings);
  assert.equal(plan.status, 'verified'); assert.equal(plan.legs[1].mode, 'walk'); assert.equal(plan.gaps.length, 0);
  const impossible = await run(45);
  assert(!impossible.plans.some(p => p.requires_red_wings && p.status === 'verified'));
  assert(impossible.coverage.excluded.connection_too_short > 0);
});
test('UTC chronology and the 120-minute flight buffer also apply to composite feeders', async () => {
  for (const mutate of [
    legs => { legs[1].departure = '2026-12-04T08:00:00+08:00'; }, // before first train arrival in UTC
    legs => { legs[1].arrival = '2026-12-04T10:30:00+05:00'; }, // 90 minutes before WZ
  ]) {
    const result = await createJourneySearch({ source: compositeSource({ mutate }), places: placeIndex() }).search(trip());
    assert(!result.plans.some(p => p.requires_red_wings && p.status === 'verified'));
    assert(result.coverage.excluded.connection_too_short > 0);
  }
});
test('a composite post-flight station move starts after the sixty-minute buffer in local UTC offset', async () => {
  const source = transport(q => q.from === b.id || q.from === b.city_id ? envelope() : usual(q));
  source.searchChains = async q => {
    q.budget.remaining--;
    if (q.from !== b.id) return { status: 'ok', complete: true, chains: [] };
    return { status: 'ok', complete: true, chains: [{ legs: [
      segment('onward-one', 'train', 's22', 's25', `${q.date}T15:30:00+05:00`, `${q.date}T16:30:00+05:00`, { from_city_id: b.city_id }),
      segment('onward-two', 'train', 's25', 's2', `${q.date}T17:00:00+05:00`, `${q.date}T18:00:00+05:00`),
    ] }] };
  };
  // Query by the city: an airport-specific response may not substitute s22 for s20.
  const original = source.searchChains;
  source.searchChains = async q => q.from === b.city_id ? original({ ...q, from: b.id }) : (q.budget.remaining--, { status: 'ok', complete: true, chains: [] });
  const transitions = [];
  const result = await createJourneySearch({ source, places: placeIndex(), async transfer(q) {
    transitions.push(q); return segment('onward-walk', 'walk', q.from.id, q.to.id, q.notBefore, new Date(Date.parse(q.notBefore) + 15 * 60000).toISOString());
  } }).search(trip());
  const plan = result.plans.find(p => p.requires_red_wings);
  assert.equal(plan.status, 'verified'); assert.equal(plan.legs.length, 5);
  assert.equal(transitions[0].notBefore, '2026-12-04T15:00:00.000+05:00');
  assert.deepEqual(plan.connections.map(c => c.minimum_minutes), [120, 60, 0, 0]);
});
test('composite upstream failure and the two-request cap remain unknown under the total budget', async () => {
  const source = compositeSource({ error: true });
  const result = await createJourneySearch({ source, places: placeIndex() }).search(trip({ date_range: { from: '2026-12-01', to: '2027-01-15', meaning: 'departure_window' } }));
  assert.equal(result.status, 'partial'); assert.equal(result.coverage.chain_requests.used, 2);
  assert.equal(source.calls.filter(q => q.kind === 'searchChains').length, 2);
  assert(source.calls.length <= 24); assert.equal(result.coverage.complete, false);
  assert(result.missing_data.some(m => m.includes('upstream_unavailable')));
  assert(!result.plans.some(p => p.requires_red_wings && p.status === 'verified'));
});
test('a query on 11 December may prove boarding 373E on 12 December without shifting its timestamps', async () => {
  const source = transport(q => {
    if (q.from === b.id && q.to === destination.id) return q.date === '2026-12-11'
      ? envelope([onward('2026-12-12', { id: '373E', mode: 'train', number: '373Е' })]) : envelope();
    return usual(q);
  }, () => envelope([], { departures: [{ to: b.id, carrier_code: 617, carrier_iata: 'WZ', published_days: 'ежедневно' }] }));
  const result = await createJourneySearch({ source, places: placeIndex() }).search(trip({ date_range: { from: '2026-12-12', to: '2026-12-12', meaning: 'departure_window' } }));
  const plan = result.plans.find(p => p.requires_red_wings);
  assert.equal(plan.status, 'verified');
  assert.equal(plan.legs.at(-1).departure, '2026-12-12T15:00:00+05:00');
  assert.equal(plan.legs.at(-1).source_query_date, '2026-12-11');
  assert(result.coverage.actual_ground_departure_dates.includes('2026-12-12'));
});
test('adjacent source dates do not waive the actual departure window or validate another flight date', async () => {
  const before = transport(q => q.from === origin.id && q.to === a.id ? envelope([feeder('2026-12-03')]) : usual(q));
  const result = await createJourneySearch({ source: before, places: placeIndex() }).search(trip());
  assert(!result.plans.some(p => p.requires_red_wings));
  assert(result.coverage.excluded.departure_outside_window > 0);
  const wrongFlight = transport(q => q.from === a.id && q.to === b.id ? envelope([flight('2026-12-05')]) : usual(q));
  const otherDate = await createJourneySearch({ source: wrongFlight, places: placeIndex() }).search(trip());
  assert(!otherDate.plans.some(p => p.requires_red_wings));
});
test('four requests remain available for a baseline after expensive WZ surface searches', async () => {
  const otherA = { ...a, id: 's30' }, otherB = { ...b, id: 's40' }, places = placeIndex();
  const original = places.getStation;
  places.getStation = id => [otherA, otherB].find(s => s.id === id) ?? original(id);
  const source = transport(q => {
    if (q.from === origin.id && q.to === destination.id) return envelope([
      flight(q.date, { id: 'other-airline', from: otherA.id, to: otherB.id, carrier_code: 99, carrier_iata: 'XX' }),
      segment('ground-comparison', 'train', 's1', 's2', `${q.date}T06:00:00+05:00`, `${q.date}T10:00:00+05:00`, { evidence_status: 'published_pattern' }),
    ]);
    if (q.from === a.id && q.to === b.id) return envelope([flight(q.date)]);
    if (q.from === origin.id && q.to === otherA.id) return envelope([feeder(q.date, { to: otherA.id })]);
    if (q.from === otherB.id && q.to === destination.id) return envelope([onward(q.date, { from: otherB.id })]);
    return envelope();
  });
  const result = await createJourneySearch({ source, places }).search(trip({ date_range: { from: '2026-12-01', to: '2027-01-15', meaning: 'departure_window' } }));
  assert.equal(result.coverage.baseline_reserved_requests, 4);
  assert(source.calls.length <= 24);
  assert(result.coverage.unexamined_candidates > 0);
  assert(result.plans.some(p => !p.requires_red_wings && p.status === 'partial' && p.legs.every(l => l.mode !== 'plane')));
  assert(!result.plans.some(p => p.legs.length === 1 && p.gaps.length));
});
