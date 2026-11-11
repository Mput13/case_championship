"""Чувствительность сегментной модели к подстановке времени поезда.

Это расчёт формулы для сохранённого набора коэффициентов, а не новый расчёт
O&D, отбора маршрутов или финансовых результатов сети.
"""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data/processed"
pairs = pd.read_csv(P / "demand_pairs.csv")
fit = json.loads((P / "demand_fit.json").read_text(encoding="utf-8"))
assumptions = pd.read_csv(ROOT / "data/assumptions/demand.csv").set_index("parameter")
base_hours = float(assumptions.loc["no_rail_hr", "value"])
coefficient = float(fit["coefficients"]["lnRail"])
out = pairs[pairs.rail_imputed_96h].copy()
for hours in (48, 192):
    out[f"segment_estimate_{hours}h"] = (out.pax_base * (hours / base_hours) ** coefficient).round().astype(int)
out["hours_assumed_base"] = base_hours
out["scope"] = "сегментная формула; O&D и сеть не пересчитаны"
cols = ["a", "b", "city_a", "city_b", "pax_base", "segment_estimate_48h", "segment_estimate_192h", "hours_assumed_base", "scope"]
dest = ROOT / "outputs/verification/rail_imputation_sensitivity.csv"
dest.parent.mkdir(exist_ok=True)
out[cols].to_csv(dest, index=False, encoding="utf-8-sig")
print(f"Проверено пар: {len(out)}. Сегментная оценка сохранена в {dest}")
