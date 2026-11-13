import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeJourneyGraph, validateCorridor, findJourneyOptions } from '../src/journey-graph.mjs';
import { applyTripPatch, emptyTrip, departureRange } from '../src/journey-trip.mjs';
import { fixtureGraph, fixtureTrip, fixtureNow, tripPatch } from './journey-fixtures.test.mjs';

test('46-day window persists; ambiguous meaning blocks search; return date is not discarded', () => {
  let trip = applyTripPatch(emptyTrip(), { ...tripPatch, date_range: { ...tripPatch.date_range, meaning: 'unknown' } }, { now: fixtureNow });
  const graph = normalizeJourneyGraph(fixtureGraph());
  assert.deepEqual(findJourneyOptions(graph, trip).missing_fields, ['date_range.meaning']);
  trip = applyTripPatch(trip, { date_range: { meaning: 'departure_window' } }, { now: fixtureNow });
  assert.equal(trip.date_range.to, '2027-01-15');
  assert.equal(departureRange(trip).to, '2027-01-15');
  assert(findJourneyOptions(graph, trip).plans.length);
  const returning = applyTripPatch(trip, { date_range: { meaning: 'outbound_return' } }, { now: fixtureNow });
  assert.equal(returning.date_range.to, '2027-01-15');
  assert.equal(departureRange(returning).to, '2026-12-01');
  assert.match(findJourneyOptions(graph, returning).missing_data.join(' '), /Обратный путь.*2027-01-15/);
});

test('dated connected sourced chain verifies; exact duration and party fare include every leg', () => {
  const result = validateCorridor(normalizeJourneyGraph(fixtureGraph()), ['bus', 'rw', 'coach'], fixtureTrip());
  assert.equal(result.status, 'verified');
  assert.equal(result.total_duration_minutes, 540);
  assert.equal(result.total_price, 600);
  assert.equal(result.connections[0].minimum_minutes, 120);
  assert.equal(result.connections[0].available_minutes, 120);
  assert.equal(result.connections[1].minimum_minutes, 60);
  const wrongTrip = fixtureTrip(); wrongTrip.destination.city = 'Другой город';
  assert.equal(validateCorridor(normalizeJourneyGraph(fixtureGraph()), ['bus', 'rw', 'coach'], wrongTrip).rejected, 'trip_endpoints_mismatch');
});

test('missing transfer is not zero, short transfer rejects, missing arrival remains partial', () => {
  const raw = fixtureGraph(); raw.nodes.find(n => n.id === 'hma').min_transfer_minutes = null;
  raw.legs.find(l => l.id === 'rw').mode = 'train';
  let plan = validateCorridor(normalizeJourneyGraph(raw), ['bus', 'rw', 'coach'], fixtureTrip(), { kind: 'baseline' });
  assert.equal(plan.status, 'partial'); assert.equal(plan.total_duration_minutes, null);
  assert.equal(plan.connections[0].minimum_minutes, null);
  raw.legs.find(l => l.id === 'rw').mode = 'plane';
  raw.nodes.find(n => n.id === 'hma').min_transfer_minutes = 150;
  assert.equal(validateCorridor(normalizeJourneyGraph(raw), ['bus', 'rw', 'coach'], fixtureTrip()).rejected, 'connection_too_short');
  raw.nodes.find(n => n.id === 'hma').min_transfer_minutes = 45;
  raw.legs.find(l => l.id === 'coach').arrival = null;
  plan = validateCorridor(normalizeJourneyGraph(raw), ['bus', 'rw', 'coach'], fixtureTrip());
  assert.equal(plan.status, 'partial'); assert.equal(plan.total_duration_minutes, null);
});

test('disconnected corridor exposes missing physical transition, with no invented leg', () => {
  const raw = fixtureGraph();
  raw.nodes.push({ id: 'other-station', city: 'Екатеринбург', type: 'station', title: 'Another actual test station' });
  raw.legs.find(l => l.id === 'coach').from = 'other-station';
  const p = validateCorridor(normalizeJourneyGraph(raw), ['bus', 'rw', 'coach'], fixtureTrip());
  assert.equal(p.status, 'partial'); assert.equal(p.legs.length, 3);
  assert.equal(p.total_duration_minutes, null); assert.equal(p.total_price, null);
  assert.match(p.warnings.join(' '), /Нет проверенного перехода/);
});

test('address gap, unknown price unit and baggage evidence cannot become a complete journey', () => {
  const trip = fixtureTrip(); trip.origin.address = 'Другой адрес'; trip.baggage = 'чемодан 20 кг';
  const raw = fixtureGraph(); raw.legs[1].price_basis = null;
  const p = validateCorridor(normalizeJourneyGraph(raw), ['bus', 'rw', 'coach'], trip);
  assert.equal(p.status, 'partial'); assert.equal(p.total_duration_minutes, null); assert.equal(p.total_price, null);
  assert.match(p.warnings.join(' '), /Другой адрес/); assert.match(p.warnings.join(' '), /багажа/);
});

test('fixed WZ and no-taxi/mode constraints persist through later changes', () => {
  let trip = applyTripPatch(fixtureTrip(), { selected_flight: { number: 'WZ 90001', date: '2026-12-01' }, constraints: { allow_taxi: false } }, { now: fixtureNow });
  trip = applyTripPatch(trip, { baggage: 'рюкзак' }, { now: fixtureNow });
  assert.equal(trip.selected_flight.number, 'WZ 90001'); assert.equal(trip.constraints.allow_taxi, false);
  const plans = findJourneyOptions(normalizeJourneyGraph(fixtureGraph()), trip).plans;
  assert(plans.some(p => p.requires_red_wings));
  assert(plans.every(p => !p.legs.some(l => l.mode === 'taxi')));
  assert(plans.filter(p => p.requires_red_wings).every(p => p.legs.some(l => l.number === 'WZ 90001')));
  assert.throws(() => applyTripPatch(trip, { date_range: { from: '2026-12-02' } }, { now: fixtureNow }), /не включает сохранённый рейс/);
  const later = applyTripPatch(trip, { constraints: { departure_after: '2026-12-01T10:00:00+05:00' } }, { now: fixtureNow });
  assert.equal(findJourneyOptions(normalizeJourneyGraph(fixtureGraph()), later).plans.filter(p => p.requires_red_wings).length, 0);
});

test('no marketing-only RW, no city placeholders, unsafe source URLs and backwards times are rejected', () => {
  const raw = fixtureGraph();
  raw.legs.find(l => l.id === 'rw').carrier_code = 999;
  assert.equal(validateCorridor(normalizeJourneyGraph(raw), ['bus', 'rw', 'coach'], fixtureTrip()).rejected, 'no_confirmed_rw_segment');
  raw.nodes.find(n => n.id === 'door').type = 'city';
  let graph = normalizeJourneyGraph(raw);
  assert(!graph.legs.has('bus')); assert(!graph.legs.has('baseline'));
  raw.legs.find(l => l.id === 'rw').source_url = 'file:///etc/passwd';
  raw.legs.find(l => l.id === 'coach').arrival = '2026-12-01T10:00:00+05:00';
  graph = normalizeJourneyGraph(raw);
  assert(!graph.legs.has('rw')); assert(!graph.legs.has('coach'));
});

test('empty graph gives precise missing data, no false HMA airline absence, no demo routes', () => {
  const result = findJourneyOptions(normalizeJourneyGraph(), fixtureTrip());
  assert.deepEqual(result.plans, []); assert.equal(result.status, 'partial');
  assert.match(result.missing_data.join(' '), /Нет узлов\/источников для города отправления/);
  assert.match(result.missing_data.join(' '), /не доказательство отсутствия RW/);
});

test('snapshot normalization preserves real observed times and sources without adding ground legs', () => {
  const raw = fixtureGraph();
  const graph = normalizeJourneyGraph({ nodes: raw.nodes }, { airports: [], checked_at: null,
    sources: [{ id: 'test', name: 'Test observation', url: 'https://fixture.invalid/snapshot' }],
    flights: [{ id: 'observed-test', origin: 's-test-hma', destination: 's-test-svx', departure: '2026-12-01T09:00:00+05:00',
      arrival: null, flight_number: 'WZ 90001', carrier_code: 617, carrier_iata: 'WZ', provenance: [{ source_id: 'test' }] }] });
  assert.equal(graph.legs.size, 1); const leg = [...graph.legs.values()][0];
  assert.equal(leg.arrival, null); assert.equal(leg.data_mode, 'snapshot'); assert.equal(leg.from, 'hma');
  assert.equal(leg.source_url, 'https://fixture.invalid/snapshot');
});

test('year horizon and real calendar validation are independent of seven-day query budget', () => {
  assert.doesNotThrow(() => applyTripPatch(emptyTrip(), { date_range: { from: '2026-12-01', to: '2027-10-30' } }, { now: fixtureNow }));
  assert.throws(() => applyTripPatch(emptyTrip(), { date_range: { from: '2026-12-01', to: '2028-01-01' } }, { now: fixtureNow }), /Поддерживается планирование/);
  assert.throws(() => applyTripPatch(emptyTrip(), { date_range: { from: '2027-02-30', to: '2027-03-02' } }, { now: fixtureNow }), /существующие даты/);
});

test('scenario 2028 has a separate horizon and cannot absorb current-network flights', () => {
  const trip = applyTripPatch(emptyTrip(), { ...tripPatch, network_mode: 'scenario_2027_2028', ground_preference: 'smart_transfer',
    date_range: { from: '2028-07-01', to: '2028-07-31', meaning: 'departure_window' } }, { now: fixtureNow });
  assert.equal(trip.network_mode, 'scenario_2027_2028'); assert.equal(trip.date_range.to, '2028-07-31');
  const graph = normalizeJourneyGraph(fixtureGraph());
  assert.equal(validateCorridor(graph, ['bus', 'rw', 'coach'], trip).rejected, 'network_mode_mismatch');
  assert.throws(() => applyTripPatch(trip, { network_mode: 'current' }, { now: fixtureNow }), /Поддерживается планирование/);
});

test('120/60 minute product minima cannot be weakened by smaller source buffers', () => {
  const raw = fixtureGraph(); raw.nodes.forEach(n => { n.min_transfer_minutes = 0; });
  raw.legs.find(l => l.id === 'bus').arrival = '2026-12-01T07:01:00+05:00';
  assert.equal(validateCorridor(normalizeJourneyGraph(raw), ['bus', 'rw', 'coach'], fixtureTrip()).rejected, 'connection_too_short');
  raw.legs.find(l => l.id === 'bus').arrival = '2026-12-01T07:00:00+05:00';
  raw.legs.find(l => l.id === 'coach').departure = '2026-12-01T11:59:00+05:00';
  assert.equal(validateCorridor(normalizeJourneyGraph(raw), ['bus', 'rw', 'coach'], fixtureTrip()).rejected, 'connection_too_short');
});

test('waiting more than five hours and overnight transfers are visible, using UTC offsets for gaps', () => {
  const raw = fixtureGraph();
  raw.legs.find(l => l.id === 'coach').departure = '2026-12-02T06:00:00+05:00';
  raw.legs.find(l => l.id === 'coach').arrival = '2026-12-02T09:00:00+05:00';
  const p = validateCorridor(normalizeJourneyGraph(raw), ['bus', 'rw', 'coach'], fixtureTrip());
  assert.equal(p.connections[1].available_minutes, 1140); assert(p.connections[1].long_wait); assert(p.connections[1].next_day);
  assert.match(p.warnings.join(' '), /превышает 5 часов/); assert.match(p.warnings.join(' '), /следующие сутки/);
  const constrained = fixtureTrip(); constrained.constraints.allow_overnight = false;
  assert.equal(validateCorridor(normalizeJourneyGraph(raw), ['bus', 'rw', 'coach'], constrained).rejected, 'overnight_connection_excluded');
});
