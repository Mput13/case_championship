# Воспроизведение MR12

Из корня checkout. Нужны Git objects указанных exact commits и уже установленный Python 3.11 / SciPy 1.17.1 / NumPy 2.4.3. Новые зависимости и сеть для расчёта не требуются. Владельческие working folders не читаются.

```sh
git show c43e58569f3fc561bb7d0dd0806995b718ef01a9:context/23_night_run_20261110/contract.md
git show c43e58569f3fc561bb7d0dd0806995b718ef01a9:context/23_night_run_20261110/briefs/allocation_variants_review.md
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 -B context/23_night_run_20261110/allocation_variants_review/reproduce.py
```

Последняя команда заново создаёт независимые numeric tables/certificates/manifests в папке этого review. Издательские report/findings/handoff она не переписывает. Все input reads — `git show exact_commit:path`; полные команды и хэши входов записаны в source_manifest. Независимый расчёт использует собственные коэффициенты и матрицу, проверяет published certificates и строит дополнительные LP/certificates через highs-ds. Затем supplementary owner replay в собственной временной папке воспроизводит 15 outputs и выполняет in-memory refusal probe; временная папка удаляется после завершения subprocesses.

Ожидаемый итог: `PASS_SCOPED`, 16 cases, 48 primary, 32 secondary, 15 unions, 90 budget rows. Проверки и floating-point residuals: independent_checks.json. Published x проверяется по offer, а не принимается по summary. Полные primary/secondary shadows сохранены в соответствующих CSV.

Проверка исходно доставленного пакета без записи:

```sh
python3 -B context/23_night_run_20261110/allocation_variants_review/verify_package.py
```

После осознанного воспроизведения на другом окружении runtime-version metadata и последние floating-point bits могут отличаться. Проверять residuals и смысл результата; не подменять исходный output_manifest. Для подготовки новой версии своего review используется явное `verify_package.py --seal`.

Команды доставки этого scope (без force, merge/rebase и PR):

```sh
git add -- context/23_night_run_20261110/allocation_variants_review
git diff --cached --stat
git commit -m "research: independently review MR12 allocation and finite variants"
git push -u origin research/night-allocation-variants-review-20261110
git rev-parse HEAD
git ls-remote --heads origin refs/heads/research/night-allocation-variants-review-20261110
git status --short
```

Финальная пара HEAD/ls-remote сообщается после push; SHA текущего commit не записывается внутрь себя. Handoff и manifest связывают review с точными prepared/subject commits.
