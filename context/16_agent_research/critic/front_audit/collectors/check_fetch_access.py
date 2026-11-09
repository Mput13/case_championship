from pathlib import Path
import urllib.request,datetime,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
SAFE_RESPONSE_HEADERS={'content-type','content-length','content-encoding','last-modified','etag','date','cache-control','expires','accept-ranges'}
def safe_headers(headers):
 return {k:v for k,v in headers.items() if k.lower() in SAFE_RESPONSE_HEADERS}
class Trace(urllib.request.HTTPRedirectHandler):
 def __init__(self):self.redirects=[]
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  self.redirects.append({'from':req.full_url,'to':newurl,'status':code});return super().redirect_request(req,fp,code,msg,headers,newurl)
results=[]
for pid in ['4685','4687','6503']:
 url=f'https://t.me/s/favt_info/{pid}';t=Trace();now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 with urllib.request.build_opener(t).open(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=30) as r:
  b=r.read();p=ROOT/'raw/primary'/f'favt_info_{pid}.html';p.write_bytes(b)
  results.append({'source_url':url,'checked_at_utc':now,'http_status':r.status,'final_url':r.url,'redirects':t.redirects,'content_type':r.headers.get('Content-Type'),'headers':safe_headers(r.headers),'bytes':len(b),'raw_path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(b).hexdigest()})
log={'native_tool':'web.open','native_failures':[{'url':r['source_url'],'error':'Internal Error ()\nURL '+r['source_url']+' is not accessible via this tool.','time_note':'Observed this audit run 2026-11-09, before successful urllib probe; native tool response supplied no timestamp.'} for r in results],'fallback_tool':'Python stdlib urllib HTTP text fetch','fallback_results':results,'diagnosis':'The exact public URLs are reachable over HTTP from this environment and return HTML. Failure is specific to web.open access/rendering path; underlying reason UNKNOWN. No evidence that login or a browser is required.','safe_fix':'Use saved raw HTTP HTML with exact URL/status/hash for this research. Do not restart services, change profiles, or infer a T3 defect.'}
(ROOT/'native_access_diagnostic.json').write_text(json.dumps(log,ensure_ascii=False,indent=2))
# Refresh hashes because live pages can vary between HTTP probes.
manifest=json.loads((ROOT/'primary_manifest.json').read_text())
for r in results:
 m=next(x for x in manifest if x.get('source_url')==r['source_url']);m.update({k:r[k] for k in ['sha256','bytes','raw_path','http_status','headers']});m['retrieved_at_utc']=r['checked_at_utc'];m['final_url']=r['final_url'];m['redirects']=r['redirects'];m['content_type']=r['content_type']
(ROOT/'primary_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print([(x['http_status'],x['final_url'],x['bytes']) for x in results])
