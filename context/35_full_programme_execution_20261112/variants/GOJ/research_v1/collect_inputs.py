"""Read exact Git blobs; retain only GOJ rows with original row identities."""
import csv, hashlib, io, json, pathlib, subprocess

ROOT = pathlib.Path(__file__).resolve().parent
PINS = {
    'BASE':'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6',
    'FIVE':'c18f7640ea36647a05b39089e5293f22dd009f63',
    'P00R':'b7d74e67dd6c603db049b1915b1afec987e3b458',
    'P02':'d9486f113f074c185a94bcc5c0afeef12ea3574f',
    'P03':'79dc698b99dfe866886d32376ed388e85bdd039c',
    'P04':'620a0ac4bb11763319c4227485f6a3996b91d367',
    'P06':'982f13d9b6c378ed9581125ecc5c40f17dade6a3',
}
def blob(package, path):
    b = subprocess.check_output(['git','show',PINS[package]+':'+path])
    return b, {'package':package,'commit':PINS[package],'path':path,
               'git_blob':subprocess.check_output(['git','rev-parse',PINS[package]+':'+path],text=True).strip(),
               'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def relevant(row):
    return any(x in str(row) for x in ['GOJ','Нижний Новгород','Нижнего Новгорода','Нижний_Новгород'])
def collect():
    selected, manifests = {}, []
    files = {
      'BASE':('data/manual/', ['rw_routes_now.csv','route_competitors.csv','known_flows.csv','rail_schedule_spotchecks.csv','airport_tech.csv','bases.csv','network_routes.csv','longlist.csv']),
      'FIVE':('context/33_five_city_reassessment_20261112/cities/GOJ/', ['sources.csv','claims.csv','routes.csv','schedule_week.csv','schedule_observations.csv','features.csv','block_comparison.csv','listed_subsidies_2026.csv']),
      'P02':('context/35_full_programme_execution_20261112/P02/', ['competitor_products.csv','calendar_inventory.csv','fare_panel.csv','market_coverage.csv','ordered_itineraries.csv','competitor_responses.csv','historical_route_context.csv','historical_demand_context.csv','clock_conflicts.csv','alternatives_contract.csv']),
      'P03':('context/35_full_programme_execution_20261112/P03/', ['airport_constraints.csv','aircraft_type_parameters.csv']),
      'P04':('context/35_full_programme_execution_20261112/P04/', ['cost_ranges.csv','event_rate_map.csv','airport_reference_examples.csv','support_terms.csv']),
    }
    for package,(prefix,names) in files.items():
        for name in names:
            path=prefix+name
            # Some author files live outside data/manual; resolve from this exact tree.
            if package=='BASE':
                matches=[x for x in subprocess.check_output(['git','ls-tree','-r','--name-only',PINS[package],'data'],text=True).splitlines() if x.endswith('/'+name)]
                if not matches: continue
                path=matches[0]
            b,m=blob(package,path); rows=[]
            for n,row in enumerate(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))),2):
                if relevant(row) or (package=='FIVE' and name=='sources.csv'):
                    canon=json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
                    rid=next((row[k] for k in ['product_id','schedule_instance_id','claim_id','cost_id','rate_id','response_id','feature_id','market_id','source_id'] if row.get(k)),f'row:{n}')
                    rows.append({'source_row_number':n,'source_row_id':rid,'row_sha256':hashlib.sha256(canon).hexdigest(),'row':row})
            m['selected_rows']=len(rows);m['selection']='GOJ or inflection of Нижний Новгород in row; GOJ sources registry retained for local claims'
            manifests.append(m);selected[package+'/'+name]=rows
    for package,path in [
        ('FIVE','context/33_five_city_reassessment_20261112/cities/GOJ/dossier.md'),
        ('FIVE','context/33_five_city_reassessment_20261112/cities/GOJ/decision.json'),
        ('P00R','context/35_full_programme_execution_20261112/P00R/contract_addendum.json'),
        ('P06','context/35_full_programme_execution_20261112/P06/producer_contract.json'),
        ('P06','context/35_full_programme_execution_20261112/P06/README.md'),
        ('P00R','context/34_full_programme_plan_20261112/variant_research_plan.json'),
        ('P00R','context/34_full_programme_plan_20261112/common_spec.json'),
        ('P04','context/35_full_programme_execution_20261112/P04/sources/goj_tariff_20261101.pdf'),
        ('P04','context/35_full_programme_execution_20261112/P04/sources/goj_tariff_20261101.txt'),
    ]:
        b,m=blob(package,path);m['selection']='read for interpretation; full blob not copied';manifests.append(m)
        if path.endswith('/variant_research_plan.json'):
            plan=json.loads(b)
            selected['PLAN/legacy_hypotheses']=[{'source_row_number':i,'source_row_id':r['candidate_id'],'row_sha256':hashlib.sha256(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'row':r} for i,r in enumerate(plan['legacy_hypotheses'],1) if relevant(r)]
    for name,data in [('source_pins.json',{'pins':PINS,'inputs':manifests,'row_hash_recipe':'sha256 UTF8 json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(comma,colon)); source_row_number is CSV header=1; quoted multiline fields count as logical records'}),('goj_source_rows.json',selected)]:
        (ROOT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    return selected
if __name__=='__main__':
    d=collect();print(json.dumps({k:len(v) for k,v in d.items()},ensure_ascii=False))
