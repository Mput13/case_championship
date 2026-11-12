"""Проверка происхождения, дат, вместимости времени и границ исследовательского пакета."""
import csv
import datetime as dt
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[4]
def sha(x):return hashlib.sha256(x).hexdigest()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def rows(name):
 with (ROOT/name).open(newline='') as f:return list(csv.DictReader(f))
def readj(name):return json.loads((ROOT/name).read_text())
def timestamp(x):return dt.datetime.fromisoformat(x.replace('Z','+00:00'))
def run():
 checks=[]
 def check(name,ok,details):checks.append({'check':name,'pass':bool(ok),'details':details})
 pins=readj('source_pins.json');cache={}
 for src in pins['input_files']:
  key=(src['commit'],src['git_path'])
  blob=subprocess.check_output(['git','show',src['commit']+':'+src['git_path']],cwd=REPO)
  check('source_file:'+src['git_path'],sha(blob)==src['sha256'],src['commit'])
  if src['git_path'].endswith('.csv'):cache[key]=list(csv.DictReader(blob.decode().splitlines(keepends=True)))
 records=rows('source_rows.csv');errors=[]
 for r in records:
  orig=cache[r['pinned_commit'],r['pinned_git_path']][int(r['source_csv_record_number'])-1]
  if sha(canonical(orig).encode())!=r['source_row_sha256']:errors.append(r['source_row_id'])
 check('all_selected_source_row_hashes',not errors,{'records':len(records),'errors':errors[:10]})
 primary=rows('evidence/SVX_primary_schedule_products.csv');errors=[]
 for r in primary:
  expected=r.pop('row_sha256')
  if sha(canonical(r).encode())!=expected:errors.append(r['record_id'])
  text=(ROOT/'evidence'/f'{r["source_id"]}_full_text.txt').read_bytes()
  if sha(text)!=r['source_text_sha256']:errors.append('text:'+r['record_id'])
 check('primary_schedule_hashes',not errors,{'records':len(primary),'errors':errors[:10]})
 live=readj('evidence/live_fetch_receipts.json')
 check('fetch_receipts_selected_texts',all(sha((ROOT/r['selected_text_path']).read_bytes())==r['selected_text_sha256'] for r in live if r['status'].startswith('HTTP_OK')),len(live))
 flights=rows('dated_templates/flights.csv');rot=rows('dated_templates/rotations.csv');airdays=rows('dated_templates/aircraft_days.csv')
 ids=[f['flight_instance_id'] for f in flights]
 check('flight_ids_unique',len(ids)==len(set(ids)),len(ids))
 check('utc_block_durations',all((timestamp(f['arrival_utc'])-timestamp(f['departure_utc'])).total_seconds()/60==int(f['block_minutes']) for f in flights),len(flights))
 byrot=defaultdict(list)
 for f in flights:byrot[f['rotation_id']].append(f)
 errors=[]
 for r in rot:
  legs=sorted(byrot[r['rotation_id']],key=lambda x:x['departure_utc'])
  if len(legs)!=2 or legs[0]['origin_airport']!='SVX' or legs[-1]['destination_airport']!='SVX' or legs[0]['destination_airport']!=legs[1]['origin_airport']:errors.append(r['rotation_id'])
  if sum(int(f['block_minutes']) for f in legs)!=int(r['block_minutes']):errors.append('block:'+r['rotation_id'])
 check('complete_rotations_and_sums',not errors,{'rotations':len(rot),'errors':errors[:10]})
 assignment=defaultdict(list)
 for f in flights:assignment[f['programme_id'],f['window_id'],f['scenario_unit_id']].append(f)
 errors=[]
 for fs in assignment.values():
  fs.sort(key=lambda x:x['departure_utc'])
  for a,b in zip(fs,fs[1:]):
   gap=(timestamp(b['departure_utc'])-timestamp(a['arrival_utc'])).total_seconds()/60
   if gap<45 or a['destination_airport']!=b['origin_airport']:errors.append((a['flight_instance_id'],b['flight_instance_id']))
 check('tail_continuity_turn_and_overlap',not errors,errors[:10])
 check('all_reference_days_u8',max(int(x['block_minutes']) for x in airdays)<=480,max(int(x['block_minutes']) for x in airdays))
 winter=[f for f in flights if f['window_id']=='2028-winter' and f['origin_airport']=='SVX']
 result={}
 expected={'SVX-U1':4,'SVX-U12':8,'SVX-U123':11,'SVX-U1234':11}
 for pid,n in expected.items():
  fs=[f for f in winter if f['programme_id']==pid];c=Counter(f['destination_airport'] for f in fs)
  result[pid]=dict(c);check('winter_pair_count:'+pid,len(c)==n,result[pid])
  exp={k:(12 if k in ['OMS','KUF','UFA','GOJ'] else 8) for k in c}
  if pid=='SVX-U1234':
   for k in ['OMS','KUF','UFA','GOJ']:exp[k]+=4
   for k in ['MRV','KJA']:exp[k]+=8
  check('winter_frequencies:'+pid,dict(c)==exp,{'actual':dict(c),'expected':exp})
 # Взаимоисключающие программы не объединяются в одну физическую ёмкость.
 targets=readj('programme_candidates.json')
 check('no_economics_invented',all(x['profit'] is None and x['passengers'] is None and x['cash_need'] is None for x in targets['programmes']),'Все денежные и спросовые выходы null; P05/P06 NOT_RUN')
 cal=rows('programme_calendar.csv')
 check('full24month_delivery_matrix',len(cal)==24*len(targets['programmes'])*4 and len({r['month'] for r in cal})==24,len(cal))
 check('no_new_TU214_in_maincase',all(r['new_TU214_count']=='0' for r in cal),'Отдельная явная ветвь0')
 check('no_new_SJ_before_H2_2027',all(r['new_SJ_eligible_by_case']=='False' for r in cal if r['month']<'2027-07'),'Eligibility не actual availability')
 assumptions={x['assumption_id'] for x in readj('assumptions.json')}
 check('assumption_ids_unique',len(assumptions)==len(readj('assumptions.json')),len(assumptions))
 dispositions=rows('hypothesis_dispositions.csv');required={'C07','C09','C10','C11','C14','C15','C16','C17','C18','C22','C26','C27','C31','C32','C33','C34','C35'}
 check('all17_legacy_hypotheses',required.issubset({r['legacy_id'] for r in dispositions}),sorted(required))
 check('C22_C26_not_silently_rejected',all('НЕВЫПОЛНЕНА' in next(r['stage_A_disposition'] for r in dispositions if r['legacy_id']==i) for i in ['C22','C26']),'Собственные ветви переданы; не экономический отказ')
 chains=rows('dated_templates/historical_chain_controls.csv')
 check('C17_summer_dated_in_summer',next(r['date'] for r in chains if r['control_id']=='C17-S').startswith('2028-07'),'Разные даты зимы/лета')
 check('no_retiming_without_KEEP_binding',all(r['matched_future_KEEP_flight_id']=='UNKNOWN' and r['action']=='REPLACE_CLOCK_ONLY_IF_MATCHED_KEEP_FLIGHT' for r in rows('dated_templates/retiming_actions.csv')),'Нельзя молча превратить REPLACE в ADD')
 check('stress_failure_visible',any(r['u8_exceeded']=='True' and r['block_multiplier']=='1.2' for r in rows('resource_sensitivity.csv')),'Исходный шаблон u8 не принимается при20% удлинении')
 manifest=ROOT/'manifest.json'
 if manifest.exists():
  mismatches=[]
  m=readj('manifest.json')
  for r in m['files']:
   path=ROOT/r['path']
   if not path.exists() or sha(path.read_bytes())!=r['sha256']:mismatches.append(r['path'])
  check('manifest_hashes',not mismatches,mismatches)
 return {'status':'PASS' if all(r['pass'] for r in checks) else 'FAIL','checks':checks,
  'scope':'Происхождение, арифметика и календарь исследовательского дизайна. Не операционная или коммерческая приёмка.',
  'not_run':['P05 calibration','P06 live RW programme evaluation','independent P06 acceptance','actual crews/MRO/slots','full cost/cash','final strategy']}

if __name__=='__main__':
 r=run()
 if '--record' in sys.argv:
  # Выполнять перед seal_package.py; после seal использовать read-only без --record.
  r['checks']=[x for x in r['checks'] if x['check']!='manifest_hashes']
  r['status']='PASS' if all(x['pass'] for x in r['checks']) else 'FAIL'
  (ROOT/'verification.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
 print(canonical({'status':r['status'],'checks':len(r['checks']),'failed':[x for x in r['checks'] if not x['pass']]}))
 sys.exit(0 if r['status']=='PASS' else 1)
