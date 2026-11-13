const boundedInteger = (value, fallback, min, max) => {
  if (value === undefined || value === '') return fallback;
  const n = Number(value);
  if (!Number.isInteger(n) || n < min || n > max) throw new Error('Invalid numeric configuration');
  return n;
};
export function loadConfig(env = process.env) {
  const scheduleMode = env.SCHEDULE_MODE || 'snapshot';
  if (!['snapshot', 'live'].includes(scheduleMode)) throw new Error('Invalid SCHEDULE_MODE');
  const config = {
    host: env.HOST || '127.0.0.1', port: boundedInteger(env.PORT, 3080, 0, 65535),
    publicOrigin: env.PUBLIC_ORIGIN || '', scheduleMode,
    yandexKey: env.YANDEX_RASP_API_KEY || '', yandexBase: env.YANDEX_RASP_BASE_URL || 'https://api.rasp.yandex-net.ru/v3.0/',
    yandexKeyFile: env.YANDEX_RASP_API_KEY_FILE || '', publicDirectory: env.PUBLIC_DIRECTORY || '',
    chatEnabled: env.ENABLE_CHAT === 'true',
    walkRoutingEnabled: env.ENABLE_OSM_WALK_ROUTING === 'true',
    llmEnabled: env.ENABLE_LLM === 'true', maiBase: env.MAI_BASE_URL || 'https://api-ai.mai.ru',
    maiModel: env.MAI_MODEL || '', maiKey: env.MAI_API_KEY || '', maiKeyFile: env.MAI_API_KEY_FILE || '',
    maiProtocol: env.MAI_PROTOCOL || '', maiPath: env.MAI_CHAT_PATH || '/v1/chat/completions',
    agentEngine: env.AGENT_ENGINE || 'pi', maiCAFile: env.MAI_CA_FILE || '',
    httpTimeout: boundedInteger(env.HTTP_TIMEOUT_MS, 10000, 100, 15000),
    llmTimeout: boundedInteger(env.LLM_TIMEOUT_MS, 120000, 100, 120000),
    maxOutputTokens: boundedInteger(env.MAX_OUTPUT_TOKENS, 4096, 512, 8192),
    maxLLMCalls: boundedInteger(env.MAX_LLM_CALLS, 20, 0, 1000),
    maxBodyBytes: 8192, maxConcurrentPlans: 4, maxConcurrentOutbound: 2,
    maxVariants: 3,
  };
  if (!['pi', 'direct'].includes(config.agentEngine)) throw new Error('Invalid AGENT_ENGINE');
  if (config.maiModel.length > 128 || /[\r\n\u0000]/.test(config.maiModel)) throw new Error('Invalid MAI_MODEL');
  if (config.publicOrigin && new URL(config.publicOrigin).origin !== config.publicOrigin) throw new Error('PUBLIC_ORIGIN must be an origin');
  return config;
}
