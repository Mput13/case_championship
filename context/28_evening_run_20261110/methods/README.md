# Вечерняя методика: отбор сети, календарь и бюджет

Первый содержательный срез: воспроизведена новая модель Насти и выполнены отдельные исправления отбора. Исходники и ночной freeze сохранены. Это owner package, независимая проверка нового scope ещё не выполнена.

## Основные результаты

- **Омск без поддержки:** сохранение найденной сети cap4 даёт−186,480 млн RUB вместо−367,062 млн у исходного cap10; улучшение180,582 млн при меньшем часовом ресурсе. Среди пяти рассмотренных хабов base без поддержки этот найденный OMS лучше KUF−282,645 млн. Оба отрицательны до полного бюджета.
- **Direct-shortlist:** состав400 предварительных кандидатов меняется на1/8/1/7 для base/base_sub/cautious/cautious_sub. При cap10 конечные авторские восемь треугольников и их деньги **не изменились**. Сохранение меньших допустимых сетей улучшает direct base до−1317,399 млн, но19 модельных пар не выполняют конечный gate8–12. Отдельная постановка8–12 городских пар даёт base−440,106 млн и base_sub−225,171 млн; это новое ограничение, не денежный эффект одной правки shortlist.
- **Поддержка и календарь:** OMS base_sub остаётся+387,722 млн при модельной поддержке и до неизвестных расходов. Смысл48 недель отделён: без переноса спроса cautious OMS frontier−2420,155 млн против−2385,315 млн при авторской концентрации. Никакого повторного вычета НДС из net yield нет.

384 рассчитанных сети;303 frontier rows;72 проверки авторских опубликованных показателей и3 точных audit money fixtures. [Спецификация](comparison_spec.md), [все кандидаты](runs/selection_v1/all_candidates.csv), [сохранённые допустимые сети](runs/selection_v1/preserved_frontiers.csv), [изменения shortlist](runs/selection_v1/shortlist_changes.csv), [проверки](runs/selection_v1/semantic_checks.json).

Запуск из этого worktree:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 -B context/28_evening_run_20261110/methods/selection_experiment.py
python3 -B context/28_evening_run_20261110/methods/verify_selection.py
python3 context/28_evening_run_20261110/methods/package_manifest.py --check
```

Нужны имеющиеся Python/numpy/pandas; новые зависимости не устанавливались. Public TOCHNO gz взят из exact audit5905; временный распакованный CSV создаётся только в игнорируемом `.runtime/`. Архив и его raw hash сохранены. В author files ничего не записывается.

Ограничения: bounded greedy/candidate search, не global optimum; городские MOW-пары не physical airport assignment; часовой ресурс не dispatch; поддержка не подтверждённый award; рынок, полный бюджет и cash не приняты. Отдельные годовой календарь, парк/KEEP и интеграция десяти гипотез продолжаются в новом окне до22:00.

## Срез v2

[Датированный календарь, ресурс и бюджет](annual_readout.md): четыре основные ветвиN(t), условные годовые деньги и ограничения поддержки/тарифа. Первыйselection_v1 сохранён без изменений; новые scoped reviews не наследуются.


## Общий синтез v4

[Стратегия и десять решений](strategy.md), [таблицы вариантов](strategy/finite_options.csv), [карточки](strategy/hypothesis_decisions.csv). Числа разных периодов не ранжируются вместе; actual market/fleet/fullbudget UNKNOWN. Датированный v3 exact f99 остаётся отдельным subject ревью. Новые таблицы: `python3 -B strategy_tables.py`; source-cell/closed-form/preservation checks: `python3 -B verify_strategy.py`. `budget_components.csv` и `hypothesis_decisions.csv` — курируемые source-based проекции, не новый модельный runtime. Все35 ID сохранены в `strategy/hypothesis_queue35.csv`.
