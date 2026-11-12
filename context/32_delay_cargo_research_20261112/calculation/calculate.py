#!/usr/bin/env python3
"""Deterministic conditional RW delay/cargo study. Writes ONLY this directory.

No network, installation, dispatch approval, observed OD/rates or free fleet.
The completed context31 P05/P06 joint allocator and P04 costs are reused unchanged.
"""
import sys
sys.dont_write_bytecode = True
import csv
import hashlib
import importlib.util
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
ROOT = STUDY.parents[1]
C31 = ROOT / 'context/31_direct_growth_research_20261112'
UTC = timezone.utc
ZONES = {'SVX': 'Asia/Yekaterinburg', 'OMS': 'Asia/Omsk',
         'KUF': 'Europe/Samara', 'GOJ': 'Europe/Moscow'}
ROUTES = {'SVX-OMS': ('OMS', 100, 105), 'SVX-KUF': ('KUF', 105, 100),
          'SVX-GOJ': ('GOJ', 130, 130)}
LAYOUTS = ('EQUAL_GAP_G390', 'EQUAL_BUFFER_B30', 'END_OF_DAY_NEXT0900')
SHOCKS = (0, 30, 60, 120)
RATES = (25, 50, 100, 200, 400)  # diagnostic RUB / paid kg, NOT quotes
ALPHAS = (1.0, 0.5, 0.25, 0.0)
VERSION = 'DC-1.0-20261112'


def read(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(name, data):
    assert Path(name).name == name
    (HERE/name).write_text(json.dumps(data, ensure_ascii=False, indent=2,
                                    sort_keys=True, allow_nan=False)+'\n')


def table(name, rows):
    rows = list(rows)
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with (HERE/name).open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        for r in rows:
            w.writerow({k: 'NULL' if v is None else round(v, 8) if isinstance(v, float) else v
                        for k, v in r.items()})


def minutes(x):
    return x.total_seconds()/60


def dt(x):
    d = datetime.fromisoformat(x.replace('Z', '+00:00'))
    if d.tzinfo is None:
        raise ValueError('Timezone is required')
    return d.astimezone(UTC)


def local(day, clock, airport):
    return datetime.fromisoformat(day+'T'+clock).replace(tzinfo=ZoneInfo(ZONES[airport])).astimezone(UTC)


def iso(d):
    return d.isoformat()


def clock(d, airport):
    return d.astimezone(ZoneInfo(ZONES[airport])).isoformat()


def load_economics():
    spec = importlib.util.spec_from_file_location('completed_route_economics', C31/'route_economics/calculate.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def flight(fid, origin, destination, departure, block, kind, source):
    assert origin != destination and block > 0
    return dict(fid=fid, origin=origin, destination=destination, dep=departure,
                arr=departure+timedelta(minutes=block), block=block, kind=kind, source=source)


def chain(route, layout):
    """Controlled physical tasks: new RT then four retained real-OD sectors.

    All clocks are analyst scenarios. Directed OMS/KUF blocks are published
    RRJ-95B analogues; GOJ130/130 is solely a hypothetical sensitivity point.
    The same retained tasks, including exact UTC times, appear in P and KEEP.
    """
    away, out, back = ROUTES[route]
    dep = local('2027-02-02', '18:00', 'SVX')
    basis = 'EXPLICIT_GOJ_130_EACH_DIRECTION_NOT_EXACT_BLOCK' if away == 'GOJ' else 'PUBLISHED_DIRECTIONAL_RRJ95B_ANALOGUE_NOT_2027_SCHEDULE'
    new = [flight('NEW-OUT', 'SVX', away, dep, out, 'new', basis)]
    new.append(flight('NEW-BACK', away, 'SVX', new[-1]['arr']+timedelta(minutes=60), back, 'new', basis))
    first = (local('2027-02-03', '00:30', 'SVX') if layout == 'EQUAL_GAP_G390'
             else new[-1]['arr']+timedelta(minutes=90) if layout == 'EQUAL_BUFFER_B30'
             else local('2027-02-03', '09:00', 'SVX'))
    following = [flight('FOLLOW-KUF-OUT', 'SVX', 'KUF', first, 105, 'retained', 'WZ-1033;svx_dep:375-379;published analogue')]
    following.append(flight('FOLLOW-KUF-BACK', 'KUF', 'SVX', following[-1]['arr']+timedelta(minutes=60), 100, 'retained', 'WZ-1034;svx_arr:391-395;100 minute RRJ95B analogue'))
    following.append(flight('FOLLOW-OMS-OUT', 'SVX', 'OMS', following[-1]['arr']+timedelta(minutes=75), 100, 'retained', 'WZ-5071;svx_dep:317;published RRJ95B analogue'))
    following.append(flight('FOLLOW-OMS-BACK', 'OMS', 'SVX', following[-1]['arr']+timedelta(minutes=60), 105, 'retained', 'WZ-5072;svx_arr:342;published RRJ95B analogue'))
    return {'P': new+following, 'KEEP': following}


def replay(flights, turn, shock=0, other_ready=None, initial_ready=None):
    """One isolated departure hold at NEW-OUT; no weather or probability model.

    max(plan, preceding actual arrival + minimum turn, known other-ready gate,
        imposed first departure hold). Arrival = actual departure + fixed block.
    No midnight reset. UNKNOWN crew/MRO gates are not evaluated as permission.
    """
    ready = initial_ready or local('2027-02-02', '18:00', 'SVX')
    position = 'SVX'
    result = []
    previous_arrival = None
    previous_plan_arrival = None
    for f in flights:
        assert f['origin'] == position, 'Physical positioning must be explicit'
        gate = (other_ready or {}).get(f['fid'], f['dep'])
        imposed = f['dep']+timedelta(minutes=shock if f['fid'] == 'NEW-OUT' else 0)
        actual_dep = max(f['dep'], ready, gate, imposed)
        actual_arr = actual_dep+timedelta(minutes=f['block'])
        incoming = 0 if previous_arrival is None else minutes(previous_arrival-previous_plan_arrival)
        buffer = None if previous_plan_arrival is None else minutes(f['dep']-previous_plan_arrival)-turn
        delay = minutes(actual_dep-f['dep'])
        result.append(dict(flight=f, actual_dep=actual_dep, actual_arr=actual_arr,
                           aircraft_ready=ready, known_other_ready=gate, imposed=imposed,
                           dep_delay=delay, arr_delay=delay, incoming_delay=incoming,
                           buffer=buffer, absorbed=max(0, incoming-delay) if f['fid'] != 'NEW-OUT' else 0))
        position, ready = f['destination'], actual_arr+timedelta(minutes=turn)
        previous_arrival, previous_plan_arrival = actual_arr, f['arr']
    return result


def source_admission():
    rows = []
    def add(id_, path, locator, status, used, rationale, **extra):
        rows.append(dict(admission_id=id_, source_path=path, locator=locator,
                         admission=status, admitted_use=used, limitation_or_correction=rationale, **extra))
    for i, r in enumerate(read(STUDY/'schedule_data/paired_control_calendars.csv'), 2):
        elapsed = minutes(dt(r['arr_utc']+'+00:00')-dt(r['dep_utc']+'+00:00'))
        zero = r['origin'] == r['destination'] or float(r['block_nominal_min']) == 0
        error = elapsed-float(r['block_nominal_min'])
        add(f'CAL-{i}', 'schedule_data/paired_control_calendars.csv', f'CSV line {i};{r["pair"]};{r["date_local"]}',
            'QUARANTINE_PLACEHOLDER' if zero else 'REJECT_SCENARIO_CLOCK' if error else 'SCENARIO_NOT_FUTURE_OFFER',
            'NONE: physical chain rebuilt from admitted directions',
            'SVX-SVX is not a flight' if zero else 'UTC/local mismatch; reconstruct via zoneinfo and admitted block' if error else 'UTC arithmetic agrees, but no tail/crew/2027 schedule proof',
            original_origin=r['origin'], original_destination=r['destination'], source_utc_elapsed_min=elapsed,
            stated_block_min=float(r['block_nominal_min']), difference_min=error)
    add('CARGO-S06', 'cargo_data/airport_handling.csv', 'source_id S06; ar-rmz.ru', 'QUARANTINE_AIRPORT_IDENTITY',
        'NONE for SVX operating hours', 'Remezov/different-airport hostname; identification unconfirmed. Never transfer to Koltsovo.')
    add('CARGO-S05', 'cargo_data/airport_handling.csv', 'source_id S05', 'PUBLISHED_CHANNEL_ONLY',
        '24h terminal context only', 'No RW acceptance, flight cutoff, contract or price established')
    add('WEIGHT-REPAIR', 'cargo_data/capacity_assumptions.csv', 'structural payload ceiling; commercial cargo residual', 'REPLACE_AMBIGUOUS_FORMULA',
        'One noncargo subtraction in each total-mass constraint', 'Hold constraint subtracts only load actually in hold; cabin passenger mass never deducted from hold4200')
    add('RRJ95B-TCDS', 'cargo_data/aircraft_payload_limits.csv', 'S03; EASA.IM.A.176 issue03 p13 copy', 'VARIANT_BOUNDARY_ONLY',
        'MTOW45880 MLW41000 MZFW40000 conditional B frontier', 'Secondary hosted old document; not LR approval, actual DOW or RW configuration')
    add('HOLD-MAX', 'cargo_data/aircraft_payload_limits.csv', 'S04; RW cargo', 'MARKETING_MAXIMUM_ONLY',
        '4200kg;20.15m3 conditional compartment ceiling', 'Not free capacity; floor, geometry, distribution and variant UNKNOWN')
    add('RATES-DEMAND', 'cargo_data/cargo_rates.csv;directional_demand.csv', 'OMS/GOJ/KUF to SVX', 'UNKNOWN',
        'Thresholds only', 'Quote channel is not an order, price, realized net rate or contract')
    add('ASR', 'inputs/transcripts/New Recording 5.txt;New Recording 6.txt', 'both complete transcripts; transcript_manifest.json', 'QUALITATIVE_ONLY',
        'joint planning, cascade, cargo request process', 'Aeroflot attribution per user; ASR errors; no numerical RW inputs')
    add('BLOCK-OMS', '../31_direct_growth_research_20261112/ops_inputs/directed_blocks.csv', 'svx_dep:317;svx_arr:342', 'PUBLISHED_RRJ95B_ANALOGUE',
        'SVX-OMS100;OMS-SVX105', 'Not dated2027 timetable, actual operation or same-tail proof')
    add('BLOCK-KUF', '../31_direct_growth_research_20261112/ops_inputs/directed_blocks.csv', 'svx_dep:375-379;kuf_dep:19-23;svx_arr:391-395', 'PUBLISHED_VARIANT_ANALOGUES',
        'SVX-KUF105;KUF-SVX100 for RRJ95B scenario', 'B100 reverse08:00KUF to10:40SVX admitted separately from LR105 to10:45. Do not mix variants; the cheaper package105 reverse is not silently relabeled B.')
    add('BLOCK-GOJ', 'schedule_data/flight_chain_evidence.csv', 'SVX-GOJ rows; conflict UNKNOWN', 'SCENARIO_ONLY',
        '130 each direction is an analyst point', 'Do not adopt127/103 from weaker saved board as exact GOJ blocks; applicability UNKNOWN')
    add('FOLLOW-CHAINS', 'schedule_data/README.md;../31_direct_growth_research_20261112/ops_inputs/directed_blocks.csv', 'reconstructed two physical RTs', 'CONTROLLED_SAME_TAIL_SCENARIO',
        'Four retained sectors common P/KEEP; tail S1 conditional existing RRJ95B', 'All clocks, rotations and same-tail assignment scenario; no actual idle or donor established')
    add('COMMON', '../31_direct_growth_research_20261112/audit/common_contract.json', 'resource;market_seat_rules;support_cases', 'COMPLETED_CONDITIONAL_CONTRACT',
        'H1 existing fleet only; NS; donor/F once; 45/60 min diagnostic', '8BH not FDP; actual released tail, crew/MRO/reserve UNKNOWN')
    add('RE-API', '../31_direct_growth_research_20261112/route_economics/APIhandoff.json', 'evaluate_combined_programme; README; calculate.py', 'REUSE_COMPLETED_API',
        'Joint directed monthly pool/physical seats; P minus retained affected KEEP', 'No solo-margin summation; supplied explicit physical calendars; full company scope UNKNOWN')
    add('P04-P05', '../31_direct_growth_research_20261112/route_economics/calculate.py', 'costs;fare;choice_bundle;evaluate_combined_programme', 'EXPLICIT_SCENARIO_TRANSFER',
        'Same P05/P04 base/cautious drivers, constant RUB2026; NS', 'Historical cost points not 2027 paid prices; opaque pax500/650 remains F; no ground-delay block expense')
    add('OPS-REVIEW', '../31_direct_growth_research_20261112/source_review/README.md', 'canonical admission and findings', 'COMPLETED_ADMISSION_LIMITS',
        'No new OD/netyield/contracts; published not flown', 'No date/variant/same-tail promotion from mixed sources')
    return rows


def build_delay():
    controls, events, summaries, recovery = [], [], [], []
    for route in ROUTES:
        for layout in LAYOUTS:
            cc = chain(route, layout)
            for control, fs in cc.items():
                for seq, f in enumerate(fs, 1):
                    controls.append(dict(route=route, layout=layout, control=control, sequence=seq,
                        flight_id=f['fid'], origin=f['origin'], destination=f['destination'], kind=f['kind'],
                        dep_utc=iso(f['dep']), arr_utc=iso(f['arr']), dep_local=clock(f['dep'],f['origin']),
                        arr_local=clock(f['arr'],f['destination']), block_min=f['block'], tail='S1_CONDITIONAL_EXISTING_RRJ95B',
                        tail_assignment='UNKNOWN_actual;SCENARIO_model', source=f['source'], date_status='FEB01_07_2027_SCENARIO',
                        known_other_gates='NONE_NUMERIC;crew_MRO_slot_handling_UNKNOWN', gap_status='CONTROLLED_G_NOT_ACTUAL_IDLE'))
            for turn in (45, 60):
                for shock in SHOCKS:
                    rr = {c: replay(fs, turn, shock if c == 'P' else 0) for c,fs in cc.items()}
                    for control, rs in rr.items():
                        for seq, e in enumerate(rs, 1):
                            f = e['flight']
                            events.append(dict(route=route, layout=layout, min_turn_scenario_min=turn,
                                injection_min=shock, injection_point='NEW-OUT_departure_hold_only_P', control=control, sequence=seq,
                                flight_id=f['fid'], origin=f['origin'], destination=f['destination'], kind=f['kind'],
                                planned_dep_utc=iso(f['dep']), planned_arr_utc=iso(f['arr']),
                                actual_dep_utc=iso(e['actual_dep']), actual_arr_utc=iso(e['actual_arr']),
                                planned_dep_local=clock(f['dep'],f['origin']), actual_dep_local=clock(e['actual_dep'],f['origin']),
                                actual_arr_local=clock(e['actual_arr'],f['destination']),
                                block_min=f['block'], aircraft_ready_utc=iso(e['aircraft_ready']),
                                known_other_ready_utc=iso(e['known_other_ready']), imposed_hold_until_utc=iso(e['imposed']),
                                incoming_delay_min=e['incoming_delay'], available_buffer_above_min_turn_min=e['buffer'],
                                buffer_consumed_min=e['absorbed'], dep_delay_min=e['dep_delay'], arr_delay_min=e['arr_delay'],
                                cycle_count=1, extra_block_min_from_ground_delay=0, crew_MRO_status='UNKNOWN'))
                    following = [e for e in rr['P'] if e['flight']['kind'] == 'retained']
                    delayed = [e for e in following if e['dep_delay'] > 0]
                    first, last = following[0], following[-1]
                    returned = rr['P'][1]
                    no_late = next((e['flight']['fid'] for e in rr['P'][1:] if e['dep_delay'] == 0), None)
                    prebuffer = 60-turn
                    nextbuffer = minutes(first['flight']['dep']-returned['flight']['arr'])-turn
                    summaries.append(dict(route=route, layout=layout, min_turn_scenario_min=turn,
                        injection_min=shock, new_out_delay_min=rr['P'][0]['dep_delay'], new_return_arr_delay_min=returned['arr_delay'],
                        outstation_buffer_above_turn_min=prebuffer, return_to_first_KEEP_buffer_min=nextbuffer,
                        max_injected_delay_without_first_KEEP_lateness_min=prebuffer+nextbuffer,
                        first_KEEP_dep_delay_min=first['dep_delay'], delayed_retained_departures=len(delayed),
                        retained_sum_departure_delay_min=sum(e['dep_delay'] for e in following),
                        KEEP_delayed_departures=sum(e['dep_delay']>0 for e in rr['KEEP']),
                        excess_P_minus_KEEP_departure_delay_min=sum(e['dep_delay'] for e in following)-sum(e['dep_delay'] for e in rr['KEEP']),
                        last_retained_arrival_delay_min=last['arr_delay'], terminal_tail_location='SVX',
                        first_absorbed_flight=no_late, horizon_planned_arrival_utc=iso(last['flight']['arr']),
                        horizon_actual_arrival_utc=iso(last['actual_arr']),
                        stop_state='AIRCRAFT_DELAY_ABSORBED' if last['arr_delay']==0 else 'HORIZON_WITH_POSITIVE_RESIDUAL',
                        extra_new_RT_crew_duty_window_min=returned['arr_delay'],
                        extra_follow_KUF_crew_duty_window_min=following[1]['arr_delay'],
                        extra_follow_OMS_crew_duty_window_min=following[3]['arr_delay'],
                        crew_rule='Need max(0,extension-actual_remaining_duty); rest deficit=max(0,release_delay-actual_rest_surplus)',
                        actual_remaining_duty_min=None, actual_min_rest_min=None, actual_rest_surplus_min=None,
                        hard_cutoff_utc=None, max_injection_before_confirmed_cutoff_min=None,
                        hypothetical_first_KEEP_cutoff_slack_min=30,
                        max_injection_before_hypothetical_cutoff_min=prebuffer+nextbuffer+30,
                        hypothetical_cutoff_excess_min=max(0,first['dep_delay']-30),
                        cancellation='CONDITIONAL_NEED_ONLY;hard_cutoff_and_recovery_availability_UNKNOWN', probability=None))
                    if shock == 0:
                        continue
                    for option in ('ADD_BUFFER', 'EARLIER_NEW_RT', 'RETIME_FOLLOWING', 'END_OF_DAY', 'RESERVE_TAIL', 'SWAP_CREW'):
                        need = first['dep_delay']
                        resource = ('S1 plus additional protected gap' if option in ('ADD_BUFFER','EARLIER_NEW_RT','END_OF_DAY')
                                    else 'S1 plus revised slots and all downstream acceptance' if option=='RETIME_FOLLOWING'
                                    else 'R1 existing compatible RRJ95B + qualified crew at SVX' if option=='RESERVE_TAIL'
                                    else 'C1 qualified flight-ready crew at SVX; aircraft still required')
                        recovery.append(dict(route=route, layout=layout, min_turn_scenario_min=turn, injection_min=shock,
                            option=option, minutes_needed_to_protect_first_KEEP=need,
                            protects_aircraft_cascade=(option!='SWAP_CREW'), required_resource=resource,
                            ready_location='SVX', latest_flight_ready_for_ontime_utc=iso(first['flight']['dep']),
                            latest_flight_ready_hypothetical_cutoff_utc=iso(first['flight']['dep']+timedelta(minutes=30)),
                            confirmed_latest_ready_utc=None, resource_availability='UNKNOWN',
                            resource_exclusivity='Alternatives, not simultaneous. R1 covers entire retained closed 4-leg chain; S1 remains SVX. One resource cannot cover another call.',
                            additional_new_RT_crew_window_min=returned['arr_delay'],
                            next_rest_extra_needed_if_surplus0_min=returned['arr_delay'],
                            next_rest_extra_needed_if_surplus60_min=max(0,returned['arr_delay']-60),
                            first_KEEP_delay_after_option_if_confirmed_min=need if option=='SWAP_CREW' else 0,
                            terminal_delay_after_option_if_confirmed_min=last['arr_delay'] if option=='SWAP_CREW' else 0,
                            result_clock_basis='Revised calendar for RETIME/END_OF_DAY; original clocks for other alternatives',
                            cost_RUB=None, ground_delay_block_cost_RUB=0,
                            cost_condition=('C_swap + C_position + C_donor_reserve <= L_avoided' if option=='RESERVE_TAIL'
                                            else 'C_crew + C_position <= L_avoided_due_to_crew_gate' if option=='SWAP_CREW'
                                            else 'C_option + lost_donor_or_buffer_contribution <= L_avoided'),
                            break_even_probability='p_BE=C_resilience/L_avoided if L_avoided>0; p and L UNKNOWN',
                            restriction='Crew swap cannot advance a late aircraft. Retiming shifts passenger times. Earlier/buffer/end-day require real freed gap; next-day rest/MRO persists.'))
    return controls, events, summaries, recovery


def econ_request(route, with_new):
    """Complete calendar for API, not route engine geometric clock defaults.

    Old target RT Monday is explicitly one retained frequency in this scenario.
    Two downstream RTs are also retained. Other RW products/donor UNKNOWN.
    API's protected reserve is an anonymous CONDITIONAL existing resource;
    reserve_available=None ensures it is never reported as a real free reserve.
    """
    away, out, back = ROUTES[route]
    b = {('SVX','KUF'):105, ('KUF','SVX'):100, ('SVX','OMS'):100, ('OMS','SVX'):105}
    b.update({('SVX',away):out,(away,'SVX'):back})
    def pattern(id_, dest, day, time):
        return dict(id=id_,path=['SVX',dest,'SVX'], weekdays=[datetime.fromisoformat(day).isoweekday()],
                    frequency_per_week=1, operating_weeks=['2027-02-01','2027-02-08','2027-02-15','2027-02-22'],start=day,end='2027-02-28',
                    departure_local=time,workingtailids=['S1'])
    pp = [pattern('OLD-TARGET',away,'2027-02-01','09:00'),
          pattern('FOLLOW-KUF','KUF','2027-02-03','00:30'),
          pattern('FOLLOW-OMS','OMS','2027-02-03','06:10')]
    if with_new:
        pp.append(pattern('NEW-TARGET',away,'2027-02-02','18:00'))
    return dict(timezones=ZONES,turn_minutes=60,block_case='nominal',diagnostic_bh_day=8,
        blocks=[dict(origin=a,destination=z,nominal_minutes=m,high_minutes=m,aircraft_variant='RRJ-95B',
                     evidence='EXPLICIT_GOJ_SCENARIO_NOT_BLOCK_FACT' if 'GOJ' in (a,z) else 'CONDITIONAL_DIRECTIONAL_VARIANT_TIMING_ANALOGUE') for (a,z),m in sorted(b.items())],
        tails=[dict(id='S1',type='RRJ-95B',initial_location='SVX',available_from='2027-02-01T00:00:00Z',
                    available_to='2027-03-01T00:00:00Z',donor='UNKNOWN;conditional_G_not_actual_idle'),
               dict(id='R1',type='RRJ-95B',initial_location='SVX',reserve=True,donor='UNKNOWN;not_confirmed_available')],
        patterns=pp)


def build_passengers(re):
    ledger, cases, requests = [], [], {}
    for route,(away,_,_) in ROUTES.items():
        calendars = {'P':econ_request(route,True), 'KEEP':econ_request(route,False)}
        requests[route] = calendars
        for scenario in ('base','cautious'):
            for alpha in ALPHAS:
                overrides = {}
                directions = {('SVX','KUF'),('KUF','SVX'),('SVX','OMS'),('OMS','SVX'),('SVX',away),(away,'SVX')}
                for a,b in sorted(directions):
                    prior,_,_ = re.annual(a,b,scenario,2027)
                    pot = prior*.5*re.P05.monthly_profile(2027)[2]/.6
                    overrides[f'{a}>{b}/2027-02'] = pot*(alpha if (a,b)==(away,'SVX') else 1)
                result = re.evaluate_combined_programme([], scenario, keep_patterns=[],
                    start='2027-02-01',end='2027-02-28',demand_overrides=overrides,
                    donor_loss=None,omitted_F=None,existing_slots=1,delivery_scenario='S0',reserve_available=None,
                    calendar_requests=calendars)
                if 'programme' not in result:
                    raise ValueError((route,result))
                sector_rows = {}
                for control,key in [('P','programme'),('KEEP','keep')]:
                    v = result[key]
                    by_flight = defaultdict(float)
                    products = {p['product_id']:p for p in v['bundle']['products']}
                    for a in v['allocation']['allocations']:
                        if a['owner']=='RW':
                            prod = products[a['product_id']]
                            # This study only admits direct single-leg products.
                            assert len(prod['legs'])==1
                            by_flight[prod['legs'][0]] += a['carried']
                    sector_rows[control] = []
                    for f in v['bundle']['flights']:
                        a,b = f['origin_airport'],f['destination_airport']
                        cost = re.costs(a,b,scenario,f['block_hours_costscreen'])
                        gross, net = re.fare(a,b,scenario)
                        pax = by_flight[f['flight_instance_id']]
                        row = dict(route=route,scenario=scenario,return_potential_alpha=alpha,control=control,
                            row_kind='PHYSICAL_SECTOR',flight_id=f['flight_instance_id'],pattern_id=f['pattern_id'],origin=a,destination=b,
                            departure_utc=f['departure_utc'],arrival_utc=f['arrival_utc'],block_hours=f['block_hours_costscreen'],
                            directed_cycles=1,modeled_pax=pax,saleable_seats=100, gross_fare_RUB=gross,net_fare_RUB=net,
                            net_revenue_RUB=pax*net,fuel_t_burn_cost_driver=cost['fuel_t'],
                            fuel_RUB=cost['fuel_cost'],nonfuel_block_cycle_RUB=cost['other_cost'],known_cost_RUB=cost['fixed_cost'],
                            allocated_sector_contribution_RUB=pax*net-cost['fixed_cost'],
                            fixed_opaque_pax_cost_included=False,omitted_pax_cost_axis_RUB_per_pax=cost['pax_unknown_stress'],
                            support_RUB=0,price_year=2026,new_frequency=f['pattern_id'].startswith('NEW-TARGET'),
                            scope='JOINT_P05_P06_CONTROLLED_AFFECTED_KEEP_NOT_FULL_RW',actual_pax=None,full_result_RUB=None)
                        sector_rows[control].append(row)
                        ledger.append(row)
                newrows = [r for r in sector_rows['P'] if r['new_frequency']]
                out = [r for r in newrows if r['origin']=='SVX']
                back = [r for r in newrows if r['destination']=='SVX']
                added_turns = len(out)
                assert added_turns == len(back) == 4
                p, k = result['programme'],result['keep']
                month_m = result['known_increment_P_minus_KEEP_before_F_donor']
                m = month_m/added_turns
                retained_p = sum(r['net_revenue_RUB'] for r in sector_rows['P'] if not r['new_frequency'])
                own_loss = k['net_revenue']-retained_p
                case = dict(route=route,scenario=scenario,return_potential_alpha=alpha,
                    monetary_scope='PER_ADDED_RT_FROM_FEB2027_FOUR_WEEK_SCENARIO',added_monthly_turns=added_turns,
                    new_out_pax=sum(r['modeled_pax'] for r in out)/added_turns,
                    new_back_pax=sum(r['modeled_pax'] for r in back)/added_turns,
                    allocated_new_out_contribution_RUB=sum(r['allocated_sector_contribution_RUB'] for r in out)/added_turns,
                    allocated_new_back_contribution_RUB=sum(r['allocated_sector_contribution_RUB'] for r in back)/added_turns,
                    allocated_new_RT_contribution_RUB=sum(r['allocated_sector_contribution_RUB'] for r in newrows)/added_turns,
                    P_net_revenue_RUB=p['net_revenue'],KEEP_net_revenue_RUB=k['net_revenue'],
                    P_known_cost_RUB=p['known_cost'],KEEP_known_cost_RUB=k['known_cost'],
                    own_retained_revenue_loss_RUB=own_loss/added_turns,
                    monthly_known_increment_P_minus_KEEP_RUB=month_m,
                    known_increment_P_minus_KEEP_before_F_donor_delay_RUB=m,
                    incremental_RW_pax=(p['rw_journeys']-k['rw_journeys'])/added_turns,
                    return_allocated_loss_RUB=max(0,-sum(r['allocated_sector_contribution_RUB'] for r in back)/added_turns),
                    whole_turn_launch_gap_before_unknowns_RUB=max(0,-m),
                    full_P_minus_KEEP_RUB=None,F_actual_RUB=None,donor_actual_RUB=None,delay_cost_actual_RUB=None,
                    actual_return_weakness='UNKNOWN;alpha_common_P_KEEP_sensitivity_not_observed',
                    allocator_status=result['status'],reserve_available='UNKNOWN',
                    scope='Each of four February weeks: retained Monday target RT plus two following RTs in KEEP; P adds Tuesday target RT. Whole February choice prevents partial-horizon frequency distortion. Actual full affected RW programme UNKNOWN.')
                cases.append(case)
                ledger.append(dict(case,row_kind='PAIRED_TURN_P_MINUS_KEEP',control='P-KEEP',
                    revenue_increment_RUB=(p['net_revenue']-k['net_revenue'])/added_turns,
                    cost_increment_RUB=(p['known_cost']-k['known_cost'])/added_turns,
                    support_RUB=0,price_year=2026,old_target_frequency_basis='1/week scenario plus following task if same pair; not observed RW frequency',
                    opaque_pax_cost_treatment='500/650 remains omitted F until nonoverlap bridge; distribution already in P05 net',
                    extra_block_cost_due_to_ground_delay_RUB=0))
    write_json('api_requests.json',requests)
    write_json('economic_cases.json',cases)
    return ledger,cases


def mass_boundary(pnoncargo, q, fuel_dep, fuel_arr):
    """Upper allowable actual DOW for given physical load, not DOW estimate."""
    return min(40000-pnoncargo-q,45880-fuel_dep-pnoncargo-q,41000-fuel_arr-pnoncargo-q)


def conditional_capacity(dow, fuel_dep, fuel_arr, n, body=75, cabin=10, checked=20,
                         mail=0, comat=0, bag_density=200, cargo_density=100,
                         floor_limit=None, geometry_limit=None):
    """Diagnostic max; approved capacity NULL if any operational limit unknown.

    Cabin bags10 are outside body75. Hold contains checked bags, mail, COMAT.
    DOW already contains operator items: comat is only extra, never in DOW too.
    """
    pnoncargo=n*(body+cabin+checked)+mail+comat
    totalmass=min(40000-dow-pnoncargo,45880-dow-fuel_dep-pnoncargo,41000-dow-fuel_arr-pnoncargo)
    holdmass=4200-n*checked-mail-comat
    volume=20.15-(n*checked+mail+comat)/bag_density
    upper=max(0,min(totalmass,holdmass,volume*cargo_density))
    approved=None if floor_limit is None or geometry_limit is None else max(0,min(upper,floor_limit,geometry_limit))
    return dict(pnoncargo=pnoncargo,totalmass=totalmass,holdmass=holdmass,
                free_volume=volume,conditional_upper=upper,approved_capacity=approved)


def chargeable_kg(physical_kg, volume_m3, divisor=None, rounding_kg=None, minimum_kg=0):
    if divisor is None:
        return None
    q=max(physical_kg,volume_m3*1_000_000/divisor,minimum_kg)
    return math.ceil(q/rounding_kg)*rounding_kg if rounding_kg else q


def paid_threshold(margin, net_rate, omitted_F=0, donor=0, delay_cost=0, fixed_awb=0):
    """Zero omissions are a boundary argument, never an actual-input assertion."""
    loss=max(0,omitted_F+donor+delay_cost+fixed_awb-margin)
    return loss/net_rate if net_rate>0 else 0 if loss==0 else None


def build_cargo(cases):
    be, frontier, decisions = [], [], []
    for c in cases:
        base={k:c[k] for k in ('route','scenario','return_potential_alpha')}
        m=c['known_increment_P_minus_KEEP_before_F_donor_delay_RUB']
        for r in RATES:
            be.append(dict(base,net_contribution_per_paid_kg_axis_RUB=r,
                axis_status='DIAGNOSTIC_NOT_PRICE_OR_DEMAND',
                return_allocated_loss_RUB=c['return_allocated_loss_RUB'],
                kg_paid_BE_allocated_return=paid_threshold(-c['return_allocated_loss_RUB'],r),
                whole_P_minus_KEEP_before_unknowns_RUB=m,
                kg_paid_BE_launch_before_unknowns=paid_threshold(m,r),
                monetary_scope='PER_ADDED_RT_FROM_FEB2027_FOUR_WEEK_SCENARIO',
                whole_launch_formula='max(0,F_net+D_external+C_delay+C_AWB-known_increment)/r',
                return_formula='max(0,loss_back+C_AWB_back+nonoverlap_back_cost)/r',
                F_net_RUB=None,D_external_RUB=None,C_delay_RUB=None,C_AWB_RUB=None,
                actual_required_paid_kg_for_launch=None,actual_paid_orders_kg=None,actual_net_rate=None,
                actual_physical_capacity_kg=None,
                rate_scope='Net paid-kg contribution after VAT/agent/variable handling/additional fuel/displaced pax or baggage; fixed AWB in C_AWB once',
                decision_rule='If whole turn already positive, back-sector repair alone is not a launch reversal; F/donor/delay can still reverse',
                physical_mapping='UNKNOWN_AWB_divisor_density_rounding_minimum;paid_kg_not_payload_kg'))
        decisions.append(dict(base,threshold='WHOLE_TURN',known_subtotal_RUB=m,
            max_combined_F_donor_delay_before_cargo_RUB=m,
            required_cargo_net_contribution_before_unknowns_RUB=max(0,-m),
            full_decision='LAUNCH only if m+q_paid*r-F_net-D_external-C_delay-C_AWB>=0 AND operations/capacity/order gates confirmed',
            actual_decision='UNKNOWN',next_RW_data='All affected KEEP products/yields and donor; dated tail/crew/MRO; net cargo quote/orders and approved load',
            probability=None,delay_minute_price_RUB=None,cancellation_saving_RUB=None))
        decisions.append(dict(base,threshold='RESILIENCE',known_subtotal_RUB=None,
            full_decision='C_swap+C_position+C_donor_reserve <= L_avoided; p_BE=C_resilience/L_avoided, L_avoided>0',
            actual_decision='UNKNOWN',next_RW_data='Avoidable scenario lost contribution + reaccommodation/refund/position recovery; fixed cancellation costs and probabilities',
            probability=None,delay_minute_price_RUB=None,cancellation_saving_RUB=None))
    # Frontier contains no invented DOW point. Fuel and passenger/bag/density
    # axes are explicitly arbitrary diagnostics, with output max allowable DOW.
    for route in ROUTES:
        for n in (25,50,75,100):
            for bags in (10,20):
                for rho in (100,250):
                    hold=4200-n*bags
                    volume=20.15-n*bags/200
                    for depfuel in (3000,4500,6000):
                        for q in (0,250,500,1000,2000,3000,4200):
                            noncargo=n*(75+10+bags)
                            paid=chargeable_kg(q,q/rho,6000)
                            frontier.append(dict(route=route,frontier_kind='DIAGNOSTIC_PARAMETER_GRID_NOT_LOADSHEET',
                                variant='RRJ95B_BOUNDARY_ONLY_NOT_LR_APPROVAL',passengers_axis=n,body_kg_each_axis=75,
                                cabin_bag_kg_each_axis=10,checked_bag_kg_each_axis=bags,mail_COMAT_extra_kg_axis=0,
                                noncargo_total_mass_kg=noncargo,hold_non_cargo_mass_kg=n*bags,
                                bag_density_kg_m3_axis=200,cargo_density_kg_m3_axis=rho,
                                physical_cargo_kg_axis=q,cargo_volume_m3=q/rho,remaining_hold_mass_kg=hold,
                                remaining_hold_volume_m3=volume,
                                max_physical_from_hold_and_volume_upper_kg=max(0,min(hold,volume*rho)),
                                fits_marketing_hold_mass=(q<=hold),fits_marketing_volume=(q/rho<=volume),
                                departure_fuel_including_reserves_kg_axis=depfuel,arrival_fuel_kg_axis=1500,
                                max_allowed_DOW_kg=mass_boundary(noncargo,q,depfuel,1500),
                                max_allowed_departure_fuel_formula=f'45880-DOW_actual-{noncargo}-{q}',
                                diagnostic_AWB_divisor_cm3_per_kg=6000,diagnostic_chargeable_kg_no_rounding_minimum=paid,
                                actual_DOW_kg=None,actual_fuel_dep_kg=None,actual_physical_residual_kg=None,
                                actual_chargeable_residual_kg=None,approved_cargo_capacity_kg=None,
                                floor_geometry_distribution='UNKNOWN;all must pass even when these inequalities pass',
                                caveat='0 mail/COMAT is scenario only; DOW includes crew/equipment once; fuel dep includes reserves, not burn-only. LR capacity UNKNOWN, not zero.'))
    # Link paid thresholds to physical frontiers for every diagnostic rate;
    # no silent equality of paid kg and real mass.
    for c in cases:
        for rate in RATES:
            paid=c['whole_turn_launch_gap_before_unknowns_RUB']/rate
            for rho in (100,250):
                ratio=max(1,1_000_000/6000/rho)
                physical=paid/ratio
                for n in (50,100):
                    noncargo=n*(75+10+20)
                    hold=4200-n*20
                    volume=20.15-n*20/200
                    frontier.append(dict(route=c['route'],scenario=c['scenario'],return_potential_alpha=c['return_potential_alpha'],
                        frontier_kind='LAUNCH_BE_LINK_DIAGNOSTIC_RATE_DIV6000',variant='RRJ95B_BOUNDARY_ONLY_NOT_LR_APPROVAL',
                        net_contribution_per_paid_kg_axis_RUB=rate,
                        passengers_axis=n,body_kg_each_axis=75,cabin_bag_kg_each_axis=10,checked_bag_kg_each_axis=20,
                        mail_COMAT_extra_kg_axis=0,noncargo_total_mass_kg=noncargo,hold_non_cargo_mass_kg=n*20,
                        bag_density_kg_m3_axis=200,cargo_density_kg_m3_axis=rho,physical_cargo_kg_axis=physical,
                        paid_kg_BE_before_unknowns=paid,cargo_volume_m3=physical/rho,
                        remaining_hold_mass_kg=hold,remaining_hold_volume_m3=volume,
                        max_physical_from_hold_and_volume_upper_kg=max(0,min(hold,volume*rho)),
                        fits_marketing_hold_mass=(physical<=hold),fits_marketing_volume=(physical/rho<=volume),
                        departure_fuel_including_reserves_kg_axis=4500,arrival_fuel_kg_axis=1500,
                        max_allowed_DOW_kg=mass_boundary(noncargo,physical,4500,1500),
                        diagnostic_AWB_divisor_cm3_per_kg=6000,diagnostic_chargeable_kg_no_rounding_minimum=paid,
                        actual_DOW_kg=None,actual_physical_residual_kg=None,approved_cargo_capacity_kg=None,
                        actual_chargeable_residual_kg=None,floor_geometry_distribution='UNKNOWN',
                        caveat='Continuous one-AWB/no rounding or minimum diagnostic; net rate axis is not a quote. Add F/donor/delay/fixed AWB first.'))
    for route in ROUTES:
        frontier.append(dict(route=route,frontier_kind='LR_UNKNOWN_NOT_ZERO',variant='RRJ95LR_REQUIRES_OWN_LIMITS_AND_LOADSHEET',
            actual_DOW_kg=None,actual_physical_residual_kg=None,actual_chargeable_residual_kg=None,
            approved_cargo_capacity_kg=None,floor_geometry_distribution='UNKNOWN',
            caveat='No B45880/41000/40000 limits automatically transferred to LR; lack of data is not zero capacity.'))
    return be,frontier,decisions


def assumptions():
    items=[
        ('A01','Feb01-07 2027 is scenario, not an approved published2027 calendar','All dates/clocks and tail S1 assignment conditional; actual donor/gap UNKNOWN'),
        ('A02','S1 and optional R1 are existing RRJ95B conditional resources only','No SJ100 in H1, including reserve; no fleet-stock=free-tail inference'),
        ('A03','OMS100/105;KUF105/100 directed RRJ95B timing analogues','KUF B reverse08:00 to10:40=100 kept separate from LR08:00 to10:45=105; published offers not same tail or approved future blocks'),
        ('A04','GOJ130/130 purely analyst scenario','Exact blocks conflict UNKNOWN; not credible range bound or false factual row'),
        ('A05','New RT dep18:00SVX Feb02; away scheduled turn60','Physical time arithmetic in UTC with IANA zones'),
        ('A06','G390 next00:30SVX Feb03; equalbuffer next=new arrival+90; endday next09:00','Same four physical subsequent tasks in P and KEEP per layout. Equalbuffer30 is above T60;45 at T45'),
        ('A07','Four retained sectors:KUF105/100 then OMS100/105','Away scheduled turns60; between RTs75; all clocks and same-tail assignment scenario'),
        ('A08','Minimum turn45/60 diagnostic P03 only','Crew remaining duty/rest/report/release/MRO/slots/airport and cargo cutoff UNKNOWN;8BH not FDP'),
        ('A09','Single departure hold at NEW-OUT +0/+30/+60/+120','Isolated exogenous experiment, not a probability or causal shared-weather proof'),
        ('A10','Constant block after ground hold; known other-ready gate defaults plan','No taxi/APU incremental cost invented; unknown actual gates require separate data'),
        ('A11','Econ each of four February weeks: KEEP Monday target RT plus following KUF/OMS RTs','Full-month joint choice; divide monthly delta by four added RTs for perturn thresholds. Avoid partial-month API frequency distortion. Complete affected company KEEP UNKNOWN'),
        ('A12','Same P05 directed monthly potential pool and P06 physical inventory in P/KEEP','Alpha1/.5/.25/0 only return potential multiplied equally P/KEEP, not an observed weak route'),
        ('A13','P04 historical cost scenario transfer and P05 net fares; no support','Constant RUB2026; price2027 contract/taxes UNKNOWN; opaque pax500/650 left in F to avoid distribution overlap'),
        ('A14','Full M+qpaid*r-F-D-Cdelay-CAWB','Donor outside affected KEEP once; fixed cargo AWB once; netrate after all variable cost/displacement; no expected value with unknown probability'),
        ('A15','Net paidkg rate25/50/100/200/400 diagnostic grid','Not market quotes, demand, orders or revenue evidence; r<=0 cannot repair positive loss'),
        ('A16','Weight formula subtracts noncargo once within each mass term','DOW not OEW; include dispatch reserves at departure; cabin bags only once'),
        ('A17','RRJ95B45880/41000/40000 boundary and hold4200/20.15 marketing caps','Not LR operating approval; unknown DOW/fuel/floor/geometry -> actual residualNULL; LR unknown not0'),
        ('A18','Mass axes N25/50/75/100, body75+cabin10, checked10/20,mail/COMAT0','Arbitrary sensitivities, not operator mass standard or actual load; DOW crew/equipment/COMAT overlap must be reconciled'),
        ('A19','FuelDep3000/4500/6000 includes reserves;FuelArr1500;bag density200,cargo100/250','Diagnostic axes only; maxDOW threshold is not an invented DOW point'),
        ('A20','AWB divisor6000 cm3/kg with no rounding/minimum only diagnostic','Actual billing UNKNOWN; paid kg not physical kg; m3 never added to kg'),
        ('A21','Hypothetical cutoff first retained dep+30','Actual hardcutoff and maximum delay before it NULL; crossing hypothesis needs recovery, not automatic cancellation'),
        ('A22','Alternative R1 occupies all four downstream sectors and returnsSVX','Separate compatible type/crew/location/readiness required; not double-booked or actually available'),
        ('A23','Crew additional window=delay to crew segment final arrival, before unknown slack','Report/release offsets unchanged scenario; need=max(0,window-remaining duty), rest=max(0,release delay-rest surplus)')]
    return [dict(assumption_id=i,assumption=v,scope_and_limit=l,status='SCENARIO_OR_UNKNOWN_NOT_RW_FACT') for i,v,l in items]


def input_paths():
    paths=[]
    for folder in ('schedule_data','cargo_data','inputs'):
        paths.extend(p for p in (STUDY/folder).rglob('*') if p.is_file())
    paths.extend(STUDY/n for n in ('TASKS.md','EXPERT_PRACTICE.md'))
    # Capture imported source and its pinned local dependencies, not just CSV outputs.
    for folder in ('audit','ops_inputs','source_review','route_economics'):
        paths.extend(p for p in (C31/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    return sorted(set(paths))


def build():
    re=load_economics()
    controls,events,summaries,recovery=build_delay()
    ledger,cases=build_passengers(re)
    be,frontier,decisions=build_cargo(cases)
    route_summary=[]
    for route in ROUTES:
        b=next(c for c in cases if c['route']==route and c['scenario']=='base' and c['return_potential_alpha']==1)
        k=next(c for c in cases if c['route']==route and c['scenario']=='cautious' and c['return_potential_alpha']==1)
        stress=next(s for s in summaries if s['route']==route and s['layout']=='EQUAL_GAP_G390' and s['min_turn_scenario_min']==60 and s['injection_min']==120)
        equal=next(s for s in summaries if s['route']==route and s['layout']=='EQUAL_BUFFER_B30' and s['min_turn_scenario_min']==60 and s['injection_min']==120)
        route_summary.append(dict(route=route,selection='Retain selected schedule/cargo cases; not top-margin ranking',
            schedule_evidence='SOURCE_DIRECTIONAL_ANALOGUES' if route!='SVX-GOJ' else 'GOJ_EXACT_BLOCK_UNKNOWN_130_SCENARIO_ONLY',
            cargo_research='UNKNOWN_directional_orders_rate_AWB_RW_handling_contract_all_three',
            base_alpha1_known_increment_RUB=b['known_increment_P_minus_KEEP_before_F_donor_delay_RUB'],
            cautious_alpha1_known_increment_RUB=k['known_increment_P_minus_KEEP_before_F_donor_delay_RUB'],
            base_alpha1_new_back_allocated_contribution_RUB=b['allocated_new_back_contribution_RUB'],
            G390_T60_D120_first_retained_delay_min=stress['first_KEEP_dep_delay_min'],
            G390_T60_D120_delayed_retained_departures=stress['delayed_retained_departures'],
            G390_T60_D120_terminal_residual_min=stress['last_retained_arrival_delay_min'],
            equalbuffer_T60_D120_first_retained_delay_min=equal['first_KEEP_dep_delay_min'],
            full_launch='UNKNOWN_actual_F_donor_ops_cargo',actual_physical_cargo_capacity_kg=None,
            answer_delay='Conditional on common G390: compare explicit blocks; equal buffer removes route ordering',
            answer_cargo='Require positive whole-turn delta after F/donor/delay, not repair of allocated back sector only',
            first_RW_fields='Dated KEEP/tail release+crew/MRO/slots; observed directed pax netyield; orders/net cargo quote/AWB and loadsheet'))
    outputs={'route_summary.csv':route_summary,'control_flights.csv':controls,'delay_events.csv':events,
             'delay_summary.csv':summaries,'recovery_options.csv':recovery,'passenger_turn_ledger.csv':ledger,
             'cargo_break_even.csv':be,'cargo_capacity_frontier.csv':frontier,'decision_thresholds.csv':decisions,
             'assumptions.csv':assumptions(),'source_admission.csv':source_admission()}
    for name,rs in outputs.items():
        table(name,rs)
    manifest=dict(version=VERSION,write_scope=str(HERE),source_network_access=False,
        input_files=[dict(path=str(p.relative_to(ROOT)),sha256=digest(p)) for p in input_paths()],
        outputs={n:dict(rows=len(rs),sha256=digest(HERE/n)) for n,rs in sorted(outputs.items())},
        auxiliary_outputs={n:digest(HERE/n) for n in ('api_requests.json','economic_cases.json')},
        code={n:digest(HERE/n) for n in ('calculate.py','verify.py') if (HERE/n).exists()},
        documentation={n:digest(HERE/n) for n in ('README.md',) if (HERE/n).exists()},
        units=dict(time='minutes UTC elapsed; local timestamps retain offset/date',mass='physical kg',
                   billing='paid chargeable kg, not physical kg',volume='m3',money='constant RUB2026; scenarios NS'),
        status='SCOPE_COMPLETE_CONDITIONAL_3_ROUTE_CASES_NOT_LAUNCH_OR_OPERATING_APPROVAL')
    write_json('manifest.json',manifest)
    return outputs


if __name__=='__main__':
    out=build()
    print(json.dumps({'status':'BUILT','rows':{n:len(r) for n,r in out.items()}},sort_keys=True))
