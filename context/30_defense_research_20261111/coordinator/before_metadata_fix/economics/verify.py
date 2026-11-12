"""Run calculate twice, verify identities and provenance. No writes outside economics."""
import sys,os,json,csv,hashlib,subprocess,math
from pathlib import Path
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent;ROOT=OUT.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def rows(name):return list(csv.DictReader((OUT/name).open()))
inputs=list((ROOT/'inputs/model_schedule/latest').rglob('*'))
for folder,names in {'model_schedule':['freeze.md','freeze.json','fixed_networks.csv','replay_receipt.json','replay_inputs_manifest.json','scheduling_notes.md'],'review_costs':['review.md','accepted_cost_inputs.csv','support_inputs.csv','findings.csv','validation.json'],'review_evidence':['review.md','buyers_opportunities_corrected.csv','findings.csv'],'coordinator':['cost_items_corrected.csv','support_conditions_corrected.csv'],'base_costs':['costs.md','cost_items.csv','support_conditions.csv','sources.csv','validation.json'],'inputs/fuel_review':['calculation.json','report.md','handoff.md','fuel_sensitivity.csv','source_manifest.json','verification.json']}.items():
 inputs += [ROOT/folder/n for n in names]
inputs += [ROOT/'TASKS.md',ROOT/'pins.json']
before={str(p):sha(p) for p in inputs if p.is_file()};checks=[]
def check(n,ok):checks.append(dict(check=n,passed=bool(ok)))
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
cmd=[sys.executable,str(OUT/'calculate.py')]
subprocess.run(cmd,env=env,cwd=OUT,check=True)
names=['baseline_ledger.csv','fixed_network_sensitivities.csv','seasonality_cases.csv','breakeven_frontier.csv','network_comparison.csv','findings_admission.csv']
first={n:sha(OUT/n) for n in names}
subprocess.run(cmd,env=env,cwd=OUT,check=True)
check('deterministic_two_actual_runs',first=={n:sha(OUT/n) for n in names})
check('all_named_inputs_unchanged',before=={p:sha(Path(p)) for p in before})
manifest=json.loads((ROOT/'model_schedule/replay_inputs_manifest.json').read_text())
for entry in manifest['files']:
 p=Path(entry['local_path'])
 if not p.is_absolute():p=ROOT/'inputs/model_schedule'/p
 check('frozen_input_hash_'+entry['path'],p.is_file() and sha(p)==entry['sha256'])
baseline=rows(names[0]);close=lambda a,b:abs(a-b)<.02
for b in baseline:
 n=b['network_id'];f=lambda k:float(b[k])
 check(n+'_ticket_before_after',close(f('ticket_before_forgone_rub')-f('forgone_rw_rub'),f('net_ticket_rub')))
 check(n+'_revenue_grant_once',close(f('net_ticket_rub')+f('route_grant_rub'),f('revenue_net_rub_year')))
 check(n+'_credit_net_once',close(f('gross_fuel_rub')-f('fuel_credit_rub'),f('net_fuel_rub')))
 check(n+'_fuel_units',close(f('fuel_tonnes')*f('fuel_price_rub_t'),f('gross_fuel_rub')))
 check(n+'_contribution',close(f('revenue_net_rub_year')-f('cost_rub_year'),f('contribution_rub_year')))
 check(n+'_cost',close(f('net_fuel_rub')+f('other_variable_rub'),f('cost_rub_year')))
 for r in rows('fixed_network_sensitivities.csv'):
  if r['network_id']!=n or r['case']!='PURE_RECEIPTS_MULTIPLIER_FIXED_PASSENGERS':continue
  expected=f('contribution_rub_year')+(float(r['k_rub_t'])-32930)*f('fuel_tonnes')+(float(r['s'])-1)*f('ticket_before_forgone_rub')
  check(n+'_pure_credit_receipts_identity',close(expected,float(r['Fmax_rub_year'])))
 for r in rows('seasonality_cases.csv'):
  if r['network_id']!=n:continue
  check(n+'_fixed_weekly_flights',close(float(r['flights_week']),f('flights_week')))
  if r['case']=='UNCHANGED_WEEKLY_PROFILE':
   for k in ('contribution_rub_year','passenger_segments_year','fuel_tonnes','revenue_net_rub_year'):
    check(n+'_period_'+r['period_weeks']+'_'+k,close(float(r[k]),f(k)*float(r['period_weeks'])/52))
 for r in rows('breakeven_frontier.csv'):
  if r['network_id']!=n or not r.get('required_credit_rub_t'):continue
  F=float(r['F_budget_axis_rub_year']);k=float(r['k_rub_t'])
  check(n+'_credit_frontier',close(f('contribution_rub_year')+(float(r['required_credit_rub_t'])-32930)*f('fuel_tonnes'),F))
  check(n+'_receipts_frontier',close(f('contribution_rub_year')+(k-32930)*f('fuel_tonnes')+(float(r['required_receipts_or_fare_multiplier'])-1)*f('ticket_before_forgone_rub'),F))
check('zero_new_demand_admission',all(r['additional_passengers']=='0' and r['numeric_model_update']=='0' for r in rows('findings_admission.csv')))
checks+=json.loads((OUT/'calculation_checks.json').read_text())['checks']
errors=[c for c in checks if not c['passed']]
unknowns=['RW credit entitlement, eligible tonnes and actual cash lag','monthly primary OD and actual retained demand/yield','F after overlap reconciliation; lease/capital or donor opportunity cost','A; deposits; working capital; VAT/tax/full PnL','actual fleet slots crews MCT and through ticket; SJ100 PD8 readiness','pilot frequencies and economics; launch approval']
(OUT/'validation.json').write_text(json.dumps(dict(status='PASS_ARITHMETIC_WITH_UNKNOWNS' if not errors else 'FAIL',checks_count=len(checks),errors=errors,unknowns=unknowns,determinism=first,checks=checks,operational_failures=['ramp high blocks161.5h>140','22 far-end turn failures'],note='Technical errors separated from operational FAIL and UNKNOWN'),ensure_ascii=False,indent=2)+'\n')
outputs=names+['calculate.py','verify.py','README.md','calculation_checks.json','validation.json']
(OUT/'manifest.json').write_text(json.dumps(dict(pin='0b0fbcb742ea2e54e05b80a5b8e890200fd5daae',inputs=[dict(path=p,sha256=h) for p,h in sorted(before.items())],outputs=[dict(path=n,sha256=sha(OUT/n),bytes=(OUT/n).stat().st_size) for n in outputs],runtime=sys.executable,environment=json.loads((OUT/'calculation_checks.json').read_text())['environment'],writes='economics only; no source edits, commits, research, new passengers or optimizer',adapter='Pinned hub build with frequency iteration replaced in memory by frozen frequencies; direct joint with fixed_selection and empty candidate list; no source mutation'),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(checks=len(checks),errors=len(errors),unknowns=len(unknowns))))
raise SystemExit(bool(errors))
