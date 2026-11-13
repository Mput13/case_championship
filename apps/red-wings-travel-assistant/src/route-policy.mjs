// Product default for this prototype: a flight should not require a 15-hour
// ground approach. This is a configurable-in-code planning bound, not a fact
// about carrier operations or a passenger guarantee.
export const MAX_AIRPORT_GROUND_MINUTES = 8 * 60;
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
