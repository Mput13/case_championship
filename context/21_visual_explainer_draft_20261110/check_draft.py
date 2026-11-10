#!/usr/bin/env python3
from pathlib import Path
from html.parser import HTMLParser
import collections,csv,hashlib,json,re,subprocess
P=Path(__file__).resolve().parent;R=P.parents[1]
page=(R/'research-report-draft.html').read_text()
class Parser(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.links=[];self.sections=[];self.programs=0;self.remote=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        if tag=='a' and 'href' in a:self.links.append(a['href'])
        if tag=='section':self.sections.append(a.get('id'))
        if 'data-program' in a:self.programs+=1
        if tag in ['script','img','link'] and any(a.get(k,'').startswith('http') for k in ['src','href']):self.remote.append(a)
p=Parser();p.feed(page)
assert not [x for x,n in collections.Counter(p.ids).items() if n>1], 'duplicate IDs'
broken=[x for x in p.links if x.startswith('#') and x[1:] not in p.ids]
assert not broken,broken
assert p.programs==35
assert p.sections.index('inputs')<p.sections.index('money')<p.sections.index('screening')<p.sections.index('team-context')<p.sections.index('programs')
assert p.sections.index('archetypes')<p.sections.index('programs')
assert not p.remote
assert not re.search(r'\d+(?:d|s|l)?vh',page)
manifest=json.loads((P/'inputs_manifest.json').read_text())
for x in manifest['inputs']:assert hashlib.sha256((P/x['local']).read_bytes()).hexdigest()==x['sha256'],x['local']
protected=json.loads((P/'protected_before.json').read_text())
current_protected_hashes={f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in protected}
protection={f:current_protected_hashes[f]==h for f,h in protected.items()}
parent_receipt=P/'parent_monitoring_update.json'
allowed_monitoring={'context/16_agent_research/colleague_refs.json','context/16_agent_research/updates.jsonl'}
authorized_changes=json.loads(parent_receipt.read_text())['paths'] if parent_receipt.exists() else {}
assert set(authorized_changes)<=allowed_monitoring
accepted_protection={f:unchanged or (f in authorized_changes and authorized_changes[f]['before_sha256']==protected[f] and authorized_changes[f]['after_sha256']==current_protected_hashes[f]) for f,unchanged in protection.items()}
assert all(accepted_protection.values()),protection
cov=json.loads((P/'map_coverage.json').read_text());assert cov['geography_mapped']==35 and cov['geometry_only']==6
# Published own-product layer is checked from dated frozen rows, not inferred from absence.
services=list(csv.DictReader((P/'inputs/published-services.csv').open()))
counts={d:len([x for x in services if x['origin']=='SVX' and x['destination']==d and x['carrier']=='RED WINGS']) for d in ['OMS','REN','KUF','KZN']}
assert counts=={'OMS':2,'REN':4,'KUF':7,'KZN':7},counts
js=subprocess.check_output(['node',str(P/'check_controls.cjs')],text=True)
result=dict(result='PASS',sections=p.sections,programs=35,unique_ids=len(p.ids),internal_links=len([x for x in p.links if x.startswith('#')]),broken_links=broken,external_runtime_dependencies=p.remote,protected_files_unchanged=protection,input_sha256_verified=len(manifest['inputs']),map_coverage=cov['geography_mapped'],geometry_only=cov['geometry_only'],published_RW_counts=counts,controls=json.loads(js),not_run=['new market research','economic workflow','full model replay','live booking or commercial acceptance','publication','server','push'])
result['authorized_parent_monitoring_changes']=[f for f in protection if not protection[f] and accepted_protection[f]]
(P/'checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
qa=P/'qa';qa.mkdir(exist_ok=True)
for name,ids in {'alignment':['case-alignment'],'state':['state-and-delivery'],'study':['agent-study'],'atlas':['atlas'],'archetypes':['archetypes'],'catalog':['programs'],'screening':['screening','team-context'],'c14':['c14'],'inputs':['inputs'],'kover':['kover']}.items():
    css='main>header,main>section{display:none!important}'+','.join('main>section#'+i for i in ids)+'{display:block!important}'
    (qa/(name+'.html')).write_text(page.replace('</style>',css+'</style>',1))
print(json.dumps({'result':'PASS','programs':35,'maps':result['controls']['maps_rendered'],'input_hashes':len(manifest['inputs']),'protected':all(accepted_protection.values()),'authorized_parent_monitoring_changes':result['authorized_parent_monitoring_changes']}))
