#!/usr/bin/env python3
"""Candidate evidence mapping; baseline7180bf5 bytes and inputs remain frozen."""
import csv
import hashlib
import io
import json
import re
import subprocess
from collections import Counter,defaultdict
from pathlib import Path

OUT=Path(__file__).resolve().parent
BRIDGE=OUT.parent
ROOT=BRIDGE.parents[2]
SOURCE='17b4f348f15ea8695688d9435933cb4965568408'
BASELINE='7180bf5e03905a7892b3031f2447c5b33d10e244'
SP='context/23_night_run_20261110/primary_evidence/'
BP='context/23_night_run_20261110/data_bridge/'
input_rows=[]


def sha(b):return hashlib.sha256(b).hexdigest()


def blob(commit,path):return subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT)


def read(commit,path,fmt='csv'):
    b=blob(commit,path)
    input_rows.append(dict(source_commit=commit,path=path,sha256=sha(b),bytes=len(b)))
    return json.loads(b) if fmt=='json' else list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))


def write(name,rows,columns=None):
    with (OUT/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=columns or list(dict.fromkeys(k for r in rows for k in r)),lineterminator='\n')
        w.writeheader();w.writerows(rows)


def dump(name,value):(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def main():
    manifest=read(SOURCE,SP+'manifest.json','json')
    upstream_handoff=read(SOURCE,SP+'handoff.json','json')
    upstream_hashes=[]
    for r in manifest['files']:
        b=blob(SOURCE,SP+r['path'])
        upstream_hashes.append(dict(path=r['path'],expected_sha256=r['sha256'],actual_sha256=sha(b),
                                    status='PASS' if sha(b)==r['sha256'] else 'FAIL'))
    write('upstream_output_hash_checks.csv',upstream_hashes)
    cards=read(SOURCE,SP+'route_product_cards.csv')
    adapters=read(SOURCE,SP+'adapter_mapping.csv')
    conflicts=read(SOURCE,SP+'schedule_conflicts.csv')
    gaps=read(SOURCE,SP+'gap_resolution.csv')
    facts=read(SOURCE,SP+'primary_facts.csv')
    coverage=read(SOURCE,SP+'coverage.csv')
    parameter=read(BASELINE,BP+'normalized/parameter_registry.csv')
    entity=read(BASELINE,BP+'normalized/entity_resolution.csv')
    it=read(BASELINE,BP+'normalized/itinerary.csv')
    physical=read(BASELINE,BP+'normalized/physical_leg.csv')
    catalog={r['entity_code']:r for r in entity}
    source_adapter={(r['card_id'],r['candidate_id']):r for r in adapters}
    mappings=[];card_candidates=[]
    for n,c in enumerate(cards,2):
        unknown=c['value_status']=='UNKNOWN' or not c['one_way_departures']
        clock=c['clock_consensus_status']=='CONFLICT_HOLD'
        assigned='YEAR_ASSIGNED' in c['value_status']
        oa,da=catalog.get(c['origin']),catalog.get(c['destination'])
        admitted=bool(oa and da and oa['key_status']=='MATCHED_UNIQUE_DIRECTORY' and da['key_status']=='MATCHED_UNIQUE_DIRECTORY')
        targets=defaultdict(list)
        for r in physical:
            if r['origin']==c['origin'] and r['destination']==c['destination'] and r['period_start']==c['period_start'] and r['period_end']==c['period_end']:
                targets[(r['model_id'],r['candidate_id'],'PHYSICAL_LEG_ENDPOINT_CONTEXT')].append(r['physical_leg_id'])
        for r in it:
            if r['origin']==c['origin'] and r['destination']==c['destination'] and r['period_start']==c['period_start'] and r['period_end']==c['period_end']:
                targets[(r['model_id'],r['candidate_id'],'FINAL_OD_SUBSTITUTE_CONTEXT')].append(r['itinerary_id'])
        if not targets:targets[('','','NO_BASELINE_ENDPOINT_MATCH')]=[]
        for (model,cid,kind),rowids in sorted(targets.items()):
            status='CONTEXT_CANDIDATE_ONLY'
            if unknown:status='UNKNOWN_NO_POSITIVE_SOURCE_CARD'
            elif not admitted:status='HOLD_AIRPORT_IDENTITY'
            elif clock:status='HOLD_EXACT_CLOCK; SUPPLY_CONTEXT_ONLY'
            elif assigned:status='HOLD_YEAR_ASSIGNMENT; CONDITIONAL_SUPPLY_CONTEXT_ONLY'
            if not model:status='NO_BASELINE_ENDPOINT_MATCH'
            mappings.append(dict(evidence_commit=SOURCE,evidence_author_ref='Mput13 / primary Sol; publishers per source card',
                                 card_id=c['card_id'],source_card_row=n,source_program_ids=c['candidate_ids'],
                                 source_program_namespace='tsiri_proposal_evidence_adapter; context/21_team_proposals/routes.csv',
                                 source_input_set_id=c['input_set_id'],source_ids=c['source_ids'],raw_sha256=c['raw_sha256'],
                                 baseline_commit=BASELINE,baseline_model_id=model,baseline_candidate_id=cid,
                                 mapping_kind=kind,mapping_basis='EXACT_ORDERED_ENDPOINT_CODES_AND_IDENTICAL_7DAY_PERIOD; NOT_FLIGHT_IDENTITY',
                                 origin=c['origin'],destination=c['destination'],period_start=c['period_start'],period_end=c['period_end'],
                                 baseline_row_ids=';'.join(sorted(set(rowids))),baseline_matched_row_count=len(set(rowids)),
                                 card_published_departures=c['one_way_departures'],count_unit='SOURCE_CARD_PUBLICATION_COUNT; NON_ADDITIVE',
                                 clock_status=c['clock_consensus_status'],year_assignment='INFERRED_YEAR' if assigned else ('UNKNOWN' if unknown else 'SOURCE_EXPLICIT_OR_REUSED'),
                                 airport_identity_status='MATCHED' if admitted else 'HOLD_OR_UNMATCHED',
                                 variant_identity='H_UFA4_PROPOSAL_DIFFERS_FROM_OLD_RELAXED; NO_ID_EQUIVALENCE' if 'H_UFA_4' in c['candidate_ids'].split(';') else 'PROGRAM_IDENTITIES_NOT_ASSERTED',
                                 status=status,numerical_uplift='NONE',model_input_changed=False,
                                 acceptance_scope='CANDIDATE_ENDPOINT_CONTEXT_MAPPING_ONLY; PRIMARY_INDEPENDENT_REVIEW_PENDING',
                                 seats='',observed_final_OD='',net_fare='',missing_reason='No comparable seats/actual endpoint OD/net fare; no dispatch or ticket acceptance'))
        for cid in c['candidate_ids'].split(';'):
            a=source_adapter.get((c['card_id'],cid))
            card_candidates.append(dict(card_id=c['card_id'],source_program_id=cid,adapter_mapping_found=bool(a),
                                         source_program_commit=a['source_commit'] if a else '',source_program_path=a['program_path'] if a else '',
                                         source_card_status=c['value_status'],source_clock_status=c['clock_consensus_status'],
                                         evidence_commit=SOURCE,source_acceptance='REPORTED_BY_PRIMARY_PACKAGE; INDEPENDENT_REVIEW_PENDING'))
    write('candidate_endpoint_mapping.csv',mappings)
    write('source_candidate_card_links.csv',card_candidates)
    write('clock_holds.csv',[dict(evidence_commit=SOURCE,**r,bridge_admission='HOLD_EXACT_TIME; NOT_PHYSICAL_FLIGHT_DUPLICATES') for r in conflicts])
    write('fact_admission.csv',[dict(evidence_commit=SOURCE,**r,
         bridge_scope='PUBLISHED_EVENT_OR_REPORTED_AGGREGATE_CONTEXT_ONLY',
         source_acceptance_scope=r['acceptance_scope'],bridge_acceptance='CANDIDATE_CONTEXT; PRIMARY_INDEPENDENT_REVIEW_PENDING',
         model_input_changed=False,numerical_uplift='NONE') for r in facts])
    fact_mappings=[]
    for n,f in enumerate(facts,2):
        feature='ssj_mro' if f['entity']=='KUF' else ('pax_2025' if f['entity']=='REN' else '')
        matches=[r for r in parameter if r['model_id']=='nastya:screening' and r['candidate_id']==f['entity'] and r['parameter_id']==feature] if feature else []
        if not matches:matches=[None]
        for p in matches:
            fact_mappings.append(dict(evidence_commit=SOURCE,source_fact_row=n,source_id=f['source_id'],source_entity=f['entity'],
                                      source_metric=f['metric'],source_value=f['value'],source_unit=f['unit'],source_qualifier=f['qualifier'],
                                      source_period_start=f['period_start'],source_period_end=f['period_end'],
                                      baseline_commit=BASELINE,baseline_model_id=p['model_id'] if p else '',
                                      baseline_candidate_id=p['candidate_id'] if p else '',baseline_parameter_id=feature,
                                      baseline_value=p['value'] if p else '',baseline_value_class=p['value_status'] if p else '',
                                      mapping_status='KUF_2025_OPENING_EVENT_CONTEXT_ONLY; CURRENT_PARAM_UPGRADE_HOLD' if f['entity']=='KUF' else
                                      ('REN_STRICT_LOWER_BOUND_CONTEXT; NO_EXACT_VALUE_REPLACEMENT' if f['entity']=='REN' else
                                       'SVX_CARRIER_AGGREGATE_DISTINCT_ENTITY_GRAIN; NO_AIRPORT_OR_ENDPOINT_OD_SUBSTITUTION'),
                                      numerical_uplift='NONE',model_input_changed=False,independent_review='PENDING'))
    write('fact_to_baseline_mapping.csv',fact_mappings)
    write('gap_admission.csv',[dict(evidence_commit=SOURCE,**r,bridge_effect='Candidate evidence delta; baseline unchanged') for r in gaps])
    write('source_market_coverage.csv',[dict(evidence_commit=SOURCE,**r) for r in coverage])
    baseline_changes=[]
    tree=subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE,BP],cwd=ROOT,text=True).splitlines()
    for p in tree:
        actual=ROOT/p
        if not actual.is_file() or sha(actual.read_bytes())!=sha(blob(BASELINE,p)):baseline_changes.append(p)
    sanitation=[]
    for p in sorted(OUT.iterdir()):
        if not p.is_file() or p.name in ['outputs_manifest.json','verification.json','handoff.json','input_manifest.json']:continue
        txt=p.read_text()
        if p.suffix=='.csv':
            rr=list(csv.reader(io.StringIO(txt)))
            if not rr or len(set(rr[0]))!=len(rr[0]) or any(len(r)!=len(rr[0]) for r in rr[1:]):sanitation.append(p.name+':CSV_SHAPE')
        if re.search(r'\bgh[pousr]_[A-Za-z0-9]{25,}\b|\bsk-(?:proj-)?[A-Za-z0-9_-]{30,}\b|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',txt):
            sanitation.append(p.name+':POTENTIAL_SECRET')
        if p.suffix in ['.zip','.gz','.db','.sqlite','.pdf','.xlsx']:sanitation.append(p.name+':RAW_RUNTIME_FILE')
    checks=[dict(check='UPSTREAM_OUTPUT_GIT_HASHES',status='PASS' if all(r['status']=='PASS' for r in upstream_hashes) else 'FAIL',files=len(upstream_hashes)),
            dict(check='SOURCE_CARD_UNIQUE',status='PASS' if len({r['card_id'] for r in cards})==len(cards)==112 else 'FAIL',rows=len(cards)),
            dict(check='CARD_TO_SOURCE_ADAPTER_FK',status='PASS' if all(r['adapter_mapping_found'] for r in card_candidates) else 'FAIL',links=len(card_candidates)),
            dict(check='CLOCK_CONFLICTS_RETAINED',status='PASS' if len(conflicts)==12 else 'FAIL',held_source_service_keys=len(conflicts)),
            dict(check='BASELINE_BYTES_UNCHANGED',status='PASS' if not baseline_changes else 'FAIL',files=len(tree),changed=baseline_changes),
            dict(check='NO_ECONOMIC_INPUT_UPLIFT',status='PASS' if all(not r['model_input_changed'] and r['numerical_uplift']=='NONE' for r in mappings) else 'FAIL'),
            dict(check='NO_PHYSICAL_FLIGHT_CREATION',status='PASS' if not (OUT/'physical_leg.csv').exists() else 'FAIL',scope='Only endpoint context links; source publications neither summed nor allocated as physical legs'),
            dict(check='ADDENDUM_SANITIZER_AND_CSV_SHAPE',status='PASS' if not sanitation else 'FAIL',errors=sanitation)]
    fail=sum(r['status']=='FAIL' for r in checks)
    dump('verification.json',dict(checks=checks,failed=fail,independent_review=False,raw_rechecked_here=False,
                                parent_validation='User reports36output/12Git/28raw hashes and bounded literals/date counts; this addendum personally repeats only output Git hashes and endpoint mapping checks'))
    dump('input_manifest.json',dict(source_commit=SOURCE,baseline_commit=BASELINE,inputs=input_rows,
                                    source_package_independent_review='PENDING',source_cards_grain='Source-specific published product cards, not physical flights',
                                    source_publication_rows=209,source_service_keys=173,no_automatic_uplift=True))
    dump('handoff.json',dict(ready_for_review=fail==0,package_id='DATA_BRIDGE_CANDIDATE_PRIMARY17B',baseline_commit=BASELINE,
                             source_commit=SOURCE,baseline_input_set_replaced=False,baseline_bytes_changed=baseline_changes,
                             mappings=len(mappings),cards=len(cards),source_candidate_links=len(card_candidates),
                             source_card_status_counts=dict(Counter(r['value_status'] for r in cards)),
                             source_service_rows=209,source_service_keys=173,source_rows_are_physical_flights=False,
                             acceptance='CANDIDATE_CONTEXT_MAPPING_ONLY; NO_ECONOMICS_OR_PREDICTIVE_UPLIFT',
                             primary_independent_review='PENDING',checks_passed=len(checks)-fail,checks_failed=fail,
                             holds=['12conflicting service clocks; exact connection time HOLD','KUF/GSV year assignment remains inferred',
                                    'H_UFA4 proposal composition differs from old RELAXED; no identifier-based variant merge',
                                    'Unknown/duplicate publication cards not additive','KUF MRO event2025 not current RW access/capacity',
                                    'SVX reported outcomes2025 not target-week OD/transfer share/P&L'],
                             reproduce='PYTHONDONTWRITEBYTECODE=1 python3 '+str(OUT.relative_to(ROOT)/'build_addendum.py')))
    outputs=[]
    for p in sorted(OUT.iterdir()):
        if p.is_file() and p.name!='outputs_manifest.json':
            b=p.read_bytes();outputs.append(dict(path=p.name,sha256=sha(b),bytes=len(b),grain='Named source card/context mapping or scoped receipt; see CSV keys and verification'))
    dump('outputs_manifest.json',dict(files=outputs,self_excluded=True,baseline_manifest_unchanged=True))
    print(json.dumps(dict(ready_for_review=fail==0,checks=len(checks),failed=fail,mappings=len(mappings),cards=len(cards)),ensure_ascii=False))
    if fail:raise SystemExit(1)


if __name__=='__main__':main()
