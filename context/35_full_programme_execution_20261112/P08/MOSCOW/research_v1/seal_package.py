#!/usr/bin/env python3
"""Hash payload; envelope metadata deliberately avoids self-referential hashes."""
from pathlib import Path
import csv, datetime, hashlib, json

R=Path(__file__).resolve().parent
def load(p):return json.loads((R/p).read_text())
def digest(b):return hashlib.sha256(b).hexdigest()
def save(p,o):(R/p).write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':
 v=load('verification.json')
 assert v['status']=='PASS','Не запечатывать проваленную проверку.'
 excluded={'manifest.json','handoff.json'}
 files=[]
 for p in sorted(R.rglob('*')):
  if not p.is_file() or p.name in excluded or '__pycache__' in p.parts or p.name.startswith('.'):continue
  relative=str(p.relative_to(R))
  files.append(dict(path=relative,sha256=digest(p.read_bytes()),bytes=p.stat().st_size,role='pinned_input_extract' if relative.startswith('inputs/') else ('public_source_text' if relative.startswith('sources/') else 'research_payload_or_reproducer')))
 root='context/35_full_programme_execution_20261112/P08/MOSCOW/research_v1/'
 save('manifest.json',dict(package='P08-MOW-A',version='research_v1',scope_root=root,status='STAGE_A_COMPLETE; STAGE_B_DEPENDENCIES_OPEN',files=files,payload_bytes=sum(f['bytes'] for f in files),payload_file_count=len(files),metadata_envelope_excluded_from_payload_hashes=sorted(excluded),commit_instruction='Добавить только перечисленный payload и два metadata envelope файла в этом каталоге. Git mutations выполняет координатор.',frozen_inputs=load('input_manifest.json')['pins'],raw_source_policy='Полные чужие fixture/архивы не копировались. Только выбранные строки с source logical rows/hashes; новые dated templates созданы здесь.'))
 p=load('programme_candidates.json');recipes=load('recipes.json')
 save('handoff.json',dict(package='P08-MOW-A',version='research_v1',status='STAGE_A_RESEARCH_COMPLETE',completed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),write_scope=root,manifest_path=root+'manifest.json',manifest_sha256=digest((R/'manifest.json').read_bytes()),input_manifest_sha256=digest((R/'input_manifest.json').read_bytes()),programme_candidates_sha256=digest((R/'programme_candidates.json').read_bytes()),handoff_document=root+'handoff.md',sourcepins=load('input_manifest.json')['pins'],counts=dict(recipes=len(recipes),programmes=len(p['programmes']),author_MOW_geographies=sum(r['legacy_id'].startswith('Прямые') for r in recipes),named_archival_branches=['C08','C19','C25-GOJ','C25-KUF'],physical_base_control='DME-CONTROL',dated_physical_leg_templates=len(load('dated_templates/flights.json')),source_records=len(load('sources_registry.json')),assumptions=len(load('assumptions.json'))),verification=dict(status=v['status'],checks_passed=v['checks_passed'],checks_total=v['checks_total'],scope=v['scope'],independent_acceptance=v['independent_acceptance']),findings=[
 'MOW не аэропорт. ZIA/DME имеют разное историческое/текущее доказательство; VKO/SVO не свободные SSJ базы.',
 'C19 T иO имеют Fri→Mon только изVOG; C ZIA–VOG–MCX–VOG–ZIA даёт такой RT обоим origin в выбранном календаре.',
 'Историческая продажаRW MCX–VOG2025 означает необходимость сохранять/пересчитывать существующий собственный бизнес вKEEP.',
 'C25 имеет опубликованного N4 конкурента и несовпадающие дни направлений. T/O дают10/11ночей; фактическая трассаKGD/парк/спрос UNKNOWN.',
 'C08 исторический A4 черезIAR не current nonstop; архивный reverse clock противоречив. Конкретный C out-and-back превышает u10, T/O в reference точке нет; это не экономический отказ.',
 'Одна неделя не умножалась на52 для денежных/пассажирских выводов; полный24month календарь перечислен по датам.'
 ],strong_source_tranche_paths=['airport_status.csv','KEEP_evidence.csv','sources_registry.json','source_issues.csv','ground_products.csv','dated_templates/trip_windows.csv'],stage_B=dict(status='OPEN_NOT_RUN',requests_file=root+'dependency_requests.csv',request_ids=[f'MOW-D{i:02}' for i in range(1,11)],owners=['P03 actual resource/crew/MRO/dispatch/futureKEEP','P05 common monthly demand/choice/RT prices/ground/own diversion','P04 full cost/thresholds/recognised support/event cash/liquidity','P06 accepted P/KEEP bundles, independent acceptance pending','P09 joint mixed-programme comparison with no resource/OD double counting']),economic_outputs='NOT_RUN; null, не0',operational_acceptance='UNKNOWN; templates не physical_inventory admission',safety_scope=dict(git_mutations=False,shared_files_written=False,children_started=False,browser_used=False,paid_services=False,external_messages='только явно разрешённые сообщения координатору',restarts=False,public_site=False),limitations=['нет прогноза RW N(t); H2 boundary не service entry','future SJ100_PD8 отдельный отSSJ100_SaM146; нет переноса расходов как факта','14 tail-days/week — выбранный одинаковый экспериментальный модуль1+1, не свободный парк или рекомендация по размеру','57 альтернатив не суммировать,8–12pairs относится к итоговой сети конца2028','source coverage PARTIAL; отсутствие предложения не нулевой рынок'],envelope_hash_rule='manifest.json/handoff.json исключены из собственного payload; handoff содержит hash manifest; координатор может закрепить оба Git blob IDs своим commit.'))
 print(json.dumps(dict(manifest_sha256=digest((R/'manifest.json').read_bytes()),handoff_sha256=digest((R/'handoff.json').read_bytes()),payload_files=len(files),payload_bytes=sum(f['bytes'] for f in files)),ensure_ascii=False))
