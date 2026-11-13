import { createHash } from 'node:crypto';
import { datedTime, isoDate } from './validation.mjs';
import { shiftLocalTime } from './time-utils.mjs';
import { excessiveAirportGround } from './route-policy.mjs';

const DAY = 86400000;
const PUBLIC = ['plane', 'train', 'suburban', 'bus'];
const GROUND = ['train', 'suburban', 'bus'];
const MODES = [...PUBLIC, 'taxi', 'walk'];
const BOOKING = 'https://flyredwings.com/booking/';
const BEFORE_PLANE = 120;
const AFTER_PLANE = 60;
const key = value => String(value ?? '').toLowerCase().replaceAll('ё', 'е').replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
const code = value => typeof value === 'string' && /^[cs]\d{1,12}$/.test(value);
const stationId = value => typeof value === 'string' ? value : value?.id ?? value?.code;
const rw = leg => Number(leg.carrier_code) === 617 && leg.carrier_iata === 'WZ';
const minutes = (a, b) => (Date.parse(b) - Date.parse(a)) / 60000;
const shiftDate = (date, days) => new Date(Date.parse(`${date}T12:00:00Z`) + days * DAY).toISOString().slice(0, 10);
const shiftTime = shiftLocalTime;
const groundQueryDate = (departure, date) => departure && isoDate(date) && Math.abs(Date.parse(departure.slice(0, 10)) - Date.parse(date)) <= DAY;
const hash = value => createHash('sha256').update(value).digest('hex').slice(0, 20);
const unique = values => [...new Set(values)];
const bounded = (value, fallback, max) => Number.isInteger(value) && value >= 0 ? Math.min(value, max) : fallback;
const abort = signal => { if (signal?.aborted) throw signal.reason instanceof Error ? signal.reason : new DOMException('Aborted', 'AbortError'); };
function url(value) {
  try { const u = new URL(value); return ['http:', 'https:'].includes(u.protocol) && !u.username && !u.password ? u.href : null; }
  catch { return null; }
}
function distance(a, b) {
  if (![a?.lat, a?.lon, b?.lat, b?.lon].every(Number.isFinite)) return null;
  const rad = n => n * Math.PI / 180;
  const h = Math.sin(rad(b.lat - a.lat) / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(rad(b.lon - a.lon) / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.min(1, Math.sqrt(h)));
}
function sameCity(station, place) {
  return station?.city_id === place.id || place.stations?.some(s => s.id === station?.id) ||
    (key(station?.city) === key(place.title) && Boolean(key(station?.city)) && (!station.region || !place.region || key(station.region) === key(place.region)));
}
function airportStop(stop, airport) {
  if (stop.id === airport.id || stop.airport_id === airport.id) return true;
  // A similarly named stop is still a distinct physical node. This only keeps
  // it as a feeder candidate; a transfer callback must connect the two nodes.
  if (!/аэропорт|airport/iu.test(stop.title ?? '')) return false;
  if (stop.city_id && airport.city_id && stop.city_id !== airport.city_id) return false;
  const names = [airport.title, airport.city].map(key).filter(Boolean);
  const title = key(stop.title);
  return names.some(name => name.split(' ').filter(t => t.length > 2 && !/^(аэропорт|airport|международный|international)$/.test(t)).some(t => title.split(' ').includes(t)));
}

function weekdaySet(value) {
  if (Array.isArray(value) && value.every(v => Number.isInteger(v) && v >= 1 && v <= 7)) return new Set(value.map(v => v % 7));
  if (typeof value !== 'string' || !value.trim()) return null;
  const s = key(value);
  if (/ежеднев|daily|every day/.test(s)) return new Set([0, 1, 2, 3, 4, 5, 6]);
  if (/^[01]{7}$/.test(value)) return new Set([...value].flatMap((v, i) => v === '1' ? [(i + 1) % 7] : []));
  const patterns = [/воскрес|\bвс\b|sunday|\bsun\b/u, /понедель|\bпн\b|monday|\bmon\b/u, /вторник|\bвт\b|tuesday|\btue\b/u,
    /сред|\bср\b|wednesday|\bwed\b/u, /четвер|\bчт\b|thursday|\bthu\b/u, /пятниц|\bпт\b|friday|\bfri\b/u, /суббот|\bсб\b|saturday|\bsat\b/u];
  // JS \b is ASCII-only: use token membership for Russian abbreviations.
  const short = ['вс', 'пн', 'вт', 'ср', 'чт', 'пт', 'сб'];
  const days = patterns.flatMap((p, i) => p.test(s) || s.split(' ').includes(short[i]) ? [i] : []);
  if (/будн|weekdays/.test(s)) return new Set([1, 2, 3, 4, 5]);
  if (/выходн|weekends/.test(s)) return new Set([0, 6]);
  return days.length ? new Set(days) : null;
}

// Calendars select GET dates, never manufacture a dated transport edge. Work is
// bounded by the number of samples, not by the length of the user's window.
function prospectiveDates(pattern, range, limit) {
  const calendar = pattern.published_calendar ?? {};
  const start = [range.from, pattern.published_start_date, calendar.start_date].filter(isoDate).sort().at(-1);
  const end = [range.to, pattern.published_end_date, calendar.end_date].filter(isoDate).sort()[0];
  if (start > end || !limit) return [];
  const list = Array.isArray(calendar) ? calendar : calendar.dates ?? pattern.dates;
  const explicit = Array.isArray(list) ? list.filter(isoDate) : [];
  const exceptions = calendar.excluded_dates ?? calendar.except_days;
  const excluded = new Set(Array.isArray(exceptions) ? exceptions.filter(isoDate) : []);
  const days = weekdaySet(pattern.published_days ?? calendar.days ?? calendar.weekdays);
  const valid = d => d >= start && d <= end && !excluded.has(d) && (!days || days.has(new Date(`${d}T12:00:00Z`).getUTCDay()));
  if (explicit.length) {
    const values = unique(explicit.filter(valid)).sort();
    return unique(Array.from({ length: Math.min(limit, values.length) }, (_, i) => values[Math.floor(i * (values.length - 1) / Math.max(1, Math.min(limit, values.length) - 1))]));
  }
  const span = Math.round((Date.parse(end) - Date.parse(start)) / DAY);
  const dates = [];
  for (let i = 0; i < limit; i++) {
    const anchor = shiftDate(start, Math.floor(i * span / Math.max(1, limit - 1)));
    // Search at most a week around each anchor, including the end of a window.
    for (let delta = 0; delta < 7; delta++) {
      const next = shiftDate(anchor, delta), prev = shiftDate(anchor, -delta);
      const found = [next, prev].find(d => valid(d) && !dates.includes(d));
      if (found) { dates.push(found); break; }
    }
  }
  return dates.sort();
}

function normalizeLeg(raw, stations, envelope = {}, defaults = {}) {
  const from = stationId(raw?.from) ?? defaults.from, to = stationId(raw?.to) ?? defaults.to;
  if (!code(from) || !code(to) || !from.startsWith('s') || !to.startsWith('s') || from === to || !MODES.includes(raw?.mode)) return null;
  const departure = datedTime(raw.departure), arrival = datedTime(raw.arrival);
  if (departure && arrival && Date.parse(arrival) <= Date.parse(departure)) return null;
  const sourceUrl = url(raw.source_url ?? envelope.source_url);
  const links = (raw.links ?? []).filter(l => l?.label && url(l.url)).map(l => ({ label: String(l.label), url: url(l.url) }));
  if (sourceUrl && !links.some(l => l.url === sourceUrl)) links.push({ label: 'Проверить расписание', url: sourceUrl });
  if (raw.mode === 'plane' && rw(raw) && !links.some(l => l.url === BOOKING)) links.push({ label: 'Проверить рейс и цену у Red Wings', url: BOOKING });
  return { ...raw, id: String(raw.id ?? hash([from, to, raw.mode, raw.number, departure].join('|'))), from, to,
    origin: String(raw.origin ?? stations.get(from)?.title ?? from), destination: String(raw.destination ?? stations.get(to)?.title ?? to),
    departure, arrival, duration_minutes: departure && arrival ? minutes(departure, arrival) : Number.isFinite(raw.duration_minutes) && raw.duration_minutes > 0 ? raw.duration_minutes : null,
    evidence_status: ['dated', 'published_pattern', 'indicative', 'unknown'].includes(raw.evidence_status) ? raw.evidence_status : 'unknown',
    price: null, source_name: raw.source_name ?? envelope.source_name ?? 'Расписание транспорта', source_url: sourceUrl,
    checked_at: raw.checked_at ?? envelope.checked_at ?? null, links };
}

function makePlan({ legs, gaps = [], trip, kind, variant }) {
  if (!legs.length || (kind === 'with_rw' && !legs.some(l => l.mode === 'plane' && rw(l)))) return { rejected: 'no_rw' };
  if (legs.some(l => l.mode === 'plane' && !rw(l))) return { rejected: 'unsupported_airline' };
  if (excessiveAirportGround(legs)) return { rejected: 'airport_ground_too_long' };
  if (kind !== 'with_rw' && legs.some(l => l.mode === 'plane' && rw(l))) return { rejected: 'baseline_contains_rw' };
  const c = trip.constraints ?? {}, warnings = [], connections = [], intervalChecks = [];
  let incomplete = false, timingComplete = true;
  const partial = (reason, affectsTime = true) => { incomplete = true; if (affectsTime) timingComplete = false; warnings.push(reason); };
  const fixed = trip.selected_flight;
  if (kind === 'with_rw' && fixed && !legs.some(l => key(l.number).replaceAll(' ', '').replace(/^ин/, 'wz') === key(fixed.number).replaceAll(' ', '').replace(/^ин/, 'wz') && l.departure?.slice(0, 10) === fixed.date && (!fixed.leg_id || l.id === fixed.leg_id))) return { rejected: 'selected_flight_not_preserved' };
  const range = trip.date_range.meaning === 'outbound_return' ? { from: trip.date_range.from, to: trip.date_range.from } : trip.date_range;
  const first = legs[0], last = legs.at(-1);
  if (first.departure && (first.departure.slice(0, 10) < range.from || first.departure.slice(0, 10) > range.to)) return { rejected: 'departure_outside_window' };
  if (c.departure_after && first.departure && Date.parse(first.departure) < Date.parse(c.departure_after)) return { rejected: 'departure_too_early' };
  if (c.arrive_by && last.arrival && Date.parse(last.arrival) > Date.parse(c.arrive_by)) return { rejected: 'arrival_too_late' };
  for (const l of legs) {
    if (((c.allow_taxi === false || trip.ground_preference === 'public') && l.mode === 'taxi') || (c.modes?.length && !c.modes.includes(l.mode))) return { rejected: 'mode_excluded' };
    const night = l.departure && l.arrival && (Number(l.departure.slice(11, 13)) < 6 || Number(l.departure.slice(11, 13)) >= 22 || Number(l.arrival.slice(11, 13)) < 6 || Number(l.arrival.slice(11, 13)) >= 22 || l.departure.slice(0, 10) !== l.arrival.slice(0, 10));
    if (c.allow_night_travel === false && night) return { rejected: 'night_travel_excluded' };
    if (!l.departure || !l.arrival || l.evidence_status !== 'dated' || !l.source_url) partial(`Участок ${l.origin} → ${l.destination}: датированное выполнение и источник подтверждены не полностью.`);
    if (trip.baggage && !l.baggage_note) partial(`Условия багажа на участке ${l.origin} → ${l.destination} не подтверждены.`, false);
    if (c.allow_night_travel === false && !l.departure) partial('Ночное время одного из участков не проверено.');
  }
  for (let i = 1; i < legs.length; i++) {
    const prev = legs[i - 1], next = legs[i];
    const minimum = (prev.mode === 'plane' ? AFTER_PLANE : 0) + (next.mode === 'plane' ? BEFORE_PLANE : 0);
    const available = prev.arrival && next.departure ? minutes(prev.arrival, next.departure) : null;
    if (available !== null && available < minimum) return { rejected: 'connection_too_short' };
    const connected = prev.to === next.from;
    if (!connected) partial(`Нет проверенного физического перехода: ${prev.destination} → ${next.origin}.`);
    if (available === null) partial(`Время пересадки ${prev.destination} → ${next.origin} подтверждено не полностью.`);
    const overnight = prev.arrival && next.departure && prev.arrival.slice(0, 10) !== next.departure.slice(0, 10);
    if (overnight && c.allow_overnight === false) return { rejected: 'overnight_excluded' };
    if (overnight || available > 300) warnings.push(`${overnight ? 'Ожидание до следующего дня' : 'Длительное ожидание'}: ${prev.destination} → ${next.origin}${available === null ? '' : `, ${Math.round(available)} мин`}.`);
    connections.push({ from_leg: prev.id, to_leg: next.id, status: connected && available !== null ? 'verified' : 'unknown', available_minutes: available, minimum_minutes: minimum,
      overnight: Boolean(overnight), long_wait: available !== null && available > 300,
      basis: minimum ? 'Минимум: 120 мин перед самолётом, 60 мин после прилёта; физический переход учитывается отдельно. Это не гарантия при задержках.' : 'Последовательность подтверждённых участков в одном узле.' });
  }
  // An indicative transfer can have only a sourced duration. Reject impossible
  // connections using that duration, but leave its timestamps and status unknown.
  for (let i = 0; i < legs.length - 2; i++) {
    if (!legs[i].arrival) continue;
    let j = i + 1, duration = 0;
    while (j < legs.length && (!legs[j].departure || !legs[j].arrival) && legs[j].physical_transfer) {
      if (legs[j].duration_minutes === null) { duration = null; break; }
      duration += legs[j++].duration_minutes;
    }
    if (j > i + 1 && duration !== null && legs[j]?.departure) {
      const after = legs[i].mode === 'plane' ? AFTER_PLANE : 0;
      const before = legs[j].mode === 'plane' ? BEFORE_PLANE : 0;
      const platform = ['train', 'suburban'].includes(legs[j].mode) ? 15 : 0;
      const minimum = duration + after + before + platform;
      const available = minutes(legs[i].arrival, legs[j].departure);
      if (available < minimum) return { rejected: 'connection_too_short' };
      const ready = shiftTime(legs[i].arrival, minimum);
      intervalChecks.push({ method: 'conservative_interval', ready_at: ready, departure_at: legs[j].departure,
        slack_minutes: available - minimum, interval_between_services_minutes: available,
        transport_duration_minutes: duration, post_arrival_buffer_minutes: after, pre_departure_buffer_minutes: before,
        platform_buffer_minutes: platform,
        explanation: `Между подтверждёнными перевозками ${available} мин: ${after} мин после прилёта, ${duration} мин на переезд/ожидание по источнику, ${before} мин перед вылетом и ${platform} мин на вход к платформе. Расчётная готовность ${ready.slice(11, 16)}, запас ${available - minimum} мин. Это оценка, не точное отправление наземного транспорта и не гарантия пересадки.` });
    }
  }
  for (const gap of gaps) partial(gap.reason);
  if (trip.origin.address) { gaps = [...gaps, { kind: 'first_mile', from: trip.origin.address, to: first.from, reason: `Путь от адреса ${trip.origin.address} до ${first.origin} не рассчитан.` }]; partial(gaps.at(-1).reason); }
  if (trip.destination.address) { gaps = [...gaps, { kind: 'last_mile', from: last.to, to: trip.destination.address, reason: `Путь от ${last.destination} до адреса ${trip.destination.address} не рассчитан.` }]; partial(gaps.at(-1).reason); }
  if (c.max_budget !== null && c.max_budget !== undefined) partial('Соблюдение бюджета не подтверждено: цены у перевозчиков неизвестны.', false);
  const status = incomplete ? 'partial' : 'verified';
  const sources = [...new Map(legs.flatMap(l => [l.source_url && { name: l.source_name, url: l.source_url, checked_at: l.checked_at }, ...l.links.map(v => ({ name: v.label, url: v.url, checked_at: l.checked_at }))]).filter(Boolean).map(s => [s.url, s])).values()];
  const inconvenient = connections.some(c => c.long_wait || c.overnight);
  const summary = incomplete ? 'Частичный кандидат: пересадки или подъезд не проверены полностью. Покупать билеты на всю цепочку до проверки нельзя.'
    : inconvenient ? 'Расписание стыкуется, но есть длительное ожидание или переход на следующий день. Сравните с базовым путём.'
      : 'Датированные участки стыкуются с минимальными буферами; наличие мест, цена и риск задержек требуют отдельной проверки.';
  if (incomplete) warnings.push('Не покупайте билеты на всю цепочку до проверки неизвестных участков и пересадок.');
  warnings.push('Расписание не подтверждает наличие мест. Цена уточняется у перевозчиков.');
  if (trip.date_range.meaning === 'outbound_return') warnings.push(`Рассчитан путь туда; обратная поездка ${trip.date_range.to} не проверена.`);
  return { id: hash(`${kind}:${legs.map(l => l.id).join('|')}:${gaps.map(g => g.kind).join('|')}`),
    title: `${kind === 'with_rw' ? 'Поездка с Red Wings' : 'Базовый путь без Red Wings'}: ${trip.origin.city} → ${trip.destination.city}`,
    status, network_mode: 'current', requires_red_wings: kind === 'with_rw', variant, summary, legs, gaps, connections, warnings: unique(warnings), sources,
    ...(intervalChecks.length ? { connection_checks: intervalChecks[0], interval_checks: intervalChecks } : {}),
    recommendation: { status: incomplete ? 'needs_validation' : inconvenient ? 'inconvenient' : 'schedule_checked' },
    connection_quality: { long_wait_count: connections.filter(c => c.long_wait).length, overnight_count: connections.filter(c => c.overnight).length,
      max_wait_minutes: Math.max(0, ...connections.map(c => c.available_minutes ?? 0)),
      total_wait_minutes: connections.reduce((sum, c) => sum + (c.available_minutes ?? 0), 0) },
    total_duration_minutes: timingComplete && !gaps.length ? minutes(first.departure, last.arrival) : null, total_price: null,
    reasonableness: { status: 'unknown', explanation: 'Нет сопоставимых полных датированных путей с одинаковыми конечными узлами.' } };
}

/** Live, bounded search of public feeder + one WZ flight + public onward.
 * config.maxRequests (default/max 24), maxChainRequests (default/max 2), airportLimit (default/max 5),
 * airportRadiusKm (default/max 450), datesPerRoute (default/max 3).
 * Calendars are research hints; only search(date) can supply a flight leg.
 * No HTTP, credentials, scenarios, fares or synthetic surface legs live here.
 */
export function createJourneySearch({ source, places, config = {}, transfer } = {}) {
  if (!source || !places || typeof source.search !== 'function' || typeof source.schedule !== 'function' || typeof places.resolve !== 'function' || typeof places.nearbyAirports !== 'function') throw new TypeError('source.search/schedule and places.resolve/nearbyAirports are required');
  const maxRequests = bounded(config.maxRequests, 24, 24);
  const airportLimit = Math.max(1, bounded(config.airportLimit, 5, 5));
  const radiusKm = Math.max(1, Math.min(Number.isFinite(config.airportRadiusKm) ? config.airportRadiusKm : 450, 450));
  const datesPerRoute = Math.max(1, bounded(config.datesPerRoute, 3, 3));
  const maxChainRequests = bounded(config.maxChainRequests, 2, 2);

  async function resolvePlaces(query, { signal } = {}) {
    abort(signal);
    const result = await places.resolve(query, { signal });
    abort(signal);
    return result;
  }

  async function search(trip, { signal } = {}) {
    abort(signal);
    const missing = [], excluded = {}, queries = [], stations = new Map(), resolutions = new Map(), queryCache = new Map(), transferCache = new Map(), accessCache = new Map(), sourceMap = new Map();
    const budget = { remaining: maxRequests };
    let exhausted = false, incompleteResponses = false, unexamined = 0, reserved = 0, chainRequests = 0;
    const availableRequests = () => Math.max(0, budget.remaining - reserved);
    const requested = trip?.date_range;
    const coverage = { requested_window: requested ? { ...requested } : null, departure_window: null,
      scope: 'До пяти аэропортов в радиусе 450 км; одно авиаплечо, прямые наземные участки и до двух запросов цепочек с пересадками. Проверенная пересадка требует одного физического узла либо отдельного переезда. Календарь только выбирает даты.',
      exhaustive: false, complete: false, queries, transfers: [], origin_airports: [], destination_airports: [], candidate_flight_dates: [], sampled_flight_dates: [], excluded };
    function finish(plans, status) {
      exhausted ||= budget.remaining === 0;
      coverage.request_budget = { limit: maxRequests, used: maxRequests - budget.remaining, remaining: budget.remaining, exhausted };
      coverage.unexamined_candidates = unexamined;
      coverage.queried_dates = unique(queries.filter(q => q.date).map(q => q.date)).sort();
      coverage.checked_dates = unique(queries.filter(q => q.date && q.status === 'ok' && q.complete).map(q => q.date)).sort();
      coverage.sampled_flight_dates = unique(queries.filter(q => q.date && q.kind === 'search' && q.modes.length === 1 && q.modes[0] === 'plane').map(q => q.date)).sort();
      coverage.incomplete_responses = incompleteResponses;
      coverage.chain_requests = { limit: maxChainRequests, used: chainRequests };
      coverage.actual_ground_departure_dates = unique(plans.flatMap(p => p.legs.filter(l => GROUND.includes(l.mode) && l.departure).map(l => l.departure.slice(0, 10)))).sort();
      for (const p of plans) for (const s of p.sources) sourceMap.set(s.url, s);
      return { status, ...(trip?.network_mode === 'scenario_2027_2028' ? {} : { network_mode: 'current' }), plans, sources: [...sourceMap.values()], missing_data: unique(missing), coverage };
    }
    if (trip?.network_mode === 'scenario_2027_2028') { missing.push('Сценарная сеть 2027–2028 обрабатывается отдельно от поиска действующего расписания.'); return finish([], 'partial'); }
    const fields = [];
    if (!trip?.origin?.city) fields.push('origin.city');
    if (!trip?.destination?.city) fields.push('destination.city');
    if (!requested || !isoDate(requested.from) || !isoDate(requested.to) || requested.from > requested.to) fields.push('date_range');
    else if (!['departure_window', 'outbound_return'].includes(requested.meaning)) fields.push('date_range.meaning');
    if (fields.length) { missing.push(...fields); return { ...finish([], 'needs_input'), missing_fields: fields }; }
    const range = { from: requested.from, to: requested.meaning === 'outbound_return' ? requested.from : requested.to };
    coverage.departure_window = range;
    coverage.window_days = Math.round((Date.parse(range.to) - Date.parse(range.from)) / DAY) + 1;
    if (requested.meaning === 'outbound_return') missing.push(`Обратная поездка ${requested.to} не проверена.`);

    function rememberStation(s, city) {
      if (!code(s?.id)) return null;
      const value = { ...stations.get(s.id), ...s };
      if (city) { value.city_id ??= city.id; value.city ??= city.title; value.region ??= city.region; }
      stations.set(value.id, value);
      return value;
    }
    async function resolve(query) {
      if (!resolutions.has(query)) resolutions.set(query, resolvePlaces(query, { signal }).catch(error => {
        abort(signal); incompleteResponses = true;
        missing.push(`Не удалось разрешить место «${query}»; это не отсутствие города или транспорта.`);
        return { status: 'unavailable', places: [] };
      }));
      const result = await resolutions.get(query);
      for (const p of result?.places ?? []) for (const s of p.stations ?? []) rememberStation(s, p);
      return result;
    }
    const placeQuery = p => code(p.place_id) ? p.place_id : p.region && !key(p.city).includes(key(p.region)) ? `${p.city}, ${p.region}` : p.city;
    const endpointResults = await Promise.all([resolve(placeQuery(trip.origin)), resolve(placeQuery(trip.destination))]);
    const resolved = endpointResults.map((r, i) => {
      if (r?.status === 'ok' && r.places?.length === 1) return r.places[0];
      // A saved node can disambiguate without discarding region information.
      const selected = r?.places?.filter(p => p.id === [trip.origin, trip.destination][i].node_id || p.stations?.some(s => s.id === [trip.origin, trip.destination][i].node_id));
      return selected?.length === 1 ? selected[0] : null;
    });
    if (resolved.some(p => !p || !code(p.id))) {
      endpointResults.forEach((r, i) => { if (!resolved[i]) missing.push(`${i ? 'destination' : 'origin'}.${r?.status === 'ambiguous' ? 'region' : 'city'}: ${r?.status ?? 'unavailable'}`); });
      const result = finish([], endpointResults.some(r => r?.status === 'unavailable') ? 'partial' : 'needs_input');
      result.place_choices = { origin: endpointResults[0], destination: endpointResults[1] };
      return result;
    }
    const [origin, destination] = resolved;
    coverage.resolved_places = resolved.map(p => ({ id: p.id, title: p.title, region: p.region ?? null }));
    async function airports(place) {
      let nearby = [];
      try { nearby = await places.nearbyAirports(place, { limit: airportLimit, radiusKm, signal }); abort(signal); }
      catch { abort(signal); incompleteResponses = true; missing.push(`Не полностью исследованы аэропорты рядом с ${place.title}.`); }
      return [...new Map([...(place.stations ?? []).filter(s => s.type === 'airport' && s.scheduled_catalog_candidate !== false), ...(Array.isArray(nearby) ? nearby : [])].map(s => [s.id, s])).values()]
        .filter(s => code(s.id) && (distance(place, s) === null || distance(place, s) <= radiusKm))
        .sort((a, b) => Number(sameCity(b, place)) - Number(sameCity(a, place)) || (distance(place, a) ?? Infinity) - (distance(place, b) ?? Infinity))
        .slice(0, airportLimit).map(s => rememberStation(s, (place.stations ?? []).some(v => v.id === s.id) ? place : null));
    }
    const [fromAirports, toAirports] = await Promise.all([airports(origin), airports(destination)]);
    coverage.origin_airports = fromAirports.map(s => s.id); coverage.destination_airports = toAirports.map(s => s.id);
    function addSource(value, name = 'Расписание транспорта', checkedAt = null) { const link = url(value); if (link) sourceMap.set(link, { name, url: link, checked_at: checkedAt }); }
    async function call(method, args) {
      const cacheKey = JSON.stringify([method, args]);
      if (queryCache.has(cacheKey)) return queryCache.get(cacheKey);
      abort(signal);
      if (budget.remaining <= 0) { exhausted = true; return { status: 'request_budget_exhausted', segments: [], complete: false }; }
      if (!availableRequests()) return { status: 'request_budget_reserved', segments: [], complete: false };
      const before = budget.remaining, allocated = availableRequests(), requestBudget = { remaining: allocated };
      let answer;
      try { answer = await source[method]({ ...args, signal, budget: requestBudget }); abort(signal); }
      catch { abort(signal); answer = { status: 'upstream_unavailable', segments: [], complete: false }; }
      // The adapter normally owns GET accounting. This fallback also bounds
      // injected adapters that do not decrement the shared budget themselves.
      budget.remaining = before - Math.min(allocated, Math.max(1, allocated - requestBudget.remaining));
      answer ??= { status: 'upstream_unavailable', segments: [], complete: false };
      const rows = answer.segments ?? answer.legs ?? [];
      queries.push({ kind: method, ...args, status: answer.status, complete: answer.complete === true, ...(answer.error_code ? { error_code: answer.error_code } : {}),
        count: Array.isArray(answer.chains) ? answer.chains.length : Array.isArray(answer.departures) ? answer.departures.length : Array.isArray(answer.stations) ? answer.stations.length : rows.length });
      if (answer.status !== 'ok' || answer.complete !== true) {
        incompleteResponses = true;
        if (answer.status === 'request_budget_exhausted') exhausted = true;
        missing.push(`Расписание ${args.station ?? `${args.from} → ${args.to}`} (${args.date ?? 'календарь'}) проверено не полностью: ${answer.status ?? 'unknown'}.`);
      }
      addSource(answer.source_url, answer.source_name, answer.checked_at);
      queryCache.set(cacheKey, answer);
      return answer;
    }
    async function registeredLeg(raw, envelope) {
      const leg = normalizeLeg(raw, stations, envelope);
      if (!leg) return null;
      for (const side of ['from', 'to']) {
        const id = leg[side], embedded = raw[`${side}_station`] ?? raw[side];
        if (typeof places.getStation === 'function' && !Number.isFinite(stations.get(id)?.lat)) {
          try { const s = await places.getStation(id, { signal }); abort(signal); if (s) rememberStation(s); }
          catch { abort(signal); }
        }
        rememberStation({ ...(typeof embedded === 'object' ? embedded : {}), id, title: side === 'from' ? leg.origin : leg.destination,
          ...(raw[`${side}_city_id`] ? { city_id: raw[`${side}_city_id`] } : {}) });
      }
      addSource(leg.source_url, leg.source_name, leg.checked_at);
      return leg;
    }
    async function rows(args) {
      const envelope = await call('search', args);
      const result = [];
      for (const raw of envelope.status === 'ok' ? envelope.segments ?? envelope.legs ?? [] : []) {
        const leg = await registeredLeg(raw, envelope);
        if (!leg || !args.modes.includes(leg.mode)) continue;
        // A train's query date can describe its starting station's date. Keep
        // the observed boarding instant (+/- one source day), never shift it.
        if (leg.evidence_status === 'dated' && (leg.mode === 'plane' ? leg.departure?.slice(0, 10) !== args.date : !groundQueryDate(leg.departure, args.date))) continue;
        result.push({ ...leg, source_query_date: args.date });
      }
      result.complete = envelope.status === 'ok' && envelope.complete === true;
      return result;
    }

    async function chainRows(args) {
      const result = [];
      const cacheKey = JSON.stringify(['searchChains', args]);
      if (typeof source.searchChains !== 'function' || (!queryCache.has(cacheKey) && (chainRequests >= maxChainRequests || !availableRequests()))) {
        result.complete = false; return result;
      }
      if (!queryCache.has(cacheKey)) chainRequests++;
      const envelope = await call('searchChains', args);
      for (const raw of envelope.status === 'ok' ? envelope.chains ?? [] : []) {
        if (!Array.isArray(raw.legs) || !raw.legs.length) continue;
        const legs = [];
        for (const rawLeg of raw.legs) legs.push(await registeredLeg(rawLeg, envelope));
        if (legs.some(l => !l || !args.modes.includes(l.mode) || !l.departure || !l.arrival || l.evidence_status !== 'dated') ||
          !groundQueryDate(legs[0].departure, args.date) ||
          (args.from.startsWith('s') && legs[0].from !== args.from) || (args.to.startsWith('s') && legs.at(-1).to !== args.to)) continue;
        const connected = [legs[0]], gaps = [];
        let rejected = false;
        for (let i = 1; i < legs.length; i++) {
          const prev = legs[i - 1], next = legs[i];
          if (Date.parse(next.departure) < Date.parse(prev.arrival)) { countRejection('connection_too_short'); rejected = true; break; }
          if (prev.to !== next.from) {
            const move = await physical(prev.to, next.from, prev.arrival);
            if (move?.rejected) { countRejection(move.rejected); rejected = true; break; }
            if (move) connected.push(move);
            else gaps.push({ kind: 'transfer', from: prev.to, to: next.from, reason: `Нет проверенного физического перехода ${prev.destination} → ${next.origin}.` });
          }
          connected.push(next);
        }
        if (!rejected) result.push({ legs: connected, gaps });
      }
      result.complete = envelope.status === 'ok' && envelope.complete === true;
      return result;
    }

    const routes = new Map();
    const boardDate = trip.selected_flight?.date ?? (range.from === range.to ? range.from : null);
    for (const from of fromAirports) {
      const envelope = await call('schedule', { station: from.id, modes: ['plane'], direction: 'departure',
        ...(boardDate ? { date: boardDate } : {}) });
      for (const hint of envelope.departures ?? envelope.segments ?? envelope.legs ?? []) {
        if (!rw(hint)) continue;
        if (trip.selected_flight && key(hint.number).replaceAll(' ', '').replace(/^ин/, 'wz') !==
          key(trip.selected_flight.number).replaceAll(' ', '').replace(/^ин/, 'wz')) continue;
        let targets = [];
        const toId = stationId(hint.to);
        if (toId) {
          let target = stations.get(toId);
          if (!target && typeof places.getStation === 'function') { try { target = await places.getStation(toId, { signal }); abort(signal); } catch { abort(signal); } }
          if (!target && hint.to_station) target = hint.to_station;
          if (target) targets = [rememberStation({ ...target, id: toId })];
        }
        if (!targets.length && hint.destination_query) {
          const resolvedHint = await resolve(hint.destination_query);
          if (resolvedHint?.status !== 'ok' || resolvedHint.places?.length !== 1) { missing.push(`Неоднозначный пункт назначения табло: ${hint.destination_query}.`); continue; }
          const city = resolvedHint.places[0];
          targets = (city.stations ?? []).filter(s => s.type === 'airport').map(s => rememberStation(s, city));
          if (!targets.length) targets = (await airports(city)).filter(s => sameCity(s, city));
        }
        for (const to of targets) {
          if (to.id === from.id) continue;
          const near = toAirports.some(s => s.id === to.id) || sameCity(to, destination) || (distance(to, destination) !== null && distance(to, destination) <= radiusKm);
          if (!near) continue;
          const routeKey = `${from.id}:${to.id}`;
          if (!routes.has(routeKey)) routes.set(routeKey, { from, to, hints: [] });
          routes.get(routeKey).hints.push(hint);
        }
      }
    }
    const routeList = [...routes.values()].sort((a, b) => (distance(origin, a.from) ?? Infinity) + (distance(destination, a.to) ?? Infinity) - (distance(origin, b.from) ?? Infinity) - (distance(destination, b.to) ?? Infinity));
    for (const route of routeList) {
      route.dates = trip.selected_flight ? [trip.selected_flight.date] : unique(route.hints.flatMap(h => prospectiveDates(h, range, datesPerRoute))).sort();
      // Multiple published threads must not multiply the per-route request cap.
      if (route.dates.length > datesPerRoute) route.dates = prospectiveDates({ published_calendar: route.dates }, range, datesPerRoute);
    }
    const tasks = [];
    for (let i = 0; i < datesPerRoute; i++) for (const route of routeList) if (route.dates[i]) tasks.push({ route, date: route.dates[i] });
    coverage.candidate_flight_dates = unique(tasks.map(t => t.date)).sort();
    coverage.calendar_routes = routeList.map(r => ({ from: r.from.id, to: r.to.id, validation_dates: r.dates }));
    if (coverage.window_days > datesPerRoute) missing.push('Длинное окно сохранено; проверяется выборка дат по календарям, все дни и все наземные пересадки не перебирались.');

    function endpoint(place, tripPlace) { return code(tripPlace.node_id) ? tripPlace.node_id : code(place.suggested_node_id) ? place.suggested_node_id : place.id; }
    const groundModes = GROUND.filter(m => !trip.constraints?.modes?.length || trip.constraints.modes.includes(m));
    async function airportAccess(airport) {
      if (accessCache.has(airport.id)) return accessCache.get(airport.id);
      if (code(airport.city_id)) await resolve(airport.city_id);
      const nearbyStop = s => s.id !== airport.id && s.type !== 'airport' &&
        (airportStop(s, airport) || (distance(s, airport) !== null && distance(s, airport) <= 1));
      let stops = [...stations.values()].filter(nearbyStop);
      if (!stops.length && typeof source.nearestStations === 'function' && [airport.lat, airport.lon].every(Number.isFinite)) {
        const answer = await call('nearestStations', { lat: airport.lat, lon: airport.lon, radiusKm: 1, modes: groundModes });
        stops = (answer.stations ?? []).map(s => rememberStation(s)).filter(s => s && nearbyStop(s));
      }
      const sorted = stops.sort((a, b) => (distance(a, airport) ?? Infinity) - (distance(b, airport) ?? Infinity));
      const distinctModes = [...new Map(sorted.map(s => [s.transport_type ?? s.type, s]).reverse()).values()];
      const result = [...new Map([...distinctModes, ...sorted].map(s => [s.id, s])).values()].slice(0, 2);
      accessCache.set(airport.id, result);
      return result;
    }
    async function physical(fromId, toId, notBefore) {
      if (fromId === toId) return null;
      const cacheKey = `${fromId}:${toId}:${notBefore}`;
      if (transferCache.has(cacheKey)) return transferCache.get(cacheKey);
      let leg = null;
      if (transfer && availableRequests() > 0) {
        const before = budget.remaining, allocated = availableRequests(), requestBudget = { remaining: allocated };
        try {
          const value = await transfer({ from: stations.get(fromId) ?? { id: fromId }, to: stations.get(toId) ?? { id: toId }, notBefore, signal, budget: requestBudget });
          abort(signal);
          const normalized = value && normalizeLeg(value, stations, {}, { from: fromId, to: toId });
          if (normalized && normalized.from === fromId && normalized.to === toId) {
            leg = normalized.departure && Date.parse(normalized.departure) < Date.parse(notBefore)
              ? { rejected: 'connection_too_short' } : { ...normalized, physical_transfer: true };
          }
        } catch { abort(signal); missing.push(`Источник физического перехода ${fromId} → ${toId} недоступен.`); }
        budget.remaining = before - Math.min(allocated, Math.max(1, allocated - requestBudget.remaining));
        coverage.transfers.push({ from: fromId, to: toId, not_before: notBefore, status: leg?.rejected ?? leg?.evidence_status ?? 'unknown' });
      } else if (transfer) { if (!budget.remaining) exhausted = true; return null; }
      transferCache.set(cacheKey, leg);
      return leg;
    }
    const countRejection = reason => { excluded[reason] = (excluded[reason] ?? 0) + 1; };
    async function surface(flight, from, to, side) {
      const before = side === 'before', place = before ? origin : destination, tripPlace = before ? trip.origin : trip.destination;
      const airport = before ? from : to;
      const exact = tripPlace.node_id === airport.id;
      if (exact) return [{ legs: [], gaps: [] }];
      const at = before ? flight.departure : flight.arrival;
      const local = sameCity(airport, place);
      const gap = () => ({ legs: [], gaps: [{ kind: local ? before ? 'first_mile' : 'last_mile' : before ? 'feeder' : 'onward', from: before ? endpoint(place, tripPlace) : airport.id, to: before ? airport.id : endpoint(place, tripPlace),
        reason: `Нет подтверждённого ${before ? 'подъезда' : 'продолжения пути'} ${before ? place.title : airport.title} → ${before ? airport.title : place.title}; время и физические переходы неизвестны.` }] });
      if (!at) return [gap()];
      if (!groundModes.length) { countRejection('mode_excluded'); return []; }
      const options = [];
      const comfortableSurface = option => {
        const scheduled = option.legs.filter(l => l.evidence_status === 'dated' && !l.physical_transfer && l.mode !== 'walk');
        const boundary = before ? scheduled.at(-1)?.arrival : scheduled[0]?.departure;
        if (!boundary) return false;
        const available = before ? minutes(boundary, flight.departure) : minutes(flight.arrival, boundary);
        const transferTime = option.legs.filter(l => l.physical_transfer).reduce((sum, l) => sum + (l.duration_minutes ?? 0), 0);
        const spare = available - (before ? BEFORE_PLANE : AFTER_PLANE) - transferTime;
        return boundary.slice(0, 10) === at.slice(0, 10) && spare >= 0 && spare <= 300;
      };
      const hasComfortableSurface = () => options.some(comfortableSurface);
      const hasConnectedSurface = () => options.some(option => option.gaps.length === 0 && comfortableSurface(option));
      let uncertain = false;
      const date = at.slice(0, 10);
      const searchDate = async d => {
        const a = before ? endpoint(place, tripPlace) : airport.id, b = before ? airport.id : endpoint(place, tripPlace);
        let found = await rows({ from: a, to: b, date: d, modes: groundModes });
        const alt = airport.city_id;
        // Search the airport city only when the station query yielded no usable
        // connection. A returned airport bus stop never causes a city excursion.
        const add = async (list, airportSide) => {
          uncertain ||= !list.complete || list.some(candidate => (candidate.legs ?? [candidate]).some(l => !l.departure || !l.arrival || l.evidence_status !== 'dated'));
          for (const candidate of list) {
            const ground = candidate.legs ?? [candidate];
            if (ground.some(l => !l.departure || !l.arrival || l.evidence_status !== 'dated') && !candidate.legs) continue;
            const first = ground[0], last = ground.at(-1), leg = before ? last : first;
            if (!first?.departure || !last?.arrival) continue;
            const outside = before ? first.departure.slice(0, 10) < range.from || first.departure.slice(0, 10) > range.to : false;
            const available = before ? minutes(last.arrival, flight.departure) : minutes(flight.arrival, first.departure);
            if (outside || available < (before ? BEFORE_PLANE : AFTER_PLANE)) { countRejection(outside ? 'departure_outside_window' : 'connection_too_short'); continue; }
            const atAirport = before ? leg.to : leg.from;
            const stop = stations.get(atAirport);
            // The city fallback can end at a city station. It is usable only via
            // an explicit physical transition, never an implicit zero-distance edge.
            const belongs = atAirport === airportSide || atAirport === airport.id || (stop && airportStop(stop, airport)) || (airport.city_id && stop?.city_id === airport.city_id);
            if (!belongs) continue;
            const firstNode = before ? first.from : last.to;
            rememberStation({ ...stations.get(firstNode), id: firstNode }, place);
            const transferLeg = atAirport === airport.id ? null : await physical(before ? atAirport : airport.id, before ? airport.id : atAirport, before ? leg.arrival : shiftTime(flight.arrival, AFTER_PLANE));
            if (transferLeg?.rejected) { countRejection(transferLeg.rejected); continue; }
            const gaps = [...(candidate.gaps ?? []), ...(atAirport === airport.id || transferLeg ? [] : [{ kind: 'transfer', from: before ? atAirport : airport.id, to: before ? airport.id : atAirport,
              reason: `Нет проверенного физического перехода ${before ? leg.destination : airport.title} → ${before ? airport.title : leg.origin}.` }])];
            const legList = before ? [...ground, ...(transferLeg ? [transferLeg] : [])] : [...(transferLeg ? [transferLeg] : []), ...ground];
            const probe = makePlan({ legs: before ? [...legList, flight] : [flight, ...legList], gaps, trip: { ...trip, selected_flight: null }, kind: rw(flight) ? 'with_rw' : 'baseline', variant: 'probe' });
            // The probe lacks the opposite side, so only connection feasibility
            // and mode restrictions are relevant at this stage.
            if (probe.rejected && ['connection_too_short', 'mode_excluded', 'night_travel_excluded', 'overnight_excluded'].includes(probe.rejected)) { countRejection(probe.rejected); continue; }
            options.push({ legs: legList, gaps });
          }
        };
        await add(found, airport.id);
        let stops = accessCache.get(airport.id) ?? [];
        if (!hasComfortableSurface() && availableRequests() > 0) {
          stops = await airportAccess(airport);
          for (const stop of stops) {
            if (availableRequests() <= 0) break;
            const local = await rows({ from: before ? endpoint(place, tripPlace) : stop.id, to: before ? stop.id : endpoint(place, tripPlace), date: d, modes: groundModes });
            await add(local, stop.id);
            if (hasComfortableSurface()) break;
          }
        }
        if (!hasComfortableSurface() && code(alt) && alt !== airport.id && alt !== place.id && availableRequests() > 0) {
          found = await rows({ from: before ? endpoint(place, tripPlace) : alt, to: before ? alt : endpoint(place, tripPlace), date: d, modes: groundModes });
          await add(found, alt);
        }
        // Only after direct alternatives failed, ask the upstream route search
        // for explicit details. No city-specific graph or invented ground edge.
        const reachedAirportStop = options.some(option => comfortableSurface(option) && option.gaps.length && option.gaps.every(gap =>
          gap.kind === 'transfer' && airportStop(stations.get(before ? gap.from : gap.to), airport)));
        if (!hasConnectedSurface() && !reachedAirportStop && typeof source.searchChains === 'function') {
          const targets = stops.length ? stops.map(s => s.id) : [airport.id, ...(code(alt) && alt !== place.id ? [alt] : [])];
          for (const target of unique(targets)) {
            const chains = await chainRows({ from: before ? endpoint(place, tripPlace) : target, to: before ? target : endpoint(place, tripPlace), date: d, modes: groundModes });
            await add(chains, target);
            if (hasConnectedSurface()) break;
          }
        }
      };
      await searchDate(date);
      // Query dates can differ from actual boarding dates (long-distance trains
      // including 373E). Window constraints apply to actual departures above.
      for (const offset of before ? [-1, 1] : [1, -1]) {
        if (options.length || !availableRequests()) break;
        await searchDate(shiftDate(date, offset));
      }
      if (options.length) return options.sort((a, b) => Number(comfortableSurface(b)) - Number(comfortableSurface(a)) || a.gaps.length - b.gaps.length || (before ? Date.parse(b.legs[0].departure) - Date.parse(a.legs[0].departure) : Date.parse(a.legs.at(-1).arrival) - Date.parse(b.legs.at(-1).arrival))).slice(0, 3);
      // Municipal access inside the user's endpoint city can remain an explicit
      // first/last-mile gap. A missing intercity feeder/onward is different.
      if (local || uncertain || !availableRequests()) return [gap()];
      missing.push(`В проверенные даты нет допустимого ${before ? 'подъезда к' : 'продолжения пути из'} ${airport.title}; цепочка исключена. Другие даты и сложные наземные маршруты не проверены.`);
      countRejection(before ? 'no_feasible_feeder' : 'no_feasible_onward');
      return [];
    }
    async function build(flight, from, to, kind, variant) {
      const before = await surface(flight, from, to, 'before'), after = await surface(flight, from, to, 'after');
      const plans = [];
      for (const a of before) for (const b of after) {
        const plan = makePlan({ legs: [...a.legs, flight, ...b.legs], gaps: [...a.gaps, ...b.gaps], trip, kind, variant });
        if (plan.rejected) countRejection(plan.rejected);
        else if (plan.legs.every(l => l.mode === 'plane') && plan.gaps.length) {
          countRejection('flight_only_with_missing_surface');
          missing.push(...plan.gaps.map(g => g.reason));
        } else plans.push(plan);
      }
      return plans;
    }

    const rwPlans = [], baseline = [], directRwFlights = [];
    const directDate = tasks[0]?.date ?? range.from;
    const directModes = PUBLIC.filter(m => !trip.constraints?.modes?.length || trip.constraints.modes.includes(m));
    if (directModes.length) {
      const direct = await rows({ from: endpoint(origin, trip.origin), to: endpoint(destination, trip.destination), date: directDate, modes: directModes });
      for (const l of direct) {
        if (l.mode === 'plane') {
          if (rw(l)) directRwFlights.push({ flight: l, from: stations.get(l.from), to: stations.get(l.to) });
          continue;
        }
        const plan = makePlan({ legs: [l], trip, kind: 'baseline', variant: 'all_transport_direct' });
        if (!plan.rejected) baseline.push(plan); else countRejection(plan.rejected);
      }
    }
    // Keep a small part of the same cap for the comparison; three WZ dates must
    // not consume the entire budget before any baseline access is examined.
    reserved = maxRequests >= 8 && !baseline.some(p => p.status === 'verified') ? Math.min(4, budget.remaining) : 0;
    coverage.baseline_reserved_requests = reserved;
    for (const { flight, from, to } of directRwFlights.slice(0, 3)) {
      if (from && to) rwPlans.push(...await build(flight, from, to, 'with_rw', 'public_with_rw'));
    }
    for (let i = 0; i < tasks.length; i++) {
      if (!availableRequests() || rwPlans.filter(p => p.status === 'verified').length >= 3) { unexamined += tasks.length - i; if (!budget.remaining) exhausted = true; break; }
      const { route, date } = tasks[i];
      const flights = await rows({ from: route.from.id, to: route.to.id, date, modes: ['plane'] });
      for (const flight of flights.filter(l => l.mode === 'plane' && l.from === route.from.id && l.to === route.to.id && l.departure && l.arrival).slice(0, 6)) {
        if (rw(flight)) rwPlans.push(...await build(flight, route.from, route.to, 'with_rw', 'public_with_rw'));
      }
    }
    reserved = 0;
    if (!baseline.some(p => p.variant === 'all_transport_direct') && groundModes.length && budget.remaining > 0) {
      const chains = await chainRows({ from: endpoint(origin, trip.origin), to: endpoint(destination, trip.destination), date: directDate, modes: groundModes });
      for (const chain of chains) {
        const plan = makePlan({ ...chain, trip, kind: 'baseline', variant: 'all_transport_connections' });
        if (plan.rejected) countRejection(plan.rejected); else baseline.push(plan);
      }
    }
    const order = (a, b) => Number(b.status === 'verified') - Number(a.status === 'verified') ||
      a.connection_quality.overnight_count - b.connection_quality.overnight_count || a.connection_quality.long_wait_count - b.connection_quality.long_wait_count || a.gaps.length - b.gaps.length ||
      (a.total_duration_minutes ?? Infinity) - (b.total_duration_minutes ?? Infinity) || a.connection_quality.total_wait_minutes - b.connection_quality.total_wait_minutes || a.legs.length - b.legs.length;
    const dedupe = plans => [...new Map(plans.sort(order).map(p => [p.id, p])).values()].sort(order);
    const chosenRW = dedupe(rwPlans).slice(0, 3), chosenBaseline = [];
    for (const variant of ['all_transport_direct', 'all_transport_connections']) {
      const plan = dedupe(baseline.filter(p => p.variant === variant))[0];
      if (plan) chosenBaseline.push(plan);
    }
    for (const p of chosenRW) {
      const comparable = chosenBaseline.find(b => p.status === 'verified' && b.status === 'verified' && p.total_duration_minutes !== null && b.total_duration_minutes !== null && p.legs[0].from === b.legs[0].from && p.legs.at(-1).to === b.legs.at(-1).to && p.legs[0].departure.slice(0, 10) === b.legs[0].departure.slice(0, 10));
      if (comparable && p.total_duration_minutes > comparable.total_duration_minutes) {
        p.reasonableness = { status: 'detour', baseline_plan_id: comparable.id,
          explanation: `На этой дате между теми же конечными узлами путь с RW дольше проверенного базового пути на ${Math.round(p.total_duration_minutes - comparable.total_duration_minutes)} мин. Цены и другие даты не сравнивались.` };
        p.summary = p.reasonableness.explanation;
        p.recommendation.status = 'compare_baseline';
      }
    }
    if (!chosenRW.length) missing.push('Не подтверждена подходящая цепочка с Red Wings; ограниченный поиск и недоступные ответы не доказывают отсутствие маршрута.');
    if (!chosenBaseline.length) missing.push('Наземный вариант для сравнения пока не подтверждён.');
    if (exhausted || budget.remaining === 0) missing.push('Бюджет запросов исчерпан; непроверенные направления и даты остаются неизвестными.');
    if (unexamined) missing.push('Часть перспективных рейсов/дат не проверена; показаны найденные варианты, поиск не исчерпывающий.');
    const plans = [...chosenRW, ...chosenBaseline];
    for (const p of plans) for (const g of p.gaps) missing.push(g.reason);
    return finish(plans, plans.length && plans.every(p => p.status === 'verified') && !missing.length && !incompleteResponses ? 'ok' : 'partial');
  }
  return { search, resolvePlaces };
}
