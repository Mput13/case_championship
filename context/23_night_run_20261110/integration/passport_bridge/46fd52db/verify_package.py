#!/usr/bin/env python3
"""Meaningful transfer/provenance checks, not an economic or market test."""
import csv
import hashlib
import io
import json
import pathlib
import re
import subprocess
import sys
from urllib.parse import urlparse
from read_sources import PINS

P=pathlib.Path(__file__).resolve().parent
PREFIX='context/23_night_run_20261110/passport_bridge/'
def rows(name):
    with (P/name).open() as f:
        r=csv.reader(f); allrows=list(r)
    assert all(len(r)==len(allrows[0]) for r in allrows),name+' malformed CSV'
    return list(csv.DictReader(io.StringIO((P/name).read_text())))
def blob(alias,path):return subprocess.check_output(['git','show',PINS[alias]+':'+path])
results=[]
def check(name,fn):
    try:
        detail=fn();results.append(dict(check=name,status='PASS',detail=detail))
    except Exception as e:results.append(dict(check=name,status='FAIL',detail=str(e)))
def identity(data,key):
    vals=[r[key] for r in data];assert len(vals)==len(set(vals));return set(vals)
C=rows('claims.csv');R=rows('requirements_evidence.csv');E=rows('evidence_index.csv');K=rows('competitor_and_svx_gaps.csv');D=rows('decision_options.csv')
def ids():
    cs=identity(C,'claim_id');rs=identity(R,'requirement_id');es=identity(E,'evidence_id');identity(K,'example_id');identity(D,'decision_id')
    for c in C:
        assert set(c['evidence_ids'].split(';'))<=es,c['claim_id']
        assert set(c['requirement_ids'].split(';'))<=rs,c['claim_id']
    for r in R:
        assert set(r['existing_evidence_ids'].split(';'))<=es,r['requirement_id']
        assert set(r['allowed_claim_ids'].split(';'))<=cs,r['requirement_id']
        assert r['gap'] and r['next_action'] and r['reviewable_output'],r['requirement_id']
    for r in K:assert set(r['exact_evidence_ids'].split(';'))<=es,r['example_id']
    for r in D:assert set(r['evidence_ids'].split(';'))<=es and r['status']=='OPEN_DECISION'
    assert set(c['group'] for c in C)=={'МОЖНО_СЕЙЧАС','УСЛОВНЫЙ_СЦЕНАРИЙ','НЕЛЬЗЯ_УТВЕРЖДАТЬ'}
    return dict(requirements=len(R),claims=len(C),evidence=len(E),examples=len(K),options=len(D))
check('IDENTIFIERS_AND_REFERENCES',ids)
def source_hashes():
    s=json.loads((P/'source_manifest.json').read_text());n=0
    for r in s['sources']:
        assert r['commit'] in PINS.values()
        raw=subprocess.check_output(['git','show',r['commit']+':'+r['path']])
        assert hashlib.sha256(raw).hexdigest()==r['sha256'],r['path'];assert len(raw)==r['bytes'];n+=1
    for e in E:
        if e['source_commit']:
            raw=subprocess.check_output(['git','show',e['exact_ref']]);assert hashlib.sha256(raw).hexdigest()==e['sha256']
            assert e['source_commit'] in e['github_url'] and e['source_path'] in e['github_url']
    return dict(exact_blobs_verified=n,live_sources='NOT_READ_BY_CHECK')
check('EXACT_SOURCE_HASHES',source_hashes)
def official():
    r=json.loads((P/'official_case_receipt.json').read_text());o=json.loads((P/'official_requirements.json').read_text())
    old=json.loads(blob('brief','context/17_research_report/network_recovery/receipts/case_brief.json'))
    assert r['status']==200 and r['url']=='https://mai-way.ru/tasks/red-wings/'
    assert r['sha256']==old['source_sha256']==o['raw_sha256']
    assert r['bytes']==old['size_bytes']==44261
    assert not (P/'official_case_text.txt').exists()
    assert len(o['requirements'])==21
    return dict(raw_hash_matches_historical=True,wording='personally read sections5–7; original background not independently validated')
check('OFFICIAL_REQUIREMENT_RECEIPT',official)
def cards():
    src=list(csv.DictReader(io.StringIO(blob('primary','context/23_night_run_20261110/primary_evidence/route_product_cards.csv').decode())))
    by={r['card_id']:r for r in src};n=0
    for r in K:
        if r['kind']!='ROUTE_OFFER':continue
        s=by[r['source_card_ids']]
        for left,right in [('carrier','carrier'),('flight','flight'),('published_count','one_way_departures'),('departure_dates','departure_dates'),('raw_sha256','raw_sha256'),('source_rows','source_rows'),('source_ids','source_ids')]:
            assert r[left]==s[right],r['example_id']+' '+left
        assert len(s['departure_dates'].split(';'))==int(s['one_way_departures'])
        assert s['period_start']=='2026-12-07' and s['period_end']=='2026-12-13'
        n+=1
    assert sum(int(by[c]['one_way_departures']) for c in ['RPC026','RPC027'])==4
    assert sum(int(by[c]['one_way_departures']) for c in ['RPC053','RPC054'])==4
    assert by['RPC029']['one_way_departures']==by['RPC055']['one_way_departures']=='4'
    assert by['RPC008']['one_way_departures']==by['RPC052']['one_way_departures']=='2'
    assert len([r for r in K if r['kind']=='REGIONAL_BASE_PROFILE'])>=2
    return dict(route_card_transfers_checked=n,ufa_directional_totals='4/4;4/4;2/2; raw rule checks inherited')
check('CARD_COUNTS_DATES_HASHES',cards)
def weights():
    original=list(csv.DictReader(io.StringIO(blob('screen','context/23_night_run_20261110/screening/criteria_comparison.csv').decode())))
    exported=rows('author_weights.csv');assert len(exported)==len(original)==36
    for x,y in zip(original,exported):
        for a,b in [('origin_model','model'),('criterion','criterion'),('weight','raw_weight'),('normalized_weight','normalized_weight'),('direction','direction')]:assert x[a]==y[b]
    assert sum(float(r['raw_weight']) for r in exported if r['model']=='nastya')==125
    assert sum(float(r['raw_weight']) for r in exported if r['model']=='tsiri_stage22')==100
    return '36 author rows unchanged; sums125/100; no chosen team profile'
check('ORIGINAL_WEIGHTS_PRESERVED',weights)
def numeric_literals():
    # Transfer assertions against exact independent-review prose. No model execution.
    refs={a:blob(a,'context/23_night_run_20261110/'+p+'/report.md').decode() for a,p in [
        ('repair_review','model_repair_review'),('common_review','common_comparison_review'),('strategy_review','strategy_accounting_review'),('source_review','source_join_review')]}
    wanted={
        'repair_review':['1\u202f372','1\u202f072','20/18','20/21'],
        'common_review':['0.6835090019901104','−449 822.70','2.4617708804','2.9194370052','129','28','58'],
        'strategy_review':['−446 063,89','2 703 326,676013','240','630','4→8','23','67','72'],
        'source_review':['800 тыс.','2,5','129','28','58']}
    for a,literals in wanted.items():
        for literal in literals:assert literal in refs[a],a+' missing '+repr(literal)
    ck=json.loads(blob('kover_review','context/23_night_run_20261110/cost_kover_review/findings.json'))
    f=ck['confirmed_findings'][0];assert f['severity']=='P2'
    assert f['measured_effects']['H_UFA_8_day2_legs_shifted_by_1440_minutes']==16
    assert f['example']['correct_departure_utc']=='2026-12-08T07:25:00+00:00'
    actual={r['claim_id']:r['ready_russian_wording'] for r in C}
    transferred={
        'C04':['20','18'], 'C05':['800','2,5'], 'S01':['0,683509','−3,168'],
        'S03':['−449 822,70','2,462','2,919'], 'S04':['2 703 326,68'],
        'S05':['240'], 'S06':['446 063,89'], 'S07':['восемь'], 'S08':['67','72','8000']}
    for cid,numbers in transferred.items():
        for value in numbers:assert value in actual[cid],cid+' changed transferred literal '+value
    svx={r['example_id']:r for r in K}
    assert svx['V01']['published_count']=='800000' and 'rounded' in svx['V01']['unit']
    assert svx['V03']['published_count']=='2.5' and 'growth factor' in svx['V03']['unit']
    assert svx['V06']['published_count']=='129/28/58'
    return 'Selected quoted source numbers/units matched; economic recalculation NOT_RUN'
check('TRANSFERRED_NUMBERS_AND_P2_WITNESS',numeric_literals)
def limits():
    c={r['claim_id']:r for r in C}
    assert c['C12']['acceptance_scope']=='OWNER_DERIVATION/PENDING'
    assert 'HOLD' in c['X06']['acceptance_scope'] and 'NOT' in c['X01']['acceptance_scope']
    for id in ['S01','S02','S03','S04','S05','S06','S07','S08']:
        assert c[id]['group']=='УСЛОВНЫЙ_СЦЕНАРИЙ' and c[id]['use_condition'] and c[id]['prohibited_extension']
    assert any(r['requirement_kind']=='ORGANIZER_CONTEXT' for r in R)
    assert any(r['requirement_kind']=='CONTRACT_ANALYTICAL_STANDARD' for r in R)
    h=json.loads((P/'handoff.json').read_text())
    assert 'NOT_RUN' in h['independent_review'];assert h['safety']['automatic_continuation'] is False
    for id in ['E20','E21','E22']:
        e=next(r for r in E if r['evidence_id']==id);assert 'PENDING' in e['acceptance_scope']
    return 'Open policy choices, pending exact inputs and source/recovery holds retained'
check('ACCEPTANCE_BOUNDARIES',limits)
def urls_and_files():
    count=0
    for r in E:
        u=urlparse(r['github_url']);assert u.scheme=='https' and u.netloc;count+=1
    for f in P.glob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)',f.read_text()):
            if target.startswith('https://'):
                assert urlparse(target).netloc;continue
            assert (P/target.split('#')[0]).exists(),f.name+' -> '+target
    for name in json.loads((P/'handoff.json').read_text())['required_deliverables']:assert (P/name).is_file()
    return dict(evidence_urls_syntax_checked=count,live_link_status='NOT_RUN; no mass network calls')
check('LINK_LOCATORS_AND_REQUIRED_FILES',urls_and_files)
def scope():
    base=PINS['root']
    committed=subprocess.check_output(['git','diff','--name-only',base,'HEAD'],text=True).splitlines()
    working=subprocess.check_output(['git','diff','--name-only','HEAD'],text=True).splitlines()
    staged=subprocess.check_output(['git','diff','--cached','--name-only'],text=True).splitlines()
    untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],text=True).splitlines()
    for path in committed+working+staged+untracked:assert path.startswith(PREFIX),path
    assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='research/night-passport-bridge-20261110'
    forbidden={'raw','node_modules','.venv','__pycache__','.runtime'}
    for f in P.rglob('*'):assert not (set(f.relative_to(P).parts)&forbidden),str(f)
    assert sum(f.stat().st_size for f in P.rglob('*') if f.is_file())<1_000_000
    subprocess.run(['git','diff','--check'],check=True,capture_output=True)
    return 'All committed/staged/working/untracked task writes confined to assigned scope; no runtime/dependencies'
check('SAFE_WRITE_SCOPE',scope)
if '--write-checks' not in sys.argv:
    def manifests():
        m=json.loads((P/'output_manifest.json').read_text());listed={r['path']:r for r in m['files']}
        expected={f.relative_to(P).as_posix() for f in P.rglob('*') if f.is_file() and f.name not in {'output_manifest.json','delivery_receipt.json'}}
        assert set(listed)==expected,(set(listed)^expected)
        for name,r in listed.items():
            raw=(P/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==r['sha256'],name;assert len(raw)==r['bytes']
        return dict(hashed_outputs=len(listed))
    check('OUTPUT_MANIFEST',manifests)
status='PASS' if all(r['status']=='PASS' for r in results) else 'FAIL'
out=dict(status=status,check_scope='Self-check of synthesis transfer/provenance/package only; not independent review or economic recalculation',checks=results)
if '--write-checks' in sys.argv:(P/'checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if status=='PASS' else 1)
