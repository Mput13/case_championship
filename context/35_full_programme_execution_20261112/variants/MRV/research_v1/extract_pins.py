import csv, io, json, hashlib, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PINS={'BASE':'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6','FIVE':'c18f7640ea36647a05b39089e5293f22dd009f63','P00R':'b7d74e67dd6c603db049b1915b1afec987e3b458','P02':'d9486f113f074c185a94bcc5c0afeef12ea3574f','P03':'79dc698b99dfe866886d32376ed388e85bdd039c','P04':'620a0ac4bb11763319c4227485f6a3996b91d367','P06':'982f13d9b6c378ed9581125ecc5c40f17dade6a3'}
BASE=['data/manual/rw_routes_now.csv','data/manual/route_competitors.csv','data/manual/airport_tech.csv','data/manual/fare_offer_spotchecks.csv','data/manual/known_flows.csv','data/manual/pax_2025_overrides.csv','data/processed/demand_pairs.csv','data/processed/catchments.csv','data/external/colleagues/primary_monthly_increments.csv','data/external/colleagues/primary_seasonality_profiles.csv','data/raw/favt_airports_2007_2020.csv','data/manual/rail_schedule_spotchecks.csv','data/manual/competitor_bases.csv','data/manual/competitor_hubs.csv']
WANTED={'P02':['calendar_inventory.csv','competitor_products.csv','fare_panel.csv','market_coverage.csv','historical_demand_context.csv','historical_route_context.csv','physical_adjacent_leg_candidates.csv','ordered_itineraries.csv','season_coverage.csv','offer_monthly_coverage.csv','alternatives_contract.csv','competitor_responses.csv','source_issues.csv','clock_conflicts.csv','demand_history_coverage.csv'], 'P03':['airport_constraints.csv','existing_commitments.csv','aircraft_type_parameters.csv','fleet_observations.csv'], 'P04':['airport_coverage.csv','cost_ranges.csv','event_rate_map.csv','financial_cost_coverage.csv','assumption_ids.csv'], 'P00R':['schema_patch.csv','minimal_counterexamples.csv']}
manifest=[]
summary={}
def read(tag,path):
    raw=subprocess.check_output(['git','show',PINS[tag]+':'+path])
    manifest.append({'input_id':tag+':'+path,'commit_sha':PINS[tag],'path':path,'git_blob_sha':subprocess.check_output(['git','rev-parse',PINS[tag]+':'+path],text=True).strip(),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
    return raw
for tag in ['BASE','P00R','P02','P03','P04']:
    paths=BASE if tag=='BASE' else ['context/35_full_programme_execution_20261112/'+tag+'/'+f for f in WANTED[tag]]
    if tag=='P00R':paths+=['context/34_full_programme_plan_20261112/city_research_seed.csv']
    for path in paths:
        raw=read(tag,path)
        try: s=raw.decode('utf-8-sig')
        except UnicodeDecodeError: s=raw.decode('cp1251')
        rows=list(csv.DictReader(io.StringIO(s)))
        picked=[]
        for n,row in enumerate(rows,2):
            if not any('MRV' in str(v) or 'Минераль' in str(v) for v in row.values()):continue
            picked.append({'source_file':path,'source_commit':PINS[tag],'source_row_number':n,'source_row_sha256':hashlib.sha256(json.dumps(row,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),**row})
        out=f'inputs/{tag}_{Path(path).stem}_MRV.csv'
        if picked:
            with (ROOT/out).open('w') as f:
                w=csv.DictWriter(f,fieldnames=list(picked[0]));w.writeheader();w.writerows(picked)
        summary[tag+':'+path]={'source_rows':len(rows),'selected_rows':len(picked),'extract':out if picked else None}
        if tag in ['P03','P04'] or 'city_research_seed' in path: print(tag,path,json.dumps(picked,ensure_ascii=False)[:4500])
for tag,path in [('P06','context/35_full_programme_execution_20261112/P06/producer_contract.json'),('P06','context/35_full_programme_execution_20261112/P06/README.md'),('P03','context/35_full_programme_execution_20261112/P03/operating_rules.json'),('P04','context/35_full_programme_execution_20261112/P04/cash_rules.json')]:
    read(tag,path)
(ROOT/'source_pins.json').write_text(json.dumps({'pins':PINS,'files':manifest,'extraction_policy':'Только git show exact SHA. source_row_number — номер CSV-записи + заголовок; source_row_sha256 — канонический JSON исходной записи UTF-8 с sort_keys и compact separators. Полные чужие fixtures не копируются.','selected':summary},ensure_ascii=False,indent=2)+'\n')
print('COUNTS',json.dumps({k:v['selected_rows'] for k,v in summary.items()},ensure_ascii=False))
