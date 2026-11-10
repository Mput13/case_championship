import subprocess, hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINS = {'new':'dc1eb38d4c6b7c18386b3db4b1750166bb010ffd','old':'066d3e288b41859b9ac33a3e571456a22d877795','previous_review':'3f54697'}
rows=[]
for name,sha in PINS.items():
    paths=subprocess.check_output(['git','ls-tree','-r','--name-only',sha],text=True).splitlines()
    for p in paths:
        keep = (name=='new' and (p.startswith('data/assumptions/') or p.startswith('data/manual/') or p.startswith('src/') and p.endswith('.py') or p in ['data/processed/catchments.csv','data/processed/od_fit.json','data/processed/od_pairs.csv','data/processed/demand_estimates.csv','data/processed/network_routes.csv','data/processed/network_summary.csv','data/processed/fleet_ramp.csv','data/raw/favt_subsidy_2026.csv','data/raw/tochno_intercity/data_intercity_connectivity_162_v20260629.csv','docs/24_hypotheses_comparison.md','docs/26_steps_2_4_5.md','docs/HANDOFF.md','AGENTS.md'])) or (name=='old' and p in ['src/network_model.py','data/assumptions/network.csv','data/processed/network_routes.csv','data/processed/network_summary.csv']) or (name=='previous_review' and p.startswith('context/28_evening_run_20261110/late_nastya_impact/') and p.split('/')[-1] in ['report.md','handoff.md','source_manifest.json','subsidy_counterexamples.csv'])
        if not keep: continue
        data=subprocess.check_output(['git','show',f'{sha}:{p}'])
        dest=HERE/'inputs'/name/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        rows.append({'pin':name,'commit':subprocess.check_output(['git','rev-parse',sha],text=True).strip(),'path':p,'git_blob':subprocess.check_output(['git','rev-parse',f'{sha}:{p}'],text=True).strip(),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
(HERE/'source_manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
(HERE/'author_diff.patch').write_bytes(subprocess.check_output(['git','diff',PINS['old'],PINS['new'],'--','src/network_model.py','data/assumptions/network.csv','docs/24_hypotheses_comparison.md','docs/26_steps_2_4_5.md','docs/HANDOFF.md']))
print(json.dumps({'files':len(rows),'bytes':sum(r['bytes'] for r in rows)}))

# Raw connectivity is untracked in the owner's commit; use the same frozen
# methods5512 gzip receipt as the previous exact review, explicitly qualified.
import gzip
sha='5512f7d474a5db4bb658aae30b10f8b886629861'
p='context/28_evening_run_20261110/methods/inputs/audit_5905/replay/inputs/tochno_intercity.csv.gz'
data=subprocess.check_output(['git','show',f'{sha}:{p}'])
dest=HERE/'inputs/frozen/tochno_intercity.csv.gz';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
rows.append({'pin':'frozen_methods_raw','commit':sha,'path':p,'git_blob':subprocess.check_output(['git','rev-parse',f'{sha}:{p}'],text=True).strip(),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'qualification':'Not tracked in dc1eb38; frozen alternative input identical to previous exact review.'})
raw=gzip.decompress(data)
dest=HERE/'runtime/data_intercity_connectivity_162_v20260629.csv';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
rows.append({'pin':'gzip_derivative','path':str(dest.relative_to(HERE)),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'qualification':'Temporary runtime; recreated by capture_inputs.py; removed after checks.'})
for p in ['context/12_network_economics/inputs.json','context/12_network_economics/sources.json']:
    data=subprocess.check_output(['git','show',f"{PINS['new']}:{p}"])
    dest=HERE/'inputs/new'/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    rows.append({'pin':'new','commit':PINS['new'],'path':p,'git_blob':subprocess.check_output(['git','rev-parse',f"{PINS['new']}:{p}"],text=True).strip(),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
(HERE/'source_manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
