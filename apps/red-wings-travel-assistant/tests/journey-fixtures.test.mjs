// Entirely synthetic offline fixtures. None of these are real transport facts.
import { createAssistantMessageEventStream } from '@earendil-works/pi-ai';
import { emptyTrip, applyTripPatch } from '../src/journey-trip.mjs';
export const fixtureNow = new Date('2026-11-13T12:00:00Z');
export const fixtureConfig = { llmEnabled: true, maiModel: 'offline-test', maxLLMCalls: 1000,
  llmTimeout: 1000, chatTurnTimeoutMs: 3000, chatNow: () => fixtureNow };
const source = { source_name: 'SYNTHETIC TEST DATA', source_url: 'https://fixture.invalid/timetable', evidence_status: 'dated', checked_at: '2026-11-13T00:00:00Z' };
const at = time => `2026-12-01T${time}:00+05:00`;
export function fixtureGraph() {
  const node = (id, city, title, type, extra = {}) => ({ id, city, title, type,
    min_transfer_minutes: 45, transfer_source_url: 'https://fixture.invalid/buffers', ...extra });
  const leg = (id, from, to, mode, departure, arrival, extra = {}) => ({ id, from, to, mode,
    ...source, departure: at(departure), arrival: at(arrival), price: 100, currency: 'RUB', price_basis: 'person', ...extra });
  return { nodes: [
    node('door', 'Ханты-Мансийск', 'Ленина 109', 'address', { address: 'Ленина 109' }),
    node('hma', 'Ханты-Мансийск', 'Synthetic HMA airport', 'airport', { schedule_code: 's-test-hma', iata: 'HMA' }),
    node('svx', 'Екатеринбург', 'Synthetic SVX airport', 'airport', { schedule_code: 's-test-svx', iata: 'SVX' }),
    node('miass', 'Миасс', 'Synthetic Miass station', 'station'),
  ], legs: [
    leg('taxi', 'door', 'hma', 'taxi', '06:00', '06:30'),
    leg('bus', 'door', 'hma', 'bus', '06:00', '07:00'),
    leg('rw', 'hma', 'svx', 'plane', '09:00', '11:00', { carrier_code: 617, carrier_iata: 'WZ', carrier: 'Synthetic RW', number: 'WZ 90001' }),
    leg('coach', 'svx', 'miass', 'bus', '12:00', '15:00'),
    leg('baseline', 'door', 'miass', 'bus', '07:00', '16:00'),
  ], corridors: [{ id: 'synthetic-rw', origin_city: 'Ханты-Мансийск', destination_city: 'Миасс', kind: 'with_rw', leg_ids: ['bus', 'rw', 'coach'] },
    { id: 'synthetic-baseline', origin_city: 'Ханты-Мансийск', destination_city: 'Миасс', kind: 'baseline', leg_ids: ['baseline'] }] };
}
export const tripPatch = { origin: { city: 'Ханты-Мансийск', address: 'Ленина 109' }, destination: { city: 'Миасс' },
  date_range: { from: '2026-12-01', to: '2027-01-15', meaning: 'departure_window' }, passengers: 2 };
export const fixtureTrip = () => applyTripPatch(emptyTrip(), tripPatch, { now: fixtureNow });
export const call = (name, args = {}, id = name) => ({ type: 'toolCall', id, name, arguments: args });
export function respond(model, content, { stopReason = content.some(c => c.type === 'toolCall') ? 'toolUse' : 'stop', usage } = {}) {
  const stream = createAssistantMessageEventStream();
  const message = { role: 'assistant', content, model: model.id, provider: model.provider, api: model.api, stopReason, timestamp: Date.now(),
    usage: usage === undefined ? { input: 40, output: 30, cacheRead: 0, cacheWrite: 0, totalTokens: 70,
      cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } } : usage };
  stream.push({ type: 'done', reason: stopReason, message });
  return stream;
}
export const say = text => ({ type: 'text', text });
