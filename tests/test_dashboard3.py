"""Дашборд 3: данные встроены целиком, цифры сходятся с таблицами модели, правила проверки читаются."""
import csv
import json
import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/redwings_panel_v3.html"


def payload():
    text = OUT.read_text(encoding="utf-8")
    m = re.search(r"\bconst D\s*=\s*", text)
    data, _ = json.JSONDecoder().raw_decode(text[m.end():])
    return text, data


class Dashboard3Tests(unittest.TestCase):
    def test_rays_sum_to_hub_result(self):
        _, d = payload()
        for h in d["hubs"]:
            rs = d["rays"][h["scenario"]].get(h["hub"], [])
            self.assertTrue(rs, h["hub"])
            self.assertAlmostEqual(sum(r["res"] for r in rs), h["result_mln_year"], delta=1.0, msg=f'{h["scenario"]} {h["hub"]}')

    def test_every_hub_and_ray_on_map(self):
        _, d = payload()
        for sc in d["rays"].values():
            for h, rs in sc.items():
                self.assertIn(h, d["pts"])
                for r in rs:
                    self.assertIn(r["to"], d["pts"], f"{h}-{r['to']}")

    def test_inputs_match_files(self):
        _, d = payload()
        with open(ROOT / "data/manual/known_flows.csv", encoding="utf-8") as f:
            self.assertEqual(len(d["kf"]), len(list(csv.DictReader(f))))
        with open(ROOT / "data/manual/upload_rules.csv", encoding="utf-8") as f:
            rules = list(csv.DictReader(f))
        self.assertEqual([r["expr"] for r in d["rules"]], [r["expr"] for r in rules])
        self.assertTrue(all(r["level"] in ("ошибка", "предупреждение") for r in rules))

    def test_version_switch_in_all_dashboards(self):
        for name in ("redwings_panel.html", "redwings_panel_v1.html", "redwings_panel_v3.html"):
            self.assertIn('href="redwings_panel_v3.html"', (ROOT / "outputs" / name).read_text(encoding="utf-8"), name)

    def test_demo_is_labelled(self):
        text, d = payload()
        self.assertIn("пример", d["demo"]["file_csv"])
        self.assertIn("t-demo", text)


if __name__ == "__main__":
    unittest.main()
