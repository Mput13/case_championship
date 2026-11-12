"""Metadata, evidence qualification and source-to-claim links for the P03 tranche."""
import csv, hashlib, json
from pathlib import Path
from collect_sources import URLS, PLAN, AUTHOR, FIVE
P=Path(__file__).resolve().parent
def dump(name,obj):(P/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def csvout(name,rows):
 with (P/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

receipts=[]
for f in ['fetch_receipts.json','supplemental_fetch_receipts.json','fap145_fetch_receipts.json']:
 receipts+=json.loads((P/f).read_text())
byid={}
for r in receipts:
 if r['source_id'] not in byid or r['status']!='fetch_failed':byid[r['source_id']]=r
source_rows=[]
for sid,r in byid.items():
 file=r.get('saved_path','');status=r['status'];coverage='Public source body captured; only claims qualified below may be used.'
 if file.endswith('.txt') and (P/file).stat().st_size<100:status='empty_body_not_evidence';coverage='No usable page body. Do not infer source content.'
 if sid in ['YAK-SJ100','UAC-SSJ','TU214-MOD']:
  file='native_search_receipts.json';status='native_search_primary_extract_only_direct_TLS_failed';coverage='Manufacturer primary page read through native search; direct HTTPS verification failed. Marketing description, not AFM.'
 if sid=='FAVT-AOC':coverage='Registry explicitly dated2025-09-04; current fleet/base availability not established.'
 if sid=='TU214-ANNOUNCEMENT':coverage='Secondary Interfax direct statement by named UAC head: announced batch/start, not annual RW handover calendar.'
 if sid=='LAW381-REGISTERED-PDF':coverage='Registered primary document scan; official publication identity captured separately. Visually checked pages in law381_visual_check.json.'
 if sid=='LAW381-TEXT-MIRROR':coverage='Secondary text mirror for navigation; operative points crosschecked against registered scan.'
 source_rows.append(dict(source_id=sid,url=r['url'],source_role=r['source_role'],retrieved_at=r['retrieved_at'],as_of='source-specific; fleet2026undated, AOC2025dated, MROhistorical, legal validity explicit',status=status,local_path=file,sha256=hashlib.sha256((P/file).read_bytes()).hexdigest() if file else '',coverage=coverage,lower='UNKNOWN',upper='UNKNOWN',unit='document',error=r.get('error','')))
for sid,path,commit,coverage in [
 ('PLAN','context/34_full_programme_plan_20261112/common_spec.json',PLAN,'Accepted user steering overrides prepared/not-launched labels; plan inputs pinned.'),
 ('PLAN_VARIANTS','context/34_full_programme_plan_20261112/variant_research_plan.json',PLAN,'Legacy hypotheses are lineage and endpoint inventory, not mandatory unchanged experiments.'),
 ('CASE_H2_RULE','context/34_full_programme_plan_20261112/common_spec.json',PLAN,'Current user/case boundary for SJ only; not delivery evidence.'),
 ('AUTHOR_AIRPORT_TECH','data/manual/airport_tech.csv',AUTHOR,'Inherited type-operation claims; fractions0.5 and rw_support0 are not converted to certified/current MRO/base facts.'),
 ('ARCHIVE_NETWORK_ROUTES','data/processed/network_routes.csv',AUTHOR,'Archived frequencies and rounded distances; numerical resource threshold diagnostics only, not accepted programme.'),
 ('FIVE_CITY_RESEARCH','context/33_five_city_reassessment_20261112/cities/TJM/sources.csv',FIVE,'Exact pinned research and sources for five-city reuse; see full input manifest.')]:
 local='inputs/'+commit[:8]+'/'+path
 source_rows.append(dict(source_id=sid,url='git:'+commit+':'+path,source_role='pinned_input',retrieved_at='2026-11-12',as_of=commit,status='pinned_blob',local_path=local,sha256=hashlib.sha256((P/local).read_bytes()).hexdigest(),coverage=coverage,lower='UNKNOWN',upper='UNKNOWN',unit='versioned input',error=''))
csvout('sources.csv',source_rows)
dump('native_search_claims.json',[
 dict(source_id='YAK-SJ100',url='https://yakovlev.ru/products/sj-100/',access='native web search primary extract; direct TLS failure retained',observed_fields={'engine':'2xPD8','manufacturer_max_seats':103,'advertised_range_km':3530,'advertised_takeoff_runway_m':1900},qualification='Published marketing specifications; conditions and operator cabin not established; no RW delivery/airframe entry inference.'),
 dict(source_id='UAC-SSJ',url='https://uacrussia.ru/en/DDoS01/793e7e55/superjet/',access='native web search primary extract; direct TLS failure retained',observed_fields={'base_range_km':3000,'long_range_km':4500,'passengers_in_description':98},qualification='Legacy type-family description; current tail variant and dispatch weight require operator data.'),
 dict(source_id='TU214-MOD',url='https://www.rostec.ru/en/media/news/the-tu-214-with-domestically-made-systems-received-the-approval-of-a-major-modification/',access='native web primary extract; direct TLS failure retained',observed_fields={'modification_approval_published':'2025-12-27','engine':'PS90A'},qualification='Modification approval and general output plan do not establish RW deliveries or operator readiness.'),
])
dump('coordination_outbox.json',{'thread_id':'91bc9ad6-4e9f-4954-8714-1e4366064b78','delivered_steers':['P03-Q01 and GOJ evidence','No381 and TJM evidence'],'not_delivered_steer':{'code':'thread_not_sendable','exact_message':'Thread 91bc9ad6-4e9f-4954-8714-1e4366064b78 has no running turn that can be steered.','pending_content':'FAP145 Order367 transition/current MRO scope and completed diagnostic threshold tables','handling':'No parent restart or unsolicited new turn. Include in final P03 handoff; no children per explicit role.'}})
dump('schema.json',{
 'unknown':'Literal UNKNOWN is missing information, never numeric zero. Empty numeric values in source snapshots are not imputed.',
 'fleet_calendar.csv':{'key':['calendar_id','aircraft_or_cohort_id','date'],'grain':'monthly cohort summary with inclusive period_end; exact conditional entry dates in diagnostic_delivery_events.csv','unit':'physical tails, tail-days, block hours; columns labelled screening are conditional','record_kind':['parametric_resource','diagnostic_resource_case'],'delivery_forecast':'UNKNOWN in all rows','approved_project_block_hours':'UNKNOWN in all rows until actual assignment and remaining gates accepted','double_count_warning':'PARAMETRIC and DIAG are alternative descriptions, not additive pools. Choose one calendar_id per type/scenario. Existing cohort totals are family observations, not type/variant allocations.'},
 'airport_constraints.csv':{'key':['iata'],'coverage':'20 seeds plus49 additional historical/operating endpoints, including international extension points;69 total','unit':'airport-specific published/unknown constraints','status':'Partial coverage inventory, not airport operational certification. Physical runway length is not TORA/TODA/ASDA/LDA.'},
 'minimum_resource_required.csv':{'key':['requirement_id'],'unit':'hours-only necessary tails under declared k,u and reserve assumptions','coverage':'20 archived hub networks x2 archived market scenarios x2 route-factor points x3 utilisation points=240 rows','not_additive':'Individual networks compete for same resource; joint programme must be recalculated by common engine. MOW legs unresolved are explicitly counted.'},
 'diagnostic_resource_cases':'DIAG_SJ_GOJ8 fixed archived frequencies8 physical pairs; derived target4 at k1.2,u8 plus reserve1. Not a chosen economic programme.',
 'crew_calendar.csv':{'key':['crew_pool_id','date'],'unit':'qualified personnel and individual duty/rest roster, not aircraft block-hours','coverage':'All6 type cohorts x24months;144 rows; actual staffing/duty/rest UNKNOWN; ordinary80h flight-time limit and conditional90h limit are not headcounts or a roster.'},
 'rebuild':'python3 context/35_full_programme_execution_20261112/P03/build_package.py && python3 context/35_full_programme_execution_20261112/P03/prepare_metadata.py && python3 context/35_full_programme_execution_20261112/P03/verify_package.py',
 'source_refresh':'collect_sources.py performs new HTTP collection and changes evidence; not part of offline replay.',
 'future_joint_types':'No new Tu214 mandatory for CASE_SJ; parametric Tu214 branches independent of SJ; request concrete P08I frequencies/readiness thresholds before deriving additional numerical Tu214 calendars.'})
claims=[
 ('P03-C01','RW publishes20RRJ95,3Tu214,2Tu204,3B777;availableprojectresourceUNKNOWN','fleet_observations.csv','RW-FLEET;FAVT-AOC','observed_public_description;unknownavailability'),
 ('P03-C02','GOJ RW contract throughDAILY supports separateoutstation/overnightcandidate','airport_constraints.csv:iata=GOJ','GOJ-MRO','publishedagreement;capacityandPD8UNKNOWN'),
 ('P03-C03','TJM Yamal hangar is not RW allocation;historical3vs6remainunresolved','airport_constraints.csv:iata=TJM','TJM-MRO-JAN;TJM-MRO-SEP','historicalfacility;contractUNKNOWN'),
 ('P03-C04','No381 replacesNo139 for2027-28;crewrosterisaseparategate','operating_rules.json:crew_rules','LAW381-REGISTERED-PDF;LAW381-OFFICIAL-HTTP','primarydocument;operator-specificcomplianceNOT_CHECKED'),
 ('P03-C05','ConcreteGOJ8fixedfrequenciesrequire3working+1reserveunderk1.2/u8proxy','minimum_resource_required.csv:P03-MIN-GOJ-base-K1.2-U8','ARCHIVE_NETWORK_ROUTES','conditionalhours-onlythreshold;notrotationacceptance'),
 ('P03-C06','Four numeric SJ diagnostic delivery branches preserve UNKNOWNforecast','fleet_calendar.csv:DIAG_SJ_GOJ8_*','CASE_H2_RULE;ARCHIVE_NETWORK_ROUTES','selecteddatedresourcecases;notforecast'),
 ('P03-C07','Current MRO approval must be refreshed;oldFAP285newsnot2027-28approval','operating_rules.json:maintenance_rules','FAP145-MINTRANS;FAP145-367','primarylegaltext;actualcertificatesUNKNOWN'),
 ('P03-C08','No free hangar space for non-local based aircraft publicly stated at UFA','airport_constraints.csv:iata=UFA','UFA-TECH','publishedaccessrestriction;newlocalbaseagreementnotruledout'),
]
csvout('claims.csv',[dict(claim_id=a,claim=b,result_locator=c,source_ids=d,status_and_limits=e) for a,b,c,d,e in claims])
print(json.dumps({'sources':len(source_rows),'claims':len(claims)}))
