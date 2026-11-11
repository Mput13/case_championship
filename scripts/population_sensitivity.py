"""Проверка чувствительности спроса без изменения основной модели.

Данные 2025 года — оценка зон из catchment_extra.csv, включающая подстановки.
Сегментная и O&D модели переобучаются на тех же наблюдениях; после этого
отдельно пересчитывается омский хаб без субсидий. Вся выдача остаётся в
outputs/verification/population_2025 и не используется основной панелью.
С --rail вместо населения используется выборка датированных поездов;
она сохраняется в outputs/verification/rail_spotchecks.
"""
from pathlib import Path
import argparse
import json
import shutil
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import demand_model as dm
import od_model
import demand_compare
import network_model as nm

SOURCE = ROOT / "data" / "processed"
OUT = ROOT / "outputs" / "verification" / "population_2025"


def population_nodes(original_nodes, catchments, extra):
    values = extra.set_index("iata")["catchment_pop_2025"]
    if values.index.has_duplicates:
        raise ValueError("Повторяющиеся аэропорты в оценке населения")
    ids = catchments.iata
    missing = ids[~ids.isin(values.dropna().index)]
    if len(missing):
        raise ValueError(f"Нет оценки населения: {', '.join(missing)}")
    if (values.loc[ids] <= 0).any():
        raise ValueError("Население зоны должно быть положительным")
    n = original_nodes.copy()
    for i in n.index:
        n.loc[i, "pop"] = values.loc[list(dm.MOW)].sum() if i == "MOW" else values.loc[i]
    return n


def main():
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--rail", action="store_true", help="проверка отдельных поездов вместо сценария населения")
    args = parser.parse_args()
    if args.rail:
        OUT = ROOT / "outputs" / "verification" / "rail_spotchecks"
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("catchments.csv", "catchment_extra.csv", "destinations.csv", "longlist.csv"):
        shutil.copy2(SOURCE / name, OUT / name)
    base_nodes = dm.nodes()
    if args.rail:
        original_links = dm.links
        observations = pd.read_csv(ROOT / "data" / "manual" / "rail_schedule_spotchecks.csv")
        if observations.hours.isna().any() or (observations.hours <= 0).any():
            raise ValueError("Время поездки должно быть положительным")
        keys = observations.apply(lambda r: tuple(sorted((r.city_a, r.city_b))), axis=1)
        if keys.duplicated().any():
            raise ValueError("В выборке поездов есть повторяющиеся пары")
        def adjusted_links():
            direct, rail = original_links()
            rail = rail.copy()
            for row in observations.itertuples():
                if (row.city_a, row.city_b) not in rail.index or (row.city_b, row.city_a) not in rail.index:
                    raise ValueError(f"Пара {row.city_a} — {row.city_b} отсутствует в исходном наборе")
                rail.loc[(row.city_a, row.city_b)] = row.hours
                rail.loc[(row.city_b, row.city_a)] = row.hours
            return direct, rail
        dm.links = adjusted_links
        label = "выборочные рейсы поездов 2026"
    else:
        alt_nodes = population_nodes(base_nodes, pd.read_csv(SOURCE / "catchments.csv"),
                                     pd.read_csv(SOURCE / "catchment_extra.csv"))
        dm.nodes = lambda: alt_nodes.copy()
        label = "зоны 2025 с подстановками"
    dm.P = od_model.P = demand_compare.P = nm.P = OUT
    dm.main()
    od_model.main()
    demand_compare.main()
    D = nm.Demand()
    all_nodes = list(D.n.index)
    results = []
    for scen in ("base", "cautious"):
        A = nm.load_assumptions()[scen]
        chosen, r = nm.hub_best("OMS", D, A, A["demand_scen"], all_nodes)
        legs, trans, hours, cost, rev, od_l, od_t, flights, migr, forgone, subs = r
        seg = sum(2 * leg["carried_dir_week"] for leg in legs.values())
        results.append({"scenario": scen, "hub": "OMS", "spokes": chosen,
                        "segments_year": round(seg * A["weeks_per_year"]),
                        "result_mln_year": round((rev-cost) * A["weeks_per_year"] / 1e6, 1),
                        "revenue_mln_year": round(rev * A["weeks_per_year"] / 1e6, 1),
                        "input_scenario": label})
    (OUT / "omsk_hub.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Омский хаб, чувствительность:", json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
