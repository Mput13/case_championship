#!/usr/bin/env python3
"""Reproduce targeted primary-page checks from saved bytes, not airport OD."""
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re

BASE=Path(__file__).resolve().parents[1]

class Visible(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in {'script','style'}:self.skip+=1
    def handle_endtag(self,tag):
        if tag in {'script','style'}:self.skip=max(0,self.skip-1)
    def handle_data(self,text):
        if not self.skip:self.parts.append(text)

def main():
    by_id={r['dataset_id']:r for r in json.loads((BASE/'dataset_manifest.json').read_text())['datasets']}
    reports=[]
    checks=[
        ('C13',{'opening_date_2025_07_25':r'25 июля 2025','publication_2025_08_01':r'01 Августа 2025','operator_reports_opened':r'открыл свои двери'}),
        ('C14',{'112_rooms':r'112 номеров','airport_access_34km':r'34 км от аэропорта','rail_access_250metres':r'250 метрах от ж/д вокзала'}),
        ('C15',{'Kazan_Ekaterinburg_car_saving_gt6h':r'от Казани до Екатеринбурга более,? чем на 6 часов','freight_saving_gt4h':r'грузового больше,? чем на 4 часа','road_section_275km':r'Дюртюли – Ачит протяженностью 275 км'}),
    ]
    for did,patterns in checks:
        record=by_id[did];data=(BASE/record['raw_path']).read_bytes();parser=Visible();parser.feed(data.decode('utf-8-sig'))
        text=re.sub(r'\s+',' ',' '.join(parser.parts));matched={k:bool(re.search(v,text,re.I)) for k,v in patterns.items()}
        reports.append(dict(dataset_id=did,source_url=record['source_url'],raw_path=record['raw_path'],
                            sha256=hashlib.sha256(data).hexdigest(),retrieved_at_utc=record['retrieved_at_utc'],
                            targeted_markers=matched,status='PRIMARY_CONTEXT_MATCH_SCOPED',
                            limits='Operator statement; no paid air OD, city origins, realized use or causal market addition measured'))
        assert all(matched.values()),did
    # Native search-tool text was read by the critic; not a fabricated HTTP-byte receipt.
    native=[
        dict(dataset_id='C12',source_url=by_id['C12']['source_url'],checked_on='2026-11-09',
             method='Native web text open; publisher page displayed; crawl metadata says two months ago',
             facts_read=dict(publication_date='2026-07-22',practice_started='2026-06',total_students=15,lyulka=6,salyut=9),
             raw_byte_status='NOT_ACQUIRED_DIRECT_TLS_FAILED',
             limits='Training participation; no ticket, transport, airport choice, return date, winter recurrence or net-new RW sale'),
        dict(dataset_id='ST19_RW_NOTICE',source_url='https://flyredwings.com/en/press/news/red-wings-so-2-avgusta-nachnet-perevozit-passazhirov-izhavia-iz-ekaterinburga-v-izhevsk/',checked_on='2026-11-09',
             method='Native web text open; crawl metadata says today',
             facts_read=dict(publication_date='2026-08-01',announced_start='2026-08-02',route='SVX-IJK',august_weekdays=['Friday','Sunday'],nominal_aircraft_family='SSJ-100',prior_issuer_bookings_carried=True),
             raw_byte_status='NOT_ACQUIRED_IN_CRITIC',
             limits='Announcement and prior bookings are not flight completion, passenger counts or December schedule; regulator certificate fact independently NOT_ACQUIRED'),
    ]
    out=dict(generated_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),reports=reports,native_text_read_checks=native,
             unavailable=dict(C11='Direct TLS failed; native source open timeout; 43-person claim not independently acquired',regulator_notice='Native source open timeout; no independent certificate verification'),
             acceptance='Targeted facts about mechanisms and access only; no demand or launch acceptance')
    (BASE/'evidence/stage19_primary_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'raw_primary_pages':len(reports),'marker_checks':sum(len(r['targeted_markers'])for r in reports),'native_text_checks':len(native),'all_targeted_markers_match':True}))

if __name__=='__main__':main()
