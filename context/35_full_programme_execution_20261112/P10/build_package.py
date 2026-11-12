#!/usr/bin/env python3
"""P10: capacity and ranking diagnostics, NOT a parallel demand/cash model."""
import calendar
import csv
from datetime import date
import hashlib
import json
import math
from pathlib import Path

R=Path(__file__).resolve().parent
VERSION='P10-1.0-20261112'
ASOF='2026-11-12'

def jwrite(name,obj):
    (R/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def table(name,rows):
    fields=list(dict.fromkeys(k for x in rows for k in x))
    with (R/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def readcsv(name):
    with (R/name).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))

def sha(path):return hashlib.sha256((R/path).read_bytes()).hexdigest()

def loc(source,needle,stop=None):
    lines=(R/source).read_text(encoding='utf-8').splitlines()
    indices=[i+1 for i,l in enumerate(lines) if needle in l]
    if not indices:raise ValueError((source,needle))
    start=indices[0];end=start
    if stop:
        end=next(i+1 for i,l in enumerate(lines) if i+1>=start and stop in l)
    return {'source_text_path':source,'source_text_sha256':sha(source),'source_row_id':f'L{start}-L{end}','source_row_sha256':hashlib.sha256(('\n'.join(lines[start-1:end])+'\n').encode()).hexdigest(),'line_start':start,'line_end':end}

def source_registry():
    rs=[]
    for f in ('fetch_receipts.json','fetch_receipts_official_extra.json','fetch_receipts_method_extra.json'):
        rs+=json.loads((R/f).read_text())
    use={
      'RW25':('первичная публикация','2.7млн весь бизнес; >2млн российские типы; около1000B777 чартерных рейсов','Округлённый итог; нет domestic/international/charter числовой матрицы; полётный пассажир не уникальное лицо'),
      'RW24':('первичная публикация; расхождение версии','2.9млн за2024; опубликовано09.04.2025','Не согласуется с формулировкой RW25 о сопоставимости с2024; точный темп RW24→25 не принят'),
      'RW26H1':('первичная публикация; частичный срез','Почти1млн на российских самолётах с начала2026; Tu214+8%; новые20маршрутов','Дата20июля; сравнение сH1 без точного cutoff; не весь бизнес, не годовой рост'),
      'RW_FLEET':('первичная текущая страница','20RRJ95×100;3Tu214×194;2Tu204×210;3B777×412','Перечисленный парк; crew/MRO/свободный ресурс неизвестны; дальность страницы не dispatch guarantee'),
      'RW_VIETNAM':('первичная публикация','50тыс.пассажиров и125рейсов в Камрань за12месяцев; пакетные продажи; пути8ч40/10ч','Счётчик рейсов в аэропорт и пассажиров может иметь разные направления; не выводить LF или годовую производительность'),
      'RW_ISRAEL':('первичная публикация; датированное предложение','Около140тыс.пассажиров2025;1100рейсов; Tu214 и5ч45 по объявлению2026','Страна и география не маршрутныйOD; возобновление17апреля не гарантирует доступ2027–28'),
      'FAVT25':('первичная страница скачана','108.85млн;81.45domestic+27.40international; порядокtop5;top5total76.57','Рынок российских авиакомпаний;214.66млн аэропортов исключено из знаменателя; нет полной таблицы по всем АК'),
      'AF25_OFFICIAL':('первичный PDF скачан','АК29.5473млн;group55.3403млн;АКdomestic19.6557/int9.8916','Данные управленческого учёта; две разные единицы анализа; группа включает дочерних'),
      'AF26_OFFICIAL':('первичный PDF скачан','10M2026 group46.7047млн/АК24.9015млн; +11.9%groupinternational','Частичный год; не экстраполировать12/10; не добавлять к годовому2025'),
      'AF25':('републикация собственного релиза; дубликат','Подтверждает AF25_OFFICIAL','Для итоговых цифр приоритет официальномуPDF; не независимый источник'),
      'AF26_10M':('републикация собственного релиза; дубликат','Подтверждает AF26_OFFICIAL','Не отдельное наблюдение'),
      'AF_IR':('первичный каталог скачан','Прямые URL PDF2025 и2026','Каталог не числовое наблюдение'),
      'DP25':('собственный релиз на АвиаПорт; авторствоАКПобеда','13.8млн;>11.8domestic;>1.9international;LF94.8%','В относительном сравнении опечатка2025к2025; проценты не исправлены молча; округление мешает точной сумме'),
      'S725':('первичный текст через native web;HTTP403 при прямой загрузке','12.8млн2025;LF90%','Страница без даты; текущий snapshot; не вся S7Group'),
      'FV25':('первичная публикация скачана','12млн2025;10.5domestic;1.5international;+4.4%;январь2026 отдельно','Перераспределение Шаттла между АК меняет индивидуальный рейтинг без такого же роста группы'),
      'UT25':('первичная публикация скачана','АК6.2млн на самолётах;group6.9млн;вертолёты0.7млн','Пределы периметра;6.9 не показатель самолётной АК'),
      'FAVT24':('первичная страница скачана','111.7млн2024;рост5.9%','Рост рынка в прошлом, не прогноз отдельного конкурента'),
      'FAVT_METHOD_HIST':('первичный исторический сборник скачан','12ГА: один раз за рейс, не этап; дети<2 исключены; carrier по номеруУВД','Сборник содержит формы2007 и более поздние ссылки2009; дата URL2008 не дата всех редакций; действующая2026 редакция не подтверждена'),
      'STAT17':('первичный исторический текст индексирован','Росстат: рейс/этап различны; один раз за рейс','Прямое скачиваниеTLSошибка; актуальная редакция2026 неизвестна; не утверждение действующего правового режима'),
      'STAT_FORM_HIST':('историческая первичная форма индексирована','НомерУВД определяет статистического перевозчика; один раз за рейс','Форма10ГА авиаработ не основание считать её текущей формой всей АК; используем только историческое подтверждение определения'),
      'STAT_TRANSPORT':('доступ не получен','Текущая редакция методики не установлена','TLSошибка и native timeout; формальная текущая сверка открыта'),
      'YAK_SJ100':('первичная страница индексирована; P03 pin','PD8;до103кресел;3530км; тип отдельно отRRJ95','RWкомпоновка иcommercialavailability неизвестны; сертификат двигателя не сертификат готового парка'),
      'ROSTEC_SSJ_UTIL':('исторический первичный текст индексирован','Около400ч/месяц уRW описано дляSSJ в2023','Пример/пиковый месяц; не годовое среднее и неSJ100/PD8 производительность'),
      'RW_NEW_CEO':('индексированный текст;HTTP410 при скачивании','20SSJ; ожидаются новые машины в2027 безразбивки','НестабильныйURL; не нужен для числовых итогов, не подтверждение поставок'),
      'TU11':('вторичная публикация прямого заявления главыОАК','24.06.2026: первые11Tu214дляRW; начало2027','Нет первичного RW/OAK графика передачи/ввода;11не парк2028'),
      'S7_TU_PLAN':('первичный индексированный текст; open вернул посторонний список','Меморандум100Tu214; начало2029; до213кресел','Только индексированныйprimary excerpt; rawopen не подтвердил текст; не считать100поставками и не назначать ежегодный темп'),
    }
    for row in rs:
        s,c,l=use[row['source_id']]
        row.update(qualification=s,confirmed=c,coverage=l,unit='по полю факта; пассажир/рейс/тип/место; не смешивать',as_of=ASOF,status='published' if 'не получен' not in s else 'unknown')
        if row['source_id']=='TU11':row['publication_date']='2026-06-24'
        if row['source_id']=='FAVT24':row['publication_date']='2025-01-31'
        if row['source_id']=='AF26_10M':row['publication_date']='2026-11-12'
        if row['source_id']=='S7_TU_PLAN':row['publication_date']='2026-02-04'
        if row['source_id']=='FAVT_METHOD_HIST':row['publication_date']='UNKNOWN;историческийсборник,формы2007иссылки2009;URL2008неопределяетдатуредакций'
        if row['source_id']=='STAT17':row['publication_date']='UNKNOWN;историческийпервичныйиндексированныйтекст;актуальнаяредакция2026неподтверждена'
        if row['source_id']=='S725':row.update(text_path='sources/native_S725.txt',text_sha256=sha('sources/native_S725.txt'))
        if row['source_id']=='STAT17':row.update(text_path='sources/native_STAT17_definition.txt',text_sha256=sha('sources/native_STAT17_definition.txt'))
        if row['source_id']=='STAT_FORM_HIST':row.update(text_path='sources/native_metric_forms.txt',text_sha256=sha('sources/native_metric_forms.txt'))
        if row['source_id'] in ('YAK_SJ100','ROSTEC_SSJ_UTIL'):row.update(text_path='sources/native_manufacturer_search.txt',text_sha256=sha('sources/native_manufacturer_search.txt'))
        if row['source_id']=='S7_TU_PLAN':row.update(text_path='sources/native_manufacturer_search.txt',text_sha256=sha('sources/native_manufacturer_search.txt'))
    table('sources.csv',rs);jwrite('sources.json',rs)
    return {r['source_id']:r for r in rs}

def claims(sources):
    seed=[
      ('CL-RW25','RW25','sources/RW25.txt','общий пассажиропоток Red Wings составил 2,7','весь бизнес2025',2700000,'отчётных пассажиров/год','округлено'),
      ('CL-RW24','RW24','sources/RW24.txt','Пассажиропоток авиакомпании достиг 2,9','весь бизнес2024',2900000,'отчётных пассажиров/год','расхождение публикаций; не исправлено'),
      ('CL-MKT25','FAVT25','sources/FAVT25.txt','108,85','российские авиакомпании2025',108850000,'отчётных пассажиров/год','полный год'),
      ('CL-RANK25','FAVT25','sources/FAVT25.txt','В топ-5','отдельные перевозчики2025',None,'порядокtop5','нет полного числового списка'),
      ('CL-GROWTH24','FAVT24','sources/FAVT24.txt','5,9%','рынок2024',0.059,'доля изменения за год','исторический темп; не будущий рост конкурента'),
      ('CL-DP25','DP25','sources/DP25.txt','13,8 млн клиентов','АК2025',13800000,'отчётных пассажиров/год','округлено;опечатка года в сравнении'),
      ('CL-FV25','FV25','sources/FV25.txt','По итогам 2025 года','АК2025',12000000,'отчётных пассажиров/год','округлено'),
      ('CL-UT25','UT25','sources/UT25.txt','6,2 млн','самолётная АК2025',6200000,'отчётных пассажиров/год','неgroup6.9'),
      ('CL-FORM','FAVT_METHOD_HIST','sources/FAVT_METHOD_HIST.txt','При этом подсчет перевезенных пассажиров (почты и грузов) осуществляется только один раз','историческая форма12ГА',None,'пассажир/рейс','действующая редакция2026 UNKNOWN'),
      ('CL-ATC','FAVT_METHOD_HIST','sources/FAVT_METHOD_HIST.txt','осуществляет перевозчик, чей номер рейса использовался','исторические указания',None,'статистический перевозчик','не автоматически marketing code'),
      ('CL-TU11','TU11','sources/TU11.txt','они получают первые 11','объявленный пакет будущихTu214',11,'самолётов','нет годового графикаRW'),
    ]
    rows=[]
    for cid,sid,path,needle,scope,val,unit,note in seed:
        rows.append(dict(claim_id=cid,source_id=sid,url=sources[sid]['url'],organization=sources[sid]['organization'],publication_date=sources[sid]['publication_date'],period=sources[sid]['period'],scope=scope,value=val,unit=unit,status='published',coverage=note,**loc(path,needle)))
    # Exact table rows in official PDFs; retain the extracted row and full-PDF hash.
    for cid,sid,needle,val,scope in [('CL-AF25','AF25_OFFICIAL','29 547,3',29547300,'индивидуальнаяАК2025'),('CL-AFG25','AF25_OFFICIAL','55 340,3',55340300,'group2025'),('CL-AF26','AF26_OFFICIAL','24 901,5',24901500,'индивидуальнаяАК10M2026'),('CL-AFG26','AF26_OFFICIAL','46 704,7',46704700,'group10M2026')]:
        p=f'sources/{sid}.txt'; rows.append(dict(claim_id=cid,source_id=sid,url=sources[sid]['url'],organization='ПАО Аэрофлот',publication_date=sources[sid]['publication_date'],period=sources[sid]['period'],scope=scope,value=val,unit='отчётных пассажиров за указанный период',status='published',coverage='Управленческий учёт; тысячи×1000',source_pdf_sha256=sha(f'sources/{sid}.pdf'),**loc(p,needle)))
    table('source_claims.csv',rows)
    return rows

def assumption_register():
    rows=[]
    def add(aid,field,value,unit,why,impact,refine,range_='UNKNOWN',source='P10 author; current task',kind='сценарное условие'):
        rows.append(dict(assumption_id=aid,subject_version=VERSION,field=field,selected_value=value,unit=unit,kind=kind,selected_by='исследовательP10',user_approved='нет; рабочий исследовательский выбор в разрешённой области',rationale=why,source=source,justified_range_or_UNKNOWN=range_,sensitivity_or_impact=impact,how_to_refine=refine,as_of=ASOF))
    add('P10-METRIC','единица№2','индивидуальнаяавиакомпания','юридическийперевозчик','Рабочее определение пользователя; группы ведутся отдельно','Иначе2-е место и порог меняются','Подтвердить конкретный перечень юридическихперевозчиков у организаторов',source='задачаP10; PLAN metric_policy',kind='пользовательскаяпостановка')
    add('P10-REPORT','перевод сегментов в отчётных пассажиров','UNKNOWN','пассажир/рейс','Первичные исторические указания считают рейс один раз, не каждый этап; текущая редакциянеподтверждена','Нельзя принятьP09segments какрост№2','Получить отчёт12ГА/RW определение и mapping reporting_flight_id/operator/age/no-show',source='FAVT_METHOD_HIST;STAT17',kind='существенныйнеизвестный')
    add('P10-ROUND','точность исторического разрыва','около11.1млн','пассажиров/год','RW2.7иDP13.8округлены до0.1млн','Равенство13.8не доказывает обгон; округление неCI','Точные годовые строки Росавиации по обеимАК',range_='Если обычное округление к0.1млн:разрыв11.0..11.2млн; правило округленияUNKNOWN',source='RW25;DP25',kind='точностьпубликации')
    add('P10-KEEP-ANCHOR','будущий reference KEEP','2700000','отчётныхпассажиров/год','Сохраняем весь исторический объём как явное диагностическое условие; это не фактическийKEEP2027/28','Все итоговые числовые условныеуровни сдвигаются на изменениеKEEP; P09 KEEPещёнеготов','P09 полный24месячныйKEEP domestic/international/charter; общийфлотипродажи',source='RW25; задачаP10',kind='историческийякорь в сценарии')
    add('P10-C0','темп ориентира и reference рынка',0,'доля/год','Нулеваядинамика как контроль неизменного масштаба','Порогостаётся13.8млн; непрогноз','Обновлятьполныйгодовойрейтинг/ёмкости',source='RW25;FAVT25;DP25')
    add('P10-C007','темп ориентира и reference рынка',0.007,'доля/год','Повтор опубликованного малого темпаПобеды как условие, не прогноз; в релизеопечаткагода','Геометрическийростпорога; конкурентымогутсмениться','Точныйисправленныйрелиз и планыкаждойАК',source='DP25:опубликовано+0.7%,comparisonyear typo')
    add('P10-C059','темп ориентира и reference рынка',0.059,'доля/год','Историческийроствсегорынка2024 повторяетсякакстрессусиленияконкуренции; неоценкакаждойАК','Увеличивает порог2028 и долгосрочныйнеобходимыйресурс','Конкурентныекалендари/слоты/новыеВС; собственныесценариипоАК',source='FAVT24:5.9%за2024')
    add('P10-CMIX','неодинаковыйтемпсоперников','AF−1.8%;DP+0.7%;S7flat;Россия+4.4%;рынокflat','доля/год','Механически повторяем опубликованные2025темпыAF/DP/FV;дляS7нейтральныйконтроль,неизвестныйтемпнеобъявленнулевымфактом. ПереносШаттлапоказываетограничениеэкстраполяции','Меняетносителяпорога№2:РоссияможетобойтиПобеду;непрогноз','Отдельныекалендарикаждогоюридическогоперевозчика,внутригрупповойперераспределение',source='AF25_OFFICIAL;DP25;FV25;P10author')
    add('P10-SHARE','доля induced/foreign-recapture средиnetnew',['0','1'],'доля','Два крайних способа изменения российского знаменателя: перераспределение между российскимиАК или новые/отнятыеуиностранных перевозки','M_P=M_KEEP+alpha*delta; это условные крайние случаи, не confidence interval','P05 происхождениекаждойдополнительнойпоездки и статистическийmapping',range_='0..1 математическаяобластьпри отсутствиипрочихэффектоврынка',source='определение российскогоmarket;FAVT25')
    add('P10-NET','полнаяпродажаёмкости безсобственноймиграции',1,'условный netnew reportingpax/occupiedsegment','Только для capacity-only масштаба; не оценкаспроса/эффекта;реальныйкоэффициентUNKNOWN','Условныйприростможетбытьменьше,равен0илиотрицателен сдонором/KEEP; actualdeltaNULL','СовместныйP05/P06перерасчётвсехпродаж/договоров/KEEP',range_='UNKNOWN дляnetdelta; physicalcapacity неэкономическаяграница',source='методическоеусловиеP10')
    add('P10-YEARS','годы отображения',[2027,2028,2030,2035],'год','2027–28обязательныйэтап;2030/2035только масштабывозможныхгоризонтов','Не устанавливает срокдостижения№2','Выбиратьдату только послесогласованногопланаиподтверждённогоресурса',source='задачаP10;срок№2неустановлен')
    add('P10-DELIVERY','календарь4/2/4/0SJ','точные строкиP03_DELIVERIES','борт/дата','Повторяем опубликованный diagnostic P03 безсозданияконкурирующегографика; not forecast','Разныеaircraftdays2027–28; delayedв2028неравенfull4year','RWдоговоры/передача/ввод/crew/MRO/сертификация',source='79dc698...:diagnostic_delivery_events.csv')
    add('P10-TU0','новыеTu214 в2027–28',0,'борт','Обязательная самостоятельная ветвьбезновогоTu214','SJкейс и сохранениеwholebusiness не зависятотпакета11','Проверятьсостояниепоставок, непереписываяэтуконтрольнуюветвь',source='задачаP10',kind='пользовательскаяветвь')
    add('P10-TU11','новыеTu214 longterm',11,'дополнительныхбортов','Исследуемобъявленныйпакетпослеполнойготовности; датаUNKNOWN','11летнихэквивалентовнеобеспечиваютвесьgapподзаданнойпроизводительностью','Полныйкалендарьcommercialavailability ифинусловий; сохранятьветвь0',source='TU11;вторичныйnamedstatement')
    add('P10-SEATS-SJ','компоновкаSJ100/PD8',100,'кресел/борт','Расчётныйпроектныйаналог100; производительдо103; RWконфигурацияUNKNOWN; отделён отRRJ95','103vs100даёт+3%припрочихравных; нетпереносарасходов','УтверждённаякомпоновкаRW дляточноготипа',range_='UNKNOWN;100и103разныеусловия,неожидаемыйинтервал',source='P03_TYPES;YAK_SJ100;old digital seat analogue')
    add('P10-SEATS-TUNEW','компоновкановогоTu214',194,'кресел/борт','КомпоновкадействующегоRW какявныйаналог; новаяUNKNOWN','Производительностьмасштабируетсясместами; не переносрасходов','Контракт/утверждённаякабина дляновогоRWборта',source='RW_FLEET;P03_TYPES')
    add('P10-UTIL','LF/блок-время/активныйналёт/доступность','type_productivity.csv','разныеединицыпоименованы','Дизайнточкипродолженыизстарогоd48b... иразложеныпосезонам; нетгодовойкалибровки/планаполётовRW','ЧислобортовобратнопропорциональноLF*h*a ипрямопропорциональноt;нетобщейпроизводительностипарка','Помесячныеналёт/циклы/кресло-LF/ТО/резервпо ВС итипам',source='OLD_DIGITAL_PARAMETERS;ROSTEC_SSJ_UTIL;RW_VIETNAM')
    add('P10-SEASON','помесячнаяутилизация','зима,лето,межсезонье','blockh/активныйдень','Непереносимдекабрьскуюнеделю×52; явно задаёмполныйгоди365/366дней;формапрофилясценарная','Сезоннаяформауменяетсуммуtaildays*h;калиброванногоинтерваланет','История2025/2026помесячнопокаждомутипу;P03датыдоступности')
    add('P10-AVAIL','availability включаетТОирезерв','поименновтаблице','долякалендарноговремени','Одинвычетa; второйрезервсверхнеприменяется; графикнепроверен','Не применятьaповерхужеapprovedprojecthoursP03','Вместодоли использовать disjointtaildatestates P03',source='старыйdiagnostic;P03контракт')
    add('P10-CREW','производительныймесячныйналётодногочленаэкипажа','UNKNOWN','blockh/человек/месяц','Неизвестныростер,допуски,отпуска/учеба; минимальныйсоставнечислосотрудников','Headcount=assignedflightcrew_blockh/H_personприраздельныхтипах; числоUNKNOWN','RWtraining/roster/ФАПдействующейредакции;P03')
    add('P10-CASH','KEEPcash,unitcosts,openingliquidity','UNKNOWN','RUBсгодомцен/месяц','ПолнойфинансовойматрицыRWнет; referenceP04небудущаяставка; не ставим0','Peakfunding,прибыльидатабезубыточностиUNKNOWN; естьформулы/сигналы','P04драйверы+RWдоговоры/денежныйплан; расчёттолькоP06',source='P04;P06;задачаP10',kind='существенныенеизвестные')
    add('P10-NORMALIZE','нормировкаденежнойчувствительности','1RUB/пассажир;1000000RUB/aircraftmonth','единицамасштаба,неставка','Показываемкоэффициентыденежнойэкспозициибезвыдуманнойцены','Неоценкаплатежа/маржи; дляреальнойставкиумножить коэффициент,затемP06cash','Реальныецены/валюта/периодипрофильоплаты',range_='непараметррынка;единицанормировки',kind='арифметическаянормировка')
    add('P10-DIGITAL','независимое добавление пассажировP11','запрещено','boarding/reportingevent','Заказы/багаж/повторныеобращениянепассажиры; P09можетуже включатьновыепродажи','Экономияидопуслугивденежномреестре; пассажиры толькоdeduplicatedrealisedincrement','P11cohorts/eventkeys/control иP09 jointrecompute',source='задачаP10;OLD_DIGITAL_HANDOFF',kind='границаинтеграции')
    table('assumptions_register.csv',rows);jwrite('assumptions_register.json',rows)
    return rows

def competitor_scale(claims):
    cm={c['claim_id']:c for c in claims}
    seed=[
      ('AF','Аэрофлот','individual_carrier',1,29547300,'CL-AF25','AF25_OFFICIAL',19655700,9891600,'неgroup'),
      ('DP','Победа','individual_carrier',2,13800000,'CL-DP25','DP25',None,None,'domestic>11.8млн;international>1.9млн;неточноеразбиение'),
      ('S7','Сибирь/S7Airlines','individual_carrier',3,12800000,None,'S725',None,None,'неS7Group'),
      ('FV','Россия','individual_carrier',4,12000000,'CL-FV25','FV25',10500000,1500000,'входитвАэрофлотgroup'),
      ('U6','Уральскиеавиалинии','individual_carrier',5,None,None,'FAVT25',None,None,'числосовместимогогодовогоитогаUNKNOWN;невыводимразностьюокруглённыхtop5'),
      ('UT','ЮТэйр','individual_carrier_fixedwing',None,6200000,'CL-UT25','UT25',5000000,None,'group6.9отдельно;местовполномрейтингездесьнеустановлено'),
      ('WZ','RedWings','individual_carrier',None,2700000,'CL-RW25','RW25',None,None,'весьбизнес;точноеместовполномрейтингездесьнеподтверждено'),
      ('AFG','ГруппаАэрофлот','group',None,55340300,'CL-AFG25','AF25_OFFICIAL',41958700,13381600,'включаетAF/DP/FV;несуммировать'),
      ('UTG','ГруппаЮТэйр','group_with_helicopters',None,6900000,None,'UT25',None,None,'самолёты6.2+вертолёты0.7;несуммировать'),
      ('RUM','Всерассматриваемыероссийскиеавиакомпании','market_denominator',None,108850000,'CL-MKT25','FAVT25',81450000,27400000,'неаэропорты/неиностранныеперевозчики'),
    ]
    rows=[]
    for eid,name,typ,rank,pax,cid,sid,dom,intl,lim in seed:
        row=dict(row_id=f'{eid}:2025:reported',entity_id=eid,entity=name,entity_type=typ,period_start='2025-01-01',period_end='2025-12-31',period_grain='year',rank_among_individual_carriers=rank,reported_passengers=pax,domestic_reported_passengers=dom,international_reported_passengers=intl,unit='отчётныхпассажировзауказанныйпериод',source_id=sid,claim_id=cid,as_of=ASOF,status='published' if pax is not None else 'unknown_value_published_rank',coverage=lim)
        if cid:row.update({k:cm[cid][k] for k in ('source_row_id','source_text_path','source_text_sha256')})
        if eid=='S7':row.update(source_text_path='sources/native_S725.txt',source_text_sha256=sha('sources/native_S725.txt'),source_row_id='native official company paragraph12.8m')
        rows.append(row)
    for eid,name,pax,dom,intl,cid in [('AF','Аэрофлот',24901500,15310900,9590600,'CL-AF26'),('AFG','ГруппаАэрофлот',46704700,34226800,12477900,'CL-AFG26')]:
        rows.append(dict(row_id=f'{eid}:2026_10M:reported',entity_id=eid,entity=name,entity_type='individual_carrier' if eid=='AF' else 'group',period_start='2026-01-01',period_end='2026-10-31',period_grain='10months',rank_among_individual_carriers=None,reported_passengers=pax,domestic_reported_passengers=dom,international_reported_passengers=intl,unit='отчётныхпассажировза10месяцев',source_id='AF26_OFFICIAL',claim_id=cid,as_of=ASOF,status='published',coverage='неполныйгод;неумножать12/10;несмешиватьс2025',**{k:cm[cid][k] for k in ('source_row_id','source_text_path','source_text_sha256')}))
    table('competitor_scale.csv',rows)
    return rows

def metrics():
    seed=[
      ('reported_passengers','Отчётныйперевезённыйпассажир','пассажирнарейсе','airline,reportingflight,date,boardinggroup','Одинраззарейс;некаждыйэтап;историческоеопределение;актуальнаясверкаUNKNOWN','FAVT_METHOD_HIST;STAT17','primarytarget№2;aggregate sum only under compatible reportingdefinition'),
      ('OD_journeys','Конечнаяпоездка','поездка','journey_id,departuredate,origin,destination','Однапоездкаможетсодержатьнесколькорейсов/этапов;сквознойтарифодинраз','P00R;P06','неравнаreportedбезmapping'),
      ('passenger_segments','Пассажирскийэтап','занятоекреслонаэтапе','physicalflight_instance_id,passengerboardinggroup','Одинпассажирнакаждомфизическомплечерасходуеткресло;несколькоэтаповпододнимreportingflightнеравнынесколькимreportedpax','P06;FAVT_METHOD_HIST','проверкавместимости;неprimaryranking'),
      ('unique_travellers','Уникальныйчеловек','человек','deidentifiedperson_id,period','Повторныеполётысчитаютсяодинраздляэтойметрики;вreportingкаждаяперевозка','P10-REPORT','НЕиспользоватьвзнаменателе108.85млн'),
      ('flight_instance','Физическийдатированныйвылет','этапполёта','operator,flight_instance_id,departureUTC','Маршрутсдвумяэтапамииоднимномеромдолжениметьдвавылетныхinstance','P03;P06','capacitynotbookings'),
      ('reporting_flight','Статистическийрейс','рейс','statisticalcarrier,ATCflightnumber,reportingflightdate','Маркетинговыйномер/RT/кодсампосебенедоказываеткоммерческуюнепрерывность','FAVT_METHOD_HIST;P02','mappingNULLдопринятия'),
      ('ASK','Располагаемыекреслокилометры','кресло-км','physicalflight_instance_id,distance,seats_available','Суммафизическихкресел×расстояние;закрытыекресланеavailable','AF25_OFFICIAL;FAVT_METHOD_HIST','непассажиры'),
      ('RPK','Пассажирооборот','пассажиро-км','physicalflight_instance_id,distance,occupiedseats','Суммапассажировнаэтапе×расстояние','AF25_OFFICIAL;FAVT_METHOD_HIST','ростRPKможетсовпастьсоснижениемpax'),
      ('LF_seatkm','Занятостькреселпорасстоянию','RPK/ASK','airline,period','ОпубликованныйLFможетбытьвзвешенрасстоянием;неравенчислузанятыхкресел/креселнавылет','AF25_OFFICIAL','некалибруетP10LFseatбезданных'),
      ('LF_seats','Занятостькреселпоэтапам','occupiedseatsegments/offeredseatsegments','type,period','Условиеcapacitydiagnostic;фактическийгодовойRWпо типуUNKNOWN','P10-UTIL','P10onlynotestimated'),
      ('market_share','Доляотчётныхперевозок','доляили п.п.','metricversion,entityscope,period,externalscenario','S=P_RW/M_Russian;delta=S_PROJECT−S_KEEP;M_PROJECTможетотличатьсяиз-заиндуцированныхперевозок','FAVT25;P10-SHARE','согласованныечислитель/знаменатель'),
      ('charter','Чартерныепассажирскиеперевозки','reportedpax/period','service_regime,domestic_orinternational,operator','Чартерпересекаетсясgeography;domestic+international+charterнельзяскладывать','RW25;FAVT_METHOD_HIST','четыренепересекающиесяячейкиdom/int×regular/charter'),
      ('digital_orders','Оплаченныйзаказ','заказ','order_id,cohort,eventtime','Занесколькоseatcoupons/пассажиров/услуг;отмена/no-showнефактическаяперевозка','OLD_DIGITAL_PARAMETERS;P10-DIGITAL','недобавлятькP09pax'),
      ('listed_aircraft','Перечисленныйпарк','борт','registration,type,snapshot','Неравенисправным/свободным/коммерческидоступнымбортам','RW_FLEET;P03','несчитатьновыйпакет11готовымпарком'),
      ('full_incremental_operating_result','Полныйдобавочныйоперационныйрезультат','RUBpriceyear/period','PvsKEEP,samecontext','Выручка/поддержка/переменные+фиксированные+использованиеВС/запуск/выход;инвестицииифинансированиеотдельно','P04;P06','P10нерассчитываетновуюденежнуюмодель'),
      ('peak_funding','Пиковаяпотребностьвликвидности','RUBpriceyear','jointKEEPandprojectmonthlycash,openingbalances','Максимумдефицитасовместногосальдо;пикиKEEPиPнескладываютсямеханически','P04;P06','UNKNOWNдополученияcash'),
    ]
    rows=[dict(metric_id=a,name_ru=b,unit=c,grain_and_key=d,definition=e,source_id=f,admission_rule=g,version=VERSION,as_of=ASOF) for a,b,c,d,e,f,g in seed]
    table('metric_dictionary.csv',rows)
    examples=[
      dict(example_id='EX1',description='100пассажировA→CнаодномreportingрейсесдвумяэтапамиA-B/B-C',OD_journeys=100,passenger_segments=200,reported_passengers_if_historical_definition_applies=100,fare_charges=100,qualification='условныйпример;недоказательствокоммерческойнепрерывностиRT581/651'),
      dict(example_id='EX2',description='100поездокA→Cна2разныхreportingрейсахA-B/B-CоднойАК',OD_journeys=100,passenger_segments=200,reported_passengers_if_historical_definition_applies=200,fare_charges=100,qualification='2рейса;одинсквознойтарифеслиэтодоказанныйitinerary;currentmappingrequiresapproval'),
      dict(example_id='EX3',description='Тежесамые100продажучтеныP09ицифровымэкспериментомP11',OD_journeys=100,passenger_segments=100,reported_passengers_if_historical_definition_applies=100,extra_reported_passengers_on_sum=0,fare_charges=100,qualification='P11неприбавляет100повторно;денежныеэффектыраздельны'),
    ];table('metric_bridge_examples.csv',examples)

def aircraft_constraints():
    source='inputs/P03_TYPES_aircraft_type_parameters.csv'
    rows=readcsv(source)
    for i,row in enumerate(rows,2):
        canonical=json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'))
        row.update(source_commit='79dc698b99dfe866886d32376ed388e85bdd039c',source_path='context/35_full_programme_execution_20261112/P03/aircraft_type_parameters.csv',source_row_id=f'csv_record:{i}',source_file_sha256=sha(source),source_row_sha256=hashlib.sha256(canonical.encode()).hexdigest(),P10_admission='Сохранённая строка P03; рекламная дальность не ограничение AFM и не разрешение на маршрут с полной нагрузкой. Топливо, ТО и доступность не заменены нулём; расходы нового ПД-8 из SaM146 не переносятся.')
    table('aircraft_constraints.csv',rows)

def thresholds():
    rates={'C_FLAT':0.,'C_SLOW007':.007,'C_RECOVERY059':.059,'C_MIXED_HISTORY':0.}
    rows=[];trajectories=[]
    for cid,g in rates.items():
        for year in [2025,2027,2028,2030,2035]:
            n=year-2025;factor=(1+g)**n
            base={'Аэрофлот':29547300,'Победа':13800000,'Сибирь/S7':12800000,'Россия':12000000}
            cr={x:g for x in base} if cid!='C_MIXED_HISTORY' else {'Аэрофлот':-.018,'Победа':.007,'Сибирь/S7':0.,'Россия':.044}
            contenders={name:pax*(1+cr[name])**n for name,pax in base.items()}
            threshold=sorted(contenders.values(),reverse=True)[1]
            runner=next(name for name,pax in contenders.items() if pax==threshold)
            for name,pax in contenders.items():trajectories.append(dict(competition_scenario_id=cid,year=year,carrier=name,reported_pax_condition=pax,annual_growth_condition=cr[name],rank_under_condition=sorted(contenders.values(),reverse=True).index(pax)+1,status='conditional_notforecast',coverage='толькочетыревосстановленныхчисловыхконтендера;полныйбудущийрейтингUNKNOWN',assumption_id='P10-CMIX' if cid=='C_MIXED_HISTORY' else {'C_FLAT':'P10-C0','C_SLOW007':'P10-C007','C_RECOVERY059':'P10-C059'}[cid]))
            rows.append(dict(threshold_case_id=f'{cid}:{year}',competition_scenario_id=cid,year=year,threshold_reported_pax=threshold,threshold_carrier_under_condition=runner,threshold_rule='2nd largest among pinnedtop4; futurefullrankUNKNOWN',market_annual_growth_condition=g,source_id='DP25;FAVT25;FAVT24;AF25_OFFICIAL;FV25',reference_market_KEEP=108850000*factor,reference_RW_KEEP=2700000,gap_to_reference_RW_KEEP=threshold-2700000,required_RW_CAGR_from2025_to_year=(threshold/2700000)**(1/n)-1 if n else None,unit='отчётныхпассажиров/год;CAGRдоля/год',period=f'{year}-01-01/{year}-12-31',status='historical_diagnostic' if year==2025 else 'conditional_scale_scenario',as_of=ASOF,assumption_ids='P10-METRIC;P10-ROUND;P10-KEEP-ANCHOR;P10-YEARS;'+{'C_FLAT':'P10-C0','C_SLOW007':'P10-C007','C_RECOVERY059':'P10-C059','C_MIXED_HISTORY':'P10-CMIX'}[cid],coverage='публичныйокруглённыйпорогнеобгон;необеспеченностьспросом;возможендругой№2'))
    table('threshold_scenarios.csv',rows);table('competitor_trajectories.csv',trajectories);return rows

def productivity():
    rows=[]
    # This is a capacity identity at explicit points, not a forecast or tariff/choice engine.
    specs=[
      ('RRJ95_EXISTING','SaM146',100,.85,2.,.90,[8,8,9,9,10,10,10,10,9,9,8,8],'базовая'),
      ('RRJ95_EXISTING','SaM146',100,.75,2.5,.85,[6,6,7,7,8,8,8,8,7,7,6,6],'осторожная'),
      ('SJ100_PD8_NEW','PD8',100,.85,2.,.90,[8,8,9,9,10,10,10,10,9,9,8,8],'базовая'),
      ('SJ100_PD8_NEW','PD8',100,.75,2.5,.85,[6,6,7,7,8,8,8,8,7,7,6,6],'осторожная'),
      ('TU214_EXISTING','PS90A',194,.88,3.,.90,[9,9,10,10,11,11,11,11,10,10,9,9],'базовая'),
      ('TU214_EXISTING','PS90A',194,.80,4.,.85,[7,7,8,8,9,9,9,9,8,8,7,7],'осторожная'),
      ('TU214_NEW_DOMESTIC','PS90A',194,.88,3.,.90,[9,9,10,10,11,11,11,11,10,10,9,9],'базовая'),
      ('TU214_NEW_DOMESTIC','PS90A',194,.80,4.,.85,[7,7,8,8,9,9,9,9,8,8,7,7],'осторожная'),
      ('TU204_100B_EXISTING','PS90A',210,.88,3.,.90,[9,9,10,10,11,11,11,11,10,10,9,9],'базовая'),
      ('TU204_100B_EXISTING','PS90A',210,.80,4.,.85,[7,7,8,8,9,9,9,9,8,8,7,7],'осторожная'),
      ('B777_200ER_EXISTING','exactengineUNKNOWN',412,.90,10.,.85,[11,11,12,12,13,13,13,13,12,12,11,11],'базовая'),
      ('B777_200ER_EXISTING','exactengineUNKNOWN',412,.80,11.,.80,[9,9,10,10,11,11,11,11,10,10,9,9],'осторожная'),
    ]
    for typ,eng,seats,lf,block,a,h,market in specs:
        key=f'{typ}:{market}';hours=sum(calendar.monthrange(2028,m)[1]*h[m-1]*a for m in range(1,13))
        flights=hours/block;cap=flights*seats*lf
        rows.append(dict(productivity_id=key,aircraft_type=typ,engine=eng,condition=market,year_reference=2028,seats=seats,seat_count_status='scenarioRWconfigurationUNKNOWN' if 'NEW' in typ else 'publishedRWtypepage',LF_seat_segment_condition=lf,block_hours_per_segment=block,availability_including_MRO_and_reserve=a,block_hours_per_active_day_by_month=json.dumps(h),annual_block_hours_per_listed_tail=hours,annual_segment_equivalents_per_tail=flights,annual_occupied_segment_equivalents_per_tail=cap,annual_reported_pax_per_tail=None,true_calibrated_range='UNKNOWN',operational_validation='NOT_RUN; дробныерейсытолькоэквиваленты,нетмаршрутов/ростера',source_id='RW_FLEET;P03_TYPES;OLD_DIGITAL_PARAMETERS;RW_VIETNAM;ROSTEC_SSJ_UTIL',assumption_ids='P10-UTIL;P10-SEASON;P10-AVAIL;P10-REPORT'+(';P10-SEATS-SJ' if typ=='SJ100_PD8_NEW' else ';P10-SEATS-TUNEW' if typ=='TU214_NEW_DOMESTIC' else ''),unit='кресла;LF;blockh/этап;blockh/борт/год;occupiedsegments/борт/год',as_of=ASOF,status='capacity_design_point_not_forecast'))
    table('type_productivity.csv',rows);return rows

def delivery_months(prod):
    inputs=readcsv('inputs/P03_DELIVERIES_diagnostic_delivery_events.csv')
    for i,row in enumerate(inputs,2):row['source_row_id']=f'csv_record:{i}'
    pm={x['condition']:x for x in prod if x['aircraft_type']=='SJ100_PD8_NEW'}
    rows=[]
    for delivery in ['phased','partial','delayed','no_new']:
      events=[e for e in inputs if e['delivery_scenario_id']==delivery]
      for condition,p in pm.items():
        h=json.loads(p['block_hours_per_active_day_by_month'])
        for year in [2027,2028]:
          for m in range(1,13):
            start=date(year,m,1);n=calendar.monthrange(year,m)[1];end=date(year,m,n)
            commercial_days=0;handed_days=0;endcount=0
            for e in events:
              entry=date.fromisoformat(e['conditional_entry_date']);handed=date.fromisoformat(e['handover_date'])
              commercial_days+=max(0,(end-max(start,entry)).days+1)
              handed_days+=max(0,(end-max(start,handed)).days+1)
              endcount+=int(entry<=end)
            hours=commercial_days*h[m-1]*p['availability_including_MRO_and_reserve']
            legs=hours/p['block_hours_per_segment'];cap=legs*p['seats']*p['LF_seat_segment_condition']
            rows.append(dict(resource_case_id=f'SJ_NO_NEW_TU:{delivery}:{condition}',fleet_scope_id='CASE_SJ',delivery_scenario_id=delivery,condition=condition,month=start.strftime('%Y-%m'),days_in_month=n,new_SJ_inducted_end=endcount,new_TU214_inducted_end=0,conditional_commercial_tail_days=commercial_days,post_handover_tail_days=handed_days,post_handover_tail_months=handed_days/n,conditional_block_hours=hours,conditional_flight_segment_equivalents=legs,conditional_occupied_segment_equivalents=cap,actual_net_new_reported_pax=None,actual_peak_funding_RUB=None,source_id='P03_DELIVERIES',source_commit='79dc698b99dfe866886d32376ed388e85bdd039c',source_sha256=sha('inputs/P03_DELIVERIES_diagnostic_delivery_events.csv'),source_row_ids=';'.join(e['source_row_id'] for e in events) if events else 'explicit no_new branch;0newaircraft not unknownexistingresource',source_rows_sha256=hashlib.sha256(json.dumps(events,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),productivity_id=p['productivity_id'],assumption_ids='P10-DELIVERY;P10-TU0;P10-UTIL;P10-SEASON;P10-AVAIL;P10-SEATS-SJ',unit='taildays;blockhours;occupiedsegments;notapprovedRWcapacity',status='conditional_capacity_diagnostic',as_of=ASOF))
    table('resource_calendar_monthly.csv',rows);return rows

def growth_cases(thresh,months):
    rows=[]
    for delivery in ['phased','partial','delayed','no_new']:
      for condition in ['базовая','осторожная']:
       for year in [2027,2028]:
        ms=[x for x in months if x['delivery_scenario_id']==delivery and x['condition']==condition and x['month'].startswith(str(year))]
        cap=sum(x['conditional_occupied_segment_equivalents'] for x in ms)
        for t in [x for x in thresh if x['year']==year]:
          k=t['reference_RW_KEEP'];mk=t['reference_market_KEEP'];threshold=t['threshold_reported_pax']
          for alpha in [0,1]:
            pp=k+cap;mp=mk+alpha*cap;delta=(pp/mp-k/mk)*100
            rows.append(dict(growth_case_id=f'{VERSION}:SJ_TU0:{delivery}:{condition}:{t["competition_scenario_id"]}:{year}:alpha{alpha}',fleet_scope_id='CASE_SJ',programme_id='P10_SCALE_DIAGNOSTIC_NOT_P09_PROGRAMME',programme_version=VERSION,delivery_scenario_id=delivery,productivity_condition=condition,competition_scenario_id=t['competition_scenario_id'],year=year,new_TU214_in_period=0,new_SJ_inducted_end=ms[-1]['new_SJ_inducted_end'],conditional_occupied_segment_capacity=cap,conditional_sold_reporting_increment_if_mapping1_and_net1=cap,reference_RW_KEEP_pax=k,reference_market_KEEP_pax=mk,conditional_RW_project_pax=pp,conditional_market_project_pax=mp,alpha_new_to_Russian_market=alpha,conditional_share_KEEP_percent=100*k/mk,conditional_share_PROJECT_percent=100*pp/mp,conditional_share_delta_pp=delta,number2_scenario_landmark=threshold,remaining_gap_if_landmark_held=threshold-pp,actual_P09_net_reported_passengers=None,actual_P09_share_delta_pp=None,actual_full_incremental_result_RUB=None,actual_peak_funding_RUB=None,as_of=ASOF,period_start=f'{year}-01-01',period_end=f'{year}-12-31',unit='отчётныхпассажиров/годтолькоусловно;долипроценты/п.п.',status='CAPACITY_ONLY_CONDITIONAL_NOT_DEMAND_OR_ECONOMIC_ACCEPTANCE',coverage='подзаданнойпроизводительностью;1reportingpax/occupiedsegment;allnewnet;KEEP2.7сценарный;реальныепродажи/потериUNKNOWN',assumption_ids=t['assumption_ids']+';P10-DELIVERY;P10-UTIL;P10-SEASON;P10-AVAIL;P10-TU0;P10-REPORT;P10-NET;P10-SHARE;P10-SEATS-SJ',source_id='RW25;FAVT25;DP25;P03_DELIVERIES;P06'))
    table('growth_cases.csv',rows);return rows

def required_resources(thresh,prod):
    rows=[];front=[]
    for t in [x for x in thresh if x['year'] in (2025,2028,2030,2035)]:
      gap=t['gap_to_reference_RW_KEEP']
      for p in prod:
        cap=p['annual_occupied_segment_equivalents_per_tail'];needed=math.ceil(gap/cap)
        rows.append(dict(requirement_id=f'{t["threshold_case_id"]}:{p["productivity_id"]}',threshold_case_id=t['threshold_case_id'],year=t['year'],aircraft_type=p['aircraft_type'],condition=p['condition'],gap_to_reference_KEEP=gap,occupied_segment_per_tail_year=cap,additional_full_tail_year_equivalents=gap/cap,additional_indivisible_tails_at_design_point=needed,additional_offered_seat_segments=gap/p['LF_seat_segment_condition'],additional_flight_segment_equivalents=gap/(p['seats']*p['LF_seat_segment_condition']),additional_block_hours=gap/(p['seats']*p['LF_seat_segment_condition'])*p['block_hours_per_segment'],crew_productive_person_hours_minimum_condition=None,unit='пассажирскиеэтапы/год;бортогод;борт;blockh',status='necessary_resource_identity_conditional_reportingmapping1',coverage='добавочно при сохранении referenceKEEP;нельзявычесть28разнородныхбортов;неpipelineпоставок;безспроса/слотов/ростера',source_id='RW25;DP25;RW_FLEET;P03_TYPES',assumption_ids=t['assumption_ids']+';'+p['assumption_ids']+';P10-NET;P10-CREW'))
      for condition in ['базовая','осторожная']:
        sj=next(p for p in prod if p['aircraft_type']=='SJ100_PD8_NEW' and p['condition']==condition)
        tu=next(p for p in prod if p['aircraft_type']=='TU214_NEW_DOMESTIC' and p['condition']==condition)
        wb=next(p for p in prod if p['aircraft_type']=='B777_200ER_EXISTING' and p['condition']==condition)
        for n_tu in [0,11]:
          # All are additional full commercially usable tail years, date UNKNOWN.
          for n_sj in [0,4]:
            residual=max(0,gap-n_tu*tu['annual_occupied_segment_equivalents_per_tail']-n_sj*sj['annual_occupied_segment_equivalents_per_tail'])
            front.append(dict(frontier_id=f'{t["threshold_case_id"]}:{condition}:Tu{n_tu}:SJ{n_sj}',threshold_case_id=t['threshold_case_id'],reference_year_for_landmark=t['year'],commercial_availability_year='UNKNOWN;не назначено2028',condition=condition,additional_TU214_full_tail_years=n_tu,additional_SJ100_full_tail_years=n_sj,TU214_conditional_segment_capacity=n_tu*tu['annual_occupied_segment_equivalents_per_tail'],SJ100_conditional_segment_capacity=n_sj*sj['annual_occupied_segment_equivalents_per_tail'],residual_reported_equivalent_gap=residual,alternative_A_additional_SJ100_only=math.ceil(residual/sj['annual_occupied_segment_equivalents_per_tail']),alternative_B_additional_B777_like_only=math.ceil(residual/wb['annual_occupied_segment_equivalents_per_tail']),B777_acquisition_or_free_resource='UNKNOWN;непредлагаетсякакзаказ',financing='UNKNOWN;P06cashrequired',status='frontier_of_disjoint_resource_choices_not_a_selected_or_financed_strategy',assumption_ids='P10-TU11;P10-TU0;P10-UTIL;P10-REPORT;P10-NET;P10-KEEP-ANCHOR;P10-CASH;P10-SEATS-SJ;P10-SEATS-TUNEW'))
    table('required_resources_by_type.csv',rows);table('resource_frontier.csv',front)
    listed={'RRJ95_EXISTING':20,'TU214_EXISTING':3,'TU204_100B_EXISTING':2,'B777_200ER_EXISTING':3}
    fs=[]
    for typ,n in listed.items():
        for p in [x for x in prod if x['aircraft_type']==typ]:
            fs.append(dict(fleet_record_id=f'{typ}:{p["condition"]}',aircraft_type=typ,published_listed_tails=n,published_seats_per_tail=p['seats'],all_listed_full_year_occupied_segment_equivalent=n*p['annual_occupied_segment_equivalents_per_tail'],condition=p['condition'],actual_available_or_free_tails=None,actual_KEEP_carried_by_type=None,actual_increment=None,coverage='Этоёмкостьвсегоусловногоlistedпарка,ужеобслуживающегоKEEP;неприбавлятьк2.7млн',source_id='RW_FLEET',assumption_ids='P10-UTIL;P10-AVAIL;P10-SEASON;P10-REPORT',status='listed_fleet_design_capacity_not_growth'))
    table('existing_fleet_separate_types.csv',fs)

def finance_drivers(months,growth):
    rows=[]
    for r in months:
      rows.append(dict(resource_case_id=r['resource_case_id'],month=r['month'],post_handover_aircraft_months=r['post_handover_tail_months'],normalised_lease_exposure_RUB_if_1m_per_aircraft_month=r['post_handover_tail_months']*1000000,commercial_tail_days=r['conditional_commercial_tail_days'],conditional_flight_segments=r['conditional_flight_segment_equivalents'],conditional_block_hours=r['conditional_block_hours'],conditional_occupied_segments=r['conditional_occupied_segment_equivalents'],net_revenue_and_contribution='UNKNOWN;P05/P06',lease_rate_RUB_per_aircraft_month=None,crew_MRO_base_launch_exit_RUB=None,KEEP_cash_RUB=None,actual_incremental_result_RUB=None,actual_peak_funding_RUB=None,status='cost_driver_coefficients_not_cost_forecast',assumption_ids='P10-CASH;P10-NORMALIZE;P10-DELIVERY;P10-UTIL',unit='RUBнормировкитолько;aircraftmonths;blockhours;segments'))
    table('funding_exposure_drivers.csv',rows)
    equations={
      'version':VERSION,'money_engine':'P06 only; no P10 monetary forecast',
      'incremental_operating_result':'delta_net_revenue + delta_eligible_support - delta_variable_cost - delta_fixed_cost - delta_aircraft_use - delta_launch_expensed - delta_exit_expensed - delta_DA, all same futurePvsKEEP; obligations deduplicated',
      'joint_cash_before_financing':'opening_unrestricted_cash + KEEP_cash_events + project_minus_KEEP_cash_events + digital_residual_cash_events - minimum_operating_cash_buffer; all event dated, samecontext',
      'required_committed_financing':'max(0,-min_t(joint_cash_before_financing_t)); KEEPpeak+projectpeak is NOT this maximum in general',
      'finance_capacity_gate':'signed_undrawn_facility_available_by_t + irrevocable_owner_funding_by_t >= cash_shortfall_by_t including exit/remaining commitments; otherwise adapt before commitment',
      'full_cost_threshold':'maximum_affordable_unknown_cost = incremental_net_revenue + eligible_support - all_other_full_incremental_costs; never set every unknown independently at its own maximum',
      'reference_gap_coefficient':{'historical_gap_passengers_per_year':11100000,'annual_result_change_RUB_per_1_RUB_net_contribution_per_incremental_reported_pax':11100000,'qualification':'unit-normalisation only; margin UNKNOWN and fare change requires P05/P06 reallocation'},
      'calendar_sensitivity':'+1mRUB per post-handover aircraft-month changes accrued aircraft cost by funding_exposure_drivers coefficient; cash timing UNKNOWN; not a lease quote',
      'delivery_delay_sensitivity':'avoidable future cost can be deferred; already-signed deposits/crew/launch and lostnetcontribution remain. No cash benefit sign assigned without event dates.',
      'break_even_date':None,'break_even_status':'UNKNOWN;not imposed by2028; financing and trajectory to improvement must be validated',
      'finance_scenarios':[
        {'id':'F_COMMITTED','condition':'committed funds cover full dated joint deficit + signed exit/contingency obligations','action':'stage only resource/demand/operations admitted programmes','numeric_budget_RUB':None},
        {'id':'F_LIMITED','condition':'committed available cash below next programme peak','action':'choose feasible nondominated reduced tranche under budget, preserve earlier viable candidates; if none do not sign new commitments','numeric_budget_RUB':None},
        {'id':'F_NONE_NEW','condition':'no incremental financing authorised','action':'retain KEEP and evaluate no-new resource productivity/contract adaptation within proven funded cash; do not claim these have zero cost','numeric_budget_RUB':None}
      ],'assumption_ids':['P10-CASH','P10-NORMALIZE','P10-CREW']}
    jwrite('financing_thresholds.json',equations)

def bridge():
    key=['programme_id','programme_version','fleet_scope_id','external_scenario_id','delivery_calendar_id','market_version','choice_version','cost_version','response_policy_id','evaluation_mode','decision_date','information_set_id','keep_evaluation_id','input_manifest_sha256','period_start','period_end','cash_start','price_year','affected_scope_id','metric_version','reporting_adapter_version','whole_business_KEEP_version','P11_experiment_version']
    b={
      'version':VERSION,'status':'STAGE_A_RESEARCH_READY_STAGE_B_INTEGRATION_PENDING',
      'as_of':ASOF,'number2_deadline':None,'first_stage':['2027-01','2028-12'],
      'primary_metric':'annual compatible reported passengers individual airline; group separate',
      'source_pins':json.loads((R/'input_manifest.json').read_text()),
      'upstream':{'P09':{'commit':None,'output_manifest_sha256':None,'evaluation_id':None,'status':'NOT_RECEIVED'},'P11':{'commit':None,'output_manifest_sha256':None,'experiment_version':None,'status':'NOT_RECEIVED'},'P06':{'commit':'982f13d9b6c378ed9581125ecc5c40f17dade6a3','contract_version':'P06-1.0','acceptance':'author42checksPASS;independentacceptancepending;toyisnotRW'}},
      'join_key':key,
      'partition_key':['month','statistical_carrier_id','domestic_or_international','regular_or_charter','aircraft_variant','affected_scope_id'],
      'passenger_event_key':['deidentified_boarding_group_id','statistical_carrier_id','reporting_flight_instance_id','origin_boarding','destination_alighting','departure_utc'],
      'commercial_event_key':['journey_id','order_id','ticket_coupon_id','service_event_id','experiment_cohort_id'],
      'rules':[
        'Отчётныепассажиры=SUMотдельныхboardinggroupswithinreportingflight),послесверкиметодики;никакогоautomaticsegments=reported.',
        'P09должендатьPиKEEPвсегозатронутогобизнесаприединомресурсе/рынке. ЕслиP09толькорегиональный,добавитьсохранённыйвнешнийKEEPпоdisjoint_scope_id;потери/перетокмеждусрезамиучитываютсясовместно.',
        'P11заказы/багаж/контактныеобращениянепассажиры. Поэкспериментальнымкогортам rerun P06успешныеисполненныеперевозки,отмены/рефанды/ноушоу и вытесненныепродажи.',
        'ЕслиP09содержитP11choice/serviceuplift,passenger_residual_P11=0bydedup,безповторногодобавленияэффекта;этоисключениедубликата,неUNKNOWNэффект=0.',
        'У digitalмаржи,тарифов,поддержки/экономиитрудадолжныбытьразныеeconomic_event_id и cash_event_id; затраты реализации один раз. Экономиявременибезизмененияплатежейнеcashsaving.',
        'Domestic/internationalиregular/charter—двеоси. Нельзядобавитьcharterкобщемуdomestic+international.',
        'Delta share=100*(P_RW/M_P - KEEP_RW/M_KEEP) одногоyear/scenario; M_P учитываетновыероссийскиеперевозки/перетокиотиностранных,доноры/отмены;airportthroughputнеиспользуется.',
        'НетвалидногоP09/P11пинаилиmapper—итоговыечислаполяnull,statusUNKNOWN;неподставлять0илиcapacitydiagnostic.'
      ],
      'outputs_pending':{'RW_reported_P_2027':None,'RW_reported_P_2028':None,'RW_reported_KEEP_2027':None,'RW_reported_KEEP_2028':None,'delta_reported_Pax_2027':None,'delta_reported_Pax_2028':None,'share_delta_pp_2027':None,'share_delta_pp_2028':None,'whole_business_incremental_operating_result_RUB':None,'whole_business_peak_funding_RUB':None,'number2_attained':None},
      'required_checks':['exactpins/hash','samecontextjoin','disjointbusinesspartitions','reportingflightmapping','samefutureKEEP','ownmigration+donorsnotdoublecount','marketdenominatorattribution','digitaldedup/experimentcausality','24monthseasoncalendar','separatefleetvariants','cashcoverage/datedcommitments','independentreview'],
      'historical_bridge':'OLD_STRATEGY_BRIDGE retained as previous version: frozen2025anchor +2028weekannualiseddiagnostic; not admitted as currentwholebusinessforecast',
      'assumption_ids':['P10-REPORT','P10-KEEP-ANCHOR','P10-DIGITAL','P10-CASH','P10-SHARE']}
    jwrite('growth_bridge.json',b)
    months=[]
    for year in (2027,2028):
      for m in range(1,13):
        months.append(dict(month=f'{year}-{m:02d}',P09_commit=None,P11_commit=None,whole_business_KEEP_version=None,reporting_adapter_version=None,RW_reported_KEEP=None,RW_reported_PROJECT=None,Russian_market_KEEP=None,Russian_market_PROJECT=None,net_new_reported_passengers=None,share_delta_pp=None,incremental_full_operating_result_RUB=None,joint_cash_before_financing_RUB=None,status='PENDING_UPSTREAM_PINS_NOT_ZERO'))
    table('growth_bridge_monthly_pending.csv',months)

def main():
    sources=source_registry();cs=claims(sources);assumption_register();competitor_scale(cs);metrics();aircraft_constraints()
    ts=thresholds();ps=productivity();ms=delivery_months(ps);gs=growth_cases(ts,ms)
    required_resources(ts,ps);finance_drivers(ms,gs);bridge()
    print(json.dumps({'version':VERSION,'claims':len(cs),'sources':len(sources),'growth_cases':len(gs),'resource_months':len(ms),'threshold2028':[(x['competition_scenario_id'],x['threshold_reported_pax']) for x in ts if x['year']==2028],'phased2028':[(x['productivity_condition'],round(x['conditional_occupied_segment_capacity']),round(x['conditional_share_delta_pp'],4)) for x in gs if x['delivery_scenario_id']=='phased' and x['year']==2028 and x['competition_scenario_id']=='C_FLAT' and x['alpha_new_to_Russian_market']==0]},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
