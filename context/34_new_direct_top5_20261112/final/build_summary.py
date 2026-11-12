#!/usr/bin/env python3
"""Assemble published model rows and labelled arithmetic boundaries; no demand fitting."""
from pathlib import Path
import csv
import json

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent


def read(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def write(name, rows):
    with (HERE / name).open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def money(value):
    return f'{float(value) / 1e6:+.2f}'.replace('.', ',')


def clock(value):
    return value[11:16] + ' UTC' + value[-6:]


def main():
    ranks = read(STUDY / 'coordinator/rankings_both_assumptions.csv')
    programmes = read(STUDY / 'calculation/programme_comparison.csv')
    cancellation = read(STUDY / 'cancellation_control/comparison.csv')
    flights = read(STUDY / 'calculation/flights.csv')
    delay = read(STUDY / 'calculation/delay_events.csv')
    be = read(STUDY / 'calculation/break_even.csv')
    windows = read(STUDY / 'calculation/AER_window_comparison.csv')
    write('TOP5_BOTH_ASSUMPTIONS.csv', ranks)
    write('CONTROLS.csv', cancellation)
    full5 = sorted(ranks, key=lambda r: int(r['full_prior_rank']))[:5]
    stress5 = sorted(ranks, key=lambda r: int(r['asymmetric_stress_rank']))[:5]

    # A price boundary from already calculated NEW flight cost, relative to removing
    # the same donor. Fixed quantity, no outside own-RW loss/F; not a sales forecast.
    price_points = []
    for scenario in ('base', 'cautious'):
        row = next(r for r in cancellation if r['programme'] == 'AER1' and r['scenario'] == scenario
                   and r['adjacent_case'] == 'P05_ADJACENT_PRIOR')
        boundary = next(r for r in be if r['programme'] == 'AER1' and r['scenario'] == scenario
                        and r['axis'] == 'NET_FARE_SCALE_FIXED_Q')
        reference = float(boundary['model_net_a'])
        cost = float(row['new_flights_avoidable_cost_delta_month'])
        quantity = float(row['new_pair_journeys_month'])
        required_net = cost / quantity
        price_points.append(dict(scenario=scenario, new_flight_cost_month_RUB=cost,
            model_paid_journeys_month=quantity, reference_net_model_RUB=reference,
            required_net_at_model_quantity_RUB=required_net,
            raw_max_net_discount_vs_model_reference_RUB=reference-required_net,
            equal_direction_pax_each_flight_at_reference_net=cost/(8*reference),
            rotations_month=4, scenario_seats_per_flight=100, outside_RW_migration='UNKNOWN; zero only for this boundary',
            omitted_F_and_differential_parking='UNKNOWN; excluded boundary',
            actual_competitor_fare='UNKNOWN', actual_net_RW_yield='UNKNOWN',
            scope='New AER flights versus removing same donor; fixed quantity; NOT a clock-specific forecast',
            source='cancellation_control/comparison.csv + calculation/break_even.csv'))
    write('AER_PRICE_BOUNDARIES.csv', price_points)
    window_rows = []
    for time in ('07:00', '14:00', '21:00'):
        ws = [r for r in windows if r['clock_SVX'] == time]
        w0 = next(r for r in ws if r['shock_minutes'] == '0')
        for point in price_points:
            valid = w0['D0_valid'] == 'True'
            window_rows.append(dict(departure_SVX=time, date=w0['date'], scenario=point['scenario'],
                arrival_AER=w0['out_arrival_AER_local'], departure_AER=w0['return_departure_AER_local'],
                arrival_SVX=w0['return_arrival_SVX_local'], clock_status=w0['status'],
                confirmed_slot='UNKNOWN', observed_clock_price='UNKNOWN',
                model_price_boundary_net_RUB=point['required_net_at_model_quantity_RUB'] if valid else 'NOT_APPLICABLE_INVALID_D0',
                equal_direction_pax_each_flight=point['equal_direction_pax_each_flight_at_reference_net'] if valid else 'NOT_APPLICABLE_INVALID_D0',
                max_net_discount_vs_model_reference_RUB=point['raw_max_net_discount_vs_model_reference_RUB'] if valid else 'NOT_APPLICABLE_INVALID_D0',
                delay30_following=next(r['late_following'] for r in ws if r['shock_minutes'] == '30') or 'none in aircraft-only scenario',
                delay60_following=next(r['late_following'] for r in ws if r['shock_minutes'] == '60') or 'none in aircraft-only scenario',
                delay120_following=next(r['late_following'] for r in ws if r['shock_minutes'] == '120') or 'none in aircraft-only scenario',
                scope='Financial boundary freezes AER1 quantity/cost; no measured time premium; outside losses/F and crew/MRO unknown'))
    write('AER_WINDOW_DECISION.csv', window_rows)

    selected = ['SVX-KJA', 'TJM-MRV', 'TRI:SVX-AER-MRV']
    selected_flights = [r for r in flights if r['programme'] in selected and r['flight_id'].startswith('NEW-')
                        and r['departure_local'][:10] in ('2027-02-02', '2027-02-05')]
    write('THREE_ROTATIONS.csv', selected_flights)
    delay_rows = []
    for programme in selected + ['AER1']:
        for shock in (30, 60, 120):
            records = [r for r in delay if r['programme'] == programme and int(r['shock_minutes']) == shock
                       and r['window'] == 'MAIN' and r['target_group'] == 'NEW_PAIR'
                       and r['flight_id'].startswith('RET-')]
            assert records, (programme, shock)
            maximum = max(float(r['departure_delay_minutes']) for r in records)
            delay_rows.append(dict(programme=programme, initial_hold_min=shock,
                max_retained_departure_delay_min=maximum,
                late_retained_departures=sorted({r['flight_id'] for r in records if float(r['departure_delay_minutes']) > 0}),
                scope='Aircraft-only; worst of separately shocked NEW_PAIR legs; crew/rest/slots/cancellation not established',
                source='calculation/delay_events.csv'))
    write('DELAY_SUMMARY.csv', delay_rows)

    data = dict(period='2027-02-01/2027-02-28', unit='million constant RUB2026',
        qualified_new_routes=0, candidates=ranks, programmes=programmes, controls=cancellation,
        price_boundaries=price_points, window_decisions=window_rows, rotations=selected_flights, delays=delay_rows,
        primary_source_truth='not established for OD/yield/own-RW absence/free aircraft/slots',
        scope='P-minus-KEEP before unknown costs; priors are scenarios, not observed demand')
    (HERE / 'DATA.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

    names = {'GOJ-KJA':'Нижний Новгород—Красноярск', 'TJM-MRV':'Тюмень—Минеральные Воды',
             'CEK-MRV':'Челябинск—Минеральные Воды', 'GOJ-TOF':'Нижний Новгород—Томск',
             'SVX-KJA':'Екатеринбург—Красноярск', 'SVX-IKT':'Екатеринбург—Иркутск', 'OMS-PEE':'Омск—Пермь'}
    reasons = {'GOJ-KJA':'Командировки и поездки к близким; преимущество прямого перелёта надо доказать относительно пересадки.',
               'TJM-MRV':'Отдых и лечение на Кавминводах, обратные поездки после отдыха; конкурируют цена и дни.',
               'CEK-MRV':'Отдых и лечение; новый RW должен предложить преимущество перед существующим nonstop.',
               'GOJ-TOF':'Поездки к близким, учёба и командировки; объём и причины выбора пока не измерены.',
               'SVX-KJA':'Поездки к близким и деловые поездки; выбирать RW будут только при подходящей цене и времени.'}
    report = ['# Новые прямые маршруты: итог для команды', '',
      '**Готов условный отбор, а не пять доказанно новых линий.** Из12 пар ни по одной не установлено одновременно актуальное отсутствие собственного nonstop RW, продаваемый объём и свободный самолёт. Немедленный запуск не обоснован. Первой проверять Екатеринбург—Красноярск: по рынку есть опубликованное конкурентное предложение, а результат меньше зависит от доходов двух соседних плеч. Сначала выяснить, нет ли уже собственного RW; тогда это усиление частоты, а не новый маршрут.', '',
      'Приоритет проверки не равен максимальной модельной прибыли: при всех P05 priors лидирует Нижний—Красноярск; при стрессовом обнулении соседних доходов — Екатеринбург—Красноярск. Независимая проверка выявила эту зависимость; прежний единственный рейтинг исправлен.', '',
      'Срез: свежие P08/P09 и шаг-1, источники на12.11.2026; публикации на16–22ноября и февраль2027 разделены. Четыре полные недели01–28.02.2027. Один условно доступный действующий RRJ в Екатеринбурге и отдельный резерв, одинаковые задания-доноры. Новых SJ нет. Деньги ниже — изменение переменного вклада к одному KEEP, млн ₽2026 за февраль, до неизвестных F/резерва/парковки и внешнего перетока RW. Спрос и тарифы P05 — сценарии.', '',
      '|Кандидат, порядок полного prior|Тип|Все плечи: база / осторожно|Асимметричный стресс: база / осторожно|Кто может полететь — гипотеза|',
      '|---|---|---:|---:|---|']
    for r in full5:
        label = 'A?' if r['classification'] == 'UNKNOWN' else 'B?'
        report.append(f'|{r["full_prior_rank"]}. {names[r["pair"]]}|{label}|{money(r["base_full_prior_RUB"])} / {money(r["cautious_full_prior_RUB"])}|{money(r["base_asymmetric_stress_RUB"])} / {money(r["cautious_asymmetric_stress_RUB"])}|{reasons[r["pair"]]}|')
    report += ['',
      '**A?** — предполагаемый свободный коридор, но полного датированного покрытия для доказательства отсутствия nonstop нет. **B?** — опубликован конкурентный nonstop; собственный RW не подтверждён и его отсутствие тоже не доказано. По каждой паре спрос туда/обратно, помесячная сезонность, сравнимая цена с20кг и выбор времени остаются непроверенными. Перечисленные цели поездки не контракты и не численный спрос. Поезда и пересадки не получили сопоставимой полной корзины времени/цены; подтверждённую экономию не заявляем.', '',
      'Стресс выключает доходы соседних плеч треугольника, сохраняя его расходы; у челночной программы весь новый рынок остаётся. Это намеренно асимметричный стресс, не единый реалистичный базовый сценарий. Его отдельная очередь: ' + ', '.join(names[r['pair']] for r in stress5) + '. Оба допущения показаны равноправно в [CSV](final/TOP5_BOTH_ASSUMPTIONS.csv). У Нижний—Красноярск восстановление55,93% разницы соседней выручки меняет порядок с Екатеринбург—Красноярск; это денежная чувствительность, не прогноз продаж.', '',
      '**Треугольная прямая сеть сохранена.** Контроль Екатеринбург—Сочи—Минводы—Екатеринбург идёт во вторник, обратная ориентация — в пятницу. Все6плеч оплачены. AER1/AER2 — отдельные челночные контроли, а не замена всей стратегии. Полная авторская сеть сохранена с её исходным ресурсом и не уменьшена молча до одного борта.', '',
      '|Контроль|База|Осторожно|', '|---|---:|---:|']
    labels = {'KEEP':'Сохранить расписание', 'CANCEL_TUE_KEEP_FRI':'Снять вторничный донор без замены',
              'CANCEL_BOTH':'Снять оба донора без замены', 'AER1':'Сочи:1 дополнительный оборот/нед.',
              'AER2':'Сочи:2 дополнительных оборота/нед.', 'TRI:SVX-AER-MRV':'Треугольник Сочи—Минводы'}
    for name in ('KEEP','CANCEL_TUE_KEEP_FRI','CANCEL_BOTH','AER1','AER2','TRI:SVX-AER-MRV'):
        values = {r['scenario']:r for r in cancellation if r['programme'] == name and r['adjacent_case'] == 'P05_ADJACENT_PRIOR'}
        report.append(f'|{labels[name]}|{money(values["base"]["known_P_minus_KEEP_month"])}|{money(values["cautious"]["known_P_minus_KEEP_month"])}|')
    report += ['',
      'В осторожном сценарии сами новые рейсы Сочи дают −1,95млн ₽ для AER1 и −3,91млн для AER2; треугольник — −6,93млн относительно снятия тех же доноров. Поэтому положительная дельта к слабому модельному KEEP не доказывает необходимость нового рейса. Это не утверждение, что реальные задания RW убыточны, и не рекомендация их отменять: реальные продажи, избегаемые расходы, обязательства, поддержка и затраты простоя неизвестны. Общие расходы снятия донора одинаковы у соответствующих вариантов отмены и замены и повторно не вычитаются.', '',
      'В BASE два челночных оборота опережают треугольник всего на0,121млн ₽/месяц; в осторожном — на3,020млн. Различающиеся расходы/продажи могут перевернуть это сравнение. Без соседних доходов треугольник даёт −11,84/−14,06млн; это стресс, не доказательство неэффективности треугольников.', '',
      '**Обороты и окупаемость.** [Три конкретных программы](final/THREE_PROGRAMMES.md) содержат даты, местные часы/UTC, задержки30/60/120 и условные пороги. В [таблице окон Сочи](final/AER_WINDOW_DECISION.csv)07:00/14:00/21:00 — сценарные часы, не подтверждённые слоты. Вылет21:00 уже без задержки конфликтует со следующими заданиями. Остальные окна требуют реального борта, его готовности, экипажа, ТО, блоков и слотов. Стоимостной расчёт не снимает превышение диагностических8ч налёта; это ограничение модели, не норма рабочего времени экипажа.', '',
      f'Для новых рейсов Сочи отдельно от эффекта снятия донора при100 проданных местах на каждом плече и нулевой внешней потере RW условный net-порог — {price_points[0]["required_net_at_model_quantity_RUB"]:.0f} ₽ в базе и {price_points[1]["required_net_at_model_quantity_RUB"]:.0f} ₽ в осторожном. При заданном модельном net нижняя симметричная граница — {price_points[0]["equal_direction_pax_each_flight_at_reference_net"]:.1f}/{price_points[1]["equal_direction_pax_each_flight_at_reference_net"]:.1f} пассажира на каждый вылет при100 сценарных креслах; это не прогноз спроса. В осторожном net-порог выше модельного тарифа13 241 ₽: положительной скидки относительно этого ориентира нет. Фактические тарифы и допустимая скидка не подтверждены. Груз не добавлен: нет заказа, ставки и проверенной свободной ёмкости. Чтобы изменить осторожный выбор AER1 против снятия того же донора, груз должен дать минимум1,955млн ₽ дополнительного net-вклада за месяц уже после его перевозочных расходов, плюс остальные различающиеся потери. Это денежный порог, не найденные заказы.', '',
      '**Одно условие запуска:** новая программа должна давать больший проверенный результат, чем лучшая допустимая альтернатива — KEEP, снятие тех же заданий или другой оборот, — после всех различающихся расходов, собственного перетока и потерь донора. Одновременно должны быть подтверждены борт, вариант/нагрузка, экипажи, ТО и слоты. Сейчас это условие не доказано.', '',
      'У RW запросить в первую очередь:', '',
      '1. Полный зимний operated/marketed календарь, а затем обезличенные продажи по OD, направлениям, датам и времени: пассажиры, net после сборов/возвратов/комиссий, старые клиенты и замещение освободившихся кресел. Начать с SVX—KJA и AER; если собственный nonstop уже есть, переклассифицировать в частоты.',
      '2. Фактический оборот и задания конкретного действующего борта во вторник/пятницу и после них; блоки, модификация/AFM, загрузка и топливо, экипажи/отдых, ТО, отдельный резерв и подтверждение слотов обоими аэропортами.',
      '3. Маржу снятых заданий по действительно избегаемым расходам; цены топлива/обслуживания, обязательства и компенсации при снятии, поддержку по конкретным договорам, стоимость простоя против полётов. По новым рынкам — сопоставимые котировки и подтверждённые покупатели/гарантированные блоки, а не население или список предприятий.', '',
      '[Независимое ревью](review/README.md):16 проверок PASS, вердикт CHANGES. Координатор исправил объяснение;18 прежних численных артефактов побайтно сохранены. Дополнительный контроль снятия доноров отдельно проверен координатором:24 строки сравнения,240 ledger-строк,560 физических строк и32 парных порога; новой приёмки Astra ему не приписываем. [Полные расчёты](calculation/README.md), [контроль отмены](cancellation_control/README.md), [проверка итоговой сборки](final/verify.py). Решение команды не объявляется принятым.']
    (STUDY / 'RESULTS.md').write_text('\n'.join(report) + '\n')

    details = ['# Три предметные программы', '',
      'Контролируемые сценарии, не фактический хвост. Один действующий E1 в SVX, отдельный неподтверждённый резерв R1; все следующие задания одинаковы. Времена показываются местными с UTC-смещением. Период — февраль2027; ниже первая неделя, затем тот же вторник/пятница повторён четыре раза.', '']
    for programme in selected:
        details += [f'## {programme}', '', '|Дата|Плечо|Вылет|Прилёт|', '|---|---|---|---|']
        for r in selected_flights:
            if r['programme'] == programme:
                details.append(f'|{r["departure_local"][:10]}|{r["origin"]}→{r["destination"]}|{clock(r["departure_local"])}|{clock(r["arrival_local"])}|')
        ds = [r for r in delay_rows if r['programme'] == programme]
        details += ['', 'Максимальное опоздание следующих сохранённых вылетов при отдельных задержках нового плеча30/60/120мин: ' +
                    ' / '.join(str(int(r['max_retained_departure_delay_min'])) for r in ds) + 'мин. Запас поглощает эти задержки только по готовности самолёта; экипаж и ТО не проверены.', '']
        if programme in ('SVX-KJA', 'TJM-MRV'):
            br = [r for r in be if r['programme'] == programme and r['axis'] == 'SYMMETRIC_JOINT_Q_BOUNDARY']
            nr = [r for r in be if r['programme'] == programme and r['axis'] == 'NET_FARE_SCALE_FIXED_Q']
            details += ['Порог центральной пары в асимметричном стрессе, **без выручки соседних плеч**, до внешнего перетока/F; это нижняя денежная граница при фиксированных остальных потоках. В обе стороны принято одинаковое число продаж, четыре вылета каждого направления:', '', '|Сценарий|Пассажиров на каждый вылет|Net на модельном числе пассажиров|', '|---|---:|---:|']
            for r in br:
                net = next(n for n in nr if n['scenario'] == r['scenario'])
                details.append(f'|{r["scenario"]}|{float(r["q_a_required"])/4:.1f}|{float(net["net_a_required"]):.0f} ₽|')
            details += ['', 'Это не два независимых минимума спроса. Для треугольника требование выше100 означает, что одна центральная пара не покрывает всю цепочку; нужны доходы других плеч или снижение затрат. Оно не доказывает невозможность рентабельного треугольника с подтверждённой соседней выручкой.', '']
        else:
            details += ['Весь цикл продаёт три разных рынка. Центральная AER—MRV не обязана одна покрывать все расходы. Full-prior результат+11,659/+6,202млн ₽; без выручки двух связей сSVX −11,845/−14,064млн. В осторожном по сравнению со снятием обоих доноров новый цикл даёт −6,930млн. Достаточность продаж проверяется по сумме net выручки всех шести направленных плеч, не умножением кресел на желаемую загрузку.', '']
    details += ['Следующий KEEP начинается в23:55SVX в выбранном B30-контроле. У челночного AER14:00 запас55мин сверх обслуживания: +120 даёт до65мин опоздания следующего вылета; вылет07:00 имеет больший запас. Это отличается от прежнего G390/00:30 и не должно смешиваться с его числами.', '',
                'Все положительные новые программы сохраняют флаг превышения диагностических8BH и неизвестные crew/MRO/slots/type/payload/release. Численная согласованность часов и поглощение задержки не являются эксплуатационным допуском. Цена резерва, вероятность, стоимость минуты и автоматическая отмена не выдуманы.']
    (HERE / 'THREE_PROGRAMMES.md').write_text('\n'.join(details) + '\n')
    ai = [
      ('first-pass new markets','gpt-6-luna','UNKNOWN template; external search not performed; excluded as factual admission'),
      ('first-pass competitors','gpt-6-luna','Partial generator output; excluded as canonical input'),
      ('fresh P08/P09 audit','gpt-6.1-sol','Local version/contract/API verification; no market calibration'),
      ('targeted new-market recovery','gpt-6.1-sol','Real external requests and explicit source limitations'),
      ('targeted competitor recovery','gpt-6.1-sol','Primary/labelled secondary schedule evidence; RW absence unproved'),
      ('joint calculation','gpt-6.1-sol','Executed model, calendars, thresholds and reproducibility'),
      ('independent review','gpt-6-astra','16 executed checks; CHANGES, not unconditional acceptance'),
      ('cancellation control','gpt-6.1-sol','Executed two cancellation counterfactuals using same monthly allocation'),
      ('coordinator','gpt-6.1-sol','Source/code inspection, explanatory fixes, views and scoped independent control checks')]
    write('AI_USE.csv', [dict(role=role, model=model, actual_work=work,
          limitation='No model output alone proves observed demand, current own-RW absence, profit or dispatch')
          for role, model, work in ai])
    template = HERE / 'chart_template.html'
    if template.exists():
        chart_data = dict(qualified_new_routes=0, candidates=ranks,
            controls=[{key: row[key] for key in ('programme', 'scenario', 'adjacent_case',
                'known_P_minus_KEEP_month', 'diagnostic_8BH_failures')} for row in cancellation])
        (HERE / 'CHART_DATA.json').write_text(json.dumps(chart_data, ensure_ascii=False, indent=2) + '\n')
        (HERE / 'COMPARISON.html').write_text(template.read_text().replace('__DATA__',
            json.dumps(chart_data, ensure_ascii=False).replace('</', '<\\/')))
    print(json.dumps({'top5_full_prior':[r['pair'] for r in full5], 'top5_stress':[r['pair'] for r in stress5],
                      'qualified_new_routes':0, 'route_examples':selected, 'new_models_fitted':False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
