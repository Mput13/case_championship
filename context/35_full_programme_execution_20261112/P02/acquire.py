"""Public, unauthenticated source snapshots; never books or calls paid APIs."""
import concurrent.futures, datetime, hashlib, json, pathlib, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
URLS = {
    'NEW_UVT_SCHEDULE': 'https://www.uvtaero.ru/raspisanie',
    'NEW_UVT_FLEET': 'https://www.uvtaero.ru/flots/crj-200',
    'NEW_UVT_FARES': 'https://www.uvtaero.ru/conditions',
    'NEW_AZ_WINTER': 'https://azimuth.ru/ru/news/aviakompaniya-azimut-otkryla-prodazhu-aviabiletov-na-osen-zimu-2026-2027-iz-mineralnyh-vod-krasnodara-kalugi-i-ufy',
    'NEW_AZ_FARES': 'https://azimuth.ru/ru/passengers/fares',
    'NEW_AZ_FLEET': 'https://azimuth.ru/ru/about/fleet',
    'NEW_RW_SALE': 'https://flyredwings.com/november-sale-2026/',
    'NEW_RW_FARES': 'https://flyredwings.com/fares/',
    'NEW_RW_WINTER': 'https://flyredwings.com/press/news/red-wings-pereshla-na-osenne-zimnee-raspisanie-poletov/',
    'NEW_RW_OMSK': 'https://flyredwings.com/press/news/red-wings-stanet-bazovoj-aviakompaniej-omskogo-aeroporta/',
    'NEW_RW_BELAVIA': 'https://flyredwings.com/en/press/news/red-wings-i-belavia-rasshiryayut-marshrutnuyu-set-v-ramkax-kod-sheringa/',
    'NEW_N4_TRANSFER': 'https://mindortrans.tatarstan.ru/index.htm/news/2514977.htm',
    'NEW_OMSK_SCHEDULE': 'https://www.aeroomsk.ru/karta-poleta/pdf/w26/w26-20261105.pdf',
}

def fetch(item):
    key, url = item
    row = dict(source_id=key, url=url, retrieved_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), acquisition='new_public_http', primary=True)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (research; public information)'})
        with urllib.request.urlopen(req, timeout=35) as r:
            data = r.read(6_000_001)
            if len(data) > 6_000_000:
                raise ValueError('source exceeds 6 MB cap')
            ext = '.pdf' if data.startswith(b'%PDF') else '.html'
            target = ROOT / 'evidence' / (key + ext)
            target.write_bytes(data)
            row.update(http_status=r.status, final_url=r.url, content_type=r.headers.get('Content-Type'), bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), path=str(target.relative_to(ROOT)), status='ACQUIRED')
    except Exception as e:
        row.update(status='ACCESS_FAILED', error=str(e))
    return row

if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(fetch, URLS.items()))
    (ROOT / 'evidence' / 'fetch_receipts.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ('source_id','status','bytes','error') if k in r} for r in rows], ensure_ascii=False))
