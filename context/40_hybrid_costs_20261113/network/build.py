#!/usr/bin/env python3
"""Fixed P40 only: independent seasonal arithmetic + exact pinned-code checks.
No network search, main pipeline, git mutation, price research or dated flight invention.
"""
import sys
sys.dont_write_bytecode=True
import csv, hashlib, json, math
from collections import Counter
from itertools import combinations
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
OWNER='f20000e72d5ca934f45f3aaaca4c320750ebccff'
OLD='c11eb8c15d32add540d89d086f62487a5b2d424e'
SRC=HERE/'source'/OWNER[:8]
SPOKES=['MOW','IKT','VOG','GOJ','KJA','KUF','BAX','GSV','UUD']
CHAINS={'GSV_MRV':['MOW','GSV','MRV','MOW'],'AER_VOG':['MOW','AER','VOG','MOW']}
MONTHS={'summer':[4,5,6,7,8,9,10],'winter':[11,12,1,2,3]}
WEIGHT={'summer':7/12,'winter':5/12}
MAIN=['OMS','GSV_MRV','AER_VOG','DIRECT2','HYBRID']
checks=[];route_rows=[];exposures=[];components=[];annual=[];season_totals=[];od_rows=[]

def read(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def dump(name,obj):(HERE/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def table(name,rows):
    rows=list(rows); keys=list(dict.fromkeys(k for r in rows for k in r))
    with (HERE/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
        for r in rows:w.writerow({k:('UNKNOWN' if v is None else v) for k,v in r.items()})
def close(label,a,b,tol=1e-5):
    delta=abs(float(a)-float(b)); ok=delta<=tol
    checks.append(dict(check=label,actual=a,expected=b,abs_error=delta,tolerance=tol,passed=ok))
    assert ok,checks[-1]
def require(label,v):close(label,int(bool(v)),1,0)
def pair(a,b):return tuple(sorted((a,b)))
def line(path,needle):return next(i for i,s in enumerate((SRC/path).read_text().splitlines(),1) if needle in s)
def ref(path,needle):return f'{OWNER}:{path}:{line(path,needle)}'

def load_model():
    sys.path.insert(0,str(SRC/'src'))
    import demand_model as dm
    dm.TOCHNO=SRC/'data/raw/tochno_selected.csv.gz'
    import network_model as nm
    return nm,nm.Demand(),nm.load_assumptions()

def profile(D,A,a,b,s):
    v=(D.profiles[a]+D.profiles[b])/2
    v=1+A['season_amplitude']*(v-1);v=v/v.mean()
    seasonal=v[[m-1 for m in MONTHS[s]]]
    return float(seasonal.mean()),seasonal/seasonal.mean()
def share(A,km,competitive,dem,seg,f):
    if km<A['transfer_min_km']:return 0.
    if competitive:
        fc=seg/(A['seats']*A['competitor_lf'])
        return min(A['capture_competitive'],f/(f+fc)) if fc>0 else 0.
    return A['capture_open']*(1-math.exp(-f/A['capture_freq_scale']))
def fare(A,km):return A['fare_fixed_rub']+A['fare_per_km_rub']*km
def carried(A,want,f,ratios):return float(np.minimum(want*ratios,f*A['seats']*A['lf_peak_max']).mean())
def bh(D,A,a,b):return A['block_fixed_h']+D.km(a,b)*(A['route_factor_south'] if D.south(a,b) else A['route_factor'])/A['block_speed_kmh']
def single_leg(D,A,sc,a,b,s):
    sf,ratios=profile(D,A,a,b,s);W=A['weeks_per_year']
    return dict(a=a,b=b,km=D.km(a,b),competitive=D.has_direct(a,b),dem=D.get(a,b,sc)/(2*W)*sf,
                seg=D.seg(a,b,sc)/(2*W)*sf,rw_now=D.rw.get(pair(a,b),0)*A['seats']*A['rw_existing_lf']*sf,
                ratios=ratios,sf=sf,block_h=bh(D,A,a,b))
def finish_leg(A,L,f,loc,tr,mg,transfer_revenue,spilled):
    # All fields are weekly BOTH directions, except f / one-flight block_h.
    n=2*f;hours=n*L['block_h'];segs=2*(loc+tr);tonnes=hours*A['fuel_t_per_hour']+n*A['fuel_t_per_cycle']
    localrev=2*loc*fare(A,L['km']);forgone=2*mg*fare(A,L['km'])
    out={k:v for k,v in L.items() if k not in {'ratios'}}
    out.update(freq=f,departures=n,block_hours=hours,available_seats=n*A['seats'],fuel_t=tonnes,
        local_journeys=2*loc,transfer_boardings=2*tr,segments=segs,migrated_journeys=2*mg,
        gross_local_fare_revenue_rub=localrev,gross_transfer_fare_revenue_rub=transfer_revenue,
        own_migration_forgone_rub=forgone,route_subsidy_rub=0.,
        net_revenue_rub=localrev+transfer_revenue-forgone,spilled_segments=2*spilled,
        fuel_gross_rub=tonnes*A['fuel_rub_per_t'],fuel_credit_rub=tonnes*A['fuel_compensation_rub_per_t'],
        mro_rub=hours*A['mro_rub_per_hour'],crew_rub=hours*A['crew_rub_per_hour'],
        navigation_rub=hours*A['navigation_rub_per_hour'],ground_rub=n*A['ground_rub_per_flight'],
        deice_rub=n*A['deicing_rub_per_flight'],pax_cost_rub=segs*A['pax_cost_rub'])
    out['fuel_net_rub']=out['fuel_gross_rub']-out['fuel_credit_rub']
    out['cost_rub']=sum(out[k] for k in COST_POS)-out['fuel_credit_rub']
    out['subtotal_rub']=out['net_revenue_rub']-out['cost_rub']
    return out

COST_POS=['fuel_gross_rub','mro_rub','crew_rub','navigation_rub','ground_rub','deice_rub','pax_cost_rub']
SUM_FIELDS=['departures','block_hours','available_seats','fuel_t','local_journeys','transfer_boardings','segments',
 'migrated_journeys','gross_local_fare_revenue_rub','gross_transfer_fare_revenue_rub','own_migration_forgone_rub',
 'route_subsidy_rub','net_revenue_rub','spilled_segments',*COST_POS,'fuel_credit_rub','fuel_net_rub','cost_rub','subtotal_rub']

def transfer_filter(D,A):
    rows=[]
    for x,y in combinations(SPOKES,2):
        km=D.km(x,y);ratio=(D.km('OMS',x)+D.km('OMS',y))/km
        reasons=[]
        if km<A['transfer_min_km']:reasons.append('distance_below_minimum')
        if D.has_direct(x,y):reasons.append('existing_direct_service')
        if x in D.closed or y in D.closed:reasons.append('closed_airport')
        if ratio>A['transfer_max_circuity']:reasons.append('circuity_exceeds_limit')
        rows.append(dict(origin=x,destination=y,direct_km=km,via_OMS_km=D.km('OMS',x)+D.km('OMS',y),
          circuity=ratio,limit=A['transfer_max_circuity'],has_existing_direct=D.has_direct(x,y),accepted=not reasons,
          rejection=';'.join(reasons),evidence=ref('src/network_model.py','if (D.km(H, X) + D.km(H, Y)) / dxy')))
    return rows

def hub(D,A,sc,s,filters):
    legs={x:single_leg(D,A,sc,'OMS',x,s) for x in SPOKES};W=A['weeks_per_year']
    trans=[(r['origin'],r['destination'],r['direct_km'],D.get(r['origin'],r['destination'],sc)/(2*W)*
            A['capture_transfer']*profile(D,A,r['origin'],r['destination'],s)[0]) for r in filters if r['accepted']]
    def flow(f):
        local={x:L['dem']*share(A,L['km'],L['competitive'],L['dem'],L['seg'],f[x]) for x,L in legs.items()}
        tf=[(x,y,km,q*(1-math.exp(-min(f[x],f[y])/A['capture_freq_scale']))) for x,y,km,q in trans]
        return local,tf
    f={x:int(A['min_freq_week']) for x in SPOKES}
    for _ in range(100):
        loc,tf=flow(f);wanted=dict(loc)
        for x,y,km,q in tf:wanted[x]+=q;wanted[y]+=q
        nf={x:int(min(A['max_freq_week'],max(A['min_freq_week'],math.ceil(wanted[x]/(A['seats']*A['lf_max']))))) for x in SPOKES}
        if nf==f:break
        f=nf
    else:raise AssertionError('hub frequency convergence')
    loc,tf=flow(f);load=dict(loc)
    for x,y,km,q in tf:load[x]+=q;load[y]+=q
    scale={x:carried(A,load[x],f[x],legs[x]['ratios'])/load[x] if load[x]>0 else 1. for x in SPOKES}
    local={x:loc[x]*scale[x] for x in SPOKES}
    tf=[(x,y,km,q*min(scale[x],scale[y])) for x,y,km,q in tf]
    transfer=Counter();trev=Counter()
    for x,y,km,q in tf:
        transfer[x]+=q;transfer[y]+=q
        fare_once=2*q*fare(A,km)*A['transfer_fare_factor']
        denom=legs[x]['km']+legs[y]['km']
        trev[x]+=fare_once*legs[x]['km']/denom;trev[y]+=fare_once*legs[y]['km']/denom
    out=[finish_leg(A,legs[x],f[x],local[x],transfer[x],min(local[x],legs[x]['rw_now']),trev[x],load[x]-local[x]-transfer[x]) for x in SPOKES]
    require(f'{sc}/{s}/transfer_fare_once',abs(sum(trev.values())-sum(2*q*fare(A,km)*A['transfer_fare_factor'] for x,y,km,q in tf))<1e-7)
    ods=[dict(origin='OMS',destination=x,via='',kind='LOCAL',journeys=2*local[x]) for x in SPOKES]
    ods += [dict(origin=x,destination=y,via='OMS',kind='TRANSFER',journeys=2*q) for x,y,km,q in tf]
    return out,ods

def direct(D,A,sc,s,selected,frequencies=None,allocation_context=None):
    sl={cid:[single_leg(D,A,sc,a,b,s) for a,b in zip(CHAINS[cid],CHAINS[cid][1:])] for cid in selected}
    fs={}
    for cid,ls in sl.items():
        if frequencies is not None:fs[cid]=frequencies[cid][s];continue
        f=int(A['min_freq_week'])
        for _ in range(100):
            q=[L['dem']*share(A,L['km'],L['competitive'],L['dem'],L['seg'],f) for L in ls]
            nf=int(min(A['direct_max_freq_week'],max(A['min_freq_week'],math.ceil(max(q)/(A['seats']*A['lf_max'])))))
            if nf==f:break
            f=nf
        else:raise AssertionError('direct frequency convergence')
        fs[cid]=f
    aggregate=Counter()
    for cid,ls in sl.items():
        for L in ls:aggregate[pair(L['a'],L['b'])]+=fs[cid]
    if allocation_context is not None:aggregate=allocation_context
    out=[];ods=[]
    for cid,ls in sl.items():
        f=fs[cid]
        for L in ls:
            F=aggregate[pair(L['a'],L['b'])]
            want=L['dem']*share(A,L['km'],L['competitive'],L['dem'],L['seg'],F)
            tot=carried(A,want,F,L['ratios']);loc=tot*f/F;mg=min(tot,L['rw_now'])*f/F
            o=finish_leg(A,L,f,loc,0,mg,0,(want-tot)*f/F);o['chain_id']=cid;o['pair_total_frequency_context']=F
            out.append(o);ods.append(dict(origin=L['a'],destination=L['b'],via='',kind='LOCAL',journeys=2*loc))
    return out,ods,fs

def replay_source(nm,D,A,sc,ind,source_legs,label):
    require(label+'/length',len(ind)==len(source_legs))
    for o,l in zip(ind,source_legs):
        require(label+'/pair/'+o['a']+o['b'],(o['a'],o['b'])==(l['a'],l['b']))
        for key,expected in [('freq',l['freq']),('block_h',l['block_h']),('cost_rub',l['cost_week']),
              ('net_revenue_rub',l['rev_week']),('segments',2*l['carried_dir_week']),('migrated_journeys',2*l['migrated'])]:
            close(label+'/'+o['a']+o['b']+'/'+key,o[key],expected,1e-6)

def add_case(cid,sc,s,legs,ods,A,accounting='FIXED_NETWORK_REPRICED'):
    E=A['weeks_per_year']*WEIGHT[s]
    total={k:sum(l[k] for l in legs) for k in SUM_FIELDS}
    total['transfer_journeys']=sum(o['journeys'] for o in ods if o['kind']=='TRANSFER')
    total['journeys']=sum(o['journeys'] for o in ods)
    close(f'{cid}/{sc}/{s}/segments=local+2transfer',total['segments'],total['local_journeys']+2*total['transfer_journeys'])
    close(f'{cid}/{sc}/{s}/ODjourneys',total['journeys'],total['local_journeys']+total['transfer_journeys'])
    row=dict(case_id=cid,scenario=sc,season=s,accounting=accounting,season_weight=WEIGHT[s],
             operational_model_weeks=A['weeks_per_year'],equivalent_season_weeks=E,
             **{k:v*E for k,v in total.items()},weekly_BH=total['block_hours'],weekly_departures=total['departures'])
    season_totals.append(row)
    for o in ods:
        od_rows.append(dict(dict(case_id=cid,scenario=sc,season=s,**o),journeys=o['journeys']*E,
                           own_existing_freq=D_GLOBAL.rw.get(pair(o['origin'],o['destination']),0)))
    for l in legs:
        route_rows.append(dict(case_id=cid,scenario=sc,season=s,accounting=accounting,chain_id=l.get('chain_id','OMS'),
          origin=l['a'],destination=l['b'],distance_km=l['km'],one_flight_BH=l['block_h'],frequency_week_each_direction=l['freq'],
          orientation='BOTH_DIRECTIONS',pair_total_frequency_context=l.get('pair_total_frequency_context',l['freq']),
          equivalent_season_weeks=E,**{k:l[k]*E for k in SUM_FIELDS}))
    def exposure(scope,metric,v,unit):
        exposures.append(dict(case_id=cid,scenario=sc,season=s,scope=scope,metric=metric,value=v,unit=unit,
          equivalent_season_weeks=E,quality='UNDATE_MODEL_EXPOSURE_NOT_SLOTS',accounting=accounting))
    units=dict(departures='flight_departures',block_hours='BH',available_seats='offered_seat_segments',fuel_t='burn_tonnes',
      local_journeys='endpoint_journeys',transfer_boardings='boarded_segments_of_transfer_journeys',segments='boarded_segments',
      migrated_journeys='one_way_old_RW_journeys',spilled_segments='unserved_boarded_segment_equivalents',transfer_journeys='connection_events',journeys='endpoint_journeys')
    for k,u in units.items():exposure('NETWORK',k,total[k]*E,u)
    for k,u in [('crew_room_nights','room_nights'),('away_aircraft_nights','aircraft_nights'),('ferry_departures','flight_departures'),
                ('transfer_bags','bag_connections'),('deice_treatments','actual_treatments')]:exposure('NETWORK',k,None,u)
    ap=sorted({l['a'] for l in legs}|{l['b'] for l in legs})
    for airport in ap:
        ll=[l for l in legs if airport in (l['a'],l['b'])]
        for key,u in [('departures','flight_departures'),('available_seats','offered_seats'),('segments','passenger_boardings')]:
            exposure(airport,'boardings' if key=='segments' else key,sum(l[key]/2 for l in ll)*E,u)
        exposure(airport,'arrivals',sum(l['departures']/2 for l in ll)*E,'flight_arrivals')
        exposure(airport,'transfer_connections',total['transfer_journeys']*E if airport=='OMS' else 0.,'connection_events')
    rates=[('fuel_gross_rub','fuel_t','fuel_rub_per_t',1),('fuel_credit_rub','fuel_t','fuel_compensation_rub_per_t',-1),
       ('mro_rub','block_hours','mro_rub_per_hour',1),('crew_rub','block_hours','crew_rub_per_hour',1),
       ('navigation_rub','block_hours','navigation_rub_per_hour',1),('ground_rub','departures','ground_rub_per_flight',1),
       ('deice_rub','departures','deicing_rub_per_flight',1),('pax_cost_rub','segments','pax_cost_rub',1)]
    for k,driver,param,sign in rates:
        components.append(dict(case_id=cid,scenario=sc,season=s,accounting=accounting,component=k,
          quantity=total[driver]*E,quantity_unit=units[driver],unit_rate=A[param],amount_rub=total[k]*E,
          cost_signed_rub=sign*total[k]*E,revenue_signed_rub=0.,included_in_cost=True,
          rate_source=ref('data/assumptions/network.csv',param+','),formula_source=ref('src/network_model.py','def leg_cost(')))
    for k,sign in [('gross_local_fare_revenue_rub',1),('gross_transfer_fare_revenue_rub',1),('own_migration_forgone_rub',-1),('route_subsidy_rub',1)]:
        components.append(dict(case_id=cid,scenario=sc,season=s,accounting=accounting,component=k,quantity=None,quantity_unit='FARE_WEIGHTED_JOURNEYS',
          unit_rate=None,amount_rub=total[k]*E,cost_signed_rub=0.,revenue_signed_rub=sign*total[k]*E,included_in_cost=False,
          formula_source=ref('src/network_model.py','tk = 2 * t * fare(') if 'transfer' in k else ref('src/network_model.py','plain = gross - forgone_rev')))
    close(f'{cid}/{sc}/{s}/cost_ledger',sum(r['cost_signed_rub'] for r in components if r['case_id']==cid and r['scenario']==sc and r['season']==s),row['cost_rub'],1e-4)
    return row

def calibration():
    m=[f'm{i}' for i in range(1,13)]
    totals=pd.read_csv(HERE/'source/airport_months_national_sums.csv').set_index('year')
    afl=pd.read_csv(SRC/'data/processed/aeroflot_traffic_monthly.csv');passengers=afl[afl.metric=='passengers']
    index=lambda x:np.asarray(x,dtype=float)/np.asarray(x,dtype=float).mean()
    ks={}
    for y in [2017,2018,2019]:
        allp=index(totals.loc[y,m].values);dom=index(passengers[passengers.month.str.startswith(str(y))].sort_values('month').value)
        ks[y]=float(np.polyfit(allp-1,dom-1,1)[0])
    k=float(np.mean(list(ks.values())))
    fb=np.mean([index(passengers[passengers.month.str.startswith(str(y))].sort_values('month').value) for y in [2023,2024,2025]],axis=0)
    published=json.loads((SRC/'data/processed/seasonality_calibration.json').read_text())
    close('seasonality/k_domestic_from_monthly_sums',round(k,4),published['k_domestic'],0)
    for y,v in ks.items():close(f'seasonality/k_{y}',round(v,4),published['k_by_year'][str(y)],0)
    for i,v in enumerate(fb):close(f'seasonality/fallback_m{i+1}',round(v,4),published['fallback_profile_aeroflot_domestic_2023_2025'][i],0)
    raw=pd.read_csv(HERE/'source/airport_months_selected.csv')
    names={r['iata']:r for r in read(SRC/'data/manual/favt_airport_names.csv')}
    profile_out=[]
    for row in read(SRC/'data/processed/airport_seasonality.csv'):
        iata=row['iata'];prof=[]
        for y in [2017,2018,2019]:
            got=[]
            for name in names[iata]['favt_names'].split(';') if iata in names else []:
                dy=raw[(raw.year==y)&(raw.airport==name)]
                if len(dy) and dy[m].notna().all(axis=None):got.append(dy[m].iloc[0].values)
            if got:
                v=np.sum(got,axis=0) if names[iata]['combine']=='sum' else got[0]
                if (v>0).all():prof.append(index(v))
        idx=1+k*(np.mean(prof,axis=0)-1) if prof else fb
        for j,v in enumerate(idx):
            close(f'seasonality/{iata}/m{j+1}',round(float(v),4),float(row[m[j]]),0)
            profile_out.append(dict(iata=iata,month=j+1,recomputed_index=round(float(v),4),published_index=float(row[m[j]]),fallback=not bool(prof)))
    table('seasonality_profile_checks.csv',profile_out)
    lfs=afl[afl.metric=='passenger_load_factor']
    dump('seasonality_validation.json',dict(k_domestic=k,k_by_year=ks,airport_profiles_verified=12,
      monthly_profile_cells_verified=144,local_airport_raw_owner_manifest_match=False,
      explanation='Local airport raw SHA differs from owner raw manifest (reason unverified); derived national calibration and all 144 used rounded profile cells reproduce exactly. No assertion of raw provenance equivalence.',
      domestic_max_load_factor_by_year={str(y):float(lfs[lfs.month.str.startswith(str(y))].value.max()) for y in [2024,2025]}))

def run():
    global D_GLOBAL
    for item in json.loads((HERE/'source_manifest.json').read_text()):
        require('snapshot_sha/'+item['snapshot_path'],hashlib.sha256((HERE/item['snapshot_path']).read_bytes()).hexdigest()==item['sha256'])
    calibration()
    nm,D,AS=load_model();D_GLOBAL=D
    D.profiles={r['iata']:np.array([float(r[f'm{i}']) for i in range(1,13)]) for r in read(SRC/'data/processed/airport_seasonality.csv')}
    D.rw={pair(r['a'],r['b']):float(r['freq_week_each_way']) for r in read(SRC/'data/manual/rw_routes_now.csv')};D.closed=nm.CLOSED
    filters=transfer_filter(D,AS['base']);table('transfer_filter.csv',filters)
    published=read(SRC/'data/processed/network_routes.csv');context=read(HERE/'source/direct_pair_allocation_context.csv')
    published_replays=[];frozen={};source_replays=[]
    original_seasons=nm.seasons
    for sc in ['base','cautious']:
        A=AS[sc];W=A['weeks_per_year'];frozen[sc]={}
        jointlegs={}
        for s in MONTHS:
            H,HO=hub(D,A,sc,s,filters)
            # Exact owner fixed branch; keep season_on=1 (monthly spill/peak cap intact).
            nm.seasons=lambda AA,ss=s:[(ss,1.)]
            hr=nm.hub_network('OMS',D,A,sc,SPOKES,fixed_spokes=SPOKES)[1]
            replay_source(nm,D,A,sc,H,list(hr[0].values()),f'owner_fixed_hub/{sc}/{s}')
            nm.seasons=original_seasons
            add_case('OMS',sc,s,H,HO,A)
            DD,DO,fs=direct(D,A,sc,s,list(CHAINS))
            jointlegs[s]=DD
            for cid in CHAINS:
                LL,OO,ff=direct(D,A,sc,s,[cid])
                add_case(cid,sc,s,LL,OO,A)
                frozen[sc].setdefault(cid,{})[s]=ff[cid]
                close(f'{sc}/{s}/{cid}/alone_equals_joint_revenue',sum(l['net_revenue_rub'] for l in LL),sum(l['net_revenue_rub'] for l in DD if l['chain_id']==cid),1e-6)
            add_case('DIRECT2',sc,s,DD,DO,A)
            add_case('HYBRID',sc,s,H+DD,HO+DO,A)
            # Publication is an attribution with frequencies of non-selected peer triangles still present.
            freqs={cid:{ss:float(next(r for r in published if r['scenario']==sc and r['variant']=='Прямые '+'-'.join(CHAINS[cid][:-1]))['freq_week_each_way' if ss=='summer' else 'freq_week_winter']) for ss in MONTHS} for cid in CHAINS}
            agg=Counter()
            for r in context:
                if r['scenario']==sc:agg[pair(r['from'],r['to'])]+=float(r['freq_week_each_way' if s=='summer' else 'freq_week_winter'])
            PD,PO,_=direct(D,A,sc,s,list(CHAINS),freqs,agg)
            add_case('PUBLISHED_SELECTED_DIRECT',sc,s,PD,PO,A,'FULL_DIRECT_PAIR_ALLOCATION_ATTRIBUTE_ONLY')
            add_case('PUBLISHED_HYBRID_ADD',sc,s,H+PD,HO+PO,A,'HUB_PLUS_FULL_DIRECT_ALLOCATION_ATTRIBUTE_ONLY')
        # Replay exact direct fixed branch once (empty universe prevents any candidate enumeration).
        selection=[]
        for cid,chain in CHAINS.items():
            ls=[]
            for a,b in zip(chain,chain[1:]):
                ls.append(dict(a=a,b=b,km=D.km(a,b),south=D.south(a,b),competitive=D.has_direct(a,b),
                   dem=D.get(a,b,sc)/(2*W),seg=D.seg(a,b,sc)/(2*W),rw_now=nm.rw_pax_week(a,b,A),freq_s={'year':3}))
            selection.append((None,*chain[:3],None,None,None,None,ls))
        replay=nm.direct_network(D,A,sc,[],fixed_selection=selection)
        for i,cid in enumerate(CHAINS):
            for j,l in enumerate(replay[i][8]):
                for s in MONTHS:close(f'direct_code/{sc}/{cid}/{s}/frequency',frozen[sc][cid][s],l['freq_s'][s],0)
                for key,codeval in [('net_revenue_rub',l['rev_week']),('cost_rub',l['cost_week']),('segments',2*l['carried_dir_week'])]:
                    v=sum(WEIGHT[s]*[x for x in jointlegs[s] if x['chain_id']==cid][j][key] for s in MONTHS)
                    close(f'direct_code/{sc}/{cid}/{j}/{key}',v,codeval,1e-6)
        # Exact published rounded selected-route exports, independently calculated from pair context only.
        for r in published:
            if r['scenario']!=sc:continue
            if r['variant']=='Хаб OMS':
                if sc!='base':continue # published cautious changes composition; see comparison, keep fixed9 main.
                cid='OMS'
            elif r['variant'].startswith('Прямые '):cid='PUBLISHED_SELECTED_DIRECT'
            else:continue
            ll=[x for x in route_rows if x['case_id']==cid and x['scenario']==sc and (x['origin'],x['destination'])==(r['from'],r['to'])]
            for key,col,prec in [('net_revenue_rub','revenue_mln_year',1),('cost_rub','cost_mln_year',1),('subtotal_rub','result_mln_year',1)]:
                close(f'published_route/{sc}/{r["from"]}/{r["to"]}/{col}',round(sum(x[key] for x in ll)/1e6,prec),float(r[col]),0)
            close(f'published_route/{sc}/{r["from"]}/{r["to"]}/pax',round(sum(x['segments'] for x in ll)),float(r['pax_year_segments']),0)
    # OD-set proof before any hub/direct sums may be described as a joint hybrid.
    hset={pair(r['origin'],r['destination']) for r in od_rows if r['case_id']=='OMS'}
    dset={pair(r['origin'],r['destination']) for r in od_rows if r['case_id']=='DIRECT2'}
    require('joint_OD/hub_direct_intersection_empty',not(hset&dset))
    require('joint_OD/two_direct_chains_intersection_empty',not({pair(r['origin'],r['destination']) for r in od_rows if r['case_id']=='GSV_MRV'} & {pair(r['origin'],r['destination']) for r in od_rows if r['case_id']=='AER_VOG'}))
    require('hub_spoke_count_fixed9',len(SPOKES)==9)
    hp={pair('OMS',s) for s in SPOKES};dp={pair(a,b) for ch in CHAINS.values() for a,b in zip(ch,ch[1:])}
    require('joint_physical_legs/no_duplicate_service',not(hp&dp))
    invariants=dict(hub_local_OD=sorted([list(pair('OMS',s)) for s in SPOKES]),
      hub_transfer_OD=sorted([list(pair(r['origin'],r['destination'])) for r in filters if r['accepted']]),
      direct_OD=sorted([list(p) for p in dset]),shared_OD=sorted([list(p) for p in hset&dset]),
      invariant='Every endpoint journey is in exactly one offered OD set; hub segments=local+2*transfer; one transfer fare split over two spokes. Under source existing-direct + 1.35 circuity filter, OD sets are disjoint.',
      shared_airports_or_city_markets=['GSV','MOW','VOG'],physical_leg_intersection=[],
      own_migration='Only OMS-UUD in fixed offered OD has existing RW frequency. Old fare forgone is subtracted once for local migrated journeys. No transfer-OD own migration is present.',
      excluded_MOW_pairs=[r for r in filters if 'MOW' in (r['origin'],r['destination']) and ({r['origin'],r['destination']} & {'GSV','VOG'})],
      scope_limit='Not a behavioural network-choice model. Latent substitution on excluded highly circuitous itineraries is assumed zero under the explicitly frozen filter, not empirically measured.',
      shared_services='Do not add separate station/base fixed costs for shared GSV/MOW/VOG twice. Flight, passenger, ground proxy and BH costs add because events differ; negotiated station minimums/discounts are unknown.')
    dump('joint_OD_proof.json',invariants)
    for cid in MAIN+['PUBLISHED_SELECTED_DIRECT','PUBLISHED_HYBRID_ADD']:
        for sc in ['base','cautious']:
            rr=[r for r in season_totals if r['case_id']==cid and r['scenario']==sc]
            totals={k:sum(r[k] for r in rr) for k in SUM_FIELDS+['journeys','transfer_journeys']}
            annual.append(dict(case_id=cid,scenario=sc,accounting=rr[0]['accounting'],model_year_weeks=AS[sc]['weeks_per_year'],
              period='ANNUAL_STEADY_STATE_AFTER_ENTRY_NOT_2027_CALENDAR',**totals,
              result_mln_unrounded=totals['subtotal_rub']/1e6,result_mln_rounded=round(totals['subtotal_rub']/1e6)))
    fleet=[]
    base_work={}
    for cid in MAIN:
        for sc in ['base','cautious']:
            rr=[r for r in season_totals if r['case_id']==cid and r['scenario']==sc]
            peak=max(r['weekly_BH'] for r in rr)
            if cid=='HYBRID':
                bases={base:max(r['weekly_BH'] for r in season_totals if r['case_id']==part and r['scenario']==sc) for base,part in [('OMS','OMS'),('MOW','DIRECT2')]}
            else:bases={'OMS' if cid=='OMS' else 'MOW':peak}
            work={b:math.ceil(h/70) for b,h in bases.items()};working=sum(work.values());reserve=len(bases)
            if sc=='base':base_work[cid]=work
            row=dict(case_id=cid,scenario=sc,peak_weekly_BH=peak,minimum_working_aircraft=working,
              local_reserve_aircraft=reserve,total_with_local_reserves=working+reserve,
              pooled_single_reserve_arithmetic=math.ceil(peak/70)+1,
              retained_base_working_aircraft=sum(base_work[cid].values()),retained_base_local_reserve_aircraft=len(base_work[cid]),
              retained_base_total=sum(base_work[cid].values())+len(base_work[cid]),
              working_resource_labels=';'.join(f'{b}-W{i:02d}' for b,n in work.items() for i in range(1,n+1)),
              reserve_resource_labels=';'.join('R_'+b for b in bases),
              interpretation='Capacity lower bound, no tail rotations/slot/turn/crew or MRO feasibility proof; labels are scenario resources, not registrations.')
            fleet.append(row)
            for r in annual:
                if r['case_id']==cid and r['scenario']==sc:r.update({k:v for k,v in row.items() if k not in {'case_id','scenario','interpretation'}})
    table('fleet_requirements.csv',fleet)
    # Annual and seasonal airport/network exposure and component API tables.
    for cid in MAIN+['PUBLISHED_SELECTED_DIRECT','PUBLISHED_HYBRID_ADD']:
        for sc in ['base','cautious']:
            er=[r for r in exposures if r['case_id']==cid and r['scenario']==sc]
            for scope,metric in sorted({(r['scope'],r['metric']) for r in er}):
                rows=[r for r in er if r['scope']==scope and r['metric']==metric]
                exposures.append(dict(rows[0],season='annual',value=None if any(r['value'] is None for r in rows) else sum(r['value'] for r in rows),equivalent_season_weeks=AS[sc]['weeks_per_year']))
            cr=[r for r in components if r['case_id']==cid and r['scenario']==sc]
            for comp in dict.fromkeys(r['component'] for r in cr):
                rows=[r for r in cr if r['component']==comp]
                components.append(dict(rows[0],season='annual',quantity=None if rows[0]['quantity'] is None else sum(r['quantity'] for r in rows),
                   amount_rub=sum(r['amount_rub'] for r in rows),cost_signed_rub=sum(r['cost_signed_rub'] for r in rows),revenue_signed_rub=sum(r['revenue_signed_rub'] for r in rows)))
    B=lambda cid:next(r for r in annual if r['case_id']==cid and r['scenario']=='base')
    close('deck455/reproduced',B('OMS')['result_mln_rounded'],455,0)
    close('deck113/publication_attribution_reproduced',B('PUBLISHED_SELECTED_DIRECT')['result_mln_rounded'],113,0)
    close('deck568/publication_addition_reproduced',B('PUBLISHED_HYBRID_ADD')['result_mln_rounded'],568,0)
    require('fixed_repriced_differs_materially_from_deck568',B('HYBRID')['subtotal_rub']-B('PUBLISHED_HYBRID_ADD')['subtotal_rub']>1e6)
    comparisons=[]
    for sc in ['base','cautious']:
        for cid in CHAINS:
            fixed=next(r for r in annual if r['case_id']==cid and r['scenario']==sc)
            pub=[r for r in route_rows if r['case_id']=='PUBLISHED_SELECTED_DIRECT' and r['scenario']==sc and r['chain_id']==cid]
            p={k:sum(r[k] for r in pub) for k in ['net_revenue_rub','cost_rub','subtotal_rub','segments']}
            comparisons.append(dict(case_id=cid,scenario=sc,**{'fixed_'+k:fixed[k] for k in p},**{'published_'+k:v for k,v in p.items()},
              fixed_minus_published_result_rub=fixed['subtotal_rub']-p['subtotal_rub'],cause='Full-network shared MRV-MOW and/or MOW-AER frequencies allocate carried passengers proportionally. Reprice selected network after removing peers.'))
    table('published_allocation_comparison.csv',comparisons)
    # Full source published cautious OMS differs from fixed9, explicitly retained as diagnostic only.
    summary_comparison=[]
    for r in read(SRC/'data/processed/network_summary.csv'):
        if r['hub']=='OMS':
            a=next(x for x in annual if x['case_id']=='OMS' and x['scenario']==r['scenario'])
            summary_comparison.append(dict(scenario=r['scenario'],published_spokes=r['routes'],fixed_spokes=9,published_result_mln=r['result_mln_year'],
              fixed_result_mln=a['result_mln_unrounded'],same_composition=r['scenario']=='base',
              published_spoke_list=';'.join(x['to'] for x in published if x['scenario']==r['scenario'] and x['variant']=='Хаб OMS'),fixed_spoke_list=';'.join(SPOKES)))
    table('published_hub_comparison.csv',summary_comparison)
    table('route_ledger.csv',route_rows);table('component_ledger.csv',components);table('seasonal_exposures.csv',exposures)
    table('seasonal_results.csv',season_totals);table('annual_results.csv',annual);table('od_inventory.csv',od_rows)
    old_manifest=json.loads((HERE/'source/p39/snapshot_manifest.json').read_text())
    current_manifest=json.loads((HERE/'source_manifest.json').read_text())
    delta=[]
    for item in current_manifest:
        if item.get('commit')!=OWNER:continue
        old=next((r for r in old_manifest if r['commit']==OLD and r['path']==item.get('path')),None)
        if old and not any(r['path']==item['path'] for r in delta):
            delta.append(dict(path=item['path'],old_sha256=old['source_sha256'],fresh_sha256=item['source_sha256'],
                 unchanged=old['source_sha256']==item['source_sha256']))
    oldbase=next(r for r in read(HERE/'source'/OLD[:8]/'data/processed/network_summary.csv') if r['hub']=='OMS' and r['scenario']=='base')
    flatA=dict(AS['base'],season_on=0.)
    flat=nm.hub_network('OMS',D,flatA,'base',SPOKES,fixed_spokes=SPOKES)[1]
    dump('source_delta.json',dict(old_owner=OLD,fresh_owner=OWNER,P39_method='source/p39/audit.py; reused immutable snapshot checking, cost decomposition, segment/OD identities and explicit model-period accounting; not its old optimiser/exporter',
      file_hash_delta=delta,new_files=['src/seasonality.py','docs/37_seasonality.md','data/processed/airport_seasonality.csv','data/processed/seasonality_calibration.json','monthly calibration tables'],
      prior_selected_OMS=dict(routes=int(oldbase['routes']),flights_week=int(oldbase['flights_week']),result_mln=int(oldbase['result_mln_year']),scope='HISTORICAL_COMPARISON_ONLY_NOT_P40_INPUT'),
      fresh_fixed_OMS=dict(routes=9,summer_departures_week=128,winter_departures_week=96,weighted_departures_week=5962.666666666667/52,result_mln=B('OMS')['result_mln_unrounded']),
      same_fixed9_flat_counterfactual_result_mln=(flat[4]-flat[3])*52/1e6,
      explanation='Annual OD data, fit, catchments, raw connectivity and unit costs unchanged; seasonal profiles/monthly spill/frequency and search path changed. Fixed replay bypasses search, rating and new chosen-hub UI. Previous 503/138/12 only historical provenance.',
      rules_and_longlist='Scoring-input/path changes exist but are not used to reselect fixed P40 cities.'))
    dump('budget_boundary.json',dict(status='COMPLETED_VARIABLE_FINANCIAL_AND_EXPOSURE_HANDOFF',
      main_case='HYBRID',base_operating_subtotal_rub=B('HYBRID')['subtotal_rub'],
      included=['fuel burn gross','fuel credit as cost deduction once','MRO hourly proxy','crew hourly proxy','navigation hourly proxy',
        'ground per departure proxy','deice expected allowance per departure','pax per boarded segment','own old fare forgone deducted from revenue'],
      additions_rule='Add only uncovered differential expenses. No second full ground/MRO/crew/pax bill; no second fuel credit; no double transfer fare.',
      fleet=dict(OMS_working=6,OMS_reserve=1,MOW_working=3,MOW_reserve=1,local_total=11,
        geographic_reserve_resources=['R_OMS','R_MOW'],direct2_shared_MOW_reserve_once=True),
      station_unique=['OMS','MOW','IKT','VOG','GOJ','KJA','KUF','BAX','GSV','UUD','AER','MRV'],shared_station_fixed_service_once=['MOW','VOG','GSV'],
      missing_prices='Not researched in this role; independent budget assembly owns uncovered BoQ. This handoff has no blocking dependency on it.',
      finance_main_excluded_by_user=True,financing_annual_rub=None,financing_status='UNKNOWN_NOT_ZERO_SEPARATE',
      financing_formula='annual_financing = sum(annual charge by actual financed tail); net_after_finance = subtotal - uncovered_operating_additions - annual_financing',
      residual_before_all_uncovered_operating_additions_and_finance_rub=B('HYBRID')['subtotal_rub'],
      arithmetic_financing_ceiling_per_11_tail_year_rub=B('HYBRID')['subtotal_rub']/11,
      ceiling_caveat='Pure break-even quotient if no other additions. Not a quoted aircraft price, lease benchmark or finance allowance.',
      cash_vs_PnL='Gross fuel cash vs later tax-credit receipts/timing/eligibility unresolved; model net fuel is PnL scenario. Spares inventory/deposits and launch cash must not be summed again as annual consumption/amortisation.',
      unknown_quantities=['bag incidence','actual deice events','crew roster/room nights','overnight stays','IRROPS incidence','ferry/positioning movements','dispatch/tail/crew MRO buffers'],
      entry='No new SJ100/PD8 before H2 2027. These are annual steady-state frequencies after entry, not full 2027 revenue; actual delivery/entry dates unknown.'))
    bridge=[]
    cost_fields=dict(FUEL='fuel_gross_rub',CREDIT='fuel_credit_rub',GROUND='ground_rub',PAX='pax_cost_rub',MRO_PROXY='mro_rub',NAV='navigation_rub',DEICE='deice_rub',CREW_PROXY='crew_rub',MIGRATION='own_migration_forgone_rub',GRANT='route_subsidy_rub')
    for r in read(HERE/'source/p39/coverage.csv'):
        if r['network']!='OMS':continue
        bridge.append(dict(item_id=r['item_id'],item=r['item'],P39_status=r['status'],
          P40_status='EXCLUDED_FROM_MAIN_BY_USER_FINANCING_SEPARATE' if r['item_id'] in {'LEASE_WORK','LEASE_RES','CAPITAL'} else r['status'],
          applies_to_fixed_cases=';'.join(MAIN),existing_component=cost_fields.get(r['item_id'],'UNKNOWN_BASKET_ALLOCATION_OR_ABSENT'),
          existing_amount_source='api.expenses_for(case_id,scenario)[components]; never use P39 old exposure quantities',
          annual_add_or_replace_rule=r['annual_add_or_replace_rule'],accounting_class=r['accounting_class'],
          missing_quantity_or_scope=r['missing_part_request'],P39_evidence=r['evidence'],
          fresh_formula_source=ref('src/network_model.py','def leg_cost('),new_prices=False))
    table('coverage_bridge.csv',bridge)
    dump('fleet_gates.json',dict(status='CAPACITY_RULE_LOWER_BOUND_NOT_DISPATCH_VALIDATION',
      model_rule='ceil(peak seasonal weekly BH / 70) + 1 reserve per geographically independent base',
      summer_weekly_BH=dict(OMS=396.79030273023005,MOW=174.81055814942258,combined=571.6008608796526),
      fixed_local_resources=dict(OMS_working=['OMS-W01','OMS-W02','OMS-W03','OMS-W04','OMS-W05','OMS-W06'],OMS_reserve=['R_OMS'],
        MOW_working=['MOW-W01','MOW-W02','MOW-W03'],MOW_reserve=['R_MOW']),
      published_ten=dict(arithmetic='6 OMS working + 3 MOW working + 1 pooled R1 = 10; 7 hub + 3 direct means direct working increment only',
        status='CONDITIONAL_RESERVE_GAP_AT_SECOND_BASE',
        gates=['Define which actual MOW airport is used','Identify reserve location and readiness at each base','Guarantee donor/local replacement aircraft and qualified crew or paid ferry lead time',
               'Show reserve recovery windows, simultaneous-AOG policy, maintenance and weather constraints','Include repositioning, donor opportunity cost and station support where actually incurred'],
        note='A single R1 cannot provide immediate simultaneous local coverage in OMS and MOW. Existing operator reserve might satisfy one gate, but availability and donor effect are unknown, not zero.'),
      no_extra_reserve_double_count='OMS model already includes one spare. Add only missing MOW spare; two direct triangles share the same MOW reserve. Do not sum standalone chain fleets.',
      not_checked=['actual tail circulation','slots','minimum turns','daily rolling-duty limits','crew qualifications/roster','maintenance due dates/PD8 support','actual rotations/positioning','weekly closure constraints'],
      resource_labels='Scenario identifiers only, not actual aircraft registrations',
      cautious='Fixed same OD/city composition remains; lower minimum BH fleet is a sensitivity, retained base fleet remains 11 for full-budget fixed costs.'))
    source_refs=[]
    for p,needles in {
      'src/network_model.py':['def leg_cost(','def seasons(','def pair_profile(','def spill_carried(','def leg_share(',
       'def hub_network(','if fixed_spokes is not None:','tk = 2 * t * fare(','mg = min(loc_c[X]',
       'def direct_network(','def tri_eval(','def joint(sel):','g["F"] += fs[s]','tot * f / F',
       'if fixed_selection is not None:','hours_peak / (A["block_h_per_day"] * 7)'],
      'src/seasonality.py':['YEARS =','def year_index(','np.polyfit(','fb = np.mean(','idx = 1 + k * (raw - 1)'],
      'data/assumptions/network.csv':['weeks_per_year,','spare_aircraft,','season_on,','season_amplitude,','lf_peak_max,','fuel_compensation_rub_per_t,']}.items():
        for needle in needles:
            n=line(p,needle);source_refs.append(dict(citation=f'{OWNER}:{p}:{n}',snapshot_path=str((SRC/p).relative_to(HERE)),line=n,text=(SRC/p).read_text().splitlines()[n-1]))
    table('evidence_lines.csv',source_refs)
    metadata=dict(owner_commit=OWNER,previous_owner=OLD,hub=dict(hub='OMS',spokes=SPOKES),chains=CHAINS,
      orientations={k:[v,list(reversed(v))] for k,v in CHAINS.items()},frozen_seasonal_frequencies=frozen,
      frequency_unit='complete directed circuits/week in EACH orientation; each triangle yields 6*f one-way departures/week',
      map_edges=[dict(network='OMS',origin='OMS',destination=x) for x in SPOKES]+[dict(network=k,origin=a,destination=b) for k,ch in CHAINS.items() for a,b in zip(ch,ch[1:])],
      airport_scope='MOW is a pooled city market at SVO coordinates, not an approved operating/billing airport.',
      capacity='100 seats SSJ95B proxy; SJ100/PD8 economics not independently calibrated; no entry before H2 2027',
      seasons=MONTHS,weights=WEIGHT,annualization='Weekly seasonal means * scenario W * 7/12 or 5/12. W=52 base,48 cautious; not 365/7; not 48/52 demand scaling.',
      main_cases=MAIN,diagnostic_cases=['PUBLISHED_SELECTED_DIRECT','PUBLISHED_HYBRID_ADD'],
      budget_boundary='Existing variable costs, crew/MRO proxies and own fare forgone retained. Lease/purchase excluded from MAIN by user; financing separately UNKNOWN_NOT_ZERO. Station/IT/insurance/launch/cash additions belong to budget assembly.',
      completed_handoff=True,blocking_dependencies=[])
    dump('network_map_and_frozen_chains.json',metadata)
    dump('CASES.json',dict(metadata=metadata,cases=annual,seasons=season_totals,joint_OD_proof=invariants,
      omissions=['purchase_or_lease_financing_separate_not_zero','fixed_staff_net_of_included_crew','fixed_base_services_net_of_ground_and_MRO',
        'insurance','IT_distribution_net_of_fare_definition','launch','overnight_rooms_without_roster','IRROPS_without_incidence',
        'spares_inventory_deposits_cash_not_same_as_expense'],physical_calendar='NOT_BUILT; no approved dates/slots/turns/rosters. Use api.runtime_calendar only for season-average scenario months after entry.'))
    table('checks.csv',checks)
    dump('validation.json',dict(status='PASS',completed_handoff=True,checks=len(checks),failed_checks=0,
      owner_commit=OWNER,snapshot_files=len(current_manifest),snapshot_hashes_verified=True,main_fixed_cases=5,scenarios=['base','cautious'],
      independent_seasonal_calculator=True,pinned_hub_and_direct_code_replayed=True,
      direct_search_universe_empty=True,global_search_called=False,main_pipeline_called=False,
      reproduced_deck_rounded=[455,113,568],deck113_568_are_full_network_attribution_not_repriced_fixed_network=True,
      fixed_hybrid_result_mln=B('HYBRID')['result_mln_unrounded'],local_reserve_fleet=11,published_single_reserve_conditional_fleet=10,
      shared_OD_count=len(hset&dset),hub_transfer_OD_count=sum(r['accepted'] for r in filters),new_prices=False,
      airport_raw_owner_hash_mismatch_disclosed=True,standalone_annual_not_full_2027=True,python=sys.version,
      dependencies=dict(numpy=np.__version__,pandas=pd.__version__),write_boundary=str(HERE)))
    dump('handoff.json',dict(status='COMPLETED',role='P40 fixed seasonal hybrid physical and variable-financial calculator',
      owner_commit=OWNER,blocking_dependencies=[],waiting_for_budget_agent=False,write_boundary=str(HERE),
      api='api.py: expenses_for(case_id,scenario,season="annual"); runtime_calendar(case_id,scenario,entry_month,months=12)',
      main_files=['CASES.json','annual_results.csv','component_ledger.csv','seasonal_exposures.csv','route_ledger.csv','joint_OD_proof.json','fleet_requirements.csv','budget_boundary.json'],
      major_findings=['455/113/568 rounded reproduced for publication attribution','Repriced fixed exact two direct chains yield143.322510mln and hybrid598.293890mln',
        'Hub+direct OD sets disjoint under frozen direct/circuity filter','Local geographic reserve rule needs11; deck10 has conditional reserve coverage',
        'Cautious same fixed network kept; annual steady-state after entry, not full2027; financing excluded by user but unknown notzero'],
      global_search=False,main_pipeline=False,deck_edited=False,git_mutations=False,new_prices=False))
    print(json.dumps(dict(status='PASS',checks=len(checks),hub_mln=B('OMS')['result_mln_unrounded'],
       direct_fixed_mln=B('DIRECT2')['result_mln_unrounded'],hybrid_fixed_mln=B('HYBRID')['result_mln_unrounded'],
       direct_published_mln=B('PUBLISHED_SELECTED_DIRECT')['result_mln_unrounded'],hybrid_published_mln=B('PUBLISHED_HYBRID_ADD')['result_mln_unrounded'])))

if __name__=='__main__':run()
