from pathlib import Path
import subprocess, hashlib, json, datetime
ROOT=Path(__file__).resolve().parents[1]
SHA='71b493d0051dc3acf2a7619801e5b0eb022bddd3'
FILES=['src/longlist_data.py','src/longlist_score.py','src/build_longlist.py','src/kover_days.py','src/fetch_telegram.py','src/scan_news.py','src/update.py','src/fetch_static.py','data/sources.toml','data/processed/destinations.csv','data/processed/longlist.csv','data/processed/longlist_computed.csv','data/processed/longlist_scores.csv','data/processed/longlist_scores_min500.csv','data/processed/kover_days.csv','data/manual/longlist_manual.csv','data/assumptions/longlist_weights.csv','data/raw/_manifest.json','data/raw/favt_posts.csv','docs/HANDOFF.md','docs/16_scenarios_closures_reopening.md','docs/22_data_sources_longlist.md']
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
entries=[]
for name in FILES:
    b=subprocess.check_output(['git','show',SHA+':'+name])
    p=ROOT/'raw/front'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    entries.append({'source_sha':SHA,'source_path':name,'local_path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'retrieved_at_utc':now,'acquisition_status':'ACQUIRED_RAW','limitations':'git snapshot from colleague; not independent verification of originating observation'})
(ROOT/'input_manifest.json').write_text(json.dumps({'inputs':entries,'other_input_sha':'5e896e8ea5bb97136c71c49562a345b8f210bf11','snapshot_at_utc':now},ensure_ascii=False,indent=2))
(ROOT/'progress.md').write_text('# Аудит front\n\nВходы извлечены из SHA '+SHA+'. Просмотрены алгоритмы до исполнения. Свежий код по-прежнему обращает неизвестное rail_hr в статус gap, а список конкурентных хабов замкнут на KJA/IKT/VVO. Проверка масштаба и чувствительности продолжается. scan_news уже содержит авиационный фильтр: старое замечание о его отсутствии не повторяется.\n')
print(len(entries),'files',sum(x['bytes'] for x in entries),'bytes')
