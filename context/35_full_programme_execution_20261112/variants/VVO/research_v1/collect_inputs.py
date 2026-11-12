"""VVO-only extracts of pinned Git blobs. Does not mutate Git or other packages."""
import csv, hashlib, io, json, subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent
P = 'context/35_full_programme_execution_20261112/'
PINS = {'author':'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6','reassessment':'c18f7640ea36647a05b39089e5293f22dd009f63','P00R':'b7d74e67dd6c603db049b1915b1afec987e3b458','P02':'d9486f113f074c185a94bcc5c0afeef12ea3574f','P03':'79dc698b99dfe866886d32376ed388e85bdd039c','P04':'620a0ac4bb11763319c4227485f6a3996b91d367','P06':'982f13d9b6c378ed9581125ecc5c40f17dade6a3'}
FILES = {
 'author':['data/manual/airport_tech.csv','data/manual/rw_routes_now.csv','data/manual/known_flows.csv','data/manual/longlist_manual.csv','data/manual/pax_2025_overrides.csv','data/manual/route_competitors.csv','data/manual/fare_offer_spotchecks.csv','data/manual/competitor_bases.csv','data/manual/competitor_hubs.csv','data/processed/longlist.csv','data/processed/longlist_scores.csv','data/processed/catchments.csv','data/external/colleagues/route_product_cards.csv','data/external/colleagues/primary_monthly_increments.csv','data/external/colleagues/primary_seasonality_profiles.csv','context/11_practical_screening/city_matrix.csv'],
 'P02':[P+'P02/'+x+'.csv' for x in ['market_coverage','city_coverage','competitor_products','calendar_inventory','fare_panel','historical_demand_context','historical_route_context','physical_adjacent_leg_candidates','ordered_itineraries','clock_conflicts','competitor_responses']],
 'P03':[P+'P03/'+x+'.csv' for x in ['airport_constraints','existing_commitments','aircraft_type_parameters']],
 'P04':[P+'P04/'+x+'.csv' for x in ['airport_coverage','airport_reference_examples','cost_ranges','thresholds','budget_components']],
 'P00R':['context/34_full_programme_plan_20261112/city_research_seed.csv'],
}

def digest(x):return hashlib.sha256(x).hexdigest()
def show(label,path):return subprocess.check_output(['git','show',PINS[label]+':'+path])
def relevant(row):
 identifiers=['iata','city','airport','origin','destination','from_iata','to_iata','a','b','base','hub']
 known=[str(row[k]) for k in identifiers if k in row]
 if known:return any(x in ['VVO','Владивосток','UHWW'] for x in known)
 return any(x in json.dumps(row,ensure_ascii=False) for x in ['VVO','Владивосток','UHWW'])

def main():
 (OUT/'inputs').mkdir(exist_ok=True)
 manifest=[]
 for label,paths in FILES.items():
  for path in paths:
   raw=show(label,path); rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
   shared=path.endswith(('aircraft_type_parameters.csv','thresholds.csv','budget_components.csv'))
   selected=[]
   for i,row in enumerate(rows,2):
    if relevant(row) or shared:
     canonical=json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
     selected.append({'source_commit':PINS[label],'source_path':path,'source_row_number':i,'source_blob_sha256':digest(raw),'source_row_sha256':digest(canonical),'source_row_id':row.get('product_id',row.get('market_id',row.get('key',row.get('iata',row.get('threshold_id',row.get('budget_component_id',str(i))))))),'data':row})
   name=label+'__'+path.replace('/','__').replace('.csv','.json')
   (OUT/'inputs'/name).write_text(json.dumps(selected,ensure_ascii=False,indent=2)+'\n')
   manifest.append({'source_id':'PIN-'+label+'-'+Path(path).stem,'commit':PINS[label],'path':path,'source_blob_sha256':digest(raw),'source_git_blob':subprocess.check_output(['git','rev-parse',PINS[label]+':'+path],text=True).strip(),'source_row_count':len(rows),'selected_row_count':len(selected),'filter':'VVO / Владивосток / UHWW; common aircraft/threshold/cost-driver schema explicitly retained' if shared else 'VVO / Владивосток / UHWW only','extract_path':'inputs/'+name})
 for label,path in [('P00R','context/34_full_programme_plan_20261112/variant_research_plan.json'),('P06',P+'P06/producer_contract.json'),('P06',P+'P06/README.md'),('P00R',P+'P00R/contract_addendum.json')]:
  raw=show(label,path)
  item={'source_id':'PIN-'+label+'-'+Path(path).stem,'commit':PINS[label],'path':path,'source_blob_sha256':digest(raw),'read_only_reference':True}
  if path.endswith('variant_research_plan.json'):
   obj=json.loads(raw); selected=[x for x in obj['legacy_hypotheses'] if relevant(x)];(OUT/'inputs/legacy_VVO_hypotheses.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2)+'\n');item['extract_path']='inputs/legacy_VVO_hypotheses.json'
  manifest.append(item)
 (OUT/'input_manifest.json').write_text(json.dumps({'pins':PINS,'sources':manifest},ensure_ascii=False,indent=2)+'\n')
 print(json.dumps([{'path':x['path'],'rows':x.get('selected_row_count')} for x in manifest],ensure_ascii=False))

if __name__=='__main__':main()
