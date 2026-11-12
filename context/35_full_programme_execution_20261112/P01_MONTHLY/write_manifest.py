#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,csv,datetime
P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
data_files=['airport_monthly.csv','carrier_monthly.csv','airport_pair_segment_observations.csv','endpoint_od_observations.csv','airport_aggregate_observations.csv','carrier_aggregate_observations.csv','national_aviation_observations.csv','granularity_crosswalk.csv','calibration_eligibility.csv','assumptions.csv','airport_monthly_coverage.csv','coverage_gaps.csv','sources.csv','reconciliation.csv']
artifacts={f:{'sha256':sha(P/f),'rows':len(list(csv.DictReader((P/f).open())))} for f in data_files}
handoff={'package':'P01-MONTHLY','as_of':'2026-11-12','status':'STAGE_A_RESEARCH_PACKAGE_COMPLETE_WITH_EXPLICIT_COVERAGE_GAPS','output_directory':str(P),'source_pins':json.loads((P/'input_manifest.json').read_text()),'artifacts':artifacts,'summary':json.loads((P/'monthly_summary.json').read_text()),'validation':{'export_integrity':json.loads((P/'validation.json').read_text())['export_integrity'],'independent_acceptance':'NOT_RUN','endpoint_od_admission':'NOT_CONFIRMED','P05_P06_integration':'NOT_RUN','economic_verdict':'NOT_EVALUATED'},'stage_b_requests':['Определение airport total/ВВЛ/МВЛ и версии KJA','Направленность сегментов и аэропорты MOW; конфликт формулировок PEE','Месячные формы остальных аэропортов и недостающих периодов; 407 клеток без total','Подтверждение однородности самолётной совокупности ЮТэйр и недостающих месяцев','Правила fit/holdout для вложенных периодов и частей перевозчиков','Проверка переноса авиационной сезонности на конкретные пары RW; коэффициенты UNKNOWN','Реальные конечные OD/продажи, физическое предложение и совместимое будущее KEEP'],'publication':{'git_mutations':False,'external_messages':False,'paid_services':False,'public_site_changes':False,'common_files_changed':False},'readme':'handoff.md','manifest':'manifest.json'}
(P/'handoff.json').write_text(json.dumps(handoff,ensure_ascii=False,indent=2)+'\n')
files=[]
for f in sorted(P.rglob('*')):
 if not f.is_file() or f.name in ['manifest.json','manifest.sha256'] or '__pycache__' in f.parts:continue
 files.append({'path':str(f.relative_to(P)),'bytes':f.stat().st_size,'sha256':sha(f)})
m={'package':'P01-MONTHLY','generated_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'write_boundary':str(P),'files':files,'file_count':len(files),'bytes_total':sum(x['bytes'] for x in files),'source_pins_file':'input_manifest.json','handoff':'handoff.md','no_git_mutations':True}
(P/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n');digest=sha(P/'manifest.json');(P/'manifest.sha256').write_text(digest+'  manifest.json\n');print(json.dumps({'files':len(files),'bytes':m['bytes_total'],'manifest_sha256':digest,'data_artifacts':artifacts},ensure_ascii=False))
