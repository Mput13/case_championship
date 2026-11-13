import test from 'node:test';
import assert from 'node:assert/strict';
import { createChatService } from '../src/chat-service.mjs';
import { fixtureConfig, respond, say } from './journey-fixtures.test.mjs';

test('cancel a dispatched provider ignoring abort: no hang, no retry, usage remains unknown', async () => {
  let entered, resolveProvider, calls = 0, upstreamSignal;
  const started = new Promise(resolve => { entered = resolve; });
  const service = createChatService({ config: fixtureConfig, async provider(model, context, options) {
    calls++; upstreamSignal = options.signal; entered();
    return new Promise(resolve => { resolveProvider = () => resolve(respond(model, [say('Late result must not enter history')])); });
  } });
  const controller = new AbortController();
  const pending = service.handle({ message: 'Начать' }, { signal: controller.signal });
  await started; controller.abort();
  const result = await pending;
  assert.equal(result.error_code, 'aborted'); assert.equal(result.usage.status, 'unknown'); assert(upstreamSignal.aborted);
  resolveProvider();
  const second = await service.handle({ session_id: result.session_id, message: 'Повторить' });
  assert.equal(second.error_code, 'usage_unknown_hold'); assert.equal(calls, 1);
  assert(!JSON.stringify(second).includes('Late result'));
});
