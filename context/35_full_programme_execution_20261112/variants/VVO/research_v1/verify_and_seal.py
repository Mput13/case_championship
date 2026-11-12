"""Offline integrity/resource checks. No Git, network, paid execution or P06 claims."""
import ast,csv,datetime,hashlib,json,re,shutil
from collections import Counter,defaultdict
from pathlib import Path
from extract_local import ROOT,write_csv,dump

def sha(raw):return hashlib.sha256(raw).hexdigest()
def readcsv(name):return list(csv.DictReader((ROOT/name).open()))
def main():
 checks=[]
 def check(name,ok,detail):
  checks.append({'check':name,'passed':bool(ok),'detail':detail})
 required=['case.json','evidence.csv','market_deltas.csv','hypotheses.json','programme_candidates.json','comparison_requests.csv','assumptions.csv','readiness.json','handoff.json','input_manifest.json']
 check('required_outputs',all((ROOT/x).is_file() and (ROOT/x).stat().st_size>10 for x in required),required)
 for f in ROOT.glob('*.py'):ast.parse(f.read_text())
 check('python_syntax',True,'Все локальные скрипты разобраны через ast; сетевых запросов здесь нет.')
 parsed=0
 for f in ROOT.rglob('*.json'):
  if '__pycache__' in f.parts or f.name in ['output_manifest.json','validation.json']:continue
  json.loads(f.read_text());parsed+=1
 check('json_parse',True,parsed)
 hashes=[]
 for f in (ROOT/'sources').glob('*.receipt.json'):
  r=json.loads(f.read_text())
  if r['status']=='CAPTURED':hashes.append(sha((ROOT/r['path']).read_bytes())==r['sha256'])
 check('captured_public_source_hashes',all(hashes),{'verified':len(hashes),'filtered_coordinates':'Полный набор не сохранён; его исходныйhash находитсявreceipt,selectedrowsотдельно.'})
 rowhash=[]
 for f in (ROOT/'inputs').glob('*.json'):
  o=json.loads(f.read_text())
  if isinstance(o,list):
   for r in o:
    if 'data' in r and 'source_row_sha256' in r:rowhash.append(sha(json.dumps(r['data'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())==r['source_row_sha256'])
 check('pinned_selected_row_hashes',all(rowhash),len(rowhash))
 obs=readcsv('schedule_observations.csv');evidence=readcsv('evidence.csv');ass=readcsv('assumptions.csv')
 check('schedule_rows_and_provenance',len(obs)==1178 and all(r['source_row_id'] and len(r['source_row_sha256'])==64 and len(r['source_blob_sha256'])==64 for r in obs),len(obs))
 check('unknown_inventory_preserved',all(r['saleable_seats']=='UNKNOWN' and r['inventory_id']=='UNKNOWN' for r in obs),'Ни один ярлык API не преобразован в продаваемые кресла.')
 check('WZ_sample_only',not any(r['flight_label'].startswith('WZ-') for r in obs),'Отрицательная выборка не выводит полное отсутствие RW.')
 sid={json.loads(f.read_text())['source_id'] for f in (ROOT/'sources').glob('*.receipt.json')}
 check('evidence_source_resolution',all(r['source_id'] in sid for r in evidence),len(evidence))
 check('evidence_units_periods_coverage',all(all(r[k] for k in ['unit','period','coverage','status','source_url','organisation','source_locator'] if k!='source_locator') for r in evidence),len(evidence))
 stops=json.loads((ROOT/'throughstop_observations.json').read_text())
 check('IO106_ordered_stoplist',any(r['flight_label']=='IO-106' and r['ordered_airports']==['VVO','BQS','HTA','IKT'] for r in stops),'Объявленный station-pair IKT не трактуется nonstop.')
 e36=next(r for r in evidence if r['evidence_id']=='E36')
 check('direct_BQS_UUS_control',e36['value']=='8460','FAVT2026строка14 — регуляторный тариф/маршрут,не livequote.')
 f=readcsv('diagnostic_flights.csv');by=defaultdict(list)
 for r in f:by[(r['programme_id'],r['aircraft_id'])].append(r)
 conflict=[]
 for k,rs in by.items():
  rs.sort(key=lambda r:r['departure_utc'])
  for a,b in zip(rs,rs[1:]):
   gap=(datetime.datetime.fromisoformat(b['departure_utc'])-datetime.datetime.fromisoformat(a['arrival_utc'])).total_seconds()/60
   if gap<60 or a['destination_airport']!=b['origin_airport']:conflict.append([k,a['flight_instance_id'],b['flight_instance_id'],gap])
 check('central_fragment_continuity',not conflict,{'legs':len(f),'conflicts':conflict})
 def footprint(pid):return Counter((r['origin_airport'],r['destination_airport'],r['departure_local'][:10],r['block_min'],r['nominal_seats_scenario']) for r in f if r['programme_id']==pid)
 check('H2_R2_same_routes_days_resource',footprint('P-VVO-H2')==footprint('P-VVO-R2'),'Только время и условия защиты различаются;сравнениецен/продажнеисполнено.')
 connections=json.loads((ROOT/'connection_candidates.json').read_text())
 check('six_120min_connections',len(connections)==6 and all(r['connection_minutes']==120 for r in connections),len(connections))
 # Stress fixed departure times: failed turns require retiming, not a city-level rejection.
 g={(r['origin'],r['destination']):r for r in readcsv('geometry_and_block_proxies.csv')};sens=[]
 for pid in ['P-VVO-R1','P-VVO-R2','P-VVO-H2','P-VVO-ALT-SVX']:
  for blockcol in ['lower_planning_min','planning_block_min','upper_planning_min']:
   for turn in [45,60,90]:
    collisions=0;daily=defaultdict(int)
    for (programme,tail),rs in by.items():
     if programme!=pid:continue
     for r in rs:
      geom=g.get((r['origin_airport'],r['destination_airport']),g.get((r['destination_airport'],r['origin_airport'])));daily[(tail,r['departure_local'][:10])]+=int(geom[blockcol])
     for a,b in zip(rs,rs[1:]):
      geom=g.get((a['origin_airport'],a['destination_airport']),g.get((a['destination_airport'],a['origin_airport'])));arrival=datetime.datetime.fromisoformat(a['departure_utc'])+datetime.timedelta(minutes=int(geom[blockcol]));gap=(datetime.datetime.fromisoformat(b['departure_utc'])-arrival).total_seconds()/60
      if gap<turn:collisions+=1
    maxbh=max(daily.values())/60
    sens.append({'programme_id':pid,'block_proxy':blockcol,'turn_min':turn,'fixed_departure_turn_conflicts':collisions,'max_daily_block_h':round(maxbh,2),'days_over8BH':sum(x>480 for x in daily.values()),'days_over10BH':sum(x>600 for x in daily.values()),'days_over12BH':sum(x>720 for x in daily.values()),'status':'нужнаперестановкавремени' if collisions else 'толькоproxyturn/позициябезконфликта','unit':'конфликты;блок-часы;дни','period':'03–09.07.2028,диагностика','coverage':'фиксированные departures;не проверкаcrew/AFM/MRO/reserve/слотов','source_id':'geometry_and_block_proxies.csv;diagnostic_flights.csv','assumption_id':'VVO-A02;VVO-A03;VVO-A09'})
 write_csv('resource_sensitivity.csv',sens)
 check('resource_stress_not_hidden',any(r['fixed_departure_turn_conflicts'] for r in sens),'Сдвигproxyblock/turnможетнарушатьфиксированноерасписание;таблицанеисправляетсярадиPASS.')
 hs=json.loads((ROOT/'hypotheses.json').read_text())['hypotheses'];p=json.loads((ROOT/'programme_candidates.json').read_text())['programmes']
 check('all_hypotheses_explained',len(hs)==7 and all(all(r[k] for k in ['signal','source','mechanism','counterfactual','distinguishingtest','ancestorIDs','outcome','outcome_evidence','condition_to_revisit']) for r in hs),len(hs))
 check('all_programmes_use_shared_inputs',len(p)==6 and all(r['needs_common_inputs'] and r['own_sales_policy'] and r['delivery_logic'] and r['tu214_new_aircraft_branch']==0 for r in p),len(p))
 check('24_month_scope_preserved',len(readcsv('programme_monthly_spec.csv'))==24*6,'Месячнаяспецификация;неизвестныеflightcounts/demandне0,не52x.')
 check('no_unconditional_money_claim',json.loads((ROOT/'readiness.json').read_text())['P06_executed'] is False and all(r.get('revenue_RUB')=='NOT_RUN' for r in readcsv('market_deltas.csv')),'P05/P06рыночная/денежнаяприёмкаNOT_RUN.')
 check('assumptions_described',len(ass)==18 and all(all(r[k] for k in ['selected_by','why','range_or_UNKNOWN','affected_conclusion','sensitivity','refinement','source_id']) for r in ass),len(ass))
 required_qa=['VVO_AIRPORT_RATES-1.png','VVO_AIRPORT_RATES-6.png','VVO_TERMINAL_DOWNLOAD-01.png','VVO_TERMINAL_DOWNLOAD-10.png','VVO_TERMINAL_DOWNLOAD-11.png','VVO_INCENTIVES-13.png','VVO_HANDLING-17.png','VVO_HANDLING-23.png','FAVT_DFO_2026-1.png']
 check('material_PDF_pages_preserved',all((ROOT/'qa'/x).exists() for x in required_qa),'Страницыоткрытычерезview_image:ставки,примечания,условияскидок,55/70мин,прямойBQS–UUS.')
 dump('validation.json',{'status':'PASS' if all(r['passed'] for r in checks) else 'FAIL','checks':checks,'check_count':len(checks),'independent_acceptance':'NOT_RUN;проверкивыполненыавторомлокальногопакета','acceptance_boundary':'Целостность/схема/арифметика/условнаяпозиция.Не фактическийрынок/свободныйпарк/dispatch/финансы/готовностьпаспорта.','resource_sensitivity':'resource_sensitivity.csv:отрицательныеfixedscheduleстрокисохранены.'})
 assert all(r['passed'] for r in checks),[r for r in checks if not r['passed']]
 # Task-created bytecode only; no user runtime/dependencies are removed.
 for d in ROOT.rglob('__pycache__'):shutil.rmtree(d)
 files=[]
 for path in sorted(ROOT.rglob('*')):
  if not path.is_file() or path.name=='output_manifest.json':continue
  files.append({'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':sha(path.read_bytes()),'kind':'source' if 'sources' in path.parts else 'pinned_extract' if 'inputs' in path.parts else 'visual_source_QA' if 'qa' in path.parts else 'deliverable_or_reproducer'})
 dump('output_manifest.json',{'package_id':'VVO-research-v1','stage':'A COMPLETE;B OPEN','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'root':str(ROOT),'source_pins':json.loads((ROOT/'input_manifest.json').read_text())['pins'],'scope':'Толькоэтоткаталог;коммиткоординатором;общийGitнеизменялся.','manifest_self_hash_policy':'Файлmanifestнехешируетсамсебя;итоговыйSHA256передаётсякоординаторуотдельно.','file_count':len(files),'total_bytes':sum(r['bytes'] for r in files),'files':files})
 print(json.dumps({'status':'PASS','checks':len(checks),'file_count':len(files),'bytes':sum(r['bytes'] for r in files),'manifest_sha256':sha((ROOT/'output_manifest.json').read_bytes())},ensure_ascii=False))

if __name__=='__main__':main()
