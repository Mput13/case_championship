#!/usr/bin/env python3
"""Pin core operating release and join its gates without filling held fields."""
from pathlib import Path
import csv,hashlib,io,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
SHA='b264780e65a0e04afd42da811652039c70fc1def'
PREFIX='context/16_agent_research/core/integration_v1/'
SCOPE={'KVX','MRV','NJC','UFA','SVX','OMS','KJA'}
def digest(b):return hashlib.sha256(b).hexdigest()
def sha(p):return digest(p.read_bytes())
def write(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
    checks={}
    for name,expected in [('input_manifest.json','3c3d3b1b843fe32f91b98fa2b033706d29a6e5e41e32844f631958f97f7a0040'),('operating/output_manifest.json','be78b61e2c26d7bc5f9dd7d1cfcc05de2568a8f41c0ca0edd8757671a6113a93')]:
        b=subprocess.check_output(['git','show',SHA+':'+PREFIX+name]);assert digest(b)==expected;checks[name]=expected
    tables={};inputs=[]
    for name in ['service_rules.csv','dated_instances.csv','physical_leg_requirements.csv','coverage.csv','unmatched.csv','quarantine.csv','airport_keys.csv']:
        b=subprocess.check_output(['git','show',SHA+':'+PREFIX+'operating/'+name]);rows=list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))));total=len(rows)
        if name=='airport_keys.csv':rows=[r for r in rows if r['iata'] in SCOPE]
        p=ROOT/'inputs/core_b264780'/name;p.parent.mkdir(exist_ok=True)
        if name=='airport_keys.csv':
            stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows);stored=stream.getvalue().encode()
        else:stored=b
        if p.exists():assert p.read_bytes()==stored
        else:p.write_bytes(stored)
        tables[name]=rows;inputs.append({'input_id':'core003:'+name,'source_git_sha':SHA,'source_path':PREFIX+'operating/'+name,'source_sha256':digest(b),'source_row_count':total,'stored_path':str(p.relative_to(ROOT)),'stored_sha256':digest(stored),'stored_row_count':len(rows),'transform':'csv exact iata membership in fixed seven-airport scope' if name=='airport_keys.csv' else 'identity'})
    manifest={'input_set_id':'phase2-frozen-003-core-operating','core_input_set':'CORE-INT-V1:ddda7fb1af0361483b27464836996016799e44e35542f21291117c0c790a4c54','source_git_sha':SHA,'verified_upstream_manifests':checks,'contract_sha256':sha(ROOT/'contract.json'),'inputs':inputs,'non_override_rule':'Core frozen operating scope predates alternativefa39de4; historical C14 board rows do not override dated December airport rules in separate input002. Unknown arrival dates/operators/stops remain unknown.'}
    p=ROOT/'input_sets/phase2-frozen-003.json';b=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
    if p.exists():assert p.read_bytes()==b
    else:p.write_bytes(b)
    run_inputs={'input_manifest_sha256':sha(p),'script_sha256':sha(Path(__file__)),'experiment_output_manifest':sha(ROOT/'runs/c26661067277af20/output_manifest.json')}
    run_id=digest(json.dumps(run_inputs,sort_keys=True).encode())[:16];out=ROOT/'operating_join'/run_id
    if out.exists():
        frozen=json.loads((out/'manifest.json').read_text())
        for row in frozen['files']:assert sha(out/row['path'])==row['sha256']
        print(json.dumps({'run_id':run_id,'status':'REPLAY_HASH_MATCH'}));return
    out.mkdir(parents=True)
    keys=tables['airport_keys.csv'];assert len(keys)==7 and len({r['iata'] for r in keys})==7
    assert all(not r['quarantine_reason'] for r in keys)
    old={r['iata']:r for r in csv.DictReader((ROOT/'runs/c26661067277af20/airport_keys.csv').open())}
    key_join=[]
    for r in keys:
        prior=old[r['iata']];key_join.append({'iata':r['iata'],'experiment_airport_id':prior['airport_id'],'core_airport_id':r['airport_id'],'core_airport_key_version':r['airport_key_version'],'id_matches':prior['airport_id']==r['airport_id'],'experiment_iana':prior['iana'],'core_iana':r['iana_timezone'],'iana_matches':prior['iana']==r['iana_timezone'],'core_acceptance':r['key_acceptance'],'quarantine_reason':r['quarantine_reason']})
    assert all(r['id_matches'] and r['iana_matches'] for r in key_join);write(out/'airport_key_join.csv',key_join)
    coverage={(r['experiment_id'],r['origin_iata'],r['destination_iata']):r for r in tables['coverage.csv']};joined=[]
    for r in tables['physical_leg_requirements.csv']:
        c=coverage[r['experiment_id'],r['origin_iata'],r['destination_iata']]
        joined.append({**r,'retained_rule_count':c['retained_rule_count'],'retained_dated_departures_07_27':c['retained_dated_departures_07_27'],'complete_calendar_instances':c['complete_calendar_instances'],'core_source_scope':c['source_scope'],'absence_of_service_claim':c['absence_of_service_claim'],'real_resource_acceptance':'UNKNOWN','binding_rule':'Requirement structure may be shared; incomplete records cannot establish realised capacity'})
    assert all(r['absence_of_service_claim']=='FALSE' for r in joined);write(out/'physical_requirement_coverage_join.csv',joined)
    diagnostics=[]
    for r in tables['service_rules.csv']:
        diagnostics.append({k:r[k] for k in ['service_rule_id','experiment_id','physical_leg_key','origin_iata','destination_iata','source_id','source_row','year_status','weekday_basis','arrival_day_offset','arrival_day_offset_status','operating_carrier_id','operating_carrier_status','marketing_carrier_id','marketing_carrier_status','nonstop_status','rule_acceptance','quarantine_reason']})
    write(out/'service_rule_gates.csv',diagnostics)
    # Preserve partial dated records exactly; never use scenario arrivals as source evidence.
    dated=[]
    for r in tables['dated_instances.csv']:
        dated.append({k:r[k] for k in ['instance_id','experiment_id','origin_iata','destination_iata','departure_date_local','departure_utc','arrival_utc','arrival_day_offset_status','calendar_acceptance','product_acceptance','operating_carrier_id','marketing_carrier_id','nonstop_status']})
    write(out/'dated_source_acceptance.csv',dated)
    result={'run_id':run_id,'key_join_rows':len(key_join),'physical_requirement_rows':len(joined),'rule_rows':len(diagnostics),'dated_rows':len(dated),'unknown_arrival_utc_rows':sum(not r['arrival_utc'] for r in dated),'source_quarantine_rows_retained':len(tables['quarantine.csv']),'actual_resource_acceptance':'UNKNOWN','new_market_acceptance':'NONE','C14_precedence':'Use input002 for newer declared December schedule; keep input003 older limited coverage separately','scope':'No market table, no TOX/RMZ alias substitution, no caller-provided scenario overwrites source blanks'}
    (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps({'run_id':run_id,'inputs':run_inputs,'files':[{'path':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.iterdir()) if p.is_file()]},indent=2)+'\n')
    print(json.dumps(result))
if __name__=='__main__':main()
