#!/usr/bin/env python3
"""Source binding and delivery checks; no economic/rehearsal acceptance."""
import hashlib,json,re,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent
m=json.loads((P/'input_manifest.json').read_text()); checks=[]
def check(name,ok,detail=None):
 checks.append({'name':name,'pass':bool(ok),'detail':detail});assert ok,name
for r in m['files']:
 b=subprocess.check_output(['git','show',r['commit']+':'+r['path']]);check('exact blob '+r['package']+'/'+Path(r['path']).name,hashlib.sha256(b).hexdigest()==r['sha256'])
 if r['local_path']:check('local snapshot '+r['local_path'],(P/r['local_path']).read_bytes()==b)
manifest_checks=[]
for pkg,name in [('P00R','artifact_manifest.json'),('P02','output_manifest.json'),('P03','sp_adapter/output_manifest.json'),('P04','output_manifest.json'),('P04','schema_adapter_manifest.json'),('P06','output_manifest.json')]:
 d=json.loads((P/'inputs'/pkg/'context/35_full_programme_execution_20261112'/pkg/name).read_text());reg={r.get('path',r.get('file')):r['sha256'] for r in d['files']}
 for r in m['files']:
  if r['package']!=pkg:continue
  rel=r['path'].split('/'+pkg+'/',1)[1]
  if rel in reg:
   ok=r['sha256']==reg[rel];check('upstream manifest '+pkg+'/'+rel,ok);manifest_checks.append({'package':pkg,'file':rel,'pass':ok})
d=json.loads((P/'ui_candidate/data/source_data.json').read_text());check('20 seed cities available',len(d['cities'])>=20);check('actual products count',len(d['products'])==2274)
check('no financial demo or historical model exported',d['evaluations']==[] and 'net' not in d and 'steps' not in d)
html=(P/'ui_candidate/dashboard.html').read_text();check('self contained executable assets',not re.search(r'<script[^>]+src=|<link[^>]+(?:stylesheet|fonts)',html))
check('transparent outer root','body{margin:0;background:transparent}' in html)
check('no viewport height units',not re.search(r'\d(?:d|s|l)?vh\b',html))
for s in ['adapter.js','app.js']:
 r=subprocess.run(['node','--check',str(P/'ui_candidate/source'/s)],capture_output=True,text=True);check('JS syntax '+s,r.returncode==0,r.stderr or None)
used={a['assumption_id'] for a in json.loads((P/'assumptions_register.json').read_text())}
for r in d['products']:
 used.update(x.strip() for x in r['assumption_ids'].split(';') if x.strip())
used.update(r['assumption_id'] for r in d['costs'])
reg={a['assumption_id']:a for a in d['assumptions']};check('all used assumption IDs resolved',used<=reg.keys(),sorted(used-reg.keys()))
(P/'used_assumption_ids.json').write_text(json.dumps(sorted(used),ensure_ascii=False,indent=2)+'\n')
(P/'used_assumptions_register.json').write_text(json.dumps([reg[k] for k in sorted(used)],ensure_ascii=False,indent=2)+'\n')
links=[dict(r,git_url='https://github.com/Mput13/case_championship/blob/'+r['commit']+'/'+r['path']) for r in m['files']]
(P/'source_version_links.json').write_text(json.dumps({'files':links,'new_external_collection':False},ensure_ascii=False,indent=2)+'\n')
result={'status':'PASS','checks':checks,'upstream_manifest_checks':manifest_checks,'used_assumption_count':len(used),'scope':'Source hashes, local snapshots, manifest-covered used files, shape, syntax and packaging only','not_claimed':['market validity','physical inventory','operational feasibility','economics','number2','independent approval','final presentation rehearsal']}
(P/'qa/verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'PASS','checks':len(checks),'upstream_manifest_matches':len(manifest_checks),'used_assumption_count':len(used)}))
