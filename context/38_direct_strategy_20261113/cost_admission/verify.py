#!/usr/bin/env python3
"""Offline admission checks; writes only validation.json in this package."""
from pathlib import Path
import csv,json,hashlib,subprocess,decimal
O=Path(__file__).resolve().parent;R=O.parents[2];checks={};errors=[]
def check(k,condition,detail=None):
 checks[k]={'pass':bool(condition),'detail':detail}
 if not condition:errors.append(k)
tables={}
for p in sorted(O.glob('*.csv')):
 with p.open(encoding='utf-8',newline='') as f:raw=list(csv.reader(f))
 check(p.name+'_width',bool(raw) and len(raw[0])==len(set(raw[0])) and all(len(r)==len(raw[0]) for r in raw[1:]),{'rows':len(raw)-1,'columns':len(raw[0])})
 tables[p.name]=list(csv.DictReader(p.open(encoding='utf-8',newline='')))
sources={r['source_id']:r for r in tables['sources.csv']}
check('unique_source_ids',len(sources)==len(tables['sources.csv']))
check('source_references',all(r['source_id'] in sources for name,rs in tables.items() if name!='sources.csv' for r in rs))
check('source_response_files',all(not s['response_file'] or (O/s['response_file']).is_file() for s in sources.values()))
# exact_requests mutable while assembling, hash exempt; source bytes otherwise immutable
check('source_hashes',all(s['sha256']=='UNKNOWN' or hashlib.sha256((O/s['response_file']).read_bytes()).hexdigest()==s['sha256'] for s in sources.values()))
costs=tables['canonical_cost_items.csv'];ids={r['item_id']:r for r in costs}
check('unique_cost_ids',len(ids)==len(costs))
check('amount_units_status_coverage',all(r['unit'] and r['tax_basis'] and r['status'] and r['sourcecoverage'] and r['whatmodelchanges'] and (r['amount']=='UNKNOWN' or decimal.Decimal(r['amount']).is_finite()) for r in costs))
check('unknown_not_zero',all(r['amount']=='UNKNOWN' and r['model_value']=='UNKNOWN' for r in costs if r['status']=='UNKNOWN'))
check('no_public_numeric_overwrite',all(r['model_value']=='UNKNOWN' for r in costs if r['status']!='SCENARIO'))
check('scenario_preserved',all(ids[k]['amount']==v and ids[k]['status']=='SCENARIO' for k,v in {'FUEL-BASE':'137996','FUEL-CAUT':'161696','GROUND-BASE':'96089','GROUND-CAUT':'115307'}.items()))
public=[r for r in costs if r['source_id'] in ['SVX-T','SVX-H']]
over=tables['ground_overlap.csv'];check('tax_overlap_coverage',set(r['item_id'] for r in public)==set(r['item_id'] for r in over) and all(r['auto_add']=='NO' and r['included_in_existing']=='UNKNOWN' for r in over) and all(r['tax_basis']=='EX_VAT' if r['amount']!='UNKNOWN' else r['tax_basis']=='UNKNOWN' for r in public))
check('special_gpu_period_and_minimum',ids['SVX-GPU-OFFER']['effective_period']=='2026-09-16..2027-08-10 inclusive' and '30' in ids['SVX-GPU-OFFER']['conditions'] and 'Written' in ids['SVX-GPU-OFFER']['conditions'])
check('billing_formula_examples',270*max(30,10)==8100 and 537*24==12888 and 21120*max(4,2)==84480)
check('hangar_not_RRJ_quote',ids['SVX-HANGAR-ANALOG']['status']=='PUBLIC_ANALOG_NOT_RRJ_QUOTE' and ids['SVX-HANGAR-ANALOG']['model_value']=='UNKNOWN')
check('mro_5airports_2types',len(tables['mro_gates.csv'])==10 and {(r['airport'],r['aircraft']) for r in tables['mro_gates.csv']}=={(a,t) for a in ['SVX','KJA','AER','MRV','GOJ'] for t in ['RRJ95B/LR','SJ100_PD8']})
check('pd8_and_free_capacity_unknown',all(r['free_capacity']=='UNKNOWN' and r['price']=='UNKNOWN' and (r['aircraft']!='SJ100_PD8' or r['status']=='UNKNOWN') for r in tables['mro_gates.csv']))
check('fixed_costs_not_avoidable',all(r['avoidable']=='NO' for r in tables['reserve_launch_costs.csv'] if r['cost_id'] in ['FIXED-CREW','EXISTING-LEASE']))
check('commercial_MAIN0',all(r['main_incremental_revenue']=='0' and r['status']=='MAIN0_OPTION_ONLY' for r in tables['commercial_options.csv']))
check('no_new_support_credit',all(r['main_model_credit']=='NONE_NEW' for r in tables['support_conditions.csv']))
check('numeric_model_admission_zero',sum(int(r['numeric_model_updates']) for r in tables['source_admission.csv'])==0)
before=json.loads((O/'excerpts/preservation_before.json').read_text());changed=[f for f,h in before.items() if not (R/f).is_file() or hashlib.sha256((R/f).read_bytes()).hexdigest()!=h]
check('preservation1621',len(before)==1621 and not changed,{'count':len(before),'changed':changed})
pins=json.loads((R/'context/38_direct_strategy_20261113/source_pins.json').read_text());head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();check('head_pin',head==pins['head'],head)
refresults={}
for ref,pinned in pins['refs'].items():
 p=subprocess.run(['git','rev-parse','--verify',ref],cwd=R,text=True,capture_output=True)
 refresults[ref]='MATCH' if p.returncode==0 and p.stdout.strip()==pinned else ('ABSENT' if p.returncode else 'DIFFERENT')
check('available_pinned_refs_match',all(v!='DIFFERENT' for v in refresults.values()),refresults)
req=json.loads((O/'exact_requests.json').read_text());lim=req['research_limits'];check('bounded_round',lim['rounds']==1 and lim['queries']<=16 and lim['opens_including_retries_and_downloads']<=24,lim)
check('rw_requests_present',len(req['rw_requests'])>=10)
required=['README.md','canonical_cost_items.csv','ground_overlap.csv','mro_gates.csv','reserve_launch_costs.csv','support_conditions.csv','commercial_options.csv','sources.csv','source_admission.csv','decision_gaps.csv','exact_requests.json','verify.py']
check('outputs_complete',all((O/f).is_file() for f in required))
result={'status':'PASS' if not errors else 'FAIL','checks':checks,'errors':errors,'numeric_model_updates':0,'public_numeric_rows':sum(r['status'].startswith('PUBLIC') and r['amount']!='UNKNOWN' for r in costs),'cost_rows':len(costs),'scope':'Offline schema/refs/units/tax-overlap and tracked preservation checks; not dispatch approval or proof actual contracts','limits':'Initial two web envelopes not fully persisted; downloaded primary evidence complete. Untracked concurrent coordinator files excluded from preservation guard.'}
(O/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='checks'},ensure_ascii=False,indent=2));raise SystemExit(bool(errors))
