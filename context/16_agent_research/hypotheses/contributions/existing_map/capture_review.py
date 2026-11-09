#!/usr/bin/env python3
"""Snapshot an explicit colleague review without overwriting original inputs."""
from pathlib import Path
import csv,datetime,hashlib,json
P=Path(__file__).resolve().parent
SOURCE=Path('/Users/a/.t3/worktrees/case_championship/research-case5-data-critic-20261109/context/16_agent_research/critic/front_audit')
FILES=['audit.md','findings.csv','progress.md','input_manifest.json','primary_manifest.json','reproduction.json','partial_day_impact.json']
now=datetime.datetime.now(datetime.timezone.utc).isoformat();rows=[]
for name in FILES:
 source=SOURCE/name;b=source.read_bytes();sha=hashlib.sha256(b).hexdigest()
 rel=Path('review_evidence/front_audit_20261109')/name;out=P/rel
 out.parent.mkdir(parents=True,exist_ok=True)
 if out.exists():assert out.read_bytes()==b,'Review changed; capture a new version instead of overwriting '+str(out)
 else:out.write_bytes(b)
 assert hashlib.sha256(source.read_bytes()).hexdigest()==sha,'Source changed during snapshot'
 rows.append({'dataset_id':'CRITIC_FRONT_'+name.replace('.','_'),'source_url':str(source),'source_path':str(source),'raw_path':str(rel),'sha256':sha,'bytes':len(b),'retrieved_at_utc':now,'published_at':'2026-11-09; exact report publication time UNKNOWN','organization':'case_championship independent data critic','grain':'review_document_or_review_result','geographic_coverage':'Russian airports; targeted Favt Telegram pages 4685/4687/6503','temporal_coverage':'review 2026-11-09; inspected post examples April/July 2026','record_count':sum(1 for _ in csv.DictReader(b.decode().splitlines())) if name=='findings.csv'else None,'acquisition_status':'ACQUIRED_RAW','evidence_type':'REVIEW_EVIDENCE','value_status':'DERIVED','license':'UNKNOWN','reviewed_input_sha':'71b493d0051dc3acf2a7619801e5b0eb022bddd3','limitations':'Snapshot of critic review, not independently rerun here and not a complete reparse. Targeted44 posts/19 replies cannot estimate full-archive contamination. Primary raw remains at critic paths linked by its copied manifests.','collector_version':'capture_review.py v1','command':'python3 context/16_agent_research/hypotheses/contributions/existing_map/capture_review.py'})
manifest={'schema_version':1,'status':'REVIEW_EVIDENCE_SNAPSHOTTED','input_sha':'71b493d0051dc3acf2a7619801e5b0eb022bddd3','datasets':rows,'review_scope':{'selected_pages':3,'unique_posts':44,'reply_posts':19,'parser_body_mismatches':19,'sample_is_not_random':True,'full_history_reparse':'NOT_RUN','full_rating_recalculation_with_corrected_telegram':'NOT_RUN','local_rerun':'NOT_RUN'}}
(P/'review_source_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
with (P/'review_source_registry.csv').open('w',newline='')as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(json.dumps({'review_files':len(rows),'bytes':sum(r['bytes']for r in rows),'status':manifest['status']},ensure_ascii=False))
