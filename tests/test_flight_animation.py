"""Проверки расписания, справочников аэропортов/конкурентов и встроенной анимации хаба Омск (OMS)."""
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

        # Интерактивные данные аэропортов, конкурентов и лучей
        airports = payload["airports"]
        for code in ("OMS", "IKT", "UUD", "VOG", "MOW", "GSV", "GOJ", "KUF", "KJA", "BAX", "UFA", "NOZ", "SVX"):
            self.assertIn(code, airports)
        self.assertTrue(airports["KJA"]["comp_hub"])
        self.assertIn("Аэрофлот", airports["KJA"]["comp_hub_carrier"])
        self.assertTrue(airports["IKT"]["comp_hub"])
        self.assertEqual(airports["IKT"]["comp_hub_carrier"], "S7")
        self.assertGreaterEqual(len(airports["OMS"]["oms_carriers"]), 10)
        self.assertTrue(airports["OMS"]["tariffs"])

        spokes = payload["spokes"]
        self.assertIn("IKT", spokes)
        self.assertIsNotNone(spokes["IKT"]["base"])
        self.assertEqual(spokes["BAX"]["comp"]["fare_tr"], 15012)
        self.assertEqual(spokes["KUF"]["comp"]["fare_tr"], 16405)
        self.assertGreaterEqual(len(payload["ramp_conns"]), 10)

    def test_prod_panel_clean_and_standalone_page(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import package_dashboard as pd

        panel_bytes = (ROOT / "outputs/redwings_panel.html").read_bytes()
        pd.validate_html(panel_bytes)
        panel_html = panel_bytes.decode("utf-8")
        m = re.search(r"\bconst D\s*=\s*", panel_html)
        self.assertIsNotNone(m)
        d, _ = json.JSONDecoder().raw_decode(panel_html[m.end():])
        self.assertNotIn("anim", d)
        self.assertNotIn("anim-card", panel_html)
        self.assertIn('href="oms_flight_animation.html"', panel_html)

        standalone_bytes = (ROOT / "outputs/oms_flight_animation.html").read_bytes()
        pd.validate_html(standalone_bytes)
        standalone = standalone_bytes.decode("utf-8")
        self.assertIn("const ANIM", standalone)
        self.assertIn("mountOmsFlightPlayer", standalone)
        self.assertIn("an-mob-hide", standalone)
        self.assertIn("an-fold", standalone)
        self.assertLess(standalone.lower().find('<meta charset="utf-8">'), 1024)


if __name__ == "__main__":
    unittest.main()
