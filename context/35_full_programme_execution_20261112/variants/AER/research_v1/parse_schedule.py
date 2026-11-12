"""Извлечение опубликованных строк; не инвентарь и не фактические рейсы."""
import csv, hashlib, html, json, re
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
receipts={r['source_id']:r for r in json.loads((ROOT/'fetch_receipts.json').read_text())}
names={'ПЕРМЬ':'PEE','САРАТОВ':'GSV','ВОЛГОГРАД':'VOG','МАХАЧКАЛА':'MCX','БАТУМИ':'BUS','ТБИЛИСИ':'TBS','ТЕЛЬ-АВИВ':'TLV','АЛМАТЫ':'ALA','САРАНСК':'SKX','НАРЬЯН-МАР':'NNM','МОСКВА / ШРМ':'SVO','НИЖНЕКАМСК':'NBC','НИЖНИЙ НОВГОРОД':'GOJ','МАГНИТОГОРСК':'MQF','УФА':'UFA'}
def one(pattern,s):
    m=re.search(pattern,s,re.S);return html.unescape(re.sub('<.*?>','',m.group(1))).strip() if m else 'UNKNOWN'
def iso(s):return datetime.strptime(s,'%d.%m.%Y').date().isoformat()
rows=[];outcomes=[]
for sid in ['SCHEDULE_PEE','SCHEDULE_GSV','SCHEDULE_VOG','SCHEDULE_MCX','SCHEDULE_RW']:
    raw=(ROOT/'sources'/(sid+'.html')).read_text(); starts=list(re.finditer(r'<div class="main-widget__content__item-block">',raw))
    marker=raw.find('data-type="arrival"');count=0
    for j,m in enumerate(starts):
        part=raw[m.start():starts[j+1].start() if j+1<len(starts) else len(raw)]
        dest=one(r'<div class="main-widget-td1 main-widget-td1__company">(.*?)</div>',part)
        flight=one(r'<span class="main-widget-td1-baggage__seasons--flight">(.*?)</span>',part)
        if not re.fullmatch(r'[A-Z0-9]{2}-[0-9]+',flight):continue
        period=re.findall(r'\b\d{2}\.\d{2}\.\d{4}\b',part)
        direction='arrival' if marker>=0 and m.start()>marker else 'departure'
        row={'offer_row_id':f'AER-PUB-{sid}-{j+1:03d}','origin':'AER' if direction=='departure' else names.get(dest,'UNKNOWN'), 'destination':names.get(dest,'UNKNOWN') if direction=='departure' else 'AER', 'source_city_label':dest,'direction':direction,'flight':flight,'carrier':one(r'<span class="main-widget-td1-baggage__seasons--aircompany">(.*?)</span>',part),'valid_from':iso(period[0]) if period else 'UNKNOWN','valid_to':iso(period[1]) if len(period)>1 else iso(period[0]) if period else 'UNKNOWN','station_clock_local':one(r'<p class="main-widget-td1--country__seasons">(.*?)</p>',part),'weekdays_ru':one(r'<div class="main-widget-td1 main-widget-td1__flight">(.*?)</div>',part),'source_id':sid,'source_url':receipts[sid]['url'],'source_html_byte_offset_utf8':len(raw[:m.start()].encode()),'source_html_sha256':receipts[sid]['sha256'],'row_fragment_sha256':hashlib.sha256(part.split('</div></div></div>',1)[0].encode()).hexdigest(),'as_of':receipts[sid]['fetched_at_utc'],'unit':'опубликованная строка расписания; местное время станции','period':'valid_from..valid_to','coverage':'только результат фильтра; полнота UNKNOWN; не продажа','status':'PUBLISHED_SCHEDULE_NOT_INVENTORY','aircraft':'UNKNOWN','seats':'UNKNOWN','fare_rub':'UNKNOWN','baggage':'UNKNOWN','booking_lead_days':'NOT_A_PRICE_QUOTE','physical_adjacency':'UNKNOWN','future_extension':'не продлевать автоматически на 2028'}
        rows.append(row);count+=1
    outcomes.append({'source_id':sid,'parsed_rows':count,'status':'ROWS_FOUND' if count else 'NO_ROWS_IN_THIS_FILTER_NOT_MARKET_ABSENCE','pagination_present':'nav-more-departure=page-2' in raw or 'nav-more-arrival=page-2' in raw,'complete':False})
with (ROOT/'local_schedule_offers.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(ROOT/'schedule_query_outcomes.json').write_text(json.dumps(outcomes,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(outcomes,ensure_ascii=False))
print('RW markets',sorted(set((r['origin'],r['destination']) for r in rows if r['flight'].startswith('WZ'))))
