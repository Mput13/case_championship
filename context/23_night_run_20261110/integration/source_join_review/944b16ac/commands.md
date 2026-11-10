# Воспроизведение проверки

Из корня подготовленного checkout; Python 3 и уже имеющийся lxml. Новые зависимости не устанавливать.

```sh
git show --no-patch --format=fuller 17b4f348f15ea8695688d9435933cb4965568408
git show --no-patch --format=fuller abc09bbb8e62d3513749b60b252d4521997acfc3
git show --no-patch --format=fuller 7180bf5e03905a7892b3031f2447c5b33d10e244
PYTHONDONTWRITEBYTECODE=1 python3 context/23_night_run_20261110/source_join_review/independent.py
```

Последняя команда читает exact Git blobs и 22 raw по записанным owner paths и SHA256, пишет только эту папку. Ожидаемый exit **1**: 51 PASS, один предметный FAIL, P2 registry/raw-snapshot mismatch. Отсутствующий raw или несовпадающий хеш прерывает проверку, а не выдаёт PASS.

Точечный P2 repro без raw:

```sh
git show 17b4f348f15ea8695688d9435933cb4965568408:context/23_night_run_20261110/primary_evidence/source_registry.csv
git show 17b4f348f15ea8695688d9435933cb4965568408:context/23_night_run_20261110/primary_evidence/dated_evidence.csv
git show 93fa5cf4a10ab67e05c93d19fc5375fc58ef9299:context/17_aircraft_route_review/evidence/sources.json
```

Сравнить `registry.raw_sha256` и `dated_evidence.html_sha256` для одинаковых `source_id`: svx_schedule и svx_schedule_arr. В stage17 sources.json hashes соответствуют dated rows, в registry стоят более ранние hashes context12.

Доставка выполняется только своей папкой:

```sh
git add -- context/23_night_run_20261110/source_join_review/
git commit -m 'research: independently review pinned source and bridge joins'
git push origin HEAD:refs/heads/research/night-source-join-review-20261110
git ls-remote origin refs/heads/research/night-source-join-review-20261110
```

Без force, merge, rebase и PR. Remote SHA сообщается в завершении; commit не может содержать собственный SHA без рекурсивного изменения. `handoff.json` принадлежит коммиту, указанному в завершении.
