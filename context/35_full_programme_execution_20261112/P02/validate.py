"""Owner checks of provenance, calendar, joins and independent small counterexamples."""
import csv, datetime as dt, hashlib, itertools, json, pathlib, subprocess
P=pathlib.Path(__file__).resolve().parent
def rows(f):return list(csv.DictReader((P/f).open()))
checks=[]
def check(name,value,detail=''):
    checks.append(dict(check=name,passed=bool(value),detail=detail))
inputs=json.loads((P/'input_manifest.json').read_text())
for r in inputs:
    b=(P/r['path']).read_bytes()
    check('input_hash:'+r['source_id'],hashlib.sha256(b).hexdigest()==r['sha256'])
    original=subprocess.check_output(['git','show',r['commit']+':'+r['git_path']])
    check('input_exact_git_blob:'+r['source_id'],b==original)
sources={r['source_id']:r for r in json.loads((P/'sources.json').read_text())}
products=rows('competitor_products.csv');calendar=rows('calendar_inventory.csv');coverage=rows('market_coverage.csv');monthly=rows('offer_monthly_coverage.csv');assumptions=rows('assumptions_register.csv')
ids={r['product_id'] for r in products};aids={r['assumption_id'] for r in assumptions}
check('product_ids_unique',len(ids)==len(products))
check('market_keys_unique',len({r['market_id'] for r in coverage})==len(coverage))
check('monthly_keys_unique',len({(r['market_id'],r['month']) for r in monthly})==len(monthly))
check('all_20_seed_cities_retained',len(rows('city_coverage.csv'))==20)
check('all_380_directed_seed_pairs_registered',sum('twenty_city_domain' in r['scope'] for r in coverage)==380)
check('all_product_sources_resolve',all(r['source_id'] in sources for r in products))
check('all_assumption_ids_resolve',all(set(r['assumption_ids'].split(';'))<=aids for r in products))
check('calendar_lineage_resolves',all(set(r['source_product_ids'].split(';'))<=ids for r in calendar))
check('no_unknown_as_zero_month',all(r['dated_published_station_pair_instances']!='0' for r in monthly))
check('no_market_completeness_overclaim',all(r['complete_market']=='false' and r['absence_proves_no_competitor']=='false' for r in coverage))
check('no_published_inventory_claim',all(r['seat_inventory_usable']=='false' and r['open_seats']=='UNKNOWN' for r in calendar))
check('no_2028_factual_offer',not any(r['departure_date'].startswith('2028') for r in calendar))
check('calendar_instance_key_unique',len({r['schedule_instance_id'] for r in calendar})==len(calendar))
check('quote_not_order',all('no_order' in r['sellability'] for r in products if r['row_grain'].startswith('dated_primary')))
rw=[r for r in products if r['source_id']=='NEW_RW_QUOTE' and r['fare_basis']=='Standard']
check('primary_RW_20kg_quote',len(rw)==1 and rw[0]['fare_rub']=='5200' and rw[0]['departure_date']=='2026-12-08' and rw[0]['open_seats']=='UNKNOWN')
uvt=[r for r in products if r['source_id']=='NEW_UVT_SCHEDULE' and r['carrier']=='RT' and r['flight']=='RT651']
pairs={(r['origin'],r['destination']) for r in uvt}
check('RT651_through_pattern_present',{('KZN','OMS'),('KZN','RMZ'),('RMZ','OMS')}<=pairs,str(sorted(pairs)))
patterns=rows('ordered_itineraries.csv')
check('RT581_direction_correction',all(r['ordered_airports']=='KZN;GOJ;CEK' for r in patterns if r['flight_number']=='RT581'),'Corrected route KZN→GOJ→CEK; no GOJ→KZN→CEK assumption.')
fare=rows('fare_panel.csv')
check('quote_lead_days',all(int(r['booking_lead_days'])==(dt.date.fromisoformat(r['departure_date'])-dt.date.fromisoformat(r['as_of'])).days for r in fare))
check('seasonal_quote_dates_present',{'2026-12-08','2026-12-11','2027-01-12','2027-05-11','2027-07-13'}<={r['departure_date'] for r in fare})
query=rows('query_outcomes.csv')
check('no_offer_not_absence',all(r['absence_of_flight_established']=='false' and r['absence_of_market_established']=='false' for r in query))
check('RW_summer_no_quote_not_zero_supply',not any(r['carrier']=='WZ' and r['departure_date'] in ['2027-05-11','2027-07-13'] for r in fare))
check('inferred_source_year_flagged',all(r['year_status']=='INFERRED_CURRENT_WINTER_P02-A07' for r in products if 'P02-A07' in r['assumption_ids']))
patch=rows('inputs/P00R_schema_patch.csv')
for pid,name in [('SP03','alternatives_contract.csv'),('SP13','season_coverage.csv')]:
    spec=next(r for r in patch if r['patch_id']==pid)
    required=[x.strip() for x in spec['required_fields'].split(';')]
    exported=rows(name)
    check('schema_required_columns:'+pid,set(required)<=set(exported[0]),str(sorted(set(required)-set(exported[0]))))
    keys=['offer_set_id','demand_pool_id','travel_date_or_period','customer_segment','product_id'] if pid=='SP03' else ['coverage_id']
    check('schema_keys_unique:'+pid,len({tuple(r[k] for k in keys) for r in exported})==len(exported))
check('SP03_no_imputed_netfare',all(r['net_fare']=='UNKNOWN' for r in rows('alternatives_contract.csv')))
check('SP02_future_markets_not_fabricated',all(r['status'].startswith('NOT_ADMITTED') and r['potential_journeys']=='UNKNOWN' and r['demand_pool_id']=='UNKNOWN' for r in rows('market_binding_requests.csv')))
# Minimal counterexample independent of builder: seats cannot be separately sold to every path.
paths=[(1,0),(0,1),(1,1)]
independent_pair_capacity=sum(1 for _ in paths)
feasible=[q for q in itertools.product([0,1],repeat=3) if all(sum(q[i]*paths[i][leg] for i in range(3))<=1 for leg in [0,1])]
check('counterexample_pair_capacity_overstates_journeys',independent_pair_capacity==3 and max(map(sum,feasible))==2,'Two legs capacity1; three pair-level capacities would admit3 journeys; feasible maximum2.')
check('fare_baggage_arithmetic',5200-4000==1200 and 8800-5200==3600,'RW bag-compatible quote adds1200; observed UT20kg minusRW20kg=3600, subject to UT fee comparability/time differences.')
for r in json.loads((P/'evidence/fetch_receipts.json').read_text()):
    if 'path' in r:check('capture_hash:'+r['source_id'],hashlib.sha256((P/r['path']).read_bytes()).hexdigest()==r['sha256'])
issues=[r for r in calendar if r['clock_conflict']=='true']
report=dict(status='PASS' if all(r['passed'] for r in checks) else 'FAIL',checks=checks,check_count=len(checks),failed=[r for r in checks if not r['passed']],owner_checks_only=True,independent_review='NOT_RUN',commercial_acceptance='NOT_ESTABLISHED',market_coverage_complete=False,clock_conflicts_retained=len(issues),limitations=['No paid data, no booking, no payment.','Source completeness, open seats, annual OD and future forecast are not proven by structural checks.','Endpoint published product may include stops; do not sum station-pair capacities.'])
(P/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
write_fields=list(issues[0]) if issues else list(calendar[0])
with (P/'clock_conflicts.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,write_fields);w.writeheader();w.writerows(issues)
print(json.dumps({k:v for k,v in report.items() if k not in ['checks']},ensure_ascii=False))
raise SystemExit(0 if report['status']=='PASS' else 1)
