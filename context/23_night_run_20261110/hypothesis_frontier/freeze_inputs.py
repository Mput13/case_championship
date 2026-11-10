#!/usr/bin/env python3
"""Read only exact Git objects; write only this research package."""
from pathlib import Path
import subprocess, hashlib, json, csv, io

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
H = '6ed8788882e7b4d07044b4f6e686ff71eadd8ac5'
PREFIX = 'context/16_agent_research/hypotheses/'
SOURCES = []

def add(alias, sha, path, grain):
    SOURCES.append((alias, sha, path, grain))

add('case_requirements.md', 'f1774e1f66a9483fb618ca6003abd9dc4d8563e1', 'context/00_brief/case5_requirements.md', 'case requirement')
for n in ['candidates.csv','inputs/candidate_catalog.json','existing_hypotheses.csv','evaluation_runs.jsonl','data_requests.csv','normalized/geometry_screen_sensitivity.csv','normalized/reproduced_thresholds.csv']:
    add('hypotheses/'+n,H,PREFIX+n,'candidate / declared observation; original grain retained')
for n in ['contract.json','scenario_programs.json','input_manifest.json','input_sets/phase2-frozen-002.json','input_sets/phase2-frozen-003.json','README.md','handoff.json',
          'runs/c26661067277af20/physical_legs.csv','runs/c26661067277af20/c01_connections.csv','runs/c26661067277af20/c01_dated_cohorts.csv','runs/c26661067277af20/c07_comparison.csv','runs/c26661067277af20/c07_directional_clock_references.csv','runs/c26661067277af20/replacement_states.csv',
          'cost_resource/6cf441ef38e2c6c5/matched_resource_deltas.csv','cost_resource/6cf441ef38e2c6c5/residual_gap_accounting.csv','cost_resource/6cf441ef38e2c6c5/money_product_definitions.csv',
          'c14_products/3906edd033f75bc6/flight_hotel_calendar.csv','c14_products/3906edd033f75bc6/summary.json','c14_calendar_flex/13bad5060a24f3ce/later_return_date_tradeoff.csv',
          'inputs/alternative_fa39de4/normalized/dated_flights.csv','inputs/alternative_fa39de4/normalized/flight_rules.csv','inputs/alternative_fa39de4/stay_offer/stay_rules.csv','inputs/alternative_fa39de4/stay_offer/public_offers.csv',
          'inputs/core/omsk_domestic_timetable_rows.csv','operating_join/126bccd230436e9f/summary.json']:
    add('experiment/'+n,H,PREFIX+'experiment_v1/'+n,'exact frozen experiment input/output; row grain per table')
for alias,sha,base,names in [
    ('core','505e24663e5952bae9b9540bb9a5a622663bfc2a','context/16_agent_research/core/integration_v1/', ['phase2_handoff.md','operating/coverage.csv','operating/dated_instances.csv','operating/quarantine.csv']),
    ('alternative','ef365ac2a936117e5b3bb12ea99c816d7b1a101c','context/16_agent_research/alternative/', ['signal_cards.csv','findings.md']),
    ('methods','abb1c76254d2d4e3cf9edd5c345b9cdb224f6abe','context/23_night_run_20261110/methods/', ['common_comparison_readout.md','budget_readout.md','runs/budget_v1/supply_upper_bounds.csv','runs/common_demand_v1/summary.csv']),
    ('budget_review','2278b184bbc83c590238c9f461581e3b045a11d0','context/23_night_run_20261110/budget_review/', ['report.md','handoff.json']),
    ('primary','17b4f348f15ea8695688d9435933cb4965568408','context/23_night_run_20261110/primary_evidence/', ['findings.md','primary_facts.csv','route_product_cards.csv','handoff.json']),
    ('source_join_review','944b16ac2dcde846e29dac2d47e11e5143f9fc2b','context/23_night_run_20261110/source_join_review/', ['report.md','handoff.json','findings.json']),
    ('model_repair','27740ffea0821aa404ecd1013d1bb141613261f3','context/23_night_run_20261110/model_repair/', ['handoff.json']),
    ('model_repair_review','445a5d523d4b57d8c89b2344e1913de2e5f9dc6b','context/23_night_run_20261110/model_repair_review/', ['handoff.json']),
    ('cost_kover','afadee35ebeefe54a05bdfc5b3e224a370f90e0a','context/23_night_run_20261110/cost_kover/', ['findings.md','handoff.json'])]:
    for n in names:add(alias+'/'+n,sha,base+n,'context only; not promoted into new operating calendar or fare')

def main():
    manifest=[]
    for alias,sha,path,grain in SOURCES:
        raw=subprocess.check_output(['git','show',sha+':'+path],cwd=REPO)
        dest=ROOT/'inputs'/alias
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(raw)
        rows=len(list(csv.DictReader(io.StringIO(raw.decode())))) if path.endswith('.csv') else None
        exact_grains={
            'candidates.csv':'one candidate specification, candidate_id; 35 products, not city observations',
            'existing_hypotheses.csv':'one attributed ancestor idea; idea family, not an additional flight',
            'data_requests.csv':'one required data acquisition/test request',
            'geometry_screen_sensitivity.csv':'candidate_id x path_id x scenario screen_km; great-circle screen, not dispatch',
            'reproduced_thresholds.csv':'one old conditional threshold recipe; no observed sales',
            'physical_legs.csv':'one hypothetical variant x date x directed physical leg; two hypothetical tails or one chain',
            'c01_connections.csv':'variant x date x directed endpoint itinerary x assumed minimum connection',
            'c01_dated_cohorts.csv':'variant x initial date x booked nights x assumed minimum connection; one return-cohort design',
            'c07_comparison.csv':'one chain turn scenario against fixed two-leg reference',
            'c07_directional_clock_references.csv':'one directed leg clock proxy with source/date-alignment restrictions',
            'replacement_states.csv':'one KEEP/REPLACE/CANCEL accounting state; actual donor NULL',
            'matched_resource_deltas.csv':'candidate x per-operating-date tail/resource delta',
            'residual_gap_accounting.csv':'candidate x named baseline x symbolic residual K',
            'money_product_definitions.csv':'candidate itinerary template and target OD for monetary threshold',
            'flight_hotel_calendar.csv':'outbound instance x named property x booked-date basis x nights; alternatives overlap',
            'later_return_date_tradeoff.csv':'one original property product request x earliest captured return',
            'dated_flights.csv':'one PLANNED_FROM_ADVERTISED_RULE endpoint instance; not independently proven physical nonstop',
            'flight_rules.csv':'one captured airport endpoint schedule rule and validity interval',
            'stay_rules.csv':'one named property x published admission/checkin/minimum-stay fields',
            'public_offers.csv':'one published property tariff offer with native billing unit; not realised price',
            'omsk_domestic_timetable_rows.csv':'one airport table row with inbound/outbound local clocks; same tail/date offsets not admitted',
            'coverage.csv':'one experiment/route coverage cell; absence from frozen table is not absence of service',
            'dated_instances.csv':'one retained dated departure; arrival/performance may be NULL',
            'quarantine.csv':'one retained rejection/ambiguous record; no promotion to operational input',
            'signal_cards.csv':'one alternative-data mechanism card; not endpoint demand',
            'supply_upper_bounds.csv':'fixed model-program x scenario x optimistic capacity certificate; context only',
            'summary.csv':'one frozen common-demand program/scenario/recipe aggregate; context only',
            'primary_facts.csv':'source x entity x metric x publication period; exact qualifier retained',
            'route_product_cards.csv':'source-specific endpoint publication/absence card; HOLDs and UNKNOWN retained'
        }
        grain=exact_grains.get(Path(path).name,grain)
        manifest.append(dict(input_id=alias,source_commit=sha,source_path=path,git_blob=subprocess.check_output(['git','rev-parse',sha+':'+path],cwd=REPO,text=True).strip(),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),rows=rows,grain=grain,stored_path=str(dest.relative_to(ROOT)),capture='git show exactSHA:path; no live source substitution'))
    (ROOT/'source_manifest.json').write_text(json.dumps(dict(input_set_id='frontier-frozen-001',prepared_base='f1774e1f66a9483fb618ca6003abd9dc4d8563e1',inputs=manifest),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(inputs=len(manifest),bytes=sum(x['bytes'] for x in manifest))))

if __name__=='__main__':main()
