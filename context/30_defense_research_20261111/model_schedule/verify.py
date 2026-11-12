"""Bounded fixed-network replay and constructive schedule; no network search.
Run with pandas/numpy available and PYTHONDONTWRITEBYTECODE=1.
"""
import csv, json, math, sys, hashlib
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

OUT=Path(__file__).resolve().parent
IN=OUT.parent/'inputs/model_schedule'
LATEST=IN/'latest'
sys.dont_write_bytecode=True
sys.path.insert(0,str(LATEST/'src'))
import network_model as m
import pandas, numpy, platform
DATE='2026-11-11'
PIN='0b0fbcb742ea2e54e05b80a5b8e890200fd5daae'
def read(p):
    with p.open() as f:return list(csv.DictReader(f))
def write(name,rows):
    rows=[dict(r,checked_date=DATE) for r in rows]
    with (OUT/name).open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)
def dump(n,x):(OUT/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')

D=m.Demand(); AS=m.load_assumptions(); published=read(LATEST/'data/processed/network_routes.csv')
networks=[]; fixed=[];checks=[]; initial=None
for s in ('base','base_sub'):
    rows=[r for r in published if r['scenario']==s and r['variant']=='Хаб OMS']
    sp=[r['to'] for r in rows]
    _,r=m.hub_network('OMS',D,AS[s],'base',list(D.n.index),fixed_spokes=sp)
    legs,tr,h,c,rev,ol,ot,n,mg,fg,sub=r
    networks.append(dict(id='OMS_CURRENT_'+s.upper(),scenario=s,spokes=sp,flights_week=n,model_block_h_week=h,working=math.ceil(h/70),reserve=1,revenue_net_rub_year=rev*52,cost_rub_year=c*52,contribution_rub_year=(rev-c)*52,route_grant_rub_year=sub*52,forgone_rw_revenue_rub_year=fg*52))
    for x,l in legs.items():
        checks.append(dict(check='published_frequency',network=networks[-1]['id'],route='OMS-'+x,pass_=l['freq']==int(next(v for v in rows if v['to']==x)['freq_week_each_way'])))
        fixed.append(dict(network_id=networks[-1]['id'],scenario=s,unit='hub_spoke',origin='OMS',destination=x,frequency_each_direction_week=l['freq'],directed_flights_week=2*l['freq'],model_block_h_oneway=l['block_h'],model_block_h_week=2*l['freq']*l['block_h'],status='FROZEN_PUBLISHED_REPLAY',source=f'{PIN}:data/processed/network_routes.csv;src/network_model.py'))

# The published 3-aircraft ramp fixes composition, but does not export frequencies.
sp=['MOW','IKT','GOJ','VOG','NOZ','UFA']; _,r=m.hub_network('OMS',D,AS['base'],'base',list(D.n.index),fixed_spokes=sp)
legs,tr,h,c,rev,ol,ot,n,mg,fg,sub=r;initial=legs
networks.append(dict(id='OMS_RAMP3_BASE',scenario='base',spokes=sp,flights_week=n,model_block_h_week=h,working=math.ceil(h/70),reserve=1,revenue_net_rub_year=rev*52,cost_rub_year=c*52,contribution_rub_year=(rev-c)*52,route_grant_rub_year=sub*52,team_selected='UNKNOWN',period='H2 2027 scenario; no exact launch date approved'))
for x,l in legs.items():fixed.append(dict(network_id='OMS_RAMP3_BASE',scenario='base',unit='hub_spoke',origin='OMS',destination=x,frequency_each_direction_week=l['freq'],directed_flights_week=2*l['freq'],model_block_h_oneway=l['block_h'],model_block_h_week=2*l['freq']*l['block_h'],status='COMPOSITION_PUBLISHED_FREQUENCY_FIXED_REPLAY',source=f'{PIN}:data/processed/fleet_ramp.csv;src/network_model.py'))
for x in ('MOW','KUF','KJA'):fixed.append(dict(network_id='OMS_PILOT_H1_2027',scenario='roadmap',unit='hub_spoke',origin='OMS',destination=x,frequency_each_direction_week='UNKNOWN',directed_flights_week='UNKNOWN',model_block_h_oneway='UNKNOWN',model_block_h_week='UNKNOWN',status='PUBLISHED_ROADMAP_NO_FREQUENCY',source=f'{PIN}:docs/26_steps_2_4_5.md:43'))

# Preserve the actual published direct triangles and joint pair sharing.
for s in ('base','base_sub'):
    rows=[r for r in published if r['scenario']==s and r['variant'].startswith('Прямые ')]
    grouped=defaultdict(list)
    for row in rows:grouped[row['variant']].append(row)
    selection=[]
    for name,rr in grouped.items():
        B,X,Y=name.split(' ',1)[1].split('-');ls=[]
        for v in rr:
            a,b=v['from'],v['to'];km=D.km(a,b);f=int(v['freq_week_each_way'])
            ls.append(dict(a=a,b=b,km=km,south=D.south(a,b),competitive=D.has_direct(a,b),dem=D.get(a,b,'base')/104,seg=D.seg(a,b,'base')/104,rw_now=m.rw_pax_week(a,b,AS[s]),freq=f))
            bh=m.leg_cost(AS[s],km,D.south(a,b),0)[0]
            fixed.append(dict(network_id='DIRECT_CURRENT_'+s.upper(),scenario=s,unit=name,origin=a,destination=b,frequency_each_direction_week=f,directed_flights_week=2*f,model_block_h_oneway=bh,model_block_h_week=2*f*bh,status='FROZEN_PUBLISHED_TRIANGLE',source=f'{PIN}:data/processed/network_routes.csv;src/network_model.py'))
        selection.append((0,B,X,Y,0,0,0,0,ls))
    rr=m.direct_network(D,AS[s],'base',list(D.n.index),fixed_selection=selection)
    h=sum(x[4] for x in rr);c=sum(x[5] for x in rr);rev=sum(x[6] for x in rr)
    networks.append(dict(id='DIRECT_CURRENT_'+s.upper(),scenario=s,triangles=list(grouped),flights_week=sum(2*l['freq'] for x in rr for l in x[8]),model_block_h_week=h,working=math.ceil(h/70),reserve=1,revenue_net_rub_year=rev*52,cost_rub_year=c*52,contribution_rub_year=(rev-c)*52,route_grant_rub_year=sum(x[11] for x in rr)*52,resource_limits='same fleet cap 10; search caps 4/6/8/10; 8-12 triangles, not 8-12 physical pairs'))
write('fixed_networks.csv',fixed)

# Explicit scenario blocks in minutes. These are NOT dispatch times or geometric estimates.
# Bounds deliberately preserve uncertainty; MOW is an unresolved city market.
blocks={'MOW':(195,210,255),'IKT':(180,210,240),'GOJ':(165,195,225),'VOG':(195,225,270),'NOZ':(90,105,135),'UFA':(105,135,165)}
tz={'OMS':'Asia/Omsk','MOW':'Europe/Moscow','IKT':'Asia/Irkutsk','GOJ':'Europe/Moscow','VOG':'Europe/Volgograd','NOZ':'Asia/Novokuznetsk','UFA':'Asia/Yekaterinburg'}
utc=timezone.utc; start=datetime(2027,9,6,tzinfo=ZoneInfo(tz['OMS']))
# 22 roundtrips, exactly the 3-aircraft ramp frequencies, two operating slots plus one spare.
# Spread thin routes across the week; two daily departure waves are only a construction.
routes=['MOW','IKT','GOJ','VOG','NOZ','UFA','IKT','GOJ','VOG','IKT','UFA','MOW','IKT','GOJ','VOG','NOZ','UFA','IKT','GOJ','VOG','NOZ','MOW']
routes[3],routes[4]=routes[4],routes[3]
routes[9],routes[10]=routes[10],routes[9]
slots=[(tail,day,hour) for day in range(7) for tail in ('S1','S2') for hour in ([5,17] if day in (1,3,5,6) else [5])]
flights=[]
for i,((tail,day,hour),x) in enumerate(zip(slots,routes)):
    dep=(start+timedelta(days=day,hours=hour)).astimezone(utc)
    for a,b in [('OMS',x),(x,'OMS')]:
        lo,bh,hi=blocks[x];arr=dep+timedelta(minutes=bh)
        flights.append(dict(network_id='OMS_RAMP3_BASE',flight_id=f'F{len(flights)+1:03d}',tail_slot=tail,origin=a,destination=b,departure_utc=dep.isoformat(),arrival_utc=arr.isoformat(),departure_local=dep.astimezone(ZoneInfo(tz[a])).isoformat(),arrival_local=arr.astimezone(ZoneInfo(tz[b])).isoformat(),local_arrival_day_delta=(arr.astimezone(ZoneInfo(tz[b])).date()-dep.astimezone(ZoneInfo(tz[a])).date()).days,block_min=bh,scenario_block_low_min=lo,scenario_block_high_min=hi,turnaround_assumed_min=60,aircraft='SJ-100 modeled as SSJ-95B 100 seats; actual modification UNKNOWN',airport_status='UNKNOWN_MOW_AIRPORT' if x=='MOW' else 'IATA_NAMED',status='SCENARIO_CONSTRUCTION_NOT_APPROVED',source='freeze OMS_RAMP3_BASE; scheduling_notes.md scenario intervals'))
        dep=arr+timedelta(minutes=60)
write('proposed_initial_flights.csv',flights)
dt=lambda s:datetime.fromisoformat(s)
rot=[]
for tail in ('S1','S2'):
    ff=sorted([f for f in flights if f['tail_slot']==tail],key=lambda f:f['departure_utc']);prev=None
    for f in ff:
        gap=(dt(f['departure_utc'])-dt(prev['arrival_utc'])).total_seconds()/60 if prev else None
        highgap=gap-(prev['scenario_block_high_min']-prev['block_min']) if prev else None
        good=prev is None or (prev['destination']==f['origin'] and gap>=60)
        rot.append(dict(tail_slot=tail,check_id=f['flight_id'],start_airport=f['origin'],end_airport=f['destination'],start_utc=f['departure_utc'],end_utc=f['arrival_utc'],ground_gap_min=gap if gap is not None else 'INITIAL_AT_OMS_ASSUMED',continuity_status='PASS_ARITHMETIC' if good else 'FAIL',overnight_airport=f['origin'] if prev and dt(prev['arrival_utc']).astimezone(ZoneInfo(tz[f['origin']])).date()!=dt(f['departure_utc']).astimezone(ZoneInfo(tz[f['origin']])).date() else '',weekly_block_h='',upper_bound_weekly_block_h='',operational_status='UNKNOWN crew duty/base/MRO/slots/airport-hours; turnaround 60 is assumption',source='proposed_initial_flights.csv'))
        checks.append(dict(check='rotation_continuity',tail=tail,flight=f['flight_id'],pass_=good));prev=f
        rot[-1].update(ground_gap_if_preceding_leg_high_min=highgap if highgap is not None else 'UNKNOWN_INITIAL',high_block_turn_status='NOT_APPLICABLE_INITIAL' if highgap is None else 'FAIL_60_MIN_ASSUMED_TURN' if highgap<60 else 'PASS_ARITHMETIC_ONLY')
    hours=sum(f['block_min'] for f in ff)/60;upper=sum(f['scenario_block_high_min'] for f in ff)/60
    checks.append(dict(check='nominal_weekly_70h',tail=tail,pass_=hours<=70))
    byday=defaultdict(float)
    for f in ff:byday[f['departure_local'][:10]]+=f['block_min']/60
    for day,dayh in byday.items():
        rot.append(dict(tail_slot=tail,check_id='DAILY_'+day,weekly_block_h='',daily_departure_attributed_block_h=dayh,continuity_status='MEASUREMENT_ONLY',operational_status='ABOVE_10H_DAILY_PLANNING_AVERAGE' if dayh>10 else 'WITHIN_10H_DAILY_PLANNING_AVERAGE',source='proposed_initial_flights.csv; attribution by local departure day, not crew duty'))
    rot.append(dict(tail_slot=tail,check_id='WEEK_AND_WRAP',start_airport=ff[0]['origin'],end_airport=ff[-1]['destination'],start_utc=ff[0]['departure_utc'],end_utc=ff[-1]['arrival_utc'],ground_gap_min=((dt(ff[0]['departure_utc'])+timedelta(days=7))-dt(ff[-1]['arrival_utc'])).total_seconds()/60,continuity_status='PASS_ARITHMETIC',weekly_block_h=hours,upper_bound_weekly_block_h=upper,operational_status='CONDITIONAL nominal <=70 h/week' if hours<=70 else 'FAIL_70_H_WEEK',source='proposed_initial_flights.csv'))
rot.append(dict(tail_slot='S3',check_id='RESERVE',start_airport='OMS',end_airport='OMS',weekly_block_h=0,continuity_status='ASSUMED_AVAILABLE',operational_status='UNKNOWN actual tail/release/serviceability; no double allocation',source='network.csv:spare_aircraft=1'))
write('rotation_checks.csv',rot)
connections=[]
for f in flights:
    if f['destination']!='OMS':continue
    for g in flights:
        if g['origin']!='OMS' or f['origin']==g['destination']:continue
        wait=(dt(g['departure_utc'])-dt(f['arrival_utc'])).total_seconds()/60
        if 45<=wait<=240:
            connections.append(dict(inbound_id=f['flight_id'],outbound_id=g['flight_id'],origin=f['origin'],via='OMS',destination=g['destination'],arrival_utc=f['arrival_utc'],departure_utc=g['departure_utc'],arrival_local=f['arrival_local'],departure_local=g['departure_local'],wait_min=wait,arithmetic_status='WITHIN_SCENARIO_45_240',mct_min='UNKNOWN',through_ticket='UNKNOWN',airport_status='CONDITIONAL_MOW_UNRESOLVED' if 'MOW' in (f['origin'],g['destination']) else 'OMS_NAMED',operational_status='UNKNOWN_NOT_SELLABLE_CERTIFICATE',passengers_added=0,source='proposed_initial_flights.csv;45-240 min screening assumption'))
write('connection_checks.csv',connections)
candidate_count=len(connections)
# Report the earliest weekly-recurring connection to every other spoke, including gaps.
connections=[]
for f in flights:
    if f['destination']!='OMS':continue
    for dest in initial:
        if dest==f['origin']:continue
        opts=[]
        for g in flights:
            if g['origin']!='OMS' or g['destination']!=dest:continue
            departure=dt(g['departure_utc'])
            while departure<dt(f['arrival_utc'])+timedelta(minutes=45):departure+=timedelta(days=7)
            opts.append(((departure-dt(f['arrival_utc'])).total_seconds()/60,g,departure))
        wait,g,departure=min(opts,key=lambda z:z[0])
        connections.append(dict(inbound_id=f['flight_id'],outbound_id=g['flight_id'],origin=f['origin'],via='OMS',destination=dest,arrival_utc=f['arrival_utc'],departure_utc=departure.isoformat(),arrival_local=f['arrival_local'],departure_local=departure.astimezone(ZoneInfo(tz['OMS'])).isoformat(),wait_min=wait,arithmetic_status='WITHIN_SCENARIO_45_240' if wait<=240 else 'FAIL_SCENARIO_MAX_240_MIN',mct_min='UNKNOWN',through_ticket='UNKNOWN',airport_status='CONDITIONAL_MOW_UNRESOLVED' if 'MOW' in (f['origin'],dest) else 'OMS_NAMED',operational_status='UNKNOWN_NOT_SELLABLE_CERTIFICATE',passengers_added=0,source='proposed_initial_flights.csv;weekly recurrence;45-240 min screening assumption'))
write('connection_checks.csv',connections)
for x,l in initial.items():
    for a,b in [('OMS',x),(x,'OMS')]:checks.append(dict(check='schedule_frequency',route=a+'-'+b,pass_=sum(f['origin']==a and f['destination']==b for f in flights)==l['freq']))
for f in flights:
    checks.append(dict(check='utc_local_duration',flight=f['flight_id'],pass_=abs((dt(f['arrival_local'])-dt(f['departure_local'])).total_seconds()/60-f['block_min'])<1e-8))
review=read(IN/'review/fuel_sensitivity.csv');v=next(x for x in review if x['network']=='fixed_new_network' and x['credit_rub_per_t']=='32930')
checks.append(dict(check='late_review_exact_base',pass_=abs(networks[0]['contribution_rub_year']-float(v['contribution_rub']))<0.01))
for net in networks:
    pub=[x for x in read(LATEST/'data/processed/network_summary.csv') if x['scenario']==net['scenario'] and (x['hub']=='OMS' if net['id'].startswith('OMS_CURRENT') else x['variant'].startswith('Прямые'))]
    if net['id']=='OMS_RAMP3_BASE':continue
    checks.append(dict(check='rounded_published_result',network=net['id'],pass_=round(net['contribution_rub_year']/1e6)==int(pub[0]['result_mln_year'])))
freeze=dict(checked_date=DATE,pin=PIN,selection='OMS team strategy retained; ramp3 is scenario, TEAM_SELECTED UNKNOWN',networks=networks,calendar=dict(schedule_week='2027-09-06/2027-09-12',status='SCENARIO_H2_2027_NOT_APPLICATION',annual_base_weeks=52,cautious_weeks=48,cautious_note='annual demand concentrated in 48 weeks, not automatic 4/52 demand loss'),pilot=dict(id='OMS_PILOT_H1_2027',spokes=['MOW','KUF','KJA'],frequency='UNKNOWN',fleet='up to 3 existing SSJ, conditional release',separate_from_ramp=True),type=dict(model='100-seat SSJ-95B analog for SJ-100; actual SJ100/PD8 certification/registration/delivery UNKNOWN',spare=1),ledger=dict(revenue='net ticket revenue after forgone existing RW revenue; transfer fare once, shared across two legs; route subsidy included in revenue when selected',cost='fuel net credit + cycle + hourly MRO/crew/navigation + ground/deice + passenger cost',excluded='lease/capital/base/startup/office/fullPnL/tax cash timing UNKNOWN; do not call result profit',fuel_credit_rub_per_t=dict(base=32930,cautious=3024),support='base_sub reselected or baseline retained by hub_best; not fixed-network grant delta',model_block='0.5 + exact great-circle km * regional route_factor / 750; ECONOMIC PROXY ONLY'),prior_packages=dict(fuel_review='c5ec29f7a89e457ed104026877b8f8d3b6101ca9:late_fuel_review; old +952 base_sub belongs to older code without current fare choice',dashboard='5101302f93c349268f4ba0ff26832ff261e1a9e7:methods_final/freeze; TEAM_ACCEPTED false; distinct input model',dated='f99d6cd52dcc06995bf984fddd2f057226243b06:programs.json covers OMS1/OMS4/OMS8 and others, not current ramp6; only primary timetable orientation reused'),operational_status='UNKNOWN; constructive arithmetic only')
dump('freeze.json',freeze)
index={x['path']:x['sha'] for x in json.loads((IN/'latest_tree_index.json').read_text())};manifest=[]
for p in sorted(LATEST.rglob('*')):
    if not p.is_file():continue
    b=p.read_bytes();rel=p.relative_to(LATEST).as_posix();blob=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest();expected=index.get(rel)
    manifest.append(dict(local_path=str(p),path=rel,commit=PIN if expected else 'UNTRACKED_RAW_FROM_PRIOR_AUDIT',git_blob=blob,expected_git_blob=expected,sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),status='MATCH_EXACT_PIN' if blob==expected else 'RAW_DEPENDENCY_NOT_IN_GIT' if expected is None else 'MISMATCH'))
    checks.append(dict(check='input_blob',path=rel,pass_=expected is None or expected==blob))
for entry in json.loads((IN/'source_receipts.json').read_text()):
    p=IN/entry['local_path'];b=p.read_bytes();blob=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
    manifest.append(dict(entry,sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),status='MATCH_EXACT_PIN' if blob==entry['git_blob'] else 'MISMATCH'))
    checks.append(dict(check='auxiliary_source_blob',path=entry['path'],pass_=blob==entry['git_blob']))
dump('replay_inputs_manifest.json',dict(checked_date=DATE,files=manifest,environment=dict(python=platform.python_version(),pandas=pandas.__version__,numpy=numpy.__version__),raw_note='TOCHNO copied from prior bounded audit sandbox; absent from git, hash preserved, no new source verification',run='PYTHONDONTWRITEBYTECODE=1 <python-with-pandas-numpy> '+str(OUT/'verify.py')))
dump('validation.json',dict(checked_date=DATE,checks=checks,failed=sum(not c['pass_'] for c in checks),flights=len(flights),connections_screened=len(connections),connections_within_scenario=sum(c['arithmetic_status']=='WITHIN_SCENARIO_45_240' for c in connections),schedule_nominal_h=sum(f['block_min'] for f in flights)/60,schedule_upper_h=sum(f['scenario_block_high_min'] for f in flights)/60,high_block_turn_failures=sum(r.get('high_block_turn_status')=='FAIL_60_MIN_ASSUMED_TURN' for r in rot),upper_bound_fleet_capacity_status='FAIL_TWO_WORKING_TAILS_140_H_WEEK',operational_approval='UNKNOWN',notes='Arithmetic PASS is not airline approval; 70h is weekly average, daily peak and crew duty unresolved.'))
print(json.dumps(dict(failed=sum(not c['pass_'] for c in checks),networks=networks,flights=len(flights),connections=len(connections)),ensure_ascii=False,indent=2))
sys.exit(1 if any(not c['pass_'] for c in checks) else 0)
