#!/usr/bin/env python3
"""Validate the evidence package; this does not validate market demand or profits."""
import csv
import importlib.util
import json
import re
import sys

sys.dont_write_bytecode = True
from datetime import date
from pathlib import Path

P = Path(__file__).resolve().parent
SCHEMAS = {
    'sources': 'source_id,title,organization,url,published_at,accessed_at,period,geography,metric,unit,source_type,access_status,limitations',
    'claims': 'claim_id,claim,evidence_status,source_ids,period,geography,value,unit,mechanism,decision_impact,uncertainty',
    'routes': 'origin,destination,product,season,competitors,frequency_evidence,demand_evidence,ground_alternative,rw_overlap,operating_constraints,assessment,source_ids,missing_fields',
    'features': 'feature_id,feature,evidence_ids,mechanism,affected_markets,magnitude_or_bound,counterevidence,decision_effect,unknowns',
}


def main():
    tables = {}
    for name, schema in SCHEMAS.items():
        with (P / f'{name}.csv').open(newline='') as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames == schema.split(','), (name, reader.fieldnames)
            tables[name] = list(reader)
        assert tables[name], name
        for row in tables[name]:
            assert None not in row and all(v is not None for v in row.values()), row

    def ids(name, key, prefix):
        result = [r[key] for r in tables[name]]
        assert len(result) == len(set(result))
        assert all(re.fullmatch(prefix + r'\d{2}', v) for v in result)
        return set(result)

    source_ids = ids('sources', 'source_id', 'PEE-S')
    claim_ids = ids('claims', 'claim_id', 'PEE-C')
    ids('features', 'feature_id', 'PEE-F')
    for name in ('claims', 'routes'):
        for row in tables[name]:
            assert row['source_ids'] and set(row['source_ids'].split(';')) <= source_ids, row
    for row in tables['features']:
        assert set(row['evidence_ids'].split(';')) <= claim_ids, row
    for row in tables['sources']:
        assert row['url'].startswith(('https://', 'git:')), row
        assert ' ' not in row['url'], row
        assert row['accessed_at'] == '2026-11-12', row
        if row['published_at']:
            assert date.fromisoformat(row['published_at']) <= date(2026, 11, 12), row
        assert row['access_status'] and row['limitations'], row
    for row in tables['claims']:
        if row['evidence_status'] == 'unknown':
            assert row['value'] == '', row
        assert row['period'] and row['geography'] and row['uncertainty'], row
    for row in tables['routes']:
        assert row['origin'] == 'PEE' and re.fullmatch('[A-Z]{3}', row['destination'])
        assert all(row[k] for k in SCHEMAS['routes'].split(',')), row
    assert len({r['destination'] for r in tables['routes']}) == len(tables['routes'])

    spec = importlib.util.spec_from_file_location('pee_calculate', P / 'calculate.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    expected = module.calculate()
    assert expected == json.loads((P / 'calculations.json').read_text())
    covered = {r['destination'] for r in tables['routes']}
    assert set(expected['coverage_model_unique_PEE_partners']) <= covered
    assert expected['airport_2025']['component_sum'] == 2004861
    assert abs(expected['support_2027']['VOG']['table_program_rub_not_award'] - 12968408.2) < .01
    assert expected['dated_complete_trip_illustrations']['PEE_MCX']['total_min_scenario'] == 395
    assert expected['dated_complete_trip_illustrations']['PEE_MRV']['total_min_scenario'] == 420
    decision = json.loads((P / 'decision.json').read_text())
    assert decision['iata'] == 'PEE' and decision['as_of'] == '2026-11-12'
    assert {r['id'] for r in decision['alternatives']} == {
        'localdirect', 'existingbase', 'newbase', 'hub', 'groundfeed', 'noproject'}
    for row in decision['alternatives']:
        for key in ('condition', 'threshold', 'parameter_source', 'action_if_fails',
                    'strongest_for', 'strongest_against'):
            assert row[key], row

    dossier = (P / 'dossier.md').read_text()
    assert all(f'{len(tables[k])}' in dossier for k in tables)
    unknown_refs = set(re.findall(r'PEE-[SCF]\d{2}', dossier)) - source_ids - claim_ids - {
        r['feature_id'] for r in tables['features']}
    assert not unknown_refs, unknown_refs
    registered_urls = {r['url'] for r in tables['sources']}
    external_urls = set(re.findall(r'\]\((https://[^)]+)\)', dossier))
    assert external_urls <= registered_urls, external_urls - registered_urls
    report = {
        'status': 'PASS', 'as_of': '2026-11-12',
        'counts': {k: len(v) for k, v in tables.items()},
        'model_partners_covered': len(expected['coverage_model_unique_PEE_partners']),
        'pinned_sha256_verified': expected['pinned_manifest_entries_sha256_verified'],
        'checks': ['exact_brief_csv_schemas', 'unique_PEE_identifiers', 'referential_integrity',
                   'unknown_numeric_values_empty', 'all_model_PEE_partners_covered',
                   'six_alternatives_with_threshold_source_action', 'reproduced_calculations',
                   'published_and_access_dates', 'dossier_external_links_registered'],
        'not_proven_by_validation': ['market_OD', 'profit', 'future_flight_execution',
                                     'subsidy_award_or_cash', 'airport_MCT_MRO_readiness'],
    }
    (P / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
