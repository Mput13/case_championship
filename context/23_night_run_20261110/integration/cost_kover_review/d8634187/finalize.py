#!/usr/bin/env python3
"""Create a manifest without self-referential commit/manifest hashes."""
import csv
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXCLUDED={'output_manifest.json','handoff.json','remote_receipt.json','delivery_receipt.json'}
GRAINS={
    'parameter_checks.csv':'parameter_id; 117 author/public/unknown parameters, no actual contracts',
    'primary_selected_rows.csv':'KHV source version x selected source item; amount/unit/date personally read',
    'independent_baselines.csv':'profile x alternative programme x author scenario',
    'independent_scenarios.csv':'profile x alternative programme x author scenario x overlay; arithmetic versus temporal status separate',
    'independent_affected_journeys.csv':'alternative programme x author scenario x overlay x original sales CSV line; union of affected legs',
    'independent_cash.csv':'alternative programme x author scenario x overlay x relative net cash day; timing fixture only',
    'timebase_audit.csv':'alternative programme x physical leg x departure/arrival event; source week versus erroneous row-date anchor',
    'delay_template_conflicts.csv':'alternative programme x author scenario x adjacent planning-label flights; not count of actual cancellations',
    'reference_joins.csv':'baseline/reference programme pair x author scenario; no acceptance inherited',
    'independent_nastya_cost_samples.csv':'author scenario x chosen distance/south flag/passengers; bounded function only',
}


def main():
    files=[]
    for p in sorted(ROOT.iterdir()):
        if not p.is_file() or p.name in EXCLUDED:continue
        assert p.suffix not in {'.pdf','.png','.bin','.db','.zip','.log'},p
        data=p.read_bytes();count=None
        if p.suffix=='.csv':count=len(list(csv.DictReader(data.decode('utf-8-sig').splitlines())))
        files.append(dict(path=p.name,sha256=hashlib.sha256(data).hexdigest(),size_bytes=len(data),rows=count,
            grain=GRAINS.get(p.name,'pinned input receipt, reviewer code or narrative; see schema'),
            role='REVIEWER_CODE' if p.suffix=='.py' else 'INDEPENDENT_REVIEW_OUTPUT'))
    aggregate=hashlib.sha256('\n'.join(r['path']+'\t'+r['sha256'] for r in files).encode()).hexdigest()
    (ROOT/'output_manifest.json').write_text(json.dumps(dict(version='CKR-exact-afadee-review-v1',files=files,
        aggregate_sha256=aggregate,excluded=sorted(EXCLUDED),local_only='.local/ renders and text; no full raw copy',
        acceptance='offline review and selected source rows only; no market/dispatch/launch acceptance'),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(files=len(files),payload_bytes=sum(r['size_bytes'] for r in files),aggregate_sha256=aggregate)))


if __name__=='__main__':main()
