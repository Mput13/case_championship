"""Pin only P03 inputs; fetch public primary sources without cookies or browser state."""
import concurrent.futures, csv, hashlib, json, re, subprocess, urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLAN = 'b4d2ddf690440eb5cd051839cc263cf16b364ca4'
AUTHOR = 'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6'
FIVE = 'c18f7640ea36647a05b39089e5293f22dd009f63'

class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.skip=0
    def handle_starttag(self, tag, attrs):
        if tag in ['script','style','noscript']: self.skip+=1
        if tag in ['p','div','br','li','tr','h1','h2','h3','td','th']: self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in ['script','style','noscript']: self.skip=max(0,self.skip-1)
    def handle_data(self, data):
        if not self.skip: self.parts.append(data)
    def get(self):
        return '\n'.join(x for x in (re.sub(r'\s+',' ',s).strip() for s in ''.join(self.parts).splitlines()) if x)+'\n'

URLS = [
 ('RW-FLEET','https://flyredwings.com/about/park/'),
 ('RW-WINTER','https://flyredwings.com/press/news/red-wings-pereshla-na-osenne-zimnee-raspisanie-poletov/'),
 ('RW-ZIA-MRO','https://flyredwings.com/press/news/red-wings-otkryla-angar-texnicheskogo-obsluzhivaniya-vozdushnyx-sudov-v-aeroportu-zhukovskij/'),
 ('RW-SVX-MRO','https://flyredwings.com/press/news/pervaya-linejnaya-stancziya-aviakompanii-red-vings/'),
 ('RW-TU-HANDOVER','https://flyredwings.com/en/press/news/aviakompaniya-red-wings-popolnila-park-samoletom-tu-214/'),
 ('FAVT-TU-ENTRY','https://special.favt.gov.ru/novosti-novosti/?id=10750'),
 ('GOJ-MRO','https://ar-goj.ru/about/news/volga-avia-nachala-provodit-tekhnicheskoe-obsluzhivanie-samo/'),
 ('GOJ-TECH','https://ar-goj.ru/partners/airlines/airport/'),
 ('GOJ-TERMS','https://ar-goj.ru/partners/airlines/koordinatsiya-raspisaniya/'),
 ('GSV-TECH','https://ar-gsv.ru/partners/airlines/airport/'),
 ('KUF-TECH','https://ar-kuf.ru/partners/airlines/airport/'),
 ('KUF-TERMS','https://ar-kuf.ru/partners/airlines/koordinatsiya-raspisaniya/'),
 ('KUF-MRO','https://special.favt.gov.ru/posesheniya-regionov/?id=18097'),
 ('REN-TECH','https://ar-ren.ru/partners/airlines/airport/'),
 ('OMS-MRO','https://www.aeroomsk.ru/ob-aeroporte/press-tsentr/novosti/207/'),
 ('UFA-TECH','https://www.airportufa.ru/partners/airlines/specifications/'),
 ('UFA-CERT','https://www.airportufa.ru/partners/airlines/certification/'),
 ('UFA-GENERAL','https://www.airportufa.ru/about/general/'),
 ('TJM-MRO-JAN','https://yamalaero.ru/about/news/Yamal-Airlines-has-introduced-new-hangar-complex/'),
 ('TJM-MRO-SEP','https://yamalaero.ru/about/news/dmitriy-artyukhov-anton-alikhanov-i-aleksandr-moor-visited-the-new-aviation-hangar-Yamal-Airlines/'),
 ('TJM-TERMS','https://tjmport.ru/partners/airlines/documents/'),
 ('YAK-SJ100','https://yakovlev.ru/products/sj-100/'),
 ('UAC-SSJ','https://www.uacrussia.ru/ru/DDoS01/793e7e55/ru/superjet/'),
 ('UEC-PD8','https://www.uecrus.com/press/noveyshiy-aviatsionnyy-dvigatel-pd-8-dlya-superdzheta-poluchil-sertifikat-tipa/'),
 ('FAVT-PD8','https://special.favt.gov.ru/novosti-novosti/?id=18741'),
 ('FAVT-AOC','https://www.favt.gov.ru/dejatelnost-aviakompanii-reestr-komercheskie-perevozki/'),
 ('LAW381-OFFICIAL','https://publication.pravo.gov.ru/document/0001202511280038'),
 ('LAW381-ROSTRUD','https://xn--80akibcicpdbetz7e2g.xn--p1ai/reminder/145'),
 ('LAW381-REGISTERED-PDF','https://minjust.consultant.ru/files/56679'),
 ('TU214-MOD','https://rostec.ru/en/media/news/the-tu-214-with-domestically-made-systems-received-the-approval-of-a-major-modification/'),
 ('TU214-ANNOUNCEMENT','https://www.interfax.ru/russia/1098088'),
]

def pin():
    specs={PLAN:[f'context/34_full_programme_plan_20261112/{x}' for x in ['common_spec.json','requirements.csv','method_map.csv','variant_research_plan.json','city_research_seed.csv','work_packages.json']],
           AUTHOR:['src/network_model.py','src/rules.py','data/manual/airport_tech.csv','data/manual/rw_routes_now.csv','data/manual/closed_airports.csv','data/assumptions/bases.csv','data/assumptions/network.csv','data/processed/network_routes.csv','data/processed/network_summary.csv','docs/17_fleet_range_maintenance_time.md','docs/20_fleet_deliveries_evidence.md','context/11_practical_screening/sources.json','context/11_practical_screening/city_matrix.csv'],
           FIVE:[f'context/33_five_city_reassessment_20261112/cities/{c}/{f}' for c in ['TJM','CEK','PEE','UFA','GOJ'] for f in ['sources.csv','features.csv','dossier.md']]}
    records=[]
    for commit,paths in specs.items():
        for path in paths:
            b=subprocess.check_output(['git','show',f'{commit}:{path}'])
            dest=ROOT/'inputs'/commit[:8]/path
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
            records.append(dict(commit=commit,path=path,git_blob=subprocess.check_output(['git','rev-parse',f'{commit}:{path}'],text=True).strip(),sha256=hashlib.sha256(b).hexdigest(),local_path=str(dest.relative_to(ROOT)),kind='pinned_prior_evidence_not_new_collection'))
    (ROOT/'input_manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')

def fetch(item):
    sid,url=item; now=datetime.now(timezone.utc).isoformat()
    rec=dict(source_id=sid,url=url,retrieved_at=now,collection='new_http_fetch_of_public_source',source_role='secondary_direct_named_statement' if sid=='TU214-ANNOUNCEMENT' else 'primary',http_status='',final_url='',saved_path='',sha256='',error='')
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 research source capture'})
        with urllib.request.urlopen(req,timeout=22) as r:
            b=r.read(5_000_001);rec['http_status']=r.status;rec['final_url']=r.url;ct=r.headers.get('Content-Type','')
            if len(b)>5_000_000: raise ValueError('Source exceeds 5MB budget')
            if b.startswith(b'%PDF'):
                path=ROOT/'sources'/f'{sid}.pdf';path.write_bytes(b)
                subprocess.run(['pdftotext','-layout',str(path),str(path.with_suffix('.txt'))],check=True)
            else:
                charset=r.headers.get_content_charset() or 'utf-8'
                p=Text();p.feed(b.decode(charset,errors='replace'));text=p.get()
                # Never persist markup, hidden inputs, cookies, scripts or tokens.
                path=ROOT/'sources'/f'{sid}.txt';path.write_text(text)
            rec['saved_path']=str(path.relative_to(ROOT));rec['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            rec['response_bytes']=len(b);rec['content_type']=ct
            rec['status']='captured_requires_semantic_check'
    except Exception as e:
        rec['status']='fetch_failed';rec['error']=f'{type(e).__name__}: {e}'
    return rec

if __name__=='__main__':
    pin();(ROOT/'sources').mkdir(exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool: records=list(pool.map(fetch,URLS))
    (ROOT/'fetch_receipts.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({r['source_id']:r['status'] for r in records},ensure_ascii=False))
