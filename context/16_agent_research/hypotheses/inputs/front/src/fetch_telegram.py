"""Скачивает публичную ленту Telegram-канала (t.me/s/<канал>) и дописывает новые посты.

Первый запуск качает всё начиная с --since; следующие — только посты новее уже сохранённых
(инкрементально), поэтому ежедневное обновление занимает секунды.

Выход: data/raw/telegram/<канал>.csv (id, dt_utc, dt_msk, text); для favt_info — data/raw/favt_posts.csv
Запуск: python src/fetch_telegram.py favt_info --since 2024-11-01
        python src/fetch_telegram.py airportkazan            (последние 90 дней при первом запуске)
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
UA = "Mozilla/5.0 (case-champ research script)"
MSK = timezone(timedelta(hours=3))
TEXT_RE = re.compile(r'tgme_widget_message_text[^>]*>(.*?)</div>', re.S)
DT_RE = re.compile(r'datetime="([^"]+)"')
FIELDS = ["id", "dt_utc", "dt_msk", "text"]


def out_path(channel):
    if channel == "favt_info":
        return ROOT / "data" / "raw" / "favt_posts.csv"
    return ROOT / "data" / "raw" / "telegram" / f"{channel}.csv"


def fetch(channel, before=None):
    url = f"https://t.me/s/{channel}" + (f"?before={before}" if before else "")
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            print(f"  повтор {attempt + 1}: {e}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"не удалось скачать {url}")


def parse(page, channel):
    rows = []
    post_re = re.compile(rf'data-post="{re.escape(channel)}/(\d+)"(.*?)(?=data-post="|\Z)', re.S | re.I)
    for pid, body in post_re.findall(page):
        dt = DT_RE.search(body)
        if not dt:
            continue
        tx = TEXT_RE.search(body)
        text = html.unescape(re.sub(r"<br\s*/?>", "\n", tx.group(1))) if tx else ""
        text = re.sub(r"<[^>]+>", "", text).strip()
        utc = datetime.fromisoformat(dt.group(1))
        rows.append({"id": int(pid), "dt_utc": utc.isoformat(),
                     "dt_msk": utc.astimezone(MSK).isoformat(), "text": text})
    return rows


def load(path):
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as f:
        return {int(r["id"]): r for r in csv.DictReader(f)}


def update(channel, since=None, pause=1.0):
    """Дописывает новые посты. Возвращает (всего, новых)."""
    path = out_path(channel)
    posts = load(path)
    known_max = max(posts) if posts else 0
    if since is None:
        since = datetime.now(MSK) - timedelta(days=90)
    before, new = None, 0
    while True:
        rows = parse(fetch(channel, before), channel)
        if not rows:
            break
        for r in rows:
            if r["id"] not in posts:
                new += 1
            posts[r["id"]] = r
        oldest = min(r["id"] for r in rows)
        oldest_dt = datetime.fromisoformat(min(rows, key=lambda r: r["id"])["dt_msk"])
        if oldest <= known_max or oldest_dt < since or oldest <= 1 or oldest == before:
            break
        before = oldest
        time.sleep(pause)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for pid in sorted(posts):
            w.writerow({k: posts[pid][k] for k in FIELDS})
    return len(posts), new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("channel")
    ap.add_argument("--since", help="самая ранняя дата (МСК), YYYY-MM-DD; по умолчанию 90 дней назад")
    a = ap.parse_args()
    since = datetime.fromisoformat(a.since).replace(tzinfo=MSK) if a.since else None
    total, new = update(a.channel, since)
    print(f"{a.channel}: всего {total}, новых {new} → {out_path(a.channel)}")


if __name__ == "__main__":
    main()
