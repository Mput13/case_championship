#!/usr/bin/env python3
"""Independent, offline review of exact Git objects. Never imports owner builders.

Run from this checkout. Writes only next to this script. Requires lxml, openpyxl,
pdftotext. No network; reads ancestor objects to check inherited provenance.
"""
import collections as C
import csv
import datetime as dt
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess as sp
import sys
from zoneinfo import ZoneInfo
from lxml import html
from openpyxl import load_workbook

SHA = '38f0f7ae8a10b6a60bd2d5ab39b18a9865e2b78b'
SCOPE = 'context/28_evening_run_20261110/evidence/'
OUT = Path(__file__).resolve().parent
PROBES = OUT / 'probes'
PROBES.mkdir(exist_ok=True)
cache = {}
reads = {}
results = []

def git_bytes(commit, path):
    key = (commit, path)
    if key not in cache:
        cache[key] = sp.check_output(['git', 'show', commit + ':' + path])
        reads[key] = {'commit': commit, 'path': path,
                      'bytes': len(cache[key]), 'sha256': digest(cache[key])}
    return cache[key]

def digest(b): return hashlib.sha256(b).hexdigest()
def raw(p): return git_bytes(SHA, SCOPE + p)
def txt(p): return raw(p).decode('utf-8-sig')
def rows(p): return list(csv.DictReader(io.StringIO(txt(p))))
def js(p): return json.loads(raw(p))
def check(name, condition, detail=None):
    results.append({'check': name, 'passed': bool(condition), 'details': detail})

# Independently compare all declared historical blobs and exact package hashes.
manifest = js('input_manifest.json')
for x in manifest:
    b = git_bytes(x['commit'], x['path'])
    check('git input: ' + x['path'], b == raw(x['snapshot']) and
          digest(b) == x['sha256'] and len(b) == x['bytes'])
output = js('output_manifest.json')
for x in output['files']:
    b = raw(x['path'])
    check('sealed output: ' + x['path'], len(b) == x['bytes'] and digest(b) == x['sha256'])
paths = sp.check_output(['git', 'ls-tree', '-r', '--name-only', SHA, SCOPE], text=True).splitlines()
receipts = [js(p[len(SCOPE):]) for p in paths if p.endswith('/receipt.json')]
for x in receipts:
    for pathfield, hashfield in [('raw_path', 'sha256'), ('text_path', 'text_sha256')]:
        if x.get(pathfield): check('receipt ' + x['source_id'] + ' ' + pathfield,
                                  digest(raw(x[pathfield])) == x[hashfield])

# Fresh extraction from original PDF bytes (no HTTP). Keep text, not copied PDFs.
for sid in ['favt_regional_rules', 'favt_2026_pdf', 'omsk_winter_pdf']:
    b = raw(f'raw/web/{sid}/source.pdf')
    extracted = sp.check_output(['pdftotext', '-layout', '-', '-'], input=b)
    (PROBES / (sid + '.txt')).write_bytes(extracted)
    check('fresh pdftotext: ' + sid, extracted == raw(f'raw/web/{sid}/text.txt'), digest(extracted))
if '--render' in sys.argv:
    for sid, first, last in [('favt_regional_rules',13,15),('omsk_winter_pdf',2,2),('favt_2026_pdf',1,1)]:
        sp.run(['pdftoppm','-f',str(first),'-l',str(last),'-scale-to','1700','-png','-',str(PROBES/sid)],
               input=raw(f'raw/web/{sid}/source.pdf'),check=True,stdout=sp.DEVNULL,stderr=sp.PIPE)
rules = txt('raw/web/favt_regional_rules/text.txt')
check('regional identity v7', '22-64160-00191' in rules and 'Версия 7' in rules)
dfo = txt('raw/web/favt_2026_pdf/text.txt')
check('separate DFO identity', '22-68861-00481' in dfo and 'Аврора' in dfo)
check('all seats five days original clause', all(s in rules for s in
      ['не позднее чем за 5 дней', 'на все места в салоне экономического класса', 'не превышающей размера\nспециального тарифа']))
check('retail includes VAT', 'с учетом налога на добавленную стоимость' in rules)

# Independent raw HTML rowspan/colspan reader, and XLSX cell-value/merged-range reader.
table = html.fromstring(raw('raw/web/favt_regional_oldhost/source.html')).xpath('//table')[-1]
occupied = {}
htmlgrid = []
for ri, tr in enumerate(table.xpath('.//tr')):
    col = 0
    for cell in tr.xpath('./th|./td'):
        while (ri, col) in occupied: col += 1
        val = ' '.join(cell.text_content().split())
        for dr in range(int(cell.get('rowspan', '1'))):
            for dc in range(int(cell.get('colspan', '1'))): occupied[ri+dr, col+dc] = val
        col += int(cell.get('colspan', '1'))
    if ri: htmlgrid.append([occupied.get((ri, k), '') for k in range(11)])
wb = load_workbook(io.BytesIO(raw('raw/web/favt_xlsx_mainhost/source.xlsx')), data_only=True)
ws = wb.active
merged = {}
for rng in ws.merged_cells.ranges:
    v = ws.cell(rng.min_row, rng.min_col).value
    for rr in range(rng.min_row, rng.max_row+1):
        for cc in range(rng.min_col, rng.max_col+1): merged[rr, cc] = v
xlsxgrid = [[merged.get((r, c), ws.cell(r, c).value) for c in range(1, 12)]
            for r in range(3, ws.max_row+1)]
# Styled blank rows below the table carry no source values.
while xlsxgrid and all(v is None for v in xlsxgrid[-1]): xlsxgrid.pop()
fields = ['route_no','airline','origin_city','destination_city','km','aircraft','seats',
          'period','flights_per_week','round_trips_2026','cofinancing_note']
def norm(v, index):
    s = '' if v is None else str(v)
    s = re.sub(r'\s+', '', s.replace('\\n', ''))
    if index in (0, 4, 6, 8, 9):
        try: return str(Decimal(s.replace(',', '.')).normalize())
        except InvalidOperation: pass
    return s
def counts(grid): return C.Counter(tuple(norm(v, i) for i, v in enumerate(r)) for r in grid)
hc, xc = counts(htmlgrid), counts(xlsxgrid)
check('raw HTML/XLSX all11 multiset', hc == xc and len(htmlgrid) == len(xlsxgrid) == 423,
      {'HTML':len(htmlgrid), 'XLSX':len(xlsxgrid), 'HTML_only':sum((hc-xc).values()),
       'XLSX_only':sum((xc-hc).values()), 'normalization':'Decimal exact, whitespace only; all11fields retained'})
extract = rows('extracts/favt_regional_2026_full.csv')
check('HTML exported extract all11', counts([[r[k] for k in fields] for r in extract]) == hc)
route_matches = rows('subsidy_route_matches.csv')
check('18matched program rows remain exact source rows',len(route_matches)==18 and
      all(tuple(norm(r[k],i) for i,k in enumerate(fields)) in hc for r in route_matches))
old = rows('raw/git/4a976356/data/raw/favt_subsidy_2026.csv')
check('old CSV retained 446', len(old) == 446)
changes = {}
for r in rows('subsidy_route_matches.csv'):
    same = [o for o in old if all(norm(o[a], 1) == norm(r[b], 1) for a,b in
           [('airline','airline'),('origin','origin_city'),('destination','destination_city'),('period','period')])]
    changes.setdefault(r['route'], []).append({'current':r,'prior':same})
check('new RW IJK November-December row',any(r['current']['period']=='01.11.2026-31.12.2026' and
      not r['prior'] and 'Ред Вингс' in r['current']['airline'] for r in changes['IJK-SVX']))
check('KUF NJC version frequency2to3',any(r['current']['flights_per_week']=='3' and
      any(o['flights_per_week']=='2' for o in r['prior']) for r in changes['KUF-NJC']))
check('OMS UFA version roundtrips31to5',any(r['current']['round_trips_2026']=='5' and
      any(o['round_trips_2026']=='31' for o in r['prior']) for r in changes['OMS-UFA']))
(PROBES/'version_differences.json').write_text(json.dumps({k:changes.get(k) for k in
    ['IJK-SVX','KUF-NJC','OMS-UFA']}, ensure_ascii=False, indent=2)+'\n')

# Lookup seven diagnostic examples in independent PDF grids and official distances.
capline = next(s for s in rules.splitlines() if '84 - 103 **' in s)
caps = [int(s.replace(' ', '')) for s in re.findall(r'\d{3} \d{3}', capline)]
# Compare package grid rather than assuming a transcribed header width.
check('PDF subsidy cap row', caps == [int(r['cap_rub_per_oneway_flight']) for r in rows('subsidy_cap_84_103_seats.csv')], caps)
fareline = next(s for s in rules.splitlines() if '2 017' in s and '10 953' in s)
fares = [int(s.replace(' ', '')) for s in re.findall(r'\d{1,2} \d{3}', fareline)]
check('PDF special fare grid', fares == [int(r['base_special_fare_rub_including_vat']) for r in rows('subsidy_special_fare_grid.csv')], fares)
for r in rows('subsidy_cap_examples.csv'):
    km = int(r['official_km'])
    # Appendix1 has <200,201-300,...,1001-1100,1101-1200,1201-1400,1401+.
    ci = 0 if km<=200 else ((km-201)//100+1 if km<=1200 else (11 if km<=1400 else 12))
    fi = 0 if km<=200 else min((km-201)//100+1, 19)
    relevant = [s for s in extract if s['route'] == r['route']]
    check('joint cap/fare example '+r['route'], int(r['appendix1_cap_rub_oneway']) == caps[ci]
          and int(r['base_special_fare_rub_including_vat']) == fares[fi]
          and int(r['example_roundtrip_envelope_rub']) == 2*caps[ci]
          and any(Decimal(norm(s['km'],4)) == km for s in relevant)
          and r['assumed_actual_seats']=='100' and r['coefficient_assumed_for_example']=='1'
          and 'UNKNOWN' in r['actual_RW_award'], {'km':km, 'cap':caps[ci], 'retail':fares[fi]})

# Reconstruct and compare the critical source records without owner code.
obs = rows('service_observations.csv')
byid = {r['observation_id']:r for r in obs}
pairs = {r['route'] for r in rows('pair_registry.csv')}
source_reconstructed = []
for sid, base in [('koltsovo_schedule','SVX'),('koltsovo_schedule_arr','SVX'),('samara_schedule','KUF')]:
    tree = html.fromstring(txt(f'raw/web/{sid}/source.html'))
    for ix, tr in enumerate(tree.xpath('//table//tr'),1):
        vals = [' '.join(c.text_content().split()) for c in tr.xpath('./th|./td')]
        oid = f'{sid}_{ix}'
        if oid not in byid: continue
        dep, arr, days, period, carrier, flight, aircraft, endpoint = vals
        a,b = (endpoint,base) if sid.endswith('_arr') else (base,endpoint)
        got = dict(origin=a,destination=b,departure_local=dep,arrival_local=arr,weekdays=days,
                   period=period,carrier=carrier,flight=flight,aircraft=aircraft)
        check('fresh raw schedule '+oid, all(byid[oid][k]==v for k,v in got.items()))
        source_reconstructed.append(oid)
for r in obs:
    if not r['observation_id'].startswith('OLD'): continue
    line = int(r['observation_id'][3:])
    inherited = rows('raw/git/4a9971be/context/21_visual_explainer_draft_20261110/inputs/published-services.csv')[line-2]
    check('inherited row '+r['observation_id'], all(r[k]==inherited[k] for k in
          ['origin','destination','flight','carrier','date','period','departure_local','arrival_local','weekdays','aircraft'])
          and r['raw_sha256']==inherited['html_sha256'])

# Follow the pinned derivative back to its real context17 source commit; never
# manufacture a historical primary hash by hashing a URL or newer capture.
lineage = json.loads(git_bytes('4a9971beeacbc40559943eae05b9004c90165917',
                             'context/21_visual_explainer_draft_20261110/inputs_manifest.json'))
entry = next(x for x in lineage['inputs'] if x.get('local')=='inputs/published-services.csv')
check('context21 to context17 blob', git_bytes(entry['commit'],entry['path']) ==
      raw('raw/git/4a9971be/context/21_visual_explainer_draft_20261110/inputs/published-services.csv'))
prior_sources = json.loads(git_bytes(entry['commit'],'context/17_aircraft_route_review/evidence/sources.json'))
oldhash = {s['url']:s['sha256'] for s in prior_sources if s.get('sha256')}
inherited_obs = [r for r in obs if r['observation_id'].startswith('OLD')]
check('129 inherited primary hashes vs context17 metadata',
      sum(bool(r['raw_sha256']) for r in inherited_obs)==129 and
      all(oldhash.get(r['source_url'])==r['raw_sha256'] for r in inherited_obs if r['raw_sha256']),
      {'context17_commit':entry['commit'],'path':entry['path'],
       'blank_primary_hash_preserved':[r['observation_id'] for r in inherited_obs if not r['raw_sha256']],
       'limit':'Historical primary bytes not included here; metadata/blob chain checked; newer capture never substituted.'})

# All fresh UFA rows: active weekdays only, including intermittent departures.
def classnodes(node, tag, classname):
    return node.xpath('.//'+tag+'[contains(concat(" ",normalize-space(@class)," ")," '+classname+' ")]')
for sid, dest in [('ufa_omsk','OMS'),('ufa_surgut','SGC'),('ufa_njc','NJC'),('ufa_mrv','MRV')]:
    tree=html.fromstring(txt(f'raw/web/{sid}/source.html'))
    for ix, node in enumerate(classnodes(tree,'div','b-card-sez-card__main'),1):
        oid=f'{sid}_{ix}'
        if oid not in byid: continue
        def cell(cls):
            return ';'.join(' '.join(n.text_content().split()) for block in classnodes(node,'div',cls)
                            for n in classnodes(block,'span','b-card-sez-card__info'))
        got=dict(origin='UFA',destination=dest,flight=cell('b-card-sez-card__td_number'),
          carrier=cell('b-card-sez-card__td_company'),period=cell('b-card-sez-card__td_period'),
          departure_local=cell('b-card-sez-card__td_time--start'),arrival_local=cell('b-card-sez-card__td_time--end'),
          aircraft=cell('b-card-sez-card__td_flight'),
          weekdays=';'.join(n.text_content().strip() for n in classnodes(node,'span','_active')))
        check('fresh raw UFA '+oid,all(byid[oid][k]==v for k,v in got.items()))
        source_reconstructed.append(oid)

uvt=html.fromstring(txt('raw/web/uvt_schedule/source.html'))
for r in [o for o in obs if o['source_id']=='uvt_schedule']:
    ti,ri=map(int,re.search(r'table (\d+) tbody/tr (\d+)',r['locator']).groups())
    tr=uvt.xpath('//table')[ti-1].xpath('.//tbody/tr')[ri-1]
    vals=[' '.join(c.text_content().split()) for c in tr.xpath('./td|./th')]
    # The two source tables independently print both directions. Flight label
    # selects the direction, not the heading's city or a guessed departure hour.
    side=3 if vals[3]==r['flight'] else 8
    check('fresh raw UVT '+r['observation_id'], vals[side]==r['flight'] and vals[1]==r['period']
          and vals[side+1].replace('-',':')==r['departure_local']
          and vals[side+2].replace('-',':')==r['arrival_local'] and vals[side+3]==r['weekdays']
          and vals[7]==r['aircraft'])
    source_reconstructed.append(r['observation_id'])

oms=txt('raw/web/omsk_winter_pdf/text.txt').split('\n')
for r in [o for o in obs if o['source_id']=='omsk_winter_pdf']:
    li=int(re.search(r'line (\d+)',r['locator'])[1])
    parts=re.split(r'\s{2,}',oms[li-1].strip())
    check('fresh raw OMS '+r['observation_id'], r['departure_local']==parts[5].replace('.',':')
          and r['arrival_local']==parts[9].replace('.',':') and r['period']==parts[7]
          and r['carrier']==parts[8] and r['aircraft']==parts[0])
    source_reconstructed.append(r['observation_id'])

# Advertisements are extracted from captured route cards, not a booking quote.
fare_tree=html.fromstring(txt('raw/web/utair_trip/source.html'))
fare_rows=rows('fare_observations.csv')
for r in fare_rows:
    ix=int(re.search(r'div index (\d+)',r['locator'])[1]);node=fare_tree.xpath('//div')[ix-1]
    href=node.xpath('.//a[1]/@href')[0]
    text=' '.join(node.text_content().split())
    price=int(re.sub(r'\D','',re.search(r'от\s*([\d\s]+)\s*₽',text)[1]))
    dates=';'.join(node.xpath('.//*[contains(@class,"__flightDate")]/text()'))
    check('advertised fare '+href, r['primary_url']=='https://trip.utair.ru'+href and
          r['origin']+'/'+r['destination']==href[1:].upper() and int(r['advertised_from_rub'])==price
          and r['travel_date_label']==dates and r['final_quote']=='False' and r['bag']=='UNKNOWN'
          and r['year'].startswith('NOT_EXPLICIT'))
check('13advertisements only',len(fare_rows)==13)

# Independent date expansion and multiset verification; no counting duplicate publications as service.
week = [dt.date(2026,12,7)+dt.timedelta(days=i) for i in range(7)]
days = dict(zip(['пн','вт','ср','чт','пт','сб','вс'],range(7)))
months = dict(zip(['янв','фев','мар','апр','мая','июн','июл','авг','сен','окт','ноя','дек'],range(1,13)))
expanded = []
held = []
for r in obs:
    if r['date']: dates = [dt.date.fromisoformat(r['date'])]
    else:
        matches = re.findall(r'(\d{2})\.(\d{2})\.(\d{4}|\d{2})',r['period'])
        bounds = [dt.date(int(y) if len(y)==4 else 2000+int(y),int(m),int(d)) for d,m,y in matches]
        if not bounds:
            bounds = [dt.date(2026 if months[m]>=4 else 2027,months[m],int(d)) for d,m in
                      re.findall(r'(\d{1,2})\s+(янв|фев|мар|апр|мая|июн|июл|авг|сен|окт|ноя|дек)',r['period'].lower())]
        allowed = set(range(7)) if 'ежедневно' in r['weekdays'].lower() else {v for k,v in days.items() if k in r['weekdays'].lower()}
        if not bounds or len(bounds)>2 or not allowed:
            held.append(r['observation_id']); continue
        dates = [d for d in week if bounds[0]<=d<=bounds[-1] and d.weekday() in allowed]
    for d in dates:
        if d in week: expanded.append((r['origin'],r['destination'],d.isoformat(),r['flight'].replace(' ',''),
            r['departure_local'],r['arrival_local'],r['aircraft'],r['source_id'],r['observation_id']))
cols = ['origin','destination','date','flight','departure_local','arrival_local','aircraft','source_id','observation_id']
check('independent 359 publication expansion', C.Counter(expanded)==C.Counter(tuple(r[k] for k in cols) for r in rows('dated_service_records.csv')) and len(expanded)==359,
      {'expanded':len(expanded),'held':held})
groups = C.defaultdict(list)
for r in expanded: groups[r[:4]].append(r)
conflicts = {k:v for k,v in groups.items() if len({r[4:7] for r in v})>1}
check('conflicts are KUF SVX',all(k[:2]==('KUF','SVX') for k in conflicts))
check('215 unique /144 duplicates/12 conflicts', len(groups)==215 and len(expanded)-len(groups)==144 and len(conflicts)==12,
      {'unique':len(groups),'duplicates':len(expanded)-len(groups),'conflicts':len(conflicts)})
instances = rows('dated_service_instances.csv')
for r in instances:
    k=tuple(r[c] for c in cols[:4]); group=groups[k]
    check('instance '+str(k), int(r['publication_records'])==len(group) and (r['clock_or_type_conflict']=='True')==(k in conflicts)
          and r['oneway_departures']=='1' and r['departure_local']==' | '.join(sorted({p[4] for p in group}))
          and r['arrival_local']==' | '.join(sorted({p[5] for p in group})))
(PROBES/'conflicts.json').write_text(json.dumps([{'key':k,'publications':v} for k,v in conflicts.items()],ensure_ascii=False,indent=2)+'\n')
registry = rows('pair_registry.csv'); joins=rows('pair_hypothesis_join.csv')
check('45pairs/85joins/10IDs/23positive22gaps', len(pairs)==len(registry)==45 and len(joins)==85 and
      {r['hypothesis'] for r in joins}=={'C01','C03','C04','C07','C10','C14','C17','C31','C33','C35'} and
      sum(r['coverage_status']=='GAP_NOT_ABSENCE' for r in registry)==22 and all(r['route'] in pairs for r in joins))
check('no absence/full market claim', all(r['competitor_absence_established']=='False' and r['complete_market']=='False' for r in registry))
check('all45 joint subsidy/fare gates', all('ALL economy seats' in r['joint_fare_obligation'] and
      'retail includesVAT' in r['special_fare_2027_2028'] and r['signed_RW_contract_2027_2028']=='NOT_OBSERVED'
      for r in rows('subsidy_applicability.csv')))

# Six timing examples independently recalculated with IANA offsets and day shifts.
airports = rows('raw/git/4a9971be/context/21_visual_explainer_draft_20261110/inputs/airports.csv')
tz = {r['iata_code']:r['iana_timezone'] for r in airports if r.get('iata_code') and r.get('iana_timezone')}
def clock(date, text, airport):
    hh, mm = map(int,re.search(r'(\d{2}):(\d{2})',text).groups())
    bump = re.search(r'\(\+(\d+)\)',text)
    date = dt.date.fromisoformat(date)+dt.timedelta(days=int(bump[1]) if bump else 0)
    return dt.datetime.combine(date,dt.time(hh,mm),ZoneInfo(tz[airport])).astimezone(dt.timezone.utc)
timing=[]
for r in rows('alternative_timing_examples.csv'):
    a,b,c=r['path'].split('>')
    firstdep=clock(r['leg1_date'],r['leg1_departure_local'],a)
    arrivals=[clock(r['leg1_date'],v,b) for v in r['leg1_arrival_local'].split(' | ')]
    seconddep=clock(r['leg2_date'],r['leg2_departure_local'],b)
    finalarr=clock(r['leg2_date'],r['leg2_arrival_local'],c)
    waits=[(seconddep-v).total_seconds()/60 for v in arrivals]
    elapsed=(finalarr-firstdep).total_seconds()/60
    for leg in (1,2):
        ids=r[f'leg{leg}_observation_ids'].split(';')
        check('timing source observations '+r['path']+' '+str(leg),all(oid in byid for oid in ids)
              and all(byid[oid]['flight'].replace(' ','')==r[f'leg{leg}_flight'] for oid in ids))
    check('timing '+r['path'], min(waits)==float(r['connection_min_minutes']) and max(waits)==float(r['connection_max_minutes'])
          and elapsed==float(r['elapsed_min_minutes'])==float(r['elapsed_max_minutes']))
    timing.append({'path':r['path'],'waits_minutes':waits,'elapsed_minutes':elapsed})
(PROBES/'timing.json').write_text(json.dumps(timing,indent=2)+'\n')

diagnostic=js('native_reader_diagnostic.json')
check('diagnostic reports rather than reenacts errors', diagnostic['reported_by'].startswith('root intake') and
      'unknown' in diagnostic['layer_finding'] and diagnostic['additional_probe'].startswith('NOT_RUN'))
for x in diagnostic['personally_captured_direct_http']:
    receipt=js(f"raw/web/{x['source_id']}/receipt.json")
    check('diagnostic matches receipt '+x['source_id'], x==receipt)

fleet_facts=rows('fleet_facts.csv')
fleet_text=txt('raw/web/rw_fleet/text.txt')
fleet_html=' '.join(html.fromstring(txt('raw/web/rw_fleet/source.html')).text_content().split())
for label,count,seats in [('SSJ100 (RRJ-95)',20,100),('Ту-214',3,194),('Ту-204-100B',2,210),('Boeing 777-200ER',3,412)]:
    check('fleet snapshot '+label, re.search(re.escape(label)+r'\n'+str(count)+r'\nвместимость\n'+str(seats)+r'\nмест',fleet_text) is not None)
    check('fleet primary HTML '+label,re.search(re.escape(label)+r'\s*'+str(count)+r'\s*вместимость\s*'+str(seats)+r'\s*мест',fleet_html) is not None)
check('nominal not free',all(r['free_aircraft']=='UNKNOWN' and r['dispatch_ready_aircraft']=='UNKNOWN' for r in fleet_facts[:4]))
sj=txt('raw/web/sj100_interview/text.txt');tu=txt('raw/web/tu214_firsthand_interview/text.txt')
check('SJ first industry handovers H2 2027', 'во второй половине 2027 года' in sj and 'Red Wings' not in sj and 'Ред Вингс' not in sj)
check('11Tu214 batch first in2027', 'первые самолеты из этих 11 будут поставлены в 2027 году авиакомпании Red Wings' in tu)
for sid,phrase in [('sj100_interview','во второй половине 2027 года'),
                   ('tu214_firsthand_interview','первые самолеты из этих 11 будут поставлены в 2027 году авиакомпании Red Wings'),
                   ('pd8_certificate','завершила сертификацию самолета Ил-114-300 и двигателя ПД-8'),
                   ('izhavia_substitution','выполняет до конца августа'),
                   ('kirov_mrv_regulator','по четвергам и воскресеньям')]:
    primary_text=' '.join(html.fromstring(txt(f'raw/web/{sid}/source.html')).text_content().split())
    check('primary HTML claim '+sid, phrase in primary_text)
check('four scenarios explicitly conditional',{r['scenario'] for r in rows('fleet_delivery_gates.csv')}=={'on_time_staged','partial','delay','none'})

summary={'reviewed_sha':SHA,'scope':SCOPE,'created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
         'passed':sum(r['passed'] for r in results),'failed':[r for r in results if not r['passed']],
         'input_git_blobs':len(manifest),'output_hashes':len(output['files']),'receipts':len(receipts),
         'raw_hashes':sum(bool(r.get('raw_path')) for r in receipts),'text_hashes':sum(bool(r.get('text_path')) for r in receipts),
         'fresh_airport_rows':len(source_reconstructed),'checks':results,
         'NOT_RUN':['live search/fetch/browser','future award/payment','bookability/final20kg quote/residual inventory',
                    'free tail-level fleet/market/economics acceptance','owner build/verify scripts']}
(OUT/'verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
(OUT/'input_manifest.json').write_text(json.dumps(list(reads.values()),ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='checks'},ensure_ascii=False,indent=2))
sys.exit(bool(summary['failed']))
