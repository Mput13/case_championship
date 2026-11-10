#!/usr/bin/env python3
"""Scoped findings and a file manifest; no contact, upload, or publication."""
import hashlib
import json
import platform
from datetime import datetime, timezone
import scipy
import calculate as c


def findings():
    records=[
        dict(id='C01',status='ASSESSED_CONDITIONAL',mechanism='same-leg synchronisation versus same-leg unsynchronised; full base budget separate',
             base_delta_rub_week=1695505.7500616387,cautious_delta_rub_week=897307.7104317499,
             operating_example='7/11Dec diagnostic four-leg sets; real UT152/A46122Sat12Dec wait12h50',
             threshold='K_retiming+L_other <= row Kmax; full new programme only0.299m base before K/alternative',
             resource='hypothetical NJC and UFA tail positions; MCT60; two seats/one fare',
             evidence='outputs/C01_synchronization.csv; outputs/C01_spend_thresholds.csv; outputs/dated_connections.csv'),
        dict(id='C03',status='ASSESSED_CONDITIONAL',mechanism='existing Samara operating station versus expansion and weekly SVX deployment',
             base_local_contribution_rub_week=-4847183.6991582755,cautious_local_contribution_rub_week=-16434886.976119602,
             operating_example='KUF-ARH/OMS/NJC/MRV2RT each; Azimut KUF-NJC9/12Dec and KUF-MRV published',
             threshold='new KUF capacity cost minus deployment lodging <=1.136m/1.664m to save ferry cost; no-support gap remains',
             resource='one diagnostic working tail42.486bh/week; spare/crew/alternative unknown',
             evidence='outputs/C03_base_comparison.csv; outputs/fixed_routes.csv; programs.json'),
        dict(id='C04',status='ASSESSED_CONDITIONAL',mechanism='OMS compact1pair ->4pairs ->8pairs; local dated rotations and separate ideal-bank envelope',
             operating_example='OMS-KJA competitorFV6845/6846; direct and triangle not conflated',
             threshold='all three stages negative no-support within named fares/OD/2RT; omitted K/alternative not zero',
             resource='working tails1/1/2; not author12-spoke+388 programme',
             evidence='outputs/fixed_programs.csv; outputs/bank_upper_bound.csv; outputs/bank_exclusions.csv; outputs/fixed_daily_resources.csv'),
        dict(id='C07',status='ASSESSED_WITH_BOUNDED_CAUTIOUS_REFUSAL',mechanism='full SVX-OMS-KJA-OMS-SVX versus published SVX-OMS-SVX and next assignment',
             base_delta_rub_week=-1754011.114649373,cautious_delta_rub_week=-3755185.580875518,
             operating_example='WZ5071Tue/Fri, WZ5072Wed/Sat; Wed07:25WZ5049 as real possible next task only',
             threshold='base local break-even129.79/week/side exceeds entire82.73local OD at fixed through; cautious all-endpoint-OD upper bound still-2.057m',
             resource='added9bh/week; return+310/355/400min; actual next tail/crew unknown',
             evidence='outputs/C07_extension.csv; outputs/C07_demand_bounds.csv; outputs/C07_next_assignment.csv'),
        dict(id='C33',status='ASSESSED_CONDITIONAL',mechanism='retime same8 published IDs/dates, preserve both physical legs and old occupied seats',
             operating_example='KUF-SVX-OMS8/11Dec and OMS-SVX-KUF9/12Dec; waits635/1270->75/65min',
             threshold='15%local loss: local-only+1.458m/+0.219m;85/80%sold allow100%+0.556m/+0.219m;100%occupied<=0 before retimingK/other losses',
             resource='same constructed tail415blockmin/2370elapsedmin; OMS wait50->1815min; real tail/capacity/protection unknown',
             evidence='outputs/C33_retiming.csv; outputs/C33_tail_waits.csv; outputs/C33_final_published_baseline.csv'),
    ]
    (c.HERE/'findings.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    c.write('hypotheses_status.csv',records)
    (c.HERE/'handoff.json').write_text(json.dumps(dict(
        status='ONE_SCOPED_PACKAGE_COMPLETE_FOR_FRESH_REVIEW',hypotheses=[r['id'] for r in records],
        owner_pin='4a9763565f70b9ab1eddde2f5daca07687560948',
        audit_pin='5905f8e8655cfdf2cd3ab5326dfec1df8bb98961',
        first_slice_preserved='941d9ebfe97c86baa210da2c56bb1f94cbe298b0',
        evidence_pins=['06cb721b3e8e4eb8710c065c7b02078a112626a9','38f0f7ae8a10b6a60bd2d5ab39b18a9865e2b78b'],
        package_paths=dict(report='v2/README.md',programs='v2/programs.json',findings='v2/findings.json',checks='v2/checks.json'),
        integration='route_deltas explicit scenario/network/route/date; no independent summation of alternatives',
        future_calendar_company_KEEP_Nt='root methods responsibility; no annual or company share claim from this diagnostic week',
        supported_joint_fare_case='NOT_CALCULATED; award/rate/coefficient/special-fare net-yield inputs missing; no-support separate',
        source_review='fresh independent source review pending, not claimed complete',
        no_children=True,no_UIQA=True,no_PR=True,no_foreign_edits=True,
        runtime=dict(python=platform.python_version(),scipy=scipy.__version__),
        next='coordinator fresh scoped numerical review; no child or further cycle launched here'),ensure_ascii=False,indent=2)+'\n')


def manifest():
    entries=[]
    for p in sorted(c.HERE.rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts or p.name=='output_manifest.json':continue
        b=p.read_bytes();entries.append(dict(path=str(p.relative_to(c.HERE)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
    (c.HERE/'output_manifest.json').write_text(json.dumps(dict(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),manifest_self_excluded=True,
        original_inputs_manifest='../input_manifest.json',new_inputs_manifests=['additional_input_manifest.json','final_evidence_input_manifest.json','../public_sources_manifest.json'],
        files=entries),ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':
    findings();manifest()
