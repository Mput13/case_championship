"""Verify saved evidence against exact blobs and HTTP receipts; no mutations outside D."""
import csv,io,json,pathlib,hashlib,subprocess
D=pathlib.Path(__file__).resolve().parent
H=lambda b:hashlib.sha256(b).hexdigest()
errors=[];count=0;row_count=0;http_count=0
for item in json.loads((D/'input_manifest.json').read_text()):
    commit,path=item['git_commit'],item['git_path']
    b=subprocess.check_output(['git','show',commit+':'+path]);count+=1
    blob=subprocess.check_output(['git','rev-parse',commit+':'+path],text=True).strip()
    if H(b)!=item['source_sha256'] or blob!=item['blob_id']:errors.append('blob/hash:'+path)
    loc=item.get('local_extract')
    if not loc:continue
    p=D/loc
    if not p.exists():errors.append('missing:'+loc);continue
    if path.endswith('.csv') and loc.endswith('.json'):
        source=list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))
        for row in json.loads(p.read_text()):
            index=row['source_line']-2
            if row['row']!=source[index]:errors.append('row mismatch:'+loc+':'+str(index))
            expected=H(json.dumps(source[index],ensure_ascii=False,sort_keys=True).encode())
            if row.get('row_sha256') and row['row_sha256']!=expected:errors.append('row hash:'+loc+':'+str(index))
            row_count+=1
for r in json.loads((D/'fetch_receipts.json').read_text()):
    if not r.get('sha256'):continue
    sid=r['source_id'];matched=[]
    for ext in ['html','pdf','docx']:
        p=D/'sources'/f'{sid}.{ext}'
        if p.exists() and H(p.read_bytes())==r['sha256']:matched.append(ext)
    if not matched:errors.append('receipt:'+sid)
    http_count+=1
manifest=json.loads((D/'output_manifest.json').read_text())
for x in manifest['files']:
    p=D/x['path']
    if not p.exists() or p.stat().st_size!=x['bytes'] or H(p.read_bytes())!=x['sha256']:errors.append('manifest:'+x['path'])
for p in D.glob('*.json'):
    try:json.loads(p.read_text())
    except Exception as e:errors.append('json:'+p.name+':'+str(e))
report={'status':'PASS' if not errors else 'CHANGES','scope':'Личная сверка точных входов, строк, сохранённых HTTP bytes и manifest. Не независимая экономическая или эксплуатационная приёмка.',
 'pinned_files_rechecked':count,'csv_records_rechecked':row_count,'http_receipts_rechecked':http_count,
 'manifest_files_rechecked':len(manifest['files']),'errors':errors,
 'not_run':['P05 calibration','P06 engine execution/independent acceptance','Live fare basket','Physical inventory/crew/MRO/slots admission','Financial evaluation']}
(D/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
if errors:raise SystemExit(1)
