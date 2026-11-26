#!/usr/bin/env python3
"""Build colleague integration/reconciliation pack in context/40_swarm_pricing_research_20261113/colleague_bridge/ without touching colleague directories or P09/."""
import io
import json
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/a/agent-audit-2026-09/case_championship")
BASE = ROOT / "context" / "40_swarm_pricing_research_20261113"
OUT = BASE / "colleague_bridge"
OUT.mkdir(parents=True, exist_ok=True)

mc = pd.read_csv(BASE / "market_competition_209.csv")
rps = pd.read_csv(BASE / "recomputed_programmes_summary.csv")
yh = pd.read_csv(BASE / "yandex_hub_departures.csv")
sub26 = pd.read_csv(BASE / "swarm" / "subsidies_2026.csv")
rp = pd.read_csv(ROOT / "context" / "42_consensus_strategy_20261113" / "route_evidence" / "route_passports.csv")
with open(ROOT / "context" / "42_consensus_strategy_20261113" / "consensus.json", encoding="utf-8") as f:
    consensus = json.load(f)


def sorted_pair(a: str, b: str) -> str:
    return "-".join(sorted([a.strip(), b.strip()]))


def hub_direct_check(a: str, b: str):
    """Check cached yandex_hub_departures.csv across all 22 hubs, resolving MOW to Moscow city titles."""
    city_kw = {
        "MOW": ["Москва"],
        "ZIA": ["Жуковский"],
        "AER": ["Сочи"],
        "VOG": ["Волгоград"],
        "GSV": ["Саратов"],
        "MRV": ["Минеральные Воды"],
        "OMS": ["Омск"],
        "IKT": ["Иркутск"],
        "GOJ": ["Нижний Новгород"],
        "KUF": ["Самара"],
        "SVX": ["Екатеринбург"],
        "KJA": ["Красноярск"],
        "TJM": ["Тюмень"],
    }
    found = []
    for st, dst in [(a, b), (b, a)]:
        if st in set(yh["station"]) and dst in city_kw:
            sub = yh[yh["station"] == st]
            pat = "|".join(city_kw[dst])
            m = sub[sub["title"].str.contains(pat, case=False, na=False)]
            if len(m) > 0:
                carriers = sorted(set(m["carrier_iata"].dropna().astype(str)))
                found.append((st, dst, len(m), m["date"].nunique(), carriers))
    return found


def as_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"true", "1", "yes"}


# 1. Reconcile origin/шаг-1 route_competitors_todo.csv
todo_raw = subprocess.check_output(
    ["git", "show", "origin/шаг-1:data/manual/route_competitors_todo.csv"], cwd=ROOT
).decode("utf-8")
todo = pd.read_csv(io.StringIO(todo_raw))
todo["pair"] = todo.apply(lambda r: sorted_pair(r["a"], r["b"]), axis=1)
todo["p09_lookup_pair"] = todo["pair"].apply(
    lambda p: p.replace("MOW", "ZIA") if "MOW" in p else p
)
# fix sorting after replacing MOW -> ZIA
todo["p09_lookup_pair"] = todo["p09_lookup_pair"].apply(
    lambda p: sorted_pair(*p.split("-"))
)

mc_idx = mc.set_index("pair")
rows_todo = []
for _, r in todo.iterrows():
    p = r["pair"]
    lp = r["p09_lookup_pair"]
    exact_match = p in mc_idx.index
    zia_match = (not exact_match) and ("MOW" in p) and (lp in mc_idx.index)
    mow_hub = hub_direct_check(r["a"], r["b"])
    if exact_match:
        m = mc_idx.loc[p]
        if m["direct_competitor_count"] > 0:
            api_status = "прямой рейс"
        elif pd.notna(m["F_comp_transfer_20kg"]):
            api_status = "с пересадкой (подтв. TP)"
        else:
            api_status = "нет данных API"
        rows_todo.append({
            "a": r["a"],
            "b": r["b"],
            "city_a": r["city_a"],
            "city_b": r["city_b"],
            "now_shag1": r["now"],
            "p40_match_scope": "exact_pair",
            "p40_status": api_status,
            "direct_competitors": m["direct_competitors"],
            "connecting_competitors": m["connecting_competitors"],
            "competitor_daily_seats": round(float(m["competitor_daily_seats"]), 1),
            "F_comp_direct_20kg": None if pd.isna(m["F_comp_direct_20kg"]) else round(float(m["F_comp_direct_20kg"]), 0),
            "F_comp_transfer_20kg": None if pd.notna(m["F_comp_transfer_20kg"]) is False else round(float(m["F_comp_transfer_20kg"]), 0),
            "subsidized_2026": as_bool(m["subsidized_2026"]),
            "subsidized_carriers_2026": m["subsidized_carriers_2026"],
            "W_comp_2028": round(float(m["W_comp_2028"]), 3),
        })
    else:
        hub_carriers = sorted({c for item in mow_hub for c in item[4]})
        hub_flights = sum(item[2] for item in mow_hub)
        scope = "yandex_hub_city_check" if mow_hub else ("zia_proxy_only" if zia_match else "outside_p09_209")
        status = f"прямой по Яндексу (MOW город: {','.join(hub_carriers)})" if (mow_hub and "MOW" in p) else (
            f"прямой по Яндексу ({','.join(hub_carriers)})" if mow_hub else "вне 209 пар P09 (нужен добор TP при включении)"
        )
        rows_todo.append({
            "a": r["a"],
            "b": r["b"],
            "city_a": r["city_a"],
            "city_b": r["city_b"],
            "now_shag1": r["now"],
            "p40_match_scope": scope,
            "p40_status": status,
            "direct_competitors": json.dumps(hub_carriers, ensure_ascii=False) if hub_carriers else "[]",
            "connecting_competitors": "",
            "competitor_daily_seats": None,
            "F_comp_direct_20kg": None,
            "F_comp_transfer_20kg": None,
            "subsidized_2026": None,
            "subsidized_carriers_2026": "",
            "W_comp_2028": None,
        })

todo_df = pd.DataFrame(rows_todo)
todo_df.to_csv(OUT / "route_competitors_todo_verified.csv", index=False)

# 2. Audit all 12 pairs of context/42_consensus_strategy_20261113
consensus_pairs = [
    ("MOW-AER", "T1", "Moscow triangle 1", "AER-ZIA", "AER", "MOW"),
    ("AER-VOG", "T1", "Moscow triangle 1", "AER-VOG", "AER", "VOG"),
    ("MOW-VOG", "T1", "Moscow triangle 1", "VOG-ZIA", "VOG", "MOW"),
    ("MOW-GSV", "T2", "Moscow triangle 2", "GSV-ZIA", "GSV", "MOW"),
    ("GSV-MRV", "T2", "Moscow triangle 2", "GSV-MRV", "GSV", "MRV"),
    ("MOW-MRV", "T2", "Moscow triangle 2", "MRV-ZIA", "MRV", "MOW"),
    ("OMS-MOW", "OMS_pilot", "Omsk pilot (3->5 RT)", "OMS-ZIA", "OMS", "MOW"),
    ("OMS-IKT", "OMS_pilot", "Omsk pilot (3->5 RT)", "IKT-OMS", "OMS", "IKT"),
    ("OMS-GOJ", "OMS_main", "Omsk main (3 RT)", "GOJ-OMS", "OMS", "GOJ"),
    ("OMS-VOG", "OMS_main", "Omsk main (3 RT)", "OMS-VOG", "OMS", "VOG"),
    ("OMS-KUF", "OMS_extra", "Omsk extra (3 RT)", "KUF-OMS", "OMS", "KUF"),
    ("OMS-GSV", "OMS_extra", "Omsk extra (3 RT)", "GSV-OMS", "OMS", "GSV"),
]
rp_idx = rp.set_index("pair_id")
cons_rows = []
for cpair, branch, stage, p09_pair, a_code, b_code in consensus_pairs:
    rp_row = rp_idx.loc[cpair].to_dict() if cpair in rp_idx.index else {}
    hub_info = hub_direct_check(a_code, b_code)
    hub_carriers = sorted({c for x in hub_info for c in x[4]})
    hub_flights_total = sum(x[2] for x in hub_info)
    if p09_pair in mc_idx.index:
        m = mc_idx.loc[p09_pair]
        p09_direct_cnt = int(m["direct_competitor_count"])
        p09_direct_list = m["direct_competitors"]
        p09_daily_seats = round(float(m["competitor_daily_seats"]), 1)
        f_dir = None if pd.isna(m["F_comp_direct_20kg"]) else round(float(m["F_comp_direct_20kg"]), 0)
        f_tr = None if pd.isna(m["F_comp_transfer_20kg"]) else round(float(m["F_comp_transfer_20kg"]), 0)
        sub_flag = as_bool(m["subsidized_2026"])
        sub_car = m["subsidized_carriers_2026"]
        w28 = round(float(m["W_comp_2028"]), 3)
        in_p09 = True
    else:
        p09_direct_cnt = None
        p09_direct_list = None
        p09_daily_seats = None
        f_dir = None
        f_tr = None
        sub_flag = None
        sub_car = None
        w28 = None
        in_p09 = False
    if "MOW" in cpair and hub_carriers:
        note = (
            f"КРИТИЧНО: P09 кодировал Москву как {p09_pair} (0 прямых из ZIA, пересадочный тариф ~{int(f_tr)} ₽), "
            f"тогда как по городу Москва (SVO/DME/VKO) Яндекс фиксирует {hub_flights_total} прямых рейсов за 2 даты ({','.join(hub_carriers)})."
        )
    elif cpair == "OMS-IKT":
        note = f"Вне P09 209 пар; но по yandex_hub_departures подтверждён прямой конкурент S7 ({hub_flights_total} рейсов за 2 даты в оба конца)."
    elif not in_p09:
        note = "Вне P09 209 пар; прямых в 2-дневном срезе Яндекса из OMS/VOG/GOJ не зафиксировано — для совместного PnL требуется добор цен TP."
    else:
        note = (
            f"Полностью в P09 ({p09_pair}): прямых конкурентов={p09_direct_cnt}, "
            f"ориентир пересадки F_comp_transfer_20kg={int(f_tr) if f_tr else 'N/A'} ₽, субсидия 2026={sub_flag}."
        )
    cons_rows.append({
        "consensus_pair": cpair,
        "branch": branch,
        "stage": stage,
        "p09_manifest_pair": p09_pair,
        "in_p09_209": in_p09,
        "p09_direct_competitor_count": p09_direct_cnt,
        "p09_direct_competitors": p09_direct_list,
        "yandex_city_level_direct_carriers": json.dumps(hub_carriers, ensure_ascii=False),
        "yandex_city_level_flights_2d": hub_flights_total,
        "p09_F_comp_direct_20kg_rub": f_dir,
        "p09_F_comp_transfer_20kg_rub": f_tr,
        "author_fare_model_rub": rp_row.get("author_fare_model_rub", None),
        "author_result_mln_year": rp_row.get("author_result_mln_year", None),
        "subsidized_2026_in_p09": sub_flag,
        "W_comp_2028_in_p09": w28,
        "reconciliation_note": note,
    })

cons_df = pd.DataFrame(cons_rows)
cons_df.to_csv(OUT / "consensus_12_pairs_competition_audit.csv", index=False)

# 3. Audit P38 top5.csv
p38_raw = subprocess.check_output(
    ["git", "show", "origin/research/direct-growth-delay-cargo-20261112:context/38_direct_strategy_20261113/final/top5.csv"],
    cwd=ROOT,
).decode("utf-8")
p38 = pd.read_csv(io.StringIO(p38_raw))
p38_rows = []
for _, r in p38.iterrows():
    p = sorted_pair(*r["pair"].split("-"))
    in_p09 = p in mc_idx.index
    hub_info = hub_direct_check(*r["pair"].split("-"))
    hub_carriers = sorted({c for x in hub_info for c in x[4]})
    if in_p09:
        m = mc_idx.loc[p]
        p38_rows.append({
            "p38_rank": int(r["rank"]),
            "pair": r["pair"],
            "p09_pair": p,
            "in_p09_209": True,
            "p38_competitor": r["competitor"],
            "p40_direct_competitors": m["direct_competitors"],
            "p40_daily_seats": round(float(m["competitor_daily_seats"]), 1),
            "p40_F_comp_direct_20kg_rub": None if pd.isna(m["F_comp_direct_20kg"]) else round(float(m["F_comp_direct_20kg"]), 0),
            "p40_competitor_var_floor_rub": None if pd.isna(m["competitor_var_floor"]) else round(float(m["competitor_var_floor"]), 0),
            "p40_competitor_full_floor_rub": None if pd.isna(m["competitor_full_floor"]) else round(float(m["competitor_full_floor"]), 0),
            "p40_subsidized_2026": as_bool(m["subsidized_2026"]),
            "p40_subsidized_carriers_2026": m["subsidized_carriers_2026"],
            "p40_W_comp_2028": round(float(m["W_comp_2028"]), 3),
        })
    else:
        p38_rows.append({
            "p38_rank": int(r["rank"]),
            "pair": r["pair"],
            "p09_pair": p,
            "in_p09_209": False,
            "p38_competitor": r["competitor"],
            "p40_direct_competitors": json.dumps(hub_carriers, ensure_ascii=False),
            "p40_daily_seats": None,
            "p40_F_comp_direct_20kg_rub": None,
            "p40_competitor_var_floor_rub": None,
            "p40_competitor_full_floor_rub": None,
            "p40_subsidized_2026": None,
            "p40_subsidized_carriers_2026": "",
            "p40_W_comp_2028": None,
        })

p38_df = pd.DataFrame(p38_rows)
p38_df.to_csv(OUT / "p38_top5_competition_audit.csv", index=False)

# 4. Programme metrics comparison for Consensus-relevant hubs
hub_progs = [
    "MRV_SEASONAL", "AER_SEASONAL", "AER_HYBRID", "KUF_RADIAL",
    "VOG_RADIAL", "VOG_HYBRID", "OMS_RADIAL", "OMS_HYBRID", "OMS_HUB",
    "GOJ_RADIAL", "GSV_RADIAL", "SVX_RADIAL", "SVX_BANK9",
]
sub_rps = rps[
    rps["programme_id"].isin(hub_progs)
    & rps["config"].isin(["p09_legacy_check", "comp_market_base", "comp_market_cautious", "comp_expansion_stress_2028"])
].copy()
pivot_rows = []
for pid in hub_progs:
    d = {"programme_id": pid}
    for cfg, short in [
        ("p09_legacy_check", "p09"),
        ("comp_market_base", "base"),
        ("comp_market_cautious", "cautious"),
        ("comp_expansion_stress_2028", "exp2028"),
    ]:
        row = sub_rps[(sub_rps["programme_id"] == pid) & (sub_rps["config"] == cfg)].iloc[0]
        d[f"{short}_rank"] = int(row["rank_known_subtotal"])
        d[f"{short}_delta_mln"] = round(float(row["delta_known_operating_subtotal"]) / 1e6, 1)
        d[f"{short}_trips_k"] = round(float(row["delta_journeys"]) / 1e3, 1)
        d[f"{short}_lf_pct"] = round(float(row["flight_load_factor"]) * 100.0, 1)
        d[f"{short}_cash_peak_mln"] = round(float(row["known_components_incremental_peak_diagnostic"]) / 1e6, 1)
    pivot_rows.append(d)
pd.DataFrame(pivot_rows).to_csv(OUT / "consensus_hubs_p09_vs_market.csv", index=False)

# 5. Drop-in colleague manifest snippet for origin/шаг-1
manifest_snippet = {
    "p40_summary": {
        "source_dir": "context/40_swarm_pricing_research_20261113",
        "path": "context/40_swarm_pricing_research_20261113/recomputed_programmes_summary.csv",
    },
    "p40_market_209": {
        "source_dir": "context/40_swarm_pricing_research_20261113",
        "path": "context/40_swarm_pricing_research_20261113/market_competition_209.csv",
    },
    "p40_todo_verified": {
        "source_dir": "context/40_swarm_pricing_research_20261113",
        "path": "context/40_swarm_pricing_research_20261113/colleague_bridge/route_competitors_todo_verified.csv",
    },
    "p40_consensus_audit": {
        "source_dir": "context/40_swarm_pricing_research_20261113",
        "path": "context/40_swarm_pricing_research_20261113/colleague_bridge/consensus_12_pairs_competition_audit.csv",
    },
    "p40_p38_audit": {
        "source_dir": "context/40_swarm_pricing_research_20261113",
        "path": "context/40_swarm_pricing_research_20261113/colleague_bridge/p38_top5_competition_audit.csv",
    },
    "p40_cashflow_diag": {
        "source_dir": "context/40_swarm_pricing_research_20261113",
        "path": "context/40_swarm_pricing_research_20261113/model_outputs/cashflow_diagnostics_summary.csv",
    },
}
with open(OUT / "p40_colleague_manifest_snippet.json", "w", encoding="utf-8") as f:
    json.dump(manifest_snippet, f, ensure_ascii=False, indent=2)

# 6. COLLEAGUE_SYNC_RU.md
disagreements = todo_df[
    (todo_df["p40_match_scope"] == "exact_pair")
    & (
        (todo_df["now_shag1"].str.contains("прямой") & ~todo_df["p40_status"].str.contains("прямой"))
        | (~todo_df["now_shag1"].str.contains("прямой") & todo_df["p40_status"].str.contains("прямой"))
        | (todo_df["now_shag1"].str.contains("нет") & todo_df["p40_status"].str.contains("пересад"))
    )
]
md = f"""# Сверка расчётов P40 с ветками коллег (`42_consensus_strategy`, `origin/шаг-1`, `P38`, `P39`)

*Все экономические величины по `P09` — частичный известный операционный subtotal к пересчитанному `KEEP`, млн ₽, период 2027–2028, в ценах 2026 г., при `RW_SUPPORT_NEW = 0` (`full company P&L / lease / launch costs = UNKNOWN`). Сценарии `comp_market_base` / `comp_market_cautious` / `comp_expansion_stress_2028` — условные оценки, а не вероятности.*

## 1. Главный мост с `context/42_consensus_strategy_20261113` (консенсус 12 пар)

В `consensus.json` коллеги прямо зафиксировали: **«joint new PnL NOT_RUN»** и **«competition список неполный»**, а также **«unresolved: physical Moscow airport»**. Наш пакет закрывает оба пробела по живым данным API (`market_competition_209.csv`, `yandex_hub_departures.csv`) и пересчёту хабов:

1. **Критическая поправка по Москве (`ZIA` vs `MOW`)**:
   - В `P09` все 5 московских пар из консенсуса (`AER-ZIA`, `VOG-ZIA`, `GSV-ZIA`, `MRV-ZIA`, `OMS-ZIA`) зашиты именно на **Жуковский (`ZIA`)**, где `0` прямых конкурентов и высокий пересадочный якорь (`31.0–34.4 тыс. ₽` с 20 кг багажом).
   - Но при выборе **общегородской Москвы (`SVO`/`DME`/`VKO`)** наши выгрузки `yandex_hub_departures.csv` фиксируют жёсткую прямую конкуренцию на **всех пяти** направлениях (`SU`, `DP`, `S7`, `U6`, `FV`, `UT`, `Y7`): `AER-MOW` (26 вылетов/2 даты), `MRV-MOW` (24 вылета/2 даты), `VOG-MOW` (14), `GSV-MOW` (10), `OMS-MOW` (9). Поэтому без подтверждения слотов именно в `ZIA` переносить ZIA-рентабельность на `MOW` нельзя.
2. **Почему треугольники через `VOG` и `GSV` устойчивы, а омская база (`OMS`) уязвима в осторожном спросе**:
   - **`VOG_RADIAL`** — единственная Парето-устойчивая программа во всех трёх рыночных режимах: **#12 в Базе (`+545.2 млн ₽`)**, **#1 в Осторожном (`+298.5 млн ₽`, пик кассового разрыва `0.0 млн`)**, **#1 в Стрессе экспансии 2028 (`+293.7 млн ₽`, пик `0.0 млн`)**.
   - **`GOJ_RADIAL`** (#2 в Осторожном `+190.9 млн`, #2 в Экспансии `+184.7 млн`) и **`GSV_RADIAL`** (#4 `+105.1 млн`, #5 `+100.5 млн`) также держат плюс при падении спроса — это подтверждает выбор `VOG`, `GSV`, `GOJ` в консенсусе коллег.
   - Зато **`OMS_RADIAL`** падает с **`+540.1 млн ₽`** (#13 в Базе, LF `50.2%`) до **`-192.2 млн ₽`** (#29 в Осторожном, LF `23.6%`, кассовый пик `136.7 млн ₽`) и **`-195.5 млн ₽`** в Экспансии-2028 (`OMS_HYBRID` `-433.2 млн`, `OMS_HUB` `-563.5 млн`). Для защиты омской базы критически важны именно недорогие «опорные» споки (`OMS-GOJ`, `OMS-VOG`) и контроль прямой конкуренции **`S7` на `OMS-IKT`** (подтверждён в Яндекс-выгрузке).
3. **Покрытие 12 пар консенсуса** (полная таблица — [consensus_12_pairs_competition_audit.csv](consensus_12_pairs_competition_audit.csv)):
   - **8 из 12 пар** уже полностью обсчитаны в нашей базе 209 пар (`AER-VOG`, `GSV-MRV`, `KUF-OMS` + 5 `*-ZIA`).
   - **4 омские пары** (`OMS-IKT`, `OMS-GOJ`, `OMS-VOG`, `OMS-GSV`) не входили в матрицу 209 пар `P09`; по `OMS-IKT` прямой конкурент `S7` подтверждён через `yandex_hub_departures.csv`, для совместного PnL по `consensus.json` достаточно добрать котировки `Travelpayouts` только по этим 4 парам.

## 2. Сверка с `origin/шаг-1` (`route_competitors_todo.csv` и `fetch_colleague_research.py`)

- Проверена вся таблица `data/manual/route_competitors_todo.csv` (205 строк) — экспорт в точном формате готов в [route_competitors_todo_verified.csv](route_competitors_todo_verified.csv).
- По **84 точным совпадениям** с нашими 209 парами найдено **{len(disagreements)} содержательных расхождений**:
  - `BAX-KJA`: в `шаг-1` стояло «с пересадкой: Новосибирск», а живой API зафиксировал прямой **`KV` (КрасАвиа, ~11,917 ₽)**.
  - 9 пар (`AER-VOG`, `CEK-IJK`, `CEK-NOJ`, `HMA-PEE`, `KUF-VOG`, `MQF-SGC`, `MRV-VOG`, `OMS-PEE`, `REN-TJM`): в `шаг-1` стояло «сейчас авиамаршрута нет», но `Travelpayouts` подтверждает рабочие пересадочные маршруты (`13.8–28.8 тыс. ₽` с 20 кг), которые ограничивают ценовой потолок.
  - 2 пары (`AER-REN`, `GOJ-REN`): в `шаг-1` помечены как «прямой рейс», но в наших зимне-весенних окнах зафиксированы только пересадки (`17.3–17.6 тыс. ₽`, вероятна сезонность).
- Для встраивания в панель `origin/шаг-1` подготовлен готовый фрагмент манифеста: [p40_colleague_manifest_snippet.json](p40_colleague_manifest_snippet.json).

## 3. Сверка с веткой `origin/research/direct-growth-delay-cargo-20261112` (`P38` и `P39`)

- **`P38` (`top5.csv` — прямые/треугольные цепочки из `SVX`)** — см. [p38_top5_competition_audit.csv](p38_top5_competition_audit.csv):
  - `MRV-SVX` (#1 в `P38`): в нашей базе 209 — **`SU` + `U6` (336 кресел/сутки)**, медиана `13,400 ₽` (var floor `6,694 ₽`, full floor `9,882 ₽`), `W_comp_2028 = 0.535`. Это объясняет, почему в `P09` сам хаб `SVX_RADIAL` просел с `+681.7 млн` (#15) до `+394.4 млн` (#25) в Базе и **`-15.2 млн ₽`** в Экспансии-2028 (риск кластера `SU` «Поволжье и Урал»).
  - `KJA-SVX` (#2 в `P38`): **`FV` (130 кресел/сутки)**, `15,241 ₽`, `W_comp_2028 = 0.413`.
  - `MRV-TJM` (#5 в `P38`): **`A4` + `UT` + `YC` (73.6 кресел/сутки)**, `16,843 ₽`, **субсидия 2026 (`A4`)**.
  - `GOJ-KJA` и `IKT-SVX` вне 209 пар `P09` (на `IKT-SVX` у `P38` зафиксирован `S7`, в 2-дневном срезе Яндекса отсутствовал — частотность не ежедневная).
- **`P39` (ставки аренды SSJ100 и прайс аэропорта Омск-2026)**:
  - Полностью совместимы: в наших сценариях `RW_SUPPORT_NEW = 0` и лизинг/поддержка ВС не включены в частичный subtotal (`MISSING_COST_HEADROOM`), поэтому предупреждение `P39` (не складывать построчные тарифы `tarifs_rus_20260821.pdf` поверх агрегированного `ground 96 089 / 115 307 ₽/рейс` без детализации) сохраняется без двойного счёта.
"""
with open(OUT / "COLLEAGUE_SYNC_RU.md", "w", encoding="utf-8") as f:
    f.write(md)

print("Built colleague_bridge files:", [p.name for p in sorted(OUT.iterdir())])
