import http from 'node:http';
import { readFile, realpath, stat } from 'node:fs/promises';
import { resolve, sep, extname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadConfig } from './src/config.mjs';
import { DirectAgentAdapter } from './src/agent.mjs';
import { PiAgentAdapter } from './src/pi-agent.mjs';
import { loadSnapshot, SnapshotSchedules, LiveSchedules } from './src/schedules.mjs';
import { planTrip, getExamples } from './src/planner.mjs';
import { InputError } from './src/validation.mjs';
import { abortable } from './src/chat-callbacks.mjs';

const PUBLIC = fileURLToPath(new URL('./public/', import.meta.url));
const MIME = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon', '.woff2': 'font/woff2' };
function headers(res) {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Referrer-Policy', 'no-referrer');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; form-action 'self'");
}
function json(res, status, body) {
  if (res.destroyed) return;
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(body));
}
const failure = message => ({ status: 'error', data_mode: 'unavailable', message, variants: [], sources: [] });
async function readBody(req, max) {
  if (!/^application\/json(?:;|$)/i.test(req.headers['content-type'] || '')) throw new InputError('Нужен Content-Type: application/json.', 415);
  if (Number(req.headers['content-length']) > max) throw new InputError('Слишком большой запрос.', 413);
  let size = 0;
  const chunks = [];
  for await (const chunk of req.iterator({ destroyOnReturn: false })) {
    size += chunk.length;
    if (size > max) throw new InputError('Слишком большой запрос.', 413);
    chunks.push(chunk);
  }
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); }
  catch { throw new InputError('Некорректный JSON.'); }
}
async function staticFile(pathname, req, res, root) {
  let decoded;
  try { decoded = decodeURIComponent(pathname); } catch { throw new InputError('Некорректный путь.'); }
  if (decoded.includes('\0') || decoded.includes('\\') || decoded.split('/').some(part => part.startsWith('.'))) throw new InputError('Файл не найден.', 404);
  let base, path;
  try {
    base = await realpath(root);
    path = await realpath(resolve(base, `.${decoded === '/' ? '/index.html' : decoded}`));
  } catch { throw new InputError('Файл не найден.', 404); }
  if (!path.startsWith(`${base}${sep}`) || !MIME[extname(path)]) throw new InputError('Файл не найден.', 404);
  const info = await stat(path);
  if (!info.isFile() || info.size > 4 * 1024 * 1024) throw new InputError('Файл не найден.', 404);
  res.writeHead(200, { 'Content-Type': MIME[extname(path)], 'Content-Length': info.size });
  res.end(req.method === 'HEAD' ? undefined : await readFile(path));
}
function sameOrigin(req, config) {
  if (req.headers['sec-fetch-site'] === 'cross-site') return false;
  const origin = req.headers.origin;
  if (!origin) return true; // Non-browser clients; JSON and no CORS still required.
  if (config.publicOrigin) return origin === config.publicOrigin;
  try {
    const url = new URL(origin);
    return ['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname) && url.protocol === 'http:' && url.host === req.headers.host;
  } catch { return false; }
}
export async function createServer({ config = loadConfig(), snapshot = null, schedules = null, agent = null, chatService = null, publicRoot = PUBLIC } = {}) {
  snapshot ??= await loadSnapshot();
  schedules ??= config.scheduleMode === 'live' ? new LiveSchedules(config) : new SnapshotSchedules(snapshot);
  agent ??= config.agentEngine === 'pi' ? new PiAgentAdapter(config) : new DirectAgentAdapter(config);
  let active = 0, readActive = 0;
  let windowStart = Date.now(), requests = 0, readRequests = 0;
  const server = http.createServer(async (req, res) => {
    headers(res);
    try {
      if ((req.url?.length ?? 0) > 2048) throw new InputError('Слишком длинный URL.', 414);
      const url = new URL(req.url, 'http://localhost');
      // Versioned browser entry permits a new deployment to coexist with the
      // previous process while its existing conversations finish.
      if (url.pathname.startsWith('/api-v2/')) url.pathname = '/api/' + url.pathname.slice('/api-v2/'.length);
      if (url.pathname === '/api/health' && req.method === 'GET') return json(res, 200, {
        status: config.scheduleMode === 'live' && !(config.yandexKey || config.yandexKeyFile) ? 'degraded' : 'ok',
        ...agent.health(), schedule_mode: schedules.mode, schedule_configured: config.scheduleMode === 'snapshot' || Boolean(config.yandexKey || config.yandexKeyFile), chat_configured: Boolean(chatService),
      });
      if (url.pathname === '/api/examples' && req.method === 'GET') return json(res, 200, getExamples(snapshot));
      if (url.pathname === '/api/chat/examples' && req.method === 'GET') {
        if (!chatService) return json(res, 503, { status: 'error', message: 'Чат ещё не подключён.', examples: [] });
        return json(res, 200, await chatService.examples());
      }
      const manifest = url.pathname === '/api/demos' && req.method === 'GET';
      const control = req.method === 'GET' && ['/api/places', '/api/flights'].includes(url.pathname);
      if (manifest || control || (['/api/plan', '/api/chat', '/api/chat/start', '/api/chat/demo'].includes(url.pathname) && req.method === 'POST')) {
        const chat = url.pathname !== '/api/plan';
        const cheap = manifest || url.pathname === '/api/places' || url.pathname === '/api/chat/demo';
        if (!chat && chatService) throw new InputError('Используйте диалоговый поиск /api/chat.', 410);
        if (chat && !chatService) return json(res, 503, { status: 'error', message: 'Чат ещё не подключён.', reply: 'Чат ещё не подключён.', plans: [] });
        if (!control && url.search) throw new InputError('Параметры поиска передаются в JSON.');
        if (!sameOrigin(req, config)) throw new InputError('Запрос с другого сайта запрещён.', 403);
        if (Date.now() - windowStart >= 60000) { windowStart = Date.now(); requests = 0; readRequests = 0; }
        // QR audiences share this process. Local prepared seeds and suggestions
        // have their own finite budget; they never consume paid/search slots.
        if ((cheap ? readActive >= 64 || ++readRequests > 1200 : active >= config.maxConcurrentPlans || ++requests > 30)) {
          res.setHeader('Retry-After', '60'); throw new InputError('Слишком много запросов. Попробуйте позднее.', 429);
        }
        if (cheap) readActive++; else active++;
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), chat ? 225000 : 45000);
        const abort = () => { if (!res.writableEnded) controller.abort(); };
        res.on('close', abort);
        try {
          if (manifest) return json(res, 200, await chatService.demos());
          if (control) {
            const fields = url.pathname === '/api/places' ? ['q'] : ['from', 'date'];
            if ([...url.searchParams.keys()].some(k => !fields.includes(k)) || fields.some(k => url.searchParams.getAll(k).length !== 1)) throw new InputError('Некорректные параметры поиска.');
            const answer = await abortable(Promise.resolve().then(() => url.pathname === '/api/places'
              ? chatService.suggest(url.searchParams.get('q'), { signal: controller.signal })
              : chatService.flightOptions({ from: url.searchParams.get('from'), date: url.searchParams.get('date') }, { signal: controller.signal })), controller.signal);
            return json(res, 200, answer);
          }
          const body = await readBody(req, chat ? 16384 : config.maxBodyBytes);
          if (chat) {
            const method = url.pathname === '/api/chat/start' ? 'initialForm' : url.pathname === '/api/chat/demo' ? 'preparedDemo' : 'handle';
            const answer = await chatService[method](body, { signal: controller.signal });
            return json(res, answer.status === 'error' ? 502 : 200, answer);
          }
          const plan = await planTrip(body, { snapshot, schedules, agent, config, signal: controller.signal });
          return json(res, plan.status === 'error' ? 502 : 200, plan);
        } finally { clearTimeout(timer); res.off('close', abort); if (cheap) readActive--; else active--; }
      }
      if (url.pathname.startsWith('/api/')) throw new InputError('API-метод не найден.', 404);
      if (!['GET', 'HEAD'].includes(req.method)) throw new InputError('Метод не поддерживается.', 405);
      await staticFile(url.pathname, req, res, publicRoot);
    } catch (error) {
      // No request, address, message, provider response, path, key or stack logging.
      if (!res.headersSent) {
        if (error instanceof InputError && error.statusCode === 413) res.setHeader('Connection', 'close');
        json(res, error instanceof InputError ? error.statusCode : 500, failure(error instanceof InputError ? error.message : 'Внутренняя ошибка сервера.'));
      }
      else res.destroy();
    }
  });
  server.requestTimeout = 10000;
  server.headersTimeout = 10000;
  server.timeout = 240000;
  server.keepAliveTimeout = 5000;
  server.maxHeadersCount = 40;
  server.on('clientError', (_error, socket) => socket.end('HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n'));
  return server;
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const config = loadConfig();
    let chatService;
    if (config.chatEnabled) {
      const { createLiveChat } = await import('./src/chat-bootstrap.mjs');
      chatService = await createLiveChat({ config, snapshot: await loadSnapshot() });
    }
    const server = await createServer({ config, chatService, ...(config.publicDirectory ? { publicRoot: resolve(config.publicDirectory) } : {}) });
    server.on('error', () => { console.error('Server startup failed. Check bind configuration.'); process.exitCode = 1; });
    server.listen(config.port, config.host, () => console.log(JSON.stringify({ status: 'listening', port: server.address().port, schedule_mode: config.scheduleMode })));
  } catch { console.error('Server initialization failed. Check configuration and snapshot.'); process.exitCode = 1; }
}
