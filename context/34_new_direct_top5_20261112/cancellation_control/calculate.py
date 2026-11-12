#!/usr/bin/env python3
"""Narrow P34 cancellation counterfactual. No legacy build or writes outside HERE."""
import sys
sys.dont_write_bytecode=True
import csv, json, hashlib, importlib.util
from pathlib import Path
from collections import defaultdict, Counter
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
STUDY=HERE.parent
spec=importlib.util.spec_from_file_location('cancel_source_p34',STUDY/'calculation/calculate.py')
P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)
NAMES=['CANCEL_TUE_KEEP_FRI','CANCEL_BOTH','AER1','AER2',P.AER_TRIANGLE,'KEEP']
CASES=[('base',False),('base',True),('cautious',False),('cautious',True)]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(n,x):(HERE/n).write_text(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False)+'\n')
def table(n,rs):
    keys=list(dict.fromkeys(k for r in rs for k in r))
    with (HERE/n).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys,lineterminator='\n');w.writeheader()
        for r in rs:w.writerow({k:'NULL' if v is None else format(v,'.10f') if isinstance(v,float) else v for k,v in r.items()})
def close(a,b):assert abs(a-b)<max(1e-5,abs(b)*1e-10),(a,b)
def evaluate(name,sc,noadj):
    if not name.startswith('CANCEL'):return P.evaluate(name,sc,noadj,clock='14:00' if name.startswith('AER') else '07:00')
    original=P.project_patterns
    def cancel_patterns(_,clock):
        ps=P.retained_patterns()
        if name=='CANCEL_TUE_KEEP_FRI':ps.append(P.pattern('DONOR-FRI-KUF',['SVX','KUF','SVX'],5,'18:00'))
        return ps
    P.project_patterns=cancel_patterns
    try:z=P.evaluate('KEEP',sc,noadj)
    finally:P.project_patterns=original
    z['name']=name;z['new_pair']='NONE_INTENTIONAL_NO_NEW_PRODUCTS'
    assert not any(f['rotation_id'].startswith('NEW-') for f in z['ops_results']['P']['flights'])
    return z

def group(f,z):
    rid=f['pattern_id']
    if rid.startswith('DONOR-TUE'):return 'DONOR_TUE_OMS'
    if rid.startswith('DONOR-FRI'):return 'DONOR_FRI_KUF'
    if rid.startswith('NEW-'):return 'NEW_PAIR' if P.pair(f['origin_airport'],f['destination_airport'])==z['new_pair'] else 'ADJACENT'
    return 'RETAINED_OLD_RW'

def ledger(z,sc,case):
    rows=[]
    for side,label in [('P','programme'),('KEEP','keep')]:
        data=z[label];fs={f['flight_instance_id']:f for f in data['bundle']['flights']}
        products={p['product_id']:p for p in data['bundle']['products']}
        gs={g:dict(journeys=0.,net_revenue=0.,avoidable_cost=0.,fuel_cost=0.,other_cost=0.,flights=0.,block_hours=0.) for g in ['DONOR_TUE_OMS','DONOR_FRI_KUF','RETAINED_OLD_RW','NEW_PAIR','ADJACENT']}
        for a in data['allocation']['allocations']:
            if a['owner']!='RW':continue
            p=products[a['product_id']];g=gs[group(fs[p['legs'][0]],z)]
            g['journeys']+=a['carried'];g['net_revenue']+=a['carried']*p['net_fare']
        for f in fs.values():
            g=gs[group(f,z)];c=P.RE.costs(f['origin_airport'],f['destination_airport'],sc,f['block_hours_costscreen'])
            g['flights']+=1;g['block_hours']+=f['block_hours_costscreen']
            for k,ck in [('avoidable_cost','fixed_cost'),('fuel_cost','fuel_cost'),('other_cost','other_cost')]:g[k]+=c[ck]
        for g,vals in gs.items():
            vals['contribution']=vals['net_revenue']-vals['avoidable_cost']
            r=dict(programme=z['name'],scenario=sc,adjacent_case=case,side=side,group=g,donor_deducted_again=False)
            for k,v in vals.items():r[k+'_month']=v;r[k+'_per4']=v/4
            rows.append(r)
        close(sum(v['net_revenue'] for v in gs.values()),data['net_revenue'])
        close(sum(v['avoidable_cost'] for v in gs.values()),data['known_cost'])
    return rows

def allocation_checks(z):
    pots=[];freq=[]
    for label in ['programme','keep']:
        d=z[label];b=d['bundle'];a=d['allocation']
        pools={(m['demand_pool_id'],m['month'],m['customer_segment']):m['potential_journeys'] for m in b['markets']};pots.append(pools)
        for key,q in pools.items():close(sum(x['final_choice'] for x in a['allocations'] if (x['demand_pool_id'],x['month'],x['customer_segment'])==key),q)
        for s in a['seats']:assert s['carried_segments']<=s['saleable_seats']+1e-7
        counts=Counter((f['origin_airport'],f['destination_airport']) for f in b['flights'])
        fs={f['flight_instance_id']:f for f in b['flights']}
        for p in b['products']:
            if p['owner']=='RW':
                f=fs[p['legs'][0]];expected=counts[f['origin_airport'],f['destination_airport']]/4
                close(p['frequency'],expected);freq.append(p['frequency'])
    assert pots[0]==pots[1]
    return dict(OD_conservation=True,seat_conservation=True,same_P_KEEP_potential=True,frequency_full_month=True,min_RW_frequency=min(freq),max_RW_frequency=max(freq))

def build():
    P.protect()
    source_manifest=json.loads((STUDY/'calculation/manifest.json').read_text())
    for r in source_manifest['inputs']:assert sha(ROOT/r['path'])==r['sha256'],r['path']
    comparisons=[];ledgers=[];flights=[];zs={};checks=[]
    old=P.read(STUDY/'calculation/programme_comparison.csv')
    for name in NAMES:
        for sc,noadj in CASES:
            case='NO_UNCONFIRMED_REVENUE' if noadj else 'P05_ADJACENT_PRIOR'
            z=evaluate(name,sc,noadj);assert P.valid_economics(z)
            zs[name,sc,case]=z
            checks.append(dict(programme=name,scenario=sc,adjacent_case=case,**allocation_checks(z)))
            ls=ledger(z,sc,case);ledgers+=ls
            row=P.programme_row(z,sc,noadj)
            row['comparison_group']='CANCELLATION_CONTROL' if name.startswith('CANCEL') else row['comparison_group']
            row['missing_retained_lossbudget']=None # no claim about unobserved actual losses
            row['reason']='Conditional monthly P06 rerun; all 32 FOLLOW retained; no actual closure instruction'
            row['cycles_month']=len(z['ops_results']['P']['flights']);row['cycles_per4']=row['cycles_month']/4
            row['closed_rotations_month']=len({f['rotation_id'] for f in z['ops_results']['P']['flights']})
            row['conditional_working_tails']=1;row['conditional_reserve_tails']=1;row['new_SJ_used']=False
            row['actual_fixed_parking']=None;row['actual_cancellation_contracts']=None;row['actual_D']=None
            row['actual_gates']=None;row['penalty_storage_actual']=None
            row['P_contribution_month']=z['programme']['known_contribution'];row['KEEP_contribution_month']=z['keep']['known_contribution']
            for g,rg in [('DONOR','donor'),('RETAINED','retained'),('NEW','new_flights')]:
                select=lambda r:r['group'].startswith(g) or g=='NEW' and r['group']=='ADJACENT'
                for metric in ['net_revenue','avoidable_cost','contribution']:
                    v=sum((1 if r['side']=='P' else -1)*r[metric+'_month'] for r in ls if select(r))
                    row[rg+'_'+metric+'_delta_month']=v;row[rg+'_'+metric+'_delta_per4']=v/4
            row['avoided_cost_vs_KEEP_month']=z['keep']['known_cost']-z['programme']['known_cost']
            row['avoided_cost_vs_KEEP_per4']=row['avoided_cost_vs_KEEP_month']/4
            for side,label in [('P','programme'),('KEEP','keep')]:
                for k in ['net_revenue','known_cost','known_contribution','rw_journeys']:
                    row[side+'_'+k+'_per4']=z[label][k]/4
            close(sum(row[g+'_contribution_delta_month'] for g in ['donor','retained','new_flights']),row['known_P_minus_KEEP_month'])
            if not name.startswith('CANCEL'):
                ref=next(r for r in old if r['programme']==name and r['scenario']==sc and r['adjacent_case']==case)
                for k in ['known_P_minus_KEEP_month','net_revenue_P_month','avoidable_cost_P_month','net_revenue_KEEP_month','avoidable_cost_KEEP_month']:close(row[k],float(ref[k]))
            comparisons.append(row)
            if sc=='base' and not noadj:
                for side in ['P','KEEP']:
                    zz=dict(z);zz['ops_results']={'P':z['ops_results'][side]}
                    for f in P.serialize_flights(name,zz):
                        f['side']=side;f['rotation_id']='/'.join(f['flight_id'].split('/')[:-1]);f['initial_location']='SVX';flights.append(f)
    # Pairwise exact differences, including retained/donor reallocation rather than subtracting gross new revenue.
    pairs=[('AER1','CANCEL_TUE_KEEP_FRI'),('AER2','CANCEL_BOTH'),(P.AER_TRIANGLE,'CANCEL_BOTH'),('CANCEL_TUE_KEEP_FRI','KEEP'),('CANCEL_BOTH','KEEP'),('AER2','AER1'),(P.AER_TRIANGLE,'AER1'),(P.AER_TRIANGLE,'AER2')]
    thresholds=[]
    for sc,noadj in CASES:
        case='NO_UNCONFIRMED_REVENUE' if noadj else 'P05_ADJACENT_PRIOR'
        lookup={r['programme']:r for r in comparisons if r['scenario']==sc and r['adjacent_case']==case}
        for a,b in pairs:
            x,y=lookup[a],lookup[b];d=x['known_P_minus_KEEP_month']-y['known_P_minus_KEEP_month']
            r=dict(A=a,B=b,scenario=sc,adjacent_case=case,scoped_A_minus_B_month=d,scoped_A_minus_B_per4=d/4,
                   preferred_before_unknowns=a if d>0 else b if d<0 else 'TIE',actual_omitted_cost_A_minus_B=None,
                   omitted_cost_A_minus_B_tie_threshold_month=d,omitted_cost_A_minus_B_tie_threshold_per4=d/4,
                   decision_rule='Choose A iff omitted_cost_A - omitted_cost_B < scoped_A_minus_B; includes differential idle/parking/obligations; common donor cancellation expense cancels',
                   actual_F_cancellation=None,actual_parking=None,full_PnL_A_minus_B=None)
            for g in ['donor','retained','new_flights']:
                r[g+'_contribution_difference_month']=x[g+'_contribution_delta_month']-y[g+'_contribution_delta_month']
            r['net_revenue_difference_month']=x['net_revenue_P_month']-y['net_revenue_P_month']
            r['avoidable_cost_difference_month']=x['avoidable_cost_P_month']-y['avoidable_cost_P_month']
            close(d,r['net_revenue_difference_month']-r['avoidable_cost_difference_month'])
            thresholds.append(r)
        ranked=sorted(lookup.values(),key=lambda r:-r['known_P_minus_KEEP_month'])
        for rank,r in enumerate(ranked,1):r['conditional_rank_among_6']=rank
    table('comparison.csv',comparisons);table('ledger.csv',ledgers);table('flights.csv',flights);table('pairwise_thresholds.csv',thresholds)
    dump('request_config.json',dict(period=[P.START,P.END],names=NAMES,scenarios=CASES,cancellation_products='NONE intentional',demand_overrides=None,support=0,cargo=0,requests={name:zs[name,'base','P05_ADJACENT_PRIOR']['requests'] for name in NAMES[:2]}))
    assumptions=[
      ('scope','FULL28Feb2027; same S1 E1/R1 as P34; E1 initially SVX; R1 unscheduled; no new SJ/hub/initial aircraft'),
      ('cancellation','Only specified donor rotations removed; 32 dated FOLLOW identical P/KEEP; idle E1 stays SVX; no SVX-SVX sectors or revenue'),
      ('economics','Joint P06 monthly OD/seat/choice through P34.evaluate -> P31.evaluate_combined_programme; same P05/P04 inputs; no overrides/new passengers/quotes/support/cargo'),
      ('cost','P04 fixed_cost is scenario fuel plus cycle/MRO/blockcrew/navigation/ground/deice; not full corporate fixed cost; actual avoidability unknown'),
      ('frequency','Four departures in 28day February = 1/week; no weekly .25 exposure; demand prorated once'),
      ('pairwise','Common cancellation liabilities apply to cancel and replacement and cancel out; differential idle/parking/obligations can flip choice at signed pairwise threshold'),
      ('unknown','Full PnL/cash/actual fixed parking/cancellation contracts/actual D/gates NULL; no zero-valued actual penalty or storage assumed'),
      ('interpretation','Model counterfactual, no instruction to cancel real RW or subsidised routes; actual obligations/admission/dispatch unresolved'),
      ('stress','Full-prior BASE/CAUTIOUS and original asymmetric NO_UNCONFIRMED_REVENUE preserved; triangle central AER-MRV retained in stress; AER and cancel unchanged by stress')]
    table('assumptions.csv',[dict(item=k,assumption=v) for k,v in assumptions])
    lines=['# Узкий контроль отмены доноров','', 'Совместный rerun P/KEEP, полный февраль 2027; млн RUB2026 до неизвестных расходов. Это контрфакт модели, не распоряжение отменять реальные RW рейсы.','', '|Программа|BASE full prior|CAUTIOUS full prior|BASE noadj|CAUTIOUS noadj|','|---|---:|---:|---:|---:|']
    for name in NAMES:
        vals=[next(r['known_P_minus_KEEP_month']/1e6 for r in comparisons if r['programme']==name and r['scenario']==sc and r['adjacent_case']==('NO_UNCONFIRMED_REVENUE' if na else 'P05_ADJACENT_PRIOR')) for sc,na in [('base',False),('cautious',False),('base',True),('cautious',True)]]
        lines.append('|'+name+'|'+'|'.join(f'{v:.6f}' for v in vals)+'|')
    lines+=['','Добавка замены сверх снятия тех же доноров (full prior):']
    for r in thresholds:
        if r['adjacent_case']=='P05_ADJACENT_PRIOR' and r['A'] in ['AER1','AER2',P.AER_TRIANGLE] and r['B'].startswith('CANCEL'):
            lines.append(f"- {r['scenario']} {r['A']} − {r['B']}: {r['scoped_A_minus_B_month']/1e6:+.6f} млн/месяц, {r['scoped_A_minus_B_per4']/1e6:+.6f} млн /4; собственные новые рейсы {r['new_flights_contribution_difference_month']/1e6:+.6f}, доноры {r['donor_contribution_difference_month']/1e6:+.6f}, retained {r['retained_contribution_difference_month']/1e6:+.6f}.")
    lines+=['','Отмена сохраняет все 32 FOLLOW: пассажиры OMS/KUF перераспределяются при меньшей общей частоте, а не вычитаются из старой маржи. Нулевое число NEW_PAIR — намеренная программа. KEEP имеет положительные продажи/выручку и расходы; его scoped contribution может быть отрицательным. KEEP−KEEP=0.','', 'Суммы donor/retained/new, netrev и избегаемые fuel/other costs по обеим сетям — ledger.csv; физика P и KEEP с UTC/local/позицией/turns — flights.csv. Один сектор = один cycle; замкнутые RT/треугольники указаны отдельно. Все суммы месяца и /4; без годового пересчёта.','', 'Правило выбора A против B: scoped(A−B) − (omitted_A−omitted_B). Порог равен signed scoped(A−B), приведён в pairwise_thresholds.csv. Общие расходы отмены донора сокращаются при сравнении cancel с соответствующим replacement. Для проигрывающей замены необходима экономия её индивидуальных неизвестных расходов больше абсолютного дефицита; никаких выдуманных рублей парковки/компенсаций. Полные PnL, actual parking/Fcancellation/contracts/D/gates NULL. Support/cargo=0 — сценарий; actual penalty/storage не объявлены нулём.','', 'E1/R1, conditional release, блоки и резерв сохранены из P34. Нет нового хаба/SJ или нулевых секторов. 8BH — исходный диагностический envelope, не crew law; его превышения остаются в comparison.csv. Dispatch/crew/MRO/payload/slots и реальные обязательства требуют фактов.','', 'Ожидание cautious 6.651599/13.131477 млн проверяется как объясняемый инвариант: отмена не меняет OMS/KUF-пулы по сравнению с AER replacement (AER отдельный OD), поэтому донор/retained части совпадают; собственный AER-вклад отделяется точно. Подгонки нет.','', 'Один command calculate/verify, два настоящих детерминированных прогона:', '```sh','python3 -B context/34_new_direct_top5_20261112/cancellation_control/verify.py','```', 'Исходные core/author/review/coordinator не изменяются. Manifest фиксирует source hashes и цепочку исходного P34 manifest/dependency receipt; validation — две проверки байтов, 1190 и всех существовавших файлов P31/P32/P33/P34 вне этой папки. HEAD не фиксируется.']
    (HERE/'README.md').write_text('\n'.join(lines)+'\n')
    P.protect()
    inputs=[STUDY/'calculation/manifest.json',STUDY/'calculation/calculate.py',STUDY/'calculation/programme_comparison.csv',STUDY/'calculation/programme_ledger.csv',STUDY/'team_audit/code_handoff.md',STUDY/'team_audit/dependency_receipt.json',STUDY/'coordinator/AER_result_bridge.csv',P.C33/'protected_files.json']
    inputs+= [ROOT/r['path'] for r in json.loads((STUDY/'team_audit/dependency_receipt.json').read_text())]
    dump('manifest.json',dict(scope='two cancellation counterfactuals and exact existing controls only',source_inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in sorted(set(inputs))],source_manifest_inputs_checked=len(source_manifest['inputs']),protection_count=1190,no_HEAD_assertion=True,allocation_checks=checks,outputs=[dict(path=p.name,sha256=sha(p)) for p in sorted(HERE.iterdir()) if p.is_file() and p.name not in ['manifest.json','validation.json']]))
    print(json.dumps(dict(status='CALCULATED_CONDITIONAL',joint_evaluations=len(zs),cautious_cancellation={r['programme']:r['known_P_minus_KEEP_month'] for r in comparisons if r['programme'].startswith('CANCEL') and r['scenario']=='cautious' and r['adjacent_case']=='P05_ADJACENT_PRIOR'})))
if __name__=='__main__':build()
