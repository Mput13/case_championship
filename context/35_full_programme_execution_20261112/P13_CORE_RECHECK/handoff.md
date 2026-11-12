# Перепроверка P06 adaptive

**CHANGES** на exact `bb378f1e8bd3c621e83ccf50086f9ce15c6bb9ec`, manifest `74b37e90d6221957e56e26e559b85d07bc58e3138458354c51db9fda568b67b1` (101 payload), P06-1.0.1-adaptive. Frozen P13_CORE проверен и не изменён.

Исходные 3 воспроизводителя отклонены; F02 закрыт в проверенном scope. F01 закрыт частично: **S2 F01-R1**, `P06/engine/core.py:306–307`. Отбор `accrual_month < decision[:7]` пропускает уже прошлые начисления месяца решения. Минимальный input: `inputs/derived_same_month_dated_accrual_indirect.json`. Решение 15.02 меняет длительность рейса 10.03; неизменённое начисление с accrual_date 10.02 меняется 20→30 RUB и принимается как CONDITIONAL. Expected: ContractError. Две дополнительные формы — monthly-only accrual и выручка выполненного 10.02 рейса (6000→4000 RUB) после добавления будущей альтернативы 20.02.

Минимальная правка: отбирать прошлые derived accruals по полной доступной дате, сохраняя консервативный monthly fallback; для generated journey revenue использовать дату продукта/первого плеча. Положительные действия 20.02 при решении 15.02 должны оставаться допустимыми.

28 проверок: **25 PASS, 3 FAIL одного S2**. B21 и I03 PASS; прошлые производные cash и аванс защищены; fixed evaluate/compare/scenario совпали с base после исключения только engine_version. Рыночная калибровка, полный KEEP и реальные договоры не были gates этого review. Код/inputs/results, coverage и hashes: review.json, recheck.py, coverage_and_limits.md, output_manifest.json.
