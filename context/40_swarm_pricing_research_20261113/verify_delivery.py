#!/usr/bin/env python3
"""Final offline delivery checks; --fresh repeats four substantive evaluations."""
import sys
sys.dont_write_bytecode=True
import argparse,csv,hashlib,json,math
from pathlib import Path
from build_competition_market import ROOT,readcsv,dump
from run_competitive_p09 import fingerprints

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--fresh',action='store_true');args=ap.parse_args()
    manifest=json.loads((ROOT/'model_outputs/run_manifest.json').read_text());assert manifest['input_sha256']==fingerprints()
    market=json.loads((ROOT/'market_competition_209.json').read_text());rows=readcsv(ROOT/'recomputed_programmes_summary.csv');by={(r['programme_id'],r['config']):r for r in rows}
    assert len(market)==209 and len({r['pair'] for r in market})==209
    assert len(rows)==968 and len(by)==968
    assert len(readcsv(ROOT/'hub_weights_22.csv'))==22
    assert manifest['legacy_programmes_checked']==121 and manifest['canonical_programmes_checked']==9
    for m in market:
        assert 'WZ' not in m['direct_competitors']
        assert 0<=m['W_comp_2027']<=m['W_comp_2028']<=1
    details=json.loads((ROOT/'spotlight9_deep_dive.json').read_text());sums={}
    for r in details:sums[(r['programme_id'],r['config'])]=sums.get((r['programme_id'],r['config']),0)+r['delta_known_contribution']
    for key,value in sums.items():assert abs(value-float(by[key]['delta_known_operating_subtotal']))<.02,(key,value)
    fresh=[]
    if args.fresh:
        import competitive_p09_engine as e
        ps=json.loads((e.P09/'programmes.json').read_text())['programmes']
        for pid,cfg in [('VOG_RADIAL',1),('KGD_RADIAL',1),('VOG_HYBRID',5),('MRV_SEASONAL',1)]:
            c=e.CONFIGURATIONS[cfg];p=next(p for p in ps if p['programme_id']==pid);r=e.evaluate(p,c);saved=by[pid,c['config']]
            errors={k:abs(r[k]-float(saved[k])) for k in ['delta_journeys','delta_revenue_net','delta_known_operating_subtotal','known_components_incremental_peak_diagnostic']}
            assert max(errors.values())<.01,(pid,errors)
            fresh.append(dict(programme_id=pid,config=c['config'],status='PASS',absolute_errors=errors))
            print(pid,c['config'],'fresh PASS',flush=True)
    artifacts=json.loads((ROOT/'model_outputs/artifact_manifest.json').read_text());bad=[]
    for name,sha in artifacts['files'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=sha:bad.append(name)
    assert not bad,bad
    result=dict(status='PASS',routes=209,hubs=22,summary_rows=968,route_rows=len(details),route_programme_checks=len(sums),source_hashes_unchanged=len(manifest['input_sha256']),artifact_hashes_checked=len(artifacts['files']),fresh_reproduction=fresh,
        financial_scope='KNOWN_COMPONENTS_ONLY;FULL_RESULT_AND_FULL_FUNDING_UNKNOWN',write_boundary=str(ROOT))
    dump('model_outputs/delivery_verification.json',result);print(json.dumps(result,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
