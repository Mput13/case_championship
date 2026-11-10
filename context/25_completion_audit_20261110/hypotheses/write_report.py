"""Write findings and review handoff from the frozen sources and completed checks."""
from collections import Counter
import csv
import json
import re
import subprocess

from source_access import OUT, REPO, PINS, H, F, R, M, source, rows, evidence, at, dump, seal_sources


def e(label,path,needle):
    return at(label,path,needle)


def link(ev,label=None):
    return f"[{label or (ev['path']+':'+str(ev['line']))}](https://github.com/Mput13/case_championship/blob/{ev['commit']}/{ev['path']}#L{ev['line']})"


def main():
    disposition=list(csv.DictReader((OUT/'disposition.csv').open()))
    checks=json.loads((OUT/'checks.json').read_text())
    findings=[
        dict(id='HYP-AUDIT-001',severity='P1',kind='OUTCOME_COMPLETION_GAP',status='OPEN_OUTCOME; scoped task work delivered',
             title='Три законченных опыта не закрывают решение по35 гипотезам или финальную сеть',
             observation='Сначала9 механизмов из35; phase2 назначил3, frontier продолжил те же3. Остальные32 не получили адресного расчёта в проверенных пакетах. Это не доказательство провала исполнителей относительно их узких briefs; итоговый выбор сети остаётся незавершённым.',
             evidence=[e('base','context/16_agent_research/briefs/hypotheses.md','Предложить широкий'),e('base','context/16_agent_research/phase2_brief.md','Три основных'),e('base','context/23_night_run_20261110/briefs/hypothesis_frontier.md','Выбери до3'),e('review',R+'report.md','остальные 32'),e('hypotheses',H+'experiment_v1/handoff.json','Full case8-12')],
             consequence='Нельзя объявить общий поиск завершённым либо принять три пилота за совместную сеть8–12. C04 в Q02 был comparator, самостоятельного OMS-base результата нет.',
             minimal_fix='В итоговом handoff явно оставить3 частично исследованных/32 неоценённых в нашем scope, перечислить6 отложенных E-first-wave, назначить конечные следующие проверки. Слово complete применять к named task/package, не к outcome. Не запускать продолжение этим аудитом.'),
        dict(id='HYP-AUDIT-002',severity='P2',kind='HISTORICAL_ECONOMICS_OMISSION',status='CORRECTED_IN_THIS_AUDIT; legacy files unchanged',
             title='Фраза об отсутствии всякой экономической оценки стирает сохранённые денежные пороги и cost recipes',
             observation='В6ed есть108 строк grid,3 K recipes,matched resource deltas,9 опубликованных тарифных строк и2 условных суммы коэффициентов. Утверждение родителя известно из текущего поручения; дословный его источник в проверенных repo-файлах не установлен, поэтому ошибку не приписываем конкретной строке UI/документа.',
             evidence=[e('hypotheses',H+'experiment_v1/README.md','Денежная таблица'),e('hypotheses',H+'experiment_v1/README.md','Публичные строки'),e('hypotheses',H+'experiment_v1/README.md','residual_gap'),e('hypotheses',H+'experiment_v1/README.md','Денежные108'),e('base','context/16_agent_research/coordinator/20261109T154615Z/hypotheses/cost_resource/6cf441ef38e2c6c5/manifest.json','conditional_thresholds_with_product_keys')],
             consequence='Пропадает уже полученный inverse/price/resource результат. Противоположное утверждение о полной проверенной прибыли тоже неверно:actual gap/fare/seats/market и18 frontier money terms UNKNOWN.',
             minimal_fix='Писать:есть частичная условная экономика и проверенные пороги; реальный денежный результат и полный P&L/cash не установлены. Сохранить grid/K/tariff ссылки и область единиц.'),
        dict(id='HYP-AUDIT-003',severity='P2',kind='NO_DOCUMENTED_EARLY_REJECTION',status='DOCUMENTED; no retrospective reasons added',
             title='Причины последующей отсрочки нельзя выдавать за ранний экономический отсев',
             observation='Все35 original evaluation_status=NOT_EVALUATED; early run log не содержит rejected_candidates. Для26 вне девятки дана общая scope-формулировка, для9 — механизм выбора. Stop_rule описывает будущий критерий, не наступивший результат. Поздние BLOCKED_* frontier — новые gates, не историческая причина отказа.',
             evidence=[e('hypotheses',H+'findings.md','Остальные 26'),e('hypotheses',H+'evaluation_runs.jsonl','"rejected_candidates": []'),e('hypotheses',H+'candidates.csv','C03,'),e('frontier',F+'experiment_queue.csv','Q06,')],
             consequence='Иначе отсутствие рынка/договора превращается в необоснованный отрицательный вывод. У6 ранее выбранных E02/E04/E06/E07/E08/E09 нет реализованного адресного опыта.',
             minimal_fix='В каждой карточке разделить original status, original selection reason, later unresolved parameter и bounded failed case. Для35 documented_early_rejection=ABSENT;scope/UNKNOWN не отказ.'),
        dict(id='HYP-AUDIT-004',severity='P2',kind='ANALOGUE_AND_NAMESPACE_BOUNDARY',status='CHECKED; no cross-system Cxx join used',
             title='Прежние деньги отрицательных сетей и положительных route-сценариев не равны результатам наших35 продуктов',
             observation='Context21 имеет8 отрицательных network contributions,42 route thresholds и другой upstream universe. Source-linked scale tests содержат20 положительных сценариев до extra fixed. EC_H01–11 — семейства PROPOSED_NOT_ACCEPTED. Наследование/одинаковый город или Cxx другого автора не переносит деньги в конкретную новую карточку.',
             evidence=[e('hypotheses',H+'existing_hypotheses.csv','EC_H01,'),e('base','context/21_visual_explainer_draft_20261110/inputs/economics.csv','D_SVX8,base'),e('base','context/21_visual_explainer_draft_20261110/inputs/breakeven.csv','SVX-MRV,base,1,0'),e('economics21','context/18_unit_economics_audit/source_linked_scale_tests.csv','SVX-MRV,base,0.5,1.0'),e('methods',M+'handoff_compact.md','fixed-product') if 'fixed-product' in source('methods',M+'handoff_compact.md') else e('methods',M+'handoff_compact.md','cautious')],
             consequence='Нельзя отвергать C01 по UFA8, C07 по отрицательному additional SVX–OMS, C14 по SVX–MRV или C31 по generic pilot. Нельзя и объявлять их прибыльными по20 положительным scale rows.',
             minimal_fix='Связывать namespace+source_commit+full product/legs+period+baseline+money definition. Аналоги показывать отдельно с несоответствием. Оставить положительные и отрицательные исходные строки.'),
        dict(id='HYP-AUDIT-005',severity='P2',kind='UNKNOWN_IS_NOT_ECONOMICS_STOP_RULE',status='SCENARIO_RECIPES_PROVIDED_FOR_ALL35; new runs not started',
             title='UNKNOWN ограничивает утверждение о реальности, но не запрещает обоснованную сценарную экономику',
             observation='Contracts прямо допускают диапазоны/пороги с происхождением. Для всех35 можно сформулировать named baseline, capacity/money conservation и условия дополнительных затрат; степень численной опоры различается. Для3 уже есть численные inverse grids; у остальных нет собственного денежного run.',
             evidence=[e('base','context/23_night_run_20261110/contract.md','Диапазоны закрытых параметров'),e('base','context/23_night_run_20261110/contract.md','Если статьи неизвестны'),e('base','context/16_agent_research/phase2_brief.md','Итог может быть интервалом'),e('hypotheses',H+'experiment_v1/contract.json','fare_origin'),e('frontier',F+'test_contract.json','K(q)')],
             consequence='Ожидание всех закрытых данных оставляет полезные пороги без расчёта; одновременно round numbers нельзя назвать рыночно обоснованным доверительным интервалом.',
             minimal_fix='Применить индивидуальные scenario_economics_possible_now из disposition.csv:обозначить source-linked, public coefficient, author stress и UNKNOWN; при нехватке диапазона вывести break-even surface. Полный cash и actual resource не повышать автоматически.')
    ]
    dump('findings.json',dict(audit='NEW_FINITE_COMPLETION_AUDIT_20261110',verdict='CHANGES_TO_OUTCOME_COMPLETION_CLAIM',
                             arithmetic_verdict='NO_DIFFERENCES_IN_PERSONALLY_RECOMPUTED_ROWS',
                             note='P1/P2 label materiality of completion/interpretation gaps, not newly discovered owner code defects. Historical scoped approvals are preserved.',
                             findings=findings))

    refs={
        'initial':e('base','context/16_agent_research/briefs/hypotheses.md','Предложить широкий'),
        'phase2':e('base','context/16_agent_research/phase2_brief.md','Три основных'),
        'night':e('base','context/23_night_run_20261110/briefs/hypothesis_frontier.md','Выбери до3'),
        'money':e('hypotheses',H+'experiment_v1/README.md','Денежная таблица'),
        'cost':e('hypotheses',H+'experiment_v1/README.md','residual_gap'),
        'review':e('review',R+'report.md','остальные 32'),
        'full':e('methods',M+'handoff_compact.md','FullPnL'),
        'positive':e('economics21','context/18_unit_economics_audit/source_linked_scale_tests.csv','SVX-MRV,base,0.5,1.0'),
    }
    report=f'''# Аудит завершённости35 гипотез

10 ноября2026. Новый конечный аудит на base `{PINS['base']}`. Проверенные pins: hypotheses `{PINS['hypotheses']}`, frontier `{PINS['frontier']}`, review `{PINS['review']}`, methods frozen `{PINS['methods']}`. Это самостоятельный пакет проверки сохранённых результатов. Новые опыты, сбор источников, дети и продолжение ночного цикла не запускались.

**Вывод: закрыто выполнение ограниченных исследовательских заданий; конечное решение по35 гипотезам не закрыто.** Найдено0 документированных ранних отказов от целой карточки. Все35 получили спецификации и геометрию;9 выбраны для углубления, адресные опыты выполнены для3: C01/C07/C14. Остальные32 в проверенных пакетах не испытаны адресно. Для трёх есть частичная условная экономика, а реальная прибыль, доступный ресурс и полный P&L/cash остаются неизвестными. Доказательство невозможности отдельных временных/ёмкостных условий сохранено и не расширено до отказа от гипотезы.

Полная построчная ведомость — [disposition.csv](disposition.csv):ровно35 уникальных C01–C35, original status/selection reason, geometry/calendar/demand/money/fleet, старые денежные результаты или аналоги, вывод, следующая проверка и допустимая сценарная экономика с источниками. Каждая evidence-ссылка содержит полный commit/path/line и локальную копию. Все записи относятся к namespace `hypotheses35`; одноимённые Cxx иных систем не соединялись.

## Что было сделано и что не было отвергнуто

В двух исторических coordinator snapshots13:18/14:22 UTC содержимое `candidates.csv` побайтово совпало с hypotheses pin. Во всех35 строках ранний статус `NOT_EVALUATED`, спрос/нетто-тариф/ресурс `UNKNOWN`. Ранние `evaluation_runs.jsonl` перечисляют35 участников, `economics/demand_fit=NOT_RUN`, `rejected_candidates=[]`. У26 карточек вне первой девятки дословная причина:«Сохранён в широком поиске; отсутствие в первой очереди не означает опровержения или низкого спроса». У9 выбранных указана ценность разных механизмов, а не ранг прибыли. `stop_rule` — будущий критерий проверки, он не является зафиксированным наступившим отказом.

Лично пересчитаны144 chord-leg строки из координат50 аэропортов,81 path и324 screen строки. Максимальная погрешность округления менее0,0005км. Ни2300км, ни500км не стали основанием автоматического экономического отказа. Хорда не dispatch/track/block/payload. У C21 сохранены214 буквальных arrival rules KHV:это опубликованное предложение, не demand, free fleet или complete return calendar. Исторические RW observations C11/C22 и сторонние корпоративные примеры прочитаны как контекст сохранённого источника, без новой внешней проверки.

Последующие frontier `BLOCKED_*` обозначают неизвестные/условия следующей проверки. Они не восстанавливают историческую причину раннего отсева. В ведомости все35 имеют `documented_early_rejection=ABSENT`. Основной disposition:3 `DEFERRED_UNKNOWN_WITH_PARTIAL_TESTS`,32 `NOT_EVALUATED_OUR_SCOPE`. Это не классификация32 идей как бесперспективных.

| Состояние | Число | Что именно установлено |
|---|---:|---|
|Доказанный отказ от целой карточки|0|Такого завершённого доказательства в проверенных материалах нет|
|Условный отказ фиксированному случаю|Есть внутри3 тестов|Например MCT90 C01, недостаточный advance C07, capacity fixture с K500тыс.; это не отказ всей идее|
|Отложено из-за неизвестного после частичных тестов|3|C01/C07/C14:actual sales/cost/resource/product gates не закрыты|
|Адресно не оценено из-за нашего scope|32|26 вне девятки и6 выбранных, не вошедших в трёхтестовый проход|

## Частичная экономика трёх опытов

Утверждение «никакой экономической оценки трёх нет» слишком сильное. Его точная формулировка дана в нынешнем поручении; дословная repo-строка родителя не установлена. В6ed уже сохранены численные inverse-сценарии, состав затрат, ресурсы и коэффициенты. Корректная формулировка: **есть проверенные условные пороги и cost recipes, нет установленного реального денежного результата и полного бюджета**. {link(refs['money'])}, {link(refs['cost'])}.

1. `conditional_thresholds_with_product_keys.csv` содержит108 уникальных candidate×gap×fare×variable_cost комбинаций, по36 на C01/C07/C14. Это3×3×4×3, а не108 полевых опытов. Разные run-версии и keyed projection повторяют тот же grid. Лично повторены целочисленная инверсия, одна through fare, endpoint journeys, boardings, margin at threshold и отрицательная предыдущая ступень. Расхождений нет. Результаты со source lines — [money_recalculation.csv](money_recalculation.csv).
2. Пример K=1млн, F=8000 за one-way journey и v=500 даёт `q=ceil(1000000/(2×7500))=67` на направление. Это134 one-way journeys,1,072млн билетной выручки и5000 условного превышения маржи над K. У C01 —268 boardings; у локальных OMS–KJA C07 и KVX–MRV C14 —134. Реальные K/F/q/остаточные места неизвестны. У C14 в K остаются все4 предложенных RW legs, хотя threshold относится к local KVX–MRV продукту.
3. В `residual_gap_accounting.csv` отдельно раскрыты3 baseline. Для C01 одинаковые flight costs сокращаются только при действительно одинаковых затратах/контрактах, остаются retiming/base/overnight/local loss. C07 несёт все новые OMS–KJA legs/ground events и изменение обеих базовых продаж. C14 несёт полную SVX–KVX–MRV–KVX–SVX программу минус явно названные другие вклады. Нельзя второй раз вычитать ту же потерянную выручку как потерянную маржу.
4. В9 публичных строках есть реальные опубликованные тарифные числа. Лично проверены суммы OMS911+947=1858 и UFA553+499=1052руб./т MTOW при однократном выставлении каждого сбора. Это коэффициенты, не оплаченный бюджет и не нижняя граница:MTOW/modification, billing multiplicity, contract/discount/VAT и полный набор услуг неизвестны. UFA685руб./час стоянки — опубликованная строка для группыSSJ, а применимость к нужным минутам/договору надо задавать отдельно. Coordinator15:46 сохранил manifest этого cost_resource, не все его CSV; полные строки восстановлены именно из дерева6ed.
5. Frontier добавил4 mechanical fixtures. При100 номинальных местах и80 прежних остаётся20; F−v=7500 даёт максимум300тыс. новой парной маржи. K300тыс. требует20 на направление и помещается; K500тыс. требует34 и перегружает каждое использованное плечо на14. Положительные10000руб. арифметического остатка приq34 не снимают capacity failure. Все18 actual monetary difference terms frontier остались NULL.

Это уже полезная денежная работа. Она не является calibrated demand, received fare, actual availability, profitable network или financial acceptance.

## Границы C01/C07/C14

**C01, Уфа.** Проверялся NJC–UFA–MRV, не все три пути карточки. В фиксированном same-leg примере север прибывает09:00UTC/уходит17:00, южный reference вылетает08:00 и возвращается13:45. Для неотрицательных сдвигов x/y условие существования стыковки `2M+T≤180`. Лично перебраны совместные clock inequalities для9 M/T профилей и54 return limits, независимо от owner/reviewer кода. M45/60 допускает решения; M90 с T30/45/60 — нет в заданном окне. Шесть feasible профилей дают5/6 сочетаний выезда7/11декабря и7/10/14ночей; у10ночей после7декабря нет нужного17декабря в frozen Mon/Fri set. Это не observed demand. При M60/T45 x=y120 даёт60/75мин стыковок и45turn; следующий ресурс/реальная no-new-base ротация/цена local sales неизвестны. Время не доказывает выгоду новой базы.

**C07, Екатеринбург–Омск–Красноярск.** Лично восстановлены18 turn/slack границ и54 advance gates. Против reference205block/255elapsed цепочка имеет475block и565/610/655elapsed при T30/45/60. Добавка270block и310/355/400elapsed. `advance=max(0,220+3T−L)`, L уже net of next turn, не crew-duty limit. При T45/L180 нужно175мин опережения;174 недостаточно. С прежним стартом и L0 прежний возврат невозможен. Это условный временной отказ; loop/ранний старт не доказывает available aircraft. OMS–KJA часы — proxy другой компании, donor/next assignment/crew/MRO и изменённые собственные продажи неизвестны. C04 Омск был сравнительным вопросом в очереди, отдельной экономики новой базы не получил.

**C14, Киров–Минводы.** Старые21UNKNOWN input001 не удалены. На12 published dated flights input002 лично заново соединены24 запроса =2 выезда×2 свойства×2 booked-date bases×3 срока и96 tolerance-policy строк. Exact return есть у12/24 property rows. При0/1/2/3 дополнительных ночах получается6/7/9/11 distinct date/stay совпадений из12, property copies не пассажиры. Для checkout25декабря capture returns заканчивается24декабря:UNKNOWN, не no service. Ночное заселение, timezone/minimum/room inventory, полный dated transfer, customer willingness, airline seats/fare/rights и operating/nonstop неизвестны. Дата совпала — ещё не bookable package. PERSON_BED_DAY/PERSON_DAY нельзя умножать на nights без правил billing. A4 calendar не даёт RW выручку/кресла.

Сохранённое независимое review58a02028 имеет APPROVE_SCOPED для calendar/arithmetic/conservation, не market/full-money/operating acceptance. Новый аудит не расширяет его scope. {link(refs['review'])}.

## Прежние деньги и пределы переноса

В context21 visual inputs найдены не пустые подписи, а8 денежных строк и42 порога. Их bytes совпали с upstream93fa5cf `context/21_team_proposals/comparison.csv` и `context/18_unit_economics_audit/breakeven.csv`; проверена provenance в `inputs_manifest.json`. Для8 сетевых строк лично пересчитаны `gross−foregone−flight−new_pax+saved_pax`. Для42 порогов использован отдельный route_ledger flight cost и margin, повторены threshold/at100/capacity; полный author model/solver не запускался. [historical_economics.csv](historical_economics.csv), [breakeven_recalculation.csv](breakeven_recalculation.csv).

| Context21 сеть | Base,млн RUB/неделю | Cautious,млн RUB/неделю |
|---|---:|---:|
|D_SVX8|−7,326331|−17,737274|
|D_previous_best8|−5,023171|−14,417665|
|H_UFA_4|−4,623004|−15,163157|
|H_UFA_8|−9,496920|−28,166230|

Это вклад до base/fleet/opportunity, условные additional flights, не доказанная замена действующего донора. Эти сети не равны C01/C07/C14. В historical stage16 pin сохранено30 aggregate rows, включая NO_LAUNCH и пустую D_improved снулевыми legs; их нули не прибыль авиакомпании. Агрегатная арифметика30 строк также повторена. EC_H01–11 в ancestor registry имеют PROPOSED_NOT_ACCEPTED и UNKNOWN value, это семейства гипотез, не11 результатов отказа.

У исторического SVX–MRV пилота bf564c7 лично повторены4 инверсии:base85 оплаченных на сторону до fixed,94 при10% запасе к flight cost,124 при симметричном распределении1млн/неделю; cautious180 до fixed. Эти числа не подставляются в новый продукт или фактический type swap C31. Поздний context21 SVX–MRV base threshold уже83,429675≈84 до extra fixed при иной cost/margin версии; при100местах вклад+425857,35руб./неделю до дополнительной нагрузки, при+500тыс. —−74142,65. Версии не следует смешивать.

В `source_linked_scale_tests.csv` есть48 сценариев SVX–MRV/SVX–AER, из них20 положительных до extra fixed:8 MRV и12 AER, все base. Лично проверена их contribution arithmetic. Например SVX–MRV при endpoint_fraction0,5 и winter_ratio1 даёт условные100 проданных/направление и+425857,35; AER при0,25/0,5 также достигает nominal100 и+200945,85. Это сценарии с долей endpoint и сезонностью, не наблюдённый OD/paid sales, не actual100 payload и не полный бюджет. Положительные строки сохранены в [positive_historical_scenarios.csv](positive_historical_scenarios.csv), а не стёрты общим «всё отрицательно». {link(refs['positive'])}.

Frozen methods дополнительно имеет8 supply upper-bound строк. Лично повторена арифметика full_local_revenue−pax−flight, но не доказательство оптимизационного сертификата. Все4 cautious upper bounds отрицательны в фиксированном enumerated-product universe даже при relaxed demand/no migration. Это условный отказ именно этому supply/fare/cost universe; он не запрещает иную цену, cost recipe, новый продукт, иной ресурс или сеть. FullPnL/peakCash frozen methods остаются NULL. {link(refs['full'])}.

## Что можно считать приUNKNOWN

Недостаток actual OD/fare/resource запрещает называть сценарий фактом. Он не требует вообще остановить расчёт. Для каждой строки ведомости дана отдельная допустимая постановка:что фиксируем, какой K/премию/гарантию/долю/ресурс варьируем и какой порог получаем. Новых численных money experiments этим аудитом не выполнено.

Общая инкрементальная форма: `ΔC=Σq_j(F_j−v_j)−K(q)`. q ограничен одним общим endpoint pool и каждым physical-leg residual seat; fare начисляется один раз. K включает только согласованные добавочные рейсы/ground/base/fleet/switch/opportunity/local-loss статьи без повторного списания. Unknown terms сохраняются. Если обоснованы интервалы F/v/K, при фиксированном допустимом q можно вывести `ΔC_min/ΔC_max`; при зависимом K(q), displacement или изменении capacity нужен полный joint расчёт, не формула с постоянным K. Полный cash требует датированных receipts/payments/депозитов/финансирования отдельно от P&L.

Уже имеющаяся численная опора неодинакова. Публичные airport rate coefficients привязаны к конкретным услугам/датам; это допустимые условные элементы cost recipe. Source-linked annual segment scale требует явно неизвестных endpoint fraction/seasonality/capture. Старые F6–12тыс./v0–1000/K0–1млн — происхождение author inversion stress, не эмпирические границы рынка. Сценарный nominal100 или residual20 — mechanical ceiling, не эксплуатационный факт. При отсутствии ценового диапазона полезен ответ«какая гарантированная оплата/маржа покрывает программу», а не выдуманный точечный тариф.

В частности:C03/C04/C06/new bases — границы B/F против действующей базы; C10/C12/C18/C20/C32 — guaranteed block/payment и асимметрия; C27/C28 — bus contract/protection против residual air seats; C31 — обе программы до/после type swap; C33 — новые и потерянные связи при тех же рейсах; C34 — avoided damage против своевременной доставки резерва без вероятности из постов; C30 — две ветви после наблюдаемого триггера без даты/вероятности. Это конкретные расчётные вопросы, а не причины не оценивать идеи.

## Кто ограничил исследования тремя тестами

Исходный coordinator brief требовал широкий первичный набор и6–10 различающихся кандидатов для углубления. Девятка выполнила именно этот отбор; ранний brief не обещал полную экономику всех35. {link(refs['initial'])}.

В сохранённом `phase2_brief.md:9,21` координатор назначил C14/C01/C07 как3 основных опыта и предписал Astra начать experiment_v1 для них. Документ описывает просьбу пользователя о ещё2часах; исходная реплика пользователя с выбором именно3 в проверенных артефактах не предъявлена. Следовательно, подтверждён владелец ограничения на уровне постановки — coordinator brief, а персональную волю пользователя о численном лимите не восстанавливаем. Git-коммит этого файла:f6366f888803c076dab6b47d497751ffe5a61566, author metadata Mput13,09.11.2026 17:14:07+03; Git-author не доказывает, кто сформулировал решение. {link(refs['phase2'])}.

Ночной coordinator brief прямо потребовал«выбери до3» по снижению неопределённости/охвату/входам. Конкретный исполнитель frontier выбрал те же C01/C07/C14 и зафиксировал причины Q01–Q03;32 идеи сохранил как deferred. Это имело договорное основание для ограниченного task, но не заменило outcome по широкому поиску. Source of limit — brief, source of actual choice — executor queue/test_contract. Brief в base связан с f1774e1f66a9483fb618ca6003abd9dc4d8563e1. {link(refs['night'])}.

Шесть исходно выбранных, но не выполненных E-first-wave:C02/E02, C10/E04, C17/E06, C21/E07, C27/E08, C31/E09. Их приоритет был объяснён, отмена по отрицательному результату не документирована. Эти шесть вместе с26 вне первой девятки дают32 адресно неиспытанных.

Task-completion:35specs+9queue;3 ограниченных experiment_v1;35-classification+3 frontier tests;scoped review. Outcome-completion:обоснованный hub/direct/mixed выбор, единый ресурс/спрос/полный бюджет, готовая8–12-route программа, топ3/≥10городов и≥2конкурента в согласованной постановке, годовые passengers/revenue/share иroadmap2028 — этим рядом пакетов не установлен. Сообщать первое как второе нельзя. Исторические корректные scoped approvals не отозваны; арифметических расхождений в лично пересчитанных строках нет.

## Личная проверка и передача

Все источники получены `git show exactSHA:path`; новые внешние страницы/тарифы/расписания не проверялись. Лично сверены35unique/original status/отбор/ancestor keys, совпадение двух ранних snapshots,144geometry legs/81paths/324screens,108money cells и сохранённые их версии,9rates/2sums,4capacity fixtures,18NULL money terms, границы и календарные joins описанных3 тестов,8+30aggregate money rows,42break-even,4старых pilot inverses,48source-linked scenario money rows,8capacity-bound arithmetic rows. Счёт проверок в `checks.json` — технический receipt, не оценка качества/доказанности рынка.

Не выполнялись owner/reviewer code replay, полный solver/LP-certificate proof, live source audit, измерение demand/paid revenue, operational/dispatch/fleet acceptance, новый budget/cash run или полный новый эксперимент по32 карточкам. Сохранённые source observations/independent review отмечены как supplied evidence; их прежние PASS не добавлены к моим личным checks. Пакет не меняет исходные модели/UI/документы.

Замечания и минимальные действия — [findings.json](findings.json). Команда воспроизведения: `PYTHONDONTWRITEBYTECODE=1 python3 context/25_completion_audit_20261110/hypotheses/build_audit.py`, затем `write_report.py` и `verify_package.py` в той же папке. [source_manifest.json](source_manifest.json) фиксирует exact blobs;[handoff.json](handoff.json) — границы передачи. Новая работа не запускается автоматически.
'''
    # One concise line per ID complements the machine-readable disposition.
    table='\n## Все35 карточек\n\n| ID | Карточка | Адресная работа сверх геометрии | Решение этого аудита |\n|---|---|---|---|\n'
    for r in disposition:
        cid=r['candidate_id']
        done={'C01':'Same-leg clock/calendar;36 money inverses;K/resource/fixtures',
              'C07':'Four-leg time/advance;36 money inverses;K/resource/fixtures',
              'C14':'Published calendar/stay/flex joins;36 money inverses;full-chain K',
              'C11':'Исторические RW observations;dated improvement NOT_RUN',
              'C21':'214 inbound rules;product/economics NOT_RUN',
              'C22':'Историческая RW BAX–HTA observation;новый цикл NOT_RUN'}.get(cid,'Спецификация/причина выбора;адресный run NOT_RUN')
        state='Частично проверено;actual gates UNKNOWN' if cid in ['C01','C07','C14'] else 'Не оценено в нашем scope;не отказ'
        table+=f"|{cid}|{r['title']}|{done}|{state}|\n"
    report_text=report+table
    # Keep Russian prose readable; preserve hashes, identifiers, paths and inline code.
    chunks=re.split(r'(`[^`]*`|\]\([^)]*\))',report_text)
    for i in range(0,len(chunks),2):
        chunks[i]=re.sub(r'(?<=[А-Яа-яЁё])(?=\d)|(?<=\d)(?=[А-Яа-яЁё])',' ',chunks[i])
        chunks[i]=re.sub(r'([:;,])(?=[А-Яа-яЁё])',r'\1 ',chunks[i])
        chunks[i]=re.sub(r';(?=\S)', '; ', chunks[i])
        chunks[i]=re.sub(r'(?<=[А-Яа-яЁёA-Za-z])[,](?=\d)', ', ', chunks[i])
        for before,after in {
            'snapshots13:18':'snapshots 13:18', 'причина:«':'причина: «',
            'disposition:3':'disposition: 3', 'KHV:actual':'KHV: actual',
            'C14:actual':'C14: actual', '—268':'— 268', '—134':'— 134',
            'граница:MTOW':'граница: MTOW', 'группыSSJ':'группы SSJ',
            'Coordinator15:46':'Coordinator 15:46', 'приq34':'при q=34',
            '09:00UTC':'09:00 UTC', '45turn':'45 мин разворота',
            'reference205block/255elapsed':'reference 205 мин полёта / 255 мин занятости',
            '475block':'475 мин полёта', '565/610/655elapsed':'565/610/655 мин занятости',
            '270block':'270 мин полёта', '310/355/400elapsed':'310/355/400 мин занятости',
            '21UNKNOWN':'21 UNKNOWN', 'checkout25':'checkout 25', ':UNKNOWN':': UNKNOWN',
            'review58a02028':'review 58a02028', 'upstream93fa5cf':'upstream 93fa5cf',
            'снулевыми':'с нулевыми', 'инверсии:base85':'инверсии: base 85',
            'cautious180':'cautious 180', 'fixed:8':'fixed: 8',
            'endpoint_fraction0,5':'endpoint_fraction=0,5', 'winter_ratio1':'winter_ratio=1',
            'nominal100':'nominal 100', 'actual100':'actual 100', 'residual20':'residual 20',
            'приUNKNOWN':'при UNKNOWN', 'ответ«':'ответ «', 'В частности:C03':'В частности: C03',
            'Для 8 сетевых строк лично пересчитаны':'Для 8 сетевых строк лично пересчитана формула',
            'найдены не пустые подписи, а 8 денежных строк':'сохранены 8 денежных строк',
            'inverse-сценарии':'пороговые сценарии', 'cost recipes':'рецепты расчёта затрат',
            '108 полевых опытов':'108 проверок рынка',
        }.items():
            chunks[i]=chunks[i].replace(before,after)
    (OUT/'report.md').write_text(''.join(chunks),encoding='utf-8')
    dump('handoff.json',dict(status='ONE_FINITE_AUDIT_PACKAGE_COMPLETE',base_parent=PINS['base'],pins=PINS,
                             intended_branch='audit/completion-hypotheses-20261110',
                             outputs=['report.md','disposition.csv','findings.json','manifest.json','source_manifest.json','checks.json',
                                      'money_recalculation.csv','breakeven_recalculation.csv','historical_economics.csv','positive_historical_scenarios.csv'],
                             counts=checks['summary'],verdict='CHANGES_TO_OUTCOME_COMPLETION_CLAIM; no arithmetic differences in personally checked rows',
                             historical_reviews='Preserved, not expanded/reissued',
                             writes_only='context/25_completion_audit_20261110/hypotheses/',
                             runtime_changes='NONE',owner_code_executed=False,external_sources_refreshed=False,new_experiments_started=False,
                             children_threads_polling='NONE',continuation='NOT_STARTED; this is one finite package',
                             publication='Commit and push isolated branch only; no force/merge/rebase/PR; exact final SHA reported after commit, outside self-referential manifest'))
    # Git metadata is attribution evidence only, not proof of personal authorship/intent.
    logs={}
    for path in ['context/16_agent_research/phase2_brief.md','context/23_night_run_20261110/briefs/hypothesis_frontier.md']:
        logs[path]=subprocess.check_output(['git','log','-1','--format=%H%n%an%n%ad%n%s','--date=iso-strict',PINS['base'],'--',path],cwd=REPO,text=True).splitlines()
    dump('brief_git_metadata.json',logs)
    seal_sources()


if __name__=='__main__':
    main()
