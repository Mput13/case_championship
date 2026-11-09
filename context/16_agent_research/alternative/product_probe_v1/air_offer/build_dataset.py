#!/usr/bin/env python3
"""Rebuild compact factual air probe outputs from frozen public-source receipts."""
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def write_csv(name, rows):
    with (ROOT / name).open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(name, obj):
    (ROOT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def main():
    receipts = {p.stem: json.loads(p.read_text()) for p in sorted((ROOT / 'receipts').glob('*.json'))}
    fare = receipts['fares_20261109']
    availability = receipts['availability_07_14_dec2026']
    write_csv('fare_observations.csv', [
        {'observation_id': 'AIR01', 'observation_type': 'DATED_OFFER_QUERY', 'carrier': 'Azimuth',
         'origin': 'KVX', 'destination': 'MRV', 'outbound_date': '2026-12-07', 'return_date': '2026-12-14',
         'adult_count': 1, 'search_utc': availability['retrieved_at_utc'], 'gross_price': '', 'currency': 'UNKNOWN',
         'price_status': 'UNKNOWN', 'availability_status': 'UNKNOWN_ACCESS_BLOCKED', 'fare_brand': 'UNKNOWN',
         'checked_baggage': 'UNKNOWN', 'cabin_baggage': 'UNKNOWN', 'refund': 'UNKNOWN', 'change': 'UNKNOWN',
         'source_id': availability['snapshot_id'], 'source_url': availability['source_url'],
         'http_status': availability['http_status'], 'detail': 'HTTP Error 403: Forbidden; generic nginx error body; no offer response'},
        {'observation_id': 'AIR02', 'observation_type': 'ADVERTISED_FARE_NOT_DATE_QUOTE', 'carrier': 'Azimuth',
         'origin': 'KVX', 'destination': 'MRV', 'outbound_date': '', 'return_date': '', 'adult_count': '',
         'search_utc': fare['retrieved_at_utc'], 'gross_price': '', 'currency': 'RUB',
         'price_status': 'ADVERTISED_FROM_2688_RUB_ONLY', 'availability_status': 'UNKNOWN', 'fare_brand': 'UNKNOWN',
         'checked_baggage': 'UNKNOWN', 'cabin_baggage': 'UNKNOWN', 'refund': 'UNKNOWN', 'change': 'UNKNOWN',
         'source_id': fare['snapshot_id'], 'source_url': fare['source_url'], 'http_status': fare['http_status'],
         'detail': 'Official teaser from 2688 RUB; link targets 16.11.2026/1-0-0; no booking result obtained; not a December quote or revenue'}
    ])
    policies = [
        ('LT', 'Легкий', 'Economy', 1, 5, 0, '', 'NOT_PERMITTED', '', 'PERMITTED_WITH_FEE', 5000),
        ('FL', 'Гибкий', 'Economy', 1, 5, 1, 23, 'PERMITTED_WITH_FEE', 5000, 'PERMITTED_WITH_FEE', 5000),
        ('BS', 'Базовый', 'Comfort', 1, 10, 2, 23, 'PERMITTED_WITH_FEE', 5000, 'PERMITTED_WITH_FEE', 5000),
        ('FR', 'Свободный', 'Comfort', 1, 10, 2, 23, 'PERMITTED_WITHOUT_CARRIER_FEE', 0, 'PERMITTED_WITHOUT_CARRIER_FEE', 0),
    ]
    write_csv('fare_policy_rules.csv', [
        {'policy_id': 'POLICY_' + brand, 'carrier': 'Azimuth', 'brand_code': brand, 'brand_ru': name,
         'class': cls, 'cabin_pieces': cp, 'cabin_kg_per_piece': ck,
         'checked_pieces_included': bp, 'checked_kg_per_piece': bk,
         'refund_before_checkin_close': refund, 'refund_fee_from_rub': rf,
         'change_before_checkin_close': change, 'change_fee_from_rub': cf,
         'voluntary_refund_after_checkin_close': 'NOT_PERMITTED', 'voluntary_change_after_checkin_close': 'NOT_PERMITTED',
         'specific_offer_applicability': 'UNCONFIRMED', 'source_ids': 'fares_20261109;baggage_20261109',
         'source_url': fare['source_url'], 'retrieved_at_utc': fare['retrieved_at_utc'],
         'caveat': 'General brand policy; not a selected-offer fare rule; special subsidised non-brand fares may apply; amounts are from-values, not total exchange/refund cost'}
        for brand, name, cls, cp, ck, bp, bk, refund, rf, change, cf in policies
    ])
    write_csv('airport_buffers.csv', [
        {'buffer_id': 'CHECKIN_CLOSE', 'carrier': 'Azimuth', 'airport': 'MRV',
         'event': 'Airport passenger and baggage check-in closes', 'minutes_before_scheduled_departure': 40,
         'value_status': 'OBSERVED', 'policy_scope': 'GENERAL_CARRIER_RULE', 'specific_flight_confirmation': 'UNCONFIRMED',
         'source_id': 'carriage_20261109', 'source_url': receipts['carriage_20261109']['source_url'],
         'detail': 'General rule has exceptions for individual routes; current retrieved page does not establish an MRV-specific exception; minimum processing cutoff, not a recommended airport-arrival margin'},
        {'buffer_id': 'CHECKIN_OPEN', 'carrier': 'Azimuth', 'airport': 'MRV',
         'event': 'Airport check-in opens', 'minutes_before_scheduled_departure': 120,
         'value_status': 'OBSERVED', 'policy_scope': 'GENERAL_CARRIER_FAQ', 'specific_flight_confirmation': 'UNCONFIRMED',
         'source_id': 'registration_20261109', 'source_url': receipts['registration_20261109']['source_url'],
         'detail': 'FAQ says opens 2h before departure; carriage rules say begins no later than 2h before departure; this is opening time, not an airport-arrival recommendation'},
        {'buffer_id': 'BOARDING_CLOSE', 'carrier': 'Azimuth', 'airport': 'MRV',
         'event': 'Boarding gate arrival deadline', 'minutes_before_scheduled_departure': '',
         'value_status': 'UNKNOWN', 'policy_scope': 'DEADLINE_ON_BOARDING_PASS', 'specific_flight_confirmation': 'UNKNOWN',
         'source_id': 'carriage_20261109', 'source_url': receipts['carriage_20261109']['source_url'],
         'detail': 'Section 9.1 requires gate arrival by time printed on boarding pass; no universal numeric boarding-close buffer recovered; do not substitute 20min'}
    ])
    inherited = []
    for name in ['azimuth_bundle_20261109', 'azimuth_timetable_20261109', 'azimuth_timetable_results_js_20261109']:
        r = json.loads((ROOT.parent / 'receipts' / (name + '.json')).read_text())
        inherited.append({'source_id': name, 'source_url': r['source_url'], 'retrieved_at_utc': r['retrieved_at_utc'],
                          'sha256': r['sha256'], 'receipt_path': '../receipts/' + name + '.json',
                          'ownership': 'Root-acquired frozen source, read-only reuse', 'authorship': 'Official Azimuth booking frontend',
                          'use': 'Static source inspection only; fetched JavaScript was never executed'})
    write_json('client_query_contract.json', {
        'status': 'OBSERVED_IN_PUBLIC_CLIENT_NOT_PUBLISHED_API_CONTRACT',
        'source_id': 'azimuth_bundle_20261109', 'source_sha256': inherited[0]['sha256'],
        'rpc_url': 'https://booking.azimuth.ru/rpc/tsh', 'wire_format': 'JSON array of [method, parameters] pairs over POST',
        'availability_method': 'get-availability', 'availability_request_parameters': availability['request_parameters'],
        'timetable_method': 'get-air-schedule',
        'timetable_parameter_names': ['departure', 'arrival', 'min_dep_date', 'max_dep_date', 'show_prices'],
        'timetable_price_default': 'N', 'timetable_execution': 'NOT_RUN_AFTER_PUBLIC_RPC_HTTP403',
        'init_session_execution': 'NOT_RUN', 'fetched_js_execution': 'NOT_RUN',
        'credential_handling': 'No Cookie or Authorization supplied, recorded or reused; no browser/session state; response credential headers discarded',
        'mutation_methods_execution': 'NOT_RUN: create-order/select-offer/passenger data/hold/reservation/payment were outside scope',
        'barrier': '403 Forbidden before a usable application response; no causality claim about WAF, auth, or endpoint validity'
    })
    extracts = [
        {'fact_id': 'E01', 'source_id': 'fares_20261109', 'kind': 'PARAPHRASE',
         'fact': 'Economy LT includes 5kg cabin baggage, no checked bag, no voluntary refund; FL includes 5kg cabin baggage and one 23kg checked bag. LT/FL changes and FL refunds before check-in closes have fees from RUB5000. Special subsidised fares can sit outside brands.'},
        {'fact_id': 'E02', 'source_id': 'baggage_20261109', 'kind': 'PARAPHRASE',
         'fact': 'Cabin baggage limit is 55x40x20cm; included checked piece dimension total is at most203cm. Brand baggage allowances are general policy only.'},
        {'fact_id': 'E03', 'source_id': 'carriage_20261109', 'kind': 'PARAPHRASE',
         'fact': 'Section9 gives general airport passenger/baggage check-in closure40min before scheduled departure, with possible exceptions by route; section9.1 places boarding deadline on the boarding pass.'},
        {'fact_id': 'E04', 'source_id': 'registration_20261109', 'kind': 'PARAPHRASE',
         'fact': 'Carrier FAQ states airport check-in opens2h before departure and closes40min before departure.'},
        {'fact_id': 'E05', 'source_id': 'fares_20261109', 'kind': 'LIMITED_FACTUAL_AD_EXTRACT',
         'route': 'KVX-MRV', 'advertised_from_rub': 2688,
         'booking_link': 'https://booking.azimuth.ru/new/#/!/KVX/MRV/16.11.2026/1-0-0/?lang=ru',
         'classification': 'ADVERTISED_FARE_NOT_DATE_QUOTE', 'relevance_limit': 'Link date16Nov2026 differs from targetDecember dates; no availability or offer terms observed'},
        {'fact_id': 'E06', 'source_id': 'availability_07_14_dec2026', 'kind': 'ERROR_OBSERVATION',
         'http_status': 403, 'error': 'HTTPError: HTTP Error403: Forbidden', 'body_summary': 'Generic HTML403 Forbidden, nginx/1.31.2',
         'classification': 'UNKNOWN_ACCESS_BLOCKED', 'interpretation_limit': 'No inference of sold-out seats, zero demand, cancelled service, invalid method, auth requirement or unavailable fare'}
    ]
    write_json('safe_factual_extracts.json', {'extract_authorship': 'Independent C14 air-offer research agent; paraphrases and factual transcriptions',
                                            'source_authorship': 'АО «Авиакомпания АЗИМУТ» / official booking frontend', 'extracts': extracts})
    artifacts = {}
    for name in ['fare_observations.csv', 'fare_policy_rules.csv', 'airport_buffers.csv', 'client_query_contract.json', 'safe_factual_extracts.json']:
        b = (ROOT / name).read_bytes()
        artifacts[name] = {'sha256': hashlib.sha256(b).hexdigest(), 'size_bytes': len(b)}
    write_json('source_manifest.json', {
        'dataset_id': 'c14-air-offer-public-probe-v1', 'created_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'researcher': 'Independent C14 air-offer research agent', 'source_authorship': 'Official airline primary sources',
        'scope': 'KVX-MRV return itinerary,1adult,07-14Dec2026; general carrier policies separate from dated offers',
        'dated_offer_result': 'UNKNOWN_ACCESS_BLOCKED_HTTP403', 'successful_dated_price_quotes': 0,
        'not_run': ['10-21Dec2026 second scenario after same publicRPC barrier', 'get-air-schedule HTTP query', 'session initialization',
                    'browser execution', 'captcha/auth bypass', 'reservation/order/hold', 'passenger record', 'payment'],
        'local_raw_policy': 'Locally ignored raw_hold; no full carrier HTML/JS for public redistribution; credentials redacted before retained output; original source SHA and stored SHA separated',
        'public_extract_policy': 'Only factual extracts, URL, SHA, safe receipts and scripts; no contacts, auth values or absolute local paths',
        'sources': [dict(r, authorship='Official Azimuth source') for r in receipts.values()],
        'inherited_read_only_sources': inherited, 'artifacts': artifacts,
        'acceptance_limits': ['Access failure does not establish zero demand or no seats.', 'Advertised from2688RUB is not a target-date price.',
                              'General policy does not establish selected-offer brand, baggage, refund, exchange or gross price.',
                              'Observed fare or ad cannot establish yield or realised revenue.', 'No boarding-pass-specific deadline available.']
    })
    print('Built5 factual tables/contracts plus source_manifest.json from6 frozen publicHTTP receipts')


if __name__ == '__main__':
    main()
