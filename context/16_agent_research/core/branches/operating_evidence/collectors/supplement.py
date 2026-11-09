#!/usr/bin/env python3
"""Selected, visually checked tariff rows and faithful Omsk schedule extraction."""
import collections,csv,hashlib,json,re,subprocess
from datetime import date,datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from normalize import write,OUT,ROOT

def omsk():
    src=ROOT/'raw/omsk_winter_20261105.pdf';dest=OUT/'omsk_winter_20261105.txt'
    subprocess.run(['pdftotext','-layout',str(src),str(dest)],check=True)
    domestic=dest.read_text().split('МЕЖДУНАРОДНЫЕ РЕЙСЫ')[0];rows=[];exceptions=[]
    for ix,line in enumerate(domestic.splitlines(),1):
        if 'Омск' not in line or not re.search(r'\d{2}\.\d{2}\.\d{2,4}',line):continue
        cc=re.split(r'\s{2,}',line.strip())
        if len(cc)!=10:
            exceptions.append(dict(source_line=ix,raw_line=line,reason='Single-leg exception or unexpected columns; retained, not turned into a roundtrip'))
            continue
        typ,fno,from_dep,routing,oms_arr,oms_dep,days,period,carrier,to_arr=cc
        rows.append(dict(source_dataset_id='omsk_winter_2026',source_text_line=ix,source_pdf_page=1+domestic[:domestic.find(line)].count('\f'),aircraft_type_raw=typ,flight_numbers_raw=fno,routing_raw=routing,preceding_origin_departure_local_raw=from_dep,omsk_arrival_local_raw=oms_arr,omsk_departure_local_raw=oms_dep,onward_arrival_local_raw=to_arr,weekdays_raw=days,period_raw=period,carrier_raw=carrier,time_basis='local time, explicitly stated in PDF',date_basis='weekdays/period in airport schedule; remote-origin departure can fall on preceding date, verify before expansion',value_status='OBSERVED',observation_kind='PUBLISHED_AIRPORT_TIMETABLE',executed_status='UNKNOWN',limitations='Two-leg/through-flight rule, not OD demand. Preserve full routing including Tobolsk. No automatic IATA transliteration of Cyrillic carrier aliases.'))
    write('omsk_domestic_timetable_rows.csv',rows);write('omsk_domestic_timetable_exceptions.csv',exceptions)
    return dict(domestic_rows=len(rows),exceptions=len(exceptions),carriers=len(set(r['carrier_raw'] for r in rows)))
def uvt_week():
    with (OUT/'uvt_schedule_rules_unique.csv').open() as f:rules=list(csv.DictReader(f))
    by={};conflicts=[]
    for r in rules:
        if not r['valid_from'] or not r['valid_to'] or not r['weekdays_iso']:continue
        days=set(map(int,r['weekdays_iso'].split(';')))
        for offset in range(7):
            dt=date(2026,12,7)+timedelta(days=offset)
            if r['valid_from']<=dt.isoformat()<=r['valid_to'] and dt.isoweekday() in days:
                k=(r['origin_city_raw'],r['destination_city_raw'],r['flight_number_normalized'],dt.isoformat(),r['departure_local_raw'])
                obs=dict(origin_city_raw=k[0],destination_city_raw=k[1],flight_number=k[2],departure_local_date=k[3],departure_local_raw=k[4],arrival_local_raw=r['arrival_local_raw'],source_table_origin=r['source_table_origin'],source_table_row=r['source_table_row'],nonstop_status=r['nonstop_status'],value_status='DERIVED',method='Calendar expansion of explicit validity dates and weekdays; mirrored representations deduplicated by directed flight/date/departure')
                if k in by and by[k]['arrival_local_raw']!=obs['arrival_local_raw']:
                    by[k]['calendar_conflict']='HOLD arrival-time conflict in source'
                    by[k]['arrival_local_raw']=None
                    conflicts.append(obs)
                else:by[k]=obs
    write('uvt_published_endpoint_week_20261207.csv',by.values())
    if conflicts:write('uvt_calendar_conflicts.csv',conflicts)
    return dict(endpoint_date_rows=len(by),arrival_time_conflicts=len(conflicts),nonstop_departure_total='UNKNOWN; endpoint offers include through flights')
def omsk_week():
    """Only the OMS departure leg has an unambiguous airport-local operating date."""
    key_source=ROOT.parents[1]/'canonical_keys.csv';snapshot=ROOT/'raw/parent_canonical_keys_snapshot.csv'
    if not snapshot.exists():snapshot.write_bytes(key_source.read_bytes())
    with snapshot.open() as f:allkeys=list(csv.DictReader(f))
    bycode=collections.defaultdict(list)
    for r in allkeys:
        if r['entity_type']=='airport' and r['relation']=='identity' and r['iata']:bycode[r['iata']].append(r)
    aliases={'Домодедово':'DME','Шереметьево':'SVO','Екатеринбург':'SVX','Иркутск':'IKT','Казань':'KZN','Краснодар':'KRR','Красноярск':'KJA','Минеральные Воды':'MRV','Надым':'NYM','Нижневартовск':'NJC','Новосибирск':'OVB','Новый Уренгой':'NUX','Норильск':'NSK','Ноябрьск':'NOJ','Омск':'OMS','Салехард':'SLY','Санкт-Петербург':'LED','Сочи':'AER','Сургут':'SGC','Тобольск':'TOX','Ханты-Мансийск':'HMA'}
    def resolve(name):
        code=aliases.get(name);rr=bycode[code]
        return code,rr[0]['canonical_id'] if len(rr)==1 else None,rr[0]['iana_timezone'] if len(rr)==1 else None
    with (OUT/'omsk_domestic_timetable_rows.csv').open() as f:rules=list(csv.DictReader(f))
    rows=[]
    for r in rules:
        dates=re.findall(r'\d{2}\.\d{2}\.\d{2}(?:\d{2})?',r['period_raw'])
        def dparse(s):return datetime.strptime(s,'%d.%m.%Y' if len(s)==10 else '%d.%m.%y').date()
        if not dates:continue
        start,end=dparse(dates[0]),dparse(dates[-1])
        weekdays=set(range(1,8)) if r['weekdays_raw']=='ежедневно' else set(map(int,re.findall('[1-7]',r['weekdays_raw'])))
        routing=re.split(' – | - ',r['routing_raw']);ix=routing.index('Омск')
        dest=routing[ix+1] if ix+1<len(routing) else None
        if not dest:continue
        code,key,tz=resolve(dest);_,okey,otz=resolve('Омск')
        nums=re.findall(r'\d+',r['flight_numbers_raw']);outnum=nums[-1]
        for i in range(7):
            dt=date(2026,12,7)+timedelta(days=i)
            if not (start<=dt<=end and dt.isoweekday() in weekdays):continue
            dep=datetime.fromisoformat(dt.isoformat()+'T'+r['omsk_departure_local_raw'].replace('.',':')).replace(tzinfo=ZoneInfo(otz))
            rows.append(dict(source_dataset_id='omsk_winter_2026',source_text_line=r['source_text_line'],carrier_raw=r['carrier_raw'],flight_numbers_source=r['flight_numbers_raw'],outbound_flight_numeric=outnum,origin_airport_iata='OMS',destination_airport_iata=code,origin_airport_key=okey,destination_airport_key=key,origin_iana_timezone=otz,destination_iana_timezone=tz,departure_date_local=dt.isoformat(),departure_local=dep.isoformat(),departure_utc=dep.astimezone(ZoneInfo('UTC')).isoformat(),published_onward_arrival_local_raw=r['onward_arrival_local_raw'],full_routing_raw=r['routing_raw'],endpoint_last_city=routing[-1],next_airport_name=dest,nonstop_status='published next leg in explicit routing; no execution proof',value_status='DERIVED',method='Explicit OMS weekdays/period × dates 7-13Dec; next stop from full routing; exact IATA alias then parent canonical registry; UTC from zoneinfo',limitations='Source carrier labels not fully resolved marketing/operating; capacity and block hours not inferred. Arrival date not inferred. OMS dates cannot be reused as remote-origin departure dates.'))
    unique={}
    for r in rows:
        k=tuple(r[x] for x in ['carrier_raw','outbound_flight_numeric','destination_airport_iata','departure_local'])
        if k in unique:raise ValueError('Duplicate same carrier/flight/airport/date: '+str(k))
        unique[k]=r
    write('omsk_outbound_week_20261207.csv',rows)
    counts=collections.Counter((r['carrier_raw'],r['destination_airport_iata']) for r in rows)
    write('omsk_outbound_frequency_20261207.csv',[dict(carrier_raw=c,origin_airport_iata='OMS',destination_airport_iata=d,week='2026-12-07/13',published_departures=n,frequency_unit='OMS departures in this one direction in target week',value_status='DERIVED',source_dataset_id='omsk_winter_2026',limitations='Published offered flights, not flown demand or capacity; no null-as-zero absence inference') for (c,d),n in sorted(counts.items())])
    (OUT/'canonical_dependency.json').write_text(json.dumps(dict(snapshot_path='raw/parent_canonical_keys_snapshot.csv',parent_path=str(key_source),sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),limitations='Parent assembled OurAirports/Travelpayouts directory; IATA aliases for named airports manually resolved; not official state certification'),ensure_ascii=False,indent=2)+'\n')
    return dict(directional_departure_instances=len(rows),carrier_destination_groups=len(counts),missing_airport_keys=sum(not r['destination_airport_key'] for r in rows),missing_timezones=sum(not r['destination_iana_timezone'] for r in rows))
def costs():
    # Each selected numeric row was read in its complete rendered page, not OCR.
    vals=[]
    def add(source,airport,effective,page,item,value,unit,scope,notes):
        vals.append(dict(source_dataset_id=source,airport_iata=airport,effective_from=effective,known_on='2026-11-09',pdf_page=page,item=item,value=value,unit=unit,VAT_basis='published excluding VAT / VAT added if applicable; legal applicability not inferred',scope=scope,value_status='OBSERVED',source_status='VALIDATED',validation_scope='SELECTED_VISUALLY_CHECKED_ROW; not full document or RW paid basket',method='Manual transcription from rendered PDF, visually reviewed 2026-11-09',limitations=notes+'; public tariff, not RW negotiated contract or full paid basket'))
    common='Read footnotes and service package overlap before applying'
    for item,v,u,scope in [('takeoff_landing',553,'RUB/t MTOW','airport fee'),('transport_security',499,'RUB/t MTOW','airport fee'),('terminal_domestic',70.5,'RUB/passenger','domestic'),('terminal_international',102,'RUB/passenger','international'),('passenger_service_domestic',268,'RUB/passenger','domestic'),('passenger_service_domestic_excluding_baggage',264.5,'RUB/passenger','alternative package, not additive'),('passenger_service_domestic_excluding_checkin_baggage',261,'RUB/passenger','alternative package, not additive'),('passenger_service_international',452,'RUB/passenger','international'),('stairs_boarding',9650,'RUB/stairs operation','boarding'),('stairs_disembarkation',9650,'RUB/stairs operation','disembarkation'),('stairs_both',19300,'RUB/stairs operation','alternative combined package, not additive'),('bus',8100,'RUB/vehicle','passenger transport'),('fuel_uplift',1696,'RUB/t fuel','fuel service'),('fuel_storage',1353,'RUB/t fuel','fuel service'),('temporary_parking_SSJ',685,'RUB/hour','Sukhoi Superjet aircraft type group')]:
        add('ufa_services_20261111','UFA','2026-11-11',1,item,v,u,scope,common)
    add('ufa_fuel_20261111','UFA','2026-11-11',1,'aviation_fuel_TS1_RT',136300,'RUB/t fuel','Russian/Belarus consumers','Fuel purchase price; uplift is listed separately; contract inclusion unknown')
    for item,v,u,scope,page in [('takeoff_landing',911,'RUB/t MTOW','Russian operators; coefficient1 for airplanes over12t',1),('transport_security',947,'RUB/t MTOW','Russian operators; coefficient1 for airplanes over12t',1),('terminal_domestic_adult',97,'RUB/passenger','domestic adult',1),('terminal_domestic_child2to12',48.5,'RUB/passenger','domestic age2-12',1),('terminal_international_adult',140,'RUB/passenger','international adult',1),('passenger_service_domestic_adult',200,'RUB/passenger','domestic adult',1),('passenger_service_domestic_child2to12',100,'RUB/passenger','domestic age2-12',1),('passenger_service_international_adult',297,'RUB/passenger','international adult',1),('mechanical_deicing_SSJ_excluding_fluid',53446,'RUB/unit','SSJ100/RRJ95B and group MTOW30-74.999t; fluid EXTRA',10),('manual_deicing_SSJ',7148,'RUB/unit','SSJ100/RRJ95B and group MTOW30-74.999t',10),('GPU_APA80_140_Aist3',535,'RUB/min','electrical ground power service',10)]:
        add('omsk_tariff_base_20260821','OMS','2026-08-21',page,item,v,u,scope,common+'; later amendments downloaded and checked')
    add('omsk_tariff_amend_20261010','OMS','2026-10-10',1,'deicing_fluid_typeI',211000,'RUB/t fluid','Aviaflo EG','Supersedes base 204500 RUB/t; weather consumption unknown')
    add('omsk_tariff_amend_20261010','OMS','2026-10-10',1,'deicing_fluid_typeIV',246,'RUB/litre fluid','Aviaflight EG / Green Flo','Supersedes base 236 RUB/litre; do not interchange tonne and litre without density')
    add('omsk_tariff_amend_20261015','OMS','2026-10-15',1,'VIP_service_conditional',5740,'RUB/person','VIP service if previous month business-lounge volume exceeds1000','Conditional VIP service; not ordinary passenger handling')
    write('airport_cost_selected_verified.csv',vals)
    return dict(selected_visually_checked_rows=len(vals),airports=2,contract_cost_observations=0)
def join_check():
    with (OUT/'uvt_schedule_rules_unique.csv').open() as f:uvt=list(csv.DictReader(f))
    with (OUT/'omsk_domestic_timetable_rows.csv').open() as f:oms=list(csv.DictReader(f))
    a=next(r for r in uvt if r['origin_city_raw']=='Казань' and r['destination_city_raw']=='Омск' and '651' in r['flight_number_raw'])
    b=next(r for r in oms if '651/652' in r['flight_numbers_raw'])
    row=dict(source1_dataset_id='uvt_schedule_current',source1_row=a['source_table_row'],source1_origin_city=a['origin_city_raw'],source1_destination_city=a['destination_city_raw'],source1_flight=a['flight_number_raw'],source1_period=a['validity_raw'],source1_weekdays=a['weekdays_raw'],source1_departure=a['departure_local_raw'],source1_arrival=a['arrival_local_raw'],source2_dataset_id='omsk_winter_2026',source2_text_line=b['source_text_line'],source2_full_routing=b['routing_raw'],source2_weekdays=b['weekdays_raw'],source2_period=b['period_raw'],source2_origin_departure=b['preceding_origin_departure_local_raw'],source2_omsk_arrival=b['omsk_arrival_local_raw'],join_method='carrier identity RT/ЮВ + flight651 + Kazan/Omsk endpoints + intersecting explicit period; independent publishers',departure_time_match=a['departure_local_raw'].replace('-','.')==b['preceding_origin_departure_local_raw'],arrival_time_match=a['arrival_local_raw'].replace('-','.')==b['omsk_arrival_local_raw'],finding='UVT endpoint offer is a through flight via Tobolsk; NOT nonstop Kazan-Omsk',decision_use='Do not use endpoint pair listings as direct-capacity inventory; preserve intermediate airport and stop time',value_status='DERIVED')
    assert row['departure_time_match'] and row['arrival_time_match'] and 'Тобольск' in b['routing_raw']
    write('uvt_omsk_two_source_join.csv',[row]);return row
def main():
    summary={'omsk':omsk(),'uvt_week':uvt_week(),'omsk_week':omsk_week(),'selected_costs':costs(),'two_source_join':join_check()}
    (OUT/'supplement_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
