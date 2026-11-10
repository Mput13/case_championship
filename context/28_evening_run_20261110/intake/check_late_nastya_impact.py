import csv,gzip,hashlib,io,json,math,subprocess
from pathlib import Path
SHA='3f54697bdd37c753f7d6911028e1dc0304b67c88'
P='context/28_evening_run_20261110/late_nastya_impact/'
def blob(s,p):return subprocess.check_output(['git','show',s+':'+p])
def obj(p):return json.loads(blob(SHA,P+p))
outputs=obj('output_manifest.json')['files']
for path,r in outputs.items():
 b=blob(SHA,P+path);assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
inputs=obj('source_manifest.json');assert not inputs['missing']
gitcount=0
for r in inputs['files']:
 if r.get('commit'):
  b=blob(r['commit'],r['source_path']);gitcount+=1
  assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['git_blob']
 elif r['pin']=='working_tree_instructions': b=blob(SHA,P+r['local_path'])
 elif r['pin']=='methods_gzip_derivative':
  source=next(x for x in inputs['files'] if x['local_path']==r['source_path'])
  b=gzip.decompress(blob(source['commit'],source['source_path']))
 else:raise AssertionError(r)
 assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
h=obj('handoff.json');assert h['subject_sha']=='066d3e288b41859b9ac33a3e571456a22d877795'
rows=list(csv.DictReader(io.StringIO(blob(SHA,P+'subsidy_counterexamples.csv').decode())))
r=next(r for r in rows if r['route']=='OMS-GOJ')
fare=2093+6.3*float(r['author_distance_km']);assert math.isclose(fare,float(r['author_formula_fare_rub']),abs_tol=1e-7)
grant=2*float(r['frequency_each_way_week'])*52*185228*7/12
assert math.isclose(grant,float(r['annual_smoothed_grant_author_rub']),abs_tol=1e-7)
assert fare>float(r['base_special_fare_including_vat_rub'])
gap=sum(float(x['fixed_volume_local_fare_reduction_7_months_rub']) for x in rows)
assert math.isclose(gap,obj('subsidy_formula_receipt.json')['local_only_7month_fare_gap_rub'],abs_tol=1e-6)
model=blob(h['subject_sha'],'src/network_model.py').decode()
assert 'def hub_best' in model and 'def sub_rule' in model
result=dict(review_sha=SHA,subject_sha=h['subject_sha'],status=h['status'],review_output_hashes=len(outputs),exact_git_blobs=gitcount,non_git_receipts_checked=2,real_example='OMS-GOJ formula fare/grant and five-route diagnostic scale rechecked',limits=['diagnostic gap is not corrected PnL','regional fare adjustment/retail-net/actual award unknown','main OMS cap example scoped only','no upstream frozen replacement','no operating/market/fullPnL acceptance'])
Path(__file__).with_name('late_nastya_impact_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result))
