#!/usr/bin/env python3
"""Fetch bounded public Telegram HTML and extract exact main/reply class tokens.

The reviewed front fetcher provides URL/date conventions, but its first-match text
regex is deliberately replaced. Output is a source text archive, not event labels.
"""
import argparse
import csv
import datetime as dt
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
import shlex
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
SAFE_HEADERS={'content-type','content-length','last-modified','etag','date','cache-control'}
VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
class Node:
    def __init__(self,tag='',attrs=None):self.tag=tag;self.attrs=dict(attrs or []);self.children=[]
    def nodes(self):
        yield self
        for c in self.children:
            if isinstance(c,Node):yield from c.nodes()
    def text(self):
        if self.tag=='br':return '\n'
        return ''.join(c.text() if isinstance(c,Node) else c for c in self.children)
class DOM(HTMLParser):
    def __init__(self):super().__init__();self.root=Node();self.stack=[self.root]
    def handle_starttag(self,t,a):
        n=Node(t,a);self.stack[-1].children.append(n)
        if t not in VOID:self.stack.append(n)
    def handle_startendtag(self,t,a):self.stack[-1].children.append(Node(t,a))
    def handle_endtag(self,t):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==t:self.stack=self.stack[:i];break
    def handle_data(self,d):self.stack[-1].children.append(d)
def parse(body,channel):
    dom=DOM();dom.feed(body);rows=[]
    for n in dom.root.nodes():
        post=n.attrs.get('data-post','')
        if not re.fullmatch(re.escape(channel)+r'/\d+',post):continue
        nodes=list(n.nodes());texts=[x for x in nodes if 'js-message_text' in x.attrs.get('class','').split()]
        replies=[x for x in nodes if 'js-message_reply_text' in x.attrs.get('class','').split()]
        times=[x.attrs['datetime'] for x in nodes if x.tag=='time' and 'datetime' in x.attrs]
        if len(texts)>1:raise ValueError('Multiple main text nodes for '+post)
        rows.append(dict(channel=channel,message_id=post.split('/')[1],published_at_utc=times[-1] if times else '',
            main_text=texts[0].text().strip() if texts else '',reply_text='\n'.join(x.text().strip() for x in replies),
            main_text_node_count=len(texts),reply_node_count=len(replies),text_status='MAIN_BODY_EXACT_CLASS' if texts else 'NO_TEXT_NODE_MEDIA_OR_SERVICE',
            source_url='https://t.me/'+post))
    return rows
def main():
    ap=argparse.ArgumentParser();ap.add_argument('channel');ap.add_argument('--before',action='append',default=[]);ap.add_argument('--query',action='append',default=[]);ap.add_argument('--latest',action='store_true');args=ap.parse_args()
    boundaries=[('before',v) for v in args.before]+[('query',v) for v in args.query]+([('latest','latest')] if args.latest or not (args.before or args.query) else [])
    dest=ROOT/'raw/telegram_main'/args.channel;dest.mkdir(parents=True,exist_ok=True)
    manifest_file=ROOT/('telegram_'+args.channel+'_manifest.json')
    entries=json.loads(manifest_file.read_text())['datasets'] if manifest_file.exists() else []
    file=ROOT/'normalized'/('telegram_main_'+args.channel+'.csv')
    records=list(csv.DictReader(file.open())) if file.exists() else []
    for kind,value in boundaries:
        boundary='query_'+hashlib.sha256(value.encode()).hexdigest()[:12] if kind=='query' else value
        url='https://t.me/s/'+args.channel+('' if kind=='latest' else '?'+urllib.parse.urlencode({'q':value} if kind=='query' else {'before':int(value)}))
        at=dt.datetime.now(dt.timezone.utc).isoformat();e=dict(dataset_id='telegram_main_'+args.channel+'_'+boundary,source_url=url,retrieved_at_utc=at,
            organization='Росавиация' if args.channel=='favt_ru' else 'Publisher '+args.channel,grain='public message',geographic_coverage='Per message',temporal_coverage='Parsed publication range',
            publication_date='Per message',key_fields='channel;message_id;snapshot',units='text',license='UNKNOWN; official public messages, retain attribution',
            collector_version='telegram-main-dom-v1',command=shlex.join(['python3','context/16_agent_research/core/collectors/fetch_telegram_main.py',args.channel]+(['--latest'] if kind=='latest' else ['--query' if kind=='query' else '--before',value])),
            decision_use='Primary published market and airport aggregates with dates; parser separates replies',limitations='Bounded selected snapshots; not full archive, not operating event classifier; forwarding and claims need semantic review')
        try:
            with urllib.request.urlopen(url,timeout=45) as r:
                body=r.read(1_000_001);e['http_status']=r.status;e['response_headers']={k:v for k,v in r.headers.items() if k.lower() in SAFE_HEADERS}
            if len(body)>1_000_000:raise ValueError('1MB per-page limit')
            f=dest/(boundary+'.html')
            if f.exists():f=dest/(boundary+'_'+dt.datetime.now(dt.timezone.utc).strftime('%H%M%S')+'.html')
            f.write_bytes(body);rs=parse(body.decode(),args.channel)
            for r in rs:r['raw_path']=str(f.relative_to(ROOT));r['snapshot_at_utc']=at
            records+=rs;e.update(raw_path=str(f.relative_to(ROOT)),sha256=hashlib.sha256(body).hexdigest(),size_bytes=len(body),record_count=len(rs),acquisition_status='PARSED',compression='none')
        except Exception as x:e.update(acquisition_status='ACCESS_FAILED',error=type(x).__name__+': '+str(x),raw_path=None,sha256=None,record_count=None)
        entries.append(e);print(e['dataset_id'],e['acquisition_status'],e.get('record_count'),e.get('error',''),flush=True)
    if records:
        with file.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    manifest_file.write_text(json.dumps(dict(datasets=entries),ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
