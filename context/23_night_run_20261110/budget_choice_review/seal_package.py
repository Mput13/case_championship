#!/usr/bin/env python3
"""One-time package manifest generation; never needed by the verifier."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
GRAINS={
    'independent_candidates.csv':'one capture-law/scenario/domain/candidate with original summary and union row',
    'independent_pairwise_inequalities.csv':'one ordered candidate/alternative pair in one finite choice problem',
    'independent_dominance_certificates.csv':'one strictly dominated candidate/domain with a sufficient direct certificate',
    'independent_region_vertices.csv':'one candidate/domain exact feasible vertex in nonnegative F/B',
    'independent_all_boundaries.csv':'one globally admissible pairwise tie interval in one finite problem',
    'independent_general_boundary_points.csv':'one exact point on a globally admissible tie interval',
    'independent_final_boundaries.csv':'one law/scenario/final-domain complete switch boundary',
    'independent_boundary_sides.csv':'one final-boundary F offset and B test versus all alternatives',
    'independent_gate_counts.csv':'one of 15 finite portfolio unions',
    'independent_source_money.csv':'one of 90 source portfolio/law/scenario money bridges',
    'independent_constraint_terms.csv':'one law/scenario/restricted action penalty expression',
    'independent_constraint_floors.csv':'one law/scenario global newbase-constraint floor',
    'independent_projection.csv':'one exact original result row and source semantic metadata',
    'independent_byte_preservation.csv':'one pre-existing exact Git blob compared between ba9 and subject',
    'independent_determinism.csv':'one of 13 newly generated owner output files',
    'independent_witness_slacks.csv':'one owner candidate witness versus one alternative',
    'independent_exclusions.csv':'one excluded candidate/domain with all pre-economic reasons',
    'source_manifest.json':'one record per exact source-commit/path Git blob read',
    'checks.json':'one record per executed personal assertion; not independent experiment count',
    'counterexamples.json':'one numerical counterexample or explicitly marked accounting fixture',
}
files=[]
for p in sorted(ROOT.rglob('*')):
    if not p.is_file() or p.name=='output_manifest.json':continue
    assert '_runtime' not in p.parts and '__pycache__' not in p.parts,p
    data=p.read_bytes();name=p.relative_to(ROOT).as_posix()
    files.append(dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
                      grain=GRAINS.get(name,'review document, reproducible code, or one scoped verification receipt')))
(ROOT/'output_manifest.json').write_text(json.dumps(dict(package_id='MR13_BUDGET_CHOICE_REVIEW_20261110',
    subject_commit='c6adf25cc39712cbfdd2d34acdabd31366b33bce',files=files,
    excludes=['output_manifest.json: self-hash excluded']),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(files=len(files),bytes=sum(x['bytes']for x in files))))
