#!/usr/bin/env python3
"""Freeze public schedule rows and advertised fares; never infer traffic from seats.

Usage: python3 scripts/collect_network_sources.py --cache /tmp/rw_econ
The cache contains <id>.raw HTTP responses. --refresh downloads the documented
public URLs first. Economics is reproduced offline from the resulting JSON files.
"""
import argparse
import datetime as dt
import hashlib
import html
import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'context/12_network_economics'
PAIRS = [('GOJ', x) for x in ['OMS','KUF','MMK','UFA','AER','VOG','ARH','MRV']] + [
    ('ZIA','ARH'),('ARH','MRV'),('MRV','ZIA'),('ZIA','GSV'),('GSV','AER'),('AER','ZIA'),
    ('SVX','OMS'),('OMS','KUF'),('KUF','SVX'),('SVX','NJC'),('NJC','VOG'),('VOG','SVX')]
KEYS = {tuple(sorted(x)) for x in PAIRS}
KEYS.update(tuple(sorted(x)) for x in [('AER','KUF'),('AER','UFA'),('ARH','KUF'),
    ('ARH','UFA'),('ARH','VOG'),('KUF','MMK'),('MMK','MRV'),('MMK','UFA'),
    ('MMK','VOG'),('MRV','OMS'),('OMS','VOG')])
URLS = {}
for a in ['goj','gsv','kuf','svx']:
    URLS[a+'_schedule'] = f'https://ar-{a}.ru/schedule/'
    URLS[a+'_schedule_arr'] = f'https://ar-{a}.ru/schedule/?type=arr'
URLS.update({
    'rw_destinations':'https://flyredwings.com/cities/418/',
    'zia_season':'https://zia.aero/flights/seasonal-schedule/',
    'ufa_tech':'https://www.airportufa.ru/partners/airlines/specifications/',
    'ufa_cert':'https://www.airportufa.ru/partners/airlines/certification/',
    'ufa_tariff':'https://www.airportufa.ru/upload/medialibrary/be3/76qp5v5bwi8cc5ka59wyd0q179l3biy6.pdf',
    'ufa_fuel':'https://www.airportufa.ru/upload/medialibrary/38c/4agy8jfom9bcf7504sc6m053wnfjo646.pdf',
    'ufa_registration':'https://www.airportufa.ru/upload/medialibrary/809/e6r72hr2dsuw6zp8rk075iva0eeiqp1w.pdf',
    'ufa_aer':'https://www.airportufa.ru/schedule/sochi/',
    'ufa_aer_arr':'https://www.airportufa.ru/schedule/sochi/?CITY_CODE=sochi&direction=FROM',
    'ufa_schedule':'https://www.airportufa.ru/schedule/',
})

class Tables(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.row=None; self.cell=None
    def handle_starttag(self, tag, attrs):
        if tag=='tr': self.row=[]
        if tag in ['td','th'] and self.row is not None: self.cell=[]
    def handle_data(self, data):
        if self.cell is not None: self.cell.append(data)
    def handle_endtag(self, tag):
        if tag in ['td','th'] and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split())); self.cell=None
        if tag=='tr' and self.row is not None:
            self.rows.append(self.row); self.row=None

def freeze(cache, refresh=False):
    OUT.mkdir(exist_ok=True,parents=True)
    sources=[]; rules=[]; texts={}
    for sid,url in URLS.items():
        path=cache/(sid+'.raw')
        if sid=='ufa_registration' and not path.exists(): path=cache/'ufa_registration.pdf'
        if refresh:
            path=cache/(sid+'.raw')
            path.write_bytes(urllib.request.urlopen(url,timeout=30).read())
        if not path.exists(): continue
        data=path.read_bytes()
        accessed=dt.datetime.fromtimestamp(path.stat().st_mtime,dt.timezone(dt.timedelta(hours=3))).date().isoformat()
        sources.append(dict(id=sid,url=url,accessed=accessed,bytes=len(data),
                            sha256=hashlib.sha256(data).hexdigest(),kind='primary',
                            note='snapshot of publication, not guarantee of operation'))
        if sid in ['ufa_aer','ufa_aer_arr']:
            # Only the _active weekday spans denote operation; every card also
            # contains the six/seven inactive weekday labels for layout.
            for chunk in data.decode('utf-8').split('<div class="b-card-sez-card">')[1:]:
                vals=re.findall(r'<span class="b-card-sez-card__info">([^<]+)</span>',chunk)
                dates=re.findall(r'<span class="b-card-sez-card__info (?:start|end)">([^<]+)</span>',chunk)
                days=re.findall(r'<span class="b-card-sez-card__td_day-week[^"<>]*_active[^"<>]*"\s*>([^<]+)</span>',chunk)
                if len(vals)<7 or not dates:continue
                lo,hi=dates[0],dates[-1]
                iso=lambda v:dt.datetime.strptime(v,'%d.%m.%Y').date().isoformat()
                origin,dest=('AER','UFA') if sid.endswith('_arr') else ('UFA','AER')
                rules.append(dict(source=sid,origin=origin,destination=dest,departure_local=vals[0],arrival_local=vals[1],
                    weekdays=', '.join(x.lower() for x in days),period=iso(lo)+' / '+iso(hi),
                    carrier=vals[3],flight=vals[4].replace(' ','-'),aircraft=vals[6]))
            sources[-1].update(schedule_rows=sum(r['source']==sid for r in rules),listed_airports=['AER'],coverage='route specific only')
        if 'schedule' not in sid and sid!='rw_destinations': continue
        text=data.decode('utf-8'); texts[sid]=text
        if not re.match(r'(goj|gsv|kuf|svx)_schedule',sid): continue
        parser=Tables(); parser.feed(text)
        airport=sid[:3].upper(); arr=sid.endswith('_arr')
        valid=[r for r in parser.rows if len(r)==8 and re.match(r'^\d\d:\d\d$',r[0])]
        sources[-1].update(schedule_rows=len(valid),
                           listed_airports=sorted({r[-1] for r in valid}),
                           coverage='full rendered departure/arrival seasonal table')
        for r in valid:
            origin,dest=(r[-1],airport) if arr else (airport,r[-1])
            if tuple(sorted([origin,dest])) not in KEYS: continue
            rules.append(dict(source=sid,origin=origin,destination=dest,departure_local=r[0],
                arrival_local=r[1],weekdays=r[2],period=r[3],carrier=r[4],flight=r[5],aircraft=r[6]))
    fares=[]
    for m in re.finditer(r'<a href="(?P<url>/booking/#/search/(?P<a>[A-Z]{3})(?P<b>[A-Z]{3})(?P<date>\d{8})ADT1)" class="sale-wrap">\s*<span class="sale-name">(?P<label>.*?)</span>\s*<span class="sale-price">от (?P<price>[\d\s\xa0]+) ₽</span>',texts['rw_destinations']):
        a,b=m['a'],m['b']
        if tuple(sorted([a,b])) not in KEYS: continue
        fares.append(dict(origin=a,destination=b,date=dt.datetime.strptime(m['date'],'%Y%m%d').date().isoformat(),
            advertised_from_rub=int(re.sub(r'\s','',m['price'])),label=html.unescape(m['label']),
            url='https://flyredwings.com'+m['url'],source='rw_destinations',
            baggage='UNKNOWN',fees='UNKNOWN',nonstop='UNKNOWN',
            comparable_quote=False,note='advertised minimum for a date; may include connections; not realised yield'))
    for name,obj in [('sources.json',sources),('schedule_rules.json',rules),('advertised_fares.json',fares)]:
        (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(sources=len(sources),target_rules=len(rules),advertised_fares=len(fares))))

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--cache',type=Path,required=True); ap.add_argument('--refresh',action='store_true')
    args=ap.parse_args(); freeze(args.cache,args.refresh)
