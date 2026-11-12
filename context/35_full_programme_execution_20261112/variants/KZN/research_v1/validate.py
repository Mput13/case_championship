"""Самопроверка целостности/происхождения Stage A, не независимая приёмка."""
import csv,hashlib,io,json,subprocess
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime
ROOT=Path(__file__).resolve().parent
def h(b):return hashlib.sha256(b).hexdigest()
def load(n):return json.loads((ROOT/n).read_text())
def rows(n):return list(csv.DictReader((ROOT/n).open()))
checks=[]
def check(name,ok,detail):
    checks.append(dict(check=name,status='PASS' if ok else 'FAIL',detail=detail))
required=['case.json','evidence.csv','market_deltas.csv','hypotheses.json','programme_candidates.json','comparison_requests.csv','assumptions.csv','readiness.json','handoff.json']
check('Обязательные выходы',all((ROOT/x).is_file() for x in required),required)
json_files=[];csv_files=[]
for f in ROOT.rglob('*'):
    if f.suffix=='.json' and f.name not in ['output_manifest.json','validation.json']:json.loads(f.read_text());json_files.append(str(f.relative_to(ROOT)))
    if f.suffix=='.csv':
        with f.open() as inp:
            rr=list(csv.DictReader(inp));assert all(None not in r for r in rr),str(f)
        csv_files.append(str(f.relative_to(ROOT)))
check('JSON/CSV читаются',True,dict(json_count=len(json_files),csv_count=len(csv_files)))
manifest=load('input_manifest.json');cache={}
for f in manifest['files']:
    raw=subprocess.check_output(['git','show',f['commit']+':'+f['path']]);assert h(raw)==f['sha256'],f
    cache[f['commit']+':'+f['path']]=raw
check('Закреплённые Git blobs',True,dict(files=len(manifest['files']),note='git show exact SHA; Git не изменяется'))
extract=load('pinned_KZN_rows.json')
for x in extract:
    raw=cache[x['source_commit']+':'+x['source_path']]
    rr=list(csv.DictReader(io.StringIO(raw.decode())));source=rr[x['source_csv_record']-1]
    assert source==x['row'];assert h(json.dumps(source,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())==x['canonical_row_sha256']
check('Строки KZN и их хеши',True,dict(rows=len(extract),method=manifest['row_hash_method']))
receipts=load('fetch_receipts.json');receipts_by_id={x['source_id']:x for x in receipts}
for x in receipts:
    if x.get('path'):assert h((ROOT/x['path']).read_bytes())==x['sha256'],x['source_id']
check('Публичные загрузки и хеши',True,dict(receipts=len(receipts),saved=sum(bool(x.get('path')) for x in receipts),failed=[x['source_id'] for x in receipts if x['status']!='FETCHED']))
rules=rows('local_published_services.csv')
assert len(rules)==141
assert not any(r['destination']=='IJK' for r in rules)
assert all(r['open_seats']=='UNKNOWN' and r['fare_rub']=='UNKNOWN' for r in rules)
for r in rules:assert r['source_sha256']==receipts_by_id[r['source_id']]['sha256']
check('Опубликованные правила не инвентарь',True,'141 строка; IJK fallback исключён; цены/свободные кресла UNKNOWN; through-stop/codeshare сохранены.')
nu=[r for r in rules if r['destination']=='NUX' and r['flight']=='WZ 1507'];assert len(nu)==10
check('NUX — отдельные даты',True,dict(WZ1507_rules=len(nu),qualification='Не отмена иных продаж и не годовая частота.'))
legs=rows('proposed_legs_diagnostic.csv');assert len(set(r['flight_id'] for r in legs))==len(legs)
counts=Counter(x['programme_id'] for x in legs)
assert counts=={'P-KZN-R1':20,'P-KZN-C1':24,'P-KZN-W2':32,'P-KZN-R2':32}
for pid in counts:
    ll=[x for x in legs if x['programme_id']==pid];tails=defaultdict(list)
    for x in ll:tails[x['tail_template_id']].append(x)
    for tail,ls in tails.items():
        ls.sort(key=lambda x:x['departure_utc'])
        for a,b in zip(ls,ls[1:]):
            assert a['destination']==b['origin'];assert (datetime.fromisoformat(b['departure_utc'])-datetime.fromisoformat(a['arrival_utc'])).total_seconds()>=45*60
    expected={'P-KZN-R1':{'OMS':3,'PEE':2,'MRV':3,'MCX':2},'P-KZN-C1':{'OMS':2,'MRV':2,'MCX':2},'P-KZN-W2':{'OMS':4,'NJC':4,'MRV':4,'MCX':4},'P-KZN-R2':{'OMS':4,'NJC':4,'MRV':4,'MCX':4}}[pid]
    for dst,n in expected.items():assert sum(x['origin']=='KZN' and x['destination']==dst for x in ll)==n
check('Проектные плечи/частоты/позиции',True,dict(counts=counts,note='Только условные блоки и turn45; не реальные назначения/crew/ТО.'))
w2=[x for x in legs if x['programme_id']=='P-KZN-W2'];r2=[x for x in legs if x['programme_id']=='P-KZN-R2']
fields=['tail_template_id','origin','destination','departure_utc','arrival_utc','block_min']
assert [[r[f] for f in fields] for r in w2]==[[r[f] for f in fields] for r in r2]
check('W2 и R2-clock: один физический ресурс',True,'32 одинаковых плеча; сквозная продажа меняется в Stage B, не дублируется инвентарь.')
for north,south in [('OMS','MRV'),('NJC','MCX')]:
    arrivals=[x for x in w2 if x['origin']==north and x['destination']=='KZN' and x['arrival_utc'][11:16]=='09:30']
    assert len(arrivals)==2
    for a in arrivals:
        outs=[x for x in w2 if x['origin']=='KZN' and x['destination']==south and x['departure_utc'][:10]==a['arrival_utc'][:10]]
        gaps=[(datetime.fromisoformat(x['departure_utc'])-datetime.fromisoformat(a['arrival_utc'])).total_seconds()/60 for x in outs]
        assert 90 in gaps
check('Интервал трансферного шаблона',True,'90 минут; реальный MCT/багаж/терминал/защита UNKNOWN. MCT120 отклоняет только этот шаблон.')
hy=load('hypotheses.json')['hypotheses'];pp=load('programme_candidates.json')['programmes'];aa=rows('assumptions.csv')
assert len(hy)==8 and len(pp)==9 and len(aa)==18
assert all(x.get(k) for x in hy for k in ['signal','source_ids','mechanism','counterfactual','distinguishing_test','ancestorIDs','outcome','revisit_condition'])
aid={x['assumption_id'] for x in aa};assert all(a in aid for p in pp for a in p['assumption_ids'])
assert all(len(p['month_policy'])==24 for p in pp)
assert all('NOT_RUN' in p['money_result'] for p in pp)
check('Гипотезы/допущения/24 месяца',True,'8 исходов; 9 кандидатов; 18 assumption IDs; денежный результат NOT_RUN.')
ss={r['source_id'] for r in rows('sources.csv')}
for tab in ['evidence.csv','local_cost_reference.csv','local_published_services.csv','proposed_legs_diagnostic.csv','assumptions.csv','comparison_requests.csv']:
    for r in rows(tab):assert r['source_id'] in ss,(tab,r['source_id'])
check('Источники таблиц зарегистрированы',True,'Поле source_id разрешается в sources.csv.')
check('Ставки/страницы PDF',len(rows('local_cost_reference.csv'))==22,'8 PNG лично просмотрены; основной тарифp1–2, deice/приёмp1–2, parkingp1, жидкостиp1, скидкиp24–25. Не независимая правовая/ценовая приёмка.')
dump=dict(status='PASS' if all(x['status']=='PASS' for x in checks) else 'FAIL',validation_scope='Самопроверка происхождения, ссылок и арифметики Stage A. Не независимое ревью, не P06 acceptance, не проверка реальной экономики.',checks=checks)
(ROOT/'validation.json').write_text(json.dumps(dump,ensure_ascii=False,indent=2)+'\n')
print(dump['status'],len(checks),'checks; evidence rows',len(extract),'programme legs',len(legs))
assert dump['status']=='PASS'
