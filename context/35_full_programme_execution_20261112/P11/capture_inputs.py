#!/usr/bin/env python3
"""Read exact Git objects and public information pages; writes only this package."""
import csv, hashlib, json, subprocess, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OLD = 'd48b4a4f86de29aa968665f1601b785bd1824c54'
PIN = '65cab12d2eae49dc91d1f77dd4860bc9bd7e20d2'
P06 = '982f13d9b6c378ed9581125ecc5c40f17dade6a3'

def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')

def sha(data):
    return hashlib.sha256(data).hexdigest()

class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.skip = 0; self.out = []
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style','noscript'): self.skip += 1
        if not self.skip and tag in ('p','div','br','li','tr','h1','h2','h3','h4'): self.out.append('\n')
    def handle_endtag(self, tag):
        if tag in ('script','style','noscript') and self.skip: self.skip -= 1
        if not self.skip and tag in ('p','div','li','tr','td','th','h1','h2','h3','h4'): self.out.append('\n')
    def handle_data(self, data):
        if not self.skip: self.out.append(data)

PINS = [
    ('HIST_CARDS',PIN,'context/28_evening_run_20261110/integration/digital_growth/cards.md','inputs/historical_cards.md'),
    ('HIST_CORRECTION',PIN,'context/28_evening_run_20261110/integration/digital_growth/correction.json','inputs/historical_correction.json'),
    ('HIST_OBS',OLD,'context/28_evening_run_20261110/digital_growth/evidence/browser_observations.json','inputs/historical_observations.json'),
    ('HIST_PARAMS',OLD,'context/28_evening_run_20261110/digital_growth/parameters.json','inputs/historical_parameters.json'),
    ('HIST_SOURCES',OLD,'context/28_evening_run_20261110/digital_growth/sources.csv','inputs/historical_sources.csv'),
    ('HIST_D01_MODAL',OLD,'context/28_evening_run_20261110/digital_growth/illustrations/D01_seat_skip_confirmation.png','evidence/historical/D01_seat_skip_confirmation.png'),
    ('HIST_D01_BOUNDARY',OLD,'context/28_evening_run_20261110/digital_growth/illustrations/D01_passenger_data_boundary.png','evidence/historical/D01_passenger_data_boundary.png'),
    ('P06_CONTRACT',P06,'context/35_full_programme_execution_20261112/P06/producer_contract.json','inputs/P06_producer_contract.json'),
    ('PLAN_REQ',PIN,'context/34_full_programme_plan_20261112/requirements.csv','inputs/plan_requirements.csv'),
    ('PLAN_SPEC',PIN,'context/34_full_programme_plan_20261112/common_spec.json','inputs/plan_common_spec.json'),
]

PAGES = [
    ('RW_HOME','https://flyredwings.com/'),
    ('RW_HOW','https://flyredwings.com/how-to-book/'),
    ('RW_FARES','https://flyredwings.com/fares/'),
    ('RW_SERVICES','https://flyredwings.com/services/'),
    ('RW_BAGGAGE','https://flyredwings.com/baggage/dopolnitelnyj-bagazh/'),
    ('RW_BAGFAQ','https://flyredwings.com/faq/uslugi-na-bortu/dopolnitelnye-uslugi/kak-kupit-dopolnitelnyj-bagazh/'),
    ('RW_REFUND','https://flyredwings.com/change-and-refund/'),
    ('RW_RETURNABILITY','https://flyredwings.com/services/vozvratnost-bileta/'),
    ('RW_FAQ','https://flyredwings.com/faq/'),
    ('RW_PREP','https://flyredwings.com/faq/podgotovka-k-poletu/'),
    ('RW_CHECKIN','https://flyredwings.com/check-in-rules/'),
    ('RW_SEAT','https://flyredwings.com/services/choice-place/'),
    ('RW_CHANGE','https://flyredwings.com/services/change/'),
]

def capture(item):
    source_id, url = item
    now = datetime.now(timezone.utc).isoformat()
    row = dict(source_id=source_id, url=url, organization='АО «Ред Вингс»', retrieved_at_utc=now,
               publication_date=None, period='Публичные условия на момент получения 2026-11-12; не договор конкретного билета',
               unit='условие/публичный путь; RUB для опубликованных цен', granularity='страница',
               coverage='Открытая русская версия, без реального билета и без проверки исполнения', method='urllib HTTPS GET')
    try:
        request = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read(); row.update(http_status=response.status, final_url=response.url,
                    last_modified=response.headers.get('Last-Modified'))
        path = ROOT / 'sources' / (source_id + '.html'); path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
        parser=Text(); parser.feed(data.decode('utf-8','replace'))
        lines=[' '.join(x.split()) for x in ''.join(parser.out).splitlines() if x.strip()]
        txt='\n'.join(f'{i:04d}\t{s}' for i,s in enumerate(lines,1))+'\n'
        textpath=path.with_suffix('.txt'); textpath.write_text(txt)
        row.update(status='PRIMARY_PUBLIC_CAPTURE', path=str(path.relative_to(ROOT)), sha256=sha(data),
                text_path=str(textpath.relative_to(ROOT)),text_sha256=sha(txt.encode()), text_rows=len(lines))
    except Exception as exc:
        row.update(status='FETCH_ERROR',error=f'{type(exc).__name__}: {exc}')
    return row

def main():
    pins=[]
    for source_id,commit,path,out in PINS:
        data=subprocess.check_output(['git','show',f'{commit}:{path}'])
        target=ROOT/out; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
        pins.append(dict(source_id=source_id,commit=commit,source_path=path,local_path=out,sha256=sha(data),
                        git_blob=subprocess.check_output(['git','rev-parse',f'{commit}:{path}']).decode().strip(),
                        status='EXACT_GIT_OBJECT',coverage='Только выбранный файл; прежние наблюдения не выданы за новые'))
    dump(ROOT/'input_manifest.json',dict(pinned_at_utc=datetime.now(timezone.utc).isoformat(),pins=pins,
          scope='P11 only; no city market/fleet table used; P02/P03 not accepted as annual physical inventory'))
    with ThreadPoolExecutor(max_workers=6) as pool: rows=list(pool.map(capture,PAGES))
    dump(ROOT/'sources/registry.json',rows)
    print(json.dumps([dict(source_id=r['source_id'],status=r['status'],rows=r.get('text_rows'),error=r.get('error')) for r in rows],ensure_ascii=False,indent=2))

if __name__=='__main__': main()
