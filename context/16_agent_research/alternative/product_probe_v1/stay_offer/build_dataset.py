#!/usr/bin/env python3
"""Rebuild compact factual tables and calendar candidates from pinned observations.

Standard library only. Does not infer stock, minimum stay, medical eligibility,
number of billable bed-days, itinerary quotes, demand, or realised revenue.
"""
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
PINNED_RECEIPTS = ('20261109T141704Z.json', '20261109T141915Z.json')

def dump_csv(name, rows):
    with (BASE / name).open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build():
    receipts = [json.loads((BASE / 'receipts' / name).read_text()) for name in PINNED_RECEIPTS]
    sources = {row['source_id']: row for receipt in receipts for row in receipt['sources']}
    offers = [
        dict(offer_id='C14-STAY-MET-CLASSIC-2026', property_id='METALLURG_ESSENTUKI',
             property_name='Санаторий Металлург', city='Ессентуки', program='Классическая',
             treatment_vs_leisure='TREATMENT_PROGRAM', room='Корпус 1; первая категория; двухместный',
             selected_occupancy='2 adults sharing; price per adult', currency='RUB',
             tariff_amount_per_person=7760, price_unit='PERSON_BED_DAY', solo_in_same_room_per_day=9940,
             valid_from='2026-11-01', valid_through='2026-12-31',
             price_kind='PUBLIC_TARIFF_NOT_DATE_QUOTE', date_inventory='UNKNOWN',
             all_in_itinerary_price='UNKNOWN', billing_days_for_requested_nights='UNKNOWN',
             inclusions='room; three diet meals daily; treatment within selected programme',
             exclusions='extra services outside programme; early/late occupancy may cost extra',
             tax_status='M05 states tourist-tax amount100RUB per bed-day appears on invoice; inclusion in M02 tariff UNKNOWN',
             medical_gate='doctor-assigned programme; required sanatorium medical card per M03',
             source_ids='M02;M03;M04;M05', tariff_locator='M02 p1; building1 double and solo rows; last date column',
             tariff_raw_sha256=sources['M02']['raw_sha256'], observed_at_utc=sources['M02']['observed_at_utc']),
        dict(offer_id='C14-STAY-CS-WELLNESS-2026', property_id='CENTROSOUZ_KISLOVODSK',
             property_name='Санаторий Центросоюз-Кисловодск', city='Кисловодск', program='Оздоровление и отдых; полный пансион',
             treatment_vs_leisure='WELLNESS_WITH_LIMITED_MEDICAL_SERVICES', room='Двухместный стандарт; лечебный корпус',
             selected_occupancy='2 adults sharing; price per adult', currency='RUB',
             tariff_amount_per_person=7400, price_unit='PERSON_DAY', solo_in_same_room_per_day=12200,
             valid_from='2026-11-24', valid_through='2026-12-26',
             price_kind='PUBLIC_TARIFF_NOT_DATE_QUOTE', date_inventory='UNKNOWN',
             all_in_itinerary_price='UNKNOWN', billing_days_for_requested_nights='UNKNOWN',
             inclusions='room; three buffet meals; pool; gym; mineral water and terrenkur; therapist consultation in C02',
             exclusions='other investigations or treatments paid separately; early/late occupancy may cost extra',
             tax_status='UNKNOWN', medical_gate='limited wellness list; not equivalent to full treatment course',
             source_ids='C01;C02;C03;C04;C05;C06', tariff_locator='C05 p1; medical-building double-standard row; final two occupancy columns; C01 confirms occupancy text',
             tariff_raw_sha256=sources['C05']['raw_sha256'], observed_at_utc=sources['C05']['observed_at_utc'])
    ]
    rules = [
        dict(property_id='METALLURG_ESSENTUKI', checkin_from='12:00', checkout_by='10:00',
             clock_scope='PROPERTY_PUBLISHED_CLOCK', timezone_iana='UNKNOWN_IN_THIS_DATASET',
             minimum_stay='UNKNOWN', minimum_unit='UNKNOWN',
             minimum_evidence='not stated in captured primary price/rules/room sources; no inference from third parties',
             stay7n_allowed='UNKNOWN', stay10n_allowed='UNKNOWN', stay14n_allowed='UNKNOWN',
             early_late_rule='up to2h free if room unbooked;2–12h half day;over12h full day; availability required',
             late_arrival_rule='missed hours not refunded; booked category may be lost after missed arrival',
             rules_valid_until='UNKNOWN', source_ids='M02;M03', locator='M02 p1 footnote; M03 section2 and registration terms',
             observed_at_utc=sources['M03']['observed_at_utc']),
        dict(property_id='CENTROSOUZ_KISLOVODSK', checkin_from='14:00', checkout_by='12:00',
             clock_scope='PROPERTY_PUBLISHED_CLOCK', timezone_iana='UNKNOWN_IN_THIS_DATASET',
             minimum_stay='UNKNOWN', minimum_unit='UNKNOWN',
             minimum_evidence='not stated in captured primary wellness tariff/programme/service-list/rules sources',
             stay7n_allowed='UNKNOWN', stay10n_allowed='UNKNOWN', stay14n_allowed='UNKNOWN',
             early_late_rule='early stay up to12h: no more than half day; late checkout refers to provider rules; inventory UNKNOWN',
             late_arrival_rule='provider may decline contract if guest arrives next day after booked arrival',
             rules_valid_until='UNKNOWN', source_ids='C03', locator='C03 p2 clauses8–11',
             observed_at_utc=sources['C03']['observed_at_utc'])
    ]
    dump_csv('public_offers.csv', offers)
    dump_csv('stay_rules.csv', rules)
    candidates = []
    for offer in offers:
        rule = next(r for r in rules if r['property_id'] == offer['property_id'])
        for start in range(7, 14):
            checkin = dt.date(2026, 12, start)
            for nights in (7, 10, 14):
                checkout = checkin + dt.timedelta(days=nights)
                last_night = checkout - dt.timedelta(days=1)
                candidates.append(dict(
                    candidate_id=f"{offer['offer_id']}-{checkin.isoformat()}-{nights}N",
                    offer_id=offer['offer_id'], property_id=offer['property_id'],
                    assumed_property_checkin_date=checkin.isoformat(), nights=nights,
                    property_checkout_date=checkout.isoformat(), last_occupied_night=last_night.isoformat(),
                    checkin_from=rule['checkin_from'], checkout_by=rule['checkout_by'],
                    arrival_flight_to_property_connection='UNKNOWN', departure_property_to_flight_connection='UNKNOWN',
                    checkout_not_after_2026_12_27=str(checkout <= dt.date(2026, 12, 27)).upper(),
                    occupied_nights_inside_tariff_period=str(checkin.isoformat() >= offer['valid_from'] and last_night.isoformat() <= offer['valid_through']).upper(),
                    checkout_inside_tariff_period=str(checkout.isoformat() <= offer['valid_through']).upper(),
                    billing_day_count='UNKNOWN', minimum_stay_eligibility='UNKNOWN', date_inventory='UNKNOWN',
                    product_status='CALENDAR_CANDIDATE_ONLY', priced_available_itinerary='UNKNOWN'))
    dump_csv('stay_calendar_candidates.csv', candidates)
    safe = {
        'method': 'Manually transcribed factual fields, not full-text source copies; tariff rows visually checked against PDF',
        'facts': [
            {'source_id':'M02', 'locator':'p1 building1 double row; last period; footnote', 'fields':{'rate_rub_person_bed_day':7760,'solo_rub_person_bed_day':9940,'from':'2026-11-01','through':'2026-12-31','checkin':'12:00','checkout':'10:00'}},
            {'source_id':'M04', 'locator':'room-page FAQ: included services', 'fields':{'included':['room','three diet meals','selected treatment programme']}},
            {'source_id':'C05', 'locator':'p1 medical-building double standard; last period; occupancy pictograms', 'fields':{'rate_rub_person_day_double':7400,'solo_rub_person_day':12200,'from':'2026-11-24','through':'2026-12-26','meal_plan':'three meals'}},
            {'source_id':'C01', 'locator':'full-board table heading', 'fields':{'html_winter_start':'2026-11-23','pdf_winter_start':'2026-11-24','disagreement_impact':'none for December7–27 calendar; source inconsistency preserved'}},
            {'source_id':'C03', 'locator':'p2 clause9', 'fields':{'checkin':'14:00','checkout':'12:00'}},
            {'source_id':'C04', 'locator':'p1 final note', 'fields':{'other_investigations_and_treatments':'paid separately'}}
        ]
    }
    (BASE / 'safe_factual_extracts.json').write_text(json.dumps(safe,ensure_ascii=False,indent=2)+'\n')
    source_rows=[]
    for source in sources.values():
        source_rows.append({k:source.get(k,'UNKNOWN') for k in ['source_id','url','publisher','role','coverage','observed_at_utc','http_status','bytes','raw_sha256','access_status','redistribution_license','raw_retention']})
    dump_csv('source_index.csv', source_rows)
    assert len(offers)==2 and len(rules)==2 and len(candidates)==42
    assert all(x['date_inventory']=='UNKNOWN' for x in offers+candidates)
    assert all(x['checkout_not_after_2026_12_27']=='TRUE' for x in candidates)
    ignored = {'dataset_manifest.json','raw_hold','__pycache__'}
    paths = sorted(path for path in BASE.rglob('*') if path.is_file() and not any(part in ignored for part in path.relative_to(BASE).parts))
    manifest={
        'dataset_id':'C14_stay_offer_product_probe_v1', 'case':'C14 Kirov–Mineralnye Vody sanatorium product',
        'search_date_utc':'2026-11-09', 'collection_first_utc':min(s['observed_at_utc'] for s in sources.values()),
        'pinned_receipts':list(PINNED_RECEIPTS),
        'collection_last_utc':max(s['observed_at_utc'] for s in sources.values()),
        'source_count':len(sources), 'offer_count':len(offers), 'stay_rule_count':len(rules), 'calendar_candidate_count':len(candidates),
        'grain':{'public_offers.csv':'one selected provider tariff/programme/room/occupancy row with alternative solo rate',
                 'stay_rules.csv':'one provider rule set observed at collection time',
                 'stay_calendar_candidates.csv':'offer x hypothetical property checkin date x requested nights; no flight join'},
        'scope':{'property_checkin_window':['2026-12-07','2026-12-13'],'nights':[7,10,14],'checkout_deadline':'2026-12-27'},
        'acceptance':{'public_primary_tariffs':'OBSERVED','checkin_checkout':'OBSERVED','minimum_stay':'UNKNOWN',
                      'date_inventory':'UNKNOWN','priced_available_itinerary':'UNKNOWN','medical_eligibility':'UNKNOWN',
                      'flight_and_transfer_join':'NOT_PERFORMED_HERE','realised_airline_revenue':'NOT_MEASURED'},
        'rights':{'source_licence':'UNKNOWN','raw':'HELD_NOT_PUBLISHED; ignored; exact SHA in receipts',
                  'published_content':'factual structured extracts and source metadata only','individual_contacts':'not extracted'},
        'reproduction':['python3 build_dataset.py','python3 collect_sources.py verify'],
        'fresh_collection':'python3 collect_sources.py collect; new receipt does not update the pinned dataset automatically',
        'collection_dependencies':'Python standard library only; optional PDF QA used preinstalled Poppler',
        'files':[{'path':str(path.relative_to(BASE)), 'sha256':digest(path), 'bytes':path.stat().st_size} for path in paths]
    }
    (BASE / 'dataset_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print('Built',len(offers),'tariffs;',len(rules),'rules;',len(candidates),'calendar candidates; minimum and inventory UNKNOWN')

if __name__ == '__main__':
    build()
