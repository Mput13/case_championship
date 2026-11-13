import { createAssistantMessageEventStream } from '@earendil-works/pi-ai';
import { streamSimple } from '@earendil-works/pi-ai/api/openai-completions';
import { readKey } from './agent.mjs';
import { loadMaiCA, scopedMaiFetch } from './mai-transport.mjs';

// Shared by every chat service/session in this Node process. Constructing a new
// service cannot reset MAX_LLM_CALLS or reconcile an unobserved paid response.
const ledger = { calls: 0, unknown: false };
export function processUsage() { return { calls: ledger.calls, unknown: ledger.unknown }; }
const zeroUsage = () => ({ input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0,
  cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } });
export function knownUsage(usage) {
  return usage && ['input', 'output', 'cacheRead', 'cacheWrite', 'totalTokens'].every(k => Number.isInteger(usage[k]) && usage[k] >= 0) && usage.totalTokens > 0;
}
export function chatModel(config) {
  return { id: config.maiModel || 'offline-injected-provider', name: config.maiModel || 'offline-injected-provider',
    api: 'openai-completions', provider: 'mai', baseUrl: 'https://api-ai.mai.ru/v1',
    reasoning: true, input: ['text'], contextWindow: 32768, maxTokens: config.maxOutputTokens ?? 4096,
    // Pi requires these numbers; they are not MAI financial receipts.
    cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
    compat: { supportsStore: false, supportsDeveloperRole: false, supportsReasoningEffort: false,
      maxTokensField: 'max_tokens', supportsUsageInStreaming: true, thinkingFormat: 'deepseek', requiresReasoningContentOnAssistantMessages: true } };
}

export async function prepareChatProvider(config, provider) {
  // Tests inject the Pi streamFn signature (function, or {streamFn}). No secret
  // or certificate is opened in that path. Production has one fixed endpoint.
  if (provider) {
    const streamFn = typeof provider === 'function' ? provider : provider.streamFn;
    if (typeof streamFn !== 'function') throw new Error('invalid_provider');
    return { streamFn, apiKey: undefined, transport: undefined };
  }
  if (config.maiBase?.replace(/\/$/, '') !== 'https://api-ai.mai.ru' || config.maiPath !== '/v1/chat/completions' || config.maiProtocol !== 'openai-chat-completions' || !config.maiModel) throw new Error('provider_not_configured');
  const apiKey = await readKey(config);
  const ca = await loadMaiCA(config.maiCAFile);
  return { streamFn: streamSimple, apiKey, ca };
}

export function boundedChatStream({ config, prepared, audit }) {
  return (model, context, options) => {
    const output = createAssistantMessageEventStream();
    const requestController = new AbortController();
    let done = false, reserved = false, timer;
    const fail = code => {
      if (done) return;
      done = true;
      audit.error ??= code;
      if (reserved) { ledger.unknown = true; audit.usage_unknown = true; }
      requestController.abort(); clearTimeout(timer); options.signal?.removeEventListener('abort', abort);
      const error = { role: 'assistant', content: [], api: model.api, provider: model.provider, model: model.id,
        timestamp: Date.now(), stopReason: options.signal?.aborted ? 'aborted' : 'error', errorMessage: code, usage: zeroUsage() };
      output.push({ type: 'error', reason: error.stopReason, error });
    };
    const abort = () => fail('aborted');
    if (options.signal?.aborted) { fail('aborted'); return output; }
    if (ledger.unknown) { fail('usage_unknown_hold'); return output; }
    if (ledger.calls >= (config.maxLLMCalls ?? 20)) { fail('process_call_budget'); return output; }
    if (audit.model_calls >= 3) { fail('turn_call_budget'); return output; }
    if (Buffer.byteLength(JSON.stringify(context)) > 55000) { fail('context_budget'); return output; }
    // Reservation happens synchronously before dispatch, including concurrent sessions.
    ledger.calls++; audit.model_calls++; reserved = true;
    options.signal?.addEventListener('abort', abort, { once: true });
    let requestCount = 0;
    const transport = prepared.transport ?? (prepared.apiKey ? scopedMaiFetch(prepared.ca, { onRequest() {
      if (++requestCount > 1) throw new Error('http_request_budget');
      audit.http_requests++;
    } }) : undefined);
    timer = setTimeout(() => fail('provider_timeout'), Math.min(config.llmTimeout ?? 120000, 120000));
    void (async () => {
      try {
        const upstream = await prepared.streamFn(model, context, { ...options, signal: requestController.signal, apiKey: prepared.apiKey,
          ...(transport ? { fetch: transport } : {}), maxRetries: 0, maxTokens: config.maxOutputTokens ?? 4096,
          timeoutMs: config.llmTimeout ?? 120000, temperature: 0.3, cacheRetention: 'none',
          ...(audit.model_calls === 3 ? { toolChoice: 'none' } : {}) });
        for await (const event of upstream) {
          if (done) break;
          if (event.type === 'done' || event.type === 'error') {
            const message = event.message ?? event.error;
            const known = knownUsage(message?.usage);
            audit.usage.push(known ? { input: message.usage.input, output: message.usage.output,
              cacheRead: message.usage.cacheRead, cacheWrite: message.usage.cacheWrite, totalTokens: message.usage.totalTokens } : null);
            if (!known) { ledger.unknown = true; audit.usage_unknown = true; audit.error ??= 'usage_unknown'; }
            if (known && message.usage.output > (config.maxOutputTokens ?? 4096)) audit.error ??= 'output_budget';
            if (!Array.isArray(message?.content) || JSON.stringify(message.content).length > 65000) { fail('invalid_model_response'); break; }
            if (!['stop', 'toolUse'].includes(message.stopReason)) audit.error ??= 'incomplete_model_response';
            // Do not relay provider error bodies, reasoning or arbitrary exception text.
            if (event.type === 'error') message.errorMessage = audit.error ?? 'provider_error';
            reserved = false; done = true;
          }
          output.push(event);
        }
        if (!done) fail('unobserved_response');
      } catch { fail('provider_error'); }
      finally { clearTimeout(timer); options.signal?.removeEventListener('abort', abort); }
    })();
    return output;
  };
}
