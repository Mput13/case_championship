#!/usr/bin/env python3
"""Build one report from immutable artifacts; never execute peer code or export raw."""
import csv
import gzip
import hashlib
import html
import io
import json
import math
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'context/17_research_report'
TEAM_OUT = ROOT / 'context/19_report_update_20261110'
PINS = {
    'core': '505e24663e5952bae9b9540bb9a5a622663bfc2a',
    'alternative': 'ef365ac2a936117e5b3bb12ea99c816d7b1a101c',
    'hypotheses': '6ed8788882e7b4d07044b4f6e686ff71eadd8ac5',
    'critic': 'fd086bad2ae30c46e95d6e38954dc99a18627902',
    'coordinator': '7686d1d2cb5fd72130b5028cb8e08b39a1d9b2e6',
    'recovery': '063f13cc535c7e94557df694b92071926acb7669',
    'nastya_step1': '2f03b693a62c219e9475fcd1e26295039f6a49d7',
    'tsiri_stage22': '6ec84a7d2a6eb50b547a61df82fc5a424f48f146',
    'tsiri_economics': '93fa5cf4a10ab67e05c93d19fc5375fc58ef9299',
    'team_review': 'ea542b0c38771f5ad55e67ac02e14b49f07c142c',
    'konstantin': '9dbaee7ee53ee10ecb6db64d1cf634a7c0bceba7',
}
REPO = 'https://github.com/Mput13/case_championship'
INPUTS = {}


def source_path(role, path):
    if role in {'nastya_step1', 'tsiri_stage22', 'tsiri_economics', 'team_review', 'konstantin'}:
        return path
    if role == 'recovery':
        return 'context/17_research_report/network_recovery/' + path
    return 'context/16_agent_research/' + ('' if role == 'coordinator' else role + '/') + path


def link(role, path):
    return f'{REPO}/blob/{PINS[role]}/{source_path(role, path)}'


def read(role, path):
    full = source_path(role, path)
    b = subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{PINS[role]}:{full}'])
    INPUTS[(role, path)] = {'role': role, 'commit': PINS[role], 'path': full,
                           'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b), 'url': link(role, path)}
    return (gzip.decompress(b) if path.endswith('.gz') else b).decode('utf-8-sig')


def rows(role, path):
    return list(csv.DictReader(io.StringIO(read(role, path))))


def esc(value):
    return html.escape(str(value), quote=True)


def table(data, columns, caption, role, path):
    head = ''.join(f'<th scope="col"><code>{esc(key)}</code><span>{esc(label)}</span></th>' for key, label in columns)
    body = ''.join('<tr>' + ''.join(f'<td class="{"numeric" if re.fullmatch(r"[-+]?[0-9.]+", row.get(key, "")) else "text"}">{esc(row.get(key) or "UNKNOWN")}</td>' for key, _ in columns) + '</tr>' for row in data)
    return (f'<div class="table-scroll" tabindex="0" role="region" aria-label="{esc(caption)}"><table>'
            f'<caption>{esc(caption)}</caption><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'
            f'<p class="source"><a href="{link(role, path)}">CSV: {esc(Path(path).name)}</a> · '
            'выбранные столбцы реальных строк; пустое значение обозначено UNKNOWN.</p>')


def candidate_table(candidates, inherited):
    ancestry = {r['id']: r for r in inherited}
    output = []
    for c in candidates:
        tested = c['candidate_id'] in {'C01', 'C07', 'C14'}
        queue = c['selected_for_deepening'] == 'True'
        status = 'Ограниченный опыт' if tested else ('В очереди углубления' if queue else 'Сохранён для сравнения')
        origins = []
        for aid in c['ancestor_ids'].split(';'):
            a = ancestry[aid]
            assert re.match(r'https://github.com/[^/]+/[^/]+/blob/[0-9a-f]{40}/', a['source_url'])
            origins.append(f'<li><a href="{esc(a["source_url"])}">{esc(aid)}</a>: {esc(a["original_author"])}.</li>')
        detail = (f'<details><summary>Проверка и происхождение</summary>'
                  f'<p><b>Пассажир:</b> {esc(c["passenger_and_purpose"])}.</p>'
                  f'<p><b>Продукт:</b> {esc(c["rw_product"])}.</p>'
                  f'<p><b>Условие отказа:</b> {esc(c["stop_rule"])}.</p>'
                  f'<p><b>Ресурс:</b> {esc(c["resource_requirement"])}.</p>'
                  '<p>Спецификация: роль GPT-6 Astra. Основания:</p>'
                  f'<ul>{"".join(origins)}</ul></details>')
        search = ' '.join([c['candidate_id'], c['title'], c['proposed_paths'], c['passenger_and_purpose'],
                           c['ancestor_ids'], ' '.join(ancestry[x]['original_author'] for x in c['ancestor_ids'].split(';'))])
        route = '<br>'.join(esc(part).replace('&gt;', ' → ') for part in c['proposed_paths'].split(';'))
        output.append(f'<tr data-program data-queue="{str(queue).lower()}" data-tested="{str(tested).lower()}" '
                      f'data-search="{esc(search.lower())}"><th scope="row"><span class="program-id">{esc(c["candidate_id"])}</span>'
                      f'{esc(c["title"])}<span class="program-state">{status}</span></th>'
                      f'<td class="routes">{route}</td><td>{detail}</td></tr>')
    return ''.join(output)


def c07_chart(c07):
    series = [('Исходное задание', 205, 50, 255, '')]
    for row in c07:
        elapsed = int(row['elapsed_candidate_minutes'])
        series.append((f'Цепочка · turn {row["variant"].split("turn")[1]} мин', 475, elapsed - 475,
                       elapsed, f'+{row["return_delay_vs_reference_minutes"]} мин'))
    return ''.join(f'<div class="chart-row"><div class="bar-label">{title}</div><div class="bar-track">'
                   f'<div class="bar-block" style="width:{block/7:.4f}%"></div>'
                   f'<div class="bar-ground" style="width:{ground/7:.4f}%"></div></div>'
                   f'<div class="bar-number">{total}<span>{delta}</span></div></div>'
                   for title, block, ground, total, delta in series)


def team_update():
    """Project saved integrated results; do not run or change any colleague model."""
    stage = 'context/22_stage1_audit/'
    for name in ['release_note.md', 'final_acceptance.md', 'main_source_checks.md',
                 'integration_decisions.md', 'accepted_model_inputs.json', 'model_rules.json',
                 'recommended_weights.csv', 'evidence_ledger.csv']:
        read('tsiri_stage22', stage + name)
    acceptance = json.loads(read('tsiri_stage22', stage + 'final_acceptance.json'))
    validation = json.loads(read('tsiri_stage22', stage + 'final_validation.json'))
    profiles = json.loads(read('tsiri_stage22', stage + 'weight_profiles.json'))
    scores = rows('tsiri_stage22', stage + 'final_scores.csv')
    comparison = rows('tsiri_stage22', stage + 'final_comparison.csv')
    research = rows('tsiri_stage22', stage + 'accepted_research.csv')
    for path in ['docs/HANDOFF.md', 'docs/24_hypotheses_comparison.md', 'docs/25_step1_open_questions.md',
                 'src/network_model.py', 'src/fetch_telegram.py', 'src/kover_days.py',
                 'data/processed/network_summary.csv', 'data/processed/network_routes.csv']:
        read('nastya_step1', path)
    # stage22 changed the screening layer, not the audited network or reply fetcher.
    for path in ['src/network_model.py', 'src/fetch_telegram.py']:
        assert read('tsiri_stage22', path) == read('nastya_step1', path)
    for path in ['context/18_team_sync/step1_review/report.md',
                 'context/18_team_sync/step1_review/findings.json',
                 'context/18_team_sync/night_workflow_proposal.md']:
        read('team_review', path)
    for path in ['context/20_strategy_scope/README.md', 'context/21_team_proposals/README.md',
                 'context/21_team_proposals/validation.json', 'context/21_team_proposals/routes.csv',
                 'context/18_unit_economics_audit/breakeven.csv']:
        read('tsiri_economics', path)
    economy = rows('tsiri_economics', 'context/21_team_proposals/comparison.csv')
    read('konstantin', 'context/09_additional_research/report.md')
    primary = sorted((r for r in scores if (r['stress'], r['min_dist_km'], r['mode'], r['profile']) ==
                     ('base', '500', 'expansion_allowed', 'balanced')), key=lambda r: int(r['rank']))
    assert [r['iata'] for r in primary[:4]] == ['OMS', 'REN', 'BAX', 'KUF']
    assert all(abs(float(r['score']) - acceptance['primary']['scores'][r['iata']]) < 1e-12 for r in primary[:4])
    assert acceptance['verdict'] == 'ACCEPT_WITH_LIMITATIONS' and len(comparison) == 140
    recommended = profiles['recommended']['criteria']
    assert sum(c['weight'] for c in recommended) == 100
    assert validation['total_scenarios'] == 140
    def fmt(n, places=6):
        return f'{float(n):.{places}f}'.replace('.', ',')
    chart = []
    for r in primary[:4]:
        chart.append(f'<div class="rank-bar"><span>{esc(r["rank"])}. {esc(r["city"])} <code>{r["iata"]}</code></span>'
                     f'<span class="rank-track" aria-hidden="true"><i style="width:{float(r["score"])*100:.5f}%"></i></span>'
                     f'<b>{fmt(r["score"])}</b></div>')
    selected = [
        ('Основной · 500 км · развитие опоры', 'base', '500', 'expansion_allowed', 'balanced'),
        ('Строго новый узел · 500 км', 'base', '500', 'strict_new', 'balanced'),
        ('Без отсечки 500 км · те же веса', 'base', '0', 'expansion_allowed', 'balanced'),
        ('Приоритет локального рынка · 500 км', 'base', '500', 'expansion_allowed', 'local_market'),
        ('Приоритет связности · 500 км', 'base', '500', 'expansion_allowed', 'connectivity'),
        ('Устойчивость волны · 500 км', 'base', '500', 'expansion_allowed', 'resilience'),
        ('Без преимущества ручной изученности · 500 км', 'base', '500', 'expansion_allowed', 'evidence_neutral'),
        ('Только введения «Ковра» · основные веса', 'intro_only', '500', 'expansion_allowed', 'balanced'),
        ('Локальный рынок + общие нейтральные ячейки', 'common_neutral', '500', 'expansion_allowed', 'local_market'),
        ('Устойчивость + общие нейтральные ячейки', 'common_neutral', '500', 'expansion_allowed', 'resilience'),
    ]
    ranking, chosen = [], []
    for label, stress, distance, mode, profile in selected:
        r, = [r for r in comparison if (r['stress'], r['min_dist_km'], r['mode'], r['profile']) ==
              (stress, distance, mode, profile)]
        chosen.append({'label': label, **r})
        names = r['top3_cities'].split(' / ')
        ranking.append(f'<div class="ranking-case"><div>{esc(label)}</div><ol>' +
                       ''.join(f'<li><span>{esc(name)}</span><small>{fmt(r["score"+str(i)])}</small></li>'
                               for i, name in enumerate(names, 1)) + '</ol></div>')
    meanings = {
        'gap_pop': ('Население направлений с пробелом связности', 'Где связь могла бы быть полезна; это не число покупателей.'),
        'last365_days': ('Дни публикаций об ограничениях', 'Меньше — предпочтительнее. Без часов простоя и потерь стыковок.'),
        'competitor_hub': ('База конкурента', 'Риск входа; отсутствие упоминания не означает отсутствие конкурента.'),
        'pax_2025': ('Пассажиропоток аэропорта за 2025', 'Масштаб уже обслуженного потока, не свободный спрос.'),
        'catchment_pop_2025': ('Население зоны 75 км', 'Локальная основа рынка с оговорками о географии и пересчёте населения.'),
        'transfer_demand_base': ('Геометрия модельных пересадочных пар', 'Показатель связности. Модельные поездки не являются продажами.'),
        'strategy_region': ('Стратегический приоритет', 'Предпочтение из кейса; денежный эффект отдельно.'),
        'transfer_zone': ('Возможность трансфера', 'Поддержка пересадки не доказывает время стыковки и сквозной багаж.'),
        'ssj_mro': ('Опубликованное ТО SSJ', 'Возможность обслуживания отдельно от договора и свободной мощности.'),
        'wage_2024': ('Зарплата', 'Частичная оценка платёжеспособности с неполным охватом.'),
        'bad_weather_days': ('Погодный показатель', 'В этом скрининге UNKNOWN у всех; нейтральный центр — импутация.'),
    }
    weights = ''.join(f'<tr><th scope="row">{esc(meanings[c["column"]][0])}</th>'
                      f'<td class="numeric">{c["weight"]}%</td><td>{esc(meanings[c["column"]][1])}</td></tr>'
                      for c in recommended if c['weight'])
    alternatives = [profiles['recommended']] + profiles['alternatives']
    profile_rows = ''.join('<tr><th scope="row">' + esc(meanings[c['column']][0]) + '</th>' +
                           ''.join(f'<td class="numeric">{next(x["weight"] for x in p["criteria"] if x["column"]==c["column"])}%</td>' for p in alternatives) + '</tr>'
                           for c in recommended if c['weight'])
    economic_rows = []
    for network, name in [('H_UFA_8','Новая база UFA · 8 лучей'), ('H_UFA_4','UFA · ядро из 4 лучей'),
                          ('D_SVX8','SVX · 8 пар как добавка'), ('D_previous_best8','Прямой ZIA/SVX · 8 пар')]:
        by_scenario = {r['scenario']: r for r in economy if r['network'] == network}
        b, c = by_scenario['base'], by_scenario['cautious']
        assert all(float(r['contribution_before_base_fleet_opportunity']) < 0 for r in (b,c))
        economic_rows.append(f'<tr><th scope="row">{name}</th><td data-label="Частота на пару в каждом направлении">{2 if network.startswith("H_") else 1}/нед.</td>'
                             f'<td data-label="Борта: рабочие + резерв">{b["active_allocated"]} + {b["reserve_scenario"]}</td>'
                             f'<td data-label="Налёт, ч/нед.">{fmt(b["weekly_block_hours"],2)}</td>'
                             f'<td data-label="Результат: база / осторожный, млн ₽/нед.">{fmt(float(b["contribution_before_base_fleet_opportunity"])/1e6,2)} / {fmt(float(c["contribution_before_base_fleet_opportunity"])/1e6,2)}</td></tr>')
    links = {
        'STEP1': ('nastya_step1', 'docs/25_step1_open_questions.md'),
        'STEP1_COMPARE': ('nastya_step1', 'docs/24_hypotheses_comparison.md'),
        'TEAM_REVIEW': ('team_review', 'context/18_team_sync/step1_review/report.md'),
        'NIGHT_PLAN': ('team_review', 'context/18_team_sync/night_workflow_proposal.md'),
        'STAGE22': ('tsiri_stage22', stage+'release_note.md'),
        'FINAL_SCORES': ('tsiri_stage22', stage+'final_scores.csv'),
        'FINAL_COMPARE': ('tsiri_stage22', stage+'final_comparison.csv'),
        'FINAL_ACCEPT': ('tsiri_stage22', stage+'final_acceptance.md'),
        'ACCEPTED_RESEARCH': ('tsiri_stage22', stage+'accepted_research.csv'),
        'WEIGHTS': ('tsiri_stage22', stage+'weight_profiles.json'),
        'STAGE_RULES': ('tsiri_stage22', stage+'model_rules.json'),
        'SOURCE_CHECKS': ('tsiri_stage22', stage+'main_source_checks.md'),
        'ECONOMICS': ('tsiri_economics', 'context/21_team_proposals/README.md'),
        'ECONOMICS_CSV': ('tsiri_economics', 'context/21_team_proposals/comparison.csv'),
        'STRATEGY_SCOPE': ('tsiri_economics', 'context/20_strategy_scope/README.md'),
        'KONSTANTIN': ('konstantin', 'context/09_additional_research/report.md'),
    }
    replacements = {'TEAM_RANK_BARS': ''.join(chart), 'TEAM_RANKING': ''.join(ranking),
                    'TEAM_WEIGHTS': weights, 'PROFILE_WEIGHTS': profile_rows,
                    'TEAM_ECONOMICS': ''.join(economic_rows)}
    replacements.update({'LINK_'+label:link(role,path) for label,(role,path) in links.items()})
    facts = {'primary_top4': [{k:r[k] for k in ('iata','city','score','unknown_weight_share','rank_best','rank_worst')} for r in primary[:4]],
             'selected_scenarios': chosen, 'scenario_count':len(comparison), 'weight_sum':100,
             'acceptance':acceptance['verdict'], 'network_model_unchanged_from_step1':True,
             'telegram_fetch_unchanged_from_step1':True, 'kover_financial_module':'NOT_IMPLEMENTED',
             'night_workflow':'PROPOSED_NOT_STARTED', 'model_replay':'NOT_RUN',
             'new_research':'NOT_PERFORMED', 'accepted_research_rows':len(research)}
    return replacements, facts


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    recovery = json.loads(read('recovery', 'recovery_summary.json'))
    assert recovery['inventory_items'] == 63 and recovery['actual_http_reads'] == 47
    assert len(recovery['verified_scoped_current_exact_byte_sources']) == 6
    for path in ['inventory.csv', 'manifest.json', 'semantic_validation.json',
                 'parsed/national_market_observations.csv', 'parsed/khv_cost_components.csv']:
        read('recovery', path)
    for path in ['absence_report.md', 'phase2_brief.md', 'status.json', 'threads.json', 'journal_notes.json',
                 'kover_scenario_spec.md', 'coordinator/20261109T154615Z/checkpoint.json',
                 'coordinator/20261109T170202Z/checkpoint.json', 'coordinator/20261109T170202Z/critic_phase2_handoff.json',
                 'coordinator/20261109T170202Z/summary.md']:
        read('coordinator', path)
    critic = json.loads(read('critic', 'integration_v1/phase2_handoff.json'))
    capacity = json.loads(read('critic', 'integration_v1/reviews/conditional_capacity/reproduction.json'))
    candidates = rows('hypotheses', 'candidates.csv')
    inherited = rows('hypotheses', 'existing_hypotheses.csv')
    registries = {role: rows(role, 'source_registry.csv') for role in ('core', 'alternative')}
    h = 'experiment_v1/'
    specs = {
        'AIRPORT': ('core', 'normalized/airport_version.csv'),
        'ACCESS': ('core', 'normalized/access_alternative.csv.gz'),
        'MUNICIPAL': ('core', 'branches/social_economy/normalized/example_join_municipal_2024.csv'),
        'TOURISM': ('alternative', 'modules/tourism/normalized/primary_monthly_increments.csv'),
        'WEATHER': ('alternative', 'normalized/weather_monthly_2024.csv'),
        'BUSINESS': ('alternative', 'modules/business/normalized/sibur_sites.csv'),
        'MARKET': ('core', 'integration_v1/operating/market_observation_v1.csv'),
        'RULE': ('alternative', 'product_probe_v1/normalized/flight_rules_v2.csv'),
        'C07': ('hypotheses', h + 'runs/c26661067277af20/c07_comparison.csv'),
        'C14': ('hypotheses', h + 'c14_products/3906edd033f75bc6/flight_hotel_calendar.csv'),
        'FLEX': ('hypotheses', h + 'c14_calendar_flex/13bad5060a24f3ce/later_return_date_tradeoff.csv'),
        'RESOURCE': ('hypotheses', h + 'cost_resource/6cf441ef38e2c6c5/matched_resource_deltas.csv'),
        'C01': ('hypotheses', h + 'runs/c26661067277af20/c01_dated_cohorts.csv'),
    }
    data = {key: rows(role, path) for key, (role, path) in specs.items()}
    money_path = h + 'cost_resource/6cf441ef38e2c6c5/conditional_thresholds_with_product_keys.csv'
    money = rows('hypotheses', money_path)
    flex_summary = json.loads(read('hypotheses', h + 'c14_calendar_flex/13bad5060a24f3ce/summary.json'))
    for path in ['integration_v1/operating/coverage.csv', 'integration_v1/social/coverage.csv']:
        read('core', path)
    for path in ['modules/tourism/normalized/primary_validation.json', 'normalized/weather_validation.json']:
        read('alternative', path)
    positive = [r for r in data['FLEX'] if r['additional_booked_nights'] not in ('', 'UNKNOWN') and int(r['additional_booked_nights']) > 0]
    assert len(candidates) == 35 and len(inherited) == 107
    assert sum(c['selected_for_deepening'] == 'True' for c in candidates) == 9
    assert all(c['evaluation_status'] == 'NOT_EVALUATED' for c in candidates)
    assert len(data['AIRPORT']) == 1845 and len(data['ACCESS']) == 180 * 179 * 3 == 96660
    assert len(data['MUNICIPAL']) == 2022 and all(r['year'] == '2024' for r in data['MUNICIPAL'])
    assert len(registries['core']) == 90 and len(registries['alternative']) == 264
    assert len(data['C14']) == 24 and all(r['full_product_gate'] == 'UNKNOWN' for r in data['C14'])
    assert len(money) == 108 and len(data['C07']) == 3
    assert [int(r['elapsed_candidate_minutes']) for r in data['C07']] == [565, 610, 655]
    assert all(int(r['elapsed_candidate_minutes']) - int(r['elapsed_baseline_minutes']) == int(r['return_delay_vs_reference_minutes']) for r in data['C07'])
    assert len(positive) == flex_summary['positive_extensions'] == 10
    assert {int(r['additional_booked_nights']) for r in positive} == {1, 2, 3}
    assert flex_summary['beyond_capture_unknown'] == 2
    assert capacity['required_q'] == math.ceil(500000 / (2 * (8000 - 500))) == 34
    assert 34 + 80 == capacity['load_per_leg'] == 114
    assert 2 * 20 * (8000 - 500) - 500000 == capacity['margin_at_reserved_capacity_rub'] == -200000
    assert critic['decision'] == 'NOT_READY_FOR_STRATEGY_OR_LAUNCH'
    excerpts = {
        'AIRPORT': ([r for r in data['AIRPORT'] if r['iata_code'] in ('SVX', 'OMS')], [('airport_id','Ключ'),('iata_code','IATA'),('municipality','Город по справочнику'),('iana_timezone','Часовой пояс'),('snapshot_at_utc','Срез UTC')], 'Два объекта справочника аэропортов'),
        'ACCESS': (data['ACCESS'][:2], [('origin_area_id','Откуда'),('destination_area_id','Куда'),('mode','Транспорт'),('distance_hr','Часы'),('duration_status','Тип времени')], 'Две строки транспортной матрицы'),
        'MUNICIPAL': (data['MUNICIPAL'][:2], [('oktmo','Ключ'),('municipality','Муниципальное образование'),('year','Год'),('gross_monthly_wage_rub','Зарплата, ₽/месяц'),('annual_average_population_persons','Население, человек')], 'Соединение муниципальной зарплаты и населения'),
        'TOURISM': ([r for r in data['TOURISM'] if r['year']=='2025' and r['area_name']=='Алтайский край'][:2], [('dataset_id','Показатель'),('area_name','Территория'),('period','Месяц'),('ytd_value','С начала года'),('monthly_increment','За месяц'),('unit','Единица')], 'Накопленное значение и месячная разность'),
        'WEATHER': (data['WEATHER'][:2], [('station_id','Станция'),('icao','Код'),('month','Месяц'),('observed_hours','Часов в архиве'),('calendar_hours','Часов по календарю'),('temperature_mean_c','Средняя °C')], 'Исторические месяцы станции NOAA'),
        'BUSINESS': (data['BUSINESS'][:2], [('site_name','Площадка'),('group_id','Группа'),('locality_label_curated','Населённый пункт'),('relationship','Что установлено')], 'Две площадки корпоративной географии'),
        'MARKET': (data['MARKET'][:2], [('entity_id','Объект'),('period_start','Начало периода'),('period_end','Конец периода'),('value','Значение'),('unit','Единица')], 'Рыночные наблюдения с отдельными периодами'),
        'RULE': ([r for r in data['RULE'] if r['origin_iata']=='KVX'][:2], [('flight_number','Номер'),('weekdays_iso','День ISO'),('valid_from','Начало'),('valid_to','Конец'),('departure_local_time','Вылет'),('arrival_local_time','Прилёт')], 'Опубликованные правила Киров → Минеральные Воды'),
        'C14': (data['C14'][:2], [('booked_checkin_local_date','Условная дата заезда'),('booked_checkout_local_date','Условный выезд'),('hotel_nights','Ночей'),('return_departure_local','Обратный вылет по правилу'),('calendar_gate','Совпадение даты')], 'Один вылет, две трактовки даты заезда'),
        'FLEX': (positive[:2], [('original_checkout_local_date','Первоначальный выезд'),('next_captured_return_date','Поздний возврат'),('additional_booked_nights','Дополнительных ночей'),('extra_hotel_charge','Доплата'),('full_product_acceptance','Продукт целиком')], 'Условный перенос обратной даты'),
        'C01': (data['C01'][:1], [('candidate','Программа'),('outbound_origin_date','Вылет'),('one_way_journeys','Поездок туда/обратно'),('leg_seats_consumed','Посадок'),('roundtrip_customers','Клиентов RT'),('value_type','Тип')], 'Один клиент: две поездки и четыре посадки'),
        'RESOURCE': ([r for r in data['RESOURCE'] if r['candidate']=='C01'], [('resource','Ресурс'),('delta_block_minutes','Δ block, мин'),('delta_elapsed_minutes','Δ занятость, мин'),('first_departure_shift_minutes','Сдвиг вылета, мин'),('return_shift_minutes','Сдвиг возврата, мин')], 'Сценарное изменение ресурса C01'),
        'C07': (data['C07'], [('variant','Сценарий'),('legs_candidate','Плеч'),('block_candidate_minutes','Block, мин'),('elapsed_candidate_minutes','Оборот, мин'),('return_delay_vs_reference_minutes','Δ к 255 мин'),('donor_id','Донор')], 'Три варианта оборота C07'),
    }
    replacements = {'CANDIDATE_ROWS': candidate_table(candidates,inherited), 'C07_CHART': c07_chart(data['C07'])}
    team_replacements, team_checks = team_update()
    replacements.update(team_replacements)
    for key, (selected, columns, caption) in excerpts.items():
        assert selected
        replacements[key + '_EXAMPLE'] = table(selected, columns, caption, *specs[key])
    sources = {
        'CORE': ('core','integration_v1/phase2_handoff.md'), 'CORE_REGISTRY': ('core','source_registry.csv'),
        'ALT_REGISTRY': ('alternative','source_registry.csv'), 'HYPOTHESES': ('hypotheses','candidates.csv'),
        'ANCESTRY': ('hypotheses','existing_hypotheses.csv'), 'CRITIC': ('critic','integration_v1/professional_review.md'),
        'CRITIC_SCOPE': ('critic','integration_v1/phase2_handoff.json'), 'FLOW': ('critic','integration_v1/reviews/front2272/review.md'),
        'CAPACITY': ('critic','integration_v1/reviews/conditional_capacity/review.md'), 'LATE': ('critic','integration_v1/reviews/late_phase2/review.md'),
        'MONEY': ('hypotheses',money_path), 'C14': specs['C14'], 'FLEX': specs['FLEX'],
        'KOVER': ('coordinator','kover_scenario_spec.md'), 'SUMMARY': ('coordinator','coordinator/20261109T170202Z/summary.md'),
        'RECOVERY': ('recovery', 'report.md'), 'RECOVERY_INVENTORY': ('recovery', 'inventory.csv'),
        'RECOVERY_COSTS': ('recovery', 'parsed/khv_cost_components.csv'),
    }
    for label, (role,path) in sources.items():
        read(role,path)
        replacements['LINK_'+label] = link(role,path)
    pin_labels = {'nastya_step1':'Настя · шаг 1', 'tsiri_stage22':'Костя · stage22', 'tsiri_economics':'Костя · экономика', 'team_review':'Михаил · review и план context18', 'konstantin':'Константин · методы'}
    replacements['PIN_ROWS'] = ''.join(f'<tr><th scope="row">{pin_labels.get(role, role)}</th><td><a href="{REPO}/tree/{sha}"><code>{sha}</code></a></td></tr>' for role,sha in PINS.items())
    document = (ROOT/'templates/research-report.html').read_text()
    for key,value in replacements.items():
        document = document.replace('@@'+key+'@@',value)
    assert not re.search(r'@@[A-Z_]+@@',document), 'Unresolved token'
    assert all(x not in document for x in ['/Users/','file://','Set-Cookie','Bearer ','t3-thread://'])
    (ROOT/'research-report.html').write_text(document)
    checks = {'report':'research-report.html','programs':35,'attributed_records':107,'queue':9,'bounded_experiments':3,
              'source_cards':{'core':90,'alternative':264},'independent_source_count':'NOT_DETERMINED',
              'c14_calendar_rows':24,'c14_positive_extensions':10,'c14_beyond_capture_unknown':2,
              'c07_elapsed_minutes':[565,610,655],'c07_reference_minutes':255,'c07_deltas_minutes':[310,355,400],
              'conditional_capacity_fixture':'PASS','market_validation':'NOT_PERFORMED',
              'network_recovery':'BOUNDED_COMPLETE_NOT_INTEGRATED_IN_MODELS',
              'recovery_inventory_items':63,'recovery_http_reads':47,'recovery_scoped_sources':6}
    (OUT/'build_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
    (OUT/'input_manifest.json').write_text(json.dumps({'pins':PINS,'inputs':list(INPUTS.values()),
        'export_policy':'Selected normalized columns and authored explanation; no raw/private/full-text copies',
        'acceptance':'Presentation and consistency checks; no new market or launch acceptance'},ensure_ascii=False,indent=2)+'\n')
    TEAM_OUT.mkdir(parents=True, exist_ok=True)
    team_inputs = [v for v in INPUTS.values() if v['role'] in {'nastya_step1','tsiri_stage22','tsiri_economics','team_review','konstantin'}]
    (TEAM_OUT/'team_update_manifest.json').write_text(json.dumps({
        'attribution':{'nastya_step1':'Настя / kiruha355; explicit user identification',
                       'tsiri_stage22':'Костя / mput; explicit user identification',
                       'tsiri_economics':'Костя / mput; earlier economics version',
                       'team_review':'Михаил / Mput13; coordinator package, distinct from mput',
                       'konstantin':'Константин; attribution retained from team synthesis'},
        'pins':PINS,'inputs':team_inputs,'output':'research-report.html',
        'output_sha256':hashlib.sha256(document.encode()).hexdigest(),
        'excluded_as_final':'context/22_stage1_audit/model_outputs/scenario_summary.csv: BASELINE_ONLY_RESEARCH_NOT_INTEGRATED',
        'scope':'Saved artifacts and report presentation; no publication, push, new research or model replay',
    },ensure_ascii=False,indent=2)+'\n')
    (TEAM_OUT/'team_update_checks.json').write_text(json.dumps(team_checks,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(checks,ensure_ascii=False))

if __name__ == '__main__':
    main()
