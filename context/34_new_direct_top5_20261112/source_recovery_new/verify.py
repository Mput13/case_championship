#!/usr/bin/env python3
"""Offline artifact validation; structural pass is never market verification."""
import csv,hashlib,json,re,sys
from pathlib import Path
B=Path(__file__).resolve().parent
SCHEMAS={
'classification.csv':'pair period week_start week_end classification nonstop_competitor rw_nonstop rw_frequency_each_way coverage reason direct_source_field',
'schedules.csv':'pair period week_start week_end origin destination carrier_operated carrier_marketed flight frequency_per_week days departure_local arrival_local block_minutes observed_period field_status direct_source_field proposed_departure_local window_status window_source notes',
'fares_and_alternatives.csv':'pair period week_start week_end origin destination travel_date travel_date_status adults one_way checked_baggage_kg gross_rub net_rub fare_status quote_retrieved_at transfer_alternative rail_alternative elapsed_minutes alternative_fare_rub direct_source_field request_parameters_source notes',
'demand_reasons.csv':'pair period week_start week_end origin destination customer_hypothesis purpose seasonality direction_reason why_choose quantified_endpoint_journeys rw_existing_passengers support_contract direct_source_field hypothesis_status',
'sources.csv':'source_id url source_type publication_date retrieval_date covered_date locator short_quote proves limitations access_status excerpt_path',
}
errors=[];tables={}
def check(ok,msg):
    if not ok:errors.append(msg)
required=list(SCHEMAS)+['notes.md','actual_requests.json','verify.py']
for name in required:check((B/name).is_file(),f'missing {name}')
for name,header in SCHEMAS.items():
    if not (B/name).is_file():continue
    with (B/name).open(newline='',encoding='utf-8') as f:
        raw=list(csv.reader(f))
    check(bool(raw),f'empty {name}')
    if not raw:continue
    check(raw[0]==header.split(),f'schema {name}')
    check(all(len(r)==len(raw[0]) for r in raw[1:]),f'width {name}')
    with (B/name).open(newline='',encoding='utf-8') as f:tables[name]=list(csv.DictReader(f))
sources={r['source_id']:r for r in tables.get('sources.csv',[])}
check(len(sources)==len(tables.get('sources.csv',[])),'duplicate source id')
for sid,r in sources.items():
    check(all(r.values()),f'empty source metadata {sid}')
    check((B/r['excerpt_path']).is_file(),f'missing excerpt {sid}')
    check(r['source_type'] in {'PRIMARY','MARK_SECONDARY','LOCAL_PINNED','PROPOSAL'},f'source type {sid}')
for name,rows in tables.items():
    for r in rows:
        for key in ('direct_source_field','window_source'):
            if key in r:
                for sid in r[key].split(';'):check(sid in sources,f'reference {name}:{sid}')
        check('VERIFIED' not in r.values(),f'blanket VERIFIED {name}')
pairs={'GOJ-KJA','GOJ-TOF','KUF-TOF','OMS-PEE'}
weeks={'ordinary':('2026-11-16','2026-11-22'),'target':('2027-02-01','2027-02-07')}
for name in ('classification.csv','schedules.csv','fares_and_alternatives.csv','demand_reasons.csv'):
    rows=tables.get(name,[]);expected=8 if name=='classification.csv' else 16
    check(len(rows)==expected,f'row count {name}')
    for pair in pairs:
        for period,dates in weeks.items():
            selected=[r for r in rows if r['pair']==pair and r['period']==period]
            check(len(selected)==(1 if name=='classification.csv' else 2),f'pair/period {name}:{pair}:{period}')
            check(all((r['week_start'],r['week_end'])==dates for r in selected),f'dates {name}:{pair}:{period}')
            if name!='classification.csv':
                a,b=pair.split('-');check({(r['origin'],r['destination']) for r in selected}=={(a,b),(b,a)},f'directions {name}:{pair}')
    check({r['pair'] for r in rows}==pairs,f'out-of-scope pair {name}')
for r in tables.get('classification.csv',[]):
    check(r['classification']=='UNKNOWN','unsupported positive/absence classification')
    check(r['rw_frequency_each_way']=='UNKNOWN','unproven frequency')
for r in tables.get('schedules.csv',[]):
    check(r['frequency_per_week']=='UNKNOWN' and r['block_minutes']=='UNKNOWN','unproven numeric schedule')
    check(r['window_status']=='PROPOSAL_FOR_COMPUTATIONAL_CHECK_ONLY' and r['window_source']=='P01','proposal attribution')
for r in tables.get('fares_and_alternatives.csv',[]):
    check(all(r[k]=='UNKNOWN' for k in ('gross_rub','net_rub','elapsed_minutes','alternative_fare_rub')),'unquoted fare/alternative number')
    check(r['adults']=='1' and r['checked_baggage_kg']=='20' and r['request_parameters_source']=='USER_TASK','fare request provenance')
for r in tables.get('demand_reasons.csv',[]):check(r['quantified_endpoint_journeys']=='UNKNOWN','unobserved OD number')
qcount=None
if (B/'actual_requests.json').is_file():
    log=json.loads((B/'actual_requests.json').read_text());qcount=sum(len(c['args'].get('search_query',[])) for c in log['calls'])
    check(qcount==10 and qcount==log['search_queries'],'query budget/count')
    check(all(c.get('result') for c in log['calls']),'missing actual tool response')
    for entry in log.get('same_page_archive_requests',[]):
        if 'archive' in entry:
            p=B/entry['archive'];check(p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256'],'archive integrity')
report=dict(structural_validation='PASS' if not errors else 'FAIL',research_resolution='PARTIAL_EVIDENCE_ALL_ASSIGNED_CLASSES_UNKNOWN',market_verified=False,errors=errors,search_queries=qcount,row_counts={k:len(v) for k,v in tables.items()},missing_files=[n for n in required if not (B/n).is_file()],scope='four assigned pairs; two directions; ordinary and target weeks separate',files_sha256={n:hashlib.sha256((B/n).read_bytes()).hexdigest() for n in required if (B/n).is_file()})
(B/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='files_sha256'},ensure_ascii=False,indent=2))
sys.exit(bool(errors))
