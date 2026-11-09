"""Собирает единый список критериев лонглиста: что за критерий, его вес и значение у каждого города.

Два источника критериев:
  1. Основные — строки data/assumptions/longlist_weights.csv, значения из data/processed/longlist.csv.
  2. Подключаемые — любой файл data/criteria/<ключ>.csv (см. data/criteria/README.md).
     Положил файл — критерий появился в расчёте, на пульте весов, на табло и в талоне.
     Код править не нужно.

Пропуски: у основных критериев правило в колонке fill (подставить сырое значение);
у подключаемых пропуск = нейтральная оценка 0,5 и пометка «нет данных».

Выход: data/processed/criteria.json — его читают src/longlist_score.py и панель.
Запуск: python src/build_criteria.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
DROP = ROOT / "data" / "criteria"
OUT = P / "criteria.json"
COMPETITOR_HUB = {"KJA": "группа «Аэрофлот» — хаб (аэропорт, итоги 2025)",
                  "IKT": "S7 — хаб (сайт S7)", "VVO": "«Аврора» и S7 — базовые (аэропорт, итоги 2025)"}
FMTS = {"mln", "days", "km", "int", "yesno", "level", "pct", "num"}


def num(v):
    try:
        f = float(str(v).replace(" ", "").replace(",", "."))
        return None if f != f else f
    except (TypeError, ValueError):
        return None


def txt(v):
    return None if v is None or (isinstance(v, float) and v != v) or str(v).strip() == "" else str(v)


def core(ll, w):
    """Основные критерии: значение, подпись и источник для каждого города."""
    vals = {}
    for r in ll.itertuples():
        i = r.iata
        v = {
            "gap_pop": (num(r.gap_pop), None, "«Если быть точным»: нет прямого рейса и поезда ≤12 ч"),
            "last365_days": (num(r.last365_days), None, "Росавиация, t.me/s/favt_info"),
            "competitor_hub": (1.0 if i in COMPETITOR_HUB else 0.0, "да" if i in COMPETITOR_HUB else "не найден",
                               COMPETITOR_HUB.get(i, "доля перевозчиков появится после ключа Яндекса")),
            "pax_2025": (num(r.pax_2025), None, txt(r.pax_source_url)),
            "catchment_pop": (num(r.catchment_pop), None, "города больше 100 тыс. в 75 км, перепись 2021"),
            "dist_bases_km": (min(num(r.dist_msk_km), num(r.dist_ekb_km)), None,
                              f"Москва {int(r.dist_msk_km)} км · Екатеринбург {int(r.dist_ekb_km)} км"),
            "strategy_region": (num(r.strategy_region), None, f"{r.fed_district} · Урал, ДФО, СКФО, ЮФО"),
            "transfer_zone": (num(r.transfer_zone), None, txt(r.transfer_source)),
            "rostec_link": (num(r.rostec_link), txt(r.rostec_note), txt(r.rostec_source)),
        }
        if str(r.pax_2025_qualifier).startswith(">"):
            v["pax_2025"] = (v["pax_2025"][0], "≥", v["pax_2025"][2])
        vals[i] = {k: {"v": a, "t": b, "s": c} for k, (a, b, c) in v.items()}
    crit = []
    for x in w.itertuples():
        crit.append({"key": x.column, "label": x.criterion, "short": x.short, "dir": x.direction,
                     "weight": float(x.weight), "why": x.why, "fmt": x.fmt, "board": int(x.board),
                     "fill": num(x.fill), "origin": "основной"})
    return crit, vals


def dropins(known, weights):
    """Подключаемые критерии из data/criteria/*.csv."""
    crit, vals = [], {}
    if not DROP.exists():
        return crit, vals
    for f in sorted(DROP.glob("*.csv")):
        key = f.stem
        if key in known:
            print(f"пропущен {f.name}: ключ {key} уже есть среди основных")
            continue
        d = pd.read_csv(f, dtype=str).fillna("")
        need = {"iata", "value"}
        if not need <= set(d.columns):
            print(f"пропущен {f.name}: нужны колонки iata и value")
            continue
        meta = d.iloc[0].to_dict()
        fmt = meta.get("fmt") or "num"
        w = weights.get(key, num(meta.get("weight")) or 0.0)
        b = num(meta.get("board"))
        crit.append({"key": key, "label": meta.get("label") or key, "short": meta.get("short") or meta.get("label") or key,
                     "dir": meta.get("direction") or "+", "weight": w, "why": meta.get("why") or "",
                     "fmt": fmt if fmt in FMTS else "num", "board": 1 if b is None else int(b),
                     "fill": None, "origin": f.name})
        for r in d.itertuples():
            vals.setdefault(r.iata.strip().upper(), {})[key] = {
                "v": num(r.value), "t": txt(getattr(r, "text", "")), "s": txt(getattr(r, "source", ""))}
        print(f"подключён критерий {key} из {f.name}: {sum(1 for r in d.itertuples() if num(r.value) is not None)} значений")
    return crit, vals


def main():
    ll = pd.read_csv(P / "longlist.csv")
    w = pd.read_csv(ROOT / "data/assumptions/longlist_weights.csv")
    crit, vals = core(ll, w)
    known = {c["key"] for c in crit}
    extra_w = {}
    crit2, vals2 = dropins(known, extra_w)
    crit += crit2
    for i in vals:
        vals[i].update(vals2.get(i, {}))
        for c in crit2:
            vals[i].setdefault(c["key"], {"v": None, "t": None, "s": None})
    OUT.write_text(json.dumps({"criteria": crit, "values": vals}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"критериев: {len(crit)} ({len(crit2)} подключаемых) → {OUT}")


if __name__ == "__main__":
    main()
