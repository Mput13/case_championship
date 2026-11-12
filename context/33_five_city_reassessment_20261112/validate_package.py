"""Offline validation of the assembled evidence package; no network calls."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit
import csv
import hashlib
import json
import re

from synthesis_content import CITY_ORDER, CITY_SECTIONS, ROUTE_NOTES

ROOT = Path(__file__).resolve().parent
HEADERS = {
    "sources": "source_id,title,organization,url,published_at,accessed_at,period,geography,metric,unit,source_type,access_status,limitations",
    "claims": "claim_id,claim,evidence_status,source_ids,period,geography,value,unit,mechanism,decision_impact,uncertainty",
    "routes": "origin,destination,product,season,competitors,frequency_evidence,demand_evidence,ground_alternative,rw_overlap,operating_constraints,assessment,source_ids,missing_fields",
    "features": "feature_id,feature,evidence_ids,mechanism,affected_markets,magnitude_or_bound,counterevidence,decision_effect,unknowns",
}


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links, self.sections = [], [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a":
            self.links.append(attrs.get("href", ""))
        if tag == "section":
            self.sections.append(attrs.get("id"))


def main():
    manifest = json.loads((ROOT / "input_manifest.json").read_text())
    for item in manifest:
        raw = (ROOT / item["path"]).read_bytes()
        assert len(raw) == item["bytes"], item["path"]
        assert hashlib.sha256(raw).hexdigest() == item["sha256"], item["path"]
    assert set(CITY_SECTIONS) == set(CITY_ORDER)
    counts = {}
    for code in CITY_ORDER:
        directory = ROOT / "cities" / code
        data = {}
        for name, header in HEADERS.items():
            names, records = read_csv(directory / (name+".csv"))
            assert names == header.split(","), (code, name)
            assert records and all(None not in row and all(x is not None for x in row.values()) for row in records)
            data[name] = records
        sources = {r["source_id"] for r in data["sources"]}
        claims = {r["claim_id"] for r in data["claims"]}
        features = {r["feature_id"] for r in data["features"]}
        assert len(sources) == len(data["sources"])
        assert len(claims) == len(data["claims"])
        assert len(features) == len(data["features"])
        for row in data["claims"] + data["routes"]:
            refs = re.findall(code+r"-S\d+", row["source_ids"])
            assert refs and set(refs) <= sources, (code, row)
        for row in data["features"]:
            refs = re.findall(code+r"-[SC]\d+", row["evidence_ids"])
            assert refs and set(refs) <= sources | claims, (code, row)
        for row in data["claims"]:
            if row["evidence_status"].upper() == "UNKNOWN":
                assert row["value"] == "", (code, row)
        for _, _, ids in CITY_SECTIONS[code]["paragraphs"]:
            assert set(ids) <= sources, (code, ids)
        destinations = {r["destination"] for r in data["routes"]}
        assert all(note[0] in destinations for note in ROUTE_NOTES[code]), code
        decision = json.loads((directory / "decision.json").read_text())
        options = decision.get("options", decision.get("alternatives"))
        assert options and len(options) == 6, code
        assert (directory / "dossier.md").stat().st_size > 2000, code
        counts[code] = {name:len(records) for name, records in data.items()}
    report = (ROOT / "report.html").read_text()
    doc = Document()
    doc.feed(report)
    assert len(doc.ids) == len(set(doc.ids)), "duplicate anchors"
    required = {"rule", "method", "economics", "decision", "assumptions", "evidence"} | {c.lower() for c in CITY_ORDER}
    assert required <= set(doc.sections), required - set(doc.sections)
    local_links = 0
    for href in doc.links:
        parsed = urlsplit(href)
        if parsed.scheme or parsed.netloc:
            assert parsed.scheme in {"https", "http"}, href
            continue
        if parsed.path:
            target = ROOT / unquote(parsed.path)
            # This validator writes its own linked result after all checks pass.
            assert target.is_file() or target == ROOT / "validation.json", href
            local_links += 1
        elif parsed.fragment:
            assert unquote(parsed.fragment) in doc.ids, href
    assert "Cannot publish" not in report
    out = {
        "status": "PASS", "scope": "offline_provenance_registry_links_document_structure",
        "pinned_inputs": len(manifest), "cities": counts, "report_sections": doc.sections,
        "local_links_checked": local_links, "report_sha256": hashlib.sha256(report.encode()).hexdigest(),
        "not_proven": ["observed OD", "realized revenue", "contracted costs or support",
                       "actual fleet availability", "commercial launch readiness", "full profit"],
    }
    (ROOT / "validation.json").write_text(json.dumps(out, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
