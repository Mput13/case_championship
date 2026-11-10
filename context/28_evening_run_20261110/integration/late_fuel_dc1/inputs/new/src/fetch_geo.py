"""Скачивает контуры для карты (Natural Earth, Public Domain) и упрощает их до размера страницы.

Границы стран — версия Natural Earth «с точки зрения РФ» (ne_10m_admin_0_countries_rus).
Регионы РФ, озёра, реки — Natural Earth 10m.
Выход: data/processed/geo_map.json — {countries, regions, lakes, rivers} в GeoJSON,
       координаты округлены до 0,01°, линии упрощены (Дуглас — Пекер, 0,03°).
Запуск: python src/fetch_geo.py
"""
import json
import urllib.request
from pathlib import Path

from shapely.geometry import MultiPolygon, Polygon, box, mapping, shape
from shapely.geometry.polygon import orient

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "geo"
OUT = ROOT / "data" / "processed" / "geo_map.json"
BASE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
FILES = ["ne_10m_admin_0_countries_rus", "ne_10m_admin_1_states_provinces",
         "ne_10m_lakes", "ne_10m_rivers_lake_centerlines"]
BBOX = box(10, 30, 190, 82)   # от Калининграда до Чукотки, с соседями
TOL = 0.03


def get(name):
    p = RAW / f"{name}.geojson"
    if not p.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(BASE + name + ".geojson", headers={"User-Agent": "case-champ"})
        with urllib.request.urlopen(req, timeout=300) as r:
            p.write_bytes(r.read())
        print("скачано", name, p.stat().st_size)
    return json.loads(p.read_text(encoding="utf-8"))


def rnd(o):
    if isinstance(o, float):
        return round(o, 2)
    if isinstance(o, (list, tuple)):
        return [rnd(x) for x in o]
    return o


def simplify(features, keep, tol=TOL, props=()):
    out = []
    for f in features:
        if not keep(f["properties"]):
            continue
        g = shape(f["geometry"])
        if not g.intersects(BBOX):
            continue
        g = g.intersection(BBOX).simplify(tol, preserve_topology=True)
        if g.is_empty:
            continue
        # d3-geo ждёт внешний контур по часовой стрелке (обратно правилу GeoJSON), иначе
        # многоугольник «выворачивается» и закрашивает весь земной шар
        if isinstance(g, Polygon):
            g = orient(g, sign=-1.0)
        elif isinstance(g, MultiPolygon):
            g = MultiPolygon([orient(p, sign=-1.0) for p in g.geoms])
        m = mapping(g)
        out.append({"type": "Feature", "properties": {k: f["properties"].get(k) for k in props},
                    "geometry": {"type": m["type"], "coordinates": rnd(m["coordinates"])}})
    return out


def main():
    c = get(FILES[0])
    a1 = get(FILES[1])
    lk = get(FILES[2])
    rv = get(FILES[3])
    geo = {
        "countries": simplify(c["features"], lambda p: True, props=("ADM0_A3", "NAME_RU")),
        "regions": simplify(a1["features"], lambda p: p.get("adm0_a3") == "RUS", props=("name_ru",)),
        "lakes": simplify(lk["features"], lambda p: (p.get("scalerank") or 9) <= 6),
        "rivers": simplify(rv["features"], lambda p: (p.get("scalerank") or 9) <= 6),
        "source": "Natural Earth 10m (Public Domain): admin_0 countries, точка зрения РФ; admin_1 РФ; "
                  "озёра и реки scalerank ≤ 6. https://www.naturalearthdata.com",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(geo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("готово", OUT, round(OUT.stat().st_size / 1e6, 2), "МБ;",
          {k: len(v) for k, v in geo.items() if isinstance(v, list)})


if __name__ == "__main__":
    main()
