"""Проверки модели и согласованности выпускных таблиц."""
import sys
from types import SimpleNamespace
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import network_model as nm


def test_optional_subsidy_keeps_baseline_candidate(monkeypatch):
    a = dict(nm.load_assumptions()["cautious_sub"], fleet_cap=4, season_on=0.0)   # подставная сеть без сезонов
    def fake_hub(h, d, assumptions, scen, nodes, fixed_spokes=None):
        # Жадный отбор с поддержкой ошибочно находит худшую сеть.
        chosen = list(fixed_spokes) if fixed_spokes else ["old" if not assumptions["use_subsidy"] else "new"] * 8
        result = (12 if chosen[0] == "old" else 5) if fixed_spokes else (10 if not assumptions["use_subsidy"] else 5)
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


def test_search_includes_intermediate_fleet_limits():
    a = nm.load_assumptions()["base"]
    assert nm.search_caps(a) == list(range(2, 11))
    assert nm.search_caps(dict(a, fleet_cap=3)) == [2, 3]


def test_frequency_rejects_impossible_load_factor():
    a = dict(nm.load_assumptions()["base"], lf_max=1.01)
    with pytest.raises(ValueError, match="100%"):
        nm.freq_for(100, a)


def test_federal_subsidy_requires_different_known_regions(monkeypatch):
    class D:
        n = pd.DataFrame({"region": ["Омская область", "Омская область", None]}, index=["A", "B", "C"])
    monkeypatch.setattr(nm, "_load_held", lambda _: None)
    monkeypatch.setattr(nm, "SUB_HUBS", {"A"})
    a = nm.load_assumptions()["base_sub"]
    assert nm.sub_rule(D(), a, "A", "B") == (0.0, "аэропорты в одном субъекте РФ")
    assert nm.sub_rule(D(), a, "A", "C") == (0.0, "субъект аэропорта не указан")


def test_federal_subsidy_can_connect_two_hubs(monkeypatch):
    class D:
        n = pd.DataFrame({"region": ["Регион 1", "Регион 2"]}, index=["A", "B"])
        seg_tab = {}
        def km(self, a, b): return 500
        def has_direct(self, a, b): return False
    monkeypatch.setattr(nm, "_load_held", lambda _: None)
    monkeypatch.setattr(nm, "_SUB_HELD", {})
    monkeypatch.setattr(nm, "SUB_HUBS", {"A", "B"})
    rate, reason = nm.sub_rule(D(), nm.load_assumptions()["base_sub"], "A", "B")
    assert rate > 0 and reason == ""
    rate, _ = nm.sub_rule(D(), dict(nm.load_assumptions()["base_sub"], search_exclude_two_hubs=True), "A", "B")
    assert rate == 0


def test_hub_search_retains_previous_candidate_when_expanding_subsidy(monkeypatch):
    a = dict(nm.load_assumptions()["cautious_sub"], fleet_cap=2, season_on=0.0)
    def fake_hub(h, d, assumptions, scen, nodes, fixed_spokes=None):
        chosen = list(fixed_spokes) if fixed_spokes else ["old" if assumptions.get("search_exclude_two_hubs") else "new"] * 8
        result = 10 if chosen[0] == "old" else 2
        return chosen, (None, None, 10, 100, 100 + result)
    monkeypatch.setattr(nm, "hub_network", fake_hub)
    chosen, result = nm.hub_best("TJM", None, a, "cautious", [], baseline=(["base"] * 8, None))
    assert chosen[0] == "old"
    assert result[4] - result[3] == 10


def test_direct_search_retains_previous_candidate_when_expanding_subsidy(monkeypatch):
    a = dict(nm.load_assumptions()["cautious_sub"], fleet_cap=2, season_on=0.0)
    def candidate(name, result):
        return (0, name, "X", "Y", 10, 100, 100 + result)
    def fake_direct(d, assumptions, scen, nodes, fixed_selection=None):
        name = fixed_selection[0][1] if fixed_selection else ("old" if assumptions.get("search_exclude_two_hubs") else "new")
        return [candidate(name, {"old": 10, "new": 2, "base": 1}[name])] * 8
    monkeypatch.setattr(nm, "direct_network", fake_direct)
    chosen = nm.direct_best(None, a, "cautious", [], baseline=[candidate("base", 1)] * 8)
    assert chosen[0][1] == "old"


def test_observation_source_preserves_region_and_annualisation():
    d = nm.Demand.__new__(nm.Demand)
    d.observation_meta = {frozenset(("A", "B")): ("region", "2025", 1),
                          frozenset(("A", "C")): ("airport", "I полугодие 2025", 2)}
    row = SimpleNamespace(a="A", b="B", observed=100, direct_now=True, own_trips_share=0.9)
    assert "вся область" in d.describe(row)
    row.b = "C"
    assert "полугодие" in d.describe(row) and "× 2" in d.describe(row)


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
        a = nm.load_assumptions()[row.scenario]
        # рейсов в неделю — в среднем за год по двум сезонам расписания (лето 7 месяцев, зима 5)
        w = dict(nm.seasons(a))
        freq_year = (legs.freq_week_each_way * w.get("summer", 1.0) + legs.freq_week_winter * w.get("winter", 0.0)
                     if "summer" in w else legs.freq_week_each_way)
        assert abs(2 * freq_year.sum() - row.flights_week) < 1
        # загрузка: плановая lf_max на сезон, месячный пик — до lf_peak_max
        assert (legs.load_factor <= nm.lf_cap(a) + .005).all()
        assert (legs.pax_year_segments <= 2 * freq_year * a["weeks_per_year"] * a["seats"] * nm.lf_cap(a) + .5).all()
        assert (legs.pax_year_spilled >= 0).all()
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


def test_fleet_ramp_matches_main_and_optional_support():
    ramp = pd.read_csv(ROOT / "data/processed/fleet_ramp.csv")
    summary = pd.read_csv(ROOT / "data/processed/network_summary.csv")
    assert (ramp.aircraft <= ramp.fleet_cap).all()
    for scenario, rows in ramp.groupby("scenario"):
        rows = rows.sort_values("fleet_cap")
        a = nm.load_assumptions()[scenario]
        feasible = rows[rows.routes.ge(a["min_routes"])]
        assert feasible.result_mln_year.diff().dropna().ge(0).all()
        last = rows.iloc[-1]
        if last.fleet_cap == a["fleet_cap"]:
            main = summary[summary.scenario.eq(scenario) & summary.hub.eq(last.hub)].iloc[0]
            for column in ("aircraft", "routes", "segments_year", "result_mln_year", "subsidy_mln_year"):
                assert main[column] == last[column], (scenario, column)
    for scenario in ("base", "cautious"):
        plain = ramp[ramp.scenario.eq(scenario)].set_index("fleet_cap")
        supported = ramp[ramp.scenario.eq(scenario + "_sub")].set_index("fleet_cap")
        m = nm.load_assumptions()[scenario]["min_routes"]
        # с субсидией итог не ниже, кроме случая, когда сеть без субсидии не набирает min_routes маршрутов,
        # а с субсидией набирает: требование кейса «8–12 маршрутов» важнее (best_of)
        short = plain.routes.lt(m) & supported.routes.ge(m)
        assert (supported.result_mln_year.ge(plain.result_mln_year) | short).all()
