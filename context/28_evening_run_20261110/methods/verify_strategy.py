"""Source-cell and bounded synthesis checks, separate from independent review."""
import csv,hashlib,json,math,subprocess
from model_kernel import ROOT
def read(p):return list(csv.DictReader((ROOT/p).open()))
checks=[]
def check(name,ok):
 assert ok,name
 checks.append(name)
options=read('strategy/finite_options.csv');routes=read('strategy/option_routes.csv')
check('24 finite options unique',len(options)==24 and len({r['option'] for r in options})==24)
for r in options:
 rr=[x for x in routes if x['option']==r['option']];pairs={tuple(sorted((x['origin'],x['destination']))) for x in rr}
 check('distinct route count '+r['option'],len(pairs)==int(r['model_endpoint_pairs']))
 check('resource sum '+r['option'],int(r['total_planning_tails'])==int(r['constructed_working_tails'])+1)
 check('not actual accepted '+r['option'],r['actual_resource_market_fullPnL']=='UNKNOWN')
# Independent closed form for two equal open-market f2 offers pooled at f4.
net=json.loads((ROOT/'runs/selection_v1/networks.json').read_text())
for s in ('base','cautious'):
 r=next(r for r in read('strategy/mixed11_routes.csv') if r['scenario']==s and {r['origin'],r['destination']}=={'KUF','OMS'})
 scale=net[f'AUTHOR_52_48_CONCENTRATED/{s}/OMS/GREEDY/cap4']['assumptions']['capture_freq_scale']
 q2=float(r['naive_independent_local_journeys'])/2;q4=q2*(1+math.exp(-2/scale))
 check('open f4 closed form '+s,abs(q4-float(r['pooled_local_journeys']))<1e-7 and q2<=q4<=2*q2)
 summary=next(x for x in read('strategy/mixed11_budget.csv') if x['scenario']==s)
 correction=sum(float(x['contribution_correction']) for x in read('strategy/mixed11_routes.csv') if x['scenario']==s)
 check('mixed money conservation '+s,abs(float(summary['shared_market_corrected_contribution'])-float(summary['naive_sum_contribution'])-correction)<1e-7)
 check('mixed11 pair and flight grain '+s,summary['distinct_endpoint_pairs']=='11' and summary['route_program_rows']=='12' and summary['flights_week']=='48')
cards=read('strategy/hypothesis_decisions.csv');required={r['id'] for r in read('inputs/contract_4a997/hypotheses.csv')}
check('exact ten required IDs',{r['id'] for r in cards}==required and len(cards)==10)
columns={'C01':'delta_contribution_rub_week','C03':'Kmax_extra_KUF_base_minus_deployment_lodging_rub_week','C04':'contribution_rub_week','C07':'delta_contribution_rub_week','C33':'delta_contribution_rub_week','C10':'minimum_guarantee_return_per_person','C14':'minimum_package_price_per_person','C17':'minimum_summer_paid_people_each_leg','C31':'maximum_tu_new_allin_cost_plus_K','C35':'maximum_integration_retime_risk_K'}
for r in cards:
 sr=read(r['input_path']);col=columns[r['id']]
 for s,field in [('base','base_value'),('cautious','cautious_value')]:
  matching=[x for x in sr if x['scenario']==s and col in x and x[col] and abs(float(x[col])-float(r[field]))<1e-7]
  check('source numeric cell '+r['id']+'/'+s,bool(matching))
check('35 hypotheses preserved',len(read('strategy/hypothesis_queue35.csv'))==35)
check('25 retained untested',sum(r['evening_status']=='RESERVED_NOT_TESTED_THIS_WINDOW' for r in read('strategy/hypothesis_queue35.csv'))==25)
# The current synthesis does not edit reviewed v3 inputs, runs, or computational code.
sha='f99d6cd52dcc06995bf984fddd2f057226243b06';prefix='context/28_evening_run_20261110/methods/'
old=json.loads(subprocess.check_output(['git','show',sha+':'+prefix+'output_manifest.json']))
preserved=[]
for r in old['files']:
 if r['path'] in ('handoff.json','requests.json','progress.md','README.md'):continue
 check('v3 bytes '+r['path'],hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256']);preserved.append(r['path'])
(ROOT/'strategy/verification.json').write_text(json.dumps(dict(status='PASS_OWNER_SCOPED',checks=len(checks),preserved_v3_subject=sha,preserved_v3_files=len(preserved),checks_run=checks,independent_review='NOT_INHERITED; EV-MR03 exactf99 only'),indent=2)+'\n')
print(json.dumps(dict(checks=len(checks),preserved_v3=len(preserved),status='PASS_OWNER_SCOPED')))
