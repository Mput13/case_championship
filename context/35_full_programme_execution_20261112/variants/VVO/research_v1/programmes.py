"""Dated operational diagnostics, not a P06-accepted RW bundle."""
import csv,datetime,json
from collections import Counter,defaultdict
from zoneinfo import ZoneInfo
from extract_local import ROOT,dump,write_csv
G={(r['origin'],r['destination']):r for r in csv.DictReader((ROOT/'geometry_and_block_proxies.csv').open())}
TZ={'VVO':'Asia/Vladivostok','BQS':'Asia/Yakutsk','UUS':'Asia/Sakhalin','PKC':'Asia/Kamchatka','HTA':'Asia/Chita','SVX':'Asia/Yekaterinburg','OMS':'Asia/Omsk','GOJ':'Europe/Moscow','KUF':'Europe/Samara','UFA':'Asia/Yekaterinburg','HRB':'Asia/Shanghai','PKX':'Asia/Shanghai'}
WEEK=datetime.date(2028,7,3)
PERIOD='2027-01/2028-12'
assert WEEK.weekday()==0
F=[]
def rt(pid,tail,day,base,other,minute,seq):
 block=int(G.get((base,other),G.get((other,base)))['planning_block_min'])
 depart=datetime.datetime.combine(WEEK+datetime.timedelta(days=day),datetime.time(),ZoneInfo(TZ[base]))+datetime.timedelta(minutes=minute)
 for a,b,t in [(base,other,depart),(other,base,depart+datetime.timedelta(minutes=block+60))]:
  # All arithmetic remains in the base timezone; local clocks are derived separately.
  arrival=t+datetime.timedelta(minutes=block)
  fid=f'{pid}:T{tail}:{day}:{seq}:{a}-{b}'
  F.append({'programme_id':pid,'flight_instance_id':fid,'aircraft_id':f'{pid}:SCENARIO-T{tail}','origin_airport':a,'destination_airport':b,'departure_utc':t.astimezone(datetime.timezone.utc).isoformat(),'arrival_utc':arrival.astimezone(datetime.timezone.utc).isoformat(),'departure_local':t.astimezone(ZoneInfo(TZ[a])).isoformat(),'arrival_local':arrival.astimezone(ZoneInfo(TZ[b])).isoformat(),'block_min':block,'nominal_seats_scenario':100,'saleable_seats':'UNKNOWN','aircraft_variant':'UNBOUND:RRJ95B/RRJ95LR/SJ100_PD8 separate branches required','status':'предложенный диагностический рейс; не расписаниеRW','period':'03–09.07.2028,одна диагностическая неделя','coverage':'без реальныххвостов/crew/ТО/slot/KEEP;не годоваясеть','source_id':'COORDINATES;VVO_WINTER_REG;RW_2022_CANCEL','assumption_id':'VVO-A01;VVO-A02;VVO-A03;VVO-A05;VVO-A06;VVO-A08;VVO-A09;VVO-A18'})

def build_flights():
 # 1-tail lean programme: 9 round trips, no promised connecting bank.
 for d,dests in enumerate([['BQS','UUS'],['HTA'],['BQS'],['UUS'],['BQS','UUS'],['HTA'],['BQS']]):
  for s,dest in enumerate(dests):rt('P-VVO-R1',1,d,'VVO',dest,420 if len(dests)>1 and s==0 else 780 if s else 480,s)
 # 2 tails, 20 round trips. HUB and RADIAL have exactly the same route/day/count footprint.
 for pid in ['P-VVO-R2','P-VVO-H2','P-VVO-ALT-SVX']:
  alt=pid.endswith('SVX');base='SVX' if alt else 'VVO';mapping={'BQS':'OMS','UUS':'GOJ','HTA':'KUF','PKC':'UFA'} if alt else {x:x for x in ['BQS','UUS','HTA','PKC']}
  for d in range(7):
   if d in [0,2,4]:rt(pid,1,d,base,mapping['HTA'],480,0);rt(pid,2,d,base,mapping['PKC'],480,0)
   elif d in [1,3,5]:
    for tail,spoke in [(1,'BQS'),(2,'UUS')]:
     b=int(G.get((base,mapping[spoke]),G.get((mapping[spoke],base)))['planning_block_min'])
     first=(660-(2*b+60)) if pid=='P-VVO-H2' else 420
     second=780 if pid=='P-VVO-H2' else 765 if tail==1 else 960
     rt(pid,tail,d,base,mapping[spoke],first,0);rt(pid,tail,d,base,mapping[spoke],second,1)
   else:
    rt(pid,1,d,base,mapping['BQS'],480,0);rt(pid,2,d,base,mapping['UUS'],480,0)
 write_csv('diagnostic_flights.csv',F)
 checks=[]
 for pid in ['P-VVO-R1','P-VVO-R2','P-VVO-H2','P-VVO-ALT-SVX']:
  fs=[x for x in F if x['programme_id']==pid];by=defaultdict(list)
  for r in fs:by[r['aircraft_id']].append(r)
  tails=[];conf=[]
  for tail,rs in by.items():
   rs.sort(key=lambda x:x['departure_utc']);daily=defaultdict(int)
   for r in rs:daily[r['departure_local'][:10]]+=r['block_min']
   for a,b in zip(rs,rs[1:]):
    gap=(datetime.datetime.fromisoformat(b['departure_utc'])-datetime.datetime.fromisoformat(a['arrival_utc'])).total_seconds()/60
    if a['destination_airport']!=b['origin_airport'] or gap<60:conf.append({'before':a['flight_instance_id'],'after':b['flight_instance_id'],'gap_minutes':gap})
   tails.append({'tail_id':tail,'block_hours_week':round(sum(r['block_min'] for r in rs)/60,2),'max_daily_block_hours':round(max(daily.values())/60,2),'initial_location':rs[0]['origin_airport'],'final_location':rs[-1]['destination_airport'],'daily_excess_over_10h_proxy':[d for d,m in daily.items() if m>600]})
  checks.append({'programme_id':pid,'legs':len(fs),'roundtrips':len(fs)//2,'counts_each_way':dict(Counter(r['destination_airport'] for r in fs if r['origin_airport'] in ['VVO','SVX'])),'geometry_planning_continuity_conflicts':conf,'tails':tails,'status':'только арифметика/позиция planning-образца;crew,ТО,reserve,range,slots UNKNOWN'})
 pairs=[]
 for d in [1,3,5]:
  for a,b in [('BQS','UUS'),('UUS','BQS')]:
   day=(WEEK+datetime.timedelta(days=d)).isoformat();inc=next(r for r in F if r['programme_id']=='P-VVO-H2' and r['origin_airport']==a and r['departure_local'][:10]==day and r['flight_instance_id'].split(':')[3]=='0');out=next(r for r in F if r['programme_id']=='P-VVO-H2' and r['destination_airport']==b and r['departure_local'][:10]==day and r['flight_instance_id'].split(':')[3]=='1');gap=(datetime.datetime.fromisoformat(out['departure_utc'])-datetime.datetime.fromisoformat(inc['arrival_utc'])).total_seconds()/60
   pairs.append({'origin':a,'via':'VVO','destination':b,'date':day,'arrival_leg_id':inc['flight_instance_id'],'departure_leg_id':out['flight_instance_id'],'connection_minutes':gap,'fare_unit':'RUB/конечнаяпоездка,начислениеодинраз','seat_use':'одно кресло на каждом из2плеч','status':'временнаясвязьусловна;продажа/защита/MCTRW UNKNOWN','source_id':'VVO_TRANSFER_RULES','assumption_id':'VVO-A04;VVO-A11;VVO-A15'})
 dump('connection_candidates.json',pairs)
 dump('resource_diagnostic.json',{'period':'03–09.07.2028','checks':checks,'connection_candidates':len(pairs),'all_hub_connections_120min':all(r['connection_minutes']==120 for r in pairs),'real_resource_accepted':False,'not_run':['P06bundle evaluation','реальная годоваяраскладка','dispatchweights','lawfulcrewrosters','MRO/reserve','P/KEEP reallocation','денежнаяэкономика'],'limitations':'Не умножать на52. Все100кресел иblock proxyусловны. НачальнаяпозициявVVO/SVX требуетперегонаприразвёртывании;оннеизображёнвнедельномфрагменте и не равеннулю.'})
 return checks

COMMON={
 'status':'Stage A: проверяемый кандидат; условен до общих входов Stage B',
 'period':PERIOD,'unit':'программа/физические плечи/конечные поездки','coverage':'локальный компонент общей сети; не самостоятельная сеть8–12 и не доказательство№2',
 'aircraft_branches':['RRJ95B/SaM146:своиAFM/хвосты/затраты','RRJ95LR/SaM146:отдельныйвариант','SJ100/PD8:своипоставка/ввод/AFM/crew/ТО/затраты'],
 'tu214_new_aircraft_branch':0,
 'sources':['RW_2022_CANCEL','VVO_WINTER','VVO_TRANSFER_RULES','PIN-P06-producer_contract','PIN-P04-thresholds'],
 'needs_common_inputs':['P03:одинаковыйP/KEEPtailcalendar,donor,current sales,reserve,MRO,crew,slots,AFM,перегоны','P05:единыеmonth×OD×segmentпулы,цены20кг,choice,tripduration,existingRWproducts,response_policy','P04:rate-to-driverприменимость,launch/base/fuel/MRO/crew/exit,расписаниеоплат,начальныеобязательства','P06:полныйbundle иобщийпересчёт затронутогоKEEP'],
 'own_sales_policy':{'retained':'Все не изменённые существующие продажи/обязательства RW сохраняются в будущемKEEP и P. Их перечень UNKNOWN, не пустой.','new':'Только явно добавленные датированные плечи и продукты.','shifted':'Только с departure-product ID, изменение времени/дня учитывается в спросе.','reduced':'Нет предполагаемого бесплатного донора. Если переносится существующий борт, его прежние рейсы/маржа/продажи/восстановление входят в сравнение.','cannibalization':'Один общий P05 demand_pool, в том числе варианты с пересадкой через действующие базы; не сумма независимых моделей.'},
 'delivery_logic':{'0ready':'Нет добавочных собственных рейсов VVO на новомSJ;KEEP и partner-вариант остаются. Это не обнуление существующегоRW.','1ready':'R1 только после доказанного ввода, экипажа и резерва; сопоставить альтернативу для того же одного борта.','2ready_phased':'R2/H2 только после обоих вводов и отдельного резерва; дата не назначена местным исследователем.','partial':'Частоты/сеть снижаются доR1 либо остаётсяKEEP;проектная цель8–12общая.','delay':'Сдвиг по календарюP03,пересчёт сезона/платежей/запуска; нельзяпростоумножитьнеделю.','existing_tail_redeploy':'Допустимтолькопослеустановлениядонора и его потерянногорезультата.'},
 'finance':'NOT_RUN. Использовать P04 TH-OPTION/TH-FIXED/TH-LAUNCH/TH-FUNDING; положительный variable contribution не полный результат. Нет локальной калибровкиспроса или денег.',
 'assumption_ids':['VVO-A02','VVO-A03','VVO-A04','VVO-A05','VVO-A06','VVO-A07','VVO-A08','VVO-A09','VVO-A10','VVO-A11','VVO-A12','VVO-A13','VVO-A14']}

def programmes():
 rows=[]
 def add(pid,title,role,flights,ods,resource,change,cf):
  rows.append({**COMMON,'programme_id':pid,'title':title,'role':role,'flight_pattern':flights,'OD_products':ods,'resource_group':resource,'changes':change,'counterfactual':cf,'distinguishing_tests':[]})
 add('P-VVO-R1','Небольшая радиальная программа VVO','новая компактная сезонная база, существование базыRWнепредполагается',{'BQS':{'RT_week':4,'days':'пн/ср/пт/вс'},'UUS':{'RT_week':3,'days':'пн/чт/пт'},'HTA':{'RT_week':2,'days':'вт/сб'}},['VVO–BQS','VVO–UUS','VVO–HTA'],{'operating_tails':1,'diagnostic_legs_week':18,'reserve':'UNKNOWN; ветви выделенный1дополнительный либо договорнойсместом/SLA','overnight':'VVO; ТО/crew/стоянка не подтверждены','paid_tail_scope':'тот же календарь и1рабочийборт у альтернативы;зимойинойресурсне исчезает'},'Добавить только разрешённые физические рейсы; защищённые пересадки не обещать. Летнийпилот;межсезонье/зима отдельныечастоты и условия.','Тотже1борт остаётся в принятой существующейбазе;остальнаясетьсохраняется. Перегоны,новаябаза и потерядонороввключены.')
 add('P-VVO-R2','Радиальная программа на двух бортах','новая база без намеренно синхронизированной волны',{'BQS':{'RT_week':7,'days':'2RTвт/чт/сб;1RTвс'},'UUS':{'RT_week':7,'days':'2RTвт/чт/сб;1RTвс'},'HTA':{'RT_week':3,'days':'пн/ср/пт'},'PKC':{'RT_week':3,'days':'пн/ср/пт'}},['VVO–BQS','VVO–UUS','VVO–HTA','VVO–PKC'],{'operating_tails':2,'diagnostic_legs_week':40,'reserve':'UNKNOWN;тот жеreservecalendarвP/KEEP','overnight':'оба вVVO','crew':'всеFTE,duty,отдыхUNKNOWN'},'Добавление4уникальныхпар;предлагаемыечастотынеявляютсяоценкойспроса. Естественныепересадки допускаютсяобщимchoice.','H2при техже20RT/днях/парке;ALT-SVXпри томжепарке;KEEPсбудущимиобязательствами.')
 add('P-VVO-H2','Те же рейсы с волной BQS–VVO–UUS','смешанная радиальная программа и защищённая внутренняя пересадка',rows[-1]['flight_pattern'],['теже4локальныхOD','BQS–VVO–UUS и UUS–VVO–BQSвт/чт/сб;возвратчерез2/3/7ночей'],{'operating_tails':2,'diagnostic_legs_week':40,'reserve':'UNKNOWN;единыйресурссR2','overnight':'оба вVVO','bank':'вт/чт/сб:оба inbound11:00,оба outbound13:00;120мин','needs':'двеодновременныестоянки/handling/трансфер/багаж,местанеустановлены'},'Переставить время7+7короткихRT;HTA/PKCбезизменений. На деньволны по2RTсBQS/UUS. Одинсквознойтарифнапоездку и2занятыхкресельныхсегмента.','R2с темижефизическимирейсами/днями/типами;сохранить P05пулы,считатьпотерилокальныхпродажиззасдвигавремени и recoverycost.')
 rows[-1]['distinguishing_tests']=['Дополнительный полный результат H2–R2 после перераспределения всех продаж и расходовзащиты, не добавлениестаройтрансфернойвыручки.','Сравнить прямойBQS–UUS иконкурентныепересадки черезKHV: не считать отсутствие ихвVVOAPI отсутствиемрынка.','Тесттайминга/возвратов90/120/180мин,+30/+60delay,лето/зима/межсезонье.']
 add('P-VVO-ALT-SVX','Альтернативное применение двух бортов в SVX','существующая базаRW;конкретныйсвободныйресурснеподтверждён',{'OMS':{'RT_week':7},'GOJ':{'RT_week':7},'KUF':{'RT_week':3},'UFA':{'RT_week':3}},['SVX–OMS','SVX–GOJ','SVX–KUF','SVX–UFA'],{'operating_tails':2,'diagnostic_legs_week':40,'reserve':'тотже физический календарьчто уVVO;небесплатныйпул','overnight':'SVX','note':'ЧислоRTодинаковое,блок-часы отличаются;доступныйнеиспользованныйресурссохраняется/можетбытьпереоптимизированобщимядром'},'Добавочные частоты из действующей базы, с сохранением существующихрейсов и общегоучётасобственногоперетока. Сетка — контролируемыйресурсныйконтроль, не новаяоценкарынковOMS/GOJ/KUF/UFA.','R2/H2VVOприодинаковыхtailavailability,external/calendar иfullbusinessKEEP. Дельта включаетвыгодыальтернативныхрынков, несравниваетнезависимыескоринги.')
 add('P-VVO-PARTNER','Пересадки через VVO с партнёром','VVO как рынок/стыковочный аэропорт без новойсобственнойбазы',{'own_VVO':'не добавлять до договора','partner_markets':['BQS/HTA/IKT/UUS/YKS→VVO→HRB/PKX/PEK/PVG'],'physical_flights':'только выбранные датированные рейсы партнёров, не весь опубликованный набор'},['подтверждаемые сквозные OD; PEK/PKX раздельно'],{'own_operating_tails_VVO':0,'same_fleet':'два борта остаются вALT-SVX;внутригрупповыеобязательствасохраняются','partner_capacity':'UNKNOWN,неfree;требуетсяallotment/prorate/SLA','reserve':'вреальномоператорскомсоглашении,нефиктивныйRWtail'},'Заключение/тестдоговоровсамо неавторизовановэтомисследовании. ВStageBодинкорпоративныйдоход,платаоператору,misconnectcash.','ALT-SVXбезпартнёрскогопродуктаиVVOH2/новаябаза;тежеRWборта,добавочныедоговорныесобытияявны.')
 add('P-VVO-I1','Северо-восточный Китай как дополнительный продукт','дополнительная международная ветвь,необязательнаядляисходногокейса',{'HRB':{'RT_week':2},'PKX':{'RT_week':2},'source_of_hours':'заменитьвR1по2RTBQS иUUS,не добавлятьбесплатныечасы'},['VVO–HRB','VVO–PKX'],{'operating_tails':1,'reserve':'какR1;права/международныйдопуск/SJ100раздельноUNKNOWN','new_Tu214':0},'Условная замена части предложенияR1, а не действующихнеизвестныхRWпродаж. СпроситаймингоценитьпротивнаблюдаемогопредложенияКитая.','R1беззамены;PARTNERна техжемаршрутах;выпадающиеBQSUUSпродажипересчитываются.')
 dump('programme_candidates.json',{'stage':'A','main_network_target':'8–12 уникальных airport pairs в общей проектной сети на конец2028; здесьлокальные компоненты3/4пар','programmes':rows,'kernel_delivery':'Это спецификации ичастичныйоперационныйfragment, не полныйbundle producer_contract P06. ДатированныеflightIDsестьтолько4диагностическихпрограмм. ДляPARTNER/I1сознательнонетмнимогослота/договора/кресел.'})
 monthly=[]
 for year in [2027,2028]:
  for month in range(1,13):
   season='лето' if month in [6,7,8,9] else 'межсезонье' if month in [4,5,10] else 'зима'
   for pid in ['P-VVO-R1','P-VVO-R2','P-VVO-H2','P-VVO-ALT-SVX','P-VVO-PARTNER','P-VVO-I1']:
    monthly.append({'month':f'{year}-{month:02}','programme_id':pid,'season':season,'action_calendar_rule':'Только после service_entry и всехoperationalgatesP03;летниеR2/H2Jun–Sep;остальныемесяцыR1илиKEEPсотдельнойчастотой. ALTиспользуеттотжекалендарьресурса.','additional_SJ100_before_H22027':'нетновыхSJпоусловиюкейса;existingtailтолькосдонором' if year==2027 and month<7 else 'N(t)толькоизP03;нефиксированныйпрогноз','actual_flight_count':'UNKNOWNдоразвёртыванияобщегокалендаря','month_demand':'UNKNOWN,не0','revenue':'NOT_RUN','unit':'месяц×спецификацияпрограммы','period':f'{year}-{month:02}','coverage':'24месяца перечислены;недельныйfragment неannualized','status':'условный календарный контракт,не годовоерасписание','source_id':'PIN-P03-aircraft_type_parameters;PIN-P06-producer_contract','assumption_id':'VVO-A06;VVO-A07;VVO-A08;VVO-A11'})
 write_csv('programme_monthly_spec.csv',monthly)
 return rows

if __name__=='__main__':
 c=build_flights();p=programmes();print(json.dumps({'programmes':len(p),'diagnostic_legs':len(F),'diagnostics':c},ensure_ascii=False))
