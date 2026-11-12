"""Структурная проверка, границы доказательств и manifest только локального REN-пакета."""
from pathlib import Path
import csv,json,hashlib,subprocess,datetime as dt,math
R=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(n):return json.loads((R/n).read_text())
def csvrows(n):return list(csv.DictReader((R/n).open()))
def dump(n,x):(R/n).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
required=['case.json','evidence.csv','market_deltas.csv','hypotheses.json','programme_candidates.json',
          'comparison_requests.csv','assumptions.csv','readiness.json','README.md','producer_fragment.json',
          'resource_checks.json','rotation_templates.csv','matched_comparison_checks.json','sources.csv']
checks=[]
def check(name,condition,detail):
    checks.append({'check':name,'status':'PASS' if condition else 'FAIL','detail':detail})
check('required_artifacts',all((R/x).is_file() and (R/x).stat().st_size>10 for x in required),required)
json_count=0
for f in R.rglob('*.json'):
    if f.name in ['output_manifest.json','validation.json','handoff.json']:continue
    json.loads(f.read_text(),parse_constant=lambda s:(_ for _ in ()).throw(ValueError('Nonfinite '+s)))
    json_count+=1
check('valid_JSON_no_nonfinite',True,{'json_files':json_count})
need={'unit','period','coverage','status','source_id'}
for n in ['evidence.csv','market_deltas.csv','comparison_requests.csv','assumptions.csv','competitor_offer_rows.csv',
          'resource_diagnostics.csv','rotation_templates.csv','connection_diagnostics.csv','fare_observations.csv',
          'monthly_activation_rules.csv','market_coverage_update.csv','source_issues.csv','sources.csv']:
    rs=csvrows(n);check('table_contract:'+n,bool(rs) and need.issubset(rs[0]),{'rows':len(rs),'required_columns':sorted(need)})
sources={x['source_id']:x for x in csvrows('sources.csv')}
check('source_files_sha256',all((R/s['local_file']).is_file() and sha(R/s['local_file'])==s['sha256_raw'] for s in sources.values()),
      {'sources':len(sources),'scope':'saved raw public response, not freshness or operational admission'})
check('evidence_source_foreign_keys',all(x['source_id'] in sources for x in csvrows('evidence.csv')),'All evidence facts link to a source registry row')
pin_checks=[]
for manifest in ['input_pins.json','additional_input_pins.json']:
    for x in load(manifest)['files']:
        b=subprocess.check_output(['git','show',x['commit']+':'+x['path']])
        pin_checks.append(hashlib.sha256(b).hexdigest()==x['file_sha256'])
check('exact_git_input_hashes',all(pin_checks),{'files':len(pin_checks),'reads':'git show, no branch checkout/fetch or mutations'})
row_count=0
for f in R.glob('*.subset.json'):
    x=json.loads(f.read_text())
    for r in x.get('rows',[]):
        row_count+=1
        h=hashlib.sha256(json.dumps(r['row'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        assert h==r['source_row_sha256_canonical_json'],f
check('preserved_source_row_hashes',True,{'rows':row_count,'hash_rule':'sorted compact UTF8 JSON of string-valued DictReader row'})
hyps=load('hypotheses.json')['hypotheses'];programmes=load('programme_candidates.json')['programmes']
check('hypothesis_dispositions',all(x.get('outcome') and x.get('reconsideration_condition') and x.get('source') and x.get('distinguishing_test') and x.get('ancestorIDs') for x in hyps),{'hypotheses':len(hyps)})
check('no_unconditional_money_or_share',all(x['monetary_result'] is None and x['market_share_result'] is None for x in programmes),'P05 and complete admitted P/KEEP unavailable')
check('no_MOW_in_flights',all(x['origin_airport']!='MOW' and x['destination_airport']!='MOW' for x in csvrows('rotation_templates.csv')),'Airport-level physical prototype flights')
check('no_overlap_only',all(x['continuity_and_no_overlap']=='PASS' for x in load('resource_checks.json')['checks']),
      {'tail_weeks':len(load('resource_checks.json')['checks']),'not_checked':'crew/MRO/slots/reserve/readiness'})
check('same_local_products_R1_E1',all(x['local_legs_same_clocks_R1_E1']=='PASS' for x in load('matched_comparison_checks.json')['checks']),'Same local clocks, weekdays and diagnostic nominal seats; base/crew/prices unknown')
con=csvrows('connection_diagnostics.csv')
check('H1_and_unsynchronised_counterexample',all(float(x['connection_minutes'])==90 for x in con if x['programme_id']=='CP-REN-H1') and any(float(x['connection_minutes'])<0 for x in con if x['programme_id']=='CP-REN-H1-U'),
      'Same physical flight count and nominal seats; H1-U shifted T2+180min loses some same-day links')
months=csvrows('monthly_activation_rules.csv')
check('24_month_rules_not_annualised_week',len(months)==24 and len({x['month'] for x in months})==24,'Rules include D0/partial/delay/phased; not actual accepted N(t) or annual flight inventory')
check('incomplete_fragment_not_evaluated',load('producer_fragment.json')['status']=='INCOMPLETE_NOT_ENGINE_INPUT' and load('resource_checks.json')['P06_run']=='NOT_RUN','No toy/dummy P05 calibration or financial zero bundle')
check('visual_PDF_evidence',load('pdf_visual_qa.json')['status']=='PERSONALLY_VIEWED','Local tariffp1/2, fuelp1 and discountp3 personally viewed; other pages not claimed visually accepted')
failed=[x for x in checks if x['status']=='FAIL']
assert not failed,failed
validation={'status':'PASS_STRUCTURAL_AND_DIAGNOSTIC_ONLY','as_of':'2026-11-12','checks':checks,
    'counts':{'programmes':len(programmes),'hypotheses':len(hyps),'evidence_facts':len(csvrows('evidence.csv')),
              'offer_rows':len(csvrows('competitor_offer_rows.csv')),'prototype_flights':len(csvrows('rotation_templates.csv')),
              'comparison_requests':len(csvrows('comparison_requests.csv')),'assumptions':len(csvrows('assumptions.csv'))},
    'acceptance_limit':'No current free RW aircraft, executable future schedule, SJ100 dispatch approval, calibrated demand, profitability, funding or market-share claim.',
    'external_effects':'No Git mutations, installs, paid services, bookings, public deployment or external correspondence; only authorized coordinator updates.'}
dump('validation.json',validation)

handoff={
 'package_id':'REN-research-v1-20261112','stage_a':'COMPLETE','stage_b':'PENDING_COMMON_INPUTS_AND_ADMISSION',
 'write_root':str(R),'language':'ru','as_of':'2026-11-12','read_first':'README.md',
 'manifest':'output_manifest.json','manifest_hash_rule':'SHA256 for every retained file except output_manifest.json itself; handoff has no circular hash of manifest',
 'counts':validation['counts'],
 'source_pins':load('additional_input_pins.json')['pins'],
 'conclusion':'REN сохраняется в сравнении. Сначала R1/E1/D1 на одинаковом G1, затем H1/H1-U и лучший direct на G2; экономический победитель не назначен.',
 'current_role':'Опубликованное присутствие RW/outstation и origin-market; собственные летние EVN и partner MSQ. База/хаб/свободный ресурс RW в REN UNKNOWN.',
 'new_useful_evidence':[
    'Локальный fuel reference141405руб/т безНДС с01.11.2026, подписан30.10; общие handling references получены для P04. Они не будущие оплаченные RW ставки.',
    '64% transit discount для45–50т закончился31.10.2026. Не финансировать будущий хаб этой скидкой; MRV50% лишь до31.12.2026 и доступ RW неизвестен.',
    'Bus101 от вокзала120руб, первая подача10:00. Текущий RW09:50 в среду требует иного наземного доступа. В опытеR1/E1 местные часы строго совпадают: outboundREN11:30.',
    'Есть собственная летняя линияREN-EVN1/нед; её нельзя обнулить вKEEP. Есть заявленный единый билетREN-SVX-MSQ.',
    '109 официальных outbound/inbound schedule rows сsource row IDs/hash; ранее P02 имел лишь3частично описанных исходящих рынкаREN из28. Новые строки тоже не admission физических кресел.',
    'Непрерывность/no-overlap на458 diagnostic flights проверена; H1 90мин связи имеют контрольH1-U на тех же рейсах. Crew/TO/MCT/слоты/reserve иSJ100непроверены.'
 ],
 'comparison_priority':[
    {'id':'REN-G1','programmes':['CP-REN-R1','CP-REN-E1','CP-REN-D1'],'required':'Общий tail/calendar/initial location, futureKEEP, P05 sharedOD/choice, P04 differential base/extra-leg/alternative-use costs; не19часов=прибыль.'},
    {'id':'REN-G2','programmes':['CP-REN-H1','CP-REN-H1-U'],'required':'Сначала effect bank on same flights; затем лучший прямой портфель на тех же2line хвостах. OMSovernight и длинные служебные дни учитываются.'},
    {'id':'REN-extension','programmes':['CP-REN-R2','CP-REN-00','CP-REN-X1'],'required':'Совместный ресурс/свои продажи и сценарии поставок; туристические блоки только по договору, international с0новыхТу214.'}
 ],
 'shared_inputs_needed':{'P02':'dated seasons, through/physical legs, quote baskets and response resource',
    'P03':'real common resource/initial positioning, futureKEEP/donors, supply/service_entry, crew/TO/reserve, SJ100 separate, slots/MCT/airport contracts',
    'P04':'accept local reference applicability and future rate ranges/thresholds; full base/launch/exit/contract cash and no cost double counts',
    'P05':'one monthly finalOD/choice/cannibalization model; no independent local capture/money model',
    'P07/P08/P09':'joint P/KEEP recompute and global8–12unique pairs; exact manifests; no sum of separate author outcomes'},
 'blockers_are_not_rejections':'H-REN-01..08 условны по названным неизвестным; H-REN-ROLE оценена по текущим источникам. Один шаблон/500км/старыйscore не экономический отказ городу.',
 'personal_checks':{'validation':'validation.json','resource':'resource_checks.json','matched':'matched_comparison_checks.json','pdf':'pdf_visual_qa.json'},
 'not_run':['P06 evaluate/compare for real RW','P05 calibration','annual/monthly financial outcome','actual crew/TO/reserve feasibility','live quote/booking inventory','newSJ100_PD8 dispatch','independent acceptance of commonP06'],
 'operations_boundary':'All shared inputs read via git show exactSHA; no shell Git mutations or edits outside assigned root. No child agents.',
 'commit_instruction':'Координатор может коммитить завершённый Stage A по output_manifest.json. Не менять frozen авторские исходы, другие ветки/файлы, публичный Site или дашборд Анастасии.'
}
dump('handoff.json',handoff)
files=[]
for p in sorted(R.rglob('*')):
    if not p.is_file() or p.name=='output_manifest.json' or '__pycache__' in p.parts:continue
    files.append({'path':str(p.relative_to(R)),'sha256':sha(p),'bytes':p.stat().st_size})
dump('output_manifest.json',{'package_id':handoff['package_id'],'root':str(R),'as_of':'2026-11-12',
    'status':'SEALED_STAGE_A_CONDITIONAL_RESEARCH','files':files,'excluded':['output_manifest.json self hash','__pycache__'],
    'source_provenance':'input_pins.json;additional_input_pins.json;sources.csv;sources/fetch_receipts.json;*.subset.json',
    'scope':'Only assigned REN directory. Shared changes outside are not ours and not included.',
    'validation_status':validation['status']})
manifest=load('output_manifest.json')
assert all(sha(R/x['path'])==x['sha256'] for x in manifest['files'])
print(json.dumps({'status':validation['status'],'checks':len(checks),'files':len(files),
                  'package_bytes':sum(x['bytes'] for x in files),'manifest_sha256':sha(R/'output_manifest.json'),
                  'handoff_sha256':sha(R/'handoff.json'),'counts':validation['counts']},ensure_ascii=False))
