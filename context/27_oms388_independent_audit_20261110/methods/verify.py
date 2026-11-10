from pathlib import Path
import csv,json,hashlib,subprocess
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
PIN='d4a6eabb42671e5b16d44abedcdc6ceafb692528'
def git(*args):
 return subprocess.check_output(['git','-C',str(ROOT),*args])
protected=json.loads((OUT.parent/'protected_owner_files.json').read_text())
bad=[p for p,h in protected.items() if not (ROOT/p).is_file() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
pin_is_ancestor=subprocess.run(['git','-C',str(ROOT),'merge-base','--is-ancestor',PIN,'HEAD'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
files=['src/network_model.py','src/demand_model.py','src/od_model.py','src/demand_compare.py','src/rules.py','data/assumptions/network.csv','data/assumptions/range.csv','data/processed/network_summary.csv','data/processed/od_fit.json','data/manual/rw_routes_now.csv','context/12_network_economics/inputs.json']
evidence=[]
for p in files:
 b=git('show',f'{PIN}:{p}')
 evidence.append({'path':p,'source_sha':PIN,'git_blob':git('rev-parse',f'{PIN}:{p}').decode().strip(),'sha256':hashlib.sha256(b).hexdigest(),'working_matches_pin':(ROOT/p).read_bytes()==b})
counts={}
for name in ['findings.csv','model_map.csv','ai_provenance.csv']:
 with (OUT/name).open(encoding='utf-8',newline='') as h:
  rows=list(csv.DictReader(h))
 assert rows and all(None not in r and all(v is not None for v in r.values()) for r in rows)
 assert len({r['id'] for r in rows})==len(rows)
 counts[name]=len(rows)
words=len((OUT/'methodology.md').read_text().split())
prior='4a9763565f70b9ab1eddde2f5daca07687560948'
same={p:git('show',f'{prior}:{p}')==git('show',f'{PIN}:{p}') for p in files[:7]}
readme='context/23_night_run_20261110/methods/README.md'
exists=subprocess.run(['git','-C',str(ROOT),'cat-file','-e',f'a77e4cfbd14e560d26407479b7252cfcb15f4f41:{readme}'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
r={'reviewed_pin':PIN,'source_pin_is_ancestor':pin_is_ancestor,'protected_count':len(protected),'protected_mismatches':bad,'evidence':evidence,'same_as_late_owner':same,'previous_methods_readme_exists':exists,'replacement_reads':['handoff_compact.md','strategy_accounting_readout.md'],'rows':counts,'methodology_word_count':words,'model_execution':False,'external_research':False,'validation_scope':'static evidence, schemas and protected hashes; no financial replay'}
r['pass']=pin_is_ancestor and len(protected)==389 and not bad and all(x['working_matches_pin'] for x in evidence) and words<=900
(OUT/'verification.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:r[k] for k in ['pass','protected_count','protected_mismatches','rows','methodology_word_count','previous_methods_readme_exists']},ensure_ascii=False))
assert r['pass']
