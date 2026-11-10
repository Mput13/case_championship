#!/usr/bin/env python3
"""Addressed public read-only source capture. Does not browse, book, or contact anyone."""
import concurrent.futures
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
DEST=HERE/'inputs/public_20261110'
DEST.mkdir(exist_ok=True)
SOURCES={
 'rw_winter':'https://flyredwings.com/press/news/red-wings-pereshla-na-osenne-zimnee-raspisanie-poletov/',
 'rw_kuf_ist':'https://flyredwings.com/en/press/news/red-wings-osenyu-zapustit-rejsy-iz-samary-v-stambul/',
 'oms_winter':'https://www.aeroomsk.ru/karta-poleta/pdf/w26/w26-20261105.pdf',
 'kuf_dep':'https://ar-kuf.ru/schedule/',
 'kuf_arr':'https://ar-kuf.ru/schedule/?type=arr',
 'svx_dep':'https://ar-svx.ru/schedule/',
 'svx_arr':'https://ar-svx.ru/schedule/?type=arr',
 'ufa_njc_arr':'https://www.airportufa.ru/schedule/nizhnevartovsk/?CITY_CODE=nizhnevartovsk&direction=FROM',
 'ufa_mrv_dep':'https://www.airportufa.ru/schedule/mineralnye_vody/?CITY_CODE=mineralnye_vody&direction=TO',
}


def capture(item):
    name,url=item
    when=datetime.now(timezone.utc).isoformat()
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 research source verification'})
        with urllib.request.urlopen(req,timeout=25) as r:
            data=r.read(); content_type=r.headers.get('Content-Type',''); final_url=r.url
        path=DEST/(name+('.pdf' if 'pdf' in content_type else '.html'))
        path.write_bytes(data)
        return dict(source_id=name,url=url,final_url=final_url,retrieved_at_utc=when,status='HTTP_READ_OK',
                    local=str(path.relative_to(HERE)),content_type=content_type,bytes=len(data),
                    sha256=hashlib.sha256(data).hexdigest(),scope='published offer; no flown/sales/capacity proof')
    except Exception as e:
        return dict(source_id=name,url=url,retrieved_at_utc=when,status='READ_FAILED',exact_error=repr(e))


if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        rows=list(pool.map(capture,SOURCES.items()))
    (HERE/'public_sources_manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(rows,ensure_ascii=False,indent=2))
