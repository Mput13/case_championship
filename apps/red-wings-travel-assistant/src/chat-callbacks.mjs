import { MODES } from './journey-trip.mjs';
import { sourceUrl } from './journey-graph.mjs';
import { isRedWings } from './schedules.mjs';
import { excessiveAirportGround } from './route-policy.mjs';

// Callbacks are installed by server code, never named or supplied by a client
// or model. Abort races also release the session lock if an adapter ignores its
// signal; late results cannot write back into the session.
export async function abortable(promise, signal) {
  if (signal.aborted) throw new Error('aborted');
  let onAbort;
  const stopped = new Promise((_, reject) => {
    onAbort = () => reject(new Error('aborted'));
    signal.addEventListener('abort', onAbort, { once: true });
  });
  try { return await Promise.race([promise, stopped]); }
  finally { signal.removeEventListener('abort', onAbort); }
}

/** Trusted server journeySearch callback result, not an LLM tool argument.
 * {status:'ok'|'partial'|'needs_input', plans:Plan[], sources?:Source[],
 *  missing_data?:string[], ...coverage metadata}. Preserve its verified payload
 * and provenance; the search implementation owns route/transfer validation.
 */
export function acceptJourneyResult(value, trip) {
  if (!value || !Array.isArray(value.plans) || value.plans.length > 20 ||
      (value.status && !['ok', 'partial', 'needs_input'].includes(value.status))) throw new Error('invalid_journey_search_result');
  if (value.network_mode && value.network_mode !== trip.network_mode) throw new Error('mixed_network_modes');
  for (const p of value.plans) {
    if (!p || typeof p.id !== 'string' || typeof p.title !== 'string' || !['verified', 'partial', 'candidate'].includes(p.status) ||
        typeof p.requires_red_wings !== 'boolean' || !Array.isArray(p.legs) || !p.legs.length || p.legs.length > 20 || !Array.isArray(p.warnings) || !Array.isArray(p.sources)) throw new Error('invalid_journey_plan');
    for (const l of p.legs) if (!l || !MODES.includes(l.mode) || typeof l.origin !== 'string' || typeof l.destination !== 'string' ||
      !['dated', 'published_pattern', 'indicative', 'unknown'].includes(l.evidence_status)) throw new Error('invalid_journey_leg');
    if (p.legs.some(l => l.mode === 'plane' && !(trip.network_mode === 'scenario_2027_2028'
      ? l.carrier_iata === 'WZ' && (l.carrier_code == null || Number(l.carrier_code) === 617) : isRedWings(l)))) throw new Error('unsupported_airline');
    if (trip.network_mode === 'current' && excessiveAirportGround(p.legs)) throw new Error('airport_ground_too_long');
    for (const field of ['total_duration_minutes', 'total_price']) if (p[field] !== null && (!Number.isFinite(p[field]) || p[field] < 0)) throw new Error('invalid_journey_total');
    if ((p.network_mode && p.network_mode !== trip.network_mode) || p.legs.some(l => l.mode === 'plane' && l.network_mode && l.network_mode !== trip.network_mode)) throw new Error('mixed_network_modes');
    if (p.legs.some(l => (trip.constraints.allow_taxi === false || trip.ground_preference === 'public') && l.mode === 'taxi')) throw new Error('taxi_constraint_violated');
    if (trip.constraints.modes && p.legs.some(l => !trip.constraints.modes.includes(l.mode))) throw new Error('transport_constraint_violated');
    if (trip.selected_flight && p.requires_red_wings && !p.legs.some(l => l.mode === 'plane' &&
        String(l.number ?? '').toUpperCase().replace(/[\s-]/g, '').replace(/^ИН/, 'WZ') === trip.selected_flight.number.toUpperCase().replace(/[\s-]/g, '').replace(/^ИН/, 'WZ') &&
        l.departure?.slice(0, 10) === trip.selected_flight.date && (!trip.selected_flight.leg_id || l.id === trip.selected_flight.leg_id))) throw new Error('selected_flight_not_preserved');
    if (p.legs.some(l => l.links?.some(link => !sourceUrl(link.url)))) throw new Error('invalid_journey_link');
  }
  if (Buffer.byteLength(JSON.stringify(value)) > 200000) throw new Error('journey_search_result_too_large');
  const result = structuredClone({ ...value, status: value.status ?? (value.plans.length && value.plans.every(p => p.status === 'verified') ? 'ok' : 'partial') });
  for (const p of result.plans) {
    p.network_mode ??= trip.network_mode;
    if (trip.network_mode === 'scenario_2027_2028') {
      p.status = 'candidate'; p.network_label = 'Сценарный режим (сеть 2027–2028)';
      p.total_price = null; p.total_duration_minutes = null;
      p.warnings.push('Проектируемая сеть; действующее расписание и бронирование не подтверждены.');
      result.status = 'partial';
    }
    for (const l of p.legs) if (!l.links?.length) {
      l.links = sourceUrl(l.source_url) ? [{ label: 'Источник участка', url: sourceUrl(l.source_url) }] : [];
      p.warnings.push(`Нет подтверждённой ссылки на конкретное расписание/покупку: ${l.origin} → ${l.destination}.`);
    }
  }
  return result;
}
