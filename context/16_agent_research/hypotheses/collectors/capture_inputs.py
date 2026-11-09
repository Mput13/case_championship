#!/usr/bin/env python3
"""Read-only capture of pinned Git inputs and small public HTTP sources."""
from pathlib import Path
import argparse, csv, hashlib, io, json, subprocess, urllib.request
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
VERSION = "hypotheses-capture-v1"
GIT = {
    "front": ("71b493d0051dc3acf2a7619801e5b0eb022bddd3", [
        "data/sources.toml", "data/processed/destinations.csv", "data/raw/_manifest.json",
        "src/update.py", "src/fetch_telegram.py", "src/scan_news.py", "src/longlist_data.py"]),
    "conditional": ("bf564c7b66a2559c21e9f519ae5a3f28a489378f", [
        "context/16_conditional_decision/recommendation.md",
        "context/16_conditional_decision/calculation_limits.md",
        "context/16_conditional_decision/research/decision_evidence.csv",
        "context/16_conditional_decision/model/pilot_booking_gate.csv",
        "context/16_conditional_decision/model/comparison.csv",
        "context/16_conditional_decision/model/input_manifest.json"]),
}
HTTP = [
    ("HYP-S01", "https://ourairports.com/countries/RU/airports.csv", "ourairports_ru.csv", "OurAirports community", "airport record", "Russia as classified by source", "snapshot, effective date unknown", "Public domain per OurAirports data policy; see source page", "Coordinates are community observations, not operational approval; timezone and catchment absent"),
    ("HYP-S02", "https://khvaero.ru/passengers/schedule/?foreign=2", "khv_schedule.html", "Khabarovsk Airport", "published service rule", "routes to/from KHV", "winter 2026/27 as published", "UNKNOWN", "Planned schedule, not execution or OD; operating carrier may differ from marketing code; raw page can vary"),
]

def now(): return datetime.now(timezone.utc).isoformat()
def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--http", action="store_true"); args=ap.parse_args()
    records=[]
    for label,(commit,paths) in GIT.items():
        for path in paths:
            b=subprocess.check_output(["git","show",f"{commit}:{path}"])
            dst=ROOT/"inputs"/label/path; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(b)
            records.append(dict(dataset_id=f"GIT-{label}-{Path(path).name}",source_url=f"https://github.com/Mput13/case_championship/blob/{commit}/{path}",source_sha=commit,raw_path=str(dst.relative_to(ROOT)),sha256=sha(b),size_bytes=len(b),retrieved_at_utc=now(),publication_date="UNKNOWN",grain="repository input file",geographic_coverage="per file",temporal_coverage="per file",record_count=None,acquisition_status="ACQUIRED_RAW",limitations="Colleague input; source claims are not independently validated by capture",collector_version=VERSION,command="python3 context/16_agent_research/hypotheses/collectors/capture_inputs.py --http",license="UNKNOWN"))
    for name,src in [("research_contract.md",Path("context/16_agent_research/research_contract.md")),("data_wishlist.csv",Path("context/16_agent_research/data_wishlist.csv")),("integration_contract.md",Path("/Users/a/agent-audit-2026-09/case_championship/context/16_agent_research/integration_contract.md"))]:
        b=src.read_bytes(); dst=ROOT/"inputs"/name;dst.write_bytes(b)
        records.append(dict(dataset_id="CONTRACT-"+name,source_url="local:"+str(src.resolve()),raw_path=str(dst.relative_to(ROOT)),sha256=sha(b),size_bytes=len(b),retrieved_at_utc=now(),publication_date="2026-11-09",grain="research contract",geographic_coverage="Russia",temporal_coverage="research 2026-11-09",record_count=None,acquisition_status="ACQUIRED_RAW",limitations="Local coordination document, not market evidence",collector_version=VERSION,license="project internal"))
    if args.http:
        for sid,url,name,org,grain,geo,period,license_,limits in HTTP:
            rec=dict(dataset_id=sid,source_url=url,organisation=org,retrieved_at_utc=now(),publication_date="UNKNOWN",grain=grain,geographic_coverage=geo,temporal_coverage=period,record_count=None,collector_version=VERSION,command="python3 context/16_agent_research/hypotheses/collectors/capture_inputs.py --http",license=license_,limitations=limits)
            try:
                req=urllib.request.Request(url,headers={"User-Agent":"Case5-public-research/1.0"})
                with urllib.request.urlopen(req,timeout=40) as res:
                    b=res.read(5_000_001); rec["http_status"]=res.status;rec["final_url"]=res.url
                if len(b)>5_000_000: raise ValueError("Source exceeds 5 MB sample budget")
                if name.endswith(".csv"):
                    rows=list(csv.DictReader(io.StringIO(b.decode("utf-8-sig"))))
                    if not rows or "latitude_deg" not in rows[0]: raise ValueError("Unexpected airport CSV schema")
                    rec["record_count"]=len(rows);rec["units"]="latitude/longitude degrees; elevation feet"
                    rec["key_fields"]=["id","ident"]
                dst=ROOT/"raw"/name; dst.write_bytes(b)
                rec.update(raw_path=str(dst.relative_to(ROOT)),sha256=sha(b),size_bytes=len(b),acquisition_status="ACQUIRED_RAW")
            except Exception as exc:
                rec.update(raw_path=None,sha256=None,size_bytes=None,acquisition_status="ACCESS_FAILED",error=f"{type(exc).__name__}: {exc}")
            records.append(rec)
    out=ROOT/"inputs"/"capture_manifest.json";out.write_text(json.dumps({"created_at_utc":now(),"collector_version":VERSION,"datasets":records},ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"files":len(records),"failed":[r for r in records if r["acquisition_status"]=="ACCESS_FAILED"]},ensure_ascii=False))

if __name__=="__main__":main()
