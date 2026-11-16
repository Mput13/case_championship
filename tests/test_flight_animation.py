"""Проверки расписания и встроенной анимации полётов хаба Омск (OMS)."""
import csv
import json
import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FlightAnimationTests(unittest.TestCase):
    def test_animation_payload_and_invariants(self):
        import sys
        sys.path.insert(0, str(ROOT / "src"))
        from build_flight_animation import build_animation_payload

        payload = build_animation_payload()
        self.assertIn("OMS", payload["pts"])
        modes = payload["modes"]
        self.assertEqual(set(modes), {"radial", "full", "start"})

        # Радиальная (5+1 ВС): без фидеров KJA/BAX, ровно 50 оборотов = 100 рейсов
        r = modes["radial"]
        self.assertEqual(len(r["aircraft"]), 5)
        self.assertEqual(r["stats"]["total_rotations"], 50)
        self.assertEqual(r["stats"]["total_legs"], 100)
        self.assertLessEqual(r["stats"]["max_ac_bh"], 70.0)
        self.assertGreaterEqual(r["stats"]["min_turn_min"], 60)
        self.assertNotIn("KJA", r["spokes"])
        self.assertNotIn("BAX", r["spokes"])

        # Полная хабовая (7+1 ВС): 9 лучей, ровно 64 оборота = 128 рейсов
        f = modes["full"]
        self.assertEqual(len(f["aircraft"]), 7)
        self.assertEqual(f["stats"]["total_rotations"], 64)
        self.assertEqual(f["stats"]["total_legs"], 128)
        self.assertLessEqual(f["stats"]["max_ac_bh"], 70.0)
        self.assertGreaterEqual(f["stats"]["min_turn_min"], 60)
        self.assertIn("KJA", f["spokes"])
        self.assertIn("BAX", f["spokes"])

        # Старт хаба (2+1 ВС): ровно 44 рейса из oms_ramp_week_flights.csv
        with open(ROOT / "data/external/colleagues/oms_ramp_week_flights.csv", encoding="utf-8") as fh:
            csv_count = sum(1 for _ in csv.DictReader(fh))
        s = modes["start"]
        self.assertEqual(len(s["aircraft"]), 2)
        self.assertEqual(s["stats"]["total_legs"], csv_count)
        self.assertLessEqual(s["stats"]["max_ac_bh"], 70.0)

    def test_embedded_in_dashboard3_and_standalone(self):
        panel_html = (ROOT / "outputs/redwings_panel.html").read_text(encoding="utf-8")
        m = re.search(r"\bconst D\s*=\s*", panel_html)
        self.assertIsNotNone(m)
        d, _ = json.JSONDecoder().raw_decode(panel_html[m.end():])
        self.assertIn("anim", d)
        self.assertEqual(d["anim"]["modes"]["radial"]["stats"]["total_legs"], 100)

        standalone = (ROOT / "outputs/oms_flight_animation.html").read_text(encoding="utf-8")
        self.assertIn("const ANIM", standalone)
        self.assertLess(standalone.lower().find("<meta charset=\"utf-8\">"), 1024)


if __name__ == "__main__":
    unittest.main()
