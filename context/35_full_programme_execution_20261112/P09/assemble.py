"""Публикационные таблицы P09; ни один overview не выдаётся за canonical float bytes."""
import copy,csv,gzip,hashlib,json,re,subprocess
from pathlib import Path
from collections import Counter,defaultdict
import programme_builder as b
import evaluate_programmes as e

ROOT=b.ROOT
def read_csv(p):return list(csv.DictReader(p.open()))
def readj(p):return json.loads(p.read_text())

def merge_mrv():
    p=ROOT/'late_inputs/variants/MRV/research_v1';manifest=hashlib.sha256((p/'output_manifest.json').read_bytes()).hexdigest()
    for filename,target,key in [('programme_candidates.json','normalized_candidates.json','programmes'),('hypotheses.json','normalized_hypotheses.json','hypotheses')]:
        old=readj(ROOT/target);old=[r for r in old if r['city']!='MRV'];raw=readj(p/filename)
        for i,r in enumerate(raw[key]):
            ident=r.get('programme_id',r.get('hypothesis_id',r.get('id','MRV:'+str(i))))
            old.append(dict(id=ident,city='MRV',source_path='context/35_full_programme_execution_20261112/variants/MRV/research_v1/'+filename,source_file_sha256=hashlib.sha256((p/filename).read_bytes()).hexdigest(),source_row_id=ident,source_row_index=i,source_row_sha256=b.digest(r),manifest_sha256=manifest,coordinator_scope_accepted=True,commit='6a6326c2dcfe32e47ec25621bda0d15fcfe48ae1',raw=r))
        # Existing payload bytes were proven identical to exact root; acceptance is research scope only.
        for r in old:r['coordinator_scope_accepted']=True;r['admission_scope']='SOURCE_RESEARCH_ONLY';r['commit']='6a6326c2dcfe32e47ec25621bda0d15fcfe48ae1'
        b.dump(ROOT/target,old)

def dispositions(ps,results):
    byid={p['programme_id']:p for p in ps};evaluated={x['programme_id'] for x in results};rows=[]
    for c in readj(ROOT/'normalized_candidates.json'):
        dom,foreign=e.raw_pairs(c['raw']);auth='AUTH_'+c['id'];city=c['city']
        programmes=[x for x in [auth,city+'_RADIAL',city+'_HUB',city+'_HYBRID',city+'_BANK9',city+'_BANK_HYBRID'] if x in evaluated]
        if auth in evaluated:
            # none contains no new working tail and cannot establish an authored path's economics.
            ss={x['status'] for x in results if x['programme_id']==auth and x['delivery']!='none'}
            status='ОЦЕНЕНА_УСЛОВНАЯ_ПРИВЯЗКА_АВТОРСКОГО_PATH' if 'CONDITIONAL_P05_P06_CALCULATED'in ss else 'КОНКРЕТНЫЙ_КАЛЕНДАРЬ_НЕВЫПОЛНИМ; АВТОРСКАЯ_ЭКОНОМИКА_NOT_RUN'
            scope='Сохранены исходные ordered paths/weekdays; ресурс и будущий KEEP заданы P09. Это не полный реальный московский бизнес.'
            open_='Реальные ownsales, доступ/слоты, crew/MRO, полный бюджет; при INFEASIBLE исправить конкретный календарь, не отбрасывать город.'
        elif foreign:
            status='УСЛОВНА_МЕЖДУНАРОДНАЯ_ИЛИ_СМЕШАННАЯ_ВЕТВЬ_OPEN'
            scope='Местный P05/P06 screen и общие городские конструкции'+('; international/thresholds_monthly.csv дляI03/I06' if city in ['SVX','KUF'] else '')
            open_='Индивидуальные dated legs/международный OD/SPA/допуски/иностранные ставки; domestic candidate не экономически отклонён.'
        elif dom:
            status='ЧАСТИЧНО_ОБЩИЙ_SCREEN_АВТОРСКИЙ_STAGE_B_OPEN'
            scope='Общий P05/P06 oneRT screen и отдельные полные городские конструкции. Оригинальные частоты/цепочки автора целиком НЕ проиграны.'
            open_='Индивидуальная привязка авторского календаря, before/after/KEEP и требуемых ресурсов к ядру; не считать выполненной из-за похожего города.'
        else:
            status='УСЛОВНА_ПАРТНЕРСКАЯ_KEEP_ИЛИ_НЕПРИВЯЗАННЫЙ_РЕЦЕПТ_OPEN'
            scope='Источник сохранён; общая KEEP policy посчитана. Нет основания объявить авторскую ветвь экономически отвергнутой.'
            open_='Точный исполнимый physical/commercial product или partner inventory/договор и outcome.'
        rows.append(dict(candidate_id=c['id'],city=city,status=status,evaluation_scope=scope,evaluated_constructs=programmes,domestic_pairs=dom,foreign_or_unmapped_pairs=foreign,source_row_id=c['source_row_id'],source_row_sha256=c['source_row_sha256'],manifest_sha256=c['manifest_sha256'],source_commit=c['commit'],reason='Различаем полный авторский рецепт, диагностический пример и P09 конструкцию; низкийscore/500км/конкурент не критерий отказа.',revisit_condition=open_,economic_rejection=False,source_stage_A='COMPLETE_RESEARCH_ONLY'))
    b.csvwrite(ROOT/'candidate_dispositions.csv',rows)
    hrows=[]
    for h in readj(ROOT/'normalized_hypotheses.json'):
        r=h['raw'];hrows.append(dict(hypothesis_id=h['id'],city=h['city'],source_outcome=r.get('outcome',r.get('status','UNKNOWN')),P09_outcome='ЧАСТИЧНО_ОЦЕНЕН_МЕХАНИЗМ_В_ОБЩИХ_КОНСТРУКЦИЯХ; индивидуальноезакрытиеOPEN',programme_refs=r.get('programme_ids',[]),source_row_sha256=h['source_row_sha256'],manifest_sha256=h['manifest_sha256'],revisit_condition=r.get('revisit_condition','Принятый индивидуальный P05/P06 тест или доказательный критерий отказа'),prior_verdict_preserved=True))
    b.csvwrite(ROOT/'hypothesis_dispositions.csv',hrows)
    legacy=[]
    for h in readj(ROOT/'legacy_hypotheses.json'):
        cid=h['candidate_id'];matched=[x['id'] for x in readj(ROOT/'normalized_hypotheses.json') if cid in json.dumps(x['raw'],ensure_ascii=False)]
        authored=[x['id'] for x in readj(ROOT/'normalized_candidates.json') if cid in json.dumps(x['raw'],ensure_ascii=False)]
        legacy.append(dict(candidate_id=cid,title=h['title'],historical_outcome=h['author_evaluation_status'],historical_scope=h['checked_result_and_scope'],ancestor_ids=h['ancestor_ids'],successor_hypotheses=matched,successor_programmes=authored,P09_outcome='ПРОИСХОЖДЕНИЕ_СОХРАНЕНО; индивидуальныйфинальныйисходOPEN',reason='Новый общий screen не переписывает frozen старую оценку и не доказывает все авторские рецепты',revisit_condition='Принятый индивидуальный тест с тем же KEEP/ресурсом или доказательный критерий объединения/отказа'))
    b.csvwrite(ROOT/'legacy_hypothesis_mapping.csv',legacy)

def context_validation():
    p=ROOT/'late_inputs/P01_MONTHLY/airport_pair_segment_observations.csv';rows=[]
    for x in read_csv(p):
        a,z=x['origin_code'],x['destination_code'];prior=None
        if a in b.D.nodes and z in b.D.nodes:
            prior=b.D.prior(a,z)[0]
        rows.append(dict(observation_id=x['observation_id'],origin=a,destination=z,observed_value=x['value'],unit=x['unit'],period_start=x['period_start'],period_end=x['period_end'],direction_basis=x['direction_basis'],overlap_group_id=x['overlap_group_id'],source_url=x['source_url'],source_row_sha256=b.digest(x),P05_annual_bidirectional_OD_prior=prior,comparability='РАЗНАЯ_СОВОКУПНОСТЬ; НЕ_CALIBRATION_PASS_OR_FAIL',use='Проверить масштаб по coupon/segment/OD bridge; не складывать overlapgroups, не делить UNKNOWN direction на2.',correction_applied=False))
    b.csvwrite(ROOT/'historical_validation_context.csv',rows)
    b.dump(ROOT/'metric_adapter_status.json',dict(P10_pin='6a6326c2dcfe32e47ec25621bda0d15fcfe48ae1',P10_manifest='5bf0be3d7e0c5a9796329e4784ebc816cb4228f3f97314d40c0e941425129426',status='UNKNOWN_COMPATIBLE_REPORTING_ADAPTER',canonical_metric_adapter=None,journeys='Конечнаяпоездка; тарифодинраз',segments='Расходкресланафизическомплече',reporting_flight_id_in_dated_template='Только предложенная scenarioidentity; не принятыйстатистическийmapping',missing=['statistical flight continuity','boarding group to reportingflight mapping','carrier vs group scope','совместимый future denominator','полный affectedcompanyKEEP'],reported_share=None,rank_number2_date=None,P01_endpoint_OD_observations=0,P01_carrier_monthly_note='36UTrows include9helicopter rows; fixedwing only27. Не использованы для подменыrouteOD.'))

def main():
    merge_mrv();ps=readj(ROOT/'programmes.json')['programmes'];byid={p['programme_id']:p for p in ps}
    rs=[readj(p) for p in sorted((ROOT/'evaluations').glob('*.json'))]
    b.csvwrite(ROOT/'scenario_results.csv',[{k:x.get(k) for k in ['programme_id','label','delivery','scenario','response','status','journeys','passenger_segments','delta_journeys','revenue_net','delta_revenue_net','known_operating_subtotal','delta_known_operating_subtotal','full_operating_result','full_delta_result','known_components_incremental_peak_diagnostic','full_incremental_peak','whole_company_peak','reported_share','unique_pairs_end2028','dispatch_ready','global_optimum','calendar_flights']} for x in rs])
    monthly=[r for x in rs for r in x.get('results_monthly',[])];b.csvwrite(ROOT/'results_monthly.csv',monthly)
    dispositions(ps,rs);context_validation()
    selected=readj(ROOT/'finalist_selection.json')['selected'];flights=[];assignments=[];resource=[];drivers=[];network=[]
    b.dump(ROOT/'fleet_calendar.json',{d:b.fleet(d) for d in ['phased','partial','delayed','none']})
    for delivery in ['phased','partial','delayed','none']:
        for pid in selected:
            c=b.build_calendar(byid[pid],delivery);tags=dict(programme_id=pid,delivery=delivery)
            flights += [dict(**tags,**f) for f in c['flights']];assignments += [dict(**tags,**a) for a in c['assignments']]
            for m in b.MONTHS:
                ff=[f for f in c['flights'] if f['departure_utc'].startswith(m)];used={a['aircraft_id'] for a in c['assignments'] if a['flight_instance_id']in {f['flight_instance_id'] for f in ff}}
                for t in c['fleet_calendar']:
                    resource.append(dict(**tags,month=m,aircraft_id=t['aircraft_id'],aircraft_variant=t['variant'],committed=t['transfer_date'][:7]<=m,transferred=t['transfer_date'][:7]<=m,entered_service=t['service_entry_date'][:7]<=m,reserve=t['reserve_role'] and t['service_entry_date'][:7]<=m,used_in_calendar=t['aircraft_id']in used,unused_but_committed=t['transfer_date'][:7]<=m and t['aircraft_id']not in used,crew_maintenance_status='UNKNOWN_CONDITIONAL_PROFILE_ONLY',tail_charge='UNKNOWN retained monthly in both P/KEEP; not0',assumption_id='P09-RESOURCE'))
                hours=sum((b.p05.utc(f['arrival_utc'])-b.p05.utc(f['departure_utc'])).total_seconds()/3600 for f in ff)
                drivers.append(dict(**tags,month=m,physical_legs=len(ff),block_hours=hours,departures=len(ff),fuel_t_base=hours*1.55+len(ff)*.2,fuel_t_cautious=hours*1.9+len(ff)*.25,aircraft_mtow_t_analogue=49.45,full_future_rate_status='UNKNOWN',assumption_ids='P09-PERFORMANCE;P09-COST'))
            for pair,n in Counter(tuple(sorted([f['origin_airport'],f['destination_airport']])) for f in c['flights'] if f['project_network'] and f['departure_utc'].startswith('2028-12')).items():network.append(dict(**tags,airport_pair='-'.join(pair),dated_physical_legs_dec2028=n,period='2028-12',status='PROPOSED_SCENARIO_NOT_PUBLISHED',source_programmes=byid[pid].get('source_programme_ids',[])))
    b.csvwrite(ROOT/'dated_flights.csv',flights);b.csvwrite(ROOT/'assignments.csv',assignments);b.csvwrite(ROOT/'resource_monthly.csv',resource);b.csvwrite(ROOT/'cost_drivers_monthly.csv',drivers);b.csvwrite(ROOT/'network_end2028.csv',network)
    thresholds=[];invest=[]
    lookup={(r['programme_id'],r['delivery'],r['scenario'],r['response']):r for r in rs}
    for r in rs:
        if r['status']!='CONDITIONAL_P05_P06_CALCULATED':continue
        H=r['delta_known_operating_subtotal'];tails=b.fleet(r['delivery']);work=[t for t in tails if t['aircraft_id'].startswith('N') and not t['reserve_role']]
        station_months=len([m for m in b.MONTHS if work and m>=min(t['service_entry_date'][:7] for t in work)])
        thresholds.append(dict(programme_id=r['programme_id'],delivery=r['delivery'],scenario=r['scenario'],response=r['response'],net_missing_operating_cost_break_even=H,extra_station_months_scenario=station_months,max_extra_station_cost_per_month=None if not station_months else H/station_months,max_total_startup_if_other_missing_zero=H,same_committed_tail_cost_delta_coefficient=0,max_same_common_tail_rate=None,full_delta_equation='H - net_missing_cost_delta + unknown_extra_revenue_delta; mutually exclusive residual terms',condition='Каждый порог отдельно при фиксированных остальных неизвестных; не одновременно допустимые бюджеты. H не прибыль.',source_help='P04 contracts, invoices, base setup/exit, residual crew/MRO beyond hourly analogue; full KEEP/coupon/SPA',assumption_ids='P09-COST;P09-MISSING;P09-KEEP'))
        if r['delivery']=='phased' and r['response']=='passive' and r['scenario'] in ['base','cautious']:
            no=lookup[r['programme_id'],'none',r['scenario'],'passive'];q=sum(1 for t in tails if t['aircraft_id'].startswith('N') for m in b.MONTHS if t['transfer_date'][:7]<=m)
            delta=r['known_operating_subtotal']-no['known_operating_subtotal']
            invest.append(dict(programme_id=r['programme_id'],scenario=r['scenario'],comparison='SEPARATE_INVESTMENT_VS_NO_ACQUISITION_NOT_MAIN_EQUAL_FLEET',delta_known_operating_components=delta,additional_committed_new_tail_months=q,max_average_operating_aircraft_use_rate_if_other_missing_zero=None if not q else delta/q,full_delta_result=None,funding=None,assumption_ids='P09-ENTRY;P09-RESOURCE;P09-MISSING',condition='Operating aircraft-use convention; no rent+depreciation duplication. Start/exit/base/interest/capex/cashlags remain functions.'))
    b.csvwrite(ROOT/'thresholds.csv',thresholds);b.csvwrite(ROOT/'investment_no_acquisition.csv',invest)
    response=[];hub=[]
    for r in rs:
        if r['status']!='CONDITIONAL_P05_P06_CALCULATED':continue
        key=r['programme_id'],r['delivery'],r['scenario'],'passive'
        if r['response']=='response10' and key in lookup:
            p=lookup[key];response.append(dict(programme_id=r['programme_id'],scenario=r['scenario'],response='P05-A13 адресный−10% incumbent residual fare',delta_journeys_vs_passive=r['delta_journeys']-p['delta_journeys'],delta_known_subtotal_vs_passive=r['delta_known_operating_subtotal']-p['delta_known_operating_subtotal'],future_competitor_capacity='UNKNOWN',response_empirically_identified=False))
        if r['programme_id'].endswith(('_HUB','_BANK9')):
            c=lookup.get((r['programme_id']+'_LOCAL_ONLY',r['delivery'],r['scenario'],r['response']))
            if c and c['status']=='CONDITIONAL_P05_P06_CALCULATED':hub.append(dict(programme_id=r['programme_id'],delivery=r['delivery'],scenario=r['scenario'],response=r['response'],connection_only_delta_journeys=r['journeys']-c['journeys'],connection_only_delta_revenue=r['revenue_net']-c['revenue_net'],connection_only_delta_known_subtotal=r['known_operating_subtotal']-c['known_operating_subtotal'],control='SAME_FLIGHTS_NO_TRANSFER_PRODUCTS',identified_causal_effect=False))
    b.csvwrite(ROOT/'sensitivity_response.csv',response);b.csvwrite(ROOT/'connection_value_controls.csv',hub)
    b.csvwrite(ROOT/'robust_frontier.csv',readj(ROOT/'finalist_selection.json')['frontier'])
    assumptions=b.ASSUMPTIONS+b.P05_ASSUMPTIONS
    for r in b.COSTROWS:
        assumptions.append(b.assumption(r['assumption_id'],r['value'] or {'base':r['base_point'],'cautious':r['cautious_point']},r['unit'],r['source_id']+' '+r['source_url']+' '+r['range_basis'],r['coverage'],r['threshold_formula'],r['refinement'],r['lower']+'..'+r['upper']+'; '+r['status']))
    for p in [ROOT/'schedule_sensitivity_assumption.json',ROOT/'international/assumptions.json',ROOT/'existing_ssj/assumption.json']:
        if p.exists():x=readj(p);assumptions.extend(x if isinstance(x,list) else [x])
    assumptions.append(b.assumption('H-EXPERT-NET-CARGO-01','PROPOSED; income/payload/cost/mail contract UNKNOWN','груз/почта;RUB','Координатор: экспертный контекст AFL/hubs и belly cargo/mail; отдельный экспертный пакет готовится','Никакой добавки в базовую выручку; потенциальный дополнительный эффект требует отдельного совместного capacity/cost расчёта','Не задана произвольная доля или тариф','Договор, тоннаж/сезон/плотность, payload/cargo hold, наземная обработка/почтовые SLA'))
    assumptions.append(b.assumption('P09-SELECTION',{'screen_date':'2028-04-03','pairs_per_working_tail':3,'target_pairs':9,'frontier_objectives':['min_base_cautious_delta_known_subtotal','min_base_cautious_delta_journeys'],'numerical_tolerance':{'journeys':1e-6,'RUB':0.01}},'дата; пары; RUB2026; поездки','Один одинаковый контрольный оборот помогает построить конструкции; окончательная экономика считается на всех 731 датах. Три маршрута × два оборота в неделю дают шесть рабочих дней. Цель 9 внутри заданных пользователем 8–12. Pareto без весов/вероятностей.','Состав исследуемого множества и приоритеты; не критерий окончательного отказа другим парам','Уже посчитаны все 20 городов, существующая база, полные bank-контроли, hybrid и отдельные московские пути; альтернативная оптимизация частот остаётся OPEN','Месячный локальный OD/ownsales, slot/crew/AFM и полный ratebook'))
    b.dump(ROOT/'parameterledger.json',assumptions);b.csvwrite(ROOT/'parameterledger.csv',assumptions,fields=list(dict.fromkeys(k for a in assumptions for k in a)))
    b.dump(ROOT/'roadmap.json',dict(period=['2027-01','2028-12'],delivery_is_scenario_not_RW_plan=True,steps=[dict(period='до активации программы',action='Принять полный будущий KEEP/ownsales и ресурс по хвостам; сверить локальный OD и тариф; получить crew/MRO/AFM/slots и договорные ставки',gate='fullscope accepted; failure=>KEEP или новый явный сценарий'),dict(period='2027H2 условное окно',action='Передача→30дней сценарного ввода→один резерв совместимого типа; коммерческий запуск только после рабочегоN2',gate='service entry/crew/MRO/access accepted, финансирование покрыто;необязателен плюс первогоэтапа'),dict(period='2028-04 условный шаг',action='Второй рабочийборт: сравнить добавочный вклад прямого/волнового/смешанного шага и потерянное альтернативное применение',gate='Совместный P05/P06 пересчёт; подписанные обязательства не стирать'),dict(period='2028-09..12 условный шаг',action='Третий рабочийборт,8–12проектныхпар; уточнение частот по сезону; проверить ресурс и всюзатронутую сеть',gate='Непокрытые расходы нижеthreshold, финансирование в согласованномлимите; лимитUNKNOWN')],stop_conditions=['Нарушение доступности/безопасной эксплуатации или необходимого разрешения: не запускать затронутые рейсы','Отрицательный fullincremental result относительно допустимой альтернативы при отсутствии доказуемой траектории улучшения','Потребность вcash превышает принятыйлимит: лимитнеустановлен, не объявлятьдостижениеусловия','Пересматривать только будущие решения; сохранять прошлые выручку/платежи/обязательства и cancel/refund events'],payback_date=None,company_rank2_date=None))
    b.dump(ROOT/'supplemental_hypotheses.json',dict(P11=dict(source_manifest='bb8cecfcb37ea98c53ef27d2a22aa9745896fd00c29713060b0dc9b853c79c57',contract='sealed/P11/P09_integration_contract.json',commercial_effect=None,applied_to_base=False,reason='Неидентифицированныйdigital uplift не меняет P05intercept и не удваивает ancillary. Нужен experiment/cohort/causalestimate и единыйeventowner.'),expert=dict(hypothesis_id='H-EXPERT-NET-CARGO-01',status='PROPOSED',income=None,payload=None,applied_to_base=False),P02I=dict(source_manifest='8a47965b024e546c3e99f55334b3bb6f6d3bf43ae51f1583fc65d75d28cd316d',calculated=['I03_opportunity_threshold','I06_opportunity_threshold'],full_international_choice='OPEN',new_Tu214=0)))
    counts=Counter(x['status'] for x in rs)
    b.dump(ROOT/'build_summary.json',dict(programmes=len(ps),evaluations=len(rs),statuses=dict(counts),monthly_rows=len(monthly),author_candidates=len(readj(ROOT/'normalized_candidates.json')),local_hypotheses=len(readj(ROOT/'normalized_hypotheses.json')),legacy_hypotheses=35,calendar_rows_finalists=len(flights),finalists=selected,demand_status='SCENARIO_NOT_IDENTIFIED',full_financial_acceptance=False,source_research_pin='6a6326c2dcfe32e47ec25621bda0d15fcfe48ae1',engine_pin='982f13d9b6c378ed9581125ecc5c40f17dade6a3',global_optimality=False))
    print('ASSEMBLED',len(rs),'evaluations',len(flights),'flights',counts,flush=True)

if __name__=='__main__':main()
