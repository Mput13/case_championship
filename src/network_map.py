"""Шаг 4. Карты сетей для паспорта и слайдов: хаб и прямые рейсы, базовый сценарий.

Контуры — Natural Earth (data/processed/geo_map.json), проекция — равновеликая коническая Альберса
для России (параллели 52° и 64°, центральный меридиан 95°). Маршруты — дуги большого круга,
толщина линии — пассажиры в год, подпись — рейсов в неделю в одну сторону.
Шрифт задан явно (Arial); Calibri не используется.

Выход: outputs/map_hub.png, outputs/map_direct.png
Запуск: python src/network_map.py   (после src/network_model.py)
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import Polygon  # noqa: E402

import demand_model as dm  # noqa: E402
import rules  # noqa: E402
from airports_meta import NAME  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
OUT = ROOT / "outputs"
plt.rcParams["font.family"] = "Arial"
INK, RED, STEEL, PAPER, SEA, LAND2, LINE = "#111318", "#E32A2F", "#8C96A6", "#FBFAF7", "#E4EBF0", "#ECEAE4", "#B9B5AC"

PHI1, PHI2, PHI0, LAM0 = np.radians(52), np.radians(64), np.radians(50), np.radians(95)
N = (np.sin(PHI1) + np.sin(PHI2)) / 2
C = np.cos(PHI1) ** 2 + 2 * N * np.sin(PHI1)
RHO0 = np.sqrt(C - 2 * N * np.sin(PHI0)) / N


def proj(lon, lat):
    lon, lat = np.radians(np.asarray(lon, float)), np.radians(np.asarray(lat, float))
    lon = np.where(lon - LAM0 < -np.pi, lon + 2 * np.pi, lon)
    rho = np.sqrt(C - 2 * N * np.sin(lat)) / N
    th = N * (lon - LAM0)
    return rho * np.sin(th), RHO0 - rho * np.cos(th)


def gc(lon1, lat1, lon2, lat2, n=60):
    a = np.radians([lat1, lon1]); b = np.radians([lat2, lon2])
    va = np.array([np.cos(a[0]) * np.cos(a[1]), np.cos(a[0]) * np.sin(a[1]), np.sin(a[0])])
    vb = np.array([np.cos(b[0]) * np.cos(b[1]), np.cos(b[0]) * np.sin(b[1]), np.sin(b[0])])
    om = np.arccos(np.clip(va @ vb, -1, 1))
    t = np.linspace(0, 1, n)[:, None]
    v = (np.sin((1 - t) * om) * va + np.sin(t * om) * vb) / np.sin(om)
    return np.degrees(np.arctan2(v[:, 1], v[:, 0])), np.degrees(np.arcsin(v[:, 2]))


def rings(geom):
    t, c = geom["type"], geom["coordinates"]
    if t == "Polygon":
        return [c[0]]
    if t == "MultiPolygon":
        return [p[0] for p in c]
    if t == "LineString":
        return [c]
    if t == "MultiLineString":
        return c
    return []


def base_map(ax, geo, extent=(26, 136, 41, 69)):
    ax.set_facecolor(SEA)
    for f in geo["countries"]:
        rus = f["properties"].get("ADM0_A3") == "RUS"
        for r in rings(f["geometry"]):
            x, y = proj(*np.array(r).T)
            ax.add_patch(Polygon(np.c_[x, y], closed=True, fc=PAPER if rus else LAND2, ec=LINE, lw=0.6 if rus else 0.4, zorder=1))
    for f in geo["regions"]:
        for r in rings(f["geometry"]):
            x, y = proj(*np.array(r).T)
            ax.plot(x, y, color="#E2DFD8", lw=0.35, zorder=2)
    for f in geo["lakes"]:
        for r in rings(f["geometry"]):
            x, y = proj(*np.array(r).T)
            ax.add_patch(Polygon(np.c_[x, y], closed=True, fc="#C9DCE8", ec="none", zorder=2))
    lo, la = np.meshgrid(np.linspace(extent[0], extent[1], 40), np.linspace(extent[2], extent[3], 20))
    x, y = proj(lo.ravel(), la.ravel())
    ax.set_xlim(x.min(), x.max())
    ax.set_ylim(y.min(), y.max())
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)


def draw(legs, nodes, title, sub, fname, hub=None, ring_km=None, extent=(26, 136, 41, 69)):
    geo = json.loads((P / "geo_map.json").read_text(encoding="utf-8"))
    lo, la = np.meshgrid(np.linspace(extent[0], extent[1], 40), np.linspace(extent[2], extent[3], 20))
    gx, gy = proj(lo.ravel(), la.ravel())
    w = 13
    fig, ax = plt.subplots(figsize=(w, w * (gy.max() - gy.min()) / (gx.max() - gx.min()) / 0.96 + 1.3), dpi=170)
    fig.patch.set_facecolor("#F3F1EC")
    base_map(ax, geo, extent)
    if hub and ring_km:
        lo, la = nodes.loc[hub, "longitude_deg"], nodes.loc[hub, "latitude_deg"]
        brg = np.radians(np.arange(0, 361, 3)); d = ring_km / 6371
        p1, l1 = np.radians(la), np.radians(lo)
        p2 = np.arcsin(np.sin(p1) * np.cos(d) + np.cos(p1) * np.sin(d) * np.cos(brg))
        l2 = l1 + np.arctan2(np.sin(brg) * np.sin(d) * np.cos(p1), np.cos(d) - np.sin(p1) * np.sin(p2))
        x, y = proj(np.degrees(l2), np.degrees(p2))
        ax.fill(x, y, color="#3FA772", alpha=0.07, zorder=3)
        ax.plot(x, y, color="#3FA772", lw=1.2, zorder=3)
        tx, ty = proj(np.degrees(l2[3]), np.degrees(p2[3]))
        ax.text(tx, ty, f"SSJ-100 / SJ-100 · {ring_km:,} км".replace(",", " "), color="#2E7D4F", fontsize=9, fontweight="bold",
                ha="center", va="bottom", zorder=6)
    mx = legs.pax.max()
    pts = set()
    placed = []
    for r in legs.itertuples():
        A, B = nodes.loc[r.a], nodes.loc[r.b]
        lo, la = gc(A.longitude_deg, A.latitude_deg, B.longitude_deg, B.latitude_deg)
        x, y = proj(lo, la)
        ax.plot(x, y, color=RED, lw=0.8 + 4.2 * r.pax / mx, alpha=0.85, solid_capstyle="round", zorder=4)
        m = int(len(x) * (0.45 if r.Index % 2 else 0.6))
        ax.text(x[m], y[m], f"{r.freq}/нед", fontsize=7.5, color=INK, ha="center", va="center", zorder=7,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
        pts |= {r.a, r.b}
    for i in pts:
        n = nodes.loc[i]
        x, y = proj(n.longitude_deg, n.latitude_deg)
        is_hub = i == hub or i in ("MOW", "SVX") and hub is None
        ax.scatter(x, y, s=140 if is_hub else 34, c=RED if is_hub else "white", edgecolors=INK, linewidths=1.3, zorder=8,
                   marker="s" if i in ("MOW", "SVX") and hub is None else "o")
        dy = 0.004
        for px, py_ in placed:  # соседняя подпись рядом — опускаем эту ниже точки
            if abs(px - x) < 0.06 and abs(py_ - y) < 0.012:
                dy = -0.016
        placed.append((x, y))
        ax.text(x + 0.006, y + dy, NAME.get(i, n.main_city), fontsize=10 if is_hub else 8.5,
                fontweight="bold" if is_hub else "normal", color=INK, zorder=9,
                path_effects=[matplotlib.patheffects.withStroke(linewidth=2.5, foreground="white")])
    fig.text(0.04, 0.95, title, fontsize=17, fontweight="bold", color=INK)
    fig.text(0.04, 0.915, sub, fontsize=10.5, color="#5E6675")
    fig.text(0.04, 0.03, "Толщина линии — пассажиров в год; подпись — рейсов в неделю в одну сторону. Контуры: Natural Earth. "
             "Спрос: модель шага 2 (docs/23); сеть: src/network_model.py (docs/24).", fontsize=8, color="#5E6675")
    fig.subplots_adjust(left=0.02, right=0.98, top=0.88, bottom=0.06)
    fig.savefig(OUT / fname, facecolor=fig.get_facecolor())
    plt.close(fig)
    print("карта", OUT / fname)


def ru(v, d=0):
    return f"{v:,.{d}f}".replace(",", " ").replace(".", ",")


def fit_extent(legs, nodes, pad_lon=6, pad_lat=3):
    """Рамка карты по концам маршрутов с полями (раньше рамка прямой сети была задана числами в коде)."""
    ids = set(legs.a) | set(legs.b)
    lo = nodes.loc[list(ids), "longitude_deg"]
    la = nodes.loc[list(ids), "latitude_deg"]
    return (float(lo.min() - pad_lon), float(lo.max() + pad_lon), float(la.min() - pad_lat), float(la.max() + pad_lat))


def main():
    import matplotlib.patheffects  # noqa: F401
    nodes = dm.nodes()
    r = pd.read_csv(P / "network_routes.csv")
    s = pd.read_csv(P / "network_summary.csv")
    b = r[r.scenario == "base"]
    sb = s[s.scenario == "base"].set_index("variant")
    hubs = sb[sb.hub.notna() & (sb.hub != "")]
    best = hubs.sort_values("result_mln_year", ascending=False).iloc[0]
    H = best.hub
    hl = b[b.variant == f"Хаб {H}"]
    legs = pd.DataFrame({"a": hl["from"], "b": hl["to"], "pax": hl.pax_year_segments, "freq": hl.freq_week_each_way})
    city = best.name.replace("Хаб ", "")
    loc = {"Омск": "Омске", "Уфа": "Уфе", "Волгоград": "Волгограде", "Нижний Новгород": "Нижнем Новгороде",
           "Хабаровск": "Хабаровске"}.get(city, city)
    draw(legs, nodes, f"Гипотеза 1: хаб в {loc}",
         f"{int(best.routes)} маршрутов · {int(best.aircraft)} самолётов · {ru(best.segments_year/1e3)} тыс. пассажиров в год · "
         f"доля рынка +{ru(best.share_pp, 2)} п. п. · базовый сценарий",
         "map_hub.png", hub=H, ring_km=rules.GREEN)
    d = b[b.variant.str.startswith("Прямые")]
    dr = sb.loc["Прямые рейсы из Москвы и Екатеринбурга"]
    legs = pd.DataFrame({"a": d["from"], "b": d["to"], "pax": d.pax_year_segments, "freq": d.freq_week_each_way})
    legs = legs.groupby(["a", "b"], as_index=False).agg(pax=("pax", "sum"), freq=("freq", "sum"))
    bases = sorted({x for x in d["from"]} & {"MOW", "SVX"})
    who = "из Москвы" if bases == ["MOW"] else "из Екатеринбурга" if bases == ["SVX"] else "из Москвы и Екатеринбурга"
    draw(legs, nodes, f"Гипотеза 2: прямые рейсы {who}",
         f"{int(dr.routes)} треугольников база — X — Y — база · {int(dr.aircraft)} самолётов · "
         f"{ru(dr.segments_year/1e3)} тыс. пассажиров в год · доля рынка +{ru(dr.share_pp, 2)} п. п. · базовый сценарий",
         "map_direct.png", extent=fit_extent(legs, nodes))


if __name__ == "__main__":
    main()
