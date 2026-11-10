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

## methods-integration-v5

Cost-timebase correction87ee импортирована отдельно; задержкиHOLD не включены как доступные деньги. C-overlay и C/Ninteraction имеют разныеcontracts/runs. Добавлен portfolioDguard: текущие30deltas0, synthetic400→300. common_demand.simulate получил явный флагDguard, default84cases/151regionsbyteunchanged. Portfolio calendar row order deterministic in separate replay directory; oldv1bytesunchanged. Current acceptance matrix различает original CHANGES и corrected parentchecks.

- v6: новые allocation/final_variant contracts и расчёты; методы исходного local-first и historical runs не изменены. Добавлены exactMR09/MR10/frontier inputs и admission_v2. Границы полного бюджета/доноров/cash собраны в decision_conditions.md.

- v7: sourceC/local-first finite budget domains,58-row semantic projection and cohesive model_comparison.md; отдельные admission_v3 иFRONTIER_REVIEW58a. v6allocation/currentalpha ивсеhistorical inputs/runs сохранены.

- v8: отдельный admission guard наexactf7a,MR11oracle,MR12two-prose-roundingfix,passport46fdcurrentqualification projection. Всеoldnumericruns/inputs неизменны;admission_v4 новое событие.

- v9: exactMR13e4a receipt,admission_v5 икомпактныйhandoff; numericoutputs unchanged. Приоритет толькоremaining reviews/materialfixes/freeze.
