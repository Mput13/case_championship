"""Обновить подписи источников в готовой сети без изменения пассажиров и денег."""
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from network_model import Demand

P = ROOT / "data/processed"
routes = pd.read_csv(P / "network_routes.csv")
full = pd.read_csv(P / "mandatory_routes_all_scenarios.csv")
table = pd.read_csv(P / "mandatory_routes_table.csv")
pd.testing.assert_frame_equal(full[routes.columns], routes)
base = routes[routes.scenario.eq("base")]
assert table["Вариант"].tolist() == base.variant.tolist()
demand = Demand()
routes["demand_source"] = [demand.method(a, b) for a, b in zip(routes["from"], routes["to"])]
full["demand_source"] = routes["demand_source"]
table["Откуда спрос пары"] = routes.loc[routes.scenario.eq("base"), "demand_source"].tolist()
routes.to_csv(P / "network_routes.csv", index=False, encoding="utf-8")
full.to_csv(P / "mandatory_routes_all_scenarios.csv", index=False, encoding="utf-8")
table.to_csv(P / "mandatory_routes_table.csv", index=False, encoding="utf-8")
print(f"Обновлены подписи источников: {len(routes)} плеч во всех сценариях")
