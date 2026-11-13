import test from 'node:test';
import assert from 'node:assert/strict';
import { createChatService } from '../src/chat-service.mjs';
import { processUsage } from '../src/chat-provider.mjs';
import { fixtureConfig, respond, call, say, tripPatch } from './journey-fixtures.test.mjs';

test('three calls per user turn, including continuations; final call disables tools; zero retries', async () => {
  let count = 0;
  const service = createChatService({ config: fixtureConfig, provider(model, context, options) {
    count++; assert.equal(options.maxRetries, 0); assert.equal(options.maxTokens, 4096);
    if (count === 3) assert.equal(options.toolChoice, 'none');
    return respond(model, [call('inspect_corridors', {}, `call-${count}`)]);
  } });
  const result = await service.handle({ message: 'Осмотри данные' });
  assert.equal(count, 3); assert.equal(result.usage.model_calls, 3); assert.equal(result.error_code, 'turn_call_budget');
});

test('process call budget survives service recreation and charges a dispatched call only once', async () => {
  const cap = processUsage().calls + 1;
  let count = 0;
  const opts = { config: { ...fixtureConfig, maxLLMCalls: cap }, provider(model) { count++; return respond(model, [say('Уточните город.')]); } };
  await createChatService(opts).handle({ message: 'один' });
  const result = await createChatService(opts).handle({ message: 'два' });
  assert.equal(count, 1); assert.equal(result.error_code, 'process_call_budget');
});

test('pre-cancel and disabled configuration do not dispatch even an injected provider', async () => {
  let calls = 0;
  const provider = model => { calls++; return respond(model, [say('no')]); };
  assert.equal((await createChatService({ config: fixtureConfig, provider }).handle({ message: 'x' }, { signal: AbortSignal.abort() })).error_code, 'aborted');
  assert.equal((await createChatService({ config: { ...fixtureConfig, llmEnabled: false }, provider }).handle({ message: 'x' })).error_code, 'disabled');
  assert.equal(calls, 0);
});

test('cancellation of general search releases session; a late callback cannot overwrite cards', async () => {
  let entered, resolveSearch, calls = 0;
  const started = new Promise(resolve => { entered = resolve; });
  const service = createChatService({ config: fixtureConfig,
    journeySearch: async () => { entered(); return new Promise(resolve => { resolveSearch = resolve; }); },
    provider(model) { calls++; return respond(model, calls === 1 ? [call('update_trip', tripPatch), call('find_journey_options')] : [say('Контекст сохранён.')]); } });
  const controller = new AbortController();
  const pending = service.handle({ message: 'Найти путь' }, { signal: controller.signal });
  await started; controller.abort();
  const result = await pending; assert.equal(result.error_code, 'aborted'); assert.equal(calls, 1);
  resolveSearch({ status: 'ok', plans: [] });
  const next = await service.handle({ session_id: result.session_id, message: 'Продолжим обсуждение' });
  assert.notEqual(next.error_code, 'session_busy'); assert.equal(calls, 2); assert.deepEqual(next.plans, []);
});

test('a complete response above the former 1200-token cap is accepted with known usage', async () => {
  const service = createChatService({ config: fixtureConfig, provider(model, _context, options) {
    assert.equal(options.maxTokens, 4096); assert.equal(model.maxTokens, 4096);
    return respond(model, [say('Подробный ответ сохранён.')], { usage: { input: 40, output: 2200, cacheRead: 0, cacheWrite: 0, totalTokens: 2240 } });
  } });
  const result = await service.handle({ message: 'Разбери варианты' });
  assert.equal(result.reply_origin, 'llm'); assert.equal(result.error_code, undefined);
  assert.equal(result.usage.status, 'recorded'); assert.equal(result.usage.receipts[0].output, 2200);
});

test('unknown usage stops BEFORE tool mutation, blocks automatic continuation and future process calls', async () => {
  let calls = 0;
  const provider = model => { calls++; return respond(model, [call('update_trip', tripPatch)], { usage: null }); };
  const service = createChatService({ config: fixtureConfig, provider });
  const result = await service.handle({ message: 'Найди путь' });
  assert.equal(calls, 1); assert.equal(result.error_code, 'usage_unknown'); assert.equal(result.trip.origin, null);
  assert.deepEqual(result.tool_events, []); assert.equal(result.usage.status, 'unknown');
  const next = await createChatService({ config: fixtureConfig, provider }).handle({ message: 'Повтори' });
  assert.equal(next.error_code, 'usage_unknown_hold'); assert.equal(calls, 1);
});
