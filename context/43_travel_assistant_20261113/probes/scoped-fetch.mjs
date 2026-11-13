import https from 'node:https';
import { Transform, Readable } from 'node:stream';

// Used only for the fixed MAI endpoint. Never a process-wide trust override.
export function scopedMaiFetch(ca, { onRequest = () => {}, maxBytes = 1048576 } = {}) {
  const agent = new https.Agent({ ca, rejectUnauthorized: true, keepAlive: false });
  return async (input, init) => {
    const request = new Request(input, init);
    const url = new URL(request.url);
    if (url.origin !== 'https://api-ai.mai.ru' || url.pathname !== '/v1/chat/completions' || url.search || request.method !== 'POST') throw new Error('MAI endpoint rejected');
    const body = Buffer.from(await request.arrayBuffer());
    if (body.length > 65536) throw new Error('MAI request too large');
    onRequest();
    return new Promise((resolve, reject) => {
      const upstream = https.request(url, {
        method: 'POST', agent, signal: request.signal,
        headers: { ...Object.fromEntries(request.headers), 'accept-encoding': 'identity', 'content-length': String(body.length) },
      }, response => {
        if (response.statusCode >= 300 && response.statusCode < 400) { response.resume(); reject(new Error('MAI redirect rejected')); return; }
        let bytes = 0;
        const capped = new Transform({ transform(chunk, encoding, callback) {
          bytes += chunk.length;
          callback(bytes > maxBytes ? new Error('MAI response too large') : null, bytes > maxBytes ? undefined : chunk);
        } });
        response.on('error', error => capped.destroy(error));
        capped.on('close', () => response.destroy());
        response.pipe(capped);
        const headers = new Headers();
        for (const [key, value] of Object.entries(response.headers)) if (value !== undefined) headers.set(key, Array.isArray(value) ? value.join(', ') : value);
        resolve(new Response(Readable.toWeb(capped), { status: response.statusCode, headers }));
      });
      upstream.setTimeout(30000, () => upstream.destroy(new Error('MAI request timeout')));
      upstream.on('error', reject);
      upstream.end(body);
    });
  };
}
