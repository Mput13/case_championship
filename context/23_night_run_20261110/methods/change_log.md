# Изменения пакетов

| Версия | Изменение | Влияние | Следующая проверка |
|---|---|---|---|
| `344f4425...` | Первая спецификация, inventory, decisions/requests, pinned numerical examples | Разведены единицы/периоды/ресурс, подтверждены арифметические примеры | Независимый MR05 по exact SHA |
| methods-budget-v2 | 8 оптимистичных верхних границ и 224 сертификата; тариф/затраты, donor/cash | При cautious inputs одного роста спроса недостаточно в четырёх фиксированных сетях; full budget остаётся UNKNOWN | Новый независимый review отдельно от MR05 |
| methods-budget-v2 | 20/18 переименованы в модельные endpoint-пары с MOW | Числа те же; operating airport routes больше не подразумеваются | Связать с датированными airport legs только через явный adapter |
| methods-budget-v2 | Screening review `6a038b9b...` принят отдельным input set | Приёмка арифметики повышена только в scope reviewer; основной радиус всё ещё OPEN_DECISION | Не выбирать радиус по суммам scores разных наборов |

## methods-common-v3

Добавлен общий опыт изменения только рецепта спроса на context21; исходные авторские и budgetv1 результаты сохранены. Новые manifests фиксируют четыре переданных пакета. MR05 original verdict CHANGES сохранён; current-label closure не распространяется на новые выводы. В160строках затрат нового адаптера квалифицированы отсутствующие metadata, суммы не менялись.

## methods-strategy-v4

Отдельные mixed/resource/product bridges; исходные commonv3 и budgetv2 runs неизменны. Подключены новые exact reviews с сохранением scopes; primarylineage parentcorrection не стала independent/source acceptance. MR02timebaseP2 удержан до отдельного исправления. Манифест теперь включает вложенные output_manifest.json как обычные входы; исключается только собственный корневой manifest.
