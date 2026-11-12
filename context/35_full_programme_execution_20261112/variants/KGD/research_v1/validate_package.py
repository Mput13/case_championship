#!/usr/bin/env python3
"""Проверка provenance и границ Stage A; не приёмка рынка/экономики."""
import csv
import hashlib
import io
import json
import pathlib
import subprocess

root=pathlib.Path(__file__).resolve().parent
pins=json.loads((root/'source_pins.json').read_text())
checks=[]
def check(name,ok,detail):
    checks.append({'check':name,'status':'PASS' if ok else 'FAIL','detail':detail})
for entry in pins['files']:
    data=subprocess.check_output(['git','show',entry['commit']+':'+entry['path']])
    check('pinned_source:'+entry['source_id'],hashlib.sha256(data).hexdigest()==entry['sha256'],entry['commit']+':'+entry['path'])
    local=entry.get('local_path','')
    if local.endswith('.csv'):
        original=list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))
        selected=list(csv.DictReader((root/local).open()))
        good=True
        for row in selected:
            idx=int(row['source_csv_line'])-2
            source_row=original[idx]
            canonical=json.dumps(source_row,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
            good &= hashlib.sha256(canonical).hexdigest()==row['source_row_sha256']
            good &= all(row[k]==v for k,v in source_row.items())
        check('selected_rows:'+local,good and len(selected)==entry['selected_rows'],{'rows':len(selected),'expected':entry['selected_rows']})
for p in root.rglob('*.json'):
    if p.name not in ('validation.json','output_manifest.json'):
        json.loads(p.read_text())
check('json_parse',True,'Все JSON прочитаны')
for name in ('evidence.csv','market_deltas.csv','comparison_requests.csv','assumptions.csv','offer_observations.csv','monthly_design_calendar.csv','source_conflicts.csv'):
    rows=list(csv.DictReader((root/name).open()))
    check('table_metadata:'+name,bool(rows) and all(all(r.get(k) for k in ('units','period','coverage','status','source_id')) for r in rows),{'rows':len(rows)})
programmes=json.loads((root/'programme_candidates.json').read_text())['programmes']
check('no_money_winner',all(p['money_result'] is None for p in programmes),'Денежная оценка не исполнялась')
check('zero_new_tu214',all(p['new_tu214']==0 for p in programmes),'Ветка нулевых новых Ту-214 сохранена')
cal=list(csv.DictReader((root/'monthly_design_calendar.csv').open()))
check('24_unique_months',len(cal)==24 and len({r['month'] for r in cal})==24,'2027-01…2028-12; условный дизайн')
check('new_SJ_timing_gate',all('НЕ РАНЬШЕ' in r['new_sj100_branch'] for r in cal if r['month']<'2027-07'),'Новые SJ не обещаны в первом полугодии 2027')
readiness=json.loads((root/'readiness.json').read_text())
check('stage_b_open',readiness['joint_final_acceptance']=='NOT_READY' and readiness['stage_b']=='OPEN_REQUIRED','Stage A не финальная экономика')
manifest=json.loads((root/'output_manifest.json').read_text())
for r in manifest['files']:
    p=root/r['path']
    if p.name=='validation.json':continue
    check('output_hash:'+r['path'],p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],r['bytes'])
failed=[c for c in checks if c['status']=='FAIL']
validation={'status':'PASS' if not failed else 'FAIL','scope':'Личная проверка автором пакета: source pins, selected-row integrity, manifest, границы Stage A. Не независимая приёмка P03/P05/P06.','checks':checks,'failed':failed,'external_acceptance':'NOT_RUN'}
(root/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
files=[]
for p in sorted(root.rglob('*')):
    if p.is_file() and p.name!='output_manifest.json' and '__pycache__' not in p.parts:
        files.append({'path':str(p.relative_to(root)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
manifest['files']=files;manifest['total_bytes']=sum(x['bytes'] for x in files)
(root/'output_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':validation['status'],'checks':len(checks),'failed':failed,'files':len(files),'bytes':manifest['total_bytes']},ensure_ascii=False))
raise SystemExit(1 if failed else 0)
