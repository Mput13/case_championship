import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fetchJson, ConnectorError } from './network.mjs';
import { datedTime, isoDate } from './validation.mjs';

const HOST = 'api.rasp.yandex-net.ru';
const MODES = new Set(['plane', 'train', 'suburban', 'bus']);
const stationCode = value => typeof value === 'string' && /^(?:c|s)\d{1,12}$/.test(value);
export function normalizeTransportSegment(segment, checkedAt) {
  const thread = segment?.thread;
  if (segment?.has_transfers !== false || !MODES.has(thread?.transport_type) || !stationCode(segment.from?.code) || !stationCode(segment.to?.code)) return null;
  const departure = datedTime(segment.departure);
  const arrival = datedTime(segment.arrival);
  const usableArrival = departure && arrival && Date.parse(arrival) > Date.parse(departure) ? arrival : null;
  const url = new URL('https://rasp.yandex.ru/search/');
  url.search = new URLSearchParams({ fromId: segment.from.code, toId: segment.to.code, ...(departure ? { when: departure.slice(0, 10) } : {}) });
  const carrier = thread.carrier;
  return {
    id: createHash('sha256').update([thread.uid, segment.from.code, segment.to.code, departure].join('|')).digest('hex').slice(0, 20),
    from: segment.from.code, to: segment.to.code, mode: thread.transport_type,
    origin: segment.from.title, destination: segment.to.title,
    carrier: carrier?.title ?? null, carrier_code: carrier?.code ?? null, carrier_iata: carrier?.codes?.iata ?? null,
    number: thread.number ?? null, thread_uid: thread.uid ?? null, departure, arrival: usableArrival,
    duration_minutes: departure && usableArrival ? (Date.parse(usableArrival) - Date.parse(departure)) / 60000 : null,
    price: null, availability: 'unknown',
    evidence_status: departure ? 'dated' : 'published_pattern',
    source_name: 'Яндекс Расписания', source_url: url.href, checked_at: checkedAt,
    ...(segment.days ? { published_days: segment.days } : {}),
    ...(segment.start_date ? { published_start_date: segment.start_date } : {}),
    // A source calendar is retained as data; no recurring occurrence is invented here.
    ...(segment.schedule ? { published_calendar: segment.schedule } : {}),
    links: [{ label: 'Проверить расписание', url: url.href },
      ...(thread.transport_type === 'plane' && (carrier?.codes?.iata === 'WZ' || carrier?.code === 617)
        ? [{ label: 'Покупка на сайте Red Wings', url: 'https://flyredwings.com/booking/' }] : [])],
  };
}

// In transfers=true responses the journey endpoints and transfer records carry
// physical stations; detail.from/to may contain settlements instead. Never use
// those settlement codes as a station, or infer stations from a train's title.
export function normalizeTransportChain(segment, checkedAt, { date } = {}) {
  if (!isoDate(date)) return null;
  if (segment?.has_transfers === false) {
    const leg = normalizeTransportSegment(segment, checkedAt);
    return leg && leg.mode !== 'plane' && leg.from.startsWith('s') && leg.to.startsWith('s') && leg.from !== leg.to && leg.departure && leg.arrival
      ? { id: leg.id, legs: [{ ...leg, source_query_date: date }], gaps: [], source_url: leg.source_url, checked_at: checkedAt } : null;
  }
  const details = segment?.details;
  if (segment?.has_transfers !== true || !Array.isArray(details) || details.length < 2) return null;
  const station = (...nodes) => {
    const physical = nodes.filter(n => typeof n?.code === 'string' && /^s\d{1,12}$/.test(n.code));
    return physical.length && physical.every(n => n.code === physical[0].code) ? physical[0] : null;
  };
  const legs = [], gaps = [];
  for (let i = 0; i < details.length; i++) {
    const detail = details[i];
    if (detail?.is_transfer === true) {
      if (!details[i - 1]?.thread || !details[i + 1]?.thread || !station(detail.transfer_from) || !station(detail.transfer_to)) return null;
      continue; // A wait is not a transport edge or evidence of a station move.
    }
    if (!detail?.thread || detail.has_transfers === true || !['train', 'suburban', 'bus'].includes(detail.thread.transport_type)) return null;
    const from = station(detail.from, i === 0 ? segment.departure_from : null, details[i - 1]?.transfer_to);
    const to = station(detail.to, i === details.length - 1 ? segment.arrival_to : null, details[i + 1]?.transfer_from);
    if (!from || !to || from.code === to.code) return null;
    const leg = normalizeTransportSegment({ ...detail, has_transfers: false, from, to }, checkedAt);
    if (!leg?.departure || !leg.arrival) return null;
    legs.push({ ...leg, from_station: { ...from, id: from.code }, to_station: { ...to, id: to.code },
      ...(stationCode(detail.from?.code) && detail.from.code.startsWith('c') ? { from_city_id: detail.from.code } : {}),
      ...(stationCode(detail.to?.code) && detail.to.code.startsWith('c') ? { to_city_id: detail.to.code } : {}),
      source_query_date: date, source_detail_index: i });
  }
  if (legs.length < 2) return null;
  const first = legs[0], last = legs.at(-1);
  if ((segment.departure && Date.parse(segment.departure) !== Date.parse(first.departure)) ||
      (segment.arrival && Date.parse(segment.arrival) !== Date.parse(last.arrival))) return null;
  for (let i = 1; i < legs.length; i++) {
    const prev = legs[i - 1], next = legs[i];
    if (Date.parse(prev.arrival) > Date.parse(next.departure)) return null;
    if (prev.to !== next.from) gaps.push({ kind: 'transfer', from: prev.to, to: next.from,
      reason: `Нет проверенного физического перехода ${prev.destination} → ${next.origin}.` });
  }
  const sourceUrl = new URL('https://rasp.yandex.ru/search/');
  sourceUrl.search = new URLSearchParams({ fromId: first.from, toId: last.to, when: date, transfers: 'true' });
  for (const leg of legs) {
    leg.chain_source_url = sourceUrl.href;
    leg.links.push({ label: 'Источник цепочки с пересадками', url: sourceUrl.href });
  }
  return { id: createHash('sha256').update(legs.map(l => l.id).join('|')).digest('hex').slice(0, 20),
    legs, gaps, source_url: sourceUrl.href, source_name: 'Яндекс Расписания', checked_at: checkedAt };
}
export class YandexTransportSource {
  constructor(config, { fetchImpl = fetch, now = () => new Date() } = {}) { this.config = config; this.fetchImpl = fetchImpl; this.now = now; }
  configured() { return Boolean(this.config.yandexKey || this.config.yandexKeyFile); }
  async #key() {
    if (this.config.yandexKey) return this.config.yandexKey;
    if (!this.config.yandexKeyFile) return '';
    const value = (await readFile(this.config.yandexKeyFile, 'utf8')).trim();
    if (!value || value.length > 8192 || /[\r\n]/.test(value)) throw new ConnectorError('credential_unavailable');
    return value;
  }
  async #request(path, params, { signal, budget, maxBytes = 1048576 } = {}) {
    const key = await this.#key();
    if (!key) return { status: 'key_required', complete: false };
    if (!budget || !Number.isInteger(budget.remaining) || budget.remaining <= 0) return { status: 'request_budget_exhausted', complete: false };
    budget.remaining--;
    const url = new URL(`https://${HOST}/v3.0/${path}/`);
    url.search = new URLSearchParams({ ...params, format: 'json', lang: 'ru_RU' });
    try {
      const data = await fetchJson(url.href, { hosts: [HOST], fetchImpl: this.fetchImpl, headers: { Authorization: key },
        timeout: this.config.httpTimeout ?? 15000, maxBytes, signal });
      if (!data || data.error) throw new ConnectorError('invalid_schedule_response');
      return { status: 'ok', data, checked_at: this.now().toISOString() };
    } catch (error) { return { status: 'upstream_unavailable', complete: false, error_code: error instanceof ConnectorError ? error.code : 'transport_error' }; }
  }
  async stationsList({ signal, budget } = {}) {
    const result = await this.#request('stations_list', {}, { signal, budget, maxBytes: 64 * 1024 * 1024 });
    if (result.status === 'ok' && !Array.isArray(result.data?.countries)) return { status: 'upstream_unavailable', complete: false };
    return result;
  }
  async nearestStations({ lat, lon, radiusKm = 5, modes = ['train', 'suburban', 'bus'], signal, budget } = {}) {
    if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180 ||
      !Number.isFinite(radiusKm) || radiusKm <= 0 || radiusKm > 50 || !Array.isArray(modes) || modes.some(m => !MODES.has(m))) throw new ConnectorError('invalid_transport_query');
    const result = await this.#request('nearest_stations', { lat: String(lat), lng: String(lon), distance: String(radiusKm),
      transport_types: modes.join(','), limit: '100', offset: '0' }, { signal, budget });
    if (result.status !== 'ok') return { ...result, stations: [] };
    if (!Array.isArray(result.data?.stations)) return { status: 'upstream_unavailable', stations: [], complete: false };
    const stations = result.data.stations.filter(s => stationCode(s.code)).map(s => ({
      id: s.code, title: s.title, type: s.station_type, transport_type: s.transport_type,
      lat: s.lat ?? s.latitude ?? null, lon: s.lng ?? s.longitude ?? null, distance_km: s.distance ?? null,
    }));
    const p = result.data.pagination;
    return { status: 'ok', stations, complete: p?.offset === 0 && p.total === stations.length, checked_at: result.checked_at };
  }
  async schedule({ station, date, modes = ['plane', 'train', 'suburban', 'bus'], direction = 'departure', signal, budget } = {}) {
    if (!stationCode(station) || !station.startsWith('s') || (date !== undefined && !isoDate(date)) ||
      !['departure', 'arrival'].includes(direction) || !Array.isArray(modes) || !modes.length || modes.some(m => !MODES.has(m))) throw new ConnectorError('invalid_transport_query');
    const result = await this.#request('schedule', { station, ...(date ? { date } : {}), transport_types: modes.join(','),
      event: direction, limit: '100', offset: '0' }, { signal, budget });
    if (result.status !== 'ok') return { ...result, departures: [], legs: [], segments: [] };
    const data = result.data;
    if (data.station?.code !== station || !Array.isArray(data.schedule)) return { status: 'upstream_unavailable', departures: [], legs: [], segments: [], complete: false };
    const url = new URL(`https://rasp.yandex.ru/station/${station.slice(1)}/`);
    if (date) url.searchParams.set('date', date);
    // Station boards have only one endpoint and time. They discover directions;
    // only a subsequent dated pair search can become a complete flight leg.
    const departures = data.schedule.filter(s => MODES.has(s.thread?.transport_type)).map(s => {
      const thread = s.thread, parts = (thread.short_title || thread.title || '').split(/\s+[—–]\s+/u);
      return { from: direction === 'departure' ? station : null, to: direction === 'arrival' ? station : null,
        origin: direction === 'departure' ? data.station.title : parts[0] || null,
        destination: direction === 'arrival' ? data.station.title : parts.at(-1) || null,
        destination_query: direction === 'departure' && parts.length === 2 ? parts[1] : null,
        origin_query: direction === 'arrival' && parts.length === 2 ? parts[0] : null,
        mode: thread.transport_type, number: thread.number ?? null, thread_uid: thread.uid ?? null,
        carrier: thread.carrier?.title ?? null, carrier_iata: thread.carrier?.codes?.iata ?? null, carrier_code: thread.carrier?.code ?? null,
        departure: datedTime(s.departure), arrival: datedTime(s.arrival), published_days: s.days ?? null,
        evidence_status: date ? 'dated' : 'published_pattern', source_name: 'Яндекс Расписания', source_url: url.href,
        checked_at: result.checked_at, price: null, links: [{ label: 'Табло аэропорта или станции', url: url.href }] };
    });
    const p = data.pagination;
    return { status: 'ok', departures, legs: departures, segments: departures, checked_at: result.checked_at,
      checked_dates: date ? [date] : [], complete: p?.offset === 0 && p.total === data.schedule.length, source_url: url.href };
  }
  async search({ from, to, date, modes = ['plane', 'train', 'suburban', 'bus'], signal, budget }) {
    if (!stationCode(from) || !stationCode(to) || (date !== undefined && !isoDate(date)) || !Array.isArray(modes) || !modes.length || modes.some(mode => !MODES.has(mode))) throw new ConnectorError('invalid_transport_query');
    const key = await this.#key();
    if (!key) return { status: 'key_required', legs: [], complete: false, checked_dates: [], message: 'Нет доступа к датированным транспортным расписаниям. Опубликованный маршрут не подтверждает стыковку.' };
    if (!budget || !Number.isInteger(budget.remaining) || budget.remaining <= 0) return { status: 'request_budget_exhausted', legs: [], complete: false, checked_dates: [] };
    budget.remaining--;
    const url = new URL(`https://${HOST}/v3.0/search/`);
    url.search = new URLSearchParams({ from, to, ...(date ? { date } : {}), transport_types: modes.join(','), transfers: 'false', add_days_mask: 'true', limit: '100', offset: '0', format: 'json', lang: 'ru_RU' });
    try {
      const data = await fetchJson(url.href, { hosts: [HOST], fetchImpl: this.fetchImpl, headers: { Authorization: key }, timeout: this.config.httpTimeout ?? 10000, maxBytes: 1048576, signal });
      if (!Array.isArray(data?.segments) || data.error || data.search?.from?.code !== from || data.search?.to?.code !== to || (date && data.search?.date !== date)) throw new ConnectorError('invalid_schedule_response');
      const checkedAt = this.now().toISOString();
      const legs = data.segments.map(s => normalizeTransportSegment(s, checkedAt)).filter(Boolean)
        .map(l => ({ ...l, source_query_date: date ?? null, evidence_status: date ? l.evidence_status : 'published_pattern' }));
      const p = data.pagination;
      const complete = p?.offset === 0 && Number.isInteger(p.total) && p.total === data.segments.length && legs.length === data.segments.length && !data.interval_segments?.length;
      const sourceUrl = new URL('https://rasp.yandex.ru/search/');
      sourceUrl.search = new URLSearchParams({ fromId: from, toId: to, ...(date ? { when: date } : {}) });
      return { status: 'ok', legs, segments: legs, complete, source_url: sourceUrl.href, checked_at: checkedAt, checked_dates: date ? [date] : [], calendar_query: !date,
        note: 'Источник расписания, не цены/места. Ответ без даты используется для исследования календаря, не доказывает конкретную стыковку.' };
    } catch (error) { return { status: 'upstream_unavailable', legs: [], complete: false, checked_dates: [], error_code: error instanceof ConnectorError ? error.code : 'transport_error' }; }
  }
  // Separate contract: do not flatten composite journeys into source.search's
  // direct legs. A dated details record is the only source of composite edges.
  async searchChains({ from, to, date, modes = ['train', 'suburban', 'bus'], signal, budget } = {}) {
    if (!stationCode(from) || !stationCode(to) || !isoDate(date) || !Array.isArray(modes) || !modes.length ||
      modes.some(mode => !['train', 'suburban', 'bus'].includes(mode))) throw new ConnectorError('invalid_transport_query');
    const result = await this.#request('search', { from, to, date, transport_types: modes.join(','),
      transfers: 'true', add_days_mask: 'true', limit: '100', offset: '0' }, { signal, budget });
    const empty = { chains: [], legs: [], segments: [], complete: false, checked_dates: [] };
    if (result.status !== 'ok') return { ...result, ...empty };
    const data = result.data;
    if (!Array.isArray(data?.segments) || data.search?.from?.code !== from || data.search?.to?.code !== to || data.search?.date !== date)
      return { status: 'upstream_unavailable', error_code: 'invalid_schedule_response', ...empty };
    const chains = data.segments.map(s => normalizeTransportChain(s, result.checked_at, { date })).filter(c => c && c.legs.every(l => modes.includes(l.mode)) &&
      (!from.startsWith('s') || c.legs[0].from === from) && (!to.startsWith('s') || c.legs.at(-1).to === to));
    const p = data.pagination, sourceUrl = new URL('https://rasp.yandex.ru/search/');
    sourceUrl.search = new URLSearchParams({ fromId: from, toId: to, when: date, transfers: 'true' });
    return { status: 'ok', chains, legs: [], segments: [], checked_at: result.checked_at, checked_dates: [date],
      source_url: sourceUrl.href, source_name: 'Яндекс Расписания',
      complete: p?.offset === 0 && Number.isInteger(p.total) && p.total === data.segments.length && chains.length === data.segments.length && !data.interval_segments?.length,
      scope: 'Датированные details; разные станции требуют отдельного физического перехода. Неподдержанные и интервальные участки не подтверждены.' };
  }
}
