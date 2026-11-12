from pathlib import Path
import csv,json,hashlib,subprocess,io,datetime as dt
R=Path(__file__).resolve().parents[2]; O=Path(__file__).resolve().parent
C=R/'context/36_overnight_chain_search_20261112'; P=R/'context/34_new_direct_top5_20261112/source_recovery_competitors'
PIN='cd04921fe5dd14dbf5c469b7f15a5efc203abc7b'
def rows(p):return list(csv.DictReader(p.open()))
def sha(b):return hashlib.sha256(b).hexdigest()
def write(n,rs):
 with (O/n).open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
def dump(n,d):(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
sources=[]
def src(sid,loc,kind,scope,limit,excerpt='',url=''):
 sources.append(dict(source_id=sid,location=loc,url=url,source_kind=kind,covered_dates=scope,limitations=limit,excerpt_file=excerpt))
# Preserve immutable source pins, without copying full artifacts.
manifest=[]
for ent in json.loads((C/'input_snapshot_manifest.json').read_text()):
 p=C/ent['snapshot'];assert sha(p.read_bytes())==ent['sha256'];manifest.append(ent)
paths=['P08/MOSCOW/research_v1/KEEP_evidence.csv','P08/MOSCOW/research_v1/market_evidence.csv','P08/MOSCOW/research_v1/direct_candidates.csv','P08/SVX/research_v1/direct_candidates.csv','P08/SVX/research_v1/evidence/SVX_primary_schedule_products.csv']
pinned={}
for p in paths:
 full='context/35_full_programme_execution_20261112/'+p
 b=subprocess.check_output(['git','show',PIN+':'+full],cwd=R);pinned[p]=list(csv.DictReader(io.StringIO(b.decode())))
 manifest.append(dict(commit=PIN,path=full,sha256=sha(b)))
dump('evidence/input_provenance.json',manifest)
# P34 original provenance + small excerpts only.
for r in rows(P/'sources.csv'):
 sid='P34-'+r['source_id'];fn='evidence/'+sid+'.txt'
 (O/fn).write_text(r['short_quote']+'\nLocator: '+r['locator']+'\nProves: '+r['proves']+'\nLimitations: '+r['limitations']+'\n')
 src(sid,str((P/'sources.csv').relative_to(R))+'#'+r['source_id'],r['source_kind'],r['covered_dates'],r['limitations'],fn,r['url'])
for sid,name,kind,scope,limit in [
 ('P34-CLASS','classification.csv','LOCAL_ADMISSION','two study weeks','Not proof of RW absence'),
 ('P34-SCHEDULE','schedules.csv','LOCAL_CANONICAL','per flight validity','Published pattern; contextual years; not execution'),
 ('P34-NOTES','notes.md','LOCAL_ADMISSION','per source','Yamal contradiction; not admitted numerical frequency')]:
 src(sid,str((P/name).relative_to(R)),kind,scope,limit)
for sid,p in [('P08-SVX','P08/SVX/research_v1/direct_candidates.csv'),('P08-MOW-KEEP','P08/MOSCOW/research_v1/KEEP_evidence.csv'),('P08-MOW-MARKET','P08/MOSCOW/research_v1/market_evidence.csv')]:
 src(sid,'git:'+PIN+':context/35_full_programme_execution_20261112/'+p,'PINNED_LOCAL','per original record','Design/history/partial market; no new calibration')
for sid,p in [('P09','P09/canonical_summary.csv'),('P08-MOW-HANDOFF','P08/MOSCOW/research_v1/handoff.md'),('P08-SVX-HANDOFF','P08/SVX/research_v1/HANDOFF.md')]:
 src(sid,str((C/'inputs/latest_team/context/35_full_programme_execution_20261112'/p).relative_to(R)),'PINNED_LOCAL','original scenario periods','P09 model outputs are not observed OD or net yield')
src('P36-PRIOR',str((C/'research_market/market_pairs.csv').relative_to(R)),'LOCAL_INCOMPLETE','two study weeks','UNKNOWN rows provide no new evidence; erroneous cross-pair P36-WEB1 removed')
# Exact new request logs and concise observations; no claim that an empty page is absence.
req=json.loads((O/'actual_requests.json').read_text())['requests']
new=[
 ('MOW-CITY','https://zbordirect.com/ru/tools/schedule?arrival_city=KGD&departure_city=MOW','SECONDARY_EMPTY','NONE','City MOW query returned no schedule; no per-flight codes available; not ZIA evidence','turn0view0 L5-L10: city header MOW; no schedule returned.'),
 ('RW-KGD2025','https://flyredwings.com/press/news/red-wings-otkryla-ezhednevnye-rejsy-iz-moskvy-v-kaliningrad/','PRIMARY_AIRLINE_HISTORICAL','2025-07-25 onward; continuation UNKNOWN','Not current 2026/27; no flight number or specific aircraft','turn0view1 L111-L118: publication 26 June 2025; DME; daily from 25 July, Fri/Sat/Sun from 8 September; 2h50; family fleet paragraph not flight aircraft.'),
 ('WZ-AIRPORTIA','https://www.airportia.com/route/moscow-kaliningrad-flights-zia-kgd/','LABELLED_SECONDARY','2026-09-24 only for WZ901','History only; incomplete tracker; no target-week absence inference','turn2view0 L23-L31,L42-L50: explicit ZIA/KGD; WZ901 Sep24 08:10/10:00 scheduled, departure 08:08. WZ903/4591 are separate records; no projection.'),
 ('WZ-PF','https://planefinder.net/data/flight/WZ901','LABELLED_SECONDARY','2026-09-24; 2026-11-12 separately','Tracker clocks conflict with Airportia; generic Charter label not route-date service classification; no primary operator proof','turn2view1 L2-L20: Red Wings WZ901; Sep24 ZIA/KGD SU95 RA-89122 09:25 MSK/09:05 EET; Nov12 LED/KGD SU95 RA-89138. Number reused; clocks quarantined.'),
 ('WZ-PIPP','https://pipp.enkeltsystem.no/ru/flight/wz-901','SECONDARY_SEARCH_OPEN_FAILED','2026-09-24 snippet only','Open TimeoutError; snippet not independent full table admission','turn1search3 lists Sep24 ZIA08:10/KGD10:00; other routes same flight number. turn2view2 TimeoutError.'),
 ('RW-BUS','https://flyredwings.com/press/news/red-wings-prodlila-programmu-poletov-iz-moskvy-v-gruziyu/','PRIMARY_AIRLINE','winter2026/27 starting2026-10-26; exact end UNKNOWN','Programme mixed SSJ100/Tu204/214; type/tail per flight UNKNOWN','turn2view3 L111-L114: 10 Aug2026 announcement; ZIA-BUS Tue/Fri/Sun 08:10; return14:20; TBS daily; mixed types.'),
 ('SVX-NEW','https://ar-svx.ru/schedule/','PRIMARY_AIRPORT','per flight row contextual winter2026/27','No full legal operator register; absence of WZ in pair block is not RW absence','turn4view2 L219-L226 repeats FV KJA patterns. turn4view1 L503-L511 AER has FV/DP/U6, no WZ in captured block. Year assigned contextually.'),
 ('RW-SVX-NEW','https://flyredwings.com/directions/ekaterinburg/','PRIMARY_AIRLINE_MARKETING','undated','Global city-selector entries are not route evidence; no dated nonstop register','turn3view1 L130-L184 destination marketing; turn4view3 Sochi match L299 is global selector, not SVX-AER flight.'),
 ('RW-WINTER','https://flyredwings.com/en/press/news/red-wings-pereshla-na-osenne-zimnee-raspisanie-poletov/','PRIMARY_AIRLINE','through2027-03-27 general programme only','Network announcement not exhaustive route-date/operator table; not primary confirmation of three target own routes','turn4view0 L111-L118: publication27Oct2026; winter through27Mar2027; hub cities/regions; no pair-specific KJA/AER/KGD timetable.')]
for sid,url,kind,scope,limit,ex in new:
 fn='evidence/'+sid+'.txt';(O/fn).write_text(ex+'\n'+url+'\n'+limit+'\n');src(sid,'actual_requests.json',kind,scope,limit,fn,url)
# Every preserved published pattern keeps its own period, row locator, evidence class.
services=[]; unknown=[]
fields=['service_id','pair','origin','destination','week','week_start','week_end','covered_dates','valid_start','valid_end','days_mon0','carrier_operated','carrier_marketed','flight','departure_local','arrival_local','arr_day_offset','aircraft','status','evidence_class','source_id','source_locator','update_status','limitations']
for r in rows(P/'schedules.csv'):
 if r['status']!='PUBLISHED_PATTERN_ONLY':
  unknown.append(dict(pair=r['pair'],origin=r['origin'],destination=r['destination'],week=r['week'],field='rw_nonstop',value='UNKNOWN',field_status='no_update',source_id='P34-'+r['source_id'],reason=r['limitation']));continue
 z=dict.fromkeys(fields,'UNKNOWN');z.update(service_id='P34-'+r['schedule_id'],pair=r['pair'],origin=r['origin'],destination=r['destination'],week=r['week'],week_start=r['week_start'],week_end=r['week_end'],covered_dates=r['applicable_departures'],valid_start=r['valid_start'],valid_end=r['valid_end'],days_mon0=r['days'],carrier_operated=r['carrier'],flight=r['flight'],departure_local=r['dep_local'],arrival_local=r['arr_local'],arr_day_offset=r['arr_day_offset'],aircraft=r['aircraft'],status='PUBLISHED_PATTERN_ONLY',evidence_class='LABELLED_SECONDARY' if '_Z' in r['source_id'] else 'PRIMARY_AIRPORT',source_id='P34-'+r['source_id'],source_locator='schedules.csv:'+r['schedule_id']+'; '+r['direct_source_field'],update_status='no_update',limitations=r['limitation']+'; carrier label as published; marketed UNKNOWN; future execution not proven');services.append(z)
# One current AER competitor pattern only, not a new own-RW assertion.
for week,ws,we in [('ordinary','2026-11-16','2026-11-22'),('target','2027-02-01','2027-02-07')]:
 dates=[str(dt.date.fromisoformat(ws)+dt.timedelta(days=i)) for i in range(7)]
 z=dict.fromkeys(fields,'UNKNOWN');z.update(service_id='NEW-AER-'+week,pair='SVX-AER',origin='SVX',destination='AER',week=week,week_start=ws,week_end=we,covered_dates=';'.join(dates),valid_start='2026-11-12',valid_end='2027-03-27',days_mon0='0,1,2,3,4,5,6',carrier_operated='Россия',flight='FV-6122',departure_local='05:05',arrival_local='07:05',arr_day_offset='0',aircraft='B-737',status='PUBLISHED_PATTERN_ONLY',evidence_class='PRIMARY_AIRPORT',source_id='SVX-NEW',source_locator='turn4view1 L503-L504',update_status='new_observation',limitations='Year contextual winter2026/27; published carrier label; no reverse inference');services.append(z)
z=dict.fromkeys(fields,'UNKNOWN');z.update(service_id='WZ901-20260924',pair='ZIA-KGD',origin='ZIA',destination='KGD',week='historical',covered_dates='2026-09-24',valid_start='2026-09-24',valid_end='2026-09-24',days_mon0='3',carrier_operated='Red Wings (secondary attribution)',carrier_marketed='Red Wings (WZ label)',flight='WZ901',departure_local='08:10',arrival_local='10:00',arr_day_offset='0',aircraft='SU95 (Plane Finder secondary)',status='HISTORICAL_SECONDARY_ONLY',evidence_class='LABELLED_SECONDARY',source_id='WZ-AIRPORTIA;WZ-PF',source_locator='turn2view0 L31,L47 scheduled clocks; turn2view1 L15 aircraft/operator attribution',update_status='new_observation',limitations='Clocks are Airportia scheduled, not Plane Finder actual; do not combine actual clocks or infer regular days; no current resource');services.append(z)
write('canonical_services.csv',services)
# Pair-level field-specific references. Blank source means no admissible field observation.
pairs=[]; oldclass={r['pair']:r for r in rows(P/'classification.csv')}
for r in rows(C/'research_market/market_pairs.csv'):
 a,b=r['origin'],r['destination'];pair=a+'-'+b;cl=oldclass.get(pair); comp='PUBLISHED_NONSTOP_BOTH_WEEKS' if cl else 'UNKNOWN';cs=';'.join('P34-'+x for x in cl['competitor_source_ids'].split(';')) if cl else ''
 if pair=='SVX-AER':comp='PUBLISHED_NONSTOP_OUTBOUND_BOTH_WEEKS';cs='SVX-NEW'
 hist='UNKNOWN';hs='';histstatus='no_update'
 if pair=='DME-KGD':hist='RW_DIRECT_2025_PRIMARY';hs='RW-KGD2025;P08-MOW-KEEP'
 if pair=='ZIA-KGD':hist='RW_ZIA_KGD_20260924_SECONDARY';hs='WZ-AIRPORTIA;WZ-PF';histstatus='new_observation'
 row=dict(pair=pair,physical_origin=a,physical_destination=b,city_pool_id=('MOW' if a in ['DME','ZIA'] else a)+'-'+b,novelty_status='UNPROVED_CONDITIONAL_CLASS_A_B',novelty_field_status='no_update',novelty_source_id='P34-CLASS' if cl else '',rw_nonstop_nov='UNKNOWN',rw_nonstop_feb='UNKNOWN',rw_nonstop_field_status='no_update',rw_nonstop_source_id=('RW-SVX-NEW;SVX-NEW' if pair in ['SVX-KJA','SVX-AER'] else 'P34-'+cl['rw_source_ids'].split(';')[0] if cl else ''),competitor_status=comp,competitor_field_status='new_observation' if pair=='SVX-AER' else 'no_update',competitor_source_id=cs,historical_rw_status=hist,historical_field_status=histstatus,historical_source_id=hs,directed_daily_od='UNKNOWN',od_field_status='no_update',od_source_id='',net_fare='UNKNOWN',fare_field_status='no_update',fare_source_id='',time_preference='UNKNOWN',time_field_status='no_update',time_source_id='',covered_nov='2026-11-16/2026-11-22 per positive service only',covered_feb='2027-02-01/2027-02-07 per positive service only',calibration_update='no_update',notes='UNKNOWN does not overwrite prior known; not absent; no new demand calibration; field refs only')
 pairs.append(row)
 for week in ['ordinary','target']:
  for origin,dest in [(a,b),(b,a)]:
   unknown.append(dict(pair=pair,origin=origin,destination=dest,week=week,field='rw_nonstop',value='UNKNOWN',field_status='no_update',source_id=row['rw_nonstop_source_id'],reason='No explicit dated full own-operated nonstop confirmation; no absence inference'))
write('canonical_market_pairs.csv',pairs);write('unknown_fields.csv',unknown)
resolution=[]
def res(field,value,status,source,gate):resolution.append(dict(flight='WZ901',field=field,value=value,field_status=status,source_id=source,gate=gate))
res('physical_airport_20260924','ZIA; destination KGD','HISTORICAL_SECONDARY','WZ-AIRPORTIA;WZ-PF','No primary route-date confirmation; DME2025 is a separate product')
res('carrier_operated','Red Wings attributed by secondary trackers','SECONDARY_ONLY','WZ-PF;WZ-AIRPORTIA','Legal operating-carrier primary confirmation UNKNOWN')
res('carrier_marketed','Red Wings / WZ901 as labelled','SECONDARY_ONLY','WZ-AIRPORTIA','WZ code alone does not prove own tail')
res('aircraft_20260924','SU95 / RA-89122','SECONDARY_ONLY','WZ-PF','Not current free RRJ or a verified Moscow donor')
res('scheduled_clocks_20260924','08:10 ZIA / 10:00 KGD','SECONDARY_ONLY','WZ-AIRPORTIA','Plane Finder historical clocks differ; retain separate conventions; no derived block')
res('period_days','single observed date 2026-09-24 Thursday; recurring days UNKNOWN','HISTORICAL_ONLY','WZ-AIRPORTIA;WZ-PF','Do not infer weekly Thursday or extend into either target week')
res('service_type','UNKNOWN regular/charter on Sep24','UNKNOWN','WZ-PF','Generic current Charter label is not date-specific')
res('current_number_reuse','2026-11-12 LED-KGD; not Moscow','SECONDARY_ONLY','WZ-PF','Flight number not unique route/time key')
res('city_table','No table returned for city MOW query','NO_USABLE_TABLE','MOW-CITY','Could not read per-flight codes in original table; no physical airport inference from title')
res('DME_link','Official announcement dated2025-06-26; DME service from2025-07-25','HISTORICAL_PRIMARY','RW-KGD2025','No automatic continuation2026/27; no ZIA or WZ901 assignment')
res('ZIA0810_BUS','Official Tue/Fri/Sun ZIA-BUS08:10 winter2026/27','PRIMARY_PROGRAMME','RW-BUS;P08-MOW-HANDOFF','Different destination; mixed SSJ/Tu types, exact tail UNKNOWN')
res('final_gate','NOT_RESOLVED_CURRENT_MOSCOW_RRJ_BASELINE','GATE_NOT_RESOLVED','WZ-AIRPORTIA;WZ-PF;RW-KGD2025;MOW-CITY','Historical ZIA supported secondary; own current route-date/operator/type/period/days not primary resolved; initial Moscow RRJ/donor must be conditional with opportunity cost or paid positioning; B777/CXR/Tu history inadmissible')
write('WZ901_resolution.csv',resolution)
ad=[]
def admit(pair,field,sid,decision,scope,why):ad.append(dict(pair=pair,field=field,source_id=sid,decision=decision,covered_dates=scope,reason=why))
for r in services:admit(r['pair'],'published_service_fields',r['source_id'],'PRESERVE' if r['update_status']=='no_update' else 'ADMIT_WITH_LIMITS',r['covered_dates'],r['source_locator']+'; '+r['limitations'])
for r in pairs:
 admit(r['pair'],'calibration','', 'no_update','NONE','No new observed directed OD/netfare/time choice; prior scenarios stay scenarios')
 if r['pair'] not in ['DME-KGD','ZIA-KGD']:admit(r['pair'],'all_fields','P36-PRIOR','REJECT_CROSS_PAIR_WEB1','NONE','MOW-KGD snippet is irrelevant to this pair; UNKNOWN is not evidence')
admit('TJM-MRV','Yamal_frequency','P34-YAMAL;P34-TJM_Z;P34-MRV_TJM_Z','QUARANTINE_CONTRADICTION','primary excerpt ends2026-11-13; secondary claims2026-11-20/2027-02-05 and Sundays','Keep positive secondary claims labelled, do not treat as absent; not numerical schedule admission')
admit('SVX-KJA','rw_current_nonstop','P08-SVX;RW-SVX-NEW;SVX-NEW','no_update','NONE','P08-D05 is FV competitor signal; captured blocks and marketing not complete own RW register')
admit('SVX-AER','rw_current_nonstop','RW-SVX-NEW;SVX-NEW;RW-WINTER','no_update','NONE','Global selector/hub list not direct route proof; own RW UNKNOWN')
admit('MOW-KGD','current_own_resource','WZ-AIRPORTIA;WZ-PF;RW-KGD2025','GATE_NOT_RESOLVED','NONE','Historical evidence retained; primary current route-date/type/tail/operating period missing')
admit('ALL','observed_OD_netfare','P09','REJECT_AS_CALIBRATION','NONE','P09 canonical summaries model scenario journeys/revenue/headroom; full_delta_result UNKNOWN; not market observations')
write('source_admission.csv',ad);write('sources.csv',sources)
# Retain just the selected fresh P08 rows; do not export entire corpus.
selected=[]
for p,rs in pinned.items():
 for r in rs:
  if (r.get('origin'),r.get('destination'))==('SVX','KJA') or r.get('airport_pair') in ['DME:KGD','ZIA:KGD','SVX:ZIA'] or r.get('keep_item_id') in ['KEEP-ZIA-BUS','KEEP-DME-KGD-HISTORY']:
   selected.append(dict(pinned_path=p,record=r))
dump('evidence/P08_selected_records.json',selected)
# Read/hash exact excerpts from P34 supporting preservation, only the relevant lines.
for name in ['open2.txt','open3.txt','search1.txt']:
 text=(P/'evidence'/name).read_text(); lines=text.splitlines(); chosen=[]
 for i,line in enumerate(lines):
  if any(s in line for s in ['YC 177','YC 178','YC-177','A4 602','A4 613','UT 509','UT 510','23.10','13.11']):chosen.extend(lines[max(0,i-1):i+2])
 (O/'evidence'/('P34_selected_'+name)).write_text('\n'.join(chosen)+'\n')
