"""Проверки единиц и передачи входных данных модели спроса."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_airport_population_and_coordinates_are_usable():
    nodes = pd.read_csv(ROOT / "data/processed/catchments.csv")
    assert nodes.iata.notna().all() and not nodes.iata.duplicated().any()
    for col in ("pop", "latitude_deg", "longitude_deg"):
        assert np.isfinite(nodes[col]).all()
    assert nodes["pop"].gt(0).all()
    assert nodes.latitude_deg.between(-90, 90).all()
    assert nodes.longitude_deg.between(-180, 180).all()


def test_pairs_preserve_rail_missing_and_positive_demand():
    pairs = pd.read_csv(ROOT / "data/processed/demand_pairs.csv")
    keys = pairs.apply(lambda r: tuple(sorted((r.a, r.b))), axis=1)
    assert not keys.duplicated().any()
    assert pairs.rail_imputed_96h.eq(pairs.rail_hr.isna()).all()
    assert pairs.rail_hr.dropna().gt(0).all()
    for col in ("pop_a", "pop_b", "km", "pax_base", "pax_cautious", "pax_optimistic"):
        assert np.isfinite(pairs[col]).all() and pairs[col].gt(0).all()


def test_known_flow_annualisation_and_coverage_are_transferred():
    known = pd.read_csv(ROOT / "data/manual/known_flows.csv")
    pairs = pd.read_csv(ROOT / "data/processed/demand_pairs.csv")
    key = lambda a, b: tuple(sorted((a, b)))
    observations = {key(r.from_iata, r.to_iata): r for r in known.itertuples()}
    checked = 0
    for r in pairs[pairs.observed.notna()].itertuples():
        source = observations[key(r.a, r.b)]
        assert r.observed == source.pax * source.annual_factor
        assert r.observed_coverage == source.coverage
        assert r.observed_annual_factor == source.annual_factor
        checked += 1
    assert checked > 0
