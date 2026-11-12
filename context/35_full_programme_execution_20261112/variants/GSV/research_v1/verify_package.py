"""Проверка доказательного пакета и seal. Не тест спроса, экономики или независимая приёмка."""
import argparse
import calendar
import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def read(name):return json.loads((ROOT/name).read_text())
def csvread(name):return list(csv.DictReader((ROOT/name).open()))
checks=[]
def check(name,ok,details=''):
    checks.append(dict(check=name,status='PASS' if ok else 'FAIL',details=details))

required=['case.json','evidence.csv','market_deltas.csv','hypotheses.json','programme_candidates.json','comparison_requests.csv','assumptions.csv','readiness.json','handoff.json']
check('required_outputs',all((ROOT/x).is_file() for x in required))
pins=read('source_pins.json'); bypin={x['pin_id']:x for x in pins}
check('unique_source_pin_ids',len(pins)==len(bypin))
contents={}
for pin in pins:
    b=subprocess.check_output(['git','show',pin['commit']+':'+pin['path']])
    check('exact_source_blob:'+pin['pin_id'],sha(b)==pin['sha256'])
    contents[pin['pin_id']]=b
selected=read('pinned_gsv_rows.json')
originals={k:list(csv.DictReader(io.StringIO(b.decode('utf-8-sig')))) for k,b in contents.items() if bypin[k]['path'].endswith('.csv')}
check('pinned_rows_bound_to_exact_source',all(x['pin_id'] in originals and originals[x['pin_id']][x['logical_row_ordinal']-1]==x['row'] and sha(canonical(x['row']))==x['canonical_row_sha256'] for x in selected),str(len(selected))+' выбранных строк')
receipts=read('fetch_receipts.json'); rs={x['source_id']:x for x in receipts}
check('retained_http_bytes_match_receipts',all((ROOT/x['local_path']).is_file() and sha((ROOT/x['local_path']).read_bytes())==x['sha256'] for x in receipts if 'local_path' in x))
check('wrong_resource_not_silently_admitted',all('content_assessment' in rs[x] for x in ['GSV-TERMINAL','GSV-SLOTS','GSV-SUMMER','GSV-IN-DECJAN']))
prog=read('programme_candidates.json')['programmes']; pids={x['programme_id'] for x in prog}; hyp=read('hypotheses.json')['hypotheses']; hids={x['hypothesis_id'] for x in hyp}
check('unique_programmes_hypotheses',len(pids)==len(prog) and len(hids)==len(hyp))
check('hypothesis_programme_references',all(set(x['programme_ids'])<=pids for x in hyp) and all(set(x['hypothesis_ids'])<=hids for x in prog))
check('all_hypotheses_have_explainable_outcome',all(x.get('outcome') and x.get('outcome_explanation') and x.get('distinguishing_test') and x.get('reconsideration_condition') for x in hyp))
check('no_new_Tu214_in_all_candidates',all(x['new_Tu214_count']==0 for x in prog))
assumptions={x['assumption_id'] for x in csvread('assumptions.csv')}
check('programme_assumptions_resolve',all(set(x['assumption_ids'])<=assumptions for x in prog))
delta=csvread('market_deltas.csv');check('market_deltas_bound',all(x['programme_id'] in pids for x in delta))
req=csvread('comparison_requests.csv');check('comparison_request_programmes_resolve',all(set(x['programme_ids'].split(';'))<=pids for x in req))
schedule=csvread('schedule_observations.csv')
check('schedule_row_hashes',all(sha(canonical([x['departure_local'],x['arrival_local'],x['weekdays'],x['period'],x['carrier'],x['flight'],x['aircraft'],x['destination'] if x['origin']=='GSV' else x['origin']]))==x['source_row_sha256'] for x in schedule))
check('schedule_source_hashes',all(x['source_sha256']==rs[x['source_id']]['sha256'] for x in schedule))
def find(sid,flight,periodpart):
    matches=[x for x in schedule if x['source_id']==sid and x['flight']==flight and periodpart in x['period']]
    assert len(matches)==1,(sid,flight,matches)
    return matches[0]
def minutes(clock):
    h,m=map(int,clock.split(':'));return h*60+m
arr=find('GSV-ARR-DECJAN','WZ-5047','23 дек');out=find('GSV-TIMETABLE-DECJAN','WZ-1751','23 дек')
ret=find('GSV-ARR-DECJAN','WZ-1752','23 дек');end=find('GSV-TIMETABLE-DECJAN','WZ-5048','28 окт')
diag=read('corridor_clock_check.json')
check('dated_corridor_connections_from_source',minutes(out['departure_local'])-minutes(arr['arrival_local'])==diag['outbound_connection_min']==175 and minutes(end['departure_local'])-minutes(ret['arrival_local'])==diag['inbound_connection_min']==160)
blocks=[minutes(arr['arrival_local'])-minutes(arr['departure_local'])+60,minutes(out['arrival_local'])-minutes(out['departure_local']),minutes(ret['arrival_local'])-minutes(ret['departure_local']),minutes(end['arrival_local'])-minutes(end['departure_local'])-60]
check('corridor_blocks_timezone_arithmetic',blocks==diag['scheduled_block_min'] and sum(blocks)==535)
span=minutes(end['arrival_local'])-minutes(arr['departure_local'])
check('corridor_span_not_single_ordinary_crew',span==diag['same_tail_elapsed_span_min']==920 and span>diag['ordinary_single_uninterrupted_crew_duty_limit_4_landings_min'])
rates={r['rate_id']:r for r in csvread('local_cost_drivers.csv')}
text=(ROOT/'sources/GSV-TARIFF-20261101.txt').read_text().split('\f')
check('local_rates_selected_pages',len(rates)==17 and '1 301,00' in text[0] and '1 090,00' in text[0] and '298,00' in text[1] and '575,00' in text[1] and '64,03' in text[7] and '31.12.2026' in text[13])
check('boarding_pass_locator_corrected_to_page8',rates['GSV-SECOND-BP']['source_locator'].startswith('PDF page 8'))
check('rate_quantities_and_future_rates_not_zero',all(x['quantity']=='UNKNOWN' and x['future_rate']=='UNKNOWN' for x in rates.values()))
foot=csvread('monthly_design_footprint.csv');months={f'{y}-{m:02}' for y in [2027,2028] for m in range(1,13)}
check('calendar_24_month_coverage',all({x['month'] for x in foot if x['programme_id']==p['programme_id']}==months for p in prog if p['routes']))
check('february2028_has29days',calendar.monthrange(2028,2)[1]==29)
for p in prog:
    if p['programme_id']=='PG-GSV-02':
        ff=[x for x in foot if x['programme_id']==p['programme_id'] and x['month']=='2028-02']
        check('radial_full_feb2028_one_RT_per_calendar_day',sum(int(x['conditional_template_roundtrips']) for x in ff)==29 and sum(int(x['conditional_template_oneway_segments']) for x in ff)==58)
check('monthly_pattern_not_admitted_or_forecast',all(x['admitted_flights']=='UNKNOWN' and x['status']=='TECHNICAL_PATTERN_NOT_APPROVED_FLIGHTS' for x in foot))
check('no_new_SJ_gate_before_H22027',all(x['new_SJ_earliest_case_gate']=='INELIGIBLE_PRE_H2_2027' for x in foot if x['month']<'2027-07'))
check('stage_boundaries_remain_explicit',read('readiness.json')['stage_B']=='REQUIRED' and read('readiness.json')['economic_winner']=='UNKNOWN' and read('readiness.json')['independent_acceptance']=='NOT_RUN')

parser=argparse.ArgumentParser();parser.add_argument('--seal',action='store_true');args=parser.parse_args()
if args.seal:
    report=dict(status='PASS' if all(x['status']=='PASS' for x in checks) else 'FAIL',scope='Source binding, package consistency, dated clock and calendar arithmetic. Не независимая приёмка рынка, расписания, crew compliance или экономики.',counts={'checks':len(checks),'pinned_rows':len(selected),'schedule_rules':len(schedule),'hypotheses':len(hyp),'programmes':len(prog),'deltas':len(delta),'comparison_requests':len(req),'local_cost_drivers':len(rates)},checks=checks)
    (ROOT/'verification_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    if report['status']!='PASS':
        print(json.dumps(report,ensure_ascii=False));raise SystemExit(1)
    files=[]
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file() or path.name=='output_manifest.json' or '__pycache__' in path.parts or path.name=='.DS_Store':continue
        b=path.read_bytes();files.append(dict(path=str(path.relative_to(ROOT)),sha256=sha(b),bytes=len(b)))
    manifest=dict(package_id='GSV-research-v1',schema_version=1,status='STAGE_A_COMPLETE_STAGE_B_REQUIRED',generated_at=dt.datetime.now(dt.timezone.utc).isoformat(),hash_algorithm='SHA256 exact file bytes',excluded=['output_manifest.json (self reference)','__pycache__',' .DS_Store'],file_count=len(files),total_bytes=sum(x['bytes'] for x in files),files=files)
    (ROOT/'output_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
else:
    manifest=read('output_manifest.json')
    check('manifest_hashes',all((ROOT/x['path']).is_file() and sha((ROOT/x['path']).read_bytes())==x['sha256'] and (ROOT/x['path']).stat().st_size==x['bytes'] for x in manifest['files']))
    actual={str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and p.name not in {'output_manifest.json','.DS_Store'} and '__pycache__' not in p.parts}
    check('manifest_complete',actual=={x['path'] for x in manifest['files']})
failed=[x for x in checks if x['status']!='PASS']
print(json.dumps(dict(status='FAIL' if failed else 'PASS',checks=len(checks),failed=failed,scope='Проверка пакета; Stage B не принят'),ensure_ascii=False))
raise SystemExit(bool(failed))
