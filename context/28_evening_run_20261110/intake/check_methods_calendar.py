#!/usr/bin/env python3
"""Bounded accounting intake; independent v2 review still required."""
import csv, hashlib, io, json, math, subprocess
from collections import defaultdict
from pathlib import Path
SHA='aa7779192d809558e38b1eb9bdfa25913a3afdc8'
OLD='48686bf2276c435d7a260f4de6741c9b65d26e32'
ROOT='context/28_evening_run_20261110/methods/'
def blob(s,p): return subprocess.check_output(['git','show',s+':'+p])
def data(p): return blob(SHA,ROOT+p)
def rows(p): return list(csv.DictReader(io.StringIO(data(p).decode())))
def near(x,y): assert math.isclose(float(x),float(y),rel_tol=1e-9,abs_tol=1e-5),(x,y)
out=json.loads(data('output_manifest.json'))['files']
for r in out:
 b=data(r['path']);assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
source=json.loads(data('source_manifest.json'))['files']
for r in source:
 b=data(r['path']);assert b==blob(r['source_commit'],r['source_path']) and hashlib.sha256(b).hexdigest()==r['sha256']
old=json.loads(blob(OLD,ROOT+'output_manifest.json'))['files'];preserved=[]
for r in old:
 if r['path'].startswith(('inputs/','runs/selection_v1/')) or r['path'] in ('selection_experiment.py','verify_selection.py'):
  assert data(r['path'])==blob(OLD,ROOT+r['path']);preserved.append(r['path'])
daily=rows('runs/annual_v1/aircraft_calendar_daily.csv')
assert len({(r['branch'],r['availability'],r['date']) for r in daily})==len(daily)
for r in daily:
 assert int(r['received_new'])==int(r['in_entry_new'])+int(r['entered_new'])
 assert int(r['entered_new'])==int(r['planned_grounded_new'])+int(r['reserve_new'])+int(r['working_new'])
 assert int(r['reserve_new'])<=1 and min(int(r[k]) for k in ('working_new','entered_new','in_entry_new'))>=0
annual=rows('runs/annual_v1/annual_budget.csv');monthly=rows('runs/annual_v1/monthly_budget.csv')
keys=('branch','availability','scenario','network','year');groups=defaultdict(list)
for r in monthly: groups[tuple(r[k] for k in keys)].append(r)
sumfields=('calendar_days','working_aircraft_days','allocated_reserve_days','ticket_after_migration_rub','support_rub','variable_cost_rub','contribution_rub','journeys','segments')
for r in annual:
 ms=groups[tuple(r[k] for k in keys)];assert len(ms)==12
 for field in sumfields: near(sum(float(x[field]) for x in ms),r[field])
 near(float(r['ticket_before_migration_rub'])-float(r['foregone_ticket_rub']),r['ticket_after_migration_rub'])
 near(float(r['ticket_after_migration_rub'])+float(r['support_rub'])-float(r['variable_cost_rub']),r['contribution_rub'])
 near(float(r['journeys'])+float(r['transfer_journeys']),r['segments'])
 assert r['actual_future_support_rub']=='' and r['full_delta_pnl']==''
bound=rows('runs/support_v1/coupled_boundaries.csv');counter=rows('runs/support_v1/fare_constraint_counterexamples.csv');by={r['network_id']:r for r in bound}
for c in counter:
 r=by[c['network_id']]
 coupled=float(r['fare_constrained_net_receipts_upper_eta1'])+float(r['all_nonMOW_flight_cap_coefficient1'])-float(r['owner_variable_cost_rub_year'])
 near(coupled,r['contribution_at_eta1_all_flight_caps']);near(coupled,c['coupled_eta1_ceiling'])
 naive=float(r['owner_ticket_after_migration_rub_year'])+float(r['all_nonMOW_flight_cap_coefficient1'])-float(r['owner_variable_cost_rub_year'])
 near(naive,c['naive_replace_support_keep_owner_yield']);near(naive-coupled,c['overstatement_from_ignoring_fare_ceiling'])
 assert r['income_accepted_in_strategy']=='False'
result={'subject_sha':SHA,'status':'COORDINATOR_INTAKE_PASS_INDEPENDENT_REVIEW_PENDING','checks':{'output_hashes':len(out),'source_blobs':len(source),'v1_selected_files_byte_identical':len(preserved),'daily_resource_rows':len(daily),'annual_rows':len(annual),'monthly_rows':len(monthly),'month_to_year_equalities':len(annual)*len(sumfields),'support_examples':len(counter)},'not_run':['independent dated rotation construction/MCT validation','full N(t) policy/source validation','actual future subsidy rights and cash','full business replay or global optimum'],'qualifications':['Annual finance is active-day exposure of weekly offers, not fully dated ticket sales','Shadow passenger subsidy retained as author scenario only','Coupled grant/fare upper envelope not actual revenue','EV-MR01 does not cover this v2; new EV-MR02 required']}
Path(__file__).with_name('methods_calendar_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
