import { readFile, writeFile } from 'node:fs/promises';
import { fetchJson } from '../../../apps/red-wings-travel-assistant/src/network.mjs';
import { YandexTransportSource } from '../../../apps/red-wings-travel-assistant/src/transport-sources.mjs';
const key = (await readFile(process.env.YANDEX_RASP_API_KEY_FILE, 'utf8')).trim();
const receipt = { checked_at: new Date().toISOString(), queries: [], key_in_url: false };
for (const path of ['carrier/?code=WZ&system=iata&format=json', 'copyright/?format=json']) {
  try {
    const data = await fetchJson('https://api.rasp.yandex-net.ru/v3.0/' + path, { hosts: ['api.rasp.yandex-net.ru'], headers: { Authorization: key }, timeout: 15000 });
    if (path.startsWith('carrier')) receipt.carriers = data.carriers ?? data.carrier ?? data;
    else receipt.copyright = data;
    receipt.queries.push({ method: path.split('/')[0], status: 'ok' });
  } catch (error) { receipt.queries.push({ method: path.split('/')[0], status: 'error', error_code: error.code ?? error.constructor.name }); }
}
const source = new YandexTransportSource({ yandexKeyFile: process.env.YANDEX_RASP_API_KEY_FILE });
const search = await source.search({ from: 's9623563', to: 's9600370', date: '2026-12-11', modes: ['plane'], budget: { remaining: 1 } });
receipt.flight_search = search;
await writeFile(new URL('../receipts/yandex_access.json', import.meta.url), JSON.stringify(receipt, null, 2) + '\n');
console.log(JSON.stringify({ queries: receipt.queries, flight_search_status: search.status, complete: search.complete, flights: search.legs?.map(({ number, carrier, carrier_code, carrier_iata, departure, arrival }) => ({ number, carrier, carrier_code, carrier_iata, departure, arrival })) }, null, 2));
