#!/usr/bin/env python3
"""Author data/identity checks; does not validate RW demand or cash."""
import calendar
import csv
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import subprocess

R=Path(__file__).resolve().parent
REPO=R.parents[2]
checks=[]
def ok(name,condition,detail=''):
    checks.append(dict(check_id=f'P10-V{len(checks)+1:02d}',name=name,pass_=bool(condition),evidence=detail))
def csvrows(name):
    with (R/name).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256((R/p).read_bytes()).hexdigest()
def near(a,b):return math.isclose(float(a),float(b),rel_tol=1e-11,abs_tol=1e-7)

pins=json.loads((R/'input_manifest.json').read_text())
pin_pass=True
for p in pins:
    b=subprocess.check_output(['git','show',f'{p["commit"]}:{p["source_path"]}'],cwd=REPO)
    pin_pass &= hashlib.sha256(b).hexdigest()==p['sha256']
    if p['saved_path']:pin_pass &= (R/p['saved_path']).read_bytes()==b
ok('ВходыпрочитанипровереныпоexactSHA/gitshow',pin_pass,f'{len(pins)}pinrecords;nomovingbranch')

cs=csvrows('source_claims.csv');pass_claims=True
for c in cs:
    p=R/c['source_text_path'];lines=p.read_text().splitlines();excerpt='\n'.join(lines[int(c['line_start'])-1:int(c['line_end'])])+'\n'
    pass_claims &= sha(c['source_text_path'])==c['source_text_sha256']
    pass_claims &= hashlib.sha256(excerpt.encode()).hexdigest()==c['source_row_sha256']
    if c.get('source_pdf_sha256'):pass_claims &= sha(f'sources/{c["source_id"]}.pdf')==c['source_pdf_sha256']
ok('Локаторыстроки/sourcehash/PDFhashвосстанавливаются',pass_claims,f'{len(cs)}sourceclaims')
facts={c['claim_id']:c for c in cs}
ok('ПервичныеRW2025иDP2025дают11.1млнориентир',near(float(facts['CL-DP25']['value'])-float(facts['CL-RW25']['value']),11100000),'Округлённыеpublishedvalues;notexactpassingrank')
ok('Рынок2025совместимdomestic+international',near(81450000+27400000,facts['CL-MKT25']['value']))
ok('AFindividualиgroupнеперепутаны',near(facts['CL-AF25']['value'],29547300) and near(facts['CL-AFG25']['value'],55340300))
ok('Новыйофициальный2026PDFпроверенза10месяцев',near(facts['CL-AF26']['value'],24901500) and near(facts['CL-AFG26']['value'],46704700))
ok('RW2024расхождениесохранено',near(facts['CL-RW24']['value'],2900000) and 'расхождение' in facts['CL-RW24']['coverage'])

ass=csvrows('assumptions_register.csv');aids={r['assumption_id'] for r in ass}
ok('РеестрassumptionIDsуникален',len(aids)==len(ass),f'{len(aids)}IDs')
ok('Всеassumptionимеютавтора/почему/диапазонилиUNKNOWN/чувствительность/какзапросить',all(all(r.get(k) for k in ['selected_by','rationale','justified_range_or_UNKNOWN','sensitivity_or_impact','how_to_refine']) for r in ass))
refpass=True
for name in ['growth_cases.csv','resource_calendar_monthly.csv','type_productivity.csv','required_resources_by_type.csv','resource_frontier.csv','funding_exposure_drivers.csv','roadmap.csv']:
    for r in csvrows(name):
        refpass &= all(a in aids for a in r.get('assumption_ids','').split(';') if a)
ok('ИспользованныеassumptionIDsнайденывреестре',refpass)

ts=csvrows('threshold_scenarios.csv');tr=csvrows('competitor_trajectories.csv')
ok('Будущийпорогпосчитанкаквторойсоперник',all(near(t['threshold_reported_pax'],sorted([float(x['reported_pax_condition']) for x in tr if x['competition_scenario_id']==t['competition_scenario_id'] and x['year']==t['year']],reverse=True)[1]) for t in ts))
ok('Сменаcarrierпорога№2показана',next(t for t in ts if t['threshold_case_id']=='C_MIXED_HISTORY:2030')['threshold_carrier_under_condition']=='Россия')
ok('Ростпорога2028вrecoveryнефиксирован13.8',near(next(t for t in ts if t['threshold_case_id']=='C_RECOVERY059:2028')['threshold_reported_pax'],13800000*1.059**3))

ms=csvrows('resource_calendar_monthly.csv');ps=csvrows('type_productivity.csv');pm={p['productivity_id']:p for p in ps}
keys={r['resource_case_id'] for r in ms}
ok('Каждаяветвьресурсаимеет24месяцабезповторов',len(ms)==192 and len(keys)==8 and all(len([r for r in ms if r['resource_case_id']==k])==24 and len({r['month'] for r in ms if r['resource_case_id']==k})==24 for k in keys))
ok('2028високосныйгодучтён',all(r['days_in_month']=='29' for r in ms if r['month']=='2028-02'))
ok('НовыхTu214восновнойветви0;старыйпаркнеобнулён',all(r['new_TU214_inducted_end']=='0' for r in ms) and {r['published_listed_tails'] for r in csvrows('existing_fleet_separate_types.csv')}=={'20','3','2'})
ok('No-new0толькодобавочнаяёмкостьновыхSJ',all(near(r['conditional_occupied_segment_equivalents'],0) for r in ms if r['delivery_scenario_id']=='no_new'))
ok('НетновыхSJдоH22027',all(near(r['conditional_occupied_segment_equivalents'],0) for r in ms if r['month']<'2027-07'))
arithmetic=True
for r in ms:
    p=pm[r['productivity_id']];m=int(r['month'][5:]);h=json.loads(p['block_hours_per_active_day_by_month'])[m-1]
    calc=float(r['conditional_commercial_tail_days'])*h*float(p['availability_including_MRO_and_reserve'])/float(p['block_hours_per_segment'])*float(p['seats'])*float(p['LF_seat_segment_condition'])
    arithmetic &= near(calc,r['conditional_occupied_segment_equivalents'])
ok('Помесячнаяcapacityарифметикапересчитана',arithmetic)
ph=[r for r in ms if r['resource_case_id']=='SJ_NO_NEW_TU:phased:базовая' and r['month'].startswith('2028')]
phcap=sum(float(r['conditional_occupied_segment_equivalents']) for r in ph)
full4=4*float(pm['SJ100_PD8_NEW:базовая']['annual_occupied_segment_equivalents_per_tail'])
ok('4бортавконце2028не4полныхбортогода',near(phcap,455748.75) and phcap<full4,f'phased={phcap};full4={full4}')
cal_events=csvrows('inputs/P03_DELIVERIES_diagnostic_delivery_events.csv')
ok('P03календарьточновоспроизведён',len(cal_events)==10 and {r['conditional_entry_date'] for r in cal_events if r['delivery_scenario_id']=='phased'}=={'2027-07-31','2027-10-31','2028-01-31','2028-05-01'})
ok('Базоваяиосторожнаяпроизводительностьпоказаныраздельно',all(next(float(x['annual_occupied_segment_equivalents_per_tail']) for x in ps if x['aircraft_type']==p['aircraft_type'] and x['condition']=='осторожная')<float(p['annual_occupied_segment_equivalents_per_tail']) for p in ps if p['condition']=='базовая'))
ok('ДействующийRRJ95иновыйSJ100/PD8отдельно',{'RRJ95_EXISTING','SJ100_PD8_NEW','TU214_EXISTING','TU214_NEW_DOMESTIC','TU204_100B_EXISTING','B777_200ER_EXISTING'}=={p['aircraft_type'] for p in ps})

gs=csvrows('growth_cases.csv')
ok('Матрицасценариевполна:4delivery×2productivity×2year×4competition×2attribution',len(gs)==128 and len({r['growth_case_id'] for r in gs})==128)
sharepass=True
for g in gs:
    k=float(g['reference_RW_KEEP_pax']);mk=float(g['reference_market_KEEP_pax']);delta=float(g['conditional_occupied_segment_capacity']);alpha=float(g['alpha_new_to_Russian_market'])
    sharepass &= near(float(g['conditional_share_delta_pp']),100*((k+delta)/(mk+alpha*delta)-k/mk))
ok('ДельтадолиP−KEEPпересчитананаодномпериодеиусловии',sharepass)
ok('НеизвестныйP09/cashненазван0',all(not g['actual_P09_net_reported_passengers'] and not g['actual_P09_share_delta_pp'] and not g['actual_full_incremental_result_RUB'] and not g['actual_peak_funding_RUB'] for g in gs))
ok('ReferenceKEEPнеобнулёнвнулевойветви',all(near(g['reference_RW_KEEP_pax'],2700000) for g in gs))
rr=csvrows('required_resources_by_type.csv');resourcepass=True
for x in rr:
    need=int(x['additional_indivisible_tails_at_design_point']);cap=float(x['occupied_segment_per_tail_year']);gap=float(x['gap_to_reference_KEEP'])
    resourcepass &= need*cap>=gap and (need-1)*cap<gap
ok('Ресурсокруглёнпотипам,безсреднегосмешанногопарка',resourcepass)
fr=csvrows('resource_frontier.csv')
ok('11Tuнеприписаныконкретномугодуcommercialavailability',all(r['commercial_availability_year'].startswith('UNKNOWN') for r in fr))
ok('Долгосрочныересурсныеальтернативынесложеныкакновыенезависимыеэффекты',all(float(r['residual_reported_equivalent_gap'])>=0 for r in fr) and all('disjoint' in r['status'] for r in fr))

ex=csvrows('metric_bridge_examples.csv')
ok('Контрпримеродинрейс/дваэтапа:100reportedпри200segments',ex[0]['OD_journeys']=='100' and ex[0]['passenger_segments']=='200' and ex[0]['reported_passengers_if_historical_definition_applies']=='100')
ok('Контрпримердварейса:200reportedпри100journeysи100тарифах',ex[1]['reported_passengers_if_historical_definition_applies']=='200' and ex[1]['fare_charges']=='100')
ok('Контрпримерdigital:повторныетежесамыепродажинеприбавлены',ex[2]['extra_reported_passengers_on_sum']=='0')
b=json.loads((R/'growth_bridge.json').read_text())
ok('P09/P11ещёнеготовы,финальныецифрыJSONnull',all(v is None for v in b['outputs_pending'].values()) and b['upstream']['P09']['commit'] is None and b['upstream']['P11']['commit'] is None)
ok('24месячныйbridgeнеизвестен,ненулевой',len(csvrows('growth_bridge_monthly_pending.csv'))==24 and all(not r['net_new_reported_passengers'] and r['status']=='PENDING_UPSTREAM_PINS_NOT_ZERO' for r in csvrows('growth_bridge_monthly_pending.csv')))
ok('Вмостеестьполныйконтекстиотчётныйадаптер',{'programme_version','keep_evaluation_id','input_manifest_sha256','reporting_adapter_version','whole_business_KEEP_version','P11_experiment_version'}.issubset(set(b['join_key'])) and b['number2_deadline'] is None)

fds=csvrows('funding_exposure_drivers.csv');costpass=True
for r in fds:costpass &= near(float(r['post_handover_aircraft_months'])*1e6,r['normalised_lease_exposure_RUB_if_1m_per_aircraft_month'])
ok('Денежнаяэкспозициясчитаетсякакнормировка,нецена',costpass and all(not r['lease_rate_RUB_per_aircraft_month'] for r in fds))
ok('54posthandoveraircraftmonthsдляphased',near(sum(float(r['post_handover_aircraft_months']) for r in fds if r['resource_case_id']=='SJ_NO_NEW_TU:phased:базовая'),54))
f=json.loads((R/'financing_thresholds.json').read_text())
ok('Fundingиспользуетсовместныйcash,аокупаемостьнепридумана',f['break_even_date'] is None and 'NOT' in f['required_committed_financing'] and f['money_engine'].startswith('P06 only'))
ok('Укаждойзарегистрированнойгипотезыестьисход/доказательство/граница',len(csvrows('growth_hypothesis_outcomes.csv'))==7 and all(r['outcome'] and r['evidence'] and r['scope_and_revisit'] for r in csvrows('growth_hypothesis_outcomes.csv')))
ok('Дорожнаякартаимеетсигналидействие,включаяотсутствиепоставок/финансирования',len(csvrows('roadmap.csv'))==11 and all(r['advance_signal'] and r['stop_or_revisit_signal'] and r['adaptation'] for r in csvrows('roadmap.csv')))

result={'version':'P10-1.0-20261112','authority':'author data and arithmetic verification only; not independent review','passed':sum(x['pass_'] for x in checks),'total':len(checks),'status':'PASS' if all(x['pass_'] for x in checks) else 'FAIL','checks':checks,'not_run':['realRWannualP09/P06demandandseatallocation','commercialavailability/crewandMROacceptance','wholebusinessKEEPcash/financingforecast','digitalcausalacceptance/dedupwithactualP11','independentnumerical/decisionreview','livebooking/payment/externalpublication']}
(R/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'passed':result['passed'],'total':result['total'],'failures':[x for x in checks if not x['pass_']]},ensure_ascii=False,indent=2))
if result['status']!='PASS':raise SystemExit(1)
