#!/usr/bin/env python3
"""Read pinned public Git blobs or portable snapshot; never run author models."""
import csv, io, json, hashlib, subprocess, re
from pathlib import Path
from collections import Counter, defaultdict
OUT = Path(__file__).resolve().parent
ROOT = OUT.parent.parent
PINS = {'owner':'1654110dfdc3f6737aebce95e46dd993d631be5b','synthesis':'a460f4686dc267c69001b8fbb18fa01f83ed2af2','prior':'79281803e49763d6ff22c3d06efb941b5c86b53b','methods':'a77e4cfbd14e560d26407479b7252cfcb15f4f41','proposals':'93fa5cf4a10ab67e05c93d19fc5375fc58ef9299'}
SNAP = OUT/'network_fleet_source_snapshot.json'
cache = json.loads(SNAP.read_text()) if SNAP.exists() else {}
used = {}
def sha(b): return hashlib.sha256(b).hexdigest()
def blob(key,path,select=None):
    commit=PINS[key]; ident=commit+':'+path
    if ident in cache:
        e=cache[ident]; assert sha(e['text'].encode())==e['snapshot_sha256'], ident
    else:
        raw=subprocess.check_output(['git','show',ident],cwd=ROOT)
        text=raw.decode(); e={'commit':commit,'path':path,'source_sha256':sha(raw),'selection':'full'}
        if select:
            rows=list(csv.DictReader(io.StringIO(text)))
            chosen=[(i+2,r) for i,r in enumerate(rows) if select(r)]
            f=io.StringIO(newline=''); w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(r for _,r in chosen)
            text=f.getvalue();e['selection']='selected CSV rows';e['source_line_numbers']=[i for i,_ in chosen];e['source_row_count']=len(rows)
        if any(path.endswith(x) for x in ['models/coverage.csv','models/report.md','hypotheses/disposition.csv']):
            text='';e['selection']='hash-only supporting audit; completion/model readouts retained'
        e.update(text=text,snapshot_sha256=sha(text.encode()));cache[ident]=e
    used[ident]=e
    return e['text']
def rows(key,path,select=None):return list(csv.DictReader(io.StringIO(blob(key,path,select))))
def ref(key,path):return PINS[key]+':'+path
def url(key,path):return 'https://github.com/Mput13/case_championship/blob/'+PINS[key]+'/'+path
def emit(name,data,fields=None):
    fields=fields or list(dict.fromkeys(k for r in data for k in r))
    with (OUT/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(data)
    return data
def pair(a,b):return '-'.join(sorted((a,b)))
OR='data/processed/network_routes.csv'; OS='data/processed/network_summary.csv'; OA='data/assumptions/network.csv'; OM='src/network_model.py'
UP='context/23_night_run_20261110/methods/runs/final_variants_v1/network_union.csv'
PC='context/24_network_followup_20261110/model/'
FP='context/23_night_run_20261110/methods/inputs/set001/tsiri_93fa/context/17_aircraft_route_review/model/flights.csv'
owner=rows('owner',OR); summary=rows('owner',OS); assumptions=rows('owner',OA);blob('owner',OM)
union=rows('methods',UP); legs=rows('prior',PC+'dated_legs.csv');freq=rows('prior',PC+'frequencies.csv'); baseline=rows('prior',PC+'baseline_comparison.csv'); contract=json.loads(blob('prior',PC+'network_contract.json'))
previous=rows('methods',FP,lambda r:r['profile']=='ROUTE_INPUTS_UPPER_100' and r['network']=='D_case')
proposals=rows('proposals','context/21_team_proposals/comparison.csv')
for path in ['context/00_brief/case5_requirements.md','docs/01_case_brief.md']:blob('owner',path)
for path in ['parent/completion_readout.md','parent/models_readout.md','models/coverage.csv','models/report.md','hypotheses/disposition.csv']:blob('synthesis','context/25_completion_audit_20261110/'+path)
for path in ['final_variant_contract.json','common_demand_contract.json']:blob('methods','context/23_night_run_20261110/methods/'+path)
options=[]; fleet=[]; register=[]; checks={}; ownergroups={}
for s in summary:
    scen=s['scenario']; hub=s['hub']; oid='OWNER_'+scen+'_'+(hub or 'DIRECT')
    rr=[r for r in owner if r['scenario']==scen and (r['variant']=='Хаб '+hub if hub else r['variant'].startswith('Прямые '))]
    counts=Counter(pair(r['from'],r['to']) for r in rr); mow=sum('MOW' in p.split('-') for p in counts)
    airport=sum('MOW' not in p.split('-') for p in counts)
    ownergroups[oid]=dict(rows=len(rr),unique_geographic_pairs=len(counts),unique_airport_pairs=airport,duplicate_pair_rows=len(rr)-len(counts),mow_pairs=mow)
    options.append(dict(option_id=oid,model_version=PINS['owner'],input_set_id='OWNER_network.csv_'+scen,scenario=scen,portfolio=s['variant'],period='author annual scenario; calendar year UNKNOWN',unit='unique unordered pair / aircraft',source_route_count=s['routes'],source_route_count_unit='hub spokes' if hub else 'selected triangles',source_leg_rows=len(rr),unique_model_pairs=len(counts),unique_airport_pairs=airport,aggregate_MOW_pairs=mow,duplicate_pair_rows=len(rr)-len(counts),airport_pairs=';'.join(sorted(counts)),model_8_12_gate=str(8<=airport<=12 and mow==0),working_allocated=int(s['aircraft'])-1,reserve_assumption=1,total_model_aircraft=s['aircraft'],working_ceiling='',total_fleet_cap=10,dated_legs='',schedule_status='NO_DATED_ROTATIONS; aggregate hours gate',decision_status='TEAM_DECISION',evidence_class='AUTHOR_SCENARIO',source=ref('owner',OS)+';'+ref('owner',OR)+';'+ref('owner',OA)+';'+ref('owner',OM),boundary='MOW is aggregate city code; no expansion to ZIA/DME/SVO; direct routes counts triangles, not route pairs'))
    fleet.append(dict(option_id=oid,period='author annual scenario; '+('52' if scen=='base' else '48')+' model weeks',aircraft_type='SSJ proxy; SJ-100/PD-8 not validated',model_analogue='SSJ100 / SSJ-95B author assumption',seats_per_leg=100,working_aircraft=int(s['aircraft'])-1,reserve_aircraft=1,total_aircraft=s['aircraft'],total_fleet_cap=10,working_ceiling='',method='ceil(sum weekly block hours/(10 h/day * 7 days))+1 reserve; working=reported total-1',schedule_status='NO_DATED_ROTATIONS',actual_free_aircraft='',actual_free_status='UNKNOWN',model_version=PINS['owner'],input_set_id='OWNER_network.csv_'+scen,source=ref('owner',OS)+';'+ref('owner',OA)+';'+ref('owner',OM),boundary='scalar hours gate does not prove aircraft circulation, slots, crew or MRO'))
    for n,r in enumerate(rr):
        register.append(dict(route_id=oid+'_'+str(n+1),option_id=oid,component=r['variant'],scenario=scen,origin=r['from'],destination=r['to'],pair_id=pair(r['from'],r['to']),grain='unordered segment pair; frequency each direction',airport_resolution='AGGREGATED_MOW' if 'MOW' in (r['from'],r['to']) else 'AIRPORT_CODE',frequency=r['freq_week_each_way'],frequency_unit='departures per direction per model week',frequency_period='author scenario typical week; calendar dates UNKNOWN',pax_year_segments=r['pax_year_segments'],pax_year_local=r['pax_year_local'],pax_year_transfer_segments=r['pax_year_transfer_seg'],pax_period='author annual scenario; '+('52' if scen=='base' else '48')+' weeks; calendar year UNKNOWN',pax_unit='occupied leg segments/year; not unique endpoint OD',change='',change_status='UNKNOWN',method='AUTHOR_SCENARIO; '+r['demand_source']+'; freq_for/capture in src/network_model.py',donor_route='',donor_status='UNKNOWN',model_version=PINS['owner'],input_set_id='OWNER_network.csv_'+scen,source=ref('owner',OR),source_row=owner.index(r)+2,boundary='retain triangle membership and repeated pair rows; not additive unique routes; proxy/source label is not validated OD'))
# Source dated ledgers have separate aircraft labels by alternative, never summed as actual tails.
component_legs={k:[r for r in legs if r['common_network']==k] for k in contract['networks']}
component_legs['D_previous_best8']=previous
for k,ll in component_legs.items():
    assert len({r['id'] for r in ll})==len(ll)
    c=Counter(pair(r['origin'],r['destination']) for r in ll)
    checks[k]={'dated_legs':len(ll),'unique_pairs':len(c),'working_label_count':len({r['aircraft'] for r in ll}),'duplicate_flight_ids':0,'pairs':sorted(c)}
    if k in contract['networks']:
        v=contract['networks'][k];assert len(ll)==v['dated_legs'];assert sorted(c)==sorted(v['pairs']);assert checks[k]['working_label_count']==v['model_working_aircraft']
    fs=defaultdict(list)
    for r in ll:fs[(r['origin'],r['destination'])].append(r)
    for (a,b),fl in sorted(fs.items()):
        if k!='D_previous_best8':
            fr=next(r for r in freq if r['network']==k and r['origin']==a and r['destination']==b);assert int(fr['departures_week'])==len(fl)
        register.append(dict(route_id=k+'_'+a+'_'+b,option_id='METHODS_'+k,component=k,scenario='base;cautious fixed supply',origin=a,destination=b,pair_id=pair(a,b),grain='directed leg; group reverse direction for route pair',airport_resolution='AIRPORT_CODE',frequency=len(fl),frequency_unit='directed departures in dated model week',frequency_period='2026-12-07/2026-12-13',pax_year_segments='',pax_year_local='',pax_year_transfer_segments='',pax_period='',pax_unit='',change='ADD',change_status='AUTHOR_SCENARIO_ADDITIONAL_FLIGHTS; not actual change approval',method='count exact dated flight IDs; synthetic block/calendar',donor_route='',donor_status='UNKNOWN; no actual donor assigned',model_version=PINS['methods'] if k=='D_previous_best8' else PINS['prior'],input_set_id='FINAL_VARIANT_SYNTHESIS_V1' if k=='D_previous_best8' else 'set001+common_demand_contract_v1',source=ref('methods',FP) if k=='D_previous_best8' else ref('prior',PC+'dated_legs.csv')+';'+ref('prior',PC+'frequencies.csv'),source_row='',boundary='MODEL_DATED_LEGS_NOT_PUBLISHED_OR_PERFORMED; no annual extrapolation',source_profile=fl[0]['profile'],dated_flight_ids=';'.join(r['id'] for r in fl),dates=';'.join(sorted({r['date'] for r in fl})),change_source=ref('proposals','context/21_team_proposals/comparison.csv')))
unionchecks=[]
for r in union:
    components=r['portfolio'].split('+'); pp=set(); total=0;flight_keys=set();scoped_tails=set()
    for c in components:
        ll=component_legs[c];cp={pair(x['origin'],x['destination']) for x in ll};pp|=cp;total+=len(cp)
        flight_keys.update((c,x['id']) for x in ll);scoped_tails.update((c,x['aircraft']) for x in ll)
    assert sorted(pp)==r['airport_pairs'].split(';')
    assert len(pp)==int(r['unique_model_airport_pairs'])
    assert total-len(pp)==int(r['duplicate_pair_count_removed'])
    assert len(flight_keys)==int(r['model_dated_flight_instances'])
    assert len(scoped_tails)==int(r['working_allocated'])
    assert (8<=len(pp)<=12)==(r['model_8_12_count_gate']=='True')
    unionchecks.append({'portfolio':r['portfolio'],'unique_pairs':len(pp),'duplicate_pairs_removed':total-len(pp),'scoped_working_labels':len(scoped_tails),'physical_tail_uniqueness':'UNKNOWN; no registrations; source sums component allocations'})
    oid='METHODS_'+r['portfolio']
    options.append(dict(option_id=oid,model_version=PINS['methods'],input_set_id=r['input_set_id'],scenario='base;cautious source supply; no new joint optimization',portfolio=r['portfolio'],period='2026-12-07/2026-12-13 model week',unit='unique unordered airport pair / aircraft',source_route_count=r['unique_model_airport_pairs'],source_route_count_unit='union unordered airport pairs',source_leg_rows=r['model_dated_flight_instances'],unique_model_pairs=len(pp),unique_airport_pairs=len(pp),aggregate_MOW_pairs=0,duplicate_pair_rows=r['duplicate_pair_count_removed'],airport_pairs=r['airport_pairs'],model_8_12_gate=r['model_8_12_count_gate'],working_allocated=r['working_allocated'],reserve_assumption=r['reserve_assumption'],total_model_aircraft=int(r['working_allocated'])+int(r['reserve_assumption']),working_ceiling=4,total_fleet_cap='',dated_legs=r['model_dated_flight_instances'],schedule_status='DATED_MODEL_COMPONENTS; joint physical rotation UNKNOWN' if len(components)>1 else 'DATED_MODEL_ONLY; physical dispatch UNKNOWN',decision_status='TEAM_DECISION',evidence_class='AUTHOR_SCENARIO',source=ref('methods',UP)+';'+ref('methods','context/23_night_run_20261110/methods/final_variant_contract.json'),boundary=r['scope'],joint_model_gates_pass=r['joint_model_gates_pass']))
    fleet.append(dict(option_id=oid,period='2026-12-07/2026-12-13',aircraft_type='100-seat SSJ-class author scenario; dispatch variant UNKNOWN',model_analogue='existing SSJ-class; not validated SJ-100/PD-8',seats_per_leg=100,working_aircraft=r['working_allocated'],reserve_aircraft=r['reserve_assumption'],total_aircraft=int(r['working_allocated'])+1,total_fleet_cap='',working_ceiling=4,method='count component-scoped working labels; sum source allocations; pool reserve once by assumption; no joint tail optimization',schedule_status='DATED_MODEL_COMPONENTS' if len(components)>1 else 'DATED_MODEL_ONLY',actual_free_aircraft='',actual_free_status='UNKNOWN',model_version=PINS['methods'],input_set_id=r['input_set_id'],source=ref('methods',UP)+';'+ref('methods','context/23_night_run_20261110/methods/final_variant_contract.json'),boundary='component labels are not registrations; same real aircraft cannot be promised to overlapping alternatives',source_profiles=';'.join(c+':'+component_legs[c][0]['profile'] for c in components)))
emit('network_options.csv',options);emit('route_register.csv',register);emit('fleet_requirements.csv',fleet)
selected=[]
for slot in range(1,13):
    selected.append(dict(slot_id=slot,selection_status='TEAM_DECISION',team_accepted_source='',option_id='',origin='',destination='',pair_id='',change='',frequency='',frequency_unit='',period_start='',period_end='',pax_year='',pax_definition='',aircraft_type='',required_working='',reserve='',rotation_id='',calculation_status='WAITING_FINAL_CALC',source='',boundary='empty slot; does not count toward 8–12 selected routes'))
emit('selected_network_template.csv',selected)
supply=[];balance=[]
# These are resource time buckets, not a roadmap or promised delivery milestones.
for period in ['2027_H1','2027_H2','2028']:
    supply.append(dict(period=period,scenario_id='',batch_id='',aircraft_type='SJ-100/PD-8 new; existing SSJ tracked separately',new_N_t='',delivered='',delivery_date='',inducted='',induction_date='',technical_ready='',technical_ready_date='',crew_ready='',mro_ready='',existing_allocated='',existing_obligations='',reserve='',availability='',actual_free='',quantity_unit='aircraft; distinct registrations',earliest_case_delivery='H2_2027',delivery_status='UNKNOWN; earliest case constraint is not delivery promise',status='WAITING_FINAL_CALC',team_status='TEAM_DECISION',source=ref('owner','context/00_brief/case5_requirements.md'),boundary='new_N_t/delivered are cumulative within type; batch_id distinct, no duplicate tail; case constraint only, not observed supply'))
    balance.append(dict(period=period,scenario_id='',aircraft_type='',ready_existing='',ready_new='',existing_obligations='',reserve='',available_working='',required_working='',balance_aircraft='',physical_rotation_gate='',unit='aircraft',formula_available='ready_existing + ready_new - existing_obligations - reserve',formula_balance='available_working - required_working',null_rule='if any numeric dependency is empty return NULL, never substitute 0',dependencies='fleet_supply_template: ready/type/period/obligations/reserve; fleet_requirements or final selected dated rotations: required_working',status='WAITING_FINAL_CALC',source=ref('synthesis','context/25_completion_audit_20261110/models/report.md'),boundary='ready_new counts inducted AND technically/crew/MRO ready unique tails once; allocated existing is subset of ready_existing, not additive; no physical acceptance from nonnegative balance'))
emit('fleet_supply_template.csv',supply);emit('resource_balance_template.csv',balance)
SNAP.write_text(json.dumps(used,ensure_ascii=False,indent=2)+'\n')
# Verification of the package and protected original files, no author-model execution.
protected_path=OUT/'protected_owner_files.json'
protected=json.loads(protected_path.read_text()) if protected_path.exists() else {}
protected_bad=[p for p,h in protected.items() if not (ROOT/p).is_file() or sha((ROOT/p).read_bytes())!=h]
source_checks=[]
for ident,e in used.items():
    proc=subprocess.run(['git','show',ident],cwd=ROOT,capture_output=True)
    state='PASS' if proc.returncode==0 and sha(proc.stdout)==e['source_sha256'] else ('SNAPSHOT_ONLY' if proc.returncode else 'FAIL')
    assert state!='FAIL',ident
    source_checks.append(dict(source=ident,source_sha256=e['source_sha256'],snapshot_sha256=e['snapshot_sha256'],selection=e['selection'],verification=state))
formatchecks={}
for name in ['network_options.csv','route_register.csv','selected_network_template.csv','fleet_requirements.csv','fleet_supply_template.csv','resource_balance_template.csv']:
    b=(OUT/name).read_bytes();rs=list(csv.DictReader(io.StringIO(b.decode())))
    assert b'\r' not in b and all(None not in r and all(v is not None for v in r.values()) for r in rs)
    formatchecks[name]={'rows':len(rs),'LF_only':True,'rectangular':True,'sha256':sha(b)}
assert len(owner)==128 and len(legs)==64 and len(freq)==40 and len(union)==15 and len(previous)==16
assert all(not r['origin'] and not r['destination'] and not r['frequency'] and not r['pax_year'] for r in selected)
assert all(not r['balance_aircraft'] and not r['available_working'] for r in balance)
assert all(not r['actual_free_aircraft'] for r in fleet)
assert all(not r['new_N_t'] and not r['delivered'] and not r['availability'] for r in supply)
assert not protected_bad,protected_bad
reference_count=0
for table in [options,register,fleet,supply,balance]:
    for record in table:
        for field in ['source','change_source']:
            for source in record.get(field,'').split(';'):
                if source:
                    assert source in used,source
                    reference_count+=1
notes_path=OUT/'network_fleet_notes.md'
link_checks=[]
if notes_path.exists():
    for target in re.findall(r'\]\(([^)]+)\)',notes_path.read_text()):
        if target.startswith('https://github.com/Mput13/case_championship/blob/'):
            tail=target.split('/blob/',1)[1];commit,path=tail.split('/',1)
            assert commit+':'+path in used,target
        else:
            assert (OUT/target).is_file(),target
        link_checks.append({'target':target,'status':'PASS_PINNED_SOURCE_OR_LOCAL_FILE'})
# Repeated builds must reproduce all six CSVs exactly from the public snapshots.

validation=dict(component='network_fleet',status='PASS',scope='source/table/count/schema verification only; no optimizer or financial replay',source_counts=dict(owner_routes=len(owner),owner_summary=len(summary),methods_union=len(union),prior_dated_legs=len(legs),prior_directed_frequencies=len(freq),prior_baseline_comparison=len(baseline),previous_selected_flights=len(previous)),owner_pair_checks=ownergroups,dated_component_checks=checks,union_checks=unionchecks,format_checks=formatchecks,source_checks=source_checks,protected_files=dict(checked=len(protected),expected=381,manifest_sha256=sha(protected_path.read_bytes()) if protected else '',mismatches=protected_bad,status='PASS' if len(protected)==381 else 'NOT_AVAILABLE_FOR_PORTABLE_REBUILD'),null_checks=dict(csv_null_encoding='empty cell',json_null_encoding='null',selected_slots=12,team_accepted_routes=0,unknown_actual_free_preserved=True,supply_unknown_preserved=True,balance_unknown_preserved=True),model_execution='NOT_RUN',source_snapshot_sha256=sha(SNAP.read_bytes()),reference_checks={'csv_source_references':reference_count,'notes_links':link_checks},artifact_hashes={p.name:sha(p.read_bytes()) for p in [Path(__file__),notes_path] if p.exists()})
(OUT/'network_fleet_validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'PASS','output_counts':{k:v['rows'] for k,v in formatchecks.items()},'protected_checked':len(protected),'protected_mismatches':len(protected_bad),'sources':len(used)},ensure_ascii=False))
