"""EV-MR02 exact-v2 review. No owner calculation/verifier functions used in independent math.

Run from repository root with BLAS thread limits. Subject snapshot is recreated from
git blobs inside this review's ignored runtime. Owner Demand/load supplies pinned OD
and geography only; all calendar, financial, schedule and cash equations are here.
"""
import calendar
import copy
import csv
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from collections import Counter, defaultdict

SHA = 'aa7779192d809558e38b1eb9bdfa25913a3afdc8'
PREFIX = 'context/28_evening_run_20261110/methods/'
HERE = Path(__file__).resolve().parent
SUBJECT = HERE / '.runtime/subject'
for k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[k] = '1'
FILES = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', SHA, PREFIX], text=True).splitlines()
for name in FILES:
    path = SUBJECT / name[len(PREFIX):]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(subprocess.check_output(['git', 'show', SHA + ':' + name]))

def read(name):
    return list(csv.DictReader((SUBJECT / name).open()))

def js(name):
    return json.loads((SUBJECT / name).read_text())

checks = Counter()
worst = defaultdict(float)
def near(actual, expected, group, tol=.002):
    delta = abs(float(actual) - float(expected))
    worst[group] = max(worst[group], delta)
    assert delta <= tol, (group, actual, expected, delta)
    checks[group] += 1

receipts = []
for file in ['source_manifest.json'] + [f'inputs/{i}/receipt.json' for i in ('evidence_06cb', 'network_941d', 'digital_45c3')]:
    for r in js(file)['files']:
        raw = (SUBJECT / r['path']).read_bytes()
        original = subprocess.check_output(['git', 'show', r['source_commit'] + ':' + r['source_path']])
        assert raw == original and len(raw) == r['bytes'] and hashlib.sha256(raw).hexdigest() == r['sha256']
        checks['source_receipts'] += 1
        receipts.append(dict(receipt=file, path=r['path'], source_commit=r['source_commit'], source_path=r['source_path'], sha256=r['sha256']))
for r in js('output_manifest.json')['files']:
    raw = (SUBJECT / r['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == r['sha256'] and len(raw) == r['bytes']
    checks['output_hashes'] += 1

# Independent receipt of the source 2026 cap/fare table, not primary/legal review.
rule = (SUBJECT / 'inputs/evidence_06cb/raw/web/favt_regional_rules/text.txt').read_text()
assert 'произведение количества выполненных рейсов' in rule
assert 'на все места в салоне экономического класса' in rule
assert '84 - 103 ** 104 280 113 643 132 367 151 091 169 816 188 540 207 265 225 989 244 713 263 438 282 162 310 249 403 871' in rule
assert '2 017 2 258 2 741 3 225 3 708 4 191 4 674 5 157 5 640 6 123 6 606 7 089 7 572 8 055 8 538 9 021 9 504 9 987 10 470 10 953' in rule

sys.path.insert(0, str(SUBJECT))
from model_kernel import load  # pinned input loader ONLY, not owner finance/calendar helpers
D, assumptions = load()
net = js('runs/selection_v1/networks.json')
plans = js('runs/resource_v1/plans.json')

def fare(a, km):
    return a['fare_fixed_rub'] + a['fare_per_km_rub'] * km

def shadow(a, x, y):
    return 0. if 'MOW' in (x, y) else a['subsidy_rub_per_pax'] * a['use_subsidy']

def share(a, l, freq):
    if l['km'] < a['transfer_min_km']:
        return 0.
    if l['competitive']:
        comp = l['seg'] / (a['seats'] * a['competitor_lf'])
        return min(a['capture_competitive'], freq / (freq + comp)) if comp > 0 else 0.
    return a['capture_open'] * (1 - math.exp(-freq / a['capture_freq_scale']))

def leg_expense(a, l, q, freq):
    factor = a['route_factor_south'] if l['south'] else a['route_factor']
    hours = a['block_fixed_h'] + l['km'] * factor / a['block_speed_kmh']
    fixed = (a['fuel_t_per_hour'] * hours + a['fuel_t_per_cycle']) * a['fuel_rub_per_t']
    fixed += hours * (a['mro_rub_per_hour'] + a['crew_rub_per_hour'] + a['navigation_rub_per_hour'])
    fixed += a['ground_rub_per_flight'] + a['deicing_rub_per_flight']
    return 2 * freq * hours, 2 * freq * fixed + 2 * q * a['pax_cost_rub']

def fixed_offer(key, year):
    n = net[key]
    a, m, source = n['assumptions'], n['metrics'], n['result']
    days = (dt.date(year+1, 1, 1) - dt.date(year, 1, 1)).days
    weeks = days / 7
    sc = a['demand_scen']
    hub = m['kind'] == 'HUB'
    if hub:
        legs = {x: dict(l, dem=D.get(l['a'], l['b'], sc)/(2*weeks), seg=D.seg(l['a'], l['b'], sc)/(2*weeks)) for x, l in source[0].items()}
        local = {x:l['dem']*share(a, l, l['freq']) for x,l in legs.items()}
        transfer = []
        # Existing eligible-pair universe is frozen: revalue frequencies, never reselect.
        for x,y,km,_ in source[1]:
            q = D.get(x,y,sc)/(2*weeks)*a['capture_transfer']*(1-math.exp(-min(legs[x]['freq'],legs[y]['freq'])/a['capture_freq_scale']))
            transfer.append((x,y,km,q))
        load = dict(local)
        for x,y,km,q in transfer:
            load[x] += q; load[y] += q
        scale = {x:min(1, l['freq']*a['seats']*a['lf_max']/load[x]) if load[x] else 1 for x,l in legs.items()}
        local = {x:q*scale[x] for x,q in local.items()}
        transfer = [(x,y,km,q*min(scale[x],scale[y])) for x,y,km,q in transfer]
        carried = dict(local)
        for x,y,km,q in transfer:
            carried[x] += q; carried[y] += q
        ls = []
        for x,l in legs.items():
            ls.append(dict(l, q=carried[x], local=local[x], mg=min(local[x],l['rw_now'])))
    else:
        ls = [dict(l, dem=D.get(l['a'],l['b'],sc)/(2*weeks), seg=D.seg(l['a'],l['b'],sc)/(2*weeks)) for t in source for l in t[8]]
        groups = defaultdict(list)
        for l in ls: groups[tuple(sorted((l['a'],l['b'])))].append(l)
        for members in groups.values():
            first = members[0]; freq = sum(l['freq'] for l in members)
            q = min(first['dem']*share(a,first,freq),freq*a['seats']*a['lf_max'])
            mg = min(q,first['rw_now'])
            for l in members: l.update(q=q*l['freq']/freq, mg=mg*l['freq']/freq)
        transfer = []
    ticket = cost = support = foregone = migrated = segments = hours = flights = 0.
    for l in ls:
        h,c = leg_expense(a,l,l['q'],l['freq']); hours += h; cost += c
        ticket += 2*(l['local'] if hub else l['q'])*fare(a,l['km'])
        foregone += 2*l['mg']*fare(a,l['km']); migrated += 2*l['mg']
        support += 2*((l['local'] if hub else l['q'])-l['mg'])*shadow(a,l['a'],l['b'])
        segments += 2*l['q']; flights += 2*l['freq']
    tr_inc = 0.
    for x,y,km,q in transfer:
        unit = fare(a,km)*a['transfer_fare_factor']
        sub = shadow(a,m['network'],x)+shadow(a,m['network'],y)
        ticket += 2*q*unit; support += 2*q*sub
        tr_inc += 2*q*(unit+sub-2*a['pax_cost_rub'])*weeks
    tr_j = 2*sum(t[3] for t in transfer)*weeks
    c = (ticket-foregone+support-cost)*weeks
    return dict(id=key, scenario=m['scenario'], network=m['network'], year=year,
        constructed_working=plans[key]['working_tails'], model_city_pairs=m['model_city_pairs'],
        model_8_12_pair_gate=m['model_8_12_pair_gate'],
        ticket_before_migration_rub_year=ticket*weeks,foregone_ticket_rub_year=foregone*weeks,
        ticket_after_migration_rub_year=(ticket-foregone)*weeks,support_rub_year=support*weeks,
        variable_cost_rub_year=cost*weeks,contribution_rub_year=c,journeys_year=segments*weeks-tr_j,
        segments_year=segments*weeks,transfer_journeys_year=tr_j,migrated_segments_year=migrated*weeks,
        net_added_segments_listed_keep_only=(segments-migrated)*weeks,block_hours_week=hours,flights_week=flights,
        local_only_no_refill_contribution_rub_year=c-tr_inc,all_transfer_increment_rub_year=tr_inc)

fixed = {}
for row in read('runs/annual_v1/fixed_offer_year_values.csv'):
    key,year = row['id'],int(row['year'])
    own = fixed_offer(key,year);fixed[(key,year)] = own
    for k,v in own.items():
        if isinstance(v,(float,int)) and not isinstance(v,bool):near(row[k],v,'fixed_offer_values')
    assert row['connection_acceptance'] == 'UNKNOWN_UNTIL_DATED_MCT_AND_INVENTORY_CHECK'

signatures=set();expected_fixed_ids=set()
for key in plans:
    n=net[key];m=n['metrics'];source=n['result']
    legs=list(source[0].values()) if m['kind']=='HUB' else [l for t in source for l in t[8]]
    signature=(m['scenario'],m['network'],tuple((l['a'],l['b'],l['freq']) for l in legs))
    if signature in signatures:continue
    signatures.add(signature);expected_fixed_ids.add(key)
assert set(fixed)=={(key,year) for key in expected_fixed_ids for year in (2027,2028)},'missing or extra deduplicated candidate valuation'
checks['complete_unique_offer_universe']=len(expected_fixed_ids)

# Resource states independently expanded from stated batches, not owner cohort CSV.
batch_spec = [(dt.date(2027,7,1),3),(dt.date(2027,10,1),1),(dt.date(2028,4,1),2),(dt.date(2028,7,1),2)]
def shift(date, months):
    index = date.year*12 + date.month-1 + months
    y,mo = divmod(index,12)
    return dt.date(y,mo+1,min(date.day,calendar.monthrange(y,mo+1)[1]))

def state(branch, availability, date):
    delay = {'PHASED':0,'PARTIAL_FIRST4':0,'DELAY3':3,'DELAY6':6,'DELAY12':12,'NO_NEW':0}[branch]
    received = entered = ground = 0
    for batch,(raw,count) in enumerate(batch_spec):
        if branch == 'NO_NEW' or (branch == 'PARTIAL_FIRST4' and batch>=2):continue
        receipt = shift(raw,delay);ready = receipt+dt.timedelta(days=30)
        for tail in range(count):
            received += int(date>=receipt);entered += int(date>=ready)
            start = shift(ready,12)+dt.timedelta(days=14*tail)
            ground += int(availability=='14D_GROUNDING_STRESS' and start<=date<start+dt.timedelta(days=14))
    serviceable = entered-ground;reserve = int(serviceable>0)
    return dict(received_new=received,in_entry_new=received-entered,entered_new=entered,
                planned_grounded_new=ground,reserve_new=reserve,working_new=serviceable-reserve)

daily = read('runs/annual_v1/aircraft_calendar_daily.csv')
for row in daily:
    expected = state(row['branch'],row['availability'],dt.date.fromisoformat(row['date']))
    for k,v in expected.items():near(row[k],v,'daily_resource',tol=0)
    assert row['company_total_entered']=='LEGACY_ENTERED(t) + entered_new'

cohorts = read('runs/annual_v1/delivery_cohorts.csv')
assert Counter(r['branch'] for r in cohorts)==Counter(PHASED=8,PARTIAL_FIRST4=4,DELAY3=8,DELAY6=8,DELAY12=8)
for r in cohorts:
    receipt=dt.date.fromisoformat(r['received']);ready=dt.date.fromisoformat(r['ready'])
    start=dt.date.fromisoformat(r['maintenance_start']);end=dt.date.fromisoformat(r['maintenance_end'])
    assert receipt>=dt.date(2027,7,1) and ready-receipt==dt.timedelta(days=30)
    assert start>=shift(ready,12) and end-start==dt.timedelta(days=14)
    checks['delivery_cohorts']+=1

def closed(date):
    return date.isocalendar().year==date.year and date.isocalendar().week in (2,15,28,41)

flow_fields = ['ticket_before_migration_rub_year','foregone_ticket_rub_year','ticket_after_migration_rub_year',
    'support_rub_year','variable_cost_rub_year','contribution_rub_year','journeys_year','segments_year',
    'transfer_journeys_year','migrated_segments_year','net_added_segments_listed_keep_only',
    'local_only_no_refill_contribution_rub_year','all_transfer_increment_rub_year']

def annual_replay(row):
    year=int(row['year']);days=(dt.date(year+1,1,1)-dt.date(year,1,1)).days
    offers=[v for (key,y),v in fixed.items() if y==year and v['scenario']==row['scenario'] and v['network']==row['network']]
    total=defaultdict(float);monthly=defaultdict(lambda:defaultdict(float));selections=[]
    for offset in range(days):
        day=dt.date(year,1,1)+dt.timedelta(days=offset)
        rr=state(row['branch'],row['availability'],day)
        eligible=[v for v in offers if v['constructed_working']<=rr['working_new'] and v['model_city_pairs']<=12]
        finals=[v for v in eligible if v['model_8_12_pair_gate']]
        chosen=max(finals or eligible,key=lambda v:(v['contribution_rub_year'],-v['constructed_working'])) if eligible and not(row['scenario'].startswith('cautious') and closed(day)) else None
        selections.append((str(day),chosen['id'] if chosen else 'KEEP'))
        for s in (total,monthly[str(day)[:7]]):
            s['calendar_days']+=1
            for src,dst in [('received_new','new_received_aircraft_days'),('entered_new','new_entered_aircraft_days'),('planned_grounded_new','new_grounded_aircraft_days'),('reserve_new','new_reserved_aircraft_days')]:s[dst]+=rr[src]
            if chosen:
                for f in flow_fields:s[f.replace('_year','')]+=chosen[f]/days
                s['active_days']+=1;s['working_aircraft_days']+=chosen['constructed_working'];s['allocated_reserve_days']+=1
                s['final_gate_days']+=chosen['model_8_12_pair_gate'];s['pilot_days']+=not chosen['model_8_12_pair_gate']
                s['block_hours_equivalent']+=chosen['block_hours_week']/7;s['flights_equivalent']+=chosen['flights_week']/7
                s['unallocated_working_aircraft_days']+=rr['working_new']-chosen['constructed_working']
                s['economic_KEEP_days_before_excluded_costs']+=chosen['contribution_rub_year']<=0
            else:s['keep_days']+=1;s['unallocated_working_aircraft_days']+=rr['working_new']
    zero_fields=[f.replace('_year','') for f in flow_fields]+[
        'active_days','keep_days','final_gate_days','pilot_days','working_aircraft_days','allocated_reserve_days',
        'block_hours_equivalent','flights_equivalent','unallocated_working_aircraft_days','economic_KEEP_days_before_excluded_costs']
    for s in [total,*monthly.values()]:
        for field in zero_fields:s[field]+=0
    return total,monthly,selections

def finish_check(row, own):
    c,sub,tr=own['contribution_rub'],own['support_rub'],own['all_transfer_increment_rub']
    near(row['excluded_cost_headroom_if_external_donor_delta_zero'],c,'signed_headroom')
    near(row['external_signed_donor_delta_required_if_K_zero'],max(0,-c),'signed_donor')
    if sub>0:near(row['support_fraction_for_variable_zero'],(sub-c)/sub,'support_fraction')
    else:assert row['support_fraction_for_variable_zero']==''
    if tr>0:near(row['transfer_realization_fraction_for_variable_zero'],-own['local_only_no_refill_contribution_rub']/tr,'transfer_boundary')
    else:assert row['transfer_realization_fraction_for_variable_zero']==''
    action='CONDITIONAL_LAUNCH_ONLY_IF_KminusD_LE_HEADROOM' if c>0 else 'KEEP_UNLESS_NAMED_POSITIVE_DONOR_OR_VALID_ADDITIONAL_SUPPORT'
    assert row['economic_action']==action
    for field in ('full_delta_pnl','full_company_pnl','peak_cash','actual_future_support_rub'):assert row[field]==''

annual = read('runs/annual_v1/annual_budget.csv')
month_index={(r['branch'],r['availability'],r['scenario'],r['network'],r['month']):r for r in read('runs/annual_v1/monthly_budget.csv')}
intervals=defaultdict(dict)
for r in read('runs/annual_v1/program_intervals.csv'):
    d=dt.date.fromisoformat(r['start'])
    while d<dt.date.fromisoformat(r['end_exclusive']):
        key=(r['branch'],r['availability'],r['scenario'],r['network'],r['year'])
        assert str(d) not in intervals[key]
        intervals[key][str(d)]=r['selected_id'];d+=dt.timedelta(days=1)
examples=[];replayed={}
for row in annual:
    total,months,selections=annual_replay(row)
    key=tuple(row[k] for k in ('branch','availability','scenario','network','year'))
    replayed[key]=total
    for k,v in total.items():near(row[k],v,'annual_replay')
    finish_check(row,total)
    for mon,vals in months.items():
        mr=month_index[key[:4]+(mon,)]
        for k,v in vals.items():near(mr[k],v,'monthly_replay')
        finish_check(mr,vals)
    assert intervals[key]==dict(selections),('selected programs',key)
    checks['selected_daily_programs']+=len(selections)
    if row['availability']=='14D_GROUNDING_STRESS' and row['scenario']=='base_sub' and row['network'] in ('OMS','KUF') and row['branch'] in ('PHASED','PARTIAL_FIRST4','DELAY6','NO_NEW'):
        examples.append(dict(zip(('branch','availability','scenario','network','year'),key))|dict(contribution_rub=total['contribution_rub'],active_days=total['active_days'],transfer_threshold=row['transfer_realization_fraction_for_variable_zero'],selected_steps=[r for i,r in enumerate(selections) if i==0 or r[1]!=selections[i-1][1]]))

def rotation_check(rows):
    groups=defaultdict(list)
    for r in rows:groups[(r['network_id'],r['tail'])].append(r)
    for group in groups.values():
        ordered=sorted(group,key=lambda r:r['departure_utc']);weekly=0.;byday=defaultdict(list)
        for i,r in enumerate(ordered):
            dep=dt.datetime.fromisoformat(r['departure_utc']);arr=dt.datetime.fromisoformat(r['arrival_utc'])
            assert dep.date()>=dt.date(2028,8,7) and dep.date()<=dt.date(2028,8,13)
            assert arr>dep and abs((arr-dep).total_seconds()/3600-float(r['block_hours']))<1e-7
            if i:
                prev=ordered[i-1];pa=dt.datetime.fromisoformat(prev['arrival_utc'])
                assert prev['destination']==r['origin'],'airport continuity'
                assert (dep-pa).total_seconds()>=45*60-1e-5,'turn/overlap'
            weekly+=float(r['block_hours']);byday[dep.date()].append(r)
        assert weekly<=70+1e-6,'weekly70'
        for dailyrows in byday.values():
            assert sum(float(r['block_hours']) for r in dailyrows)<=14+1e-6,'daily14'
            first=dt.datetime.fromisoformat(dailyrows[0]['departure_utc']);last=dt.datetime.fromisoformat(dailyrows[-1]['arrival_utc'])
            assert (last-first).total_seconds()/3600+.75<=16+1e-6,'elapsed16'
            assert dailyrows[0]['origin']==dailyrows[-1]['destination'],'closed rotation'
    return len(rows)

rotations=read('runs/resource_v1/dated_rotations.csv')
checks['rotation_legs']=rotation_check(rotations)
for key,plan in plans.items():
    assert plan['status']=='CONSTRUCTED_CONDITIONAL' and not plan['dispatch_acceptance']
    actual=Counter((r['origin'],r['destination']) for r in rotations if r['network_id']==key)
    n=net[key];r=n['result'];expected=Counter();blocks={};job_specs={}
    if n['metrics']['kind']=='HUB':
        for x,l in r[0].items():
            expected[(l['a'],l['b'])]+=int(l['freq']);expected[(l['b'],l['a'])]+=int(l['freq'])
            blocks[(l['a'],l['b'])]=blocks[(l['b'],l['a'])]=l['block_h']
            base=n['metrics']['network'];job_specs[base+'-'+x]=dict(base=base,airports=[base,x,base],blocks=[l['block_h']]*2,freq=int(l['freq']))
    else:
        for t in r:
            base,x,y=t[1:4];bs=[l['block_h'] for l in t[8]];freq=int(t[8][0]['freq'])
            for l in t[8]:
                expected[(l['a'],l['b'])]+=int(l['freq']);expected[(l['b'],l['a'])]+=int(l['freq'])
                blocks[(l['a'],l['b'])]=blocks[(l['b'],l['a'])]=l['block_h']
            for airports,bh in [([base,x,y,base],bs),([base,y,x,base],list(reversed(bs)))]:
                job_specs['-'.join(airports)]=dict(base=base,airports=airports,blocks=bh,freq=freq)
    assert actual==expected,(key,'frequency')
    assert len({r['tail'] for r in rotations if r['network_id']==key})<=plan['working_tails']
    got=Counter();lower=0
    for base,b in plan['bases'].items():
        total_for_base=sum(sum(j['blocks'])*j['freq'] for j in job_specs.values() if j['base']==base)
        lower+=math.ceil((total_for_base-1e-9)/70)
        assert len(b['slots'])==7
        for day in b['slots']:
            assert len(day)==b['working_tails']
            for slot in day:
                bh=elapsed=0.
                for job in slot['tasks']:
                    assert {k:job[k] for k in ('base','airports','blocks','freq')}==job_specs[job['id']]
                    got[job['id']]+=1;bh+=sum(job['blocks']);elapsed+=sum(job['blocks'])+.75*len(job['blocks'])
                near(slot['block'],bh,'slot_block');near(slot['elapsed'],elapsed,'slot_elapsed')
                assert bh<=14+1e-6 and elapsed<=16+1e-6
        for tail in range(b['working_tails']):assert sum(day[tail]['block'] for day in b['slots'])<=70+1e-6
    assert got==Counter({k:j['freq'] for k,j in job_specs.items()})
    assert lower==plan['lower_bound_sum_bases'] and lower<=plan['working_tails']
    for row in rotations:
        if row['network_id']!=key:continue
        near(row['block_hours'],blocks[(row['origin'],row['destination'])],'dated_leg_block')
        assert row['date']==dt.datetime.fromisoformat(row['departure_utc']).date().isoformat()
        assert (row['physical_airport_resolved']=='True')==('MOW' not in (row['origin'],row['destination']))
    checks['constructed_programs']+=1

# Flight and fare constraints are computed from the pinned tables independently.
fare_table=[2017,2258,2741,3225,3708,4191,4674,5157,5640,6123,6606,7089,7572,8055,8538,9021,9504,9987,10470,10953]
grant_bands=[(0,199,104280),(201,300,113643),(301,400,132367),(401,500,151091),(501,600,169816),(601,700,188540),(701,800,207265),(801,900,225989),(901,1000,244713),(1001,1100,263438),(1101,1200,282162),(1201,1400,310249),(1401,math.inf,403871)]
def limits(km):
    distance=math.ceil(km)
    g=next((cap for lo,hi,cap in grant_bands if lo<=distance<=hi),None)
    if distance==200:return g,None
    fareband=0 if distance<200 else min(19,(distance-201)//100+1)
    return g,fare_table[fareband]

def coupled(key,eta=1.):
    n=net[key];a,m,src=n['assumptions'],n['metrics'],n['result'];weeks=a['weeks_per_year']
    hub=m['kind']=='HUB';legs=list(src[0].values()) if hub else [l for t in src for l in t[8]]
    g=receipts=0.;caps={}
    assert 84<=a['seats']<=103
    for l in legs:
        nonmow='MOW' not in (l['a'],l['b']);gc,fc=limits(l['km'])
        if nonmow:
            assert gc is not None and fc is not None
            g+=2*l['freq']*weeks*gc;unit=min(fare(a,l['km']),eta*fc)
        else:unit=fare(a,l['km'])
        caps[tuple(sorted((l['a'],l['b'])))]=eta*fc if nonmow else unit
        q=l['local_carried'] if hub else l['carried_dir_week']
        receipts+=2*q*unit*weeks
    if hub:
        for x,y,km,q in src[1]:
            ceiling=caps[tuple(sorted((m['network'],x)))]+caps[tuple(sorted((m['network'],y)))]
            receipts+=2*q*min(fare(a,km)*a['transfer_fare_factor'],ceiling)*weeks
    receipts-=m['foregone_ticket_rub_year']
    return receipts,g,receipts+g-m['variable_cost_rub_year']

support_examples=[]
for row in read('runs/support_v1/coupled_boundaries.csv'):
    key=row['network_id'];r,g,c=coupled(key)
    for k,v in [('fare_constrained_net_receipts_upper_eta1',r),('all_nonMOW_flight_cap_coefficient1',g),('contribution_at_eta1_all_flight_caps',c),('required_fraction_of_all_caps_at_eta1',(net[key]['metrics']['variable_cost_rub_year']-r)/g)]:near(row[k],v,'coupled_summary')
    if row['minimum_eta_for_variable_zero_at_all_caps']:
        eta=float(row['minimum_eta_for_variable_zero_at_all_caps']);near(coupled(key,eta)[2],0,'eta_zero',.0001)
        assert coupled(key,eta-1e-6)[2]<0
    if row['network'] in ('OMS','KUF') and row['scenario']=='base_sub':support_examples.append(row)
listing=defaultdict(list)
for row in read('inputs/evidence_06cb/subsidy_route_matches.csv'):listing[tuple(sorted((row['origin'],row['destination'])))].append(row)
for row in read('runs/support_v1/route_constraints.csv'):
    nonmow='MOW' not in (row['origin'],row['destination']);gc,fc=limits(float(row['distance_model_km']))
    near(row['per_flight_table_cap_coefficient1'],gc if nonmow else 0,'route_cap')
    if nonmow:near(row['special_gross_economy_fare_base'],fc,'route_fare')
    else:assert row['special_gross_economy_fare_base']==''
    assert row['actual_grant']=='' and row['future_award']=='UNKNOWN'
    matches=listing[tuple(sorted((row['origin'],row['destination'])))]
    assert row['listed2026_carriers']==' | '.join(sorted({m['airline'] for m in matches}))
    assert (row['RW_in_2026_list']=='True')==any('Ред Вингс' in m['airline'] for m in matches)
for row in read('runs/support_v1/fare_constraint_counterexamples.csv'):
    key=row['network_id'];r,g,c=coupled(key);m=net[key]['metrics'];naive=m['ticket_after_migration_rub_year']+g-m['variable_cost_rub_year']
    near(row['overstatement_from_ignoring_fare_ceiling'],naive-c,'coupled_counterexample')

for row in read('runs/budget_v1/full_budget_conditions.csv'):
    key=tuple(row[k] for k in ('branch','availability','scenario','network','year'));own=replayed[key]
    c=own['contribution_rub'];nd=own['new_received_aircraft_days'];wd=own['working_aircraft_days']+own['allocated_reserve_days']
    for k,v in [('C_rub',c),('max_K_minus_external_signed_D',c),('received_aircraft_days',nd),('allocated_working_and_reserve_days',wd)]:near(row[k],v,'budget_conditions')
    for field,denom in [('finance_cost_per_received_day_upper_if_only_missing_cost',nd),('allocated_aircraft_day_cost_upper_if_only_missing_cost',wd)]:
        if denom:near(row[field],c/denom,'budget_coefficients')
        else:assert row[field]==''
    assert row['actual_full_pnl']=='' and row['actual_peak_cash']==''
for row in read('runs/budget_v1/OMS_KUF_rank_conditions.csv'):
    def val(network):return replayed[(row['branch'],row['availability'],row['scenario'],network,row['year'])]
    a,b=val('OMS'),val('KUF');diff=a['contribution_rub']-b['contribution_rub'];wd=a['working_aircraft_days']-b['working_aircraft_days']
    near(row['contribution_A_minus_B_rub'],diff,'rank_boundaries')
    near(row['received_new_aircraft_days_difference'],a['new_received_aircraft_days']-b['new_received_aircraft_days'],'same_resource')
    if wd:near(row['additional_allocated_cost_per_day_rank_boundary'],diff/wd,'rank_coefficients')
    else:assert row['additional_allocated_cost_per_day_rank_boundary']==''

cash_examples=[]
event_rows=read('runs/budget_v1/cash_events.csv')
for row in read('runs/budget_v1/cash_timing_cases.csv'):
    ev=[];timing=row['timing'];ticketfirst=timing.startswith('TICKET')
    for (branch,avail,scenario,fam,mon),mr in month_index.items():
        if (branch,avail,scenario,fam)!=(row['branch'],'14D_GROUNDING_STRESS','base_sub',row['network']):continue
        year,month=map(int,mon.split('-'));start=dt.date(year,month,1);end=dt.date(year,month,calendar.monthrange(year,month)[1])
        td,cd=(start,end) if ticketfirst else (end,start)
        ev += [(str(td),1,'new_ticket_net_equivalent',float(mr['ticket_before_migration_rub'])),(str(td),2,'old_receipt_foregone',-float(mr['foregone_ticket_rub'])),(str(cd),3 if ticketfirst else 0,'variable_cost_equivalent',-float(mr['variable_cost_rub']))]
        if timing!='COST_FIRST_NO_GRANTED_SUPPORT':ev += [(str(end+dt.timedelta(days=45 if ticketfirst else 90)),4,'historical_owner_support_shadow',float(mr['support_rub']))]
    ev.sort();balance=low=0.;stored=[r for r in event_rows if all(r[k]==row[k] for k in ('branch','network','timing'))]
    assert len(ev)==len(stored)
    for e,r in zip(ev,stored):
        date,order,kind,amount=e
        assert (r['date'],int(r['same_day_order']),r['kind'])==(date,order,kind)
        balance+=amount;low=min(low,balance)
        near(r['amount_net_settlement_equivalent'],amount,'cash_amounts');near(r['cumulative'],balance,'cash_order')
    near(row['peak_financing_equivalent'],-low,'cash_peak');near(row['ending_net_equivalent_after_all_proxy_events'],balance,'cash_end')
    assert row['actual_peak_cash']==''
    cash_examples.append(row)

# Adversarial checks mutate in-memory copies only, never owner/raw/frozen files.
probes=[]
def reject(name, fn):
    try:fn()
    except (AssertionError, ValueError) as e:probes.append(dict(id=name,status='REJECTED_AS_EXPECTED',reason=str(e)))
    else:raise AssertionError(('mutation escaped',name))

ready=dt.date(2027,7,31)
assert state('PHASED','14D_GROUNDING_STRESS',ready-dt.timedelta(days=1))['working_new']==0
assert state('PHASED','14D_GROUNDING_STRESS',ready)['working_new']==2
assert shift(dt.date(2028,2,29),12)==dt.date(2029,2,28)
for date in [dt.date(2027,12,31),dt.date(2028,1,1),dt.date(2028,2,29),dt.date(2028,4,30),dt.date(2028,7,31),dt.date(2028,8,13),dt.date(2028,9,11)]:
    probes.append(dict(id='calendar_boundary_'+str(date),state=state('PHASED','14D_GROUNDING_STRESS',date),status='CHECKED'))
rr=state('PHASED','14D_GROUNDING_STRESS',ready)
assert state('PHASED','14D_GROUNDING_STRESS',dt.date(2028,7,30))['planned_grounded_new']==0
assert state('PHASED','14D_GROUNDING_STRESS',dt.date(2028,7,31))['planned_grounded_new']==1
assert state('PHASED','14D_GROUNDING_STRESS',dt.date(2028,9,10))['planned_grounded_new']==1
assert state('PHASED','14D_GROUNDING_STRESS',dt.date(2028,9,11))['planned_grounded_new']==0
reject('grounding_end_inclusive_extra_day',lambda:near(state('PHASED','14D_GROUNDING_STRESS',dt.date(2028,9,11))['planned_grounded_new'],1,'mutation',tol=0))
reject('one_day_early_entry',lambda:near(state('PHASED','14D_GROUNDING_STRESS',ready-dt.timedelta(days=1))['entered_new'],3,'mutation',tol=0))
reject('reserve_double_subtracted',lambda:near(rr['entered_new'],rr['planned_grounded_new']+2*rr['reserve_new']+rr['working_new'],'mutation',tol=0))
entry_state=state('PHASED','14D_GROUNDING_STRESS',dt.date(2027,10,15))
reject('entry_double_subtracted',lambda:near(entry_state['working_new'],entry_state['received_new']-2*entry_state['in_entry_new']-entry_state['reserve_new'],'mutation',tol=0))
assert all(sum(closed(dt.date(y,1,1)+dt.timedelta(days=i)) for i in range(366 if calendar.isleap(y) else 365))==28 for y in (2027,2028))
key=next(k for k,y in fixed if y==2028 and net[k]['metrics']['scenario']=='base_sub' and net[k]['metrics']['network']=='OMS')
sample=fixed[(key,2028)]['variable_cost_rub_year']
reject('leap_year_using_365_denominator',lambda:near(sample/365,sample/366,'mutation'))
bad=copy.deepcopy(rotations[:2]);bad[1]['origin']='ZZZ';reject('airport_discontinuity',lambda:rotation_check(bad))
bad=copy.deepcopy(rotations[:2]);bad[1]['departure_utc']=(dt.datetime.fromisoformat(bad[0]['arrival_utc'])+dt.timedelta(minutes=44)).isoformat();bad[1]['arrival_utc']=(dt.datetime.fromisoformat(bad[1]['departure_utc'])+dt.timedelta(hours=float(bad[1]['block_hours']))).isoformat();reject('turn_44_minutes',lambda:rotation_check(bad))
bad=copy.deepcopy(rotations[:2]);bad[1]['departure_utc']=bad[0]['departure_utc'];bad[1]['arrival_utc']=bad[0]['arrival_utc'];bad[1]['block_hours']=bad[0]['block_hours'];reject('overlapping_tail_legs',lambda:rotation_check(bad))
def synthetic_cycle(block, gap=45, n=1):
    out=[]
    for d in range(n):
        dep=dt.datetime(2028,8,7+d,6,tzinfo=dt.timezone.utc)
        for a,b in [('OMS','KUF'),('KUF','OMS')]:
            arr=dep+dt.timedelta(hours=block)
            out.append(dict(network_id='synthetic',tail='T1',departure_utc=dep.isoformat(),arrival_utc=arr.isoformat(),origin=a,destination=b,block_hours=block))
            dep=arr+dt.timedelta(minutes=gap)
    return out
assert rotation_check(synthetic_cycle(5,n=7))==14
reject('weekly_70_exceeded',lambda:rotation_check(synthetic_cycle(5.01,n=7)))
reject('daily_14_exceeded',lambda:rotation_check(synthetic_cycle(7.01)))
reject('elapsed_16_exceeded',lambda:rotation_check(synthetic_cycle(6,gap=240)))
assert limits(199)==(104280,2017) and limits(200)==(None,None) and limits(201)==(113643,2258)
assert limits(300)==(113643,2258) and limits(301)==(132367,2741)
assert limits(1200)[0]==282162 and limits(1201)[0]==310249 and limits(1400)[0]==310249 and limits(1401)[0]==403871
probes.append(dict(id='distance_band_edges_and_200_unresolved',status='CHECKED',distances=[199,200,201,300,301,1200,1201,1400,1401,2000,2001]))
oms=next(r for r in support_examples if r['network']=='OMS');key=oms['network_id'];m=net[key]['metrics'];r,g,c=coupled(key)
reject('uncapped_owner_fare_with_flight_grant',lambda:near(c,m['ticket_after_migration_rub_year']+g-m['variable_cost_rub_year'],'mutation'))
reject('second_automatic_VAT_deduction',lambda:near(c,r/1.2+g-m['variable_cost_rub_year'],'mutation'))
reject('grant_pax_unit_instead_of_flights',lambda:near(g,m['segments_year']*1773,'mutation'))
# Two-leg trip consumes two seats, receives exactly one constrained through fare.
q,netfare,cap1,cap2,eta=10,9000,3000,4000,.8
one=q*min(netfare,eta*(cap1+cap2));assert one==56000 and 2*q==20
reject('one_through_fare_charged_twice',lambda:near(one,2*one,'mutation'))
assert coupled(key,.8)[0]<=coupled(key,1)[0]
assert shadow(net[key]['assumptions'],'MOW','OMS')==0
# Linear no-refill boundary is not a new optimisation or connection proof.
fixture=next(r for r in annual if r['branch']=='PHASED' and r['availability']=='14D_GROUNDING_STRESS' and r['scenario']=='base_sub' and r['network']=='OMS' and r['year']=='2028')
local,transfer=float(fixture['local_only_no_refill_contribution_rub']),float(fixture['all_transfer_increment_rub'])
fraction=-local/transfer;near(local+fraction*transfer,0,'linear_fraction')
assert local+(fraction-1e-6)*transfer<0
reject('closed_weeks_recapture_into_open_days',lambda:near(337/365,1,'mutation',tol=0))
# Signed donor ledger and additional costs: migration is already included in C.
new_receipts,foregone,varcost=100.,15.,70.
C=new_receipts-foregone-varcost
old_extra_receipts,avoided_costs,replacement,K=-8.,12.,3.,9.
donor=old_extra_receipts+avoided_costs-replacement
assert C+donor-K==7 and C+donor-(K+7)==0 and C+donor-(K+8)==-1
reject('migration_or_donor_double_deduction',lambda:near(C+donor-K,C+donor-foregone-K,'mutation',tol=0))
assert C+donor-(K+25)+25==C+donor-K # identical finance in both actions cancels
reject('cash_receipt_replaces_foregone_with_zero',lambda:near(new_receipts-foregone-varcost,new_receipts-varcost,'mutation',tol=0))
summary=dict(subject_sha=SHA,independent_checks=dict(checks),maximum_abs_error={k:v for k,v in worst.items() if k!='mutation'},
    mutation_max_expected_deviation=worst['mutation'],
    source_receipt_checks=len(receipts),fixed_offer_rows=len(fixed),daily_resource_rows=len(daily),annual_rows=len(annual),
    monthly_rows=len(month_index),annual_sign_counts=dict(Counter('positive' if float(r['contribution_rub'])>0 else 'negative' if float(r['contribution_rub'])<0 else 'zero' for r in annual)),
    selected_examples=examples,support_examples=support_examples,cash_examples=cash_examples,
    adversarial_probes=probes,owner_helpers_used=['model_kernel.load for pinned Demand/assumptions only'],
    owner_helpers_not_used=['annual_calendar','resource_construction','dated_offer.revalue','dated_offer.construct','verify_calendar','support_budget','budget_conditions','model_kernel.metrics','network_model financial functions'],
    acceptance='ARITHMETIC_CONDITIONAL_DIAGNOSTIC_ONLY; no market, fleet/crew/airport/MCT, award, full PnL or actual gross cash acceptance')
(HERE/'independent_results.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ('selected_examples','support_examples','cash_examples','adversarial_probes')},indent=2))
print('adversarial probes:',len(probes),'rejected mutations:',sum(p['status']=='REJECTED_AS_EXPECTED' for p in probes))
