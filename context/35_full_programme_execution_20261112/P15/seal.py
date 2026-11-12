#!/usr/bin/env python3
"""Seal the owned final conditional UI package. No Git writes."""
import hashlib,json,pathlib
P=pathlib.Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def read(n):return json.loads((P/n).read_text())
def dump(n,o):(P/n).write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
v=read('qa/verification.json');r=read('qa/rehearsal.json');live=read('qa/live_full_results.json');visual=read('qa/visual_review.json');index=read('accepted/index.json')
assert v['status']=='PASS_EXACT_TRANSPORT_AND_OFFLINE_DELIVERY' and r['status']=='PASS' and r['elapsed_ms']>=120000
assert live['full_test']['status']=='PASS' and live['window_test']['status']=='PASS'
assert index['coordinator_acceptance']=='ACCEPTED_FOR_UI' and index['independent_acceptance']=='APPROVE_WITH_EXPLICIT_LIMITS'
htmlbytes=(P/'dashboard_candidate.html').read_bytes();htmlsha=sha(htmlbytes)
assert htmlsha==v['replay_sha256']['dashboard_candidate.html']
theme_patch=read('qa/root_contrast_patch.json') if (P/'qa/root_contrast_patch.json').exists() else None
if theme_patch:
    # Preserve the exact historical rehearsal; verify the single CSS insertion
    # by reversing it in memory, without relabelling that run as a new run.
    before=b':root{--paper:var(--secondary,#F3F1EC);'
    after=b':root{color-scheme:light dark;--paper:var(--secondary,#F3F1EC);'
    assert htmlbytes.count(after)==1
    assert sha(htmlbytes.replace(after,before,1))==theme_patch['before_html_sha256']==r['dashboard_sha256']==visual['dashboard_sha256']
    assert htmlsha==theme_patch['after_html_sha256'] and theme_patch['status']=='PASS_CSS_ONLY_HOST_CONTRAST'
    css=(P/'source/app.css').read_bytes()
    assert sha(css.replace(after,before,1))==theme_patch['before_css_sha256']
else:
    assert htmlsha==r['dashboard_sha256']==visual['dashboard_sha256']
files=[]
for f in sorted(P.rglob('*')):
    if not f.is_file():continue
    rel=f.relative_to(P)
    if '__pycache__' in rel.parts or str(rel) in ['output_manifest.json','handoff.json','handoff.md'] or (rel.parts[0]=='qa' and f.suffix=='.html'):continue
    b=f.read_bytes();files.append({'path':rel.as_posix(),'sha256':sha(b),'bytes':len(b)})
manifest={'package':'P15','version':'P15-final-conditional-ui-v2-author6cbe'+('-root-theme1' if theme_patch else ''),'status':'FINAL_CONDITIONAL_RESEARCH_UI_READY','write_scope':'context/35_full_programme_execution_20261112/P15/','author_view_commit':'6cbe817320f75db9823984e7c4eeb6091fd7d996','producer_commit':index['producer_commit'],'producer_manifest_sha256':index['producer_manifest_sha256'],'coordinator_acceptance':'ACCEPTED_FOR_UI_CONDITIONAL_RESEARCH','independent_programme_acceptance':'APPROVE_WITH_EXPLICIT_LIMITS','files':files,'file_count':len(files),'bytes':sum(f['bytes'] for f in files),'hash_algorithm':'SHA256 file bytes','metadata_envelope_excluded':['output_manifest.json','handoff.json','handoff.md'],'temporary_runtime_excluded':['qa/*.html','__pycache__/'],'Git_mutations':0,'children':0,'independent_P16_acceptance':'NOT_RUN','root_css_patch':theme_patch}
dump('output_manifest.json',manifest);mh=sha((P/'output_manifest.json').read_bytes())
handoff={'package':'P15','version':manifest['version'],'status':manifest['status'],'manifest_sha256':mh,'files':len(files),'bytes':manifest['bytes'],'entry':'dashboard_candidate.html','dashboard_sha256':htmlsha,'data':'dashboard_data.json','data_sha256':sha((P/'dashboard_data.json').read_bytes()),'claim_links':'claim_links.csv','adapter':['dataadapter.py','bind_final.py','source/adapter.js','source/final.js'],'replay':'replay.py','contract':'ui_contract.json','accepted_index':'accepted/index.json','producer_commit':index['producer_commit'],'producer_manifest_sha256':index['producer_manifest_sha256'],'root_authorisation_commit':index['root_authorisation_commit'],'independent_P13_manifest_sha256':index['independent_review']['manifest_sha256'],'expert_manifest_sha256':'3c09a05cc35215e060173370463fc525f98f6804488c008e75a122fe9c8ba1b6','author_view_commit':manifest['author_view_commit'],'original_author_baseline':'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6','P12_history_commit':'06207b1650bd1c83e0f0761b25d063f2c395ace7','coverage':read('integration_coverage.json'),'checks':{'exact_sources_transport_offline':v['count'],'producer_verified_same_path_leaves':v['canonical_verified_same_path_leaves_from_receipts'],'canonical_native':{'programmes':9,'scenarios_each':2,'checks_per_programme':17,'width':1440,'files':'qa/canonical_*.json'},'full_native_UI':len(live['full_test']['checks']),'window_transitions':len(live['window_test']['checks']),'narrow_native_html_states':{'navigation':14,'overview':10,'windows':29},'narrow_real_click_select_Escape_focus':'qa/native_keyboard_narrow.json','visual_widths':[1440,390,1280],'actual_120s_route_ms':r['elapsed_ms'],'actual_120s_log':'qa/rehearsal.json','speech_plan':'defence_5min.md;5min+3minquestions,120sUIinside5min','independent_P16':'NOT_RUN'},'not_claimed':['SCENARIO_NOT_IDENTIFIED resolved','fullprofit/funding/reportedshare/number2','market/contract/crew/ТО/slots/dispatch readiness','unique final winner','physical projector or spoken5min acceptance'],'remaining_substantive_unknowns':['Full operating/cash budget, own migration and binding financing','Actual RW aircraft/crew/ТО/station staff+parts/recovery/slots/time comfort/events','P10 reported metric bridge/F07; no integrated market share or number2 date'],'ui_completion':'COMPLETE for authorised conditional research scope; no outstanding producer/root input needed','boundaries':{'children':0,'Git_mutations':0,'outside_P15_writes':0,'server_started':False,'author_branch_change':False,'public_Site':False,'new_paid_services':False,'external_messages':False,'bookings_payments_PNR':False,'restarts':False}}
if theme_patch:
    handoff['root_css_patch']=theme_patch
    handoff['checks']['actual_120s_rehearsal_html_sha256']=r['dashboard_sha256']
    handoff['checks']['actual_120s_rehearsal_scope']='Historical pre-patch UI; exact inverse-hash proof limits the later change to CSS color-scheme only. Fresh light/dark/narrow previews and offline transport checks passed.'
dump('handoff.json',handoff)
(P/'handoff.md').write_text(f'''# P15: итоговая условная исследовательская сборка

Готов `dashboard_candidate.html`: актуальный авторский v2 вид kiruha355 exact6cbe8173, четыре вкладки, окна подробностей, карта и полные canonical результаты9программ×2сценария. DefaultVOG_RADIAL — условный пример frontier;MRV/AER иSVXконтроль сохранены. Финансовые селекторы содержат реальные данные.

ManifestSHA256:`{mh}`. Payload:{len(files)}файлов/{manifest['bytes']}байт. HTMLSHA256:`{htmlsha}`. Manifest/handoff исключены из собственногоpayload для отсутствия циклического хеша.

Числа из P09 exact736859fdd08448c2564b7b9269b751abe00b5cbc/manifest7b20a1a247ee4b3cf96d94648bb36d61482cb0a58eb7a296ada49a78c818d1fa. Собственный accepted/index.json содержит rootb16c28c6 разрешениеусловного показа иP13 APPROVE_WITH_EXPLICIT_LIMITS. Исходные pending P09 не менялись. Losslessgzip/base64 — только транспорт; каждое JSONleaf сохранено, fullcanonicalgzip/receipt/inputpins/audit/replay доступны. Отдельный обзор1958сценариев/178конструкций имеет свойmode/sourcehash и не заменяетcanonical.

VOGcautiousH263891478.0220616 — дельта известных компонентов кKEEP, неprofit. Абсолютный известный подытогVOG отрицателен в обоихсценариях. Полная дельта показана как функция неизвестных расходов/доходов. Fullprofit/funding/reportedshare/№2 null/UNKNOWN сохранены; спрос SCENARIO_NOT_IDENTIFIED. Парк/crew/ТО/slots остаются условными. Геометрия и календарь неoperationalPASS.

Сохранены все20городов,160кандидатов,169гипотез,663evidence rows,2274P02продукта,6SVX+57Moscow,87international,128capacity-onlyP10,4P11политики иP01monthly. {v['claim_links']}claimlinks. Исходные datasets названы конкретно вметоде. ЭкспертI01–I05 подключён с частичнымcoverage; пятьmaterialunknown не объявленыпройденнымиchecks.

Проверено:{v['count']}source/transport/replayassertions;2509322same-pathleaves поreceipts; native18canonicalcontexts по17checksнапрограмму;117полныхUIchecks;29windowchecks;390pxnavigation14+overview10+windows29. Реальные nativeclick/select/Escape на390×844 иfocusreturn PASS. Исправлена гонкаасинхронногоcloseокна; повторный actual120s прошёл за{r['elapsed_ms']:.2f}ms в том же полномUI. PNG:qa/desktop.png, narrow.png, projector-network.png, network.png, resource-narrow.png, calendar-narrow.png, strategy.png, direct-narrow.png, source-narrow.png. Это собственная визуальная проверка; P16 независимо NOT_RUN,1280 —layout, не физическийпроектор.

Повтор:python3 context/35_full_programme_execution_20261112/P15/replay.py → verify.py. Генерация временныхполныхQAкопий:prepare_qa.py. Речь5минут+3минутывопросов, внутри120sUI:defence_5min.md. Нового ожиданияRW/root/исследований нет; остаточные substantiveunknown показаны как ограничения законченного условного результата.

Запись толькоP15; Gitwrites/children/server/publication/authorbranch/booking/payments/restarts0. Nativepreview_snapshot resource одинраз завершилсяtimeout15000ms: сохранён точныйerror, последующиеact/evaluate иnativehtml_preview работают, PNGполучены штатнымhtml_preview. Host/чужие вкладки/процессы не менялись. Коммититкоординатор поmanifest.
''')
# Verify sealed bytes before handing off.
assert all(sha((P/r['path']).read_bytes())==r['sha256'] for r in files)
print(json.dumps({'status':manifest['status'],'manifest_sha256':mh,'files':len(files),'bytes':manifest['bytes'],'dashboard_sha256':htmlsha},ensure_ascii=False))
