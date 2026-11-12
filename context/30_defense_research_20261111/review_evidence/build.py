from pathlib import Path
import csv,json,hashlib
P=Path('/home/mputi/.t3/scratch/red-wings-team-update-20261109-b45f8804/context/30_defense_research_20261111')
O=P/'review_evidence'
def write(name,fields,rows):
 with (O/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
files=[P/d/f for d,fs in [('history',['history.md','events.csv','sources.csv','validation.json']),('buyers',['buyers.md','opportunities.csv','sources.csv','validation.json'])] for f in fs]
(O/'input_hashes.json').write_text(json.dumps({str(f.relative_to(P)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},indent=2))
with (P/'buyers/opportunities.csv').open() as f: raw=list(csv.reader(f))
fields=raw[0]+['evidence_status','passenger_volume_status','source_ids','legal_buyer_primary_status','beneficiary','beneficiary_status','endpoint_status','primary_document_url']
rows=[]
for a in raw[1:]:
 if a[0]=='BUY-02': a=a[:15]+[a[15]+','+a[16],a[17]]
 if a[0] in ('BUY-03','BUY-04'): a=a[:15]+a[16:]
 assert len(a)==17
 d=dict(zip(raw[0],a));d.update(evidence_status='UNKNOWN',passenger_volume_status='UNKNOWN',source_ids='',legal_buyer_primary_status='UNKNOWN',beneficiary='',beneficiary_status='UNKNOWN',endpoint_status='UNKNOWN',primary_document_url='')
 for k in ('amount_unit','people_or_rotations','convertible_trips'): d[k]=''
 if d['id'] in ('BUY-02','BUY-03','BUY-04'):
  d.update(buyer_or_intermediary='',endpoint_evidence='',purpose='',fit_to_oms_offer='',result='No route-specific buyer evidence located in original bounded search; demand remains UNKNOWN')
 rows.append(d)
u='https://zakupki.kontur.ru/RQ0302100024826000396'
eis='https://zakupki.gov.ru/epz/pricereq/card/common-info.html?reestrNumber=0302100024826000396'
rows[0].update(buyer_or_intermediary='Отделение Фонда пенсионного и социального страхования Российской Федерации по Республике Бурятия; ИНН 0323048828 (reported_secondary)',endpoint_evidence='Ulan-Ude–Omsk and Omsk–Ulan-Ude city pairs reproduced by aggregator; primary attachment unavailable',period_season='2026; reported service deadline 2026-12-01; actual travel dates UNKNOWN',procurement_contract_status='reported_secondary: price-information request published 2026-09-18; price collection 2026-09-18 to 2026-09-21; award and execution UNKNOWN',fit_to_oms_offer='City pair matches OMS-UUD; airport codes, direct service, schedule and RW supplier fit UNKNOWN',unknowns='Primary documents; legal buyer primary confirmation; awardee; passenger count; fare; actual travel dates; airport endpoints; direct/connecting itinerary; recurrence; RW allocation',result='Route-specific price-request lead only; not a signed purchase or realized demand',evidence_status='reported_secondary',source_ids='SRC-01',beneficiary='SVO participants and accompanying persons travelling for rehabilitation/sanatorium treatment; individual beneficiaries and treatment institution UNKNOWN',beneficiary_status='reported_secondary',endpoint_status='reported_secondary',primary_document_url=eis)
rows[4].update(buyer_or_intermediary='ФГБУЗ «Западно-Сибирский медицинский центр Федерального медико-биологического агентства»; ИНН 5502018378 (reported_secondary)',amount_unit='499000 RUB total mixed air/rail contract; no OD allocation',evidence_status='reported_secondary',source_ids='SRC-02',beneficiary='Employees of the named institution on business travel (reported_secondary)',beneficiary_status='reported_secondary',result='Mixed-mode contract only; OMS-MOW is selected candidate pair, not evidenced contract endpoint')
write('buyers_opportunities_corrected.csv',fields,rows)
with (P/'buyers/sources.csv').open() as f: raw=list(csv.reader(f))
sources=[]
for a in raw[1:]:
 if len(a)>10:a=a[:9]+[','.join(a[9:])]
 d=dict(zip(raw[0],a));d.update(evidence_status='reported_secondary',review_status='carried_forward_not_reopened',numeric_input_effect='No passenger input admitted')
 sources.append(d)
sources[0].update(publication_or_contract_date='2026-09-18',short_evidence='Buryatia social fund price request; Ulan-Ude–Omsk and return among five city pairs; rehabilitation travel; no awarded volume',reliability='Secondary aggregator; EIS inaccessible after two attempts',what_changes='Identifies reported legal buyer and price-request stage; city-pair lead only',limits='Award, passengers, actual flights, recurrence, primary legal buyer confirmation and airport endpoints UNKNOWN',review_status='opened_2026-11-11')
sources[1].update(short_evidence='ZSMC FMBA staff travel; 499000 RUB mixed air/rail contract reported; no city-pair allocation',review_status='opened_2026-11-11')
sources[3].update(publication_or_contract_date='',period='',short_evidence='ORENAIR-branded undated page describes group requests; footer 2009–2015 and unrelated betting links',reliability='Current publisher control and airline-primary provenance UNKNOWN',what_changes='Exclude from evidence of a current airline offer or OMS program',limits='Branding/domain availability does not establish current airline control; no OMS program or demand evidenced',evidence_status='UNKNOWN',review_status='opened_excluded_as_current_primary')
sources[4]['what_changes']='Product taxonomy only; no buyer or actual OMS program demonstrated'
write('buyers_sources_corrected.csv',raw[0]+['evidence_status','review_status','numeric_input_effect'],sources)
rw='https://flyredwings.com/press/news/red-wings-stanet-bazovoj-aviakompaniej-omskogo-aeroporta/'
mk='https://omsk.mk.ru/social/2022/06/16/11-napravleniy-pereletov-ne-okhvatyvaet-bazovyy-omskiy-aviaperevozchik.html'
ngs='https://ngs55.ru/text/business/2022/09/14/71653223/'
ram='https://travel.rambler.ru/news/49328873-aviakompaniya-red-wings-perestala-bazirovatsya-v-omske-i-sokratila-reysy/'
favt='https://special.favt.gov.ru/novosti-novosti/?id=9209'
F=[]
def finding(id,file,line,row,status,evidence,url,date,impact):
 F.append(dict(finding_id=id,orig_file=file,orig_line=line,orig_row=row,status=status,evidence=evidence,url=url,source_date=date,checked_date='2026-11-11',numeric_input_effect=impact))
finding('R01','buyers/opportunities.csv',2,'BUY-01','correct_reported_secondary','Aggregator names Buryatia social fund, INN 0323048828; replace speculative Omsk medical center. EIS timeout then SSL verification failure.',u,'2026-09-18','No passenger number; legal identity correction only')
finding('R02','buyers/buyers.md',9,'BUY-01','qualify_reported_secondary','Price-information request, not evidence of an awarded one-off purchase. City pair Ulan-Ude–Omsk and return; participants/accompanying persons; airports/direct routing UNKNOWN.',u,'2026-09-18','No quantified passenger input; 1 service unit must not become 1 passenger')
finding('R03','buyers/opportunities.csv',3,'BUY-02','csv_repair','18 columns vs 17 header: unquoted comma splits unknowns. Rejoin cells 16 and 17; retain final result.','local:buyers/opportunities.csv','','Parsing only; no new demand')
finding('R04','buyers/opportunities.csv',4,'BUY-03; BUY-04 line 5','csv_repair','Both rows have 18 columns vs 17; redundant Unknown after convertible_trips shifts unknowns/result. Remove redundant placeholder.','local:buyers/opportunities.csv','','Parsing only; unknown volumes remain blank')
finding('R05','buyers/sources.csv',2,'SRC-01; SRC-05 line 6','csv_repair','14 and 12 columns vs header 10; trailing limits contain unquoted commas. Join overflow into limits.','local:buyers/sources.csv','','No numeric effect')
finding('R06','buyers/opportunities.csv',2,'BUY-01; BUY-05 line 6; validation.json line 9','correct_missing_semantics','0 quantified / 0 attributable cannot be numeric zero demand. All five people_or_rotations and convertible_trips blank with passenger_volume_status UNKNOWN.','local:buyers/validation.json','','Null semantics corrected; no zero passenger estimate and no added passengers')
finding('R07','buyers/opportunities.csv',6,'BUY-05','retain_reported_secondary','499000 RUB total air/rail contract; ZSMC FMBA customer; no MOW allocation in listing.','https://zakupki.kontur.ru/32616272735','2026-08-07; contract 2026-08-12','499000 retained as documentary total only; no route revenue/passenger input')
finding('R08','buyers/sources.csv',5,'SRC-04','exclude_current_primary','Undated branded content, 2009–2015 footer, unrelated betting links; current airline control not authenticated. Remove current service page / airline primary label.','https://www.orenair.ru/services/group_travel/','','No numeric effect; no OMS program established')
finding('R09','buyers/sources.csv',6,'SRC-05','retain_taxonomy_only','Intermediary service description is not an actual buyer program; not reopened in this round.','https://aviacenter.ru/partnering/groups','','No numeric input')
finding('R10','history/history.md',5,'H01/H02; events.csv lines 2-3','accept_with_date_correction','Release dated 2021-12-06 announces first SSJ and January start; existing routes stated for current season, not verified through January.',rw,'2021-12-06','No realized aircraft count; date label H02 becomes as of 2021-12-06')
finding('R11','history/history.md',11,'H03; events.csv line 4','qualify_attribution','June article attributes contraction to international connectivity task; 41 May flights reported completed; 32 June planned. Media relay, not directly inspected airline statement.',mk,'2022-06-16','Retain reported 41 / planned 32 only; no execution or passenger forecast')
finding('R12','history/events.csv',6,'H05/H06; history.md line 7','accept_reported_secondary','Contemporary reporting supports RW initiative and effective 2022-08-01; cooperation agreement distinct and retained. Native termination document/cause UNKNOWN.',ngs+' ; '+ram,'2022-09-14','No numeric model change; does not prove demand adequacy or insufficiency')
finding('R13','history/events.csv',5,'H04; sources.csv line 4','primary_recheck_UNKNOWN','Original reports weekly 43 paired flights as subsidy plan. Page timeout then HTTP403; exact row not independently reread. NVK should be NOZ in project IATA schema.',favt,'2022 (original metadata)','No current numeric input; retain 1/week and 43 pairs only as original reported plan pending primary verification')
finding('R14','history/events.csv',8,'H07; sources.csv line 6','upgrade_reported_secondary','NGS opened: airport says August RRJ-95 maintenance contract; Rambler reproduction reports work from September 1. Actual contract not inspected.',ngs+' ; '+ram,'2022-09-14','No numeric input; maintenance is not basing')
finding('R15','history/history.md',21,'UNKNOWN aircraft count','clarify','Replace after first SSJ wording with actual permanently based fleet count and arrival/departure dates UNKNOWN; first aircraft was planned, not confirmed delivered by this release.',rw,'2021-12-06','No fleet count admitted')
write('findings.csv',list(F[0]),F)
H=[dict(orig_file='history/events.csv',orig_line=3,orig_row='H02',field='date_or_period',original='2021-12 to 2022-01',corrected='as of 2021-12-06; current season per release',status='verified_primary_snapshot',url=rw,source_date='2021-12-06',numeric_input_effect='No numeric model change; removes unsupported January coverage'),dict(orig_file='history/events.csv',orig_line=5,orig_row='H04',field='route_or_scope',original='OMS-NVK',corrected='OMS-NOZ (Omsk–Novokuznetsk; project network code)',status='identifier_correction',url='user-provided current network snapshot; original event city name',source_date='',numeric_input_effect='Route key correction only; no demand admitted')]
write('history_corrections.csv',list(H[0]),H)
