import hashlib,json,subprocess,sys
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
sha='dc1eb38d4c6b7c18386b3db4b1750166bb010ffd'
registry=[
('FNS_RATE','primary_fns','https://www.nalog.gov.ru/rn25/news/activities_fts/16602418/','2800 RUB/t through 2028','sources/find1.txt'),
('NK182','primary_law_fns_linked','https://nalog.garant.ru/fns/nk/92aac53b8daca11cbb548fe097eb3ed8/','Recipient and ownership from Russian supplier','sources/cash_find.txt'),
('NK200','primary_law_fns_linked','https://nalog.garant.ru/fns/nk/948c9c0734b6e944a4727660f2d5a027/','2.08, eligible refuelling volume, damper formula and 2027/28 reference prices','sources/primary201.txt'),
('NK201','primary_law_fns_linked','https://nalog.garant.ru/fns/nk/1efa800d5f474b5131ebc599024686d7/','Operator certificate, contract, invoices and uplift registers','sources/primary201section.txt'),
('NK192','primary_law_fns_linked','https://nalog.garant.ru/fns/nk/eee2dfc53c633b2005c2409be06a1d1e/','Monthly tax period','sources/cash_find.txt'),
('NK203','primary_law_fns_linked','https://nalog.garant.ru/fns/nk/53c63b880ad65ac5ac688c75b48629cb/','Ordinary reimbursement follows declaration, audit and decision','sources/cash_primary.txt'),
('NK204','primary_law_fns_linked','https://nalog.garant.ru/fns/nk/3ddec0358899d3ea2b04c72578ab41e7/','3.1(5),5 declaration and payment deadlines, not promised refund date','sources/cash_declaration_full.txt'),
('UFA_FUEL','primary_airport_pdf','https://www.airportufa.ru/upload/medialibrary/38c/4agy8jfom9bcf7504sc6m053wnfjo646.pdf','133200 RUB/t ex VAT from 17Aug2026; visually read','sources/ufa_fuel.pdf'),
('REUTERS_TMT','secondary_reuters_calculation','https://ru.themoscowtimes.com/2026/10/06/dempfer-dlya-aviakerosina-v-rf-vyros-v-15-raza-v-senavg-raschyot-reyter-a207929','All nine 2026 months, not RW payment receipts','sources/find1.txt')]
now=datetime.now(timezone.utc).isoformat()
(HERE/'source_registry.json').write_text(json.dumps([dict(id=i,kind=k,url=u,supports=s,receipt=p,checked_at_utc=now,status='READ',limit='Not actual Red Wings certificate, tax account or payment acceptance') for i,k,u,s,p in registry],ensure_ascii=False,indent=2)+'\n')
files=json.loads((HERE/'source_manifest.json').read_text());checks=[]
for r in files:
    if r['pin']=='gzip_derivative':continue
    rel = 'inputs/frozen/tochno_intercity.csv.gz' if r['pin']=='frozen_methods_raw' else f"inputs/{r['pin']}/{r['path']}"
    data=(HERE/rel).read_bytes();ok=hashlib.sha256(data).hexdigest()==r['sha256'];assert ok,rel;checks.append(rel)
calc=json.loads((HERE/'calculation.json').read_text())
assert round(calc['fixed_old_network'][-1]['contribution_rub']/1e6)==332
assert round(calc['fixed_new_network'][-1]['contribution_rub']/1e6)==503
assert round(calc['fixed_new_network_route_grant_scenario']['contribution_rub']/1e6)==952
assert calc['route_deletion_examples'][-1]['allocated_contribution_rub']<0<calc['route_deletion_examples'][-1]['full_minus_without_contribution_rub']
assert (HERE/'reproduce.stderr.txt').read_text()==''
assert hashlib.sha256((HERE/'sources/ufa_fuel.pdf').read_bytes()).hexdigest()=='2099eebce85b10435715ce3aae126866c51b4938f74affbba43432e9ea1bf644'
status=subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],text=True)
outside=[line for line in status.splitlines() if str(HERE.relative_to(Path.cwd()))+'/' not in line]
assert not outside,outside
provenance={'subject':sha,'previous':'066d3e288b41859b9ac33a3e571456a22d877795','previous_review':subprocess.check_output(['git','rev-parse','3f54697'],text=True).strip(),'review_base_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'branch':subprocess.check_output(['git','branch','--show-current'],text=True).strip(),'subject_identity':subprocess.check_output(['git','show','-s','--format=fuller',sha],text=True),'finished_checks_at_utc':now,'writes_only':str(HERE.relative_to(Path.cwd())),'bounds':'No owner edits, PR, merge/rebase/force, child agents, provider changes, browser, paid requests, outreach or restarts; requested reports to coordinator only.'}
(HERE/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n')
verification={'status':'PASS_SCOPED','checked_at_utc':now,'input_hashes_verified':len(checks),'same_old_source_replay':'PASS','fixed_OMS_sensitivities':'PASS','new_cap4_6_8_10':'PASS','OMS_base_sub_arithmetic':'PASS_CONDITIONAL_GRANT','allocated_money_reconciliation':'PASS','hub_summaries_reconciled':len(calc['inventory_reconciliation']),'direct_summaries_reconciled':len(calc['direct_inventory_reconciliation']),'prior_functions_unchanged':calc['unchanged_prior_functions'],'UFA_original_hash_and_visual_read':'PASS','scope_violation_paths':outside,'not_run':['Actual RW legal or tax-account acceptance','2027/28 fuel credit forecast','Full additional PnL/cash/donor and calendar/MCT acceptance','All-hub and direct solver','UI/browser'],'runtime_cleanup':'Check cleanup_receipt.json; capture_inputs.py recreates the sole raw derivative'}
(HERE/'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2)+'\n')
manifest=[]
for path in sorted(HERE.rglob('*')):
    if not path.is_file() or path.name in ['output_manifest.json','push_receipt.json','finalize.stdout.txt'] or 'runtime' in path.relative_to(HERE).parts:continue
    b=path.read_bytes();manifest.append(dict(path=str(path.relative_to(HERE)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
(HERE/'output_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'PASS_SCOPED','inputs_verified':len(checks),'output_files':len(manifest),'bytes':sum(r['bytes'] for r in manifest),'subject':sha}))
