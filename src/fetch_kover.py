"""Скачивает публичную ленту Росавиации t.me/s/favt_info и сохраняет все посты.

Зачем: готовой таблицы «дней с ограничениями (Ковёр)» по всем аэропортам нет.
Meduza (03.07.2026) считала дни по данным Росавиации; мы повторяем этот метод
по первоисточнику — каналу Росавиации, где публикуется каждое введение ограничений.

Выход: data/raw/favt_posts.csv (id, дата UTC, дата МСК, текст поста).
Запуск: python src/fetch_kover.py            (вся лента, ~10 мин)
        python src/fetch_kover.py --since 2025-01-01
"""
import argparse
import csv
import html
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "favt_posts.csv"
URL = "https://t.me/s/favt_info"
UA = "Mozilla/5.0 (case-champ research script)"
MSK = timezone(timedelta(hours=3))

POST_RE = re.compile(r'data-post="favt_info/(\d+)"(.*?)(?=data-post="favt_info/|\Z)', re.S)
TEXT_RE = re.compile(r'tgme_widget_message_text[^>]*>(.*?)</div>', re.S)
DT_RE = re.compile(r'datetime="([^"]+)"')


def fetch(before=None):
    url = URL + (f"?before={before}" if before else "")
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # сеть/лимит — ждём и повторяем
            print(f"  retry {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"не удалось скачать {url}")


def parse(page):
    rows = []
    for pid, body in POST_RE.findall(page):
        dt = DT_RE.search(body)
        tx = TEXT_RE.search(body)
        if not dt:
            continue
        text = html.unescape(re.sub(r"<br\s*/?>", "\n", tx.group(1))) if tx else ""
        text = re.sub(r"<[^>]+>", "", text).strip()
        utc = datetime.fromisoformat(dt.group(1))
        rows.append({"id": int(pid), "dt_utc": utc.isoformat(),
                     "dt_msk": utc.astimezone(MSK).isoformat(), "text": text})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2000-01-01", help="самая ранняя дата (МСК), YYYY-MM-DD")
    args = ap.parse_args()
    since = datetime.fromisoformat(args.since).replace(tzinfo=MSK)

    posts = {}
    before = None
    while True:
        rows = parse(fetch(before))
        if not rows:
            break
        for r in rows:
            posts[r["id"]] = r
        oldest = min(r["id"] for r in rows)
        oldest_dt = datetime.fromisoformat(min(rows, key=lambda r: r["id"])["dt_msk"])
        print(f"до поста {oldest}: {oldest_dt:%Y-%m-%d}, всего {len(posts)}", flush=True)
        if oldest_dt < since or oldest <= 1 or oldest == before:
            break
        before = oldest
        time.sleep(1.0)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "dt_utc", "dt_msk", "text"])
        w.writeheader()
        for pid in sorted(posts):
            if datetime.fromisoformat(posts[pid]["dt_msk"]) >= since:
                w.writerow(posts[pid])
    print(f"сохранено: {OUT}")


if __name__ == "__main__":
    main()
