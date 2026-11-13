import test from 'node:test';
import assert from 'node:assert/strict';
import { excessiveAirportGround } from '../src/route-policy.mjs';
import { acceptJourneyResult } from '../src/chat-callbacks.mjs';
import { emptyTrip } from '../src/journey-trip.mjs';
test('a fifteen-hour airport approach is excluded; normal regional access and ground-only journeys remain possible', () => {
  const plane = { mode: 'plane' };
  const bus = duration => ({ mode: 'bus', duration_minutes: duration });
  assert(excessiveAirportGround([bus(900), plane]));
  assert(excessiveAirportGround([bus(300), bus(300), plane]));
  assert.equal(excessiveAirportGround([bus(330), plane, bus(180)]), false);
  assert.equal(excessiveAirportGround([bus(900)]), false);
});
test('the response boundary rejects a competing or unidentified airline even when labelled a comparison', () => {
  for (const carrier of [{ carrier_code: 29, carrier_iata: 'UT' }, { carrier_code: 617, carrier_iata: 'XX' }, {}]) {
    const plan = { id: 'comparison', title: 'Comparison', status: 'verified', requires_red_wings: false,
      warnings: [], sources: [], total_duration_minutes: null, total_price: null,
      legs: [{ mode: 'plane', origin: 'A', destination: 'B', evidence_status: 'dated', ...carrier }] };
    assert.throws(() => acceptJourneyResult({ plans: [plan] }, emptyTrip()), /unsupported_airline/);
  }
});
