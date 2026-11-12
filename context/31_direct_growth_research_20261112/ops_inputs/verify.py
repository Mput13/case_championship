from pathlib import Path
import json,csv,hashlib,copy
from calendar_engine import generate
from p06_adapter import check,P06
ROOT=Path(__file__).resolve().parent
checks=[]
def ok(name,condition):
 if not condition:raise AssertionError(name)
 checks.append(name)
def load(n):return json.loads((ROOT/n).read_text())
def rows(n):return list(csv.DictReader((ROOT/n).open()))
r=load('example_request.json');x=generate(r)
ok('2RT_3triangle_2added_physical_legs',len(x['flights'])==7)
ok('no_double_BH',sum(z['block_hours'] for z in x['monthly'])==7)
ok('single_rotation_elapsed_turns',[(z['physical_legs'],z['elapsed_minutes']) for z in x['rotations']]==[(2,165),(3,270),(2,165)])
ok('crew_and_MRO_unknown',x['crew']==x['maintenance']=='UNKNOWN')
ok('one_protected_reserve',x['reserve']==['DEMO-R'])
p06=check(r,x);ok('frozen_P06_independent_physical_checker',p06['status']=='CONDITIONAL' and not p06['errors'] and not p06['dispatch_ready'])
for name,change,needle in [
 ('reserve_used',lambda q:q['patterns'][0].update(workingtailids=['DEMO-R']),'RESERVE_OR_UNKNOWN'),
 ('no_working_tail',lambda q:q['patterns'][0].update(workingtailids=[]),'NO_WORKING_TAIL'),
 ('position_disconnected',lambda q:q['tails'][0].update(initial_location='GOJ'),'POSITION_MISMATCH'),
 ('pre_entry',lambda q:q['tails'][0].update(available_from='2028-01-01T00:00:00Z'),'OUTSIDE_ENTRY'),
 ('unclosed',lambda q:q['patterns'][0].update(path=['KUF','GOJ']),'UNCLOSED'),
 ('MOW_city',lambda q:q['patterns'][0].update(path=['KUF','MOW','KUF']),'UNRESOLVED_MOW'),
 ('missing_directed_block',lambda q:q.update(blocks=[]),'MISSING_DIRECTED_BLOCK'),
 ('SJ_before_H22027',lambda q:q['tails'][0].update(type='SJ100_PD8'),'SJ_BEFORE_H2'),
 ('maintenance_overlap',lambda q:q['tails'][0].update(maintenance_windows=[dict(start='2027-01-04T00:00:00Z',end='2027-01-05T00:00:00Z')]),'MAINTENANCE_CONFLICT'),
 ('reserve_absent',lambda q:q['tails'].pop(),'MISSING_PROTECTED_RESERVE'),
 ('duplicate_flight',lambda q:q['patterns'].append(copy.deepcopy(q['patterns'][0])),'DUPLICATE_PHYSICAL_FLIGHT')]:
 q=copy.deepcopy(r);change(q);v=generate(q);ok(name,v['status']=='INFEASIBLE' and any(needle in e for e in v['errors']))
q=copy.deepcopy(r);q['patterns']=q['patterns'][:1];q['patterns'][0].update(start='2027-12-31',end='2027-12-31',weekdays=[5],operating_weeks=['2027-12-27'],departure_local='23:30');q['timezones']['KUF']='UTC';v=generate(q)
ok('midnight_month_year_BH_conservation',sum(z['block_hours'] for z in v['monthly'])==2 and len(v['monthly'])==2)
q=copy.deepcopy(r);q['patterns'][0]['operating_weeks']=[];v=generate(q);ok('operating_weeks_excludes_dates',len(v['flights'])==5)
blocks=rows('directed_blocks.csv');ok('KUF_UTC4_GOJ_UTC3_80min',any(z['origin']=='KUF' and z['destination']=='GOJ' and z['published_minutes']=='80' for z in blocks))
ok('unsupported_times_not_fabricated',all(not z['nominal_minutes'] and not z['high_minutes'] for z in blocks if z['evidence'] in ['UNKNOWN_CASE_SPECIFIC_BLOCK','P03_GEOMETRIC_DIAGNOSTIC_COSTSCREEN_ONLY']))
cal=rows('resource_calendar.csv');ok('no_SJ_before_H2_any_role',all(not(z['aircraft_type']=='SJ100_PD8' and z['date']<'2027-07-01' and z['state'] not in ['NOT_DELIVERED']) for z in cal))
ok('E0S0_zero_working_resource',all(z['scenario_working_available']=='0' for z in cal if z['evaluation_resource']=='E0/S0'))
ok('resource_unique_date_slot',len(cal)==len(set((z['evaluation_resource'],z['date'],z['slot_id']) for z in cal)))
refs=rows('reference_feasibility.csv');ok('fixed8triangles_19uniquepairs',all(z['triangles']=='8' and z['unique_pairs']=='19' for z in refs if z['programme']=='dashboard_fixed_triangles' and z['case']=='base'))
ok('same24months9resources_KEEP_and_references',len(refs)==24*9*7)
ok('no_unapproved_crew_MRO_PASS',all(z['maintenance']=='UNKNOWN' and z['crew']=='UNKNOWN' for z in cal))
q=copy.deepcopy(r);q['tails'][0].pop('available_from');q['tails'][0]['initial_location']=None;v=generate(q);ok('unknown_availability_position_not_zero_or_known_conflict',v['status']=='CONDITIONAL_PHYSICAL_CONSISTENCY')
for m in load('source_manifest.json'):ok('hash:'+m['local_path'],hashlib.sha256(Path(m['local_path']).read_bytes()).hexdigest()==m['sha256'])
gate=load('source_review_delta.json')
ok('review_numeric_updates_all_zero',all(gate[k]==0 for k in ['numeric_updates_observed_OD','numeric_updates_net_yield','numeric_updates_contracts']))
ok('BRU_quarantined_without_numeric_blocks',all(z['evidence']=='QUARANTINED_UNRESOLVED_ENDPOINT' and not z['nominal_minutes'] and not z['high_minutes'] for z in blocks if 'BRU' in [z['origin'],z['destination']]))
ok('KUF_GOJ_secondary_exceptions_preserved',any('27/30' in z.get('weekdays_raw','') and z['origin']=='KUF' and z['destination']=='GOJ' for z in blocks))
ok('canonical_supplemental_manifest_no_raw',any('canonical_supplemental_directed_services.csv' in m['local_path'] for m in load('source_manifest.json')) and not any(m['local_path'].endswith('/market_supplemental/directed_services.csv') for m in load('source_manifest.json')))
raw=load('handoff.json')['raw_snapshot_sha256'];ok('provided_raw_hash',raw=='aed8463339b988a7c9ac81aa976a4fc25c152e4066b551d25cbdcc16ebe16d53')
result=dict(status='PASS_SCOPED_VALIDATION_NOT_OPS_APPROVAL',count=len(checks),checks=checks,p06_status=p06,limitations=['no market or profitability validation','no actual tail dispatch approval','no future schedule/source verification','reference proxy necessary screen only'])
(ROOT/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(status=result['status'],checks=len(checks),P06=p06['status'])))
