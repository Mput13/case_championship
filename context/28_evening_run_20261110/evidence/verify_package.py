#!/usr/bin/env python3
"""Read-only package verification. --seal writes validation and a content manifest."""
import pathlib,json,hashlib,csv,subprocess,re,sys,collections
R=pathlib.Path(__file__).resolve().parent
SCOPE='context/28_evening_run_20261110/evidence/'
checks=[]
def check(name,ok,details=None):
 checks.append(dict(check=name,pass_=bool(ok),details=details));assert ok,(name,details)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(n):return list(csv.DictReader(open(R/n)))
inputs=json.loads((R/'input_manifest.json').read_text())
for x in inputs:
 p=R/x['snapshot'];check('input:'+x['path'],p.exists() and sha(p)==x['sha256'] and p.stat().st_size==x['bytes'])
receipts=[]
for p in sorted((R/'raw/web').glob('*/receipt.json')):
 x=json.loads(p.read_text());receipts.append(x)
 if x.get('raw_path'):check('raw:'+x['source_id'],sha(R/x['raw_path'])==x['sha256'])
 if x.get('text_path'):check('text:'+x['source_id'],sha(R/x['text_path'])==x['text_sha256'])
active={'C01','C03','C04','C07','C10','C14','C17','C31','C33','C35'}
links=rows('pair_hypothesis_join.csv');pairs=rows('pair_registry.csv');pkeys={x['route'] for x in pairs}
check('all10IDs',set(x['hypothesis'] for x in links)==active)
check('all45pairs unique',len(pkeys)==len(pairs)==45)
check('pair join',not ({x['route'] for x in links}-pkeys))
check('applicability join',{x['route'] for x in rows('subsidy_applicability.csv')}==pkeys)
check('readout10',{x['hypothesis'] for x in rows('hypothesis_readout.csv')}==active)
check('no false complete or absence claims',all(x['complete_market']=='False' and x['competitor_absence_established']=='False' for x in pairs))
check('source coverage preserved',sum(x['coverage_status']=='GAP_NOT_ABSENCE' for x in pairs)==22)
for x in rows('subsidy_controls.csv')+rows('fleet_facts.csv'):
 locator=x['locator'];check('locator:'+x['id'],'NOT_FOUND' not in locator and 'RAW_NOT' not in locator)
 path,nums=locator.rsplit(':',1);text=(R/path).read_text().split('\n')
 check('line range:'+x['id'],all(0<int(v)<=len(text) and text[int(v)-1].strip() for v in nums.split(',')))
control={x['id']:x for x in rows('subsidy_controls.csv')}
check('fare grant joint condition present','ALL economy seats' in control['SUB15']['fact'] and 'unconstrained yield' in control['SUB15']['model_consequence'])
lines=(R/'raw/web/favt_regional_rules/text.txt').read_text().split('\n')
capline=next(x for x in lines if '84 - 103 **' in x)
primary_caps=[int(x.replace(' ','')) for x in re.findall(r'\d{3} \d{3}',capline)]
check('cap grid vs primary extracted row',primary_caps==[int(x['cap_rub_per_oneway_flight']) for x in rows('subsidy_cap_84_103_seats.csv')],primary_caps)
check('visually inspected cap example805km',next(x for x in rows('subsidy_cap_examples.csv') if x['route']=='OMS-SVX')['appendix1_cap_rub_oneway']=='225989')
fareline=next(x for x in lines if '2 017' in x and '10 953' in x)
primary_fares=[int(x.replace(' ','')) for x in re.findall(r'\d{1,2} \d{3}',fareline)]
check('fare grid vs primary extracted row',primary_fares==[int(x['base_special_fare_rub_including_vat']) for x in rows('subsidy_special_fare_grid.csv')],primary_fares)
check('joint condition in route adapter',all('ALL economy seats' in x['joint_fare_obligation'] for x in rows('subsidy_applicability.csv')))
sourcechecks=json.loads((R/'subsidy_source_checks.json').read_text());check('HTML XLSX normalization equality',sourcechecks['normalized_row_multiset_equal'] and sourcechecks['official_html_rows']==sourcechecks['official_xlsx_rows']==423)
rawpdf=(R/'raw/web/favt_2026_pdf/text.txt').read_text();check('different programPDF preserved','22-68861-00481' in rawpdf and 'Аврора' in rawpdf)
ss=rows('subsidy_route_matches.csv');check('IJK RW November row',any(x['route']=='IJK-SVX' and 'Ред Вингс' in x['airline'] and '01.11.2026' in x['period'] for x in ss))
obs=rows('service_observations.csv');inst=rows('dated_service_instances.csv');recs=rows('dated_service_records.csv')
check('all instances in named week',all('2026-12-07'<=x['date']<='2026-12-13' for x in inst))
keys=[(x['origin'],x['destination'],x['date'],x['flight']) for x in inst];check('unique departure keys',len(keys)==len(set(keys)))
check('duplicates not additive',len(recs)>len(inst) and all(x['oneway_departures']=='1' for x in inst))
check('source conflicts retained',sum(x['clock_or_type_conflict']=='True' for x in inst)==12)
ufa_omsk=[x for x in obs if x['source_id']=='ufa_omsk'];check('active weekday CSS respected',bool(ufa_omsk) and all(x['weekdays']=='Сб' for x in ufa_omsk))
check('OMS KJA published2out',sum(x['origin']=='OMS' and x['destination']=='KJA' for x in inst)==2)
check('KUF NJC scheduled2not program3',sum(x['origin']=='KUF' and x['destination']=='NJC' for x in inst)==2)
check('C01 real timezone example',any(x['hypothesis']=='C01' and x['path']=='NJC>SVX>MRV' and float(x['elapsed_max_minutes'])==545 and float(x['connection_min_minutes'])==220 for x in rows('alternative_timing_examples.csv')))
check('four delivery branches',{x['scenario'] for x in rows('fleet_delivery_gates.csv')}=={'on_time_staged','partial','delay','none'})
changed=subprocess.check_output(['git','diff','--name-only','4a9971beeacbc40559943eae05b9004c90165917'],cwd=R,text=True).splitlines()
unknown=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=R,text=True).splitlines()
# Git paths are repository-relative for diff, cwd-relative for ls-files.
check('tracked diff scope',all(x.startswith(SCOPE) for x in changed))
check('untracked scope',all(not x.startswith('../') for x in unknown))
validation=dict(status='PASS_OFFLINE_PROVENANCE_JOIN_EXTRACTION_ONLY',checks_passed=len(checks),git_inputs=len(inputs),http_receipts=len(receipts),raw_hashes=sum(bool(x.get('raw_path')) for x in receipts),text_hashes=sum(bool(x.get('text_path')) for x in receipts),pairs=len(pairs),hypothesis_route_links=len(links),service_records=len(obs),dated_publication_records=len(recs),unique_published_departures=len(inst),source_conflicts=12,uncovered_pairs=22,checks=checks,NOT_RUN=['independent source review','booked protected journey','final20kg quote','actual residual seat inventory','2027/2028 award or payment proof','tail-level commercial dispatch/resource acceptance','dated rail/ground quote'])
if '--seal' in sys.argv:
 (R/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
 files=[p for p in sorted(R.rglob('*')) if p.is_file() and p.name!='output_manifest.json' and '__pycache__' not in p.parts]
 manifest=[dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=sha(p)) for p in files]
 (R/'output_manifest.json').write_text(json.dumps(dict(files=manifest,total_files=len(files),total_bytes=sum(x['bytes'] for x in manifest),scope=SCOPE),ensure_ascii=False,indent=2)+'\n')
elif (R/'output_manifest.json').exists():
 m=json.loads((R/'output_manifest.json').read_text());check('output manifest',all((R/x['path']).exists() and sha(R/x['path'])==x['sha256'] for x in m['files']))
print(json.dumps({k:v for k,v in validation.items() if k!='checks'},ensure_ascii=False,indent=2))
