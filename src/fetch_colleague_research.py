"""Таблицы из исследований коллег для панели: берёт файлы из закреплённых коммитов git и кладёт в data/external/colleagues/.

Каждый файл — точная копия или выборка из коммита; откуда взят, записано в research_manifest.json.
Запуск: py -3.13 src/fetch_colleague_research.py   (нужны локальные объекты git: git fetch без pull)
"""
import io
import json
import re
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "external" / "colleagues"

# коммит → путь; коммиты закреплены, чтобы панель не менялась от новых правок в чужих ветках
SRC = {
    "week": ("ffcc78d", "context/30_defense_research_20261111/model_schedule/proposed_initial_flights.csv"),
    "connections": ("ffcc78d", "context/30_defense_research_20261111/model_schedule/connection_checks.csv"),
    "five_city": ("e2bd5db", "context/33_five_city_reassessment_20261112/common_economics/report.md"),
    "p09": ("b16c28c", "context/35_full_programme_execution_20261112/P09/scenario_results.csv"),
    "p10_prod": ("b16c28c", "context/35_full_programme_execution_20261112/P10/type_productivity.csv"),
    "p10_thr": ("b16c28c", "context/35_full_programme_execution_20261112/P10/threshold_scenarios.csv"),
    # прямые рейсы из Екатеринбурга, февраль 2027 (ветка research/direct-growth-delay-cargo-20261112)
    "p34_controls": ("4b8dc86", "context/34_new_direct_top5_20261112/final/CONTROLS.csv"),
    "p36_results": ("4b8dc86", "context/36_overnight_chain_search_20261112/RESULTS.md"),
}

# коды контрольных программ P34 → подписи для панели
P34_LABEL = {"KEEP": "Оставить расписание", "CANCEL_TUE_KEEP_FRI": "Снять один старый рейс", "CANCEL_BOTH": "Снять оба старых рейса",
             "AER1": "Челнок в Сочи: 1 оборот в неделю", "AER2": "Челнок в Сочи: 2 оборота в неделю",
             "TRI:SVX-AER-MRV": "Треугольник Екатеринбург — Сочи — Минводы"}


def show(sha, path):
    return subprocess.run(["git", "show", f"{sha}:{path}"], cwd=ROOT, capture_output=True, check=True).stdout.decode("utf-8")


def five_city_table(md):
    """Таблица «Авторский продукт 8–12 программ, базовый спрос»: вклад сети при бюджете 2–7 самолётов."""
    part = md.split("### Авторский продукт 8–12 программ, базовый спрос", 1)[1]
    rows = [l for l in part.splitlines() if l.startswith("|") and "---" not in l and "Сеть" not in l]
    out = []
    for l in rows:
        c = [x.strip() for x in l.strip("|").split("|")]
        if len(c) != 7:
            break
        for b, v in zip(range(2, 8), c[1:]):
            out.append({"network": c[0], "aircraft_budget": b,
                        "result_mln_year": None if v == "NF" else float(v.replace(" ", "").replace(",", "."))})
    return pd.DataFrame(out)


def md_table(md, head):
    """Строки markdown-таблицы, у которой первая колонка заголовка равна head."""
    lines = md.splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith("|") and l.strip("|").split("|")[0].strip() == head)
    rows = []
    for l in lines[i + 2:]:
        if not l.startswith("|"):
            break
        rows.append([x.strip() for x in l.strip().strip("|").split("|")])
    return rows


def num(v):
    return float(v.replace("−", "-").replace("+", "").replace(" ", "").replace(",", "."))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    man = {}
    wk = pd.read_csv(io.StringIO(show(*SRC["week"])))
    wk.to_csv(OUT / "oms_ramp_week_flights.csv", index=False, encoding="utf-8")
    cn = pd.read_csv(io.StringIO(show(*SRC["connections"])))
    cn.to_csv(OUT / "oms_ramp_connections.csv", index=False, encoding="utf-8")
    fc = five_city_table(show(*SRC["five_city"]))
    fc.to_csv(OUT / "five_city_budget.csv", index=False, encoding="utf-8")
    p9 = pd.read_csv(io.StringIO(show(*SRC["p09"])))
    p9 = p9[(p9.delivery == "phased") & (p9.response == "passive") & p9.scenario.isin(["base", "cautious"])
            & p9.status.str.startswith("CONDITIONAL")]
    p9[["programme_id", "label", "scenario", "delta_journeys", "delta_revenue_net", "delta_known_operating_subtotal",
        "unique_pairs_end2028"]].to_csv(OUT / "p09_programmes.csv", index=False, encoding="utf-8")
    pd.read_csv(io.StringIO(show(*SRC["p10_prod"]))).to_csv(OUT / "p10_type_productivity.csv", index=False, encoding="utf-8")
    pd.read_csv(io.StringIO(show(*SRC["p10_thr"]))).to_csv(OUT / "p10_threshold_scenarios.csv", index=False, encoding="utf-8")
    ct = pd.read_csv(io.StringIO(show(*SRC["p34_controls"])))
    ct = ct[ct.adjacent_case == "P05_ADJACENT_PRIOR"]
    ct = pd.DataFrame({"programme": ct.programme, "label": ct.programme.map(P34_LABEL), "scenario": ct.scenario,
                       "delta_vs_keep_mln_month": (ct.known_P_minus_KEEP_month / 1e6).round(3)})
    ct.to_csv(OUT / "p34_triangle_shuttle_controls.csv", index=False, encoding="utf-8")
    md = show(*SRC["p36_results"])
    pairs = [{"rank": int(r[0]), "pair": r[1], "path": r[2], "base_mln_month": num(r[3]), "cautious_mln_month": num(r[4]), "competitor": r[5]}
             for r in md_table(md, "Место в основном сценарии")]
    pd.DataFrame(pairs).to_csv(OUT / "p36_new_pairs.csv", index=False, encoding="utf-8")
    prog = [{"programme": r[0], "scenario": "base" if r[1] == "Базовый" else "cautious", "keep": num(r[2]), "same_without_new": num(r[3]),
             "replace": num(r[4]), "new_flights_only": num(r[5])} for r in md_table(md, "Программа") if len(r) == 6]
    pd.DataFrame(prog).to_csv(OUT / "p36_programmes.csv", index=False, encoding="utf-8")
    for k, (sha, path) in SRC.items():
        man[k] = {"commit": sha, "path": path}
    (OUT / "research_manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    print("ok", len(wk), "рейсов недели;", len(fc), "строк пяти городов;", len(p9), "программ P09;", len(ct), "контролей P34;", len(pairs), "пар и", len(prog), "программ P36")


if __name__ == "__main__":
    main()
