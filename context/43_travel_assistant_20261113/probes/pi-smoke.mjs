import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { scopedMaiFetch } from './scoped-fetch.mjs';

const app = new URL('../../../apps/red-wings-travel-assistant/', import.meta.url);
const { Agent } = await import(new URL('node_modules/@earendil-works/pi-agent-core/dist/index.js', app));
const { streamSimple } = await import(new URL('node_modules/@earendil-works/pi-ai/dist/api/openai-completions.js', app));
const receipt = JSON.parse(await readFile(new URL('../receipts/mai_tls_public.json', import.meta.url), 'utf8'));
const ca = receipt.scoped_trust.root_pem;
const { X509Certificate } = await import('node:crypto');
if (createHash('sha256').update(new X509Certificate(ca).raw).digest('hex') !== 'd26d2d0231b7c39f92cc738512ba54103519e4405d68b5bd703e9788ca8ecf31') throw new Error('Unexpected MAI CA');
const apiKey = (await readFile(process.env.MAI_API_KEY_FILE, 'utf8')).trim();
const snapshot = JSON.parse(await readFile(new URL('data/snapshot.json', app), 'utf8'));
const flight = snapshot.flights.find(f => f.carrier_iata === 'WZ' && f.arrival);
if (!flight) throw new Error('Verified fixture required');
const audit = { checked_at: new Date().toISOString(), package: '@earendil-works/pi-agent-core', version: '1.5.2', model: 'deepseek-v4.1-flash', status: 'started', http_requests: 0, model_calls: 0, tool_calls: [], usage: [], cost_status: 'unknown', max_model_calls: 2, max_output_tokens_per_call: 512, retries: 0 };
const transport = scopedMaiFetch(ca, { onRequest() { if (++audit.http_requests > 2) throw new Error('HTTP budget exceeded'); } });
const model = { id: audit.model, name: audit.model, api: 'openai-completions', provider: 'mai', baseUrl: 'https://api-ai.mai.ru/v1', reasoning: true, input: ['text'],
  contextWindow: 8192, maxTokens: 512, cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
  compat: { supportsStore: false, supportsDeveloperRole: false, supportsReasoningEffort: false, maxTokensField: 'max_tokens', supportsUsageInStreaming: true, thinkingFormat: 'deepseek', requiresReasoningContentOnAssistantMessages: true } };
const tool = { name: 'get_verified_flight', label: 'Проверенный рейс', description: 'Read one saved real Red Wings flight, not live availability.',
  parameters: { type: 'object', properties: {}, additionalProperties: false },
  execute: async () => { audit.tool_calls.push('get_verified_flight'); return { content: [{ type: 'text', text: JSON.stringify({ flight_number: flight.flight_number, departure: flight.departure, arrival: flight.arrival, data_mode: 'snapshot', price: null, availability: 'unknown' }) }], details: {} }; },
};
const agent = new Agent({ initialState: { model, tools: [tool], systemPrompt: 'This is an integration test. Call get_verified_flight exactly once. Then answer briefly in Russian with only the returned flight number and departure date, noting it is a saved schedule and price is unknown. Do not invent data.' },
  identity: { attribution: null }, toolExecution: 'sequential',
  streamFn: (m, context, options) => { audit.model_calls++; return streamSimple(m, context, { ...options, apiKey, fetch: transport, maxRetries: 0, timeoutMs: 25000, maxTokens: 512, temperature: 0, cacheRetention: 'none' }); },
  beforeToolCall: async ({ toolCall }) => toolCall.name !== tool.name || audit.tool_calls.length >= 1 ? { block: true, reason: 'Tool budget exceeded', terminate: true } : undefined,
  finishTurn: async () => audit.model_calls >= 2 ? { action: 'end' } : undefined,
});
agent.subscribe(event => {
  if (event.type === 'message_end' && event.message.role === 'assistant') {
    const usage = event.message.usage;
    audit.usage.push({ input: usage?.input, output: usage?.output, cacheRead: usage?.cacheRead, totalTokens: usage?.totalTokens, stop_reason: event.message.stopReason });
  }
});
const started = Date.now();
const timer = setTimeout(() => agent.abort(), 55000);
try {
  await agent.prompt('Проверь рейс через инструмент.');
  const last = [...agent.state.messages].reverse().find(m => m.role === 'assistant');
  audit.status = audit.tool_calls.length === 1 && audit.model_calls === 2 && last?.stopReason === 'stop' ? 'completed' : 'incomplete';
  audit.final_answer = last?.content.filter(b => b.type === 'text').map(b => b.text).join('');
} catch (error) { audit.status = 'indeterminate'; audit.error_class = error.constructor.name; }
finally { clearTimeout(timer); }
audit.elapsed_ms = Date.now() - started;
await writeFile(new URL('../receipts/mai_pi_tool_smoke.json', import.meta.url), JSON.stringify(audit, null, 2) + '\n');
console.log(JSON.stringify(audit, null, 2));
