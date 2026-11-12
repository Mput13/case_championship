#!/usr/bin/env python3
"""Read pinned inputs only; write transparent PEE arithmetic, not a network refit."""
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent.parent


def rows(name):
    with (PACKAGE / 'inputs/model' / name).open() as f:
        return list(csv.DictReader(f))


def calculate():
    manifest = json.loads((PACKAGE / 'input_manifest.json').read_text())
    for item in manifest:
        p = PACKAGE / item['path']
        assert hashlib.sha256(p.read_bytes()).hexdigest() == item['sha256'], p
    rr = rows('network_routes.csv')
    summaries = rows('network_summary.csv')
    model = {}
    for scenario in ('base', 'base_sub', 'cautious', 'cautious_sub'):
        selected = [r for r in rr if r['scenario'] == scenario and r['variant'] == 'Хаб PEE']
        summary = next(r for r in summaries if r['scenario'] == scenario and r['hub'] == 'PEE')
        local = sum(float(r['pax_year_local']) for r in selected)
        transfer_segments = sum(float(r['pax_year_transfer_seg']) for r in selected)
        seats = sum(float(r['freq_week_each_way']) * 2 * 52 * 100 for r in selected)
        model[scenario] = {
            'status': 'pinned_model_scenario_not_observation',
            'summary': summary,
            'sum_local_rounded_rows': local,
            'sum_transfer_segments_rounded_rows': transfer_segments,
            'seats_year_assumed_100_seats_52_weeks': seats,
            'local_only_seat_fraction_arithmetic_not_reoptimized_load': local / seats,
            'transfer_share_of_segments_from_rounded_rows': transfer_segments / (local + transfer_segments),
            'rows': [{k: r[k] for k in ('to', 'km', 'freq_week_each_way', 'pax_year_local',
                                       'pax_year_transfer_seg', 'pax_year_segments', 'result_mln_year')}
                     | {'local_only_seat_fraction': float(r['pax_year_local']) /
                        (float(r['freq_week_each_way']) * 2 * 52 * 100)} for r in selected],
            'rounding_difference_vs_summary_segments': local + transfer_segments - float(summary['segments_year'])
        }
        assert abs(local + transfer_segments - float(summary['segments_year'])) <= 3
        assert abs(transfer_segments - 2 * float(summary['transfer_od_year'])) <= 3
    known = [r for r in rows('known_flows.csv') if r['from_iata'] == 'PEE']
    top3 = sum(float(r['pax']) for r in known if r['to_iata'] in ('MOW', 'AER', 'LED'))
    # Legal act 44-01-02-618, 06.10.2026, pp. 4-6. Regional amounts in its table;
    # no unobserved federal allocation or second regional payer is added.
    support = {
        'VOG': {'departures_each_way': 44, 'regional_rub_out': 147368.28, 'regional_rub_back': 147368.27},
        'GOJ_winter': {'departures_each_way': 59, 'regional_rub_out': 63215.83, 'regional_rub_back': 63215.82},
        'GOJ_summer': {'departures_each_way': 44, 'regional_rub_out': 98450.88, 'regional_rub_back': 98450.87},
        'MSQ': {'roundtrips': 54, 'regional_rub_per_roundtrip': 1186000},
        'NQZ': {'roundtrips': 36, 'regional_rub_per_roundtrip': 1200000},
        'RGK': {'departures_each_way': 48, 'regional_rub_out': 786131, 'regional_rub_back': 786131},
    }
    for r in support.values():
        if 'roundtrips' in r:
            r['table_program_rub_not_award'] = r['roundtrips'] * r['regional_rub_per_roundtrip']
        else:
            r['table_program_rub_not_award'] = r['departures_each_way'] * (r['regional_rub_out'] + r['regional_rub_back'])
            r['scenario_seats_100_not_required_aircraft_size'] = r['departures_each_way'] * 2 * 100
            r['regional_rub_per_scenario_available_seat'] = r['table_program_rub_not_award'] / r['scenario_seats_100_not_required_aircraft_size']
    output = {
        'as_of': '2026-11-12',
        'pinned_manifest_entries_sha256_verified': len(manifest),
        'model': model,
        'airport_2025': {
            'total': 2004861, 'domestic': 1707582, 'international': 284295, 'transit_as_named_by_airport': 12984,
            'component_sum': 1707582 + 284295 + 12984,
            'transit_share_not_transfer_share': 12984 / 2004861,
            'top3_pair_segments_from_pinned_secondary_source': top3,
            'top3_share_of_domestic_if_definitions_compatible': top3 / 1707582,
        },
        'support_2027': support,
        'access_scenarios_minutes': {
            'status': 'illustration_not_measured_door_to_door_distribution',
            'local_access_assumed': 60, 'local_predeparture_assumed': 90,
            'PEE_ready_to_depart': 60 + 90,
            'SVX_bus_fast_published_plus_120_buffer': 318 + 120,
            'SVX_bus_other_published_plus_120_buffer': 420 + 120,
            'extra_vs_local_fast': 318 + 120 - 150,
            'extra_vs_local_other': 420 + 120 - 150,
            'rail_sample_340_plus_station_airport_65_plus_buffer_120': 340 + 65 + 120,
        },
        'OMS_direct_3weekly_100seats_scenario': {
            'seats': 3 * 2 * 52 * 100, 'model_local_pax_base': 7985,
            'model_local_seat_fraction': 7985 / (3 * 2 * 52 * 100),
            'pax_at_75pct_scenario_not_break_even': 3 * 2 * 52 * 100 * .75,
            'extra_pax_to_75pct_not_break_even': 3 * 2 * 52 * 100 * .75 - 7985,
        },
        'education_upper_bound_scenario': {
            'foreign_entrants_one_university_2025': 352 + 22,
            'assumed_annual_oneway_flights_each': 4,
            'all_destinations_pax_segments_if_every_entrant_flies': (352 + 22) * 4,
            'not_an_estimate_for_one_OD': True,
        },
        'dated_complete_trip_illustrations': {
            'status': 'published_air_times_plus_explicit_access_assumptions_not_observed_trip',
            'date': '2026-11-13',
            'PEE_origin_access_min_assumed': 60,
            'PEE_preflight_min_assumed': 90,
            'arrival_to_destination_min_assumed': 60,
            'PEE_MCX': {'flight': 'A44028', 'departure_local': '07:55 UTC+5',
                        'arrival_local': '09:00 UTC+3', 'air_min': 185,
                        'total_min_scenario': 60 + 90 + 185 + 60,
                        'leave_origin_PEE_local_scenario': '05:25',
                        'reach_destination_MCX_local_scenario': '10:00'},
            'PEE_MRV': {'flight': 'A46018', 'departure_local': '15:50 UTC+5',
                        'arrival_local': '17:20 UTC+3', 'air_min': 210,
                        'total_min_scenario': 60 + 90 + 210 + 60,
                        'leave_origin_PEE_local_scenario': '13:20',
                        'reach_destination_MRV_local_scenario': '18:20'},
            'SVX_MRV_fast_bus_misses_U6_205_on_Friday': {
                'bus_arrives_SVX_local': '10:40', 'flight_departs_SVX_local': '08:45',
                'bus_arrives_min_after_departure': 115,
                'sources': ['PEE-S12', 'PEE-S42'],
                'other_airlines_or_overnight_bus_not_ruled_out': True,
            },
        },
        'coverage_model_unique_PEE_partners': sorted({r['to'] if r['from'] == 'PEE' else r['from']
                                                    for r in rr if 'PEE' in (r['from'], r['to'])}),
    }
    assert output['airport_2025']['component_sum'] == output['airport_2025']['total']
    return output


if __name__ == '__main__':
    (HERE / 'calculations.json').write_text(json.dumps(calculate(), ensure_ascii=False, indent=2) + '\n')
    print('Verified pinned manifest; wrote calculations.json')
