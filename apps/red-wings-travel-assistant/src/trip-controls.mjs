import { randomUUID } from 'node:crypto';
import { geographicDistance } from './place-index.mjs';
import { emptyTrip, applyTripPatch } from './journey-trip.mjs';
import { InputError, isoDate, datedTime, flightNumber } from './validation.mjs';

const DAY = 86400000;
const OPTION_TTL = 10 * 60 * 1000;
const OPTION_LIMIT = 500;
const code = value => typeof value === 'string' && /^[cs]\d{1,12}$/u.test(value);
const controls = /[\p{Cc}\p{Cf}]/u;
const text = value => typeof value === 'string' ? value.trim() : '';
const key = value => text(value).toLocaleLowerCase('ru').replaceAll('ё', 'е')
  .replace(/[—–]/gu, '-').replace(/[\s,()]+/gu, ' ').trim();
const abort = signal => signal?.throwIfAborted();
const fields = new Set(['origin_id', 'destination_id', 'date_from', 'date_to', 'flight_option_id', 'origin_address', 'destination_address', 'wishes']);

function inputCode(value) {
  if (!code(value)) throw new InputError('Выберите город, станцию или аэропорт из подсказок.');
  return value;
}
function address(value) {
  if (value === undefined || value === '') return null;
  if (typeof value !== 'string' || value.length > 240 || controls.test(value)) {
    throw new InputError('Адрес должен содержать не более 240 символов без управляющих знаков.');
  }
  return value.trim() || null;
}
function dateWindow(from, to, now) {
  if (!isoDate(from) || !isoDate(to)) throw new InputError('Укажите существующие даты в формате ГГГГ-ММ-ДД.');
  if (from > to) throw new InputError('Последняя дата выезда должна быть не раньше первой.');
  if ((Date.parse(to) - Date.parse(from)) / DAY + 1 > 366) throw new InputError('Окно выезда может содержать не более 366 календарных дней.');
  const today = now.toISOString().slice(0, 10);
  const horizon = new Date(now.getTime() + 366 * DAY).toISOString().slice(0, 10);
  if (from < today || to > horizon) throw new InputError(`Поддерживается планирование с ${today} до ${horizon}.`);
}
function coordinates(node) {
  return {
    ...(Number.isFinite(node.lat) && Math.abs(node.lat) <= 90 ? { lat: node.lat } : {}),
    ...(Number.isFinite(node.lon) && Math.abs(node.lon) <= 180 ? { lon: node.lon } : {}),
  };
}
function score(entry, query) {
  const title = key(entry.title), iata = key(entry.iata);
  if (entry.id === query || iata === query || title === query) return 0;
  if (title.startsWith(query)) return 1;
  if (title.split(/[\s-]+/u).some(word => word.startsWith(query))) return 2;
  if (title.includes(query)) return 3;
  const context = key(`${entry.title} ${entry.city} ${entry.region} ${entry.iata ?? ''} ${entry.id}`);
  return query.split(' ').every(word => context.includes(word)) ? 4 : Infinity;
}
function redWings(row) {
  const carrier = row.carrier_code == null ? null : Number(row.carrier_code);
  const iata = text(row.carrier_iata).toUpperCase();
  return (carrier === 617 || iata === 'WZ') && (carrier === null || carrier === 617) && (!iata || iata === 'WZ');
}
function numberFrom(row) {
  return flightNumber(row.number) ?? (/^\d{1,5}$/u.test(row.number ?? '') ? flightNumber(`WZ ${row.number}`) : null);
}

/** Local place lookup and bounded, dated airport boards; no model or geocoder. */
export function createTripControls({ places, source, now = () => new Date() }) {
  let loading;
  const options = new Map();

  async function index(signal) {
    abort(signal);
    loading ??= (async () => {
      const data = await places.load({ signal });
      const entries = [], byId = new Map(), citiesByTitle = new Map();
      for (const city of data.places) {
        if (!/^c\d{1,12}$/u.test(city.id) || !text(city.title)) continue;
        const entry = { id: city.id, kind: 'city', title: city.title, city: city.title,
          region: city.region ?? '', place_id: city.id, ...coordinates(city) };
        entries.push(entry); byId.set(entry.id, entry);
        const title = key(entry.title);
        citiesByTitle.set(title, citiesByTitle.has(title) ? null : entry);
        for (const station of city.stations ?? []) {
          if (!/^s\d{1,12}$/u.test(station.id) || !text(station.title) || byId.has(station.id)) continue;
          const node = { id: station.id, kind: station.type === 'airport' || station.station_type === 'airport' ? 'airport' : 'station',
            title: station.title, city: city.title, region: city.region ?? '', node_id: station.id,
            place_id: city.id, ...coordinates(station), iata: station.iata,
            scheduled_catalog_candidate: station.scheduled_catalog_candidate };
          entries.push(node); byId.set(node.id, node);
        }
      }
      return { entries, byId, citiesByTitle };
    })().catch(error => { loading = undefined; throw error; });
    const result = await loading;
    abort(signal);
    return result;
  }
  const publicPlace = ({ iata, scheduled_catalog_candidate, ...entry }) => ({ ...entry });
  function prune(at) {
    for (const [id, entry] of options) if (entry.expires <= at) options.delete(id);
    while (options.size > OPTION_LIMIT) options.delete(options.keys().next().value);
  }
  async function lookup(id, data, signal) {
    const entry = data.byId.get(id);
    if (!entry || (id.startsWith('s') && !(await places.getStation(id, { signal })))) {
      throw new InputError('Выбранное место отсутствует в справочнике. Выберите его из подсказок заново.');
    }
    abort(signal);
    return entry;
  }

  async function suggest(query, { signal } = {}) {
    if (typeof query !== 'string' || query.length > 160 || query.trim().length < 2 || controls.test(query)) {
      throw new InputError('Для поиска места введите от 2 до 160 символов без управляющих знаков.');
    }
    let data;
    try { data = await index(signal); }
    catch (error) { abort(signal); return { status: 'unavailable', places: [] }; }
    const q = key(query);
    const found = data.entries.map(entry => ({ entry, rank: score(entry, q) })).filter(item => Number.isFinite(item.rank))
      .sort((a, b) => a.rank - b.rank || (a.entry.kind === 'city' ? 0 : 1) - (b.entry.kind === 'city' ? 0 : 1)
        || a.entry.title.localeCompare(b.entry.title, 'ru') || a.entry.id.localeCompare(b.entry.id))
      .slice(0, 12).map(item => publicPlace(item.entry));
    return { status: 'ok', places: found };
  }

  async function flightOptions(query, { signal } = {}) {
    if (!query || typeof query !== 'object' || Array.isArray(query)) throw new InputError('Укажите точку вылета и дату.');
    const { from, date } = query;
    inputCode(from);
    dateWindow(date, date, now());
    prune(now().getTime());
    let data;
    try { data = await index(signal); }
    catch (error) { abort(signal); return { status: 'unavailable', flights: [], message: 'Справочник аэропортов временно недоступен.' }; }
    const origin = await lookup(from, data, signal);
    let airports;
    if (origin.kind === 'airport') airports = [origin];
    else if (origin.kind === 'city') {
      airports = data.entries.filter(entry => entry.kind === 'airport')
        .map(entry => ({ ...entry, distance: geographicDistance(origin, entry) }))
        .filter(entry => entry.distance <= 100)
        .sort((a, b) => Number(Boolean(b.iata || b.scheduled_catalog_candidate)) - Number(Boolean(a.iata || a.scheduled_catalog_candidate))
          || a.distance - b.distance || a.id.localeCompare(b.id));
    } else throw new InputError('Для выбора рейса укажите город или аэропорт вылета.');
    if (!airports.length) return { status: 'unavailable', flights: [], message: 'В справочнике нет аэропорта в пределах 100 км от выбранного города.' };

    let partial = airports.length > 5, checked = 0;
    const flights = [], seen = new Set(), budget = { remaining: 5 };
    for (const airport of airports.slice(0, 5)) {
      abort(signal);
      let result;
      try { result = await source.schedule({ station: airport.id, date, modes: ['plane'], direction: 'departure', signal, budget }); }
      catch (error) { abort(signal); partial = true; continue; }
      abort(signal);
      if (result?.status !== 'ok' || !Array.isArray(result.departures)) { partial = true; continue; }
      checked++;
      if (result.complete !== true || result.departures.length > 100) partial = true;
      for (const row of result.departures.slice(0, 100)) {
        if (!row || row.mode !== 'plane' || !redWings(row)) continue;
        const departure = datedTime(row.departure), number = numberFrom(row);
        // A calendar or a board returning another day must never become a dated option.
        if (row.from !== airport.id || !departure || departure.slice(0, 10) !== date || !number) { partial = true; continue; }
        const title = text(row.destination_query) || text(row.destination);
        const dedup = `${airport.id}|${number}|${departure}|${title}`;
        if (seen.has(dedup)) continue;
        seen.add(dedup);
        const destination = data.byId.get(row.to) ?? data.citiesByTitle.get(key(title));
        const url = new URL(`https://rasp.yandex.ru/station/${airport.id.slice(1)}/`);
        url.searchParams.set('date', date);
        const id = randomUUID(), at = now();
        flights.push({ id, number, date: departure.slice(0, 10),
          origin: { id: airport.id, title: airport.title, city: airport.city },
          destination: { ...(destination ? { id: destination.id, city: destination.city } : {}),
            title: title || destination?.title || 'Направление в табло не указано' },
          departure,
          // Board arrival is at the queried station, not at the flight destination.
          arrival: null, source_url: row.source_url || result.source_url || url.href,
          checked_at: datedTime(row.checked_at) || datedTime(result.checked_at) || at.toISOString() });
        options.set(id, { number, date: departure.slice(0, 10), expires: at.getTime() + OPTION_TTL });
        prune(at.getTime());
      }
    }
    flights.sort((a, b) => Date.parse(a.departure) - Date.parse(b.departure) || a.number.localeCompare(b.number));
    const status = !checked ? 'unavailable' : partial ? 'partial' : 'ok';
    return { status, flights, ...(!checked ? { message: 'Расписание временно недоступно. Попробуйте загрузить рейсы снова.' }
      : partial ? { message: 'Проверена часть расписания. Список рейсов может быть неполным.' }
        : !flights.length ? { message: 'В проверенных табло на эту дату рейсы Red Wings не найдены.' } : {}) };
  }

  async function normalizeForm(body, { signal } = {}) {
    if (!body || typeof body !== 'object' || Array.isArray(body) || ![Object.prototype, null].includes(Object.getPrototypeOf(body))) throw new InputError('Нужен JSON-объект с параметрами поездки.');
    if (Object.keys(body).some(field => !fields.has(field))) throw new InputError('Форма содержит неизвестные поля.');
    const originId = inputCode(body.origin_id), destinationId = inputCode(body.destination_id);
    const from = body.date_from, to = body.date_to === undefined ? from : body.date_to;
    const at = now();
    dateWindow(from, to, at);
    const originAddress = address(body.origin_address), destinationAddress = address(body.destination_address);
    // Validated for the backend's separate message; wishes are not a Trip field.
    if (body.wishes !== undefined && (typeof body.wishes !== 'string' || body.wishes.length > 2000
      || /[\u0000-\u0008\u000b-\u001f\u007f-\u009f\p{Cf}]/u.test(body.wishes))) {
      throw new InputError('Пожелания должны содержать не более 2000 символов без управляющих знаков, кроме перевода строки и табуляции.');
    }
    let selected = null;
    prune(at.getTime());
    if (body.flight_option_id !== undefined) {
      if (typeof body.flight_option_id !== 'string' || !(selected = options.get(body.flight_option_id))) {
        throw new InputError('Выбранный рейс неизвестен или срок выбора истёк. Загрузите расписание и выберите рейс заново.');
      }
      if (selected.date < from || selected.date > to) throw new InputError('Дата выбранного рейса должна попадать в окно выезда.');
    }
    let data;
    try { data = await index(signal); }
    catch (error) { abort(signal); throw new InputError('Справочник мест временно недоступен. Повторите поиск.', 503); }
    const origin = await lookup(originId, data, signal), destination = await lookup(destinationId, data, signal);
    const endpoint = (entry, value) => ({ city: entry.city, region: entry.region || null, place_id: entry.place_id,
      node_id: entry.node_id ?? null, address: value });
    try {
      return applyTripPatch(emptyTrip(), { origin: endpoint(origin, originAddress), destination: endpoint(destination, destinationAddress),
        date_range: { from, to, meaning: 'departure_window' },
        selected_flight: selected ? { number: selected.number, date: selected.date, leg_id: null } : null }, { now: at });
    } catch (error) { throw new InputError(error.message); }
  }

  return { suggest, flightOptions, normalizeForm };
}
