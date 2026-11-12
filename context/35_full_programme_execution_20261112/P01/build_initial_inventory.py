#!/usr/bin/env python3
"""Build the coordinator's initial inventory, without upgrading historical evidence."""
import csv
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
PLAN = ROOT / 'context/34_full_programme_plan_20261112'


def write_csv(name, rows):
    with (BASE / name).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    plan = json.loads((PLAN / 'variant_research_plan.json').read_text())
    history = plan['legacy_hypotheses']
    write_csv('hypothesis_history.csv', history)
    write_csv('hypothesis_dispositions.csv', [dict(
        hypothesis_id=h['candidate_id'], title=h['title'],
        current_run_disposition='WORK_NOT_DONE_IN_CURRENT_PROGRAMME',
        historical_result_scope=h['checked_result_and_scope'],
        meaning='Reassessment/merge/supersession pending; not an economic rejection or erasure of prior evidence',
        successor_ids='', source='variant_research_plan.json / preserved inventory35',
    ) for h in history])
    write_csv('city_coverage.csv', [dict(
        iata=c['iata'], city=c['city'], role='TO_ESTABLISH_FROM_EVIDENCE',
        market_research='P02_IN_PROGRESS', operations_research='P03_IN_PROGRESS',
        new_programme_evaluation='NOT_RUN', applicability_disposition='PENDING',
        distance_500km_reassessment=c['distance_500km_reassessment'],
    ) for c in plan['seed_cities']])
    signals = [
        dict(hypothesis_id='H-P02-02', version=1, parent_ids='P02 new source signal',
             city_or_markets='KZN–Тобольск (аэропорт уточнить)–OMS; RT581 markets to resolve',
             source='https://www.uvtaero.ru/raspisanie',
             claim_and_mechanism='A nonstop product may compete differently with a through product involving an intermediate stop; count physical seats once.',
             distinguishing_test='Same endpoint OD/date: compare true nonstop, ordered through itinerary and other sellable alternatives through the common choice/resource engine.',
             owner='P02 signal; future P07/P08 variant task',
             status='PROPOSED_FROM_RESEARCHER_SIGNAL',
             evidence_acceptance='P02 pinned source/handoff pending; not independently accepted by this inventory',
             uncertainty='Adjacent physical legs, sale rights, continuity and actual inventory must be qualified.'),
        dict(hypothesis_id='H-P03-01', version=1, parent_ids='C02; P03 new applicability signal',
             city_or_markets='GOJ operating role and affected routes',
             source='https://ar-goj.ru/about/news/volga-avia-nachala-provodit-tekhnicheskoe-obsluzhivanie-samo/',
             claim_and_mechanism='Outstation/night-stop with limited line maintenance may differ materially from the cost/resource commitment of a full new base.',
             distinguishing_test='Compare the same intended markets served through outstation, radial base and transfer-hub programmes, including crew, maintenance scope and full cash.',
             owner='P03 signal; future P07 variant task',
             status='PROPOSED_FROM_RESEARCHER_SIGNAL',
             evidence_acceptance='P03 pinned source/handoff pending; not independently accepted by this inventory',
             uncertainty='Current RW contract, free maintenance windows, price and SJ-100 applicability remain unknown.'),
    ]
    write_csv('active_hypotheses.csv', signals)
    for source, target in [('assumptions_register.csv', 'assumptions_inventory.csv'), ('reuse_map.csv', 'reuse_register.csv')]:
        (BASE / target).write_bytes((PLAN / source).read_bytes())
    write_csv('dependency_requests.csv', [dict(
        request_id='DR-P02-MONTHLY-DEMAND-001', requested_by='P02',
        field='monthly 2025 and available 2026 airport/carrier aggregates plus endpoint OD observations',
        owner='coordinator P01 / P05; focused source research if required',
        status='OPEN_SOURCE_AND_GRAIN_QUALIFICATION',
        constraint='Tourism EMISS62073 and other non-aviation monthly series are not monthly aviation OD; annual airport segments are not endpoint journeys.',
        work_continuing='P02 offer/competition research and P03/P04 inputs continue independently',
    )])
    inputs = [PLAN / p for p in ['variant_research_plan.json', 'reuse_map.csv', 'assumptions_register.csv']]
    result = dict(
        status='USABLE_INITIAL_INVENTORY_NOT_FULL_P01_ACCEPTANCE',
        legacy_hypotheses=len(history), seed_cities=len(plan['seed_cities']),
        new_signal_hypotheses=len(signals),
        evidence_upgrade=False, new_network_calculations=False,
        input_files=[dict(path=str(p.relative_to(ROOT)), sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in inputs],
        limits='Historical outcomes are preserved; current hypothesis dispositions, complete assumption scan and source acceptance remain in progress.',
    )
    (BASE / 'initial_inventory.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'input_files'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
