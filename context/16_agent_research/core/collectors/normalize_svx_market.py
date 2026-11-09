#!/usr/bin/env python3
"""Selected numeric claims from two primary airport publications; no OD model."""
import csv
from html.parser import HTMLParser
import json
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
class Text(HTMLParser):
    def __init__(self):super().__init__();self.skip=0;self.parts=[]
    def handle_starttag(self,t,a):
        if t in {'script','style'}:self.skip+=1
    def handle_endtag(self,t):
        if t in {'script','style'}:self.skip=max(0,self.skip-1)
    def handle_data(self,d):
        if not self.skip:self.parts.append(d)
CLAIMS={
 'svx_2025_route_traffic':[
  ('ALL','8385','thousand passenger movements','около','8 миллионов 385 тысяч'),
  ('DOMESTIC','5.8','million passenger movements','порядка','5,8 миллиона'),
  ('INTERNATIONAL','2.6','million passenger movements','','2,6 миллиона'),
  ('MOW','2000','thousand route passengers','почти','почти 2 миллиона'),
  ('LED','700','thousand route passengers','около','около 700 тысяч'),
  ('AER','785','thousand route passengers','','785 тысяч'),
  ('MRV','211','thousand route passengers','','211 тысяч'),
  ('OVB','170','thousand route passengers','более','более 170 тысяч'),
 ],
 'svx_january_2025_route_traffic':[
  ('AER','49','thousand route passengers','превысил','49 тысяч'),
  ('MRV','16','thousand route passengers','порядка','порядка 16 тысяч'),
 ]}
def main():
    manifests=sorted(ROOT.glob('additional_market_*_manifest.json'));assert len(manifests)==1
    mf=manifests[0];d=json.loads(mf.read_text());rows=[]
    for e in d['datasets']:
        assert e['acquisition_status']=='ACQUIRED_RAW'
        p=Text();p.feed((ROOT/e['raw_path']).read_text());text=re.sub(r'\s+',' ',' '.join(p.parts))
        jan=e['dataset_id']=='svx_january_2025_route_traffic'
        date='2025-02-07' if jan else '2026-01-19'
        assert ('7 февраля 2025' if jan else '19 января 2026') in text
        e.update(publication_date=date,geographic_coverage='Ekaterinburg SVX; reported national/international market totals and named route markets',
            temporal_coverage='2025-01' if jan else '2025 calendar year',key_fields='publication;airport;destination market;period',
            units='Publisher rounded passengers; period/qualifier retained',grain='airport/route market × reporting period',
            acquisition_status='PARSED',value_status='OBSERVED',record_count=len(CLAIMS[e['dataset_id']]),record_count_unit='selected numeric claims; not complete page table')
        for dest,value,unit,qualifier,literal in CLAIMS[e['dataset_id']]:
            assert literal in text,literal
            rows.append(dict(source_dataset_id=e['dataset_id'],source_url=e['source_url'],raw_path=e['raw_path'],
                origin_airport_iata='SVX',destination_market_code=dest,destination_key_scope='Travel market; MOW is not a single airport',
                period_start='2025-01-01',period_end='2025-01-31' if jan else '2025-12-31',value=value,unit=unit,qualifier=qualifier,
                value_status='OBSERVED',published_at=date,retrieved_at_utc=e['retrieved_at_utc'],literal_evidence=literal,
                direction_scope='Both directions explicit in January article' if jan else 'Route reporting direction not explicitly defined; do not split without source clarification',
                limitations='Airport-published aggregate, not endpoint OD, unique persons, RW sales or available incremental share. Rounded qualifiers preserved; Jan does not forecast December.',
                decision_use='Segment-scale anchor and seasonal crosscheck for independent demand model validation'))
    mf.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
    with (ROOT/'normalized/svx_market_observation.csv').open('w',newline='') as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print('primary airport numeric claims',len(rows))
if __name__=='__main__':main()
