#!/usr/bin/env python3
"""Actual P37 verification only. Never calls completed builders or verifiers."""
import sys
sys.dont_write_bytecode = True
import copy
import csv
import importlib.util
import json
import traceback
from decimal import Decimal as D
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('p37_local_calculation', HERE/'calculate.py')
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def check_close(a, b, tolerance='0.00001'):
    assert abs(D(str(a))-D(str(b))) <= D(tolerance), (a, b)


def read(name):
    with (HERE/name).open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def expect_error(fn):
    try:
        fn()
    except (ValueError, ArithmeticError):
        return
    raise AssertionError('Expected rejected input')


def main():
    args = M.parameters()
    checks, evidence = {}, {}
    before = M.guard_snapshot()

    def test(name, fn):
        try:
            fn()
            checks[name] = 'PASS'
            print('PASS', name, flush=True)
        except Exception as e:
            checks[name] = 'FAIL'
            evidence[name] = repr(e)
            traceback.print_exc()

    generated = ('README.md', 'costs.csv', 'break_even.csv', 'directional_frontier.csv',
                 'quote_template.csv', 'actual_inputs_needed.csv', 'source_manifest.json')
    old = {name: M.sha(HERE/name) for name in generated}
    manifest = M.main(args)

    def deterministic():
        assert old == {name: M.sha(HERE/name) for name in generated}
        assert manifest['guards_unchanged_during_calculation']
    test('actual_calculation_rerun_byte_deterministic', deterministic)

    def strict_edges():
        assert M.min_strict(D(100), D(10)) == 11
        assert M.min_strict(D('99.999'), D(10)) == 10
        assert M.min_strict(D('100.001'), D(10)) == 11
        assert M.min_strict(D(0), D(10)) == 1
        assert M.min_strict(D(-1), D(10)) == 0
        assert M.extra_plan(D(-1), D(10), D(8), 1, 1) == (0, 0, True)
        assert M.extra_plan(D(0), D(10), D(8), 1, 1) == (1, 0, True)
        assert M.extra_plan(D(15), D(10), D(8), 1, 1) == (1, 1, True)
        assert M.extra_plan(D(18), D(10), D(8), 1, 1)[2] is False
        expect_error(lambda: M.min_strict(D(1), D(0)))
        # Exhaustive small inventory cross-check of minimum total tickets.
        for ro, rb in [(D(10), D(8)), (D(8), D(10)), (D(10), D(10))]:
            for need in map(D, (-1, 0, 8, 10, 18, 20, 28, 38, 40)):
                xo, xb, feasible = M.extra_plan(need, ro, rb, 2, 2)
                possible = [(a+b, a, b) for a in range(3) for b in range(3) if a*ro+b*rb > need]
                assert feasible == bool(possible)
                if possible:
                    assert xo+xb == min(possible)[0] and xo <= 2 and xb <= 2
    test('strict_integer_equality_floor_plus_one_and_extra_ticket_caps', strict_edges)

    def units():
        base, caut = M.cost_components('base'), M.cost_components('cautious')
        check_close(base['fuel_burned_t'], D(200)/60*D('1.55')+D('.2'))
        check_close(caut['fuel_burned_t'], D(200)/60*D('1.9')+D('.25'))
        check_close(base['cost_rub'], '988334.2')
        check_close(caut['cost_rub'], D('4289417')/3)
        for c in (base, caut):
            check_close(c['cost_rub'], sum(c[k] for k in ('fuel_rub','mro_rub','navigation_rub','ground_rub','deice_rub')))
            check_close(c['fuel_rub'], c['fuel_burned_t']*c['landed_fuel_rub_t'])
        for sc in M.NET:
            leg, rt, month = [next(r for r in read('costs.csv') if r['scenario']==sc and r['direction']==di) for di in ('out','ROUNDTRIP','FEB4')]
            check_close(rt['cost_rub'], 2*D(leg['cost_rub']))
            check_close(month['cost_rub'], 4*D(rt['cost_rub']))
            assert leg['uplift_added_again_rub'] == leg['lease_avoided_rub'] == leg['fixed_crew_avoided_rub'] == '0'
            assert D(leg['fixed_crew_excluded_rub']) > 0
    test('burn_t_landed_once_MRO_navigation_ground_deice_fixedcrew_lease', units)

    defaults = M.parameters([])
    costs, be, ff = M.calculations(defaults, [])

    def month():
        for sc in M.NET:
            r = {a['horizon']: a for a in be if a['scenario']==sc and a['metric']=='balanced_minimum_strict'}
            C = 2*M.cost_components(sc)['cost_rub']; net=M.NET[sc]
            assert r['ONE_ROTATION']['n_out'] == M.min_strict(C, 2*net)
            assert r['FEB4_REPEAT_SAME_INTEGER_SALES']['tickets_each_direction_horizon'] == 4*r['ONE_ROTATION']['n_out']
            assert r['FEB4_POOLED_INTEGER_SALES']['n_out'] == M.min_strict(4*C, 2*net)
            z = copy.deepcopy(defaults); z.oneoff_f_rub=D(1000000)
            _, bb, _ = M.calculations(z, [])
            q = next(a for a in bb if a['scenario']==sc and a['horizon']=='FEB4_REPEAT_SAME_INTEGER_SALES' and a['metric']=='balanced_minimum_strict')
            assert q['n_out'] == M.min_strict(4*C+D(1000000), 8*net)
            assert q['oneoff_F_horizon'] == D(1000000)
            assert q['n_out'] != M.min_strict(4*(C+D(1000000)), 8*net)
        b = next(a for a in be if a['scenario']=='base' and a['horizon']=='ONE_ROTATION' and a['metric']=='balanced_minimum_strict')
        assert b['n_out'] == b['n_back'] == 69
        pooled = next(a for a in be if a['scenario']=='base' and a['horizon']=='FEB4_POOLED_INTEGER_SALES' and a['metric']=='balanced_minimum_strict')
        assert pooled['n_out'] == 274 and pooled['all_new_flight_tickets_horizon'] == 548
        assert b['all_new_flight_tickets_horizon'] == 138
        evidence['baseline_balanced'] = {sc: {a['horizon']: {'n_each':a['n_out'], 'tickets_total_horizon':a['all_new_flight_tickets_horizon'], 'feasible':a['feasible']} for a in be if a['scenario']==sc and a['metric']=='balanced_minimum_strict'} for sc in M.NET}
    test('four_rotations_eight_legs_not_double_fare_oneoff_F_once_month_pool', month)

    def exhaustive_frontiers():
        variants = [defaults, copy.deepcopy(defaults)]
        variants[1].net_out=D(12000); variants[1].net_back=D(20000); variants[1].net_basis='asymmetric fixture'
        variants[1].cannib_out=7; variants[1].cannib_back=3
        variants[1].old_net_out=D(9000); variants[1].old_net_back=D(8000)
        variants[1].pax_variable_out=D(300); variants[1].pax_variable_back=D(200)
        variants[1].oneoff_f_rub=D(12345); variants[1].recurring_f_rub_per_roundtrip=D(7000)
        variants[1].d_rub_per_roundtrip=D(8000); variants[1].recapture_rub=D(1000)
        count=0
        for v in variants:
            _, bb, frows=M.calculations(v, [])
            for r in frows:
                sc=r['scenario']; turns=r['rotations']; repeated=r['horizon']!='FEB4_POOLED_INTEGER_SALES'
                scale=turns if repeated else 1
                (ro,rb),_=M.choose_yields(v,sc,[])
                (eo,eb),loss,_=M.coefficients(v,(ro,rb))
                fixed=turns*(2*M.cost_components(sc)['cost_rub']+loss+v.recurring_f_rub_per_roundtrip+v.d_rub_per_roundtrip)+v.oneoff_f_rub
                cap=r['cap_each_direction']; no=r['n_out']; nb=r['n_back_min_strict']
                margin=lambda n: no*scale*eo+n*scale*eb-fixed
                feasible=[n for n in range(v.cannib_back if repeated else turns*v.cannib_back, cap+1) if margin(n)>0]
                assert r['feasible']==bool(feasible)
                if feasible:
                    assert nb==min(feasible) and 0<=no<=cap and 0<=nb<=cap
                assert margin(nb)>0
                if nb>(v.cannib_back if repeated else turns*v.cannib_back): assert margin(nb-1)<=0
                count+=cap+1
            for r in bb:
                if r['metric']=='balanced_minimum_strict':
                    assert r['margin_at_integer']>0
                    if r['n_out']>max(v.cannib_out,v.cannib_back)* (1 if r['horizon']!='FEB4_POOLED_INTEGER_SALES' else r['rotations']):
                        assert r['margin_one_less']<=0
                    assert r['feasible']==(r['n_out']<=r['cap_each_direction'])
        evidence['frontier_integer_inventory_points_checked']=count
    test('directional_asymmetric_frontiers_strict_both_direction_caps', exhaustive_frontiers)

    def cannib():
        z=copy.deepcopy(defaults);z.cannib_out=10;z.cannib_back=5
        z.old_net_out=D(9000);z.old_net_back=D(8000);z.recapture_rub=D(12000);z.saved_old_pax_variable_rub=D(3000)
        effective,loss,_=M.coefficients(z,(D(14000),D(13000)))
        assert effective==(D(14000),D(13000)) and loss==D(115000)
        _,bb,_=M.calculations(z,[])
        r=next(a for a in bb if a['scenario']=='base' and a['horizon']=='ONE_ROTATION' and a['metric']=='balanced_minimum_strict')
        assert r['all_new_flight_tickets_horizon']-r['new_to_RW_tickets_horizon']==15
        z.lost_rw_contribution_rub=D(115000)
        expect_error(lambda:M.coefficients(z,(D(14000),D(13000))))
        for sc in M.NET:
            s=[a for a in be if a['scenario']==sc and a['horizon']=='ONE_ROTATION' and a['metric']=='cannibalization_stress_equal_old_new_net']
            assert [a['n_out'] for a in s]==sorted(a['n_out'] for a in s)
            assert all(a['new_to_RW_tickets_horizon']+a['transferred_tickets_horizon']==a['all_new_flight_tickets_horizon'] for a in s)
        evidence['cannib_count_fixture_loss_rub']=str(loss)
    test('cannib_not_new_RW_demand_recapture_saved_once_no_joint_loss_repeat', cannib)

    def historical():
        target={'base':('3049747.6216269','3767311.2911838'), 'cautious':('-6984900.2591655','-6172965.1936041')}
        for sc,(direct,mainvalue) in target.items():
            replay=manifest['direct_only_reproduction'][sc]
            check_close(replay['direct_only_delta_month'],direct)
            check_close(replay['main_including_conditional_through_delta_month'],mainvalue)
            check_close(replay['retained_direct_revenue_change'],0)
            assert replay['same_old_flight_ids']==120
            assert replay['direct_only_states']['KEEP']==replay['direct_only_states']['WITHOUT_NEW']
            assert replay['through_in_primary_threshold'] is False
        assert manifest['pure_API_calls']=={'choice_bundle':4,'P06.allocate':4}
        assert manifest['old_builders_or_verifiers_run'] is False
        assert all(r.get('through_revenue',0)==0 for r in be)
        assert all(r.get('actual_full_profit') is None for r in be)
        assert manifest['actual_full_profit'] is manifest['actual_sales'] is None
        w=manifest['focused_window']
        assert (w['prior_ground_minutes'],w['prior_slack_after_turn60'],w['next_ground_minutes'])==(170,110,1985)
        assert w['actual_crew_rest_reserve_slot_release'] is None
    test('pure_API_reproduction_same_KEEP_ADD_through_OFF_actual_NULL_window', historical)

    def quote_gate():
        q=dict.fromkeys(M.QUOTE_FIELDS,'')
        q.update(quote_id='TEST',date='2026-11-13',travel_date='2027-02-01',direction='out',flight='TEST1',carrier='TEST',
                 baggage='20kg checked + hand',baggage_kg='20',hand_baggage_included='true',mandatory_fees_included='true',
                 adults='1',cabin='economy',currency='RUB',allin_price='20000',status='VERIFIED',source='fixture only')
        qq,reject=M.confirmed_quotes([q,dict(q,status='UNVERIFIED',net_yield_if_verified='1')])
        assert len(qq)==len(reject)==1 and qq[0]['net'] is None
        assert M.choose_yields(defaults,'base',qq)[0][0]==M.NET['base']
        v=copy.deepcopy(defaults);v.net_retention_factor=D('.90')
        expect_error(lambda:M.choose_yields(v,'base',qq))
        v.net_retention_basis='intentional fixture, not observed'
        value,basis=M.choose_yields(v,'base',qq)
        assert value[0]==18000 and 'SCENARIO' in basis[0]
        qq,_=M.confirmed_quotes([dict(q,net_yield_if_verified='18000',net_verification_basis='fixture settlement')])
        assert M.choose_yields(defaults,'cautious',qq)[0][0]==18000
        expect_error(lambda:M.confirmed_quotes([dict(q,net_yield_if_verified='18000')]))
        expect_error(lambda:M.confirmed_quotes([dict(q,baggage_kg='15')]))
        expect_error(lambda:M.confirmed_quotes([dict(q,net_yield_if_verified='21000',net_verification_basis='bad')]))
        qq,_=M.confirmed_quotes([q,dict(q,quote_id='TEST2')])
        expect_error(lambda:M.choose_yields(defaults,'base',qq))
        template,ignored=M.confirmed_quotes(read('quote_template.csv'))
        assert template==[] and len(ignored)==2
        parsed=M.parameters(['--quotes',str(HERE/'quote_template.csv'),'--net-out','17000','--net-basis','fixture'])
        assert parsed.quotes==HERE/'quote_template.csv' and parsed.net_out==17000
    test('quotes_verified_only_gross_upper_bound_no_automatic_VAT_commission', quote_gate)

    def prices_and_caps():
        for sc in M.NET:
            rows=[r for r in be if r['scenario']==sc and r['horizon']=='ONE_ROTATION']
            levels=[r for r in rows if r['metric']=='net_yield_change_inverse_threshold_only']
            baseline=next(r for r in rows if r['metric']=='balanced_minimum_strict')
            assert levels[0]['n_out']>=baseline['n_out']>=levels[1]['n_out']
            for r in rows:
                if r['metric']=='equal_direction_net_BE':
                    check_close(r['rub_per_direct_ticket'], M.cost_components(sc)['cost_rub']/r['n_out'])
            cap=next(r for r in rows if r['metric']=='capacity_ceiling_conditional_subtotal')
            check_close(cap['rub'],200*M.NET[sc]-2*M.cost_components(sc)['cost_rub'])
            assert cap['feasible']==(sc=='base')
        evidence['base_frontier']=[{'out':r['n_out'],'back_min_strict':r['n_back_min_strict']} for r in ff if r['scenario']=='base' and r['horizon']=='ONE_ROTATION']
    test('changed_net_changes_threshold_capacity_ceiling_net_BE_80_90_100', prices_and_caps)

    def protected():
        assert before==M.guard_snapshot()==manifest['guards']
        assert before['protected_count']==1418
        files={p.name for p in HERE.iterdir() if p.is_file()}
        assert files <= M.ALLOWED
        assert not (HERE/'__pycache__').exists()
        assert all(M.sha(HERE/n)==h for n,h in manifest['output_hashes'].items())
    test('protected_1418_all_P36_unchanged_only_allowed_outputs_no_bytecode', protected)

    status='PASS' if all(v=='PASS' for v in checks.values()) else 'FAIL'
    M.dump('validation.json',dict(status=status, command=' '.join(sys.argv), python=sys.executable,
        checks=checks, evidence=evidence, source_manifest_sha256=M.sha(HERE/'source_manifest.json'),
        protected_before_after=before, actual_calculation_rerun=True,
        output_hashes={n:M.sha(HERE/n) for n in generated},
        no_external_search=True, no_old_builder_verify=True, actual_sales=None, actual_full_profit=None,
        scope='inverse direct-ticket threshold vs same KEEP, not forecast or dispatch'))
    print(status, str(HERE/'validation.json'))
    if status!='PASS':
        raise SystemExit(1)


if __name__=='__main__':
    main()
