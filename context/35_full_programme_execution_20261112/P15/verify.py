#!/usr/bin/env python3
"""Source integrity and offline delivery checks. Not economic/operational acceptance."""
import csv,hashlib,json,pathlib,re,subprocess
P=pathlib.Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
checks=[]
def check(name,ok):
    checks.append({'name':name,'pass':bool(ok)})
    if not ok: raise AssertionError(name)
def run():
    d=json.loads((P/'dashboard_data.json').read_text());m=json.loads((P/'input_manifest.json').read_text())
    for r in m['files']:
        if r.get('snapshot'):check('source bytes '+r['snapshot'],sha((P/r['snapshot']).read_bytes())==r['sha256'])
    check('20 city domain',len(d['cities'])==20)
    check('20 sealed dossiers',len(d['dossiers'])==20)
    check('No economic substitute',d['result_package'] is None and d['evaluations']==[] and d['integration']['finalquantitativebinding']=='OPEN')
    check('160 authored candidates',sum(len(x['programmes']) for x in d['dossiers'].values())==160)
    check('169 explicit hypothesis records',sum(len(x['hypotheses']) for x in d['dossiers'].values())==169)
    check('87 international cards',len(d['branches']['P02I']['international_market_cards.csv'])==87)
    check('128 capacity scenarios keep actual metric unknown',len(d['branches']['P10']['growth_cases.csv'])==128 and all(r['actual_P09_net_reported_passengers']=='' for r in d['branches']['P10']['growth_cases.csv']))
    check('P01 fixed-wing separates 9 helicopter rows',len(d['branches']['P01_MONTHLY']['carrier_monthly.csv'])==36 and len([r for r in d['branches']['P01_MONTHLY']['carrier_monthly.csv'] if r['aircraft_mode']=='вертолёты'])==9)
    check('P11 no commercial revenue assumed',len(d['digital']['digital_cards.json']['cards'])==4)
    old=json.loads((P/'inputs/P12/assumptions_register.json').read_text())
    check('P12 assumptions preserved',all(a in d['assumptions'] for a in old))
    links=list(csv.DictReader((P/'claim_links.csv').open()))
    check('All claim rows have source path/hash/id/version',all(r['path'] and re.fullmatch('[a-f0-9]{64}',r['row_sha256']) and r['source_row_id'] and r['version'] for r in links))
    html=(P/'dashboard_candidate.html').read_text()
    check('Four sections retained',len(re.findall(r'<section id=',html))==4)
    check('Offline scripts/styles',not re.search(r'<script[^>]+src=|<link[^>]+rel=["\']stylesheet',html,re.I))
    check('Transparent outer body','body{margin:0;background:transparent}' in html)
    check('Root-approved projection contract',json.loads((P/'ui_contract.json').read_text())['root_approval'].startswith('Q-P09-UI01'))
    for file in ['app.js','adapter.js','stage_a.js']:subprocess.run(['node','--check',str(P/'source'/file)],check=True)
    before={n:sha((P/n).read_bytes()) for n in ['dashboard_data.json','dashboard_candidate.html','claim_links.csv','input_manifest.json']}
    subprocess.run(['python3',str(P/'replay.py')],check=True,stdout=subprocess.PIPE)
    after={n:sha((P/n).read_bytes()) for n in before}
    check('Deterministic snapshot-only replay',before==after)
    result={'status':'PASS_SOURCE_INTEGRITY_AND_OFFLINE_DELIVERY_ONLY','checks':checks,'count':len(checks),'replay_sha256':after,'claim_links':len(links),'economic_acceptance':'NOT_RUN','actual_P09_import':'NOT_RUN','P16':'NOT_RUN'}
    (P/'qa/verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['checks','replay_sha256']},ensure_ascii=False))
if __name__=='__main__':run()
