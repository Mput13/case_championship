import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';

const normalized = value => String(value ?? '').toLocaleLowerCase('ru').replaceAll('ё', 'е')
  .replace(/^\s*(?:г[.]?\s+|город\s+)/u, '').replace(/[—–]/gu, '-').replace(/\s+/gu, ' ').trim();
const point = s => Number.isFinite(s.lat) && Number.isFinite(s.lon);
export function geographicDistance(a, b) {
  if (!point(a) || !point(b)) return Infinity;
  const rad = n => n * Math.PI / 180;
  const dLat = rad(b.lat - a.lat), dLon = rad(b.lon - a.lon);
  const x = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLon / 2) ** 2;
  return 6371 * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(Math.max(0, 1 - x)));
}
function finite(value) { return value === null || value === '' || value === undefined ? null : Number.isFinite(Number(value)) ? Number(value) : null; }
export function compactRussianPlaces(data, checkedAt) {
  const places = [];
  for (const country of data?.countries ?? []) {
    if (country.title !== 'Россия') continue;
    for (const region of country.regions ?? []) for (const settlement of region.settlements ?? []) {
      const id = settlement.codes?.yandex_code;
      if (!/^c\d+$/u.test(id ?? '')) continue;
      const stations = (settlement.stations ?? []).filter(s => /^s\d+$/u.test(s.codes?.yandex_code ?? '')).map(s => ({
        id: s.codes.yandex_code, title: s.title, city_id: id, city: settlement.title, region: region.title,
        type: s.station_type === 'airport' ? 'airport' : s.transport_type === 'train' || s.transport_type === 'suburban'
          ? 'train_station' : s.transport_type === 'bus' ? 'bus_station' : 'station',
        station_type: s.station_type, transport_type: s.transport_type,
        lat: finite(s.latitude), lon: finite(s.longitude),
      }));
      // A station point only screens geographically close airports; it is never
      // used as a street address or as evidence of ground journey duration.
      const representative = stations.find(s => point(s) && s.type === 'train_station' && normalized(s.title) === normalized(settlement.title))
        ?? stations.find(s => point(s) && s.type !== 'airport') ?? stations.find(point);
      places.push({ id, title: settlement.title, region: region.title, country: country.title,
        lat: representative?.lat ?? null, lon: representative?.lon ?? null, stations });
    }
  }
  return { version: 1, checked_at: checkedAt, source_name: 'Яндекс Расписания', places };
}

export class PlaceIndex {
  #loaded = null;
  #loading = null;
  #stations = new Map();
  constructor({ source, cachePath, data, airportCatalog, now = () => new Date(), maxAgeMs = 86400000 } = {}) {
    this.source = source; this.cachePath = cachePath; this.data = data; this.airportCatalog = airportCatalog; this.now = now; this.maxAgeMs = maxAgeMs;
  }
  async load({ signal } = {}) {
    if (this.#loaded) return this.#loaded;
    if (this.#loading) return this.#loading;
    this.#loading = this.#read({ signal });
    try {
      this.#loaded = await this.#loading;
      for (const p of this.#loaded.places) for (const s of p.stations) {
        if (s.type === 'airport' && this.airportCatalog) {
          const matching = (this.airportCatalog.airports ?? []).map(a => ({ ...a, distance: geographicDistance(a, s) }))
            .filter(a => a.distance <= 3).sort((a, b) => a.distance - b.distance)[0];
          s.scheduled_catalog_candidate = Boolean(matching);
          if (matching) Object.assign(s, { iata: matching.iata, catalog_ident: matching.ident,
            catalog_source: this.airportCatalog.source_url, scheduled_catalog_candidate: true });
        }
        this.#stations.set(s.id, s);
      }
      return this.#loaded;
    } finally { this.#loading = null; }
  }
  async #read({ signal }) {
    if (this.data) return this.data.places ? this.data : compactRussianPlaces(this.data, this.now().toISOString());
    if (this.cachePath) {
      try {
        const cached = JSON.parse(await readFile(this.cachePath, 'utf8'));
        if (cached.version === 1 && Array.isArray(cached.places) && cached.places.length &&
          this.now().getTime() - Date.parse(cached.checked_at) < this.maxAgeMs) return cached;
      } catch { /* Missing or stale cache requires one dictionary request. */ }
    }
    const result = await this.source?.stationsList({ signal, budget: { remaining: 1 } });
    if (result?.status !== 'ok') throw new Error('place_dictionary_unavailable');
    const compact = compactRussianPlaces(result.data, result.checked_at);
    if (!compact.places.length) throw new Error('place_dictionary_unavailable');
    if (this.cachePath) {
      await mkdir(dirname(this.cachePath), { recursive: true });
      await writeFile(this.cachePath, JSON.stringify(compact), { mode: 0o600 });
    }
    return compact;
  }
  async resolve(query, { signal } = {}) {
    const data = await this.load({ signal }), q = normalized(query);
    if (!q || q.length > 240) return { status: 'not_found', places: [] };
    let found = data.places.filter(p => p.id === query || normalized(p.title) === q || normalized(`${p.title}, ${p.region}`) === q ||
      p.stations.some(s => s.iata && normalized(s.iata) === q));
    if (!found.length) {
      found = data.places.flatMap(p => {
        const matches = p.stations.filter(s => s.id === query || normalized(s.title) === q);
        return matches.map(s => ({ ...p, lat: s.lat ?? p.lat, lon: s.lon ?? p.lon, matched_station: s, suggested_node_id: s.id }));
      });
    }
    if (!found.length) found = data.places.filter(p => normalized(`${p.title}, ${p.region}`).includes(q));
    const total = found.length;
    return { status: total === 0 ? 'not_found' : total === 1 ? 'ok' : 'ambiguous', places: found.slice(0, 20),
      total, checked_at: data.checked_at, source_name: data.source_name, coverage: 'Российские населённые пункты справочника Яндекс Расписаний. Адреса домов не геокодированы.' };
  }
  async nearbyAirports(place, { limit = 5, radiusKm = 450, signal } = {}) {
    const data = await this.load({ signal });
    const origin = typeof place === 'string' ? data.places.find(p => p.id === place) : place;
    if (!origin || !point(origin)) return [];
    return data.places.flatMap(p => p.stations).filter(s => s.type === 'airport' && point(s) && (!this.airportCatalog || s.scheduled_catalog_candidate))
      .map(s => ({ ...s, distance_km: geographicDistance(origin, s), distance_kind: 'geographic_screen_only' }))
      .filter(s => s.distance_km <= radiusKm).sort((a, b) => a.distance_km - b.distance_km).slice(0, Math.max(1, Math.min(10, limit)));
  }
  async getStation(id, { signal } = {}) { await this.load({ signal }); return this.#stations.get(id) ?? null; }
}
