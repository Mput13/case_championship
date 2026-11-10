"""Descriptive two-year projection from frozen outputs, not a new forecast."""
import csv
import hashlib
import io
import json
import subprocess
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SHA='f99d6cd52dcc06995bf984fddd2f057226243b06'
PATH='context/28_evening_run_20261110/methods/runs/integer_year_v1/annual_comparison.csv'
b=subprocess.check_output(['git','show',SHA+':'+PATH])
assert hashlib.sha256(b).hexdigest()=='cef26d5e1f4d468f9c67e83d32690b16f43e0fab50574f408e8beb21be162f1c'
groups=defaultdict(dict)
for rownum,row in enumerate(csv.DictReader(io.StringIO(b.decode())),2):
    key=tuple(row[k] for k in ['branch','scenario','network'])
    assert row['year'] not in groups[key]
    groups[key][row['year']]=(rownum,row)
out=[]
for (branch,scenario,network),g in sorted(groups.items()):
    assert set(g)=={'2027','2028'}
    n27,a=g['2027']; n28,z=g['2028']
    c27=D(a['dated_contribution_rub']); c28=D(z['dated_contribution_rub']); change=c28-c27
    f27=D(a['dated_flights']);f28=D(z['dated_flights'])
    out.append(dict(branch=branch,scenario=scenario,network=network,
        flights2027=a['dated_flights'],flights2028=z['dated_flights'],
        journeys2027=a['dated_journeys'],journeys2028=z['dated_journeys'],
        net_added_segments2027=a['net_added_segments_listed_keep_only'],net_added_segments2028=z['net_added_segments_listed_keep_only'],
        contribution_rub2027=a['dated_contribution_rub'],contribution_rub2028=z['dated_contribution_rub'],
        contribution_change_rub=str(change),
        contribution_trend='NO_PROJECT_FLIGHTS' if f27==f28==0 else ('IMPROVES' if change>0 else 'WORSENS' if change<0 else 'UNCHANGED'),
        project_activated_later=f27==0 and f28>0,
        support=a['support'], full_company_pnl='UNKNOWN', cumulative_financing='UNKNOWN',
        profit_year='NOT_ESTABLISHED',forecast_status='FIXED_CONSTRUCTED_TIMETABLE_CONDITIONAL_NOT_ACTUAL_FORECAST',
        source_sha=SHA,source_path=PATH,source_row2027=n27,source_row2028=n28))
assert len(out)==48
target=ROOT/'trajectory_2027_2028.csv'
with target.open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
read=list(csv.DictReader(target.open()))
for r in read:
    assert D(r['contribution_change_rub'])==D(r['contribution_rub2028'])-D(r['contribution_rub2027'])
    assert r['profit_year']=='NOT_ESTABLISHED'
result=dict(source_sha=SHA,source_path=PATH,source_sha256=hashlib.sha256(b).hexdigest(),
    source_rows=96,paired_cases=48,all_original_strings_preserved=True,
    only_new_arithmetic='2028 contribution minus2027 contribution',
    full_pnl_cash_profit_year_not_inferred=True,independent_review_of_projection='NOT_RUN',
    upstream_review_sha='994c6c0d293ae6053b4e73b279689c5020314e09')
(ROOT/'trajectory_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result))
