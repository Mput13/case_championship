"""Bounded acceptance: read inputs; write acceptance/verification.json only."""
from pathlib import Path
import csv, json, hashlib, subprocess, math
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
AUD=OUT.parent
PIN='d4a6eabb42671e5b16d44abedcdc6ceafb692528'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p): return list(csv.DictReader(p.open()))
def close(a,b): assert abs(a-b)<0.001,(a,b)
assert subprocess.run(['git','merge-base','--is-ancestor',PIN,'HEAD'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
protected=json.loads((AUD/'protected_owner_files.json').read_text())
assert len(protected)==389
assert all(sha(ROOT/p)==h for p,h in protected.items())
A={r['parameter']:float(r['base']) for r in rows(ROOT/'data/assumptions/network.csv')}
ledger=rows(AUD/'replay/ledger.csv'); legs=[r for r in ledger if r['record_type']=='leg']; od=[r for r in ledger if r['record_type'].startswith('od_')]
assert len(legs)==12 and len(od)==36
s=lambda rs,k: math.fsum(float(r[k]) for r in rs)
T=s(od,'ticket_gross_rub_year'); F=s(od,'foregone_rw_rub_year'); S=s(od,'subsidy_rub_year')
for r in od:
 close(float(r['ticket_gross_rub_year']),float(r['trips_year'])*float(r['fare_rub_per_trip']))
 close(float(r['subsidy_rub_year']),float(r['eligible_segments_year'])*A['subsidy_rub_per_pax'])
for r in legs:
 hours=float(r['block_hours_year']); flights=float(r['flights_year']); pax=float(r['segments_year'])
 fuel=(hours*A['fuel_t_per_hour']+flights*A['fuel_t_per_cycle'])*A['fuel_rub_per_t']
 cost=fuel+hours*(A['mro_rub_per_hour']+A['crew_rub_per_hour']+A['navigation_rub_per_hour'])+flights*(A['ground_rub_per_flight']+A['deicing_rub_per_flight'])+pax*A['pax_cost_rub']
 close(cost,float(r['variable_cost_rub_year']))
for r in od:
 if r['record_type']=='od_local':
  leg=next(x for x in legs if x['b']==r['b'])
  close(float(r['fare_rub_per_trip']),A['fare_fixed_rub']+A['fare_per_km_rub']*float(leg['km']))
V=s(legs,'variable_cost_rub_year'); C=T-F+S-V; C0=T-F-V
close(C,387722372.7102387); close(C0,-706409621.3819437)
close(T,s(legs,'ticket_gross_rub_year')); close(S,s(legs,'subsidy_rub_year'))
close(s(legs,'segments_year'),s(od,'segments_year'))
cf={r['case']:r for r in rows(AUD/'replay/counterfactuals.csv')}
for network in ('base8','base_sub12'):
 x,y=[cf[network+'_support'+str(i)] for i in (0,1)]
 for k in ('ticket_gross_rub_year','foregone_rw_rub_year','variable_cost_rub_year','segments_year','od_trips_year','flights_year','block_hours_year'):
  assert x[k]==y[k],k
 close(float(y['contribution_rub_year'])-float(x['contribution_rub_year']),float(y['subsidy_rub_year']))
summary=rows(ROOT/'data/processed/network_summary.csv')
rounding=[{'row':i+2,'scenario':r['scenario'],'variant':r['variant'],'display':float(r['revenue_mln_year'])-float(r['var_cost_mln_year']),'author':float(r['result_mln_year'])} for i,r in enumerate(summary) if float(r['revenue_mln_year'])-float(r['var_cost_mln_year'])!=float(r['result_mln_year'])]
assert len(rounding)==6
inputs=json.loads((ROOT/'context/12_network_economics/inputs.json').read_text()); assert len(inputs['markets'])==31
files=['src/network_model.py','src/dashboard_template.html','data/assumptions/network.csv','context/12_network_economics/inputs.json','src/fetch_subsidy.py','context/04_research/README.md']
for p in files: assert subprocess.check_output(['git','show',PIN+':'+p],cwd=ROOT)==(ROOT/p).read_bytes()
refs=[('27dd316f6e0654a0b4d3cb0aa3d98d1e74e37b51','context/26_team_transfer_20261110/late_owner_source_snapshot.json'),('a77e4cfbd14e560d26407479b7252cfcb15f4f41','context/23_night_run_20261110/methods/README.md')]
archives=[]
for ref,p in refs:
 r=subprocess.run(['git','show',ref+':'+p],cwd=ROOT,capture_output=True)
 archives.append({'sha':ref,'file':p,'exists':r.returncode==0,'sha256':hashlib.sha256(r.stdout).hexdigest() if r.returncode==0 else None})
result={'pin':PIN,'scope':'independent ledger arithmetic and static source trace; no new optimizer run; no tax adjustment','protected_count':389,'protected_unchanged':True,'unit':'RUB / 52-week model year, OMS base_sub12; not actual sales or confirmed 2028 award','ticket_before_migration':T,'foregone':F,'support':S,'variable_cost':V,'contribution':C,'fixed_network_without_support':C0,'fullPnL':None,'cash':None,'fixed_network_support_identity':True,'rounding_errors':rounding,'fare_source_unit':inputs['fare_unit'],'fare_market_count':len(inputs['markets']),'source_hashes':{p:sha(ROOT/p) for p in files},'reviewed_artifact_hashes':{str(p.relative_to(ROOT)):sha(p) for p in [AUD/'replay/ledger.csv',AUD/'replay/counterfactuals.csv',AUD/'methods/methodology.md',AUD/'replay/README.md',AUD/'sources/sources.md']},'archive_checks':archives}
(OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'pass':True,'C':C,'C0':C0,'protected':389,'rounding_errors':len(rounding)}))
