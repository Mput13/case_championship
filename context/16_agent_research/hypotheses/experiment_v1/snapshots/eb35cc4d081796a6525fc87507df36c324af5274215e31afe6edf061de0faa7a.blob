#!/usr/bin/env python3
"""Date-only cost of accepting a later return within the frozen capture."""
from pathlib import Path
from datetime import date
import csv,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    product=ROOT/'c14_products/3906edd033f75bc6/flight_hotel_calendar.csv'
    flights=ROOT/'inputs/alternative_fa39de4/normalized/dated_flights.csv'
    source_rows=list(csv.DictReader(product.open()));return_rows=[r for r in csv.DictReader(flights.open()) if r['origin_iata']=='MRV']
    input_hashes={'product_csv':sha(product),'dated_flights':sha(flights),'script':sha(Path(__file__))};ident=hashlib.sha256(json.dumps(input_hashes,sort_keys=True).encode()).hexdigest()[:16]
    out=ROOT/'c14_calendar_flex'/ident;out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for r in source_rows:
        desired=date.fromisoformat(r['booked_checkout_local_date']);future=sorted([f for f in return_rows if date.fromisoformat(f['departure_local_date'])>=desired],key=lambda x:x['departure_utc'])
        chosen=future[0] if future else None;new_date=date.fromisoformat(chosen['departure_local_date']) if chosen else None
        extra=(new_date-desired).days if chosen else None
        rows.append(dict(product_request_id=r['product_request_id'],property_id=r['property_id'],stay_basis=r['stay_basis'],original_hotel_nights=r['hotel_nights'],original_checkout_local_date=desired.isoformat(),exact_return_gate=r['calendar_gate'],
            later_return_policy='SCENARIO_CUSTOMER_ACCEPTS_LATER_RETURN; not an observed preference',next_captured_return_id=chosen['instance_id'] if chosen else '',next_captured_return_date=new_date.isoformat() if chosen else '',
            additional_booked_nights=extra,revised_booked_nights=int(r['hotel_nights'])+extra if extra is not None else '',calendar_adjustment_gate='DATE_AVAILABLE_IN_CAPTURE_ONLY' if chosen else 'UNKNOWN_BEYOND_CAPTURE_HORIZON',
            hotel_extended_inventory='UNKNOWN',late_admission='UNKNOWN',extra_hotel_charge='UNKNOWN',extra_airfare='UNKNOWN',ground_compatibility='UNKNOWN',flight_inventory='UNKNOWN',customer_acceptance='UNKNOWN',full_product_acceptance='UNKNOWN'))
    p=out/'later_return_date_tradeoff.csv'
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    assert len(rows)==24
    assert all(r['additional_booked_nights']==0 for r in rows if r['exact_return_gate']=='RETURN_RULE_PRESENT')
    assert all(r['additional_booked_nights'] is None for r in rows if r['original_checkout_local_date']=='2026-12-25')
    summary={'module_run':ident,'rows':len(rows),'positive_extensions':sum(r['additional_booked_nights'] is not None and r['additional_booked_nights']>0 for r in rows),'extension_nights_present':sorted({r['additional_booked_nights'] for r in rows if r['additional_booked_nights'] is not None and r['additional_booked_nights']>0}),'beyond_capture_unknown':sum(r['additional_booked_nights'] is None for r in rows),'market_acceptance':'NONE','billing_days_not_assumed_equal_nights':True}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps({'inputs':input_hashes,'files':[{'path':p.name,'sha256':sha(p)} for p in sorted(out.iterdir()) if p.is_file() and p.name!='manifest.json']},indent=2)+'\n')
    print(json.dumps(summary))
if __name__=='__main__':main()
