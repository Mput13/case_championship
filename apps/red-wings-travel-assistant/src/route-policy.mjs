// Product default for this prototype: a flight should not require a 15-hour
// ground approach. This is a configurable-in-code planning bound, not a fact
// about carrier operations or a passenger guarantee.
export const MAX_AIRPORT_GROUND_MINUTES = 8 * 60;

// Ground-only paths inform ranking internally; passengers receive WZ journeys.
export function redWingsResult(result) {
  const plans = result.plans.filter(p => p.requires_red_wings === true && p.legs.some(l => l.mode === 'plane' &&
    l.carrier_iata === 'WZ' && (l.carrier_code == null || Number(l.carrier_code) === 617)) &&
    p.legs.every(l => l.mode !== 'plane' || l.carrier_iata === 'WZ' && (l.carrier_code == null || Number(l.carrier_code) === 617)));
  const sources = [...new Map(plans.flatMap(p => p.sources ?? []).map(s => [s.url, s])).values()];
  return { ...result, plans, sources, ...(plans.length ? {} : { status: 'needs_input',
    missing_data: ['Подберите другие даты или аэропорт для поездки с Red Wings.'] }) };
}
export function excessiveAirportGround(legs) {
  if (!legs.some(l => l.mode === 'plane')) return false;
  const groups = [[]];
  for (const leg of legs) {
    if (leg.mode === 'plane') groups.push([]);
    else groups.at(-1).push(leg);
  }
  return groups.some(group => {
    if (!group.length) return false;
    const knownDuration = group.reduce((sum, l) => sum + (Number.isFinite(l.duration_minutes) ? l.duration_minutes : 0), 0);
    const start = Date.parse(group[0].departure), end = Date.parse(group.at(-1).arrival);
    return knownDuration > MAX_AIRPORT_GROUND_MINUTES ||
      Number.isFinite(start) && Number.isFinite(end) && (end - start) / 60000 > MAX_AIRPORT_GROUND_MINUTES;
  });
}
