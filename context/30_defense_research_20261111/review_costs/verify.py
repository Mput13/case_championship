#!/usr/bin/env python3
"""Read-only checks of finished inputs; writes only review_costs/validation.json."""
from pathlib import Path
import csv,json,hashlib,math,datetime
P=Path(__file__).resolve().parent; B=P.parent
checks=[]
def ok(name,condition,detail=''):
 checks.append(dict(check=name,passed=bool(condition),detail=detail))
def loadcsv(p):
 with p.open(newline='') as f:
  rows=list(csv.reader(f));ok('CSV width '+p.name,all(len(r)==len(rows[0]) for r in rows[1:]));return list(csv.DictReader(p.open(newline='')))
def near(a,b,tol=1e-5):return abs(a-b)<=tol
h=json.loads((P/'input_hashes.json').read_text());ok('Named inputs unchanged since review baseline',all(hashlib.sha256((B/k).read_bytes()).hexdigest()==v for k,v in h.items()),str(len(h)))
m=json.loads((B/'inputs/latest_panel/source_manifest.json').read_text());ok('Four pinned snapshot hashes',len(m['files'])==4 and all(hashlib.sha256((B/'inputs/latest_panel'/x['path']).read_bytes()).hexdigest()==x['sha256'] for x in m['files']))
cost=loadcsv(P/'accepted_cost_inputs.csv');support=loadcsv(P/'support_inputs.csv');findings=loadcsv(P/'findings.csv')
for rows in [cost,support]:
 ok('Unique IDs',len({r['id'] for r in rows})==len(rows))
 ok('UNKNOWN has no numeric value',all(not r['value'] for r in rows if r['status']=='UNKNOWN'))
 ok('Provenance and calculator gate',all(r['source'] or r['path'] for r in rows) and all(r['admission_gate'] and r['effectiveperiod'] and r['tax'] for r in rows))
ok('No additive admission',not any(r['calculator_action']=='add' for r in cost+support))
params={r['parameter'] if 'parameter' in r else next(iter(r.values())):r for r in csv.DictReader((B/'inputs/latest_panel/data/assumptions/network.csv').open())}
# CSV uses parameter key in first column; verify actual header names without assuming them.
with (B/'inputs/latest_panel/data/assumptions/network.csv').open() as f:
 raw=list(csv.reader(f))
vals={r[0]:(r[1],r[2]) for r in raw[1:]}
ok('Existing model cost and credit parameters',all(vals[k]==v for k,v in {'ground_rub_per_flight':('96089','115307'),'fuel_rub_per_t':('134896','161696'),'fuel_compensation_rub_per_t':('32930','3024')}.items()) and 133200+1696==134896)
repair=json.loads((B/'coordinator/csv_repair.json').read_text())
ok('Original CSV hashes equal coordinator receipts',hashlib.sha256((B/'base_costs/cost_items.csv').read_bytes()).hexdigest()==repair['original_sha256'] and hashlib.sha256((B/'base_costs/support_conditions.csv').read_bytes()).hexdigest()==repair['support_original_sha256'])
ok('3024 net excise arithmetic',near(2800*(2.08-1),3024))
d=json.loads((B/'inputs/fuel_review/calculation.json').read_text())
ok('Saved precise series mean arithmetic',near(sum(d['monthly_precise_series'])/9,32930.28333333333) and round(sum(d['monthly_precise_series'])/9)==32930,'Series itself inherited from saved Reuters/TMT citation; not independently authenticated')
net=d['fixed_new_network'];zero=net[0]
for r in net:
 legs=r['legs'];tonnes=sum((1.55*x['block_h']+.2)*2*x['freq_each_way']*52 for x in legs)
 ok('Saved OMS12 fuel and contribution credit '+str(r['credit_rub_per_t']),near(tonnes,r['fuel_tonnes_year']) and near(tonnes*r['credit_rub_per_t'],r['credit_rub']) and near(r['fuel_gross_rub']-r['credit_rub']+r['nonfuel_cost_rub'],r['cost_rub']) and near(r['revenue_rub']-r['cost_rub'],r['contribution_rub']))
ok('18391.64 threshold before omitted costs',near(-zero['contribution_rub']/zero['fuel_tonnes_year'],18391.640281474378))
routes=list(csv.DictReader((B/'inputs/latest_panel/data/processed/network_routes.csv').open()));routes=[r for r in routes if r['scenario']=='base' and r['variant']=='Хаб OMS' and r['from']=='OMS']
by={r['to']:r for r in routes};leg=net[2]['legs']
ok('Current OMS12 route/frequency and rounded km agree with saved review',set(by)=={r['to'] for r in leg} and all(float(by[x['to']]['freq_week_each_way'])==x['freq_each_way'] and abs(float(by[x['to']]['km'])-x['km'])<=.5 for x in leg) and sum(2*float(r['freq_week_each_way']) for r in routes)==138)
ok('Current rounded route revenues and allocated results agree',all(abs(float(by[x['to']]['revenue_mln_year'])-x['rev_rub']/1e6)<=.051 and abs(float(by[x['to']]['result_mln_year'])-x['allocated_result_rub']/1e6)<=.051 for x in leg))
summary=list(csv.DictReader((B/'inputs/latest_panel/data/processed/network_summary.csv').open()));q=next(r for r in summary if r['scenario']=='base' and r['hub']=='OMS')
ok('Current OMS base summary 12/7 503',q['routes']=='12' and q['aircraft']=='7' and q['flights_week']=='138' and abs(float(q['result_mln_year'])-net[2]['contribution_rub']/1e6)<.5)
oldmanifest=json.loads((B/'inputs/fuel_review/source_manifest.json').read_text());comparisons=[]
for x in m['files']:
 old=next((r for r in oldmanifest if r['pin']=='new' and r['path']==x['path']),None)
 comparisons.append(dict(path=x['path'],sha256_same_as_dc1=bool(old and old['sha256']==x['sha256'])))
ok('Different commits are not asserted byte-identical',not all(x['sha256_same_as_dc1'] for x in comparisons))
ok('UFA PDF hash agrees with saved review',hashlib.sha256((P/'receipts/ufa_fuel.pdf').read_bytes()).hexdigest()=='2099eebce85b10435715ce3aae126866c51b4938f74affbba43432e9ea1bf644')
attempts=json.loads((P/'receipts/source_checks.json').read_text());ok('Bounded access budget',len(attempts['external_attempts'])==8 and attempts['tax_primary_sources']==4)
ok('Review word limit',len((P/'review.md').read_text().split())<=1500)
result=dict(status='PASS_SCOPED_WITH_UNKNOWNS' if all(x['passed'] for x in checks) else 'FAIL',checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),numeric_updates_to_model=0,checks=checks,version_comparison=comparisons,limitations=['No current OMS tariff body obtained; no contract price admission','No full economic model replay; arithmetic from saved legs and visible rounded snapshot comparison only','Actual RW eligibility/tonnes/tax ledger/cash lag UNKNOWN','No independent reopening of art192/203/204; timing remains inherited and conditional','Baseline hashes record named finished inputs at artifact build, not a whole-worktree before/after audit','No unfinished model_schedule or review_evidence contents read'])
(P/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'checks':len(checks),'failed':[x for x in checks if not x['passed']]},ensure_ascii=False))
raise SystemExit(0 if all(x['passed'] for x in checks) else 1)
