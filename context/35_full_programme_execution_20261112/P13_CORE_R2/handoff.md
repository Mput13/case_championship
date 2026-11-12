# Перепроверка F01-R1

**APPROVE** для exact subject `b51a47cf93cc01ca899d18d2ef94d9340261963f`, P06-1.0.2-adaptive. Остаточный `P13_CORE_RECHECK/F01-R1` закрыт в проверенном scope; новых findings нет.

Лично выполнено **41 PASS, 0 FAIL**. Все три frozen residual-входа теперь получают ContractError по historical derived accruals/cash. Оба будущих изменения внутри месяца допускаются. Прошлые derived cash/customer advance, исходные три reproducer, B21 и I03 сохраняют ожидаемое поведение. Fixed evaluate/compare/scenario совпали с заново исполненными 982f13d и bb378f1, исключён только engine_version. Все 176 payload трёх pinned manifest проверены по hashes/bytes и покрытию tree.

Датированная граница — строго раньше дня решения; сам день не заморожен. Monthly-only guard берёт первое число. Fallback generated revenue на первое плечо проверен напрямую на точных AST-узлах. Публичный API требует departure_date и отклоняет его отсутствие до этой ветви: это ограничение покрытия, не новая поддержка входа без даты.

Авторские 11 regression / 42 suite / 3 CLI/API + invalid-manifest — отдельные свидетельства автора; они не переобъявлены моей независимой приёмкой. Синтетические проверки не RW forecast. Рынок, полный KEEP, новые договорные gates и транзакционная отмена/возврат вне scope.

Воспроизведение из корня репозитория:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 context/35_full_programme_execution_20261112/P13_CORE_R2/reproduce.py
PYTHONDONTWRITEBYTECODE=1 python3 context/35_full_programme_execution_20261112/P13_CORE_R2/assemble.py
```

Результаты: review.json, results.json, coverage.csv, coverage_and_limits.md. Exact входы и подробные adaptive/fixed diagnostics сохранены в inputs/ и results/. Source pins: source_verification.json, read_set.json, source_inspection.md. Все payload перечислены с SHA256/bytes в output_manifest.json; manifest исключает только себя.

Запись ограничена P13_CORE_R2. Subject и frozen reviews не изменялись; Git mutations, дети, установки, внешние/платные вызовы, публикации и перезапуски не выполнялись.
