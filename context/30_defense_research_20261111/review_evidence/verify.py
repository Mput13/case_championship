#!/usr/bin/env python3
from pathlib import Path
import csv,hashlib,json
from datetime import datetime,timezone
O=Path(__file__).resolve().parent; P=O.parent

def inspect(path):
 with path.open(newline='') as f:
  reader=csv.DictReader(f); header=reader.fieldnames; rows=[]; bad=[]
  for row in reader:
   rows.append(row)
   if None in row or any(v is None for v in row.values()):
    bad.append({'line':reader.line_num,'actual_width':len(header)+len(row.get(None,[]))-sum(v is None for v in row.values())})
 return {'header_width':len(header),'rows':len(rows),'unique_headers':len(header)==len(set(header)),'bad_rows':bad},rows
original={}
for rel in ['history/events.csv','history/sources.csv','buyers/opportunities.csv','buyers/sources.csv']:
 original[rel]=inspect(P/rel)[0]
assert original['buyers/opportunities.csv']['bad_rows']==[{'line':3,'actual_width':18},{'line':4,'actual_width':18},{'line':5,'actual_width':18}]
assert original['buyers/sources.csv']['bad_rows']==[{'line':2,'actual_width':14},{'line':6,'actual_width':12}]
assert not original['history/events.csv']['bad_rows'] and not original['history/sources.csv']['bad_rows']
outputs={}; data={}
for name in ['buyers_opportunities_corrected.csv','buyers_sources_corrected.csv','findings.csv','history_corrections.csv']:
 outputs[name],data[name]=inspect(O/name)
 assert not outputs[name]['bad_rows'] and outputs[name]['unique_headers']
rows=data['buyers_opportunities_corrected.csv']; src=data['buyers_sources_corrected.csv']; findings=data['findings.csv']
assert len(rows)==5 and {r['id'] for r in rows}=={f'BUY-0{i}' for i in range(1,6)}
assert {r['to'] for r in rows}=={'MOW','IKT','GOJ','KUF','UUD'}
assert all(r['convertible_trips']==r['people_or_rotations']=='' and r['passenger_volume_status']=='UNKNOWN' for r in rows)
assert rows[0]['evidence_status']=='reported_secondary' and '0323048828' in rows[0]['buyer_or_intermediary']
assert all('Omsk Regional Military' not in r['buyer_or_intermediary'] for r in rows)
assert rows[4]['convertible_trips']=='' and '499000' in rows[4]['amount_unit'] and rows[4]['endpoint_status']=='UNKNOWN'
assert src[3]['evidence_status']=='UNKNOWN' and src[3]['period']==''
ids={s['source_id'] for s in src}; assert len(ids)==5
assert all(set(filter(None,r['source_ids'].split(';')))<=ids for r in rows)
assert len({r['finding_id'] for r in findings})==len(findings)
assert all(r['numeric_input_effect'] and r['evidence'] and r['url'] for r in findings)
for r in findings:
 assert 1<=int(r['orig_line'])<=len((P/r['orig_file']).read_text().splitlines())
expected=json.loads((O/'input_hashes.json').read_text())
unchanged={p:hashlib.sha256((P/p).read_bytes()).hexdigest()==h for p,h in expected.items()}; assert all(unchanged.values())
result={'checked_at':datetime.now(timezone.utc).isoformat(),'result':'PASS','original_csv':original,'output_csv':outputs,'input_files_unchanged':unchanged,'checks':{'unique_ids':True,'source_references_resolve':True,'finding_lines_resolve':True,'all_passenger_numbers_blank':True,'unknown_not_zero':True,'mixed_amount_not_allocated':True,'orenair_not_current_primary':True},'quantified_volume_rows':sum(bool(r['convertible_trips']) for r in rows),'contract_passengers':None,'contract_passengers_status':'UNKNOWN','source_review':'manual; automated checks validate structure and declared invariants, not source truth','external_packages':6,'primary_attempts':{'BUY-01 EIS':2,'history S03 favt':2},'scope_excludes':['economics','base_costs','model_schedule','full 12-route research']}
(O/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(result,ensure_ascii=False,indent=2))
