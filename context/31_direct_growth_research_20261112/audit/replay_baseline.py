"""Limited exact-function replay; stdlib table adapter, no full demand refit/search claim."""
import ast,csv,json,math,pathlib,types
ROOT=pathlib.Path(__file__).resolve().parent
B=ROOT/'inputs/audit_model/dceadc98'
def rows(p):return list(csv.DictReader((B/p).open()))
source=B/'src/network_model.py'
names={'rw_pax_week','leg_cost','fare','capture','leg_share','freq_for','leg_with_subsidy','sub','hub_network','direct_network'}
tree=ast.parse(source.read_text()); tree.body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
closed={r['iata'] for r in rows('data/manual/closed_airports.csv')}
freq={frozenset((r['a'],r['b'])):float(r['freq_week_each_way']) for r in rows('data/manual/rw_routes_now.csv')}
bases=list(dict.fromkeys(r['node'] for r in rows('data/assumptions/bases.csv')))
ns=dict(math=math,CLOSED=closed,RW_FREQ=freq,rules=types.SimpleNamespace(BASES=bases))
exec(compile(tree,str(source),'exec'),ns)
node={r['iata']:r for r in rows('data/processed/catchments.csv')};node['MOW']=node['SVO']
pairs=rows('data/processed/demand_pairs.csv'); direct={frozenset((r['a'],r['b'])) for r in pairs if r['direct_now']=='True'}
od={frozenset((r['a'],r['b'])):r for r in rows('data/processed/od_pairs.csv')}
est={frozenset((r['a'],r['b'])):r for r in rows('data/processed/demand_estimates.csv') if r['od_base']}
south={r['region'] for r in rows('data/assumptions/south_west_regions.csv')};ranges={r['parameter']:float(r['value']) for r in rows('data/assumptions/range.csv')}
class D:
 def km(self,a,b):
  x,y=node[a],node[b];la,lo,lb,lp=map(math.radians,[float(x['latitude_deg']),float(x['longitude_deg']),float(y['latitude_deg']),float(y['longitude_deg'])]);return 12742*math.asin(math.sqrt(math.sin((lb-la)/2)**2+math.cos(la)*math.cos(lb)*math.sin((lp-lo)/2)**2))
 def south(self,a,b):return node[a]['region'] in south or node[b]['region'] in south
 def green(self,a,b):return ranges['ssj_green_south_km' if self.south(a,b) else 'ssj_green_km']
 def get(self,a,b,s):
  k=frozenset((a,b));r=est.get(k) or od[k];return float(r['od_'+s])
 def seg(self,a,b,s):
  k=frozenset((a,b));e=est.get(k);o=od.get(k,{})
  if e and e['direct_now']=='True' and e['segments_base']:return float(e['segments_base'])*(1 if s=='base' else self.get(a,b,s)/max(self.get(a,b,'base'),1))
  if o.get('segments_on_link'):return float(o['segments_on_link'])*(1 if s=='base' else self.get(a,b,s)/max(self.get(a,b,'base'),1))
  return self.get(a,b,s)
 def has_direct(self,a,b):return frozenset((a,b)) in direct
D=D();out={'scope':'exact function AST + explicit CSV adapter; subset replay, not original full pipeline; direct connectivity reconstructed from processed demand_pairs, missing raw connectivity excluded','nodes':['MOW','SVX','OMS','KUF','GOJ','MRV','UFA','KZN'],'runs':[]}
for s in ['base','cautious']:
 A={r['parameter']:float(r[s]) for r in rows('data/assumptions/network.csv')};A['use_subsidy']=0
 H,r=ns['hub_network']('OMS',D,A,s,out['nodes'],fixed_spokes=['MOW','SVX','KUF','GOJ'])
 assert all(l['lf']<=A['lf_max']+1e-9 for l in r[0].values())
 out['runs'].append(dict(scenario=s,family='hub_fixed4',hours_week=r[2],variable_contribution_RUB_modelyear=(r[4]-r[3])*A['weeks_per_year'],segments_week=sum(2*l['carried_dir_week'] for l in r[0].values()),journeys_week=r[5]+r[6]))
 t=ns['direct_network'](D,A,s,out['nodes']);assert all(l['lf']<=A['lf_max']+1e-9 for x in t for l in x[8])
 out['runs'].append(dict(scenario=s,family='direct_subset_triangles',triangles=len(t),hours_week=sum(x[4] for x in t),variable_contribution_RUB_modelyear=sum(x[6]-x[5] for x in t)*A['weeks_per_year']))
(ROOT/'replay/baseline_subset.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False,indent=2))
