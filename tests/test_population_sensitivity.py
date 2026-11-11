import importlib.util
from pathlib import Path

import pandas as pd
import pytest


PATH = Path(__file__).resolve().parents[1] / "scripts" / "population_sensitivity.py"
SPEC = importlib.util.spec_from_file_location("population_sensitivity", PATH)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_new_population_preserves_nodes_and_groups_moscow():
    ids = list(module.dm.MOW)
    catchments = pd.DataFrame({"iata": ids + ["OMS"]})
    extra = pd.DataFrame({"iata": ids + ["OMS"], "catchment_pop_2025": [10] * len(ids) + [25]})
    nodes = pd.DataFrame({"pop": [1, 2], "main_city": ["Москва", "Омск"]}, index=["MOW", "OMS"])
    result = module.population_nodes(nodes, catchments, extra)
    assert result.loc["MOW", "pop"] == 10 * len(ids)
    assert result.loc["OMS", "pop"] == 25
    assert nodes.loc["OMS", "pop"] == 2


def test_new_population_rejects_missing_airport():
    catchments = pd.DataFrame({"iata": ["OMS", "KZN"]})
    extra = pd.DataFrame({"iata": ["OMS"], "catchment_pop_2025": [25]})
    with pytest.raises(ValueError, match="Нет оценки населения"):
        module.population_nodes(pd.DataFrame(), catchments, extra)
