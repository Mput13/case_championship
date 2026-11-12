"""Sanitize public captures and write a manifest. No network or credentials."""
import hashlib,json,pathlib,re
P=pathlib.Path(__file__).resolve().parent
f=P/'evidence/fetch_receipts.json';rows=json.loads(f.read_text())
for r in rows:
    if r.get('status')!='ACQUIRED' or 'raw_response_sha256' in r:continue
    target=P/r['path']
    if target.suffix!='.html':continue
    raw=target.read_bytes();s=raw.decode('utf-8',errors='replace')
    s=re.sub(r'<script\b[^>]*>.*?</script>','<!-- script omitted from evidence -->',s,flags=re.S|re.I)
    s=re.sub(r'(data-check|data-validationcode)="[^"]*"',r'\1="OMITTED"',s)
    s=re.sub(r'(<input[^>]*name="(?:sessid|csrf[^\"]*|[^\"]*token[^\"]*)"[^>]*value=")[^"]*',r'\1OMITTED',s,flags=re.I)
    target.write_text(s)
    r['raw_response_sha256']=r.pop('sha256');r['sha256']=hashlib.sha256(target.read_bytes()).hexdigest();r['stored_bytes']=target.stat().st_size;r['sanitization']='scripts and public anti-CSRF fields omitted; no cookies/headers captured'
f.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
files=[]
for path in sorted(P.rglob('*')):
    if not path.is_file() or path.name in ('output_manifest.json','handoff.json'):continue
    b=path.read_bytes();files.append(dict(path=str(path.relative_to(P)),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b)))
(P/'output_manifest.json').write_text(json.dumps(dict(version='P02-v2-seasonal-20261112',files=files,excluded_self_and_handoff=True),ensure_ascii=False,indent=2)+'\n')
print('Manifest files',len(files))
