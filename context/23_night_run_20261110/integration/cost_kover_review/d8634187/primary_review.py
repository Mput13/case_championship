#!/usr/bin/env python3
"""Verify pinned KHV raw files read-only; optional local page rendering.

The selected values below were personally read from complete page renders.
This script verifies their join to the frozen extract, not human comprehension.
No new download and no full raw copy is made.
"""
import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path
import review

OUT=Path(__file__).resolve().parent
OWNER=Path('/Users/a/.t3/worktrees/case_championship/t3-6b143a3b-f769e5714dcb4e77/context/23_night_run_20261110/cost_kover')
SOURCES={
    'khv_tariff_current':('khv_tariff_current.pdf','be2e98cdf0a53fecb7c25a2bbc75335da4dd5079daaedc46145de53b641ee7db'),
    'khv_tariff_202611':('khv_tariff_202611.pdf','e0a64e7a328f5eed24b91a287479d7027ed9515a96a03fbf968fcf6819cc2be9'),
}
SELECTED=[
    ('takeoff_landing','1.1.1',562,700,'RUB per tonne MTOW','2026-02-10'),
    ('transport_security','1.2.1',445,609,'RUB per tonne MTOW','2026-02-10'),
    ('conditional_takeoff_surcharge','1.1.1.1',40,40,'percent of applicable takeoff charge','2026-01-01'),
    ('temporary_parking_40_60t_day','1.4.3',25224,25224,'RUB per day','2026-01-01'),
    ('temporary_parking_40_60t_hour','1.5.3',1051,1051,'RUB per hour','2026-01-01'),
    ('basing_40_60t_month','1.6.3',133477,133477,'RUB per month','2026-01-01'),
    ('passenger_stairs','2.1',8700,9144,'RUB per stairs unit','2026-01-16'),
    ('passenger_bus_COBUS','2.2.1',4510,4740,'RUB per vehicle unit','2026-01-16'),
]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--render',action='store_true');args=parser.parse_args()
    extracts={(r['source_id'],r['component_id']):r for r in review.rows('inputs/khv_cost_components.csv')}
    selected=[];receipts=[];local=OUT/'.local';local.mkdir(exist_ok=True)
    for id,(name,expected_sha) in SOURCES.items():
        src=OWNER/'raw_hold'/name;data=src.read_bytes();sha=hashlib.sha256(data).hexdigest();assert sha==expected_sha
        receipt=dict(source_id=id,path=str(src),sha256=sha,bytes=len(data),raw_hash_verified_personally=True,
            source_url=next(r['source_url'] for k,r in extracts.items() if k[0]==id),
            full_raw_copied=False,full_raw_published=False,pages={})
        for page in [1,7]:
            target=local/(name[:-4]+'_page'+str(page));png=target.with_suffix('.png')
            if args.render:
                subprocess.run(['pdftoppm','-f',str(page),'-l',str(page),'-scale-to','2100','-singlefile','-png',str(src),str(target)],check=True,capture_output=True)
                text=subprocess.check_output(['pdftotext','-f',str(page),'-l',str(page),'-layout',str(src),'-'])
                target.with_suffix('.txt').write_bytes(text)
            meta=dict(visual_review='PERSONALLY_READ_FULL_RENDER_ON_2026-11-10; rates and row dates page1, VAT note page7',
                recreation='python3 -B '+str(OUT/'primary_review.py')+' --render')
            if png.exists():meta.update(render_path=str(png.relative_to(OUT)),render_sha256=review.digest(png.read_bytes()))
            txt=target.with_suffix('.txt')
            if txt.exists():meta['text_sha256']=review.digest(txt.read_bytes())
            receipt['pages'][str(page)]=meta
        for component,row,old,new,unit,new_date in SELECTED:
            actual=extracts[id,component];expected=new if id=='khv_tariff_202611' else old
            date=new_date if id=='khv_tariff_202611' else '2026-01-01'
            review.eq(actual['value'],expected);assert actual['unit']==unit and actual['source_row']==row and actual['effective_from']==date
            assert actual['source_sha256']==sha and 'EXCLUDES_VAT' in actual['vat_basis']
            selected.append(dict(source_id=id,component_id=component,source_row=row,value=expected,unit=unit,effective_from=date,
                amount_and_date_page=1,vat_note_page=7,tax_basis='EXCLUDES_VAT; applicable statutory addition not quantified',
                source_sha256=sha,personal_visual_check='PASS',actual_RW_contract='UNKNOWN'))
        receipts.append(receipt)
    review.jsonout('primary_raw_receipts.json',receipts)
    review.csvout('primary_selected_rows.csv',selected)
    review.jsonout('primary_checks.json',dict(selected_rows=16,raw_files_hashed=2,pages_personally_read=4,
        selected_extract_match='PASS',full_document_extraction='NOT_CLAIMED',RW_contract='UNKNOWN',
        conditions='40 percent surcharge applies to the specified days4/5, 0500-0700 UTC; no universal surcharge inferred',
        row_dates='New source general start Jan1; takeoff/security effective Feb10, stairs/bus Jan16, not filename month',
        parking='Hourly/day/month entries are different billing bases; do not add automatically',
        UFA_OMS='30 pinned selected rows joined and units/dates checked in review.py; primary raw not personally read or hashed'))
    print(json.dumps(dict(raw_hashes='PASS',selected_rows=16,actual_RW_contract='UNKNOWN')))


if __name__=='__main__':main()
