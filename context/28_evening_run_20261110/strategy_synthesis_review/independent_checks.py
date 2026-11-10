#!/usr/bin/env python3
"""EV-MR04: exact Git blobs, stdlib only; never executes owner calculators.

Run from the repository, with OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
MKL_NUM_THREADS=1 python3 context/28_evening_run_20261110/
strategy_synthesis_review/independent_checks.py
"""
import calendar
import csv
import datetime as dt
import hashlib
import io
import json
import math
import subprocess
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

SHA = '9f0b5d25af720107e99e209e1c69b098497358be'
PREFIX = 'context/28_evening_run_20261110/methods/'
OUT = Path(__file__).resolve().parent
manifest = {}
checks = []
evidence = {}

@lru_cache(None)
def blob(path, sha=SHA):
    data = subprocess.check_output(['git', 'show', sha + ':' + path])
    oid = subprocess.check_output(['git', 'rev-parse', sha + ':' + path]).decode().strip()
    manifest[(sha, path)] = dict(commit=sha, path=path, git_blob=oid,
        sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
    return data

def text(path):
    return blob(PREFIX + path).decode()

def rows(path):
    return list(csv.DictReader(io.StringIO(text(path))))

def js(path):
    return json.loads(text(path))

def check(name, ok, detail=None):
    checks.append(dict(name=name, passed=bool(ok), detail=detail))

def near(a, b, tol=1e-6):
    return abs(float(a) - float(b)) <= tol

def pair(r):
    return tuple(sorted((r['origin'], r['destination'])))

def single(rr, **filters):
    match = [r for r in rr if all(r.get(k) == str(v) for k, v in filters.items())]
    assert len(match) == 1, (filters, len(match))
    return match[0]

# Record the entry points actually read; source reviews are scopes, not v4 acceptance.
for p in ('strategy.md', 'strategy_tables.py', 'verify_strategy.py',
          'requests.json', 'qualification_events_v4.json'):
    text(p)
alignment_sha = 'd125f87d2caeb3b08cfa3c6471d9aeb000f6c605'
for p in ('AGENTS.md', 'context/26_strategy_reset_20261110/contract.md',
          'context/28_evening_run_20261110/contract.md'):
    blob(p, alignment_sha)
evidence['alignment_commit'] = alignment_sha

# A. Reprice all 12 source program rows, then pool unordered markets before sales.
rr = rows('inputs/network_b471/v2/outputs/fixed_routes.csv')
dd = rows('inputs/network_b471/v2/outputs/demand_fare_inputs.csv')
params = rows('inputs/nastya_4a976/data/assumptions/network.csv')
net = js('runs/selection_v1/networks.json')
mixed_out = rows('strategy/mixed11_budget.csv')
mixed_route_out = rows('strategy/mixed11_routes.csv')
mixed_evidence = []
for s in ('base', 'cautious'):
    a = {r['parameter']: float(r[s]) for r in params}
    selected = [r for r in rr if r['scenario'] == s and r['network'] in ('KUF4', 'OMS8')]
    demand = {}
    for r in dd:
        if r['scenario'] == s and r['frequency_each_direction'] == '2':
            key = pair(r)
            if key in demand:
                check('same oriented demand ' + s + '/' + '-'.join(key),
                    all(demand[key][k] == r[k] for k in ('diagnostic_week_od_one_direction',
                        'direct_in_author_input', 'net_fare_rub', 'annual_segments_competition_proxy')))
            demand[key] = r

    def sales(d, f, demand_override=None):
        od = float(d['diagnostic_week_od_one_direction']) if demand_override is None else demand_override
        if d['direct_in_author_input'] == 'True':
            other = float(d['annual_segments_competition_proxy']) / 104 / (a['seats'] * a['competitor_lf'])
            share = min(a['capture_competitive'], f / (f + other))
        else:
            share = a['capture_open'] * (-math.expm1(-f / a['capture_freq_scale']))
        return 2 * min(od * share, f * a['seats'] * a['lf_max'])

    costs = 0.0
    naive = 0.0
    pooled = defaultdict(float)
    for r in selected:
        key = pair(r); d = demand[key]; f = float(r['frequency_each_direction'])
        q = sales(d, f); fare = a['fare_fixed_rub'] + a['fare_per_km_rub'] * float(d['km'])
        hours = float(r['block_hours_week']); flights = int(r['flights_week'])
        fixed = hours * (a['fuel_t_per_hour'] * a['fuel_rub_per_t'] + a['mro_rub_per_hour'] +
            a['crew_rub_per_hour'] + a['navigation_rub_per_hour']) + flights * (
            a['fuel_t_per_cycle'] * a['fuel_rub_per_t'] + a['ground_rub_per_flight'] + a['deicing_rub_per_flight'])
        c = q * (fare - a['pax_cost_rub']) - fixed
        check('reprice source ' + s + '/' + r['network'] + '/' + '-'.join(key),
              near(q, r['local_journeys_week']) and near(c, r['local_only_contribution_rub_week']) and near(fare, d['net_fare_rub']))
        costs += fixed; naive += c; pooled[key] += f
    total = sum(sales(demand[p], f) * (float(demand[p]['net_fare_rub']) - a['pax_cost_rub'])
                for p, f in pooled.items()) - costs
    summary = single(mixed_out, scenario=s)
    qdelta = sum(sales(demand[p], f) for p, f in pooled.items()) - sum(float(r['local_journeys_week']) for r in selected)
    check('mixed independent total ' + s, near(total, summary['shared_market_corrected_contribution']) and
        near(naive, summary['naive_sum_contribution']) and near(qdelta, summary['shared_market_sales_correction']))
    check('mixed unchanged flights and hours ' + s, len(selected) == 12 and len(pooled) == 11 and
        sum(int(r['flights_week']) for r in selected) == 48 and
        near(sum(float(r['block_hours_week']) for r in selected), 125.43576441759129))
    for p, f in pooled.items():
        r = next(x for x in mixed_route_out if x['scenario'] == s and pair(x) == p)
        check('pooled route ' + s + '/' + '-'.join(p), near(r['pooled_local_journeys'], sales(demand[p], f)) and
              near(r['joint_frequency_each_direction'], f))
    d = demand[('KUF', 'OMS')]; q2 = sales(d, 2); q4 = sales(d, 4)
    raw2 = float(d['diagnostic_week_od_one_direction']) * a['capture_open'] * (-math.expm1(-2/a['capture_freq_scale']))
    raw4 = float(d['diagnostic_week_od_one_direction']) * a['capture_open'] * (-math.expm1(-4/a['capture_freq_scale']))
    check('closed form preconditions ' + s, d['direct_in_author_input'] == 'False' and
          raw2 < 2*a['seats']*a['lf_max'] and raw4 < 4*a['seats']*a['lf_max'])
    check('closed form identity ' + s, near(q4, q2*(1+math.exp(-2/a['capture_freq_scale']))))
    capped2, capped4 = sales(d, 2, 10000), sales(d, 4, 10000)
    bad_formula = capped2*(1+math.exp(-2/a['capture_freq_scale']))
    check('closed form is not universal ' + s, not near(capped4, bad_formula))
    mixed_evidence.append(dict(scenario=s, weekly_oneway_OD=float(d['diagnostic_week_od_one_direction']),
        open=True, q2_both_directions=q2, q4_both_directions=q4, naive_overlap=2*q2,
        raw_oneway_q2=raw2, raw_oneway_q4=raw4, planning_seats_oneway_f2=2*a['seats']*a['lf_max'],
        planning_seats_oneway_f4=4*a['seats']*a['lf_max'], fare=float(d['net_fare_rub']), pax_cost=a['pax_cost_rub'],
        naive_total=naive, corrected_total=total, correction=total-naive, journey_correction=qdelta,
        capped_counterexample=dict(oneway_OD=10000, actual_q2=capped2, actual_q4=capped4, wrong_closed_form_q4=bad_formula)))
evidence['mixed11'] = mixed_evidence

# B. Compare route records at program-leg grain, then aggregate physical unordered pairs.
options = rows('strategy/finite_options.csv'); routes = rows('strategy/option_routes.csv')
frontier = rows('runs/selection_v1/preserved_frontiers.csv')
plans = js('runs/resource_v1/plans.json')
check('finite cardinalities', len(options) == 24 and len({r['option'] for r in options}) == 24 and len(routes) == 205)
check('six families by four scenarios', Counter(r['scenario'] for r in options) == Counter(base=6, base_sub=6, cautious=6, cautious_sub=6))
pair_examples = []
for opt in options:
    key = opt['option']; n = net[key]; m = n['metrics']
    source = list(n['result'][0].values()) if m['kind'] == 'HUB' else [leg for t in n['result'] for leg in t[8]]
    actual = [r for r in routes if r['option'] == key]
    expected = Counter((l['a'], l['b'], float(l['freq'])) for l in source)
    got = Counter((l['origin'], l['destination'], float(l['frequency_each_direction_week'])) for l in actual)
    unique = {tuple(sorted((l['a'], l['b']))) for l in source}
    check('option route source ' + key, expected == got and len(unique) == int(opt['model_endpoint_pairs']) and 8 <= len(unique) <= 12)
    check('option value source ' + key, all(near(opt[a], m[b]) for a,b in (
        ('annual_contribution_source','contribution_rub_year'), ('annual_journeys_source','journeys_year'),
        ('annual_segments_source','segments_year'), ('block_hours_week','block_hours_week'), ('flights_week','flights_week')))
        and int(opt['constructed_working_tails']) == plans[key]['working_tails'] and
        opt['source_calendar'] == m['calendar'] and
        opt['support_status'] == ('HISTORICAL_OWNER_SHADOW' if m['scenario'].endswith('_sub') else 'NONE'))
    choices = [r for r in frontier if r['cap'] == '10' and r['calendar'].startswith('AUTHOR') and
        r['network'] == m['network'] and r['scenario'] == m['scenario'] and
        (m['network'] != 'DIRECT' or r['policy'] == 'SIGNED_CITY_PAIRS_PRESERVE')]
    check('found set selected source ' + key, len(choices) == 1 and choices[0]['selected_id'] == key)
    check('route temporal and airport boundary ' + key, all(r['date'] == '' and
        r['calendar_basis'] == 'AUTHOR_FIXED_WEEKLY_52_OR48; NOT_DATED_FLIGHT' and
        r['physical_airport_resolved'] == str('MOW' not in pair(r)) for r in actual))
    if len(actual) > len(unique):
        ct = Counter(pair(r) for r in actual)
        duplicate = next(p for p,v in ct.items() if v > 1)
        pair_examples.append(dict(option=key, program_rows=len(actual), unique_pairs=len(unique),
            duplicate_pair=duplicate, frequencies=[r['frequency_each_direction_week'] for r in actual if pair(r) == duplicate]))
evidence['pair_grain_counterexamples'] = pair_examples

# Independent N(t): only resource gate, no annual revenue, LP, MCT or synchronization replay.
contract = js('calendar_contract.json')
batches = contract['delivery_branches']['PHASED']
def shift(date, months):
    y, mo = divmod(date.year*12+date.month-1+months,12)
    return dt.date(y,mo+1,min(date.day,calendar.monthrange(y,mo+1)[1]))

def working(branch, date):
    if branch == 'NO_NEW': return (0,0,0,0)
    delay = int(branch[5:]) if branch.startswith('DELAY') else 0
    entered = grounded = 0
    for when, count in (batches[:2] if branch == 'PARTIAL_FIRST4' else batches):
        ready = shift(dt.date.fromisoformat(when), delay) + dt.timedelta(days=contract['entry_days'])
        if date < ready: continue
        entered += count
        age = (date-shift(ready,12)).days
        grounded += sum(14*k <= age < 14*(k+1) for k in range(count))
    reserve = min(1, entered-grounded)
    return entered-grounded-reserve, entered, grounded, reserve

readyrows = rows('strategy/finite_option_readiness.csv')
check('readiness cardinality', len(readyrows) == 144 and len({(r['option'],r['branch'],r['year']) for r in readyrows}) == 144)
for r in readyrows:
    opt = single(options, option=r['option']); year = int(r['year']); need = int(opt['constructed_working_tails'])
    days = [dt.date(year,1,1)+dt.timedelta(days=i) for i in range(366 if calendar.isleap(year) else 365)]
    days = [str(d) for d in days if working(r['branch'],d)[0] >= need]
    check('readiness independently reconstructed ' + '/'.join((r['option'],r['branch'],r['year'])),
        int(r['required_working_tails']) == need and len(days) == int(r['days_with_aggregate_resource']) and
        (days[0] if days else '') == r['first_date_with_resource'] and (days[-1] if days else '') == r['last_date_with_resource'])
boundary = []
for day in ('2028-04-30','2028-05-01','2028-07-30','2028-09-10','2028-09-11'):
    vals = working('PHASED',dt.date.fromisoformat(day))
    boundary.append(dict(date=day,working=vals[0],entered=vals[1],grounded=vals[2],reserve=vals[3]))
evidence['resource_boundaries'] = boundary

# C. Match exact selectors, units and conditions of ten cards, not arbitrary equal values.
cards = rows('strategy/hypothesis_decisions.csv')
spec = {
 'C01':('delta_contribution_rub_week',dict(local_loss_fraction_south='0')),
 'C03':('Kmax_extra_KUF_base_minus_deployment_lodging_rub_week',{}),
 'C04':('contribution_rub_week',dict(network='OMS8')),
 'C07':('delta_contribution_rub_week',dict(turn_minutes='45')),
 'C33':('delta_contribution_rub_week',dict(occupied_state='planning_lf_sold_allow100',local_loss_fraction_trunk='0.15')),
 'C10':('minimum_guarantee_return_per_person',dict(phase='launch_closed',cohorts='1',K_probe='0')),
 'C14':('minimum_package_price_per_person',dict(K_probe='0')),
 'C17':('minimum_summer_paid_people_each_leg',dict(year='2027',summer_people_each_leg_probe='40',K_probe='0')),
 'C31':('maximum_tu_new_allin_cost_plus_K',dict(demand_layer='nastya_primary',additional_mrv_paid_each_leg_probe='0',foregone_tu_old_mission_contribution_probe='0',tu_new_allin_cost_probe='2000000')),
 'C35':('maximum_integration_retime_risk_K',dict(fare_case='original_no_support_fare',K_probe='0.0'))}
check('ten required IDs',set(spec) == {r['id'] for r in cards} and len(cards) == 10)
source_cells = []
for c in cards:
    col, selectors = spec[c['id']]; source = rows(c['input_path'])
    for scenario, field in [('base','base_value'),('cautious','cautious_value')]:
        selected = [r for r in source if r['scenario'] == scenario and all(r.get(k) == v for k,v in selectors.items())]
        check('card selected cell ' + c['id'] + '/' + scenario, len(selected) == 1 and near(selected[0][col],c[field]))
        if selected:
            r = selected[0]
            source_cells.append(dict(id=c['id'],scenario=scenario,path=PREFIX+c['input_path'],
                line=source.index(r)+2,column=col,value=r[col],selectors=selectors,unit=c['unit'],period=c['period']))
    check('card conditional acceptance '+c['id'], c['team_accepted'] == 'False' and c['actual_full_result'] == '')
    receipt_dir = 'inputs/network_b471' if c['id'] in ('C01','C03','C04','C07','C33') else 'inputs/products_3889'
    receipt = js(receipt_dir+'/receipt.json'); relative = c['input_path'][len(receipt_dir)+1:]
    rec = next(r for r in receipt['files'] if r['path'] == relative)
    check('card source Git bytes '+c['id'], blob(PREFIX+c['input_path']) == blob(rec['source_path'], c['input_sha']) and
          hashlib.sha256(blob(PREFIX+c['input_path'])).hexdigest() == rec['sha256'])
evidence['selected_source_cells'] = source_cells

# Inspect the other semantic dimensions required by the brief, without re-solving LPs.
semantic = {}
c10 = rows('inputs/products_3889/outputs/C10_contract_thresholds.csv')
c14 = rows('inputs/products_3889/outputs/C14_full_package_thresholds.csv')
c17 = rows('inputs/products_3889/outputs/C17_seasonal_thresholds.csv')
c35 = rows('inputs/products_3889/outputs/addendum_C35_internal_KEEP.csv')
c35ext = rows('inputs/products_3889/outputs/C35_partner_thresholds.csv')
for s in ('base','cautious'):
    launch = single(c10,scenario=s,phase='launch_closed',cohorts='1',K_probe='0')
    steady = single(c10,scenario=s,phase='steady28',cohorts='1',K_probe='0')
    check('C10 launch and steady basis '+s,near(launch['roundtrips'],2) and near(steady['roundtrips'],1) and
        float(launch['minimum_guarantee_return_per_person']) > float(steady['minimum_guarantee_return_per_person']) and
        near(float(launch['minimum_guarantee_return_per_person'])*float(launch['people_in_new_cohorts']),
             float(launch['airline_variable_cost'])-float(launch['retail_revenue'])))
    package = single(c14,scenario=s,K_probe='0')
    air = (float(package['airline_variable_cost'])-float(package['retail_revenue']))/float(package['distinct_return_customers'])
    other = sum(float(package[k]) for k in ('hotel_cost','ground_cost','product_service','expected_protection_probe'))/float(package['distinct_return_customers'])
    check('C14 airline vs full package '+s,near(air,package['minimum_air_guarantee_return_per_person']) and
        near(air+other,package['minimum_package_price_per_person']) and package['revenue_legs']=='16' and
        package['positioning_legs']=='16' and package['peak_beds']==('120' if s=='base' else '80'))
    own = single(c35,scenario=s,fare_case='original_no_support_fare',K_probe='0.0')
    ext = single(c35ext,scenario=s,K_probe='0')
    revenue = float(own['through_oneway_journeys'])*float(own['customer_oneway_fare'])
    correct = revenue-float(own['incremental_two_leg_pax_handling_protection_cost'])-float(own['lost_previous_own_contribution_probe'])
    check('C35 one fare two seats '+s,near(own['rw_used_seat_segments'],2*float(own['through_oneway_journeys'])) and
        near(revenue,own['customer_total_fare_revenue']) and near(correct,own['maximum_integration_retime_risk_K']) and
        own['external_partner_payment']=='0' and own['additional_subsidy_from_new_flights']=='0')
    check('C35 external paid inventory '+s,near(ext['maximum_partner_price_per_reserved_seat'],
        (float(ext['customer_total_fare_revenue'])-float(ext['rw_pax_handling_protection_cost'])-
         float(ext['lost_previous_own_contribution_probe']))/float(ext['protected_seat_segments_each_operator'])))
    semantic[s] = dict(C10_launch=float(launch['minimum_guarantee_return_per_person']),
        C10_steady=float(steady['minimum_guarantee_return_per_person']),C14_airline_floor=air,C14_full_package_floor=air+other,
        C35_own_K=correct,C35_external_block_seat_price=float(ext['maximum_partner_price_per_reserved_seat']))
check('C17 both years 35 winter and 35 summer', {r['year'] for r in c17}=={'2027','2028'} and
      all(r['winter_roundtrips']=='35' and r['summer_roundtrips']=='35' for r in c17))
check('C17 tested whole recipe physically exceeds 100',all(float(r['minimum_summer_paid_people_each_leg'])>100 for r in c17))

resource = rows('inputs/network_b471/v2/outputs/fixed_daily_resources.csv')
slots = {n:len({r['tail_scenario'] for r in resource if r['network']==n}) for n in ('KUF4','OMS8')}
check('three separate base constructed slots',slots=={'KUF4':1,'OMS8':2})
semantic['mixed_slot_basis'] = slots

# Concrete money counterexamples: probes are reviewer examples, not adopted inputs.
c31base = next(r for r in source_cells if r['id']=='C31' and r['scenario']=='base')
cap = float(c31base['value'])
semantic['C31_single_cap_boundary'] = dict(cap=cap,Tu_allin=2000000,old_Tu_lost_net=200000,
    other_K=100000,result=cap-2000000-200000-100000,
    explanation='Each component individually below cap, joint sum exceeds it; no C31/C35 union replay')
ext = single(c35ext,scenario='base',K_probe='0')
semantic['C35_segment_boundary'] = dict(new_RW_segments_external=float(ext['through_oneway_journeys']),
    displaced_old_journeys=float(ext['own_cannibalised_journeys_probe']),
    one_old_RW_segment_net=160-40,two_old_RW_segments_net=160-2*40,
    explanation='Same160 new external-feed RW segments minus40 old journeys need old RW-segment count;120 is not unconditional company growth')
cash = rows('inputs/products_3889/outputs/cash_events.csv')
cashsummary = rows('inputs/products_3889/outputs/cash_summary.csv')
check('cash scope 1318 events14 timing cases',len(cash)==1318 and
      sum(r['kind']=='TIMING_FIXTURE_K0' for r in cashsummary)==14)
cs = single(cashsummary,hypothesis='C35',scenario='base',entity='airline',kind='TIMING_FIXTURE_K0')
check('C35 cash vs economic margin',near(cs['cash_balance_end'],787392) and
      near(cs['minimum_external_funding_if_same_day_netting'],480000) and
      near(float(cs['cash_balance_end'])-200000,ext['variable_incremental_contribution_at_block_probe']))
semantic['cash_ordering_boundary'] = dict(same_day_outflow=480000,same_day_receipt=480000,
    day_net=0,outflow_before_receipt_funding=480000,
    explanation='Reviewer ordering counterexample: zero day-end cash does not show intraday funding sufficiency')
evidence['semantic_boundaries'] = semantic

# Preserve original queue identity and uncertainty, not just its row count.
original_portfolio = list(csv.DictReader(io.StringIO(blob(
    'context/26_strategy_reset_20261110/hypothesis_portfolio.csv',
    '4a9971beeacbc40559943eae05b9004c90165917').decode())))

# Register lineage and budget completeness. Interpretations are discussed in report.md.
budget = rows('strategy/budget_components.csv')
check('21 unique budget components',len(budget) == 21 and {r['id'] for r in budget} == {'B%02d'%i for i in range(1,22)})
queue = rows('strategy/hypothesis_queue35.csv')
check('35 distinct preserved and 25 reserves',len(queue) == 35 and len({r['id'] for r in queue}) == 35 and
      sum(r['evening_status'] == 'RESERVED_NOT_TESTED_THIS_WINDOW' for r in queue) == 25)
evidence['original_portfolio_columns'] = list(original_portfolio[0])
check('35 original queue IDs', {r['id'] for r in queue} == {r['id'] for r in original_portfolio})
original_by_id = {r['id']:r for r in original_portfolio}
preserved_fields = [('title','title'),('family','family'),
    ('historical_status','historical_disposition'),('next_test_preserved','proposed_next_test')]
check('queue original text and uncertainty',all(all(r[d]==original_by_id[r['id']][s] for d,s in preserved_fields) and
    r['not_rejected_for_nonselection']=='True' for r in queue))
acceptance = rows('strategy/acceptance_register.csv')
check('no inherited v4 reviews',all(r['inherited_to_v4'] == 'False' for r in acceptance))
expected_subjects = {
 'EV-MR01':('48686bf2276c435d7a260f4de6741c9b65d26e32','bd2c27d2157d29d04fa1b3201e01392786fb035f'),
 'EV-MR02':('aa7779192d809558e38b1eb9bdfa25913a3afdc8','8cb5fde05c51ae05f7b72e3cb996f0cb4fa26550'),
 'SOURCE_REVIEW':('38f0f7ae8a10b6a60bd2d5ab39b18a9865e2b78b','13f7c373954cc16b33a53b7c46436ee3f15f753b'),
 'NETWORK_FINAL_REVIEW':('b47118a48b6d5480217077bf8699a63665c0eb7a','cccc728b401d3a1234045220f42496ac48e0d475'),
 'PRODUCTS_FINAL_REVIEW':('388908b6da3539484cb8e2e03ada6ff5cb2204a4','6cc8c37e23c89488f3113efd96952d13f253f274'),
 'DIGITAL_FINAL_REVIEW':('d48b4a4f86de29aa968665f1601b785bd1824c54','10464979fd510380aafe7e421d241a8f176d538d')}
check('upstream exact subject mappings',all((single(acceptance,id=k)['subject_sha'],single(acceptance,id=k)['review_sha'])==v
      for k,v in expected_subjects.items()))
check('EV-MR03 separate pending subject',single(acceptance,id='METHODS_V3')['subject_sha']=='f99d6cd52dcc06995bf984fddd2f057226243b06' and
      single(acceptance,id='METHODS_V3')['verdict']=='PENDING_EV_MR03')
bridge = rows('strategy/whole_company_bridge.csv')
check('company scale bridge kept conditional',len(bridge)==6 and all(
    r['future_KEEP2028']=='UNKNOWN' and r['future_total_market2028']=='UNKNOWN' and r['future_rank_share']=='NOT_ESTIMATED' and
    near(r['illustration_keep2025_unchanged_plus_project'],2700000+float(r['dated_new_segments_less_listed_migration'])) and
    near(r['remaining_to_historical_second_if_no_other_change'],13800000-2700000-float(r['dated_new_segments_less_listed_migration']))
    for r in bridge))
evidence['budget_rows'] = len(budget)
for path in ('annual_calendar.py','calendar_contract.json','model_kernel.py',
    'inputs/network_b471/v2/calculate.py','inputs/network_b471/v2/findings.json',
    'inputs/network_b471/v2/outputs/C33_next_assignment.csv',
    'inputs/network_b471/v2/outputs/bank_upper_bound.csv',
    'inputs/products_3889/budget_requirements.json','inputs/products_3889/handoff.md',
    'inputs/products_3889/outputs/C10_budget_envelopes.csv',
    'inputs/products_3889/outputs/C17_alternatives.csv',
    'inputs/products_3889/parameters.json',
    'inputs/network_b471/v2/outputs/C07_demand_bounds.csv',
    'inputs/network_b471/v2/outputs/cost_coverage.csv',
    'inputs/digital_d48/annual_carriers.csv','inputs/digital_d48/parameters.json',
    'inputs/digital_d48/digital_thresholds.csv','qualification_events_v3.json'):
    text(path)
evidence['scope_exclusions'] = ['EV-MR03 integer annual/MCT/LP/sync/C31C35 calculation NOT_RUN',
    'No live market/source validity, free fleet, award, operational acceptance, full PnL, gross cash or team acceptance',
    'No owner verifier execution; no 480-hash/325-copy/442-v3 preservation rerun']

OUT.mkdir(exist_ok=True)
(OUT/'checks.json').write_text(json.dumps(dict(subject=SHA,checks=checks,
    passed=sum(c['passed'] for c in checks),failed=sum(not c['passed'] for c in checks)),ensure_ascii=False,indent=2)+'\n')
(OUT/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
(OUT/'input_manifest.json').write_text(json.dumps(dict(subject=SHA,files=list(manifest.values())),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(checks=len(checks),failed=[c['name'] for c in checks if not c['passed']],
    mixed11=mixed_evidence,resource_boundaries=boundary),ensure_ascii=False,indent=2))
raise SystemExit(1 if any(not c['passed'] for c in checks) else 0)
