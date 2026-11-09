#!/usr/bin/env python3
from pathlib import Path
import collections,csv,hashlib,json
P=Path(__file__).resolve().parent
m=json.loads((P/'dataset_manifest.json').read_text());r=list(csv.DictReader((P/'existing_hypotheses.csv').open()))
assert len({x['id'] for x in r})==len(r)
assert len({x['dataset_id'] for x in m['datasets']})==len(m['datasets'])
assert not m['unavailable']
by={(x['source_sha'],x['source_path']):x for x in m['datasets']}
for x in r:
 assert (x['source_sha'],x['source_path']) in by,x['id']
 for f in ['original_author','original_claim','mechanism','evidence_status','corrected_current_interpretation','unresolved_test']:
  assert x[f],(x['id'],f)
for x in m['datasets']:
 p=P/x['raw_path'];assert p.stat().st_size==x['bytes'];assert hashlib.sha256(p.read_bytes()).hexdigest()==x['sha256']
review=json.loads((P/'review_source_manifest.json').read_text())
for x in review['datasets']:
 p=P/x['raw_path'];assert p.stat().st_size==x['bytes'];assert hashlib.sha256(p.read_bytes()).hexdigest()==x['sha256']
indexed={x['id']:x for x in r}
for id in ['FRONT_CLOSURES','FRONT_NEWS']:
 assert indexed[id]['evidence_status']=='PARSER_CONTAMINATION'
 assert indexed[id]['admission_status']=='HOLD'
 assert indexed[id]['review_evidence_refs']
assert indexed['KIR_Н5']['admission_status']=='HYPOTHESIS_RETAINED_INPUT_HOLD'
assert review['review_scope']['full_history_reparse']=='NOT_RUN'
result={'status':'PASS','hypothesis_map_rows':len(r),'record_types':dict(collections.Counter(x['record_type'] for x in r)),'pinned_source_files':len(m['datasets']),'all_map_sources_snapshotted':True,'all_input_sha256_verified':True,'original_raw_unchanged':True,'review_source_files':len(review['datasets']),'review_sha256_verified':True,'parser_contamination_hold_propagated':True,'colleague_code_executed':False,'economic_reproduction':'NOT_RUN','primary_live_validation':'NOT_RUN','review_local_reproduction':'NOT_RUN','full_telegram_reparse':'NOT_RUN','limit':'Validates provenance, review snapshot and map structure, not truth of colleague claims or market forecasts.'}
(P/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
