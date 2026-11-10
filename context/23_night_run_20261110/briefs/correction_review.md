# MR10: независимая проверка двух исправленных производных пакетов

Новый Sol 6.1 xhigh. Работа только в `context/23_night_run_20261110/correction_review/`, новая ветка `research/night-correction-review-20261110`. Без детей, новых тредов, сообщений коллегам, мониторинга, расписаний. Срок первого законченного пакета — 08:00 МСК, общий предел 10:00. Проверка, а не исправление исходников. Пользователь разрешил новый независимый review; finished children не переиспользуются.

## Закреплённые входы

- Root `f1774e1f66a9483fb618ca6003abd9dc4d8563e1`: `context/23_night_run_20261110/primary_lineage_correction/`.
- Root `87ee52de15c2bdf396d9c06ba600fd413d5ab4a8`: `context/23_night_run_20261110/cost_kover_timebase_correction/`.
- Primary original `17b4f348f15ea8695688d9435933cb4965568408`, bridge `abc09bbb8e62d3513749b60b252d4521997acfc3`, correct receipt `93fa5cf4a10ab67e05c93d19fc5375fc58ef9299:context/17_aircraft_route_review/evidence/sources.json`.
- Original source review `944b16ac2dcde846e29dac2d47e11e5143f9fc2b:context/23_night_run_20261110/source_join_review/`.
- Kover original `afadee35ebeefe54a05bdfc5b3e224a370f90e0a:context/23_night_run_20261110/cost_kover/`; author time epoch in `93fa5cf4a10ab67e05c93d19fc5375fc58ef9299:scripts/build_team_comparison.py`.
- Independent original Kover findings are already immutable in payload `af96da977becc161eac132f587e1fd3c4d6918a3:context/23_night_run_20261110/cost_kover_review/findings.json`. Its delivery metadata was pending at discovery. Use only this exact payload as supplied objection, not a moving branch or acceptance of the correction.

Read exact blobs using git show. Source/output manifests pin remaining inputs. No live owner folders. Public Site, report, dashboard, other owners and raw bytes remain unchanged. No force/merge/rebase/PR. No network research needed; fetch missing exact objects is allowed. Do not publish full raw, contacts or auth. Commit/push only safe own scope; final exact SHA must match ls-remote.

## A. SVX snapshot lineage correction

Reproduce the original mismatch: original registry refers to Nov8 context12 receipts while129 dated rows use Nov9 context17 hashes. Independently trace both source IDs to the correct pinned context17 receipts. Check capture date, raw hash, status and identity; absent byte size must remain NULL rather than reuse old size. Distinguish historical from current receipts.

Check all209 original dated cells and386 original mapping cells remain identical; explain which new columns are provenance. Check full source_snapshot identities and all foreign keys,129 affected rows,28 cards,58 mappings. Verify cardinality, no row loss/duplication or fabricated source. Check the6 exact-clock HOLD mappings remain held; no-match and context-only do not become supply or OD acceptance. Rebuild only inside your own scratch within scope if needed; never write into the correction package. A deterministic author replay alone is insufficient: use independent joins and representative literal receipts.

Determine whether this closes SJR-P2-001 for the derivative metadata only. Original17b CHANGES remains a historical verdict. New source-content, operation, legal capacity, year/clock/OD claims are outside scope. No requirement to redownload raw.

## B. Kover timebase and dependent admission

Establish author minutes are absolute from period_start UTC, including day offsets. Independently compute66 selected legs/132 events, departure and arrival, both days and rollover; verify original wrong events and corrected timestamps. Test half-open restrictions, day2, airport timezones and horizon checks using a separate small oracle.

Mandatory example H_UFA8 date2026-12-08/minute1885 must be2026-12-08T07:25Z; Dec8 window0→16 affected legs. Corrected day1+1440 UFA8 adjacent template conflicts23; UFA4 conflicts11 per scenario. Verify retained planning-tail IDs without inventing recovery resources. Global alternative rotations/tails are not proven impossible by the adjacent-template test.

Check40 original day1 arithmetic rows match BEFORE admission gating. The4 unresolved delay cases must not present served-all, unserved counts, realizable contribution or cash as accepted plan. Original algebra can remain clearly hypothetical_if_recovered; verify consumers can distinguish NULL admitted fields from hypothetical numbers. Inspect scenario_summary, affected_journeys, physical_leg_status and cash_fixture together. Original no-kover bytes and unaffected day1 cancellation values stay unchanged. Check source_commit/input_set/run provenance points to the separate correction and original.

Independent day1 cost/tariff/raw review is another running task on afadee: do not duplicate it, extend its scope, or inherit its eventual result. Here review only the time axis, affected sets, calendar conflicts, conservation/admission consequences and preservation of unaffected values. Full dispatch, actual fleet, contract costs and recovery economics remain UNKNOWN.

## Deliverable and decision

Create report.md, findings.json, handoff.json, source_manifest.json, output_manifest.json, concise reproducible independent checks and counterexamples. APPROVE_SCOPED or CHANGES separately for A/B; exact P1/P2 file:line and smallest fix. Preserve unresolved boundaries even if fixes pass. List personal checks separately from supplied review claims. Do not count hashes as proof of market or operation.

Read contract.md in prepared checkout. No children or all-to-all communication. Do not poll other work. Finish bounded work, push safe package, verify exact remote SHA, return a short handoff. No automatic next cycle.
