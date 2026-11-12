"""Read-only acquisition. All outputs stay in P04; no paid/API side effects."""
import concurrent.futures
import csv
import hashlib
import io
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import requests
import fitz

ROOT = Path(__file__).resolve().parent
PLAN = 'b4d2ddf690440eb5cd051839cc263cf16b364ca4'
AUTHOR = 'dceadc98f9a293d7530cb7bc50ca4411a95aa4b6'
CITY = 'c18f7640ea36647a05b39089e5293f22dd009f63'
RECEIPTS = []

def sha(b):
    return hashlib.sha256(b).hexdigest()

def pin(commit, path, name):
    b = subprocess.check_output(['git', 'show', f'{commit}:{path}'])
    dst = ROOT / 'inputs' / name
    dst.write_bytes(b)
    RECEIPTS.append(dict(source_id=name, acquisition='saved_git_blob', input_commit=commit,
                         input_path=path, local_path=str(dst.relative_to(ROOT)), sha256=sha(b), bytes=len(b)))
    return b

def fetch(item):
    sid, url = item
    now = datetime.now(timezone.utc).isoformat()
    try:
        r = requests.get(url, timeout=35, headers={'User-Agent':'RedWingsCaseResearch/1.0 public sources'})
        r.raise_for_status()
        b = r.content
        ext = '.pdf' if b.startswith(b'%PDF') else '.html'
        dst = ROOT / 'sources' / (sid + ext)
        dst.write_bytes(b)
        txt = ''
        if ext == '.pdf':
            with fitz.open(stream=b, filetype='pdf') as doc:
                txt = '\n'.join(f'\n--- PDF PAGE {i+1} ---\n' + p.get_text() for i,p in enumerate(doc))
        else:
            from html import unescape
            txt = re.sub(r'(?is)<(script|style).*?>.*?</\1>', '', r.text)
            txt = unescape(re.sub('<[^>]+>', ' ', txt))
            txt = '\n'.join(re.sub(r'\s+',' ',x).strip() for x in txt.splitlines() if x.strip())
        txt='\n'.join(line.rstrip() for line in txt.splitlines())+'\n'
        (ROOT / 'sources' / (sid+'.txt')).write_text(txt)
        return dict(source_id=sid, url=url, final_url=r.url, acquisition='new_public_HTTP_GET',
                    retrieved_at=now, status='ACQUIRED', local_path=str(dst.relative_to(ROOT)),
                    sha256=sha(b), text_sha256=sha(txt.encode()),text_normalization='line-end whitespace stripped; raw HTTP bytes preserved', bytes=len(b), content_type=r.headers.get('Content-Type'))
    except Exception as e:
        return dict(source_id=sid, url=url, acquisition='new_public_HTTP_GET', retrieved_at=now,
                    status='UNAVAILABLE_THIS_ATTEMPT', error=f'{type(e).__name__}: {e}')

def main():
    if (ROOT/'source_receipts.json').exists():
        raise SystemExit('Existing capture preserved. For URL reproduction use --refetch-to NEW_DIR; offline checks do not refetch.')
    for f in ['common_spec.json','requirements.csv','method_map.csv','variant_research_plan.json','assumptions_register.csv']:
        try:
            pin(PLAN, 'context/34_full_programme_plan_20261112/'+f,'plan_'+f)
        except subprocess.CalledProcessError:
            raise
    for f in ['data/assumptions/network.csv','context/12_network_economics/inputs.json',
              'context/12_network_economics/sources.json','context/12_network_economics/published_cost_reference.csv',
              'src/network_model.py','data/assumptions/subsidy_cap_84_103.csv']:
        pin(AUTHOR,f,'author_'+Path(f).name)
    pin(CITY,'context/33_five_city_reassessment_20261112/README.txt','five_city_README.txt')
    core='505e24663e5952bae9b9540bb9a5a622663bfc2a'
    reg=pin(core,'context/16_agent_research/core/branches/operating_evidence/source_registry.csv','saved_airport_sources.csv')
    pin(core,'context/16_agent_research/core/branches/operating_evidence/normalized/airport_cost_selected_verified.csv','saved_airport_rates.csv')
    for f in ['monthly_compensation.csv','README.md','comparison_checks.json','reuters_receipt.json']:
        pin(PLAN,'context/28_evening_run_20261110/post_close/20261110_fuel_explanation/'+f,'fuel_history_'+f)
    for f in ['cost_parameters.csv','budget_terms.csv','range_registry.csv']:
        pin(PLAN,'context/23_night_run_20261110/integration/cost_kover/afadee35/'+f,'historical_'+f)
    needed=['ufa_fuel_20261111','ufa_services_20261111','omsk_tariff_base_20260821']
    urls=[(r['dataset_id'],r['source_url']) for r in csv.DictReader(io.StringIO(reg.decode())) if r['dataset_id'] in needed]
    urls += [
      ('ufa_services_20261101','https://www.airportufa.ru/upload/medialibrary/be3/76qp5v5bwi8cc5ka59wyd0q179l3biy6.pdf'),
      ('ufa_fuel_20260817','https://www.airportufa.ru/upload/medialibrary/38c/4agy8jfom9bcf7504sc6m053wnfjo646.pdf'),
      ('ufa_tariff_index','https://www.airportufa.ru/partners/airlines/tariffs/'),
      ('goj_tariff_index','https://ar-goj.ru/partners/airlines/tariffs/'),
      ('kuf_tariff_index','https://ar-kuf.ru/partners/airlines/tariffs/'),
      ('ar_discounts_2026','https://ar-goj.ru/upload/iblock/281/vcaqxbhgah3dkkcdswa7xtgh7k8maln1/Polozhenie-o-predostavlenii-skidok-aviakompaniyam-v-aeroportakh-AO-UK-Aeroporty-Regionov-s-01.01.2026.pdf'),
      ('khv_tariff_202611','https://khvaero.ru/partners/open-info-khabaero/law/fee/prices/tarif_2026_11.pdf'),
      ('fts_excise_2026','https://www.nalog.gov.ru/rn25/news/activities_fts/16602418/'),
      ('nk200','https://nalog.garant.ru/fns/nk/948c9c0734b6e944a4727660f2d5a027/'),
      ('nk201','https://nalog.garant.ru/fns/nk/1efa800d5f474b5131ebc599024686d7/'),
      ('nk203','https://nalog.garant.ru/fns/nk/53c63b880ad65ac5ac688c75b48629cb/'),
      ('uec_pd8_support','https://www.uecrus.com/press/odk-vnedrila-it-sistemu-servisnoy-podderzhki-dvigateley-dlya-samoletov-ms-21-i-sj-100/'),
      ('favt_regional_index','https://favt.gov.ru/dejatelnost-vozdushnye-perevozki-subsidirovanie-regionalnyh-vozdushnyh-perevozok/'),
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(fetch, urls):
            RECEIPTS.append(r)
            print(r['source_id'],r.get('status'),r.get('bytes',r.get('error')))
    (ROOT/'source_receipts.json').write_text(json.dumps(RECEIPTS,ensure_ascii=False,indent=2)+'\n')

if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--refetch-to',help='New subdirectory of P04 for public URL replay; never rewrites frozen sources')
    args=parser.parse_args()
    if args.refetch_to:
        old_root=ROOT
        records=json.loads((ROOT/'source_receipts.json').read_text())
        target=(ROOT/args.refetch_to).resolve()
        if not target.is_relative_to(ROOT) or target==ROOT or target.exists():
            raise SystemExit('Target must be a NEW directory inside P04')
        ROOT=target
        (ROOT/'sources').mkdir(parents=True)
        urls=[(r['source_id'],r['url']) for r in records if r.get('url')]
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
            new=list(ex.map(fetch,urls))
        (ROOT/'source_receipts.json').write_text(json.dumps(new,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'new_capture':str(ROOT.relative_to(old_root)),'records':len(new)}))
    else:
        main()
