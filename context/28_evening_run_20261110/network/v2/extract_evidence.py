#!/usr/bin/env python3
"""Extract addressed official schedule rows from saved sources, never UI automation."""
from html.parser import HTMLParser
import json
import re
import calculate as c


class Tables(HTMLParser):
    def __init__(self):
        super().__init__();self.rows=[];self.row=None;self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='tr':self.row=[]
        if tag in ['td','th'] and self.row is not None:self.cell=[]
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ['td','th'] and self.cell is not None:
            self.row.append(' '.join(' '.join(self.cell).split()));self.cell=None
        if tag=='tr' and self.row is not None:
            self.rows.append(self.row);self.row=None


def main():
    manifests={r['source_id']:r for r in json.loads((c.SOURCE_ROOT/'public_sources_manifest.json').read_text())}
    wanted={'kuf_dep':['WZ-1034','A4-4047','A4-6308'],
            'kuf_arr':['WZ-1033','A4-4048','A4-6307'],
            'svx_dep':['WZ-5071','WZ-1033','WZ-5049','FV-6792','FV-6800'],
            'svx_arr':['WZ-5072','WZ-1034','FV-6791','FV-6799']}
    extracted=[]
    for src,flights in wanted.items():
        parser=Tables();parser.feed((c.SOURCE_ROOT/manifests[src]['local']).read_text())
        for no,row in enumerate(parser.rows,1):
            if not any(x in row for x in flights):continue
            extracted.append(dict(source_id=src,source_table_row=no,source_url=manifests[src]['url'],
                                  source_sha256=manifests[src]['sha256'],row=' | '.join(row),
                                  state='PUBLISHED_OFFER_NOT_FLOWN; configuration/fare/sales UNKNOWN'))
    text=(c.SOURCE_ROOT/'inputs/public_20261110/oms_winter.txt').read_text()
    for line_no,line in enumerate(text.splitlines(),1):
        if re.search(r'5071/5072|6845/\s*6846',line):
            extracted.append(dict(source_id='oms_winter',source_table_row='pdftotext-layout line'+str(line_no),
                                  source_url=manifests['oms_winter']['url'],source_sha256=manifests['oms_winter']['sha256'],
                                  row=' '.join(line.split()),state='PUBLISHED_OFFER_NOT_FLOWN; days refer OMS column'))
    c.write('primary_service_rows.csv',extracted)
    coverage=[]
    markets=[('C01','NJC','UFA','Utair UT151/152, pinned RPC029/055; current UFA pages captured'),
             ('C01','UFA','MRV','Azimut A46022/6122/6021/6121, pinned RPC026/027/053/054; current page captured'),
             ('C01','NJC','MRV','author direct=True; matched winter direct primary row NOT_OBTAINED; summer/aggregator not substituted'),
             ('C03','KUF','NJC','Azimut A44047/4048 Dec9/12, primary KUF rows'),
             ('C03','KUF','MRV','Azimut A46308/6307 Tue/Wed/Sat, primary KUF rows'),
             ('C03','KUF','ARH','no row in inspected primary snapshot; connection alternatives through SVO/LED not dated/quoted here'),
             ('C03','KUF','OMS','no row in inspected primary snapshot; existing RW via SVX is concrete C33 alternative'),
             ('C04/C07','OMS','KJA','Rossiya FV6845/6846 Mon/Sat at OMS; actual125/145min clocks, SSJ100 configuration UNKNOWN'),
             ('C07/C33','SVX','OMS','RW WZ5071/5072 Tue/Fri outbound, Wed/Sat inbound; primary rows match'),
             ('C07','SVX','KJA','Rossiya FV6791/6792 six days plus FV6799/6800 Tue in pinned cards; primary rows saved'),
             ('C33','KUF','SVX','RW WZ1033/1034; Utair UT281/282 in pinned cards. KUF inbound5min clock disagreement retained'),
            ]
    for h,a,b,note in markets:
        coverage.append(dict(hypothesis=h,origin=a,destination=b,coverage=note,
                             matched_final_20kg_fare='NOT_OBTAINED',seats='100 only our scenario; other exact configurations UNKNOWN',
                             applicability='2026/27 source window only; no automatic2027/28 continuation'))
    for x in ['GOJ','NOZ','GSV','UFA','TOF','VOG']:
        coverage.append(dict(hypothesis='C04',origin='OMS',destination=x,
                             coverage='author demand/direct flag supplied; complete dated winter competitor market NOT_OBTAINED',
                             matched_final_20kg_fare='NOT_OBTAINED',seats='UNKNOWN competitor configuration',
                             applicability='cannot infer competitor absence from missing card'))
    c.write('competition_coverage.csv',coverage)
    print('extracted',len(extracted),'addressed primary rows;',len(coverage),'market coverage records')


if __name__=='__main__':
    main()
