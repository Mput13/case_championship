import csv,json
from pathlib import Path

P=Path(__file__).resolve().parent
U='UNKNOWN'
sources=[]
def source(sid,url,kind,locator,quote,covered,proves,archive,pub=U):
 sources.append(dict(source_id=sid,url=url,source_kind=kind,publication_date=pub,retrieved_at='2026-11-12T16:10:28Z',covered_dates=covered,locator=locator,short_quote=quote,proves=proves,limitations='Published evidence only; not actual execution or booking inventory; absence of a row is not universal absence',excerpt_file='evidence/'+archive+'.txt'))
source('SVX_DEP','https://ar-svx.ru/schedule/','PRIMARY_AIRPORT','open3 L142–145,L190–192; open4 L219–227,L575–577','Красноярск; FV-6800; FV-6792. Иркутск; S7-6416. Владивосток; U6-571. Хабаровск; U6-173.','2026-10/2027-03 per individual row; year inferred from current winter context','Competitor flight patterns, times, types; no WZ in captured pair blocks','open4')
source('RW_SVX','https://flyredwings.com/directions/ekaterinburg/','PRIMARY_AIRLINE','open1 L130–184','Направления из Екатеринбурга','Undated current marketing page','Own RW destination marketing checked separately; no dated complete RW scope','open1')
source('TJM_FAIL','https://tjm.aero/passazhiram/raspisanie-reysov/','PRIMARY_ATTEMPT_FAILED','open1 turn2view2','URL https://tjm.aero/passazhiram/raspisanie-reysov/ is not accessible via this tool.','NONE','Failure only; no schedule facts','open1')
source('CEK_FAIL','https://cekport.ru/schedule/','PRIMARY_ATTEMPT_FAILED','open1 turn2view3','Failed to fetch https://cekport.ru/schedule/: (404) Not Found','NONE','Failure only','open1')
source('A4_FAIL','https://azimuth.ru/ru/flights/schedule','PRIMARY_ATTEMPT_FAILED','open1 turn2view4','URL https://azimuth.ru/ru/flights/schedule is not accessible via this tool.','NONE','Failure only','open1')
source('KHV','https://khvaero.ru/passengers/schedule/','PRIMARY_AIRPORT','search3 L284','ЕКАТЕРИНБУРГ | 14.11.2026 - 28.03.2027 | U6 | У6-173 | ежедневно | 13:00 | 17:50','2026-11-14/2027-03-28','Arrival from SVX; conflicts in clock with SVX departure table; do not combine clocks','search3')
source('SVX_ARR','https://ar-svx.ru/schedule/?type=arr','PRIMARY_AIRPORT','open3 L150–153,L199–201; open4 L229–238,L608–610','Красноярск; FV-6791; FV-6799. Иркутск; S7-6415. Владивосток; U6-572. Хабаровск; U6-174.','2026-10/2027-03 per row; year contextual','Reverse competitor flights; no WZ in captured pair blocks','open4')
source('YAMAL','https://yamal.ru/passazhiram/schedule/TJM/MRV','PRIMARY_SEARCH_EXCERPT_OPEN_FAILED','search1 turn0search0; open2 turn4view1','YC-177 | 23.10 - 13.11','2026-10-23/2026-11-13 contextual','Historical/nearby Yamal only; open failed TimeoutError; cannot extend to ordinary week','search1')
source('CEK_Z','https://zbordirect.com/ru/tools/schedule/CEK/MRV','MARK_SECONDARY','open2 L5–12','11/11/26 06:55 – 08:25 3h 30m Azimuth A4 6024','2026-11-11/2027-03-26 contextual year on endpoint','Dated competitor nonstop pattern; not registry of all operators','open2')
source('TJM_Z','https://zbordirect.com/ru/tools/schedule/TJM/MRV','MARK_SECONDARY','open2 L5–11','A4 6134; четверг, воскресенье по 25.03; YC 177; UT 509','2026-11/2027-03 per flight','Dated competitor nonstop pattern incl later Yamal; Yamal conflicts with primary excerpt','open2')
source('RW_TJM','https://flyredwings.com/directions/tyumen/','PRIMARY_AIRLINE','open2 L130–141','Направления из Тюмени; Самара; Махачкала','Undated current marketing','RW own marketing inspected; not full dated schedule','open2')
source('RW_CEK','https://flyredwings.com/directions/chelyabinsk/','PRIMARY_AIRLINE','open2 L130–157','Направления из Челябинска','Undated current marketing','RW own marketing inspected; no inference of zero RW business','open2')
source('MRV_EMPTY','https://mvairport.ru/schedule/','PRIMARY_EMPTY','open3 turn5view5','This page has no readable lines.','NONE','No usable dated primary schedule','open3')
source('MRV_CEK_Z','https://zbordirect.com/ru/tools/schedule/MRV/CEK','MARK_SECONDARY','open3 L5–12','11/11/26 00:35 – 05:55 3h 20m Azimuth A4 6023','2026-11-11/2027-03-26 contextual year','Reverse competitor pattern only','open3')
source('MRV_TJM_Z','https://zbordirect.com/ru/tools/schedule/MRV/TJM','MARK_SECONDARY','open3 L5–11','A4 6133; UT 510; YC 178','2026-11/2027-03 per flight','Reverse competitor patterns; Yamal future claim secondary only','open3')
source('FC_KJA','https://www.flightconnections.com/flights-from-svx-to-kja','MARK_SECONDARY','open3 L7–11,L62–90; open4 no Red Wings match','Last updated on: 09-17-2026','2026-09-17; not target weeks','Aeroflot marketing route context only; not current operator register or RW history proof','open3','2026-09-17')

def write(name,rows):
 assert rows
 with (P/name).open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
for row in sources:
 if row['source_id'] in ['SVX_DEP','SVX_ARR']: row['excerpt_file']='evidence/'+row['source_id']+'.txt'
write('sources.csv',sources)
pairs=['TJM-MRV','CEK-MRV','SVX-KJA','SVX-IKT','SVX-VVO','SVX-KHV']
classrows=[]
for pair in pairs:
 rw={'TJM-MRV':'RW_TJM','CEK-MRV':'RW_CEK'}.get(pair,'RW_SVX')
 comp={'TJM-MRV':'TJM_Z;MRV_TJM_Z','CEK-MRV':'CEK_Z;MRV_CEK_Z'}.get(pair,'SVX_DEP;SVX_ARR')
 classrows.append(dict(pair=pair,ordinary_start='2026-11-16',ordinary_end='2026-11-22',ordinary_class='COMPETITOR_NONSTOP_RW_NOT_CONFIRMED',target_start='2027-02-01',target_end='2027-02-07',target_class='COMPETITOR_NONSTOP_RW_NOT_CONFIRMED',competitor_source_ids=comp+(';KHV' if pair=='SVX-KHV' else ''),rw_status=U,rw_source_ids=rw+(';SVX_DEP;SVX_ARR' if pair.startswith('SVX') else ''),rw_scope='Own marketing checked; airport pair blocks checked for SVX; no explicit complete dated RW register obtained',newness='UNRESOLVED_RELAUNCH_HISTORY' if pair=='SVX-KJA' else 'UNRESOLVED',history='Historical RW claim not restored to a primary locator; RELAUNCH conditional on history confirmation' if pair=='SVX-KJA' else U,basis='Competitor published nonstop; no admission of RW absence. Future schedule is a published offer, not completed execution',target_limit='Only Tue/Sat KJA flights extend through target week; KHV forward target corroborated by arrival table with clock conflict' if pair in ['SVX-KJA','SVX-KHV'] else 'Per-flight published validity; primary or marked secondary; no full operator registry'))
write('classification.csv',classrows)

# Each row is one published pattern; counts below are counts of its applicable departures,
# never total market capacity or observed execution. Times are local. Target dates are analyst scope.
patterns=[]
def pat(pair,o,d,carrier,flight,days,start,end,dep,arr,offset,typ,sid,loc,lim=''):
 patterns.append(dict(pair=pair,origin=o,destination=d,carrier=carrier,flight=flight,days=days,valid_start=start,valid_end=end,dep_local=dep,arr_local=arr,arr_day_offset=offset,aircraft=typ,source_id=sid,direct_source_field=loc,limitation=lim))
for o,d,flight,dep,arr,days,sid in [('TJM','MRV','A4-6134','07:00','08:55','3,6','TJM_Z'),('MRV','TJM','A4-6133','00:20','06:00','3,6','MRV_TJM_Z'),('TJM','MRV','UT-509','17:05','18:50','6','TJM_Z'),('MRV','TJM','UT-510','10:40','16:05','6','MRV_TJM_Z')]:
 pat('TJM-MRV',o,d,'Азимут' if flight.startswith('A4') else 'Utair',flight,days,('2026-11-12' if o=='TJM' else '2026-11-08') if flight.startswith('A4') else ('2026-11-15' if o=='TJM' else '2026-11-08'),'2027-03-25' if flight.startswith('A4') else '2027-03-21',dep,arr,'0','RRJ-95' if flight.startswith('A4') else 'B737-800',sid,'L9','MARK_SECONDARY; not comparable fare; year contextual at validity end')
for o,d,f,dep,arr,sid in [('CEK','MRV','A4-6024','06:55','08:25','CEK_Z'),('MRV','CEK','A4-6023','00:35','05:55','MRV_CEK_Z')]:
 pat('CEK-MRV',o,d,'Азимут',f,'2,4,5','2026-11-11','2027-03-26',dep,arr,'0','RRJ-95',sid,'L9','MARK_SECONDARY; excludes 2027-01-01; no overlap with study weeks')
for o,d,f,dep,arr,sid in [('SVX','IKT','S7-6416','15:15','22:20','SVX_DEP'),('IKT','SVX','S7-6415','12:40','14:15','SVX_ARR')]:
 pat('SVX-IKT',o,d,'S7',f,'0,3,5','2026-10-26','2027-03-27',dep,arr,'0','B737',sid,'open3 L191' if o=='SVX' else 'open3 L200')
for o,d,f,dep,arr,days,start,end,offset in [('SVX','VVO','U6-571','18:15','06:20','4','2026-10-30','2027-03-26','1'),('SVX','VVO','U6-571','19:10','07:15','0,1,2,3,5,6','2026-10-26','2027-03-21','1'),('VVO','SVX','U6-572','07:20','10:05','5','2026-10-31','2027-03-27','0'),('VVO','SVX','U6-572','08:20','11:05','0,1,2,3,4,6','2026-10-27','2027-03-22','0')]:
 pat('SVX-VVO',o,d,'Уральские авиалинии',f,days,start,end,dep,arr,offset,'A320NEO','SVX_DEP' if o=='SVX' else 'SVX_ARR','open3 L143–144' if o=='SVX' else 'open3 L151–152')
pat('SVX-KHV','SVX','KHV','Уральские авиалинии','U6-173','0,1,2,3,4,5,6','2026-10-26','2026-12-27','18:55','06:10','1','A320','SVX_DEP','open4 L576','Clock conflicts with KHV arrival table; no extrapolation beyond December')
pat('SVX-KHV','KHV','SVX','Уральские авиалинии','U6-174','0,1,2,3,4,5,6','2026-10-27','2026-12-28','07:50','09:55','0','A320NEO','SVX_ARR','open4 L609','No extrapolation beyond December')
# Arrival table explicitly labels origin SVX. Preserve conflict rather than synthesizing clocks.
pat('SVX-KHV','SVX','KHV','Уральские авиалинии','U6-173','0,1,2,3,4,5,6','2026-11-14','2027-03-28',U,U,U,U,'KHV','search3 L284','Arrival table clock 13:00/17:50 conflicts; clocks withheld; duplicate evidence not additive frequency')
for o,d,flight,days,start,end,dep,arr,off,typ,loc in [
 ('SVX','KJA','FV-6800','1','2026-10-27','2027-03-23','22:25','03:30','1','RRJ-95B','L220'),
 ('SVX','KJA','FV-6792','4','2026-11-13','2026-12-18','11:40','16:30','0','B737','L221'),
 ('SVX','KJA','FV-6792','6','2026-11-15','2026-12-20','12:05','16:55','0','A319','L222'),
 ('SVX','KJA','FV-6792','5','2026-11-14','2027-03-20','12:10','17:00','0','B737','L223'),
 ('SVX','KJA','FV-6792','2','2026-11-18','2026-12-16','12:10','17:05','0','B737','L224'),
 ('SVX','KJA','FV-6792','3','2026-11-19','2026-12-24','12:10','17:05','0','B737','L225'),
 ('SVX','KJA','FV-6792','0','2026-10-26','2026-12-21','13:40','18:35','0','B737','L226'),
 ('KJA','SVX','FV-6791','4','2026-11-20','2026-12-18','09:30','10:45','0','B737','L231'),
 ('KJA','SVX','FV-6791','6','2026-11-15','2026-12-20','10:00','11:10','0','B737','L232'),
 ('KJA','SVX','FV-6791','5','2026-11-14','2027-03-20','10:05','11:15','0','B737','L233'),
 ('KJA','SVX','FV-6791','3','2026-11-19','2026-12-24','10:05','11:15','0','B737','L234'),
 ('KJA','SVX','FV-6791','2','2026-11-18','2026-12-16','10:10','11:15','0','B737','L235'),
 ('KJA','SVX','FV-6791','0','2026-10-26','2026-12-21','11:30','12:45','0','B737','L236'),
 ('KJA','SVX','FV-6799','1','2026-10-27','2027-03-23','19:50','21:10','0','RRJ-95LR','L237')]:
 pat('SVX-KJA',o,d,'Россия',flight,days,start,end,dep,arr,off,typ,'SVX_DEP' if o=='SVX' else 'SVX_ARR','open4 '+loc,'Operator Россия per airport; do not relabel Aeroflot operator; year inferred winter context')
from datetime import date,timedelta
weeks=[('ordinary','2026-11-16','2026-11-22'),('target','2027-02-01','2027-02-07')]
schedule=[]
for p in patterns:
 for week,begin,end in weeks:
  dates=[date.fromisoformat(begin)+timedelta(days=i) for i in range(7)]
  selected=[x.isoformat() for x in dates if p['valid_start']<=x.isoformat()<=p['valid_end'] and x.weekday() in map(int,p['days'].split(','))]
  if selected:
   schedule.append(dict(schedule_id='SCH%03d'%(len(schedule)+1),week=week,week_start=begin,week_end=end,**p,applicable_departures=';'.join(selected),count_published_pattern=len(selected),count_source_field=p['source_id']+':'+p['direct_source_field']+' days+validity; calendar-derived',status='PUBLISHED_PATTERN_ONLY'))
for pair in pairs:
 a,b=pair.split('-')
 for o,d in [(a,b),(b,a)]:
  for week,begin,end in weeks:
   schedule.append(dict(schedule_id='SCH%03d'%(len(schedule)+1),week=week,week_start=begin,week_end=end,pair=pair,origin=o,destination=d,carrier='Red Wings',flight=U,days=U,valid_start=U,valid_end=U,dep_local=U,arr_local=U,arr_day_offset=U,aircraft=U,source_id={'TJM-MRV':'RW_TJM','CEK-MRV':'RW_CEK'}.get(pair,'RW_SVX'),direct_source_field='destination marketing body; incomplete dates',limitation='No dated RW nonstop confirmation; not a zero frequency',applicable_departures=U,count_published_pattern=U,count_source_field=U,status=U))
write('schedules.csv',schedule)
fares=[];demand=[]
for pair in pairs:
 a,b=pair.split('-')
 for o,d in [(a,b),(b,a)]:
  for week,start,end in weeks:
   fares.append(dict(pair=pair,origin=o,destination=d,week=week,scope_start=start,scope_end=end,requested_basket='economy; 1 adult; one-way; 20kg checked; all fees',gross_rub=U,net_rub=U,quote_timestamp=U,quote_source_id=U,direct_source_field=U,alternative='Competitor nonstop: schedules.csv; dated rail/transfer basket UNKNOWN',status=U,reason='No complete dated basket with baggage and fees obtained; marketing from/month minimum excluded'))
  demand.append(dict(pair=pair,origin=o,destination=d,ordinary_endpoint_journeys=U,target_endpoint_journeys=U,demand_source_id=U,direct_source_field=U,who_hypothesis='Health/leisure travelers and visiting friends/family' if b=='MRV' and d=='MRV' else 'Returning residents, visiting friends/family, individual business travelers',why_hypothesis='Convenient nonstop timing could attract travelers; no directed purpose or OD measurement obtained',seasonality=U,rail_or_transfer_documented=U,evidence_status='HYPOTHESIS_ONLY; not observed directed demand',incremental_rw=U,limitation='No sector/population to trips; no seats times LF; old RW marketing customers not automatically new'))
write('fares_and_alternatives.csv',fares);write('demand_reasons.csv',demand)

