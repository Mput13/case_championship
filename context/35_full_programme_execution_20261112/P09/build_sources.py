"""Выборка P02 и локальных источников по исследованным парам, с row hashes."""
from pathlib import Path
import csv,hashlib,io,json,subprocess
import programme_builder as b

def main():
    ps=json.loads((b.ROOT/'programmes.json').read_text())['programmes']
    pairs={tuple(sorted((s['base'],d))) for p in ps for s in p['working_slots'] for d in s['spokes']}
    for d in b.KEEP_DEST:pairs.add(tuple(sorted(['SVX',d])))
    registry=[];selection=[]
    rev='d9486f113f074c185a94bcc5c0afeef12ea3574f';prefix='context/35_full_programme_execution_20261112/P02/'
    out=b.ROOT/'competition';out.mkdir(exist_ok=True)
    for name in ['market_coverage.csv','competitor_products.csv','fare_panel.csv']:
        raw=subprocess.check_output(['git','show',rev+':'+prefix+name],cwd=b.ROOT)
        rows=list(csv.DictReader(io.StringIO(raw.decode())));selected=[]
        for i,r in enumerate(rows):
            if 'origin'in r:a,z=r['origin'],r['destination']
            else:
                v=r['market_id'].split(':');a,z=v[-2:]
            if tuple(sorted([a,z])) not in pairs:continue
            h=b.digest(r);selected.append(dict(source_data_row=i+1,source_row_sha256=h,source_file_sha256=hashlib.sha256(raw).hexdigest(),source_commit=rev,**r))
            selection.append(dict(source_id=r.get('product_id',r['market_id']),source_path=prefix+name,source_row_id=r.get('product_id',r['market_id']),source_data_row=i+1,source_row_sha256=h,source_file_sha256=hashlib.sha256(raw).hexdigest(),commit=rev,selection='Выбранная airportpair входит в исследуемый календарь'))
        b.csvwrite(out/name,selected)
        if name=='competitor_products.csv':
            for r in selected:
                registry.append(dict(source_id=r['product_id'],url=r['source_url'],organization=r['carrier']+' / опубликованный source label; legal operator UNKNOWN',publication_date=r.get('retrieved_at','UNKNOWN'),as_of=r['as_of'],period=r.get('period') or r['departure_date'],unit=r.get('unit','предложение'),granularity=r['row_grain'],status=r['status'],coverage=r['coverage'],source_row_id=r['product_id'],source_row_sha256=r['source_row_sha256'],source_path='competition/competitor_products.csv',use='Контекст конкуренции; не физические кресла2027–2028'))
    for r in b.COSTROWS:
        registry.append(dict(source_id=r['cost_id'],url=r['source_url'],organization=r['geography_or_airport']+' airport/service source; historical model where HIST',publication_date=r['effective_from'],as_of=r['as_of'],period=r['period'],unit=r['unit'],granularity='названная услуга/драйвер',status=r['status'],coverage=r['coverage'],source_row_id=r['cost_id'],source_row_sha256=b.digest(r),source_path='subject/P04/cost_ranges.csv',use='Ставка/аналитический аналог/неизвестный driver, по status'))
    for c in b.LOCAL_CORRECTIONS:
        r=c['raw'];registry.append(dict(source_id=r.get('source_id'),url=c['source_url'],organization=c['city']+' аэропорт; издатель указан в первичном документе',publication_date=r.get('effective_from',r.get('period','UNKNOWN')),as_of=r.get('as_of','2026-11-12'),period=r.get('period','UNKNOWN'),unit=r.get('unit',r.get('units')),granularity='услуга и единица',status=c['status'],coverage=r.get('coverage','UNKNOWN'),source_row_id=r.get('cost_id',r.get('rate_id',r.get('driver_id',r.get('cost_reference_id')))),source_row_sha256=c['source_row_sha256'],source_path=c['source_path'],use='Замена reference'+str(c['original_P04_value'])+' на'+str(c['value']) if c['applied'] else 'Контекст; не применён старыйpriceyear'))
    b.csvwrite(b.ROOT/'sources.csv',registry);b.dump(b.ROOT/'competition_row_lineage.json',selection);b.dump(b.ROOT/'local_rate_corrections.json',b.LOCAL_CORRECTIONS)
    print('sources',len(registry),'selectedrows',len(selection),'programme_pairs',len(pairs))

if __name__=='__main__':main()
