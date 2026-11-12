"""Общие датированные программы P09. P05/P06 импортируются из exact git subject.

Числа здесь — открытые аналитические условия, не прогноз поставок/диспетчерский допуск.
"""
from pathlib import Path
from datetime import datetime, date, timedelta, timezone
from collections import defaultdict, Counter
from functools import lru_cache
import calendar, copy, csv, hashlib, importlib.util, itertools, json, math, sys

ROOT=Path(__file__).resolve().parent.parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'subject/P06'))
from engine import core
from engine.operations import check_operations, check_itineraries
from engine.choice import allocate, apply_response
from engine.finance import finance, funding
spec=importlib.util.spec_from_file_location('p05_pinned',ROOT/'subject/P05/model.py')
p05=importlib.util.module_from_spec(spec);spec.loader.exec_module(p05)
D=p05.Demand()
MONTHS=[f'{y}-{m:02d}' for y in [2027,2028] for m in range(1,13)]
DATES=[date(2027,1,1)+timedelta(days=i) for i in range(731)]
PINS=json.loads((ROOT/'input_pins.json').read_text())
VERSION='P09-v1-20261112'
EXISTING_VARIANT='SSJ100_SaM146_REFERENCE_100'
NEW_VARIANT='SJ100_PD8_SEPARATE_WITH_SSJ_COST_ANALOGUE'
KEEP_DEST=['UFA','OMS','REN','GOJ','PEE','MCX']

def dump(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def digest(obj):return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def csvwrite(path,rows,fields=None):
    rows=list(rows)
    if not rows and fields is None:return
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader()
        for r in rows:w.writerow({k:'UNKNOWN' if v is None else json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()})
def timestamp(d,hour=0):return datetime.combine(d,datetime.min.time(),timezone.utc)+timedelta(hours=hour)
def iso(t):return t.isoformat(timespec='seconds').replace('+00:00','Z')
@lru_cache(maxsize=None)
def distance(a,b):return p05.km(D.nodes[a],D.nodes[b])
@lru_cache(maxsize=None)
def block(a,b):return math.ceil((45+distance(a,b)/650*60)/5)*5

def assumption(aid,value,unit,basis,effect,sensitivity,refinement,range_='UNKNOWN; сценарные точки не доверительный интервал'):
    return dict(assumption_id=aid,value=value,unit=unit,selected_by='P09 исследователь Astra xhigh',basis=basis,approval_status='ANALYTIC_SCENARIO_NOT_RW_PLAN_OR_USER_PARAMETER_APPROVAL',range_or_unknown=range_,affected_conclusions=effect,sensitivity=sensitivity,refinement=refinement)

ASSUMPTIONS=[
    assumption('P09-RESOURCE','E1 занят KEEP; новые: phased 4, partial 2, delayed 2, none 0; один новый резерв, остальные рабочие','физические сценарные борта','Минимальные целочисленные группы 1/2/3 рабочих + 1 резерв; раздельный резерв типов. Числа выбраны для проверки масштаба, а не как план RW.','Объём сети и платежи за занятые/неиспользуемые борта','Все четыре ветви; группа 1/2/3','Поставка по бортам, назначения, crew и ТО; P03 UNKNOWN'),
    assumption('P09-ENTRY',{'phased':['2027-08-01','2027-11-01','2028-04-01','2028-09-01'],'partial':['2027-08-01','2027-11-01'],'delayed':['2028-07-01','2028-11-01'],'none':[]},'даты ввода; передача за30 календарных дней','Поступление не раньше2027H2; 30 дней ввода — открытая проверочная задержка, договорный срок UNKNOWN.','Календарь/доступность/обязательства','phased/partial/delayed/none','План поставок и фактический ввод'),
    assumption('P09-KEEP','E1: SVX–UFA/OMS/REN/GOJ/PEE/MCX, одна RT по одному дню пн–сб; воскресенье без коммерческих рейсов. Новые рабочие борта в KEEP усиливают этот набор','датированные рейсы и поездки','Условный контрфакт действующих направлений; не полный наблюдаемый бизнес. Названия направлений проверяются по закреплённым SVX inputs. Неизвестный остальной бизнес учитывается символическим affected remainder.','Собственный переток, альтернативное применение ресурса, потерянные продажи','KEEP интенсивность/тариф и дополнительные own через общие P05; остаток UNKNOWN','RW dated schedule/coupon sales/задания по хвостам'),
    assumption('P09-SCHEDULE','пн/чт,вт/пт,ср/сб; 3 маршрута на рабочий борт; радиальная1RT/день; bank2RT/день только block<=10h; воскресенье без рейсов','RT/week; UTC','Общий структурный шаблон; генерация всех731 дат, изменение состава при вводе ресурса. Не расширение недели P03.','Частота, вместимость, ценность времени и хвосты','Сезонный пик: дополнительный воскресный RT для radial; bank требует отдельный контроль','Слоты, часовые ограничения, crew, спрос по дням'),
    assumption('P09-PERFORMANCE',{'seats':100,'blocked':0,'block_formula':'ceil5(45+km/650*60)','turn_min':45,'max_block_day':10,'range_screen_km':3000,'mtow_t':49.45},'места;мин;ч;км;т','Открытый SSJ-аналог. ПД8 — отдельный вариант с переносом аналога только для чувствительности; не подтверждённый AFM, load/range или burn. Прямой геодезический путь не airways.','Геометрический/ресурсный сценарий и расходы','8h и 10h; дальность2500/3000; никакого dispatchPASS','AFM конкретных RRJ/SJ, ETOPS/маршрутизация, crew/MRO, реальная компоновка'),
    assumption('P09-OPS','crew окна и ТО UNKNOWN; воскресенье + ночные интервалы не доказательство нормативного отдыха; резерв N1 не выполняет коммерческие рейсы','условия допуска','Отделение механической выполнимости от реальных crew/MRO/dispatch. Старый E1 имеет собственную неизвестную резервную инфраструктуру.','Любой допуск','Дефицит ресурса и дополнительные простои открыты','P03 принятые roster/maintenance/KEEP'),
    assumption('P09-COST','P04 базовые/осторожные HIST burn/MRO/crew/nav + UFA fuel136300/t; airport movement reference UFA либо закреплённая местная ставка','постоянные RUB2026','Явный аналитический аналог. Ни одна ставка не названа контрактом2028. HIST pax500/650 не добавляется к локальным paxfees: состав неизвестен.','Частичный операционный subtotal; полный результат функция отсутствующих ставок','Base/cautious; раздельные BH/cycle/pax/base/tail пороги','Договоры топлива/ТО/crew/навигации, service mapping; P04'),
    assumption('P09-MISSING','полная база, launch/exit, tail lease, own remainder, crew fixed premium, foreign alternative и finance UNKNOWN','RUB по драйверам','Нет credible bounds. Общие обязательства одинакового флота сокращаются только при одинаковом договоре; это не нулевая цена.','Полный delta и финансирование','Пороги остаточной стоимости; символические коэффициенты','P04/P03/RW finance contract fields'),
    assumption('P09-CASH',{'receipt_days_before_flight':30,'variable_invoice_days_after':30,'opening_cash_test':0,'minimum_cash_test':0},'дни;RUB','Условная симметричная политика известных компонентов; фактические lag/opening/mincash/interest неизвестны. Выручка одна на поездку.','Только known-component funding diagnostic; full peak UNKNOWN','Получение0/30/60 дней, оплата0/30 дней; missing cash symbolic','Billing, эквайринг, налоги, договоры, opening cash и interest schedule'),
    assumption('P09-SUPPORT',0,'RUB','Ветвь без поддержки. Отсутствие начисления — выбранный сценарий, не утверждение об отсутствии законного права. Неподходящие/истёкшие льготы не начисляются.','Известный subtotal без поддержки','Порог поддержки; фактическое право/платёж отдельно','P04 eligibility/contract/payment events'),
    assumption('P09-SCOPE','Объединение OD P и KEEP; немоделируемый затронутый внутренний/международный остаток сохранён символически. Место№2 и reportedshare UNKNOWN','поездки/сегменты/рейсы','Пока нет P10 совместимого reporting_flight_id/boarding_group и полного бизнеса.','Нет выводов о доле рынка или компании в целом','Remainder opportunity threshold','P10 adapter; международные OD и own contracts'),
    assumption('P09-SEASON',{'peak_months':[6,7,8],'winter_months':[12,1,2],'rest':'межсезонье'},'месяцы','Помесячный спрос P05 уже сезонный. Peak radial Sunday — отдельный тест частоты, не повышение спроса.','Реальное число дат, пик загрузки','bad_season использует cautious P05 в6–8; flat_daily есть в P05 и может быть дополнительным тестом','Маршрутные месяц/OD и сезонные slot данные'),
    assumption('P09-RESPONSE','P05-A13: incumbent fare−10% в тех OD/date, где присутствует RW','условный логит outside inclusive value','Одна и та же адресная функция ответа для P и KEEP; outside composite не физические кресла конкурента.','Спрос/выручка/переток','passive/response10','P02 future dated competitor supply и booking evidence'),
]
P05_ASSUMPTIONS=json.loads((ROOT/'subject/P05/assumptions_register.json').read_text())

def fleet(delivery='phased'):
    entries={'phased':['2027-08-01','2027-11-01','2028-04-01','2028-09-01'],'partial':['2027-08-01','2027-11-01'],'delayed':['2028-07-01','2028-11-01'],'none':[]}[delivery]
    def record(tid,variant,entry,transfer,reserve=False):
        return dict(aircraft_id=tid,variant=variant,transfer_date=iso(timestamp(transfer)),service_entry_date=iso(timestamp(entry)),available_from=iso(timestamp(entry)),available_to='2029-01-01T00:00:00Z',initial_location='SVX',turn_minutes=45,reserve_intervals=[['2027-01-01T00:00:00Z','2029-01-01T00:00:00Z']] if reserve else [],maintenance_intervals=None,crew_windows=None,max_daily_block_hours=10,assumption_id='P09-RESOURCE',reserve_role=reserve)
    out=[record('E1',EXISTING_VARIANT,date(2027,1,1),date(2026,12,1))]
    for i,s in enumerate(entries):
        d=date.fromisoformat(s);out.append(record(f'N{i+1}',NEW_VARIANT,d,d-timedelta(days=30),i==0))
    return out

def leg(a,b,start,tid,variant,mode,project=True):
    fid=f'{tid}:{a}-{b}:{start.strftime("%Y%m%dT%H%M")}'
    f=dict(flight_instance_id=fid,schedule_id=VERSION,operator='RW_SCENARIO',flight_number=f'P09-{tid}',origin_airport=a,destination_airport=b,departure_utc=iso(start),arrival_utc=iso(start+timedelta(minutes=block(a,b))),aircraft_variant=variant,seats=100,technical_blocked_seats=0,saleable_seats=0 if mode=='positioning' else 100,physical_adjacent_leg=True,scheduled_status='proposed',source_status='scenario',source_period='2027–2028',assumption_id='P09-PERFORMANCE',distance_km=distance(a,b),project_network=project and mode!='positioning',role=mode,reporting_flight_id=fid,boarding_group_rule='одна посадка на независимый flight_id; through sale отдельно')
    if mode=='positioning':f['technical_blocked_seats']=100
    a=dict(flight_instance_id=fid,aircraft_id=tid,crew_id=None,action='keep' if tid=='E1' else 'add',assumption_id='P09-OPS')
    return f,a

def ferry_path(base):
    if base=='SVX':return []
    # All ferry legs count in resource/cost; long eastern positions split explicitly.
    candidates=[['SVX',base],['SVX','KJA',base],['SVX','KJA','IKT',base],['SVX','KJA','IKT','KHV',base]]
    valid=[p for p in candidates if len(set(p))==len(p) and all(distance(a,b)<=3000 for a,b in zip(p,p[1:]))]
    return min(valid,key=lambda p:sum(block(a,b) for a,b in zip(p,p[1:]))) if valid else None

def build_calendar(programme,delivery='phased'):
    tails=fleet(delivery); flights=[];assignments=[];unserved=[]
    def emit(a,b,t,tail,mode,project=True):
        f,z=leg(a,b,t,tail['aircraft_id'],tail['variant'],mode,project);flights.append(f);assignments.append(z);return datetime.fromisoformat(f['arrival_utc'].replace('Z','+00:00'))
    def rt(h,s,t,tail,mode,project=True):
        arrival=emit(h,s,t,tail,mode,project)
        return emit(s,h,arrival+timedelta(minutes=45),tail,mode,project)
    for ti,tail in enumerate(tails):
        if tail['reserve_role']:continue
        tid=tail['aircraft_id'];entry=date.fromisoformat(tail['service_entry_date'][:10]);end=date(2028,12,30)
        if tid=='E1':base='SVX';spokes=KEEP_DEST;bank=False;start=entry
        else:
            wi=int(tid[1:])-2
            spec_=programme['working_slots'][wi] if wi<len(programme['working_slots']) else dict(base='SVX',spokes=[],bank=False)
            base=spec_['base'];spokes=spec_['spokes'];bank=spec_.get('bank',False);start=entry+timedelta(days=1)
            if not spokes:continue
            path=ferry_path(base)
            if path is None:
                unserved.append(dict(tail=tid,reason='POSITIONING_PATH_OPEN',base=base));continue
            if path:
                cur=timestamp(entry,5)
                for a,b in zip(path,path[1:]):cur=emit(a,b,cur,tail,'positioning')+timedelta(minutes=45)
                # Ferry crew legality unknown; split >10h over dates, not secretly approve.
                if sum(block(a,b) for a,b in zip(path,path[1:]))>600:
                    unserved.append(dict(tail=tid,reason='FERRY_DAILY_BLOCK_OVER10H',base=base))
            if base!='SVX':
                cur=timestamp(date(2028,12,31),5)
                for a,b in zip(path[::-1],path[-2::-1]):cur=emit(a,b,cur,tail,'positioning')+timedelta(minutes=45)
        for d in DATES:
            if d<start or d>end or not spokes:continue
            dow=d.weekday()
            if dow==6:continue
            if tid=='E1':spoke=spokes[dow%len(spokes)];rt(base,spoke,timestamp(d,6),tail,'existing_KEEP',False);continue
            spoke=spokes[dow%3%len(spokes)]
            if distance(base,spoke)>3000:
                unserved.append(dict(tail=tid,day=d.isoformat(),pair=f'{base}-{spoke}',reason='RANGE_SCREEN_GT3000_NOT_ECONOMIC_REJECTION'));continue
            if bank and block(base,spoke)*4<=600:
                # Return to hub at11:00, second departure12:00. 60-minute transfer.
                first=timestamp(d,11+wi*.1)-timedelta(minutes=block(base,spoke)*2+45)
                rt(base,spoke,first,tail,'hub_bank')
                rt(base,spoke,timestamp(d,12+wi*.1),tail,'hub_bank')
            else:
                rt(base,spoke,timestamp(d,6.5+wi*0.1),tail,'radial')
                if bank:unserved.append(dict(tail=tid,day=d.isoformat(),pair=f'{base}-{spoke}',reason='BANK4LEGS_GT10H_RADIAL_STAGE_ONLY'))
    flights.sort(key=lambda f:f['departure_utc'])
    return dict(flights=flights,assignments=assignments,fleet_calendar=tails,unserved=unserved)

@lru_cache(maxsize=None)
def p05_market(a,b,day,scenario):
    m=day[:7];n=calendar.monthrange(int(day[:4]),int(day[5:7]))[1]
    return D.market(a,b,m,scenario,segment='travel_date:'+day,cohort_weight=1/n)

def products_for_day(flights,scenario='base',allow_transfer=True):
    """P05 producer_fragment without its O(all_24month_flights²) cross-date scan."""
    fs=[f for f in flights if f['saleable_seats']>0]
    if not fs:return {'markets':[],'products':[]}
    # Delegation to the unchanged P05 builder is per date; no date can share inventory.
    frag=p05.producer_fragment(fs,scenario)
    if not allow_transfer:
        frag['products']=[p for p in frag['products'] if len(p['legs'])<=1]
    for p in frag['products']:
        p['coverage']='P09: дата полного предложенного календаря; SCENARIO_NOT_IDENTIFIED'
        if p['owner']=='RW':
            p['source_id']='P09_DATED_SCHEDULE_P05_MODEL'
            p['as_of']='2026-11-12';p['booking_lead_days']=30
            p['cash_profile']=[dict(date=(date.fromisoformat(p['departure_date'])-timedelta(days=30)).isoformat(),fraction=1)]
    return frag

def pair_fragments(pfs,kfs,scenario,allow_transfer=True,response='passive'):
    pf=products_for_day(pfs,scenario,allow_transfer);kf=products_for_day(kfs,scenario,True)
    markets={core.pool_key(m):m for m in pf['markets']+kf['markets']}
    outside={}
    for x in pf['products']+kf['products']:
        if x['owner']!='RW':outside[x['product_id']]=x
    rules=[]
    if response=='response10':
        c=p05.coefficients(scenario)
        for x in outside.values():
            if x.get('outside_component')=='UNREPRESENTED_EXISTING_AIR':
                rules.append(dict(demand_pool_id=x['demand_pool_id'],month=x['month'],customer_segment=x['customer_segment'],rw_frequency_at_least=1,target_product_ids=[x['product_id']],gross_fare_multiplier=1,frequency_multiplier=1,intercept_delta=c['price_per_rub']*x['reference_gross_fare']*(-.1),assumption_id='P09-RESPONSE'))
    for frag in [pf,kf]:
        frag['markets']=list(markets.values())
        frag['products']=list(outside.values())+[x for x in frag['products'] if x['owner']=='RW']
        frag['response_policy']=dict(response_policy_id='P09-'+response,rules=rules,assumption_id='P09-RESPONSE')
    return pf,kf

def econ_event(eid,category,q,rate,month_,source,aid='P09-COST',payments=True):
    e=dict(economic_event_id=eid,owner=eid,category=category,scope='affected_business',driver_unit='named_driver',quantity=q,rate=rate,amount=None if q is None or rate is None else q*rate,currency='RUB',price_year=2026,fx_policy='constant_2026_RUB',accrual_month=month_,noncash=False,avoidability='explicit_scenario',shared_event_id=eid,source_id=source,assumption_id=aid,cash_plan_status='explicit' if payments and rate is not None else 'unknown')
    if payments and rate is not None:
        y,m=map(int,month_.split('-'));pay=date(y,m,calendar.monthrange(y,m)[1])+timedelta(days=30)
        e['payments']=[dict(date=pay.isoformat(),fraction=1)]
    return e

COSTROWS=list(csv.DictReader((ROOT/'subject/P04/cost_ranges.csv').open()))
COSTS={x['cost_id']:x for x in COSTROWS}
def economic_events(cal,scenario,programme):
    events=[]
    c='base_point' if scenario=='base' else 'cautious_point'
    rates={k:float(COSTS['HIST-'+k][c]) for k in ['fuel_t_per_hour','fuel_t_per_cycle','mro_rub_per_hour','crew_rub_per_hour','navigation_rub_per_hour']}
    bymonth=defaultdict(list)
    for f in cal['flights']:bymonth[f['departure_utc'][:7]].append(f)
    for m,fs in bymonth.items():
        bh=sum((p05.utc(f['arrival_utc'])-p05.utc(f['departure_utc'])).total_seconds()/3600 for f in fs)
        fuel=bh*rates['fuel_t_per_hour']+len(fs)*rates['fuel_t_per_cycle']
        events.append(econ_event(m+':fuel','variable_cost',fuel,136300,m,'P04:UFA-fuel-20261111;HIST-fuel;P09 территориальный/PD8 аналог'))
        for key in ['mro_rub_per_hour','crew_rub_per_hour','navigation_rub_per_hour']:
            events.append(econ_event(m+':'+key,'variable_cost',bh,rates[key],m,'P04:HIST-'+key))
        for airport,n in Counter(f['origin_airport'] for f in fs).items():
            for key in ['takeoff_landing','security']:
                row=COSTS.get(airport+'-'+key,COSTS['UFA-'+key]);rate=float(row['value'])
                events.append(econ_event(m+':'+airport+':'+key,'variable_cost',49.45*n,rate,m,'P04:'+row['cost_id']+';P09 mapped turn scenario'))
    # Common committed aircraft charge is retained even while idle/reserve.
    for t in cal['fleet_calendar']:
        for m in MONTHS:
            if t['transfer_date'][:7]<=m:
                e=econ_event('SHARED:'+t['aircraft_id']+':'+m,'aircraft_use',1,None,m,'P04:UNK-lease-'+t['variant'],'P09-MISSING')
                e['driver_unit']='tail_month';events.append(e)
    return events

def make_bundle(programme,delivery,scenario,cal,fragments,response='passive',evaluation_id=None):
    pid=programme['programme_id'];eid=evaluation_id or ':'.join([pid,delivery,scenario,response]);kid=':'.join(['KEEP',delivery,scenario,response])
    markets=[m for f in fragments for m in f['markets']];products=[p for f in fragments for p in f['products']]
    mk={core.pool_key(m):m for m in markets};markets=list(mk.values())
    pids=[p['product_id'] for p in products];assert len(pids)==len(set(pids))
    c=dict(evaluation_id=eid,programme_id=pid,programme_version=VERSION,fleet_scope_id='CASE_SJ',external_scenario_id=scenario,delivery_calendar_id='P09-'+delivery,market_version=p05.VERSION,choice_version=p05.VERSION,cost_version='P04final+P09-explicit-analogue-v1',response_policy_id='P09-'+response,evaluation_mode='fixed_programme',decision_date='2026-11-12',information_set_id='P09-pinned-20261112',keep_evaluation_id=eid if pid=='KEEP' else kid,input_manifest_sha256='pending',period_start='2027-01',period_end='2028-12',cash_start='2026-12',price_year=2026,affected_scope_id='P09-common-affected-conditional-with-unknown-remainder')
    calendars=[]
    for pool,segment in sorted({(m['demand_pool_id'],m['customer_segment']) for m in markets}):
        present={m['month'] for m in markets if m['demand_pool_id']==pool and m['customer_segment']==segment}
        calendars.append(dict(demand_pool_id=pool,customer_segment=segment,zero_months=[m for m in MONTHS if m not in present],unknown_months=[],assumption_id='P09-SCOPE',zero_reason='Датированная когорта невозможна в другом календарном месяце; не отсутствие рынка.'))
    events=economic_events(cal,scenario,programme)
    cov={k:dict(status='unknown',event_ids=[],rationale='Точный недостающий компонент в parameterledger; subtotal не полный бюджет',assumption_id='P09-MISSING') for k in ['variable_cost','base','aircraft_use','reserve','startup','exit','support']}
    cov['variable_cost']['event_ids']=[e['economic_event_id'] for e in events if e['category']=='variable_cost']
    cov['aircraft_use']['event_ids']=[e['economic_event_id'] for e in events if e['category']=='aircraft_use']
    cov['support']=dict(status='not_applicable',event_ids=[],rationale='Отдельная ветвь без поддержки, право/будущий платёж не установлены',assumption_id='P09-SUPPORT')
    b=dict(context=c,markets=markets,market_calendar=calendars,products=products,flights=cal['flights'],fleet_calendar=cal['fleet_calendar'],assignments=cal['assignments'],contracts=[],economic_events=events,cash_events=[],opening_balances=[],assumptions=ASSUMPTIONS+P05_ASSUMPTIONS,input_manifest=[{k:r[k] for k in ['source_id','commit','path','sha256']} for r in PINS if r['source_id'] in ['P05','P06','P04','P03']],choice_model=p05.coefficients(scenario),response_policy=dict(response_policy_id='P09-'+response,rules=[r for f in fragments for r in f['response_policy']['rules']],assumption_id='P09-RESPONSE'),cost_coverage=cov,cash_coverage={k:'unknown' for k in ['operating','investing','tax','financing','finance_interest']},cash_policy=dict(opening_cash=None,minimum_cash=None,project_opening_cash=None,project_minimum_cash=None,assumption_id='P09-CASH'),resource_operators=['RW_SCENARIO'],accounting_policy='operating_aircraft_use_excludes_interest',information_set=dict(information_set_id=c['information_set_id'],facts=[dict(fact_id='P05-P06-source-pins',available_at='2026-11-12')]),keep_policy=dict(keep_policy_id='P09-future-KEEP-v1',future_period=['2027-01','2028-12'],resource_policy='Те же committed tails и календарь, включая неиспользуемый резерв',existing_business='Условный E1 сохраняется в обеих сторонах; unknown affected remainder остаётся отдельной функцией, не0',alternative_new_resource_use='Усиление существующих SVX направлений теми же новыми рабочими бортами',excluded_unaffected_scope='Неизменный бизнес вне затронутого спроса сокращается; затронутый остаток неизвестен',avoidable_cost_rules='Полные общие tail obligations сохранены; переменные драйверы по датированным рейсам',assumption_id='P09-KEEP'),programme_target=dict(branch='main' if delivery=='phased' else 'resource_shortfall',rationale='8–12 проектных airportpairs на конец2028; deficit stage допускает меньше',assumption_id='P09-SCHEDULE'),metric_adapter=None)
    return core.seal(b)

KEEP=dict(programme_id='KEEP',label='Будущий KEEP с тем же committed ресурсом',working_slots=[dict(base='SVX',spokes=KEEP_DEST[i:i+3],bank=False) for i in [0,3,0]])

def build_pair(programme,delivery='phased',scenario='base',response='passive',dates=None):
    pc=build_calendar(programme,delivery);kc=build_calendar(KEEP,delivery)
    if dates is not None:
        for c in [pc,kc]:
            c['flights']=[f for f in c['flights'] if f['departure_utc'][:10] in dates]
            ids={f['flight_instance_id'] for f in c['flights']};c['assignments']=[a for a in c['assignments'] if a['flight_instance_id'] in ids]
    byp=defaultdict(list);byk=defaultdict(list)
    for f in pc['flights']:byp[f['departure_utc'][:10]].append(f)
    for f in kc['flights']:byk[f['departure_utc'][:10]].append(f)
    pp=[];kk=[]
    for day in sorted(set(byp)|set(byk)):
        p,k=pair_fragments(byp[day],byk[day],scenario,programme.get('transfers',True),response);pp.append(p);kk.append(k)
    return make_bundle(programme,delivery,scenario,pc,pp,response),make_bundle(KEEP,delivery,scenario,kc,kk,response)

if __name__=='__main__':
    control=dict(programme_id='CONTROL_SVX_UFA_OMS',label='Контроль одной пары с будущим KEEP',working_slots=[dict(base='SVX',spokes=['UFA'],bank=False)],transfers=True)
    p,k=build_pair(control,dates={'2028-12-04','2028-12-05'})
    result=core.compare(p,k)
    for n,j in [('control_programme.json',control),('control_compare_input.json',dict(project=p,keep=k)),('control_compare_result.json',result),('parameterledger.json',ASSUMPTIONS+P05_ASSUMPTIONS)]:dump(ROOT/'early'/n,j)
    print(json.dumps(dict(status=result['project']['status'],delta=result['delta_summary'],thresholds=result['thresholds'],operations=result['project']['operations']['status'],flights=len(p['flights']),sha256=digest(result)),ensure_ascii=False))
