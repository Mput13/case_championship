"""Known public URLs only. Receipts and small extracts; full HTML ignored locally."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.request

HERE = Path(__file__).resolve().parent
SOURCES = [
    ("case", "https://mai-way.ru/tasks/red-wings/", ["2027", "2028", "500", "Жуковский", "Екатеринбург"]),
    ("REN_pax", "https://ar-ren.ru/about/news/aeroport-orenburg-obsluzhil-za-2025-god-bolee-950/", ["951", "885,5", "65,6"]),
    ("OMS_mro", "https://www.aeroomsk.ru/ob-aeroporte/press-tsentr/novosti/207/", ["03.12.2024", "В настоящее время ИАС"]),
    ("RW_support", "https://flyredwings.com/press/news/red-wings-pereshla-na-osenne-zimnee-raspisanie-poletov/", ["27 октября 2026", "Полеты выполняются из опорных"]),
]

class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip-1)
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

def fetch(spec):
    name, url, terms = spec
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 independent-source-review"})
    with urllib.request.urlopen(req, timeout=25) as response:
        raw = response.read()
        record = {"id": name, "url": url, "final_url": response.url, "status": response.status,
                  "accessed_utc": datetime.now(timezone.utc).isoformat(),
                  "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                  "content_type": response.headers.get("Content-Type"),
                  "acquisition": "textual_HTTP_known_URL_no_browser"}
    p = HERE/"raw_public"
    p.mkdir(exist_ok=True)
    (p/(name+".html")).write_bytes(raw)
    parser = Text()
    parser.feed(raw.decode("utf-8", errors="replace"))
    text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
    (p/(name+".txt")).write_text(text+"\n")
    record["term_occurrences"] = {x: text.count(x) for x in terms}
    # At most 24 words of source text per receipt, distributed across key terms.
    budget = 24
    extracts = []
    for term in terms:
        pos = text.find(term)
        if pos >= 0 and budget:
            words = text[pos:].split()[:min(budget, 6)]
            extracts.append(" ".join(words))
            budget -= len(words)
    record["short_extracts"] = extracts
    return record

def main():
    with ThreadPoolExecutor(max_workers=4) as ex:
        records = list(ex.map(fetch, SOURCES))
    records[0]["native_open_error"] = "URL https://mai-way.ru/tasks/red-wings/ is not accessible via this tool."
    records[0]["fallback_reason"] = "Native web.open cannot access this one URL; direct public HTTP works. No live-session or infrastructure action."
    (HERE/"primary_receipts.json").write_text(json.dumps(records, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps([{k: r[k] for k in ("id", "status", "sha256", "bytes", "term_occurrences", "short_extracts")} for r in records], ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
