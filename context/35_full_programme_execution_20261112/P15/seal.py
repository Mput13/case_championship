#!/usr/bin/env python3
"""Seal owned delivery. No Git operations."""
import hashlib,json,pathlib
P=pathlib.Path(__file__).resolve().parent
def digest(b):return hashlib.sha256(b).hexdigest()
def dump(n,o):(P/n).write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
files=[]
for p in sorted(P.rglob('*')):
    if not p.is_file():continue
    r=p.relative_to(P)
    if '__pycache__' in r.parts or r.as_posix() in ['output_manifest.json','handoff.json','handoff.md'] or (r.parts[0]=='qa' and p.suffix=='.html'):continue
    b=p.read_bytes();files.append(dict(path=r.as_posix(),sha256=digest(b),bytes=len(b)))
manifest={'package':'P15','version':'P15-stageA-ui-v2-root20','status':'STAGE_A_INTEGRATOR_READY_FINAL_QUANTITATIVE_BINDING_OPEN','write_scope':'context/35_full_programme_execution_20261112/P15/','files':files,'file_count':len(files),'bytes':sum(r['bytes'] for r in files),'hash_algorithm':'SHA256 file bytes','metadata_envelope_excluded':['output_manifest.json','handoff.json','handoff.md'],'temporary_runtime_excluded':['qa/*.html','__pycache__/'],'git_operations':'NONE','independent_P16_acceptance':'NOT_RUN'}
dump('output_manifest.json',manifest);mh=digest((P/'output_manifest.json').read_bytes())
coverage=json.loads((P/'integration_coverage.json').read_text())
handoff={'package':'P15','version':'P15-stageA-ui-v2-root20','status':manifest['status'],'manifest_sha256':mh,'files':len(files),'bytes':manifest['bytes'],'entry':'dashboard_candidate.html','data':'dashboard_data.json','claim_links':'claim_links.csv','adapter':'dataadapter.py','replay':'replay.py','import_contract':'ui_contract.json','root_approved_change':'Q-P09-UI01_UI_PROJECTION','P12_history_commit':'06207b1650bd1c83e0f0761b25d063f2c395ace7','author_panel_commit':'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6','coverage':coverage,'checks':{'source_offline':json.loads((P/'qa/verification.json').read_text())['count'],'native_interactions_1440':55,'native_interactions_390':55,'visuals':'desktop/narrow/projector-layout/direct/strategy/source; author review','actual_P09_binding':'NOT_RUN','actual_computed_scenario_switch':'NOT_RUN','P16_actual_full_results_120s_rehearsal':'NOT_RUN'},'remaining_stage_B':['exact accepted P09 quantitative root envelope/pin/manifest and result labels; projection contract known','P09 same-future KEEP/calendar/resource/choice/cost/cash acceptance','P10 reported-metric mapper/F07 before integrated share/number2','actual finalist preset and independent P16 rehearsal'],'boundaries':{'children':0,'Git_mutations':0,'outside_P15_writes':0,'public_Site':False,'author_branch_change':False,'new_paid_services':False,'external_messages':False,'bookings':False,'restarts':False,'server_started':False}}
dump('handoff.json',handoff)
(P/'handoff.md').write_text(f'''# P15: передача интегратора

Stage A интегратор готов. Откройте `dashboard_candidate.html`; сведения о данных и повторе — `README.md`. Авторская панель и четыре раздела P12 сохранены.

Manifest SHA256: `{mh}`. В payload {len(files)} файлов, {manifest['bytes']} байт; manifest/handoff — отдельный envelope без циклического хеша. Запись только P15; Git/children0.

Подключены все 20 sealed городов root6a6326c (160 кандидатов / 169 гипотез), 2274 продукта P02, 6 SVX + 57 Moscow программ P08, 87 международных карточек P02I, 128 capacity-only условий P10 и 4 карточки P11. 10745 claim links. P01_MONTHLY подключён как наблюдения; endpoint OD не установлен.

316 проверок источников/offline replay и 55 native interaction checks при 1440 / 390 px прошли. Визуальные снимки: `qa/`. Это авторская проверка, не P16.

**finalquantitativebinding OPEN.** Количественный ACCEPTED_FOR_UI root pin для реальных P09 projection data ещё не поступил. Q-P09-UI01 принят в `ui_contract.json`; P12 контракт сохранён историей. Точный P09 projection contract d721896... проверен; pending producer данные не подключены. Интегратор не подставляет demo и не суммирует денежные результаты в JS. Прямая команда подключения — в README; точный запрос производителю — `p09_contract_request.md`.

Stage B: sealed P09 и валидация JSONpaths/hash convention, общий KEEP/resource/choice/cash, P10 metric mapper/F07, preset финалиста и P16 actual 120 s rehearsal. Итоговый рейтинг/денежный победитель/прибыль/доля/срок №2 не заявлены.
''')
print(json.dumps({'manifest_sha256':mh,'files':len(files),'bytes':manifest['bytes']},ensure_ascii=False))
