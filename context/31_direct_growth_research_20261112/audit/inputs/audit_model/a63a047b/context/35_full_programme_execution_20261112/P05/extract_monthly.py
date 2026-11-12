"""Optional source refresh: xlrd==2.0.2; model/build need only stdlib + CSV.

python3 -m pip install --target P05/.runtime xlrd==2.0.2 --no-deps
PYTHONPATH=P05/.runtime python3 P05/extract_monthly.py
"""
import hashlib
import re
from pathlib import Path
import xlrd
from model import ROOT, write_csv, write_json

MONTHS={x:i+1 for i,x in enumerate("January February March April May June July August September October November December".split())}


def extract():
    rows=[]
    for vintage in (2025,2026):
        path=ROOT/f"evidence/NEW_AEROFLOT_{vintage}_MONTHLY.xls"
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        book=xlrd.open_workbook(str(path))
        for s in book.sheets():
            assert "Passengers carried" == s.cell_value(10,2)
            assert "Domestic" == s.cell_value(12,2).strip()
            assert "thousands" == s.cell_value(10,3)
            for col in range(4,s.ncols):
                h=" ".join(str(s.cell_value(1,col)).split())
                match=re.fullmatch(r"([A-Za-z]+)\s+(2025|2026)",h)
                if not match:
                    continue
                month=f"{match[2]}-{MONTHS[match[1]]:02d}"
                if match[2]!=str(vintage):
                    continue
                for metric,row,unit in [("passengers_all",10,"thousand_carrier_passengers"),("passengers_international",11,"thousand_carrier_passengers"),("passengers_domestic",12,"thousand_carrier_passengers"),("RPK_domestic",6,"million_passenger_km"),("ASK_domestic",34,"million_seat_km"),("LF_domestic",27,"fraction")]:
                    val=s.cell_value(row,col)
                    if not isinstance(val,(int,float)):
                        continue
                    rows.append(dict(month=month,entity=s.name,metric=metric,value=val,unit=unit,status="observed_published_carrier_aggregate",
                        source_id=f"NEW_AEROFLOT_{vintage}_MONTHLY",source_sha256=digest,source_sheet=s.name,source_row_1based=row+1,source_column_1based=col+1,
                        scope="domestic_or_total_carrier_aggregate_not_endpointOD",collection="new_primary_http_then_xlrd",as_of="2026-11-12"))
    write_csv(ROOT/"aviation_monthly_history.csv",rows)
    counts={y:len([r for r in rows if r['metric']=='passengers_domestic' and r['entity']=='Aeroflot Group' and r['month'].startswith(str(y))]) for y in (2025,2026)}
    assert counts=={2025:12,2026:10},counts
    write_json(ROOT/"evidence/monthly_extraction.json",dict(parser="xlrd2.0.2",data_cells=len(rows),monthly_group_domestic_counts=counts,
        profile_use="2025Group domestic seasonal analogue only;2026JanOct kept outside profile fitting",separate_entity="Aeroflot Airline is a separate entity, not added to Group",
        not_endpoint_OD=True,not_market_share_denominator=True))
    print(counts)


if __name__=="__main__":
    extract()
