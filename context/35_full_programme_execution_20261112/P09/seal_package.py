"""Создать манифест только P09. Никаких git mutations."""
import hashlib,json,sys,shutil
from pathlib import Path
P=Path(__file__).resolve().parent

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(1024*1024),b''):h.update(x)
 return h.hexdigest()

def main():
    # Только созданные локальным запуском bytecode caches внутри назначенной области.
    for path in P.rglob('__pycache__'):
        if path.is_dir():shutil.rmtree(path)
    if '--verify' in sys.argv:
        m=json.loads((P/'manifest.json').read_text());assert all((P/r['path']).stat().st_size==r['bytes'] and sha(P/r['path'])==r['sha256'] for r in m['files']);print('MANIFEST_PASS',len(m['files']),sha(P/'manifest.json'));return
    validation=json.loads((P/'validation.json').read_text());assert validation['status']=='PASS'
    exclude={'manifest.json','manifest.sha256'}
    rows=[dict(path=str(f.relative_to(P)),bytes=f.stat().st_size,sha256=sha(f)) for f in sorted(P.rglob('*')) if f.is_file() and str(f.relative_to(P)) not in exclude and '__pycache__' not in f.parts]
    manifest=dict(package='P09',version='conditional_comparison_v1_20261112',root='context/35_full_programme_execution_20261112/P09',path_base='root',status='COMPLETED_CONDITIONAL_COMPARISON_PACKAGE',acceptance='INDEPENDENT_ACCEPTANCE_PENDING',source_root_pin='6a6326c2dcfe32e47ec25621bda0d15fcfe48ae1',P06_pin='982f13d9b6c378ed9581125ecc5c40f17dade6a3',file_count=len(rows),bytes=sum(r['bytes'] for r in rows),files=rows,scope='Только собственная область P09; источник/сценарий/расчёт != market/dispatch/fullfinance acceptance',excluded=['manifest.json','manifest.sha256','generated __pycache__'],validation_checks=len(validation['checks']),full_canonical_main=18,full_canonical_existing_ssj=2,git_mutations=False)
    (P/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');digest=sha(P/'manifest.json');(P/'manifest.sha256').write_text(digest+'  manifest.json\n');print(json.dumps(dict(sha256=digest,files=len(rows),bytes=manifest['bytes'],validation_checks=len(validation['checks'])),ensure_ascii=False))
if __name__=='__main__':main()
