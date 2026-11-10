#!/usr/bin/env python3
"""Pinned, read-only source audit. --write writes only this package, no model replay."""
import argparse
import ast
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PINS = {
    'NO': '2f03b693a62c219e9475fcd1e26295039f6a49d7',
    'NB': 'b91e0672af396bacd91651abeff8732fa733859d',
    'NL': '1654110dfdc3f6737aebce95e46dd993d631be5b',
    'C': '93fa5cf4a10ab67e05c93d19fc5375fc58ef9299',
    'S': '6ec84a7d2a6eb50b547a61df82fc5a424f48f146',
    'M': 'a77e4cfbd14e560d26407479b7252cfcb15f4f41',
    'F': '79281803e49763d6ff22c3d06efb941b5c86b53b',
    'P': 'f8b94a5c8b28e51664c5fff4a11606fb8f41c4d6',
}
METHOD = 'context/23_night_run_20261110/methods/'
FOLLOW = 'context/24_network_followup_20261110/'
DASH = 'context/24_decision_dashboard_20261110/'
CACHE = {}


def source(ref, path):
    key = (ref, path)
    if key not in CACHE:
        CACHE[key] = subprocess.check_output(['git', 'show', PINS[ref]+':'+path], cwd=ROOT)
    return CACHE[key]


def txt(ref, path):
    return source(ref, path).decode('utf-8-sig')


def rows(ref, path):
    return list(csv.DictReader(io.StringIO(txt(ref, path))))


def js(ref, path):
    return json.loads(txt(ref, path))


def ev(ref, path, start, end=None):
    lines = txt(ref, path).splitlines()
    end = end or start
    assert 1 <= start <= end <= len(lines), (ref, path, start, end, len(lines))
    return dict(ref=ref, commit=PINS[ref], path=path, line_start=start, line_end=end,
                excerpt='\n'.join(lines[start-1:end]),
                url=f'https://github.com/Mput13/case_championship/blob/{PINS[ref]}/{path}#L{start}-L{end}')


def near(a, b, tolerance=1e-6):
    assert math.isfinite(float(a)) and abs(float(a)-float(b)) <= tolerance, (a,b)


def leaf(ref, path, name, cls=None):
    tree = ast.parse(txt(ref, path))
    container = tree.body if cls is None else next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name==cls).body
    fn = next(x for x in container if isinstance(x,ast.FunctionDef) and x.name==name)
    namespace = {'math':math}
    exec(compile(ast.Module(body=[fn],type_ignores=[]), '<pinned leaf function>', 'exec'), namespace)
    return namespace[name]


def formula_checks():
    # 1. A real Nastya route; exact geography and leaf function only, no Demand/model construction.
    route = rows('NL','data/processed/network_routes.csv')[0]
    assert (route['from'],route['to'],route['variant'],route['scenario']) == ('OMS','MOW','Хаб OMS','base')
    geo = {r['iata']:r for r in rows('NL','data/processed/catchments.csv')}
    a,b = geo['OMS'],geo['SVO']  # Exact source nodes() definition maps MOW to SVO coordinates.
    la1,lo1,la2,lo2 = map(math.radians, [float(a['latitude_deg']),float(a['longitude_deg']),float(b['latitude_deg']),float(b['longitude_deg'])])
    km = 12742*math.asin(math.sqrt(math.sin((la2-la1)/2)**2+math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2))
    ap = rows('NL','data/assumptions/network.csv'); p = {r['parameter']:float(r['base']) for r in ap}
    pax = float(route['pax_year_segments'])/(2*p['weeks_per_year']*float(route['freq_week_each_way']))
    h = .5+km*1.1/750
    tonnes = 1.55*h+.2
    fuel = tonnes*134896
    cost = fuel+(35000+15000+6000)*h+96089+15000+500*pax
    actual_h,actual_cost = leaf('NL','src/network_model.py','leg_cost')(p,km,False,pax)
    near(actual_h,h); near(actual_cost,cost)
    assert round(km)==int(route['km']) and round(pax/100,2)==float(route['load_factor'])
    first = dict(id='ROW1_NASTYA_OMS_MOW',status='PASS_LEAF_ARITHMETIC_ROUNDED_PASSENGER_INPUT',
        source=ev('NL','data/processed/network_routes.csv',2), km_from_exact_coordinates=km,
        block_h=h, fuel_t=tonnes, fuel_RUB=fuel, per_flight_pax_from_rounded_annual=pax,
        cost_RUB=cost, delta_vs_exact_leaf_RUB=actual_cost-cost,
        unit_chain='km/(km/h)=h; (t/h*h+t/cycle)*RUB/t=RUB; h*RUB/h=RUB',
        caveat='Stored annual passenger count is rounded; this is not an exact unrounded route ledger replay or observed cost.')

    # 2. A real B mass-test row, including minutes->hours and the MTOW airport correction.
    caps = rows('C','context/17_aircraft_route_review/model/capacity.csv')
    index,c = next((i,r) for i,r in enumerate(caps,2) if r['flight_id']=='RRJ95B_MASS_TEST_H_GOJ_8_000' and r['scenario']=='cautious')
    cfg=js('C','context/15_team_update/model/configuration.json'); p=cfg['scenarios']['cautious']
    h=float(c['block_minutes'])/60; tonnes=p['fuel_t_per_hour']*h+p['fuel_t_per_cycle']
    fuel=tonnes*(p['fuel_rub_per_t']+p['fuel_uplift_rub_per_t'])
    basket=49.45*(553+499)+19300+8100+16668
    mass_adjustment=(45.88-49.45)*(553+499)*1.2
    cost=fuel+h*(55000+22000+8000)+basket*1.2+.4*100000+mass_adjustment
    near(cost,c['flight_variable_cost']); near(tonnes*1000,c['trip_fuel_kg'])
    allowed=min(40000-29500,45880-29500-(tonnes*1000+1500),41000-29500-1500)
    capacity=min(100,math.floor(allowed/100)); near(capacity,c['capacity_scenario'])
    near(29500+100*100+tonnes*1000+1500,c['takeoff_mass_at_100'])
    class ModelInput:
        scenarios=cfg['scenarios']
        old={'ufa_reference_basket_rub':basket}
    exact=leaf('C','scripts/build_team_comparison.py','flight_cost','Model')(ModelInput(),dict(c,block_minutes=float(c['block_minutes'])),'cautious')+mass_adjustment
    near(exact,cost)
    second=dict(id='ROW2_CIRI_GOJ_AER_B_CAUTION',status='PASS_COST_AND_ILLUSTRATIVE_MASS',
        source=ev('C','context/17_aircraft_route_review/model/capacity.csv',index),
        block_min=float(c['block_minutes']),block_h=h,fuel_t=tonnes,fuel_RUB=fuel,
        UFA_basket_before_factor_RUB=basket,MTOW_airport_adjustment_RUB=mass_adjustment,
        flight_variable_cost_RUB=cost,delta_vs_export_RUB=cost-float(c['flight_variable_cost']),
        available_payload_kg=allowed,capacity_scenario=capacity,
        caveat='DOW/reserves/burn are scenarios; mass arithmetic is not AFM, dispatch approval or SJ100 performance.')

    # 3. Fixed network, one real first leg plus a network ledger price identity and N demand mapping.
    legs=rows('F',FOLLOW+'model/dated_legs.csv'); chosen=[r for r in legs if r['common_network']=='D_SVX8']
    hours=sum(float(r['block_minutes'])/60 for r in chosen)
    tonnes=1.55*hours+.2*len(chosen); improvement=tonnes*(137996-134896)
    price=next(r for r in rows('F',FOLLOW+'price_sensitivity.csv') if (r['network'],r['scenario'],r['recipe'])==('D_SVX8','base','C'))
    near(hours,39.5); near(tonnes,64.425); near(improvement,price['delta_contribution'])
    pl=rows('F',FOLLOW+'price_sensitivity_legs.csv')[0]
    fl=next(r for r in chosen if r['id']==pl['flight_id'])
    t=1.55*float(fl['block_minutes'])/60+.2
    near(t,pl['fuel_t']); near(t*(-3100),pl['delta_cost'])
    mapping=rows('F',FOLLOW+'model/source_snapshot/methods/runs/common_demand_v1/demand_mapping.csv')[0]
    near(float(mapping['N_annual_proxy'])/104,mapping['N_week_direction_stress'])
    assert mapping['pair']=='AER-SVX' and float(mapping['C_week_direction'])==480
    baseline=rows('F',FOLLOW+'model/baseline_comparison.csv')
    cbase=next(r for r in baseline if (r['network'],r['scenario'],r['recipe'])==('D_SVX8','base','C'))
    nbase=next(r for r in baseline if (r['network'],r['scenario'],r['recipe'])==('D_SVX8','base','N'))
    near(cbase['flight_variable_cost'],nbase['flight_variable_cost'])
    gain_demand=float(nbase['contribution_before_base_fleet_opportunity'])-float(cbase['contribution_before_base_fleet_opportunity'])
    for key in ['sold_journeys','transfer_journeys','segment_pax','migrated_RW_total','gross_revenue','foregone_RW_revenue']:
        near(price[key],cbase[key])
    third=dict(id='ROW3_FOLLOWUP_D_SVX8_BASE_C',status='PASS_FIXED_COST_PRICE_IDENTITY_AND_DEMAND_UNIT_CONVERSION',
        source=ev('F',FOLLOW+'price_sensitivity.csv',2),
        first_leg=ev('F',FOLLOW+'price_sensitivity_legs.csv',2),first_leg_block_min=float(fl['block_minutes']),
        first_leg_fuel_t=t,first_leg_delta_RUB=t*(-3100),
        network_legs=len(chosen),network_block_h=hours,network_fuel_t=tonnes,
        price_before_RUB_t=137996,price_after_RUB_t=134896,price_improvement_RUB=improvement,
        contribution_before_RUB=float(price['before_contribution']),contribution_after_RUB=float(price['after_contribution']),
        demand_mapping=ev('F',FOLLOW+'model/source_snapshot/methods/runs/common_demand_v1/demand_mapping.csv',2),
        AER_SVX_C_journeys_week_direction=480,AER_SVX_N_annual_proxy=780000,AER_SVX_N_week_direction=7500,
        whole_network_C_to_N_contribution_delta_RUB=gain_demand,
        caveat='Price delta holds all sales fixed; C-to-N changes every mapped market. Neither experiment estimates price elasticity or validates winter demand.')
    return [first,second,third]


N='src/network_model.py'; A='data/assumptions/network.csv'
CORE='scripts/build_team_comparison.py'; ROUTE='scripts/build_aircraft_route_review.py'
CONFIG='context/15_team_update/model/configuration.json'; ASS='context/17_aircraft_route_review/assumptions.json'
COVERAGE=[]


def add(system, dimension, status, included, missing, *evidence):
    COVERAGE.append(dict(system=system,dimension=dimension,status=status,included=included,missing=missing,evidence=list(evidence)))


def coverage():
    s='Настя: old/dashboard/latest'
    add(s,'aircraft_type_variant','PROXY_TYPE','Семейство SSJ; явно приравнивает SJ-100 к SSJ-95B до сертификации; green gates 2300/2150 км.','Нет отдельной модели ПД-8, борта, AFM, массы, ветра и payload.',ev('NL',A,2),ev('NL','data/assumptions/range.csv',2,5),ev('NL','src/rules.py',11,25))
    add(s,'seats','MODELED','100 в сети; частота и LF cap85/80%. В отдельном latest demand comparator кресла берутся из таблицы типов.','Нет типо- и маршрутно-зависимой dispatch ёмкости; schedule seats не наблюдённый спрос.',ev('NL',A,2,5),ev('NL',N,120,122),ev('NL','src/demand_compare.py',77,110),ev('NL','data/assumptions/aircraft_seats.csv',1,22))
    add(s,'fuel','MODELED_SCENARIO','1.55/1.90 т/ч + .20/.25 т/цикл; total134896/161696 руб/т один раз.','Нет PD8 burn, OFP, контрактов по аэропортам/датам и налоговой сверки.',ev('NL',A,21,23),ev('NL',N,89,95))
    add(s,'block_costs','MODELED_PROXY','0.5+km*k/750 ч; k1.10/1.20; MRO35/55k,crew15/22k,nav6/8k руб/ч.','Нет фактических трасс/сезонного блока/технических затрат по варианту.',ev('NL',A,10,13),ev('NL',A,24,26),ev('NL',N,89,95))
    add(s,'airport_costs','COMMON_REFERENCE_SCENARIO','ground96089/115307 руб/рейс; deicing15/40k; pax500/650.','Уфа распространена как единая корзина; реальные договоры и состав по аэропортам неизвестны.',ev('NL',A,27,29),ev('NL',N,95))
    add(s,'calendar','AGGREGATE_ONLY','Недельная частота/часы; 7 дней; год52/48 недель.','Нет dated legs, UTC, суточной ротации, MCT, crew/slots; 48 недель не измеренный Ковёр.',ev('NL',A,6,8),ev('NL',A,32),ev('NL',N,188,208),ev('NL',N,383,398))
    add(s,'allocated_vs_available','REQUIREMENT_NOT_AVAILABILITY','fleet_cap10 включая1reserve; рабочие9; aircraft=ceil(hours/70)+1.','Ни доступных10, ни формируемого по датам нового N не доказано; строка о5 не отдельный main run.',ev('NL',A,6,8),ev('NL',N,208),ev('NL',N,388,395))
    add(s,'donor_opportunity','EXCLUDED','Вклад до аренды/базы/офиса; учтены лишь новые переменные расходы.','Нет KEEP/CANCEL/REPLACE конкретного донора, высвобождения борта/часов и opportunity.',ev('NL',N,16,18),ev('NL',N,391,395))
    add(s,'existing_network_competition','PARTIAL','Флаг direct из сохранённых связей; QSI proxy f_comp=D/(100*.8); общий OD budget исправлен в NB/NL.','Нет full incumbent расписания/capacity; не вычитает переток своих продаж и donor PnL.',ev('NL',N,106,117),ev('NL',N,278,314),ev('NL','src/demand_model.py',68,78))
    add(s,'demand_netfare','SCENARIO_PROXY','Сеть:known flow либоgravity; observed кромеairline_group; тариф2093+6.30*km/1636+4.78*km. Latest отдельные OD inversion,аналоги,schedule capacity иseasonality comparator.','Новый comparator не подаёт od_pairs/demand_estimates в сеть: она читает demand_pairs. Achieved net yield/elasticity UNKNOWN.',ev('NL',N,43,69),ev('NL',A,33,34),ev('NL','src/od_model.py',40,85),ev('NL','src/demand_compare.py',130,145),ev('NL','src/demand_compare.py',194,218),ev('NL','data/assumptions/demand.csv',3,10))
    add(s,'full_budget','NOT_COMPLETED','revenue-variable_cost за синтетический год.','Нет полного PnL, cash, lease, базы, start/exit, donor; subsidy неизвестна.',ev('NL',N,18),ev('NL',N,393,395))
    add(s,'phasing_delivery_newN_delay_2027_28','NOT_NUMERIC','fleet_cap является допущением; сертификация упомянута.','Нет функции поставок, ввода, delay/no-delivery, N(t), 2027/28 сезонного расчёта.',ev('NL',A,2,8),ev('NL',N,373,395))

    s='Цири:93fa/context15-17-21'
    add(s,'aircraft_type_variant','VARIANT_TESTS_NOT_PD8','B/B100/LR записи; B/LR illustrative mass tests; context21 UPPER100.','SJ100_PD8 performance и allocation пусты; B/LR не переносить.',ev('C',ROUTE,19,41),ev('C',ROUTE,223,233),ev('C',ASS,15,18))
    add(s,'seats','MODELED_BY_PROFILE','100 upper; mass profiles ограничивают capacity каждого leg; B cautious GOJ-AER75.','Context21 не использует mass-limited75: это отдельный UPPER100 profile.',ev('C',ROUTE,34,41),ev('C','scripts/build_team_proposals.py',21,31),ev('C','context/17_aircraft_route_review/model/capacity.csv',1338))
    add(s,'fuel','MODELED_SCENARIO','minutes/60;1.55/.20 либо1.90/.25;136300+1696/160000+1696.','Не измеренный типовой расход, reserve не оплаченный trip burn; нет PD8/контрактов.',ev('C',CONFIG,31,41),ev('C',CONFIG,51,61),ev('C',CORE,489,493),ev('C',ROUTE,37,41))
    add(s,'block_costs','DATED_PROXY','Published directional max; fallback30min+km/750 rounded5; +60 stress отдельный.','Не фактический dispatch/OFP; winter winds/route approvals UNKNOWN.',ev('C',ROUTE,20,29),ev('C',CORE,489,493),ev('C',ASS,9,15))
    add(s,'airport_costs','MASS_ADJUSTED_REFERENCE','UFA basket49.45t*(553+499)+19300+8100+16668; B45.88t adjustment;deicing expectation.','All-airport contracts/состав/налоги и реальный MTOW борта UNKNOWN.',ev('C',ROUTE,30,33),ev('C',CORE,489,493))
    add(s,'calendar','DATED_MODEL','7-13.12.2026 UTC; 45min turn;60-240min transfer; tail continuity;10h block/16h span,6days.','Не разрешённое расписание: crew/slots/airport windows/protected product UNKNOWN.',ev('C',CONFIG,3,16),ev('C',CORE,360,371),ev('C',CORE,433,478))
    add(s,'allocated_vs_available','ALLOCATED_NOT_AVAILABLE','Ceiling4working+1reserve; actual allocated D_SVX8=1/H4=2/H8=4; previous D=2.','Не фактические свободные борта; один reserve не мгновенно на двух базах.',ev('C','scripts/build_team_proposals.py',57,61),ev('C','context/21_team_proposals/comparison.csv',2,9),ev('C','scripts/build_conditional_decision.py',274,277))
    add(s,'donor_opportunity','PARTIAL_MIGRATION_ONLY','Вычитает foregone RW revenue, возвращает saved old pax variable; B0 reference.','Не снимает старые рейсы/их fixed flight costs; нет названного донора или доказанного высвобождения.',ev('C',ROUTE,53,68),ev('C',CONFIG,71,74),ev('C','scripts/build_team_proposals.py',60,61))
    add(s,'existing_network_competition','PARTIAL_SCENARIO','WZ dated seats cap, migration60/80% known versus5/10%unknown; transfer competition.65.','Не полная residual capacity/частоты конкурентов; не наблюдаемый переток.',ev('C',ROUTE,74,84),ev('C',CORE,313,327),ev('C',ROUTE,47,63))
    add(s,'demand_netfare','EXPLICIT_SCENARIOS','Distance bands endpoint/week/direction; stage16 setup задаёт local_peak.45/.30 вместо старогоconfig capture;transfer competition.65;fare_once;oldfare отдельно.','PaidOD,achieved netyield,seasonality,elasticity UNKNOWN. Effective setup важнее старогоconfiguration export.',ev('C',CORE,313,327),ev('C','scripts/build_conditional_decision.py',28,39),ev('C','context/16_conditional_decision/assumptions.json',40,45),ev('C',ROUTE,47,65),ev('C',CONFIG,73,74))
    add(s,'full_budget','THRESHOLDS_NOT_FULL_BUDGET','Stage16 fixed500k/allocated working+reserve/week, base500k stress и inverse thresholds.','Stage21 contribution исключает actual fixed/base/opportunity; cash/deposits/start/exit неизвестны.',ev('C','context/16_conditional_decision/assumptions.json',45,48),ev('C','scripts/build_conditional_decision.py',317,335),ev('C',CONFIG,17,19))
    add(s,'phasing_delivery_newN_delay_2027_28','QUALITATIVE_ROADMAP','Roadmap H1/H22027,H1/H22028; delivery gate >=H22027; delay->reduce/defer, existing SSJ fallback.','Нет числа/даты приёмки и ramp-up, сертификации/ТО, сезонной экономики или delay-ledger.',ev('C','context/15_team_update/roadmap_to_2028.csv',2,6))

    s='Цири:stage22/6ec (screen only)'
    for d,status,included,missing,*e in [
        ('aircraft_type_variant','SCREEN_ONLY','ssj_mro weight8;ssj_ops reference0.','Нет performance/PD8 economics.',ev('S','context/22_stage1_audit/recommended_weights.csv',12,16)),
        ('seats','OUT_OF_SCOPE','Городской балл.','Кресла не рассчитывает.',ev('S','src/stage1_audit_rules.py',1,5)),
        ('fuel','OUT_OF_SCOPE','Нет нового fuel расчёта.','Сохранившийся network_model — legacy2f, не новая экономика Цири.',ev('S','src/stage1_audit_rules.py',133,137)),
        ('block_costs','OUT_OF_SCOPE','Критерии географии/режима.','Нет нового блока/стоимости.',ev('S','src/stage1_audit_rules.py',133,137)),
        ('airport_costs','OUT_OF_SCOPE','Нет денежной модели.','Нет актуализации аэропортовых ставок.',ev('S','src/stage1_audit_rules.py',1,5)),
        ('calendar','OUT_OF_SCOPE','Снимок скоринга.','Шаги2-4/maps retained,NOT verified.',ev('S','src/stage1_audit_rules.py',133,137)),
        ('allocated_vs_available','UNKNOWN','Опорный статус отделён от физической базы.','Нет выделенных/доступных бортов.',ev('S','src/stage1_audit_rules.py',69,74)),
        ('donor_opportunity','OUT_OF_SCOPE','Нет donor функции.','Не оценка замены существующей сети.',ev('S','src/stage1_audit_rules.py',1,5)),
        ('existing_network_competition','SCREEN_ONLY','Support modes; слабые competitor flags->UNKNOWN; gate>=500.','База конкурента не route share.',ev('S','src/stage1_audit_rules.py',33,39),ev('S','src/stage1_audit_rules.py',64,74)),
        ('demand_netfare','PROXY_NOT_SALES','transfer demand proxy с полным диапазоном; городские веса.','Нет OD/netfare; top3 не прибыль.',ev('S','src/stage1_audit_rules.py',98,101)),
        ('full_budget','OUT_OF_SCOPE','Не рассчитывает.','Нельзя переводить score в деньги.',ev('S','src/stage1_audit_rules.py',1,5)),
        ('phasing_delivery_newN_delay_2027_28','OUT_OF_SCOPE','Сохранён период источника support2026/27.','Нет новогоN(t) или программы2027/28.',ev('S','src/stage1_audit_rules.py',69,74)),
    ]: add(s,d,status,included,missing,*e)

    s='Общие методы:a77'
    add(s,'aircraft_type_variant','INHERITED_UPPER100','Supply context21/93fa; не новая типовая модель; source results projection отдельно.','Нет PD8 performance; legacy2f годовой контур не приводится к типу автоматически.',ev('M',METHOD+'common_demand_contract.json',6,15),ev('M',METHOD+'final_model_projection.py',13,35))
    add(s,'seats','INHERITED_FIXED','Наследует per-leg capacity; расходует одно место на каждом leg через simulate.','Не новый payload/вариант/dispatch.',ev('M',METHOD+'common_demand.py',68,103))
    add(s,'fuel','MODELED_INHERITED','Тот же flight_cost с /60 и commodity+uplift; per-flight checks.','Нет PD8 burn/местных контрактов.',ev('M',METHOD+'common_demand.py',38,43),ev('M',METHOD+'common_demand.py',124,132))
    add(s,'block_costs','INHERITED_DATED','Сохранённые dated minutes context21; отдельный resource hours gate для Насти.','Hours gate не tail schedule; Nastya7days versus common6days.',ev('M',METHOD+'resource_comparison.py',15,24))
    add(s,'airport_costs','COMMON_UFA_SCENARIO','Корзина49.45t;airport_factor;deicing.','Нет контрактов по реальным leg airports.',ev('M',METHOD+'common_demand.py',38,43))
    add(s,'calendar','FIXED_SOURCE_CALENDAR','Exact flight IDs/dates; portfolio source tail namespaces и45min continuity.','Не совместная переупаковка на меньшее число бортов; не operating approval.',ev('M',METHOD+'portfolio_comparison.py',29,48))
    add(s,'allocated_vs_available','EXPLICIT_RESOURCE_GATES','working sum,4working+1reserve gate; larger envelope explicitly conditional.','Никакого confirmed future fleet; нет даты появления нового N.',ev('M',METHOD+'portfolio_comparison.py',64,87),ev('M',METHOD+'final_variant_synthesis.py',34,38))
    add(s,'donor_opportunity','SYMBOLIC_AND_FIXTURE','Общий own migration pool; KEEP/CANCEL/REPLACE fixture; donor delta условно в budget.','Не реальный named donor, не освобождённый парк; fixture не доход компании.',ev('M',METHOD+'common_demand.py',81,99),ev('M',METHOD+'budget_thresholds.py',140,166),ev('M',METHOD+'final_variant_synthesis.py',64,71))
    add(s,'existing_network_competition','CONTROLLED_POLICY','Frozen migration/caps; standalone claims D guard отдельно от pooled Q(f).','D guard не требует нового Q(f); конкурентные данные/перетоки остаются сценарными.',ev('M',METHOD+'portfolio_guard_comparison.py',9,35),ev('M',METHOD+'portfolio_comparison.py',69,79))
    add(s,'demand_netfare','CONTROLLED_RECIPE_EXPERIMENT','C weekly scenario versus N annual/104 BOTH scenarios; fares fixed; noZIA->MOW.','Не full Nastya replay/зимний endpointOD/оценка эластичности.',ev('M',METHOD+'common_demand.py',144,167),ev('M',METHOD+'common_demand_contract.json',10,18))
    add(s,'full_budget','SYMBOLIC_NOT_NUMERIC','C-(working+reserve)*F-base*B-O; cash fixture; actualFullPnL=NULL.','Нет договорныхF/B/other, реального donor/cash/start/exit/seasonality.',ev('M',METHOD+'budget_thresholds.py',115,120),ev('M',METHOD+'final_variant_synthesis.py',59,75))
    add(s,'phasing_delivery_newN_delay_2027_28','CONDITIONAL_ENVELOPE_ONLY','Portfolio выше4 рабочих явно не подтверждён будущим парком.','Нет deliveries/rampup/delay-year расчёта.',ev('M',METHOD+'portfolio_comparison.py',83,107),ev('M',METHOD+'resource_comparison.py',38,40))

    s='Коллегиальный followup:792818'
    add(s,'aircraft_type_variant','INHERITED_NOT_UPDATED','C21 supply; owner54cd snapshot separate; operational family facts only.','Нет новой типовой модели/PD8/подтверждения ARH-MRV payload.',ev('F',FOLLOW+'model/build_baseline.py',20,33),ev('F',FOLLOW+'research/operations.md',11,15))
    add(s,'seats','FIXED_UPPER100','Сохраняет64legs и supply; нет numerical replacements.','Нет нового capacity после research.',ev('F',FOLLOW+'model/finalize_integration.py',175,190),ev('F',FOLLOW+'model/final_round/integration_receipt.json',7,10))
    add(s,'fuel','SEPARATE_PRICE_SCENARIO','137996->134896 total (delta3100/t); commodity=total-uplift; owner134896 once.','Не принятый контракт; burn/hours/cautious не меняются.',ev('F',FOLLOW+'model/finalize_integration.py',155,172),ev('F',FOLLOW+'model/finalize_integration.py',183,203),ev('F',FOLLOW+'research/costs_final.md',7,11))
    add(s,'block_costs','UNCHANGED_FIXED','64 dated leg times; delta fuel_t*delta commodity; h=min/60.','Нет новых measured block/crew/MRO.',ev('F',FOLLOW+'model/finalize_integration.py',180,203))
    add(s,'airport_costs','REFERENCE_ONLY','Уточнены scope,MTOW,pax,uplift и tax статусы;0 replacements.','PDF заново не подтверждены; actual all-airport costs неизвестны.',ev('F',FOLLOW+'research/costs_final.md',15,25))
    add(s,'calendar','FIXED_MODEL_ONLY','Original dated legs7-13Dec; operations gates отмечены.','Target-week published RW itinerary,MCT,protected ticket не подтверждены.',ev('F',FOLLOW+'research/operations.md',3,15))
    add(s,'allocated_vs_available','UNKNOWN_PRESERVED','Owner handoff просит dated resource; no aircraft assignment admitted.','Fullfleet/crew/MRO contracts и available tails UNKNOWN.',ev('F',FOLLOW+'research/operations.md',9,15),ev('F',FOLLOW+'model/integrate_once.py',230,233))
    add(s,'donor_opportunity','UNCHANGED_EXCLUDED','Own migration inherited; no donor savings/subsidy added.','Нет named donor savings, opportunity/exit.',ev('F',FOLLOW+'price_scenario_bridge.json',44,49),ev('F',FOLLOW+'model/integrate_once.py',230,233))
    add(s,'existing_network_competition','CONTEXT_ONLY','14/16 planned SVX departures reconfirmed; no numeric admission.','Implicit year/performed/residual seats UNKNOWN; не новый capture.',ev('F',FOLLOW+'research/market_final.md',12,24))
    add(s,'demand_netfare','UNCHANGED_SCENARIOS','211k/785k annual,16k Jan historical; C/N unchanged; net yields UNKNOWN.','780k frozen N не заменён785k; price sensitivity не demand response.',ev('F',FOLLOW+'research/market_final.md',7,8),ev('F',FOLLOW+'research/market_final.md',18,24),ev('F',FOLLOW+'model/finalize_integration.py',214,224))
    add(s,'full_budget','NULL_PRESERVED','12 final rows delta0; fullPnL/peakcash=NULL; 50 findings apply=false.','FINAL означает завершённый раунд; не бюджет/launch.',ev('F',FOLLOW+'model/final_round/integration_receipt.json',1,15),ev('F',FOLLOW+'model/integrate_once.py',230,233))
    add(s,'phasing_delivery_newN_delay_2027_28','NOT_CALCULATED','Сохранены dated2026 fixed programs.','Нет annual2027/28,deliveryN/delay sensitivity.',ev('F',FOLLOW+'price_scenario_bridge.json',15,18),ev('F',FOLLOW+'model/integrate_once.py',230,233))

    s='Дашборд родителя:f8b94a5c'
    # Presentation coverage inherits explicitly; UI also evaluates affine/budget expressions.
    presentation={
        'aircraft_type_variant':('Показывает исходные model программы, source pins.','Нет собственного type/PD8 контракта.',17,24),
        'seats':('Сегменты/поездки из source или affine зависимости.','Новые capacity/performance не рассчитывает.',17,21),
        'fuel':('Сохранённый flight-variable-cost ledger.','Fuel-price792818 не импортирован; burn/commodity не редактирует.',37,41),
        'block_costs':('Наследует денежный flight cost.','Не пересчитывает block/crew/MRO по новому типу.',37,41),
        'airport_costs':('Наследует flight-variable-cost; отдельно scenarioF/B.','F/B не новые airport contracts.',19,24),
        'calendar':('Указывает7-13Dec; годовые52/48 в отдельном разделе.','Нет новой ротации/сезонного расписания.',29,31),
        'allocated_vs_available':('Фильтрдо4; показывает working+1reserve.','Нет фактической available fleet.',23,37),
        'donor_opportunity':('Показывает foregoneRW иsaved oldpax отдельно.','Нет named donor/offloaded flight cost.',37,41),
        'existing_network_competition':('ВыборQ(F) versus Dguard из source portfolios.','Новых competitor observations/marketfit нет.',21,24),
        'demand_netfare':('Affine C/N scale/blend; fares остаются fixed.','Нет нового ODfit/netyield/elasticity.',17,24),
        'full_budget':('UI вычитает(working+1)*F+newbase*B.','Otherterms должны быть равны; не actualfullPnL/cash.',19,24),
        'phasing_delivery_newN_delay_2027_28':('Сохраняет requirements/source ограничения.','НовыхN(t),поставок,delay и2027/28 экономики нет.',65,65),
    }
    for d,(included,missing,start,end) in presentation.items():
        add(s,d,'PRESENTATION_INHERITED',included,missing,ev('P',DASH+'dashboard.js',start,end),ev('P',DASH+'build_dashboard.py',27,46),ev('P',DASH+'README.md',24))
    assert len(COVERAGE)==72
    return COVERAGE


def findings():
    def f(id,severity,claim,conclusion,fix,*evidence):
        return dict(id=id,severity=severity,claim_under_review=claim,conclusion=conclusion,minimal_fix=fix,evidence=list(evidence))
    return [
        f('F01','S1_CLAIM_BOUNDARY','Тип самолёта вообще игнорировался / все числа уже относятся к SJ100_PD8.',
          'Оба крайних утверждения неверны. Тип/кресла/топливо учитываются через SSJ proxy; Цири дополнительно B/LR mass tests. PD8 model/dispatch/capacity отсутствует.',
          'Подписать SSJ proxy и profile; для SJ100_PD8 отдельный type/route performance input и повтор только затронутой экономики.',ev('NL',A,2),ev('C',ROUTE,34,41),ev('C',ROUTE,223,233),ev('C',ASS,18)),
        f('F02','S1_VERSION_MIX','Старый прямой результат Насти остаётся текущим / B3 не исправлен.',
          'NO повторяет OD между треугольниками; NB/NL агрегирует физическую пару. Saved direct base -280->-420 млн/год; cautious-5385->-5578, aircraft7->8. NB=NL для network code/parameters/summary. Parent nastya_network уже NB.',
          'Сохранить старые2f как historical; не переносить его author replay/repair на NB без отдельного label; не требовать повторного того же исправления.',ev('NO',N,278,298),ev('NL',N,278,341),ev('NO','data/processed/network_summary.csv',7,13),ev('NL','data/processed/network_summary.csv',7,13),ev('P',DASH+'build_dashboard.py',8,11)),
        f('F03','S1_RESOURCE_BOUNDARY','Ceiling10 /4+1 / aircraft row подтверждают доступный парк и поставки2027/28.',
          'Это ограничения/распределения. У Насти ceil(hours/70)+1 без календаря; у Цири context21 allocation1/2/4 рабочих при ceiling4. Delivered/free N(t) неизвестен.',
          'Отдельные поля allocated, available_by_date, reserve geography, delivery/commissioning dates и delay/no-delivery scenario; UNKNOWN не0.',ev('NL',A,6,8),ev('NL',N,388),ev('C','context/21_team_proposals/comparison.csv',2,9),ev('M',METHOD+'final_variant_synthesis.py',34,38)),
        f('F04','S1_BUDGET_BOUNDARY','Переменный вклад или inverse threshold — полный бюджет/launch decision.',
          'Существуют symbolic budget,500k stress,cash/donor fixtures; actual fixed/donor/cash/FullPnL отсутствуют. Own migration не равно снятию донорского рейса.',
          'Уточнить contribution before fleet/base/opportunity; заполнить named donor KEEP/CANCEL/REPLACE и датированный incremental PnL/cash.',ev('C',CONFIG,17,19),ev('C',CONFIG,71,74),ev('M',METHOD+'budget_thresholds.py',115,120),ev('M',METHOD+'budget_thresholds.py',140,166),ev('M',METHOD+'final_variant_synthesis.py',64,71)),
        f('F05','S1_EXPERIMENT_BOUNDARY','Followup снизил цены/спрос/порог на основании новых данных.',
          '50findings;0applied;12delta0. Отдельная author sensitivity меняет fuel commodity3100/t, не fares/demand. C/N и пороги при исходных costs сохранены.',
          'Отдельные labels factual admission, fuel-price scenario, C/N quantity experiment; α0.683509 и scale2.461771 не переносить на новыеcosts/PD8.',ev('F',FOLLOW+'model/final_round/integration_receipt.json',7,15),ev('F',FOLLOW+'price_scenario_bridge.json',29,49),ev('F',FOLLOW+'model/scenario_thresholds.csv',2,3),ev('F',FOLLOW+'model/finalize_integration.py',183,224)),
        f('F06','S1_LINEAGE_BOUNDARY','Stage22 заменяет сетевую модель93fa или исправляет её performance.',
          'Stage22 меняет city screening; steps2-4 retained NOTverified. Его src/network_model blob равен NO; C21/code отсутствуют в этом дереве, но сохранены в93fa/followup.',
          'Хранить отдельные lineage93fa C21 и6ec stage1; не объявлять удалённую в другой ветке экономику отменённой.',ev('S','src/stage1_audit_rules.py',133,137),ev('S','context/22_stage1_audit/final_comparison.csv',2,6),ev('F',FOLLOW+'provenance.json',4,8)),
        f('F07','S2_ROADMAP_PRECISION','Цири совсем не рассматривала2027/28 либо уже рассчитала deliveries/delay.',
          'Roadmap есть, включаяH22027 иdelay->reduce/defer; численногоN(t),ramp-up,сезонного бюджета нет.',
          'Сохранить qualitative roadmap; добавить delivery and induction ledger, пофазную допустимость/экономику.',ev('C','context/15_team_update/roadmap_to_2028.csv',2,6)),
        f('F08','S2_ATTRIBUTION','Ciri — Константин.',
          'Проверенные pins не устанавливают это соответствие. Git author/название файла не доказательство личности. Используется только Цири и exact source SHA.',
          'Не приписывать Константину без явного подтверждения; не менять авторство материалов.',ev('M',METHOD+'common_demand_contract.json',4,12)),
        f('F09','S2_LATEST_DEMAND_SCOPE','Настя вообще не считала endpointOD/сезонность или еёlatest уже пересчитала ими сетевую экономику.',
          'В NL есть od_model и demand_compare: link-count inversion с1transfer,таблица кресел по типам,аналоги,сценарная гостиничная сезонность. Они пишут od_pairs/demand_estimates; network_model по-прежнему читает demand_pairs и старый gravity fit.',
          'Сохранить новый модуль отдельным исследовательским результатом; не приписывать ему изменение network contribution/2027-28. Для интеграции нужен явный input contract и новыйrun.',ev('NL','src/od_model.py',40,85),ev('NL','src/demand_compare.py',77,110),ev('NL','src/demand_compare.py',145,157),ev('NL','src/demand_compare.py',194,218),ev('NL','data/assumptions/demand.csv',3,10),ev('NL',N,43,69)),
    ]


def extra_sources():
    for ref in ['NO','NB','NL','S']:
        for path in [N,A,'data/processed/network_summary.csv']:
            source(ref,path)
    for ref in ['NO','NB','NL']:
        source(ref,'data/processed/longlist_scores_min500.csv')
    for path in ['README.md','provenance.json','price_sensitivity.csv','price_sensitivity_legs.csv','owner_fuel_formula_check.json','owner_handoff_final.csv','model/baseline_comparison.csv','model/scenario_thresholds.csv','model/build_baseline.py','model/integrate_once.py','model/finalize_integration.py','model/network_contract.json','model/source_manifest.json','model/owner_handoff.csv']:
        source('F',FOLLOW+path)
    tree=subprocess.check_output(['git','ls-tree','-r','--name-only',PINS['F'],FOLLOW+'model/final_round',FOLLOW+'research'],cwd=ROOT,text=True)
    for path in tree.splitlines(): source('F',path)
    for path in ['src/network_model.py','data/assumptions/network.csv','data/processed/network_summary.csv']:
        assert source('NL',path)==source('NB',path)
        assert source('NL',path)==source('F',FOLLOW+'owner_snapshot/'+path)
    for path in ['common_demand.py','common_boundaries.py','common_demand_contract.json']:
        assert source('M',METHOD+path)==source('F',FOLLOW+'model/source_snapshot/methods/'+path)


def checks():
    out=formula_checks()
    extra_sources()
    receipt=js('F',FOLLOW+'model/final_round/integration_receipt.json')
    admission=rows('F',FOLLOW+'findings_admission.csv')
    final=rows('F',FOLLOW+'model/final_round/integration_comparison.csv')
    assert len(admission)==50 and all(r['apply']=='false' for r in admission)
    assert len(final)==12 and all(float(r['delta_contribution'])==0 for r in final)
    assert receipt['applied_findings']==0
    for filename,expected in receipt['output_sha256'].items():
        assert hashlib.sha256(source('F',FOLLOW+'model/final_round/'+filename)).hexdigest()==expected
    # Static lineage verification, no replay/optimisation; pin presence is an assertion.
    assert source('S',N)==source('NO',N)
    parent=js('P',DASH+'data.json')
    assert parent['nastya_network']==rows('NB','data/processed/network_summary.csv')
    parent_sources=js('P',DASH+'source_manifest.json')
    assert PINS['F'] not in {r['commit'] for r in parent_sources}
    for ref,sha in PINS.items():
        assert subprocess.check_output(['git','rev-parse',sha+'^{commit}'],cwd=ROOT,text=True).strip()==sha
    summary_changes=[]
    for ref in ['NO','NB','NL']:
        for i,r in enumerate(rows(ref,'data/processed/network_summary.csv'),2):
            if not r['hub']:
                summary_changes.append(dict(ref=ref,line=i,**r))
    return dict(status='PASS_SCOPED_OFFLINE',full_replay='NOT_RUN',live_sources='NOT_ACCESSED',
        checks=out,lineage=dict(NB_equals_NL_network_inputs_outputs=True,owner54_snapshot_equals_NL_network_inputs_outputs=True,
        stage22_network_code_equals_NO=True,followup_common_source_equals_M=True,
        parent_nastya_network_equals_NB=True,parent_has_no_F_source_pin=True),
        final_round=dict(findings=50,apply_true=0,comparison_rows=12,all_deltas_zero=True,receipt_output_hashes_match=True),
        nastya_direct_summary=summary_changes)


def write_json(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--write',action='store_true');args=parser.parse_args()
    cov=coverage();fs=findings();result=checks()
    manifest=dict(schema=1,as_of='2026-11-10',base_commit=PINS['P'],pins=PINS,
        access='LOCAL_GIT_OBJECTS_ONLY; no fetch, web or model main()',
        stage22_pin_resolution='User text stage22+6ec84...; verified40char object and followup provenance base_commit.',
        sources=[dict(ref=ref,commit=PINS[ref],path=path,sha256=hashlib.sha256(data).hexdigest(),
                      git_blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),bytes=len(data),lines=len(data.splitlines()),
                      url=f'https://github.com/Mput13/case_championship/blob/{PINS[ref]}/{path}')
                 for (ref,path),data in sorted(CACHE.items())])
    package=dict(schema=1,verdict='CHANGES_FOR_UNCONDITIONAL_SJ100_PD8_2027_28_CLAIMS',
                 source_models_changed=False,overall_winner=None,findings=fs)
    if args.write:
        write_json(HERE/'findings.json',package);write_json(HERE/'audit_checks.json',result)
        write_json(HERE/'source_manifest.json',manifest)
        with (HERE/'coverage.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,['system','dimension','status','included','missing','evidence_exact_path_line','evidence_urls']);w.writeheader()
            for r in cov:
                w.writerow({k:v for k,v in r.items() if k!='evidence'}|dict(
                    evidence_exact_path_line='; '.join(f"{e['commit']}:{e['path']}:{e['line_start']}-{e['line_end']}" for e in r['evidence']),
                    evidence_urls='; '.join(e['url'] for e in r['evidence'])))
        print(json.dumps(dict(status=result['status'],coverage_rows=len(cov),findings=len(fs),source_files=len(CACHE),formula_rows=3)))
    else:
        assert js_local('source_manifest.json')==manifest
        assert js_local('findings.json')==package
        assert js_local('audit_checks.json')==result
        with (HERE/'coverage.csv').open() as f:
            actual_coverage=list(csv.DictReader(f))
        expected_coverage=[]
        for r in cov:
            expected_coverage.append({k:v for k,v in r.items() if k!='evidence'}|dict(
                evidence_exact_path_line='; '.join(f"{e['commit']}:{e['path']}:{e['line_start']}-{e['line_end']}" for e in r['evidence']),
                evidence_urls='; '.join(e['url'] for e in r['evidence'])))
        assert actual_coverage==expected_coverage
        handoff=js_local('handoff.json')
        for path,expected in handoff['artifacts_sha256'].items():
            assert hashlib.sha256((HERE/path).read_bytes()).hexdigest()==expected,path
        print(json.dumps(dict(status='PASS_PACKAGE_SOURCE_HASHES_AND_THREE_ROWS',source_files=len(CACHE),coverage_rows=72,full_replay='NOT_RUN')))


def js_local(path): return json.loads((HERE/path).read_text())


if __name__=='__main__': main()
