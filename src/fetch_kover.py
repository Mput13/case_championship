"""Канал Росавиации t.me/s/favt_info → data/raw/favt_posts.csv (обёртка над fetch_telegram.py).

Готовой таблицы «дней с ограничениями» по аэропортам нет; Meduza (03.07.2026) считала дни
по данным Росавиации. Мы повторяем этот метод по первоисточнику.
Запуск: python src/fetch_kover.py --since 2024-11-01   (первый раз ~25 мин, дальше — только новые посты)
"""
import argparse
from datetime import datetime

from fetch_telegram import MSK, update

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2024-11-01")
    ap.add_argument("--rebuild", action="store_true", help="скачать всю ленту заново (после смены парсера)")
    a = ap.parse_args()
    total, new = update("favt_info", datetime.fromisoformat(a.since).replace(tzinfo=MSK), rebuild=a.rebuild)
    print(f"favt_info: всего {total}, новых {new}")
