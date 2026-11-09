"""Accepted offline stage-1 snapshot rules, version 2026-11-10 round 2.

Raw UNKNOWN stays null. Utility and scenario bounds are separate from evidence.
This is a comparative screen, never a model of sales or profit.
"""
import copy
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / 'context/22_stage1_audit'
SUPPORT = ['KUF', 'KZN', 'AER', 'MCX']
DOC_KEYS = ['competitor_hub', 'ssj_mro', 'transfer_zone']
RW_URL = 'https://flyredwings.com/press/news/red-wings-pereshla-na-osenne-zimnee-raspisanie-poletov/'
OMS_URL = 'https://www.aeroomsk.ru/ob-aeroporte/press-tsentr/novosti/207/'
REN_URL = 'https://ar-ren.ru/about/news/aeroport-orenburg-obsluzhil-za-2025-god-bolee-950/'


def utility(v, c):
    if v is None or c.get('constant') or c['hi'] <= c['lo']:
        return .5
    z = max(0., min(1., (v-c['lo'])/(c['hi']-c['lo'])))
    return 1-z if c['dir'] == '-' else z


def profiles():
    p = json.loads((A/'weight_profiles.json').read_text())
    return [p['recommended']] + p['alternatives']


def build(ll):
    policy = json.loads((A/'rules.json').read_text())
    assert policy['eligibility']['primary_min_distance_km'] == 500
    assert policy['eligibility']['comparison'] == '>='
    assert policy['normalization']['kind'] == 'fixed_snapshot_minmax'
    assert policy['normalization']['missing_utility'] == .5
    assert policy['normalization']['do_not_refit_after_filter'] is True
    assert policy['samara_modes']['primary'] == 'expansion_allowed'
    assert policy['weight_sum'] == 100
    baseline = json.loads((A/'baseline/data/processed/criteria.json').read_text())
    with (A/'recommended_weights.csv').open(newline='') as f:
        weights = list(csv.DictReader(f))
    criteria = []
    for r in weights:
        criteria.append(dict(key=r['column'], label=r['criterion'], short=r['short'], dir=r['direction'],
            weight=float(r['weight']), fill=float(r['fill']) if r['fill'] else None,
            lo=float(r['lo']), hi=float(r['hi']), group=r['group'], why=r['why'], fmt=r['fmt'],
            board=int(r['board']), status='proposal_not_team_approved', origin='основной', fixed=True))
    for c in criteria:
        reference = [baseline['values'][i][c['key']].get('v') for i in ll.index]
        c['constant'] = all(v is not None for v in reference) and len(set(reference)) == 1
    import pandas as pd
    intro = pd.read_csv(ROOT/'data/processed/kover_days.csv').set_index('iata').last365_days_intro
    vals = copy.deepcopy(baseline['values'])
    for i in ll.index:
        r = ll.loc[i]
        for c in criteria:
            k = c['key']; x = vals[i][k]
            v = x.get('v'); status = 'UNKNOWN' if v is None else 'FACT_primary_in_scope'
            note = 'Сохранённый источник первого прохода; повторно не проверялся.'
            x.update(source_date='', accessed_date='2026-11-10', scope='stage1_snapshot', status=status,
                     reference_period='', uncertainty_reason='', raw_low=v, raw_high=v)
            if k == 'competitor_hub' and v in [.25, .75]:
                status = 'INDIRECT' if v == .75 else 'UNKNOWN'; v = None
                note = 'Слабое вторичное свидетельство; отсутствие записи не доказывает отсутствие базы.'
            if k == 'ssj_mro' and v == .5:
                status = 'INDIRECT'; v = None; note = 'Наличие эксплуатанта не доказывает станцию ТО.'
            if k == 'rw_support':
                v = 1 if i in SUPPORT else None
                status = 'FACT_primary_in_scope' if i in SUPPORT else 'UNKNOWN'
                if i in SUPPORT:
                    x.update(s=RW_URL, source_date='2026-10-27', reference_period='2026-10-27..2027-03-27')
                note = 'Опорный статус не доказывает физическую базу/хаб. UNKNOWN сохраняется условно.'
            if k == 'rostec_link' and v == 0:
                v = None; status = 'UNKNOWN'; note = 'Не найдено не означает отсутствие.'
            if k == 'transfer_zone' and i in ['OMS', 'IKT', 'KZN']:
                v = None; status = 'INDIRECT' if i == 'KZN' else 'UNKNOWN'
                note = 'Историческое/вторичное или международное свидетельство не подтверждает внутренний трансфер.'
            if k == 'ssj_mro' and i == 'OMS':
                v = 1; status = 'FACT_primary_in_scope'
                x.update(s=OMS_URL, source_date='2024-12-03', reference_period='2024-12-03')
                note = 'Опубликованное действующее ТО SSJ; текущие договор, свободная мощность и область допуска UNKNOWN.'
            if k == 'bad_weather_days':
                v = None; status = 'UNKNOWN'
                note = 'Локальных gz нет; старый знаменатель включал невалидные поля. Значение не подтверждено.'
            x.update(v=v, status=status, note=note, raw_low=v, raw_high=v)
            u = utility(v,c); lo = hi = u
            if v is None:
                lo, hi = 0., 1.; x['raw_low'] = x['raw_high'] = None
                x['uncertainty_reason'] = 'missing_or_weak_evidence'
            if k == 'gap_pop':
                a, b = max(0., v-float(r.gap_pop_rail_unknown)), v
                x.update(raw_low=a, raw_high=b, reference_period='stored_snapshot')
                lo, hi = utility(a,c), utility(b,c); u = (lo+hi)/2
                if a != b: x['uncertainty_reason'] = 'unknown_rail_time'
                x['note'] = 'Условный географический proxy; центральный вклад неизвестного поезда 50%, не наблюдённый спрос.'
            if k == 'transfer_demand_base':
                lo, hi = 0., 1.; x.update(raw_low=0, raw_high=c['hi'], status='INDIRECT',
                    uncertainty_reason='full_model_sensitivity_no_pair_scenario_outputs',
                    note='Модельно взвешенный proxy пар. Только base сохранён; полный диапазон шкалы, не OD/продажи/доверительный интервал.')
            if k == 'catchment_pop_2025':
                x.update(coverage={'coord_imputed_share':float(r.pop_coord_imputed_share),
                                   'region_factor_share':float(r.pop25_region_factor_share)}, reference_period='2025-01-01')
                if r.pop_coord_imputed_share > 0 or r.pop25_region_factor_share > 0:
                    lo, hi = 0., 1.; x.update(uncertainty_reason='population_imputation', status='INDIRECT', raw_low=None, raw_high=None)
            if k == 'wage_2024':
                x.update(coverage={'wage_pop_coverage':float(r.wage_pop_coverage)}, reference_period='2024')
                if r.wage_pop_coverage < 1:
                    lo, hi = 0., 1.; x.update(uncertainty_reason='partial_wage_coverage', status='INDIRECT', raw_low=None, raw_high=None)
            if k == 'pax_2025':
                q = str(r.pax_2025_qualifier); x['reference_period'] = '2025'
                if q.startswith('>'):
                    x.update(v=None, t='>'+str(int(v)), raw_low=v, raw_high=c['hi'], status='INDIRECT',
                             uncertainty_reason='qualified_lower_bound', note='Нижняя граница; верх шкалы — крайний сценарий, не прогноз.')
                    lo, hi = utility(v,c), 1.; u = (lo+hi)/2
                elif q == '≈':
                    lo, hi = 0., 1.; x.update(t='≈', status='INDIRECT', uncertainty_reason='approximate_precision_unspecified', raw_low=None, raw_high=None)
                if i == 'CEK':
                    a,b = 2160421,2166689
                    lo,hi=utility(a,c),utility(b,c)
                    x.update(raw_low=a, raw_high=b, status='INDIRECT', uncertainty_reason='published_total_scope_discrepancy')
                if i == 'REN':
                    lo,hi = utility(951000,c),utility(951200,c); u=utility(951100,c)
                    x.update(v=None, t='>951000', raw_low=951000, raw_high=951200, status='INDIRECT', s=REN_URL,
                        source_date='2026-01-15', raw_fact='>951000', approximate_derived=951100,
                        uncertainty_reason='rounded_components_assumption',
                        note='Первичный факт >951000; 885500+65600≈951100. Диапазон 951000–951200 только при округлении каждой компоненты до сотни; точный итог UNKNOWN.')
            if k == 'last365_days':
                x.update(reference_period='stored_last365_window', note='Дни публикаций введения ИЛИ снятия по МСК; не длительность и не потерянные стыковки.')
            x.update(u=u, u_low=lo, u_high=hi, unknown=x['status']=='UNKNOWN', indirect=x['status']=='INDIRECT',
                     clipped=v is not None and not (c['lo'] <= v <= c['hi']))
    return dict(criteria=criteria, values=vals, stage1=dict(version='2026-11-10-round2',
        approval='proposed_not_team_approved', primary_min_km=500, primary_mode='expansion_allowed',
        strict_excluded=SUPPORT, intro_only={i:int(intro.loc[i]) for i in ll.index}, profiles=[dict(id=p['id'],label=p['label'],weights={c['column']:c['weight'] for c in p['criteria']}) for p in profiles()],
        interval_scope='Conservative bounds for encoded evidence/model/coverage scenarios; not full real-world uncertainty or probabilities.',
        other_steps='Steps 2–4 and embedded maps retained; NOT verified by this audit.'))
