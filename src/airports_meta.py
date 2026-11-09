"""Общий справочник аэропортов для расчётов (данные — в data/manual/).

CLOSED — аэропорты, закрытые с 24.02.2022 и не открытые на 08.11.2026 (docs/16, раздел 3):
data/manual/closed_airports.csv. В базовом сценарии туда не летаем.
NAME — как называть аэропорт людям, если главный город его зоны звучит иначе:
data/manual/airport_names.csv.
"""
from pathlib import Path

import pandas as pd

_M = Path(__file__).resolve().parents[1] / "data" / "manual"
CLOSED = dict(pd.read_csv(_M / "closed_airports.csv")[["iata", "name"]].values)
NAME = dict(pd.read_csv(_M / "airport_names.csv")[["iata", "name"]].values)
