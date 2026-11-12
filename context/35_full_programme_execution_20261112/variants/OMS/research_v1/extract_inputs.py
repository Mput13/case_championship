import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PREFIX = 'context/35_full_programme_execution_20261112/'
PINS = {'P00R':'b7d74e67dd6c603db049b1915b1afec987e3b458','P02':'d9486f113f074c185a94bcc5c0afeef12ea3574f','P03':'79dc698b99dfe866886d32376ed388e85bdd039c','P04':'620a0ac4bb11763319c4227485f6a3996b91d367','P06':'982f13d9b6c378ed9581125ecc5c40f17dade6a3','MODEL':'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6','REASSESS':'c18f7640ea36647a05b39089e5293f22dd009f63'}
FILES = {
 'P02':['calendar_inventory.csv','competitor_products.csv','market_coverage.csv','historical_demand_context.csv','historical_route_context.csv','fare_panel.csv','ordered_itineraries.csv','physical_adjacent_leg_candidates.csv','clock_conflicts.csv','competitor_responses.csv'],
 'P03':['airport_constraints.csv','existing_commitments.csv','crew_calendar.csv','aircraft_type_parameters.csv'],
 'P04':['airport_reference_examples.csv','airport_coverage.csv','cost_ranges.csv','event_rate_map.csv'],
 'MODEL':['data/manual/rw_routes_now.csv','data/manual/known_flows.csv','data/manual/airport_tech.csv','data/assumptions/bases.csv','data/processed/network_routes.csv','data/manual/route_competitors.csv','data/manual/fare_offer_spotchecks.csv','data/processed/catchments.csv'],
}
manifest = []
for owner, files in FILES.items():
 for filename in files:
  path = filename if owner == 'MODEL' else PREFIX+owner+'/'+filename
  raw = subprocess.check_output(['git','show',PINS[owner]+':'+path])
  rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
  selected = []
  for i,row in enumerate(rows,2):
   idkeys = ('a','b','origin','destination','from','to','from_iata','to_iata','iata','node','geography_or_airport','city','city_or_airport','market_id','ordered_airports','demand_pool_id')
   matched = any(row.get(k) in ('OMS','Омск') or 'OMS' in row.get(k,'').split(':') or 'OMS' in row.get(k,'').split(';') for k in idkeys)
   if matched:
    canonical = json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    selected.append({'source_row_number_header_is_1':i,'source_row_sha256':hashlib.sha256(canonical).hexdigest(),'source_row_id':next((row[k] for k in ('schedule_instance_id','product_id','cost_id','example_id','itinerary_pattern_id','market_id') if row.get(k)),str(i)),'row':row})
  dest='inputs/'+owner+'_'+Path(filename).stem+'_OMS.json'
  (ROOT/dest).write_text(json.dumps(selected,ensure_ascii=False,indent=2)+'\n')
  manifest.append({'owner':owner,'commit':PINS[owner],'path':path,'source_blob_git_oid':subprocess.check_output(['git','rev-parse',PINS[owner]+':'+path],text=True).strip(),'source_sha256':hashlib.sha256(raw).hexdigest(),'source_rows':len(rows),'selected_rows':len(selected),'local_extract':dest,'selection':'OMS in identifying columns; no semantic full-text filter','row_hash_method':'SHA256 UTF8 json sorted keys compact separators of parsed source row'})
for owner,filename in [('P06','producer_contract.json'),('P06','README.md'),('P00R','contract_addendum.json')]:
 path=PREFIX+owner+'/'+filename;raw=subprocess.check_output(['git','show',PINS[owner]+':'+path])
 manifest.append({'owner':owner,'commit':PINS[owner],'path':path,'source_sha256':hashlib.sha256(raw).hexdigest(),'use':'contract read, not copied'})
(ROOT/'source_pins.json').write_text(json.dumps({'pins':PINS,'inputs':manifest},ensure_ascii=False,indent=2)+'\n')
for x in manifest:
 if 'selected_rows' in x:print(x['owner'],x['path'].split('/')[-1],x['selected_rows'])
