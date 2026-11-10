#!/usr/bin/env python3
"""Bounded MR14: exact Git inputs, standard library, writes only beside this file."""
import ast
import collections
import copy
import csv
import difflib
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import types
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[2]
PREFIX = 'context/23_night_run_20261110/methods/'
SUBJECT = '7e65c687e12cf45534852a3c47d6a5c8cf7dda07'
PRIOR = 'c6adf25cc39712cbfdd2d34acdabd31366b33bce'
FROZEN = 'f7a034dc91917cc69c5f8b3a729c3d1c6dfeb5b9'
MR11 = 'ea2a9626aef75c121f2da7d778b47edce0d571b7'
MR12 = '5e9b4765c60f4cc7ecb1d1a4dad20d3996235cab'
PASSPORT = '46fd52db073cffc46a598f44489d0761c6853410'
RUNTIME = OUT / '.runtime'
ROOT = RUNTIME / PREFIX
SOURCES = {}
CHECKS = collections.Counter()


def grain(path):
    if path.endswith('flights.csv'):
        return 'source profile/network/physical flight id; dated directed leg and absolute UTC minutes from period epoch'
    if path.endswith('capacity.csv'):
        return 'source profile/network/scenario/flight id; directed endpoints, scenario seats and per-flight variable RUB'
    if 'independent_affected_itinerary.csv' in path:
        return 'MR11 candidate/scenario/recipe/ordered flight_ids; affected legs, endpoint journeys and one through fare'
    if 'itinerary_at_unit_scale.csv' in path:
        return 'full experiment/source/profile/network/input set/period/scenario/recipe/OD/ordered flight_ids at multiplier 1'
    if path.endswith('requirements_evidence.csv') or path.endswith('requirement_addendum.csv'):
        return 'passport exact commit/namespaced requirement id; original strings and separate methods addendum'
    if path.endswith('claims.csv') or path.endswith('claim_qualifications.csv'):
        return 'passport exact commit/namespaced claim id; original wording/scope and separate proposal'
    if path.endswith('acceptance_matrix.csv'):
        return 'artifact/exact input commit/review commit; historical bounded verdict and excluded scope'
    if path.endswith('summary.csv'):
        return 'original keyed network/scenario/recipe/multiplier or upstream run grain; scenario quantities and conditional money'
    if path.endswith('.csv'):
        return 'preserved original keyed upstream table; preservation only unless separately listed as independently checked'
    return 'exact code/document/contract/receipt; original historical scope retained'


def raw(path, sha=SUBJECT, full=False):
    p = path if full else PREFIX + path
    data = subprocess.check_output(['git', 'show', sha + ':' + p], cwd=REPO)
    SOURCES[sha + ':' + p] = dict(commit=sha, path=p, bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        grain=grain(p))
    return data


def rows(path, sha=SUBJECT, full=False):
    return list(csv.DictReader(io.StringIO(raw(path, sha, full).decode('utf-8-sig'))))


def obj(path, sha=SUBJECT):
    return json.loads(raw(path, sha))


def save(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def check(ok, label):
    if not ok:
        raise AssertionError(label)
    CHECKS[label] += 1


def near(a, b, label):
    check(math.isfinite(float(a)) and math.isfinite(float(b)) and abs(D(str(a))-D(str(b))) <= D('0.00001'), label)


def materialize(path):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(raw(path))


def load_code(name):
    module = types.ModuleType(name)
    module.__file__ = str(ROOT / (name + '.py'))
    exec(compile(raw(name + '.py'), module.__file__, 'exec'), module.__dict__)
    return module


def receipt_checks():
    result = []
    for folder in ['integration-oracle-001', 'integration-review-001', 'allocation-review-001', 'passport-001']:
        receipt = obj('inputs/' + folder + '/receipt.json')
        for f in receipt['files']:
            actual = raw(f['path'])
            upstream = raw(f['source_path'], f['source_commit'], full=True)
            check(actual == upstream, 'receipt_exact_upstream_bytes')
            check(hashlib.sha256(actual).hexdigest() == f['sha256'], 'receipt_sha256')
            check(len(actual) == f['bytes'], 'receipt_length')
            check(f['source_commit'] == receipt['source_commit'], 'receipt_commit_consistency')
            result.append(dict(input_set=folder, path=f['path'], source_commit=f['source_commit'],
                               source_path=f['source_path'], bytes=len(actual), sha256=f['sha256'], status='PASS'))
    save('receipt_checks.json', result)


def independent_inputs(g):
    sales, summary, flights, capacity = [rows(p) for p in [g.SALES, g.SUMMARY, g.FLIGHTS, g.CAPACITY]]
    for p in [g.SALES, g.SUMMARY, g.FLIGHTS, g.CAPACITY]:
        check(raw(p) == raw(p, FROZEN), 'four_exact_f7a_byte_pins')
    unit = [r for r in summary if D(r['multiplier']) == 1]
    ctx = ['experiment_id','source_commit','source_variant','source_profile','source_network','input_set_id',
           'period_start','period_end','price_basis','tax_basis']
    def group(r):
        return tuple(r[k] for k in ['network','scenario','recipe']) + (D(r['multiplier']),)
    def fullkey(r):
        return tuple(r[k] for k in ctx) + group(r) + (r['origin'],r['destination'],tuple(r['flight_ids'].split(';')))
    check(len(sales) == len({fullkey(r) for r in sales}) == 384, '384_unique_full_context_itinerary_keys')
    check(len(unit) == len({group(r) for r in unit}) == 12, '12_unique_unit_groups')
    grouped = collections.defaultdict(list)
    for s in sales:
        grouped[group(s)].append(s)
    check(set(grouped) == {group(r) for r in unit}, 'full_group_coverage')
    oracle = rows('inputs/integration-oracle-001/independent_affected_itinerary.csv')
    om = {(r['candidate'],r['scenario'],r['recipe'],r['flight_ids']):r for r in oracle}
    check(len(om) == len(oracle) == 160, '160_unique_upstream_oracle_rows')
    affected = {}
    details = []
    local_count = transfer_count = 0
    for u in unit:
        ss = grouped[group(u)]
        ff = [f for f in flights if (f['profile'],f['network']) == (u['source_profile'],u['source_network'])]
        cc = [c for c in capacity if (c['profile'],c['network'],c['scenario']) == (u['source_profile'],u['source_network'],u['scenario'])]
        fm = {f['id']:f for f in ff}; cm = {c['flight_id']:c for c in cc}
        check(len(fm)==len(ff) and len(cm)==len(cc), 'source_join_unique')
        used = {i for s in ss for i in s['flight_ids'].split(';')}
        check(used == set(fm) == set(cm), 'complete_physical_and_capacity_join')
        epoch = datetime.fromisoformat(u['period_start']+'T00:00:00+00:00')
        end = datetime.fromisoformat(u['period_end']+'T00:00:00+00:00')+timedelta(days=1)
        check((end-epoch).days==7, 'one_week_period')
        start_event = datetime(2026,12,7,tzinfo=timezone.utc)
        end_event = start_event+timedelta(days=1)
        touched = set()
        double_day_touched = set()
        for f in ff:
            c=cm[f['id']]
            check((c['origin'],c['destination'])==(f['origin'],f['destination']), 'capacity_endpoint_join')
            near(c['block_minutes'],f['block_minutes'],'capacity_block_join')
            dep=epoch+timedelta(minutes=float(f['departure_utc_minute']))
            arr=epoch+timedelta(minutes=float(f['arrival_utc_minute']))
            check(dep.date().isoformat()==f['date'], 'absolute_minutes_match_source_date')
            check((dep.date()-epoch.date()).days+1==int(f['day']), 'absolute_minutes_match_source_day')
            check(epoch<=dep<end and dep<arr, 'dated_leg_in_week')
            near((arr-dep).total_seconds()/60,f['block_minutes'],'absolute_block_duration')
            if (f['origin']=='UFA' and start_event<=dep<end_event) or (f['destination']=='UFA' and start_event<=arr<end_event):
                touched.add(f['id'])
            wrong_dep=dep+timedelta(days=int(f['day'])-1)
            wrong_arr=arr+timedelta(days=int(f['day'])-1)
            if (f['origin']=='UFA' and start_event<=wrong_dep<end_event) or (f['destination']=='UFA' and start_event<=wrong_arr<end_event):
                double_day_touched.add(f['id'])
        occupied=collections.Counter(); market=collections.defaultdict(list)
        for s in ss:
            check(all(s[k]==u[k] for k in ctx), 'full_context_matches_summary')
            ids=s['flight_ids'].split(';'); legs=[fm[i] for i in ids]; q=D(s['sold_journeys'])
            check(legs[0]['origin']==s['origin'] and legs[-1]['destination']==s['destination'], 'directed_endpoints')
            check(all(a['destination']==b['origin'] for a,b in zip(legs,legs[1:])), 'connected_itinerary')
            check((len(ids)==2)==(s['transfer']=='True'), 'local_transfer_incidence')
            check(q>=0 and q<=D(s['desired'])+D('0.0000001'), 'desired_bound')
            near(q*D(s['fare_once']),s['gross_revenue'],'one_through_fare')
            near(q*len(ids),s['segment_pax'],'one_seat_per_used_leg')
            near(q if len(ids)==2 else 0,s['transfer_journeys'],'transfer_quantity')
            near(D(s['migrated_RW_direct'])+D(s['migrated_RW_unverified_connecting']),s['migrated_RW_total'],'own_migration_parts')
            for i in ids:
                occupied[i]+=q
            market[s['origin'],s['destination']].append(s)
            local_count+=len(ids)==1; transfer_count+=len(ids)==2
            hit=touched.intersection(ids)
            if hit:
                k=(u['network'],u['scenario'],u['recipe'],s['flight_ids'])
                check(k not in affected,'independent_affected_unique')
                affected[k]=dict(journeys=q,fare_once=D(s['fare_once']),lost_fare_once=q*D(s['fare_once']),affected_leg_count=len(hit))
        for i,c in cm.items():
            check(occupied[i]<=D(c['capacity_scenario'])+D('0.0000001'), 'capacity_conservation')
        for mk, offers in market.items():
            demands={D(s['D']) for s in offers}
            check(len(demands)==1,'directed_D_consistency')
            check(sum(D(s['sold_journeys']) for s in offers)<=next(iter(demands))+D('0.0000001'),'directed_D_bound')
        for field in g.SUM_FIELDS:
            near(sum(D(s[field]) for s in ss),u[field],'independent_summary_'+field)
        near(sum(D(c['flight_variable_cost']) for c in cc),u['flight_variable_cost'],'one_flight_cost_total')
        later=next(f for f in ff if int(f['day'])>1)
        later_time=epoch+timedelta(minutes=float(later['departure_utc_minute']))
        details.append(dict(network=u['network'],scenario=u['scenario'],recipe=u['recipe'],itineraries=len(ss),
            flight_ids=len(fm),directed_markets=len(market),affected_flight_ids=sorted(touched),
            day1_double_day_counterexample_discriminating=touched!=double_day_touched,
            later_day_witness=dict(flight_id=later['id'],source_day=later['day'],source_date=later['date'],
                epoch_plus_absolute_minute=later_time.isoformat(),
                invalid_double_day_time=(later_time+timedelta(days=int(later['day'])-1)).isoformat()),
            timebase='period epoch + absolute UTC minute once; no extra day offset'))
    check(set(affected)==set(om),'independent_oracle_full_key_set')
    for k, values in affected.items():
        for field,value in values.items():
            near(value,om[k][field],'independent_oracle_'+field)
    save('independent_inputs.json',dict(status='PASS',subject=SUBJECT,frozen=FROZEN,unique_itineraries=384,
        summary_groups=12,local_rows=local_count,transfer_rows=transfer_count,affected_rows=len(affected),groups=details,
        day1_limitation='Day1 touched sets alone cannot detect the historical double-day defect. All selected dated legs independently match absolute source dates; the historical code is unchanged.',
        trust='MR11 oracle exact bytes/provenance personally checked; upstream economic derivation reviewed as evidence, not rerun as MR11. No observed OD or operating acceptance.'))
    return sales,summary,flights,capacity,oracle


def execute_new_scripts():
    outputs=[
        'runs/input_admission_v1/input_receipt.json','runs/input_admission_v1/mutation_checks.json','runs/input_admission_v1/checks.json',
        'runs/passport_methods_v1/requirement_addendum.csv','runs/passport_methods_v1/claim_qualifications.csv','runs/passport_methods_v1/status.json',
        'runs/admission_v4/acceptance_matrix.csv','runs/admission_v4/status.json']
    scripts=[load_code(n) for n in ['admit_frozen_interaction','qualify_passport_methods','update_acceptance_v8']]
    captured=[]
    for repeat in range(2):
        for module in scripts:
            module.main()
        current={p:(ROOT/p).read_bytes() for p in outputs}
        for p,b in current.items():
            check(b==raw(p),'eight_owner_outputs_exact_replay')
        captured.append(current)
    check(captured[0]==captured[1],'eight_outputs_repeat_deterministic')
    save('replay.json',dict(status='PASS',executed=[m.__name__+'.main()' for m in scripts],
        common_demand='Exact subject module loaded without main; original rows/save used',
        repeats=2,new_outputs=[dict(path=p,sha256=hashlib.sha256(b).hexdigest()) for p,b in captured[0].items()],
        mutation_owner_output=json.loads(captured[0]['runs/input_admission_v1/mutation_checks.json']),
        old_interaction_main_executed=False))
    return scripts[0]


def own_probes(g, inputs):
    sales,summary,flights,capacity,oracle=inputs
    reference={g.key(r) for r in sales}
    records=[]
    def probe(name,mutate,expected):
        data=copy.deepcopy(inputs)
        mutate(data)
        try:
            g.validate(data[0],reference,*data[1:])
        except Exception as e:
            reason=str(e)
            check(isinstance(e,ValueError) and reason==expected,'own_validator_expected_rejection')
            records.append(dict(probe=name,path='direct validate API; fixed reference keys',status='REJECTED',reason=reason))
        else:
            raise AssertionError('Own probe accepted: '+name)
    probe('duplicate_full_key',lambda x:x[0].append(copy.deepcopy(x[0][0])),'DUPLICATE_ITINERARY_KEY')
    probe('missing_full_key',lambda x:x[0].pop(0),'ITINERARY_KEY_SET_DRIFT')
    probe('wrong_period_context',lambda x:x[0][0].update(period_start='2026-12-08'),'CONTEXT_DRIFT')
    probe('reversed_OD',lambda x:x[0][0].update(origin=x[0][0]['destination'],destination=x[0][0]['origin']),'ITINERARY_KEY_SET_DRIFT')
    market_fields=['network','scenario','recipe','origin','destination']
    market_counts=collections.Counter(tuple(r[k] for k in market_fields) for r in sales)
    target=next(r for r in sales if market_counts[tuple(r[k] for k in market_fields)]>1)
    unit=next(r for r in summary if g.group(r)==g.group(target))
    fi=next(i for i,f in enumerate(flights) if f['id']==target['flight_ids'].split(';')[0])
    probe('physical_endpoint_conflict',lambda x:x[2][fi].update(origin='WRONG_AIRPORT'),'ENDPOINT_KEY')
    same_market=next(i for i,r in enumerate(sales) if r is not target and tuple(r[k] for k in market_fields)==tuple(target[k] for k in market_fields))
    probe('inconsistent_directed_D',lambda x:x[0][same_market].update(D=str(float(target['D'])+1)),'MARKET_D_CONFLICT')
    indices=[i for i,r in enumerate(sales) if (r['network'],r['scenario'],r['recipe'],r['origin'],r['destination'])==(target['network'],target['scenario'],target['recipe'],target['origin'],target['destination'])]
    def low_D(x):
        for i in indices:x[0][i]['D']='0'
    probe('consistent_but_insufficient_directed_D',low_D,'DIRECTED_MARKET_BOUND')
    ci=next(i for i,c in enumerate(capacity) if c['flight_id']==target['flight_ids'].split(';')[0] and c['scenario']==target['scenario'])
    probe('capacity_conflict',lambda x:x[3][ci].update(capacity_scenario='0'),'LEG_CAPACITY')
    probe('oracle_quantity_corrupt',lambda x:x[4][0].update(journeys=str(float(x[4][0]['journeys'])+1)),'INDEPENDENT_AFFECTED_ORACLE')
    probe('oracle_fare_corrupt',lambda x:x[4][0].update(fare_once=str(float(x[4][0]['fare_once'])+1)),'INDEPENDENT_AFFECTED_ORACLE')
    probe('oracle_affected_leg_count_corrupt',lambda x:x[4][0].update(affected_leg_count=str(int(x[4][0]['affected_leg_count'])+1)),'INDEPENDENT_AFFECTED_ORACLE')
    probe('oracle_missing_key',lambda x:x[4].pop(0),'INDEPENDENT_ORACLE_KEY')
    probe('oracle_duplicate_key',lambda x:x[4].__setitem__(1,copy.deepcopy(x[4][0])),'INDEPENDENT_ORACLE_KEY')
    # Direct API limitations are not changed-input admission bypasses: main pins all four tables.
    def direct_capacity_metadata(x):x[3][ci].update(origin='WRONG_AIRPORT')
    data=copy.deepcopy(inputs);direct_capacity_metadata(data)
    g.validate(data[0],reference,*data[1:])
    records.append(dict(probe='capacity_endpoint_metadata_only',path='direct validate API',status='ACCEPTED_API_LIMITATION',
        implication='Not a main admission bypass: capacity bytes differ and main rejects before validation.'))
    for pin in [g.SALES,g.SUMMARY,g.FLIGHTS,g.CAPACITY]:
        path=ROOT/pin; original=path.read_bytes();path.write_bytes(original+b'\n')
        try:
            g.main()
        except ValueError as e:
            check(str(e)=='IMMUTABLE_HASH_DRIFT_REQUIRES_NEW_INPUT_SET_AND_ORACLE','main_pin_rejects_each_changed_table')
            records.append(dict(probe='changed_pinned_bytes',input_path=pin,path='main',status='REJECTED',reason=str(e)))
        else:
            raise AssertionError('Changed pin accepted: '+pin)
        finally:path.write_bytes(original)
    receipt_path=ROOT/'inputs/integration-oracle-001/receipt.json'
    receipt_original=receipt_path.read_bytes()
    # Receipt corruption: fixed oracle quantities are left untouched.
    for name,mutate in [
        ('oracle_receipt_wrong_source_commit',lambda r:r.update(source_commit='0'*40)),
        ('oracle_receipt_empty_file_list',lambda r:r.update(files=[])),
        ('oracle_receipt_wrong_hash',lambda r:r['files'][0].update(sha256='0'*64))]:
        receipt=json.loads(receipt_original);mutate(receipt);receipt_path.write_text(json.dumps(receipt))
        try:
            g.main()
        except ValueError as e:
            records.append(dict(probe=name,path='main',status='REJECTED',reason=str(e)))
        else:
            records.append(dict(probe=name,path='main',status='ACCEPTED',
                reported_oracle_commit=json.loads((ROOT/'runs/input_admission_v1/checks.json').read_text())['independent_oracle_commit']))
        finally:receipt_path.write_bytes(receipt_original)
    # Replace oracle bytes by a new serialization and self-receipt; all numeric values stay fixed.
    oracle_path=ROOT/'inputs/integration-oracle-001/independent_affected_itinerary.csv'
    original=oracle_path.read_bytes()
    oracle_path.write_bytes(original+b'\n')
    receipt=json.loads(receipt_original);receipt['source_commit']='0'*40
    receipt['files'][0].update(sha256=hashlib.sha256(oracle_path.read_bytes()).hexdigest(),source_commit='0'*40,bytes=len(oracle_path.read_bytes()))
    receipt_path.write_text(json.dumps(receipt))
    try:
        g.main()
        records.append(dict(probe='changed_oracle_bytes_plus_self_updated_receipt',path='main',status='ACCEPTED',
            oracle_bytes_equal_exact_MR11=False,reported_oracle_commit=json.loads((ROOT/'runs/input_admission_v1/checks.json').read_text())['independent_oracle_commit']))
    finally:
        oracle_path.write_bytes(original);receipt_path.write_bytes(receipt_original)
    # A same-owner oracle reconstructed from the protected sales also passes if receipt coverage is removed.
    # This changes provenance, not protected sales or economic quantities.
    fields=list(oracle[0])+['review_test_provenance']
    buffer=io.StringIO();writer=csv.DictWriter(buffer,fields);writer.writeheader()
    for r in reversed(oracle):
        candidates=[s for s in sales if (s['network'],s['scenario'],s['recipe'],s['flight_ids'])==(r['candidate'],r['scenario'],r['recipe'],r['flight_ids'])]
        check(len(candidates)==1,'self_oracle_source_key_unique')
        s=candidates[0]
        writer.writerow(dict(candidate=s['network'],scenario=s['scenario'],recipe=s['recipe'],flight_ids=s['flight_ids'],
            affected_leg_count=r['affected_leg_count'],journeys=s['sold_journeys'],fare_once=s['fare_once'],
            lost_fare_once=str(float(s['sold_journeys'])*float(s['fare_once'])),review_test_provenance='OWNER_SALES_RECONSTRUCTION'))
    oracle_path.write_text(buffer.getvalue(),newline='')
    receipt=json.loads(receipt_original);receipt.update(source_commit='0'*40,files=[])
    receipt_path.write_text(json.dumps(receipt))
    try:
        g.main()
        records.append(dict(probe='same_owner_reconstructed_oracle_plus_empty_receipt',path='main',status='ACCEPTED',
            oracle_bytes_equal_exact_MR11=False,protected_four_inputs_unchanged=True,
            replaced_oracle_sha256=hashlib.sha256(oracle_path.read_bytes()).hexdigest(),
            reported_oracle_commit=json.loads((ROOT/'runs/input_admission_v1/checks.json').read_text())['independent_oracle_commit']))
    finally:
        oracle_path.write_bytes(original);receipt_path.write_bytes(receipt_original)
    g.main()
    save('own_probes.json',records)


def qualifications():
    requirements=rows('inputs/passport-001/requirements_evidence.csv')
    claims=rows('inputs/passport-001/claims.csv')
    rq=rows('runs/passport_methods_v1/requirement_addendum.csv')
    cq=rows('runs/passport_methods_v1/claim_qualifications.csv')
    check(len(requirements)==len(rq)==26 and len(claims)==len(cq)==33,'passport_26_33_counts')
    rmap={r['requirement_id']:r for r in requirements};cmap={r['claim_id']:r for r in claims}
    check({r['passport_requirement_id'] for r in rq}==set(rmap),'passport_requirement_ids')
    check({r['passport_claim_id'] for r in cq}==set(cmap),'passport_namespaced_claim_ids')
    for q in rq:
        original=rmap[q['passport_requirement_id']]
        for out,src in [('original_kind','requirement_kind'),('original_requirement','requirement_paraphrase'),('original_available_result','available_result'),('original_gap','gap')]:
            check(q[out]==original[src],'original_requirement_strings_preserved')
        check(q['passport_commit']==PASSPORT and q['requirement_fully_satisfied_by_this_addendum']=='False' and q['passport_independent_review']=='PENDING','requirement_no_acceptance_promotion')
    for q in cq:
        original=cmap[q['passport_claim_id']]
        for out,src in [('original_group','group'),('original_wording','ready_russian_wording'),('original_acceptance_scope','acceptance_scope')]:
            check(q[out]==original[src],'original_claim_strings_preserved')
        check(q['passport_commit']==PASSPORT and q['original_overwritten']=='False' and q['passport_independent_review']=='PENDING','claim_no_acceptance_promotion')
    addenda=[r['passport_requirement_id'] for r in rq if not r['methods_addendum'].startswith('No additional')]
    check(len(addenda)==16,'16_method_addenda')
    qmap={r['passport_claim_id']:r for r in cq}
    s03=qmap['S03']
    check('−449 822,70' in s03['current_wording_proposal'] and '2,4617708804/2,9194370052' in s03['current_wording_proposal'],'S03_original_numbers_retained')
    check('not a shortage of demand' in s03['current_scope'] and 'not the new LP allocator' in s03['current_scope'],'S03_saturation_and_local_first_scope')
    check('NEW_CURRENT_QUALIFICATION_EVENT_NOT_REWRITE'==qmap['C12']['qualification_kind'],'C12_separate_current_event')
    matrix=rows('runs/admission_v4/acceptance_matrix.csv'); prior=rows('runs/admission_v3/acceptance_matrix.csv')
    current={r['artifact']:r for r in matrix}; old={r['artifact']:r for r in prior}
    changed={'methods-integration-v5','methods-allocation-and-final-variants-v6','methods-finite-budget-choice-and-model-projection-v7'}
    for name,r in old.items():
        if name not in changed:check(current[name]==r,'admission_old_rows_preserved')
    check(current['methods-integration-v5']['input_commit']==FROZEN and current['methods-integration-v5']['review_commit']==MR11,'MR11_exact_review_subject')
    check(current['methods-allocation-and-final-variants-v6']['input_commit']=='ba9f6b85b4f8c9847948ae428ef3fbcfca9e2009' and current['methods-allocation-and-final-variants-v6']['review_commit']==MR12,'MR12_exact_review_subject')
    check(current['methods-finite-budget-choice-and-model-projection-v7']['input_commit']==PRIOR and current['methods-finite-budget-choice-and-model-projection-v7']['verdict']=='MR13_RUNNING_EXACT_c6ad','MR13_not_inherited')
    check(current['passport_bridge']['input_commit']==PASSPORT and current['passport_bridge']['verdict']=='OWNER_SYNTHESIS_INDEPENDENT_PENDING','passport_pending_not_inherited')
    check(current['methods-input-admission-and-passport-v8']['verdict']=='OWNER_CHECKS_ONLY_INDEPENDENT_PENDING','v8_not_inherited')
    status=obj('runs/admission_v4/status.json')
    check(status['original_primary']=='CHANGES' and status['original_cost']=='CHANGES' and status['delay_holds']==4 and status['clock_holds']==12,'historical_CHANGES_4delay_12clock')
    check(current['primary_evidence+data_bridge']['verdict']=='CHANGES' and current['cost_kover']['verdict'].startswith('CHANGES'),'historical_matrix_CHANGES')
    check('12clockholds' in current['primary_lineage_correction']['does_not_approve'] and '4delayHOLD' in current['cost_kover_timebase_correction']['scope'],'historical_matrix_hold_scopes')
    save('qualification_checks.json',dict(status='PASS',requirements=26,claims=33,method_addenda=addenda,
        original_strings_preserved=True,source_passport=PASSPORT,MR11_subject=FROZEN,MR12_subject=current['methods-allocation-and-final-variants-v6']['input_commit'],
        original_pending_preserved=True,namespaces='passport_claim_id has no frontier hypothesis join',
        S03_scope=s03['current_scope'],city_airport_operating_scope=[r['methods_addendum'] for r in rq if r['passport_requirement_id'] in ['R11','R12']],
        inherited_still_held=dict(primary='CHANGES',cost='CHANGES',clock=12,delay=4),
        outside_scope=['main passport review','MR11/MR12 calculations','MR13 v7 choice domains','external city-link requirement verification']))


def candidate_fix(g):
    original=raw('admit_frozen_interaction.py').decode()
    receipt_path=ROOT/'inputs/integration-oracle-001/receipt.json'
    oracle_path=ROOT/'inputs/integration-oracle-001/independent_affected_itinerary.csv'
    receipt_bytes=receipt_path.read_bytes();oracle_bytes=oracle_path.read_bytes()
    expected=hashlib.sha256(receipt_bytes).hexdigest()
    old="    receipt=json.loads((m.ROOT/'inputs/integration-oracle-001/receipt.json').read_text())"
    new="    receipt_bytes=(m.ROOT/'inputs/integration-oracle-001/receipt.json').read_bytes()\n"+\
        "    require(hashlib.sha256(receipt_bytes).hexdigest()=='"+expected+"','ORACLE_RECEIPT_DRIFT_REQUIRES_NEW_REVIEW')\n"+\
        "    receipt=json.loads(receipt_bytes)"
    check(original.count(old)==1,'candidate_patch_exact_anchor')
    proposed=original.replace(old,new)
    patch=''.join(difflib.unified_diff(original.splitlines(True),proposed.splitlines(True),
        fromfile='a/'+PREFIX+'admit_frozen_interaction.py',tofile='b/'+PREFIX+'admit_frozen_interaction.py'))
    (OUT/'suggested_fix.patch').write_text(patch)
    fixed=types.ModuleType('candidate_fix_only');fixed.__file__=g.__file__
    exec(compile(proposed,g.__file__,'exec'),fixed.__dict__)
    fixed.main()
    for p in ['runs/input_admission_v1/checks.json','runs/input_admission_v1/mutation_checks.json','runs/input_admission_v1/input_receipt.json']:
        check((ROOT/p).read_bytes()==raw(p),'candidate_fix_preserves_baseline_outputs')
    tests=[]
    for name,mutate in [
        ('wrong_source_commit',lambda r:r.update(source_commit='0'*40)),
        ('empty_coverage',lambda r:r.update(files=[])),
        ('forged_file_hash',lambda r:r['files'][0].update(sha256='0'*64)),
        ('changed_oracle_plus_updated_receipt',lambda r:r['files'][0].update(sha256=hashlib.sha256(oracle_bytes+b'\n').hexdigest(),bytes=len(oracle_bytes)+1))]:
        receipt=json.loads(receipt_bytes);mutate(receipt)
        receipt_path.write_text(json.dumps(receipt))
        if name=='changed_oracle_plus_updated_receipt':oracle_path.write_bytes(oracle_bytes+b'\n')
        try:
            fixed.main()
        except ValueError as e:
            check(str(e)=='ORACLE_RECEIPT_DRIFT_REQUIRES_NEW_REVIEW','candidate_fix_rejects_provenance_drift')
            tests.append(dict(probe=name,status='REJECTED',reason=str(e)))
        else:raise AssertionError('Candidate patch did not reject: '+name)
        finally:
            receipt_path.write_bytes(receipt_bytes);oracle_path.write_bytes(oracle_bytes)
    g.main()
    save('candidate_fix_check.json',dict(status='PASS_IN_REVIEW_MEMORY_ONLY',applied_to_owner=False,
        receipt_sha256=expected,exact_baseline_three_outputs_preserved=True,tests=tests,
        rationale='An immutable hash for this exact independently checked receipt anchors its required files, hashes, commit and coverage. Existing oracle file checks then reject altered bytes. No general validator added.'))


def preservation():
    listing=subprocess.check_output(['git','ls-tree','-r','--name-only',PRIOR,'--',PREFIX],cwd=REPO).decode().splitlines()
    scoped=[p for p in listing if p.startswith(PREFIX+('inputs/')) or p.startswith(PREFIX+'runs/') or p.startswith(PREFIX+'analysis/')]
    old=[]
    for path in scoped:
        before=raw(path,PRIOR,full=True);after=raw(path,SUBJECT,full=True)
        check(before==after,'prior_inputs_runs_analysis_bytes_preserved')
        old.append(dict(path=path,sha256=hashlib.sha256(after).hexdigest(),bytes=len(after)))
    check(len(old)==398,'398_prior_files')
    before=raw('decision_conditions.md',PRIOR).decode();after=raw('decision_conditions.md').decode()
    check(before.replace('1786,197','1786,193').replace('542,443','542,444')==after,'MR12_O01_exact_two_prose_substitutions')
    check(before.count('1786,197')==1 and before.count('542,443')==1,'MR12_O01_two_occurrences')
    for p in ['kover_demand_interaction.py','common_demand.py','portfolio_guard_comparison.py']:
        check(raw(p)==raw(p,PRIOR),'old_algorithm_bytes_unchanged_from_parent')
    check(raw('kover_demand_interaction.py')==raw('kover_demand_interaction.py',FROZEN),'old_interaction_unchanged_from_MR11')
    save('preservation.json',dict(status='PASS',base=PRIOR,subject=SUBJECT,count=len(old),files=old,
        prose_only={'1786,197':'1786,193','542,443':'542,444'},old_interaction_main_changed=False))


def narrow_manifest():
    manifest=obj('output_manifest.json')
    listed={r['path']:r for r in manifest['files']}
    narrow=[p for p in listed if p.startswith(('runs/input_admission_v1/','runs/passport_methods_v1/','runs/admission_v4/'))]
    narrow+=['admit_frozen_interaction.py','qualify_passport_methods.py','update_acceptance_v8.py',
             'inputs/integration-oracle-001/receipt.json','inputs/passport-001/receipt.json']
    for p in narrow:
        b=raw(p)
        check(hashlib.sha256(b).hexdigest()==listed[p]['sha256'] and len(b)==listed[p]['bytes'],'owner_manifest_narrow_sha_and_size')
    save('owner_manifest_check.json',dict(status='PASS',scope='new scripts/eight outputs/oracle and passport receipts only',
        checked_paths=narrow,whole_package_reacceptance=False))


def main():
    OUT.mkdir(exist_ok=True)
    check(not RUNTIME.exists(),'fresh_own_runtime')
    try:
        for p in ['common_demand.py','admit_frozen_interaction.py','qualify_passport_methods.py','update_acceptance_v8.py']:
            materialize(p)
        common=load_code('common_demand');sys.modules['common_demand']=common
        guard=load_code('admit_frozen_interaction')
        for p in [guard.SALES,guard.SUMMARY,guard.FLIGHTS,guard.CAPACITY,
            'inputs/integration-oracle-001/receipt.json', 'inputs/integration-oracle-001/independent_affected_itinerary.csv',
            'inputs/integration-oracle-001/independent_cancellation16.csv','inputs/integration-oracle-001/adversarial_probes.json',
            'inputs/passport-001/requirements_evidence.csv','inputs/passport-001/claims.csv','runs/admission_v3/acceptance_matrix.csv']:
            materialize(p)
        receipt_checks()
        inputs=independent_inputs(guard)
        guard=execute_new_scripts()
        own_probes(guard,inputs)
        candidate_fix(guard)
        qualifications()
        preservation()
        narrow_manifest()
        # Read exact upstream derivation and narrow owner receipts as audit inputs, without running MR11 again.
        raw('context/23_night_run_20261110/methods_integration_review/oracle.py',MR11,full=True)
        raw('context/23_night_run_20261110/methods_integration_review/findings.json',MR11,full=True)
        raw('context/23_night_run_20261110/allocation_variants_review/findings.json',MR12,full=True)
        for p in ['contract.md','briefs/input_admission_review.md']:
            raw('context/23_night_run_20261110/'+p,'5c7f0ea561bdf387c7abe476ca68eaf78aa791bd',full=True)
        for p in ['checks/v8_replay.json','checks/mr12_o01_resolution.json','output_manifest.json',
                  'integration_status.md','reproduce.md','handoff.json','acceptance_events.json']:
            raw(p)
        save('check_counts.json',dict(status='PASS',checks=dict(CHECKS),total=sum(CHECKS.values()),
            meaning='Assertion count is execution evidence, not a score or expanded acceptance'))
        save('source_manifest.json',dict(subject=SUBJECT,inputs=list(SOURCES.values())))
    finally:
        if RUNTIME.exists():shutil.rmtree(RUNTIME)
    print(json.dumps(dict(status='COMPLETE',subject=SUBJECT,checks=sum(CHECKS.values()),sources=len(SOURCES)),ensure_ascii=False))


if __name__=='__main__':
    main()
