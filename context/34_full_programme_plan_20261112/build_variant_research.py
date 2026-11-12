#!/usr/bin/env python3
"""Describe data-driven research branches; do not run network calculations or agents."""
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
AUTHOR = 'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6'
HISTORY = 'context/23_night_run_20261110/integration/hypothesis_frontier/519998ed/inventory35.csv'


def pinned_csv(path):
    raw = subprocess.check_output(['git', 'show', f'{AUTHOR}:{path}'], cwd=ROOT)
    return list(csv.DictReader(io.StringIO(raw.decode()))), hashlib.sha256(raw).hexdigest()


def main():
    summary, summary_hash = pinned_csv('data/processed/network_summary.csv')
    routes, routes_hash = pinned_csv('data/processed/network_routes.csv')
    cities = []
    for row in summary:
        if row['scenario'] == 'base' and row['hub']:
            cities.append({
                'iata': row['hub'], 'city': row['variant'].removeprefix('Хаб '),
                'status': 'SEED_CANDIDATE_NOT_SELECTED',
                'role_to_establish': 'new_or_existing_base_or_hub; verify current role and commitments',
                'distance_500km_reassessment': row['hub'] in {'UFA', 'GOJ', 'PEE', 'CEK', 'TJM'},
            })
    history_raw = (ROOT / HISTORY).read_bytes()
    history_rows = list(csv.DictReader(io.StringIO(history_raw.decode())))
    legacy = [{key: row[key] for key in [
        'candidate_id', 'title', 'author_network_form', 'author_operating_base',
        'author_paths', 'ancestor_ids', 'author_evaluation_status', 'checked_result_and_scope',
    ]} for row in history_rows]
    seeds = {}
    for row in routes:
        if row['scenario'] == 'base' and row['variant'].startswith('Прямые '):
            item = seeds.setdefault(row['variant'], {'historical_name': row['variant'], 'legs': []})
            item['legs'].append([row['from'], row['to']])
            item['status'] = 'HISTORICAL_ROTATION_SEED_NOT_ACCEPTED_PROGRAMME'
            item['airport_resolution'] = 'MOW must be resolved to a specific airport before scheduling or costing'

    # These illustrate matched questions. They are neither selected networks nor a dispatch queue.
    examples = [
        ('E01', 'Уфа', ['UFA'], ['C01', 'C10', 'C11'],
         'Достаточны ли местные и пересадочные продажи после учёта действующих альтернатив и ответа конкурентов?',
         ['Синхронизированный пересадочный узел', 'Радиальная база без обязательной синхронизации', 'Прямые программы из существующей базы']),
        ('E02', 'Нижний Новгород', ['GOJ'], ['C02', 'C28', 'C32'],
         'Даёт ли полезный деловой календарь и география преимущество, за которое пассажир платит?',
         ['Пересадочный узел', 'Прямые рейсы с подходящими датами возврата', 'Наземный доступ и существующее авиапредложение']),
        ('E03', 'Омск', ['OMS', 'SVX', 'KJA'], ['C04', 'C07', 'C33'],
         'Как обслуживать целевой рынок Омск–Красноярск с учётом всех базовых плеч и прежних заданий?',
         ['Новая база в Омске', 'Проверяемая цепочка Екатеринбург–Омск–Красноярск–Омск–Екатеринбург', 'Иное применение того же доступного ресурса']),
        ('E04', 'Самара', ['KUF', 'SVX', 'VOG'], ['C03', 'C09', 'C16'],
         'Как соотносятся собственный местный спрос, пересадки и полная стоимость открытия или развития базы?',
         ['Радиальная база', 'Пересадочная программа', 'Прямые обороты или цепочки из существующей базы']),
        ('E05', 'Пермь, Челябинск, Тюмень', ['PEE', 'CEK', 'TJM'], ['C06', 'C13', 'C15', 'C17', 'C27'],
         'Меняет ли близость Екатеринбурга роль каждого города, если учитывать наземный доступ, местные рынки и уже занятый ресурс?',
         ['Отдельная роль каждого города как базы или узла', 'Прямые и сезонные продукты', 'Наземный подвоз или партнёрское обслуживание']),
    ]
    plan = {
        'status': 'PROPOSED_NOT_LAUNCHED',
        'authority': 'Current user: investigate variants in parallel within one system; form and revise hypotheses from data, including during research.',
        'seed_city_count': len(cities), 'seed_cities': cities,
        'city_domain': 'The 20 inherited candidates are the starting hub/base inventory, not a closed domain of all airports or a final shortlist. New cities may be added on evidence. Direct endpoints are not restricted to this hub list.',
        'legacy_hypothesis_count': len(legacy), 'legacy_hypotheses': legacy,
        'legacy_policy': 'History and evidence to reuse, not 35 mandatory unchanged experiments. Reformulate, merge, supersede or add hypotheses with reasons and lineage. A superseded formulation is not an economic rejection; preserve valid prior evidence and its scope.',
        'legacy_direct_rotation_seeds': list(seeds.values()),
        'direct_search': 'Generate ordinary returns, additions or retiming of existing flights, seasonal programmes, complete rotations and supported contract products from markets and resource. Historical triangles are examples, not an imposed network form. Existing service is not automatically a new market.',
        'matched_examples': [dict(id=a, title=b, airports=c, legacy_ids=d, question=e, alternatives=f, status='ILLUSTRATIVE_QUESTION_PENDING_DATA') for a,b,c,d,e,f in examples],
        'programme_families': [
            {'id': 'KEEP', 'meaning': 'Будущая работа без проекта при том же внешнем сценарии и доступном ресурсе'},
            {'id': 'EXISTING_BASE_DIRECT', 'meaning': 'Развитие действующих баз, прямых рейсов и существующих продуктов'},
            {'id': 'RADIAL_BASE', 'meaning': 'Новая или расширенная радиальная база с опорой на местный спрос'},
            {'id': 'TRANSFER_HUB', 'meaning': 'Новый или расширенный узел с продаваемыми пересадками'},
            {'id': 'MIXED', 'meaning': 'Совместно рассчитанные хабовые и независимые прямые программы'},
            {'id': 'EXTENDED', 'meaning': 'Дополнительные международные и смешанные варианты парка; отдельно без новых Ту-214'},
        ],
        'data_to_hypothesis': [
            'Map dated markets, actual and published products, competition, fleet, existing obligations, costs and coverage gaps.',
            'Identify a specific passenger problem or network opportunity supported by those inputs; an empty timetable record does not prove unmet demand.',
            'Register a falsifiable hypothesis, mechanism, relevant markets, competing explanation, expected decision impact and distinguishing experiment.',
            'Test feasible alternatives through the common engine; an unsupported critical input leads to sourced research, justified ranges or decision thresholds.',
            'Update the active set as evidence arrives. Record new, revised, merged and superseded versions; never manufacture reasons to reject unfinished work.',
        ],
        'hypothesis_record_fields': [
            'hypothesis_id', 'version', 'parent_ids', 'city_or_markets', 'observed_signal_and_source_ids',
            'claim_and_mechanism', 'counterfactual', 'competing_explanation', 'distinguishing_test',
            'critical_unknowns_and_assumption_ids', 'owner_task_id', 'input_versions', 'status',
            'result_scope', 'revision_reason', 'successor_ids', 'revisit_condition',
        ],
        'parallel_investigation': {
            'unit': 'A coherent programme or matched alternatives for one city/market, including local data, competitors, resource and economics; split a broad branch when evidence justifies it.',
            'dispatcher': 'coordinator; packages P07/P08/P08I describe work families and may have multiple centrally delegated instances',
            'max_active_children_including_shared_engine_and_reviews': 4,
            'model_for_variant_research': 'gpt-6.1-sol', 'effort': 'xhigh',
            'common_engine_and_joint_comparison': 'gpt-6-astra / xhigh',
            'workers_may_spawn_children': False,
            'work_scope_template': 'context/35_full_programme_execution_20261112/variants/{variant_id}/{revision_id}/',
            'instance_brief_rule': 'At dispatch, the coordinator materialises a distinct task ID, variant/revision, pinned input versions and the unique work_scope_template in the actual brief. Family-level P07/P08/P08I scopes are aggregate outputs, not a shared write directory for parallel variant workers.',
            'dispatch_rule': 'As pinned usable inputs become available, dispatch distinct variants in parallel. Keep enough capacity for shared data, engine and meaningful checks. No permanent city agent waiting idle and no fixed finalist quota.',
            'coverage_rule': 'Every seed city gets an explicit applicability disposition; every active hypothesis gets a reasoned result or precise unresolved condition. Depth follows potential decision impact and real uncertainty, not a clock cutoff. All viable material variants are deepened; history may be merged or superseded.',
            'hypothesis_updates': 'A worker proposes or revises hypotheses in its branch. The coordinator checks duplicates, records lineage and dispatches affected work; existing workers do not silently change shared inputs.',
            'per_branch_outputs': ['hypothesis_card.json', 'evidence_delta.csv', 'programme_spec.json', 'common_engine_result_refs.json', 'counterarguments.json', 'assumption_ids.csv', 'dependency_requests.csv', 'handoff.json'],
            'feedback': 'Variant result → shared comparison → identify the input or design difference that changes the decision → responsible data owner or variant → new pinned input/design → rerun affected alternatives. Data discoveries relevant to other branches are propagated through the coordinator.',
            'independence': 'Variant research must seek counterevidence. Independent reviews remain fresh tasks with the existing author-exclusion rules.',
        },
        'joint_comparison': {
            'comparison_key': ['fleet_scope_id', 'delivery_calendar_id', 'external_scenario_id', 'period', 'input_version'],
            'shared_inputs': ['monthly_resource', 'market_definition_and_demand', 'competitor_products', 'common_cost_rules', 'KEEP'],
            'endogenous_differences': 'Itinerary quality, own sales migration, capacity, launch/base costs and explicitly modelled competitor reactions may differ by programme.',
            'steps': [
                'Evaluate feasible individual programmes and matched alternatives under comparable resource constraints; unneeded resource may remain unused.',
                'Generate combined hub/direct programmes using route and flight specifications, not the sum of stand-alone results.',
                'Reassign shared fleet, dated seats and passenger choices; count fares, base costs, support, donors and reserves once.',
                'Compare net additional traffic and revenue, full incremental result, funding and risks against same-period KEEP; retain non-dominated choices where preferences or budgets are unresolved.',
                'Stress the fixed programme, then evaluate feasible adaptation and staged launch under the same scenario.',
            ],
            'output': 'Versioned programme × scenario × month table with resource, before/after network, traffic, economics, funding, uncertainty, traceable hypotheses and actions.',
            'subjective_tradeoffs': 'Keep every weight, proxy, estimated cost and range in the user assumption register. No hidden all-purpose winner score.',
            'limits': 'Best found programme is not a proof of global optimality; record search coverage and remaining decision-relevant gaps.',
        },
        'sources': [
            {'commit': AUTHOR, 'path': 'data/processed/network_summary.csv', 'sha256': summary_hash},
            {'commit': AUTHOR, 'path': 'data/processed/network_routes.csv', 'sha256': routes_hash},
            {'path': HISTORY, 'sha256': hashlib.sha256(history_raw).hexdigest(), 'scope': 'preserved historical register, not revalidated market claims'},
        ],
        'execution': {'agents_launched': False, 'new_network_calculations': False, 'new_market_facts_collected': False},
    }
    (BASE / 'variant_research_plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')
    with (BASE / 'city_research_seed.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(cities[0]))
        writer.writeheader()
        writer.writerows(cities)
    print(json.dumps({'cities': len(cities), 'historical_hypotheses': len(legacy), 'historical_direct_rotations': len(seeds), 'state': plan['status']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
