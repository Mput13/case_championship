#!/usr/bin/env python3
"""Independent bounded review. Reads exact Git blobs and hash-locked owner raw only.

No upstream code is executed or imported; writes are restricted to this directory.
Run from repository root with the existing Python 3 environment (lxml available).
"""
import calendar
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import math
import re
import subprocess
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from lxml import html

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
PREFIX = 'context/23_night_run_20261110/'
PRIMARY = '17b4f348f15ea8695688d9435933cb4965568408'
BRIDGE = 'abc09bbb8e62d3513749b60b252d4521997acfc3'
BASELINE = '7180bf5e03905a7892b3031f2447c5b33d10e244'
OWNER = Path('/Users/a/.t3/worktrees/case_championship/t3-24183fe2-932bcc337b6511df') / PREFIX / 'primary_evidence'
inputs, raw_inputs, checks = {}, {}, []


def digest(b):
    return hashlib.sha256(b).hexdigest()


def blob(sha, path, grain='source/code/receipt; field-level meaning in report'):
    b = subprocess.check_output(['git', 'show', sha + ':' + path], cwd=ROOT)
    if (sha,path) not in inputs:
        meta=subprocess.check_output(['git','log','-1','--format=%H%x09%an%x09%aI',sha,'--',path],cwd=ROOT,text=True).strip().split('\t')
        refs={PRIMARY:'Михаил / Mput13; primary-evidence Sol role',BRIDGE:'Михаил / Mput13; data-bridge Sol role',BASELINE:'Михаил / Mput13; data-bridge Sol role',
              '93fa5cf4a10ab67e05c93d19fc5375fc58ef9299':'Цири / mput',
              '2f03b693a62c219e9475fcd1e26295039f6a49d7':'Анастасия / kiruha355',
              'ef365ac2a936117e5b3bb12ea99c816d7b1a101c':'Михаил / Mput13; alternative Sol role',
              '505e24663e5952bae9b9540bb9a5a622663bfc2a':'Михаил / Mput13; core Sol role'}
        inputs[(sha, path)] = dict(commit=sha, path=path, sha256=digest(b), bytes=len(b), grain=grain,
                                   artifact_author_ref=refs.get(sha,'See pinned input manifest; not inferred from Git author'),
                                   last_file_commit=meta[0],last_file_git_author=meta[1],last_file_author_date=meta[2],
                                   publisher='NOT_APPLICABLE_TO_GIT_ADAPTER; raw publishers listed separately')
    return b


def table(sha, path):
    return list(csv.DictReader(io.StringIO(blob(sha, path).decode('utf-8-sig'))))


def obj(sha, path):
    return json.loads(blob(sha, path))


def ptable(name):
    return table(PRIMARY, PREFIX + 'primary_evidence/' + name)


def btable(name):
    return table(BRIDGE, PREFIX + 'data_bridge/' + name)


def check(name, ok, detail):
    checks.append(dict(check=name, status='PASS' if ok else 'FAIL', detail=detail))


def close(a, b):
    return math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-6)


def raw(path, expected, publisher, grain, url=''):
    b = Path(path).read_bytes()
    actual = digest(b)
    raw_inputs[str(path)] = dict(path=str(path), sha256=actual, expected_sha256=expected,
                                 bytes=len(b), publisher=publisher or None, publisher_missing_reason='' if publisher else 'Not specified in pinned raw receipt', grain=grain, source_url=url,
                                 status='PASS' if actual == expected else 'FAIL')
    if actual != expected:
        raise ValueError('Raw hash mismatch: ' + str(path))
    return b


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def write(name, rows):
    if not rows:
        return
    with (OUT / name).open('w', newline='') as f:
        w = csv.DictWriter(f, list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader()
        w.writerows(rows)


def primary():
    receipts = obj(PRIMARY, PREFIX + 'primary_evidence/http_receipts.json')
    registry = {r['source_id']: r for r in ptable('source_registry.csv')}
    docs = {}

    def doc(sid):
        if sid not in docs:
            r = next(r for r in receipts if r['source_id'] == sid)
            b = raw(OWNER / r['raw_local_path'], r['sha256'], registry[sid]['publisher'],
                    registry[sid]['grain'], r['url'])
            docs[sid] = html.fromstring(b.decode('utf-8'))
        return docs[sid]

    # Independent whole-rule reconstruction, then a set difference on all dated cells.
    fields = ['source_id', 'source_card', 'origin', 'destination', 'source_direction', 'carrier',
              'flight', 'departure_local', 'arrival_local', 'displayed_duration', 'aircraft',
              'active_days', 'period_start', 'period_end', 'period_kind']
    parsed, dated = [], []
    weekdays = {'Пн': 0, 'Вт': 1, 'Ср': 2, 'Чт': 3, 'Пт': 4, 'Сб': 5, 'Вс': 6}
    week = [dt.date(2026, 12, d) for d in range(7, 14)]
    for code, stems in [('OMS', ('ufa_oms', 'ufa_oms_to')), ('NJC', ('ufa_njc', 'ufa_njc_to')),
                        ('MRV', ('ufa_mrv', 'ufa_mrv_to')), ('KUF', ('ufa_kuf', 'ufa_kuf_to')),
                        ('GOJ', ('ufa_goj_fixed', 'ufa_goj_to'))]:
        for sid in stems:
            tree = doc(sid)
            direction = tree.xpath('//input[@name="DIRECTION"]/@value')[0]
            check('RAW_DIRECTION:' + sid, direction == ('TO' if sid.endswith('_to') else 'FROM'), direction)
            origin, destination = (code, 'UFA') if direction == 'FROM' else ('UFA', code)
            cards = tree.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," b-card-sez-card ") and not(contains(@class,"--caption"))]')
            for no, card in enumerate(cards, 1):
                cells = {}
                for cell in card.xpath('.//div[@class]'):
                    tokens = cell.attrib['class'].split()
                    for token in tokens:
                        if token.startswith('b-card-sez-card__td_'):
                            key = token.split('__td_', 1)[1]
                            values = [' '.join(e.itertext()).strip() for e in cell.xpath('.//span[contains(@class,"__info")]')]
                            cells[key] = [' '.join(v.split()) for v in values]
                get = lambda k: (cells.get(k) or [''])[0]
                dates = [dt.datetime.strptime(s, '%d.%m.%Y').date() for s in cells['period']]
                days = [''.join(e.itertext()).strip() for e in card.xpath('.//span[@class]')
                        if '_active' in e.attrib['class'].split()]
                r = dict(source_id=sid, source_card=str(no), origin=origin, destination=destination,
                         source_direction=direction, carrier=get('company'), flight=get('number'),
                         departure_local=get('time--start'), arrival_local=get('time--end'),
                         displayed_duration=get('duration'), aircraft=get('flight'), active_days=';'.join(days),
                         period_start=dates[0].isoformat(), period_end=dates[-1].isoformat(),
                         period_kind='SINGLE_DATE' if len(dates) == 1 else 'INCLUSIVE_RANGE')
                parsed.append(r)
                allowed = {weekdays[d] for d in days}
                for date in week:
                    if dates[0] <= date <= dates[-1] and (dates[0] == dates[-1] or date.weekday() in allowed):
                        dated.append(dict(r, date=date.isoformat()))
    key = lambda r, cols: tuple(r[c] for c in cols)
    check('UFA_ALL_RAW_RULE_CELLS', Counter(key(r, fields) for r in parsed) == Counter(key(r, fields) for r in ptable('ufa_schedule_rules.csv')), dict(recomputed=len(parsed)))
    datefields = fields + ['date']
    expected = ptable('ufa_dated_services.csv')
    check('UFA_ALL_20_DATED_ROWS', Counter(key(r, datefields) for r in dated) == Counter(key(r, datefields) for r in expected), dict(recomputed=len(dated), pinned=len(expected)))
    write('ufa_calendar_recomputed.csv', dated)
    offsets = dict(UFA=5, OMS=6, NJC=5, MRV=3, KUF=4, GOJ=3)
    minutes = lambda s: int(s.split(':')[0]) * 60 + int(s.split(':')[1])
    conflicts = [r for r in parsed if (minutes(r['arrival_local']) - minutes(r['departure_local']) + 60*(offsets[r['origin']] - offsets[r['destination']])) % 1440 != minutes(r['displayed_duration'])]
    check('UFA_8_CONFLICTS_EXCLUDED', len(conflicts) == 8 and all(not r['period_start'] <= day.isoformat() <= r['period_end'] for r in conflicts for day in week), dict(count=len(conflicts)))

    # Source facts: bounded locator evidence only. Full source text is never copied to outputs.
    fact_checks = {
        'kuf_mro_favt': ['30 апреля', '4Y-Check', 'как ожидается', 'Россия'],
        'svx_results_2025': ['800 тыс.', '15%', '2,5 раза', '16%', '11%'],
        'ren_pax_recheck': ['951', '885,5', '65,6'],
        'oms_mro_recheck': ['В настоящее время', 'Red Wings', '2025'],
        'nordstar_rw_2024': ['2024', 'Волгоград', 'NordStar', 'Саратов', 'Red Wings'],
    }
    facts = []
    for sid, literals in fact_checks.items():
        tree = doc(sid)
        text = ' '.join(tree.text_content().split())
        ok = all(lit in text for lit in literals)
        facts.append(dict(source_id=sid, expected_bounded_literals=literals, all_present=ok,
                          source_text_sha256=digest(text.encode()), stage='RAW_READ_AND_SCOPED_INTERPRETATION; see report'))
        check('PRIMARY_LITERAL_LOCATORS:' + sid, ok, dict(literals=literals))
    save('primary_fact_locators.json', facts)

    # Independently derive short-date KUF calendars; year remains an assumption.
    months = dict(янв=1, фев=2, мар=3, апр=4, май=5, мая=5, июн=6, июл=7, авг=8, сен=9, окт=10, ноя=11, дек=12)
    endpoint_samples = []
    for sid, arrival in [('kuf_schedule_new', False), ('kuf_schedule_arr_new', True)]:
        for no, tr in enumerate(doc(sid).xpath('//tr'), 1):
            vals = [' '.join(e.text_content().split()) for e in tr.xpath('./td|./th')]
            if len(vals) != 8 or vals[-1] not in ('MRV', 'NJC'):
                continue
            dep, arr, days, period, carrier, flight, aircraft, other = vals
            boundaries = [(int(a), months[b[:3]]) for a, b in re.findall(r'(\d+)\s+([а-я]+)', period.lower())]
            first, last = boundaries
            start = dt.date(2026 if first[1] >= 10 else 2027, first[1], first[0])
            end = dt.date(start.year + (last[1] < first[1]), last[1], last[0])
            active = set(range(7)) if 'ежеднев' in days else {weekdays[d.strip().capitalize()] for d in days.split(',')}
            dates = [d.isoformat() for d in week if start <= d <= end and d.weekday() in active]
            endpoint_samples.append(dict(source_id=sid, raw_tr=no, origin=other if arrival else 'KUF',
                                         destination='KUF' if arrival else other, flight=flight, carrier=carrier,
                                         dates=';'.join(dates), count=len(dates), period_raw=period,
                                         year_status='ASSUMED_2026_27_NOT_SOURCE_EXPLICIT'))
    write('kuf_endpoint_calendar.csv', endpoint_samples)
    evidence = ptable('dated_evidence.csv')
    exp = Counter((r['source_id'],r['origin'],r['destination'],r['flight'],d) for r in endpoint_samples for d in r['dates'].split(';') if d)
    got = Counter((r['source_id'],r['origin'],r['destination'],r['flight'],r['date']) for r in evidence if r['source_id'].startswith('kuf_schedule') and {r['origin'],r['destination']} & {'MRV','NJC'})
    check('KUF_MRV_NJC_RAW_CONDITIONAL_DATES', exp == got, dict(rows=sum(exp.values()), directional_counts=dict(Counter(r['origin']+'>'+r['destination'] for r in evidence if r['source_id'].startswith('kuf_schedule') and {r['origin'],r['destination']} & {'MRV','NJC'}))))

    aliases = {'РедВингс': 'WZ', 'ЮТэйр': 'UT', 'Азимут': 'A4', 'Уральские а/л': 'U6'}
    groups = defaultdict(list)
    for line, r in enumerate(evidence, 2):
        f = re.sub(r'[^A-Z0-9]', '', r['flight'].upper())
        if f.isdecimal():
            f = aliases.get(r['carrier'], 'UNKNOWN') + '-' + f
        else:
            f = f[:2] + '-' + f[2:]
        groups[(r['origin'], r['destination'], r['date'], f)].append((line, r))
    holds = {k for k, rr in groups.items() if len({(r['departure_local'],r['arrival_local']) for _,r in rr}) > 1}
    idrows = ptable('service_identity.csv')
    holdrows = ptable('schedule_conflicts.csv')
    kcols = ['origin','destination','date','normalized_flight']
    check('PUBLICATION_KEYS_AND_CLOCK_HOLDS', len(evidence) == 209 and len(groups) == 173 and len(holds) == 12 and set(groups) == {key(r,kcols) for r in idrows} and holds == {key(r,kcols) for r in holdrows}, dict(publication_rows=len(evidence), service_keys=len(groups), clock_holds=len(holds)))
    cards = ptable('route_product_cards.csv')
    check('CARD_UNKNOWNS_NO_NOMINAL_SEATS_OR_FARE', len(cards)==112 and sum(r['value_status']=='UNKNOWN' for r in cards)==56 and all(not r['seats_per_departure'] and not r['comparable_fare_rub'] for r in cards) and all(not r['one_way_departures'] for r in cards if r['value_status']=='UNKNOWN'), dict(cards=len(cards), unknown=sum(r['value_status']=='UNKNOWN' for r in cards)))
    scope = obj(PRIMARY, PREFIX+'primary_evidence/candidate_scope.json')
    check('H_UFA4_PROPOSAL_VARIANT', set(scope['leaves']['H_UFA_4']) == {'GSV','MRV','NJC','OMS'}, scope['leaves'])
    old_variant=obj('93fa5cf4a10ab67e05c93d19fc5375fc58ef9299','context/16_conditional_decision/model/selected_networks.json')['H_UFA_4']['leaves']
    check('CONDITIONAL16_CONTEXT21_VARIANTS_DISTINCT',set(old_variant)=={'GOJ','GSV','NJC','OMS'} and set(old_variant)!=set(scope['leaves']['H_UFA_4']),dict(conditional16=old_variant,context21=scope['leaves']['H_UFA_4']))
    # Denominators directly from source proposals; no use of author's coverage_summary.
    src = table('93fa5cf4a10ab67e05c93d19fc5375fc58ef9299', 'context/21_team_proposals/routes.csv')
    denominators = []
    for network in ['D_SVX8','H_UFA_8','H_UFA_4']:
        pairs = {tuple(r['pair'].split('-')) for r in src if r['network']==network}
        rays = {p for a,b in pairs for p in [(a,b),(b,a)]}
        leaves = {c for a,b in pairs for c in (a,b) if c!='UFA'}
        markets = [('DIRECT_PROGRAM' if network=='D_SVX8' else 'HUB_RAY', rays)]
        if network != 'D_SVX8':
            markets.append(('ENDPOINT_OD_VIA_UFA', {(a,b) for a in leaves for b in leaves if a!=b}))
        for role, markets in markets:
            positive = len({(r['origin'],r['destination']) for r in evidence} & markets)
            denominators.append(dict(candidate_id=network,market_role=role,directed_markets=len(markets),positive=positive,unknown=len(markets)-positive))
    write('coverage_recomputed.csv', denominators)
    summary = ptable('coverage_summary.csv')
    check('COVERAGE_DENOMINATORS', all(any(r['candidate_id']==s['candidate_id'] and r['market_role']==s['market_role'] and r['directed_markets']==int(s['directed_markets']) and r['positive']==int(s['positive_dated_markets']) for r in denominators) for s in summary), denominators)

    # A source_id alone must not point to a different captured body than its rows.
    mismatches=[]
    for line,r in enumerate(evidence,2):
        registered=registry[r['source_id']]
        if registered['raw_sha256']!=r['html_sha256']:
            mismatches.append(dict(dated_evidence_line=line,source_id=r['source_id'],origin=r['origin'],destination=r['destination'],date=r['date'],flight=r['flight'],
                                   registry_raw_sha256=registered['raw_sha256'],row_raw_sha256=r['html_sha256'],registry_capture=registered['captured_at_utc']))
    write('source_registry_mismatches.csv',mismatches)
    stage17=obj('93fa5cf4a10ab67e05c93d19fc5375fc58ef9299','context/17_aircraft_route_review/evidence/sources.json')
    newer={r['id']:r for r in stage17}
    resolution=[dict(source_id=sid,pinned_stage17_hash=newer[sid]['sha256'],pinned_stage17_capture=newer[sid]['accessed'],
                     rows_affected=sum(r['source_id']==sid for r in mismatches),all_row_hashes_match_stage17=all(r['row_raw_sha256']==newer[sid]['sha256'] for r in mismatches if r['source_id']==sid)) for sid in sorted({r['source_id'] for r in mismatches})]
    save('source_registry_resolution.json',resolution)
    check('SOURCE_REGISTRY_ROW_RAW_VERSION_FK',not mismatches,dict(affected_rows=len(mismatches),affected_sources=resolution,scope='P2 lineage defect; no numerical calendar change established'))


def bridge():
    names = ['itinerary','itinerary_leg','physical_leg','market_pool','money_ledger','capacity_allocation','evaluation_summary','entity_resolution','candidate_register','candidate_airport_link','airport_weather_month','candidate_regional_tourism']
    t = {n: btable('normalized/'+n+'.csv') for n in names}
    it, legs, phys, pools, money, alloc = [t[n] for n in names[:6]]
    pidx = {r['physical_leg_id']:r for r in phys}
    midx = {r['market_pool_id']:r for r in pools}
    iidx = {r['itinerary_id']:r for r in it}
    check('ITINERARY_AND_PHYSICAL_IDENTITIES', len(iidx)==len(it)==860 and len(pidx)==len(phys)==376 and len(legs)==1092, dict(itineraries=len(it),incidence=len(legs),physical=len(phys)))
    grouped = defaultdict(list)
    use, od, accounts = defaultdict(float), defaultdict(float), defaultdict(dict)
    failures=[]
    for r in legs:
        grouped[r['itinerary_id']].append(r)
        parent=iidx[r['itinerary_id']]
        if any(r[k]!=parent[k] for k in ['model_id','source_commit','scenario_id','candidate_id','priority']): failures.append(r['itinerary_id'])
        use[(r['candidate_id'],r['scenario_id'],r['priority'],r['physical_leg_id'])]+=float(r['seat_segments_used'])
    for r in money:
        if r['itinerary_id']:accounts[r['itinerary_id']][r['account']]=float(r['amount_rub'])
    examples=[]
    for iid,r in iidx.items():
        ll=sorted(grouped[iid],key=lambda x:int(x['leg_sequence']))
        ff=[pidx[l['physical_leg_id']] for l in ll]
        n=float(r['sold_journeys'])
        valid=(len(ll)==int(r['leg_count']) and close(r['segment_pax'],n*len(ll)) and close(r['local_journeys'],n if len(ll)==1 else 0) and close(r['transfer_journeys'],n if len(ll)>1 else 0))
        valid &= all(close(l['seat_segments_used'],n) for l in ll)
        valid &= ff[0]['origin']==r['origin'] and ff[-1]['destination']==r['destination']
        valid &= all(a['destination']==b['origin'] and float(a['arrival_utc_minute'])<=float(b['departure_utc_minute']) for a,b in zip(ff,ff[1:]))
        a=accounts[iid]
        valid &= close(a['gross_revenue'],n*float(r['whole_journey_fare_rub'])) and close(a['incremental_revenue'],a['gross_revenue']-a['foregone_RW_revenue'])
        valid &= close(r['net_new_journeys'],n-float(r['migrated_RW_journeys']))
        pool=midx[r['market_pool_id']]
        valid &= (r['origin'],r['destination'],r['scenario_id'])==(pool['origin'],pool['destination'],pool['scenario_id'])
        if not valid:failures.append(iid)
        od[(r['candidate_id'],r['scenario_id'],r['priority'],r['market_pool_id'])]+=n
        if len(ll)==2 and len(examples)<3:
            examples.append(dict(itinerary_id=iid,origin=r['origin'],destination=r['destination'],sold_journeys=n,seat_segments=sum(float(l['seat_segments_used']) for l in ll),gross_revenue_once=a['gross_revenue'],fare=r['whole_journey_fare_rub'],physical_leg_ids=[l['physical_leg_id'] for l in ll]))
    check('ALL_ITINERARY_CONTINUITY_SEATS_FARE_ONCE',not failures,dict(failures=failures[:10],checked=len(it)))
    check('SHARED_CAPACITY_PER_STRATEGY_SCENARIO_PRIORITY',all(v<=float(pidx[k[3]]['seats'])+1e-7 for k,v in use.items()),dict(used_flight_groups=len(use),maximum_load=max(use.values())))
    check('SHARED_OD_PER_STRATEGY_SCENARIO_PRIORITY',all(v<=float(midx[k[3]]['pool_journeys'])+1e-6 for k,v in od.items()),dict(used_market_groups=len(od)))
    ak=lambda r:(r['itinerary_id'],r['physical_leg_id'],r['scenario_id'],r['priority'])
    check('CAPACITY_ALLOCATION_EXACT_INCIDENCE',len({ak(r) for r in alloc})==len(alloc) and {ak(r):float(r['allocated_seats']) for r in alloc}=={ak(r):float(r['seat_segments_used']) for r in legs},dict(rows=len(alloc)))
    cost=[r for r in money if r['account']=='flight_variable_cost']
    ck=lambda r:(r['candidate_id'],r['scenario_id'],r['priority'],r['physical_leg_id'])
    check('FLIGHT_COST_ONCE_PER_SCENARIO',len({ck(r) for r in cost})==len(cost)==628 and all(not r['itinerary_id'] and r['physical_leg_id'] in pidx for r in cost),dict(cost_rows=len(cost)))
    sums=defaultdict(lambda:defaultdict(float))
    for r in money:sums[(r['candidate_id'],r['scenario_id'],r['priority'])][r['account']]+=float(r['amount_rub'])
    economics=[]
    for r in t['evaluation_summary']:
        if r['model_id']!='ciri:conditional16':continue
        a=sums[(r['candidate_id'],r['scenario_id'],r['priority'])]
        contribution=a['gross_revenue']-a['foregone_RW_revenue']-a['flight_variable_cost']-a['new_pax_variable']+a['saved_old_pax_variable']
        economics.append(dict(candidate=r['candidate_id'],scenario=r['scenario_id'],priority=r['priority'],gross_delta=a['gross_revenue']-float(r['gross_revenue_rub']),contribution_delta=contribution-float(r['contribution_before_fixed_rub']),full_budget_unknown=not r['full_budget_rub']))
    check('ECONOMIC_SUMMARY_RECONCILIATION',all(abs(r['gross_delta'])<1e-6 and abs(r['contribution_delta'])<1e-6 and r['full_budget_unknown'] for r in economics),dict(summaries=len(economics)))
    write('economics_recomputed.csv',economics)
    save('two_leg_examples.json',examples)
    entity={r['entity_code']:r for r in t['entity_resolution']}
    held={c for c,r in entity.items() if r['key_status']!='MATCHED_UNIQUE_DIRECTORY'}
    check('HELD_DIRECTORY_IDENTITIES_EMPTY',all(not entity[c]['airport_id'] and not entity[c]['airport_key_version'] for c in held) and entity['MOW']['key_status']=='GROUP_NOT_AIRPORT',dict(held=sorted(held)))
    heldkeys=[]
    for r in phys:
        for side in ['origin','destination']:
            if r[side] in held and r[side+'_airport_key']:heldkeys.append(r['physical_leg_id'])
    check('NO_PHYSICAL_IDENTITY_HOLD_BYPASS',not heldkeys,dict(failures=heldkeys))
    weather=t['airport_weather_month']
    check('WEATHER_KEYS_NO_HOLD_BYPASS',len(weather)==432 and len({(r['entity_code'],r['station_id'],r['month']) for r in weather})==432 and all(r['entity_code'] not in held and r['airport_identity_match']=='True' and r['admitted_scope']=='HISTORICAL_STATION_CONTEXT_ONLY' and float(r['observed_hours'])<=float(r['calendar_hours']) for r in weather),dict(rows=len(weather),airports=len({r['entity_code'] for r in weather})))
    tourism=t['candidate_regional_tourism']
    cells={(r['canonical_region_id'],r['indicator_code'],r['year']) for r in tourism}
    check('TOURISM_SOURCE_GRAIN_AND_UNIT_HOLD',len(tourism)==624 and len(cells)==42 and all(r['entity_code'] not in held and r['year']=='2024' and ((r['numeric_use_admitted']=='True')==bool(r['unit_native'] and not r['unit_missing_reason'])) for r in tourism),dict(incidence=len(tourism),source_cells=len(cells),unknown_incidence=sum(r['numeric_use_admitted']=='False' for r in tourism)))
    # All 386 endpoint links rebuilt directly, including empty cards and retained holds.
    mappings=btable('candidate_addendum_primary17b/candidate_endpoint_mapping.csv')
    cards=ptable('route_product_cards.csv')
    cidx={r['card_id']:r for r in cards}
    errors=[]
    for line,r in enumerate(mappings,2):
        c=cidx[r['card_id']]
        target=phys if r['mapping_kind']=='PHYSICAL_LEG_ENDPOINT_CONTEXT' else it if r['mapping_kind']=='FINAL_OD_SUBSTITUTE_CONTEXT' else []
        idfield='physical_leg_id' if target is phys else 'itinerary_id'
        matches=[x[idfield] for x in target if all(x[k]==r[k] for k in ['origin','destination','period_start','period_end']) and x['model_id']==r['baseline_model_id'] and x['candidate_id']==r['baseline_candidate_id']]
        valid=set(filter(None,r['baseline_row_ids'].split(';')))==set(matches) and int(r['baseline_matched_row_count'])==len(set(matches))
        valid &= all(r[k]==c[k] for k in ['origin','destination','period_start','period_end'])
        valid &= r['numerical_uplift']=='NONE' and r['model_input_changed']=='False' and not r['seats'] and not r['observed_final_OD'] and not r['net_fare']
        if r['baseline_model_id']:
            if c['value_status']=='UNKNOWN':valid &= r['status']=='UNKNOWN_NO_POSITIVE_SOURCE_CARD'
            elif c['clock_consensus_status']=='CONFLICT_HOLD':valid &= r['status'].startswith('HOLD_EXACT_CLOCK')
            elif 'YEAR_ASSIGNED' in c['value_status']:valid &= r['status'].startswith('HOLD_YEAR_ASSIGNMENT')
        if not valid:errors.append(line)
    check('ADDENDUM_ALL_386_TARGET_LINKS_AND_HOLDS',len(mappings)==386 and not errors,dict(rows=len(mappings),failures=errors[:20],status_counts=dict(Counter(r['status'] for r in mappings))))
    baseline_paths=subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE,PREFIX+'data_bridge/'],cwd=ROOT,text=True).splitlines()
    changed=[p for p in baseline_paths if blob(BASELINE,p)!=blob(BRIDGE,p)]
    check('BASELINE_70_FILES_FROZEN',len(baseline_paths)==70 and not changed,dict(files=len(baseline_paths),changed=changed))


def raw_context():
    receipts=btable('checks/raw_receipts.csv')
    byid={r['dataset_id']:r for r in receipts}
    def body(dataset):
        r=byid[dataset]
        return raw(r['held_raw_path'],r['expected_stored_sha256'],r['publisher'],r['source_grain'],r['source_url'])
    weather=btable('normalized/airport_weather_month.csv')
    weather_cells=[]
    for station in ['218230-99999','287220-99999']:
        b=body('noaa_lite_'+station+'-2024')
        months=defaultdict(list)
        for line in gzip.decompress(b).decode().splitlines():
            v=list(map(int,line.split()));months[f'{v[0]:04d}-{v[1]:02d}'].append(v)
        # Frozen parsed source, including station not used by the new airport join.
        parsed=table('ef365ac2a936117e5b3bb12ea99c816d7b1a101c','context/16_agent_research/alternative/normalized/weather_monthly_2024.csv')
        for r in [r for r in parsed if r['station_id']==station]:
            mm=months[r['month']]
            temps=[v[4]/10 for v in mm if v[4]!=-9999]
            winds=[v[8]/10 for v in mm if v[8]!=-9999]
            recomputed=dict(observed_hours=len({tuple(v[:4]) for v in mm}),calendar_hours=calendar.monthrange(2024,int(r['month'][-2:]))[1]*24,
                            temperature_observations=len(temps),wind_observations=len(winds),temperature_below_minus20_count=sum(x < -20 for x in temps),
                            wind_ge12_ms_count=sum(x>=12 for x in winds),temperature_mean_c=round(sum(temps)/len(temps),3))
            for k,v in recomputed.items():
                weather_cells.append(dict(station=station,month=r['month'],field=k,recomputed=v,pinned=r[k],match=abs(float(r[k])-v)<=0.00051))
    check('INDEPENDENT_RAW_WEATHER_PARSE',all(r['match'] for r in weather_cells),dict(cells=len(weather_cells),stations=2))
    write('weather_cells_recomputed.csv',weather_cells)
    def ziprows(b):
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            member=next(n for n in z.namelist() if n.endswith('.csv'))
            with z.open(member) as f:
                yield from enumerate(csv.DictReader(io.TextIOWrapper(f,encoding='utf-8-sig'),delimiter=';'),2)
    context=table('505e24663e5952bae9b9540bb9a5a622663bfc2a','context/16_agent_research/core/integration_v1/social/gateway_region_context_2024.csv')
    cross={r['airport_iata']:r for r in btable('normalized/gateway_region_crosswalk.csv')}
    selected={int(r['source_row']) for r in context}
    rawrows={n:r for n,r in ziprows(body('branches__social_economy__tochno_regions_tourism')) if n in selected}
    tourism=[]
    for r in context:
        s=rawrows[int(r['source_row'])]
        ok=s['object_oktmo']==cross[r['airport_iata']]['regional_oktmo'] and s['year']==r['year']=='2024' and s['indicator_code']==r['indicator_code'] and close(s['indicator_value'],r['value'])
        ok &= s['indicator_unit']==(r['unit_native'] or 'ND')
        tourism.append(dict(airport=r['airport_iata'],region=cross[r['airport_iata']]['regional_oktmo'],indicator=r['indicator_code'],year=r['year'],source_row=r['source_row'],value=r['value'],unit_raw=s['indicator_unit'],match=ok))
    check('INDEPENDENT_RAW_TOURISM_42_CELLS',all(r['match'] for r in tourism),dict(cells=len(tourism),unknown_units=sum(r['unit_raw']=='ND' for r in tourism)))
    write('tourism_cells_recomputed.csv',tourism)
    # Deterministic distinct-key municipal sample; no claims about all 4044 cells.
    municipal=table('505e24663e5952bae9b9540bb9a5a622663bfc2a','context/16_agent_research/core/branches/social_economy/normalized/example_join_municipal_2024.csv')
    clean=[r for r in municipal if r['municipal_type_agrees']=='True']
    chosen=[clean[i] for i in sorted(set([0,1,len(clean)//4,len(clean)//2,3*len(clean)//4,len(clean)-2,len(clean)-1]))]
    out=[]
    for dataset,field,locator,typefield in [('tochno_bdmo_municipal_wages','gross_monthly_wage_rub','wage_source_row','wage_source_mun_type'),('tochno_bdmo_municipal_population','annual_average_population_persons','population_source_row','population_source_mun_type')]:
        ids={int(r[locator]) for r in chosen}
        selected={n:r for n,r in ziprows(body(dataset)) if n in ids}
        for r in chosen:
            s=selected[int(r[locator])]
            ok=s['region_id']==r['region_id'] and s['oktmo']==r['oktmo'] and s['year']==r['year']=='2024' and s['mun_type']==r[typefield] and close(s['indicator_value'],r[field])
            ok &= s['indicator_unit']==('Рубль' if dataset.endswith('wages') else 'Человек')
            out.append(dict(dataset=dataset,source_row=r[locator],region=r['region_id'],oktmo=r['oktmo'],year=r['year'],municipal_type=s['mun_type'],field=field,value=r[field],unit_raw=s['indicator_unit'],period_raw=s['indicator_period'],match=ok))
    check('INDEPENDENT_RAW_MUNICIPAL_SAMPLE',all(r['match'] for r in out),dict(keys=len(chosen),cells=len(out),clean_keys_total=len(clean),scope='NO_CITY_OR_CATCHMENT_ALLOCATION'))
    write('municipal_cells_recomputed.csv',out)


def fidelity():
    """Check source values directly as well as internal accounting consistency."""
    ciri='93fa5cf4a10ab67e05c93d19fc5375fc58ef9299'
    cp='context/16_conditional_decision/model/'
    it=btable('normalized/itinerary.csv')
    source=table(ciri,cp+'sales.csv')
    mapping=dict(candidate_id='network',scenario_id='scenario',priority='priority',origin='origin',destination='destination',departure_date='date',
                 sold_journeys='sold_journeys',local_journeys='local_journeys',transfer_journeys='transfer_journeys',
                 net_new_journeys='net_new_journeys',migrated_RW_journeys='migrated_RW_total',whole_journey_fare_rub='effective_fare',segment_pax='segment_pax')
    failures=[]
    for r in it:
        s=source[int(r['source_row'])-2]
        if r['source_commit']!=ciri or r['model_id']!='ciri:conditional16' or any(r[k]!=s[v] for k,v in mapping.items()):failures.append(r['itinerary_id'])
    check('SOURCE_TO_ITINERARY_ALL_860',len(source)==len(it) and not failures,dict(rows=len(it),failures=failures))
    phys=btable('normalized/physical_leg.csv')
    sourceflights=table(ciri,cp+'flights.csv')
    ids={(r['network'],r['id']):r for r in sourceflights}
    pp=[r for r in phys if r['model_id']=='ciri:conditional16']
    check('SOURCE_TO_CIRI_PHYSICAL_ALL_314',len(pp)==len(ids)==314 and all(all(r[k]==ids[r['candidate_id'],r['author_flight_id']][v] for k,v in dict(origin='origin',destination='destination',departure_date='date',departure_utc_minute='departure_utc_minute',arrival_utc_minute='arrival_utc_minute',block_minutes='block_minutes',seats='capacity').items()) for r in pp),dict(rows=len(pp)))
    cap=table(ciri,cp+'capacity.csv')
    costs=btable('normalized/money_ledger.csv')
    costs=[r for r in costs if r['account']=='flight_variable_cost']
    costidx={(r['candidate_id'],r['scenario_id'],r['priority'],r['physical_leg_id'].split(':')[-1]):r for r in costs}
    use=defaultdict(float)
    for r in btable('normalized/itinerary_leg.csv'):
        use[(r['candidate_id'],r['scenario_id'],r['priority'],r['physical_leg_id'].split(':')[-1])]+=float(r['seat_segments_used'])
    check('SOURCE_CAPACITY_AND_COST_ALL_628',len(costidx)==len(cap) and all(close(costidx[r['network'],r['scenario'],r['priority'],r['id']]['amount_rub'],r['flight_variable_cost']) and close(use[r['network'],r['scenario'],r['priority'],r['id']],r['sold_segment_pax']) and use[r['network'],r['scenario'],r['priority'],r['id']]<=float(r['capacity'])+1e-7 for r in cap),dict(rows=len(cap)))
    resources=btable('normalized/resource_ledger.csv')
    check('DATED_FLIGHT_RESOURCE_BLOCK_IDENTITY',all(sum(r['candidate_id']==s['candidate_id'] for r in pp)==int(s['weekly_legs']) and close(sum(float(r['block_minutes']) for r in pp if r['candidate_id']==s['candidate_id'])/60,s['weekly_block_hours']) for s in resources),dict(networks=len(resources)))
    stage=btable('normalized/ciri_stage1_scores.csv')
    check('STAGE22_NOT_CONDITIONAL16_UPGRADE',len(stage)==14 and all(r['model_id']=='ciri_stage1:screening' and r['source_commit']=='6ec84a7d2a6eb50b547a61df82fc5a424f48f146' for r in stage) and all(r['source_commit']==ciri for r in it),dict(stage_rows=len(stage)))
    annual=btable('normalized/route_program.csv')
    routes=table('2f03b693a62c219e9475fcd1e26295039f6a49d7','data/processed/network_routes.csv')
    check('NASTYA_ANNUAL_SOURCE_FIDELITY',len(annual)==len(routes)==128 and all(all(r[k]==routes[int(r['source_row'])-2][v] for k,v in dict(scenario_id='scenario',variant='variant',origin_code='from',destination_code='to',frequency_each_way_week='freq_week_each_way',passenger_segments_annual='pax_year_segments',local_segments_annual='pax_year_local',transfer_segments_annual='pax_year_transfer_seg').items()) and not r['flight_date'] and r['market_unit']=='ANNUAL_BIDIRECTIONAL_SEGMENTS' for r in annual),dict(routes=len(annual)))
    flow=btable('normalized/line_flow_context.csv')
    check('ANNUAL_SEGMENT_FLOW_NOT_RENAMED_OD',len(flow)==1428 and all(not r['weekly_OD_conversion'] and r['market_grain']=='ANNUAL_BIDIRECTIONAL_LINE_SEGMENTS; NOT_FINAL_OD' for r in flow),dict(rows=len(flow)))
    entity={r['entity_code']:r for r in btable('normalized/entity_resolution.csv')}
    stations=table('ef365ac2a936117e5b3bb12ea99c816d7b1a101c','context/16_agent_research/alternative/normalized/join_airport_station_mapping.csv')
    parsed=table('ef365ac2a936117e5b3bb12ea99c816d7b1a101c','context/16_agent_research/alternative/normalized/weather_monthly_2024.csv')
    sp={(r['station_id'],r['month']):r for r in parsed}
    sm={(r['station_id'],'OA:'+r['airport_id']):r for r in stations}
    w=btable('normalized/airport_weather_month.csv')
    errors=[]
    for r in w:
        m=sm.get((r['station_id'],r['airport_id']))
        p=sp.get((r['station_id'],r['month']))
        ok=m is not None and p is not None and m['iata']==r['entity_code'] and m['icao']==entity[r['entity_code']]['directory_icao'] and r['month'].startswith('2024-')
        ok &= all(r[k]==p[v] for k,v in dict(observed_hours='observed_hours',calendar_hours='calendar_hours',temperature_observations='temperature_observations',wind_observations='wind_observations',frost_sample_count='temperature_below_minus20_count',wind_sample_count='wind_ge12_ms_count',temperature_mean_c='temperature_mean_c').items())
        if not ok:errors.append((r['entity_code'],r['station_id'],r['month']))
    check('WEATHER_ALL_432_SOURCE_CELLS_IDENTITY',not errors,dict(rows=len(w),failures=errors))
    # Reconstruct the full addendum target-key set. Per-row validity alone would miss omissions.
    cards=ptable('route_product_cards.csv')
    expected=set()
    for c in cards:
        targets=set()
        for rows,kind in [(phys,'PHYSICAL_LEG_ENDPOINT_CONTEXT'),(it,'FINAL_OD_SUBSTITUTE_CONTEXT')]:
            for r in rows:
                if all(c[k]==r[k] for k in ['origin','destination','period_start','period_end']):
                    targets.add((r['model_id'],r['candidate_id'],kind))
        if not targets:targets={('','','NO_BASELINE_ENDPOINT_MATCH')}
        expected.update((c['card_id'],*t) for t in targets)
    mappings=btable('candidate_addendum_primary17b/candidate_endpoint_mapping.csv')
    actual={(r['card_id'],r['baseline_model_id'],r['baseline_candidate_id'],r['mapping_kind']) for r in mappings}
    check('ADDENDUM_TARGET_LINK_COMPLETENESS',expected==actual and len(actual)==len(mappings)==386,dict(expected=len(expected),actual=len(actual),missing=sorted(expected-actual),extra=sorted(actual-expected)))
    held={c for c,r in entity.items() if r['key_status']!='MATCHED_UNIQUE_DIRECTORY'}
    program=btable('normalized/route_program.csv')
    links=btable('normalized/candidate_airport_link.csv')
    check('AUXILIARY_IDENTITY_JOINS_RETAIN_HOLDS',all(not r['airport_id'] and not r['airport_key_version'] for r in links if r['entity_code'] in held) and all(not r[side+'_airport_key'] for r in program for side in ['origin','destination'] if r[side+'_code'] in held),dict(held_codes=sorted(held)))
    params=btable('normalized/parameter_registry.csv')
    admission=btable('candidate_addendum_primary17b/fact_to_baseline_mapping.csv')
    check('FACT_ADMISSION_NO_CURRENT_MRO_OR_EXACT_REN_UPGRADE',all(r['numerical_uplift']=='NONE' and r['model_input_changed']=='False' for r in admission) and any('CURRENT_PARAM_UPGRADE_HOLD' in r['mapping_status'] for r in admission if r['source_entity']=='KUF') and any('NO_EXACT_VALUE_REPLACEMENT' in r['mapping_status'] for r in admission if r['source_entity']=='REN'),dict(facts=len(admission),baseline_kuf_mro=[r['value_status'] for r in params if r['candidate_id']=='KUF' and r['parameter_id']=='ssj_mro']))


if __name__=='__main__':
    for name in ['build_package.py','curate.py','check_and_summarize.py','primary_facts.csv','findings.md','source_lock.json','manifest.json']:
        blob(PRIMARY,PREFIX+'primary_evidence/'+name,'Code or claim register personally inspected; exact lines in report/findings')
    primary()
    bridge()
    raw_context()
    fidelity()
    save('independent_results.json',dict(checks=checks,failed=sum(r['status']=='FAIL' for r in checks),
                                        author_code_executed=False,network_used=False,raw_copied=False,
                                        pins=dict(primary=PRIMARY,bridge=BRIDGE,baseline=BASELINE)))
    save('source_manifest.json',dict(git_inputs=list(inputs.values()),raw_inputs=list(raw_inputs.values()),
                                   grain_note='Raw datasets retain publisher/year/unit grain; checks are bounded and do not prove economic feasibility.'))
    print(json.dumps(dict(checks=len(checks),failed=[r for r in checks if r['status']=='FAIL'],git_inputs=len(inputs),raw_inputs=len(raw_inputs)),ensure_ascii=False,indent=2))
    raise SystemExit(1 if any(r['status']=='FAIL' for r in checks) else 0)
