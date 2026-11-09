#!/usr/bin/env python3
"""Keep fa39 rules immutable; separate carrier association from legal role.

No extra source/network. This table is a typed adapter for new consumers.
"""
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SHA='fa39de413ac00a93b0214840aae2e7916332cef5'
PATH='context/16_agent_research/alternative/product_probe_v1/normalized/flight_rules.csv'

def main():
    raw=subprocess.check_output(['git','show',SHA+':'+PATH])
    source=list(csv.DictReader(io.StringIO(raw.decode('utf-8'))));rows=[]
    for r in source:
        out=dict(r)
        out.update(source_carrier_association='Azimuth / A4 prefix published with airport rule; carrier news corroborates route',
                   operating_carrier_id=None,operating_carrier_iata=None,marketing_carrier_iata=None,
                   legal_carrier_role_status='UNKNOWN',legal_role_missing_reason='Source association does not establish operating or marketing legal role for a future instance',
                   value_status='OBSERVED',derived_fields='rule_id;origin_iana;destination_iana;arrival_day_offset',
                   day_offset_value_status='DERIVED',timezone_value_status='DERIVED',
                   legacy_input_commit=SHA,legacy_table_sha256=hashlib.sha256(raw).hexdigest(),
                   adapter_version='c14-flight-role-adapter-v2')
        rows.append(out)
    p=ROOT/'normalized/flight_rules_v2.csv'
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (ROOT/'normalized/flight_role_adapter_validation.json').write_text(json.dumps({'rows':len(rows),'legacy_input_commit':SHA,
        'legacy_table_sha256':hashlib.sha256(raw).hexdigest(),'legal_operating_marketing_fields':'NULL_UNKNOWN',
        'source_carrier_association':'retained','calendar_rule_ids_clocks_periods_changed':False,
        'value_status':'OBSERVED for published rule fields; explicit DERIVED statuses for day offset/timezone'},ensure_ascii=False,indent=2)+'\n')
    print('Typed6 rules; source association retained, legal carrier roles NULL; old snapshot unchanged')

if __name__=='__main__':main()
