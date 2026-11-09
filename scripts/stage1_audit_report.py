"""Compact static report artifacts generated only from computed round-2 outputs."""
from html import escape
from pathlib import Path
import pandas as pd


def write_reports(root,data,summary,attribution):
    a=root/'context/22_stage1_audit'
    s=pd.DataFrame(summary);f=pd.read_csv(a/'final_scores.csv')
    main=f[(f.stress=='base')&(f.min_dist_km==500)&(f['mode']=='expansion_allowed')&(f.profile=='balanced')]
    def pick(profile='balanced',distance=500,mode='expansion_allowed',stress='base'):
        return s[(s.profile==profile)&(s.min_dist_km==distance)&(s['mode']==mode)&(s.stress==stress)].iloc[0]
    p=pick();strict=pick(mode='strict_new');no=pick(distance=0)
    tops=lambda r:r['top3_cities'].replace(' / ',' — ')
    table='\n'.join('| '+str(r.city)+' | '+f'{r.score:.9f}'+' | '+f'{r.score_low:.6f}–{r.score_high:.6f}'+' | '+f'{r.rank_best}–{r.rank_worst}'+' | '+f'{r.unknown_weight_share:.0%} / {r.indirect_weight_share:.0%}'+' |' for r in main.head(4).itertuples())
    profiles='\n'.join(f"- **{x['label']}** (`{x['id']}`): {tops(pick(x['id']))}." for x in data['stage1']['profiles'])
    at=pd.DataFrame(attribution);atlines=[]
    labels=['исходные данные/веса/шкалы','исправленные данные и центральные UNKNOWN-допущения','фиксированные шкалы','предложенные веса','строгий допуск']
    for (step,g),label in zip(at.groupby('step',sort=False),labels):atlines.append(f"{label}: "+' / '.join(g.head(3).iata))
    brief=f'''# Шаг 1: пересчёт для обсуждения, 10 ноября 2026

Это предложение методики, **не team-approved**. Рейтинг сравнивает условную привлекательность проекта; он не оценивает прибыль, продажи, физическую базу или готовность аэропорта запустить стыковочную волну. Исходный срез `2f03b693a62c219e9475fcd1e26295039f6a49d7` сохранён в baseline. Нового research, сетевых загрузок, оптимизаторов и расчёта экономики не было. Незакоммиченные исправления первого прохода сохранены. Ветка `research/stage1-panel-audit-20261110`; commit/push не выполнялись.

Основной режим сохраняет фильтр ≥500 км до исторического набора SVO/DME/VKO/SVX и разрешает развитие существующей опоры. Не прошли PEE/UFA/GOJ/CEK/TJM. Расстояния — ортодромические географические proxy, а порог500 — нормативное правило, без измеренной каннибализации. Физическая пригодность маршрутов, слоты, MCT, багаж, договоры ТО и ресурсы остаются условными воротами: UNKNOWN не означает ни подтверждённую пригодность, ни автоматическое исключение.

## Результат и хрупкая граница

Основной топ-3: **{tops(p)}**. Барнаул опережает Самару всего на **{p.third_fourth_gap:.9f}** балла0–1. Нижняя/верхняя оценки и ранги ниже — сценарные границы закодированных неопределённостей, не доверительные интервалы. Совместная реализуемость всех независимых крайних значений не установлена.

| Город | Балл | Диапазон балла | Место | Вес UNKNOWN / INDIRECT |
|---|---:|---:|---:|---:|
{table}

При strict_new с500: **{tops(strict)}**, разрыв третьего с четвёртым **{strict.third_fourth_gap:.9f}**. Симметрично исключены KUF/KZN/AER/MCX по первичному опорному статусу. OMS и CEK не исключены автоматически: старая wiki и отсутствие в перечне не решают их текущий статус. Их участие остаётся conditional. Без500, на тех же шкалах: **{tops(no)}**; разрыв третьего с четвёртым **{no.third_fourth_gap:.9f}**. Это отдельная чувствительность, основной фильтр не отключён.

## Смысл 18 рекомендуемых весов

Сумма100; веса нормативные и не подогнаны под лидера. Proxy рынка ограничены45: gap_pop13 — население направлений с пробелом связности; transfer12 — модельно взвешенная геометрия пар; локальное население10 — демографическая основа; pax2025 семь — обслуженный масштаб; зарплата3 — частичный proxy платёжеспособности. Эти признаки зависимы и не являются пятью независимыми доказательствами наблюдённого спроса.

Операционный блок45: дни публикаций ограничений22 — исторический proxy риска; погода7 — исследовательский показатель с непроверенным покрытием; зона трансфера8 — организация пересадки; ТО SSJ8 — опубликованная техническая возможность. Конкурент7 отражает наличие чужой базы, без измерения доминирования. Стратегия3 — явное предпочтение акционеров, без денежной оценки. Нулевые веса: расстояние — только допуск500; Ростех — справочно, без обещаний доступа к мощностям; H24 — проверка режима волны; SSJ_ops — справочная практика приёма; RW_support — классификация допуска; demand_gap — зависимая модельная производная; pax2019 — исторический контекст. Постоянный критерий даёт нейтральные0,5.

Альтернативы рассчитаны без назначения нового профиля:

{profiles}

Строгие и безфильтровые результаты всех профилей есть в final_comparison.csv и summary.html. Common-neutral стресс задаёт конкуренту, ТО и трансферу0,5 **у всех**: основная тройка balanced сохраняется, но это не доказывает устойчивости к другим неизвестным. При intro-only на сохранённой колонке тройка становится **{tops(pick(stress='intro_only'))}**, разрыв третьего с четвёртым **{pick(stress='intro_only').third_fourth_gap:.9f}**. Основной показатель сохранён: дни публикаций введения или снятия, без вывода о потерянных стыковках.

## Исправленные данные и метод

Слабые competitor0,25/0,75 и косвенное ТО перестали считаться точными числами: raw пустой, статус отдельно, центр0,5 и диапазон0–1. Ошибка знака в исследовании OMS исправлена: competitor0,25→0,5 при направлении «−» **снижает** балл. OMS transfer_zone из старого отрицания и IKT из международного контекста переведены в UNKNOWN; KZN вторичная трансферная публикация — INDIRECT. REN/KUF зона трансфера и ТО UNKNOWN.

Для REN сохранён факт **>951000** за2025. Производные951100 и951000–951200 требуют обычного округления каждой опубликованной компоненты885500 и65600 до сотни. Нижний951000 сценарий меняет балл REN лишь на **0,000000598**, порядок не меняется. Точный итог UNKNOWN. Верх12,5млн показан только как край шкалы, без физического прогноза. Прочие приблизительные pax получили полный сценарный диапазон при неизвестной точности; расхождение итогов CEK передано отдельным интервалом.

Шкалы20 городов заморожены до отбора, clipping одинаков во всех сценариях. Неизвестный поезд даёт gap-интервал; неполный зарплатный охват и импутации населения расширяют utility до0–1 без штрафного множителя. Для transfer сохранён только агрегат base: парных cautious/optimistic выходов нет, используется полный модельный диапазон шкалы. Погода нейтрализована в центре и имеет0–1: локальных gz нет, достоверное поле из старого расчёта восстановить нельзя. Sentinel−9999 и валидные знаменатели исправлены и проверены fixture; полное почасовое покрытие не доказано.

Последовательное разложение смены тройки (порядок-зависимое, не Shapley): {'; '.join(atlines)}. Полные баллы каждого шага — attribution.csv. Оно отделяет данные, шкалы, веса и допуск; ни один переход не объявлен причинным доказательством экономической выгоды.

## Источники, проверка и незакрытое

[RW,27.10.2026](https://flyredwings.com/press/news/red-wings-pereshla-na-osenne-zimnee-raspisanie-poletov/) подтверждает опоры, без вывода о физическом базировании. [OMS,03.12.2024](https://www.aeroomsk.ru/ob-aeroporte/press-tsentr/novosti/207/) описывает действующее ТО SSJ для RW/России/Азимута; текущий договор, мощность и область допуска UNKNOWN. [REN,15.01.2026](https://ar-ren.ru/about/news/aeroport-orenburg-obsluzhil-za-2025-god-bolee-950/) публикует нижнюю границу и округлённые компоненты. Это принятые адресные проверки основной модели, без нового чтения сети интегратором. Даты доступа10.11.2026 отделены от publication_date. Прочие сохранённые источники и их ограничения видны в evidence_ledger.csv и карточках панели.

Проверены140 конфигураций Python/реального JS через Node,2170 сравнений городов: максимальное расхождение0. Проверены маски, интервалы, исключённые составы, RNG, clipping, постоянный признак, некорректные веса, погодный fixture и один детерминированный повтор. Baseline/raw/Excel и встроенные пейлоады шагов2–4 неизменны. Эти шаги и экономика **не проверены этим аудитом**. Полная неопределённость реального проекта **НЕ выполнена**: отсутствуют OD/захват, совместные ошибки, полнота публикаций и почасовая погода. ZIA+SVX чувствительность не выполнена без raw координат. Совпадение панели относится к вычислительному слою; браузерная проверка по заданию не запускалась.
'''
    (a/'brief.md').write_text(brief,encoding='utf-8')
    # Compact self-contained static exhibit, no JavaScript/CDN/server.
    trs=[]
    for x in data['stage1']['profiles']:
        cells=''.join('<td>'+escape(pick(x['id'],d,m)['top3'].replace(' / ',' · '))+'</td>' for d,m in [(500,'expansion_allowed'),(500,'strict_new'),(0,'expansion_allowed'),(0,'strict_new')])
        trs.append('<tr><th>'+escape(x['id'])+'</th>'+cells+'</tr>')
    weightlabels={'gap_pop':'Пробел связности','last365_days':'Дни публикаций','competitor_hub':'Чужая база','pax_2025':'Pax 2025','catchment_pop_2025':'Население','dist_bases_km':'Расстояние','transfer_demand_base':'Transfer proxy','strategy_region':'Стратегия','transfer_zone':'Трансфер','rostec_link':'Ростех','ssj_mro':'ТО SSJ','wage_2024':'Зарплата','bad_weather_days':'Погода','h24':'H24','ssj_ops':'SSJ ops','rw_support':'Опора RW','demand_gap':'Demand gap','pax_2019':'Pax 2019'}
    bars=''.join(f'<div class="w"><span>{weightlabels[c["key"]]}</span><i><b style="width:{c["weight"]/30*100:.2f}%"></b></i><strong>{c["weight"]:g}</strong></div>' for c in data['criteria'])
    rows=''.join(f'<tr><th>{escape(r.city)}</th><td>{r.score:.6f}</td><td>{r.rank_best}–{r.rank_worst}</td><td>{r.unknown_weight_share:.0%} / {r.indirect_weight_share:.0%}</td></tr>' for r in main.head(4).itertuples())
    html='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Шаг 1 · пересчёт</title><style>
:root{color-scheme:light dark;--foreground:#242a33;--card:rgba(127,140,155,.05);--border:rgba(127,140,155,.25);--chart-1:#c74648;--chart-2:#3f877e;--chart-3:#99823a;--chart-4:#6678a6;--chart-5:#9569a2}
@media(prefers-color-scheme:dark){:root{--foreground:#e1e6ee}}
*{box-sizing:border-box}html,body{margin:0;padding:0;background:transparent;color:var(--foreground);font:13px/1.45 system-ui,sans-serif}.outer{max-width:728px;width:100%;margin:0;background:transparent}h1{font-size:22px;margin:0 0 5px}h2{font-size:15px;margin:0 0 10px}p{margin:7px 0}.muted{opacity:.75;font-size:12px}.card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px;margin:12px 0}.lead{font-size:17px;font-weight:650}.gap{color:var(--chart-1);font-weight:650}table{border-collapse:collapse;width:100%;font-size:12px}th,td{text-align:left;padding:7px 4px;border-bottom:1px solid var(--border);vertical-align:top}thead th{font-size:10px;font-weight:600}tbody th{font-weight:550}.weights{display:grid;grid-template-columns:1fr 1fr;gap:8px 20px}.w{display:grid;grid-template-columns:110px 1fr 20px;gap:6px;align-items:center;font-size:12px}.w i{height:7px;background:var(--border);border-radius:9px;overflow:hidden}.w b{display:block;height:100%;background:var(--chart-2)}.w strong{text-align:right}.chip{display:inline-block;border:1px solid var(--border);padding:2px 7px;border-radius:10px;font-size:11px;margin-right:4px}.rules td{white-space:nowrap;font-variant-numeric:tabular-nums}@media(max-width:530px){h1{font-size:19px}.card{padding:10px}.rules{font-size:9px}.rules th,.rules td{padding:7px 2px}.rules tbody th{font-size:9px;max-width:60px;overflow-wrap:anywhere}.weights{gap:7px 12px}.w{grid-template-columns:84px 1fr 15px;font-size:10px;gap:4px}.lead{font-size:16px}}
</style><main class="outer"><h1>Шаг 1 · предложенная методика</h1><p class="muted">10.11.2026 · 20 городов · фиксированные шкалы · не решение команды</p>
'''
    html+=f'<section class="card"><h2>Основной режим: ≥500 км · развитие опоры допустимо</h2><p class="lead">{escape(tops(p))}</p><p class="gap">Барнаул − Самара: +{p.third_fourth_gap:.8f}</p><table><thead><tr><th>Кандидат</th><th>Балл 0–1</th><th>Место*</th><th>UNKNOWN / косвенные</th></tr></thead><tbody>{rows}</tbody></table><p class="muted">*Сценарные границы, не вероятности. Все кандидаты условны по проектным воротам.</p></section>'
    html+='<section class="card"><h2>Пять принятых для сравнения профилей</h2><table class="rules"><thead><tr><th>Профиль</th><th>500 · развитие</th><th>500 · новый</th><th>Без500 · развитие</th><th>Без500 · новый</th></tr></thead><tbody>'+''.join(trs)+'</tbody></table><p class="muted">Строгий режим исключает KUF/KZN/AER/MCX. OMS/CEK UNKNOWN, остаются условно. Без500 — только чувствительность.</p></section>'
    html+='<section class="card"><h2>Рекомендуемые веса · сумма 100</h2><p><span class="chip">Proxy рынка 45</span><span class="chip">Эксплуатация 45</span><span class="chip">Конкурент 7</span><span class="chip">Стратегия 3</span></p><div class="weights">'+bars+'</div></section>'
    html+=f'<section class="card"><h2>Что меняет границу тройки</h2><p>Intro-only «Ковёр»: <b>{escape(pick(stress="intro_only")["top3"])}</b>. Основной показатель — дни публикаций, без оценки потерянных стыковок.</p><p>Common-neutral документов: <b>{escape(pick(stress="common_neutral")["top3"])}</b>. REN951000 и производное951100 дают ту же тройку.</p><p>Transfer proxy: полный модельный диапазон0–1; погода UNKNOWN без архивов. Полная неопределённость проекта не восстановлена.</p><p class="muted">Python = реальный JS: 140 конфигураций, 2170 городских сравнений, ошибка0. Baseline сохранён; шаги2–4/Excel/экономика этим аудитом не проверены. Рейтинг не означает прибыль.</p></section></main></html>'
    (a/'summary.html').write_text(html,encoding='utf-8')
    docs=f'''# 25. Шаг 1: пересчитанный скрининг, 10.11.2026

Результат для обсуждения, **не решение команды**. Авторитетный вход: [brief](../context/22_stage1_audit/brief.md), [сценарии](../context/22_stage1_audit/final_comparison.csv), [валидация](../context/22_stage1_audit/final_validation.json). Панель: [outputs/redwings_panel.html](../outputs/redwings_panel.html).

Основной режим сохраняет500км, допускает развитие опоры и фиксирует шкалы20 городов: **{tops(p)}**. Разрыв третьего с четвёртым: **{p.third_fourth_gap:.9f}**. Strict_new: **{tops(strict)}**; без500: **{tops(no)}**. У всех трёх основных лидеров сценарные места1–15. Это широкие границы закодированных неизвестных, не вероятность выбора.

Прежнее утверждение об одинаковых первых двух во всех профилях было ошибочным уже для baseline. При новых профилях тройка тоже меняется:

{profiles}

Intro-only даёт {tops(pick(stress='intro_only'))}. Поэтому третье место нельзя объявлять устойчивым. Частоты случайных весов — диагностическое семейство, не вероятность истинного ранга.

Исправлены слабые числовые свидетельства, интервалы квалифицированного pax, фиксированные шкалы, неизвестный поезд, охват зарплаты/населения. OMS опубликованное ТО принято на03.12.2024, текущая договорная доступность UNKNOWN. REN точный итог UNKNOWN; факт>951000, производное951100 допустимо только с оговоркой округления. KUF/REN трансфер и ТО UNKNOWN. Опорный статус не равен физической базе или хабу.

Weather sentinel и знаменатель исправлены; gz отсутствуют, поэтому погода UNKNOWN. Transfer остаётся модельным proxy с полным сценарием шкалы. Полнота публикаций/почасовой погоды, OD/конверсия, совместная реализуемость и экономика не восстановлены. Географические радиусы не являются эксплуатационным допуском.

Воспроизведение без сети, пересборки Excel и шагов2–4:

```sh
/home/mputi/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12 scripts/finalize_stage1_audit.py
```

Baseline и старый текст документа сохранены в [baseline](../context/22_stage1_audit/baseline/). Изменение ручного CSV само по себе не означает принятия факта: нужен явный пересмотр принятого snapshot и правил. Новые веса100 — предложение, а не автоматическое утверждение команды.
'''
    (root/'docs/25_step1_open_questions.md').write_text(docs,encoding='utf-8')
