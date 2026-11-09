#!/usr/bin/env python3
"""Copy immutable numeric tables from pinned Git blobs; no HTTP/model execution."""
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parent
PIN='a875cdd1ecaf778f53ba06cab1c66581a7f215c6'
BASE='context/16_agent_research/core/'
FILES=[
 'normalized/airport_version.csv','normalized/city_version.csv','canonical_keys.csv',
 'normalized/timezone_crosscheck.csv','normalized/market_observation.csv','dataset_manifest.json',
 'branches/operating_evidence/normalized/carrier_source_aliases.csv',
 'branches/operating_evidence/normalized/uvt_schedule_rules_unique.csv',
 'branches/operating_evidence/normalized/iraero_published_itineraries.csv',
 'branches/operating_evidence/normalized/svx_published_schedule_rules.csv',
 'branches/operating_evidence/normalized/omsk_domestic_timetable_rows.csv',
 'branches/operating_evidence/normalized/omsk_outbound_week_20261207.csv',
 'branches/operating_evidence/normalized/azimuth_flight_instances.csv',
 'branches/social_economy/normalized/region_crosswalk.csv',
]
def main():
    entries=[]
    for path in FILES:
        body=subprocess.check_output(['git','show',PIN+':'+BASE+path]);dest=ROOT/'inputs'/path
        dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():assert dest.read_bytes()==body, 'Refuse to overwrite frozen bytes'
        else:dest.write_bytes(body)
        entries.append(dict(path=str(dest.relative_to(ROOT)),source_git_path=BASE+path,source_commit=PIN,
            sha256=hashlib.sha256(body).hexdigest(),size_bytes=len(body)))
    contract=json.loads((ROOT/'contract.json').read_text())
    digest=hashlib.sha256(json.dumps(dict(contract=contract,inputs=entries),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    manifest=dict(schema_version='core-integration-input-set-v1',input_set_id='CORE-INT-V1:'+digest,
        frozen_source_commit=PIN,files=entries,contract=contract,
        critical_overlays=['CM01 semantic observation ID includes period/entity/unit/kind; preserve both rows',
            'CM02 Tobolsk freeform→TOX mapping quarantined, no substitution from another auxiliary table',
            'Inherited timezone conflicts and coordinate disagreements remain quarantined'])
    dest=ROOT/'input_manifest.json'
    if dest.exists():assert json.loads(dest.read_text())==manifest,'Frozen input manifest changed'
    else:dest.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(manifest['input_set_id'],len(entries),'files')
if __name__=='__main__':main()
