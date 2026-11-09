#!/usr/bin/env python3
"""Add explicit region namespace without treating source ISO as validated."""
import csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    f=ROOT/'canonical_keys.csv';rows=list(csv.DictReader(f.open()))
    rows=[r for r in rows if r['entity_type']!='region']
    cw=list(csv.DictReader((ROOT/'branches/social_economy/normalized/region_crosswalk.csv').open()))
    for c in cw:
        r={k:'' for k in rows[0]}
        r.update(entity_type='region',canonical_id=c['canonical_area_id'],source_system='Rosstat regional code via Tochno',
            source_key=c['regional_oktmo'],name=c['regional_table_label'],parent_id='COUNTRY-SCOPE:RU_PUBLISHER',
            oktmo=c['regional_oktmo'],relation='Explicit source-region label mapping; '+c['geographic_rule'],
            snapshot_at_utc='2026-11-09',limitations='Source namespace preserved; not ISO verification; source boundary edition required. Region can span timezones.',
            timezone_validation_status='NOT_A_SINGLE_TIMEZONE_ENTITY')
        rows.append(r)
    assert len({r['canonical_id'] for r in rows})==len(rows)
    for f in [ROOT/'canonical_keys.csv',ROOT/'normalized/canonical_keys.csv']:
        with f.open('w',newline='') as h:
            w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print('canonical keys',len(rows),'including',len(cw),'regions')
if __name__=='__main__':main()
