#!/usr/bin/env python3
"""Format synthesis and hash its safe artifacts; never read a moving source folder."""
import csv
import datetime as dt
import hashlib
import json
import pathlib
from read_sources import PINS

P=pathlib.Path(__file__).resolve().parent
def rows(name):
    with (P/name).open() as f:return list(csv.DictReader(f))
def dump(name,obj): (P/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
E={r['evidence_id']:r for r in rows('evidence_index.csv')}
C=rows('claims.csv')
titles={'МОЖНО_СЕЙЧАС':'Можно использовать сейчас','УСЛОВНЫЙ_СЦЕНАРИЙ':'Условные сценарные формулировки','НЕЛЬЗЯ_УТВЕРЖДАТЬ':'Нельзя утверждать'}
text=['# Формулировки для паспорта','',
      'Это заготовки, из которых команда выбирает нужные строки. Они не составляют финальный паспорт и не утверждают стратегию. Для короткого паспорта сохраняйте условия, которые меняют смысл вывода. Проверенная арифметика чужого пакета здесь приведена по его независимому review; этот исполнитель её заново не запускал.','',
      'Срез: exact inputs из brief на `77343ca9dccc14d60c51d4559485646219ecd1cd`. Для каждого E-ID полные SHA, путь, локатор, hash и grain приведены в [evidence_index.csv](evidence_index.csv). Первая группа содержит также подтверждённые ограничения знания; она не означает рыночную приёмку.','']
for group,title in titles.items():
    text+=['## '+title,'']
    for c in C:
        if c['group']!=group:continue
        text+=['### '+c['claim_id'],'']
        if group=='НЕЛЬЗЯ_УТВЕРЖДАТЬ':text+=['**Недопустимый тезис:** '+c['ready_russian_wording'],'']
        else:text+=[c['ready_russian_wording'],'']
        links=[]
        for id in c['evidence_ids'].split(';'):
            e=E[id]; links.append(f"[{id}]({e['github_url']}) — {e['source_commit'] or 'HTTP receipt'}; {e['locator']}")
        text+=['Доказательство: '+'; '.join(links)+'.','',
               '**Scope:** `'+c['acceptance_scope']+'`. '+c['use_condition'],'',
               '**Граница:** '+c['prohibited_extension'],'']
(P/'passport_claims.md').write_text('\n'.join(text))

readings=json.loads((P/'personal_readings.json').read_text())
by_ref={(e['source_commit'],e['source_path']):e for e in E.values() if e['source_commit']}
sources=[]
for r in readings:
    r=dict(r); e=by_ref.get((r['commit'],r['path']))
    r['grain']=e['grain'] if e else 'instruction/inventory/report; see exact path'
    r['inspection_locator']=e['locator'] if e else 'instruction or inventory inspected; not a full independent audit'
    r['evidence_id']=e['evidence_id'] if e else None
    r['reading_boundary']='Git blob bytes obtained and hashed. Listed sections/selected rows inspected; not every source or model pipeline personally re-audited. Some large outputs inspected in excerpts.'
    sources.append(r)
dump('source_manifest.json',dict(package_id='passport-bridge-20261110-v1',prepared_base=PINS['root'],
    source_policy='exact git show; only new official-page wording HTTP capture allowed; no live/moving context22 inputs',
    sources=sources,new_public_source_receipt=json.loads((P/'official_case_receipt.json').read_text()),
    primary_raw_policy='No full raw, articles, auth/cookies/PII, dependencies or runtime snapshots committed.',
    memory_boundary='Registry informed metric/provenance caution only; no memory result is evidence in this package.'))
checks=json.loads((P/'checks.json').read_text()) if (P/'checks.json').exists() else {'status':'PENDING'}
dump('handoff.json',dict(package_id='passport-bridge-20261110-v1',status='READY_FOR_COORDINATOR_SYNTHESIS',
    author='Sol 6.1 xhigh; bounded research synthesis',prepared_base=PINS['root'],
    branch='research/night-passport-bridge-20261110',scope='context/23_night_run_20261110/passport_bridge/',
    content_cutoff='Exact SHA set supplied by brief; no automatic upgrades. New official wording receipt at '+json.loads((P/'official_case_receipt.json').read_text())['requested_at_utc'],
    first_package_deadline_msk='2026-11-10T08:20:00+03:00',global_stop_msk='2026-11-10T10:00:00+03:00',
    entrypoint='README.md',requirements_matrix='requirements_evidence.csv',claims='claims.csv',claim_prose='passport_claims.md',
    competitor_examples='competitor_and_svx_gaps.csv',decisions='decision_options.csv',next_day_plan='next_day_plan.md',agent_process='agent_method_appendix.md',
    required_deliverables=['requirements_evidence.csv','passport_claims.md','claims.csv','competitor_and_svx_gaps.csv','decision_options.csv','next_day_plan.md','agent_method_appendix.md'],
    counts=dict(requirements=len(rows('requirements_evidence.csv')),claims=len(C),competitor_svx_entries=len(rows('competitor_and_svx_gaps.csv')),open_decisions=len(rows('decision_options.csv'))),
    main_gap='Joint final 8–12-route network with common budget/resource, owner parameter ranges and consistent company-market denominator.',
    pending_inputs=dict(frontier=PINS['frontier'],methods_v5=PINS['methods5'],timebase_correction=PINS['timebase']),
    inherited_holds=['Original SVX source lineage:129 rows/28 cards/58 mappings','Delay served-all unavailable; original timebase/recovery HOLD',
        'No observed endpoint OD, actual performed flights, actual full budget, dispatch or launch acceptance'],
    own_acceptance=['EXACT_GIT_BYTES_HASHED','REQUIREMENT_WORDING_CHECKED_HTTP','SYNTHESIS_AND_TRANSFER_CHECKED'],
    independent_review='NOT_RUN_FOR_THIS_SYNTHESIS; own prose review is not independent acceptance',
    checks_status=checks['status'],not_run=['new economic model','UI/browser','full author replay','rerun upstream reviews','paid/market execution','chosen strategy','new children/threads/messages/schedules'],
    next_action='Coordinator may consume the pinned safe scope; decisions and further reviews require their own exact inputs. This worker ends without another automatic cycle.',
    delivery='Payload commit and receipt commit recorded separately after push; final remote HEAD equality verified; no circular self-SHA embedded.',
    safety=dict(writes_only_assigned_scope=True,force=False,merge=False,rebase=False,pull_request=False,public_report_or_site_changed=False,dashboard_or_owners_changed=False,
        paid_services=False,infrastructure=False,automatic_continuation=False)))

# The manifest does not hash itself. Delivery receipts can be appended in a later
# commit and are checked separately against the immutable payload commit.
excluded={'output_manifest.json','delivery_receipt.json'}
outputs=[]
for f in sorted(P.rglob('*')):
    if not f.is_file() or f.name in excluded:continue
    raw=f.read_bytes();outputs.append(dict(path=f.relative_to(P).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
dump('output_manifest.json',dict(package_id='passport-bridge-20261110-v1',algorithm='SHA256',
    exclusions=['output_manifest.json (self-reference)','delivery_receipt.json (post-push receipt, separate commit)'],files=outputs))
print('Formatted claims, source/output manifests and handoff; status '+checks['status'])
