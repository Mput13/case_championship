#!/usr/bin/env python3
"""Evidence/display adapter. Does not calculate demand, costs, allocations or money."""
import argparse, csv, hashlib, io, json, pathlib, subprocess, re

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
PREFIX = 'context/35_full_programme_execution_20261112/'
PINS = {'P12':'06207b1650bd1c83e0f0761b25d063f2c395ace7',
        'STAGE_A':'6a6326c2dcfe32e47ec25621bda0d15fcfe48ae1',
        'P02':'d9486f113f074c185a94bcc5c0afeef12ea3574f',
        'P03':'79dc698b99dfe866886d32376ed388e85bdd039c',
        'P04':'620a0ac4bb11763319c4227485f6a3996b91d367',
        'P06':'982f13d9b6c378ed9581125ecc5c40f17dade6a3'}
def sha(b): return hashlib.sha256(b).hexdigest()
def dump(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n')
def canon(v): return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',',':'),allow_nan=False).encode()
def parse(b, name):
    if name.endswith('.csv'): return list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))
    return json.loads(b)

class Intake:
    def __init__(self,snapshot_only=False): self.files=[]; self.claims=[];self.snapshot_only=snapshot_only
    def remember(self, package, path, b, version, manifest_hash, target):
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(b)
        self.files.append(dict(package=package, path=path, sha256=sha(b), bytes=len(b),
                               version=version, manifest_sha256=manifest_hash,
                               snapshot=str(target.relative_to(HERE))))
        obj=parse(b,path)
        if isinstance(obj,list):
            obj=[self.row(package,path,r,i+2,version,sha(b)) for i,r in enumerate(obj)]
        return obj
    def row(self, package, path, row, index, version, file_hash):
        if not isinstance(row,dict): return row
        r=dict(row)
        rid=next((str(r[k]) for k in ['source_row_id','product_id','evidence_id','programme_id','hypothesis_id','request_id','market_id','source_id','card_id','assumption_id'] if r.get(k)),f'row:{index}')
        ref={'package':package,'path':path,'version':version,'file_sha256':file_hash,
             'source_row_number':index,'source_row_id':rid,'row_sha256':sha(canon(row))}
        r['_ref']=ref
        self.claims.append({**ref,'claim_id':f'{package}:{path}:{index}',
                            'url':r.get('url',r.get('source_url','UNKNOWN')),
                            'organization':r.get('organization',r.get('publisher','UNKNOWN')),
                            'as_of':r.get('as_of',r.get('retrieved_at','UNKNOWN')),
                            'period':r.get('period','UNKNOWN'),'unit':r.get('unit',r.get('units','UNKNOWN')),
                            'granularity':r.get('granularity',r.get('row_grain','source_row')),
                            'status':r.get('status','source_export'),'coverage':r.get('coverage','source_specific_incomplete'),
                            'assumption_ids':r.get('assumption_ids',r.get('assumption_id',''))})
        return r
    def git(self, package, name):
        path=PREFIX+package+'/'+name
        mpath=PREFIX+package+'/output_manifest.json'
        if self.snapshot_only:
            b=(HERE/'inputs'/package/name).read_bytes();mb=(HERE/'inputs'/package/'output_manifest.json').read_bytes()
        else:
            b=subprocess.check_output(['git','show',PINS[package]+':'+path],cwd=REPO)
            mb=subprocess.check_output(['git','show',PINS[package]+':'+mpath],cwd=REPO)
            (HERE/'inputs'/package).mkdir(parents=True,exist_ok=True);(HERE/'inputs'/package/'output_manifest.json').write_bytes(mb)
        m=json.loads(mb); expected=next((r['sha256'] for r in m['files'] if r['path']==name),None)
        if name!='output_manifest.json' and expected!=sha(b): raise ValueError(f'Git manifest mismatch {path}')
        return self.remember(package,path,b,PINS[package],sha(mb),HERE/'inputs'/package/name)
    def sealed(self, entry, names):
        path=pathlib.Path(entry['path']); root=HERE/'inputs'/entry['package']
        mf=entry.get('manifest_file','output_manifest.json')
        read=lambda name:(root/name).read_bytes() if self.snapshot_only else subprocess.check_output(['git','show',PINS['STAGE_A']+':'+str(path/name)],cwd=REPO)
        mb=read(mf)
        if sha(mb)!=entry['manifest_sha256']: raise ValueError(f'Sealed manifest changed {path}')
        m=json.loads(mb); members={r['path']:r for r in m['files']}; result={}
        (HERE/'inputs'/entry['package']).mkdir(parents=True,exist_ok=True)
        (HERE/'inputs'/entry['package']/mf).write_bytes(mb)
        for name in names:
            if name not in members: continue
            b=read(name)
            if sha(b)!=members[name]['sha256']: raise ValueError(f'Sealed member changed {path/name}')
            result[name]=self.remember(entry['package'],str(path/name),b,PINS['STAGE_A'],sha(mb),HERE/'inputs'/entry['package']/name)
        return result

CITY_FILES=['case.json','handoff.json','hypotheses.json','programme_candidates.json','readiness.json',
            'comparison_requests.csv','evidence.csv','market_deltas.csv','assumptions.csv',
            'sources.csv','sources.json','source_catalog.json','source_catalog.csv','source_metadata.csv',
            'fare_observations.csv','price_observations.csv','local_fare_panel.csv','offer_observations.csv',
            'competitor_offers.csv','competitor_offer_rows.csv','competitor_observations.csv',
            'local_schedule_offers.csv','resource_diagnostics.csv','geometric_diagnostics.csv',
            'resource_checks.json','resource_probe_results.json','resource_diagnostic.json',
            'resource_diagnostics.json','resource_screen.json','resource_summary.csv','source_index.json','connection_diagnostics.csv','source_issues.csv','source_issues.json',
            'source_conflicts.csv','data_conflicts.json','local_data_issues.json','operations_checks.json']

def val(obj, *keys):
    for k in keys:
        if obj.get(k) is not None: return obj[k]
    return None
def programme_rows(p): return p.get('programmes',p.get('candidates',[]))

def bind_projection_metadata(package,artifact_commit,intake):
    """Attach audit metadata only; result values/arrays are never mapped or recomputed."""
    if package.get('coordinator_acceptance')!='ACCEPTED_FOR_UI':raise ValueError('P09 не принят координатором для количественного UI')
    projected='PROJECTION' in package.get('result_mode','') or any('projection_sha256' in e for e in package.get('evaluations',[]))
    if not projected:return package
    def read(name):
        path=PREFIX+'P09/'+name
        b=subprocess.check_output(['git','show',artifact_commit+':'+path],cwd=REPO)
        target=HERE/'inputs/P09'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
        intake.files.append(dict(package='P09',path=path,version=artifact_commit,sha256=sha(b),bytes=len(b),snapshot=str(target.relative_to(HERE)),manifest_sha256=package['manifest_sha256']))
        return json.loads(b),sha(b)
    contract,ch=read('projection_contract.json')
    package['payload_kind']='P09_UI_PROJECTION';package['projection_contract']=contract
    package['projection_contract_artifact']={'commit':artifact_commit,'sha256':ch,'path':PREFIX+'P09/projection_contract.json'}
    for e in package['evaluations']:
        receipt,rh=read(e['audit_receipt'])
        if sha(canon(e['result']))!=e['projection_sha256'] or e['projection_sha256']!=receipt['projection_sha256']:raise ValueError('P09 projection hash mismatch')
        if e['source_full_result_sha256']!=receipt['full']['sha256'] or e['source_full_result_path']!=receipt['full']['path']:raise ValueError('P09 full result link mismatch')
        e['projection_meta']={'source_full_result_sha256':e['source_full_result_sha256'],'projection_sha256':e['projection_sha256'],'input_pins':receipt['input_manifest'],'result_mode':e['result_mode'],'audit':{'path':e['audit_receipt'],'sha256':rh,'commit':artifact_commit},'replay':{'command':contract['replay'],'audit_script':contract['audit_script'],'builder_sha256':receipt.get('builder_sha256'),'commit':artifact_commit},'full_result_artifact':receipt['full'],'verified_same_path_leaves':receipt['verified_same_path_leaves']}
    return package

def map_pairs(p,city_code=None):
    """Extract explicitly specified airport pairs or adjacent template points, not OD demand."""
    pairs=set()
    def walk(x):
        if isinstance(x,dict):
            a=val(x,'origin','origin_airport','from');b=val(x,'destination','destination_airport','to')
            if isinstance(a,str) and isinstance(b,str) and re.fullmatch('[A-Z]{3}',a) and re.fullmatch('[A-Z]{3}',b):pairs.add((a,b))
            for v in x.values():walk(v)
        elif isinstance(x,list):
            if len(x)>1 and all(isinstance(v,str) and re.fullmatch('[A-Z]{3}',v) for v in x):pairs.update(zip(x,x[1:]))
            else:
                for v in x:walk(v)
        elif isinstance(x,str):
            pairs.update(re.findall(r'(?=\b([A-Z]{3})[>–—→:-]([A-Z]{3})\b)',x))
    for k in ['airport_pairs','unique_airport_pairs','programme_airport_pairs','target_airport_pairs','legs','routes','flight_changes','patterns','pattern','flight_pattern','rotation_templates','rotation_paths','flights','flight_rules','route_changes']:
        walk(p.get(k))
    if city_code and isinstance(p.get('flight_pattern'),dict):
        pairs.update((city_code,k) for k in p['flight_pattern'] if re.fullmatch('[A-Z]{3}',k))
    return [dict(origin=a,destination=b,status='RESEARCH_TEMPLATE_NOT_ACCEPTED_FLIGHT') for a,b in sorted(pairs) if a!=b]

def build(extra_intake=None, results_commit=None, results_path=None,snapshot_only=False):
    intake=Intake(snapshot_only)
    # Exact P12 data is the author-component and geographic basis, not a financial model.
    p12path=PREFIX+'P12/ui_candidate/data/source_data.json'
    b=(HERE/'inputs/P12/source_data.json').read_bytes() if snapshot_only else subprocess.check_output(['git','show',PINS['P12']+':'+p12path],cwd=REPO)
    p12m=(HERE/'inputs/P12/output_manifest.json').read_bytes();expected=next(r['sha256'] for r in json.loads(p12m)['files'] if r['path']=='ui_candidate/data/source_data.json')
    if sha(b)!=expected:raise ValueError('P12 source data snapshot mismatch')
    intake.files.append(dict(package='P12',path=p12path,sha256=sha(b),bytes=len(b),version=PINS['P12'],manifest_sha256=sha(p12m),snapshot='inputs/P12/source_data.json'))
    pending_contract=HERE/'inputs/P09/projection_contract_pending.json'
    cb=pending_contract.read_bytes();ch=sha(cb)
    if ch!='d721896cdc4193b9e2a70bd54a25baaedd00db0e967a711c5a359d424b0c1e7d':raise ValueError('Pending P09 contract hash changed')
    intake.files.append(dict(package='P09_CONTRACT_ONLY_PENDING',path=PREFIX+'P09/projection_contract.json',sha256=ch,bytes=len(cb),version='FILE_SHA256:'+ch,manifest_sha256=None,snapshot='inputs/P09/projection_contract_pending.json',acceptance='CONTRACT_ONLY_NOT_QUANTITATIVE_ACCEPTANCE'))
    d=json.loads(b); d['version']='P15-stageA-v2-root20'; d['pins'].update(PINS)
    d['release'].update(P06='IMPLEMENTED_CONDITIONAL_ENGINE_INDEPENDENT_ACCEPTANCE_PENDING',P03='DATED_DEC2028_DIAGNOSTIC_NOT_ANNUAL_OR_FREE_RW_FLEET',P09='FINAL_QUANTITATIVE_BINDING_OPEN')
    d['P12_source_sha256']=sha(b);d['dossiers']={}; d['branches']={};d['branch_manifests']={};d['result_package']=None
    products=intake.git('P02','competitor_products.csv')
    d['products']=products;d['summary']=intake.git('P02','build_summary.json')
    coverage=intake.git('P02','city_coverage.csv')
    for c in d['cities']:
        r=next(r for r in coverage if r['city']==c['iata'])
        c.update(partial=int(r['partially_evidenced_outbound_markets']),markets=int(r['required_outbound_markets']),
                 uncovered=int(r['uncovered_outbound_markets']),source_refs=[r['_ref']],stage_A='NOT_SEALED')
    d['clock_conflicts']=intake.git('P02','clock_conflicts.csv')
    d['physical_boundaries']=intake.git('P02','physical_adjacent_leg_candidates.csv')
    # No conversion from marketing products to seats is performed.
    seal=json.loads((HERE/'inputs/sealed_intake.json').read_text())
    entries=list(seal['packages'])
    if extra_intake:
        extra=json.loads(pathlib.Path(extra_intake).read_text());specs={e['path'].rstrip('/'):e for e in extra['packages']}
        rootpaths={e['path'].rstrip('/') for e in entries}
        merged=[]
        for e in entries:
            spec=specs.get(e['path'].rstrip('/'))
            if spec:
                if e['manifest_sha256']!=spec['manifest_sha256']:raise ValueError('Root intake/config manifest differs')
                e={**e,**spec,'status':e['status']}
            merged.append(e)
        entries=merged+[e for e in extra['packages'] if e['path'].rstrip('/') not in rootpaths]
    seen=set()
    for entry in entries:
        if entry['package'] in seen: continue
        seen.add(entry['package'])
        if entry['package'].startswith('P07-'):
            code=pathlib.Path(entry['path']).parts[-2]
            raw=intake.sealed(entry,CITY_FILES)
            c=raw['case.json']; pr=raw['programme_candidates.json'];hy=raw['hypotheses.json']
            ref=lambda name:next(f for f in intake.files if f['package']==entry['package'] and f['path'].endswith('/'+name))
            programmes=[intake.row(entry['package'],ref('programme_candidates.json')['path'],r,i+1,PINS['STAGE_A'],ref('programme_candidates.json')['sha256']) for i,r in enumerate(programme_rows(pr))]
            for p in programmes:p['_map_pairs']=map_pairs(p,code)
            hypotheses=[intake.row(entry['package'],ref('hypotheses.json')['path'],r,i+1,PINS['STAGE_A'],ref('hypotheses.json')['sha256']) for i,r in enumerate(hy['hypotheses'])]
            dossier={'manifest_sha256':entry['manifest_sha256'],'case':c,'handoff':raw.get('handoff.json'),
                     'readiness':raw.get('readiness.json'),'programmes':programmes,'hypotheses':hypotheses,
                     'comparisons':raw.get('comparison_requests.csv',[]),'evidence':raw.get('evidence.csv',[]),
                     'markets':raw.get('market_deltas.csv',[]),'programme_policy':{k:v for k,v in pr.items() if k not in ['programmes','candidates']},
                     'fares':[], 'sources':[], 'resource_diagnostics':{}, 'source_conflicts':{}}
            for name,rows in raw.items():
                if name in ['sources.csv','sources.json','source_catalog.json','source_catalog.csv','source_metadata.csv','source_index.json']: dossier['sources'].append({'file':name,'records':rows})
                if name in ['fare_observations.csv','price_observations.csv','local_fare_panel.csv','offer_observations.csv']:dossier['fares']+=rows
                if 'resource_' in name or 'geometric_' in name or name=='operations_checks.json':dossier['resource_diagnostics'][name]=rows
                if any(k in name for k in ['conflict','issues']):dossier['source_conflicts'][name]=rows
            d['dossiers'][code]=dossier
            for city in d['cities']:
                if city['iata']==code:city['stage_A']='SEALED_RESEARCH_NOT_ECONOMIC_ACCEPTANCE'
            d['assumptions']+=raw.get('assumptions.csv',[])
        elif entry['package']=='P11':
            d['digital']=intake.sealed(entry,['digital_cards.json','source_claims.json','source_rows.csv','source_manifest.json','assumptions_register.json','funnel_and_economics.json','counterexamples.json','P09_integration_contract.json'])
            d['assumptions']+=d['digital'].get('assumptions_register.json',[])
        elif entry['package'] in ['P08-SVX','P08-MOSCOW','P02I','P10','P01_MONTHLY']:
            # Coordinator's explicit sealed intake names only; never discover moving output files.
            names=entry.get('ui_files',[])
            if not names: raise ValueError(f"Need explicit ui_files for {entry['package']}")
            branch=intake.sealed(entry,names)
            for name,obj in list(branch.items()):
                if isinstance(obj,dict):
                    f=next(f for f in intake.files if f['package']==entry['package'] and f['path'].endswith('/'+name))
                    for key in ['programmes','hypotheses','cards']:
                        if isinstance(obj.get(key),list):obj[key]=[intake.row(entry['package'],f['path'],r,i+1,PINS['STAGE_A'],f['sha256']) for i,r in enumerate(obj[key])]
                if 'assumptions' in name:
                    assumptions=obj if isinstance(obj,list) else obj.get('assumptions',[]) if isinstance(obj,dict) else []
                    d['assumptions']+=assumptions
            d['branches'][entry['package']]=branch
            d['branch_manifests'][entry['package']]=dict(path=entry['path'],manifest_sha256=entry['manifest_sha256'],status=entry.get('status','SEALED_RESEARCH'))
    if results_commit or results_path:
        if not results_commit or not results_path or not re.fullmatch('[a-f0-9]{40}',results_commit):raise ValueError('Exact 40hex results commit and path required')
        b=subprocess.check_output(['git','show',results_commit+':'+results_path],cwd=REPO)
        result=json.loads(b)
        # Artifact commit and producer payload commit may differ: never require a self-referential Git SHA.
        result=bind_projection_metadata(result,results_commit,intake)
        subprocess.run(['node',str(HERE/'validate_result.cjs')],input=canon(result),check=True,cwd=HERE,stdout=subprocess.PIPE)
        d['result_package']=result
        d['result_artifact_pin']={'commit':results_commit,'path':results_path,'sha256':sha(b)}
        (HERE/'inputs/P09').mkdir(exist_ok=True);(HERE/'inputs/P09/result_package.json').write_bytes(b)
        dump(HERE/'inputs/P09/ui_envelope_bound.json',result)
        intake.files.append(dict(package='P09',path=results_path,sha256=sha(b),version=results_commit,manifest_sha256=result['manifest_sha256']))
    d['integration']={'sealed_cities':list(d['dossiers']),
                      'pending_cities':[c['iata'] for c in d['cities'] if c['iata'] not in d['dossiers']],
                      'finalquantitativebinding':'BOUND' if d['result_package'] else 'OPEN',
                      'P16_actual_full_results_rehearsal':'NOT_RUN',
                      'root_intake_snapshot_sha256':sha((HERE/'inputs/sealed_intake.json').read_bytes())}
    d['assumptions']+=json.loads((HERE/'assumptions_register.json').read_text())
    # Unique registry key is package + ID; retain original IDs as authored.
    dump(HERE/'dashboard_data.json',d);dump(HERE/'input_manifest.json',{'files':intake.files,'boundary':'Selected sealed source rows only; no entire foreign fixture/archive copied.'})
    with (HERE/'claim_links.csv').open('w',newline='') as f:
        keys=list(intake.claims[0]);w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
        for r in intake.claims:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()})
    css='\n'.join((HERE/'source'/n).read_text() for n in ['author-components.css','app.css'])
    code='\n'.join((HERE/'source'/n).read_text() for n in ['adapter.js','app.js','stage_a.js'])
    html=(HERE/'source/template.html').read_text().replace('/* CSS */',css).replace('/* DATA */',json.dumps(d,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')).replace('/* CODE */',code)
    (HERE/'dashboard_candidate.html').write_text(html)
    dump(HERE/'integration_coverage.json',{'data':d['integration'],'counts':{'products':len(products),'city_programmes':sum(len(x['programmes']) for x in d['dossiers'].values()),'city_hypotheses':sum(len(x['hypotheses']) for x in d['dossiers'].values()),'evidence_rows':sum(len(x['evidence']) for x in d['dossiers'].values()),'claim_links':len(intake.claims),'clock_conflicts':len(d['clock_conflicts'])},
         'sections':{'hubs':'sealed cases/hypotheses/controls/markets, all20 hubs and mapped endpoints','direct':'P02 source products and local fare restrictions; P08/P02I only when sealed','network':'source-stage specification/resource pairs; P09 results only from pinned accepted package','strategy':'P11 real policies and test mechanisms; P10 capacity separated from reported passengers'},
         'not_claimed':['operational PASS','economic winner','physical seat admission','2028 observed network','integrated market share','P16 acceptance']})
    print(json.dumps(d['integration'],ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--extra-intake');p.add_argument('--results-commit');p.add_argument('--results-path');p.add_argument('--snapshot-only',action='store_true');a=p.parse_args()
    build(a.extra_intake,a.results_commit,a.results_path,a.snapshot_only)
