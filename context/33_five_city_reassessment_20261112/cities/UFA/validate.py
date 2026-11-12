"""Validate schemas, references, pinned hashes, route coverage and arithmetic.
Run: python3 /absolute/path/UFA/validate.py. Offline; no external side effects.
"""
from pathlib import Path
import csv,hashlib,json,math,re,subprocess,sys
P=Path(__file__).resolve().parent
schemas={
'sources.csv':'source_id,title,organization,url,published_at,accessed_at,period,geography,metric,unit,source_type,access_status,limitations',
'claims.csv':'claim_id,claim,evidence_status,source_ids,period,geography,value,unit,mechanism,decision_impact,uncertainty',
'routes.csv':'origin,destination,product,season,competitors,frequency_evidence,demand_evidence,ground_alternative,rw_overlap,operating_constraints,assessment,source_ids,missing_fields',
'features.csv':'feature_id,feature,evidence_ids,mechanism,affected_markets,magnitude_or_bound,counterevidence,decision_effect,unknowns'}
tables={}
for n,cols in schemas.items():
 with (P/n).open() as f:
  reader=csv.DictReader(f);assert reader.fieldnames==cols.split(','),n
  rows=list(reader);assert all(None not in r and all(v is not None for v in r.values()) for r in rows),n
  assert rows,n;tables[n]=rows
sources={r['source_id'] for r in tables['sources.csv']};claims={r['claim_id'] for r in tables['claims.csv']}
assert len(sources)==len(tables['sources.csv']);assert len(claims)==len(tables['claims.csv'])
assert all(x.startswith('UFA-') for x in sources|claims)
assert len({r['feature_id'] for r in tables['features.csv']})==len(tables['features.csv'])
for n in ['claims.csv','routes.csv']:
 for row in tables[n]:
  for ref in row['source_ids'].split(';'):assert ref in sources,(n,ref)
for row in tables['features.csv']:
 for ref in row['evidence_ids'].split(';'):assert ref in claims,ref
model=list(csv.DictReader((P.parent.parent/'inputs/model/network_routes.csv').open()))
expected={r['to'] for r in model if r['scenario']=='base' and r['variant']=='Хаб UFA'}
author={r['destination'] for r in tables['routes.csv'] if 'author_hub' in r['product']}
assert author==expected,(author,expected)
assert all(r['origin']=='UFA' for r in tables['routes.csv'])
dec=json.loads((P/'decision.json').read_text())
assert dec['iata']=='UFA'
assert {x['option'] for x in dec['options']}=={'localdirect','existingbase','newbase','hub','groundfeed','noproject'}
for x in dec['options']:
 for key in ['status','strongest_for','strongest_against','decision_parameter','condition_or_threshold','obtain_from','action_if_condition_changes']:assert x[key],(x['option'],key)
for f in dec['evidence_files'].values():assert (P/f).is_file(),f
schedule=list(csv.DictReader((P/'schedule_rows.csv').open()))
sums=json.loads((P/'schedule_summary.json').read_text());logs=json.loads((P/'schedule_fetch_log.json').read_text())
assert all(x['status']!='error' for x in logs),logs
assert len(schedule)==sum(x.get('rows',0) for x in logs)
assert all(not x['ambiguous_records'] for x in sums)
assert all(x['published_departures']==len(x['dates_and_flights']) for x in sums if x['published_departures']!='')
assert all(sum(x['by_airline'].values())==x['published_departures'] for x in sums if x['published_departures']!='')
for code,n in [('SVX',4),('NUX',2)]:
 assert all(x['by_airline'].get('Red Wings')==n for x in sums if x['destination']==code)
assert all(x['published_departures']=='' for x in sums if x['destination'] in ['TOF','KEJ'])
assert [x['published_departures'] for x in sums if x['destination']=='GOJ']==[0,0,2]
assert [x['published_departures'] for x in sums if x['destination']=='OMS']==[0,0,1]
# Calculate again and require deterministic output; this also checks every manifest hash.
f=P/'calculations.json';before=f.read_bytes()
subprocess.run([sys.executable,str(P/'calculate.py')],stdout=subprocess.DEVNULL,check=True)
assert f.read_bytes()==before,'Calculation output drift'
c=json.loads(f.read_text());nd=c['network_diagnostics']
assert len(c['input_manifest_verified'])==34
assert math.isclose(nd['annual_local_model']+nd['annual_transfer_segments_model'],408337,abs_tol=2)
assert math.isclose(nd['annual_transfer_segments_model'],2*115716,abs_tol=1)
assert math.isclose(c['tariff_basket_scenario']['subtotal_listed_only_rub'],117721.26,abs_tol=.001)
assert math.isclose(nd['fuel_only_additional_cost_if_all_network_fuel_priced_at_ufa_mln'],70.80008672533336)
for r in tables['claims.csv']:
 if r['evidence_status'] in ['unknown','not_fully_verified','secondary_unverified_magnitude','condition']:assert r['value']=='',(r['claim_id'],r['value'])
for n in ['sources.csv','claims.csv','routes.csv','features.csv','decision.json','calculations.json']:
 assert not re.search(r'\b(?:NaN|Infinity)\b',(P/n).read_text()),n
# Check all explicit source/claim ids in the dossier, allowing shorthand Sxx/Cxx explained at its start.
for ref in re.findall(r'\bUFA-[SC]\d{2}\b',(P/'dossier.md').read_text()):assert ref in sources|claims,ref
result={'status':'PASS','as_of':'2026-11-12','schemas':'exact brief headers','counts':{k:len(v) for k,v in tables.items()},'pinned_manifest_files_verified':34,'author_base_routes_covered':sorted(author),'published_schedule_rows':len(schedule),'route_pages_read':sum(x['status']=='read' for x in logs),'weeks_checked':sorted({x['week_start'] for x in sums}),'schedule_conflicts':0,'arithmetic':'deterministic offline rerun passed','references':'all explicit source/claim IDs resolve','unknown_values':'empty, not zero','decision_options':6,'not_validated':['Actual flown services or route OD','Public sale and cabin capacity of corporate flights','Full airline profit or financing','Current restricted statistical PDFs beyond indexed text','Equal-resource network reoptimization and live commercial launch']}
(P/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
