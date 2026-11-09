#!/usr/bin/env python3
"""Independent scoped review of a frozen core worktree, without running its code."""
import argparse
import collections
import csv
import datetime as dt
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import subprocess
from zoneinfo import ZoneInfo

BASE=Path(__file__).resolve().parent
CORE_SHA='a875cdd1ecaf778f53ba06cab1c66581a7f215c6'
DEFAULT='/Users/a/.t3/worktrees/case_championship/research-case5-raw-core-20261109/context/16_agent_research/core'
SAFE={'content-type','content-length','last-modified','etag','date','cache-control','content-encoding','expires','accept-ranges'}
VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}

class Text(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,t,a):
        if t in {'script','style'}:self.skip+=1
    def handle_endtag(self,t):
        if t in {'script','style'}:self.skip=max(0,self.skip-1)
    def handle_data(self,d):
        if not self.skip:self.parts.append(d)

class MainText(HTMLParser):
    def __init__(self):super().__init__();self.stack=[];self.out=collections.defaultdict(list)
    def handle_starttag(self,t,a):
        a=dict(a);post,main=self.stack[-1][1:] if self.stack else ('',False)
        post=a.get('data-post',post);main=main or 'js-message_text' in a.get('class','').split()
        if main and post and t=='br':self.out[post].append('\n')
        if t not in VOID:self.stack.append((t,post,main))
    def handle_endtag(self,t):
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==t:self.stack=self.stack[:i];break
    def handle_data(self,d):
        if self.stack and self.stack[-1][2]:self.out[self.stack[-1][1]].append(d)

class FirstTable(HTMLParser):
    def __init__(self):super().__init__();self.level=0;self.done=False;self.rows=[];self.row=None;self.cell=None
    def handle_starttag(self,t,a):
        if t=='table' and not self.done:self.level+=1
        if self.level!=1:return
        if t=='tr':self.row=[]
        if t in {'td','th'} and self.row is not None:self.cell=[dict(a),[]]
    def handle_data(self,d):
        if self.level==1 and self.cell is not None:self.cell[1].append(d)
    def handle_endtag(self,t):
        if self.level==1 and t in {'td','th'} and self.cell is not None:
            self.row.append((self.cell[0],re.sub(r'\s+',' ',' '.join(self.cell[1])).strip()));self.cell=None
        if self.level==1 and t=='tr' and self.row is not None:self.rows.append(self.row);self.row=None
        if t=='table' and self.level:
            self.level-=1
            if not self.level:self.done=True
    def expanded(self):
        spans={};out=[]
        for rownum,cells in enumerate(self.rows,1):
            values={col:v for col,(remaining,v) in spans.items()}
            spans={col:(remaining-1,v) for col,(remaining,v) in spans.items() if remaining>1}
            col=0
            for attrs,value in cells:
                while col in values:col+=1
                width=int(attrs.get('colspan',1));height=int(attrs.get('rowspan',1))
                for dx in range(width):
                    values[col+dx]=value if dx==0 else ''
                    if height>1:spans[col+dx]=(height-1,values[col+dx])
                col+=width
            out.append((rownum,[values.get(i,'') for i in range(max(values,default=-1)+1)]))
        return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',default=DEFAULT);ap.add_argument('--refresh',action='store_true');args=ap.parse_args()
    source=Path(args.source_root);raw=BASE/'raw/snapshot';raw.mkdir(parents=True,exist_ok=True);inputs=[]
    def load(name):
        dest=raw/name
        if args.refresh or not dest.exists():
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((source/name).read_bytes())
        data=dest.read_bytes();receipt={'source_relative_path':name,'local_path':str(dest.relative_to(BASE)),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
        git=subprocess.run(['git','show',CORE_SHA+':context/16_agent_research/core/'+name],cwd=BASE,capture_output=True)
        if git.returncode==0:
            receipt['pinned_git_sha256']=hashlib.sha256(git.stdout).hexdigest();receipt['matches_pinned_git_blob']=receipt['sha256']==receipt['pinned_git_sha256'];assert receipt['matches_pinned_git_blob'],name
            receipt['provenance_kind']='PINNED_GIT_MATCH'
        else:receipt['provenance_kind']='EXTERNAL_IGNORED_RAW_OR_ARCHIVE'
        inputs.append(receipt)
        return data
    def rows(name):return list(csv.DictReader(io.StringIO(load(name).decode('utf-8-sig'))))
    manifest=load('dataset_manifest.json');m=json.loads(manifest)
    # No HTTP header values are propagated into the public receipt.
    assert not any(k.lower() in {'cookie','set-cookie','authorization'} for d in m['datasets'] for k in (d.get('headers') or d.get('response_headers') or {}))
    market=rows('normalized/market_observation.csv');svx=rows('normalized/svx_market_observation.csv')
    duplicate_ids={k:v for k,v in collections.Counter(r['observation_id'] for r in market).items() if v>1}
    duplicates=[{'csv_row':i+2,**{k:r[k]for k in ['observation_id','entity_id','metric','period_start','period_end','value','unit','observation_kind']}}for i,r in enumerate(market)if r['observation_id']in duplicate_ids]
    texts={}
    for name in sorted({r['raw_path'] for r in market}):
        parser=MainText();parser.feed(load(name).decode());texts.update({k:''.join(v)for k,v in parser.out.items()})
    literal_errors=[r['source_id'] for r in market if r['literal_value']not in texts.get('favt_ru/'+r['source_id'].split(':')[1],'')]
    svx_errors=[]
    for name in sorted({r['raw_path']for r in svx}):
        parser=Text();parser.feed(load(name).decode());s=re.sub(r'\s+',' ',' '.join(parser.parts))
        svx_errors.extend(r['source_dataset_id']+':'+r['destination_market_code']for r in svx if r['raw_path']==name and r['literal_evidence']not in s)
    op='branches/operating_evidence/'
    subsidy=rows(op+'normalized/favt_subsidy_2026_full.csv');parser=FirstTable();parser.feed(load(op+'raw/favt_regional_2026.html').decode());grid=dict(parser.expanded());fields=['route_number_raw','carrier_raw','origin_airport_name_raw','destination_airport_name_raw','distance_oneway_km_raw','aircraft_type_raw','seats_raw','period_raw','frequency_per_week_raw','paired_flights_2026_raw','note_raw']
    subsidy_errors=[{'source_row':r['source_row']}for r in subsidy if grid[int(r['source_row'])]!=[r[k]for k in fields]]
    rules=rows(op+'normalized/omsk_domestic_timetable_rows.csv');instances=rows(op+'normalized/omsk_outbound_week_20261207.csv');freq=rows(op+'normalized/omsk_outbound_frequency_20261207.csv')
    pdf=load(op+'raw/omsk_winter_20261105.pdf');pdfpath=raw/op/'raw/omsk_winter_20261105.pdf'
    text=subprocess.check_output(['pdftotext','-layout',str(pdfpath),'-']).decode().split('МЕЖДУНАРОДНЫЕ РЕЙСЫ')[0];lines=text.splitlines()
    cols=['aircraft_type_raw','flight_numbers_raw','preceding_origin_departure_local_raw','routing_raw','omsk_arrival_local_raw','omsk_departure_local_raw','weekdays_raw','period_raw','carrier_raw','onward_arrival_local_raw']
    pdf_errors=[r['source_text_line']for r in rules if re.split(r'\s{2,}',lines[int(r['source_text_line'])-1].strip())!=[r[k]for k in cols]]
    expected=[]
    for r in rules:
        dates=re.findall(r'\d{2}\.\d{2}\.\d{2}(?:\d{2})?',r['period_raw']);parse=lambda x:dt.datetime.strptime(x,'%d.%m.%Y'if len(x)==10 else '%d.%m.%y').date()
        start,end=parse(dates[0]),parse(dates[-1]);weekdays=set(range(1,8))if r['weekdays_raw']=='ежедневно'else set(map(int,re.findall('[1-7]',r['weekdays_raw'])))
        route=re.split(' – | - ',r['routing_raw']);i=route.index('Омск')
        if i+1==len(route):continue
        for day in range(7):
            date=dt.date(2026,12,7)+dt.timedelta(days=day)
            if start<=date<=end and date.isoweekday() in weekdays:expected.append((r['source_text_line'],date.isoformat(),r['omsk_departure_local_raw'].replace('.',':'),route[i+1]))
    actual=[(r['source_text_line'],r['departure_date_local'],r['departure_local'][11:16],r['next_airport_name'])for r in instances]
    utc_errors=[i+2 for i,r in enumerate(instances)if dt.datetime.fromisoformat(r['departure_local']).astimezone(ZoneInfo('UTC')).isoformat()!=r['departure_utc']]
    actual_freq=collections.Counter((r['carrier_raw'],r['destination_airport_iata'])for r in instances);freq_errors=[i+2 for i,r in enumerate(freq)if actual_freq[(r['carrier_raw'],r['destination_airport_iata'])]!=int(r['published_departures'])]
    airports=rows('normalized/airport_version.csv');keys=rows(op+'raw/parent_canonical_keys_snapshot.csv')
    tob=[{'csv_row':i+2,**r}for i,r in enumerate(instances)if r['next_airport_name']=='Тобольск']
    for name in ['collectors/extract_market.py',op+'collectors/supplement.py',op+'collectors/normalize.py']:load(name)
    result={'generated_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'source_root':str(source),'manifest_created_at_utc':m['created_at_utc'],'manifest_sha256':hashlib.sha256(manifest).hexdigest(),'execution':'Own stdlib parser/calendar only; colleague models not executed',
      'market':{'rows':len(market),'unique_observation_ids':len(set(r['observation_id']for r in market)),'duplicate_identity_rows':duplicates,'unique_full_grain':len({tuple(r[k]for k in ['source_id','entity_id','metric','period_start','period_end','unit','observation_kind'])for r in market}),'primary_main_body_literal_errors':literal_errors,'source_posts':len({r['source_id']for r in market}),'plan_or_allocation_rows':sum(r['observation_kind']!='REPORTED_OUTTURN'for r in market)},
      'svx':{'rows':len(svx),'primary_literal_errors':svx_errors,'MOW_group_preserved':all('not a single airport'in r['destination_key_scope']for r in svx if r['destination_market_code']=='MOW'),'annual_direction_unknown_preserved':all('not explicitly defined'in r['direction_scope']for r in svx if r['period_end']=='2025-12-31'),'jan_both_directions_preserved':all('Both directions explicit'in r['direction_scope']for r in svx if r['period_end']=='2025-01-31')},
      'subsidy':{'rows':len(subsidy),'independent_primary_table_data_rows':len(grid)-1,'all11cells_mismatch_rows':subsidy_errors,'actual_flights_and_cash_blank':all(r['actual_operated_flights']==r['subsidy_award_RUB']==r['subsidy_paid_RUB']==''for r in subsidy),'programme_kind_preserved':all(r['observation_kind']=='OBSERVED_PROGRAMME_PLAN'for r in subsidy)},
      'omsk':{'rules':len(rules),'pdf_text_rule_mismatches':pdf_errors,'instances':len(instances),'expected_calendar_instances':len(expected),'calendar_multiset_equal':collections.Counter(expected)==collections.Counter(actual),'utc_errors':utc_errors,'frequency_errors':freq_errors,'frequency_groups':len(freq),'tobolsk_join_rows':tob,'tobolsk_airport_alternatives':[{k:r[k]for k in ['airport_id','ident','iata_code','name','scheduled_service','travel_city_code','latitude_deg','longitude_deg']}for r in airports if r['iata_code']in {'TOX','RMZ'}],'frozen_key_alternatives':[{k:r[k]for k in ['canonical_id','name','iata','icao_or_ident','relation']}for r in keys if r['entity_type']=='airport'and r['iata']in {'TOX','RMZ'}]},
      'acceptance':'Scoped source-claim and calendar reconciliation only; no independent endpoint OD, paid yield, executed programme, free capacity or strategy forecast accepted'}
    (BASE/'input_manifest.json').write_text(json.dumps({'captured_at_utc':result['generated_at_utc'],'core_git_sha':CORE_SHA,'snapshot_policy':'First run freezes working files. Eleven tracked inputs match pinned core Git SHA; ten raw archives are external content-hashed files. --refresh is a new snapshot and must be separately archived. Raw input redistribution not licensed here.','files':inputs},ensure_ascii=False,indent=2)+'\n')
    (BASE/'reproduction.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k not in {'omsk'}}|{'omsk':{k:v for k,v in result['omsk'].items()if k not in {'tobolsk_join_rows','tobolsk_airport_alternatives','frozen_key_alternatives'}}},ensure_ascii=False))

if __name__=='__main__':main()
