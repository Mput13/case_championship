"""Полный календарь: общая P05 choice + P06 allocation/finance, без сумм городских моделей.

Для обзора независимые датированные компоненты решаются ядром P06 по датам.
Повторяющиеся типы дат мемоизируются по месяцу, полному набору рейсов и сценарию.
Число повторений берётся из731 реально перечисленных дат, а не из недели*52.
"""
import argparse, copy, csv, hashlib, json, math, re, time
from collections import defaultdict,Counter
from pathlib import Path
import programme_builder as b

ROOT=b.ROOT
b.p05.Demand=lambda:b.D  # read-only reuse of the identical pinned prior; no model change
DAY_CACHE={}

def daily_shape(fs):
    return [(x['flight_instance_id'].split(':',1)[0],x['origin_airport'],x['destination_airport'],x['departure_utc'][11:],x['arrival_utc'][11:],x['saleable_seats'],x['aircraft_variant']) for x in fs]

def daily_evaluate(pfs,kfs,scenario,transfers,response,record=False):
    day=(pfs or kfs)[0]['departure_utc'][:10]
    key=b.digest([day[:7],scenario,transfers,response,daily_shape(pfs),daily_shape(kfs)])
    if key in DAY_CACHE and not record:return DAY_CACHE[key]
    p,k=b.pair_fragments(pfs,kfs,scenario,transfers,response)
    outputs=[]
    for fs,frag in [(pfs,p),(kfs,k)]:
        bundle=dict(flights=fs,markets=frag['markets'],products=frag['products'],choice_model=b.p05.coefficients(scenario),contracts=[],economic_events=[],response_policy=frag['response_policy'])
        assert not b.check_itineraries(bundle)
        products=b.apply_response(bundle);allocation=b.allocate(bundle,products)
        ps={p['product_id']:p for p in products};rw=[a for a in allocation['allocations'] if a['owner']=='RW']
        row=dict(journeys=sum(a['carried'] for a in rw),passenger_segments=sum(a['carried']*len(ps[a['product_id']]['legs']) for a in rw),revenue_net=sum(a['carried']*ps[a['product_id']]['net_fare'] for a in rw),transfer_journeys=sum(a['carried'] for a in rw if len(ps[a['product_id']]['legs'])>1),potential_journeys=sum(m['potential_journeys'] for m in frag['markets']),outside_air_choice=sum(a['final_choice'] for a in allocation['allocations'] if ps[a['product_id']].get('outside_component')=='UNREPRESENTED_EXISTING_AIR'),seat_capacity=sum(f['saleable_seats'] for f in fs),unfilled_seats=sum(x['unsold_seats'] for x in allocation['seats']))
        row['departing_pax_by_airport']={}
        fby={f['flight_instance_id']:f for f in fs}
        for r in allocation['seats']:
            a=fby[r['flight_instance_id']]['origin_airport'];row['departing_pax_by_airport'][a]=row['departing_pax_by_airport'].get(a,0)+r['carried_segments']
        if record:row.update(products=products,allocation=allocation,markets=frag['markets'])
        outputs.append(row)
    if not record:DAY_CACHE[key]=outputs
    return outputs

def raw_pairs(raw):
    pairs=set();foreign=set()
    def add(seq):
        for a,z in zip(seq,seq[1:]):
            if a==z:continue
            if a in b.D.nodes and z in b.D.nodes and 'MOW' not in (a,z):pairs.add(tuple(sorted((a,z))))
            else:foreign.add((a,z))
    def walk(x):
        if isinstance(x,str):
            for m in re.findall(r'\b[A-Z]{3}(?:\s*[-–—>:→/]\s*[A-Z]{3})+\b',x):add(re.findall(r'[A-Z]{3}',m))
        elif isinstance(x,list):
            if len(x)>1 and all(isinstance(t,str) and re.fullmatch('[A-Z]{3}',t) for t in x):add(x)
            else:
                for v in x:walk(v)
        elif isinstance(x,dict):
            a=x.get('origin_airport',x.get('origin'));z=x.get('destination_airport',x.get('destination'))
            if isinstance(a,str) and isinstance(z,str) and re.fullmatch('[A-Z]{3}',a) and re.fullmatch('[A-Z]{3}',z):add([a,z])
            for k,v in x.items():
                if not any(s in k.lower() for s in ['source','sha','assumption','ancestor','lineage','counterfactual','compare','needs','unknown','evidence','risk']):walk(v)
    selected={k:v for k,v in raw.items() if any(s in k.lower() for s in ['pair','route','flight','pattern','rotation','path','market','spoke','network','od','leg']) and k not in ['programme_id','hypothesis_id']}
    walk(selected)
    return sorted(pairs),sorted(foreign)

def screen_pairs():
    candidates=json.loads((ROOT/'normalized_candidates.json').read_text());rows=[];citypairs=defaultdict(set);lineage=defaultdict(list)
    for c in candidates:
        pairs,foreign=raw_pairs(c['raw'])
        rows.append(dict(candidate_id=c['id'],city=c['city'],domestic_pairs=pairs,foreign_or_unmapped_pairs=foreign,source_row_id=c['source_row_id'],source_row_sha256=c['source_row_sha256'],source_file_sha256=c['source_file_sha256'],manifest_sha256=c['manifest_sha256']))
        if c['city'] in b.D.nodes:
            for a,z in pairs:
                if c['city'] in (a,z):
                    other=z if a==c['city'] else a
                    citypairs[c['city']].add(other);lineage[(c['city'],other)].append(c['id'])
    # Source-backed candidate catalogue supplemented explicitly from the common P05 prior.
    cities=[x['iata'] for x in json.loads((ROOT/'subject/PLAN/variant_research_plan.json').read_text())['seed_cities']]
    cities+=['SVX']
    screen=[];chosen={}
    monthly=list(csv.DictReader((ROOT/'subject/P05/od_monthly.csv').open()))
    print('P05monthly_fields',list(monthly[0]),flush=True)
    for city in cities:
        if city not in b.D.nodes:continue
        options=set(citypairs[city])
        # Fallback is a design expansion, not a local author conclusion.
        for pair in b.D.od:
            if city in pair:
                other=pair[1] if pair[0]==city else pair[0]
                if other in b.D.nodes and other!='MOW':options.add(other)
        opts=[]
        for other in sorted(options):
            km=b.distance(city,other)
            if km>3000 or 2*b.block(city,other)>600:continue
            day=b.date(2028,4,3);tail={'aircraft_id':'SCREEN','variant':b.NEW_VARIANT};t=b.timestamp(day,6)
            f,a=b.leg(city,other,t,'SCREEN',b.NEW_VARIANT,'screen')
            g,z=b.leg(other,city,b.p05.utc(f['arrival_utc'])+b.timedelta(minutes=45),'SCREEN',b.NEW_VARIANT,'screen')
            pr,kr=daily_evaluate([f,g],[],'base',False,'passive')
            bh=2*b.block(city,other)/60
            qfuel=bh*1.55+2*.2
            cost=qfuel*136300+bh*(35000+15000+6000)+2*49.45*(553+499)
            row=dict(city=city,destination=other,airport_pair='-'.join(sorted([city,other])),distance_km=km,block_minutes_oneway=b.block(city,other),journeys_one_RT_control=pr['journeys'],revenue_one_RT_control=pr['revenue_net'],reference_cost_one_RT_control=cost,known_contribution_one_RT_control=pr['revenue_net']-cost,status='ОДНОДНЕВНЫЙ_SCREEN_NOT_PROGRAMME_ECONOMICS',source_programmes=lineage[(city,other)],design_expansion=not bool(lineage[(city,other)]),demand_status='P05_SCENARIO_NOT_IDENTIFIED',assumption_ids=['P09-PERFORMANCE','P09-COST','P05-A01','P05-A07'])
            screen.append(row);opts.append(row)
        opts.sort(key=lambda x:(-x['known_contribution_one_RT_control'],x['destination']))
        chosen[city]=[r['destination'] for r in opts[:9]]
    b.dump(ROOT/'candidate_pair_mapping.json',rows);b.csvwrite(ROOT/'pair_screen.csv',screen)
    return cities,chosen,lineage,rows

def construct_programmes():
    cities,chosen,lineage,rawmaps=screen_pairs();ps=[]
    for city in cities:
        if len(chosen.get(city,[]))<1:continue
        destinations=chosen[city]
        for bank in [False,True]:
            typ='HUB' if bank else 'RADIAL';pid=f'{city}_{typ}'
            slots=[dict(base=city,spokes=destinations[i:i+3],bank=bank) for i in [0,3,6] if destinations[i:i+3]]
            sourceids=sorted({x for d in destinations for x in lineage[(city,d)]})
            family='EXISTING_HUB_DEVELOPMENT' if city=='SVX' and bank else 'EXISTING_BASE_DEVELOPMENT' if city in ['SVX','KUF'] else 'EXISTING_PRESENCE_DEVELOPMENT' if city in ['KZN','MCX'] else 'NEW_HUB_POLICY' if bank else 'NEW_RADIAL_BASE'
            ps.append(dict(programme_id=pid,label=f'{city}: '+('стыковочные волны' if bank else 'радиальная база'),family=family,city=city,working_slots=slots,transfers=bank,source_programme_ids=sourceids,source_city_manifest=next((x['manifest_sha256'] for x in rawmaps if x['city']==city),None),network_pairs=[sorted([city,d]) for d in destinations],selection_rule='До9 лучших локальных/P05 пар по общему однооборотному P05/P06 control; не глобальный optimum, не экономический отказ остальных.',comparison_controls='same fleet/KEEP; HUB отличается частотой, отдельный same-schedule no-transfer control обязателен',stage='CONDITIONAL_CALCULATED_SCENARIO',unknowns=['свободный ресурс','crew/MRO/AFM','полный KEEP и own international','local contracts/rates','неидентифицированный спрос'],assumption_ids=[a['assumption_id'] for a in b.ASSUMPTIONS]))
    b.dump(ROOT/'programmes.json',dict(version=b.VERSION,programmes=[b.KEEP]+ps,not_additive=True,global_optimum=False))
    return ps

def monthly_finance(cal,monthly,programme,scenario):
    """Revenue aggregation is an exact additive sufficient statistic of P06 allocations.
    No revenue formula other than carried journey * P05 net fare is introduced.
    P06 finance owns all accrual/cash/terminal arithmetic.
    """
    events=b.economic_events(cal,scenario,programme)
    for m,row in monthly.items():
        for airport,q in row.get('departing_pax_by_airport',{}).items():
            for key in ['terminal_domestic','pax_service_domestic']:
                rate,source=b.pax_rate(airport,key)
                events.append(b.econ_event(m+':'+airport+':'+key,'variable_cost',q,rate,m,source))
        ev=b.econ_event('ALLOCATED_REVENUE:'+m,'revenue',1,row['revenue_net'],m,'P05-products + P06-allocate; daily additive aggregation','P09-CASH',False)
        # Exact daily receipt buckets saved in row: price received30d before journey.
        ev['cash_plan_status']='explicit';events.append(ev)
    cash=[]
    for m,row in monthly.items():
        for d,amt in row['receipt_daily'].items():
            cash.append(dict(cash_event_id='REV:'+d+':'+m,economic_event_id='ALLOCATED_REVENUE:'+m,related_asset_or_contract_id='ALLOCATED_REVENUE:'+m,payment_date=d,amount_signed=amt,category='operating',currency='RUB',fx_at_payment=1,deposit_flag=False,source_id='P05+P06',status='scenario',assumption_id='P09-CASH'))
    coverage={x:dict(status='unknown',event_ids=[],rationale='Полный компонент UNKNOWN; subtotal отдельно',assumption_id='P09-MISSING') for x in ['variable_cost','base','aircraft_use','reserve','startup','exit','support']}
    coverage['support']=dict(status='not_applicable',event_ids=[],rationale='Сценарий без поддержки',assumption_id='P09-SUPPORT')
    bundle=dict(context=dict(period_start='2027-01',period_end='2028-12',cash_start='2026-12',price_year=2026),flights=cal['flights'],products=[],economic_events=events,cash_events=cash,opening_balances=[],cost_coverage=coverage,accounting_policy='operating_aircraft_use_excludes_interest',cash_coverage={x:'unknown' for x in ['operating','investing','tax','financing','finance_interest']},cash_policy=dict(opening_cash=None,minimum_cash=None,project_opening_cash=None,project_minimum_cash=None))
    return b.finance(bundle,[],[])

def evaluate(programme,delivery='phased',scenario='base',response='passive'):
    pc=b.build_calendar(programme,delivery);kc=b.build_calendar(b.KEEP,delivery)
    # Global physical checks precede any choice partition.
    ops=[]
    for cal in [pc,kc]:
        op=b.check_operations(dict(context={'period_start':'2027-01','period_end':'2028-12'},resource_operators=['RW_SCENARIO'],**{x:cal[x] for x in ['flights','fleet_calendar','assignments']}))
        ops.append(op)
    if any(o['errors'] for o in ops):
        return dict(programme_id=programme['programme_id'],delivery=delivery,scenario=scenario,response=response,status='INFEASIBLE_CONSTRUCTED_CALENDAR',operations=ops,scope='Не отказ всем программам города',open_work=pc['unserved'])
    byp=defaultdict(list);byk=defaultdict(list)
    for f in pc['flights']:byp[f['departure_utc'][:10]].append(f)
    for f in kc['flights']:byk[f['departure_utc'][:10]].append(f)
    ms=[{m:dict(journeys=0.,passenger_segments=0.,revenue_net=0.,transfer_journeys=0.,seat_capacity=0.,unfilled_seats=0.,receipt_daily={},departing_pax_by_airport={}) for m in b.MONTHS} for _ in [0,1]]
    certificates=Counter()
    for day in sorted(set(byp)|set(byk)):
        ext='cautious' if scenario=='bad_season' and int(day[5:7]) in [6,7,8] else 'base' if scenario=='bad_season' else scenario
        x=daily_evaluate(byp[day],byk[day],ext,programme.get('transfers',True),response)
        key=b.digest([day[:7],ext,programme.get('transfers',True),response,daily_shape(byp[day]),daily_shape(byk[day])]);certificates[key]+=1
        for rows,r in zip(ms,x):
            z=rows[day[:7]]
            for col in ['journeys','passenger_segments','revenue_net','transfer_journeys','seat_capacity','unfilled_seats']:z[col]+=r[col]
            for airport,q in r['departing_pax_by_airport'].items():z['departing_pax_by_airport'][airport]=z['departing_pax_by_airport'].get(airport,0)+q
            receipt=(b.date.fromisoformat(day)-b.timedelta(days=30)).isoformat();z['receipt_daily'][receipt]=z['receipt_daily'].get(receipt,0)+r['revenue_net']
    finances=[monthly_finance(cal,mm,programme,'base' if scenario=='bad_season' else scenario) for cal,mm in [(pc,ms[0]),(kc,ms[1])]]
    monthly=[]
    for i,m in enumerate(b.MONTHS):
        p,k=ms[0][m],ms[1][m];pf,kf=[f['results_monthly'][i] for f in finances]
        monthly.append(dict(programme_id=programme['programme_id'],delivery=delivery,scenario=scenario,response=response,month=m,journeys=p['journeys'],passenger_segments=p['passenger_segments'],transfer_journeys=p['transfer_journeys'],revenue_net=p['revenue_net'],KEEP_journeys=k['journeys'],KEEP_revenue_net=k['revenue_net'],delta_journeys=p['journeys']-k['journeys'],delta_passenger_segments=p['passenger_segments']-k['passenger_segments'],delta_revenue_net=p['revenue_net']-k['revenue_net'],known_operating_subtotal=pf['known_operating_subtotal'],KEEP_known_operating_subtotal=kf['known_operating_subtotal'],delta_known_operating_subtotal=pf['known_operating_subtotal']-kf['known_operating_subtotal'],full_operating_result=None,full_delta_result=None,seat_capacity=p['seat_capacity'],flight_load_factor=None if not p['seat_capacity'] else p['passenger_segments']/p['seat_capacity'],reported_passengers=None,market_share=None,demand_status='SCENARIO_NOT_IDENTIFIED',dispatch_ready=False))
    knowncash=[]
    for sign,f in zip([1,-1],finances):
        for e in f['cash_events']:
            if e['amount_signed'] is not None:knowncash.append(dict(e,amount_signed=sign*e['amount_signed'],cash_event_id=str(sign)+e['cash_event_id']))
    fdiag=b.funding(knowncash,'2026-12','2028-12',0,0)
    pairs=sorted({tuple(sorted([f['origin_airport'],f['destination_airport']])) for f in pc['flights'] if f['project_network'] and f['departure_utc'].startswith('2028-12')})
    summary=dict(programme_id=programme['programme_id'],label=programme['label'],delivery=delivery,scenario=scenario,response=response,status='CONDITIONAL_P05_P06_CALCULATED',journeys=sum(x['journeys'] for x in monthly),passenger_segments=sum(x['passenger_segments'] for x in monthly),delta_journeys=sum(x['delta_journeys'] for x in monthly),revenue_net=sum(x['revenue_net'] for x in monthly),delta_revenue_net=sum(x['delta_revenue_net'] for x in monthly),known_operating_subtotal=sum(x['known_operating_subtotal'] for x in monthly),delta_known_operating_subtotal=sum(x['delta_known_operating_subtotal'] for x in monthly),full_operating_result=None,full_delta_result=None,known_components_incremental_peak_diagnostic=fdiag['peak_dated_day_end'],full_incremental_peak=None,whole_company_peak=None,reported_share=None,unique_pairs_end2028=len(pairs),dispatch_ready=False,global_optimum=False,cache_date_signatures=len(certificates),calendar_flights=len(pc['flights']),choice_method='unchanged P05 producer + unchanged P06 allocate per disjoint dated component; additive P06 finance',dates_generated=731)
    return dict(**summary,results_monthly=monthly,calendar=pc,operations=ops[0],finance=finances[0],keep_finance=finances[1],known_cash_difference=knowncash,funding_diagnostic=fdiag,date_component_certificates=dict(certificates),end2028_pairs=pairs,open_work=pc['unserved'])

def export_result(result,path,keep_calendar=False):
    r={k:v for k,v in result.items() if k not in ['calendar','finance','keep_finance','known_cash_difference','operations','date_component_certificates','open_work']}
    if 'operations'in result:
        o=result['operations']
        r['operations_summary']={k:v for k,v in o.items() if k not in ['rotations','unknowns']} if isinstance(o,dict) else o
        if isinstance(o,dict):r['operations_summary'].update(unknown_count=len(o['unknowns']),unknown_examples=o['unknowns'][:12],unknown_details='Воспроизводятся P06 check_operations по saved dated flights/fleet/assignments; все crew/MRO UNKNOWN')
    if 'open_work'in result:r['open_work_count']=len(result['open_work']);r['open_work_examples']=result['open_work'][:4]
    b.dump(path,r)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--construct',action='store_true');ap.add_argument('--programme');ap.add_argument('--all',action='store_true');ap.add_argument('--delivery',default='phased');ap.add_argument('--scenario',default='base');ap.add_argument('--response',default='passive');args=ap.parse_args()
    if args.construct:construct_programmes();return
    ps=json.loads((ROOT/'programmes.json').read_text())['programmes']
    if args.programme:ps=[p for p in ps if p['programme_id']==args.programme]
    elif not args.all:raise ValueError('--programme or --all required')
    out=ROOT/'evaluations';out.mkdir(exist_ok=True)
    for p in ps:
        st=time.time();r=evaluate(p,args.delivery,args.scenario,args.response);name='__'.join([p['programme_id'],args.delivery,args.scenario,args.response]);export_result(r,out/(name+'.json'))
        print(json.dumps(dict(programme=p['programme_id'],status=r['status'],seconds=round(time.time()-st,2),delta=r.get('delta_known_operating_subtotal'),journeys=r.get('delta_journeys'),pairs=r.get('unique_pairs_end2028'),cache=len(DAY_CACHE)),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
