#!/usr/bin/env python3
"""Independent narrow reconstruction of a frozen gravity-model export.

Does not import/execute the author's model. Scenarios are sensitivity, not CIs.
"""
from pathlib import Path
import collections
import csv
import datetime as dt
import hashlib
import io
import json
import math
import zipfile
import numpy as np

BASE=Path(__file__).resolve().parent
RAW=BASE/'raw'
ARCHIVE=BASE.parent/'front_audit/raw/primary/tochno_intercity.zip'
MEMBER_SHA='aed8463339b988a7c9ac81aa976a4fc25c152e4066b551d25cbdcc16ebe16d53'
MOW={'SVO','DME','VKO','ZIA'}
RESORT={'AER','MRV'}

def csvread(p):return list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
def num(s):return None if s in ('',None) else float(s)
def sha(b):return hashlib.sha256(b).hexdigest()
def matrix(rows):return np.array([[1,*r] for r in rows],dtype=float)
def fit(X,y):return np.linalg.lstsq(X,y,rcond=None)[0]
def prediction(X,b):return np.exp(X@b)
def ape_metrics(actual,pred):
    a=np.array(actual);p=np.array(pred)
    return dict(usual_actual_denominator_median_APE_pct=float(np.median(np.abs(p/a-1))*100),forecast_denominator_median_APE_pct=float(np.median(np.abs(a/p-1))*100),share_within_x2=float(np.mean(np.maximum(p/a,a/p)<=2)))

def main():
    manifest=json.loads((BASE/'input_manifest.json').read_text())
    assert all(sha((BASE/e['local_path']).read_bytes())==e['sha256'] for e in manifest['files'])
    stored=ARCHIVE.read_bytes()
    with zipfile.ZipFile(io.BytesIO(stored)) as z:
        member=[n for n in z.namelist() if n.endswith('.csv') and not n.startswith('__MACOSX/')][0]
        b=z.read(member);assert sha(b)==MEMBER_SHA
        t=list(csv.DictReader(io.StringIO(b.decode('utf-8-sig')),delimiter=';'))
    rail={(r['city_from'],r['city_to']):r for r in t if r['transport_type']=='rail'}
    catch=csvread(RAW/'data/processed/catchments.csv');nodes={r['iata']:r.copy() for r in catch if r['iata'] not in MOW}
    source_mow=[r for r in catch if r['iata'] in MOW]
    nodes['MOW']=dict(iata='MOW',pop=str(sum(float(r['pop']) for r in source_mow)),main_city='Москва')
    def features(a,b,fill=96):
        aa,bb=nodes[a],nodes[b];r=rail.get((aa['main_city'],bb['main_city']))
        hr=num(r['distance_hr']) if r else None
        return [math.log(float(aa['pop']))+math.log(float(bb['pop'])),math.log(hr if hr is not None else fill),float('MOW' in {a,b}),float(bool(RESORT & {a,b}))],hr,r
    known=csvread(RAW/'data/manual/known_flows.csv');cal=[r for r in known if r['use']=='fit' and r['from_iata'] in nodes and r['to_iata'] in nodes]
    targets=np.array([float(r['pax'])*float(r['annual_factor']) for r in cal]);y=np.log(targets)
    X=matrix([features(r['from_iata'],r['to_iata'])[0] for r in cal]);beta=fit(X,y);loo=[]
    for i in range(len(cal)):
        keep=np.arange(len(cal))!=i;loo.append(float(prediction(X[i:i+1],fit(X[keep],y[keep]))[0]))
    loo=np.array(loo);log_actual_over_pred=y-np.log(loo);q=np.quantile(log_actual_over_pred,[.2,.8]);full=prediction(X,beta)
    doc_report=json.loads((RAW/'data/processed/demand_fit.json').read_text());pairs=csvread(RAW/'data/processed/demand_pairs.csv');spokes=csvread(RAW/'data/processed/demand_spokes.csv');bycand=csvread(RAW/'data/processed/demand_by_candidate.csv')
    pairidx={tuple(sorted([r['a'],r['b']])):r for r in pairs}
    export_errors=[]
    for r in pairs:
        f,_,_=features(r['a'],r['b']);v=math.exp(np.array([1,*f])@beta)
        if abs(v-float(r['pax_base']))>.501:export_errors.append(dict(pair=r['a']+'-'+r['b'],recomputed=v,exported=r['pax_base']))
    grouped={}
    for origin in sorted({r['from_iata']for r in cal}):
        hold=np.array([r['from_iata']==origin for r in cal]);pred=prediction(X[hold],fit(X[~hold],y[~hold]));grouped[origin]=dict(rows=int(hold.sum()),**ape_metrics(targets[hold],pred))
    within_sample_above20=float(np.mean(log_actual_over_pred>=q[0]));missing_cal=[]
    for i,r in enumerate(cal):
        _,hr,rr=features(r['from_iata'],r['to_iata'])
        if hr is None:missing_cal.append(dict(pair=r['from_iata']+'-'+r['to_iata'],missing_reason=rr.get('missing_reason') if rr else 'NO_CITY_KEY',source=rr.get('source')if rr else None))
    # Refit under three explicit missing-rail scenarios, with known rail unchanged.
    scenarios=[]
    for fill in [24,48,96,168]:
        xx=matrix([features(r['from_iata'],r['to_iata'],fill)[0] for r in cal]);bb=fit(xx,y);agg=collections.Counter();changed=[]
        for s in spokes:
            if s['direct_now']=='True' or s['status']=='closed':continue
            pp=pairidx[tuple(sorted([s['hub'],s['to']]))]
            f,hr,rr=features(pp['a'],pp['b'],fill);v=math.exp(np.array([1,*f])@bb);agg[s['hub']]+=round(v)
            if hr is None:changed.append(dict(hub=s['hub'],to=s['to'],missing_reason=rr.get('missing_reason')if rr else 'NO_CITY_KEY'))
        scenarios.append(dict(fill_hours=fill,scenario_status='SCENARIO_NOT_CONFIDENCE_INTERVAL',coefficients=[float(v)for v in bb],top3=[k for k,v in agg.most_common(3)],candidate_totals=dict(agg),missing_rail_gap_spokes=len(changed),missing_reasons=dict(collections.Counter(r['missing_reason']for r in changed))))
    cleaning=[]
    for name in ['base31','exclude_region','exclude_halfyear_annualization','exclude_both']:
        keep=np.array([(name not in ['exclude_region','exclude_both'] or r['coverage']!='region') and (name not in ['exclude_halfyear_annualization','exclude_both'] or float(r['annual_factor'])==1) for r in cal]);bb=fit(X[keep],y[keep]);agg=collections.Counter()
        for s in spokes:
            if s['direct_now']=='True' or s['status']=='closed':continue
            f,_,_=features(s['hub'],s['to']);agg[s['hub']]+=round(math.exp(np.array([1,*f])@bb))
        cleaning.append(dict(scenario=name,remaining_calibration_rows=int(keep.sum()),top3=[k for k,v in agg.most_common(3)],candidate_totals=dict(agg),interpretation='Sensitivity to questionable calibration rows; not a corrected OD model or confidence interval'))
    # Exported summary is exactly the sum of per-pair model values, not independent demand evidence.
    aggs=[]
    for r in bycand:
        ss=[s for s in spokes if s['hub']==r['hub'] and s['direct_now']=='False' and s['status']!='closed']
        aggs.append(dict(hub=r['hub'],sum_base=sum(int(s['pax_base'])for s in ss),export_base=int(r['pax_no_direct_base']),sum_cautious=sum(int(s['pax_cautious'])for s in ss),export_cautious=int(r['pax_no_direct_cautious'])))
    low=[]
    for r in known:
        if r['use']!='fit':
            pp=pairidx.get(tuple(sorted([r['from_iata'],r['to_iata']])))
            if pp:low.append(dict(pair=r['from_iata']+'-'+r['to_iata'],reported_group_lower=float(r['pax'])*float(r['annual_factor']),model_base=int(pp['pax_base']),model_optimistic=int(pp['pax_optimistic']),status='Pinned asserted lower bound, not independently source-authenticated here'))
    feature_criteria=json.loads((RAW/'data/processed/criteria.json').read_text())['criteria']
    demandweights=[c for c in feature_criteria if c['key']=='demand_gap']
    source_clusters=collections.Counter(r['source']for r in cal)
    out=dict(generated_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),input_sha=manifest['input_sha'],author='kiruha355',collector_version='critic-front-demand-1',environment={'numpy':np.__version__},execution_policy='Own numpy/stdlib equations only; author code not executed/imported',
      external_archive=dict(path=str(ARCHIVE),stored_sha256=sha(stored),member=member,member_sha256=sha(b)),
      shape=dict(manual_rows=len(known),fit_rows=len(cal),carrier_group_lower_rows=sum(r['use']!='fit'for r in known),unique_fit_unordered_pairs=len({tuple(sorted([r['from_iata'],r['to_iata']]))for r in cal}),airport_nodes=len(nodes),output_pairs=len(pairs),unique_output_unordered_pairs=len(pairidx),spokes=len(spokes),candidates=len(bycand)),
      calibration=dict(coverage_counts=dict(collections.Counter(r['coverage']for r in cal)),period_annual_factor_counts=dict(collections.Counter(r['period']+';factor='+r['annual_factor']for r in cal)),origin_counts=dict(collections.Counter(r['from_iata']for r in cal)),source_cluster_counts=dict(source_clusters),missing_rail_rows=missing_cal,coefficients=[float(v)for v in beta],expected_rounded_coefficients=doc_report['coefficients']),
      loo=dict(**ape_metrics(targets,loo),reported_median_abs_error_pct=doc_report['loo_median_abs_error_pct'],cautious_residual_factor=float(math.exp(q[0])),optimistic_residual_factor=float(math.exp(q[1])),fraction_of_31_LOO_residuals_above_fitted20pct_cut=within_sample_above20,leave_origin_cluster_out=grouped,validation_scope='LOO on selected airport-segment sample; model feature family selected using same LOO; no independent endpoint/no-direct test'),
      exported_model_values=dict(mismatches=export_errors,reconciled_pairs=len(pairs)-len(export_errors)),summary_aggregation=aggs,rail_missing_scenarios=scenarios,calibration_cleaning_scenarios=cleaning,group_lower_checks=low,criterion=demandweights,
      frequency_example=dict(annual_both_direction_segments=70000,daily_both_directions=70000/365,daily_per_direction=70000/365/2,seats=100,load_factor_scenario=.8,one_way_departures_per_week=70000/(52*100*.8),round_trips_per_week=70000/(52*2*100*.8),scope='Capacity arithmetic for whole market if fully served; capture by RW UNKNOWN; no frequency recommendation'),
      limits=['Observed report aggregation is not synthetic merely because multiple sources are combined.','Endpoint OD/new-direct counterfactual/transfer residual are not identified by this regression on segment counts.','Reproduction is conditional arithmetic, not forecast or data-truth acceptance.','Rail missing fills and annual_factor2 are modelling scenarios; residual quantiles do not guarantee prospective80percent coverage.'])
    (BASE/'reproduction.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(shape=out['shape'],loo=out['loo'],pair_mismatches=len(export_errors),rail_scenario_top3=[{k:r[k]for k in ['fill_hours','top3','missing_rail_gap_spokes']}for r in scenarios],criterion=demandweights),ensure_ascii=False))

if __name__=='__main__':main()
