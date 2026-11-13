#!/usr/bin/env python3
"""P40 conditional uncovered cost assembly. Writes ONLY this calculation directory.
No exporters, network research, git operations or source mutations.
Use network/.venv/bin/python3 -B calculation/build.py (pandas needed only for bounded10).
"""
import sys
sys.dont_write_bytecode = True
import csv
import hashlib
import importlib.util
import json
import math
from collections import Counter
from itertools import product
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
NET = ROOT / 'network'
BUD = ROOT / 'budget'
MAIN = ['OMS', 'GSV_MRV', 'AER_VOG', 'DIRECT2', 'HYBRID']
SOURCE = NET / 'source/f20000e7'

def read(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

API = module('p40_network_api', NET / 'api.py')
BA = module('p40_budget_api', BUD / 'budget_api.py')
P = json.loads((HERE / 'policy.json').read_text())
ASS = json.loads((BUD / 'assumptions.json').read_text())
PARAMS = {r['parameter_id']: r for r in read(BUD / 'cost_parameters.csv')}
BOQ = read(BUD / 'station_BoQ.csv')
ONCE = read(BUD / 'oneoff_cash.csv')

def table(name, rows):
    rows = list(rows)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with (HERE / name).open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, keys)
        w.writeheader()
        w.writerows(rows)

def dump(name, obj):
    (HERE / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def input_paths():
    # Explicit dependency files only; no directory hash, .venv or mutable whole-P40 pin.
    names = ['TASK.md', 'integration_policy.md', 'calculation/policy.json',
             'calculation/build.py', 'calculation/verify.py']
    names += ['network/' + x for x in [
        'README.md', 'api.py', 'build.py', 'CASES.json', 'annual_results.csv',
        'seasonal_results.csv', 'component_ledger.csv', 'seasonal_exposures.csv',
        'fleet_requirements.csv', 'route_ledger.csv', 'od_inventory.csv',
        'joint_OD_proof.json', 'source_manifest.json']]
    names += ['budget/' + x for x in [
        'README.md', 'budget_api.py', 'cost_parameters.csv', 'station_BoQ.csv',
        'oneoff_cash.csv', 'launch_totals.csv', 'assumptions.json',
        'coverage_netting_rules.csv', 'handoff.json']]
    srcnames = [
        'src/network_model.py', 'src/demand_model.py', 'src/rules.py', 'src/airports_meta.py',
        'data/assumptions/network.csv', 'data/assumptions/demand.csv',
        'data/assumptions/resort_airports.csv', 'data/assumptions/longlist_params.csv',
        'data/assumptions/subsidy_cap_84_103.csv', 'data/assumptions/subsidy_hub_airports.csv',
        'data/assumptions/siberia_fareast_regions.csv', 'data/assumptions/subsidy_special_fare.csv',
        'data/assumptions/bases.csv', 'data/assumptions/range.csv',
        'data/assumptions/south_west_regions.csv', 'data/raw/favt_subsidy_2026.csv',
        'data/manual/rw_routes_now.csv', 'data/manual/closed_airports.csv',
        'data/manual/airport_names.csv', 'data/processed/catchments.csv',
        'data/processed/od_fit.json', 'data/processed/od_pairs.csv',
        'data/processed/demand_estimates.csv', 'data/processed/demand_pairs.csv',
        'data/processed/airport_seasonality.csv', 'data/raw/tochno_selected.csv.gz']
    names += ['network/source/f20000e7/' + x for x in srcnames]
    return [ROOT / n for n in names]

def manifest():
    return [{'path': str(p.relative_to(ROOT)), 'sha256': sha(p), 'bytes': p.stat().st_size}
            for p in input_paths()]

def rate(key, budget):
    return float(PARAMS[key][budget])

def station_rows():
    out = []
    for r in BOQ:
        b = r['scenario']; q = float(r['qty']); u = r['unit']; rt = float(r['rate'])
        if r['item_id'] == 'it_support':
            q = float(r['coverage_hours_year']); rt = rt * 12 / float(r['effective_hours_FTE_year'])
            u = 'RUB/outsourced-hour'; periods = 1
        else:
            if b in P['ceil_staff_in'] and r['item_id'] in P['ceil_staff_groups']:
                q = math.ceil(q)
            periods = 12
        amt = q * rt * periods
        out.append(dict(variant=r['variant'], budget=b, item=r['item_id'], quantity=q,
                        periods=periods, rate=rt, rate_unit=u, annual_rub=amt,
                        fractional_BoQ_rub=float(r['amount_annual']),
                        rounding_delta_rub=amt-float(r['amount_annual']),
                        price_status=r['price_class'], quantity_status='AUTHOR_SCENARIO'))
    return out

STATIONS = station_rows()

def station_total(budget):
    rr = [r for r in STATIONS if r['variant'] == P['station_variant'][budget] and r['budget'] == budget]
    return sum(r['annual_rub'] for r in rr), sum(r['rounding_delta_rub'] for r in rr)

def it_hour(budget):
    r = next(r for r in BOQ if r['scenario'] == budget and r['item_id'] == 'it_support')
    return float(r['rate']) * 12 / float(r['effective_hours_FTE_year'])

def expense(v, cid, budget):
    """Quantities are for requested period; fixed cost coverage follows calendar months."""
    j = P['budget_scenarios'].index(budget)
    s = v['season']; w = 1 if s == 'annual' else P['season_weights'][s]
    d = v['drivers']; ap = v['airports']
    nonbase = sorted(set(ap) - {'OMS', 'MOW'})
    oms = 'OMS' in ap
    omsdep = ap.get('OMS', {}).get('departures', 0)
    mowdep = ap.get('MOW', {}).get('departures', 0)
    nonbasedep = sum(ap[a]['departures'] for a in nonbase)
    # Closed circuits are costing normalizers, not dated tail/crew rotations.
    circuit = omsdep if oms else 0
    circuit += (d['departures'] - 2 * omsdep) / 3
    crew_extra = circuit * P['crew_extra_share_of_closed_circuits'][j]
    at = d['transfer_journeys'] * P['irrops_transfer_affected_share'][j]
    al = d['local_journeys'] * P['irrops_local_direct_affected_share'][j]
    affected = at + al
    ir = ASS['irrops']
    paxnights = affected * ir['overnight_share_of_affected'][j] * ir['nights_per_overnight'][j]
    if oms:
        oms_affected = at + al * P['irrops_OMS_local_event_share']
        # In hybrid, only hub local journeys can generate the OMS local events.
        if cid.startswith('HYBRID'):
            hub_local = API.expenses_for('OMS', v['scenario'], s)['drivers']['local_journeys']
            oms_affected = at + hub_local * P['irrops_local_direct_affected_share'][j] * P['irrops_OMS_local_event_share']
    else:
        oms_affected = 0
    groups = oms_affected / P['irrops_people_per_event_group']
    q = {p['qty']: 0.0 for p in PARAMS.values()}
    q.update(
        covered_aircraft_years=P['retained_fleet'][cid]*w,
        uncovered_dcs_departures=d['departures']*P['dcs_uncovered_departure_share'][j],
        uncovered_outstation_months=len(nonbase)*12*w,
        uncovered_outstation_callout_departures=nonbasedep*P['outstation_callout_share'][j],
        uncovered_mow_coordination_departures=mowdep*P['mow_coordination_uncovered_share'][j],
        uncovered_oms_basing_aircraft_months=P['based_OMS_tails'][cid]*12*w,
        uncovered_extra_bag_services=omsdep*P['oms_additional_bag_order_share_of_OMS_departures'][j],
        uncovered_rep_workplace_services=omsdep*P['oms_additional_repdesk_share_of_OMS_departures'][j],
        single_room_nights=paxnights+P['crew_persons']*crew_extra,
        double_room_nights=0,
        uncovered_crew_person_days=P['crew_persons']*crew_extra,
        uncovered_crew_position_segments=P['crew_persons']*2*crew_extra,
        uncovered_crew_vehicle_trips=2*crew_extra,
        uncovered_passenger_meals=affected*ir['meals_per_affected'][j],
        uncovered_rebooked_journeys=affected*ir['rebooking_share_of_affected'][j],
        uncovered_bus_started_hours=groups*P['irrops_bus_started_hours_per_event_group'][j],
        uncovered_meal_distribution_services=groups*P['irrops_distribution_services_per_event_group'][j],
        oms_retained_months=12*w if oms else 0)
    ev = BA.evaluate(q, budget, P['station_variant'][budget], v['operating_subtotal_before_uncovered_rub'])
    station, delta = station_total(budget) if oms else (0, 0)
    delta *= w
    costs = ev['unit_costs'].copy()
    costs['station_OMS'] = station*w
    costs['mow_parking_analogue'] = P['based_MOW_tails'][cid]*12*w*rate('oms_parking',budget)*P['mow_parking_OMS_analogue_multiplier'][j]
    total = sum(costs.values())
    before = v['operating_subtotal_before_uncovered_rub']
    residual = before-total
    row = dict(case_id=cid, market=v['scenario'], budget=budget, season=s,
               retained_tails=P['retained_fleet'][cid], fixed_months=12*w,
               nonbase_stations=len(nonbase), nonbase_station_codes=';'.join(nonbase),
               network_subtotal_rub=before, included_costs_rub=v['included_costs_rub'],
               net_revenue_rub=v['net_revenue_after_old_fare_forgone_rub'],
               annual_or_period_recurring_rub=total, insurance_rub=costs['insurance'],
               residual_before_insurance_rub=residual+costs['insurance'],
               residual_after_recurring_rub=residual,
               station_OMS_rub=costs['station_OMS'], staff_rounding_delta_rub=delta,
               oms_basing_rub=costs['oms_parking'], mow_parking_analogue_rub=costs['mow_parking_analogue'],
               SLA_rub=costs['outstation_sla'], callout_rub=costs['outstation_callout'],
               dcs_rub=costs['dcs_net'], mow_coordination_rub=costs['mow_extra'],
               additional_bag_rub=costs['oms_extra_bag'], repdesk_rub=costs['oms_rep_desk'],
               passenger_irrops_rub=paxnights*rate('hotel_single',budget)+sum(costs[k] for k in ['irrops_meal','irrops_rebook','oms_bus','meal_distribution']),
               crew_extra_rub=P['crew_persons']*crew_extra*rate('hotel_single',budget)+sum(costs[k] for k in ['crew_perdiem','crew_position','crew_transfer']))
    qty = dict(case_id=cid, market=v['scenario'], budget=budget, season=s,
               quantity_status='AUTHOR_SCENARIO_ON_SOURCE_EXPOSURES',
               source_departures=d['departures'], source_local_journeys=d['local_journeys'],
               source_transfer_journeys=d['transfer_journeys'], source_fuel_t=d['fuel_t'],
               OMS_departures=omsdep, MOW_departures=mowdep, nonbase_departures=nonbasedep,
               nonbase_station_codes=';'.join(nonbase), closed_circuits=circuit,
               selected_crew_extra_circuits=crew_extra, affected_transfers=at,
               affected_local_direct=al, passenger_single_room_nights=paxnights,
               crew_single_room_nights=P['crew_persons']*crew_extra,
               OMS_expected_event_groups=groups,
               MOW_analogue_tail_months=P['based_MOW_tails'][cid]*12*w, **q)
    return row, qty, costs, ev

def launch(v, cid, budget, recurring_row):
    j = P['budget_scenarios'].index(budget)
    oms = 'OMS' in v['airports']; variant = P['station_variant'][budget]
    selected = [r for r in ONCE if r['scenario'] == budget and
                ((oms and r['item_id'].startswith(variant+'_')) or r['item_id'] == 'pool_security')]
    totals = Counter()
    for r in selected:
        totals[r['ledger']] += float(r['amount_cash'])
    # OMS fixed setup above covers OMS itself; every other physical-market interface once.
    markets = sorted(set(v['airports'])-{'OMS'})
    hours = len(markets)*P['it_configuration_hours_per_unique_nonOMS_market'][j]
    itsetup = hours*it_hour(budget)
    deployments = P['working_fleet'][cid]*P['crew_launch_deployments_per_working_tail'][j]
    crewsetup = deployments*(P['crew_persons']*(rate('hotel_single',budget)+rate('crew_perdiem',budget)+2*rate('crew_position',budget))+2*rate('crew_transfer',budget))
    totals['ONEOFF_EXPENSE'] += itsetup+crewsetup
    # Funding of selected already-expensed services, never another operating deduction.
    basis = sum(recurring_row[k] for k in ['oms_basing_rub','mow_parking_analogue_rub','SLA_rub','callout_rub','mow_coordination_rub','additional_bag_rub','repdesk_rub'])
    wc = basis/365*P['working_capital_prepay_days'][j]
    residual = recurring_row['residual_after_recurring_rub']
    return dict(case_id=cid, market=v['scenario'], budget=budget,
                oneoff_expense_rub=totals['ONEOFF_EXPENSE'], CAPEX_rub=totals['CAPEX'],
                refundable_deposits_rub=totals['REFUNDABLE_DEPOSIT'], working_capital_rub=wc,
                initial_owned_inventory_rub=0,
                launch_cash_rub=sum(totals.values())+wc,
                capex_depreciation_3y_rub=totals['CAPEX']/P['capex_life_years_accounting_stress'],
                steady_state_after_CAPEX_3y_stress_rub=residual-totals['CAPEX']/3,
                entry_year_PnL_if_full_steady_year_rub=residual-totals['CAPEX']/3-totals['ONEOFF_EXPENSE'],
                IT_setup_market_codes=';'.join(markets), IT_setup_markets=len(markets),
                IT_setup_hours=hours, IT_actual_hour_rate_rub=it_hour(budget), IT_setup_rub=itsetup,
                crew_setup_deployments=deployments, crew_setup_rub=crewsetup,
                working_capital_selected_daily_basis_rub=basis/365,
                refundable_pool_deposit_count=1,
                status='AUTHOR_SCENARIO; cash_not_annual_expense; entry_year_column_is_not_2027_forecast')

def summarise_source(nb, legs, ods, season):
    E = 52*nb.WEIGHT[season]
    totals = {k:sum(l[k] for l in legs)*E for k in nb.SUM_FIELDS}
    totals['transfer_journeys'] = sum(o['journeys'] for o in ods if o['kind']=='TRANSFER')*E
    totals['journeys'] = sum(o['journeys'] for o in ods)*E
    airports = {}
    for a in sorted({l['a'] for l in legs}|{l['b'] for l in legs}):
        ll = [l for l in legs if a in (l['a'],l['b'])]
        airports[a] = {'departures':sum(l['departures']/2 for l in ll)*E,
                       'boardings':sum(l['segments']/2 for l in ll)*E,
                       'arrivals':sum(l['departures']/2 for l in ll)*E,
                       'available_seats':sum(l['available_seats']/2 for l in ll)*E,
                       'transfer_connections':0}
    return dict(scenario='base',season=season,
                included_costs_rub=totals['cost_rub'],
                net_revenue_after_old_fare_forgone_rub=totals['net_revenue_rub'],
                operating_subtotal_before_uncovered_rub=totals['subtotal_rub'],
                drivers=totals,airports=airports, weekly_BH=totals['block_hours']/E)

def combine(v1, v2, season):
    out = dict(scenario='base', season=season)
    for key in ['included_costs_rub','net_revenue_after_old_fare_forgone_rub','operating_subtotal_before_uncovered_rub']:
        out[key] = v1[key]+v2[key]
    out['drivers'] = {k:v1['drivers'].get(k,0)+v2['drivers'].get(k,0)
                      for k in set(v1['drivers'])&set(v2['drivers'])
                      if v1['drivers'].get(k) is not None and v2['drivers'].get(k) is not None}
    out['airports'] = {}
    for a in sorted(set(v1['airports'])|set(v2['airports'])):
        x=v1['airports'].get(a,{}); y=v2['airports'].get(a,{})
        out['airports'][a] = {k:x.get(k,0)+y.get(k,0) for k in sorted(set(x)|set(y))}
    return out

def bounded10():
    """50 cached joint seasonal evaluations, 625 annual combinations, no other chains."""
    import numpy as np
    nb = module('p40_pure_network_build', NET/'build.py')
    nm,D,AS = nb.load_model()
    D.profiles = {r['iata']:np.array([float(r[f'm{i}']) for i in range(1,13)])
                  for r in read(SOURCE/'data/processed/airport_seasonality.csv')}
    D.rw = {nb.pair(r['a'],r['b']):float(r['freq_week_each_way']) for r in read(SOURCE/'data/manual/rw_routes_now.csv')}
    D.closed = nm.CLOSED
    # Reuse source methods, cache inputs of single_leg per season: no linear profit scaling.
    from functools import lru_cache
    single = nb.single_leg
    @lru_cache(None)
    def cached_leg(sc,a,b,s):
        return single(D,AS[sc],sc,a,b,s)
    nb.single_leg = lambda DD,AA,sc,a,b,s:cached_leg(sc,a,b,s)
    hubOD = {nb.pair(r['origin'],r['destination']) for r in read(NET/'od_inventory.csv') if r['case_id']=='OMS'}
    cache = {}; replay_errors = []
    for s in ['summer','winter']:
        for f1,f2 in product(range(3,8), repeat=2):
            fs={'GSV_MRV':{s:f1},'AER_VOG':{s:f2}}
            ll,oo,_ = nb.direct(D,AS['base'],'base',s,list(nb.CHAINS),fs)
            do = {nb.pair(o['origin'],o['destination']) for o in oo}
            assert not hubOD & do, 'common OD appeared'
            assert len(do)==6
            v = summarise_source(nb,ll,oo,s)
            if (f1,f2)==(7,7):
                api = API.expenses_for('DIRECT2','base',s)
                for k in ['included_costs_rub','net_revenue_after_old_fare_forgone_rub','operating_subtotal_before_uncovered_rub']:
                    err=abs(v[k]-api[k]); assert err<1e-4
                    replay_errors.append(err)
            hv = combine(API.expenses_for('OMS','base',s),v,s)
            objective = expense(hv,'HYBRID10','base')[0]['residual_after_recurring_rub']
            cache[(s,f1,f2)] = (v,hv,objective)
    best = None; feasible=0
    for f1s,f2s,f1w,f2w in product(range(3,8),repeat=4):
        sm=cache[('summer',f1s,f2s)]; wi=cache[('winter',f1w,f2w)]
        if max(sm[0]['weekly_BH'],wi[0]['weekly_BH'])>140+1e-9:
            continue
        feasible+=1; score=sm[2]+wi[2]
        candidate=(score,(f1s,f2s,f1w,f2w),sm,wi)
        if best is None or score>best[0]: best=candidate
    score,freq,sm,wi=best
    selected={}
    for cid,i in [('DIRECT2_10',0),('HYBRID10',1)]:
        selected[(cid,'summer')]=sm[i];selected[(cid,'winter')]=wi[i]
        selected[(cid,'annual')]=combine(sm[i],wi[i],'annual')
    info=dict(status='BOUNDED_OPTIMUM_NOT_GLOBAL_OR_DISPATCH_PROOF',
              market='base',budget='base',enumerated=625,feasible=feasible,
              cached_joint_direct_season_calls=50,
              frequencies_each_orientation=dict(GSV_MRV=dict(summer=freq[0],winter=freq[2]),
                                                 AER_VOG=dict(summer=freq[1],winter=freq[3])),
              DIRECT2_weekly_BH=dict(summer=sm[0]['weekly_BH'],winter=wi[0]['weekly_BH']),
              HYBRID10_best_residual_rub=score,retained_fleet=10,
              MOW_working=2,MOW_reserve=1,OMS_retained=7,
              full_7_7_replay_max_abs_error_rub=max(replay_errors),common_OD_intersection=[],
              limitations='No new OD/fare/chain; source nonlinear capture/monthly spill recalculated jointly. Only 3..7 integer frequencies in each season, not a timetable or global optimum.')
    table('bounded10_candidates.csv', [dict(season=s,GSV_MRV_freq=f1,AER_VOG_freq=f2,
          direct_weekly_BH=vv[0]['weekly_BH'],HYBRID10_central_period_residual_rub=vv[2],
          BH_fits_two_working=vv[0]['weekly_BH']<=140+1e-9)
          for (s,f1,f2),vv in cache.items()])
    return selected,info

def report(results,launches,bounded):
    def get(cid,m='base',b='base'):
        return next(r for r in results if r['case_id']==cid and r['market']==m and r['budget']==b)
    def m(v): return f'{v/1e6:,.3f}'.replace(',',' ')
    h=get('HYBRID');o=get('OMS');dr=get('DIRECT2');ten=get('HYBRID10')
    lines=['# Непокрытые расходы выбранного гибрида — условная смета', '',
      f"После выбранных recurring-добавок центральный остаток: **OMS {m(o['residual_after_recurring_rub'])} млн, DIRECT2 {m(dr['residual_after_recurring_rub'])} млн, HYBRID (11 бортов) {m(h['residual_after_recurring_rub'])} млн руб./модельный год**. Это steady-state после полного ввода сети, не полный 2027 год и не фактическая прибыль. Покупка/лизинг исключены из MAIN по указанию пользователя; страховка и все неподтверждённые количества — сценарии.", '',
      'Одна таблица: млн руб.; low/base/high — отдельные сметы при неизменном рыночном base. Последний столбец — рыночный cautious при центральной смете; сохранён базовый парк и 12 месяцев фиксированных услуг.', '',
      '| Контур | Бортов | До добавок base | Recurring base | До страховки base | Остаток low | Остаток base | Остаток high | cautious / смета base |',
      '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for cid in MAIN+['DIRECT2_10','HYBRID10']:
        r=get(cid); last='—' if cid not in MAIN else m(get(cid,'cautious')['residual_after_recurring_rub'])
        lines.append(f"| {cid} | {r['retained_tails']} | {m(r['network_subtotal_rub'])} | {m(r['annual_or_period_recurring_rub'])} | {m(r['residual_before_insurance_rub'])} | {m(get(cid,b='low')['residual_after_recurring_rub'])} | {m(r['residual_after_recurring_rub'])} | {m(get(cid,b='high')['residual_after_recurring_rub'])} | {last} |")
    lines+=['', 'GSV_MRV = MOW–GSV–MRV–MOW; AER_VOG = MOW–AER–VOG–MOW. Их standalone-парк по 3 борта **не складывается**: DIRECT2 пересчитан с общими MOW-ресурсами на 4 борта. Гибрид пересчитывает уникальные станции и депозит один раз. 113/568 млн из презентации — атрибуция внутри полной direct-сети; 143,323/598,294 млн здесь — только две выбранные цепочки, без произвольной замены чисел.', '',
      f"В центральных **{m(h['annual_or_period_recurring_rub'])} млн** HYBRID: станция OMS {m(h['station_OMS_rub'])}; страховка {m(h['insurance_rub'])}; OMS basing {m(h['oms_basing_rub'])}; MOW parking-аналог {m(h['mow_parking_analogue_rub'])}; SLA {m(h['SLA_rub'])}; callout {m(h['callout_rub'])}; DCS {m(h['dcs_rub'])}; MOW координация {m(h['mow_coordination_rub'])}; допбагаж {m(h['additional_bag_rub'])}; repdesk {m(h['repdesk_rub'])}; IRROPS пассажиров {m(h['passenger_irrops_rub'])}; дополнительный crew travel {m(h['crew_extra_rub'])}.", '',
      'Сметные единицы и границы:', '',
      '- Low: lean BoQ с дробными FTE; base: lean с ceil отдельно manager/coordinator/local_ops; high: expanded с ceil этих групп. ИТ остаётся подрядными часами. Количества BoQ — сценарии; зарплата, офис и ИТ — плановые ставки, heated storage — primary OMS за м²-месяц. Фактический штат и покрытие UNKNOWN. Полное сравнение lean/expanded и поправки — station.csv.',
      f"- Base lean: 2/2/2 FTE вместо 1,190/1,738/1,738; 400 outsourced IT часов × {it_hour('base'):.6f} руб./ч. Поправка округления **{m(h['staff_rounding_delta_rub'])} млн/год**. High expanded: 2/6/4 FTE, 1000 IT часов; выбранный офис15/15/25 м² и storage5/5/10 м² по BoQ.",
      '- Страховка3/8/20 млн руб./tail-year — выбранный stress, НЕ quote/рыночный диапазон. Retained7/3/3/4/11, резервы включены, при cautious не высвобождаются автоматически. Ошибочная ранняя строка budget coverage «7+3=10» заменена проверенной физикой11.',
      '- OMS basing: 117100 ×7×12 =9,8364 млн/год исключительно как неоплаченная часть сверх ground. Месячная и часовая/суточная стоянка — альтернативы для одного tail-time; второй корзины нет. MOW тариф UNKNOWN: выбран0/1×/2× OMS-аналог на3 standalone или4 combined борта; в HYBRID10 —3. Это не тариф Москвы.',
      '- SLA: уникальные nonbase станции ×12 месяцев: OMS8, DIRECT2 — 4, HYBRID10; MOW уже база. Ставки10/25/60 тыс./station-month. Callout300/700/1500 руб. только на0/5/20% nonbase departures. DCS10/30/80 только на0/50/100% всех departures. MOW100/300/600 только на0/100/100% новых MOW departures; фактический scope UNKNOWN.',
      '- Допбагаж4450/service —0/1/5% OMS departures как дополнительные заказы, не пассажир/кг/мешок/каждый transfer. Repdesk1229,51/workplace-service —0/0/100% OMS departures только при дополнительном заказе, не check-in.',
      '- IRROPS: transfer affected0,2/1/3%, local/direct0,1/0,5/1,5% — непересекающиеся поездки. Overnight25/50/100%, nights1/1/2, meals1/2/3, rebook25/50/100% из budget. RO4100 за single room-night =person-night; еда500/800/1200, rebook3000/8000/15000 — лишь incremental differential, исходная выручка снова не возвращается.',
      '- Только OMS event-scope: transfers +50% местных OMS affected, группы40 человек; bus0/2/2 started hours и distribution0/1/1 service на ожидаемую группу, ×3430/3275. Direct-only OMS-тарифами не тарифицируется. Дробные ожидания не инвойсы; invoice_event_example.json показывает отдельное округление43 человек:2 группы,4 started hours,2 distributions; комнаты single43 при одной ночи.',
      '- Crew stress4 человека:0/1/5% закрытых circuits (OMS departures/2 +direct departures/3): каждому1 room-night,1 person-day,2 positioning person-segments; группе2 road trips. Только дополнительные услуги сверх сохранённого BHcrew15/22 тыс.; фактического roster нет. Setup отдельно0/1/2 таких deployments на рабочий борт единожды.',
      '- Полные ground/pax/MRO/crew не добавлены повторно. Налоговые scope сохранены: OMS primary exVAT, hotel как опубликовано, остальное planning. Никакого автоматического20/22%; дополнительный невозмещаемый налог уменьшает остаток рубль в рубль.', '',
      'Launch cash и P&L (млн руб., центральная смета, base рынок):', '']
    for cid in ['OMS','DIRECT2','HYBRID','HYBRID10']:
        l=next(l for l in launches if l['case_id']==cid and l['market']=='base' and l['budget']=='base')
        lines.append(f"- {cid}: oneoff expense **{m(l['oneoff_expense_rub'])}**, CAPEX **{m(l['CAPEX_rub'])}**, refundable deposits **{m(l['refundable_deposits_rub'])}**, working capital **{m(l['working_capital_rub'])}**; всего выбранный launch cash **{m(l['launch_cash_rub'])}**. Steady остаток с CAPEX/3year stress **{m(l['steady_state_after_CAPEX_3y_stress_rub'])}**.")
    lines+=['', '- Launch IT:50/100/200 часов на уникальный nonOMS market × фактическая конверсия budget FTE-month×12/productivefund:583,333/801,429/1184,615 руб./час. Треугольники — по 3 market, DIRECT2 — 5, HYBRID — 11; OMS-собственный setup уже в BoQ, общие MOW/GSV/VOG один раз. Recurring IT часы не setup. MOW условно один физический аэропорт.',
      '- Один pool security2/5/12 млн на совместный network, плюс OMS office deposit по BoQ; owned initial stock не выбран (exchange-pool design). Working capital0/15/30 дней только выбранных уже начисленных service cash, не повторный расход. Launch не вычитается ежегодно; CAPEX/3 — отдельный выбранный accounting stress, не закон. Type rating, fleet acquisition и фактический cash ramp UNKNOWN.', '',
      f"Ограниченный вариант10: OMS7 +MOW2working+1reserve. Перебрано625 комбинаций3..7 для двух цепочек ×двух сезонов, допустимо{bounded['feasible']}; joint direct пересчитан нелинейно из source model, common OD пуст. Лучший central base: GSV_MRV summer/winter **{bounded['frequencies_each_orientation']['GSV_MRV']['summer']}/{bounded['frequencies_each_orientation']['GSV_MRV']['winter']}**, AER_VOG **{bounded['frequencies_each_orientation']['AER_VOG']['summer']}/{bounded['frequencies_each_orientation']['AER_VOG']['winter']}** в неделю **в каждой ориентации**. DIRECT2 BH summer/winter **{bounded['DIRECT2_weekly_BH']['summer']:.3f}/{bounded['DIRECT2_weekly_BH']['winter']:.3f} ≤140**. Остаток HYBRID10 **{m(ten['residual_after_recurring_rub'])} млн**, разница к11 **{m(ten['residual_after_recurring_rub']-h['residual_after_recurring_rub'])} млн**. Direct до добавок вырос с143,323 до177,829 млн: новый расчёт capture/spill снижает затраты быстрее выручки, а не масштабирует прежнюю прибыль. Это лучший только в заданном диапазоне и по этому критерию, не глобальный оптимум и не подтверждение расписания. Полные7/7 обеих цепочек требуют174,811 BH/нед и не помещаются в два рабочих борта.", '',
      'Fuelcredit32930→3024 руб./т на ТОМ ЖЕ base physical schedule: вычитается только fuel_t×29906 из base остатка, cautious сюда не подставляется:', '']
    for cid in ['OMS','DIRECT2','HYBRID','HYBRID10']:
        r=get(cid)
        lines.append(f"- {cid}: burn {r['fuel_t_same_base_schedule']:.3f} т; ухудшение **{m(r['fuel_credit_reduction_rub'])} млн**; остаток **{m(r['residual_fuel_credit_3024_rub'])} млн**.")
    lines+=['', 'Финансирование — отдельные выбранные пороги0/2/4/6 млн руб./tail-month, не quotes. Для центрального HYBRID: '+', '.join(f"{x//1000000} → {m(h['residual_after_recurring_rub']-x*11*12)}" for x in P['finance_RUB_tail_month_sensitivity'])+' млн остатка. Break-even финансирование **'+m(h['residual_after_recurring_rub']/(11*12))+' млн/tail-month**, страховая премия при прочих base-допущениях **'+m(h['residual_before_insurance_rub']/11)+' млн/tail-year**. В thresholds.csv есть также индивидуальный порог MOW parking и запас на прочие ежегодные непокрытые расходы/невозмещаемый налог.', '',
      'Файлы: results.csv —36 годовых комбинаций (30 основных +6 bounded); seasonal_results.csv — лето/зима; quantities.csv — компактные годовые unit quantities; seasonal_quantities.csv — периодные единицы; launch.csv, station.csv, included.csv, sensitivities.csv, thresholds.csv; policy.json — все выбранные правила; bounded10.json; input_manifest.json — явные зависимости, без .venv и whole-P40 hash.', '',
      'Точный локальный повтор из корня worktree:', '', '```bash',
      'cd /home/mputi/.t3/scratch/red-wings-team-update-20261109-b45f8804',
      'context/40_hybrid_costs_20261113/network/.venv/bin/python3 -B context/40_hybrid_costs_20261113/calculation/build.py',
      'context/40_hybrid_costs_20261113/network/.venv/bin/python3 -B context/40_hybrid_costs_20261113/calculation/verify.py',
      '```', '', 'Проверки и их фактический итог — validation.json: денежные тождества, API convergence, отсутствие двойных станций/пассажиров, единицы, сохранённые входные хеши и byte-identical повтор в новом процессе Python3. Source/network/budget/P39/панель/презентация не изменяются. UNKNOWN actual profit/contracts сохраняется.']
    (HERE/'RESULTS.md').write_text('\n'.join(lines)+'\n')

def build():
    initial = manifest()
    selected, bounded = bounded10()
    result=[]; seasonal=[]; quantities=[]; sq=[]; launches=[]; included=[]; sensitivities=[]; thresholds=[]
    for cid in MAIN+['DIRECT2_10','HYBRID10']:
        for market in (['base','cautious'] if cid in MAIN else ['base']):
            views = {s:API.expenses_for(cid,market,s) if cid in MAIN else selected[(cid,s)]
                     for s in ['annual','summer','winter']}
            if cid in MAIN:
                v=views['annual']
                included.append(dict(case_id=cid,market=market,included_costs_rub=v['included_costs_rub'],
                                     **{k:r['cost_signed_rub'] for k,r in v['components'].items() if r['cost_signed_rub']}))
            for budget in P['budget_scenarios']:
                r,q,_,_=expense(views['annual'],cid,budget)
                l=launch(views['annual'],cid,budget,r)
                if market=='base':
                    fuel=views['annual']['drivers']['fuel_t'];debit=fuel*P['fuel_credit_stress']['difference_RUB_t']
                    r.update(fuel_t_same_base_schedule=fuel,fuel_credit_reduction_rub=debit,
                             residual_fuel_credit_3024_rub=r['residual_after_recurring_rub']-debit)
                result.append(r);quantities.append(q);launches.append(l)
                for s in ['summer','winter']:
                    sr,qq,_,_=expense(views[s],cid,budget);seasonal.append(sr);sq.append(qq)
                tailmonths=P['retained_fleet'][cid]*12
                rafter=r['residual_after_recurring_rub']
                thresholds.append(dict(case_id=cid,market=market,budget=budget,
                    finance_break_even_RUB_tail_month=rafter/tailmonths,
                    insurance_break_even_RUB_tail_year=r['residual_before_insurance_rub']/P['retained_fleet'][cid],
                    MOW_parking_break_even_RUB_tail_month=(rafter+r['mow_parking_analogue_rub'])/(P['based_MOW_tails'][cid]*12) if P['based_MOW_tails'][cid] else '',
                    other_annual_uncovered_or_unrecoverable_tax_headroom_rub=rafter,
                    meaning='negative means already exhausted; one-at-a-time replacement, not additive headrooms'))
                if budget=='base':
                    for f in P['finance_RUB_tail_month_sensitivity']:
                        sensitivities.append(dict(case_id=cid,market=market,kind='finance_chosen_not_quote',rate=f,unit='RUB/tail-month',quantity=tailmonths,residual_rub=rafter-f*tailmonths))
                    for ins in ASS['insurance_sweep_RUB_aircraft_year']:
                        sensitivities.append(dict(case_id=cid,market=market,kind='insurance_chosen_not_quote',rate=ins,unit='RUB/tail-year',quantity=P['retained_fleet'][cid],residual_rub=r['residual_before_insurance_rub']-ins*P['retained_fleet'][cid]))
    table('results.csv',result);table('seasonal_results.csv',seasonal)
    table('quantities.csv',quantities);table('seasonal_quantities.csv',sq)
    table('launch.csv',launches);table('station.csv',STATIONS);table('included.csv',included)
    table('sensitivities.csv',sensitivities);table('thresholds.csv',thresholds)
    dump('bounded10.json',bounded)
    dump('invoice_event_example.json',dict(status='AUTHOR_GROUP_INVOICE_EXAMPLE_NOT_ANNUAL_FORECAST',
         affected_people=43,single_room_nights_for_one_night=43,hotel_rub=43*4100,
         selected_event_groups=math.ceil(43/40),bus_started_hours=math.ceil(43/40)*2,
         bus_rub=math.ceil(43/40)*2*3430,distribution_services=math.ceil(43/40),
         distribution_rub=math.ceil(43/40)*3275,group_size_is_chosen_not_bus_capacity_fact=True))
    report(result,launches,bounded)
    assert initial==manifest(), 'Input changed during build'
    dump('input_manifest.json',initial)
    return result

if __name__=='__main__':
    rr=build()
    h=next(r for r in rr if r['case_id']=='HYBRID' and r['market']=='base' and r['budget']=='base')
    print(json.dumps(dict(status='BUILT',annual_rows=len(rr),HYBRID_central_residual_rub=h['residual_after_recurring_rub']),ensure_ascii=False))
