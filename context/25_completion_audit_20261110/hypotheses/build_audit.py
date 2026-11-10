"""Independent, offline arithmetic and completion audit. Never executes owner code."""
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_CEILING
import hashlib
import json
import math
import subprocess

from source_access import OUT, REPO, PINS, H, F, R, M, source, rows, obj, evidence, at, dump, write_csv, seal_sources

checks = []


def check(name, condition, scope, detail=None):
    checks.append(dict(check=name, passed=bool(condition), scope=scope, detail=detail))
    if not condition:
        raise AssertionError((name, detail))


def near(a, b, tolerance=0.00001):
    return abs(float(a) - float(b)) <= tolerance


def ref(e):
    return f"{e['commit']}:{e['path']}:{e['line']}"


def main():
    candidates = rows("hypotheses", H + "candidates.csv")
    catalog = obj("hypotheses", H + "inputs/candidate_catalog.json")
    ancestors = rows("hypotheses", H + "existing_hypotheses.csv")
    frontier = rows("frontier", F + "inventory35.csv")
    reviewer_inventory = rows("review", R + "independent_inventory35.csv")
    profiles = json.loads((OUT / "profiles.json").read_text())
    ids = [f"C{i:02d}" for i in range(1, 36)]
    check("35 unique original IDs in exact order", [r['candidate_id'] for r in candidates] == ids,
          "inventory", dict(rows=len(candidates), unique=len({r['candidate_id'] for r in candidates})))
    check("frontier IDs preserve 35", [r['candidate_id'] for r in frontier] == ids, "inventory")
    check("independent review inventory preserves 35", [r['candidate_id'] for r in reviewer_inventory] == ids, "inventory")
    check("35 manual audit profiles", set(profiles) == set(ids), "inventory")
    check("catalog and CSV preserve IDs, titles and original statuses",
          [(r['candidate_id'],r['title'],r['evaluation_status']) for r in catalog['candidates']]
          == [(r['candidate_id'],r['title'],r['evaluation_status']) for r in candidates], "specification consistency")
    check("35 original NOT_EVALUATED", all(r['evaluation_status'] == 'NOT_EVALUATED' for r in candidates), "historical status")
    check("35 original demand/fare/resource UNKNOWN", all(r['demand_status'] == r['net_fare_status'] == r['resource_status'] == 'UNKNOWN' for r in candidates), "historical status")
    selected = [r['candidate_id'] for r in candidates if r['selected_for_deepening'] == 'True']
    check("initial selection has nine mechanisms", selected == ['C01','C02','C07','C10','C14','C17','C21','C27','C31'], "historical selection")
    ancestor_map = {r['id']: (i, r) for i, r in enumerate(ancestors, 2)}
    check("all declared ancestors resolve without Cxx cross-system join",
          all(a in ancestor_map for c in candidates for a in c['ancestor_ids'].split(';')), "namespace")
    runs = [json.loads(x) for x in source('hypotheses', H + 'evaluation_runs.jsonl').splitlines()]
    check("early geometry runs did not reject candidates",
          all(r.get('rejected_candidates') == [] and r.get('economics') == 'NOT_RUN' for r in runs), "early rejection log")

    # Original historical snapshots, not reconstructed reasons.
    snapshot_results = []
    for timestamp in ['20261109T131856Z','20261109T142217Z']:
        path = f'context/16_agent_research/coordinator/{timestamp}/hypotheses/candidates.csv'
        blob = source('base', path)
        equal = blob == source('hypotheses', H + 'candidates.csv')
        check('snapshot candidates equal exact original '+timestamp, equal, 'historical lineage')
        snapshot_results.append(dict(path=path, commit=PINS['base'], sha256=hashlib.sha256(blob.encode()).hexdigest(),
                                     same_as_original_candidates=equal))
    for name in ['manifest.json']:
        path = 'context/16_agent_research/coordinator/20261109T154615Z/hypotheses/cost_resource/6cf441ef38e2c6c5/' + name
        # The coordinator saved a manifest, not every money CSV. Read the full tree at6ed for the rows.
        blob = source('base', path)
        equal = blob == source('hypotheses', H + 'experiment_v1/cost_resource/6cf441ef38e2c6c5/' + name)
        check('coordinator cost manifest equals exact hypotheses '+name, equal, 'historical lineage; not a complete local CSV snapshot')
        snapshot_results.append(dict(path=path, commit=PINS['base'], sha256=hashlib.sha256(blob.encode()).hexdigest(),
                                     same_as_original_candidates=None, same_as_original_cost_resource=equal))
    dump('historical_snapshot_checks.json', snapshot_results)

    # Recompute every chord from coordinates, independently of author collectors.
    legs = rows('hypotheses', H + 'normalized/geometry_legs.csv')
    paths = rows('hypotheses', H + 'normalized/geometry_paths.csv')
    screens = rows('hypotheses', H + 'normalized/geometry_screen_sensitivity.csv')
    airport_rows = rows('hypotheses', H + 'normalized/airports_ru.csv')
    used_codes = {r[k] for r in legs for k in ['origin','destination']}
    airport_map = {}
    for r in airport_rows:
        code = r['iata_code']
        if code in used_codes:
            check('unambiguous frozen coordinate '+code, code not in airport_map, 'geometry coordinates')
            airport_map[code] = (float(r['latitude_deg']), float(r['longitude_deg']))
    check('50 original example airports available', set(airport_map) == used_codes and len(used_codes) == 50, 'geometry')

    def distance(a, b):
        la, lo = map(math.radians, airport_map[a]); lb, lob = map(math.radians, airport_map[b])
        x = math.sin((lb-la)/2)**2 + math.cos(la)*math.cos(lb)*math.sin((lob-lo)/2)**2
        return 2*6371.0088*math.asin(math.sqrt(min(1, x)))

    by_candidate = defaultdict(list)
    by_path = defaultdict(list)
    max_error = 0
    for i, leg in enumerate(legs, 2):
        expected = distance(leg['origin'], leg['destination'])
        max_error = max(max_error, abs(expected-float(leg['distance_km'])))
        check('geometry leg '+str(i), near(expected, leg['distance_km'], .00051), 'chord only, not dispatch')
        by_candidate[leg['candidate_id']].append(leg)
        by_path[(leg['candidate_id'], leg['path_id'])].append(expected)
    for p in paths:
        values = by_path[(p['candidate_id'],p['path_id'])]
        check('geometry path '+p['candidate_id']+'/'+p['path_id'], near(sum(values),p['total_chord_km'],.00051)
              and near(max(values),p['max_leg_km'],.00051), 'chord only, not dispatch')
    for s in screens:
        values = by_path[(s['candidate_id'],s['path_id'])]
        check('screen '+s['candidate_id']+'/'+s['path_id']+'/'+s['screen_km'],
              (max(values)>float(s['screen_km'])) == (s['any_leg_over_screen']=='True'), 'scenario screen, not rejection')
    check('geometry 144 legs 81 paths 324 screens', (len(legs),len(paths),len(screens)) == (144,81,324), 'geometry')

    # Check all 108 money rows by integer inversion, fare conservation and seat usage.
    money_path = H+'experiment_v1/cost_resource/6cf441ef38e2c6c5/conditional_thresholds_with_product_keys.csv'
    money = rows('hypotheses', money_path)
    money_audit = []
    for i, r in enumerate(money, 2):
        gap = Decimal(r['residual_funding_gap_rub'])
        fare = Decimal(r['net_fare_rub_per_oneway_journey'])
        cost = Decimal(r['variable_cost_rub_per_oneway_journey'])
        q = int((gap/(2*(fare-cost))).to_integral_value(rounding=ROUND_CEILING))
        journeys = 2*q
        boardings = journeys*int(r['legs_per_oneway_journey'])
        contribution = 2*q*(fare-cost)-gap
        ok = (int(r['required_paid_journeys_each_direction']) == q
              and int(r['total_oneway_journeys']) == journeys
              and int(r['physical_boardings']) == boardings
              and Decimal(r['required_ticket_revenue_rub']) == journeys*fare
              and Decimal(r['contribution_at_threshold_rub']) == contribution)
        if q:
            ok &= Decimal(r['contribution_one_customer_below_rub']) == 2*(q-1)*(fare-cost)-gap
            ok &= 2*(q-1)*(fare-cost)-gap < 0 <= contribution
        ok &= r['optimistic_nominal_cap_gate'] == ('WITHIN_NOMINAL_UPPER_BOUND' if q<=100 else 'ABOVE_NOMINAL_UPPER_BOUND')
        check('historical money row '+str(i), ok, 'conditional inverse, no market acceptance')
        money_audit.append(dict(candidate_id=r['candidate'], source_commit=PINS['hypotheses'], source_path=money_path,
                                source_line=i, gap_rub=str(gap), fare_rub=str(fare), journey_cost_rub=str(cost),
                                computed_q_each_direction=q, computed_endpoint_journeys=journeys,
                                computed_boardings=boardings, computed_ticket_revenue_rub=str(journeys*fare),
                                computed_contribution_rub=str(contribution), pass_arithmetic=bool(ok),
                                real_gap_fare_demand_seats='UNKNOWN'))
    check('108 unique money cells,36 per candidate', len(money)==108 and Counter(r['candidate'] for r in money)=={'C01':36,'C07':36,'C14':36}, 'money inventory')
    check('108 unique candidate-gap-fare-variable tuples', len({tuple(r[k] for k in ['candidate','residual_funding_gap_rub','net_fare_rub_per_oneway_journey','variable_cost_rub_per_oneway_journey']) for r in money}) == 108, 'money inventory')
    for run in ['86d92475089a6128','c26661067277af20']:
        rr = rows('hypotheses', H+f'experiment_v1/runs/{run}/conditional_thresholds.csv')
        check('preserved earlier money grid '+run, len(rr)==108 and all(all(a[k]==b[k] for k in a) for a,b in zip(rr,money)), 'versions, not additional independent observations')
    write_csv('money_recalculation.csv', money_audit)
    tariffs_path = H+'experiment_v1/cost_resource/6cf441ef38e2c6c5/published_tariff_references.csv'
    tariffs = rows('hypotheses', tariffs_path)
    coefficients = rows('hypotheses', H+'experiment_v1/cost_resource/6cf441ef38e2c6c5/conditional_tariff_coefficients.csv')
    for name in ['conditional_tariff_coefficients.csv','matched_resource_deltas.csv','residual_gap_accounting.csv',
                 'movement_count_deltas.csv','published_tariff_references.csv']:
        check('earlier cost-resource preserved '+name,
              source('hypotheses',H+'experiment_v1/cost_resource/8762cfe3b8961b31/'+name)
              == source('hypotheses',H+'experiment_v1/cost_resource/6cf441ef38e2c6c5/'+name),
              'historical version identity, not additional independent data')
    for c in coefficients:
        vals = [Decimal(r['value']) for r in tariffs if r['airport_iata']==c['airport'] and r['item'] in ['takeoff_landing','transport_security']]
        check('published coefficient sum '+c['airport'], sum(vals)==Decimal(c['reference_coefficient']), 'conditional rate only, not invoice')
    residual = rows('hypotheses', H+'experiment_v1/cost_resource/6cf441ef38e2c6c5/residual_gap_accounting.csv')
    resources = rows('hypotheses', H+'experiment_v1/cost_resource/6cf441ef38e2c6c5/matched_resource_deltas.csv')
    fixtures = rows('frontier', F+'runs/economics/capacity_conditioned_thresholds.csv')
    for i,r in enumerate(fixtures,2):
        margin = int(r['net_fare_per_endpoint_journey'])-int(r['journey_expense'])
        q = math.ceil(int(r['assumed_K_fixed_rub'])/(2*margin))
        seats = int(r['nominal_seats_each_leg'])-int(r['local_sales_each_used_leg'])
        check('frontier money fixture '+str(i), q==int(r['required_q_each_direction']) and seats==int(r['residual_each_leg'])
              and int(r['maximum_new_contribution_with_locals_preserved_rub'])==2*seats*margin
              and (q<=seats)==(r['capacity_gate']=='PASS_FIXTURE_ONLY'), 'mechanical fixture, not realized money')
    terms = rows('frontier', F+'runs/economics/monetary_difference_terms.csv')
    check('18 actual money terms remain null', len(terms)==18 and all(not r['value_rub'] and not r['full_money_delta_rub'] for r in terms), 'unknown ledger')

    # Independent frontier clock inequalities. No use of owner/reviewer executable code.
    boundaries = rows('frontier', F+'runs/hf01/retiming_boundaries.csv')
    boundary_map = {}
    for r in boundaries:
        m,t = int(r['connection_min_minutes']),int(r['turn_min_minutes'])
        pairs = [(x,y) for x in range(241) for y in range(196) if m<=x-60<=180 and m<=195-y<=180 and 45+y-x>=t]
        ok = bool(pairs)==(r['feasible']=='True') == (2*m+t<=180)
        if pairs:
            ok &= near(min(x for x,y in pairs),r['south_departure_shift_min_minutes'])
            ok &= near(max(x for x,y in pairs),r['south_departure_shift_max_minutes'])
            ok &= near(min(y for x,y in pairs),r['south_return_shift_min_minutes'])
            ok &= near(max(y for x,y in pairs),r['south_return_shift_max_minutes'])
        check('C01 joint clock region '+r['scenario_id'],ok,'frozen hypothetical flights')
        boundary_map[r['scenario_id']] = (bool(pairs),min((y for x,y in pairs),default=None))
    for i,r in enumerate(rows('frontier',F+'runs/hf01/return_deadlines.csv'),2):
        feasible,ymin = boundary_map[r['scenario_id']]
        expected = feasible and ymin<=int(r['allowed_return_slip_minutes'])
        check('C01 deadline '+str(i),expected==(r['gate']=='FEASIBLE_SCENARIO_TIMES'),'frozen hypothetical flights')
    programs = obj('hypotheses',H+'experiment_v1/scenario_programs.json')
    # Frozen C01 operating dates are explicit in the scenario program.
    check('C01 six declared operating dates', '2026-12-07' in json.dumps(programs) and '2026-12-25' in json.dumps(programs), 'scenario calendar')
    operation_dates = {date(2026,12,d) for d in [7,11,14,18,21,25]}
    c01_products = rows('frontier',F+'runs/hf01/dated_products.csv')
    product_counts = Counter()
    for i,r in enumerate(c01_products,2):
        checkout = date.fromisoformat(r['departure_date'])+timedelta(days=int(r['hotel_nights']))
        feasible,_ = boundary_map[r['scenario_id']]
        expected = feasible and checkout in operation_dates
        check('C01 product date '+str(i), checkout.isoformat()==r['booked_checkout_date'] and expected==(r['gate']=='DATE_AND_CLOCK_SCENARIO_PASS'),'hypothetical dates, not sold trips')
        product_counts[r['scenario_id']] += expected
    check('C01 5/6 or0/6 in all nine profiles', all(v==(5 if boundary_map[k][0] else 0) for k,v in product_counts.items()), 'scenario product count')
    advance = rows('frontier',F+'runs/hf07/return_advance_boundaries.csv')
    advance_map = {}
    for i,r in enumerate(advance,2):
        t,l = int(r['turn_minutes']),int(r['net_arrival_deadline_slack_minutes'])
        delta=220+3*t; needed=max(0,delta-l)
        dep=datetime.fromisoformat(r['reference_departure_svx_local'])-timedelta(minutes=needed)
        ret=dep+timedelta(minutes=475+3*t)
        ok=(near(475+3*t,r['chain_elapsed_minutes']) and near(delta,r['delta_elapsed_minutes'])
            and near(needed,r['required_departure_advance_minutes'])
            and dep.isoformat()==r['departure_svx_local_at_minimum_advance']
            and ret.isoformat()==r['candidate_return_svx_local'])
        check('C07 clock boundary '+str(i),ok,'other-carrier clock proxy, not RW operation')
        advance_map[r['scenario_id']]=needed
    for i,r in enumerate(rows('frontier',F+'runs/hf07/advance_limits.csv'),2):
        check('C07 allowance '+str(i), (int(r['advance_allowance_minutes'])>=advance_map[r['scenario_id']])==(r['gate']=='PASS_SCENARIO_RETURN_LIMIT'),'scenario limit')

    flights = rows('hypotheses',H+'experiment_v1/inputs/alternative_fa39de4/normalized/dated_flights.csv')
    returns = sorted((date.fromisoformat(r['departure_local_date']),r['instance_id']) for r in flights if r['origin_iata']=='MRV' and r['destination_iata']=='KVX')
    flight_map = {r['instance_id']:r for r in flights}
    calendar = rows('hypotheses',H+'experiment_v1/c14_products/3906edd033f75bc6/flight_hotel_calendar.csv')
    calendar_expected = {}
    for i,r in enumerate(calendar,2):
        flight=flight_map[r['outbound_instance_id']]
        checkin=date.fromisoformat(flight['departure_local_date'] if r['stay_basis'].startswith('BOOK_DEPARTURE') else flight['arrival_local_date'])
        checkout=checkin+timedelta(days=int(r['hotel_nights']))
        later=next(((d,k) for d,k in returns if d>=checkout),None)
        exact=next((k for d,k in returns if d==checkout),'')
        check('C14 original calendar '+str(i),checkin.isoformat()==r['booked_checkin_local_date'] and checkout.isoformat()==r['booked_checkout_local_date'] and exact==r['return_instance_id'],'incumbent advertised calendar, not bookability')
        calendar_expected[r['product_request_id']] = (checkout,later)
    flex = rows('frontier',F+'runs/hf14/bookability_tolerance.csv')
    flex_counts = defaultdict(set)
    flex_property_counts = Counter()
    for i,r in enumerate(flex,2):
        checkout,later = calendar_expected[r['product_request_id']]
        needed = (later[0]-checkout).days if later else None
        tolerance=int(r['max_additional_booked_nights'])
        expected=needed is not None and needed<=tolerance
        check('C14 flexibility '+str(i), (r['minimum_additional_booked_nights']==str(needed) if needed is not None else not r['minimum_additional_booked_nights'])
              and expected==(r['date_gate']=='DATE_MATCH_ONLY'),'dates only, not people or demand')
        if expected:
            flex_counts[tolerance].add(r['date_stay_combination_id'])
            flex_property_counts[tolerance]+=1
    check('C14 distinct counts6/7/9/11', [len(flex_counts[i]) for i in range(4)]==[6,7,9,11], 'calendar union')
    check('C14 property counts12/14/18/22', [flex_property_counts[i] for i in range(4)]==[12,14,18,22], 'calendar alternatives')

    # Read and reconcile actual historic money rows outside frontier.
    economics_path = 'context/21_visual_explainer_draft_20261110/inputs/economics.csv'
    breakeven_path = 'context/21_visual_explainer_draft_20261110/inputs/breakeven.csv'
    economics = rows('base', economics_path)
    upstream_economics = rows('economics21','context/21_team_proposals/comparison.csv')
    be = rows('base', breakeven_path)
    check('context21 economics exact upstream bytes',source('base',economics_path)==source('economics21','context/21_team_proposals/comparison.csv'),'lineage')
    check('context21 breakeven exact upstream bytes',source('base',breakeven_path)==source('economics21','context/18_unit_economics_audit/breakeven.csv'),'lineage')
    route_ledger = rows('economics21','context/18_unit_economics_audit/route_ledger.csv')
    route_map = {(r['route'],r['scenario']):r for r in route_ledger}
    legacy_audit = []
    for i,r in enumerate(economics,2):
        inc = float(r['gross_revenue'])-float(r['foregone_RW_revenue'])
        costs = float(r['flight_variable_cost'])+float(r['new_pax_variable'])-float(r['saved_old_pax_variable'])
        contribution=inc-costs
        check('context21 money row '+str(i), near(inc,r['incremental_revenue']) and near(costs,r['incremental_operating_cost']) and near(contribution,r['contribution_before_base_fleet_opportunity']),'aggregate reconciliation, not full model replay')
        legacy_audit.append(dict(namespace='context21_network',id=r['network'],scenario=r['scenario'],source_commit=PINS['base'],source_path=economics_path,source_line=i,
                                 recomputed_contribution_rub=contribution,period='2026-12-07/2026-12-13; RUB/week',scope='before base/fleet/opportunity; conditional additional flights',personal_check='gross-foregone-flight-pax+saved only'))
    be_audit=[]
    for i,r in enumerate(be,2):
        ledger=route_map[(r['route'],r['scenario'])]
        f=int(r['frequency_per_direction']);margin=float(r['unit_incremental_margin_current_yield']);burden=float(r['weekly_extra_burden'])
        cost=float(ledger['flight_variable_cost'])+burden
        threshold=cost/(2*f*margin);at100=2*f*100*margin-cost
        ok=near(threshold,r['linear_paid_threshold_NOT_capacity_forecast']) and near(at100,r['contribution_at100_and_current_fare'])
        ok &= (threshold<=100)==(r['within_nominal100']=='True')
        ok &= near(float(ledger['contribution_before_base_fleet_opportunity']),2*f*float(r['paid_now_per_departure'])*margin-float(ledger['flight_variable_cost']))
        check('context21 break-even row '+str(i),ok,'fixed flight costs/margin from separate ledger; dispatch and demand unknown')
        be_audit.append(dict(route=r['route'],scenario=r['scenario'],source_commit=PINS['base'],source_path=breakeven_path,source_line=i,
                             weekly_extra_burden=burden,computed_threshold=threshold,computed_at100_rub=at100,within_nominal100=threshold<=100,pass_arithmetic=bool(ok)))
    write_csv('breakeven_recalculation.csv',be_audit)
    old_comp_path=H+'inputs/conditional/context/16_conditional_decision/model/comparison.csv'
    old_comparison=rows('hypotheses',old_comp_path)
    for i,r in enumerate(old_comparison,2):
        contribution=float(r['gross_revenue'])-float(r['foregone_RW_revenue'])-float(r['flight_variable_cost'])-float(r['new_pax_variable'])+float(r['saved_old_pax_variable'])
        check('stage16 historical aggregate row '+str(i),near(contribution,r['contribution_before_base_fleet_opportunity']),'aggregate arithmetic; old range screen not current dispatch rule')
        legacy_audit.append(dict(namespace='stage16_network',id=r['network'],scenario=r['scenario'],source_commit=PINS['hypotheses'],source_path=old_comp_path,source_line=i,
                                 recomputed_contribution_rub=contribution,period=r['period'],scope='historical bf564c7; different universe, before base/fleet/opportunity',personal_check='aggregate ledger only'))
    write_csv('historical_economics.csv',legacy_audit)
    pilot=rows('hypotheses',H+'inputs/conditional/context/16_conditional_decision/model/pilot_booking_gate.csv')
    reproduced=rows('hypotheses',H+'normalized/reproduced_thresholds.csv')
    for i,(r,p) in enumerate(zip(pilot,reproduced),2):
        cost=float(r['flight_cost']);margin=float(r['net_new_margin_per_booked'])
        check('stage16 pilot inverse '+str(i),
              near(cost/margin,r['required_paid_pax_before_fixed'])
              and math.ceil(cost/margin)==int(p['required_pax_before_fixed'])
              and math.ceil(1.1*cost/margin)==int(p['required_pax_10pct_variable_cost_margin'])
              and math.ceil((cost+500000)/margin)==int(p['required_pax_with_symmetric_1m_weekly_fixed']),
              'historical pilot only, not any new35 candidate')
    scales=rows('economics21','context/18_unit_economics_audit/source_linked_scale_tests.csv')
    for i,r in enumerate(scales,2):
        ledger=route_map[(r['route'],r['scenario'])]
        margin=float(next(b['unit_incremental_margin_current_yield'] for b in be if (b['route'],b['scenario'])==(r['route'],r['scenario'])))
        expected=2*float(r['paid_per_departure'])*margin-float(ledger['flight_variable_cost'])
        check('source-linked conditional money row '+str(i),near(expected,r['contribution_before_extra_fixed']),'scenario arithmetic; source segment totals not endpoint demand')
    positives=[(i,r) for i,r in enumerate(scales,2) if float(r['contribution_before_extra_fixed'])>0]
    write_csv('positive_historical_scenarios.csv',[dict(source_commit=PINS['economics21'],source_path='context/18_unit_economics_audit/source_linked_scale_tests.csv',source_line=i,**r) for i,r in positives])
    supply=rows('methods',M+'runs/budget_v1/supply_upper_bounds.csv')
    for i,r in enumerate(supply,2):
        computed=float(r['full_local_revenue'])-float(r['full_local_pax_cost'])-float(r['flight_variable_cost'])
        check('methods capacity-bound arithmetic '+str(i),near(computed,r['optimistic_contribution_upper']),'arithmetic only, certificate scope from supplied review')
    check('four cautious capacity bounds negative',all(float(r['optimistic_contribution_upper'])<0 for r in supply if r['scenario']=='cautious'),'fixed-product relaxation; not all35')

    # Capture context/contracts for evidence, without executing their instructions.
    for label,paths_to_read in {
        'base':['context/16_agent_research/briefs/hypotheses.md','context/16_agent_research/phase2_brief.md',
                'context/16_agent_research/research_contract.md','context/23_night_run_20261110/contract.md',
                'context/23_night_run_20261110/briefs/hypothesis_frontier.md',
                'context/16_agent_research/coordinator/20261109T142217Z/phase2_specs_manifest.json',
                'context/16_agent_research/coordinator/20261109T142217Z/phase2_specs/hypotheses/experiment_v1/contract.json',
                'context/21_visual_explainer_draft_20261110/inputs_manifest.json'],
        'hypotheses':[H+'findings.md',H+'methods.md',H+'experiments_queue.csv',H+'status.json',
                      H+'normalized/reproduced_thresholds.csv',H+'normalized/khv_arrival_rules.csv',
                      H+'experiment_v1/README.md',H+'experiment_v1/handoff.json',H+'experiment_v1/status.json',H+'experiment_v1/contract.json',
                      H+'experiment_v1/runs/c26661067277af20/replacement_states.csv',H+'experiment_v1/runs/c26661067277af20/summary.json'],
        'frontier':[F+'findings.md',F+'test_contract.json',F+'experiment_queue.csv',F+'handoff.json'],
        'review':[R+'report.md',R+'findings.json',R+'handoff.json'],
        'methods':[M+'handoff_compact.md',M+'budget_readout.md'],
        'economics21':['context/18_unit_economics_audit/input_registry.csv','context/18_unit_economics_audit/evidence/observed_pair_segments.csv'],
    }.items():
        for path in paths_to_read: source(label,path)
    observations=rows('hypotheses',H+'contributions/source_access/observations.csv')
    check('214 literal incumbent KHV rules',len(rows('hypotheses',H+'normalized/khv_arrival_rules.csv'))==214,'published inbound context, not demand')

    queue = rows('frontier',F+'experiment_queue.csv')
    queue_by_candidate={c:r for r in queue for c in r['candidate_ids'].split(';')}
    hypothesis_by_id={r['candidate_id']:r for r in frontier}
    disposition=[]
    for i,c in enumerate(candidates,2):
        cid=c['candidate_id'];p=profiles[cid];f=hypothesis_by_id[cid]
        candidate_paths=[r for r in paths if r['candidate_id']==cid]
        geo_line=[j for j,r in enumerate(paths,2) if r['candidate_id']==cid]
        flagged=[r for r in screens if r['candidate_id']==cid and r['screen_km']=='2300' and r['any_leg_over_screen']=='True']
        ev=[evidence('hypotheses',H+'candidates.csv',i),evidence('base','context/16_agent_research/coordinator/20261109T131856Z/hypotheses/candidates.csv',i),
            evidence('hypotheses',H+'normalized/geometry_paths.csv',geo_line[0],geo_line[-1]),evidence('frontier',F+'inventory35.csv',i),
            evidence('frontier',F+'experiment_queue.csv',next(j for j,r in enumerate(queue,2) if cid in r['candidate_ids'].split(';')))]
        for ancestor in c['ancestor_ids'].split(';'):
            ev.append(evidence('hypotheses',H+'existing_hypotheses.csv',ancestor_map[ancestor][0]))
        if cid in ['C01','C07','C14']:
            for path in ['experiment_v1/cost_resource/6cf441ef38e2c6c5/conditional_thresholds_with_product_keys.csv',
                         'experiment_v1/cost_resource/6cf441ef38e2c6c5/residual_gap_accounting.csv']:
                rr=rows('hypotheses',H+path)
                lines=[j for j,r in enumerate(rr,2) if r['candidate']==cid]
                ev.append(evidence('hypotheses',H+path,lines[0],lines[-1]))
        historical_money = ('Прямые36 арифметических grid-строк; состав K и ресурсные дельты; actual money UNKNOWN.'
                            if cid in ['C01','C07','C14'] else 'Отдельного numerical money run именно этой спецификации в проверенном дереве нет; происхождение/аналог ниже не переносит результат.')
        disposition.append(dict(candidate_id=cid,namespace='hypotheses35',title=c['title'],source_commit=PINS['hypotheses'],source_path=H+'candidates.csv',source_line=i,
                                original_status=c['evaluation_status'],original_demand_fare_resource='UNKNOWN / UNKNOWN / UNKNOWN',
                                first_snapshot='f8b94a5:context/16_agent_research/coordinator/20261109T131856Z/hypotheses/candidates.csv:'+str(i),
                                initially_selected_for_deepening=c['selected_for_deepening'],historical_selection_or_scope_reason=c['selection_rationale'],
                                documented_early_rejection='ABSENT; no rejected candidate in early evaluation_runs.jsonl',
                                phase2_executed_test={'C01':'C01 same-leg sync/unsync','C07':'C07 reference vs four-leg chain','C14':'C14 calendar input001/002'}.get(cid,'NOT_IN_THREE_TEST_SCOPE'),
                                frontier_state=f['queue_state'],frontier_later_reason=queue_by_candidate[cid]['reason']+(' C04: comparator only, separate OMS-base test NOT_RUN.' if cid=='C04' else ''),
                                geometry_performed=f"{len(candidate_paths)} paths/{len(by_candidate[cid])}legs; max chord {max(float(r['max_leg_km']) for r in candidate_paths):.3f}km; {len(flagged)} paths flagged at2300; own audit recomputed. Scenario screen, not dispatch/rejection.",
                                calendar_performed=p.get('calendar','Только proposed paths/frequency specification и chord screen; отдельного dated outward/return test именно этой карточки в проверенных артефактах нет.'),
                                demand_performed='Все ранние runs:demand_fit NOT_RUN; actual endpoint OD, realised fare и migration не измерены. Наблюдения/контекст не превращены в paid demand.',
                                money_performed=historical_money,
                                fleet_performed=p.get('fleet','Геометрия/словесный resource_requirement есть; ни actual free tail/crew/MRO, ни named donor/dated full production rotation этой карточки не установлены.'),
                                historical_economics_or_analogue=p['analogue'],
                                disposition='DEFERRED_UNKNOWN_WITH_PARTIAL_TESTS' if cid in ['C01','C07','C14'] else 'NOT_EVALUATED_OUR_SCOPE',
                                conditional_rejection_scope=p.get('conditional','NO_DOCUMENTED_REJECTION; последующий unresolved parameter не ретроспективная причина отсева.'),
                                what_can_be_concluded=p['conclusion'],specific_next_check=p['next'],
                                scenario_economics_possible_now=p['scenario'],
                                scenario_limits='Это допустимая следующая постановка, не выполненный здесь новый economic experiment. UNKNOWN сохраняется; численные grid/stress не confidence bounds. Нужны named baseline, период, один fare и capacity ledger; полный cash отдельно.',
                                evidence_json=json.dumps(ev,ensure_ascii=False)))
    write_csv('disposition.csv',disposition)
    check('disposition exactly35 unique',len(disposition)==35 and len({r['candidate_id'] for r in disposition})==35,'delivery')

    tree=subprocess.check_output(['git','ls-tree','-r','--name-only',PINS['hypotheses'],'--',H],cwd=REPO,text=True)
    (OUT/'hypotheses_tree_at_pin.txt').write_text(tree)
    money_files=[p for p in tree.splitlines() if any(term in p for term in ['cost_resource/','conditional_thresholds','reproduced_thresholds','comparison.csv','breakeven.csv'])]
    dump('money_file_inventory.json',dict(commit=PINS['hypotheses'],subtree=H,files=money_files,
                                          duplicate_policy='108 unique threshold scenarios; versions and keyed projections not independent market observations'))
    dump('checks.json',dict(mode='NEW_FINITE_OFFLINE_AUDIT',checks=checks,summary=dict(passed=sum(c['passed'] for c in checks),failed=sum(not c['passed'] for c in checks),
                        rows=35,early_rejections=0,selected_initially=9,directly_tested=3,scope_untested=32,
                        money_scenarios=108,context21_network_money_rows=len(economics),historic_stage16_rows=len(old_comparison),break_even_rows=len(be),
                        source_linked_scenario_rows=len(scales),positive_source_linked_rows=len(positives),geometry_max_abs_error_km=max_error),
                        exclusions=['No live sources refreshed','No owner/reviewer executable code run','No full economic model replay/LP certificate proof','No observed sales/realised revenue/operating acceptance','No new candidate experiment or continuation']))
    seal_sources()
    print(json.dumps(json.loads((OUT/'checks.json').read_text())['summary'],ensure_ascii=False))


if __name__=='__main__':
    main()
