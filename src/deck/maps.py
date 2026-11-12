"""Карты для презентации: хабы и прямые рейсы на светлой карте (Natural Earth из data/processed/geo_map.json).

Запуск: py -3.13 src/deck/maps.py  → outputs/presentation/maps/*.png
"""
import json
import math
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402
from matplotlib.patches import Polygon  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "presentation" / "maps"
FONT_DIR = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts"
for f in ("Onest-Regular.ttf", "Onest-Medium.ttf", "Onest-Bold.ttf"):
    if (FONT_DIR / f).exists():
        fm.fontManager.addfont(str(FONT_DIR / f))
plt.rcParams["font.family"] = "Onest"

C = {"sea": "#E3ECF2", "land": "#F4F1EA", "rus": "#ECE6DA", "border": "#FFFFFF", "ink": "#2A2F3A",
     "muted": "#6B7280", "red": "#E32A2F", "next": "#E8962E", "green": "#2F9E6A", "base": "#5B6475"}

# коническая проекция Ламберта для России
LAT1, LAT2, LAT0, LON0 = math.radians(50), math.radians(64), math.radians(55), 70.0
N_ = math.log(math.cos(LAT1) / math.cos(LAT2)) / math.log(math.tan(math.pi / 4 + LAT2 / 2) / math.tan(math.pi / 4 + LAT1 / 2))
F_ = math.cos(LAT1) * math.tan(math.pi / 4 + LAT1 / 2) ** N_ / N_
R0 = F_ / math.tan(math.pi / 4 + LAT0 / 2) ** N_


def proj(lon, lat):
    r = F_ / math.tan(math.pi / 4 + math.radians(lat) / 2) ** N_
    t = N_ * math.radians(lon - LON0)
    return r * math.sin(t), R0 - r * math.cos(t)


def rings(geom):
    if geom["type"] == "Polygon":
        return geom["coordinates"]
    if geom["type"] == "MultiPolygon":
        return [r for poly in geom["coordinates"] for r in poly]
    return []


ASPECT = 1.55  # ширина / высота окна карты на слайде


def base_map(ax, geo, ext):
    ax.set_facecolor(C["sea"])
    for f in geo["countries"]:
        rus = f["properties"].get("ADM0_A3") == "RUS"
        for ring in rings(f["geometry"]):
            pts = [proj(x, y) for x, y in ring]
            ax.add_patch(Polygon(pts, closed=True, fc=C["rus"] if rus else C["land"], ec="#D9D3C7", lw=0.6, zorder=1))
    for f in geo["regions"]:
        for ring in rings(f["geometry"]):
            pts = [proj(x, y) for x, y in ring]
            ax.add_patch(Polygon(pts, closed=True, fc="none", ec=C["border"], lw=0.5, zorder=2))
    for f in geo["lakes"]:
        for ring in rings(f["geometry"]):
            ax.add_patch(Polygon([proj(x, y) for x, y in ring], closed=True, fc=C["sea"], ec="none", zorder=2))
    xs = [proj(lo, la)[0] for lo in (ext[0], ext[1]) for la in (ext[2], ext[3])]
    ys = [proj(lo, la)[1] for lo in (ext[0], ext[1]) for la in (ext[2], ext[3])]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    # окно под пропорции слайда: добираем по короткой стороне вокруг центра
    w, hgt = x1 - x0, y1 - y0
    if w / hgt > ASPECT:
        c = (y0 + y1) / 2; hgt = w / ASPECT; y0, y1 = c - hgt / 2, c + hgt / 2
    else:
        c = (x0 + x1) / 2; w = hgt * ASPECT; x0, x1 = c - w / 2, c + w / 2
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.axis("off")


def arc(a, b, bend=0.12, n=40):
    (x0, y0), (x1, y1) = a, b
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = x1 - x0, y1 - y0
    cx, cy = mx - dy * bend, my + dx * bend
    pts = []
    for i in range(n + 1):
        t = i / n
        pts.append(((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1, (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1))
    return zip(*pts)


def city(ax, xy, name, kind="dot", dx=0.004, dy=0.004, size=11, weight="medium", color=None, ha="left"):
    color = color or C["ink"]
    if kind == "hub":
        ax.scatter(*xy, s=260, c="white", edgecolors=C["red"], linewidths=3.2, zorder=6)
        ax.scatter(*xy, s=70, c=C["red"], zorder=7)
    elif kind == "hub_next":
        ax.scatter(*xy, s=220, c="white", edgecolors=C["red"], linewidths=2.2, linestyle="--", zorder=6)
    elif kind.startswith("hub_n"):
        ax.scatter(*xy, s=420, c=C["next"], edgecolors="white", linewidths=2.5, zorder=6)
        ax.text(xy[0], xy[1], kind[5:], fontsize=12, fontweight="bold", color="white", ha="center", va="center", zorder=7)
    elif kind == "base":
        ax.scatter(*xy, s=70, c=C["base"], marker="s", zorder=6)
    else:
        ax.scatter(*xy, s=26, c="white", edgecolors=C["ink"], linewidths=1.4, zorder=6)
    ax.text(xy[0] + dx, xy[1] + dy, name, fontsize=size, fontweight=weight, color=color, zorder=8, ha=ha,
            path_effects=[matplotlib.patheffects.withStroke(linewidth=3, foreground="white")])


import matplotlib.patheffects  # noqa: E402


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    geo = json.loads((ROOT / "data/processed/geo_map.json").read_text(encoding="utf-8"))
    d = json.loads((ROOT / "outputs/presentation/deck_data.json").read_text(encoding="utf-8"))
    ap = pd.read_csv(ROOT / "data/raw/ourairports_airports.csv", low_memory=False)
    ap = ap[ap.type.str.contains("airport") & ap.iata_code.notna()].drop_duplicates("iata_code").set_index("iata_code")
    xy = lambda c: proj(*(ap.loc["SVO" if c == "MOW" else c, ["longitude_deg", "latitude_deg"]].astype(float).tolist()))
    names = {r["to"]: r["city"].replace(" (Бегишево)", "") for r in d["routes"]}
    names.update({"MOW": "Москва", "SVX": "Екатеринбург", "OMS": "Омск", "KUF": "Самара"})

    # --- карта хабов: лучи Омска и следующие хабы по очереди ---
    NEXT = {"KUF": (2, "Самара", 0.0, -0.034, "center"), "CEK": (3, "Челябинск", 0.006, -0.036, "left"), "TJM": (4, "Тюмень", 0.0, 0.020, "center")}
    fig, ax = plt.subplots(figsize=(9.3, 6.0), dpi=220)
    base_map(ax, geo, (35, 110, 47, 60))
    H = d["hub"]
    mx = max(r["pax"] for r in d["routes"])
    for r in d["routes"]:
        xs, ys = arc(xy(H), xy(r["to"]), 0.05)
        ax.plot(list(xs), list(ys), color=C["red"], lw=1.2 + 3.2 * r["pax"] / mx, alpha=0.85, solid_capstyle="round", zorder=4)
    off = {"MOW": (-0.012, 0.004, "right"), "IAR": (-0.006, 0.010, "right"), "GOJ": (0.002, 0.010, "left"), "VOG": (-0.010, -0.010, "right"),
           "GSV": (-0.010, -0.012, "right"), "NBC": (-0.008, 0.008, "right"), "UFA": (-0.004, 0.010, "right"),
           "TOF": (0.004, 0.009, "left"), "NOZ": (0.006, -0.018, "left"), "IKT": (-0.006, -0.022, "right"), "UUD": (0.006, 0.006, "left")}
    for r in d["routes"]:
        if r["to"] in NEXT:
            continue
        o = off.get(r["to"], (0.004, 0.005, "left"))
        city(ax, xy(r["to"]), names[r["to"]], dx=o[0], dy=o[1], ha=o[2], size=10.5)
    # следующие хабы по очереди: Самара (опорный аэропорт Red Wings), Челябинск и Тюмень (высокий итог сети)
    for code, (n_, name, dx, dy, ha) in NEXT.items():
        city(ax, xy(code), name, kind=f"hub_n{n_}", dx=dx, dy=dy, size=12, weight="bold", color="#B8701A", ha=ha)
    city(ax, xy(H), "Омск\nпервый хаб", kind="hub", dx=0.0, dy=-0.058, size=14, weight="bold", color=C["red"], ha="center")
    fig.subplots_adjust(0, 0, 1, 1)
    fig.savefig(OUT / "map_hubs.png", facecolor=C["sea"])
    plt.close(fig)

    # --- карта прямых рейсов: окупаемые треугольники ---
    tri = pd.read_csv(ROOT / "data/processed/network_routes.csv")
    tri = tri[(tri.scenario == "base") & tri.variant.str.startswith("Прямые")]
    res = tri.groupby("variant").triangle_result_mln_year.first().sort_values(ascending=False)
    pos = [v for v, x in res.items() if x > 0]
    fig, ax = plt.subplots(figsize=(9.3, 6.0), dpi=220)
    base_map(ax, geo, (33, 77, 42, 58))
    shown = set()
    for i, v in enumerate(pos):
        codes = v.replace("Прямые ", "").split("-")
        for a, b in ((codes[0], codes[1]), (codes[1], codes[2]), (codes[2], codes[0])):
            xs, ys = arc(xy(a), xy(b), 0.1 if i % 2 else -0.1)
            ax.plot(list(xs), list(ys), color=C["green"], lw=2.4, alpha=0.85, solid_capstyle="round", zorder=4)
        shown.update(codes)
    off2 = {"GSV": (0.004, 0.006, "left"), "MRV": (0.005, -0.012, "left"), "AER": (-0.005, -0.012, "right"), "VOG": (0.005, 0.004, "left"),
            "KUF": (0.005, 0.006, "left"), "OMS": (0.0, 0.012, "center"), "KRO": (0.005, 0.006, "left")}
    for c in sorted(shown - {"MOW"}):
        o = off2.get(c, (0.004, 0.005, "left"))
        nm_ = {"GSV": "Саратов", "MRV": "Минеральные Воды", "AER": "Сочи", "VOG": "Волгоград", "KRO": "Курган"}.get(c, names.get(c, c))
        city(ax, xy(c), nm_, dx=o[0], dy=o[1], ha=o[2], size=11)
    city(ax, xy("MOW"), "Москва, база", kind="base", dx=-0.008, dy=0.008, size=11, weight="bold", color=C["base"], ha="right")
    fig.subplots_adjust(0, 0, 1, 1)
    fig.savefig(OUT / "map_direct.png", facecolor=C["sea"])
    plt.close(fig)
    print("ok", OUT, "треугольников в плюсе:", len(pos))


if __name__ == "__main__":
    main()
