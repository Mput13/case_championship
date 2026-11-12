from pathlib import Path
import csv,json,hashlib,datetime as dt
from collections import defaultdict
R=Path(__file__).resolve().parent
def dump(n,x):(R/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def table(n,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with (R/n).open('w',newline='') as f:
        w=csv.DictWriter(f,keys);w.writeheader();w.writerows(rows)
def read(n):return list(csv.DictReader((R/n).open()))

# Явно отделяем дату чтения страницы от момента действительной котировки.
fare=[]
for dst,price in [('SVX',6605),('GOJ',8300),('OMS',12705),('NOZ',10230),('MSQ',21285)]:
    fare.append(dict(observation_id='REN-AD-'+dst,origin='REN',destination=dst,
        source_id='RW-REN-PRODUCTS',url='https://flyredwings.com/directions/orenburg/',
        carrier='RW advertised product; partners/legs UNKNOWN',fare_rub=price,fare_basis='advertised_from',
        travel_date='UNKNOWN',return_date='UNKNOWN',quoted_as_of='UNKNOWN',retrieved_at='2026-11-12',booking_lead_days='UNKNOWN',
        quoted_party='UNKNOWN',baggage='UNKNOWN for this advertisement; do not join generic Standard20kg to its price',
        fees='UNKNOWN',physical_legs='UNKNOWN; may connect',open_seats='UNKNOWN',
        unit='RUB/advertised product, scope UNKNOWN',period='page snapshot12.11.2026',
        coverage='advertisement; not ticket quote; not future yield',status='NOT_ADMITTED_TO_PRICE_CALIBRATION',assumption_id='A-REN-13'))
p=json.loads((R/'P02_competitor_products.csv.subset.json').read_text())
for r in p['rows']:
    x=r['row']
    if x.get('product_id')!='P02-89cad5af0c237129':continue
    fare.append(dict(observation_id=x['product_id'],origin='SVX',destination='REN',source_id='P02:NEW_RW_SALE',
        url=x['source_url'],carrier='RW advertisement; exact fare product UNKNOWN',fare_rub=x['fare_rub'],
        fare_basis='promotion_from; linked search return02–04Dec; fare scope UNKNOWN',travel_date='2026-12-02',return_date='2026-12-04',
        quoted_as_of='UNKNOWN; campaign10–12Nov',retrieved_at=x['retrieved_at'],booking_lead_days='UNKNOWN for actual quoted product',
        quoted_party='search linkADT1; price party binding UNKNOWN',baggage=x['baggage'],fees='UNKNOWN',physical_legs='UNKNOWN',open_seats='UNKNOWN',
        unit='RUB/advertised product; do not divide by2',period=x['period'],coverage='preserved pinned promotional row; not live quote',
        status='NOT_ADMITTED_TO_PRICE_CALIBRATION',assumption_id='A-REN-13',source_row_line=r['source_row_line'],source_row_sha256=r['source_row_sha256_canonical_json']))
table('fare_observations.csv',fare)

out=read('competitor_offer_rows.csv');out=[x for x in out if x['origin']=='REN']
bydest=defaultdict(list)
for x in out:bydest[x['destination']].append(x['offer_id'])
legacy=json.loads((R/'P02_market_coverage.csv.subset.json').read_text())
coverage=[]
for old in legacy['rows']:
    x=old['row'];mid=x.get('market_id','')
    if ':REN:' not in mid:continue
    dest=mid.split(':')[-1]
    sources=[];scope='UNKNOWN: no newly acquired direct dated REN offer for required pair'
    if dest in bydest:sources=['REN-SCHEDULE-OUT'];scope='published_outbound_intervals_only; not physical inventory or year demand'
    if dest=='GOJ':sources=['REN-GOJ-RGK26'];scope='summer2026 started route2/w; winter/future UNKNOWN'
    if dest=='MSQ':sources=['RW-B2-PRIMARY'];scope='ordered product viaSVX; dates/fare/inventory UNKNOWN'
    if dest=='AER':sources=['REN-WINTER26'];scope='winter press announcement; missing detailed row, not absence'
    if dest=='MOW':sources=['REN-SCHEDULE-OUT'];scope='partial component SVO dated; MOW aggregate not resolved fully to airports'
    coverage.append(dict(market_id=mid,destination_airport_or_city=dest,
        prior_row_id=old['source_row_id'],prior_row_line=old['source_row_line'],prior_row_sha256=old['source_row_sha256_canonical_json'],
        original_P02_coverage=x.get('coverage',x.get('status','see pinned row')),
        new_source_ids=';'.join(sources) or 'NONE',new_offer_ids=';'.join(bydest.get(dest,[])),
        source_scope=scope,missing='2027/28 actual offer/monthlyOD/fare-baggage-lead/open seats/physical continuity',
        period='history2025/offer2026-27;future2027-28 scenario',unit='directed airport/city market',
        coverage='partial evidence only; unobserved not zero; no economic rejection',status='RETAINED_FOR_SHARED_RESEARCH'))
# Добавленные источниками международные/летние пары, которых нет в исходных28.
for dest,sids in [('ALA','REN-SCHEDULE-OUT'),('GYD','REN-SCHEDULE-OUT'),('SSH','REN-SCHEDULE-OUT'),('AYT','REN-WINTER26'),('EVN','RW-REN-EVN26;REN-EVN-AIRPORT26'),('RGK','REN-GOJ-RGK26')]:
    coverage.append(dict(market_id='AIR:REN:'+dest,destination_airport_or_city=dest,prior_row_id='new_local_extension',
        prior_row_line='NOT_IN_REQUIRED28',prior_row_sha256='NOT_APPLICABLE',original_P02_coverage='not local-required28',
        new_source_ids=sids,new_offer_ids=';'.join(bydest.get(dest,[])),source_scope='separate dated/seasonal product as in source registry',
        missing='2027/28 demand/fare/rights/resource',period='2026seasonal/2027-28scenario',unit='directed airport market',
        coverage='not whole international market',status='RETAINED_EXTENSION'))
for row in coverage:row['source_id']=row['new_source_ids'] if row['new_source_ids']!='NONE' else 'P02:market_coverage.csv'
table('market_coverage_update.csv',coverage)

issues=[
 dict(issue_id='REN-SI-01',source_id='REN-SCHEDULE-IN;REN-SCHEDULE-OUT',issue='21Nov WZ901 inbound differs from20Nov WZ5050 outbound; cannot infer shared tail or physical inventory',action='P02/P03 dated continuity evidence',status='OPEN',period='2026-11-20/21'),
 dict(issue_id='REN-SI-02',source_id='REN-WINTER26;REN-SCHEDULE-OUT',issue='AER/AYT in seasonal release but absent from preserved detailed table',action='retain competitor/offer unknown; request seasonal dated row',status='OPEN_COVERAGE',period='ОЗП2026/27'),
 dict(issue_id='REN-SI-03',source_id='REN-TARIFF-INDEX;REN-DISCLOSURE',issue='web tool index advertised editions16Nov/1Dec while direct HTTP saved1Nov edition; snapshots differ in information set',action='use exact saved1Nov reference, future-dated web editions not used for as_of12Nov',status='BOUNDED_BY_PINS',period='2026-11-12 collection'),
 dict(issue_id='REN-SI-04',source_id='REN-TARIFF26',issue='approval header has blank order number/date',action='published reference only; obtain legal applicability/invoice in P04',status='OPEN_APPLICABILITY',period='edition2026-11-01'),
 dict(issue_id='REN-SI-05',source_id='BASE:longlist:REN;REN-TECH',issue='older longlist runway2503m versus current airport page2500x42m',action='keep original row; use primary2500m only as published airport card, exact AIP/NOTAM/dispatch unresolved',status='SOURCE_VERSION_DIFFERENCE',period='pinned BASE / snapshot12Nov'),
 dict(issue_id='REN-SI-06',source_id='REN-SALT-STATS',issue='1.6 vs1.8million visits in public reports; unique persons/mode not established',action='do not admit either as airOD or confidence interval',status='NOT_ADMITTED',period='summer2025'),
 dict(issue_id='REN-SI-07',source_id='REN-UFA-RAIL',issue='specific Yandex archival thread returned HTTP404; search text retained only as discovery evidence',action='fresh primary/date-specific rail source required',status='OPEN_SOURCE',period='2026-09-05 historical'),
 dict(issue_id='REN-SI-08',source_id='RW-REN-PRODUCTS;P02:NEW_RW_SALE',issue='from-prices lack full date/brand/baggage/fees/party binding; promo linked return search',action='no quote/yield/price response calibration',status='NOT_ADMITTED',period='snapshot12Nov / promo10–12Nov'),
 dict(issue_id='REN-SI-09',source_id='REN-GROUND-BUS',issue='generic80minutes vs concrete70/75/85minute intervals; effective date unknown',action='use specific published service, future schedule/access remains scenario',status='BOUNDED',period='snapshot12Nov'),
]
table('source_issues.csv',[dict(x,unit='source issue',coverage='local evidence boundary') for x in issues])
dump('price_collection_outcomes.json',{'as_of':'2026-11-12',
    'attempts':[{'url':'https://www.tbank.ru/travel/flights/routes/REN/MRV/','tool':'web.open','result':'Failed to fetch: TimeoutError'},
                {'url':'https://www.tbank.ru/travel/flights/routes/REN/GOJ/','tool':'web.open','result':'Failed to fetch: TimeoutError'},
                {'url':'https://avia.tutu.ru/f/Orenburg/Mineralnye_Vody/','tool':'web.open','result':'URL is not accessible via this tool'},
                {'url':'https://www.tbank.ru/travel/flights/routes/REN/SVX/','tool':'web.open','result':'READ; stale/general advertising page, month rows and connecting carriers mixed; not accepted quote'}],
    'conclusion':'No comparable dated fare/baggage/fees/booking_lead basket admitted. Not evidence of no market or no fares.',
    'accepted_price_calibration_rows':0,'request_id':'CR-REN-02'})
dump('pdf_visual_qa.json',{'status':'PERSONALLY_VIEWED',
    'pages':[{'file':'sources/REN-TARIFF26.pdf','pages_1_based':[1,2],'images':['sources/REN-TARIFF26-01.png','sources/REN-TARIFF26-02.png'],
              'verified':'edition01.11.2026; blank approvalheader;656/806;5%;82/110;189/273;2329/2990;withoutVAT'},
             {'file':'sources/REN-FUEL26.pdf','pages_1_based':[1],'images':['sources/REN-FUEL26-1.png'],
              'verified':'signature30.10.2026;fuel141405RUB/t from01.11;PVK378.90RUB/kg from03.07.2025;withoutVAT'},
             {'file':'sources/REN-DISCOUNT26.pdf','pages_1_based':[3],'images':['sources/REN-DISCOUNT26-3.png'],
              'verified':'64% new transit45–50t;expiry31.10.2026;exceptions and context'}],
    'limit':'Other PDF pages have text extraction, not claimed all visually reviewed. No PDF created or edited.'})

# Equal-product test checks the consequential part of R1/E1 matching.
fl=read('rotation_templates.csv');matched=[]
for w in sorted({x['week'] for x in fl}):
    def local(pid):
        return sorted((x['origin_airport'],x['destination_airport'],x['departure_utc'],x['arrival_utc'])
            for x in fl if x['programme_id']==pid and x['week']==w and 'SVX' not in [x['origin_airport'],x['destination_airport']])
    assert local('CP-REN-R1')==local('CP-REN-E1')
    matched.append({'week':w,'local_legs_same_clocks_R1_E1':'PASS','same_flights':12})
dump('matched_comparison_checks.json',{'checks':matched,'causal_boundary':'Only local clocks/frequency/same nominal seats matched. Initial location/ferry/base/crew, actual resources and choice/cost unknown.',
    'initial_transition':'P03 must put G1/G2 in identical physical starting states. Positioning SVX→REN for R1/R2 and SVX→OMS for H1 cannot be omitted or free. End-state/exit positioning also required.'})

# Делаем для интегратора доступные человеку формулировки в основных машинных полях.
case=json.loads((R/'case.json').read_text())
case['principal_conclusion']='Сначала совместно сравнить R1 (ночёвка в REN), E1 (полный оборот из SVX) и D1 (дополнительные прямые рейсы из SVX) на одном G1. H1 отдельно сравнивается с несинхронным H1-U и лучшим прямым портфелем на G2. Экономический победитель не выбран.'
case['operations']['ground']='Вокзал–REN автобус101:120руб, первые опубликованные arrival10:00. R1/E1 departure11:30 диагностически учитывает этот доступ; будущий график/такси/дом–вокзал UNKNOWN.'
case['operations']['initial_transition']='Общая начальная позиция реального нового хвоста UNKNOWN. Позиционирование в REN/OMS, платежи запуска, конечная позиция и выход входят в P03/P04; не признаны бесплатными.'
dump('case.json',case)

# Небольшая отдельная запись об одинаковых исходных позициях; unknown не ноль.
a=read('assumptions.csv');a.append(dict(assumption_id='A-REN-20',value='UNKNOWN',unit='initial location;positioning flights/costs;terminal state',
    selected_by='исследователь REN',why_and_source='Парные опыты требуют одного физического начального состояния нового ресурса; недельные шаблоны имеют разные необходимые ночёвки.',
    range_or_unknown='UNKNOWN',affected_conclusions='R1/E1/D1/H1; стартовая ликвидность и база',
    sensitivity='Включить ferry/commercial positioning и выход; при текущем борте отдельно прежние задания.',
    how_to_refine='P03 общий fleet_scope/initial state и P04 startup/exit/cash events',period='2027–2028 плюс предпусковой период',
    coverage='не принятое нулевое позиционирование',status='research_not_team_accepted'))
source_map={
 'A-REN-01':'REN-WINTER26;REN-SCHEDULE-OUT;REN-SCHEDULE-IN',
 'A-REN-02':'programme_candidates.json;исследовательский календарь поездки',
 'A-REN-03':'REN-SCHEDULE-IN;REN-SCHEDULE-OUT;P03',
 'A-REN-04':'REN-TERMINAL26;P03;диагностический сценарий',
 'A-REN-05':'P03:aircraft_type_parameters.csv',
 'A-REN-06':'P03:aircraft_type_parameters.csv;REN-TECH',
 'A-REN-07':'REN-SCHEDULE-OUT;REN-SCHEDULE-IN;REN-GOJ-RGK26;REN-EVN-AIRPORT26;P03',
 'A-REN-08':'programme_candidates.json;P03', 'A-REN-09':'P03',
 'A-REN-10':'условие кейса;P03', 'A-REN-11':'REN-SCHEDULE-OUT;RW-REN-EVN26;RW-B2-PRIMARY;P03',
 'A-REN-12':'REN-DISCOUNT26;P04', 'A-REN-13':'REN-PAX25;BASE:network_routes.csv;P05',
 'A-REN-14':'REN-TARIFF26;REN-FUEL26;REN-CONTRACT-TERMS;P04',
 'A-REN-15':'REN-SCHEDULE-OUT;P02', 'A-REN-16':'REN-SALT-TOUR;REN-SALT-RAIL;REN-SALT-STATS;P05',
 'A-REN-17':'условие задания;P03', 'A-REN-18':'выбор исследователя;P03;P05',
 'A-REN-19':'REN-GROUND-BUS;matched_comparison_checks.json',
 'A-REN-20':'P03;P04;matched_comparison_checks.json'}
for row in a:row['source_id']=source_map[row['assumption_id']]
table('assumptions.csv',a)
p=json.loads((R/'programme_candidates.json').read_text())
for x in p['programmes']:
    x['initial_transition']='Требуется единая начальная позиция G1/G2 и полный маршрут ввода/выхода. Ночёвки в REN или OMS не возникают бесплатно.'
    x['assumption_ids'].append('A-REN-20')
    if x['programme_id'] in ['CP-REN-R1','CP-REN-E1']:
        x['local_departure']='REN11:30 local; все местные часы туда/обратно R1/E1 совпадают; A-REN-19'
        x['assumption_ids'].append('A-REN-19')
p['mechanical_control']={'programme_id':'CP-REN-H1-U','parent':'CP-REN-H1','action':'Сдвинуть T2 на180мин; сохранить физические рейсы и места. Это контроль по синхронизации, не восьмой самостоятельный бизнес-кандидат.'}
dump('programme_candidates.json',p)
pin=json.loads((R/'input_pins.json').read_text())
for x in pin['files']:
    if x['path'].endswith('context/11_practical_screening/city_matrix.csv'):
        x['selection_disposition']='DISCARDED: text filter matched GOJ row mentioning REN; not REN evidence; no output retained'
dump('input_pins.json',pin)
ready=json.loads((R/'readiness.json').read_text())
ready['eligible_for']='Коммит завершённого Stage A координатором; подготовка полных P/KEEP после приёмки общих входов.'
ready['stage_b']='PENDING: общая калибровка спроса, P/KEEP, реальные ресурсы и договоры, денежные/кассовые события, совместное сравнение.'
dump('readiness.json',ready)
print('Supplement: fares',len(fare),'market coverage rows',len(coverage),'issues',len(issues),'matched weeks',len(matched))
