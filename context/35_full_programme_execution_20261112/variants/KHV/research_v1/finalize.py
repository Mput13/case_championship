import pathlib,json,csv,hashlib,subprocess
R=pathlib.Path(__file__).parent
def js(n,x):(R/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def read(n):return json.loads((R/n).read_text())
# Repair snapshot extensions while preserving response hashes.
renames={'LOCAL_SUPPORT':'pdf','KHV_MARKETING':'pdf','KHV_CONTRACT':'docx'}
for sid,ext in renames.items():
 old=R/'sources'/f'{sid}.html';new=R/'sources'/f'{sid}.{ext}'
 if old.exists():old.rename(new)
for name in ['fetch_receipts.json']:
 x=read(name)
 for v in x:
  if v['source_id'] in renames and v.get('http_status')==200:v['local_path']='sources/'+v['source_id']+'.'+renames[v['source_id']]
 js(name,x)
s=list(csv.DictReader((R/'sources.csv').open()))
for x in s:
 if x['source_id'] in renames:x['local_path']='sources/'+x['source_id']+'.'+renames[x['source_id']]
with (R/'sources.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=s[0].keys());w.writeheader();w.writerows(s)
js('acquisition_issues.json',{'issues':[{'tool':'web.open','url':'https://khvaero.ru/partners/open-info-khabaero/law/fee/prices/tarif_2026_11.pdf','exact_error':'URL https://khvaero.ru/partners/open-info-khabaero/law/fee/prices/tarif_2026_11.pdf is not accessible via this tool.','fallback':'Использованы уже закреплённые KHV-строки P04 по620a0ac4;новый тариф не принят.','status':'NOT_NEWLY_FETCHED'},{'tool':'Python urllib','url':'https://khvaero.ru/passengers/schedule/','exact_error':'[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate (_ssl.c:1006)','fallback':'Тот же официальный оператор на https://khv.aero/passengers/schedule/ получен с обычной проверкойTLS;сертификатная проверка не отключалась.','status':'ALTERNATE_OFFICIAL_HOST_ACQUIRED'},{'tool':'web.click','url':'https://khv.aero/partners/docs/Complex_dogovor_ob_okazanii_uslug_dlya_rossiiskih_potrebitelei.docx','exact_error':'(400) Unsupported content-type: application/vnd.openxmlformats-officedocument.wordprocessingml.document','fallback':'Прямая текстовая HTTP-загрузка и чтение word/document.xml черезstdlibzip/xml;никакого browser use.','status':'ACQUIRED'},{'tool':'HTTP','url':'https://khv.aero/passengers/transport/','exact_error':'HTTP200;Элемент не найден!','fallback':'Не принят как источник о наземном доступе;GROUND_VVO оставлен с собственными ограничениями.','status':'CONTENT_NOT_FOUND'}],'diagnostic_scope':'Без вмешательства в сессии;детей не запускали по прямому ограничению задания;сервисы не перезапускались.'})
obs=list(csv.DictReader((R/'competitor_observations.csv').open()));counts=list(csv.DictReader((R/'local_schedule_week_counts.csv').open()))
fare={'UUD':12349,'HTA':10956,'YKS':14088,'BQS':4884,'NER':6253,'DYR':13860}
markets=[]
for code,city in [('UUD','УЛАН-УДЭ'),('HTA','ЧИТА'),('UUS','ЮЖНО-САХАЛИНСК'),('GDX','МАГАДАН'),('PKC','ПЕТРОПАВЛОВСК-КАМЧАТСКИЙ'),('VVO','ВЛАДИВОСТОК'),('BQS','БЛАГОВЕЩЕНСК'),('YKS','ЯКУТСК'),('IKT','ИРКУТСК'),('OVB','НОВОСИБИРСК'),('SVX','ЕКАТЕРИНБУРГ'),('NLI','НИКОЛАЕВСК-НА-АМУРЕ')]:
 rows=[v for v in obs if v['city']==city];selected=[v for v in counts if v['city']==city]
 markets.append(dict(market_id='AIR:KHV:'+code,airport_pair=['KHV',code],source_row_ids=[v['row_id'] for v in rows],source_ids=sorted(set(v['source_id'] for v in rows)),published_carriers=sorted(set(v['carrier_normalised'] for v in rows)),week_diagnostics=selected,unit='publishedstationpairrules;notseats',period='2026-11/2027-03;selectedtwoweeks',status='PARTIAL_PUBLISHED_OFFER',coverage='Неполный набор продуктов;маркетинговыйкоднеавтоматическиоператор;креслаUNKNOWN',published_social_fare_2026= fare.get(code),fare_unit='RUB/пассажирскийтариф;LOCAL_SUPPORT' if code in fare else None,fare_status='не датированная котировка;booking_lead/багаж UNKNOWN' if code in fare else 'UNKNOWN',true_OD_monthly=None,rw_committed_sales=None,response_hypothesis='Существующий перевозчик может изменить тариф или использовать уже имеющиеся частоты. Объём доступного ресурса неизвестен;новые частоты без источника не добавлять.',response_source='KHV_WINTER;KHV_OUT',assumption_id='A-KHV-14;A-KHV-19;A-KHV-20;A-KHV-21;A-KHV-22'))
js('local_market_profiles.json',{'markets':markets,'coverage':'Только конкретные airportpairs. Москва остаётся городским агрегатом в релизе,а не выдуманным MOWаэропортом. BeijingairportUNKNOWN,поэтому PEK/PKX не приписаны.','catchment':'Авторские617441 и705129 имеютразныеопределения;невыбраныкакчислопокупателей. ДоступкKHV/VVO,поезд,пересадкаиконкуренция требуютP05адаптера.'})
# Общие пороги запрашиваются у владельцев P04/P05/P06, не рассчитываются локально.
js('stageB_threshold_spec.json',{'owner':'P04/P05/P06','status':'REQUEST_NOT_EVALUATED','period':'Помесячно2027-01..2028-12 и денежные события до запуска','contribution':'P06 начисляет нетто-тариф конечной поездке один раз, списывает места на каждом использованном датированном плече и принятые переменные расходы. Продажа сквозной поездки не равна двум независимым продажам сегментов.','full_result_threshold':'При фиксированных принятых ресурсах и прочих обязательствах максимальная допустимая дополнительная местная стоимость базы/запуска/выхода равна остатку дельты полного результата P06 относительно того же будущего KEEP до добавления этих пока неизвестных событий. Упущенное задание уже входит в P−KEEP и не вычитается повторно.','partner_threshold':'Найти ставку партнёрского события, при которой P0 вместе с тем же альтернативным применением ресурса RW равен H2. Ограничить продажу доступными местами партнёра и условиями защиты.','fare_threshold':'Найти нетто-тариф поездки, покрывающий принятую программу, с повторным выбором P05 при изменении цены. Не сохранять спрос неизменным при повышении цены, кроме явно отдельного диагностического опыта с фиксированным спросом.','cash_threshold':'Отдельно моделировать фактическую предоплату, депозиты, поступление поддержки и оплату. Публичные100% предоплаты — условие stress-ветви, а не подписанный факт RW.','support':'Не предполагать право на поддержку. Использовать события и применимость P04 для конкретного года;неизвестное будущее назначение остаётся UNKNOWN.','required_outputs':['Конечные поездки и сегменты по месяцам','Добавочный переменный вклад','Полный добавочный результат','Пик денег и потребность в финансировании до улучшения','Чистый прирост пассажиров RW с учётом собственного перетока','Условия остановки или изменения программы'],'assumption_ids':['A-KHV-14','A-KHV-15','A-KHV-16','A-KHV-17','A-KHV-19','A-KHV-22','A-KHV-27']})
# Pin the final input manifest itself and expose a compact source tranche.
js('usable_tranche.json',{'package':'KHV-research-v1','stage':'A_COMPLETE_LOCAL_ONLY','files':[dict(path=str(p.relative_to(R)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in [R/'case.json',R/'evidence.csv',R/'sources.csv',R/'local_schedule_rows.csv',R/'programme_candidates.json',R/'resource_checks.json',R/'comparison_requests.csv',R/'input_manifest.json']],'priority':'R1vsE1same1tail;H2vsD2/P0same2tails;fullKEEPandalternativeusedrequired','economics':'NOT_RUN;P05missing;P06independentacceptancepending'})
checks=[]
def ck(name,ok,detail):checks.append(dict(check=name,pass_=bool(ok),detail=detail))
required=['case.json','evidence.csv','market_deltas.csv','hypotheses.json','programme_candidates.json','comparison_requests.csv','assumptions.csv','readiness.json','handoff.json','input_manifest.json','resource_checks.json']
ck('requiredoutputs',all((R/n).exists() for n in required),required)
for p in sorted(R.rglob('*.json')):
 try:json.loads(p.read_text());ok=True
 except Exception:ok=False
 ck('json:'+str(p.relative_to(R)),ok,'parse')
inputs=read('input_manifest.json')
for x in inputs['sources']:
 b=subprocess.check_output(['git','show',x['commit']+':'+x['path']]);ck('pin:'+x['source_id'],hashlib.sha256(b).hexdigest()==x['full_source_sha256'],x['commit'])
 p=R/x['output'];ck('extractexists:'+x['source_id'],p.exists(),x['output'])
 if p.suffix=='.json':
  o=json.loads(p.read_text())
  if isinstance(o,list) and o and isinstance(o[0],dict) and 'original_row' in o[0]:
   ck('rowhash:'+x['source_id'],all(hashlib.sha256(json.dumps(v['original_row'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==v['source_row_sha256'] for v in o),'canonical original row SHA256')
for x in read('fetch_receipts.json'):
 if x.get('http_status')==200:
  p=R/x['local_path'];ck('responsehash:'+x['source_id'],p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==x['sha256'],'rawHTTPbytes')
rc=read('resource_checks.json');ck('rotationfrequencyconservation',all(x['frequency_conservation'] for x in rc['checks']),rc['checks'])
ck('badclockcounterexamplekept',all(not x['window75_180_met'] for x in rc['naive_bank_time_counterexamples']),'195/197minmiss selectedwindow;not city rejection')
ck('correctedclockwindow',all(x['window75_180_met'] for x in rc['corrected_bank_time_examples']),'proxyonly;crew/MCT/slotsUNKNOWN')
ass={v['assumption_id'] for v in csv.DictReader((R/'assumptions.csv').open())}
ck('assumptionIDs_unique',len(ass)==28,'28 local assumptions')
for x in read('programme_candidates.json')['programmes']:
 ck('programmeassumptions:'+x['programme_id'],set(x['assumption_ids']).issubset(ass),'alllocalIDsregistered')
 ck('nozeroUnknownCapacity:'+x['programme_id'],all(v['capacity']=='UNKNOWN_P03' for v in x['legs']),'nocapacityfabricated')
ck('sourceschedule443',len(list(csv.DictReader((R/'local_schedule_rows.csv').open())))==443,'221arrival+222departurerules')
ck('hypotheses7outcomes',len(read('hypotheses.json')['hypotheses'])==7 and all(x['disposition'] and x['revisit_condition'] for x in read('hypotheses.json')['hypotheses']),'notallcityrejected')
ck('noP06claim',read('readiness.json')['P06_run']=='NOT_RUN_INCOMPLETE_REAL_BUNDLE','notsoftwareacceptanceorprofit')
js('validation.json',{'scope':'Локальные механические и provenance проверки;не независимая приёмка экономики/рынка/операций.','checks':checks,'passed':sum(x['pass_'] for x in checks),'failed':sum(not x['pass_'] for x in checks),'status':'PASS_LOCAL_ONLY' if all(x['pass_'] for x in checks) else 'FAIL','expected_not_run':['P05choicecalibration','RWphysicaldatedinventoryadmission','P03crew/ТО/резерв/KEEP','P04futurefullcostcash','P06fullRWcomparison','independentreview']})
assert all(x['pass_'] for x in checks),[x for x in checks if not x['pass_']]
# Manifest does not hash itself: no circular attestation.
files=[dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),role='pinned_input' if 'inputs' in p.relative_to(R).parts else 'public_source' if 'sources' in p.relative_to(R).parts else 'package') for p in sorted(R.rglob('*')) if p.is_file() and p.name!='output_manifest.json']
js('output_manifest.json',{'package_id':'KHV-research-v1','directory':str(R),'stageA':'COMPLETE_LOCAL_RESEARCH_AND_CONSTRUCTION','stageB':'OPEN','sourcepins':inputs['pins'],'files':files,'file_count':len(files),'total_bytes':sum(x['bytes'] for x in files),'manifest_self_hash':'excluded_by_design','git_operations':'read_only gitshow/ls-tree/rev-parse/status;noGitmutations','commands_for_offline_replay':['python3 build_package.py','python3 polish_package.py','python3 resource_check.py','python3 finalize.py'],'replay_note':'Run from any directory with these script paths; uses saved source bytes and pinned blobs. Network reacquisition intentionally separate and changes information set.','not_claimed':['economicwinner','realRWfleetavailability','P06acceptance','independentmarketreview']})
print('validation',len(checks),'PASS; manifest',len(files),'files',sum(x['bytes'] for x in files),'bytes')
