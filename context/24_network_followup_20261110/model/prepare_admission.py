#!/usr/bin/env python3
"""Create first-pass admission ledgers and the one-round integration package."""
import csv
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
from build_baseline import HERE, OUT, METHODS, CONTEXT, RUN, read_csv, write_csv, write_json, sha256

FIELDS = ['finding_id', 'researcher_id', 'claim', 'admission_status', 'apply', 'model_parameter',
          'network', 'scenario', 'recipe', 'pair', 'value', 'source_url', 'source_artifact', 'source_sha256',
          'source_period_start', 'source_period_end', 'source_unit', 'source_tax_basis',
          'model_period_start', 'model_period_end', 'model_unit', 'model_tax_basis',
          'source_kind', 'source_scope', 'carrier', 'conversion', 'condition', 'reliability', 'rejection_reason']
COST_UNITS = {
    'fuel_t_per_hour': 't/block_hour', 'fuel_t_per_cycle': 't/flight_cycle',
    'fuel_rub_per_t': 'RUB/t_excluding_uplift', 'fuel_uplift_rub_per_t': 'RUB/t_uplift_only',
    'mro_rub_per_hour': 'RUB/block_hour', 'crew_rub_per_hour': 'RUB/block_hour',
    'navigation_rub_per_hour': 'RUB/block_hour', 'airport_factor': 'dimensionless_airport_basket_multiplier',
    'deicing_probability': 'probability_per_flown_leg', 'deicing_operation_rub': 'RUB/deicing_operation',
    'pax_cost': 'RUB/occupied_segment'}
TAX = 'EX_RECOVERABLE_VAT_AS_AUTHOR_SCENARIO'
PERIOD = {'start': '2026-12-07', 'end': '2026-12-13'}


def main():
    admission = []
    for row in read_csv(RUN / 'demand_mapping.csv'):
        for recipe, parameter, status in [('C', 'C_week_direction', 'scenario_only'), ('N', 'N_week_direction_stress', 'proxy')]:
            admission.append(dict(finding_id=f"BASE_{row['network']}_{row['scenario']}_{row['pair']}_{recipe}",
                parameter='weekly_demand', network=row['network'], scenario=row['scenario'], recipe=recipe, pair=row['pair'],
                value=row[parameter], source='source_snapshot/methods/runs/common_demand_v1/demand_mapping.csv',
                source_commit='a77e4cfbd14e560d26407479b7252cfcb15f4f41',
                source_period='2026-12-07/2026-12-13 scenario' if recipe == 'C' else row['N_period'] or 'UNSPECIFIED_MODEL_SCALE',
                source_unit='endpoint_journeys/week/direction scenario' if recipe == 'C' else 'annual_pair_flow_proxy_both_directions; source grain=' + row['N_coverage'],
                model_period='2026-12-07/2026-12-13', model_unit='endpoint_journeys/week/direction', tax_basis='NOT_APPLICABLE_QUANTITY',
                admission_status=status, conversion='none; frozen weekly scenario' if recipe == 'C' else 'Nannual/104 in BOTH scenarios; explicit source-grain/season proxy, not observed winter OD',
                reliability='EXACT_ARTIFACT_HIGH; real endpoint winter demand unvalidated',
                permitted_change='same endpoint pair and weekly direction; source period/grain retained; proxy/scenario label compulsory unless observed winter endpoint OD',
                not_permitted='airport total/route segments/offer seats as paid endpoint demand; N denominator 96; automatic new-owner OD substitution'))
    config = json.loads((CONTEXT / '15_team_update/model/configuration.json').read_text())
    for sc, p in config['scenarios'].items():
        for parameter, unit in COST_UNITS.items():
            admission.append(dict(finding_id=f'BASE_COST_{sc}_{parameter}', parameter=parameter, network='ALL', scenario=sc, recipe='ALL', pair='',
                value=p[parameter], source='source_snapshot/context21/context/15_team_update/model/configuration.json', source_commit='93fa5cf4a10ab67e05c93d19fc5375fc58ef9299',
                source_period='frozen scenario as_of 2026-11-09', source_unit=unit, model_period='2026-12-07/2026-12-13', model_unit=unit,
                tax_basis=TAX, admission_status='scenario_only', conversion='none', reliability='EXACT_AUTHOR_SCENARIO; applicability/net tax basis unverified externally',
                permitted_change='same parameter/unit on every flown leg; same C/N and all three networks within scenario; isolate fuel vs uplift and airport basket vs deicing',
                not_permitted='double VAT/uplift/handling; uniform actual tariff claim from a single-airport quote'))
    entries = [
        ('FARE', 'fare_once_net', 'scenario_only', 'RUB/endpoint_journey', 'original net fare scenario, not retail quote or achieved yield', 'same pair, both directions and both C/N; keep foregone old-RW fare independent; reorder same local-first allocator'),
        ('SUPPLY', 'dated_legs/100_seats/1_2_4_working_plus_conditional_reserve', 'scenario_only', 'dated_leg/seat/model_aircraft', 'frozen dated ledger, not available physical fleet', 'not mutable in final round; material supply changes require separate study'),
        ('MIGRATION', 'can/known_direct_capacity/oldfare/old_segments', 'scenario_only', 'journey/week/direction; RUB/old_journey; segments', 'author direct cap + unverified own connecting migration', 'not mutable automatically; preserve old-RW deduction, avoid donor double count'),
        ('AIRPORT_TOTAL', 'weekly_demand', 'rejected_missing_scope', 'airport_total', 'aggregation includes other routes/transfers, not endpoint OD', 'context only until a scoped OD allocation is supplied'),
        ('OFFER', 'weekly_demand', 'rejected_missing_scope', 'published_departures/seats', 'offer quantity is not paid demand', 'can constrain alternative schedule/capture scenarios only; no direct demand replacement'),
        ('RETAIL', 'fare_once_net', 'scenario_only', 'gross_retail_quote', 'quote needs two dates/basket/carrier/taxes; not achieved RW net yield', 'explicit net reconciliation and scenario label; no direct_input from retail'),
        ('OWNER_OD', 'weekly_demand', 'rejected_missing_scope', 'owner_OD_model', 'new owner OD module is not an automatic networkmoney input', 'new exact export and scoped admission necessary; frozen N matrix retained'),
        ('OWNER_ANNUAL', 'common_weekly_money', 'rejected_missing_scope', 'RUB/year;52_base_48_cautious_model_weeks', 'different supplies/periods/allocator', 'keep static annual owner audit separate'),
        ('EXCLUDED', 'F/B/support/start/exit/donor/cash', 'rejected_missing_scope', 'incremental_RUB_and_dated_cash', 'actual amounts UNKNOWN; no zero factual default', 'separate named incremental/full budget ledger required'),
        ('C01', 'proposal_gate', 'rejected_missing_scope', 'protected_dated_itinerary', 'NJC>UFA>MRV MCT/rotation/product not accepted', 'keep separate gate from H_UFA_4'),
        ('C07', 'proposal_gate', 'rejected_missing_scope', 'dated_rotation', 'SVX>OMS>KJA>OMS>SVX next assignment not accepted', 'no automatic operating program or donor assignment')]
    for key, parameter, status, unit, rationale, allowed in entries:
        admission.append(dict(finding_id=key, parameter=parameter, network='ALL', scenario='ALL', recipe='ALL', pair='', value='',
            source='frozen model/handoff; no new external research', source_commit='', source_period='see frozen source metadata', source_unit=unit,
            model_period='2026-12-07/2026-12-13', model_unit=unit, tax_basis=TAX if key in ('FARE', 'RETAIL') else 'SEPARATE_OR_NOT_APPLICABLE',
            admission_status=status, conversion='NONE_AUTOMATIC', reliability=rationale, permitted_change=allowed, not_permitted='automatic upgrade or factual zero for UNKNOWN'))
    write_csv(HERE / 'input_admission.csv', admission)
    write_csv(HERE / 'input_admission_template.csv', [], FIELDS)
    gaps = [
        ('OD', 'closed/paid winter endpoint OD, same direction/period', 'UNKNOWN', 'weekly_demand only with unit/period/pair admission; otherwise proxy/scenario', 'demand', 'all three fixed networks'),
        ('YIELD', 'achieved RW net through fare and old RW opportunity fare', 'UNKNOWN', 'retail quote only scenario; fare once, oldfare separate', 'product', 'RUB/endpoint journey; explicit taxes/basket'),
        ('FLEET', 'named available tail/type/payload/crew/MRO/reserve location', 'UNKNOWN', 'no fixed-supply edits or donor assignment in final adapter', 'operations', '100-seat author scenario is not physical acceptance'),
        ('FREQUENCY', 'published/performed operations for exact dated legs', 'UNKNOWN', 'offer evidence cannot be paid demand', 'operations', 'same week; route-pair and direction, no deduplication errors'),
        ('TAX_COST', 'applicable airport/fuel/pax cost and recoverable VAT treatment', 'UNKNOWN', 'same units; fuel/uplift and fees/deicing separated; symmetrical all flown legs', 'cost', 'do not generalize one quote to all legs as fact'),
        ('F_B', 'incremental fleet/base/support', 'UNKNOWN', 'separate nonzero or sourced zero incremental costs', 'budget', 'not already variable line items'),
        ('START_EXIT', 'incremental start/exit recognition and dates', 'UNKNOWN', 'separate PnL and gross cash timing', 'budget', 'not a weekly zero default'),
        ('DONOR', 'named KEEP/CANCEL/REPLACE commitments and external delta', 'UNKNOWN', 'avoid double counting foregone own RW already deducted', 'budget', 'OMS/REN model losses do not identify donors'),
        ('CASH', 'dated gross receipts/payments/deposits/capex/financing', 'UNKNOWN', 'peak cash NULL until closed dated ledger', 'budget', 'not contribution or annual net money'),
        ('C01', 'NJC>UFA>MRV MCT/turn/dated rotation/protected product', 'HOLD', 'independent proposal gate; no automatic H_UFA_4 acceptance', 'operations', 'single itinerary seats on both legs'),
        ('C07', 'SVX>OMS>KJA>OMS>SVX next assignment', 'HOLD', 'independent gate; fixed common supply retained', 'operations', 'not auto-accepted program'),
        ('RESEARCH', 'final evidence packages from three research agents', 'NOT_INTEGRATED', 'exact one final targeted round; no wait/poll/unfinished ingestion', 'integrator', 'use finalized manifests and one row per finding'),
        ('REPLAY_LIMIT', 'source demand/operating/full-network-generation replay', 'NOT_PERFORMED', 'fixed-ledger arithmetic alone verified; no full model/operating claim', 'integrator', 'latest methods source from exact MCP, not local git-show')]
    write_csv(HERE / 'gap_map.csv', [dict(gap_id=i, required=r, state=s, integration_rule=a, scope_owner=o, unit_scope=u) for i,r,s,a,o,u in gaps])
    handoff = []
    for sc, p in config['scenarios'].items():
        for parameter in COST_UNITS:
            handoff.append(dict(what='conditional shared variable-cost update', file_parameter=f'common.scenarios.{sc}.{parameter}',
                                before=p[parameter], after=p[parameter], condition='NO_CHANGE_FIRST_PASS; final source/unit/tax admission; every flown leg and both C/N symmetric',
                                source='exact93fa configuration; no new research integrated', reliability='author scenario only', status='BASELINE_RETAINED'))
    handoff += [
        dict(what='N annual-to-directed-week proxy', file_parameter='common.recipe_N.denominator', before=104, after=104,
             condition='BOTH common scenarios retain /104; not winter observed OD; owner cautious /96 is different model',
             source='exacta77 common_demand_contract.json', reliability='exact recipe; demand applicability proxy', status='BASELINE_RETAINED'),
        dict(what='current owner annualization', file_parameter='owner_snapshot/data/assumptions/network.csv:weeks_per_year', before='base52/cautious48', after='base52/cautious48',
             condition='owner files unchanged; no substitution into common week', source='exact54cddfa network.csv', reliability='exact author assumptions', status='SEPARATE_CONTOUR'),
        dict(what='achieved net fare', file_parameter='common.offers[pair].fare_once and oldfare separately', before='frozen net scenarios', after='frozen net scenarios',
             condition='RW realized net evidence or explicit retail-to-net scenario; fare once; old migration fare not automatically changed', source='exact93fa sales.csv', reliability='scenario, not achieved yield', status='PENDING_FINAL_ADMISSION'),
        dict(what='excluded incremental budget', file_parameter='full_budget.F/B/support/start/exit/external_donor_delta/cash', before='UNKNOWN/NULL', after='UNKNOWN/NULL',
             condition='named incremental source and dated cash; no factual zero or automatic OMS/REN donor', source='exacta77 handoff and frozen config', reliability='unknown actual amounts', status='NOT_INTEGRATED'),
        dict(what='network and operating resource', file_parameter='freeze/network_contract.json;dated_legs.csv', before='D_SVX8/H_UFA4/H_UFA8;1/2/4 working + conditional1 reserve', after='SAME_FIXED_SUPPLY',
             condition='no new network selection; physical tail/type/dispatch acceptance remains UNKNOWN', source='exact93fa dated ledger; exacta77 common supply', reliability='model supply only', status='FROZEN')]
    write_csv(HERE / 'owner_handoff.csv', handoff)
    contract = dict(schema_version=1, status='BASELINE_ONLY_ADAPTER_READY_NOT_EXECUTED', final_round_limit=1,
        baseline_sha256=sha256(HERE / 'baseline_comparison.csv'), network_contract_sha256=sha256(HERE / 'network_contract.json'), source_manifest_sha256=sha256(HERE / 'source_manifest.json'),
        permitted_networks=['D_SVX8','H_UFA_4','H_UFA_8'], permitted_scenarios=['base','cautious'], recipes=['C','N'],
        fixed_period=PERIOD, model_tax_basis=TAX, supported_cost_parameters=COST_UNITS,
        supported_other_parameters={'weekly_demand':'endpoint_journeys/week/direction','fare_once_net':'RUB/endpoint_journey'},
        finding_fields=FIELDS, admission_statuses=['direct_input','proxy','scenario_only','rejected_missing_scope'],
        researcher_manifest_schema={'researcher_id':'same as package','status':'FINAL','finding_ids':'all finding IDs for this agent, possibly empty'},
        package_path_resolution='all paths relative to OUT; resolved paths must remain inside OUT; sources bound by SHA-256',
        readiness='three exact finalized manifests and complete findings enumeration required; no automatic polling or unfinished ingestion',
        demand_rule='only existing endpoint pairs; directed-week model unit; annual source retains explicit proxy conversion; never airport total/offer as direct demand',
        fare_rule='pair and both recipes; fare_once_net changes new fare only; old-RW fare frozen; retail quote scenario_only after explicit tax/basket reconciliation',
        shared_cost_rule='ALL networks and ALL recipes within scenario; common factor applied to every dated flown leg; no double uplift/handling/VAT; no individual unscoped quote upgraded to global actual cost',
        excluded_from_adapter=['fleet/base/support/start/exit/donor/cash', 'capture/migration policy', 'supply/aircraft/capacity/frequency', 'allocator', 'network selection','ranking'],
        effect='creates separate final_round sensitivity and owner handoff; immutable baseline and owner/src untouched',
        receipt='final_round/integration_receipt.json; second applied round refused', dry_run='validates and computes without writing or spending final-round receipt',
        run='python3 context/24_network_followup_20261110/model/integrate_once.py --package <OUT-relative package.json> [--apply]')
    write_json(HERE / 'integration_contract.json', contract)
    package = dict(schema_version=1, round='FINAL_TARGETED_INTEGRATION', ready=False, all_findings_enumerated=False,
                   baseline_sha256=contract['baseline_sha256'], network_contract_sha256=contract['network_contract_sha256'],
                   researchers=[dict(researcher_id=i, status='PENDING', manifest_path='', manifest_sha256='') for i in ('demand','product_operations','cost_budget')],
                   findings_csv='', findings_sha256='', finding_count=None)
    write_json(HERE / 'final_integration_package.template.json', package)
    print(json.dumps(dict(status='BASELINE_ONLY', admission_rows=len(admission), future_findings_integrated=0, gap_rows=len(gaps), final_round_executed=False)))

if __name__ == '__main__':
    main()
