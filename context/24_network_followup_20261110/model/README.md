# Fixed-network first pass

**BASELINE_ONLY / PASS_SCOPED.** The twelve common rows were reconciled to exact methods exports and replayed on fixed ledger inputs. No new research finding has been integrated. The single final targeted integration round remains available.

Read `model_audit.md` for findings and limits, `baseline_comparison.csv` for all twelve C/N × base/cautious rows, `validation.json` for replay coverage, and `adapter_validation.json` for numerical and admission checks. `source_manifest.json` binds immutable historical snapshots and the five exact current-owner exports in `../owner_snapshot/`. `output_manifest.json` hashes the direct deliverables.

`freeze/network_contract.json` is the initial contract. `network_contract.json` adds verified supply bindings. Only D_SVX8, H_UFA_4 and H_UFA_8 are compared for 7–13 December 2026. `dated_legs.csv` and `frequencies.csv` retain dates, aircraft labels, directed frequencies and the absolute UTC epoch. Working aircraft 1/2/4 and the conditional reserve are model assumptions, not available tails. Results are author-model contribution before fleet/base/opportunity; full PnL and peak cash remain NULL.

Offline reproduction, from the real repository root:

```sh
python3 context/24_network_followup_20261110/model/build_baseline.py
python3 context/24_network_followup_20261110/model/prepare_admission.py
python3 context/24_network_followup_20261110/model/verify_model.py
```

Own code is confined to `model/*.py`; historical `.py` snapshots are evidence. Upstream `main`, original network generators, owner optimizer and ranking do not run. Stage1, weights, owner source, dashboard and protected files are untouched. No fetch, checkout, reset, worktree, commit, push or agent messaging is part of this pass.

For the final round use `integration_contract.json`, `input_admission_template.csv` and `final_integration_package.template.json`. Each of the three researchers must supply a byte-hashed FINAL manifest with every finding ID; every finding gets direct_input/proxy/scenario_only/rejected_missing_scope admission, separate source/period/unit/tax/reliability and explicit apply=true/false. Context-only findings may be admitted without a numeric update; incomplete scope stays rejected. `input_admission.csv` describes the frozen inputs; `gap_map.csv` and `owner_handoff.csv` describe pending changes.

The adapter defaults to a non-writing dry run:

```sh
python3 context/24_network_followup_20261110/model/integrate_once.py --package model/<final-package.json>
```

The separate final round is recorded only with `--apply`; it writes `model/final_round/`, preserves the baseline and owner files, and refuses another consumed round. The pending template is intentionally rejected. Do not run it on unfinished research. Source hash checks verify supplied bytes; they are not an independent market/source approval.

Supported numerical changes keep the same offer support: symmetric per-pair weekly demand, net new fare once (old-RW fare separately frozen), and shared fuel/uplift/hourly/airport/deicing/passenger costs on every flown leg and both recipes. One-direction observed OD cannot replace the symmetric pair as fact; use an explicit proxy/scenario or retain it as context. Airport totals, route segments and offer seats cannot become paid endpoint demand. Retail quotes require explicit net reconciliation and scenario admission. Supply, allocator, capture/migration policy, full budget, donor assignment and ranking changes are outside the adapter.
