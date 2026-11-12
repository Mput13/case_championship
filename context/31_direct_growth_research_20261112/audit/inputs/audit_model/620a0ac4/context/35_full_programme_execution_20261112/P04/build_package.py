"""Build P04 evidence tables without changing shared inputs or frozen baselines."""
import csv
import json
from decimal import Decimal as D
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERSION = 'P04-v1-20261112'
ASSUMPTIONS, COSTS, SUPPORT = [], [], []
RECEIPTS = json.loads((ROOT/'source_receipts.json').read_text())
SOURCES = {r['source_id']: r for r in RECEIPTS}

def writecsv(name, rows):
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with (ROOT/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)

def writejson(name,obj):
    (ROOT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')

def assume(aid,subject,value,unit,basis,source_id='',lower='',upper='',status='ANALYST_SELECTED_NOT_USER_APPROVED',
           affected='P06/P09 economics and funding',sensitivity='',refine='',choice_type='method_or_missing_input',selected_by='P04 research agent'):
    ASSUMPTIONS.append(dict(assumption_id=aid,subject_version=VERSION,subject=subject,value=value,unit=unit,
      selected_by=selected_by,choice_type=choice_type,basis=basis,source_id=source_id,
      approval_status=status,lower=lower,upper=upper,range_status='UNKNOWN' if lower=='' else 'EXPLICIT_SCOPE_NOT_CONFIDENCE_INTERVAL',
      affected_conclusions=affected,sensitivity=sensitivity,refinement=refine,
      change='NEW_P04_REGISTER_ENTRY; historical sources preserved',supersedes_id='',confidence_interval=False))
    return aid

def cost(cid,category,geo,typ,driver,unit,value,source,page,eff,*,lower='',upper='',status='published_offer',
         basis='Published local price; not a paid RW invoice or future contractual bound',
         includes='',excludes='',cash='',overlap='',formula='',end='',choice='Use local published rate only in its scope',refine='',tax='Excluding VAT; recoverability and applicable rate require invoice/legal mapping',
         base='',cautious='',period='2026 reference; 2027-2028 unpriced',ledger='variable_operating',currency='RUB'):
    aid='P04-A-'+cid
    r=SOURCES.get(source,{})
    if status=='published_offer' and value!='' and lower=='' and upper=='':
        lower=upper=value
        basis='SINGLE_PUBLISHED_LOCAL_POINT; not bounds on RW paid/future rate. '+basis
    assume(aid,cid,value if value!='' else 'UNKNOWN',unit,basis,source,lower,upper,
      affected=f'{geo}/{typ} {category}; {ledger}',sensitivity=formula or f'dResult/dRate = -quantity({driver})',
      refine=refine or 'Obtain dated local RW contract/invoice, service scope and settlement schedule',
      choice_type='published_reference_application' if status=='published_offer' else 'historical_scenario_or_unknown')
    ASSUMPTIONS[-1]['selected_by']=('Airport sets published rate; P04 chooses local reference application' if status=='published_offer'
      else 'Historical author model; individual parameter author UNKNOWN; P04 retains as unapproved point' if status=='scenario'
      else 'P04 identifies missing required field; numeric value not selected')
    COSTS.append(dict(cost_id=cid,key=category,period=period,geography_or_airport=geo,aircraft_type=typ,
      driver=driver,unit=unit,currency='N/A_physical_quantity' if unit.startswith('t/') else currency,price_year=2026 if value!='' else '',tax_basis=tax,
      value=value,base_point=base,cautious_point=cautious,lower=lower,upper=upper,range_basis=basis,
      status=status,source_id=source,source_url=r.get('url',''),source_local_path=r.get('local_path',''),
      source_pdf_page=page,retrieved_at=r.get('retrieved_at','saved_git_blob; see receipts'),as_of='2026-11-12',
      effective_from=eff,effective_until=end or 'UNKNOWN; check revisions',method_version=VERSION,
      coverage=choice,ledger=ledger,included_components=includes,excluded_components=excludes,
      accrual_rule='Service/consumption period; commitment items follow contract',cash_rule=cash or 'Contract invoice/prepayment/payment event; lag UNKNOWN',
      overlap_guard=overlap or 'One service item once per physical movement; alternative packages mutually exclusive',
      threshold_formula=formula or f'max_affordable_rate = residual_headroom / quantity({driver}); quantity=0 requires separate branch',
      refinement=refine or 'RW contract plus airport revision and service specification',assumption_id=aid))

def make_costs():
    # Every point below is a local reference, not an empirical range of actual RW costs.
    pubs={
      'UFA':('ufa_services_20261111','2026-11-11',[
        ('takeoff_landing','mtow_t_per_billed_turn','RUB/t_MTOW',553,1),('security','mtow_t_per_billed_turn','RUB/t_MTOW',499,1),
        ('terminal_domestic','eligible_departing_pax','RUB/pax',70.5,1),('terminal_international','eligible_departing_pax','RUB/pax',102,1),
        ('pax_service_domestic','eligible_departing_pax','RUB/pax',268,1),('pax_service_international','eligible_departing_pax','RUB/pax',452,1),
        ('stairs_both','stairs_arrival_departure_pair','RUB/pair',19300,1),('bus','bus_units','RUB/vehicle',8100,1),
        ('fuel_uplift','uplifted_t','RUB/t',1696,1),('fuel_storage','stored_t','RUB/t',1353,1),
        ('parking_SSJ','billable_parking_h','RUB/h',685,1),('deice_one_stage_SSJ','deice_events','RUB/event',49970,2),
        ('deice_two_stage_SSJ','deice_events','RUB/event',65000,2),('receive_release_SSJ','turns','RUB/turn',16668,3),
        ('deice_one_stage_Tu214','deice_events','RUB/event',53160,2),('deice_two_stage_Tu214','deice_events','RUB/event',69200,2),
        ('receive_release_Tu214','turns','RUB/turn',31457,3),
        ('crew_preflight_medical','crew_persons','RUB/person',420,1),('crew_transport','crew_transport_units','RUB/transport',4950,1)]),
      'GOJ':('goj_tariff_20261101','2026-11-01',[
        ('takeoff_landing','mtow_t_per_billed_turn','RUB/t_MTOW',870,1),('security','mtow_t_per_billed_turn','RUB/t_MTOW',663,1),
        ('terminal_domestic','eligible_departing_pax','RUB/pax',180,2),('terminal_international','eligible_departing_pax','RUB/pax',180,2),
        ('pax_service_domestic','eligible_departing_pax','RUB/pax',780,2),('pax_service_international','eligible_departing_pax','RUB/pax',1050,2),
        ('stairs_both','stairs_arrival_departure_pair','RUB/pair',15600,3),('bus','bus_approaches','RUB/approach',7260,3),
        ('crew_preflight_medical','crew_persons','RUB/person',436,3),('crew_postflight_medical','crew_persons','RUB/person',1990,3),
        ('crew_transport','crew_transport_units','RUB/transport',3405,3),('towing','towing_events','RUB/event',25400,3)]),
      'KUF':('kuf_tariff_20261101','2026-11-01',[
        ('takeoff_landing','mtow_t_per_billed_turn','RUB/t_MTOW',410.6,1),('security','mtow_t_per_billed_turn','RUB/t_MTOW',360.4,1),
        ('terminal_domestic','eligible_departing_pax','RUB/pax',142,2),('terminal_international','eligible_departing_pax','RUB/pax',202,2),
        ('pax_service_domestic','eligible_departing_pax','RUB/pax',436.8,2),('pax_service_international','eligible_departing_pax','RUB/pax',524.2,2),
        ('stairs_both','stairs_arrival_departure_pair','RUB/pair',25000,3),('bus','bus_approaches','RUB/approach',8180,3),
        ('crew_preflight_medical','crew_persons','RUB/person',420,3),('crew_postflight_medical','crew_persons','RUB/person',1690,3),
        ('crew_transport','crew_transport_units','RUB/transport',3400,3),('towing','towing_events','RUB/event',25300,3)]),
      'OMS':('omsk_tariff_base_20260821','2026-08-21',[
        ('takeoff_landing','mtow_t_per_billed_turn','RUB/t_MTOW',911,1),('security','mtow_t_per_billed_turn','RUB/t_MTOW',947,1),
        ('terminal_domestic','eligible_departing_adult_pax','RUB/pax',97,1),('terminal_international','eligible_departing_adult_pax','RUB/pax',140,1),
        ('pax_service_domestic','eligible_departing_adult_pax','RUB/pax',200,1),('pax_service_international','eligible_departing_adult_pax','RUB/pax',297,1)]),
      'KHV':('khv_tariff_202611','2026-01-01',[
        ('takeoff_landing','mtow_t_per_billed_turn','RUB/t_MTOW',700,1),('security','mtow_t_per_billed_turn','RUB/t_MTOW',609,1),
        ('basing_40_60t','based_aircraft_months','RUB/tail/month',133477,1),('basing_60_120t','based_aircraft_months','RUB/tail/month',168160,1),
        ('basing_120_300t','based_aircraft_months','RUB/tail/month',210200,1),
        ('parking_40_60t','billable_parking_h','RUB/h',1051,1),('stairs_single','stairs_operations','RUB/operation',9144,1),
        ('bus_large','bus_units','RUB/vehicle',4740,1),('crew_medical','crew_persons','RUB/person',264,7)])}
    for airport,(source,edition,items) in pubs.items():
        for category,driver,unit,value,page in items:
            eff=edition
            if airport in ['GOJ','KUF']:
                eff='2019-01-01' if page<3 else '2025-12-21'
            if airport=='KHV' and category in ['takeoff_landing','security']:eff='2026-02-10'
            typ='SSJ100_SaM146' if category.endswith('SSJ') else ('40<MTOW<=60t' if '40_60' in category else 'all_applicable_types')
            if category.endswith('Tu214'):typ='Tu214'
            if '60_120' in category:typ='60<MTOW<=120t'
            if '120_300' in category:typ='120<MTOW<=300t'
            cost(f'{airport}-{category}',category,airport,typ,driver,unit,value,source,page,eff,
                 includes='Only named service in primary price list',
                 excludes='Other handling; flights/crew/parts/base business; VAT; contractual minima and discounts',
                 choice=f'Local reference; document edition {edition}. OMS base amendments require item-by-item check; not 2027 forecast.',
                 ledger='base_fixed' if 'basing_' in category else 'variable_operating')
    cost('UFA-fuel-20261111','fuel_product','UFA','all_applicable_types','uplifted_t','RUB/t',136300,'ufa_fuel_20261111',1,'2026-11-11',
         includes='TS-1/RT product only',excludes='Uplift1696/t; storage1353/t if billed; VAT; fuel excise/support')
    cost('UFA-fuel-20260817','fuel_product_historical','UFA','all_applicable_types','uplifted_t','RUB/t',133200,'ufa_fuel_20260817',1,'2026-08-17',
         end='supersession exact date UNKNOWN; new published reference effective2026-11-11',
         choice='Historical author reference only; not added together with new fuel price')
    # Preserve author points. No invented credible endpoints.
    historical=[('fuel_t_per_hour','block_hours','t/block_h',1.55,1.90),('fuel_t_per_cycle','cycles','t/cycle',.20,.25),
      ('mro_rub_per_hour','block_hours','RUB/block_h',35000,55000),('crew_rub_per_hour','block_hours','RUB/block_h',15000,22000),
      ('navigation_rub_per_hour','block_hours','RUB/block_h',6000,8000),('pax_cost_rub','occupied_segments','RUB/occupied_segment',500,650)]
    for k,driver,unit,b,c in historical:
        cost('HIST-'+k,k,'historical_network_proxy','SSJ100_SaM146_analogue',driver,unit,'','author_network.csv','', '',
             status='scenario',base=b,cautious=c,basis='Two author scenario points at dceadc98; credible range UNKNOWN; not estimated confidence bounds',
             includes='Historical model aggregate; item split not known',excludes='SJ100/PD8 actual performance or MRO offer',
             overlap='Choose legacy aggregate OR component build; do not add crew fixed payroll or passenger-service tariff without decomposing legacy aggregate',
             refine='Fuel: P03 dispatch/tail data. Crew: roster/payroll/flight pay. MRO: type-engine PBH and cycles/minimum utilisation contract. Navigation: route/MTOW tariff.')
        ASSUMPTIONS[-1]['value']=f'base={b};cautious={c};credible_range=UNKNOWN'
    unknown=[
      ('fuel_contract_future','uplifted_t','RUB/t','variable_operating','2027/28 airport supplier invoice and fuel tankering plan'),
      ('fuel_burn_SJ100_PD8','block_hours_and_cycles','t/flight','variable_operating','Type/engine flight-plan burn versus distance/payload/weather; P03'),
      ('mro_hour','block_hours','RUB/block_h','variable_operating','Engine+airframe PBH scope, minimum BH, hard-time parts and exclusions'),
      ('mro_cycle','cycles','RUB/cycle','variable_operating','Landing gear/brakes/engine life-limited-parts cycle policy; separate from PBH'),
      ('mro_calendar','tail_months','RUB/tail/month','aircraft_use','Scheduled calendar checks, committed reserves, escalation and recovery'),
      ('crew_payroll','crew_FTE_months','RUB/FTE/month','crew_fixed','Roster, employer charges, training, leave/standby and duty limits'),
      ('crew_variable','block_hours','RUB/block_h','variable_operating','Flight pay only if not already in salary/historical hourly proxy'),
      ('crew_hotel','person_nights','RUB/person/night','variable_operating','Airport-city hotel rate, room occupancy, season and transport'),
      ('navigation','route_distance_MTOW_airspace','RUB/flight','variable_operating','Dated domestic/foreign ANSP tariff, route distance and currency'),
      ('lease','committed_tail_months','RUB/tail/month','aircraft_use','RW lessor term sheet by aircraft/engine; include minimum and return conditions'),
      ('owned_depreciation','owned_tail_months','RUB/tail/month','depreciation','Acquisition basis, residual and useful life; choose ownership basis'),
      ('insurance','tail_months_and_ASK','RUB/month','aircraft_use','Hull/war/liability certificate, territories, premium and deductibles'),
      ('base_operations','base_months','RUB/base/month','base_fixed','Incremental station staff/room/IT/security/utilities not airport parking'),
      ('base_MRO_capacity','base_months','RUB/base/month','base_fixed','Available certified line station, tools, minimum fee and qualified people'),
      ('reserve_aircraft','reserve_tail_months','RUB/tail/month','aircraft_use','Dedicated/shared reserve allocation and truly additional commitments'),
      ('entry_expense','launches','RUB/launch','startup_expense','Hiring, training, certification, commercial launch expensed portion'),
      ('induction_expense','inducted_tails','RUB/tail','startup_expense','Acceptance, familiarisation, training, ferry and entry into service'),
      ('launch_capex','launches','RUB/launch','capex','Base equipment/spares/IT assets and depreciation basis'),
      ('aircraft_purchase','accepted_tails','RUB/tail','capex','RW purchase/lease structure and actual acceptance payment calendar'),
      ('aircraft_advance','ordered_tails','RUB/tail','advance','Pre-delivery deposit/advance dates; offset against final purchase amount'),
      ('security_deposit','contracts','RUB/contract','deposit','Refundable deposit timing, setoff, restrictions, forfeiture and release'),
      ('exit_penalty','terminated_contracts','RUB/exit','exit_expense','Notice period, severance, station restoration and supplier minimum bills'),
      ('redelivery','returned_tails','RUB/tail','exit_expense','Engine/airframe condition, reserve credit, ferry and redelivery location'),
      ('ferry','physical_ferry_legs','RUB/leg','variable_operating','Fuel, fees, crew and end-position restoration; no passengers needed to incur costs'),
      ('distribution_payment','bookings_or_revenue','RUB/booking_or_fraction','variable_operating','GDS/agent/acquiring/channel settlement; gross versus net sales basis'),
      ('passenger_other','occupied_segments','RUB/segment','variable_operating','Catering, baggage and connection support excluding separately charged terminal fees'),
      ('disruption','affected_journeys_nights_legs','RUB/event','variable_operating','Refunds/rebooking/hotels and preventable cancellation costs by event'),
      ('charter_guarantee','guaranteed_blocks','RUB/block','commercial','Tour-operator allotment, guarantees, release, advance and failure terms'),
      ('foreign_handling','foreign_turns','LOCAL/turn','variable_operating','SGHA/local supplier quote with currency, airport and service regime'),
      ('foreign_fuel','uplifted_t','LOCAL/t','variable_operating','Airport supplier price, tax, uplift and payment currency; no automatic Russian fuel credit'),
      ('fx','dated_foreign_settlements','RUB/LOCAL','currency','Dated FX/hedge and bank conversion fees; no common arbitrary FX multiplier'),
      ('international_access','authorisations_slots','RUB/programme','startup_expense','Permits, visa/crew handling, overflight, slots, insurance and local representative'),
      ('tax_profit','taxable_profit_and_losses','RUB/month','tax','Actual taxable base, carryforwards, tax status and payment dates'),
      ('interest','daily_debt_balances','RUB/month','finance','Loan margin, floor, fees, day count, collateral and cash dates; CBR rate is not RW offer'),
      ('VAT','invoice_taxes','RUB/month','tax','Invoice-level output/input VAT, recoverable fraction and refund/payment period'),
      ('ticket_collection','bookings_date','RUB/month','working_capital','Advance sales, agent/merchant holdbacks, refunds and month-of-carriage mapping'),
      ('supplier_payment','invoice_date','RUB/month','working_capital','Prepayment days, credit days, minimum guaranteed settlement and invoice lag'),
      ('support_payment','approved_claim_date','RUB/month','working_capital','Agency/tax approval date, bank-credit date and corrections; no immediate refund'),
      ('donor_lost_contribution','changed_keep_flights','RUB/month','counterfactual','KEEP full affected revenue/cost with same resource and passenger recapture'),
      ('new_tail_opportunity','feasible_alternative_programme','RUB/month','opportunity','Best available alternative from common engine; no fictional donor for new delivery')]
    for k,driver,unit,ledger,missing in unknown:
        types=['SSJ100_SaM146','SJ100_PD8','Tu214','other_existing_RW_type'] if k in ['mro_hour','mro_cycle','mro_calendar','crew_payroll','lease','reserve_aircraft','induction_expense'] else ['specified_type_required']
        for typ in types:
            special_formula={
              'fuel_burn_SJ100_PD8':'max_affordable_fuel_t_per_flight = residual_headroom_RUB / (completed_flights * effective_net_fuel_RUB_per_t); physical model must fit route/payload',
              'fx':'break_even_RUB_per_LOCAL = remaining_RUB_headroom / net_foreign_cost_exposure_LOCAL; sign/zero exposure branches explicit',
              'charter_guarantee':'min_required_net_guarantee_RUB_per_block = (full_cost_other - revenue_other - eligible_support) / guaranteed_blocks',
              'new_tail_opportunity':'Compare full feasible alternative programme result under common resource; memo opportunity value is not another cash cost',
              'donor_lost_contribution':'Full affected-business project-KEEP already includes donor sales/cost change; do not subtract this bridge memo again'}
            cost('UNK-'+k+'-'+typ,k,'airport_or_base_or_route_required',typ,driver,unit,'','plan_common_spec.json','', '',
                 status='unknown',basis='Credible internal/local contract range UNKNOWN; physical non-negativity is not a price estimate',
                 ledger=ledger,refine=missing,excludes='No substitution by zero, generic ±percent or other type contract',
                 choice='Required by budget coverage; unresolved amount propagates to full total',formula=special_formula.get(k,''),currency='LOCAL' if unit.startswith('LOCAL') else 'RUB')

def make_support():
    def add(sid,name,source,unit,formula,eligibility,cap,lag,exclusions,period,fields,*,value='',lower='',upper=''):
        aid='P04-A-'+sid
        assume(aid,name,value or 'UNKNOWN_AWARD',unit,'Apply only after individual eligibility and exact period/version check',source,lower,upper,
          affected='Support accrual; full operating result; funding; supported fare/demand',sensitivity='S_required = C_full - R; awarded S must satisfy legal and budget limits',refine=fields)
        r=SOURCES[source]
        SUPPORT.append(dict(scheme_id=sid,name=name,period=period,geography_or_airport='Scheme-specific route/fuel purchase',
          source_id=source,source_url=r.get('url',''),source_local_path=r.get('local_path',''),as_of='2026-11-12',
          retrieved_at=r.get('retrieved_at','saved_snapshot'),status='published_scheme; RW2027_2028_award_UNKNOWN',
          unit=unit,value=value,lower=lower,upper=upper,accrual_formula=formula,eligibility=eligibility,limit=cap,
          cash_lag=lag,exclusions_and_overlap=exclusions,remaining_fields=fields,assumption_id=aid))
    add('SUP-REGIONAL','Regional network decision22-64160-00191-R Version7','regional_rules_v7_retry','RUB/completed_one_way_flight',
      'sum(completed_eligible_flights * contracted_rate<=Appendix1_cap * applicable_Appendix6_coefficient); award/budget limit',
      'Awarded route and operator; one recipient per route; different federal subjects; standard endpoint-to-listed-hub; cofinance/Arctic exceptions. Prior-year8000/10000 passengers and exceptions, continuation<=15000 half-cap branch; p5z summer condition explicitly checked. Max1500km or3000km Siberia/FE with exceptions; approved aircraft/seats and fare cap.',
      'Appendix1 by seats/distance; Appendix6 locality and prior-year airport traffic; half-cap if p5d applies; contract and federal budget',
      'Report by15 next month; decision within10 days after receipt; correction5 days then review5 days; payment no later10th working day after decision. Actual receipt and 2027/28 calendar UNKNOWN.',
      'Not industry average per pax; not all domestic routes; do not stack other federal route-subsidy decisions; regional cofinance distinct signed schedule; cash not fare or gross turnover',
      'Published V7 captured2026-11-12; document registered2025-02-04; future contract/version/appropriation UNKNOWN',
      'route_id; operator; award_year; distance;seat_band;prior_year_route_pax;hub/exception;federal_request;cofinance_amount;approved_fare;eligible_dates;report/decision/payment dates')
    add('SUP-SPECIAL','Accessibility/special fare decision22-68866-00363-R Version8','special_fare_rules','RUB/eligible_carried_passenger_one_way',
      'eligible_actual_carried_passengers * route-specific passenger subsidy; contract/budget limit',
      'Exact listed route, passenger categories/registration/documents, special fare, operator agreement and available quota; no generic domestic eligibility',
      'Specific route/passenger tariff and subsidy appendices; not regional per-flight table',
      'Monthly report by15 following month; contract cash schedule and actual receipt UNKNOWN; do not reuse regional10+10 clock without checking this scheme',
      'Carrier cash receipt separate from paid special fare; no double federal reimbursement',
      'Version8 dated2025-11-20; 2027/28 award UNKNOWN',
      'route/passenger category;per-passenger award;fare;eligible_pax;quota;report acceptance;payment date')
    add('SUP-SOCIAL-FE','Social Far East decision22-68861-00481-R','social_fareast_rules','RUB/completed_one_way_flight',
      'eligible_completed_flights * route-specific flight subsidy; contract/budget limit',
      'Exact social route list and award; designated operator/commercial code and special fare; not an unrestricted RW option',
      'Route-specific appendix; scope may require whole awarded route set',
      'Report by15 next month; review10 working days per p3; payment/contract dates require separate verification',
      'Not multiplied by all passengers or duplicated across two federal schemes',
      'Published decision captured2026-11-12; 2027/28 award UNKNOWN',
      'eligible route set; award operator;funding allocation;flight_count;special fare;cash date')
    add('SUP-FUEL-BASE','Net base aviation excise credit','nk200','RUB/eligible_t',
      'eligible_t * 2800*(2.08-1) = eligible_t*3024; gross deduction5824 less accrued excise2800',
      'Registered certified operator; qualifying received kerosene used to fuel operated aircraft; Russian supplier/invoices/uplift registers under Art201p21. Actual qualifying share UNKNOWN.',
      '3024/t is statutory conditional net component at stated law; eligible quantity<=documented qualifying fuel, not automatically model burn',
      'Tax declaration/documents -> verification/offset/refund -> actual bank receipt. Art203 decision within7 days after audit; notice5 days is not total collection lag. Actual RW lag UNKNOWN.',
      'If supplier price already net of credit do not claim again; do not book5824 as net benefit; abroad uplift not automatically qualifying',
      'FNS published2800/t through2028; apply law at tax period and actual eligibility',
      'RW tax registration;received-and-uplifted eligible tonnes;excise accrual;price tax composition;return vs offset;filing/audit/refund dates',value=3024,lower=3024,upper=3024)
    add('SUP-FUEL-DAMPER','Variable aviation kerosene damper','nk200','RUB/eligible_t',
      'max(C_export_alternative-C_domestic_conditional,0) * K_DT_COMP; V_AVIA=rate*eligible_t; monthly statutory rounding',
      'Same operator/document/quantity requirements as base; official monthly source variables required; not a fixed32930/t benefit',
      'No defended numeric forecast bound. Conditional domestic reference67300 in2026,70000 in2027,72800 in2028; these are formula parameters, not airport procurement prices.',
      'Tax claim/verification/offset/refund; future lag UNKNOWN, material working capital',
      'Historical32930.283333 for Jan-Sep2026 is total compensation incl3024; do not add3024 again. Joint fuel-market/FX scenario, not independent price forecast.',
      'Monthly mechanism in captured Art200p21; 2027/28 market variables UNKNOWN',
      'Officialmonthlyexport/netback;K_DT_COMP;FX;taxperiod;eligible_t;declaration/receipt calendar')
    add('SUP-AIRPORT-DISCOUNT','Airport incentives or new-route discount','arh_discounts_2026','RUB/eligible_service_invoice',
      'sum(eligible_invoice_line * individually_confirmed_discount); mutually exclusive rebates reconciled',
      'ARH2026 published policy exists; exact route/new-service/volume terms and contract must be checked. AR2026 PDF404 recorded; no copied network-wide discount assumed.',
      'Only covered eligible service lines; unknown actual discount is not zero evidence or50%default',
      'Invoice reduction or later credit note according to signed terms; cash effect follows settlement',
      'Either reduce cost or record cost rebate once; not extra ticket revenue or government subsidy',
      'ARH policy2026; airport-specific future applicability UNKNOWN',
      'Airport+route;contract;eligible items;discount dates;minimums;credit note/clawback')
    add('SUP-LEASE-FINANCE','Concessional leasing/state-backed finance','plan_common_spec.json','RUB/contract',
      'Contractual scheduled payments and finance costs versus comparable nonconcessional contract',
      'Aircraft/type, lessor agreement, recipient and actual conditions required; production programme announcement not RW cash receipt',
      'UNKNOWN; no subsidy assigned per announced aircraft',
      'Advance/acceptance/monthly instalment/deposit calendar; grace period and guarantee terms UNKNOWN',
      'Do not both reduce lease cost and add same support receipt; purchase/lease/ownership treatments exclusive',
      '2027-2028 and long-term conditional contract',
      'Term sheet;principal;rate;subsidy recipient;grace;guarantee;delivery/acceptance;security deposits')
    add('SUP-INTERNATIONAL','Foreign/charter programme support or guarantee','plan_common_spec.json','LOCAL/contract_or_flight',
      'Only signed eligible support or commercial guaranteed receipts by flight/seat/block with clawback',
      'Destination country/scheme/contract/currency and route rights; no Russian domestic flag shortcut',
      'UNKNOWN for each country/programme; tour-operator guarantee is commercial revenue, not state subsidy',
      'Advance/escrow/receivable/default dates and conversion required',
      'Charter-block payment counted once instead of adding individual ticket sales for same guaranteed inventory',
      'Route/country2027-2028 contract-specific',
      'Scheme legal text;recipient;eligibility;currency;guarantor;settlement;default and refund terms')

def make_register_and_rules():
    assume('P04-A-METRIC-A','Full incremental operating result + separate investing/financing/tax',
      'A','accounting definition','User explicitly confirmed via coordinator message2026-11-12. Aircraft use cost remains in operating result.',
      'plan_common_spec.json',status='USER_CONFIRMED',affected='All economics and cash claims',
      sensitivity='Lease vs own basis changes operating charge and cash timing, not permission to omit aircraft cost',
      refine='Set ownership_basis per tail/contract; disaggregate interest/tax schedules')
    assume('P04-A-REF-MTOW','Airport arithmetic comparator','49.45t;80 departing adults;one billable turn','t;pax;turn',
      '49.45t in pinned author inputs;80pax is a transparent arithmetic probe, not load-factor forecast','author_inputs.json',
      affected='airport_reference_examples.csv only',sensitivity='Cost=(takeoff+security)*MTOW+(terminal+pax_service)*pax',
      refine='Use actual type/registration certified MTOW and dated passenger categories')
    assume('P04-A-NULL','Unknown propagation','null total with known subtotal and exact missing IDs','logic',
      'common_spec unknown!=0 and current user; avoid false all-in budget', 'plan_common_spec.json',
      sensitivity='Resolve missing field or proved upper bound; recompute only affected total',refine='Accepted input manifest per dependent programme')
    assume('P04-A-ELIGIBILITY','Regional summer eligibility','separate no-support / seasonal-supported / exception-year-round branches','branch',
      'Decision V7 appendix p5z wording concerns carriage on route, not only months of payment; independent interpretation required',
      'regional_rules_v7_retry',status='INTERPRETATION_REQUIRES_VALIDATION',
      affected='Supported annual programme fares, demand, result, funding',
      sensitivity='With no established exception keep award=null; no-support branch remains available',
      refine='Validate full rule/version and contract with Rosaviatsiya programme administrator or qualified legal reviewer')
    assume('P04-A-PRICEYEAR','Future cost escalation','UNKNOWN by supplier, currency and year','factor',
      'No source establishes 2027/28 RW contract prices; generic inflation±percent unsupported','plan_common_spec.json',
      sensitivity='Future price ceiling = residual margin/quantity; nominal cash and real diagnostics kept separate',
      refine='Dated quotes or contract escalators; P06 expose price_year and FX')
    assume('P04-A-COUNTERFACTUAL','KEEP and alternatives','full affected-business difference plus opportunity memo','method',
      'Same future period/scenario; cancelled donor economics already included in project-KEEP difference', 'plan_common_spec.json',
      sensitivity='If donor included in delta never subtract again. If new tail: compare feasible alternative, no invented donor.',
      refine='P06/P09 jointly reallocate affected passenger choices/flights/tails/base costs')
    assume('P04-A-FIXTURE','Cash arithmetic counterexample','M0 launch100 capex200 deposit50; monthly R600 variable400 fixed50 use100 D&A20; support50 received+2mo','kRUB',
      'Synthetic arithmetic unit test chosen by P04; no RW cost estimate, no economic recommendation',
      affected='cash_fixture.csv and cash_counterexamples.json only',sensitivity='Move support+2mo; full result unchanged, funding changes',
      refine='Replace every driver by accepted monthly programme inputs; all omitted fixture taxes/interest explicitly0 in synthetic boundary')
    assume('P04-A-THRESHOLD','Decision thresholds instead of invented cost bands','Symbolic headroom/quantity','RUB/unit',
      'Algebraic thresholds conditional on specified known terms; not an empirical plausible range',
      affected='thresholds.csv; no profitability certificate',sensitivity='Joint unknown costs share one headroom; separate maxima cannot be combined',
      refine='Source actual prices then evaluate common monthly engine')
    rules={
      'version':VERSION,'metric_choice':'A','metric_choice_status':'USER_CONFIRMED',
      'input_commits':{'plan':'b4d2ddf690440eb5cd051839cc263cf16b364ca4','author':'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6','five_city':'c18f7640ea36647a05b39089e5293f22dd009f63'},
      'accounting_currency':'RUB nominal by month; retain original currency, FX date, price year and tax basis',
      'comparison':'Project minus future KEEP on same period/fleet-scope/scenario and all affected sales/obligations',
      'unknown_policy':{'CSV':'empty numeric with status=unknown, exact missing field and assumption ID','JSON':'null',
        'totals':'known_subtotal + missing_ids; final_total=null if any required nonzero-quantity component unresolved',
        'zero_allowed':'Only sourced zero or explicitly inapplicable item with applicability evidence; synthetic fixture zero labelled',
        'no_support_branch':'Deliberate counterfactual with award=0; actual award remains UNKNOWN',
        'no_paid_bound':'No unsupported±percent range; historical base/cautious are scenario points, not confidence bounds'},
      'metrics':{
        'variable_contribution_before_support':'R_net - C_flight_variable - C_passenger_variable',
        'variable_contribution_after_eligible_support':'variable_contribution_before_support + S_recognisable_fuel + S_recognisable_route',
        'full_operating_result':'R_net + S_recognisable - C_variable - C_incremental_fixed - C_aircraft_use - D_and_A_owned_or_capex - C_startup_expense - C_exit_expense',
        'incremental_full_result':'full_operating_result_project - full_operating_result_KEEP',
        'post_finance_tax_result':'incremental_full_result - incremental_interest_and_finance_expense - incremental_profit_tax; nullable',
        'project_cash_pre_financing_pre_interest_tax':'customer_cash + support_cash + operating_rebates - gross_operating_cash - capex_cash - advances_cash - deposits_cash + returned_deposits + disposal_cash',
        'project_cash_before_financing':'project_cash_pre_financing_pre_interest_tax - project_interest_cash - project_tax_cash',
        'funding_before_financing':'max(0,-min(cumsum(project_cash_before_financing))) at actual event dates, including pre-launch and wind-down; not annual loss',
        'financing_cash':'equity_cash + debt_draws - debt_principal_repayments - financing_only_fees; interest is already in project_cash_before_financing, do not repeat',
        'post_financing_cash':'project_cash_before_financing + financing_cash',
        'incremental_cash':'cash_project - cash_KEEP; enterprise total and incremental project funding separately labelled',
        'operating_to_cash_bridge':'Operating_result + D&A + noncash_MRO_reserve_expense - actual_MRO_cash_excluded_from_P&L - delta_receivables - delta_inventory - delta_advances - delta_deposits + delta_payables + delta_customer_advances - capex_cash + disposal_cash - interest_cash - tax_cash; reconcile to direct event ledger',
        'reserve_treatment':'If PBH reserve is actually remitted monthly, that payment is cash and must not be added back as noncash. Later maintenance invoice net of reserve setoff/refunds. If accounting reserve only: add back then cash at event.'},
      'aircraft_cost_basis':{
        'cash_operating_lease':'Lease/use charge in operating result; contractual rental cash in cash ledger; purchase capex and owned depreciation absent for same contract',
        'owned':'Depreciation, insurance, maintenance and crew in operating result; purchase/advance in investing cash; principal financing separate',
        'capitalised_lease':'Explicit management/accounting mapping: right-of-use depreciation/use cost, interest separate; liability principal cash; never full rent plus depreciation',
        'existing_aircraft':'Committed common lease/crew remain in both KEEP and project; not cancelled merely because flight cancelled. Show total commitments and avoidable delta.',
        'new_aircraft':'No lost historical donor necessarily; availability/acceptance/induction and alternative use jointly evaluated',
        'reserve':'One physical reserve with dated assignment; cost charged once including idle calendar commitments; availability is not price'},
      'double_count_guards':[
        'One journey fare once; each flown leg consumes seat and incurs physical flight cost.',
        'Aircraft t/hour*blockh and t/cycle must be calibrated as additive decomposition; do not add cycle burn to an already complete total flight burn.',
        'Fuel product + uplift + storage only if separately billed; exclude recoverable VAT from result but track gross VAT cash and recovery.',
        'Deduction5824 includes excise2800 liability: net base benefit3024; gross and net presentations reconcile.',
        'Airport turn charged once at actual airport using billing rules; origin/destination physical movements and landing/takeoff package not blindly duplicated.',
        'Full passenger service versus reduced/no-baggage/transit packages are alternatives. Terminal and passenger service may be separate where tariff says so.',
        'Historical aggregate pax500/650 cannot be added to itemised terminal+service+catering until overlap decomposed.',
        'UFA receive/release is ground service, not a complete engine/airframe PBH reserve; verify scope before combining with MRO contract.',
        'Airport basing133477/month in KHV is aerodrome service, not complete staff/crew/MRO base cost; parking/basing replacement verified by contract.',
        'Once donor contribution is included in all-affected-business project-KEEP, no extra subtraction. Shadow alternative cost is memo, not another cash outflow.',
        'Shared base, reserve, entry cost, support cap and common OD are evaluated once for combined programme, not sum of standalone variants.',
        'Airframe advance offsets final purchase payment; deposit is asset/cash until expense or forfeiture. Capex and depreciation are different ledgers.',
        'Airport rebate either reduces expense or is support credit once; charter guaranteed blocks replace corresponding inventory revenue, not added to it.'
      ],
      'support_eligibility':{
        'three_valued_logic':'true/false/null per test; null never becomes true; no-award sensitivity is separate from actual unknown',
        'required_keys':['scheme_version','operator','award_year','airport_pair','service_regime','eligible_dates','seat_band','distance','fare_cap','award_rate','award_volume','budget_limit','required_documents','cash_schedule'],
        'regional_ordinary':'Different subjects + eligible endpoint/listed hub + distance limit + previous traffic criterion + no overlapping federal route support + admissible calendar + selected operator/contract/volume/fare/budget',
        'seasonal_branch':'Winter-only operations where p5z applies; not merely remove summer subsidy while retaining untested year-round supported programme',
        'year_round_branch':'Requires proven Arctic/FE/remote or requested federal rate<=5%cap exception (and all other criteria) or independently validated applicable contract/rule',
        'p5z_status':'INTERPRETATION_REQUIRES_VALIDATION; rule addresses route carriage, not only payment months; no prohibition of unsubsidised year-round service',
        'new_rule_or_contract':'New pinned evidence version; do not silently substitute historic V7 for future award terms',
        'fuel':'Qualifying received and uplifted fuel registry and excise position; model burnt tonnes only physical proxy; domestic-flight boolean is insufficient'},
      'cash_dates':{
        'ticket':'Booking/payment, merchant/agent settlement, carriage revenue and refund separate; bookings beyond horizon retain liability',
        'regional':'Report<=15 next month -> decision<=10 days -> payment<=10 working days; returned report correction5 days/review5 days; use Russian workday calendar including holidays',
        'fuel_tax':'Actual filing/audit/offset/refund dates; no supported universal1/2/3month bank lag; tax offset is not bank cash',
        'cost':'Order/advance, service/invoice, supplier due and payment date; fixed minima survive cancellation if committed',
        'end_of_horizon':'Include terminal receivables/payables/deposits/refunds/lease return/penalties; do not recognise refunds or liquidate assets at arbitrary horizon',
        'funding':'Use event-level intra-month peak; month-end minimum can understate liquidity. Monthly reporting carries event extrema.'},
      'regional_cash_calendar':{
        'source_id':'regional_rules_v7_retry','source_pages':[6,7],
        'report':{'relative_to':'carriage_month_end','next_month_day_latest':15,'actual_submission_date':None},
        'decision':{'relative_to':'report_received_date','days_max':10,'day_unit':'days_as_written;calendar_classification_requires_legal_calendar_mapping'},
        'payment':{'relative_to':'positive_decision_date','days_max':10,'day_unit':'working_days','actual_bank_credit_date':None},
        'correction':{'carrier_days_max':5,'agency_review_days_max':5,'clock_starts':'actual_return/receipt_dates'},
        'future_applicability':'Needs pinned applicable2027/28rule and agreement; current published deadlines are not unconditional future receipt promise',
        'funding_application':'Use event deadline/actual date per explicit scenario; unresolved report date/workday calendar/award leaves receipt and peak unknown'},
      'scenario_policy':{'base_cautious':'External/scenario definitions, not confidence intervals',
        'joint_fuel':'Procurement fuel, export/netback, FX, statutory credit and qualifying tonnes jointly scenario-defined; isolated rate sensitivity labelled',
        'prices_2027_2028':'Unknown until dated contract/forecast with rationale; 2026 references do not auto-escalate',
        'international':'Costs by country, airport, currency, route corridor, ground handler, fuel and payment regime; separately model charter guarantee/default',
        'delivery':'Monthly aircraft acceptance, induction, crew/MRO readiness and reserve; phased/partial/delayed/no_new separate by type'},
      'dependencies':{'P03':['type/variant/MTOW;blockhour/cycle/tail-month;fuel model;crew and MRO calendar;induction/reserve'],
        'P06_P09':['accepted monthly project+KEEP programme by airport/type;dated physical flights and occupied segments;net journey revenue;donor/restored sales;contract cost mapping;support claims;event payment dates'],
        'P02I_P08I':['international airport/country costs/FX/access/charter contracts and guarantees'],
        'budget_release':'No final RW budget/peak funding without accepted quantities and required price/settlement evidence; publish known subtotal plus affine unknown exposure and thresholds'},
      'assumption_ids':['P04-A-METRIC-A','P04-A-NULL','P04-A-PRICEYEAR','P04-A-COUNTERFACTUAL','P04-A-ELIGIBILITY'],
      'implementation_boundary':'Financial contract and worked arithmetic, not replacement for P06 common engine; no market/network simulation executed here'}
    writejson('cash_rules.json',rules)

def examples():
    rows=[]
    for geo in ['UFA','GOJ','KUF','OMS']:
        rr={r['key']:D(str(r['value'])) for r in COSTS if r['geography_or_airport']==geo and r['status']=='published_offer'}
        movement=(rr['takeoff_landing']+rr['security'])*D('49.45')
        pax=(rr['terminal_domestic']+rr['pax_service_domestic'])*80
        rows.append(dict(example_id='AIRPORT-'+geo,geography_or_airport=geo,price_year=2026,mtow_t=49.45,
          adult_departing_pax=80,movement_and_security_rub=str(movement),terminal_and_pax_rub=str(pax),
          selected_four_items_subtotal_rub=str(movement+pax),full_airport_turn_total='',
          omitted='Other handling/parking/crew/fuel/MRO/VAT; this is not all-in turn price or RW paid rate',
          assumption_id='P04-A-REF-MTOW',source_ids=';'.join(sorted({r['source_id'] for r in COSTS if r['geography_or_airport']==geo}))))
    writecsv('airport_reference_examples.csv',rows)
    assume('P04-A-SUPPORT-PROBE','Regional support progression probe',
      '100 seats;1000km;20 completed one-way flights/month;7 operating months;80pax/flight;coefficient1','seats;km;flights;months;pax;factor',
      'Explicit algebraic probe of primary V7 appendices; not a route proposal, award, passenger forecast or approved budget',
      'regional_rules_v7_retry',affected='support_examples.csv only; candidate repeat-year support risk',
      sensitivity='Prior-year11200 crosses ordinary8000 criterion; eligible continuation<=15000 has half-cap and modified fare; exceptions may change result',
      refine='P06 route calendar/demand; future award and rule; local cofinance/remote status')
    writecsv('support_examples.csv',[
      dict(example_id='REG-CAP-1000KM',case='conditional_standard84_103seat_band_901_1000km',
        completed_one_way_flights=20,months=7,pax_per_flight=80,conditional_annual_carried_segments=11200,
        max_federal_rate_per_flight=244713,cap_coefficient=1,base_special_fare_ceiling=5640,
        maximum_arithmetic_support_for140_flights=34259820,
        meaning='Cap only; award may be absent/lower; must satisfy fare/calendar/prior traffic and all other eligibility',
        source='regional_rules_v7_retry.pdf pp11,12,14,15',assumption_id='P04-A-SUPPORT-PROBE'),
      dict(example_id='REG-REPEAT-YEAR',case='conditional_p5d_continuation_prior_year11200_and_all_other_criteria',
        completed_one_way_flights=20,months=7,pax_per_flight=80,conditional_annual_carried_segments=11200,
        max_federal_rate_per_flight=122356.5,cap_coefficient=1,base_special_fare_ceiling=8460,
        maximum_arithmetic_support_for140_flights=17129910,
        meaning='Half-cap continuation branch<=15000; not automatic award. If exception applies evaluate actual exception. Growth can reduce support cap next year.',
        source='regional_rules_v7_retry.pdf pp11,14footnote,15footnote',assumption_id='P04-A-SUPPORT-PROBE')])
    assume('P04-A-CBR-REFERENCE','Financing-rate reference','Key14%;2027mean12.5-13.5%;2028mean9-10%','percent/year',
      'Bank of Russia23Oct2026 decision and5Nov summary; forecast ranges are policy scenarios, not confidence intervals or RW loan spread',
      'cbr_rate_summary_20261105',affected='Financing cost research; no numerical RW borrowing cost selected',
      sensitivity='interest=sum(daily_debt*(reference_rate+contract_spread)*dayfraction)+fees; spread/floor/tenor UNKNOWN',
      refine='Loan/lease term sheet by currency/date; actual leverage and payment schedule')
    writecsv('finance_reference.csv',[
      dict(reference_id='CBR-20261023',period='2026-10-23 decision',metric='key_rate',value=14,lower=14,upper=14,unit='percent_per_year',
        status='published_policy_rate;not_RW_borrowing_offer',source_id='cbr_rate_summary_20261105',RW_contract_margin='',assumption_id='P04-A-CBR-REFERENCE'),
      dict(reference_id='CBR-2027',period='2027',metric='forecast_average_key_rate',value='',lower=12.5,upper=13.5,unit='percent_per_year',
        status='CBR_conditional_forecast;not_confidence_interval_or_RW_rate_bound',source_id='cbr_rate_summary_20261105',RW_contract_margin='',assumption_id='P04-A-CBR-REFERENCE'),
      dict(reference_id='CBR-2028',period='2028',metric='forecast_average_key_rate',value='',lower=9,upper=10,unit='percent_per_year',
        status='CBR_conditional_forecast;not_confidence_interval_or_RW_rate_bound',source_id='cbr_rate_summary_20261105',RW_contract_margin='',assumption_id='P04-A-CBR-REFERENCE')])
    # Affine thresholds expose unpriced drivers, no invented full budget.
    thresholds=[
      ('TH-FIXED','max_affordable_incremental_fixed_monthly','(R+S-C_variable-C_aircraft_use-D&A-C_launch_exp-C_exit_exp)/active_base_months','RUB/base/month','active_base_months>0; all other terms fixed and defined'),
      ('TH-LAUNCH','max_affordable_one_time_launch_expense','sum(R+S-C_variable-C_fixed-C_aircraft_use-D&A-C_exit_exp)','RUB/launch','Given horizon; not discounted investment threshold or finance capacity'),
      ('TH-MRO','max_affordable_MRO_hourly','(R+S-C_excluding_MRO)/block_hours','RUB/block_h','MRO calendar/cycle fees separately counted; no joint claim all unknowns at separate maxima'),
      ('TH-SUPPORT','required_recognisable_support','C_full_operating-R_net','RUB/period','Compare against eligibility/contract cap; legal cap does not imply award'),
      ('TH-FUEL','max_effective_net_fuel_price','(R+S_nonfuel-C_nonfuel_full)/eligible_consumed_t','RUB/t','Separate nonqualifying fuel and future excise cash; fixed sales arithmetic only'),
      ('TH-FARE','break_even_net_journey_yield','(C_full_operating-S)/unique_sold_journeys','RUB/journey','Fare changes require demand reassignment in P06; no fixed-pax market forecast'),
      ('TH-COFINANCE','minimum_incremental_regional_or_commercial_funding','max(0,required_support-confirmed_federal_support)','RUB/period','Keep no-award baseline; regional cofinance must have its own signed terms'),
      ('TH-FUNDING','required_committed_liquidity','max(0,-min_event(cumsum(project_cash_before_financing)))','RUB','Include prelaunch/exits and terminal liabilities; unknown dates imply unknown peak'),
      ('TH-DELAY','support_delay_extra_bridge_constant_flow','eligible_monthly_support * extra_unpaid_months','RUB','Steady monthly toy flow only; actual event cash path may differ'),
      ('TH-OPTION','new_base_vs_existing_base_operating_headroom','result_before_new_base_costs_new - result_before_extra_costs_existing','RUB/period','Common fleet/KEEP and common input versions; subtract only truly different uncounted costs')]
    writecsv('thresholds.csv',[dict(threshold_id=t,field=f,formula=formula,unit=u,conditions=c,assumption_id='P04-A-THRESHOLD') for t,f,formula,u,c in thresholds])
    # Synthetic fully specified fixture: correct P&L/cash identities, not network acceptance.
    fixture=[]
    cum=D(0);cum_nolag=D(0)
    for m in range(7):
        rev=D(600 if m else 0);var=D(400 if m else 0);fix=D(50 if m else 0);use=D(100 if m else 0)
        da=D(20 if m else 0);support=D(50 if m else 0);startup=D(100 if m==0 else 0)
        capex=D(200 if m==0 else 0);deposit=D(50 if m==0 else 0)
        received=D(50 if m>=3 else 0)
        op=rev+support-var-fix-use-da-startup
        cash=rev+received-var-fix-use-startup-capex-deposit
        cash_nolag=cash+support-received;cum+=cash;cum_nolag+=cash_nolag
        fixture.append(dict(month_index=m,unit='kRUB_SYNTHETIC',revenue=rev,variable=var,fixed=fix,aircraft_use=use,
          depreciation=da,startup_expense=startup,support_accrual=support,support_cash=received,
          capex_cash=capex,deposit_cash=deposit,interest_cash=0,tax_cash=0,financing_cash=0,
          operating_result=op,cash_before_financing=cash,cumulative_cash=cum,cumulative_cash_immediate_support=cum_nolag,
          support_receivable=support*max(0,min(m,2)),assumption_id='P04-A-FIXTURE',status='SYNTHETIC_NOT_RW_ESTIMATE'))
    writecsv('cash_fixture.csv',fixture)
    writejson('cash_counterexamples.json',{
      'scope':'Synthetic exact arithmetic only; no empirical rate/market acceptance',
      'support_lag':{'operating_result_months1to6_kRUB':80,'peak_funding_lag2_kRUB':350,'peak_funding_immediate_kRUB':350,
        'cum_cash_end6_lag2_kRUB':150,'cum_cash_end6_immediate_kRUB':250,
        'interpretation':'Initial launch dominates peak here; delay worsens cash and receivable without automatically changing peak. Counterexample to adding S*lag blindly to total funding.'},
      'intra_month':{'start_cash':0,'day1_supplier_payment':-100,'day28_customer_receipt':100,'month_end_net_cash':0,'actual_peak_funding':100},
      'fuel_net_credit':{'gross_deduction_rub_per_t':5824,'accrued_excise_rub_per_t':2800,'net_base_rub_per_t':3024,'wrong_net_if5824used':2800},
      'existing_lease':{'project_same_common_lease':100,'KEEP_same_common_lease':100,'true_incremental_common_lease':0,
        'interpretation':'Flight cancellation does not release common committed lease100. Show total commitment in both branches.'},
      'own_migration':{'KEEP_old_contribution':100,'project_new_contribution':120,'correct_incremental':20,'wrong_after_second_donor_subtraction':-80},
      'unknown':{'known_subtotal':100,'missing_MRO':None,'correct_total':None,'wrong_total_if_null_coalesced_zero':100},
      'shared_base':{'programme_A_base':50,'programme_B_base':50,'joint_one_base':50,'standalone_sum':100},
      'reserve_vs_invoice':'Monthly paid PBH+full later invoice double counts unless reserve setoff and scope reconciled',
      'history_not_forecast':'2026 simple monthly industry mean is not RW paid amount, fuel-volume-weighted mean, or2027/28 rate',
      'assumption_ids':['P04-A-FIXTURE','P04-A-COUNTERFACTUAL','P04-A-NULL']})

def supporting_tables():
    bands=[('less_than200',None,200,104280,15.7),('201_300',201,300,113643,13.7),('301_400',301,400,132367,11.4),
      ('401_500',401,500,151091,10.1),('501_600',501,600,169816,9.3),('601_700',601,700,188540,8.7),
      ('701_800',701,800,207265,8.3),('801_900',801,900,225989,8),('901_1000',901,1000,244713,7.7),
      ('1001_1100',1001,1100,263438,7.5),('1101_1200',1101,1200,282162,7.4),('1201_1400',1201,1400,310249,7.2),
      ('1401_and_more',1401,None,403871,6.8)]
    writecsv('support_caps_84_103.csv',[dict(band_id=k,distance_lower_km=lo,distance_upper_km=hi,distance_upper_inclusive=(lo is not None),source_boundary_label=k,
      seats='84-103; specific112/cofinance exceptions require rule validation',flight_cap_rub=cap,
      efficiency_rub_per_actual_pax_km=eff,continuation_p5d_cap_factor='0.5',
      source_id='regional_rules_v7_retry',cap_pdf_page=14,efficiency_pdf_page=19,
      caveat='Ceiling not award;distance metric/rounding and boundary200/201 require explicit mapping;territory coefficient separate',
      assumption_id='P04-A-SUP-REGIONAL') for k,lo,hi,cap,eff in bands])
    limits=[2017,2258,2741,3225,3708,4191,4674,5157,5640,6123,6606,7089,7572,8055,8538,9021,9504,9987,10470,10953]
    labels=['less_than200']+[f'{lo}_{lo+99}' for lo in range(201,2001,100)]+['2001_and_more']
    writecsv('support_fare_caps.csv',[dict(band_id=k,base_special_fare_rub=v,p5d_factor='1.5',FarEast_Arctic_factor='1.25 exceptp5d',
      cofinance='Regional adjustment only with documented decision',source_id='regional_rules_v7_retry',pdf_page=15,
      caveat='Eligible product fare constraint;do not treat as realised net yield;tax/fees/product terms separately mapped',
      assumption_id='P04-A-SUP-REGIONAL') for k,v in zip(labels,limits)])
    eligibility=[
      ('EL01','effective_rule_and_award_year','All supported branches','Version and year match applicable programme/contract; current public2025/26 evidence not2027/28award','UNKNOWN future','1-5'),
      ('EL02','selected_operator_contract_budget','All supported branches','One recipient per route;selected operator and agreement;remaining budget/flight volume','UNKNOWN RW2027/28','6-7'),
      ('EL03','different_federal_subjects','Regional','Both endpoints in different subjects','NULL if unresolved geography','11p5a'),
      ('EL04','endpoint_hub_or_exception','Regional','Ordinary endpoint-to-listed hub;cofinance/Arctic exception not inferred from proximity500km','NULL if unproven exception','9p1;11p5b'),
      ('EL05','distance_or_exception','Regional','<=1500km general;<=3000km Siberia/FE;cofinance/intraFE exception','NULL if route distance/regime unknown','11p5c'),
      ('EL06','prior_year_traffic_or_exception','Regional','8000 both directions general;10000FE;exact cofinance/remote exceptions;continuation<=15000 separately','NULL if prior-year flow unknown','11p5g/p5d'),
      ('EL07','summer_carriage_condition','Regional','No May-Sep carriage for ordinary branch;Arctic/FE/remote or federal_request<=5%cap exception','INTERPRETATION_REQUIRES_VALIDATION','12p5z'),
      ('EL08','other_federal_scheme_overlap','Regional','Exclude overlapping federal route subsidy;other independent fuel-tax mechanism mapped separately','NULL if allocation unknown','11p5e'),
      ('EL09','seat_type_route_cap','Regional','Aircraft certified/operator-authorised and contracted seats;Appendix1 cap;Appendix6 coefficient;half-cap ifp5d','NULL if aircraft/award not specified','6p2;7p6;14;20'),
      ('EL10','special_fare_and_product','Regional','Appendix2 ceiling with applicable factors;actual net revenue and demand consistent with sellable product','NULL if fare contract unclear','15'),
      ('EL11','completed_eligible_flights_and_claims','Regional','Only completed eligible flights within approved dates/volume;monthly report and supporting cofinance documents','NULL if operation/claim absent','6-7'),
      ('EL12','efficiency_and_clawback','Regional','Monitor actual subsidy/RPK threshold and compliance;contract may change or funds returned','NULL until monthly realised metrics','10-11;13;19'),
      ('EL13','no_award_business_branch','Unsubsidised','Set support0 explicitly in diagnostic;year-round unsubsidised routes remain business options','NOT_A_CLAIM_OF_NO_LEGAL_SUPPORT','scope interpretation')]
    writecsv('support_eligibility_rules.csv',[dict(rule_id=i,field=f,applies_to=a,test=t,unknown_handling=u,source_id='regional_rules_v7_retry',pdf_pages=p,
      assumption_id='P04-A-ELIGIBILITY') for i,f,a,t,u,p in eligibility])
    # One exhaustive budget interface generated from the unpriced cost driver inventory.
    budget=[]
    for r in COSTS:
        if r['cost_id'].startswith('UNK-'):
            budget.append(dict(budget_component_id=r['cost_id'],component=r['key'],aircraft_type=r['aircraft_type'],
              quantity_field=r['driver'],rate_field=r['cost_id'],unit=r['unit'],P_and_L_ledger=r['ledger'],
              monthly_project_quantity='',monthly_KEEP_quantity='',applicability='UNKNOWN_until_programme_contract_mapping',
              rate='',known_subtotal='',full_total='',missing_reason=r['refinement'],
              double_count_guard=r['overlap_guard'],assumption_id=r['assumption_id']))
    writecsv('budget_components.csv',budget)
    cities=json.loads((ROOT/'inputs/plan_variant_research_plan.json').read_text())['seed_cities']
    coverage=[]
    for c in cities:
        a=c['iata'];known=a in ['UFA','GOJ','KUF','OMS','KHV']
        coverage.append(dict(airport=a,coverage='SELECTED_LOCAL_PRIMARY_ITEMS' if known else 'LOCAL_RATE_NOT_EXTRACTED_IN_P04',
          future_2027_2028='UNKNOWN_contract_escalator',fuel='UFA_public_reference_only' if a=='UFA' else 'UNKNOWN_local_fuel',
          base_staff_MRO='UNKNOWN',contract_discount='UNKNOWN',cash_terms='UNKNOWN',
          next_source='Airport dated price list plus RW SGHA/fuel/MRO/base contracts',
          decision_rule='Exact unknown terms remain parametric; absence of extracted price does not reject airport'))
    writecsv('airport_coverage.csv',coverage)
    questions=[dict(question_id='P04-Q001',source='common_spec.metric_policy; requirements.R11; user/coordinator2026-11-12',
      quote='incremental_full_result; monthly_and_cumulative_cash; peak_funding',
      interpretations='A operating result+separate investment/finance/tax; B after interest/tax under assumed contracts',
      recommended_temporary_resolution='A; use charge in operating result; capex/advance/finance/tax separate',
      status='USER_CONFIRMED',answer='User explicitly confirmed A through coordinator; confirmed in current turn',
      affected='P06/P09/P10; all money metrics',continuing_work='All cost/support/cash research',assumption_id='P04-A-METRIC-A'),
      dict(question_id='P04-Q002',source='Rosaviatsiya22-64160-00191-R Version7; PDFp12 appendixp5z; p6p1 contract/budget; p9 definitions; p11-12 exceptions',
      quote='перевозки по маршрутам не осуществляются в период с мая по сентябрь в год предоставления субсидии',
      interpretations='Literal route-carriage restriction; author baseline only no-summer-payment7/12',
      recommended_temporary_resolution='No-award/no-support; eligible seasonal-supported; year-round-supported only proven exception/validated contract. No general ban on year-round unsubsidised routes.',
      status='INTERPRETATION_REQUIRES_VALIDATION',answer='Coordinator confirms legal-validation issue, not user vote',
      affected='Supported annual calendar, eligible fares/demand, result, cash',continuing_work='No-support and local cost thresholds continue',
      addressee='Rosaviatsiya regional subsidy programme administrator / qualified independent legal reviewer',
      preamble='Within federal budget obligations and agreements; one recipient per route; decision governs regional passenger-transport subsidy',
      exceptions='Arctic / FarEast / Appendix4 remote settlement / requested federal one-way rate<=5% Appendix1 cap; all other eligibility still applies',
      edition_validity='V7 registered04.02.2025; official page captured12.11.2026; explicit sunset not identified; future2027/28 version/agreement must be verified',
      assumption_id='P04-A-ELIGIBILITY')]
    writecsv('clarification_requests.csv',questions)
    writecsv('dependency_requests.csv',[
      dict(request_id='P04-D01',to='P03',fields='type/variant MTOW;dated block_h/cycles;tankering/fuel;crew/MRO/induction/reserve calendar',
           purpose='Cost quantities and type separation',without='Rates remain input references; total fuel/crew/resource cost UNKNOWN',acceptance='exact commit+manifest+units+period'),
      dict(request_id='P04-D02',to='P06/P09',fields='Monthly programme and same-scenario futureKEEP: physical flights by airport/type;journey revenue;occupied segments;tail/base months;changed/donor business;invoice/cash calendar',
           purpose='Full budget and money bridge',without='Final programme budget, funding and break-even month UNKNOWN; formulas/interface usable now',acceptance='exact commit+manifest; joint programme recomputed not sum'),
      dict(request_id='P04-D03',to='Programme owner/airline expert',fields='RW lessor/MRO/crew/base/SGHA contracts;support award/claim register;settlement and tax position',
           purpose='Replace unbounded unknown rates and cash lags',without='Use symbolic thresholds not invented bounds',acceptance='Redacted field-level evidence; no secrets in artifacts'),
      dict(request_id='P04-D04',to='P02I/P08I',fields='Country/airport foreign fuel/handling/ANSP FX/access and insurance;charter guarantee/advance/default terms',
           purpose='Additional international/mixed-fleet budget distinct from CASE_SJ',without='Foreign costs and programme cash remain UNKNOWN',acceptance='exact currency/year/regime and contract/source receipt')])
    writecsv('variant_proposals.csv',[
      dict(proposal_id='P04-V01',parent_ids='RADIAL_BASE;TRANSFER_HUB;EXISTING_BASE_DIRECT',change_type='REVISE_MATCHED_COST_COMPARISON',
        evidence='GOJ/KUF/UFA/OMS local tariffs; airport_reference_examples.csv',
        mechanism='One UFA basket masks local monetary differences; use identical flight/MTOW/pax with local items and separately unknown base/MRO',
        test='Recompute cost-sensitive common-fleet candidates with local billable basket, not airport multiplier±20%',
        result_scope='Cost decomposition; no city selected/rejected or market forecast',critical_unknowns='Full contracts;future prices;extra base and MRO',
        revisit='Accepted monthly programme input',shared_input_change='PROPOSAL_ONLY; coordinator pins'),
      dict(proposal_id='P04-V02',parent_ids='all_route_supported_variants',change_type='SPLIT_ELIGIBILITY_AND_CASH_BRANCHES',
        evidence='regional_rules_v7_retry pp6/7/11/12/14/15/20',
        mechanism='Supported seasonal or exception-year-round changes fare/cash path and competing no-award choice',
        test='Joint seasonal operations+special fare+award cap+cash lag versus no-support product; do not hold fare/demand fixed as forecast',
        result_scope='Conditional legal/financial branches; not proof support will be awarded',critical_unknowns='P04-Q002;future award;fare/product demand',
        revisit='New law/contract version or award',shared_input_change='PROPOSAL_ONLY; coordinator pins'),
      dict(proposal_id='P04-V03',parent_ids='new_base_vs_existing_chain;MIXED',change_type='ADD_STAGED_COMMITMENT_TEST',
        evidence='Unknown entry/exit/lease/deposit terms; full budget contract and thresholds.csv',
        mechanism='Staged commitment may reduce prelaunch peak/exit cost even when operating result is unchanged',
        test='Same monthly flights/demand then dated entry/advance/lease covenants; fixed programme vs feasible staged adaptation separately',
        result_scope='Hypothesis to test; no unsourced savings amount',critical_unknowns='Quotes;notice periods;minimum terms',
        revisit='Term sheet and monthly programme',shared_input_change='PROPOSAL_ONLY; coordinator pins')])

def main():
    make_costs();make_support();make_register_and_rules();examples();supporting_tables()
    writecsv('cost_ranges.csv',COSTS);writecsv('support_terms.csv',SUPPORT)
    old=list(csv.DictReader((ROOT/'inputs/plan_assumptions_register.csv').open()))
    old_by_parameter={r['parameter']:r['assumption_id'] for r in old}
    legacy=[]
    for row in csv.DictReader((ROOT/'inputs/author_network.csv').open()):
        if row['parameter'].startswith('subsidy_') or row['parameter']=='fuel_compensation_rub_per_t':
            aid='P04-A-HISTORY-'+row['parameter']
            assume(aid,row['parameter'],f"base={row['base']};cautious={row['cautious']}",row['unit'],
              'Pinned author value only; current model must apply scheme-specific eligibility/quantity/cap/cash. No automatic admission.',
              'author_network.csv',affected='Historical lineage only; not current forecast',
              sensitivity='Replace flat points with support_terms and eligibility branches; do not silently rewrite baseline',
              refine='Future award/contract and monthly eligible operations',selected_by='Historical author model; exact parameter author UNKNOWN')
            legacy.append(dict(**row,assumption_id=aid,admission='HISTORICAL_ONLY_NOT_FUTURE_RATE',prior_plan_assumption_id=old_by_parameter.get(row['parameter'],'')))
    writecsv('historical_support_points.csv',legacy)
    writecsv('assumption_changes.csv',[dict(assumption_id=a['assumption_id'],prior_plan_assumption_id=old_by_parameter.get(a['subject'].removeprefix('HIST-'),''),
      action='ADD_VERSIONED_DETAIL_OR_MISSING_FIELD; DO_NOT_OVERWRITE_PLAN',
      change=a['change'],approval_status=a['approval_status'],source_id=a['source_id']) for a in ASSUMPTIONS])
    writecsv('cost_assumptions.csv',ASSUMPTIONS);writejson('cost_assumptions.json',ASSUMPTIONS)
    writecsv('assumption_ids.csv',[{'assumption_id':a['assumption_id']} for a in ASSUMPTIONS])
    print(json.dumps({'cost_rows':len(COSTS),'support_schemes':len(SUPPORT),'assumptions':len(ASSUMPTIONS)}))

if __name__=='__main__':main()
