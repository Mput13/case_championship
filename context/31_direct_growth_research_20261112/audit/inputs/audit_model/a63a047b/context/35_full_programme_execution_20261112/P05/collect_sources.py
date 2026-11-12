"""Read-only public primary-source collection; no browser, accounts or paid data."""
import concurrent.futures
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parent
SOURCES=[
    ("NEW_FAVT_2025", "https://www.favt.gov.ru/novosti-novosti?id=17763&version=print", "2025 domestic81.45m, international27.40m; carrier traffic, not endpointOD"),
    ("NEW_FAVT_H1", "https://www.favt.gov.ru/novosti-novosti?id=16352&version=print", "2025H1 domestic38.1m; national aggregate"),
    ("NEW_MINTRANS_9M", "https://mintrans.gov.ru/storage/app/uploads/public/693/a67/76d/693a6776d1023744670920.pdf", "2025JanSep domestic63.3m; p5; bulletin not monthly route data"),
    ("NEW_UFA_2025", "https://www.airportufa.ru/news/2025/mezhdunarodnyy-aeroport-ufa-podvel-itogi-2025-goda/", "2025airport4,929,715; domestic4m rounded; notOD"),
    ("NEW_UFA_2026", "https://airportufa.ru/news/2026/itogi-raboty-otrasli-v-letniy-period/", "2026JanAug domestic2,563,649; international666,148; airport grain"),
    ("NEW_FNS_OUTSIDE_MOSCOW", "https://www.nalog.gov.ru/rn74/news/tax_doc_news/9421077/", "2019 tax authority clarification: all itinerary points outside Moscow/Moscowregion; not2027 legal guarantee"),
    ("NEW_MIT_CHOICE", "https://dspace.mit.edu/entities/publication/f3b76f4c-50f8-4a58-b8bc-065eaa1baa13", "Booking and seat-availability data identify itinerary/fare choice; no Russian coefficients transferred"),
    ("NEW_MIT_LIMITS", "https://dspace.mit.edu/entities/publication/db824909-798a-47f9-92cd-2f0720656bae", "Logit substitution limitations; not RW numerical calibration"),
    ("NEW_AEROFLOT_IR", "https://ir.aeroflot.ru/ru/reporting/traffic-statistics/", "Attempted monthly carrier series; web returned access restricted; not usableOD"),
    ("NEW_AEROFLOT_2025_MONTHLY", "https://ir.aeroflot.ru/fileadmin/user_upload/files/rus/reports/oper_stat/2025/traffic_figures_december.xls", "Full2025 monthly group and individual-carrier statistics; carrier segments, not OD"),
    ("NEW_AEROFLOT_2026_MONTHLY", "https://ir.aeroflot.ru/fileadmin/user_upload/files/rus/reports/oper_stat/2026/traffic_figures_2026_october.xls", "2026JanOct monthly carrier statistics; not OD"),
]


def fetch(item):
    sid,url,scope=item
    row=dict(source_id=sid,url=url,scope=scope,collection="new_public_http",retrieved_at=datetime.now(timezone.utc).isoformat())
    try:
        with urlopen(Request(url,headers={"User-Agent":"Research source verification"}),timeout=20) as r:
            data=r.read(15_000_000);ct=r.headers.get("Content-Type","")
            row.update(http_status=r.status,content_type=ct,final_url=r.url)
        suffix=".xls" if url.endswith('.xls') else ".pdf" if "pdf" in ct else ".html"
        dest=ROOT/"evidence"/(sid+suffix);dest.write_bytes(data)
        row.update(local_path=str(dest.relative_to(ROOT)),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),status="FETCHED_SOURCE_CONTENT_REQUIRES_SCOPE_CHECK")
        if "Доступ к сайту временно ограничен" in data.decode("utf-8",errors="ignore"):
            row["status"]="ACCESS_RESTRICTED_NOT_DATA"
    except Exception as e:
        row.update(status="FETCH_FAILED_NOT_DISPROOF",error=repr(e))
    return row


if __name__=="__main__":
    (ROOT/"evidence").mkdir(exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        receipts=list(pool.map(fetch,SOURCES))
    (ROOT/"evidence/fetch_receipts.json").write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps([{k:r[k] for k in ["source_id","status","bytes","error"] if k in r} for r in receipts],ensure_ascii=False))
