#!/usr/bin/env python3
"""Offline evidence integrity and dimensional boundary checks; not live acceptance."""
import argparse, csv, hashlib, json, math, struct, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def get(n):return json.loads((ROOT/n).read_text())

def validate():
    checks=[]
    def check(name,ok,detail=''):
        checks.append(dict(check=name,status='PASS' if ok else 'FAIL',detail=detail))
    inputs=get('input_manifest.json')
    for p in inputs['pins']:
        b=(ROOT/p['local_path']).read_bytes()
        check('pinned:'+p['source_id'],sha(b)==p['sha256'])
        blob=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
        check('git_blob:'+p['source_id'],blob==p['git_blob'])
    sources=get('sources/registry.json')
    for r in sources:
        check('source_status:'+r['source_id'],r['status']=='PRIMARY_PUBLIC_CAPTURE')
        check('source_hash:'+r['source_id'],sha((ROOT/r['path']).read_bytes())==r['sha256'])
        check('text_hash:'+r['source_id'],sha((ROOT/r['text_path']).read_bytes())==r['text_sha256'])
    sources_by={r['source_id']:r for r in sources}
    with (ROOT/'source_rows.csv').open() as f:rows=list(csv.DictReader(f))
    for r in rows:
        if r['source_id'] in sources_by:
            src=sources_by[r['source_id']]
            text=(ROOT/src['text_path']).read_text().splitlines()[int(r['row_number'])-1].split('\t',1)[1]
            check('row:'+r['source_row_id'],text==r['text'] and sha(text.encode())==r['row_sha256'])
        else:
            path=ROOT/'evidence/browser'/(r['source_id']+'.json')
            value=json.loads(path.read_text())['tool_result']['value']
            check('browser_row:'+r['source_row_id'],sha(canonical(value))==r['row_sha256'] and sha(path.read_bytes())==r['source_sha256'])
    rowids={r['source_row_id'] for r in rows}
    claims=get('source_claims.json');claimids={c['claim_id'] for c in claims}
    for c in claims:check('claim_rows:'+c['claim_id'],set(c['source_row_ids'])<=rowids)
    assumptions=get('assumptions_register.json');aids={a['assumption_id'] for a in assumptions}
    check('unique_assumptions',len(aids)==len(assumptions))
    required=['basis','selected_by','range_or_unknown','affected_conclusions','sensitivity','how_to_refine']
    check('assumptions_complete',all(all(a.get(k) for k in required) for a in assumptions))
    cards=get('digital_cards.json')
    check('four_areas',len(cards['cards'])==4 and len({c['area'] for c in cards['cards']})==4)
    check('unknown_forecast',all(v is None for v in cards['forecast'].values()))
    for c in cards['cards']:
        check('card_references:'+c['card_id'],set(c['facts'])<=claimids and set(c['required_inputs']+c['assumption_ids'])<=aids)
        check('card_chain:'+c['card_id'],all(c.get(k) for k in ['mechanism','metric','effect_unit','execution','implementation_cost','net_contribution','breakeven','experiment','stop_threshold']))
    months=get('funnel_and_economics.json')['calendar']
    check('24_months_unknown',len(months)==24 and len({m['month'] for m in months})==24 and all(m['eligible_exposures'] is None and m['cash_delta'] is None for m in months))
    with (ROOT/'historical_threshold_replay.csv').open() as f:hist=list(csv.DictReader(f))
    expected={('D01','base'):(850000,.00066),('D01','cautious'):(-2625000,.004),
              ('D02','base'):(1300000,.0024),('D02','cautious'):(-1625000,1/75),
              ('D03','base'):(800000,1/18),('D03','cautious'):(-1775000,4/9)}
    raw=get('inputs/historical_parameters.json')['digital_scenarios']
    for r in hist:
        k=(r['card_id'],r['historical_scenario']);bal,threshold=expected[k]
        src=next(v for v in raw if (v['id'],v['scenario'])==k)
        check('old_arithmetic:'+':'.join(k),math.isclose(float(r['first_year_resource_equivalent_rub']),bal) and math.isclose(float(r['breakeven_absolute_delta']),threshold))
        check('old_row_hash:'+':'.join(k),sha(canonical(src))==r['source_row_sha256'])
        check('old_not_cash:'+':'.join(k),r['cash_effect_rub']=='UNKNOWN')
    visual=get('visual_evidence.json')
    for v in visual['evidence']:
        p=ROOT/v['file'];b=p.read_bytes()
        check('png:'+v['evidence_id'],b[:8]==b'\x89PNG\r\n\x1a\n' and sha(b)==v['sha256'])
    check('own_tabs_closed',visual['own_tabs_closed'] and not visual['other_tabs_touched'] and not visual['profile_changed'])
    check('integration_not_admitted',get('P09_integration_contract.json')['status']=='PROPOSED_MEASUREMENT_ADAPTER_NOT_IMPLEMENTED_OR_ADMITTED')
    check('no_actual_transaction_acceptance',get('digital_cards.json')['stage_b']=='NOT_RUN')
    return dict(status='PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL',
                passed=sum(c['status']=='PASS' for c in checks),failed=sum(c['status']=='FAIL' for c in checks),
                meaning='Целостность источников/связей и воспроизведение старой арифметики; не live/экономическая/независимая приёмка RW',checks=checks)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seal',action='store_true');args=ap.parse_args()
    result=validate()
    if args.seal:
        (ROOT/'validation_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        if result['status']!='PASS':print(json.dumps(result,ensure_ascii=False));return 1
        files=[]
        for p in sorted(ROOT.rglob('*')):
            if not p.is_file() or p.name=='output_manifest.json' or '__pycache__' in p.parts:continue
            b=p.read_bytes();files.append(dict(path=str(p.relative_to(ROOT)),bytes=len(b),sha256=sha(b)))
        body=dict(package='P11',version='20261112-stageA-v1',state='STAGE_A_COMPLETE_STAGE_B_NOT_RUN',
                  files=files,hash_convention='SHA256 exact bytes; manifest excluded from itself',
                  git_mutations=False,live_acceptance=False)
        body['manifest_body_sha256']=sha(canonical(body))
        (ROOT/'output_manifest.json').write_text(json.dumps(body,ensure_ascii=False,indent=2)+'\n')
    elif (ROOT/'output_manifest.json').exists():
        manifest=get('output_manifest.json');body=dict(manifest);inner=body.pop('manifest_body_sha256')
        if sha(canonical(body))!=inner:raise RuntimeError('manifest body hash mismatch')
        actual={str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and p.name!='output_manifest.json' and '__pycache__' not in p.parts}
        recorded={f['path'] for f in manifest['files']}
        if actual!=recorded:raise RuntimeError('manifest file set mismatch: '+str(actual^recorded))
        for f in manifest['files']:
            b=(ROOT/f['path']).read_bytes()
            if len(b)!=f['bytes'] or sha(b)!=f['sha256']:raise RuntimeError('file hash mismatch: '+f['path'])
    print(json.dumps(dict(status=result['status'],passed=result['passed'],failed=result['failed'],manifest_sha256=sha((ROOT/'output_manifest.json').read_bytes()) if (ROOT/'output_manifest.json').exists() else None),ensure_ascii=False))
    return int(result['status']!='PASS')

if __name__=='__main__':sys.exit(main())
