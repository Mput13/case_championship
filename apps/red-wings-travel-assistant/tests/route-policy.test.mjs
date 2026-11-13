import test from 'node:test';
import assert from 'node:assert/strict';
import { excessiveAirportGround, redWingsResult } from '../src/route-policy.mjs';
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

test('passenger results require a WZ flight; a ground-only fallback cannot replace it', () => {
  const ground = { id: 'train-only', requires_red_wings: false, legs: [{ mode: 'train' }], sources: [{ url: 'https://fixture.invalid/train' }] };
  const flight = { id: 'rw', requires_red_wings: true, legs: [{ mode: 'bus' }, { mode: 'plane', carrier_iata: 'WZ', carrier_code: 617 }], sources: [{ url: 'https://fixture.invalid/rw' }] };
  const result = redWingsResult({ status: 'ok', plans: [ground, flight], sources: [...ground.sources, ...flight.sources] });
  assert.deepEqual(result.plans, [flight]); assert.deepEqual(result.sources, flight.sources);
  const empty = redWingsResult({ status: 'ok', plans: [ground], sources: ground.sources });
  assert.deepEqual(empty.plans, []); assert.equal(empty.status, 'needs_input');
  assert.match(empty.missing_data[0], /Red Wings/);
  assert.equal(redWingsResult({ plans: [{ ...flight, legs: [...flight.legs, { mode: 'plane', carrier_iata: 'UT' }] }] }).plans.length, 0);
});
