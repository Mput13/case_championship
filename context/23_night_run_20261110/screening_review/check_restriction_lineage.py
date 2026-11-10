"""Bounded fifth source check: BAX/KUF reported-day lineage, not full scraping."""
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
SHA = "2f03b693a62c219e9475fcd1e26295039f6a49d7"

def read(path):
    raw = subprocess.check_output(["git", "show", SHA+":"+path])
    return raw, list(csv.DictReader(io.StringIO(raw.decode())))

def main():
    raw, posts = read("data/raw/favt_posts.csv")
    aliases_raw, alias_rows = read("data/manual/kover_aliases.csv")
    _, days = read("data/processed/kover_days.csv")
    by_days = {r["iata"]: r for r in days}
    aliases = {r["iata"]: r["aliases"].split(";") for r in alias_rows}
    window = [r for r in posts if "2025-11-10" <= r["dt_msk"][:10] <= "2026-11-09"]
    checked = {}
    for i in ("BAX", "KUF"):
        pattern = re.compile("|".join(r"(?<![а-я])"+re.escape(x)+r"(?![а-я])" for x in aliases[i]), re.I)
        hits = [r for r in window if pattern.search(r["text"].replace("ё", "е"))]
        hitdays = sorted({r["dt_msk"][:10] for r in hits})
        assert len(hitdays) == int(by_days[i]["last365_days"])
        checked[i] = {"aliases": aliases[i], "main_text_mentions": len(hits), "mention_days": len(hitdays),
                      "stored_reported_days": int(by_days[i]["last365_days"]), "dates": hitdays}
    # One date, two primary messages: intro and lift count as one publication day.
    samples = []
    for ident, event in (("2601", "intro"), ("2609", "lift")):
        p = next(r for r in posts if r["id"] == ident)
        assert p["dt_msk"][:10] == "2025-11-10"
        assert ("ВВЕДЕНЫ" if event == "intro" else "СНЯТЫ") in p["text"]
        samples.append({"id": ident, "event_manually_read": event, "datetime_msk": p["dt_msk"],
                        "primary_url": "https://t.me/s/favt_info/"+ident,
                        "text_sha256": hashlib.sha256(p["text"].encode()).hexdigest(),
                        "parser_version": p["parser_version"], "main_text_only": True})
    result = {"scope": "bounded_stored_primary_capture_and_derived_count; NOT full raw-to-derived replay or live corpus completeness",
              "source_commit": SHA, "source_path": "data/raw/favt_posts.csv",
              "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "rows": len(posts),
              "aliases_sha256": hashlib.sha256(aliases_raw).hexdigest(), "period": ["2025-11-10", "2026-11-09"],
              "cities": checked, "sample_posts": samples,
              "native_errors": ["URL https://t.me/s/favt_info/2601 is not accessible via this tool.", "URL https://t.me/s/favt_info/2609 is not accessible via this tool."],
              "limits": ["No live completeness proof; zero means no matching captured publication in this window.",
                         "Mention-day equality is a narrow independent cross-check, not replacement of all-airport event parser.",
                         "No proof of downtime, cancellations, future risk or missing BAX messages."]}
    (HERE/"restriction_lineage.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({"cities": {i: {k:v for k,v in x.items() if k != "dates"} for i,x in checked.items()}, "samples": samples}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
