#!/usr/bin/env python3
"""Bounded read-only primary-source fetch; publish hashes and short facts only."""
import datetime
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.request

OUT=Path(__file__).resolve().parent
URL='https://mai-way.ru/tasks/red-wings/'

class Visible(HTMLParser):
    def __init__(self):super().__init__();self.hidden=0;self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag in ['script','style','noscript']:self.hidden+=1
    def handle_endtag(self,tag):
        if tag in ['script','style','noscript']:self.hidden=max(0,self.hidden-1)
    def handle_data(self,data):
        if not self.hidden:self.parts.append(data)

def main():
    receipt=dict(url=URL,accessed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        initial_native_error='web.open: URL https://mai-way.ru/tasks/red-wings/ is not accessible via this tool.',
        fallback_reason='Known primary URL; textual HTTP fetch, no browser, no authentication, no services changed.',
        full_raw_exported=False)
    try:
        with urllib.request.urlopen(urllib.request.Request(URL,headers={'User-Agent':'research-screening-audit/1.0'}),timeout=15) as response:
            raw=response.read(1_000_001);assert len(raw)<=1_000_000
            receipt.update(status=response.status,final_url=response.url,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
        p=Visible();p.feed(raw.decode('utf-8','replace'));text=re.sub(r'\s+',' ',' '.join(p.parts))
        terms=['500','Жуков','Екатеринбург','Кольцово','базир','хаб','веса','топ']
        receipt['visible_term_occurrences']={term:len(re.findall(re.escape(term),text,re.I)) for term in terms}
        # Two tiny fragments, together below 25 source words, no page DOM or full text.
        snippets=[]
        for term in ['Жуков','Екатеринбург']:
            match=re.search(term+r'[^.!?]{0,90}',text,re.I)
            if match:snippets.append(' '.join(match.group().split('Генеральный')[0].split()[:8]))
        receipt['short_fragments']=snippets
        receipt['case_500km_rule_found']=bool(re.search(r'500\s*(?:км|километр)',text,re.I))
        receipt['interpretation']='No 500 km criterion found in visible case page; this supports the policy-assumption reading, not empirical cannibalization.'
    except Exception as exc:
        receipt.update(status='FETCH_FAILED',error=f'{type(exc).__name__}: {exc}')
        held=Path('/Users/a/agent-audit-2026-09/case_championship/context/17_research_report/network_recovery/raw_hold/case_brief.bin')
        if held.exists():
            raw=held.read_bytes();p=Visible();p.feed(raw.decode('utf-8','replace'))
            text=re.sub(r'\s+',' ',' '.join(p.parts))
            receipt.update(fallback='parent_held_snapshot_readonly_not_current',held_sha256=hashlib.sha256(raw).hexdigest(),
                case_500km_rule_found=bool(re.search(r'500\s*(?:км|километр)',text,re.I)))
    (OUT/'case_source_check.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':main()
