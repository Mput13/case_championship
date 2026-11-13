import http from 'node:http';
import { readFile, appendFile } from 'node:fs/promises';
import { YandexTransportSource } from '../../../apps/red-wings-travel-assistant/src/transport-sources.mjs';
import { PlaceIndex } from '../../../apps/red-wings-travel-assistant/src/place-index.mjs';
import { fetchJson } from '../../../apps/red-wings-travel-assistant/src/network.mjs';
const source = new YandexTransportSource({ yandexKeyFile: process.env.YANDEX_RASP_API_KEY_FILE, httpTimeout: 10000 });
const places = new PlaceIndex({ source, cachePath: 'apps/red-wings-travel-assistant/.runtime/russian-places.json',
  airportCatalog: JSON.parse(await readFile('apps/red-wings-travel-assistant/data/service-airports.json', 'utf8')) });
let active = 0, requests = 0;
const server = http.createServer(async (req, res) => {
  const reply = (status, body) => { res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' }); res.end(JSON.stringify(body)); };
  if (req.method !== 'GET') return reply(405, { error: 'read_only' });
  const url = new URL(req.url, 'http://127.0.0.1');
  const label = url.searchParams.get('task') ?? 'unlabelled';
  if (!/^[a-z_]{1,40}$/u.test(label)) return reply(400, { error: 'invalid_task' });
  if (active >= 4 || requests >= 100) return reply(429, { error: 'broker_budget_or_concurrency' });
  active++;
  try {
    let result;
    if (url.pathname === '/resolve') result = await places.resolve(url.searchParams.get('q') ?? '');
    else if (url.pathname === '/airports') {
      const p = await places.resolve(url.searchParams.get('q') ?? '');
      result = p.status === 'ok' ? { airports: await places.nearbyAirports(p.places[0], { limit: 5 }) } : p;
    } else if (url.pathname === '/search') {
      requests++;
      result = await source.search({ from: url.searchParams.get('from'), to: url.searchParams.get('to'), date: url.searchParams.get('date') || undefined,
        modes: (url.searchParams.get('modes') ?? 'plane,train,suburban,bus').split(','), budget: { remaining: 1 } });
    } else if (url.pathname === '/schedule') {
      requests++;
      result = await source.schedule({ station: url.searchParams.get('station'), date: url.searchParams.get('date') || undefined,
        modes: (url.searchParams.get('modes') ?? 'plane').split(','), budget: { remaining: 1 } });
    } else if (url.pathname === '/chain-search') {
      const from = url.searchParams.get('from'), to = url.searchParams.get('to'), date = url.searchParams.get('date');
      if (!/^[sc]\d+$/u.test(from ?? '') || !/^[sc]\d+$/u.test(to ?? '') || !/^\d{4}-\d{2}-\d{2}$/u.test(date ?? '')) return reply(400, { error: 'invalid_query' });
      requests++;
      const endpoint = new URL('https://api.rasp.yandex-net.ru/v3.0/search/');
      endpoint.search = new URLSearchParams({ from, to, date, transfers: 'true', transport_types: 'train,suburban,bus', limit: '100', format: 'json', lang: 'ru_RU' });
      result = await fetchJson(endpoint.href, { hosts: ['api.rasp.yandex-net.ru'], timeout: 15000, maxBytes: 4 * 1024 * 1024,
        headers: { Authorization: (await readFile(process.env.YANDEX_RASP_API_KEY_FILE, 'utf8')).trim() } });
    } else return reply(404, { error: 'unknown_method' });
    await appendFile('context/44_travel_assistant_chat_20261113/receipts/broker.jsonl', JSON.stringify({ at: new Date().toISOString(), task: label, path: url.pathname,
      status: result.status ?? 'ok', request_count: requests }) + '\n');
    reply(200, result);
  } catch { reply(502, { error: 'source_unavailable' }); }
  finally { active--; }
});
server.listen(3090, '127.0.0.1', () => console.log('Transport research broker listening on loopback:3090'));
