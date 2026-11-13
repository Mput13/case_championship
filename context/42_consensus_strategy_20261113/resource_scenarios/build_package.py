#!/usr/bin/env python3
"""Bounded, offline schedule diagnostic. All writes stay beside this file."""
import csv
import copy
import hashlib
import io
import json
import math
import re
import subprocess
import sys
import types
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[2]
BASE = 'context/35_full_programme_execution_20261112/'
P08 = BASE + 'P08/MOSCOW/research_v1/'
OMS = BASE + 'variants/OMS/research_v1/'
UTC = timezone.utc
PINS = {
    'research_root': '6a6326c2dcfe32e47ec25621bda0d15fcfe48ae1',
    'P03': '79dc698b99dfe866886d32376ed388e85bdd039c',
    'P06': '982f13d9b6c378ed9581125ecc5c40f17dade6a3',
    'author': 'f20000e72d5ca934f45f3aaaca4c320750ebccff',
}
TZ = {'ZIA': 3, 'DME': 3, 'AER': 3, 'VOG': 3, 'GSV': 4,
      'MRV': 3, 'OMS': 6, 'IKT': 8, 'GOJ': 3, 'KUF': 4}
SOURCES = []


def dump(name, data):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def csvout(name, rows):
    assert rows, name
    with (OUT / name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def source(owner, path, purpose, save=None):
    sha = PINS[owner]
    raw = subprocess.check_output(['git', 'show', sha + ':' + path], cwd=REPO)
    SOURCES.append(dict(commit=sha, source_path=path, sha256=hashlib.sha256(raw).hexdigest(),
                        bytes=len(raw), use=purpose, local_copy=save))
    if save:
        p = OUT / save
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
    return raw.decode()


def readcsv(s):
    return list(csv.DictReader(io.StringIO(s)))


def iso(t):
    return t.astimezone(UTC).isoformat(timespec='minutes').replace('+00:00', 'Z')


def local(t, airport):
    return t.astimezone(timezone(timedelta(hours=TZ[airport]))).isoformat(timespec='minutes')


coords_text = source('research_root', P08 + 'inputs/AUTHOR_catchments.csv',
                     'Только координаты физических аэропортов; население и OD не используются.')
COORD = {r['iata']: (float(r['latitude_deg']), float(r['longitude_deg'])) for r in readcsv(coords_text)}
author = source('author', 'outputs/redwings_panel.html',
                'Только координаты IKT; отдельная авторская модель, деньги/спрос не переносим.')
match = re.search(r'\{"city": "Иркутск", "iata": "IKT"', author)
ikt = json.JSONDecoder().raw_decode(author[match.start():])[0]
COORD['IKT'] = (ikt['lat'], ikt['lon'])
dump('inputs/coordinates.json', {a: dict(latitude=COORD[a][0], longitude=COORD[a][1],
                                       utc_offset_hours=TZ[a], source='author' if a == 'IKT' else 'research_root/P08')
                                for a in TZ})
recipes = json.loads(source('research_root', P08 + 'recipes.json', 'Происхождение двух географий.'))
dump('inputs/selected_recipes.json', [r for r in recipes if r['recipe_id'] in ['MOW-R01', 'MOW-R03']])
source('research_root', P08 + 'assumptions.json', 'P08 45min turn, block formula, no delivery claim.', 'inputs/P08_assumptions.json')
source('research_root', P08 + 'airport_status.csv', 'ZIA diagnostic branch; DME sensitivity; actual base UNKNOWN.', 'inputs/P08_airport_status.csv')
source('research_root', P08 + 'build_package.py', 'Exact implementation of P08 block analogue and timezone conventions.')
source('research_root', P08 + 'input_manifest.json', 'Underlying P08 pins and source provenance.', 'inputs/P08_input_manifest.json')
source('research_root', OMS + 'resource_diagnostic.json', 'Prior OMS example is SVX/OMS/KJA; not blocks for these new routes.', 'inputs/OMS_resource_diagnostic.json')
source('research_root', OMS + 'local_operating_constraints.csv', 'OMS operational unknowns.', 'inputs/OMS_local_operating_constraints.csv')
source('P03', BASE + 'P03/aircraft_type_parameters.csv', 'RRJ95B/LR distinct from SJ100_PD8.', 'inputs/P03_aircraft_type_parameters.csv')
source('P03', BASE + 'P03/sp_adapter/crew_advisory.json', 'Aircraft elapsed is not crew legality.', 'inputs/P03_crew_advisory.json')
for name in ['common', 'operations']:
    source('P06', BASE + 'P06/engine/' + name + '.py', 'Unmodified P06 check_operations.', 'inputs/P06_' + name + '.py')
pkg = types.ModuleType('p06_resource_diagnostic')
pkg.__path__ = []
sys.modules[pkg.__name__] = pkg
for name in ['common', 'operations']:
    module = types.ModuleType(pkg.__name__ + '.' + name)
    module.__package__ = pkg.__name__
    sys.modules[module.__name__] = module
    exec(compile((OUT / ('inputs/P06_' + name + '.py')).read_text(), name + '.py', 'exec'), module.__dict__)
CHECK_OPS = sys.modules[pkg.__name__ + '.operations'].check_operations


def distance(a, b):
    lat, lon = map(math.radians, COORD[a])
    lat2, lon2 = map(math.radians, COORD[b])
    h = math.sin((lat2-lat)/2)**2 + math.cos(lat)*math.cos(lat2)*math.sin((lon2-lon)/2)**2
    return 12742 * math.asin(min(1, math.sqrt(h)))


def block(a, b, stress=1.0, route_factor=1.2):
    nominal = 5 * math.ceil((30 + 60 * route_factor * distance(a, b) / 750) / 5)
    return 5 * math.ceil(nominal * stress / 5)


SCENARIOS = [
    dict(id='UNDER4', branch='under', ready=4, oms_working=0, oms_pairs=0, keep=1, phase='2027H2_or_later'),
    dict(id='PILOT5', branch='plan_pilot', ready=5, oms_working=1, oms_pairs=2, keep=0, phase='2027H2_or_later'),
    dict(id='PLAN6', branch='plan_expansion', ready=6, oms_working=2, oms_pairs=4, keep=0, phase='2028_or_later'),
    dict(id='EXTRA7', branch='extra_same_frequency', ready=7, oms_working=3, oms_pairs=6, keep=0, phase='2028_or_later'),
    dict(id='EXTRA8', branch='extra_frequency', ready=8, oms_working=4, oms_pairs=6, keep=0, phase='2028_or_later'),
]


def start_week(s, season):
    # Calendar samples only. They do not assign a delivery/readiness date.
    return date.fromisoformat('2028-02-07' if season == 'winter' else
                              '2027-08-02' if s['id'] in ['UNDER4', 'PILOT5'] else '2028-08-07')


def missions(s, moscow):
    out = []
    # Both orientations on the same date, using the two Moscow tails.
    for triangle, x, y, days in [('TRI_AER_VOG', 'AER', 'VOG', [0, 3]),
                                ('TRI_GSV_MRV', 'GSV', 'MRV', [1, 4])]:
        for tid, route, orient in [('M1', [moscow, x, y, moscow], 'forward'),
                                   ('M2', [moscow, y, x, moscow], 'reverse')]:
            for day in days:
                out.append(dict(day=day, tail=tid, base=moscow, route=route, mission=triangle, orientation=orient))
    if s['id'] == 'EXTRA8':
        om = [('O1', moscow, [0, 1, 3, 4, 6]), ('O2', 'IKT', [0, 1, 3, 4, 5]),
              ('O3', 'GOJ', [0, 3, 6]), ('O3', 'VOG', [1, 4, 5]),
              ('O4', 'KUF', [0, 3, 6]), ('O4', 'GSV', [1, 4, 5])]
    else:
        om = [('O1', moscow, [0, 3, 6]), ('O1', 'IKT', [1, 4, 5]),
              ('O2', 'GOJ', [0, 3, 6]), ('O2', 'VOG', [1, 4, 5]),
              ('O3', 'KUF', [0, 3, 6]), ('O3', 'GSV', [1, 4, 5])][:s['oms_pairs']]
    for tail, dest, days in om:
        for day in days:
            out.append(dict(day=day, tail=tail, base='OMS', route=['OMS', dest, 'OMS'],
                            mission='OMS_' + dest, orientation='out_and_back'))
    return sorted(out, key=lambda m: (m['day'], m['base'], m['tail']))


def schedule(s, season, airport, stress, weeks=1):
    start = start_week(s, season)
    flights, rotations = [], []
    prefix = f"{s['id']}_{season}_{airport}_x{stress:.1f}"
    for wk in range(weeks):
        for m in missions(s, airport):
            day = start + timedelta(days=7*wk+m['day'])
            dep = datetime.combine(day, datetime.min.time(), timezone(timedelta(hours=TZ[m['base']]))) + timedelta(hours=8)
            dep = dep.astimezone(UTC)
            first = dep
            rid = f"{prefix}_{day}_{m['tail']}"
            summed = 0
            for leg, (a, b) in enumerate(zip(m['route'], m['route'][1:]), 1):
                mins = block(a, b, stress)
                arr = dep + timedelta(minutes=mins)
                flights.append(dict(scenario_id=s['id'], season=season, reference_week=str(start),
                                    airport_branch=airport, block_stress=stress, template_flight_id=rid+f'_L{leg}',
                                    rotation_id=rid, aircraft_id=m['tail'], base_airport=m['base'],
                                    aircraft_variant='SJ100_PD8', block_basis='SSJ_geometry_analogue_NOT_PD8_performance',
                                    mission=m['mission'], orientation=m['orientation'], leg_order=leg,
                                    origin_airport=a, destination_airport=b, departure_utc=iso(dep), arrival_utc=iso(arr),
                                    departure_local=local(dep, a), arrival_local=local(arr, b),
                                    departure_weekday=dep.astimezone(timezone(timedelta(hours=TZ[a]))).isoweekday(),
                                    distance_km=round(distance(a,b), 3), block_minutes=mins,
                                    nominal_block_minutes=block(a,b), ground_before_minutes=45 if leg > 1 else '',
                                    status='SCENARIO_NOT_PUBLISHED_NOT_INVENTORY', seats='', saleable_seats=''))
                summed += mins
                dep = arr + timedelta(minutes=45)
            rotations.append(dict(scenario_id=s['id'], season=season, reference_week=str(start),
                                  airport_branch=airport, block_stress=stress, rotation_id=rid,
                                  date=str(day), weekday=day.isoweekday(), aircraft_id=m['tail'], base_airport=m['base'],
                                  route='-'.join(m['route']), sectors=len(m['route'])-1,
                                  departure_utc=iso(first), arrival_utc=iso(arr),
                                  departure_local=local(first,m['base']), arrival_local=local(arr,m['base']),
                                  block_minutes=summed, elapsed_minutes=int((arr-first).total_seconds()/60),
                                  report_minutes_proxy=60, release_minutes_proxy=30,
                                  duty_minutes_proxy=int((arr-first).total_seconds()/60)+90,
                                  duty_over_12h_proxy=int((arr-first).total_seconds()/60)+90 > 720,
                                  return_to_base_same_local_day=local(first,m['base'])[:10] == local(arr,m['base'])[:10]))
    return flights, rotations


def as_bundle(s, season, airport, flights, block_limit=10, variant='SJ100_PD8'):
    start = start_week(s, season)
    end = start + timedelta(days=7)
    lo, hi = str(start)+'T00:00Z', str(end)+'T00:00Z'
    tails = []
    roles = [('M1',airport,False),('M2',airport,False),('MR',airport,True)]
    if s['oms_working']:
        roles += [(f'O{n}', 'OMS', False) for n in range(1,s['oms_working']+1)] + [('OR','OMS',True)]
    for tid, base, reserve in roles:
        tails.append(dict(aircraft_id=tid, variant=variant, transfer_date=None, service_entry_date=None,
                          available_from=lo, available_to=hi, initial_location=base, turn_minutes=45,
                          reserve_intervals=[[lo,hi]] if reserve else [], maintenance_intervals=None,
                          crew_windows=None, max_daily_block_hours=block_limit, assumption_id='RES-A01'))
    fs = []
    for f in flights:
        fs.append(dict(flight_instance_id=f['template_flight_id'], schedule_id='diagnostic', operator='SCENARIO_RW',
                       flight_number=f['template_flight_id'], origin_airport=f['origin_airport'],
                       destination_airport=f['destination_airport'], departure_utc=f['departure_utc'], arrival_utc=f['arrival_utc'],
                       aircraft_variant=variant, seats=None, technical_blocked_seats=None, saleable_seats=None,
                       physical_adjacent_leg=True, scheduled_status='proposed', source_status='constructed_not_observed',
                       source_period=str(start), assumption_id='RES-A03', distance_km=f['distance_km']))
    return dict(context=dict(period_start=str(start)[:7],period_end=str(end)[:7]), resource_operators=['SCENARIO_RW'],
                flights=fs, fleet_calendar=tails,
                assignments=[dict(flight_instance_id=f['template_flight_id'], aircraft_id=f['aircraft_id'],
                                  crew_id=None, action='diagnostic_only', assumption_id='RES-A01') for f in flights])


ALL_FLIGHTS, ALL_ROTATIONS, OPS, RESOURCE, RETURNS, TAILS = [], [], [], [], [], []
checks = []
def check(name, passed, detail):
    checks.append(dict(check=name, status='PASS' if passed else 'FAIL', detail=detail))


for s in SCENARIOS:
    for season in ['summer','winter']:
        for airport in ['ZIA','DME']:
            for stress in [1.0,1.1,1.2]:
                flights, rotations = schedule(s, season, airport, stress)
                ALL_FLIGHTS.extend(flights)
                ALL_ROTATIONS.extend(rotations)
                bundle = as_bundle(s, season, airport, flights)
                result = CHECK_OPS(bundle)
                result8 = CHECK_OPS(as_bundle(s, season, airport, flights, block_limit=8))
                ssj_result = CHECK_OPS(as_bundle(s, season, airport, flights, variant='RRJ95LR_100'))
                run = f"{s['id']}/{season}/{airport}/x{stress}"
                unknown_counts = Counter(x.rsplit(': ',1)[-1] for x in result['unknowns'])
                OPS.append(dict(run=run, status=result['status'], errors=result['errors'],
                                unknown_count=len(result['unknowns']), unknown_categories=dict(unknown_counts),
                                sample_unknowns=result['unknowns'][:5], dispatch_ready=False,
                                stricter_8h_status=result8['status'], stricter_8h_errors=result8['errors'],
                                RRJ95LR_analogue_status=ssj_result['status'], RRJ95LR_analogue_errors=ssj_result['errors'],
                                RRJ95LR_donor_and_prior_sales='UNKNOWN; no existing tail released',
                                duty_over_12h_proxy=[r['rotation_id'] for r in rotations if r['duty_over_12h_proxy']]))
                check(run+'/P06_no_hard_errors_at10h', not result['errors'], result['status'])
                check(run+'/same_day_base_returns', all(r['return_to_base_same_local_day'] for r in rotations), len(rotations))
                check(run+'/resource_partition', 3+s['oms_working']+bool(s['oms_working'])+s['keep']==s['ready'], s)
                check(run+'/reserve_not_flown', set(result['unused_aircraft']) == ({'MR','OR'} if s['oms_working'] else {'MR'}), result['unused_aircraft'])
                ordered = Counter((f['origin_airport'],f['destination_airport']) for f in flights)
                check(run+'/unique_pairs', len({tuple(sorted(p)) for p in ordered}) == 6+s['oms_pairs'], len(ordered)//2)
                expected = {}
                for m in missions(s,airport):
                    for a,b in zip(m['route'],m['route'][1:]): expected[(a,b)] = expected.get((a,b),0)+1
                check(run+'/frequency', ordered == expected, dict(sorted((a+'-'+b,n) for (a,b),n in ordered.items())))
                bytail = defaultdict(list)
                for r in rotations: bytail[r['aircraft_id']].append(r)
                for tid, rs in bytail.items():
                    TAILS.append(dict(run=run, aircraft_id=tid, base_airport=rs[0]['base_airport'],
                                      role='working', active_days=len(rs), allocation_tail_days=7,
                                      block_hours=round(sum(r['block_minutes'] for r in rs)/60,3),
                                      maximum_daily_block_hours=round(max(r['block_minutes'] for r in rs)/60,3),
                                      maximum_duty_hours_proxy=round(max(r['duty_minutes_proxy'] for r in rs)/60,3),
                                      nonflying_days=7-len(rs), maintenance_accepted=False))
                for tid,base in [('MR',airport)] + ([('OR','OMS')] if s['oms_working'] else []):
                    TAILS.append(dict(run=run, aircraft_id=tid, base_airport=base, role='dedicated_standby',
                                      active_days=0, allocation_tail_days=7, block_hours=0,maximum_daily_block_hours=0,
                                      maximum_duty_hours_proxy=0,nonflying_days=7,maintenance_accepted=False))
                if s['keep']:
                    TAILS.append(dict(run=run,aircraft_id='K1',base_airport='UNKNOWN_KEEP_LOCATION',role='KEEP_unassigned_to_project',
                                      active_days='',allocation_tail_days=7,block_hours='',maximum_daily_block_hours='',
                                      maximum_duty_hours_proxy='',nonflying_days='',maintenance_accepted=False))
                # Independent turn/location and cyclic boundary check, including last -> next week's first.
                for tid in bytail:
                    fs=sorted([f for f in flights if f['aircraft_id']==tid],key=lambda f:f['departure_utc'])
                    valid=True
                    for a,b in zip(fs,fs[1:]+[fs[0]]):
                        end=datetime.fromisoformat(a['arrival_utc'].replace('Z','+00:00'))
                        begin=datetime.fromisoformat(b['departure_utc'].replace('Z','+00:00'))
                        if b is fs[0]: begin += timedelta(days=7)
                        valid &= a['destination_airport']==b['origin_airport'] and (begin-end).total_seconds()>=45*60
                    check(run+'/'+tid+'/cyclic_location_turn',valid,'includes week seam')
                if stress == 1.0:
                    # Repetition for return-date search only, NOT another delivered season or annualisation.
                    repeat, _ = schedule(s,season,airport,stress,weeks=3)
                    for f in flights:
                        arrive=datetime.fromisoformat(f['arrival_local']).date()
                        ret=[r for r in repeat if r['origin_airport']==f['destination_airport'] and r['destination_airport']==f['origin_airport']]
                        found={n:[r for r in ret if (datetime.fromisoformat(r['departure_local']).date()-arrive).days==n] for n in [3,4,7]}
                        RETURNS.append(dict(scenario_id=s['id'],season=season,airport_branch=airport,
                                            outbound_id=f['template_flight_id'],origin=f['origin_airport'],destination=f['destination_airport'],
                                            outbound_departure_local=f['departure_local'],outbound_arrival_local=f['arrival_local'],
                                            return_3_nights_id=found[3][0]['template_flight_id'] if found[3] else '',
                                            return_3_nights_departure_local=found[3][0]['departure_local'] if found[3] else '',
                                            return_4_nights_id=found[4][0]['template_flight_id'] if found[4] else '',
                                            return_4_nights_departure_local=found[4][0]['departure_local'] if found[4] else '',
                                            return_7_nights_id=found[7][0]['template_flight_id'] if found[7] else '',
                                            return_7_nights_departure_local=found[7][0]['departure_local'] if found[7] else '',
                                            has_3_or_4_nights=bool(found[3] or found[4]),has_7_nights=bool(found[7]),
                                            scope='calendar_direct_legs_only; seats_sales_utility_UNKNOWN'))
            # Baseline resource totals per season, airport; block factor sensitivity is separate.
            fs,rs=schedule(s,season,airport,1.0)
            for base in [airport,'OMS']:
                own=[r for r in rs if r['base_airport']==base]
                if not own: continue
                RESOURCE.append(dict(scenario_id=s['id'],branch=s['branch'],phase=s['phase'],ready_threshold=s['ready'],
                                     season=season,reference_week=str(start_week(s,season)),airport_branch=airport,base_airport=base,
                                     working_aircraft=2 if base==airport else s['oms_working'],standby_aircraft=1,
                                     keep_aircraft_outside_project=s['keep'] if base==airport else 0,
                                     total_project_pairs=6+s['oms_pairs'],base_pairs=6 if base==airport else s['oms_pairs'],
                                     weekly_rotations=len(own),weekly_sectors=sum(r['sectors'] for r in own),
                                     weekly_block_hours=round(sum(r['block_minutes'] for r in own)/60,3),
                                     weekly_duty_hours_proxy=round(sum(r['duty_minutes_proxy'] for r in own)/60,3),
                                     max_daily_block_hours=round(max(r['block_minutes'] for r in own)/60,3),
                                     max_duty_hours_proxy=round(max(r['duty_minutes_proxy'] for r in own)/60,3),
                                     peak_concurrent_duties=max(Counter(r['date'] for r in own).values()),
                                     standby_crew_at_this_base='REQUIRED_UNKNOWN',MRO_at_this_base='REQUIRED_UNKNOWN',
                                     actual_ready_date='',actual_fleet_status='UNKNOWN',status='CONDITIONAL'))

csvout('dated_templates.csv',ALL_FLIGHTS)
csvout('rotations.csv',ALL_ROTATIONS)
csvout('base_resource_requirements.csv',RESOURCE)
csvout('tail_week_utilisation.csv',TAILS)
csvout('return_windows.csv',RETURNS)
dump('operations_results.json',OPS)

# Exact scenario rows are independent from seasonal samples and physical Moscow branch.
rows=[]
for s in SCENARIOS:
    rows.append(dict(scenario_id=s['id'],branch=s['branch'],ready_threshold=s['ready'],phase=s['phase'],
                     aircraft_variant='SJ100_PD8 hypothetical_ready',moscow_airport_status='UNCONFIRMED;ZIA diagnostic;DME separate sensitivity',
                     moscow_working=2,moscow_standby=1,oms_working=s['oms_working'],oms_standby=int(bool(s['oms_working'])),
                     keep_outside_project=s['keep'],unique_project_pairs=6+s['oms_pairs'],moscow_pair_RT_per_week=2,
                     oms_pair_RT_per_week='5 ZIA/IKT;3 GOJ/VOG/KUF/GSV' if s['id']=='EXTRA8' else 3 if s['oms_pairs'] else 0,
                     weekly_project_sectors=24+(44 if s['id']=='EXTRA8' else s['oms_pairs']*6),
                     resource_status='CONDITIONAL',delivery_schedule='UNKNOWN',actual_ready_date='',
                     action='OMS postponed; one residual tail KEEP with task/location UNKNOWN' if s['id']=='UNDER4' else
                            'Launch only after both-base readiness and commercial gates; no official RW deliveries implied'))
for sid in ['DELAYED','NO_NEW']:
    rows.append(dict(scenario_id=sid,branch=sid.lower(),ready_threshold='',phase='2027H2_2028',
                     aircraft_variant='SJ100_PD8 delayed;existing_RRJ95_requires_donor',moscow_airport_status='UNCONFIRMED',
                     moscow_working='',moscow_standby='',oms_working='',oms_standby='',keep_outside_project='',
                     unique_project_pairs='',moscow_pair_RT_per_week='',oms_pair_RT_per_week='',weekly_project_sectors='',
                     resource_status='CONDITIONAL',delivery_schedule='UNKNOWN' if sid=='DELAYED' else '0 new within defined no_new branch',
                     actual_ready_date='',action='Before readiness keep existing tasks; activate highest affordable threshold only after readiness' if sid=='DELAYED' else
                     'No new-resource programme without an explicit existing-tail donor; KEEP remains; donor result and cost UNKNOWN'))
csvout('candidate_resource_requirements.csv',rows)

# Adversarial probes exercise the unchanged imported checker, not new acceptance rules.
probe_s=SCENARIOS[1]
probe_fs,_=schedule(probe_s,'summer','ZIA',1.0)
original=as_bundle(probe_s,'summer','ZIA',probe_fs)
probe_results=[]
for name in ['wrong_initial_location','turn_shortfall','standby_assigned_without_release','variant_mismatch']:
    b=copy.deepcopy(original)
    if name=='wrong_initial_location': b['fleet_calendar'][0]['initial_location']='OMS'
    elif name=='turn_shortfall':
        # Longer first arrival with the following departure kept fixed.
        b['flights'][0]['arrival_utc']=iso(datetime.fromisoformat(b['flights'][0]['arrival_utc'].replace('Z','+00:00'))+timedelta(minutes=5))
    elif name=='standby_assigned_without_release':
        for a in b['assignments']:
            if a['aircraft_id']=='M1': a['aircraft_id']='MR'
    else: b['flights'][0]['aircraft_variant']='RRJ95B'
    try:
        result=CHECK_OPS(b)
        rejected=bool(result['errors'])
        evidence=result['errors'][:3]
    except ValueError as e:
        rejected=True
        evidence=[str(e)]
    probe_results.append(dict(probe=name,rejected=rejected,evidence=evidence))
    check('adversarial/'+name,rejected,evidence)
dump('adversarial_probes.json',probe_results)

# At-base substitution only; separate standby tails are consumed at their own bases.
reserve_probes=[]
for replace in [{'M1':'MR'},{'O1':'OR'},{'M1':'MR','O1':'OR'}]:
    b=copy.deepcopy(original)
    for a in b['assignments']: a['aircraft_id']=replace.get(a['aircraft_id'],a['aircraft_id'])
    for t in b['fleet_calendar']:
        if t['aircraft_id'] in replace.values(): t['reserve_intervals']=[]
    result=CHECK_OPS(b)
    reserve_probes.append(dict(replace=replace,errors=result['errors'],status=result['status'],
                               remaining_dedicated_standby=2-len(replace),
                               assumption='At base before first departure; typed standby available and explicitly released. Crew/MRO still UNKNOWN.',
                               away_from_base_recovery='NOT_RUN; ferry, response time, crew and cost UNKNOWN'))
    check('reserve_substitution/'+str(replace),not result['errors'],result['status'])
dump('reserve_substitution_probes.json',reserve_probes)

# Explicit frequency and tail-day bounds, independent from mission-loop expectations.
for s in SCENARIOS:
    fs,rs=schedule(s,'summer','ZIA',1.0)
    count=Counter(tuple(sorted((f['origin_airport'],f['destination_airport']))) for f in fs)
    for pair,n in count.items():
        target=10 if s['id']=='EXTRA8' and 'OMS' in pair and any(a in pair for a in ['ZIA','IKT']) else 6 if 'OMS' in pair else 4
        check(s['id']+'/independent_pair_frequency/'+str(pair),n==target,dict(legs=n,expected=target))
    oms_rotations=[r for r in rs if r['base_airport']=='OMS']
    check(s['id']+'/OMS_working_bound',math.ceil(len(oms_rotations)/7)==s['oms_working'],
          'Within selected closed-RT/10h-day pattern: even two shortest OMS RTs exceed10h; not universal fleet minimum.')

check('UTC_local_identity',all(datetime.fromisoformat(f['departure_local'])==datetime.fromisoformat(f['departure_utc'].replace('Z','+00:00'))
                             and datetime.fromisoformat(f['arrival_local'])==datetime.fromisoformat(f['arrival_utc'].replace('Z','+00:00'))
                             for f in ALL_FLIGHTS),'all departures and arrivals retain explicit offsets')
check('725min_duty_counterexample',all(r['duty_minutes_proxy']==725 for r in ALL_ROTATIONS
                                     if r['route'] in ['OMS-ZIA-OMS','OMS-DME-OMS'] and r['block_stress']==1.2),
      'ceil5 stressed blocks +45min turn +60min report +30min release')

check('all_direct_departures_have_short_return',all(r['has_3_or_4_nights'] for r in RETURNS),
      dict(departures=len(RETURNS),missing=[r['outbound_id'] for r in RETURNS if not r['has_3_or_4_nights']]))
check('all_direct_departures_have_7_night_return',all(r['has_7_nights'] for r in RETURNS),len(RETURNS))
check('no_new_SJ_template_before_H2_2027',min(f['departure_utc'] for f in ALL_FLIGHTS)>='2027-07-01',min(f['departure_utc'] for f in ALL_FLIGHTS))
check('physical_airport_only',all('MOW' not in [f['origin_airport'],f['destination_airport']] for f in ALL_FLIGHTS),'ZIA and DME are separate alternatives')

# Stress comparison holds initial departures but propagates later departures to preserve 45min turns.
stress_fixed_failures=[]
for s in SCENARIOS:
    for season in ['summer','winter']:
        for airport in ['ZIA','DME']:
            nominal,_=schedule(s,season,airport,1.0)
            for factor in [1.1,1.2]:
                conflicts=[]
                byrot=defaultdict(list)
                for f in nominal: byrot[f['rotation_id']].append(f)
                for rot,fs in byrot.items():
                    for a,b in zip(fs,fs[1:]):
                        stressed_arr=datetime.fromisoformat(a['departure_utc'].replace('Z','+00:00'))+timedelta(minutes=block(a['origin_airport'],a['destination_airport'],factor))
                        gap=(datetime.fromisoformat(b['departure_utc'].replace('Z','+00:00'))-stressed_arr).total_seconds()/60
                        if gap<45: conflicts.append(dict(flight=a['template_flight_id'],remaining_turn_minutes=gap))
                stress_fixed_failures.append(dict(scenario_id=s['id'],season=season,airport=airport,factor=factor,
                                                   failed_turns=len(conflicts),examples=conflicts[:2],
                                                   verdict='FAIL_FIXED_CLOCK_45MIN_TURN; RETIMED_STRESS_IS_SEPARATE'))

findings = [
    dict(id='F01',status='FAIL_ALTERNATIVE_CALENDAR',finding='One orientation Mon/Thu and the reverse Tue/Fri has no exact 7-night return on any of the six Moscow pairs.',
         counterexample='ZIA>AER Mon 2027-08-02; AER>ZIA Tue/Fri only; no return Mon 2027-08-09.',
         remedy='Two Moscow working tails: both orientations Mon/Thu AER-VOG; Tue/Fri GSV-MRV.'),
    dict(id='F02',status='FAIL_FIXED_CLOCK_STRESS',finding='45min exact baseline turns cannot absorb any positive block overrun with all later departures fixed.',
         remedy='Stress templates explicitly retime following legs; new slots and sales times remain unaccepted.'),
    dict(id='F03',status='CONDITIONAL',finding='8h/day filter fails some OMS round trips; 10h/day has no hard errors in this bounded sample. Neither is crew approval.'),
    dict(id='F04',status='CONDITIONAL',finding='At x1.2 OMS-ZIA and OMS-DME round-trip duty proxy is 725min (12h05); above chosen 12h screening marker. No legal FTL verdict.',
         remedy='Actual report/release, RPP, rests and roster required; retime or explicit crew relief only after costing.'),
    dict(id='F05',status='CONDITIONAL',finding='7 ready supports the constructed 12-pair 3RT/week programme with 3 OMS working +1 OMS standby. 8 is not a derived minimum for 12 pairs.',
         remedy='8-ready example has 4 OMS working +1 standby and increases OMS-Moscow and OMS-IKT to5RT/week. Demand and financing UNKNOWN.'),
    dict(id='F06',status='CONDITIONAL',finding='All enumerated direct departures have at least one 3-or4-night return and a7-night return under repeated pattern. Identical usefulness, full-day stay, prices and seats are not proved.'),
]
dump('verification.json',dict(status='CONDITIONAL',bounded_package_complete=True,dispatch_ready=False,
                             hard_check_failures=[c for c in checks if c['status']=='FAIL'],checks=checks,
                             findings=findings,fixed_clock_stress_failures=stress_fixed_failures,
                             counts=dict(flights=len(ALL_FLIGHTS),rotations=len(ALL_ROTATIONS),operations_runs=len(OPS),
                                         return_tests=len(RETURNS),checks=len(checks)),
                             boundaries=dict(annual_2027_2028_calendar='NOT_RUN',FTL='NOT_RUN',slots='UNKNOWN',
                                             demand_and_fares='NOT_RUN',joint_PnL='NOT_RUN',crew_MRO_actual='UNKNOWN',
                                             free_existing_fleet='UNKNOWN',delivery_dates='UNKNOWN',live_acceptance=False)))
dump('inputpins.json',dict(pins=PINS,sources=SOURCES,
                          unused_supplied_dependencies=dict(P04='620a0ac; no new costs or legal interpretation',P05='a63a047; no demand/choice calculation'),
                          git_actions='read-only git show; no fetch/status/index/branch/commit/push',network_calls=0,
                          source_copy_note='Exact engine copies inside this package only; core and frozen inputs unchanged.'))

pair_rows=[]
for airport in ['ZIA','DME']:
    fs,_=schedule(SCENARIOS[3],'summer',airport,1.0)
    for a,b in sorted({tuple(sorted((f['origin_airport'],f['destination_airport']))) for f in fs}):
        pair_rows.append(dict(airport_branch=airport,pair=a+'-'+b,distance_km=round(distance(a,b),3),
                              route_factor_1_1_block_minutes=block(a,b,route_factor=1.1),
                              route_factor_1_2_reference_block_minutes=block(a,b),
                              block_stress_1_1_minutes=block(a,b,1.1),block_stress_1_2_minutes=block(a,b,1.2),
                              basis='ceil5(30+60*k*gc/750); stress applied afterwards; symmetric diagnostic analogue'))
csvout('pair_block_assumptions.csv',pair_rows)

# Human readout/assumptions and handoff are authored alongside this reproducible numeric package.
print(json.dumps(dict(rows=len(ALL_FLIGHTS),runs=len(OPS),checks=len(checks),
                      hard_failures=[c for c in checks if c['status']=='FAIL'],
                      baseline_ZIA=[r for r in RESOURCE if r['season']=='summer' and r['airport_branch']=='ZIA']),ensure_ascii=False))
