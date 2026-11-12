"""Hash finished P05 package; handoff binds manifest without self-hash cycles."""
import hashlib
import json
from model import ROOT, VERSION, write_json


def main():
    rows=[]
    for p in sorted(ROOT.rglob('*')):
        rel=p.relative_to(ROOT)
        if not p.is_file() or '.runtime' in rel.parts or '__pycache__' in rel.parts or str(rel) in ['output_manifest.json','handoff.json']:
            continue
        rows.append(dict(path=str(rel),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    write_json(ROOT/'output_manifest.json',dict(version=VERSION,files=rows,file_count=len(rows),excluded=['output_manifest.json','handoff.json','.runtime/**','__pycache__/**'],
        input_binding='input_manifest.json uses exact Gitblobs; source_lock.json binds newpublic bytes',independent_acceptance='NOT_RUN'))
    v=json.loads((ROOT/'validation.json').read_text());b=json.loads((ROOT/'build_summary.json').read_text())
    write_json(ROOT/'handoff.json',dict(package='P05',version=VERSION,branch='t3/passenger-demand-net-yield',parent_commit='65cab12d2eae49dc91d1f77dd4860bc9bd7e20d2',
        package_commit_binding='Exact finalcommit is reported to coordinator; resolve this manifest at that commit, not livebranch',
        manifest_sha256=hashlib.sha256((ROOT/'output_manifest.json').read_bytes()).hexdigest(),file_count=len(rows),outputs=['od_monthly.csv','choice_model.json','net_yield.csv','validation.json','producer_fragments.json','ordered_legs.csv','response_fragments.json'],
        dependencies=dict(P00R='b7d74e67dd6c603db049b1915b1afec987e3b458',P02v2='d9486f113f074c185a94bcc5c0afeef12ea3574f',P04final='620a0ac4bb11763319c4227485f6a3996b91d367',P03v2='79dc698b99dfe866886d32376ed388e85bdd039c',P06early='bc70308fe091c5767dbf26b02d06a7d750a65614'),
        used_assumption_ids=v['used_assumption_ids'],register_change='16 explicitP05assumptions; historicalbaselines not overwritten',
        own_checks=dict(mechanical=len(v['checks']),failed=sum(not c['passed'] for c in v['checks']),engine='evaluate/compare/scenario:conditional allocationexecuted; operationalresult/fundingnull',
                        season_holdout='10 primary2026 carrieraggregatemonths,notrouteOD',segment_proxy='25annualrows groupedholdout;medianAPE62.05%;notendpointOD'),
        coverage=b,remaining_fields='dependency_requests.csv',hypothesis_proposals='hypotheses_delta.json',independent_review='NOT_RUN_AUTHOR_NOT_ELIGIBLE_AS_P13_REVIEWER',
        release='USABLE_SCENARIO_MODEL_INTERFACE_FOR_CASE_SJ; notfullRWmarketcalibration,operationalacceptance,wholeKEEP,profit,funding ormarketsharedecision',
        limitations=['No new observed monthly endpointOD','Behavioural/ownmigration/potentialmapping notidentified','P03only11–17Dec2028 diagnosticweek','Unknown competitorphysicalinventory inoutsidecomposite,notinventedflights',
                     'FullKEEP,contractblocks,futureprice/tax/distributionandcash unresolved','Dynamicresponseallocationusable;earlyP06comparepolicygate unresolved','InternationalP02I separateversion;notblockingCASE_SJ'],
        reproduction=['python3 P05/build.py','python3 P05/check_engine.py','python3 P05/validate.py','python3 P05/package_notes.py','python3 P05/seal.py']))
    print(json.dumps(dict(files=len(rows),manifest_sha256=hashlib.sha256((ROOT/'output_manifest.json').read_bytes()).hexdigest(),total_bytes=sum(r['bytes'] for r in rows))))


if __name__=='__main__':main()
