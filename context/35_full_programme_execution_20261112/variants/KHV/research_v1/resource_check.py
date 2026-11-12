"""Геометрическая диагностика проектных цепочек, не новый экономический движок."""
import pathlib,json,csv,datetime,hashlib
R=pathlib.Path(__file__).parent
P=json.loads((R/'programme_candidates.json').read_text())['programmes']
g={(r['origin'],r['destination']):r for r in csv.DictReader((R/'geometry_diagnostics.csv').open())}
def block(a,b,mode):
 r=g.get((a,b),g.get((b,a)))
 return None if r is None else int(r[mode])
rotations={
'KHV-R1':[(1,[1,3,5],['KHV','UUD','KHV']),(1,[2,4,6,7],['KHV','UUS','KHV'])],
'KHV-H2':[(1,[1,4],['KHV','UUD','KHV','UUS','KHV']),(2,[1,4],['KHV','UUS','KHV','UUD','KHV']),(1,[2,5],['KHV','HTA','KHV','GDX','KHV']),(2,[2,5],['KHV','GDX','KHV','HTA','KHV'])],
'KHV-D2':[(1,[1,2,4,5],['UUD','UUS','UUD']),(2,[1,2,4,5],['HTA','GDX','HTA'])],
'KHV-E1':[(1,[1,3,5],['SVX','IKT','KHV']),(1,[2,4,6],['KHV','IKT','SVX'])]
}
rows=[];checks=[]
for pid,rots in rotations.items():
 weekly={}
 for tail,days,path in rots:
  for d in days:
   legs=list(zip(path,path[1:]));counts=[]
   for key in ['block_analogue_minutes','block_grid_low_minutes','block_grid_high_minutes']:
    counts.append(sum(block(a,b,key) for a,b in legs))
   rows.append(dict(programme_id=pid,working_tail_placeholder=tail,iso_weekday=d,rotation='>'.join(path),legs=len(legs),block_proxy_minutes=counts[0],proxy_low_minutes=counts[1],proxy_high_minutes=counts[2],turn_between_legs_minutes=60*(len(legs)-1),unit='minutes/diagnostic_day;notcrew_duty',period='representative_week_after_service_entry;notyear',coverage='greatcircleproxy;noUTCslots/crew/ТО/admission',status='geometry_only',source_id='GEOMETRY_airports;programme_candidates.json',assumption_id='A-KHV-03;A-KHV-04;A-KHV-05;A-KHV-10;A-KHV-11'))
   for a,b in legs:weekly[(a,b)]=weekly.get((a,b),0)+1
 p=next(x for x in P if x['programme_id']==pid)
 declared={}
 for x in p['legs']:
  a,b=x['origin_airport'],x['destination_airport'];f=x['roundtrips_per_week'];declared[a,b]=f;declared[b,a]=f
 checks.append(dict(programme_id=pid,frequency_conservation=declared==weekly,weekly_leg_instances=sum(weekly.values()),weekly_block_proxy_minutes=sum(x['block_proxy_minutes'] for x in rows if x['programme_id']==pid),working_tail_placeholders=p['working_aircraft_required'],reserve_admission='UNKNOWN',location_continuity='within_rotations;E1_nextdayreturn;D2external_access_unresolved',verdict='CONSISTENT_FRAGMENT_NOT_OPERATIONALLY_ADMITTED'))
with (R/'resource_diagnostics.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
# Two-tail bank timing under proxy; arbitrary start time moves both tails jointly.
banks=[]; corrected=[]
for west,east in [('UUD','UUS'),('HTA','GDX')]:
 bw=block('KHV',west,'block_analogue_minutes');be=block('KHV',east,'block_analogue_minutes')
 arrwest=6*60+2*bw+60;arreast=8*60+2*be+60
 dep=max(arrwest,arreast)+75
 banks.append(dict(west=west,east=east,west_arrival_KHV_minutes_since_midnight=arrwest,east_arrival_KHV_minutes_since_midnight=arreast,both_onward_departures_KHV_minutes=dep,west_to_east_connect_minutes=dep-arrwest,east_to_west_connect_minutes=dep-arreast,window75_180_met=75<=dep-arrwest<=180 and 75<=dep-arreast<=180,source_id='GEOMETRY_airports',assumption_id='A-KHV-05;A-KHV-06;A-KHV-11',status='scenario_clock_construction_not_accepted_MCT'))
 corrected.append(dict(west=west,east=east,target_arrival_KHV_minutes=810,west_departure_KHV_minutes=810-2*bw-60,east_departure_KHV_minutes=810-2*be-60,both_onward_departures_KHV_minutes=885,connection_minutes_each_direction=75,window75_180_met=True,source_id='GEOMETRY_airports',assumption_id='A-KHV-05;A-KHV-06;A-KHV-11;A-KHV-28',status='corrected_scenario_clock_construction_not_MCT_or_slot_admission'))
(R/'resource_checks.json').write_text(json.dumps(dict(checks=checks,naive_bank_time_counterexamples=banks,corrected_bank_time_examples=corrected,limitations=['Формулы частот и цепочек согласованы;операционная приёмка NOT_RUN','600/700/800кмч и18/24/36мин—контрольная сетка геометрического аналога;не опубликованные характеристики типа и не вероятностный интервал','Начала банков06:00/08:00 KHV—сценарные часы для проверки пересечения;слотов/crew не подтверждают','Требуются точные UTC,flight IDs,crew relay,ТО,reserve,подводкаD2изопорнойсети','Никакой P06 toy не объявлен RW результатом'],status='DIAGNOSTIC_ONLY'),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(checks,ensure_ascii=False));print(json.dumps(corrected,ensure_ascii=False))
