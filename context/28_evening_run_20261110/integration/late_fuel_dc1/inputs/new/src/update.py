"""Одна команда обновления: загрузка источников → проверки → пересчёт → панель.

Порядок как в инструментах дата-инжиниринга (ELT):
  1. extract — по реестру data/sources.toml запускает загрузчики, у которых подошёл срок
               (или все с --force), каждый в отдельном процессе: сбой одного не роняет остальные;
  2. check   — у каждого файла считает строки и SHA-256, сравнивает с прошлым запуском,
               ставит статус ok / warn (данных меньше нужного или файл не обновлялся дольше
               stale_days) / fail (загрузчик упал) / manual (ручной источник);
  3. build   — если что-то изменилось, пересчитывает цепочку скриптов в порядке зависимостей;
  4. scan    — ищет новые цифры в лентах (src/scan_news.py) и кладёт их во «входящие»;
  5. log     — пишет data/raw/_manifest.json (последнее состояние) и data/raw/_runs.csv (история).

Запуск: python src/update.py            (то, что пора обновить)
        python src/update.py --force    (всё)
        python src/update.py --only favt_info
По расписанию: Планировщик заданий Windows или cron раз в сутки.
"""
import argparse
import csv
import hashlib
import json
import subprocess
import sys
import tomllib
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MSK = timezone(timedelta(hours=3))
MANIFEST = ROOT / "data" / "raw" / "_manifest.json"
RUNS = ROOT / "data" / "raw" / "_runs.csv"
# цепочка пересчёта (каждый шаг читает выход предыдущих)
BUILD = ["src/longlist_data.py", "src/kover_days.py", "src/catchment_extra.py",
         "src/demand_model.py", "src/demand_summary.py", "src/od_model.py", "src/demand_compare.py",
         "src/transfer_potential.py",
         "src/build_longlist.py", "src/build_criteria.py", "src/longlist_score.py",
         "src/network_model.py", "src/network_map.py", "src/build_workbook.py",
         "src/scan_news.py", "src/build_dashboard.py"]


def rows_and_hash(p):
    if not p.exists():
        return None, None
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    if p.suffix == ".csv":
        csv.field_size_limit(10**8)
        with p.open(encoding="utf-8", errors="replace", newline="") as f:
            n = sum(1 for _ in csv.reader(f)) - 1   # записи, а не строки файла: в постах есть переносы
    elif p.suffix == ".json":
        n = 0
    else:
        n = None
    return n, h


def run(cmd):
    parts = cmd.split()
    r = subprocess.run([sys.executable, str(ROOT / parts[0]), *parts[1:]], cwd=ROOT / "src",
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--no-build", action="store_true")
    a = ap.parse_args()

    reg = tomllib.loads((ROOT / "data" / "sources.toml").read_text(encoding="utf-8"))
    man = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    now = datetime.now(MSK)
    changed, done_cmds, log = False, {}, []

    for sid, s in reg.items():
        if a.only and sid != a.only:
            continue
        prev = man.get(sid, {})
        last = datetime.fromisoformat(prev["fetched_at"]) if prev.get("fetched_at") else None
        due = a.force or last is None or now - last >= timedelta(days=s["every_days"])
        out = ROOT / s["output"]
        status, msg = "ok", ""
        if s["cmd"] and due:
            if s["cmd"] in done_cmds:            # один загрузчик на несколько источников
                code, tail = done_cmds[s["cmd"]]
            else:
                print(f"→ {sid}: {s['cmd']}", flush=True)
                code, tail = run(s["cmd"])
                done_cmds[s["cmd"]] = (code, tail)
            msg = tail[0][:200]
            if code != 0:
                status = "fail"
            else:
                last = now
        elif not s["cmd"]:
            status = "manual"
        n, h = rows_and_hash(out)
        if out.exists() and not s["cmd"]:
            last = datetime.fromtimestamp(out.stat().st_mtime, MSK)
        if n is None and h is None:
            status = "missing" if status != "fail" else status
        elif status == "ok" and n is not None and n < s["min_rows"]:
            status, msg = "warn", f"строк {n}, ожидалось не меньше {s['min_rows']}"
        if status in ("ok", "manual") and last and now - last > timedelta(days=s["stale_days"]):
            status, msg = "stale", f"не обновлялся {(now - last).days} дн."
        if h and h != prev.get("sha256"):
            changed = True
        man[sid] = {"name": s["name"], "owner": s["owner"], "url": s["url"], "kind": s["kind"],
                    "role": s["role"], "license": s["license"], "feeds": s["feeds"],
                    "status": status, "message": msg, "rows": n, "sha256": h,
                    "prev_rows": prev.get("rows"),
                    "fetched_at": last.isoformat() if last else None, "checked_at": now.isoformat(),
                    "stale_days": s["stale_days"]}
        log.append([now.isoformat(), sid, status, n, msg])
        print(f"  {sid:18} {status:8} строк={n} {msg}")

    MANIFEST.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    new_file = not RUNS.exists()
    with RUNS.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["checked_at", "source", "status", "rows", "message"])
        w.writerows(log)

    if a.no_build or not (changed or a.force):
        print("пересчёт не нужен" if not a.no_build else "пересчёт пропущен")
        return
    for step in BUILD:
        code, tail = run(step)
        print(f"  build {step:26} {'ok' if code == 0 else 'FAIL'} {tail[0][:120]}")
        if code != 0:
            sys.exit(f"пересчёт остановлен на {step}")


if __name__ == "__main__":
    main()
