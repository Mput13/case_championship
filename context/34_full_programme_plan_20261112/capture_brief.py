#!/usr/bin/env python3
"""Capture the public brief without browser, credentials or model execution."""
import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

BASE = Path(__file__).resolve().parent
URL = 'https://mai-way.ru/tasks/red-wings/'

class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden -= 1
    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)

def main():
    request = urllib.request.Request(URL, headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
        status = response.status
    parser = VisibleText()
    parser.feed(raw.decode('utf-8', 'replace'))
    text = re.sub(r'\s+', ' ', ' '.join(parser.parts)).strip()
    dst = BASE / 'inputs'
    dst.mkdir(exist_ok=True)
    (dst / 'case_live.html').write_bytes(raw)
    (dst / 'case_live.txt').write_text(text+'\n')
    receipt = {'url':URL,'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),'http_status':status,'html_sha256':hashlib.sha256(raw).hexdigest(),'text_sha256':hashlib.sha256((text+'\n').encode()).hexdigest(),'matches':{'number2':re.findall(r'№\s*2|номер\s+(?:2|два)',text,re.I),'digital':re.findall(r'цифров\w*',text,re.I)},'scope':'Only the fetched page text; absence here does not disprove later organizer additions supplied by the user.'}
    (dst / 'brief_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(receipt,ensure_ascii=False))

if __name__ == '__main__':
    main()
