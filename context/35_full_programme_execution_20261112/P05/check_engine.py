"""Run pinned P06 evaluate/compare/scenario with P03/P05, retaining all costs UNKNOWN.

This is an interface run on actual package records and conditional dated schedules,
not operational/resource acceptance, a complete KEEP or full RW economics.
"""
import copy
import json
import sys
from model import ROOT, VERSION, write_json
sys.path.insert(0,str(ROOT/'inputs/P06'))
from engine.core import evaluate, compare, scenario, seal


def bundle(side,market_scenario,fragments,p03):
    source=p03['branches']['phased'][side]
    f=fragments[market_scenario][side]
    b={k:copy.deepcopy(source[k]) for k in ['flights','fleet_calendar','assignments','keep_policy','resource_operators']}
    b.update({k:copy.deepcopy(f[k]) for k in ['markets','products','contracts','choice_model','response_policy']})
    b['economic_events']=[];b['cash_events']=[];b['opening_balances']=[]
    b['assumptions']=source['assumptions']+f['assumptions']
    b['input_manifest']=[dict(source_id=r['input_id'],commit=r['commit'],path=r['path'],sha256=r['sha256']) for r in json.loads((ROOT/'input_manifest.json').read_text())]
    b['cost_coverage']={k:dict(status='unknown',event_ids=[],rationale='P04 full programme drivers/contracts not instantiated; unknown is not zero',assumption_id='P05-A16') for k in ['variable_cost','base','aircraft_use','reserve','startup','exit','support']}
    b['cash_coverage']={k:'unknown' for k in ['operating','investing','tax','financing']}
    b['cash_policy']=dict(opening_cash=None,minimum_cash=None,project_opening_cash=None,project_minimum_cash=None,assumption_id='P05-A12')
    b['accounting_policy']='operating_aircraft_use_excludes_interest'
    infoid='P05-PINNED-20261112'
    b['information_set']=dict(information_set_id=infoid,facts=[dict(fact_id='pinned_producer_inputs',available_at='2026-11-12')])
    b['programme_target']=dict(branch='diagnostic_selected_week',rationale='P03 one selected December2028 week; annual supply, whole KEEP and costs unknown',assumption_id='P05-A08')
    b['metric_adapter']=None
    keepid='P05-INTERFACE-'+market_scenario+'-KEEP'
    b['context']=dict(evaluation_id=keepid if side=='keep' else 'P05-INTERFACE-'+market_scenario+'-PROJECT',
        programme_id='KEEP' if side=='keep' else 'P03_GOJ8_RETURNS_DIAGNOSTIC',programme_version=VERSION,fleet_scope_id='CASE_SJ',
        external_scenario_id='P05-'+market_scenario,delivery_calendar_id='P03_RETURNS_V2_phased',market_version=VERSION,choice_version=VERSION+'-'+market_scenario,
        cost_version='P04_PROGRAMME_DRIVERS_UNKNOWN',response_policy_id=f['response_policy']['response_policy_id'],evaluation_mode='fixed_programme',decision_date='2026-11-12',
        information_set_id=infoid,keep_evaluation_id=keepid,input_manifest_sha256='unsealed',period_start='2027-01',period_end='2028-12',cash_start='2026-11',price_year=2026,
        affected_scope_id='P03_SELECTED_DATES_NOT_WHOLE_RW_BUSINESS')
    return seal(b)


def main():
    dest=ROOT/'engine_interface';dest.mkdir(exist_ok=True)
    fragments=json.loads((ROOT/'producer_fragments.json').read_text());p03=json.loads((ROOT/'inputs/P03/sp_adapter/p06_bound_fragments.json').read_text())
    bundles=[];checks=[]
    for s in ['base','cautious']:
        p=bundle('project',s,fragments,p03);k=bundle('keep',s,fragments,p03)
        # Common resource/calendar/KEEP policy inputs remain byte-equivalent.
        k['keep_policy']=copy.deepcopy(p['keep_policy'])
        result=evaluate(p);comp=compare(p,k);bundles.extend([p,k])
        write_json(dest/(s+'_project_bundle.json'),p);write_json(dest/(s+'_keep_bundle.json'),k)
        write_json(dest/(s+'_compare_input.json'),dict(project=p,keep=k))
        # Large repetitive event/metadata trees omitted from report, not hidden checks.
        checks.append(dict(scenario=s,evaluate_status=result['status'],operation_errors=result['operations']['errors'],
            allocation_executed=result['allocation'] is not None,unknown_dependencies=result['unknown_dependencies'],
            summary=result['summary'],delta_summary=comp['delta_summary'],funding_status=comp['project_incremental_funding']['status'],
            peak_funding=comp['project_incremental_funding']['peak_month_end'],metric_share_claimed=False))
        assert result['allocation'] is not None,'P06 dated choice did not execute'
        assert result['summary']['operating_result'] is None
        assert comp['project_incremental_funding']['peak_month_end'] is None
    sc=scenario(bundles)
    assert len(sc['evaluations'])==4
    write_json(dest/'scenario_input.json',dict(bundles=bundles))
    write_json(dest/'checks.json',dict(subject_engine_commit='bc70308fe091c5767dbf26b02d06a7d750a65614',
        producer_P03_commit='79dc698b99dfe866886d32376ed388e85bdd039c',interfaces_called=['evaluate','compare','scenario'],scenario_evaluations=4,checks=checks,
        acceptance='INTERFACE_PASS_ONLY; source/crew/MRO/fullKEEP/fullCE/cost/cash acceptance unresolved; distribution already netted inP05 must not duplicateP04cost',
        price_year='2026RUB scenario reference; future cash FX/indexation not inferred'))
    print(json.dumps([dict(scenario=x['scenario'],status=x['evaluate_status'],allocated=x['allocation_executed'],operations_error_count=len(x['operation_errors']),operating_result=x['summary']['operating_result'],peak_funding=x['peak_funding']) for x in checks],ensure_ascii=False))


if __name__=='__main__':main()
