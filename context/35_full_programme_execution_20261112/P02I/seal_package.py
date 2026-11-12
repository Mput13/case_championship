"""Manifest готового P02I: только назначенный каталог, без Git mutations."""
from pathlib import Path
import csv, datetime, hashlib, json
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,value): (ROOT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def count(name):
    with (ROOT/name).open() as f:return len(list(csv.DictReader(f)))
def main():
    v=json.loads((ROOT/'validation.json').read_text())
    if v['status']!='PASS':raise SystemExit('Пакет не запечатывается при FAIL происхождения/границ')
    summary=json.loads((ROOT/'build_summary.json').read_text())
    write('tariff_visual_review.json',{
      'reviewer':'P02I, личное чтение изображений; не независимый pass',
      'TBS':{'source':'evidence/TBS-TARIFF.pdf','source_sha256':sha(ROOT/'evidence/TBS-TARIFF.pdf'),'pages_viewed':[1,2,3,4],'selected_rates_verified':'LTO7.5USD/т; lighting20%; scheduledparking1.5USD/т/ч; fire55USD; departing25USD/transfer6USD; aircraftsecurity2.5EUR/т; passengersecurity6.2EUR; night15% с ограничениемscope','limitations':'Ночная область15%/20%, округление и налоговая применимость требуют договора; rate2026 не будущаяставка.'},
      'TLV':{'source':'evidence/TLV-TARIFF.pdf','source_sha256':sha(ROOT/'evidence/TLV-TARIFF.pdf'),'pages_viewed':[1,2],'selected_rates_verified':'landing24.15USD+16.13USD за ступень; parking25%; bridge345.30/513.40USD; airportATC66.37/176.79USD; departingT3/T1 33.87/15.61USD; incoming6.68USD; baggageT3 6.81/10.90 иT1 4.06/8.15USD','limitations':'Terminal allocation, MTOW и invoice basesUNKNOWN; T1/T3 и peak/offpeak альтернативные, не суммируемые.'},
      'BY_note':{'source':'evidence/RU-BY-APPOINT.pdf','source_sha256':sha(ROOT/'evidence/RU-BY-APPOINT.pdf'),'page_viewed':1,'read_result':'НотаМИДРФ17695/2дснг,20.11.2025. Ульяновск–Минск2/нед; Владикавказ–Минск3/нед; Волгоград–Минск2/нед.','limitations':'Назначение не означает иностранныйpermit/слот/полет; аэропорты не указаны.'}})
    write('handoff.json',{
      'package_id':'P02I','version':'1.0','status':'STAGE_A_RESEARCH_READY_FOR_COORDINATOR','as_of':'2026-11-12','scope':'Международные дополнения к самостоятельному CASE_SJ; самостоятельного финансового/choice движка нет',
      'write_boundary':'context/35_full_programme_execution_20261112/P02I/',
      'counts':summary,'required_deliverables':['international_market_cards.csv','international_access.csv','foreign_cost_inputs.csv','programme_hypotheses.json','cost_support_fx_unknowns.csv','assumptions.csv','manifest.json','handoff.md'],
      'additional_deliverables':['aircraft_profiles.csv','sources.csv','demand_context.csv','city_domain_coverage.csv','unresolved_network_destinations.csv','delivery_branch_contract.json','kernel_handoff_map.csv','input_manifest.json','validation.json','source_issues.json','correction_lineage.json','tariff_visual_review.json'],
      'exact_source_pins_file':'input_manifest.json','exact_source_blob_count':18,
      'row_provenance':{'verified_source_records':v['pinned_rows_verified'],'p02_products':count('inputs/pinned_international_products.csv'),'fields':['source_commit','source_git_path','source_file_sha256','source_csv_record_number','source_csv_line_start','source_csv_line_end','source_row_sha256','product_id если в оригинале']},
      'assumptions':'P02I-A01..P02I-A14; численные диапазоны будущих неизвестных не выдуманы; сценарии не доверительные интервалы',
      'zero_new_tu214':'Обязательный календарь24месяца нулевых новыхготовыхбортов; существующийKEEPсохраняется',
      'priority_experiments':['I01: партнёрскийподвоз и собственныепрямые','I02: Кавказ direct/feed/domestic','I03: KUF–IST direct/feed/domestic'],
      'new_finding':'НотаМИДРФ17695/2дснг20.11.2025: Волгоград–Минск2/нед по российскому назначению; иностранныйдопуск/слоты/продажи UNKNOWN',
      'validation':{'status':v['status'],'checks':v['checks_total'],'failed':v['checks_failed'],'scope':v['validation_scope'],'independent_acceptance':'NOT_RUN'},
      'stage_b_remaining':[
        {'owner':'P03','fields':'24месяца dated KEEP/P; tail/crew/MRO/reserve; реальнаятрасса/payload/запасные; физическиекресла; слоты/обратныйрейс/MCT; ввод/донор'},
        {'owner':'P05','fields':'ПомесячныйOD по двумсторонам/сегментам; общийchoice; ownmigration; прямые/трансфер/блоки; даты/asof/lead/gross/net/baggage; partnerprorate'},
        {'owner':'P04','fields':'Полныйиностранныйоборот; futurecontractrates/currency/tax/FX/paymentdate; лизинг/поддержка/guarantees/advance/default; funding trajectory'},
        {'owner':'P06/P07/P08/P09/P10','fields':'Accepted binding по producer_contract982f13d9; matched единыйпересчётP−KEEP; общийресурс/спрос без двойного счёта'},
        {'owner':'Координатор/независимыйпроверяющий','fields':'Рынок/права/ресурс/экономика/полнота; авторскиеинварианты и implementedconditionalengine не финальнаяприёмка'}],
      'not_claimed':['выбраннаясеть','полныйюридическийдопуск','свободныйпарк','годоваяпрограмма','прибыль/лидерство/окупаемость','достижение№2','сопоставимыеживыетарифныепары','независимаяприёмкаP06'],
      'authorization_actions':{'git_mutations':False,'shared_files_modified':False,'public_site_changed':False,'paid_services_started':False,'messages_to_external_people':False,'restarts':False,'browser_interaction':False,'coordinator_tranche_messages':True},
      'publication':'Только координатор может коммитить/пушить этот пакет; manifest.json — точныйсписокфайлов. Автоматическойпубликациинет.'})
    files=[]
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file() or p.name in ('manifest.json','manifest.sha256') or '__pycache__' in p.parts:continue
        files.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)})
    write('manifest.json',{'package_id':'P02I','version':'1.0','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'root':'context/35_full_programme_execution_20261112/P02I','scope':'Завершённый исследовательский пакет; StageBи независимаяприёмка отдельно','input_manifest_sha256':sha(ROOT/'input_manifest.json'),'validation_sha256':sha(ROOT/'validation.json'),'self_hash_policy':'manifest.json и manifest.sha256 исключены из списка, SHAmanifest хранится отдельно','file_count':len(files),'total_bytes':sum(r['bytes'] for r in files),'files':files})
    (ROOT/'manifest.sha256').write_text(sha(ROOT/'manifest.json')+'  manifest.json\n')
    print(json.dumps({'manifest_sha256':sha(ROOT/'manifest.json'),'files':len(files),'total_bytes':sum(r['bytes'] for r in files),'handoff_sha256':sha(ROOT/'handoff.md')},ensure_ascii=False))
if __name__=='__main__':main()
