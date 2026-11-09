#!/usr/bin/env python3
"""Independent pinned-source/calendar/accounting reconciliation. Never run peer code."""
import argparse
import csv
import datetime as dt
import hashlib
import io
import itertools
import json
import re
import subprocess
from collections import Counter
from fractions import Fraction
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parent
ALT = 'fa39de413ac00a93b0214840aae2e7916332cef5'
HYP = 'eac4ed472c834c8520e94ebeff160211d1f675e2'
AR = 'context/16_agent_research/alternative/product_probe_v1/'
HR = 'context/16_agent_research/hypotheses/experiment_v1/'
CR = 'c14_products/3906edd033f75bc6/'
MR = 'cost_resource/6cf441ef38e2c6c5/'
RAW = BASE / 'raw' / 'input_set002'
OUT = BASE / 'reviews' / 'input_set002'
receipts = []
differences = []

def digest(b):
    return hashlib.sha256(b).hexdigest()

def capture(sha, path):
    b = subprocess.check_output(['git', 'show', sha + ':' + path])
    target = RAW / sha / path
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert target.read_bytes() == b
    else:
        target.write_bytes(b)
    receipts.append(dict(git_sha=sha, git_path=path, sha256=digest(b), bytes=len(b)))
    return b

def js(sha, path):
    return json.loads(capture(sha, path))

def rows(sha, path):
    return list(csv.DictReader(io.StringIO(capture(sha, path).decode())))

def equal(kind, actual, expected, key=''):
    if actual != expected:
        differences.append(dict(kind=kind, key=key, actual=actual, expected=expected))

def hashed_manifest(sha, root, manifest, field):
    for r in manifest[field]:
        b = capture(sha, root + r['path'])
        equal('HASH', digest(b), r['sha256'], r['path'])
        equal('BYTES', len(b), r.get('bytes', r.get('size_bytes')), r['path'])

def timestamp(s):
    return dt.datetime.fromisoformat(s)

def elapsed(a, b):
    return int((timestamp(a) - timestamp(b)).total_seconds() / 60)

def clock(s):
    a, b = map(int, s.split(':'))
    return 60 * a + b

class BlockText(HTMLParser):
    """Read complete labelled timetable blocks as text, not a cloned DOM extractor."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.current = None
        self.blocks = []

    def handle_starttag(self, tag, attrs):
        if tag == 'div':
            if self.current is not None:
                self.depth += 1
            elif 'result__block' in dict(attrs).get('class', '').split():
                self.current = []
                self.depth = 1

    def handle_endtag(self, tag):
        if tag == 'div' and self.current is not None:
            self.depth -= 1
            if self.depth == 0:
                self.blocks.append(' '.join(' '.join(self.current).split()))
                self.current = None

    def handle_data(self, data):
        if self.current is not None:
            self.current.append(data)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--airport-raw', type=Path)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_bytes = capture(HYP, HR + 'input_sets/phase2-frozen-002.json')
    equal('INPUT_SET_HASH', digest(manifest_bytes), '411a351509191dae5fc138ea13c40b0f783c0fb05fa65ad446a5d6f9edf37e45')
    m = json.loads(manifest_bytes)
    for p, h in m['verified_upstream_manifest_hashes'].items():
        equal('UPSTREAM_MANIFEST', digest(capture(ALT, AR + p)), h, p)
    for r in m['inputs']:
        b = capture(ALT, r['source_path'])
        equal('INPUT_HASH', digest(b), r['sha256'], r['input_id'])
        equal('FROZEN_COPY', capture(HYP, HR + r['stored_path']), b, r['input_id'])
    fm = js(ALT, AR + 'flight_checkpoint_manifest.json')
    hashed_manifest(ALT, AR, fm, 'files')
    cm = js(HYP, HR + CR + 'output_manifest.json')
    hashed_manifest(HYP, HR + CR, cm, 'files')
    mm = js(HYP, HR + MR + 'manifest.json')
    hashed_manifest(HYP, HR + MR, mm, 'outputs')
    for path, key, expected in [
        ('scripts/c14_product_probe.py', 'script', cm['input_hashes']['script']),
        ('scripts/cost_resource_probe.py', 'script_sha256', mm['inputs']['script_sha256']),
        ('contract.json', 'contract', cm['input_hashes']['contract']),
        ('runs/c26661067277af20/output_manifest.json', 'old_output', mm['inputs']['output_manifest_sha256']),
        ('inputs/core/airport_cost_selected_verified.csv', 'tariff', mm['inputs']['tariff_sha256']),
    ]:
        equal('MODULE_INPUT', digest(capture(HYP, HR + path)), expected, key)
    for old in js(HYP, HR + 'runs/c26661067277af20/output_manifest.json')['files']:
        p = HR + 'runs/c26661067277af20/' + old['path']
        equal('OLD_RUN_UNCHANGED', digest(capture(HYP, p)), old['sha256'], p)
    for run, d in [('3906edd033f75bc6', cm['input_hashes']), ('6cf441ef38e2c6c5', mm['inputs'])]:
        equal('RUN_ID', digest(json.dumps(d, sort_keys=True).encode())[:16], run)

    rules = rows(ALT, AR + 'normalized/flight_rules.csv')
    flights = rows(ALT, AR + 'normalized/dated_flights.csv')
    raw_path = RAW / 'airport_timetable.bin'
    if args.airport_raw:
        data = args.airport_raw.read_bytes()
        assert digest(data) == fm['raw_sources'][0]['sha256']
        raw_path.write_bytes(data)
    data = raw_path.read_bytes()
    equal('PRIMARY_RAW_HASH', digest(data), fm['raw_sources'][0]['sha256'])
    parser = BlockText()
    parser.feed(data.decode())
    blocks = [b for b in parser.blocks if re.search(r'[АA]4601[34]', b)]
    equal('PRIMARY_BLOCKS', len(blocks), 6)
    source_cells = []
    for block, rule in zip(blocks, rules):
        # Literal published cells checked independently from the normalized export.
        dates = re.findall(r'\d{2}\.\d{2}\.\d{4}', block)
        times = re.findall(r'(?<!\d)\d{2}:\d{2}(?!\d)', block)
        day = re.search(r'Дни\s+(Пн|Вт|Ср|Чт|Пт|Сб|Вс)', block)[1]
        weekday = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'].index(day) + 1
        expected = [dt.datetime.strptime(x, '%d.%m.%Y').date().isoformat() for x in dates]
        equal('PRIMARY_PERIOD', [rule['valid_from'], rule['valid_to']], expected, rule['rule_id'])
        equal('PRIMARY_CLOCKS', [rule['departure_local_time'], rule['arrival_local_time']], times, rule['rule_id'])
        equal('PRIMARY_WEEKDAY', rule['weekdays_iso'], str(weekday), rule['rule_id'])
        equal('PRIMARY_FLIGHT', rule['flight_number'], re.search(r'[АA]4601[34]', block)[0].replace('А', 'A'))
        labelled_direction = 'Направление ' + rule['departure_local_time'] + ' ' + rule['origin_name_source'] + ' ' + rule['arrival_local_time'] + ' ' + rule['destination_name_source'] + ' Аэропорт прилета'
        equal('PRIMARY_DIRECTION', labelled_direction in block, True, rule['rule_id'])
        source_cells.append(dict(rule_id=rule['rule_id'], published_dates=dates, published_times=times, weekday_iso=weekday))
    equal('PRIMARY_LOCAL_FOOTER', 'местное время аэропортов прилета/вылета' in data.decode(), True)
    expected_dates = set()
    rule_map = {r['rule_id']: r for r in rules}
    for r in rules:
        for n in range(21):
            day = dt.date(2026, 12, 7) + dt.timedelta(days=n)
            if r['valid_from'] <= day.isoformat() <= r['valid_to'] and str(day.isoweekday()) == r['weekdays_iso']:
                expected_dates.add((r['rule_id'], day.isoformat()))
    equal('CALENDAR_EXPANSION', {(f['rule_id'], f['departure_local_date']) for f in flights}, expected_dates)
    for f in flights:
        r = rule_map[f['rule_id']]
        dep = timestamp(f['departure_local_date'] + 'T' + r['departure_local_time']).replace(tzinfo=ZoneInfo(r['origin_iana']))
        # Explicitly conditional <24h rollover, not independently observed arrival date.
        offset = int(r['arrival_local_time'] <= r['departure_local_time'])
        arrival_date = dep.date() + dt.timedelta(days=offset)
        arr = timestamp(arrival_date.isoformat() + 'T' + r['arrival_local_time']).replace(tzinfo=ZoneInfo(r['destination_iana']))
        equal('DEPARTURE_UTC', f['departure_utc'], dep.astimezone(dt.timezone.utc).isoformat(), f['instance_id'])
        equal('ARRIVAL_UTC', f['arrival_utc'], arr.astimezone(dt.timezone.utc).isoformat(), f['instance_id'])
        equal('DURATION', int(f['planned_duration_minutes']), int((arr-dep).total_seconds()/60), f['instance_id'])
        equal('NO_EXECUTION_INVENTORY', [f['performed_status'], f['inventory_status']], ['UNKNOWN', 'UNKNOWN'])

    hotels = {h['property_id']: h for h in rows(ALT, AR + 'stay_offer/stay_rules.csv')}
    offers = {h['property_id']: h for h in rows(ALT, AR + 'stay_offer/public_offers.csv')}
    products = rows(HYP, HR + CR + 'flight_hotel_calendar.csv')
    equal('PRODUCT_ROW_COUNT', len(products), 24)
    equal('PRODUCT_UNIQUE_IDS', len({r['product_request_id'] for r in products}), len(products))
    outward = {f['instance_id']: f for f in flights if f['origin_iata'] == 'KVX' and f['departure_local_date'] <= '2026-12-13'}
    returns = {f['departure_local_date']: f for f in flights if f['origin_iata'] == 'MRV'}
    combinations = set(itertools.product(outward, hotels, [7, 10, 14], ['BOOK_DEPARTURE_DATE_REQUIRES_LATE_ADMISSION', 'BOOK_AIRPORT_ARRIVAL_DATE_REGULAR_CHECKIN']))
    equal('PRODUCT_GRID', {(r['outbound_instance_id'], r['property_id'], int(r['hotel_nights']), r['stay_basis']) for r in products}, combinations)
    oracle = []
    for p in products:
        f = outward[p['outbound_instance_id']]
        h = hotels[p['property_id']]
        start = dt.date.fromisoformat(f['departure_local_date'] if p['stay_basis'].startswith('BOOK_DEPARTURE') else f['arrival_local_date'])
        end = start + dt.timedelta(days=int(p['hotel_nights']))
        back = returns.get(end.isoformat())
        gate = 'UNKNOWN_HORIZON_COVERAGE' if end > dt.date(2026, 12, 27) else ('RETURN_RULE_PRESENT' if back else 'NO_EXACT_RETURN_IN_CAPTURED_RULES')
        equal('HOTEL_DATE', (p['booked_checkin_local_date'], p['booked_checkout_local_date']), (start.isoformat(), end.isoformat()), p['product_request_id'])
        equal('RETURN_JOIN', (p['return_instance_id'], p['calendar_gate']), (back['instance_id'] if back else '', gate), p['product_request_id'])
        budget = str(clock(back['departure_local_datetime'][11:16])-clock(h['checkout_by'])) if back else ''
        wait = str(clock(h['checkin_from'])-clock(f['arrival_local_datetime'][11:16])) if p['stay_basis'].startswith('BOOK_AIRPORT') else ''
        equal('CONDITIONAL_CLOCKS', [p['conditional_return_ground_plus_airport_buffer_budget_minutes'], p['conditional_airport_arrival_to_regular_checkin_clock_gap_minutes']], [budget, wait], p['product_request_id'])
        equal('UNKNOWN_GATES', [p[k] for k in ['hotel_min_stay_gate', 'hotel_admission_gate', 'inventory_gate', 'full_product_gate', 'operating_carrier_actual']], ['UNKNOWN']*5)
        equal('NO_IMPUTED_MONEY', [p[k] for k in ['total_stay_price', 'airfare_quote', 'realised_airline_revenue', 'transfer_duration_minutes']], ['']*4)
        equal('PROPERTY_ZONE_NOT_FILLED', p['property_iana'], h['timezone_iana'])
        oracle.append(dict(outbound_date=f['departure_local_date'], airport_arrival_date=f['arrival_local_date'], property_id=h['property_id'], stay_basis=p['stay_basis'], nights=int(p['hotel_nights']), booked_checkin_date=start.isoformat(), checkout_date=end.isoformat(), return_rule=gate, full_product='UNKNOWN', value_status='SCENARIO'))
    ground = rows(ALT, AR + 'ground_transfer/transfer_schedule.csv')
    gj = rows(HYP, HR + CR + 'ground_date_join.csv')
    equal('GROUND_NO_DATE_FILL', {r['date_coverage'] for r in gj}, {'UNKNOWN_DATE_COVERAGE'})
    equal('GROUND_DATES_AUDITED', {r['airport_arrival_date'] for r in gj}, {'2026-12-08', '2026-12-11'})
    # Verify date coverage from the full schedule, independently of author aggregate joins.
    date_col = 'service_date'
    ground_dates = Counter(r[date_col] for r in ground)
    equal('MISSING_ACTUAL_ARRIVAL_DATES', any(d in ground_dates for d in ['2026-12-08', '2026-12-11']), False)

    legs = rows(HYP, HR + 'runs/c26661067277af20/physical_legs.csv')
    deltas = rows(HYP, HR + MR + 'matched_resource_deltas.csv')
    for r in deltas:
        if r['candidate'] == 'C01':
            a = sorted([x for x in legs if x['variant']=='C01_unsync' and x['tail']==r['resource'] and '_2026-12-07_' in x['leg_id']], key=lambda x:x['departure_utc'])
            b = sorted([x for x in legs if x['variant']=='C01_sync' and x['tail']==r['resource'] and '_2026-12-07_' in x['leg_id']], key=lambda x:x['departure_utc'])
        else:
            a = sorted([x for x in legs if x['variant']=='C07_reference'], key=lambda x:x['departure_utc'])
            b = sorted([x for x in legs if x['variant']==r['candidate_program']], key=lambda x:x['departure_utc'])
        actual = [int(r[k]) for k in ['delta_block_minutes','delta_elapsed_minutes','first_departure_shift_minutes','return_shift_minutes','physical_flight_count_delta']]
        expected = [sum(int(x['block_minutes']) for x in b)-sum(int(x['block_minutes']) for x in a), elapsed(b[-1]['arrival_utc'], b[0]['departure_utc'])-elapsed(a[-1]['arrival_utc'], a[0]['departure_utc']), elapsed(b[0]['departure_utc'],a[0]['departure_utc']),elapsed(b[-1]['arrival_utc'],a[-1]['arrival_utc']),len(b)-len(a)]
        equal('RESOURCE_DELTAS', actual, expected, r['resource']+r['candidate_program'])
    definitions = {r['candidate']:r for r in rows(HYP, HR + MR + 'money_product_definitions.csv')}
    money = rows(HYP, HR + MR + 'conditional_thresholds_with_product_keys.csv')
    prior = rows(HYP, HR + 'runs/c26661067277af20/conditional_thresholds.csv')
    equal('MONEY_ROW_COUNT', len(money), len(prior))
    equal('MONEY_EXPECTED_COUNT', len(money), 108)
    for r, old in zip(money, prior):
        equal('PRIOR_NUMERICS_UNCHANGED', {k:r[k] for k in old}, old)
        p = definitions[r['candidate']]
        path_legs = len(p['outward_leg_sequence'].split(';'))
        equal('EXPLICIT_PATH_LENGTH', int(p['legs_per_oneway_journey']), path_legs)
        equal('MONEY_CONSERVATION', int(r['physical_boardings']), int(r['total_oneway_journeys'])*path_legs)
        equal('PRODUCT_KEYS', {k:r[k] for k in p}, p)
    tariffs = rows(HYP, HR + 'inputs/core/airport_cost_selected_verified.csv')
    coeff = rows(HYP, HR + MR + 'conditional_tariff_coefficients.csv')
    for c in coeff:
        rates = [r for r in tariffs if r['airport_iata']==c['airport'] and r['item'] in ['takeoff_landing','transport_security']]
        equal('TARIFF_COEFFICIENT', Fraction(c['reference_coefficient']), sum(Fraction(r['value']) for r in rates), c['airport'])
        equal('NO_INVOICE', c['paid_budget_rub'], '')
    result = dict(alternative_sha=ALT, hypotheses_sha=HYP, input_set_id=m['input_set_id'], raw_source_sha256=digest(data), source_rules_checked=len(source_cells), dated_instances_checked=len(flights), hotel_variants_checked=len(products), return_calendar_matches=sum(r['calendar_gate']=='RETURN_RULE_PRESENT' for r in products), matched_return_by_booked_date_assumption=dict(Counter(r['stay_basis'] for r in products if r['calendar_gate']=='RETURN_RULE_PRESENT')), ground_schedule_rows=len(ground), ground_date_counts=dict(ground_dates), resource_deltas_checked=len(deltas), money_rows_checked=len(money), old_run_preserved=True, differences=differences, arithmetic_acceptance='PASS_SCOPED' if not differences else 'CHANGES', calendar_acceptance='PUBLISHED_RULE_AND_EXPLICIT_HOTEL_DATE_SCENARIOS_ONLY', market_acceptance='NOT_ACCEPTED_NO_LABELS', full_product_acceptance='UNKNOWN', operational_acceptance='UNKNOWN_OPERATOR_STOPS_TAIL_DONOR_RESOURCE', conditional_economics='NO_ACTUAL_COST_OR_REALIZED_YIELD; CONSTANT_GAP_THRESHOLDS_ONLY')
    (OUT/'input_manifest.json').write_text(json.dumps(dict(inputs=receipts, raw_source=dict(path='raw/input_set002/airport_timetable.bin',sha256=digest(data),bytes=len(data),storage='LOCAL_IGNORED')),indent=2)+'\n')
    (OUT/'source_cells.json').write_text(json.dumps(source_cells,ensure_ascii=False,indent=2)+'\n')
    (OUT/'reproduction.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n')
    with (OUT/'hotel_calendar_oracle.csv').open('w',newline='') as h:
        w=csv.DictWriter(h,fieldnames=list(oracle[0]));w.writeheader();w.writerows(oracle)
    print(json.dumps(result,ensure_ascii=False,default=str))
    assert not differences

if __name__ == '__main__':
    main()
