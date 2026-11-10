#!/usr/bin/env python3
"""Read exact Git inputs, write reviewer evidence in this directory only."""
from pathlib import Path
from html.parser import HTMLParser
import subprocess, json, hashlib, re, csv, io, math, datetime

OUT = Path(__file__).resolve().parent
BASE = 'context/23_night_run_20261110/'
SCOPE = BASE + 'morning_report/'
SUBJECT = '9eb06a3206e477565e1a97ecfe5b9b63e975694e'
METHODS = 'a77e4cfbd14e560d26407479b7252cfcb15f4f41'
ROOT = 'd8ea350a0388d35f5b559f65a57109d862d2eb85'
observed = []
checks = []
def read(sha, path):
    b = subprocess.check_output(['git', 'show', sha + ':' + path])
    observed.append(dict(commit=sha, path=path, sha256=hashlib.sha256(b).hexdigest(), bytes=len(b)))
    return b
def check(name, condition, detail=None):
    checks.append(dict(name=name, status='PASS' if condition else 'FAIL', detail=detail))
def rows(b):
    return list(csv.DictReader(io.StringIO(b.decode())))

html_bytes = read(SUBJECT, SCOPE + 'morning-report.html')
s = html_bytes.decode()
d = json.loads(read(SUBJECT, SCOPE + 'report_data.json'))
manifest = json.loads(read(SUBJECT, SCOPE + 'sources_manifest.json'))
for x in manifest['inputs']:
    b = read(x['commit'], x['path'])
    check('input_hash:' + x['path'], hashlib.sha256(b).hexdigest() == x['sha256'] and len(b) == x['bytes'])
check('subject_html_sha256', hashlib.sha256(html_bytes).hexdigest() == '8f7ed280f2c255d7690170194ab81ae6c0209096d2225fc38f7bc22ad48486f2')
check('root_delivery_byte_identical', Path('morning-report.html').read_bytes() == html_bytes)
for key, sha, path in [
    ('common_rows', ROOT, BASE+'checkpoint_0800/common_comparison.csv'),
    ('inventory35', ROOT, BASE+'integration/hypothesis_frontier/519998ed/inventory35.csv'),
    ('finite_networks', METHODS, BASE+'methods/runs/final_variants_v1/network_union.csv'),
    ('requirements', ROOT, BASE+'integration/passport_bridge/46fd52db/requirements_evidence.csv'),
    ('claims', ROOT, BASE+'integration/passport_bridge/46fd52db/claims.csv'),
    ('competitors', ROOT, BASE+'integration/passport_bridge/46fd52db/competitor_and_svx_gaps.csv')]:
    check('exact_data_transfer:'+key, d[key] == rows(read(sha,path)), len(d[key]))
check('methods_root_projection_exact', read(ROOT,BASE+'integration/methods/a77e4cfb/handoff_compact.md') == read(METHODS,BASE+'methods/handoff_compact.md'))

class Parse(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids=[]; self.anchors=[]; self.programs=[]; self.runtime=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if 'id' in a: self.ids.append(a['id'])
        if a.get('href','').startswith('#'): self.anchors.append(a['href'][1:])
        if 'data-program' in a: self.programs.append(a['data-program'])
        if tag=='script' and 'src' in a: self.runtime.append(a['src'])
p=Parse(); p.feed(s)
check('unique_ids', len(p.ids)==len(set(p.ids)),len(p.ids))
check('anchors_resolve', set(p.anchors)<=set(p.ids),len(p.anchors))
check('all_35_programs_once', sorted(p.programs)==['C%02d'%i for i in range(1,36)])
check('no_external_script', not p.runtime)
check('no_email_or_local_home', not re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|/Users/|/home/',s))
m=json.loads(re.search(r'<script id="map-data" type="application/json">(.*?)</script>',s,re.S)[1].replace('<\\/','</'))
check('MOW_has_no_airport_point', 'MOW' not in m['airports'])
for k,mp in m['maps'].items():
    codes={c for path in mp['paths'] for c in path}
    check('geography:'+k, not mp['missing'] and all(c in m['airports'] and -180<=m['airports'][c]['lon']<=180 and -90<=m['airports'][c]['lat']<=90 for c in codes))
for k in ['C01','C07','C08','C23','C27','C35','H_UFA_4']:
    (OUT/('route_'+k+'.json')).write_text(json.dumps(m['maps'][k],ensure_ascii=False,indent=2)+'\n')
check('C01_distinct_from_fixed_H4', m['maps']['C01']['edges']!=m['maps']['H_UFA_4']['edges'])
check('C07_full_round_trip',m['maps']['C07']['paths']==[['SVX','OMS','KJA','OMS','SVX']])
check('C08_ZIA_not_MOW',m['maps']['C08']['paths']==[['ZIA','ARH','MRV','ZIA']])
check('C27_ground_geometry',m['maps']['C27']['kind']=='geometry' and 'Дорога' in m['maps']['C27']['note'])
for r in d['common_rows']:
    n=lambda k:float(r[k])
    ok=math.isclose(n('incremental_revenue'), n('gross_revenue')-n('foregone_RW_revenue'),abs_tol=.001)
    ok=ok and math.isclose(n('contribution_before_base_fleet_opportunity'),n('incremental_revenue')-n('new_pax_variable')+n('saved_old_pax_variable')-n('flight_variable_cost'),abs_tol=.001)
    check('common_identity:'+r['network']+'/'+r['scenario']+'/'+r['recipe'],ok)
check('common_period_price_tax',len({(r['period_start'],r['period_end'],r['price_basis'],r['tax_basis']) for r in d['common_rows']})==1)
by={(r['network'],r['scenario'],r['recipe']):float(r['contribution_before_base_fleet_opportunity']) for r in d['common_rows']}
dc=by['D_SVX8','base','C']-by['H_UFA_4','base','C']; dn=by['D_SVX8','base','N']-by['H_UFA_4','base','N']
check('common_endpoint_order_changes',dc<0<dn)
boundary=read(METHODS,BASE+'methods/runs/common_demand_v1/recipe_rank_boundaries.csv').decode()
check('alpha_transferred_from_exact_upstream','0.683509' in boundary and '0,683509' in s)
check('five_model_gate_sets',sum(r['joint_model_gates_pass']=='True' for r in d['finite_networks'])==5)
js=re.findall(r'<script>(.*?)</script>',s,re.S)[-1]
r=subprocess.run(['node','--check'],input=js,text=True,capture_output=True)
check('inline_JS_compile',r.returncode==0,r.stderr)
prefix=js[:js.index("document.querySelectorAll('[data-map]')")]
probe='const document={getElementById:()=>({textContent:'+json.dumps(json.dumps(m,ensure_ascii=False))+'})};\n'+prefix+"\nfor(const id of Object.keys(DATA.maps)){const v=renderMap(id);if(!v.includes('<svg')||v.includes('NaN')||v.includes('undefined'))throw new Error(id);}console.log(Object.keys(DATA.maps).length);"
r=subprocess.run(['node'],input=probe,text=True,capture_output=True)
check('all_map_renderer_strings',r.returncode==0,dict(stdout=r.stdout.strip(),stderr=r.stderr))
for token in ['дефект интервалов ранга при точных ничьих','Исправленный погодный знаменатель не доказывает операционный эффект','Четыре delay-случая остаются HOLD / NULL','Старые local-first пороги не перенесены на LP','Это не утверждение о прибыли компании']:
    check('explicit_qualification:'+token,token in s)
result=dict(subject=SUBJECT, completed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), checks=checks, failed=sum(x['status']=='FAIL' for x in checks), personal_visual='NOT_RUN; root native1200/390 supplied upstream', economic_replay='NOT_RUN', alpha_recalculation='NOT_RUN; endpoint money interpolation is invalid with changing seat allocation and was removed from reviewer probe; exact boundary CSV transfer checked', source_research='NOT_RUN', operating_acceptance='NOT_RUN')
(OUT/'checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(OUT/'source_manifest.json').write_text(json.dumps(observed,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(checks=len(checks),failed=result['failed']),ensure_ascii=False))
raise SystemExit(bool(result['failed']))
