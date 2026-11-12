"""Численные пороги международного применения SSJ при неизвестном международном OD.

Не создаёт конкурирующую P05-модель. Внутренние продажи пересчитываются P05/P06;
международная выручка/SPA/доступ и остаток иностранных расходов — явные переменные.
"""
import copy,csv,json
import programme_builder as b
import evaluate_programmes as e

def main():
    ps={p['programme_id']:p for p in json.loads((b.ROOT/'programmes.json').read_text())['programmes']}
    cards={r['market_card_id']:r for r in csv.DictReader((b.ROOT/'sealed/P02I/international_market_cards.csv').open())}
    rows=[];flightrows=[];specs=[]
    for parent_id,dest,mins,cardid,hyp in [('SVX_RADIAL','URC',240,'IMC-SVX-URC','I06'),('KUF_RADIAL','IST',275,'IMC-KUF-IST','I03')]:
        parent=ps[parent_id];base=parent['working_slots'][0]['base'];spokes=parent['working_slots'][0]['spokes']
        p=copy.deepcopy(parent);p['programme_id']=parent_id+'_INTL_RESERVATION';p['label']=base+'–'+dest+': международная замена двух внутренних оборотов в неделю'
        p['working_slots'][0]['ordered_paths_iso_weekday']={str(i+1):[base,spokes[i%3],base] for i in range(6) if i not in [1,4]}
        specs.append(dict(programme=p,parent=parent_id,hypothesis_id=hyp,new_Tu214=0,international_OD='UNKNOWN; не расширять domestic P05 gravity на foreign',revenue_mode='FOREIGN_NET_REVENUE_SYMBOLIC',source_card=cards[cardid],source_row_sha256=b.digest(cards[cardid]),return_duration_assumption='Симметричный published elapsed аналог; обратный OFP/season/routing UNKNOWN',foreign_cost_coverage='Только явно перенесённый SSJ hourly/fuel аналог и российский movement; foreign handling/FX/insurance/permits/tax/SPA UNKNOWN',through_journeys='UNKNOWN, не удалять существующие own/partner contracts'))
        for delivery in ['phased','partial','delayed','none']:
            tails={x['aircraft_id']:x for x in b.fleet(delivery)};tail=tails.get('N2')
            dates=[]
            if tail:
                start=b.date.fromisoformat(tail['service_entry_date'][:10])+b.timedelta(days=1)
                dates=[d for d in b.DATES if start<=d<=b.date(2028,12,30) and d.isoweekday() in [2,5]]
            bymonth={m:[d for d in dates if d.isoformat().startswith(m)] for m in b.MONTHS}
            for d in dates:
                t=b.timestamp(d,6.5);arrival=t+b.timedelta(minutes=mins);back=arrival+b.timedelta(minutes=45)
                for a,z,depart,arrive in [(base,dest,t,arrival),(dest,base,back,back+b.timedelta(minutes=mins))]:
                    flightrows.append(dict(programme_id=p['programme_id'],delivery=delivery,aircraft_id='N2',aircraft_variant=b.NEW_VARIANT,departure_utc=b.iso(depart),arrival_utc=b.iso(arrive),origin_airport=a,destination_airport=z,nominal_seats_scenario=100,accepted_saleable_seats=None,reported_flight_id=None,international_journeys=None,status='PROPOSED_CONDITIONAL_PHYSICAL_TEMPLATE_NOT_ADMITTED_INVENTORY',source_card=cardid,source_row_sha256=b.digest(cards[cardid]),assumption_id='P09-INTERNATIONAL'))
            for scenario in ['base','cautious']:
                r=e.evaluate(p,delivery,scenario,'passive');original=json.loads((b.ROOT/'evaluations'/('__'.join([parent_id,delivery,scenario,'passive'])+'.json')).read_text())
                assert r['status']=='CONDITIONAL_P05_P06_CALCULATED'
                rates={'base':(1.55,.2,35000+15000+6000),'cautious':(1.9,.25,55000+22000+8000)}[scenario]
                for i,m in enumerate(b.MONTHS):
                    nrt=len(bymonth[m]);bh=2*nrt*mins/60;fuel=bh*rates[0]+2*nrt*rates[1]
                    domestic_movement=sum(float(b.COSTS.get(base+'-'+key,b.COSTS['UFA-'+key])['value']) for key in ['takeoff_landing','security'])*49.45*nrt
                    known_cost=fuel*136300+bh*rates[2]+domestic_movement
                    current=r['results_monthly'][i];prior=original['results_monthly'][i]
                    opportunity=prior['known_operating_subtotal']-current['known_operating_subtotal']
                    threshold=opportunity+known_cost
                    rows.append(dict(programme_id=p['programme_id'],parent_programme_id=parent_id,hypothesis_id=hyp,delivery=delivery,scenario=scenario,month=m,new_Tu214=0,foreign_roundtrips=nrt,foreign_physical_legs=2*nrt,foreign_block_hours=bh,domestic_retained_journeys=current['journeys'],domestic_delta_journeys_vs_parent=current['journeys']-prior['journeys'],domestic_retained_revenue=current['revenue_net'],foregone_domestic_known_contribution=opportunity,foreign_known_analogue_cost=known_cost,foreign_net_revenue_minus_missing_cost_required_to_equal_parent=threshold,conditional_required_net_RUB_per_100occupied_leg=None if not nrt else threshold/(2*nrt*100),foreign_OD_journeys=None,combined_full_revenue=None,combined_full_result=None,status='ЧИСЛЕННЫЙ_OPPORTUNITY_THRESHOLD; международная fullchoice/economics OPEN',assumption_ids='P09-INTERNATIONAL;P09-COST;P09-SCOPE;P02I-A03;P02I-A04;P02I-A06'))
    out=b.ROOT/'international';out.mkdir(exist_ok=True)
    b.csvwrite(out/'thresholds_monthly.csv',rows);b.csvwrite(out/'dated_templates.csv',flightrows);b.dump(out/'programmes.json',dict(programmes=specs,main_CASE_SJ_independent=True,new_Tu214=0,existing_Tu214='KEEP не обнулён; общий неизменный остаток вне CASE_SJ; перераспределение требует отдельного источника',other_8_P02I_hypotheses='CONDITIONAL_OPEN; exact missing fields retained in sealed/P02I/programme_hypotheses.json',capital_branch='Инвестиционная ветвь новогоТу214 UNKNOWN; единица сравнительного опыта не поставочный прогноз'))
    b.dump(out/'assumptions.json',[b.assumption('P09-INTERNATIONAL','Два RT/week вт/пт; опубликованныйonewayelapsed240/275minсимметрично в обе стороны; российскийcostаналог','RT;min;RUB2026','P02I IMC-SVX-URC/IMC-KUF-IST; новыйпрозрачный ресурсныйопыт; не прогнозспроса/допуск','Цена отказаот внутренних рейсов и минимальныйnet международного применения','Иностранные расходы/допуски/нагрузка/OD остаются переменными; никакого доверительного интервала','P05 foreign markets/SPA; P03 OFP/AFM and own KEEP; P04 contracts/FX; P02I access')])
    print('international_monthly',len(rows),'physical_templates',len(flightrows),flush=True)

if __name__=='__main__':main()
