import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createDemoCatalogue, loadDemoCatalogue, validateDemo } from '../src/demo-catalogue.mjs';

const read = async id => JSON.parse(await readFile(new URL(`../data/demos/${id}.json`, import.meta.url), 'utf8'));
const feeder = await read('feeder-flight');
const arrival = await read('arrival-train');
const ground = await read('ground-alternative');
const direct = await read('direct-flight');
const scenario = await read('scenario-transfer');
const changed = (original, change) => { const copy = structuredClone(original); change(copy); return copy; };

test('four local prepared examples expose only manifest metadata, readable labels and original evidence levels', async () => {
  const catalogue = await loadDemoCatalogue();
  assert.equal(catalogue.list().demos.length, 4);
  for (const item of catalogue.list().demos) {
    assert.deepEqual(Object.keys(item).sort(), ['id', 'label', 'type', 'checked_at', 'data_mode', 'description'].sort());
    assert(!/^[\w-]+$/u.test(item.label));
    const demo = catalogue.get(item.id);
    assert(demo.result.reply.length > 0);
    assert(!/не ответ LLM|зарегистрированн\S* граф/iu.test(demo.result.reply));
  }
  assert.equal(catalogue.get('feeder-flight').result.plans[0].status, 'partial');
  assert.equal(catalogue.get('arrival-train').result.plans[0].status, 'partial');
  assert.equal(catalogue.get('ground-alternative'), null);
  assert.throws(() => validateDemo(ground));
  assert.equal(catalogue.get('direct-flight').result.plans[0].status, 'verified');
  for (const item of catalogue.list().demos) assert(catalogue.get(item.id).result.plans.every(p => p.requires_red_wings && p.legs.some(l => l.mode === 'plane' && l.carrier_iata === 'WZ')));
  const future = catalogue.get('scenario-transfer');
  assert.equal(future.result.plans[0].status, 'candidate');
  assert.equal(future.result.plans[0].total_duration_minutes, null);
  assert(future.result.plans[0].transfer_options.every(o => !o.recommended));
  const copy = catalogue.get('feeder-flight'); copy.trip.origin.city = 'changed'; copy.result.plans.length = 0;
  assert.notEqual(catalogue.get('feeder-flight').trip.origin.city, 'changed');
  assert.equal(catalogue.get('feeder-flight').result.plans.length, 1);
});

test('catalogue IDs cannot be forged into paths, URLs, inherited properties or mismatched entries', () => {
  const catalogue = createDemoCatalogue([feeder]);
  for (const id of ['../feeder-flight', '/etc/passwd', 'https://example.com/x', '__proto__', 'constructor', 'feeder-flight.json', null]) assert.equal(catalogue.get(id), null);
  assert.throws(() => validateDemo(feeder, 'arrival-train'));
  assert.throws(() => createDemoCatalogue([feeder, feeder]));
  assert.throws(() => validateDemo({ ...feeder, id: '../feeder-flight' }));
});

test('schema, real calendar dates and UTC chronology are checked instead of trusting verification prose', () => {
  for (const mutate of [
    d => { d.result.usage = { model_calls: 2 }; },
    d => { d.result.sources = [{ name: 'missing URL' }]; },
    d => { d.result.plans[0].warnings = [42]; },
    d => { delete d.trip.constraints.allow_taxi; },
    d => { d.trip.date_range.from = '2026-02-30'; },
    d => { d.result.plans[0].legs[0].departure = '2026-12-08T24:00:00+05:00'; },
    d => { d.result.plans[0].legs[0].arrival = '2026-02-30T19:06:00+05:00'; },
    d => { d.result.plans[0].legs[0].arrival = d.result.plans[0].legs[0].departure; },
    d => { d.result.plans[0].legs[1].id = d.result.plans[0].legs[0].id; },
    d => { d.result.plans[0].legs[3].carrier_code = 999; },
    d => { d.result.plans[0].legs[3].departure = d.result.plans[0].legs[3].departure.replace('+05:00', '+08:00');
      d.result.plans[0].legs[3].arrival = d.result.plans[0].legs[3].arrival.replace('+04:00', '+07:00'); },
  ]) assert.throws(() => validateDemo(changed(feeder, mutate)));
});

test('120-minute preflight minimum includes sourced walking duration without invented timestamps', () => {
  const exact = changed(feeder, d => { d.result.plans[0].legs[2].duration_minutes = 50; });
  assert.equal(validateDemo(exact).result.plans[0].status, 'partial');
  assert.throws(() => validateDemo(changed(exact, d => { d.result.plans[0].legs[2].duration_minutes = 51; })), /connection_buffer/);
  assert.throws(() => validateDemo(changed(exact, d => { d.result.plans[0].legs[2].source_url = null; })), /transfer_source/);
});

test('60-minute postflight minimum includes published bus allowance across null timestamps', () => {
  const exact = changed(arrival, d => { d.result.plans = [d.result.plans[0]]; d.result.plans[0].legs[1].duration_minutes = 178; });
  assert.equal(validateDemo(exact).result.plans[0].status, 'partial');
  assert.throws(() => validateDemo(changed(exact, d => { d.result.plans[0].legs[1].duration_minutes = 179; })), /connection_buffer/);
});

test('network mixing, promoted partials, forged references and trip constraint violations are rejected', () => {
  for (const mutate of [
    d => { d.result.plans[0].network_mode = 'scenario_2027_2028'; },
    d => { d.result.plans[0].legs[0].network_mode = 'scenario_2027_2028'; },
    d => { d.result.plans[0].legs[0].data_mode = 'scenario'; },
    d => { d.result.plans[0].status = 'verified'; },
    d => { d.trip.selected_flight.number = 'WZ 9999'; },
    d => { d.trip.constraints.modes = ['plane']; },
    d => { d.result.plans[0].legs[2].mode = 'taxi'; },
    d => { d.result.plans[0].legs[0].source_url = 'file:///etc/passwd'; },
    d => { d.result.plans[0].legs[0].links[0].url = 'javascript:alert(1)'; },
  ]) assert.throws(() => validateDemo(changed(feeder, mutate)));
  assert.throws(() => validateDemo(changed(scenario, d => { d.data_mode = 'snapshot'; })));
  assert.throws(() => validateDemo(changed(scenario, d => { d.result.plans[0].status = 'verified'; })));
  const partial = changed(direct, d => { d.result.plans[0].status = 'partial'; d.result.status = 'ok'; });
  assert.equal(validateDemo(partial).result.plans[0].status, 'partial');
  assert.equal(validateDemo(partial).result.status, 'partial');
});
