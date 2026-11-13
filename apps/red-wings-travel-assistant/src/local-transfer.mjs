import { createWalkTransfer } from './walk-transfer.mjs';

// Published airport route 65: this is an interval-based conservative duration,
// not an invented dated bus departure. Dated intercity legs remain separate.
const SVX = 's9600370', RAIL = 's9607404';
export function createLocalTransfer({ places, walkRoutingEnabled = false, fetchImpl, now = () => new Date() } = {}) {
  const walk = createWalkTransfer({ enabled: walkRoutingEnabled, fetchImpl, now });
  return async function transfer(args) {
    const from = await places.getStation(args.from.id, { signal: args.signal }) ?? args.from;
    const to = await places.getStation(args.to.id, { signal: args.signal }) ?? args.to;
    if (from.id === SVX && to.id === RAIL && args.notBefore) {
      const local = new Date(Date.parse(args.notBefore) + 5 * 3600000);
      const weekend = [0, 6].includes(local.getUTCDay());
      const ready = local.getUTCHours() * 60 + local.getUTCMinutes();
      const first = weekend ? 381 : 359, last = weekend ? 1426 : 1431;
      // Outside the independently verified departure window, leave it unknown.
      if (ready < first || ready > last - 44) return null;
      return { id: 'svx-route-65-to-station', from: from.id, to: to.id, mode: 'bus',
        origin: 'Кольцово, аэропорт', destination: 'Екатеринбург-Пасс., железнодорожный вокзал',
        carrier: null, number: '65', departure: null, arrival: null, duration_minutes: 109, price: null,
        evidence_status: 'published_pattern', source_name: 'Аэропорт Кольцово: автобус №65',
        source_url: 'https://ar-svx.ru/how-to-get/from/bus/', checked_at: '2026-11-13',
        note: 'По опубликованному режиму: 65 мин в пути и до 44 мин ожидания. Конкретное отправление автобуса на выбранную дату не подтверждено. Не включает 60 мин после прилёта.',
        links: [{ label: 'Автобус №65: маршрут и интервалы', url: 'https://ar-svx.ru/how-to-get/from/bus/' }] };
    }
    return walk({ ...args, from, to });
  };
}
