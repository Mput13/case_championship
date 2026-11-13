import test from 'node:test';
import assert from 'node:assert/strict';
import { createChatService } from '../src/chat-service.mjs';
import { fixtureConfig } from './journey-fixtures.test.mjs';

test('provider timeout aborts transport and returns without an automatic paid retry', async () => {
  let calls = 0, upstreamSignal;
  const service = createChatService({ config: { ...fixtureConfig, llmTimeout: 30 }, provider(_model, _context, options) {
    calls++; upstreamSignal = options.signal; return new Promise(() => {});
  } });
  const result = await service.handle({ message: 'Поищи' });
  assert.equal(result.error_code, 'provider_timeout'); assert.equal(result.usage.status, 'unknown'); assert(upstreamSignal.aborted);
  assert.equal((await service.handle({ message: 'Снова' })).error_code, 'usage_unknown_hold'); assert.equal(calls, 1);
});
