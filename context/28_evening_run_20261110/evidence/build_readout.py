#!/usr/bin/env python3
"""Bounded research handoff: observed facts, applicability, unresolved decision inputs."""
import pathlib,csv,re,json,hashlib
from lxml import html
R=pathlib.Path(__file__).resolve().parent

def read(n):return list(csv.DictReader(open(R/n)))
def write(n,rows):
 fields=list(dict.fromkeys(k for x in rows for k in x))
 with (R/n).open('w',newline='') as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)
# Advertised airline fares retain baggage/year/finality limitations.
p=R/'raw/web/utair_trip/source.html';tree=html.fromstring(p.read_text());fare=[]
pairs={x['route'] for x in read('pair_registry.csv')}
for i,x in enumerate(tree.xpath('//div'),1):
 if not any(c.endswith('__flight') for c in x.get('class','').split()):continue
 hrefs=x.xpath('.//a[1]/@href')
 if not hrefs or not re.fullmatch('/[a-z]{3}/[a-z]{3}',hrefs[0]):continue
 a,b=hrefs[0][1:].upper().split('/');route='-'.join(sorted((a,b)))
 if route not in pairs:continue
 text=' '.join(x.text_content().split());price=re.search(r'от\s*([\d\s]+)\s*₽',text)
 dates=x.xpath('.//*[contains(@class,"__flightDate")]/text()')
 if not price:continue
 fare.append(dict(route=route,origin=a,destination=b,carrier='Utair',advertised_from_rub=int(re.sub(r'\D','',price[1])),travel_date_label=';'.join(dates),year='NOT_EXPLICIT; do not auto-shift past dates to next year',bag='UNKNOWN',tax_basis='UNKNOWN',final_quote=False,capture_date='2026-11-10',primary_url='https://trip.utair.ru'+hrefs[0],source_url='https://trip.utair.ru/country/ru',raw_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),locator='div index '+str(i)+'; route href '+hrefs[0],observation_vs_model='PRIMARY_ADVERTISED_FROM_FARE_NOT_REALIZED_NET_YIELD'))
write('fare_observations.csv',fare)
summary={x['route']:x for x in read('pair_registry.csv')}
findings=[
 ('C01','UFA: published direct Utair toSGC/NJC and Azimut toMRV; NJC-MRV listed Azimut competitor. NJC-SVX-MRV timing example545min is a concrete alternative publication, not a sold protected trip.','ufa_surgut;ufa_njc;ufa_mrv;favt_regional_oldhost;alternative_timing_examples.csv','Demand for north-south UFA connections is not the full northern passenger flow; compare direct competitor and viaSVX, not empty market.','ARH-UFA,ARH-OMS,MCX-UFA and SGC-MCX current primary date coverage; total fare, MCT, seats and transfer capture unknown.'),
 ('C03','KUF-MRV3 published departures and KUF-NJC2 in7-13Dec. KUF-SVX-OMS on8Dec has245-250min connection interval due source5min clock conflict.','samara_schedule;koltsovo_schedule_arr;subsidy_route_matches.csv;alternative_timing_examples.csv','Existing base has direct competitor offers; no automatic RW grant from Azimut listing. Possible viaSVX must enter KEEP comparison.','ARH-KUF/KUF-OMS direct complete-market coverage, employer contract guarantees and full base cost missing. Clock conflict retained.'),
 ('C04','OMS-KJA: official2026 program Aeroflot; winter airport PDF operating publication Rossiya FV6846 Mon/Sat01:30-04:35. OMS-IKT S7 twice weekly. Model MOW decomposed only as observed DME/SVO context, no model airport chosen.','favt_regional_oldhost;omsk_winter_pdf','Compact base and historicalOMS12 remain different networks. Existing OMS-KJA is not a newly discovered empty market. Actual airport and future dated KEEP needed.','OMS-KUF/PEE/TJM and manyOMS12 spokes not covered by a complete current-market source; rail, grant/contract2027, free fleet and full base cash unknown.'),
 ('C07','RW SVX-OMS depTue/Fri21:20, OMS arrivesnextday00:00 and returns00:50; actual current turn50min in OMS. Existing SVX-KJA Rossiya7each direction/week; OMS-KJA competitorMon/Sat.','koltsovo_schedule;koltsovo_schedule_arr;omsk_winter_pdf;weekly_service_context.csv','Extension must change the named dated turn or use different resource. Do not call the entire interval free without protecting OMS-SVX return and next SVX assignment.','Actual tail/crew/dispatch gates, return retiming and passenger fare for SVX-OMS-KJA not observed; requires calendar and signed old-network delta.'),
 ('C10','UFA-SGC has14 published dated Utair departures7-13Dec across regular and intermittent flight numbers; company advertises from8000RUB on07December, year implicit and baggage unknown. RW also publishes SVX-SGC twice that week.','ufa_surgut;utair_trip;koltsovo_schedule;fare_observations.csv','Corporate guarantee must beat a concrete competing product and pay for commitment; cannot treat all northern workers as unserved. Advertised price is not RW net yield or contract guarantee.','Employer names, shift calendar, min-seat/tariff guarantee, penalties, actual charter accessibility and remaining inventory unknown.'),
 ('C14','KVX-MRV: Azimut named2026 withSU95/100seats,3weekly program frequency inJan-Apr/Oct-Dec. Regulator repost23Jul saysThu/Sun twice weekly at that time; these periods are not the same schedule.','favt_regional_oldhost;kirov_mrv_regulator','Own RW program competes with existing Azimut product; grant listing and July frequencies cannot validate a winter two-week sanatorium package.','Winter dated outbound/return pair,20kg final fare and sanatorium partner commitments/transfer prices NOT_DONE; primary procurement terms absent.'),
 ('C17','UVT PEE-RGK RT255/256 Sunday08:10/13:50 published07Jun-27Dec2026,CRJ200; existing product reaches winter, not only summer.','uvt_schedule;weekly_service_context.csv','Seasonal reassignment requires an annual resource calendar and current competitor seasonal calendar. One weekly competitor publication is positive evidence, not annual demand.','MMK-PEE current winter source NOT_DONE; PEE-SVX positioning publication not captured; rail/transfer total price unknown.'),
 ('C31','SVX-MRV on7-13Dec has7Aeroflot and7Ural departures per direction; RW own SVX-MRV flight not found in these partial captures. RW fleet3Tu214/2Tu204 are company totals.','koltsovo_schedule;koltsovo_schedule_arr;rw_fleet','Substitution hypothesis needs a real RW donor and both old assignments, and an actually free replacement type. Competitor schedule does not prove RW has a loaded route to upgauge.','RW dated donor flight, replacing type availability, lease/crew/MRO economics, lost alternate assignment and signed full cash unknown; not economic rejection.'),
 ('C33','RW SVX-GOJ4each way and SVX-OMS2each way in selected week; SVX-MRV source shows competitors. GOJ-SVX-OMS existing chronology example has1315min connection.','context21_published_services;koltsovo_schedule;koltsovo_schedule_arr;alternative_timing_examples.csv','Retiming can compare actual same flights. Preserve local sales and existing connections; no invented RW MRV donor; long layover timing does not prove demand.','Tail rotation, MCT, protected fare, local time elasticity and existing connections lost are not observed; threshold calculation can retain symbolic terms.'),
 ('C35','Izhavia own01Aug statement assignedIJK-SVX toRW only until endAug. Official2026 list namesRW Nov-Dec2weekly,SSJ100. No dated winter Izhavia operation or interline agreement found.','izhavia_substitution;favt_regional_oldhost','A partnership based on old carrier identity is conditional. If current legs are bothRW, measure own sales/cannibalization; validate actual partner and fare split before external-feed claim.','WinterIJK-SVX exact dates/clocks, partner commercial authority, through-ticket responsibility, block price and seats NOT_DONE; KRO-GOJ optional variant has additional gaps.')
]
write('hypothesis_readout.csv',[dict(hypothesis=i,network=i+'_registered',observation=f,source_ids=s,decision_implication=d,unresolved=u,research_status='TARGETED_EVIDENCE_COLLECTED; MARKET_COVERAGE_PARTIAL',hypothesis_economic_verdict='NOT_ASSIGNED_BY_EVIDENCE_AGENT') for i,f,s,d,u in findings])
# Missing fields stay actionable. Lack of dated rail quotes is a task limitation, not an economic filter.
gaps=[]
for x in read('pair_registry.csv'):
 priority='P1' if any(c in x['hypotheses'].split(';') for c in ['C01','C03','C04','C07']) else 'P2'
 gaps.append(dict(route=x['route'],hypotheses=x['hypotheses'],priority=priority,published_records=x['published_records'],program_rows=x['official_2026_program_rows'],air_market_status=x['coverage_status'],rail_or_ground_same_date='NOT_DONE; not zero competition',rail_source_attempt='FPC report access failed; no dated RZD trip inventory obtained',fare20kg='NOT_OBSERVED',next_data_owner_or_source='official origin/destination airport schedules; carrier booking quote; RZD exact-date train; signed operator/region contract',effect='future capture/yield, protected transfer and grant revenue remain conditional',revisit_condition='new named date/operator/source or finalized calculation network; do not infer complete coverage from current source set'))
write('decision_gaps.csv',gaps)
print('fare advertisements',len(fare),'hypothesis readouts',len(findings),'gap rows',len(gaps))
