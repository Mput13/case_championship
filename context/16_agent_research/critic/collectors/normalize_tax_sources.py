#!/usr/bin/env python3
"""Decode declared HTML encodings and retain visible text for source inspection."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib
import json
import re

BASE=Path(__file__).resolve().parents[1]
class Text(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.hidden=0
    def handle_starttag(self,t,a):
        if t in ('script','style'):self.hidden+=1
    def handle_endtag(self,t):
        if t in ('script','style'):self.hidden=max(0,self.hidden-1)
    def handle_data(self,s):
        if not self.hidden:self.parts.append(s)

def main():
    out=[]
    for name in ['fns_2026_excise_rates.html','fns_linked_nk_article200.html']:
        p=BASE/'raw'/name;b=p.read_bytes();m=re.search(br'charset=["\s]*([^\s";>]+)',b[:4096],re.I)
        enc=m[1].decode('ascii') if m else 'utf-8'
        parser=Text();parser.feed(b.decode(enc));text=' '.join(' '.join(parser.parts).split())+'\n'
        q=BASE/'normalized'/(name+'.txt');q.write_text(text)
        out.append(dict(raw_path=str(p.relative_to(BASE)),raw_sha256=hashlib.sha256(b).hexdigest(),declared_encoding=enc,normalized_path=str(q.relative_to(BASE)),normalized_sha256=hashlib.sha256(q.read_bytes()).hexdigest(),method='HTMLParser visible data excluding script/style; collapse whitespace'))
    (BASE/'evidence/tax_source_transforms.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(out))

if __name__=='__main__':main()
