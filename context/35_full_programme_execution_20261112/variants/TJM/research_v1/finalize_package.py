"""Local resource diagnostics and referential/hash validation. No live model run."""
import csv, datetime as dt, hashlib, io, json, pathlib, subprocess
from collections import Counter, defaultdict
R=pathlib.Path(__file__).resolve().parent
def read(f):return json.loads((R/f).read_text())
def save(f,v):(R/f).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def table(f,rows):
    with (R/f).open('w',newline='') as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
p=read('programme_candidates.json')['programmes']
needed={frozenset([l['origin_airport'],l['destination_airport']]) for q in p for l in q['flight_templates']}
sha='dceadc98f9a293d7530cb7bc50ca4411a95aa4b6';mp=read('source_pins.json');dist={};distance_rows=[]
for f,ka,kb in [('data/processed/destinations.csv','from','to'),('data/processed/demand_pairs.csv','a','b')]:
    b=subprocess.check_output(['git','show',sha+':'+f]);rows=list(csv.DictReader(io.StringIO(b.decode())))
    for n,z in enumerate(rows,2):
        key=frozenset([z[ka],z[kb]])
        if key in needed and key not in dist:
            dist[key]=float(z['km']);distance_rows.append({'source_commit':sha,'source_file':f,'source_row_number':n,'source_row_sha256':hashlib.sha256(json.dumps(z,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'origin':z[ka],'destination':z[kb],'km':float(z['km']),'data_scope':'Геометрический параметр автора; спрос/деньги из строки не импортированы','unit':'км по прямой','period':'география, pinned version','coverage':'только пары локальных кандидатов','status':'MODEL_GEOMETRY_NOT_DISPATCH'})
    if not any(x['path']==f and x['commit']==sha for x in mp['files']):
        mp['files'].append({'pin_id':'AUTHOR','commit':sha,'path':f,'blob_oid':subprocess.check_output(['git','rev-parse',sha+':'+f],text=True).strip(),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
save('source_pins.json',mp);save('resource_distance_rows.json',distance_rows)

# Historical block analogue applied symmetrically; not an observed schedule.
# No published 10h planning cap is accepted as a crew legal limit.
known_turn=45/60
screens=[]
for q in p:
    dailies=defaultdict(lambda:{'legs':[],'hours_low':0,'hours_high':0,'missing':[]})
    for line in q['rotation_paths']:
        for day in line['weekdays_iso']:
            x=dailies[(line['resource_group'],day)]
            for a,b in zip(line['airports'],line['airports'][1:]):
                x['legs'].append([a,b]);km=dist.get(frozenset([a,b]))
                if km is None:x['missing'].append(a+'-'+b)
                else:
                    x['hours_low']+=.5+km*1.1/750
                    x['hours_high']+=.5+km*1.2/750
    for (group,day),x in dailies.items():
        complete=not x['missing']
        screens.append({'programme_id':q['programme_id'],'resource_group':group,'weekday_iso':day,'chain':'>'.join([x['legs'][0][0]]+[z[1] for z in x['legs']]),'legs_per_day':len(x['legs']),'block_h_inherited_k11':round(x['hours_low'],3) if complete else 'UNKNOWN','block_h_inherited_k12':round(x['hours_high'],3) if complete else 'UNKNOWN','elapsed_lower_bound_h_45min_turn':round(x['hours_low']+(len(x['legs'])-1)*known_turn,3) if complete else 'UNKNOWN','excluded':'bank synchronisation; actual winds/route; crew sign-on/off/rest; deicing; maintenance; MCT; slot; standby; reserve and cancellations','missing_pairs':';'.join(x['missing']),'unit':'блок-час/рабочий день;час elapsed lower bound','period':'шаблон дня активного сезона;не годовая оценка','coverage':'геометрический screen, не operational pass','status':'DIAGNOSTIC_ONLY','source_id':'TJM-S01;TJM-P03','assumption_ids':'TJM-A07;TJM-A08'})
table('resource_diagnostics.csv',screens)
checks=[]
def check(id,ok,detail):
    checks.append({'check_id':id,'status':'PASS' if ok else 'FAIL','detail':detail})
allsource={x['source_id'] for x in csv.DictReader((R/'sources.csv').open())}
allevidence=list(csv.DictReader((R/'evidence.csv').open()))
check('evidence_source_refs',all(set(z['source_id'].split(';'))<=allsource for z in allevidence),'Каждая доказательная строка ссылается на sources.csv; статус current/inherited раздельный.')
ass={z['assumption_id'] for z in csv.DictReader((R/'assumptions.csv').open())}
check('programme_assumption_refs',all(set(q['assumption_ids'])<=ass for q in p),'Все локальные параметры программ имеют зарегистрированные assumption_id.')
hs={x['hypothesis_id'] for x in read('hypotheses.json')['hypotheses']}
check('programme_hypothesis_refs',all(set(q['hypothesis_ids'])<=hs for q in p),'Программы связаны с локальными гипотезами.')
def pc(q):return Counter((l['origin_airport'],l['destination_airport'],d) for l in q['flight_templates'] for d in l['weekdays_iso'])
check('paired01_same_dated_legs',pc(p[0])==pc(p[1]),'P01/P02 имеют одинаковые направления и дни: 16 legs/нед; разный порядок/время и база.')
check('paired02_same_working_tail_resource',p[2]['resource']['working_tails_lower_bound']==p[3]['resource']['working_tails_lower_bound']==2,'Два одинаково доступных рабочих resource groups; reserve/crew не доказаны; налёт может различаться.')
check('paired02_same_flight_count',sum(pc(p[2]).values())==sum(pc(p[3]).values())==24,'24 направленных legs/нед в каждом сценарии, разные маршруты; не требование равенства block-hours.')
for q in p:
    loc={};good=True
    for day in range(1,8):
        for line in q['rotation_paths']:
            if day not in line['weekdays_iso']:continue
            g=line['resource_group'];a=line['airports']
            if g in loc and loc[g]!=a[0]:good=False
            loc[g]=a[-1]
    # This checks station continuity only, not aircraft availability or clock feasibility.
    check(q['programme_id']+'_station_continuity',good,'Порядок недельных цепочек не телепортирует самолёт. Первичное позиционирование/неделя boundary требуют P03.')
rows=list(csv.DictReader((R/'calendar_design_counts.csv').open()))
check('24_months_each_programme',all(len([x for x in rows if x['programme_id']==q['programme_id']])==24 for q in p),'24 явных календарных месяца; 2027 pilot Q4 сценарный, не установленный ввод.')
for q in p[:4]:
    y=sum(int(z['proposed_physical_legs_before_ops']) for z in rows if z['programme_id']==q['programme_id'] and z['month'].startswith('2028'))
    check(q['programme_id']+'_calendar_2028',y in ([836] if q['programme_id'] in ['TJM-P01','TJM-P02'] else [1248]),f'Фактический календарный счёт по дням недели: {y}; не52-кратное годовое приближение.')
check('no_financial_winner',read('case.json')['monetary_winner'] is None,'Без P05/P03/P04 принятой калибровки нет денежного победителя.')
check('types_separate',all(q['resource'].get('new_Tu214')==0 and q['resource'].get('SJ100_PD8') for q in p),'0 новых Ту214 — сценарная ветвь; SSJ/SJ100 разделены в каждом кандидате.')
# Verify that read input blobs still match exact SHA hashes, without touching the worktree.
check('pinned_blob_hashes',all(hashlib.sha256(subprocess.check_output(['git','show',x['commit']+':'+x['path']])).hexdigest()==x['sha256'] for x in mp['files']),'Все source pins повторно сверены по git show точного SHA; никаких движущихся веток.')
save('validation.json',{'status':'PASS' if all(x['status']=='PASS' for x in checks) else 'FAIL','checks':checks,'meaning':'Только структура, происхождение, календарная арифметика и станционная непрерывность. Не independent acceptance экономики, crew/MRO, physical seats или годовой сети.','engine_run':'NOT_RUN','independent_reviewer':'NOT_RUN; самопроверка автора пакета'})
print(json.dumps({'validation':read('validation.json')['status'],'checks':len(checks),'failures':[z for z in checks if z['status']=='FAIL'],'resource_rows':len(screens)},ensure_ascii=False))

def manifest():
    files=[]
    for f in sorted(R.rglob('*')):
        if f.is_file() and f.name!='output_manifest.json' and '__pycache__' not in f.parts:
            b=f.read_bytes();files.append({'path':str(f.relative_to(R)),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
    save('output_manifest.json',{'package_id':'TJM-research-v1','root':str(R),'file_hash_algorithm':'sha256 exact bytes','manifest_self_hash':'исключён для предотвращения рекурсии; хэш самого manifest передаётся в handoff-сообщении','scope':'Только назначенный каталог; никаких runtime зависимостей/копий fixtures других городов','files':files})
manifest()
