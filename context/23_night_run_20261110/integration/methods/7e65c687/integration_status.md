# Приёмка расчётов и перенос в паспорт

Срез v8 добавляет отдельный допуск закреплённого входа и текущие квалификации для паспортного пакета46fd52db. Денежные и календарные результаты v3–v7 не пересчитаны. Содержательное сопоставление — [model_comparison.md](model_comparison.md), конечные варианты — [decision_conditions.md](decision_conditions.md), условные F/B границы — [budget_choice_readout.md](budget_choice_readout.md). Их исторические статусы читаются вместе с новой [матрицей приёмки](runs/admission_v4/acceptance_matrix.csv).

## Новые независимые результаты

**MR11 ea2a9626 на exact f7a — APPROVE_SCOPED.** Приняты16 C/N cancellation случаев,40 adapter rows с4HOLD,12 C cancellation/8 cash-fixture ledgers,8 burden thresholds и90 портфельных строк с30 D-only branches. Это не фактический cash, observed OD или приёмка изменённых входов. Внешние MR10 correction scopes не поглощены.

**MR12 5e9b4765 на exact ba9f — A/B APPROVE_SCOPED.** Приняты фиксированная постановка распределения и15 конечных модельных объединений в обозначенном scope; новыхP1/P2 нет. P3MR12-O01 исправлен только в прозе: максимум сегментов UFA8/C/base теперь **1786,193 сегмента и542,444 трансферной поездки**, как округление исходных1786.193148851081/542.4439973311994. Разность56,304 сегмента, деньги и вывод не изменены. [Событие исправления](checks/mr12_o01_resolution.json) сохраняет исходный subject и отдельную parent projection1b7f6280. Исторический exact ba9f остаётся доступным в Git.

FRONTIER_REVIEW58a02028 принимает календарные/механические границы exact519998; MR10 4604059a — только f177metadata/value preservation и87eetimebase/gating. Original17b/afadee CHANGES остаются историческими;12 clockholds,4 delayHOLD и UNKNOWN alternative recovery не сняты. MR13 проверяет exact c6ad отдельно; новый input-admission guard v8 не объявлен принятым этим review.

## Допуск фиксированного входа

MR11 показал ограничение старой проверки set coverage: дублированная N-itinerary в изменённом CSV проходит её и искажает два результата UFA4/base. Это не дефект закреплённого f7a — его байты и независимый oracle совпали. Поэтому новый [admit_frozen_interaction.py](admit_frozen_interaction.py) выполняется отдельно **до** повторного использования этой ветви.

Он допускает только четыре точных файла subject f7a:384 unit-scale itinerary rows,84 summary rows, исходные model flights и capacity. Проверка включает:

- точные байты/SHA и полные уникальные itinerary/summary ключи; контекст профиля, source network, input_set, recipe и периода;
- все flight/capacity IDs, концы/связность пути, места каждого плеча, единый направленный D, один тариф и сумму стоимости рейсов;
- сверку12 unit-scale групп по всем денежным/пассажирским составляющим;
-160 affected itinerary rows против **сохранённого независимого oracle MR11**, с отдельным pinned receipt.

[checks.json](runs/input_admission_v1/checks.json) и [mutation_checks.json](runs/input_admission_v1/mutation_checks.json) фиксируют семь отказов: duplicate N, пропуск itinerary, изменённая сумма тарифа, неверный source profile, изменённые байты, несовпадение independent oracle при прежнем ключе, duplicate unit summary. Все порчи сделаны в памяти; frozen CSV не менялись. Новый guard проверен владельцем, его собственный independent review PENDING.

Изменённые данные не получают допуск от того, что соблюдают несколько старых численных тождеств. Нужны новый input_set/manifest, определённый состав ключей, источник/семантика изменённых полей и новая oracle-проверка соответствующего scope. Старый oracle160 строк нельзя считать ожиданием для нового спроса или расписания. Guard не является универсальным валидатором будущих сетей; старый interaction script и его результаты не переписаны.

## Текущие квалификации паспорта

Пакет46fd52db сохранён отдельно:26 требований и33 тезиса со своим cutoff и pending-статусами. [requirement_addendum.csv](runs/passport_methods_v1/requirement_addendum.csv) добавляет16 методических уточнений; [claim_qualifications.csv](runs/passport_methods_v1/claim_qualifications.csv) сохраняет оригинальные формулировки и отдельные текущие предложения. Сам паспортный synthesis ожидает собственной независимой проверки.

Новые события MR10/MR11/frontier заменяют **текущую** квалификацию статуса для соответствующих exact subjects, но не переписывают исторический паспортный C12 «pending». Для S03 предложена точная формулировка: при насыщении всех мест у D_SVX8 остаётся отрицательный вклад под прежними tariff/cost/migration/local-first; это не недостаток спроса после насыщения. Число−449822,70 и прежние UFA thresholds сохранены. Они не перенесены на fixed-offer LP.

Для R11/R13 теперь доступны два совместных набора по12 модельных аэропортовых пар и пять наборов, прошедших только count/resource gates. Требование кейса относится к связям городов; final city/airport mapping, выбранный состав, actual operating calendar, бюджет и решение команды остаются отдельными gates. Прохождение модельного счёта не закрывает весь пункт паспорта.

Коды паспортных тезисов `C01…` и исследовательских гипотез `C01…` относятся к разным пространствам имён. Проекция использует `passport_claim_id`; гипотезы не присоединяются по совпадению короткого ID. Все35 гипотез/32untested остаются в frozen frontier queue.

Финальные незакрытые решения остаются предметными: цель/знаменатель доли, D-recipe и закон захвата, выбранные8–12 связи, одинаковый период/сезонность, именованный donor, действительно добавочные fleet/base/support/launch расходы, cash dates и допустимое recovery. Новые scoped passes подтверждают ограниченные расчёты и не заменяют эти входы или командный выбор.
