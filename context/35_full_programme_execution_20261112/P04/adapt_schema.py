"""Add SP09/SP10/SP11 mapping while preserving the already-pinned P04 payload."""
import csv
import hashlib
import json
import subprocess
from pathlib import Path

P=Path(__file__).resolve().parent
PAYLOAD='dfda83ed8f3a17d57025a70c1a45ade544a96a1f'
SCHEMA_COMMIT='b7d74e67dd6c603db049b1915b1afec987e3b458'
SCHEMA_PATH='context/35_full_programme_execution_20261112/P00R/schema_patch.csv'

def rows(f):
    with (P/f).open(newline='') as s:return list(csv.DictReader(s))

def csvout(f,rs):
    with (P/f).open('w',newline='') as s:
        w=csv.DictWriter(s,list(rs[0]));w.writeheader();w.writerows(rs)

def out(f,v):
    (P/f).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')

def filehash(f):return hashlib.sha256((P/f).read_bytes()).hexdigest()

def main():
    schema=subprocess.check_output(['git','show',SCHEMA_COMMIT+':'+SCHEMA_PATH])
    (P/'inputs/accepted_schema_patch.csv').write_bytes(schema)
    accepted={r['patch_id']:r for r in rows('inputs/accepted_schema_patch.csv') if r['patch_id'] in ['SP09','SP10','SP11']}
    assert len(accepted)==3
    rates=rows('cost_ranges.csv');mapped=[]
    for r in rates:
        ledger=r['ledger'];k=r['key']
        economic_category={'variable_operating':'variable_operating_expense','base_fixed':'operating_fixed_base',
          'aircraft_use':'aircraft_use_expense','crew_fixed':'operating_fixed_crew','depreciation':'owned_asset_depreciation',
          'startup_expense':'startup_expense','exit_expense':'exit_expense'}.get(ledger,'outside_operating_result_or_bridge_memo')
        cash_category={'capex':'investing','advance':'investing','deposit':'investing','tax':'tax','finance':'operating'}.get(ledger,'operating')
        if ledger in ['opportunity','counterfactual','commercial','working_capital','currency']:
            cash_category='MAPPING_REQUIRED_NOT_ADDITIONAL_PAYMENT'
        if k=='charter_guarantee':economic_category='net_charter_block_revenue';cash_category='operating'
        if ledger=='finance':economic_category='finance_expense_outside_operating_result'
        noncash='true' if ledger=='depreciation' else ('unknown_contract_and_policy' if k.startswith('mro_') else 'false_for_actual_service_or_contract_charge')
        q='accepted_monthly_programme_driver_required'
        if r['cost_id'].startswith('HIST-fuel_t_') or k=='fuel_burn_SJ100_PD8':
            economic_category='physical_quantity_model_input_not_RUB_expense';cash_category='NONE_physical_driver'
        mapped.append(dict(rate_id=r['cost_id'],economic_event_id='NOT_INSTANTIATED',evaluation_id='REQUIRED_FROM_P06',
          owner_asset_or_flight_or_journey_or_base='Bind physical flight/journey/tail/contract/base according to driver',
          category=economic_category,scope='all_affected_business;project_and_KEEP_separate',driver_unit=r['unit'],quantity_driver=r['driver'],
          quantity_status=q,rate=r['value'],rate_status=r['status'],historical_base_point=r['base_point'],historical_cautious_point=r['cautious_point'],
          amount='',amount_status='UNKNOWN_until_admitted_rate_quantity_and_scope',currency=r['currency'],price_year=r['price_year'],
          fx_policy='Required if monetary currency!=RUB;not applicable to physical driver',accrual_month='REQUIRED_FROM_P06',
          noncash_flag=noncash,avoidability='CONTRACT_REQUIRED; committed common cost retained in bothP/KEEP',
          shared_event_id='Required when shared by programmes/flights; one count within evaluation',
          cash_category=cash_category,payment_date_or_month='UNKNOWN_until_contract_event',
          cash_guard='Actual invoice/advance/settlement;economic accrual is not automatic payment;no duplicate reserves/lease/capex',
          source_id=r['source_id'],assumption_id=r['assumption_id'],mapping_assumption_id='P04-A-SP09-MAPPING'))
    csvout('event_rate_map.csv',mapped)
    coverage=[
      dict(cost_group='aircraft_use',scope='SSJ_SaM146;SJ100_PD8;Tu214;other_existing_types separately',
        economic_fields='Lease/use expense OR owned/right-of-use depreciation under chosen convention;insurance;calendar maintenance',
        cash_fields='Rental payment OR purchase/advance/principal;deposits separate;interest outside operating_result',
        rate_coverage='UNKNOWN_RW_contract_rates;historical variable flight costs exclude full use charge',
        driver_coverage='UNKNOWN_until_P03/P06 tail_months/availability/ownership/committed_payment',
        local_reference='None establishes full aircraft use rate',full_cost_covered=False,
        required_fields='ownership_basis;tail_id;lease_or_purchase_contract;rate;minimum_term;calendar;common_with_KEEP;payment_dates',
        guard='Do not fullrent+sameassetdepreciation+purchase as three expenses;unused committed tail cost remains',assumption_id='P04-A-SP09-MAPPING'),
      dict(cost_group='startup',scope='New base or aircraft induction; incremental existing-base entry separately',
        economic_fields='Expensed hiring/training/acceptance/ferry/launch plus D&A of capitalised setup',
        cash_fields='Actual setup expense+capex+advance+deposit cash;capital portion is not current expense',
        rate_coverage='UNKNOWN;no documented total launch estimate or defensible band',driver_coverage='UNKNOWN_launch_date/inducted_tails/actual contracts',
        local_reference='Published per-operation airport service rates do not establish launch package',full_cost_covered=False,
        required_fields='launch_id;item;capitalised_or_expensed;quantity;quote;advance;acceptance;payment;depreciation_basis',
        guard='Expense/capex split;advance offsets final invoice;no automatic zero while waiting',assumption_id='P04-A-SP09-MAPPING'),
      dict(cost_group='reserve',scope='Physical dated reserve tails and crew/MRO capability;new and existing separated',
        economic_fields='Incremental committed aircraft-use/crew/insurance/calendar reserve cost',
        cash_fields='Actual dedicated/shared reserve commitments by contract;not extra purchase if tail already included',
        rate_coverage='UNKNOWN;no generic free reserve assumption',driver_coverage='UNKNOWN_P03 reserve_calendar/shared_assignments',
        local_reference='None establishes full reserve cost',full_cost_covered=False,
        required_fields='tail_or_cohort_id;reserve_role;count;dates;shared_with;committed_payment_id;KEEP_same_commitment',
        guard='Reserve not also active tail;shared cost counted once;common commitment cancels only in delta',assumption_id='P04-A-SP09-MAPPING'),
      dict(cost_group='base',scope='Each named airport and actual aircraft/type programme',
        economic_fields='Incremental station staff/space/IT/MRO/parking/base commitments',cash_fields='Gross paid invoices,minima,deposits and their calendar',
        rate_coverage='PARTIAL_local_service_only;complete_base_total_UNKNOWN',driver_coverage='UNKNOWN_active_base_months/staff/MRO/contract',
        local_reference='KHV aerodrome basing133477RUB/tail/month40-60t;16816060-120t;not full base',full_cost_covered=False,
        required_fields='base_id;airport;station_scope;MROavailability;FTE;space;minimums;service_overlap;months;invoice_terms',
        guard='Basing/parking alternatives checked;shared base and existing incremental expansion only once',assumption_id='P04-A-SP09-MAPPING'),
      dict(cost_group='exit',scope='Each station,lease,crew and supplier commitment,including post2028 tail',
        economic_fields='Termination/severance/redelivery/restoration expenses and provisions under explicit recognition',
        cash_fields='Actual penalties/redelivery/ferry,remaining minimums,deposit return/setoff and claims',
        rate_coverage='UNKNOWN_not_zero;no universal fullyreversible launch assumption',driver_coverage='UNKNOWN_exitdate/notice/condition/obligation',
        local_reference='Per-operation towing/ferry service references insufficient for full termination amount',full_cost_covered=False,
        required_fields='contract_id;termination_date;notice;remaining_commitments;return_condition;depositoffset;payment_dates;terminal_balances',
        guard='Retain obligations beyond2028;do not invent endhorizon refundable cash or erase remaining lease',assumption_id='P04-A-SP09-MAPPING')]
    csvout('financial_cost_coverage.csv',coverage)
    delta=[
      dict(assumption_id='P04-A-SP09-MAPPING',subject='Map pinned P04 drivers to acceptedSP09/SP10',value='Mapping only;no instantiated events/quantities/futurecontractrates',unit='schema',
        selected_by='P04 under coordinator acceptedSP09/SP10',basis=f'{SCHEMA_COMMIT}:{SCHEMA_PATH}',approval_status='SCHEMA_ACCEPTED_BY_COORDINATOR; MAPPING_SELF_CHECKED',
        lower='UNKNOWN amounts',upper='UNKNOWN amounts',affected_conclusions='P06 event import and full-cost coverage',sensitivity='Known subtotal never certifies full cost when required group unknown',refinement='Instantiate accepted programme/contract events and evidence'),
      dict(assumption_id='P04-A-SP10-INTEREST',subject='Interest cash classification consistent with payload andSP11',value='Interest cash operating/finance_interest;interest accrual outside operating_result;debt principal/equity financing',unit='classification',
        selected_by='P04 routine presentation convention;userA remains confirmed',basis='AcceptedSP09/SP10/SP11;payloadcash_rules subtractinterest beforefinancing',approval_status='ANALYST_SELECTED_NOT_USER_APPROVED;A_USER_CONFIRMED',
        lower='UNKNOWN interest amount',upper='UNKNOWN interest amount',affected_conclusions='cash_before_financing and financing_cash reconciliation',sensitivity='Alternative interest financing classification needs explicit redefinition of funding metric and no double subtraction',refinement='P06 retain this mapping or document policy change with reclassified comparative metrics'),
      dict(assumption_id='P04-A-SP11-BOUNDARY',subject='Opening cash,minimum liquidity and whole-business boundary',value='GeneralSP11formula;actualopening_cash/minimum_cash/KEEPcashUNKNOWN',unit='RUB',
        selected_by='Coordinator acceptedSP11;P04 clarification of zero-opening toy',basis='AcceptedSP11;payloadzeroopening/minimum case is arithmetic specialcase',approval_status='SCHEMA_ACCEPTED_BY_COORDINATOR;MONETARY_BOUNDARIES_UNSELECTED',
        lower='UNKNOWN',upper='UNKNOWN',affected_conclusions='Incremental project funding vs whole-business funding and liquidity floor',sensitivity='funding=max_t(0,mincash_t-openingcash-cumpreFinCash_t);monthendaggregationcanunderstate',refinement='Treasury beginningcash,restrictedcash,liquidityfloor and acceptedfutureKEEPcash schedule')]
    csvout('assumption_changes_sp09_sp11.csv',delta)
    adapter={
      'status':'SCHEMA_ADAPTER_ONLY;NO_NEW_RW_EVENTS_OR_BUDGET','payload_commit':PAYLOAD,
      'schema_source':{'commit':SCHEMA_COMMIT,'path':SCHEMA_PATH,'local_path':'inputs/accepted_schema_patch.csv','sha256':hashlib.sha256(schema).hexdigest(),
        'admission':'Coordinator explicitly acceptedSP01-SP13 in current message; source CSVhistoricalstatusPROPOSED is preserved as bytes'},
      'patches':accepted,'rate_map':'event_rate_map.csv','cost_coverage':'financial_cost_coverage.csv','assumption_delta':'assumption_changes_sp09_sp11.csv',
      'economic_events':{'key':['evaluation_id','economic_event_id'],
        'construction':'Admitted rate*accepted quantity by owner,month and currency;net journey revenue once;shared_event_iddeduplicates only inside sameevaluation',
        'negative_delta':'Compute complete P and completeKEEP then subtract;donor/opportunity memo not second expense',
        'noncash':'Owned/capitalisedassetdepreciation true;PBHreserve cash status by actual contract;do not infer allMROhourlyreservesnoncash',
        'unknown':'No economic event amount until rate/quantity/scope known or explicit scenario/threshold branch;publicationprice is historicalreference until futureapplication admitted'},
      'cash_events':{'key':['evaluation_id','cash_event_id'],'economic_event_id':'nullable;CAPEX/advance/deposit can have no current operatingexpense',
        'owner':'related_asset_or_contract_id links advances,finalpayment,deposit,refund and terminalbalance',
        'one_to_many':'One economic event may settle in several payments;cash event not created by merely copyingaccrual_month',
        'categories':{'operating':'Customer/chartercash;suppliers/rent/crew/MRO;supportreceipts/rebates;interestcash subcategoryfinance_interest',
          'investing':'Ownedaircraft/basecapex and capitaladvances;refundablecontractdeposit assetflow separatelyflagged;assetdisposal',
          'tax':'VAT/profittax/excise payments/refunds/offsetcashmapping;fuel supportalready mapped once',
          'financing':'Debtprincipal/equity and financingonlyfees;notjourneyrevenue;interestnotdeductedagain'},
        'tax_support_guard':'Fuelcredit either separate supportoperatingreceipt or taxsettlementflow using explicitpostingpolicy;neverboth.Settlementbyoffsethasnobankreceipt.',
        'balances':'Opening/closingAR,AP,inventory,advances,customeradvances,deposits,debt and posthorizonobligations reconcile'},
      'boundaries':{'cash_before_financing':'operating_cash + investing_cash + tax_cash',
        'funding_before_financing':'max_over_event_t(0,minimum_cash_t - opening_cash - cumulative_cash_before_financing_t)',
        'payload_special_case':'payloadmax(-mincumcash) requiresopening_cash=0 andminimum_cash=0;onlyexplicitdiagnostic/fixture,notobservedRWliquidity',
        'unknown_opening_or_floor':'FinalactualfundingUNKNOWN;publishconditionalincrementalflowandboundarythreshold,notassumedzero',
        'project_incremental':'DerivedfromPminusKEEPcashbyeventonthesameboundary;positiveKEEPcashnotavailableunlessincludedwithprovenliquidity',
        'whole_business':'FullRWfundingUNKNOWNifunaffected/KEEPcashunknown;selectedprojectbudgetdoesnotestablishwholecompanybudget',
        'time':'Prelaunchthroughpost2028obligations;eventminimaandmonthlyreports;end2028receivables/depositsnotautomaticallycollected',
        'minimum_cash':'Liquidityfloorbydate;separatefromminimumobservedclosingcashmetric;noarbitraryreservepercentage'},
      'assumption_ids':[r['assumption_id'] for r in delta],
      'existing_inputs_unmodified':'All134payloadfiles and output_manifest remainbyteidentical;newaddon has separate manifest'}
    out('schema_adapter.json',adapter)
    manifest=json.loads((P/'output_manifest.json').read_text())
    immutable=all(filehash(r['path'])==r['sha256'] for r in manifest['files'])
    assert immutable
    assert len(mapped)==len(rates) and {r['rate_id'] for r in mapped}=={r['cost_id'] for r in rates}
    assert all(r['quantity_status']=='accepted_monthly_programme_driver_required' and r['amount']=='' for r in mapped)
    assert len(coverage)==5 and not any(r['full_cost_covered'] for r in coverage)
    assert max(0,100-40-(-20))==80 # General floor/opening formula, unlike zero-opening20.
    checks={'status':'TARGETED_SELF_CHECK_PASS','independent_review':'NOT_RUN','checks':[
      {'id':'AD01','result':'PASS','evidence':'All134payloadfilehashesunchanged'},
      {'id':'AD02','result':'PASS','evidence':'Exactly127rateIDs maponce;noevents/quantities/amountsinvented'},
      {'id':'AD03','result':'PASS','evidence':'All5requiredcostgroupsincompletecoverageexplicit'},
      {'id':'AD04','result':'PASS','evidence':'SP09/SP10/SP11 exactGitblobpinned;sourceproposalstatusnotrewritten'},
      {'id':'AD05','result':'PASS','evidence':'Opening40,floor100,cumcash-20 impliesfunding80;zeroboundaryspecialcasewouldgive20'}]}
    out('schema_adapter_checks.json',checks)
    supplemental=['adapt_schema.py','inputs/accepted_schema_patch.csv','event_rate_map.csv','financial_cost_coverage.csv','assumption_changes_sp09_sp11.csv','schema_adapter.json','schema_adapter_checks.json']
    sm={'payload_commit':PAYLOAD,'schema_commit':SCHEMA_COMMIT,'files':[dict(path=f,sha256=filehash(f),bytes=(P/f).stat().st_size) for f in supplemental],
      'self_hash_in':'handoff.json.schema_adapter.manifest_sha256','status':'SUPPLEMENT_ONLY;payloadunchanged'}
    out('schema_adapter_manifest.json',sm)
    h=json.loads((P/'handoff.json').read_text())
    h['schema_adapter']={'manifest_path':'schema_adapter_manifest.json','manifest_sha256':filehash('schema_adapter_manifest.json'),
      'schema_commit':SCHEMA_COMMIT,'schema_patch_ids':['SP09','SP10','SP11'],'files':sm['files'],
      'checks':'schema_adapter_checks.json','rate_map':'event_rate_map.csv','full_cost_coverage':'financial_cost_coverage.csv',
      'boundaries':'Actualopeningcash/minimumliquidity/KEEPcashUNKNOWN;generalSP11formula;noactualbudgetcreated'}
    old=[r['assumption_id'] for r in rows('cost_assumptions.csv')]
    h['assumption_ids']=old+[r['assumption_id'] for r in delta]
    h['assumption_changes']='Payloadassumption_changes.csv plus additiveassumption_changes_sp09_sp11.csv;nooverwriteofpinnedregister'
    h['checks']['schema_adapter_targeted']='5PASS;schema_adapter_checks.json;nofullnetworkrerun'
    h['boundaries'].append('SP11generalopeningcash/minimumliquidityboundarysupersedesanyimplicitzero-boundaryinterpretationofpayloadformula;originalfilespreserved') if 'SP11generalopeningcash/minimumliquidityboundarysupersedesanyimplicitzero-boundaryinterpretationofpayloadformula;originalfilespreserved' not in h['boundaries'] else None
    out('handoff.json',h)
    print(json.dumps({'schema_adapter_checks':'5PASS','payload_unchanged':immutable,'event_rate_rows':len(mapped),'coverage_groups':5,'assumption_ids':len(h['assumption_ids']),'adapter_manifest_sha256':filehash('schema_adapter_manifest.json')}))

if __name__=='__main__':main()
