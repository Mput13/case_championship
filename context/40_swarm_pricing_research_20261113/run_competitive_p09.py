#!/usr/bin/env python3
"""Reproduce full non-AUTH P09 comparison without writing to the pinned subject.

python3 run_competitive_p09.py --rebuild-market
python3 run_competitive_p09.py --configs comp_market_base --programmes VOG_RADIAL
"""
import sys
sys.dont_write_bytecode=True
import argparse, csv, hashlib, json, subprocess, time
from collections import Counter,defaultdict
from pathlib import Path
from build_competition_market import ROOT,P09,dump,writecsv,build

SPOTLIGHT=['VOG_RADIAL','VOG_HYBRID','VOG_BANK9','AER_HYBRID','AER_SEASONAL','MRV_HYBRID','KUF_RADIAL','SVX_RADIAL','SVX_BANK9']
METRICS=['journeys','passenger_segments','delta_journeys','revenue_net','delta_revenue_net','known_operating_subtotal','delta_known_operating_subtotal','known_components_incremental_peak_diagnostic']

def fingerprints():
    paths=[P09/x for x in ['programme_builder.py','evaluate_programmes.py','programmes.json','input_pins.json','subject/P05/model.py','subject/P06/engine/choice.py','subject/P06/engine/finance.py','subject/P06/engine/operations.py']]
    paths+=sorted((P09/'subject/P04').glob('*.csv'))
    paths+=sorted((ROOT/'swarm').glob('*.json'))+[ROOT/x for x in ['routes_manifest_209.csv','travelpayouts_prices_209.csv','yandex_hub_departures.csv','yandex_spotlight_segments.csv','yandex_hub_schedules.json','yandex_spotlight_search.json']]
    return {str(p.relative_to(ROOT.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

def pareto(rows,x='delta_journeys',y='delta_known_operating_subtotal'):
    out=[]
    valid=[r for r in rows if r.get(x) is not None and r.get(y) is not None]
    for r in valid:
        if not any(s[x]>=r[x] and s[y]>=r[y] and (s[x]>r[x]+1e-6 or s[y]>r[y]+1e-6) for s in valid):out.append(r)
    return sorted(out,key=lambda r:-r[y])

def base_summary(result,config,pinned):
    r={k:v for k,v in result.items() if not isinstance(v,(list,dict))}
    r.update(config=config['config'],pricing_policy=config['pricing_policy'],competitive_response=config['response'],expansion_stress=config['expansion'],RW_SUPPORT_NEW=0,fuel_price_rub_t=80000 if config['fuel_net'] else 136300,
        price_year=2026,period_start='2027-01',period_end='2028-12',full_delta_result=None,full_incremental_peak=None)
    monthly=result.get('results_monthly',[])
    seats=sum(m['seat_capacity'] for m in monthly)
    r['flight_load_factor']=result.get('passenger_segments',0)/seats if seats else None
    r['seat_capacity']=seats
    r['missing_cost_headroom']=r.get('delta_known_operating_subtotal')
    for k in METRICS:r['p09_original_'+k]=pinned.get(k)
    for k in ['delta_journeys','delta_revenue_net','delta_known_operating_subtotal']:
        r['change_vs_p09_'+k]=r[k]-pinned[k] if r.get(k) is not None and pinned.get(k) is not None else None
    return r

def route_day(e,pfs,kfs,transfers,legacy_mode=False):
    if legacy_mode:records=e.ORIGINAL_DAILY(pfs,kfs,e.CONFIG['scenario'],transfers,'passive',True)
    else:records=e.daily_evaluate(pfs,kfs,e.CONFIG['scenario'],transfers,'passive',True)
    output=[]
    for fs,r in zip((pfs,kfs),records):
        stats=defaultdict(lambda:defaultdict(float));fby={f['flight_instance_id']:f for f in fs};ps={p['product_id']:p for p in r['products']}
        for f in fs:
            pair='-'.join(sorted((f['origin_airport'],f['destination_airport'])))
            z=stats[pair];z['flights']+=1;z['seats']+=f['saleable_seats'];z['flight_variable_cost']+=e.flight_cost(f,e.CONFIG['scenario'],e.CONFIG['fuel_net'])
        def attribute(alloc,tag=''):
            for x in alloc['allocations']:
                p=ps[x['product_id']]
                if p['owner']!='RW':continue
                q=x['carried']
                for l,weight in zip(p['legs'],p['revenue_weights']):
                    f=fby[l];pair='-'.join(sorted((f['origin_airport'],f['destination_airport'])))
                    z=stats[pair];z[tag+'revenue_net']+=q*p['net_fare']*weight
                    z[tag+'pax_fees']+=q*sum(e.b.pax_rate(f['origin_airport'],k)[0] for k in ['terminal_domestic','pax_service_domestic'])
                    z[tag+'passenger_segments']+=q
                    if not tag:z['journey_equivalents']+=q*weight;z['gross_revenue']+=q*p['gross_fare']*weight
        attribute(r['allocation'])
        if not legacy_mode:
            # Direct-availability counterfactual at exactly the SAME RW fares,
            # connecting alternatives and physical RW schedule. No reoptimisation.
            without=[p for p in r['products'] if p['owner']!='AIR_COMP_DIRECT']
            bundle=dict(flights=fs,markets=r['markets'],products=without,choice_model=e.b.p05.coefficients(e.CONFIG['scenario']),contracts=[],economic_events=[])
            no_direct=e.b.allocate(bundle,without);attribute(no_direct,'no_direct_')
        for z in stats.values():
            for k in ['revenue_net','pax_fees','passenger_segments','journey_equivalents','gross_revenue','no_direct_revenue_net','no_direct_pax_fees','no_direct_passenger_segments']:
                z[k]+=0. # Structural zeros also on positioning legs with no products.
            z['known_contribution']=z['revenue_net']-z['flight_variable_cost']-z['pax_fees']
            z['direct_presence_effect_on_contribution']=z['known_contribution']-(z['no_direct_revenue_net']-z['flight_variable_cost']-z['no_direct_pax_fees']) if not legacy_mode else 0.
        output.append(stats)
    return output

def deep_dive(e,p,config,summary):
    e.configure(config);pc=e.b.build_calendar(p,'phased');kc=e.b.build_calendar(e.b.KEEP,'phased')
    bys=[]
    for cal in [pc,kc]:
        by=defaultdict(list)
        for f in cal['flights']:by[f['departure_utc'][:10]].append(f)
        bys.append(by)
    signatures={}
    for day in sorted(set(bys[0])|set(bys[1])):
        pfs,kfs=bys[0][day],bys[1][day]
        key=e.b.digest([day[:7],e.legacy.daily_shape(pfs),e.legacy.daily_shape(kfs)])
        if key not in signatures:signatures[key]=[0,pfs,kfs]
        signatures[key][0]+=1
    totals=[defaultdict(lambda:defaultdict(float)),defaultdict(lambda:defaultdict(float))]
    for count,pfs,kfs in signatures.values():
        for total,stats in zip(totals,route_day(e,pfs,kfs,p.get('transfers',True),config['pricing_policy']=='legacy')):
            for pair,z in stats.items():
                for k,v in z.items():total[pair][k]+=v*count
    rows=[]
    for pair in sorted(set(totals[0])|set(totals[1])):
        z,k=totals[0][pair],totals[1][pair];market=e.MARKETS.get(pair,{})
        row=dict(config=config['config'],programme_id=p['programme_id'],pair=pair,**z,
            keep_known_contribution=k['known_contribution'],delta_known_contribution=z['known_contribution']-k['known_contribution'],
            delta_direct_presence_effect=z['direct_presence_effect_on_contribution']-k['direct_presence_effect_on_contribution'],
            load_factor=z['passenger_segments']/z['seats'] if z['seats'] else None,
            weighted_gross_fare=z['gross_revenue']/z['journey_equivalents'] if z['journey_equivalents'] else None,
            direct_competitors=market.get('direct_competitors',[]),competitor_daily_seats=market.get('competitor_daily_seats'),F_comp_direct_20kg=market.get('F_comp_direct_20kg'),
            W_comp_2028=market.get('W_comp_2028'),rw_subsidized_2026=market.get('rw_subsidized_2026'),subsidized_carriers_2026=market.get('subsidized_carriers_2026',[]),
            protection_status='NO_DIRECT_OBSERVED_COVERAGE_LIMITED' if not market.get('direct_competitors') else 'DIRECT_COMPETITION',
            allocation_basis='net_journey_revenue_split_across_legs_by_pinned_revenue_weights;each_departure_pax_fee_once;includes_positioning',
            causal_status='MODEL_ABLATION_FIXED_RW_FARES_NOT_EMPIRICAL_CAUSAL_EFFECT')
        rows.append(row)
    got=sum(r['delta_known_contribution'] for r in rows);expected=summary.get('delta_known_operating_subtotal')
    assert expected is not None and abs(got-expected)<.02,(p['programme_id'],got,expected)
    return rows

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--rebuild-market',action='store_true');ap.add_argument('--configs',nargs='*');ap.add_argument('--programmes',nargs='*');ap.add_argument('--skip-deep-dive',action='store_true');args=ap.parse_args()
    before=fingerprints()
    if args.rebuild_market or not (ROOT/'market_competition_209.json').exists():build()
    import competitive_p09_engine as e
    ps=[p for p in json.loads((P09/'programmes.json').read_text())['programmes'] if not p['programme_id'].startswith('AUTH')]
    if args.programmes:ps=[p for p in ps if p['programme_id'] in args.programmes]
    configs=[c for c in e.CONFIGURATIONS if not args.configs or c['config'] in args.configs]
    st=time.time();summary=[];monthly=[];equivalence=[];timing=[]
    neutral=e.neutral_calibration_test(next(p for p in ps if p['programme_id']=='VOG_HYBRID') if any(p['programme_id']=='VOG_HYBRID' for p in ps) else ps[-1])
    for config in configs:
        e.configure(config);t=time.time()
        for i,p in enumerate(ps):
            pid=p['programme_id'];path=P09/'evaluations'/f"{pid}__phased__{config['scenario']}__passive.json"
            pinned=json.loads(path.read_text()) if path.exists() else {}
            r=e.evaluate(p,config);row=base_summary(r,config,pinned);summary.append(row)
            for m in r.get('results_monthly',[]):monthly.append(dict(m,config=config['config'],pricing_policy=config['pricing_policy']))
            if config['pricing_policy']=='legacy':
                errors={k:abs(r[k]-pinned[k]) for k in METRICS if r.get(k) is not None and pinned.get(k) is not None}
                assert r['status']==pinned.get('status'),(pid,r['status'],pinned.get('status'))
                assert max(errors.values(),default=0)<.01,(pid,errors)
                equivalence.append(dict(programme_id=pid,status='PASS',metric_absolute_errors=errors,reference_path=str(path.relative_to(P09)),reference_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            if i%20==0:print(json.dumps(dict(config=config['config'],done=i+1,total=len(ps),seconds=round(time.time()-t,1),programme=pid,delta=row.get('delta_known_operating_subtotal')),ensure_ascii=False),flush=True)
        timing.append(dict(config=config['config'],programmes=len(ps),seconds=time.time()-t,daily_cached_signatures=len(e.CACHE or e.legacy.DAY_CACHE)))
        print('CONFIG_DONE',json.dumps(timing[-1]),flush=True)
        # Durable per-config checkpoint; complete CSV is replaced after all configs.
        dump('model_outputs/'+config['config']+'_summary.json',[r for r in summary if r['config']==config['config']])
    frontier=[];top15=[]
    for c in configs:
        rs=[r for r in summary if r['config']==c['config'] and r.get('delta_known_operating_subtotal') is not None]
        ranked=sorted(rs,key=lambda r:-r['delta_known_operating_subtotal'])
        for rank,r in enumerate(ranked,1):r['rank_known_subtotal']=rank
        for r in pareto(rs):r['pareto']=True;frontier.append(dict(r))
        for r in ranked[:15]:top15.append(dict(r))
    original_rank={r['programme_id']:r['rank_known_subtotal'] for r in summary if r['config']=='p09_legacy_check' and 'rank_known_subtotal' in r}
    for r in summary:
        r['pareto']=r.get('pareto',False);r['p09_original_rank_base']=original_rank.get(r['programme_id'])
    robust=[]
    for policy,suffix in [('market_match',''),('yield_optimal','_yield')]:
        names=['comp_market_base'+suffix,'comp_market_cautious'+suffix,'comp_expansion_stress_2028'+suffix]
        for pid in [p['programme_id'] for p in ps]:
            rs=[r for r in summary if r['programme_id']==pid and r['config'] in names and r.get('delta_journeys') is not None]
            if len(rs)==3:robust.append(dict(programme_id=pid,pricing_policy=policy,delta_journeys=min(r['delta_journeys'] for r in rs),delta_known_operating_subtotal=min(r['delta_known_operating_subtotal'] for r in rs)))
    rf=[]
    for policy in ('market_match','yield_optimal'):
        rf+=pareto([r for r in robust if r['pricing_policy']==policy])
    writecsv('recomputed_programmes_summary.csv',summary);writecsv('model_outputs/recomputed_monthly.csv',monthly)
    writecsv('model_outputs/pareto_frontiers.csv',frontier);writecsv('model_outputs/robust_frontier.csv',rf);writecsv('model_outputs/top15_programmes.csv',top15)
    writecsv('model_outputs/robust_all_programmes.csv',robust)
    dump('model_outputs/legacy_equivalence.json',dict(status='PASS' if equivalence else 'NOT_RUN',programmes=len(equivalence),neutral_intercept_check=neutral,checks=equivalence))
    # Canonical validation for the nine: fast aggregator may differ in rounding,
    # but must preserve the published P06 journey/revenue/headroom projection.
    canonical=list(csv.DictReader((P09/'canonical_summary.csv').open()));canonical_checks=[]
    for row in summary:
        if row['config']!='p09_legacy_check':continue
        old=next((x for x in canonical if x['programme_id']==row['programme_id'] and x['scenario']=='base'),None)
        if old:
            errors={k:abs(row[k]-float(old['missing_cost_headroom' if k=='delta_known_operating_subtotal' else k])) for k in ['delta_journeys','delta_revenue_net','delta_known_operating_subtotal']}
            assert max(errors.values())<.01,(row['programme_id'],errors)
            canonical_checks.append(dict(programme_id=row['programme_id'],status='PASS',absolute_errors=errors))
    dump('model_outputs/canonical_equivalence.json',canonical_checks)
    details=[]
    if not args.skip_deep_dive:
        for config in configs:
            if config['config'] not in ['p09_legacy_check','comp_market_base','comp_market_cautious','comp_expansion_stress_2028','comp_market_base_yield']:continue
            leaders=[r['programme_id'] for r in sorted([r for r in summary if r['config']==config['config'] and r.get('delta_known_operating_subtotal') is not None],key=lambda r:-r['delta_known_operating_subtotal'])[:3]]
            selected=set(SPOTLIGHT+leaders+['KZN_HYBRID','REN_RADIAL'])
            if config['config']!='p09_legacy_check':
                selected|={p['programme_id'] for p in ps if any(set(s['spokes'])&{'SVO','DME','VKO','ZIA'} for s in p['working_slots'])}
            for p in ps:
                row=next(r for r in summary if r['config']==config['config'] and r['programme_id']==p['programme_id'])
                if p['programme_id'] not in selected or row.get('delta_known_operating_subtotal') is None:continue
                details+=deep_dive(e,p,config,row)
                print('DETAIL_DONE',config['config'],p['programme_id'],flush=True)
        writecsv('spotlight9_deep_dive.csv',details);dump('spotlight9_deep_dive.json',details)
    after=fingerprints();assert before==after,'READ_ONLY_INPUT_CHANGED'
    manifest=dict(status='COMPLETED_CONDITIONAL_SCENARIO',programmes=len(ps),configurations=configs,evaluations=len(summary),elapsed_seconds=time.time()-st,timing=timing,allocation_sanity=e.CHECKS,
        input_sha256=before,read_only_inputs_unchanged=True,unmapped_indirect_endpoint_pairs=sorted(e.UNKNOWN_PAIRS),
        legacy_programmes_checked=len(equivalence),canonical_programmes_checked=len(canonical_checks),route_rows=len(details),
        reproduction='PYTHONDONTWRITEBYTECODE=1 python3 context/40_swarm_pricing_research_20261113/run_competitive_p09.py --rebuild-market',
        limits=['No bookings-based demand calibration','No complete future competing schedules','Baggage rule normalization, not exact checkout','Subsidy payments and future eligibility unknown','Full operating result and full financing remain UNKNOWN','No dispatch or market share acceptance'])
    dump('model_outputs/run_manifest.json',manifest)
    print(json.dumps({k:v for k,v in manifest.items() if k not in ['input_sha256','unmapped_indirect_endpoint_pairs','configurations']},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
