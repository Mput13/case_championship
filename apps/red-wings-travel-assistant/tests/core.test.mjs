import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { validateRequest, datedTime, flightNumber, InputError } from '../src/validation.mjs';
import { loadSnapshot, SnapshotSchedules, LiveSchedules } from '../src/schedules.mjs';
import { planTrip, getExamples } from '../src/planner.mjs';
import { loadConfig } from '../src/config.mjs';
import { allowedLink, navigationLink } from '../src/links.mjs';

const snapshot = await loadSnapshot();
const config = loadConfig({});
const request = { mode: 'trip', origin: 'Самара', destination: 'Екатеринбург', date_from: '2026-12-08', date_to: '2026-12-08', preference: 'balanced' };
const plan = (overrides = {}, options = {}) => planTrip({ ...request, ...overrides }, { snapshot, config, schedules: new SnapshotSchedules(snapshot), ...options });

test('strict calendar dates, 7-day inclusive span, required flight fields and bounded strings', () => {
  assert.equal(validateRequest({ ...request, date_to: '2026-12-14' }).date_to, '2026-12-14');
  for (const patch of [
    { date_to: '2026-12-15' }, { date_to: '2026-12-07' }, { date_from: '2026-02-30' },
    { date_from: '2026-2-08' }, { date_from: '2026-12-08T00:00:00Z' }, { origin: 'a'.repeat(101) },
    { message: 'x'.repeat(1001) }, { preference: 'cheapest' }, { mode: 'flight' },
    { mode: 'flight', flight_number: 'SU 123', flight_date: '2026-12-08' },
    { mode: 'flight', flight_number: 'WZ 1034', flight_date: '2026-12-09' },
    { origin: 'Екатеринбург' }, { origin: { code: 'KUF' } },
  ]) assert.throws(() => validateRequest({ ...request, ...patch }), InputError);
  assert.equal(flightNumber('ИН-1034'), 'WZ 1034');
  assert.equal(flightNumber('WZ 1034; echo pwn'), null);
  assert.equal(datedTime('2026-12-08T08:00:00'), null);
  assert.equal(datedTime('2026-12-08T24:00:00Z'), null);
  assert.equal(datedTime('2026-02-30T08:00:00+04:00'), null);
});

test('snapshot is dated, hash-pinned, bounded and provenance resolves to raw receipts', async () => {
  assert.equal(snapshot.data_mode, 'snapshot');
  assert.equal(snapshot.checked_at, null);
  assert.equal(snapshot.airports.length, 20);
  assert.equal(snapshot.flights.length, 43);
  assert.equal(snapshot.flights.filter(f => f.arrival).length, 3);
  const sources = new Map();
  for (const source of snapshot.sources) {
    const raw = await readFile(new URL(`../../../${source.path}`, import.meta.url));
    assert.equal(createHash('sha256').update(raw).digest('hex'), source.sha256);
    sources.set(source.id, JSON.parse(raw));
  }
  for (const flight of snapshot.flights) {
    assert.equal(flight.price, null);
    assert.equal(flight.carrier_code, 617);
    assert.equal(flight.carrier_iata, 'WZ');
    for (const p of flight.provenance) {
      const row = p.pointer.split('/').filter(Boolean).reduce((v, key) => v[key], sources.get(p.source_id)[p.source_key]);
      assert.equal(row.departure, flight.departure);
      assert.equal(flightNumber(row.thread.number), flight.flight_number);
      if (p.source_id === 'search') assert.equal(row.arrival, flight.arrival);
    }
  }
});

test('actual Samara flight preserves offsets and 100-minute airborne time, total stays unknown', async () => {
  const result = await plan();
  assert.equal(result.status, 'ok');
  assert.equal(result.data_mode, 'snapshot');
  assert.equal(result.variants.length, 1);
  const v = result.variants[0], plane = v.legs[1];
  assert.equal(plane.departure, '2026-12-08T08:00:00+04:00');
  assert.equal(plane.arrival, '2026-12-08T10:40:00+05:00');
  assert.equal(plane.duration_minutes, 100);
  assert.equal(v.duration_minutes, null);
  assert.equal(v.total_price, null);
  assert.equal(v.departure, null);
  for (const leg of [v.legs[0], v.legs[2]]) {
    assert.equal(leg.status, 'suggestion');
    assert.equal(leg.departure, null);
    assert.equal(leg.arrival, null);
    assert.equal(leg.price, null);
    assert.equal(leg.carrier, null);
  }
});

test('missing arrival remains null; no price zero or computed connection', async () => {
  const result = await plan({ origin: 'Барнаул', date_from: '2026-12-11', date_to: '2026-12-11' });
  assert.equal(result.status, 'ok');
  assert.equal(result.variants[0].legs[1].arrival, null);
  assert.equal(result.variants[0].legs[1].duration_minutes, null);
  assert.equal(result.variants[0].total_price, null);
});

test('covered absence, uncovered dates/cities and partial pagination have different outcomes', async () => {
  assert.equal((await plan({ origin: 'Казань', destination: 'Уфа' })).status, 'no_routes');
  assert.equal((await plan({ date_from: '2026-12-09', date_to: '2026-12-09' })).status, 'needs_data');
  assert.equal((await plan({ origin: 'Москва' })).status, 'needs_data');
  assert.equal((await plan({ origin: 'Санкт-Петербург', destination: 'Самара', date_from: '2026-12-11', date_to: '2026-12-11' })).status, 'needs_data');
  const partial = await plan({ date_to: '2026-12-11' });
  assert.equal(partial.status, 'ok');
  assert.equal(partial.variants.length, 2);
  assert.match(partial.coverage_note, /2026-12-09, 2026-12-10/);
  assert(partial.variants.every(v => v.warnings.some(w => w.includes('часть поиска'))));
});

test('flight mode validates exact date and source-carrier identity, never trusts WZ prefix alone', async () => {
  const result = await plan({ mode: 'flight', flight_number: 'ИН 1034', flight_date: '2026-12-08' });
  assert.equal(result.status, 'ok');
  assert.equal(result.variants[0].legs[1].flight_number, 'WZ 1034');
  assert.equal((await plan({ mode: 'flight', flight_number: 'WZ 9999', flight_date: '2026-12-08' })).status, 'no_routes');
  const forged = structuredClone(snapshot);
  forged.flights = forged.flights.map(f => ({ ...f, carrier_code: 26 }));
  assert.equal((await plan({}, { schedules: new SnapshotSchedules(forged) })).variants.length, 0);
});

test('every example produces a source-backed variant; source URLs and navigation are allowlisted', async () => {
  const examples = getExamples(snapshot);
  assert(examples.examples.length >= 4);
  for (const example of examples.examples) {
    const result = await plan(example.request);
    assert.equal(result.status, 'ok', example.label);
    for (const variant of result.variants) for (const leg of variant.legs) for (const link of leg.links) assert.equal(allowedLink(link.url), link.url);
  }
  assert.throws(() => allowedLink('https://flyredwings.com.evil.example/'));
  assert.throws(() => allowedLink('javascript:alert(1)'));
  assert.equal(new URL(navigationLink('Самара & #', 'аэропорт')).hostname, 'yandex.ru');
});

test('live mode without key returns needs_data/unavailable and never uses snapshot', async () => {
  const schedules = new LiveSchedules(loadConfig({ SCHEDULE_MODE: 'live' }), { fetchImpl: () => { throw new Error('Must not call'); } });
  const result = await plan({}, { schedules });
  assert.equal(result.status, 'needs_data');
  assert.equal(result.data_mode, 'unavailable');
  assert.equal(result.variants.length, 0);
});

test('live connector error is an error, never no_routes or snapshot success', async () => {
  const schedules = new LiveSchedules(loadConfig({ SCHEDULE_MODE: 'live', YANDEX_RASP_API_KEY: 'test-secret' }), {
    now: () => new Date('2026-11-13T00:00:00Z'), fetchImpl: async () => new Response('{}', { status: 401 }),
  });
  const result = await plan({}, { schedules });
  assert.equal(result.status, 'error');
  assert.equal(result.error_code, 'unauthorized');
  assert.equal(result.data_mode, 'unavailable');
  assert.equal(result.variants.length, 0);
  assert(!JSON.stringify(result).includes('test-secret'));
});

test('fastest preference never claims a whole-trip ranking from incomplete ground data', async () => {
  const result = await plan({ preference: 'fastest' });
  assert(result.variants[0].warnings.some(w => w.includes('Сравнение общей длительности недоступно')));
});

test('agent failure does not remove a confirmed schedule or become connector failure', async () => {
  const result = await plan({}, { agent: { explain: async () => { throw new Error('provider failure'); } } });
  assert.equal(result.status, 'ok');
  assert.equal(result.variants[0].legs[1].flight_number, 'WZ 1034');
  assert.equal(result.assistant.status, 'error');
});
