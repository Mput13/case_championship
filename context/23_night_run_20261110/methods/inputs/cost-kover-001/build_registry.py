#!/usr/bin/env python3
"""Publish selected rate provenance and unknown contract terms, without GET."""
import csv
import hashlib
import json
from pathlib import Path
import overlay as o

ROOT, INP = o.ROOT, o.INPUTS


def main():
    params, provenance, reconciliation, ranges, budget = [], [], [], [], []
    source_manifest = json.loads((ROOT / 'source_manifest.json').read_text())
    source_by_name = {Path(x['local_path']).name: x for x in source_manifest['sources']}
    urls = {x['dataset_id']: x for x in o.readcsv(INP / 'core_registry.csv')}
    default = dict(currency='RUB', tax_basis='UNKNOWN', effective_from=None, effective_until=None,
                   known_on=None, price_basis='UNKNOWN', physical_application='UNKNOWN',
                   provenance_type='UNKNOWN', value_status='UNKNOWN', included_in=None,
                   avoidability='UNKNOWN contract terms; no automatic cancellation saving',
                   range_type='NOT_A_STATISTICAL_INTERVAL', missing_reason=None)

    def add(row, file, locator, upstream=None):
        record = {**default, **row}
        params.append(record)
        item = source_by_name.get(file)
        provenance.append(dict(parameter_id=record['parameter_id'], snapshot='inputs/' + file,
                               source_locator=locator, input_file_sha256=item['sha256'] if item else None,
                               source_commit=item.get('source_commit') if item else None,
                               upstream_url=(upstream or {}).get('url'),
                               primary_raw_sha256=(upstream or {}).get('sha256'),
                               primary_raw_verification='INHERITED_PINNED_EXTRACTION; raw not hashed here' if upstream else 'AUTHOR_OR_UNKNOWN_NOT_A_PRIMARY_PRICE',
                               note='No contract rate inferred; original byte-preserved input retained'))

    expense_keys = ['fuel_t_per_hour', 'fuel_t_per_cycle', 'fuel_rub_per_t', 'fuel_uplift_rub_per_t',
                    'mro_rub_per_hour', 'crew_rub_per_hour', 'navigation_rub_per_hour', 'pax_cost',
                    'airport_factor', 'deicing_probability', 'deicing_operation_rub']
    registry = {r['parameter']: r for r in o.readcsv(INP / 'tsiri_cost_registry.csv')}
    for sc in ['base', 'cautious']:
        p, basket = o.parameters(sc)
        for key in expense_keys:
            ref = registry[key]
            add(dict(parameter_id=f'TSIRI:{sc}:{key}', category=key, model='Tsiri', author_scenario=sc,
                     value=p[key], unit=ref['unit'], price_basis=ref['status'],
                     tax_basis='Author net / excluding recoverable VAT; actual recoverability UNKNOWN',
                     physical_application='All model legs by author scenario; fuel source UFA only',
                     provenance_type=('AUTHOR_STRESS' if key == 'fuel_rub_per_t' and sc == 'cautious' else
                                      'LOCAL_PUBLIC_RATE_WITH_NETWORK_SCENARIO_APPLICATION' if key in ['fuel_rub_per_t', 'fuel_uplift_rub_per_t'] else 'AUTHOR_ASSUMPTION'),
                     value_status='AUTHOR_INPUT_NOT_CONTRACT', included_in='flight_variable_cost' if key != 'pax_cost' else 'new_pax_variable per occupied segment',
                     effective_from='2026-11-11' if key in ['fuel_rub_per_t', 'fuel_uplift_rub_per_t'] and sc == 'base' else None),
                'tsiri_cost_registry.csv', key)
        add(dict(parameter_id=f'TSIRI:{sc}:airport_turn_basket', category='airport_services', model='Tsiri',
                 author_scenario=sc, value=basket * p['airport_factor'], unit='RUB/physical departure reference basket',
                 tax_basis='Reference UFA list excludes VAT; network recoverability UNKNOWN',
                 physical_application='UFA reference applied to every physical leg; no local tariff inference',
                 price_basis='49.45t*(553+499)+19300+8100+16668; cautious multiplied 1.2',
                 provenance_type='AUTHOR_REFERENCE_BASKET', value_status='AUTHOR_INPUT_NOT_CONTRACT',
                 included_in='flight_variable_cost once per leg; do not add airport tariffs again'),
            'tsiri_inputs.json', 'reference_basket; stage15 base fuel override kept separately')

    author_keys = {'fuel_t_per_hour', 'fuel_t_per_cycle', 'fuel_rub_per_t', 'mro_rub_per_hour',
                   'crew_rub_per_hour', 'navigation_rub_per_hour', 'ground_rub_per_flight',
                   'deicing_rub_per_flight', 'pax_cost_rub', 'weeks_per_year'}
    for line, r in enumerate(o.readcsv(INP / 'nastya_network.csv'), 2):
        if r['parameter'] not in author_keys:
            continue
        for sc in ['base', 'cautious']:
            add(dict(parameter_id=f'NASTYA:{sc}:{r["parameter"]}', category=r['parameter'], model='Anastasia',
                     author_scenario=sc, value=float(r[sc]), unit=r['unit'], price_basis=r['source'],
                     physical_application='Author network reference; not price discovery at every airport',
                     provenance_type='AUTHOR_INPUT', value_status='AUTHOR_INPUT_NOT_CONTRACT',
                     included_in='author annual network contribution',
                     missing_reason='Tax basis not specified by this table; 48 weeks combines weather and restrictions, not kover downtime' if r['parameter'] == 'weeks_per_year' else 'Author source labels retained as claims; actual contract UNKNOWN'),
                'nastya_network.csv', f'CSV line {line}')

    for line, r in enumerate(o.readcsv(INP / 'primary_ufa_oms.csv'), 2):
        src = urls[r['source_dataset_id']]
        add(dict(parameter_id=f'PUBLIC:{r["source_dataset_id"]}:{r["item"]}', category=r['item'], model=None,
                 airport=r['airport_iata'], value=float(r['value']), unit=r['unit'], tax_basis=r['VAT_basis'],
                 effective_from=r['effective_from'], known_on=r['known_on'], price_basis='Published selected rate, not negotiated RW basket',
                 physical_application=f'{r["airport_iata"]}: {r["scope"]}', provenance_type='PRIMARY_PUBLISHED_RATE_IN_PINNED_EXTRACT',
                 value_status='SOURCE_EXTRACT_INHERITED; not independently visually reviewed in MR02',
                 included_in='Not added to author costs automatically; use as reference or a new named scenario',
                 missing_reason=r['limitations']), 'primary_ufa_oms.csv', f'CSV line {line}; PDF page {r["pdf_page"]}',
            dict(url=src['source_url'], sha256=src['sha256']))

    for line, r in enumerate(o.readcsv(INP / 'khv_cost_components.csv'), 2):
        add(dict(parameter_id=f'PUBLIC:{r["source_id"]}:{r["component_id"]}', category=r['component_id'],
                 model=None, airport='KHV', value=float(r['value']), unit=r['unit'], tax_basis=r['vat_basis'],
                 effective_from=r['effective_from'], effective_until=r['effective_to'] or None,
                 known_on=r['retrieved_at_utc'], price_basis='Published Khabarovsk airport component; separate terminal-company list excluded',
                 physical_application=r['conditions'], provenance_type='PRIMARY_PUBLISHED_RATE_IN_AUTHORISED_PARENT_EXTRACT',
                 value_status=r['temporal_role'], included_in='Not used to replace UFA/network costs',
                 missing_reason=r['limitation']), 'khv_cost_components.csv', f'CSV line {line}; source item {r["source_row"]}',
            dict(url=r['source_url'], sha256=r['source_sha256']))
        provenance[-1]['primary_raw_verification'] = ('RAW_HASH_VERIFIED; MR02 visually checked selected new-PDF page1 values and page7 VAT note; self-check, independent review pending' if r['source_id'] == 'khv_tariff_202611' else 'RAW_HASH_VERIFIED; historical selected row visual review inherited from parent, independent review pending')

    unknowns = [
        ('lease_committed', 'RUB/tail/week', 'Lease commitments and true incremental fleet cost; existing lease not saved by cancellation', 'full_budget'),
        ('crew_fixed_salary', 'RUB/crew/week', 'Salary already allocated versus additional hires; keep ongoing salary', 'full_budget'),
        ('crew_overnight', 'RUB/person/night', 'Crew count, collective terms, hotels and positioning not priced', 'disruption_and_base'),
        ('mro_station', 'RUB/base/week', 'Line-maintenance contract and availability separate from usage reserve', 'full_budget'),
        ('reserve_aircraft_increment', 'RUB/reserve_tail/week', 'Dedicated versus shared reserve and actual incremental lease/crew cost', 'full_budget'),
        ('base_launch_expense', 'RUB/base/launch', 'Which startup items are expensed versus capitalised and when', 'full_budget'),
        ('base_running_increment', 'RUB/base/week', 'Only actual extra commitments; not entire airport tariff list', 'full_budget'),
        ('base_capex', 'RUB/base/launch', 'Capital spending and amortisation schedule', 'cash_capex'),
        ('repositioning', 'RUB/physical_ferry_leg', 'Need, distance, dispatch costs and ending aircraft position', 'transition'),
        ('exit_and_termination', 'RUB/contract_exit', 'Penalties, remaining obligations and recoverable balances', 'transition'),
        ('support_or_subsidy', 'RUB/eligible_journey_or_period', 'Eligibility, awarded route/volume, accrual and collection date; no automatic subsidy', 'support'),
        ('net_fuel_tax_contract_credit', 'RUB/t_fuel', 'RW eligibility and incremental net benefit after accrued tax and supplier rebates; no gross statutory deduction', 'support'),
        ('working_capital_inventory', 'RUB/period_end', 'Actual inventory movements and initial stock', 'cash_only'),
        ('working_capital_receivable', 'RUB/period_end', 'Agency settlements and collection lag', 'cash_only'),
        ('working_capital_payable', 'RUB/period_end', 'Supplier settlement lag and minimum bills', 'cash_only'),
        ('ticket_cash_collection', 'fraction_of_net_fare', 'Actual precollection fraction and gross fare tax basis; fixture fixes fraction=1 only', 'cash_only'),
        ('refundable_deposit', 'RUB/contract', 'Security deposits, refund conditions and timing', 'cash_only'),
        ('refund_gross_tax_cash', 'RUB/affected_endpoint_journey', 'Author net fare is not gross customer refund; actual tax/fees UNKNOWN', 'cash_only'),
        ('vat_recoverability', 'fraction_of_input_VAT', 'Legal application, service type, invoice and actual recoverability not inferred', 'tax'),
        ('compensation', 'RUB/eligible_affected_journey', 'Eligibility, carrier responsibility and contract terms not assumed', 'disruption'),
        ('passenger_hotel_meal', 'RUB/person/day', 'Affected people, nights, meals, service obligations and prices', 'disruption'),
        ('rebooking_paid', 'RUB/reprotected_journey', 'Protected ticket terms and actual alternative seats/fares', 'disruption'),
        ('extra_delay_fuel', 't/physical_operation', 'APU/taxi/holding/ferry cannot be inferred from elapsed delay', 'disruption'),
        ('cancellation_airport_penalty', 'RUB/cancelled_movement', 'Minimum billing, reservations, prepaid services and cancellation terms', 'disruption'),
        ('donor_or_old_RW_restoration', 'journeys/dated_old_itinerary', 'No donor selected. Returning migrants need their own protected inventory and fare/cost bridge', 'counterfactual'),
    ]
    for key, unit, reason, category in unknowns:
        add(dict(parameter_id='UNKNOWN:' + key, category=category, model='RW_actual', value=None,
                 unit=unit, missing_reason=reason, physical_application='Actual candidate/contract/period must be specified'),
            'tsiri_stage16_assumptions.json', 'MR02 explicitly unknown term; no empirical value in permitted inputs')
        budget.append(dict(term=key, value=None, unit=unit, ledger=category,
                           rule=reason, inclusion_guard='Only delta to chosen baseline; do not re-add a component included in flight/pax cost'))
    # Preserve illustrative fixed-cost inputs as author scenarios, not estimates.
    stage16 = json.loads((INP / 'tsiri_stage16_assumptions.json').read_text())
    for key in ['fixed_per_allocated_working_or_reserve_tail_week', 'new_base_week_scenario']:
        add(dict(parameter_id='AUTHOR_FIXED_SCENARIO:' + key, category='fixed_scenario', model='Tsiri',
                 value=stage16[key], unit='RUB/tail/week' if 'tail' in key else 'RUB/base/week',
                 provenance_type='AUTHOR_ILLUSTRATIVE_SCENARIO', value_status='NOT_EMPIRICAL_NOT_APPLIED',
                 physical_application='Stage16 sensitivity; excluded from baseline contribution and MR02 numeric overlay',
                 tax_basis='UNKNOWN', price_basis='Chosen author scenario; methods owns general fixed-budget comparison'),
            'tsiri_stage16_assumptions.json', key)

    reconciliation.extend([
        dict(id='FUEL_BASE_BUNDLE', left='Anastasia fuel_rub_per_t=134896 (133200 product +1696 uplift)', right='Tsiri effective product136300 +1696 uplift =137996', common_unit='RUB/t_fuel before extra unknown contract/tax adjustment', difference=3100,
             application='Same physical tonne can be compared arithmetically; author tax basis and network contracts not established; no baseline overwrite'),
        dict(id='FUEL_CAUTIOUS', left='Anastasia161696 including uplift', right='Tsiri160000+1696=161696', common_unit='RUB/t_fuel author stress', difference=0,
             application='Equal scenario numbers do not confirm an actual market price'),
        dict(id='UFA_FUEL_CURRENT_TARGET_WEEK', left='Public product136300 + published uplift1696', right='137996 if separately billed; storage1353 is not automatic extra', common_unit='RUB/t_fuel ex VAT reference', difference=None,
             application='Effective11Nov before target week7Dec; product/uplift/storage package conditions UNKNOWN'),
        dict(id='UFA_TURN_ROUNDING', left='Anastasia ground96089', right='Tsiri96089.4=49.45*(553+499)+19300+8100+16668', common_unit='RUB/reference_turn', difference=0.4,
             application='Rounding difference only; geographic contract equivalence not established; basket already inside flight cost'),
        dict(id='UFA_PASSENGER_BILLING', left='Public terminal70.5 and domestic passenger service268 per eligible passenger', right='Author pax500/650 per occupied segment; airport basket includes no such realised volume', common_unit='RUB/eligible_passenger versus RUB/occupied_segment', difference=None,
             application='Transfer/arrival/departure exemptions and fare inclusion UNKNOWN; no automatic addition or subtraction of passenger rates'),
        dict(id='MTOW_VERSUS_BURN', left='Airport fees RUB/t_MTOW', right='Fuel RUB/t_fuel times burn_t', common_unit='Different mass bases', difference=None,
             application='MTOW49.45t is a scenario, not uplift51 tonnes; cycle burn0.2/0.25t is separate physical proxy'),
        dict(id='OMS_FLUID_DENSITY', left='TypeI211000 RUB/t', right='TypeIV246 RUB/litre', common_unit='Not convertible without product density and amounts', difference=None,
             application='Alternative fluids; add consumption only if operation and billable quantities specified'),
        dict(id='KHV_REVISION', left='562+445=1007 RUB/t_MTOW in old linked PDF', right='700+609=1309 RUB/t_MTOW in newer linked PDF', common_unit='RUB/t_MTOW ex VAT; same two selected components', difference=302,
             application='At illustrative49.45t: +14933.9 RUB. KHV only; no RW invoice or full-turn inference; source row effective10Feb, not filename month'),
        dict(id='KHVPARKING_ALTERNATIVES', left='25224 RUB/day', right='1051 RUB/hour (24h=25224)', common_unit='Alternative time billing', difference=0,
             application='Do not sum daily and hourly rates, or infer basing133477/month is a complete new-base budget'),
        dict(id='NASTYA48', left='base52 weeks', right='cautious48 weeks combines weather and kover', common_unit='Author annual operating weeks', difference=-4,
             application='Not four kover weeks, not a frequency or probability; no conversion to event duration'),
    ])
    for key, lo, hi, typ, meaning in [
        ('avoidable_cost_share', 0, 1, 'PHYSICAL_FRACTION_BOUND', 'Actual share UNKNOWN; MR02 endpoints are named contract sensitivities'),
        ('unserved_endpoint_journeys', 0, None, 'CONSERVATION_BOUND', 'Upper bound is affected frozen sold journeys, not affected legs times journeys'),
        ('precollected_net_fare_fraction', 0, 1, 'PHYSICAL_FRACTION_BOUND', 'Actual fraction UNKNOWN; cash fixture uses1'),
        ('restriction_duration_hours', 24, 24, 'CONDITIONAL_STRESS_POINT', 'Explicit episode input, not estimated downtime or confidence bound'),
        ('bank_delay_minutes', 1440, 1440, 'CONDITIONAL_STRESS_POINT', 'Chosen next-day bank hypothesis; actual recovery UNKNOWN'),
        ('base_setup_cost', None, None, 'UNKNOWN_CONTRACT_PARAMETER', 'No zero or average substituted'),
        ('compensation_hotel_cost', None, None, 'UNKNOWN_CONTRACT_PARAMETER', 'Conditional eligibility and quantities required'),
        ('fuel_scenario_points', 136300, 160000, 'PUBLIC_LOCAL_REFERENCE_AND_AUTHOR_STRESS', 'Different provenance; not statistical min/max or a market interval'),
    ]:
        ranges.append(dict(parameter=key, lower=lo, upper=hi, range_type=typ, meaning=meaning,
                           confidence_level=None, statistical_interval=False))
    o.writecsv(ROOT / 'cost_parameters.csv', params)
    o.writecsv(ROOT / 'parameter_provenance.csv', provenance)
    o.writecsv(ROOT / 'unit_reconciliation.csv', reconciliation)
    o.writecsv(ROOT / 'range_registry.csv', ranges)
    o.writecsv(ROOT / 'budget_terms.csv', budget)
    print(json.dumps(dict(parameters=len(params), unknown_contract_terms=len(unknowns), unit_reconciliations=len(reconciliation))))


if __name__ == '__main__':
    main()
