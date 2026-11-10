#!/usr/bin/env python3
"""Compact readout of all predeclared outcomes; no new scenarios selected."""
from collections import defaultdict
import json
from pathlib import Path
import reproduction as r

OUT=Path(__file__).resolve().parent

def main():
    comp=r.read_csv(OUT/'comparison.csv')
    selected=[x for x in comp if
        (x['origin_model'] in ['nastya','front_historical']) or
        (x['origin_model']=='tsiri_stage22' and x['stress']=='base' and x['profile']=='balanced') or
        (x['origin_model']=='tsiri_historical' and x['profile']=='base') or
        (x['origin_model']=='controlled_common_stage22' and x['profile']=='balanced')]
    robustness=r.read_csv(OUT/'robustness.csv');loo=defaultdict(list)
    for x in robustness:
        if x['kind']=='leave_one_out':loo[x['threshold_km'],x['profile']].append(x)
    stats=[dict(threshold=k[0],profile=k[1],n=len(v),top3_set_changes=sum(x['same_top3']=='False' for x in v),
        alternatives=[dict(omitted=x['omitted'],top3=x['top3']) for x in v if x['same_top3']=='False']) for k,v in loo.items()]
    refs=[x for x in r.read_csv(OUT/'one_factor_deltas.csv') if x['factor']=='reference_points']
    distance=r.read_csv(OUT/'distances.csv')
    changes=[dict(iata=x['iata'],old=x['author_rounded_km'],new=x['km_unrounded'],delta=x['delta_to_author_rounded'])
        for x in distance if x['reference_set']=='case_ZIA_SVX' and float(x['delta_to_author_rounded'])!=0]
    att=r.read_csv(OUT/'attribution_local.csv');ag=defaultdict(list)
    for x in att:ag[x['step']].append(x)
    stages=[dict(step=k,top3=' / '.join(x['iata'] for x in v[:3]),score1=v[0]['score'],score3=v[2]['score']) for k,v in ag.items()]
    bounds=[x for x in r.read_csv(OUT/'unknown_bounds.csv') if x['threshold_km']=='500' and x['profile']=='balanced']
    facts=dict(key_comparisons=selected,loo_by_profile=stats,
        radius_reference_change_comparisons=len(refs),radius_reference_top3_changes=sum(x['before_top3']!=x['after_top3'] for x in refs),
        radius_reference_eligibility_changes=sum(bool(x['excluded'] or x['added']) for x in refs),
        changed_distances=changes,attribution_sequence=stages,balanced500_bounds=bounds,
        balanced500_loo=[x for x in robustness if x['profile']=='balanced' and x['threshold_km']=='500'],
        profiles500=[x for x in comp if x['origin_model']=='tsiri_stage22' and x['stress']=='base' and x['threshold_km']=='500' and x['mode']=='expansion_allowed'])
    r.dump('report_facts.json',facts)
    print(json.dumps(dict(key_comparisons=[{k:x[k] for k in ['origin_model','scenario','universe_n','top3','score1','score2','score3','replay_status']} for x in selected],
        loo_stats=[{k:x[k] for k in ['threshold','profile','n','top3_set_changes']} for x in stats],
        reference_comparisons=len(refs),reference_top3_changes=facts['radius_reference_top3_changes'],
        reference_eligibility_changes=facts['radius_reference_eligibility_changes'],
        changed_distances=changes,
        attribution_sequence=stages),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
