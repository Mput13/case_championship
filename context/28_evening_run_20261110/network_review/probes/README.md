# Воспроизведение ревью

Subject: `b47118a48b6d5480217077bf8699a63665c0eb7a`.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python3 context/28_evening_run_20261110/network_review/probes/review.py
```

Нужен уже установленный Python с numpy/scipy и локальные Git objects закреплённых входов. Зависимости не устанавливаются. Скрипт извлекает только subject `network/` в `probes/.runtime/`, выполняет owner `run_all.py`, затем независимые проверки и удаляет runtime. `--keep-runtime` оставляет его для разбора. Записи ограничены `network_review/`; owner/raw в рабочем дереве не меняются.

`owner_replay.log` — воспроизведённые 101 авторских проверки; это отдельная supplied-design проверка, не независимый allocator. `results.json` — 1006 собственных checks, включая pin/file/calendar identities. Число проверок не является оценкой качества стратегии.

Независимые численные проверки:

- OD/capture/fare/cost из raw pinned CSV, distance через сферическую косинусную формулу.
- Перебор вершин трёхмерной LP: C01, C07, C33; capacities общие у locals/through.
- Собственный packing simplex с primal/dual certificate для банков. Повторная направленная постановка проверяет фактор 2 и общие кресла каждого направления.
- 126 edge/adversarial случаев сравнивают owner LP, vertex oracle и simplex. Seed `47118`; отрицательные маржи, нулевые ёмкости/пулы, вытеснение, равные стоимости и binding capacity.
- Состояния C33 сохраняют остаток занятых мест и его неизменную маржу; численный свидетель допускает равное распределение по двум датам в каждом направлении. Это условие сценария, не PNR evidence.
- Все 14 bridge rows и одинаковые коммерческие рейсы KUF4/deployment; отдельная чувствительность bank capacity 100% фиксирует границу planning LF.
- Все 146 labelled alternative rows, UTC/local/date/block, tail continuity/turns, 1/1/2 OMS positions, MCT и следующие окна C07/C33. Только выбранные 8 published C33 IDs/clocks, без повторного полного source audit.

Поле `details` содержит собственные оптимумы, решения и dual prices. Журнал каждой проверки находится в `checks`. Runtime не входит в доказательные артефакты. `subject_manifest.json` содержит все 120 Git blobs scope; `review_manifest.json` фиксирует уже файлы ревью.

Расхождения с subject в окончательном проходе: нет. Manifest timestamp не сравнивается побайтно; остальные 50 файлов v2 совпадают. Настоящие остатки, protected booking, actual fleet/crew, supported joint-fare budget, cash и будущая годовая экономика не проверялись.
