#!/usr/bin/env python3
"""Публичные первичные страницы; никаких бронирований и UI."""
from pathlib import Path
import concurrent.futures, datetime, hashlib, json, re, urllib.request
from html import unescape

ROOT=Path(__file__).resolve().parent
SOURCES=[
 ('MOW-S01','Red Wings','2023-02-02','2023-02; не автоматический статус 2027–2028','аэропорт/вид ТО','https://flyredwings.com/press/news/red-wings-otkryla-angar-texnicheskogo-obsluzhivaniya-vozdushnyx-sudov-v-aeroportu-zhukovskij/','Исторический первичный статус ZIA как базы SSJ100 и ангара A-check; 2 места в ангаре не 2 свободных самолёта. C-check во втором полугодии — план. Текущие сертификат/слоты/договор и SJ100_PD8 UNKNOWN.'),
 ('MOW-S02','Red Wings','2026-08-10','зима 2026/27, старт 2026-10-26','аэропорт/маршрут/дни недели/типовое семейство','https://flyredwings.com/press/news/red-wings-prodlila-programmu-poletov-iz-moskvy-v-gruziyu/','ZIA: Тбилиси ежедневно, Батуми вт/пт/вс, вылет 08:10; SSJ100 и Ту204/214 названы совместно. Конкретный борт/тип на дату не закреплён. Сохранить продажи KEEP.'),
 ('MOW-S03','Red Wings','2026-04-16','с 2026-04-17; не гарантия будущего исполнения','аэропорт/маршрут/семейство/частота','https://flyredwings.com/press/news/red-wings-vozobnovlyaet-polety-v-izrail/','ZIA–TLV ежедневно на Ту214, заявлено 5ч45. Самолёт этого задания не ресурс SSJ. 140 тыс. пассажиров в 2025 относится к сети Израиля RW, не одному московскому аэропорту.'),
 ('MOW-S04','Red Wings','2025-06-26','с 2025-07-25 ежедневно; с 2025-09-08 пт/сб/вс, конец UNKNOWN','направление/частота/объявленная длительность','https://flyredwings.com/press/news/red-wings-otkryla-ezhednevnye-rejsy-iz-moskvy-v-kaliningrad/','DME–KGD объявлен; 2ч50. Отдельный тип и борт на дату не указан. Не доказательство собственного свободного SSJ в ноябре 2026.'),
 ('MOW-S05','Red Wings','2025-05-15','начало чартерной программы 2025','аэропорт/чартерный продукт','https://flyredwings.com/press/news/red-wings-nachala-letat-iz-moskvy-v-nyachang/','DME–CXR чартер с туроператорами, широкофюзеляжный самолёт; не SSJ inventory. Доход/обязательства партнёрского продукта сохранить в KEEP.'),
 ('MOW-S06','Red Wings','UNKNOWN; живая справочная страница','as_of 2026-11-12','представительство/режим работы','https://flyredwings.com/contacts/representatives/','DME круглосуточно; ZIA во время обслуживания рейса. Это представительство, не расписание, MRO контракт или свободный парк.'),
 ('MOW-S07','Red Wings','2026-10-27','осень/зима 2026–2027','сеть/опорные города','https://flyredwings.com/press/news/red-wings-pereshla-na-osenne-zimnee-raspisanie-poletov/','Москва названа на уровне города. Без отдельной привязки не распределять ресурс между DME/ZIA/VKO/SVO.'),
 ('MOW-S08','Red Wings','2026-09-02','с 2026-09-01','маркетинговый и фактический перевозчик/стыковка','https://flyredwings.com/press/news/red-wings-i-belavia-rasshiryayut-marshrutnuyu-set-v-ramkax-kod-sheringa/','B2 выполняет Беларусь на названных линиях; RW продаёт комбинированные продукты. Это общий пример operator/marketing split, не московская физическая вместимость.'),
 ('MOW-S09','Red Wings','2025-09-24/2025-10-01; уточнить по документу','редакция правил на сайте as_of 2026-11-12','правила/определения','https://flyredwings.com/regulations/','Код-шеринг различает оператора и маркетингового партнёра. WZ в табло не даёт автоматически свой самолёт и исчезновение маркетингового дохода.'),
 ('MOW-S10','Red Wings','2025-09-16','продажа 16–18.09.2025; перевозка 23.09.2025–28.03.2026','архивная акция/перечень пар','https://flyredwings.com/autumn-sale-2025/','MCX–VOG был собственным продаваемым RW направлением в объявленной акции. Частота/тип/факт выполнения и весь 2026 из этого не следуют.'),
 ('MOW-S11','Red Wings','2025-11-11','продажа 11–13.11.2025; перевозка с 18.11.2025 в глубину открытых продаж','архивная акция/перечень пар','https://flyredwings.com/november-sale-2025/','MCX–VOG — отдельный исторический продаваемый продукт. Тариф акции требует RT; текущая цена/остаток кресел UNKNOWN.'),
 ('MOW-S12','Азимут','2022-03-31','объявленная программа 2022','ordered legs/пункты остановок','https://azimuth.ru/ru/news/aviakompaniya-azimut-vypolnila-pervyy-reys-mineralnye-vody-yaroslavl-arhangelsk','Исторический MRV–IAR–ARH, а не доказанный nonstop MRV–ARH. Не переносить 2022 в текущий календарь.'),
 ('MOW-S13','Red Wings','UNKNOWN; справочная страница','as_of 2026-11-12, не конкретный рейс','аэропорт/маркетинговая длительность','https://flyredwings.com/directions/moscow/kaliningrad/','Физические пункты DME/KGD; справочные 2ч05 конфликтуют с новостью 2025 2ч50. Для блока не использовать маркетинговую карточку.'),
 ('MOW-S14','Росавиация','2026-05-15','перечень субсидируемых маршрутов 2026, приказ 261-П','строка программы поддержки/перевозчик/тип/период','https://favt.gov.ru/dejatelnost-organizacija-perevozok-subsidirovanie-vozdushnyh-perevozok-regionalnye-perevozki/','Реестр/приказ — правовое основание контекста конкурента, не факт выполнения и не присуждённая поддержка RW 2027–2028.'),
 ('MOW-S15','Red Wings','UNKNOWN; справочная страница','as_of 2026-11-12','доступ к физическому аэропорту','https://flyredwings.com/zhukovsky-airport/','Путь до ZIA нужен в P05 вместе с доступом к альтернативным московским аэропортам; нельзя считать весь MOW одним одинаковым терминалом.'),
 ('MOW-S16','Домодедово','2026-08-24','01.06–23.08.2026','аэропорт/направление/рост к прошлому году','https://dt.dme.ru/book/news/samye-bystrorastuschie-zarubezhnye-napravleniya-leta-2026-goda-iz-domodedovo/','Первичное подтверждение DME–CXR RW летом 2026; рост направления не OD или маржа SSJ.'),
]

def fetch(s):
 sid,org,pub,period,grain,url,coverage=s
 rec=dict(source_id=sid,organization=org,url=url,publication_date=pub,period=period,unit='см. гранулярность; денежные величины не извлекаются',granularity=grain,coverage=coverage,lower='UNKNOWN',upper='UNKNOWN',retrieved_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='UNKNOWN',http_status=None,collection='публичный HTTP GET, без браузера',year_2027_2028_use='только обоснование сценария; не продление факта')
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 research source verification'})
  with urllib.request.urlopen(req,timeout=25) as r: b=r.read(3_000_001);rec.update(http_status=r.status,final_url=r.url)
  if len(b)>3_000_000:raise ValueError('лимит источника 3 MB')
  rec['response_sha256']=hashlib.sha256(b).hexdigest();rec['response_bytes']=len(b)
  h=b.decode('utf-8',errors='replace')
  h=re.sub(r'<(script|style)\b.*?</\1>','',h,flags=re.S|re.I)
  text=unescape(re.sub('<[^>]+>','\n',h));text=re.sub(r'[ \t\xa0]+',' ',text);text=re.sub(r'\n\s*\n+','\n',text)
  start=text.find('\n'+re.sub(r'<[^>]+>','',re.search(r'<h1[^>]*>(.*?)</h1>',h,re.S|re.I).group(1)).strip()) if re.search(r'<h1[^>]*>(.*?)</h1>',h,re.S|re.I) else -1
  if start>=0:text=text[start:]
  for marker in ['Перейти ко всем новостям','Go to all news']:
   end=text.find(marker)
   if end>100:text=text[:end]
  path=ROOT/'sources'/f'{sid}.txt';path.write_text(text.strip()+'\n')
  rec.update(saved_path=str(path.relative_to(ROOT)),saved_text_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),status='HTTP_OK_TEXT_SAVED; содержательная оценка в sources_review.json')
 except Exception as e:rec.update(status='FETCH_FAILED_NOT_ABSENCE',error=f'{type(e).__name__}: {e}')
 return rec

if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:rows=list(pool.map(fetch,SOURCES))
 (ROOT/'sources_registry.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps([{k:r.get(k) for k in ['source_id','http_status','status','error','saved_text_sha256']} for r in rows],ensure_ascii=False,indent=2))
