import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from demand_compare import correct_omsk_tobolsk


def test_tobolsk_correction_is_restricted_to_identified_flight():
    original = pd.DataFrame([
        {"destination_airport_iata": "TOX", "next_airport_name": "Тобольск", "outbound_flight_numeric": 652, "carrier_raw": "ЮВТаэро"},
        {"destination_airport_iata": "TOX", "next_airport_name": "Тобольск", "outbound_flight_numeric": 900, "carrier_raw": "ЮВТаэро"},
    ])
    corrected = correct_omsk_tobolsk(original)
    assert corrected.destination_airport_iata.tolist() == ["RMZ", "TOX"]
    assert original.destination_airport_iata.tolist() == ["TOX", "TOX"]
