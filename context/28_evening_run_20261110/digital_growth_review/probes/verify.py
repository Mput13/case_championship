#!/usr/bin/env python3
"""Independent exact-Git-blob audit. Writes only into this review package."""
import csv
import hashlib
import io
import json
import math
import subprocess
from datetime import datetime, timezone
from fractions import Fraction as F
from pathlib import Path

SUBJECT = 'd48b4a4f86de29aa968665f1601b785bd1824c54'
SCOPE = 'context/28_evening_run_20261110/digital_growth/'
OUT = Path(__file__).resolve().parent
REVIEW = OUT.parent
REPO = REVIEW.parents[2]

def git(*args):
    return subprocess.check_output(['git', *args], cwd=REPO)

def blob(path, commit=SUBJECT):
    return git('show', f'{commit}:{path}')

def load(name):
    return json.loads(blob(SCOPE + name))

def rows(name):
    return list(csv.DictReader(io.StringIO(blob(SCOPE + name).decode())))

def q(x):
    return F(str(x))

def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def main():
    checks = []
    def equal(label, actual, expected):
        ok = math.isclose(float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-9)
        checks.append({'check': label, 'actual': float(actual) if isinstance(actual, F) else actual, 'expected': float(expected), 'pass': ok})
        assert ok, label

    manifest = load('manifest.json')
    pins = []
    for entry in manifest['inputs']:
        b = blob(entry['path'], entry['commit'])
        ok = len(b) == entry['bytes'] and hashlib.sha256(b).hexdigest() == entry['sha256']
        pins.append({**entry, 'verified': ok})
        assert ok
    files = []
    for line in git('ls-tree', '-r', SUBJECT, '--', SCOPE).decode().splitlines():
        meta, path = line.split('\t')
        b = blob(path)
        files.append({'path': path, 'git_blob': meta.split()[2], 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()})
    lookup = {r['path'][len(SCOPE):]: r for r in files}
    for entry in manifest['artifacts']:
        actual = lookup[entry['path']]
        assert all(entry[k] == actual[k] for k in ('bytes', 'sha256'))
    assert set(lookup) == {r['path'] for r in manifest['artifacts']} | {'manifest.json'}
    (REVIEW / 'source_manifest.json').write_text(json.dumps({'subject_sha': SUBJECT, 'scope': SCOPE,
        'pinned_inputs': pins, 'subject_files': files, 'artifact_hashes_verified': len(manifest['artifacts'])}, ensure_ascii=False, indent=2) + '\n')

    p = load('parameters.json')
    digital = rows('digital_thresholds.csv')
    for x, r in zip(p['digital_scenarios'], digital):
        tag = x['id'] + '/' + x['scenario']
        assert x['id'] == r['id'] and x['scenario'] == r['scenario']
        n, d, m, c, i, s = [q(x[k]) for k in ('eligible_events','uplift_absolute','unit_contribution_rub','cannibalized_contribution_rub','implementation_cash_rub','annual_support_cash_rub')]
        gross = n*d*m
        expected = {'incremental_outcomes':n*d,'incremental_contribution_before_cannibalization_rub':gross,
            'net_variable_contribution_rub':gross-c,'annual_result_after_support_rub':gross-c-s,
            'first_year_result_after_implementation_rub':gross-c-s-i,'break_even_uplift_absolute':(c+i+s)/n/m,
            'break_even_uplift_pp':100*(c+i+s)/n/m,'max_implementation_for_year_one_break_even_rub':gross-c-s,
            'cash_out_budget_year_one_rub':i+s}
        for field, value in expected.items():
            equal(tag+'/'+field, r[field], value)
        equal(tag+'/break_even_residual', n*((c+i+s)/n/m)*m-c-i-s, 0)
        assert (float(r['first_year_result_after_implementation_rub']) < 0) == (x['scenario'] == 'cautious')
        assert r['cash_in_effect'] == 'NOT_ESTIMATED'
    assert len(digital) == len(p['digital_scenarios']) == 6

    resources = rows('resource_scale.csv')
    scenarios = {x['id']:x for x in p['resource_scenarios']}
    for r in resources:
        x = scenarios[r['id']]
        target, seats, lf, t, h, a = [q(v) for v in (r['target_passenger_segments_per_year'], x['seats'], x['load_factor'], x['block_hours_per_leg'], x['productive_hours_per_active_day'], x['availability_including_reserve'])]
        gap = target-q(p['red_wings_passengers'])
        production = 365*h*a*seats*lf/t
        expected = {'incremental_passenger_segments_per_year':gap,'incremental_seats_per_year':gap/lf,
            'incremental_one_way_legs_per_year':gap/seats/lf,'incremental_one_way_legs_per_day':gap/seats/lf/365,
            'incremental_block_hours_per_year':gap/seats/lf*t,'passenger_segments_per_stock_year':production,
            'additional_stock_equivalent_ceil':math.ceil(gap/production),'total_homogeneous_stock_equivalent_ceil':math.ceil(target/production)}
        for field, value in expected.items():
            equal(r['id']+'/'+str(target)+'/'+field, r[field], value)
        k = int(r['additional_stock_equivalent_ceil'])
        assert (k-1)*production < gap <= k*production
    assert len(resources) == 16

    gap = q(p['number_two_landmark'])-q(p['red_wings_passengers'])
    mix = rows('mixed_scale.csv')
    fractions = {'regional_base':F(1,2), 'medium_194':F(35,100), 'wide_412':F(15,100)}
    assert sum(fractions.values()) == 1
    for r in mix:
        x = scenarios[r['id']]
        fraction = fractions[r['id']]
        pax = gap*fraction
        legs = pax/q(x['seats'])/q(x['load_factor'])
        hours = legs*q(x['block_hours_per_leg'])
        annual = 365*q(x['productive_hours_per_active_day'])*q(x['availability_including_reserve'])
        for field, expected in {'incremental_passenger_fraction':fraction,'incremental_passengers':pax,
            'one_way_legs':legs,'block_hours':hours,'additional_stock_equivalent_ceil':math.ceil(hours/annual)}.items():
            equal('mixed/'+r['id']+'/'+field, r[field], expected)
    assert len(mix) == 3

    market = q(p['market_passengers'])
    baseline = q(p['red_wings_passengers'])
    landmark = q(p['number_two_landmark'])
    shares = rows('market_share_scenarios.csv')
    for r, denominator in zip(shares, [market, market+gap]):
        for field, expected in {'rw_share_before_pct':baseline/market*100,'rw_share_after_pct':landmark/denominator*100,
            'change_pp':landmark/denominator*100-baseline/market*100,'scenario_market':denominator}.items():
            equal('share/'+r['scenario']+'/'+field, r[field], expected)
        assert r['baseline_year'] == '2025'
    assert len(shares) == 2

    power = rows('experiment_power.csv')
    power_inputs = [(F(4,100),F(1,1000),1000000), (F(4,100),F(3,1000),1000000), (F(8,100),F(5,1000),500000), (F(40,100),F(10,100),60000)]
    for r, (b,d,n) in zip(power, power_inputs):
        per_arm = math.ceil(2*F(28,10)**2*b*(1-b)/d**2)
        for field, expected in {'assumed_baseline':b,'absolute_MDE':d,'events_per_arm_approx':per_arm,
            'events_total':2*per_arm,'traffic_days_approx':F(2*per_arm*365,n)}.items():
            equal('power/'+r['id']+'/'+field, r[field], expected)
    assert len(power) == 4

    # Independent counterexamples: unit/percentage/flow substitutions change the answer.
    probes = {
        'D01_percentage_points': {'correct_0_1pp_outcomes_at_1m':1000,'incorrect_0_1_fraction_outcomes':100000,'factor_error':100},
        'D01_full_capacity_counterexample': {'extra_web_orders':100,'displaced_same_margin_orders':100,'unit_margin':2500,'gross_web_contribution':250000,'net_carrier_contribution':0},
        'D01_orders_are_not_passengers': {'orders':1000,'passengers_per_order':2,'legs_per_passenger':2,'segments':4000},
        'D02_early_shift_counterexample': {'existing_bags_shifted_3500_to_2700':500,'new_bags':0,'revenue_change_rub':-400000,'assumption':'Same bags and matched published minima only; not a live price quote.'},
        'D02_gross_price_is_not_margin': {'new_bags':2500,'illustrative_price':2700,'assumed_unit_margin':1000,'gross_receipts':6750000,'contribution':2500000},
        'D03_denominator': {'initial_help_cases':60000,'baseline_repeat_probability':0.4,'after':0.3,'avoided_repeat_cases':6000,'not_10_percent_relative':2400},
        'D03_probability_bound': {'baseline':0.4,'required_reduction':float(F(2000000,30000*150)),'max_resource_saving':1800000,'first_year_cost':2000000,'best_possible_first_year_result':-200000},
        'D03_staffing_counterexample': {'avoided_contacts':6000,'resource_value_each':300,'resource_value':1800000,'cash_saving_with_fixed_staff_and_no_avoided_hire':0},
        'D03_one_case_two_repeats': {'change_in_probability_of_any_repeat':0,'change_in_contact_count':-1,'limitation':'Binary probability model monetizes one avoided case; not full repeat-contact workload without multiplicity model.'},
        'D01_time': {'traffic_days':float(F(2*int(power[0]['events_per_arm_approx'])*365,1000000)),'after_last_exposure_refund_followup_days':14,'not_a_monthly_effect_test':True},
        'D03_time': {'enrolment_days':float(F(2*377*365,60000)),'last_cohort_repeat_followup_days':7,'total_lower_bound_days':float(F(2*377*365,60000)+7)},
        'reserve_once': {'base_100seat_capacity':139612.5,'stock_gap_ceil':80,'double_reserve_wrong_ceil':math.ceil(gap/(F(1396125,10)*F(9,10)))},
        '2028_calendar': {'standard_days':365,'calendar_2028_days':366,'not_a_delivery_calendar':True},
        'company_group': {'aeroflot_group_m':55.3403,'company_m':29.5473,'utair_fixedwing_m':6.2,'utair_group_m':6.9,'not_additive':True},
        'joint_effect_counterexample': {'baseline_orders':100,'orders_after_D01_alone':110,'orders_after_D02_alone':110,'orders_after_both_same_people':110,'sum_of_separate_uplifts_wrong':20,'joint_uplift':10}
    }
    save('counterexamples.json', probes)
    save('arithmetic_checks.json', {'subject_sha':SUBJECT,'method':'Independent rational arithmetic; no owner calculate import; all generated numeric fields checked.',
        'counts':{'digital':6,'resource':16,'power':4,'share':2,'mixed':3},'numeric_assertions':len(checks),'checks':checks,'passed':True})

    # Execute the reviewed owner script only inside the owned review directory.
    repro = OUT / 'owner_reproduction'
    repro.mkdir(exist_ok=True)
    for name in ['calculate.py','parameters.json']:
        (repro/name).write_bytes(blob(SCOPE+name))
    run = subprocess.run(['python3', str(repro/'calculate.py')], cwd=REPO, capture_output=True, text=True, check=True)
    generated = ['digital_thresholds.csv','resource_scale.csv','market_share_scenarios.csv','experiment_power.csv','mixed_scale.csv','validation.json']
    matches = {name:(repro/name).read_bytes()==blob(SCOPE+name) for name in generated}
    assert all(matches.values())
    save('owner_reproduction.json', {'subject_sha':SUBJECT,'stdout':run.stdout,'stderr':run.stderr,'byte_identical':matches})

    png_dir = OUT / 'pinned_png'
    png_dir.mkdir(exist_ok=True)
    from PIL import Image
    pngs = []
    for item in files:
        if item['path'].endswith('.png'):
            path = png_dir / Path(item['path']).name
            path.write_bytes(blob(item['path']))
            with Image.open(path) as im:
                im.load()
                pngs.append({'name':path.name,'size':im.size,'sha256':item['sha256'],'decoded':True})
    assert len(pngs) == 14
    save('png_decode.json', pngs)
    print(json.dumps({'passed':True,'pins':len(pins),'artifacts':len(manifest['artifacts']),'numeric_assertions':len(checks),'pngs':len(pngs),'at_utc':datetime.now(timezone.utc).isoformat()}))

if __name__ == '__main__':
    main()
