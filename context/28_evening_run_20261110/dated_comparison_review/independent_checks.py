"""Independent EV-MR03 oracle. No owner solver/emitter or owner PASS is used.

Demand() is used only as the already scoped pinned input adapter. Frequencies,
geometries, construction slots and delivery daily inputs are held as supplied.
All valuations, timestamps, LP matrices, resource checks and product differences
below are reconstructed separately. Run with -B and BLAS thread limits of one.
"""
import calendar,csv,datetime as dt,functools,json,math,sys
from collections import defaultdict,Counter
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix

HERE=Path(__file__).resolve().parent
P=HERE/'_runtime/methods'
sys.path.insert(0,str(P))
from model_kernel import load
D,_=load()
NET=json.loads((P/'runs/selection_v1/networks.json').read_text())
PLANS=json.loads((P/'runs/resource_v1/plans.json').read_text())
RESULTS={};DETAIL=[]

def read(f):return list(csv.DictReader((P/f).open()))
def stamp(s):return dt.datetime.fromisoformat(s)
def day(s):return dt.date.fromisoformat(s)
def monday(d):return d-dt.timedelta(days=d.weekday())
def days(a,b):return [a+dt.timedelta(days=i) for i in range((b-a).days)]
def near(a,b,atol=1e-4):assert abs(float(a)-float(b))<=atol,(a,b,abs(float(a)-float(b)))
def write(name,obj):
    (HERE/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def mark(name,**values):
    RESULTS[name]=values;print(name,json.dumps(values,ensure_ascii=False),flush=True)

def fare(a,km):return a['fare_fixed_rub']+a['fare_per_km_rub']*km
def support(a,x,y):return a['use_subsidy']*a['subsidy_rub_per_pax']*('MOW' not in (x,y))
def cost(a,l):
    bh=a['block_fixed_h']+l['km']*(a['route_factor_south'] if l['south'] else a['route_factor'])/a['block_speed_kmh']
    c=(a['fuel_t_per_hour']*bh+a['fuel_t_per_cycle'])*a['fuel_rub_per_t']+bh*(a['mro_rub_per_hour']+a['crew_rub_per_hour']+a['navigation_rub_per_hour'])+a['ground_rub_per_flight']+a['deicing_rub_per_flight']
    return c

RW={frozenset((r['a'],r['b'])):float(r['freq_week_each_way']) for r in read('inputs/nastya_4a976/data/manual/rw_routes_now.csv')}
def share(a,l,f,W):
    if l['km']<a['transfer_min_km']:return 0.
    if l['competitive']:
        comp=D.seg(l['a'],l['b'],a['demand_scen'])/(2*W*a['seats']*a['competitor_lf'])
        return min(a['capture_competitive'],f/(f+comp)) if comp>0 else 0.
    return a['capture_open']*(1-math.exp(-f/a['capture_freq_scale']))

@functools.lru_cache(None)
def value(key,year):
    n=NET[key];a=n['assumptions'];W=(366 if calendar.isleap(year) else 365)/7;H=n['metrics']['network'];legs={};quotas={};units={}
    if n['metrics']['kind']=='HUB':
        src=n['result'][0];f={x:l['freq'] for x,l in src.items()}
        local={x:D.get(H,x,a['demand_scen'])/(2*W)*share(a,l,f[x],W) for x,l in src.items()}
        transfers={}
        for x,y,km,_ in n['result'][1]:
            transfers[(x,y)]=(km,D.get(x,y,a['demand_scen'])/(2*W)*a['capture_transfer']*(1-math.exp(-min(f[x],f[y])/a['capture_freq_scale'])))
        load=dict(local)
        for (x,y),(km,q) in transfers.items():load[x]+=q;load[y]+=q
        scales={x:min(1.,f[x]*a['seats']*a['lf_max']/q) if q else 1. for x,q in load.items()}
        for x,l in src.items():
            q=local[x]*scales[x];mg=min(q,RW.get(frozenset((H,x)),0.)*a['seats']*a['rw_existing_lf'])
            for pair in ((H,x),(x,H)):legs[pair]=dict(l,q=q/f[x],mg=mg/f[x])
        for (x,y),(km,q) in transfers.items():
            q*=min(scales[x],scales[y]);u=fare(a,km)*a['transfer_fare_factor']-2*a['pax_cost_rub']+support(a,H,x)+support(a,H,y)
            for pair in ((x,y),(y,x)):quotas[pair]=q;units[pair]=u
    else:
        pooled=defaultdict(list)
        for t in n['result']:
            for l in t[8]:pooled[frozenset((l['a'],l['b']))].append((t,l))
        for pair,members in pooled.items():
            l=members[0][1];F=sum(v['freq'] for t,v in members)
            q=min(D.get(l['a'],l['b'],a['demand_scen'])/(2*W)*share(a,l,F,W),F*a['seats']*a['lf_max'])
            mg=min(q,RW.get(pair,0.)*a['seats']*a['rw_existing_lf'])
            for t,l in members:
                b,x,y=t[1:4]
                for task in ('-'.join((b,x,y,b)),'-'.join((b,y,x,b))):legs[(task,pair)]=dict(l,q=q/F,mg=mg/F)
    return a,legs,quotas,units

def emit(key,date,case):
    a,legs,_,_=value(key,date.year);out=[];HUB=NET[key]['metrics']['kind']=='HUB'
    for base,b in PLANS[key]['bases'].items():
        for tail,slot in enumerate(b['slots'][date.weekday()]):
            clock=dt.datetime.combine(date,dt.time(6),dt.timezone.utc)
            for job in slot['tasks']:
                for x,y,bh in zip(job['airports'],job['airports'][1:],job['blocks']):
                    l=legs[(x,y) if HUB else (job['id'],frozenset((x,y)))];q=l['q'];mg=l['mg'];F=fare(a,l['km']);c=cost(a,l)
                    f=dict(flight_id=f'{case}/{date}/{len(out)+1:03}',date=str(date),origin=x,destination=y,departure_utc=clock.isoformat(),arrival_utc=(clock+dt.timedelta(hours=bh)).isoformat(),tail=f'{base}-{tail}',network_id=key,block_hours=bh,capacity_model=a['seats']*a['lf_max'],local_journeys=q,migrated_journeys=mg,local_contribution=(q-mg)*(F+support(a,x,y))-q*a['pax_cost_rub']-c)
                    out.append(f);clock+=dt.timedelta(hours=bh,minutes=45)
    return out

def lp(fs,quota,units,hub,minimum=60,maximum=180,aggregate=False):
    """Build independent incidence constraints; use the IPM optimizer."""
    fs=sorted(fs,key=lambda x:x['flight_id']);caps={f['flight_id']:float(f['capacity_model'])-float(f['local_journeys']) for f in fs};assert min(caps.values(),default=0)>=-1e-8
    ff={f['flight_id']:f for f in fs};cols=[];rhs=dict(caps)
    if aggregate:
        rhs=defaultdict(float)
        for f in fs:
            if f['destination']==hub:rhs[('in',f['origin'])]+=caps[f['flight_id']]
            if f['origin']==hub:rhs[('out',f['destination'])]+=caps[f['flight_id']]
        for pair in sorted(quota):
            a=('in',pair[0]);b=('out',pair[1])
            if a in rhs and b in rhs:cols.append((pair,a,b,None))
    else:
        ins=defaultdict(list);outs=defaultdict(list)
        for f in fs:
            if f['destination']==hub:ins[f['origin']].append(f)
            if f['origin']==hub:outs[f['destination']].append(f)
        for pair in sorted(quota):
            for a in ins[pair[0]]:
                for b in outs[pair[1]]:
                    w=(stamp(b['departure_utc'])-stamp(a['arrival_utc'])).total_seconds()/60
                    if minimum-1e-10<=w<=maximum+1e-10:cols.append((pair,a['flight_id'],b['flight_id'],w))
    for pair,q in quota.items():rhs[('market',pair)]=q
    if not cols:return dict(gain=0.,q=0.,alloc=[],usage={},market={},gap=0.,edges=set())
    rk=sorted(rhs,key=str);ri={k:i for i,k in enumerate(rk)};rr=[];cc=[]
    for j,(pair,a,b,w) in enumerate(cols):
        for k in (a,b,('market',pair)):rr.append(ri[k]);cc.append(j)
    M=coo_matrix((np.ones(len(rr)),(rr,cc)),shape=(len(rhs),len(cols))).tocsr();b=np.array([rhs[k] for k in rk]);u=np.array([units[c[0]] for c in cols])
    opt=linprog(-u,A_ub=M,b_ub=b,bounds=(0,None),method='highs-ipm');assert opt.success,opt.message
    usage=M@opt.x;assert max(usage-b)<1e-6
    dual=b@opt.ineqlin.marginals;gap=abs(float(dual-opt.fun));assert gap<1e-4
    alloc=[(col,float(q)) for col,q in zip(cols,opt.x) if q>1e-8];markets=defaultdict(float)
    for (pair,a,c,w),q in alloc:markets[pair]+=q
    return dict(gain=float(u@opt.x),q=float(sum(opt.x)),alloc=alloc,usage={k:float(usage[i]) for i,k in enumerate(rk)},market=dict(markets),gap=gap,edges={(a,b) for pair,a,b,w in cols})

def resource(fs):
    bytail=defaultdict(list);week=defaultdict(float);daily=defaultdict(float);cnt=0
    for f in fs:
        dep=stamp(f['departure_utc']);arr=stamp(f['arrival_utc']);near((arr-dep).total_seconds()/3600,float(f['block_hours']),1e-8)
        bytail[f['tail']].append(f);week[(f['tail'],str(monday(dep.date())))]+=float(f['block_hours']);daily[(f['tail'],dep.date())]+=float(f['block_hours'])
    assert max(week.values(),default=0)<=70+1e-7 and max(daily.values(),default=0)<=14+1e-7
    for tail,fl in bytail.items():
        for a,b in zip(sorted(fl,key=lambda f:stamp(f['departure_utc'])),sorted(fl,key=lambda f:stamp(f['departure_utc']))[1:]):
            assert a['destination']==b['origin'],(tail,a,b)
            assert stamp(b['departure_utc'])-stamp(a['arrival_utc'])>=dt.timedelta(minutes=45)
            cnt+=1
    return cnt

def annual_checks():
    intervals=read('runs/annual_v1/program_intervals.csv');daily=read('runs/annual_v1/aircraft_calendar_daily.csv')
    supply={(r['branch'],r['date']):int(r['working_new']) for r in daily if r['availability']=='14D_GROUNDING_STRESS'}
    original=defaultdict(dict)
    for r in intervals:
        if r['branch'] not in ('PHASED','PARTIAL_FIRST4','DELAY6','NO_NEW') or r['availability']!='14D_GROUNDING_STRESS' or r['network'] not in ('OMS','KUF','DIRECT'):continue
        case='/'.join(r[k] for k in ('branch','scenario','network','year'))
        for date in days(day(r['start']),day(r['end_exclusive'])):assert date not in original[case];original[case][date]=r['selected_id']
    choices={(r['case'],r['week_start']):r for r in read('runs/integer_year_v1/weekly_choice_adjustments.csv')}
    wkrows={(r['case'],r['week_start']):r for r in read('runs/integer_year_v1/weekly_allocation.csv')}
    annual={r['case']:r for r in read('runs/integer_year_v1/annual_comparison.csv')}
    expectedcaps={(r['case'],r['origin'],r['destination']):r for r in read('runs/integer_year_v1/annual_market_caps.csv')}
    nweekly=0;maxgap=0.;maxobjerr=0.;countcaps=0;directional=0;transitions=0;allfs=[];cross=defaultdict(list);crossflights=defaultdict(list);week_examples=[];fiscal={}
    for case,dates in sorted(original.items()):
        branch,scenario,H,y=case.split('/');year=int(y);assert len(dates)==(366 if calendar.isleap(year) else 365)
        weeks=defaultdict(list)
        for date in dates:weeks[monday(date)].append(date)
        totals=defaultdict(float);markets=defaultdict(float);allcase=[]
        for mon,dd in sorted(weeks.items()):
            dd=sorted(dd);ids={dates[d] for d in dd};minimum=min(supply[(branch,str(d))] for d in dd)
            supplied=choices[(case,str(mon))];near(supplied['minimum_working_available'],minimum)
            pool=[k for k in ids if k!='KEEP' and PLANS[k]['working_tails']<=minimum]
            if scenario.startswith('cautious') and mon.isocalendar().week in (2,15,28,41):pool=[]
            finals=[k for k in pool if NET[k]['metrics']['model_8_12_pair_gate']];pool=finals or pool
            chosen=max(pool,key=lambda k:NET[k]['metrics']['contribution_rub_year']) if pool else 'KEEP'
            assert chosen==supplied['weekly_selected_id'];assert ids==set(supplied['original_daily_ids'].split(' | '))
            cross[(branch,scenario,H,str(mon))].append((year,chosen))
            if len(ids)>1 and len(week_examples)<8:week_examples.append(dict(case=case,week=str(mon),resource=[supply[(branch,str(d))] for d in dd],original=sorted(ids),chosen=chosen))
            if chosen=='KEEP':assert (case,str(mon)) not in wkrows;continue
            fs=[f for date in dd for f in emit(chosen,date,case)];allcase+=fs
            assert len({f['network_id'] for f in fs})==1
            _,_,Q,U=value(chosen,year);quota={p:q*len(dd)/7 for p,q in Q.items()}
            res=lp(fs,quota,U,H);agg=lp(fs,quota,U,H,aggregate=True)
            local=sum(f['local_contribution'] for f in fs);wr=wkrows[(case,str(mon))]
            for field,v in [('local_only_contribution',local),('capacity_only_contribution',local+agg['gain']),('dated_MCT_contribution',local+res['gain']),('transfer_journeys',res['q']),('source_transfer_quota',sum(quota.values())),('dated_flights',len(fs))]:
                maxobjerr=max(maxobjerr,abs(float(wr[field])-v));near(wr[field],v)
            maxgap=max(maxgap,res['gap'],agg['gap']);assert res['gain']<=agg['gain']+1e-5;nweekly+=1
            totals['dated_flights']+=len(fs);totals['block_hours']+=sum(f['block_hours'] for f in fs);totals['local_journeys']+=sum(f['local_journeys'] for f in fs);totals['migrated_journeys']+=sum(f['migrated_journeys'] for f in fs);totals['transfer_journeys']+=res['q'];totals['local_only_contribution']+=local;totals['dated_transfer_gain']+=res['gain'];totals['capacity_only_transfer_gain']+=agg['gain']
            for f in fs:markets[(f['origin'],f['destination'])]+=f['local_journeys']
            for p,q in res['market'].items():markets[p]+=q
        transitions+=resource(allcase)
        crossflights[(branch,scenario,H)].extend(f for f in allcase if day(f['date']) in days(dt.date(2027,12,27),dt.date(2028,1,3)))
        totals['dated_contribution_rub']=totals['local_only_contribution']+totals['dated_transfer_gain'];totals['integer_capacity_only_contribution_rub']=totals['local_only_contribution']+totals['capacity_only_transfer_gain'];totals['dated_journeys']=totals['local_journeys']+totals['transfer_journeys'];totals['dated_segments']=totals['local_journeys']+2*totals['transfer_journeys'];totals['net_added_segments_listed_keep_only']=totals['dated_segments']-totals['migrated_journeys']
        for field,v in totals.items():near(annual[case][field],v,1e-3)
        pairq=defaultdict(float)
        for (x,y),q in markets.items():
            limit=D.get(x,y,'cautious' if scenario.startswith('cautious') else 'base')
            assert q<=limit/2+1e-6,(case,x,y,q,limit/2);directional+=1;pairq[tuple(sorted((x,y)))]+=q
        for (x,y),q in pairq.items():
            r=expectedcaps[(case,x,y)];near(float(r['local_journeys'])+float(r['transfer_journeys']),q);near(r['slack'],float(r['annual_model_OD'])-q);assert q<=float(r['annual_model_OD'])+1e-6;countcaps+=1
        if case=='PHASED/base_sub/OMS/2028':allfs=allcase
        fiscal[case]={k:float(annual[case][k]) for k in ('v2_active_day_equivalent_contribution','integer_capacity_only_contribution_rub','dated_contribution_rub')}
    for k,vals in cross.items():assert len({v for y,v in vals})==1,(k,vals)
    crossyear_transitions=sum(resource(fs) for fs in crossflights.values())
    crossing_connections=0
    for (branch,scenario,H),fs in crossflights.items():
        for a in fs:
            for b in fs:
                if day(a['date']).year==day(b['date']).year or a['destination']!=H or b['origin']!=H:continue
                w=(stamp(b['departure_utc'])-stamp(a['arrival_utc'])).total_seconds()/60
                crossing_connections+=60<=w<=180
    assert crossing_connections==0
    assert len(annual)==96 and nweekly==2298 and countcaps==563
    write('weekly_minimum_examples.json',week_examples)
    write('annual_oracle_values.json',fiscal)
    mark('A_annual',annual_cases=len(annual),calendar_choices=len(choices),weekly_LPs=nweekly,annual_bidirectional_OD_caps=countcaps,independent_directed_OD_caps=directional,continuity_including_program_changes=transitions,cross_year_week_transitions=crossyear_transitions,cross_year_MCT_connections=crossing_connections,max_oracle_primal_dual_gap=maxgap,max_weekly_field_difference=maxobjerr,cross_year_week_programs='consistent in supplied data; mutation separately tests general rule')
    exported=read('runs/integer_year_v1/OMS_2028_dated_flights.csv');assert len(exported)==len(allfs)==5976
    index={f['flight_id']:f for f in allfs};used=defaultdict(float);mq=defaultdict(float);gain=0.
    for f in exported:
        g=index[f['flight_id']]
        for field in ('origin','destination','date','tail','departure_utc','arrival_utc','network_id'):assert f[field]==g[field],(field,f,g)
        for field in ('local_journeys','migrated_journeys','local_contribution','block_hours','capacity_model'):near(f[field],g[field])
    itins=read('runs/integer_year_v1/OMS_2028_dated_itineraries.csv')
    for r in itins:
        a=index[r['inbound_flight']];b=index[r['outbound_flight']];q=float(r['journeys']);pair=(r['origin'],r['destination']);assert a['destination']==b['origin']=='OMS' and a['origin']==pair[0] and b['destination']==pair[1]
        w=(stamp(b['departure_utc'])-stamp(a['arrival_utc'])).total_seconds()/60;assert 60<=w<=180;near(w,r['wait_minutes'])
        assert monday(day(a['date']))==monday(day(b['date']))
        _,_,quota,unit=value(a['network_id'],2028);near(r['one_fare_margin'],unit[pair]);near(r['margin'],q*unit[pair]);gain+=q*unit[pair]
        used[a['flight_id']]+=q;used[b['flight_id']]+=q;mq[(str(monday(day(a['date']))),pair)]+=q
    for r in read('runs/integer_year_v1/OMS_2028_capacity.csv'):
        f=index[r['flight_id']];near(r['capacity'],f['capacity_model']);near(r['local'],f['local_journeys']);near(r['transfer'],used[f['flight_id']]);near(r['residual'],f['capacity_model']-f['local_journeys']-used[f['flight_id']]);assert float(r['residual'])>=-1e-6
    near(gain,annual['PHASED/base_sub/OMS/2028']['dated_transfer_gain'],1e-3)
    mark('A_exported_inventory',flights=len(exported),itineraries=len(itins),seat_occupancy_identity=sum(used.values()),twice_journeys=2*sum(float(r['journeys']) for r in itins),one_fare_gain=gain)

def connections_checks():
    raw=read('runs/resource_v1/dated_rotations.csv');bykey=defaultdict(list);lookup={}
    for i,r in enumerate(raw):r=dict(r,flight_id=f'F{i:05d}');bykey[r['network_id']].append(r);lookup[r['flight_id']]=r
    maxerr=0.;maxgap=0.;cert=0
    source={r['case']:r for r in read('runs/connections_v1/summary.csv')}
    suppliedcaps=defaultdict(list)
    for r in read('runs/connections_v1/flight_capacity.csv'):suppliedcaps[r['case']].append(r)
    assignments=defaultdict(list)
    for r in read('runs/connections_v1/itinerary_assignments.csv'):assignments[r['case']].append(r)
    for case,r in source.items():
        key=r['network_id'];n=NET[key];a=n['assumptions'];H=n['metrics']['network'];legs=n['result'][0];Q={};U={};fs=[]
        for x,y,km,t in n['result'][1]:
            for pair in ((x,y),(y,x)):Q[pair]=t;U[pair]=fare(a,km)*a['transfer_fare_factor']-2*a['pax_cost_rub']+support(a,H,x)+support(a,H,y)
        for f in bykey[key]:
            x=f['origin'] if f['destination']==H else f['destination'];fs.append(dict(f,capacity_model=a['seats']*a['lf_max'],local_journeys=legs[x]['local_carried']/legs[x]['freq']))
        oracle=lp(fs,Q,U,H,int(r['planning_mct_minutes']),int(r['max_wait_minutes']));local=n['metrics']['contribution_rub_year']/a['weeks_per_year']-sum(Q[p]*U[p] for p in Q)
        ownlocal=0.
        for f in fs:
            x=f['origin'] if f['destination']==H else f['destination'];l=legs[x];ql=l['local_carried']/l['freq'];mg=l['migrated']/l['freq']
            ownlocal+=(ql-mg)*(fare(a,l['km'])+support(a,H,x))-cost(a,l)-ql*a['pax_cost_rub']
        near(ownlocal,local)
        maxerr=max(maxerr,abs(local+oracle['gain']-float(r['dated_contribution_rub_week'])));near(local+oracle['gain'],r['dated_contribution_rub_week']);near(oracle['q'],r['dated_transfer_journeys_week']);maxgap=max(maxgap,oracle['gap'])
        usage=defaultdict(float);markets=defaultdict(float);gain=0.
        for it in assignments[case]:
            a1=lookup[it['inbound_flight']];b1=lookup[it['outbound_flight']];pair=(it['origin'],it['destination']);q=float(it['journeys']);w=(stamp(b1['departure_utc'])-stamp(a1['arrival_utc'])).total_seconds()/60
            assert a1['destination']==b1['origin']==H and a1['origin']==pair[0] and b1['destination']==pair[1];near(w,it['wait_minutes']);assert float(r['planning_mct_minutes'])<=w<=float(r['max_wait_minutes']);assert it['fare_count']=='1' and it['seat_segments_per_journey']=='2';near(it['margin_per_journey'],U[pair]);near(it['margin'],q*U[pair]);gain+=q*U[pair]
            usage[it['inbound_flight']]+=q;usage[it['outbound_flight']]+=q;markets[pair]+=q
        for row in suppliedcaps[case]:near(row['transfer_used'],usage[row['flight_id']]);near(float(row['model_capacity'])-float(row['fixed_local'])-float(row['transfer_used']),row['residual']);assert float(row['residual'])>=-1e-6
        for p,q in markets.items():assert q<=Q[p]+1e-6
        near(gain,oracle['gain']);cert+=1
    mark('A_diagnostic_weeks',cases=cert,exported_assignments=sum(map(len,assignments.values())),capacity_rows=sum(map(len,suppliedcaps.values())),max_objective_difference=maxerr,max_primal_dual_gap=maxgap)

def sync_checks():
    r=json.loads((P/'runs/synchronised_v1/validation.json').read_text());key=r['network_id'];n=NET[key];a=n['assumptions'];legs=n['result'][0];fs=read('runs/synchronised_v1/flights.csv');Q={};U={}
    for x,y,km,q in n['result'][1]:
        for pair in ((x,y),(y,x)):Q[pair]=q;U[pair]=fare(a,km)*a['transfer_fare_factor']-2*a['pax_cost_rub']+support(a,'OMS',x)+support(a,'OMS',y)
    raw={f'F{i:05d}':f for i,f in enumerate(read('runs/resource_v1/dated_rotations.csv'))};base=[];alt=[];shift_hours=0.
    for f in fs:
        old=raw[f['flight_id']];assert old['network_id']==key
        for k in ('origin','destination','tail','date','block_hours'):assert f[k]==old[k]
        x=f['origin'] if f['destination']=='OMS' else f['destination'];near(f['local_journeys'],legs[x]['local_carried']/legs[x]['freq']);near(f['capacity_model'],a['seats']*a['lf_max'])
        delta=(stamp(f['departure_utc'])-stamp(old['departure_utc'])).total_seconds()/60;near(delta,r['offset_minutes'][f['tail']]);near((stamp(f['arrival_utc'])-stamp(old['arrival_utc'])).total_seconds()/60,delta)
        assert stamp(f['departure_utc']).date()==stamp(f['arrival_utc']).date()==day(f['date'])
        g=dict(f,departure_utc=old['departure_utc'],arrival_utc=old['arrival_utc']);base.append(g);alt.append(f);shift_hours+=abs(delta)/60
    before=lp(base,Q,U,'OMS');after=lp(alt,Q,U,'OMS');transitions=resource(alt);assert len(fs)==152 and len({f['tail'] for f in fs})==7 and transitions==145
    # The same offsets repeat each week; directly verify the Sunday->Monday wrap.
    resource(alt+[dict(f,departure_utc=(stamp(f['departure_utc'])+dt.timedelta(days=7)).isoformat(),arrival_utc=(stamp(f['arrival_utc'])+dt.timedelta(days=7)).isoformat()) for f in alt])
    lost=before['edges']-after['edges'];gained=after['edges']-before['edges'];cr=read('runs/synchronised_v1/connection_changes.csv')
    assert {(f['inbound'],f['outbound']) for f in cr if f['state']=='LOST'}==lost
    assert {(f['inbound'],f['outbound']) for f in cr if f['state']=='GAINED'}==gained
    changes=read('runs/synchronised_v1/market_changes.csv');weighted=0.
    for f in changes:
        pair=(f['origin'],f['destination']);near(f['one_fare_margin'],U[pair]);near(float(f['alternative_journeys'])-float(f['baseline_journeys']),f['delta']);weighted+=float(f['delta'])*U[pair]
        near(before['market'].get(pair,0),f['baseline_journeys']);near(after['market'].get(pair,0),f['alternative_journeys'])
    delta=after['gain']-before['gain'];near(delta,r['delta_before_shift_cost_and_external_loss']);near(weighted,delta);near(shift_hours,101)
    local=n['metrics']['contribution_rub_year']/a['weeks_per_year']-sum(Q[p]*U[p] for p in Q)
    ownlocal=0.;foregone=0.
    for f in fs:
        x=f['origin'] if f['destination']=='OMS' else f['destination'];l=legs[x];ql=l['local_carried']/l['freq'];mg=l['migrated']/l['freq']
        ownlocal+=(ql-mg)*(fare(a,l['km'])+support(a,'OMS',x))-cost(a,l)-ql*a['pax_cost_rub'];foregone+=mg*fare(a,l['km'])
    near(ownlocal,local)
    near(local+before['gain'],r['baseline_contribution_rub_week']);near(local+after['gain'],r['alternative_contribution_rub_week']);assert local+after['gain']<0
    for p in read('runs/synchronised_v1/shift_cost_frontier.csv'):near(p['delta_after_shift_charge_before_external_loss'],delta-shift_hours*float(p['shift_cost_per_flight_hour_rub']))
    mark('B_synchronisation',flights=len(fs),working_tails=7,continuity_transitions=transitions,weekly_wrap='PASS',lost_links=len(lost),gained_links=len(gained),losing_markets=sum(float(f['delta'])<-1e-7 for f in changes),before_journeys=before['q'],after_journeys=after['q'],fixed_local_contribution=ownlocal,fixed_foregone_local_ticket=foregone,increment=delta,shift_hours=shift_hours,zero_external_fixed_cost_threshold=delta/shift_hours,after_contribution=local+after['gain'])

def products_checks():
    pref='inputs/products_3889/';params=json.loads((P/pref/'parameters.json').read_text());src=read(pref+'outputs/dated_flights.csv');a=read(pref+'inputs/nastya/data/assumptions/network.csv');A={s:{r['parameter']:float(r[s]) for r in a} for s in ('base','cautious')};dem={frozenset((r['a'],r['b'])):r for r in read(pref+'inputs/nastya/data/processed/demand_estimates.csv')}
    c31=[f for f in src if f['hypothesis']=='C31' and f['network']=='ADD_SSJ_OMS'];old=[f for f in src if f['hypothesis']=='C35' and f['network']=='rw_KEEP_retimed'];feed=[f for f in src if f['hypothesis']=='C35' and f['network']=='external_feed'];connections=[]
    # Rebuild from actual timestamps and directions, without same-date prefilter.
    for rw in c31+old:
        for f in feed:
            for first,second in ((rw,f),(f,rw)):
                if first['destination']==second['origin']=='SVX' and first['origin']!=second['destination']:
                    w=(stamp(second['departure_utc'])-stamp(first['arrival_utc'])).total_seconds()/60
                    if 90<=w<=180:connections.append(dict(first=first['flight_id'],second=second['flight_id'],rw_flight=rw['flight_id'],rw_variant=rw['network'],wait=w,first_arrival=first['arrival_utc'],second_departure=second['departure_utc']))
    assert len(c31)==4 and len(old)==16 and len(feed)==16
    assert len(connections)==16 and all(c['rw_variant']=='rw_KEEP_retimed' for c in connections)
    assert {f['date'] for f in c31}=={'2027-07-05','2027-07-08'}
    assert [d.isoformat() for d in days(day(params['C35']['start']),day(params['C35']['end'])+dt.timedelta(days=1)) if d.weekday() in (1,4)]==sorted({f['date'] for f in feed})
    union=read('runs/joint_products_v1/dated_connection_union.csv');assert {(r['rw_flight'],r['feed_flight']) for r in union if r['eligible']=='True'}=={(r['rw_flight'],r['first'] if r['first']!=r['rw_flight'] else r['second']) for r in connections}
    examples=[dict(flight_id=f['flight_id'],weekday=day(f['date']).strftime('%A'),origin=f['origin'],destination=f['destination'],departure_local=f['departure_local'],arrival_local=f['arrival_local'],departure_utc=f['departure_utc'],arrival_utc=f['arrival_utc']) for f in c31+[f for f in feed+old if f['date']=='2027-07-06']]
    write('product_calendar_examples.json',dict(new_C31_and_first_C35_day=examples,eligible_connections=connections))
    c31rows=read(pref+'outputs/C31_replacement_frontier.csv');c35rows=read(pref+'outputs/C35_partner_thresholds.csv');front=read('runs/joint_products_v1/joint_frontier.csv');capacity=read('runs/joint_products_v1/shared_flight_capacity.csv');calc={}
    def fc(s,l):
        z=A[s];h=float(l['block_hours']);return (z['fuel_t_per_hour']*h+z['fuel_t_per_cycle'])*z['fuel_rub_per_t']+h*(z['mro_rub_per_hour']+z['crew_rub_per_hour']+z['navigation_rub_per_hour'])+z['ground_rub_per_flight']+z['deicing_rub_per_flight']
    for s in A:
        z=A[s];v=z['pax_cost_rub'];om=dem[frozenset(('SVX','OMS'))];mr=dem[frozenset(('SVX','MRV'))];ij=dem[frozenset(('IJK','OMS'))]
        Fo=z['fare_fixed_rub']+z['fare_per_km_rub']*float(om['km']);Fm=z['fare_fixed_rub']+z['fare_per_km_rub']*float(mr['km']);Fj=(z['fare_fixed_rub']+z['fare_per_km_rub']*float(ij['km']))*z['transfer_fare_factor']
        cap=lambda f:z['capture_competitive']*(1-math.exp(-f/3))
        q31=min(400,float(om['od_'+s])*(cap(4)-cap(2))*7/365)
        q35=min(160,float(ij['od_'+s])*z['capture_transfer']*(1-math.exp(-2/3))*25/365)
        oldp=params['C31']['old_ssj_paid_people_each_leg'][s];oldmrv=[f for f in src if f['hypothesis']=='C31' and f['network']=='KEEP_SSJ_MRV']
        saved=sum(fc(s,f)+v*oldp for f in oldmrv);ommargin=q31*(Fo-v)-sum(fc(s,f) for f in c31);ceiling=saved+ommargin
        cann=q35*params['C35']['own_cannibalised_fraction_probe'][s];loss=cann*5000;payment=160*3000;direct=q35*(v+params['C35']['journey_handling_rub'][s]+params['C35']['expected_disruption_cost_rub_per_journey_probe'][s]);C35=q35*Fj-direct-loss-payment
        # Full KEEP difference with explicit MRV revenues and signed old-Tu result.
        keep_mrv=4*oldp*Fm-saved
        replacement_mrv=4*oldp*Fm  # Tu all-in and its old mission added below.
        near(replacement_mrv+ommargin-keep_mrv,ceiling)
        for r in front:
            if r['scenario']!=s:continue
            L=float(r['Tu_old_mission_loss_probe']);T=float(r['Tu_allin_new_cost_probe']);full_difference=replacement_mrv+ommargin+C35-T-(keep_mrv+L)
            near(r['new_endpoint_local_segments'],q31);near(r['through_journeys'],q35);near(r['partner_payment'],payment);near(r['C31_ceiling_before_Tu_K_and_old_Tu_donor'],ceiling);near(r['C35_contribution_after_partner_and_listed_own_loss'],C35);near(r['conditional_joint_before_K_and_other_network'],full_difference);near(r['maximum_Tu_allin_plus_K_at_given_donor'],ceiling+C35-L)
        for r in capacity:
            if r['scenario']!=s:continue
            isold=r['variant']=='rw_KEEP_retimed';own=85 if isold else 0;local=0 if isold else q31/4;through=q35/16 if isold else 0
            near(r['protected_existing_sales_all_markets'],own);near(r['new_endpoint_SVX_OMS'],local);near(r['new_through_IJK_OMS'],through);near(r['total'],own+local+through);assert own+local+through<=100
        calc[s]=dict(new_local=q31,through_journeys=q35,one_customer_fare=Fj,partner_reserved=160,partner_payment=payment,own_feed_migration_loss=loss,C31_ceiling=ceiling,C35_contribution=C35,joint_ceiling=ceiling+C35)
    assert len(front)==18 and len(capacity)==40
    write('product_oracle_values.json',calc)
    mark('C_joint_products',new_C31_flights=4,C31_same_date_feed=0,independent_UTC_connections=len(connections),eligible_old_rw=16,frontiers=len(front),capacity_rows=len(capacity),full_contract_reserved_seats=160,full_payment=480000,base_joint_Tu_K_ceiling=calc['base']['joint_ceiling'],later_C31_weeks='KEEP; no repetition',internal_feed='excluded separate alternative')

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('section',choices=['all','annual','connections','sync','products'],default='all',nargs='?');args=ap.parse_args()
    for name,fn in [('connections',connections_checks),('annual',annual_checks),('sync',sync_checks),('products',products_checks)]:
        if args.section in ('all',name):fn()
    write('independent_results_'+args.section+'.json',dict(status='PASS',subject='f99d6cd52dcc06995bf984fddd2f057226243b06',sections=RESULTS))
