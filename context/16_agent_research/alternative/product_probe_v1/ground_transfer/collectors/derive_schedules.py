#!/usr/bin/env python3
"""Normalize frozen official SKPPK date results; never substitute missing routes."""
import csv, hashlib, html, json, pathlib, re, urllib.parse
ROOT = pathlib.Path(__file__).resolve().parents[1]
STATIONS = {'9613073':('rail_mineralnye_vody','Минеральные Воды'), '9612962':('rail_kislovodsk','Кисловодск'), '9612972':('rail_pyatigorsk','Пятигорск'), '9612992':('rail_essentuki','Ессентуки')}
def plain(s): return ' '.join(html.unescape(re.sub('<[^>]*>', ' ', s)).split())
def duration_minutes(s):
    hours = re.search(r'(\d+)\s+час',s); mins = re.search(r'(\d+)\s+минут',s)
    assert hours or mins, s
    return (int(hours.group(1))*60 if hours else 0) + (int(mins.group(1)) if mins else 0)
def minutes(s): a,b=map(int,s.split(':'));return a*60+b
def write(name, rows):
    assert rows, name
    with (ROOT/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
schedules=[]; fares=[]; checks=[]
for path in sorted((ROOT/'receipts').glob('skppk_dec*.json')):
    receipt=json.loads(path.read_text()); raw=(ROOT/receipt['raw_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==receipt['sha256'],path
    s=raw.decode('utf-8'); q=urllib.parse.parse_qs(urllib.parse.urlsplit(receipt['url']).query)
    date=q['date'][0]; origin=q['from'][0];destination=q['to'][0]
    assert re.search(r"<input type='date' value='"+date+"'",s), (path,'date field')
    day=str(int(date[-2:])); assert re.search('Расписание на '+day+' декабря 2026г.',s), (path,'heading date')
    for code, role in [(origin,'from'),(destination,'to')]:
        assert re.search("id='"+role+"'\\s+data-code='"+code+"'\\s+value='"+STATIONS[code][1]+"'",s), (path,role)
    blocks=re.findall(r"<a href='([^']+)' class='row-wrapper'>(.*?)</a>",s,re.S)
    assert blocks,(path,'no rows; empty result must be investigated')
    n=0
    for href,block in blocks:
        times=re.findall(r"<p class='time'>(.*?)</p>",block); assert len(times)==2
        durtext=plain(re.search(r"<p class='duration'>(.*?)</p>",block,re.S).group(1));dur=duration_minutes(durtext)
        train=plain(re.search(r"<p class='train'>(.*?)</p>",block,re.S).group(1)).removeprefix('Поезд ')
        carrier=plain(re.search(r"<p class='carrier'>(.*?)</p>",block,re.S).group(1)).removeprefix('Перевозчик: ')
        offset=(minutes(times[0])+dur-minutes(times[1]))/1440
        assert offset>=0 and offset.is_integer(), (path,train,'duration-clock mismatch')
        row_id=receipt['source_id']+'_'+train
        common={'observation_id':row_id,'candidate_id':'C14','origin_place_id':STATIONS[origin][0],'origin_name':STATIONS[origin][1], 'origin_source_code':origin,'destination_place_id':STATIONS[destination][0],'destination_name':STATIONS[destination][1],'destination_source_code':destination,'service_date':date,'train_number':train,'operating_carrier_advertised':carrier,'source_id':receipt['source_id'],'source_url':receipt['url'],'source_sha256':receipt['sha256'],'searched_utc':receipt['completed_utc']}
        schedules.append({**common,'departure_clock':times[0],'arrival_clock':times[1],'duration_minutes':dur,'duration_basis':'PUBLISHED_DATED_SCHEDULE','arrival_day_offset':int(offset),'day_offset_basis':'DERIVED_FROM_PUBLISHED_CLOCKS_AND_DURATION','origin_iana':'UNKNOWN','destination_iana':'UNKNOWN','source_time_basis':'NOT_EXPLICIT_ON_CAPTURED_PAGE','valid_from':date,'valid_through':date,'exceptions':'NO_EXTRAPOLATION; operator warns of unscheduled changes','service_status':'ADVERTISED_SCHEDULE; NOT_PERFORMED_INSTANCE','booking_status':'NOT_QUERIED','conditions':'Station-to-station only; excludes airport shuttle/wait/walk/final-sanatorium leg','detail_url':urllib.parse.urljoin(receipt['url'],html.unescape(href))})
        amount=re.search(r'Полный тариф:\s*([\d.]+)',plain(block));assert amount
        fares.append({**common,'amount_rub':amount.group(1),'price_unit':'RUB_PER_PERSON_ONE_WAY_FULL_TARIFF','price_basis':'SOURCE_DISPLAYED_TARIFF_ON_DATED_SCHEDULE_PAGE','fare_validity':'DISPLAYED_FOR_QUERY_DATE; effective tariff instrument not verified','inventory_status':'UNKNOWN_NOT_A_SEAT_QUOTE','included':'Rail leg only','excluded_or_unknown':'Airport shuttle; baggage/other eligibility conditions not verified; no purchase','realised_revenue':'UNKNOWN'})
        n+=1
    checks.append({'source_id':receipt['source_id'],'date':date,'rows':n,'checks':'raw hash; requested date echoed in field and heading; origin/destination codes and labels; duration-clock consistency; unique row ids'})
assert len({r['observation_id'] for r in schedules})==len(schedules)
write('transfer_schedule.csv',schedules);write('transfer_fare_observations.csv',fares)
(ROOT/'schedule_verification.json').write_text(json.dumps({'status':'PASS','rows':len(schedules),'sources':checks,'limitations':['No IANA or time-basis statement on captured date pages: left UNKNOWN','Schedule is advertised; not observed operation or inventory','Sampled dates only; no interpolation']},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'schedule_rows':len(schedules),'fare_rows':len(fares),'date_pages':len(checks)},ensure_ascii=False))
