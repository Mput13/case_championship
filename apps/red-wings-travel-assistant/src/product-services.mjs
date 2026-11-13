const basket = () => ({ status: 'not_connected', title: 'Оформление в одной корзине',
  description: 'Целевая интеграция White Label РЖД-ЦПР и страхования стыковки по модели Trip&Fly. Требует подключения партнёрского API; сейчас билеты оформляются отдельно.', links: [] });
const map = (from, to) => {
  const url = new URL('https://yandex.ru/maps/');
  url.search = new URLSearchParams({ rtext: `${from}~${to}`, rtt: 'mt' });
  return url.href;
};
// An explicit product rule, not an assertion about a particular operator:
// partners may win within 15 minutes only with checked connections and no
// additional transfers/night stay. Unknown metrics never earn the badge.
export function rankTransferOptions(options, { comparableMinutes = 15 } = {}) {
  const known = o => o.status === 'available' && o.connection_status === 'verified' &&
    Number.isFinite(o.total_duration_minutes) && Number.isInteger(o.transfers) && typeof o.overnight === 'boolean';
  const valid = options.filter(known);
  const best = [...valid].sort((a, b) => Number(a.overnight) - Number(b.overnight) || a.total_duration_minutes - b.total_duration_minutes || a.transfers - b.transfers)[0];
  const eligible = best ? valid.filter(o => o.is_red_wings_partner === true &&
    o.total_duration_minutes <= best.total_duration_minutes + comparableMinutes &&
    Number(o.overnight) <= Number(best.overnight) && o.transfers <= best.transfers)
    .sort((a, b) => a.total_duration_minutes - b.total_duration_minutes)[0] : null;
  return options.map(o => ({ ...o, recommended: Boolean(eligible && o.id === eligible.id),
    ...(eligible && o.id === eligible.id ? { recommendation_badge: 'Рекомендуемый партнёрский трансфер под рейс WZ',
      recommendation_reason: `Стыковка проверена; без дополнительных пересадок и ночёвки относительно лучшего сравнимого варианта. Допуск по общему времени — ${comparableMinutes} мин.` } : {}) }))
    .sort((a, b) => Number(b.recommended) - Number(a.recommended) || Number(known(b)) - Number(known(a)) ||
      (Number.isFinite(a.total_duration_minutes) && Number.isFinite(b.total_duration_minutes) ? a.total_duration_minutes - b.total_duration_minutes : 0));
}
export function decorateJourneyResult(result, trip) {
  return { ...result, plans: result.plans.map(p => ({ ...p, network_mode: trip.network_mode ?? 'current',
    ...(p.transfer_options ? { transfer_options: rankTransferOptions(p.transfer_options) } : {}),
    ...(p.requires_red_wings ? { basket: basket() } : {}) })) };
}
export function scenarioJourney(trip) {
  const omsk = /омск/iu.test(trip.origin?.city ?? '');
  const olkhon = /ольхон|хужир/iu.test(`${trip.destination?.city ?? ''} ${trip.destination?.address ?? ''}`);
  if (!omsk || !olkhon) return { status: 'partial', plans: [], sources: [], missing_data: [
    'Для этой пары сценарный маршрут не задан. Сценарная сеть 2027–2028 не подменяется действующим расписанием.' ] };
  const options = [{ id: 'public', title: 'Общественный транспорт', status: 'unverified', connection_status: 'unknown', duration_minutes: null,
    description: 'Нужно проверить на выбранную дату переезд из аэропорта в Иркутск и автобус до Хужира, включая сезонную переправу. Стыковка пока не рассчитана.',
    links: [{ label: 'Проверить путь общественным транспортом', url: map('Аэропорт Иркутск', 'Хужир, остров Ольхон') }] },
  { id: 'smart-transfer', title: 'Умный трансфер — целевой партнёрский шаттл под рейс WZ', status: 'target', duration_minutes: null,
    description: 'Предлагаемый прямой шаттл IKT → Хужир без заезда на городской автовокзал. Перевозчик подстраивает расписание под WZ, Red Wings приводит авиапассажиров. После подтверждения сопоставимого времени и удобства такой партнёрский вариант получает приоритет. Требуются партнёр, сезонный маршрут и тариф; бронирование не подключено.', links: [] }];
  const plan = { id: 'scenario-oms-ikt-olkhon', title: 'Омск → Иркутск → Ольхон', status: 'candidate',
    network_mode: 'scenario_2027_2028', requires_red_wings: true, total_duration_minutes: null, total_price: null,
    summary: 'Сценарный режим (сеть 2027–2028). Проектируемый рейс OMS → IKT: 3 рейса туда-обратно в неделю; дни и время ещё не заданы.',
    legs: [{ id: 'scenario-oms-ikt', mode: 'plane', origin: 'Омск (OMS)', destination: 'Иркутск (IKT)',
      carrier: 'Red Wings — сценарное предложение', carrier_iata: 'WZ', number: null, departure: null, arrival: null,
      duration_minutes: null, price: null, evidence_status: 'unknown', source_name: 'Условие демонстрационного сценария MULTIMODAL_SPEC, REQ-6',
      source_url: null, checked_at: null, links: [] }],
    warnings: ['Это предложение сети, не опубликованный рейс. Покупка недоступна.',
      'Время прилёта не задано: ни общественный транспорт, ни шаттл пока нельзя считать состыкованными.',
      'Для Ольхона нужны сезонные условия переправы и адрес прибытия; полное время и цена неизвестны.'],
    reasonableness: { status: 'unknown', explanation: 'Сравнить удобство можно после задания времени рейса и проверки наземного сообщения.' },
    transfer_options: options, basket: basket(), sources: [] };
  return { status: 'partial', plans: [plan], sources: [], missing_data: ['Нужно проектное время рейса OMS → IKT и подтверждённые наземные расписания/партнёрский шаттл.'],
    coverage: { network_mode: 'scenario_2027_2028', live_queries: 0, condition_source: 'MULTIMODAL_SPEC.md, сценарий 3' } };
}
