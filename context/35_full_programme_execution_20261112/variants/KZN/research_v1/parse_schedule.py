"""Нормализация только скачанных KZN departures; codeshare не отдельный борт."""
import csv,hashlib,json,re
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class Node:
    def __init__(self,tag='',attrs=None):self.tag=tag;self.attrs=dict(attrs or []);self.children=[]
    def text(self):return ' '.join((' '.join(x.text() if isinstance(x,Node) else x for x in self.children)).split())
    def find(self,cls):
        out=[]
        if cls in self.attrs.get('class','').split():out.append(self)
        for c in self.children:
            if isinstance(c,Node):out+=c.find(cls)
        return out
class DOM(HTMLParser):
    def __init__(self):super().__init__();self.root=Node();self.stack=[self.root]
    def handle_starttag(self,t,a):
        n=Node(t,a);self.stack[-1].children.append(n)
        if t not in ['area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr']:self.stack.append(n)
    def handle_endtag(self,t):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==t:self.stack=self.stack[:i];break
    def handle_data(self,d):self.stack[-1].children.append(d)
def parse():
    receipts={x['source_id']:x for x in json.loads((ROOT/'fetch_receipts.json').read_text())};rows=[]
    for f in sorted((ROOT/'evidence').glob('SCH-*.html')):
        sid=f.stem;iata=sid[4:];p=DOM();p.feed(f.read_text());nodes=p.root.find('flights-table__item')
        # Невалидный slug izhevsk возвращает весь список; не связывать 500 строк с IJK.
        if iata=='IJK':continue
        for n in nodes:
            def val(c):return n.find(c)[0].text() if n.find(c) else 'UNKNOWN'
            days=val('table_days');period=val('table_dates');dates=re.findall(r'\d\d\.\d\d\.\d{4}',period)
            if not dates:dates=re.findall(r'\d\d\.\d\d\.\d{4}',days)
            names=n.find('item-number__name-text');flight=names[0].text() if names else 'UNKNOWN'
            row=dict(source_id=sid,source_row_id=n.attrs.get('id'),source_url=receipts[sid]['url'],source_sha256=receipts[sid]['sha256'],as_of=receipts[sid]['retrieved_at'],origin='KZN',destination=iata,departure_local=val('table_time'),weekdays_or_date=days,flight=flight,shared_flight_names=val('sharing_names'),terminals=val('table_terminal'),valid_from=dates[0] if dates else 'UNKNOWN',valid_to=dates[-1] if dates else 'UNKNOWN',period='W26/27, exact validity in row',unit='published_departure_rule',coverage='airport page departures only; source-specific incomplete; not inventory',status='PUBLISHED_NOT_EXECUTED',arrival_local='UNKNOWN',aircraft='UNKNOWN',open_seats='UNKNOWN',fare_rub='UNKNOWN',baggage='UNKNOWN',booking_lead_days='UNKNOWN; no dated price quote',physical_path='KZN>RMZ>OMS' if iata=='OMS' and flight.startswith('RT') else 'KZN>GOJ>CEK' if iata=='CEK' and flight.startswith('RT') else 'SOURCE_ENDPOINT_NOT_ADMITTED_PHYSICAL')
            row['canonical_row_sha256']=hashlib.sha256(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest();rows.append(row)
    with (ROOT/'local_published_services.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print('published rules',len(rows))
    for dest in sorted(set(r['destination'] for r in rows)):
        rr=[r for r in rows if r['destination']==dest];print(dest,len(rr),sorted(set(r['flight'] for r in rr)))
if __name__=='__main__':parse()
