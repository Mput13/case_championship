# Воспроизведение MR11

Из корня репозитория, Python3 со стандартной библиотекой; установка и платные запросы не требуются. Все input SHA закреплены в oracle.py; нужные Git objects уже присутствуют. Source code/data владельца читаются через exact `git show`, рабочие methods-папки не читаются.

```sh
python3 -B context/23_night_run_20261110/methods_integration_review/oracle.py
python3 -B context/23_night_run_20261110/methods_integration_review/probes.py
python3 -B context/23_night_run_20261110/methods_integration_review/verify_package.py
```

Первая команда строит независимые16 cancellation/12 C-ledger/8cash/8threshold/90portfolio и preservation receipts. Вторая повторяет30 owner-файлов в памяти и17 негативных/граничных примеров. Она материализует только шесть небольших JSON в своей `.scratch/owner`, не создаёт процессов/серверов и удаляет этот временный каталог после закрытия файлов. Результаты не включают зависимости, raw, auth или контакты.

Третья команда проверяет output hashes, source Git hashes, формы CSV/JSON, ровно разрешённый write scope относительно root77343 и базовые семантические количества. `--write-manifest` применяется только при сборке собственного пакета; без флага проверка ничего не пишет.

Owner-код выполняется только в probes.py как предмет проверки. Результат oracle.py вычисляется собственными формулами/allocator. Повторяются фиксированные сценарии; независимая приёмка MR10, все исходные модели и настоящие продажи не запускаются.

Публикация собственного пакета:

```sh
git diff --check
git add -- context/23_night_run_20261110/methods_integration_review/
git commit -m "research: independently review MR11 integration v5"
git push -u origin HEAD:refs/heads/research/night-methods-integration-review-20261110
git rev-parse HEAD
git ls-remote --heads origin refs/heads/research/night-methods-integration-review-20261110
```

Delivery receipt записывается отдельным последующим commit и содержит exact SHA уже отправленного payload. SHA финального commit проверяется `ls-remote` после последнего push и сообщается в final; собственный SHA в своё дерево не встраивается. Force/merge/rebase/PR не используются.
