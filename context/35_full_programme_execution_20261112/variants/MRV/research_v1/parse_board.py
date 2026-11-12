import re,csv,json,hashlib
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class Flights(HTMLParser):
    def __init__(self):super().__init__();self.stack=[];self.current=None;self.depth=None;self.rows=[]
    def handle_starttag(self,t,attrs):
        a=dict(attrs);cls=a.get('class','').split()
        if t=='div' and 'flight' in cls:
            self.current={'day_class':next(x for x in cls if x.startswith('day-'))};self.depth=len(self.stack)
        self.stack.append((t,cls))
        if t in ['br','hr','img','input','meta','link','source','wbr']:self.stack.pop()
    def handle_endtag(self,t):
        if not self.stack:return
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==t:
                if self.current is not None and i==self.depth:
                    self.rows.append(self.current);self.current=None;self.depth=None
                del self.stack[i:];break
    def handle_data(self,s):
        if self.current is None or not s.strip():return
        for _,cls in reversed(self.stack):
            keys=set(cls)&{'flight_number','departure_ap_name','departure_time','arrival_ap_name','arrival_time','flight_status'}
            if keys:
                k=next(iter(keys));self.current[k]=self.current.get(k,'')+' '+s.strip();break
p=Flights();p.feed((ROOT/'sources/AZ_BOARD.html').read_text())
mapping={'Минеральные Воды':'MRV','Самара':'KUF','Пермь':'PEE','Сургут':'SGC','Чебоксары':'CSY','Ереван':'EVN','Тбилиси':'TBS','Сочи':'AER','Уфа':'UFA','Челябинск':'CEK','Омск':'OMS','Киров':'KVX','Тюмень':'TJM','Нижний Новгород':'GOJ','Москва (Внуково)':'VKO','Санкт-Петербург':'LED','Махачкала':'MCX','Нижнекамск':'NBC','Пенза':'PEZ','Ижевск':'IJK','Нижневартовск':'NJC','Ханты-Мансийск':'HMA','Ташкент':'TAS','Стамбул':'IST','Алматы':'ALA','Красноярск':'KJA','Краснодар':'KRR'}
daymap={'day-1':'2026-11-11','day-2':'2026-11-12','day-3':'2026-11-13'}
out=[]
for n,row in enumerate(p.rows,1):
    row={k:v.strip() for k,v in row.items()}
    if 'Минеральные Воды' not in (row.get('departure_ap_name'),row.get('arrival_ap_name')):continue
    d={'source_id':'AZ_BOARD','source_row_id':f'AZ_BOARD-flight-{n:03}','source_row_sha256':hashlib.sha256(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'board_group_date':daymap.get(row['day_class'],'UNKNOWN'),'origin':mapping.get(row.get('departure_ap_name'),'UNKNOWN'),'destination':mapping.get(row.get('arrival_ap_name'),'UNKNOWN'),**row,'unit':'dated_published_flight;local_clock','period':'board_groups_2026-11-11..13;local_departures_may_cross_date','as_of':'2026-11-12','coverage':'Одна официальная трёхдневная доска A4, только MRV; не полный рынок/не 2027–2028/не продажи','status':'PUBLISHED_OR_REPORTED_BOARD_ONLY','source_url':'https://azimuth.ru/ru/schedule?date=2026-11-13','assumption_id':'A-MRV-BOARD-DATE'}
    for field in ['departure_time','arrival_time']:
        m=re.search(r'План:\s*(\d{2}:\d{2})',d.get(field,''));d[field+'_planned']=m.group(1) if m else 'UNKNOWN'
        m=re.search(r'План:\s*\d{2}:\d{2},\s*(\d+) нояб\.',d.get(field,''))
        d[field+'_date']=f'2026-11-{int(m.group(1)):02}' if m else (daymap[row['day_class']] if row['day_class']=='day-2' else 'UNKNOWN')
        d[field+'_date_basis']='explicit_local_day_month_with_asof_year' if m else ('today_board_group_current_date' if row['day_class']=='day-2' else 'UNKNOWN')
    d['departure_date']=d['departure_time_date']
    out.append(d)
fields=list(dict.fromkeys(k for r in out for k in r))
with (ROOT/'local_dated_competitors.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(out)
print(json.dumps({'total_source_flight_blocks':len(p.rows),'mrv_rows':len(out),'row_date_overrides_board_group':sum(r['departure_date']!=r['board_group_date'] for r in out),'local_dates':sorted(set(r['departure_date'] for r in out)),'selected_13Nov':[{k:r[k] for k in ['source_row_id','origin','destination','flight_number','departure_date','departure_time_planned','arrival_time_planned']} for r in out if r['departure_date']=='2026-11-13' and ({r['origin'],r['destination']}&{'KUF','PEE','GOJ','KVX','TBS','EVN'})]},ensure_ascii=False))
