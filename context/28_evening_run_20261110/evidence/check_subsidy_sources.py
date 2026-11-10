#!/usr/bin/env python3
"""Compare distinct official captures after an explicit, narrow normalization."""
import csv,json,pathlib,collections,re,hashlib
import pandas as pd
R=pathlib.Path(__file__).resolve().parent
cols=['route_no','airline','origin_city','destination_city','km','aircraft','seats','period','flights_per_week','round_trips_2026','cofinancing_note']
p=R/'raw/web/favt_xlsx_mainhost/source.xlsx'
x=pd.read_excel(p,header=None,dtype=str,keep_default_na=False)
rows=[];num=''
for i,vals in enumerate(x.values.tolist()[2:],3):
 d=dict(zip(cols,vals));num=d['route_no'] or num;d['route_no']=num;d['xlsx_row']=i
 d['source_id']='favt_xlsx_mainhost';d['raw_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();rows.append(d)
with (R/'extracts/favt_xlsx_regional_2026.csv').open('w',newline='') as f:w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
h=list(csv.DictReader(open(R/'extracts/favt_regional_2026_full.csv')))
def norm(s,k):
 s=str(s).replace('\\n',' ').replace('\n',' ').replace('\xa0',' ')
 if k in ('km','seats','flights_per_week','round_trips_2026'):
  s=s.replace(' ','').replace(',','.')
  try:return str(float(s))
  except ValueError:return s
 return re.sub(r'\s+','',s)
fields=cols # no removal of route/operator/period/quantity differences
hc=collections.Counter(tuple(norm(r[k],k) for k in fields) for r in h)
xc=collections.Counter(tuple(norm(r[k],k) for k in fields) for r in rows)
diff=[]
for side,c in [('HTML_ONLY',hc-xc),('XLSX_ONLY',xc-hc)]:
 for vals,n in c.items():diff.append(dict(side=side,count=n,**dict(zip(fields,vals))))
with (R/'subsidy_html_xlsx_differences.csv').open('w',newline='') as f:w=csv.DictWriter(f,['side','count']+cols);w.writeheader();w.writerows(diff)
old=list(csv.DictReader(open(R/'raw/git/4a976356/data/raw/favt_subsidy_2026.csv')))
changed=[]
for row in csv.DictReader(open(R/'subsidy_route_matches.csv')):
 matches=[o for o in old if o['airline']==row['airline'] and o['origin']==row['origin_city'] and o['destination']==row['destination_city'] and norm(o['period'],'period')==norm(row['period'],'period')]
 old_values=sorted({(o['flights_per_week'],o['round_trips_2026']) for o in matches})
 if not matches or (row['flights_per_week'],row['round_trips_2026']) not in old_values:
  changed.append(dict(route=row['route'],airline=row['airline'],period=row['period'],prior_csv_matching_rows=len(matches),prior_frequency_roundtrips=json.dumps(old_values,ensure_ascii=False),current_frequency=row['flights_per_week'],current_round_trips=row['round_trips_2026'],current_html_row=row['html_table_row'],classification='VERSION_DIFFERENCE_NOT_RETROSPECTIVE_ERROR; multirow matching is not an award join'))
with (R/'subsidy_prior_current_differences.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,list(changed[0]));w.writeheader();w.writerows(changed)
checks=dict(official_html_rows=len(h),official_xlsx_rows=len(rows),normalized_row_multiset_equal=hc==xc,difference_rows=len(diff),normalization='whitespace and literal backslash-n removed; numeric spaces/decimal comma normalized; all11fields retained',old_owner_csv_rows=len(old),old_owner_csv_sha256=hashlib.sha256((R/'raw/git/4a976356/data/raw/favt_subsidy_2026.csv').read_bytes()).hexdigest(),interpretation='Same11field rows after stated normalization establishes these two captures match; not PDFfcdd4 identity, contract, execution, award or future rights.')
(R/'subsidy_source_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n');print(json.dumps(checks,ensure_ascii=False,indent=2))
