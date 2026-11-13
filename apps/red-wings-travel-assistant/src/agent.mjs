import { open } from 'node:fs/promises';
import { ConnectorError, Gate, fetchJson, allowedEndpoint } from './network.mjs';
const MAI_HOSTS = ['api-ai.mai.ru'];
const fallback = 'Варианты собраны по расписанию. Цены и наличие мест неизвестны; наземную дорогу и запас до регистрации нужно проверить отдельно.';

export async function readKey(config) {
  if (config.maiKey) return config.maiKey;
  let file;
  try {
    file = await open(config.maiKeyFile, 'r');
    const info = await file.stat();
    if (!info.isFile() || info.size > 8192) throw new Error();
    const key = (await file.readFile('utf8')).trim();
    if (!key || /[\r\n]/.test(key)) throw new Error();
    return key;
  } catch { throw new ConnectorError('credential_unavailable'); }
  finally { await file?.close(); }
}
// Port for a future Pi adapter: health() and explain({request, plan, signal}).
// No route generation, tool execution, filesystem access or shell capability is exposed to a model.
export class DirectAgentAdapter {
  constructor(config, { fetchImpl = fetch } = {}) { this.config = config; this.fetchImpl = fetchImpl; this.gate = new Gate(1); }
  health() {
    const c = this.config;
    const configured = Boolean(c.maiModel && (c.maiKey || c.maiKeyFile) && c.maiProtocol === 'openai-chat-completions');
    return { model_configured: configured, generation_enabled: c.llmEnabled, ...(configured ? { model: c.maiModel } : {}) };
  }
  async explain({ request, plan, signal }) {
    const c = this.config;
    if (!c.llmEnabled) return { status: 'disabled', text: fallback };
    if (!this.health().model_configured) return { status: 'not_configured', text: fallback };
    const facts = [
      { id: 'scope', text: `Подтверждены ${plan.variants.length} варианта с прямым рейсом Red Wings; каждый дополнен рекомендациями наземной дороги.` },
      { id: 'source', text: plan.data_mode === 'snapshot' ? 'Использован сохранённый снимок расписания, не live-проверка.' : 'Получен live-ответ расписания; наличие мест не проверено.' },
      { id: 'price', text: 'Цена билета и полная стоимость поездки неизвестны.' },
      { id: 'ground', text: 'Время наземной дороги и запас до регистрации требуют отдельной проверки.' },
      { id: 'duration', text: 'Общая длительность поездки неизвестна, поскольку наземные участки не рассчитаны.' },
    ];
    try {
      return await this.gate.run(async () => {
        const base = allowedEndpoint(c.maiBase, MAI_HOSTS);
        if (!base.pathname.endsWith('/')) base.pathname += '/';
        const url = allowedEndpoint(new URL(c.maiPath, base).href, MAI_HOSTS);
        if (url.search) throw new ConnectorError('invalid_endpoint');
        const key = await readKey(c);
        const answer = await fetchJson(url.href, { hosts: MAI_HOSTS, method: 'POST', fetchImpl: this.fetchImpl, timeout: c.llmTimeout, maxBytes: 65536, signal,
          headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ model: c.maiModel, stream: false, max_tokens: 256, temperature: 0,
            messages: [{ role: 'system', content: 'Select the most useful factual reminders for the given preference. Return only JSON {"fact_ids":[...]}, 1 to 5 unique IDs from the supplied facts. No new facts, prose, links, tools or bookings.' },
              // Deliberately exclude addresses and free-text messages from provider data.
              { role: 'user', content: JSON.stringify({ preference: request.preference, mode: request.mode, facts }) }] }) });
        const choice = answer?.choices?.[0];
        if (choice?.finish_reason !== 'stop' || choice.message?.tool_calls || typeof choice.message?.content !== 'string') throw new ConnectorError('invalid_model_response', { indeterminate: true });
        let selection;
        try { selection = JSON.parse(choice.message.content); } catch { throw new ConnectorError('invalid_model_response', { indeterminate: true }); }
        if (!selection || Object.keys(selection).join(',') !== 'fact_ids' || !Array.isArray(selection.fact_ids) || !selection.fact_ids.length || selection.fact_ids.length > 5 || new Set(selection.fact_ids).size !== selection.fact_ids.length || selection.fact_ids.some(id => !facts.some(f => f.id === id))) throw new ConnectorError('invalid_model_response', { indeterminate: true });
        // Only server-authored facts reach the UI. Arbitrary model text/URLs never do.
        return { status: 'ok', text: selection.fact_ids.map(id => facts.find(f => f.id === id).text).join(' ') };
      });
    } catch (error) {
      return { status: error.indeterminate ? 'indeterminate' : 'error', text: fallback, error_code: error instanceof ConnectorError ? error.code : 'agent_error', retry_performed: false };
    }
  }
}
