import csv,json
from pathlib import Path
ROOT=Path(__file__).parent; PARENT=ROOT.parent
with (PARENT/'pair_seed.csv').open() as f: seed={r['pair'] for r in csv.DictReader(f) if r['group']=='REGIONAL_MOSCOW'}
def read(name):
 with (ROOT/name).open(newline='') as f: return list(csv.DictReader(f))
def check(name,required,unique=None):
 rows=read(name); assert rows, name
 assert all(set(r)==set(rows[0]) for r in rows),name
 assert set(required)==set(rows[0]),name
 if unique: assert len({tuple(r[k] for k in unique) for r in rows})==len(rows),name
 return rows
pairs=check('pair_evidence.csv',['pair','airport_a','airport_b','programmes','scenarios','group','commercial_status','rw_nonstop_status','competitor_nonstop_status','connecting_status','period_scope','evidence_refs','finding','limitations'],['pair'])
assert {r['pair'] for r in pairs}==seed
for fn in ['services.csv','fares.csv','monthly_demand.csv','alternatives.csv','decision_gaps.csv','sources.csv']: check(fn,read(fn)[0].keys())
services=read('services.csv'); assert len(services)==len(seed)*2*5
assert {r['pair'] for r in services}==seed
assert all(r['week_start']<r['week_end'] for r in services)
refs={r['source_ref'] for r in read('sources.csv')}
assert all(ref in refs for row in pairs for ref in row['evidence_refs'].split(';') if ref.startswith('S'))
assert len(seed)==16
result={'status':'PASS','regional_moscow_seed_pairs':len(seed),'pair_evidence_rows':len(pairs),'services_rows':len(services),'fares_rows':len(read('fares.csv')),'monthly_demand_rows':len(read('monthly_demand.csv')),'sources_rows':len(read('sources.csv')),'checks':['csv widths','exact seed coverage','unique pair keys','period bounds','source refs'],'limitations':'UNKNOWN values remain unresolved; no numeric demand, fare, or frequency admitted.'}
(ROOT/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
