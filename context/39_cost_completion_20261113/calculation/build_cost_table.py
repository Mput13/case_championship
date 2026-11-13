#!/usr/bin/env python3
"""P39 offline integration of completed handoffs; Python standard library only.

All output is confined to this script's directory. No old exporter is imported.
UNKNOWN is None internally, explicit UNKNOWN in CSV, null in JSON.
"""
from pathlib import Path
import csv
import json
import re
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict

HERE = Path(__file__).resolve().parent
INPUT = HERE.parent
OUTPUTS = ['COST_TABLE.csv', 'RESULT.md', 'ASSUMPTIONS.md', 'workings.json']
P38_ANNUAL = 'model_audit/snapshot/56400c5f/context/38_direct_strategy_20261113/economics/annual_results.selected.csv'
STATUS = {
    'FULL_IN_MODEL': ('FULL', 'Полностью учтена названная модельная формула'),
    'PARTIAL': ('PARTIAL', 'Учтено частично; остаток неизвестен'),
    'ABSENT': ('ABSENT', 'Статья отсутствует в формуле; сумма неизвестна'),
    'UNRESOLVED_BASKET': ('UNRESOLVED', 'Нерасшифрованная корзина; пересечение не разрешено'),
}


def read(name):
    with (INPUT/name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def number(value):
    return None if value in ('', 'UNKNOWN', 'NULL', None) else float(value)


def money(value):
    return None if value is None else float(Decimal(str(value)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))


def product(price, quantity):
    return None if price is None or quantity is None else money(price*quantity)


def strict_sum(values):
    return None if any(x is None for x in values) else sum(values)


def cell(value):
    if value is None:
        return 'UNKNOWN'
    if isinstance(value, (dict,list)):
        return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False)
    return str(value)


def ref(name, line):
    return '../'+name+':'+str(line)


def resolve_ref(value):
    match = re.fullmatch(r'(.+):(\d+)', value)
    return bool(match and (HERE/match[1]).is_file() and 0 < int(match[2]) <= len((HERE/match[1]).read_text(encoding='utf-8-sig').splitlines()))


COVERAGE = {(r['item_id'],r['network']):(i,r) for i,r in enumerate(read('model_audit/coverage.csv'),2)}
DRIVERS = {(r['model'],r['network'],r['scenario'],r['item_id']):(i,r) for i,r in enumerate(read('model_audit/annual_drivers.csv'),2)}
EXPOSURE = {(r['model'],r['network'],r['scenario'],r['scope'],r['metric']):(i,r) for i,r in enumerate(read('model_audit/exposures.csv'),2)}
PRICES = {r['id']:(i,r) for i,r in enumerate(read('omsk_price_recovery/prices.csv'),2)}
FLEET = {r['stableID']:(i,r) for i,r in enumerate(read('research_fleet/price_evidence.csv'),2)}
LEASE = {r['id']:(i,r) for i,r in enumerate(read('fleet_price_recovery/prices.csv'),2)}

PRICE_MAP = {
    'GROUND_DETAIL':['REF-LAND','REF-SEC','REF-PAX'],
    'MRO_LINE':['MRO-LINE-RRJ','MRO-TOOLS'],
    'MRO_HEAVY':['MRO-HEAVY-RRJ','TECH-RESERVE-HIST-RUB'],
    'ENGINE':['MRO-ENGINE-RESERVE-SAM146','MRO-SJPD8','TECH-RESERVE-HIST-RUB'],
    'SPARES_USE':['MRO-ROTABLE-SPARES','MRO-AOG-LOGISTICS'],
    'SPARES_STOCK':['MRO-ROTABLE-SPARES'],
    'CREW_FIXED':['CREW-ADDL'], 'CREW_TRAIN':['CREW-TRAVEL'],
    'CREW_POSITION':['CREW-TRAVEL','OMS-CITYBUS'],
    'LEASE_WORK':['LEASE-RW-2027','LEASE-HIST-RUB','LEASE-HIST-USD','FLEET-LEASE-SJPD8'],
    'LEASE_RES':['LEASE-RW-2027','LEASE-HIST-RUB'],
    'CAPITAL':['FLEET-LEASE-SJPD8'], 'FERRY':['DONOR-FERRY'],
    'PARKING':['OMS-BASE-30–74.999 т','OMS-BASE-75–99.999 т','OMS-PARK-H-30–74.999 т','OMS-PARK-H-75–99.999 т','OMS-PARK-D-30–74.999 т','OMS-PARK-D-75–99.999 т','REF-PARK-EXCESS'],
    'CREW_HOTEL':['CREW-TRAVEL','ANALOG-HOTEL-SINGLE','ANALOG-HOTEL-DOUBLE'],
    'INSURANCE':['INS-RW-2027'],
    'OVERHEAD':['OMS-WH-11.19.1','OMS-WH-11.19.2','OMS-RACK','OMS-IT-TGM-IN','OMS-IT-TGM-AV','UNKNOWN-OFFICE','UNKNOWN-DCS','UNKNOWN-IT','UNKNOWN-SALARY','MRO-WAREHOUSE'],
    'DISTRIBUTION':['LAUNCH-SALES'],
    'DISRUPT':['ANALOG-HOTEL-SINGLE','ANALOG-HOTEL-DOUBLE','ANALOG-MEAL-DELTA','OMS-CITYBUS','OMS-MEAL-DISTR'],
    'OMS_SETUP':['OMS-PASS-PERM','OMS-PASS-OUT','OMS-PASS-ONCE','OMS-ESCORT','UNKNOWN-GSE','UNKNOWN-DCS','MRO-TOOLS','LAUNCH-SALES'],
    'TRANSFER':['OMS-BAG'], 'DONOR':['DONOR-FERRY'],
    'DEPOSITS':['OMS-CONTRACT'],
}

# These are derivatives/sensitivities to an unknown unit, never invented prices.
UNITS = {
    'FUEL':('fuel_burn','RUB/t burned'), 'UPLIFT':('fuel_burn','RUB/t burned; uplift tonnes UNKNOWN'),
    'CREDIT':('fuel_burn','RUB/t burned; eligibility UNKNOWN'),
    'GROUND':('departures','RUB/physical departure'),
    'GROUND_DETAIL':('departures','RUB/physical departure; billed turns UNKNOWN'),
    'PAX':('passenger_segments','RUB/boarded segment'),
    'MRO_PROXY':('block_hours','RUB/BH'), 'MRO_LINE':('block_hours','RUB/BH'),
    'MRO_HEAVY':('block_hours','RUB/BH'), 'ENGINE':('block_hours','RUB/BH'),
    'SPARES_USE':('block_hours','RUB/BH'), 'NAV':('block_hours','RUB/BH'),
    'DEICE':('departures','RUB/physical departure allowance'),
    'CREW_PROXY':('block_hours','RUB/BH'),
    'DISTRIBUTION':('journeys','RUB/endpoint journey; channel volume UNKNOWN'),
    'TICKET_VAT':('journeys','RUB/endpoint journey; taxable gross UNKNOWN'),
    'MIGRATION':('journeys','RUB/endpoint journey; affected own journeys UNKNOWN'),
    'GRANT':('departures','RUB/departure; eligibility UNKNOWN'),
}
UNKNOWN_FORMULAS = {
    'CREDIT_CASH':'Eligible_tonnes * approved_credit; cash_peak = dated_tax_receivable - collected_credit; eligible tonnes/dates UNKNOWN',
    'VAT':'Expense = unrecoverable_invoice_VAT; WC = recoverable_VAT * actual_cash_lag; invoice_tax/recovery/lag UNKNOWN',
    'SPARES_STOCK':'Stock_cash = sum(stock_SKU_qty * signed_unit_price); refundable_pool_deposit separately; annual_consumption in SPARES_USE',
    'CREW_FIXED':'FTE = sum(posts * coverage_hours) / effective_paid_hours; annual_payroll = sum(paid_FTE_months * loaded_payroll_per_month) - allocated_existing_crew_proxy',
    'CREW_TRAIN':'Launch = entrants * initial_course_quote; recurrent = staff * courses_per_year * recurrent_quote; FTE/counts/quotes UNKNOWN',
    'CREW_POSITION':'sum(crew_trips * ticket_quote + person_days * allowance + ordered_bus_begun_hours * 3430); roster/trips UNKNOWN',
    'LEASE_WORK':'sum(working_tail_billed_months * signed_rent); actual months/rent UNKNOWN; fullPnL classification versus incremental cash and donor D separately',
    'LEASE_RES':'sum(reserve_tail_billed_months * signed_standby_rent); one R1 already in fleet; share/location/terms UNKNOWN',
    'CAPITAL':'CAPEX = tail_qty * purchase_quote; annual_depreciation + interest per policy; refundable_deposit and finance_cash separately; mutually exclusive with renting same service',
    'FERRY':'sum(uncovered_dated_ferry_BH * (burn_rate*net_fuel + MRO + nav) + ferry_departures*(ground+deice)); ferry plan/overlap UNKNOWN',
    'PARKING':'Choose ONE billing rule: monthly_rate * billed_aircraft_months OR hourly_rate * eligible_hours OR daily_rate * eligible_days; free_window, tail_location, MTOW, existing_ground_share UNKNOWN',
    'CREW_HOTEL':'sum(actual_room_nights * contracted_room_rate + person_days * per_diem); room_nights/roster UNKNOWN; aircraft_nights are not rooms',
    'INSURANCE':'sum(tail_policy_periods * signed_premium); allocated existing fleet premium versus incremental endorsement; price UNKNOWN',
    'OVERHEAD':'Station annual = FTE_months*wage + premises_months*rent + IT/support + storage_m2_months*330_or_1000 + ordered_workplace_flights*1229.51; scope/quantities/overlap UNKNOWN',
    'REFUNDS':'sum(event_affected_tickets * residual_refund_or_compensation) net of reversed revenue, saved variable expense and existing provisions; events/liabilities UNKNOWN',
    'DISRUPT':'Affected_OMS_transfer_journeys = transfer_journeys * affected_fraction; hotel = affected * nights/occupancy * room_rate; meal+transport+rebooking separate UNKNOWN; no assumed disruption frequency',
    'OMS_SETUP':'Launch expense + CAPEX + refundable deposit + advance + stock separately, each signed_BoQ_qty * quote; ownership and provider-included scope UNKNOWN',
    'TRANSFER':'Extra_bag_service_cost = ordered_extra_services * 4450; annual sensitivity = OMS_departures * services_per_OMS_departure * 4450; bags, services and ground overlap UNKNOWN',
    'CANCEL_OLD':'sum(action_specific_penalties + unavoidable_old_minima - proven_avoidable_costs); old contracts/actions UNKNOWN; not automatic rent/payroll savings',
    'DONOR':'External_D = removed_donor_revenue - actually_avoidable_donor_expense - already_in_joint_delta; signed_retained/removed_jobs UNKNOWN; noncash opportunity, not invoice',
    'DEPOSITS':'Advance_cash = next_service_volume * prepayment_share; working_capital_peak = max_t(cumulative_outflows - inflows); refundable_deposit/stock separate; dates/amounts UNKNOWN',
}


def exposure(t, metric, scope='NETWORK'):
    if metric=='block_hours' and t['model']=='P38':
        metric = 'block_hours_departure_attributed'
    return EXPOSURE.get((t['model'],t['network'],t['scenario'],scope,metric))


def value(t, metric, scope='NETWORK'):
    r = exposure(t, metric, scope)
    return number(r[1]['value']) if r else None


def source_meta(sid):
    if sid in PRICES:
        i,r = PRICES[sid]
        return {'id':sid,'value_min':number(r['min']),'value_max':number(r['max']),
                'unit':r['unit'],'currency':r['currency'],'date':r['effective'],'tax':r['tax'],
                'admission':r['classification'],'source':r['source'],'locator':r['page'],
                'reliability':r['provenance'],'limits':r['overlap'], 'ref':ref('omsk_price_recovery/prices.csv',i)}
    if sid in LEASE:
        i,r = LEASE[sid]
        return {'id':sid,'value':r['exact_amount'],'unit':r['unit'],'currency':r['currency'],
                'date':r['effective_date'],'tax':r['tax'],'admission':r['status'],
                'source':r['source'],'locator':r['locator'],'reliability':r['reliability'],
                'limits':r['analog_limits'],'ref':ref('fleet_price_recovery/prices.csv',i)}
    if sid in FLEET:
        i,r = FLEET[sid]
        return {'id':sid,'value':r['value/range+currency'],'unit':r['units'],'date':r['effective_date'],
                'tax':r['tax'],'admission':'HISTORICAL_OR_UNKNOWN_NOT_2027_QUOTE',
                'source':r['primaryURL'],'locator':r['excerpt'],'reliability':r['confidence/scope'],
                'limits':r['analog_derivation'],'ref':ref('research_fleet/price_evidence.csv',i)}
    if sid=='TECH-RESERVE-HIST-RUB':
        return {'id':sid,'value_inclVAT18':2874480,'value_exVAT18':2436000,
                'unit':'RUB/aircraft-month','date':'2015-04-22; court2021-04-15',
                'tax':'historical VAT18%; VAT438480','admission':'HISTORICAL_OVERLAP_ONLY',
                'source':'https://sudact.ru/arbitral/doc/P6tWcgW0i6Jj/','locator':'§11.2; coordinator root check',
                'reliability':'coordinator completed primary-text check; signed scope UNKNOWN',
                'limits':'Not added over MRO35000/55000; refundability/expense classification UNKNOWN',
                'ref':ref('coordinator/source_admission.md',5)}
    if sid=='OMS-CONTRACT':
        return {'id':sid,'date':'generic2026; signed_RW_UNKNOWN','unit':'100% prepayment of ordered service',
                'tax':'UNKNOWN','admission':'TERMS_ONLY_NO_AMOUNT',
                'source':'../omsk_price_recovery/sources/oms_contract.pdf','locator':'p8 §§6.1/6.7.1',
                'reliability':'primary generic contract; RW signed terms UNKNOWN',
                'limits':'Cash advance, not new expense','ref':ref('omsk_price_recovery/excerpts/contract_verified.txt',4)}
    raise KeyError(sid)


def scenario(name, unit_min=None, unit_max=None, quantity=None, unit='UNKNOWN',
             source='MODEL_AUDIT', basis='UNKNOWN unit/quantity: formula only', group='',
             gate='CONDITIONAL: signed scope, quantity, tax and nonoverlap required', period='annual sensitivity'):
    return {'name':name, 'unit_min':unit_min,'unit_max':unit_max,'unit':unit,'quantity':quantity,
            'period':period,'formula':'unit_price * quantity', 'full_service_min_rub':product(unit_min,quantity),
            'full_service_max_rub':product(unit_max,quantity),'addition_rub':None,
            'price_source_id':source,'basis':basis,'exclusive_group':group,'addition_gate':gate}


def sensitivities(item,t,c):
    s=[]
    if item in UNITS:
        metric, unit = UNITS[item]
        q=value(t,metric)
        s.append(scenario('derivative_per_1_RUB_not_a_quote',1,1,q,unit,
                          basis='Нормированный коэффициент: изменение unit на 1 RUB × actual model exposure. Это не цена услуги и не принятая добавка.'))
    if item in ('LEASE_WORK','LEASE_RES'):
        q=c['working_months_stress'] if item=='LEASE_WORK' else c['reserve_months_stress']
        s.append(scenario('2015_RUB_nominal_benchmark_no_indexation',7560000/1.18,7560000/1.18,q,'RUB exVAT18 / aircraft-month',
                          'LEASE-HIST-RUB','Все соответствующие model tails условно оплачиваются 12 месяцев; реальные billed months UNKNOWN. 2015 RUB номинально, без индексации; не бюджет2027.',
                          'aircraft_ownership_or_rent',period='12 retained billing months stress, not 52/48 weeks conversion'))
    elif item=='MRO_HEAVY':
        s.append(scenario('2015_technical_reserve_full_service_overlap_unknown',2436000,2436000,c['all_fleet_months_stress'],
                          'RUB exVAT18 / aircraft-month','TECH-RESERVE-HIST-RUB',
                          '2015 technical reserve, full fleet stress; no assignment to heavy/engine costs until signed scope; shown ONCE under MRO_HEAVY.',
                          'MRO_PROXY_HEAVY_ENGINE_SPARES',gate='DO_NOT_ADD before scope; replace matching MRO/reserve or only documented uncovered residual'))
    elif item=='OVERHEAD':
        for sid in ['OMS-WH-11.19.1','OMS-WH-11.19.2']:
            p=PRICES[sid][1];u=number(p['min'])
            s.append(scenario('10_m2_storage_12_months_'+sid,u,u,120,'RUB preVAT / m2-month',sid,
                              'На10 м² хранения имущества в OMS ×12месяцев. Не офис/ангар/самостоятельный склад; area/term UNKNOWN.', 'OMS_storage_heated_or_unheated'))
        s.append(scenario('one_informing_workplace_per_OMS_departure',1229.51,1229.51,c['OMS_departures'],
                          'RUB preVAT / workplace-flight','OMS-RACK','Один заказанный пост информирования на каждое фактическое OMS departure, только sensitivity; НЕ DCS/check-in.'))
        for sid,u in [('OMS-IT-TGM-IN',6.23),('OMS-IT-TGM-AV',55.6)]:
            s.append(scenario('per_one_message_'+sid,u,u,1,'RUB preVAT / telegram',sid,
                              'На1 заказанную телеграмму; годовое число сообщений UNKNOWN; не DCS/broadband.',period='per-one-message coefficient'))
    elif item=='TRANSFER':
        s.append(scenario('one_extra_bag_service_per_OMS_departure',4450,4450,c['OMS_departures'],
                          'RUB preVAT / additional ordered service','OMS-BAG',
                          'Ровно1 дополнительное обслуживание на каждый OMS departure, НЕ базовая частота/не kg/не bag per pax. Для DIRECT/P38 это только заказанная операция в OMS, не новый transfer product.'))
    elif item=='PARKING':
        q=c['working_months_stress'] if t['model']=='OWNER' and t['network']=='OMS' else 12
        for bracket in ['30–74.999 т','75–99.999 т']:
            for scheme in ['BASE','PARK-H','PARK-D']:
                sid='OMS-'+scheme+'-'+bracket;p=PRICES[sid][1];u=number(p['min'])
                n=q if scheme=='BASE' else 1
                desc=('Рабочий парк OMS ×12 условных оплачиваемых месяцев; reserve отдельно, место UNKNOWN.' if t['model']=='OWNER' and t['network']=='OMS'
                      else 'Нормировка: один условный борт в OMS на12 оплачиваемых месяцев; не весь сетевой парк.') if scheme=='BASE' else 'На1 eligible оплачиваемый час/сутки; годовая длительность и free window UNKNOWN.'
                s.append(scenario('OMS_'+scheme+'_'+bracket,u,u,n,p['unit']+' preVAT',sid,desc,
                                  'parking_billing_choice',period='annual conditional fleet-months' if scheme=='BASE' else 'unit sensitivity, not annual quantity'))
        if t['model']=='OWNER' and t['network']=='OMS':
            s.append(scenario('OMS_all_fleet_30_74_monthly_if_reserve_based_OMS',117100,117100,c['all_fleet_months_stress'],
                              'RUB preVAT / aircraft-month','OMS-BASE-30–74.999 т','Альтернатива whole fleet: рабочие+УЖЕ существующий1reserve, только если весь парк базируется OMS.',
                              'parking_billing_choice'))
    elif item=='DISRUPT':
        q=.01*c['transfer_journeys']
        s.append(scenario('one_percentage_point_transfer_one_night_single',4100,4100,q,
                          'published RUB tax UNKNOWN / room-night','ANALOG-HOTEL-SINGLE',
                          'На1 процентный пункт model transfer journeys ×1ночь ×single occupancy. Ожидаемая частота UNKNOWN; дробные room-nights — коэффициент, booking нужен integer event roster.', 'hotel_occupancy_choice'))
        s.append(scenario('one_percentage_point_transfer_one_night_double',4650,4650,q/2,
                          'published RUB tax UNKNOWN / room-night','ANALOG-HOTEL-DOUBLE',
                          'На1п.п. transfer journeys ×1ночь /2чел. в номере; допустимо только при double occupancy; не цена per passenger.', 'hotel_occupancy_choice'))
        s.append(scenario('one_begun_bus_motorhour',3430,3430,1,'RUB preVAT / begun motorhour','OMS-CITYBUS',
                          'На1 начатый моточас; вместимость/маршрут/подача/число автобусов UNKNOWN, per-pax цена не выводится.',period='unit coefficient; annual motorhours UNKNOWN'))
        s.append(scenario('one_meal_distribution_service_no_food',3275,3275,1,'RUB preVAT / service','OMS-MEAL-DISTR',
                          'На1 обслуживание раздачи; цена рациона UNKNOWN. Пакетный breakfast delta950 не standalone meal quote.',period='unit coefficient; annual services UNKNOWN'))
    elif item=='CREW_HOTEL':
        for sid,u in [('ANALOG-HOTEL-SINGLE',4100),('ANALOG-HOTEL-DOUBLE',4650)]:
            s.append(scenario('one_room_night_'+sid,u,u,1,'published RUB tax UNKNOWN / room-night',sid,
                              'OMS local2026 analogue; на1номер-ночь, не aircraft night; размещение экипажей и других городов UNKNOWN.', 'crew_hotel_occupancy_choice',period='unit coefficient; annual roster UNKNOWN'))
    elif item=='CREW_POSITION':
        s.append(scenario('one_ordered_bus_motorhour',3430,3430,1,'RUB preVAT / begun motorhour','OMS-CITYBUS',
                          'Только локальная операция OMS; число экипажных рейсов/автобусов/моточасов UNKNOWN.',period='unit coefficient; annual roster UNKNOWN'))
    elif item=='OMS_SETUP':
        for sid,u in [('OMS-PASS-PERM',696.72),('OMS-PASS-OUT',696.72),('OMS-PASS-ONCE',209.02),('OMS-ESCORT',4050)]:
            s.append(scenario('per_one_order_'+sid,u,u,1,'RUB preVAT / '+PRICES[sid][1]['unit'],sid,
                              'На1 заказ/пропуск; постоянный до5лет не означает ежегодную покупку; это малая часть запуска, не CAPEX оборудования.',period='one-off unit coefficient; order count UNKNOWN'))
    if not s:
        s.append(scenario('one_unknown_billable_unit',quantity=1,unit='unknown quote / article-specific billing unit',
                          basis='На1 billable unit: полный cost =1*P_UNKNOWN; фактический unit, quantity, timing и overlap — в формуле и запросе RW.'))
    return s


def cases():
    out=[]
    dated=read('model_audit/p38_dated_exposure.csv')
    active=defaultdict(set)
    for r in dated:
        active[r['candidate']].add((r['tail'],r['dep'][:7]))
    annual={(r['candidate'],r['scenario']):(i,r) for i,r in enumerate(read(P38_ANNUAL),2) if r['state']=='THREE_STATE_DELTA'}
    for filename in ['model_audit/owner_network_totals.csv','model_audit/p38_network_totals.csv']:
        for line,t in enumerate(read(filename),2):
            model=t['model'];net=t['network'];sc=t['scenario'];w=number(t['working_aircraft']);r=number(t['reserve_aircraft'])
            margin=number(t['subtotal_rub']);months=12*(w+r)
            oms=value(t,'departures','OMS')
            # Absent airport rows are zero only if a complete airport-departure listing sums to the network total.
            airports=[x for k,x in EXPOSURE.items() if k[:3]==(model,net,sc) and k[3]!='NETWORK' and k[4]=='departures']
            if oms is None:
                assert abs(sum(number(x[1]['value']) for x in airports)-number(t['departures']))<1e-7
                oms=0.0
            c={'case':':'.join([model,net,sc]),'model':model,'network':net,'scenario':sc,'period':t['period'],
               'weeks':number(t.get('weeks')),'calendar_days':365 if model=='P38' else None,
               'working_aircraft':w,'reserve_aircraft':r,'fleet_total':w+r,
               'departures':number(t['departures']),'OMS_departures':oms,'block_hours':number(t['block_hours']),
               'journeys':number(t['journeys']),'segments':number(t['segments']),'transfer_journeys':number(t['transfers']),
               'model_cost_rub':number(t['cost_rub']),'model_margin_rub':margin,
               'total_unaccounted_load_break_even_rub':margin,
               'positive_extra_load_feasible':margin>=0,'working_months_stress':w*12,'reserve_months_stress':r*12,
               'all_fleet_months_stress':months,'actual_billed_aircraft_months':None,
               'active_working_tail_months_in_2027_calendar':len(active[net]) if model=='P38' else None,
               'rent_ceiling_all_fleet_per_aircraft_month_rub':margin/months,
               'rent_ceiling_working_only_other_load_zero_rub':margin/(12*w),
               'rent_stress_full_allocation_exVAT_rub':product(7560000/1.18,months),
               'rent_stress_residual_after_allocation_rub':money(margin-7560000/1.18*months),
               'technical_reserve_stress_exVAT_rub':product(2436000,months),
               'existing_fuel_credit_rub':number(t.get('fuel_credit_rub')) if model=='OWNER' else 0.0,
               'existing_crew_in_cost_rub':number(t.get('crew_rub')) if model=='OWNER' else 0.0,
               'excluded_fixed_crew_reference_rub':number(t.get('fixed_crew_excluded')) if model=='P38' else None,
               'existing_migrated_receipts_deduction_rub':number(t.get('forgone_receipts_rub')) if model=='OWNER' else None,
               'source_ref':ref(filename,line),'source_original':t.get('source','see model_audit/coverage.csv exact P38 refs'),
               'incremental_new_rent_cash_rub':None,'full_PnL_rub':None,
               'rent_stress_basis':'2015 RUB nominal benchmark, no indexation; 12 retained billing months per declared working/reserve tail; not actual invoices or2027 quote'}
            if model=='P38':
                i,a=annual[(net,sc)];c.update({'R_minus_W_rub':number(a['R_minus_W']),'R_minus_K_rub':number(a['R_minus_K']),
                    'delta_source_ref':ref(P38_ANNUAL,i),
                    'R_minus_W_rent_ceiling_if_all36_months_new_rub':number(a['R_minus_W'])/months,
                    'R_minus_K_rent_ceiling_if_all36_months_new_rub':number(a['R_minus_K'])/months})
            out.append((t,c))
    return out


def calculate():
    rows=[];casepairs=cases()
    for t,c in casepairs:
        covnet=t['network'] if t['model']=='OWNER' else 'P38_K2_THREE_FINALISTS'
        for (item,net),(line,cov) in COVERAGE.items():
            if net!=covnet:
                continue
            di,driver=DRIVERS[(t['model'],t['network'],t['scenario'],item)]
            assert driver['status']==cov['status']
            ids=PRICE_MAP.get(item,[]);meta=[source_meta(sid) for sid in ids]
            ss=sensitivities(item,t,c)
            refs=[ref('model_audit/coverage.csv',line),ref('model_audit/annual_drivers.csv',di),c['source_ref']]+[m['ref'] for m in meta]
            exrefs=[]
            for metric in ['departures','block_hours','passenger_segments','journeys','transfer_journeys','working_aircraft','reserve_aircraft']:
                e=exposure(t,metric)
                if e:exrefs.append(ref('model_audit/exposures.csv',e[0]))
            e=exposure(t,'departures','OMS')
            if e:exrefs.append(ref('model_audit/exposures.csv',e[0]))
            if item in UNITS:
                metric,unit=UNITS[item]
                formula=f'Uncovered/repriced unit P * actual {metric}={value(t,metric)}; delta only after matching existing proxy/overlap; see model_formula'
            else:formula=UNKNOWN_FORMULAS[item]
            allowed='CONDITIONAL'
            if item in ['FUEL','MRO_PROXY','NAV','DEICE']:allowed='REPLACE'
            elif item in ['CREDIT','CREW_PROXY','DISTRIBUTION','TICKET_VAT','MIGRATION']:allowed='DO_NOT_ADD'
            elif cov['status']=='ABSENT':allowed='CONDITIONAL_ADD'
            price_admission='CURRENT_PRICE_UNKNOWN'
            if any(m.get('admission')=='DIRECT_OMS' for m in meta):price_admission='OMS_2026_PUBLISHED_UNIT_ONLY; 2027_AND_ADDITION_CONDITIONAL'
            if item in ('LEASE_WORK','LEASE_RES'):price_admission='HISTORICAL_STRESS_ONLY; CURRENT_UNKNOWN'
            if item in ('MRO_LINE','MRO_HEAVY','ENGINE'):price_admission='HISTORICAL_OR_UNKNOWN; NOT_2027_ADMITTED'
            if item=='CREW_HOTEL':price_admission='LOCAL_2026_ANALOGUE; CURRENT_TAX_UNKNOWN'
            included=number(driver['existing_proxy_amount_rub'])
            role=driver['amount_role']
            if t['model']=='P38' and item=='CREW_PROXY':
                role='EXCLUDED_REFERENCE_ONLY_NOT_IN_COST';included=0.0
            if t['model']=='P38' and item in ('CREDIT','GRANT','PAX'):
                included=0.0;role='EXPLICIT_ZERO_IN_MAIN_NOT_UNKNOWN_ACTUAL_COST'
            request=cov['missing_part_request']
            for sid in ids:
                if sid in LEASE:request+=' '+LEASE[sid][1]['requestRW']
                elif sid in FLEET:request+=' '+FLEET[sid][1]['requestRW']
            if any(s.startswith('OMS-') for s in ids):
                request+=' RW/OMS: подписанная спецификация и цены2027, billable unit/MTOW, объём по месяцам и хвостам/рейсам, free window, НДС/вычет и уже включённая доля ground96089/115307/MRO; заказчик/перевыставление; исключить одинаковую функцию ownbuy/lease/outsource.'
            missing_ru='UNKNOWN: '+cov['in_model_components']+' '+cov['annual_add_or_replace_rule']
            boundary='NORMALIZED_SENSITIVITY_NOT_BASE; full-service figures below are mutually exclusive or separate scoped services, never accepted additions'
            row={
                'row_id':c['case']+':'+item,'article_id':item,'article_ru':cov['item'],'case':c['case'],
                'model':t['model'],'network':t['network'],'scenario':t['scenario'],'period':t['period'],
                'coverage_network':covnet,'coverage_status_original':cov['status'],
                'coverage':STATUS[cov['status']][0],'coverage_ru':STATUS[cov['status']][1],
                'coverage_reason':cov['status_reason'],'code_table_exact_lines':cov['evidence'],
                'coverage_ref':ref('model_audit/coverage.csv',line),
                'already_in_model':cov['in_model_components'],'model_formula':cov['formula_or_basket'],
                'existing_rate_and_unit':cov['existing_rate']+'; '+cov['unit'],
                'existing_annual_amount_rub':included,'existing_amount_role':role,
                'excluded_reference_rub':number(driver['existing_proxy_amount_rub']) if t['model']=='P38' and item=='CREW_PROXY' else None,
                'existing_component_allocation':cov['component_allocation'],
                'annual_driver':driver['annual_driver'],'driver_refs':exrefs,
                'OMS_departures':c['OMS_departures'],'all_network_departures':c['departures'],
                'boarded_segments':c['segments'],'endpoint_journeys':c['journeys'],'transfer_journeys':c['transfer_journeys'],
                'missing_or_replacement_scope':missing_ru,'payer':cov['payer']+'; '+('OMS: заказчик по generic §6.1, RW signed payer/reimbursement UNKNOWN' if ids else 'signed payer/reimbursement UNKNOWN'),
                'unit_prices_and_sources':meta,'unit_price_admission':price_admission,
                'annual_formula':formula,'normalized_scenarios':ss,'scenario_boundary':boundary,
                'actual_missing_quantity':'UNKNOWN; model exposure above is not proof of contracted billing volume',
                'full_service_annual_actual_min_rub':None,'full_service_annual_actual_max_rub':None,
                'annual_addition_min_rub':None,'annual_addition_max_rub':None,
                'allowed_action':allowed,'addition_or_replacement_gate':cov['annual_add_or_replace_rule'],
                'one_off_expense_rub':None,'CAPEX_cash_rub':None,'refundable_deposit_cash_rub':None,
                'advance_cash_rub':None,'spares_stock_cash_rub':None,'working_capital_peak_rub':None,
                'accounting_class':cov['accounting_class'],'tax_model':cov['tax'],
                'overlap_and_exclusivity':cov['not_additive_with']+'; '+cov['annual_add_or_replace_rule'],
                'source_ids':['MODEL_AUDIT']+ids,'source_refs':refs,
                'source_date':'completed handoffs accessed2026-11-13; unit effective dates separately in unit_prices_and_sources',
                'reliability':cov['reliability']+'; price applicability/quantities/tax/overlap require RW confirmation',
                'request_RW':request,
            }
            rows.append(row)
    workings={'status':'COMPLETED','coverage_rows':117,'cost_table_rows':len(rows),'cases':[c for t,c in casepairs],
        'admitted_additions_count':0,'admitted_new_expenses_known_subtotal_rub':0,
        'admitted_subtotal_meaning':'Новых обоснованных additions нет; не значит бюджет0.',
        'annual_missing_total_rub':None,'full_PnL_rub':None,'full_cash_budget_rub':None,
        'launch':{k:None for k in ['one_off_expense_rub','CAPEX_rub','refundable_deposit_rub','advance_rub','spares_stock_rub','working_capital_peak_rub']},
        'rent_history':{'name':'2015 RUB nominal benchmark, no indexation','gross_rub':7560000,'VAT_historical':.18,
                        'exVAT_rub':7560000/1.18,'current_2027_price_rub':None,'USD_to_RUB_FX':None},
        'technical_reserve_history':{'gross_rub':2874480,'VAT_historical':.18,'exVAT_rub':2436000,'added_to_MRO':False},
        'aggregation_rule':'UNKNOWN propagates. Do not sum normalized sensitivities, overlapping baskets or alternatives. No full PnL from partial costs.'}
    return rows,workings


def fmt(x,dec=2):
    return 'UNKNOWN' if x is None else f'{x:,.{dec}f}'.replace(',',' ')


def case_label(c):
    net={'C0121723':'P38 C0121723','W7324a9b711d148bebb00/V0':'P38 W7324…','Wa17798465f19ba7addfb/V0':'P38 Wa177…'}.get(c['network'],c['model']+' '+c['network'])
    return net+' '+c['scenario'].upper()


def report(rows,w):
    cs=w['cases'];by={(r['case'],r['article_id']):r for r in rows}
    lines=['# P39 — готовый расчёт недостающих расходов, 13.11.2026','',
        '**Новых обоснованных additions нет; это не значит бюджет 0.** Основной реестр — [COST_TABLE.csv](COST_TABLE.csv): 546 строк =39 статей×14 неизменённых вариантов. Все117 исходных статусов покрытия воспроизведены; полнота модельной формулы не доказывает полноту фактического счёта. Полный годовой бюджет, full PnL, cash и стоимость запуска остаются **UNKNOWN**.','',
        'Численно оценены опубликованные единицы и условные коэффициенты услуги. Они отделены от `annual_addition_* = UNKNOWN`; **цена всей услуги по аналогу не равна добавке сверх модели**. Разрешение `REPLACE`/`DO_NOT_ADD`/`CONDITIONAL[_ADD]` и адресный запрос RW есть в каждой строке. Принятых безусловных `ADD` нет.','',
        '## Запуск и годовой остаток','',
        '| Мера | Принятая сумма | Что требуется |','|---|---:|---|',
        '| Разовый expense запуска | UNKNOWN | BoQ, ввод/обучение/интеграции, объём и уже оплаченный scope |',
        '| CAPEX | UNKNOWN | Собственность, GSE/инструменты/IT, сроки и амортизация |',
        '| Возвратный депозит | UNKNOWN | Договор, сумма, возвратность/зачёт |',
        '| Предоплата | UNKNOWN | Generic OMS §6.7.1:100% объёма обслуживания; signed RW график неизвестен |',
        '| Первоначальный stock ЗИП | UNKNOWN | SKU/количество/цены/собственность; потребление отдельно |',
        '| Peak working capital | UNKNOWN | Даты оплаты/выручки/возвратов и возмещения топлива |',
        '| Новые принятые годовые additions | Нет новых обоснованных additions | Пустая допущенная часть не равна полному бюджету0 |',
        '| Условные сценарии услуги | Числа ниже и в CSV | Нельзя суммировать взаимоисключающие/пересекающиеся функции |',
        '| Оставшаяся неучтённая годовая нагрузка | UNKNOWN | Rent, premium, payroll, MRO scope, F/C/D, сбои и station volumes |','',
        '## Экспозиция и точный порог нагрузки','',
        'M — неокруглённый subtotal из current replay, уже после модельных вычетов. Порог всей дополнительной экономической нагрузки L: `M−L=0`, то есть L*=M. Для условного годового начисления12 месяцев на каждый объявленный борт: `r*all=M/[12×(working+1)]`; `r*work=M/(12×working)` только при нулевой иной нагрузке и отдельно обеспеченном резерве. Отрицательный порог означает, что положительной допустимой добавки уже нет. Расчёт хранится без округления входной M в [workings.json](workings.json); в таблице ₽/борт-месяц округлены до копеек.','',
        '| Вариант | Working+R | Период | Flights / OMS dep | BH | Journeys / segments | L*=M, млн₽ | r*all / r*work, ₽/борт-мес |','|---|---:|---|---:|---:|---:|---:|---:|']
    for c in cs:
        period=f"{int(c['weeks'])} model weeks" if c['model']=='OWNER' else '2027,365дн'
        lines.append(f"| {case_label(c)} | {int(c['working_aircraft'])}+1 | {period} | {int(c['departures'])} / {int(c['OMS_departures'])} | {fmt(c['block_hours'])} | {fmt(c['journeys'])} / {fmt(c['segments'])} | {fmt(c['model_margin_rub']/1e6,6)} | {fmt(c['rent_ceiling_all_fleet_per_aircraft_month_rub'])} / {fmt(c['rent_ceiling_working_only_other_load_zero_rub'])} |")
    lines+=['',
        'Owner52/48 — модельные недели, не365 дней и не основание сократить неизбежную аренду/зарплату на48/52. Фактоплачиваемые борт-месяцы **UNKNOWN**. В P38 датированный completed plan даёт24 активных working tail-months, отдельно1R1; 36 оплачиваемых месяцев — условие удержания всего ресурса весь год. Сети имеют разный парк и состав расходов; это учётные строки, **не рейтинг равночисленного парка**.','',
        'Для P38 M выше — standalone REPLACE subtotal. Проектный incremental counterfactual иной:','',
        '| P38 | ΔR−W, млн₽ | ΔR−K, млн₽ | r*ΔR−W / r*ΔR−K при всех36 НОВЫХ борт-мес, ₽ |','|---|---:|---:|---:|']
    for c in cs:
        if c['model']=='P38':
            lines.append(f"| {case_label(c)} | {fmt(c['R_minus_W_rub']/1e6,6)} | {fmt(c['R_minus_K_rub']/1e6,6)} | {fmt(c['R_minus_W_rent_ceiling_if_all36_months_new_rub'])} / {fmt(c['R_minus_K_rent_ceiling_if_all36_months_new_rub'])} |")
    lines+=['',
        'Incremental rent cash существующего борта может быть0 **только** после подтверждения одинакового уже оплаченного графика и отсутствия новых хвостов/продления/endorsement во всех альтернативах; сейчас UNKNOWN. Full-PnL allocation остаётся по договору/учётной политике. Внешний упущенный вклад D — отдельная неденежная поправка, после уже включённых internal old-product deltas. Owner forgone — мигрировавшая выручка, не полный donor contribution. Для finance lease нельзя сложить все платежи, амортизацию и проценты повторно.','',
        '## Сопоставимые условные коэффициенты','',
        'OMS2026 цены «кроме того НДС», численная текущая ставка/вычет UNKNOWN. Это preVAT sensitivities, не договор2027. HOTEL — опубликованные RUB2026 с неизвестным налогом; его нельзя механически суммировать с exVAT. Нулевая transfer-экспозиция DIRECT/P38 относится только к transfer product; общий риск сбоев UNKNOWN.','',
        '| Вариант | 1 extra bag service / OMS dep, ₽ preVAT | 1 пост информирования / OMS dep, ₽ preVAT | 1п.п. transfer journeys ×1ночь single / double, ₽ published |','|---|---:|---:|---:|']
    for c in cs:
        ss=by[(c['case'],'DISRUPT')]['normalized_scenarios']
        hotel=[x['full_service_min_rub'] for x in ss[:2]]
        lines.append(f"| {case_label(c)} | {fmt(4450*c['OMS_departures'])} | {fmt(1229.51*c['OMS_departures'])} | {fmt(hotel[0])} / {fmt(hotel[1])} |")
    lines+=['',
        '- Багаж4450/дополнительное обслуживание по заявке; не RUB/kg, не на каждого пассажира/стыковку. Условие таблицы — ровно1 заказ на каждый OMS departure. Сценарий отражает всю услугу; добавка UNKNOWN до itemization ground96089/115307 и pax500/650.','- Стойка1229.51/рабочее место на рейс — информирование; DCS/check-in UNKNOWN. Все сетевые departures вместо OMS departures дали бы неверный объём.','- Flagman single4100/room-night; double4650/room-night при2чел. Коэффициент `.01×transfer_journeys×1ночь/occupancy`, не вероятность срыва. Трансфер — одна journey с двумя boarded segments. Для реальных броней нужны целые комнаты по событиям. Breakfast950 — разница пакетов, не standalone рацион.','- На10м² хранения имущества ×12мес: **39 600 /120 000 ₽ preVAT** для unheated/heated; это не здание/ангар и не весь station overhead.','- Автобус3430/начатый моточас; маршрут, вместимость и количество UNKNOWN; цены per-pax нет. Раздача питания3275/обслуживание не включает доказанную стоимость еды.','- Parking:30–74.999т117100/мес,1018/час,24432/сутки;75–99.999т130200/мес,1140/час,27360/сутки. MTOW/договор выбирать условием; **monthly/hour/day альтернативны**. На1год одного оплачиваемого борта месячно1 405 200 /1 562 400 ₽ preVAT. OMS BASE working6×12:8 431 200 /9 374 400; если подтверждено базирование уже существующего R1 там же, весь парк7×12:9 836 400 /10 936 800. Реальные billing months/free window/ground overlap UNKNOWN.','- На1 постоянный пропуск до5лет696.72; разовый209.02; сопровождение4050/обслуживание, preVAT. Телеграммы6.23/55.60 за штуку не заменяют broadband/DCS. Никакой из коэффициентов не задаёт реальный объём заказа.','',
        '## Только stress аренды: «2015 RUB номинальный benchmark, без индексации»','',
        '`7 560 000/1.18=6 406 779.66101695 ₽ exVAT18/борт-месяц`. Это историческая сухая субаренда другого оператора в судебном пересказе; не текущая цена RW и не основной бюджет. Самолётные месяцы ниже = объявленные working×12 плюс УЖЕ имеющийся1reserve×12 при условии годового удержания. Actual billed months UNKNOWN; USD180000 не конвертирован без доказанного FX.','',
        '| Вариант | Working / R / total борт-мес в stress | Full allocation аренды, млн₽ exVAT18 | M минус ТОЛЬКО этот stress, млн₽ |','|---|---:|---:|---:|']
    for c in cs:
        lines.append(f"| {case_label(c)} | {int(c['working_months_stress'])} / {int(c['reserve_months_stress'])} / {int(c['all_fleet_months_stress'])} | {fmt(c['rent_stress_full_allocation_exVAT_rub']/1e6,6)} | {fmt(c['rent_stress_residual_after_allocation_rub']/1e6,6)} |")
    lines+=['',
        '**Это остаток после одной гипотезы, не full PnL.** Технический резерв2015 отдельно:2 874 480inclVAT18 =2 436 000exVAT18/борт-мес. Его полный stress есть один раз в MRO_HEAVY CSV и workings; добавка UNKNOWN. Scope/возвратность не раскрыты: не прибавлять поверх MRO35000/55000BH и не называть депозитом/ценой engine repair. Исторический USD и S7USD2023 не стали RUB2027 quote. Страховая стоимость78B и initial tender premium исключены.','',
        '## Все39 статей: читаемый указатель основной таблицы','',
        'F=полностью учтена указанная модельная формула; P=частично; A=нет в формуле; U=нераскрытая корзина. Все отсутствующие денежные суммы UNKNOWN. Для каждой строки/варианта CSV содержит точный code/table:line, существующий annual amount, actual exposure, цену/дату/налог, полную стоимость нормировки, gate добавки, cash classes, source/reliability и точный запрос RW.','',
        '| Статья | OMS / DIRECT / P38 | Цена или коэффициент недостающей части | Действие |','|---|---|---|---|']
    letters={'FULL_IN_MODEL':'F','PARTIAL':'P','ABSENT':'A','UNRESOLVED_BASKET':'U'}
    notes={
        'FUEL':'UNKNOWN; +1₽/t×burn tonnes; заменить landed/burn', 'UPLIFT':'UNKNOWN; +1₽/t×burn, received/uplift объём отдельно',
        'CREDIT':'Owner32930/3024 уже вычтен; P38MAIN0, eligible UNKNOWN', 'CREDIT_CASH':'UNKNOWN; eligible tonnes×credit и cash dates',
        'VAT':'UNKNOWN; unrecoverableVAT и recovery lag отдельно', 'GROUND':'96089/115307×all network flights уже в модели; новая корзина не добавка',
        'GROUND_DETAIL':'OMS911/947 perMTOW и200/pax только reference; billable MTOW/turn/pax UNKNOWN',
        'PAX':'Owner500/650×segments уже учтено; P38MAIN0; новый scope UNKNOWN',
        'MRO_PROXY':'35000/55000×actualBH уже учтено', 'MRO_LINE':'UNKNOWN; S7USD2023 только historical, +1₽/BH коэффициент',
        'MRO_HEAVY':'UNKNOWN; due list; техрезерв2015 отдельно с overlap gate', 'ENGINE':'UNKNOWN; PBH/LLP/SaM146; PD8 не рассчитан',
        'SPARES_USE':'UNKNOWN; +1₽/BH; pool/consumption отдельно', 'SPARES_STOCK':'UNKNOWN; SKU×quote; stock/deposit не расход года',
        'NAV':'6000/8000×BH уже учтено', 'DEICE':'15000/40000×flight allowance уже учтено',
        'CREW_PROXY':'Owner15000/22000×BH учтено; P38 исключено ровно1раз',
        'CREW_FIXED':'UNKNOWN; FTE coverage/effective hours и loaded payroll', 'CREW_TRAIN':'UNKNOWN; entry×course и refresher отдельно',
        'CREW_POSITION':'UNKNOWN; roster/trips;3430/begun bus-hour coefficient',
        'LEASE_WORK':'Текущая UNKNOWN; исторический rent stress working×12', 'LEASE_RES':'Текущая UNKNOWN;1R1 уже есть; stress12мес',
        'CAPITAL':'UNKNOWN; ownbuy/lease альтернативы, finance/deposit отдельно', 'FERRY':'OwnerUNKNOWN; P38 dated ferry0; +BH/flight scope',
        'PARKING':'OMSmonthly/hour/day альтернативны, billing UNKNOWN', 'CREW_HOTEL':'На1room-night4100single/4650double; roster UNKNOWN',
        'INSURANCE':'PremiumUNKNOWN; signed period/tail/endorsement',
        'OVERHEAD':'На10м²39600/120000; пост×OMSdep; полный overhead UNKNOWN',
        'DISTRIBUTION':'UNKNOWN; net bridge уже есть; blanket commission не добавлять',
        'TICKET_VAT':'UNKNOWN; повторно net yield не делить', 'REFUNDS':'UNKNOWN; affected tickets×residual liability, без двойного lost revenue',
        'DISRUPT':'1п.п.transfer×night hotel; bus/food отдельно; incidence UNKNOWN',
        'OMS_SETUP':'На1pass696.72/209.02, escort4050; BoQ/capexUNKNOWN',
        'TRANSFER':'4450×extra ordered services; на1extra/OMSdep выше', 'CANCEL_OLD':'UNKNOWN; signed action penalties/avoidable costs',
        'DONOR':'UNKNOWN; uncovered external contributionD, noncash',
        'MIGRATION':'Уже учтённый forgone/joint old delta; остатокUNKNOWN',
        'GRANT':'Owner modelgrant один раз; P38MAIN0; entitlementUNKNOWN',
        'DEPOSITS':'UNKNOWN; dated advances/deposits/WC; не annual expense',
    }
    for (item,net),(i,cov) in COVERAGE.items():
        if net!='OMS':continue
        stat=' / '.join(letters[COVERAGE[(item,n)][1]['status']] for n in ['OMS','DIRECT','P38_K2_THREE_FINALISTS'])
        act=by[('OWNER:OMS:base',item)]['allowed_action']
        lines.append(f"| {item}: {cov['item']} | {stat} | {notes[item]} | {act} |")
    lines+=['',
        '## Передача','',
        'Готово, ожиданий входов нет. Для допуска сумм RW нужны прежде всего: tail rent/insurance schedules2027 и existing-vs-new obligations; itemization ground/MRO/pax; paid crew roster; station BoQ/ownership; hotel/disruption quantities; договорный cash calendar и внешний donorD. Запросы по каждой статье уже в CSV.','',
        'Источники с относительными путями и правилами допуска: [ASSUMPTIONS.md](ASSUMPTIONS.md); базовый [coverage117](../model_audit/coverage.csv), [exposures476](../model_audit/exposures.csv), [owner current replay](../model_audit/owner_network_totals.csv), [P38 replay](../model_audit/p38_network_totals.csv), [OMS34](../omsk_price_recovery/prices.csv), [fleet recovery5](../fleet_price_recovery/prices.csv), [координатор](../coordinator/source_admission.md). P30/P38 переиспользованы через completed audit; новый поиск/оптимизация не выполнялись.','',
        'Офлайн Python3, из любого cwd (абсолютные пути):','',
        '```bash',f'python3 -B {HERE}/build_cost_table.py',f'python3 -B {HERE}/verify.py','```','',
        'Сборка и verify исполнены дважды; хеши выходов совпали. [validation.json](validation.json) фиксирует units/tax/annual formulas/UNKNOWN/exclusivity/source refs/coverage и неизменность исходных tracked bytes+индекса без вызова Git. Запись только calculation; панель/старые inputs не изменены.']
    return '\n'.join(lines)+'\n'


def assumptions():
    return '''# Допущения, источники и допуск P39

1. Только completed входы. Приоритет: model_audit для scope/exposure/current margin; omsk_price_recovery34 и первичные PDF вместо первого research_omsk6; fleet_price_recovery5 с coordinator root check для исторических резервов; research_fleet15 для незакрытых запросов. Pins/TASK/contract прочитаны. Никакого нового поиска или запуска старых exporters.
2. Coverage117 переносится буквально в546 case rows. FULL означает полноту названной модели, не реальный invoice. U/UNKNOWN не означает0. Существующий annual proxy не отдельный недостающий cost. Для P38 excluded crew amount показан reference отдельно, included cost0; pax/credit/grant MAIN0 — факт кода, не действительные цены0.
3. Owner BASE52 и CAUT48 model weeks; annual carried из replay, не annual demand, не prorata48/52. Passenger segments=journeys+transfer_journeys; transfers дают два плеча. Багаж/room-nights/paid turns из этого не выводятся. P38 ровно2027 календарь, UTC whole-flight departure attribution; scope differs from calendar-split BH. Departures OMS берутся из scope OMS; если строки нет, ноль разрешён только после сверки полного airport breakdown с network total.
4. Ресурсы из exact totals: OMS BASE6+1, DIRECT BASE7+1, DIRECT_SUB BASE8+1; CAUT берётся из своего сценария. P38 каждый2+R1. Не добавлять второй резерв.12 contractual billing months не выводятся из52/48недель. Для named rent stress это явное условие удержания каждого модельного борта весь год: working×12 и1R1×12; actual invoices неизвестны. Датированный P38 имеет24 активных working tail-months, не36 активных рабочих самолётов. Разница между активностью и оплатой сохранена.
5. Unknown internal None, CSV UNKNOWN, JSON null. Любое неизвестное слагаемое делает полный итог UNKNOWN; None×0 остаётся UNKNOWN. Единственный0 нового принятого subtotal означает пустое множество подтверждённых additions. Это не полный budget0. Sensitivities отражают стоимость всей названной услуги; addition всегда UNKNOWN до раскрытия scope/tax/qty/overlap. Никаких математических overlap bounds, выданных за факт, нет.
6. Нормировка +1RUB/unit — производная годовой суммы по unit, не найденная цена. Для остальных UNKNOWN дан exact formula/one-unit unknown price и запрос. Вложенные normalized_scenarios — часть ЕДИНСТВЕННОЙ COST_TABLE, не новые расходные реестры; альтернативы и unit coefficients нельзя суммировать. full_service_annual_actual UNKNOWN, пока фактический объём не доказан. Decimal HALF_UP только на выводе; replay M и деление порога без предварительного округления, ценовые произведения до копеек.
7. Действия: REPLACE заменяет одинаковую модельную корзину; DO_NOT_ADD запрещает повтор той же формулы/credit/tax/internal migration (исправление scope только по отдельному bridge); CONDITIONAL и CONDITIONAL_ADD требуют signed current price, billing volume и доказанного uncovered scope. Ни одна строка не допущена как безусловный ADD. Ownbuy/lease/outsource одной функции взаимоисключающие.
8. Запуск expense, CAPEX, refundable deposit, advance, spares stock и peak WC отдельны. Траты на stock не annual consumption. Цена самолёта не годовая аренда; lease cash не складывается с depreciation+interest без учётной политики. OpportunityD не денежный платёж; internal migration/old product changes уже учтены.

## Единицы и разрешённые первичные цены

- [OMS34](../omsk_price_recovery/prices.csv), [primary scan2026](../omsk_price_recovery/sources/oms_20260821.pdf), [точная ручная транскрипция](../omsk_price_recovery/excerpts/oms_tables.txt), [проверка изменений](../omsk_price_recovery/excerpts/amendments.txt): ставки с21.08.2026, применимость2027UNKNOWN. Все значения «кроме того НДС»; numeric current VAT/recoverabilityUNKNOWN.330/1000perм²-month только складское хранение;1229.51perworkplace-flight только информирование;4450peradditional ordered service не kg/pax/автоматическийtransfer.117100monthly для30–74.999т,130200для75–99.999т: тип/MTOW неизвестен, условия не сглажены в один fake quote. Hourly/day/monthly/free-window взаимосвязь только по договору.
- [Generic OMS contract](../omsk_price_recovery/sources/oms_contract.pdf), [точные условия](../omsk_price_recovery/excerpts/contract_verified.txt): заказчик платит по дате услуги;100% предоплата generic scope, не signed RW guarantee и не повторный expense. Общая ground96089/115307 не расшифрована, новый весь airport tariff поверх неё запрещён.911/947perMTOW и200perpax толькоREFERENCE_ONLY, не pricing всей корзины.
- [Flagman saved official HTML](../omsk_price_recovery/sources/flagman.html), [текст строки82–104](../omsk_price_recovery/excerpts/flagman.txt):01.02–31.12.2026;4100single,4650double за номер-ночь RO, налогUNKNOWN.950=(5050−4100) breakfast package difference, не самостоятельный ration quote. На1п.п.transfer journeys используется0.01×Jtransfer×nights/occupancy. Single/double альтернативы, дробное значение — sensitivity; фактическая бронь только по целым room-nights и событиям. Прочие disruption costs неизвестны.
- Bus3430perbegun motorhour OMS§8.1:capacity/route/pickup неизвестны, per-pax quote не выведен.3275permeal distribution service — операция раздачи, food priceUNKNOWN. Telegram6.23/55.60 не DCS/интернет. Пропуска696.72до5лет не ежегодная ставка;209.02single,4050escort/service. Количество всех заказовUNKNOWN.

## История, отклонённые входы и надёжность

- [Fleet recovery5](../fleet_price_recovery/prices.csv), [точные выдержки](../fleet_price_recovery/source_excerpts.md), [coordinator root check](../coordinator/source_admission.md): судебный legal mirror, акт15.04.2021 А08-2884/2015, спорные договоры2013–2015 другого оператора, remand. Medium confidence historical contract recital, нет current RW price. Stress назван **2015 RUB номинальный benchmark, без индексации**:7560000inclVAT18 /1.18; gross VAT1153220.34 округлён в акте, использована ставка18%, без повторного неттирования. USD180000incl18 не переводится без FX и не образует диапазон сRUB.
- Координатор§11.2: технические резервы2874480inclVAT18, VAT438480, exVAT2436000peraircraft-month. Показаны один раз как full-service stress вMRO_HEAVY, не добавлены кMRO35000/55000BH. Scope, refundability, engine/heavy/spares split неизвестны; ENGINE ссылается на источник, без повторной денежной строки резерва. Сомнительный court aggregate8713220.34 не используется.
- [Research fleet15](../research_fleet/price_evidence.csv): S7USD2023 MEL67/event, detached932/person24h, NDT1587/24h, storage110/65USD/m²-month — historical scope только, без FX/индексации/цены2027. Canonical OMS storage лучше для местной единицы; MRO price2027 остаётсяUNKNOWN. RRJ/SaM146 не PD8 forecast.
- Текущая аренда RW2027 и premiumUNKNOWN.78B — insured value, не premium. Initial tender12946975 — rejected aggregator lead; никакой нормализации на борт/год. RW19.08.2025 — дата публикации, не доказанный policy inception.
- [Первый OMS проход](../research_omsk/price_evidence.csv) superseded там, где recovery уточнил источник. PKC16.90/kg толькоINDEX_ONLY, не используем numerical OMS price. Hotel Aero430 и bus3000 такжеINDEX_ONLY; secondary wage42–50тыс. не admitted. Допуск unit не допуск annual addition.
- [Model coverage](../model_audit/coverage.csv), [annual drivers](../model_audit/annual_drivers.csv), [476 exposures](../model_audit/exposures.csv), [scope](../model_audit/model_scope.json), [prior reuse P27/P30/P38](../model_audit/prior_reuse.csv), [source line text](../model_audit/evidence_lines.csv), [snapshot mapping](../model_audit/snapshot_manifest.json): высокая надёжность к exact pinned code/arithmetic, UNKNOWN к фактическим счетам и договорам. Оригинальные commit:path:line вCSV не заменены текущим файлом. Относительные source_refs дополнительно указывают точные строки handoff.
- [Current owner totals](../model_audit/owner_network_totals.csv) даютM по каждому варианту. DIRECT_SUB115.317320млн не старые99.981. [P38 totals](../model_audit/p38_network_totals.csv) — standaloneREPLACE; [completed saved annual delta](../model_audit/snapshot/56400c5f/context/38_direct_strategy_20261113/economics/annual_results.selected.csv) — отдельныеR−W/R−K. Нет rerun choice/seasonal optimization. Аренда существующего tail — fullPnL allocation, incremental cash только signed differential, external donorD отдельно и без двойного internal delta.

## Контроль неизменности

verify.py напрямую читает Git index, хеширует его и содержимое всех исходно tracked entries; Git CLI не запускается. Равенство before/after индекс+tracked content доказывает неизменность ранее существовавшего tracked diff. Все входы P39 за пределами calculation также агрегированно SHA256-проверены. Baseline protection.json не перезаписывается. Два offline build/verify дают одинаковые4 output SHA256; validation.json детерминирован и фиксирует итог. Панель, старые inputs и исходные handoffs не меняются.
'''


def main():
    rows,w=calculate()
    with (HERE/'COST_TABLE.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader()
        writer.writerows({k:cell(v) for k,v in r.items()} for r in rows)
    (HERE/'workings.json').write_text(json.dumps(w,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    (HERE/'RESULT.md').write_text(report(rows,w))
    (HERE/'ASSUMPTIONS.md').write_text(assumptions())
    print('Built COST_TABLE.csv: 546 rows, 14 cases, 39 articles. Full budget UNKNOWN.')


if __name__=='__main__':
    main()
