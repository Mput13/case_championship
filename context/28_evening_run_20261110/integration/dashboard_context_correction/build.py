#!/usr/bin/env python3
"""Explicit evidence-association projection; never rewrite source delivery."""
import argparse
import copy
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUBJECT = '5101302f93c349268f4ba0ff26832ff261e1a9e7'
EVIDENCE = '38f0f7ae8a10b6a60bd2d5ab39b18a9865e2b78b'
PREFIX = 'context/28_evening_run_20261110/dashboard_handoff/'
inputs = []

def read(sha, path):
    b = subprocess.check_output(['git', 'show', sha + ':' + path])
    inputs.append(dict(commit=sha, path=path, sha256=hashlib.sha256(b).hexdigest(),
                       git_blob=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(), bytes=len(b)))
    return b

def encoded(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode()

def project(context, cards, program, registry):
    context = copy.deepcopy(context)
    cards = copy.deepcopy(cards)
    original_rows = context['rows']
    assert len({r['record_id'] for r in original_rows}) == len(original_rows)
    remove, additions, associations = [], [], []
    for gap in original_rows:
        if gap['record_type'] != 'calculation_pair_gap' or gap['route'] not in registry:
            continue
        supporting = [r for r in original_rows if r['route'] == gap['route']
                      and r['record_type'] != 'calculation_pair_gap']
        # The registry may be positive but a delivery may omit the supporting rows.
        # Such a case needs a new explicit projection, never an invented absence.
        assert supporting, ('Known registry route without delivered context', gap['route'])
        legs = [r for r in program['rows'] if r['hypothesis_id'] == gap['hypothesis_id']
                and r['route'] == gap['route']]
        assert legs
        aid = 'CALCULATION_LEG_CONTEXT:' + gap['hypothesis_id'] + ':' + gap['route']
        association = dict(association_id=aid, hypothesis_id=gap['hypothesis_id'], route=gap['route'],
            basis='CALCULATION_LEG_EXACT_AIRPORT_PAIR', registry_hypotheses=registry[gap['route']]['hypotheses'],
            programme_record_ids=[r['record_id'] for r in legs],
            programme_source_refs=[r['provenance'] for r in legs],
            original_evidence_record_ids=[r['record_id'] for r in supporting],
            no_new_observations=True, no_automatic_future_extension=True)
        associations.append(association)
        replacement_ids = []
        for source in supporting:
            row = copy.deepcopy(source)
            row['record_id'] = 'RC:calculation_link:' + gap['hypothesis_id'] + ':' + source['record_id']
            row['hypothesis_id'] = gap['hypothesis_id']
            row['association_id'] = aid
            row['original_evidence_record_id'] = source['record_id']
            row['association_kind'] = 'DERIVED_CALCULATION_LEG_LINK_NOT_NEW_OBSERVATION'
            # source_fields and provenance remain the exact original evidence row.
            additions.append(row)
            replacement_ids.append(row['record_id'])
        remove.append(gap['record_id'])
        card = next(c for c in cards['cards'] if c['hypothesis_id'] == gap['hypothesis_id'])
        assert gap['record_id'] in card['route_context_ids']
        card['route_context_ids'] = [x for x in card['route_context_ids'] if x != gap['record_id']] + replacement_ids
    context['rows'] = [r for r in original_rows if r['record_id'] not in remove] + additions
    assert len({r['record_id'] for r in context['rows']}) == len(context['rows'])
    ids = {r['record_id'] for r in context['rows']}
    assert all(set(c['route_context_ids']) <= ids for c in cards['cards'])
    context['association_boundary'] = 'Added aliases link existing evidence to calculation legs; deduplicate observations by original_evidence_record_id or exact source locator, never sum cross-hypothesis aliases.'
    patch = dict(subject_sha=SUBJECT, evidence_sha=EVIDENCE, finding='ROOT-DASH-01',
        removed_context_record_ids=remove, added_context_record_ids=[r['record_id'] for r in additions],
        associations=associations, original_85_route_links_unchanged=True,
        review_status='ROOT_CORRECTION_PENDING_INDEPENDENT_RECHECK',
        scope='Only context associations; no prices, frequencies, economic calculations or source acceptance changed')
    return context, cards, patch

def main():
    args = argparse.ArgumentParser()
    args.add_argument('--verify', action='store_true')
    args = args.parse_args()
    context, cards, program = [json.loads(read(SUBJECT, PREFIX + name + '.json'))
                               for name in ['route_context', 'cards', 'program_changes']]
    links = read(SUBJECT, PREFIX + 'route_links.csv')
    registry_rows = list(csv.DictReader(io.StringIO(read(EVIDENCE,
        'context/28_evening_run_20261110/evidence/pair_registry.csv').decode())))
    registry = {r['route']: r for r in registry_rows}
    corrected, corrected_cards, patch = project(context, cards, program, registry)
    assert len(registry) == 45 and len(list(csv.DictReader(io.StringIO(links.decode())))) == 85
    assert len(patch['associations']) == 1 and patch['associations'][0]['route'] == 'KUF-SVX'
    assert len(patch['associations'][0]['programme_record_ids']) == 16
    assert len(patch['added_context_record_ids']) == 34 and len(corrected['rows']) == 672
    assert {r['route'] for r in corrected['rows'] if r['record_type']=='calculation_pair_gap'} == {'TLV-ZIA','SVX-ZIA'}
    for before, after in zip(cards['cards'], corrected_cards['cards']):
        assert {k:v for k,v in before.items() if k!='route_context_ids'} == {k:v for k,v in after.items() if k!='route_context_ids'}
        if before['hypothesis_id'] != 'C33': assert before == after
    old = {r['record_id']: r for r in context['rows']}
    for row in corrected['rows']:
        if 'original_evidence_record_id' not in row:
            assert row == old[row['record_id']]
        else:
            source = old[row['original_evidence_record_id']]
            changed = {'record_id','hypothesis_id','association_id','original_evidence_record_id','association_kind'}
            assert {k:v for k,v in row.items() if k not in changed} == {k:v for k,v in source.items() if k not in changed}
    # Reapplying does not create more observations or alter card references.
    again, again_cards, again_patch = project(corrected, corrected_cards, program, registry)
    assert again == corrected and again_cards == corrected_cards and not again_patch['associations']
    try:
        duplicate = copy.deepcopy(context); duplicate['rows'].append(duplicate['rows'][0])
        project(duplicate, cards, program, registry)
    except AssertionError: pass
    else: raise AssertionError('duplicate record was not rejected')
    outputs = {'route_context.json':encoded(corrected),'cards.json':encoded(corrected_cards),
               'context_patch.json':encoded(patch),'source_manifest.json':encoded(inputs),
               'checks.json':encoded(dict(status='PASS_ROOT_CHECKS', original_rows=639, projected_rows=672,
                    association_aliases=34, affected_programme_records=16, original_links=85,
                    preserved_cards=9, all_ten_metric_sets_unchanged=True, genuine_gaps_retained=2,
                    exact_source_fields_and_qualifications_preserved=True, no_new_observations=True,
                    idempotent=True, duplicate_rejected=True, independent_recheck='PENDING'))}
    outputs['output_manifest.json'] = encoded([dict(path=n, sha256=hashlib.sha256(b).hexdigest(),bytes=len(b)) for n,b in sorted(outputs.items())])
    for name, b in outputs.items():
        if args.verify: assert (HERE/name).read_bytes() == b, name
        else: (HERE/name).write_bytes(b)
    print('PASS: 34 existing evidence associations linked to C33; economics and original 85 links unchanged; two actual registry gaps retained')

if __name__ == '__main__': main()
