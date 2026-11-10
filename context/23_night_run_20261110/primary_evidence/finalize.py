#!/usr/bin/env python3
"""Self-contained delivery manifest and acceptance boundaries, only in own package scope."""
import csv,datetime,hashlib,json,pathlib,subprocess
R=pathlib.Path(__file__).resolve().parent;SCOPE='context/23_night_run_20261110/primary_evidence/'
now=datetime.datetime.now(datetime.timezone.utc).isoformat()

def j(n):return json.loads((R/n).read_text())
def save(n,x):(R/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def rows(n):return list(csv.DictReader((R/n).open()))
validation=j('validation.json');assert all(x['pass_'] for x in validation['checks'])
# Confirm six parent receipts against actual preserved public bodies, without re-collecting.
parent=pathlib.Path('/Users/a/agent-audit-2026-09/case_championship/context/22_case_alignment_20261110')
parent_checks=[]
for rec in j('parent_primary_receipts.json')['acquisitions']:
 p=parent/rec['local_path'];actual=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
 parent_checks.append(dict(source_id=rec['source_id'],sha256=rec['sha256'],actual_sha256=actual,status='MATCH' if actual==rec['sha256'] else 'NOT_LOCALLY_AVAILABLE' if actual is None else 'MISMATCH'))
assert not any(x['status']=='MISMATCH' for x in parent_checks)
# No tracked source/dashboard/Site file may have been modified by this role.
status=subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],text=True).splitlines()
outside=[l for l in status if l[3:] and not l[3:].startswith(SCOPE)]
assert not outside, outside
assert subprocess.run(['git','check-ignore','-q',SCOPE+'raw/probe']).returncode==0
# Validate all delivered CSV field counts and card foreign keys.
counts={}
for p in R.glob('*.csv'):
 with p.open(newline='') as f:
  rr=list(csv.reader(f));assert rr and all(len(r)==len(rr[0]) for r in rr),p.name;counts[p.name]=len(rr)-1
cards=rows('route_product_cards.csv');ids={x['card_id'] for x in cards};assert len(ids)==len(cards)
assert all(x['card_id'] in ids for x in rows('adapter_mapping.csv'))
assert all(c['duration_usable_for_network']=='false' for c in cards if c['clock_consensus_status']=='CONFLICT_HOLD')
# Primary fact register: data level and period precede any downstream interpretation.
receipts={r['source_id']:r for r in j('http_receipts.json')};facts=[]
def fact(sid,entity,metric,value,unit,qualifier,start,end,level,unknown):
 r=receipts[sid];facts.append(dict(source_id=sid,entity=entity,metric=metric,value=value,unit=unit,qualifier=qualifier,period_start=start,period_end=end,evidence_level=level,source_url=r['url'],captured_at_utc=r['captured_at_utc'],raw_sha256=r['sha256'],source_commit='',author_ref='publisher: '+('Росавиация' if sid=='kuf_mro_favt' else 'Оренбург airport' if sid=='ren_pax_recheck' else 'Red Wings'),collector='Sol 6.1 xhigh',value_status='PUBLISHED_PRIMARY_SCOPED',acceptance_scope='RAW_HASH_VERIFIED;EXTRACTION_CHECKED;SOURCE_SUPPORTED_IN_STATED_SCOPE',unknown=unknown))
fact('kuf_mro_favt','KUF','SSJ maintenance station started',1,'published event','event, not current availability','2025-04-30','2025-04-30','PRIMARY_REGULATOR_EVENT','RW contract; current scope certificate; free capacity; first4Ycompletion')
fact('ren_pax_recheck','REN','airport annual passenger movements',951000,'airport passengers as published','strictly greater than; exact total UNKNOWN','2025-01-01','2025-12-31','PRIMARY_AIRPORT_ROUNDED_LOWER_BOUND_RECHECK','exact integer; rounding method; endpoint journeys')
fact('svx_results_2025','RW@SVX','hub passenger aggregate',800000,'passengers per publisher counting rule','rounded 800 thousand; reported not bookings audit','2025-01-01','2025-12-31','PRIMARY_CARRIER_REPORTED_AGGREGATE','counting rule; transfer absolute/share; P&L')
fact('svx_results_2025','RW@SVX','hub traffic annual growth',15,'percent vs prior year','carrier reported; no causal attribution','2025-01-01','2025-12-31','PRIMARY_CARRIER_REPORTED_RATIO','unrounded numerator/denominator; unique OD')
fact('svx_results_2025','RW@SVX','transfer passenger growth factor',2.5,'multiplicative ratio vs prior year','growth factor, not share or absolute demand','2025-01-01','2025-12-31','PRIMARY_CARRIER_REPORTED_RATIO','absolute transfers; prior base; segment/journey accounting; causal effect')
with (R/'primary_facts.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,list(facts[0]));w.writeheader();w.writerows(facts)
counts['primary_facts.csv']=len(facts)
verification=dict(verified_at_utc=now,csv_rows=counts,parent_raw_hash_checks=parent_checks,scope_check='PASS: git status only own folder',raw_ignore_check='PASS',card_foreign_keys='PASS',clock_hold_propagation='PASS',status='READY_FOR_INDEPENDENT_REVIEW; not independent acceptance')
save('package_checks.json',verification)
# File manifest has no circular hashes of itself/handoff. Git identifies their exact bytes.
grains={'source_registry.csv':'source × capture/receipt','gap_resolution.csv':'airport/route × precise gap','route_product_cards.csv':'directed market × source-specific product or explicit unknown','coverage.csv':'directed market × period','coverage_summary.csv':'candidate × market role','dated_evidence.csv':'source × directional dated service','service_identity.csv':'normalized published service key × multiple source rows','schedule_conflicts.csv':'published service key with incompatible clocks','ufa_schedule_rules.csv':'source × HTML card with active weekdays and explicit dates','ufa_dated_services.csv':'UFA published rule × date','endpoint_schedule_rules.csv':'KUF/GSV source rule with explicit seasonal year assignment','svx_observations.csv':'historical or reported hub fact × period × source','ground_alternatives.csv':'city pair × rail direction with historical period','adapter_mapping.csv':'candidate × evidence card','primary_facts.csv':'primary quantitative/event fact × qualified period'}
files=[]
for p in sorted(R.iterdir()):
 if not p.is_file() or p.name in ['manifest.json','handoff.json']:continue
 b=p.read_bytes();files.append(dict(path=p.name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),grain=grains.get(p.name,'script / scoped report / receipt; see file'),rows=counts.get(p.name)))
manifest=dict(package_id='night-primary-evidence-20261110-v1',created_at_utc=now,collector='Sol 6.1 xhigh / research sub-agent',source_base_commit='2191b180aed5191735d44ba6c7f190e5d8e3934a',scope=SCOPE,source_locks='source_lock.json',parent_context='parent_context_lock.json',raw_receipts='http_receipts.json',files=files,raw_local_bytes=sum(r.get('bytes',0) for r in receipts.values()),raw_git_policy='ignored local public bodies only; new inputs require new ids; no auth/cookie/PII',grain_policy='source/period/unit/evidence levels stay distinct',acceptance_scope=validation['acceptance_scope'],scoped_source_supported_fact_register='primary_facts.csv',independent_review='NOT_RUN',outside_scope=validation['outside_scope'],delivery=dict(remote='origin',branch='research/night-primary-evidence-20261110',push='explicit HEAD:refs/heads/research/night-primary-evidence-20261110; no force; no PR'),self_hash='excluded to prevent recursive manifest; exact version identified by Git commit')
save('manifest.json',manifest)
save('handoff.json',dict(package_id=manifest['package_id'],status='READY_FOR_INDEPENDENT_REVIEW',finished_at_utc=now,branch='research/night-primary-evidence-20261110',source_base_commit=manifest['source_base_commit'],delivery_commit_locator='git log -1 --format=%H -- '+SCOPE+'handoff.json; exact pushed SHA reported separately after commit',manifest='manifest.json',manifest_sha256=hashlib.sha256((R/'manifest.json').read_bytes()).hexdigest(),findings='findings.md',commands='commands.md',primary_deltas=['KUF SSJ MRO station primary opening event2025; current RW access/capacity UNKNOWN','SVX2025 carrier-reported rounded800k, +15%, transfers×2.5; no P&L or transfer share','UFA MRV4 andNJC4 per direction, GOJ2 target-week; KUF MRV3/NJC2 seasonal-year-assigned','core OMS-MRV2 andOMS-NJC3 joined, explicitly reused','source duplicate/conflicting clocks preserved; no frequency-to-capture inference'],known_closed_gaps_preserved=['OMS MRO03Dec2024','REN2025 >951000; exact total UNKNOWN'],artifact_counts=dict(cards=counts['route_product_cards.csv'],directed_coverage_markets=counts['coverage.csv'],dated_source_rows=counts['dated_evidence.csv'],unique_published_service_keys=validation['unique_published_service_keys']),acceptance_scope=manifest['acceptance_scope'],source_supported_scope='Only qualified facts in primary_facts.csv and sourced qualitative interpretations; not sales/economics',critical_holds=['12service keys with conflicting published clocks; exact connection time HOLD','KUF/GSV source rules omit year; winter2026/27 assignment explicit','single-date KUF/OMS UFA services cannot be carried into target week','deduplicate source publications before any supply aggregate','H_UFA4 proposal differs from earlier RELAXED scenario selection'],remaining_unknowns=['current REN transfer zone/MCT/SSJ MRO','current OMS competitive base and physical RW base','current MRO capacity/contracts','full endpoint product universe; connecting ticket/MCT/ground date-matched products','seats/final comparable fares/net yield/observed endpoint demand/2027-28 programme'],next_actions=['independent review exact Git package; repeat critical calendar and provenance checks','join scoped facts/coverage into comparison adapter without changing frozen author results','preserve uncertain periods and clock conflicts; select explicit new input_set if resolving','no ranking/economics uplift solely from this push'],no_changes=['colleague source trees','dashboard','public Site','model weights/defaults','frozen author results'],independent_review='NOT_RUN',financial_or_launch_acceptance='OUTSIDE_SCOPE'))
print(json.dumps(dict(status='READY_FOR_INDEPENDENT_REVIEW',files=len(files),csv_rows=counts,manifest_sha256=hashlib.sha256((R/'manifest.json').read_bytes()).hexdigest()),ensure_ascii=False))
