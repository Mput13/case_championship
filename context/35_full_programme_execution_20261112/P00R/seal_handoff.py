#!/usr/bin/env python3
"""Seal already committed payload. The next commit contains envelopes only."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
PREFIX=str(OUT.relative_to(ROOT))+'/'

def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)

def dump(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def digest(path):
    b=path.read_bytes()
    return dict(file=path.name,sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))

if __name__=='__main__':
    commit=git('rev-parse','HEAD').decode().strip()
    branch=git('branch','--show-current').decode().strip()
    review=json.loads((OUT/'method_review.json').read_text())
    files=[]
    for path in sorted(OUT.iterdir()):
        if path.name in ['handoff.json','artifact_manifest.json']:
            continue
        assert path.is_file(),path
        assert git('show',commit+':'+PREFIX+path.name)==path.read_bytes(),path
        files.append(dict(**digest(path),commit_scope='review_payload_commit'))
    checks=json.loads((OUT/'checks.json').read_text())
    assert checks['status']=='PASS' and checks['cases_checked']==20
    envelope=dict(
        package='P00R',status='COMPLETE',programme_status='NOT_COMPLETE_NOT_ASSESSED',
        role='methods_review',model='gpt-6-astra',effort='xhigh',
        created_at=datetime.now(timezone.utc).isoformat(),branch=branch,
        commit=commit,review_payload_commit=commit,
        commit_scope='Exact commit of every payload file below. handoff.json and artifact_manifest.json are added in a subsequent envelope-only commit; its exact SHA is supplied in final handback. No file can contain its own Git commit hash.',
        delivery_commit_command='git log -1 --format=%H -- '+PREFIX+'handoff.json',
        input_manifest='input_manifest.json',files=files,artifact_manifest='artifact_manifest.json',
        inputs=dict(plan=review['reviewed_plan_commit'],author_baseline=review['author_baseline_commit'],five_city=review['five_city_commit'],producer_packages_received=[]),
        conclusion='CHANGES: принципы постановки приняты; до содержательного общего расчёта закрепить конкретные схемы и инварианты F01–F06. F07 ограничивает только долю/№2. P06 может приступать к реализации сейчас.',
        findings=[dict(id=f['finding_id'],title=f['title'],severity=f['severity'],blocks=f['blocks'],minimum_fix=f['minimum_fix']) for f in review['findings']],
        practical_inputs_for_P06=['schema_patch.csv','contract_addendum.json','counterexample_inputs.json','minimal_counterexamples.csv'],
        own_checks=dict(arithmetic_cases=20,status='PASS',pinned_inputs=11,register_and_references='PASS',write_boundary='PASS',evidence='checks.json',latest_targeted_check='checks_subset.json',not_engine_acceptance=True),
        commands=['python3 '+PREFIX+'run_checks.py','python3 '+PREFIX+'run_checks.py --cases CE13 --verify-handoff'],
        assumptions=dict(used_ids=review['used_assumption_ids'],register=['assumptions_register.csv','assumptions_register.json'],delta='assumption_changes.csv',historical_ids_not_adopted=review['historical_assumptions_referenced_not_adopted']),
        clarifications=dict(file='clarification_requests.csv',confirmed=['Q-P00R-001','P04-Q001'],unresolved=[]),
        remaining_fields=review['acceptable_unknowns'],specific_requests=review['exact_next_requests'],
        boundaries=review['not_run'],source_read_boundary=review['source_read_boundary'],
        changes_outside_assigned_package=False,children_created=False,full_network_runs=False,
        purchases_payments_bookings_external_messages_restarts_site_publication=False,
        communication=dict(question_delivered_to_coordinator=True,
                           early_artifact_notice='NOT_DELIVERED',
                           error='thread_not_sendable: Thread 91bc9ad6-4e9f-4954-8714-1e4366064b78 has no running turn that can be steered.',
                           diagnosis='No running parent turn for mode=steer; no service failure inferred, no restart or child diagnostic launched under explicit no-children boundary.',
                           recovery='Deliver committed final result through task completion; no repeated steer attempts.'),
        integration='Coordinator pins exact payload/envelope SHA and manifest; integrate only P00R. No merge/rebase or modification of foreign branches performed.',
        publish_receipt='Own-branch commit/push and remote SHA verification are reported in the final handback after this envelope is committed.'
    )
    dump('handoff.json',envelope)
    dump('artifact_manifest.json',dict(version=1,package='P00R',review_payload_commit=commit,
                                     files=files+[dict(**digest(OUT/'handoff.json'),commit_scope='envelope_commit')],
                                     self_hash_policy='Manifest excludes itself. Its SHA256 and exact envelope Git commit are supplied in final handback.'))
    print(json.dumps(dict(payload_commit=commit,payload_files=len(files),manifest_sha256=digest(OUT/'artifact_manifest.json')['sha256']),ensure_ascii=False))
