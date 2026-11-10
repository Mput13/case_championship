#!/usr/bin/env python3
"""Bounded intake of final network programs; separate from fresh review."""
import csv, datetime as dt, hashlib, io, json, math, subprocess
from pathlib import Path
SHA='b47118a48b6d5480217077bf8699a63665c0eb7a';OLD='941d9ebfe97c86baa210da2c56bb1f94cbe298b0'
ROOT='context/28_evening_run_20261110/network/';V=ROOT+'v2/'
def blob(s,p):return subprocess.check_output(['git','show',s+':'+p])
def data(p):return blob(SHA,V+p)
def rows(p):return list(csv.DictReader(io.StringIO(data(p).decode())))
def near(x,y):assert math.isclose(float(x),float(y),rel_tol=1e-9,abs_tol=1e-5),(x,y)
oldpaths=subprocess.check_output(['git','ls-tree','-r','--name-only',OLD,ROOT]).decode().splitlines()
assert len(oldpaths)==25
for p in oldpaths:assert blob(OLD,p)==blob(SHA,p)
out=json.loads(data('output_manifest.json'))['files']
for r in out:
 b=data(r['path']);assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
copied=0
for name in ('additional_input_manifest.json','final_evidence_input_manifest.json'):
 for r in json.loads(data(name))['inputs']:
  b=blob(SHA,ROOT+r['local']);assert b==blob(r['commit'],r['path'])
  assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'];copied+=1
c01=rows('outputs/C01_synchronization.csv');c33=rows('outputs/C33_retiming.csv')
for r in c01:
 near(float(r['ticket_revenue_unsync_rub_week'])-float(r['fixed_flight_cost_rub_week'])-float(r['pax_cost_unsync_rub_week']),r['contribution_unsync_rub_week'])
 near(float(r['ticket_revenue_sync_rub_week'])-float(r['fixed_flight_cost_rub_week'])-float(r['pax_cost_sync_rub_week']),r['contribution_sync_rub_week'])
 near(float(r['contribution_sync_rub_week'])-float(r['contribution_unsync_rub_week']),r['delta_contribution_rub_week'])
 near(float(r['total_journeys_week'])+float(r['new_through_journeys_week']),r['segments_week'])
 near(2*(150+145+155+140)/60,r['block_hours_week'])
bridge=rows('outputs/first_to_final_bridge.csv')
for r in bridge:
 near(float(r['final'])-float(r['first_slice']),r['delta'])
 if r['network']=='C01':
  loss=float(r['metric'].split('loss')[1]);x=next(x for x in c01 if x['scenario']==r['scenario'] and float(x['local_loss_fraction_south'])==loss)
  near(x['contribution_sync_rub_week'],r['final'])
for r in c33:
 near(float(r['ticket_revenue_after_rub_week'])-float(r['ticket_revenue_before_rub_week'])-float(r['delta_pax_cost_rub_week']),r['delta_contribution_rub_week'])
 near(r['delta_contribution_rub_week'],r['Kmax_retiming_rub_week'])
 assert float(r['extra_block_minutes'])==0
 # Extra-aircraft field is explicitly conditional; full next-task availability is not admitted.
 assert 'L_changed_slots' in r['full_result_formula']
flights=rows('outputs/dated_flights.csv')
assert len({(r['network'],r['variant'],r['tail_scenario'],r['flight_id']) for r in flights})==len(flights)
for r in flights:
 dep=dt.datetime.fromisoformat(r['departure_utc']);arr=dt.datetime.fromisoformat(r['arrival_utc'])
 near((arr-dep).total_seconds()/60,r['block_minutes'])
 assert dep==dt.datetime.fromisoformat(r['departure_local']) and arr==dt.datetime.fromisoformat(r['arrival_local'])
nexttask=rows('outputs/C33_next_assignment.csv')
opportunity=dt.datetime.fromisoformat('2026-12-09T07:25:00+05:00')
for r in nexttask:
 near((opportunity-dt.datetime.fromisoformat(r['tail_ready_SVX_local'])).total_seconds()/60,r['slack_minutes'])
 assert r['actual_tail_assignment']=='UNKNOWN'
assert any(float(r['slack_minutes'])<0 for r in nexttask)
baseline=rows('outputs/C33_final_published_baseline.csv')
source=list(csv.DictReader(io.StringIO(blob('38f0f7ae8a10b6a60bd2d5ab39b18a9865e2b78b','context/28_evening_run_20261110/evidence/dated_service_instances.csv').decode())))
def key(r):return tuple(r[k] for k in ('origin','destination','date','flight'))
index={key(r):r for r in source}
assert len(baseline)==8
for r in baseline:
 for field in ('departure_local','arrival_local','clock_or_type_conflict','source_ids','publication_records'):
  assert r[field]==index[key(r)][field]
result={'subject_sha':SHA,'status':'COORDINATOR_INTAKE_PASS_INDEPENDENT_REVIEW_PENDING','checks':{'old_files_byte_identical':len(oldpaths),'v2_output_hashes':len(out),'new_copied_source_blobs':copied,'C01_rows':len(c01),'C33_rows':len(c33),'change_bridge_rows':len(bridge),'dated_flights':len(flights),'C33_next_assignment_rows':len(nexttask),'C33_exact_published_matches':len(baseline)},'material_qualifications':['C01 total contribution changed with directional time analogue; synchronization delta unchanged','C33 same flight count/block time does not preserve next tail assignment','C03/C04 local dated programs and ideal-bank upper bound are separate','C07/C33 share WZ5071/5072 and cannot be added independently','Diagnostic week is not annual forecast; full resource/market/budget not admitted'],'not_run':['independent LP/solver replay','full resource calendar and future N(t)','actual tail assignment or passenger inventory','supported compliant PnL']}
Path(__file__).with_name('network_final_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
