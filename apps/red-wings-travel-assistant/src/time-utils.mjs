// Keep the known local offset when shifting a timetable instant. Serializing
// everything as UTC changes displayed dates and can invent an overnight wait.
export function shiftLocalTime(value, amountMinutes) {
  const ms = Date.parse(value), suffix = String(value).match(/(Z|[+-]\d{2}:\d{2})$/u)?.[1];
  if (!Number.isFinite(ms) || !Number.isFinite(amountMinutes) || !suffix) return null;
  if (suffix === 'Z') return new Date(ms + amountMinutes * 60000).toISOString();
  const offsetMinutes = (Number(suffix.slice(1, 3)) * 60 + Number(suffix.slice(4))) * (suffix[0] === '+' ? 1 : -1);
  return new Date(ms + (amountMinutes + offsetMinutes) * 60000).toISOString().slice(0, -1) + suffix;
}
