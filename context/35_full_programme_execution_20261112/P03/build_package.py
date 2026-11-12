"""Rebuild the P03 research tables from pinned inputs. No network/paid execution."""
import calendar, collections, csv, hashlib, json, math
from datetime import date, timedelta
from pathlib import Path

P = Path(__file__).resolve().parent
PLAN='b4d2ddf690440eb5cd051839cc263cf16b364ca4'
AUTHOR='dceadc98f9a293d7530cb7bc50ca4411a95aa4b6'
FIVE='c18f7640ea36647a05b39089e5293f22dd009f63'
ASOF='2026-11-12'
UNKNOWN='UNKNOWN'

def read(path):
    with Path(path).open(newline='') as f:return list(csv.DictReader(f))
def write(name, rows):
    rows=list(rows)
    if name in ['fleet_calendar.csv','airport_constraints.csv','minimum_resource_required.csv']:
        for row in rows:
            row.setdefault('method_version','P03-v1')
            row.setdefault('retrieved_at',ASOF)
            row.setdefault('as_of','2026-11-12 evidence snapshot; future values are scenarios')
            row.setdefault('lower',UNKNOWN);row.setdefault('upper',UNKNOWN)
            if name=='fleet_calendar.csv':
                row.update(status='scenario',unit='tails; tail-days; block hours in separately named columns',period=row['date']+'/'+row['period_end'],geography_or_airport=row['base_airport'],coverage='All24months; monthly cohort summary, dated conditional entries separate; actual crew/MRO/KEEP UNKNOWN')
            elif name=='minimum_resource_required.csv':
                row.update(status='scenario',source_id='ARCHIVE_NETWORK_ROUTES',unit='tails; block hours/week',period='archived representative week; not annual2027-28 schedule',geography_or_airport=row['programme_id'].split('_')[2],coverage='One concrete archived hub programme; source frequencies and rounded distances; hours-only conditional threshold')
            else:
                row['coverage']='Partial airport evidence inventory; not current operational certification'
    with (P/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def js(name, obj): (P/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def prior(commit,path):return P/'inputs'/commit[:8]/path
def addmonths(d,n):
    y,m=divmod(d.year*12+d.month-1+n,12);return date(y,m+1,min(d.day,calendar.monthrange(y,m+1)[1]))
months=[date(y,m,1) for y in [2027,2028] for m in range(1,13)]
seed=read(prior(PLAN,'context/34_full_programme_plan_20261112/city_research_seed.csv'))
oldtech={r['iata']:r for r in read(prior(AUTHOR,'data/manual/airport_tech.csv'))}
routes=read(prior(AUTHOR,'data/processed/network_routes.csv'))
oldrules=read(prior(AUTHOR,'data/assumptions/network.csv'))
registry=[]
def assumption(n,field,value,unit,basis,affected,sensitivity,refine,lower=UNKNOWN,upper=UNKNOWN,status='P03 diagnostic selection; user approved method, not numerical point'):
    registry.append(dict(assumption_id=f'P03-A{n:03}',parameter=field,value=value,unit=unit,selected_by='P03 / gpt-6.1-sol xhigh',basis=basis,approval_status=status,lower=lower,upper=upper,range_basis='Bounds remain UNKNOWN unless a mathematical or source constraint is stated; scenario points are not confidence bounds',affected_conclusions=affected,sensitivity=sensitivity,refinement_method=refine,source_commit=AUTHOR if n<=6 else PLAN,version='P03-v1'))

assumption(1,'historical block-time proxy','0.5 + km*k/750','block hours/flight','Author network.csv and network_model.py leg_cost; uncalibrated kinematic proxy, not a dispatch time','minimum_resource_required; numerical diagnostic calendars','recompute every affected route using dated type-specific block times','P02 seasonal schedule samples; operator route planning')
assumption(2,'utilisation screening points','6.5;8;10','block hours/working tail/day','6.5 and 8 in author docs17; 10 in author network.csv. Three explicit diagnostic points, no evidence-based interval','hours-only necessary fleet threshold','show all three points on same archived programme; not same as changing market scenario','Actual type/base/month dispatch data; duty and MRO calendars')
assumption(3,'generic route-factor diagnostic bracket','1.10;1.20','route km / great-circle km','Author network.csv uses 1.10 ordinary and 1.20 south/west; apply both to every leg as envelope of this proxy only','minimum_resource_required; no route feasibility conclusion','recompute with directional filed tracks, winds, alternates and airspace','Operator flight planning; no inference of certified range',1.10,1.20)
assumption(4,'proxy speed',750,'km/hour','Author block_speed_kmh, no current type-specific calibration','minimum_resource_required','block time sensitivity via A001','Dated type-specific scheduled/actual block times')
assumption(5,'proxy fixed time',0.5,'hours/flight','Author block_fixed_h; not an observed taxi allowance','minimum_resource_required','block time sensitivity via A001','Observed block-time regression with held-out routes')
assumption(6,'diagnostic dedicated reserve',1,'tail per isolated project fleet','Author spare_aircraft; a policy stress, not consequence of national serviceability. Keep separate from tail-specific MRO','diagnostic target; screening ceilings','also publish zero-reserve hours-only threshold; do not subtract same unavailable tail twice','RW dispatch recovery policy and reserve coverage by location',0,UNKNOWN)
assumption(7,'SJ earliest handover boundary','2027-07-01','date','Current user/case H2 2027 restriction; no delivery commitment','CASE_SJ new fleet before Jul2027 excluded','later first arrival; no_new branch','Named RW delivery contract and acceptance dates',status='User-established case scenario boundary; not a factual forecast')
assumption(8,'diagnostic handover grid','2027-07-01 plus 3 months per required tail','date grid','First boundary allowed by case, then quarter steps to expose staged resource, not manufacturer output. Number of tails derived from archived GOJ eight-pair hours threshold at u=8 and k=1.2','DIAG_SJ_GOJ8 phased/partial/delayed/no_new','change dates alone on fixed frequencies; actual season results must be recalculated','P06/P07 programme-specific dated readiness needs')
assumption(9,'diagnostic induction lag',30,'calendar days per tail','Explicit one-month planning stress; duration is not established by public evidence. Crew/MRO/type admission must independently be ready','DIAG_SJ_GOJ8 counts and tail-days','0/30/90 days as labelled diagnostic choices; no plausible confidence range asserted','RW induction work breakdown, training slots and MRO approval')
assumption(10,'partial diagnostic cohort size','floor(target/2)','tails','Capacity stress at half the derived target; does not estimate RW share of national output','DIAG_SJ_GOJ8 partial','integer sweep 0..target; compare threshold crossings','Coordinator programme resource frontier')
assumption(11,'delayed diagnostic shift',6,'calendar months','Two quarter steps of the same date grid, not a forecast','DIAG_SJ_GOJ8 delayed','shift date vector; retain sunk costs with P04','Contract milestones and readiness dates')
assumption(12,'future SJ diagnostic cabin',100,'seats','Author SSJ operator cabin as an explicitly separate analogue; manufacturer advertises max103; no RW SJ cabin confirmed','If coordinator elects this input in network engine','100 vs operator-confirmed cabin; never transfer costs/performance implicitly','RW signed cabin configuration / certified weight-and-balance')
assumption(13,'future RW SJ and annual Tu214 delivery forecast',UNKNOWN,'tails by type/month','No accepted named RW delivery calendar; 11 Tu214 is an announcement, not an annual allocation','all programme growth; funding','delivery axes independent by type; no_new required','Named contract, serial number, handover and induction plan')
assumption(14,'existing free resource and prior tasks',UNKNOWN,'tail-date; flights; block hours','Published fleet totals and winter city list do not reveal spare tails or uncommitted hours','all existing-fleet project effects','necessary release threshold and lost donor/alternative result; UNKNOWN cannot pass','RW tail assignments, charter/lease obligations, AOG, planned maintenance and sales')
assumption(15,'RW airport/MRO contractual access',UNKNOWN,'scope; dates; slots; RUB; SLA','Named historical/current public evidence preserved; no assumption of free capacity from presence of a provider','base/outstation decisions','compare contract/positioning cost and approved scope; no generic zero cost','Airport and certified MRO service agreements; capacity schedule')
assumption(16,'numerical calendar screening status','conditionally inducted and ring-fenced; additional MRO and actual crew UNKNOWN','categorical','Allows numerical capacity diagnostics under stated gates without claiming operator availability. Gross ready counts are a scenario state, not acceptance','fleet_calendar diagnostic rows','loss of a tail-day reduces pre-additional-outage ceiling by u; no multiplicative serviceability plus same reserve','Dated programme and independently accepted tail/crew/MRO assignments')
assumption(17,'monthly calendar aggregation','month; event dates retained','period','Planning horizon all2027–28; partial-month tail-days computed from exact diagnostic events. Calendar is expanded daily for final schedules','fleet_calendar; seasonal integration','monthly sums do not establish daily peak or location feasibility','P06 expands tail event calendars against dated flights and P02 coverage')
assumption(18,'type transfer/performance/cost gaps',UNKNOWN,'payload; fuel; MRO; runway; crew approval','Marketing range and runway lengths lack dispatch conditions; SSJ SaM146 does not certify SJ PD8 or future Tu214','route suitability and type economics','type-specific fuel/payload/time/maintenance threshold; not blanket range rejection','AFM/RLE, approved maintenance programme, contract and type-specific route study')
write('assumptions_register.csv',registry);js('assumptions_register.json',registry)

# A public snapshot is a separately dated observation. It is not forward spare fleet.
observations=[]
for typ,count,seats,rng in [('RRJ95_FAMILY',20,100,4200),('TU214_EXISTING',3,194,5200),('TU204_100B',2,210,3800),('B777_200ER',3,412,9100)]:
    observations.append(dict(observation_id='P03-FLEET-'+typ,aircraft_type=typ,reported_count=count,seats_published=seats,range_published_km=rng,as_of='UNDATED carrier page retrieved 2026-11-12',retrieved_at=ASOF,source_id='RW-FLEET',status='observed_public_statement',coverage='public fleet description; no tail/date serviceability or free allocation',lower=UNKNOWN,upper=UNKNOWN))
for typ,count in [('RRJ95B',2),('RRJ95LR_100',20),('TU214_EXISTING',2),('TU204_100B',2),('B777_21H',3)]:
    observations.append(dict(observation_id='P03-AOC2025-'+typ,aircraft_type=typ,reported_count=count,seats_published=UNKNOWN,range_published_km=UNKNOWN,as_of='2025-09-04',retrieved_at=ASOF,source_id='FAVT-AOC',status='observed_dated_registry_snapshot',coverage='dated certificate inventory; cannot add to or reconcile silently with RW2026 page',lower=UNKNOWN,upper=UNKNOWN))
write('fleet_observations.csv',observations)

params=[]
for typ,engine,seats,rng,source,lim in [
 ('RRJ95B','SaM146','100 family page; tail cabin UNKNOWN','3000 for 98 passengers','UAC-SSJ;RW-FLEET','Base variant; no current B/LR allocation accepted'),
 ('RRJ95LR_100','SaM146','100 family page; tail cabin UNKNOWN','4500 for 98 passengers','UAC-SSJ;RW-FLEET','LR marketing performance; no route-specific payload/dispatch guarantee'),
 ('SJ100_PD8','PD8','RW cabin UNKNOWN; manufacturer up to103','3530 advertised','YAK-SJ100','1900m advertised takeoff runway need has unspecified conditions; airframe/operator readiness not proved by engine certificate'),
 ('TU214_EXISTING','PS90A','194 published RW','5200 advertised RW','RW-FLEET','Do not conflate existing restored aircraft with future domestic-system version'),
 ('TU214_NEW_DOMESTIC','PS90A','UNKNOWN RW configuration','UNKNOWN for exact RW variant','TU214-MOD;TU214-ANNOUNCEMENT','Three-member crew branch unless approved AFM proves otherwise; batch11 is not 2027/28 fleet'),
 ('TU204_100B','PS90A','210 published RW','3800 advertised RW','RW-FLEET','Separate type/variant, resource and missions'),
 ('B777_200ER','UNKNOWN exact engine per tail','412 published RW','9100 advertised RW','RW-FLEET','Whole-business KEEP must preserve or explicitly change international/charter tasks; no free tail implied')]:
    params.append(dict(aircraft_type=typ,engine=engine,seats=seats,range_context=rng,flight_crew_minimum='2 scenario pending exact AFM' if typ in ['RRJ95B','RRJ95LR_100','SJ100_PD8','B777_200ER'] else '3 scenario pending exact AFM',flight_crew_status='type/variant AFM and RW roster required',cabin_crew=UNKNOWN,block_time=UNKNOWN,fuel_t_per_block_hour=UNKNOWN,fuel_t_per_cycle=UNKNOWN,mro_interval_and_downtime=UNKNOWN,dispatch_runway_and_payload=UNKNOWN,approved_airport_list=UNKNOWN,source_id=source,status='published technical description and explicit gaps',as_of=ASOF,assumption_ids='P03-A012;P03-A018',limitations=lim))
write('aircraft_type_parameters.csv',params)

# Airport inventory: preserve every seed and endpoints of historical hypotheses, separately from facts.
v=json.loads(prior(PLAN,'context/34_full_programme_plan_20261112/variant_research_plan.json').read_text())
endpoints=set()
for h in v['legacy_hypotheses']:
    for token in h.get('author_paths','').replace(';','>').split('>'):
        if len(token.strip())==3:endpoints.add(token.strip())
endpoints |= {'SVX','ZIA','DME','SVO','VKO','LED','OVB','KRR','BUS','TBS','EVN','IST','TLV','TAS','ALA','NQZ','MSQ','FRU','HRG','HKT'}
names={r['iata']:r['city'] for r in seed}
names.update(dict(SVX='Екатеринбург / Кольцово',ZIA='Жуковский / Раменское',DME='Москва / Домодедово',SVO='Москва / Шереметьево',VKO='Москва / Внуково',LED='Санкт-Петербург / Пулково',OVB='Новосибирск / Толмачёво',KRR='Краснодар / Пашковский',BUS='Батуми',TBS='Тбилиси',EVN='Ереван',IST='Стамбул / Istanbul',TLV='Тель-Авив / Ben Gurion',TAS='Ташкент',ALA='Алматы',NQZ='Астана',MSQ='Минск',FRU='Бишкек',HRG='Хургада',HKT='Пхукет'))
support={'SVX','KZN','KUF','AER','MCX','LED'}
tech={'GOJ':('3005x45','64/R/B/X/T','27','GOJ-TECH'),'KUF':('3001x45','82/R/C/X/T for15/33','54','KUF-TECH'),'REN':('2500x42','41/R/B/X/T','22','REN-TECH'),'GSV':('3000x45','50/R/B/W/T','21','GSV-TECH')}
mro={
 'GOJ':('ВОЛГА-АВИА','RRJ95 line maintenance through DAILY CHECK','RW contract publicly stated 2026-10-26; price/expiry/capacity UNKNOWN','GOJ-MRO','outstation/overnight+line service and full base are separate candidates'),
 'OMS':('ИАС Омского аэропорта','RRJ95 service in 2024; exact current scope UNKNOWN','RW client stated 2024-12-03;2026/27 contract UNKNOWN','OMS-MRO','Historical8 technicians and6 trainees are not current available man-hours'),
 'KUF':('Яковлев','SSJ station opened 2025-04-30; first4Y check announced for Rossiya','RW contractual access UNKNOWN','KUF-MRO','3500m2 facility is not available RW capacity or PD8 approval'),
 'TJM':('Ямал','SSJ hangar; historical Jan2024 capacity3 vs Sep2024 capacity6','RW contractual access UNKNOWN','TJM-MRO-JAN;TJM-MRO-SEP','Do not choose between3 and6 silently; neither is spare RW capacity'),
 'ZIA':('Red Wings','SSJ A-check started Feb2023; C-check then future plan','Own MRO historical statement; current scope/capacity UNKNOWN','RW-ZIA-MRO','Two simultaneous positions stated historically; PD8 access UNKNOWN'),
 'SVX':('Red Wings','SSJ line station certified Dec2022','Own station historical statement; current scope/capacity UNKNOWN','RW-SVX-MRO','Existing technical footprint is not unoccupied tail/crew time'),
 'UFA':('ТС Техник;НВ-Техник;Aeroflot/Yamal line stations','exact RRJ95/PD8 scope UNKNOWN','RW contract UNKNOWN; airport says no hangar space for non-local based aircraft','UFA-TECH','Conditional constraint for non-local basing; not blanket impossibility of a newly negotiated local base')}
airports=[]
for code in sorted(set(names)|endpoints):
    if code=='MOW':continue
    r=oldtech.get(code,{})
    row=dict(iata=code,city_or_airport=names.get(code,code),coverage_role='seed20' if code in {r['iata'] for r in seed} else 'additional_historical_endpoint_or_operating_extension',period='snapshot2026-11-12;2027-28 rules must be refreshed',status='published_offer' if r or code in mro else 'unknown',runway_published_m=UNKNOWN,runway_strength_published=UNKNOWN,public_parking_positions=UNKNOWN,hours_published=UNKNOWN,technical_source_id=UNKNOWN,ssj100_admission='published airport RRJ95 listing' if code in tech else UNKNOWN,history_ssj_ops_claim=r.get('ssj_source',UNKNOWN),history_ssj_ops_provenance='AUTHOR:data/manual/airport_tech.csv' if r else UNKNOWN,sj100_pd8_admission=UNKNOWN,tu204_214_admission='published airport type listing' if code in tech else UNKNOWN,b777_admission='published KUF B777200 listing' if code=='KUF' else UNKNOWN,base_role='RW support airport city per27Oct2026; footprint not quantified' if code in support else 'UNKNOWN; omission from winter support list is not absence',base_role_source_id='RW-WINTER' if code in support else UNKNOWN,mro_provider=UNKNOWN,mro_type_scope=UNKNOWN,rw_mro_contract=UNKNOWN,mro_source_id=UNKNOWN,available_mro_capacity=UNKNOWN,slots_and_ground_handling_contract=UNKNOWN,overnight_stands_and_crew_rooms=UNKNOWN,rw_mct_and_baggage_agreement=UNKNOWN,aip_notam_declared_distances_and_restrictions=UNKNOWN,year_round_seasonal_windows='UNKNOWN for2027-28; H24 if published is not slot/NOTAM availability',restriction_or_counterexample='Published reception or another carrier operation does not certify all weights/variants/dates',source_id='AUTHOR_AIRPORT_TECH' if r else 'PLAN_VARIANTS',retrieved_at=ASOF,as_of='per named source, not automatically2027-28',unit='airport-specific constraints',lower=UNKNOWN,upper=UNKNOWN,assumption_ids='P03-A015;P03-A018')
    if code in tech:
        row['runway_published_m'],row['runway_strength_published'],row['public_parking_positions'],row['technical_source_id']=tech[code]
        row['hours_published']='H24 published; no dated operational guarantee'
    if code in mro:
        row['mro_provider'],row['mro_type_scope'],row['rw_mro_contract'],row['mro_source_id'],row['restriction_or_counterexample']=mro[code]
    if code=='UFA':
        row['hours_published']='H24 published';row['technical_source_id']='UFA-TECH';row['restriction_or_counterexample']+=';1500domestic/800international pax per hour are terminal totals, not spare capacity'
    if code in ['ZIA','DME']:
        row['base_role']='Named physical case baseline airport; historical RW base statement Feb2023; 2026 winter Moscow city does not resolve airport';row['base_role_source_id']='RW-ZIA-MRO;PLAN'
    if code=='CEK':
        row['base_role']='Historical RW base named Feb2023; current winter list omission does not disprove base';row['base_role_source_id']='RW-ZIA-MRO;RW-WINTER'
    if code=='VKO':
        row['base_role']='AOC2025 lists VKO/DME; current2027-28 project resource UNKNOWN';row['base_role_source_id']='FAVT-AOC'
    if code=='SVO':row['restriction_or_counterexample']='Included in author MOW aggregation without proof of RW base; never allocate MOW resource to SVO'
    if code in ['GOJ','KUF']:
        row['slots_and_ground_handling_contract']='Schedule approval required; services per existing contract or public offer; individual project conditions UNKNOWN'
        row['source_id']+=';'+code+'-TERMS'
    if code=='GOJ':row['year_round_seasonal_windows']+='; normal schedule request at least3working days; this is not a slot guarantee'
    airports.append(row)
write('airport_constraints.csv',airports)

# Store inherited obligations with their coverage defects instead of inventing a tail assignment.
obligations=[]
for i,r in enumerate(read(prior(AUTHOR,'data/manual/rw_routes_now.csv')),1):
    obligations.append(dict(commitment_id=f'P03-KEEP-{i:03}',a=r['a'],b=r['b'],historical_frequency_each_way=r['freq_week_each_way'],source_status=r['freq_status'],source=r['source'],period='2026 snapshot; partly7-13Dec2026; not2027-28 annual calendar',aircraft_type=UNKNOWN,tail_assignment=UNKNOWN,dated_flights=UNKNOWN,sold_seats_and_contract_obligations=UNKNOWN,disposition='KEEP unless explicit programme change with donor opportunity result',qualification='subsidy award/52 or chosen1per week is not dated flight obligation',assumption_ids='P03-A014;P03-A017'))
for typ in ['RRJ95_FAMILY','TU214_EXISTING','TU204_100B','B777_200ER']:
    obligations.append(dict(commitment_id='P03-KEEP-'+typ,a=UNKNOWN,b=UNKNOWN,historical_frequency_each_way=UNKNOWN,source_status='incomplete_whole_business_inventory',source='RW-FLEET;RW-WINTER',period='2027-28 future KEEP required',aircraft_type=typ,tail_assignment=UNKNOWN,dated_flights=UNKNOWN,sold_seats_and_contract_obligations=UNKNOWN,disposition='Preserve regular/domestic/international/charter tasks or price explicit released alternative',qualification='No free type-wide resource proven; B777 excluded from CASE_SJ growth but retained in whole-business bridge',assumption_ids='P03-A014'))
write('existing_commitments.csv',obligations)

# Screening thresholds on concrete archived frequencies. Recalculate target programme, never sum rows.
thresholds=[]
for market in ['base','cautious']:
 for h in [r['iata'] for r in seed]:
    legs=[r for r in routes if r['scenario']==market and r['variant']=='Хаб '+h]
    physical_pairs={tuple(sorted((r['from'],r['to']))) for r in legs if 'MOW' not in [r['from'],r['to']]}
    for k in [1.1,1.2]:
     hrs=sum(2*float(r['freq_week_each_way'])*(.5+float(r['km'])*k/750) for r in legs)
     for u in [6.5,8,10]:
        working=math.ceil(hrs/(7*u))
        thresholds.append(dict(requirement_id=f'P03-MIN-{h}-{market}-K{k}-U{u}',record_kind='minimum_resource_required',programme_id=f'ARCHIVE_HUB_{h}_{market}',source_commit=AUTHOR,source_path='data/processed/network_routes.csv',historical_routes=len(legs),resolved_unique_airport_pairs=len(physical_pairs),unresolved_MOW_legs=sum('MOW' in [r['from'],r['to']] for r in legs),flights_week=2*sum(float(r['freq_week_each_way']) for r in legs),block_proxy_k=k,block_proxy_hours_week=round(hrs,6),screening_utilisation=u,minimum_working_tails_hours_only=working,reserve_policy_tails=1,minimum_total_tails_under_policy=working+1,maximum_hours_for_target=7*u*working,calendar_or_rotation_acceptance='NOT_CHECKED',crew_acceptance='UNKNOWN',mro_acceptance='UNKNOWN',payload_and_airspace_acceptance='UNKNOWN',delivery_forecast=UNKNOWN,interpretation='Necessary hours-only threshold under named proxy; archived weekly frequency is not annual demand or a2027-28 programme',assumption_ids='P03-A001;P03-A002;P03-A003;P03-A004;P03-A005;P03-A006'))
write('minimum_resource_required.csv',thresholds)

# Four diagnostic calendars use a target derived from GOJ's 8 actual airport pairs.
goj_threshold=next(r for r in thresholds if r['requirement_id']=='P03-MIN-GOJ-base-K1.2-U8')
target=goj_threshold['minimum_total_tails_under_policy']
assert target==4
events=[]
for branch in ['phased','partial','delayed','no_new']:
    n=target if branch in ['phased','delayed'] else target//2 if branch=='partial' else 0
    for i in range(n):
        handover=addmonths(date(2027,7,1),3*i+(6 if branch=='delayed' else 0));ready=handover+timedelta(days=30)
        events.append(dict(diagnostic_resource_case='DIAG_SJ_GOJ8',delivery_scenario_id=branch,aircraft_or_cohort_id=f'DIAG_SJ_GOJ8_{branch}_TAIL{i+1}',aircraft_type='SJ100_PD8',handover_date=handover.isoformat(),conditional_entry_date=ready.isoformat(),induction_days=30,crew_ready_date_if_diagnostic_gates_met=ready.isoformat(),mro_support_ready_date_if_diagnostic_gates_met=ready.isoformat(),certification_and_operator_approval='CONDITION_TO_BE_MET_BY_ENTRY;not_observed',new_aircraft_prior_task='none_assumed_new;alternative_use_still_required',delivery_forecast=UNKNOWN,source_id='ARCHIVE_NETWORK_ROUTES;CASE_H2_RULE',assumption_ids='P03-A007;P03-A008;P03-A009;P03-A010;P03-A011;P03-A013;P03-A016'))
write('diagnostic_delivery_events.csv',events)

cal=[]
types=[('RRJ95_FAMILY',20,'existing'),('TU214_EXISTING',3,'existing'),('TU204_100B',2,'existing'),('B777_200ER',3,'existing'),('SJ100_PD8',UNKNOWN,'new'),('TU214_NEW_DOMESTIC',UNKNOWN,'new')]
for branch in ['phased','partial','delayed','no_new']:
 for typ,count,kind in types:
  for month in months:
    end=addmonths(month,1)-timedelta(days=1);zero=kind=='new' and (branch=='no_new' or (typ=='SJ100_PD8' and month<date(2027,7,1)))
    symbol='SJ' if typ=='SJ100_PD8' else 'TU'
    delivery='0' if zero else f'D_{symbol}_{branch}({month:%Y-%m})' if kind=='new' else 'not_a_new_delivery_cohort'
    cal.append(dict(calendar_id='PARAMETRIC_'+branch,record_kind='parametric_resource',delivery_scenario_id=branch,aircraft_or_cohort_id='PARAM_'+branch+'_'+typ,aircraft_type=typ,date=month.isoformat(),period_end=end.isoformat(),period_grain='month',days_in_month=(end-month).days+1,reported_count_reference=count,reported_count_as_of='RW undated fleet page12Nov2026,not forecast',delivery_forecast=UNKNOWN,delivery_in_month=delivery,delivered_by_period_end=0 if zero else UNKNOWN,conditionally_inducted_by_period_end=0 if zero else UNKNOWN,conditional_ready_aircraft_days=0 if zero else UNKNOWN,conditional_reserve_aircraft_days=0 if zero else UNKNOWN,screening_block_hours_before_additional_outage=0 if zero else UNKNOWN,approved_project_block_hours=UNKNOWN,crew_calendar_status='UNKNOWN;separate_roster_not_hours',planned_mro_tail_dates=UNKNOWN,unplanned_mro_status=UNKNOWN,spare_policy='parameter by type/base/date; no shared reserve across incompatible types',base_airport='UNKNOWN;physical airport required',prior_task_or_alternative='existing KEEP/donor must be identified' if kind=='existing' else 'alternative deployment of new resource required',readiness_rule='entry=max(handover+induction,crew_ready,MRO_ready,airframe/operator/airport approvals); remove dated withdrawal intervals',resource_expression='count of unique admissible tail-date assignments after KEEP,reserve and disjoint MRO states; insufficient commitments imply UNKNOWN',seasonal_windows='P02 full-year coverage pending; apply dated flight calendars and airport windows',schedule_acceptance='NOT_CHECKED',source_id='RW-FLEET;PLAN',assumption_ids='P03-A007;P03-A013;P03-A014;P03-A015;P03-A017;P03-A018'))
for branch in ['phased','partial','delayed','no_new']:
 ev=[e for e in events if e['delivery_scenario_id']==branch]
 for month in months:
    end=addmonths(month,1)-timedelta(days=1);dates=[month+timedelta(days=i) for i in range((end-month).days+1)]
    ready=[sum(date.fromisoformat(e['conditional_entry_date'])<=d for e in ev) for d in dates]
    reserves=[min(1,n) for n in ready]
    base=next(r.copy() for r in cal if r['calendar_id']=='PARAMETRIC_'+branch and r['aircraft_type']=='SJ100_PD8' and r['date']==month.isoformat())
    base.update(calendar_id='DIAG_SJ_GOJ8_'+branch,record_kind='diagnostic_resource_case',aircraft_or_cohort_id='DIAG_SJ_GOJ8_'+branch,reported_count_reference='not_operator_fleet',reported_count_as_of='scenario_only',delivery_in_month=sum(month<=date.fromisoformat(e['handover_date'])<=end for e in ev),delivered_by_period_end=sum(date.fromisoformat(e['handover_date'])<=end for e in ev),conditionally_inducted_by_period_end=ready[-1],conditional_ready_aircraft_days=sum(ready),conditional_reserve_aircraft_days=sum(reserves),screening_block_hours_before_additional_outage=8*sum(n-r for n,r in zip(ready,reserves)),approved_project_block_hours=UNKNOWN,spare_policy='one diagnostic dedicated reserve once any tail ready; MRO losses not silently zeroed',base_airport='GOJ hypothetical;SJ100PD8 ground/MRO admission UNKNOWN',prior_task_or_alternative='ring-fenced diagnostic new resource;foregone alternative unknown',source_id='ARCHIVE_NETWORK_ROUTES;CASE_H2_RULE',assumption_ids='P03-A001;P03-A002;P03-A003;P03-A006;P03-A007;P03-A008;P03-A009;P03-A010;P03-A011;P03-A013;P03-A015;P03-A016;P03-A017;P03-A018')
    cal.append(base)
write('fleet_calendar.csv',cal)
crew_calendar=[]
for typ,_,_ in types:
 for month in months:
    crew_calendar.append(dict(crew_pool_id='PARAM_CREW_'+typ,aircraft_type=typ,date=month.isoformat(),period_end=(addmonths(month,1)-timedelta(days=1)).isoformat(),grain='month; requires individual duty/rest roster for acceptance',base_airport=UNKNOWN,qualified_captains=UNKNOWN,qualified_first_officers=UNKNOWN,qualified_flight_engineers=UNKNOWN if typ in ['TU214_EXISTING','TU204_100B','TU214_NEW_DOMESTIC'] else 'not assumed required; exact AFM verification pending',qualified_cabin_crew=UNKNOWN,training_medical_leave_and_standby_dates=UNKNOWN,flight_duty_assignments=UNKNOWN,positioning_and_ground_duties=UNKNOWN,preceding_month_quarter_year_flight_hours=UNKNOWN,daily_and_weekly_rest=UNKNOWN,ordinary_month_flight_hours_per_person=80,conditional_consent_month_limit=90,flight_time_definition='engine start to full stop/shutdown per381pt8; not automatically scheduled block time',resource_acceptance='UNKNOWN',source_id='LAW381-REGISTERED-PDF',method_version='P03-v1',status='unknown',assumption_ids='P03-A014;P03-A018',refinement='P06 dated crew assignments and RW RPP; no PASS from aircraft block-hours'))
write('crew_calendar.csv',crew_calendar)
readiness=[]
for branch in ['phased','partial','delayed','no_new']:
    ev=[e for e in events if e['delivery_scenario_id']==branch]
    first=max(e['conditional_entry_date'] for e in ev) if len(ev)>=target else 'NOT_REACHED_IN_DIAGNOSTIC'
    for row in [r for r in cal if r['calendar_id']=='DIAG_SJ_GOJ8_'+branch]:
        ready=row['conditionally_inducted_by_period_end'];working=max(0,ready-1)
        readiness.append(dict(diagnostic_resource_case='DIAG_SJ_GOJ8',delivery_scenario_id=branch,date=row['date'],fixed_programme='ARCHIVE_HUB_GOJ_base;8uniquephysicalpairs;notendorsednetwork',minimum_resource_required=target,conditional_ready_tails_month_end=ready,working_after_diagnostic_reserve=working,screening_block_hours_week_at_month_end=working*7*8,programme_proxy_hours_week=goj_threshold['block_proxy_hours_week'],hours_only_threshold_met_at_month_end=ready>=target,first_full_threshold_date=first,actual_rotations='NOT_CHECKED',crew_acceptance='UNKNOWN',mro_and_PD8_admission='UNKNOWN',delivery_forecast=UNKNOWN,scope='thresholdonly;notfullmonthfeasibility,annualpassengersorprofit',assumption_ids='P03-A001;P03-A002;P03-A003;P03-A006;P03-A008;P03-A009;P03-A010;P03-A011;P03-A016'))
write('diagnostic_programme_readiness.csv',readiness)

rules={
 'version':'P03-v1','as_of':ASOF,'planning_commit':PLAN,'forecast_status':'UNKNOWN','numeric_diagnostics':'fleet_calendar.csv record_kind=diagnostic_resource_case; never interpret as RW delivery schedule',
 'case_scope':{'CASE_SJ':'standalone existing Superjet release and/or new SJ100;no newTu214 prerequisite','target':'8-12 unique physical airport pairs by end2028 in main scenario;intermediate and scarce-resource branches may be smaller','horizon':'2027-01-01 through2028-12-31 monthly;dated seasonal flights;no December-week times52','new_SJ100_earliest_handover':'2027-07-01 case assumption','new_TU214_earliest':'separate parameter;do not inherit SJ H2 condition','delivery_branches':['phased','partial','delayed','no_new'],'type_joint_branches':'independent type-specific calendars; evaluate material products, not assumed perfect correlation'},
 'delivery_parameter_contract':{'D_type_branch_month':'nonnegative integer handovers specific to RW only when pinned; UNKNOWN otherwise','phased':'chosen planned vector; not national output','partial':'componentwise cumulative deliveries <= phased, final strictly smaller positive when phased>1; integer diagnostic separately declared','delayed':'same chosen vector shifted by positive date lag, independent by type','no_new':'zero handovers in selected horizon; does not set existing spare resource to zero','approval':'handover, airworthiness/operator entry, crew, MRO and airport approval are separate gates'},
 'type_rules':['RRJ95B and RRJ95LR share only a reported family count; do not duplicate20 across each','RRJ95 SaM146 and SJ100 PD8 are different inputs; no unmarked cost/reliability/performance transfer','Tu204100B, existingTu214, new domestic-systemTu214 and B777200ER remain separate','Manufacturer range/runway publicity is not payload-range/AFM evidence; unsupported2300/2900km and2200m screens cannot be feasibility certificates'],
 'calendar_rules':{'unit':'physical tail-date or explicit scenario cohort; monthly aggregation is a planning table','entry':'max(handover+induction,crew_ready,MRO_ready,certification/operator/airport approval)','allocation':'one tail can have one state/location per interval; flights, repositioning, maintenance, KEEP and reserve cannot overlap','no_double_deduction':'partition airworthiness/MRO once; no national serviceability multiplier plus subtraction of same maintenance/reserve tails','reserve':'separate by compatible type/location; ring-fenced reserve cannot simultaneously fly KEEP/project; release only by explicit policy','donor':'each released existing flight/task has dated capacity/sales and lost result; new aircraft have alternative-use cost rather than fictional donor','upper_bound':'sum(block hours) <= offered capacity is necessary only; no schedule PASS from aggregate resources','calendar_days':'use real month length including Feb2028=29; count only ready days and approved seasonal windows'},
 'crew_rules':{
   'document':'Mintrans10Nov2025No381 registered28Nov2025No84348',
   'official_url':'http://publication.pravo.gov.ru/document/0001202511280038',
   'source_id':'LAW381-REGISTERED-PDF;LAW381-OFFICIAL-HTTP',
   'effective_from':'2026-03-01','effective_to_exclusive':'2032-03-01',
   'order_points':{'3':'No139 of2005 and listed changes repealed','4':'validity dates'},
   'applicability':'AnnexI pt1 includes flight/cabin crew and maintenance personnel with relevant licences; AnnexII pt3 mandatory for operator manuals, rosters and timetables',
   'working_time':'pts4,8: flight duty plus ground work and positioning; duty includes preparation/postflight, intermediate standing without rest and relevant delay; flight-time engine-start/stop definition differs from scheduled block time',
   'flight_time_limits_pt9':{'ordinary_hours':{'calendar_month':80,'calendar_quarter':240,'calendar_year':800},'with_documented_written_consent_and_worker_representatives':{'calendar_month':90,'calendar_quarter':270,'calendar_year':900},'medical_limits_also_apply':True},
   'minimum_flight_crew_duty_pt12_appendix1_minutes':[{'base_report':'06:01-21:59','landings_1_2':720,'landings_3_4':630,'landings_5plus':510},{'base_report':'22:00-06:00','landings_1_2':660,'landings_3_4':600,'landings_5plus':390}],
   'duty_qualifiers':['All examined aircraft are non-light transport aircraft with2+flight crew; appendix1 only;3landings in1-2column only for explicitly applicablepts33/34','pt12 local base report time; after >=48h outside base use local outstation per rule; rolling24h applies','pt13 cabin duty extra<=30min only under specified difference and worker representative condition','pts14-19/appendix4 augmented crews require numbers, rest equipment and conditions; not assumed by aircraft range','pt35 exceptional commander extensions are not routine planned capacity'],
   'rest_pts50_54':{'normal':'at least2*completed duty','pt51':'UTC difference>=4h: add30min per hour difference','pt52':'after>=48h in>=4h difference zones:return to base rest>=48h','pt53':'if outstation road time>60min add both specified transfers','pt54':'shortened rest only with worker representatives conditions,appendix5,andpts51/53'},
   'appendix5_minimum_rest_hours':[{'completed_duty':'<=12h','base':12,'outstation':10},{'completed_duty':'>12h and<=14h','base':14,'outstation':12},{'completed_duty':'>14h','base':18,'outstation':16}],
   'weekly_rest_pts56_58':'at least42h;no less often than after6consecutive workdays or2consecutive night duties;night is>=50%22:00-06:00base local;details and exceptions per actual document',
   'roster_and_actuals_pts59_60':'monthly roster and actual time records required;operator-specific rules and worker arrangements must be supplied',
   'acceptance':'UNKNOWN report time,crew id,qualification,ground/positioning work,rest or cumulative time=>UNKNOWN,not PASS;aircraft-hours cannot substitute crew calendar',
   'implementation_scope':'P03 transcribes research constraints,not certified exhaustive crew-compliance software;P06 must validate all relevant provisions on complete rosters'
 },
 'maintenance_rules':{'current_approval':'Obtain current organisation approval and scope for type, engine and location under Part145. Order367 points3/4: effective2025-03-01 to2031-03-01; prior documents continued to2026-09-01 subject to changes/cancellation. Historical FAP285 news is lineage, not current authorisation.','source_id':'FAP145-MINTRANS;FAP145-367','required_fields':['tail','AFM_variant','approved_maintenance_programme_revision','task_due_hours_cycles_calendar','remaining_life','planned_start_end_location','provider_approved_scope','contract_slot','spares_tools','engine/support_SLA','AOG/recovery_plan'],'GOJ':'Public RW agreement through DAILY CHECK for RRJ95; no implied C-check or PD8 access.','TJM':'Yamal facility exists historically; RW access and current capacity UNKNOWN.','KUF':'Historical SSJ station; first4Y check announced for Rossiya; RW access UNKNOWN.','ZIA_SVX':'Historical own SSJ footprint; refresh scope and capacity.','induction':'Training and support of PD8 separate from SaM146; no universal3month fact adopted.'},
 'airport_rules':{'physical_nodes':'MOW is not assignable airport;ZIA/DME/SVO/VKO separate;no cross-airport same-tail connection without repositioning','reception':'publishedRRJ95 receipt does not automatically approveSJ100PD8,all payloads or runway conditions','dated_constraints':['AIP/NOTAM','TORA/TODA/ASDA/LDA','pavementACN-PCN/PCR','RFFS','obstacle/terrain','temperature/wind/contamination','alternate and airspace route','slot','groundhandling/fuel/deicing','stand/night parking','crew accommodation','MRO scope and contracted capacity'],'published_H24':'does not override seasonal/temporary closure or slot scarcity','transfer':'MCT by operator/airport/flow and baggage/ticket conditions;competitorMCT notRW guarantee','unknown_handling':'not proof of ban or zero capacity;programme conditional with exact missing fields'},
 'downstream_dependencies':{'P02':'full2027-28seasonal/directional flight offers+operated data,physicalairports,types,block times and coverage','P06':'dated rotations/crew/MRO assignment and monthly integration;screening thresholds not feasible schedule','P07_P08':'programme-specificfrequency/startdates,base/outstation roles and targetresource thresholds','P04':'type-specific contracts,induction/base/MRO/crew/reserve/repositioning/cash and lostalternatives'},
 'checks':'verification.json;counterexamples.json;law381_visual_check.json',
 'assumption_ids':[r['assumption_id'] for r in registry]
}
js('operating_rules.json',rules)

questions=[dict(question_id='P03-Q01',source='common_spec fleet_calendar;worker brief;user steering2026-11-12',quote='основной N(t) остаётся параметром, но для сравнений нужны также явно условные численные календари и точки потребности конкретных программ',interpretations='parametric only;parametric plus diagnostic numerical resource cases',temporary_recommendation='parametric primary+programme-derived numeric diagnostics;noRW forecast',affected='fleet_calendar;minimum_resource_required;P06/P07',continuing_work='types;airports;legal crew constraints;numeric diagnostics',status='RESOLVED_BY_USER_STEERING',answer='separate delivery_forecast UNKNOWN,diagnostic_resource_case,minimum_resource_required;updateprogramme needs withP06/P07',recalculation_scope='affectedprogramme thresholds,events,monthlycounts only',coordination='t3_thread_send steer delivered;no blockinguserask')]
write('clarification_requests.csv',questions)

deltas=[
 ('P03-ED01','GOJ','RRJ95/SaM146','2026-10-26 public agreement','re-fetched known pinned evidence','GOJ-MRO','RW agreement throughDAILY confirmed byairport statement','Compareoutstation/overnight+lineMROagainstnewbase;noPD8/heavyMRO/capacityinference'),
 ('P03-ED02','TJM','RRJ95/SaM146','2024-01-24;2024-09-19','re-fetched known c18f764 evidence','TJM-MRO-JAN;TJM-MRO-SEP','Yamalhangarclaims3and6SSJ;capacityconflictretained','RWcontract,currentfreeslots,PD8notknown;do notuse6or3asRWresource'),
 ('P03-ED03','ALL','allflight/cabincrewandMROpersonnel','2026-03-01 through2032-02-29','newprimarydocumentcollection','LAW381-REGISTERED-PDF;LAW381-OFFICIAL-HTTP','No381replacesNo139;duty/restseparatefromblockhours','P06/P09crewvalidationmustuse381;unknownrosterisnotPASS'),
 ('P03-ED04','UFA','hangaraccess;exactSSJscopeUNKNOWN','undatedpagefetched12Nov2026','re-fetched known c18f764 evidence','UFA-TECH','Publishednohangerspacefornon-localbasedaircraft','TestnegotiatedlocalbaseorremoteMRO;notblanketairportrejection'),
 ('P03-ED05','RW_FLEET','fourcurrenttypefamilies','2025-09-04vsundatedcarrierpage12Nov2026','newfetchofpublicsnapshots','FAVT-AOC;RW-FLEET','RegistrySSJ22/Tu2142vswebsiteSSJ20/Tu2143havedifferentdates/definitions','Do notcombineorcallreadypool;requesttailcalendar'),
 ('P03-ED06','ALL','SJ100PD8vsRRJ95','publishedproductdata;notoperatorcalendar','newsearchread;directTLSfailurepreserved','YAK-SJ100;UAC-SSJ;FAVT-PD8','ManufacturerPD8productandenginecertificateareseparatefromRWairframeentry','NoportofSSJcostorreliability;noalltypeguaranteefromrange/runwayfilter'),
 ('P03-ED07','ALL','MRO organisation approval by type/engine/location','Part145 effective2025-03-01; prior documents transition to2026-09-01','new primary collection','FAP145-MINTRANS;FAP145-367','Order367 points3/4 requires current approval review for2027-28','Historical FAP285 station announcements establish infrastructure history; request current approval scope and contracts')]
write('evidence_delta.csv',[dict(evidence_delta_id=a,geography=b,aircraft_or_subject=c,applicability_period=d,collection_kind=e,source_id=f,finding=g,consequence_and_limits=h) for a,b,c,d,e,f,g,h in deltas])

write('variant_proposals.csv',[
 dict(proposal_id='P03-V01',related_ids='C02;C28;C32;E02',airports='GOJ',proposal='SeparateGOJoutstation/overnightwithRRJ95DAILYcontractfromfullnewbase',basis='P03-ED01',distinguishing_test='sameflights+datedcrewandMROavailability;priceovernight/positioningagainstnewbase',unresolved='availablecapacity,prices,crewrooms,PD8approval',status='proposal_for_coordinator;notsharedinputmutation'),
 dict(proposal_id='P03-V02',related_ids='C13;E05',airports='TJM',proposal='ComparecontractedthirdpartySSJMROwithownnewinfrastructure',basis='P03-ED02',distinguishing_test='pricedserviceandslots+positioning+recoveryagainstnewbase',unresolved='YamalRWaccess;conflictinghistoricalcapacity;PD8',status='proposal_for_coordinator;notsharedinputmutation'),
 dict(proposal_id='P03-V03',related_ids='C01;C10;C11;E01',airports='UFA',proposal='ExplicitnegotiatedlocalbaseorremoteMRObranchinsteadoffreehangar',basis='P03-ED04',distinguishing_test='contractedhangarandMROscopeorcostedrepositioning',unresolved='newlocalbasecontractandcertifiedtypescope',status='proposal_for_coordinator;notexclusion')])

write('dependency_requests.csv',[
 dict(request_id='P03-D01',owner='P02',fields='dated seasonal flights all2027-28;airportpair,type,blocktimes,cancelled/operatedandcoverage',why='weeklyproxyisnotschedule;preserveexistingduties',blocks='operationalacceptance',available_now='archivedfrequencythresholds;airportconstraints',rerun_trigger='pinnedseasonalinput'),
 dict(request_id='P03-D02',owner='P06/P07/P08',fields='concreteprogramme8-12pairs,datedfrequency/launch,tailrotations,crewassignment/MROdates',why='updateprogramme-specificresourcecasesasagreed;checkpeakandlocation',blocks='finalschedulingandnumericalcalendaracceptance',available_now='4derivedGOJdiagnosticbranches;240minimumresourcerows',rerun_trigger='newpinnedprogrammeorfailedconstraint'),
 dict(request_id='P03-D03',owner='coordinator/operator',fields='existingtailroster,subvariant,airworthiness,donor/chartertasks,crewandmaintenanceprogramme,airport/MROcontracts',why='unknownnotzero;nominalfleetnotavailable',blocks='realRWsparefleetorfulloperatoracceptance',available_now='namedpublicMROevidence;thresholdsandprecisefields',rerun_trigger='relevantacceptedfield'),
 dict(request_id='P03-D04',owner='P04',fields='induction/crew/MRO/base/stand/repositioning/reservecontractsandcash,type-specific',why='noMRO/basepriceinvented;lossalternativesandcashmustbecounted',blocks='fullincrementalfinance',available_now='namedprovidersandscope;pricestatusUNKNOWN',rerun_trigger='pinnedcost/contractchange')])

js('counterexamples.json',[
 {'id':'P03-CE01','claim_challenged':'Enoughweeklyhoursmeansfeasibletimetable','example':'Oneplanehas56weeklyblockhoursbudget;twooutboundflightsbothdepart07:00fromdifferentairportsandlast2heach.Total4<56butassignmentimpossible','result':'aggregatepasses;rotationfails'},
 {'id':'P03-CE02','claim_challenged':'Blockhoursguaranteecrewduty','example':'Dutywith5landingsreporting22:00local,duration7h;flightblock4h;appendix1night5pluslimit6h30forordinaryminimalcrew','result':'hoursproxycanpass;dutyfailsunlessexplicitdifferentapprovedarrangement'},
 {'id':'P03-CE03','claim_challenged':'Appendix5automaticallyallows12hrest','example':'Completeddayduty10h;nextreport14hlater;ordinarypt50rest>=20h;12hminimumcannotbeusedwithoutpt54conditions','result':'ordinaryrestfails;donotapplyminimumsilently'},
 {'id':'P03-CE04','claim_challenged':'Daily8blockhoursonecrewperaircraft','example':'31days*8h=248flight-hoursifflighttimeassumed=blocktime;ordinary80h/monthneedsatleastceil248/80=4completecrewsetsbeforeallotherconstraints','result':'onecrewsetfails;flighttimevsblockmustalsobeseparate'},
 {'id':'P03-CE05','claim_challenged':'EnginePD8certificateandRRJairportadmissionproveSJready','example':'PD8hasenginecertificate;GOJcontractscopeRRJ95DAILY;noairframe/operator/PD8MRObaseapprovalprovided','result':'readinessUNKNOWN'},
 {'id':'P03-CE06','claim_challenged':'20reportedSSJ=20projecttails','example':'If20readytailshave20simultaneousKEEPassignments,freeprojecttails0;withoutassignmentsactualfreepoolUNKNOWN','result':'nominalcountdoesnotestablishfreepool'},
 {'id':'P03-CE07','claim_challenged':'MOWisasinglephysicalbase','example':'AircraftarrivesDME06:00andnextdeparturesZIA06:45;sameMOWnodehidestherequiredrepositioningandgroundprocess','result':'MOWaggregationcannotcertifyrotation'},
 {'id':'P03-CE08','claim_challenged':'No_newmeansprojectcannotoperate','example':'Newhandovers0butexplicitlyreleasedexistingtailmayoperatewithpricedlostdonor;alternativelyallKEEPoccupied','result':'existingresourceconditional;notzeroorfreebydefault'},
 {'id':'P03-CE09','claim_challenged':'TJMhangarsizeisRWcapacity','example':'Yamalreports6positionsbutallcontractuallyoccupied;RWavailable0;publicsourcegivesnocurrentoccupancy','result':'RWaccessUNKNOWN;6isnotallocatable'},
 {'id':'P03-CE10','claim_challenged':'Decweeklycapacityextends52weeks','example':'Oneinductedtailready01Dec2028has31calendardaysin2028;31*8=248grossdiagnostichours,not365*8=2920','result':'useexactentrydates;seasonaldatesandreservefurtherreduce'}])

js('law381_visual_check.json',{'source':'sources/LAW381-REGISTERED-PDF.pdf','source_role':'Registered primary document scan hosted at Minjust/Consultant copy; official publication identity also captured.','sha256':hashlib.sha256((P/'sources/LAW381-REGISTERED-PDF.pdf').read_bytes()).hexdigest(),'pages_in_pdf':26,'visually_read_pdf_pages':[1,2,3,4,6,7,8,9,13,14,15,22,26],'verified_points':['Order3 repeals139','Order4 effective2026-03-01 through2032-03-01','AnnexI applicability;II3/4','II8 duty and flight-time definition','II9 limits80/240/800 and conditional90/270/900','II12/13 report time and landings','II50-54 normal/shortened rest and UTC/road time','II56-60 weekly rest and rosters','Appendix1 day/night landing columns','Appendix5 minimum rest table'],'normal_rest_pt50':'PDF pages13/14 visually checked; text mirror and Rostруд primary guidance crosschecked.','not_done':'Exhaustive compliance software; operator RPP; all augmented-crew and exception branches; actual RW crew roster.','reviewer':'P03 author; not independent review'})

print(json.dumps({'calendar_rows':len(cal),'airport_rows':len(airports),'threshold_rows':len(thresholds),'diagnostic_target_tails':target,'assumptions':len(registry)},ensure_ascii=False))
