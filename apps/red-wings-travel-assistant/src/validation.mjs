export class InputError extends Error {
  constructor(message, statusCode = 400) { super(message); this.statusCode = statusCode; }
}
export const MAX_DATE_DAYS = 7;
export function isoDate(value) {
  if (typeof value !== 'string' || !/^20\d{2}-\d{2}-\d{2}$/.test(value)) return false;
  const n = Date.parse(`${value}T00:00:00Z`);
  return Number.isFinite(n) && new Date(n).toISOString().slice(0, 10) === value;
}
export function datedTime(value) {
  if (typeof value !== 'string' || !/^20\d{2}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,3})?(?:Z|[+-]\d\d:\d\d)$/.test(value)) return null;
  if (!isoDate(value.slice(0, 10)) || !Number.isFinite(Date.parse(value))) return null;
  const hours = Number(value.slice(11, 13));
  return hours < 24 && Number(value.slice(14, 16)) < 60 && Number(value.slice(17, 19)) < 60 ? value : null;
}
export const normalizeCity = value => value.trim().toLowerCase().replaceAll('ё', 'е').replace(/[–—]/g, '-').replace(/\s+/g, ' ');
export function flightNumber(value) {
  if (typeof value !== 'string') return null;
  const match = value.toUpperCase().replace(/[\s-]/g, '').match(/^(?:WZ|ИН)(\d{1,5})$/u);
  return match ? `WZ ${Number(match[1])}` : null;
}
export function datesBetween(from, to) {
  const result = [];
  for (let t = Date.parse(`${from}T00:00:00Z`); t <= Date.parse(`${to}T00:00:00Z`); t += 86400000) result.push(new Date(t).toISOString().slice(0, 10));
  return result;
}
function stringField(body, name, max, optional = false) {
  const value = body[name];
  if (optional && (value === undefined || value === '')) return '';
  if (typeof value !== 'string' || !value.trim() || value.length > max || /[\u0000-\u001f\u007f]/u.test(value)) throw new InputError(`Некорректное поле ${name}.`);
  return value.trim();
}
export function validateRequest(body) {
  if (!body || typeof body !== 'object' || Array.isArray(body)) throw new InputError('Нужен JSON-объект.');
  if (!['trip', 'flight'].includes(body.mode)) throw new InputError('Укажите режим trip или flight.');
  const result = { mode: body.mode, origin: stringField(body, 'origin', 100), destination: stringField(body, 'destination', 100) };
  if (normalizeCity(result.origin) === normalizeCity(result.destination)) throw new InputError('Города отправления и назначения должны различаться.');
  for (const name of ['date_from', 'date_to']) {
    if (!isoDate(body[name])) throw new InputError(`Нужна существующая дата YYYY-MM-DD в ${name}.`);
    result[name] = body[name];
  }
  const span = (Date.parse(result.date_to) - Date.parse(result.date_from)) / 86400000 + 1;
  if (span < 1 || span > MAX_DATE_DAYS) throw new InputError(`Диапазон должен содержать от 1 до ${MAX_DATE_DAYS} календарных дней.`);
  result.preference = body.preference ?? 'balanced';
  if (!['balanced', 'fastest', 'fewest_changes'].includes(result.preference)) throw new InputError('Неизвестное предпочтение.');
  for (const name of ['message', 'origin_address', 'destination_address']) result[name] = stringField(body, name, name === 'message' ? 1000 : 240, true);
  if (result.message) throw new InputError('Свободные пожелания пока не обрабатываются. Укажите города, даты и адреса в отдельных полях.');
  if (body.mode === 'flight') {
    result.flight_number = flightNumber(stringField(body, 'flight_number', 24));
    if (!result.flight_number) throw new InputError('Укажите номер Red Wings, например WZ 1034.');
    if (!isoDate(body.flight_date) || body.flight_date < result.date_from || body.flight_date > result.date_to) throw new InputError('Дата рейса должна попадать в выбранный период.');
    result.flight_date = body.flight_date;
  }
  return result;
}
