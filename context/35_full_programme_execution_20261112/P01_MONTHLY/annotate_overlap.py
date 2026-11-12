#!/usr/bin/env python3
from pathlib import Path
import csv,json,re,hashlib
p=Path(__file__).resolve().parent
def read(f):return list(csv.DictReader((p/f).open()))
def write(f,rs):
 with (p/f).open('w',newline='') as o:w=csv.DictWriter(o,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
rs=read('airport_pair_segment_observations.csv')
for r in rs:
 r['overlap_group_id']=r['origin_code']+'-'+(r['destination_code'] or r['destination_name_original'])+'-'+r['period_start'][:4];r['calibration_status']='CONDITIONAL_SEGMENT_ONLY';r['airport_mapping_status']='MOW_NOT_AIRPORT' if r['destination_code']=='MOW' else 'REQUIRES_P05_AIRPORT_BINDING' if 'CONDITIONAL' in r['destination_kind'] or not r['destination_code'] else 'NAMED_AIRPORT_MAPPING_PM_A09'
for r in rs:
 rawlines=(p/'sources_receipts'/(r['source_id']+'.txt')).read_text().splitlines();match=re.search(r'[.]txt:(\d+)',r['source_row_id']);line_no=int(match[1]) if match else None
 if line_no is None:
  n=int(r['value'])
  for i,line in enumerate(rawlines,1):
   compact=re.sub(r'\s','',line)
   if str(n) in compact or (format(n/1000,'g').replace('.',',')+'тыс' in compact.replace('.','')) or (format(n/1000000,'g').replace('.',',')+'млн' in compact):line_no=i;break
 if line_no is None:raise ValueError(('Missing source row',r['observation_id']))
 r['source_row_id']=r['source_id']+'.txt:'+str(line_no)+'#'+r['observation_id'];r['source_row_sha256']=hashlib.sha256(rawlines[line_no-1].encode()).hexdigest()
write('airport_pair_segment_observations.csv',rs)
kf=read('calibration_eligibility.csv')
for r in kf:
 r['additional_primary_observation_ids']=';'.join(x['observation_id'] for x in rs if x['origin_code']==r['from_iata'] and x['destination_code']==r['to_iata'] and x['period_start']==r['period_start'] and x['period_end']==r['period_end']);r['overlap_group_id']=r['from_iata']+'-'+r['to_iata']+'-2025';r['assumption_ids']=';'.join(dict.fromkeys(r['assumption_ids'].split(';')+['PM-A13']))
write('calibration_eligibility.csv',kf)
a=[r for r in read('assumptions.csv') if r['assumption_id']!='PM-A13'];a.append(dict(assumption_id='PM-A13',assumption='Вложенные периоды и доли перевозчиков не независимые наблюдения',owner_reason='Исследователь P01; год/Q1/месяц и группа/все перевозчики перекрываются',range_or_unknown='Новых числовых весов нет; степень независимости определяется покрытием',impact_and_how_to_refine='P05 выбирает уровни fit/контроля и отложенные пары/периоды до оценки; KF031 и KUF2025-MRV не складывать и не считать двумя независимыми случаями',application='Использовать overlap_group_id; годовые и месячные пассажиры не суммировать друг с другом'));write('assumptions.csv',a)
x=[r for r in read('granularity_crosswalk.csv') if r['granularity']!='airport_period_block']
for r in x:
 if r['granularity']=='endpoint_od':r['limitations']='В текущем пакете подтверждённых строк конечных OD нет'
x.append(dict(granularity='airport_period_block',grain='Аэропорт или пара × опубликованный блок месяцев',numerator='Пассажиры за Q1/H1/лето/год по определению издателя',eligible_use='Контроль масштаба только соответствующего блока',limitations='Летние три месяца не один месяц; Top10 не полный список; вложенные блоки не независимы',assumption_ids='PM-A07;PM-A12;PM-A13'));write('granularity_crosswalk.csv',x)
s=json.loads((p/'monthly_summary.json').read_text());s.update(known_flows_qualified=37,assumptions_count=len(a));(p/'monthly_summary.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
