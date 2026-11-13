import test from 'node:test';
import assert from 'node:assert/strict';
import { shiftLocalTime } from '../src/time-utils.mjs';
test('physical-transfer shifts preserve local date/offset and true elapsed time across midnight', () => {
  for (const [start, n, end] of [
    ['2026-12-02T11:45:00+05:00', 1, '2026-12-02T11:46:00.000+05:00'],
    ['2026-12-02T23:45:00+05:00', 60, '2026-12-03T00:45:00.000+05:00'],
    ['2026-12-02T00:15:00-03:00', -30, '2026-12-01T23:45:00.000-03:00'],
  ]) { assert.equal(shiftLocalTime(start, n), end); assert.equal(Date.parse(end) - Date.parse(start), n * 60000); }
});
