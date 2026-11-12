"""Readable metadata only. Original sources, pinned rows, IDs and hashes stay exact."""
import csv,json,re
from extract_local import ROOT

def spacing(value):
 if not isinstance(value,str) or value.startswith(('http://','https://')):return value
 value=re.sub(r'(?<=[а-яё])(?=[A-Za-z0-9])',' ',value)
 value=re.sub(r'(?<=[A-Za-z0-9])(?=[А-Яа-яЁё])',' ',value)
 value=re.sub(r'([,;])(?=[А-Яа-яЁёA-Za-z])',r'\1 ',value)
 replacements={'техже':'тех же','томуже':'тому же','неподтверждён':'не подтверждён','неустановлен':'не установлен','неизменялись':'не изменялись','иззадефицитаресурса':'из-за дефицита ресурса','всепериоды':'все периоды','нескладывать':'не складывать','неприменять':'не применять','непереносить':'не переносить','необнулять':'не обнулять','неподставляется':'не подставляется','потерядоноров':'потеря доноров','свободнымпарком':'свободным парком','негодовой':'не годовой','независимыескоринги':'независимые скоринги','публичныедокументы':'публичные документы','общиефайлы':'общие файлы','новаябаза':'новая база','новойбазы':'новой базы','новыхбортов':'новых бортов','текущаябаза':'текущая база','проектнаясеть':'проектная сеть','годоваясеть':'годовая сеть','годовоерасписание':'годовое расписание','физическиеплечи':'физические плечи','реальныехвосты':'реальные хвосты','цены20':'цены 20','нетфинального':'нет финального','нефинальнаяэкономика':'не финальная экономика','завершённыйпакет':'завершённый пакет','готовксведениюкоординатором':'готов к сведению координатором','проверкилокальные':'проверки локальные','текущаяроль':'текущая роль','неоперационныйдопуск':'не операционный допуск','допринятияобщегокалендаря':'до принятия общего календаря','готовностьпаспорта':'готовность паспорта','проверкаcrew':'проверка crew','не проверкаcrew':'не проверка crew'}
 for a,b in replacements.items():value=value.replace(a,b)
 return value
SKIP={'source_id','source_row_id','source_row_sha256','source_blob_sha256','source_sha256','source_segments','source_url','source_locator','programme_id','programme_ids','flight_instance_id','arrival_leg_id','departure_leg_id','assumption_id','assumption_ids','ancestorIDs','source_pins','output_directory','path','extract_path','sha256','source_git_blob','source_path','source_commit','segments_json','observed_competition'}
def walk(o,key=''):
 if key in SKIP:return o
 if isinstance(o,dict):return {k:walk(v,k) for k,v in o.items()}
 if isinstance(o,list):return [walk(x,key) for x in o]
 return spacing(o)
def write(name,o):(ROOT/name).write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

def main():
 for name in ['case.json','hypotheses.json','programme_candidates.json','readiness.json','handoff.json','resource_diagnostic.json','connection_candidates.json','throughstop_observations.json']:
  write(name,walk(json.loads((ROOT/name).read_text())))
 for name in ['assumptions.csv','evidence.csv','market_deltas.csv','comparison_requests.csv','local_reference_rates.csv','programme_monthly_spec.csv']:
  path=ROOT/name
  with path.open() as f:r=csv.DictReader(f);fields=r.fieldnames;rows=[{k:v if k in SKIP else spacing(v) for k,v in row.items()} for row in r]
  with path.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 hand=json.loads((ROOT/'handoff.json').read_text())
 hand['write_boundary']='Запись только в context/35_full_programme_execution_20261112/variants/VVO/research_v1/. Git и общие файлы не менялись; координатор получает manifest и сам решает, что коммитить.'
 hand['main_conclusion']='VVO остаётся условным кандидатом. Действующая база RW не подтверждена; объявленную региональную программу 2022 года отменили из-за дефицита ресурса в существующей сети. Построены R1, парные R2/H2, альтернативное использование тех же бортов в SVX, партнёрский и международный варианты. Экономического победителя нет.'
 hand['known_unknowns']='Открыты 12 адресных запросов Stage B. Не приняты спрос/выбор, реальные хвосты и резерв, crew/ТО/слоты, договорные затраты и график денег. Stage A не является итоговой стратегией.'
 hand['prohibitions']=['Не превращать SU/HZ/FV-ярлыки и collision groups в физические кресла.','Не считать IO-106 VVO–IKT беспосадочным.','Не считать объявленные в2022 три SSJ свободным парком.','Не умножать диагностическую неделю на52.','Не назначать RW скидки2026 по историческим порогам без доказанной применимости.','Не складывать результаты независимых денежных моделей.']
 hand['new_high_value_evidence'].append('В перечне Росавиации2026 уже есть BQS–UUS Авроры:8460 RUB за направление. Это контроль H2; не датированная цена с20кг. Геометрический путь черезVVO в1.493раза длиннее прямого.')
 hand['coordinator_action']='Сначала проверить source pins, README.txt, case.json и requests. Для общего расчёта принять версии P03/P04/P05, собрать полные P/KEEP-bundles P06 и пересчитать совместную сеть. VVO-компонент даёт3–4 внутренние пары; общий целевой размер8–12 не является требованием наполнить их одним городом.'
 hand['reproduce_offline']=['python3 build_package.py','python3 programmes.py','python3 finalize_package.py','python3 polish_outputs.py','python3 verify_and_seal.py']
 hand['early_tranche_note']='Ранее координатору отправлен транш604d413f676945d5c5e4442aef9b821522d976b581f1b047ac6ac9bf191ed184; его не редактировали. В итоговом пакете появились E34–E36, новые расписания и проверки.'
 write('handoff.json',hand)
 case=json.loads((ROOT/'case.json').read_text())
 case['programme_selection_reason']='R1 проверяет компактный ресурс: две короткие региональные пары BQS/UUS и западное плечо HTA. R2 добавляет PKC как более дальнее островное направление с летним сигналом. H2 изолирует эффект времени и защиты на тех же рейсах. Это набор различающих опытов, а не отбор по доказанной доходности.'
 case['unselected_markets']={'KHV':'617км и25 групп в ноябрьской выборке сохраняются как конкуренция и партнёрский источник. Действующий конкурент или расстояние сами по себе не отсекают рынок. Отдельная собственная программа KHV здесь не оценивалась; её можно получить заменой оборотов после общей калибровки.','IKT/UUD/YKS':'Существующее предложение описано и передано как возможный источник партнёрского/прямого продукта. Отдельные базовые программы в этом пакете не считались; это не экономическое отклонение.'}
 case['core_transfer_counterexample']='Прямой BQS–UUS у Авроры есть в регуляторном перечне2026 (строка14,8460 RUB). ЧерезVVO геометрия длиннее в1.493раза. Перед выбором H2 нужны даты/частоты/доступность/полная цена прямой альтернативы и возможность обратной поездки. Не считать этот OD незанятым.'
 case['ground_handling_reference']='В опубликованном графике по приказу134 от22.02.2022 Су95 включён в55-минутный оборот ВВЛ–ВВЛ и70-минутный ВВЛ–МВЛ. Domestic planning60мин имеет локальную опору, но удалённые аэропорты, договор RW и SJ100/ПД-8 не подтверждены.'
 case['RW_role']['current']='UNKNOWN: не подтверждены действующая база/хаб, свободные борта и договоры RW. Полная современная роль outstation также не установлена.'
 case['RW_role']['historical']='20.01.2022 объявлено будущее базирование3SSJ100;15.05 региональная программа отменена из-за нагрузки на парк;30.05 пассажиров LED–VVO переводили на SU. Ни один из этих источников не доказывает действующую базу2026.'
 case['segments']={'деловые_корпоративные':'ВЭФ подтверждает событийное окно с общим потоком94тыс операций аэропорта. Число делегатов, дополнительный поток, цели обычных пассажиров и гарантированные договорные объёмы UNKNOWN.','туристические':'Летний пик внутренних перевозок, летняя программа LED и зимние Китай/ЮВА — основания для проверки сезонных продуктов. Доли туристов и цель поездки в OD не измерены.','семейные_личные':'Размер и доля VFR/семейных поездок не установлены. Договорный спрос и веса сегментов не назначены.','business_day_returns':'На HTA/PKC не обещан ежедневный деловой возврат. Сетка проверяется по длительности2/3/4/7ночей в обе стороны, затем по общему P05 trip-duration.'}
 case['price_coverage']['regulatory_tariffs']='BQS–VVO6807, VVO–HTA12936, VVO–UUD13068, BQS–UUS8460 RUB за направление по перечню2026. Это регуляторные специальные тарифы, не датированные20кг котировки и не поддержка RW2028.'
 write('case.json',case)
 # Aliases make field ownership explicit without changing programme IDs.
 p=json.loads((ROOT/'programme_candidates.json').read_text())
 for r in p['programmes']:
  r['source_id']=';'.join(r['sources'])
  if r['programme_id'] in ['P-VVO-PARTNER','P-VVO-I1'] and 'VVO-A15' not in r['assumption_ids']:r['assumption_ids'].append('VVO-A15')
 write('programme_candidates.json',p)
 h=json.loads((ROOT/'hypotheses.json').read_text())
 for r in h['hypotheses']:r['source_id']=';'.join(r['source'])
 write('hypotheses.json',h)
 index=json.loads((ROOT/'source_index.json').read_text())
 with (ROOT/'evidence.csv').open() as f:ev=list(csv.DictReader(f))
 for r in index['public_sources']:
  sid=r['source_id'];associated=[e for e in ev if e['source_id']==sid]
  r['organisation']=associated[0]['organisation'] if associated else ('АО «Международный аэропорт Владивосток»' if sid.startswith('VVO_') else 'OurAirports / David Megginson' if sid=='COORDINATES' else 'UNKNOWN; только попытка доступа')
  r['publication_date']=';'.join(sorted({e['publication_date'] for e in associated if e['publication_date']!='UNKNOWN'})) or 'UNKNOWN'
  r['period']=';'.join(sorted({e['period'] for e in associated})) or (sid.split('_')[2] if sid.startswith('VVO_API_') else 'снимок2026-11-12; конкретная применимость в таблицах')
  r['unit']=';'.join(sorted({e['unit'] for e in associated})) or ('строка опубликованного расписания' if sid.startswith('VVO_API_') else 'WGS84 degrees' if sid=='COORDINATES' else 'исходный документ/попытка получения')
  r['granularity']='airport VVO × date × source label; не физический inventory' if sid.startswith('VVO_API_') else ';'.join(sorted({e['granularity'] for e in associated})) or 'документ/справочный набор'
  r['coverage']='Частичное покрытие VVO; факты только в указанном периоде. Отсутствие или ошибка доступа не означает нулевой рынок. Внутренние договоры RW, полный OD и физический инвентарь этим источником не устанавливаются.'
  r['as_of']='2026-11-12'
 write('source_index.json',index)
 print('Метаданные отредактированы; исходные строки/файлы/ID/hash не изменены.')

if __name__=='__main__':main()
