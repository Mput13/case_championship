#!/usr/bin/env python3
"""Offline legal/fleet evidence tables and explicit applicability gates."""
import csv,pathlib,json,hashlib
R=pathlib.Path(__file__).resolve().parent

def read(n):
 with (R/n).open(newline='') as f:return list(csv.DictReader(f))
def write(n,rows):
 keys=list(dict.fromkeys(k for x in rows for k in x))
 with (R/n).open('w',newline='') as f:
  w=csv.DictWriter(f,keys);w.writeheader();w.writerows(rows)
def loc(sid,needle):
 p=R/'raw/web'/sid/'text.txt'
 if not p.exists():return 'RAW_NOT_AVAILABLE'
 lines=p.read_text().split('\n')
 inds=[str(i) for i,x in enumerate(lines,1) if needle.lower() in x.lower()]
 return str(p.relative_to(R))+':'+','.join(inds[:8]) if inds else 'NOT_FOUND:'+needle
rules='favt_regional_rules';url='https://old.favt.gov.ru/public/materials/0/3/9/e/7/039e77a7205ca81e3070590870e45a3e.pdf'
controls=[
 ('SUB01','program_identity','Regional network is decision 22-64160-00191-R; 22-68861-00481-R is a different Far East program','Program identification; matching carrier and geography required','Решение о порядке предоставления субсидии',1),
 ('SUB02','unit','Amount is completed eligible flights times contracted per-flight amount capped by appendix1 times appendix6 coefficient','Not a universal RUB/passenger grant; leg allocation must match contract','Размер субсидии рассчитывается',7),
 ('SUB03','recipient','One subsidized route has one carrier recipient; aircraft/AOC and subsidiary commercial-code conditions apply','Existing competitor listing cannot be transferred automatically to RW','только одному',6),
 ('SUB04','budget_contract','Within annual budget limits and subsidy contracts; reduced limits may reduce contracted amount','2026 list is not 2027 entitlement and not a cash receipt','в пределах лимитов бюджетных обязательств',6),
 ('SUB05','operator_selection','Priority goes first to prior subsidized operator then prior unsubsidized operator under the stated selection rule','New RW bid is not guaranteed by being non-Moscow','При поступлении заявки',6),
 ('SUB06','report_cash','Monthly report due by15 next month; FAVT checks within10days; cash within10workingdays after positive payment decision','Model accrual and dated receipt are separate; rejected/corrected report can delay cash','ежемесячно',6),
 ('SUB07','geography','Different RF subjects; hub-airport, distance and other requirements have cofinanced/remote/Arctic exceptions','Do not replace route eligibility by a blanket nonMOW Boolean','пункты отправления и назначения маршрута расположены в разных',11),
 ('SUB08','distance','Standard max3000km for routes to/from Siberia/FarEast,1500km others; exceptions for cofinanced and intraFarEast routes','Test exact airports; not all physical paths qualify','не превышает 3000',11),
 ('SUB09','prior_volume','Prior-year route volume <=10000 both directions FarEast,8000 others, with explicit cofinancing/remote exceptions; special15k branch','High planned demand alone does not establish disqualification or support','не превысил 10 тыс.',11),
 ('SUB10','season','May-Sep general restriction with listed Arctic/FarEast/remote/low federal share exceptions','Need month-specific eligibility and funded flights','перевозки по маршрутам не осуществляются',12),
 ('SUB11','fare','Special fare is passenger fare including VAT constrained by appendix2, with stated increases','A maximum passenger fare is not a carrier grant and not net yield','специальный тариф',9),
 ('SUB12','cap','Appendix1 max per one-way flight depends on seats and distance; special15k branch halves cap','Table cap is not award; coefficient and financing conditions stay explicit','84 - 103',14),
 ('SUB13','double_support','Routes subsidized from federal budget under other government decisions are excluded by stated condition','Do not stack incompatible federal programs','иными',11),
 ('SUB14','transfer_legs','For transport with intermediate landing and change to another aircraft type, formula sums section grants','Not proof every transfer passenger earns two grants','с промежуточной посадкой',7),
 ('SUB15','joint_grant_fare_condition','Paragraph7a requires ALL economy seats be offered at no more than the applicable special fare, no later than5days before service starts; it does not guarantee all seats sell','Grant+retail fare cap+period+cofinancing must be admitted together. Do not replace1773with cap/flight while keeping unconstrained yield. Regional fare increases need specific authority; special fare includesVAT and is not net yield. A no-support/market-fare case and a support/capped-fare case need separate joint budgets.','на все места',13),
]
write('subsidy_controls.csv',[dict(id=i,topic=t,fact=f,model_consequence=c,source_id=rules,primary_url=url,locator=loc(rules,n),pdf_page=p,classification='PRIMARY_RULE_VERSION7; FUTURE_AWARD_UNKNOWN') for i,t,f,c,n,p in controls])
# Appendix1 row84-103, visually checked p14. These are upper tariff-grid values, not payments.
bands=[('lt200',0,199,104280),('201_300',201,300,113643),('301_400',301,400,132367),('401_500',401,500,151091),('501_600',501,600,169816),('601_700',601,700,188540),('701_800',701,800,207265),('801_900',801,900,225989),('901_1000',901,1000,244713),('1001_1100',1001,1100,263438),('1101_1200',1101,1200,282162),('1201_1400',1201,1400,310249),('1401_plus',1401,None,403871)]
write('subsidy_cap_84_103_seats.csv',[dict(distance_band=b,min_km=lo,max_km=hi if hi else '',cap_rub_per_oneway_flight=cap,unit='RUB/one-way completed flight before territory coefficient and applicable reductions',source_id=rules,locator=loc(rules,'84 - 103'),pdf_page=14,applicability='84-103actual seats; cofinanced-seat footnote; paragraph5d halves cap; not award or cash') for b,lo,hi,cap in bands])
# Appendix2 base passenger fare includingVAT; authorized increases are separate facts.
fares=[2017,2258,2741,3225,3708,4191,4674,5157,5640,6123,6606,7089,7572,8055,8538,9021,9504,9987,10470,10953]
fare_bands=[('lt200',0,199)]+[(f'{lo}_{lo+99}',lo,lo+99) for lo in range(201,1902,100)]+[('2001_plus',2001,None)]
write('subsidy_special_fare_grid.csv',[dict(distance_band=b,min_km=lo,max_km=hi if hi else '',base_special_fare_rub_including_vat=fare,unit='RUB/passenger/one direction/economy seat',source_id=rules,locator=loc(rules,'2 017'),pdf_page=15,applicability='Base appendix2 grid. Specific region fare increase and Arctic/FarEast/paragraph5d multipliers require route-period evidence; not final baggage quote or net yield.') for (b,lo,hi),fare in zip(fare_bands,fares)])
ss=read('subsidy_route_matches.csv');pairs=read('pair_registry.csv')
app=[]
for p in pairs:
 s=[x for x in ss if x['route']==p['route']];rw=[x for x in s if 'Ред Вингс' in x['airline']]
 app.append(dict(route=p['route'],hypotheses=p['hypotheses'],networks=p['networks'],source_period='2026',listed_operators=';'.join(sorted({x['airline'] for x in s})),rw_program_list_match_2026=bool(rw),other_carrier_program_list_match_2026=any(x not in rw for x in s),periods_2026=' | '.join(sorted({x['period'] for x in s})),eligibility_2027_2028='UNKNOWN_REQUIRES_FUTURE_RULE_AND_SELECTION',signed_RW_contract_2027_2028='NOT_OBSERVED',RW_award_amount='UNKNOWN',unit='per eligible performed flight under decision and contract',cap='appendix1 seat-distance grid; coefficient/reductions/financing required',cash='UNKNOWN_NOT_INFERRED_FROM_LIST',baseline_no_award='explicit scenario: zero grant; not estimate of unknown actual award',source_id='favt_regional_oldhost;favt_regional_rules',classification='ROUTE_PROGRAM_MATCH' if s else 'NO_MATCH_IN_THIS_2026_LIST_NOT_PROOF_OF_INELIGIBILITY'))
for row in app:
 matching=[x for x in ss if x['route']==row['route']]
 row['cofinancing_notes_2026']=' | '.join(sorted({x['cofinancing_note'] for x in matching}))
 row['joint_fare_obligation']='Paragraph7a: offer ALL economy seats <= applicable special fare, no later than5days before service. Apply jointly with grant/period/cofinancing; no unconstrained yield substitution.'
 row['special_fare_2027_2028']='UNKNOWN; appendix2 base grid and authorized route/region/period increases must be checked; retail includesVAT, net-yield bridge required'
write('subsidy_applicability.csv',app)
# Useful cap arithmetic on actual officially listed distances; no extension to hypothetical unmatched pairs.
examples=[]
for route in ['OMS-SVX','IJK-SVX','KJA-OMS','KVX-MRV','KUF-NJC','KUF-MRV','OMS-UFA']:
 s=next(x for x in ss if x['route']==route);km=int(s['km'].replace(' ',''));cap=next(v for b,lo,hi,v in bands if lo<=km and (hi is None or km<=hi))
 special_fare=next(f for (b,lo,hi),f in zip(fare_bands,fares) if lo<=km and (hi is None or km<=hi))
 examples.append(dict(route=route,official_km=km,assumed_actual_seats=100,appendix1_cap_rub_oneway=cap,coefficient_assumed_for_example=1,per_award_rate='UNKNOWN<=cap subject to rules',example_roundtrip_envelope_rub=2*cap,actual_RW_award='UNKNOWN; operator and period check mandatory',base_special_fare_rub_including_vat=special_fare,joint_fare_condition='ALL economy seats <= applicable authorized special fare; base grid increase and retail-to-net bridge UNKNOWN; no unconstrained yield',source_id=rules+';favt_regional_oldhost',classification='DIAGNOSTIC_UPPER_ENVELOPE_NOT_REVENUE'))
write('subsidy_cap_examples.csv',examples)
fleet=[]
for typ,n,seats,km,needle in [('SSJ100 (RRJ-95)',20,100,4200,'SSJ100 (RRJ-95)'),('Ту-214',3,194,5200,'Ту-214'),('Ту-204-100B',2,210,3800,'Ту-204-100B'),('Boeing777-200ER',3,412,9100,'Boeing 777-200ER')]:
 fleet.append(dict(id='FLEET'+str(len(fleet)+1),aircraft_type=typ,count=n,seats=seats,range_km=km,fact='Company published fleet configuration snapshot',as_of='2026-11-10 capture; page update date not stated',source_id='rw_fleet',primary_url='https://flyredwings.com/about/park/',locator=loc('rw_fleet',needle),observation_vs_model='PRIMARY_COMPANY_PUBLISHED',free_aircraft='UNKNOWN',dispatch_ready_aircraft='UNKNOWN',applicability='nominal fleet and marketing range; not payload guarantee, tail availability or free resource'))
for row in [
 dict(id='FLEET5',aircraft_type='PD-8 engine, not SJ-100 aircraft',fact='Regulator reports engine type certification on2026-06-05',source_id='pd8_certificate',primary_url='https://special.favt.gov.ru/novosti-novosti/?id=18741',needle='завершила сертификацию',observation_vs_model='PRIMARY_REGULATOR_STATEMENT',applicability='Engine certificate does not prove SJ-100 aircraft certificate or airline entry into service'),
 dict(id='FLEET6',aircraft_type='SJ-100/PD-8',fact='Chemezov announced first airline handovers in H2 2027 in firsthand interview15Sep2026',source_id='sj100_interview',primary_url='https://www.vesti.ru/ns/chemezov-nazval-sroki-peredachi-aviakompaniyam-pervykh-sj-100-s-dvigatelyami-pd-8',needle='Передача российским',observation_vs_model='PRIMARY_FIRSTHAND_INTERVIEW_PLAN',applicability='Industry timing plan; no RW quantity, RW-specific months or commercial-ready fleet; not a guarantee'),
 dict(id='FLEET7',aircraft_type='new Russian types unspecified',fact='RW says it will be among the first operators and highlights crew preparation',source_id='rw_first_operator',primary_url='https://flyredwings.com/press/news/roman-chuev-stal-generalnym-direktorom-red-wings/',needle='первых',observation_vs_model='PRIMARY_COMPANY_PLAN',applicability='No quantity/calendar by type. Does not turn5/10 SJ-100 into a company forecast'),
 dict(id='FLEET8',aircraft_type='new import-substituted Tu-214',count=11,fact='UAC press office told publisher first aircraft of11 expected in2027; FNB-funded lease scheme',source_id='tu214_firsthand_interview',primary_url='https://www.business-gazeta.ru/news/702033',needle='из этих 11',observation_vs_model='PRIMARY_FIRSTHAND_PRESS_OFFICE_QUOTATION_PLAN',applicability='11 is announced batch, not11in2027; yearly distribution, RW handovers, lease payments, induction/crew/configuration unknown'),
]:
 row['locator']=loc(row['source_id'],row.pop('needle'));fleet.append(row)
write('fleet_facts.csv',fleet)
# No invented company delivery path. Exact resource thresholds remain algebraic inputs for methods.
gates=[('on_time_staged','T(t) receives named aircraft in stages from no earlier than H2 2027; n(t) to be supplied','Deliveries do not operate until induction+crew+MRO acceptance','Treat docs20 5/10as diagnostic alternatives only'),('partial','0<N_delivered(t)<N_plan(t)','Network limited to available dated aircraft and hours; no annual52week multiplication of a Dec week','No numerical RW subset verified'),('delay','First airline handover shifted to later month/year','Earlier timetable and contribution become0for unflown project flights; retain launch/contract cash costs','Delay duration must be named scenario, not forecast'),('none','N_new(t)=0in selected horizon, explicitly a stress scenario','Use verified spare resource or signed donor changes; C33/partner retiming may proceed within current resource','Not a claim that RW receives0aircraft')]
write('fleet_delivery_gates.csv',[dict(scenario=s,delivery_condition=d,network_consequence=c,evidence_limit=l,resource_formula='available_by_type(t)=existing_dispatch_ready(t)+inducted_new(t)-KEEP_commitments(t)-MRO(t)-reserve(t)',minimum_project_condition='project_required_working_aircraft(t)<=available_by_type(t); block/rotation/crew constraints also required',SJ100_RW_count_forecast='UNKNOWN',Tu214_RW_annual_count_forecast='UNKNOWN',observation_vs_model='SCENARIO_AND_RESOURCE_IDENTITY') for s,d,c,l in gates])
# Inventory all HTTP receipts; failed reads remain visible.
reg=[]
for p in sorted((R/'raw/web').glob('*/receipt.json')):
 x=json.loads(p.read_text());x['receipt_path']=str(p.relative_to(R));x['fitness']='FULL_RAW_CAPTURE_NOT_AUTOMATIC_CLAIM_ACCEPTANCE' if 'raw_path' in x else 'ACCESS_FAILURE_NO_NEGATIVE_FACT'
 if x.get('text_path') and len((R/x['text_path']).read_text().strip())<80:
  x['fitness']='SHORT_OR_EMPTY_EXTRACTION; no schedule inferred'
 if x['source_id'] in ('favt_2026_order','favt_order637_2026'):
  x['fitness']='SCANNED_ORDER; page1 visual context only, attachments not captured as part of PDF'
 if x['source_id']=='favt_xlsx_mainhost':x['fitness']='PRIMARY_BINARY;423rows compared to captured HTML in subsidy_source_checks.json'
 reg.append(x)
write('source_registry.csv',reg)
print('controls',len(controls),'fleet',len(fleet),'route applicability',len(app),'HTTP receipts',len(reg))
