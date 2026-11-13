import { createHash } from 'node:crypto';
import { datesBetween, datedTime, flightNumber, validateRequest } from './validation.mjs';
import { isRedWings, resolveAirport } from './schedules.mjs';
import { bookingLink, navigationLink, scheduleLink } from './links.mjs';
import { ConnectorError } from './network.mjs';

const priceNote = 'Стоимость билета и наземных участков неизвестна. Наличие мест не проверено.';
function ground(origin, destination) {
  return { mode: 'ground', origin, destination, departure: null, arrival: null, carrier: null, price: null, status: 'suggestion',
    source_name: 'Навигационная рекомендация', source_url: null,
    links: [{ label: 'Общественным транспортом', url: navigationLink(origin, destination, 'mt') },
      { label: 'Автомобилем', url: navigationLink(origin, destination) }] };
}
function variant(flight, origin, destination, request) {
  const airportFrom = `${origin.city}, аэропорт ${origin.name} (${origin.iata})`;
  const airportTo = `${destination.city}, аэропорт ${destination.name} (${destination.iata})`;
  const departure = datedTime(flight.departure);
  const arrivalCandidate = datedTime(flight.arrival);
  const arrival = arrivalCandidate && Date.parse(arrivalCandidate) > Date.parse(departure) ? arrivalCandidate : null;
  const sourceUrl = scheduleLink(origin.code, destination.code, departure.slice(0, 10));
  const plane = { mode: 'plane', origin: airportFrom, destination: airportTo, departure, arrival,
    duration_minutes: arrival ? (Date.parse(arrival) - Date.parse(departure)) / 60000 : null,
    carrier: 'Red Wings', carrier_code: flight.carrier_code, carrier_iata: flight.carrier_iata,
    flight_number: flight.flight_number, price: null, status: 'scheduled', source_name: 'Яндекс Расписания', source_url: sourceUrl,
    links: [{ label: 'Проверить расписание', url: sourceUrl }, { label: 'Выбрать билет у Red Wings', url: bookingLink() }],
    provenance: flight.provenance,
  };
  const warnings = ['Наземные участки и запас до регистрации ещё не рассчитаны. Ссылки на карты не передают дату поездки.'];
  if (!arrival) warnings.push('Источник не содержит подтверждённого времени прилёта.');
  if (request.preference === 'fastest') warnings.push('Сравнение общей длительности недоступно: время наземной дороги неизвестно. Показаны вылеты по времени отправления.');
  return {
    id: createHash('sha256').update(`${flight.origin}|${flight.destination}|${flight.departure}|${flight.flight_number}`).digest('hex').slice(0, 16),
    title: `${origin.city} → ${destination.city} · ${flight.flight_number}`,
    departure: null, arrival: null, duration_minutes: null, total_price: null, currency: 'RUB', price_note: priceNote, warnings,
    legs: [ground(request.origin_address ? `${origin.city}, ${request.origin_address}` : origin.city, airportFrom), plane,
      ground(airportTo, request.destination_address ? `${destination.city}, ${request.destination_address}` : destination.city)],
  };
}
export async function planTrip(input, { snapshot, schedules, agent, config, signal }) {
  const request = validateRequest(input);
  const base = { status: 'needs_data', data_mode: schedules.mode, checked_at: null, variants: [], sources: [] };
  const origin = resolveAirport(snapshot, request.origin);
  const destination = resolveAirport(snapshot, request.destination);
  if (!origin || !destination) return { ...base, message: 'Город вне покрытия прототипа. Выберите пару из примеров или списка поддержанных городов.', coverage_note: snapshot.airports.map(a => a.city).join(', ') };
  if (origin.code === destination.code) return { ...base, message: 'Выберите разные аэропорты.' };
  const dates = request.mode === 'flight' ? [request.flight_date] : datesBetween(request.date_from, request.date_to);
  let result;
  try { result = await schedules.search({ origin, destination, dates, signal }); }
  catch (error) {
    return { ...base, status: 'error', data_mode: 'unavailable', error_code: error instanceof ConnectorError ? error.code : 'connector_error',
      message: 'Источник расписания не ответил корректно. Результат поиска неизвестен; снимок вместо live не подставлялся.' };
  }
  if (result.unavailable) return { ...base, data_mode: 'unavailable', message: result.coverage_note, error_code: result.code, coverage_note: result.coverage_note };
  Object.assign(base, { checked_at: result.checked_at, sources: result.sources, coverage_note: result.coverage_note });
  const missingNote = result.missing_dates?.length ? ` Неполное покрытие дат: ${result.missing_dates.join(', ')}.` : '';
  base.coverage_note += missingNote;
  const candidates = result.flights.filter(f => isRedWings(f) && f.origin === origin.code && f.destination === destination.code && datedTime(f.departure) &&
    dates.includes(f.departure.slice(0, 10)) && flightNumber(f.flight_number) && (request.mode !== 'flight' || f.flight_number === request.flight_number));
  const unique = [...new Map(candidates.map(f => [`${f.departure}|${f.flight_number}|${f.origin}|${f.destination}`, f])).values()];
  unique.sort((a, b) => Date.parse(a.departure) - Date.parse(b.departure));
  if (!unique.length) return { ...base, status: result.complete ? 'no_routes' : 'needs_data', message: result.complete
    ? 'В проверенном расписании на выбранные даты нет подходящего прямого рейса Red Wings между этими аэропортами. Другие аэропорты и пересадки не проверялись.'
    : 'Данных недостаточно, чтобы подтвердить или исключить подходящий рейс. Попробуйте дату из примеров.' };
  const variants = unique.slice(0, config.maxVariants).map(f => variant(f, origin, destination, request));
  if (!result.complete) for (const v of variants) v.warnings.push(`Показана только подтверждённая часть поиска.${missingNote}`);
  const plan = { ...base, status: 'ok', variants, ...(unique.length > config.maxVariants ? { message: `Показаны первые ${config.maxVariants} вылетов; уточните даты.` } : {}) };
  if (agent) {
    try { plan.assistant = await agent.explain({ request, plan, signal }); }
    catch { plan.assistant = { status: 'error', text: 'Пояснение недоступно. Варианты из расписания сохранены.' }; }
  }
  return plan;
}
export function getExamples(snapshot) {
  const pairs = [['Самара', 'Екатеринбург', '2026-12-08'], ['Казань', 'Екатеринбург', '2026-12-08'], ['Екатеринбург', 'Уфа', '2026-12-08'], ['Екатеринбург', 'Казань', '2026-12-11']];
  const examples = [];
  for (const [origin, destination, date] of pairs) {
    const from = resolveAirport(snapshot, origin), to = resolveAirport(snapshot, destination);
    const flight = snapshot.flights.find(f => f.origin === from?.code && f.destination === to?.code && f.departure.startsWith(date) && isRedWings(f));
    if (!flight) continue;
    const request = { mode: 'trip', origin, destination, date_from: date, date_to: date, preference: 'balanced' };
    examples.push({ id: `trip-${examples.length + 1}`, label: `${origin} → ${destination}`, request });
    if (examples.length === 1) examples.push({ id: 'flight-samara', label: `Уже есть ${flight.flight_number}`, request: { ...request, mode: 'flight', flight_number: flight.flight_number, flight_date: date } });
  }
  return { examples, data_mode: 'snapshot', coverage_note: snapshot.coverage_note,
    cities: snapshot.airports.map(a => ({ city: a.city, airport: a.name, iata: a.iata })),
    dates: [...new Set(snapshot.coverage.map(c => c.date))], max_date_days: 7 };
}
