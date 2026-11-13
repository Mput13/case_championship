import test from 'node:test';
import assert from 'node:assert/strict';
import { rankTransferOptions, scenarioJourney } from '../src/product-services.mjs';
const option = (id, mins, extra = {}) => ({ id, status: 'available', connection_status: 'verified', total_duration_minutes: mins, transfers: 1, overnight: false, ...extra });
test('partner priority requires comparable checked convenience; public alternatives stay visible', () => {
  const p = option('public', 100), s = option('partner', 110, { is_red_wings_partner: true });
  assert.deepEqual(rankTransferOptions([p, s]).map(o => [o.id, o.recommended]), [['partner', true], ['public', false]]);
  for (const change of [{ total_duration_minutes: 130 }, { transfers: 2 }, { overnight: true }, { connection_status: 'unknown' }, { status: 'target' }, { total_duration_minutes: null }]) {
    assert.equal(rankTransferOptions([p, { ...s, ...change }]).find(o => o.id === 'partner').recommended, false);
  }
});
test('future OMS IKT remains a separate unknown-time concept with no invented booking or connection', () => {
  const result = scenarioJourney({ origin: { city: 'Омск' }, destination: { city: 'Ольхон, Хужир' } });
  const plan = result.plans[0];
  assert.equal(plan.network_mode, 'scenario_2027_2028'); assert.equal(plan.status, 'candidate');
  assert.equal(plan.legs[0].departure, null); assert.equal(plan.total_duration_minutes, null);
  assert.equal(plan.transfer_options.find(o => o.id === 'smart-transfer').status, 'target');
  assert.equal(rankTransferOptions(plan.transfer_options).some(o => o.recommended), false);
});
