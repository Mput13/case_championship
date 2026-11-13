#!/usr/bin/env python3
"""Read-only verification of sealed member hashes and dated resource records."""
import csv
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def date(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def verify():
    manifests = {}
    for folder in ('route_evidence', 'resource_scenarios'):
        base = ROOT / folder
        raw = (base / 'output_manifest.json').read_bytes()
        manifest = json.loads(raw)
        for item in manifest['files']:
            content = (base / item['path']).read_bytes()
            assert len(content) == item['bytes'], item['path']
            assert digest(content) == item['sha256'], item['path']
        manifests[folder] = {'sha256': digest(raw), 'members': len(manifest['files'])}

    base = ROOT / 'resource_scenarios'
    pins = json.loads((base / 'inputpins.json').read_text())
    for source in pins['sources']:
        raw = subprocess.check_output(['git', 'show', source['commit'] + ':' + source['source_path']], cwd=ROOT)
        assert digest(raw) == source['sha256'], source['source_path']
        assert len(raw) == source['bytes'], source['source_path']

    with (base / 'dated_templates.csv').open() as stream:
        flights = list(csv.DictReader(stream))
    assert len({row['template_flight_id'] for row in flights}) == len(flights)
    groups = defaultdict(list)
    for row in flights:
        assert row['seats'] == row['saleable_seats'] == ''
        assert (date(row['arrival_utc']) - date(row['departure_utc'])).total_seconds() == int(row['block_minutes']) * 60
        assert date(row['departure_local']) == date(row['departure_utc'])
        assert date(row['arrival_local']) == date(row['arrival_utc'])
        groups[tuple(row[k] for k in ('scenario_id', 'season', 'airport_branch', 'block_stress'))].append(row)

    expected_pairs = {'UNDER4': 6, 'PILOT5': 8, 'PLAN6': 10, 'EXTRA7': 12, 'EXTRA8': 12}
    expected_workers = {'UNDER4': 2, 'PILOT5': 3, 'PLAN6': 4, 'EXTRA7': 5, 'EXTRA8': 6}
    for (scenario, season, airport, stress), rows in groups.items():
        pairs = {tuple(sorted((r['origin_airport'], r['destination_airport']))) for r in rows}
        assert len(pairs) == expected_pairs[scenario]
        assert len({r['aircraft_id'] for r in rows}) == expected_workers[scenario]
        frequencies = Counter((r['origin_airport'], r['destination_airport']) for r in rows)
        for (origin, destination), count in frequencies.items():
            expected = 2
            if 'OMS' in (origin, destination):
                expected = 5 if scenario == 'EXTRA8' and ({origin, destination} & {airport, 'IKT'}) else 3
            assert count == expected, (scenario, origin, destination, count, expected)
        daily = defaultdict(list)
        for row in rows:
            daily[(row['aircraft_id'], row['departure_local'][:10])].append(row)
        for legs in daily.values():
            legs.sort(key=lambda r: date(r['departure_utc']))
            assert sum(int(r['block_minutes']) for r in legs) <= 600
            assert legs[0]['origin_airport'] == legs[0]['base_airport']
            assert legs[-1]['destination_airport'] == legs[0]['base_airport']
            for previous, current in zip(legs, legs[1:]):
                assert previous['destination_airport'] == current['origin_airport']
                assert (date(current['departure_utc']) - date(previous['arrival_utc'])).total_seconds() >= 45 * 60

    with (base / 'return_windows.csv').open() as stream:
        returns = list(csv.DictReader(stream))
    for row in returns:
        assert row['has_3_or_4_nights'] == row['has_7_nights'] == 'True'
        outbound_day = date(row['outbound_departure_local']).date()
        for nights in (3, 4, 7):
            value = row[f'return_{nights}_nights_departure_local']
            if value:
                assert (date(value).date() - outbound_day).days == nights
    return {
        'status': 'PASS', 'manifests': manifests, 'exact_git_inputs': len(pins['sources']),
        'dated_flights_checked': len(flights), 'scenario_week_airport_stress_groups': len(groups),
        'return_rows_checked': len(returns),
        'limits': 'Read-only provenance and selected CSV arithmetic/calendar checks; not independent engine/market/crew/MRO/slots/finance acceptance.'
    }


if __name__ == '__main__':
    print(json.dumps(verify(), ensure_ascii=False, indent=2))
