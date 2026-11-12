#!/usr/bin/env python3
"""Verify exact author preservation and lossless accepted research transport."""
import gzip, hashlib, json, pathlib, subprocess, base64
P=pathlib.Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def main():
    html=(P/'dashboard.html').read_bytes();author=(P/'author_original.html').read_bytes()
    assert html.startswith(b'<!doctype html><html lang="ru">\n'+author+b'\n')
    q=json.loads((P/'canonical_data.json').read_text())['results']
    assert len(q['catalogue'])==9 and sum(len(c['evaluations']) for c in q['catalogue'])==18
    assert q['root_authorisation']['coordinator_acceptance']=='ACCEPTED_FOR_UI'
    contexts=[]
    for pid,p in q['packets'].items():
        gz=base64.b64decode(p['data']);raw=gzip.decompress(gz)
        assert sha(gz)==p['gzip_sha256'] and sha(raw)==p['sha256']
        e=json.loads(raw)
        for v in e['evaluations']:
            r=v['result'];assert r['project']['context']['programme_id']==pid
            assert len(r['project']['results_monthly'])==len(r['delta_monthly'])==24
            assert r['delta_summary']['operating_result'] is None
            assert r['project_incremental_funding']['peak_dated_day_end'] is None
            contexts.append(r['project']['context']['evaluation_id'])
    assert len(contexts)==len(set(contexts))==18
    assert len(json.loads((P/'canonical_data.json').read_text())['products'])==2274
    assert len(html)<25*1024*1024
    subprocess.run(['node','--check',str(P/'canonical.js')],check=True)
    out=dict(status='PASS',author_block_byte_identical=True,author_sha256=sha(author),html_sha256=sha(html),canonical_contexts=contexts,months_each=24,product_rows=2274,full_profit_and_funding_unknown=True,UI_model_recalculation=False,independent_UI_acceptance='NOT_RUN',timed_rehearsal_this_UI='NOT_RUN')
    (P/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='canonical_contexts'},ensure_ascii=False))
if __name__=='__main__':main()
