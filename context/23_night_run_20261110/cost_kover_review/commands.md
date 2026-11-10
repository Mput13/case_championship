# Воспроизведение проверки

Рабочий каталог — root репозитория, содержащий Git objects exact inputs. Python 3, стандартная библиотека. Новых зависимостей и окружений нет. Скрипты пишут только в свою папку, не запускают author main/selector, self-checks автора, сеть или чужие программы.

```sh
python3 -B context/23_night_run_20261110/cost_kover_review/review.py
python3 -B context/23_night_run_20261110/cost_kover_review/primary_review.py
python3 -B context/23_night_run_20261110/cost_kover_review/finalize.py
```

Ожидается `review=CHANGES`, 8 baseline, 40 combinations, 24 probes (22 PASS и два воспроизведения одного P2), 117 параметров, 16 выбранных KHV строк и два совпавших raw hash. CHANGES здесь — успешное обнаружение дефекта в закреплённом объекте проверки. Нулевой exit code означает исполнение ревью, а не PASS оригинала.

`primary_review.py` читает два raw PDF только из разрешённой owner-папки:

`/Users/a/.t3/worktrees/case_championship/t3-6b143a3b-f769e5714dcb4e77/context/23_night_run_20261110/cost_kover/raw_hold/`.

Полные raw не копируются и в Git не включены. На другом checkout отсутствие этих локальных raw означает **NOT_RUN** для первичного повторения; ранее зафиксированная личная проверка остаётся в receipt, но новый запуск её не совершил. Не подменять оригинал свежей загрузкой по тому же URL без сверки SHA256.

Для повторного локального рендера тех же raw используются установленный Poppler и команда:

```sh
python3 -B context/23_night_run_20261110/cost_kover_review/primary_review.py --render
```

Она создаёт только `.local/*_page1.png`, `*_page7.png` и соответствующий text под своей папкой. В Git они исключены. Нужно лично открыть рендеры и прочитать выбранные строки страницы 1, единицы/индивидуальные даты и примечание о НДС страницы 7; программное совпадение значений не заменяет чтение. В этом review такие четыре рендера были прочитаны лично. Нового primary GET не было.

Каждый исходник основного review читается командой вида:

```sh
git show afadee35ebeefe54a05bdfc5b3e224a370f90e0a:context/23_night_run_20261110/cost_kover/overlay.py
git show 553e63a5de32cff941fde3ca28175f242f28375c:context/23_night_run_20261110/cost_kover/output_manifest.json
git show 93fa5cf4a10ab67e05c93d19fc5375fc58ef9299:scripts/build_team_comparison.py
```

`source_manifest.json` хранит полные SHA, пути, размеры и hashes всех прочитанных Git inputs. `.local` не участвует в публикационном manifest; первичные факты, raw/render hashes и recipe сохранены отдельно. `output_manifest.json` исключает себя и delivery metadata для отсутствия циклических hashes.

Проверка scope и remote после публикации:

```sh
git diff --name-only f1774e1f66a9483fb618ca6003abd9dc4d8563e1 HEAD
git ls-remote --heads origin research/night-cost-kover-review-20261110
```

Первый список должен содержать только `context/23_night_run_20261110/cost_kover_review/`. Remote SHA сверяется с `remote_receipt.json` и финальным handoff; точный SHA не записывается внутрь собственного commit. Отдельный metadata commit хранит remote receipt ранее опубликованного payload, а финальный delivery SHA сообщается по завершении.

В ходе разработки reviewer script дважды завершался до завершения probes: исправлены предположение о наличии `id` во всех source manifests (`reference_input_manifest` использует `local_path`) и выбор узкого окна без пересадочной продажи. Эти ошибки относились к новому reviewer script, не к MR02. Полный конечный запуск после исправлений завершён; результаты ранних неполных запусков не использованы как приёмка.
