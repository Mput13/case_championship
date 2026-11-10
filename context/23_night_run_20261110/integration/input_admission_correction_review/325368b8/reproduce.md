# Воспроизведение MR15

Из корня этого Git repository:

```sh
python3 -B context/23_night_run_20261110/input_admission_correction_review/verify.py
```

Нужны Python 3 со стандартной библиотекой, Git и уже доступные objects exact commits:

- Subject root: `4a89bf1c04b24224a6a85a6cb9b6ca1cad032ab0`.
- Owner: `7e65c687e12cf45534852a3c47d6a5c8cf7dda07`.
- Original review: `f579eeb888a98554b901afeee628c30a85cc48bf`.
- MR11 oracle: `ea2a9626aef75c121f2da7d778b47edce0d571b7`.
- Guard frozen inputs: `f7a034dc91917cc69c5f8b3a729c3d1c6dfeb5b9`.

Fetch, зависимости, сеть, новые environments и сервисы для replay не нужны. Предметные входы читаются только через exact Git blobs. Проверяющий script создаёт примерно 1.4 MiB входов за один проход внутри `.runtime-*` своей папки и удаляет runtime через `TemporaryDirectory`. Полные репозитории, raw, `.git`, окружения и кеши не копируются.

Сначала проверяются root manifests, MR14 patch, pinned receipt и три independently fetched MR11 blobs. Затем исполняется exact root runner с переназначением только `HERE/REPO` для своих записей. Наконец original/corrected main запускаются отдельно в новых процессах для baseline и каждого из 17 случаев. Выходы предыдущего запуска удаляются перед следующим, отклонённый main обязан не создавать admission outputs.

Ожидаемый итог stdout:

```json
{"status": "PASS", "own_main_cases": 17, "original_bypasses": 9, "corrected_rejections": 17, "baseline_identical": 3, "source_blobs": 33, "runtime_removed": true}
```

`PASS` означает совпадение проверок с ожиданиями, включая воспроизведённые обходы исходного main. Вердикт MR15 и граница закрытия P2 записаны отдельно в `findings.json`. Replay обновляет только source/check/probe/baseline evidence в review scope; документы, subject correction и исторический MR14 не меняются.

Для проверки состава доставленного пакета:

```sh
python3 -B - <<'PY'
import hashlib, json
from pathlib import Path
p = Path('context/23_night_run_20261110/input_admission_correction_review')
m = json.loads((p/'output_manifest.json').read_text())
assert {str(f.relative_to(p)) for f in p.rglob('*') if f.is_file()} == {f['path'] for f in m['files']} | {'output_manifest.json'}
for f in m['files']:
    data = (p/f['path']).read_bytes()
    assert hashlib.sha256(data).hexdigest() == f['sha256']
    assert len(data) == f['bytes']
assert not list(p.glob('.runtime-*'))
print('PASS_OUTPUT_MANIFEST')
PY
```

Output manifest исключает только себя во избежание рекурсивного хеша. Git commit закрепляет весь manifest; итоговый HEAD и remote SHA подтверждаются после push отдельно в сообщении доставки.
