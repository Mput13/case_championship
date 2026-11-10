#!/usr/bin/env python3
"""Build the scoped narrative and audit registers from replay results; no network or owner writes."""
import csv
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PIN = "d4a6eabb42671e5b16d44abedcdc6ceafb692528"
PRIOR = "ea926f4d422d8bbe222cf75656a214a1759470d4"


def write_csv(name, rows):
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with (HERE / name).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    v = json.loads((HERE / "validation.json").read_text())
    m = v["fixed_network"]["base_sub"]
    t = v["fixed_network"]["thresholds"]
    ledger = list(csv.DictReader((HERE / "ledger.csv").open()))
    legs = [r for r in ledger if r["record_type"] == "leg"]
    cfs = {r["case"]: r for r in csv.DictReader((HERE / "counterfactuals.csv").open())}
    findings = []
    def finding(id, priority, loc, observation, evidence, impact, correction, kind, novelty):
        findings.append(dict(id=id, priority=priority, source_sha=PIN, file_line=loc,
            observation=observation, evidence=evidence, impact_on_388_or_recommendation=impact,
            concrete_correction=correction, classification=kind, known_or_new=novelty,
            units_period_geography="RUB/model year of 52 weeks; OMS network unless stated"))
    finding("RPL-01", "P1", "src/network_model.py:57",
        "Любое не-MOW плечо получает 1773 RUB на новый сегмент; право, ставка, лимит и контракт не проверяются кодом.",
        "ledger.csv: subsidy=1094131994.0921826 RUB; eligible segments=617107.7236842542; model rule only. data/assumptions/network.csv:43 openly qualifies mean.",
        f"Fixed sub12 without support={float(cfs['base_sub12_support0']['contribution_rub_year'])}; zero requires {t['support_fraction_for_zero']:.12f} of modeled support before unknown costs.",
        "Добавить по каждому плечу award_status/rate/cap/period/paid_unit; UNKNOWN entitlement оставить UNKNOWN. Нынешнюю среднюю сохранить именованным сценарием, дать support0/current рядом.",
        "допущение + ограничение; не доказанный арифметический баг", "известно late_owner_delta; новый численный fixed-network порог")
    finding("RPL-02", "P1", "src/network_model.py:168",
        "+388 есть contribution после заданных переменных расходов, до полного добавочного бюджета и дельты прежней сети.",
        f"ledger.csv; cost_coverage.csv; contribution={m['contribution_rub_year']}; src/network_model.py:23 excludes lease/base/office.",
        "FullPnL UNKNOWN. При D_old=0 сумма всех оставшихся добавочных расходов до нуля не больше 387722372.7102387 RUB/year.",
        "Публиковать C=387722372.71; ΔPnL=C+D_old−K_unknown. Составить lease/base/support/startup/opportunity budget без повторного вычета уже включённых статей; cash отдельно.",
        "ограничение", "известно; новый точный бюджетный потолок")
    finding("RPL-03", "P1", "src/network_model.py:266",
        "Переток учтён как min(local carried, listed old RW pax); старый тариф приравнен новому; старые flight costs не уменьшаются и old passenger saving не возвращается.",
        "Base8: migrated=8840; foregone=144755158.71722305 RUB. Base_sub12: listed local/transfer overlaps=0. No original-network schedule/delta in return at :284. rw_routes_now.csv has 41 pairs, not a complete airline baseline.",
        "Для sub12 численный эффект перечисленного перетока 0; это не доказательство отсутствия любого own-RW diversion. Нельзя второй раз вычитать эти же foregone receipts.",
        "Добавить KEEP/CANCEL/REPLACE по старым рейсам, retained fare/subsidy/pax-cost saving/donor delta. Пока UNKNOWN; вариант saved old pax cost=8840×500=4420000 RUB/year только для base8 при явном условии избегаемости.",
        "ограничение + сценарное допущение; не баг знака", "известная проблема; проверен новый ledger")
    finding("RPL-04", "P2", "src/network_model.py:278",
        "Одна transfer OD получает билет один раз и субсидию на каждое не-MOW плечо. Это две разные единицы, а не повтор билета.",
        "36 OD rows: 12 local+24 transfer. ticket OD sum=leg allocated sum; subsidy OD sum=leg sum. OD-only scenario uses 384183.30576663266 eligible OD; exact support in counterfactuals.csv.",
        "При одной выплате на OD вне Москвы тот же supply/sales даёт −25252620.25770378 RUB/year. Законность оплаты по плечам этим опытом не установлена.",
        "Явно подписать paid_unit=eligible carried segment; рядом оставить one_nonMOW_OD как сценарий. Единицу фактического договора подтвердит sources; автоматическую смену правила не применять.",
        "проверенный факт кода + альтернативный сценарий", "семантика известна; новый fixed-sales сценарий")
    finding("RPL-05", "P2", "src/dashboard_template.html:723",
        "Лестница вычисляет result повторным вычитанием независимо округлённых revenue и cost, расходясь с result_mln_year.",
        "panel_validation.json: 6/24 rows differ by ±1 mln RUB; KUF/base −282 vs −283; KUF/base_sub +343 vs +342. Embedded JSON itself matches replay.",
        "OMS base_sub остаётся +388; исходная экономика не меняется, но отображённые итоги шести строк неверно округлены.",
        "Применить patches/001_authoritative_rounded_result.patch: при slider0 брать авторский result; slope оставить rounded net ticket receipts. Проверено patch application и JS arithmetic 24 rows; точный monetary slider требует будущих unrounded полей.",
        "доказанная ошибка отображения", "новое в этом проходе")
    finding("RPL-06", "P2", "src/network_model.py:522",
        "routes прямой сети = число треугольников; routes хаба = число лучей. Сравнение 8 и 12 использует разные единицы.",
        "validation.json direct_counts: direct 8 programs/24 leg rows in every scenario; unique endpoint pairs base/base_sub/cautious/cautious_sub=18/19/21/20. MOW is city aggregate, not identified airport.",
        "Не меняет OMS388. Число 8 само по себе не доказывает выполнение требования 8–12 уникальных связей для direct; это уже отмечено late-owner audit.",
        "Экспортировать program_count/leg_rows/unique_city_pairs отдельно, не переопределять сеть и не оптимизировать города. В UI подписать треугольники; airport-pair count UNKNOWN до выбора MOW airport.",
        "ограничение единицы/представления", "известно; повторён новый export")
    finding("RPL-07", "P2", "src/network_model.py:539",
        "mandatory table выбирает только base, подмешивает cautious по variant/from/to и не экспортирует base_sub. Пустые cautious могут означать другую сеть.",
        "Replayed mandatory_routes_table.csv:64 rows,24 missing cautious. Новый 12-spoke base_sub присутствует в network_routes.csv и HTML net.routes, но отсутствует в этой mandatory table.",
        "+388 не снабжён соответствующей обязательной CSV таблицей; NaN нельзя заменить нулём или считать спросом на fixed base network.",
        "Добавить отдельный scenario×variant×pair export для четырёх выбранных сетей, сохраняя реальные частоты каждого scenario. Fixed-network cautious demand при необходимости считать отдельно и именовать.",
        "известное ограничение экспорта; не нулевой спрос", "известно late_owner_delta; подтверждено replay")
    finding("RPL-08", "P1", "src/network_model.py:467",
        "fare_rev/net revenue означает gross tariff receipts после foregone, а не net после налогов, комиссии, возвратов и продажи трансфера.",
        "fare() at :171 is fixed+km; :272/:277 charge once per OD; no explicit tax/commission/refund bridge. cost bases are mixed reference assumptions from UFA.",
        f"До неучтённых затрат допустимая общая потеря билетных поступлений {100*(1-t['ticket_receipt_fraction_for_zero']):.9f}% от gross обнуляет вклад, если support/cost unchanged.",
        "Назвать поле ticket_after_migration, добавить gross→retained receipts bridge по датам/единицам. Налоговую корректировку или комиссии сейчас не придумывать и не снимать НДС повторно.",
        "ограничение; сценарные тарифы", "известно ранее; новый fixed-network порог")
    finding("RPL-09", "P2", "src/network_model.py:289",
        "Base8→base_sub12 меняет состав сети и ресурс; разность их итогов не является чистым эффектом субсидии.",
        "counterfactuals.csv: base8 support0 −367061628.90116817; support1 +174189700.33066338; sub12 support0 −706409621.3819437; support1 +387722372.7102387.",
        "Sub12 expansion lowers unsupported contribution by 339347992.48077554, then modeled support adds1094131994.0921826. Положительный результат сохранён.",
        "Показывать fixed-network матрицу 2×2; bridge имеет раскрытый последовательный порядок demand→competitor basis→migration→base8→sub12→support, не уникальные независимые эффекты.",
        "проверенный факт + ограничение причинного сравнения", "известная постановка; новый численный мост")
    finding("RPL-10", "P3", "src/demand_model.py:70",
        "Чистый checkout не содержит ignored raw TOCHNO CSV; системный python3 не имеет pandas. Это препятствие упаковки/окружения, не финансовая ошибка.",
        "Existing local CSV hash=aed8463339b988a7c9ac81aa976a4fc25c152e4066b551d25cbdcc16ebe16d53 equals data/raw/_manifest.json:60; used Python3.12.14/pandas2.2.3/numpy2.3.5.",
        "Обычный src/network_model.py без подготовки на этой машине падает до расчёта; offline replay устраняет этот барьер без изменения protected inputs.",
        "Запускать reproduce.py локальным Python с requirements.txt; public source gzip включён в replay/inputs с лицензией/версией/хешем. Не запускать update.py --force (оно качает и пишет общие данные).",
        "runtime/packaging ограничение", "локально подтверждено")
    finding("RPL-11", "P3", "src/network_model.py:372",
        "Прежний double capture общей direct пары не воспроизведён; joint делит один pooled flow и одну migration между программами.",
        "validation.json fixed_network.direct_pair_checks:4 scenario probes; expected=min(D×share(totalF),capacity(totalF)); sums of carried and migration match to<1e-9 passenger/week/direction.",
        "Нет основания ещё раз исправлять старый B3 или ухудшать OMS388. Fuel factor134896 in :166 применяется однократно, отдельного uplift1696 в формуле нет.",
        "Сохранить существующий joint и единичный fuel cost; при новых изменениях повторять pooled-pair accounting invariants. Это подтверждение ограниченного scope, не рыночной достоверности.",
        "проверенный факт; дефект не обнаружен", "известное исправление; проверено на текущем pin")
    write_csv("findings.csv", findings)

    coverage = []
    def cost(item, field, status, formula, loc, note):
        amount = sum(float(x[field]) for x in legs) if field else "UNKNOWN"
        coverage.append(dict(item=item, status=status, amount_rub_model_year=amount, unit="RUB/year_52_model_weeks",
            geography="OMS_base_sub12", formula_or_boundary=formula, source_sha=PIN, file_line=loc, qualification=note))
    cost("fuel incl model uplift", "fuel_rub_year", "INCLUDED_REFERENCE_ASSUMPTION", "flights×(1.55×BH+0.2)×134896", "src/network_model.py:166", "134896=133200+1696 once; common UFA proxy, no current route contract confirmation")
    cost("MRO variable", "mro_rub_year", "INCLUDED_ASSUMPTION", "block_hours×35000", "src/network_model.py:167", "Not complete maintenance reserves/entry-into-service budget")
    cost("crew variable", "crew_rub_year", "INCLUDED_ASSUMPTION", "block_hours×15000", "src/network_model.py:167", "Does not prove headcount, training, positioning, accommodation or fixed payroll coverage")
    cost("navigation", "navigation_rub_year", "INCLUDED_ASSUMPTION", "block_hours×6000", "src/network_model.py:167", "Common proxy")
    cost("airport/ground basket", "ground_rub_year", "INCLUDED_REFERENCE_ASSUMPTION", "flights×96089", "src/network_model.py:168", "UFA SSJ basket for every endpoint; exact included services and other-airport deltas unknown; avoid adding whole basket twice")
    cost("deicing expected", "deicing_rub_year", "INCLUDED_ASSUMPTION", "flights×15000", "src/network_model.py:168", "0.25×60000 expectation all model weeks; no seasonal calendar")
    cost("passenger variable", "pax_variable_rub_year", "INCLUDED_ASSUMPTION", "carried segments×500", "src/network_model.py:168", "Transfer OD pays this cost twice because it occupies 2 legs; not duplicate ticket revenue")
    cost("total known variable costs", "variable_cost_rub_year", "TOTAL_INCLUDED_NOT_ADDITIVE", "sum above; not another cost", "src/network_model.py:270", "Do not sum this total with its component rows")
    cost("lease/depreciation/financing", None, "UNKNOWN_NOT_ZERO", "incremental annual fleet cost; no assumed price", "src/network_model.py:23", "8 total model aircraft includes1 spare; available resource and alternative employment unknown")
    cost("new base/fixed ground/office", None, "UNKNOWN_NOT_ZERO", "incremental only; subtract what already in ground basket", "src/network_model.py:23", "Base staff, facilities, storage, support agreements unknown")
    cost("entry/training/recruitment", None, "UNKNOWN_NOT_ZERO", "periodized PnL separately from upfront cash", "src/network_model.py:167", "MRO/crew hourly proxies do not specify inclusion; avoid full duplicate budgets")
    cost("sales/GDS/payment/transfer product", None, "UNKNOWN_OR_POSSIBLY_IN_PAX_PROXY", "incremental item minus amount already covered by500", "src/network_model.py:168", "No fee schedule or protected connection budget")
    cost("delays/cancellations/refunds/reaccommodation", None, "UNKNOWN_NOT_ZERO", "dated disruption/residual seats/cash required", "src/network_model.py:430", "kover_days is descriptive exposure; not a financial disruption model")
    cost("taxes/retained fare/cost tax compatibility", None, "UNKNOWN_NOT_ZERO", "net receipt and recoverable cost bridge; no automatic VAT stripping", "src/network_model.py:467", "Ticket_after_migration is not ex-tax ex-commission net yield")
    cost("old-network saving/loss/opportunity", None, "UNKNOWN_SIGNED_DELTA", "D_old excludes foregone already deducted; KEEP flight cost delta0 if unchanged", "src/network_model.py:274", "Base_sub listed migrated0; lost subsidy/old yields/old flown legs and displaced productive resource unresolved")
    cost("working capital/deposit/capex", None, "UNKNOWN_CASH_NOT_AUTOMATIC_PNL", "dated receipts/payments; avoid treating cash deposit as PnL cost", "src/network_model.py:23", "Cash plan not present")
    coverage.append(dict(item="aggregate allowance before zero", status="THRESHOLD_NOT_COST_ESTIMATE",
        amount_rub_model_year=m["contribution_rub_year"], unit="RUB/year_52_model_weeks", geography="OMS_base_sub12",
        formula_or_boundary="K_unknown <= 387722372.7102387 + D_old; stated number assumes D_old=0", source_sha=PIN,
        file_line="src/network_model.py:284", qualification="4.0387747157 mln RUB per total model aircraft-month only if this is the sole omitted expense; no lease quote"))
    write_csv("cost_coverage.csv", coverage)
    prior_path = "context/25_completion_audit_20261110/hypotheses/positive_historical_scenarios.csv"
    prior = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{PRIOR}:{prior_path}"])
    (HERE / "inputs/prior_positive_scenarios.csv").write_bytes(prior)
    positives = list(csv.DictReader(prior.decode().splitlines()))
    bridge_rows = list(csv.DictReader((HERE / "version_bridge.csv").open()))
    money = lambda x: f"{float(x):,.2f}".replace(",", " ")
    parts = ["# Replay OMS +388 — один основной проход\n",
        f"Pin `{PIN}`, branch `audit/oms388-independent-20261110`. Реально выполнены неизменённые `main()` owner165, owner4a976 и pin в удаляемых sandbox. Все 389 protected SHA-256 совпали до и после. Только `replay/`; без внешнего исследования, оптимизации новых городов, commit/push и обращений к людям.\n",
        "## Результат и денежный смысл\n",
        f"**+388 воспроизводится: +{money(m['contribution_rub_year'])} ₽ за модельный год 52 недель.** Это вклад после заданных переменных расходов. FullPnL и cash — UNKNOWN, не ноль. Типичный будущий год около 2028, спрос2025, цены2025–2026, без календаря и роста рынка; не фактические продажи.\n",
        "| Статья OMS base_sub12 | ₽ / модельный год |\n|---|---:|",
        f"| Билетные поступления gross | {money(m['ticket_gross_rub_year'])} |",
        f"| Вычет собственной старой выручки по перечисленным парам | {money(m['foregone_rw_rub_year'])} |",
        f"| Билеты после перетока (не налоговый net yield) | {money(m['ticket_after_migration_rub_year'])} |",
        f"| Сценарная поддержка | {money(m['subsidy_rub_year'])} |",
        f"| Всего поступлений в модели | {money(m['total_revenue_rub_year'])} |",
        f"| Учтённые переменные расходы | {money(m['variable_cost_rub_year'])} |",
        f"| Contribution | **{money(m['contribution_rub_year'])}** |\n",
        f"{m['segments_year']:.6f} сегментов = {m['od_trips_year']:.6f} поездок + {m['transfer_trips_year']:.6f} пересадочных поездок; местных {m['local_trips_year']:.6f}. 7 904 рейса, {m['block_hours_year']:.6f} блок-часов, 7 рабочих модельных бортов +1 резерв. Это средняя часовая потребность, не доказанное расписание.\n",
        "`ledger.csv`: 12 leg rows +12 local OD +24 transfer OD. На OD билет записан один раз; для сверки на legs transfer revenue разнесена 50/50 (это только бухгалтерское распределение). Суммировать OD и leg деньги вместе нельзя. Расходы в leg rows разбиты на топливо, ТО, экипаж, навигацию, ground, deicing, пассажира. Все денежные и сегментные тождества сошлись.\n",
        "## Контрфакты при фиксированной сети\n",
        "| Сеть / поддержка | Contribution, ₽ / модельный год |\n|---|---:|",
    ]
    for case, label in [("base8_support0", "Base8 / 0"), ("base8_support1", "Base8 / current"), ("base_sub12_support0", "Sub12 / 0"), ("base_sub12_support1", "Sub12 / current"), ("base_sub12_one_payment_per_nonMOW_OD", "Sub12 / одна выплата на OD вне MOW — сценарий")]:
        parts.append(f"| {label} | {money(cfs[case]['contribution_rub_year'])} |")
    parts += ["\nВнутри каждой пары support0/current одинаковы рейсы, частоты, продажи и расходы. В текущем коде платятся **сегменты**, не конечные поездки. One-OD сценарий не объявляется правовым исправлением или багом. Право и ставка фактической поддержки — за пределами replay.\n",
        f"На Sub12 ноль до неизвестных расходов требует {100*t['support_fraction_for_zero']:.6f}% сценарной поддержки, или {t['rub_per_eligible_segment_for_zero']:.6f} ₽ на eligible segment. Без поддержки дефицит706.410 млн ₽. При неизменной поддержке общая потеря {100*(1-t['ticket_receipt_fraction_for_zero']):.6f}% модельных билетных поступлений съедает весь вклад. Эти пороги держат спрос/рейсы постоянными.\n",
        f"Полный добавочный бюджет: `ΔPnL = 387 722 372.7102387 + D_old − K_unknown`. При `D_old=0` максимум всех пропущенных добавочных затрат до нуля —387.722 млн ₽/год. Условный потолок4.038775 млн ₽ на каждый из8 бортов в месяц предполагает, что это единственная пропущенная статья; **это не оценка аренды**. `cost_coverage.csv` показывает границы включения, возможные перекрытия и UNKNOWN. Старые неизменённые flight costs не вычитать повторно; уже вычтенную foregone revenue не вычитать снова.\n",
        "## Мост версий\n",
        "Ниже последовательная атрибуция из `version_bridge.csv`, не уникальный причинный/Shapley расклад. При изменении спроса/состава частоты и capacity пересчитываются owner build; субсидия и migration в fixed topology частоты не меняют.\n",
        "| Переход | Δ млн ₽/год | Уровень млн ₽/год |\n|---|---:|---:|",
    ]
    for row in bridge_rows:
        parts.append(f"| {row['stage']} | {float(row['delta_rub_year'])/1e6:.6f} | {float(row['contribution_rub_year'])/1e6:.6f} |")
    parts += ["\nИсходный owner165: SHA`1654110dfdc3f6737aebce95e46dd993d631be5b`; owner4a976: SHA`4a9763565f70b9ab1eddde2f5daca07687560948`. Старый ввод на current build даёт ровно старый −312.097208 млн ₽, остаток0. Общие тарифные и стоимостные параметры не изменились; их эффект в этом version bridge0. Смена сегментного спроса на endpoint и базы конкурентной частоты разделена в заданном порядке, но обратный порядок даст другой разрез. 4a976→d4a: денежная дельта0, шаблон панели менялся. Сети сравниваются внутри того же годового контура.\n",
        "Прежний C/N из context23/24 — другой недельный опыт на других fixed supply/ценах/own-RW accounting. В годовой мост он не включён и на52 не умножен. Отрицательные исходные C/N сети не опровергают все положительные сценарии. Из прошлого принятого аудита без пересчёта сохранены `inputs/prior_positive_scenarios.csv` (" + str(len(positives)) + " строк): положительные source-linked сценарии SVX–MRV и SVX–AER при заданных endpoint/winter коэффициентах. Это иные продукты, не подтверждённый спрос/net yield и не доказательство OMS388. Источник архивной выборки: SHA`" + PRIOR + "`:" + prior_path + ".\n",
        "## Замечания и исправление\n",
        "Полный реестр — `findings.csv`: у каждого ID есть приоритет, exact SHA, file:line, доказательство, влияние, конкретная правка, тип и новизна. Основные ограничения: фактическая поддержка/полный бюджет/старые рейсы/retained yield. Известные 8 треугольников —24 строки legs и18/19/21/20 уникальных модельных city-pairs; это не8 airport-pairs. Mandatory CSV не содержит base_sub; 24 пустых cautious не равны нулевому спросу. Прежний B3 повторного direct capture не обнаружен; четыре pooled-pair accounting проверки прошли. Uplift в134896 ₽/т применён один раз.\n",
        "**Доказанная новая ошибка только отображения:** шесть строк лестницы расходятся с авторским округлённым итогом на±1 млн ₽. `patches/001_authoritative_rounded_result.patch` использует result при нулевом slider; patch применён только в sandbox, arithmetic проверена Node по всем24 строкам. OMS388 и все модельные деньги не меняются. Slope slider остаётся на округлённых ticket receipts; полный UI/DOM не проверялся.\n",
        "HTML `const D.net` совпал с новым `load_network()` по summary24/routes265/asm16/check6/nodes38. Четыре CSV совпали по значениям у pin и4a976, три у165; байты отличаются CRLF↔LF, а в summary165 ещё знаком0.0/−0.0 в двух контрольных нулях. Старый methods/README.md отсутствует по указанному пути a77e4cf: вместо него через git show прочитаны handoff_compact.md/model_comparison.md/common_comparison_readout.md; это не молчаливая приёмка новой модели.\n",
        "## Точный повтор без сети\n",
        "Из корня этой рабочей копии, на указанном pin, с локальными git-объектами трёх owner версий и protected_owner_files.json:\n",
        "```bash\nREPLAY_PYTHON=/home/mputi/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3\n\"$REPLAY_PYTHON\" context/27_oms388_independent_audit_20261110/replay/reproduce.py\n\"$REPLAY_PYTHON\" context/27_oms388_independent_audit_20261110/replay/check_results.py\n```\n",
        "Python3.12.14, pandas2.2.3, numpy2.3.5; также нужны git, patch, Node. `requirements.txt` фиксирует библиотеки для другого подготовленного Python; сам replay ничего не скачивает. Public TOCHNO CSV упакован в `inputs/tochno_intercity.csv.gz`, версия29.06.2026, CC BY4.0, источник указан в owner `data/raw/SOURCES.md:10`; распакованный SHA-256 `aed8463339b988a7c9ac81aa976a4fc25c152e4066b551d25cbdcc16ebe16d53` совпал с owner manifest. Никаких приватных переписок/контактов/идентификаторов сессий в пакет не копировалось.\n",
        "Остановлен после основного прохода. Не установлены: рыночная достоверность endpoint demand/цен, договорная единица субсидии, incremental full budget, old-network baseline, bookability и dispatch. Для них нужны адресные входы координатора; дополнительные поиски/раунды не выполнялись.\n",
    ]
    (HERE / "README.md").write_text("\n".join(parts), encoding="utf-8")
    print(json.dumps({"findings": len(findings), "cost_coverage_rows": len(coverage), "prior_positive_scenarios": len(positives)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
