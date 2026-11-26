#!/usr/bin/env python3
"""Generate Russian readout and terminal CSV reconciliations from saved runs."""
import sys
sys.dont_write_bytecode=True
import csv,json,statistics,hashlib,math
from collections import defaultdict
from pathlib import Path
from build_competition_market import ROOT,P09,readcsv,writecsv,dump
from run_competitive_p09 import SPOTLIGHT

def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])
def num(v,scale=1,d=1):return 'UNKNOWN' if v is None else f'{float(v)/scale:,.{d}f}'.replace(',',' ')
def pct(v):return 'UNKNOWN' if v is None else num(v*100,1,1)+'%'
def main():
    summary=[]
    for r in readcsv(ROOT/'recomputed_programmes_summary.csv'):
        for k in ['journeys','passenger_segments','delta_journeys','revenue_net','delta_revenue_net','known_operating_subtotal','delta_known_operating_subtotal','known_components_incremental_peak_diagnostic','flight_load_factor','seat_capacity','rank_known_subtotal','p09_original_rank_base']:
            r[k]=float(r[k]) if r.get(k) not in ('',None,'UNKNOWN') else None
        summary.append(r)
    manifest=json.loads((ROOT/'model_outputs/run_manifest.json').read_text());market=json.loads((ROOT/'market_competition_209.json').read_text());mby={m['pair']:m for m in market}
    details=json.loads((ROOT/'spotlight9_deep_dive.json').read_text());quality=json.loads((ROOT/'calibration/market_quality.json').read_text())
    observed=readcsv(ROOT/'calibration/yandex_deduplicated_direct.csv')
    legacy_routes={(r['programme_id'],r['pair']):r for r in details if r['config']=='p09_legacy_check'}
    for row in details:
        for k in ['revenue_net','pax_fees','passenger_segments','journey_equivalents','gross_revenue','no_direct_revenue_net','no_direct_pax_fees','no_direct_passenger_segments']:
            row.setdefault(k,0.)
        row['observed_direct_competitor_flights']=[{k:o[k] for k in ['carrier','flight_number','a','b','date','vehicle','seats','source']} for o in observed if o['pair']==row['pair'] and o['carrier']!='WZ']
        row['direct_evidence_scope']='observed sample flights plus quote/award presence; aggregate removal ablation cannot identify individual carrier causal shares'
        old=legacy_routes.get((row['programme_id'],row['pair']))
        row['p09_original_route_known_contribution']=old['known_contribution'] if old else None
        row['change_vs_p09_route_known_contribution']=row['known_contribution']-old['known_contribution'] if old else None
        row['p09_original_route_weighted_gross_fare']=old.get('weighted_gross_fare') if old else None
    writecsv('spotlight9_deep_dive.csv',details);dump('spotlight9_deep_dive.json',details)
    by={(r['programme_id'],r['config']):r for r in summary};configs=manifest['configurations'];front=readcsv(ROOT/'model_outputs/pareto_frontiers.csv');robust=readcsv(ROOT/'model_outputs/robust_frontier.csv')
    canonical=json.loads((ROOT/'model_outputs/canonical_equivalence.json').read_text());eq=json.loads((ROOT/'model_outputs/legacy_equivalence.json').read_text())
    def ranks(c):return sorted([r for r in summary if r['config']==c and r['delta_known_operating_subtotal'] is not None],key=lambda r:-r['delta_known_operating_subtotal'])
    def get(p,c,k='delta_known_operating_subtotal'):return by.get((p,c),{}).get(k)
    checks=[]
    assert len(market)==209 and len({m['pair'] for m in market})==209
    assert len(summary)==manifest['programmes']*len(configs)
    assert len({(r['programme_id'],r['config']) for r in summary})==len(summary)
    monthly=readcsv(ROOT/'model_outputs/recomputed_monthly.csv');monthly_tot=defaultdict(lambda:defaultdict(float))
    for r in monthly:
        for k in ['journeys','passenger_segments','delta_journeys','revenue_net','delta_revenue_net','delta_known_operating_subtotal','seat_capacity']:monthly_tot[(r['programme_id'],r['config'])][k]+=float(r[k])
    for r in summary:
        if r['delta_known_operating_subtotal'] is None:continue
        residuals={k:abs(r[k]-monthly_tot[(r['programme_id'],r['config'])][k]) for k in ['journeys','passenger_segments','delta_journeys','revenue_net','delta_revenue_net','delta_known_operating_subtotal','seat_capacity']}
        assert max(residuals.values())<.01,(r['programme_id'],r['config'],residuals)
        if r['programme_id']=='KEEP':assert abs(r['delta_known_operating_subtotal'])<.01
        assert 0<=r['flight_load_factor']<=1+1e-10
        checks.append(dict(programme_id=r['programme_id'],config=r['config'],monthly_summary_max_residual=max(residuals.values()),status='PASS'))
    writecsv('model_outputs/csv_reconciliation_checks.csv',checks)
    programmes=json.loads((P09/'programmes.json').read_text())['programmes'];subrows=[]
    for p in programmes:
        if p['programme_id'].startswith('AUTH'):continue
        pairs=set('-'.join(sorted((slot['base'],d))) for slot in p['working_slots'] for d in slot['spokes'])
        sub=[q for q in pairs if mby.get(q,{}).get('subsidized_2026') not in (None,'false')];rw=[q for q in pairs if mby.get(q,{}).get('rw_subsidized_2026')]
        subrows.append(dict(programme_id=p['programme_id'],proposed_unique_pairs=len(pairs),matched_subsidy_2026_pairs=len(sub),rw_awarded_2026_pairs=len(rw),subsidy_pairs=sub,rw_subsidy_pairs=rw,new_rw_support_2027_2028_rub=0,future_eligibility='UNKNOWN_NO_ACCRUAL'))
    writecsv('model_outputs/programmes_subsidy_exposure.csv',subrows)
    support=[]
    for c in ['comp_market_base','comp_market_cautious','comp_expansion_stress_2028']:
        for pid in SPOTLIGHT:
            rs=[r for r in details if r['config']==c and r['programme_id']==pid and r.get('flights',0)>0]
            buckets=defaultdict(lambda:dict(routes=0,contribution=0.,revenue=0.,passenger_segments=0.))
            for r in rs:
                key='RW_SUBSIDY2026_HISTORY' if r.get('rw_subsidized_2026') else 'OTHER_SUBSIDY2026' if r.get('subsidized_carriers_2026') else 'NO_MATCHED_SUBSIDY2026'
                b=buckets[key];b['routes']+=1;b['contribution']+=r['known_contribution'];b['revenue']+=r['revenue_net'];b['passenger_segments']+=r['passenger_segments']
            for k,v in buckets.items():support.append(dict(config=c,programme_id=pid,subsidy_exposure_class=k,**v,actual_new_rw_support=0,scope='full_constructed_calendar_including_E1;known_contribution_not_full_self_sufficiency'))
    writecsv('model_outputs/subsidy_contribution_decomposition.csv',support)
    hubtops=[]
    for config in configs:
        for hub in sorted({p.get('city') for p in programmes if p.get('city') and not p['programme_id'].startswith('AUTH')}):
            ps=[p['programme_id'] for p in programmes if p.get('city')==hub]
            rs=[r for r in ranks(config['config']) if r['programme_id'] in ps]
            if rs:hubtops.append(dict(hub=hub,config=config['config'],best_programme=rs[0]['programme_id'],delta_known_operating_subtotal=rs[0]['delta_known_operating_subtotal'],delta_journeys=rs[0]['delta_journeys'],rank=rs[0]['rank_known_subtotal']))
    writecsv('model_outputs/hub_best_programmes.csv',hubtops)
    report=[]
    report.append('# Экономика сети Red Wings с прямой и стыковочной конкуренцией\n')
    report.append('Расчёт выполнен 13.11.2026. Период: январь 2027 — декабрь 2028, постоянные рубли 2026 года. Во всех основных ветвях новые субсидии Red Wings равны нулю. База сравнения — будущий KEEP в том же рынке и с тем же календарём поставки `phased`.')
    best=ranks('comp_market_base')[0];caut=ranks('comp_market_cautious')[0];stress=ranks('comp_expansion_stress_2028')[0]
    report.append(f"\nЛидер по частичному добавочному операционному результату в базовом конкурентном рынке — **{best['programme_id']}**, {num(best['delta_known_operating_subtotal'],1e6)} млн ₽ и {num(best['delta_journeys'],1000)} тыс. добавочных поездок к KEEP. Его собственный известный subtotal равен **{num(best['known_operating_subtotal'],1e6)} млн ₽**: положительная дельта означает улучшение относительно убыточного KEEP. В осторожном рынке лидер — **{caut['programme_id']}** ({num(caut['delta_known_operating_subtotal'],1e6)} млн ₽); при экспансии — **{stress['programme_id']}** ({num(stress['delta_known_operating_subtotal'],1e6)} млн ₽). Положительная дельта задаёт допустимую добавочную стоимость недостающих компонентов при фиксированном прочем остатке. Полная прибыль и полная потребность в финансировании остаются UNKNOWN.")
    report.append('\n## Входные данные и покрытие\n')
    report.append(table(['Показатель','Результат'],[
        ['Маршрутные пары / хабы',f"209 / {len(readcsv(ROOT/'hub_weights_22.csv'))}"],['Котировки до / после очистки',f"21 346 / {quality['clean_unique_quotes']}"],
        ['Удалённые дубли',quality['rejected']['duplicate_quote']],['Предложения других аэропортов',quality['rejected']['airport_mismatch']],
        ['Прямая конкуренция найдена',f"{quality['direct_pairs']} / 209"],['Есть точная аэропортная пара и прямая котировка',f"{quality['direct_priced_pairs']} / 209"],
        ['Есть стыковочная котировка',f"{quality['connecting_priced_pairs']} / 209"],['Есть совпадение с субсидиями 2026',quality['subsidy_2026_pairs']],['Из них в реестре указан WZ',quality['rw_subsidized_2026_pairs']],
        ['Программы / конфигурации / оценки',f"{manifest['programmes']} / {len(configs)} / {manifest['evaluations']}"],['Непокрытые пары косвенных OD сверх 209 рёбер',len(manifest['unmapped_indirect_endpoint_pairs'])],
    ]))
    report.append('\nКотировки дедуплицированы по паре аэропортов, направлению, перевозчику, рейсу, дате, цене и числу пересадок. Исключены цены вне 500–150 000 ₽ и несоответствующие аэропорты. Медиана и 25-й перцентиль рассчитываются после нормализации багажа. Суточная частота берётся из двух зимних дат по обследованным направлениям с сохранением нулевых наблюдений; реестр субсидий даёт нижнюю сценарную частоту при наличии явного числа. При наличии только котировки используется **2 рейса в неделю на направление**, диапазон для уточнения 1–7. Таких оценок перевозчик–маршрут — '+str(sum(c['frequency_quality'].startswith('ASSUMED') for r in market for c in r['direct_carrier_details']))+'. Средняя частота двух дней, умноженная на 7, не является проверенным недельным расписанием.')
    report.append('\nWZ исключён из списка соперников и сохранён как исторический ценовой якорь. Маркетинговые SU 6001–6999 приведены к FV. Московская городская квота не переносится автоматически на DME/SVO/ZIA: например, SU в списке получателей городской субсидии не доказывает прямой рейс из DME. Неполная выборка без прямого предложения означает «прямой конкурент не найден», а не подтверждённую монополию.')
    report.append('\n## Багаж и сопоставимость тарифов\n')
    report.append(table(['Перевозчик','Добавление к кэш-цене в центральной ветви','Условие'],[
        ['DP / 5N','3 000–3 100 ₽ за плечо','Динамическая онлайн-доплата; для 5N аналог DP'],['SU / FV','4 400 / 4 720 ₽ прямой; 5 040 ₽ трансфер','3 200 ₽ в исследовании — спред пакета, не универсальная онлайн-доплата'],
        ['S7','3 000 / 4 000 ₽ за сквозную поездку','До / от 1 500 км; единый билет — допущение'],['U6','3 500 ₽ за плечо','Опубликованный минимум'],['UT','3 000 ₽ за плечо','Консервативная сегментная трактовка'],
        ['A4','4 199 ₽ коммерческий; 500/1 000 ₽ при низком спецтарифе','Только если A4 совпадает с субсидируемым перевозчиком и пределом тарифа'],['N4 / EO','2 800–3 500 / 3 000 ₽ за плечо','Зональный / региональный аналог'],['RT / IO','2 500 / 2 000–3 400 ₽ за плечо','Апгрейд до 20 кг / дистанционный аналог'],
    ]))
    report.append('\nВ кэш-ответах отсутствуют fare brand, включённые услуги и стоимость реального оформления. Поэтому **ни одна котировка не названа точной ценой checkout с 20 кг**. Центральный расчёт предполагает, что кэш показывает безбагажный тариф; диапазоны доплаты сохранены на уровне перевозчика. Если часть котировок уже включает чемодан, центральная ветвь завышает цену конкурента и может переоценивать RW. Проверка официальной [страницы Азимута](https://azimuth.ru/ru/passengers/baggage/excess) подтверждает базовую цену от 4 199 ₽, но не тарифную семью каждого предложения. Итоговые цены симметризованы по направлениям пары, это отдельное ограничение.')
    report.append('\n## Сезонные цены\n')
    report.append('Сначала сравниваются медианы одного перевозчика на одной паре и в одном продукте (прямой / стыковочный). Отношение к зиме сглаживается к дистанционному пулу с весом n/(n+2), ограничивается 0,6–1,8 и нормируется на средний календарный год. Такой профиль использует фактический состав кэш-срезов, но не отделяет сезонность от booking lead, акции и выбора дат. Рост спроса уже задан помесячным P05 и повторно не умножается на ценовой индекс.')
    report.append('\n'+table(['Профиль','Зима','Весна/осень','Лето'],[[typ]+[num(statistics.median(r[key][s] for r in market),1,3) for s in ['winter','shoulder','summer']] for typ,key in [('Медиана индекса прямых','direct_season_indices'),('Медиана индекса стыковок','transfer_season_indices')]]))
    priced=[r for r in market if any(d['quotes'] for d in r['direct_carrier_details'])]
    ratios=[r['F_comp_direct_20kg']/float(r['ref_gross_rub']) for r in priced]
    report.append(f"\nНа {len(priced)} парах хотя бы с одной прямой котировкой медианное отношение годового нормализованного якоря к плоской кривой P05 равно {num(statistics.median(ratios),1,3)}. У {sum(x<.8 for x in ratios)} пар цена ниже 80% P05, у {sum(x>1.2 for x in ratios)} — выше 120%. Плоская кривая не заменяет рынок; выборка прямых цен не доказывает сильную общую летнюю надбавку. Для стыковочных предложений летний профиль заметно выше, но влияние состава кэш-срезов не отделено.")
    report.append('\n## Порог цены и поддержка\n')
    report.append('Для каждого прямого перевозчика интерполированы переменный и полный пороги из исследовательских таблиц по типу ВС и расстоянию. Яндекс уточняет тип: E170 — 78 кресел, E190 — 110, CRJ-200 — 50, ATR72 — 70, SSJ — сценарно 100; 189-местные LCC отделены от FSC. Пороги — параметрические аналоги при принятых LF, а не раскрытая себестоимость конкретного рейса. Для отсутствующих перевозчиков явно указан аналог. В порогах конкурентов используется условный net fuel 80 тыс. ₽/т из исследования; основная RW ветвь сохраняет P09 136,3 тыс. ₽/т. Этот асимметричный консервативный выбор показан отдельной чувствительностью, он не доказывает разное фактическое право на демпфер.')
    report.append('\nРеестр 2026 года подтверждает маршрут/участника/условия, но не величину выплаты на пассажира в 2027–2028. Поэтому сохранены пороги без маршрутной выплаты и **стресс снижения порога на 20%** для совпавшего субсидируемого инкумбента, с диапазоном 0–30% для дальнейшей проверки. Доля регионального софинансирования не используется как процент скидки себестоимости. Для льгот ДФО ценовой порог отражает угрозу на доступной льготной части спроса; размер этой части UNKNOWN. Никакой новый платёж RW не начислен. Совпадение с историческим WZ не означает будущую поддержку, а положительный частичный вклад без поддержки не доказывает полную коммерческую самоокупаемость.')
    report.append('\n## Модель спроса, кресел и цены\n')
    report.append('Потенциальный спрос, base/cautious коэффициенты цены/времени/частоты, датированные самолёты, расписание, P06 simultaneous allocation, операционные проверки и финансовый ledger импортируются из pinned P09. Общие рынки проекта и KEEP объединяются до выбора. В каждом рынке отдельный продукт `AIR_COMP_DIRECT` создаётся по перевозчику с конечной ёмкостью, тарифом и временем 45 + km/750 × 60. `AIR_COMP_TRANSFER` имеет стыковочное время, цену и верхнюю ёмкость по потенциальному спросу, поскольку реальный сквозной остаток кресел неизвестен. Для совместимости с неизменным P06 внешние продукты кодируются типом `outside`, их рассчитанная полезность цены/времени/частоты записана в intercept, а конечная product capacity продолжает действовать. Внешний `final_choice` не выдаётся за наблюдённую посадку.')
    report.append('\nСтарая опорная масса air 0,6 распределяется между прямыми конкурентами и трансфером, а не добавляется второй раз. При возврате цен, времени, частоты к старым reference и снятии ограничений внешней ёмкости RW аллокация совпадает со старым P05. Прямые конкуренты не получают штраф за пересадку. Реальное сокращение времени и изменение частоты влияют на их полезность. Кресла RW расходуются по каждому физическому плечу, сквозная выручка начисляется поездке один раз.')
    report.append('\n`market_match`: ориентир — минимальная цена явного прямого продукта +3%, максимум +10% к прямому рынку и не выше сезонного reference/стыковки с ограниченной временной премией. `yield_optimal`: 11 точек между порогом переменных затрат RW при 85% плановой LF и рыночным потолком, плюс опорная corridor-точка. Максимизируется ожидаемый вклад отдельного продукта до совместной аллокации P06. Это ограниченная одномерная оптимизация, **не доказанный сетевой optimum**. Если нижний порог выше потолка готовности платить, выбирается потолок и сохраняется убыток; модель не поднимает цену до искусственного плюса. Тарифы проверяются на дату/месяц и продукт, а сезонные anchors общие. Отдельный `calibration/rw_pricing_audit.csv` показывает обе политики на одинаковом изолированном RT всех 209 пар зимой, в мае и июле; его нельзя складывать с результатами сетей.')
    report.append('\nРеакция: только в рынках с RW конкурент снижает цену на 10%, LCC/совпавший субсидируемый инкумбент — на 15%, с остановкой на пороге researched_floor / 0,97. Это дополнительный сценарный запас 3% над порогом, не повторное начисление уже включённой дистрибуции. Уже наблюдаемая цена ниже модельной себестоимости не повышается и не получает дополнительный демпинг. Одинаковое правило применяется к проекту и KEEP по их собственной представленности.')
    report.append('\n## Экспансия конкурентов\n')
    report.append('Прозрачный вес W_comp складывается из плотности прямых кресел (до 0,28), риска 189-местного LCC (0,18), кластера Аэрофлота (0,10 в 2027 / 0,18 в 2028), Nordwind/Икар (0,12), S7 (0,10), субсидируемого инкумбента (0,14). Факторы и коэффициенты сохранены по каждой паре; хабовый вес — среднее его собственных пар, без многократного присвоения общих магистралей всем хабам. Вес — сценарная экспозиция, не вероятность.')
    report.append('\nДо октября 2027 экспансия равна нулю; в IV квартале действует 25% интенсивности 2028. С 2028 существующие прямые частоты/кресла растут на 0,75 × W_comp, цены могут снизиться ещё до 0,10 × W_comp с тем же полом. На связанных с SVX, KZN и Сибирью/ДФО парах вводится эквивалент 2 рейсов в неделю × фактор экспозиции на 100-местном аналоге. Это проверка угрозы, не опубликованное расписание. [Публикация Росавиации](https://www.favt.gov.ru/novosti-rossii/?id=19626) передаёт план 8 МС-21 в 2027 и 10 в 2028; фактическая поставка, ввод и высвобождение конкретных SSJ этим не установлены. S7 E170, Nordwind KZN, Азимут MRV и 189-местная Победа учитываются через разные типы/цены/факторы; стратегии из файла исследователей не объявлены независимо подтверждёнными фактами целиком.')
    hubs=readcsv(ROOT/'hub_weights_22.csv')
    report.append('\n'+table(['Хаб','W 2027','W 2028'],[[h['hub'],num(h['W_comp_2027'],1,3),num(h['W_comp_2028'],1,3)] for h in sorted(hubs,key=lambda h:-float(h['W_comp_2028']))]))
    report.append('\n## Сравнение конфигураций\n')
    report.append(table(['Конфигурация','Лидер по Δ subtotal','Δ subtotal, млн ₽','Собственный subtotal','Δ поездок, тыс.','LF','Кассовый пик известных Δ, млн ₽'],[
        [c['config'],ranks(c['config'])[0]['programme_id'],num(ranks(c['config'])[0]['delta_known_operating_subtotal'],1e6),num(ranks(c['config'])[0]['known_operating_subtotal'],1e6),num(ranks(c['config'])[0]['delta_journeys'],1000),pct(ranks(c['config'])[0]['flight_load_factor']),num(ranks(c['config'])[0]['known_components_incremental_peak_diagnostic'],1e6)] for c in configs]))
    report.append('\nВсе дельты — относительно KEEP, заново рассчитанного при тех же ценах/конкурентах/поставках. Поэтому новая дельта может расти даже при снижении собственной выручки, если конкуренты сильнее ухудшили KEEP. Сравнение с P09 в summary содержит и абсолютные показатели, и старые/новые дельты. Приписывать всё изменение одной прямой конкуренции нельзя: одновременно обновлены багаж, сезонный anchor, цена RW и внешние альтернативы. Для прямой доступности отдельно выполнена абляция при фиксированных ценах RW и расписании.')
    report.append('\n## Девять финалистов и контролей\n')
    report.append(table(['Программа','P09 base, млн ₽','Рынок base','Рынок cautious','Экспансия','Base yield','Ранг P09 / base / stress'],[
        [p,num(get(p,'p09_legacy_check'),1e6),num(get(p,'comp_market_base'),1e6),num(get(p,'comp_market_cautious'),1e6),num(get(p,'comp_expansion_stress_2028'),1e6),num(get(p,'comp_market_base_yield'),1e6),
         ' / '.join(num(get(p,c,'rank_known_subtotal'),1,0) for c in ['p09_legacy_check','comp_market_base','comp_expansion_stress_2028'])] for p in SPOTLIGHT]))
    report.append('\n'+table(['Программа','Δ поездок base, тыс.','Δ net-выручки base, млн ₽','LF base','Пик известных Δ base, млн ₽','Пик stress, млн ₽'],[
        [p,num(get(p,'comp_market_base','delta_journeys'),1000),num(get(p,'comp_market_base','delta_revenue_net'),1e6),pct(get(p,'comp_market_base','flight_load_factor')),num(get(p,'comp_market_base','known_components_incremental_peak_diagnostic'),1e6),num(get(p,'comp_expansion_stress_2028','known_components_incremental_peak_diagnostic'),1e6)] for p in SPOTLIGHT]))
    report.append('\n## Рейтинг программ и Pareto\n')
    for name,label in [('comp_market_base','Базовый рынок'),('comp_market_cautious','Осторожный рынок'),('comp_expansion_stress_2028','Экспансия 2028')]:
        report.append('\n### '+label+'\n')
        report.append(table(['Ранг','Программа','Δ subtotal, млн ₽','Δ поездок, тыс.','LF'],[[int(r['rank_known_subtotal']),r['programme_id'],num(r['delta_known_operating_subtotal'],1e6),num(r['delta_journeys'],1000),pct(r['flight_load_factor'])] for r in ranks(name)[:15]]))
        report.append('\nPareto по поездкам и частичному subtotal: '+', '.join(r['programme_id'] for r in front if r['config']==name)+'.')
    report.append('\nУстойчивый фронт по минимуму трёх сопоставимых точек (base, cautious, expansion; без вероятностей):\n')
    report.append(table(['Политика','Программа','min Δ subtotal, млн ₽','min Δ поездок, тыс.'],[[r['pricing_policy'],r['programme_id'],num(r['delta_known_operating_subtotal'],1e6),num(r['delta_journeys'],1000)] for r in robust]))
    report.append('\nПрограммы с одинаковыми значениями могут быть физически эквивалентными календарями: HUB/HUB_LOCAL_ONLY или BANK9/BANK9_LOCAL_ONLY при отсутствии реализуемого трансфера. Они сохранены с происхождением. KEEP участвует в фронте как нулевая альтернатива. Отрицательный сценарий построенной сети не является отказом от всех возможных сетей города.')
    report.append('\n### Лучшие конструкции 15 хабов в базовом рынке\n')
    report.append(table(['Хаб','Лучшая конструкция','Δ subtotal, млн ₽','Δ поездок, тыс.'],[[r['hub'],r['best_programme'],num(r['delta_known_operating_subtotal'],1e6),num(r['delta_journeys'],1000)] for r in sorted([r for r in hubtops if r['config']=='comp_market_base'],key=lambda r:-r['delta_known_operating_subtotal'])[:15]]))
    if (ROOT/'model_outputs/input_sensitivities.csv').exists():
        sens=readcsv(ROOT/'model_outputs/input_sensitivities.csv')
        report.append('\n## Чувствительность к неполноте входов\n')
        report.append('Дополнительные независимые пересчёты проекта и KEEP: багаж уже содержался в цене (приближённая нижняя корзина), частота quote-only соперников 1 или 7 вместо 2 рейсов в неделю, отсутствие 20% снижения порога субсидируемого инкумбента. Наблюдённые/реестровые частоты не меняются. Это отдельные условия, не доверительный интервал.')
        cases=sorted({r['sensitivity_case'] for r in sens})
        report.append('\n'+table(['Программа','Центральный base, млн ₽']+cases,[[p,num(get(p,'comp_market_base'),1e6)]+[num(next((r['delta_known_operating_subtotal'] for r in sens if r['programme_id']==p and r['sensitivity_case']==s),None),1e6) for s in cases] for p in ['MRV_SEASONAL','AER_SEASONAL','VOG_RADIAL','KUF_RADIAL','SVX_RADIAL']]))
        report.append('\nПоследняя колонка floor_relief0 сопоставляется с центральным **cautious**, остальные — с base. Из-за неизвестного fare brand нельзя объявлять узкий разброс точностью прогноза. В багажной чувствительности прямые цены уменьшены на median addon перевозчика, стыковочные — на 3 500 ₽; это приближённая нижняя оценка, а не точное восстановление тарифа.')
    report.append('\n## Маршрутная маржа\n')
    report.append('Маршрутный вклад = net-выручка поездок, разнесённая по плечам исходными P05 revenue_weights, минус затраты рейсов и сборы на каждого вылетающего пассажира. Включены перегонные рейсы. Это часть операционного результата, без неизвестной базы/лизинга/запуска/выхода. В каждой разобранной программе сумма маршрутных дельт сверена с итоговым Δ subtotal с допуском 0,02 ₽. Столбец «эффект прямых» — разница с удалением явных прямых конкурентов при фиксированных ценах RW и всех остальных альтернативах. Он показывает модельный эффект доступности, не фактическую потерю продаж. При 100% LF этот эффект часто нулевой: основной ущерб конкуренции проходит через более низкую цену RW. Поэтому рядом показан прежний вклад P09; его изменение включает все обновлённые допущения и не является чистой причинной оценкой. Номера рейсов, даты, типы и перевозчики доступны в observed_direct_competitor_flights маршрутного JSON и в таблице Yandex.')
    reps={'VOG':'VOG_RADIAL','AER':'AER_HYBRID','MRV':'MRV_HYBRID','KUF':'KUF_RADIAL','SVX':'SVX_RADIAL','KZN':'KZN_HYBRID','REN':'REN_RADIAL'}
    for hub,pid in reps.items():
        rs=[r for r in details if r['config']=='comp_market_base' and r['programme_id']==pid and hub in r['pair'].split('-') and r.get('seats',0)>0]
        rs=sorted(rs,key=lambda r:r['known_contribution'])
        report.append(f'\n### {hub}, {pid}\n')
        report.append(table(['Пара','Прямые конкуренты','Кресел конкурентов/сут.','Вклад P09, млн ₽','Вклад новый, млн ₽','Δ к KEEP, млн ₽','Эффект доступности прямых, млн ₽','LF'],[
            [r['pair'],','.join(r['direct_competitors']) or 'не найдены',num(r['competitor_daily_seats'],1,0),num(r['p09_original_route_known_contribution'],1e6),num(r['known_contribution'],1e6),num(r['delta_known_contribution'],1e6),num(r['direct_presence_effect_on_contribution'],1e6),pct(r['load_factor'])] for r in rs]))
        losses=[r['pair'] for r in rs if r['known_contribution']<0];directloss=[r['pair'] for r in rs if r['known_contribution']<0 and r['direct_competitors']]
        report.append('\nОтрицательный известный вклад: '+(', '.join(losses) or 'нет в этой конструкции')+'. Из них с найденными прямыми конкурентами: '+(', '.join(directloss) or 'нет')+'. Наличие прямого конкурента само по себе не доказывает причину убытка; разложение выше отделяет цену/ёмкость от операционных затрат.')
    report.append('\n## Исторические субсидии и коммерческий вклад\n')
    report.append(table(['Программа','Пар в конструкции','Пар с поддержкой 2026','В 2026 указан WZ','Начислено RW 2027–28'],[[r['programme_id'],r['proposed_unique_pairs'],r['matched_subsidy_2026_pairs'],r['rw_awarded_2026_pairs'],0] for r in subrows if r['programme_id'] in SPOTLIGHT+['REN_RADIAL','KZN_HYBRID']]))
    report.append('\n`programmes_subsidy_exposure.csv` содержит все конструкции; `subsidy_contribution_decomposition.csv` отделяет вклад фактически рассчитанных пар с историческим WZ, поддержкой соперников и без найденной поддержки. Долю «самоокупаемых коммерчески» нельзя честно определить по одному частичному subtotal: отсутствуют полные расходы и будущие договоры. Можно определить только пары с положительным известным вкладом при **нулевых новых выплатах RW**. Для новой поддержки минимальная потребность по известным компонентам равна max(0, −Δ subtotal); полная потребность включает неизвестные добавочные расходы и эффект собственного бизнеса.')
    report.append('\n## Деньги и условия решения\n')
    if (ROOT/'model_outputs/cashflow_diagnostics_summary.csv').exists():
        cash=readcsv(ROOT/'model_outputs/cashflow_diagnostics_summary.csv')
        report.append(table(['Программа, stress','Пик до 12.2028, млн ₽','С оплатой счетов до 02.2029, млн ₽'],[[p,num(next((r['known_incremental_peak_to2028_12'] for r in cash if r['programme_id']==p and r['config']=='comp_expansion_stress_2028'),None),1e6),num(next((r['known_incremental_peak_with_settlement_tail_to2029_02'] for r in cash if r['programme_id']==p and r['config']=='comp_expansion_stress_2028'),None),1e6)] for p in SPOTLIGHT]))
        report.append('\nПравая колонка погашает хвост тех же рейсов 2027–2028 без нового бизнеса 2029. Она показывает чувствительность к границе горизонта, а не прогноз денежных потоков действующей компании в 2029. Полные P06 accrual/cash bridges и terminal balances сохранены в cashflow_diagnostics.json.')
    report.append('P06 ledger сохранён: выручка поступает за 30 дней до перелёта, известные переменные счета оплачиваются по принятой P09 схеме +30 дней от конца месяца. Нулевой diagnostic peak возможен из-за этих лагов и сокращения расходов относительно KEEP. Это не подтверждение отсутствия кассового разрыва компании: opening cash, налоги, договоры базы/борта/запуска, проценты и остальной бизнес UNKNOWN. Платежи после горизонта и terminal obligations остаются в исходной логике P06. Ни общий денежный пик, ни полный результат не заполнены нулями.')
    report.append(f"\nДля защиты кейса используйте {best['programme_id']} как базовую расчётную альтернативу, а {stress['programme_id']} — как контроль осторожного рынка с экспансией. Сопоставляйте их расписания и equal-resource KEEP, а не складывайте независимые победившие хабы. Порог допустимых недостающих добавочных затрат в stress у базового лидера: **{num(get(best['programme_id'],'comp_expansion_stress_2028'),1e6)} млн ₽** за два года. Если он отрицательный, известная экономика уже требует улучшения цены/загрузки/расписания или поддержки; если положительный — это максимальный суммарный net missing-cost бюджет при прочих фиксированных неизвестных, а не одновременно допустимые бюджеты каждой статьи.")
    report.append('\nДо выбора сети нужно получить: тарифные бренды и paid baggage в одних и тех же dated quotes; полный недельный/сезонный календарь прямых конкурентов; booking-based OD и эластичности; реальный донор/альтернативное использование RW; стоимость базы, экипажей, ТО, ввода/выхода и резервов; право и сроки выплат. Условие пересмотра SVX — фактический ввод МС-21 и опубликованные частоты SU/FV по конкретным спицам, KZN — реальные волны N4/EO, востока — E170/частоты S7. Условие остановки построенной программы: устойчиво отрицательный полный добавочный результат после уточнения этих полей либо превышение согласованного финансирования. Дата окупаемости и достижение №2 настоящим пересчётом не установлены.')
    report.append('\n## Воспроизводимость\n')
    report.append(f"Legacy: **{manifest['legacy_programmes_checked']}/{manifest['programmes']} PASS**, отдельно сверены **{len(canonical)}** опубликованных canonical финалистов. Нейтральная замена competitor inclusive value: max ошибка RW {eq['neutral_intercept_check']['max_rw_carried_error']:.3g}. Проверки аллокатора: {manifest['allocation_sanity']['allocation_calls']} вызовов; max residual спроса {manifest['allocation_sanity']['max_demand_residual']:.3g}, max excess кресел RW {manifest['allocation_sanity']['max_seat_excess']:.3g}, конкурентов {manifest['allocation_sanity']['max_competitor_capacity_excess']:.3g}. Все {len(checks)} пригодных строк итогового CSV сверены с помесячными результатами. Полный run занял {num(manifest['elapsed_seconds'],60,1)} мин. Хеши использованных P09 и исследовательских входов не изменились.")
    report.append('\n```bash\nPYTHONDONTWRITEBYTECODE=1 python3 context/40_swarm_pricing_research_20261113/run_competitive_p09.py --rebuild-market\nPYTHONDONTWRITEBYTECODE=1 python3 context/40_swarm_pricing_research_20261113/test_competitive_p09.py\nPYTHONDONTWRITEBYTECODE=1 python3 context/40_swarm_pricing_research_20261113/run_input_sensitivities.py\nPYTHONDONTWRITEBYTECODE=1 python3 context/40_swarm_pricing_research_20261113/export_pricing_audit.py\nPYTHONDONTWRITEBYTECODE=1 python3 context/40_swarm_pricing_research_20261113/export_cash_diagnostics.py\nPYTHONDONTWRITEBYTECODE=1 python3 context/40_swarm_pricing_research_20261113/build_synthesis_report.py\n```')
    report.append('\nВоспроизводимость означает детерминированный offline-расчёт закреплённых входов. Рыночная валидация, реальное бронирование, dispatch и финансовые договоры этим не подтверждены. Использовано 731 датированное календарное число, а не умножение диагностической недели на 52. Ветви partial/delayed/none исходного P09 сохранены в коде и доступны через evaluate(delivery=...), но данная матрица по заданию пересчитана только при phased. Исторические результаты и вердикты P09 не переписаны. Из-за границы записи только в папку 40 не запускался общий скрипт fetch, который меняет context/16 и .git; расчёт строго закреплён на текущих локальных входах.')
    report.append('\n## Файлы\n')
    files=['market_competition_209.csv','market_competition_209.json','hub_weights_22.csv','competitive_p09_engine.py','run_competitive_p09.py','test_competitive_p09.py','recomputed_programmes_summary.csv','spotlight9_deep_dive.csv','spotlight9_deep_dive.json','model_outputs/run_manifest.json','model_outputs/legacy_equivalence.json','model_outputs/canonical_equivalence.json','model_outputs/pareto_frontiers.csv','model_outputs/robust_frontier.csv','model_outputs/top15_programmes.csv','model_outputs/hub_best_programmes.csv','model_outputs/programmes_subsidy_exposure.csv','model_outputs/subsidy_contribution_decomposition.csv','model_outputs/recomputed_monthly.csv','model_outputs/csv_reconciliation_checks.csv','model_outputs/input_sensitivities.csv','model_outputs/cashflow_diagnostics.json','model_outputs/cashflow_diagnostics_summary.csv','model_outputs/known_incremental_cash_monthly.csv','calibration/rw_pricing_audit.csv','calibration/market_quality.json','calibration/seasonal_price_indices.csv','calibration/competitor_carrier_route.csv','calibration/yandex_deduplicated_direct.csv','calibration/source_verification.json']
    report.append('\n'.join(f'- [{name}]({ROOT/name})' for name in files))
    (ROOT/'SYNTHESIS_REPORT_RU.md').write_text('\n\n'.join(report)+'\n')
    # Compact self-contained SVG chart rendered in HTML, for T3 inline preview.
    chartp=['MRV_SEASONAL','VOG_RADIAL','AER_HYBRID','AER_SEASONAL','MRV_HYBRID','KUF_RADIAL','VOG_HYBRID','SVX_RADIAL','SVX_BANK9']
    cs=[('p09_legacy_check','P09'),('comp_market_base','Рынок'),('comp_market_cautious','Осторожный'),('comp_expansion_stress_2028','Экспансия')]
    vals=[get(p,c) or 0 for p in chartp for c,_ in cs];lo=min(0,min(vals))/1e6;hi=max(vals)/1e6;scale=400/(hi-lo);zero=190-lo*scale
    svg=['<svg viewBox="0 0 720 710" style="width:100%;height:auto" role="img" aria-label="Изменение частичного операционного результата по программам">']
    for j,(c,label) in enumerate(cs):svg.append(f'<rect x="{15+j*170}" y="12" width="10" height="10" fill="var(--chart-{j+1})"/><text x="{30+j*170}" y="22" fill="var(--foreground)" font-size="12">{label}</text>')
    for tick in [-500,0,500,1000]:
        tx=zero+tick*scale
        svg.append(f'<line x1="{tx}" y1="48" x2="{tx}" y2="650" stroke="var(--border)"/><text x="{tx}" y="43" text-anchor="middle" fill="var(--muted-foreground)" font-size="11">{tick}</text>')
    for i,p in enumerate(chartp):
        y=55+i*66;svg.append(f'<text x="8" y="{y+18}" text-anchor="start" fill="var(--foreground)" font-size="12">{p}</text>')
        for j,(c,label) in enumerate(cs):
            v=(get(p,c) or 0)/1e6;x=zero+min(0,v)*scale;width=abs(v)*scale
            svg.append(f'<rect x="{x:.2f}" y="{y+j*12}" width="{width:.2f}" height="9" rx="2" fill="var(--chart-{j+1})"><title>{p}, {label}: {v:.1f} млн ₽</title></rect>')
    svg.append(f'<line x1="{zero}" y1="48" x2="{zero}" y2="650" stroke="var(--muted-foreground)"/><text x="190" y="685" fill="var(--muted-foreground)" font-size="12">Δ известного операционного subtotal к KEEP, млн ₽, 2027–2028</text></svg>')
    html='<html><head><meta charset="utf-8"><style>:root{font-family:var(--font-sans)}body{margin:0}p{font-size:13px;color:var(--muted-foreground)}svg text{font-family:var(--font-sans)}</style></head><body>'+''.join(svg)+'<p>Новые выплаты RW = 0. Полная прибыль и полная потребность в финансировании UNKNOWN.</p></body></html>'
    (ROOT/'model_outputs/programme_comparison.html').write_text(html)
    artifact_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.rglob('*') if p.is_file() and p.suffix in ('.py','.csv','.json','.md','.html') and p.name!='artifact_manifest.json' and p.parent.name!='swarm' and p.name not in ('fetch_apis.py','fetch_tp_only.py','yandex_hub_schedules.json','yandex_spotlight_search.json')}
    dump('model_outputs/artifact_manifest.json',dict(files=artifact_hashes,write_boundary=str(ROOT),p09_read_only=True,csv_checks=len(checks)))
    print(json.dumps(dict(report=str(ROOT/'SYNTHESIS_REPORT_RU.md'),csv_checks=len(checks),base_leader=best['programme_id'],stress_leader=stress['programme_id']),ensure_ascii=False))

if __name__=='__main__':main()
