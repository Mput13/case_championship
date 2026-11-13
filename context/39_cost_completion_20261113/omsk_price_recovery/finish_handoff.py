from pathlib import Path
import json,csv
P=Path('/home/mputi/.t3/scratch/red-wings-team-update-20261109-b45f8804/context/39_cost_completion_20261113/omsk_price_recovery')
queries=[
'site.aeroomsk.ru "21.08.2026"',
'Омск аэропорт гостиница официальный тариф стоимость проживания',
'site.aeroomsk.ru тариф питание трансфер гостиница',
'site:aeroomsk.ru/aviakompaniyam/ "2026" "Прейскурант"',
'site:aeroomsk.ru "21.08" "2026" тарифы',
'site:aeroomsk.ru "Ставки и тарифы"',
'site:pkc.aero "16,90" багаж 2025',
'Омск трансфер аэропорт официальный прайс 2026 автобус стоимость',
'site:wm-3.ru питание завтрак стоимость']
opens=[
('open','https://www.aeroomsk.ru/aviakompaniyam/stavki-i-taryfy/','Internal Error / inaccessible'),
('open','https://www.wm-3.ru/index.php/nomera/standart-nomera','502 Bad Gateway'),
('open','https://hotelflagman.ru/ru/preyskurant-cen','success; dated primary table'),
('open','https://otel41.ru/','success; current page maintenance, no transfer quote'),
('open','https://pkc.aero/upload/iblock/4ef/l9aevzf4ka9oq29xig8g0fdtr10w6p8t/Preyskurant-na-uslugi-i-tvary-AO-MAPKE-dlya-rossiyskikh-potrebiteley-uslug-po-sostoyaniyu-01.03.2025.pdf','Internal Error / inaccessible'),
('open','https://www.aeroomsk.ru/aviakompaniyam/stavki-i-tarify/','success; 312 lines, corrected index'),
('click99','https://www.aeroomsk.ru/aviakompaniyam/stavki-i-tarify/2026/tarifs_rus_20260821.pdf','success; 11 pages; no text layer'),
('click100','https://www.aeroomsk.ru/aviakompaniyam/stavki-i-tarify/2026/pr568-2026.pdf','success; 1 page; no text layer'),
('click101','https://www.aeroomsk.ru/aviakompaniyam/stavki-i-tarify/2026/pr610-2026.pdf','success; 1 page; no text layer'),
('click40','https://www.aeroomsk.ru/partneram/arendatoram/','success; no numeric rent'),
('click68','https://www.aeroomsk.ru/ob-aeroporte/vakansii/','success; no admitted station gross salary'),
('open','https://www.wm-3.ru/index.php/pitanie','TimeoutError; primary indexed snippet 430'),
('open','https://omsk.avtobus1.ru/uslugi/transfer','success; rate from 3000/hr minimum4hr'),
('open','https://pkc.aero/upload/iblock/334/5rj03vhu6n9ju7e7ns4xaapqidi21tf7/Preyskurant-MAPKE-ot-01.01.2025g-deystvuyushchiy-na-01.01.2025-s-izm-ot-_26.01.2025_-okonch.pdf','Error fetching; one alternative then stop'),
('open','https://www.aeroomsk.ru/partneram/dogovor_otn/ano-2026.pdf','400 Content length too large 19860586; direct download succeeds')]
log=json.loads((P/'direct_calls.json').read_text())
for d in log:
 if d.get('file')=='sources/pkc.pdf':d['file']='sources/pkc_http404.html'
 if d.get('file')=='sources/pkc_alt.pdf':d['file']='sources/pkc_alt_http404.html'
(P/'direct_calls.json').write_text(json.dumps(log,ensure_ascii=False,indent=2))
actual=dict(status='completed',access_date='2026-11-13',web_search_queries=[dict(sequence=i+1,q=q) for i,q in enumerate(queries)],web_open_click_attempts=[dict(sequence=i+1,operation=op,url=u,outcome=o) for i,(op,u,o) in enumerate(opens)],web_screenshot_attempts=[dict(ref='turn4view0',page=0),dict(ref='turn4view1',page=0),dict(ref='turn4view2',page=0)],counts=dict(additional_search_queries=9,web_open_click_attempts=15,web_screenshot_attempts=3,direct_http_attempts=len(log)),direct_http_log='direct_calls.json',limits='9/12 targeted queries and 15/16 web opens/clicks; direct byte downloads and screenshot attempts separately disclosed, not hidden as successful opens',local_errors=['initial script imported unavailable bs4 before any HTTP request; replaced by stdlib regex','pdftotext returns only page separators on scanned OMS PDFs; all11 tariff pages and both amendments inspected visually; contract p5–8 inspected','Aero direct TLS expired; certificate verification not bypassed'],stopping='PKC primary + one alternative both HTTP404 then stop; Aero hotel room primary fails then Flagman alternative; no bookings/contacts; no unrelated salary substitution; no further searches')
(P/'actual_calls.json').write_text(json.dumps(actual,ensure_ascii=False,indent=2))
(P/'README.md').write_text('''# OMS price recovery — completed handoff, 2026-11-13

Запись ограничена этой папкой. Прочитаны ../TASK.md и все 6 строк ../research_omsk/price_evidence.csv. Предыдущие outputs не изменялись. Без git/commit/push, субагентов, контактов, бронирований и расчёта сетевого бюджета. Crew/MRO/lease самолёта не исследовались.

Главный результат: доступен правильный индекс `/stavki-i-tarify/`, тогда как переданный `/stavki-i-taryfy/` не открылся. Первичные bytes прайса OMS с 21.08.2026 и обоих октябрьских изменений сохранены; все 11 страниц прайса и обе страницы изменений просмотрены визуально. `pdftotext` не извлекает текст из сканов; точные строки вручную переписаны в `excerpts/oms_tables.txt`, изображения страниц сохранены в `renders/`. `sources_manifest.json` содержит размер/SHA256 и PDF magic. Не считать пустые `.txt` автоматическим отрицательным поиском.

## Готовые единичные цены

`prices.csv` — 34 строки с раздельными классификациями DIRECT_OMS, ANALOGUE_LOCAL_UNIT, ANALOGUE_DERIVED, ANALOGUE_INDEX_ONLY, UNKNOWN и REFERENCE_ONLY. Для каждой есть unit/min/max/tax/effective/source/access/page/provenance/overlap/quantity/payer/free_window. Численные прямые строки — опубликованный тариф, не доказательство дополнительных затрат RW.

- Складское хранение имущества: неотапливаемое 330, отапливаемое 1000 RUB/м²/месяц (§11.19, p10). Это услуга хранения, а не доказанная аренда самостоятельного склада.
- Стойка представителя для информирования: 1229.51 RUB/рабочее место на рейс/обслуживание (§2.3 p2), не quote DCS/check-in.
- Пропуска: постоянный до 5 лет 696.72 RUB/шт.; разовый 209.02 RUB/шт. (§5.2 p4). Сопровождение сторонних работников/транспорта 4050 RUB/обслуживание (§5.3).
- Перегрузка/снятие/погрузка груза, почты и багажа по заявке при задержках или иных причинах, в т.ч. повторная: 4450 RUB/обслуживание (§2.15 p3), НЕ RUB/kg и не автоматическая доплата за весь трансферный багаж.
- Базирование на асфальтобетоне: 117100 RUB/месяц для МВМ 30–74.999 т, 130200 для 75–99.999 т (p5 §9.1.1). Временная стоянка соответственно 1018/1140 RUB/час или 24432/27360 RUB/сутки (p6 §§9.2.1,9.3.1). Выбор схемы и пересечение со сверхнормативной стоянкой требуют договора; не суммировать схемы.
- Городской автобус OMS: 3430 RUB/начинающийся моточас (p5 §8.1). Вместимость/минимум/подача/маршрут аэропорт–отель UNKNOWN. Это прямой местный тариф услуги, не маршрутная закупка.
- Раздача бортпитания в аэровокзале: 3275 RUB/обслуживание (p2 §2.8), еда не включена в доказанную цену этой операции.
- IT: 6.23 за обработку входящей телеграммы и 55.60 за телеграмму авиационной наземной сети (p11); телефон по тарифам Ростелекома. Эти строки не заменяют DCS/интернет/установку/поддержку.

В колонке OMS написано «кроме того НДС», p11 отсылает к законодательству; численный процент для этих услуг не указан. Не применять 20%/22% без отдельной проверки. Льгота p11 явно дана для медосмотров 7.1/7.2, не переносится на другие услуги. Бесплатное окно стоянки и договорная связь §§1.1.3/9.1/9.2/9.3 UNKNOWN: прайс его не задаёт. Даты/состав изменений в `excerpts/amendments.txt`: октябрь меняет жидкости, выпуск малых ВС и условный VIP-тариф, извлечённые целевые строки не меняются.

Скачан типовой договор (24 страницы, просмотр p5–8). §6.1 p8: платит заказчик по тарифам на дату обслуживания. §6.7.1: 100% предоплата объёма обслуживания рейса, остаток в зачёт будущей предоплаты. Это потребность в оборотных средствах, не повторный расход. Подписанный RW договор/индивидуальные скидки UNKNOWN. Пересечение услуг с уже учтёнными 96089/115307 RUB ground/flight не разрешено; базовые airportfees — только REFERENCE_ONLY. Никакой допуск в годовую модель здесь не выполнен.

## Помощь пассажирам: только единичные аналоги

Официальный Флагман: стандарт RO 4100 RUB за одноместный номер/сутки, 4650 за двухместный; срок 01.02–31.12.2026, НДС не раскрыт. HTML bytes сохранены. Разница BB–RO одноместного стандарта 5050−4100=950 RUB — расчётный аналог завтрака в пакете, не отдельный quote питания. У Аэро официальный индекс показывает завтрак 430 RUB/чел при безналичном бронировании, но сама страница timeout, прямая загрузка TLS expired: только ANALOGUE_INDEX_ONLY. Цены номеров Аэро не допущены после ошибки; одна альтернатива Флагман успешно получена.

Автобус1: Нефаз 44 места, от 3000 RUB/час, минимум4 часа, следовательно от12000 RUB/заказ; верхняя граница UNKNOWN. Это каталог местного поставщика, не фиксированная цена закупленного маршрута. Не делить на 44 как доказанную цену пассажира. Частота срывов, число пострадавших, номера, ночи, рационы и заказы транспорта UNKNOWN. Никакая из этих цен не устанавливает вероятность нарушения стыковки.

PKC16.90: индекс первичного PDF явно называет перегрузку багажа с борта одного ВС на другой, RUB/kg, с01.01.2025, безНДС, по заявке авиакомпании; не обычная обработка/почта в этой строке. Но оригинальный PDF и одна январская альтернатива вернули404 (сохранены тела HTML, не PDF); веб также не получил документы. Поэтому проверка первичного PDF/page НЕ завершена и прежнее PASS не подтверждено. Строка только ANALOGUE_INDEX_ONLY; для OMS теперь имеется собственная цена §2.15 с иной единицей. По PKC поиск остановлен.

Офис, DCS/check-in оборудование, broadband, CAPEX станции и gross salary station agent остаются UNKNOWN. Официальная страница арендаторов не дала ставок; опубликованные инженерные вакансии не заменяют станционную зарплату. Вилка42–50тыс. из предыдущего вторичного агрегатора не допущена. Численность не выводится из зарплаты: FTE=Σ(посты×часы покрытия за период)/эффективный фонд часов сотрудника за тот же период, все входы UNKNOWN. Покупка оборудования и покупка handling той же функции — альтернативные варианты.

## Передача и проверка

`actual_calls.json` — фактические9 запросов из12, 15 web opens/clicks из16, отдельно3 screenshot attempts и все direct HTTP downloads/errors. Прямые загрузки не скрыты: исходный индекс403, ошибки TLS/404, затем успешные bytes OMS. `direct_calls.json` — download log, `sources_manifest.json` — bytes/hashes; `validation.csv` — проверки с refs на каждую строку и ограничениями. Индексированные сведения явно отделены от проверенных первичных bytes. `handoff.json` даёт машиночитаемый итог completed. Данные готовы для роли с модельными экспозициями; общий запуск/годовой бюджет не рассчитан.
''')
rows=list(csv.DictReader((P/'prices.csv').open()))
for r in rows:
 assert (P/r['excerpt']).is_file(),r['id']
 assert r['quantity'] and r['overlap'] and r['classification']
 if r['min']!='UNKNOWN' and r['max']!='UNKNOWN':assert float(r['min'])<=float(r['max'])
assert all((P/d['file']).exists() for d in log if 'file' in d)
(P/'handoff.json').write_text(json.dumps(dict(status='completed',objective='OMS narrow price recovery',rows=len(rows),files=['prices.csv','validation.csv','actual_calls.json','direct_calls.json','sources_manifest.json','README.md'],direct_oms_prices=sum(r['classification']=='DIRECT_OMS' for r in rows),model_admission='not performed; quantities and overlap unresolved',primary_pdf_verified=['oms_20260821.pdf all11pages','oms_amend_1010.pdf p1','oms_amend_1015.pdf p1','oms_contract.pdf p5–8 only'],unresolved=['office rental','DCS/check-in systems','broadband installation/support','station gross salary','FTE counts/coverage','free parking window and tariff stacking','disruption incidence','PKC primary PDF page verification'],validation='CSV refs exist; numeric bounds consistent; all saved downloads/log references exist; hashes recorded'),ensure_ascii=False,indent=2))
print('completed:',len(rows),'rows; direct HTTP attempts',len(log),'; local validation passed')
