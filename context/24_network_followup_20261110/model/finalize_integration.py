#!/usr/bin/env python3
"""Final scoped delivery. Offline only; reuses the frozen integrator.

--prepare makes the 50-row evidence package without numerical admission.
Run integrate_once.py --apply exactly once, then --report.
--verify is read-only and replays the fixed ledger, not the applied round.
Never run the baseline builders to reproduce this final delivery.
"""
import argparse
import ast
import collections
import csv
import html
import json
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode = True
from build_baseline import (HERE, OUT, REPO, NAMES, NUMERIC, MONEY_RESULT, read_csv,
                            write_csv, write_json, sha256, near, load_inputs)
from prepare_admission import FIELDS, TAX, PERIOD
import integrate_once as adapter

EXTRA = ['source_reference_period', 'period_qualification', 'source_publication_date',
         'source_accessed_at', 'why', 'separate_sensitivity_use']
RESEARCH = {'demand': 'market_final.csv', 'cost_budget': 'costs_final.csv',
            'product_operations': 'operations.csv'}
STAMP = '2026-11-10'
LOCK = HERE / 'final_input_lock.json'


def require(v, message):
    if not v:
        raise AssertionError(message)


def check_lock(publication=None):
    lock = json.loads(LOCK.read_text())
    omitted = {'delegation_round1.local.json',
               'delegation_round2_research.local.json',
               'delegation_round2_integration.local.json'}
    if publication is not None:
        require(set(publication['omitted_orchestration_files']) <= omitted,
                'unexpected publication omission')
        require(set(publication['packaging_changed_files']) == {'model/finalize_integration.py'},
                'unexpected post-integration source change')
    for name, expected in lock['files'].items():
        if publication is not None and name in publication['omitted_orchestration_files']:
            continue
        if publication is not None and name in publication['packaging_changed_files']:
            expected = publication['packaging_changed_files'][name]['release_sha256']
        require(sha256(OUT / name) == expected, f'pre-existing bytes changed: {name}')
    if publication is not None:
        return  # Frozen scientific bytes are checked; checkout/HEAD may legitimately change.
    require(subprocess.check_output(['git', 'branch', '--show-current'], cwd=REPO, text=True).strip() == lock['branch'], 'branch changed')
    require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip() == lock['HEAD'], 'HEAD changed')
    require(not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=REPO, text=True).strip(), 'tracked files changed')
    return lock


def verify_research():
    researchers = []
    for rid, filename in RESEARCH.items():
        path = OUT / f'research/accepted_manifests/{rid}.json'
        manifest = json.loads(path.read_text())
        require(manifest['status'] == 'FINAL' and manifest['researcher_id'] == rid, rid)
        data = read_csv(OUT / manifest['file'])
        require(sha256(OUT / manifest['file']) == manifest['sha256'], f'{rid}: CSV hash')
        require([r['finding_id'] for r in data] == manifest['finding_ids'], f'{rid}: findings order/enumeration')
        if manifest.get('source_manifest'):
            src = OUT / manifest['source_manifest']
            require(sha256(src) == manifest['source_manifest_sha256'], f'{rid}: source manifest hash')
            for entry in json.loads(src.read_text())['files']:
                relative = entry['file']
                p = REPO / relative if relative.startswith('context/') else OUT / 'research' / relative
                require(entry['status'] == 'FINAL' and sha256(p) == entry['sha256'], f'{rid}: source artifact {relative}')
        researchers.append(dict(researcher_id=rid, status='FINAL', manifest_path=str(path.relative_to(OUT)), manifest_sha256=sha256(path)))
    return researchers


def admission(rid, r):
    fid = r['finding_id']
    historical = fid in ('M01_route_passengers', 'M01_monthly_passengers', 'M02_route_passengers')
    plan = fid in ('M01_competitor_frequency', 'M02_competitor_frequency')
    cost_reference = fid.startswith('C_LEGACY_') or fid in ('C_RECON_OLD', 'C_RECON_NEW')
    context = historical or plan or fid in ('OP02', 'OP05')
    status = 'proxy' if context else 'scenario_only' if cost_reference else 'rejected_missing_scope'
    start = end = ''
    qualification = 'UNKNOWN applicability; source_reference_period is not established coverage'
    if historical:
        start, end = ('2025-01-01', '2025-01-31') if 'monthly' in fid else ('2025-01-01', '2025-12-31')
        qualification = 'Reported historical aggregate interval; no directional winter endpoint OD conversion'
    elif status != 'rejected_missing_scope':
        start = end = STAMP
        qualification = ('ACCESS_DATE_ONLY; publication/validity undated; timetable year implicit' if plan else
                         'ACCESS_DATE_ONLY; undated page; not target-week operating approval' if fid.startswith('OP') else
                         'REGISTER_REVIEW_DATE_ONLY; claimed effective dates in source_reference_period; actual validity end and December contract UNKNOWN')
    why = r['scope_limit'] + ' | ' + r['model_change']
    unit = r['unit'] or 'UNKNOWN_UNIT_NO_OBSERVATION'
    param = ('weekly_demand' if r['parameter'] in ('route_passengers', 'monthly_passengers') else
             'fare_once_net' if r['parameter'] == 'comparable_fare' else r['parameter'])
    tax = 'SAVED_EXVAT_CLAIM_UNVERIFIED' if cost_reference else 'UNKNOWN_NO_PRICE' if ('fare' in fid or rid == 'cost_budget') else 'NOT_APPLICABLE_QUANTITY_OR_PROCESS'
    path = OUT / 'research' / RESEARCH[rid]
    out = {k: '' for k in FIELDS + EXTRA}
    out.update(finding_id=fid, researcher_id=rid, claim=f"{r['parameter']}: {r['value'] or 'UNKNOWN'}; {r['topic']}",
               admission_status=status, apply='false', model_parameter=param,
               network=r['network_or_candidate'], scenario='NONE_APPLIED', recipe='NONE_APPLIED', value=r['value'],
               source_url=r['source_url'] or f"artifact://research/{RESEARCH[rid]}#{fid}",
               source_artifact=str(path.relative_to(OUT)), source_sha256=sha256(path),
               source_period_start=start, source_period_end=end, source_unit=unit, source_tax_basis=tax,
               model_period_start=PERIOD['start'], model_period_end=PERIOD['end'],
               model_unit=('endpoint_journeys/week/direction' if param == 'weekly_demand' else 'RUB/endpoint_journey' if param == 'fare_once_net' else 'NOT_APPLIED'),
               model_tax_basis=TAX if rid == 'cost_budget' or param == 'fare_once_net' else 'NOT_APPLICABLE_QUANTITY_OR_PROCESS',
               source_kind=r['evidence_kind'], source_scope=r['scope_limit'], carrier='UNKNOWN_OR_ALL_CARRIERS_AGGREGATE',
               conversion='NONE_TO_MODEL; historical/offer/reference/process context only; UNKNOWN never zero',
               condition='Do not change numerical inputs; ' + why, reliability=r['reliability'],
               rejection_reason=why if status == 'rejected_missing_scope' else '', source_reference_period=r['reference_period'],
               period_qualification=qualification, source_publication_date=r['publication_date'],
               source_accessed_at=r['accessed_at'], why=why,
               separate_sensitivity_use='PRICE_BASIS_AUTHOR_SCENARIO; bridge total-minus-uplift; no actual-rate admission' if fid in ('C_RECON_OLD', 'C_RECON_NEW') else 'NONE')
    return out


def prepare():
    require(not LOCK.exists(), 'prepare already done; do not rewrite lock/package')
    require(not (HERE / 'final_round/integration_receipt.json').exists(), 'round already consumed')
    files = {str(p.relative_to(OUT)): sha256(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p != Path(__file__).resolve()}
    write_json(LOCK, dict(files=files, branch=subprocess.check_output(['git', 'branch', '--show-current'], cwd=REPO, text=True).strip(),
                          HEAD=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()))
    researchers = verify_research()
    rows = [admission(rid, r) for rid, f in RESEARCH.items() for r in read_csv(OUT / 'research' / f)]
    require(len(rows) == len({r['finding_id'] for r in rows}) == 50, '50 unique finding IDs required')
    write_csv(OUT / 'findings_admission.csv', rows, FIELDS + EXTRA)
    write_adapter_projection(rows)
    package = json.loads((HERE / 'final_integration_package.template.json').read_text())
    package.update(ready=True, all_findings_enumerated=True, researchers=researchers,
                   findings_csv='model/findings_adapter.csv', findings_sha256=sha256(HERE / 'findings_adapter.csv'), finding_count=50,
                   detailed_admission_csv='findings_admission.csv', detailed_admission_sha256=sha256(OUT/'findings_admission.csv'),
                   integration_policy='No direct numeric updates. Keep UFA-local evidence scope intact. Separate fixed-ledger author price sensitivity is outside factual admission.')
    write_json(OUT / 'final_integration_package.json', package)
    adapter.read_package('final_integration_package.json')
    check_lock()
    print(json.dumps(dict(status='FINAL_PACKAGE_READY', findings=50, admissions=collections.Counter(r['admission_status'] for r in rows), apply_true=0)))


def write_adapter_projection(rows):
    projected=[]
    for r in rows:
        x={k:r[k] for k in FIELDS}
        x['condition'] += '; ' + '; '.join(k+'='+r[k] for k in EXTRA)
        projected.append(x)
    write_csv(HERE/'findings_adapter.csv',projected,FIELDS)


def owner_formula():
    src = OUT / 'owner_snapshot/src/network_model.py'
    fn = next(n for n in ast.parse(src.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == 'leg_cost')
    fuel = next(n.value for n in fn.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'fuel' for t in n.targets))
    fields = [n.slice.value for n in ast.walk(fuel) if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant)]
    require(fields.count('fuel_rub_per_t') == 1 and not any('uplift' in str(k) for k in fields), 'owner formula uplift duplication')
    assumptions = {r['parameter']: r for r in read_csv(OUT / 'owner_snapshot/data/assumptions/network.csv')}
    receipts = []
    for sc in ('base', 'cautious'):
        a = {k: float(v[sc]) for k, v in assumptions.items()}
        total = 134896 if sc == 'base' else 161696
        near(a['fuel_rub_per_t'], total, 'owner combined price')
        bh = 2.5
        actual = eval(compile(ast.Expression(fuel), '<exact owner fuel expression>', 'eval'), {'__builtins__': {}}, {'A': a, 'bh': bh})
        near(actual, (a['fuel_t_per_hour']*bh+a['fuel_t_per_cycle'])*total, 'combined price once')
        receipts.append(dict(scenario=sc, owner_total=total, uplift_added_again=False, formula=ast.unparse(fuel), block_hours_test=bh, computed_fuel=actual))
    return dict(status='STATIC_EXACT_FUEL_EXPRESSION_CHECK_ONLY', owner_optimizer_run=False, source_sha256=sha256(src),
                difference_is_price_basis_not_automatic_error=True, cases=receipts)


def price_sensitivity():
    """Cost ledger only: no market row is promoted to all-leg source scope."""
    m, _, _, _, _, _, config = load_inputs()
    supply = read_csv(HERE / 'dated_legs.csv')
    baseline = read_csv(HERE / 'baseline_comparison.csv')
    require(len(supply) == 64 and len({r['id'] for r in supply}) == 64, 'same 64 dated legs')
    details, output = [], []
    sums = {}
    for sc in ('base', 'cautious'):
        p = config['scenarios'][sc]
        pp = dict(p)
        if sc == 'base':
            require(p['fuel_rub_per_t'] == 136300 and p['fuel_uplift_rub_per_t'] == 1696, 'frozen fuel price')
            pp['fuel_rub_per_t'] = 134896 - p['fuel_uplift_rub_per_t']
            require(pp['fuel_rub_per_t'] == 133200, 'total-minus-uplift bridge')
        require([k for k in p if p[k] != pp[k]] == (['fuel_rub_per_t'] if sc == 'base' else []), 'cost parameter only')
        for n in NAMES:
            selected = [r for r in supply if r['common_network'] == n]
            for leg in selected:
                h = float(leg['block_minutes']) / 60
                fuel_t = p['fuel_t_per_hour'] * h + p['fuel_t_per_cycle']
                old, new = m.flight_cost(float(leg['block_minutes']), p), m.flight_cost(float(leg['block_minutes']), pp)
                delta = new-old
                near(delta, fuel_t * (pp['fuel_rub_per_t']-p['fuel_rub_per_t']), 'commodity + uplift exactly once')
                details.append(dict(network=n, scenario=sc, flight_id=leg['id'], date=leg['date'], fuel_t=fuel_t,
                                    commodity_before=p['fuel_rub_per_t'], uplift_before=p['fuel_uplift_rub_per_t'], total_before=p['fuel_rub_per_t']+p['fuel_uplift_rub_per_t'],
                                    commodity_after=pp['fuel_rub_per_t'], uplift_after=pp['fuel_uplift_rub_per_t'], total_after=pp['fuel_rub_per_t']+pp['fuel_uplift_rub_per_t'],
                                    flight_cost_before=old, flight_cost_after=new, delta_cost=delta, tax_basis=TAX,
                                    status='AUTHOR_FIXED_LEDGER_SCENARIO_NOT_APPLICABLE_RATE'))
            ls = [r for r in details if r['network'] == n and r['scenario'] == sc]
            sums[n, sc] = sum(r['delta_cost'] for r in ls)
    for b in baseline:
        n, sc, recipe = b['network'], b['scenario'], b['recipe']
        ls = [r for r in details if r['network'] == n and r['scenario'] == sc]
        old_cost = sum(r['flight_cost_before'] for r in ls)
        near(old_cost, b['flight_variable_cost'], 'frozen per-leg cost equals baseline')
        delta = sums[n, sc]
        before = float(b[MONEY_RESULT])
        after = before-delta
        row = dict(network=n, scenario=sc, recipe=recipe, variant='SEPARATE_FIXED_LEDGER_PRICE_BASIS_SCENARIO_ONLY',
                   period_start=PERIOD['start'], period_end=PERIOD['end'], tax_basis=TAX,
                   model_flown_legs=len(ls), fuel_t=sum(r['fuel_t'] for r in ls), cost_before=old_cost,
                   cost_after=old_cost+delta, delta_cost=delta, before_contribution=before,
                   after_contribution=after, delta_contribution=-delta,
                   initial_contribution_deficit=-before, improvement_pct_of_initial_deficit=100*(-delta)/(-before),
                   deficit_remaining=-after, initial_deficit_over_improvement=(-before)/(-delta) if delta else None,
                   sign_changed=(before >= 0) != (after >= 0), full_pnl=None, peak_cash=None,
                   launch_accepted=False, source_findings='C_RECON_OLD;C_RECON_NEW')
        row.update({k: float(b[k]) for k in NUMERIC if k not in ('flight_variable_cost', MONEY_RESULT)})
        near(row['gross_revenue']-row['foregone_RW_revenue']-row['new_pax_variable']+row['saved_old_pax_variable']-row['cost_after'], after, 'scenario money identity')
        output.append(row)
    for sc in ('base', 'cautious'):
        for recipe in ('C', 'N'):
            selected = [r for r in output if r['scenario'] == sc and r['recipe'] == recipe]
            old_order = [r['network'] for r in sorted(selected, key=lambda x: -x['before_contribution'])]
            new_order = [r['network'] for r in sorted(selected, key=lambda x: -x['after_contribution'])]
            require(old_order == new_order, 'network order unexpectedly changed')
            for r in selected:
                r.update(order_before=' > '.join(old_order), order_after=' > '.join(new_order), order_changed=False)
    return output, details


def handoff(rows):
    result = []
    A = 'data/assumptions/network.csv'
    for r in rows:
        fid = r['finding_id']
        current = 'UNKNOWN in this scoped evidence; actual current-owner cell not exported'
        proposed = 'KEEP_UNKNOWN'
        unit = r['source_unit']
        condition = r['why']
        effect = 'No common numeric effect; gate remains UNKNOWN'
        if r['researcher_id'] == 'demand':
            if 'fare' in fid:
                file, param = A, 'fare_fixed_rub/fare_per_km_rub + proposed achieved_RW_net_fare[pair,date] metadata'
                current = 'formula scenarios base2093+6.30/km; cautious1636+4.78/km; achieved yield UNKNOWN'
                condition += '; obtain closed paid-ticket net fare after refunds, taxes, commissions, bags; keep old-RW fare separate'
                unit = 'RUB/endpoint_journey; net basket explicitly reconciled'
            elif 'frequency' in fid:
                file, param = 'context/12_network_economics/competition.csv', 'proposed source_URL/as_of/valid_from/valid_to/year_status/plan_vs_performed for ' + fid[:3]
                current = 'M01 14 / M02 16 published SVX departures/week; others UNKNOWN; not current owner frequency inference'
                proposed = 'ADD_SOURCE_VALIDITY_METADATA_ONLY; KEEP_UNKNOWN performed flights/residual seats'
                condition += '; need dated operator schedule export and actual completion; implicit year kept explicit'
                unit = 'planned directed departures/week, not paid pax'
            else:
                file, param = 'data/manual/known_flows.csv', 'pair/period/coverage; src/network_model.py:Demand; common N annual/104 metadata'
                current = 'common C weekly scenario; frozen N annual_proxy/104 BOTH scenarios; no replacement with 211000/785000'
                proposed = 'MARK_ANNUAL_ROUTE_OR_AIRPORT_PROXY; KEEP_UNKNOWN winter_endpoint_OD'
                condition += '; need closed directional endpoint OD by date, direct/transfer split and paid journeys; do not divide historical aggregate into observed winter OD'
                unit = 'source movements/year or month versus endpoint_journeys/week/direction'
        elif fid in ('C_LEGACY_00','C_LEGACY_01','C_LEGACY_06','C_RECON_OLD','C_RECON_NEW'):
            file, param = A + '; src/network_model.py:leg_cost', 'fuel_rub_per_t -> proposed fuel_commodity_rub_per_t/fuel_uplift_rub_per_t/fuel_total_rub_per_t + tax_basis/effective_dates/source_scope'
            current = 'owner54cd combined base134896/cautious161696, multiplied once; common base136300+1696; different price bases'
            proposed = 'SPLIT_METADATA_PRESERVE_OWNER_TOTAL; KEEP_UNKNOWN actual December RW contract and recoverable VAT'
            effect = 'No owner numerical edit; separate base sensitivity total134896 versus137996; cautious unchanged'
            condition += '; require invoices/contracts by airport, commodity/uplift inclusion, VAT eligibility, discounts and validity; no all-network actual UFA rate'
            unit = 'RUB/t; commodity + uplift = total; source tax claim unverified'
        elif fid.startswith('C_LEGACY_') or fid.startswith('C_PDF') or fid == 'C_FUEL_NEW':
            file, param = A, 'ground_rub_per_flight/pax_cost_rub + proposed tariff_components/source_scope/tax_basis/effective_dates'
            current = 'ground base96089/cautious115307; pax500/650 author scenarios; tariff scope/tax/contract UNKNOWN'
            proposed = 'KEEP_UNKNOWN actual contract; label historical tariff REFERENCE_ONLY'
            condition += '; need primary tariff text, billing MTOW, departing pax, included handling and deicing; receive-release is not MRO'
        elif fid == 'C_SUPPORT_NJC':
            file, param = 'data/raw/favt_subsidy_2026.csv; data/assumptions/network.csv', 'proposed RW_UFA_NJC_award_status/recipient/period/income_recognition/cash_terms'
            condition += '; need signed RW agreement/award, applicable route/date/volume, rate and payment/recognition conditions'
            current = 'specific RW award/amount UNKNOWN; common no active credit (not factual zero subsidy)'
        elif fid.startswith('C_SVX_'):
            file = A
            param = {'C_SVX_actual_fuel_price':'fuel_rub_per_t + actual_fuel_contract_status', 'C_SVX_base_contract':'proposed incremental_base_F_B_status',
                     'C_SVX_lease_contract':'proposed lease_and_available_tails_status', 'C_SVX_crew_contract':'crew_rub_per_hour + crew_contract_status',
                     'C_SVX_MRO_contract_available_capacity':'mro_rub_per_hour + MRO_contract/spare_capacity_status'}[fid]
            current = 'actual contract/resource UNKNOWN; model hourly/fuel scenario is not a signed contract'
            condition += '; obtain closed contracts, dated named available tails, crew/MRO windows, base obligations and incremental amounts; full PnL/peak cash remain NULL'
        else:
            file = 'context/12_network_economics/schedule_rules.json; docs/17_fleet_range_maintenance_time.md'
            param = {'OP01':'proposed C01_dated_legs/UTC_rollover/turn_gate', 'OP02':'proposed C01_protected_product/RW_MCT/through_baggage_gate',
                     'OP03':'proposed C07_full_rotation/block_turn_operating_window_gate', 'OP04':'proposed C07_named_next_tail_assignment_gate',
                     'OP05':'proposed C08_R95_subtype/date/payload_dispatch_gate'}[fid]
            current = 'UNKNOWN operational acceptance; frozen common model legs not C01/C07/C08 approval'
            condition += '; obtain carrier-approved dated rotation and protected product/MCT, or AFM/OFP/payload/technical clearance for named aircraft; generic family/range insufficient'
        result.append(dict(findingID=fid, owner_file=file, parameter=param, current=current, proposed=proposed, unit=unit,
                           source=r['source_url'], source_artifact=r['source_artifact'], source_sha256=r['source_sha256'],
                           source_date=r['source_publication_date'] or r['source_reference_period'] or 'UNDATED/UNKNOWN',
                           source_accessed_at=r['source_accessed_at'], reliability=r['reliability'], expected_effect_or_gate=effect,
                           condition=condition, status='HANDOFF_ONLY_OWNER_UNCHANGED_NO_REQUEST_SENT'))
    # Two cross-cutting owner actions preserve unit/period/budget semantics.
    result.extend([
        dict(findingID='CROSS_PERIOD', owner_file=A+'; data/processed/network_summary.csv', parameter='weeks_per_year; common N /104; annual versus common week', current='owner54cd base52/cautious48; common fixed 7–13.12.2026; N/104 both', proposed='PRESERVE_SEPARATE_CONTOURS; label annual proxy and model weeks', unit='RUB/model_week versus RUB/model_year; movements versus endpoint journeys', source='artifact://owner_snapshot/data/assumptions/network.csv', source_artifact='owner_snapshot/data/assumptions/network.csv', source_sha256=sha256(OUT/'owner_snapshot/data/assumptions/network.csv'), source_date='54cd export', source_accessed_at=STAMP, reliability='EXACT_AUTHOR_ASSUMPTIONS_NOT_ACTUAL_YEAR', expected_effect_or_gate='No week×52 factual annualization', condition='Need seasonal dated operating/demand ledger for real annual result', status='HANDOFF_ONLY_OWNER_UNCHANGED_NO_REQUEST_SENT'),
        dict(findingID='CROSS_BUDGET', owner_file=A+'; src/network_model.py', parameter='proposed full_PnL/peak_cash/external_donor_delta/F/B/support/start/exit', current='UNKNOWN/NULL; own-RW foregone revenue already deducted in common contribution', proposed='KEEP_UNKNOWN', unit='incremental RUB and dated gross cash', source='artifact://model/model_audit.md', source_artifact='model/model_audit.md', source_sha256=sha256(HERE/'model_audit.md'), source_date='frozen model audit', source_accessed_at=STAMP, reliability='MISSING_CLOSED_BUDGET', expected_effect_or_gate='No launch acceptance; no fabricated subsidy or donor savings', condition='Need named KEEP/CANCEL/REPLACE obligations, lease/base/support/start/exit cash dates and financing; avoid own-migration double subtraction', status='HANDOFF_ONLY_OWNER_UNCHANGED_NO_REQUEST_SENT')])
    return result


def money(x, digits=3):
    return f'{x/1e6:,.{digits}f}'.replace(',', ' ')


def report():
    check_lock()
    verify_receipts()
    verify_research()
    _, _, rows = adapter.read_package('final_integration_package.json')
    receipt = json.loads((HERE / 'final_round/integration_receipt.json').read_text())
    require(receipt['applied_findings'] == 0 and receipt['findings'] == 50, 'factual numeric changes must be zero')
    _, repeated, repeat_detail, _, repeat_legs = adapter.compute(rows)
    frozen = read_csv(HERE / 'baseline_comparison.csv')
    saved = read_csv(HERE / 'final_round/integration_comparison.csv')
    require(len(saved) == len(repeated) == 12, '12 final rows')
    worst = 0.0
    for r in repeated:
        b = next(x for x in frozen if (x['network'],x['scenario'],x['recipe']) == (r['network'],r['scenario'],r['baseline_recipe']))
        s = next(x for x in saved if (x['network'],x['scenario'],x['baseline_recipe']) == (r['network'],r['scenario'],r['baseline_recipe']))
        for k in NUMERIC:
            worst = max(worst, near(r[k], b[k], ('baseline unchanged', k)), near(r[k], s[k], ('one deterministic repeat', k)))
        near(r['delta_contribution'], 0, 'no research monetary effect')
    require(len(repeat_detail) == len(read_csv(HERE/'final_round/integration_itineraries.csv')) == 384, 'all itinerary rows')
    for actual, written in zip(repeat_detail, read_csv(HERE/'final_round/integration_itineraries.csv')):
        for k,v in actual.items():
            if isinstance(v, (int,float)) and not isinstance(v,bool):
                near(v, written[k], ('itinerary deterministic repeat',k))
            else:
                require(str(v) == written[k], ('itinerary deterministic repeat',k))
    for r in rows:
        require(sha256(OUT / r['source_artifact']) == r['source_sha256'], 'every ID including rejection source hash')
        require(r['apply'] == 'false', 'no numerical factual update')
    sensitivity, leg_costs = price_sensitivity()
    require((sensitivity, leg_costs) == price_sensitivity(), 'one deterministic sensitivity repeat')
    write_csv(OUT / 'price_sensitivity.csv', sensitivity)
    write_csv(OUT / 'price_sensitivity_legs.csv', leg_costs)
    owner_check = owner_formula()
    write_json(OUT / 'owner_fuel_formula_check.json', owner_check)
    bridge = dict(status='SEPARATE_AUTHOR_FIXED_LEDGER_SCENARIO_ONLY', findings=['C_RECON_OLD','C_RECON_NEW'],
                  reason_outside_adapter='UFA-local reference finding cannot be applied as all-leg evidence without replacing its source_scope; preserve original scope and apply=false. This separate object defines a common author price basis, not a contract.',
                  source_artifacts={p:sha256(OUT/p) for p in ['research/costs_final.csv','research/accepted_manifests/cost_budget.json','model/source_snapshot/context21/context/15_team_update/model/configuration.json','owner_snapshot/src/network_model.py','owner_snapshot/data/assumptions/network.csv']},
                  period=PERIOD, scenario='base', recipes=['C','N'], networks=list(NAMES), applies_to='all fixed flown legs as an AUTHOR SCENARIO ONLY',
                  before=dict(commodity=136300,uplift=1696,total=137996), after=dict(total=134896,uplift=1696,commodity_from_total_minus_uplift=133200),
                  delta_RUB_t=-3100, tax_basis=TAX, tax_claim='No invoice/VAT eligibility confirmed, no second VAT removal', cautious='UNCHANGED commodity160000+uplift1696',
                  authoritative_baseline_changed=False, source_prices_verified=False, donor_savings_added=False, subsidy_added=False,
                  alpha_recomputed=False, demand_threshold_recomputed=False)
    write_json(OUT / 'price_scenario_bridge.json', bridge)
    write_csv(OUT / 'owner_handoff_final.csv', handoff(read_csv(OUT/'findings_admission.csv')))
    write_readme(sensitivity, rows)
    write_html(sensitivity)
    protected = json.loads((OUT/'protected_city_stage.json').read_text())
    require(len(protected) == 7, 'seven protected files')
    protected_result = {p:dict(expected=h, actual=sha256(REPO/p), match=sha256(REPO/p)==h) for p,h in protected.items()}
    require(all(r['match'] for r in protected_result.values()), 'protected hashes')
    check_lock()
    validation = dict(status='PASS_SCOPED_FINAL_FIXED_LEDGER_ONLY', findings=50, all_finding_IDs_accounted=True,
                      researcher_counts={rid:sum(r['researcher_id']==rid for r in rows) for rid in RESEARCH},
                      admission_counts=dict(collections.Counter(r['admission_status'] for r in rows)), all_50_source_hashes_checked=True,
                      direct_numeric_updates=0, applied_research_findings=0, actual_findings_money_delta_RUB=0,
                      final_apply_count=1, apply_command_attempts=2, first_attempt='REJECTED_NO_INTEGRATION: CSV extra fields; no receipt; fixed-schema projection then one successful consumed round', final_receipt_sha256=sha256(HERE/'final_round/integration_receipt.json'),
                      baseline_rows=12, baseline_max_numeric_delta=worst, tolerance_RUB=1e-6,
                      deterministic_repeat=dict(final_rows=12,itinerary_rows=384,price_scenario_rows=12,leg_cost_rows=128, result='PASS_ONE_REPEAT'),
                      money_identity=True, fare_once_and_seat_each_leg=True, own_migration_deduction_preserved=True,
                      fuel_commodity_plus_uplift_once=True, owner_combined_fuel_once=True,
                      price_scenario_cost_only=True, demand_net_yield_capture_allocator_capacity_migration_unchanged=True,
                      same_64_dated_legs=True, all_base_legs_and_both_recipes_symmetric=True, cautious_unchanged=True,
                      no_sign_or_order_change=True, periods_and_tax_labels_preserved=True,
                      original_thresholds_preserved_new_cost_thresholds_not_recomputed=True,
                      protected_city_stage=protected_result, protected_all_match=True,
                      preexisting_files_unchanged=len(json.loads(LOCK.read_text())['files']),
                      owner_files_modified=False, owner_optimizer_run=False, original_network_generation_replayed=False,
                      source_approval='Supplied research classifications and local bytes only; no new external requests or independent price validation',
                      full_PnL=None, peak_cash=None, actual_fleet_or_contract_acceptance=False,
                      limitations=['No direct winter endpoint OD or achieved net yield', 'Unreadable public cost PDFs; unknown specific RW award',
                                   'Undated conditional UFA process is not RW MCT/protected product', 'Fixed ledger replay only; actual operations and excluded incremental budget UNKNOWN',
                                   'No visual browser QA in subagent; root must show summary.html using html_preview/html_render'])
    write_json(OUT/'final_validation.json', validation)
    # Include all bytes, including frozen evidence; manifest itself is excluded to avoid self-reference.
    manifest = dict(status='FINAL_SCOPED_DELIVERY', files=[dict(path=str(p.relative_to(OUT)),bytes=p.stat().st_size,sha256=sha256(p))
                    for p in sorted(OUT.rglob('*')) if p.is_file() and p != OUT/'final_manifest.json'],
                    offline_command='python3 context/24_network_followup_20261110/model/finalize_integration.py --verify',
                    apply='ALREADY_CONSUMED_ONCE; do not rerun integrate_once --apply or baseline builders',
                    actual_numeric_updates=0, separate_author_sensitivity='price_sensitivity.csv', unresolved='Retained in final_validation.json and owner_handoff_final.csv; no further research rounds')
    write_json(OUT/'final_manifest.json',manifest)
    print(json.dumps(dict(status=validation['status'], findings=50, direct_numeric_updates=0, sensitivity=[{k:r[k] for k in ('network','scenario','recipe','delta_contribution','after_contribution','improvement_pct_of_initial_deficit')} for r in sensitivity], protected_all_match=True), ensure_ascii=False))


def verify_receipts():
    package = json.loads((OUT/'final_integration_package.json').read_text())
    require(sha256(OUT/package['detailed_admission_csv']) == package['detailed_admission_sha256'], 'detailed admission hash')
    full = read_csv(OUT/package['detailed_admission_csv'])
    projected = read_csv(OUT/package['findings_csv'])
    require(len(full) == len(projected) == 50, 'projection rows')
    for a,b in zip(full,projected):
        require(all(a[k] == b[k] for k in FIELDS if k != 'condition'), 'projection changed finding fields')
        require(b['condition'] == a['condition'] + '; ' + '; '.join(k+'='+a[k] for k in EXTRA), 'projection lost qualification')
        require(sha256(OUT/a['source_artifact']) == a['source_sha256'], 'rejected/admitted hash')
    receipt=json.loads((HERE/'final_round/integration_receipt.json').read_text())
    require(receipt['package_sha256']==sha256(OUT/'final_integration_package.json'), 'successful receipt package hash')
    for name,expected in receipt['output_sha256'].items():
        require(sha256(HERE/'final_round'/name)==expected, 'successful integration output hash')
    attempts=json.loads((HERE/'final_round_attempts.json').read_text())
    require(attempts['successful_consumed_rounds']==1 and len(attempts['attempts'])==2, 'explicit failed attempt and one successful round')


def verify():
    verify_receipts()
    publication_path = OUT/'publication_manifest.json'
    publication = json.loads(publication_path.read_text()) if publication_path.exists() else None
    check_lock(publication)
    verify_research()
    manifest = publication if publication is not None else json.loads((OUT/'final_manifest.json').read_text())
    for r in manifest['files']:
        require(sha256(OUT/r['path'])==r['sha256'] and (OUT/r['path']).stat().st_size==r['bytes'], f"final manifest mismatch: {r['path']}")
    _,_,rows=adapter.read_package('final_integration_package.json')
    _, repeated, _, _, _=adapter.compute(rows)
    saved=read_csv(HERE/'final_round/integration_comparison.csv')
    for r,s in zip(repeated,saved):
        for k in NUMERIC: near(r[k],s[k],('read-only replay',k))
    scenario,legs=price_sensitivity()
    for actual,written in zip(scenario,read_csv(OUT/'price_sensitivity.csv')):
        for k,v in actual.items():
            if isinstance(v,(int,float)) and not isinstance(v,bool): near(v,written[k],('scenario replay',k))
    owner_formula()
    protected=json.loads((OUT/'protected_city_stage.json').read_text())
    require(all(sha256(REPO/p)==h for p,h in protected.items()),'protected')
    print(json.dumps(dict(status='PASS_READ_ONLY_OFFLINE_REPLAY', finding_ids=len(rows), final_apply_repeated=False, baseline_rows=len(repeated), scenario_rows=len(scenario), dated_legs=64, protected_files=len(protected), manifest_files=len(manifest['files']))))


def write_readme(sensitivity,rows):
    # Filled by the same deterministic report step; text is kept local, no Pages or publication.
    text = readme_text(sensitivity, rows)
    require(600 <= len(text.split()) <= 900, f'README word target: {len(text.split())}')
    (OUT/'README.md').write_text(text)


def readme_text(sensitivity, rows):
    return README_TEMPLATE.replace('@@TABLE@@', '\n'.join(f"| {r['network']} / {r['recipe']} | {money(r['before_contribution'])} | {money(r['delta_contribution'],6)} | {money(r['after_contribution'])} | {r['improvement_pct_of_initial_deficit']:.2f}% |" for r in sensitivity if r['scenario']=='base'))


def write_html(sensitivity):
    # Self-contained HTML/SVG: root displays it in T3; no server/browser used here.
    (OUT/'summary.html').write_text(html_text(sensitivity))


README_TEMPLATE = '''Финальная интеграция завершена 10 ноября 2026 года. Приняты к учёту все 50 findingID: 26 рыночных, 19 стоимостных и 5 операционных. У каждого есть admission, apply=false, единицы, период либо явная неизвестность, налоговый статус, объяснение и SHA-256 сохранённого исследовательского артефакта. Один раунд `integrate_once.py --apply` успешно записан; подтверждённых числовых замен **0**, денежный эффект фактических находок **0 рублей**. FINAL означает закрытие раунда, не достоверность отсутствующих данных. [Реестр](findings_admission.csv), [package](final_integration_package.json), [receipt](model/final_round/integration_receipt.json) сохраняют эту границу. Первый вызов остановился на дополнительных колонках CSV без receipt; совместимая проекция сохранила квалификации, второй записал единственный раунд. Исходные baseline и snapshots не переписаны; рейтинг, веса, owner и публичная панель не изменены.

Для последнего уточнения выбраны пять пробелов, от которых зависит решение: зимний endpoint OD, достигнутый net yield, состав цены топлива с налогами, защищённый пересадочный продукт и доступный ресурс с полным бюджетом. Первые два определяют доход; третий проверяет сопоставимость затрат; последние два отделяют математическую программу от продаваемого и выполнимого продукта. Нового поиска и обращений к команде здесь не было. Остальные UNKNOWN зафиксированы, дополнительных исследовательских раундов не предполагается.

[Итоги Кольцово](https://ar-svx.ru/about/news/razvitie-infrastruktury-novye-servisy-i-rost-passazhiropotok/) от 19.01.2026 подтверждают старые округлённые 211 тыс. SVX–MRV и 785 тыс. SVX–AER за 2025 год. [Январская публикация](https://ar-svx.ru/about/news/v-yanvare-passazhiry-koltsovo-chashche-vsego-letali-otdykhat/) от 07.02.2025 даёт около 16 тыс. двусторонних движений SVX–MRV–SVX за январь 2025; >49 тыс. AER — вспомогательный контекст. Надёжность высокая для опубликованных агрегатов, применимость к декабрьскому OD отсутствует. [Рыночный FINAL](research/market_final.md) сохраняет 14/16 плановых вылетов из индексированного расписания; год неявный, выполнение неизвестно. Котировки с одинаковой корзиной на 7/11 декабря не получены; розничная gross-цена всё равно не достигнутый RW net yield.

[Стоимостный FINAL](research/costs_final.md) фиксирует непрочитанные PDF и неизвестную конкретную субсидию RW UFA–NJC. Числа 133200, 136300, 1696 и аэропортовые сборы остаются REFERENCE_ONLY; даты начала и exVAT — утверждения сохранённого реестра, не перепроверенные декабрьские договоры. Арифметика точна: 133200+1696=134896, 136300+1696=137996. [Проверка owner-формулы](owner_fuel_formula_check.json) показывает однократное умножение на объединённые 134896; дополнительного uplift в этой формуле нет. Разница ценовых основ сама по себе не ошибка. Второго снятия НДС не выполнялось; возмещаемость неизвестна.

Все 12 baseline вкладов остаются отрицательными до fleet/base/opportunity. Внутри недели UFA-программы сжаты на 7–8 декабря, D — на 7–12; это авторские датированные legs, не опубликованное расписание. В base C порядок по величине вклада: H_UFA4, D_SVX8, H_UFA8; в base N: D_SVX8, H_UFA4, H_UFA8. В cautious обе рецептуры сохраняют порядок H_UFA4, D_SVX8, H_UFA8; вклады C равны −15.163/−17.737/−28.166 млн рублей, N −13.132/−13.849/−25.092 млн. Это сравнение фиксированных предложений, не выбор оптимальной сети. [Все денежные статьи](model/baseline_comparison.csv) и [повтор](model/final_round/integration_comparison.csv) доступны без округления.

Отдельная **авторская** чувствительность задаёт общую base-основу 133200+1696 для всех flown legs трёх сетей и обоих C/N. Локальная находка UFA не переименована в общесетевую ставку: adapter требует ALL_FIXED_FLOWN_LEGS, поэтому реестр не применяет её, а [отдельный bridge](price_scenario_bridge.json) переводит total134896−uplift1696 в commodity133200. Это проверка модельных чисел, не принятый контракт. Изменяется только flight cost; cautious, места, частоты, спрос, fares, capture, migration и allocator сохраняются.

Млн рублей за модельную неделю; последний столбец — доля исходного дефицита, закрытая снижением стоимости:

| Сеть / рецепт | Baseline | Улучшение | После | Дефицит закрыт |
|---|---:|---:|---:|---:|
@@TABLE@@

Знак и порядок не меняются. [Расчёт](price_sensitivity.csv) содержит остаточный дефицит, отношение дефицита к улучшению, тоннаж и затраты; [плечи](price_sensitivity_legs.csv) показывают однократный uplift. Эффект заметно меньше исходного дефицита каждой строки.

Порог α=0.6835090019901081 сохранён только для исходного base: каждый endpoint D=(1−α)C+αN, те же dated supply, fares, capture, migration/caps, local-first и внутригрупповая сортировка. Это равенство D_SVX8/H_UFA4 при −3.168101768 млн рублей, не сезонность, доля трансфера, вероятность или прибыль. C/base H_UFA4 demandscale=2.4617708803940044 обнуляет только вклад при одновременном масштабировании всех C endpoint рынков и исходных затратах. Оба порога зависят от allocator/сети; полный PnL требует исключённых расходов. При новой цене они **не пересчитаны**, старый α на неё не переносится. [Точные квалификации](model/scenario_thresholds.csv).

Аэропортовый поток, пассажиры сегментов, endpoint поездки и пересадки различаются. Одна двухплечевая поездка получает тариф один раз и занимает два кресла-сегмента; segment_pax=sold_journeys+transfer_journeys. Own-RW migration не новые пассажиры: net_new=sold−migrated, потерянный старый доход уже вычтен. C — недельный авторский сценарий; N — annual/104 proxy в обоих сценариях. Owner54cd с 52/48 модельными неделями — отдельный годовой контур; common неделю нельзя умножать на 52 как фактический год.

[Уфа](https://www.airportufa.ru/en/scoreboard/transfer/) описывает недатированную процедуру 1–4 часа при through-check-in, не RW MCT или защищённую продажу. C01/C07/C08 остаются UNKNOWN. FullPnL, peakcash, доступный парк и договоры — NULL/UNKNOWN. [Owner handoff](owner_handoff_final.csv) передаёт конкретные поля: commodity/uplift/total и налоги; annual/proxy и срок конкурентных источников; protected product/MCT; статусы субсидии, базы, lease, crew/MRO и ресурса. Нужны закрытые OD/билетные выгрузки, счета/договоры, подписанный award, ротации и датированный incremental budget, без запросов владельцам сейчас.

Рекомендация по запуску не меняется: представленные числа не обосновывают запуск или пилот ради меньшего отрицательного вклада. Они также не доказывают убыточность любого хаба. [Validation](final_validation.json) проверяет денежные тождества, сохранность всех 64 legs и пассажиров, 50 хешированных ID, единственный детерминированный повтор и 7 protected hashes. Проверка ограничена fixed ledger, не внешней достоверностью спроса или эксплуатацией. Offline: `python3 context/24_network_followup_20261110/model/finalize_integration.py --verify`. Повторный apply и baseline builders для воспроизведения не запускать.
'''


def html_text(rows):
    # The visual is generated only from computed rows. All units are RUB/model week.
    base = [r for r in rows if r['scenario']=='base']
    sections=[]
    colors={'D_SVX8':'var(--blue)','H_UFA_4':'var(--green)','H_UFA_8':'var(--purple)'}
    for sc,title in [('base','Base · исходная цена'),('cautious','Cautious · без изменения')]:
        group=[r for r in rows if r['scenario']==sc]
        scale=30
        bars=''
        for n in NAMES:
            rr=[r for r in group if r['network']==n]
            bars+=f'<div class="barrow"><b>{n.replace("H_UFA_","H_UFA")}</b><div>'
            for r in rr:
                width=(-r['before_contribution']/1e6)/scale*100
                bars+=f'<div class="track"><span class="bar" style="width:{width:.3f}%;background:{colors[n]}"></span><span class="bartext">{r["recipe"]} {money(r["before_contribution"])} млн</span></div>'
            bars+='</div></div>'
        sections.append(f'<section><h2>{title}</h2><p class="muted">Вклад до fleet/base/opportunity · млн ₽ / модельную неделю</p>{bars}</section>')
    table=''.join(f'<tr><td>{r["network"].replace("H_UFA_","H_UFA")} / {r["recipe"]}</td><td>{money(r["before_contribution"])}</td><td class="positive">+{money(r["delta_contribution"],6)}</td><td>{money(r["after_contribution"])}</td><td>{r["improvement_pct_of_initial_deficit"]:.2f}%</td></tr>' for r in base)
    return '''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Финальная интеграция: фиксированные сети</title><style>
:root{--text:#20272c;--muted:#616e77;--line:#dbe2e6;--panel:rgba(128,145,155,.055);--blue:#597cac;--green:#508c7c;--purple:#9476a1;--accent:#237664;--warn:#8b6228;--radius:12px;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--text);color-scheme:light dark}
@media(prefers-color-scheme:dark){:root{--text:#e4e9eb;--muted:#a5b1b9;--line:#3b464e;--panel:rgba(152,173,187,.07);--blue:#7399cc;--green:#71b39d;--purple:#b194bf;--accent:#80cdb4;--warn:#dab47e}}
*{box-sizing:border-box}html,body,.outer{background:transparent;margin:0;padding:0}body{font-size:13px;line-height:1.48}.outer{width:100%;max-width:728px;margin:0 auto}h1{font-size:25px;line-height:1.18;margin:0 0 9px;font-weight:730;letter-spacing:-.45px}h2{font-size:16px;margin:0 0 5px}p{margin:5px 0 10px}.muted{color:var(--muted);font-size:12px}.lead{font-size:14px}.statline{display:flex;gap:9px;flex-wrap:wrap;margin:13px 0 17px}.stat{flex:1;min-width:130px;border:1px solid var(--line);border-radius:var(--radius);padding:11px}.stat b{display:block;font-size:24px;line-height:1.1}.stat span{font-size:11px;color:var(--muted)}section{border-top:1px solid var(--line);padding:15px 0 10px}.barrow{display:grid;grid-template-columns:78px 1fr;gap:9px;margin:10px 0}.barrow>b{font-size:11px;padding-top:7px}.track{height:25px;position:relative;margin:3px 0;background:var(--panel);border-radius:4px;overflow:hidden}.bar{height:100%;display:block;opacity:.34}.bartext{position:absolute;inset:3px 8px;font-variant-numeric:tabular-nums;font-size:12px}.note{border-left:3px solid var(--warn);padding:2px 10px;margin:10px 0;color:var(--muted);font-size:12px}.tablewrap{overflow:auto}table{border-collapse:collapse;width:100%;font-size:12px;font-variant-numeric:tabular-nums;white-space:nowrap}th,td{text-align:right;padding:8px 4px;border-bottom:1px solid var(--line)}th:first-child,td:first-child{text-align:left}th{font-size:10px;color:var(--muted);font-weight:600}.positive{color:var(--accent)}.chartgrid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.card{background:var(--panel);padding:10px;border-radius:8px;font-size:12px}.card b{display:block;margin-bottom:4px}.actions{margin:7px 0;padding-left:20px}.actions li{padding:3px 0}.foot{font-size:11px;color:var(--muted);padding:10px 0 0}a{color:inherit;text-decoration-color:var(--line)}@media(max-width:480px){h1{font-size:23px}.stat{min-width:90px;padding:8px}.stat b{font-size:21px}.chartgrid,.grid{grid-template-columns:1fr}.barrow{grid-template-columns:70px 1fr}.outer{width:100%}th,td{padding:7px 3px;font-size:11px}}
</style></head><body><main class="outer"><h1>Находки уточнили границы.<br>Экономический вывод сохраняется.</h1><p class="lead">7–13 декабря 2026 · D_SVX8 / H_UFA4 / H_UFA8<br>C — недельный сценарий. N — annual/104 proxy, не наблюдённый зимний OD.</p><div class="statline"><div class="stat"><b>50 / 50</b><span>ID с admission и source hash</span></div><div class="stat"><b>0 ₽</b><span>эффект фактических находок</span></div><div class="stat"><b>64 legs</b><span>фиксированы · 100 мест/leg</span></div></div>''' + '<div class="chartgrid">'+''.join(sections)+'</div>'+  '''<section><h2>Отдельно: общая авторская цена топлива</h2><p>Только base: <b>137996 → 134896 ₽/т</b> = commodity <b>136300 → 133200</b> + неизменный uplift <b>1696</b>. На всех legs и обоих C/N.</p><div class="note">SCENARIO_ONLY · UFA reference не принят как реальная цена всей сети. Bridge: total134896 − uplift1696 = commodity133200. Cautious сохранён; authoritative baseline не изменён.</div><div class="tablewrap"><table><thead><tr><th>Сеть / рецепт</th><th>До, млн ₽</th><th>Δ вклад, млн ₽</th><th>После, млн ₽</th><th>Дефицит<br>закрыт</th></tr></thead><tbody>''' + table+ '''</tbody></table></div><p class="muted">Δ затрат = −Δ вклада. Места, частоты, пассажиры, спрос, net fare, own migration и allocator те же. Все вклады отрицательны; порядок сетей сохраняется.</p></section><section><h2>Что источники устанавливают</h2><div class="grid"><div class="card"><b>Рынок · исторический контекст</b><a href="https://ar-svx.ru/about/news/razvitie-infrastruktury-novye-servisy-i-rost-passazhiropotok/">2025: MRV 211 тыс., AER 785 тыс.</a> Надёжно для агрегата. Январь 2025: MRV ≈16 тыс. двусторонне. 14/16 — опубликованный план с неявным годом, не выполнение. Котировки 7/11 декабря и achieved yield UNKNOWN.</div><div class="card"><b>Расходы и эксплуатация</b>PDF ставок повторно не прочитаны; конкретный RW subsidy UNKNOWN. Owner134896 уже включает uplift, формула не повторяет его. <a href="https://www.airportufa.ru/en/scoreboard/transfer/">UFA 1–4 ч</a> — undated процедура при through-check-in, не RW MCT. C01/C07/C08 не приняты.</div></div></section><section><h2>Два прежних порога — только при исходных условиях</h2><p><b>α = 0.683509</b>: интерполяция каждого C↔N endpoint D при base уравнивает D_SVX8 и H_UFA4 на <b>−3.168102 млн ₽</b>. <b>C/base H_UFA4 ×2.461771</b>: нулевой вклад при масштабировании всех C рынков.</p><p class="muted">Те же fixed supply, fares/capture/migration, local-first и сортировка; без F/B/donor. Это не сезонность, трансферная доля или полный PnL; нельзя переносить на другой allocator/сеть. Для новой цены пороги не пересчитаны.</p></section><section><h2>Пять конкретных передач владельцу</h2><ol class="actions"><li>Разделить fuel commodity / uplift / total; добавить налоговую базу, даты и область договора.</li><li>Получить закрытые winter endpoint OD и net ticket yield; отметить annual/104 proxy и 52/48 owner отдельно.</li><li>Добавить конкурентам URL, срок, год и plan/performed; не считать offer платным спросом.</li><li>Закрыть protected sale, RW MCT/багаж и датированные ротации; C01/C07/C08 остаются gates.</li><li>Подтвердить award, базу, lease/crew/MRO, named tails и incremental budget/cash. FullPnL/peakcash — NULL.</li></ol></section><p class="foot">Одна through-поездка: один тариф и два занятых сегмента. Own-RW migration не новые пассажиры; старый доход уже вычтен. Неделю не умножаем на 52 как фактический год. Эти числа не обосновывают запуск или пилот ради меньшего убытка и не доказывают убыточность любого хаба. Один apply; replay и 7 protected hashes проверены. Данные: baseline_comparison.csv, price_sensitivity.csv; полный handoff: owner_handoff_final.csv. Рейтинг/веса не менялись.</p></main></body></html>'''


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--prepare',action='store_true')
    g.add_argument('--report',action='store_true')
    g.add_argument('--verify',action='store_true')
    a=p.parse_args()
    if a.prepare: prepare()
    elif a.report: report()
    else: verify()
