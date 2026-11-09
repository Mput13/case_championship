#!/usr/bin/env python3
"""Reconcile new conditional hotel/date/deadline pass without promoting availability."""
import argparse
import csv
import datetime as dt
import io
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import review_input_set002 as c

SHA='f92f21e143c923c79656e15776e6f66732f70f50'
ROOT=c.AR
OUT=c.BASE/'reviews'/'alternative_f92'

class Text(HTMLParser):
    def __init__(self):
        super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ['script','style']:self.skip+=1
    def handle_endtag(self,tag):
        if tag in ['script','style']:self.skip=max(0,self.skip-1)
    def handle_data(self,s):
        if not self.skip:self.parts.append(s)

def get(path):return c.capture(SHA,ROOT+path)
def rows(path):return list(csv.DictReader(io.StringIO(get(path).decode())))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--air-policy-raw-root',type=Path)
    args=ap.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    b=get('dataset_manifest.json');manifest=json.loads(b)
    c.equal('DATASET_MANIFEST',c.digest(b),'1261733dd625f0e5d569ea85fa5460132d1bf4b98cec648fffe61561f760aaac')
    for r in manifest['public_files']:
        data=get(r['path']);c.equal('PUBLIC_FILE_HASH',c.digest(data),r['sha256'],r['path'])
        c.equal('PUBLIC_FILE_SIZE',len(data),r['size_bytes'],r['path'])
    frozen=json.loads(get('frozen_product_inputs.json'))
    for r in frozen['files']:
        data=get(r['path']);c.equal('PRODUCT_INPUT_HASH',c.digest(data),r['sha256'],r['path'])
        if not r['path'].startswith('air_offer/'):
            c.equal('BASE_FA39_UNCHANGED',data,c.capture(c.ALT,ROOT+r['path']),r['path'])
    c.equal('OLD_FLIGHT_CHECKPOINT_UNCHANGED',c.digest(get('flight_checkpoint_manifest.json')),'7d589e1492688aa29aa8396b7f3e3be64f2674fe98521cba6825a4d02364aaa6')
    policies=json.loads(get('air_offer/source_manifest.json'))
    checked_raw=[]
    for source_id in ['carriage_20261109','registration_20261109','availability_07_14_dec2026']:
        receipt=next(r for r in policies['sources']if r['snapshot_id']==source_id)
        target=c.BASE/'raw'/'alternative_f92_policy'/Path(receipt['raw_path']).name
        if args.air_policy_raw_root:
            data=(args.air_policy_raw_root/receipt['raw_path']).read_bytes()
            assert c.digest(data)==receipt['stored_sha256']
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        data=target.read_bytes()
        c.equal('STORED_POLICY_HASH',c.digest(data),receipt['stored_sha256'],source_id)
        c.equal('STORED_POLICY_BYTES',len(data),receipt['stored_size_bytes'],source_id)
        # The source bytes were sanitized by their collector. We verify stored
        # bytes, retaining original hash as receipt-only, not claiming a replay
        # of unavailable original credentials or printing them.
        checked_raw.append(dict(source_id=source_id,stored_sha256=c.digest(data),stored_bytes=len(data),original_source_sha256=receipt['source_sha256'],original_bytes_verified_by_this_review=(receipt['source_sha256']==receipt['stored_sha256']),storage='LOCAL_IGNORED'))
        if source_id=='carriage_20261109':
            p=Text();p.feed(data.decode());text=' '.join(' '.join(p.parts).split())
            c.equal('GENERAL40_PRIMARY',bool(re.search(r'заканчивается за 40 минут.*?если иное не предусмотрено для отдельных направлений',text)),True)
    flights={r['instance_id']:r for r in rows('normalized/dated_flights.csv')}
    hotels={r['property_id']:r for r in rows('stay_offer/stay_rules.csv')}
    buffers=rows('air_offer/airport_buffers.csv')
    close=next(r for r in buffers if r['buffer_id']=='CHECKIN_CLOSE')
    c.equal('GENERAL_POLICY_NOT_SPECIFIC',[close['minutes_before_scheduled_departure'],close['policy_scope'],close['specific_flight_confirmation']],['40','GENERAL_CARRIER_RULE','UNCONFIRMED'])
    data=rows('normalized/conditional_stay_calendars.csv')
    c.equal('GRID_COUNT',len(data),24)
    c.equal('UNIQUE_CASES',len({r['product_case_id']for r in data}),24)
    oracle=[]
    for r in data:
        outbound=flights[r['outbound_instance_id']];hotel=hotels[r['property_id']]
        arrival=c.timestamp(outbound['arrival_local_datetime']);departure=c.timestamp(outbound['departure_local_datetime'])
        start=departure.date()if r['reservation_date_anchor'].startswith('DEPARTURE')else arrival.date()
        end=start+dt.timedelta(days=int(r['assumed_nights']))
        c.equal('ASSUMED_DATES',[r['assumed_reservation_start_date'],r['assumed_checkout_date']],[start.isoformat(),end.isoformat()],r['product_case_id'])
        c.equal('BOOKED_DATES_NULL',[r['actual_booked_checkin_date'],r['actual_booked_checkout_date'],r['booking_status']],['','','UNKNOWN'])
        midnight=dt.datetime.combine(start+dt.timedelta(days=1),dt.time(0),tzinfo=arrival.tzinfo)
        opening=dt.datetime.combine(start,dt.time.fromisoformat(hotel['checkin_from']),tzinfo=arrival.tzinfo)
        preservation=int((midnight-arrival).total_seconds()/60)
        opening_gap=int((opening-arrival).total_seconds()/60)
        c.equal('STRICT_DATE_BOUND',int(r['max_exit_wait_transfer_minutes_to_preserve_assumed_checkin_date_exclusive']),preservation,r['product_case_id'])
        c.equal('OPENING_NOT_DEADLINE',int(r['minutes_from_airport_arrival_to_checkin_opening']),opening_gap,r['product_case_id'])
        c.equal('LATE_ADMISSION_REQUIRED',r['late_next_day_acceptance_required'],str(arrival.date()>start))
        returns=[f for f in flights.values()if f['origin_iata']=='MRV'and f['departure_local_date']==end.isoformat()]
        c.equal('CALENDAR_RETURN',r['captured_return_rule_same_checkout_date'],str(bool(returns)),r['product_case_id'])
        budget=None;net=None
        if returns:
            back=returns[0];checkout=dt.datetime.combine(end,dt.time.fromisoformat(hotel['checkout_by']),tzinfo=arrival.tzinfo)
            budget=int((c.timestamp(back['departure_local_datetime'])-checkout).total_seconds()/60)
            net=budget-40
            c.equal('RETURN_ID',r['return_instance_id'],back['instance_id'])
        c.equal('RETURN_TOTAL_BUDGET',r['max_property_exit_transfer_airport_buffer_minutes'],str(budget)if budget is not None else'',r['product_case_id'])
        c.equal('RETURN_MINUS_GENERAL_CLOSE',r['max_exit_wait_transfer_queue_minutes_before_general_checkin_close'],str(net)if net is not None else'',r['product_case_id'])
        c.equal('NO_AVAILABILITY_OR_PRICE_FILL',[r[k]for k in ['airport_to_property_total_minutes','billable_day_count','confirmed_stay_total_rub','dated_air_fare_quote_rub','boarding_cutoff_minutes']],['']*5)
        c.equal('PRODUCT_STILL_UNKNOWN',r['product_availability'],'UNKNOWN')
        oracle.append(dict(case_id=r['product_case_id'],booked_dates='UNKNOWN',assumed_start=start.isoformat(),assumed_checkout=end.isoformat(),strict_preservation_bound_minutes=preservation,opening_clock_gap_minutes=opening_gap,return_rule=bool(returns),conditional_total_budget_minutes=budget,conditional_after_general40_minutes=net,value_status='SCENARIO',full_product='UNKNOWN'))
    fares=rows('air_offer/fare_observations.csv')
    failed=next(r for r in fares if r['observation_type']=='DATED_OFFER_QUERY')
    c.equal('403_NOT_ZERO_OFFER',[failed['http_status'],failed['price_status'],failed['gross_price'],failed['availability_status']],['403','UNKNOWN','','UNKNOWN_ACCESS_BLOCKED'])
    advert=next(r for r in fares if r['observation_type']=='ADVERTISED_FARE_NOT_DATE_QUOTE')
    c.equal('TEASER_NOT_DATED_QUOTE',advert['gross_price'],'')
    result=dict(input_git_sha=SHA,base_flight_commit=c.ALT,manifest_public_files_checked=len(manifest['public_files']),frozen_product_files=len(frozen['files']),conditional_cases=len(data),calendar_return_matches=sum(r['captured_return_rule_same_checkout_date']=='True'for r in data),strict_date_bounds=sorted({r['strict_preservation_bound_minutes']for r in oracle}),after_general40_budgets=sorted({r['conditional_after_general40_minutes']for r in oracle if r['conditional_after_general40_minutes']is not None}),actual_booked_dates_known=0,exact_transfer_durations_known=0,primary_general40_scope='PUBLISHED_GENERAL_RULE_WITH_EXCEPTIONS; MRV_SPECIFIC_UNCONFIRMED',fare_status='ONE403_QUERY_NOT_PRICE_OR_ZERO_DEMAND; TEASER_NOT_DECQUOTE',differences=c.differences,acceptance='PASS_CONDITIONAL_DATE_AND_TIME_ARITHMETIC_ONLY'if not c.differences else'CHANGES',hotel_timezone='CURATED_ASSUMPTION_IN_THIS_VERSION; not independently verified hotel IANA',full_product='UNKNOWN',market_yield='NOT_ACCEPTED',old_inputs='fa39/frozen001/frozen002 retained separately')
    (OUT/'input_manifest.json').write_text(json.dumps(dict(inputs=c.receipts,policy_stored_raw=checked_raw),indent=2)+'\n')
    (OUT/'reproduction.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n')
    with(OUT/'conditional_budget_oracle.csv').open('w',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(oracle[0]));w.writeheader();w.writerows(oracle)
    print(json.dumps(result,ensure_ascii=False,default=str));assert not c.differences

if __name__=='__main__':main()
