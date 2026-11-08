#!/usr/bin/env python3
"""Reproduce a provisional city screen and physical network sketch; no demand fit.

Python 3 standard library only. Run from any directory. Sources are frozen inputs;
rerunning does not overwrite research evidence or contact external services.
"""
import copy
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'context/11_practical_screening'
DATA = json.loads((OUT / 'inputs.json').read_text())
SOURCES = json.loads((OUT / 'sources.json').read_text())
GEO = json.loads((OUT / 'coordinates.json').read_text())
A = {r['iata']: r for r in GEO}
CRITERIA = list(DATA['weights']['base'])


def distance(a, b):
    x, y = map(math.radians, (A[a]['lat'], A[a]['lon']))
    v, w = map(math.radians, (A[b]['lat'], A[b]['lon']))
    return 12742 * math.asin(min(1, math.sqrt(math.sin((v-x)/2)**2 +
                    math.cos(x)*math.cos(v)*math.sin((w-y)/2)**2)))


def clamp(x):
    return max(0, min(100, x))


def csv_out(name, rows):
    if not rows:
        return
    with (OUT / name).open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def md_table(headers, rows):
    def cell(v):
        return str(v).replace('|', '/').replace('\n', ' ')
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                      '| ' + ' | '.join(['---'] * len(headers)) + ' |'] +
                     ['| ' + ' | '.join(map(cell, r)) + ' |' for r in rows])


def calculate_cities(ceiling=None):
    g = DATA['geography']
    ceiling = ceiling or g['detour_ceiling']
    pairs = [(x,y) for x in g['north'] for y in g['south']] + \
            [(x,y) for x in g['east'] for y in g['east_south']]
    rows, details = [], []
    for c in DATA['cities']:
        h = c['iata']
        values = []
        for x,y in pairs:
            d1,d2,d0 = distance(x,h),distance(h,y),distance(x,y)
            ratio = (d1+d2)/d0
            usable = g['min_leg_km'] <= d1 <= g['max_leg_km'] and \
                     g['min_leg_km'] <= d2 <= g['max_leg_km']
            value = max(0,min(1,(ceiling-ratio)/(ceiling-1))) if usable else 0
            values.append(value)
            details.append(dict(hub=h,origin=x,destination=y,leg1_km=round(d1,2),
                                leg2_km=round(d2,2),detour=round(ratio,5),
                                geometry_value=round(value,5)))
        coverage = sum(values)/len(values)*100
        distinct = clamp(min(distance(h,'DME'),distance(h,'SVX')) /
                         g['distance_scale_km'] * 100)
        row = dict(iata=h,city=c['city'],market=clamp((c['population_thousands']-500)/10),
                   competition=sum(c['competition_interval'])/2,
                   geography=.75*coverage+.25*distinct,
                   technical=sum(c['technical_interval'])/2,
                   basing=sum(c['basing_interval'])/2,
                   coverage=coverage,distance_existing_min_km=min(distance(h,'DME'),distance(h,'SVX')),
                   new_node=c.get('new_node',True))
        lo,hi=0,0
        for k,w in DATA['weights']['base'].items():
            interval=c.get(k+'_interval',[row[k],row[k]])
            lo += w*interval[0];hi += w*interval[1]
        row['interval_low']=lo;row['interval_high']=hi
        rows.append(row)
    return rows,details


def rank(rows, weights, new_only=False):
    result = [dict(r,score=sum(weights[k]*r[k] for k in CRITERIA))
              for r in rows if not new_only or r['new_node']]
    return sorted(result,key=lambda r:(-r['score'],r['iata']))


def hhmm(minutes):
    return f'{int(minutes)//60:02d}:{int(minutes)%60:02d}'


N = DATA['network_assumptions']


def block(a,b,speed=None,overhead=None):
    return math.ceil((distance(a,b)/(speed or N['speed_kmh']) +
                      (N['block_overhead_hours'] if overhead is None else overhead))*60)


def build_networks(speed=None,overhead=None,turn=None,use_slack=True):
    turn=N['turn_minutes'] if turn is None else turn
    legs=[]
    hub=rank(cities,DATA['weights']['base'],True)[0]['iata']
    for day in range(1,7):
        for index,pair in enumerate(DATA['hub_pairs'],1):
            morning,afternoon = pair if day%2 else pair[::-1]
            b1=block(hub,morning,speed,overhead);b2=block(hub,afternoon,speed,overhead)
            arrival=N['hub_arrival_utc_minute'];departure=N['hub_departure_utc_minute']
            schedule=[(hub,morning,arrival-2*b1-turn,arrival-b1-turn),
                      (morning,hub,arrival-b1,arrival),
                      (hub,afternoon,departure,departure+b2),
                      (afternoon,hub,departure+b2+turn,departure+2*b2+turn)]
            for a,b,start,end in schedule:
                legs.append(dict(network='A',day=day,aircraft=f'A{index}',origin=a,destination=b,
                                 departure_utc_minute=start,arrival_utc_minute=end,
                                 block_minutes=end-start,ferry=False))
        for index,cycle in enumerate(DATA['direct_cycles'],1):
            route=list(cycle if day%2 else cycle[::-1])
            if use_slack and index==2 and day<=4:
                pos=route.index('GSV')
                route=route[:pos+1]+['AER','GSV']+route[pos+1:]
            t=N['direct_start_utc_minute']
            for a,b in zip(route,route[1:]):
                bt=block(a,b,speed,overhead)
                legs.append(dict(network='B',day=day,aircraft=f'B{index}',origin=a,destination=b,
                                 departure_utc_minute=t,arrival_utc_minute=t+bt,
                                 block_minutes=bt,ferry=False))
                t+=bt+turn
            # Independent B reinforcement uses its own available working day,
            # without adding GOJ or a new base. It is a supply scenario, not
            # a claim that extra seats on these legs will sell.
            extra=[]
            if use_slack and index==3:
                extra=[('SVX','OMS'),('OMS','SVX')]
            for a,b in extra:
                bt=block(a,b,speed,overhead)
                legs.append(dict(network='B',day=day,aircraft=f'B{index}',origin=a,destination=b,
                                 departure_utc_minute=t,arrival_utc_minute=t+bt,
                                 block_minutes=bt,ferry=False))
                t+=bt+turn
    violations=[];daily=defaultdict(list)
    for r in legs:daily[(r['network'],r['day'],r['aircraft'])].append(r)
    for key,rs in daily.items():
        rs=sorted(rs,key=lambda r:r['departure_utc_minute'])
        for left,right in zip(rs,rs[1:]):
            if left['destination']!=right['origin']:violations.append([*key,'spatial_discontinuity'])
            if left['arrival_utc_minute']+turn>right['departure_utc_minute']:violations.append([*key,'turn_conflict'])
        if rs[0]['origin']!=rs[-1]['destination']:violations.append([*key,'overnight_not_base'])
        if rs[0]['departure_utc_minute']<0 or rs[-1]['arrival_utc_minute']>=1440:violations.append([*key,'crosses_utc_day'])
        if sum(r['block_minutes'] for r in rs)>N['max_daily_block_hours']*60:violations.append([*key,'daily_block_limit'])
        if rs[-1]['arrival_utc_minute']-rs[0]['departure_utc_minute']>N['max_aircraft_day_span_hours']*60:violations.append([*key,'aircraft_day_span'])
    return hub,legs,violations


def network_summary(legs):
    out=[]
    for net in ['A','B']:
        rs=[r for r in legs if r['network']==net]
        daily=defaultdict(list)
        for r in rs:daily[(r['day'],r['aircraft'])].append(r)
        maximum=max(sum(r['block_minutes'] for r in s) for s in daily.values())/60
        spans=[max(r['arrival_utc_minute'] for r in s)-min(r['departure_utc_minute'] for r in s) for s in daily.values()]
        hours=sum(r['block_minutes'] for r in rs)/60
        seats=len(rs)*N['seats']
        out.append(dict(network=net,routes=len({tuple(sorted([r['origin'],r['destination']])) for r in rs}),
                        weekly_legs=len(rs),weekly_block_hours=round(hours,2),weekly_seats=seats,
                        daily_block_max=round(maximum,2),day_span_max=round(max(spans)/60,2),
                        hour_lower_bound_active=math.ceil(hours/(6*N['max_daily_block_hours'])),
                        constructed_active=len({r['aircraft'] for r in rs}),spares=N['spare_aircraft'],
                        weekly_pax_segments_lf55=round(seats*N['lf_low']),
                        weekly_pax_segments_lf80=round(seats*N['lf_high'])))
    return out


def connections(legs,hub):
    out=[]
    for day in range(1,7):
        inbound=[r for r in legs if r['network']=='A' and r['day']==day and r['destination']==hub]
        outbound=[r for r in legs if r['network']=='A' and r['day']==day and r['origin']==hub]
        for a in inbound:
            for b in outbound:
                wait=b['departure_utc_minute']-a['arrival_utc_minute']
                if a['origin']!=b['destination'] and N['connection_min_minutes']<=wait<=N['connection_max_minutes']:
                    out.append(dict(day=day,origin=a['origin'],hub=hub,destination=b['destination'],
                                    arrival_utc=hhmm(a['arrival_utc_minute']),departure_utc=hhmm(b['departure_utc_minute']),
                                    wait_minutes=wait,
                                    detour=round((distance(a['origin'],hub)+distance(hub,b['destination']))/distance(a['origin'],b['destination']),3),
                                    status='POTENTIAL_NOT_MCT_OR_SALES_VERIFIED'))
    return out


cities,geo_details=calculate_cities()
ranking=[]
for label,weights in DATA['weights'].items():
    for scope in ['all','new_node']:
        for n,r in enumerate(rank(cities,weights,scope=='new_node'),1):
            ranking.append(dict(weights=label,scope=scope,rank=n,**{k:round(v,4) if isinstance(v,float) else v for k,v in r.items()}))
csv_out('ranking.csv',ranking)
csv_out('geography_pairs.csv',geo_details)
csv_out('city_matrix.csv',[{**c,'population_source':'POP-2' if c['iata'] in ['GSV','TJM'] else 'POP-1',
                            'sources':';'.join(c['sources']),
                            'competition_interval':json.dumps(c['competition_interval']),
                            'technical_interval':json.dumps(c['technical_interval']),
                            'basing_interval':json.dumps(c['basing_interval'])} for c in DATA['cities']])

sensitivity=[]
def add_case(label,rows):
    for scope in ['all','new_node']:
        rr=rank(rows,DATA['weights']['base'],scope=='new_node')
        sensitivity.append(dict(case=label,scope=scope,top3=' > '.join(r['iata'] for r in rr[:3]),
                                scores='; '.join(f"{r['iata']}={r['score']:.2f}" for r in rr[:3])))
add_case('baseline_midpoints',cities)
for code,criterion,value,label in [
    ('UFA','technical',100,'UFA_technical_confirmed_100'),
    ('KZN','competition',50,'KZN_base_does_not_mean_dominance_50'),
    ('GSV','basing',100,'GSV_favourable_basing_100'),
    ('GOJ','basing',0,'GOJ_no_acceptable_basing_0')]:
    changed=copy.deepcopy(cities)
    next(r for r in changed if r['iata']==code)[criterion]=value;add_case(label,changed)
changed=copy.deepcopy(cities)
for r in changed:r['technical']=100
add_case('all_technical_100_no_information_advantage',changed)
changed=copy.deepcopy(cities)
next(r for r in changed if r['iata']=='UFA').update(technical=100,competition=75)
add_case('UFA_joint_technical100_competition75',changed)
for ceiling in [1.4,1.8]:add_case(f'geographic_detour_ceiling_{ceiling}',calculate_cities(ceiling)[0])
csv_out('sensitivity.csv',sensitivity)

# OAT measures: one unknown criterion at its range ends, all other inputs centred.
oat=[]
for c in DATA['cities']:
    for k in ['competition','technical','basing']:
        lo,hi=c[k+'_interval']
        if lo==hi:continue
        for val in [lo,hi]:
            changed=copy.deepcopy(cities);next(r for r in changed if r['iata']==c['iata'])[k]=val
            rr=rank(changed,DATA['weights']['base'],True)
            oat.append(dict(iata=c['iata'],criterion=k,value=val,top3=' > '.join(r['iata'] for r in rr[:3])))
csv_out('missing_input_effects.csv',oat)

hub,legs,violations=build_networks()
for net in ['A','B']:
    if len({r['aircraft'] for r in legs if r['network']==net})>N['active_aircraft']:
        violations.append([net,'all_days','all_aircraft','active_pool_exceeded'])
assert not violations,violations
assert hub=='GOJ','Network sketch must be re-designed if the first city changes'
summary=network_summary(legs);conns=connections(legs,hub)
_,b0legs,_=build_networks(use_slack=False)
csv_out('direct_initial_summary.csv',[r for r in network_summary(b0legs) if r['network']=='B'])
csv_out('flight_instances.csv',legs);csv_out('potential_connections.csv',conns);csv_out('network_summary.csv',summary)
routes=[]
for net in ['A','B']:
    pairs=sorted({tuple(sorted([r['origin'],r['destination']])) for r in legs if r['network']==net})
    for a,b in pairs:
        freq=Counter((r['origin'],r['destination']) for r in legs if r['network']==net and {r['origin'],r['destination']}=={a,b})
        km=distance(a,b)
        routes.append(dict(network=net,origin=a,destination=b,distance_km=round(km),
                           departures_each_direction=f"{freq[a,b]}/{freq[b,a]}",
                           block_hours=round(block(a,b)/60,2),
                           function='hub_spoke' if net=='A' else 'base_access_commercial_assumption' if {a,b}&{'ZIA','SVX'} else 'interregional_target',
                           variant_review='review_variant_payload_wind' if km>2300 else 'preliminary_distance_only_not_clearance',
                           demand_status='UNKNOWN',frequency_status='ASSUMPTION'))
csv_out('routes.csv',routes)
stress=[]
for label,speed,overhead,turn in [('base',700,.35,45),('slower_block_long_turn',650,.5,60),('shorter_block',750,.3,40)]:
    _,ls,vs=build_networks(speed,overhead,turn)
    for s in network_summary(ls):stress.append(dict(case=label,**s,violations=sum(v[0]==s['network'] for v in vs)))
csv_out('schedule_stress.csv',stress)
resource=[]
for cap in [10,8,6.5]:
    for net in ['A','B']:
        rs=[r for r in legs if r['network']==net]
        sums=defaultdict(int)
        for r in rs:sums[(r['day'],r['aircraft'])]+=r['block_minutes']
        resource.append(dict(network=net,daily_block_cap_hours=cap,
            weekly_hour_lower_bound=math.ceil(sum(sums.values())/(6*cap*60)),
            aircraft_days_above_cap=sum(v>cap*60 for v in sums.values()),
            note='hour_lower_bound_not_scheduled_minimum'))
csv_out('resource_sensitivity.csv',resource)
deployment=[]
# Both projects start from the same hypothetical 3 ZIA + 2 SVX pool.
# A places all five at GOJ. B keeps two working planes + a spare at ZIA,
# two working planes at SVX; moving that spare to SVX is NOT instantaneous.
for base,count in [('ZIA',3),('SVX',2)]:
    deployment.append(dict(network='A',origin=base,destination=hub,count=count,
                           block_hours_total=round(count*block(base,hub)/60,2),
                           status='ONE_OFF_EMPTY_DEPLOYMENT_ASSUMPTION'))
deployment.append(dict(network='B',origin='ZIA',destination='SVX',count=1,
                       block_hours_total=round(block('ZIA','SVX')/60,2),
                       status='SPARE_RESPONSE_IF_REQUIRED_NOT_WEEKLY_BASELINE'))
csv_out('deployment_and_spare.csv',deployment)

source_ids={s['id'] for s in SOURCES}
assert len(source_ids)==len(SOURCES)
assert len(DATA['cities'])>=10
assert all(set(c['sources'])<=source_ids for c in DATA['cities'])
assert all(abs(sum(w.values())-1)<1e-10 for w in DATA['weights'].values())
assert not violations,violations
assert all(r['origin']!=r['destination'] for r in legs)
assert Counter(r['network'] for r in legs)=={'A':96,'B':92}
assert len(conns)==96

sections=['# Расчётные таблицы: 8 ноября 2026\n',
          'Сгенерировано `python3 scripts/build_practical_screening.py`. Баллы неизвестных — сценарные середины интервалов. Ниже нет оценённого OD-спроса.\n',
          '## Единая таблица городов\n',
          'Население — город на 01.01.2025, тыс.; POP-1/POP-2 — вторичный справочник. Поток — обслуженные пассажиры аэропорта за 2025, не спрос на пары. UNKNOWN означает отсутствие проверенного значения.\n']
sections.append(md_table(['Город','Местный рынок: население / поток аэропорта','Конкуренция','Связанность','Пригодность аэропорта','Базирование','Источники'],
    [[c['city']+' / '+c['iata'],f"{c['population_thousands']:.1f} тыс. / "+('> ' if c['pax_qualifier']=='strict_lower_bound' else '≈ ' if 'rounded' in c['pax_qualifier'] else '')+f"{c['airport_pax_2025']/1e6:.3f} млн",c['competition'],c['connectivity'],c['technical'],c['basing'],', '.join(c['sources'])] for c in DATA['cities']]))
sections += ['\n## Баллы пяти групп и диапазон из-за пропусков\n',md_table(['Место, общий список','Город','Рынок','Конкуренция*','География','Техника*','База*','Итого','Интервал**','Новый узел'],
 [[i,r['city']]+[f'{r[k]:.2f}' for k in CRITERIA]+[f"{r['score']:.2f}",f"{r['interval_low']:.2f}…{r['interval_high']:.2f}",'да, условно' if r['new_node'] else 'исключён в строгом новом варианте'] for i,r in enumerate(rank(cities,DATA['weights']['base']),1)]),
 '* Середина явно заданного интервала, где фактов нет. ** Независимые крайние значения пропусков, не доверительный интервал и не вероятность.\n',
 '## Разумные веса и изменение топ-3\n',md_table(['Набор весов M/C/G/T/B','Общий топ-3','Топ-3 нового узла'],
 [[label+' '+str(list(w.values())),' > '.join(r['iata'] for r in rank(cities,w)[:3]),' > '.join(r['iata'] for r in rank(cities,w,True)[:3])] for label,w in DATA['weights'].items()]),
 '\n## Влияние пропусков и допущений\n',md_table(['Проверка','Общий топ-3','Топ-3 нового узла'],
 [[sensitivity[i]['case'],sensitivity[i]['top3'],sensitivity[i+1]['top3']] for i in range(0,len(sensitivity),2)]),
 '\n## Две сети: маршруты и частоты\n',
 'Частота — вылеты в каждом направлении в неделю; формат 6/6 означает шесть А→Б и шесть Б→А. Все частоты — ASSUMPTION. Длины — ортодромия, блок-время модельное.\n',
 md_table(['Сеть','Пара','км','Вылетов/нед. по направлениям','Блок, ч/плечо','Роль','Проверка варианта ВС'],
 [[r['network'],r['origin']+'–'+r['destination'],r['distance_km'],r['departures_each_direction'],r['block_hours'],r['function'],r['variant_review']] for r in routes]),
 '\n## Помашинные цепочки: нечётные и чётные дни\n',
 'Дни 1–6 — условная типовая неделя, день 7 оставлен под плановое обслуживание и восстановление. UTC, не локальное время. Это размещение самолётов, не норматив рабочего времени экипажа.\n',
 md_table(['Сеть','День','Борт','Цепочка с UTC'],
 [[net,day,aircraft,'; '.join(f"{r['origin']} {hhmm(r['departure_utc_minute'])} → {r['destination']} {hhmm(r['arrival_utc_minute'])}" for r in legs if r['network']==net and r['day']==day and r['aircraft']==aircraft)]
  for net in ['A','B'] for day in [1,2] for aircraft in sorted({r['aircraft'] for r in legs if r['network']==net})]),
 '\n## Сопоставление предложения и парка\n',md_table(list(summary[0]),[[s[k] for k in summary[0]] for s in summary]),
 f"LF 55–80% — широкий тест ёмкости, не доказательство спроса и не прогноз продаж. А: {len(conns)} потенциальных стыковок по датам (16 в день), 32 различных направленных OD; при отношении пути через GOJ к прямому ≤1.6 остаётся {sum(r['detour']<=1.6 for r in conns)} стыковок и {len({(r['origin'],r['destination']) for r in conns if r['detour']<=1.6})} направленных OD. Места и продажи на них не подтверждены.\n",
 '\n## Стресс блок-времени и оборота\n',md_table(['Сценарий','Сеть','Блок-ч/нед.','Макс. блок/день','Макс. размах дня','Нарушения условных ограничений'],
 [[s['case'],s['network'],s['weekly_block_hours'],s['daily_block_max'],s['day_span_max'],s['violations']] for s in stress]),
 '\n## Чувствительность к лимиту налёта\n',md_table(['Сеть','Лимит блок-ч/день','Нижняя оценка активных по часам','Борто-дней нарушают лимит'],
 [[s['network'],s['daily_block_cap_hours'],s['weekly_hour_lower_bound'],s['aircraft_days_above_cap']] for s in resource]),
 '\n## Первичное размещение и резерв\n',md_table(['Сеть','Из','В','Количество перегонов','Блок-ч, всего','Назначение'],
 [[s['network'],s['origin'],s['destination'],s['count'],s['block_hours_total'],s['status']] for s in deployment]),
 '\n## Источники\n',md_table(['ID','Статус прочтения','Период/публикация','Что поддерживает','URL'],
 [[s['id'],s['kind'],s.get('period',s.get('published','недатированная страница')),s['supports'],f"[источник]({s['url']})"] for s in SOURCES])]
(OUT/'tables.md').write_text('\n\n'.join(sections)+'\n')
result=dict(first_new_hub=hub,network_summary=summary,baseline_violations=violations,
            potential_connections=len(conns),potential_directed_od=len({(r['origin'],r['destination']) for r in conns}),
            checks='PASS',inputs_sha256=hashlib.sha256((OUT/'inputs.json').read_bytes()).hexdigest())
(OUT/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
chart_data={name:[dict(city=r['city'],score=round(r['score'],2))
                  for r in rank(cities,w,True)] for name,w in DATA['weights'].items()}
chart='''<!doctype html><html lang="ru"><meta charset="utf-8"><style>
body{margin:0;font:14px var(--font-sans,system-ui);color:var(--foreground)}
p{line-height:1.45}nav{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0}
button{font:inherit;border:1px solid var(--border);border-radius:6px;padding:7px 10px;background:var(--secondary);color:var(--foreground);cursor:pointer}
button[aria-pressed=true]{border-color:var(--primary);color:var(--primary)}
.row{display:grid;grid-template-columns:155px 1fr 45px;gap:9px;align-items:center;margin:12px 0}
.track{background:var(--secondary);height:15px;border-radius:3px}.bar{height:15px;background:var(--chart-1);border-radius:3px}
.note{font-size:12px;color:var(--muted-foreground,var(--foreground))}
@media(max-width:450px){.row{grid-template-columns:120px 1fr 38px;font-size:12px}}
</style><p><strong>Новые узлы: предварительные баллы</strong></p>
<nav aria-label="Наборы весов"><button data-case="base">Базовые веса</button><button data-case="market">Местный рынок</button><button data-case="geography">География</button><button data-case="operations">Реализация</button></nav>
<div id="bars" role="img" aria-label="Рейтинг городов при выбранных весах"></div>
<p class="note">Шкала 0–100. В пропусках стоят сценарные середины интервалов. Самара и Казань исключены только из строгого нового списка: RW уже называет их опорными аэропортами. При совместном улучшении технических и конкурентных входов Уфа может выйти на первое место. Баллы не измеряют спрос или прибыль.</p>
<script>const values=__DATA__;function draw(key){document.getElementById('bars').innerHTML=values[key].map((r,i)=>`<div class="row"><span>${i+1}. ${r.city}</span><div class="track"><div class="bar" style="width:${r.score}%;opacity:${i<3?1:.5}"></div></div><span>${r.score.toFixed(2)}</span></div>`).join('');document.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.case===key)))}document.querySelectorAll('button').forEach(b=>b.onclick=()=>draw(b.dataset.case));draw('base');</script></html>'''
(OUT/'ranking_chart.html').write_text(chart.replace('__DATA__',json.dumps(chart_data,ensure_ascii=False)))
print(json.dumps(result,ensure_ascii=False,indent=2))
