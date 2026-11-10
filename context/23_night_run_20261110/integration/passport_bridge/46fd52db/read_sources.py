#!/usr/bin/env python3
"""Read only exact Git blobs; record their hashes without copying source trees."""
import datetime, hashlib, json, pathlib, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parent
PINS={
'root':'77343ca9dccc14d60c51d4559485646219ecd1cd','brief':'f1774e1f66a9483fb618ca6003abd9dc4d8563e1','screen':'82dffa795146ccc575db1bb45ba9391af44def00','screen_review':'6a038b9bcd2d5476e931885e68fe3b17ef121d5e','repair':'27740ffea0821aa404ecd1013d1bb141613261f3','repair_review':'445a5d523d4b57d8c89b2344e1913de2e5f9dc6b','bridge':'abc09bbb8e62d3513749b60b252d4521997acfc3','methods':'abb1c76254d2d4e3cf9edd5c345b9cdb224f6abe','methods4':'c24bbd36356f46763eed5a1654573b6de31adc6b','budget_review':'2278b184bbc83c590238c9f461581e3b045a11d0','common_review':'7a868d1282b9c4de012e39e9fc1104d2d7f675e4','strategy_review':'0cc043484147cb9f3a23a3d3d2aea9b4a6ce9ed9','primary':'17b4f348f15ea8695688d9435933cb4965568408','source_review':'944b16ac2dcde846e29dac2d47e11e5143f9fc2b','kover':'afadee35ebeefe54a05bdfc5b3e224a370f90e0a','kover_review':'d8634187d452343a369f7cec63be50511bb70020','timebase':'87ee52de15c2bdf396d9c06ba600fd413d5ab4a8','frontier':'519998ed8c97ce5499f356a6d0f81558c7f6ee14','methods5':'f7a034dc91917cc69c5f8b3a729c3d1c6dfeb5b9','core':'505e24663e5952bae9b9540bb9a5a622663bfc2a','critic':'fd086bad2ae30c46e95d6e38954dc99a18627902'}
def read(alias,path):
    sha=PINS[alias]; data=subprocess.check_output(['git','show',f'{sha}:{path}'])
    blob=subprocess.check_output(['git','rev-parse',f'{sha}:{path}'],text=True).strip()
    file=ROOT/'personal_readings.json'
    records=json.loads(file.read_text()) if file.exists() else []
    record={'alias':alias,'commit':sha,'path':path,'git_blob':blob,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'lines':len(data.splitlines()),'read_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'git show exactSHA:path','scope':'personally read; no independent recalculation'}
    if not any(r['commit']==sha and r['path']==path for r in records):
        records.append(record); file.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    return data
if __name__=='__main__':
    for spec in sys.argv[1:]:
        alias,path=spec.split(':',1)
        print('\nSOURCE',alias,PINS[alias],path)
        for n,line in enumerate(read(alias,path).decode().splitlines(),1): print(f'{n}: {line}')
