"""Read-only admission/conservation checks for the exact emitted selection experiment."""
import csv,hashlib,json,math
from pathlib import Path
from model_kernel import ROOT,nm
p=ROOT/'runs/selection_v1'
manifest=json.loads((ROOT/'source_manifest.json').read_text())
for x in manifest['files']:
 b=(ROOT/x['path']).read_bytes();assert len(b)==x['bytes'] and hashlib.sha256(b).hexdigest()==x['sha256'],x['path']
net=json.loads((p/'networks.json').read_text());checks=0
for key,n in net.items():
 m,A,r=n['metrics'],n['assumptions'],n['result'];W=A['weeks_per_year']
 if m['kind']=='HUB':
  legs,tr,h,c,rev,loc,trans,flights,mg,fore,sub=r
  alllegs=list(legs.values())
  assert abs(sum(2*x[3] for x in tr)-trans)<1e-8
  assert abs(sum(2*x['local_carried'] for x in alllegs)-loc)<1e-8
  gross=sum(2*x['local_carried']*nm.fare(A,x['km']) for x in alllegs)+sum(2*t*nm.fare(A,km)*A['transfer_fare_factor'] for a,b,km,t in tr)
  assert abs((gross-fore+sub)-rev)<1e-6
  for x in alllegs:
   t=sum(t for a,b,km,t in tr if x['b'] in (a,b))
   assert abs(x['carried_dir_week']-x['local_carried']-t)<1e-7
   checks+=1
 else:
  alllegs=[l for x in r for l in x[8]];groups={}
  for l in alllegs:groups.setdefault(tuple(sorted((l['a'],l['b']))),[]).append(l)
  for pair,g in groups.items():
   f=sum(x['freq'] for x in g);wanted=g[0]['dem']*nm.leg_share(g[0],f,A)
   actual=sum(x['carried_dir_week'] for x in g)
   assert abs(actual-min(wanted,f*A['seats']*A['lf_max']))<1e-7
   assert actual<=g[0]['dem']+1e-7
   assert abs(sum(x['migrated'] for x in g)-min(actual,g[0]['rw_now']))<1e-7
   checks+=3
 for l in alllegs:
  assert l['carried_dir_week']<=l['freq']*A['seats']*A['lf_max']+1e-7
  assert l['migrated']<=l['carried_dir_week']+1e-7
  checks+=2
 assert abs(sum(2*l['freq']*l['block_h'] for l in alllegs)-m['block_hours_week'])<1e-7
 assert abs(sum(2*l['carried_dir_week'] for l in alllegs)*W-m['segments_year'])<1e-6
 checks+=2
oms=net['AUTHOR_52_48_CONCENTRATED/base/OMS/GREEDY/cap10']['metrics']['contribution_rub_year']
small=net['AUTHOR_52_48_CONCENTRATED/base/OMS/GREEDY/cap4']['metrics']['contribution_rub_year']
sub=net['AUTHOR_52_48_CONCENTRATED/base_sub/OMS/GREEDY/cap10']['metrics']['contribution_rub_year']
assert abs(oms+367061628.90116817)<0.01
assert abs(small+186479510.4910583)<0.01
assert abs(sub-387722372.7102387)<0.01
assert small>oms
# A deliberate omitted incumbent would reproduce the cap regression; check catches it.
regression_detected=not (oms>=small-1e-6)
assert regression_detected
result={'status':'PASS_OWNER_SCOPED','source_files':len(manifest['files']),'networks':len(net),'conservation_capacity_market_checks':checks,'exact_audit_money_fixtures':3,'known_nonmonotonic_owner_counterexample_detected':regression_detected,'independent_review':'PENDING','source_market_dispatch_acceptance':False}
(ROOT/'runs/selection_v1/semantic_checks.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
