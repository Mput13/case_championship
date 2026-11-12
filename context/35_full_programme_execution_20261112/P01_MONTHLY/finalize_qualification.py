#!/usr/bin/env python3
from pathlib import Path
import csv,json,hashlib,re
P=Path(__file__).resolve().parent;R=P/'sources_receipts';T=P/'tranches/01_qualification'
def write(name,rows,fields=None):
 with (P/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)
rows=list(csv.DictReader((T/'calibration_eligibility.csv').open()))
dates={'OMS':'2026-01-16','PEE':'2026-02-02','AER':'2026-01-20','OVB':'2025-07-20','BAX':'2026-01-13','CEK':'UNKNOWN','KJA':'2026-01-27','KUF':'2026-01-14'}
sourcekeys={'OMS':'KF_SOURCE_01','PEE':'KF_SOURCE_02','AER':'KF_SOURCE_03','OVB':'KF_SOURCE_04','BAX':'KF_SOURCE_05','CEK':'KF_SOURCE_06','KJA':'KF_SOURCE_08','KUF':'KUF_YEAR_2025'}
publishers={'OMS':'СуперОмск / пресс-служба Омского аэропорта','PEE':'В курсе.ру / Минтранс Пермского края','AER':'Коммерсантъ / Аэродинамика','OVB':'АБН 24 / аэропорт Толмачёво','BAX':'ИА Амител / Минтранс Алтайского края','CEK':'Эксперт-Урал / Миндортранс Челябинской области'}
for r in rows:
 c=r['from_iata'];r['organization']=publishers.get(c,r['organization']);k=sourcekeys[c];rec=json.loads((R/(k+'_receipt.json')).read_text());r['publication_date']=dates[c];r['live_evidence_source_id']=k;r['live_evidence_source_sha256']=rec['sha256'];r['live_evidence_url']=rec['url'];r['live_evidence_status']='PRIMARY_FETCHED' if c=='KUF' else 'SECONDARY_FETCHED';r['as_of']='2026-11-12'
 if c=='KJA':
  r['organization']='Samokatus: копия пресс-службы группы Аэрофлот';r['source_status']='CARRIER_GROUP_MIRROR_REVALIDATED';r['value_qualifier']='ROUND_PUBLISHED_100';r['publication_date']='UNKNOWN: дата 2026-01 в зеркале, точный день требует сверки';r['calibration_eligibility']='УСЛОВНО: нижняя граница сегментов всех перевозчиков только при совпадении аэропортов и направлений; не нижняя граница endpoint OD'
 elif c=='KUF':
  r['organization']='АО Международный аэропорт Курумоч / УК Аэропорты Регионов';r['source_status']='PRIMARY_UPGRADE';r['value_qualifier']='ROUND_PUBLISHED_1000';r['unit']='пассажиры на направлении аэропорта, человек; правило подсчёта прилётов/вылетов не раскрыто';r['calibration_eligibility']='УСЛОВНО: первичный годовой контроль масштаба KUF–MRV; первоначальный пробел первоисточника закрыт новым релизом';r['assumption_ids']+=';PM-A09'
 else:r['source_status']='SECONDARY_REVALIDATED'
 if c=='PEE':
  r['direction_basis']='CONFLICT: в статье «улетело», общий total называется вылетевшими; методика аэропортового счёта не получена';r['calibration_eligibility']='УСЛОВНО после проверки первичного Минтранса: численность направления сохранена; нельзя выбрать one-way/bidirectional по журналистской формулировке';r['prohibited_use']+='; не объявлять направленность установленной';r['assumption_ids']+=';PM-A10'
 if c in ['AER','CEK']:r['value_qualifier']='ROUND_PUBLISHED_10000' if c=='AER' and r['to_iata']=='MOW' else 'ROUND_PUBLISHED_1000' if c=='AER' else 'APPROX_1100000'
 if c=='BAX':r['organization']='ИА Амител со ссылкой на Минтранс Алтайского края'
 r['revision_note']='Новая живая проверка первоисточника, исходные значения и SHA сохранены' if c=='KUF' else 'Живая проверка ссылки; исходные значения и пределы granularity сохранены'
write('calibration_eligibility.csv',rows)
ass=list(csv.DictReader((T/'assumptions.csv').open()))
for a,b,c,d,e,f in [
 ('PM-A08','Не переносить профиль одного аэропорта/перевозчика на новую пару без проверки','Исследователь P01; профиль зависит от сети, сезонных рейсов, трансферов и географии','UNKNOWN: ошибка переноса; никаких весов или коэффициентов не выбрано','P05 проверяет на отложенных парах/периодах; VVO и UT — диагностические опоры, не готовые RW веса','Наблюдённые aviation ряды отдельно от tourism proxy'),
 ('PM-A09','Соотнесение названий города с аэропортом для первичных внутренних пар','Исследователь P01; Кольцово=SVX, Сочи=AER, Минеральные Воды=MRV, Курумоч=KUF','Детерминированное сопоставление названий аэропортов; MOW остаётся CITY_SYSTEM','Неправильный аэропорт меняет пару; уточнить аэропорт в первичном отчёте; MOW не распределять','Публикуемые направления остаются segment observations, не endpoint OD'),
 ('PM-A10','Направленность Пермь остаётся неустановленной','Исследователь P01; вторичная статья называет airport total вылетами','UNKNOWN: one-way или arrival+departure; коэффициент 2 не выбран','Проверить первичную таблицу Минтранса Пермского края или аэропорта; не удваивать/не делить по слову «улетело»','Сохранять исходное число с конфликтом определения'),
 ('PM-A11','Округлённые пресс-релизы не задают доверительный интервал','Исследователь P01; издатель не раскрывает правило округления','UNKNOWN: допуск округления; пороги ±500/±1000 не устанавливались','Мелкие расхождения сохраняются в reconciliation; получить точные месячные формы','Не балансировать published monthly и YTD принудительно')]:
 ass.append(dict(assumption_id=a,assumption=b,owner_reason=c,range_or_unknown=d,impact_and_how_to_refine=e,application=f))
write('assumptions.csv',ass)
# Только подтверждённые первичные сегменты. Конечные поездки ни в одной строке не установлены.
segments=[]
def add(k,oid,ori,dest,val,qual,start,finish,date,direction):
 rec=json.loads((R/(k+'_receipt.json')).read_text());segments.append(dict(observation_id=oid,origin_code=ori,destination_code=dest,destination_kind='CITY_SYSTEM' if dest=='MOW' else 'AIRPORT',period_start=start,period_end=finish,value=val,value_qualifier=qual,unit='пассажиры на направлении аэропорта',granularity='airport_pair_segments',direction_basis=direction,carrier_scope='все перевозчики в совокупности аэропорта по релизу',endpoint_od_eligible='НЕТ: начальная и конечная точки поездки не установлены',source_id=k,source_url=rec['url'],source_sha256=rec['sha256'],publication_date=date,as_of='2026-11-12',source_row_id=k+'#'+oid,assumption_ids='PM-A01;PM-A02;PM-A09;PM-A11'))
for dest,val,qual in [('MOW',1300000,'ROUND_PUBLISHED_100000'),('AER',325000,'ROUND_PUBLISHED_1000'),('LED',492000,'ROUND_PUBLISHED_1000'),('KGD',47800,'ROUND_PUBLISHED_100'),('MRV',47000,'ROUND_PUBLISHED_1000')]:add('KUF_YEAR_2025','KUF2025-'+dest,'KUF',dest,val,qual,'2025-01-01','2025-12-31','2026-01-14','UNKNOWN: направление прилётов/вылетов не раскрыто')
add('SVX_MONTH_202501','SVX202501-AER','SVX','AER',49000,'GT','2025-01-01','2025-01-31','2025-02-07','в/из курорта; оба направления по тексту')
add('SVX_MONTH_202501','SVX202501-MRV','SVX','MRV',16000,'APPROX','2025-01-01','2025-01-31','2025-02-07','SVX–MRV–SVX по тексту; сквозная поездка не установлена')
write('airport_pair_segment_observations.csv',segments)
(P/'endpoint_od_gap.md').write_text('''# Пробел конечных OD

В `endpoint_od_observations.csv` нет подтверждённых строк конечных авиационных поездок. В файле сохранён заголовок, числовые нули не подставлены.

37 закреплённых известных потоков и 7 новых первичных наблюдений направлений описывают аэропортовые/перевозочные сегменты, регион или часть перевозчиков. Наличие двух аэропортов в названии маршрута само по себе не определяет конечную поездку пассажира: он мог прибыть на первый аэропорт пересадкой либо продолжить путь из второго.

Допустимые границы: после установления обоих направлений и одинакового периода число перевезённых прямых конечных поездок между парой не превышает соответствующее число пассажирских сегментов. Пассажиры отдельной группы перевозчиков могут задавать нижнюю границу **всех сегментов** на той же паре. Эти соотношения не задают конечный OD через другие узлы, латентный спрос или долю, которую получит Red Wings.

Для прямого fit P05 нужны маршрутные продажи/билеты с начальными и конечными аэропортами, периодом, перевозчиком, правилом пересадок и двунаправленным либо направленным счётом. Ни один коэффициент перевода airport total → endpoint OD здесь не выбран. ЕМИСС 62073 остаётся статистикой размещений, а не авиационными поездками.
''')
print('qualification rows',len(rows),'primary segments',len(segments),'assumptions',len(ass))
