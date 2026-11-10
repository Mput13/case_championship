#!/usr/bin/env python3
"""Offline arithmetic only. No network, browser, bookings, or data outside this folder."""
import csv
import hashlib
import json
import math
from pathlib import Path

BASE = Path(__file__).resolve().parent


def write_csv(name, rows):
    with (BASE / name).open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    p = json.loads((BASE / 'parameters.json').read_text())
    digital = []
    for x in p['digital_scenarios']:
        gross = x['eligible_events'] * x['uplift_absolute'] * x['unit_contribution_rub']
        net_variable = gross - x['cannibalized_contribution_rub']
        annual = net_variable - x['annual_support_cash_rub']
        cost = x['implementation_cash_rub'] + x['annual_support_cash_rub'] + x['cannibalized_contribution_rub']
        required = cost / (x['eligible_events'] * x['unit_contribution_rub'])
        digital.append({**x,
            'incremental_outcomes': x['eligible_events'] * x['uplift_absolute'],
            'incremental_contribution_before_cannibalization_rub': gross,
            'net_variable_contribution_rub': net_variable,
            'annual_result_after_support_rub': annual,
            'first_year_result_after_implementation_rub': annual - x['implementation_cash_rub'],
            'break_even_uplift_absolute': required,
            'break_even_uplift_pp': required * 100,
            'max_implementation_for_year_one_break_even_rub': annual,
            'cash_out_budget_year_one_rub': x['implementation_cash_rub'] + x['annual_support_cash_rub'],
            'cash_in_effect': 'NOT_ESTIMATED',
            'status': 'DIAGNOSTIC_NOT_FORECAST'})
    write_csv('digital_thresholds.csv', digital)

    rows = []
    for target in p['resource_targets']:
        delta = max(0, target - p['red_wings_passengers'])
        for x in p['resource_scenarios']:
            legs = delta / (x['seats'] * x['load_factor'])
            hours = legs * x['block_hours_per_leg']
            stock_hours = 365 * x['productive_hours_per_active_day'] * x['availability_including_reserve']
            additional_stock = math.ceil(hours / stock_hours)
            total_stock = math.ceil(target / (x['seats'] * x['load_factor']) * x['block_hours_per_leg'] / stock_hours)
            rows.append({**x, 'target_passenger_segments_per_year': target,
                'incremental_passenger_segments_per_year': delta,
                'incremental_seats_per_year': delta / x['load_factor'],
                'incremental_one_way_legs_per_year': legs,
                'incremental_one_way_legs_per_day': legs / 365,
                'incremental_block_hours_per_year': hours,
                'additional_stock_equivalent_ceil': additional_stock,
                'total_homogeneous_stock_equivalent_ceil': total_stock,
                'passenger_segments_per_stock_year': x['seats'] * x['load_factor'] * stock_hours / x['block_hours_per_leg'],
                'status': 'SCENARIO_EQUIVALENT_NOT_FLEET_ORDER'})
    write_csv('resource_scale.csv', rows)

    shares = []
    for scenario, delta_market in [('transfer_from_other_Russian_carriers', 0), ('all_incremental_to_market', p['number_two_landmark']-p['red_wings_passengers'])]:
        before = p['red_wings_passengers']/p['market_passengers']*100
        after = p['number_two_landmark']/(p['market_passengers']+delta_market)*100
        shares.append({'scenario':scenario,'baseline_year':2025,'baseline_market':p['market_passengers'],
            'scenario_market':p['market_passengers']+delta_market,'rw_before':p['red_wings_passengers'],
            'rw_landmark':p['number_two_landmark'],'rw_share_before_pct':before,'rw_share_after_pct':after,
            'change_pp':after-before,'status':'STATIC_LANDMARK_NOT_FUTURE_SHARE'})
    write_csv('market_share_scenarios.csv', shares)

    power = []
    for card, baseline, delta, events in [
        ('D01_small_effect', .04, .001, 1000000),
        ('D01_larger_MDE', .04, .003, 1000000),
        ('D02_attach', .08, .005, 500000),
        ('D03_repeats', .40, .10, 60000),
    ]:
        per_arm = math.ceil(2 * (1.96 + .84)**2 * baseline * (1-baseline) / delta**2)
        power.append({'id':card,'assumed_baseline':baseline,'absolute_MDE':delta,
            'events_per_arm_approx':per_arm,'events_total':per_arm*2,
            'assumed_eligible_events_per_year':events,'traffic_days_approx':per_arm*2/events*365,
            'alpha_two_sided':.05,'power_approx':.80,
            'limitation':'Normal approximation only; independent binary cases; recompute with actual baseline and clusters; margin metric may need larger sample'})
    write_csv('experiment_power.csv', power)

    mixed = []
    gap = p['number_two_landmark'] - p['red_wings_passengers']
    for sid, fraction in [('regional_base', .5), ('medium_194', .35), ('wide_412', .15)]:
        x = next(s for s in p['resource_scenarios'] if s['id']==sid)
        passengers = gap * fraction
        legs = passengers / (x['seats'] * x['load_factor'])
        hours = legs * x['block_hours_per_leg']
        stock = math.ceil(hours / (365*x['productive_hours_per_active_day']*x['availability_including_reserve']))
        mixed.append({'id':sid,'incremental_passenger_fraction':fraction,'incremental_passengers':passengers,
            'one_way_legs':legs,'block_hours':hours,'additional_stock_equivalent_ceil':stock,
            'status':'ARBITRARY_MIX_DIAGNOSTIC_NOT_NETWORK_OR_FLEET_PLAN'})
    write_csv('mixed_scale.csv', mixed)

    # Reproducible sanity checks of accounting boundaries, not a market validation.
    assert math.isclose(p['number_two_landmark'] - p['red_wings_passengers'], 11100000)
    assert all(x['additional_stock_equivalent_ceil'] > 0 for x in rows)
    check = {'offline_arithmetic':'PASS','digital_rows':len(digital),'resource_rows':len(rows),
        'market_share_rows':len(shares),'power_rows':len(power),'mixed_scale_rows':len(mixed),
        'input_sha256':hashlib.sha256((BASE/'parameters.json').read_bytes()).hexdigest(),
        'live_business_effect':'NOT_RUN','cash_reconciliation':'NOT_RUN'}
    (BASE/'validation.json').write_text(json.dumps(check, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(check,ensure_ascii=False))


if __name__ == '__main__':
    main()
