"""Build P02 from frozen Git inputs and public-source captures. Standard library only."""
import calendar, collections, csv, datetime as dt, hashlib, html, json, pathlib, re
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parent
START, END = dt.date(2026, 11, 1), dt.date(2027, 10, 31)
METHOD = 'P02-v2-seasonal-20261112'
UNKNOWN = 'UNKNOWN'

def read(name):
    with (ROOT/'inputs'/name).open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

def write(name, rows, fields=None):
    fields = fields or list(dict.fromkeys(k for r in rows for k in r))
    with (ROOT/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fields,extrasaction='raise');w.writeheader();w.writerows(rows)

def jwrite(name,obj):
    (ROOT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')

def stable(s):return hashlib.sha256(s.encode()).hexdigest()[:16]
def market(a,b):return ('CITY:' if 'MOW' in (a,b) else 'AIR:')+a+':'+b
def date(s):return dt.date.fromisoformat(s)
def weekdays(s):
    s=s.lower().replace('ё','е')
    if 'ежеднев' in s:return [1,2,3,4,5,6,7]
    return [i for i,t in enumerate(['пн','вт','ср','чт','пт','сб','вс'],1) if t in s]
def flight(s,carrier=''):
    s=re.sub('[^A-ZА-Я0-9]','',s.upper())
    if carrier and s.startswith(carrier):s=s[len(carrier):]
    return s

class Text(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,t,a):
        if t in ('script','style'):self.skip+=1
    def handle_endtag(self,t):
        if t in ('script','style'):self.skip=max(0,self.skip-1)
    def handle_data(self,s):
        if not self.skip and s.strip():self.parts.append(s.strip())
def plaintext(s):
    p=Text();p.feed(s);return ' '.join(p.parts)

class Table(HTMLParser):
    def __init__(self):super().__init__();self.rows=[];self.cells=[];self.cell=None;self.origin=''
    def handle_starttag(self,t,a):
        if t=='tr':self.cells=[]
        if t in ('td','th'):self.cell=[]
    def handle_data(self,s):
        if s.strip().startswith('Из города'):self.origin=s.strip().removeprefix('Из города ')
        if self.cell is not None:self.cell.append(s)
    def handle_endtag(self,t):
        if t in ('td','th') and self.cell is not None:self.cells.append(' '.join(' '.join(self.cell).split()));self.cell=None
        if t=='tr' and self.cells:self.rows.append((self.origin,self.cells))

manifest=json.loads((ROOT/'input_manifest.json').read_text())
receipts=json.loads((ROOT/'evidence/fetch_receipts.json').read_text())
sources={r['source_id']:r for r in manifest+receipts}
seeds=json.loads((ROOT/'inputs/PLAN_variant_research_plan.json').read_text())['seed_cities']
seed_codes={r['iata'] for r in seeds}
names={r['city']:r['iata'] for r in seeds}
names.update({'Екатеринбург':'SVX','Казань':'KZN','Нижнекамск (Бегишево)':'NBC','Бугульма':'UUA','Тобольск':'RMZ','Горно-Алтайск':'RGK','Горно Алтайск':'RGK','Томск':'TOF','Новый Уренгой':'NUX','Нижневартовск':'NJC','Ноябрьск':'NOJ','Сургут':'SGC','Магнитогорск':'MQF','Санкт-Петербург':'LED','Саранск':'SKX','Чебоксары':'CSY','Киров':'KVX','Ярославль':'IAR','Усинск':'USK','Когалым':'KGP','Мурманск':'MMK','Нальчик':'NAL','Магас':'IGT','Грозный':'GRV','Петрозаводск':'PES','Москва':'MOW'})
carrier_map={'RED WINGS':'WZ','РедВингс':'WZ','Red Wings':'WZ','Россия':'FV','Аэрофлот':'SU','Победа':'DP','S7 Airlines':'S7','Сибирь':'S7','S7':'S7','ЮТэйр':'UT','ЮТейр':'UT','Utair':'UT','Уральские а/л':'U6','Ural airlines':'U6','Уральские авиалинии':'U6','NORD WIND':'N4','Северный Ветер':'N4','Nordwind Airlines':'N4','Nordwind':'N4','Азимут':'A4','Икар':'EO','ИКАР':'EO','ЮВТ АЭРО':'RT','ЮВТаэро':'RT','UVT Aero':'RT','UVT AERO':'RT','Smartavia':'5N','NordStar':'Y7','Nordstar':'Y7','РусЛайн':'7R','IrAero Airlines':'IO','ИРАЭРО':'IO','ИрАэро':'IO','Газпром авиа':'4G','Ямал':'YC','КрасАвиа':'KV','AZUR air':'ZF','Air Serbia':'JU','Nesma Airlines':'NE','Almasria Universal Airlines':'UJ','Shirak Avia':'5G','Uzbekistan Airways':'HY','Somon Air':'SZ','Pegasus Airlines':'PC','Flydubai':'FZ','Алроса':'6R','Air Cairo':'SM'}
products=[];rules=[];gaps=[]
DEFAULT=dict(row_grain='schedule_rule',status='published_offer',departure_date='',valid_from='',valid_to='',weekdays_iso='',departure_local='',arrival_local='',elapsed_min_reported=UNKNOWN,nominal_seats=UNKNOWN,nominal_seat_basis=UNKNOWN,open_seats=UNKNOWN,open_seats_scope='not_observed',fare_rub=UNKNOWN,comparable_basket='false',fare_basis=UNKNOWN,baggage=UNKNOWN,fees_status=UNKNOWN,sellability='published_schedule_not_inventory',via_airports=UNKNOWN,physical_leg_status='not_established',operating_carrier_status='source_label_only_legal_operator_unverified',marketing_carrier_status=UNKNOWN,aircraft=UNKNOWN,assumption_ids='P02-A01;P02-A03;P02-A04;P02-A05',coverage='source_specific_incomplete',method_version=METHOD,year_2027_2028_use='scenario_only_no_automatic_extension')

def add(a,b,source_id,source_locator,**kw):
    r=DEFAULT.copy();r.update(origin=a,destination=b,market_id=market(a,b),source_id=source_id,source_locator=source_locator,carrier=UNKNOWN,flight=UNKNOWN)
    src=sources[source_id];r.update(source_url=src.get('url','git:'+src.get('commit','')+':'+src.get('git_path','')),retrieved_at=src.get('retrieved_at','preserved_at_pinned_commit'),as_of=src.get('retrieved_at','preserved_source_date_not_reverified'),collection=src.get('collection',src.get('acquisition','new_browser_observation')))
    r.update(kw);r['product_id']='P02-'+stable('|'.join(str(r.get(k,'')) for k in ['source_id','source_locator','origin','destination','flight','valid_from','valid_to','departure_date','fare_basis']))
    products.append(r);return r

for n,r in enumerate(read('BASE_cards.csv'),2):
    if r['product_type']=='NO_MATCHED_PRODUCT':continue
    # Card departures are a bounded observation, never extended to season/year.
    for d in r['departure_dates'].split(';'):
        if not d:continue
        dep=r['departure_local'] if re.fullmatch(r'\d\d:\d\d',r['departure_local']) else UNKNOWN
        arr=r['arrival_local'] if re.fullmatch(r'\d\d:\d\d(?:\s*\(\+1\))?',r['arrival_local']) else UNKNOWN
        add(r['origin'],r['destination'],'BASE_cards.csv',f'row:{n};card:{r["card_id"]}',row_grain='dated_published_service',departure_date=d,valid_from=d,valid_to=d,departure_local=dep,arrival_local=arr,carrier=carrier_map.get(r['carrier'],r['carrier']),flight=r['flight'],aircraft=r['aircraft'],elapsed_min_reported=r['duration_min_minutes'] or UNKNOWN,source_url=r['source_urls'],as_of='2026-11-09/10 preserved; see card/source lock',physical_leg_status='published_endpoint_pair_not_execution',via_airports=r['via_airports'] or UNKNOWN,notes='Multiple clocks in aggregate card are not assigned to individual dates; exact mapping UNKNOWN when card clock is not singular.')

for n,r in enumerate(read('BASE_omsk.csv'),2):
    add(r['origin_airport_iata'],r['destination_airport_iata'],'BASE_omsk.csv',f'row:{n};pdf_line:{r["source_text_line"]}',row_grain='dated_published_service',departure_date=r['departure_date_local'],valid_from=r['departure_date_local'],valid_to=r['departure_date_local'],departure_local=r['departure_local'],arrival_local=r['published_onward_arrival_local_raw'],carrier=carrier_map.get(r['carrier_raw'],r['carrier_raw']),flight=r['outbound_flight_numeric'],source_url='https://www.aeroomsk.ru/karta-poleta/pdf/w26/w26-20261105.pdf',as_of='2026-11-09 preserved',physical_leg_status='published_adjacent_leg',via_airports='',notes=r['limitations'])

for n,r in enumerate(read('UFA_schedule_rows.csv'),2):
    add('UFA',r['destination'],'UFA_schedule_rows.csv',f'row:{n}',valid_from=r['valid_from'],valid_to=r['valid_to'],weekdays_iso=';'.join(map(str,weekdays(r['active_weekdays']))),departure_local=r['departure'],arrival_local=r['arrival'],carrier=carrier_map.get(r['airline'],r['airline']),flight=r['flight'],aircraft=r['aircraft'],source_url=r['source_url'],as_of='2026-11-12 preserved',elapsed_min_reported=r['block_time'],physical_leg_status='published_endpoint_pair_not_execution')

for n,r in enumerate(read('GOJ_schedule_observations.csv'),2):
    a,b=('GOJ',r['airport']) if r['direction']=='out' else (r['airport'],'GOJ')
    add(a,b,'GOJ_schedule_observations.csv',f'row:{n}',valid_from=r['valid_from'],valid_to=r['valid_to'],weekdays_iso=';'.join(map(str,weekdays(r['days']))),departure_local=r['departure_local'],arrival_local=r['arrival_local'],carrier=carrier_map.get(r['carrier'],r['carrier']),flight=r['flight'],aircraft=r['aircraft'],source_url='https://ar-goj.ru/schedule/'+('' if r['direction']=='out' else '?type=arr'),as_of='2026-11-12 preserved',physical_leg_status='published_endpoint_pair_not_execution')

# Airport pages omit years. Preserve that inference explicitly and restrict it to current winter.
month_ru={m:i for i,m in enumerate(['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек'],1)}
for src,station,direction in [('NEW_GOJ_OUT','GOJ','out'),('NEW_GOJ_IN','GOJ','in'),('NEW_SVX_OUT','SVX','out'),('NEW_SVX_IN','SVX','in'),('NEW_KUF_OUT','KUF','out'),('NEW_GSV_OUT','GSV','out')]:
    p=Table();p.feed((ROOT/'evidence'/(src+'.html')).read_text(errors='replace'))
    for n,(_,c) in enumerate(p.rows,1):
        if len(c)!=8 or not re.fullmatch('[A-Z]{3}',c[7]):continue
        a,b=(station,c[7]) if direction=='out' else (c[7],station)
        if a not in seed_codes and b not in seed_codes:continue
        mm=re.fullmatch(r'(\d{2})\s+(\w{3})\s*/\s*(\d{2})\s+(\w{3})',c[3])
        if not mm:continue
        d1,m1,d2,m2=mm.groups();m1,m2=month_ru.get(m1),month_ru.get(m2)
        if m1 is None or m2 is None:continue
        y1=2026 if m1>=10 else 2027;y2=2026 if m2>=10 else 2027
        lo,hi=dt.date(y1,m1,int(d1)),dt.date(y2,m2,int(d2))
        if hi<lo or lo<dt.date(2026,10,1) or hi>dt.date(2027,3,31):
            gaps.append(dict(gap_id='P02-YEAR-'+stable(src+str(n)),source_id=src,locator=f'table_row:{n}',issue='Yearless period not within current winter interpretation; excluded pending source-year verification'));continue
        add(a,b,src,f'table_row:{n}',valid_from=str(lo),valid_to=str(hi),weekdays_iso=';'.join(map(str,weekdays(c[2]))),departure_local=c[0],arrival_local=c[1],carrier=carrier_map.get(c[4],c[4]),flight=c[5],aircraft=c[6],assumption_ids='P02-A01;P02-A03;P02-A04;P02-A05;P02-A07',notes='Year absent from displayed row; current winter2026/27 interpretation is explicit P02-A07; do not extend to summer. Station-pair may be a through product.')

# Fresh UVT schedules include both direct and through station-pair products.
p=Table();p.feed((ROOT/'evidence/NEW_UVT_SCHEDULE.html').read_text(errors='replace'))
for n,(origin,cells) in enumerate(p.rows,1):
    if len(cells)!=12 or origin not in names or cells[0] not in names:continue
    a,b=names[origin],names[cells[0]]
    if not (a in seed_codes or b in seed_codes):continue
    m=re.fullmatch(r'(\d\d\.\d\d\.\d\d)-(\d\d\.\d\d\.\d\d)',cells[1])
    if not m:continue
    lo,hi=[dt.datetime.strptime(v,'%d.%m.%y').date().isoformat() for v in m.groups()]
    for x,y,fl,dep,arr,days,side in [(a,b,*cells[3:7],'out'),(b,a,*cells[8:12],'return')]:
        if fl.strip()=='-':continue
        flight_code='RT'+re.search(r'(\d{3,4})',fl).group(1)
        add(x,y,'NEW_UVT_SCHEDULE',f'table_row:{n}:{side}',valid_from=lo,valid_to=hi,weekdays_iso=';'.join(map(str,weekdays(days))),departure_local=dep.replace('-',':'),arrival_local=arr.replace('-',':'),carrier='RT',flight=flight_code,aircraft=cells[7],nominal_seats='50',nominal_seat_basis='NEW_UVT_FLEET:type_configuration_not_open_inventory',via_airports=UNKNOWN,physical_leg_status='station_pair_itinerary_may_include_intermediate_stops',assumption_ids='P02-A01;P02-A03;P02-A04;P02-A05;P02-A06',notes='Repeated flight numbers across station pairs must share physical inventory; continuity/sale on individual legs not assumed.')

# Fresh IrAero page is filtered to IKT, covers 12Nov–12Dec, not the full airline.
s=(ROOT/'evidence/NEW_IR_SCHEDULE.html').read_text(errors='replace')
for n,block in enumerate(re.split(r'<div class="swiper-slide flight-row',s)[1:],1):
    def field(name):
        m=re.search(r'name="'+re.escape(name)+r'" value="([^"]+)"',block);return html.unescape(m.group(1)) if m else ''
    a,b=field('origin-city-code[0]'),field('destination-city-code[0]');d=field('date[0]')
    if not (a and b and d):continue
    def cls(name):
        m=re.search(r'<div class="'+name+r'">(.*?)</div>',block,re.S);return plaintext(m.group(1)) if m else UNKNOWN
    fl=re.search(r'IO-\d+',block);ac=re.search(r'fly-info-number[^>]*>\s*<span>(.*?)</span>',block,re.S)
    add(a,b,'NEW_IR_SCHEDULE',f'flight_block:{n}',row_grain='dated_published_service',departure_date=dt.datetime.strptime(d,'%d.%m.%Y').date().isoformat(),valid_from=dt.datetime.strptime(d,'%d.%m.%Y').date().isoformat(),valid_to=dt.datetime.strptime(d,'%d.%m.%Y').date().isoformat(),carrier='IO',flight=fl.group(0) if fl else UNKNOWN,departure_local=cls('big time-departure'),arrival_local=cls('big time-arrival'),elapsed_min_reported=cls('fly-time'),aircraft=plaintext(ac.group(1)) if ac else UNKNOWN,notes='Source duration displayed separately; arrival day and route stops unverified; not used to infer block time. Only IKT origin and current search horizon.')

# Primary advertised fares have no dated availability claim.
for a,b,fl,fare in [('MRV','UFA','A46021',7530),('UFA','MRV','A46022',5950)]:
    add(a,b,'NEW_AZ_WINTER','article:2026-07-03',row_grain='advertised_fare',valid_from='2026-10-25',valid_to='2027-03-27',carrier='A4',flight=fl,fare_rub=str(fare),fare_basis='advertised_from_price_not_same_date_quote',as_of='2026-07-03 published; re-read2026-11-12',baggage=UNKNOWN,fees_status=UNKNOWN,sellability='sales_announcement_not_current_inventory')

# RW sale route amounts, preserving the actual linked dated search rather than inventing dates.
s=(ROOT/'evidence/NEW_RW_SALE.html').read_text(errors='replace')
for n,m in enumerate(re.finditer(r'<a[^>]+href="(https://flyredwings.com/booking/#/search/([^\"]+))"[^>]*>(.*?)</a>',s,re.S),1):
    url,query,inside=m.groups();t=plaintext(inside);m2=re.match(r'([A-Z]{3})([A-Z]{3})(\d{8})',query)
    price=re.search(r'от\s*([\d\s\xa0]+)',t)
    if not m2 or not price:continue
    a,b,ds=m2.groups()
    try:d=dt.datetime.strptime(ds,'%Y%m%d').date()
    except ValueError:
        gaps.append(dict(gap_id='P02-SRC-RW-MALFORMED-DATE',source_id='NEW_RW_SALE',locator=query,issue='Source link has impossible date; no correction invented'));continue
    r=add(a,b,'NEW_RW_SALE',f'offer_link:{n}',row_grain='advertised_fare',departure_date=d.isoformat(),fare_rub=re.sub(r'\D','',price.group(1)),fare_basis='promotion_from; linked search may be return; not quote',baggage='Light:no_checked_bag;Standard:20kg;advertised_brand_unknown',source_url=url,fees_status=UNKNOWN,valid_from='2026-11-16',valid_to=UNKNOWN,sellability='limited_promotion_10_12Nov_not_current_inventory',as_of='2026-11-10/12 promotion; captured2026-11-12',assumption_ids='P02-A01;P02-A02;P02-A03;P02-A05',notes='Do not divide return price by two; link is not a confirmed ticket/final fare.')

for n,r in enumerate(read('BASE_fare_spots.csv'),2):
    add(r['origin'],r['destination'],'BASE_fare_spots.csv',f'row:{n}',row_grain='dated_secondary_fare',departure_date=r['departure_date'],carrier=carrier_map.get(r['carrier'],r['carrier']),flight=r['flight'],fare_rub=r['price_rub'],fare_basis='secondary_cached_offer',as_of=r['observed_at'],source_url=r['source'],notes=r['offer_conditions'])

# Additional browser quotes and primary connection/ground releases are curated facts.
curated=json.loads((ROOT/'research_notes.json').read_text())
for r in curated['sources']:
    sources[r['source_id']]=r
for r in curated['products']:
    r=r.copy();a,b,src,loc=[r.pop(k) for k in ['origin','destination','source_id','source_locator']];add(a,b,src,loc,**r)
for r in products:
    r['booking_lead_days']=UNKNOWN
    try:r['booking_lead_days']=(date(r['departure_date'])-date(r['as_of'][:10])).days
    except (ValueError,TypeError):pass
    if r['row_grain']=='advertised_fare':r['booking_lead_days']=UNKNOWN
    r['key']=r['product_id']
    r['period']=r['departure_date'] or (r['valid_from']+'/'+r['valid_to'])
    r['unit']='product;fare_RUB_per_journey;clock_local;nominal_seats_per_aircraft'
    r['lower']=UNKNOWN;r['upper']=UNKNOWN
    r['bounds_scope']='total_physical_open_seats_unmeasured;not_price_confidence_interval'
    r['quoted_party_size']='1' if r['row_grain'].startswith('dated_primary') else UNKNOWN
    r['year_status']='INFERRED_CURRENT_WINTER_P02-A07' if 'P02-A07' in r['assumption_ids'] else 'SOURCE_OR_PINNED_EXTRACT_DATE;see_source_locator'
    r['temporal_acceptance']='conditional_source_year' if 'P02-A07' in r['assumption_ids'] else 'source_specific_only'

# Calendar projection. Dedup carrier+number+endpoints+date; station pairs are NOT independent physical legs.
cal=collections.defaultdict(list)
for r in products:
    if r['row_grain'] not in ('schedule_rule','dated_published_service','dated_primary_quote'):continue
    if r['departure_date']:
        ds=[date(r['departure_date'])]
    else:
        try:lo,hi=max(START,date(r['valid_from'])),min(END,date(r['valid_to']))
        except ValueError:continue
        w={int(x) for x in r['weekdays_iso'].split(';') if x}
        ds=[lo+dt.timedelta(days=i) for i in range(max(0,(hi-lo).days+1)) if (lo+dt.timedelta(days=i)).isoweekday() in w]
    for d in ds:
        if START<=d<=END:
            k=(r['origin'],r['destination'],r['carrier'],flight(r['flight'],r['carrier']),d.isoformat())
            cal[k].append(r)
calendar_rows=[]
for key,rs in sorted(cal.items()):
    a,b,c,fl,d=key
    clocks=sorted({re.search(r'T(\d\d:\d\d)',r['departure_local']).group(1) if 'T' in r['departure_local'] else r['departure_local'] for r in rs if r['departure_local'] and r['departure_local']!=UNKNOWN})
    calendar_rows.append(dict(schedule_instance_id='SIP-'+stable('|'.join(key)),market_id=market(a,b),origin=a,destination=b,carrier=c,flight=fl,departure_date=d,departure_local='|'.join(clocks),clock_conflict=str(len(clocks)>1).lower(),source_product_ids=';'.join(sorted({r['product_id'] for r in rs})),source_ids=';'.join(sorted({r['source_id'] for r in rs})),record_type='dated_station_pair_offer',physical_inventory_id=UNKNOWN,physical_adjacent_leg_status='published_adjacent_leg' if any(r['physical_leg_status']=='published_adjacent_leg' for r in rs) else 'UNKNOWN',open_seats=UNKNOWN,seat_inventory_usable='false',status='published_offer',method_version=METHOD))

# Explicit market domain: all 20-city directed pairs, all author hub spokes/direct legs and every evidenced product.
scope=collections.defaultdict(set)
for a in seed_codes:
    for b in seed_codes:
        if a!=b:scope[(a,b)].add('twenty_city_domain')
for r in read('BASE_network_routes.csv'):
    a,b=r['from'],r['to'];label='historical_direct:'+r['variant'] if r['variant'].startswith('Прямые') else 'author_hub:'+r['variant']
    scope[(a,b)].add(label);scope[(b,a)].add(label+':reverse_required_not_inferred_offer')
for seed in json.loads((ROOT/'inputs/PLAN_variant_research_plan.json').read_text())['legacy_direct_rotation_seeds']:
    for a,b in seed['legs']:scope[(a,b)].add('plan_direct_seed:'+seed['historical_name']);scope[(b,a)].add('plan_direct_seed_reverse:'+seed['historical_name'])
for r in products:scope[(r['origin'],r['destination'])].add('evidenced_product')
by_market=collections.defaultdict(list)
for r in products:by_market[(r['origin'],r['destination'])].append(r)
by_calendar=collections.defaultdict(list)
for r in calendar_rows:by_calendar[(r['origin'],r['destination'])].append(r)
coverage=[];monthly=[]
months=[f'{y}-{m:02}' for y,m in [(2026,11),(2026,12)]+[(2027,m) for m in range(1,11)]]
for (a,b),labels in sorted(scope.items()):
    rs=by_market[(a,b)];cs=by_calendar[(a,b)]
    f=[r for r in rs if r['row_grain'] in ('schedule_rule','dated_published_service','dated_primary_quote')]
    quotes=[r for r in rs if r['row_grain']=='dated_primary_quote' and r['comparable_basket']=='true']
    covered_months=sorted({r['departure_date'][:7] for r in cs})
    gaps_list=[]
    if not f:gaps_list.append('dated_air_schedule')
    if not quotes:gaps_list.append('comparable_20kg_dated_fare')
    gaps_list+=['complete_competitor_list','total_open_seats','monthly_endpoint_OD_2025_2026','2027_2028_supply_forecast']
    if len(covered_months)<12:gaps_list.append('uncovered_months:'+'|'.join(m for m in months if m not in covered_months))
    if not any(r['row_grain'].startswith('ground') for r in rs):gaps_list.append('ground_dated_product')
    if not any(r['row_grain']=='dated_primary_connection_quote' and r['departure_date'] for r in rs):gaps_list.append('sellable_connection_on_same_date')
    coverage.append(dict(market_id=market(a,b),origin=a,destination=b,geography_kind='city_group_unresolved_airport' if 'MOW' in (a,b) else 'airport_pair',scope=';'.join(sorted(labels)),offer_observations=len(rs),dated_station_pair_instances=len(cs),carriers=';'.join(sorted({r['carrier'] for r in f})),rw_published_products=sum(r['carrier']=='WZ' for r in f),comparable_quote_count=len(quotes),schedule_months=';'.join(covered_months),source_ids=';'.join(sorted({r['source_id'] for r in rs})),coverage_status='PARTIAL_SOURCE_COVERAGE' if rs else 'UNCOVERED',complete_market='false',absence_proves_no_competitor='false',missing_fields=';'.join(gaps_list),assumption_ids='P02-A01;P02-A02;P02-A03;P02-A04;P02-A05',method_version=METHOD))
    for month in months:
        mc=[r for r in cs if r['departure_date'].startswith(month)]
        monthly.append(dict(market_id=market(a,b),month=month,dated_published_station_pair_instances=len(mc) if mc else UNKNOWN,unit='station_pair_departures_in_source_not_physical_network_total',value_status='published_offer' if mc else 'unknown',carrier_count=len({r['carrier'] for r in mc}) if mc else UNKNOWN,nominal_seats_total=UNKNOWN,open_seats_total=UNKNOWN,source_ids=';'.join(sorted({s for r in mc for s in r['source_ids'].split(';')})),calendar_scope='within_explicit_source_dates_only',market_complete='false',history_2025='UNKNOWN',demand_OD='UNKNOWN',seasonal_comparison_ready='false',method_version=METHOD))

city_coverage=[]
for s in seeds:
    c=s['iata'];cr=[r for r in coverage if r['origin']==c];present=[r for r in cr if r['coverage_status']=='PARTIAL_SOURCE_COVERAGE']
    city_coverage.append(dict(city=c,name=s['city'],required_outbound_markets=len(cr),partially_evidenced_outbound_markets=len(present),uncovered_outbound_markets=len(cr)-len(present),covered_market_ids=';'.join(r['market_id'] for r in present),uncovered_market_ids=';'.join(r['market_id'] for r in cr if r not in present),disposition='KEEP_IN_RESEARCH; not_economic_rejection',history_monthly_2025_2026='request_P05/P01;airport_aggregates_do_not_equal_OD',future_offer_2027_2028='conditional_scenario_required',method_version=METHOD))

write('competitor_products.csv',products)
write('calendar_inventory.csv',calendar_rows)
write('market_coverage.csv',coverage)
write('offer_monthly_coverage.csv',monthly)
write('city_coverage.csv',city_coverage)
write('source_issues.csv',gaps,fields=['gap_id','source_id','locator','issue'])
write('competitor_responses.csv',curated['responses'])
write('assumptions_register.csv',curated['assumptions'])
jwrite('assumptions_register.json',curated['assumptions'])
write('clarification_requests.csv',curated['clarifications'])
write('dependency_requests.csv',curated['dependencies'])
jwrite('hypothesis_proposals.json',curated['hypotheses'])
jwrite('company_dossiers.json',curated['dossiers'])
jwrite('sources.json',list(sources.values()))
write('historical_route_context.csv',[dict(market_id=market(r['origin'],r['destination']),**r,case='preserved_not_current_reverified') for c in ['UFA','GOJ','CEK','PEE','TJM'] for r in read(c+'_routes.csv')])
write('historical_demand_context.csv',[dict(market_id=market(r['from_iata'],r['to_iata']),**r,status='preserved_observation_not_monthly_OD',monthly_disaggregation='UNKNOWN;not_annual_divided_by12',retrieved_at='preserved_in_author_commit',assumption_ids='P02-A01;P02-A05') for r in read('BASE_known_flows.csv')])
history=[]
for s in seeds:
    for y in [2025,2026]:
        for m in range(1,13 if y==2025 else 11):
            history.append(dict(airport=s['iata'],month=f'{y}-{m:02}',airport_passengers=UNKNOWN,endpoint_OD=UNKNOWN,value_status='unknown',unit='airport_passengers_and_journeys_separate',source_id=UNKNOWN,dependency_id='P02-DEP-01',reason='No compatible monthly airport or endpoint-OD source in P02 frozen inputs; annual/partial known_flows not disaggregated; tourism_EMISS_not_air_OD',impact='Cannot calibrate route monthly seasonality or infer annual_growth from one week',refinement='P05/P01 supply pinned primary airport-month and route-month totals with direction/coverage; use sourced range/threshold if OD unavailable'))
write('demand_history_coverage.csv',history)
fare_panel=[]
for r in products:
    if not r['row_grain'].startswith('dated_primary'):continue
    d=date(r['departure_date']);season='winter' if d.month in [12,1,2] else 'summer_peak' if d.month in [6,7,8] else 'shoulder_or_holiday_window'
    fare_panel.append({k:r[k] for k in ['product_id','market_id','carrier','flight','departure_date','departure_local','fare_basis','fare_rub','baggage','fees_status','comparable_basket','as_of','booking_lead_days','source_id']}|dict(weekday_iso=d.isoweekday(),seasonal_window=season,selection_reason='Same SVX-UFA reference market;Tuesday and Friday;winter/postholiday/May/summerleadpanel',causal_season_effect_identified='false',history_price_reconstructed='false',assumption_ids='P02-A02;P02-A15'))
write('fare_panel.csv',fare_panel)
# Ordered source-pattern paths. Leg adjacency is a published-pattern interpretation, not an observed operation.
patterns=[]
for fl,nodes,days,lo,hi in [('RT651',['KZN','RMZ','OMS'],'4','2026-11-05','2026-12-31'),('RT581',['KZN','GOJ','CEK'],'4','2026-11-05','2026-12-31'),('RT581',['KZN','GOJ','CEK'],'7','2026-10-25','2026-12-27')]:
    refs=[]
    for a,b in zip(nodes,nodes[1:]):
        refs.append([r['product_id'] for r in products if r['source_id']=='NEW_UVT_SCHEDULE' and r['flight']==fl and r['origin']==a and r['destination']==b and r['weekdays_iso']==days])
    through=[r['product_id'] for r in products if r['source_id']=='NEW_UVT_SCHEDULE' and r['flight']==fl and r['origin']==nodes[0] and r['destination']==nodes[-1] and r['weekdays_iso']==days]
    patterns.append(dict(itinerary_pattern_id='PAT-'+fl+'-'+days,market_id=market(nodes[0],nodes[-1]),ordered_airports=';'.join(nodes),ordered_leg_ids=';'.join('LEG:'+a+':'+b for a,b in zip(nodes,nodes[1:])),flight_number=fl,valid_from=lo,valid_to=hi,weekdays_iso=days,source_id='NEW_UVT_SCHEDULE',source_product_ids=';'.join(sorted(set(through+sum(refs,[])))),adjacency_status='published_station_clock_pattern;not_executed_proof',operating_marketing_status='source_UVT_RT_label;legal_split_UNKNOWN',aircraft_continuity=UNKNOWN,leg_sellability=UNKNOWN,through_sellability='published_schedule_only_no_dated_quote',physical_inventory_ids=UNKNOWN,nominal_seats_type='50;not_open_inventory',assumption_ids='P02-A06;P02-A11;P02-A12'))
write('ordered_itineraries.csv',patterns)
adjacent=[]
for pat in patterns:
    for ordinal,leg in enumerate(pat['ordered_leg_ids'].split(';'),1):
        _,a,b=leg.split(':')
        rr=[r for r in products if r['source_id']=='NEW_UVT_SCHEDULE' and r['flight']==pat['flight_number'] and r['origin']==a and r['destination']==b and r['weekdays_iso']==pat['weekdays_iso']]
        adjacent.append(dict(candidate_leg_id=leg,pattern_id=pat['itinerary_pattern_id'],sequence=ordinal,origin=a,destination=b,carrier_source_label='RT',flight=pat['flight_number'],departure_local=';'.join(sorted({r['departure_local'] for r in rr})),arrival_local=';'.join(sorted({r['arrival_local'] for r in rr})),valid_from=pat['valid_from'],valid_to=pat['valid_to'],weekdays_iso=pat['weekdays_iso'],source_product_ids=';'.join(sorted({r['product_id'] for r in rr})),adjacency_status='inferred_adjacent_from_published_ordered_station_clocks;not_execution',arrival_date_status=UNKNOWN,legal_operating_carrier=UNKNOWN,marketing_carrier=UNKNOWN,aircraft_continuity=UNKNOWN,leg_sellability=UNKNOWN,open_seats=UNKNOWN,accepted_for_physical_capacity='false',assumption_ids='P02-A06;P02-A11;P02-A12'))
write('physical_adjacent_leg_candidates.csv',adjacent)
queries=[]
for r in json.loads((ROOT/'evidence/RW_seasonal_quote_facts.json').read_text()):
    queries.append(dict(query_id='Q-RW-SVX-UFA-'+r['date'],market_id='AIR:SVX:UFA',as_of='2026-11-12',departure_date=r['date'],booking_lead_days=(date(r['date'])-date('2026-11-12')).days,party_size=1,status=r.get('status','quoted_offer'),fare_rub=UNKNOWN if r.get('status')=='no_results' else r['prices'][1],absence_of_flight_established='false',absence_of_market_established='false',source_id='NEW_RW_QUOTE_'+r['date'].replace('-',''),assumption_ids='P02-A03;P02-A05;P02-A15'))
write('query_outcomes.csv',queries)
jwrite('kernel_adapter_contract.json',dict(version=METHOD,unknown_sentinel=UNKNOWN,inputs=['market_coverage.csv','competitor_products.csv','calendar_inventory.csv','ordered_itineraries.csv','physical_adjacent_leg_candidates.csv','fare_panel.csv','competitor_responses.csv'],prohibited_inferences=['MOW as physical airport','no matched offer as no competitor/demand','scheduled nominal seats as open inventory','station-pair counts summed as physical network capacity','fare per leg for one through journey','single as_of cross-season quotes as pure season effect','winter fixture times52 as annual','annual airport segments as monthly endpointOD'],admission=dict(calendar='source-specific published presence only;clock conflict blocks timing validation',seat_inventory='not admitted without pinned future supply/physical-leg allocation',fares='RW explicitfee20kg quotes admitted for their dated basket only;UT conditional until fee conditions resolved',future_2027_2028='monthly scenario by coordinator,each parameter with assumption ID',market_coverage='all markets retained;unknown not rejected'),handback_to=['P05','P06','P07','P08','P02I']))
# SP03 is a source export. UNKNOWN demand-pool/segment/net fare is a hard admission dependency, never a synthetic pool.
alternatives=[];season=[];product_months=collections.defaultdict(set)
for c in calendar_rows:
    for pid in c['source_product_ids'].split(';'):product_months[pid].add(c['departure_date'][:7])
for r in products:
    travel=r['departure_date'] or (r['valid_from']+'/'+r['valid_to'])
    alternatives.append(dict(offer_set_id=METHOD,demand_pool_id=UNKNOWN,travel_date_or_period=travel,customer_segment='UNSEGMENTED_SOURCE_REFERENCE_NOT_CHOICE_SEGMENT',product_id=r['product_id'],market_id=r['market_id'],carrier=r['carrier'],operator=UNKNOWN,airport_pair=r['origin']+'>'+r['destination'] if 'MOW' not in [r['origin'],r['destination']] else UNKNOWN,gross_fare=r['fare_rub'],net_fare=UNKNOWN,currency='RUB',fare_basis=r['fare_basis'],baggage=r['baggage'],duration=r['elapsed_min_reported'],frequency='published_weekdays_ISO:'+r['weekdays_iso'] if r['weekdays_iso'] else 'one_dated_product' if r['departure_date'] else UNKNOWN,sellable_capacity=UNKNOWN,travel_period=travel,observed_at=r['as_of'],booking_lead_days=r['booking_lead_days'],sales_channel='official_airline_web_quote' if r['row_grain'].startswith('dated_primary') else 'source_timetable_or_announcement' if r['status']=='published_offer' else UNKNOWN,coverage=r['coverage'],availability_status=r['sellability'],response_policy_id='UNKNOWN_REQUIRES_COORDINATOR_P05_P06_POLICY',assumption_id=r['assumption_ids']+';P02-A16;P02-A17',source_id=r['source_id'],source_product_id=r['product_id'],fees_status=r['fees_status'],duration_unit='reported_source_format_not_normalized',row_grain=r['row_grain'],admission_status='SOURCE_ONLY_REQUIRES_DEMAND_POOL_SEGMENT_AND_FUTURE_CONTEXT_BINDING',market_basis=UNKNOWN,inventory_scope=r['open_seats_scope'],year_status=r['year_status']))
    seen=sorted(product_months[r['product_id']] | ({r['departure_date'][:7]} if r['departure_date'] else set()))
    season.append(dict(coverage_id='SC-'+r['product_id'],observation_period=travel,schedule_season='W26_27_INFERRED' if 'P02-A07' in r['assumption_ids'] else 'SOURCE_INTERVAL_NOT_ASSIGNED_WHOLE_SEASON',months_covered=';'.join(seen) or UNKNOWN,day_of_week=r['weekdays_iso'] or str(date(r['departure_date']).isoweekday()) if r['departure_date'] else r['weekdays_iso'] or UNKNOWN,booking_lead=r['booking_lead_days'],history_or_offer_or_forecast='published_offer_or_source_claim_NOT_forecast',gaps='full_year_and_history_incomplete;netfare;demand_pool;inventory;see_market_coverage',forecast_month=UNKNOWN,target_pair_count=UNKNOWN,target_count_status='PROGRAMME_TARGET_OWNED_BY_P09_NOT_ASSERTED_BY_P02',source_id=r['source_id'],assumption_id=r['assumption_ids']+';P02-A16',market_id=r['market_id'],product_id=r['product_id'],temporal_acceptance=r['temporal_acceptance']))
for alt in alternatives:
    raw=alt['duration'];alt['duration_raw']=raw
    if re.fullmatch(r'\d+(?:\.\d+)?',raw):alt['duration']=raw
    elif alt['source_id']=='UFA_schedule_rows.csv' and re.fullmatch(r'\d+:\d\d',raw):
        h,m=map(int,raw.split(':'));alt['duration']=str(h*60+m)
    else:alt['duration']=UNKNOWN
    alt['duration_unit']='minutes;source_reported_not_operationally_verified'
write('alternatives_contract.csv',alternatives)
write('season_coverage.csv',season)
write('market_binding_requests.csv',[dict(market_id=r['market_id'],origin_market=r['origin'],destination_market=r['destination'],direction='directed',market_basis=UNKNOWN,demand_pool_id=UNKNOWN,market_version='PENDING_P05',external_scenario_id='PENDING_COORDINATOR',forecast_period='2027-01..2028-12;monthly',customer_segment=UNKNOWN,potential_journeys=UNKNOWN,lower=UNKNOWN,upper=UNKNOWN,range_basis=UNKNOWN,source_id=UNKNOWN,source_period='history2025_available2026_required',as_of='2026-11-12',coverage=r['coverage_status'],status='NOT_ADMITTED_TO_SP02_UNTIL_POOL_DEFINITION_AND_DEMAND_INPUT',assumption_id='P02-A01;P02-A05;P02-A13;P02-A16') for r in coverage])
jwrite('schema_adaptation.json',dict(contract_commit='b7d74e67dd6c603db049b1915b1afec987e3b458',contract_path='context/35_full_programme_execution_20261112/P00R/schema_patch.csv',accepted_via='coordinator current instruction',SP02=dict(export='market_binding_requests.csv',status='P05_REQUIRED;no_accepted_forecast_markets_rows_created',reason='Common demand_pool_id/catchment de-overlap,customersegment,potential_vs_realized_basis and monthly2027–2028 demand not established by P02; history separate'),SP03=dict(export='alternatives_contract.csv',key=['offer_set_id','demand_pool_id','travel_date_or_period','customer_segment','product_id'],status='SOURCE_EXPORT_NOT_ALLOCATION_READY',unknowns=['demand_pool_id','customer_segment_calibration','operator_legal_identity','net_fare','physical_sellable_capacity','response_policy_id'],response_policy='same response function forKEEP/project;actual response may differ with offered project;notforced_equal_actions'),SP13=dict(export='season_coverage.csv',status='PARTIAL_HISTORY_OFFER_COVERAGE;no_unfounded_forecast_or_target',programme_target='P09 owns end2028main_scenario8–12unique physicalairportpairs;P02setsnoarbitraryfinalistquota'),frozen_tranche=dict(commit='fb918c857c9fecd109e85b8d2c3e83ff22dce639',manifest_sha256='3958d48daac966f62f0a4c1364eba28645f4d5dc95d3d5778804ce36c2ec9326',preserved=True),new_version=METHOD))
stats=dict(products=len(products),calendar_instances=len(calendar_rows),markets=len(coverage),partial_markets=sum(r['coverage_status']=='PARTIAL_SOURCE_COVERAGE' for r in coverage),uncovered_markets=sum(r['coverage_status']=='UNCOVERED' for r in coverage),cities=len(city_coverage),comparable_quotes=sum(r['comparable_basket']=='true' for r in products),clock_conflicts=sum(r['clock_conflict']=='true' for r in calendar_rows),calendar_start=str(START),calendar_end=str(END),monthly_coverage_rows=len(monthly),unique_direct_seeds=len({s.removesuffix(':reverse_required_not_inferred_offer') for r in coverage for s in r['scope'].split(';') if s.startswith('historical_direct:')}),future_factual_carryover=False,independent_review='NOT_PERFORMED_BY_AUTHOR')
jwrite('build_summary.json',stats);print(json.dumps(stats,ensure_ascii=False))
