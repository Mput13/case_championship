#!/usr/bin/env python3
"""Meaningful offline acceptance: integrity, scope, source definitions and publication boundary."""
from pathlib import Path
from datetime import datetime,timezone
import json,csv,hashlib,subprocess,sys,collections
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
ALLOW={'content-type','content-length','date','last-modified','etag','cache-control','location'}
def sha(b):return hashlib.sha256(b).hexdigest()
def jsonread(p):return json.loads((ROOT/p).read_text())
def csvread(p):return list(csv.DictReader((ROOT/p).open()))
def save(p,x):(ROOT/p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def verify():
 checks={};plan=jsonread('plan.json');receipts={p.stem:json.loads(p.read_text()) for p in (ROOT/'receipts').glob('*.json')};inventory=csvread('inventory.csv');summary=jsonread('recovery_summary.json');coverage=jsonread('semantic_validation.json')
 assert len(plan)==49 and len(receipts)==49 and len(inventory)==63
 assert len({x['item_id'] for x in inventory})==63
 for x in inventory:
  for k in ['claim_task','source_url','original_path','original_error','original_date','kind','actual_workaround_omission','relevance','retry_action','retry_status','methodology_impact','restoration']:assert x[k],(x['item_id'],k)
  if x['parent_item']:assert x['parent_item'] in {r['item_id'] for r in inventory}
 assert summary['actual_http_reads']==47 and summary['inventory_items']==63
 assert sum(r['status']=='FETCHED' for r in receipts.values())==16
 checks['inventory_complete_unique_and_all_no_retry_reasons']='PASS'
 for i,r in receipts.items():
  assert set(r.get('response_headers',{}))<=ALLOW
  assert r.get('tls_verification') is True
  if r.get('raw_path'):
   p=ROOT/r['raw_path'];assert p.resolve().is_relative_to((ROOT/'raw_hold').resolve())
   b=p.read_bytes();assert sha(b)==r['stored_sha256'] and len(b)==r['stored_size_bytes']
   if r['stored_sha256']==r['source_sha256']:assert sha(b)==r['sha256']
   ignored=subprocess.run(['git','check-ignore','-q',str(p)],cwd=REPO).returncode;assert ignored==0,str(p)
  if r['status']=='FETCHED':assert coverage[i]['status'] not in ['CONTENT_CHECK_PENDING','NOT_ACQUIRED']
 checks['stored_raw_hashes_sizes_tls_headers_and_git_ignore']='PASS'
 checks['every_HTTP200_semantically_classified']='PASS'
 for x in jsonread('pinned_references.json'):
  b=subprocess.check_output(['git','show',x['source_sha']+':'+x['path']],cwd=REPO);assert sha(b)==x['sha256'] and len(b)==x['size_bytes']
 checks['pinned_Git_sourceSHA_and_content_hashes']='PASS'
 market=csvread('parsed/national_market_observations.csv');costs=csvread('parsed/khv_cost_components.csv');carrier=csvread('parsed/carrier_crosswalk_sample.csv');tg=csvread('parsed/telegram_selected_aggregate.csv')
 assert [len(x) for x in [market,costs,carrier,tg]]==[26,16,9,4]
 assert len([x for x in tg if x['validation_status'].startswith('HOLD')])==1
 assert {x['value'] for x in costs if x['source_id']=='khv_tariff_202611' and x['source_row'] in ['1.1.1','1.2.1']}=={'700.00','609.00'}
 assert all(x['effective_from']=='2026-02-10' for x in costs if x['source_id']=='khv_tariff_202611' and x['source_row'] in ['1.1.1','1.2.1'])
 assert all(x['temporal_role']=='HISTORICAL_SUPERSEDED_AT_CAPTURE' for x in costs if x['source_id']=='khv_tariff_current')
 checks['parsed_rows_grain_period_and_KHV_revision_gates']='PASS'
 native=csvread('native_read_outcomes.csv');assert len(native)==16
 for x in native:assert (ROOT/'raw_hold'/x['result_capture']).exists()
 for x in jsonread('native_factual_extracts.json')['facts']:
  for p in x['evidence'].split('; '):assert (ROOT/p).exists(),p
 checks['native_result_lineage_no_forged_source_byte_hash']='PASS'
 assert jsonread('input_set.json')['integration_status'].startswith('NOT_INTEGRATED')
 assert summary['no_paid_model_calls'] is True
 # Bounded collector contains only the single declared read-only POST.
 posts=[r for r in receipts.values() if r['method']=='POST'];assert len(posts)==1 and posts[0]['request_parameters'][0][0]=='get-availability' and posts[0]['http_status']==403
 checks['frozen_boundary_and_single_read_only_RPC']='PASS'
 return checks
if __name__=='__main__':
 checks=verify()
 save('verification.json',dict(verified_at_utc=datetime.now(timezone.utc).isoformat(),status='PASS_SCOPED',checks=checks,limits='Offline author/source integrity and semantic-boundary checks; no new network/model requests; does not verify live sales, source truth, full archive or external independent acceptance'))
 if '--build-manifest' in sys.argv:
  files=[]
  for p in sorted(ROOT.rglob('*')):
   if not p.is_file() or p.name in ['manifest.json','manifest_sha256.txt'] or '__pycache__' in p.parts:continue
   rel=str(p.relative_to(ROOT));b=p.read_bytes();files.append(dict(path=rel,size_bytes=len(b),sha256=sha(b),publication='LOCAL_HOLD_IGNORED' if rel.startswith('raw_hold/') else 'PUBLIC_SAFE_METADATA_OR_SELECTED_FACTS'))
  contracts=[]
  for rel in ['context/16_agent_research/status.json','context/16_agent_research/threads.json','context/16_agent_research/research_contract.md','context/16_agent_research/integration_contract.md','context/16_agent_research/absence_report.md','context/16_agent_research/kover_scenario_spec.md','context/16_agent_research/diagnostics/sites_concurrency_20261109.md','context/08_audit/argon_failure_diagnostic.md','context/14_synthesis/argon_watchdog_diagnostic.md']:
   b=(REPO/rel).read_bytes();contracts.append(dict(path=rel,sha256=sha(b),size_bytes=len(b),capture_semantics='Hash at package finalization; mutable local context, not original source commit'))
  sources=[]
  for p in sorted((ROOT/'receipts').glob('*.json')):
   r=json.loads(p.read_text());sources.append(dict(source_id=r['item_id'],source_url=r['source_url'],sourceSHA=r.get('source_sha256'),storedSHA=r.get('stored_sha256'),method=r['method'],request_started_at_utc=r['request_started_at_utc'],completed_at_utc=r['completed_at_utc'],raw_path=r.get('raw_path'),status=r['status']))
  m=dict(manifest_version='network-recovery-manifest-v1',input_set='network-recovery-20261109-v1',generated_at_utc=datetime.now(timezone.utc).isoformat(),sourceSHA=jsonread('recovery_summary.json')['source_pins'],source_snapshots=sources,pinned_input_metadata='pinned_references.json',local_contract_hashes=contracts,native_tool_delivery_hashes='native_tool_manifest.json',publication_policy='Full pages, PDF, cached text and any contacts held in ignored raw_hold; only selected factual extracts and metadata public. Hidden form values stripped in held HTML; original sourceSHA and storedSHA separate.',replay=dict(collector='python3 collect_recovery.py --fetch (existing receipts never retried; use a new folder/input-set for a new date)',offline=['python3 parse_recovery.py','python3 finalize_recovery.py','python3 verify_package.py --build-manifest']),files=files,verification='verification.json',self_hash_policy='Manifest excludes itself and manifest_sha256.txt; SHA provided separately')
  save('manifest.json',m);(ROOT/'manifest_sha256.txt').write_text(sha((ROOT/'manifest.json').read_bytes())+'  manifest.json\n')
 print(json.dumps({'status':'PASS_SCOPED','checks':len(checks),'public_files':sum(not str(p.relative_to(ROOT)).startswith('raw_hold/') for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts)},ensure_ascii=False))
