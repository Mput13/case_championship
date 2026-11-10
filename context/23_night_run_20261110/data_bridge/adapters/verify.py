#!/usr/bin/env python3
"""Independent package checks and sanitizer; no network/author-code execution."""
import csv
import hashlib
import json
import math
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

OUT=Path(__file__).resolve().parents[1]
ROOT=OUT.parents[2]
PREFIX=OUT.relative_to(ROOT).as_posix()+'/'


def sha(b):return hashlib.sha256(b).hexdigest()


def read(p):
    with (OUT/p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def main():
    checks=[]
    def check(name,ok,detail):checks.append(dict(check_id=name,status='PASS' if ok else 'FAIL',detail=detail))
    files=sorted(p for p in OUT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'
                 and p.name!='outputs_manifest.json' and p.relative_to(OUT).as_posix()!='checks/package_verification.json')
    csv_errors=[];json_errors=[];sanitize_errors=[];counts=dict(csv=0,json=0,bytes=0,files=len(files))
    secret_patterns=[re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
                     re.compile(r'\bgh[pousr]_[A-Za-z0-9]{25,}\b'),
                     re.compile(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{30,}\b'),
                     re.compile(r'\bAKIA[0-9A-Z]{16}\b')]
    for p in files:
        b=p.read_bytes();counts['bytes']+=len(b)
        if len(b)>8*1024*1024:sanitize_errors.append(dict(file=str(p.relative_to(OUT)),reason='UNEXPECTED_LARGE_FILE'))
        if p.suffix in ['.zip','.gz','.pdf','.xlsx','.db','.sqlite','.png','.log']:
            sanitize_errors.append(dict(file=str(p.relative_to(OUT)),reason='RAW_OR_RUNTIME_FILE_IN_SCOPE'))
        text=b.decode('utf-8')
        if any(rx.search(text) for rx in secret_patterns):sanitize_errors.append(dict(file=str(p.relative_to(OUT)),reason='POTENTIAL_SECRET'))
        if p.suffix=='.csv':
            counts['csv']+=1;rows=list(csv.reader(text.splitlines()))
            if not rows or len(set(rows[0]))!=len(rows[0]) or any(len(r)!=len(rows[0]) for r in rows[1:]):
                csv_errors.append(str(p.relative_to(OUT)))
        if p.suffix=='.json':
            counts['json']+=1
            try:json.loads(text)
            except (ValueError,TypeError):json_errors.append(str(p.relative_to(OUT)))
    check('CSV_SHAPE',not csv_errors,csv_errors)
    check('JSON_VALID',not json_errors,json_errors)
    check('SANITIZER_NO_SECRETS_RAW_OR_LARGE_FILES',not sanitize_errors,sanitize_errors)
    tracked=subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT,text=True).splitlines()
    untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
    outside=[p for p in tracked+untracked if not p.startswith(PREFIX)]
    check('WRITE_SCOPE_ONLY_OWN_FOLDER',not outside,outside)
    manifest=json.loads((OUT/'input_manifest.json').read_text());fail=[]
    for r in manifest['source_inputs']:
        b=subprocess.check_output(['git','show',r['source_commit']+':'+r['source_path']],cwd=ROOT)
        if sha(b)!=r['sha256'] or len(b)!=r['bytes']:fail.append(r['input_id'])
    check('ALL_PINNED_INPUT_HASHES',not fail,dict(inputs=len(manifest['source_inputs']),failures=fail))
    check('CONTRACT_PIN_MATCH',sha((OUT.parent/'contract.md').read_bytes())==manifest['contract_sha256'],'Current local contract bytes equal ingested contract')
    check('PARENT_MANIFEST_PIN_MATCH',sha((OUT.parent/'input_manifest.json').read_bytes())==manifest['parent_input_manifest_sha256'],'Frozen manifest bytes unchanged')
    supplemental=json.loads((OUT/'checks/raw_input_manifest.json').read_text());supplement_fail=[]
    for r in supplemental['source_inputs']:
        b=subprocess.check_output(['git','show',r['source_commit']+':'+r['source_path']],cwd=ROOT)
        if sha(b)!=r['sha256']:supplement_fail.append(r['source_path'])
    check('SUPPLEMENTAL_PINNED_INPUT_HASHES',not supplement_fail,supplement_fail)
    # Reconcile independently from adapted tables, not from build.py's helper accumulators.
    its=read('normalized/itinerary.csv');legs=read('normalized/itinerary_leg.csv');alloc=read('normalized/capacity_allocation.csv')
    money=read('normalized/money_ledger.csv');physical=read('normalized/physical_leg.csv');pools=read('normalized/market_pool.csv')
    itidx={r['itinerary_id']:r for r in its};pidx={r['physical_leg_id']:r for r in physical};midx={r['market_pool_id']:r for r in pools}
    duplicate_ids=len(itidx)!=len(its) or len(pidx)!=len(physical) or len(midx)!=len(pools)
    check('NORMALIZED_PRIMARY_KEYS',not duplicate_ids,dict(itineraries=len(its),physical_legs=len(physical),pools=len(pools)))
    fk=[r['itinerary_id'] for r in legs if r['itinerary_id'] not in itidx or r['physical_leg_id'] not in pidx]
    check('NORMALIZED_LEG_FOREIGN_KEYS',not fk,fk[:10])
    grouped=defaultdict(list)
    for r in legs:grouped[r['itinerary_id']].append(r)
    legerr=[]
    for r in its:
        rr=sorted(grouped[r['itinerary_id']],key=lambda x:int(x['leg_sequence']))
        if len(rr)!=int(r['leg_count']) or not math.isclose(sum(float(x['seat_segments_used']) for x in rr),float(r['segment_pax']),abs_tol=1e-6):legerr.append(r['itinerary_id'])
    check('NORMALIZED_JOURNEY_SEGMENT_CONSERVATION',not legerr,dict(itineraries=len(its),leg_rows=len(legs),failures=legerr[:10]))
    gross=defaultdict(list)
    for r in money:
        if r['account']=='gross_revenue':gross[r['itinerary_id']].append(r)
    fareerr=[]
    for r in its:
        rr=gross[r['itinerary_id']]
        if len(rr)!=1 or not math.isclose(float(rr[0]['amount_rub']),float(r['sold_journeys'])*float(r['whole_journey_fare_rub']),abs_tol=1e-6):fareerr.append(r['itinerary_id'])
    check('NORMALIZED_ONE_WHOLE_FARE',not fareerr,dict(itineraries=len(its),failures=fareerr[:10]))
    allocated=defaultdict(float)
    for r in alloc:allocated[(r['model_id'],r['candidate_id'],r['scenario_id'],r['priority'],r['physical_leg_id'])]+=float(r['allocated_seats'])
    over=[dict(key=k,used=v,capacity=pidx[k[4]]['seats']) for k,v in allocated.items() if v>float(pidx[k[4]]['seats'])+1e-6]
    check('NORMALIZED_SEAT_BOUND',not over,dict(flight_scenario_keys=len(allocated),failures=over[:10]))
    pooluse=defaultdict(float)
    for r in its:pooluse[(r['candidate_id'],r['scenario_id'],r['priority'],r['market_pool_id'])]+=float(r['sold_journeys'])
    poolover=[dict(key=k,used=v) for k,v in pooluse.items() if k[3] not in midx or v>float(midx[k[3]]['pool_journeys'])+1e-6]
    check('NORMALIZED_COMMON_OD_POOL_BOUND',not poolover,dict(strategy_OD_groups=len(pooluse),failures=poolover[:10]))
    entities=read('normalized/entity_resolution.csv');held={r['entity_code'] for r in entities if r['key_status'] in ['QUARANTINE','GROUP_NOT_AIRPORT','AMBIGUOUS_IATA','UNMATCHED']}
    bad_weather=[r['entity_code'] for r in read('normalized/airport_weather_month.csv') if r['entity_code'] in held]
    bad_resolved=[r['entity_code'] for r in entities if r['entity_code'] in held and (r['airport_id'] or r['iana_timezone'])]
    check('NORMALIZED_HOLDS_NOT_BYPASSED',not bad_weather and not bad_resolved,dict(held=sorted(held),weather_bypasses=bad_weather,resolution_bypasses=bad_resolved))
    tourism=read('normalized/candidate_regional_tourism.csv')
    holdunit=[r for r in tourism if r['unit_missing_reason']]
    check('UNKNOWN_TOURISM_UNITS_NOT_ADMITTED',bool(holdunit) and all(r['numeric_use_admitted']=='False' and r['bridge_value_class']=='UNKNOWN' for r in holdunit),
          dict(candidate_incidence_rows=len(tourism),held_incidence_rows=len(holdunit),unique_source_cells_held=len({(r['canonical_region_id'],r['indicator_code'],r['year']) for r in holdunit})))
    budgets=read('normalized/evaluation_summary.csv')
    check('UNKNOWN_FULL_BUDGET_NOT_ZERO',all(r['full_budget_rub']=='' and r['full_budget_missing_reason'] for r in budgets),dict(rows=len(budgets)))
    dictionary=read('field_dictionary.csv')
    declared={(r['table'],r['field']) for r in dictionary}
    missing_fields=[]
    for p in sorted((OUT/'normalized').glob('*.csv')):
        with p.open(newline='',encoding='utf-8-sig') as f:headers=next(csv.reader(f))
        missing_fields.extend((p.relative_to(OUT).as_posix(),c) for c in headers if (p.relative_to(OUT).as_posix(),c) not in declared)
    check('FIELD_DICTIONARY_COVERS_NORMALIZED_TABLES',not missing_fields,missing_fields)
    check('FIELD_DICTIONARY_CANONICAL_CLASSES',all(r['value_class'] in ['OBSERVED','DERIVED','MODEL','SCENARIO','UNKNOWN'] for r in dictionary),
          dict(fields=len(dictionary),note='Row-dependent rules and missing/HOLD overrides remain explicit'))
    raw=json.loads((OUT/'checks/raw_verification.json').read_text());v=json.loads((OUT/'verification.json').read_text())
    check('UPSTREAM_CHECK_RESULTS',raw['failed']==0 and v['failed']==0,dict(adapter_checks=v['passed'],raw_checks=len(raw['checks'])))
    result=dict(checks=checks,failed=sum(r['status']=='FAIL' for r in checks),passed=sum(r['status']=='PASS' for r in checks),counts=counts,
                acceptance='PACKAGE_AND_JOIN_RECOMPUTATION_ONLY; NOT_INDEPENDENT_REVIEW',network_used=False,
                sanitizer='Own-package text/CSV/JSON + scoped diff; raw kept outside Git; no credentials requested/read/copied')
    (OUT/'checks/package_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    handoff=json.loads((OUT/'handoff.json').read_text())
    handoff['package_checks']=dict(passed=result['passed'],failed=result['failed'],report='checks/package_verification.json',
                                   independent_review=False,sanitizer='PASS' if not sanitize_errors else 'FAIL')
    handoff['ready_for_review']=handoff['ready_for_review'] and result['failed']==0
    (OUT/'handoff.json').write_text(json.dumps(handoff,ensure_ascii=False,indent=2)+'\n')
    # Hash manifest excludes only itself and temporary bytecode. Evidence remains separate from runtime.
    outputs=[]
    grains={
        'candidate_register':'model_id × candidate_id',
        'candidate_airport_link':'model × candidate × source row × token_position; incidence',
        'ciri_stage1_scores':'model × author screening scenario × IATA',
        'product_path_template':'candidate × path template; not one sold itinerary',
        'route_program':'model × scenario × variant × origin_code × destination_code; undated aggregate',
        'physical_leg':'physical_leg_id; dated scenario requirement',
        'market_pool':'market_pool_id; directed endpoint OD × week × scenario',
        'itinerary':'itinerary_id; strategy/scenario/priority × dated endpoint journey allocation',
        'itinerary_leg':'itinerary_id × leg_sequence',
        'capacity_allocation':'itinerary_id × physical_leg_id × scenario × priority',
        'money_ledger':'ledger_row_id; whole itinerary account or physical-flight cost account',
        'resource_ledger':'model × candidate network × week',
        'evaluation_summary':'model × candidate strategy × scenario × priority × horizon',
        'parameter_registry':'model × candidate/scenario × parameter_id',
        'published_dated_evidence':'instance_id; published calendar expansion, not execution',
        'quarantine_preserved':'quarantine_id; frozen record-level hold',
        'candidate_regional_tourism':'model × candidate × entity × canonical region × indicator × year; non-additive incidence',
        'gateway_region_crosswalk':'airport_iata; reviewed region-context mapping',
        'airport_weather_month':'entity_code × station_id × month; historical station context',
        'weather_entity_coverage':'entity_code; selected endpoint directory admission',
        'observed_market_aggregates':'observation_id × version; entity/metric/period retained',
        'line_flow_context':'unordered airport-code pair; bidirectional annual line-segment model',
        'corporate_join_hold':'source site_id; site-airport travel relation UNKNOWN',
        'entity_resolution':'entity_code in selected models; source-directory version',
        'historical_findings':'finding_id × historically reviewed input SHA',
        'hypothesis_thresholds':'candidate × product template × paired cohort gap/fare/cost',
        'decision_ledger':'decision_id; explicit status and provenance',
        'coverage':'model × candidate × dataset × endpoint incidence',
        'coverage_summary':'model × dataset; counts of covered candidate/endpoint incidences',
        'source_manifest':'input_id × pinned Git blob',
        'primary_source_registry':'role × dataset_id × raw snapshot',
        'field_dictionary':'normalized table × field; row-dependent value-class rule',
        'model_input_usage':'model × source family; computational usage status',
        'feature_fitness':'feature × admitted decision scope',
        'feature_effects':'feature × fixed candidate filter × on/off diagnostic',
        'join_manifest':'join_id; cardinality/conservation boundary',
        'join_lineage':'join_id × left source row/token × right source row/key',
        'findings':'finding_id; own package boundary/result',
        'requests':'request_id; targeted missing evidence',
        'units_dictionary':'unit_id; definition/conversion/limit',
        'mapping':'model × source table × target table/fields; adapter transform',
        'compatibility':'left model × right model × comparison dimension',
    }
    for p in sorted(OUT.rglob('*')):
        if not p.is_file() or p.name=='outputs_manifest.json' or '__pycache__' in p.parts or p.suffix=='.pyc':continue
        b=p.read_bytes();rec=dict(path=p.relative_to(OUT).as_posix(),sha256=sha(b),bytes=len(b))
        if p.suffix=='.csv':
            with p.open(newline='',encoding='utf-8-sig') as f:rec['rows']=sum(1 for _ in csv.DictReader(f))
            rec['grain']=grains.get(p.stem,'Explicit check/receipt row; keys and scope named in header and associated verification report')
        outputs.append(rec)
    (OUT/'outputs_manifest.json').write_text(json.dumps(dict(files=outputs,self_excluded=True,temporary_bytecode_excluded=True,
               scope='Hashes prove package bytes; acceptance per verification files and handoff only'),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(passed=result['passed'],failed=result['failed'],files=len(outputs),bytes=sum(r['bytes'] for r in outputs)),ensure_ascii=False))
    if result['failed']:raise SystemExit(1)


if __name__=='__main__':main()
