#!/usr/bin/env python3
"""Build a bounded evidence handoff. No economic model is executed."""
import csv
import datetime as dt
import hashlib
import io
import json
import pathlib
import subprocess
from read_sources import PINS, read

HERE = pathlib.Path(__file__).resolve().parent
BASE = PINS['root']
NOW = dt.datetime.now(dt.timezone.utc).isoformat()
N = 'context/23_night_run_20261110/'

def dump(name, value):
    (HERE/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')

def table(name, rows):
    with (HERE/name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

E = []
def ev(id, alias, path, locator, grain, scope, limit):
    raw = read(alias, path)
    E.append(dict(evidence_id=id, source_commit=PINS[alias], source_path=path,
        exact_ref=f'{PINS[alias]}:{path}', locator=locator, grain=grain,
        sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw),
        github_url=f'https://github.com/Mput13/case_championship/blob/{PINS[alias]}/{path}',
        acceptance_scope=scope, not_established=limit,
        personal_action='Exact Git bytes hashed; indicated prose/rows inspected. Upstream reviews read, not rerun.'))

ev('E01','brief','context/00_brief/case5_requirements.md','lines 3–30','research interpretation of organiser requirements','REQUIREMENTS_SYNTHESIS','Not literal organiser text; official receipt E02 resolves wording')
ev('E03','screen',N+'screening/report.md','lines 28–46, 68–75','author replay and radius policy variants','UPSTREAM_AUTHOR_REPLAY; SCENARIO_SENSITIVITY','No economic superiority or full source verification')
ev('E04','screen_review',N+'screening_review/report.md','lines 35–60, 70–84','independent screening review','UPSTREAM_APPROVE_SCOPED','Radius/weights remain OPEN_DECISION; arithmetic is not demand validation')
ev('E05','repair',N+'model_repair/handoff.json','reproduced; policy_boundary; route_definition_warning','model-repair delivery','UPSTREAM_OWNER_DERIVATION','Use E06 for independent acceptance; no common full-budget comparison')
ev('E06','repair_review',N+'model_repair_review/report.md','lines 19–30, 44–61, 65–104','independent author-replay and conservation review','UPSTREAM_AUTHOR_REPLAY_MATCHED; CONSERVATION_PASS_SCOPED','Annual symmetric aggregates vs dated scenario week; not real OD or launch')
ev('E07','bridge',N+'data_bridge/candidate_addendum_primary17b/README.md','lines 3–13','endpoint-period mapping and holds','UPSTREAM_JOIN_CONTEXT_ONLY','Endpoint match does not match a physical flight, fare, seats or sale')
ev('E08','methods',N+'methods/handoff.json','package methods-common-v3; three_findings','common-demand and adapter owner handoff','UPSTREAM_OWNER_DERIVATION; SEE E10','Do not transfer owner acceptance to all modules')
ev('E09','methods4',N+'methods/handoff.json','package methods-strategy-v4; three_findings','portfolio/resource owner handoff','UPSTREAM_OWNER_DERIVATION; SEE E11','Not a globally optimised network')
ev('E10','common_review',N+'common_comparison_review/report.md','lines 26–59, 73–100','common-demand/adapter independent review of exact abb1','UPSTREAM_CONDITIONAL_ECONOMICS_CHECKED_SCOPED','No empirical C/N calibration; old SVX lineage HOLD; full budget unknown')
ev('E11','strategy_review',N+'strategy_accounting_review/report.md','lines 13–25, 35–104','portfolio/resource independent review of exact c24','UPSTREAM_CONSERVATION_PASS; CONDITIONAL_ECONOMICS_CHECKED_SCOPED','Fixed programs/Q(F)/local-first; no dispatch; recovery HOLD')
ev('E12','budget_review',N+'budget_review/report.md','lines 21–75, 79–94','optimistic bound for enumerated products','UPSTREAM_APPROVE_SCOPED','Bound removes market/migration constraints; not predicted profit')
ev('E13','primary',N+'primary_evidence/findings.md','lines 33–90','carrier facts and source-specific published offer context','UPSTREAM_SOURCE_REPORT; E14 limits acceptance','Old SVX receipts conflict; untracked parent22 material is inherited, not new evidence here')
ev('E14','source_review',N+'source_join_review/report.md','lines 9–46, 50–68, 82–100','source and bridge independent review','UPSTREAM_SCOPED_RAW/EXTRACTION/JOIN_CHECKED','129 SVX rows/28 cards/58 mappings HOLD; actual performed and observed OD unknown')
ev('E15','primary',N+'primary_evidence/route_product_cards.csv','card_id listed in competitor_and_svx_gaps.csv','source-specific directed offer over 7–13 Dec 2026','UPSTREAM_PUBLISHED_CONTEXT; PER-CARD HOLDS','Not complete competition; seats/fares/stop status/performed flights unknown')
ev('E16','primary',N+'primary_evidence/source_registry.csv','source_id/raw_sha256/captured_at_utc','public source receipt registry','RECEIPT_READ; CONFLICTS_RETAINED','SVX old snapshot conflict must not be silently corrected here')
ev('E17','primary',N+'primary_evidence/svx_observations.csv','svx_results_2025; nordstar_rw_2024; historical rows','annual carrier-hub aggregate and historical product','UPSTREAM_SCOPED_FACTS VIA E14; HISTORICAL_OTHER_ROWS','800k rounded; ×2.5 no absolute base; inherited parent22 rows not newly validated')
ev('E18','kover',N+'cost_kover/findings.md','lines 15–24, 32–64','scenario cost and restriction overlay','UPSTREAM_OWNER_DERIVATION; SEE E19','Do not use original delay served-all; public references are not RW contracts')
ev('E19','kover_review',N+'cost_kover_review/findings.json','CKR-P2-TIMEBASE; CKR-B01–B04','independent cost/timebase findings','CHANGES_P2_TIMEBASE; UNAFFECTED_SCOPES_PRESERVED','Timebase/day2/recovery held; day1 cancellation arithmetic not falsified')
ev('E20','timebase',N+'cost_kover_timebase_correction/README.md','lines 3–11','separate coordinator correction','PARENT_TIMEBASE_AND_DELTA_CHECK_ONLY; RECHECK_PENDING','No independent acceptance of correction; delayed service/money unavailable')
ev('E21','frontier',N+'hypothesis_frontier/handoff.json','HF01/HF07/HF14; independent_review','bounded new product experiments','OWNER_DERIVATION/PENDING','Appendix only; not independently accepted or final network')
ev('E22','methods5',N+'methods/handoff.json','methods-integration-v5; three_findings','new integrated accounting/demand overlay','OWNER_DERIVATION/PENDING','No current independent approval; no upgrade of original held sources')
ev('E23','root','context/13_competitors/competitors.json','sources S7/A4/A4M/U6/U6B; carriers s7/azimuth/ural','dated competitor profiles and public source references','INHERITED_PRIMARY_READ_OR_SOURCE_SPECIFIC_STATUS','No fresh raw re-audit; current free fleet/route profit/causality unknown')
ev('E24','core','context/16_agent_research/core/integration_v1/phase2_handoff.md','Operating/Social/C14/C07','Mikhail research-system component handoff','INHERITED_SCOPED_ACCEPTANCE; C07_SEPARATE','Not author city ranking; not validated final network')
ev('E25','critic','context/16_agent_research/critic/integration_v1/phase2_handoff.json','decision; new_material_issue; outside_review_scope','earlier independent research audit','NOT_READY_FOR_STRATEGY_OR_LAUNCH','Frozen earlier scopes; no admission of later core C07')
ev('E26','root',N+'contract.md','lines 3–5, 15–19, 35–53','user-approved operating contract','USER_CONSTRAINT','Contract topology is not measured provider performance')
ev('E27','root',N+'sol_launch_receipts.json','roles/model/provider/options/next','initial recorded four-Sol launch receipts','STATIC_PROCESS_RECEIPTS','No live polling or wall-clock concurrency audit')
ev('E28','root',N+'launch_registry_seed.json','methods.model; methods.branch','recorded second Astra launch','STATIC_PROCESS_RECEIPT','First coordinator role is specified by contract; not a measured execution trace')
ev('E29','root',N+'methods_review_resolution.json','MR05-F01; reviewed_sha; fresh_checked_sha; scope','route-unit correction and narrow parent check','PARENT_NARROW_RESOLUTION; LEGACY_LABEL_HOLD','Not new general methods approval or independent full recheck')
ev('E30','screen',N+'screening/criteria_comparison.csv','origin_model + criterion','original author criteria, weights, directions','UPSTREAM_ARITHMETIC_CHECKED VIA E04','Weights are normative; source notes not all facts established')
ev('E31','brief','context/01_primary/README.md','lines 3–13','inventory of local primary materials','PINNED_INVENTORY_ONLY','Original PDF/DOCX/DOM are local, not read from live directories here')
ev('E32','brief','context/17_research_report/network_recovery/receipts/case_brief.json','request_started_at_utc; source_sha256','historical organiser HTTP receipt','INHERITED_RECEIPT; NEW_MATCH E02','Historical full raw is not committed; receipt alone is not original content')
receipt=json.loads((HERE/'official_case_receipt.json').read_text())
E.insert(1, dict(evidence_id='E02', source_commit='', source_path='official_case_receipt.json + official_requirements.json',
    exact_ref='HTTP GET '+receipt['url'], locator='sections 5–7; request '+receipt['requested_at_utc'],
    grain='organiser requirements; current capture matching historical raw hash', sha256=receipt['sha256'], bytes=receipt['bytes'],
    github_url=receipt['url'], acceptance_scope='PERSONAL_HTTP_200; REQUIREMENT_WORDING_CHECKED',
    not_established='Industry background not independently validated; supply is a case constraint, not delivery guarantee',
    personal_action='Read text from HTTP; section wording checked; raw HTML not published'))
table('evidence_index.csv',E)

requirements=[]
def req(id,kind,loc,requirement,evidence,available,claim_ids,gap,next_step,output,status='PARTIAL'):
    requirements.append(dict(requirement_id=id,requirement_kind=kind,organizer_url='https://mai-way.ru/tasks/red-wings/' if kind.startswith('ORGANIZER') else '',
        organizer_locator=loc,requirement_paraphrase=requirement,requirement_evidence='E02;E01' if kind.startswith('ORGANIZER') else 'E26',
        existing_evidence_ids=evidence,available_result=available,allowed_claim_ids=claim_ids,gap=gap,next_action=next_step,
        reviewable_output=output,status=status,decision_status='OPEN_DECISION' if status!='DOCUMENTED' else 'USER_CONSTRAINT'))
O='ORGANIZER_REQUIREMENT'; A='CONTRACT_ANALYTICAL_STANDARD'
req('R01',O,'6 цель; 6 шаг 4','Выбрать способ роста и показать эффект для доли компании','E06;E10;E11','Есть условные результаты и границы, окончательного решения нет','C01;S01;X01','Совместно выбранная реализуемая сеть и чистый эффект','Сравнить допустимые действия с одним baseline','decision ledger + выбранная сеть + прирост доли')
req('R02',O,'6 шаг 1; 7.1 рейтинг','Сократить перечень не менее десяти городов до трёх с опубликованными баллами','E03;E04','Воспроизведены варианты на 20 городах и исторический набор на 10','C02;C03','Командный основной режим допуска и тройка','Зафиксировать policy и сохранить остальные варианты','20 строк исходных значений + итоговая тройка')
req('R03',O,'6 шаг 1','Назвать критерии, веса и обосновать их','E04;E30','Сохранены веса Анастасии, stage22 и stage11; проверена чувствительность','C03;X02','Нормативное объяснение принятого профиля','Обсудить смысл шкал; не подгонять веса под город','подписанный профиль + чувствительность + UNKNOWN')
req('R04',O,'6 шаг 2','Разобрать хотя бы двух перевозчиков с региональными базами и применимость их опыта','E23;E14;E15','S7: Новосибирск/Иркутск; Азимут: Минеральные Воды и другие опубликованные базы; конкретные предложения','C06;C07','Механизм результата и сопоставимость затрат/расписаний, не только масштабы','Оформить две карточки с фактами, неизвестным и переносимым механизмом','две доказательные карточки конкурентов')
req('R05','ORGANIZER_CONTEXT','1 опыт хаба; 3.3; 5','Использовать опыт Екатеринбурга как материал для проверки нового хаба','E14;E17','Есть округлённый итог RW за 2025 и исторический партнёрский продукт','C05;X03','Абсолютный трансфер, причинный эффект, P&L не опубликованы','Развести факт роста, механизм и недоказанный финансовый результат','краткий SVX case с отдельными unknown')
req('R06',O,'5; 6 шаг 3','Посчитать хаб и прямую межрегиональную программу','E06;E10;E11','Есть разные авторские модели и контролируемое общее сравнение части программ','C01;S01;S05','Одинаковый период и полный ресурс итоговых альтернатив','Не складывать разные модели; оформить common input set','две сравнимые программы и вариант KEEP')
req('R07',O,'6 шаг 3','Для каждого варианта дать пассажиров, выручку и изменение доли','E06;E10','Поездки, сегменты и один тариф в условных ledgers сверены','C09;X04','Общий annual effect, каннибализация и совместимый знаменатель','Согласовать учёт перевозок RW и рынка; отдельно конечные поездки','таблица пассажиры/выручка/доля и reconciliation')
req('R08',O,'6 шаг 3','Для обеих гипотез показать основной и осторожный сценарии','E06;E10;E12','Сценарии уже есть, часть предпосылок закрытая или нормативная','S02;S03;S04','Обоснованные ranges и одинаковый денежный базис','Разделить источник, owner assumption и стресс','scenario registry + таблица 2×2')
req('R09',O,'6 шаг 3; блок происхождения пассажиров','Указать кресла, загрузку, тариф и частоту, метод оценочных данных','E06;E10;E18','Методы доступны; нет эмпирической калибровки всех параметров','C10;X05','Происхождение/диапазон/единица каждого закрытого параметра','Составить реестр без нулей вместо unknown','parameter registry + sensitivity')
req('R10',O,'6 блок происхождения пассажиров','Для каждой пары представить годовых пассажиров, недельные рейсы и источник либо метод','E07;E10;E15','Есть source cards и сценарные оценки, разных grain/периодов','C10;C07;X06','Полная таблица выбранных пар, сезонность и uncertainty','Связать каждую пару с методом; published supply отделить от OD','route/source-method table без пустой provenance')
req('R11',O,'6 шаг 4; 7.1 карта','В финальном варианте показать 8–12 связей между городами','E06;E11;E29','8 треугольных программ дают 20/18 model endpoint pairs; четырёхлучевой пилот меньше требования','C04;X07','Финальная сеть в ясной маршрутной единице','Выбрать 8–12 canonical endpoint pairs; раскрыть physical legs и itinerary','route register + incidence + карта')
req('R12',O,'6 шаг 4','Оценить потребность в самолётах, учитывая поступление новых SJ-100 лишь со второй половины 2027','E02;E06;E11','Есть сценарные envelopes и planning-label calendars','C08;S05;X08','Реально доступный парк, резерв и delayed-delivery scenario','Отдельно existing/occupied/additional; проверить calendar и next assignment','fleet-year table + resource gate')
req('R13',O,'5 две гипотезы','Смешанный вариант допустим при явном распределении самолётов между частями','E11','Совместный учёт отдельных программ проверен; готовой mixed стратегии нет','S06;X09','Допустимый совместный календарь и полноценные 8–12 связей','Сравнить mixed с hub/direct/KEEP при одном потолке','allocation table без двойного расхода рынка/борта')
req('R14',O,'6 шаг 5; 7.2','Дать этапы запуска до 2028 и риски парка, закрытий, конкурентов, субсидий','E11;E18;E19;E20','Есть стресс и точные причины HOLD; срок прекращения ограничений неизвестен','C08;S07;X10','Решения о сети, ресурсах и договорных расходах','Собрать gate-based roadmap с веткой задержки/остановки','roadmap 2026–2028 + risk register')
req('R15',O,'6 ИИ; 7.1 материалы','Описать задачи и инструменты ИИ, способ проверки и приложить исследовательские материалы','E24;E25;E26;E27;E28','Приложение различает роли, независимые review и owner self-check','C11;C12;X11','Командное описание собственного вклада/использования','Перенести краткий текст приложения и ссылки на exact пакеты','AI appendix + паспортная строка')
req('R16',O,'7.1 паспорт','Подготовить паспорт объёмом 1–2 страницы по шаблону: решение, данные, эффект, ограничения, ИИ','E01;E31','Готовы тезисы и матрица; локальный шаблон здесь не читался','C01;X01','Выбор и обоснованный эффект; актуальный шаблон','После выбора заполнить шаблон, проверить страницы и числа','паспорт 1–2 страницы','GAP')
req('R17',O,'7.1 рейтинг','Передать таблицу исходного перечня, весов, баллов и тройки','E03;E04;E30','Сохранённые таблицы воспроизводимы','C02;C03','Выбранный для сдачи профиль','Экспортировать без изменения dashboard','таблица рейтинга','PARTIAL')
req('R18',O,'7.1 сравнение','Передать расчёт сравнения таблицей или кодом','E06;E10;E11;E12','Воспроизводимые пакеты есть; final network пока нет','S01;S02;X01','Согласованная сводная таблица и исполнимый recipe','Закрепить input set и units; указать acceptance','таблица + exact refs + команды')
req('R19',O,'7.1 карта','Передать схему выбранных прямых связей','E06;E11','Карточки пилотов пригодны как вход, не финальная карта','C04;X07','8–12 выбранных связей и их единица','Строить карту после joint gate','схема с легендой routes/legs/OD','GAP')
req('R20',O,'7.1 срок','Отправить заочный комплект 10 ноября до 23:59','E02','Дата и комплект сверены по странице','C10','Проверка формы, файлов и факта подачи','Командный участник проверяет upload и receipt','submission checklist + receipt','DOCUMENTED')
req('R21',O,'7.2 защита 13 ноября','К защите обновить паспорт, дать 5–8 слайдов и выступление до пяти минут; roadmap обязателен','E02','Требования защиты отделены от ночного пакета','C10','Редактура, визуальная проверка и репетиция','После расчётов собрать narrative и проверить рендер','5–8 слайдов + обновлённый паспорт + roadmap','DOCUMENTED')
req('A01',A,'contract: market_pool / itinerary_leg','Один общий конечный рынок, места каждого плеча и один сквозной тариф','E06;E11','Проверены scoped conservation и migration rules','C09;S06','Совместная финальная сеть','Проверить shared pools/incidence на final input','conservation report')
req('A02',A,'contract: полный бюджет / resource','Разделить переменный вклад, полный бюджет, cash и альтернативу ресурса','E11;E12;E18;E19','Есть пороги; unknown сохранены','S02;S04;X12','Base/MRO/crew/reserve/start/working capital/support/exit/donor','Не складывать упущенную выручку с той же маржой; задать ranges','full strategy ledger + cash limitations')
req('A03',A,'contract: диапазоны / границы','Проверить условия смены вывода и остановки','E10;E11;E12','Пороговые расчёты приняты в узком сценарном scope','S01;S02;S03;S04','Owner ranges и критерий отказа для выбранного действия','Сначала задать критерий; затем bounded experiment','boundary table + rejected outcomes')
req('A04',A,'contract: Ковёр / время','Сохранить no-kover, сценарий ограничений и прекращения без прогноза даты','E18;E19;E20;E11','P2 установлен; отдельная correction ещё PENDING','S07;X10','Независимый recheck correction и feasible recovery','Удерживать delay served-all/деньги; решить либо оставить HOLD','review receipt + no-kover comparison')
req('A05',A,'contract: provenance / UNKNOWN','Не повышать старые SVX source holds и новые pending опыты','E14;E21;E22','Границы версии явно закреплены','C12;X06;X13','Новые pinned independent review receipts','Принять только новый scope после review, не движущуюся ветку','acceptance matrix')
table('requirements_evidence.csv',requirements)

claims=[]
def claim(id,group,text,evidence,scope,condition,prohibited,requirements):
    claims.append(dict(claim_id=id,group=group,ready_russian_wording=text,evidence_ids=evidence,acceptance_scope=scope,
        use_condition=condition,prohibited_extension=prohibited,requirement_ids=requirements))
U='МОЖНО_СЕЙЧАС'; S='УСЛОВНЫЙ_СЦЕНАРИЙ'; X='НЕЛЬЗЯ_УТВЕРЖДАТЬ'
claim('C01',U,'Материалы Анастасии, Цири и исследовательская система Михаила решают разные задачи: отбор города, расчёт сети и проверку источников/продуктов. Для итогового решения согласуются период, единицы и ресурс, а авторские результаты сохраняются отдельно.','E03;E06;E24;E26','PURPOSE_AND_PROVENANCE','Не называть эти работы тремя равноготовыми финансовыми моделями.','Нельзя усреднять баллы и объявлять общую победу.','R01;R06;R16')
claim('C02',U,'Арифметика сохранённых рейтингов воспроизведена. При пороге 500 км у Анастасии тройка — Омск, Оренбург, Самара; у stage22 Цири — Омск, Оренбург, Барнаул. Это результаты разных правил оценки, а не выбор прибыльной сети.','E03;E04','UPSTREAM_AUTHOR_REPLAY_MATCHED_SCOPED','Авторские версии и их шкалы названы; источники всех ячеек заново не приняты.','Тройка не является доказательством спроса, прибыли или готовности базы.','R02;R17')
claim('C03',U,'Порог 500 км и основной профиль весов остаются открытым решением команды. Организаторы предлагают удалённость как возможный критерий; обязательный численный радиус ими не установлен.','E02;E04;E30','REQUIREMENT_WORDING; OPEN_DECISION','Сохранить исходные веса и отдельно чувствительность к 0/300/500/800 км.','Не объявлять ни отсутствие фильтра, ни 500 км объективно лучшей политикой.','R02;R03')
claim('C04',U,'Восемь треугольных программ исходной модели Анастасии образуют 20 пар конечных пунктов в основном и 18 в осторожном сценарии. Это модельные пары, включая агрегат Москвы; их нельзя автоматически назвать восемью лучами или восемью физическими аэропортовыми маршрутами.','E06;E29','UPSTREAM_ROUTE_UNIT_CHECKED','Считать отдельно программу, пару концов, датированное плечо и пассажирскую поездку.','Соблюдение финального требования 8–12 ещё не установлено.','R11;R19')
claim('C05',U,'По сообщению Red Wings от 4 февраля 2026 года, через её хаб в Екатеринбурге в 2025 году перевезено около 800 тыс. пассажиров, а трансфер вырос в 2,5 раза. Публикация подтверждает сообщённый рост, но не раскрывает абсолютный трансфер и финансовый результат хаба.','E14;E17','UPSTREAM_SCOPED_SOURCE_FACT; CARRIER_REPORTED','Годовой округлённый carrier-hub aggregate; самостоятельный от old schedule lineage факт.','Нельзя вывести долю трансфера, конечный OD, прибыль или коэффициент нового хаба.','R05')
claim('C06',U,'S7 использует региональные хабы Новосибирска и Иркутска; Азимут публикует базирование в Минеральных Водах и других аэропортах и развивает прямые региональные связи на SSJ. Эти два аналога дают разные механизмы для проверки: стыковочную сеть и прямой региональный продукт.','E23','INHERITED_PRIMARY_READ; SOURCE_SPECIFIC','Факт базирования взят из закреплённого обзора; в этой задаче raw заново не читался.','Их прибыль, свободный парк и переносимость масштаба на RW не установлены.','R04')
claim('C07',U,'В опубликованной программе на 7–13 декабря 2026 года Уфа—Минеральные Воды имеет по четыре вылета в каждом направлении Азимута, Уфа—Нижневартовск — по четыре Utair, Уфа—Нижний Новгород — по два Nordwind. Это предложение по расписанию; выполнение, кресла и реальные продажи не подтверждены.','E14;E15','UPSTREAM_RAW/EXTRACTION/JOIN_CHECKED_RULES','Не складывать две публикации одного вылета; carrier label не заменяет operating-role proof.','Частота не равна свободному спросу или обоснованной capture share.','R04;R10')
claim('C08',U,'В итоговом предложении новые SJ-100 можно закладывать не раньше второй половины 2027 года — таково ограничение задания. Это условие кейса; дата фактической поставки и доступное дополнительное число бортов остаются неизвестными.','E02;E11','REQUIREMENT_CONSTRAINT; RESOURCE_LIMITATION','Существующий, занятый и дополнительный парк показывать раздельно; предусмотреть задержку.','Нельзя обещать поставку или доступный парк по общему числу самолётов компании.','R12;R14')
claim('C09',U,'В проверенных сценарных таблицах пересадочная поездка расходует место на каждом плече, а сквозной тариф учитывается один раз. Переток с собственных рейсов RW выделяется отдельно и не считается новым клиентским путешествием компании.','E06;E11;E14','UPSTREAM_CONSERVATION_PASS_SCOPED','Это свойство проверенных ledgers, а величина миграции остаётся сценарной.','Нельзя назвать сценарные поездки наблюдёнными продажами или уникальными людьми.','R07;A01')
claim('C10',U,'Задание допускает расчётные и синтетические оценки при раскрытых методе и предпосылках. Для каждой выбранной пары нужны годовой объём пассажиров, недельная частота и источник либо способ оценки.','E02;E01','PERSONAL_REQUIREMENT_WORDING_CHECKED','Даты/комплект сдачи см. requirements_evidence.csv; это не отказ от сценарной экономики.','Закрытый OD не даёт права выдать кресла за наблюдённый спрос.','R09;R10;R20;R21')
claim('C11',U,'ИИ использовался для исследования, воспроизведения моделей и отдельных независимых проверок. В пакете сохранены закреплённые входы, найденные дефекты, исправления и границы приёмки; самостоятельная проверка автора отделена от независимого review.','E06;E10;E11;E14;E19;E26;E27;E28','STATIC_PROCESS_RECORDS; UPSTREAM_REVIEW_EVIDENCE','В этой задаче выполнен синтез и проверка ссылок/чисел, без нового экономического расчёта.','Количество файлов/проверок не измеряет качество или преимущество модели.','R15')
claim('C12',U,'Новые опыты frontier, интеграция methods v5 и отдельная timebase correction включены как материалы, ожидающие независимой проверки. Их статус не изменён по текущей ветке или факту push.','E20;E21;E22','OWNER_DERIVATION/PENDING','Срез ограничен точными SHA brief; более поздние review сюда не импортируются.','Не использовать pending как уже проверенное основание выбора.','R15;A05')
claim('S01',S,'При фиксированных расписании, тарифах, затратах и local-first результат сравнения прямой программы из Екатеринбурга с четырёхлучевой программой Уфы меняется при смешении двух сценарных рецептов спроса около α=0,683509. В точке смены оба вклада отрицательны — примерно −3,168 млн рублей за неделю.','E10','UPSTREAM_CONDITIONAL_ECONOMICS_CHECKED','Только exact abb1, base C→N; α — координата сценария, не вероятность.','Не утверждать преимущество хаба на рынке или эмпирическую калибровку спроса.','R01;R06;R18;A03')
claim('S02',S,'При осторожных тарифах и расходах все четыре рассмотренные программы имеют отрицательную верхнюю границу вклада даже при продаже всех мест местным пассажирам. Рост только спроса в перечисленном наборе продуктов не устраняет убыток при сохранённых тарифах, рейсах, издержках и ёмкости.','E12','UPSTREAM_APPROVE_SCOPED_BOUND','Оптимистичное расширение без миграции и дополнительных расходов; только перечисленные продукты.','Не распространять на любую иную сеть, новый тариф/доход или другую себестоимость.','R08;R18;A02;A03')
claim('S03',S,'В основном сценарии с сохранённым перетоком RW прямой программе из Екатеринбурга не хватает спроса даже при насыщении мест: предельный вклад остаётся −449 822,70 рубля за неделю. Для программ Уфы первый ноль достигается при умножении рецепта C примерно на 2,462 и 2,919 для четырёх и восьми лучей, до неизвестных расходов полного бюджета.','E10','UPSTREAM_CONDITIONAL_ECONOMICS_CHECKED','Exact abb1; local-first; фиксированы migration, fare, costs, supply.','Множители не прогноз спроса; другая очередь/миграция меняет границу.','R08;A03')
claim('S04',S,'При одинаковых неизвестных прочих расходах четырёхлучевая программа Уфы в основном сценарии имеет меньшие условные потери, чем прямой контур из Екатеринбурга, пока сумма дополнительной недельной стоимости борта и базы меньше 2 703 326,68 рубля. Это сравнение потерь, а не положительная прибыль.','E11','UPSTREAM_CONDITIONAL_RELATIVE_BUDGET','F+B bound; F и B неотрицательны и имеют одинаковое определение; O одинаковы.','Нельзя опустить различия O, donor или выдать порог за реальные договорные расходы.','A02;A03')
claim('S05',S,'Верхний ресурсный лимит четыре рабочих борта при шести днях по десять блок-часов даёт 240 блок-часов. Он отличается от авторского лимита девять рабочих бортов при семи днях. Прохождение часовой границы само по себе не подтверждает календарь, экипажи и слоты.','E11','UPSTREAM_RESOURCE_TRANSFORMATION_CHECKED','Разные envelopes сохраняются, а common scenario задаётся отдельно.','Нельзя объявить семидневный авторский расчёт ошибочным из-за другого лимита.','R06;R12')
claim('S06',S,'Под предложенным законом общего частотного захвата совместный вклад двух прямых программ в основном сценарии на 446 063,89 рубля в неделю ниже суммы их отдельных вкладов. Разница учитывает потери уже выбранному продукту; она не доказывает превышение исходными продажами всего рынка.','E11','UPSTREAM_CONDITIONAL_PORTFOLIO_CONSERVATION','Exact c24; pooled Q(F), fixed products, local-first, общий migration cap.','Q(F) — AGENT_PROPOSAL, а не единственно возможное исправление; standalone результаты не суммировать.','R13;A01')
claim('S07',S,'Сценарий переноса уфимской волны на следующие сутки нельзя считать доступным полным обслуживанием: независимая проверка показывает пик восемь одновременно летящих бортов при исходном ресурсе четыре рабочих плюс резерв. Нужен новый календарь восстановления; до него обслуженные поездки и деньги delay-ветви удерживаются.','E11;E19;E20','UPSTREAM_COUNTEREXAMPLE; CORRECTION_PENDING','Проверен ресурсный контрпример; correction сама не получила независимый recheck.','Не использовать delay served-all, нулевую стоимость ожидания или прогноз даты окончания ограничений.','R14;A04')
claim('S08',S,'Замена стоимости 500 рублей на конечную поездку стоимостью 500 рублей на каждый из двух сегментов увеличивает иллюстративный порог покрытия миллиона рублей с 67 до 72 возвратных клиентов при тарифе 8000 рублей. Это изменение единицы предпосылки, не установленная ошибка автора.','E11','UPSTREAM_UNIT_BRIDGE_CHECKED','Сценарная иллюстрация; 134/144 односторонние поездки и 268/288 посадок.','Нельзя записать эти числа как наблюдённый спрос или прогноз продаж.','A01;A03')
claim('X01',X,'Уже выбрана прибыльная итоговая сеть Red Wings на 8–12 маршрутов.','E06;E10;E11','NOT_ESTABLISHED','В разрешённом срезе такой совместно принятый результат отсутствует.','Нужны единая сеть/ресурс/бюджет/denominator и решение команды.','R01;R16;R18')
claim('X02',X,'500 км и новые веса утверждены командой либо объективно оптимальны.','E04;E30','OPEN_DECISION','Разрешены исходные варианты и явно помеченные предложения.','Радиус и веса не определяются одной арифметической проверкой.','R03')
claim('X03',X,'800 тыс. и рост трансфера в 2,5 раза доказывают прибыльность хаба или абсолютный конечный спрос.','E14;E17','NOT_ESTABLISHED','Допустим только округлённый опубликованный агрегат с периодом.','Нет абсолютного transfer denominator, OD и P&L.','R05')
claim('X04',X,'Сценарные поездки равны уникальным людям и могут без согласования заменить пассажиров в доле рынка.','E01;E06;E14','INCOMPATIBLE_UNITS','Рыночная доля требует совместимых числителя/знаменателя и периода.','Transfer boardings, airport counts и OD journeys различны.','R07')
claim('X05',X,'Кресла, расписание и типовая загрузка являются наблюдённым спросом и фактическим выполнением.','E14;E15','NOT_ESTABLISHED','Это сценарное предложение/опубликованные правила.','Нет продаж, реальной конфигурации, выполнения и измеренной capture.','R09')
claim('X06',X,'Если карточка конкурента не найдена, конкурентов нет; весь исходный SVX слой принят по источникам.','E14;E10','UNKNOWN; SOURCE_LINEAGE_HOLD','129/28/58 остаются на HOLD; unmatched market остаётся UNKNOWN.','Отсутствие строки не ноль; исправленный registry требует нового review.','R10;A05')
claim('X07',X,'Любой пилот обязан иметь 8–12 маршрутов, а восемь треугольников автоматически удовлетворяют заданию.','E02;E06;E29','WRONG_SCOPE_AND_UNIT','8–12 относится к выбранному итоговому решению.','Исследовательский пилот может быть меньше; его нельзя выдать за весь deliverable.','R11;R19')
claim('X08',X,'Новые SJ-100 гарантированно доступны в конкретном количестве во второй половине 2027.','E02;E11','UNKNOWN_SUPPLY','Это earliest case constraint, не поставочный договор.','Нужна ветка задержки и отдельно доступный парк.','R12')
claim('X09',X,'Сумма результатов разных альтернатив является результатом смешанной стратегии.','E11','NOT_ESTABLISHED','Нужны совместные рынки, места, борта и база.','Нельзя повторно выдать один резерв или один собственный инвентарь.','R13')
claim('X10',X,'Все пассажиры перенесённой волны обслужены без дополнительных средств, а дата окончания Ковра известна.','E11;E19;E20','HOLD; UNKNOWN','Существующий delay plan не имеет необходимого ресурса.','Не превращать условную cash fixture завершения в available recovery.','R14;A04')
claim('X11',X,'Архитектура двух Astra и пула Sol доказанно быстрее или точнее других моделей/провайдеров.','E26;E27;E28','NOT_MEASURED','Есть контракт и static receipts, нет сравнительного эксперимента.','Файлы, проверки и модельные названия не являются оценкой эффекта.','R15')
claim('X12',X,'Переменный вклад является полным бюджетом, прибылью или кассовым резервом компании.','E11;E12;E18;E19','UNKNOWN_NOT_ZERO','Статьи базы/пуска/парка/выхода/оборотного капитала/donor сохраняются.','Неизвестные расходы нельзя заменять нулём или дважды вычитать donor.','A02')
claim('X13',X,'Owner self-check, push или более новая moving ветка снимают source/market/review holds.','E20;E21;E22;E26','NOT_ACCEPTED','Только новый exact review с указанным scope меняет acceptance.','Pending appendix не проверенный тезис стратегии.','A05')
table('claims.csv',claims)

weights=list(csv.DictReader(io.StringIO(read('screen',N+'screening/criteria_comparison.csv').decode())))
table('author_weights.csv',[dict(model=r['origin_model'],criterion=r['criterion'],label=r['label'],direction=r['direction'],raw_weight=r['weight'],normalized_weight=r['normalized_weight'],source_evidence_id='E30',status='AUTHOR_PROPOSAL; team final weights OPEN_DECISION') for r in weights])

official=[]
for r in requirements:
    if r['requirement_kind'].startswith('ORGANIZER'):
        official.append(dict(requirement_id=r['requirement_id'],section=r['organizer_locator'],requirement_paraphrase=r['requirement_paraphrase']))
dump('official_requirements.json',dict(url=receipt['url'],captured_at_utc=receipt['requested_at_utc'],raw_sha256=receipt['sha256'],
    raw_bytes=receipt['bytes'],historical_receipt_evidence='E32',historical_hash_matches=True,
    extraction='Human-checked paraphrases of sections 5–7 and explicitly labelled organiser context; not full HTML republication.',
    requirements=official,source_background_policy='Industry descriptions on organiser page are not independent verification of market facts.'))
# Keep the receipt and concise structured paraphrase, not a full copy of the page.
fulltext=HERE/'official_case_text.txt'
if fulltext.exists(): fulltext.unlink()

dump('input_pins.json',dict(prepared_base=BASE,pins=PINS,cutoff_policy='Only the exact SHA set in root passport_bridge brief; no moving/live inputs; new official HTTP wording receipt is expressly allowed.',
    root_brief=f'{BASE}:{N}briefs/passport_bridge.md',independent_acceptance_updates='Not imported beyond brief pins',new_source=receipt,
    memory='Registry used only for source/metric caution; no memory facts used as case evidence.'))

names={'UFA':'Уфа','MRV':'Минеральные Воды','NJC':'Нижневартовск','GOJ':'Нижний Новгород','KUF':'Самара','OMS':'Омск','SVX':'Екатеринбург','GSV':'Саратов','VOG':'Волгоград','NSK':'Норильск'}
cards=list(csv.DictReader(io.StringIO(read('primary',N+'primary_evidence/route_product_cards.csv').decode())))
registry=list(csv.DictReader(io.StringIO(read('primary',N+'primary_evidence/source_registry.csv').decode())))
reg={r['source_id']:r for r in registry}
examples=[]
def example(id,kind,subject,carrier,period,product,count,unit,coverage,refs,url,raw_hash,acceptance,gap,next_check,source_ids='',card_ids='',flight='',dates='',clock='',source_rows=''):
    examples.append(dict(example_id=id,kind=kind,subject=subject,carrier=carrier,reference_period=period,product_type=product,
        published_count=count,unit=unit,flight=flight,departure_dates=dates,source_card_ids=card_ids,source_ids=source_ids,
        exact_evidence_ids=refs,source_urls=url,raw_sha256=raw_hash,source_rows=source_rows,clock_status=clock,
        coverage=coverage,acceptance_scope=acceptance,gap=gap,next_check=next_check))
selected=['RPC008','RPC052','RPC026','RPC027','RPC053','RPC054','RPC029','RPC055','RPC013','RPC022','RPC014','RPC028','RPC030','RPC031','RPC033','RPC005','RPC012']
for cid in selected:
    r=next(x for x in cards if x['card_id']==cid)
    ids=r['source_ids'].split(';'); rr=[reg.get(s,{}) for s in ids]
    kuf=any(s.startswith('kuf') for s in ids); oms='omsk_winter_2026' in ids
    route=f"{names[r['origin']]} → {names[r['destination']]}"
    meaning='Контекст местного рынка луча Уфы; ещё не спрос RW.'
    if {r['origin'],r['destination']}=={'KUF','MRV'} or {r['origin'],r['destination']}=={'KUF','NJC'} or r['origin']=='OMS' and r['destination'] in ('MRV','NJC'):
        meaning='Прямая опубликованная альтернатива конечной поездке через Уфу; проверять обе даты и полную цену.'
    if r['own_RW']=='true': meaning='Существующее опубликованное предложение RW; возможный перенос своих продаж считать отдельно.'
    gap='Неизвестны фактическое выполнение, независимый stop-status, конфигурация/свободные места, финальная сопоставимая цена, продажи и OD.'
    if kuf:gap+=' Год 2026/27 в коротком правиле назначен по сезону; это условная календарная интерпретация.'
    acceptance='UPSTREAM_RULE_EXTRACTION_JOIN_CHECKED; NOT_PERFORMED'
    if oms:acceptance='INHERITED_CORE_EXTRACTION_JOIN; PRIMARY_RAW_NOT_REAUDITED_HERE'
    if cid in ('RPC005','RPC012'):
        acceptance='UPSTREAM_OWNER_PUBLISHED_CONTEXT; ENDPOINT_JOIN; INDEPENDENT_RAW_DATE_CHECK_NOT_CLAIMED'
    example('K'+cid[3:],'ROUTE_OFFER',route,r['carrier'],r['period_start']+'/'+r['period_end'],
        'Опубликованный direct/next-leg; физическая беспосадочность не подтверждена',r['one_way_departures'],
        'вылеты в одном указанном направлении за семь дней; не обороты и не пассажиры',
        meaning+' Одна source-specific карточка; рынок не исчерпан, другую публикацию не прибавлять.',
        'E15;E16;E14'+(';E24' if oms else ''),r['source_urls'],r['raw_sha256'],acceptance,gap,
        'Разрешить applicable year/stop/operator; сверить тот же период и basket fare до изменения capture.',
        source_ids=r['source_ids'],card_ids=cid,flight=r['flight'],dates=r['departure_dates'],clock=r['clock_consensus_status'],source_rows=r['source_rows'])

j=json.loads(read('root','context/13_competitors/competitors.json'))
src={s['id']:s for s in j['sources']}
example('P01','REGIONAL_BASE_PROFILE','S7: Новосибирск и Иркутск','S7 Airlines','срез обзора 2026-11-08; показатель перевозок 2025','Сеть с региональными хабами','','не расписание; базирование и инфраструктура',
    'Два региональных хаба, разные классы вместимости и инфраструктура группы. Переносимый механизм для проверки — полная поездка и система поддержки.',
    'E23',src['S7']['url'],'NOT_IN_PINNED_OVERVIEW','INHERITED_PRIMARY_READ; NO_FRESH_RAW_REAUDIT',
    'Наличие хаба не доказывает конкретную продаваемую стыковку, свободный флот, прибыльность или причинный эффект. Частота выбранных OD неизвестна.',
    'Для выбранной пары проверить дни/стыковку/багаж/сквозную цену и ресурс поддержки.',source_ids='S7')
example('P02','REGIONAL_BASE_PROFILE','Азимут: Минеральные Воды, Внуково, Краснодар, Сочи','Азимут','выпуск №97: итоги 2025; snapshot обзора 2026-11-08','Региональные прямые линии на SSJ','','не расписание; опубликованные базовые аэропорты',
    'Тип и продукт ближе RW; полезна проверка сезонных прямых линий и поддержки. Базы относятся к опубликованному перечню, не доказанному свободному ресурсу сегодня.',
    'E23',src['A4']['url']+';'+src['A4M']['url'],'NOT_IN_PINNED_OVERVIEW','INHERITED_PRIMARY_READ; NO_FRESH_RAW_REAUDIT',
    'Годовой поток не объясняет коммерческий результат; фактические субсидии, издержки и доступный парк неизвестны.',
    'Соединить профиль с конкретными K013/K014/K026–K027/K053–K054 без переноса чужой прибыли или capture.',source_ids='A4;A4M')
example('P03','COMPETITOR_PROFILE','Уральские авиалинии в Екатеринбурге','Уральские авиалинии','обзор 2026-11-08; годовой показатель 2025','Перевозчик общего опорного аэропорта','','не расписание; профиль конкурента',
    'При разработке новых линий из Екатеринбурга обязательна проверка локальных альтернатив этого перевозчика; общая база не доказывает feeder partnership.',
    'E23',src['U6']['url']+';'+src['U6B']['url'],'NOT_IN_PINNED_OVERVIEW','PRIMARY_SEARCH_INDEX + SECONDARY_SEARCH_INDEX; LIMITED',
    'Не новая независимая проверка базирования/выполнения/маршрутных долей. Текущие частоты каждой пары не установлены профилем.',
    'Сравнить конкретные OD выбранного списка, время возврата и basket fare.',source_ids='U6;U6B')
svx=list(csv.DictReader(io.StringIO(read('primary',N+'primary_evidence/svx_observations.csv').decode())))
for metric,sid,eid in [('RW hub passengers reported','svx_results_2025','V01'),('hub passengers growth reported','svx_results_2025','V02'),('transfer passenger ratio reported','svx_results_2025','V03'),('codeshare/connection product','nordstar_rw_2024','V04'),('RW partner routes listed','nordstar_partners_current','V05')]:
    r=next(x for x in svx if x['source_id']==sid and x['metric']==metric)
    product='Carrier-hub aggregate' if sid=='svx_results_2025' else 'Исторический direct/codeshare/advertised transfer' if sid=='nordstar_rw_2024' else 'Список партнёрских направлений'
    subject='Екатеринбург: '+metric
    if eid=='V04':subject='Лето 2024: Норильск—Екатеринбург—Саратов; Екатеринбург—Волгоград и Екатеринбург—Саратов с разными физическими перевозчиками'
    if eid=='V05':subject='Партнёрский список: Норильск—Челябинск и Екатеринбург—Саратов; не проверенная сквозная продажа'
    example(eid,'SVX_FACT' if sid=='svx_results_2025' else 'SVX_PRODUCT',subject,
        'Red Wings' if sid=='svx_results_2025' else 'NordStar / Red Wings',r['reference_period'],product,r['value'],r['unit'],
        r['applicability_to_new_hub'],'E17;E16;E14',r['source_url'],r['raw_sha256'],
        'UPSTREAM_SCOPED_SOURCE_FACT' if eid in ('V01','V02','V03','V04') else 'INHERITED_CURRENT_PAGE_SNAPSHOT; NO_FRESH_REAUDIT',
        r['not_established'],'Отделить объявленный/сообщённый продукт от выполнения, paid transfer и P&L; не переносить коэффициент на новый хаб.',source_ids=sid)
example('V06','SVX_LINEAGE_HOLD','Унаследованный слой расписания Екатеринбурга','несколько source carrier labels','публикации 08/09.11; target week 7–13.12.2026','Published servicing rows','129/28/58','строки публикаций / карточки / addendum mappings',
    'Registry ссылается на другой capture/raw hash. Это не новый вывод о неверном спросе или экономике.',
    'E14;E10','https://ar-svx.ru/schedule/','MULTIPLE; SEE E14','SOURCE_VERSION_LINEAGE_HOLD_P2',
    'Нельзя повышать SOURCE_SUPPORTED или performed-flight приёмку исходных 129 строк/28 карточек/58 mappings.',
    'Новый pinned registry с FK source_id+raw_hash+capture_date, затем отдельный независимый recheck.')
example('G01','COVERAGE_GAP','Конечные пары листьев хабовых программ Уфы','UNKNOWN','7–13.12.2026','Coverage of possible endpoint pairs','10/56;2/12','положительные directed endpoint пары / все комбинации листьев H8/H4',
    'Полные комбинации листьев, context21 proposal namespace; H4 вложен в H8. Это иной знаменатель, чем фактически экспортированные transfer OD.',
    'E13;E14','','','COVERAGE_ARITHMETIC; HOLDS_RETAINED',
    'Непокрытые пары UNKNOWN, не ноль конкурентов. Source lineage и часы удержаны.',
    'Использовать знаменатель выбранной задачи; не суммировать nested сети.')
example('G02','COVERAGE_GAP','Фактически экспортированные пересадочные OD Уфы','UNKNOWN','7–13.12.2026','Exported transfer-OD coverage','3/24;1/8','положительные направленные OD / экспортированные transfer OD H8/H4',
    'MR08 независимо проверил incidence именно экспортированных OD; 24/8 не заменять на 56/12 всех возможных пар.',
    'E10','','','JOIN_ARITHMETIC_ONLY; OLD_SOURCE_HOLD',
    'Нет observed endpoint D, fares и seats. Покрытие не доля спроса.',
    'Довести competition matrix только для финально выбранных пар и сохранять unknown.')
table('competitor_and_svx_gaps.csv',examples)

options=[]
def option(id,topic,variants,known,unknown,rule,stop,refs):
    options.append(dict(decision_id=id,topic=topic,status='OPEN_DECISION',decision_owner='Команда; владелец модели фиксирует предпосылки',
        admissible_options=variants,known_result=known,not_known=unknown,choice_evidence_or_rule=rule,stop_or_hold_condition=stop,evidence_ids=refs))
option('D01','Радиус допуска','0;300;500;800 км, с указанием опорных координат','При balanced stage22 тройки различаются; 500 км не требование организаторов.',
    'Какой порог снижает собственный переток или улучшает экономику.','Утвердить цель политики; если цели разные, сохранить expansion и strict_new раздельно.','Нельзя назвать выбранный радиус эмпирически оптимальным без эффекта на итоговый OD/деньги.','E02;E04')
option('D02','Веса и UNKNOWN','Оригинал Анастасии; balanced stage22 Цири; stage11; дополнительные явно названные профили','author_weights.csv сохраняет 36 исходных строк, stage11 30/20/25/15/10 описан в E03.',
    'Единственно правильные веса и эмпирическая полезность всех proxy.','Обосновать смысл перехода по шкале, зависимые proxy, UNKNOWN; показать чувствительность.','Не перенастраивать веса для заранее понравившейся тройки; не считать все неизвестные нулями.','E03;E04;E30')
option('D03','Расширение опоры или новая база','Расширять Екатеринбург/другие существующие опоры; strict_new; сравнить оба universe','Статус опор опубликован; физическая база и хаб не тождественны.',
    'Текущая свободная мощность ТО/базы/экипажей и цена новой базы.','Развести capital/incremental base costs, каннибализацию, местный рынок и future supply.','Исключение города — policy, не доказательство его финансовой непригодности.','E04;E11;E23')
option('D04','Порядок расхода кресел','Local-first; transfer-first; оптимизация маржи с explicit service constraints','При 3·C в review local-first и transfer-first меняют знак H4/H8. Оба расходуют общие места.',
    'Фактическая последовательность бронирования, обязательства и спрос по fare class.','Выбрать правило до расчёта; проверить общий market/leg budget и один fare.','Нельзя переносить границы local-first на другую очередь или объявить transfer рост самоцелью.','E06;E10')
option('D05','Закон захвата общего рынка','Общий D/seat bound; предложенный Q(F); альтернативная калиброванная функция','В сохранённом исходном наборе D-only не меняет деньги; Q(F) даёт отдельную сценарную дельту.',
    'Эмпирический capture, частотный отклик и ценовая эластичность.','Проверять все competing programs одним пулом; не приравнивать Q(F) к обязательному исправлению.','Если исходный D не наблюдён, писать scenario_OD; не выдавать отдельный forecast за факт.','E06;E11;E22')
option('D06','Степень изменения сети','KEEP; retiming/product; частоты/новые линии; перенос ресурса; новая база; mixed','Это сравниваемые действия. Минимальная перестройка не установлена политикой RW.',
    'Реальная donor economy, opportunity cost, доступный парк и контракты.','При одинаковом ресурсе/периоде сравнить полный incremental effect; donor назвать явно.','Не запускать при непрошедшем resource gate или неизвестном критическом условии; оставить условный вывод.','E11;E18;E26')
option('D07','Рецепт и диапазон спроса','Авторский replay; C; N; согласованные bands; новый наблюдённый input set','C/N меняет порядок base до нулевого результата; N /104 явно сценарный proxy.',
    'Observed final OD/paid bookings на нужную неделю и перенос сезонности.','Каждый owner записывает диапазон, происхождение и критерий отказа; новые данные отдельным input set.','Не называть интервалы confidence bounds или α вероятностью; не отказываться от всех сценарных расчётов.','E10;E12')
option('D08','Полный бюджет и база','Неизбежные существующие расходы; дополнительные расходы; диапазон неизвестных F/B/O; donor и cash отдельно','Имеются относительные пороги; все c24 contributions отрицательны до дополнительных статей.',
    'Договоры, старт, постоянный ТО/crew/reserve, оборотный капитал, поддержка и exit.','Сравнить одинаковый денежный базис; неизвестные оставить NULL/формулой.','Не вычитать одну упущенную маржу дважды и не объявлять operating contribution cash profit.','E11;E12;E18;E19')
option('D09','Маршрутная единица и итоговая сеть','8–12 явно названных связей конечных городов; отдельный physical-leg/itinerary register','Восемь треугольников и четыре луча — различные объекты; кейс требует итоговую сеть.',
    'Согласованный final candidate и airport assignment MOW.','До финальной карты закрепить route register; для каждой связи дать период/частоту/метод и расписание ресурса.','Не принимать количество программ за число физически выбранных связей; не требовать 8–12 от пилота.','E02;E06;E29')
option('D10','Ограничения и прекращение','No-kover; explicit cancel; feasible recovery после нового календаря; removed restrictions with other risks','Double timebase P2 воспроизведён; перенос на сутки требует пик 8; исходные day1 расчёты отдельно.',
    'Дата окончания, вероятности, контракты компенсаций и реальный recovery ресурс.','Время по одному epoch; loss fare union; считать только избегаемые затраты.','Delay served-all HOLD до доступного ресурса; дни публикаций не downtime и не вероятность.','E11;E19;E20')
option('D11','Доля рынка и annualisation','Company total consistent denominator; domestic отдельно; endpoint journeys как отдельная метрика','Организатор задаёт company passengers / all Russian carriers за один период.',
    'Совместимый прогноз знаменателя и метод учёта в числителе, net-new компании.','Дать базовый год/сценарий рынка, сегменты vs journeys reconciliation; осторожно годовые сезоны.','Не выдавать +boardings автоматически за +unique journeys; не делить декабрьский week эффект на годовой denominator.','E01;E02;E06')
table('decision_options.csv',options)

print(f'Built {len(requirements)} requirement rows; {len(claims)} claims; {len(E)} evidence references. No model run.')
print(f'Built {len(examples)} competitor/SVX entries and {len(options)} open decisions.')
