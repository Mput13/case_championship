"""Общие правила дальности для всех скриптов: пороги светофора и регионы с обходами (k_трассы 1,20).

Числа и список регионов лежат в data/assumptions/range.csv и south_west_regions.csv (источник — docs/17),
чтобы лонглист, модель сети и карта пользовались одними и теми же правилами.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
_R = pd.read_csv(ROOT / "data/assumptions/range.csv").set_index("parameter").value
GREEN = float(_R["ssj_green_km"])
GREEN_SOUTH = float(_R["ssj_green_south_km"])
TU204 = float(_R["tu204_green_km"])
TU214 = float(_R["tu214_green_km"])
SOUTH_WEST = set(pd.read_csv(ROOT / "data/assumptions/south_west_regions.csv").region)


def is_south(region):
    return region in SOUTH_WEST


def green_limit(region_a, region_b):
    """Зелёный порог SSJ для пары: юг/запад — меньше (docs/17)."""
    return GREEN_SOUTH if (is_south(region_a) or is_south(region_b)) else GREEN


def light(region_a, region_b, km):
    g = green_limit(region_a, region_b)
    if km <= g:
        return "зелёный" + (f" (юг/запад, порог {int(g):,} км)".replace(",", " ") if g < GREEN else "")
    if km <= TU204:
        return "жёлтый: SSJ на пределе, нужен Ту-204/214"
    if km <= TU214:
        return "жёлтый: только Ту-214"
    return "красный: дальше Ту-214"
