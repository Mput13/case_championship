#!/usr/bin/env python3
"""Reproduce airport-published C14 rules; expand calendar, never performed flights.

Only Python stdlib. Raw HTML held locally; publish factual cells and byte receipt.
"""
import csv
import datetime as dt
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
VERSION='c14-flight-v1'
VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}

class Node:
    def __init__(self,tag='',attrs=()):self.tag=tag;self.attrs=dict(attrs);self.children=[]
    def text(self):return ' '.join((' '.join(c.text() if isinstance(c,Node) else c for c in self.children)).split())
    def all(self,predicate):
        out=[self] if predicate(self) else []
        for c in self.children:
            if isinstance(c,Node):out.extend(c.all(predicate))
        return out
    def cls(self,name):return name in self.attrs.get('class','').split()

class DOM(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.root=Node();self.stack=[self.root]
    def handle_starttag(self,tag,attrs):
        n=Node(tag,attrs);self.stack[-1].children.append(n)
        if tag not in VOID:self.stack.append(n)
    def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs);self.handle_endtag(tag)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:self.stack=self.stack[:i];break
    def handle_data(self,text):self.stack[-1].children.append(text)

def write(name,rows):
    p=ROOT/'normalized'/name;p.parent.mkdir(exist_ok=True)
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def run():
    rec=json.loads((ROOT/'receipts/kvx_timetable_20261109.json').read_text());raw=ROOT/rec['raw_path']
    assert hashlib.sha256(raw.read_bytes()).hexdigest()==rec['sha256']
    parser=DOM();parser.feed(raw.read_text(encoding='utf-8'))
    full=parser.root.text();assert 'в расписании указано местное время аэропортов прилета/вылета' in full
    rules=[];evidence=[]
    aliases={'Минеральные воды':('MRV','OA:6514','URMM','Europe/Moscow'),'Киров':('KVX','OA:42945','USKK','Europe/Kirov')}
    day_names={'Пн':1,'Вт':2,'Ср':3,'Чт':4,'Пт':5,'Сб':6,'Вс':7}
    blocks=parser.root.all(lambda n:n.cls('result__block'))
    for ordinal,block in enumerate(blocks,1):
        nums=block.all(lambda n:n.cls('result__list__raic-name'))
        if not nums:continue
        flight=nums[0].text().replace('А','A').replace(' ','')
        if flight not in {'A46013','A46014'}:continue
        dest=block.all(lambda n:n.cls('destination_type'))
        assert len(dest)==2
        # Publisher embeds divs inside spans and void SVG image tags. Read the
        # labelled block text, keeping direction and both clocks in one match.
        journey=re.search(r'Направление (\d{2}:\d{2}) (.*?) (\d{2}:\d{2}) (.*?) Аэропорт прилета',block.text())
        assert journey, f'Missing labelled journey at block{ordinal}'
        cities=[journey[2],journey[4]];times=[journey[1],journey[3]]
        dates=re.findall(r'\d{2}\.\d{2}\.\d{4}',block.all(lambda n:n.cls('result__list_period'))[0].text())
        days=block.all(lambda n:n.cls('result__list_days'))[0].text().replace('Дни','').strip()
        period=[dt.datetime.strptime(d,'%d.%m.%Y').date().isoformat() for d in dates]
        day=day_names[days]
        a,b=[aliases[x] for x in cities]
        offset=int(times[1]<=times[0])
        identity={'flight':flight,'from':a[0],'to':b[0],'start':period[0],'end':period[1],
                  'weekday':day,'dep':times[0],'arr':times[1],'offset':offset,'zones':[a[3],b[3]]}
        rid='C14-R-'+hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:14]
        rules.append({'rule_id':rid,'operating_carrier_id':'RU_AZIMUTH','operating_carrier_iata':'A4',
            'carrier_status':'PUBLISHED_AIRLINE_ASSOCIATION; ACTUAL_OPERATOR_NOT_VERIFIED',
            'marketing_carrier_iata':'A4','flight_number':flight,'source_flight_number':nums[0].text(),
            'origin_iata':a[0],'origin_airport_id':a[1],'origin_icao':a[2],'destination_iata':b[0],
            'destination_airport_id':b[1],'destination_icao':b[2],'origin_name_source':cities[0],
            'destination_name_source':cities[1],'departure_local_time':times[0],'arrival_local_time':times[1],
            'arrival_day_offset':offset,'day_offset_status':'DERIVED_CLOCK_ROLLOVER_ASSUMES_LESS_THAN24H',
            'origin_iana':a[3],'destination_iana':b[3],'clock_basis':'AIRPORT_PUBLISHED_LOCAL_TIME',
            'timezone_mapping_status':'CURATED_AREA_IANA; published core KVX Europe/Moscow differs by name, agrees offset in2026',
            'valid_from':period[0],'valid_to':period[1],'weekdays_iso':day,'exceptions':'UNKNOWN_NOT_LISTED',
            'intermediate_stops':None,'stop_pattern_status':'UNKNOWN_NOT_STATED_IN_RULE',
            'source_status':'PARSED','value_status':'OBSERVED;day_offset_and_zone_mapping_DERIVED',
            'scope_status':'ADVERTISED_SCHEDULE_NOT_OPERATIONAL_GUARANTEE','source_snapshot':rec['snapshot_id'],
            'source_sha256':rec['sha256'],'source_url':rec['source_url'],'observed_at_utc':rec['retrieved_at_utc'],
            'source_locator':f'div.result__block occurrence{ordinal}; destination_type/period/days',
            'recipe_version':VERSION})
        evidence.append({'rule_id':rid,'block_ordinal':ordinal,'source_flight_number':nums[0].text(),
                         'departure_display':times[0]+' '+cities[0],'arrival_display':times[1]+' '+cities[1],
                         'period_display':block.all(lambda n:n.cls('result__list_period'))[0].text(),
                         'days_display':days,'source_sha256':rec['sha256']})
    assert len(rules)==len({r['rule_id'] for r in rules})==6
    write('flight_rules.csv',rules);write('flight_rule_cells.csv',evidence)
    instances=[];date=dt.date(2026,12,7)
    while date<=dt.date(2026,12,27):
        for r in rules:
            if date.isoweekday()!=r['weekdays_iso'] or not(r['valid_from']<=date.isoformat()<=r['valid_to']):continue
            departure=dt.datetime.fromisoformat(date.isoformat()+'T'+r['departure_local_time']).replace(tzinfo=ZoneInfo(r['origin_iana']))
            arrival_date=date+dt.timedelta(days=r['arrival_day_offset'])
            arrival=dt.datetime.fromisoformat(arrival_date.isoformat()+'T'+r['arrival_local_time']).replace(tzinfo=ZoneInfo(r['destination_iana']))
            minutes=int((arrival.astimezone(dt.timezone.utc)-departure.astimezone(dt.timezone.utc)).total_seconds()/60)
            assert 0<minutes<1440
            instances.append({'instance_id':r['rule_id']+':'+date.isoformat(),'rule_id':r['rule_id'],
                'flight_number':r['flight_number'],'origin_iata':r['origin_iata'],'destination_iata':r['destination_iata'],
                'departure_local_date':date.isoformat(),'departure_local_datetime':departure.isoformat(),
                'arrival_local_date':arrival_date.isoformat(),'arrival_local_datetime':arrival.isoformat(),
                'departure_utc':departure.astimezone(dt.timezone.utc).isoformat(),'arrival_utc':arrival.astimezone(dt.timezone.utc).isoformat(),
                'origin_iana':r['origin_iana'],'destination_iana':r['destination_iana'],'arrival_day_offset':r['arrival_day_offset'],
                'planned_duration_minutes':minutes,'instance_status':'PLANNED_FROM_ADVERTISED_RULE',
                'performed_status':'UNKNOWN','inventory_status':'UNKNOWN','value_status':'DERIVED',
                'source_sha256':r['source_sha256'],'recipe_version':VERSION})
        date+=dt.timedelta(days=1)
    write('dated_flights.csv',instances)
    checks={'recipe_version':VERSION,'rules':len(rules),'dated_instances':len(instances),
        'outbound_window_instances':[{k:r[k] for k in ['instance_id','departure_local_date','arrival_local_date','departure_local_datetime','arrival_local_datetime']} for r in instances if r['origin_iata']=='KVX' and r['departure_local_date']<='2026-12-13'],
        'clock_basis_evidence':'Official footer explicitly says airport-local times',
        'source_warning':'Official footer calls schedule advertising; changes possible',
        'conflict':'EarlierSA02/secondaryMonFri disagrees with current airportMonThu; versions retained, not combined',
        'no_performed_claim':True,'no_quote_or_inventory_claim':True,'stop_pattern':'UNKNOWN',
        'local_raw_sha256':rec['sha256'],'local_raw_is_public_git_input':False}
    (ROOT/'normalized/flight_validation.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(checks,ensure_ascii=False))

if __name__=='__main__':run()
