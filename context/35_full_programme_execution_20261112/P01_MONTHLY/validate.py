#!/usr/bin/env python3
from pathlib import Path
import csv,json,hashlib,datetime,re,subprocess
P=Path(__file__).resolve().parent;R=P/'sources_receipts';checks=[];errors=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(f):return list(csv.DictReader((P/f).open()))
def check(name,condition,detail=''):
 (checks if condition else errors).append({'check':name,'detail':detail})
# Pinned inputs and original line identity.
for x in json.loads((P/'input_manifest.json').read_text()):
 check('input_file_hash:'+x['saved_path'],sha(P/x['saved_path'])==x['sha256'])
 b=subprocess.check_output(['git','show',x['source_commit']+':'+x['source_path']])
 check('exact_git_source:'+x['source_path'],hashlib.sha256(b).hexdigest()==x.get('source_file_sha256',x['sha256']))
lines=(P/'inputs/BASE_known_flows.csv').read_text().splitlines()
kf=read('calibration_eligibility.csv')
for x in kf:
 n=int(x['source_row_id'].split(':')[-1]);check('known_flow_line_hash:'+x['observation_id'],hashlib.sha256(lines[n-1].encode()).hexdigest()==x['source_row_sha256'])
check('known_flow_rows_37',len(kf)==37)
check('OVB_no_annual_factor_applied',all(not x['annual_factor_applied'] and x['period_end']=='2025-06-30' for x in kf if x['from_iata']=='OVB'))
check('CEK_region_not_fitted_as_airport',next(x for x in kf if x['from_iata']=='CEK')['calibration_eligibility'].startswith('НЕТ'))
check('KUF_primary_upgrade',next(x for x in kf if x['from_iata']=='KUF')['source_status']=='PRIMARY_UPGRADE')
receipts={}
for f in R.glob('*_receipt.json'):
 r=json.loads(f.read_text());receipts[r['source_id']]=r
 if r['status']=='FETCHED':check('raw_receipt_hash:'+r['source_id'],sha(R/r['raw_file'])==r['sha256'])
# Every observation points to a downloaded primary or qualified secondary source, and exact hashes.
obsfiles=['airport_monthly.csv','airport_aggregate_observations.csv','carrier_monthly.csv','carrier_aggregate_observations.csv','airport_pair_segment_observations.csv','national_aviation_observations.csv']
for f in obsfiles:
 rs=read(f);check('unique_observation_ids:'+f,len(rs)==len(set(x['observation_id'] for x in rs)))
 for x in rs:
  check('period_bounds:'+x['observation_id'],x['period_start']<=x['period_end']<='2026-11-12')
  ks=x.get('source_ids',x.get('source_id')).split(';');hs=x.get('source_sha256','').split(';')
  check('source_binding:'+x['observation_id'],len(ks)==len(hs) and all(k in receipts and receipts[k].get('sha256')==h for k,h in zip(ks,hs)))
# Independent source-number matching: reports, not only export-vs-export arithmetic.
ut_year=read('carrier_aggregate_observations.csv');ut_month=read('carrier_monthly.csv')
for x in ut_year:
 if x['method']!='DIRECT_YTD':continue
 k=x['source_ids'];s=re.sub(r'\s','',(R/(k+'.txt')).read_text());check('UT_number_in_primary:'+x['observation_id'],str(x['value']) in s)
for x in ut_month:
 current=next(r for r in ut_year if r['carrier_id']==x['carrier_id'] and r['service_scope']==x['service_scope'] and r['period_end']==x['period_end'] and r['method']=='DIRECT_YTD')
 prior=next((r for r in ut_year if r['carrier_id']==x['carrier_id'] and r['service_scope']==x['service_scope'] and r['period_end']<x['period_end'] and r['period_end'][:7]==f'2025-{int(x["period_start"][5:7])-1:02d}' and r['method']=='DIRECT_YTD'),None)
 check('UT_adjacent_YTD_difference:'+x['observation_id'],int(x['value'])==int(current['value'])-(int(prior['value']) if prior else 0))
# KJA counts are explicit source numerals. No passenger residual converted to OD.
for x in read('airport_monthly.csv'):
 if x['airport_iata']=='KJA':
  s=re.sub(r'\s','',(R/(x['source_ids']+'.txt')).read_text());check('KJA_number_in_primary:'+x['observation_id'],str(x['value']) in s)
for x in read('airport_pair_segment_observations.csv'):
 k=x['source_id'];s=re.sub(r'\s','',(R/(k+'.txt')).read_text());n=int(x['value']);check('pair_number_in_primary:'+x['observation_id'],str(n) in s or n%1000==0 and (str(n//1000)+'тыс' in s.replace('.','')) or x['value_qualifier'].startswith('ROUND') and (format(n/1000,'g').replace('.',',')+'тыс' in s.replace('.','') or format(n/1000000,'g').replace('.',',')+'млн' in s))
for x in read('airport_pair_segment_observations.csv'):
 m=re.search(r'[.]txt:(\d+)',x['source_row_id']);k=x['source_id'];lines=(R/(k+'.txt')).read_text().splitlines();check('primary_pair_line_hash:'+x['observation_id'],bool(m) and hashlib.sha256(lines[int(m[1])-1].encode()).hexdigest()==x['source_row_sha256'])
for x in read('airport_monthly.csv'):
 if x['airport_iata']=='VVO' and x['method']=='DIRECT':
  s=re.sub(r'\s','',(R/(x['source_ids']+'.txt')).read_text());check('VVO_number_in_primary:'+x['observation_id'],format(int(x['value'])/1000,'g').replace('.',',')+'тыс' in s.replace('.',''))
check('Q1_pair_period_preserved',all(x['period_start']=='2025-01-01' and x['period_end']=='2025-03-31' for x in read('airport_pair_segment_observations.csv') if x['observation_id'].startswith('KJA2025-03-TOP')))
check('endpoint_header_no_zero_rows',len(read('endpoint_od_observations.csv'))==0)
coverage=read('airport_monthly_coverage.csv');check('coverage_grid_20x22',len(coverage)==440 and len(set(x['airport_iata'] for x in coverage))==20)
check('gaps_are_blank_not_zero',all(x['value']=='' and not x['observation_id'] for x in coverage if x['status']=='GAP_NOT_OBSERVED'))
check('KJA2025_12_months',sum(x['airport_iata']=='KJA' and x['service_scope']=='всего' and x['period_start'].startswith('2025') for x in read('airport_monthly.csv'))==12)
check('VVO_December_is_derived',all(x['method']=='DIFFERENCE_OF_ROUNDED_ADJACENT_YTD' for x in read('airport_monthly.csv') if x['airport_iata']=='VVO' and x['period_start']=='2025-12-01'))
check('VVO2026_Jan_total_lower_bound',next(x for x in read('airport_monthly.csv') if x['airport_iata']=='VVO' and x['service_scope']=='всего' and x['period_start']=='2026-01-01')['value_qualifier']=='GT')
# Intentional source disagreements remain visible; the export being valid is not data admission.
recon=read('reconciliation.csv');check('KJA_year_definition_gap_preserved',any(x['check_id']=='KJA-2025-components' and int(x['difference'])==55355 for x in recon));check('KJA_source_version_gap_preserved',any(x['check_id']=='KJA-2025-international-versions' and int(x['difference'])==16738 for x in recon))
result={'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'export_integrity':'PASS' if not errors else 'FAIL','checks_passed':len(checks),'errors':errors,'data_admission':'CONDITIONAL; endpoint OD не подтверждены; KJA определения и версии не согласованы','source_conflicts_are_not_export_failures':True,'coverage_not_completed':sum(x['status']=='GAP_NOT_OBSERVED' for x in coverage),'checks':checks}
(P/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='checks'},ensure_ascii=False));raise SystemExit(1 if errors else 0)
