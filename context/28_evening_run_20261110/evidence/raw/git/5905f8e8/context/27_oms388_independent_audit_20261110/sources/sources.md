# Sources pass (2026-11-10)

Scope: targeted check of the subsidy bridge behind OMS `base_sub` +388m RUB/year; no wider market ranking. Read owner snapshot and current pinned docs/assumptions. Checked official Federal Air Transport Agency (Rosaviatsiya / FAVT) materials.

1. [2026 routes under decision 22-68861-00481-R](https://favt.gov.ru/public/materials/f/c/d/d/4/fcdd4e01332f1ac475410a0a009a66be.pdf), FAVT PDF, accessed 2026-11-10. Table headers list airline, origin/destination airport, aircraft type, one-way special fare, and notes; rows are route-specific. Search excerpt: “Специальный тариф в одном направлении, руб.” (table header). The file in the owner snapshot is `data/raw/favt_subsidy_2026.csv`; it also carries service dates, flights/week, round trips and co-financing notes. This proves route-specific structure for the 2026 list, not eligibility/award for proposed OMS routes.
2. [Regional air transport subsidies, FAVT](https://favt.gov.ru/dejatelnost-vozdushnye-perevozki-subsidirovanie-regiony/), accessed 2026-11-10 (search snippet; page open timed out). Snippet for listed Red Wings routes includes EKB–Stavropol (01.05–30.09.2026) with 47.5% co-financing by each of two regions, EKB–Tomsk full-year with 25% regional co-financing, and EKB–Saratov multiple periods/rates. These official route-level terms contradict applying one universal rate as an established fact. Page access limitation: search-result extraction only; full page fetch timed out.
3. [FAVT notice on 2024 interregional routes](https://favt.gov.ru/novosti-novosti/?id=12149), accessed 2026-11-10. States that support for routes bypassing Moscow was implemented under Government Resolution No.1242 in 2024. This establishes historical program context only; it does not prove 2026 OMS eligibility.

## 1,773 / 1,638 inputs

Pinned `docs/24_hypotheses_comparison.md:24` derives 1,773 RUB/passenger as 7.98bn RUB divided by 4.5m passengers, citing T-J/RBK (13.05.2026) and Profile quoting Rosaviatsiya (11.03.2026). It explicitly says the sources do not establish the two figures refer to the same program. I did not find an authoritative primary document reconciling both numerator and denominator within this targeted pass (max 10 searches/openings): **UNKNOWN**. `data/assumptions/network.csv:43` reduces this proxy by 7.6% for 1,638; no primary source for that reduction was found in the inspected packet: **UNKNOWN**.

## Finding

The official evidence supports only conditional, route/operator/period-specific assistance. It does not substantiate treating every new OMS base_sub passenger as earning 1,773 RUB, and it does not substantiate +388m as profit. Preserve +388 as a conditional model result; qualify subsidy route by route against award, schedule period, aircraft/program rules and co-financing. Proposed routes without an evidenced award remain UNKNOWN. This sources pass does not value the economics or assess omitted costs.

Source extraction limit: up to 10 targeted internet opens/searches; further corroboration is for the address-specific follow-up. No private correspondence, session identifiers or personal contacts recorded.
