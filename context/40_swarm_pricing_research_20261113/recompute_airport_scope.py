#!/usr/bin/env python3
"""Recompute every affected non-AUTH programme after physical-airport adapter fix.

--compute is independent of the main run. --apply requires its finished manifest.
Fresh run_competitive_p09.py uses the corrected engine and needs no repair step.
"""
import sys
sys.dont_write_bytecode=True
import argparse,json,time
import competitive_p09_engine as e
from build_competition_market import dump,writecsv,readcsv,ROOT
from run_competitive_p09 import base_summary,deep_dive,pareto,fingerprints

def compute():
    start=time.time();before=fingerprints();ps=[p for p in json.loads((e.P09/'programmes.json').read_text())['programmes'] if not p['programme_id'].startswith('AUTH') and any(set(s['spokes'])&{'SVO','DME','VKO','ZIA'} for s in p['working_slots'])]
    summaries=[];monthly=[];details=[]
    for config in e.CONFIGURATIONS[1:]:
        e.configure(config)
        for p in ps:
            pin=json.loads((e.P09/'evaluations'/f"{p['programme_id']}__phased__{config['scenario']}__passive.json").read_text())
            r=e.evaluate(p,config);summaries.append(base_summary(r,config,pin))
            monthly+=[dict(m,config=config['config'],pricing_policy=config['pricing_policy']) for m in r['results_monthly']]
        print(config['config'],'airport',len(ps),'DONE',flush=True)
    for config in [e.CONFIGURATIONS[i] for i in [1,2,3,5]]:
        for p in ps:
            summary=next(r for r in summaries if r['programme_id']==p['programme_id'] and r['config']==config['config'])
            details+=deep_dive(e,p,config,summary)
        print(config['config'],'airport route detail DONE',flush=True)
    assert before==fingerprints()
    dump('model_outputs/airport_scope_recomputation.json',dict(status='COMPUTED',programmes=[p['programme_id'] for p in ps],summaries=summaries,monthly=monthly,details=details,
        seconds=time.time()-start,sanity=e.CHECKS,unknown_pairs=sorted(e.UNKNOWN_PAIRS),reason='P05 CITY:MOW pool retained; exact physical SVO/ZIA competition and P05 Moscow VAT restored',input_sha256=before))

def apply():
    correction=json.loads((ROOT/'model_outputs/airport_scope_recomputation.json').read_text());manifest=json.loads((ROOT/'model_outputs/run_manifest.json').read_text())
    allrows=[];corrected={(r['programme_id'],r['config']):r for r in correction['summaries']}
    for config in e.CONFIGURATIONS:
        rows=json.loads((ROOT/'model_outputs'/f"{config['config']}_summary.json").read_text())
        allrows += [corrected.get((r['programme_id'],r['config']),r) for r in rows]
    front=[];top=[]
    for config in e.CONFIGURATIONS:
        rows=[r for r in allrows if r['config']==config['config'] and r.get('delta_known_operating_subtotal') is not None]
        for rank,r in enumerate(sorted(rows,key=lambda r:-r['delta_known_operating_subtotal']),1):r['rank_known_subtotal']=rank;r['pareto']=False
        for r in pareto(rows):r['pareto']=True;front.append(dict(r))
        top+=sorted(rows,key=lambda r:-r['delta_known_operating_subtotal'])[:15]
    orank={r['programme_id']:r.get('rank_known_subtotal') for r in allrows if r['config']=='p09_legacy_check'}
    for r in allrows:r['p09_original_rank_base']=orank.get(r['programme_id'])
    robust=[]
    for policy,suffix in [('market_match',''),('yield_optimal','_yield')]:
        names=['comp_market_base'+suffix,'comp_market_cautious'+suffix,'comp_expansion_stress_2028'+suffix]
        for pid in orank:
            rs=[r for r in allrows if r['programme_id']==pid and r['config'] in names]
            if len(rs)==3:robust.append(dict(programme_id=pid,pricing_policy=policy,delta_journeys=min(r['delta_journeys'] for r in rs),delta_known_operating_subtotal=min(r['delta_known_operating_subtotal'] for r in rs)))
    rf=[]
    for policy in ['market_match','yield_optimal']:rf+=pareto([r for r in robust if r['pricing_policy']==policy])
    oldmonthly=readcsv(ROOT/'model_outputs/recomputed_monthly.csv');oldmonthly=[r for r in oldmonthly if (r['programme_id'],r['config']) not in corrected]
    olddetail=json.loads((ROOT/'spotlight9_deep_dive.json').read_text());detailkeys={(r['programme_id'],r['config']) for r in correction['details']}
    details=[r for r in olddetail if (r['programme_id'],r['config']) not in detailkeys]+correction['details']
    writecsv('recomputed_programmes_summary.csv',allrows);writecsv('model_outputs/recomputed_monthly.csv',oldmonthly+correction['monthly'])
    writecsv('model_outputs/pareto_frontiers.csv',front);writecsv('model_outputs/top15_programmes.csv',top);writecsv('model_outputs/robust_all_programmes.csv',robust);writecsv('model_outputs/robust_frontier.csv',rf)
    writecsv('spotlight9_deep_dive.csv',details);dump('spotlight9_deep_dive.json',details)
    for config in e.CONFIGURATIONS:dump('model_outputs/'+config['config']+'_summary.json',[r for r in allrows if r['config']==config['config']])
    manifest['airport_scope_recomputation']=dict(programmes=correction['programmes'],evaluations=len(correction['summaries']),seconds=correction['seconds'],reason=correction['reason'],status='APPLIED_ALL_AFFECTED_PROGRAMMES')
    manifest['elapsed_seconds_before_airport_scope_recomputation']=manifest.get('elapsed_seconds_before_airport_scope_recomputation',manifest['elapsed_seconds'])
    manifest['elapsed_seconds']=manifest['elapsed_seconds_before_airport_scope_recomputation']+correction['seconds'];manifest['route_rows']=len(details)
    manifest['unmapped_indirect_endpoint_pairs']=sorted(set(p for p in manifest['unmapped_indirect_endpoint_pairs'] if 'MOW' not in p.split('-'))|set(correction['unknown_pairs']))
    for k,v in correction['sanity'].items():manifest['allocation_sanity'][k]=manifest['allocation_sanity'][k]+v if k=='allocation_calls' else max(manifest['allocation_sanity'][k],v)
    assert manifest['input_sha256']==fingerprints()
    dump('model_outputs/run_manifest.json',manifest)
    print('APPLIED',len(corrected),'evaluations',len(details),'route rows',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--compute',action='store_true');ap.add_argument('--apply',action='store_true');a=ap.parse_args()
    if a.compute:compute()
    if a.apply:apply()
