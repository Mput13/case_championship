"""Offline review validation; writes only source_review/validation.json. No model rerun."""
import csv,hashlib,json,subprocess,sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
O=Path(__file__).resolve().parent;B=O.parent; repo=B.parent.parent
checks={}
def rows(name):
 with (O/name).open(encoding='utf-8-sig',newline='') as f:
  raw=list(csv.reader(f));assert all(len(x)==len(raw[0]) for x in raw),name
 with (O/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
a=rows('source_admission.csv'); f=rows('findings.csv')
checks['admission_unique_ids']=len({r['row_id'] for r in a})==len(a)
checks['verdict_enum']=all(r['verdict'] in {'observed','published_offer','scenario','unknown','error'} for r in a)
checks['required_fields_complete']=all(all(r.values()) for r in a)
checks['finding_admissions_exist']=all(set(r['admission_rows'].split(';')) <= {x['row_id'] for x in a} for r in f)
for p in O.glob('*.csv'): rows(p.name)
checks['csv_rectangular']=True
integrity=json.loads((O/'input_integrity.json').read_text())
checks['completed_inputs_unchanged']=all(hashlib.sha256((B/p).read_bytes()).hexdigest()==h for p,h in integrity.items())
c=json.loads((B/'audit/common_contract.json').read_text())
checks['resource_same_envelope']=all(x in c['resource']['same_envelope_for'] for x in ['KEEP','all direct types'])
checks['no_early_SJ']=all(x['delivery']>='2027-07-01' and x['entry']>='2027-07-01' for v in c['resource']['deliveries'].values() for x in v)
x=datetime(2026,12,7,18,20,tzinfo=ZoneInfo('Europe/Samara'));y=datetime(2026,12,7,18,40,tzinfo=ZoneInfo('Europe/Moscow'))
checks['KUF_GOJ_80min']=(y.timestamp()-x.timestamp())/60==80
checks['March2027_after_Dec2026']='2027-03-26'>'2026-12-13'
r=rows('canonical_supplemental_directed_services.csv')
checks['no_ZIA_for_SVX']=all('S07' not in x['source_ids'].split(';') for x in r if x['pair']=='SVX-TBS')
checks['reverse_not_forward']=all(x['completed_fact']=='UNKNOWN' for x in r if x['direction']=='TBS-SVX')
raw=repo/'context/30_defense_research_20261111/inputs/model_schedule/latest/data/raw/tochno_intercity/data_intercity_connectivity_162_v20260629.csv'
h=hashlib.sha256(raw.read_bytes()).hexdigest()
checks['raw_snapshot_matches']=h=='aed8463339b988a7c9ac81aa976a4fc25c152e4066b551d25cbdcc16ebe16d53'
venv=repo/'context/28_end_to_end_audit_20261110/code/sandbox/venv/bin/python'
v=subprocess.run([str(venv),'-c','import numpy,pandas;print(numpy.__version__,pandas.__version__)'],cwd=repo,capture_output=True,text=True)
checks['existing_venv_imports']=v.returncode==0
# Exact-ref comparison of only the reviewed P05 documentation, not live model inputs.
pinchecks=[]
for m in json.loads((B/'audit/source_manifest.json').read_text()):
 if m['commit']=='a63a047bc6559df8bac3b2dde5c6464c3c9e6a0b' and m['path'].endswith(('/P05/README.md','/P05/handoff.json')):
  local=Path(m['local_path']).read_bytes()
  git=subprocess.run(['git','show',m['commit']+':'+m['path']],cwd=repo,capture_output=True)
  pinchecks.append(git.returncode==0 and git.stdout==local and hashlib.sha256(local).hexdigest()==m['sha256'])
checks['P05_reviewed_docs_exact_pin']=len(pinchecks)==2 and all(pinchecks)
result=dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,admission_rows=len(a),findings=len(f),sources_attempted=9,substantive_pages_or_documents_read=8,new_observed_OD_updates=0,new_realized_net_yield_updates=0,new_contract_price_updates=0,model_numeric_updates=0,raw_sha256=h,environment_versions=v.stdout.strip(),technical_A05='raw and dependencies available; full pipeline NOT rerun; old snapshot NOT Git-primary',scope='One bounded source round; metadata corrections only; model code/formulas not audited',reproduction='python3 source_review/verify.py')
(O/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(not all(checks.values()))
