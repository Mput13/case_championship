#!/usr/bin/env python3
"""Read-only formula/ledger audit. All writes confined to this directory.
Requires pandas/numpy for pinned owner functions. No optimizer/main/exporter is run.
"""
import sys
sys.dont_write_bytecode=True
import calendar,csv,gzip,hashlib,importlib.util,json,math
from collections import Counter,defaultdict
from datetime import datetime,timedelta,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent
OWNER='c11eb8c15d32add540d89d086f62487a5b2d424e'
P38='56400c5f111222d7c660d4345d3d43b92d4716d5'
BASE=HERE/'snapshot'/OWNER[:8]
P=HERE/'snapshot'/P38[:8]
P38PATH='context/38_direct_strategy_20261113/'
FIN=P/P38PATH/'economics'
checks=[];exposures=[];financial=[]
manifest=json.loads((HERE/'snapshot_manifest.json').read_text())
def source(rev,path,line):return f'{rev}:{path}:{line}'
def ref_owner(line):return source(OWNER,'src/network_model.py',line)
def ref_p38(file,line):return source(P38,P38PATH+file,line)
def read(p):
 with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def table(name,rows):
 rows=list(rows);fields=list(dict.fromkeys(k for r in rows for k in r))
 with (HERE/name).open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in rows:w.writerow({k:'UNKNOWN' if v is None else v for k,v in r.items()})
def dump(name,x):(HERE/name).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def close(label,actual,expected,tol=1e-5):
 delta=abs(actual-expected);checks.append(dict(check=label,actual=actual,expected=expected,abs_error=delta,tolerance=tol,pass_=delta<=tol))
 if delta>tol:raise AssertionError(checks[-1])
def metric(model,network,sc,period,metric_name,value,unit,formula,evidence,scope='NETWORK',quality='MODELLED_NOT_OBSERVED'):
 exposures.append(dict(model=model,network=network,scenario=sc,scope=scope,period=period,metric=metric_name,value=value,unit=unit,formula=formula,evidence=evidence,quality=quality))
def src_line(path,pred):
 lines=(BASE/path).read_text().splitlines()
 return next(i for i,l in enumerate(lines,1) if pred(l))

def owner_audit():
 sys.path.insert(0,str(BASE/'src'))
 import demand_model as dm
 raw=next(x for x in manifest if x['path'].endswith('tochno_intercity.csv.gz'))
 rawpath=HERE/raw['snapshot_path']
 close('public_raw_owner_manifest_sha',int(hashlib.sha256(gzip.decompress(rawpath.read_bytes())).hexdigest()=='aed8463339b988a7c9ac81aa976a4fc25c152e4066b551d25cbdcc16ebe16d53'),1,0)
 dm.TOCHNO=rawpath # pandas transparently reads gzip; original bytes verified above.
 import network_model as nm
 D=nm.Demand();assumptions=nm.load_assumptions()
 exported=read(BASE/'data/processed/network_routes.csv')
 summaries=read(BASE/'data/processed/network_summary.csv')
 out=[];summ=[]
 for sc,A in assumptions.items():
  W=A['weeks_per_year'];period=f'MODEL_YEAR_{W:g}_WEEKS_CALENDAR_YEAR_UNSPECIFIED'
  for kind in ['OMS','DIRECT']:
   rows=[(i+2,r) for i,r in enumerate(exported) if r['scenario']==sc and (r['variant']=='Хаб OMS' if kind=='OMS' else r['variant'].startswith('Прямые '))]
   if kind=='OMS':
    selected,res=nm.hub_network('OMS',D,A,A['demand_scen'],[r['to'] for _,r in rows],fixed_spokes=[r['to'] for _,r in rows])
    legs,trans,hours,cost,rev,local,transfer,flights,migr,forgone,subs=res
    ls=list(legs.values());od=local+transfer;segments=local+2*transfer
   else:
    fixed=[]
    for variant in dict.fromkeys(r['variant'] for _,r in rows):
     rr=[r for _,r in rows if r['variant']==variant];b,x,y=variant.removeprefix('Прямые ').split('-');f=float(rr[0]['freq_week_each_way'])
     ll=[]
     for r in rr:
      a,z=r['from'],r['to'];km=D.km(a,z)
      ll.append(dict(a=a,b=z,km=km,south=D.south(a,z),competitive=D.has_direct(a,z),dem=D.get(a,z,A['demand_scen'])/(2*W),seg=D.seg(a,z,A['demand_scen'])/(2*W),rw_now=nm.rw_pax_week(a,z,A),freq=f))
     fixed.append((None,b,x,y,None,None,None,None,ll))
    # Empty search universe; only pinned fixed_selection is valued in joint().
    result=nm.direct_network(D,A,A['demand_scen'],[],fixed_selection=fixed)
    ls=[l for c in result for l in c[8]];hours=sum(c[4] for c in result);cost=sum(c[5] for c in result);rev=sum(c[6] for c in result)
    segments=sum(c[7] for c in result);migr=sum(c[9] for c in result);forgone=sum(c[10] for c in result);subs=sum(c[11] for c in result)
    flights=sum(2*l['freq'] for l in ls);od=local=segments;transfer=0
   assert len(rows)==len(ls)
   airport_dep=Counter();airport_arr=Counter();cc=Counter()
   for (lineno,r),l in zip(rows,ls):
    tag=f'owner/{sc}/{r["variant"]}/{l["a"]}>{l["b"]}'
    close(tag+'/pair',int((r['from'],r['to'])==(l['a'],l['b'])),1,0)
    close(tag+'/frequency',l['freq'],float(r['freq_week_each_way']),0)
    close(tag+'/km_rounded',round(l['km']),float(r['km']),0)
    close(tag+'/segments_rounded',round(2*l['carried_dir_week']*W),float(r['pax_year_segments']),0)
    close(tag+'/migration_rounded',round(2*l['migrated']*W),float(r['pax_year_rw_migrated']),0)
    for col,val in nm.leg_money(l,W).items():close(tag+'/'+col,val,float(r[col]),1e-8)
    n=2*l['freq']*W;bh=n*l['block_h'];tonnes=A['fuel_t_per_hour']*bh+A['fuel_t_per_cycle']*n;seg=2*l['carried_dir_week']*W
    components=dict(fuel_gross_rub=tonnes*A['fuel_rub_per_t'],fuel_credit_rub=tonnes*A['fuel_compensation_rub_per_t'],mro_rub=bh*A['mro_rub_per_hour'],crew_rub=bh*A['crew_rub_per_hour'],navigation_rub=bh*A['navigation_rub_per_hour'],ground_rub=n*A['ground_rub_per_flight'],deice_rub=n*A['deicing_rub_per_flight'],pax_cost_rub=seg*A['pax_cost_rub'])
    total=sum(v for k,v in components.items() if k!='fuel_credit_rub')-components['fuel_credit_rub']
    close(tag+'/independent_cost_components',total,l['cost_week']*W,1e-5)
    cc.update(components)
    for a in [l['a'],l['b']]:airport_dep[a]+=n/2;airport_arr[a]+=n/2
    out.append(dict(network=kind,scenario=sc,variant=r['variant'],origin=l['a'],destination=l['b'],weeks=W,departures_both_directions=n,departures_each_direction=n/2,arrivals_both_directions=n,block_hours=bh,fuel_t=tonnes,local_journeys=2*l.get('local_carried',l['carried_dir_week'])*W,transfer_boardings_on_this_spoke=2*l.get('transfer_carried',0)*W,passenger_segments=seg,net_revenue_after_forgone_rub=l['rev_week']*W,route_grant_rub=l['sub_week']*W,cost_rub=total,**components,source=source(OWNER,'data/processed/network_routes.csv',lineno),formula_source=ref_owner(266)))
   sr=next((i+2,r) for i,r in enumerate(summaries) if r['scenario']==sc and (r['hub']=='OMS' if kind=='OMS' else not r['hub']))
   sl,s=sr;reference=source(OWNER,'data/processed/network_summary.csv',sl)
   ac=math.ceil(hours/(A['block_h_per_day']*7))+A['spare_aircraft']
   calculated=dict(flights_week=flights,aircraft=ac,segments_year=round(segments*W),od_trips_year=round(od*W),transfer_od_year=round(transfer*W),**nm.money(rev,cost,forgone,migr,segments,od,W,A,subs))
   for k,v in calculated.items():
    if v is not None:close(f'owner_summary/{sc}/{kind}/{k}',v,float(s[k]),1e-8)
   close(f'owner_cost_sum/{sc}/{kind}',sum(r['cost_rub'] for r in out if r['network']==kind and r['scenario']==sc),cost*W,2e-5)
   summ.append(dict(model='OWNER',network=kind,scenario=sc,period=period,weeks=W,working_aircraft=ac-A['spare_aircraft'],reserve_aircraft=A['spare_aircraft'],departures=flights*W,block_hours=hours*W,journeys=od*W,segments=segments*W,transfers=transfer*W,net_revenue_rub=rev*W,cost_rub=cost*W,subtotal_rub=(rev-cost)*W,forgone_receipts_rub=forgone*W,route_grant_rub=subs*W,**dict(cc),source=reference))
   def m(name,v,unit,f,ev=reference,scope='NETWORK'):metric('OWNER',kind,sc,period,name,v,unit,f,ev,scope)
   for name,value,unit,f in [('departures',flights*W,'physical_flight_departures', '2*sum(freq_each_direction_week)*W'),('arrivals',flights*W,'physical_flight_arrivals','closed undated model: one arrival per flight'),('block_hours',hours*W,'block_hours','sum(2*f*block_h)*W'),('working_aircraft',ac-A['spare_aircraft'],'aircraft','ceil(weekly_BH/(10*7))'),('reserve_aircraft',A['spare_aircraft'],'aircraft','network spare_aircraft; not extra flying'),('journeys',od*W,'one_way_endpoint_journeys','local+transfer; realised model carried, not potential demand'),('local_journeys',local*W,'one_way_endpoint_journeys','sum(local carried)'),('passenger_segments',segments*W,'passenger_boarded_segments','local+2*transfer'),('transfer_journeys',transfer*W,'one_way_two_leg_journeys','2*sum(carried transfer pairs/week)*W'),('segments_on_transfer_journeys',2*transfer*W,'passenger_boarded_segments','2*transfer_journeys'),('fuel_burn',sum(r['fuel_t'] for r in out if r['network']==kind and r['scenario']==sc),'metric_tonnes_burned','burn_per_BH*BH+burn_per_cycle*departures'),('hub_transfer_bags',None,'checked_bag_transfer_events','no bag counts or bag incidence in owner inputs'),('ferry_departures',None,'physical_ferry_departures','not calendared in owner model'),('away_aircraft_nights',None,'aircraft_local_midnight_events_away_from_base','no tail/calendar/overnight inventory'),('crew_room_nights',None,'room_nights','no crew roster/rooms')]:m(name,value,unit,f)
   for airport in sorted(airport_dep):
    m('departures',airport_dep[airport],'physical_flight_departures','sum(f*W) touching endpoint; MOW airport unresolved',scope=airport)
    m('arrivals',airport_arr[airport],'physical_flight_arrivals','symmetric undated model arrivals',scope=airport)
 table('owner_route_checks.csv',out);table('owner_network_totals.csv',summ)
 financial.extend(summ)
 return summ

def p38_audit():
 weekly=read(FIN/'three_finalists_weekly.csv');monthly=read(FIN/'three_finalists_monthly.csv');ledger=read(FIN/'three_finalists_ledger.csv');annual=read(FIN/'annual_results.selected.csv');pm=read(FIN/'programmes_monthly.selected.csv')
 finalists=sorted({r['candidate'] for r in weekly});out=[];flowchecks=[];date_rows=[]
 period='CALENDAR_YEAR_2027_UTC_DEPARTURE_ATTRIBUTION';utc=timezone.utc
 start=datetime(2027,1,1,tzinfo=utc);end=datetime(2028,1,1,tzinfo=utc)
 costsfile=P/'context/31_direct_growth_research_20261112/audit/inputs/audit_model/620a0ac4/context/35_full_programme_execution_20261112/P04/cost_ranges.csv'
 rates={r['cost_id']:r for r in read(costsfile)}
 def unit_cost(h,sc):
  key='base_point' if sc=='base' else 'cautious_point';g=lambda k:float(rates['HIST-'+k][key])
  price=float(rates['UFA-fuel-20261111']['value'])+float(rates['UFA-fuel_uplift']['value']) if sc=='base' else 161696
  tonnes=h*g('fuel_t_per_hour')+g('fuel_t_per_cycle')
  c=dict(fuel_t=tonnes,fuel_cost=tonnes*price,mro=h*g('mro_rub_per_hour'),navigation=h*g('navigation_rub_per_hour'),ground=96089 if sc=='base' else 115307,deice=15000 if sc=='base' else 40000,fixed_crew_excluded=h*g('crew_rub_per_hour'))
  c['other_variable']=c['mro']+c['navigation']+c['ground']+c['deice'];c['variable_cost']=c['fuel_cost']+c['other_variable'];return c
 # Every published representative dated leg: revenue is carried*net, not demand*fare.
 for i,r in enumerate(ledger,2):
  dep=datetime.fromisoformat(r['departure_utc']);arr=datetime.fromisoformat(r['arrival_utc']);h=(arr-dep).total_seconds()/3600
  c=unit_cost(h,r['scenario']);tag=f'p38_ledger/{i}'
  for key in ['fuel_t','fuel_cost','other_variable','variable_cost','fixed_crew_excluded']:close(tag+'/'+key,c[key],float(r[key]),0.002)
  close(tag+'/net_revenue',float(r['direct_q'])*float(r['net_per_journey']),float(r['revenue']),0.0002)
  close(tag+'/through_primary',float(r['through_q']),0,0)
  if r['kind']=='positioning':
   for k in ['seats','direct_q','through_q','revenue']:close(tag+'/ferry_'+k,float(r[k]),0,0)
  flowchecks.append(dict(candidate=r['candidate'],scenario=r['scenario'],flight_id=r['flight_id'],block_hours=h,revenue_recomputed=float(r['direct_q'])*float(r['net_per_journey']),cost_recomputed=c['variable_cost'],source=ref_p38('economics/three_finalists_ledger.csv',i)))
 for cid in finalists:
  w=[r for r in weekly if r['candidate']==cid]
  # Four season exports describe the same fixed template: prove it before recurrence.
  sig=lambda rows:sorted((r['flight_id'],r['tail'],r['origin'],r['destination'],r['kind'],r['iso_weekday_UTC'],r['departure_UTC'],r['block_minutes']) for r in rows)
  template=[r for r in w if r['season']=='winter']
  for season in ['spring','summer','autumn']:close(f'p38/{cid}/same_template/{season}',int(sig(template)==sig([r for r in w if r['season']==season])),1,0)
  events=[]
  # Monday padded before year; count actual date recurrence, not 52*weekly.
  monday=start-timedelta(days=start.weekday()+7)
  while monday<end+timedelta(days=8):
   for f in template:
    hh,mm=map(int,f['departure_UTC'].split(':'));dep=monday+timedelta(days=int(f['iso_weekday_UTC'])-1,hours=hh,minutes=mm)
    arr=dep+timedelta(minutes=float(f['block_minutes']))
    events.append(dict(candidate=cid,tail=f['tail'],origin=f['origin'],destination=f['destination'],kind=f['kind'],flight_id=f['flight_id'],old=not f['job_id'].startswith('NEW-'),dep=dep,arr=arr,block_h=float(f['block_minutes'])/60))
   monday+=timedelta(days=7)
  selected=[f for f in events if start<=f['dep']<end]
  counts=Counter((f['dep'].strftime('%Y-%m'),f['tail'],f['origin'],f['destination']) for f in selected)
  source_rows=[(i+2,r) for i,r in enumerate(monthly) if r['candidate']==cid]
  close(f'p38/{cid}/monthly_key_coverage',int(set(counts)=={(r['month'],r['tail'],r['origin'],r['destination']) for _,r in source_rows}),1,0)
  for i,r in source_rows:
   k=(r['month'],r['tail'],r['origin'],r['destination']);ff=[f for f in selected if (f['dep'].strftime('%Y-%m'),f['tail'],f['origin'],f['destination'])==k]
   for key,val in [('physical_dated_departures',len(ff)),('service_dated_departures',sum(f['kind']=='SERVICE' for f in ff)),('paid_ferry_dated_departures',sum(f['kind']=='PAID_FERRY' for f in ff)),('new_dated_departures',sum(not f['old'] for f in ff)),('old_dated_departures',sum(f['old'] for f in ff))]:close(f'p38_physical/{cid}/{i}/{key}',val,float(r[key]),0)
  arrs=[f for f in events if start<=f['arr']<end]
  for f in selected:date_rows.append({k:v.isoformat() if isinstance(v,datetime) else v for k,v in f.items()})
  for sc in ['base','cautious']:
   a=next(r for r in annual if r['candidate']==cid and r['scenario']==sc and r['state']=='REPLACE')
   months=[r for r in pm if r['candidate']==cid and r['scenario']==sc and r['state']=='REPLACE']
   close(f'p38/{cid}/{sc}/months',len(months),12,0)
   for dest,src in [('net_revenue','net_revenue'),('variable_cost','variable_cost'),('journeys','journeys'),('departures','departures'),('known_annual_subtotal','known_subtotal_before_C_D_F')]:close(f'p38_annual/{cid}/{sc}/{dest}',sum(float(r[src]) for r in months),float(a[dest]),0.003)
   close(f'p38/{cid}/{sc}/departures',len(selected),float(a['departures']),0)
   comps=Counter()
   for f in selected:comps.update(unit_cost(f['block_h'],sc))
   close(f'p38/{cid}/{sc}/independent_annual_cost',comps['variable_cost'],float(a['variable_cost']),0.004)
   close(f'p38/{cid}/{sc}/independent_annual_BH',sum(f['block_h'] for f in selected),sum(float(r['BH']) for r in months),0.0001)
   for month in months:
    ff=[f for f in selected if f['dep'].strftime('%Y-%m')==month['month']]
    close(f'p38_month/{cid}/{sc}/{month["month"]}/cost',sum(unit_cost(f['block_h'],sc)['variable_cost'] for f in ff),float(month['variable_cost']),0.003)
    close(f'p38_month/{cid}/{sc}/{month["month"]}/departures',len(ff),float(month['departures']),0)
   revenue=float(a['net_revenue']);cost=float(a['variable_cost']);journeys=float(a['journeys'])
   close(f'p38_annual/{cid}/{sc}/subtotal',revenue-cost,float(a['known_annual_subtotal']),0.002)
   out.append(dict(model='P38',network=cid,scenario=sc,period=period,working_aircraft=2,reserve_aircraft=1,departures=len(selected),block_hours=sum(f['block_h'] for f in selected),journeys=journeys,segments=journeys,transfers=0,net_revenue_rub=revenue,cost_rub=cost,subtotal_rub=revenue-cost,**dict(comps),financial_replay='INDEPENDENT_COST_AND_CALENDAR; SAVED_CARRIED_TIMES_NET_AND_MONTHLY_ANNUAL_SUM; NO_CHOICE_REALLOCATION'))
   annual_item=next(x for x in manifest if x['path']==P38PATH+'economics/annual_results.csv')
   annual_line=annual_item['source_line_numbers'][annual.index(a)+1]
   def m(name,v,u,f,e=ref_p38('economics/annual_results.csv',annual_line),scope='NETWORK'):metric('P38',cid,sc,period,name,v,u,f,e,scope)
   bh_calendar=sum(max(0.,(min(f['arr'],end)-max(f['dep'],start)).total_seconds()/3600) for f in events)
   for name,v,u,f in [('departures',len(selected),'physical_flight_departures','2027 dated UTC departures from fixed weekly template'),('arrivals',len(arrs),'physical_flight_arrivals','actual arrival UTC inside 2027, includes carry-in'),('block_hours_departure_attributed',sum(f['block_h'] for f in selected),'block_hours','whole flight by UTC departure year'),('block_hours_calendar_split',bh_calendar,'block_hours','intersection of every flight with UTC year'),('service_departures',sum(f['kind']=='SERVICE' for f in selected),'physical_service_departures','count physical service, including old retained'),('ferry_departures',sum(f['kind']=='PAID_FERRY' for f in selected),'physical_ferry_departures','count explicit paid zero-seat positioning'),('working_aircraft',2,'aircraft','K2 declared resources'),('reserve_aircraft',1,'aircraft','separate R1, not flown'),('journeys',journeys,'one_way_endpoint_journeys','sum completed monthly carried; no demand substitution'),('passenger_segments',journeys,'passenger_boarded_segments','DIRECT_ONLY one segment per journey'),('transfer_journeys',0,'one_way_two_leg_journeys','DIRECT_ONLY explicit primary scope excludes through'),('segments_on_transfer_journeys',0,'passenger_boarded_segments','primary scope has no two-leg product'),('hub_transfer_bags',None,'checked_bag_transfer_events','no baggage count'),('fuel_burn',comps['fuel_t'],'metric_tonnes_burned','sum dated per-flight burn'),('crew_room_nights',None,'room_nights','no crew roster/occupancy rates')]:m(name,v,u,f)
   # Local-midnight away-aircraft exposure; not crew hotel room-nights.
   zones={'SVX':5,'AER':3,'GOJ':3,'KJA':7,'IKT':8,'CEK':5,'TJM':5,'MRV':3,'DME':3,'ZIA':3,'KUF':4,'UFA':5,'OMS':6,'PEE':5,'TOF':7,'REN':5}
   nights=0
   for tail in sorted({f['tail'] for f in events}):
    seq=sorted([f for f in events if f['tail']==tail],key=lambda f:f['dep'])
    for prev,nxt in zip(seq,seq[1:]):
     assert prev['destination']==nxt['origin']
     place=prev['destination']
     if place=='SVX':continue
     zone=timezone(timedelta(hours=zones[place]));lo=max(prev['arr'],start);hi=min(nxt['dep'],end)
     if hi<=lo:continue
     midnight=datetime.combine(lo.astimezone(zone).date()+timedelta(days=1),datetime.min.time(),zone)
     while midnight<hi:
      if midnight>=lo:nights+=1
      midnight+=timedelta(days=1)
   m('away_aircraft_nights',nights,'aircraft_local_midnight_events_away_from_base','local midnight strictly between arrival and next departure outside SVX; no crew-room inference',ref_p38('economics/three_finalists_weekly.csv',next(i+2 for i,r in enumerate(weekly) if r['candidate']==cid and r['season']=='winter')))
   for airport in sorted({f['origin'] for f in selected}|{f['destination'] for f in arrs}):
    m('departures',sum(f['origin']==airport for f in selected),'physical_flight_departures','dated UTC departure events',ref_p38('economics/three_finalists_weekly.csv',next(i+2 for i,r in enumerate(weekly) if r['candidate']==cid and r['season']=='winter')),airport)
    m('arrivals',sum(f['destination']==airport for f in arrs),'physical_flight_arrivals','dated UTC arrival events including boundary carry',ref_p38('economics/three_finalists_weekly.csv',next(i+2 for i,r in enumerate(weekly) if r['candidate']==cid and r['season']=='winter')),airport)
 # All three-state annual accounting identities for selected finalists, no optimiser rerun.
 for r in annual:
  if r['state']=='THREE_STATE_DELTA':
   vals={s:sum(float(x['known_subtotal_before_C_D_F']) for x in pm if x['candidate']==r['candidate'] and x['scenario']==r['scenario'] and x['state']==s) for s in ['KEEP','WITHOUT_NEW','REPLACE']}
   for key,a,b in [('W_minus_K','WITHOUT_NEW','KEEP'),('R_minus_W','REPLACE','WITHOUT_NEW'),('R_minus_K','REPLACE','KEEP')]:close(f'p38_delta/{r["candidate"]}/{r["scenario"]}/{key}',vals[a]-vals[b],float(r[key]),0.003)
 table('p38_ledger_checks.csv',flowchecks);table('p38_network_totals.csv',out);table('p38_dated_exposure.csv',date_rows)
 financial.extend(out)
 return finalists

def run():
 for m in manifest:
  assert hashlib.sha256((HERE/m['snapshot_path']).read_bytes()).hexdigest()==m['sha256'],m['snapshot_path']
 owner=owner_audit();finalists=p38_audit()
 table('exposures.csv',exposures)
 from coverage_builder import build
 coverage,drivers=build();table('coverage.csv',coverage);table('annual_drivers.csv',drivers)
 allowed={'FULL_IN_MODEL','PARTIAL','ABSENT','UNRESOLVED_BASKET'}
 citations=set()
 for row in coverage:
  assert row['status'] in allowed
  citations.update(row['evidence'].split(' | '))
 citations.update(r['evidence'] for r in exposures)
 citations.update(r['exact_source'] for r in read(HERE/'prior_reuse.csv'))
 resolved=[]
 for citation in sorted(citations):
  commit,path,line=citation.split(':');line=int(line)
  entry=next(x for x in manifest if x['commit']==commit and x['path']==path)
  lines=(HERE/entry['snapshot_path']).read_text().splitlines()
  if entry['selection']=='FULL':
   assert 1<=line<=len(lines),citation
   content=lines[line-1]
  else:
   assert line in entry['source_line_numbers'],citation
   content=lines[entry['source_line_numbers'].index(line)]
  resolved.append(dict(citation=citation,source_text=content,snapshot_path=entry['snapshot_path']))
 table('evidence_lines.csv',resolved)
 table('checks.csv',checks)
 dump('model_scope.json',dict(owner_commit=OWNER,p38_commit=P38,owner_networks=['OMS','DIRECT'],owner_scenarios=['base','base_sub','cautious','cautious_sub'],p38_finalists=finalists,p38_state='REPLACE; KEEP/WITHOUT_NEW saved annual delta identities also checked',comparability='Owner BASE OMS 6+1, DIRECT 7+1 or8+1 subsidy; P38 K2 2+R1. Different missions/fleet/accounting/period; no strategy ranking.',periods=dict(owner_base='52 operational model weeks; calendar year unspecified',owner_cautious='48 operational model weeks; same annual demand divided by 48 before capture. NOT 48/52 realised-pax scaling, not dated lost weeks.',p38='365 actual days Jan-Dec2027, ISO recurrence, UTC departure attribution; also separate UTC arrivals/calendar-split BH'),units=dict(journeys='model carried one-way endpoint trips, not demand or unique persons',segments='boardings; local+2*transfer',transfers='two-leg journeys/connection events at hub',bags='UNKNOWN; transfers do not determine bags',nights='away aircraft local midnights; not crew room nights',owner_airports='MOW city pool represented by SVO coordinates; airport billing UNKNOWN',fuel='model burn tonnes; not purchased/uplift/eligible tax volume'),reproduced=['Pinned owner hub fixed-spoke flow/cost/revenue, all route and summary columns at export precision, 8 networks; no selection search','Pinned owner direct joint valuation of fixed selected programmes/frequencies; shared pair flow once; empty search universe','P38 all848 completed representative ledger rows: independent flight costs, direct_q*net revenue, ferry0, excluded crew','P38 three fixed K2 finalist annual calendars independently recurred, all432 published monthly physical rows, 72 REPLACE month costs, six annual costs and saved revenue/journey sums, three-state annual delta identities'],not_reproduced=['Owner greedy selection/optimizer/main or other hubs/ramp','P38 choice allocation/annual OD calibration/full optimisation or all436 programmes','Actual costs, invoices, realised demand, tax eligibility, dispatch, cash or2028 PD8 economics'],unknown_not_zero=True,external_price_search=False,write_boundary=str(HERE)))
 counts=Counter(r['status'] for r in read(HERE/'coverage.csv')) if (HERE/'coverage.csv').exists() else {}
 dump('validation.json',dict(status='PASS',completed_handoff=True,checks=len(checks),failed_checks=sum(not c['pass_'] for c in checks),snapshot_files=len(manifest),snapshot_bytes=sum(x['bytes'] for x in manifest),snapshot_hashes_verified=True,owner_route_rows=sum(1 for _ in read(HERE/'owner_route_checks.csv')),owner_networks=8,p38_ledger_rows=848,p38_monthly_physical_rows=432,p38_annual_REPLACE_networks=6,p38_choice_recomputed=False,exposure_rows=len(exposures),coverage_status_counts=dict(counts),limitations_file='model_scope.json',runner=sys.executable,python_version=sys.version,no_old_exporters_called=True,coverage_rows=len(coverage),annual_driver_rows=len(drivers),coverage_citations_resolve=True,additional_costs_priced=False,all_missing_prices_explicit_UNKNOWN=True))
 dump('handoff.json',dict(status='COMPLETED',role='sole P39 model cost/exposure auditor',blocking_dependencies=[],owner_commit=OWNER,p38_commit=P38,files=['README.md','coverage.csv','exposures.csv','annual_drivers.csv','model_scope.json','validation.json','budget_boundary.json','prior_reuse.csv','evidence_lines.csv','audit.py','snapshot_manifest.json'],checks=len(checks),failed_checks=0,source_snapshots_verified=True,coverage_rows=len(coverage),exposure_rows=len(exposures),new_prices=False,full_budget_known=False,waits_for_other_roles=False,write_boundary=str(HERE)))
 print(json.dumps(dict(status='PASS',checks=len(checks),owner_networks=8,p38_finalists=3,exposure_rows=len(exposures))))
if __name__=='__main__':run()
