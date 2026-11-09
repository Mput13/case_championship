#!/usr/bin/env python3
"""Replay manually selected source claims; never infer OD from reported traffic.

Each number must occur literally in exact-class main message text. Units and
qualifiers retain publisher precision. Published plans are separately identified.
"""
import csv
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
# id, metric, entity, start, end, number, literal, unit, qualifier, observation kind
CLAIMS=[
 ('4262','carrier_passengers','RU_CARRIERS','2025-01-01','2025-05-31','40.4','40,4','million passenger segments','almost','REPORTED_OUTTURN'),
 ('4262','carrier_passenger_km','RU_CARRIERS','2025-01-01','2025-05-31','105.6','105,6','billion passenger km','','REPORTED_OUTTURN'),
 ('4262','carrier_seat_load_factor','RU_CARRIERS','2025-01-01','2025-05-31','88.4','88,4','percent','','REPORTED_OUTTURN'),
 ('4262','carrier_passengers','RU_CARRIERS','2025-05-01','2025-05-31','9.2','9,2','million passenger segments','','REPORTED_OUTTURN'),
 ('4883','airport_passenger_movements','RU_AIRPORTS','2025-01-01','2025-08-31','144.6','144,6','million passenger movements','','REPORTED_OUTTURN'),
 ('4883','carrier_passengers','RU_CARRIERS','2025-01-01','2025-08-31','73.7','73,7','million passenger segments','','REPORTED_OUTTURN'),
 ('4883','international_airport_passenger_movements','RU_AIRPORTS','2025-01-01','2025-08-31','33.6','33,6','million passenger movements','','REPORTED_OUTTURN'),
 ('4883','international_carrier_passengers','RU_CARRIERS','2025-01-01','2025-08-31','17.9','17,9','million passenger segments','','REPORTED_OUTTURN'),
 ('5665','domestic_carrier_passengers','RU_CARRIERS','2025-01-01','2025-12-31','81.45','81,45','million passenger segments','','REPORTED_OUTTURN'),
 ('5665','international_carrier_passengers','RU_CARRIERS','2025-01-01','2025-12-31','27.40','27,40','million passenger segments','','REPORTED_OUTTURN'),
 ('5665','airport_passenger_movements','RU_AIRPORTS','2025-01-01','2025-12-31','214.66','214,66','million passenger movements','','REPORTED_OUTTURN'),
 ('5665','top5_carrier_passengers','RU_TOP5_NAMED_CARRIERS','2025-01-01','2025-12-31','76.57','76,57','million passenger segments','','REPORTED_OUTTURN'),
 ('5665','top5_carrier_reported_share','RU_TOP5_NAMED_CARRIERS','2025-01-01','2025-12-31','70.3','70,3','percent of reported carrier traffic','','REPORTED_OUTTURN'),
 ('5907','airport_passenger_movements','IATA:TOF','2025-01-01','2025-12-31','627','627','thousand passenger movements','','REPORTED_OUTTURN'),
 ('5907','subsidized_passengers_reported','IATA:TOF','2025-01-01','2025-12-31','87.7','87,7','thousand reported passengers','Program scope not specified','REPORTED_OUTTURN'),
 ('5907','subsidized_passengers_planned','IATA:TOF','2026-01-01','2026-12-31','97','97','thousand planned passengers','more than','PUBLISHED_PLAN_NOT_OUTTURN'),
 ('6702','airport_passenger_movements','IATA:SVX','2026-01-01','2026-06-30','3.84','3,84','million passenger movements','','REPORTED_OUTTURN'),
 ('6948','airport_passenger_movements','IATA:ASF','2025-01-01','2025-12-31','784','784','thousand passenger movements','more than','REPORTED_OUTTURN'),
 ('6948','subsidized_passengers_reported','REGION:ASTRAKHAN','2025-01-01','2025-12-31','49.5','49,5','thousand reported passengers','5 routes, unspecified program','REPORTED_OUTTURN'),
 ('7151','carrier_passengers','RU_CARRIERS','2026-05-01','2026-08-31','39.5','39,5','million passenger segments','','REPORTED_OUTTURN'),
 ('7151','airport_passenger_movements','RU_AIRPORTS','2026-05-01','2026-08-31','79.7','79,7','million passenger movements','','REPORTED_OUTTURN'),
 ('7151','domestic_airport_passenger_movements','RU_AIRPORTS','2026-05-01','2026-08-31','59.2','59,2','million passenger movements','','REPORTED_OUTTURN'),
 ('7151','international_airport_passenger_movements','RU_AIRPORTS','2026-05-01','2026-08-31','20.5','20,5','million passenger movements','','REPORTED_OUTTURN'),
 ('7151','allocated_subsidy_budget','RU_THREE_PROGRAMS','2026-01-01','2026-12-31','22.9','22,9','billion RUB','Allocated, not disbursed; publication context2026','PUBLISHED_ALLOCATION_NOT_PAYMENT'),
]
def main():
    posts=list(csv.DictReader((ROOT/'normalized/telegram_main_favt_ru.csv').open()))
    by_id={}
    for p in posts:
        old=by_id.setdefault(p['message_id'],p)
        if old['main_text']!=p['main_text']:raise ValueError('Edited main text requires explicit version selection')
    rows=[]
    for id,metric,entity,start,end,value,literal,unit,qualifier,kind in CLAIMS:
        p=by_id[id]
        assert literal in p['main_text'] and p['text_status']=='MAIN_BODY_EXACT_CLASS'
        rows.append(dict(observation_id='favt_ru:'+id+':'+metric,entity_id=entity,metric=metric,
            period_start=start,period_end=end,value=value,unit=unit,qualifier=qualifier,
            value_status='OBSERVED',observation_kind=kind,source_id='favt_ru:'+id,
            published_at_utc=p['published_at_utc'],snapshot_at_utc=p['snapshot_at_utc'],
            source_url=p['source_url'],raw_path=p['raw_path'],literal_value=literal,
            validation_boundary='Manual main-text selection + literal check; official reported aggregate, not independent cell audit',
            limitations='Not unique persons or final OD; airport and carrier counts have different accounting; plans/budgets are not outturn/payments'))
    f=ROOT/'normalized/market_observation.csv'
    with f.open('w',newline='') as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print('market_observation',len(rows),'claims from',len({r['source_id'] for r in rows}),'messages')
if __name__=='__main__':main()
