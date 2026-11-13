import test from 'node:test';
import assert from 'node:assert/strict';
import { PlaceIndex, compactRussianPlaces, geographicDistance } from '../src/place-index.mjs';

const data = { countries: [{ title: 'Россия', regions: [
  { title: 'Ханты-Мансийский автономный округ', settlements: [{ title: 'Сургут', codes: { yandex_code: 'c973' }, stations: [
    { title: 'Сургут', station_type: 'airport', transport_type: 'plane', latitude: 61.34, longitude: 73.4, codes: { yandex_code: 's9623563' } },
  ] }] },
  { title: 'Самарская область', settlements: [{ title: 'Сургут', codes: { yandex_code: 'c22661' }, stations: [] }] },
] }] };
test('duplicate Russian city names remain ambiguous; region can resolve the actual airport', async () => {
  const places = new PlaceIndex({ data });
  assert.equal((await places.resolve('Сургут')).status, 'ambiguous');
  const actual = await places.resolve('Сургут, Ханты-Мансийский автономный округ');
  assert.equal(actual.status, 'ok');
  assert.equal(actual.places[0].id, 'c973');
  assert.equal((await places.nearbyAirports(actual.places[0]))[0].id, 's9623563');
  assert.equal((await places.getStation('s9623563')).city_id, 'c973');
});
test('missing coordinates do not create zero distance or nearby-airport evidence', async () => {
  const places = new PlaceIndex({ data });
  assert.deepEqual(await places.nearbyAirports((await places.resolve('c22661')).places[0]), []);
  assert.equal(geographicDistance({ lat: null, lon: null }, { lat: 60, lon: 70 }), Infinity);
  assert.equal(compactRussianPlaces(data, '2026-11-13').places.length, 2);
});
test('station lookup preserves a concrete origin within a parent city', async () => {
  const places = new PlaceIndex({ data: { version: 1, places: [{ id: 'c213', title: 'Москва', region: 'Москва', lat: 55.7, lon: 37.6,
    stations: [{ id: 's9601627', title: 'Выхино', city_id: 'c213', lat: 55.716388, lon: 37.816304, type: 'train_station' }] }] } });
  const result = await places.resolve('Выхино');
  assert.equal(result.status, 'ok'); assert.equal(result.places[0].id, 'c213');
  assert.equal(result.places[0].suggested_node_id, 's9601627');
  assert.equal(result.places[0].lon, 37.816304);
});
