#!/usr/bin/env python3
"""Offline checks; never executes Git, old exporters, or network clients.

Coordinator P3 fix: retain the historical aggregate, protect declared immutable
inputs against the independent review's per-file receipt, and exclude mutable
orchestration/review artifacts. No financial formula or output is changed.
"""
from pathlib import Path
import csv
import hashlib
import json
import os
import struct
import sys

HERE = Path(__file__).resolve().parent
INPUT = HERE.parent
ROOT = INPUT.parent.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protection():
    """Read v2/v3 Git index directly, so even the Git CLI is unnecessary."""
    gd = ROOT / '.git'
    if gd.is_file():
        gd = (ROOT / gd.read_text().strip().split(': ', 1)[1]).resolve()
    data = (gd / 'index').read_bytes()
    magic, version, count = struct.unpack('>4sII', data[:12])
    assert magic == b'DIRC' and version in (2, 3), 'unsupported index; do not bypass'
    pos = 12
    digest = hashlib.sha256()
    protected_count = 0
    for _ in range(count):
        start = pos
        flags = struct.unpack('>H', data[pos+60:pos+62])[0]
        pos += 62
        if flags & 0x4000:
            pos += 2
        end = data.index(b'\0', pos)
        name = data[pos:end]
        pos = start + ((end + 1 - start + 7) // 8) * 8
        # This package may subsequently be committed. Its own new files are
        # outputs, not changes to the pre-existing 1,908-file source tree.
        if name.startswith(b'context/39_cost_completion_20261113/'):
            continue
        protected_count += 1
        path = ROOT / os.fsdecode(name)
        payload = (os.fsencode(os.readlink(path)) if path.is_symlink()
                   else path.read_bytes() if path.is_file() else b'<MISSING>')
        digest.update(name + b'\0' + hashlib.sha256(payload).digest())
    source_digest = hashlib.sha256()
    files = sorted(p for p in INPUT.rglob('*') if p.is_file() and HERE not in p.parents)
    for p in files:
        source_digest.update(str(p.relative_to(INPUT)).encode() + b'\0' + bytes.fromhex(sha(p)))
    return {'tracked_entries': protected_count, 'index_sha256': hashlib.sha256(data).hexdigest(),
            'tracked_content_sha256': digest.hexdigest(), 'input_files': len(files),
            'input_content_sha256': source_digest.hexdigest()}


def main():
    if '--capture' in sys.argv:
        path = HERE / 'protection.json'
        assert not path.exists(), 'baseline is immutable'
        path.write_text(json.dumps(protection(), indent=2) + '\n')
        print('Protection baseline captured; Git CLI not used.')
        return
    import build_cost_table as b
    checks = []

    def check(name, condition):
        checks.append({'check': name, 'pass': bool(condition)})
        if not condition:
            raise AssertionError(name)

    baseline = json.loads((HERE / 'protection.json').read_text())
    current = protection()
    check('old_tracked_content_and_paths_preserved', all(current[k] == baseline[k]
          for k in ('tracked_entries', 'tracked_content_sha256')))
    manifest = json.loads((HERE/'immutable_inputs.json').read_text())
    anchor_path = (HERE/manifest['anchor_ref']).resolve()
    check('independent_review_anchor_unchanged', sha(anchor_path) == manifest['anchor_sha256'])
    anchor = json.loads(anchor_path.read_text())
    for name, expected_hash in manifest['paths'].items():
        check('immutable_input_matches_review_' + name,
              anchor.get(name) == expected_hash and sha(INPUT/name) == expected_hash)
    rows = list(csv.DictReader((HERE / 'COST_TABLE.csv').open(encoding='utf-8')))
    expected, workings = b.calculate()
    serialized = [{k: b.cell(v) for k, v in r.items()} for r in expected]
    check('canonical_output_matches_offline_rebuild', rows == serialized)
    check('readable_result_matches_rebuild', (HERE/'RESULT.md').read_text() == b.report(expected,workings))
    check('assumptions_matches_rebuild', (HERE/'ASSUMPTIONS.md').read_text() == b.assumptions())
    check('workings_matches_rebuild', json.loads((HERE/'workings.json').read_text()) == workings)
    check('546_unique_article_case_rows', len(rows) == 39*14 == len({r['row_id'] for r in rows}))
    check('117_coverage_rows_retained', len(b.read('model_audit/coverage.csv')) == 117)
    check('completed_input_shapes', len(b.read('model_audit/exposures.csv')) == 476 and len(b.read('omsk_price_recovery/prices.csv')) == 34 and len(b.read('research_fleet/price_evidence.csv')) == 15 and len(b.read('fleet_price_recovery/prices.csv')) == 5)
    texts = {r['citation']:r for r in b.read('model_audit/evidence_lines.csv')}
    for citation in {s.strip() for _,r in b.COVERAGE.values() for s in r['evidence'].split('|')}:
        check('original_citation_resolves_' + citation, citation in texts)
        record=texts[citation]
        source=INPUT/'model_audit'/record['snapshot_path']
        line=int(citation.rsplit(':',1)[1])
        check('exact_original_source_line_' + citation, source.read_text().splitlines()[line-1] == record['source_text'])
    for record in json.loads((INPUT/'model_audit/snapshot_manifest.json').read_text()):
        check('pinned_snapshot_hash_' + record['snapshot_path'], sha(INPUT/'model_audit'/record['snapshot_path']) == record['sha256'])
    oms = b.PRICES
    for sid,amount in [('OMS-RACK',1229.51),('OMS-BAG',4450),('OMS-CITYBUS',3430),('OMS-WH-11.19.1',330),('OMS-WH-11.19.2',1000),('OMS-BASE-30–74.999 т',117100),('OMS-BASE-75–99.999 т',130200)]:
        check('canonical_price_unit_value_' + sid, b.number(oms[sid][1]['min']) == amount and b.number(oms[sid][1]['max']) == amount and oms[sid][1]['effective']=='2026-08-21')
        check('current_tax_unknown_no_invented_rate_' + sid, 'UNKNOWN' in oms[sid][1]['tax'])
    check('hotel_price_and_tax', b.number(oms['ANALOG-HOTEL-SINGLE'][1]['min'])==4100 and b.number(oms['ANALOG-HOTEL-DOUBLE'][1]['min'])==4650 and 'UNKNOWN' in oms['ANALOG-HOTEL-SINGLE'][1]['tax'])
    for r in rows:
        key = (r['article_id'], r['coverage_network'])
        original = b.COVERAGE[key][1]
        check('coverage_status_' + r['row_id'], r['coverage_status_original'] == original['status'])
        check('russian_status_' + r['row_id'], r['coverage_ru'] == b.STATUS[original['status']][1])
        check('unknown_addition_not_zero_' + r['row_id'], r['annual_addition_min_rub'] == 'UNKNOWN' and r['annual_addition_max_rub'] == 'UNKNOWN')
        check('exact_model_and_driver_refs_' + r['row_id'], bool(r['code_table_exact_lines']) and bool(r['driver_refs']))
        check('source_refs_resolve_' + r['row_id'], all(b.resolve_ref(ref) for ref in json.loads(r['source_refs'])))
        check('source_IDs_resolve_' + r['row_id'], all(sid=='MODEL_AUDIT' or b.resolve_ref(b.source_meta(sid)['ref']) for sid in json.loads(r['source_ids'])))
        check('query_and_formula_' + r['row_id'], bool(r['request_RW']) and bool(r['annual_formula']) and bool(json.loads(r['normalized_scenarios'])))
        for s in json.loads(r['normalized_scenarios']):
            for field in ('full_service_min_rub', 'full_service_max_rub'):
                check('none_propagation_' + r['row_id'] + s['name'] + field,
                      (s[field] is None) == (s['unit_min'] is None or s['quantity'] is None) if field.endswith('min_rub') else
                      (s[field] is None) == (s['unit_max'] is None or s['quantity'] is None))
            if s['unit_min'] is not None and s['quantity'] is not None:
                check('annual_formula_' + r['row_id'] + s['name'],
                      abs(s['full_service_min_rub'] - s['unit_min'] * s['quantity']) < .011)
            check('all_sensitivity_additions_conditional_' + r['row_id'] + s['name'], s['addition_rub'] is None)
    check('none_times_zero_stays_unknown', b.product(None, 0) is None and b.strict_sum([0, None]) is None)
    check('round_half_up', b.money('1.005') == 1.01 and b.money('-1.005') == -1.01)
    check('no_new_admitted_additions', workings['admitted_additions_count'] == 0)
    check('unknown_aggregate_not_zero', workings['annual_missing_total_rub'] is None and workings['full_PnL_rub'] is None)
    check('launch_categories_separate', set(workings['launch']) == {'one_off_expense_rub','CAPEX_rub','refundable_deposit_rub','advance_rub','spares_stock_rub','working_capital_peak_rub'} and all(v is None for v in workings['launch'].values()))
    for c in workings['cases']:
        check('one_reserve_' + c['case'], c['reserve_aircraft'] == 1 and c['fleet_total'] == c['working_aircraft']+1)
        check('no_365_owner_annualization_' + c['case'], c['weeks'] in (48,52) if c['model']=='OWNER' else c['calendar_days']==365)
        check('threshold_identity_' + c['case'], abs(c['rent_ceiling_all_fleet_per_aircraft_month_rub']*c['all_fleet_months_stress']-c['model_margin_rub']) < .00001)
        check('historical_rent_18pct_once_' + c['case'], abs(c['rent_stress_full_allocation_exVAT_rub']-7560000/1.18*c['all_fleet_months_stress']) < .011)
        check('actual_billed_months_unknown_' + c['case'], c['actual_billed_aircraft_months'] is None)
        check('oms_departures_not_all_network_' + c['case'], c['OMS_departures'] <= c['departures'])
    bycase = {c['case']: c for c in workings['cases']}
    check('owner_BASE_fleets_7_8_9', [bycase[k]['fleet_total'] for k in ['OWNER:OMS:base','OWNER:DIRECT:base','OWNER:DIRECT:base_sub']] == [7,8,9])
    check('owner_OMS_segments_not_journeys', abs(bycase['OWNER:OMS:base']['segments']-bycase['OWNER:OMS:base']['journeys']-bycase['OWNER:OMS:base']['transfer_journeys']) < 1e-7)
    dated=b.read('model_audit/p38_dated_exposure.csv')
    check('P38_exact_2027_not52_weeks', len(dated)==5531 and all(r['dep'].startswith('2027-') for r in dated))
    for c in workings['cases']:
        if c['model']=='P38':
            plan=[r for r in dated if r['candidate']==c['network']]
            check('P38_actual_departures_' + c['case'], len(plan)==c['departures'])
            check('P38_actual_OMS_departures_' + c['case'], sum(r['origin']=='OMS' for r in plan)==c['OMS_departures'])
            check('P38_actual_BH_' + c['case'], abs(sum(float(r['block_h']) for r in plan)-c['block_hours'])<1e-7)
            check('P38_active_tail_months_' + c['case'], len({(r['tail'],r['dep'][:7]) for r in plan})==24==c['active_working_tail_months_in_2027_calendar'])
        for item,metric,rate in [('MRO_PROXY','block_hours',55000 if c['scenario'].startswith('cautious') else 35000),('NAV','block_hours',8000 if c['scenario'].startswith('cautious') else 6000),('GROUND','departures',115307 if c['scenario'].startswith('cautious') else 96089),('DEICE','departures',40000 if c['scenario'].startswith('cautious') else 15000)]:
            r=next(r for r in rows if r['case']==c['case'] and r['article_id']==item)
            check('independent_existing_annual_formula_' + c['case']+item, abs(float(r['existing_annual_amount_rub'])-rate*c[metric])<.0001)
        pax=next(r for r in rows if r['case']==c['case'] and r['article_id']=='PAX')
        check('pax_segments_not_journeys_' + c['case'], abs(float(pax['existing_annual_amount_rub'])-(c['segments']*(650 if c['scenario'].startswith('cautious') else 500) if c['model']=='OWNER' else 0))<.0001)
        crew=next(r for r in rows if r['case']==c['case'] and r['article_id']=='CREW_PROXY')
        check('crew_excluded_once_' + c['case'], abs(float(crew['existing_annual_amount_rub'])-(c['block_hours']*(22000 if c['scenario'].startswith('cautious') else 15000) if c['model']=='OWNER' else 0))<.0001)
    for r in rows:
        scenarios = json.loads(r['normalized_scenarios'])
        if r['article_id'] == 'PARKING':
            check('parking_options_exclusive_' + r['row_id'], all(s['exclusive_group']=='parking_billing_choice' for s in scenarios if s['price_source_id'].startswith('OMS-')))
        if r['article_id'] in ('LEASE_WORK','LEASE_RES'):
            check('historical_not_admitted_' + r['row_id'], r['unit_price_admission'] == 'HISTORICAL_STRESS_ONLY; CURRENT_UNKNOWN')
        check('no_index_only_prices_admitted_' + r['row_id'], not any(x in json.loads(r['source_ids']) for x in ['PKC-1690-AUDIT','ANALOG-AERO-BREAKFAST','ANALOG-BUS','INS-TENDER-REJECTED']))
    # Independent cross-check of the main normalized annual services from physical exposure.
    for r in rows:
        c = bycase[r['case']]
        for s in json.loads(r['normalized_scenarios']):
            if s['name']=='one_extra_bag_service_per_OMS_departure':
                check('bag_service_unit_not_kg_' + r['row_id'], s['quantity']==c['OMS_departures'] and s['unit_min']==4450)
            if s['name']=='one_informing_workplace_per_OMS_departure':
                check('desk_not_DCS_' + r['row_id'], s['quantity']==c['OMS_departures'] and s['unit_min']==1229.51)
            if s['name']=='one_percentage_point_transfer_one_night_single':
                check('hotel_journey_not_segments_' + r['row_id'], abs(s['quantity']-.01*c['transfer_journeys'])<1e-9 and s['unit_min']==4100)
    # No hidden execution of network/exporters: build imports are stdlib and input reads only.
    for filename in ['build_cost_table.py', 'verify.py']:
        import ast
        tree = ast.parse((HERE/filename).read_text())
        imports = {n.module.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        check('offline_imports_' + filename, imports <= {'pathlib','csv','json','hashlib','decimal','collections','re','datetime','struct','sys','os','ast','build_cost_table'})
    result = {'status':'PASS_SCOPED_P3_CORRECTION','checks':len(checks),'failed':0,'deterministic':True,
              'historical_protection_preserved':baseline,
              'immutable_input_count':len(manifest['paths']),
              'immutable_manifest_sha256':sha(HERE/'immutable_inputs.json'),
              'verifier_sha256':sha(Path(__file__)),
              'outputs_sha256':{n:sha(HERE/n) for n in b.OUTPUTS},
              'limits':'Tracked paths/content match historical baseline; exact immutable inputs match independent review receipt. Mutable task/review outputs excluded. Original protection.json and validation.json are historical, preserved. No market quotes2027; no full budget/PnL.'}
    (HERE/'validation_scoped.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':'PASS','checks':len(checks),'rows':len(rows)},ensure_ascii=False))


if __name__ == '__main__':
    main()
