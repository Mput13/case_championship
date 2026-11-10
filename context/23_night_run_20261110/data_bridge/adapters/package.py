#!/usr/bin/env python3
"""Create review handoff, semantic findings and bounded package manifests."""
import csv
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from build import OUT, ROOT, PINS, AUTHORS


def read(name):
    with (OUT/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def write(name,rr,columns=None):
    with (OUT/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=columns or list(dict.fromkeys(k for r in rr for k in r)),lineterminator='\n')
        w.writeheader();w.writerows(rr)


def dump(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    verification=json.loads((OUT/'verification.json').read_text())
    raw=json.loads((OUT/'checks/raw_verification.json').read_text())
    evidence_checks=verification['checks']+raw['checks']
    if verification['failed'] or raw['failed']:raise ValueError('Do not mark a failing package ready')
    unit_rows=[
        ('endpoint_journey','Одна поездка от конечного O до конечного D в одном направлении','1 поездка с пересадкой использует2 кресло-сегмента','Не уникальный человек за год; обратный путь — ещё одна поездка'),
        ('passenger_segment','Одна перевозка пассажира на одном плече','Σ поездки × число плеч','Не конечный OD; возможны пересадки'),
        ('seat_segment','Кресло одного датированного рейса','Номинальные кресла SCENARIO, не сертифицированная доступность','Нельзя переносить неиспользованное кресло на другую дату'),
        ('net_whole_journey_fare_RUB','Сценарная выручка за всю поездку','sold_journeys × effective_fare один раз','Фактические налоги/расчёты/возвраты UNKNOWN'),
        ('annual_route_flow','Поток на линии в обоих направлениях за модельный год','Модельные/калибровочные сегменты','/52/2 не превращает его в наблюдённый конечный OD'),
        ('million_RUB_year','Округлённый миллион RUB за модельный год','×1000000 для хранения в RUB','Не недельный net contribution; налоговая база/точный год не установлены'),
        ('contribution_RUB_week','Недельный вклад до базы/парка/альтернативы','incremental_revenue-flight_cost-new_pax_variable+saved_old_pax_variable','Не полная прибыль и не полученная оплата'),
        ('block_minute','Блок-время в минутах','Σ/60 даёт блок-часы','Сценарный block не подтверждает dispatch/crew/слоты'),
        ('restriction_post_day','День с классифицированным сообщением','Прокси в авторском скоринге','Не downtime и не вероятность отмены'),
        ('weather_sample_hour','Архивное наблюдение на станции','Температура/ветер из ISD-Lite; пропуски явно','Пороговые counts не потерянные часы; мороз и ветер пересекаются'),
        ('weather_threshold_day_proxy','Исследовательский эквивалент дней из пороговых выборок','Авторский bad_weather_days','Не фактические дни закрытия аэропорта'),
        ('regional_tourism_persons','Лица в региональных коллективных средствах размещения','Нативные тысячи человек сохраняются','Не уникальные туристы города, OD KVX–MRV или оплаченные пассажиры RW'),
        ('wage_RUB_month','Номинальная начисленная зарплата сотрудников учтённых организаций','Среднемесячно; январь–декабрь2024','Не доход домохозяйства; охват малых фирм/населения неполный'),
        ('ND_unit','Единица не определена издателем','NULL с причиной;14/42 региональных контекстных строк удержаны','Название индикатора не даёт права угадать единицу'),
        ('source_snapshot','Версия данных и время извлечения','SHA256, Git commit, raw receipt','Одинаковый hash не подтверждает истинность исходного измерения'),
    ]
    write('units_dictionary.csv',[dict(unit_id=k,definition=d,conversion=c,limit=l) for k,d,c,l in unit_rows])
    mappings=[
        ('nastya:screening','criteria.json values[IATA][criterion]','parameter_registry','value/status/unit/default_weight','Preserve v=NULL, source explanation and author default weight','Screening proxy only'),
        ('nastya:network','network_routes.csv scenario/variant/from/to','route_program','origin/destination/frequency/annual segments','No dated physical leg invented; MOW left as group','No seat-ledger equivalence'),
        ('nastya:network','network_summary.csv','evaluation_summary','segments/journeys/revenue/contribution','millionRUB×1e6; keep annual horizon and rounding','No common weekly price/tax/resource basis'),
        ('ciri:conditional16','markets.csv pair demand_base/cautious','market_pool','directed OD/scenario week','Expand unordered pair into two directions with same author scenario bound','Alternative networks use same pool but are mutually exclusive'),
        ('ciri:conditional16','sales.csv flight_ids','itinerary / itinerary_leg / capacity_allocation','sold_journeys/whole fare/dated flight FK','Split ; IDs; one fare per itinerary, one seat per leg','All fractional scenario, no observed sales'),
        ('ciri:conditional16','flights.csv + capacity.csv','physical_leg / money_ledger','network/flight/scenario cost','Join network+id, then scenario+priority; physical cost once per flight','Published/source fare or schedule is not observed dispatch'),
        ('ciri:conditional16','resources.csv + comparison.csv','resource_ledger / evaluation_summary','week/block/active/reserve/contribution','Keep unknown fleet/opportunity/full_budget NULL','Not complete strategy budget'),
        ('hypotheses:register35','candidates.csv','candidate_register / product_path_template','candidate/path/purpose/status','Preserve author path semantics: a loop is not one sold passenger itinerary','No inferred demand, fare, fleet or financial winner'),
        ('hypotheses:experiment3','runs/c26661067277af20/physical_legs.csv','physical_leg','leg/variant/UTC/nominal seats','Separate model_id and run/scenario boundary','Scenario physical requirements, not observed capacity'),
        ('hypotheses:experiment3','cost_resource/6cf441ef38e2c6c5/conditional_thresholds_with_product_keys.csv','hypothesis_thresholds','cohort gap/fare/journeys/boardings','Preserve cohort, not rename weekly/annual forecast','Actual funding gap/fare/residual seats/demand unknown'),
        ('ciri_stage1:screening','scores_samara_excluded_min500_base.csv','ciri_stage1_scores','IATA/score/interval/rank','Different branch/rules; original score copied with origin metadata','Not automatic replacement of Nastya score or Ciri economics'),
        ('core','airport_keys.csv','entity_resolution / candidate_airport_link','OA id/version/IANA','Unique IATA lookup, preserve quarantine; downstream weather by OA id','No name-only/city-only joins'),
        ('core+alternative','airport_keys + join_airport_station_mapping + weather_monthly_2024','airport_weather_month','OA:id → station_id → month','Check IATA/ICAO; preserve station and sample denominators','Historical point context, no cancellation probability'),
        ('core','gateway_region_crosswalk + gateway_region_context_2024','candidate_regional_tourism','airport → region → indicator/year','Use seven reviewed mappings; ND rows held; repeated context not additive','No municipality/catchment/OD inference'),
    ]
    write('adapters/mapping.csv',[dict(model_id=m,source=s,target=t,fields=f,transform=x,compatibility=c) for m,s,t,f,x,c in mappings])
    findings=[
        ('DB01','LIMIT','INCOMPATIBLE_GRAIN','nastya:network ↔ ciri:conditional16','Annual bidirectional segment-model flow cannot be equated to directed weekly endpoint OD; MOW grouping differs from airport-level ZIA.', 'compatibility.csv; line_flow_context.csv','Supply one explicit common OD input_set, period, price/tax basis and resource ceiling before numerical winner comparison.'),
        ('DB02','INFO','JOIN_CHECKED','ciri:conditional16','860 itineraries,1092 leg allocations and314 physical scenario flights reconcile; one whole fare per journey, market caps within each strategy and per-flight costs preserved.', 'verification.json; checks/ciri_capacity.csv; checks/ciri_market_pool.csv; checks/ciri_economics.csv','Independent reviewer rechecks pinned sales/capacity source rows; no SOURCE_SUPPORTED/final-demand claim.'),
        ('DB03','LIMIT','CONDITIONAL_BUDGET_ONLY','ciri/nastya economics','Unknown base/fleet/opportunity/launch/support/exit/working capital prevents full profit comparison. Blank full_budget is NULL.', 'evaluation_summary.csv; resource_ledger.csv','Team must define full budget and incumbent alternative; avoid revenue+margin opportunity doublecount.'),
        ('DB04','LIMIT','QUARANTINE_PRESERVED','identity/timezone joins','11 directory keys remain held; MOW is a separate group. Source model results are retained even when bridge identity/clock admission is held.', 'entity_resolution.csv; quarantine_preserved.csv','Resolve exact coordinate/timezone conflict in a separate input version; no silent override.'),
        ('DB05','INFO','EXTRACTION_CHECKED_SELECTED','selected raw','9 held raw hashes checked;2stations×12months×7fields;42regional tourism rows;4044municipal numeric cells match. Municipal data are not mapped to airport catchments.', 'checks/raw_verification.json','Raw/extraction acceptance applies to stated cells only; publisher accuracy and unseen stations remain outside scope.'),
        ('DB06','LIMIT','REGIONAL_CONTEXT_ONLY','tourism','42source observations expand to624 incidence rows over candidates;14source observations have unknown units and remain held. Repeated regional values are not additive demand.', 'candidate_regional_tourism.csv; coverage.csv','Use unique(region,indicator,year) for regional reporting; require product-specific OD/purpose/date linkage for passenger inference.'),
        ('DB07','INFO','FEATURE_SENSITIVITY_ONLY','Nastya weather/wage','Weather or wage removal keeps each frozen top3 set at0km and500km, with score changes. No target labels, holdout or dispatch model.', 'feature_effects.csv; checks/feature_score_deltas.csv','Do not call stability predictive gain; new station join has no numerical dependency in author model.'),
        ('DB08','LIMIT','SPARSE_CORPORATE_EVIDENCE','46SIBUR sites','Postal/map sites do not identify airport catchment, worker flows or procurement. All site→airport travel joins held; no city zeros added.', 'corporate_join_hold.csv','Select a concrete site/passenger product and obtain access geography plus travel purpose/volume before use.'),
        ('DB09','INFO','VERSION_BOUNDARY','Ciri stage1/economics; historical critic','6ec84a7d is a separate stage1 branch; it does not contain conditional16 economic output. Historical critic findings retain their reviewed SHA; they are not new allegations against2f03b693.', 'source_manifest.csv; historical_findings.csv; compatibility.csv','Review each finding against its actual input version; do not silently upgrade frozen economic inputs.'),
        ('DB10','LIMIT','NOT_RUN_NO_LABELS','new weather/tourism/corporate features','New joins provide coverage and source compatibility. No labels exist here for incremental demand/sales/cancellation prediction.', 'feature_fitness.csv; model_input_usage.csv','A dated holdout target and publication vintage are required before claiming predictive edge.'),
    ]
    write('findings.csv',[dict(finding_id=i,severity=s,status=t,scope=g,finding=f,evidence=e,next_action=n) for i,s,t,g,f,e,n in findings])
    decisions=[
        dict(decision_id='D01',status='USER_CONSTRAINT',subject='Frozen originals and dashboard/public Site',value='Unchanged; write only data_bridge',evidence='../contract.md'),
        dict(decision_id='D02',status='AGENT_PROPOSAL',subject='Common table adapter',value='Use normalized schema and explicit compatibility/HOLD; no score/financial winner',evidence='adapters/mapping.csv'),
        dict(decision_id='D03',status='OPEN_DECISION',subject='New feature inclusion/weights',value='Not approved; diagnostic on/off test only',evidence='feature_effects.csv; feature_fitness.csv'),
        dict(decision_id='D04',status='AUTHOR_PROPOSAL',subject='Ciri common demand/fare and4active+1reserve',value='Source scenario, not team policy or observed availability',evidence='93fa5cf4; parameter_registry.csv'),
        dict(decision_id='D05',status='AUTHOR_PROPOSAL',subject='Nastya scoring weights and500km filter',value='Retained as frozen author method; no policy inference',evidence='2f03b693 criteria.json; feature_effects.csv'),
        dict(decision_id='D06',status='OPEN_DECISION',subject='Full budget/resource basis of common comparison',value='Needs explicitly agreed scope/costs; NULL is not0',evidence='compatibility.csv; evaluation_summary.csv'),
    ]
    write('normalized/decision_ledger.csv',decisions)
    dictionary=read('field_dictionary.csv')
    for col in decisions[0]:
        dictionary.append(dict(table='normalized/decision_ledger.csv',field=col,value_class='DERIVED',
                               unit='identifier/text',null_rule='Empty business cell is NULL with reason',
                               interpretation='Explicit decision provenance; no team approval inferred',
                               value_class_rule='Metadata classification; use row.status to distinguish authorization/proposal/open decision'))
    write('field_dictionary.csv',dictionary)
    requests=[
        ('R01','COMMON_OD','Directed endpoint OD with period/purpose and source coverage','A concrete common period and observation/calibration; do not use airport totals or line segments as OD','Enables actual common numeric comparison'),
        ('R02','NET_FARE','Whole one-way net settlement fare','Taxes/fees/commissions/refunds/ancillaries and tax basis; same for incumbent foregone revenue','Comparable contribution and demand-price stress'),
        ('R03','BUDGET','Base/crew/MRO/reserve/startup/working capital/support/exit','Known values or explicit ranges; distinguish cost from capital and resource opportunity','Full budget vs variable contribution'),
        ('R04','QUARANTINE_KEYS','Exact directory identities/timezones for held codes','Separate input_set resolving source coordinate/timezone contradictions; no guessed name join','Admit affected airport/time joins'),
        ('R05','STATION_OPERATIONS','Wind/frost/ceiling/runway data linked to operating decision','Actual aircraft/airport thresholds and event labels; station suitability and observation cadence','Test operating conditions rather than count raw archive volume'),
        ('R06','PRODUCT_LABELS','Dated actual sales/journeys/cancellation labels','Holdout cut and publication-vintage limit; baseline same information set','NOT_RUN_NO_LABELS until supplied'),
        ('R07','CORPORATE_ACCESS','One selected site and travel program','Reviewed site/entrance→ground-access→airport keys, traveler purpose/OD, procurement/volume','Avoid treating rare industrial anecdotes as broad city demand'),
        ('R08','TOURISM_PRODUCT','KVX/MRV or other explicit product/time window','Departure/return dates, admission/minimum stay/inventory and completed ground transfer; regional aggregates alone insufficient','Connect tourism context to sellable passenger product'),
        ('R09','CALENDAR_GATES','Actual operator/nonstop/seat and dated return resource','Do not invent arrival day/MCT/one tail/crew/slots from clock fragments','Operational admission separate from source schedule publication'),
    ]
    write('requests.csv',[dict(request_id=i,dataset=d,needed=n,admission_condition=a,decision_effect=e,status='OPEN_NO_NEW_MASS_COLLECTION') for i,d,n,a,e in requests])
    examples={}
    its=read('normalized/itinerary.csv');it=next(r for r in its if r['leg_count']=='2')
    examples['two_leg_scenario_itinerary']=it
    examples['two_leg_seat_allocation']=[r for r in read('normalized/itinerary_leg.csv') if r['itinerary_id']==it['itinerary_id']]
    examples['one_whole_fare_ledger']=[r for r in read('normalized/money_ledger.csv') if r['itinerary_id']==it['itinerary_id']]
    examples['MOW_group'] = next(r for r in read('normalized/entity_resolution.csv') if r['entity_code']=='MOW')
    examples['TOF_hold'] = next(r for r in read('normalized/entity_resolution.csv') if r['entity_code']=='TOF')
    examples['published_departure_with_unknown_arrival_day']=next(r for r in read('normalized/published_dated_evidence.csv') if not r['arrival_utc'])
    examples['weather_station_month']=next(r for r in read('normalized/airport_weather_month.csv') if r['entity_code']=='UFA')
    examples['tourism_unit_hold']=next(r for r in read('normalized/candidate_regional_tourism.csv') if r['numeric_use_admitted']=='False')
    examples['overlapping_observation_periods']=next(r for r in read('checks/observation_period_overlap.csv') if r['overlap']=='True')
    dump('row_examples.json',examples)
    # Compact coverage summary, counts are source-incidence coverage not passenger volumes.
    summary=[]
    cv=read('coverage.csv')
    for model,dataset in sorted({(r['model_id'],r['dataset']) for r in cv}):
        rr=[r for r in cv if r['model_id']==model and r['dataset']==dataset]
        cc=defaultdict(list)
        for r in rr:cc[r['candidate_id']].append(r)
        summary.append(dict(model_id=model,dataset=dataset,candidates=len(cc),
                            candidates_with_admitted_context=sum(any(int(r['admitted_rows'])>0 for r in rs) for rs in cc.values()),
                            candidate_endpoint_incidences=sum(bool(r['entity_code']) for r in rr),
                            admitted_endpoint_incidences=sum(int(r['admitted_rows'])>0 for r in rr),
                            unit='coverage counts; not demand/passengers'))
    write('coverage_summary.csv',summary)
    meta=json.loads((OUT/'input_manifest.json').read_text())
    meta['supplemental_input_manifests']=['checks/raw_input_manifest.json']
    dump('input_manifest.json',meta)
    handoff=dict(package_id='NIGHT_DATA_BRIDGE_20261110_V1',ready_for_review=True,
                 role='research data bridge / Sol6.1xhigh',worktree=str(ROOT),write_scope=str(OUT.relative_to(ROOT)),
                 branch='research/night-data-bridge-20261110',source_pins=PINS,source_authors=AUTHORS,
                 verification='verification.json',raw_verification='checks/raw_verification.json',
                 independent_review='NOT_RUN; coordinator assigns fresh review against immutable commit',
                 tests_passed=len(evidence_checks),tests_failed=0,
                 actually_joined=['Nastya20city scores +128undated routes to canonical directory, with HOLDs',
                    'Ciri conditional16:72pair pools×2directions×2scenarios;860itineraries→1092legs→314physical scenario flights and628scenario flight cost rows',
                    '35research candidates→81author path templates;62scenario experiment legs kept distinct',
                    '14Ciri stage1 score rows from separate branch; no economic version upgrade',
                    '36admitted airport/station contexts×12months=432rows; candidate coverage explicit',
                    '7reviewed gateway-region mappings;42regional tourism cells,28unit-known,14held;624candidate incidence rows',
                    '24period-specific reported market observations;1428modeled bidirectional line-flow pairs kept as context'],
                 acceptance={'raw':'RAW_HASH_VERIFIED on9selected held artifacts',
                             'extraction':'EXTRACTION_CHECKED on168weather cells/42tourism rows/4044municipal numeric cells only',
                             'joins':'JOIN_CHECKED_WITH_EXPLICIT_HOLDS; no quarantine bypass',
                             'scenario_accounting':'CONSERVATION_PASS for adapted Ciri outputs; Nastya aggregate rounding identity passes',
                             'author_replay':'NOT_RUN_FULL_AUTHOR_MODEL; screening formula only matched within stored rounding',
                             'source_supported':'NOT_ASSERTED_BROADLY; primary publication truth not audited by hash',
                             'economics':'CONDITIONAL_OUTPUT_ACCOUNTING_ONLY; no full budget/profit/market acceptance'},
                 remaining_incompatible=['City screening ≠ route network ≠ passenger product',
                     'Annual bidirectional modeled line segments ≠ observed directed final OD/week',
                     'MOW group ≠ ZIA physical airport; held source keys not silently upgraded',
                     'Rounded millionRUB/year ≠ netRUB/week without common tax/price/horizon/resource assumptions',
                     'Regional annual tourism/site maps/station weather ≠ product demand or predictive edge'],
                 files_to_review=['findings.md','findings.csv','adapters/mapping.csv','compatibility.csv','model_input_usage.csv',
                                  'feature_fitness.csv','feature_effects.csv','join_manifest.csv','row_examples.json'],
                 reproduce=['python3 context/23_night_run_20261110/data_bridge/adapters/build.py',
                            'python3 context/23_night_run_20261110/data_bridge/adapters/check_raw.py',
                            'python3 context/23_night_run_20261110/data_bridge/adapters/package.py',
                            'python3 context/23_night_run_20261110/data_bridge/adapters/verify.py'],
                 outside_scope=['New sources/paid providers','Dashboard or public Site changes','Actual OD/sales/fleet evidence',
                                'Full model replays/repairs assigned to other role','Statistical feature usefulness','Financial winner'],
                 git_handoff='Exact published commit reported in final handoff; this JSON cannot contain its own commit hash.')
    dump('handoff.json',handoff)
    print(json.dumps(dict(ready_for_review=True,tests=len(evidence_checks),joined_tables=len(list((OUT/'normalized').glob('*.csv')))),ensure_ascii=False))


if __name__=='__main__':main()
