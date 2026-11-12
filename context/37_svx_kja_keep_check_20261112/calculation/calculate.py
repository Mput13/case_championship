#!/usr/bin/env python3
"""P37 narrow inverse direct-ticket threshold. No network, builders or Git.

Only P31 choice_bundle/P06.allocate pure seams are imported for historical
reproduction. All writes are restricted to this directory. Run with -B.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import csv
import hashlib
import importlib.util
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, getcontext
from pathlib import Path

getcontext().prec = 40
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
P36 = ROOT / 'context/36_overnight_chain_search_20261112'
P = P36 / 'pass2'
ZERO = Decimal(0)
D = Decimal
NET = {'base': D('14437.6991905'), 'cautious': D('12448.6253564')}
ALLOWED = {'README.md', 'costs.csv', 'break_even.csv', 'directional_frontier.csv',
           'quote_template.csv', 'actual_inputs_needed.csv', 'calculate.py',
           'verify.py', 'validation.json', 'source_manifest.json'}
READS = {}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source(path):
    path = Path(path).resolve()
    READS[str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)] = sha(path)
    return path


def rows(path):
    with source(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def write(name, value):
    assert name in ALLOWED and Path(name).name == name
    (HERE/name).write_text(value, encoding='utf-8')


def scalar(value):
    if value is None:
        return 'NULL'
    if isinstance(value, Decimal):
        return format(value, 'f')
    return value


def table(name, data):
    assert name in ALLOWED
    fields = list(dict.fromkeys(k for r in data for k in r))
    with (HERE/name).open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows({k: scalar(v) for k, v in r.items()} for r in data)


def dump(name, obj):
    write(name, json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2,
                           default=scalar, allow_nan=False) + '\n')


def digest_map(mapping):
    return hashlib.sha256(json.dumps(mapping, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def guard_snapshot():
    """Existing protected files plus all completed P36, no expanded registry."""
    protected = json.loads(source(P36/'protected_files.json').read_text())
    assert len(protected) == 1418
    actual = {p: sha(ROOT/p) for p in protected}
    assert actual == protected, 'Preexisting protected source mismatch'
    completed = {str(p.relative_to(ROOT)): sha(p) for base in (P36, ROOT/'P36')
                 if base.exists() for p in sorted(base.rglob('*'))
                 if p.is_file() and '__pycache__' not in p.parts}
    return {'protected_count': len(actual), 'protected_digest': digest_map(actual),
            'completed_P36_count': len(completed), 'completed_P36_digest': digest_map(completed)}


def min_strict(required, rate):
    """Smallest nonnegative integer n with n*rate > required; equality loses."""
    required, rate = D(required), D(rate)
    if rate <= 0:
        raise ValueError('Nonpositive marginal net: this frontier parameterization is unavailable')
    return max(0, int((required/rate).to_integral_value(rounding=ROUND_FLOOR)) + 1)


def extra_plan(required_revenue, out_rate, back_rate, out_cap, back_cap):
    """Fewest additional one-way tickets with two explicit remaining caps."""
    if required_revenue < 0:
        return (0, 0, True)
    out_first = out_rate >= back_rate
    first_rate, second_rate = (out_rate, back_rate) if out_first else (back_rate, out_rate)
    first_cap, second_cap = (out_cap, back_cap) if out_first else (back_cap, out_cap)
    first = min(first_cap, min_strict(required_revenue, first_rate))
    second = min_strict(required_revenue-first*first_rate, second_rate)
    return ((first, second, second <= second_cap) if out_first else
            (second, first, second <= second_cap))


def cost_components(sc, block_minutes=200):
    h = D(block_minutes)/60
    burn = h*(D('1.55') if sc == 'base' else D('1.9')) + (D('.20') if sc == 'base' else D('.25'))
    landed = D(137996 if sc == 'base' else 161696)
    mro = h*D(35000 if sc == 'base' else 55000)
    nav = h*D(6000 if sc == 'base' else 8000)
    ground, deice = (D(96089), D(15000)) if sc == 'base' else (D(115307), D(40000))
    return dict(block_minutes=D(block_minutes), block_hours=h, fuel_burned_t=burn,
                landed_fuel_rub_t=landed, fuel_rub=burn*landed,
                mro_rub=mro, navigation_rub=nav, ground_rub=ground, deice_rub=deice,
                cost_rub=burn*landed+mro+nav+ground+deice,
                fixed_crew_excluded_rub=h*D(15000 if sc == 'base' else 22000))


def load_api():
    path = source(ROOT/'context/31_direct_growth_research_20261112/route_economics/calculate.py')
    spec = importlib.util.spec_from_file_location('p37_pure_p31', path)
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    # No calculate/main/materialize/exporter or old verify is invoked.
    for base in (api.P05DIR, api.P06DIR, api.P04DIR, api.BASE):
        files = {str(p.relative_to(ROOT)): sha(p) for p in sorted(base.rglob('*'))
                 if p.is_file() and p.suffix in ('.py', '.json', '.csv') and '__pycache__' not in p.parts}
        READS['GROUP:'+str(base.relative_to(ROOT))] = {'count': len(files), 'sha256': digest_map(files)}
    for p in (api.ROOT/'ops_inputs/calendar_engine.py', api.ROOT/'audit/common_contract.json'):
        source(p)
    return api


def reproduce():
    """Four pure direct-only allocations; MAIN independently summed from ledgers."""
    states = [r for r in rows(P/'three_state_comparison.csv') if r['candidate_id'] == 'X_SVX_KJA']
    ledger, sales = rows(P/'revenue_cost_ledger.csv'), rows(P/'directional_sales_ledger.csv')
    weekly, sensitivity = rows(P/'final3_weekly_schedule.csv'), rows(P/'sensitivity.csv')
    eq = rows(P/'equivalence_map.csv')
    coverage = json.loads(source(P/'coverage_delta.json').read_text())
    blocks = {r['flight_id'].rsplit('/W', 1)[0]: float(r['block_minutes']) for r in weekly
              if r['candidate_id'] == 'X_SVX_KJA' and r['flight_id']}
    api = load_api()
    result = {}
    for sc in NET:
        bystate, ls_by_state, direct = {}, {}, {}
        for state in ('KEEP', 'WITHOUT_NEW', 'REPLACE'):
            r = next(r for r in states if r['scenario'] == sc and r['state'] == state)
            key = (r['equivalent_ledger_candidate'], sc, r['equivalent_ledger_state'])
            mapping = next(x for x in eq if (x['candidate_id'], x['scenario'], x['state']) == ('X_SVX_KJA', sc, state))
            assert key == (mapping['equivalent_candidate'], sc, mapping['equivalent_state'])
            ll = [a for a in ledger if (a['candidate_id'], a['scenario'], a['state']) == key]
            aa = [a for a in sales if (a['candidate_id'], a['scenario'], a['state']) == key]
            cost = sum(D(a['avoidable_variable_scenario']) for a in ll)
            rev = sum(D(a['net_revenue']) for a in aa)
            assert abs(rev-sum(D(a['revenue_once_allocated']) for a in ll)) < D('.01')
            assert abs(rev-cost-D(r['known_subtotal_before_C_D_F'])) < D('.01')
            for a in ll:
                cc = cost_components(sc, blocks[a['flight_id'].rsplit('/W', 1)[0]])
                assert abs(cc['cost_rub']-D(a['avoidable_variable_scenario'])) < D('.001')
                assert all(D(a[k]) == 0 for k in ('support', 'cargo', 'lease_avoided'))
            bystate[state] = rev-cost
            ls_by_state[state] = ll
            if state == 'WITHOUT_NEW':
                assert ll == ls_by_state['KEEP']
                direct[state] = direct['KEEP']
                continue
            fs = []
            for a in ll:
                h = blocks[a['flight_id'].rsplit('/W', 1)[0]]/60
                fs.append(dict(flight_instance_id=a['flight_id'], pattern_id=a['job_id'],
                    origin_airport=a['origin'], destination_airport=a['destination'],
                    departure_utc=a['departure_utc'], arrival_utc=(datetime.fromisoformat(a['departure_utc'])+timedelta(hours=h)).isoformat(),
                    saleable_seats=float(a['seats']), block_hours_costscreen=h, calendar_kind=a['kind'], tail_id=a['tail']))
            world = {tuple(x.split('>')) for x in coverage['worlds'][r['cohort_key']]}
            bundle = api.choice_bundle(fs, sc, world, '2027-02-01', '2027-02-28')
            assert all(len(p['legs']) == 1 for p in bundle['products'] if p['owner'] == 'RW')
            allocation = api.allocate_p06(bundle, bundle['products'])
            pp = {p['product_id']: p for p in bundle['products']}
            rr = sum(a['carried']*pp[a['product_id']]['net_fare'] for a in allocation['allocations'] if a['owner'] == 'RW')
            direct[state] = D(str(rr))-cost
            if state == 'REPLACE':
                new_ids = {f['flight_instance_id'] for f in fs if f['pattern_id'].startswith('NEW-')}
                new_sales = [a for a in allocation['allocations'] if a['owner'] == 'RW' and pp[a['product_id']]['legs'][0] in new_ids]
                direct_q = sum(a['carried'] for a in new_sales)
                newrev = sum(a['carried']*pp[a['product_id']]['net_fare'] for a in new_sales)
                assert len(new_ids) == 8 and direct_q <= 800+1e-8
                assert all(a['carried'] <= 100+1e-8 for a in new_sales)
        keep_old = {a['flight_id']: a for a in ls_by_state['KEEP']}
        add_old = {a['flight_id']: a for a in ls_by_state['REPLACE'] if not a['job_id'].startswith('NEW-')}
        assert set(keep_old) == set(add_old)
        for fid in keep_old:
            assert all(keep_old[fid][k] == add_old[fid][k] for k in ('job_id', 'tail', 'origin', 'destination', 'departure_utc', 'avoidable_variable_scenario'))
        direct_delta = direct['REPLACE']-direct['KEEP']
        main_delta = bystate['REPLACE']-bystate['KEEP']
        for case, values in [('MAIN', bystate), ('DIRECT_ONLY_NO_CONDITIONAL_THROUGHS', direct)]:
            expected = next(x for x in sensitivity if x['candidate_id'] == 'X_SVX_KJA' and x['scenario'] == sc and x['case'] == case)
            for state in values:
                assert abs(values[state]-D(expected[state])) < D('.02')
        result[sc] = dict(direct_only_delta_month=direct_delta, main_including_conditional_through_delta_month=main_delta,
                         direct_only_states=direct, main_states=bystate, new_direct_tickets_month_scenario=direct_q,
                         new_direct_tickets_per_direction_per_departure_scenario=direct_q/8,
                         new_direct_revenue_month_scenario=newrev,
                         retained_direct_revenue_change=direct_delta-(D(str(newrev))-8*cost_components(sc)['cost_rub']),
                         same_old_flight_ids=len(keep_old), through_in_primary_threshold=False)
    # Focused circular boundary only; no delay grid.
    w = [r for r in weekly if r['candidate_id'] == 'X_SVX_KJA' and r['state'] == 'REPLACE' and r['tail'] == 'T2' and r['flight_id']]
    outbound = next(r for r in w if r['flight_id'] == 'NEW-ISO1/L1/W1')
    inbound = next(r for r in w if r['flight_id'] == 'NEW-ISO1/L2/W1')
    prev = next(r for r in w if r['flight_id'] == 'OWN-WZ-1033-ISO7/L2/W1')
    nxt = next(r for r in w if r['flight_id'] == 'OWN-WZ-1033-ISO2/L1/W1')
    previous_arrival = datetime.fromisoformat(prev['arrival_local'])-timedelta(days=7)
    gap_before = int((datetime.fromisoformat(outbound['departure_local'])-previous_arrival).total_seconds()/60)
    gap_after = int((datetime.fromisoformat(nxt['departure_utc'])-datetime.fromisoformat(inbound['arrival_utc'])).total_seconds()/60)
    assert (gap_before, gap_after) == (170, 1985)
    assert all(int(r['block_minutes']) == 200 for r in (outbound, inbound))
    return result, dict(preceding_arrival_local=previous_arrival.isoformat(), new_outbound_local=outbound['departure_local'],
                        new_return_arrival_local=inbound['arrival_local'], next_old_departure_local=nxt['departure_local'],
                        prior_ground_minutes=gap_before, prior_slack_after_turn60=gap_before-60,
                        next_ground_minutes=gap_after, next_slack_after_turn60=gap_after-60,
                        aircraft_turn60_scenario=True, actual_crew_rest_reserve_slot_release=None)


QUOTE_FIELDS = ['quote_id', 'date', 'travel_date', 'direction', 'flight', 'carrier', 'baggage',
                'baggage_kg', 'hand_baggage_included', 'mandatory_fees_included', 'adults', 'cabin',
                'currency', 'allin_price', 'net_yield_if_verified', 'net_verification_basis', 'status', 'source']


def confirmed_quotes(data):
    accepted, rejected = [], []
    for i, r in enumerate(data, 2):
        if r.get('status') != 'VERIFIED':
            rejected.append({'row': i, 'reason': 'status is not VERIFIED'})
            continue
        try:
            assert all(r.get(k) for k in ('quote_id', 'date', 'travel_date', 'flight', 'carrier', 'baggage', 'source'))
            date.fromisoformat(r['date']); date.fromisoformat(r['travel_date'])
            assert r['direction'] in ('out', 'back') and r['currency'] == 'RUB'
            assert r['adults'] == '1' and r['cabin'].lower() == 'economy' and D(r['baggage_kg']) >= 20
            assert r['hand_baggage_included'].lower() == r['mandatory_fees_included'].lower() == 'true'
            gross = D(r['allin_price']); assert gross.is_finite() and gross > 0
            val = r.get('net_yield_if_verified', '')
            net = None if val in ('', 'NULL', 'UNKNOWN') else D(val)
            assert net is None or (net.is_finite() and 0 < net <= gross and r.get('net_verification_basis'))
        except (AssertionError, KeyError, ValueError, ArithmeticError) as e:
            raise ValueError(f'Malformed VERIFIED quote at CSV row {i}') from e
        accepted.append(dict(r, gross=gross, net=net))
    if len({r['quote_id'] for r in accepted}) != len(accepted):
        raise ValueError('Duplicate VERIFIED quote_id')
    return accepted, rejected


def choose_yields(args, sc, quotes):
    values, bases = [], []
    for direction in ('out', 'back'):
        explicit = getattr(args, 'net_'+direction)
        quote_id = getattr(args, 'quote_'+direction+'_id')
        candidates = [q for q in quotes if q['direction'] == direction and (not quote_id or q['quote_id'] == quote_id)]
        if quote_id and not candidates:
            raise ValueError(f'No VERIFIED {direction} quote with selected id')
        if len(candidates) > 1:
            raise ValueError(f'Ambiguous {direction} quotes: select --quote-{direction}-id')
        if explicit is not None:
            if not args.net_basis:
                raise ValueError('--net-basis required for intentional net override')
            val, basis = explicit, 'EXPLICIT_SCENARIO:'+args.net_basis
        elif candidates and candidates[0]['net'] is not None:
            val, basis = candidates[0]['net'], 'VERIFIED_QUOTE_NET:'+candidates[0]['quote_id']
        elif candidates and args.net_retention_factor is not None:
            if not args.net_retention_basis:
                raise ValueError('--net-retention-basis required; this is an intentional scenario, not verified net')
            val = candidates[0]['gross']*args.net_retention_factor
            basis = 'RETAIL_TIMES_EXPLICIT_FACTOR_SCENARIO:'+args.net_retention_basis
        else:
            val, basis = NET[sc], 'P36_NET_SCENARIO_NOT_ACTUAL'
        if not val.is_finite() or val <= 0:
            raise ValueError('Net must be finite and positive')
        values.append(val); bases.append(basis)
    return values, bases


def coefficients(args, rates):
    """L = transfers*oldnet - recapture - saved_old_pax_variable, once."""
    ro, rb = rates
    share = args.cannib_share
    oldo = args.old_net_out if args.old_net_out is not None else ro
    oldb = args.old_net_back if args.old_net_back is not None else rb
    if args.lost_rw_contribution_rub is not None:
        if share or args.cannib_out or args.cannib_back or args.recapture_rub or args.saved_old_pax_variable_rub:
            raise ValueError('Use either total lost RW contribution OR explicit cannibalization, never both')
        loss = args.lost_rw_contribution_rub
    else:
        if share and (args.cannib_out or args.cannib_back):
            raise ValueError('Use either proportional stress OR fixed transferred counts')
        loss = D(args.cannib_out)*oldo+D(args.cannib_back)*oldb-args.recapture_rub-args.saved_old_pax_variable_rub
    return (ro-args.pax_variable_out-share*oldo, rb-args.pax_variable_back-share*oldb), loss, (oldo, oldb)


def parameters(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--quotes', type=Path)
    for x in ('out', 'back'):
        p.add_argument('--quote-'+x+'-id')
        p.add_argument('--net-'+x, type=D)
        p.add_argument('--old-net-'+x, type=D)
        p.add_argument('--pax-variable-'+x, type=D, default=ZERO, help='RUB per new-flight direct ticket; default conditional bound only')
        p.add_argument('--cannib-'+x, type=int, default=0, help='Transferred tickets per rotation, not new-to-RW demand')
    p.add_argument('--net-basis')
    p.add_argument('--net-retention-factor', type=D)
    p.add_argument('--net-retention-basis')
    p.add_argument('--cannib-share', type=D, default=ZERO, help='Proportional stress only, not observed share')
    for name in ('oneoff-f-rub', 'recurring-f-rub-per-roundtrip', 'd-rub-per-roundtrip', 'recapture-rub', 'saved-old-pax-variable-rub'):
        p.add_argument('--'+name, type=D, default=ZERO)
    p.add_argument('--lost-rw-contribution-rub', type=D, help='Alternative loss per rotation; no joint-loss deduction again')
    args = p.parse_args(argv)
    for k, v in vars(args).items():
        if isinstance(v, Decimal) and (not v.is_finite() or v < 0):
            p.error(k+' must be finite and nonnegative')
    if not 0 <= args.cannib_share <= 1:
        p.error('cannib-share must be in 0..1')
    if not all(0 <= getattr(args, 'cannib_'+x) <= 100 for x in ('out', 'back')):
        p.error('fixed transferred tickets must be in 0..100 per direction per rotation')
    if args.net_retention_factor is not None and not 0 < args.net_retention_factor <= 1:
        p.error('net-retention-factor must be in (0,1]')
    return args


def calculations(args, quotes):
    costs, be, frontier = [], [], []
    for sc in NET:
        cc = cost_components(sc); C = cc['cost_rub']*2
        (ro, rb), bases = choose_yields(args, sc, quotes)
        (eo, eb), loss = coefficients(args, (ro, rb))[:2]
        if min(eo, eb) <= 0:
            raise ValueError('Nonpositive ticket contribution after stress: use smaller stress or confirmed new inputs')
        for direction in ('out', 'back', 'ROUNDTRIP', 'FEB4'):
            mult = 1 if direction in ('out', 'back') else 2 if direction == 'ROUNDTRIP' else 8
            costs.append(dict(scenario=sc, direction=direction, physical_legs=mult,
                origin='SVX' if direction == 'out' else 'KJA' if direction == 'back' else 'SVX-KJA-SVX',
                destination='KJA' if direction == 'out' else 'SVX',
                **{k: v*mult if k != 'landed_fuel_rub_t' else v for k, v in cc.items()},
                fuel_price_before_uplift_rub_t=136300 if sc == 'base' else 160000,
                uplift_rub_t_already_in_landed=1696, uplift_added_again_rub=0,
                uplift_basis='P36 landed once; CAUT 161696=160000+1696 scenario decomposition, not actual invoice',
                fixed_crew_avoided_rub=0, lease_avoided_rub=0,
                actual_fuel_cost=None, actual_avoidable_cost=None, actual_pax_cost=None,
                status='P36_COST_SCENARIO_NOT_VERIFIED_INVOICE'))
        for hname, turns, repeated in [('ONE_ROTATION', 1, True), ('FEB4_REPEAT_SAME_INTEGER_SALES', 4, True), ('FEB4_POOLED_INTEGER_SALES', 4, False)]:
            # Repeated q counts per flight. Pooled n counts per direction/month.
            scale = turns if repeated else 1
            cap = 100 if repeated else 400
            fixed = turns*(C+loss+args.recurring_f_rub_per_roundtrip+args.d_rub_per_roundtrip)+args.oneoff_f_rub
            rate_o, rate_b = scale*eo, scale*eb
            balanced = max(args.cannib_out if repeated else turns*args.cannib_out,
                           args.cannib_back if repeated else turns*args.cannib_back,
                           min_strict(fixed, rate_o+rate_b))
            common = dict(scenario=sc, horizon=hname, rotations=turns, reference='KEEP_EQUALS_WITHOUT_NEW',
                net_out=ro, net_back=rb, net_out_basis=bases[0], net_back_basis=bases[1],
                ticket_basis='tickets_per_direction_per_departure' if repeated else 'tickets_per_direction_month',
                cap_each_direction=cap, through_revenue=0, interline_revenue=0, cargo=0, support=0,
                actual_sales_out=None, actual_sales_back=None, actual_full_profit=None,
                actual_required_unknown_costs=None, zero_deduction_basis='CONDITIONAL_BOUND_NOT_ACTUAL_ZERO',
                oneoff_F_horizon=args.oneoff_f_rub, recurring_F_horizon=turns*args.recurring_f_rub_per_roundtrip,
                D_horizon=turns*args.d_rub_per_roundtrip, fixed_lost_RW_contribution_horizon=turns*loss,
                cannib_share_stress=args.cannib_share)
            def add(kind, **kwargs):
                be.append(dict(common, metric=kind, **kwargs))
            add('balanced_minimum_strict', n_out=balanced, n_back=balanced,
                tickets_each_direction_horizon=scale*balanced, all_new_flight_tickets_horizon=2*scale*balanced,
                transferred_tickets_horizon=(2*scale*balanced*args.cannib_share if args.cannib_share else turns*(args.cannib_out+args.cannib_back)),
                new_to_RW_tickets_horizon=(2*scale*balanced*(1-args.cannib_share) if args.cannib_share else 2*scale*balanced-turns*(args.cannib_out+args.cannib_back)),
                continuous_balanced_equality=fixed/(rate_o+rate_b), feasible=balanced <= cap,
                margin_at_integer=balanced*(rate_o+rate_b)-fixed,
                margin_one_less=(balanced-1)*(rate_o+rate_b)-fixed)
            # qout values are per departure even in monthly pooled frontier.
            for q in (50, 60, 70, 80, 90, 100):
                no = q if repeated else turns*q
                nb = max(args.cannib_back if repeated else turns*args.cannib_back,
                         min_strict(fixed-no*rate_o, rate_b))
                frontier.append(dict(common, n_out=no, equality_n_back=(fixed-no*rate_o)/rate_b,
                    n_back_min_strict=nb, feasible=0 <= no <= cap and nb <= cap and no >= (args.cannib_out if repeated else turns*args.cannib_out),
                    n_out_horizon=no*scale, n_back_horizon=nb*scale,
                    margin_at_integer=no*rate_o+nb*rate_b-fixed,
                    margin_at_one_less_back=None if nb == 0 else no*rate_o+(nb-1)*rate_b-fixed,
                    formula='max(0,floor((fixed_cost - n_out*effective_net_out)/effective_net_back)+1); counts/caps both directions'))
            full_margin = cap*(rate_o+rate_b)-fixed
            add('capacity_ceiling_conditional_subtotal', n_out=cap, n_back=cap, rub=full_margin,
                revenue_ceiling_horizon=cap*scale*(ro+rb), feasible=full_margin > 0,
                meaning='remaining combined F/D/lost-contribution capacity; not three separate budgets')
            for perflight in (80, 90, 100):
                n = perflight if repeated else turns*perflight
                head = n*(rate_o+rate_b)-fixed
                add('combined_additional_F_D_loss_equality_budget', n_out=n, n_back=n, rub=head,
                    strict_rule='additional total deduction must be STRICTLY LESS than rub; negative means already loss')
                # Common net needed; explicit fixed loss held, proportional oldnet
                # held at the input oldnet, not automatically scaled with new price.
                oldo, oldb = coefficients(args, (ro, rb))[2]
                needed = (fixed+n*scale*(args.pax_variable_out+args.pax_variable_back+args.cannib_share*(oldo+oldb)))/(2*n*scale)
                add('equal_direction_net_BE', n_out=n, n_back=n, rub_per_direct_ticket=needed,
                    strict_rule='common verified/scenario net must be greater than equality; demand remains unknown')
                for oldnet_label, oldnet in [('equal_to_out_net', ro), ('equal_to_back_net', rb)]:
                    maxk = int((head/oldnet).to_integral_value(rounding=ROUND_CEILING))-1
                    add('max_transferred_tickets_strict_before_other_losses', n_out=n, n_back=n,
                        old_net_basis=oldnet_label, old_net_stress_rub=oldnet,
                        max_transferred_tickets_horizon=min(2*n*scale, maxk) if maxk >= 0 else None,
                        feasible=maxk >= 0,
                        stress_basis='remaining budget/old net; recapture=saved=0; total across both directions, not actual transfers')
            for stress_share in (D('0'), D('.10'), D('.25')):
                # Deliberate severe stress oldnet=newnet, no recapture/saved cost.
                stress_rate = scale*(ro+rb)*(1-stress_share)
                z = min_strict(turns*C, stress_rate)
                add('cannibalization_stress_equal_old_new_net', stress_share=stress_share,
                    stress_basis='not observed; old net equals new net; recapture/saved pax cost=0; isolated baseline without other deductions',
                    n_out=z, n_back=z, feasible=z <= cap, rub=cap*stress_rate-turns*C,
                    all_new_flight_tickets_horizon=2*z*scale,
                    transferred_tickets_horizon=2*z*scale*stress_share,
                    new_to_RW_tickets_horizon=2*z*scale*(1-stress_share))
            for factor in (D('.90'), D('1.10')):
                z = min_strict(turns*C, scale*(ro+rb)*factor)
                add('net_yield_change_inverse_threshold_only', net_multiplier_stress=factor,
                    n_out=z, n_back=z, feasible=z <= cap,
                    stress_basis='net scenario only; recoupled demand NOT estimated; no fixed forecast of 100 sales')
            for label, oneoff, perrt in [('F_ONCE_100K', D(100000), ZERO), ('F_ONCE_500K', D(500000), ZERO),
                                          ('F_ONCE_1M', D(1000000), ZERO), ('D_PER_ROTATION_100K', ZERO, D(100000))]:
                z = min_strict(turns*C+oneoff+turns*perrt, scale*(ro+rb))
                add('isolated_extra_cost_stress', stress_label=label, oneoff_stress_rub=oneoff,
                    per_rotation_stress_rub=perrt, n_out=z, n_back=z, feasible=z <= cap,
                    stress_basis='illustrative inverse stress, not cost estimate; other unknown deductions suppressed')
            # Extra paid tickets to replace a KNOWN residual loss. Formula counts
            # all directions once; placing them remains subject to both caps.
            for knownloss in (D(100000), D(250000), D(500000)):
                deficit = turns*knownloss
                starting = min_strict(turns*C, scale*(ro+rb))
                margin_before = starting*scale*(ro+rb)-turns*C
                per_direction_extra = min_strict(deficit-margin_before, scale*(ro+rb))
                # General maximum-yield-first minimum total ticket placement.
                seats_left = max(0, 100*turns-starting*scale)
                extra_out, extra_back, total_feasible = extra_plan(deficit-margin_before, ro, rb, seats_left, seats_left)
                add('extra_tickets_for_known_loss', lost_contribution_per_rotation_rub=knownloss,
                    starting_n_out=starting, starting_n_back=starting,
                    additional_balanced_n_each=per_direction_extra,
                    additional_tickets_each_direction_horizon=scale*per_direction_extra,
                    additional_out_tickets_horizon_min=extra_out, additional_back_tickets_horizon_min=extra_back,
                    additional_total_horizon_min=extra_out+extra_back,
                    feasible=starting <= cap and starting+per_direction_extra <= cap,
                    minimum_total_feasible=starting <= cap and total_feasible,
                    formula='floor((known_loss_horizon - existing_positive_margin)/marginal_net)+1; allocate remaining seats per direction; no count of unique people')
            add('max_proportional_cannib_share_at_full_capacity_equality', fraction=1-turns*C/(100*turns*(ro+rb)),
                stress_basis='isolated equal old/new net, no recapture or other deductions; strict profit requires share below equality')
        for direction, rr, pv in [('out', ro, args.pax_variable_out), ('back', rb, args.pax_variable_back)]:
            be.append(dict(scenario=sc, horizon='ONE_LEG_OPTIONAL_DIAGNOSTIC', metric='leg_self_cover_strict', direction=direction,
                n=min_strict(cc['cost_rub'], rr-pv), cap_each_direction=100,
                feasible=min_strict(cc['cost_rub'], rr-pv) <= 100,
                meaning='not required for roundtrip profit; cross-subsidy allowed; F/D/lost contribution not assigned to legs',
                actual_full_profit=None))
    for q in quotes:
        if q['net'] is None:
            for sc in NET:
                be.append(dict(scenario=sc, horizon='ONE_LEG_RETAIL_UPPER_BOUND', metric='retail_is_only_net_upper_bound',
                    quote_id=q['quote_id'], direction=q['direction'], gross_allin_rub=q['gross'],
                    verified_net=None, optimistic_tickets_to_cover_own_leg=min_strict(cost_components(sc)['cost_rub'], q['gross']),
                    meaning='Necessary optimistic bound only: net<=retail; no VAT/commission inferred; primary model net unchanged unless explicit retention scenario', actual_full_profit=None))
    return costs, be, frontier


def write_inputs():
    needs = [
        ('q_out_q_back', 'paid direct tickets each dated one-way; no segment/through proxies', 'NULL', 'actual demand and realized net; new-flight tickets differ from new-to-RW journeys'),
        ('retail_net', 'dated one-adult economy >=20kg baggage + hand baggage + mandatory fees; RW retained net/settlement', 'NULL', 'No eligible numeric quote in completed source gate; gross is only upper bound'),
        ('actual_own_inventory', 'all RW nonstop/connecting/interline/contract products, bookings and transferred passengers', 'NULL', 'empty captured inventory is not absence of RW'),
        ('lost_RW_contribution', 'transferred tickets*old net - recapture revenue - saved old pax-variable costs, no duplicated joint loss', 'NULL', 'includes verified own connecting displacement; additional lost contribution can be nonzero'),
        ('D', 'actual displaced other old-job contribution outside selected scenario inventory', 'NULL', 'no selected old job removed/retimed; full occupancy unconfirmed'),
        ('pax_variable', 'uncovered per-ticket costs reconciled to invoices and ground basket', 'NULL', 'P04 500/650 basket not repeated automatically; unknown obligatory expense not actual zero'),
        ('fuel', 'burn, actual uplift quantity, SVX/KJA landed invoice, tankering, tax compatibility', 'NULL', 'scenario burned tonnes*landed once; no separate uplift duplication'),
        ('MRO_nav_ground_deice', 'dated local contracts and marginal avoidability incl minima and tax', 'NULL', 'historical/base scenario not actual airport quote'),
        ('F', 'one-off launch + recurrent station/crew swap/overnight/parking/reserve/other nonoverlapping costs', 'NULL', 'one-off paid once per horizon, not multiplied by4'),
        ('actual_tail_old_programme', 'registration and complete old assignments/MRO/release, before/after February', 'NULL', 'B2 two conditional tails; turn feasibility alone does not release aircraft'),
        ('actualcrew', 'night KUF roster, report/release, legal rest or replacement rested crew and incremental cost', 'NULL', '03:10 arrival ->06:00 new departure is not automatic crew readiness'),
        ('reserve', 'released separate aircraft/crew reserve and cash cost', 'NULL', 'R1_UNRELEASED is not available reserve'),
        ('slot_gate', 'dated SVX06:00/KJA11:20/12:20/SVX13:40 slots and handling gates', 'NULL', 'competitor clocks do not approve our slots'),
        ('block200', 'actual RW variant, route/wind/AFM/payload, block and turn acceptance', 'NULL', '200min each leg retained scenario; competitor185min not transferred'),
        ('price_vs_formula', 'quote missing is an input gap; strict integer formula independently tested', 'NULL', 'inverse threshold is not demand forecast or full profit'),
    ]
    table('actual_inputs_needed.csv', [dict(input=x, evidence_needed=e, actual_value=v, implication=i) for x,e,v,i in needs])
    table('quote_template.csv', [dict(zip(QUOTE_FIELDS, [
        'FILL_OUT', '', '2027-02-01', 'out', '', '', '>=20kg checked + hand baggage', '20', 'true', 'true', '1', 'economy', 'RUB', '', '', '', 'UNVERIFIED_TEMPLATE', ''])),
        dict(zip(QUOTE_FIELDS, ['FILL_BACK', '', '2027-02-01', 'back', '', '', '>=20kg checked + hand baggage', '20', 'true', 'true', '1', 'economy', 'RUB', '', '', '', 'UNVERIFIED_TEMPLATE', '']))])


def readme(be, frontier, replay, window, args, quotes):
    baseline = [r for r in be if r['metric'] == 'balanced_minimum_strict' and r['horizon'] == 'ONE_ROTATION']
    lines = ['# X_SVX_KJA — ADD против KEEP', '',
        'Расчёт выполнен. KEEP = WITHOUT_NEW; ADD сохраняет все выбранные старые задания без снятия/сдвига. '
        'Это обратный порог оплаченных **прямых one-way билетов**, не прогноз спроса. Фактические q1/q2, полная прибыль и обязательные неподтверждённые расходы — NULL. '
        'Through/interline/cargo/support в главном доходе 0. Единственной пары q1/q2 без критерия нет; ниже минимум при равных продажах и направленная граница.', '',
        '|Сценарий, не факт|Net ₽/прямой билет|Расход оборота ₽|Баланс: билетов на каждое плечо, строго >0|Вместимость|',
        '|---|---:|---:|---:|---|']
    for r in baseline:
        sc=r['scenario']
        lines.append(f"|{sc}|{r['net_out']:.7f} / {r['net_back']:.7f}|{cost_components(sc)['cost_rub']*2:,.2f}|{r['n_out']} + {r['n_back']}|{'в пределах 100/плечо' if r['feasible'] else 'НЕВОЗМОЖНО при 100/плечо'}|")
    lines += ['', 'Таблица — условный subtotal при заданных CLI-вычетах. По умолчанию F/D/потери/доп.pax=0 только как верхняя граница при положительных неизвестных расходах, '
        'не фактические нули. Если подтверждённый net меняется, меняется порог; продажи не фиксируются на 100. Seats/LF ограничивают возможность, но не создают спрос.', '',
        '## Формула и единицы', '',
        '`n_out*r_out + n_back*r_back − actual_lost_RW_contribution − additional_variable_pax_cost − launch/overnight/reserve/other F > cost_roundtrip + actual_displaced_other_job_contribution`.', '',
        'Равенство даёт нулевой вклад; строгая прибыль требует floor+1 билета. '
        '`L = k_out*oldnet_out + k_back*oldnet_back − recapture − saved_old_pax_variable`. '
        'k — перешедшие из прежних продуктов RW, а не весь новый рейс. Доп.pax — только неучтённые расходы нового рейса. '
        'Нельзя после L повторно вычитать общий joint loss. `--lost-rw-contribution-rub` альтернативен k/share. '
        'Все рубли номинальные, без выдуманного НДС. Входы L/recapture/saved/D/recurrent F заданы на оборот; oneoff F — один раз на выбранный горизонт.', '',
        'Для месяца: `4*[n_out*r_out+n_back*r_back−L−pax−recurrent F−D−C_RT]−F_once`. '
        'Один оборот — 2 рейса; февраль — 4 оборота, 8 рейсов, максимум 400 билетов/направление, 800 всего. '
        'Один RT-клиент покупает 2 one-way билета; количества здесь не уникальные люди. Тариф не умножается на4 повторно. '
        'FEB4_REPEAT требует одинаковые целые продажи на каждом повторе; FEB4_POOLED разрешает различия между неделями и проверяет месяц целиком, а не прибыль каждого оборота.', '',
        '|Сценарий|Февраль: одинаковое число на каждом вылете, за месяц/направление|Февраль: минимум целых билетов/направление по месяцу|',
        '|---|---:|---:|']
    for sc in NET:
        rr = {r['horizon']: r for r in be if r['scenario']==sc and r['metric']=='balanced_minimum_strict'}
        lines.append(f"|{sc}|{rr['FEB4_REPEAT_SAME_INTEGER_SALES']['tickets_each_direction_horizon']}|{rr['FEB4_POOLED_INTEGER_SALES']['n_out']}|")
    lines += ['', 'Месячный cap400 на направление; варианты сверх cap недостижимы. '
        'Для BASE без дополнительных вычетов месячные274 можно распределить как69/69/68/68 в каждом направлении; '
        'некоторые обороты отдельно могут быть отрицательны при положительном месяце.', '',
        '## Направленный порог', '', '|Сценарий|out 50|60|70|80|90|100|', '|---|---:|---:|---:|---:|---:|---:|']
    for sc in NET:
        ff=[r for r in frontier if r['scenario']==sc and r['horizon']=='ONE_ROTATION']
        lines.append('|'+sc+'|'+'|'.join(str(r['n_back_min_strict'])+(' вне cap' if not r['feasible'] else '') for r in ff)+'|')
    lines += ['', 'В коде `a_out=r_out−pax_variable_out−s*oldnet_out`, аналогично `a_back`; s используется только в пропорциональном стрессе. '
        '`L0=k_out*oldnet_out+k_back*oldnet_back−recapture−saved` — фиксированный вычет; при s>0 фиксированные k запрещены, '
        'и переток учитывается только в a. Альтернативный уже известный L вводится вместо k/s. '
        'Полная формула `qback_min(qout)=max(0,floor((C_RT+L0+F+D−qout*a_out)/a_back)+1)`, '
        'с дополнительным ограничением не меньше числа перешедших билетов. Каждое плечо отдельно ≤100. '
        'directional_frontier.csv содержит также оба месячных критерия. Самоокупаемость каждого плеча — отдельная необязательная диагностика: '
        'оборот допускает перекрёстное покрытие, F/D не приписаны произвольно одному плечу.', '',
        '## Расходы и пределы', '',
        'Местные часы T2: пн SVX06:00→KJA11:20, KJA12:20→SVX13:40; UTC01:00→04:20 и05:20→08:40. '
        'Оба блока 200мин (3:20), turn60. costs.csv раскрывает burn t, landed ₽/t, fuel/MRO/nav/ground/deice на плечо/оборот/4оборота. '
        'BASE на плечо: burn5.3666667t ×137996(136300+1696) +MRO116666.67 +nav20000 +ground96089 +deice15000 =988334.20₽. '
        'CAUT: burn6.5833333t ×161696 +MRO183333.33 +nav26666.67 +ground115307 +deice40000 =1429805.67₽. '
        'Burn не равен фактической заправке. Uplift1696 уже внутри landed, второй раз не начисляется; CAUT разложение160000+1696 — сценарная идентичность. '
        'Избегаемость/налоговый состав MRO/handling/fuel не подтверждены. Fixed crew50000/73333.33₽ на плечо исключены из marginal cost, '
        'фиксированная аренда и зарплата не становятся экономией. Новая смена/командировка экипажа, если обязательна, входит в F. Неучтённый pax basket не добавлен повторно.', '',
        '|Сценарий|80+80: общий запас F+D+L ₽/оборот|90+90|100+100 ceiling|Net BE80|Net BE90|Net BE100|',
        '|---|---:|---:|---:|---:|---:|---:|']
    for sc in NET:
        h=[r for r in be if r['scenario']==sc and r['horizon']=='ONE_ROTATION' and r['metric']=='combined_additional_F_D_loss_equality_budget']
        n=[r for r in be if r['scenario']==sc and r['horizon']=='ONE_ROTATION' and r['metric']=='equal_direction_net_BE']
        lines.append('|'+sc+'|'+'|'.join(f"{r['rub']:,.2f}" for r in h)+'|'+'|'.join(f"{r['rub_per_direct_ticket']:,.2f}" for r in n)+'|')
    lines += ['', 'Для строго положительного вклада сумма новых вычетов должна быть **меньше** запаса. '
        'Отрицательный запас означает убыток уже до них. Это единый бюджет: нельзя отдельно израсходовать его на F, D и cannib. '
        'В break_even.csv численно раскрыты разовые F100/500/1000тыс, D100тыс/оборот, известная потеря100/250/500тыс/оборот и дополнительные билеты с проверкой обоих caps. '
        'Стрессы перетока0/10/25% намеренно охватывают отсутствие и существенное перераспределение; это не оценка доли. '
        'В них oldnet=newnet, recapture/saved=0: потеря каждого перешедшего билета целиком уменьшает вклад. '
        'Фактические oldnet/recapture/saved нужно ввести явно. Суммарные билеты на новом рейсе и новые для RW разведены в колонках.', '',
        '|Изолированный стресс на оборот, остальные вычеты подавлены|BASE минимум/направление|CAUT минимум/направление|',
        '|---|---:|---:|']
    for share in (D('0'),D('.10'),D('.25')):
        rr=[next(r for r in be if r['scenario']==sc and r['horizon']=='ONE_ROTATION' and r['metric']=='cannibalization_stress_equal_old_new_net' and r['stress_share']==share) for sc in NET]
        lines.append(f"|Переток {share:.0%}; oldnet=newnet, без recapture/saved|"+'|'.join(str(r['n_out'])+(' вне cap' if not r['feasible'] else '') for r in rr)+'|')
    for label in ('F_ONCE_100K','F_ONCE_500K','F_ONCE_1M','D_PER_ROTATION_100K'):
        rr=[next(r for r in be if r['scenario']==sc and r['horizon']=='ONE_ROTATION' and r['metric']=='isolated_extra_cost_stress' and r['stress_label']==label) for sc in NET]
        lines.append('|'+label+'|'+'|'.join(str(r['n_out'])+(' вне cap' if not r['feasible'] else '') for r in rr)+'|')
    lines += ['', 'При исходном BASE и отсутствии прочих вычетов предельная доля перетока при100+100 —31.5449% '
        '(строго ниже; oldnet=newnet, без recapture/saved). F1млн один раз за февраль требует BASE78/вылет при повторении '
        'или309/направление при месячном критерии; это стресс, не оценка стоимости запуска. '
        'Из начальных69+69 при известных потерях100/250/500тыс₽ за оборот минимально нужно ещё6/17/34 билета суммарно; '
        'при требовании равных продаж — ещё3/9/17 на каждое плечо. Эти примеры относятся к исходным net P36, '
        'не к неподтверждённой цене и не к наблюдаемому спросу. Самоокупаемость отдельного плеча при исходных net требует BASE69, '
        'CAUT115 (вне100) билетов; это необязательный диагностический критерий. '
        'Таблицы CSV пересчитывают все пороги по новым CLI-входам.', '',
        '## Воспроизведение P36', '',
        'Старые builders/verify не запускались. Прочитаны TASK, P36 calculate/README/review, directional и revenue ledgers, sensitivity, weekly schedule. '
        'Чистые P31 choice_bundle + P06 allocate заново распределили прямые продукты KEEP/ADD в каждом сценарии. '
        'MAIN с through восстановлен из суммы directional net revenue и физического cost ledger с учётом equivalence_map. Все старые flight IDs/тайминг/cost сохранены.', '',
        '|Сценарий|DIRECT_ONLY ADD−KEEP ₽/февраль|P36 MAIN с условным through, только сверка ₽|', '|---|---:|---:|']
    for sc, v in replay.items():
        lines.append(f"|{sc}|{v['direct_only_delta_month']:,.7f}|{v['main_including_conditional_through_delta_month']:,.7f}|")
    lines += ['', 'Эти прежние модельные продажи не являются текущим спросом: прямой replay даёт BASE94.8594810 и CAUT44.7192456 билета/направление/вылет. '
        'В MAIN на outbound есть retained through-эффекты; сегментных пассажиров нельзя умножать на прямой yield. Главный обратный порог использует только прямые билеты. '
        'Сравнитель — этот KEEP, без лучшей AER-программы и без envelope/thresholds.csv P36.', '',
        '## Окно и данные рынка', '',
        f"Предыдущий T2 KUF прилетает в SVX {window['preceding_arrival_local']} (вс→пн). До06:00:170мин ground,110мин сверх turn60. "
        'После возврата пн13:40 до следующего T2 KUF вт22:45:1985мин ground,1925мин сверх turn60. '
        'Это согласованность самолёта в условной недельной ротации, не подтверждение свободного окна. '
        'actualcrew/rest после ночного рейса, reserve, registration/MRO, slots/gates — NULL. Старое задание фактически вне охвата может иметь вклад D; он не известен. Новая delay grid не строилась.', '',
        'Принят завершённый source_resolution координатора (13.11.2026), без нового внешнего поиска: '
        '[официальные вылеты](https://ar-svx.ru/schedule/) / [прилёты](https://ar-svx.ru/schedule/?type=arr). '
        '16–22ноября «Россия» покрывает 7дней в обе стороны; 1–7февраля опубликованные периоды покрывают только вт/сб — это не отсутствие остальных рейсов. '
        'Пн16ноября SVX13:40→KJA18:35, KJA11:30→SVX12:45. Наши часы — сценарий, не выданный слот; convenience/WTP неизвестны. '
        'Own RW nonstop не доказан, вторичный connecting-сигнал требует sales inventory. Численных price/baggage-qualified обновлений нет. '
        'Конкурентный вторничный RRJ185мин не подменяет наш сценарный200мин. Год в первичных строках выводится из зимнего контекста, не напечатан полностью.', '',
        '## Повтор и котировки', '',
        '`context/28_end_to_end_audit_20261110/code/sandbox/venv/bin/python -B context/37_svx_kja_keep_check_20261112/calculation/calculate.py`', '',
        'Затем тем же Python `-B .../calculation/verify.py`. Только эти10 файлов записываются в calculation/. '
        'quote_template.csv — вход-шаблон, не найденная цена. Сохраните заполненную копию как quotes.csv и передайте `--quotes PATH`. '
        'Принимаются только status=VERIFIED, валидные date/travel_date,1adult/economy/RUB,багаж≥20кг,ручная кладь/обязательные сборы,источник. '
        'Для нескольких строк направления обязательны `--quote-out-id`/`--quote-back-id`. '
        'net_yield_if_verified требует явного net_verification_basis; не известен net — retail только верхняя граница, основной net не меняется. '
        'Чужая подтверждённая котировка не доказывает достижимость такого RW net. '
        'Умышленный net/commission сценарий: `--net-retention-factor .90 --net-retention-basis EXPLICIT_ASSUMPTION` либо `--net-out ... --net-back ... --net-basis ...`; '
        'никаких автоматических НДС/комиссии. Смешанные направления/даты раскрыты в manifest, сравнимость не приписывается.', '',
        'Другие входы: `--oneoff-f-rub`, `--recurring-f-rub-per-roundtrip`, `--d-rub-per-roundtrip`, '
        '`--pax-variable-out/back`, `--cannib-out/back`, `--old-net-out/back`, `--recapture-rub`, `--saved-old-pax-variable-rub`, '
        '`--cannib-share` (альтернативный стресс), `--lost-rw-contribution-rub` (альтернатива детализации L). '
        'Если oldnet не передан, используется явный стресс равного новому net, не фактический oldnet. '
        'Отсутствие подтверждённой цены — нехватка входа; формула и integer edge проверяются независимо. actual_inputs_needed.csv перечисляет оставшиеся данные. '
        'source_manifest.json хранит источники и компактные hashes; validation.json — реальный прогон и тесты. STOP.']
    # Avoid a stale validation badge after parameter changes: verifier records output hashes.
    write('README.md', '\n'.join(lines)+'\n')


def main(args=None):
    args = args or parameters()
    before = guard_snapshot()
    for p in (HERE.parent/'TASK.md', HERE.parent/'freeze.json', P/'calculate.py', P/'README.md', P36/'review/README.md'):
        source(p)
    for name in ('calculate.py', 'verify.py'):
        if (HERE/name).exists():
            source(HERE/name)
    gate = HERE.parent/'source_resolution'
    for name in ('README.md', 'coverage.json', 'primary_services.csv', 'actual_requests.json'):
        if (gate/name).exists():
            source(gate/name)
    quotes, rejected = confirmed_quotes(rows(args.quotes)) if args.quotes else ([], [])
    replay, window = reproduce()
    costs, be, frontier = calculations(args, quotes)
    table('costs.csv', costs); table('break_even.csv', be); table('directional_frontier.csv', frontier)
    write_inputs(); readme(be, frontier, replay, window, args, quotes)
    after = guard_snapshot()
    assert before == after, 'PROTECTED/P36 CHANGED DURING RUN'
    manifest = dict(case='X_SVX_KJA', reference='KEEP_EQUALS_WITHOUT_NEW', output_directory=str(HERE.relative_to(ROOT)),
        bytecode_disabled=sys.dont_write_bytecode, pure_API_calls={'choice_bundle': 4, 'P06.allocate': 4},
        old_builders_or_verifiers_run=False, new_external_search=False, direct_only_reproduction=replay,
        focused_window=window, guards=before, guards_unchanged_during_calculation=True,
        read_sources=READS, parameters={k: str(v) if isinstance(v, (Path, Decimal)) else v for k,v in vars(args).items()},
        verified_quotes=quotes, ignored_unverified_quotes=rejected,
        price_input_status='VERIFIED_ROWS_PROVIDED' if quotes else 'NO_BAGGAGE_QUALIFIED_NUMERIC_QUOTE',
        actual_full_profit=None, actual_sales=None,
        default_zero_unknowns='CONDITIONAL_BOUND_ONLY_NOT_ACTUAL',
        cannib_oldnet_default='equal new net stress, not observed; set explicit old-net inputs',
        output_hashes={n: sha(HERE/n) for n in ('costs.csv','break_even.csv','directional_frontier.csv','quote_template.csv','actual_inputs_needed.csv','README.md')})
    dump('source_manifest.json', manifest)
    print('CALCULATED X_SVX_KJA vs KEEP; direct-only replay BASE', replay['base']['direct_only_delta_month'],
          'CAUT', replay['cautious']['direct_only_delta_month'], '; actual profit NULL')
    return manifest


if __name__ == '__main__':
    main()
