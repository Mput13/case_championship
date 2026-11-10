"""Small executable regression for R6, no archives or network required."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from catchment_extra import weather_counts, weather

rows=[('2024-01-01',-9999,-9999),('2024-01-02',-210,20),
      ('2024-01-03',0,130),('2024-01-04',0,-9999),('2024-01-05',-9999,20)]
c=weather_counts(rows,-20,12)
assert c == dict(frost=1,wind=1,either=2,valid_temp_days=3,valid_wind_days=3,
                valid_joint_days=2,record_days=5,observations=5),c
s=weather_counts([('2024-01-01',-9999,-9999)],-20,12)
assert s['valid_joint_days']==s['valid_temp_days']==s['valid_wind_days']==0
# без локальных архивов NOAA погода должна быть неизвестной; с архивами — посчитанной по допустимым дням
_w = weather()
_have = any(Path(__file__).resolve().parents[1].joinpath('data/raw/weather').glob('*.gz'))
if not _have:
    assert all(x['bad_weather_days'] is None for x in _w.values())
else:
    assert any(x['bad_weather_days'] is not None for x in _w.values())
print('PASS: sentinel days excluded; separate valid-field denominators; absent archives UNKNOWN')
