export class ConnectorError extends Error {
  constructor(code, { indeterminate = false } = {}) { super(code); this.code = code; this.indeterminate = indeterminate; }
}
export function allowedEndpoint(value, hosts) {
  let url;
  try { url = new URL(value); } catch { throw new ConnectorError('invalid_endpoint'); }
  if (url.protocol !== 'https:' || !hosts.includes(url.hostname) || url.username || url.password || (url.port && url.port !== '443') || url.hash) throw new ConnectorError('disallowed_endpoint');
  return url;
}
export class Gate {
  #active = 0;
  constructor(limit) { this.limit = limit; }
  async run(fn) {
    if (this.#active >= this.limit) throw new ConnectorError('busy');
    this.#active++;
    try { return await fn(); } finally { this.#active--; }
  }
}
export async function fetchJson(url, { hosts, fetchImpl = fetch, method = 'GET', headers = {}, body, timeout = 10000, maxBytes = 1048576, signal } = {}) {
  const endpoint = allowedEndpoint(url, hosts);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  const abort = () => controller.abort();
  if (signal?.aborted) controller.abort();
  signal?.addEventListener('abort', abort, { once: true });
  let posted = false;
  try {
    if (controller.signal.aborted) throw new ConnectorError('aborted');
    // One attempt only, including POSTs whose server-side outcome is unknown.
    posted = method === 'POST';
    const response = await fetchImpl(endpoint, { method, headers, body, signal: controller.signal, redirect: 'error' });
    if (!response.ok) {
      await response.body?.cancel();
      throw new ConnectorError(response.status === 401 || response.status === 403 ? 'unauthorized' : 'http_error', { indeterminate: posted && response.status >= 500 });
    }
    const declared = Number(response.headers.get('content-length'));
    if (declared > maxBytes) { await response.body?.cancel(); throw new ConnectorError('response_too_large', { indeterminate: posted }); }
    if (!response.body) throw new ConnectorError('invalid_response', { indeterminate: posted });
    const reader = response.body.getReader();
    const chunks = [];
    let size = 0;
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        size += value.byteLength;
        if (size > maxBytes) { await reader.cancel(); throw new ConnectorError('response_too_large', { indeterminate: posted }); }
        chunks.push(Buffer.from(value));
      }
    } finally { reader.releaseLock(); }
    try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); }
    catch { throw new ConnectorError('invalid_response', { indeterminate: posted }); }
  } catch (error) {
    if (error instanceof ConnectorError) throw error;
    // Never propagate provider bodies, URL query strings, credentials or user text.
    throw new ConnectorError(controller.signal.aborted ? 'timeout' : 'network_error', { indeterminate: posted });
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', abort);
  }
}
