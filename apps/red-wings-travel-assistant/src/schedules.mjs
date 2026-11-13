import { readFile } from 'node:fs/promises';
import { datedTime, flightNumber, normalizeCity } from './validation.mjs';
import { ConnectorError, Gate, fetchJson, allowedEndpoint } from './network.mjs';
export const YANDEX_HOSTS = ['api.rasp.yandex-net.ru', 'api.rasp.yandex.net'];
export const loadSnapshot = async () => JSON.parse(await readFile(new URL('../data/snapshot.json', import.meta.url), 'utf8'));
export function isRedWings(row) {
  // A marketing name or a WZ-looking flight number alone is insufficient.
  return row.carrier_code === 617 && row.carrier_iata === 'WZ';
}
export function resolveAirport(snapshot, text) {
  const key = normalizeCity(text);
  return snapshot.airports.find(a => normalizeCity(a.city) === key || a.iata.toLowerCase() === key) ?? null;
}
export class SnapshotSchedules {
  constructor(snapshot) { this.snapshot = snapshot; this.mode = 'snapshot'; }
  async search({ origin, destination, dates }) {
    const covered = dates.map(date => this.snapshot.coverage.find(c => c.origin === origin.code && c.date === date));
    return {
      flights: this.snapshot.flights.filter(f => f.origin === origin.code && f.destination === destination.code && dates.includes(f.departure?.slice(0, 10)) && isRedWings(f)),
      complete: covered.every(c => c?.complete),
      missing_dates: dates.filter((_, i) => !covered[i]?.complete),
      checked_at: this.snapshot.checked_at, sources: this.snapshot.sources,
      coverage_note: this.snapshot.coverage_note,
    };
  }
}
export class LiveSchedules {
  constructor(config, { fetchImpl = fetch, now = () => new Date() } = {}) {
    this.config = config; this.fetchImpl = fetchImpl; this.now = now; this.mode = 'live';
    this.gate = new Gate(config.maxConcurrentOutbound);
  }
  async search({ origin, destination, dates, signal }) {
    if (!this.config.yandexKey) return { unavailable: true, code: 'missing_schedule_key', flights: [], complete: false, sources: [], coverage_note: 'Для live-поиска нужен YANDEX_RASP_API_KEY. Снимок автоматически не подставляется.' };
    const today = this.now().toISOString().slice(0, 10);
    const horizon = new Date(this.now().getTime() + 365 * 86400000).toISOString().slice(0, 10);
    if (dates.some(date => date < today || date > horizon)) return { unavailable: true, code: 'live_date_range', flights: [], complete: false, sources: [], coverage_note: 'Live-поиск поддерживает даты от текущей UTC-даты до 365 дней вперёд.' };
    return this.gate.run(async () => {
      const flights = [];
      const missing = [];
      for (const date of dates) {
        const base = allowedEndpoint(this.config.yandexBase, YANDEX_HOSTS);
        if (!base.pathname.endsWith('/')) base.pathname += '/';
        const url = new URL('search/', base);
        url.search = new URLSearchParams({ from: origin.code, to: destination.code, date, format: 'json', lang: 'ru_RU', transport_types: 'plane', transfers: 'false', limit: '100', offset: '0' });
        const answer = await fetchJson(url.href, { hosts: YANDEX_HOSTS, fetchImpl: this.fetchImpl, headers: { Authorization: this.config.yandexKey }, timeout: this.config.httpTimeout, signal });
        if (!Array.isArray(answer?.segments) || answer.error || answer.search?.date !== date || answer.search?.from?.code !== origin.code || answer.search?.to?.code !== destination.code) throw new ConnectorError('invalid_schedule_response');
        const page = answer.pagination;
        if (!(page?.offset === 0 && Number.isInteger(page.total) && page.total >= 0 && page.total <= answer.segments.length)) missing.push(date);
        for (const segment of answer.segments) {
          const t = segment?.thread;
          const carrier = { carrier_code: t?.carrier?.code, carrier_iata: t?.carrier?.codes?.iata };
          if (!isRedWings(carrier)) {
            if (carrier.carrier_code === 617 || carrier.carrier_iata === 'WZ' || !t?.carrier?.code) missing.push(date);
            continue;
          }
          // The first prototype accepts only direct, dated airport-to-airport flights.
          if (segment.has_transfers !== false || t?.transport_type !== 'plane' || segment.from?.code !== origin.code || segment.to?.code !== destination.code) { missing.push(date); continue; }
          const departure = datedTime(segment.departure);
          const number = flightNumber(t.number);
          if (!departure || departure.slice(0, 10) !== date || !number) { missing.push(date); continue; }
          let arrival = datedTime(segment.arrival);
          if (arrival && Date.parse(arrival) <= Date.parse(departure)) { arrival = null; missing.push(date); }
          flights.push({ id: `${origin.iata}-${destination.iata}-${date}-${number.replace(' ', '')}`, origin: origin.code, destination: destination.code,
            departure, arrival, flight_number: number, source_flight_number: t.number, ...carrier, carrier: 'Red Wings', price: null,
            provenance: [{ source_id: 'yandex-live', date }] });
        }
      }
      return { flights, complete: missing.length === 0, missing_dates: [...new Set(missing)], checked_at: this.now().toISOString(),
        sources: [{ id: 'yandex-live', name: 'Яндекс Расписания', url: 'https://rasp.yandex.ru/' }],
        coverage_note: 'Live-ответ Яндекс Расписаний: только прямые рейсы между выбранными аэропортами, до 100 результатов на день. Наличие мест и цены не запрашивались.' };
    });
  }
}
