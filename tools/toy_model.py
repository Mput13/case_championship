# -*- coding: utf-8 -*-
"""
ИГРУШЕЧНАЯ модель — показывает, как устроен расчёт кейса от начала до конца.
ВСЕ ЦИФРЫ НИЖЕ УСЛОВНЫЕ (для понимания), это НЕ данные Red Wings и НЕ результат.
Запуск: python tools/toy_model.py   (нужны только pandas и numpy)
Подробное объяснение — docs/21_technical_explainer.md
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)

# ---------- 1. ЛОНГЛИСТ: многокритериальный выбор города ----------
cities = pd.DataFrame({
    "city":       ["Город A", "Город B", "Город C", "Город D"],
    "population": [1.2, 0.6, 1.0, 0.4],     # млн чел.
    "kovyor_days":[50, 0, 10, 5],           # дней ограничений за полгода (меньше = лучше)
    "fortress":   [0.8, 0.2, 0.5, 0.1],     # сила базового перевозчика 0..1 (меньше = лучше)
    "ssj_pairs":  [12, 7, 10, 6],           # сколько ключевых пар в зелёной зоне SSJ
})
better_high = {"population": True, "kovyor_days": False, "fortress": False, "ssj_pairs": True}
weights = {"population": 0.35, "kovyor_days": 0.25, "fortress": 0.20, "ssj_pairs": 0.20}

def normalize(col, high_is_good):
    x = (col - col.min()) / (col.max() - col.min())   # min-max: 0..1
    return x if high_is_good else 1 - x

def score(df, w):
    return sum(w[c] * normalize(df[c], better_high[c]) for c in w)

cities["score"] = score(cities, weights)
print("1) Лонглист (баллы 0..1):")
print(cities.sort_values("score", ascending=False)[["city", "score"]].round(2).to_string(index=False))

# Чувствительность: 2000 раз слегка меняем веса (±20%) и считаем, как часто город в топ-2
top_counts = {c: 0 for c in cities.city}
for _ in range(2000):
    w = {k: v * rng.uniform(0.8, 1.2) for k, v in weights.items()}
    s = sum(w.values()); w = {k: v / s for k, v in w.items()}
    top = cities.assign(s=score(cities, w)).nlargest(2, "s").city
    for c in top: top_counts[c] += 1
print("   Как часто город в топ-2 при случайном сдвиге весов:",
      {c: f"{n/2000:.0%}" for c, n in top_counts.items()})

# ---------- 2. СПРОС ПО ПАРЕ: гравитационная модель ----------
# Калибровка: подбираем коэффициенты по парам, где поток известен (условно 6 пар)
known = pd.DataFrame({
    "pop_a": [1.5, 1.2, 0.6, 1.0, 2.0, 0.8],
    "pop_b": [1.0, 0.5, 0.4, 1.3, 0.7, 0.6],
    "km":    [900, 1400, 700, 1800, 1100, 600],
    "pax":   [210e3, 70e3, 40e3, 95e3, 160e3, 60e3],   # пасс./год (условно)
})
# ln(pax) = ln(k) + a*ln(popA*popB) - b*ln(km)  -> обычная линейная регрессия (МНК)
X = np.column_stack([np.ones(len(known)),
                     np.log(known.pop_a * known.pop_b),
                     np.log(known.km)])
y = np.log(known.pax)
coef, *_ = np.linalg.lstsq(X, y, rcond=None)
pred = np.exp(X @ coef)
mape = np.mean(np.abs(pred - known.pax) / known.pax)
print(f"\n2) Гравитация: ln k={coef[0]:.2f}, a={coef[1]:.2f}, b={-coef[2]:.2f}; "
      f"средняя ошибка на известных парах (MAPE) = {mape:.0%}")

def gravity(pop_a, pop_b, km):
    return float(np.exp(coef[0] + coef[1] * np.log(pop_a * pop_b) + coef[2] * np.log(km)))

# ---------- 3. ДОЛЯ RED WINGS НА ПАРЕ: S-кривая по частотам ----------
def s_curve_share(our_freq, rival_freq, power=2.0):
    return our_freq**power / (our_freq**power + rival_freq**power)

# ---------- 4. МАРШРУТЫ, ПАССАЖИРЫ, САМОЛЁТЫ ----------
routes = pd.DataFrame({
    "route":      ["База–X", "База–Y", "База–Z"],
    "pop_a":      [1.5, 1.5, 1.5], "pop_b": [0.6, 1.0, 0.4],
    "km":         [800, 1500, 2600],
    "our_freq":   [7, 5, 3], "rival_freq": [0, 7, 0],   # рейсов в неделю
})
SSJ_GREEN_KM = 2300
SEATS, LF = 100, 0.85
routes["range_ok"] = routes.km <= SSJ_GREEN_KM
routes["demand"] = [gravity(r.pop_a, r.pop_b, r.km) for r in routes.itertuples()]
routes["share"] = [1.0 if r.rival_freq == 0 else s_curve_share(r.our_freq, r.rival_freq)
                   for r in routes.itertuples()]
routes["capacity"] = routes.our_freq * 2 * 52 * SEATS * LF            # предложение кресел с учётом загрузки
routes["pax"] = np.minimum(routes.demand * routes.share, routes.capacity)  # не больше, чем влезет
block_h = 0.5 + routes.km / 750
routes["hours_week"] = routes.our_freq * 2 * (block_h + 40 / 60)
ok = routes[routes.range_ok]
aircraft = ok.hours_week.sum() / (8 * 7) / 0.85
print("\n3-4) Маршруты:")
print(routes[["route", "km", "range_ok", "demand", "share", "pax", "hours_week"]]
      .round({"demand": -2, "share": 2, "pax": -2, "hours_week": 1}).to_string(index=False))
print(f"   Маршрут без зелёной дальности отброшен. Нужно самолётов: {aircraft:.1f} (+ резерв)")

# ---------- 5. ДОЛЯ РЫНКА И НЕОПРЕДЕЛЁННОСТЬ (Монте-Карло) ----------
MARKET = 108.9e6
base = ok.pax.sum()
print(f"\n5) Прирост доли (точечно): {base / MARKET * 100:.3f} п.п.")
sims = []
for _ in range(5000):
    lf = rng.uniform(0.70, 0.90)           # загрузка неизвестна точно
    dem_err = rng.lognormal(0, mape)        # ошибка модели спроса ~ как на калибровке
    pax = np.minimum(ok.demand * dem_err * ok.share, ok.our_freq * 2 * 52 * SEATS * lf)
    sims.append(pax.sum() / MARKET * 100)
p10, p50, p90 = np.percentile(sims, [10, 50, 90])
print(f"   Монте-Карло: P10={p10:.3f}  P50={p50:.3f}  P90={p90:.3f} п.п. "
      f"(«с вероятностью 90% прирост не меньше {p10:.3f} п.п.»)")
