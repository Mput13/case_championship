#!/usr/bin/env python3
"""Three selected domestic flight instances from a dated saved RW board, not full schedule."""
from pathlib import Path
from html.parser import HTMLParser
import re,csv,json,hashlib
ROOT=Path(__file__).resolve().parent.parent
class T(HTMLParser):
 def __init__(self):super().__init__();self.s=[]
 def handle_data(self,s):
  s=s.strip()
  if s:self.s.append(s)
def text(s):
 p=T();p.feed(s);return ' '.join(p.s)
h=(ROOT/'raw/SA08.html').read_text()
assert '"today":[{"flight":"WZ 5015"' in h
assert '2026-11-9' in h
# Actual snapshot explicitly labels yesterday / today / tomorrow; preserve that source convention.
tables=re.findall(r'<table>(.*?)</table>',h,re.S)
assert len(tables)==3,len(tables)
rows=[]
for body in re.findall(r'<tr>(.*?)</tr>',tables[1],re.S):
 m=re.search(r'data-value="(WZ (?:5085|5303|1081))"',body)
 if not m:continue
 cells=re.findall(r'<td\b[^>]*>(.*?)</td>',body,re.S)
 r={'flight_number':m.group(1),'local_departure_date':'2026-11-09','departure_cell_verbatim':text(cells[1]),'arrival_cell_verbatim':text(cells[2]),'reported_status':text(cells[3]),'status':'OBSERVED','source_dataset':'SA08','source_locator':'raw/SA08.html; second of three tables; dated today=2026-11-9','limitations':'Reported status in a single public snapshot; no tail, capacity, pax or current seasonal frequency'}
 assert r['reported_status']=='Выполнен';rows.append(r)
assert len(rows)==3
out=ROOT/'normalized/flight_board_sample.csv'
with out.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
m=json.loads((ROOT/'dataset_manifest.json').read_text());m['normalized_outputs']=[x for x in m['normalized_outputs'] if x['path']!='normalized/flight_board_sample.csv'];m['normalized_outputs'].append({'path':'normalized/flight_board_sample.csv','sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'record_count':3,'grain':'selected operating flight instance reported by carrier board','transformation':'python3 context/16_agent_research/hypotheses/contributions/source_access/collectors/extract_flight_sample.py','limitations':'Selection for novelty check only; not exhaustive extraction or demand evidence.'});(ROOT/'dataset_manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(rows,ensure_ascii=False,indent=2))
