#!/usr/bin/env python3
"""Deterministic metadata-only projection of primary17b; never writes owner inputs."""
import collections
import csv
import hashlib
import io
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent
PRIMARY = '17b4f348f15ea8695688d9435933cb4965568408'
TSIRI = '93fa5cf4a10ab67e05c93d19fc5375fc58ef9299'
BRIDGE = 'abc09bbb8e62d3513749b60b252d4521997acfc3'
PREFIX = 'context/23_night_run_20261110/primary_evidence/'
RECEIPTS = 'context/17_aircraft_route_review/evidence/sources.json'
TARGETS = {'svx_schedule', 'svx_schedule_arr'}
LOCK = []


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(commit, path):
    data = subprocess.check_output(['git', 'show', commit + ':' + path])
    LOCK.append(dict(source_commit=commit, path=path, sha256=sha(data), bytes=len(data)))
    return data


def table(data):
    return list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))


def save_json(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def save_csv(name, rows):
    with (ROOT / name).open('w', newline='') as out:
        writer = csv.DictWriter(out, list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def snapshot_id(source_id, raw_hash):
    return source_id + '@sha256:' + (raw_hash or 'UNAVAILABLE')


registry = table(blob(PRIMARY, PREFIX + 'source_registry.csv'))
dated = table(blob(PRIMARY, PREFIX + 'dated_evidence.csv'))
cards = table(blob(PRIMARY, PREFIX + 'route_product_cards.csv'))
frozen_manifest = json.loads(blob(PRIMARY, PREFIX + 'manifest.json'))
old_locks = json.loads(blob(PRIMARY, PREFIX + 'source_lock.json'))
correct_receipts = json.loads(blob(TSIRI, RECEIPTS))
receipts = {r['id']: r for r in correct_receipts if r['id'] in TARGETS}
assert set(receipts) == TARGETS
original_registry = {r['source_id']: r for r in registry}
assert len(original_registry) == len(registry)
affected = [r for r in dated if r['source_id'] in TARGETS]
assert len(affected) == 129
assert collections.Counter(r['source_id'] for r in affected) == {'svx_schedule': 65, 'svx_schedule_arr': 64}
assert all(r['html_sha256'] == receipts[r['source_id']]['sha256'] for r in affected)
assert all(r['html_sha256'] != original_registry[r['source_id']]['raw_sha256'] for r in affected)

# Pin exact upstream extraction rows too; row numbers in primary are CSV line numbers.
upstream = table(blob(TSIRI, 'context/17_aircraft_route_review/evidence/published_service_facts.csv'))
upstream_hashes = {r.get('html_sha256') or r.get('source_sha256') or r.get('raw_sha256') for r in upstream}
assert all(r['html_sha256'] in upstream_hashes for r in affected)

corrected = []
legacy = []
changes = []
for row in registry:
    r = dict(row)
    if r['source_id'] in TARGETS:
        c = receipts[r['source_id']]
        legacy.append(dict(source_id=r['source_id'], source_snapshot_id=snapshot_id(r['source_id'], r['raw_sha256']),
                           captured_at_utc=r['captured_at_utc'], raw_sha256=r['raw_sha256'], bytes=r['bytes'],
                           source_commit=TSIRI, receipt_path='context/12_network_economics/sources.json',
                           use_status='HISTORICAL_SNAPSHOT_NOT_SUPPORT_FOR_CONTEXT17_ROWS'))
        for key, val in [('captured_at_utc', c['accessed']), ('raw_sha256', c['sha256']),
                         ('bytes', str(c['bytes']) if 'bytes' in c else ''), ('http_status', str(c.get('http', ''))),
                         ('raw_local_path', 'upstream owner raw; body not recopied or reparsed'),
                         ('limits', 'Receipt joined to exact context17 snapshot; no new raw parse, clock resolution, sales or execution acceptance')]:
            changes.append(dict(source_id=r['source_id'], field=key, original=r[key], corrected=val))
            r[key] = val
        r['receipt_commit'] = TSIRI
        r['receipt_path'] = RECEIPTS
    else:
        r['receipt_commit'] = PRIMARY
        r['receipt_path'] = PREFIX + 'source_registry.csv'
    r['source_snapshot_id'] = snapshot_id(r['source_id'], r['raw_sha256'])
    corrected.append(r)
by_id = {r['source_id']: r for r in corrected}

# Existing cells (including times, hashes, quantities, clocks and source row numbers)
# are kept verbatim. The additional FK names the full snapshot, not only the URL.
dated_projection = []
for line, row in enumerate(dated, 2):
    r = dict(row)
    r['source_snapshot_id'] = snapshot_id(row['source_id'], row['html_sha256'])
    r['original_csv_line'] = str(line)
    r['lineage_correction_status'] = 'CORRECTED_RECEIPT_JOIN_PARENT_CHECKED' if row['source_id'] in TARGETS else 'INHERITED_NOT_REVIEWED_BY_THIS_CORRECTION'
    assert r['source_snapshot_id'] == by_id[row['source_id']]['source_snapshot_id'], (line, row['source_id'])
    dated_projection.append(r)
    assert all(r[k] == v for k, v in row.items())

# Downstream source-specific cards retain their own grain; no aggregation or uplift.
bindings = []
for row in cards:
    ids = row['source_ids'].split(';')
    if not TARGETS.intersection(ids):
        continue
    assert len(ids) == 1, row['card_id']
    sid = ids[0]
    assert row['raw_sha256'] == receipts[sid]['sha256'], row['card_id']
    bindings.append(dict(card_id=row['card_id'], source_id=sid,
                         source_snapshot_id=snapshot_id(sid, row['raw_sha256']), raw_sha256=row['raw_sha256'],
                         original_commit=PRIMARY, original_path=PREFIX + 'route_product_cards.csv',
                         clock_consensus_status=row['clock_consensus_status'],
                         lineage_status='CORRECTED_RECEIPT_JOIN_PARENT_CHECKED',
                         other_acceptance='INHERITED_SCOPE_ONLY; NO_CLOCK_OR_SUPPLY_UPGRADE'))

bridge_path = 'context/23_night_run_20261110/data_bridge/candidate_addendum_primary17b/candidate_endpoint_mapping.csv'
bridge_rows = table(blob(BRIDGE, bridge_path))
binding_by_card = {r['card_id']: r for r in bindings}
bridge_projection = []
affected_mappings = []
for line, row in enumerate(bridge_rows, 2):
    r = dict(row)
    r['original_mapping_csv_line'] = str(line)
    r['source_snapshot_id'] = ''
    r['lineage_projection_status'] = 'INHERITED_NOT_REVIEWED_BY_THIS_CORRECTION'
    if row['card_id'] in binding_by_card:
        binding = binding_by_card[row['card_id']]
        assert row['raw_sha256'] == binding['raw_sha256']
        r['source_snapshot_id'] = binding['source_snapshot_id']
        r['lineage_projection_status'] = 'CORRECTED_RECEIPT_JOIN_PARENT_CHECKED; OTHER_HOLDS_RETAINED'
        affected_mappings.append(r)
    assert all(r[k] == v for k, v in row.items())
    bridge_projection.append(r)
assert len(bridge_projection) == 386
assert len(affected_mappings) == 58
assert collections.Counter(r['status'] for r in affected_mappings) == {
    'CONTEXT_CANDIDATE_ONLY': 42, 'HOLD_EXACT_CLOCK; SUPPLY_CONTEXT_ONLY': 6, 'NO_BASELINE_ENDPOINT_MATCH': 10}

save_csv('source_registry.csv', corrected)
save_csv('dated_evidence.csv', dated_projection)
save_csv('historical_snapshot_registry.csv', legacy)
save_csv('registry_changes.csv', changes)
save_csv('card_snapshot_bindings.csv', bindings)
save_csv('candidate_endpoint_mapping.csv', bridge_projection)
save_json('inherited_service_receipts.json', dict(source_commit=TSIRI, receipt_path=RECEIPTS,
          source_author='Цири / mput', receipts=[receipts[s] for s in sorted(TARGETS)],
          receipt_scope='Pinned manifest claims; no fresh acquisition or raw-body parse'))
save_json('source_lock.json', dict(original_package_source_locks=old_locks, correction_inputs=LOCK))
save_json('unchanged_original_outputs.json', dict(original_commit=PRIMARY, files=frozen_manifest['files'],
          policy='All originals remain in their exact commit; no mutation, deletion or silent replacement. Use these projections only for the stated lineage correction.'))
validation = dict(status='PASS_PARENT_METADATA_AND_JOIN_CHECKS',
                  original_dated_rows=len(dated), affected_svx_rows=len(affected),
                  affected_source_counts=dict(collections.Counter(r['source_id'] for r in affected)),
                  unchanged_dated_original_cells=True, changed_numeric_or_clock_cells=0,
                  complete_snapshot_fk_match_rows=len(dated_projection), affected_card_bindings=len(bindings),
                  unchanged_bridge_original_cells=True, bridge_rows=len(bridge_projection),
                  affected_bridge_mappings=len(affected_mappings),
                  preserved_mapping_statuses=dict(collections.Counter(r['status'] for r in affected_mappings)),
                  legacy_snapshot_rejected_rows=len(affected),
                  context17_receipt_hashes_match_all_affected_rows=True,
                  missing_new_receipt_byte_lengths='NULL; old snapshot sizes not reused',
                  independent_review='NOT_RUN_ON_THIS_CORRECTION', raw_reparse='NOT_RUN',
                  original_primary17b_lineage_hold='RETAINED; replacement projection is separate',
                  clock_conflicts='RETAINED; NOT_RESOLVED_HERE', market_launch='NOT_ACCEPTED')
save_json('validation.json', validation)
files = []
for p in sorted(ROOT.iterdir()):
    if p.is_file() and p.name not in {'output_manifest.json', 'handoff.json'}:
        data = p.read_bytes()
        files.append(dict(path=p.name, sha256=sha(data), bytes=len(data)))
save_json('output_manifest.json', dict(package_id='primary17b-svx-lineage-correction-v1',
          inputs=LOCK, files=files, acceptance='PARENT_METADATA_JOIN_ONLY'))
save_json('handoff.json', dict(package_id='primary17b-svx-lineage-correction-v1',
          original_primary_commit=PRIMARY, correction_receipt_commit=TSIRI, receipt_path=RECEIPTS,
          status='READY_SCOPED_PARENT_CHECKED; INDEPENDENT_CORRECTION_REVIEW_NOT_RUN',
          manifest_sha256=sha((ROOT / 'output_manifest.json').read_bytes()),
          consume=['source_registry.csv', 'dated_evidence.csv', 'inherited_service_receipts.json', 'card_snapshot_bindings.csv', 'candidate_endpoint_mapping.csv'],
          purpose='Correct SVX snapshot provenance only; no new source content or economics',
          inherited_holds=['12 KUF/SVX clock conflicts', 'planned not performed', 'unknown sales/seats/OD', 'original package review verdict unchanged']))
print(json.dumps(validation, ensure_ascii=False))
