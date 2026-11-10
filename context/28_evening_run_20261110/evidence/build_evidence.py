#!/usr/bin/env python3
"""Offline assembly of pinned evidence. No HTTP, no external effects."""
import csv,hashlib,json,pathlib,re,collections,datetime
from lxml import html
R=pathlib.Path(__file__).resolve().parent
G=R/'raw/git'
B=G/'4a9971be/context/21_visual_explainer_draft_20261110/inputs'
N=G/'4a976356/data'
def read(p):
 with open(p,newline='') as f:return list(csv.DictReader(f))
def write(name,rows,fields=None):
 if fields is None:fields=list(dict.fromkeys(k for x in rows for k in x))
 with (R/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
def key(a,b):return '-'.join(sorted((a,b)))
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
active={'C01','C03','C04','C07','C10','C14','C17','C31','C33','C35'}
links=[]
for c in read(B/'candidates.csv'):
 if c['candidate_id'] not in active:continue
 for path in c['proposed_paths'].split(';'):
  pts=path.split('>')
  for a,b in zip(pts,pts[1:]):
   links.append(dict(hypothesis=c['candidate_id'],network=c['candidate_id']+'_registered',route=key(a,b),origin=a,destination=b,role='physical_leg',specification='registered_path_not_adopted_timetable',source='context21 candidates.csv:'+c['candidate_id'],observation_vs_model='HYPOTHESIS_SPECIFICATION'))
  if c['candidate_id']=='C01':
   links.append(dict(hypothesis='C01',network='C01_registered',route=key(pts[0],pts[-1]),origin=pts[0],destination=pts[-1],role='endpoint_journey',specification='north_south_OD_via_UFA',source='context21 candidates.csv:C01',observation_vs_model='HYPOTHESIS_SPECIFICATION'))
# C07 endpoint market and C35 through journey are distinct from physical legs.
for cid,a,b in [('C07','SVX','KJA'),('C35','IJK','OMS'),('C35','KRO','GOJ')]:
 links.append(dict(hypothesis=cid,network=cid+'_registered',route=key(a,b),origin=a,destination=b,role='endpoint_journey',specification='through_OD_not_two_independent_sales',source='context21 candidates.csv:'+cid,observation_vs_model='HYPOTHESIS_SPECIFICATION'))
# Historical owner OMS12 comparator, kept separate from compact C04.
ledger=read(G/'5905f8e8/context/27_oms388_independent_audit_20261110/replay/ledger.csv')
for x in ledger:
 if x['record_type']=='od_local':
  links.append(dict(hypothesis='C04',network='OWNER_OMS12_d4a6eab',route=key(x['a'],x['b']),origin=x['a'],destination=x['b'],role='owner_comparator_spoke',specification='historical_model_2028_proxy_not_new_compact_C04',source='5905f8:replay/ledger.csv',observation_vs_model='MODEL_OUTPUT'))
# Documented candidate alternative paths add their actual constituent pairs to coverage.
# These are comparison candidates, not validated protected connections.
for cid,path in [('C01','NJC>SVX>MRV'),('C01','UFA>SVX>MRV'),('C03','KUF>SVX>OMS'),('C03','KUF>SVX>NJC'),('C04','OMS>SVX>UFA'),('C07','SVX>KJA'),('C10','UFA>SVX>SGC'),('C14','KVX>MRV'),('C17','PEE>SVX>MMK'),('C31','SVX>MRV'),('C33','GOJ>SVX>OMS'),('C35','IJK>SVX>OMS')]:
 pts=path.split('>')
 for a,b in zip(pts,pts[1:]):
  links.append(dict(hypothesis=cid,network=cid+'_alternative_context',route=key(a,b),origin=a,destination=b,role='alternative_path_leg',specification='candidate path; connection/ticket/residual seats not established',source='authored comparison using captured published route graph',observation_vs_model='ALTERNATIVE_TO_VERIFY'))
for airport in ('DME','SVO'):
 links.append(dict(hypothesis='C04',network='OWNER_OMS12_airport_context',route=key('OMS',airport),origin='OMS',destination=airport,role='observed_airport_context_for_MOW',specification='actual airport evidence; model MOW remains unresolved',source='official OMS winter2026 PDF',observation_vs_model='AIRPORT_IDENTITY_CONTEXT_NOT_MODEL_CHANGE'))
links=list({tuple(x.values()):x for x in links}.values());links.sort(key=lambda x:(x['hypothesis'],x['network'],x['route'],x['role']));write('pair_hypothesis_join.csv',links)
pairs=sorted({x['route'] for x in links})
# Official regional HTML table; preserve commas in fractional roundtrip entries.
t=html.fromstring((R/'raw/web/favt_regional_oldhost/source.html').read_bytes()).xpath('//table')[-1]
grid={};rows=[]
for ri,tr in enumerate(t.xpath('.//tr')):
 ci=0
 for cell in tr.xpath('./td|./th'):
  while (ri,ci) in grid:ci+=1
  val=' '.join(cell.text_content().split())
  for rr in range(int(cell.get('rowspan','1'))):
   for cc in range(int(cell.get('colspan','1'))):grid[ri+rr,ci+cc]=val
  ci+=int(cell.get('colspan','1'))
 vals=[grid.get((ri,i),'') for i in range(11)]
 if ri:rows.append(vals)
cols=['route_no','airline','origin_city','destination_city','km','aircraft','seats','period','flights_per_week','round_trips_2026','cofinancing_note']
sub=[dict(zip(cols,v),html_table_row=i+2) for i,v in enumerate(rows)]
# IATA aliases pinned to airport/city identity; MOW stays unresolved.
name={x['iata']:x.get('name','') for x in read(N/'manual/airport_names.csv')}
alias={'Екатеринбург':'SVX','Омск':'OMS','Самара':'KUF','Уфа':'UFA','Нижневартовск':'NJC','Минеральные Воды':'MRV','Архангельск':'ARH','Сургут':'SGC','Махачкала':'MCX','Красноярск':'KJA','Пермь':'PEE','Тюмень':'TJM','Киров':'KVX','Мурманск':'MMK','Горно-Алтайск':'RGK','Ижевск':'IJK','Курган':'KRO','Нижний Новгород':'GOJ','Иркутск':'IKT','Волгоград':'VOG','Саратов':'GSV','Улан-Удэ':'UUD','Братск':'BTK','Абакан':'ABA','Москва':'MOW','Казань':'KZN','Челябинск':'CEK','Ярославль':'IAR','Новокузнецк':'NOZ','Томск':'TOF'}
for x in sub:
 x.update(origin=alias.get(x['origin_city'],''),destination=alias.get(x['destination_city'],''),source_id='favt_regional_oldhost',source_url='https://old.favt.gov.ru/dejatelnost-vozdushnye-perevozki-subsidirovanie-regiony/',observation_vs_model='OFFICIAL_2026_PROGRAM_LIST_NOT_EXECUTION_OR_CASH',source_sha256=h(R/'raw/web/favt_regional_oldhost/source.html'))
 x['route']=key(x['origin'],x['destination']) if x['origin'] and x['destination'] else ''
write('extracts/favt_regional_2026_full.csv',sub)
matched=[x for x in sub if x['route'] in pairs];write('subsidy_route_matches.csv',matched)
# Prior airport schedule instances, reused with inherited primary provenance.
obs=[]
for i,x in enumerate(read(B/'published-services.csv'),2):
 if key(x['origin'],x['destination']) not in pairs:continue
 obs.append(dict(observation_id='OLD'+str(i),route=key(x['origin'],x['destination']),origin=x['origin'],destination=x['destination'],carrier=x['carrier'],flight=x['flight'],date=x['date'],period=x['period'],departure_local=x['departure_local'],arrival_local=x['arrival_local'],weekdays=x['weekdays'],aircraft=x['aircraft'],seats='',seats_status='UNKNOWN_AIRLINE_CONFIGURATION',fare_rub='',fare_status='NO_FINAL_SAME_DATE_BAGGAGE_QUOTE',source_id='context21_published_services',source_url=x['source_url'],raw_sha256=x['html_sha256'],snapshot_sha256=h(B/'published-services.csv'),locator='published-services.csv line '+str(i),observation_vs_model='REUSED_PRIMARY_PUBLISHED_INSTANCE_YEAR_ASSIGNED',applicability='2026-12-07/13 only; no annual extrapolation; execution and residual seats unknown'))
# Fresh UFA rows: active CSS weekdays, not all seven day labels.
for sid,dest in [('ufa_omsk','OMS'),('ufa_surgut','SGC'),('ufa_njc','NJC'),('ufa_mrv','MRV')]:
 p=R/'raw/web'/sid/'source.html'
 if not p.exists():continue
 tree=html.fromstring(p.read_bytes())
 for i,row in enumerate(tree.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," b-card-sez-card__main ")]'),1):
  def cell(cls):
   v=row.xpath('.//div[contains(concat(" ",normalize-space(@class)," ")," '+cls+' ")]//span[contains(concat(" ",normalize-space(@class)," ")," b-card-sez-card__info ")]')
   return ';'.join(' '.join(x.text_content().split()) for x in v)
  flight=cell('b-card-sez-card__td_number')
  if not flight:continue
  days=row.xpath('.//span[contains(concat(" ",normalize-space(@class)," ")," _active ")]/text()')
  obs.append(dict(observation_id=sid+'_'+str(i),route=key('UFA',dest),origin='UFA',destination=dest,carrier=cell('b-card-sez-card__td_company'),flight=flight,date='',period=cell('b-card-sez-card__td_period'),departure_local=cell('b-card-sez-card__td_time--start'),arrival_local=cell('b-card-sez-card__td_time--end'),weekdays=';'.join(x.strip() for x in days),aircraft=cell('b-card-sez-card__td_flight'),seats='',seats_status='UNKNOWN_AIRLINE_CONFIGURATION',fare_rub='',fare_status='NO_FINAL_SAME_DATE_BAGGAGE_QUOTE',source_id=sid,source_url=json.loads((p.parent/'receipt.json').read_text())['url'],raw_sha256=h(p),snapshot_sha256='',locator='b-card-sez-card__main index '+str(i),observation_vs_model='PRIMARY_PUBLISHED_RULE_OR_SINGLE_DATE',applicability='source-specific offer; nominal type not seats; not all displayed weekday labels are active'))
# Fresh airport table rules. Period years are assigned to winter 2026/27 explicitly.
for sid,origin in [('koltsovo_schedule','SVX'),('koltsovo_schedule_arr','SVX'),('samara_schedule','KUF')]:
 p=R/'raw/web'/sid/'source.html'
 if not p.exists():continue
 tree=html.fromstring(p.read_text())
 for i,tr in enumerate(tree.xpath('//table//tr'),1):
  cells=[' '.join(c.text_content().split()) for c in tr.xpath('./td|./th')]
  if len(cells)!=8 or cells[-1] not in alias.values() or key(origin,cells[-1]) not in pairs:continue
  dep,arr,days,period,carrier,flight,aircraft,dest=cells
  row_origin,row_dest=(dest,origin) if sid.endswith('_arr') else (origin,dest)
  obs.append(dict(observation_id=sid+'_'+str(i),route=key(row_origin,row_dest),origin=row_origin,destination=row_dest,carrier=carrier,flight=flight,date='',period=period,departure_local=dep,arrival_local=arr,weekdays=days,aircraft=aircraft,seats='',seats_status='UNKNOWN_AIRLINE_CONFIGURATION',fare_rub='',fare_status='NO_FINAL_SAME_DATE_BAGGAGE_QUOTE',source_id=sid,source_url=json.loads((p.parent/'receipt.json').read_text())['url'],raw_sha256=h(p),snapshot_sha256='',locator='table tr index '+str(i),observation_vs_model='PRIMARY_PUBLISHED_RULE_YEAR_ASSIGNED',applicability='winter 2026/27 year assigned; route-specific rule, not execution; duplicate publications not additive'))
# UVT table has two directions in each row, each direction keeps its own clocks.
p=R/'raw/web/uvt_schedule/source.html'
tree=html.fromstring(p.read_text())
for ti,tab in enumerate(tree.xpath('//table'),1):
 headings=tab.xpath('preceding::*[contains(text(),"Из города")][1]/text()')
 city=' '.join(headings).replace('Из города','').strip()
 origin=alias.get(city)
 if not origin:continue
 for ri,tr in enumerate(tab.xpath('.//tbody/tr'),1):
  cells=[' '.join(c.text_content().split()) for c in tr.xpath('./td|./th')]
  # Rows with spanning columns are held; no guessed left-shift.
  if len(cells)!=12:continue
  dest=alias.get(cells[0]);period=cells[1];aircraft=cells[7]
  if not dest or key(origin,dest) not in pairs:continue
  for a,b,flight,dep,arr,days in [(origin,dest,*cells[3:7]),(dest,origin,*cells[8:12])]:
   if flight in ('','-'):continue
   obs.append(dict(observation_id=f'uvt_{ti}_{ri}_{a}',route=key(a,b),origin=a,destination=b,carrier='ЮВТ АЭРО',flight=flight,date='',period=period,departure_local=dep.replace('-',':'),arrival_local=arr.replace('-',':'),weekdays=days,aircraft=aircraft,seats='',seats_status='UNKNOWN_AIRLINE_CONFIGURATION',fare_rub='',fare_status='NO_FINAL_SAME_DATE_BAGGAGE_QUOTE',source_id='uvt_schedule',source_url='https://uvtaero.ru/raspisanie',raw_sha256=h(p),snapshot_sha256='',locator=f'table {ti} tbody/tr {ri}; {city}',observation_vs_model='PRIMARY_CARRIER_PUBLISHED_RULE',applicability='published rule; flight may include intermediate stop; rows duplicated from opposite city tables are not additive'))
# Selected OMS winter PDF rows; day column is anchored to the OMS calendar.
# Only departures FROM OMS are expanded; inbound local day needs its own source.
p=R/'raw/web/omsk_winter_pdf/text.txt'
selected=[]
if p.exists():
 for li,line in enumerate(p.read_text().split('\n'),1):
  cells=re.split(r'\s{2,}',line.strip())
  if len(cells)!=10:continue
  aircraft,flight,dep_other,path,arr_oms,dep_oms,days,period,carrier,arr_other=cells
  dest=next((v for k,v in [('Красноярск','KJA'),('Иркутск','IKT'),('Екатеринбург','SVX'),('Домодедово','DME'),('Шереметьево','SVO')] if path.startswith(k)),None)
  if not dest or key('OMS',dest) not in pairs:continue
  selected.append(dict(route=key('OMS',dest),raw_line=line,locator='raw/web/omsk_winter_pdf/text.txt:'+str(li),source_id='omsk_winter_pdf',primary_url='https://www.aeroomsk.ru/karta-poleta/pdf/w26/w26-20261105.pdf',raw_sha256=h(p.parent/'source.pdf'),calendar_basis='days column refers OMS; inbound departure day not independently assigned'))
  if dest=='SVX':continue # primary corroboration retained, no unverified ИН/WZ alias merge
  m=re.match(r'([A-ZА-Я0-9]+)\s*(\d+)\s*/\s*(\d+)',flight)
  if not m:continue
  number=m[1]+'-'+m[3]
  day_text='ежедневно' if days=='ежедневно' else ';'.join({'1':'пн','2':'вт','3':'ср','4':'чт','5':'пт','6':'сб','7':'вс'}[d] for d in re.findall('[1-7]',days))
  obs.append(dict(observation_id='omsk_pdf_'+str(li),route=key('OMS',dest),origin='OMS',destination=dest,carrier=carrier,flight=number,date='',period=period,departure_local=dep_oms.replace('.',':'),arrival_local=arr_other.replace('.',':'),weekdays=day_text,aircraft=aircraft,seats='',seats_status='UNKNOWN_AIRLINE_CONFIGURATION',fare_rub='',fare_status='NO_FINAL_SAME_DATE_BAGGAGE_QUOTE',source_id='omsk_winter_pdf',source_url='https://www.aeroomsk.ru/karta-poleta/pdf/w26/w26-20261105.pdf',raw_sha256=h(p.parent/'source.pdf'),snapshot_sha256='',locator='text.txt line '+str(li),observation_vs_model='PRIMARY_PUBLISHED_RULE_FULL_YEAR',applicability='OMS departure calendar only; inbound day and aircraft configuration not inferred'))
write('extracts/omsk_winter_selected_lines.csv',selected)
write('service_observations.csv',obs)
# Prior RW annualized assumptions remain separate from published date evidence.
rw=read(N/'manual/rw_routes_now.csv');rwrows=[]
for i,x in enumerate(rw,2):
 if key(x['a'],x['b']) in pairs:rwrows.append(dict(route=key(x['a'],x['b']),**x,locator='rw_routes_now.csv line '+str(i),observation_vs_model='OWNER_INPUT_'+x['freq_status'],annual_applicability='NOT_AUTOMATIC; subsidy annual average is not weekly schedule'))
write('rw_prior_inputs.csv',rwrows)
coverage=[]
for pair in pairs:
 pp=[x for x in obs if x['route']==pair];ss=[x for x in matched if x['route']==pair];rr=[x for x in rwrows if x['route']==pair];ll=[x for x in links if x['route']==pair]
 carriers=sorted({x['carrier'] for x in pp}|{x['airline'] for x in ss})
 coverage.append(dict(route=pair,airport_a=pair.split('-')[0],airport_b=pair.split('-')[1],hypotheses=';'.join(sorted({x['hypothesis'] for x in ll})),networks=';'.join(sorted({x['network'] for x in ll})),roles=';'.join(sorted({x['role'] for x in ll})),published_records=len(pp),official_2026_program_rows=len(ss),rw_prior_input_rows=len(rr),named_carriers=';'.join(carriers),coverage_status='PARTIAL_POSITIVE_EVIDENCE' if pp or ss else 'GAP_NOT_ABSENCE',competitor_absence_established=False,complete_market=False,dated_final_fare_20kg_status='NOT_OBSERVED',residual_seats_status='UNKNOWN',future_2027_2028='NO_AUTOMATIC_EXTENSION',next_gap='airport identity required' if 'MOW' in pair else 'confirm year schedule, actual carrier, tariff with baggage and remaining seats; competing via and rail'))
write('pair_registry.csv',coverage)
# All hypothesis-network-route rows get coverage by exact normalized pair; never carrier-name substring alone.
checks={'active_hypotheses':sorted(active),'hypotheses_covered':sorted({x['hypothesis'] for x in links}),'pair_count':len(pairs),'hypothesis_route_rows':len(links),'orphan_pair_join':sorted({x['route'] for x in links}-set(pairs)),'service_orphans':sorted({x['route'] for x in obs}-set(pairs)),'subsidy_orphans':sorted({x['route'] for x in matched}-set(pairs)),'published_count':len(obs),'subsidy_match_count':len(matched),'false_absence_claims':sum(bool(x['competitor_absence_established']) for x in coverage),'status':'PASS_SCOPE_JOIN_ONLY_NOT_MARKET_ACCEPTANCE'}
assert not checks['orphan_pair_join'] and not checks['service_orphans'] and not checks['subsidy_orphans'];assert checks['active_hypotheses']==checks['hypotheses_covered']
(R/'join_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(checks,ensure_ascii=False,indent=2))
