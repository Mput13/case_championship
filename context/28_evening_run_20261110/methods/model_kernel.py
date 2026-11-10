"""Pinned author arithmetic; separate extraction and bounded selection policies."""
import ast,copy,functools,gzip,hashlib,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OWNER=ROOT/'inputs/nastya_4a976'
sys.path.insert(0,str(OWNER/'src'))
import demand_model as dm
import network_model as nm

def load():
 raw=gzip.decompress((ROOT/'inputs/audit_5905/replay/inputs/tochno_intercity.csv.gz').read_bytes())
 assert hashlib.sha256(raw).hexdigest()=='aed8463339b988a7c9ac81aa976a4fc25c152e4066b551d25cbdcc16ebe16d53'
 target=ROOT/'.runtime/tochno.csv';target.parent.mkdir(exist_ok=True);target.write_bytes(raw);dm.TOCHNO=target
 d=nm.Demand()
 for name in ('get','seg','km','south','green','has_direct'):
  setattr(d,name,functools.lru_cache(None)(getattr(d,name)))
 return d,nm.load_assumptions()

class ScaledDemand:
 """Uniform lost-calendar exposure: annual OD and segments both lose 4/52, no recapture."""
 def __init__(self,d,factor):self.d,self.factor=d,factor
 def __getattr__(self,k):return getattr(self.d,k)
 def get(self,a,b,s):return self.factor*self.d.get(a,b,s)
 def seg(self,a,b,s):return self.factor*self.d.seg(a,b,s)

def extract(name,stop_target,return_expr):
 tree=ast.parse((OWNER/'src/network_model.py').read_text())
 f=copy.deepcopy(next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==name))
 def names(n):return {x.id for x in ast.walk(n) if isinstance(x,ast.Name)}
 idx=next(i for i,x in enumerate(f.body) if isinstance(x,ast.Assign) and stop_target in names(x.targets[0]))
 f.body=f.body[:idx]+[ast.Return(value=ast.parse(return_expr,mode='eval').body)]
 f.name=name+'_context';mod=ast.fix_missing_locations(ast.Module(body=[f],type_ignores=[]))
 ns=dict(nm.__dict__);exec(compile(mod,str(OWNER/'src/network_model.py')+' [extracted context]','exec'),ns)
 return ns[f.name]

hub_context=extract('hub_network','chosen','(spokes, build)')
direct_context=extract('direct_network','pre','(tri, tri_eval, joint, totals)')

def hub_greedy(spokes,build,A,cap):
 chosen=[];best=None;max_h=(cap-A['spare_aircraft'])*A['block_h_per_day']*7
 while len(chosen)<A['max_routes']:
  cand=None
  for x in spokes:
   if x in chosen:continue
   r=build(tuple(chosen+[x]))
   if r[2]>max_h+1e-9:continue
   gain=r[4]-r[3]-(best[4]-best[3] if best else 0)
   dh=r[2]-(best[2] if best else 0);score=gain/dh if dh>0 else -1e18
   if cand is None or score>cand[0]:cand=score,x,r
  if cand is None or (cand[0]<=0 and len(chosen)>=A['min_routes']):break
  chosen.append(cand[1]);best=cand[2]
 return chosen,best

def direct_candidates(d,A,scen):
 tri,tri_eval,joint,totals=direct_context(d,A,scen,list(d.n.index))
 sels=[];gross=[];net=[]
 for b,x,y,legs in tri:
  h,c,r,s,out=tri_eval(b,x,y,legs);f=out[0]['freq']
  sel=(b,x,y,f,legs);sels.append(sel);gross.append((r-c)/h)
  single=joint([sel])[0];net.append((single[6]-single[5])/single[4])
 @functools.lru_cache(None)
 def evaluate(ids):return joint([sels[i] for i in ids])
 def pairs(ids):return {tuple(sorted((l['a'],l['b']))) for i in ids for l in sels[i][4]}
 return sels,gross,net,evaluate,pairs

def direct_greedy(sels,pre,evaluate,pairs,A,cap,city_gate=False):
 ids=[];used=set();cur=(0.,0.);max_h=(cap-A['spare_aircraft'])*A['block_h_per_day']*7
 while len(ids)<A['max_routes']:
  best=None
  for i in pre:
   b,x,y,f,legs=sels[i]
   if (x,y) in used:continue
   cand_ids=tuple(ids+[i])
   if city_gate and len(pairs(cand_ids))>12:continue
   res=evaluate(cand_ids);m=sum(r[6]-r[5] for r in res);h=sum(r[4] for r in res)
   if h>max_h+1e-9:continue
   gain,dh=m-cur[0],h-cur[1];score=gain/dh if dh>0 else -1e18
   if best is None or score>best[0]:best=score,i,(m,h)
  count=len(pairs(tuple(ids))) if city_gate else len(ids)
  if best is None or (best[0]<=0 and count>=A['min_routes']):break
  ids.append(best[1]);used.add((sels[best[1]][1],sels[best[1]][2]));cur=best[2]
 return ids,evaluate(tuple(ids))

def metrics(kind,key,A,r):
 W=A['weeks_per_year']
 if kind=='HUB':
  legs,trans,h,c,rev,loc,tr,flights,mg,fore,subs=r
  leglist=list(legs.values());seg=loc+2*tr;od=loc+tr
 else:
  h,c,rev,seg,mg,fore,subs=[sum(x[i] for x in r) for i in (4,5,6,7,9,10,11)]
  leglist=[l for x in r for l in x[8]];flights=sum(2*l['freq'] for l in leglist);od=seg;tr=0
 pairs=sorted({tuple(sorted((l['a'],l['b']))) for l in leglist})
 actual=math.ceil((h-1e-9)/(A['block_h_per_day']*7))+int(A['spare_aircraft']) if h else 0
 return dict(network=key,kind=kind,model_city_pairs=len(pairs),physical_airport_assignment='MOW_UNRESOLVED' if any('MOW' in q for q in pairs) else 'MODEL_IATA_ONLY_NO_DATED_DISPATCH',aircraft_hour_lower_bound_including_reserve=actual,working_hour_lower_bound=max(0,actual-int(A['spare_aircraft'])),block_hours_week=h,flights_week=flights,journeys_year=od*W,transfer_journeys_year=tr*W,segments_year=seg*W,migrated_segments_year=mg*W,net_added_segments_listed_keep_only=(seg-mg)*W,ticket_before_migration_rub_year=(rev-subs+fore)*W,foregone_ticket_rub_year=fore*W,ticket_after_migration_rub_year=(rev-subs)*W,support_rub_year=subs*W,variable_cost_rub_year=c*W,contribution_rub_year=(rev-c)*W,model_weeks=W,pairs=';'.join('-'.join(q) for q in pairs),model_8_12_pair_gate=8<=len(pairs)<=12,actual_fleet_acceptance=False,full_pnl_rub=None,cash_rub=None)
