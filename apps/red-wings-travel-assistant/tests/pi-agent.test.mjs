import test from 'node:test';
import assert from 'node:assert/strict';
import { createAssistantMessageEventStream } from '@earendil-works/pi-ai';
import { PiAgentAdapter } from '../src/pi-agent.mjs';
import { loadConfig } from '../src/config.mjs';
import { loadMaiCA, scopedMaiFetch } from '../src/mai-transport.mjs';
import { validateRequest } from '../src/validation.mjs';

const config = loadConfig({ ENABLE_LLM: 'true', MAI_MODEL: 'test-only', MAI_API_KEY: 'test-only-key', MAI_PROTOCOL: 'openai-chat-completions' });
const input = { request: { mode: 'trip', preference: 'balanced', origin_address: 'private-address' }, plan: { variants: [{}], data_mode: 'snapshot' } };
function response(model, content, { tokens = 20, stopReason = 'toolUse' } = {}) {
  const message = { role: 'assistant', content, api: model.api, provider: model.provider, model: model.id, timestamp: Date.now(), stopReason,
    usage: { input: 10, output: 10, cacheRead: 0, cacheWrite: 0, totalTokens: tokens, cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } } };
  const stream = createAssistantMessageEventStream();
  stream.push({ type: 'done', reason: stopReason, message });
  return stream;
}
const call = (name, args = {}, id = 'call-1') => ({ type: 'toolCall', id, name, arguments: args });

test('Pi executes only the two read/compose tools and renders server facts, not model text', async () => {
  let calls = 0;
  const adapter = new PiAgentAdapter(config, { streamFn: (model, context, options) => {
    calls++;
    assert.equal(options.maxRetries, 0);
    assert.equal(options.maxTokens, 512);
    assert(!JSON.stringify(context).includes('private-address'));
    return response(model, [calls === 1 ? call('get_trip_facts') : call('compose_summary', { fact_ids: ['ground', 'price'] }, 'call-2')]);
  } });
  const result = await adapter.explain(input);
  assert.equal(result.status, 'ok');
  assert.equal(calls, 2);
  assert.deepEqual(result.tool_calls, ['get_trip_facts', 'compose_summary']);
  assert.match(result.text, /дорогу до аэропорта/);
  assert.equal(result.cost_status, 'unknown');
  assert(!JSON.stringify(result).includes('test-only-key'));
});

test('unknown usage stops the automatic paid continuation after the first tool response', async () => {
  let calls = 0;
  const adapter = new PiAgentAdapter(config, { streamFn: model => { calls++; return response(model, [call('get_trip_facts')], { tokens: 0 }); } });
  assert.equal((await adapter.explain(input)).status, 'indeterminate');
  assert.equal(calls, 1);
});

test('fabricated fact IDs never reach the UI; the run cannot exceed two model calls', async () => {
  let calls = 0;
  const adapter = new PiAgentAdapter(config, { streamFn: model => {
    calls++;
    return response(model, [calls === 1 ? call('get_trip_facts') : call('compose_summary', { fact_ids: ['free-ticket-at-100-rub'] }, 'call-2')]);
  } });
  const result = await adapter.explain(input);
  assert.equal(result.status, 'indeterminate');
  assert.equal(calls, 2);
  assert(!result.text.includes('100'));
});

test('the process call cap prevents future provider requests, and disabled mode makes no requests', async () => {
  let calls = 0;
  const streamFn = model => { calls++; return response(model, [], { stopReason: 'stop' }); };
  const capped = new PiAgentAdapter({ ...config, maxLLMCalls: 0 }, { streamFn });
  assert.equal((await capped.explain(input)).status, 'indeterminate');
  const disabled = new PiAgentAdapter({ ...config, llmEnabled: false }, { streamFn });
  assert.equal((await disabled.explain(input)).status, 'disabled');
  assert.equal(calls, 0);
});

test('CA has the pinned public fingerprint and the MAI client rejects other destinations before dispatch', async () => {
  const ca = await loadMaiCA(new URL('../certs/russian-trusted-root.pem', import.meta.url));
  let calls = 0;
  const send = scopedMaiFetch(ca, { onRequest() { calls++; } });
  for (const url of ['https://evil.example/v1/chat/completions', 'http://api-ai.mai.ru/v1/chat/completions', 'https://api-ai.mai.ru/other', 'https://api-ai.mai.ru/v1/chat/completions?secret=anything']) {
    await assert.rejects(send(url, { method: 'POST', body: '{}' }), { code: 'disallowed_endpoint' });
  }
  assert.equal(calls, 0);
});

test('unsupported wishes are rejected instead of silently ignoring a user condition', () => {
  assert.throws(() => validateRequest({ mode: 'trip', origin: 'Самара', destination: 'Екатеринбург', date_from: '2026-12-08', date_to: '2026-12-08', message: 'Только после 18:00' }), /Свободные пожелания/);
});
