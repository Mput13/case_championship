#!/usr/bin/env python3
"""Check three cited secondary calibration pages; no airport/OD truth promotion."""
from pathlib import Path
import csv
import hashlib
import json
import re
from normalize_tax_sources import Text

BASE=Path(__file__).resolve().parents[1]
SPECS={
 'CEK':('C08','front_cek_secondary.html','regional2025','аэропортов челябинской области'),
 'OVB':('C09','front_ovb_secondary.html','2025H1','первом полугодии 2025 года'),
 'OMS':('C10','front_oms_secondary.html','2025full_year','по итогам 2025 года')}

def main():
    flows=list(csv.DictReader((BASE/'front_demand_audit/raw/data/manual/known_flows.csv').open()))
    reports=[]
    for origin,(sid,fn,scope,marker)in SPECS.items():
        p=BASE/'raw'/fn;b=p.read_bytes();s=b.decode('utf-8',errors='replace');replacements=s.count('\ufffd');parser=Text();parser.feed(s)
        text=' '.join(' '.join(parser.parts).split());plain=''.join(text.split());checks=[]
        for r in flows:
            if r['from_iata']!=origin:continue
            q=int(r['pax']);patterns=[str(q)]
            if origin=='OVB':patterns=[f'{q/1000:.2f}'.replace('.',',')]
            if origin=='CEK':patterns=['1,1млн']
            found=next((x for x in patterns if x in plain),None)
            pos=plain.find(found)if found else -1
            checks.append(dict(pair=origin+'-'+r['to_iata'],recorded_raw_pax=q,period=r['period'],annual_factor=r['annual_factor'],numeric_text_found=found is not None,near_numeric_span_has_replacement='\ufffd'in plain[max(0,pos-60):pos+80] if pos>=0 else None))
        reports.append(dict(dataset_id=sid,source_tier='SECONDARY_REPORT_NOT_ORIGINAL_AIRPORT_DATA',raw_path=str(p.relative_to(BASE)),sha256=hashlib.sha256(b).hexdigest(),scope_checked=scope,context_marker_present=marker in text.lower(),utf8_replacement_count=replacements,checks=checks,limitations='Numeric/context match in article only. Direction/endpoint/transfer/coverage beyond article unknown. H1x2 is not observed full year; regional count not allocated to CEK.'))
    out=dict(input_front_sha='9d9a874b1568c2cebec9cd3fc1f33ef76f37f450',reports=reports,native_CEK_open='400 Unicode decoding error; raw HTTP byte fetch succeeded; text decoded with replacement, no raw-byte edits',acceptance='Targeted article-context check only; no primary airport series/endpoint market acceptance')
    (BASE/'evidence/front_source_context_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(out,ensure_ascii=False))

if __name__=='__main__':main()
