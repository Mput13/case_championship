#!/usr/bin/env python3
"""Explicit semantic assessments for the bounded passport review; no owner writes."""
import datetime as dt
import json
import re
from pathlib import Path
import review as r

OUT=Path(__file__).resolve().parent

REQUIREMENTS={
 'R01':'Буквальная цель и шаг выбора. PARTIAL сохраняет отсутствие принятой стратегии и общего эффекта, не объявляет победителя.',
 'R02':'Шаг1 и таблица требуют ≥10→3. Независимо сверены 20/15 городов двух поздних версий и 10/8 stage11; итоговая тройка команды ещё не выбрана.',
 'R03':'Веса и их обоснование требуются; численный профиль организаторами не назначен. 36 строк сверены с criteria.json, суммы125/100 сохранены.',
 'R04':'Не менее двух конкурентов, результат и применимость. S7/Азимут дают два разных механизма; профили не выданы за законченный причинный анализ, поэтому PARTIAL корректен.',
 'R05':'Это контекст Екатеринбурга, не самостоятельное буквальное требование доказать финансовый успех. Округлённые итоги carrier-hub и неизвестные трансфер/P&L разделены.',
 'R06':'Обе гипотезы обязательны; смешанный вариант разрешён при распределении бортов. Частичные common experiments не названы полным выполнением.',
 'R07':'Пассажиры, выручка и прирост доли нужны для каждой гипотезы; denominator и собственный переток ещё не закрыты. Поездки не подменяют перевозки автоматически.',
 'R08':'Две гипотезы × базовый/осторожный. Матрица не считает наличие нескольких сценариев готовой сопоставимой таблицей2×2; ranges остаются допущениями.',
 'R09':'Кресла/LF/тариф/частота и метод оценочных данных прямо требуются. Синтетические значения разрешены, но требуют метода, а не наблюдённого статуса.',
 'R10':'Для каждой пары нужны годовые пассажиры, рейсы/неделю и источник/метод. Разные периоды и source-specific supply явно не закрывают полную таблицу выбранной сети.',
 'R11':'8–12 относится к финальному выбранному варианту. Читать совместно с R19: карта показывает прямые связи городов. 20/18 model-node pairs с MOW и UFA4 не засчитаны как final compliance.',
 'R12':'Самолёты и earliest H2_2027 — условие кейса; ни срок поставки, ни доступное количество не обещаны. Общие часы и доступные хвосты различаются.',
 'R13':'Смешанная гипотеза условно допускается, но требует явного распределения самолётов. Итоговая mixed-сеть не объявлена проверенной.',
 'R14':'Roadmap до2028 и риски флота/закрытий/конкурентов/субсидий буквальны. План допускает задержку/остановку; дата прекращения Ковра не выдумана.',
 'R15':'Задачи, инструменты ИИ, проверки и материалы требуются. Appendix описывает static receipts, собственную редактуру и upstream review раздельно.',
 'R16':'Паспорт1–2 страницы по шаблону; шаблон в этом пакете не читался и не объявлен заполненным. GAP сохраняется.',
 'R17':'Лонглист10+, веса, баллы и три лучших — буквальный артефакт. Проверенные авторские таблицы не заменяют выбор профиля для сдачи.',
 'R18':'Формат таблица или код подтверждён. Наличие воспроизводимых частичных расчётов не закрывает финальное сравнение двух гипотез.',
 'R19':'Карта8–12 прямых связей выбранного варианта, не всех пересадочных OD. GAP и отложенное построение после выбора корректны.',
 'R20':'10ноября23:59 и состав заочного комплекта подтверждены страницей. DOCUMENTED означает требование, не факт подачи; receipt ещё отсутствует.',
 'R21':'13ноября, обновлённый паспорт,5–8слайдов,≤5мин, обязательная roadmap подтверждены. Не приписаны ночной сдаче как уже готовые артефакты.',
 'A01':'Дополнительный стандарт согласованного контракта, не буквальная строка организатора. Общий directedOD, каждое место и один тариф не требуют наблюдённого OD для сценарного решения.',
 'A02':'Полный бюджет/cash/opportunity — стандарт контракта. Неизвестные расходы оставлены формулами/NULL; переменный вклад не назван полным P&L.',
 'A03':'Диапазоны и границы — стандарт контракта. Сценарные множители/α не являются вероятностями или confidence intervals.',
 'A04':'No-kover, ограничения и прекращение — стандарт контракта. В историческом срезе correctionPENDING указан верно; поздний MR10 только в addendum.',
 'A05':'Сохранение версии/holds — стандарт контракта. В оригинале корректно удержаны старые источниковые выводы и новые pending; поздние receipts не подмешаны.',
}

# Each entry is a semantic judgement, with the numerical work explicitly separated
# from upstream evidence read. Units/periods/resources are not inferred from scores.
CLAIMS={
 'C01':('назначение/происхождение; без общей численной единицы','несколько моделей','периоды не объединяются','ресурс должен согласовываться','Прочитаны E03/E06/E24/E26: городская оценка, сеть и research components различаются; все исходные авторства сохранены.','semantic source comparison'),
 'C02':('score, безразмерный','author Nastya2f; stage22','снимки20городов; порог500км','не оценка ресурсов сети','Собственные raw-minmax баллы Анастасии и weighted sums frozen utilities stage22 дали OMS/REN/KUF и OMS/REN/BAX. Рейтинг не объявлен прибылью.','independent_screening.csv; independent_weights.csv'),
 'C03':('км и нормативные веса','0/300/500/800; OPEN_DECISION','официальная страница + frozen screening','не применяется','Официальная страница не назначает500км; независимый пересчёт тройки на4порогах. Выбор политики остаётся команде.','official_receipt.json; independent_screening.csv'),
 'C04':('программы; unordered model-node pairs','author base/cautious','годовой author export; не датированная новая сеть','MOW airport assignment UNKNOWN','Собственно пересчитаны8программ и20/18пар по реальным network_routes. Термин physical в старом export не перенесён; финальное8–12 не признано.','independent_route_pairs.csv'),
 'C05':('округлённые carrier-hub пассажиры; рост трансфера×','carrier-reported, не прогноз','2025; публикация04.02.2026','неизвестен','800000 и2.5 сверены с E17, receipt/hash с registry; содержание raw заново не принято. Абсолютный трансфер и прибыль не выведены.','receipt_sample.json; competitor_checks.csv V01/V03; inherited E14'),
 'C06':('базы/хабы и тип продукта','два примера, не causal effect','обзор08.11.2026; source-specific dates','свободный парк UNKNOWN','S7/A4/A4M сохранены PRIMARY_READ из pinned обзора; базы и SSJ совпадают. Обзор не доказывает успех либо пригодность новой базыRW.','inherited profile content; own semantic comparison'),
 'C07':('односторонние опубликованные вылеты/7дней','source-specific schedule','07–13.12.2026','кресла/выполнение UNKNOWN','Собственные joins и развёртка правил: MRV↔UFA4+4 Азимут, NJC↔UFA4+4 Utair, GOJ↔UFA2+2 Nordwind. Дубликаты публикаций не сложены.','independent_card_dates.csv; independent_rule_calendars.csv'),
 'C08':('earliest поставка; число бортов UNKNOWN','case constraint','не раньше H2_2027; roadmap2028','existing/occupied/additional отдельно','Условие страницы подтверждено; оно не превращено в поставочный договор либо гарантию доступного количества.','official_receipt.json; inherited E11 resource limits'),
 'C09':('endpoint journeys; seat-segments; один through fare','проверенные ledgers, не все возможные сети','модельные периоды своих exact входов','ограничение каждого physical leg','В собственном common oracle суммируются все legs и один fare, migration отдельно. Полный авторский replay/все upstream ledgers заново не выполнялись.','independent_common_cases.csv; E06/E11/E14 read as scoped upstream'),
 'C10':('пассажиры/год; вылеты/неделю; метод','оценочные/синтетические допускаются','official sections6–7','раскрытые предпосылки','Буквальные требования сверены текущим textGET, raw hash совпал с original. Нет запрета сценарного выбора без observedOD.','official_receipt.json; requirement_checks.csv R09/R10'),
 'C11':('описание процесса, не метрика качества','статические roles/receipts и review packages','прошедшие записанные события','полный occupancy audit NOT_RUN','Четыре роли Sol/xhigh и запись Astra сверены. Реальные дефекты/проверки видны в pinned review. Self-check и независимый review не смешаны.','checks.json AI_static_roles_match; source reports read'),
 'C12':('исторический acceptance status','original frozen cut','исходный exact set subject; позднее отдельно','не означает availability','В original frontier/v5/correction действительно pending по его brief. Сейчас нужны отдельные квалификации MR10/MR11/FRONTIER; они не переписывают historical claim.','current_qualification_addendum.csv; original input_pins.json'),
 'S01':('RUB/модельную неделю; α безразмерная координата','abb1 base C→N; local-first','07–13.12.2026','fixed context21 supply; не actual fleet','Собственный allocator и bisection дали α0.6835090019901069, оба вклада−3168101.7677873. Чувствительность не вероятность и не финансовая победа.','independent_boundaries.json; independent_common_cases.csv'),
 'S02':('верхняя граница RUB/неделю','четыре программы cautious; no migration optimistic bound','07–13.12.2026','фиксированные места/рейсы/тарифы','Собственно восстановлен local-seat upper bound и невыгодность transfer относительно local по всем заданным продуктам; все4cautious bounds<0.','independent_upper_bounds.csv'),
 'S03':('RUB/неделю; множитель рецепта','base C; local-first; сохранённая migration','07–13.12.2026','тот же supply','Собственный oracle: DSVX saturation−449822.70; H4 zero2.461770880394, H8 zero2.919437005157. Это условные пороги до неизвестного бюджета.','independent_boundaries.json'),
 'S04':('дополнительные F+B RUB/неделю','base; одинаковыеO; F,B≥0','07–13.12.2026','разные дополнительные board/base расходы','Разность собственных base вкладов2703326.676013273 округляется2703326.68. Сравниваются потери, не положительная прибыль; ΔO/donor не занулены как факт.','independent_boundaries.json; E11 budget_thresholds source'),
 'S05':('блок-часы/неделю','common4×6×10; author9×7×10','разные нормативные envelopes','240 vs630; часы не calendar acceptance','Перемножение и реальный REN246.08753часа: ceil/60=5, ceil/70=4. Ни достаточность часов, ни доступный tail не заявлены.','checks.json S05_resource_envelope/resource_real_REN_counterexample'),
 'S06':('RUB/неделю относительно суммы standalone','c24 base pooled proposedQ(F)','07–13.12.2026','совместный пул; fixed allocation','Из реальных ledger components получены−12795565.31594 против−12349501.42728, delta−446063.888659. Общий исходный D отдельно не превышен. Полный portfolio allocator здесь не повторялся.','checks.json S06_ledger_delta_rounded/original_all_four_programs_D_bound; upstream E11'),
 'S07':('одновременно летящие борта; delay served/dеньги HOLD','day1→+1440; UFA8','неделя07–13.12.2026','необходимый peak8>4+1','Собственный interval sweep по32реальным legs дал peak8. Это контрпример served-all; новый реальный recovery не строился. CorrectionPENDING верно только исторически.','independent_concurrency.csv; current_qualification_addendum.csv'),
 'S08':('возвратные клиенты; journeys; occupied segments','illustrative fare8000, K1000000','не задан реальный период','вместимость не доказывается порогом','ceil(1000000/[2×7500])=67 против ceil(1000000/[2×7000])=72. Это134/144journeys и268/288segments, изменение cost unit не ошибка автора.','checks.json S08_journey_cost_clients/S08_segment_cost_clients'),
 'X01':('недопустимый итоговый вывод','запрет выбранной прибыльной сети','разрешённый срез','joint resource/budget не установлены','Запрет обоснован отсутствием совместно принятой final8–12; scopedPASS пилотов его не снимает.','E06/E10/E11; requirement gaps; no winner inferred'),
 'X02':('нормативный радиус/веса','OPEN_DECISION','frozen author variants','не применяется','Нет источника решения команды; собственная sensitivity меняет тройки и не устанавливает оптимальность.','independent_screening.csv; source decision ledger'),
 'X03':('запрет абсолютногоOD/P&L из агрегатов','carrier-reported annual growth','2025vs2024','UNKNOWN','800000 и×2.5 допускают разные абсолютные transfer bases; нет абсолютной доли/прибыли.','counterexamples.json; E14/E17 scope read'),
 'X04':('journeys≠уникальные люди≠сегменты','запрет несовместимого market-share denominator','один период требуется','не применяется','Двухплечевая поездка даёт2segment seats и один fare; повторный клиент не новый человек. Case numerator/denominator не подменены.','own common conservation; official share definition'),
 'X05':('schedule/seats/LF≠observedOD/operation','planned publications','07–13.12.2026 examples','seats unknown','Даты и правила доказывают опубликованное предложение; карточки сохраняют UNKNOWNconfiguration/fare/executed.','competitor_checks.csv; receipt_sample.json'),
 'X06':('coverage gaps; historicalsourceHOLD','original129rows/28cards/58mappings','original17b source version','не supply/demand admission','Оригинальная ошибка raw/capture остаётся CHANGES; MR10 исправляет только отдельную derivative metadata. Отсутствие карточки остаётся UNKNOWN.','independent_coverage.csv; current_qualification_addendum.csv'),
 'X07':('единица маршрута и scope','final8–12; pilot может быть меньше','official deliverable','MOW assignment UNKNOWN','Организатор требует8–12 прямых связей final; UFA4/8triangles не названы исполнением только по счётчику.','requirement_checks.csv R11/R19; independent_route_pairs.csv'),
 'X08':('поставка/свободные борта','UNKNOWN_SUPPLY','H2_2027 earliest case date','количество UNKNOWN','Запрет гарантии корректен: earliest условие не доказывает факт и доступность.','official_receipt.json; no supply assurance'),
 'X09':('portfolio result≠сумма alternatives','common market/seat/migration/resource','один период обязателен','общий reserve/base/oldinventory','Реальная Q(F) delta и pooledD проверены отдельно; самостоятельные alternatives автоматически не стали mixedstrategy.','S06 arithmetic; inherited E11 portfolio scope'),
 'X10':('delay service/cash/датаКовра','HOLD; UNKNOWN','сценарное окно, не дата окончания','peak8 против5','Собственный peak counterexample; MR10/MR11 сохраняют delayNULL. Cashfixture не выдаётся за ресурс восстановления.','independent_concurrency.csv; addendum'),
 'X11':('скорость/точность моделей NOT_MEASURED','нет сравнительного эксперимента','static process records','occupancy audit NOT_RUN','Appendix прямо отвергает доказанное ускорение/превосходство; receipts подтверждают задачи и настройки, не эффект.','own static receipt checks; appendix semantic read'),
 'X12':('variable contribution≠fullP&L/cash','UNKNOWN_NOT_ZERO','модельная неделя vs timingfixture','дополнительныеF/B/O/donor неизвестны','Собственный cashпример: конечный+400000 при peak funding1000000. Неизвестные реальные статьи не занулены, donor не списан дважды.','independent_cash.csv; current_qualification_addendum.csv MR11'),
 'X13':('приёмка версии, не возрастветки/push','exact new review only','original and addendum separately','все исходныеholds сохраняют scope','Проверено явное отделение selfcheck и review; поздние3review допускают только свой scopedрезультат. V6/V7 цифры не приняты.','current_qualification_addendum.csv; manifests'),
}

DECISIONS={
 'D01':'Радиус/expansion/strict_new остаются нормативным выбором; изменение топов не эмпирическая оптимальность.',
 'D02':'Оригинальные веса/UNKNOWN сохранены; нет решения команды или подгонки профиля.',
 'D03':'Опорный статус не превращён в физический хаб; имеющаяся свободная инфраструктура неизвестна.',
 'D04':'Local-first и transfer-first — отдельные варианты очереди; границы первого не объявлены универсальными.',
 'D05':'Собственная проверка всех исходных claims не нашла превышения общегоD. ProposedQ(F) отдельно от D-only исправления.',
 'D06':'KEEP/продукт/частоты/перенос/база/mixed сравниваются; минимальные изменения не политикаRW.',
 'D07':'C/N — recipes; annual/104 не winterOD; ranges не statistical confidence.',
 'D08':'Полный бюджет/cash/donor разделены; относительный порог не договорная стоимость.',
 'D09':'Выбранные прямые городские связи должны читаться сR19. Модельные20/18 сMOW и8программ не признаны physicalairportcount.',
 'D10':'Исторический timebaseP2 и unavailable recovery различаются; вaddendum только новая приёмка projection.',
 'D11':'Company passenger share требует того же периода и знаменателя; seasonalannualisation и endpointjourneys отдельно.',
}


def ref(sha,folder,f):return sha+':'+r.N+folder+'/'+f


def prose(s):
    """Keep free prose legible around numeric/Latin labels; never change refs/IDs."""
    s=re.sub(r'(?<=[0-9A-Za-z])(?=[А-Яа-яЁё])',' ',s)
    s=re.sub(r'(?<=[А-Яа-яЁё])(?=[0-9A-Za-z])',' ',s)
    for a,b in [('observedOD','observed OD'),('winterOD','winter OD'),('rawminmax','raw minmax'),('fullP&L','full P&L'),('fullbudget','full budget'),('flightcosts','flight costs'),('onefare','one fare'),('served-all','served-all')]:s=s.replace(a,b)
    return s


def addendum():
    out=[]
    def put(key,event,affected,old,current,hold,targets):
        sha,folder=r.PINS[event]
        out.append(dict(addendum_id=key,event=event,review_commit=sha,review_exact_ref=ref(sha,folder,'report.md'),
                        affected_claims=affected,old_qualification=old,current_scoped_qualification=current,
                        remains_HOLD_or_UNKNOWN=hold,reviewed_target=targets,
                        personal_vs_upstream='Лично прочитаны exact report/findings/handoff и сопоставлены границы; расчёты этого upstream review здесь NOT_RERUN.',
                        original_verdict_policy='Original CHANGES у17b/afadee и original временной срез passport_bridge не переписываются.'))
    put('A01','MR10','C12;X06;X13;V06;R10;A05',
        'SJR-P2-001: исходные 129 строк / 28 карточек / 58 mappings на 17b находятся на SOURCE_VERSION_LINEAGE_HOLD; correction metadata ещё не принята в исходном срезе паспорта.',
        'APPROVE_SCOPED A: у производной f177 проверены source_snapshot FK, capture/hash, 28 bindings и 58 mapping joins. SJR-P2-001 закрыт только для metadata этой производной.',
        'Исходный 17b сохраняет исторический CHANGES. Raw bodies не перепарсены; SOURCE_SUPPORTED, выполнение, кресла и OD не получили нового принятия. Шесть clock mappings остаются HOLD.',
        'f1774e1f66a9483fb618ca6003abd9dc4d8563e1:'+r.N+'primary_lineage_correction/')
    put('A02','MR10','C12;S07;X10;X13;A04;D10',
        'Correction 87ee: PARENT_TIMEBASE_AND_DELTA_CHECK_ONLY; независимая проверка PENDING.',
        'APPROVE_SCOPED B: у correction 87ee проверены временная проекция, lineage, conservation и admission gating. Окно второго дня даёт 16 UFA8 legs; no-kover и арифметика первого дня сохранены.',
        'Исходный MR02 сохраняет CHANGES. Принятые served/unserved, delta, contribution и cash ветви delay остаются NULL. Реальные fleet/crew/slots/MCT и экономика восстановления UNKNOWN.',
        '87ee52de15c2bdf396d9c06ba600fd413d5ab4a8:'+r.N+'cost_kover_timebase_correction/')
    put('A03','MR11','C12;C09;S06;X09;X13;D05',
        'Methods v5 на f7: OWNER_DERIVATION/PENDING.',
        'APPROVE_SCOPED на точный f7: C/N cancellation, corrected adapter, 90 portfolio cases и opt-in D guard. Все 30 D_GUARD равны standalone; Q(F) остаётся AGENT_PROPOSAL.',
        'Изменённые входы требуют нового key/hash/oracle admission. Adversarial duplicate N не входит в допуск exact inputs. Глобальная оптимальность и выбранная mixed strategy не установлены.',
        'f7a034dc91917cc69c5f8b3a729c3d1c6dfeb5b9:'+r.N+'methods/')
    put('A04','MR11','C12;S07;X10;X12;D10;R08',
        'Новый C/N × Ковёр interaction ещё PENDING; C-delta автоматически не переносится в N.',
        'Узко приняты 16 cancellation cases, union itinerary, один тариф и собственные D_SVX8 legs; проверены 40 adapter rows. У hub-delay сохраняется NULL gate.',
        'Delay served-all и recovery остаются HOLD. Реальная цена, договорная избегаемость расходов, dispatch и полный бюджет UNKNOWN. MR11 сам не заменяет raw/timebase scope MR10.',
        'f7a034dc91917cc69c5f8b3a729c3d1c6dfeb5b9:'+r.N+'methods/runs/')
    put('A05','MR11','C12;X12;A02;D08',
        'Интеграция cash/burden v5 PENDING; переменный вклад не является полным cash.',
        'Проверены восемь net-cash fixtures и обратные burden-пороги. UFA8/C/base fuel+pax: fixture peak 6078104.30 RUB; UFA4: 3519154.69 RUB. Это дополнительное покрытие относительно того же baseline.',
        'Это не фактический резерв RW. VAT/gross, договорные сроки и полный cash UNKNOWN/NULL. B и ΔO остаются неизвестными; компенсация не юридическая ставка.',
        'f7a034dc91917cc69c5f8b3a729c3d1c6dfeb5b9:'+r.N+'methods/')
    put('A06','FRONTIER_REVIEW','C12;X01;X07;X11;X13;R15',
        'Frontier 519998ed: OWNER_DERIVATION/PENDING.',
        'APPROVE_SCOPED: inventory 35; C01 joint clock/calendar; C07 advance/deadline; C14 distinct date/stay joins; четыре capacity/margin fixtures. Проверены три пилота; остальные 32 спецификации NOT_EVALUATED.',
        'Inherited SVX lineage HOLD этим review не снят. Raw/source, рынок, реальный ресурс, полный бюджет и запуск не приняты. Weather: NOT_RUN_NO_OPERATIONAL_LABELS; tourism: NOT_RUN_NO_ENDPOINT_OD.',
        '519998ed8c97ce5499f356a6d0f81558c7f6ee14:'+r.N+'hypothesis_frontier/')
    for key,version,tag in [('A07','V6','ba9 allocation'),('A08','V7','c6ad budget-choice')]:
        out.append(dict(addendum_id=key,event='PENDING_'+version,review_commit='',review_exact_ref='b20d4346b6aede514dbed59112bcf878232819c8:'+r.N+'briefs/passport_review.md',
                        affected_claims='X01;X09;X12;X13;R11;A05',old_qualification=tag+' pending independent',
                        current_scoped_qualification='PENDING; ничего не принято по старшинству версии или push.',
                        remains_HOLD_or_UNKNOWN='Числа, победитель и готовность бюджета/ресурса этой версии в review не включены.',
                        reviewed_target='NOT_READ; brief даёт только short tag; exact input не добавлялся.',
                        personal_vs_upstream='Сохранено явное ограничение brief; независимого verdict в этом наборе нет.',
                        original_verdict_policy='Отдельно от MR10/MR11/FRONTIER; ни один их PASS не расширен на V6/V7.'))
    r.table('current_qualification_addendum.csv',out)


def main():
    checks=json.loads((OUT/'checks.json').read_text())
    assert checks['status']=='PASS'
    requirements=r.rows(r.SUBJECT,r.P+'requirements_evidence.csv')
    claims=r.rows(r.SUBJECT,r.P+'claims.csv')
    evidence={x['evidence_id']:x for x in r.rows(r.SUBJECT,r.P+'evidence_index.csv')}
    assert set(REQUIREMENTS)=={x['requirement_id'] for x in requirements}
    assert set(CLAIMS)=={x['claim_id'] for x in claims}
    rr=[]
    for i,x in enumerate(requirements,2):
        k=x['requirement_id']
        rr.append(dict(requirement_id=k,subject_exact_ref=r.SUBJECT+':'+r.P+'requirements_evidence.csv:'+str(i),
                       kind=x['requirement_kind'],official_locator=x['organizer_locator'],
                       wording_and_transfer_verdict='APPROVE_SCOPED',analysis=prose(REQUIREMENTS[k]),
                       deliverable_status=x['status'],fulfilled_by_review=False,
                       evidence=x['existing_evidence_ids'],minimal_owner_fix='NONE'))
    r.table('requirement_checks.csv',rr)
    cc=[]
    for i,x in enumerate(claims,2):
        k=x['claim_id'];unit,scenario,period,resource,why,personal=CLAIMS[k]
        refs=[]
        for e in x['evidence_ids'].split(';'):
            q=evidence[e]
            refs.append(e+'='+(q['source_commit']+':'+q['source_path'] if q['source_commit'] else r.SUBJECT+':'+r.P+'official_requirements.json')+' ['+q['locator']+']')
        cc.append(dict(claim_id=k,group=x['group'],subject_exact_ref=r.SUBJECT+':'+r.P+'claims.csv:'+str(i),
                       evidence_exact_refs='; '.join(refs),unit=prose(unit),scenario=prose(scenario),period=prose(period),resource=prose(resource),
                       verdict='APPROVE_SCOPED',semantic_check=prose(why),personal_work=personal,
                       inherited_acceptance=x['acceptance_scope'],scope_preserved=True,minimal_owner_fix='NONE',
                       late_update='See current_qualification_addendum.csv' if k in ['C12','S07','X01','X06','X09','X10','X12','X13'] else 'No change to original cut'))
    r.table('claim_checks.csv',cc)
    decisions=r.rows(r.SUBJECT,r.P+'decision_options.csv')
    assert set(DECISIONS)=={x['decision_id'] for x in decisions}
    r.table('decision_checks.csv',[dict(decision_id=x['decision_id'],subject_exact_ref=r.SUBJECT+':'+r.P+'decision_options.csv:'+str(i),status='OPEN_DECISION',verdict='APPROVE_SCOPED',analysis=prose(DECISIONS[x['decision_id']]),decision_taken_by_reviewer=False) for i,x in enumerate(decisions,2)])
    addendum()
    # Evaluated counterexamples target unwarranted extensions, not alleged new
    # defects in the owner package. These do not assert actual market outcomes.
    aggregate=[dict(transfer_2024=40000,transfer_2025=100000),dict(transfer_2024=160000,transfer_2025=400000)]
    assert all(x['transfer_2025']/x['transfer_2024']==2.5 for x in aggregate)
    assert len({x['transfer_2025']/800000 for x in aggregate})==2
    r.save('counterexamples.json',dict(status='PASS; all examples are constructed or recomputed, not market observations',cases=[
        dict(id='CE01',affected='C05/X03',setup='Те же 800000 в hub aggregate и рост трансфера ×2.5 допускают разные абсолютные transfer bases.',examples=aggregate,conclusion='Абсолютный transfer OD, доля трансфера и P&L не определены.'),
        dict(id='CE02',affected='C02/C03/X02',setup='Один дополнительный день сообщений BAX в заданной шкале.',result='checks.json: one_publication_day_counterexample',conclusion='Разрыв BAX/KUF меняет знак. Это sensitivity, а не найденное пропущенное сообщение.'),
        dict(id='CE03',affected='S01/X01',setup='Точка равных вкладов D_SVX8/H4.',result='independent_boundaries.json: оба -3168101.77 RUB/week',conclusion='Смена порядка не устанавливает положительную прибыль или финальную сеть.'),
        dict(id='CE04',affected='S05/S07/X10',setup='Day1 +1440 по 32 датированным UFA8 legs.',result='independent_concurrency.csv: peak 8',conclusion='Четыре рабочих борта и один резервный не позволяют served-all; recovery/cash UNKNOWN.'),
        dict(id='CE05',affected='X12',setup='Реальные строки illustrative cash fixture: launch 400000 + deposit 600000 в t0, возврат deposit в t2.',result='independent_cash.csv: terminal +400000 при peak funding 1000000',conclusion='Положительный терминальный cash не исключает потребности в финансировании. Это не фактический бюджет RW.'),
        dict(id='CE06',affected='S06/D05',setup='Все standalone программы из exact контекста объединены по directed D.',result='independent_original_D_pools.csv: все sales <= D; Q(F) delta -446063.89',conclusion='Дельта Q(F) не доказывает исходного превышения D.'),
        dict(id='CE07',affected='C09/X04',setup='10 конечных двухплечевых поездок, тариф 8000.',result=dict(journeys=10,seat_segments=20,through_fares=10,revenue=80000,wrong_revenue_if_twice=160000),conclusion='Расход кресел на двух плечах не удваивает сквозную выручку или число людей.'),
        dict(id='CE08',affected='X05/X06',setup='Положительная карточка содержит опубликованные вылеты; отсутствие карточки содержит UNKNOWN.',result='17 dated card joins; complete market proof absent',conclusion='Ни выполнение, ни отсутствие конкуренции из этих статусов не следует.'),
        dict(id='CE09',affected='D07/C10',setup='Один симметричный annual proxy 10400 может распределяться неравномерно по 52 неделям.',result=dict(flat_week_direction=100,winter_week_direction=0,winter_weeks=26,other_week_direction=200,other_weeks=26,annual_both_directions=10400),conclusion='annual/104 — сценарная ровная раскладка; не наблюдённый зимний OD. Сценарные расчёты разрешены.'),
    ]))
    # Enrich every non-route record with its actual personally checked basis.
    import csv
    with (OUT/'competitor_checks.csv').open(newline='') as f:ex=list(csv.DictReader(f))
    original={x['example_id']:x for x in r.rows(r.SUBJECT,r.P+'competitor_and_svx_gaps.csv')}
    for x in ex:
        o=original[x['example_id']];x['reference_period']=o['reference_period'];x['unit']=o['unit']
        if x['example_id'] in ['P01','P02','P03']:
            x['source_commit']='77343ca9dccc14d60c51d4559485646219ecd1cd';x['source_locator']='context/13_competitors/competitors.json:sources/carriers; '+o['source_ids']
            x['personal_check']='Literal base/product/source-status comparison with exact profile; current raw NOT_READ; no causal success claim.'
        if x['example_id']=='V06':x['personal_check']='Original17b/944b historical CHANGES read; exact MR10A later acceptance kept separately; original rows untouched.'
        if x['example_id']=='G01':x['personal_check']='Independent regroup of primary coverage.csv:10/56 and2/12; unmatched UNKNOWN. See independent_coverage.csv.'
        if x['example_id']=='G02':x['personal_check']='Independent distinctbase regroup of pinned MR08 incidence:3/24 and1/8; not raw reacceptance. See independent_coverage.csv.'
    r.table('competitor_checks.csv',ex)
    r.save('findings.json',dict(review_id='passport-review-20261110-v1',subject_commit=r.SUBJECT,verdict='APPROVE_SCOPED',
             original_temporal_slice_preserved=True,findings=[],P1=0,P2=0,required_owner_fixes=[],
             acceptance='Точность ограниченного синтеза и переноса требований/тезисов; собственные расчёты перечислены отдельно.',
             later_upstream_reviews_not_rerun=True,late_updates='current_qualification_addendum.csv',
             retained_limits=['Original SJR-P2-001 CHANGES для 17b; correction metadata принята отдельно.',
                              'Original CKR-P2-TIMEBASE CHANGES для afadee; correction projection принята отдельно; recovery HOLD.',
                              'Нет выбранной сети на 8–12 маршрутов, observed OD, полного P&L/cash, доступного tail/crew/slots, гарантии поставки или запуска.',
                              'V6 ba9 allocation и V7 c6ad pending; их числа не включены.']))
    r.save('review_development_notes.json',dict(scope='Only errors in this reviewer harness, not owner findings',resolved=[
        'Official check initially searched substring500, matching unrelated numeric text; fixed to standalone500km wording. Body hash unchanged.',
        'S04 initially compared a kopeck-rounded claim to invented extra digits; fixed to rounding actual2703326.676013273 to2703326.68.',
        'Static receipt options are a list of id/value objects, not a dict; parser corrected.'],unresolved=[]))
    done=dt.datetime.now(dt.timezone.utc).isoformat()
    r.save('handoff.json',dict(package_id='passport-review-20261110-v1',reviewer='Sol 6.1 xhigh independent bounded reviewer',
             prepared_base=r.BASE,subject_commit=r.SUBJECT,branch='research/night-passport-review-20261110',scope=r.N+'passport_review/',
             verdict='APPROVE_SCOPED',completed_review_at_utc=done,content_cutoff_msk='2026-11-10T08:30:00+03:00',global_limit_msk='2026-11-10T10:00:00+03:00',
             counts=dict(requirements=26,claims=33,competitor_examples=28,decisions=11,checks=len(checks['checks'])),
             entrypoint='report.md',findings='findings.json',late_qualification='current_qualification_addendum.csv',
             own_work=['Exact blob/hash/source FK checks','Official text wording','Raw minmax Nastya; frozen utility sums stage22; stage11 weighted components','Common allocator, bisection and bounds','Dated card joins and rule expansion','Resource concurrency','Cash fixture arithmetic','Semantic review of every row'],
             trusted_upstream=['Source-specific raw/source acceptance from original scoped reviews','MR10','MR11','FRONTIER_REVIEW'],
             NOT_RUN=['Full financial author replay','Rerun MR10/MR11/FRONTIER','New raw competitor re-audit','Live browser/UI','Sales/operation/dispatch','Final strategy/launch','V6/V7 acceptance'],
             delivery='One safe package; exact remote SHA verified after push and returned in final response. No embedded circular self-SHA.',
             safety=dict(owners_changed=False,public_site_report_dashboard_changed=False,children_threads_schedules_messages=False,paid_sources=False,infrastructure_changes=False,force_merge_rebase_PR=False),
             next='This reviewer stops after this package; no new cycle.'))
    # Merge only reads actually performed here into the independently tracked manifest.
    manifest=json.loads((OUT/'source_manifest.json').read_text());by={x['exact_ref']:x for x in manifest['sources']}
    by.update(r.SOURCES);manifest['sources']=list(by.values());r.save('source_manifest.json',manifest)
    print(json.dumps(dict(requirements=len(rr),claims=len(cc),competitors=len(ex),decisions=len(decisions),verdict='APPROVE_SCOPED')))


if __name__=='__main__':main()
