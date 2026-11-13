// Offline extractor. Never contacts an API, reads credentials, or modifies source receipts.
import { readFile, writeFile, stat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { datedTime, flightNumber } from './validation.mjs';

const root = fileURLToPath(new URL('../../../', import.meta.url));
const sourceDirectory = 'context/40_swarm_pricing_research_20261113';
const cityNames = {
  KUF: 'Самара', KZN: 'Казань', SVX: 'Екатеринбург', UFA: 'Уфа', BAX: 'Барнаул',
  GOJ: 'Нижний Новгород', GSV: 'Саратов', TOF: 'Томск', HTA: 'Чита', IAR: 'Ярославль',
  LED: 'Санкт-Петербург', KEJ: 'Кемерово', OMS: 'Омск', NOZ: 'Новокузнецк', UUD: 'Улан-Удэ',
  SGC: 'Сургут', TJM: 'Тюмень', REN: 'Оренбург', MCX: 'Махачкала', NJC: 'Нижневартовск',
};
export async function buildSnapshot(repoRoot = root) {
  const receipts = {};
  const sources = [];
  for (const [id, name] of [['hub', 'yandex_hub_schedules.json'], ['search', 'yandex_spotlight_search.json']]) {
    const path = `${sourceDirectory}/${name}`;
    const raw = await readFile(resolve(repoRoot, path));
    receipts[id] = JSON.parse(raw);
    sources.push({ id, name: 'Яндекс Расписания', path, sha256: createHash('sha256').update(raw).digest('hex'),
      fetched_at: null, file_modified_at: (await stat(resolve(repoRoot, path))).mtime.toISOString(),
      timestamp_note: 'Время изменения локального файла; точное время HTTP-получения не сохранено.',
      url: 'https://rasp.yandex.ru/' });
  }
  const airports = Object.entries(cityNames).map(([iata, city]) => {
    const record = receipts.hub[`${iata}:2026-12-08`];
    if (record?.station?.station_type !== 'airport') throw new Error(`Missing station ${iata}`);
    return { iata, city, name: record.station.title, code: record.station.code };
  });
  const coverage = [];
  const flights = [];
  for (const airport of airports) {
    for (const date of ['2026-12-08', '2026-12-11']) {
      const key = `${airport.iata}:${date}`;
      const record = receipts.hub[key];
      if (!record || !Array.isArray(record.schedule)) continue;
      const page = record.pagination;
      const complete = record.event === 'departure' && record.date === date && page?.offset === 0 && Number.isInteger(page.total) && page.total <= record.schedule.length;
      coverage.push({ origin: airport.code, date, complete, total: page?.total ?? null, saved: record.schedule.length, source_id: 'hub', source_key: key });
      for (const [index, row] of record.schedule.entries()) {
        const t = row.thread;
        if (t?.carrier?.code !== 617 || t.carrier.codes?.iata !== 'WZ' || t.transport_type !== 'plane' || row.is_fuzzy || row.stops) continue;
        const [from, to, extra] = t.title.split(' — ');
        const destination = airports.find(a => a.city === to);
        if (from !== airport.city || !destination || extra || !datedTime(row.departure) || row.departure.slice(0, 10) !== date) continue;
        const number = flightNumber(t.number);
        if (!number) continue;
        const provenance = [{ source_id: 'hub', source_key: key, pointer: `/schedule/${index}` }];
        let arrival = datedTime(row.arrival);
        for (const [searchKey, answer] of Object.entries(receipts.search)) {
          for (const [i, segment] of (answer.segments ?? []).entries()) {
            if (segment.has_transfers !== false || segment.thread?.carrier?.code !== 617) continue;
            if (flightNumber(segment.thread?.number) === number && segment.departure === row.departure && segment.from?.code === airport.code && segment.to?.code === destination.code && datedTime(segment.arrival)) {
              if (arrival && arrival !== segment.arrival) throw new Error('Conflicting arrival evidence');
              arrival = segment.arrival;
              provenance.push({ source_id: 'search', source_key: searchKey, pointer: `/segments/${i}` });
            }
          }
        }
        if (arrival && Date.parse(arrival) <= Date.parse(row.departure)) throw new Error('Invalid time order');
        flights.push({ id: `${airport.iata}-${destination.iata}-${date}-${number.replace(' ', '')}`, origin: airport.code, destination: destination.code,
          departure: row.departure, arrival, flight_number: number, source_flight_number: t.number,
          carrier_code: 617, carrier_iata: 'WZ', carrier: 'Red Wings', price: null, provenance });
      }
    }
  }
  return { schema_version: 1, data_mode: 'snapshot', extracted_at: new Date().toISOString(), checked_at: null,
    coverage_note: 'Сохранённые ответы для 8 и 11 декабря 2026 года; только прямые рейсы между перечисленными аэропортами. Снимок не подтверждает актуальность, места или цену. Точное время получения ответов неизвестно; время файла — только происхождение снимка.',
    sources, airports, coverage, flights };
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const snapshot = await buildSnapshot();
  await writeFile(new URL('../data/snapshot.json', import.meta.url), `${JSON.stringify(snapshot, null, 2)}\n`);
  console.log(JSON.stringify({ airports: snapshot.airports.length, flights: snapshot.flights.length, with_arrival: snapshot.flights.filter(f => f.arrival).length }));
}
