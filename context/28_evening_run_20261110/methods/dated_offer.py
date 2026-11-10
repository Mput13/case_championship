"""Fixed offer replay on a dated annual denominator; constructive rotations remain conditional."""
import ast,copy,functools,math
from model_kernel import OWNER,nm

def fixed_hub_function():
 tree=ast.parse((OWNER/'src/network_model.py').read_text())
 outer=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='hub_network')
 f=copy.deepcopy(next(x for x in outer.body if isinstance(x,ast.FunctionDef) and x.name=='build'))
 f.name='fixed_hub';f.args=ast.parse('def z(S,H,D,A,scen,W,fixed_freq):pass').body[0].args
 body=[]
 for x in f.body:
  if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='f' for t in x.targets):
   body.append(ast.parse('f=dict(fixed_freq)').body[0]);continue
  if isinstance(x,ast.For) and isinstance(x.iter,ast.Call) and isinstance(x.iter.func,ast.Name) and x.iter.func.id=='range':continue
  body.append(x)
 f.body=body;ns=dict(nm.__dict__);exec(compile(ast.fix_missing_locations(ast.Module(body=[f],type_ignores=[])),'fixed_hub','exec'),ns);return ns[f.name]
fixed_hub=fixed_hub_function()

def joint_function():
 tree=ast.parse((OWNER/'src/network_model.py').read_text());outer=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='direct_network')
 f=copy.deepcopy(next(x for x in outer.body if isinstance(x,ast.FunctionDef) and x.name=='joint'))
 f.args.args.append(ast.arg(arg='A'));ns=dict(nm.__dict__);exec(compile(ast.fix_missing_locations(ast.Module(body=[f],type_ignores=[])),'fixed_joint','exec'),ns);return ns['joint']
fixed_joint=joint_function()

def revalue(n,D,year_days):
 A=dict(n['assumptions'],weeks_per_year=year_days/7);r=n['result'];m=n['metrics'];sc=A['demand_scen']
 if m['kind']=='HUB':
  f={x:int(l['freq']) for x,l in r[0].items()};rr=fixed_hub(list(f),m['network'],D,A,sc,year_days/7,f)
 else:
  sel=[]
  for t in r:
   legs=[]
   for orig in t[8]:
    l=dict(orig);a,b=l['a'],l['b'];l.update(dem=D.get(a,b,sc)/(2*A['weeks_per_year']),seg=D.seg(a,b,sc)/(2*A['weeks_per_year']))
    legs.append(l)
   sel.append((t[1],t[2],t[3],int(legs[0]['freq']),legs))
  rr=fixed_joint(sel,A)
 return A,rr

def jobs_for(n):
 jobs=[];r=n['result'];m=n['metrics']
 if m['kind']=='HUB':
  for x,l in r[0].items():jobs.append(dict(id=m['network']+'-'+x,base=m['network'],airports=[m['network'],x,m['network']],blocks=[l['block_h'],l['block_h']],freq=int(l['freq'])))
 else:
  for t in r:
   b,x,y=t[1:4];bs=[l['block_h'] for l in t[8]];f=int(t[8][0]['freq'])
   jobs.extend([dict(id='-'.join((b,x,y,b)),base=b,airports=[b,x,y,b],blocks=bs,freq=f),dict(id='-'.join((b,y,x,b)),base=b,airports=[b,y,x,b],blocks=list(reversed(bs)),freq=f)])
 return jobs

def construct_base(jobs,tail_count,turn=.75):
 """Same-base cycles, balanced weekly frequency patterns, ten block hours per day."""
 slots=[[dict(block=0.,elapsed=0.,tasks=[]) for t in range(tail_count)] for d in range(7)]
 for job in sorted(jobs,key=lambda j:(-sum(j['blocks']),-j['freq'],j['id'])):
  h=sum(job['blocks']);elapsed=h+len(job['blocks'])*turn
  if h>10+1e-9:return None
  best=None
  for phase in range(7):
   trial=copy.deepcopy(slots);okay=True
   for k in range(job['freq']):
    day=(math.floor(k*7/job['freq'])+phase)%7
    free=[t for t in range(tail_count) if trial[day][t]['block']+h<=10+1e-9 and trial[day][t]['elapsed']+elapsed<=16+1e-9]
    if not free:okay=False;break
    t=min(free,key=lambda t:(trial[day][t]['block'],trial[day][t]['elapsed'],t))
    s=trial[day][t];s['tasks'].append(job);s['block']+=h;s['elapsed']+=elapsed
   if okay:
    loads=[sum(s['block'] for s in day) for day in trial]
    score=(max(loads),sum(x*x for x in loads),phase)
    if best is None or score<best[0]:best=score,trial
  if best is None:return None
  slots=best[1]
 return slots

def milp_construct(jobs,tail_count,turn=.75):
 # Pure feasibility of balanced same-base cycles; no demand or money optimisation.
 import numpy as np
 from scipy.optimize import Bounds,LinearConstraint,milp
 from scipy.sparse import lil_matrix
 count=len(jobs)*7*tail_count
 constraints=[];lo=[];hi=[]
 def col(j,d,t):return (j*7+d)*tail_count+t
 for j,job in enumerate(jobs):
  constraints.append({col(j,d,t):1 for d in range(7) for t in range(tail_count)});lo.append(job['freq']);hi.append(job['freq'])
  for d in range(7):
   constraints.append({col(j,d,t):1 for t in range(tail_count)});lo.append(job['freq']//7);hi.append(math.ceil(job['freq']/7))
 for d in range(7):
  for t in range(tail_count):
   constraints.append({col(j,d,t):math.ceil(sum(job['blocks'])*3600-1e-8) for j,job in enumerate(jobs)});lo.append(0);hi.append(50400)
   constraints.append({col(j,d,t):math.ceil((sum(job['blocks'])+len(job['blocks'])*turn)*3600-1e-8) for j,job in enumerate(jobs)});lo.append(0);hi.append(57600)
 for t in range(tail_count):
  constraints.append({col(j,d,t):math.ceil(sum(job['blocks'])*3600-1e-8) for j,job in enumerate(jobs) for d in range(7)});lo.append(0);hi.append(252000)
 matrix=lil_matrix((len(constraints),count))
 for i,row in enumerate(constraints):
  for j,v in row.items():matrix[i,j]=v
 result=milp(np.zeros(count),integrality=np.ones(count),bounds=Bounds(np.zeros(count),np.full(count,2)),constraints=LinearConstraint(matrix.tocsr(),lo,hi),options={'time_limit':2.0})
 if result.x is None:return None
 x=np.rint(result.x).astype(int)
 if np.max(np.abs(result.x-x))>1e-5:return None
 vals=matrix.tocsr()@x
 if np.any(vals<np.array(lo)-1e-7) or np.any(vals>np.array(hi)+1e-7):return None
 slots=[[dict(block=0.,elapsed=0.,tasks=[]) for t in range(tail_count)] for d in range(7)]
 for j,job in enumerate(jobs):
  for d in range(7):
   for t in range(tail_count):
    for _ in range(x[col(j,d,t)]):
     slot=slots[d][t];slot['tasks'].append(job);slot['block']+=sum(job['blocks']);slot['elapsed']+=sum(job['blocks'])+len(job['blocks'])*turn
 return slots

@functools.lru_cache(None)
def _construct(signature):
 import json
 jobs=json.loads(signature);bybase={}
 for j in jobs:bybase.setdefault(j['base'],[]).append(j)
 out={};lower=0
 for base,js in sorted(bybase.items()):
  lb=math.ceil((sum(sum(j['blocks'])*j['freq'] for j in js)-1e-9)/70);lower+=lb
  result=None
  for t in range(max(1,lb),10):
   found=construct_base(js,t)
   if found is None:found=milp_construct(js,t)
   if found is not None:result={'working_tails':t,'slots':found};break
  if result is None:return {'status':'NO_CONSTRUCTION_FOUND_NOT_INFEASIBILITY_PROOF','base':base,'working_tails':None,'lower_bound_sum_bases':lower}
  out[base]=result
 return {'status':'CONSTRUCTED_CONDITIONAL','working_tails':sum(x['working_tails'] for x in out.values()),'lower_bound_sum_bases':lower,'bases':out,'reserve_single_author_assumption':1,'reserve_location_feasibility':'UNKNOWN_FOR_MULTI_BASE' if len(out)>1 else 'ASSUMED_AT_BASE','dispatch_acceptance':False,'construction_daily_block_limit':14,'construction_tail_weekly_block_limit':70,'construction_daily_elapsed_limit':16,'crew_airport_acceptance':False}

def construct(n):
 import json
 return _construct(json.dumps(jobs_for(n),sort_keys=True))
