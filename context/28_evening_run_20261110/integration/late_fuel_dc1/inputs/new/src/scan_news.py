"""Ищет в лентах новые цифры и события и кладёт их во «входящие» на проверку человеком.

Читает все Telegram-источники из data/sources.toml (и role=data, и role=watch), посты за 120 дней.
Ищет:
  pax     — пассажиропоток с числом («обслужил 5,3 млн пассажиров»);
  route   — новые или возобновлённые рейсы;
  subsidy — субсидии;
  base    — хабы и базирование.
Каждая находка: дата, канал, ссылка на пост, тип, найденное число, города, отрывок до 220 знаков.
Автоматически в расчёт ничего не попадает: человек ставит status = принято / отклонено,
принятое переносится в data/manual с ссылкой. Решения при повторном запуске сохраняются.

Выход: data/inbox/candidates.csv
Запуск: python src/scan_news.py
"""
import csv
import re
import tomllib
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "inbox" / "candidates.csv"
MSK = timezone(timedelta(hours=3))
DAYS = 120

PATTERNS = {
    "pax": re.compile(r"(пассажиропот\w*|обслужил\w*|перевез\w*)[^.!?\n]{0,90}?"
                      r"(\d+(?:[.,]\d+)?)\s*(млн|миллион\w*|тыс\.?|тысяч\w*)", re.I),
    "route": re.compile(r"(нов\w+\s+(?:рейс|маршрут|направлени)\w*|откр\w+\s+(?:рейс|продаж|направлени)\w*|"
                        r"запуска\w*\s+рейс\w*|начн\w+\s+(?:выполнять|летать)|возобнов\w+\s+(?:рейс|пол[её]т)\w*)", re.I),
    "subsidy": re.compile(r"субсид\w+", re.I),
    "base": re.compile(r"(\bхаб\w*|базов\w+\s+авиакомпани\w*|базирован\w*)", re.I),
}
# пост берём, только если он про авиацию — иначе находят туризм, автобусы, дороги
AVIA = re.compile(r"рейс|авиа|аэропорт|самол[её]т|перевозчик|авиакомпан|пол[её]т", re.I)
CITIES = ["Москв", "Екатеринбург", "Самар", "Уф", "Казан", "Нижн\\w* Новгород", "Перм", "Челябинск",
          "Тюмен", "Омск", "Минеральн\\w* Вод", "Минвод", "Сочи", "Махачкал", "Калининград", "Саратов",
          "Волгоград", "Оренбург", "Красноярск", "Иркутск", "Владивосток", "Хабаровск", "Барнаул",
          "Новосибирск", "Санкт-Петербург", "Краснодар", "Улан-Удэ"]
CITY_RE = [(c, re.compile(r"(?<![А-Яа-яЁё])" + c, re.I)) for c in CITIES]
FIELDS = ["found_at", "date", "channel", "post_id", "url", "type", "number", "unit", "cities",
          "snippet", "status", "note"]


def snippet(text, m):
    a = max(text.rfind(".", 0, m.start()) + 1, text.rfind("\n", 0, m.start()) + 1, m.start() - 120, 0)
    s = " ".join(text[a:a + 220].split())
    return s + ("…" if len(text) > a + 220 else "")


def main():
    reg = tomllib.loads((ROOT / "data" / "sources.toml").read_text(encoding="utf-8"))
    old = {}
    if OUT.exists():
        with OUT.open(encoding="utf-8", newline="") as f:
            old = {(r["channel"], r["post_id"], r["type"]): r for r in csv.DictReader(f)}
    since = datetime.now(MSK) - timedelta(days=DAYS)
    found = dict(old)
    now = datetime.now(MSK).isoformat(timespec="minutes")
    for sid, s in reg.items():
        if s["kind"] != "telegram":
            continue
        p = ROOT / s["output"]
        if not p.exists():
            continue
        channel = s["url"].rstrip("/").split("/")[-1]
        with p.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                if datetime.fromisoformat(r["dt_msk"]) < since:
                    continue
                text = r["text"] or ""
                if not AVIA.search(text):
                    continue
                for typ, rx in PATTERNS.items():
                    m = rx.search(text)
                    if not m:
                        continue
                    key = (channel, r["id"], typ)
                    if key in found:
                        continue
                    if typ == "pax" and not re.search(r"пассажир", m.group(0), re.I):
                        continue
                    cities = [c.replace("\\w*", "") for c, cr in CITY_RE if cr.search(text)]
                    found[key] = {
                        "found_at": now, "date": r["dt_msk"][:10], "channel": channel, "post_id": r["id"],
                        "url": f"https://t.me/{channel}/{r['id']}", "type": typ,
                        "number": m.group(2) if typ == "pax" else "", "unit": m.group(3) if typ == "pax" else "",
                        "cities": "; ".join(cities[:6]), "snippet": snippet(text, m),
                        "status": "на проверке", "note": "",
                    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(found.values(), key=lambda r: (r["date"], r["channel"]), reverse=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    new = len(found) - len(old)
    by = {}
    for r in rows:
        by[r["type"]] = by.get(r["type"], 0) + 1
    print(f"входящие: всего {len(rows)}, новых {new}, по типам {by}")


if __name__ == "__main__":
    main()
