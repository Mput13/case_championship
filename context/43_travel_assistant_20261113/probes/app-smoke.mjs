import { createServer } from '../../../apps/red-wings-travel-assistant/server.mjs';
import { loadConfig } from '../../../apps/red-wings-travel-assistant/src/config.mjs';
import { once } from 'node:events';
import { writeFile } from 'node:fs/promises';
const config = loadConfig({ ...process.env, PORT: '0', SCHEDULE_MODE: 'snapshot', ENABLE_LLM: 'true', AGENT_ENGINE: 'pi', MAI_BASE_URL: 'https://api-ai.mai.ru', MAI_MODEL: 'deepseek-v4.1-flash', MAI_PROTOCOL: 'openai-chat-completions', MAI_CHAT_PATH: '/v1/chat/completions', MAX_LLM_CALLS: '2' });
const server = await createServer({ config });
server.listen(0, '127.0.0.1');
await once(server, 'listening');
const base = `http://127.0.0.1:${server.address().port}`;
const receipt = { checked_at: new Date().toISOString(), scope: 'Local HTTP API + live MAI Pi; saved schedules; not multimodal live E2E', model: config.maiModel, retries: 0 };
try {
  receipt.health = await (await fetch(base + '/api/health')).json();
  const examples = await (await fetch(base + '/api/examples')).json();
  receipt.request = examples.examples[0].request;
  const before = Date.now();
  const response = await fetch(base + '/api/plan', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(receipt.request) });
  receipt.http_status = response.status;
  receipt.elapsed_ms = Date.now() - before;
  receipt.response = await response.json();
  receipt.status = response.ok && receipt.response.status === 'ok' && receipt.response.assistant?.status === 'ok' ? 'completed' : 'incomplete';
  const html = await (await fetch(base)).text();
  receipt.ui_served = html.includes('Red Wings') && html.includes('/app.js');
  receipt.secret_not_served = (await fetch(base + '/.env')).status === 404;
  console.log(JSON.stringify({ status: receipt.status, http_status: receipt.http_status, variants: receipt.response.variants?.length, assistant: receipt.response.assistant, elapsed_ms: receipt.elapsed_ms, ui_served: receipt.ui_served, secret_not_served: receipt.secret_not_served }, null, 2));
} catch (error) { receipt.status = 'indeterminate'; receipt.error_class = error.constructor.name; console.log(JSON.stringify({ status: receipt.status, error_class: receipt.error_class })); }
finally { await new Promise(resolve => { server.closeAllConnections(); server.close(resolve); }); }
await writeFile(new URL('../receipts/app_pi_smoke.json', import.meta.url), JSON.stringify(receipt, null, 2) + '\n');
