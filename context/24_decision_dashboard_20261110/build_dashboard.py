#!/usr/bin/env python3
"""Reproducible offline presentation of pinned runs. No source model mutation."""
from pathlib import Path
import subprocess, json, csv, io, re, hashlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
NIGHT = 'context/23_night_run_20261110/'
WRITER = '9eb06a3206e477565e1a97ecfe5b9b63e975694e'
METHODS = 'a77e4cfbd14e560d26407479b7252cfcb15f4f41'
NASTYA = 'b91e0672af396bacd91651abeff8732fa733859d'
manifest = []

def read(sha, path):
    b = subprocess.check_output(['git', 'show', sha + ':' + path], cwd=ROOT)
    manifest.append(dict(commit=sha, path=path, sha256=hashlib.sha256(b).hexdigest(), bytes=len(b),
                         url='https://github.com/Mput13/case_championship/blob/'+sha+'/'+path))
    return b.decode()

def rows(sha, path):
    return list(csv.DictReader(io.StringIO(read(sha, path))))

def method(name):
    return rows(METHODS, NIGHT+'methods/'+name)

report = json.loads(read(WRITER, NIGHT+'morning_report/report_data.json'))
html = read(WRITER, NIGHT+'morning_report/morning-report.html')
maps = json.loads(re.search(r'<script id="map-data" type="application/json">(.*?)</script>', html, re.S)[1])
data = dict(report)
data.update({
    'portfolio': method('runs/portfolio_v2/summary.csv'),
    'budget': method('runs/final_variants_v1/budget_conditions.csv'),
    'affine': method('runs/common_demand_v1/affine_regions.csv'),
    'boundaries': method('runs/common_demand_v1/recipe_rank_boundaries.csv'),
    'kover': method('runs/kover_demand_v1/summary.csv'),
    'overlay': method('runs/kover_accounting_v1/context21_overlay.csv'),
    'rankings': {key: rows(NASTYA, 'data/processed/'+file) for key, file in [
        ('500', 'longlist_scores_min500.csv'), ('none', 'longlist_scores.csv'),
        ('strict', 'longlist_scores_min500_strict.csv')]},
    'nastya_network': rows(NASTYA, 'data/processed/network_summary.csv'),
    'nastya_routes': rows(NASTYA, 'data/processed/network_routes.csv'),
    'pins': {'writer': WRITER, 'methods': METHODS, 'nastya': NASTYA,
             'review': 'a782ebc8699bdaa456c121932ff9aa3d0f47fbe4',
             'late_review': '60109f632e7f2edd05d1b1e202ce83f404457c3b'},
})

# Build geographic unions from explicit model pair lists, never by adding KPIs.
for r in report['finite_networks']:
    key = r['portfolio']
    pairs = [p.split('-') for p in r['airport_pairs'].split(';')]
    missing = sorted({c for p in pairs for c in p if c not in maps['airports']})
    maps['maps']['P_'+key] = dict(id='P_'+key, title=key, paths=pairs, edges=pairs,
        bases=sorted({c for component in key.split('+') for c in maps['maps'][component]['bases']}),
        status='МОДЕЛЬНЫЙ СОСТАВ', kind='proposed', missing=missing,
        note='Модельные пары; геометрия не подтверждает расписание и доступность самолётов.')

for key, ranks in data['rankings'].items():
    points = [[r['iata']] for r in ranks[:3]]
    maps['maps']['R_'+key] = dict(id='R_'+key, title='Тройка городов', paths=points,
        edges=[], bases=[], status='СКРИНИНГ', kind='proposed',
        missing=[p[0] for p in points if p[0] not in maps['airports']],
        note='Города-кандидаты, не утверждённые базы.')

for summary in data['nastya_network']:
    hub=summary['hub'] or 'DIRECT';scenario=summary['scenario']
    route_rows=[r for r in data['nastya_routes'] if r['scenario']==scenario and
                (r['variant'].startswith('Прямые') if hub=='DIRECT' else r['variant']=='Хаб '+hub)]
    pairs=sorted({tuple(sorted([r['from'],r['to']])) for r in route_rows})
    known=[list(pair) for pair in pairs if all(c in maps['airports'] for c in pair)]
    missing=[list(pair) for pair in pairs if any(c not in maps['airports'] for c in pair)]
    key='AUTHOR_'+scenario+'_'+hub
    maps['maps'][key]=dict(id=key,title=summary['variant'],paths=known,edges=known,
        bases=[hub] if hub in maps['airports'] else [],status='АВТОРСКАЯ МОДЕЛЬ',kind='proposed',missing=[],
        unplaced=missing,all_model_pairs=len(pairs),note='География известной части авторской модели b91. MOW — агрегат Москвы, без фиктивной аэропортовой точки.')

original_maps = read('d8ea350a0388d35f5b559f65a57109d862d2eb85', NIGHT+'report_assets/maps.js')
renderer = original_maps[:original_maps.index('function setSelection')]
# Only style integration; retain projection, geographic scale and label algorithm.
renderer = renderer.replace('fill="#f8fbfb"', 'fill="var(--map-water)"').replace('stroke="#47676c"','stroke="var(--muted)"')

data['sources'] = manifest
encoded = lambda d: json.dumps(d, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
page = (HERE/'template.html').read_text().replace('/* DASHBOARD_CSS */', (HERE/'dashboard.css').read_text())
page = page.replace('<!-- DASHBOARD_DATA -->', '<script id="dashboard-data" type="application/json">'+encoded(data)+'</script><script id="map-data" type="application/json">'+encoded(maps)+'</script>')
page = page.replace('/* MAP_RENDERER */', renderer).replace('/* DASHBOARD_JS */', (HERE/'dashboard.js').read_text())
(ROOT/'decision-dashboard.html').write_text(page)
(HERE/'data.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
(HERE/'source_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
out = {'artifact':'decision-dashboard.html','sha256':hashlib.sha256(page.encode()).hexdigest(),
       'sources':len(manifest),'network_rows':len(data['portfolio']),'hypotheses':len(data['inventory35']),
       'economic_model_replay':'NOT_RUN; UI evaluates pinned affine functions only',
       'source_models_changed':False,'public_site_changed':False}
(HERE/'build_manifest.json').write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(out, ensure_ascii=False))
