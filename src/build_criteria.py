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

import rules

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
DROP = ROOT / "data" / "criteria"
OUT = P / "criteria.json"
# сведения о хабах и базах конкурентов — data/manual/competitor_hubs.csv (1 — есть, 0 — проверено, что нет)
COMP = pd.read_csv(ROOT / "data/manual/competitor_hubs.csv").set_index("iata")
PAX_UP = pd.read_csv(ROOT / "data/manual/pax_2025_overrides.csv").set_index("iata")
FMTS = {"mln", "days", "km", "int", "yesno", "level", "pct", "num"}


def num(v):
    try:
        f = float(str(v).replace(" ", "").replace(",", "."))
        return None if f != f else f
    except (TypeError, ValueError):
        return None


def txt(v):
    return None if v is None or (isinstance(v, float) and v != v) or str(v).strip() == "" else str(v)


def comp_value(i):
    if i not in COMP.index or pd.isna(COMP.loc[i, "competitor_hub"]):
        return (None, "не установлено", "не проверено")
    r = COMP.loc[i]
    v = float(r.competitor_hub)
    return (v, f"{'да' if v >= 1 else 'нет'}: {r.carrier}" if txt(r.carrier) else ("да" if v >= 1 else "нет"),
            f"{txt(r.evidence) or ''} · {r.source}".strip(" ·"))


def core(ll, w):
    """Основные критерии: значение, подпись и источник для каждого города."""
    vals = {}
    for r in ll.itertuples():
        i = r.iata
        v = {
            "gap_pop": (num(r.gap_pop), None, f"«Если быть точным»: нет прямого рейса и поезда ≤{rules.RAIL_OK_HR:.0f} ч"),
            "last365_days": (num(r.last365_days), None, "Росавиация, t.me/s/favt_info"),
            # неизвестный конкурент — пропуск (fill 0,5), а не «хаба нет» (аудит критика команды, 09.11.2026)
            "competitor_hub": comp_value(i),
            "pax_2025": (num(r.pax_2025), None, txt(r.pax_source_url)),
            "catchment_pop": (num(r.catchment_pop), None, f"города больше 100 тыс. в {rules.CATCH_KM:.0f} км, перепись 2021"),
            "dist_bases_km": (min(num(r.dist_msk_km), num(r.dist_ekb_km)), None,
                              f"Москва {int(r.dist_msk_km)} км · Екатеринбург {int(r.dist_ekb_km)} км"),
            "strategy_region": (num(r.strategy_region), None, f"{r.fed_district} · Урал, ДФО, СКФО, ЮФО"),
            "transfer_zone": (num(r.transfer_zone), None, txt(r.transfer_source)),
            "rostec_link": (num(r.rostec_link), txt(r.rostec_note), txt(r.rostec_source)),
            "catchment_pop_2025": (num(r.catchment_pop_2025), None,
                                   f"все пункты в {rules.CATCH_KM:.0f} км, перепись 2021 × Росстат 2025; без координат "
                                   f"{num(r.pop_coord_imputed_share) or 0:.0%}, коэффициент региона {num(r.pop25_region_factor_share) or 0:.0%}"),
            "wage_2024": (num(r.wage_2024), None, f"Росстат БДМО 2024, охват населения зоны {num(r.wage_pop_coverage) or 0:.0%}"),
            "bad_weather_days": (num(r.bad_weather_days), None,
                                 f"NOAA ISD-Lite 2023–2024, станция {txt(r.weather_station) or '—'}; "
                                 f"мороз {str(num(r.frost_days)).replace('.', ',')} дн., ветер {str(num(r.wind_days)).replace('.', ',')} дн."),
            "transfer_demand_base": (num(r.transfer_demand_base), None,
                                     f"{int(num(r.transfer_pairs) or 0)} пар; крупнейшие: {txt(r.top_pairs) or '—'}"),
            "ssj_mro": (num(r.ssj_mro), None, txt(r.ssj_mro_source)),
            "h24": (num(r.h24), None, txt(r.h24_source)),
            "ssj_ops": (num(r.ssj_ops), None, txt(r.ssj_source)),
            "rw_support": (num(r.rw_support), None, txt(r.rw_support_source)),
        }
        # старое определение населения — справочно для сравнения
        v["catchment_pop"] = (num(r.catchment_pop), None, f"города больше 100 тыс. в {rules.CATCH_KM:.0f} км, перепись 2021")
        if str(r.pax_2025_qualifier).startswith(">"):
            v["pax_2025"] = (v["pax_2025"][0], "≥", v["pax_2025"][2])
        vals[i] = {k: {"v": a, "t": b, "s": c} for k, (a, b, c) in v.items()}
        # диапазоны для слабых значений (аудит коллег, context/22_stage1_audit): в диапазоне мест они
        # считаются неопределёнными; центр — само значение
        lvl = COMP.loc[i, "evidence_level"] if i in COMP.index and "evidence_level" in COMP.columns else None
        if vals[i]["competitor_hub"]["v"] is not None and txt(lvl) and lvl != "первичный источник":
            vals[i]["competitor_hub"].update(lo=0.0, hi=1.0, weak=("Хаб конкурента не указан, но это видно только по Википедии" if vals[i]["competitor_hub"]["v"] < 0.5
                  else "Хаб конкурента указан только в Википедии, первичного подтверждения нет"))
        if vals[i]["ssj_mro"]["v"] is not None and 0 < vals[i]["ssj_mro"]["v"] < 1:
            vals[i]["ssj_mro"].update(lo=0.0, hi=1.0, weak="Вывод косвенный: здесь базируется эксплуатант SSJ, но станция ТО не подтверждена")
        if i in PAX_UP.index and vals[i]["pax_2025"]["v"] is not None:
            vals[i]["pax_2025"].update(lo=vals[i]["pax_2025"]["v"], hi=float(PAX_UP.loc[i, "upper_bound"]),
                                       weak=f"В источнике только «{txt(PAX_UP.loc[i, 'note']).split('«')[-1].rstrip('»')}», точной цифры нет")
        gru = num(getattr(r, "gap_pop_rail_unknown", None)) or 0
        if gru > 0 and vals[i]["gap_pop"]["v"] is not None:
            vals[i]["gap_pop"].update(lo=vals[i]["gap_pop"]["v"] - gru, hi=vals[i]["gap_pop"]["v"],
                                      weak=f"У {gru / 1e6:.2f} млн человек время поезда неизвестно, поэтому «дыра» может быть меньше".replace(".", ",", 1))
    crit = []
    for x in w.itertuples():
        crit.append({"key": x.column, "label": x.criterion, "short": x.short, "dir": x.direction,
                     "weight": float(x.weight), "why": x.why, "fmt": x.fmt, "board": int(x.board),
                     "fill": num(x.fill), "lo": num(getattr(x, "lo", None)), "hi": num(getattr(x, "hi", None)),
                     "group": txt(getattr(x, "group", None)) or "прочее", "status": txt(x.status),
                     "origin": "основной"})
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
                     "fill": None, "lo": num(meta.get("lo")), "hi": num(meta.get("hi")),
                     "group": meta.get("group") or "прочее", "status": "подключаемый", "origin": f.name})
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
