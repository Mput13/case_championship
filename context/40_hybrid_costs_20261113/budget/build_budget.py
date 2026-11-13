from pathlib import Path
import csv,json,hashlib
B=Path('/home/mputi/.t3/scratch/red-wings-team-update-20261109-b45f8804/context/40_hybrid_costs_20261113/budget')
C=B.parent.parent
S=['low','base','high']; PH='ANALYST_SELECTED_PLACEHOLDER'
def dump(n,x): (B/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def csvout(n,rs):
 with (B/n).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
def common(evidence='A01',tax='Planning amount; invoice VAT/recovery UNKNOWN; no automatic gross-up',kind=PH):
 return dict(payer='Red Wings/operator; budget assumption',tax=tax,currency='RUB',date='2026-11-13 planning; target 2027-28 unquoted',evidence=evidence,price_class=kind,добавка_vs_замена='добавка только сверх существующих корзин; подтвердить scope')
# Per-unit rates: quantity always supplied by physical/calendar builder, never inferred from deck passengers.
params=[]
def add(i,label,unit,v,driver,scope,why,kind=PH,evidence='A01',tax=None):
 d=dict(parameter_id=i,label=label,unit=unit,low=v[0],base=v[1],high=v[2],qty=driver,frequency='per named unit; multiply by exposure in matching period',scope=scope,rationale=why)
 d.update(common(evidence,kind=kind));
 if tax:d['tax']=tax
 params.append(d)
add('insurance','Aircraft hull/liability/war combined planning envelope','RUB/aircraft-year',[3000000,8000000,20000000],'covered_aircraft_years','MAIN_OPERATING','Author budget envelopes 0.25/0.667/1.667 million per tail-month, deliberately wide; no premium or percent of insured value claimed. Coverage adequacy UNKNOWN. Replace with policy; include reserve tails.','ANALYST_SELECTED_PLACEHOLDER','A_INS;P39_FLEET')
add('dcs_net','Net incremental DCS processing access','RUB/departure',[10,30,80],'uncovered_dcs_departures','MAIN_CONDITIONAL','Small variable software allowance; existing handler DCS removed first. Not a vendor quote. Fixed IT seats below exclude DCS.','ANALYST_SELECTED_PLACEHOLDER','A_IT;S_DCS')
add('outstation_sla','Airline oversight retainer excluding handling','RUB/station-month',[10000,25000,60000],'uncovered_outstation_months','MAIN_CONDITIONAL','GSV/MRV/AER/VOG only if extra airline SLA beyond handler; fixed reporting/readiness excludes callout execution. No new MOW base.','ANALYST_SELECTED_PLACEHOLDER','A_STATION')
add('outstation_callout','Extra airline irregularity coordination callout','RUB/departure',[300,700,1500],'uncovered_outstation_callout_departures','MAIN_CONDITIONAL','Budget incremental coordination work approx 0.5/1/2 hours; departure exposure is a costing normalizer, not evidence every departure needs callout. Not check-in/ramp/baggage.','ANALYST_SELECTED_PLACEHOLDER','A_STATION')
add('mow_extra','Existing MOW base extra coordination capacity','RUB/departure',[100,300,600],'uncovered_mow_coordination_departures','MAIN_CONDITIONAL','Incremental supervisor overtime/shared capacity; no construction or full base allocation. If absorbed by existing team quantity zero with explicit gate.','ANALYST_SELECTED_PLACEHOLDER','A_STATION')
add('oms_parking','OMS monthly basing 30–74.999t','RUB/aircraft-month',[117100]*3,'uncovered_oms_basing_aircraft_months','MAIN_CONDITIONAL','Choose monthly OR daily/hourly/free-window scheme, net existing ground; SSJ MTOW band must match. No assumed contract discount.','PRIMARY','P39_OMS_9.1.1','Published excluding VAT (кроме того НДС); applicable percentage/recovery UNKNOWN')
add('oms_extra_bag','Additional requested reload at OMS','RUB/service',[4450]*3,'uncovered_extra_bag_services','MAIN_CONDITIONAL','One request/service, never per passenger/bag/kg; ordinary loading/transfer handling not automatically extra.','PRIMARY','P39_OMS_2.15','Published excluding VAT; actual percentage/recovery UNKNOWN')
add('oms_rep_desk','OMS information representative workplace','RUB/workplace-service',[1229.51]*3,'uncovered_rep_workplace_services','MAIN_CONDITIONAL','One billed workplace on flight/service, not per employee or transfer passenger; not registration or DCS.','PRIMARY','P39_OMS_2.3','Published excluding VAT; actual percentage/recovery UNKNOWN')
add('hotel_single','Local hotel single room RO','RUB/room-night',[4100]*3,'single_room_nights','MAIN_CONDITIONAL','Published Flagman 2026 local analogue, no RW discount and no 2027 guarantee. Exact calendar room allocation needed.','ANALOGUE','P39_HOTEL','Hotel tax undisclosed; amount as published')
add('hotel_double','Local hotel double room RO','RUB/room-night',[4650]*3,'double_room_nights','MAIN_CONDITIONAL','At most two assigned people per room; round per event/date/eligible sharing group, not once annually.','ANALOGUE','P39_HOTEL','Hotel tax undisclosed; amount as published')
add('crew_perdiem','Extra uncovered crew subsistence','RUB/person-day',[700,1200,2000],'uncovered_crew_person_days','MAIN_CONDITIONAL','Author travel allowance budget, not statutory rate; net hourly crew15/22k BH and meals reimbursed elsewhere.','ANALYST_SELECTED_PLACEHOLDER','A_CREW')
add('crew_position','Crew positioning ticket','RUB/person-segment',[5000,10000,20000],'uncovered_crew_position_segments','MAIN_CONDITIONAL','Actual persons carried on positioning segments, not aircraft movements; exclude if roster avoids positioning.','ANALYST_SELECTED_PLACEHOLDER','A_CREW')
add('crew_transfer','Crew road transfer','RUB/vehicle-trip',[1500,2500,4000],'uncovered_crew_vehicle_trips','MAIN_CONDITIONAL','Taxi/minivan order placeholder per vehicle; do not also charge bus for same group.','ANALYST_SELECTED_PLACEHOLDER','A_CREW')
add('irrops_meal','Food procurement for affected passenger','RUB/meal',[500,800,1200],'uncovered_passenger_meals','MAIN_CONDITIONAL','Procurement allowance, excludes separate distribution service; does not prescribe legal entitlement.','ANALYST_SELECTED_PLACEHOLDER','A_IRROPS')
add('irrops_rebook','External rebooking differential','RUB/affected-journey',[3000,8000,15000],'uncovered_rebooked_journeys','MAIN_CONDITIONAL','Net incremental third-party transport less recoveries; own-flight displacement requires separate contribution logic, not full fare. No compensation automatically.','ANALYST_SELECTED_PLACEHOLDER','A_IRROPS')
add('oms_bus','OMS city bus service','RUB/started-motor-hour',[3430]*3,'uncovered_bus_started_hours','MAIN_CONDITIONAL','Actual orders and started hours; capacity/minimum/delivery UNKNOWN; not cost divided by seats.','PRIMARY','P39_OMS_8.1','Published excluding VAT; actual percentage/recovery UNKNOWN')
add('meal_distribution','OMS meal distribution operation','RUB/service',[3275]*3,'uncovered_meal_distribution_services','MAIN_CONDITIONAL','Food not included; add only if not within handling/meal delivery contract.','PRIMARY','P39_OMS_2.8','Published excluding VAT; actual percentage/recovery UNKNOWN')
# Station recurring BoQ: all own posts serve airline oversight, never reproduce handler agents.
boq=[]
for variant in ['lean_outsource','expanded']:
 specs=[('station_manager',1,8,250,[100000,130000,170000],'airline contract/safety escalation management, not airport management'),('transfer_coordinator',1 if variant=='lean_outsource' else 2,8 if variant=='lean_outsource' else 12,365,[75000,90000,115000],'connection decisions and exception desk; handler still checks in/loads bags'),('local_ops',1,8 if variant=='lean_outsource' else 16,365,[65000,80000,100000],'airline vendor oversight and documentation, no ramp/registration duties'),('it_support',1,400/250 if variant=='lean_outsource' else 1000/250,250,[70000,85000,110000],'shared IT fraction for own endpoints, not DCS vendor support')]
 for role,posts,hours,days,rates,why in specs:
  for j,s in enumerate(S):
   eff=[1800,1680,1560][j];load=[1.25,1.32,1.40][j];coverage=posts*hours*days;fte=coverage/eff;annual=fte*rates[j]*12*load
   d=dict(variant=variant,scenario=s,item_id=role,unit='RUB/FTE-month loaded',rate=rates[j]*load,qty=fte,frequency=12,amount_annual=annual,posts=posts,hours_per_post_day=hours,coverage_days_year=days,coverage_hours_year=coverage,effective_hours_FTE_year=eff,FTE=fte,gross_salary_month=rates[j],loaded_factor=load,rationale=why+'; FTE continuous equivalent, not integer hiring roster; load is analyst scenario not law',overlap_group='station_'+role)
   d.update(common('A_PAY;S_HH_KZN;S_HH_MOW;S_HH_OMS'));boq.append(d)
 # item qty fixed to variant; price uncertainty separate; no staff DCS hardware in handling.
 items=[('ops_software_seats','RUB/seat-month',3 if variant=='lean_outsource' else 6,[3000,5000,8000],'Extra office/ops/security licenses excludes DCS; no quote'),('communications','RUB/station-month',1,[10000,20000,35000],'primary+backup links/mobile and communications allowance'),('small_office','RUB/m2-month',15 if variant=='lean_outsource' else 25,[800,1200,2000],'small shared workroom; airport commercial rent UNKNOWN; excludes storage'),('heated_storage','RUB/m2-month',5 if variant=='lean_outsource' else 10,[1000]*3,'published OMS heated property storage, no maintenance consumption'),('office_consumables','RUB/station-month',1,[10000,20000,40000],'printing/cleaning/office materials only; no spare parts/GSE/MRO')]
 for i,unit,q,rates,why in items:
  for j,s in enumerate(S):
   d=dict(variant=variant,scenario=s,item_id=i,unit=unit,rate=rates[j],qty=q,frequency=12,amount_annual=rates[j]*q*12,posts='NA',hours_per_post_day='NA',coverage_days_year='NA',coverage_hours_year='NA',effective_hours_FTE_year='NA',FTE='NA',gross_salary_month='NA',loaded_factor='NA',rationale=why,overlap_group='station_'+i)
   d.update(common('P39_OMS_11.19' if i=='heated_storage' else 'A_IT;A_STATION',kind='PRIMARY' if i=='heated_storage' else PH));
   if i=='heated_storage':d['tax']='Published excluding VAT; applicable percentage/recovery UNKNOWN'
   boq.append(d)
# Launch expense/CAPEX/deposit/stock different ledgers; no annual replay.
one=[]
def cash(i,unit,q,v,ledger,why,evidence='A_LAUNCH'):
 for j,s in enumerate(S):
  d=dict(item_id=i,scenario=s,unit=unit,rate=v[j],qty=q,frequency=1,amount_cash=v[j]*q,ledger=ledger,annual_expense=0,rationale=why,overlap_group=i);d.update(common(evidence,kind='PRIMARY' if evidence.startswith('P39_') else PH));
  if evidence.startswith('P39_'):d['tax']='Published excluding VAT; percentage/recovery UNKNOWN'
  one.append(d)
for v,n,train in [('lean_outsource',4,8),('expanded',8,14)]:
 cash(v+'_laptops','RUB/device',n,[65000,85000,110000],'CAPEX','Own office laptops only, 16GB/512GB analogue; no bag-tag/check-in hardware purchase; no annual depreciation inferred','A_EQUIP;S_EQUIP')
 cash(v+'_network_furniture','RUB/station-kit',1,[150000,300000,600000],'CAPEX','router/UPS/printer/basic desks-chairs kit, split quote needed; no ramp equipment')
 cash(v+'_setup','RUB/station-setup',1,[150000,400000,900000],'ONEOFF_EXPENSE','IT configuration/security/handler interface testing; excludes airline-wide systems build and vendor monthly support')
 cash(v+'_staff_training','RUB/person-course',train,[15000,30000,60000],'ONEOFF_EXPENSE','Non-flight station induction; seats not flight crew type conversion; staff count placeholder distinct from fractional FTE')
 cash(v+'_passes','RUB/pass',train,[696.72]*3,'ONEOFF_EXPENSE','Permanent passes up to5 years, not annual renewal','P39_OMS_5.2')
 cash(v+'_office_deposit','RUB/monthly-rent-deposit',1,[15*800 if v=='lean_outsource' else 25*800,15*1200 if v=='lean_outsource' else 25*1200,15*2000 if v=='lean_outsource' else 25*2000],'REFUNDABLE_DEPOSIT','One month rent security budget; not signed requirement; recoverable asset')
cash('pool_security','RUB/pool-deposit',1,[2000000,5000000,12000000],'REFUNDABLE_DEPOSIT','Author cash reserve envelope for shared exchange pool access, not annual MRO; no purchased spare stock also assumed','A_POOL')
cash('initial_nonpool_spares','RUB/initial-stock-lot',1,[0,0,0],'INVENTORY_NOT_SELECTED','Outsource/exchange pool chosen; zero is an explicit no-owned-inventory design choice, NOT observed price. If stock purchased remove overlapping pool coverage and expense consumption through MRO only','A_POOL')
# coverage rules all with same row metadata
rules=[]
for i,basket,rule in [
 ('ground','96089/115307 RUB/flight','Existing modeled basket retained once. Handler passenger registration/loading/baggage/ramp/GPU/steps/buses presumed procured function for this BoQ; actual allocation UNKNOWN. Scope difference requires contract before adding.'),
 ('pax','500/650 RUB/boarded segment','Do not add ordinary passenger/baggage/IT services twice; transfer journey already two model segments.'),
 ('crew','15000/22000 RUB/BH','Keep hourly crew once; no full flight-crew payroll added. Extra hotel/perdiem/positioning only uncovered quantities.'),
 ('mro','35000/55000 RUB/BH','Keep MRO once; pool deposit/stock assets separate; no stock consumption/heavy/engine reserve over same MRO.'),
 ('desk','1229.51 RUB/workplace-service','Only additional information workplace actually ordered. Count max requested workplaces per flight/service, not FTE or transfer pax; hotel/event desks not each repeated.'),
 ('bag','4450 RUB/requested service','Normal baggage/transfer handling covered by chosen handler design. Extra reload order only; do not use per passenger, kg or bag; no automatic one operation per departure.'),
 ('parking','117100 RUB/aircraft-month','Add only uncovered basing months; do not combine monthly/daily/hourly scheme or existing ground parking for same tail/time.'),
 ('post','RUB/FTE-month','Own station roles exclude handler operation. If handler provides transfer coordinator subtract matching post hours before FTE, not arbitrary percent of all payroll.'),
 ('it','DCS departure and office seat','DCS software only residual beyond handler/pax; office seat license excludes DCS. No automatic 1229.51 + DCS + check-in hardware.'),
 ('room','room-night','Person-night and crew room assignment required. Single+double mutually exclusive for each person-night; double rooms ceil per date/event/share-group.'),
 ('outstation','station-month + callout','Fixed readiness retainer and incremental callout execution distinct; 4 unique GSV/MRV/AER/VOG counted once across hub/direct; existing MOW base no new-build charge.'),
 ('insurance','aircraft-year','7 hub+3direct =10 deck planning tails, reserves already included; no extra reserve automatic. Joint shared-tail allocation must sum unique covered tail-time.'),
 ('launch','oneoff/capital/working capital','ONEOFF_EXPENSE separate launch period; CAPEX not immediate annual expense; refundable deposits/stock/prepayments not annual operating expense.'),
 ('tax','invoice','Published exVAT remains exVAT. No unsupported 20/22% gross-up or second netting. Actual unrecoverable VAT add separately by invoice; cash recovery timing separately.'),
 ('finance','purchase/lease','Aircraft purchase/lease/financing excluded MAIN by latest user; no SSJ2015 7.56m transfer to SJ/PD8.'),
 ('irrops','affected journey/event','Probabilities below are analyst sensitivity, not historical observations. Rebooking, meals, hotel sum only different services; exclude losses already in revenue/migration.')]:
 d=dict(rule_id=i,existing_rate=basket,qty='scope-matched actual incremental units',frequency='once per unit/period',rule=rule,unit='scope rule');d.update(common('P39_COVERAGE;'+('P39_OMS' if i in ['desk','bag','parking'] else 'A01')));rules.append(d)
csvout('cost_parameters.csv',params);csvout('station_BoQ.csv',boq);csvout('oneoff_cash.csv',one);csvout('coverage_netting_rules.csv',rules)
a=dict(status='COMPLETED_BUDGET_MODULE_NOT_ACTUAL_PNL',team_approved=False,scenarios=S,reference_date='2026-11-13',currency='RUB',budget_price_year='2026 planning nominal; 2027-28 not escalated or quoted',station_options=['lean_outsource','expanded'],FTE_formula='posts*hours_per_post_day*coverage_days_year/effective_hours_FTE_year',effective_hours=[1800,1680,1560],payroll_load=[1.25,1.32,1.40],annualization='BoQ station retained 12 months regardless of winter flying; period station cost = annual * retained_months/12; use actual coverage_hours if known; no aircraft-night -> crew-night shortcut',MAIN_excludes=['aircraft purchase','aircraft lease','financing','CAPEX immediate writeoff','refundable deposits','initial inventory as expense'],unknown_actuals=['RW insurance premium/coverage','RW station contract/handler split','2027 salary offers','roster person-nights','IT contract','outstation minimums','invoice VAT recoverability'],no_price_fact_from=['P04 empty cells','RW insured value78bn','unperioded initial insurance tender','SSJ2015 sublease'],irrops=dict(affected_share=[0.002,0.01,0.03],overnight_share_of_affected=[0.25,0.5,1],nights_per_overnight=[1,1,2],meals_per_affected=[1,2,3],rebooking_share_of_affected=[0.25,0.5,1],note='All probabilities author scenarios; prefer actual event units over this convenience sensitivity; transport event volumes supplied separately'),insurance_sweep_RUB_aircraft_year=[0,1000000,3000000,5000000,8000000,12000000,20000000,30000000,50000000,60000000],search=dict(queries=8,opens_clicks_including_errors=12,stopped=True),API='budget_api.py evaluate(exposures,scenario,variant,residual_before=None); zero absent exposures means not yet supplied, returned explicitly; never implicit completed network budget')
dump('assumptions.json',a)
# inputs provenance, hash exact local read inputs without modifying them
paths=[B.parent/'TASK.md',B.parent/'pins.json',B.parent/'inputs/deck_text.json',C/'39_cost_completion_20261113/README.md',C/'39_cost_completion_20261113/calculation/COST_TABLE.csv',C/'39_cost_completion_20261113/omsk_price_recovery/prices.csv',C/'39_cost_completion_20261113/research_fleet/README.md',C/'39_cost_completion_20261113/fleet_price_recovery/README.md',C/'39_cost_completion_20261113/model_audit/coverage.csv']
paths+=list(C.glob('31_direct_growth_research_20261112/audit/inputs/audit_model/620a0ac4/context/35_full_programme_execution_20261112/P04/cost_ranges.csv'))
dump('sources/local_inputs.json',[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths])
print('Generated',len(params),'parameters',len(boq),'station rows',len(one),'cash rows',len(rules),'netting rules')
