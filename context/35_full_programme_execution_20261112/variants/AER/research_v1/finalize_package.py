"""Проверка воспроизводимых границ и запечатывание manifest, без Git-операций."""
import csv, hashlib, json, re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
R=Path(__file__).resolve().parent
def read(name):return json.loads((R/name).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def js(name,obj): (R/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def csvwrite(name,rows):
    with (R/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def csvread(name):return list(csv.DictReader((R/name).open()))

response=[]
for carrier,market,basis in [('Азимут','AER–MCX/TLV','SCHEDULE_MCX;LOCAL_TLV2027;AZ_BASE'),('Россия/Победа','AER–PEE','SCHEDULE_PEE'),('Победа','AER–GSV','SCHEDULE_GSV'),('Nordwind/Икар','AER–VOG','VOG_ANNOUNCEMENT')]:
    for kind in ['сохранить опубликованное предложение','ответ ценой в существующих тарифных местах','увеличить частоту при доказанном ресурсе']:
        response.append({'carrier':carrier,'market':market,'response':kind,'mechanism':'управление ценой и доступностью на действующих рейсах' if 'ценой' in kind else 'добавить физические рейсы только с назначенными хвостом/экипажем/слотами' if 'частоту' in kind else 'контрольный сценарий без ответного действия','resource_basis':'действующее опубликованное предложение; тарифные места/оптимальная цена UNKNOWN' if 'частоту' not in kind else 'свободный ресурс UNKNOWN; базирование само по себе не дополнительный самолёт','parameter_value':'UNKNOWN: назначает общая P05 response_policy; локальный множитель не выбран','assumption_id':'AER-A09','source_id':basis,'units':'продукт/цена RUB/датированные рейсы; величина UNKNOWN','period':'внешний сценарий 2027–2028; источник своим периодом','coverage':'конкурент и механизм; не прогноз реакции','status':'STAGE_B_RESPONSE_REQUEST'})
csvwrite('competitor_response_scenarios.csv',response)

products=[]
for pid in ['AER-S1','AER-H2','AER-D2','AER-I1']:
    for a in ['PEE','GSV','VOG']:
        products.append({'product_spec_id':f'{pid}-{a}-AER','programme_id':pid,'od':f'{a}↔AER','journey_leg_pattern':f'{a}–AER','revenue_unit':'один net fare на конечную поездку','capacity_rule':'одно кресло на каждом использованном датированном физическом плече; совместно с пересадками/KEEP','demand_pool_binding':'P05 UNKNOWN; не отдельный спрос для каждого кандидата','protected_status':'прямой проектный продукт, не наблюдаемая продажа','units':'поездки;кресла на плече;RUB/поездку','period':'проектный сезон2027–2028 после gates','coverage':'конструктор OD; не P06 admission','status':'DESIGN_ONLY','source_id':'AER_DESIGN;P00R;P06','assumption_id':'AER-A09;AER-A10;AER-A13'})
        for b in (['MCX'] if pid in ['AER-H2','AER-D2'] else ['TLV','BUS','TBS'] if pid=='AER-I1' else []):
            products.append({'product_spec_id':f'{pid}-{a}-{b}','programme_id':pid,'od':f'{a}↔{b}','journey_leg_pattern':f'{a}–{b}' if pid=='AER-D2' else f'{a}–AER–{b}','revenue_unit':'один сквозной net fare на поездку; разделение выручки по плечам не создаёт вторую продажу','capacity_rule':'пересадка расходует кресло каждого плеча; локальные AER и KEEP участвуют в том же лимите','demand_pool_binding':'единый P05 pool для direct/via/ground/outside и own KEEP; UNKNOWN','protected_status':'UNKNOWN: договор/MCT/багаж/восстановление обязательны' if pid!='AER-D2' else 'прямой проектный продукт','units':'поездки;кресла на плече;RUB/поездку','period':'проектный сезон2027–2028 после gates','coverage':'конструктор OD; international leg=existingKEEP, остаток UNKNOWN','status':'DESIGN_ONLY_NOT_SELLABLE_CLAIM','source_id':'AER_DESIGN;P00R;LOCAL_TLV2027;P06','assumption_id':'AER-A07;AER-A09;AER-A10;AER-A13'})
csvwrite('candidate_od_products.csv',products)

# Реальные ошибки получения сохраняются; разрешённый текстовый HTTP путь не требует UI.
js('tool_limitations.json',{'web_fetch_failures':[{'url':'https://new.aer.aero/','error':'Failed to fetch https://new.aer.aero/: (502) Bad Gateway'},{'url':'https://aer.aero/partners/','error':'URL https://aer.aero/partners/ is not accessible via this tool.'},{'url':'https://atechnics.ru/','error':'Failed to fetch https://atechnics.ru/: TimeoutError'}],'fallback':'Публичные read-only HTTP GET через urllib к официальному aer.aero; успешные ответы и hashes в fetch_receipts.json. Открытие браузера не требовалось.','other_limits':[{'attempt':'BeautifulSoup import','error':"ModuleNotFoundError: No module named 'bs4'",'resolution':'Использован стандартный html.parser; зависимостей не устанавливалось.'},{'source':'MRO_OPERATOR','error':'HTTP Error 503: Service Unavailable','consequence':'Текущий сертификат/правоRW UNKNOWN; исторический первичный релиз не повышен до текущего допуска'},{'source':'PEE_AER_PRIMARY','result':'HTTP200 без извлечённого основного текста','consequence':'Не принято как независимое подтверждение численного потока PEE; сохранён точный pinned источник.'}],'delegation':'Не запускалась: явное поручение работать самостоятельно без детей.','shared_checkout':'Только чтение exact blobs; скрипт проверки коллег, изменяющий общие журналы, не запускался по границе записи.'})

checks=[]
def check(name,ok,detail):checks.append({'check':name,'passed':bool(ok),'scope':detail})
pin=read('source_pins.json')
for p in pin['inputs']:
    check('exact_blob_manifest:'+p['path'],p['status']=='READ_EXACT_BLOB','Исходный SHA/blob/hash сохранён; проверка live refs не выполнялась')
    if p.get('local_extract','').endswith('.csv.json'):
        d=read(p['local_extract'])
        for row in d['rows']:
            h=hashlib.sha256(json.dumps(row['data'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            if h!=row['source_row_sha256']:raise ValueError('source row hash mismatch')
check('canonical_source_row_hashes',True,'Все сохранённые строки перепроверены; строки не становятся рыночной калибровкой')
for r in read('fetch_receipts.json'):
    if r['status']=='FETCHED':check('source_file_sha:'+r['source_id'],sha(R/r['local_path'])==r['sha256'],'Идентичность сохранённого HTTP ответа')
offers=csvread('local_schedule_offers.csv')
check('schedule_row_count',len(offers)==87,'87 опубликованных строк в пяти фильтрах, не 87 независимых рейсов')
check('airport_resolution',all(r['origin']!='UNKNOWN' and r['destination']!='UNKNOWN' for r in offers),'Все извлечённые station labels разрешены в airport codes; физическая смежность UNKNOWN')
check('schedule_no_inventory_claim',all(r['seats']=='UNKNOWN' and r['fare_rub']=='UNKNOWN' for r in offers),'Расписание не повышено до продаваемой ёмкости/котировки')
check('VOG_empty_not_zero',next(r for r in read('schedule_query_outcomes.json') if r['source_id']=='SCHEDULE_VOG')['status']=='NO_ROWS_IN_THIS_FILTER_NOT_MARKET_ABSENCE','Пустой текущий фильтр не экономический отказ')
check('future_TLV_in_KEEP',any(r['programme_id']=='ALL_KEEP' and r['destination']=='TLV' for r in csvread('market_deltas.csv')),'Опубликованная собственная программа2027 не записана в новый эффект')
pc=read('programme_candidates.json')['candidates'];lookup={p['programme_id']:p for p in pc}
check('six_candidate_specs',len(pc)==6,'Пять альтернатив использования авиаёмкости/стыковки и один наземный продукт')
check('paired_fleet_1',lookup['AER-S1']['working_tails_required']==lookup['AER-E1']['working_tails_required']==1,'Одинаковая размерность ресурса; фактическая доступность UNKNOWN')
check('paired_fleet_2',lookup['AER-H2']['working_tails_required']==lookup['AER-D2']['working_tails_required']==2,'Одинаковая размерность ресурса')
check('paired_identical_radials',lookup['AER-H2']['weekly_rotations'][:3]==lookup['AER-D2']['weekly_rotations'][:3],'В H2/D2 различается только применение второго хвоста')
check('zero_new_tu214',all(p['new_tu214_required']==0 for p in pc),'Построенные кандидаты не зависят от новыхТу214')
fl=csvread('dated_flight_fragments.csv');groups=defaultdict(list)
for f in fl:groups[(f['programme_id'],f['tail_role_id'])].append(f)
for key,v in groups.items():
    v.sort(key=lambda f:f['departure_utc'])
    for a,b in zip(v,v[1:]):
        check('continuity:'+a['flight_fragment_id'],a['destination']==b['origin'] and datetime.fromisoformat(b['departure_utc'])-datetime.fromisoformat(a['arrival_utc'])>=timedelta(minutes=45),'Только место/время хвоста по сценарию; crew/MRO/reserve не проверены')
check('all_fragments_2028_active_dates',all(f['period'].startswith('2028-') and 5<=int(f['period'][5:7])<=9 for f in fl),'Датированная конструкция сезона, не annualization одной недели')
check('monthly_24_each',all(len([x for x in csvread('monthly_stageB_calendar.csv') if x['programme_id']==p['programme_id']])==24 for p in pc),'24 месячных записи желаемой поставочно-ограниченной программы; не месячный спрос')
check('no_unconditional_economic_output',read('readiness.json')['economic_winner'] is None and read('programme_candidates.json')['economic_winner'] is None,'P05 не подменён локальной моделью денег/захвата')
check('hypotheses_disposition',all(x['outcome'] and x['distinguishingtest'] and x['revisit_condition'] for x in read('hypotheses.json')['hypotheses']),'Все локальные гипотезы имеют исход/пересмотр; условный исход не экономический отсев')
check('reference_arithmetic',read('cost_reference_check.json')['reference_example']['selected_five_item_subtotal_rub_excl_VAT']==98136.63,'Проверена только иллюстративная арифметика, не полный аэропортовый счёт')

# Явная чувствительность собственного банка, без произвольной оценки прибыли.
csvwrite('connection_sensitivity.csv',[{'MCT_min':m,'morning_margin_min':105-m,'evening_margin_PEE_min':90-m,'all_three_feeders_bidirectional_in_fixed_bank':m<=90,'units':'минуты;логическаясвязность','period':'проектныйбанкH2','coverage':'при выбранных block/clocks; не договорный MCT и не валидированный crew','status':'DESIGN_SENSITIVITY_NOT_CITY_REJECTION','source_id':'AER_DESIGN','assumption_ids':'AER-A05;AER-A07;AER-A15'} for m in [60,90,120,180]])
summary={'status':'PASS' if all(x['passed'] for x in checks) else 'FAIL','checks_passed':sum(x['passed'] for x in checks),'checks_total':len(checks),'source_sha_checks':len([x for x in checks if x['check'].startswith('source_file_sha:')]),'flight_fragment_count':len(fl),'meaning':'Идентичность/ссылки/даты/частичная геометрия ресурса; не независимая приёмка, не подтверждение рынка,crew/ТО,денег или P06','failed':[x for x in checks if not x['passed']]}
js('validation.json',summary)
js('qa/check_details.json',checks)
handoff={'package':'AER/research_v1','author_role':'исследовательский субагент Sol6.1 xhigh','language':'ru','created_at_utc':datetime.now(timezone.utc).isoformat(),'stageA':'COMPLETE','stageB':'REQUIRED_NOT_RUN','read_first':['handoff.md','case.json','programme_candidates.json','comparison_requests.csv','readiness.json'],'scope':'Только Сочи/AER; сохранённые входы exact SHA; local evidence/candidates, без собственного P05/P06 economics','high_value_findings':['AER подтверждён какопорныйRW, постояннаябаза/свободныйресурс UNKNOWN','AER–TLV2027 4/нед наSSJ — будущийKEEP','Новые локальные драйверы тарифов и альтернативные пакеты/стоянка','Нельзяназначать скидкуSJ2027/28 по найденным историческим программам','87строк расписания;91конфликтныйключclock,inventory UNKNOWN','Сравнение2хвостов H2/D2 сохраняетрадиали; вхабе12чдневнойстоянкииобход'],'programme_ids':[p['programme_id'] for p in pc],'hypothesis_ids':[h['hypothesis_id'] for h in read('hypotheses.json')['hypotheses']],'integration_rules':['Кандидаты/датированныефрагменты разныхпрограмм альтернативны, не суммировать','Донор/KEEP/резерв/ввод одинаковы у сравниваемых сторон','Потоки разныхисточников не складывать; рынокMOW требуетairportresolution','Защищённость/сквознойбагаж/черезкакиефизическиеплечапродаётсяпродукт UNKNOWN','Ставки2026 не будущийдоговор;не начислять всеальтернативныепакеты','Source rows/hash иmanifest обязательны'],'required_stageB_request_ids':[r['request_id'] for r in csvread('comparison_requests.csv')],'source_pins_file':'source_pins.json','source_pins_sha256':sha(R/'source_pins.json'),'new_source_receipts_sha256':sha(R/'fetch_receipts.json'),'validation':summary,'git_operations':'Только git show/ls-tree/rev-parse/status; нетcheckout/commit/push/merge/rebase/fetch','writes':'Только назначенный каталог variants/AER/research_v1','publication':'Не публиковалось; публичныйSite/дашбордАнастасии не менялись','manifest':'output_manifest.json','approval_claims':'StageA completion не является экономической или операционной приёмкой; авторские42checksP06 не перенесены накачествоэтогокейса'}
js('handoff.json',handoff)
files=[]
for p in sorted(R.rglob('*')):
    if p.is_file() and p.name!='output_manifest.json' and '__pycache__' not in p.parts:
        files.append({'path':p.relative_to(R).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size,'role':'source_evidence' if p.parts[-2]=='sources' else 'source_visual_check' if '/qa/' in str(p) else 'pinned_input_extract' if '/inputs/' in str(p) else 'research_output_or_reproduction'})
js('output_manifest.json',{'package':'AER/research_v1','format':'sha256 of raw file bytes; self excluded; no dependency/cache copies','created_at_utc':datetime.now(timezone.utc).isoformat(),'file_count':len(files),'total_bytes':sum(f['bytes'] for f in files),'stageA_status':handoff['stageA'],'stageB_status':handoff['stageB'],'files':files})
print(json.dumps(summary,ensure_ascii=False));print('manifest files',len(files),'bytes',sum(f['bytes'] for f in files))
if summary['status']!='PASS':raise SystemExit(1)
