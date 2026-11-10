# Source content audit — partial substantive result

Pin: `14354571b90545cd0618548481a857bf6b388d4a`. Only this directory was written. No model parameters, weights, cities, strategy, owner data, checkout, commits or messages changed.

Population: all **371 source IDs / 3511 claim IDs** retained. Whole JSON rows decomposed into **62,283 fields**, including context/metadata and empty fields; this is deliberately not a count of 62,283 independent numerical facts. `file_coverage.csv` gives per-file denominators and numeric-field counts. Parent claims remain unverified even where one field is confirmed. Explicit model/scenario rows receive assumption status without implying verified calibration or arithmetic.

Actual substantive acceptance: **29 atomic values**: 18 historical annual airport totals matched to the pinned cp1251 Rosaviation raw table, official Kurumoch 2024/2025 and Ufa 2025 throughput, and matching Omsk 2025 airport destination counts. Repeated fields on multiple source edges remain separate atoms. `confirmed_extractions.csv` contains the precise evidence; there is no promotion from legacy VERIFIED labels. Kurumoch's 3.57 million is rounded, not an exact passenger headcount. Airport destination counts measure airport segments, not realised endpoint OD demand.

Full-body acquisition and text parsing: 331 external catalog entries yielded at least one complete successful body (including five composite URL entries split into children); 14 internal documents read at the pin. 27 document entries have an error or incomplete child retrieval. These are acquisition/read counts, **not 331 semantically verified sources**. Error details, timestamp, URL normalization, child statuses, bytes and SHA are in `source_documents.csv`. Live retrieval is a later vintage than the model pin and cannot authenticate a vanished historical schedule. HTTP 200 can also return a generic page; literal-number candidates remain unverified.

`source_excerpts.csv` publishes at most 20 quoted words per source; full bodies are kept only in ignored `.sourcescache/`. Extracts are navigation/article samples and never imply semantic acceptance. `extraction_evidence.csv` contains factual numeric candidates with hashes and claim dimensions, explicitly not confirmations. Licenses are inherited declarations from inventory, not independently cleared rights.

Findings: whole-row source edges conflate unrelated metrics; calibration documents do not substantiate generated per-pair demand; five combined-URL references need separate document edges. `findings.csv` contains affected IDs and reproduction evidence. Monetary/network impact remains UNKNOWN because this role changed no model input and did not run a counterfactual.

Unfinished scope is material: 1,099 parent claims remain unverified. Most extracted fields lack a demonstrated conjunction of number, unit, period, airport/city, and direction. Internal dependency inspection records available first-hop documents; it does **not** complete recursive resolution of all child references. No full semantic source audit is claimed. Generic exact-token searches are screening attempts, not a substitute for reading every applicable passage. Further work must review the unresolved atomic evidence and primary child documents; no default acceptance or fabricated resolution was applied.

Reproduction from repository root:

```sh
python3 context/28_end_to_end_audit_20261110/sources/content/build_content_audit.py --recheck
# Rebuild from retained local cache (not renewed web truth):
python3 context/28_end_to_end_audit_20261110/sources/content/build_content_audit.py
# Deliberately renew full document acquisition:
python3 context/28_end_to_end_audit_20261110/sources/content/build_content_audit.py --fetch
```

Offline `--recheck` verifies strict CSV parsing, hashes, stable ID coverage, unique atoms, orphan edges and retained confirmed extractions. It can run without private cache, but cannot independently reauthenticate external source text without bodies. A clean clone can reproduce structural checks and pinned-raw proofs; re-fetching public pages may change document vintage. `validation.json` explicitly sets `complete_semantic_audit=false`.
