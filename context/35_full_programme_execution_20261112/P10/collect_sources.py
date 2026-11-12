#!/usr/bin/env python3
"""Capture public sources and exact Git inputs. Writes only inside P10."""
import concurrent.futures
import csv
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import requests

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
SOURCES = [
    ('RW25','Red Wings','2026-01-28','2025-01-01/2025-12-31','company/year','https://flyredwings.com/en/press/news/red-wings-perevezla-za-god-na-rossijskix-samoletax-2-mln-passazhirov-i-2-sovy/'),
    ('RW24','Red Wings','2025-04-09','2024-01-01/2024-12-31','company/year','https://flyredwings.com/en/press/news/red-wings-rostexa-pobedila-v-dvux-nominacziyax-premii-krylya-rossii/'),
    ('RW26H1','Red Wings','2026-07-20','2026-01-01/2026-07-20; comparison H1 not exact cutoff','Russian-type subset; partial year','https://flyredwings.com/press/news/red-wings-perevezla-pochti-million-passazhirov-na-rossijskix-lajnerax/'),
    ('RW_FLEET','Red Wings','UNKNOWN; undated','as_of retrieval','type; listed count; seats','https://flyredwings.com/about/park/'),
    ('RW_VIETNAM','Red Wings','2026-05-13','2025-05/2026-05 rolling12months','charter destination; not annual total','https://flyredwings.com/press/news/red-wings-perevezla-50-tysyach-passazhirov-vo-vetnam-za-god/'),
    ('RW_ISRAEL','Red Wings','2026-04-16','2025 annual; 2026-04 offer','country traffic; flight programme','https://flyredwings.com/en/press/news/red-wings-vozobnovlyaet-polety-v-izrail/'),
    ('FAVT25','Росавиация','2026-01-30','2025-01-01/2025-12-31','national carriers/year','https://www.favt.gov.ru/novosti-novosti?id=17763&version=print'),
    ('AF25','ПАО Аэрофлот; собственный релиз на АвиаПорт','2026-01-14','2025-01-01/2025-12-31','individual airline and group separately','https://www.aviaport.ru/news/gruppa-aeroflot-obyavlyaet-operatsionnye-rezultaty-za-dekabr-2025-goda/'),
    ('DP25','АК Победа; собственный релиз на АвиаПорт','2026-01-16','2025-01-01/2025-12-31','individual airline/year','https://www.aviaport.ru/news/pobeda-perevezla-13-8-mln-klientov-po-itogam-2025-goda/'),
    ('S725','АО Авиакомпания Сибирь','UNKNOWN; undated','2025-01-01/2025-12-31','individual airline/year','https://www.s7.ru/ru/pages/o-kompanii/'),
    ('FV25','АО Авиакомпания Россия','2026-02-11','2025 annual; January2026 separate','individual airline/year','https://www.rossiya-airlines.ru/about/news/rossiya_podvela_itogi_perevozok_v_yanvare_/?special_version=N'),
    ('UT25','ЮТэйр','2026-04-30','2025-01-01/2025-12-31','airline; group; helicopters separate','https://info.utair.ru/tpost/gruppa-yuteyr-vypustila-otchyetnost-po-msfo-za-2025-god'),
    ('AF26_10M','ПАО Аэрофлот; собственный релиз на АвиаПорт','2026-11-12; verify body','2026-01-01/2026-10-31','individual airline; group; 10months','https://www.aviaport.ru/news/gruppa-aeroflot-obyavlyaet-operatsionnye-rezultaty-za-oktyabr-2026-goda/'),
    ('AF_IR','ПАО Аэрофлот','UNKNOWN; current index','as_of retrieval','official IR index','https://ir.aeroflot.ru/ru/reporting/traffic-statistics/'),
    ('STAT17','Росстат','2017-12-29 order887; historical official methodology','methodology; not confirmed current2026 revision','reporting flight vs stage; under2 excluded','https://rosstat.gov.ru/free_doc/new_site/business/trans-sv/metod-transp.pdf'),
    ('STAT_TRANSPORT','Росстат','UNKNOWN; current index','as_of retrieval','current methodology index','https://rosstat.gov.ru/statistics/transport'),
    ('STAT_FORM_HIST','Краснодарстат','2013 order312; historical','historical form; not current authority','reporting carrier by ATC flight number; flight not stage','https://23.rosstat.gov.ru/storage/mediabank/10-GA.htm'),
    ('YAK_SJ100','ПАО Яковлев','UNKNOWN; undated','as_of retrieval','SJ100 PD8 manufacturer marketing','https://yakovlev.ru/products/sj-100/'),
    ('ROSTEC_SSJ_UTIL','Ростех','2023 historical; verify body','2023 partial/peak utilisation description','SSJ100 monthly example; not SJ100 economics','https://rostec.ru/media/news/komanda-na-vzlet-o-statuse-rossiyskoy-aviaprogrammy/'),
    ('RW_NEW_CEO','Red Wings','2026-10; verify body','as_of publication','20SSJ; expected new deliveries2027, no annual count','https://flyredwings.com/press/news/igor-ivliev-naznachen-generalnym-direktorom-red-wings/'),
    ('TU11','Интерфакс; высказывание главы ОАК','2026-06-25','announced from2027; not calendar','11aircraft announced batch, secondary direct statement','https://www.interfax.ru/russia/1098088'),
    ('S7_TU_PLAN','ОАК','2026-02; verify body','announced from2029; not delivery fact','100Tu214 memorandum; competitor long-term constraint','https://uacrussia.ru/ru/DDoS01/82d1f7e3/press-center/news/oak-s7-i-gtlk-podpisali-memorandum-o-postavke-100-samoletov-tu-214-?PAGEN_10=15'),
]
PINS = [
 ('BASE','dceadc98f9a293d7530cb7bc50ca4411a95aa4b6','src/network_model.py',False),
 ('FIVE','c18f7640ea36647a05b39089e5293f22dd009f63','context/33_five_city_reassessment_20261112/common_economics/report.md',False),
 ('PLAN','b7d74e67dd6c603db049b1915b1afec987e3b458','context/34_full_programme_plan_20261112/common_spec.json',True),
 ('P00R','b7d74e67dd6c603db049b1915b1afec987e3b458','context/35_full_programme_execution_20261112/P00R/contract_addendum.json',True),
 ('P02','d9486f113f074c185a94bcc5c0afeef12ea3574f','context/35_full_programme_execution_20261112/P02/output_manifest.json',True),
 ('P03_TYPES','79dc698b99dfe866886d32376ed388e85bdd039c','context/35_full_programme_execution_20261112/P03/aircraft_type_parameters.csv',True),
 ('P03_DELIVERIES','79dc698b99dfe866886d32376ed388e85bdd039c','context/35_full_programme_execution_20261112/P03/diagnostic_delivery_events.csv',True),
 ('P03','79dc698b99dfe866886d32376ed388e85bdd039c','context/35_full_programme_execution_20261112/P03/handoff.json',True),
 ('P04','620a0ac4bb11763319c4227485f6a3996b91d367','context/35_full_programme_execution_20261112/P04/thresholds.csv',True),
 ('P06','982f13d9b6c378ed9581125ecc5c40f17dade6a3','context/35_full_programme_execution_20261112/P06/producer_contract.json',True),
 ('P06_README','982f13d9b6c378ed9581125ecc5c40f17dade6a3','context/35_full_programme_execution_20261112/P06/README.md',True),
 ('OLD_DIGITAL_PARAMETERS','d48b4a4f86de29aa968665f1601b785bd1824c54','context/28_evening_run_20261110/digital_growth/parameters.json',True),
 ('OLD_DIGITAL_CARRIERS','d48b4a4f86de29aa968665f1601b785bd1824c54','context/28_evening_run_20261110/digital_growth/annual_carriers.csv',True),
 ('OLD_DIGITAL_SOURCES','d48b4a4f86de29aa968665f1601b785bd1824c54','context/28_evening_run_20261110/digital_growth/sources.csv',True),
 ('OLD_DIGITAL_HANDOFF','d48b4a4f86de29aa968665f1601b785bd1824c54','context/28_evening_run_20261110/digital_growth/handoff.md',True),
 ('OLD_STRATEGY_BRIDGE','65cab12d2eae49dc91d1f77dd4860bc9bd7e20d2','context/28_evening_run_20261110/integration/dashboard_handoff/5101302f/strategy/whole_company_bridge.csv',True),
]

class Plain(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'): self.hidden+=1
        if tag in ('p','div','br','tr','td','h1','h2','h3','li','section'): self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in ('script','style'): self.hidden=max(0,self.hidden-1)
    def handle_data(self,data):
        if not self.hidden: self.parts.append(data)

def capture(row):
    sid,org,pub,period,grain,url=row
    out={'source_id':sid,'organization':org,'url':url,'publication_date':pub,'period':period,'granularity':grain,'retrieved_at':dt.datetime.now(dt.timezone.utc).isoformat(),'http_status':None,'fetch_status':'UNKNOWN','error':None}
    try:
        r=requests.get(url,timeout=(12,25),headers={'User-Agent':'Mozilla/5.0 research-source-capture'},allow_redirects=True)
        out.update(http_status=r.status_code,final_url=r.url,content_type=r.headers.get('Content-Type'))
        out['body_sha256']=hashlib.sha256(r.content).hexdigest(); out['bytes']=len(r.content)
        if r.status_code!=200: out.update(fetch_status='HTTP_ERROR',error=f'HTTP {r.status_code}'); return out
        suffix='.pdf' if r.content[:4]==b'%PDF' else '.html'
        p=ROOT/'sources'/f'{sid}{suffix}'; p.write_bytes(r.content); out['raw_path']=str(p.relative_to(ROOT))
        if suffix=='.pdf':
            text_path=p.with_suffix('.txt'); c=subprocess.run(['pdftotext','-layout',str(p),str(text_path)],capture_output=True,text=True); out['pdf_extract_error']=c.stderr if c.returncode else None
        else:
            r.encoding=r.apparent_encoding or 'utf-8'; parser=Plain(); parser.feed(r.text)
            txt='\n'.join(line.strip() for line in ''.join(parser.parts).splitlines() if line.strip())
            text_path=p.with_suffix('.txt'); text_path.write_text(txt,encoding='utf-8')
        out.update(fetch_status='CAPTURED_REQUIRES_SEMANTIC_QUALIFICATION',text_path=str(text_path.relative_to(ROOT)),text_sha256=hashlib.sha256(text_path.read_bytes()).hexdigest())
    except Exception as e: out.update(fetch_status='FETCH_FAILED',error=f'{type(e).__name__}: {e}')
    return out

def main():
    (ROOT/'sources').mkdir(exist_ok=True); (ROOT/'inputs').mkdir(exist_ok=True)
    pins=[]
    for key,sha,path,save in PINS:
        b=subprocess.check_output(['git','show',f'{sha}:{path}'],cwd=REPO)
        row={'input_id':key,'commit':sha,'source_path':path,'source_blob':subprocess.check_output(['git','rev-parse',f'{sha}:{path}'],cwd=REPO,text=True).strip(),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'read_method':'git show exact commit; no moving branch','saved_path':None}
        if save:
            p=ROOT/'inputs'/f'{key}_{Path(path).name}'; p.write_bytes(b); row['saved_path']=str(p.relative_to(ROOT))
        pins.append(row)
    (ROOT/'input_manifest.json').write_text(json.dumps(pins,ensure_ascii=False,indent=2)+'\n')
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool: receipts=list(pool.map(capture,SOURCES))
    (ROOT/'fetch_receipts.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([{'id':r['source_id'],'status':r['fetch_status'],'http':r.get('http_status'),'bytes':r.get('bytes'),'error':r.get('error')} for r in receipts],ensure_ascii=False,indent=2))

if __name__=='__main__': main()
