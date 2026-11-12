#!/usr/bin/env python3
"""Offline handoff validation; no source build, money rerun or network."""
import sys
sys.dont_write_bytecode=True
import csv,hashlib,importlib.util,inspect,json,pathlib,subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
import jsonschema
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT).decode().strip()
def module(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
checks=[]
def check(name,value):
 checks.append(dict(check=name,pass_=bool(value)))
 if not value:raise AssertionError(name)
try:
 schema=read(HERE/'schemas.json');contract=read(HERE/'common_contract.json');manifest=read(HERE/'inputs_manifest.json')
 for target,data in [('contract',contract),('manifest',manifest)]:jsonschema.Draft202012Validator(schema[target]).validate(data)
 check('json_schema_contract_manifest',True)
 seed=list(csv.DictReader((HERE/'candidate_seed.csv').open()))
 for r in seed:jsonschema.Draft202012Validator(schema['seed_row']).validate(r)
 check('12_unique_unranked_unknown_candidates',len(seed)==12 and len({r['pair_key'] for r in seed})==12 and all(r['rank']=='' and r['classification']=='UNKNOWN_NOT_QUALIFIED' for r in seed))
 for r in manifest['entries']:
  p=HERE/r['snapshot'];check('snapshot_sha:'+r['snapshot'],sha(p)==r['sha256'])
  check('git_blob:'+r['path'],git('rev-parse',r['commit']+':'+r['path'])==r['git_blob'])
 baseline=read(HERE/'preservation_baseline.json')
 current_head=git('rev-parse','HEAD')
 head_drift=current_head!=baseline['head']
 check('baseline_head_is_requested_pin',baseline['head']=='79b48152ab8ff2a18648c7d6c5fb1df30525ba01')
 check('1190_protected_unchanged',len(baseline['protected'])==1190 and all(sha(ROOT/p)==s for p,s in baseline['protected'].items()))
 check('historical_protected_matches',baseline['historical_protected_manifest_matches'])
 check('tracked_files_unchanged',not git('diff','--name-only','HEAD'))
 check('window_dates',datetime.fromisoformat('2027-02-02').isoweekday()==2 and datetime.fromisoformat('2027-02-05').isoweekday()==5)
 def utc(day,clock,zone):return datetime.fromisoformat(day+'T'+clock).replace(tzinfo=ZoneInfo(zone)).timestamp()
 def mins(a,b):return (b-a)/60
 d='2027-02-02';s='Asia/Yekaterinburg';a='Europe/Moscow'
 old=[mins(utc(d,'14:00',s),utc(d,'17:30',a)),mins(utc(d,'18:30',a),utc(d,'23:00',s))]
 corrected=[mins(utc(d,'14:00',s),utc(d,'15:30',a)),mins(utc(d,'16:30',a),utc(d,'22:00',s))]
 check('P33_bug_and_canonical_UTC',old==[330,150] and corrected==[210,210] and mins(utc(d,'15:30',a),utc(d,'16:30',a))==60)
 p31=ROOT/'context/31_direct_growth_research_20261112'
 re=module('p34_readonly_economics_probe',p31/'route_economics/calculate.py')
 ops=module('p34_readonly_ops_probe',p31/'ops_inputs/calendar_engine.py')
 delay=module('p34_readonly_delay_probe',ROOT/'context/32_delay_cargo_research_20261112/calculation/calculate.py')
 check('APIs_importable',all(callable(x) for x in [re.evaluate_combined_programme,ops.generate,delay.replay,delay.flight]))
 # Preserve narrow API evidence; no economic evaluation. One physical sector tests weekly frequency semantics.
 f=dict(flight_instance_id='PROBE',origin_airport='SVX',destination_airport='KJA',departure_utc='2027-02-02T09:00:00Z',arrival_utc='2027-02-02T12:00:00Z',saleable_seats=100,block_hours_costscreen=3)
 bundle=re.choice_bundle([f],'base',{('SVX','KJA')},'2027-02-01','2027-02-07')
 products=[p for p in bundle['products'] if p.get('owner')=='RW']
 # Field name comes from pinned P05 product schema.
 freq=[p.get('frequency_week',p.get('frequency')) for p in products]
 check('weekly_adapter_defect_source_guard','len(inventory)*7/calendar.monthrange(y,m)[1]' in inspect.getsource(re.choice_bundle))
 deps=read(HERE/'dependency_receipt.json')
 for r in deps:check('dependency:'+r['path'],sha(ROOT/r['path'])==r['sha256'])
 check('fresh_step1_inputs_unchanged_from_old_pin',all(git('rev-parse','6cbe817320f75db9823984e7c4eeb6091fd7d996:'+p)==git('rev-parse','dceadc98f9a293d7530cb7bc50ca4411a95aa4b6:'+p) for p in ['data/manual/rw_routes_now.csv','data/assumptions/network.csv']))
 if (HERE/'output_hashes.json').exists():
  for path,expected_hash in read(HERE/'output_hashes.json').items():check('artifact:'+path,sha(HERE/path)==expected_hash)
 check('48_oldscreen_rows',len(list(csv.DictReader((HERE/'source_snapshot/p31_fastscreen_12pairs.csv').open())))==48)
 expected={'OMS-PEE','OMS-REN','SVX-KJA'}
 check('three_P08_matches',{r['pair'] for r in seed if r['p08_pair_present']=='True'}==expected)
 output=dict(status='PASS_WITH_HEAD_DRIFT' if head_drift else 'PASS',head_observation=dict(start=baseline['head'],end=current_head,unchanged=not head_drift,git_mutations_by_this_agent=False),schema='JSON Schema draft2020-12 via jsonschema',checks_passed=len(checks),checks=checks,API_signatures=dict(joint=str(inspect.signature(re.evaluate_combined_programme)),calendar=str(inspect.signature(ops.generate)),delay=str(inspect.signature(delay.replay))),P33_UTC=dict(original=old,canonical=corrected),weekly_frequency_defect=dict(one_departure_reported_frequency=freq,expected_per_week=1,admission='BLOCK_NUMERIC_JOINTCALC_UNTIL_NEW_AREA_ADAPTER_FIXED'),protected_files=1190,new_money_results=False,external_research_read=False)
except Exception as e:
 output=dict(status='FAIL',checks=checks,error=repr(e))
(HERE/'validation.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in output.items() if k in ['status','checks_passed','error','weekly_frequency_defect']},ensure_ascii=False))
if output['status']=='FAIL':raise SystemExit(1)
