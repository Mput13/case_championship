#!/usr/bin/env python3
"""Small public-source fetches, with exact byte hashes; no dependencies."""
import argparse
import csv
import datetime as dt
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess

BASE = Path(__file__).resolve().parents[1]
SAFE_RESPONSE_HEADERS={'content-type','content-length','content-encoding','last-modified','etag','date','cache-control','expires','accept-ranges'}

def filtered_header_text(text):
    """Persist only allowlisted response metadata, never the raw header block."""
    lines=[]
    for line in text.splitlines():
        name,sep,value=line.partition(':')
        if sep and name.lower().strip() in SAFE_RESPONSE_HEADERS:
            lines.append(name.strip()+': '+value.strip())
    return '\n'.join(lines)+'\n'
SOURCES = [
    dict(dataset_id='C01', name='case_requirements_live', organization='МАИ / организаторы',
         url='https://mai-way.ru/tasks/red-wings/', filename='organizer.html',
         period='case 2026', grain='case requirements page', coverage='Red Wings case 5', license='UNKNOWN'),
    dict(dataset_id='C02', name='MIT_route_planning_lecture', organization='MIT / Peter Belobaba',
         url='https://ocw.mit.edu/courses/16-75j-airline-management-spring-2006/2ada818cad211fb33db9828526cebd4e_lect11.pdf',
         filename='mit_route_planning.pdf', period='2006-03-15', grain='lecture slide',
         coverage='airline route economics concepts; not Russian empirical calibration', license='MIT OCW CC BY-NC-SA; verify site terms'),
    dict(dataset_id='C03', name='Finnair_key_figures', organization='Finnair',
         url='https://investors.finnair.com/en/as_an_investment/key_figures', filename='finnair_key_figures.html',
         period='2021-2025', grain='company year / metric definition', coverage='Finnair group; concepts only for RW', license='UNKNOWN'),
    dict(dataset_id='C04', name='ICAO_forecasting_fleet_data', organization='ICAO',
         url='https://www.icao.int/Meetings/STA10/Documents/Sta10_Wp014_en.pdf', filename='icao_forecasting_fleet.pdf',
         period='STA10 working paper; inspect document date', grain='methodology paper section',
         coverage='traffic and fleet forecasting data requirements; international methodology', license='UNKNOWN'),
    dict(dataset_id='C05', name='UFA_announced_fuel_tariff', organization='Международный аэропорт Уфа',
         url='https://www.airportufa.ru/upload/medialibrary/2bf/ow4eayup87onwcj9faekxpmzamddh571.pdf', filename='ufa_fuel_20261111.pdf',
         period='announced effective 2026-11-11; target schedule December 2026', grain='tariff service / effective date',
         coverage='UFA public list; not network procurement contract', license='UNKNOWN'),
    dict(dataset_id='C06', name='FNS_2026_excise_rates', organization='ФНС России',
         url='https://www.nalog.gov.ru/rn25/news/activities_fts/16602418/', filename='fns_2026_excise_rates.html',
         period='2026 excise rate notice', grain='public tax-rate notice',
         coverage='Russia statutory rate; not RW effective fuel cost or receipt', license='UNKNOWN'),
    dict(dataset_id='C07', name='NK_article200_on_FNS_linked_portal', organization='ФНС-linked legal text portal / Гарант',
         url='https://nalog.garant.ru/fns/nk/948c9c0734b6e944a4727660f2d5a027/', filename='fns_linked_nk_article200.html',
         period='text available2026-11-09; effective clauses require dated interpretation', grain='legal article clause',
         coverage='Conditional excise deduction mechanism; not RW eligibility or net payment', license='UNKNOWN'),
    dict(dataset_id='C08', name='front_CEK_calibration_secondary', organization='Эксперт-Урал',
         url='https://expert-ural.com/news/pochti-na-55-viros-passazhiropotok-iz-aeroportov-chelyabinskoy-oblasti.html', filename='front_cek_secondary.html',
         period='reported2025; inspect original article', grain='regional airport passenger-count news article', source_tier='SECONDARY',
         coverage='Chelyabinsk oblast; exact airport allocation and endpoint OD unknown', license='UNKNOWN'),
    dict(dataset_id='C09', name='front_OVB_calibration_secondary', organization='АБН24',
         url='https://abnews.ru/siberia/news/novosibirsk/2025/7/20/dalnevostochnye-goroda-stali-liderami-sredi-avianapravlenij-iz-tolmachevo', filename='front_ovb_secondary.html',
         period='2025H1; publication2025-07-20', grain='airport-pair passenger-count news article', source_tier='SECONDARY',
         coverage='Novosibirsk named routes; not observed full year or endpoint OD', license='UNKNOWN'),
    dict(dataset_id='C10', name='front_OMS_calibration_secondary', organization='СуперОмск',
         url='https://superomsk.ru/news/157499-omskiy_aeroport_opublikoval_top_10_populyarnx_napr/', filename='front_oms_secondary.html',
         period='2025; publication2026-01-16', grain='airport route ranking news article', source_tier='SECONDARY',
         coverage='Omsk airport named route counts; original airport dataset not obtained', license='UNKNOWN'),
    dict(dataset_id='C11', name='UMPO_summer_cohort', organization='Ростех',
         url='https://rostec.ru/media/news/studenty-treka-krylya-rostekha-iz-moskvy-i-sankt-peterburga-proshli-praktiku-v-odk-umpo/', filename='stage19_umpo.html',
         period='2026-08-24 report of summer practice', grain='employer cohort / training event', source_tier='PRIMARY',
         coverage='43 total trainees; no ticket origin split, mode or December bookings', license='UNKNOWN'),
    dict(dataset_id='C12', name='Perm_motory_summer_cohort', organization='ОДК',
         url='https://uecrus.com/press/odk-permskie-motory-prinyali-na-praktiku-studentov-moskovskogo-vuza/', filename='stage19_perm_cohort.html',
         period='2026-07-22 report; practice began June2026', grain='employer cohort / training event', source_tier='PRIMARY',
         coverage='15 Moscow university trainees; no observed paid flight or airport choice', license='UNKNOWN'),
    dict(dataset_id='C13', name='Park_Shafran_opening', organization='Санаторий Парк Шафран',
         url='https://parkshafran.ru/news/25-iyulya-2025-otkrytie-sanatoriya-park-shafran/', filename='stage19_shafran_opening.html',
         period='opening2025-07-25; publication2025-08-01', grain='operator facility announcement', source_tier='PRIMARY',
         coverage='Opening precedes both December2025 and2026; no guest bookings or origin OD', license='UNKNOWN'),
    dict(dataset_id='C14', name='Park_Shafran_capacity', organization='Санаторий Парк Шафран',
         url='https://parkshafran.ru/', filename='stage19_shafran_home.html',
         period='undated page observed2026-11-09', grain='operator facility stock and access description', source_tier='PRIMARY',
         coverage='112 rooms and access distances; no occupancy, stay length, guest origins or airline choice', license='UNKNOWN'),
    dict(dataset_id='C15', name='M12_road_time_change', organization='Автодор',
         url='https://russianhighways.ru/press/news/139252/', filename='stage19_avtodor.html',
         period='2026-01-26 report on2025 opening', grain='road operator travel-time statement', source_tier='PRIMARY',
         coverage='Kazan-Ekaterinburg road-time savings by vehicle type; no actual modal shift or full door-to-door time', license='UNKNOWN'),
]

def publish_index(new_records):
    """Merge receipts under a file lock; independent --only fetches may overlap."""
    with (BASE/'raw/.manifest.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        previous=json.loads((BASE/'dataset_manifest.json').read_text())['datasets'] if (BASE/'dataset_manifest.json').exists() else []
        by_id={r['dataset_id']:r for r in previous}
        by_id.update({r['dataset_id']:r for r in new_records})
        records=sorted(by_id.values(),key=lambda r:r['dataset_id'])
        manifest=dict(generated_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                      path_base='context/16_agent_research/critic',datasets=records)
        (BASE/'dataset_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        fields=['dataset_id','organization','name','source_tier','source_url','publication_date','retrieved_at_utc','period','grain',
                'geographic_coverage','units','key_fields','license','acquisition_status','raw_path','sha256','byte_size','limitations']
        with (BASE/'source_registry.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(records)
        failed=[r for r in records if r['acquisition_status']=='ACCESS_FAILED']
        with (BASE/'rejected_or_unavailable.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,['dataset_id','source_url','exit_code','error','limitations'],extrasaction='ignore');w.writeheader();w.writerows(failed)
    return records

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--only');args=parser.parse_args()
    raw = BASE/'raw'; raw.mkdir(parents=True, exist_ok=True)
    records=[]
    for spec in SOURCES:
        if args.only and spec['dataset_id']!=args.only:continue
        dest=raw/spec['filename']; headers=dest.with_suffix(dest.suffix+'.headers.txt')
        argv=['curl','--location','--fail','--silent','--show-error','--max-time','40',
              '--max-filesize','6000000','--dump-header','-','--output',str(dest),spec['url']]
        started=dt.datetime.now(dt.timezone.utc).isoformat()
        run=subprocess.run(argv,text=True,capture_output=True)
        headers.write_text(filtered_header_text(run.stdout))
        ok=run.returncode==0 and dest.exists()
        data=dest.read_bytes() if ok else b''
        receipt=dict(**spec, source_url=spec['url'], retrieved_at_utc=started,
            raw_path=str(dest.relative_to(BASE)) if ok else None,
            sha256=hashlib.sha256(data).hexdigest() if ok else None,
            byte_size=len(data) if ok else None, record_count=None,
            geographic_coverage=spec['coverage'],temporal_coverage=spec['period'],
            acquisition_status='ACQUIRED_RAW' if ok else 'ACCESS_FAILED',
            value_status='UNKNOWN', publication_date=None, units='document; see extracted source checks',
            key_fields='dataset_id; URL; retrieved_at_utc', collector_version='critic-source-fetch-v2-safe-headers',
            command=argv, exit_code=run.returncode, error=run.stderr.strip() or None,
            limitations='Raw bytes obtained does not establish empirical validity. No market or network contract coefficient inferred.')
        records.append(receipt)
        receipts=BASE/'evidence/acquisition_receipts';receipts.mkdir(exist_ok=True)
        (receipts/(spec['dataset_id']+'.json')).write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    publish_index(records)
    print(json.dumps([{'id':r['dataset_id'],'status':r['acquisition_status'],'bytes':r['byte_size']} for r in records]))

if __name__=='__main__':main()
