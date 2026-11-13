# P38 — общий расчётный контракт

Ограниченный локальный handoff для основного joint/monthly этапа. Численные market inputs не заменены. Это исполняемый адаптер и аудит входов, без нового генератора сетей, выбора стратегии или операционного допуска.

Из корня данного репозитория:

```sh
python3 -B context/38_direct_strategy_20261113/contract/verify.py
python3 -B context/38_direct_strategy_20261113/contract/month_adapter.py --month 2027-07 --candidate X_SVX_KJA --scenario base
```

CLI адаптера выводит JSON в stdout. Проверка пишет только собственный `validation.json`. Старые build/verify/exporter не вызываются. Зависимости — стандартная библиотека и закреплённые локальные P31/P34/P05/P06; интернет не нужен.

Все 60 P36-программ внесены в inventory; 37 положительны по `new − same WITHOUT_NEW` хотя бы в одном прежнем сценарии. Их 25 физических пар сохранены полностью, включая прежний top5 и AER-контроли. CEK–SVX и SVX–TJM в этом seed — оплачиваемое positioning с нулём кресел/продаж. Положительность цепи не доказывает прибыльность отдельной пары или коммерческую новизну.

Обнаружены два пропуска прежнего P31 `route_universe`: CEK–SVX и MOW–SVX, последний нужен для физического SVX–ZIA. Новый контракт сохраняет их события явно. DME и ZIA различаются в календаре и совместно используют MOW OD. Треугольник с одним направлением регионального плеча не заменяет предложение туда-обратно.

`monthly_input_audit.csv` — компактный snapshot с точными Git SHA:path:line и первичной lineage: 5 релевантных segment-наблюдений, 12 carrier-month значений активного профиля, 12 KJA airport totals, 9 альтернативных UT monthly totals и 3 сводки определения/покрытия. Endpoint OD не допущены. P01 различает сегменты, аэропортовые события и carrier passengers; SHA и статус источника не подтверждают экономическую применимость. Полные поздние P08/P09/P01 проверены по pin; пять снимков P36 не использованы как предел аудита.

По сообщению координатора, адресные `market_admission/` и `cost_admission/` завершены: 81 новый primary service positive и 23 public rates, **numeric OD/net/actual invoice updates = 0**, без replacement. Это переданный scope gate, не новые финансовые inputs и не независимая проверка их пакетов. Живые агентские outputs не читались; ожидания исследований нет.

Основному расчёту передаются `engine_handoff.md`, `common_contract.json` и `resource_contract.json`. `validation.json` содержит реальные receipts календаря, joint/P06 и порогов; PASS относится к контракту. Actual OD/net, release/R1, внешний D3/Moscow D, договорные F, crew/rest/MRO/slots/payload, full PnL и cash остаются UNKNOWN.

Записи ограничены этой папкой. Реестр защиты содержит 1621 прежний файл; 1614 неизменяемых проверяются по содержимому, 7 mutable delegation metadata исключены из guard и финансовых входов. Прежние P36/P37 и панель не изменялись; git commit/push/checkout/merge/reset не выполнялись. После handoff — STOP.
