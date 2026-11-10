#!/usr/bin/env python3
"""New pinned context only. Never substitutes a cap for an actual awarded grant."""
import csv
import json
import calculate as c


def main():
    root=c.SOURCE_ROOT/'inputs/evidence06cb'
    joins=c.read(root/'pair_hypothesis_join.csv')
    links=[r for r in joins if r['hypothesis'] in ['C01','C03','C04','C07','C33']]
    c.write('evidence06cb_pair_links.csv',links)
    keys={frozenset((r['origin'],r['destination'])) for r in links}
    matches=[r for r in c.read(root/'subsidy_route_matches.csv') if frozenset((r['origin'],r['destination'])) in keys]
    c.write('evidence06cb_subsidy_listings.csv',matches)
    caps=c.read(root/'subsidy_cap_examples.csv')
    byroute={r['route']:r for r in caps}
    no_support=c.read(c.OUT/'C07_extension.csv')
    rows=[]
    for route,flights in [('KJA-OMS',4),('KUF-NJC',4),('KUF-MRV',4),('OMS-UFA',4)]:
        r=byroute[route];cap=float(r['appendix1_cap_rub_oneway'])
        row=dict(route=route,source_pin='06cb721b3e8e4eb8710c065c7b02078a112626a9',
                 assumed_actual_seats=100,cap_rub_per_oneway_completed_flight=cap,
                 hypothetical_completed_eligible_flights=flights,territorial_coefficient_scenario=1,
                 arithmetic_payment_ceiling_rub=cap*flights,
                 contracted_rate='UNKNOWN; cannot replace by cap',actual_RW_award='NOT_ESTABLISHED',
                 fare_rule='ALL economy seats <=special retail fare; compliant net yield must be derived anew',
                 supported_PnL='NOT_CALCULATED; award/rate/coefficient/special-fare net-yield inputs missing',
                 scope='pure payment ceiling under2026table,100seats,coefficient1; not future revenue')
        rows.append(row)
    c.write('subsidy_payment_caps_only.csv',rows)
    # Thresholds measure the uncovered no-support gap. They are not grant/PnL scenarios.
    gaps=[]
    for s in ['base','cautious']:
        r=next(x for x in no_support if x['scenario']==s and x['turn_minutes']=='45')
        deficit=-float(r['delta_contribution_rub_week'])
        gaps.append(dict(hypothesis='C07',scenario=s,no_support_gap_rub_week=deficit,
                         added_completed_flights_if_all_eligible=4,
                         required_payment_rub_per_added_flight_before_fare_effect=deficit/4,
                         comparison_2026cap_at100seats_coefficient1_rub=310249,
                         min_coefficient_at_cap_before_fare_effect=deficit/(4*310249),
                         fare_effect='not assumed zero in supportedPnL; no supportedPnL computed',
                         caveat='optimistic gap threshold only; all-seat special fare can change ticket net yield, volumes and displacement',
                         prior_SVX_OMS_flights='same counts; no new per-passenger subsidy inferred from new through journeys'))
    c.write('subsidy_gap_thresholds.csv',gaps)
    (c.HERE/'evidence_addendum.json').write_text(json.dumps(dict(
        source_pin='06cb721b3e8e4eb8710c065c7b02078a112626a9',
        supplied_scope=dict(pairs=40,pair_hypothesis_links=64,service_rows=288,service_rows_are_frequencies=False),
        personal_checks='selected pinned CSV rows and primary rule text; hashes checked; no full parser review claimed',
        supplied_root_checks='hashes/twoPDF/seven cap examples; full parser review pending',
        formula='completed eligible flights * contracted per-flight rate<=appendix cap * territorial coefficient',
        fare_rule='paragraph7a requires all economy seats <= special fare; do not retain arbitrary net yield',
        no_support='original941d preserved byte-for-byte; v2 no-support diagnostic separate',
        supported_case='NOT_CALCULATED; no invented future RW award/rate or capped-fare net yield'),ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':
    main()
