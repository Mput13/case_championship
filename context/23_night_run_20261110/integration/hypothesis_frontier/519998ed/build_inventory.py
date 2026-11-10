#!/usr/bin/env python3
"""Classify all frozen specifications without changing author values or ranking cities."""
from pathlib import Path
import csv, json, collections

ROOT=Path(__file__).resolve().parent
H='6ed8788882e7b4d07044b4f6e686ff71eadd8ac5'
def read(p):return list(csv.DictReader(p.open()))
def write(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    original=read(ROOT/'inputs/hypotheses/candidates.csv')
    notes=json.loads((ROOT/'inventory_notes.json').read_text())
    assert [r[0] for r in notes]==[r['candidate_id'] for r in original]==[f'C{i:02}' for i in range(1,36)]
    geo=read(ROOT/'inputs/hypotheses/normalized/geometry_screen_sensitivity.csv')
    rows=[]
    for spec,n in zip(original,notes):
        ident,degree,change,result,unresolved,decision_test,queue=n
        g=[r for r in geo if r['candidate_id']==ident and r['screen_km']=='2300']
        row=dict(candidate_id=ident,title=spec['title'],author_ref=spec['author'],ancestor_ids=spec['ancestor_ids'],family_provenance=spec['family_provenance'],
                 source_commit=H,source_path='context/16_agent_research/hypotheses/candidates.csv',input_set_id='frontier-frozen-001',
                 author_network_form=spec['network_form'],author_operating_base=spec['operating_base'],author_paths=spec['proposed_paths'],
                 author_passenger_purpose=spec['passenger_and_purpose'],author_season_stay=spec['season_and_stay'],author_current_alternative=spec['current_alternative'],
                 author_product=spec['rw_product'],author_competitor_response=spec['competitor_and_response'],author_frequency=spec['frequency_proposal'],
                 author_resource_requirement=spec['resource_requirement'],author_stop_rule=spec['stop_rule'],author_specific_test=spec['specific_test'],author_data_request_ids=spec['data_request_ids'],
                 author_demand_status=spec['demand_status'],author_net_fare_status=spec['net_fare_status'],author_resource_status=spec['resource_status'],author_evaluation_status=spec['evaluation_status'],
                 change_degree=degree,airline_change=change,checked_result_and_scope=result,
                 geometry_paths_at_2300=len(g),paths_flagged_at_2300=sum(r['any_leg_over_screen']=='True' for r in g),
                 geometry_acceptance='SCENARIO_SCREEN_ONLY_NOT_DISPATCH',main_unresolved_parameter=unresolved,source_or_experiment_that_can_change_conclusion=decision_test,
                 queue_state=queue,classification='AGENT_PROPOSAL',new_acceptance='READ_AND_CLASSIFIED; no independent/source/market upgrade')
        rows.append(row)
    write(ROOT/'inventory35.csv',rows)
    with (ROOT/'inventory35.md').open('w') as f:
        f.write('# Реестр 35 продуктов\n\nАвтор всех конкретных спецификаций: GPT-6 Astra hypotheses role на `6ed8788882e7b4d07044b4f6e686ff71eadd8ac5`; семейства идей и ancestor IDs сохранены в CSV. Это продукты агентского исследования Михаила, не городской рейтинг Анастасии/Цири. Классификация текущего пакета — AGENT_PROPOSAL.\n\n')
        f.write('Все 35 исходных demand/net fare/resource = UNKNOWN; author evaluation_status = NOT_EVALUATED. Новые проверки не переписывают эти авторские поля. Geometry2300 — исследовательский screen, не утверждённая дальность/dispatch.\n\n')
        f.write('| ID / продукт | Изменение компании | Проверенный результат / граница | Главный неизвестный параметр | Проверка, способная изменить вывод |\n|---|---|---|---|---|\n')
        for r in rows:
            vals=[r['candidate_id']+' — '+r['title'],r['airline_change'],r['checked_result_and_scope'],r['main_unresolved_parameter'],r['source_or_experiment_that_can_change_conclusion']]
            f.write('| '+' | '.join(v.replace('|','/').replace('\n',' ') for v in vals)+' |\n')
    queue=[
      dict(queue_id='Q01',candidate_ids='C01',state='SELECTED_EXECUTED_HF01',reason='Сравнивает время/продукт с теми же рейсами рядом с вариантом новой базы; достаточно четырёх frozen сценарных плеч',uncertainty_removed='Точная граница MCT/turn/возврата, включая отказ M90; общие рейсы не равны бесплатному ресурсу',next_after_run='Actual no-new-base rotation, approved MCT/turn/slots, lost local margin',stop='Не менять спрос, mixed bundle или общий budget envelope'),
      dict(queue_id='Q02',candidate_ids='C07;C04',state='SELECTED_EXECUTED_HF07',reason='Прямой продукт из существующей базы вместо новой базы Омск; полный возврат/ночной календарь уже можно ограничить',uncertainty_removed='Сколько минут более раннего старта или позднего возврата обязательно; сам по себе замкнутый маршрут не свободный борт',next_after_run='Dated tail and next assignment, RW engineering block, crew/MRO and local fare',stop='Не объявлять донор/сбережение аренды, не оптимизировать KEEP/REPLACE/CANCEL'),
      dict(queue_id='Q03',candidate_ids='C14',state='SELECTED_EXECUTED_HF14',reason='Проверяет конкретный пассажирский продукт при прежнем предложении; даты доступны, рыночный/ценовой слой отсутствует',uncertainty_removed='Минимальная терпимость к дополнительным ночам и оставшиеся обязательные booking gates',next_after_run='Hotel admission/inventory/timezone, complete transfer and airline seats/fare; RW contract or full chain',stop='Не считать дату доступности оплаченной поездкой; не конвертировать bed-day в nights'),
      dict(queue_id='Q04',candidate_ids='C11;C33;C27;C28',state='DEFERRED_NO_NEW_RUN',reason='Полезные варианты малого изменения, но реальный baseline/остатки кресел не закреплены',uncertainty_removed='Потенциально добавка продукта без новой базы',next_after_run='Existing dated RW rotations/sales and bus obligations',stop='Не дублировать HF01 и не придумывать новую программу по карте'),
      dict(queue_id='Q05',candidate_ids='C02;C09;C15;C19;C35',state='DEFERRED_NO_NEW_RUN',reason='Следующие calendar/partner products требуют новых двусторонних дат и договора',uncertainty_removed='Ценность рабочего дня/возврата относительно incumbent/земли',next_after_run='Dated end-to-end comparator and commercial rights',stop='Не считать частоты или кодшеринг готовым продуктом'),
      dict(queue_id='Q06',candidate_ids='C10;C12;C18;C20;C32',state='DEFERRED_NO_NEW_RUN',reason='Механизм платного блока конкретен, но плательщик/оплата неизвестны',uncertainty_removed='Гарантированная маржа на нужные даты вместо прироста абстрактного OD',next_after_run='Allowed anonymised block specification and payment/return obligations',stop='Сайты предприятий, студенты и туризм не demand'),
      dict(queue_id='Q07',candidate_ids='C03;C05;C06;C13;C21;C22;C23;C24;C25;C26;C29',state='DEFERRED_NO_NEW_RUN',reason='Новые базы/remote/dispatch/partner contracts не разрешаются текущими входами',uncertainty_removed='Полный бюджет и физическая/продуктовая альтернатива',next_after_run='Current contracts/resource and differentiated endpoint product',stop='Историческое ТО, great-circle, социальная потребность не экономическая приёмка'),
      dict(queue_id='Q08',candidate_ids='C08;C16;C17;C30;C31;C34',state='DEFERRED_NO_NEW_RUN',reason='Dispatch, calibration, season, state trigger, actual fleet or recovery data needed',uncertainty_removed='Граница пригодности конкретного модуля',next_after_run='Named unresolved parameter in inventory35',stop='Не прогнозировать открытие, поставку, weather gain; общий reserve/accounting остаётся methods/cost')
    ]
    write(ROOT/'experiment_queue.csv',queue)
    degrees=[
      ('G0','Ничего не менять','C00','Прирост проекта0 по определению; прибыль компании UNKNOWN','Сохраняющиеся обязательства и действующая сеть','Baseline comparator, not RW policy'),
      ('G1','Время/продукт на тех же рейсах','C01-HF01;C11;C33;C14-HF14 passenger comparator','Число модельных/публикуемых рейсов не растёт','Реальная занятость/местные продажи/слоты/договор; HF01 не actual baseline','HF01/HF14 limited tests'),
      ('G2','Наземный или партнёрский подвоз','C27;C28;C35','Другой доступ к уже существующему рейсу','Один market pool, остаточные кресла, защита, revenue split','NOT_RUN'),
      ('G3','Добавить маршрут/частоту из существующей базы','C07;C14-RW;C09;C15;C19','Новый оплачиваемый full loop, все плечи включены','Окно борта/crew/ТО/dispatch и изменение базовых продаж','HF07 timing only; frequencies not optimised'),
      ('G4','Перенос занятого ресурса/замена типа','C31;C17','Новая программа вместо другого использования того же ресурса','Датированный донор, избегаемые статьи, обязательства и swap costs','NOT_RUN; no free resource'),
      ('G5','Новая база/хаб','C01;C03;C04;C05;C13;C21;C29','Базирование, экипажи, ТО, резерв, запуск/выход/оборотный капитал','Current contract and full budget; paid endpoint product','No new-base approval'),
      ('G6','Смешанная сеть','methods D+previous / direct+hub','Совместный инвентарь датированных рейсов и единый пул OD','Совместимость рынков/ресурсов/деньги по тому же периоду','Reserved to active methods; NOT_RUN_HERE')]
    write(ROOT/'network_change_degrees.csv',[dict(degree_id=a,degree=b,candidate_examples=c,change=d,acceptance_blocker=e,this_package=f,decision_status='OPEN_DECISION; smaller change is user comparison preference, not established RW policy') for a,b,c,d,e,f in degrees])
    (ROOT/'inventory_checks.json').write_text(json.dumps(dict(specifications=35,unique_ids=35,notes=35,selected_tests=3,source_author_fields_preserved=True,all_demand_fare_resource_unknown=all(r['demand_status']==r['net_fare_status']==r['resource_status']=='UNKNOWN' for r in original),new_city_score=False,geometry_rows=len(geo),unmatched_geometry_ids=sorted({g['candidate_id'] for g in geo}-{r['candidate_id'] for r in original})),indent=2)+'\n')
    print(json.dumps(dict(inventory=35,selected_tests=3,queue_groups=len(queue))))

if __name__=='__main__':main()
