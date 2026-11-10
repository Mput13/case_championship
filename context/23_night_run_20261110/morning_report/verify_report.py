#!/usr/bin/env python3
from pathlib import Path
import re,json,math,subprocess,hashlib
from html.parser import HTMLParser
P=Path(__file__).resolve().parent
s=(P/'morning-report.html').read_text();data=json.loads((P/'report_data.json').read_text())
class Parse(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.anchors=[];self.programs=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id' in a:self.ids.append(a['id'])
  if a.get('href','').startswith('#'):self.anchors.append(a['href'][1:])
  if 'data-program' in a:self.programs.append(a['data-program'])
p=Parse();p.feed(s)
assert len(p.ids)==len(set(p.ids));assert set(p.anchors)<=set(p.ids)
assert set(p.programs)=={'C%02d'%i for i in range(1,36)}
assert not re.search(r'\d+(?:dvh|vh)\b|height:\s*100%',s)
assert not re.search(r'<(?:script|link)[^>]+(?:src|href)=',s)
assert '/Users/' not in s
m=json.loads(re.search(r'<script id="map-data" type="application/json">(.*?)</script>',s,re.S)[1].replace('<\\/','</'))
assert 'MOW' not in m['airports']
for k,mp in m['maps'].items():
 assert not mp['missing'],(k,mp['missing'])
 for c in {c for path in mp['paths'] for c in path}:
  a=m['airports'][c];assert -180<=a['lon']<=180 and -90<=a['lat']<=90
checks=[]
for r in data['common_rows']:
 n=lambda k:float(r[k])
 assert math.isclose(n('incremental_revenue'),n('gross_revenue')-n('foregone_RW_revenue'),abs_tol=.001)
 assert math.isclose(n('contribution_before_base_fleet_opportunity'),n('incremental_revenue')-n('new_pax_variable')+n('saved_old_pax_variable')-n('flight_variable_cost'),abs_tol=.001)
 assert n('contribution_before_base_fleet_opportunity')<0
 checks.append(r['network']+'/'+r['scenario']+'/'+r['recipe'])
# Compile exact inline JS and render every geographic map with a minimal data-only DOM.
scripts=re.findall(r'<script>(.*?)</script>',s,re.S);js=scripts[-1];prefix=js[:js.index("document.querySelectorAll('[data-map]')")]
node='const document={getElementById:()=>({textContent:'+json.dumps(json.dumps(m,ensure_ascii=False))+'})};\n'+prefix+"\nfor (const id of Object.keys(DATA.maps)){const svg=renderMap(id);if(!svg.includes('<svg')||svg.includes('NaN')||svg.includes('undefined'))throw new Error(id);};console.log('ALL_MAPS_RENDER_PASS '+Object.keys(DATA.maps).length);"
result=subprocess.run(['node','-e',node],capture_output=True,text=True) if len(node)<100000 else subprocess.run(['node'],input=node,capture_output=True,text=True)
assert result.returncode==0,result.stderr
subprocess.run(['node','--check'],input=js,text=True,check=True,capture_output=True)
out={'static':'PASS','anchors':len(p.anchors),'unique_ids':len(p.ids),'programs':35,'maps':len(m['maps']),'geography':'Natural Earth frozen; real airport coordinates; no MOW point','common_arithmetic_rows':len(checks),'js_compile':'PASS','all_map_render':result.stdout.strip(),'economic_replay':'NOT_RUN','source_research':'NOT_RUN','html_sha256':hashlib.sha256(s.encode()).hexdigest()}
(P/'checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
# Native preview-only runtime assertions; final file stays unchanged.
qa=P/'qa-map.html';q=qa.read_text();instrument='''<script>
const failures=[];function check(x,m){if(!x)failures.push(m);}
for(const id of Object.keys(DATA.maps)){setSelection(id);check(document.querySelector('#selected-map svg')?.dataset.mapId===id,'selection '+id);}
setSelection('C01');const tb=document.getElementById('toc-toggle');tb.click();check(tb.getAttribute('aria-expanded')==='true','toc open');tb.click();check(tb.getAttribute('aria-expanded')==='false','toc close');
const map=document.querySelector('[data-map] .map-canvas');const z=map.previousElementSibling?.querySelector('button');if(z){z.click();check(map.querySelector('svg').style.minWidth==='800px','zoom');map.previousElementSibling.querySelectorAll('button')[1].click();}
check(document.documentElement.scrollWidth<=window.innerWidth+1,'outer overflow');console.log('REPORT_UI_QA '+JSON.stringify({selections:Object.keys(DATA.maps).length,toc:true,zoom:true,failures}));if(failures.length)throw new Error(failures.join(';'));
</script>'''
qa.write_text(q.replace('</body>',instrument+'</body>'))
