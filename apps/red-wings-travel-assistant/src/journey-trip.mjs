import { isoDate, datedTime } from './validation.mjs';

export const MODES = ['plane', 'train', 'suburban', 'bus', 'taxi', 'walk'];
const nullable = schema => ({ anyOf: [schema, { type: 'null' }] });
const str = maxLength => ({ type: 'string', minLength: 1, maxLength });
const object = properties => ({ type: 'object', properties, additionalProperties: false });
const place = object({ city: str(100), region: nullable(str(160)), place_id: nullable(str(120)), address: nullable(str(240)), node_id: nullable(str(120)) });
export const TRIP_PATCH_SCHEMA = object({
  network_mode: { enum: ['current', 'scenario_2027_2028'] },
  ground_preference: nullable({ enum: ['public', 'smart_transfer'] }),
  origin: place, destination: place,
  date_range: object({ from: str(10), to: str(10), meaning: { enum: ['unknown', 'departure_window', 'outbound_return'] } }),
  passengers: nullable({ type: 'integer', minimum: 1, maximum: 9 }),
  baggage: nullable(str(240)), requires_red_wings: { type: 'boolean' },
  selected_flight: nullable(object({ number: str(24), date: str(10), leg_id: nullable(str(120)) })),
  constraints: object({
    allow_taxi: nullable({ type: 'boolean' }), allow_overnight: nullable({ type: 'boolean' }),
    allow_night_travel: nullable({ type: 'boolean' }),
    modes: nullable({ type: 'array', items: { enum: MODES }, minItems: 1, maxItems: 6, uniqueItems: true }),
    departure_after: nullable(str(35)), arrive_by: nullable(str(35)),
    max_budget: nullable({ type: 'number', minimum: 0, maximum: 100000000 }),
  }),
});

// Validate the original arguments too: do not rely on a library's coercion or
// additional-property removal before a tool mutates the saved trip.
export function assertSchema(value, schema, path = 'arguments') {
  if (schema.anyOf) {
    if (schema.anyOf.some(s => { try { assertSchema(value, s, path); return true; } catch { return false; } })) return;
    throw new Error(`Некорректное поле ${path}`);
  }
  if (schema.enum) { if (!schema.enum.includes(value)) throw new Error(`Некорректное поле ${path}`); return; }
  const bad = () => { throw new Error(`Некорректное поле ${path}`); };
  if (schema.type === 'null') { if (value !== null) bad(); }
  else if (schema.type === 'object') {
    if (!value || typeof value !== 'object' || Array.isArray(value)) bad();
    for (const key of Object.keys(value)) {
      if (!Object.hasOwn(schema.properties, key)) bad();
      assertSchema(value[key], schema.properties[key], `${path}.${key}`);
    }
    if (schema.required?.some(k => !Object.hasOwn(value, k))) bad();
  } else if (schema.type === 'array') {
    if (!Array.isArray(value) || value.length < schema.minItems || value.length > schema.maxItems || (schema.uniqueItems && new Set(value).size !== value.length)) bad();
    value.forEach(v => assertSchema(v, schema.items, path));
  } else if (schema.type === 'string') {
    if (typeof value !== 'string' || value.trim().length < schema.minLength || value.length > schema.maxLength || /[\u0000-\u001f\u007f]/u.test(value)) bad();
  } else if (schema.type === 'boolean') { if (typeof value !== 'boolean') bad(); }
  else if (schema.type === 'number' || schema.type === 'integer') {
    if (!Number.isFinite(value) || (schema.type === 'integer' && !Number.isInteger(value)) || value < schema.minimum || value > schema.maximum) bad();
  }
}

export function emptyTrip() {
  return { network_mode: 'current', ground_preference: null, origin: null, destination: null, date_range: null, passengers: null, baggage: null,
    requires_red_wings: true, selected_flight: null,
    constraints: { allow_taxi: null, allow_overnight: null, allow_night_travel: null, modes: null,
      departure_after: null, arrive_by: null, max_budget: null } };
}

export function applyTripPatch(current, patch, { now = new Date() } = {}) {
  assertSchema(patch, TRIP_PATCH_SCHEMA);
  const next = structuredClone(current);
  for (const [key, value] of Object.entries(patch)) {
    next[key] = value && typeof value === 'object' && !Array.isArray(value) ? { ...next[key], ...value } : value;
  }
  for (const field of ['origin', 'destination']) {
    if (next[field] && !next[field].city) throw new Error(`Нужен город: ${field}`);
    if (patch[field]?.city && patch[field].city !== current[field]?.city) {
      if (!Object.hasOwn(patch[field], 'address')) next[field].address = null;
      if (!Object.hasOwn(patch[field], 'node_id')) next[field].node_id = null;
      if (!Object.hasOwn(patch[field], 'place_id')) next[field].place_id = null;
      if (!Object.hasOwn(patch[field], 'region')) next[field].region = null;
    }
  }
  const today = next.network_mode === 'scenario_2027_2028' ? '2027-01-01' : now.toISOString().slice(0, 10);
  const horizon = next.network_mode === 'scenario_2027_2028' ? '2028-12-31' : new Date(now.getTime() + 366 * 86400000).toISOString().slice(0, 10);
  const range = next.date_range;
  if (range) {
    if (!isoDate(range.from) || !isoDate(range.to) || range.from > range.to) throw new Error('Нужны обе существующие даты диапазона в правильном порядке.');
    if (range.from < today || range.to > horizon) throw new Error(`Поддерживается планирование с ${today} до ${horizon}; длина окна не ограничена семью днями.`);
    range.meaning ??= 'unknown';
  }
  for (const key of ['departure_after', 'arrive_by']) {
    if (next.constraints[key] !== null && !datedTime(next.constraints[key])) throw new Error(`Нужны дата, время и часовой пояс: ${key}`);
  }
  if (next.constraints.departure_after && next.constraints.arrive_by && Date.parse(next.constraints.departure_after) >= Date.parse(next.constraints.arrive_by)) throw new Error('Срок прибытия раньше допустимого выезда.');
  const fixed = next.selected_flight;
  if (fixed) {
    if (!fixed.number || !/^[\p{L}\d -]{2,24}$/u.test(fixed.number) || !isoDate(fixed.date)) throw new Error('Для сохранения выбранного рейса нужны номер и дата.');
    if (fixed.date < today || fixed.date > horizon) throw new Error('Дата выбранного рейса за горизонтом планирования.');
    // Preserve the selected flight; a conflicting edit is a question, not permission to replace it.
    if (range && (fixed.date < range.from || fixed.date > range.to)) throw new Error('Новый период не включает сохранённый рейс. Уточните, меняет ли пользователь рейс.');
  }
  return next;
}

export function missingTripFields(trip) {
  const missing = [];
  if (!trip.origin?.city) missing.push('origin.city');
  if (!trip.destination?.city) missing.push('destination.city');
  if (!trip.date_range) missing.push('date_range');
  else if (trip.date_range.meaning === 'unknown') missing.push('date_range.meaning');
  return missing;
}

export function departureRange(trip) {
  if (!trip.date_range || trip.date_range.meaning === 'unknown') return null;
  return { from: trip.date_range.from,
    to: trip.date_range.meaning === 'outbound_return' ? trip.date_range.from : trip.date_range.to };
}
