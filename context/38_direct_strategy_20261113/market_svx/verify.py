import csv,json
from pathlib import Path
p=Path(__file__).parent
expected={'AER-SVX','CEK-SVX','GOJ-SVX','IKT-SVX','KJA-SVX','MRV-SVX','SVX-TJM','SVX-TOF','SVX-ZIA'}
checks=[]
def read(name):
 with (p/name).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
pe=read('pair_evidence.csv'); services=read('services.csv'); fares=read('fares.csv'); demand=read('monthly_demand.csv'); alt=read('alternatives.csv'); sources=read('sources.csv'); gaps=read('decision_gaps.csv')
checks.append(('all_nine_pairs',set(x['pair'] for x in pe)==expected))
checks.append(('monthly_rows_216',len(demand)==216))
checks.append(('service_pair_coverage',set(x['pair'] for x in services)==expected))
checks.append(('fare_pair_coverage',set(x['pair'] for x in fares)==expected))
checks.append(('references_exist',all(x['source'] for x in services) and all(x['source'] for x in fares)))
checks.append(('unknown_demand_not_zero',all(x['passenger_volume']=='UNKNOWN' for x in demand)))
checks.append(('service_period_fields',all(x['valid_period'] and x['status_coverage'] for x in services)))
checks.append(('source_rows_unique',len({x['source_id'] for x in sources})==len(sources)))
checks.append(('gap_rows_unique',len({(x['pair'],x['gap']) for x in gaps})==len(gaps)))
result={'checks':[{'name':n,'pass':ok} for n,ok in checks],'counts':{'pairs':len(pe),'services':len(services),'fares':len(fares),'monthly_demand':len(demand),'alternatives':len(alt),'sources':len(sources),'decision_gaps':len(gaps)},'status':'PASS' if all(x[1] for x in checks) else 'FAIL'}
(p/'validation.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
raise SystemExit(0 if result['status']=='PASS' else 1)
