#!/usr/bin/env python3
"""Exact input/transport and offline delivery checks; no economics are calculated."""
import base64,csv,gzip,hashlib,json,pathlib,re,subprocess
P=pathlib.Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
checks=[]
def check(name,ok):
    checks.append({'name':name,'pass':bool(ok)})
    if not ok:raise AssertionError(name)
def leaf_equal(a,b):
    if type(a)!=type(b):return False
    if isinstance(a,dict):return a.keys()==b.keys() and all(leaf_equal(a[k],b[k]) for k in a)
    if isinstance(a,list):return len(a)==len(b) and all(leaf_equal(x,y) for x,y in zip(a,b))
    return a==b
def run():
    d=json.loads((P/'dashboard_data.json').read_text());q=d['lazy_results'];m=json.loads((P/'input_manifest.json').read_text())
    for r in m['files']:
        if r.get('snapshot'):check('source bytes '+r['snapshot'],sha((P/r['snapshot']).read_bytes())==r['sha256'])
    check('20 cities and sealed dossiers',len(d['cities'])==len(d['dossiers'])==20)
    check('160 candidates /169hypotheses',sum(len(x['programmes']) for x in d['dossiers'].values())==160 and sum(len(x['hypotheses']) for x in d['dossiers'].values())==169)
    check('Source stage not substituted for accepted result',d['result_package'] is None and d['integration']['finalquantitativebinding']=='BOUND_CONDITIONAL_RESEARCH')
    check('Exact author v2 pin',json.loads((P/'inputs/author_view2/source_manifest.json').read_text())[0]['commit']=='6cbe817320f75db9823984e7c4eeb6091fd7d996')
    check('87international /128capacity /4digital',len(d['branches']['P02I']['international_market_cards.csv'])==87 and len(d['branches']['P10']['growth_cases.csv'])==128 and len(d['digital']['digital_cards.json']['cards'])==4)
    check('P10 reported metric stays unknown',all(r['actual_P09_net_reported_passengers']=='' for r in d['branches']['P10']['growth_cases.csv']))
    check('P01 helicopters separated',len(d['branches']['P01_MONTHLY']['carrier_monthly.csv'])==36 and len([r for r in d['branches']['P01_MONTHLY']['carrier_monthly.csv'] if r['aircraft_mode']=='вертолёты'])==9)
    old=json.loads((P/'inputs/P12/assumptions_register.json').read_text());check('P12 assumptions preserved',all(a in d['assumptions'] for a in old))
    check('Exact producer / approved conditional scope',q['commit']=='736859fdd08448c2564b7b9269b751abe00b5cbc' and q['manifest_sha256']=='7b20a1a247ee4b3cf96d94648bb36d61482cb0a58eb7a296ada49a78c818d1fa' and q['root_authorisation']['coordinator_acceptance']=='ACCEPTED_FOR_UI')
    check('Independent programme limits recorded',q['root_authorisation']['independent_acceptance']=='APPROVE_WITH_EXPLICIT_LIMITS')
    check('9programmes /18canonical',len(q['catalogue'])==9 and sum(len(c['evaluations']) for c in q['catalogue'])==18)
    all_leaves=0
    for card in q['catalogue']:
        pid=card['programme_id'];packet=q['packets'][pid];gz=(P/'accepted'/f'{pid}.json.gz').read_bytes();b=gzip.decompress(gz)
        check(pid+' lossless gzip/base64 hash',sha(gz)==packet['gzip_sha256'] and sha(b)==packet['sha256'] and base64.b64decode(packet['data'])==gz)
        env=json.loads(b);check(pid+' accepted own envelope / producer pending retained',env['coordinator_acceptance']=='ACCEPTED_FOR_UI' and env['producer_original_header']['coordinator_acceptance']=='PENDING_COORDINATOR_ACCEPTANCE')
        raw=subprocess.check_output(['git','show',q['commit']+':'+card['producer_path']],cwd=P.parents[2]);check(pid+' exact producer wrapper SHA',sha(raw)==card['producer_sha256']);producer=json.loads(raw)
        for i,e in enumerate(env['evaluations']):
            ctx=e['result']['project']['context'];eid=ctx['evaluation_id']
            check(eid+' every JSONleaf exact type/value/null/order',leaf_equal(e['result'],producer['evaluations'][i]['result']))
            rb=json.dumps(e['result'],ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
            check(eid+' projection receipt hash',sha(rb)==e['projection_sha256']==e['projection_meta']['projection_sha256'])
            check(eid+' canonical mode /24months',e['result_mode']=='P06_FIXED_COMPARE_CANONICAL' and len(e['result']['project']['results_monthly'])==24 and len(e['result']['delta_monthly'])==24)
            check(eid+' unknowns preserved',e['result']['delta_summary']['operating_result'] is None and e['result']['project_incremental_funding']['peak_dated_day_end'] is None and all(r['project_available'] is None for r in e['resource_monthly']))
            all_leaves+=e['projection_meta']['verified_same_path_leaves']
    overview=json.loads(gzip.decompress((P/'accepted/producer_overview.json.gz').read_bytes()))
    check('1958overview separate from canonical',len(overview['overview'])==1958 and q['overview_contract']['result_mode']=='P06_DISJOINT_DATE_COMPONENTS_WITH_ADDITIVE_P06_FINANCE')
    check('178constructs /223author dispositions',len(overview['cards'])==178 and len(overview['dispositions'])==223)
    for row in overview['overview']:
        original={k:v for k,v in row.items() if k!='_source'};ref=row['_source'];b=json.dumps(original,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        if sha(b)!=ref['row_sha256']:raise AssertionError('overview row hash')
    check('All overview row hashes exact',True)
    links=list(csv.DictReader((P/'claim_links.csv').open()));check('Claim path/hash/id/version',all(r['path'] and re.fullmatch('[a-f0-9]{64}',r['row_sha256']) and r['source_row_id'] and r['version'] for r in links))
    html=(P/'dashboard_candidate.html').read_text();check('Four sections',len(re.findall(r'<section id=',html))==4)
    check('Offline scripts/styles',not re.search(r'<script[^>]+src=|<link[^>]+rel=["\']stylesheet',html,re.I))
    check('Native renderer under25MiB',(P/'dashboard_candidate.html').stat().st_size<25*1024*1024)
    check('Transparent outer root','html,body{background:transparent!important}' in html)
    for n in ['adapter.js','app.js','stage_a.js','final.js','view2.js']:subprocess.run(['node','--check',str(P/'source'/n)],check=True)
    before={n:sha((P/n).read_bytes()) for n in ['dashboard_data.json','dashboard_candidate.html','claim_links.csv','input_manifest.json']}
    subprocess.run(['python3',str(P/'replay.py')],check=True,stdout=subprocess.PIPE)
    after={n:sha((P/n).read_bytes()) for n in before};check('Deterministic snapshot-only replay',before==after)
    result={'status':'PASS_EXACT_TRANSPORT_AND_OFFLINE_DELIVERY','checks':checks,'count':len(checks),'replay_sha256':after,'claim_links':len(links),'canonical_verified_same_path_leaves_from_receipts':all_leaves,'market_operations_acceptance':'NOT_CLAIMED','independent_P13':'APPROVE_WITH_EXPLICIT_LIMITS','independent_P16':'NOT_RUN'}
    (P/'qa/verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['checks','replay_sha256']},ensure_ascii=False))
if __name__=='__main__':run()
