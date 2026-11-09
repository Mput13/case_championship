#!/usr/bin/env python3
"""Bounded conservation check of published tables; no execution of front model."""
import csv
import io
import json
import math
from pathlib import Path
import review_input_set002 as c

SHA='2272e9fac19cdebf68086a46f7ddc48c0fb2d9c8'
OUT=c.BASE/'reviews'/'front2272'

def table(path):return list(csv.DictReader(io.StringIO(c.capture(SHA,path).decode())))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    code=c.capture(SHA,'src/network_model.py').decode()
    summary=table('data/processed/network_summary.csv')
    routes=table('data/processed/network_routes.csv')
    assumptions=table('data/assumptions/network.csv')
    A={r['parameter']:float(r['base'])for r in assumptions}
    c.capture(SHA,'docs/24_hypotheses_comparison.md')
    result=[]
    for no,r in enumerate(summary,2):
        seg,od,tr=[int(r[k])for k in ['segments_year','od_trips_year','transfer_od_year']]
        delta=seg-od-tr
        local=od-tr
        selected=[v for v in routes if v['scenario']==r['scenario']and v['variant']=='Хаб '+r['hub']]if r['hub']else[]
        result.append(dict(csv_row=no,scenario=r['scenario'],hub=r['hub'],segments_year=seg,od_trips_year=od,transfer_od_year=tr,implied_local_od_year=local,segments_required_by_ODs=od+tr,segment_residual=delta,rounding_tolerance=1.5,conservation='FAIL'if abs(delta)>1.5 else'PASS_WITH_ROUNDING',route_segment_sum=sum(int(v['pax_year_segments'])for v in selected)if selected else'',route_local_sum=sum(int(v['pax_year_local'])for v in selected)if selected else'',value_status='DERIVED',scope='Published modeled counts; not observed OD'))
    hubs=[r for r in result if r['hub']]
    assert sum(r['conservation']=='FAIL'for r in hubs)==8
    # Independent scalar mechanism fixture under the published base assumptions.
    # 1000/week/direction is a unit-test SCENARIO, not an observed demand value.
    local=1000;freq=A['min_freq_week'];trace=[]
    for step in range(2):
        old=freq;desired=local*A['capture_open']*(1-math.exp(-old/A['capture_freq_scale']))
        freq=min(A['max_freq_week'],max(A['min_freq_week'],math.ceil(desired/(A['seats']*A['lf_max']))))
        trace.append(dict(step=step,frequency_used_for_capture=old,desired_dir_week=desired,resulting_frequency=freq))
    carried=min(desired,freq*A['seats']*A['lf_max'])
    billed_local=local*A['capture_open']*(1-math.exp(-freq/A['capture_freq_scale']))*(carried/desired)
    # Isolate another mechanism at fixed unequal final spoke frequencies:
    # different per-leg capture cannot represent one common transfer journey.
    t=100;fx,fy=6,3;gx=1-math.exp(-fx/A['capture_freq_scale']);gy=1-math.exp(-fy/A['capture_freq_scale'])
    transfer=dict(unit='weekly bothdirections; t100 pre-frequency captured flowSCENARIO',fixed_spoke_frequencies=[fx,fy],segments_from_independent_spokes=2*t*(gx+gy),segments_required_by_common_transfer_journeys=4*t*min(gx,gy),scope='Component fixture at fixed frequencies, not a full hub replay')
    reproduction=dict(input_git_sha=SHA,coordinator_finding='Received then independently reproduced from pinned summary; no authority-only acceptance',hub_rows=len(hubs),hub_conservation_failures=8,direct_rows=2,direct_conservation_failures=sum(r['conservation']=='FAIL'for r in result if not r['hub']),definition='For local1leg andtransfer2leg journeys, segments=local+2transfer=allOD+transfer. Counts bothdirections/year.',OMS_base_residual=next(r['segment_residual']for r in result if r['hub']=='OMS'and r['scenario']=='base'),UFA_base_residual=next(r['segment_residual']for r in result if r['hub']=='UFA'and r['scenario']=='base'),VOG_base_residual=next(r['segment_residual']for r in result if r['hub']=='VOG'and r['scenario']=='base'),local_only_fixture=dict(value_status='SCENARIO',local_demand_each_direction_week=1000,trace=trace,final_frequency=freq,carried_dir_week=carried,local_used_for_OD_and_revenue=billed_local,weekly_segment_minus_OD_residual=2*(carried-billed_local)),unequal_frequency_transfer_fixture=transfer,source_code_evidence=dict(two_iterations='src/network_model.py:166-172',local_recomputed_at_final_frequency='src/network_model.py:173-177',path_transfer_uses_minfreq_and_minscale='src/network_model.py:178-182',summary_segment_vs_OD='src/network_model.py:316-320'),full_front_model_replay='NOT_RUN',financial_correction='UNKNOWN: reconcilecommonODflows,capacity,frequencies,revenue,cost then rerun route selection; no winner inferred',inherited_input_holds='Endpoint/transfer model and Telegram remain HOLD; this is a separate conservation failure',verdict='CHANGES_P2_CONSERVATION')
    with(OUT/'conservation.csv').open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=list(result[0]));w.writeheader();w.writerows(result)
    (OUT/'input_manifest.json').write_text(json.dumps(dict(inputs=c.receipts),indent=2)+'\n')
    (OUT/'reproduction.json').write_text(json.dumps(reproduction,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in reproduction.items()if k not in ['local_only_fixture','unequal_frequency_transfer_fixture']},ensure_ascii=False))

if __name__=='__main__':main()
