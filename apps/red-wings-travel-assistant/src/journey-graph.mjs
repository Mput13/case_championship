import { createHash } from 'node:crypto';
import { datedTime, normalizeCity, isoDate } from './validation.mjs';
import { isRedWings } from './schedules.mjs';
import { MODES, departureRange, missingTripFields } from './journey-trip.mjs';
import { excessiveAirportGround } from './route-policy.mjs';

const evidenceLevels = ['dated', 'published_pattern', 'indicative', 'unknown'];
const key = value => normalizeCity(String(value ?? ''));
const finite = n => typeof n === 'number' && Number.isFinite(n) && n >= 0;
const text = (v, limit = 240) => typeof v === 'string' ? v.slice(0, limit) : null;
const numberKey = n => key(n).replace(/[\s-]/g, '').replace(/^ин/, 'wz');
export function sourceUrl(value) {
  try {
    const u = new URL(value);
    return ['http:', 'https:'].includes(u.protocol) && !u.username && !u.password ? u.href : null;
  } catch { return null; }
}
const source = leg => ({ name: leg.source_name, url: leg.source_url, checked_at: leg.checked_at ?? null });
export function collectSources(plans) {
  return [...new Map(plans.flatMap(p => p.sources ?? []).filter(s => s.url).map(s => [s.url, s])).values()];
}

// All transport edges come from server-owned data. There is deliberately no
// city-to-airport fallback, geocoder, model URL fetcher or synthesized timetable.
export function normalizeJourneyGraph(raw = {}, snapshot = {}) {
  const nodes = new Map(), legs = new Map(), issues = [];
  for (const n of raw.nodes ?? []) {
    if (!n?.id || !n.city || !n.title || !n.type || nodes.has(n.id)) { issues.push('invalid_or_duplicate_node'); continue; }
    nodes.set(n.id, { id: text(n.id, 120), city: text(n.city, 100), title: text(n.title), type: text(n.type, 40),
      address: text(n.address), iata: text(n.iata, 3), schedule_code: text(n.schedule_code, 80),
      min_transfer_minutes: finite(n.min_transfer_minutes) ? n.min_transfer_minutes : null,
      transfer_source_url: sourceUrl(n.transfer_source_url) });
  }
  for (const a of snapshot.airports ?? []) {
    const existing = [...nodes.values()].find(n => n.schedule_code === a.code || (n.iata && n.iata === a.iata) || n.id === a.code);
    if (existing) { existing.schedule_code ??= a.code; existing.iata ??= a.iata; }
    else if (a.code && a.city && a.name) nodes.set(a.code, { id: a.code, city: a.city, title: `${a.name} (${a.iata})`, type: 'airport', schedule_code: a.code, iata: a.iata, min_transfer_minutes: null });
  }
  const add = l => {
    if (!l?.id || legs.has(l.id) || !nodes.has(l.from) || !nodes.has(l.to) || l.from === l.to || !MODES.includes(l.mode)) { issues.push('invalid_or_duplicate_leg'); return; }
    if (l.mode !== 'plane' && [nodes.get(l.from), nodes.get(l.to)].some(n => n.type === 'city')) { issues.push(`city_placeholder_rejected:${l.id}`); return; }
    const url = sourceUrl(l.source_url);
    if (!url || !l.source_name || !evidenceLevels.includes(l.evidence_status)) { issues.push(`missing_leg_source:${l.id}`); return; }
    const departure = datedTime(l.departure), arrival = datedTime(l.arrival);
    if (departure && arrival && Date.parse(arrival) <= Date.parse(departure)) { issues.push(`invalid_leg_time:${l.id}`); return; }
    legs.set(l.id, { id: text(l.id, 120), from: l.from, to: l.to, mode: l.mode,
      origin: nodes.get(l.from).title, destination: nodes.get(l.to).title,
      carrier: text(l.carrier, 100), carrier_code: l.carrier_code ?? null, carrier_iata: text(l.carrier_iata, 3),
      number: text(l.number ?? l.flight_number, 40), departure, arrival,
      duration_minutes: departure && arrival ? (Date.parse(arrival) - Date.parse(departure)) / 60000 : finite(l.duration_minutes) ? l.duration_minutes : null,
      price: finite(l.price) ? l.price : null, currency: text(l.currency, 3), price_basis: ['person', 'party'].includes(l.price_basis) ? l.price_basis : null,
      evidence_status: l.evidence_status, source_name: text(l.source_name, 150), source_url: url, checked_at: text(l.checked_at, 40),
      links: (l.links ?? []).filter(v => sourceUrl(v?.url) && v.label).slice(0, 5).map(v => ({ label: text(v.label, 100), url: sourceUrl(v.url) })),
      network_mode: l.network_mode ?? raw.network_mode ?? 'current',
      min_connection_minutes: finite(l.min_connection_minutes) ? l.min_connection_minutes : null,
      valid_from: isoDate(l.valid_from) ? l.valid_from : null, valid_to: isoDate(l.valid_to) ? l.valid_to : null,
      overnight: typeof l.overnight === 'boolean' ? l.overnight : null,
      baggage_note: text(l.baggage_note), data_mode: text(l.data_mode, 30),
    });
    if (!legs.get(l.id).links.length) legs.get(l.id).links.push({ label: 'Источник участка', url });
  };
  for (const l of raw.legs ?? []) add(l);
  for (const f of snapshot.flights ?? []) {
    const from = [...nodes.values()].find(n => n.schedule_code === f.origin);
    const to = [...nodes.values()].find(n => n.schedule_code === f.destination);
    const s = (snapshot.sources ?? []).find(s => f.provenance?.some(p => p.source_id === s.id));
    if (!from || !to || !s || !datedTime(f.departure)) continue;
    add({ ...f, id: `snapshot:${f.id}`, from: from.id, to: to.id, mode: 'plane', number: f.flight_number,
      evidence_status: 'dated', source_name: s.name, source_url: s.url, checked_at: snapshot.checked_at, data_mode: snapshot.data_mode ?? 'snapshot' });
  }
  const corridors = [];
  for (const c of raw.corridors ?? []) {
    if (!c.id || !['with_rw', 'baseline'].includes(c.kind) || !Array.isArray(c.leg_ids) || !c.leg_ids.length || c.leg_ids.length > 10 || c.leg_ids.some(id => !legs.has(id))) { issues.push(`invalid_corridor:${c.id ?? '?'}`); continue; }
    const path = c.leg_ids.map(id => legs.get(id));
    if (key(nodes.get(path[0].from).city) !== key(c.origin_city) || key(nodes.get(path.at(-1).to).city) !== key(c.destination_city)) { issues.push(`corridor_endpoints_mismatch:${c.id}`); continue; }
    // Disconnected published corridors can still be inspected as partial, with
    // explicit gaps. Never turn a gap into a zero-minute transfer or a fake leg.
    corridors.push({ id: text(c.id, 120), origin_city: text(c.origin_city, 100), destination_city: text(c.destination_city, 100), leg_ids: [...c.leg_ids], kind: c.kind });
  }
  return { nodes, legs, corridors, issues, availability: raw.availability ?? (legs.size ? 'partial' : 'unavailable') };
}

function endpointCovered(place, node) {
  if (place.node_id && place.node_id !== node.id) return false;
  if (!place.address) return true;
  return [node.address, node.title].some(s => s && [key(place.address), key(`${place.city}, ${place.address}`)].includes(key(s)));
}
function nightTravel(l) {
  if (!l.departure || !l.arrival) return null;
  const dh = Number(l.departure.slice(11, 13)), ah = Number(l.arrival.slice(11, 13));
  return dh < 6 || dh >= 22 || ah < 6 || ah >= 22 || l.departure.slice(0, 10) !== l.arrival.slice(0, 10);
}
function flightMatches(leg, fixed) {
  return leg.mode === 'plane' && numberKey(leg.number) === numberKey(fixed.number) && leg.departure?.slice(0, 10) === fixed.date && (!fixed.leg_id || leg.id === fixed.leg_id);
}

export function validateCorridor(graph, legIds, trip, { kind = 'with_rw', id } = {}) {
  const legs = legIds.map(k => graph.legs.get(k));
  if (!legs.length || legs.some(l => !l)) return { rejected: 'missing_legs' };
  if (key(graph.nodes.get(legs[0].from).city) !== key(trip.origin?.city) || key(graph.nodes.get(legs.at(-1).to).city) !== key(trip.destination?.city)) return { rejected: 'trip_endpoints_mismatch' };
  const withRW = legs.some(l => l.mode === 'plane' && isRedWings(l) && l.evidence_status !== 'unknown');
  const scenario = trip.network_mode === 'scenario_2027_2028';
  if (legs.some(l => l.mode === 'plane' && l.network_mode !== trip.network_mode)) return { rejected: 'network_mode_mismatch' };
  if (kind === 'with_rw' && !withRW) return { rejected: 'no_confirmed_rw_segment' };
  if (legs.some(l => l.mode === 'plane' && !isRedWings(l))) return { rejected: 'unsupported_airline' };
  if (excessiveAirportGround(legs)) return { rejected: 'airport_ground_too_long' };
  if (kind === 'baseline' && withRW) return { rejected: 'baseline_contains_rw' };
  if (kind === 'with_rw' && trip.selected_flight && !legs.some(l => flightMatches(l, trip.selected_flight))) return { rejected: 'selected_flight_not_preserved' };
  const warnings = [], connections = [];
  const range = departureRange(trip), c = trip.constraints;
  let partial = false;
  for (const l of legs) {
    if (c.allow_taxi === false && l.mode === 'taxi') return { rejected: 'taxi_excluded' };
    if (trip.ground_preference === 'public' && l.mode === 'taxi') return { rejected: 'public_transport_required' };
    if (c.modes && !c.modes.includes(l.mode)) return { rejected: 'mode_excluded' };
    if (c.allow_night_travel === false && nightTravel(l) === true) return { rejected: 'night_travel_excluded' };
    if (c.allow_night_travel === false && nightTravel(l) === null) { partial = true; warnings.push(`Неизвестно, приходится ли ${l.number ?? l.id} на ночное время.`); }
    if (c.allow_overnight === false && l.overnight === true) return { rejected: 'overnight_excluded' };
    if (range && ((l.valid_from && l.valid_from > range.to) || (l.valid_to && l.valid_to < range.from))) return { rejected: 'outside_published_period' };
    if (!l.departure || !l.arrival || l.evidence_status !== 'dated') { partial = true; warnings.push(`Участок ${l.origin} → ${l.destination}: нет полного датированного расписания (${l.evidence_status}).`); }
    if (trip.baggage && !l.baggage_note) { partial = true; warnings.push(`Условия багажа на участке ${l.origin} → ${l.destination} не подтверждены.`); }
    if (nightTravel(l) === true) warnings.push(`Ночной участок или переход на следующие сутки: ${l.origin} → ${l.destination}.`);
    if (l.links.every(link => link.label === 'Источник участка')) warnings.push(`Для ${l.origin} → ${l.destination} есть источник; ссылка на конкретное расписание/покупку требует уточнения.`);
  }
  // A dated prefix may leave earlier than a flight. Never substitute the flight
  // date for the user's door-to-door departure window.
  const first = legs[0], last = legs.at(-1);
  if (range && first.departure && (first.departure.slice(0, 10) < range.from || first.departure.slice(0, 10) > range.to)) return { rejected: 'departure_outside_window' };
  if (range && !first.departure && legs.some(l => l.departure && l.departure.slice(0, 10) < range.from)) return { rejected: 'dated_leg_before_window' };
  if (trip.date_range?.meaning === 'outbound_return' && legs.some(l => l.arrival && l.arrival.slice(0, 10) > trip.date_range.to)) return { rejected: 'arrival_after_return_date' };
  if (c.departure_after && first.departure && Date.parse(first.departure) < Date.parse(c.departure_after)) return { rejected: 'departure_too_early' };
  if (c.arrive_by && last.arrival && Date.parse(last.arrival) > Date.parse(c.arrive_by)) return { rejected: 'arrival_too_late' };
  if ((c.departure_after && !first.departure) || (c.arrive_by && !last.arrival)) { partial = true; warnings.push('Не подтверждено соблюдение ограничения времени выезда/прибытия.'); }
  for (let i = 1; i < legs.length; i++) {
    const prev = legs[i - 1], next = legs[i], node = graph.nodes.get(prev.to);
    const connected = prev.to === next.from;
    const suppliedBuffer = next.min_connection_minutes ?? node.min_transfer_minutes ?? null;
    // Conservative product minima; they never cover a missing physical move.
    const policyBuffer = next.mode === 'plane' && prev.mode !== 'plane' ? 120 : prev.mode === 'plane' && next.mode !== 'plane' ? 60 : null;
    const buffer = connected ? policyBuffer !== null ? Math.max(policyBuffer, suppliedBuffer ?? 0) : suppliedBuffer : null;
    const bufferSource = next.min_connection_minutes !== null ? next.source_url : node.transfer_source_url;
    const bufferKnown = policyBuffer !== null || Boolean(bufferSource);
    const gap = prev.arrival && next.departure ? (Date.parse(next.departure) - Date.parse(prev.arrival)) / 60000 : null;
    if (gap !== null && (gap < 0 || (buffer !== null && gap < buffer))) return { rejected: 'connection_too_short' };
    if (!connected || buffer === null || !bufferKnown || gap === null) {
      partial = true;
      warnings.push(!connected ? `Нет проверенного перехода: ${prev.destination} → ${next.origin}.` : `Не проверен запас на пересадку в ${node.title}.`);
    }
    const nextDay = prev.arrival && next.departure && prev.arrival.slice(0, 10) !== next.departure.slice(0, 10);
    if (gap !== null && gap > 300) warnings.push(`Ожидание ${gap} мин. между ${prev.number ?? prev.id} и ${next.number ?? next.id} превышает 5 часов.`);
    if (nextDay) warnings.push(`Пересадка ${prev.destination} → ${next.origin} переходит на следующие сутки; нужна проверка ночного ожидания/ночёвки.`);
    if (c.allow_overnight === false && gap !== null && gap > 300 && nextDay) return { rejected: 'overnight_connection_excluded' };
    connections.push({ from_leg: prev.id, to_leg: next.id, status: connected && buffer !== null && bufferKnown && gap !== null ? 'verified' : 'unknown',
      available_minutes: gap, minimum_minutes: buffer, source_url: bufferSource ?? null,
      policy: policyBuffer === 120 ? '120 мин. до вылета на регистрацию/багаж, физический переезд отдельно.' : policyBuffer === 60 ? '60 мин. после прилёта на выход/багаж, физический переезд отдельно.' : null,
      long_wait: gap !== null && gap > 300, next_day: Boolean(nextDay) });
  }
  const endpointsComplete = endpointCovered(trip.origin, graph.nodes.get(first.from)) && endpointCovered(trip.destination, graph.nodes.get(last.to));
  if (!endpointCovered(trip.origin, graph.nodes.get(first.from))) warnings.push(`Не подтверждён путь от ${trip.origin.address ?? trip.origin.node_id} до ${first.origin}.`);
  if (!endpointCovered(trip.destination, graph.nodes.get(last.to))) warnings.push(`Не подтверждён путь от ${last.destination} до ${trip.destination.address ?? trip.destination.node_id}.`);
  if (!endpointsComplete) partial = true;
  const completeTime = endpointsComplete && connections.every(v => v.status === 'verified') && legs.every(l => l.evidence_status === 'dated' && l.departure && l.arrival);
  const completePrice = endpointsComplete && connections.every(v => v.status === 'verified') && legs.every(l => finite(l.price) && l.currency === 'RUB' && (l.price_basis === 'party' || (l.price_basis === 'person' && trip.passengers)));
  const totalPrice = completePrice ? legs.reduce((n, l) => n + l.price * (l.price_basis === 'person' ? trip.passengers : 1), 0) : null;
  if (c.max_budget !== null && totalPrice !== null && totalPrice > c.max_budget) return { rejected: 'over_budget' };
  if (c.max_budget !== null && totalPrice === null) { partial = true; warnings.push('Соблюдение бюджета не подтверждено: отсутствует полная цена для всех пассажиров.'); }
  if (totalPrice === null) warnings.push('Полная стоимость неизвестна; не для всех участков есть цена с валютой и единицей тарифа.');
  if (legs.some(l => l.data_mode === 'snapshot')) warnings.push('Рейсы из сохранённого снимка: актуальность, места и цена не подтверждены.');
  if (trip.date_range?.meaning === 'outbound_return') warnings.push(`Показан путь туда. Обратная поездка ${trip.date_range.to} пока не рассчитана.`);
  if (kind === 'baseline' && trip.selected_flight) warnings.push('Базовый путь для сравнения без RW; он не заменяет сохранённый рейс.');
  if (scenario) warnings.push('Сценарный режим (сеть 2027–2028): проектируемая сеть, не действующее расписание или наличие билетов.');
  const allWeak = legs.every(l => ['indicative', 'unknown'].includes(l.evidence_status));
  const sources = [...new Map([...legs.map(source), ...connections.filter(c => c.source_url).map(c => ({ name: 'Норматив пересадки', url: c.source_url }))].map(s => [s.url, s])).values()];
  return { id: id ?? createHash('sha256').update(`${kind}:${legIds.join('|')}`).digest('hex').slice(0, 16),
    title: `${kind === 'baseline' ? 'Базовый путь без Red Wings' : 'Путь с Red Wings'}: ${trip.origin.city} → ${trip.destination.city}`,
    status: scenario || allWeak ? 'candidate' : partial ? 'partial' : 'verified', requires_red_wings: kind === 'with_rw', network_mode: trip.network_mode,
    ...(scenario ? { network_label: 'Сценарный режим (сеть 2027–2028)' } : {}),
    legs: structuredClone(legs), connections, warnings: [...new Set(warnings)], sources,
    total_duration_minutes: !scenario && completeTime ? (Date.parse(last.arrival) - Date.parse(first.departure)) / 60000 : null,
    total_price: scenario ? null : totalPrice, currency: !scenario && totalPrice !== null ? 'RUB' : null,
    reasonableness: { status: 'unknown', explanation: 'Для вывода о разумности нужны сопоставимые полные пути и ограничения.' } };
}

function enumeratePaths(graph, trip) {
  const paths = [], adjacent = new Map();
  for (const l of graph.legs.values()) { if (!adjacent.has(l.from)) adjacent.set(l.from, []); adjacent.get(l.from).push(l); }
  let visits = 0;
  function walk(node, ids, seen) {
    if (++visits > 4000 || paths.length >= 150 || ids.length >= 8) return;
    for (const l of adjacent.get(node) ?? []) {
      if (seen.has(l.to)) continue;
      const next = [...ids, l.id];
      if (key(graph.nodes.get(l.to).city) === key(trip.destination.city)) paths.push(next);
      else walk(l.to, next, new Set([...seen, l.to]));
    }
  }
  for (const n of graph.nodes.values()) if (key(n.city) === key(trip.origin.city)) walk(n.id, [], new Set([n.id]));
  return { paths, truncated: visits > 4000 || paths.length >= 150 };
}

export function inspectCorridors(graph, trip) {
  const nodes = [...graph.nodes.values()].filter(n => [key(trip.origin?.city), key(trip.destination?.city)].includes(key(n.city)));
  const corridors = graph.corridors.filter(c => (!trip.origin || key(c.origin_city) === key(trip.origin.city)) && (!trip.destination || key(c.destination_city) === key(trip.destination.city)));
  return { availability: graph.availability, endpoint_nodes: nodes, corridors: corridors.map(c => ({ ...c,
    legs: c.leg_ids.map(id => graph.legs.get(id)) })),
    missing_data: [!nodes.some(n => key(n.city) === key(trip.origin?.city)) && 'Нет узлов/источников для города отправления.',
      !nodes.some(n => key(n.city) === key(trip.destination?.city)) && 'Нет узлов/источников для города назначения.',
      !corridors.length && 'Нет зарегистрированных коридоров для этой пары; можно проверить связные рёбра графа.'].filter(Boolean),
    data_issues: graph.issues.slice(0, 20),
    note: 'Отсутствие ребра в этом наборе не доказывает отсутствие рейсов или перевозчика в городе.' };
}

export function findJourneyOptions(graph, trip, { limit = 3 } = {}) {
  const missing = missingTripFields(trip);
  if (missing.length) return { status: 'needs_input', missing_fields: missing, plans: [] };
  const found = enumeratePaths(graph, trip);
  const explicit = graph.corridors.filter(c => key(c.origin_city) === key(trip.origin.city) && key(c.destination_city) === key(trip.destination.city));
  const unique = new Map();
  for (const path of [...explicit.map(c => c.leg_ids), ...found.paths]) unique.set(path.join('|'), path);
  const valid = [], excluded = {};
  for (const path of unique.values()) {
    const rw = path.some(id => { const l = graph.legs.get(id); return l.mode === 'plane' && isRedWings(l) && l.evidence_status !== 'unknown'; });
    const plan = validateCorridor(graph, path, trip, { kind: rw ? 'with_rw' : 'baseline' });
    if (plan.rejected) excluded[plan.rejected] = (excluded[plan.rejected] ?? 0) + 1;
    else valid.push(plan);
  }
  // Ordering is a transparent simplicity heuristic, never a fastest/cheapest claim.
  const order = (a, b) => ({ verified: 0, partial: 1, candidate: 2 }[a.status] - { verified: 0, partial: 1, candidate: 2 }[b.status]) ||
    a.legs.filter(l => l.mode === 'plane').length - b.legs.filter(l => l.mode === 'plane').length || a.legs.length - b.legs.length;
  const rw = valid.filter(p => p.requires_red_wings).sort(order), baseline = valid.filter(p => !p.requires_red_wings).sort(order);
  const plans = [...rw.slice(0, Math.max(1, limit - (baseline.length ? 1 : 0))), ...baseline.slice(0, 1)];
  for (const plan of plans.filter(p => p.requires_red_wings)) {
    const comparable = baseline.find(b => b.total_duration_minutes !== null && plan.total_duration_minutes !== null && b.status === 'verified' && plan.status === 'verified');
    if (comparable && plan.total_duration_minutes > comparable.total_duration_minutes && plan.legs.filter(l => l.mode === 'plane').length > comparable.legs.filter(l => l.mode === 'plane').length) {
      plan.reasonableness = { status: 'detour', explanation: `По этим датированным цепочкам требование RW добавляет перелёт и ${plan.total_duration_minutes - comparable.total_duration_minutes} мин. относительно ${comparable.id}. Цена и другие даты не сравнивались.` };
    }
  }
  const missingData = [];
  if (!rw.length && trip.requires_red_wings) missingData.push(trip.selected_flight ? 'Не найдена цепочка графа с сохранённым рейсом и допустимыми стыковками.' : 'В текущих данных нет полной подходящей цепочки с подтверждённым сегментом RW; это не доказательство отсутствия RW в городе.');
  if (!baseline.length) missingData.push('Нет сопоставимого базового пути без RW в текущем графе.');
  if (trip.date_range.meaning === 'outbound_return') missingData.push(`Обратный путь на ${trip.date_range.to} не рассчитан.`);
  if (!plans.length) missingData.push(...inspectCorridors(graph, trip).missing_data);
  return { status: plans.length && plans.every(p => p.status === 'verified') && !missingData.length ? 'ok' : 'partial', plans, missing_data: missingData,
    excluded, search_truncated: found.truncated, search_scope: 'Сохранённый граф; без проверки наличия мест. Порядок: доказательность, меньше перелётов и участков.',
    trip_date_range: structuredClone(trip.date_range) };
}
