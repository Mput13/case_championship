#!/usr/bin/env python3
"""Normalize acquired public schedule/subsidy snapshots without network calls."""
import collections, csv, hashlib, html, json, re
from datetime import datetime, date, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'normalized'
MONTHS={'янв':1,'фев':2,'мар':3,'апр':4,'май':5,'июн':6,'июл':7,'авг':8,'сен':9,'окт':10,'ноя':11,'дек':12}
DAYS={'пн':1,'вт':2,'ср':3,'чт':4,'пт':5,'сб':6,'вс':7}
def clean(t): return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>',' ',t))).strip()
def write(name,rows):
    rows=list(rows);fields=list(dict.fromkeys(k for r in rows for k in r))
    with (OUT/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fields,lineterminator='\n');w.writeheader();w.writerows(rows)
    return len(rows)
def read(name):return (ROOT/'raw'/name).read_text(encoding='utf-8',errors='replace')
def cells(tr):return [(a,clean(v)) for a,v in re.findall(r'<t[dh]\b([^>]*)>(.*?)</t[dh]>',tr,re.S|re.I)]
def grid(table):
    """Expand only explicit HTML rowspans; blank cells remain blank."""
    active={};out=[]
    for ix,tr in enumerate(re.findall(r'<tr\b[^>]*>(.*?)</tr>',table,re.S|re.I),1):
        row={};inherited={}
        for col,(left,value,origin) in list(active.items()):
            row[col]=value;inherited[col]=origin
            if left<=1:del active[col]
            else:active[col]=(left-1,value,origin)
        col=0
        for attrs,value in cells(tr):
            while col in row:col+=1
            span=int(re.search(r'rowspan=[\'\"]?(\d+)',attrs,re.I).group(1)) if re.search(r'rowspan=[\'\"]?(\d+)',attrs,re.I) else 1
            cspan=int(re.search(r'colspan=[\'\"]?(\d+)',attrs,re.I).group(1)) if re.search(r'colspan=[\'\"]?(\d+)',attrs,re.I) else 1
            row[col]=value
            if span>1:active[col]=(span-1,value,ix)
            for c in range(1,cspan):row[col+c]=''
            col+=cspan
        out.append((ix,[row[i] for i in range(max(row)+1)] if row else [],inherited))
    return out
def uvt():
    p=read('uvt_schedule_current.html');rows=[];rejected=[];raw_count=0
    for block in p.split('<div class="ras__item">')[1:]:
        m=re.search(r'Из города\s+([^<]+)',block)
        if not m:continue
        origin=clean(m.group(1))
        table=re.search(r'<table\b.*?</table>',block,re.S)
        if not table:continue
        for ix,rr,inherit in grid(table.group(0)):
            if not rr or rr[0]=='Аэропорт назначения':continue
            raw_count+=1
            if len(rr)!=12:rejected.append(dict(origin=origin,source_table_row=ix,cells=json.dumps(rr,ensure_ascii=False),reason='Unexpected width'));continue
            dest,period,carrier,f1,dep1,arr1,days1,typ,f2,dep2,arr2,days2=rr
            dates=re.findall(r'\d{2}\.\d{2}\.\d{2}',period)
            start=datetime.strptime(dates[0],'%d.%m.%y').date().isoformat() if len(dates)>=1 else None
            end=datetime.strptime(dates[-1],'%d.%m.%y').date().isoformat() if len(dates)>=1 else None
            for a,b,f,dep,arr,days,direction in [(origin,dest,f1,dep1,arr1,days1,'outbound column'),(dest,origin,f2,dep2,arr2,days2,'return column')]:
                if f in ('-',''):continue
                weekdays=sorted(DAYS[k] for k in re.findall(r'пн|вт|ср|чт|пт|сб|вс',days.lower()))
                rows.append(dict(source_dataset_id='uvt_schedule_current',source_table_origin=origin,source_table_row=ix,source_direction=direction,carrier='ЮВТ Аэро',carrier_iata='RT',origin_city_raw=a,destination_city_raw=b,flight_number_raw=f,flight_number_normalized=re.sub(r'.*?RT\)\s*-?','RT-',f).replace(' ',''),aircraft_type_raw=typ,validity_raw=period,valid_from=start,valid_to=end,weekdays_raw=days,weekdays_iso=';'.join(map(str,weekdays)),published_departures_per_week_rule=len(set(weekdays)) if weekdays else None,frequency_unit='departures per direction per full week inside rule validity',departure_local_raw=dep,arrival_local_raw=arr,time_basis='local at each airport, explicitly stated by publisher',nonstop_status='UNKNOWN; endpoint tables may include intermediate stops',value_status='OBSERVED_PUBLISHED_SCHEDULE',executed_status='UNKNOWN',structural_inheritance=json.dumps(inherit)))
    unique={};dups=[]
    for r in rows:
        key=tuple(r[k] for k in ['origin_city_raw','destination_city_raw','flight_number_raw','valid_from','valid_to','weekdays_iso','departure_local_raw','arrival_local_raw'])
        if key in unique:dups.append(dict(**r,duplicate_of_source_table_origin=unique[key]['source_table_origin'],duplicate_of_row=unique[key]['source_table_row']))
        else:unique[key]=r
    write('uvt_schedule_rules_all.csv',rows);write('uvt_schedule_rules_unique.csv',unique.values());write('uvt_mirrored_rules.csv',dups)
    if rejected:write('uvt_rejected_rows.csv',rejected)
    return dict(source_rows=raw_count,directional_rows=len(rows),unique_directional_rules=len(unique),mirrored_duplicates=len(dups),rejected=len(rejected))
def subsidy():
    p=read('favt_regional_2026.html');table=re.search(r'<table\b.*?</table>',p,re.S).group(0)
    rows=[];bad=[]
    for ix,rr,inh in grid(table):
        if ix==1:continue
        if len(rr)!=11:bad.append(dict(source_row=ix,width=len(rr),cells=json.dumps(rr,ensure_ascii=False)));continue
        no,carrier,a,b,distance,typ,seats,period,freq,pairs,note=rr
        rows.append(dict(source_dataset_id='favt_regional_2026',source_row=ix,route_number_raw=no,carrier_raw=carrier,origin_airport_name_raw=a,destination_airport_name_raw=b,distance_oneway_km_raw=distance,aircraft_type_raw=typ,seats_raw=seats,period_raw=period,frequency_per_week_raw=freq,paired_flights_2026_raw=pairs,note_raw=note,source_status='PARSED',value_status='OBSERVED_PROGRAMME_PLAN',actual_operated_flights=None,subsidy_award_RUB=None,subsidy_paid_RUB=None,structural_inheritance=json.dumps(inh),limitations='Programme-listed route/plan, not actual schedule, awarded cash, payment or observed passenger demand; frequency convention must be confirmed against programme rules'))
    write('favt_subsidy_2026_full.csv',rows)
    if bad:write('favt_subsidy_rejected.csv',bad)
    return dict(rows=len(rows),numbered_routes=len(set(r['route_number_raw'] for r in rows)),carriers=len(set(r['carrier_raw'] for r in rows)),airport_names=len(set(r[k] for r in rows for k in ['origin_airport_name_raw','destination_airport_name_raw'])),rowspan_expanded_rows=sum(r['structural_inheritance']!='{}' for r in rows),rejected=len(bad))
def iraero():
    rows=[]
    for sourcefile in sorted((ROOT/'raw').glob('iraero_*.html')):
      p=read(sourcefile.name)
      for ix,block in enumerate(re.split(r'<div class="swiper-slide flight-row[^\"]*">',p)[1:],1):
        def find(pattern):
            m=re.search(pattern,block,re.S);return clean(m.group(1)) if m else None
        a=find(r'name="origin-city-code\[0\]" value="([^"]+)"')
        b=find(r'name="destination-city-code\[0\]" value="([^"]+)"')
        d=find(r'name="date\[0\]" value="([^"]+)"')
        if not all((a,b,d)):continue
        f=find(r'<div class="grey-small">(IO-[^<]+)</div>')
        arrival_dates=re.findall(r'<div class="date-mobile">([^<]+)</div>',block)
        rows.append(dict(source_dataset_id=sourcefile.stem,source_row=ix,carrier='ИрАэро',carrier_iata='IO',origin_code_raw=a,destination_code_raw=b,flight_number_raw=f,departure_date=datetime.strptime(d,'%d.%m.%Y').date().isoformat(),departure_local=find(r'class="big time-departure">([^<]+)'),arrival_local=find(r'class="big time-arrival">([^<]+)'),arrival_date_label=arrival_dates[1] if len(arrival_dates)>1 else None,displayed_duration_raw=find(r'class="fly-time">\s*([^<]+)'),aircraft_type_raw=find(r'fly-info-number[^>]*>\s*<span>([^<]+)'),nonstop_status='UNKNOWN; same flight number is offered for several endpoints and can include stops',value_status='OBSERVED_PUBLISHED_ITINERARY',executed_status='UNKNOWN',time_basis='UNKNOWN clock basis; local-named columns retain displayed clock strings only; no UTC inference',limitations='Origin-filtered endpoint itinerary listing, not a nonstop segment inventory. Displayed flight duration has inconsistencies and is not used as block time. Clock basis was not explicitly established in saved page.'))
    write('iraero_published_itineraries.csv',rows)
    group=collections.defaultdict(set)
    for r in rows:group[(r['departure_date'],r['origin_code_raw'],r['flight_number_raw'])].add(r['destination_code_raw'])
    return dict(rows=len(rows),source_snapshots=len(set(r['source_dataset_id'] for r in rows)),origin_codes=sorted(set(r['origin_code_raw'] for r in rows)),dates=sorted(set(r['departure_date'] for r in rows)),endpoint_pairs=len(set((r['origin_code_raw'],r['destination_code_raw']) for r in rows)),flight_origin_dates_with_multiple_endpoints=sum(len(v)>1 for v in group.values()),self_endpoint_rows=sum(r['origin_code_raw']==r['destination_code_raw'] for r in rows),non_latin_code_rows=sum(not re.fullmatch('[A-Z]{3}',r['destination_code_raw']) for r in rows))
def azimuth():
    p=read('azimuth_board.html');rows=[]
    blocks=re.findall(r'<div class="flight day-(\d+)">(.*?)(?=<div class="flight day-\d+">|<div class="no-flights|</section>|\Z)',p,re.S)
    for ix,(day_class,b) in enumerate(blocks,1):
        def cls(name,until=None):
            pattern=r'<div class="'+name+r'"[^>]*>(.*?)(?='+until+r')' if until else r'<div class="'+name+r'"[^>]*>(.*?)</div>'
            m=re.search(pattern,b,re.S);return clean(m.group(1)) if m else None
        number=cls('flight_number')
        if not number:continue
        a=cls('departure_ap_name',r'<div class="departure_time">');dest=cls('arrival_ap_name',r'<div class="arrival_time">')
        dep=cls('departure_time',r'<div class="arrow">');arr=cls('arrival_time',r'<div class="flight_status"')
        status=cls('flight_status')
        def stamp(t,label):
            m=re.search(label+r':\s*(\d\d:\d\d),?\s*(\d{1,2})\s+(\w+)',t or '')
            if m:return f'2026-{MONTHS[m.group(3)[:3]]:02d}-{int(m.group(2)):02d}T{m.group(1)}'
            m=re.search(label+r':\s*(\d\d:\d\d)',t or '')
            if m:return f'2026-11-{7+int(day_class):02d}T{m.group(1)}'
            return None
        rows.append(dict(source_dataset_id='azimuth_board',source_row=ix,source_day_class=day_class,carrier='Азимут',carrier_iata='A4',flight_number_raw=number,flight_number_normalized=number.replace('А','A'),origin_name_raw=a,destination_name_raw=dest,departure_planned_local=stamp(dep,'План'),departure_actual_reported_local=stamp(dep,'Факт'),arrival_planned_local=stamp(arr,'План'),arrival_actual_reported_local=stamp(arr,'Факт'),departure_display_raw=dep,arrival_display_raw=arr,flight_status_reported=status,value_status='OBSERVED_CARRIER_BOARD',operation_evidence='carrier reports arrival' if status=='Прибыл' else 'status as published',year_status='DERIVED from snapshot year2026 and visible day labels; omitted today dates use day class2=9Nov',time_basis='clock basis to verify; preserve published local strings; no UTC inference',nonstop_status='board endpoint segment; intermediate stops not independently excluded',limitations='Finite 8-10Nov snapshot; neither monthly frequency nor complete reliability distribution. Actual timestamps are carrier reported and not ADS-B observations.'))
    write('azimuth_flight_instances.csv',rows)
    return dict(rows=len(rows),reported_arrived=sum(r['flight_status_reported']=='Прибыл' for r in rows),reported_statuses=dict(collections.Counter(r['flight_status_reported'] for r in rows)),date_labels=sorted(set((r['departure_planned_local'] or '')[:10] for r in rows)))
def svx():
    p=read('svx_schedule.html');table=re.search(r'<table\b.*?</table>',p,re.S).group(0);city=None;rows=[]
    for ix,tr in enumerate(re.findall(r'<tr\b[^>]*>(.*?)</tr>',table,re.S|re.I),1):
        rr=[v for _,v in cells(tr)]
        if len(rr)==1:city=rr[0]
        elif len(rr)==8 and rr[0]!='Отправление':
            dep,arr,days,period,carrier,f,typ,ap=rr
            weekdays=sorted(set(DAYS[k] for k in re.findall(r'пн|вт|ср|чт|пт|сб|вс',days.lower())))
            rows.append(dict(source_dataset_id='svx_schedule',source_table_row=ix,origin_airport_iata='SVX',destination_airport_iata=ap,destination_city_raw=city,carrier_raw=carrier,flight_number_raw=f,departure_local_raw=dep,arrival_local_raw=arr,weekdays_raw=days,weekdays_iso=';'.join(map(str,weekdays)),published_departures_per_week_rule=len(weekdays),validity_raw=period,validity_year='UNKNOWN in row; do not silently infer across year',aircraft_type_raw=typ,value_status='OBSERVED_PUBLISHED_SCHEDULE',operating_carrier_status='publisher airline label; marketing/operating distinction may need confirmation',nonstop_status='airport endpoint schedule; verify operating flight before capacity aggregation',time_basis='local at each city, explicitly stated by publisher',executed_status='UNKNOWN'))
    write('svx_published_schedule_rules.csv',rows)
    return dict(rows=len(rows),airport_codes=len(set(r['destination_airport_iata'] for r in rows)),carrier_labels=len(set(r['carrier_raw'] for r in rows)),rw_rows=sum(r['carrier_raw']=='RED WINGS' for r in rows))
def main():
    OUT.mkdir(exist_ok=True);summary={k:f() for k,f in [('uvt',uvt),('subsidy',subsidy),('iraero',iraero),('azimuth',azimuth),('svx',svx)]}
    # Status axis is fixed by the research contract; publisher semantics are separate.
    for filename in ['uvt_schedule_rules_all.csv','uvt_schedule_rules_unique.csv','uvt_mirrored_rules.csv','favt_subsidy_2026_full.csv','iraero_published_itineraries.csv','azimuth_flight_instances.csv','svx_published_schedule_rules.csv']:
        with (OUT/filename).open(encoding='utf-8',newline='') as f: rr=list(csv.DictReader(f))
        for r in rr:
            r['observation_kind']=r['value_status'];r['value_status']='OBSERVED'
        write(filename,rr)
    summary['collector_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    summary['limitations']=['All values retain their publisher meaning. Programme support, timetable offer and carrier-reported operation are distinct.','No observed passenger OD, realised fares, available fleet or RW negotiated cost was acquired.']
    (OUT/'parse_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
