"""Read-only checks of this package, exact Git source blobs and extracted source rows."""
import pathlib,json,csv,hashlib,subprocess,io
R=pathlib.Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
required=['case.json','evidence.csv','market_deltas.csv','hypotheses.json','programme_candidates.json','comparison_requests.csv','assumptions.csv','readiness.json','handoff.json','output_manifest.json']
for n in required:assert (R/n).is_file(),n
manifest=json.loads((R/'output_manifest.json').read_text())
for f in manifest['files']:
 p=R/f['path'];assert p.is_file(),f['path'];assert sha(p.read_bytes())==f['sha256'],f['path']
pins=json.loads((R/'source_pins.json').read_text());row_count=0
for p in pins['inputs']:
 assert 'error' not in p,p
 ref=p['commit']+':'+p['path'];raw=subprocess.check_output(['git','show',ref])
 assert sha(raw)==p['sha256'],ref
 assert subprocess.check_output(['git','rev-parse',ref]).decode().strip()==p['blob'],ref
 if 'extract_path' not in p:continue
 extract=R/p['extract_path'];assert sha(extract.read_bytes())==p['extract_sha256'],str(extract)
 originals=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
 for row in csv.DictReader(extract.open()):
  source=originals[int(row['_source_line'])-2]
  actual={k:v for k,v in row.items() if not k.startswith('_source_')}
  assert actual==source,(extract,row['_source_line'])
  assert sha(canon(source))==row['_source_row_sha256'],(extract,row['_source_line'])
  row_count+=1
for n in ['evidence.csv','market_deltas.csv','comparison_requests.csv','assumptions.csv','local_fare_panel.csv','monthly_template_calendar.csv']:
 rows=list(csv.DictReader((R/n).open()));assert rows,n
 for col in ['units','period','coverage','status','source_id']:assert col in rows[0],(n,col)
 assert all(r['source_id'] for r in rows),(n,'source_id')
h=json.loads((R/'hypotheses.json').read_text())['hypotheses'];ids=[x['hypothesis_id'] for x in h];assert len(ids)==len(set(ids))==9
for x in h:
 for k in ['signal','source','mechanism','counterfactual','distinguishingtest','ancestorIDs','outcome','condition_for_reconsideration']:assert x[k],(x['hypothesis_id'],k)
p=json.loads((R/'programme_candidates.json').read_text())['programmes'];assert len(p)==8
for x in p:assert all(i in ids for i in x['hypothesis_ids']),x['programme_id']
a={r['assumption_id'] for r in csv.DictReader((R/'assumptions.csv').open())}
for x in p:assert all(i in a for i in x['assumption_ids']),(x['programme_id'],'assumptions')
check=json.loads((R/'checks.json').read_text());assert check['status']=='PASS' and all(x['result']=='PASS' for x in check['checks'])
assert json.loads((R/'readiness.json').read_text())['stage_B'].startswith('OPEN')
assert not manifest['accepted_for_economics']
print(json.dumps({'result':'PASS','manifest_files':len(manifest['files']),'pinned_blobs_verified':len(pins['inputs']),'source_rows_verified':row_count,'required_outputs':len(required),'checks':len(check['checks']),'manifest_sha256':sha((R/'output_manifest.json').read_bytes()),'scope':'self-check only; no final economics/market/operational acceptance'},ensure_ascii=False))
