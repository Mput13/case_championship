#!/usr/bin/env python3
"""Read pinned Git blobs; write only the data_bridge package. Python stdlib only.

This adapts outputs and checks joins/accounting. It does not execute or repair
authors' economic models, estimate missing OD, or grant operational acceptance.
"""
import csv
import datetime as dt
import hashlib
import io
import json
import math
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parents[1]
ROOT = OUT.parents[2]
PINS = {
    'core': '505e24663e5952bae9b9540bb9a5a622663bfc2a',
    'alternative': 'ef365ac2a936117e5b3bb12ea99c816d7b1a101c',
    'hypotheses': '6ed8788882e7b4d07044b4f6e686ff71eadd8ac5',
    'critic': 'fd086bad2ae30c46e95d6e38954dc99a18627902',
    'nastya': '2f03b693a62c219e9475fcd1e26295039f6a49d7',
    'ciri': '93fa5cf4a10ab67e05c93d19fc5375fc58ef9299',
    'ciri_stage1': '6ec84a7d2a6eb50b547a61df82fc5a424f48f146',
}
AUTHORS = {'core': 'Михаил / Mput13; Sol core research role',
           'alternative': 'Михаил / Mput13; Sol alternative research role',
           'hypotheses': 'Михаил / Mput13; GPT-6 Astra hypotheses role',
           'critic': 'Михаил / Mput13; Sol critic role',
           'nastya': 'Анастасия / kiruha355', 'ciri': 'Цири / mput',
           'ciri_stage1': 'Цири / mput'}
CP = 'context/16_agent_research/core/'
AP = 'context/16_agent_research/alternative/'
HP = 'context/16_agent_research/hypotheses/'
C16 = 'context/16_conditional_decision/model/'
inputs, tables, joins, join_rows, checks, coverage = {}, {}, [], [], [], []
fields = {}


def digest(b):
    return hashlib.sha256(b).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def load(role, path, grain, units='', status='PARSED_PINNED_OUTPUT', fmt='csv'):
    key = role + ':' + path
    if key in inputs:
        return inputs[key]['data']
    raw = git('show', PINS[role] + ':' + path)
    log = git('log', '-1', '--format=%H%x09%an%x09%aI', PINS[role], '--', path).decode().strip().split('\t')
    text = raw.decode('utf-8-sig')
    data = json.loads(text) if fmt == 'json' else (text if fmt == 'text' else list(csv.DictReader(io.StringIO(text))))
    rec = dict(input_id='IN:' + digest(key.encode())[:16], role=role, source_commit=PINS[role],
               source_path=path, sha256=digest(raw), bytes=len(raw), grain=grain, units=units,
               artifact_author_ref=AUTHORS[role], last_file_commit=log[0], last_file_git_author=log[1],
               last_file_authored_at=log[2], stage=status, rows=len(data) if isinstance(data, list) else '',
               raw_acquisition_status='NOT_ESTABLISHED_BY_GIT_BLOB; bounded selected raw in checks/raw_receipts.csv',
               parse_status='TEXT_SOURCE_INSPECTED' if fmt=='text' else ('JSON_PARSED' if fmt=='json' else 'CSV_PARSED'),
               validation_status='SCOPED_CHECKS_IN_VERIFICATION; not blanket source support',
               data=data)
    inputs[key] = rec
    return data


def sid(role, path):
    return inputs[role + ':' + path]['input_id']


def dump(name, obj):
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def write(name, rows, columns=None):
    rows = list(rows)
    if columns is None:
        columns = list(dict.fromkeys(k for r in rows for k in r))
    if not columns:
        raise ValueError('An empty table needs its real schema: ' + name)
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=columns, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    tables[name] = dict(rows=len(rows), fields=columns)


def check(name, ok, detail, scope='ADAPTER_OFFLINE'):
    checks.append(dict(check_id=name, status='PASS' if ok else 'FAIL', detail=detail, scope=scope))


def unique(name, rows, key):
    counts = Counter(tuple(r[k] for k in key) for r in rows)
    dup = [dict(key=list(k), rows=n) for k, n in counts.items() if n > 1]
    check('UNIQUE:' + name, not dup, dict(grain=key, rows=len(rows), duplicate_keys=dup[:15]))
    return {tuple(r[k] for k in key): r for r in rows} if not dup else None


def num(v):
    return None if v is None or str(v).strip() in ('', 'UNKNOWN', 'ND') else float(v)


def near(a, b, tol=1e-6):
    return math.isclose(a, b, rel_tol=1e-10, abs_tol=tol)


def meta(model, scenario='', candidate='', scope='', market='', start='', end='', status='SCENARIO'):
    role = model.split(':')[0]
    return dict(model_id=model, author_ref=AUTHORS[role], source_commit=PINS[role],
                input_set_id='BRIDGE:' + role + ':' + PINS[role][:12], run_id='OUTPUT_ADAPTER_V1',
                scenario_id=scenario, candidate_id=candidate, period_start=start, period_end=end,
                direction_scope='DIRECTED' if model.startswith(('ciri:', 'hypotheses:')) else 'BOTH_DIRECTIONS',
                market_unit=market, currency='RUB' if model.startswith(('ciri:', 'nastya:network')) else '',
                price_basis='', tax_basis='', value_status=status, acceptance_scope=scope,
                metadata_missing_reason='Price/tax/period unset where not established by pinned output; see table dictionary')


def trace(join, left_id, right_id, status, left_source, right_source, reason=''):
    join_rows.append(dict(join_id=join, left_row_id=left_id, right_row_id=right_id,
                          join_status=status, left_input_id=left_source, right_input_id=right_source,
                          reason=reason))


def join_summary(name, left_rows, output_rows, matched, unmatched, cardinality, sums='', note=''):
    joins.append(dict(join_id=name, left_rows=left_rows, output_rows=output_rows,
                      matched_left_rows=matched, unmatched_left_rows=unmatched,
                      cardinality=cardinality, conservation=sums, note=note))


def main():
    airport_path = CP + 'integration_v1/operating/airport_keys.csv'
    airports = load('core', airport_path, 'airport directory id × frozen version', 'IATA/ICAO; IANA; directory identifiers')
    unique('airport_ids', airports, ['airport_id'])
    by_iata = defaultdict(list)
    for a in airports:
        if a['iata']:
            by_iata[a['iata']].append(a)
    quarantine = load('core', CP + 'integration_v1/operating/quarantine.csv', 'quarantine record id')
    tz = load('core', CP + 'integration_v1/operating/timezone_keys.csv', 'IANA × reference date', 'UTC offset minutes at stated date')
    unique('timezones', tz, ['iana_timezone', 'reference_date'])
    tz_by_zone = {r['iana_timezone']: r for r in tz}
    resolutions = {}

    def resolve(code):
        if code in resolutions:
            return resolutions[code]
        opts = by_iata.get(code, [])
        if code == 'MOW':
            r = dict(entity_code=code, airport_id='', airport_key_version='', iana_timezone='', timezone_key_version='',
                     key_status='GROUP_NOT_AIRPORT', missing_reason='Author groups SVO/DME/VKO/ZIA; never choose one physical airport', source_region_id='')
        elif len(opts) != 1:
            r = dict(entity_code=code, airport_id='', airport_key_version='', iana_timezone='', timezone_key_version='',
                     key_status='UNMATCHED' if not opts else 'AMBIGUOUS_IATA', missing_reason='No unique frozen airport directory match', source_region_id='')
        elif opts[0]['key_acceptance'] == 'QUARANTINE':
            a = opts[0]
            r = dict(entity_code=code, airport_id='', airport_key_version='', iana_timezone='', timezone_key_version='',
                     key_status='QUARANTINE', missing_reason=a['quarantine_reason'], source_region_id='', held_directory_id=a['airport_id'])
        else:
            a = opts[0]
            r = dict(entity_code=code, airport_id=a['airport_id'], airport_key_version=a['airport_key_version'],
                     iana_timezone=a['iana_timezone'], timezone_key_version=a['timezone_key_version'],
                     key_status='MATCHED_UNIQUE_DIRECTORY', missing_reason='' if a['iana_timezone'] else a['timezone_status'],
                     source_region_id=a['source_region_id'], directory_name=a['name'], directory_icao=a['icao'],
                     identity_acceptance=a['key_acceptance'], timezone_acceptance=a['timezone_status'])
        resolutions[code] = r
        return r

    # Actual model dependency snapshots; this is read-only source inspection.
    source_code = {}
    for role, path in [('nastya', 'src/network_model.py'), ('nastya', 'src/demand_model.py'),
                       ('nastya', 'src/longlist_score.py'), ('nastya', 'src/build_criteria.py'),
                       ('ciri', 'scripts/build_conditional_decision.py'),
                       ('ciri', 'scripts/build_team_comparison.py'),
                       ('ciri_stage1', 'src/stage1_audit_rules.py'),
                       ('hypotheses', HP+'experiment_v1/scripts/evaluate.py'),
                       ('hypotheses', HP+'experiment_v1/scripts/core_operating_join.py')]:
        # A named file is required; no glob-driven execution of collaborators' code.
        if path in git('ls-tree', '-r', '--name-only', PINS[role], path).decode().splitlines():
            source_code[(role, path)] = load(role, path, 'source code file', fmt='text')
    critic = load('critic', 'context/16_agent_research/critic/findings.csv', 'finding id × reviewed input SHA')
    write('normalized/historical_findings.csv', critic)

    ll_path, criteria_path = 'data/processed/longlist.csv', 'data/processed/criteria.json'
    ll = load('nastya', ll_path, 'candidate airport IATA', 'mixed screening proxies with field-level definitions')
    unique('nastya_longlist', ll, ['iata'])
    criteria = load('nastya', criteria_path, 'criterion definition; candidate×criterion values', fmt='json')
    routes = load('nastya', 'data/processed/network_routes.csv', 'scenario × variant × from × to', 'annual passenger segments; weekly frequency each direction')
    summary = load('nastya', 'data/processed/network_summary.csv', 'scenario × strategy', 'million RUB/annual model horizon; annual segments and journeys')
    demand = load('nastya', 'data/processed/demand_pairs.csv', 'unordered pair', 'annual bidirectional modeled route segment flow')
    assumptions = load('nastya', 'data/assumptions/network.csv', 'parameter', 'per parameter')
    known = load('nastya', 'data/manual/known_flows.csv', 'reported flow source row', 'per source row; mixed period/coverage')
    unique('nastya_route', routes, ['scenario', 'variant', 'from', 'to'])
    unique('nastya_pairs', demand, ['a', 'b'])

    cand_path = HP + 'candidates.csv'
    products = load('hypotheses', cand_path, 'candidate_id', 'research specification; numeric demand unknown')
    unique('hypotheses35', products, ['candidate_id'])
    reg, links, route_program, templates = [], [], [], []
    for n, r in enumerate(ll, 2):
        code = r['iata']; a = resolve(code)
        reg.append(dict(**meta('nastya:screening', candidate=code, scope='AUTHOR_SCREENING_OUTPUT_ADAPTED', market='SCREENING_PROXY', status='MODEL'),
                        title=r['city'], object_type='CITY_SCREENING', source_input_id=sid('nastya', ll_path), source_row=n))
        links.append(dict(model_id='nastya:screening', candidate_id=code, role='SCREENED_AIRPORT', entity_code=code,
                          airport_id=a['airport_id'], airport_key_version=a['airport_key_version'], key_status=a['key_status'],
                          source_input_id=sid('nastya', ll_path), source_row=n, token_position=1))
    for n, r in enumerate(products, 2):
        cid = r['candidate_id']
        reg.append(dict(**meta('hypotheses:register35', candidate=cid, scope='RESEARCH_SPECIFICATION_ONLY', market='UNKNOWN_FINAL_OD', status='SCENARIO'),
                        title=r['title'], object_type='PASSENGER_PRODUCT_OR_NETWORK_RESEARCH', network_form=r['network_form'],
                        source_input_id=sid('hypotheses', cand_path), source_row=n, specification_author=r['author'],
                        source_demand_status=r['demand_status']))
        for pno, path in enumerate(r['proposed_paths'].split(';'), 1):
            codes = path.strip().split('>')
            if not all(re.fullmatch('[A-Z0-9]{3}', c) for c in codes):
                raise ValueError('Unparsed author path ' + cid + ':' + path)
            tid = cid + ':PATH:' + str(pno)
            templates.append(dict(candidate_id=cid, template_id=tid, path=path, origin=codes[0], destination=codes[-1],
                                  leg_count=len(codes)-1, template_kind='AUTHOR_PATH_NOT_NECESSARILY_ONE_SOLD_ITINERARY',
                                  market_status='UNKNOWN', unit='named airport sequence', source_input_id=sid('hypotheses', cand_path), source_row=n))
            for pos, code in enumerate(codes, 1):
                a = resolve(code)
                links.append(dict(model_id='hypotheses:register35', candidate_id=cid, role='PATH_AIRPORT', entity_code=code,
                                  airport_id=a['airport_id'], airport_key_version=a['airport_key_version'], key_status=a['key_status'],
                                  source_input_id=sid('hypotheses', cand_path), source_row=n, token_position=str(pno)+':'+str(pos)))
                trace('J_PRODUCT_AIRPORT', cid+':'+str(pno)+':'+str(pos), a['airport_key_version'], a['key_status'],
                      sid('hypotheses', cand_path), sid('core', airport_path), a['missing_reason'])
    for n, r in enumerate(routes, 2):
        cid = r['variant'][4:] if r['variant'].startswith('Хаб ') else 'DIRECT_PORTFOLIO'
        for pos, code in enumerate([r['from'], r['to']], 1):
            a = resolve(code)
            links.append(dict(model_id='nastya:network', candidate_id=cid, role='PROGRAM_ENDPOINT', entity_code=code,
                              airport_id=a['airport_id'], airport_key_version=a['airport_key_version'], key_status=a['key_status'],
                              source_input_id=sid('nastya', 'data/processed/network_routes.csv'), source_row=n, token_position=pos))
        route_program.append(dict(**meta('nastya:network', r['scenario'], cid, 'AUTHOR_OUTPUT_ONLY; NO_DATED_SEAT_LEDGER',
                                         'ANNUAL_BIDIRECTIONAL_SEGMENTS', status='MODEL'),
                                  variant=r['variant'], origin_code=r['from'], destination_code=r['to'],
                                  origin_airport_key=resolve(r['from'])['airport_key_version'], destination_airport_key=resolve(r['to'])['airport_key_version'],
                                  frequency_each_way_week=r['freq_week_each_way'], passenger_segments_annual=r['pax_year_segments'],
                                  local_segments_annual=r['pax_year_local'], transfer_segments_annual=r.get('pax_year_transfer_seg', ''),
                                  flight_date='', date_missing_reason='Only annualized/weekly aggregate exported',
                                  source_input_id=sid('nastya', 'data/processed/network_routes.csv'), source_row=n))
    write('normalized/route_program.csv', route_program)
    write('normalized/product_path_template.csv', templates)

    # Ciri's dated, directional conditional program. Never pool alternative networks together.
    markets = load('ciri', C16+'markets.csv', 'unordered endpoint pair', 'journeys/week/direction; RUB/whole one-way journey')
    sales = load('ciri', C16+'sales.csv', 'network × scenario × priority × dated itinerary', 'endpoint journeys; one whole-journey revenue')
    flights = load('ciri', C16+'flights.csv', 'network × flight id', 'dated seats; UTC minute; block minute')
    capacities = load('ciri', C16+'capacity.csv', 'network × scenario × priority × flight id', 'seats; passenger segments')
    resources = load('ciri', C16+'resources.csv', 'network', 'block hours/week; aircraft; legs/week')
    comparisons = load('ciri', C16+'comparison.csv', 'network × scenario × priority', 'RUB/week; journeys/week; segments/week')
    load('ciri', C16+'assumptions.json', 'scenario assumptions', fmt='json')
    # Separate Ciri branches are inputs with different purposes, not a chronological upgrade.
    check('CIRI_STAGE1_BRANCH_NOT_ECONOMIC_UPGRADE',
          not git('ls-tree','-r','--name-only',PINS['ciri_stage1'],C16+'comparison.csv').strip(),
          '6ec84a7d stage1 branch does not contain conditional16 comparison.csv; economic input remains93fa5cf4')
    stage1_scores=load('ciri_stage1','context/22_stage1_audit/model_outputs/scores_samara_excluded_min500_base.csv',
                       'candidate IATA after author filter; explicit scenario','screening score; not network economics')
    stage1_normalized=[]
    for n,r in enumerate(stage1_scores,2):
        m=meta('ciri_stage1:screening','samara_excluded_min500_base',r['iata'],
               'AUTHOR_STAGE1_SCREENING_PROPOSAL_ONLY','SCREENING_SCORE',status='MODEL')
        stage1_normalized.append(dict(**m,**r,source_input_id=sid('ciri_stage1','context/22_stage1_audit/model_outputs/scores_samara_excluded_min500_base.csv'),source_row=n))
        reg.append(dict(**m,title=r['city'],object_type='CITY_SCREENING',source_input_id=sid('ciri_stage1','context/22_stage1_audit/model_outputs/scores_samara_excluded_min500_base.csv'),source_row=n))
        a=resolve(r['iata'])
        links.append(dict(model_id='ciri_stage1:screening',candidate_id=r['iata'],role='SCREENED_AIRPORT',entity_code=r['iata'],
                          airport_id=a['airport_id'],airport_key_version=a['airport_key_version'],key_status=a['key_status'],
                          source_input_id=sid('ciri_stage1','context/22_stage1_audit/model_outputs/scores_samara_excluded_min500_base.csv'),source_row=n,token_position=1))
    write('normalized/ciri_stage1_scores.csv',stage1_normalized)
    load('ciri_stage1','context/22_stage1_audit/model_rules.json','audit rules scenario',fmt='json')
    fidx = unique('ciri_flights', flights, ['network','id'])
    cidx = unique('ciri_capacity', capacities, ['network','scenario','priority','id'])
    midx = unique('ciri_markets', markets, ['pair'])
    unique('ciri_comparisons', comparisons, ['network','scenario','priority'])
    physical, itinerary, itlegs, allocations, money, pools, evaluations, resledger = [], [], [], [], [], [], [], []
    for n, r in enumerate(flights, 2):
        a, b = resolve(r['origin']), resolve(r['destination'])
        key = 'CIRI:'+r['network']+':'+r['id']
        base = meta('ciri:conditional16', candidate=r['network'], scope='DATED_SCENARIO_FLIGHT_ONLY', market='SEATS', start='2026-12-07', end='2026-12-13')
        physical.append(dict(**base, physical_leg_id=key, author_flight_id=r['id'], origin=r['origin'], destination=r['destination'],
                             origin_airport_key=a['airport_key_version'], destination_airport_key=b['airport_key_version'],
                             departure_date=r['date'], departure_utc_minute=r['departure_utc_minute'], arrival_utc_minute=r['arrival_utc_minute'],
                             block_minutes=r['block_minutes'], seats=r['capacity'], execution_status='UNKNOWN',
                             time_basis='Author minute axis; unchanged', source_input_id=sid('ciri',C16+'flights.csv'), source_row=n))
    for n, r in enumerate(markets, 2):
        a, b = r['pair'].split('-')
        for scen in ['base','cautious']:
            for origin,destination in [(a,b),(b,a)]:
                pool = 'CIRI_POOL:'+scen+':'+origin+'>'+destination
                pools.append(dict(**meta('ciri:conditional16', scen, scope='COMMON_SCENARIO_MARKET_POOL; NOT_OBSERVED_OD',
                                         market='ENDPOINT_JOURNEYS/WEEK/DIRECTION',start='2026-12-07',end='2026-12-13'),
                                  market_pool_id=pool, origin=origin, destination=destination, pool_journeys=r['demand_'+scen],
                                  observed_journeys='', observed_missing_reason='Source observed_OD empty; author common-band assumption',
                                  common_pool_policy='Each network is a mutually exclusive strategy. Sum only within one network/scenario/priority.',
                                  source_input_id=sid('ciri',C16+'markets.csv'), source_row=n))
    poolidx = {r['market_pool_id']:r for r in pools}
    use = defaultdict(float); sold_pools = defaultdict(float); sums = defaultdict(lambda:defaultdict(float))
    leg_errors=[]; money_errors=[]; journey_errors=[]
    for n, r in enumerate(sales, 2):
        iid='CIRI_IT:'+str(n-1)
        ids=r['flight_ids'].split(';')
        base=meta('ciri:conditional16',r['scenario'],r['network'],'SCENARIO_LEDGER_ADAPTED',
                  'DIRECTED_ENDPOINT_JOURNEYS', '2026-12-07','2026-12-13')
        pool='CIRI_POOL:'+r['scenario']+':'+r['origin']+'>'+r['destination']
        itinerary.append(dict(**base,itinerary_id=iid,priority=r['priority'],origin=r['origin'],destination=r['destination'],
                              departure_date=r['date'],market_pool_id=pool,sold_journeys=r['sold_journeys'],
                              local_journeys=r['local_journeys'],transfer_journeys=r['transfer_journeys'],net_new_journeys=r['net_new_journeys'],
                              migrated_RW_journeys=r['migrated_RW_total'],whole_journey_fare_rub=r['effective_fare'],
                              fare_status='SCENARIO',segment_pax=r['segment_pax'],leg_count=len(ids),
                              source_input_id=sid('ciri',C16+'sales.csv'),source_row=n))
        journey=float(r['sold_journeys'])
        if not near(float(r['segment_pax']), journey*len(ids)):
            journey_errors.append(iid)
        if not near(float(r['gross_revenue']), journey*float(r['effective_fare'])):
            money_errors.append(iid)
        sold_pools[(r['network'],r['scenario'],r['priority'],pool)]+=journey
        previous=None
        for pos,fid in enumerate(ids,1):
            flight=fidx.get((r['network'],fid))
            if flight is None:
                leg_errors.append(dict(itinerary_id=iid,flight_id=fid,reason='NO_FLIGHT_KEY'));continue
            key='CIRI:'+r['network']+':'+fid
            if pos==1 and flight['origin']!=r['origin']:leg_errors.append(dict(itinerary_id=iid,reason='ORIGIN_MISMATCH'))
            if pos==len(ids) and flight['destination']!=r['destination']:leg_errors.append(dict(itinerary_id=iid,reason='DESTINATION_MISMATCH'))
            if previous and (previous['destination']!=flight['origin'] or float(previous['arrival_utc_minute'])>float(flight['departure_utc_minute'])):
                leg_errors.append(dict(itinerary_id=iid,reason='BROKEN_OR_REVERSED_CONNECTION'))
            previous=flight
            itlegs.append(dict(**base,itinerary_id=iid,leg_sequence=pos,physical_leg_id=key,seat_segments_used=r['sold_journeys'],priority=r['priority']))
            allocations.append(dict(**base,itinerary_id=iid,physical_leg_id=key,priority=r['priority'],allocated_seats=r['sold_journeys'],allocation_status='FRACTIONAL_SCENARIO'))
            use[(r['network'],r['scenario'],r['priority'],fid)]+=journey
            trace('J_SALES_FLIGHT',iid+':'+str(pos),key,'MATCHED_UNIQUE',sid('ciri',C16+'sales.csv'),sid('ciri',C16+'flights.csv'))
        for account in ['gross_revenue','foregone_RW_revenue','incremental_revenue','new_pax_variable','saved_old_pax_variable']:
            money.append(dict(**base,ledger_row_id=iid+':'+account,itinerary_id=iid,priority=r['priority'],account=account,
                              amount_rub=r[account],unit='RUB/WEEK',aggregation_rule='Do not add gross/foregone/incremental together; incremental=gross-foregone',
                              source_input_id=sid('ciri',C16+'sales.csv'),source_row=n))
        for k in ['sold_journeys','segment_pax','transfer_journeys','net_new_journeys','gross_revenue','foregone_RW_revenue','incremental_revenue','new_pax_variable','saved_old_pax_variable']:
            sums[(r['network'],r['scenario'],r['priority'])][k]+=float(r[k])
        trace('J_ITINERARY_POOL',iid,pool,'MATCHED_UNIQUE' if pool in poolidx else 'UNMATCHED',sid('ciri',C16+'sales.csv'),sid('ciri',C16+'markets.csv'))
    check('CIRI_ITINERARY_PHYSICAL_FK_CONTINUITY',not leg_errors,leg_errors[:20])
    check('CIRI_ONE_FARE_PER_JOURNEY',not money_errors,dict(rows=len(sales),failures=money_errors[:20]))
    check('CIRI_TWO_SEATS_FOR_TWO_LEGS',not journey_errors,dict(rows=len(sales),failures=journey_errors[:20]))
    cap_errors=[]; cap_checks=[]
    flight_cost_sums=defaultdict(float)
    for r in capacities:
        key=(r['network'],r['scenario'],r['priority'],r['id']);actual=use.get(key,0)
        ok=near(actual,float(r['sold_segment_pax'])) and actual<=float(r['capacity'])+1e-7
        cap_checks.append(dict(network=key[0],scenario=key[1],priority=key[2],flight_id=key[3],adapter_segment_pax=actual,
                               source_segment_pax=r['sold_segment_pax'],capacity=r['capacity'],delta=actual-float(r['sold_segment_pax']),status='PASS' if ok else 'FAIL'))
        if not ok:cap_errors.append(key)
        flight_cost_sums[key[:3]]+=float(r['flight_variable_cost'])
        money.append(dict(**meta('ciri:conditional16',r['scenario'],r['network'],'SCENARIO_FLIGHT_COST_ADAPTED',
                                'RUB/WEEK','2026-12-07','2026-12-13'),
                          ledger_row_id='CIRI_FLIGHT_COST:'+r['network']+':'+r['scenario']+':'+r['priority']+':'+r['id'],
                          itinerary_id='',physical_leg_id='CIRI:'+r['network']+':'+r['id'],priority=r['priority'],
                          account='flight_variable_cost',amount_rub=r['flight_variable_cost'],unit='RUB/WEEK',
                          aggregation_rule='One physical flight cost per network/scenario/priority; no multiplication by itineraries',
                          source_input_id=sid('ciri',C16+'capacity.csv')))
    check('CIRI_CAPACITY_SOURCE_MATCH_AND_BOUND',not cap_errors,dict(rows=len(capacities),failures=cap_errors[:20]))
    pool_checks=[]
    for (network,scen,priority,pool),value in sorted(sold_pools.items()):
        bound=num(poolidx[pool]['pool_journeys']) if pool in poolidx else None
        pool_checks.append(dict(network=network,scenario=scen,priority=priority,market_pool_id=pool,
                                sold_journeys=value,pool_journeys=bound,remaining_journeys=None if bound is None else bound-value,
                                status='PASS' if bound is not None and value<=bound+1e-6 else 'FAIL'))
    check('CIRI_SHARED_MARKET_POOL_WITHIN_STRATEGY',all(r['status']=='PASS' for r in pool_checks),dict(tested_groups=len(pool_checks),failed=sum(r['status']=='FAIL' for r in pool_checks)))
    check('CIRI_ALLOCATION_ALL_PHYSICAL_KEYS_PRESENT',set(use).issubset(set(cidx)),
          dict(used_flight_scenario_keys=len(use),source_capacity_keys=len(cidx)))
    check('CIRI_ALLOCATION_GRAND_TOTAL_PRESERVED',near(sum(use.values()),sum(float(r['segment_pax']) for r in sales)),
          dict(itinerary_segment_pax=sum(float(r['segment_pax']) for r in sales),allocated_seat_segments=sum(use.values()),
               caution='Grand totals across exclusive networks/scenarios are checksums, not one network/market forecast'))
    eval_errors=[]; economics_checks=[]
    for n,r in enumerate(comparisons,2):
        base=meta('ciri:conditional16',r['scenario'],r['network'],'AUTHOR_OUTPUT_ACCOUNTING_RECONCILED_IF_CHECKS_PASS',
                  'DIRECTED_ENDPOINT_JOURNEYS/WEEK','2026-12-07','2026-12-13')
        row=dict(**base,priority=r['priority'],sold_journeys=r['sold_journeys'],segment_pax=r['segment_pax'],transfer_journeys=r['transfer_journeys'],
                 net_new_journeys=r['net_new_journeys'],gross_revenue_rub=r['gross_revenue'],incremental_revenue_rub=r['incremental_revenue'],
                 contribution_before_fixed_rub=r['contribution_before_base_fleet_opportunity'],full_budget_rub='',
                 full_budget_missing_reason='Source fleet/opportunity blank; unknown base/startup/support/exit/working capital; not zero',
                 aircraft_available='',resource_limit_active='4',resource_limit_reserve='1',source_input_id=sid('ciri',C16+'comparison.csv'),source_row=n)
        evaluations.append(row)
        expected=sums[(r['network'],r['scenario'],r['priority'])]
        for k,v in expected.items():
            if not near(v,float(r[k])):eval_errors.append(dict(network=r['network'],scenario=r['scenario'],field=k,adapter=v,source=r[k]))
        cost=flight_cost_sums[(r['network'],r['scenario'],r['priority'])]
        recomputed=float(r['incremental_revenue'])-cost-float(r['new_pax_variable'])+float(r['saved_old_pax_variable'])
        economics_checks.append(dict(network=r['network'],scenario=r['scenario'],priority=r['priority'],
                                     flight_cost_delta=cost-float(r['flight_variable_cost']),
                                     incremental_revenue_delta=float(r['incremental_revenue'])-(float(r['gross_revenue'])-float(r['foregone_RW_revenue'])),
                                     contribution_delta=recomputed-float(r['contribution_before_base_fleet_opportunity']),
                                     status='PASS' if near(cost,float(r['flight_variable_cost'])) and near(recomputed,float(r['contribution_before_base_fleet_opportunity'])) else 'FAIL'))
    check('CIRI_LEDGER_TO_SUMMARY',not eval_errors,eval_errors[:20])
    check('CIRI_FLIGHT_COST_AND_CONTRIBUTION_RECONCILE',all(r['status']=='PASS' and abs(r['incremental_revenue_delta'])<1e-6 for r in economics_checks),economics_checks)
    for n,r in enumerate(resources,2):
        resledger.append(dict(**meta('ciri:conditional16',candidate=r['network'],scope='AUTHOR_ALGEBRAIC_RESOURCE_OUTPUT_ONLY',
                                    market='AIRCRAFT/BLOCK_HOURS',start='2026-12-07',end='2026-12-13'),
                              weekly_block_hours=r['weekly_block_hours'],weekly_legs=r['weekly_legs'],active_aircraft=r['active_allocated'],
                              active_ceiling=r['active_aircraft_limit'],reserve_aircraft=r['spares'],actual_available_aircraft='',
                              actual_available_missing_reason='Not observed in source',source_input_id=sid('ciri',C16+'resources.csv'),source_row=n))
        reg.append(dict(**meta('ciri:conditional16',candidate=r['network'],scope='CONDITIONAL_NETWORK_SCENARIO',market='ENDPOINT_JOURNEYS/WEEK',
                               start='2026-12-07',end='2026-12-13'),title=r['network'],object_type='DATED_ROUTE_PORTFOLIO',source_input_id=sid('ciri',C16+'resources.csv'),source_row=n))
    resource_errors=[]
    for r in resources:
        ff=[f for f in flights if f['network']==r['network']]
        if len(ff)!=int(r['weekly_legs']) or not near(sum(float(f['block_minutes']) for f in ff)/60,float(r['weekly_block_hours'])):
            resource_errors.append(r['network'])
    check('CIRI_FLIGHT_TO_RESOURCE_RECONCILE',not resource_errors,dict(networks=len(resources),failures=resource_errors))
    for n,r in enumerate(summary,2):
        cid=r['hub'] or 'DIRECT_PORTFOLIO'
        evaluations.append(dict(**meta('nastya:network',r['scenario'],cid,'AGGREGATE_AUTHOR_OUTPUT_ADAPTED; NO_DATED_CAPACITY_OR_OD_EQUIVALENCE',
                                       'ANNUAL_BIDIRECTIONAL_MODELED_FLOW',status='MODEL'),
                                sold_journeys=r['od_trips_year'],segment_pax=r['segments_year'],transfer_journeys=r['transfer_od_year'],
                                gross_revenue_rub=float(r['revenue_mln_year'])*1e6,contribution_before_fixed_rub=float(r['result_mln_year'])*1e6,
                                full_budget_rub='',full_budget_missing_reason='Lease/base/office and launch/support/working capital absent; not zero',
                                author_rounding='million RUB rounded to integer',period_missing_reason='Annual model horizon; no dated year in export',
                                source_input_id=sid('nastya','data/processed/network_summary.csv'),source_row=n))
        if r['scenario']=='base':
            reg.append(dict(**meta('nastya:network',candidate=cid,scope='AGGREGATE_ROUTE_STRATEGY',market='ANNUAL_MODELED_SEGMENT_FLOW',status='MODEL'),
                            title=r['variant'],object_type='UNDATED_ROUTE_PORTFOLIO',source_input_id=sid('nastya','data/processed/network_summary.csv'),source_row=n))
    ncons=[]
    for r in summary:
        delta=float(r['segments_year'])-float(r['od_trips_year'])-float(r['transfer_od_year'])
        ncons.append(dict(scenario=r['scenario'],candidate=r['hub'] or 'DIRECT_PORTFOLIO',
                          segments_minus_journeys_minus_transfer=delta,rounding_tolerance=2,status='PASS_ROUNDING' if abs(delta)<=2 else 'FAIL'))
    check('NASTYA_EXPORTED_AGGREGATE_SEGMENT_IDENTITY',all(r['status']=='PASS_ROUNDING' for r in ncons),ncons,
          'AUTHOR_OUTPUT_ARITHMETIC_ONLY; NOT_MARKET_OR_DATED_CAPACITY_ACCEPTANCE')
    # Add the actual frozen research experiment physical legs; distinct from the 35 specifications.
    hlegs_path=HP+'experiment_v1/runs/c26661067277af20/physical_legs.csv'
    hlegs=load('hypotheses',hlegs_path,'variant × leg id','dated nominal scenario seats; UTC timestamps')
    unique('hypotheses_physical',hlegs,['variant','leg_id'])
    for n,r in enumerate(hlegs,2):
        physical.append(dict(**meta('hypotheses:experiment3',r['variant'],r['variant'][:3],'AUTHOR_SCENARIO_PHYSICAL_REQUIREMENT; NOT_OBSERVED_FLIGHT',
                                    'NOMINAL_SCENARIO_SEATS','2026-12-07','2026-12-27'),
                             physical_leg_id='HYP:'+r['variant']+':'+r['leg_id'],author_flight_id=r['leg_id'],
                             origin=r['origin'],destination=r['destination'],origin_airport_key=resolve(r['origin'])['airport_key_version'],
                             destination_airport_key=resolve(r['destination'])['airport_key_version'],departure_utc=r['departure_utc'],arrival_utc=r['arrival_utc'],
                             block_minutes=r['block_minutes'],seats=r['nominal_seats'],execution_status='UNKNOWN',
                             time_basis='UTC and explicit local offsets per frozen experiment',source_input_id=sid('hypotheses',hlegs_path),source_row=n))
        physical[-1]['source_run_id']='c26661067277af20'
    threshold_path=HP+'experiment_v1/cost_resource/6cf441ef38e2c6c5/conditional_thresholds_with_product_keys.csv'
    thresholds=load('hypotheses',threshold_path,'candidate × product template × gap × fare × variable cost','RUB/paired cohort; journeys/direction; customer roundtrips')
    write('normalized/hypothesis_thresholds.csv', [dict(**meta('hypotheses:experiment3',candidate=r['candidate'],
          scope='ILLUSTRATIVE_COHORT_THRESHOLD_NOT_FORECAST',market='ONEWAY_JOURNEYS/PAIRED_COHORT'),
          **r,source_input_id=sid('hypotheses',threshold_path),source_run_id='6cf441ef38e2c6c5',source_row=n) for n,r in enumerate(thresholds,2)])
    for path,data in [('candidate_register',reg),('candidate_airport_link',links),('physical_leg',physical),
                      ('market_pool',pools),('itinerary',itinerary),('itinerary_leg',itlegs),('capacity_allocation',allocations),
                      ('money_ledger',money),('resource_ledger',resledger),('evaluation_summary',evaluations)]:
        write('normalized/'+path+'.csv',data)
    unique('candidate_register',reg,['model_id','candidate_id'])
    unique('itinerary_id',itinerary,['itinerary_id'])
    unique('itinerary_leg',itlegs,['itinerary_id','leg_sequence'])
    unique('physical_leg',physical,['physical_leg_id'])
    write('checks/ciri_capacity.csv',cap_checks)
    write('checks/ciri_market_pool.csv',pool_checks)
    write('checks/ciri_economics.csv',economics_checks)
    write('checks/nastya_segment_identity.csv',ncons)
    join_summary('J_SALES_FLIGHT',len(sales),len(itlegs),len(sales),0,'1:N intentional itinerary leg expansion',
                 'Journeys counted once in itinerary; seats once per physical leg; revenue stays in money_ledger',
                 'Do not sum itinerary revenue after joining to itinerary_leg')
    join_summary('J_ITINERARY_POOL',len(sales),len(itinerary),sum(r['market_pool_id'] in poolidx for r in itinerary),
                 sum(r['market_pool_id'] not in poolidx for r in itinerary),'N:1')

    # Join existing published calendars to real directory IDs without treating them as executed legs.
    dated_path=CP+'integration_v1/c14_addendum_v1/outputs/operating_dated_instances_union.csv'
    dated=load('core',dated_path,'instance id','published local calendar expansion; UTC date if derivable')
    unique('core_dated_union',dated,['instance_id'])
    dated_norm=[]; clock_errors=[]
    for n,r in enumerate(dated,2):
        a,b=resolve(r['origin_iata']),resolve(r['destination_iata'])
        row=dict(r,bridge_origin_airport_key=a['airport_key_version'],bridge_destination_airport_key=b['airport_key_version'],
                 bridge_origin_key_status=a['key_status'],bridge_destination_key_status=b['key_status'],
                 bridge_input_id=sid('core',dated_path),bridge_source_row=n)
        dated_norm.append(row)
        if r['departure_utc']:
            from zoneinfo import ZoneInfo
            local=dt.datetime.fromisoformat(r['departure_utc']).astimezone(ZoneInfo(r['origin_iana']))
            if local.date().isoformat()!=r['departure_date_local'] or local.strftime('%H:%M')!=r['departure_local']:
                clock_errors.append(r['instance_id'])
        for side,code,key in [('origin',r['origin_iata'],a),('destination',r['destination_iata'],b)]:
            trace('J_PUBLISHED_AIRPORT',r['instance_id']+':'+side,key['airport_key_version'],key['key_status'],sid('core',dated_path),sid('core',airport_path),key['missing_reason'])
    check('CORE_DEPARTURE_UTC_LOCAL_REPLAY',not clock_errors,dict(rows=len(dated),failures=clock_errors,
          scope='Departure timestamps only; unknown arrival day left unknown; ZoneInfo validates arithmetic, not law/source truth'))
    write('normalized/published_dated_evidence.csv',dated_norm)
    write('normalized/quarantine_preserved.csv',quarantine)

    # Keys in links are a sparse incidence table, not additive observations.
    by_candidate=defaultdict(set)
    for r in links:
        by_candidate[(r['model_id'],r['candidate_id'])].add(r['entity_code'])
    for f in flights:
        by_candidate[('ciri:conditional16',f['network'])].update([f['origin'],f['destination']])
    for r in reg:
        by_candidate[(r['model_id'],r['candidate_id'])]  # Preserve explicit empty-network coverage too.
    social_path=CP+'integration_v1/social/gateway_region_context_2024.csv'
    cross_path=CP+'integration_v1/social/gateway_region_crosswalk.csv'
    social=load('core',social_path,'gateway IATA × region × indicator × year','publisher native units; ND unit held')
    cross=load('core',cross_path,'gateway IATA','explicit reviewed airport/city/region mapping; not municipal catchment')
    unique('gateway_crosswalk',cross,['airport_iata'])
    unique('gateway_social',social,['airport_iata','canonical_region_id','indicator_code','year'])
    cby={r['airport_iata']:r for r in cross}
    social_idx=defaultdict(list)
    for r in social:
        social_idx[r['airport_iata']].append(r)
    socialjoin=[]
    for (model,cid),codes in sorted(by_candidate.items()):
        if not codes:
            for dataset in ['regional_tourism_2024','historical_station_weather']:
                coverage.append(dict(model_id=model,candidate_id=cid,dataset=dataset,entity_code='',
                                     total_source_rows=0,admitted_rows=0,key_status='NO_PROGRAM_ENDPOINTS',
                                     coverage_status='NO_ENDPOINTS_IN_EXPORTED_NETWORK',geographic_grain='NOT_APPLICABLE',period='',
                                     missing_reason='Author exported zero physical legs for this strategy; no inference about empirical service/market absence'))
        for code in sorted(codes):
            match=social_idx.get(code,[])
            admitted=[r for r in match if r['unit_native'] and not r['unit_missing_reason'] and 'QUARANTINE' not in r['acceptance']]
            coverage.append(dict(model_id=model,candidate_id=cid,dataset='regional_tourism_2024',entity_code=code,
                                 total_source_rows=len(match),admitted_rows=len(admitted),key_status=resolve(code)['key_status'],
                                 coverage_status='MATCHED_REGIONAL_CONTEXT' if match else 'UNKNOWN_NOT_COVERED',
                                 geographic_grain='REGION; not city/catchment',period='2024',
                                 missing_reason='' if match else 'Reviewed gateway-region crosswalk covers seven gateways only'))
            for r in match:
                socialjoin.append(dict(model_id=model,candidate_id=cid,entity_code=code,**r,
                                       bridge_value_class='OBSERVED' if r in admitted else 'UNKNOWN',
                                       numeric_use_admitted=str(r in admitted),context_use='REGIONAL_ANNUAL_CONTEXT_ONLY',
                                       bridge_source_input_id=sid('core',social_path)))
                trace('J_CANDIDATE_TOURISM',model+':'+cid+':'+code,r['canonical_region_id']+':'+r['indicator_code']+':'+r['year'],
                      'MATCHED_CONTEXT_ONLY' if r in admitted else 'HOLD_UNIT_UNKNOWN',
                      'normalized/candidate_airport_link.csv',sid('core',social_path),r['unit_missing_reason'])
            if not match:
                trace('J_CANDIDATE_TOURISM',model+':'+cid+':'+code,'','UNMATCHED',
                      'normalized/candidate_airport_link.csv',sid('core',social_path),'Outside seven reviewed gateway-region mappings; not zero')
    write('normalized/candidate_regional_tourism.csv',socialjoin)
    write('normalized/gateway_region_crosswalk.csv',cross)

    mapping_path=AP+'normalized/join_airport_station_mapping.csv'
    weather_path=AP+'normalized/weather_monthly_2024.csv'
    mapping=load('alternative',mapping_path,'station_id × airport_id','distance km; directory identity id')
    weather=load('alternative',weather_path,'station_id × month','hourly sample counts; degC; m/s')
    unique('weather_station_month',weather,['station_id','month'])
    unique('weather_station_mapping',mapping,['station_id','airport_id'])
    # A source id, not the station/city name, joins both sources' OurAirports IDs.
    amap=defaultdict(list)
    for r in mapping:
        amap['OA:'+r['airport_id']].append(r)
    widx=defaultdict(list)
    for r in weather:widx[r['station_id']].append(r)
    weather_join=[]; weather_entities=[]
    for code in sorted(set(c for codes in by_candidate.values() for c in codes)):
        a=resolve(code)
        maps=amap.get(a['airport_id'],[]) if a['airport_id'] else []
        for m in maps:
            # Require the independent crosswalk's codes/ICAO to agree too.
            accepted=m['iata']==code and (not a.get('directory_icao') or m['icao']==a['directory_icao'])
            for w in widx.get(m['station_id'],[]):
                row=dict(entity_code=code,airport_id=a['airport_id'],airport_key_version=a['airport_key_version'],
                         station_id=m['station_id'],month=w['month'],station_distance_km=m['station_airport_distance_km'],
                         airport_identity_match=accepted,observed_hours=w['observed_hours'],calendar_hours=w['calendar_hours'],
                         temperature_observations=w['temperature_observations'],wind_observations=w['wind_observations'],
                         frost_sample_count=w['temperature_below_minus20_count'],wind_sample_count=w['wind_ge12_ms_count'],
                         temperature_mean_c=w['temperature_mean_c'],value_status='DERIVED',
                         raw_source_id=w['source_id'],raw_path=w['raw_path'],
                         admitted_scope='HISTORICAL_STATION_CONTEXT_ONLY' if accepted else 'HOLD_IDENTITY',
                         source_input_id=sid('alternative',weather_path),mapping_input_id=sid('alternative',mapping_path))
                weather_join.append(row)
                trace('J_AIRPORT_WEATHER',code,m['station_id']+':'+w['month'],'MATCHED_HISTORICAL_CONTEXT' if accepted else 'HOLD_IDENTITY',sid('core',airport_path),sid('alternative',weather_path))
        weather_entities.append(dict(entity_code=code,airport_key_status=a['key_status'],station_count=len(maps),
                                     monthly_rows=sum(len(widx.get(m['station_id'],[])) for m in maps),
                                     use_status='STATION_CONTEXT_ONLY' if maps else 'UNKNOWN',
                                     missing_reason='' if maps else 'No admitted airport-id crosswalk; no fallback by name'))
        if not maps:
            trace('J_AIRPORT_WEATHER',code,'','UNMATCHED_OR_HELD',sid('core',airport_path),sid('alternative',weather_path),
                  a['missing_reason'] or 'No admitted source station/airport-id map')
    unique('joined_weather',weather_join,['entity_code','station_id','month'])
    check('WEATHER_HOURS_NOT_ABOVE_CALENDAR',all(float(r['observed_hours'])<=float(r['calendar_hours']) for r in weather_join),
          dict(joined_rows=len(weather_join),meaning='Archive completeness; threshold counts do not measure downtime/cancellation probability'))
    check('WEATHER_CROSSWALK_IDENTITY',all(r['airport_identity_match'] for r in weather_join),dict(joined_rows=len(weather_join)))
    write('normalized/airport_weather_month.csv',weather_join)
    write('normalized/weather_entity_coverage.csv',weather_entities)
    for (model,cid),codes in sorted(by_candidate.items()):
        for code in sorted(codes):
            m=next(r for r in weather_entities if r['entity_code']==code)
            coverage.append(dict(model_id=model,candidate_id=cid,dataset='historical_station_weather',entity_code=code,
                                 total_source_rows=m['monthly_rows'],admitted_rows=m['monthly_rows'] if m['use_status']=='STATION_CONTEXT_ONLY' else 0,
                                 key_status=m['airport_key_status'],coverage_status=m['use_status'],geographic_grain='STATION_POINT',period='2024',missing_reason=m['missing_reason']))
    # Published macro traffic: preserve period and entity grain, never attach to OD by city text.
    obs_path=CP+'integration_v1/operating/market_observation_v1.csv'
    observations=load('core',obs_path,'observation_id; period part of identity','native airport/carrier aggregate units')
    unique('market_observation',observations,['observation_id'])
    unique('market_observation_version',observations,['observation_version_id'])
    period_groups=defaultdict(list)
    for r in observations:period_groups[(r['entity_id'],r['metric'])].append(r)
    period_pairs=[]
    for (entity,metric),rr in period_groups.items():
        for i,a in enumerate(rr):
            for b in rr[i+1:]:
                overlap=max(a['period_start'],b['period_start'])<=min(a['period_end'],b['period_end'])
                period_pairs.append(dict(entity_id=entity,metric=metric,left_id=a['observation_id'],right_id=b['observation_id'],
                                         left_period=a['period_start']+'/'+a['period_end'],right_period=b['period_start']+'/'+b['period_end'],
                                         overlap=overlap,aggregation='DO_NOT_SUM_OVERLAPPING_PERIODS' if overlap else 'COMPARE_DEFINITIONS_FIRST'))
    write('checks/observation_period_overlap.csv',period_pairs,
          ['entity_id','metric','left_id','right_id','left_period','right_period','overlap','aggregation'])
    check('OBSERVATION_PERIOD_IDENTITIES_PRESERVED',len({r['observation_id'] for r in observations})==24,
          dict(observation_ids=len(observations),overlap_pairs=sum(r['overlap'] for r in period_pairs),
               handling='All source period-specific IDs retained; no pooled aggregate created'))
    write('normalized/observed_market_aggregates.csv',observations)
    flow=[]
    for n,r in enumerate(demand,2):
        flow.append(dict(pair_id=r['a']+'>'+r['b'],origin=r['a'],destination=r['b'],
                         origin_key_status=resolve(r['a'])['key_status'],destination_key_status=resolve(r['b'])['key_status'],
                         modeled_segments_base=r['pax_base'],reported_flow=r['observed'],reported_raw_flow=r['observed_raw_pax'],
                         reported_coverage=r['observed_coverage'],reported_period=r['observed_period'],reported_source=r['observed_source'],
                         value_class='MODEL',observed_field_class='OBSERVED' if r['observed'] else 'UNKNOWN',
                         market_grain='ANNUAL_BIDIRECTIONAL_LINE_SEGMENTS; NOT_FINAL_OD',
                         weekly_OD_conversion='',conversion_missing_reason='Cannot divide by52/2 and rename segment flow as endpoint OD',
                         rail_hours=r['rail_hr'],rail_imputed_96h=r['rail_imputed_96h'],source_input_id=sid('nastya','data/processed/demand_pairs.csv'),source_row=n))
    write('normalized/line_flow_context.csv',flow)
    # Rare corporate evidence is retained as a sparse source, not expanded into city zeros.
    sites=load('alternative',AP+'modules/business/normalized/sibur_sites.csv','source site_id; postal address/map point','sites; source coordinates; no travel volumes')
    tourism_monthly=load('alternative',AP+'modules/tourism/normalized/primary_monthly_increments.csv',
                         'dataset × OKATO area × month','persons; derived YTD difference; NOT endpoint OD')
    unique('tourism_primary_monthly',tourism_monthly,['dataset_id','area_id','period'])
    unique('corporate_sites',sites,['site_id'])
    check('HYPOTHESES_C10_TOX_NOT_REINTRODUCED',
          all('TOX' not in r['proposed_paths'] for r in products if r['candidate_id']=='C10'),
          'Frozen35 C10 uses SVX/UFA/SGC. Historical Tobolsk airport/industrial demand confusion is not reintroduced.')
    write('normalized/corporate_join_hold.csv', [dict(site_id=r['site_id'],region_iso=r['region_iso_curated'],
          locality_label=r['locality_label_curated'],site_coordinates_status=r['coordinate_join_status'],
          airport_id='',status='HOLD_NO_REVIEWED_SITE_AIRPORT_ACCESS_KEY',travel_demand='',
          missing_reason='Company map/address does not identify passenger airport, headcount, travel origin/destination or procurement',
          source_input_id=sid('alternative',AP+'modules/business/normalized/sibur_sites.csv')) for r in sites])
    write('normalized/entity_resolution.csv',sorted(resolutions.values(),key=lambda r:r['entity_code']))
    held=[r for r in resolutions.values() if r['key_status']!='MATCHED_UNIQUE_DIRECTORY']
    check('NO_QUARANTINE_BYPASS',all(not r['airport_id'] and not r['iana_timezone'] for r in held),
          dict(held_entities=[r['entity_code'] for r in held],scope='No use of held directory IDs in new normalized identity joins'))
    join_summary('J_PRODUCT_AIRPORT',sum(1 for r in links if r['model_id']=='hypotheses:register35'),
                 sum(1 for r in links if r['model_id']=='hypotheses:register35'),
                 sum(1 for r in links if r['model_id']=='hypotheses:register35' and r['key_status']=='MATCHED_UNIQUE_DIRECTORY'),
                 sum(1 for r in links if r['model_id']=='hypotheses:register35' and r['key_status']!='MATCHED_UNIQUE_DIRECTORY'),
                 'N:1 unique directory or explicit HOLD; path tokens retained')
    join_summary('J_CANDIDATE_TOURISM',len({(r['model_id'],r['candidate_id'],r['entity_code']) for r in coverage if r['dataset']=='regional_tourism_2024'}),
                 len(socialjoin),len({(r['model_id'],r['candidate_id'],r['entity_code']) for r in socialjoin}),
                 sum(r['coverage_status']=='UNKNOWN_NOT_COVERED' for r in coverage if r['dataset']=='regional_tourism_2024'),
                 'incidence→6 distinct indicators; repeated regional context NOT ADDITIVE',
                 note='Same region can attach to multiple gateways/products; do not sum by itinerary/candidate')
    join_summary('J_AIRPORT_WEATHER',len(weather_entities),len(weather_join),sum(r['station_count']>0 for r in weather_entities),
                 sum(r['station_count']==0 for r in weather_entities),'airport→station→month, explicitly versioned ID',
                 note='No averaging stations or twelve months into cancellation probability')

    # Criteria on/off test reproduces author's exact normalization on the same candidates.
    effect_rows=[]; score_details=[]; score_replay=[]
    for min_dist in [0,500]:
        codes=[r['iata'] for r in ll if min(float(r['dist_msk_km']),float(r['dist_ekb_km']))>=min_dist]
        crit=criteria['criteria']; vals=criteria['values']; z={i:{} for i in codes}
        for c in crit:
            values={i:vals[i][c['key']]['v'] for i in codes}
            if c.get('fill') is not None:values={i:c['fill'] if v is None else v for i,v in values.items()}
            finite=[v for v in values.values() if v is not None]
            lo=c['lo'] if c.get('lo') is not None else (min(finite) if finite else None)
            hi=c['hi'] if c.get('hi') is not None else (max(finite) if finite else None)
            for i,v in values.items():
                v=None if v is None else ((v-lo)/(hi-lo) if hi>lo else 0.0)
                if v is not None and c['dir']=='-':v=1-v
                z[i][c['key']]=0.5 if v is None else v
        weights={c['key']:float(c['weight']) for c in crit}
        def scores(w):return {i:sum(z[i][k]*v for k,v in w.items())/(sum(w.values()) or 1) for i in codes}
        baseline=scores(weights); order=lambda s:sorted(codes,key=lambda i:-s[i]); before=order(baseline)
        source_scores_path='data/processed/longlist_scores'+('_min500' if min_dist else '')+'.csv'
        source_scores=load('nastya',source_scores_path,'IATA after distance filter','weighted screening score; not financial return')
        score_idx={r['iata']:r for r in source_scores}
        deltas=[abs(baseline[i]-float(score_idx[i]['score'])) for i in codes]
        score_replay.append(dict(min_dist=min_dist,rows=len(codes),max_rounding_delta=max(deltas),pass_rounding=max(deltas)<=0.00050001))
        for key in ['bad_weather_days','wage_2024','rostec_link','transfer_demand_base','last365_days','pax_2025']:
            w=dict(weights);w[key]=0;after=scores(w);ranked=order(after)
            effect_rows.append(dict(model_id='nastya:screening',test_id='REMOVE:'+key+':'+str(min_dist),feature=key,
                                    min_dist_bases_km=min_dist,test_type='ON_OFF_FIXED_INPUT_WEIGHT_RENORMALIZED',source_weight=weights[key],
                                    baseline_top3=';'.join(before[:3]),without_top3=';'.join(ranked[:3]),
                                    top3_changed=set(before[:3])!=set(ranked[:3]),max_abs_score_delta=max(abs(after[i]-baseline[i]) for i in codes),
                                    predictive_test='NOT_RUN_NO_LABELS',acceptance='DIAGNOSTIC_SENSITIVITY; NO_WEIGHT_APPROVAL'))
            for i in codes:
                score_details.append(dict(feature=key,min_dist=min_dist,iata=i,baseline_score=baseline[i],without_score=after[i],
                                          delta=after[i]-baseline[i],baseline_rank=before.index(i)+1,without_rank=ranked.index(i)+1))
    check('NASTYA_SCREENING_FORMULA_REPLAY',all(r['pass_rounding'] for r in score_replay),score_replay,
          'Formula replay on frozen criterion JSON; not full upstream AUTHOR_REPLAY_MATCHED')
    write('checks/screening_score_replay.csv',score_replay)
    write('feature_effects.csv',effect_rows)
    write('checks/feature_score_deltas.csv',score_details)
    # A parameter registry gives each numeric screening input an explicit value class.
    units_by_feature={'gap_pop':'persons at reachable destinations (proxy, not OD)',
        'pax_2025':'reported airport passenger throughput/year','last365_days':'days with classified posts in rolling365 (not downtime)',
        'catchment_pop_2025':'modeled residents in75km; census×regional update', 'dist_bases_km':'great_circle_km',
        'transfer_demand_base':'modeled bidirectional line segments/year summed over eligible pairs',
        'wage_2024':'RUB/nominal employee/month; partial coverage', 'bad_weather_days':'exploratory threshold sample-day-equivalent/year',
        'rostec_link':'author affiliation flag','competitor_hub':'author ordinal competitor proxy',
        'strategy_region':'author policy preference flag','transfer_zone':'author readiness ordinal',
        'ssj_mro':'author readiness ordinal','h24':'published availability flag','ssj_ops':'observed published SSJ route evidence flag',
        'rw_support':'published support airport flag','demand_gap':'modeled annual bidirectional route segments','pax_2019':'airport passenger throughput/year'}
    parameter=[]
    for code,vv in criteria['values'].items():
        for c in criteria['criteria']:
            key=c['key'];v=vv[key]['v']
            vclass='UNKNOWN' if v is None else ('MODEL' if key in ['transfer_demand_base','demand_gap','catchment_pop_2025'] else 'DERIVED')
            if v is not None and key in ['pax_2025','pax_2019','wage_2024']:vclass='OBSERVED' if key.startswith('pax_') else 'DERIVED'
            parameter.append(dict(**meta('nastya:screening',candidate=code,scope='AUTHOR_CRITERION_VALUE_ONLY',market='SCREENING_PROXY',status=vclass),
                                  parameter_id=key,value=v,unit=units_by_feature.get(key,'author criterion scale'),default_weight=c['weight'],
                                  missing_reason='Source criterion JSON value is NULL' if v is None else '',
                                  source_explanation=vv[key]['s'],source_input_id=sid('nastya',criteria_path),
                                  decision_status='AUTHOR_PROPOSAL',computed_fill=c.get('fill'),
                                  leakage_limit='Source availability precedes hypothetical forecast only after explicit vintage check; no predictive test'))
    for r in markets:
        for scen in ['base','cautious']:
            for field,unit in [('demand','endpoint journeys/week/direction'),('net_fare','RUB/net whole one-way journey')]:
                parameter.append(dict(**meta('ciri:conditional16',scen,scope='AUTHOR_COMMON_BAND_SCENARIO',market=unit,
                                             start='2026-12-07',end='2026-12-13'),parameter_id=r['pair']+':'+field,
                                      value=r[field+'_'+scen],unit=unit,source_input_id=sid('ciri',C16+'markets.csv'),
                                      decision_status='AUTHOR_PROPOSAL',source_explanation=r['method']))
    write('normalized/parameter_registry.csv',parameter)
    # Usage is about computational dependency, not about existence of an archive.
    usage=[]
    def usage_row(model,dataset,state,purpose,evidence,new_effect,grain,period,missing=''):
        role=model.split(':')[0]
        usage.append(dict(model_id=model,author_ref=AUTHORS[role],source_commit=PINS[role],dataset=dataset,
                          usage_status=state,purpose=purpose,dependency_evidence=evidence,new_join_can_change=new_effect,
                          geographic_grain=grain,period=period,missingness=missing,
                          caution='Usage does not grant source truth or observed demand acceptance'))
    for model in ['nastya:screening','nastya:network','ciri:conditional16','hypotheses:register35','hypotheses:experiment3','ciri_stage1:screening']:
        role=model.split(':')[0]
        for dataset,grain,period in [('airport_identity_timezone','airport version / IANA at date','directory2026; target dates2026'),
                                    ('published_schedule','published rule / dated origin departure','winter2026; explicit dates or UNKNOWN year'),
                                    ('observed_flow','airport/carrier aggregate or bidirectional route segments','2019/2025 or explicit report period'),
                                    ('scenario_final_OD','directed endpoint OD/week','2026-12-07/13 scenario'),
                                    ('social_demography_wage','municipality/catchment or region; distinct','census2021; pop2025; wage2024'),
                                    ('tourism_regional','regional annual indicator','2024; publication2025/2026'),
                                    ('corporate_sites','site/address/map point','snapshot2026-11-09'),
                                    ('weather_existing_screening','airport station archive sample metric','2023/2024'),
                                    ('weather_new_join','station×month; OA id mapping','2024 archive joined to2026 identity')]:
            state='COLLECTED_NOT_USED';purpose='Context/integration inventory';evidence='Frozen output/entrypoint inspected; this source is not an input to the adapted computation'
            effect='No numerical model effect until explicit new input_set and feature/admission choice'
            if dataset=='airport_identity_timezone':
                state='USED' if model in ['ciri:conditional16','hypotheses:experiment3'] else 'USED_IDENTITY_OR_GEOGRAPHY_ONLY'
                purpose='Entity matching/geography; explicit clock conversion only in dated programs'
                evidence='Normalized candidate_airport_link/physical_leg and pinned source entrypoint; bridge uses OA IDs with HOLD'
                effect='New canonical identities/timezones affect join admissibility; no implicit demand change'
            if dataset=='published_schedule':
                state='USED_CONTEXT_OR_CALENDAR' if model in ['ciri:conditional16','hypotheses:experiment3'] else ('USED_CONNECTIVITY_PROXY' if model.startswith('nastya:') else 'REFERENCE_ONLY')
                purpose='Calendar/own-sales constraint or direct-service flag, according to model'
                evidence='Ciri setup/goj_svx_own_calendar + Model; hypotheses evaluate/core_operating_join; Nastya Demand.links/direct flag'
                effect='Can alter calendar gates/incumbent overlap; observed flight or sale remains UNKNOWN'
            if dataset=='observed_flow' and model.startswith('nastya:'):
                state='USED';purpose='pax_2025 screening or reported/calibration segment flow';evidence='criteria.json; Demand.__init__; demand_model.main known_flows'
                effect='Changes screening/modelled segment input; cannot automatically replace endpoint OD'
            if dataset=='scenario_final_OD' and model=='ciri:conditional16':
                state='USED';purpose='Shared directional market cap and money scenarios';evidence='markets.csv; scripts/build_conditional_decision.py setup/band_values/evaluation'
                effect='A compatible new OD observation could replace common bands via a separate input_set; none supplied'
            if dataset=='social_demography_wage' and model.startswith('nastya:'):
                state='USED';purpose='catchment population/gravity demand; wage screening criterion only'
                evidence='demand_model.FEATS lnPP; criteria.json wage_2024 weight5; network does not price wages'
                effect='Weight sensitivity measured; regional context is not catchment replacement'
            if dataset=='weather_existing_screening' and model=='nastya:screening':
                state='USED';purpose='bad_weather_days criterion with author weight5';evidence='criteria.json; longlist_score.normalize/run'
                effect='On/off recomputed at0/500km; no predictive label/dispatch link'
            if model=='ciri_stage1:screening':
                evidence='context/22_stage1_audit/model_rules.json; score scenario snapshot; upstream values not fully rerun here'
                state='OUTPUT_ADAPTED_ONLY';purpose='Distinct screening methodology/output; dependency acceptance belongs to author audit'
            usage_row(model,dataset,state,purpose,evidence,effect,grain,period)
    write('model_input_usage.csv',usage)
    feature_fitness=[]
    for key,purpose,admit,overlap,effect in [
        ('airport_identity_timezone','Join flight endpoints; convert explicit local dates','DIRECTORY_MATCH_ONLY; quarantine retained','IATA must be unique; MOW is group','CLOCK_AND_ID_JOIN_CHECKED'),
        ('published_schedule','Test dated departure/return feasibility','PUBLISHED_RULE_OR_DERIVED_CALENDAR; not execution','Rules may overlap; keep rule/instance IDs and raw cell locators','24 departure timestamps checked; arrival-day unknown preserved'),
        ('observed_flow','Market scale/context or segment-model calibration','REPORTED_CARRIER/AIRPORT/LINE_GRAIN_ONLY','period overlaps; airport throughput contains arrivals/departures; segment includes connections','Cannot replace final_OD with line flow by /52/2'),
        ('wage_2024','Affordability/context in screening','PARTIAL_CATCHMENT_PROXY_ONLY','Population coverage; excludes small firms; region/municipality/catchment differ','FEATURE_ON_OFF_RUN; NOT_RUN_NO_LABELS'),
        ('tourism_regional','Destination accommodation vs local travel agencies','28/42 native-unit-known source rows as regional2024 context;14 held','No adding firms, packages, persons or repeated regions across products','NOT_RUN_NO_LABELS; weight/inclusion not approved'),
        ('corporate_sites','Identify a concrete site/access/product research question','SPARSE_CORPORATE_EVIDENCE; NO_DEMAND_NUMBER','Group membership/site address not headcount/travel/procurement; unobserved cities not zero','NOT_RUN_NO_LABELS; no airport access key'),
        ('bad_weather_days','Screening sensitivity and specific operating threshold research','AUTHOR_SCREENING_PROXY; threshold not aircraft dispatch constraint','Wind/frost counts may overlap; never sum as lost days','FEATURE_ON_OFF_RUN; NOT_RUN_NO_LABELS'),
        ('weather_new_join','Station archive coverage/context for operating conditions','HISTORICAL_STATION_CONTEXT_ONLY','Station/month samples; do not treat missing archive as clear weather or low risk','NOT_RUN_NO_LABELS; joined data not read by author model'),
        ('transfer_demand_base','Screening of modeled reachable pairs','MODEL_SEGMENT_PROXY_ONLY','Overlapping reachable markets/candidate programs share passengers; cannot sum as final demand','FEATURE_ON_OFF_RUN; NOT_RUN_NO_LABELS'),
        ('rostec_link','Author affiliation preference/context','AUTHOR_CRITERION_ONLY; NOT_SALES','Overlap with industrial/corporate anecdotes; no fleet-support inference','FEATURE_ON_OFF_RUN; NOT_RUN_NO_LABELS')]:
        feature_fitness.append(dict(feature=key,purpose=purpose,evidence='source_manifest.csv; model_input_usage.csv; frozen input SHA',
                                     admitted_scope=admit,missingness='coverage.csv / parameter_registry; NULL stays unknown',
                                     overlap_doublecount=overlap,effect_test=effect,predictive_gain='UNKNOWN',
                                     leakage='Historical source vintage is required before forecast/holdout; post-outcome publication may leak',
                                     acceptance='AGENT_PROPOSAL_FOR_ADMISSION; no team approval inferred'))
    write('feature_fitness.csv',feature_fitness)
    compatibility=[
        dict(left_model='nastya:screening',right_model='ciri_stage1:screening',dimension='city score',status='CONDITIONAL',reason='Same candidate codes can align. Different weights/normalization/UNKNOWN policy and scopes; do not average scores.'),
        dict(left_model='nastya:network',right_model='ciri:conditional16',dimension='passengers',status='INCOMPATIBLE_NUMERIC_COMPARISON',reason='Annual modeled bidirectional line-segment-derived inputs vs directed weekly final-OD scenarios; MOW group vs ZIA airport.'),
        dict(left_model='nastya:network',right_model='ciri:conditional16',dimension='money',status='INCOMPATIBLE_NUMERIC_COMPARISON',reason='Rounded millionRUB/year vs RUB/week; net/price/tax basis not reconciled; fixed/launch/opportunity budget unknown.'),
        dict(left_model='hypotheses:register35',right_model='ciri:conditional16',dimension='programs',status='STRUCTURAL_ONLY',reason='Research products and route portfolios can share physical endpoints. Register35 has UNKNOWN OD/fare/resource; cannot rank financially.'),
        dict(left_model='hypotheses:experiment3',right_model='ciri:conditional16',dimension='capacity',status='STRUCTURAL_ONLY',reason='Dated nominal scenario legs can be mapped to common fields. Different scenario legsets/periods/resources; not same upper resource bound.'),
        dict(left_model='core:observed_market',right_model='ciri:conditional16',dimension='OD',status='INCOMPATIBLE_GRAIN',reason='Reported carrier/airport aggregates do not identify directed final OD. No new common empirical demand input generated.')]
    write('compatibility.csv',compatibility)
    write('coverage.csv',coverage)
    write('join_manifest.csv',joins)
    write('join_lineage.csv',join_rows)

    # Field dictionary covers every normalized field, and keeps unknown money/calendar fields explicit.
    for path,info in list(tables.items()):
        if not path.startswith('normalized/'):continue
        for col in info['fields']:
            if col in ['model_id','author_ref','source_commit','input_set_id','run_id','scenario_id','candidate_id','source_input_id','source_row'] or any(t in col for t in ['status','reason','scope','source','acceptance','method','rule','basis','author','input','bridge','qualifier','missing']):
                klass='DERIVED';unit='identifier/text';reason='Metadata; not an observed business quantity'
            elif any(t in col for t in ['full_budget','aircraft_available','actual_available','observed_journeys','weekly_OD_conversion','flight_date']):
                klass='UNKNOWN';unit='see table unit';reason='Source does not establish value; blank is NULL, never zero'
            elif path.endswith(('observed_market_aggregates.csv','gateway_region_crosswalk.csv','published_dated_evidence.csv','candidate_regional_tourism.csv','airport_weather_month.csv')):
                klass='MIXED_EXPLICIT_ROW_STATUS';unit='native unit column; clocks local/UTC explicitly';reason='Use value_status/bridge_value_class/admitted_scope per row; derived calendar/weather not execution'
            elif path.endswith(('itinerary.csv','physical_leg.csv','capacity_allocation.csv','money_ledger.csv','resource_ledger.csv','market_pool.csv','hypothesis_thresholds.csv','itinerary_leg.csv')):
                klass='SCENARIO';unit='table market_unit; seats, journeys, minutes, RUB explicitly named';reason='Conditional author scenario, not observed demand/sales/fleet'
            elif path.endswith(('route_program.csv','evaluation_summary.csv','line_flow_context.csv')):
                klass='MODEL_OR_SCENARIO_ROW_STATUS';unit='market_unit/native field name';reason='Preserve model_id, horizon and row source; model and scenario inputs differ'
            else:
                klass='DERIVED';unit='identifier/text unless native unit named';reason='Adapter mapping/context; not passenger demand'
            fields[(path,col)]=dict(table=path,field=col,value_class=klass,unit=unit,null_rule='Empty CSV cell is NULL; use reason/status; do not fill0',interpretation=reason)
    # Rule-based mixed columns remain explicitly row-classified, with canonical classes.
    for r in fields.values():
        if r['value_class']=='MIXED_EXPLICIT_ROW_STATUS':
            r['value_class']='DERIVED'
            r['value_class_rule']='For numeric value/metric columns use row.value_status or bridge_value_class; if unit_missing_reason or HOLD then UNKNOWN. Other identity fields DERIVED.'
        elif r['value_class']=='MODEL_OR_SCENARIO_ROW_STATUS':
            r['value_class']='MODEL'
            r['value_class_rule']='For numeric outputs use row.value_status (MODEL Nastya; SCENARIO Ciri); source blank/unknown then UNKNOWN. copied reported_flow uses observed_field_class.'
        else:
            r['value_class_rule']='Blank business value is UNKNOWN; other cells use this class. Status/source/identifier fields are DERIVED metadata.'
    write('field_dictionary.csv',fields.values())
    write('source_manifest.csv',[{k:v for k,v in r.items() if k!='data'} for r in inputs.values()])
    dump('input_manifest.json',dict(contract_sha256=digest((OUT.parent/'contract.md').read_bytes()),
         parent_input_manifest_sha256=digest((OUT.parent/'input_manifest.json').read_bytes()),pins=PINS,
         source_inputs=[{k:v for k,v in r.items() if k!='data'} for r in inputs.values()],
         ingestion='Pinned Git blobs read only. No mutable worktree tables or new network downloads.',
         source_author_note='Git file author, package author and primary publisher are distinct. See source_manifest and provenance notes.'))
    dump('verification.json',dict(checks=checks,failed=sum(r['status']=='FAIL' for r in checks),
         passed=sum(r['status']=='PASS' for r in checks),acceptance_scope=['PINNED_OUTPUT_HASHED','JOIN_CHECKED_WITH_EXPLICIT_HOLDS','SCENARIO_ACCOUNTING_CHECKED'],
         outside_scope=['Full author model rerun','SOURCE_SUPPORTED for all original claims','Observed final OD','Actual ticket sales',
                        'Actual available aircraft','Full financial budget','Operational schedule clearance','Predictive gain','Independent review'],
         table_counts={k:v['rows'] for k,v in tables.items()}))
    print(json.dumps(dict(tables=len(tables),checks=len(checks),failed=sum(r['status']=='FAIL' for r in checks),
                          rows={k:v['rows'] for k,v in tables.items() if k.startswith('normalized/')},held_codes=[r['entity_code'] for r in held]),ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
