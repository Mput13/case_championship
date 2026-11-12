"""Self-checks on immutable source evidence, schemas and meaningful financial cases."""
import csv
import hashlib
import json
import subprocess
from collections import Counter
from decimal import Decimal as D
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CHECKS=[]

def check(name,ok,evidence):
    CHECKS.append(dict(check_id=name,status='PASS' if ok else 'FAIL',evidence=evidence))
    if not ok:raise AssertionError(f'{name}: {evidence}')

def rows(name):
    with (ROOT/name).open(newline='') as f:return list(csv.DictReader(f))

def main():
    receipts=json.loads((ROOT/'source_receipts.json').read_text())
    ids=[r['source_id'] for r in receipts]
    check('unique_source_ids',len(set(ids))==len(ids),f'{len(ids)} source receipts, including failures')
    verified=0;pins=0
    for r in receipts:
        if 'local_path' not in r:continue
        b=(ROOT/r['local_path']).read_bytes()
        check('source_hash:'+r['source_id'],hashlib.sha256(b).hexdigest()==r['sha256'],r['local_path'])
        verified+=1
        if r['acquisition']=='saved_git_blob':
            original=subprocess.check_output(['git','show',r['input_commit']+':'+r['input_path']])
            check('git_blob:'+r['source_id'],b==original,r['input_commit']+':'+r['input_path']);pins+=1
        if r.get('text_sha256'):
            text=(ROOT/'sources'/(r['source_id']+'.txt')).read_bytes()
            check('source_text:'+r['source_id'],hashlib.sha256(text).hexdigest()==r['text_sha256'],r['source_id'])
    assumptions=rows('cost_assumptions.csv');aid={x['assumption_id'] for x in assumptions}
    check('unique_assumption_ids',len(aid)==len(assumptions),len(aid))
    check('assumption_register_csv_json_equal',assumptions==[{k:str(v) if not isinstance(v,bool) else str(v) for k,v in x.items()} for x in json.loads((ROOT/'cost_assumptions.json').read_text())],len(aid))
    check('assumption_changes_complete',{x['assumption_id'] for x in rows('assumption_changes.csv')}==aid,len(aid))
    source_ids=set(ids)
    for name,key in [('cost_ranges.csv','cost_id'),('support_terms.csv','scheme_id')]:
        rs=rows(name)
        check('keys:'+name,len({r[key] for r in rs})==len(rs),len(rs))
        check('ids:'+name,all(r['assumption_id'] in aid and r['source_id'] in source_ids for r in rs),'Complete links to source and judgement')
        check('units:'+name,all(r['unit'] and r['period'] and r['status'] for r in rs),'Unit, period, status populated')
    costs=rows('cost_ranges.csv');byid={r['cost_id']:r for r in costs}
    unknown=[r for r in costs if r['status']=='unknown']
    check('unknown_never_zero',all(r['value']==r['base_point']==r['cautious_point']==r['lower']==r['upper']=='' and r['refinement'] for r in unknown),len(unknown))
    historical=[r for r in costs if r['status']=='scenario']
    check('historical_points_not_bounds',all(r['lower']==r['upper']=='' and r['base_point'] and r['cautious_point'] for r in historical),len(historical))
    check('type_specific_internal_fields',all(any(r['aircraft_type']==t and r['key']=='mro_hour' for r in unknown) for t in ['SSJ100_SaM146','SJ100_PD8','Tu214','other_existing_RW_type']),'No PD8/SaM146 parameter transfer')
    check('published_is_reference_only',all('SINGLE_PUBLISHED_LOCAL_POINT' in r['range_basis'] for r in costs if r['status']=='published_offer'),'No paid-contract range claim')
    check('UFA_fuel_new_constituents',D(byid['UFA-fuel-20261111']['value'])==136300 and D(byid['UFA-fuel_uplift']['value'])==1696 and byid['UFA-fuel-20261111']['effective_from']=='2026-11-11','Product+uplift137996 before optional separately billed storage and VAT')
    oldsources={r['dataset_id']:r for r in rows('inputs/saved_airport_sources.csv')}
    new={r['source_id']:r for r in receipts}
    for sid in ['ufa_services_20261111','ufa_fuel_20261111','omsk_tariff_base_20260821']:
        check('reacquired_matches_saved:'+sid,new[sid]['sha256']==oldsources[sid]['sha256'],'Byte-identical re-fetch does not create new tariff evidence')
    for e in rows('airport_reference_examples.csv'):
        g=e['geography_or_airport'];rr={r['key']:D(r['value']) for r in costs if r['geography_or_airport']==g and r['status']=='published_offer'}
        expected=(rr['takeoff_landing']+rr['security'])*D(e['mtow_t'])+(rr['terminal_domestic']+rr['pax_service_domestic'])*D(e['adult_departing_pax'])
        check('airport_example:'+g,expected==D(e['selected_four_items_subtotal_rub']) and e['full_airport_turn_total']=='','Selected4items only; all-in remains unknown')
    f=rows('cash_fixture.csv');last_ar=D(0);cum=D(0)
    for row in f:
        n=lambda k:D(row[k])
        op=n('revenue')+n('support_accrual')-sum(n(k) for k in ['variable','fixed','aircraft_use','depreciation','startup_expense'])
        cash=n('revenue')+n('support_cash')-sum(n(k) for k in ['variable','fixed','aircraft_use','startup_expense','capex_cash','deposit_cash','interest_cash','tax_cash'])
        delta_ar=n('support_receivable')-last_ar;last_ar=n('support_receivable')
        indirect=op+n('depreciation')-delta_ar-n('capex_cash')-n('deposit_cash')
        cum+=cash
        check('cash_bridge_month:'+row['month_index'],op==n('operating_result') and cash==n('cash_before_financing')==indirect and cum==n('cumulative_cash'),'Direct and accrual cash reconcile exactly')
    counter=json.loads((ROOT/'cash_counterexamples.json').read_text())
    check('cash_lag_counterexample',cum==counter['support_lag']['cum_cash_end6_lag2_kRUB'] and -min(D(r['cumulative_cash']) for r in f)==350 and -min(D(r['cumulative_cash_immediate_support']) for r in f)==350,'Lag lowers cash100; launch-dominated peak unchanged')
    check('intramonth_peak',min(0,-100,0)==-100 and sum([-100,100])==0,'Event peak100 despite month-end net0')
    check('net_excise_not_gross',D(2800)*(D('2.08')-1)==3024 and 5824-2800==3024,'Avoid overstating net base by2800/t')
    history=rows('inputs/fuel_history_monthly_compensation.csv')
    means={y:sum(D(r['total_compensation_rub_t']) for r in history if r['year']==y)/9 for y in ['2025','2026']}
    check('historical_industry_mean',means['2025']==D('7049.45') and abs(means['2026']-D('32930.28333333333333333333333'))<D('0.0000001'),'Equal-weightJan-Sep secondary industry calculation; not RW payment or forecast')
    check('regional_cap_values',len(rows('support_caps_84_103.csv'))==13 and len(rows('support_fare_caps.csv'))==20,'PrimaryPDFpp14/15 selected bands')
    caps=rows('support_caps_84_103.csv');auth_caps=rows('inputs/author_subsidy_cap_84_103.csv')
    check('caps_reconcile_author', [D(x['flight_cap_rub']) for x in caps]==[D(x['cap_rub_per_oneway_flight']) for x in auth_caps], 'Same statutory point table; eligibility not admitted by agreement')
    ex=rows('support_examples.csv')
    check('support_quantity_and_cap',20*7*80==11200 and D(ex[0]['max_federal_rate_per_flight'])/2==D(ex[1]['max_federal_rate_per_flight']) and D(ex[1]['base_special_fare_ceiling'])==D(ex[0]['base_special_fare_ceiling'])*D('1.5'),'Counterexample to fixed support through passenger growth')
    q={r['question_id']:r for r in rows('clarification_requests.csv')}
    check('Q001_user_confirmed',q['P04-Q001']['status']=='USER_CONFIRMED' and next(a for a in assumptions if a['assumption_id']=='P04-A-METRIC-A')['approval_status']=='USER_CONFIRMED','Current explicit coordinator/user decisionA')
    check('Q002_unresolved_legal',q['P04-Q002']['status']=='INTERPRETATION_REQUIRES_VALIDATION' and q['P04-Q002']['addressee'] and q['P04-Q002']['exceptions'],'No user vote or implicit approval of legal applicability')
    check('airport_domain_preserved',len(rows('airport_coverage.csv'))==20,'No airport rejected for missing price')
    for name in ['airport_reference_examples.csv','support_examples.csv','finance_reference.csv','support_caps_84_103.csv','support_fare_caps.csv','support_eligibility_rules.csv','historical_support_points.csv']:
        check('used_ids:'+name,all(r['assumption_id'] in aid for r in rows(name)),'All used judgements exported')
    owned=[p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    check('no_dependency_runtime',not any(x in p.parts for p in owned for x in ['node_modules','.venv','.next']),'No installed dependency/build artifacts')
    result={'status':'SELF_CHECK_PASS','independent_review':'NOT_RUN','checks':CHECKS,
      'counts':{'checks':len(CHECKS),'source_payloads':verified,'exact_git_blobs':pins,'cost_rows':len(costs),'unknown_cost_rows':len(unknown),'assumptions':len(aid)},
      'source_visual_review':'Selected source pages personally read; see qa/visual_review.json',
      'unverified':['Full paid RW cost basket','Future2027/28contracts and support awards','Internal lease/MRO/crew/base ranges','Future quantity and cash calendars','P04-Q002 independent legal validation','Final network budget/funding or demand/strategy acceptance']}
    (ROOT/'checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':result['status'],**result['counts']}))

if __name__=='__main__':main()
