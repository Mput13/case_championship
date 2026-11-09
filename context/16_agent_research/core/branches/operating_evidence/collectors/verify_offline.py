#!/usr/bin/env python3
"""Recount source/derived rows and verify deterministic offline replay.

Checks integrity, key multiplication, routing and state separation. They do not
validate free fleet, sales, airport contracts or execution beyond source meaning.
"""
import collections
import csv
from datetime import datetime,timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'normalized'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(name):return list(csv.DictReader((OUT/name).open()))
def unique(rows,fields):
    counts=collections.Counter(tuple(r[k] for k in fields) for r in rows)
    return dict(rows=len(rows),distinct_keys=len(counts),extra_rows=sum(c-1 for c in counts.values()))
class FirstTableRows(HTMLParser):
    def __init__(self):super().__init__();self.depth=0;self.done=False;self.rows=0
    def handle_starttag(self,t,a):
        if t=='table' and not self.done:self.depth+=1
        if t=='tr' and self.depth==1:self.rows+=1
    def handle_endtag(self,t):
        if t=='table' and self.depth:
            self.depth-=1
            if not self.depth:self.done=True
def main():
    manifests=json.loads((ROOT/'dataset_manifest.json').read_text());raw_before={e['raw_path']:sha(ROOT/e['raw_path']) for e in manifests if e.get('raw_path')}
    before={f.name:sha(f) for f in OUT.iterdir() if f.suffix in ['.csv','.json']}
    for script,stdout in [('normalize.py','normalize_replay_stdout.json'),('supplement.py','supplement_replay_stdout.json')]:
        p=subprocess.run([sys.executable,str(ROOT/'collectors'/script)],capture_output=True,text=True,check=True)
        (OUT/stdout).write_text(p.stdout)
    after={f.name:sha(f) for f in OUT.iterdir() if f.suffix in ['.csv','.json']}
    changed=[k for k in before if k in after and before[k]!=after[k]]
    raw_changed=[path for path,h in raw_before.items() if sha(ROOT/path)!=h]
    table=FirstTableRows();table.feed((ROOT/'raw/favt_regional_2026.html').read_text())
    uv=read('uvt_schedule_rules_unique.csv');ir=read('iraero_published_itineraries.csv');om=read('omsk_outbound_week_20261207.csv');cost=read('airport_cost_selected_verified.csv');join=read('uvt_omsk_two_source_join.csv')[0]
    keys=dict(uvt_rule=unique(uv,['origin_city_raw','destination_city_raw','flight_number_raw','valid_from','valid_to','weekdays_iso','departure_local_raw','arrival_local_raw']),
      oms_instance=unique(om,['carrier_raw','outbound_flight_numeric','destination_airport_iata','departure_local']))
    checks=dict(offline_replay_identical=not changed,changed_outputs=changed,raw_payloads_unchanged=not raw_changed,changed_raw=raw_changed,
      independent_HTML_subsidy_rows=table.rows,parsed_subsidy_rows=len(read('favt_subsidy_2026_full.csv')),
      subsidy_raw_table_matches_parsed=table.rows-1==len(read('favt_subsidy_2026_full.csv')),
      keys=keys,omsk_dates_within_week=all('2026-12-07'<=r['departure_date_local']<='2026-12-13' for r in om),
      omsk_missing_keys=sum(not r['origin_airport_key'] or not r['destination_airport_key'] for r in om),
      omsk_RTin_next_leg_TOX=all(r['destination_airport_iata']=='TOX' for r in om if r['carrier_raw']=='ЮВТаэро'),
      uv_omsk_join_departure_match=join['departure_time_match']=='True',uv_omsk_join_arrival_match=join['arrival_time_match']=='True',uv_omsk_join_preserves_Tobolsk='Тобольск' in join['source2_full_routing'],
      iraero_clock_basis_unknown=all(r['time_basis'].startswith('UNKNOWN') for r in ir),
      subsidy_award_paid_still_unknown=all(not r['subsidy_award_RUB'] and not r['subsidy_paid_RUB'] and not r['actual_operated_flights'] for r in read('favt_subsidy_2026_full.csv')),
      cost_rows_selected_validation_only=all(r['source_status']=='VALIDATED' and r['validation_scope'].startswith('SELECTED_') for r in cost),
      front_Telegram_restricted=all(e['acquisition_status']=='RESTRICTED_USE' for e in manifests if e['dataset_id'].startswith('colleague_')))
    checks['all_pass']=all(checks[k] for k in ['offline_replay_identical','raw_payloads_unchanged','subsidy_raw_table_matches_parsed','omsk_dates_within_week','omsk_RTin_next_leg_TOX','uv_omsk_join_departure_match','uv_omsk_join_arrival_match','uv_omsk_join_preserves_Tobolsk','iraero_clock_basis_unknown','subsidy_award_paid_still_unknown','cost_rows_selected_validation_only','front_Telegram_restricted']) and checks['omsk_missing_keys']==0 and all(v['extra_rows']==0 for v in keys.values())
    result=dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),checks=checks,limits='Offline structural, scope and integrity checks, not observed demand/contract/fleet acceptance',network_calls='None: only reviewed normalize/supplement and local pdftotext subprocess')
    (ROOT/'offline_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(checks,ensure_ascii=False,indent=2))
    if not checks['all_pass']:raise SystemExit(1)
if __name__=='__main__':main()
