from pathlib import Path
import csv,json,math,hashlib,sys
sys.dont_write_bytecode=True
from budget_api import evaluate,assigned_rooms,irrops_units,invoice_cash_bridge,extra_working_capital
B=Path(__file__).resolve().parent
checks=[]
def ok(name,cond):
 assert cond,name
 checks.append(dict(check=name,status='PASS'))
def read(n):
 with (B/n).open(newline='') as f:
  r=csv.DictReader(f);rs=list(r)
  ok(n+'_csv_shape',all(None not in x and all(v is not None for v in x.values()) for x in rs));return rs
params=read('cost_parameters.csv');boq=read('station_BoQ.csv');cash=read('oneoff_cash.csv');rules=read('coverage_netting_rules.csv')
for name,rs in [('params',params),('boq',boq),('cash',cash),('rules',rules)]:
 ok(name+'_required_metadata',all(all(x.get(k) for k in ['unit','qty','frequency','payer','tax','currency','date','evidence','price_class','добавка_vs_замена']) for x in rs))
source_ids={r['source_id'] for r in read('sources/priceclass.csv')}
ok('evidence_refs_resolve',all(set(r['evidence'].split(';'))<=source_ids for rs in [params,boq,cash,rules] for r in rs))
for rs,group,col in [(boq,['variant','item_id'],'amount_annual'),(cash,['item_id'],'amount_cash')]:
 grouped={}
 for r in rs:grouped.setdefault(tuple(r[k] for k in group),{})[r['scenario']]=float(r[col])
 ok('scenario_order_'+col,all(x['low']<=x['base']<=x['high'] for x in grouped.values()))
ok('parameter_unique',len({r['parameter_id'] for r in params})==len(params))
ok('ranges_ordered',all(0<=float(r['low'])<=float(r['base'])<=float(r['high']) for r in params))
for r in boq:
 ok('multiply_'+r['variant']+'_'+r['scenario']+'_'+r['item_id'],math.isclose(float(r['rate'])*float(r['qty'])*float(r['frequency']),float(r['amount_annual']),rel_tol=1e-10))
 if r['FTE']!='NA':ok('fte_'+r['variant']+'_'+r['scenario']+'_'+r['item_id'],math.isclose(float(r['posts'])*float(r['hours_per_post_day'])*float(r['coverage_days_year'])/float(r['effective_hours_FTE_year']),float(r['FTE']),rel_tol=1e-10))
for r in cash:ok('cash_'+r['scenario']+'_'+r['item_id'],math.isclose(float(r['rate'])*float(r['qty'])*float(r['frequency']),float(r['amount_cash']),rel_tol=1e-10))
ok('stock_deposit_not_annual',all(float(r['annual_expense'])==0 for r in cash))
ok('boq_no_duplicate_groups',len({(r['variant'],r['scenario'],r['overlap_group']) for r in boq})==len(boq))
ok('no_crew_MRO_ground_replication',not any(r['item_id'] in ('ground','crew','MRO','GPU','ramp_bus','steps','hangar','terminal') for r in boq))
ok('cash_pool_no_stock_double_count',all(float(r['amount_cash'])==0 for r in cash if r['ledger']=='INVENTORY_NOT_SELECTED'))
ok('room_group_rounding',assigned_rooms([dict(single_people=1,double_share_people=3,nights=2),dict(single_people=0,double_share_people=1,nights=1)])==dict(single_room_nights=2,double_room_nights=5))
ok('tax_bridge_identity',invoice_cash_bridge(100,0.17,0.5)==dict(invoice_cash=117.0,expense=108.5,recoverable_VAT=8.5))
ok('prepayment_no_expense',extra_working_capital(10000,7)==70000)
# Explicit normalized test fixtures; NOT annual network exposures.
summary=[]
for v in ['lean_outsource','expanded']:
 amounts=[]
 for s in ['low','base','high']:
  e={r['qty']:0 for r in params};e['oms_retained_months']=12
  a=evaluate(e,s,v,100000000);amounts.append(a['station_cost'])
  summary.append(dict(variant=v,scenario=s,station_annual=a['station_cost'],FTE=sum(float(r['FTE']) for r in boq if r['variant']==v and r['scenario']==s and r['FTE']!='NA'),note='OMS recurring BoQ ONLY; no network insurance/parking/crew travel/IRROPS included'))
  ok('complete_explicit_fixture_'+v+s,a['complete_for_supplied_scope'])
  e['covered_aircraft_years']=10;a=evaluate(e,s,v,100000000)
  for row in a['station_rate_thresholds'].values():ok('station_threshold_unit_'+v+s,row['quantity']>0 and math.isfinite(row['maximum_rate']))
  t=a['thresholds']['insurance']['maximum_rate'];other=a['total_selected_operating']-a['unit_costs']['insurance']
  ok('insurance_threshold_'+v+s,math.isclose(10*t+other,100000000,abs_tol=1e-7))
  half=dict(e,oms_retained_months=6,covered_aircraft_years=5)
  ok('period_units_'+v+s,math.isclose(evaluate(half,s,v)['total_selected_operating']*2,a['total_selected_operating'],rel_tol=1e-10))
 ok('station_order_'+v,amounts==sorted(amounts))
ok('missing_not_hidden',len(evaluate({})['missing_exposures'])==len(params)+1)
for bad in [{'covered_aircraft_years':-1},{'covered_aircraft_years':float('nan')},{'made_up':1}]:
 try:evaluate(bad);raise AssertionError('should reject')
 except ValueError:pass
ok('invalid_exposures_rejected',True)
# Best normalization rows directly useful to assembler.
norm=[]
for r in params:
 q=1000 if 'departure' in r['unit'] else (10 if 'aircraft-year' in r['unit'] else 1)
 norm.append(dict(parameter_id=r['parameter_id'],qty=q,unit=r['unit'],low=float(r['low'])*q,base=float(r['base'])*q,high=float(r['high'])*q,meaning='Pure coefficient, not claimed network total'))
for name,rs in [('station_totals.csv',summary),('normalizations.csv',norm)]:
 with (B/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
# Sweep is a reference residual unit of100m with10tail-years, NOT deck claimed568m or actual remaining headroom.
sweep=[]
for rate in json.loads((B/'assumptions.json').read_text())['insurance_sweep_RUB_aircraft_year']:
 for v in ['lean_outsource','expanded']:
  station=next(r['station_annual'] for r in summary if r['variant']==v and r['scenario']=='base')
  sweep.append(dict(variant=v,rate_RUB_aircraft_year=rate,qty_aircraft_years=10,reference_residual_before=100000000,station_base=station,insurance_total=10*rate,residual_after_selected=100000000-station-10*rate,break_even_rate=(100000000-station)/10,note='Normalized test: all variable network exposures intentionally excluded. Replace100m with audited residual and supply quantities via API. Zero insurance row sensitivity only.'))
with (B/'insurance_sweep.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(sweep[0]));w.writeheader();w.writerows(sweep)
# IRROPS per100 affected journeys (frequency uncertainty kept separate from price).
ir=[]
for j,s in enumerate(['low','base','high']):
 person_nights=100*[.25,.5,1][j]*[1,1,2][j];meals=100*[1,2,3][j];rebook=100*[.25,.5,1][j]
 # Single room planning coefficient, exact rooms still event-rounded when actual inputs supplied.
 total=person_nights*4100+meals*[500,800,1200][j]+rebook*[3000,8000,15000][j]
 ir.append(dict(scenario=s,affected_journeys=100,hotel_person_nights=person_nights,hotel_single_rate=4100,meal_qty=meals,meal_rate=[500,800,1200][j],rebook_qty=rebook,rebook_rate=[3000,8000,15000][j],amount_ex_transport=total,RUB_per_affected_journey=total/100,note='Analyst event mix; no disruption probability fact; transport and distribution service exposure excluded'))
with (B/'irrops_normalization.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(ir[0]));w.writeheader();w.writerows(ir)
sw=read('unknown_sweeps.csv')
ok('unknown_sweep_thresholds',all(math.isclose(float(r['break_even_rate'])*float(r['qty'])*float(r['loaded_factor']),float(r['reference_headroom']),rel_tol=1e-10) for r in sw))
ok('unknown_sweep_multiplication',all(math.isclose(float(r['rate'])*float(r['qty'])*float(r['loaded_factor']),float(r['amount']),rel_tol=1e-10) for r in sw))
ok('classes_valid',all(r['price_class'] in {'PRIMARY','ANALOGUE','ANALYST_SELECTED_PLACEHOLDER','UNKNOWN'} for rs in [params,boq,cash,rules] for r in rs))
# Confirm source inputs unchanged after calculations.
ok('read_inputs_hashes_unchanged',all(hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()==x['sha256'] for x in json.loads((B/'sources/local_inputs.json').read_text())))
report=dict(status='PASS',checks=len(checks),results=checks)
print(json.dumps(dict(status='PASS',checks=len(checks),station_totals=summary),ensure_ascii=False))
(B/('validation_'+sys.argv[1]+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
