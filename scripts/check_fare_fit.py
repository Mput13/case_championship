"""Повторить линейный подбор по сценариям коллег и текущим координатам."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import demand_model as dm

nodes = dm.nodes()
airports = pd.read_csv(ROOT / "data/processed/catchments.csv").set_index("iata")
source = json.loads((ROOT / "context/12_network_economics/inputs.json").read_text(encoding="utf-8"))
assumptions = pd.read_csv(ROOT / "data/assumptions/network.csv").set_index("parameter")
rows = []
for market in source["markets"]:
    orig_a, orig_b = market["pair"].split("-")
    if orig_a not in airports.index or orig_b not in airports.index:
        raise ValueError(f"Нет координат исходных аэропортов для {market['pair']}")
    p, q = airports.loc[orig_a], airports.loc[orig_b]
    airport_km = dm.hav(p.latitude_deg, p.longitude_deg, q.latitude_deg, q.longitude_deg)
    a, b = (dm.grp(x) for x in (orig_a, orig_b))
    if a not in nodes.index or b not in nodes.index:
        raise ValueError(f"Нет координат для {market['pair']}")
    x, y = nodes.loc[a], nodes.loc[b]
    km = dm.hav(x.latitude_deg, x.longitude_deg, y.latitude_deg, y.longitude_deg)
    rows.append((airport_km, km, float(market["fare_base"]), float(market["fare_cautious"])))
data = np.array(rows)
print(f"Проверено пар: {len(data)}; источник указывает, что тарифы сценарные")
for column, name in ((2, "base"), (3, "cautious")):
    slope, intercept = np.polyfit(data[:, 0], data[:, column], 1)
    slope_mow, intercept_mow = np.polyfit(data[:, 1], data[:, column], 1)
    fixed = float(assumptions.loc["fare_fixed_rub", name])
    per_km = float(assumptions.loc["fare_per_km_rub", name])
    print(f"{name}: по исходным аэропортам {intercept:.2f} + {slope:.4f} ₽/км; "
          f"в модели {fixed:.2f} + {per_km:.4f} ₽/км")
    print(f"{name}: при группировке аэропортов Москвы {intercept_mow:.2f} + {slope_mow:.4f} ₽/км")
    assert round(intercept) == fixed and round(slope, 2) == per_km, "Коэффициенты отличаются после округления"
