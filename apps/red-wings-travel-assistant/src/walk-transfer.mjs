import { createHash } from 'node:crypto';
import { fetchJson } from './network.mjs';
import { geographicDistance } from './place-index.mjs';
import { shiftLocalTime } from './time-utils.mjs';

// Small, cached pedestrian transfers between public transport station points.
// This local-demo adapter never geocodes or submits the user's street address.
// Public FOSSGIS usage policy: https://github.com/valhalla/valhalla#demo-server
const HOST = 'valhalla1.openstreetmap.de';
export function createWalkTransfer({ enabled = false, fetchImpl = fetch, now = () => new Date() } = {}) {
  const cache = new Map();
  let queued = Promise.resolve(), lastRequestAt = 0;
  return async function transfer({ from, to, notBefore, signal, budget } = {}) {
    if (!enabled || !from || !to || geographicDistance(from, to) > 1.5) return null;
    const pair = [from.lat, from.lon, to.lat, to.lon].map(n => n.toFixed(6)).join(',');
    let observed = cache.get(pair);
    if (!observed) {
      if (!budget || budget.remaining <= 0 || signal?.aborted) return null;
      budget.remaining--;
      const run = async () => {
        const spacing = Math.max(0, 1100 - (Date.now() - lastRequestAt));
        if (spacing) await new Promise(resolve => setTimeout(resolve, spacing));
        if (signal?.aborted) return null;
        lastRequestAt = Date.now();
        const url = new URL(`https://${HOST}/route`);
        url.searchParams.set('json', JSON.stringify({ locations: [{ lat: from.lat, lon: from.lon }, { lat: to.lat, lon: to.lon }],
          costing: 'pedestrian', directions_options: { units: 'kilometers', language: 'ru-RU' } }));
        try {
          const data = await fetchJson(url.href, { hosts: [HOST], fetchImpl, signal, timeout: 10000, maxBytes: 262144,
            headers: { 'User-Agent': 'RedWingsTravelAssistantLocalPrototype/0.2', 'X-Client-Id': 'red-wings-travel-assistant-local-demo' } });
          const summary = data.trip?.summary;
          if (data.trip?.status !== 0 || !Number.isFinite(summary?.time) || summary.time <= 0 ||
            !Number.isFinite(summary.length) || summary.length <= 0 || summary.length > 3) return null;
          const result = { duration_minutes: Math.ceil(summary.time / 60), distance_km: summary.length, checked_at: now().toISOString() };
          if (cache.size >= 100) cache.delete(cache.keys().next().value);
          cache.set(pair, result);
          return result;
        } catch { return null; }
      };
      const pending = queued.then(run, run);
      queued = pending.then(() => {}, () => {});
      observed = await pending;
    }
    if (!observed || signal?.aborted) return null;
    const url = new URL('https://yandex.ru/maps/');
    url.search = new URLSearchParams({ rtext: `${from.lat},${from.lon}~${to.lat},${to.lon}`, rtt: 'pd' });
    const start = typeof notBefore === 'string' && Number.isFinite(Date.parse(notBefore)) ? notBefore : null;
    return { id: `walk-${createHash('sha256').update(pair).digest('hex').slice(0, 12)}`,
      from: from.id, to: to.id, mode: 'walk', origin: from.title, destination: to.title,
      departure: start, arrival: start ? shiftLocalTime(start, observed.duration_minutes) : null,
      duration_minutes: observed.duration_minutes, distance_km: observed.distance_km,
      price: null, evidence_status: 'indicative', source_name: 'Valhalla / OpenStreetMap contributors',
      source_url: 'https://valhalla.openstreetmap.de/', checked_at: observed.checked_at,
      note: 'Оценка пешего маршрута между точками станций по OpenStreetMap; входы терминала, погода и досмотр могут увеличить время.',
      links: [{ label: 'Пеший переход на карте', url: url.href }, { label: 'Данные OpenStreetMap', url: 'https://www.openstreetmap.org/copyright' }] };
  };
}
