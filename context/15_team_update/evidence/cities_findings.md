# City data audit — 2026-11-09

Sources audited: `data/processed/longlist.csv`, `data/manual/longlist_manual.csv`, `data/processed/kover_days.csv`, `context/11_practical_screening/{city_matrix.csv,sources.json}`, `context/12_network_economics/ufa_check.md`, `docs/22_data_sources_longlist.md`, `data/raw/SOURCES.md`, `src/longlist_data.py`, and `src/longlist_score.py`.

The 20-city table is `data/processed/longlist.csv` joined by IATA with `data/processed/kover_days.csv` for closure-days. Those existing machine-readable files supply airport/city, 2025 passenger total and qualifier/source URL, 2021 catchment, direct destinations, carrier field, transfer notes, MCT proxy, and closure-day windows. Direct-network data is Tochno/Aviastats routes for June–December 2026; at the 2026-11-09 cut, the period partly lies in the future, so counts are scheduled/listed dataset values, not evidence that every flight operated. `gap_pop` counts population in reachable cities lacking direct flight and a train under 12 h; it measures access/friction, not air demand. Catchment sums 2021 populations of cities above 100,000 within 75 km of airport; it is not a full settlement catchment. Zero route/day values are observed zeros under dataset method; blank/“проверить”/UNKNOWN are missing evidence and remain distinct.

Closure-day columns cover H1 2025, H2 2025, H1 2026, Jan–Oct 2026 and rolling 365 days in `kover_days.csv`; they count dates with Rosaviatsiya restriction posts, a lower bound on publication days, not closure duration or cancellation probability. Coverage begins 2024-11-06 and ends 2026-11-09.

## Decisive checks / unresolved conflicts

- CEK passenger count conflict: 2,160,421 in existing longlist versus 2,166,689 in another reported tally; transit/inclusion definition was not evidenced, so preserve both, do not select one.
- TJM: the `competitor_hub=0` coding is not proof Utair is absent. Utair is a known local operator, but evidence reviewed does not establish formal base status or its schedule share. Keep base-carrier quantitative strength UNKNOWN.
- CEK/TJM/PEE: RRJ-95 acceptance, line maintenance/operational support, and airport operating regime were not established from the collected primary sources. Keep UNKNOWN; do not infer technical capability from runway length or airport certification generally.
- No evidence for contractually free aircraft/crew/maintenance capacity; UNKNOWN.
- Existing network counts do not establish completed operation over the full June–December 2026 period.
- Ufa: existing `ufa_check.md` remains useful feasibility evidence but does not establish a comparative city winner or contractually available capacity.

Full 20-city audit table is materialized in the existing `longlist.csv` with the closure series in `kover_days.csv`; both are intentionally left untouched under task scope. For changes/additions, see `cities_input_updates.csv`.
