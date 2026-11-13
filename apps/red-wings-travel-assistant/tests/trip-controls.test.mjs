import test from 'node:test';
import assert from 'node:assert/strict';
import { createTripControls } from '../src/trip-controls.mjs';
import { PlaceIndex } from '../src/place-index.mjs';
import { YandexTransportSource } from '../src/transport-sources.mjs';
import { InputError } from '../src/validation.mjs';
import { emptyTrip } from '../src/journey-trip.mjs';

const NOW = '2026-11-13T10:00:00Z';
const DATE = '2026-12-01';
const airport = (id, title, lat, lon, iata) => ({ id, title, type: 'airport', lat, lon, iata });
const dictionary = () => ({ version: 1, places: [
  { id: 'c213', title: 'Москва', region: 'Москва', lat: 55.75, lon: 37.62, stations: [
    { id: 's9601627', title: 'Выхино', city_id: 'c213', city: 'Москва', type: 'train_station', lat: 55.716388, lon: 37.816304 },
    airport('s100', 'Шереметьево', 55.97, 37.41, 'SVO'),
    airport('s101', 'Домодедово', 55.41, 37.9, 'DME'),
    airport('s102', 'Внуково', 55.60, 37.27, 'VKO'),
    airport('s103', 'Жуковский', 55.55, 38.15, 'ZIA'),
    airport('s104', 'Местный аэродром 1', 55.75, 37.63),
    airport('s105', 'Местный аэродром 2', 55.75, 37.64),
    airport('s106', 'Аэропорт далее 100 км', 57.75, 37.62, 'FAR'),
  ] },
  { id: 'c973', title: 'Сургут', region: 'Ханты-Мансийский автономный округ', lat: 61.25, lon: 73.4,
    stations: [airport('s9623563', 'Сургут', 61.34, 73.4, 'SGC')] },
  { id: 'c22661', title: 'Сургут', region: 'Самарская область', lat: null, lon: null, stations: [] },
  { id: 'c54', title: 'Екатеринбург', region: 'Свердловская область', lat: 56.84, lon: 60.6,
    stations: [airport('s9600370', 'Кольцово', 56.74, 60.8, 'SVX')] },
  { id: 'c10988', title: 'Миасс', region: 'Челябинская область', lat: 55.05, lon: 60.11, stations: [] },
] });
const row = (patch = {}) => ({ from: 's100', to: null, mode: 'plane', number: 'WZ 100',
  carrier_code: 617, carrier_iata: 'WZ', thread_uid: 'upstream-secret-uid',
  departure: `${DATE}T10:00:00+03:00`, arrival: null, destination: 'Екатеринбург', destination_query: 'Екатеринбург',
  source_url: `https://rasp.yandex.ru/station/100/?date=${DATE}`, checked_at: NOW, ...patch });
const board = (departures = [], patch = {}) => ({ status: 'ok', complete: true, departures, checked_at: NOW, ...patch });
function setup({ data = dictionary(), schedule = async query => board([row({ from: query.station })]), now = () => new Date(NOW) } = {}) {
  const calls = [];
  const places = new PlaceIndex({ data });
  const source = { async schedule(query) { calls.push(query); return schedule(query); } };
  return { controls: createTripControls({ places, source, now }), calls, places };
}
const form = (patch = {}) => ({ origin_id: 'c213', destination_id: 'c10988', date_from: DATE, ...patch });
const invalid = error => error instanceof InputError && error.statusCode === 400 && /[А-Яа-я]/u.test(error.message);

test('autocomplete searches the local dictionary once across cities, stations, regions, codes and IATA', async () => {
  const { places, calls } = setup();
  let loads = 0;
  const load = places.load.bind(places);
  places.load = (...args) => { loads++; return load(...args); };
  const controls = createTripControls({ places, source: { schedule() { throw new Error('No board on keystrokes'); } } });
  assert.equal((await controls.suggest('Мо')).places[0].id, 'c213');
  const station = (await controls.suggest('вЫхи')).places[0];
  assert.deepEqual(station, { id: 's9601627', kind: 'station', title: 'Выхино', city: 'Москва', region: 'Москва',
    node_id: 's9601627', place_id: 'c213', lat: 55.716388, lon: 37.816304 });
  assert.equal((await controls.suggest('s9601627')).places[0].id, station.id);
  assert.equal((await controls.suggest('c213')).places[0].kind, 'city');
  assert.equal((await controls.suggest('zia')).places[0].id, 's103');
  assert.equal((await controls.suggest('Сургут Самарская')).places[0].id, 'c22661');
  assert.equal((await controls.suggest('Сургут Ханты')).places[0].place_id, 'c973');
  assert.deepEqual((await controls.suggest('Ленина 109')).places, []);
  assert.equal(loads, 1); assert.equal(calls.length, 0);
});

test('autocomplete ranks exact matches first, caps at twelve and does not expose internal catalog fields', async () => {
  const data = dictionary();
  for (let i = 0; i < 20; i++) data.places.push({ id: `c${10000 + i}`, title: `Москва ${i}`, region: 'Область', stations: [] });
  const { controls } = setup({ data });
  const result = await controls.suggest('Москва');
  assert.equal(result.status, 'ok'); assert.equal(result.places.length, 12); assert.equal(result.places[0].id, 'c213');
  const airport = (await controls.suggest('Шереметьево')).places[0];
  assert.equal(airport.kind, 'airport'); assert(!Object.hasOwn(airport, 'iata')); assert(!Object.hasOwn(airport, 'scheduled_catalog_candidate'));
  for (const query of ['', 'М', 'x'.repeat(161), 'Выхино\n', 12, null]) await assert.rejects(controls.suggest(query), invalid);
});

test('unavailable dictionary stays unavailable and a later local load can recover', async () => {
  const { places } = setup();
  let failed = true;
  const controls = createTripControls({ places: { async load() { if (failed) throw new Error('offline'); return places.load(); } } });
  assert.deepEqual(await controls.suggest('Москва'), { status: 'unavailable', places: [] });
  assert.equal((await controls.flightOptions({ from: 'c213', date: DATE })).status, 'unavailable');
  await assert.rejects(controls.normalizeForm(form()), error => error instanceof InputError && error.statusCode === 503);
  failed = false;
  assert.equal((await controls.suggest('Москва')).places[0].id, 'c213');
});

test('city boards include all four Moscow airports within 100 km, with at most five dated GETs', async () => {
  const { controls, calls } = setup();
  const result = await controls.flightOptions({ from: 'c213', date: DATE });
  assert.equal(result.status, 'partial'); // Six indexed airports fit; five boards are checked.
  assert.equal(calls.length, 5);
  for (const id of ['s100', 's101', 's102', 's103']) assert(calls.some(call => call.station === id));
  assert(!calls.some(call => call.station === 's106'));
  assert(calls.every(call => call.date === DATE && call.direction === 'departure' && call.modes.join() === 'plane'));
  assert(calls.every(call => call.budget === calls[0].budget));
  assert.equal(calls[0].budget.remaining, 5); // A fake source does not spend the shared GET budget.
  assert(result.flights.every(flight => flight.arrival === null && flight.date === DATE));
});

test('concrete airport means exactly that board; rail stations, unknown IDs and invalid dates cause no requests', async () => {
  const { controls, calls } = setup();
  const result = await controls.flightOptions({ from: 's9623563', date: DATE });
  assert.equal(result.status, 'ok'); assert.deepEqual(calls.map(call => call.station), ['s9623563']);
  assert.equal(result.flights[0].origin.title, 'Сургут');
  for (const query of [null, [], { from: 's9601627', date: DATE }, { from: 's999999', date: DATE }, { from: 'SVO', date: DATE },
    { from: 'c213', date: '2026-02-30' }, { from: 'c213', date: '2026-2-01' }]) {
    await assert.rejects(controls.flightOptions(query), invalid);
  }
  assert.equal(calls.length, 1);
  const noPoint = await controls.flightOptions({ from: 'c22661', date: DATE });
  assert.equal(noPoint.status, 'unavailable'); assert.deepEqual(noPoint.flights, []); assert.equal(calls.length, 1);
});

test('carrier evidence, actual local departure date and endpoint identify selectable WZ flights', async () => {
  const { controls } = setup({ schedule: async () => board([
    row(), row(), // duplicate board records must not create duplicate options
    row({ number: 'ИН 101', carrier_iata: null }),
    row({ number: '102', carrier_code: null }),
    row({ number: 'WZ 103', carrier_code: 26, carrier_iata: 'SU' }),
    row({ number: 'WZ 104', carrier_code: null, carrier_iata: null }),
    row({ number: 'WZ 105', carrier_code: 26 }), // conflicting carrier metadata
    row({ number: 'SU 106' }),
    row({ number: 'WZ 107', departure: null }),
    row({ number: 'WZ 108', departure: '2026-12-02T00:01:00+03:00' }),
    row({ number: 'WZ 109', departure: `${DATE}T00:01:00+12:00`, arrival: `${DATE}T09:00:00+12:00` }),
    row({ number: 'WZ 110', from: 's999' }),
    row({ number: 'WZ 111', departure: '2026-12-01T25:00:00+03:00' }),
  ]) });
  const result = await controls.flightOptions({ from: 's100', date: DATE });
  assert.equal(result.status, 'partial');
  assert.deepEqual(result.flights.map(flight => flight.number).sort(), ['WZ 100', 'WZ 101', 'WZ 102', 'WZ 109']);
  const flight = result.flights.find(flight => flight.number === 'WZ 109');
  assert.equal(flight.date, DATE); assert.equal(flight.departure, `${DATE}T00:01:00+12:00`);
  assert.equal(flight.arrival, null); // A board arrival is not a destination arrival.
  assert.deepEqual(flight.destination, { id: 'c54', city: 'Екатеринбург', title: 'Екатеринбург' });
  assert(result.flights.every(flight => flight.id !== 'upstream-secret-uid' && !JSON.stringify(flight).includes('upstream-secret-uid')));
});

test('unknown destination hints remain hints and a failed board cannot become a no-flights result', async () => {
  const hint = setup({ schedule: async () => board([row({ destination: 'Неизвестный аэропорт', destination_query: null })]) });
  const result = await hint.controls.flightOptions({ from: 's100', date: DATE });
  assert.deepEqual(result.flights[0].destination, { title: 'Неизвестный аэропорт' });
  for (const schedule of [async () => board([], { status: 'key_required', complete: false }), async () => { throw new Error('offline'); }]) {
    const { controls, calls } = setup({ schedule });
    const response = await controls.flightOptions({ from: 's100', date: DATE });
    assert.equal(response.status, 'unavailable'); assert.deepEqual(response.flights, []); assert(response.message); assert.equal(calls.length, 1);
  }
  const empty = setup({ schedule: async () => board([]) });
  assert.equal((await empty.controls.flightOptions({ from: 's100', date: DATE })).status, 'ok');
  const incomplete = setup({ schedule: async () => board([], { complete: false }) });
  assert.equal((await incomplete.controls.flightOptions({ from: 's100', date: DATE })).status, 'partial');
});

test('normalization creates the complete trip, retaining station and parent city separately', async () => {
  const { controls, calls } = setup();
  const trip = await controls.normalizeForm(form({ origin_id: 's9601627', destination_id: 's9600370',
    date_to: '2027-01-15', origin_address: '  Ленина, 109  ', destination_address: '' }));
  assert.deepEqual(trip, { ...emptyTrip(),
    origin: { city: 'Москва', region: 'Москва', place_id: 'c213', node_id: 's9601627', address: 'Ленина, 109' },
    destination: { city: 'Екатеринбург', region: 'Свердловская область', place_id: 'c54', node_id: 's9600370', address: null },
    date_range: { from: DATE, to: '2027-01-15', meaning: 'departure_window' },
  });
  const single = await controls.normalizeForm(form());
  assert.equal(single.origin.node_id, null); assert.equal(single.origin.place_id, 'c213');
  assert.deepEqual(single.date_range, { from: DATE, to: DATE, meaning: 'departure_window' });
  assert.equal(single.selected_flight, null); assert.equal(single.requires_red_wings, true); assert.equal(calls.length, 0);
});

test('form accepts a long departure window through 366 days, not the legacy seven-day limit', async () => {
  const { controls } = setup();
  const trip = await controls.normalizeForm(form({ date_from: '2026-11-13', date_to: '2027-11-13' }));
  assert.equal(trip.date_range.to, '2027-11-13');
  for (const patch of [{ date_from: '2026-11-13', date_to: '2027-11-14' }, { date_to: '2027-11-15' },
    { date_to: '2026-11-30' }, { date_from: '2026-11-12' }, { date_from: '2027-02-29' },
    { date_to: null }, { date_to: '' }, { date_from: `${DATE}T00:00:00Z` }]) {
    await assert.rejects(controls.normalizeForm(form(patch)), invalid);
  }
});

test('form rejects unknown fields, arbitrary station/city/flight IDs, invalid addresses and non-object input', async () => {
  const { controls } = setup();
  for (const body of [null, [], new Date(), 'trip', form({ origin_id: 'Москва' }), form({ destination_id: 'c999999' }),
    form({ origin_id: 's999999' }), form({ flight_option_id: 'upstream-secret-uid' }), form({ flight_option_id: {} }),
    form({ selected_flight: { number: 'WZ 1', date: DATE } }), form({ network_mode: 'scenario_2027_2028' }),
    form({ origin_address: 'x'.repeat(241) }), form({ destination_address: 'Адрес\nдома' }),
    form({ origin_address: 'Адрес\u0085дома' }), form({ origin_address: 'Адрес\u202eдома' }), form({ origin_address: null })]) {
    await assert.rejects(controls.normalizeForm(body), invalid);
  }
  assert.equal((await controls.normalizeForm(form({ origin_address: 'x'.repeat(240) }))).origin.address.length, 240);
});

test('selected flight comes only from the server map, survives client mutation and must fit the departure window', async () => {
  const { controls } = setup();
  const { flights } = await controls.flightOptions({ from: 's100', date: DATE });
  const id = flights[0].id;
  flights[0].number = 'WZ 9999'; flights[0].date = '2027-01-01';
  // The flight airport can differ from the overall journey origin (a ground feeder).
  const trip = await controls.normalizeForm(form({ origin_id: 'c973', flight_option_id: id, date_to: '2027-01-15' }));
  assert.deepEqual(trip.selected_flight, { number: 'WZ 100', date: DATE, leg_id: null });
  await assert.rejects(controls.normalizeForm(form({ date_from: '2026-12-02', flight_option_id: id })), invalid);
  const other = setup();
  await assert.rejects(other.controls.normalizeForm(form({ flight_option_id: id })), invalid);
});

test('optional wishes are validated without adding them to Trip or changing the input body', async () => {
  const { controls } = setup();
  const plain = await controls.normalizeForm(form());
  for (const wishes of ['', 'Без такси\nМожно электричкой\tс багажом', 'я'.repeat(2000)]) {
    const body = form({ wishes }), before = structuredClone(body);
    const trip = await controls.normalizeForm(body);
    assert.deepEqual(trip, plain); assert.deepEqual(body, before);
    assert(!Object.hasOwn(trip, 'wishes'));
  }
  for (const wishes of [null, 12, {}, 'я'.repeat(2001), 'Текст\u0000', 'Текст\r', 'Текст\u001b', 'Текст\u007f', 'Текст\u0085', 'Текст\u202e']) {
    await assert.rejects(controls.normalizeForm(form({ wishes })), invalid);
  }
});

test('flight option IDs expire at ten minutes and the map evicts beyond 500 entries', async () => {
  let time = Date.parse(NOW);
  const { controls } = setup({ now: () => new Date(time), schedule: async query => board(Array.from({ length: 100 }, (_, i) => row({ from: query.station, number: `WZ ${i + 1}` }))) });
  const first = (await controls.flightOptions({ from: 's100', date: DATE })).flights[0].id;
  time += 599999;
  assert((await controls.normalizeForm(form({ flight_option_id: first }))).selected_flight);
  time++;
  await assert.rejects(controls.normalizeForm(form({ flight_option_id: first })), invalid);
  const batches = [];
  for (let i = 0; i < 6; i++) batches.push((await controls.flightOptions({ from: 's100', date: DATE })).flights);
  await assert.rejects(controls.normalizeForm(form({ flight_option_id: batches[0][0].id })), invalid);
  assert((await controls.normalizeForm(form({ flight_option_id: batches[1][0].id }))).selected_flight);
  assert((await controls.normalizeForm(form({ flight_option_id: batches[5][99].id }))).selected_flight);
});

test('cancellation propagates before lookup and between boards, without more requests', async () => {
  const stopped = new AbortController(); stopped.abort();
  const initial = setup();
  for (const run of [() => initial.controls.suggest('Москва', { signal: stopped.signal }),
    () => initial.controls.flightOptions({ from: 'c213', date: DATE }, { signal: stopped.signal }),
    () => initial.controls.normalizeForm(form(), { signal: stopped.signal })]) await assert.rejects(run(), { name: 'AbortError' });
  assert.equal(initial.calls.length, 0);
  const controller = new AbortController();
  const running = setup({ schedule: async () => { controller.abort(); return board([]); } });
  await assert.rejects(running.controls.flightOptions({ from: 'c213', date: DATE }, { signal: controller.signal }), { name: 'AbortError' });
  assert.equal(running.calls.length, 1);
});

test('real connector schema is consumed offline with five bounded authenticated GETs and no manufactured arrival/date', async () => {
  const requests = [];
  const source = new YandexTransportSource({ yandexKey: 'offline-fixture-only' }, { now: () => new Date(NOW), fetchImpl: async (url, options) => {
    requests.push(url);
    assert.equal(options.method, 'GET'); assert.equal(options.headers.Authorization, 'offline-fixture-only');
    assert.equal(url.searchParams.get('date'), DATE); assert.equal(url.searchParams.get('event'), 'departure');
    assert.equal(url.searchParams.get('transport_types'), 'plane'); assert(!url.searchParams.has('apikey'));
    return new Response(JSON.stringify({ station: { code: url.searchParams.get('station'), title: 'Аэропорт' },
      pagination: { offset: 0, total: 2 }, schedule: [
        { departure: `${DATE}T12:00:00+03:00`, arrival: null, thread: { uid: 'not-a-public-option', number: 'WZ 9',
          transport_type: 'plane', short_title: 'Москва — Екатеринбург', carrier: { code: 617, codes: { iata: 'WZ' } } } },
        { departure: '2026-12-02T12:00:00+03:00', thread: { number: 'WZ 10', transport_type: 'plane', carrier: { code: 617 } } },
      ] }));
  } });
  const places = new PlaceIndex({ data: dictionary() });
  const controls = createTripControls({ places, source, now: () => new Date(NOW) });
  const result = await controls.flightOptions({ from: 'c213', date: DATE });
  assert.equal(requests.length, 5); assert.equal(result.status, 'partial'); assert.equal(result.flights.length, 5);
  assert(result.flights.every(flight => flight.number === 'WZ 9' && flight.date === DATE && flight.arrival === null));
});
