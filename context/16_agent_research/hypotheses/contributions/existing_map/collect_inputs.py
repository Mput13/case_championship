#!/usr/bin/env python3
"""Read pinned Git blobs only; never execute colleague code. Outputs stay beside this file."""
from pathlib import Path
import csv,datetime,hashlib,io,json,subprocess
OUT=Path(__file__).resolve().parent
ROOT=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],text=True).strip())
SHA={'base':'9dbaee7ee53ee10ecb6db64d1cf634a7c0bceba7','front':'71b493d0051dc3acf2a7619801e5b0eb022bddd3','kiruha':'5e896e8ea5bb97136c71c49562a345b8f210bf11','team15':'83c2698ebebc172fd8f1d0b8a82b8bd07f8da791','team16':'bf564c7b66a2559c21e9f519ae5a3f28a489378f'}
paths={
'base':['context/16_agent_research/research_contract.md','context/16_agent_research/data_wishlist.csv','context/00_brief/case5_requirements.md','context/14_synthesis/knowledge.json','context/14_synthesis/analysis.md','context/09_additional_research/report.md','context/04_research/flash_methods/ideas.csv']+[str(p.relative_to(ROOT)) for p in (ROOT/'context/06_ideas').glob('*.md')]+[str(p.relative_to(ROOT)) for p in (ROOT/'context/14_synthesis/contributions').glob('*/*') if p.name in ['findings.json','report.md']],
'front':['docs/HANDOFF.md','data/sources.toml','src/update.py','src/fetch_telegram.py','src/scan_news.py','src/longlist_data.py','data/processed/destinations.csv','data/processed/longlist.csv','data/assumptions/longlist_weights.csv'],
'kiruha':['docs/00_index_and_ideas.md','docs/08_session_summary.md','docs/11_rail_bus_water_vs_air.md','docs/12_ground_inconvenience_prospects.md','docs/14_world_airline_videos_ideas.md','docs/16_scenarios_closures_reopening.md','docs/17_fleet_range_maintenance_time.md','docs/19_fresh_look_gaps_hypotheses.md'],
 'team15':['context/15_team_update/'+p for p in ['README.md','calculations.md','independent_review.md','route_evidence.csv','model/od_registry.csv','model/network_comparison.csv','model/standardized_OD_basis.csv','model/network_pairs.csv','model/validation.json']],
 'team16':['context/16_conditional_decision/'+p for p in ['brief.md','recommendation.md','assumptions.json','calculation_limits.md','research/README.md','research/decision_evidence.csv','research/ufa_mrv_calendar.csv','research/goj_svx_own_calendar.csv','model/validation.json','model/comparison.csv','model/selected_networks.json','model/pilot_booking_gate.csv','model/switch_summary.csv','front_review.json']]+['scripts/build_conditional_decision.py','scripts/write_conditional_note.py']}
mapping=OUT/'existing_hypotheses.csv'
if mapping.exists():
 for row in csv.DictReader(mapping.open()):
  group=next((k for k,v in SHA.items() if v==row['source_sha']),None)
  if group is None:
   group='origin_'+row['source_sha'][:8];SHA[group]=row['source_sha'];paths[group]=[]
  if row['source_path'] not in paths[group]:paths[group].append(row['source_path'])
rows=[];errors=[];now=datetime.datetime.now(datetime.timezone.utc).isoformat()
for group, pp in paths.items():
 for p in pp:
  r=subprocess.run(['git','show',SHA[group]+':'+p],capture_output=True)
  if r.returncode:
   errors.append({'source_sha':SHA[group],'source_path':p,'error':r.stderr.decode()});continue
  b=r.stdout;local=Path('raw')/group/p;q=OUT/local;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
  n=None
  if p.endswith('.csv'):n=sum(1 for _ in csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))
  meta=subprocess.check_output(['git','show','-s','--format=%an|%aI',SHA[group]],text=True).strip().split('|')
  rows.append({'dataset_id':group+'_'+hashlib.sha256(p.encode()).hexdigest()[:12],'source_url':'https://github.com/Mput13/case_championship/blob/'+SHA[group]+'/'+p,'source_path':p,'source_sha':SHA[group],'raw_path':str(local),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'retrieved_at_utc':now,'published_at':meta[1],'organization':'case_championship research team','git_commit_author':meta[0],'grain':'source_document_or_table','geographic_coverage':'Russian regional aviation; foreign methodological examples','temporal_coverage':'2026-11-09 research snapshot; underlying source periods vary','record_count':n,'acquisition_status':'ACQUIRED_RAW','value_status':'UNKNOWN','license':'UNKNOWN','limitations':'Git snapshot of colleague material, not independent primary validation; claims retain original evidence status. Git author proves file contribution, not sole intellectual authorship.','collector_version':'collect_inputs.py v1','command':'python3 context/16_agent_research/hypotheses/contributions/existing_map/collect_inputs.py'})
(OUT/'dataset_manifest.json').write_text(json.dumps({'schema_version':1,'retrieved_at_utc':now,'input_shas':SHA,'datasets':rows,'unavailable':errors},ensure_ascii=False,indent=2)+'\n')
with (OUT/'source_registry.csv').open('w',newline='')as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(json.dumps({'sources':len(rows),'bytes':sum(r['bytes'] for r in rows),'unavailable':errors},ensure_ascii=False))
