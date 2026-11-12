#!/usr/bin/env python3
"""Root-authorised, lossless P09 transport. Copies producer values; no economics."""
import base64,csv,gzip,hashlib,io,json,pathlib,subprocess
P=pathlib.Path(__file__).resolve().parent
REPO=P.parents[2]
PRODUCER='736859fdd08448c2564b7b9269b751abe00b5cbc'
AUTH='b16c28c6fd2ba9ea509e8a618f5f3b7137f1985e'
MANIFEST='7b20a1a247ee4b3cf96d94648bb36d61482cb0a58eb7a296ada49a78c818d1fa'
PRE='context/35_full_programme_execution_20261112/P09/'
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def put(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def git(commit,path):return subprocess.check_output(['git','show',commit+':'+path],cwd=REPO)

def main():
 root=P/'inputs/P09_final';root.mkdir(exist_ok=True)
 ab=git(AUTH,'context/35_full_programme_execution_20261112/P00/p09_acceptance.json');a=json.loads(ab)
 assert a['coordinator_acceptance']=='ACCEPTED_FOR_UI' and a['payload_commit']==PRODUCER and a['manifest_sha256']==MANIFEST
 (root/'root_authorisation.json').write_bytes(ab)
 review_manifest=P/'inputs/P13_FINAL/output_manifest.json';review=json.loads((P/'inputs/P13_FINAL/review.json').read_text())
 assert sha(review_manifest.read_bytes())=='1c612a8595183d7d614cdb70b24a1349a9a460dc0e04042ffbf906d715689557' and review['verdict']=='APPROVE_WITH_EXPLICIT_LIMITS'
 a['original_independent_acceptance']=a['independent_acceptance'];a['independent_acceptance']=review['verdict'];a['independent_review']={'source':'root explicit follow-up authorisation with frozen reviewed manifest','path':'context/35_full_programme_execution_20261112/P13_FINAL_PROGRAMMES/output_manifest.json','manifest_sha256':sha(review_manifest.read_bytes()),'reviewed_producer_commit':PRODUCER,'scope':review['accepted_scope']}
 mb=git(PRODUCER,PRE+'manifest.json');assert sha(mb)==MANIFEST
 manifest=json.loads(mb);(root/'manifest.json').write_bytes(mb);members={r['path']:r for r in manifest['files']};files=[];claims=[]
 def read(name,save=True):
  b=git(PRODUCER,PRE+name);assert sha(b)==members[name]['sha256'],name
  if save:
   target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
  files.append(dict(package='P09_FINAL',path=PRE+name,sha256=sha(b),bytes=len(b),version=PRODUCER,manifest_sha256=MANIFEST,snapshot=str((root/name).relative_to(P)) if save else None))
  return b
 def table(name):
  b=read(name);rows=[]
  for i,row in enumerate(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))),2):
   ref={'path':PRE+name,'commit':PRODUCER,'file_sha256':sha(b),'row_number':i,'row_sha256':sha(canonical(row)),'result_mode':'P06_DISJOINT_DATE_COMPONENTS_WITH_ADDITIVE_P06_FINANCE' if name=='scenario_results.csv' else 'PRODUCER_SOURCE_EXPORT'}
   row['_source']=ref;rows.append(row);claims.append({'claim_id':f'P09:{name}:{i}',**ref})
  return rows
 index=json.loads(read('ui/index.json'));contract=json.loads(read('projection_contract.json'))
 sidecar=json.loads(read('ui_resource_monthly.json'));cards=json.loads(read('programme_cards.json'));byid={r['programme_id']:r for r in cards}
 catalogue=[];packets={};audit=[];envelopes=[]
 for item in index['packages']:
  raw=read(item['path'],False);assert sha(raw)==item['sha256'];env=json.loads(raw)
  original_header={k:v for k,v in env.items() if k!='evaluations'}
  env.update(coordinator_acceptance='ACCEPTED_FOR_UI',commit=PRODUCER,manifest_sha256=MANIFEST,payload_kind='P09_UI_PROJECTION',projection_contract=contract,root_authorisation={'commit':AUTH,'path':'context/35_full_programme_execution_20261112/P00/p09_acceptance.json','sha256':sha(ab),'scope':a['acceptance_scope'],'independent_acceptance':a['independent_acceptance']},producer_original_header=original_header)
  metas=[]
  for e in env['evaluations']:
   rb=read(e['audit_receipt']);receipt=json.loads(rb);assert sha(canonical(e['result']))==e['projection_sha256']==receipt['projection_sha256']
   assert e['source_full_result_sha256']==receipt['full']['sha256'] and e['source_full_result_path']==receipt['full']['path']
   context=e['result']['project']['context'];assert context['fleet_scope_id']=='CASE_SJ' and context['delivery_calendar_id']=='P09-phased'
   assert e['result']['delta_summary']['operating_result'] is None and e['result']['project_incremental_funding']['peak_dated_day_end'] is None
   e['projection_meta']={'source_full_result_sha256':e['source_full_result_sha256'],'projection_sha256':e['projection_sha256'],'input_pins':receipt['input_manifest'],'result_mode':e['result_mode'],'audit':{'path':e['audit_receipt'],'sha256':sha(rb),'commit':PRODUCER},'replay':{'command':contract['replay'],'audit_script':contract['audit_script'],'commit':PRODUCER,'builder_sha256':receipt.get('builder_sha256')},'full_result_artifact':receipt['full'],'verified_same_path_leaves':receipt['verified_same_path_leaves']}
   e['resource_monthly']=[r for r in sidecar['rows'] if r['delivery']=='phased']
   e['resource_sidecar']={'mode':sidecar['result_mode'],'path':PRE+'ui_resource_monthly.json','sha256':members['ui_resource_monthly.json']['sha256'],'resource_group':sidecar['resource_group']}
   e['programme_card']=byid[context['programme_id']]
   assert sha(canonical(e['result']))==receipt['projection_sha256']
   metas.append({'label':e['label'],'scenario_label':e['scenario_label'],'context':context,'result_mode':e['result_mode'],'source_full_result_sha256':e['source_full_result_sha256'],'projection_sha256':e['projection_sha256'],'delta_summary':e['result']['delta_summary'],'delta_annual':e['result']['delta_annual'],'thresholds':e['result']['thresholds'],'network_target':e['result']['project']['network_target']})
   audit.append({'evaluation_id':context['evaluation_id'],'projection_sha256':e['projection_sha256'],'full_sha256':e['source_full_result_sha256'],'exact_result_preserved':True,'monthly_rows':len(e['result']['project']['results_monthly']),'rotations':len(e['result']['project']['operations']['rotations']),'network_changes':len(e['result']['network_changes']),'project_available_preserved_null':all(r['project_available'] is None for r in e['resource_monthly'])})
  b=canonical(env);compressed=gzip.compress(b,compresslevel=9,mtime=0);assert gzip.decompress(compressed)==b
  pid=item['programme_id'];packet=P/'accepted'/f'{pid}.json.gz';packet.parent.mkdir(exist_ok=True);packet.write_bytes(compressed)
  packets[pid]={'codec':'gzip-base64','data':base64.b64encode(compressed).decode(),'sha256':sha(b),'gzip_sha256':sha(compressed),'bytes':len(b),'compressed_bytes':len(compressed)}
  catalogue.append({'programme_id':pid,'label':metas[0]['label'],'city':byid[pid]['city'],'evaluations':metas,'producer_path':PRE+item['path'],'producer_sha256':sha(raw),'accepted_path':str(packet.relative_to(P)),'accepted_sha256':sha(b),'gzip_sha256':sha(compressed)})
  envelopes.append({k:v for k,v in catalogue[-1].items() if k!='evaluations'})
 overview=table('scenario_results.csv');dispositions=table('candidate_dispositions.csv');thresholds=table('thresholds.csv')
 secondary={'cards':cards,'overview':overview,'dispositions':dispositions,'threshold_rows':thresholds}
 sb=canonical(secondary);sgz=gzip.compress(sb,compresslevel=9,mtime=0);assert gzip.decompress(sgz)==sb
 (P/'accepted/producer_overview.json.gz').write_bytes(sgz)
 data={'version':'P15-final-conditional-v1','commit':PRODUCER,'manifest_sha256':MANIFEST,'authorisation_commit':AUTH,'root_authorisation':a,'default_programme':'VOG_RADIAL','default_scenario':'base','catalogue':catalogue,'packets':packets,'secondary_packet':{'codec':'gzip-base64','data':base64.b64encode(sgz).decode(),'sha256':sha(sb),'gzip_sha256':sha(sgz),'bytes':len(sb),'compressed_bytes':len(sgz)},'overview_contract':json.loads(read('data_contract.json'))['overview'],'ledger':json.loads(read('parameterledger.json')),'frontier':json.loads(read('finalist_selection.json')),'roadmap':json.loads(read('roadmap.json')),'metric_adapter':json.loads(read('metric_adapter_status.json')),'reports':{name:read(name).decode() for name in ['choice_report.md','economics_report.md']}}
 expert=P/'inputs/expert_final_coverage';assert sha((expert/'output_manifest.json').read_bytes())=='3c09a05cc35215e060173370463fc525f98f6804488c008e75a122fe9c8ba1b6'
 data['expert']={'manifest_sha256':sha((expert/'output_manifest.json').read_bytes()),'insertions':(expert/'final_insertions.md').read_text(),'assumptions':json.loads((expert/'assumptions.json').read_text()),'scope':'PARTIAL_COVERAGE; five material unknowns are not passed checks'}
 data['source_catalog']=json.loads((P/'inputs/source_catalog_root_context.json').read_text())
 # Numeric-equivalence document is retained separately; it never replaces canonical result.
 read('canonical_equivalence_checks.json');read('build_summary.json');table('canonical_summary.csv')
 put(P/'accepted/index.json',{'version':data['version'],'coordinator_acceptance':'ACCEPTED_FOR_UI','scope':a['acceptance_scope'],'independent_acceptance':a['independent_acceptance'],'independent_review':a['independent_review'],'producer_commit':PRODUCER,'producer_manifest_sha256':MANIFEST,'root_authorisation_commit':AUTH,'root_authorisation_sha256':sha(ab),'packages':envelopes,'default_programme':'VOG_RADIAL','result_values_modified':False,'producer_pending_files_modified':False})
 put(P/'quantitative_data.json',data);put(P/'quantitative_input_manifest.json',{'files':files,'root_authorisation':{'commit':AUTH,'sha256':sha(ab)},'claimed_scope':'Conditional research visualisation only'})
 put(P/'qa/projection_binding_audit.json',{'status':'PASS_EXACT_TRANSPORT_AND_ROOT_SCOPE','programme_count':len(catalogue),'evaluations':audit,'original_wrapper_bytes':sum(x['bytes'] for x in index['packages']),'gzip_bytes':sum(x['compressed_bytes'] for x in packets.values()),'overview_rows':len(overview),'full_profit_funding_share':'UNKNOWN; preserved','independent_programme_acceptance':a['independent_acceptance']})
 with (P/'quantitative_claim_links.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(claims[0]));w.writeheader();w.writerows(claims)
 print(json.dumps({'programmes':len(catalogue),'evaluations':len(audit),'overview':len(overview),'gzip_bytes':sum(x['compressed_bytes'] for x in packets.values())}))

def attach(data,intake):
 q=json.loads((P/'quantitative_data.json').read_text());index=json.loads((P/'accepted/index.json').read_text())
 assert index['coordinator_acceptance']=='ACCEPTED_FOR_UI' and q['commit']==PRODUCER and q['manifest_sha256']==MANIFEST
 data['lazy_results']=q;data['version']=q['version'];data['pins']['P09']=PRODUCER
 data['assumptions']+=q['ledger'];expert_assumptions=q['expert']['assumptions'];data['assumptions']+=expert_assumptions if isinstance(expert_assumptions,list) else expert_assumptions.get('assumptions',[]);data['release']['P09']='ACCEPTED_FOR_CONDITIONAL_RESEARCH_UI';data['release']['P06']='PINNED_982_CONDITIONAL_PROGRAMMES_REVIEWED_WITH_LIMITS'
 intake.files+=json.loads((P/'quantitative_input_manifest.json').read_text())['files']
 for r in csv.DictReader((P/'quantitative_claim_links.csv').open()):
  intake.claims.append({'package':'P09_PRODUCER_EXPORT','path':r['path'],'version':r['commit'],'file_sha256':r['file_sha256'],'source_row_number':r['row_number'],'source_row_id':r['claim_id'],'row_sha256':r['row_sha256'],'claim_id':r['claim_id'],'url':'Git blob '+r['commit']+':'+r['path'],'organization':'P09 research producer','as_of':'2026-11-12','period':'2027-01..2028-12','unit':'Source fields; RUB2026/journeys/segments/status; no reaggregation','granularity':r['result_mode'],'status':'CONDITIONAL_RESEARCH_SOURCE_EXPORT','coverage':'Alternative programmes; not additive','assumption_ids':'parameterledger.json'})
 for p in q['catalogue']:
  for i,e in enumerate(p['evaluations'],1):
   intake.claims.append({'package':'P09_CANONICAL_RESULT','path':p['producer_path'],'version':PRODUCER,'file_sha256':p['producer_sha256'],'source_row_number':i,'source_row_id':e['context']['evaluation_id'],'row_sha256':e['projection_sha256'],'claim_id':'CANONICAL:'+e['context']['evaluation_id'],'url':'Git blob '+PRODUCER+':'+p['producer_path'],'organization':'P09/P06 canonical projection','as_of':'2026-11-12','period':'2027-01..2028-12','unit':'Exact result fields; price_year2026','granularity':'canonical compare projection at evaluations[index].result','status':'CONDITIONAL_RESEARCH_ACCEPTED_FOR_UI','coverage':e['context']['affected_scope_id'],'assumption_ids':'parameterledger.json'})
 return data

if __name__=='__main__':main()
