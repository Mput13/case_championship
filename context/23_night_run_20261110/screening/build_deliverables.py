#!/usr/bin/env python3
"""Build Russian research handoff and a chart from verified local outputs."""
import html
import json
from pathlib import Path
import reproduction as r

OUT=Path(__file__).resolve().parent

def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
        ['| '+' | '.join(str(x).replace('|',' / ').replace('\n',' ') for x in row)+' |' for row in rows])

def main():
    facts=json.loads((OUT/'report_facts.json').read_text());manifest=json.loads((OUT/'source_manifest.json').read_text())
    case=json.loads((OUT/'case_source_check.json').read_text())
    # First draft of the tiny case fragment included a public officer name; remove
    # the irrelevant fragment before packaging, keep its document hash.
    case['short_fragments']=[s.split('Генеральный')[0].strip() for s in case.get('short_fragments',[])]
    r.dump('case_source_check.json',case)
    comps=r.read_csv(OUT/'comparison.csv')
    index={(x['origin_model'],x['scenario']):x for x in comps}
    def pick(origin,scenario):return index[origin,scenario]
    key_specs=[('front_historical','author_min0','front2272, без фильтра 500 км (история)'),
        ('front_historical','author_min500','front2272, 500 (история, score mismatch)'),
        ('nastya','author_min0','Настя 2f, без фильтра 500 км'),('nastya','author_min500','Настя 2f, 500'),
        ('tsiri_stage22','base|0|expansion_allowed|balanced','Цири 6ec stage22, без фильтра 500 км'),
        ('tsiri_stage22','base|500|expansion_allowed|balanced','Цири 6ec stage22, 500'),
        ('tsiri_historical','stage11|base|all','Цири 91 stage11, все 10'),
        ('tsiri_historical','stage11|base|new_node','Цири 91 stage11, только 8 new_node'),
        ('tsiri_historical','stage12|UFA_RRJ_admission_confirmed|base','Цири 91 stage12, уточнённый technical UFA')]
    ranking=table(['Версия и режим','N','Топ-3','Баллы (собственная шкала)','Проверка'],[
        [label,pick(a,b)['universe_n'],pick(a,b)['top3'],' / '.join(f"{float(pick(a,b)[k]):.6f}" for k in ['score1','score2','score3']),pick(a,b)['replay_status']]
        for a,b,label in key_specs])
    radius=[]
    for threshold in [0,300,500,800]:
        a=pick('controlled_common_stage22',f'historical_SVO_DME_VKO_SVX|{threshold}|expansion_allowed|balanced')
        b=pick('controlled_common_stage22',f'historical_SVO_DME_VKO_SVX|{threshold}|strict_new|balanced')
        radius.append([threshold,a['universe_n'],b['universe_n'],a['top3'],a['excluded'] or '—'])
    radiust=table(['Порог, км','N expansion','N strict_new','balanced топ-3 в обоих режимах','Исключены радиусом (expansion)'],radius)
    profiles=table(['Профиль (предложение автора)','Топ-3 при 500 км','Удаление одного критерия меняет состав'],[
        [x['profile'],x['top3'],next(f"{s['top3_set_changes']} из {s['n']}" for s in facts['loo_by_profile'] if s['threshold']=='500' and s['profile']==x['profile'])]
        for x in facts['profiles500']])
    loo=table(['Отключён только критерий','Новая тройка при 500 км'],[[x['omitted'],x['top3']] for x in facts['balanced500_loo'] if x['same_top3']=='False' and x['kind']=='leave_one_out'])
    bounds=table(['Город','Центр','Нижняя–верхняя оценка','UNKNOWN / INDIRECT','Вес с диапазоном','Место в крайних сценариях'],[
        [x['iata'],f"{float(x['score']):.6f}",f"{float(x['score_low']):.6f}–{float(x['score_high']):.6f}",
        f"{float(x['unknown_weight_share']):.0%} / {float(x['indirect_weight_share']):.0%}",f"{float(x['uncertain_weight_share']):.0%}",
        f"{x['rank_best']}–{x['rank_worst_inclusive']}"] for x in facts['balanced500_bounds'] if x['iata'] in ['OMS','REN','BAX','KUF']])
    gap=r.read_csv(OUT/'bax_kuf_gap.csv')
    gapt=table(['Критерий','Вклад в BAX − KUF'],[[x['criterion'],f"{float(x['BAX_minus_KUF_contribution']):+.9f}"] for x in gap if abs(float(x['BAX_minus_KUF_contribution']))>1e-15])
    criteria=r.read_csv(OUT/'criteria_comparison.csv')
    cm={x['criterion']:x for x in criteria if x['origin_model']=='nastya'}
    st={x['criterion']:x for x in criteria if x['origin_model']=='tsiri_stage22'}
    weightst=table(['Критерий','Направление','Настя: пунктов / доля','stage22: пунктов / доля'],[
        [k,st[k]['direction'],f"{float(cm[k]['weight']):g} / {float(cm[k]['normalized_weight']):.1%}",
            f"{float(st[k]['weight']):g} / {float(st[k]['normalized_weight']):.1%}"] for k in cm if float(cm[k]['weight']) or float(st[k]['weight'])])
    shat=table(['Вход','Git author','Точный SHA'],[[k,v['author'],v['sha']] for k,v in manifest['commits'].items()])
    report=(OUT/'report_template.md').read_text()
    tokens={'@@SHA_TABLE@@':shat,'@@RANKING@@':ranking,'@@RADIUS_TABLE@@':radiust,
        '@@GAP_TABLE@@':gapt,'@@WEIGHTS_TABLE@@':weightst,'@@PROFILES_TABLE@@':profiles,
        '@@LOO_TABLE@@':loo,'@@BOUNDS_TABLE@@':bounds,
        '@@CASE_SHA@@':case.get('sha256',case.get('held_sha256','UNKNOWN'))}
    for token,value in tokens.items():report=report.replace(token,value)
    assert '@@' not in report
    (OUT/'report.md').write_text(report)
    results=f'''# Результаты контролируемого опыта

План: [experiment_plan.md](experiment_plan.md). Общий источник — 20 городов stage22; utility и шкалы закреплены до отсева. Всего 80 конфигураций и 204 сравнения с изменением одного фактора. Пять профилей — авторские предложения, не утверждённые командой веса.

{radiust}

ZIA/SVX против исторических SVO/DME/VKO/SVX: ни одного изменения допуска или тройки в 40 парных сравнениях на четырёх проверенных порогах. Баллы выживших неизменны. Strict_new удаляет подтверждённые опоры; остальные города допущены условно. Наземное время и переток не измерены.

{profiles}

Balanced, порог 500 км: удаление одного критерия меняет состав в четырёх из 11 случаев.

{loo}

{bounds}

Равные фиксированные utility у 20 городов: авторская граница мест 1..1, локальная граница с учётом равенства 1..20. Основная тройка stage22 исправлением ties не изменилась. Исторический front2272/min500 сохранён со статусом MISMATCH_HISTORICAL_DERIVED; максимальное расхождение score с округлённым экспортом 0,001224132. Остальные проверки — [validation.json](validation.json). Ни frequency, ни доля изменений в этой сетке не являются вероятностью успеха.
'''
    (OUT/'experiment_results.md').write_text(results)
    findings=[
        ('S01','P2_policy','DECISION_REQUIRED','Порог 500 км меняет допуск; командная политика не утверждена',
         'Без фильтра CEK/UFA/OMS, с 500 км OMS/REN/BAX на одних данных; в кейсе нет правила 500 км',
         'Выбрать правило явно; сохранить вариант без фильтра и чувствительность 300/500/800; не выводить долю перетока из радиуса',
         'case_source_check.json;distances.csv;comparison.csv'),
        ('S02','P2_material','SENSITIVITY','Третье место BAX/KUF чувствительно к малым изменениям',
         'Разрыв 0.000721148; один гипотетический день сообщений меняет score на 0.001009174',
         'Показать обоих кандидатов, профили и UNKNOWN bounds; сохранить авторский порядок и проверить решающий факт',
         'bax_kuf_gap.csv;unknown_bounds.csv'),
        ('S03','P2_material','REPRODUCED_LOCAL_FIX','Диапазон места не учитывает допустимый порядок точных равенств',
         '20 одинаковых фиксированных utility дают авторское 1..1; локальная проекция с ничьей 1..20; default top3 прежний',
         'Показывать центральный min/max tied rank; включить равенство в worst-bound, сохранить tied-группу на границе',
         'inputs/tsiri_stage22/scripts/finalize_stage1_audit.py:56;tie_fixture.json'),
        ('S04','P2_method','RISK','Связанные proxy могут повторно учитывать один механизм спроса',
         'Вес семейства 45%; balanced500 меняет состав в 4/11 LOO; без семейства KHV/VVO/OMS',
         'Определить самостоятельный смысл критериев и групповой вес; сохранить проверку без семейства; не называть proxy наблюдённым OD',
         'profiles.csv;robustness.csv;criteria_comparison.csv'),
        ('S05','P2_method','LIMITATION','Погода UNKNOWN при весе 7% не различает центральные оценки',
         'Все utility 0.5; удаление weather сохраняет весь порядок; независимые погодные bounds добавляют ширину 0.07',
         'Разделить общий нейтральный вклад и независимую неопределённость; не объявлять погодные данные подтверждёнными',
         'criterion_matrix.csv;robustness.csv'),
        ('S06','P2_repro_history','HISTORICAL_MISMATCH','Исторический front2272/min500 не воспроизведён в точности экспорта',
         'max|replay−saved| = 0.001224132; last365_days расходится в шести строках; тройка совпала',
         'Сохранить mismatch; при повторном использовании старой модели выпускать отдельную согласованную ревизию',
         'front_historical_min500_mismatch.csv;front_historical_min500_normalization_mismatch.csv'),
        ('S07','P2_provenance','CORRECTED_IN_HANDOFF','Старый каталог объединял mput/Mput13; это не текущая идентификация',
         'По пользователю Цири=mput, координатор=Mput13, Константин отдельный; его независимая top3 в просмотренном каталоге не найдена',
         'Использовать актуальное авторство, сохранять исторические подписи; не выводить личность по похожему логину',
         'source_manifest.json;inputs/coordinator/context/19_report_update_20261110/team_update_manifest.json'),
        ('S08','P2_scope','DECISION_REQUIRED','Контракт нового узла отличается от развития опоры',
         'Strict симметрично удаляет KUF/KZN/AER/MCX; остальные UNKNOWN допущены условно',
         'Выбрать контракт; сохранить expansion; отдельно подтвердить физические борта, экипажи, MRO и MCT',
         'eligibility.csv;source_manifest.json'),
        ('S09','P2_acceptance','LIMITATION','Проверка производной арифметики не подтверждает raw или прибыль сети',
         '140 конфигураций и 360 utility-ячеек воспроизведены; raw, полная сеть и прибыль не пересчитывались',
         'Сохранить слои доказательств и NOT_RUN; использовать city score как очередь сетевых проверок',
         'validation.json;evidence_levels.json'),
        ('S10','P3_documentation','NEW_EVIDENCE','Чувствительность ZIA/SVX ранее имела статус NOT_RUN',
         'Теперь 80 общих конфигураций, 40 пар сравнения точек; 0 изменений допуска/тройки при 0/300/500/800',
         'Обновить только этот узкий статус; не переносить вывод на непроверенные пороги или реальные ресурсы баз',
         'distances.csv;one_factor_deltas.csv'),
    ]
    r.write_csv('findings.csv',[dict(id=x[0],severity=x[1],status=x[2],finding=x[3],delta=x[4],minimal_fix=x[5],evidence=x[6]) for x in findings])
    r.dump('evidence_levels.json',dict(
        raw_external=dict(status='NOT_REPLAYED',note='No full raw export; original aviation/Telegram/NOAA records not reconstructed; primary case fetched separately with SHA only'),
        author_derived=dict(status='FROZEN',files=58,coordinate_projection_rows=25,note='criteria.v may itself be computed or imputed; never label every v a raw fact'),
        validated_arithmetic=dict(status='PASS_SCOPED_EXCEPT_FRONT_HISTORY',stage22_configs=140,stage22_rows=2170,accepted_utility_cells=360,
            historical_stage11_configs=8,historical_stage12_configs=16,nastya_scores=35,controlled_configs=80,loo_configs=104),
        historical_exception=dict(status='MISMATCH',model='front2272_min500',max_score_delta=.0012241323280967054),
        corrected_projection=dict(stage22_ties='tie-aware min/max including equality; author files preserved',nastya_normalization='fixed20 sensitivity separately labelled'),
        validity=dict(primary_city_facts_revalidated=False,current_physical_bases_verified=False,profitability_accepted=False,team_weights_approved=False)))
    r.dump('external_sources.json',dict(as_of='2026-11-10',sources=[
        dict(url='https://mai-way.ru/tasks/red-wings/',check='case_source_check.json',role='primary requirements; no500kmrulefound'),
        dict(url='https://assets.publishing.service.gov.uk/media/5a790545e5274a2acd18b975/1132618.pdf',
            title='Multi-criteria analysis: a manual',publisher='UK Government',published='2009',read='2026-11-10',
            pages='printed37-38,63-64,68-69',use='meaning of criteria, preference independence, swing weighting, sensitivity; no aviation thresholds'),
        dict(url='https://www.oecd.org/content/dam/oecd/en/publications/reports/2008/08/handbook-on-constructing-composite-indicators-methodology-and-user-guide_g1gh9301/9789264043466-en.pdf',
            title='Handbook on Constructing Composite Indicators',publisher='OECD/EU/EC-JRC',published='2008',read='2026-11-10',
            pages='printed32-35,117-119',use='related indicators, uncertainty, normalization, leave-one-out; no estimated RW weights')]))
    build_chart(comps)
    print(json.dumps(dict(report_bytes=(OUT/'report.md').stat().st_size,findings=len(findings))))

def build_chart(comps):
    rows=[x for x in comps if x['origin_model']=='controlled_common_stage22' and x['bases']=='historical_SVO_DME_VKO_SVX' and x['profile']=='balanced' and x['mode']=='expansion_allowed']
    colors=['var(--chart-1,#76a5d3)','var(--chart-2,#7bb4a1)','var(--chart-3,#c3a777)'];parts=[]
    names={'CEK':'Челябинск','UFA':'Уфа','OMS':'Омск','PEE':'Пермь','REN':'Оренбург','BAX':'Барнаул','KJA':'Красноярск'}
    for row in rows:
        cells=[]
        for idx,code in enumerate(row['top3'].split(' / ')):
            val=float(row[f'score{idx+1}'])
            cells.append(f'<div class="candidate"><span>{html.escape(names[code])} <small>{code}</small></span><div class="track"><i style="width:{val*100:.3f}%;background:{colors[idx]}"></i></div><b>{val:.3f}</b></div>')
        parts.append(f'<section><div class="radius">{row["threshold_km"]} км<small>{row["universe_n"]} городов</small></div><div class="bars">'+''.join(cells)+'</div></section>')
    content='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
:root{color-scheme:light dark;font-family:var(--font-sans,Arial,sans-serif);color:var(--foreground,#d9dfe5)}html,body{margin:0;background:transparent}p{line-height:1.45;margin:0 0 18px}section{display:grid;grid-template-columns:78px 1fr;gap:18px;padding:15px 0;border-top:1px solid var(--border,#8885)}.radius{font-size:18px;font-weight:600}.radius small{display:block;margin-top:7px;font-weight:400;font-size:12px;opacity:.65}.candidate{display:grid;grid-template-columns:120px minmax(80px,1fr) 42px;gap:10px;align-items:center;font-size:13px;min-height:26px}.candidate small{opacity:.6;margin-left:4px}.track{height:10px;background:var(--secondary,#8882);border-radius:3px;overflow:hidden}.track i{display:block;height:100%}b{font-weight:500;text-align:right;font-variant-numeric:tabular-nums}.note{opacity:.7;font-size:12px;margin-top:17px}@media(max-width:440px){section{gap:8px;grid-template-columns:64px 1fr}.candidate{grid-template-columns:103px minmax(30px,1fr) 35px;gap:5px;font-size:12px}.candidate small{display:none}.radius{font-size:16px}}
</style><body><p>Топ-3 при изменении радиуса допуска<br><small>Общие данные stage22 · balanced · развитие опоры допускается</small></p>'''+''.join(parts)+'''<p class="note">Шкалы и баллы городов закреплены до фильтра. Смена SVO/DME/VKO/SVX на ZIA/SVX на этих порогах даёт те же тройки. Балл — сравнительный скрининг, не прибыль сети.</p></body></html>'''
    (OUT/'radius_chart.html').write_text(content)

if __name__=='__main__':main()
