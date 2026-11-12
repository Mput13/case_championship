"""Полные bank-контроли и привязка исходных московских маршрутов без смены порядка плеч."""
import copy,csv,itertools,json,time
from collections import defaultdict
import programme_builder as b
import evaluate_programmes as e

def main():
    pack=json.loads((b.ROOT/'programmes.json').read_text());ps=pack['programmes'];ids={p['programme_id'] for p in ps};new=[]
    screens=defaultdict(list)
    for x in csv.DictReader((b.ROOT/'pair_screen.csv').open()):
        if float(x['block_minutes_oneway'])<=150:screens[x['city']].append(x)
    for city,rows in screens.items():
        if len(rows)<9:continue
        rows.sort(key=lambda r:-float(r['known_contribution_one_RT_control']));ds=[r['destination'] for r in rows[:9]]
        template=copy.deepcopy(next(p for p in ps if p['programme_id']==city+'_HUB'))
        template.update(programme_id=city+'_BANK9',label=city+':9 лучей, полные общие волны',family='FULL_BANK9',working_slots=[dict(base=city,spokes=ds[i:i+3],bank=True) for i in [0,3,6]],network_pairs=[sorted([city,d]) for d in ds],selection_rule='Девять лучших пар общего screen при4block<=10h; новый контроль, не авторский готовый hub и не глобальный optimum.')
        new.append(template)
        c=copy.deepcopy(template);c.update(programme_id=city+'_BANK9_LOCAL_ONLY',label=city+': те же9 лучей и рейсы без продажи пересадок',transfers=False,family='SAME_SCHEDULE_CONNECTION_CONTROL');new.append(c)
        if city!='SVX':
            h=copy.deepcopy(template);h['working_slots'][2]=copy.deepcopy(next(p for p in ps if p['programme_id']=='SVX_RADIAL')['working_slots'][0])
            h.update(programme_id=city+'_BANK_HYBRID',label=city+': полные волны на2 бортах + прямые изSVX',family='FULL_BANK_PLUS_DIRECT');h['network_pairs']=sorted({tuple(sorted([s['base'],d])) for s in h['working_slots'] for d in s['spokes']});new.append(h)
    rejected=[]
    for c in json.loads((b.ROOT/'normalized_candidates.json').read_text()):
        if c['city']!='MOSCOW':continue
        raw=c['raw'];paths=raw.get('ordered_paths_iso_weekday');base=raw.get('physical_base_airport')
        if not paths or base not in b.D.nodes or any(p[0]!=base or p[-1]!=base or any(a not in b.D.nodes or a=='MOW' for a in p) for p in paths.values()):
            rejected.append(dict(candidate_id=c['id'],status='OPEN_SOURCE_PATH_NOT_CLOSED_OR_UNSUPPORTED',reason='Не добавлять неуказанный ferry/тип или аэропорт'));continue
        ds=sorted({x for p in paths.values() for x in p if x!=base})
        slots=[dict(base=base,spokes=ds,bank=False,ordered_paths_iso_weekday=paths)]+[dict(s,project=False) for s in copy.deepcopy(b.KEEP['working_slots'][1:])]
        pairs=sorted({tuple(sorted([a,z])) for p in paths.values() for a,z in zip(p,p[1:])})
        new.append(dict(programme_id='AUTH_'+c['id'],label=raw.get('name',c['id'])+'; исходная база '+base,family='AUTHOR_MOSCOW_ORDERED_PATH',city='MOSCOW',working_slots=slots,transfers=True,source_programme_ids=[c['id']],source_row_sha256=c['source_row_sha256'],source_city_manifest=c['manifest_sha256'],network_pairs=pairs,stage_fragment=True,stage='CONDITIONAL_AUTHORED_PATH_WITH_P09_RESOURCE_AND_KEEP',binding_note='Сохранены ordered paths/weekdays. Один новый рабочийN2 после ввода; остальной ресурс продолжает KEEP. Source six/other hours не считаются существующим RW обязательством. Полный московский affected KEEPUNKNOWN остаётся функцией.',unknowns=['ZIA/DME будущийKEEP/ownsales','AFM/crew/MRO','доступ/багаж/SPA','полные ставки'],assumption_ids=[a['assumption_id'] for a in b.ASSUMPTIONS]))
    new=[p for p in new if p['programme_id'] not in ids];pack['programmes']+=new;b.dump(b.ROOT/'programmes.json',pack);b.dump(b.ROOT/'additional_binding_open.json',rejected)
    configs=list(itertools.product(['phased','partial','delayed','none'],['base','cautious'],['passive']))+[('phased',s,'response10') for s in ['base','cautious']]+[('phased','bad_season','passive')]
    done=0;st=time.time()
    for de,sc,re in configs:
        e.DAY_CACHE.clear()
        for p in new:
            r=e.evaluate(p,de,sc,re);e.export_result(r,b.ROOT/'evaluations'/('__'.join([p['programme_id'],de,sc,re])+'.json'));done+=1
            if done%30==0:print('additional',done,'/',len(new)*len(configs),'seconds',round(time.time()-st,1),p['programme_id'],r['status'],flush=True)
    b.dump(b.ROOT/'additional_matrix_run.json',dict(programmes=len(new),evaluations=done,rejected_unbound=rejected,configs=configs,elapsed_seconds=time.time()-st))

if __name__=='__main__':main()
