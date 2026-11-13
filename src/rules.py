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
# аэропорты Москвы сводятся в один узел MOW; базы Red Wings по брифу — Москва и Екатеринбург (data/assumptions/bases.csv)
_B = pd.read_csv(ROOT / "data/assumptions/bases.csv")
MOW_AIRPORTS = set(_B[_B.node == "MOW"].iata)
BASES = list(dict.fromkeys(_B.node))
_LP = pd.read_csv(ROOT / "data/assumptions/longlist_params.csv").set_index("parameter").value
RAIL_OK_HR, CATCH_KM, MIN_DIST_KM = float(_LP["rail_ok_hr"]), float(_LP["catchment_km"]), float(_LP["min_dist_bases_km"])
# включаемый фильтр рейтинга (по умолчанию выключен, MIN_DIST_KM = 0)
FILTER_OPTION_KM = float(_LP["filter_option_km"])


def scores_file(min_dist=None):
    """Файл рейтинга городов при фильтре min_dist км (по умолчанию — основной вариант из longlist_params.csv)."""
    d = MIN_DIST_KM if min_dist is None else min_dist
    return ROOT / "data/processed" / (f"longlist_scores_min{int(d)}.csv" if d else "longlist_scores.csv")
# лонглист команды: 20 городов, пассажиропоток 2025 и ссылки на источники в колонках *_source_url.
# Копия context/07_verification/terra_cities_review/corrected_cities.csv (коммит cdefb6b, 07.11.2026), перенесена 13.11.2026.
CITIES = ROOT / "data/manual/longlist_cities.csv"


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
