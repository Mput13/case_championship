import { readFile } from 'node:fs/promises';
import { emptyTrip, applyTripPatch, missingTripFields } from './journey-trip.mjs';
import { acceptJourneyResult } from './chat-callbacks.mjs';
import { sourceUrl } from './journey-graph.mjs';
import { datedTime, flightNumber } from './validation.mjs';

// The HTTP caller selects an ID, never a filename or URL. Loading is local and
// happens at bootstrap; opening a prepared example never consults a provider.
const FILES = Object.freeze({
  'feeder-flight': 'to_flight',
  'arrival-train': 'after_flight',
  'direct-flight': 'direct_flight',
  'scenario-transfer': 'scenario_partner',
});
const descriptions = {
  to_flight: 'Электрички до Кольцово и переход к рейсу Red Wings; часть переходов требует проверки.',
  after_flight: 'Рейс Red Wings, автобус из аэропорта и две электрички с разным запасом на пересадку.',
  direct_flight: 'Прямой рейс Red Wings между аэропортами, без лишних наземных участков.',
  scenario_partner: 'Сценарий сети 2027–2028: общественный транспорт и целевой шаттл на Ольхон.',
};
const record = v => v && typeof v === 'object' && !Array.isArray(v);
const text = (v, max = 4000) => typeof v === 'string' && v.trim().length > 0 && v.length <= max && !/[\u0000\u007f]/u.test(v);
const finite = n => Number.isFinite(n) && n >= 0;
const invalid = code => { throw new Error(`invalid_demo_${code}`); };
function keys(value, allowed, required = []) {
  if (!record(value) || Object.keys(value).some(k => !allowed.includes(k)) || required.some(k => !Object.hasOwn(value, k))) invalid('schema');
}
function provenance(value) {
  if (!record(value) && !Array.isArray(value)) return;
  for (const [key, item] of Object.entries(value)) {
    if (['url', 'source_url'].includes(key) && item !== null && !sourceUrl(item)) invalid('source_url');
    if (key === 'checked_at' && item !== null && !datedTime(item)) invalid('checked_at');
    if (item && typeof item === 'object') provenance(item);
  }
}
function sources(value) {
  if (!Array.isArray(value) || value.some(s => !record(s) || !text(s.name, 1000) || !sourceUrl(s.url) ||
      (s.checked_at != null && !datedTime(s.checked_at)))) invalid('sources');
}

function validateTimeline(plan, trip) {
  const legs = plan.legs;
  let anchor = null;
  let transferMinutes = 0;
  let incomplete = false;
  const ids = new Set();
  for (const leg of legs) {
    if (!text(leg.id, 120) || ids.has(leg.id) || !Array.isArray(leg.links) ||
        leg.links.some(link => !record(link) || !text(link.label, 500) || !sourceUrl(link.url))) invalid('leg_schema');
    ids.add(leg.id);
    if (leg.network_mode && leg.network_mode !== trip.network_mode) invalid('mixed_network');
    if (leg.data_mode && ![trip.network_mode === 'current' ? 'snapshot' : 'scenario'].includes(leg.data_mode)) invalid('mixed_data_mode');
    for (const field of ['duration_minutes', 'price']) if (leg[field] !== null && !finite(leg[field])) invalid('leg_number');
    const dated = leg.departure !== null || leg.arrival !== null;
    if (dated && (!datedTime(leg.departure) || !datedTime(leg.arrival) || Date.parse(leg.arrival) <= Date.parse(leg.departure))) invalid('timestamp');
    if (leg.evidence_status === 'dated' && (!dated || !text(leg.source_name, 1000) || !sourceUrl(leg.source_url) || !datedTime(leg.checked_at))) invalid('dated_evidence');
    if (dated && leg.duration_minutes !== null && Math.abs((Date.parse(leg.arrival) - Date.parse(leg.departure)) / 60000 - leg.duration_minutes) > 1) invalid('duration');
    if (trip.network_mode === 'current' && leg.mode === 'plane' &&
        (!dated || leg.evidence_status !== 'dated' || Number(leg.carrier_code) !== 617 || leg.carrier_iata !== 'WZ' || !flightNumber(leg.number))) invalid('rw_evidence');
    if (!dated) {
      incomplete = true;
      if (leg.duration_minutes !== null) {
        if (!sourceUrl(leg.source_url) || leg.evidence_status === 'unknown') invalid('transfer_source');
        transferMinutes += leg.duration_minutes;
      }
      continue;
    }
    if (anchor) {
      const available = (Date.parse(leg.departure) - Date.parse(anchor.arrival)) / 60000;
      // Count a sourced transfer even when it has no invented dated times.
      const minimum = (anchor.mode === 'plane' ? 60 : 0) + (leg.mode === 'plane' ? 120 : 0);
      if (available < transferMinutes + minimum) invalid('connection_buffer');
      if (trip.constraints.allow_overnight === false && leg.departure.slice(0, 10) > anchor.arrival.slice(0, 10)) invalid('overnight_constraint');
    }
    anchor = leg; transferMinutes = 0;
  }
  if (plan.requires_red_wings && !legs.some(l => l.mode === 'plane' && l.carrier_iata === 'WZ')) invalid('missing_rw');
  if (!plan.requires_red_wings && legs.some(l => l.mode === 'plane')) invalid('baseline');
  if (plan.status === 'verified' && (incomplete || legs.some(l => l.evidence_status !== 'dated') || plan.gaps?.length ||
      plan.connections?.some(c => c.status !== 'verified'))) invalid('unverified_chain');
  const first = legs[0], last = legs.at(-1);
  if (first.departure && (first.departure.slice(0, 10) < trip.date_range.from || first.departure.slice(0, 10) > trip.date_range.to)) invalid('trip_date');
  if (first.departure && trip.constraints.departure_after && Date.parse(first.departure) < Date.parse(trip.constraints.departure_after)) invalid('departure_constraint');
  if (last.arrival && trip.constraints.arrive_by && Date.parse(last.arrival) > Date.parse(trip.constraints.arrive_by)) invalid('arrival_constraint');
  if (plan.total_duration_minutes !== null && (!first.departure || !last.arrival ||
      Math.abs(plan.total_duration_minutes - (Date.parse(last.arrival) - Date.parse(first.departure)) / 60000) > 1)) invalid('total_duration');
}

// Remove authoring comments, not transport facts. The preparation/snapshot
// marker is structured response metadata rather than a fabricated model turn.
function passengerReply(reply) {
  return reply?.split(/(?<=[.!?])\s+/u).filter(sentence =>
    !/не ответ LLM|зарегистрированн\S* граф|продолж\S*.*(?:настоящ\S* чат|в чате)|дальнейшее обсуждение.*чате/iu.test(sentence)).join(' ').trim();
}
export function validateDemo(value, expectedId = value?.id) {
  keys(value, ['id', 'type', 'label', 'message', 'checked_at', 'data_mode', 'trip', 'result', 'verification', 'description'],
    ['id', 'type', 'label', 'message', 'checked_at', 'data_mode', 'trip', 'result']);
  if (!Object.hasOwn(FILES, expectedId) || value.id !== expectedId || value.type !== FILES[expectedId] ||
      !text(value.label, 240) || !text(value.message) || !datedTime(value.checked_at)) invalid('metadata');
  const scenario = value.type === 'scenario_partner';
  if (value.data_mode !== (scenario ? 'scenario' : 'snapshot') || value.trip?.network_mode !== (scenario ? 'scenario_2027_2028' : 'current')) invalid('mixed_network');
  const template = emptyTrip();
  keys(value.trip, Object.keys(template), Object.keys(template));
  keys(value.trip.constraints, Object.keys(template.constraints), Object.keys(template.constraints));
  // Snapshots remain readable after their travel date. Validate against their
  // preparation date; future edits in the live conversation use today's date.
  const trip = applyTripPatch(template, value.trip, { now: new Date(value.checked_at) });
  if (missingTripFields(trip).length) invalid('incomplete_trip');
  keys(value.result, ['status', 'network_mode', 'reply', 'plans', 'sources', 'missing_data'], ['status', 'plans']);
  if (value.result.reply !== undefined && !text(value.result.reply, 6000)) invalid('reply');
  if (!value.result.plans?.length || value.result.plans.length > 3) invalid('plans');
  if (value.result.sources !== undefined) sources(value.result.sources);
  if (value.result.missing_data !== undefined && (!Array.isArray(value.result.missing_data) || value.result.missing_data.some(s => !text(s)))) invalid('missing_data');
  const ids = new Set();
  for (const p of value.result.plans) {
    if (!p.requires_red_wings || !p.legs?.some(l => l.mode === 'plane' && l.carrier_iata === 'WZ')) invalid('missing_rw');
    if (!record(p) || !Array.isArray(p.legs) || !text(p.title, 500) || ids.has(p.id)) invalid('plan');
    if (!Array.isArray(p.warnings) || p.warnings.some(s => !text(s))) invalid('warnings');
    sources(p.sources);
    ids.add(p.id);
    if (scenario && (p.status !== 'candidate' || p.total_price !== null || p.total_duration_minutes !== null)) invalid('scenario_claim');
  }
  provenance(value.result);
  const result = acceptJourneyResult(value.result, trip);
  result.plans.forEach(p => validateTimeline(p, trip));
  // Never upgrade a partial source just because the arithmetic is consistent.
  if (result.plans.some(p => p.status !== 'verified')) result.status = 'partial';
  const label = /^[\w-]+$/u.test(value.label) ? `${trip.origin.city} → ${trip.destination.city}${scenario ? ' · сценарий 2027–2028' : ' · поезд и электричка'}` : value.label;
  result.reply = passengerReply(result.reply) || result.plans.map(p => p.summary || p.title).join(' ');
  return { id: value.id, label, type: value.type, checked_at: value.checked_at, data_mode: value.data_mode,
    description: descriptions[value.type], message: value.message, trip, result };
}

export function createDemoCatalogue(entries) {
  if (!Array.isArray(entries) || entries.length > Object.keys(FILES).length) invalid('catalogue');
  const demos = new Map();
  for (const entry of entries) {
    const demo = validateDemo(entry);
    if (demos.has(demo.id)) invalid('duplicate');
    demos.set(demo.id, demo);
  }
  return {
    list: () => ({ demos: [...demos.values()].map(({ id, label, type, checked_at, data_mode, description }) => ({ id, label, type, checked_at, data_mode, description })) }),
    get: id => typeof id === 'string' && demos.has(id) ? structuredClone(demos.get(id)) : null,
  };
}

export async function loadDemoCatalogue() {
  const entries = await Promise.all(Object.keys(FILES).map(async id => {
    const content = await readFile(new URL(`../data/demos/${id}.json`, import.meta.url), 'utf8');
    if (Buffer.byteLength(content) > 200000) invalid('size');
    const entry = JSON.parse(content);
    if (entry?.id !== id) invalid('metadata');
    return entry;
  }));
  return createDemoCatalogue(entries);
}
