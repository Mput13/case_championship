"""Отдельная ветвь действующего SSJ100, без новых SJ100/Ту214 и без бесплатного донора."""
import copy,json,hashlib
import programme_builder as b
import evaluate_programmes as e
import canonical_finalists as cf
ORIGINAL=b.build_calendar
OUT=b.ROOT/'existing_ssj'

def calendar(p,delivery='none'):
    if not p.get('existing_ssj_transfer'):return ORIGINAL(p,delivery)
    assert delivery=='none'
    cal=ORIGINAL(b.KEEP,'none');tail=cal['fleet_calendar'][0];fs=[];aa=[]
    slot=p['working_slots'][0];base=slot['base'];spokes=slot['spokes'];path=b.ferry_path(base)
    def emit(a,z,t,mode):
        f,x=b.leg(a,z,t,'E1',b.EXISTING_VARIANT,mode,True);x['action']='reassign_existing';fs.append(f);aa.append(x);return b.p05.utc(f['arrival_utc'])
    def ferry(path,day):
        t=b.timestamp(day,5);bh=0
        for a,z in zip(path,path[1:]):
            if bh+b.block(a,z)/60>10:t=b.timestamp(t.date()+b.timedelta(days=1),5);bh=0
            t=emit(a,z,t,'positioning')+b.timedelta(minutes=45);bh+=b.block(a,z)/60
        return t.date()
    start=b.date(2027,1,1);end=b.date(2028,12,30)
    if path:
        start=ferry(path,start)+b.timedelta(days=1)
        return_day=b.date(2029,1,1)-b.timedelta(days=b.math.ceil(sum(b.block(a,z) for a,z in zip(path,path[1:]))/600))
        ferry(path[::-1],return_day);end=return_day-b.timedelta(days=1)
    for d in b.DATES:
        if not start<=d<=end or d.weekday()==6:continue
        z=spokes[d.weekday()%len(spokes)];t=b.timestamp(d,6.5)
        arrival=emit(base,z,t,'existing_SSJ_reassignment');emit(z,base,arrival+b.timedelta(minutes=45),'existing_SSJ_reassignment')
    return dict(flights=sorted(fs,key=lambda x:x['departure_utc']),assignments=aa,fleet_calendar=cal['fleet_calendar'],unserved=[])

def install():b.build_calendar=calendar

def main():
    install();OUT.mkdir(exist_ok=True)
    ps=json.loads((b.ROOT/'programmes.json').read_text())['programmes'];specs=[]
    for x in ps:
        if x['programme_id'].endswith('_RADIAL') and not x.get('stage_fragment'):
            p=copy.deepcopy(x);p.update(programme_id='SSJ_'+x['programme_id'],family='EXISTING_SSJ_TRANSFER_NO_NEW',existing_ssj_transfer=True,stage_fragment=True,transfers=False)
            p['working_slots']=p['working_slots'][:1];p['label']='Действующий SSJ100: '+p['working_slots'][0]['base']+'; перенос E1 с потерей прежнего KEEP'
            specs.append(p)
    b.dump(OUT/'programmes.json',specs);rows=[];flights=[]
    for p in specs:
        c=calendar(p);flights += [dict(programme_id=p['programme_id'],**f) for f in c['flights']]
        for sc in ['base','cautious']:
            for response in ['passive','response10']:
                r=e.evaluate(p,'none',sc,response);name=p['programme_id']+'__none__'+sc+'__'+response
                e.export_result(r,OUT/(name+'.json'));rows.append({k:v for k,v in r.items() if k in ['programme_id','delivery','scenario','response','status','delta_journeys','delta_known_operating_subtotal','full_delta_result','calendar_flights','unique_pairs_end2028']})
        print('SSJ',p['programme_id'],flush=True)
    b.csvwrite(OUT/'scenario_results.csv',rows,fields=list(dict.fromkeys(k for r in rows for k in r)))
    b.csvwrite(OUT/'dated_flights.csv',flights)
    viable=[]
    for p in specs:
        q=[r for r in rows if r['programme_id']==p['programme_id'] and r['response']=='passive']
        if all(r['status']=='CONDITIONAL_P05_P06_CALCULATED' for r in q):viable.append((min(r['delta_known_operating_subtotal'] for r in q),p))
    best=max(viable,key=lambda v:v[0])[1];checks=[]
    for sc in ['base','cautious']:
        a,k=b.build_pair(best,'none',sc);full=b.core.compare(a,k);name=best['programme_id']+'__none__'+sc+'__passive'
        gz=cf.write_gzip(OUT/(name+'.canonical.json.gz'),full);small=cf.projection(full);count=cf.verify_projection(small,full)
        overview=next(r for r in rows if r['programme_id']==best['programme_id'] and r['scenario']==sc and r['response']=='passive')
        diffs=dict(journeys=full['delta_summary']['journeys']-overview['delta_journeys'],known_operating_subtotal=full['thresholds']['net_missing_operating_cost_break_even']-overview['delta_known_operating_subtotal'])
        assert abs(diffs['journeys'])<1e-6 and abs(diffs['known_operating_subtotal'])<.01
        b.dump(OUT/(name+'.projection.json'),small)
        checks.append(dict(name=name,full=gz,projection_sha256=b.digest(small),verified_same_path_leaves=count,numeric_difference=diffs,project_bundle_sha256=b.digest(a),keep_bundle_sha256=b.digest(k),input_manifest=a['input_manifest'],programme_sha256=b.digest(best),method_sha256=hashlib.sha256(__import__('pathlib').Path(__file__).read_bytes()).hexdigest()))
    b.dump(OUT/'canonical_receipts.json',checks)
    b.dump(OUT/'summary.json',dict(programmes=len(specs),evaluations=len(rows),best_in_this_substudy=best['programme_id'],criterion='Наибольший минимум delta known subtotal в base/cautious; только малые программы 3пар; не глобальный optimum',main_matrix_comparable=False,reason='Отдельная одинаковая ресурсная ветвь E1 без новых; смешивать с phased newfleet frontier нельзя',no_new_SJ100=True,new_Tu214=0,donor_keep='Весь старый сценарный E1 KEEP заменён и совместно пересчитан; двойное вычитание донора запрещено',demand_status='SCENARIO_NOT_IDENTIFIED',dispatch_ready=False,full_delta_result=None))
    b.dump(OUT/'assumption.json',b.assumption('P09-EXISTING-SSJ','E1 занят старым KEEP; перенос с2027-01-01 на3луча,2RT/week каждый; ferry/потерянные продажи включены','SSJ100 SaM146; 1 условныйзанятыйборт','Материальная no-new альтернатива к сохранению E1; не утверждение о реально свободном SSJ. Старый условный KEEP тотже, новые самолёты0.','Проверка переноса существующего ресурса отдельно от получения SJ100','base/cautious и response10; величина реального donor результата остаётся неизвестной','Tail-level assignments/ownsales, reserve/crew/ТО, договорные переходные расходы'))

if __name__=='__main__':main()
