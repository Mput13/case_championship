export const LINK_HOSTS = new Set(['flyredwings.com', 'rasp.yandex.ru', 'yandex.ru']);
export function allowedLink(url) {
  const parsed = new URL(url);
  if (parsed.protocol !== 'https:' || parsed.username || parsed.password || parsed.port || !LINK_HOSTS.has(parsed.hostname)) throw new Error('Disallowed link');
  return parsed.href;
}
export function scheduleLink(from, to, date) {
  const url = new URL('https://rasp.yandex.ru/search/');
  url.search = new URLSearchParams({ fromId: from, toId: to, when: date });
  return allowedLink(url.href);
}
export function navigationLink(origin, destination, mode = 'auto') {
  const url = new URL('https://yandex.ru/maps/');
  url.search = new URLSearchParams({ rtext: `${origin}~${destination}`, rtt: mode === 'mt' ? 'mt' : 'auto' });
  return allowedLink(url.href);
}
export const bookingLink = () => allowedLink('https://flyredwings.com/booking/');
