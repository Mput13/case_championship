#!/usr/bin/env python3
"""Build the human handoff metadata and manifest for this role's files only."""
from pathlib import Path
from datetime import datetime, timezone
import csv, json, hashlib

ROOT=Path(__file__).resolve().parent
def js(name,obj):(ROOT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,rows):
    with (ROOT/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    receipt=json.loads((ROOT/'run_receipt.json').read_text())
    checks=json.loads((ROOT/'self_checks.json').read_text())
    assert checks['run_id']==receipt['run_id'] and checks['fail_count']==0
    features=[
      ('WEATHER','alternative@ef365ac2; source_join_review@944b16ac','Historical station-hour temperature/wind2024; station/airport/month join; no visibility/gust/QC or operational labels',
       'Может изменить buffer/reserve/recovery cost при доказанной связи с выполнением рейсов','Не добавлен в HF01/HF07/HF14; календарные выводы получены без него','NOT_RUN_NO_OPERATIONAL_LABELS',
       'Airline dated outcome/visibility/closures and station representativeness; predeclared out-of-time split plus no-weather ablation','Current-city2026 join does not establish station validity2024 or forecast2028; no post counts as downtime'),
      ('TOURISM','alternative@ef365ac2; core@505e2466; review@944b16ac','Monthly EMISS/YTD accommodation and regional cells; coverage/unit holds retained',
       'Может изменить сезонную форму фиксированного отдельно установленного OD','Новые веса/сезонный OD не подставлены; no/with forecast comparison NOT_RUN','NOT_RUN_NO_ENDPOINT_OD',
       'Known indicator/unit/coverage, nonoverlapping regions and independent monthly route sales holdout','Registered stays/persons/nights not unique tourists, catchment or air demand; methodology breaks not growth'),
      ('CORPORATE','alternative@ef365ac2','SIBUR sites/addresses and group-level shift workers; historic2017 Rosneft lead restricted',
       'Конкретные места сбора/работы и доступный оплаченный блок могут заменить неизвестный retail capture','Текущий плательщик/квота/две даты UNKNOWN; no new booked demand','NOT_RUN_NO_AVAILABLE_CONTRACT',
       'Permitted anonymised route/date/quantity/payment/obligations specification and incumbent comparator','Co-location is not all-to-all travel; group stock workers not ticket flow; closed charter not available RW block'),
      ('COMPETITOR_PRODUCT','primary@17b4f348; review@944b16ac; experiment input002','Endpoint schedule rules/dates and named-property rules; operating/nonstop/seats/fare holds retained',
       'Может опровергнуть преимущество нового продукта по конечной поездке','HF14: tolerance0→3 increases matched distinct combinations6→11/12; full product UNKNOWN','LIMITED_DATE_EFFECT_CHECKED_SELF',
       'Same dates/stay and full protected fare/rights/inventory/ground/hotel gates','Schedule match not bookable product, paid demand or RW revenue; no source upgrade for held129SVX rows'),
      ('SVX_EXPERIENCE','primary@17b4f348; review@944b16ac','Carrier-reported2025 aggregate800k, growth15%, transfer factor2.5',
       'Основание проверять продукт существующей базы и baseline вместо обязательной новой базы','Числа не преобразованы в OD, transfers absolute/share or P&L','CONTEXT_ONLY',
       'Definitions, absolute transfer/endpoint counts and dated itinerary revenue/resource baseline','Growth does not identify causal wave effect or profit'),
      ('MRO_BASE_CONTRACT','primary@17b4f348; review@944b16ac','KUF station event2025 and OMS historical service2024',
       'Действующий доступ/цена/мощность могут изменить базирование C03/C04 против цепочки','События не заменили UNKNOWN текущих договоров/свободной мощности','CONTEXT_ONLY',
       'Current scope certificate, RW rights, availability, prices and included-in policy','Historical station is not free current capacity or full base budget')]
    write('feature_admission.csv',[dict(feature_id=a,pinned_reference=b,coverage_and_grain=c,decision_mechanism=d,without_with_result=e,status=f,admission_condition=g,leakage_or_counterexample=h,new_input_set='NONE; future new observations require a separate input_set') for a,b,c,d,e,f,g,h in features])
    alignment=[
      ('LONG_LIST_TOP3','35 products fully inventoried; no new city score','City longlist/top3 from accepted author screening remains separate','No weights/team decisions changed','Inventory35 is not a replacement for >=10city longlist'),
      ('HUB_DIRECT_MIXED','HF01 hub-product timing; HF07 direct via existing-base chain; HF14 incumbent product calendar','Mixed D+previous and common resource/accounting envelope reserved to active methods','Same period/resource and one shared market pool must be checked by final integration','No aggregate winner'),
      ('FINAL_NETWORK_8_12','HF01=2 unique route pairs; HF07=2; C14 targetKVX-MRV plus proposedSVX-KVX positioning/commercial pair','No final8-12jointly executable route set or simultaneous allocation delivered','Need admitted full dated legs, operating resource, market allocation and budget','Pilot stage only; do not add overlaps or property/policy copies'),
      ('COMPETITORS_ENDPOINT','C14 incumbent A4 dated return/calendar; primary UFA/KUF competitors and separate source holds','Paid comparable through fare, inventory/rights/complete ground/hotel UNKNOWN','Compare same origin/destination/stay/outbound+return; operator and protection separately','No zero competitors from no card'),
      ('PASSENGERS_REVENUE_SHARE','Endpoint journeys versus physical seat segments and one fare tested mechanically','Annual OD, realised fares, net new RW after own migration and common Russian denominator UNKNOWN','No multiply one week by52 or airport aggregate into unique trips','Annual passengers/revenue/market-share delta NULL'),
      ('BASE_CAUTIOUS','New turn/MCT/deadline/extension stress axes and original cautious failure retained','New complete base/cautious economics of these35 products not available','Do not reinterpret scenario axes as probabilities; fixed MR07 certificate unchanged','Conditional thresholds only'),
      ('FLEET_TO_2027','All new model tails are hypothetical; C07 return cutoff quantified','Actual available tail, crew/MRO/dispatch/slots and donor obligations UNKNOWN','Use only verified available existing aircraft; new SJ earliestH2_2027 is case constraint','No delivery or free-aircraft claim'),
      ('ROADMAP_2028','Step: validate gates → bounded pilot → conditional joint network scale','Timing/finance/deployed8-12routes and commercial acceptance not established','Delay scenario keeps no-new-aircraft option; expansion only with paid demand/resource/full budget','2028 is conditional target, not approved launch plan'),
      ('KOVER_OTHER_RISKS','No-kover retained; no calendar of restrictions or weather probability added','Recovery/closures/other risks require actual records or named scenario','Removal date NULL; publication day differences not downtime','Cost/Kover owner-only not independent acceptance')]
    write('case_alignment.csv',[dict(requirement_id=a,available_this_package=b,missing_for_final_case=c,decision_condition=d,allowed_transfer=e) for a,b,c,d,e in alignment])
    grains={
      'inventory35.csv':'one frozen candidate ID; author fields plus owner classification, not a city score',
      'experiment_queue.csv':'one finite follow-up group, three selected tests only; all35 retained',
      'network_change_degrees.csv':'one comparison degree, not a policy ordering',
      'feature_admission.csv':'one feature mechanism/coverage/admission policy; no predictive estimate',
      'case_alignment.csv':'one case deliverable and exact gap',
      'retiming_boundaries.csv':'M x T scenario; six operating dates per feasible profile',
      'return_deadlines.csv':'M x T x allowed SOUTH return slip, minutes',
      'dated_products.csv':'profile x initial departure7/11Dec x booked7/10/14nights; two endpoint journeys/four seat segments if pass',
      'return_advance_boundaries.csv':'T x net arrival slack; one complete chain of four hypothetical legs',
      'advance_limits.csv':'chain deadline case x allowed earlier start; minutes, not legal crew duty',
      'bookability_tolerance.csv':'policy x property product request; alternatives overlap',
      'tolerance_summary.csv':'one maximum booked-night-extension policy; deduplicated12date/stay combinations',
      'monetary_difference_terms.csv':'test x named baseline x incremental money term; all real RUB values NULL',
      'capacity_conditioned_thresholds.csv':'one declared nominal100/local80/fare8000/expense500 mechanical counterexample',
      'fixture_itinerary.csv':'one directed endpoint sale in a mechanical fixture; one fare, ordered physical legs',
      'fixture_capacity_allocation.csv':'one fixture x physical leg; sum local and new seat allocation',
      'physical_legs.csv':'one hypothetical scenario x date x directed physical flight; not performed service'
    }
    tables=[]
    for p in sorted(ROOT.rglob('*.csv')):
        rel=str(p.relative_to(ROOT))
        if rel.startswith('inputs/') or p.name=='table_dictionary.csv':continue
        rows=list(csv.DictReader(p.open()))
        tables.append(dict(path=rel,grain=grains[p.name],rows=len(rows),columns=';'.join(rows[0]) if rows else '',currency='RUB only where specified',price_basis='UNKNOWN for real money; mechanical fare not market quote',tax_basis='UNKNOWN for actual money',value_status='SCENARIO/DERIVED or explicit UNKNOWN; see row',acceptance='OWNER_SELF_CHECK_ONLY; no independent/source/market/operating upgrade'))
    write('table_dictionary.csv',tables)
    findings=[
      dict(finding_id='HF-F01',candidate_id='C01',status='CONDITIONAL_BOUNDARY_SELF_CHECKED',finding='Same-north-wave feasibility requires2*M+T<=180; M60/T45 has x=y120 and returns15min before frozen sync',numeric_unit='minutes per operating date',source='inputs/experiment/scenario_programs.json',result='runs/hf01/retiming_boundaries.csv',unknown='Actual no-new-base baseline/MCT/turn/slots/tail/crew/local-margin/K(q)'),
      dict(finding_id='HF-F02',candidate_id='C07',status='CONDITIONAL_BOUNDARY_SELF_CHECKED',finding='Preserving reference return requires310/355/400min earlier start for turn30/45/60; full closure is not actual availability',numeric_unit='minutes per complete four-leg rotation',source='inputs/experiment/runs/c26661067277af20/physical_legs.csv',result='runs/hf07/return_advance_boundaries.csv',unknown='RW block/donor/actual earlier start/next assignment/base sales/complete cost'),
      dict(finding_id='HF-F03',candidate_id='C14',status='LIMITED_CALENDAR_EFFECT_SELF_CHECKED',finding='Max extra booked nights0/1/2/3 gives6/7/9/11 of12distinct date/stay matches;1combination/two property rows after capture UNKNOWN',numeric_unit='date/stay combinations, not passengers or sale probability',source='inputs/experiment/inputs/alternative_fa39de4/normalized/dated_flights.csv',result='runs/hf14/tolerance_summary.csv',unknown='Hotel admission/timezone/inventory/billed days/transfer/airline inventory/fare/rights/customer willingness'),
      dict(finding_id='HF-F04',candidate_id='C01;C07',status='MECHANICAL_COUNTEREXAMPLE',finding='Remaining20seats at scenario margin7500 can supply at most300000RUB over two directions; K500000 needs34/direction and fails preserved80seat allocation',numeric_unit='RUB per declared pair of directional opportunities',source='test_contract.json; explicit mechanical fixture',result='runs/economics/capacity_conditioned_thresholds.csv',unknown='Actual K(q), fares, other-product allocations and paid demand; no financial acceptance'),
      dict(finding_id='HF-F05',candidate_id='ALL35',status='READ_AND_CLASSIFIED',finding='All35retained with original author/status/ancestor; three tests selected, no city ranking or global mixed/budget run',numeric_unit='candidate specifications',source='inputs/hypotheses/candidates.csv',result='inventory35.csv;experiment_queue.csv',unknown='Other32main unresolved parameters explicitly named; no outcome inferred from not testing'),
      dict(finding_id='HF-H01',candidate_id='SOURCE_CONTEXT',status='INHERITED_HOLD_NOT_REPAIRED_HERE',finding='Review944b16ac holds129SVXpublication rows; no new accepted operating calendar uses them',numeric_unit='source-version lineage rows',source='inputs/source_join_review/report.md',result='source_manifest.json',unknown='Original source-registry correction outside this scope'),
      dict(finding_id='HF-H02',candidate_id='FINAL_CASE',status='OPEN_DECISION',finding='Small pilots do not satisfy8-12route final network; real full money/market/fleet and2028launch remain UNKNOWN',numeric_unit='final joint network',source='inputs/case_requirements.md',result='case_alignment.csv;network_change_degrees.csv',unknown='Common dated allocation/full budget/final objective and team strategic choice')]
    js('findings.json',dict(run_id=receipt['run_id'],classification='AGENT_PROPOSAL',independent_review='PENDING',findings=findings))
    handoff=dict(package_id='hypothesis-frontier-20261110-v1',prepared_base='f1774e1f66a9483fb618ca6003abd9dc4d8563e1',
                 completed_at_utc=datetime.now(timezone.utc).isoformat(),first_package_deadline_msk='2026-11-10T08:00:00+03:00',global_stop_msk='2026-11-10T10:00:00+03:00',
                 author='Sol 6.1 xhigh; hypothesis_frontier',run_id=receipt['run_id'],input_set_id='frontier-frozen-001',source_manifest_sha256=sha(ROOT/'source_manifest.json'),
                 source_commit='6ed8788882e7b4d07044b4f6e686ff71eadd8ac5',
                 artifacts=['findings.md','findings.json','inventory35.csv','inventory35.md','experiment_queue.csv','network_change_degrees.csv','feature_admission.csv','case_alignment.csv','table_dictionary.csv','runs/hf01','runs/hf07','runs/hf14','runs/economics','self_checks.json','reproduce.md','source_manifest.json','output_manifest.json'],
                 delivered=dict(specifications_read=35,classified=35,selected_tests=3,executed_tests=['HF01','HF07','HF14'],self_checks_passed=checks['pass_count'],negative_and_unknown_rows='All saved; no selection/deletion by outcome'),
                 owner_acceptance=['EXACT_GIT_BYTES_VERIFIED','ALL35_CLASSIFIED','SCENARIO_CALENDAR_ARITHMETIC_CHECKED','SCENARIO_RESOURCE_CONSERVATION_CHECKED','MECHANICAL_ONE_FARE_EACH_LEG_CHECKED','DETERMINISTIC_OWN_REPLAY_MATCHED'],
                 independent_review='PENDING; self-check is not independent/source/market acceptance',
                 outside_scope=['New primary raw/source acquisition or source acceptance','Observed endpoint OD, realised fares and sales','Actual free tail, crew/MRO/dispatch/slots and donor','Actual full P&L/cash and launch acceptance','City scoring/weights/team decisions','Active mixed D+previous and general resource/accounting envelope','Final8-12route jointly accepted network and unconditional2028roadmap','Changes to frozen originals, other folders, main report, Site/dashboard or infrastructure'],
                 useful_for_passport=['Conditional product/timing sensitivity HF01/HF07/HF14 after independent review','Complete improvement queue and change degrees incl KEEP','Named gates and reasons not to scale a pilot into final8-12routes'],
                 suggested_independent_review_scope=[
                     'Read exact pinned sources/author baselines; do not execute foreign live versions or promote129heldSVXrows',
                     'Repeat C01 joint inequalities and maximum x/minimum y: M60/T45 x=y120, waits60/75, SOUTH345min; prove M90 infeasible',
                     'Repeat all C07 UTC/local dates and delta270+3*T-50; one minute less required advance fails active deadline; actual donor still UNKNOWN',
                     'Deduplicate C14 property copies and policy alternatives:6/7/9/11distinct matches; checkout25Dec remains beyond capture; no physical/nonstop admission from endpoint rule',
                     'Check no bed-day*nights, no A4 revenue assigned to RW, no free base legs or fixed-cost saving from no-value-loss data',
                     'Check money/resource definitions, shared-seat counterexamples and real full money NULL; no global mixed/budget conclusions'],
                 publication=dict(remote='origin',branch='research/night-hypothesis-frontier-20261110',remote_head_resolution='git ls-remote --heads origin research/night-hypothesis-frontier-20261110',exact_remote_sha_delivery='Final message after push and remote-head verification; embedding own containing commit SHA would be circular',force=False,merge=False,rebase=False,pull_request=False,push_does_not_raise_acceptance=True))
    js('handoff.json',handoff)
    files=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='output_manifest.json']
    js('output_manifest.json',dict(package_id=handoff['package_id'],run_id=receipt['run_id'],files=files,bytes=sum(r['bytes'] for r in files),acceptance='MANIFEST_OF_OWNER_PACKAGE_ONLY'))
    print(json.dumps(dict(files=len(files),bytes=sum(r['bytes'] for r in files),run_id=receipt['run_id'])))

if __name__=='__main__':main()
