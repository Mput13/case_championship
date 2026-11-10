"""Проверки модели и согласованности выпускных таблиц."""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import network_model as nm


def test_optional_subsidy_keeps_baseline_candidate(monkeypatch):
    a = dict(nm.load_assumptions()["cautious_sub"], fleet_cap=4)
    def fake_hub(h, d, assumptions, scen, nodes, fixed_spokes=None):
        # Жадный отбор с поддержкой ошибочно находит худшую сеть.
        chosen = list(fixed_spokes) if fixed_spokes else ["old" if not assumptions["use_subsidy"] else "new"] * 8
        result = 12 if fixed_spokes else (10 if not assumptions["use_subsidy"] else 5)
        return chosen, (None, None, 10, 100, 100 + result)
    monkeypatch.setattr(nm, "hub_network", fake_hub)
    chosen, result = nm.hub_best("OMS", None, a, "cautious", [])
    assert chosen[0] == "old"
    assert result[4] - result[3] == 12


def test_no_working_aircraft_rejected():
    a = dict(nm.load_assumptions()["base"], fleet_cap=1)
    with pytest.raises(ValueError, match="Нет самолётов"):
        nm.hub_network("OMS", None, a, "base", [])
    with pytest.raises(ValueError, match="Нет самолётов"):
        nm.direct_network(None, a, "base", [])


def test_subsidy_can_be_declined(monkeypatch):
    class D:
        def km(self, a, b):
            return 1000
    a = nm.load_assumptions()["base_sub"]
    monkeypatch.setattr(nm, "sub", lambda *args: 1)
    monkeypatch.setattr(nm, "special_fare", lambda *args: 100)
    revenue, subsidy = nm.leg_with_subsidy(D(), a, "A", "B", 3, 200)
    assert subsidy == 0
    assert revenue == 400 * nm.fare(a, 1000)


def test_all_exported_networks_reconcile():
    s = pd.read_csv(ROOT / "data/processed/network_summary.csv")
    r = pd.read_csv(ROOT / "data/processed/network_routes.csv")
    assert len(s) == 84
    assert not s.duplicated(["scenario", "variant"]).any()
    assert set(s.scenario) == {"base", "base_sub", "cautious", "cautious_sub"}
    assert (s.check_segments_minus_od == 0).all()
    for row in s.itertuples():
        legs = r[r.scenario.eq(row.scenario)]
        legs = legs[legs.variant.str.startswith("Прямые ")] if pd.isna(row.hub) else legs[legs.variant.eq("Хаб " + row.hub)]
        assert len(legs) > 0
        assert abs(legs.pax_year_segments.sum() - row.segments_year) <= len(legs) * .5 + .5
        assert abs(row.segments_year - row.od_trips_year - row.transfer_od_year) <= 1
        assert abs(row.segments_year - row.rw_migrated_year - row.net_new_segments_year) <= 1
        for detail, total in [("result_mln_year", "result_mln_year"), ("revenue_mln_year", "revenue_mln_year"),
                              ("cost_mln_year", "var_cost_mln_year"), ("subsidy_mln_year", "subsidy_mln_year")]:
            assert abs(legs[detail].sum() - getattr(row, total)) <= len(legs) * .05 + .5 + 1e-8
        assert 2 * legs.freq_week_each_way.sum() == row.flights_week
        a = nm.load_assumptions()[row.scenario]
        assert (legs.load_factor <= a["lf_max"] + .005).all()
        assert (legs.pax_year_segments <= 2 * legs.freq_week_each_way * a["weeks_per_year"] * a["seats"] * a["lf_max"] + .5).all()
        assert row.aircraft <= a["fleet_cap"]
        assert a["min_routes"] <= row.routes <= a["max_routes"]
        assert abs(row.share_pp - row.net_new_segments_year / a["market_pax_2025"] * 100) < .0051
    for scenario in ("base", "cautious"):
        plain = s[s.scenario.eq(scenario)].set_index("variant")
        supported = s[s.scenario.eq(scenario + "_sub")].set_index("variant")
        assert (supported.result_mln_year >= plain.result_mln_year).all()
    full = pd.read_csv(ROOT / "data/processed/mandatory_routes_all_scenarios.csv")
    pd.testing.assert_frame_equal(full[r.columns], r)


def test_forgone_revenue_is_not_discounted_with_subsidized_tickets(monkeypatch):
    class D:
        def km(self, a, b):
            return 1000
    a = dict(nm.load_assumptions()["base_sub"], subsidy_months=12)
    monkeypatch.setattr(nm, "sub", lambda *args: 1_000_000)
    monkeypatch.setattr(nm, "special_fare", lambda *args: 1000)
    revenue, subsidy = nm.leg_with_subsidy(D(), a, "A", "B", 3, 200, forgone_rev=50_000)
    assert subsidy == 6_000_000
    assert revenue == 400 * 1000 + subsidy - 50_000
