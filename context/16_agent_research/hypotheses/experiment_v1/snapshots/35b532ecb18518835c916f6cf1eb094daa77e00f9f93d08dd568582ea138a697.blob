#!/usr/bin/env python3
"""Read only explicitly pinned colleague Git blobs; no foreign code execution."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
SHA='fa39de413ac00a93b0214840aae2e7916332cef5'
PREFIX='context/16_agent_research/alternative/product_probe_v1/'
FILES=['normalized/flight_rules.csv','normalized/dated_flights.csv','reference/airport_keys.csv','stay_offer/stay_rules.csv','stay_offer/public_offers.csv','ground_transfer/transfer_rules.csv','ground_transfer/ground_alternatives.csv','ground_transfer/transfer_schedule.csv','ground_transfer/transfer_fare_observations.csv']
def digest(b):return hashlib.sha256(b).hexdigest()
def main():
    refs={}
    for name,expected in [('dataset_manifest.json','28dd4197df4fca88b8bafbac54c09aab53caf633d8d2748a0862c3d60719fc01'),('flight_checkpoint_manifest.json','7d589e1492688aa29aa8396b7f3e3be64f2674fe98521cba6825a4d02364aaa6')]:
        b=subprocess.check_output(['git','show',SHA+':'+PREFIX+name]);assert digest(b)==expected;refs[name]=expected
    records=[]
    for name in FILES:
        b=subprocess.check_output(['git','show',SHA+':'+PREFIX+name]);p=ROOT/'inputs/alternative_fa39de4'/name;p.parent.mkdir(parents=True,exist_ok=True)
        if p.exists():assert p.read_bytes()==b
        else:p.write_bytes(b)
        records.append({'input_id':'alternative:'+name,'source_git_sha':SHA,'source_path':PREFIX+name,'source_url':'https://github.com/Mput13/case_championship/blob/'+SHA+'/'+PREFIX+name,'stored_path':str(p.relative_to(ROOT)),'sha256':digest(b),'bytes':len(b),'admission':'PUBLISHED_RULE_OR_PRODUCT_CONDITION; NOT_PERFORMED_OR_PAID_OR_AVAILABLE'})
    manifest={'input_set_id':'phase2-frozen-002','parent_input_set':'phase2-frozen-001','parent_manifest_sha256':digest((ROOT/'input_manifest.json').read_bytes()),'contract_sha256':digest((ROOT/'contract.json').read_bytes()),'upstream_git_sha':SHA,'verified_upstream_manifest_hashes':refs,'inputs':records,'changes':'C14 current airport Mon/Thu replaces SA02 Mon/Fri announcement for this new set only; prior experiment unchanged','quarantine':'Unknown intermediate stops/operator, hotel timezone/minstay/admission, transfer duration/inventory and ground dates stay unknown. No new endpoint demand/net yield.'}
    p=ROOT/'input_sets/phase2-frozen-002.json';p.parent.mkdir(exist_ok=True);b=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
    if p.exists():assert p.read_bytes()==b
    else:p.write_bytes(b)
    print(json.dumps({'input_set':manifest['input_set_id'],'files':len(records),'manifest_sha256':digest(b)}))
if __name__=='__main__':main()
