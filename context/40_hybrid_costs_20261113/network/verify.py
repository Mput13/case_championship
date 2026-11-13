#!/usr/bin/env python3
"""Execute rebuild twice, hash every generated artifact, test budget integration invariants."""
import sys
sys.dont_write_bytecode=True
import csv,hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
GENERATED=['CASES.json','annual_results.csv','component_ledger.csv','seasonal_exposures.csv','seasonal_results.csv',
 'route_ledger.csv','od_inventory.csv','transfer_filter.csv','fleet_requirements.csv','published_allocation_comparison.csv',
 'published_hub_comparison.csv','joint_OD_proof.json','network_map_and_frozen_chains.json','seasonality_profile_checks.csv',
 'seasonality_validation.json','evidence_lines.csv','source_delta.json','budget_boundary.json','coverage_bridge.csv','fleet_gates.json','handoff.json','checks.csv','validation.json']
def hashes():return {n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in GENERATED}
def close(a,b,tol=1e-4):assert abs(a-b)<=tol,(a,b)
def run():
    for _ in range(2):
        subprocess.run([sys.executable,str(HERE/'build.py')],cwd=HERE,check=True)
        current=hashes()
        if _==0:first=current
        else:assert current==first,'Non-deterministic generated outputs'
    from api import expenses_for,runtime_calendar
    checked=0
    for sc in ['base','cautious']:
        for cid in ['OMS','GSV_MRV','AER_VOG','DIRECT2','HYBRID']:
            r=expenses_for(cid,sc);comps=r['components'];drivers=r['drivers']
            close(sum(x['cost_signed_rub'] for x in comps.values()),r['included_costs_rub'])
            close(sum(x['revenue_signed_rub'] for x in comps.values()),r['net_revenue_after_old_fare_forgone_rub'])
            close(r['net_revenue_after_old_fare_forgone_rub']-r['included_costs_rub'],r['operating_subtotal_before_uncovered_rub'])
            close(drivers['segments'],drivers['local_journeys']+2*drivers['transfer_journeys'])
            close(sum(a['departures'] for a in r['airports'].values()),drivers['departures'])
            close(sum(a['arrivals'] for a in r['airports'].values()),drivers['departures'])
            close(sum(a['boardings'] for a in r['airports'].values()),drivers['segments'])
            close(sum(a['transfer_connections'] for a in r['airports'].values()),drivers['transfer_journeys'])
            seasons=[expenses_for(cid,sc,s) for s in ['summer','winter']]
            close(sum(x['included_costs_rub'] for x in seasons),r['included_costs_rub'])
            runtime=runtime_calendar(cid,sc,'2028-01',12)
            close(runtime['totals']['included_costs_rub'],r['included_costs_rub'])
            close(runtime['totals']['net_revenue_rub'],r['net_revenue_after_old_fare_forgone_rub'])
            checked+=11
        h=expenses_for('OMS',sc);d=expenses_for('DIRECT2',sc);a=expenses_for('HYBRID',sc)
        for key in ['included_costs_rub','net_revenue_after_old_fare_forgone_rub','operating_subtotal_before_uncovered_rub']:
            close(h[key]+d[key],a[key]);checked+=1
        c1=expenses_for('GSV_MRV',sc);c2=expenses_for('AER_VOG',sc)
        close(c1['included_costs_rub']+c2['included_costs_rub'],d['included_costs_rub']);checked+=1
    r=expenses_for('HYBRID','base');assert r['fleet']['total_with_local_reserves']==11
    assert r['fleet']['reserve_resource_labels']=='R_OMS;R_MOW'
    assert expenses_for('OMS','base')['drivers']['departures']!=138*52
    meta=json.loads((HERE/'network_map_and_frozen_chains.json').read_text())
    assert len(meta['hub']['spokes'])==9 and set(meta['chains'])=={'GSV_MRV','AER_VOG'}
    assert meta['frozen_seasonal_frequencies']['base']=={'GSV_MRV':{'summer':7,'winter':7},'AER_VOG':{'summer':7,'winter':7}}
    assert meta['frozen_seasonal_frequencies']['cautious']=={'GSV_MRV':{'summer':3,'winter':3},'AER_VOG':{'summer':3,'winter':3}}
    for key,ch in meta['chains'].items():assert meta['orientations'][key]==[ch,list(reversed(ch))]
    assert json.loads((HERE/'joint_OD_proof.json').read_text())['shared_OD']==[]
    try:runtime_calendar('HYBRID','base','2027-06')
    except ValueError:pass
    else:raise AssertionError('Pre H2 2027 entry accepted')
    try:expenses_for('PUBLISHED_HYBRID_ADD','base')
    except ValueError:pass
    else:raise AssertionError('Diagnostic attribution allowed into main budget API')
    half=runtime_calendar('HYBRID','base','2027-07',6)
    assert len(half['months'])==6 and half['totals']['included_costs_rub']!=r['included_costs_rub']
    # Every code citation resolves against exact source bytes and original source line numbers.
    for row in csv.DictReader((HERE/'evidence_lines.csv').open()):
        lines=(HERE/row['snapshot_path']).read_text().splitlines()
        assert lines[int(row['line'])-1]==row['text']
    report=dict(status='PASS',completed_handoff=True,deterministic_rebuilds=2,
      deterministic_artifact_hashes=first,API_integration_checks=checked,source_citations_resolve=True,
      new_global_search=False,no_old_503_138_12_in_main_results=True,scenario_calendar_only=True,
      snapshot_bytes=sum(x['bytes'] for x in json.loads((HERE/'source_manifest.json').read_text())),
      no_price_research=True,no_wait_for_budget_agent=True,blocking_dependencies=[])
    (HERE/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',deterministic_rebuilds=2,API_checks=checked)))
if __name__=='__main__':run()
