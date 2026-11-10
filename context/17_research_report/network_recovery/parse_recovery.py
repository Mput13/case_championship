#!/usr/bin/env python3
"""Offline semantic extraction of the bounded recovery snapshot."""
from pathlib import Path
from html.parser import HTMLParser
from pypdf import PdfReader
from decimal import Decimal
import csv,io,json,re,hashlib,subprocess,collections
ROOT=Path(__file__).resolve().parent
class Node:
 def __init__(self,tag='',attrs=()):self.tag=tag;self.attrs=dict(attrs);self.children=[]
 def text(self):return ' '.join(x.text() if isinstance(x,Node) else x for x in self.children if not isinstance(x,Node) or x.tag not in ['script','style','noscript'])
 def all(self,tag=None,cls=None):
  out=[self] if (tag is None or self.tag==tag) and (cls is None or cls in self.attrs.get('class','').split()) else []
  for x in self.children:
   if isinstance(x,Node):out+=x.all(tag,cls)
  return out
class Dom(HTMLParser):
 def __init__(self):super().__init__();self.root=Node();self.stack=[self.root]
 def handle_starttag(self,t,a):
  n=Node(t,a);self.stack[-1].children.append(n)
  if t not in ['br','img','meta','link','input','hr','source','wbr','area','base','embed']:self.stack.append(n)
 def handle_endtag(self,t):
  for i in range(len(self.stack)-1,0,-1):
   if self.stack[i].tag==t:self.stack=self.stack[:i];break
 def handle_data(self,s):self.stack[-1].children.append(s)
def dom(i):
 d=Dom();d.feed((ROOT/'raw_hold'/f'{i}.bin').read_text(errors='replace'));return d.root
def norm(s):return re.sub(r'\s+',' ',s).strip()
def num(s):return Decimal(re.sub(r'\s','',s).replace(',','.'))
def receipt(i):return json.loads((ROOT/'receipts'/f'{i}.json').read_text())
def save(p,x):
 f=ROOT/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def csvwrite(p,rs):
 f=ROOT/p;f.parent.mkdir(parents=True,exist_ok=True)
 with f.open('w',newline='') as s:
  w=csv.DictWriter(s,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
def provenance(i):
 r=receipt(i);return dict(source_id=i,source_url=r['source_url'],source_sha256=r['sha256'],retrieved_at_utc=r['completed_at_utc'],value_status='OBSERVED',input_set='network-recovery-20261109-v1')
def main():
 facts=[]
 press=norm(dom('favt_2025_market').text())
 for metric,value,unit,literal in [
 ('carrier_passengers_total','108.85','million passenger segments','108,85 млн человек'),
 ('carrier_passengers_domestic','81.45','million passenger segments','81,45 млн пассажиров'),
 ('carrier_passengers_international','27.40','million passenger segments','27,40 млн человек'),
 ('carrier_passengers_non_CIS','17.72','million passenger segments','17,72 млн'),
 ('carrier_passengers_local','2.74','million passenger segments','2,74 млн'),
 ('airport_passenger_movements','214.66','million passenger movements','214,66 млн пассажиров'),
 ('carrier_passenger_km','284.43','billion passenger km','284,43'),
 ('seat_load_factor','89.5','percent','89,5%'),
 ('top5_carrier_passengers','76.57','million passenger segments','76,57 млн'),
 ('top5_carrier_share','70.3','percent of carrier traffic','70,3%')]:
  assert literal in press,(metric,literal)
  facts.append(dict(metric=metric,period_start='2025-01-01',period_end='2025-12-31',value=value,unit=unit,scope='Russia; airline total or airport movements as metric specifies',grain='national aggregate x metric x period',source_locator='Official news publication 2026-01-30 21:00; timezone not asserted',lineage='ROSAVIATSIA_ADMINISTRATIVE_REPORTING',limitation='Not unique people, endpoint OD, RW-specific sales or independent survey',**provenance('favt_2025_market')))
 pdf=PdfReader(ROOT/'raw_hold/mintrans_2025_transport_report.bin')
 assert len(pdf.pages)==45
 assert '2025' in pdf.pages[0].extract_text()
 for rn,metric,values in [('50','airport_passenger_movements',['216.42','214.66']),('57','carrier_passengers_total',['111.65','108.85']),('58','carrier_passengers_domestic',['84.68','81.45'])]:
  lines=pdf.pages[3].extract_text().splitlines();line=next(x for x in lines if x.startswith(rn+' '))
  for year,val in zip([2024,2025],values):
   assert val.replace('.',',') in line
   facts.append(dict(metric=metric,period_start=f'{year}-01-01',period_end=f'{year}-12-31',value=val,unit='million passenger movements' if rn=='50' else 'million passenger segments',scope='Russia; table2.1 original accounting',grain='national aggregate x metric x year',source_locator=f'PDF page4 table2.1 row{rn}; year headings page3 visually/table-text verified',lineage='MINTRANS_COMPILATION_OF_ADMINISTRATIVE_STATISTICS; not independent of Rosaviatsia',limitation='Rounded table; not OD; 2024 rounded differently from precise 12-GA source',**provenance('mintrans_2025_transport_report')))
 table=dom('favt_stats_current').all('table');assert len(table)==1
 trs=[[norm(c.text()) for c in tr.children if isinstance(c,Node) and c.tag in ['td','th']] for tr in table[0].all('tr')]
 assert len(trs)==69 and '27.01.2025' in ' '.join(trs[1])
 start=next(n for n,t in enumerate(trs) if t[0]=='ПЕРЕВОЗКИ ПАССАЖИРОВ');end=next(n for n,t in enumerate(trs) if t[0]=='ПЕРЕВОЗКИ ГРУЗОВ И ПОЧТЫ')
 selected=[('carrier_passengers_total',trs[start],'passenger segments'),('carrier_passengers_domestic',next(t for t in trs[start:end] if t[0]=='ВНУТРЕННИЕ ПЕРЕВОЗКИ'),'passenger segments'),('carrier_passengers_international',next(t for t in trs[start:end] if t[0]=='МЕЖДУНАРОДНЫЕ ПЕРЕВОЗКИ'),'passenger segments'),('seat_load_factor',next(t for t in trs if t[0]=='ПРОЦЕНТ ЗАНЯТОСТИ ПАССАЖИРСКИХ КРЕСЕЛ'),'percent'),('carrier_passenger_km',next(t for t in trs if t[0]=='ПАССАЖИРООБОРОТ'),'thousand passenger km')]
 for metric,t,unit in selected:
  for year,col in [(2023,2),(2024,3)]:
   facts.append(dict(metric=metric,period_start=f'{year}-01-01',period_end=f'{year}-12-31',value=str(num(t[col])),unit=unit,scope='All enterprises, regular and nonregular combined',grain='national aggregate x metric x year',source_locator=f'HTML single table label {t[0]}; columns 2023/2024 total; edition2025-01-27',lineage='ROSAVIATSIA_FORM12_GA',limitation='Historical2023–2024; neither2026 stats nor airport-by-month or OD',**provenance('favt_stats_current')))
 for year in [2023,2024]:
  f={x['metric']:Decimal(x['value']) for x in facts if x['source_id']=='favt_stats_current' and x['period_start']==f'{year}-01-01'}
  assert f['carrier_passengers_total']==f['carrier_passengers_domestic']+f['carrier_passengers_international']
 assert Decimal('81.45')+Decimal('27.40')==Decimal('108.85')
 csvwrite('parsed/national_market_observations.csv',facts)
 # Source rows selected for source-conditioned cost inputs; no full-basket arithmetic.
 costs=[]
 for i in ['khv_tariff_current','khv_tariff_202611']:
  p=PdfReader(ROOT/'raw_hold'/f'{i}.bin');text=p.pages[0].extract_text();foot=p.pages[-1].extract_text();assert len(p.pages)==7 and 'не включают НДС' in foot
  is_new=i.endswith('202611')
  specs=[('1.1.1','takeoff_landing','700.00' if is_new else '562.00','RUB per tonne MTOW','2026-02-10' if is_new else '2026-01-01','Russian consumers'),('1.2.1','transport_security','609.00' if is_new else '445.00','RUB per tonne MTOW','2026-02-10' if is_new else '2026-01-01','Russian consumers'),('1.1.1.1','conditional_takeoff_surcharge','40.00','percent of applicable takeoff charge','2026-01-01','Source days4/5 and0500–0700UTC; no universal surcharge'),('1.4.3','temporary_parking_40_60t_day','25224.00','RUB per day','2026-01-01','MTOW40–60t; overlap with other parking charges unresolved'),('1.5.3','temporary_parking_40_60t_hour','1051.00','RUB per hour','2026-01-01','Alternative parking basis, do not add daily and hourly prices'),('1.6.3','basing_40_60t_month','133477.00','RUB per month','2026-01-01','Published basing component, neither new-base total nor RW contract'),('2.1','passenger_stairs','9144.00' if is_new else '8700.00','RUB per stairs unit','2026-01-16' if is_new else '2026-01-01','Selected handling service only'),('2.2.1','passenger_bus_COBUS','4740.00' if is_new else '4510.00','RUB per vehicle unit','2026-01-16' if is_new else '2026-01-01','Selected handling service only')]
  for code,component,val,unit,date,condition in specs:
   lines=text.splitlines(); pos=next(n for n,x in enumerate(lines) if x.startswith(code+' ')); chunk=[lines[pos]]
   for more in lines[pos+1:]:
    if re.match(r'^\d+(?:[.]\d+)+ ',more):break
    chunk.append(more)
   line=' '.join(chunk)
   assert num(val)==num(re.search(r'(\d[\d ]*[,][\d]{2})',line).group(1)),(code,val,line)
   if is_new and date in ['2026-02-10','2026-01-16']:assert date[8:10]+'.'+date[5:7]+'.'+date[:4] in line
   costs.append(dict(airport='KHV',component_id=component,source_row=code,value=val,unit=unit,vat_basis='EXCLUDES_VAT; source page7',effective_from=date,effective_to='',date_basis='Explicit row date' if is_new and date!='2026-01-01' else 'Document general start date2026-01-01; unchanged row',conditions=condition,temporal_role='PUBLISHER_INDEX_LINKED_REVISION' if is_new else 'HISTORICAL_SUPERSEDED_AT_CAPTURE',scope='JSC Khabarovsky Airport; excludes separate terminal-company price list',grain='airport service x rate basis x effective date',source_locator='PDF page1; amount and row date visually verified; VAT note page7',limitation='Not contracted RW price; complete handling/fuel/basing basket and dispatch UNKNOWN',**provenance(i)))
 csvwrite('parsed/khv_cost_components.csv',costs)
 diffs=[]
 for a in costs[:8]:
  b=next(x for x in costs[8:] if x['component_id']==a['component_id'])
  diffs.append(dict(component_id=a['component_id'],old_rate=a['value'],new_rate=b['value'],difference=str(Decimal(b['value'])-Decimal(a['value'])),unit=a['unit'],vat_basis='EXCLUDES_VAT',value_status='DERIVED',limitation='Source revision difference, not measured RW cost change'))
 csvwrite('parsed/khv_revision_differences.csv',diffs)
 # Minimal factual samples; whole commercial/community directories remain held.
 tp=json.loads((ROOT/'raw_hold/travelpayouts_airlines.bin').read_text());assert isinstance(tp,list) and len(tp)==1178
 of=list(csv.reader(io.StringIO((ROOT/'raw_hold/openflights_airlines.bin').read_text())));assert len(of)==6162 and all(len(x)==8 for x in of)
 code_counts=collections.Counter(x['code'] for x in tp);samples=[]
 for code in ['WZ','RT','IO','A4','SU','U6']:
  for x in tp:
   if x['code']==code:samples.append(dict(code=code,name=x['name'],ICAO='',country='',source_active_flag='',scope='Directory sample; status of operations unverified',**provenance('travelpayouts_airlines')))
  for x in of:
   if x[3]==code and x[6]=='Russia':samples.append(dict(code=code,name=x[1],ICAO=x[4],country=x[6],source_active_flag=x[7],scope='Historical community active flag; not current certificate or operating identity',**provenance('openflights_airlines')))
 csvwrite('parsed/carrier_crosswalk_sample.csv',samples)
 # One restored Telegram result: exact main-body class, no reply substitution.
 blocks=dom('telegram_main_favt_ru_query_f06d7566f2b4').all(cls='tgme_widget_message');assert len(blocks)==1
 b=blocks[0];main=b.all(cls='js-message_text');assert len(main)==1;txt=norm(main[0].text());assert '70 , 55' in txt and 'январе-июне' in txt
 post=b.attrs['data-post'];posted=b.all('time')[0].attrs['datetime']
 tg=[]
 for metric,val,period,state in [('carrier_passengers_total','70.55','2026-01-01/2026-08-31','REPORTED_EIGHT_MONTHS'),('carrier_passengers_domestic','52.33','2026-01-01/2026-08-31','REPORTED_EIGHT_MONTHS'),('carrier_passengers_international','18.22','2026-01-01/2026-08-31','REPORTED_EIGHT_MONTHS'),('airport_passenger_movements','140.3','','HOLD_SOURCE_PERIOD_CONFLICT')]:
  tg.append(dict(metric=metric,value=val,unit='million passenger movements' if metric.startswith('airport') else 'million passenger segments',period=period,source_period_literal='январе-июне' if metric.startswith('airport') else 'за восемь месяцев',validation_status=state,post_id=post,published_at_utc=posted,grain='national reported aggregate; one selected post',lineage='Official Rosaviatsia Telegram; not independent of administrative series',limitation='Airport clause has source period ambiguity; no silent correction; not full archive or operational closure intervals',**provenance('telegram_main_favt_ru_query_f06d7566f2b4')))
 assert Decimal('52.33')+Decimal('18.22')==Decimal('70.55')
 csvwrite('parsed/telegram_selected_aggregate.csv',tg)
 # Generic success/content mismatch and supporting access checks.
 validations={}
 for f in sorted((ROOT/'receipts').glob('*.json')):
  r=json.loads(f.read_text());i=r['item_id']
  validations[i]=dict(status=('NOT_APPLICABLE' if r['status']=='NOT_APPLICABLE' else 'NOT_ACQUIRED') if r['status']!='FETCHED' else 'CONTENT_CHECK_PENDING',http_status=r.get('http_status'),format='',temporal_coverage='',grain='',units='',parsed_rows=0,scope='')
 for i in ['favt_2025_market','favt_stats_current','mintrans_2025_transport_report']:
  rr=[x for x in facts if x['source_id']==i];validations[i].update(status='VERIFIED_SCOPED',format='PDF45pages' if i.startswith('mintrans') else 'HTML',temporal_coverage='2024–2025' if i.startswith('mintrans') else '2023–2024' if i=='favt_stats_current' else '2025',grain='country x metric x period',units='Explicit per row; airport movements and carrier segments separate',parsed_rows=len(rr),scope='National context/denominators; not OD')
 for i in ['khv_tariff_current','khv_tariff_202611']:
  validations[i].update(status='VERIFIED_SCOPED_HISTORICAL' if i=='khv_tariff_current' else 'VERIFIED_SCOPED',format='PDF7pages',temporal_coverage='2026; component effective dates explicit',grain='KHV service x price basis',units='RUB/MTOWtonne; RUB/day; RUB/hour; RUB/month; percent',parsed_rows=8,scope='Selected public rates; not complete costs or contract')
 validations['travelpayouts_airlines'].update(status='VERIFIED_SCOPED',format='JSON list1178',temporal_coverage='Mutable retrieval snapshot; operating dates UNKNOWN',grain='airline code entry',units='codes/names',parsed_rows=sum(x['source_id']=='travelpayouts_airlines' for x in samples),scope='Crosswalk sample; whole1178 parsed structurally; no operating proof')
 validations['openflights_airlines'].update(status='VERIFIED_SCOPED',format='CSV6162rows/8fields',temporal_coverage='Historical/mutable community snapshot',grain='airline directory entry',units='codes/names/source-active flag',parsed_rows=sum(x['source_id']=='openflights_airlines' for x in samples),scope='238sourceRussia rows, six-code factual sample only; no operations proof')
 validations['openflights_license'].update(status='VERIFIED_SOFTWARE_LICENSE_ONLY',format='Plain text AGPLv3',temporal_coverage='Licensev3',grain='Software licence document',units='N/A',scope='AGPL text is not by itself a data-specific licence for airline directory')
 validations['favt_airport_open_data'].update(status='CONTENT_MISMATCH',format='HTML generic open-data catalogue',temporal_coverage='Not established for requested airport statistics',grain='catalogue',units='N/A',scope='No requested airport passenger dataset; HTTP200 not restoration')
 validations['telegram_main_favt_ru_query_f06d7566f2b4'].update(status='VERIFIED_PARTIAL_WITH_HOLD',format='Telegram HTML exact main-body selected',temporal_coverage='2026eightmonths; airport-period clause ambiguous',grain='one official post',units='million passenger segments/movements kept separate',parsed_rows=4,scope='3carrier facts; airport figure held for period conflict; no archive reparse')
 validations['uvt_current'].update(status='VERIFIED_SUPPORTING_CONTENT',format='HTML36tables',temporal_coverage='Mixed rules including winter2026 dates',grain='published schedule rule',units='local source clocks; no new UTC derivation',scope='Actual route/date/flight rows; already available via same replacement in pinned package')
 aztext=norm(dom('azimuth_current').text());assert 'Расписание' in aztext or 'Рейсы' in aztext or 'Прибыл' in aztext
 validations['azimuth_current'].update(status='VERIFIED_SUPPORTING_CONTENT',format='HTML carrier board',temporal_coverage='Board retrieval snapshot; not target December fare',grain='displayed flight/status',units='Source display times',scope='Content availability; no price or availability result')
 validations['case_brief'].update(status='VERIFIED_SUPPORTING_CONTENT',format='HTML title and case8tables',temporal_coverage='Live task at retrieval',grain='task page',units='N/A',scope='Same sha as pinned core; not a new requirement set')
 assert '32 набора' in norm(dom('tourism_R04').text())
 validations['tourism_R04'].update(status='VERIFIED_SUPPORTING_CONTENT',format='HTML CKAN search32results',temporal_coverage='Mutable discovery page',grain='dataset catalogue search',units='N/A',scope='Not Anubis challenge; access to catalogue restored; original dataGrid statistics already acquired')
 index=dom('khv_tariff_index');links=[x.attrs.get('href','') for x in index.all('a')];assert '/partners/open-info-khabaero/law/fee/prices/tarif_2026_11.pdf' in links
 validations['khv_tariff_index'].update(status='VERIFIED_SUPPORTING_CONTENT',format='Publisher index HTML',temporal_coverage='Retrieval2026-11-09; links amended2026rate file',grain='official index link',units='N/A',scope='Establishes file lineage, not signed agreement')
 passport=norm(dom('airfield_registry_passport').text());assert '01.02.2025' in passport and '20.06.2024' in passport
 validations['airfield_registry_passport'].update(status='VERIFIED_SUPPORTING_CONTENT_WITH_LIMIT',format='Official dataset passport HTML',temporal_coverage='Metadata actuality2024-06-20, lists version2025-02-01',grain='data passport',units='N/A',scope='Latest listed DOCX returns404; current certificate table not restored')
 for i,v in validations.items():
  r=receipt(i)
  if r['status']=='FETCHED':assert v['status']!='CONTENT_CHECK_PENDING',i
  v.update(source_id=i,source_url=r['source_url'],source_sha256=r.get('sha256'),retrieved_at_utc=r['completed_at_utc'])
 save('semantic_validation.json',validations)
 csvwrite('parsed/coverage.csv',list(validations.values()))
 save('parsed/schema.json',{'schema_version':'recovery-extract-v1','null_policy':'Empty field is UNKNOWN/NOT_APPLICABLE with row limitation; never zero imputation','tables':{'national_market_observations.csv':{'key':['source_id','metric','period_start','period_end'],'grain':'national aggregate x metric x period','rows':len(facts)},'khv_cost_components.csv':{'key':['source_id','component_id'],'grain':'source revision x airport rate component','rows':len(costs)},'khv_revision_differences.csv':{'key':['component_id'],'grain':'same component old/new published rate; no real-cost attribution','rows':len(diffs)},'carrier_crosswalk_sample.csv':{'key':['source_id','code','name'],'grain':'six target codes x source entry; sample only','rows':len(samples)},'telegram_selected_aggregate.csv':{'key':['post_id','metric'],'grain':'selected post claim, not event','rows':len(tg)}}})
 save('parsed/validation_checks.json',{'checks':{'rosaviatsia2023and2024_total_equals_domestic_plus_international':'PASS','rosaviatsia2025_81.45plus27.40equals108.85':'PASS','telegram2026_52.33plus18.22equals70.55':'PASS','PDFs_validated_page_counts_and_selected_rows':'PASS','current_KHV_file_linked_by_publisher_index':'PASS','KHV700and609_effective2026_02_10_verified_visual_and_text':'PASS','every_HTTP200_has_semantic_result':'PASS'},'limits':'Author source extraction and arithmetic checks only; not independent model review or live commercial acceptance'})
 print('parsed',len(facts),'national',len(costs),'cost',len(samples),'carrier_sample',len(tg),'telegram')
if __name__=='__main__':main()
