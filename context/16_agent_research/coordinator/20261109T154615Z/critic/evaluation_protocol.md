# Границы проверки Phase2

Каждая проверка ссылается на immutable Git/input-set и собственный output. Старые попытки сохраняются; новый календарь или источник требует отдельного набора. Источник/публикуемая величина, вычисленная дата, сценарное допущение и UNKNOWN различаются.

| Gate | Свидетельство | Предел |
|---|---|---|
| Bytes/lineage |Git hashes, размеры, source copies, component ID | Не истинность рынка |
| Source cells/grain |Сверка исходных ячеек/единиц/периода и1:1ключей | Не текущий catchment/OD |
| Calendar/physical |UTC/local/day offset, все плечи/замыкание, одинаковый C01 legset | Только источник или явно названный сценарий; не tail/crew clearance |
| Conservation |Один fare/journey; кресло на каждом leg; один customer/return cohort | Примеры не распределяют реальный совместный спрос |
| Conditional money |Общий baseline, одна отмена общих расходов, полный остаточный разрыв, q−1проверка | При постоянном заданном gap; не прибыль/прогноз |
| Real product/launch |OD/netfare/кресла/продажи/tail/операционные и денежные данные | UNKNOWN до этих данных; schema/hash PASS не заменяет их |

Минимальные рабочие правила интеграции: использовать safe core overlay/quarantine; не брать legacy alias как fallback; сохранять компонентный input-set и window membership; различать publisher association и legal operating/marketing ID; не превращать плановое расписание в выполненный рейс; не перемножать bed-day tariff на nights без billing rule; не переносить пригородный образец на непокрытую дату.

Реальный денежный тест должен распределить затраты по конкретному outward/return cohort и всем физическим плечам, сравнить с сохранением/заменой/отменой реального baseline, проверить остаточные кресла после иных продуктов и цену вытеснения. Сценарные passcounts не вероятности и не доверительный интервал. При UNKNOWN donor/base/free fleet нет принятого сравнения стратегий.
