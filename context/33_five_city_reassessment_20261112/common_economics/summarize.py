#!/usr/bin/env python3
"""Derived decision boundaries and self-contained comparison chart; no model calls."""
import csv
import itertools
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent


def read(name):
    return list(csv.DictReader((OUT/name).open()))


def f(row,key):
    return float(row[key]) if row.get(key) not in ['',None] else None


def write(name,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with (OUT/name).open('w',newline='') as h:
        w=csv.DictWriter(h,keys);w.writeheader();w.writerows(rows)


def run():
    c=read('comparison.csv')
    ods=read('od_flows.csv')
    stress={(r['network_id'],int(r['fuel_compensation_rub_per_t']),float(r['transfer_keep_fraction'])):r
            for r in read('fixed_schedule_stress.csv')}
    combined=[]
    pairs=[]
    odthresholds=[]
    stressed=[]
    stressleaders=[]
    for scen,mode,budget in itertools.product(['base','cautious'],['rules500','rules0'],range(2,8)):
        rows=[r for r in c if r['demand_scenario']==scen and r['mode']==mode
              and int(r['budget_aircraft'])==budget and r['status']=='ok']
        rs=sorted(rows,key=lambda r:-f(r,'contribution_rub_year'))
        for i,j in itertools.combinations(rs,2):
            gap=f(i,'contribution_rub_year')-f(j,'contribution_rub_year')
            dh=(f(i,'block_h_week')-f(j,'block_h_week'))*f(i,'weeks_per_year')
            pairs.append(dict(demand_scenario=scen,mode=mode,budget_aircraft=budget,
                i=i['alternative'],product_i=i['product'],j=j['alternative'],product_j=j['product'],
                network_i=i['selected_network_id'],network_j=j['selected_network_id'],
                gap_rub_year=gap,annual_block_hours_i_minus_j=dh,
                fixed_additions_i_minus_j_max_rub_year=gap,
                extra_common_hour_cost_equality_rub_h=gap/dh if abs(dh)>1e-9 else None,
                positive_common_hour_cost_can_reverse=gap>0 and dh>0,
                interpretation='i beats j iff F_i-F_j+k*(H_i-H_j)<gap; F is unknown'))
        for alt in ['UFA','PEE','CEK','TJM','GOJ','OMS','DIRECT']:
            sub=[r for r in rs if r['alternative']==alt]
            if not sub:
                combined.append(dict(demand_scenario=scen,mode=mode,budget_aircraft=budget,
                    alternative=alt,status='not_feasible_in_constructed_product_menu',
                    selected_network_id=None,contribution_rub_year=None))
                continue
            r=sub[0]
            combined.append(dict(demand_scenario=scen,mode=mode,budget_aircraft=budget,
                alternative=alt,status='ok',selected_network_id=r['selected_network_id'],
                selected_product=r['product'],program_grain=r['program_grain'],programs=r['programs'],
                unique_undirected_legs=r['unique_undirected_legs'],
                aircraft_including_one_spare=r['aircraft_including_one_spare'],block_h_week=r['block_h_week'],
                contribution_rub_year=r['contribution_rub_year']))
        if rs:
            winner=rs[0]
            competitors=[r for r in rs[1:] if r['alternative']!=winner['alternative']]
            if competitors:
                runner=competitors[0]
                gap=f(winner,'contribution_rub_year')-f(runner,'contribution_rub_year')
                for o in ods:
                    if o['network_id']!=winner['selected_network_id'] or f(o,'od_year')<=0:
                        continue
                    unit=f(o,'unit_contribution_before_schedule_cost_rub')
                    lost=gap/unit if unit>0 else None
                    revenue=f(o,'full_fare_rub')
                    own=gap/revenue if revenue>0 else None
                    odthresholds.append(dict(demand_scenario=scen,mode=mode,budget_aircraft=budget,
                        winner=winner['alternative'],winner_product=winner['product'],runner=runner['alternative'],
                        runner_product=runner['product'],winner_network=winner['selected_network_id'],
                        gap_rub_year=gap,od_kind=o['kind'],a=o['a'],b=o['b'],via=o['via'],
                        observed_model_od_year=o['od_year'],unit_lost_sale_contribution_rub=unit,
                        lost_sale_od_threshold=lost,
                        lost_sale_threshold_within_observed_od=(0<=lost<=f(o,'od_year')) if lost is not None else None,
                        author_own_diversion_revenue_loss_per_od_rub=revenue,
                        additional_own_diversion_od_threshold_no_old_cost_saving=own,
                        remaining_model_new_od_for_own_diversion=f(o,'od_year')-f(o,'rw_migrated_od_year'),
                        own_diversion_threshold_within_remaining_model_new_od=(0<=own<=f(o,'od_year')-f(o,'rw_migrated_od_year')) if own is not None else None,
                        true_old_network_unit_contribution_rub=None,
                        scope='one OD lost at fixed schedule, no resale; own-diversion column follows author revenue-only accounting, old avoided costs unknown'))
        for comp,keep in itertools.product([32930,3024,0],[1,0.5,0]):
            ss=[]
            for r in rs:
                z=stress[(r['selected_network_id'],comp,keep)]
                v=dict(demand_scenario=scen,mode=mode,budget_aircraft=budget,
                    alternative=r['alternative'],product=r['product'],network_id=r['selected_network_id'],
                    fuel_compensation_rub_per_t=comp,transfer_keep_fraction=keep,
                    contribution_rub_year=z['contribution_rub_year'],
                    block_h_week=z['block_h_week'],flights_week=z['flights_week'],
                    scenario='ranking_fixed_preselected_schedules_without_reoptimization')
                stressed.append(v);ss.append(v)
            if ss:
                z=max(ss,key=lambda x:f(x,'contribution_rub_year'))
                stressleaders.append(dict(z,positive_before_unknown_fixed_cost=f(z,'contribution_rub_year')>0,
                    keep_no_new_program_contribution_rub_year=0))
    write('combined_product_comparison.csv',combined)
    write('cross_product_thresholds.csv',pairs)
    write('winner_od_loss_thresholds.csv',odthresholds)
    write('stress_comparison.csv',stressed)
    write('stress_leaders.csv',stressleaders)
    # Small JSON handoff. Unknown full costs are JSON null, never zero.
    summary=dict(subject='dceadc98f9a293d7530cb7bc50ca4411a95aa4b6',
        status='bounded_model_calculation_not_market_business_plan',
        cities=['UFA','PEE','CEK','TJM','GOJ','OMS'],direct_bases=['MOW','SVX'],
        budgets_including_one_spare=[2,3,4,5,6,7],
        main_modes=['rules500','rules0'],
        products={'author8_12':'8-12 spokes or 8-12 triangles, original grain',
                  'start3_6':'3-6 spokes or 3-6 triangles, explicit product scenario'},
        omitted_fixed_cost=None,full_profit=None,market_acceptance='NOT_RUN',
        selected_combined_programs=combined,
        not_run=json.loads((OUT/'checks.json').read_text())['not_run'])
    (OUT/'decision.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    data=[]
    for r in c:
        if r['mode'] in ['rules500','rules0']:
            data.append(dict(scenario=r['demand_scenario'],mode=r['mode'],product=r['product'],
                budget=int(r['budget_aircraft']),city=r['alternative'],status=r['status'],
                value=f(r,'contribution_rub_year')/1e6 if r['status']=='ok' else None))
    html='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{color:var(--foreground);font-family:var(--font-sans,system-ui)}
body{margin:0}h2{font-size:18px;margin:8px 0}p{font-size:13px;line-height:1.5;margin:8px 0;color:var(--muted-foreground,var(--foreground))}
label{display:inline-flex;gap:6px;align-items:center;font-size:13px;margin:6px 8px 6px 0}select{font:inherit;color:var(--foreground);background:var(--card);border:1px solid var(--border);padding:5px;border-radius:var(--radius,6px)}
svg{width:100%;height:360px;overflow:visible}svg text{font:12px var(--font-sans,system-ui);fill:var(--foreground)}
.legend{display:flex;flex-wrap:wrap;gap:12px;font-size:13px}.legend span{display:inline-flex;align-items:center;gap:5px}.swatch{width:16px;height:3px;display:inline-block}
table{border-collapse:collapse;font-size:12px;width:100%;font-variant-numeric:tabular-nums}th,td{padding:5px 3px;border-bottom:1px solid var(--border);text-align:right}th:first-child,td:first-child{text-align:left}
</style>
<h2>Вклад сети при общем ограничении парка</h2>
<label>Спрос <select id="scen"><option value="base">Базовый</option><option value="cautious">Осторожный</option></select></label>
<label>Дистанция <select id="mode"><option value="rules500">Параметр 500 км</option><option value="rules0">Параметр 0 км</option></select></label>
<label>Программа <select id="product"><option value="author8_12">8–12 лучей / треугольников</option><option value="start3_6">3–6 лучей / треугольников</option></select></label>
<p>Млн ₽ за условный год до неизвестных полных добавочных расходов. По оси X — максимум самолётов, включая один резерв. Разрыв линии означает: допустимая сеть не найдена в рассчитанном наборе.</p>
<svg id="plot" viewBox="0 0 700 360" role="img" aria-label="Сравнение вклада семи программ при бюджете от двух до семи самолётов"></svg><div id="legend" class="legend"></div><div id="table"></div>
<p>Парк — ресурсный сценарий. Greedy и переоценка сохранённых сетей не доказывают глобальный оптимум. Треугольник состоит из трёх плеч. Числа не подтверждают продажи, стыковки, поставку SJ-100 или право на топливную выплату.</p>
<script>
const data=DATA;
const cities=['UFA','PEE','CEK','TJM','GOJ','OMS','DIRECT'];
const colors=['var(--chart-1)','var(--chart-2)','var(--chart-3)','var(--chart-4)','var(--chart-5)','var(--chart-6)','var(--foreground)'];
function draw(){
const rows=data.filter(r=>r.scenario===document.getElementById('scen').value&&r.mode===document.getElementById('mode').value&&r.product===document.getElementById('product').value);
const values=rows.filter(r=>r.value!==null).map(r=>r.value);let lo=Math.min(0,...values),hi=Math.max(0,...values);let pad=(hi-lo)*.08||1;lo-=pad;hi+=pad;
const plot=document.getElementById('plot'),width=Math.max(320,plot.clientWidth),right=width-20;plot.setAttribute('viewBox',`0 0 ${width} 360`);
const x=b=>62+(b-2)*(right-62)/5,y=v=>310-(v-lo)/(hi-lo)*280;
let svg='';for(let n=0;n<5;n++){let v=lo+(hi-lo)*n/4;svg+=`<line x1="62" y1="${y(v)}" x2="${right}" y2="${y(v)}" stroke="var(--border)"/><text x="55" y="${y(v)+4}" text-anchor="end">${v.toFixed(0)}</text>`}
svg+=`<line x1="62" y1="${y(0)}" x2="${right}" y2="${y(0)}" stroke="var(--muted-foreground)" stroke-dasharray="4 3"/>`;
for(let b=2;b<=7;b++)svg+=`<text x="${x(b)}" y="335" text-anchor="middle">${b}</text>`;
cities.forEach((city,i)=>{let rr=rows.filter(r=>r.city===city).sort((a,b)=>a.budget-b.budget),path='';rr.forEach(r=>{if(r.value===null){path+=' ';return}const prev=rr.find(q=>q.budget===r.budget-1);path+=`${!prev||prev.value===null?'M':'L'}${x(r.budget)},${y(r.value)} `;svg+=`<circle cx="${x(r.budget)}" cy="${y(r.value)}" r="3" fill="${colors[i]}"><title>${city}, ${r.budget} ВС: ${r.value.toFixed(3)} млн ₽</title></circle>`});svg+=`<path d="${path}" fill="none" stroke="${colors[i]}" stroke-width="2" ${city==='DIRECT'?'stroke-dasharray="5 3"':''}/>`});
document.getElementById('plot').innerHTML=svg;
document.getElementById('legend').innerHTML=cities.map((c,i)=>`<span><i class="swatch" style="background:${colors[i]}"></i>${c}</span>`).join('');
document.getElementById('table').innerHTML='<table><thead><tr><th>Сеть</th>'+[2,3,4,5,6,7].map(x=>`<th>${x} ВС</th>`).join('')+'</tr></thead><tbody>'+cities.map(c=>'<tr><td>'+c+'</td>'+[2,3,4,5,6,7].map(b=>{let r=rows.find(r=>r.city===c&&r.budget===b);return '<td>'+(r.value===null?'—':r.value.toFixed(1))+'</td>'}).join('')+'</tr>').join('')+'</tbody></table>';
}
document.querySelectorAll('select').forEach(x=>x.addEventListener('change',draw));window.addEventListener('resize',draw);draw();
</script></html>'''.replace('DATA',json.dumps(data,ensure_ascii=False))
    (OUT/'comparison.html').write_text(html)


if __name__=='__main__':
    run()
