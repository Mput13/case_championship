#!/usr/bin/env python3
"""Enrich provenance and verify every saved raw/normalized hash; no network."""
from pathlib import Path
import collections,csv,datetime,gzip,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def main():
 mf=json.loads((ROOT/'dataset_manifest.json').read_text());uses={
 'rosstat_municipal_2025_archive':'Дополнительный демографический срез 01.01.2025 для проверки масштаба городов; до сверки с первичным файлом не использовать как окончательный критерий.',
 'archive_metadata':'Проверка целостности зеркального XLSX и явное установление неофициального загрузчика; не подтверждает первичную подлинность.',
 'tochno_settlements':'Размер расселения и контроль тяготения; раздельные город/муниципалитет/внутригородской район. Геокодирование требует проверки.',
 'tochno_regions_population':'Широкое сравнение региональных размеров и динамики; годы и численность на конец/в среднем не смешивать.',
 'tochno_regions_labor':'Рабочая сила/занятость/безработица как контекст деловых поездок; не наблюдение командировок.',
 'tochno_regions_living_standards':'Платёжеспособность как региональный контекст и диапазон тарифных гипотез; не доход конкретного пассажира.',
 'tochno_regions_tourism':'Масштаб годовых размещений и турпродукта; не уникальные туристы, не месячная сезонность и не авиапоток.',
 'tochno_regions_grp':'Экономический масштаб и деловой контекст; не направленные связи или наблюдённый OD.',
 'tochno_bdmo_municipal_wages':'Муниципальный экономический контекст вместо автоматического переноса региональной зарплаты на город; исключены малые предприятия.',
 'tochno_bdmo_municipal_population':'Муниципальный масштаб за сопоставимый год и проверка объединения с зарплатой; среднегодовое население не население города на 1 января.'}
 coverage=[]
 for e in mf['datasets']:
  did=e['dataset_id']
  if did.startswith('tochno_regions_') and did not in ['tochno_regions_description','tochno_regions_collection_page']:e['geographic_coverage']='Source-defined Russia: 85 regions plus inclusive parent-region aggregates where present; country and 8 federal districts also retained. Inspect object_level/object_name, never sum nested levels.'
  elif did=='tochno_settlements':e['geographic_coverage']='85 source-defined Russian regions, 21 507 nonoverlapping census partitions; source ISO/geocoded keys have detected errors.'
  elif did=='rosstat_municipal_2025_archive':e['geographic_coverage']='85 source-defined regions; 19 716 numeric rows with nested regions/municipalities/settlements.'
  elif did.startswith('tochno_bdmo_municipal_'):e['geographic_coverage']='82 source region IDs; municipal upper/lower levels and occasional regional aggregates retained; uneven yearly coverage, no absent region encoded as zero.'
  e['decision_use']=uses.get(did,'Документирование методики, пропусков, версии и ссылок для воспроизводимого сбора и выбора только нужных показателей.')
  if e.get('record_count') is None:e['value_status']='UNKNOWN'
  e['record_count_unit']='parsed table rows' if e.get('record_count') is not None else 'not applicable / no fact table (documentation or source metadata)'
  if 'tochno_regions_' in did and not did.endswith(('page','description')):e['units']='indicator_unit per observation; ND is NULL with reason in normalized data'
  elif did=='tochno_settlements':e['units']='persons; geographic codes are strings; coordinates degrees (unverified geocoding)'
  elif did=='rosstat_municipal_2025_archive':e['units']='persons; source territory code TЕРСОН-МО preserved as string'
  elif did=='tochno_bdmo_municipal_wages':e['units']='RUB, gross nominal average monthly wages Jan–Dec; large/medium/nonprofit employers'
  elif did=='tochno_bdmo_municipal_population':e['units']='persons, annual average resident population'
  else:e['units']='not applicable (documentation/metadata)'
  e['validation_boundary']='Byte integrity and structural checks only; independent verification of all official cells NOT_RUN.'
  e['published_at']='UNKNOWN' if not e.get('published_at') else e['published_at']
  coverage.append({k:e.get(k,'') for k in ['dataset_id','source_url','geographic_coverage','temporal_coverage','grain','record_count','record_count_unit','acquisition_status','decision_use','limitations']})
 # Every physical raw has a receipt; every gzip also records the hash of its decompressed bytes.
 recorded={e['raw_path'] for e in mf['datasets']};unrecorded=[str(p.relative_to(ROOT)) for p in (ROOT/'raw').iterdir() if p.is_file() and str(p.relative_to(ROOT)) not in recorded]
 if unrecorded:raise ValueError('unrecorded raw: '+str(unrecorded))
 seen=set();arts=[]
 for e in mf.get('normalized_artifacts',[]):
  if e['path'] in seen:continue
  seen.add(e['path']);p=ROOT/e['path']
  if p.suffix=='.gz':
   h=hashlib.sha256();n=0
   with gzip.open(p,'rb') as f:
    for b in iter(lambda:f.read(1024*1024),b''):h.update(b);n+=len(b)
   e.update(uncompressed_sha256=h.hexdigest(),uncompressed_size_bytes=n)
  arts.append(e)
 for p in sorted((ROOT/'normalized').glob('*')):
  if str(p.relative_to(ROOT)) not in seen and p.is_file():arts.append(dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),size_bytes=p.stat().st_size,record_count=None,command='pdftotext -layout raw/<document>.pdf normalized/<document>.txt' if p.suffix=='.txt' else 'generated by normalize_social.py / normalize_bdmo.py',grain='documentation or validation report'))
 mf['collectors']=[dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted((ROOT/'collectors').glob('*.py'))]
 mf['normalized_artifacts']=arts;mf['generated_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 checks=[]
 for e in mf['datasets']:
  p=ROOT/e['raw_path'];checks.append(dict(path=e['raw_path'],sha256_matches=hashlib.sha256(p.read_bytes()).hexdigest()==e['sha256'],size_matches=p.stat().st_size==e['size_bytes']))
 for e in arts:
  p=ROOT/e['path'];checks.append(dict(path=e['path'],sha256_matches=hashlib.sha256(p.read_bytes()).hexdigest()==e['sha256'],size_matches=p.stat().st_size==e['size_bytes']))
 (ROOT/'manifest_validation.json').write_text(json.dumps(dict(checked_at_utc=mf['generated_at_utc'],all_pass=all(x['sha256_matches'] and x['size_matches'] for x in checks),files=checks),ensure_ascii=False,indent=2)+'\n')
 (ROOT/'dataset_manifest.json').write_text(json.dumps(mf,ensure_ascii=False,indent=2)+'\n')
 fields=['dataset_id','source_url','source_organization','raw_path','sha256','size_bytes','retrieved_at_utc','published_at','temporal_coverage','grain','geographic_coverage','key_fields','units','record_count','record_count_unit','acquisition_status','value_status','license','limitations','decision_use','collector_version','command','validation_boundary']
 with (ROOT/'source_registry.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(mf['datasets'])
 with (ROOT/'coverage.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,list(coverage[0]));w.writeheader();w.writerows(coverage)
 print(json.dumps(dict(raw_files=len(mf['datasets']),raw_bytes=sum(e['size_bytes'] for e in mf['datasets']),normalized_files=len(arts),normalized_bytes=sum(e['size_bytes'] for e in arts),hashes_all_pass=all(x['sha256_matches'] and x['size_matches'] for x in checks))))
if __name__=='__main__':main()
