import https from 'node:https';
import { Transform, Readable } from 'node:stream';
import { readFile } from 'node:fs/promises';
import { X509Certificate, createHash } from 'node:crypto';
import { ConnectorError } from './network.mjs';

const ROOT_SHA256 = 'd26d2d0231b7c39f92cc738512ba54103519e4405d68b5bd703e9788ca8ecf31';
export async function loadMaiCA(path) {
  if (!path) return undefined; // Normally trusted TLS remains the default.
  const pem = await readFile(path, 'utf8');
  if (pem.length > 16384 || createHash('sha256').update(new X509Certificate(pem).raw).digest('hex') !== ROOT_SHA256) throw new ConnectorError('invalid_mai_ca');
  return pem;
}
// This client has no network access outside the single documented MAI route.
export function scopedMaiFetch(ca, { onRequest = () => {}, maxBytes = 262144 } = {}) {
  const agent = new https.Agent({ ...(ca ? { ca } : {}), rejectUnauthorized: true, keepAlive: false });
  return async (input, init) => {
    const request = new Request(input, init);
    const url = new URL(request.url);
    if (url.origin !== 'https://api-ai.mai.ru' || url.pathname !== '/v1/chat/completions' || url.search || request.method !== 'POST') throw new ConnectorError('disallowed_endpoint');
    const body = Buffer.from(await request.arrayBuffer());
    if (body.length > 65536) throw new ConnectorError('request_too_large');
    onRequest();
    return new Promise((resolve, reject) => {
      const upstream = https.request(url, {
        method: 'POST', agent, signal: request.signal,
        headers: { ...Object.fromEntries(request.headers), 'accept-encoding': 'identity', 'content-length': String(body.length) },
      }, response => {
        if (response.statusCode >= 300 && response.statusCode < 400) { response.resume(); reject(new ConnectorError('redirect_rejected')); return; }
        let bytes = 0;
        const capped = new Transform({ transform(chunk, encoding, callback) {
          bytes += chunk.length;
          callback(bytes > maxBytes ? new ConnectorError('response_too_large', { indeterminate: true }) : null, bytes > maxBytes ? undefined : chunk);
        } });
        response.on('error', () => capped.destroy(new ConnectorError('network_error', { indeterminate: true })));
        capped.on('close', () => response.destroy());
        response.pipe(capped);
        const headers = new Headers();
        for (const [key, value] of Object.entries(response.headers)) if (value !== undefined) headers.set(key, Array.isArray(value) ? value.join(', ') : value);
        resolve(new Response(Readable.toWeb(capped), { status: response.statusCode, headers }));
      });
      upstream.setTimeout(30000, () => upstream.destroy(new ConnectorError('timeout', { indeterminate: true })));
      upstream.on('error', () => reject(new ConnectorError('network_error', { indeterminate: true })));
      upstream.end(body);
    });
  };
}
