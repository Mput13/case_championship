import csv,json,hashlib
from pathlib import Path
B=Path.cwd(); O=B/'source_review'
def dump(name,rows):
    with (O/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def read(p):
    with (B/p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
# Read only completed, assigned inputs. Integrity manifest predates our output writes.
paths=[B/'TASKS.md',B/'remote_pins.json',B/'audit/common_contract.json',B/'audit/source_manifest.json',B/'audit/README.md']
for folder in ['ideas_calendar','ideas_commercial','ideas_portfolio','market_domestic','market_supplemental','coordinator/calendar_corrected']:
    paths.extend(sorted((B/folder).glob('*')))
manifest={str(p.relative_to(B)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}
(O/'input_integrity.json').write_text(json.dumps(manifest,indent=2))
U={
 'tbs':'https://flyredwings.com/en/press/news/red-wings-zapustit-dopolnitelnye-pryamye-rejsy-v-tbilisi-iz-ekaterinburga/',
 'tas':'https://flyredwings.com/en/press/news/red-wings-uvelichivaet-kolichestvo-rejsov-v-uzbekistan/',
 'cargo':'https://flyredwings.com/cargo/','agents':'https://flyredwings.com/agents/',
 'yandex':'https://rasp.yandex.ru/plane/samara--nizhniy-novgorod',
 'zia':'https://zia.aero/flights/seasonal-schedule/',
 'svx':'https://ar-svx.ru/about/news/dopolnitelnye-pryamye-reysy-iz-koltsovo-v-tbilisi-zapustit-r/',
 'yamal':'https://yamal.ru/passazhiram/schedule/TJM/MRV',
 'group':'https://flyredwings.com/upload/redwings/agents/%D0%98%D0%BD%D1%81%D1%82%D1%80%D1%83%D0%BA%D1%86%D0%B8%D1%8F%20%D0%BF%D0%BE%20%D0%BE%D1%84%D0%BE%D1%80%D0%BC%D0%BB%D0%B5%D0%BD%D0%B8%D1%8E%20%D0%B3%D1%80%D1%83%D0%BF%D0%BF%D0%BE%D0%B2%D1%8B%D1%85%20%D0%BF%D0%B5%D1%80%D0%B5%D0%B2%D0%BE%D0%B7%D0%BE%D0%BA.pdf'}
receipts=[]
def receipt(k,date,loc,method,fact,limit):receipts.append(dict(source_id=k,url=U[k],publication_date=date,checked_date='2026-11-12',access=method,content_locator=loc,extraction_paraphrase=fact,limits=limit))
receipt('tbs','2026-05-28','article body lines 111–117','primary substantive page','Summer 2026 daily SVX–TBS; from 28 June up to nine weekly, extra Fri 21:40 and Sun 20:30; returns Sat 01:10 and Sun 23:50.','Announcement, not realized operations/OD; no aircraft type or 2027 calendar.')
receipt('tas','2025-11-21','article body lines 111–115','primary substantive page','Carrier reports KUF–TAS twice weekly Mon/Fri begun 10 November 2025.','Historical carrier report; no target-period supply, passenger counts or yield.')
receipt('cargo','UNKNOWN','cargo page sections service, compartment parameters; lines 115–199','primary substantive page','Own-flight cargo service; quote form; baggage-compartment SSJ100 label 4200 kg and 20.15 m3.','Not residual payload after baggage or a shipment/order/price; no flight-specific variant dispatch approval.')
receipt('agents','UNKNOWN','agents page lines 111–119','primary substantive page','Agent channel covers cooperation, contracts and regular-flight blocks; links group instruction.','Selling RW inventory does not prove right/ability to buy and resell Yamal seats.')
receipt('yandex','UNKNOWN','schedule rows lines 84–95, calendar November2026/January2027','secondary substantive page','KUF–GOJ WZ5343 Mon/Fri through 26 March, except 27/30 November; exceptions 12:45–13:05; main 18:20–18:40; 30 December 13:35–14:05.','Year 2027 inferred from displayed calendar. No explicit start date; provisional listing, not carrier-primary or proof of actual operation. From price excluded.')
receipt('zia','last change 2026-07-27','page lines 49–54,178–198,226–228','primary substantive page','Page is departures from/arrivals to Zhukovsky; all points use Moscow time. Tbilisi rows include SU9 and T20 types.','These are ZIA–TBS rows, not SVX–TBS. Wrong city attribution in S07 is contradicted.')
receipt('svx','2026-05-29','article lines 72–77','primary substantive page','Koltsovo repeats daily summer and increase to nine weekly from 28 June 2026; extra days/times match carrier.','No type, donor tail, quantified OD or independent profit evidence; same announcement, not independent demand measurement.')
receipt('group','UNKNOWN','PDF p1 section1, lines2–9; actual link from agents page','primary substantive PDF','Group requests only on own regular RW flights; WZ marketing codeshare requests not accepted; tariff/payment/refund terms offered per request.','No partner-buy right and no public contract price. Approximate 2019 publication date not verified.')
receipt('yamal','UNKNOWN','exact cited URL open; site-targeted search','failed reread; prior packet attribution only','Direct open timed out; targeted search did not retrieve exact primary page. Previous package reports YC177 through 2026-11-13.','Not independently reaffirmed; no December/July or reverse-leg extrapolation. Two attempts then UNKNOWN.')
dump('source_receipts.csv',receipts)
A=[]
def add(id,ref,field,k,date,fact,v,use,why):A.append(dict(row_id=id,fileline=ref,field=field,source_url=U.get(k,k),source_date=date,checked_date='2026-11-12',taken_fact=fact,verdict=v,numeric_use=use,reason_and_impact=why))
add('R01','ideas_calendar/README.md:7; coordinator/calendar_corrected/sources.csv#S1','pair_alias','yandex','retrieved2026-11-12','Samara/Kurumoch→Nizhny/Strigino is KUF–GOJ, not SVX–GOJ','error','NO_WRONG_PAIR','Use coordinator canonical pair; old README is superseded.')
add('R02','coordinator/calendar_corrected/directed_schedule_rows.csv#S1','elapsed_minutes','yandex','retrieved2026-11-12','18:20 UTC+4→18:40 UTC+3 =80min','published_offer','HISTORICAL_LISTING_ONLY','Timezone normalization; no schedule conflict and no future dispatch blocktime claim.')
add('R03','coordinator/calendar_corrected/sources.csv#S1; directed_schedule_rows.csv#S1','weekday_and_exceptions','yandex','retrieved2026-11-12','Mon/Fri through26.03.2027 inferred year; exceptions27/30.11; extra30.12 row','published_offer','SECONDARY_LISTING_ONLY','Primary schedule and actual operation remain unknown; do not turn Mon/Fri into exception-free recurring flights.')
add('R04','market_domestic/README.md:9','December_period_exclusion','yandex','retrieved2026-11-12','26March2027 does not precede December2026','error','NO','Fix prose logic; broad secondary period includes December but is not independent primary target-date validation.')
add('R05','market_domestic/directed_services.csv#CEK-MRV;#MRV-CEK','competitor_gap','https://cekport.ru/ ; https://mrv.aero/','search2026-11-12','Targeted official-domain searches did not recover a dated directional calendar','unknown','NO','GAP_NOT_ABSENCE; competitor count and empty weekday cannot be set to zero. Retrieved aggregators excluded.')
add('R06','market_supplemental/sources.csv#S01;#S09','SVX_TBS_season_frequency','tbs','2026-05-28','From28June2026 up to9/week, daily+Fri/Sun additions; dated return times','published_offer','HISTORICAL_OFFER_ONLY','No2027 frequency or actual OD; confirms seasonal mechanism only.')
add('R07','ideas_portfolio/sources.csv#S1; season_type_evidence.csv#SVX-TBS-S26','publication_date','svx','2026-05-29','Article dated29May2026, not approxJune','error','METADATA_ONLY','Canonical date corrected; not a new market number.')
add('R08','market_supplemental/sources.csv#S07','origin_timezone_aircraft','zia','last change2026-07-27','Zhukovsky schedule in Moscow time, not SVX local rows','error','NO_FOR_SVX','Remove S07 as evidence for SVX–TBS; type remains UNKNOWN. Primary contradiction overrides title/primary flag.')
add('R09','market_supplemental/directed_services.csv#TBS-SVX','completed_fact_direction','https://flyredwings.com/flight-board/WZ/','prior packet2026-11-12','WZ1403 SVX→TBS fact copied into TBS→SVX row','error','NO_REVERSE_OBSERVATION','Reverse completed_fact UNKNOWN; forward claim only prior attribution, dynamic board not reread.')
add('R10','market_supplemental/sources.csv#S02; ideas_portfolio/season_type_evidence.csv#KUF-TAS-W25','KUF_TAS_frequency','tas','2025-11-21','Carrier says2/week Mon/Fri began10Nov2025','published_offer','HISTORICAL_REPORT_ONLY','No end date guaranteed by article; winter2025/26 context is not December2026/July2027 service.')
add('R11','market_supplemental/sources.csv#S08','TJM_MRV_dates','yamal','previous retrieval2026-11-12','Prior report ends13Nov2026; reread unsuccessful','unknown','NO_TARGET_USE','Retain attributed historical lead; no December, reverse schedule or absence inference.')
add('R12','ideas_commercial/sources.csv#S5; buyer_cargo_evidence.csv','cargo_maximum','cargo','undated; checked2026-11-12','4200kg/20.15m3 published compartment parameters','published_offer','TECHNICAL_LABEL_ONLY','Not remaining payload or cargo sales; confirm variant, baggage, fuel, volume and handling per sector.')
add('R13','ideas_commercial/ideas.csv#IC01; sources.csv#S6','partner_block_buy','agents','undated; checked2026-11-12','RW agent block inquiry channel exists','published_offer','NO_REVENUE_NUMBER','RW sells blocks does not prove partner purchase contract; q,price,resale rights and guarantee unknown.')
add('R14','market_supplemental/sources.csv#S06','group_PDF_URL_and_date','group','UNKNOWN','Actual PDF linked on agents page; own regular flights only; marketing codeshare excluded','error','METADATA_ONLY','Original malformed URL invalid; replace discovered href. 2019 approx not verified. Not partner-buy authorization.')
add('R15','ideas_commercial/ideas.csv#IC02','route_cargo_order','cargo','undated','Service exists; route/date shipment and net rate not supplied','unknown','THRESHOLD_ONLY','Cargo contribution unknown rather than zero; no invented residual tonnes.')
add('R16','ideas_commercial/ideas.csv#IC03','closed_cohort_contract','group','UNKNOWN','Request process exists; no named buyer/order/guarantee','unknown','THRESHOLD_ONLY','Contract concept remains hypothesis; guaranteed seats cannot be assumed.')
add('R17','market_domestic/comparable_fares.csv; market_supplemental/comparable_fares.csv','realized_net_yield','yandex','retrieved2026-11-12','No matching full quote receipts; from fares are offers, not realized net','unknown','NO','20kg inclusion alone cannot establish distribution, VAT, refunds or realized yield.')
add('R18','market_domestic/demand_evidence.csv; market_supplemental/demand_evidence.csv','observed_OD','LOCAL completed evidence tables','2026-11-12','No new observed directional monthly endpoint OD','unknown','THRESHOLD_ONLY','Seats×LF and airport totals prohibited as OD substitutes; direct evaluation remains permitted as conditional scenarios.')
p05='a63a047bc6559df8bac3b2dde5c6464c3c9e6a0b:context/35_full_programme_execution_20261112/P05/README.md'
add('R19','audit/common_contract.json#/scenarios; P05 README integration','OD_and_soft_choice',p05,'pinned2026-11-12','P05 annual/monthly OD and choice parameters explicitly scenario; uncalibrated','scenario','SCENARIO_ONLY','Not observed forecast; holdout carrier seasonality not endpointOD or booking-choice validation.')
add('R20','audit/common_contract.json:91-98;:412','net_VAT_distribution_paxcost',p05,'pinned2026-11-12','Net already deducts scenario VAT/distribution; legacy fare net and pax_cost may overlap','scenario','CONDITIONAL_ACCOUNTING_ONLY','Require cost-component bridge: exclude already-deducted distribution/acquiring from pax_cost; actual VAT/recoverability unknown. Do not infer current law.')
add('R21','audit/common_contract.json#/resource','E_and_S_resource','LOCAL audit/common_contract.json','2026-11-12','E0/E1/E2 conditional working slots; separate reserve/donor; S1 entriesAug/Nov2027 and delayedFeb/May2028','scenario','COMMON_SCENARIO_ONLY','No SJ beforeH22027 in any role; published fleet not free; same N(t), demand, costs/calendar for KEEP/all networks.')
add('R22','audit/common_contract.json#/critical_unknowns;#/ops','missing_cost_and_ops','LOCAL audit/common_contract.json','2026-11-12','Unknown costs, KEEP/cash and dispatch gates remain explicit','unknown','THRESHOLD_ONLY','Unknown not0; no generic2300km/+20% dispatch; geometry costscreen only; no500km/competitor exclusion.')
add('R23','audit/code_findings.csv#A05','technical_reuse','LOCAL context/30_defense_research_20261111/inputs/model_schedule/latest/data/raw/tochno_intercity/data_intercity_connectivity_162_v20260629.csv','snapshot reused2026-11-12','File hash matches user pin; venv imports numpy2.5.4/pandas3.1.1','observed','REPRODUCTION_ONLY','Technical blocker removable; no Git-primary provenance or new OD validation; no full baseline replay claimed.')
add('R24','audit/README.md; audit/common_contract.json#/engine_interface','P06_validation_scope','982f13d9b6c378ed9581125ecc5c40f17dade6a3','pinned2026-11-12','Synthetic mechanism/interface checks, not validated RW profit','scenario','MECHANISM_ONLY','No code/formula review in this scope; old +44/+503/+388 results cannot be combined.')
add('R25','ideas_calendar/ideas.csv#IC3; ideas_portfolio/ideas.csv#PORT01-05','mechanism_distinctness','LOCAL completed ideas packages','2026-11-12','Calendar/portfolio seasonal substitution overlaps; type swap is distinct resource lever','scenario','THRESHOLD_ONLY','Do not add duplicated mechanism effects. Commercial cargo distinct; cohort and block overlap inventory.')
add('R26','coordinator/calendar_corrected/sources.csv#S4; market_supplemental/sources.csv#S04','live_board_observations','https://flyredwings.com/flight-board/','prior packet2026-11-12','Prior board assertions not independently reread and no preserved board receipt inspected','unknown','NO_RECURRING_SCHEDULE','Keep attribution only; no future frequency, absence or reverse completed-flight evidence.')
dump('source_admission.csv',A)
F=[]
def finding(id,severity,refs,issue,action):F.append(dict(finding_id=id,severity=severity,admission_rows=refs,finding=issue,required_action=action,status='REVIEW_COMPLETE_ORIGINALS_UNCHANGED'))
finding('F01','material','R08','S07 maps ZIA timetable to SVX and Moscow time to local time','Quarantine S07 for SVX; corrected copies provided; aircraft UNKNOWN.')
finding('F02','material','R01;R02;R03','Old calendar alias and timezone errors; generic Mon/Fri lacks exceptions','Use coordinator canonical plus review exception annotation; never SVX alias.')
finding('F03','metadata','R04','Domestic README says March2027 precedes December2026','Correct downstream interpretation; secondary listing includes December, primary confirmation still absent.')
finding('F04','material','R09;R26','Forward board assertion copied into reverse row; evidence receipt not reviewed','Remove reverse completed claim; do not promote any board lead to season.')
finding('F05','metadata','R07;R14','Approximate airport date and malformed PDF URL','Use29May2026 and actual linked PDF; PDF date UNKNOWN.')
finding('F06','gate','R05;R11','Competitor coverage and Yamal target dates unknown','No absence inference; Yamal two attempts exhausted.')
finding('F07','gate','R06;R10','Historical seasonal supply is real published evidence','Admit historic offer only, not2027 economics or demand.')
finding('F08','gate','R12;R13;R14;R15;R16','Cargo service/block channel are real; transactions and capacity are not established','Separate own-operation from resale; payload/price/contracts require evidence.')
finding('F09','gate','R17;R18;R19;R20','No new OD/netyield; scenario choice and accounting overlap risk','Use explicit scenarios/thresholds and component-level net accounting.')
finding('F10','accepted_with_limits','R21;R22;R24','Common contract preserves shared resource and unknown gates','Retain same envelope; no global optimum or synthetic RW-profit claim.')
finding('F11','technical','R23','A05 missing dependency/raw statement is no longer a current technical blocker','Reuse matching old snapshot and existing venv; no new provenance claim.')
finding('F12','deduplicate','R25','Seasonal/day reallocations repeated across idea packages','Treat levers as alternatives or joint scenario; do not sum standalone deltas.')
dump('findings.csv',F)
# Minimal corrected copies; source files never overwritten.
s=read('market_supplemental/sources.csv')
for r in s:
 if r['source_id']=='S06':r.update(url=U['group'],publication_date='UNKNOWN',excerpt='Group requests only on own regular RW flights; marketing codeshare excluded',type='primary PDF read via actual agents-page link',what_proved='Own-flight group-request policy only')
 if r['source_id']=='S07':r.update(publication_date='last change2026-07-27',excerpt='ZIA departures/arrivals; ALL times Moscow; Tbilisi rows are ZIA-TBS',scope='ZIA summer2026; NOT SVX-TBS',what_proved='Historical ZIA schedule only',what_not_proved='SVX-TBS aircraft, times, frequencies or target periods')
 if r['source_id']=='S08':r['type']='primary URL; reread failed; previous package attribution only'
dump('canonical_supplemental_sources.csv',s)
for name,key in [('directed_services.csv','source_ids'),('route_evidence.csv','evidence_ids')]:
 rows=read('market_supplemental/'+name)
 for r in rows:
  if r['pair']=='SVX-TBS':r[key]=';'.join(v for v in r[key].split(';') if v!='S07')
  if name=='directed_services.csv' and r['direction']=='TBS-SVX':r['completed_fact']='UNKNOWN';r[key]='S01;S09'
  if name=='directed_services.csv' and r['direction']=='SVX-TBS':r['completed_fact']='UNKNOWN; prior package attributes WZ1403 forward board event, not independently reaffirmed'
 dump('canonical_supplemental_'+name,rows)
rows=read('ideas_portfolio/sources.csv');rows[0]['date']='2026-05-29';dump('canonical_portfolio_sources.csv',rows)
rows=read('coordinator/calendar_corrected/directed_schedule_rows.csv')
rows[0]['day_or_date']='Mon/Fri except2026-11-27/30; separate30Dec listing exists'
rows[0]['season']='through2027-03-26 (year from calendar; start UNKNOWN); secondary listing'
dump('canonical_calendar_directed_schedule_rows.csv',rows)
print('wrote',len(A),'admission rows and',len(F),'findings')
add('R27','ideas_portfolio/pairs.csv#SVX-BRU','endpoint_identity_and_domestic_scope','LOCAL ideas_portfolio/pairs.csv','2026-11-12','SVX-BRU labeled domestic without supporting endpoint evidence','unknown','NO_UNRESOLVED_ENDPOINT','No approved node mapping or route source supplied; quarantine identity pending confirmation, do not silently substitute BAX or other code.')
finding('F13','metadata_gate','R27','SVX-BRU domestic candidate has unresolved endpoint identity in supplied evidence','Retain candidate as unresolved; no automatic replacement airport or numerical route admission.')
dump('source_admission.csv',A);dump('findings.csv',F)
rows=read('ideas_portfolio/pairs.csv')
for r in rows:
 if r['pair_id']=='SVX-BRU':r.update(scope='UNKNOWN: endpoint identity/domestic classification unverified',screen_status='requires_endpoint_identity_check',decision='No numerical admission until endpoint mapping verified; candidate retained')
dump('canonical_portfolio_pairs.csv',rows)
