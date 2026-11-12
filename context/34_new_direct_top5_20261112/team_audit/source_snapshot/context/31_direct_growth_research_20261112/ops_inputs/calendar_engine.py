"""Dated physical rotation generator; diagnostic consistency is not ops approval.
CLI: python3 calendar_engine.py request.json --output result.json
No inference of demand, free aircraft, reverse flight times or physical MOW airport.
"""
import argparse, json
from datetime import date, datetime, timedelta, timezone
from collections import defaultdict
from zoneinfo import ZoneInfo
UTC = timezone.utc

def dt(s):
    x=datetime.fromisoformat(s.replace('Z','+00:00'))
    if x.tzinfo is None: raise ValueError('explicit timezone required')
    return x.astimezone(UTC)

def generate(request):
    """patterns: path (closed, or explicit paid positioning), weekdays ISO1..7,
    frequency_per_week (closed rotations, not per-leg multiplier), operating_weeks
    (ISO Monday dates), start/end, departure_local, workingtailids.
    blocks: directed origin/destination, nominal_minutes/high_minutes, evidence.
    tails: id,type,initial_location,available_from/to,reserve,delivery_date.
    timezones: physical airport->IANA. turn_minutes defaults P03 diagnostic45.
    Returns UTC/local flights, rotations, daily/monthly BH/cycles, resource gates.
    Missing times reject pattern; no geometric fallback. UNKNOWN never PASS.
    """
    errors=[]; flights=[]; rotations=[]; gates=[]
    tails={x['id']:x for x in request['tails']}
    if len(tails)!=len(request['tails']): raise ValueError('duplicate tail id')
    blocks={(x['origin'],x['destination']):x for x in request['blocks']}
    tz=request['timezones']; turn=request.get('turn_minutes',45)
    if turn<0: raise ValueError('negative turn')
    reserve=[x['id'] for x in tails.values() if x.get('reserve')]
    for t in tails.values():
        gates.append(dict(tail=t['id'],delivery=t.get('delivery_date'),entry=t.get('available_from'),
          location=t.get('initial_location'),positioning='UNKNOWN unless explicit paid flight',
          crew='UNKNOWN',maintenance='UNKNOWN',donor=t.get('donor','UNKNOWN'),contract='UNKNOWN'))
    for p in request['patterns']:
        path=p['path']; days=p['weekdays']; freq=p.get('frequency_per_week',len(days))
        if len(days)!=len(set(days)) or any(d not in range(1,8) for d in days) or freq!=len(days):
            raise ValueError('frequency must equal unique explicit weekdays; split multiple daily rotations into patterns')
        if path[0]!=path[-1]:
            errors.append(p['id']+':UNCLOSED_NO_PAID_POSITIONING'); continue
        if any(a=='MOW' for a in path): errors.append(p['id']+':UNRESOLVED_MOW');continue
        ids=p['workingtailids']
        if not ids: errors.append(p['id']+':NO_WORKING_TAIL');continue
        if any(x not in tails or tails[x].get('reserve') for x in ids):
            errors.append(p['id']+':RESERVE_OR_UNKNOWN_TAIL_USED');continue
        durations=[]
        for a,b in zip(path,path[1:]):
            v=blocks.get((a,b),{}).get(request.get('block_case','nominal')+'_minutes')
            if v is None: errors.append(p['id']+':MISSING_DIRECTED_BLOCK:'+a+'-'+b);break
            if v<=0: raise ValueError('block must be positive')
            durations.append(v)
        if len(durations)!=len(path)-1:continue
        start=date.fromisoformat(p['start']); end=date.fromisoformat(p['end']); n=0
        for offset in range((end-start).days+1):
            day=start+timedelta(days=offset); monday=day-timedelta(days=day.weekday())
            if day.isoweekday() not in days or ('operating_weeks' in p and monday.isoformat() not in p['operating_weeks']):continue
            tail=ids[n%len(ids)];n+=1; rid=p['id']+'/'+day.isoformat()
            when=datetime.fromisoformat(day.isoformat()+'T'+p['departure_local']).replace(tzinfo=ZoneInfo(tz[path[0]])).astimezone(UTC)
            first=when
            for i,(a,b,mins) in enumerate(zip(path,path[1:],durations)):
                arr=when+timedelta(minutes=mins); block=blocks[(a,b)]
                flights.append(dict(flight_id=rid+'/'+str(i+1),rotation_id=rid,tail=tail,origin=a,destination=b,
                  departure_utc=when.isoformat(),arrival_utc=arr.isoformat(),departure_local=when.astimezone(ZoneInfo(tz[a])).isoformat(),
                  arrival_local=arr.astimezone(ZoneInfo(tz[b])).isoformat(),block_minutes=mins,
                  kind='positioning' if i in p.get('positioning_leg_indices',[]) else 'service',
                  cost_status='UNKNOWN',evidence=block.get('evidence','SCENARIO'),ops='requires_ops_check'))
                when=arr+timedelta(minutes=turn)
            rotations.append(dict(rotation_id=rid,tail=tail,physical_legs=len(durations),block_minutes=sum(durations),
              elapsed_minutes=(arr-first).total_seconds()/60,closed=path[0]==path[-1],status='CONDITIONAL',crew='UNKNOWN',maintenance='UNKNOWN'))
    seen=set()
    for f in flights:
        key=(f['origin'],f['destination'],f['departure_utc'])
        if key in seen: errors.append(f['flight_id']+':DUPLICATE_PHYSICAL_FLIGHT')
        seen.add(key)
    daily=defaultdict(lambda:dict(block_minutes=0,cycles=0));monthly=defaultdict(lambda:dict(block_minutes=0,cycles=0))
    for tid,t in tails.items():
        seq=sorted([f for f in flights if f['tail']==tid],key=lambda f:f['departure_utc']); pos=t.get('initial_location');ready=None
        for f in seq:
            dep,arr=dt(f['departure_utc']),dt(f['arrival_utc'])
            if pos not in [None,'UNKNOWN'] and pos!=f['origin']:errors.append(f['flight_id']+':POSITION_MISMATCH_REQUIRES_PAID_FERRY')
            if ready and dep<ready:errors.append(f['flight_id']+':OVERLAP_OR_TURN')
            if (t.get('available_from') and dep<dt(t['available_from'])) or (t.get('available_to') and arr>dt(t['available_to'])):errors.append(f['flight_id']+':OUTSIDE_ENTRY_AVAILABILITY')
            if t.get('type','').startswith('SJ') and dep<dt('2027-07-01T00:00:00Z'):errors.append(f['flight_id']+':SJ_BEFORE_H22027')
            for w in t.get('maintenance_windows',[]):
                if dep<dt(w['end']) and arr>dt(w['start']):errors.append(f['flight_id']+':MAINTENANCE_CONFLICT')
            pos=f['destination'];ready=arr+timedelta(minutes=turn)
            daily[(tid,dep.date().isoformat())]['cycles']+=1;monthly[(tid,dep.strftime('%Y-%m'))]['cycles']+=1
            cursor=dep
            while cursor<arr:
                edge=min(arr,datetime.combine(cursor.date()+timedelta(days=1),datetime.min.time(),UTC))
                mins=(edge-cursor).total_seconds()/60
                daily[(tid,cursor.date().isoformat())]['block_minutes']+=mins
                monthly[(tid,cursor.strftime('%Y-%m'))]['block_minutes']+=mins;cursor=edge
    dr=[dict(tail=t,date=d,block_hours=v['block_minutes']/60,cycles=v['cycles']) for (t,d),v in sorted(daily.items())]
    for r in dr:
        if r['block_hours']>request.get('diagnostic_bh_day',8):errors.append(r['tail']+'/'+r['date']+':SCENARIO_8BH_SCREEN_EXCEEDED_NOT_CREW_LAW')
    if flights and not reserve: errors.append('MISSING_PROTECTED_RESERVE')
    return dict(status='INFEASIBLE' if errors else 'CONDITIONAL_PHYSICAL_CONSISTENCY',errors=errors,flights=flights,rotations=rotations,
      daily=dr,monthly=[dict(tail=t,month=m,block_hours=v['block_minutes']/60,cycles=v['cycles']) for (t,m),v in sorted(monthly.items())],
      reserve=reserve,deliverygates=gates,crew='UNKNOWN',maintenance='UNKNOWN',ops_approval='UNKNOWN',
      time_accounting='UTC day/month BH split at midnight; cycles on departure UTC date; elapsed includes intermediate turns once')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('request');ap.add_argument('--output',required=True);args=ap.parse_args()
    result=generate(json.load(open(args.request)));open(args.output,'w').write(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
