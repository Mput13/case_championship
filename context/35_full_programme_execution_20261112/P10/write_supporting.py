#!/usr/bin/env python3
"""Supporting registers and a compact standalone chart. P10 only."""
import csv
import hashlib
import json
from pathlib import Path

R=Path(__file__).resolve().parent
def write(name,rows):
    fields=list(dict.fromkeys(k for x in rows for k in x))
    with (R/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

dependencies=[
 ('P10-D01','P09/P03','ПолныйfutureKEEP по4ячейкамбизнеса/типам/месяцам; датированныеflights/sales/aircraft/crew/MRO/donors','P09неполучен;P03KEEP/crew/ТОUNKNOWN','Пассажиры,инкремент,вытеснение,ресурс,география','UNKNOWN не0;диагностикаP10отдельно','Принятый24месячныйbundlePиKEEPсmanifest;невырезатьстарыйбизнес'),
 ('P10-D02','RW/Росавиация;P09/P06','Текущаяредакция12ГА/определениярелизов;reporting_flight_instance_id;carrier поУВД;возраст/boarding/no-show;правиломногоплечевогоRT','Историческоепервичноеопределениеесть;текущаяредакцияUNKNOWN','Преобразованиеjourneys/segmentsвотчётныхпассажиров;№2','MapperNULL;историческиесрезыкакpublished','Принятьметрикуиверсиюадаптера;контрпримерыодинрейс/дварейса/дубли/коды'),
 ('P10-D03','Росавиация/АК','ПолныйгодовойрейтингкаждойюридическойАК2025/2026/будущийгод;точныеDP/RWзначения','Top5namesи4цифрыесть;нижетоп5неполон;2026частичный','Точныйпорогобгона/промежуточныеместа/сменасоперника','НеобъявлятьточныйрангRW;будущиепорогиусловны','Совместимыйполныйсписок;согласованныйпериметрairlinevs group'),
 ('P10-D04','P05/P02/P02I','Маршрутныйспросипродуктыпоsegment/month;ценасдатой/as_of/booking_lead;конкуренты;новыедлярынка/перетокиотдругихроссийских/иностранных','ГодовойобщийрынокнеOD;P02offerнеadmissionphysicalseats','Реальныедополнительныепродажи,цена,знаменательдоли','Непридумыватьcapture/yield;P10net1толькодиагностика','Общийдопущенныйmarket/choice/inventorybundle;сезонныйцикл'),
 ('P10-D05','P04/RWфинансы/P06','ПомесячныйKEEPcash;openingunrestrictedcash;minimumcashbuffer;договорныедаты/ставкилизинга;capex/deposits;доступныйлимитликвидностииграфикпогашения','ПолнаяматрицаRWотсутствует','Пиковоефинансирование/размерступени/устойчивостьвсегобизнеса','PeakUNKNOWN;сохранятьфизическиедрайверыипорогликвидности','ДатированныеденежныесобытиявP06;проверитьсовместныйdeficit,несуммупиков'),
 ('P10-D06','P04/RWоперации/P03','Crewrostering/training по типам;ТО/двигатели/запчасти/восстановление;запуск/база/резерв/выход;стоимостьиспользования','РеференсныеценыP04неподтверждённыеставкиSJ100/PD8','Добавочныйрезультатиресурс;штат/надёжность','Не0;предельнодопустимыеcosts;actualparameterboundsUNKNOWN','AFM/кабина/контракты/ростер;одновременнаячувствительностьнесколькихполей'),
 ('P10-D07','P11/P09/P06','Пинэксперимента;eligiblecohort/control;order/coupon/boarding/service IDs;реализованныйnetuplift;расходыпроектирования/поддержки;payrollcashchange','P11неполучен;старыеd48bсценарныеточкинеизмеренныйэффект','Digitalпассажиры/маржа/cash;двойнойсчёт','NULL;недобавлятьзаказыксегментам;P06jointrecompute','ПринятьконтрольиостаточныйэффектпослевытесненияиP09dedup'),
 ('P10-D08','P02I/RWкоммерция','Двустороннийдопуск/слот/коридор/приёмтипа/страхование/MRO/расчёты/возвраты;expiry/as_of','БудущийдоступUNKNOWN;историческийрейснегарантия','Internationalпрограмма/доставка/возможностьадаптации','НеUNKNOWN=запрет;непродатьбездопуска','Датированныйaccesspassпокаждойпериоду/паре/режиму'),
 ('P10-D09','RW/лизингодатель/производитель','Передача/вводSJ100PD8иTu214поtail/date;кабина/crew/ТО/сертификация;потерянное/альтернативноезадание','4SJdiagnostic и11Tuannounced;годовойRWграфикUNKNOWN','Доступнаягодоваяёмкостьикэшобязательства','Сохранитьno_new/partial/delayed/phasedраздельно;Tu0maincase','Подписанныйсобственныйкалендарьпоvariant;приёмкапофактуготовности'),
 ('P10-D10','RW/туроператоры/P05/P04','Чартерныеблоки/маршруты/даты/места/гарантиинеттоцен;аванс/возврат/валюта/обеспечение/кредитныйриск','ПакетныепродажиВьетнамподтверждены;будущиеобъёмы/маржаUNKNOWN','Реальныйcharterрост/оборотныйкапитал/рискконцентрации','Неturnoperatoradvanceвприбыль;неСНГ/туристыкакOD','ДоговорисогласованныйdatedseatplanвобщемP06'),
]
write('dependency_requests.csv',[dict(dependency_id=a,owner=b,required_fields=c,current_state=d,decision_impact=e,current_treatment=f,acceptance_step=g,status='STAGE_B_PENDING_NOT_ECONOMIC_REJECTION') for a,b,c,d,e,f,g in dependencies])

road=[
 ('RM01','Дообязательств2027','P09+RWоперации+P04','ЗафиксироватьвесьKEEP;неперераспределятьбортбездонора/альтернативы','Принятый24месячныйKEEP;идентифицированыфактическиеtail-date/cashобязательства','НетKEEP илинепокрытыcash/crew/ТО','Сохранитьтекущиеобязательства;новыйпакетнеподписывать;закрытьнужныеполя','P10-D01;P10-D05;P10-D06','P10-KEEP-ANCHOR;P10-CASH'),
 ('RM02','2027H1','P05/P09/P06','Сравнитьновый/существующийхаб,базу,прямыеисмешанныйSJпутьоднимядром','Реальныйseasonalрынок,сопоставимыетарифы/booking_lead;единственноепродаваемоекреслонаflight/date','Положительныйвкладбезполныхзатрат/поддержки/денегнеявляетсяpass','СравнитьусловияфинансированияиэкономикуполногоPvsKEEP;недоказанныйвариантconditional','P10-D01;P10-D04','P10-NET;P10-CASH'),
 ('RM03','2027H1–H2','RW+P03/P04','ГотовитьпоставкиSJ100PD8посвоемуграфику,безновыхTu214восновнойветви','Естьhandover+induction+crew+ТО+operator/airportapproval+fundedcash','Одинкомпонентготовностипозжеобъявленнойдаты','Перейтикpartial/delayed/no_new;перепланироватьдообещанияпродаж;подписанныеобязательствасохранитьвcash','P10-D06;P10-D09','P10-DELIVERY;P10-TU0;P10-SEATS-SJ'),
 ('RM04','Передоткрытиемкаждоймеждународнойступени','RWкоммерция+P02I','Связатькоммерческийконтракт,доступиtypecalendar','Провереныдопускиобеихсторон/слоты/коридоры/обслуживание/расчётыидатапродаж','Недействующийдопуск/невозможностьобслуживания/отзывконтракта','Приостановитьновыепродажи;защититьужепроданных;сравнитьзаранеедопущенныеальтернативыипотери','P10-D08;P10-D10','P10-CASH;P10-DELIVERY'),
 ('RM05','2027H2','RWоперации+P09','Запуститьтолькодопущеннуюресурснуюступень;можетменьше8пар','Совместныйоперационный/коммерческий/cashpassпослебазовогоиосторожногосценариев','Фактическиеотмены/ремонт/продажисдвигаютпрогнознуюcashтраекторию','Адаптироватьчастоты/сезон/цепочкисценойдоноровивыхода;недержатьполныйзапускрадиформальногоколичествапар','P10-D01;P10-D04;P10-D06','P10-DELIVERY;P10-CASH'),
 ('RM06','Каждыймесяц2027–2028','RWфинансы+P04/P06','Обновлятьсовместныйcashforecastнаоставшийсягоризонт','Подтверждённыйдоступныйкнужнойдатефинансовыйлимит≥совместныйдефицит+обязательствавыхода','Договорнаяликвидностьнижетребуемойкдатеплатежа','Остановитьновыеобязательствадоэтойточки;выбратьменьшуюдопущеннуюступень;непродолжатьснеподтверждённойсубсидией','P10-D05;P10-D06;P10-D10','P10-CASH'),
 ('RM07','Зима/межсезонье/лето2027–2028','P05/P09+коммерция','Проверятьразныйспрос,цены,доступиответконкурентовпопродуктам','Подтверждённыеизмененияконкурентныхтарифов/частот/кресел/ownmigration','Порогрентабельностииликонверсияменяются;ростRPKнеравенростуpax','ПересчитатьединыйPиKEEP;неподгонятьyield;сравнитьфиксированнуюиадаптивнуюпрограммы','P10-D03;P10-D04','P10-C059;P10-CMIX;P10-REPORT'),
 ('RM08','2027–2028поплануP11','P11+P09/P06','Проверятьdigitalчерезконтрольныекогортыиdedup','Ростреализованныхnetboardings/остаточноймаржи;качество/возвраты;фактическиеизмененияcash','Нету причинногоэффекта/услугазадвоена/экономиявременинеменяетплатежи','Неучитыватьпассажирскийэффект;исправитьсвязкуevent;сохранитьпроверенныйсервисныйэффектотдельно','P10-D07','P10-DIGITAL;P10-REPORT'),
 ('RM09','Конец2028','Координатор+независимаяпроверка','Принять8–12уникальныхairportpairsосновногосценарияиподвестипервыйэтап','ПолныйгодовойPvsKEEP:reportedpax/share/result/cash;источники;прошедшийmapping','Тольконеделя/геометрия/тестыкодаилинетполногоKEEP','Оставитьстатусconditional/NOT_RUN;незаявлять№2;передатьточныепробелы','P10-D01;P10-D02;P10-D04;P10-D05;P10-D07','P10-METRIC;P10-CASH'),
 ('RM10','После2028;срок№2неустановлен','RWстратегия/финансы/операции','Расширятьпортфельрынковипаркпотипамприресурсе,спросеифинансировании','Порог№2(t)обновлёнпоиндивидуальнымАК;принятаследующаяступенька','Конкурентырастутбыстрее;нехваткасамолётов/экипажей/MRO/слотов/финансирования','Пересмотретьтемп/географию/размерступени;путьбезновыхTuсохраняется;незаявлятьдатуокупаемости','P10-D03;P10-D05;P10-D06;P10-D09','P10-YEARS;P10-C059;P10-CMIX'),
 ('RM11','НовыйTu214;годготовностиUNKNOWN','RW+P03/P04/P02I/P09','ОтдельнопроверитькаждыйдополнительныйTu214вдолгосрочномилидополнительномварианте','Собственнаякабина/AFM/crew/MRO/доступ/деньги/спрос;подписанныйtailcalendar','Естьтолькообъявление11илисертификатсистемы/производственныйплан','Неотноситькcommercialavailability;основнойSJпакетнеблокировать;сравнитьс0Tu','P10-D08;P10-D09','P10-TU0;P10-TU11;P10-SEATS-TUNEW'),
]
write('roadmap.csv',[dict(roadmap_id=a,period=b,owner=c,action=d,advance_signal=e,stop_or_revisit_signal=f,adaptation=g,dependency_ids=h,assumption_ids=i,version='P10-1.0-20261112',status='предложенныйусловныйплан') for a,b,c,d,e,f,g,h,i in road])

outcomes=[
 ('P10-G01','ИсходныйсамостоятельныйSJкейсбезновыхTu214','оценёнмасштабвсценариях;стратегияусловна','192помесячныхресурсныхстроки;4ветвипоставок;2производительности','Сеть/спрос/cashP09неготовы;капаситинеравенэффекту','resource_calendar_monthly.csv;growth_cases.csv','P10-D01;P10-D04;P10-D05'),
 ('P10-G02','УлучшитьрезультатдействующегобизнесабезновыхSJ/Tu','условнаиз-законкретныхнеизвестных','KEEPнеобнулён;рассмотреныпроизводительность/надёжность/частоты/чартерыконтрактно','Свободныйпарк/доноры/маржа/эффектнеизвестны;0новыхбортовне0всегобизнеса','existing_fleet_separate_types.csv;report.md','P10-D01;P10-D06;P10-D10'),
 ('P10-G03','Пакет11новыхTu214закрываетцель№2','оценёнвусловномполномбортогоде;экономическийвыборусловен','11Tu≈2.063млнзанятыхэтаповвбазовомдизайне;остаток9.037млнисторическогоразрыва','ЭтонедоказательствообщейнепригодностиTu;дата/спрос/финансированиеUNKNOWN','resource_frontier.csv;required_resources_by_type.csv','P10-D04;P10-D05;P10-D09'),
 ('P10-G04','Международныеичартерыкакчастьроста','условнаиз-задоступа/договоров/спроса/экономики','ПервичныеконкретныепримерыRWираздельнаярольB777/Tu/SSJ','СтрановойрынокнеOD;нетпринятых24месячныхконтрактов','report.md;roadmap.csv','P10-D04;P10-D08;P10-D10'),
 ('P10-G05','Digitalувеличиваетпассажирскийбизнес','условнаиз-заэкспериментальногоeffect/overlap','МостP11/P09поcohort/coupon/boarding/event;заказы/услуги/контактыразделены','НетP11pin;старыеусловныеupliftнеподтверждены','growth_bridge.json;metric_bridge_examples.csv','P10-D07'),
 ('P10-G06','Приравнятьgroupиairlineвцели№2','отклонёнспособизмеренияпозаданномупериметру','ПользовательвыбралиндивидуальнуюАК;AFgroupвключает3показанныхАК;UTgroupвертолёты','Пересмотрвозможенприизменениипостановки;неэкономическоеопровержениегрупповойстратегии','competitor_scale.csv;metric_dictionary.csv','P10-D02;P10-D03'),
 ('P10-G07','Считать13.8млннеизменнойбудущейлиниейобгона','оценёнконтроль+альтернативы;какединственныйпорогнепринят','0/.7/5.9%иразныетемпыАК;сменаносителяпорога','Небудущийполныйрейтинг;нужнарегулярнаясовместимаясверка','threshold_scenarios.csv;competitor_trajectories.csv','P10-D03'),
]
write('growth_hypothesis_outcomes.csv',[dict(hypothesis_id=a,hypothesis=b,outcome=c,evidence=d,scope_and_revisit=e,artifacts=f,dependency_ids=g,status_version='P10-1.0-20261112') for a,b,c,d,e,f,g in outcomes])

changes=[
 ('LC01','d48b4a4f86de29aa968665f1601b785bd1824c54','digital_growth/annual_carriers.csv','FAVT25primary_indexed','FAVT25rawprimarydownload','новоеизвлечение','Новаястраницасохранена,таблицавсехАКпо-прежнемунеполная'),
 ('LC02','d48b4a4f86de29aa968665f1601b785bd1824c54','digital_growth/sources.csv','AF25primary_republished','AF25_OFFICIALPDFскачан;AF26_OFFICIALновый12.11.2026','новыйисточник','Неизменяетстаруюпубликацию;новыйточныйsnapshot/hashes'),
 ('LC03','d48b4a4f86de29aa968665f1601b785bd1824c54','digital_growth/parameters.json','regionalbaseh10constant;cautioush8constant','baseh8..10сезонно;cautious6..8сезонно','новоесценарноеусловие','НЕкалибровка;сезонныйпрофильнеизвестен;год365/366иP03точныедаты'),
 ('LC04','d48b4a4f86de29aa968665f1601b785bd1824c54','digital_growth/parameters.json','TuLF.88,t3,h11,a.9','отдельныеexisting/newTu;h9..11;введёносторожныйдизайнLF.8,t4,h7..9,a.85','новоесценарноеусловие','НоваяRWкабинаUNKNOWN;194явныйаналог;дополнительнаяветвь0Tu'),
 ('LC05','d48b4a4f86de29aa968665f1601b785bd1824c54','digital_growth/parameters.json','B777t8,h13,a.85,LF.9','base t10,h11..13;осторожноt11,h9..11,a.8,LF.8','новоесценарноеусловие','Длинныйcharterнеранжируетсяпооднимкреслам;RWВьетнампути8ч40/10чконтекст,неblockкалибровка'),
 ('LC06','65cab12d2eae49dc91d1f77dd4860bc9bd7e20d2','strategy/whole_company_bridge.csv','исторический2025якорь+прежний2028segmentdiagnostic;futureKEEPUNKNOWN','ростотчётныхпассажировещёNULL;типовойадаптеррейс/этапиполныйKEEPобязательны','уточнениеметрики/интеграции','Старыйfrozenнепереписан;новыйP10непринимаетweekannualizationкакгодовойпрогноз'),
 ('LC07','d48b4a4f86de29aa968665f1601b785bd1824c54','digital_growth/parameters.json','условныеD01/D02/D03upliftиunitmargin','неподставленывP10wholebusiness;ожидаетсяP11pin/control/dedup','сохранениеграницыприёмки','Неэкономическийотказdigital;правильноеотделениеопытныхданныхотсценарныхточек'),
]
write('lineage_and_assumption_changes.csv',[dict(change_id=a,old_commit=b,old_source_path=c,old_input=d,new_treatment=e,change_kind=f,limitation=g) for a,b,c,d,e,f,g in changes])

coverage=[
 ('Полныйгод2025','РынокроссийскихАК','108.85млн;dom/int;top5','полныйгод,неполныйсписокиндивидуальныхАК','FAVT25'),
 ('Полныйгод2025','RW','2.7млнвесьбизнес;русскиетипы>2млн','нетмесячной/типовой/4businesscellsматрицы;точноебронирование/dates/leadUNKNOWN','RW25'),
 ('Полныйгод2024','RW','первичныйрелиз2.9млн','расхождениеверсийсRW25неустранено','RW24'),
 ('Доступный2026','RW','почти1млннаотечественныхтипах;публикация20.07','неполныйсрез;cutoffUNKNOWN;неполнаяАК','RW26H1'),
 ('Доступный2026','AFindividual/group','официальные10месяцевраздельно','неполныйгод;совместимыйпериодRWза10месяцевнеполучен','AF26_OFFICIAL'),
 ('2027–2028зима/лето/межсезонье','SJресурс','24месячныекалендари;P03entry;условныйseasonalh','некалиброваннаяистория;нетadmittedспроса/маршрутов/цен;notannualRWforecast','P03_DELIVERIES;P10-UTIL'),
 ('2027–2028цены','Всеproductmarkets','неподставленниодинвыдуманныйтариф','P05/P02нужныdate+as_of+booking_leadпоцене;P10неденежныйchoiceengine','P10-D04'),
 ('Историческаяместность','Рейс/этапметрика','скачанпервичныйсборникРосавиации,индексРосстата','действующая2026редакцияUNKNOWN;нуженадаптерподрелиз','FAVT_METHOD_HIST;STAT17'),
]
write('source_coverage.csv',[dict(period=a,scope=b,covered=c,uncovered=d,source_id=e) for a,b,c,d,e in coverage])

data=list(csv.DictReader((R/'threshold_scenarios.csv').open()))
series=[]
labels={'C_FLAT':'Масштаб сохраняется','C_SLOW007':'Общий рост 0,7%','C_RECOVERY059':'Общий рост 5,9%','C_MIXED_HISTORY':'Разные темпы авиакомпаний'}
for cid,label in labels.items():
    series.append(dict(id=cid,label=label,points=[{'year':int(x['year']),'pax':float(x['threshold_reported_pax'])/1e6,'carrier':x['threshold_carrier_under_condition']} for x in data if x['competition_scenario_id']==cid]))
html='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Условный порог №2</title><style>
:root{color-scheme:light dark;font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--foreground,#24303f)}body{margin:0}h2{font-size:19px;margin:0 0 8px}p{margin:8px 0;color:var(--muted-foreground,#697587)}svg{display:block;width:100%;height:310px;overflow:visible}.controls{display:flex;gap:12px;flex-wrap:wrap}button{font:inherit;padding:6px 10px;border:1px solid var(--border,#b6bec7);border-radius:5px;background:transparent;color:inherit;cursor:pointer}button[aria-pressed=true]{border-color:var(--primary,#2c6cc5);color:var(--primary,#2c6cc5)}text{fill:currentColor;font-family:inherit;font-size:12px}.axis{stroke:var(--border,#b6bec7)}.note{font-size:12px}
</style><h2>Условный порог №2 среди отдельных авиакомпаний</h2><div class="controls" id="controls"></div><svg viewBox="0 0 680 310" role="img" aria-label="Сценарии годового порога пассажиров до 2035 года"><g id="chart"></g></svg><p id="readout"></p><p class="note">Старт: Победа — 13,8 млн, Red Wings — 2,7 млн за 2025. Годы 2030 и 2035 — ориентиры масштаба; срок №2 не установлен. Линия показывает сценарные условия, не прогноз. Источники: Росавиация, Аэрофлот, Победа, Россия; P10-1.0-20261112.</p><script>
const series=DATA;
const colors=['var(--primary,#2c6cc5)','var(--success,#318266)','var(--warning,#bb7b20)','var(--info,#8d5db4)'];
const svg=document.getElementById('chart'),rootSvg=svg.ownerSVGElement,controls=document.getElementById('controls');let selected=3;
function draw(){const s=series[selected],w=Math.max(320,rootSvg.clientWidth),x=y=>60+(y-2025)/10*(w-85),y=v=>260-(v-10)/16*230;rootSvg.setAttribute('viewBox',`0 0 ${w} 310`);let h='';for(let n=10;n<=26;n+=4){h+=`<path class="axis" d="M60 ${y(n)}H${w-25}" opacity=".45"/><text x="15" y="${y(n)+4}">${n} млн</text>`;}for(const n of [2025,2028,2030,2035])h+=`<text x="${x(n)}" y="287" text-anchor="middle">${n}</text>`;h+=`<polyline fill="none" stroke="${colors[selected]}" stroke-width="3" points="${s.points.map(p=>`${x(p.year)},${y(p.pax)}`).join(' ')}"/>`;for(const p of s.points)h+=`<circle cx="${x(p.year)}" cy="${y(p.pax)}" r="4" fill="${colors[selected]}"/><text x="${x(p.year)}" y="${y(p.pax)-13}" text-anchor="middle">${p.year===2027?'':p.pax.toFixed(2)}</text>`;svg.innerHTML=h;document.getElementById('readout').textContent=s.label+'. В 2030: '+s.points[3].carrier+', '+s.points[3].pax.toFixed(2)+' млн; в 2035: '+s.points[4].carrier+', '+s.points[4].pax.toFixed(2)+' млн.';Array.from(controls.children).forEach((b,i)=>b.setAttribute('aria-pressed',String(i===selected)));}
series.forEach((s,i)=>{const b=document.createElement('button');b.textContent=s.label;b.onclick=()=>{selected=i;draw()};controls.appendChild(b)});draw();new ResizeObserver(()=>draw()).observe(rootSvg);
</script></html>'''.replace('DATA',json.dumps(series,ensure_ascii=False))
(R/'scale_chart.html').write_text(html,encoding='utf-8')
print(json.dumps({'dependencies':len(dependencies),'roadmap_steps':len(road),'hypotheses':len(outcomes),'chart':'scale_chart.html'},ensure_ascii=False))
