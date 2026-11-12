"""Проверки целостности/границ; не независимая рыночная или финансовая приёмка."""
import csv,gzip,hashlib,json,subprocess,sys
from pathlib import Path
import programme_builder as b
import canonical_finalists as cf
ROOT=b.ROOT

def j(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(condition,label,evidence):
    if not condition:raise AssertionError((label,evidence))
    checks.append(dict(check=label,status='PASS',evidence=evidence))
checks=[]
def main():
    pins=j(ROOT/'input_pins.json');check(all(sha(ROOT/p['local_path'])==p['sha256'] for p in pins),'PINNED_INPUT_BYTES',len(pins))
    promotion=j(ROOT/'root_pin_promotion.json')['files'];check(all(sha(ROOT/p['snapshot'])==p['sha256'] for p in promotion),'ROOT_SOURCE_PROMOTION',len(promotion))
    early=j(ROOT/'early/manifest.json');check(sha(ROOT/'early/manifest.json')=='d39186add31208d2d175ae38795240e630392c32460fd901dd756a727f0abc43' and all(sha(ROOT/p['path'])==p['sha256'] for p in early['files']),'SEALED_EARLY_UNCHANGED',len(early['files']))
    results=[j(p) for p in (ROOT/'evaluations').glob('*.json')];valid=[r for r in results if r['status']=='CONDITIONAL_P05_P06_CALCULATED'];check(len(results)==1958 and len(valid)==1715,'EVALUATION_CARDINALITY',[len(results),len(valid)])
    check(all([m['month'] for m in r['results_monthly']]==b.MONTHS and r['dates_generated']==731 for r in valid),'FULL24_MONTHS_AND731_DATES',len(valid))
    check(all(all(r[k] is None for k in ['full_operating_result','full_delta_result','full_incremental_peak','whole_company_peak','reported_share']) and not r['dispatch_ready'] and not r['global_optimum'] for r in valid),'UNKNOWN_PRESERVATION',len(valid))
    no=[r for r in valid if r['delivery']=='none'];check(all(abs(r['delta_journeys'])<1e-6 and abs(r['delta_known_operating_subtotal'])<.01 for r in no),'NEW_RESOURCE_NONE_CONTROL_EQUAL_KEEP',len(no))
    check(all('delta_known_operating_subtotal' not in r for r in results if r['status']=='INFEASIBLE_CONSTRUCTED_CALENDAR'),'INFEASIBLE_NO_FAKE_ECONOMICS',len(results)-len(valid))
    cs=j(ROOT/'normalized_candidates.json');ds=list(csv.DictReader((ROOT/'candidate_dispositions.csv').open()));check(len(cs)==223==len(ds) and all(x['source_row_sha256'] for x in ds),'EVERY_AUTHOR_RECIPE_DISPOSITION',len(ds))
    check(sum(r['status']=='ОЦЕНЕНА_УСЛОВНАЯ_ПРИВЯЗКА_АВТОРСКОГО_PATH' for r in ds)==30 and sum('АВТОРСКАЯ_ЭКОНОМИКА_NOT_RUN' in r['status'] for r in ds)==27,'AUTHOR_PATH_NONE_IS_NOT_ECONOMIC_EVALUATION',{'calculated':30,'NOT_RUN':27})
    check(len(j(ROOT/'normalized_hypotheses.json'))==169 and len(list(csv.DictReader((ROOT/'legacy_hypothesis_mapping.csv').open())))==35,'HYPOTHESIS_LINEAGE',[169,35])
    programmes={p['programme_id']:p for p in j(ROOT/'programmes.json')['programmes']};selected=j(ROOT/'finalist_selection.json')['selected']
    for d in ['phased','partial','delayed','none']:
        kc=b.build_calendar(b.KEEP,d)
        for pid in selected:
            pc=b.build_calendar(programmes[pid],d);check(pc['fleet_calendar']==kc['fleet_calendar'],'SAME_FLEET_'+pid+'_'+d,len(pc['fleet_calendar']))
            check(not any(x['aircraft_id']=='N1' for x in pc['assignments']),'UNUSED_RESERVE_'+pid+'_'+d,'N1 без коммерческих рейсов')
            original={f['flight_instance_id']:f for f in kc['flights'] if f['flight_instance_id'].startswith('E1:')};retained={f['flight_instance_id']:f for f in pc['flights'] if f['flight_instance_id'].startswith('E1:')};check(original==retained,'EXISTING_KEEP_RETAINED_'+pid+'_'+d,len(original))
    index=j(ROOT/'ui/index.json')['packages'];n=0
    for packref in index:
        pack=j(ROOT/packref['path']);check(sha(ROOT/packref['path'])==packref['sha256'],'UI_PACKAGE_HASH_'+packref['programme_id'],packref['bytes'])
        check(pack['coordinator_acceptance']=='PENDING_COORDINATOR_ACCEPTANCE' and pack['commit'] is None,'NO_SELF_ACCEPTANCE_'+packref['programme_id'],True)
        for ev in pack['evaluations']:
            receipt=j(ROOT/ev['audit_receipt']);f=ROOT/receipt['full']['path'];check(sha(f)==receipt['full']['gzip_sha256'],'GZIP_HASH_'+ev['result']['project']['context']['evaluation_id'],True)
            with gzip.open(f,'rb') as src:raw=src.read()
            check(hashlib.sha256(raw).hexdigest()==ev['source_full_result_sha256'],'FULL_CANONICAL_HASH_'+receipt['evaluation_id'],len(raw));full=json.loads(raw);del raw
            count=cf.verify_projection(ev['result'],full);check(b.digest(ev['result'])==ev['projection_sha256'],'EXACT_PROJECTION_'+receipt['evaluation_id'],dict(canonical_JSON_leaves=count,producer_Python_leaves=receipt['verified_same_path_leaves'],note='Python tuple leaves become JSON arrays; count changes without any JSON value/path change'))
            check(not full['project']['operations']['errors'] and full['project']['operations']['dispatch_ready'] is False,'OPS_CONDITIONAL_'+receipt['evaluation_id'],full['project']['operations']['status'])
            check(abs(receipt['numeric_difference']['journeys'])<1e-6 and abs(receipt['numeric_difference']['known_operating_subtotal'])<.01 and receipt['same_float_bytes_claim'] is False,'OVERVIEW_EQUIVALENCE_'+receipt['evaluation_id'],receipt['numeric_difference'])
            n+=1;del full
    check(n==18,'CANONICAL_COMPARISONS',n)
    check(len(list(csv.DictReader((ROOT/'historical_validation_context.csv').open())))==133 and j(ROOT/'metric_adapter_status.json')['P01_endpoint_OD_observations']==0,'SEGMENTS_NOT_OD',133)
    check(len(list(csv.DictReader((ROOT/'international/thresholds_monthly.csv').open())))==384,'INTERNATIONAL_SYMBOLIC_THRESHOLDS',384)
    if (ROOT/'existing_ssj/canonical_receipts.json').exists():
        for r in j(ROOT/'existing_ssj/canonical_receipts.json'):
            with gzip.open(ROOT/r['full']['path'],'rb') as f:raw=f.read()
            full=json.loads(raw);small=j(ROOT/'existing_ssj'/(r['name']+'.projection.json'))
            check(hashlib.sha256(raw).hexdigest()==r['full']['sha256'] and b.digest(small)==r['projection_sha256'],'SSJ_CANONICAL_'+r['name'],cf.verify_projection(small,full))
    b.dump(ROOT/'validation.json',dict(status='PASS',checks=checks,scope='Авторская воспроизводимость/целостность/расчётные инварианты; independent acceptance pending; не рынок/dispatch/полные деньги',engine_pin='982f13d9b6c378ed9581125ecc5c40f17dade6a3'))
    print('PASS',len(checks),'checks')
if __name__=='__main__':main()
