"""Пересадочный потенциал города-кандидата: насколько удачно он стоит между городами, у которых нет прямого рейса.

Идея — «география связанности» коллег (context/11_practical_screening): хаб хорош, если через него
пары без прямого рейса соединяются почти без крюка. У коллег — 12 тестовых пар; здесь — все пары аэропортов.
Для хаба H берём пары X — Y, где:
  оба аэропорта в зелёной зоне SSJ от H и не ближе spoke_min_km (src/rules.py, data/assumptions/network.csv);
  между X и Y нет прямого рейса, оба открыты, X — Y не короче transfer_min_km;
  путь через H длиннее прямого не больше чем в transfer_max_circuity раз.
Значение — сумма оценок спроса этих пар по модели шага 2 (базовый сценарий; масштаб рынка, не прогноз продаж).
Параметры — те же, что у модели сети (data/assumptions/network.csv), чтобы критерий и шаг 3 считали одинаково.

Выход: data/processed/transfer_potential.csv
Запуск: python src/transfer_potential.py   (после src/demand_model.py)
"""
from pathlib import Path

import pandas as pd

import network_model as nm
from airports_meta import CLOSED

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"


def main():
    A = nm.load_assumptions()["base"]
    D = nm.Demand()
    nodes = [x for x in D.n.index if x not in CLOSED]
    cand = pd.read_csv(ROOT / "context/07_verification/terra_cities_review/corrected_cities.csv").iata
    rows = []
    for H in cand:
        if H not in D.n.index:
            continue
        reach = [X for X in nodes if X != H and A["spoke_min_km"] <= D.km(H, X) <= D.green(H, X)]
        dem = n = 0
        top = []
        for i, X in enumerate(reach):
            for Y in reach[i + 1:]:
                dxy = D.km(X, Y)
                if dxy < A["transfer_min_km"] or D.has_direct(X, Y):
                    continue
                if (D.km(H, X) + D.km(H, Y)) / dxy > A["transfer_max_circuity"]:
                    continue
                v = D.get(X, Y, "base")
                dem += v
                n += 1
                top.append((v, X, Y))
        top.sort(reverse=True)
        rows.append({"iata": H, "transfer_pairs": n, "transfer_demand_base": round(dem),
                     "top_pairs": "; ".join(f"{X}–{Y} {v / 1000:.0f} тыс." for v, X, Y in top[:5])})
    out = pd.DataFrame(rows)
    out.to_csv(P / "transfer_potential.csv", index=False, encoding="utf-8")
    print(out.sort_values("transfer_demand_base", ascending=False).to_string(index=False))


if __name__ == "__main__":
    main()
