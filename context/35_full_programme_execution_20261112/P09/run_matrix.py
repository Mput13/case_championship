"""Полная матрица фиксированных конструкций; не складывает независимые результаты."""
import copy,itertools,json,time
import programme_builder as b
import evaluate_programmes as e

def expand():
    pack=json.loads((b.ROOT/'programmes.json').read_text());ps=pack['programmes']
    ps=[p for p in ps if p['programme_id']=='KEEP' or p['programme_id'].endswith(('_RADIAL','_HUB'))]
    svx=next(p for p in ps if p['programme_id']=='SVX_RADIAL')
    additions=[]
    for p in ps:
        if p['programme_id'].endswith('_HUB'):
            c=copy.deepcopy(p);c.update(programme_id=p['programme_id']+'_LOCAL_ONLY',label=p['city']+': тот же календарь волн, только местные продукты',transfers=False,family='SAME_SCHEDULE_CONNECTION_CONTROL');additions.append(c)
            if p['city']!='SVX':
                h=copy.deepcopy(p);h['working_slots']=[copy.deepcopy(x) for x in p['working_slots'][:2]]+[copy.deepcopy(svx['working_slots'][0])]
                h.update(programme_id=p['city']+'_HYBRID',label=p['city']+': 2 борта на волнах + 1 прямой из SVX',family='HUB_PLUS_DIRECT',source_programme_ids=sorted(set(p.get('source_programme_ids',[])+svx.get('source_programme_ids',[]))))
                h['network_pairs']=sorted({tuple(sorted([s['base'],d])) for s in h['working_slots'] for d in s['spokes']});additions.append(h)
    # Explicit seasonal schedule experiments use the same source demand.
    for city in ['AER','MRV']:
        p=next(p for p in ps if p['programme_id']==city+'_RADIAL');c=copy.deepcopy(p)
        c.update(programme_id=city+'_SEASONAL',label=city+': радиальная сеть с дополнительным воскресным оборотом летом',family='SEASONAL_RADIAL',peak_sunday=True);additions.append(c)
    pack['programmes']=ps+additions;pack['expansion_rule']='Все городские HUB имеют same-flight local-only control; каждый город имеет совместно пересчитанный 2hub+1SVX hybrid; AER/MRV summer frequency control.'
    b.dump(b.ROOT/'programmes.json',pack)
    return pack['programmes']

def main():
    ps=expand();out=b.ROOT/'evaluations';out.mkdir(exist_ok=True)
    configs=list(itertools.product(['phased','partial','delayed','none'],['base','cautious'],['passive']))
    configs += [('phased',s,'response10') for s in ['base','cautious']]+[('phased','bad_season','passive')]
    st=time.time();done=0
    for delivery,scenario,response in configs:
        e.DAY_CACHE.clear()
        for p in ps:
            r=e.evaluate(p,delivery,scenario,response)
            name='__'.join([p['programme_id'],delivery,scenario,response]);e.export_result(r,out/(name+'.json'))
            done+=1
            if done%20==0:print(json.dumps(dict(done=done,total=len(ps)*len(configs),elapsed=round(time.time()-st,1),last=name,status=r['status']),ensure_ascii=False),flush=True)
        print('CONFIG_DONE',delivery,scenario,response,flush=True)
    b.dump(b.ROOT/'matrix_run.json',dict(programmes=len(ps),evaluations=done,configs=configs,elapsed_seconds=time.time()-st,engine_pin='982f13d9b6c378ed9581125ecc5c40f17dade6a3',builder_sha256=b.hashlib.sha256((b.ROOT/'programme_builder.py').read_bytes()).hexdigest(),evaluator_sha256=b.hashlib.sha256((b.ROOT/'evaluate_programmes.py').read_bytes()).hexdigest(),status='COMPUTED_CONDITIONAL_NOT_FINAL_ACCEPTANCE'))

if __name__=='__main__':main()
