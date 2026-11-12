"""Проверка происхождения и границ P02I. Не приёмка рынка/права/экономики."""
from pathlib import Path
import csv, hashlib, io, json, subprocess
ROOT=Path(__file__).resolve().parent
def digest(b):return hashlib.sha256(b).hexdigest()
def readcsv(p):return list(csv.DictReader(p.open(encoding='utf-8')))
def canonical(r):return json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def main():
    checks=[]
    def check(name,ok,detail):checks.append({'check':name,'pass':bool(ok),'detail':detail})
    pins=json.loads((ROOT/'input_manifest.json').read_text());cache={}
    for r in pins:
        b=subprocess.check_output(['git','show',r['commit']+':'+r['git_path']]);cache[(r['commit'],r['git_path'])]=b
        check('exact_blob:'+r['git_path'],digest(b)==r['sha256'],r['commit'])
    row_count=0
    for p in (ROOT/'inputs').glob('*.csv'):
        for r in readcsv(p):
            b=cache[(r['source_commit'],r['source_git_path'])]
            rr=list(csv.DictReader(io.StringIO(b.decode())));original=rr[int(r['source_csv_record_number'])-1]
            check('source_row:'+p.name+':'+r['source_csv_record_number'],digest(canonical(original))==r['source_row_sha256'],r['source_row_sha256'])
            row_count+=1
    sources=readcsv(ROOT/'sources.csv');sids={s['source_id'] for s in sources}
    for r in sources:
        p=ROOT/r['evidence_path']
        check('source_evidence:'+r['source_id'],p.is_file() and digest(p.read_bytes())==r['evidence_sha256'],r['evidence_path'])
    check('source_metadata',all(all(r.get(k) for k in ['url','organization','published_at','period','unit','granularity','status','coverage']) for r in sources),'UNKNOWN явно, пустые поля не принимаются')
    assumption_ids={r['assumption_id'] for r in readcsv(ROOT/'assumptions.csv')}
    cards=readcsv(ROOT/'international_market_cards.csv');costs=readcsv(ROOT/'foreign_cost_inputs.csv')
    access=readcsv(ROOT/'international_access.csv')
    for name,rows in [('cards',cards),('costs',costs),('access',access),('profiles',readcsv(ROOT/'aircraft_profiles.csv'))]:
        check(name+':source_ids',all(all(s in sids for s in r.get('source_ids',r.get('source_id','')).split(';')) for r in rows),'Все source IDs существуют в sources.csv')
        check(name+':assumptions',all(all(a in assumption_ids for a in r['assumption_ids'].split(';')) for r in rows),'Каждое допущение зарегистрировано')
    check('market_uniqueness',len(cards)==len({(r['origin_airport'],r['destination_airport'],r['via_airport']) for r in cards}),len(cards))
    check('no_open_seat_or_fare_invention',all(r['open_physical_seats']=='UNKNOWN' and r['fare_gross_rub']=='UNKNOWN' and r['fare_net_rub']=='UNKNOWN' for r in cards),'Котировки и физические кресла не подменены nominal capacity')
    check('no_future_route_admission',all(r['route_payload_status'].startswith('UNKNOWN') for r in cards),'Геометрия/публикация не подтверждает payload/право2028')
    check('no_future_cost_selection',all(r['future_rate_selected']=='UNKNOWN' and r['future_rate_lower']=='UNKNOWN' and r['future_rate_upper']=='UNKNOWN' for r in costs),'23 опубликованные ставки и16 неизвестных компонентов; нет выдуманного диапазона')
    seeds=json.loads((ROOT/'inputs/seed_cities.json').read_text());coverage=readcsv(ROOT/'city_domain_coverage.csv')
    check('all20cities_visible',{r['iata'] for r in seeds}=={r['iata'] for r in coverage} and len(coverage)==20,'Пробелы не экономический отказ')
    for o in ['IKT','BAX']:
        cr=[r for r in cards if r['origin_airport']==o and r['destination_airport']=='IST']
        check('N4_connection_not_nonstop:'+o,len(cr)==1 and cr[0]['via_airport']=='KZN' and 'via:KZN' in cr[0]['competitors_observed'],'Нельзя создать прямой рейс из connection_release')
    check('Belavia_not_RW_aircraft',all(r['form']=='Belavia_operating_partner_leg' for r in cards if r['origin_airport'] in ['SVX','LED','MCX'] and r['destination_airport']=='MSQ'),'Operating leg и опубликованный кодшер разделены')
    d=json.loads((ROOT/'delivery_branch_contract.json').read_text());zero=next(x for x in d['tu214_branches'] if x['id']=='ZERO_NEW_TU214')
    check('zero_new_tu214',len(zero['new_ready_count_by_month'])==24 and set(zero['new_ready_count_by_month'])=={0},'Заданный сценарий, существующие борта не обнулены')
    check('no_invented_positive_tu_calendar',all(r.get('new_ready_calendar') is None for r in d['tu214_branches'] if r['id']!='ZERO_NEW_TU214'),'Символические положительные ветви доP03')
    h=json.loads((ROOT/'programme_hypotheses.json').read_text())['hypotheses']
    check('hypotheses10',len(h)==10 and len({r['hypothesis_id'] for r in h})==10, 'I01..I10')
    check('hypotheses_financial_not_run',all(r['economic_status'].startswith('NOT_RUN') and r['exact_missing_fields'] and r['source_ids'] for r in h),'Готовое исследование не финальная экономика')
    check('hypotheses_sources',all(all(s in sids for s in r['source_ids']) for r in h),'Только зарегистрированные источники')
    check('tariff_qa_files',all((ROOT/'evidence'/f).exists() for f in ['TBS-TARIFF-page-1.png','TBS-TARIFF-page-2.png','TBS-TARIFF-page-3.png','TBS-TARIFF-page-4.png','TLV-TARIFF-page-1.png','TLV-TARIFF-page-2.png','RU-BY-APPOINT-page1.png']),'Визуальные доказательства прочитанных таблиц/скана')
    check('KZ_soft404_not_accepted',next(r for r in sources if r['source_id']=='KZ-AIP')['status']=='WEB_OPEN_VERIFIED_HTTP200_SOFT404_REJECTED','Прямая HTTPстраница404 не стала AIP')
    report={'status':'PASS' if all(r['pass'] for r in checks) else 'FAIL','validation_scope':'Авторская проверка exact blobs/row hashes/связности и границ; не независимая приёмка и не подтверждение рынка/ресурса/права/экономики','checks_total':len(checks),'checks_failed':sum(not r['pass'] for r in checks),'pinned_rows_verified':row_count,'checks':checks}
    (ROOT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='checks'},ensure_ascii=False,indent=2))
    for r in checks:
        if not r['pass']:print('FAIL',r)
    raise SystemExit(0 if report['status']=='PASS' else 1)
if __name__=='__main__':main()
