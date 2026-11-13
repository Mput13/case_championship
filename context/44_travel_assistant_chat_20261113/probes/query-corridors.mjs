import { readFile, writeFile } from 'node:fs/promises';
import { YandexTransportSource } from '../../../apps/red-wings-travel-assistant/src/transport-sources.mjs';
const directory = JSON.parse(await readFile(new URL('../receipts/station_nodes.json', import.meta.url), 'utf8'));
const airport = iata => directory.settlements.flatMap(c => c.stations).find(s => s.transport_type === 'plane' && s.codes?.iata === iata)?.codes?.yandex_code;
const requests = [
  { id: 'HMA-SGC-bus', from: 'c57', to: 'c973', date: '2026-12-11', modes: ['bus'] },
  { id: 'HMA-SVX-baseline', from: 'c57', to: 's9600370', date: '2026-12-11', modes: ['plane'] },
  { id: 'SVX-Miass-ground', from: 'c54', to: 'c11212', date: '2026-12-11', modes: ['train', 'suburban', 'bus'] },
  { id: 'CEK-Miass-ground', from: 'c56', to: 'c11212', date: '2026-12-11', modes: ['train', 'suburban', 'bus'] },
  ...(airport('CEK') ? [{ id: 'SGC-CEK-plane', from: 's9623563', to: airport('CEK'), date: '2026-12-11', modes: ['plane'] }] : []),
];
const budget = { remaining: requests.length };
const source = new YandexTransportSource({ yandexKeyFile: process.env.YANDEX_RASP_API_KEY_FILE });
const results = [];
let cursor = 0;
await Promise.all([0, 1].map(async () => {
  while (cursor < requests.length) {
    const request = requests[cursor++];
    const answer = await source.search({ ...request, budget });
    results.push({ request, answer });
  }
}));
const receipt = { checked_at: new Date().toISOString(), requests: requests.length, remaining_budget: budget.remaining, results };
await writeFile(new URL('../receipts/corridor_searches.json', import.meta.url), JSON.stringify(receipt, null, 2) + '\n');
for (const { request, answer } of results) console.log(JSON.stringify({ query: request.id, status: answer.status, complete: answer.complete, count: answer.legs?.length, legs: answer.legs?.slice(0, 8).map(l => ({ mode:l.mode, number:l.number, origin:l.origin, destination:l.destination, departure:l.departure, arrival:l.arrival, carrier:l.carrier })) }, null, 2));
