"""Dependency-free Python3 API. Exposures are quantities IN THE REQUESTED PERIOD.
No network/passenger reconstruction. All zero defaults are reported as missing.
"""
from pathlib import Path
import csv,json,math
B=Path(__file__).resolve().parent
SCENARIOS=('low','base','high')
def rows(name):
 with (B/name).open(newline='') as f:return list(csv.DictReader(f))
def evaluate(exposures,scenario='base',variant='lean_outsource',residual_before=None):
 if scenario not in SCENARIOS or variant not in ('lean_outsource','expanded'):raise ValueError('scenario/variant')
 for k,v in exposures.items():
  if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:raise ValueError(k)
 params=rows('cost_parameters.csv'); allowed={p['qty'] for p in params}|{'oms_retained_months'}
 if set(exposures)-allowed:raise ValueError('unknown exposure keys: '+str(set(exposures)-allowed))
 missing=sorted(allowed-set(exposures));retained=exposures.get('oms_retained_months',0)
 station=sum(float(r['amount_annual']) for r in rows('station_BoQ.csv') if r['scenario']==scenario and r['variant']==variant)*retained/12
 costs={p['parameter_id']:float(p[scenario])*exposures.get(p['qty'],0) for p in params}
 total=station+sum(costs.values())
 thresholds={}
 if residual_before is not None:
  if not math.isfinite(residual_before):raise ValueError('residual')
  for p in params:
   q=exposures.get(p['qty'],0)
   # Replace this item's cost, keep other selected budget assumptions constant.
   numerator=residual_before-total+costs[p['parameter_id']]
   thresholds[p['parameter_id']]=dict(unit=p['unit'],quantity=q,maximum_rate=numerator/q if q else None,meaning='negative maximum means other costs already exhaust residual; qty0 undefined')
 station_thresholds={}
 if residual_before is not None:
  for r in rows('station_BoQ.csv'):
   if r['scenario']!=scenario or r['variant']!=variant:continue
   q=float(r['qty'])*12*retained/12
   old=float(r['amount_annual'])*retained/12
   station_thresholds[r['item_id']]=dict(unit=r['unit'],quantity=q,maximum_rate=(residual_before-total+old)/q if q else None)
 return dict(station_rate_thresholds=station_thresholds,scenario=scenario,variant=variant,station_cost=station,unit_costs=costs,total_selected_operating=total,residual_after_selected=None if residual_before is None else residual_before-total,thresholds=thresholds,missing_exposures=missing,complete_for_supplied_scope=not missing,note='Author budget only; not actual PnL. Uncovered exposure keys require explicit scope netting; missing quantities do not imply free services. Tax bridge/finance/capital not included.')
def irrops_units(transfer_journeys,scenario='base'):
 """Convenience author sensitivity; hotel person-nights, not rounded room invoice."""
 j=SCENARIOS.index(scenario);a=json.loads((B/'assumptions.json').read_text())['irrops'];affected=transfer_journeys*a['affected_share'][j]
 return dict(affected_journeys=affected,passenger_person_nights=affected*a['overnight_share_of_affected'][j]*a['nights_per_overnight'][j],uncovered_passenger_meals=affected*a['meals_per_affected'][j],uncovered_rebooked_journeys=affected*a['rebooking_share_of_affected'][j],note='Assign hotel rooms and bus orders by event before evaluate; do not bill fractional aggregate rooms.')
def assigned_rooms(events):
 """Each event = {single_people, double_share_people, nights}; pre-group by date/sharing eligibility."""
 single=double=0
 for e in events:
  for k in ('single_people','double_share_people','nights'):
   if int(e[k])!=e[k] or e[k]<0:raise ValueError(k)
  single+=e['single_people']*e['nights'];double+=math.ceil(e['double_share_people']/2)*e['nights']
 return dict(single_room_nights=single,double_room_nights=double)
def invoice_cash_bridge(exvat,vat_rate,recoverable_fraction):
 """Call only with explicitly evidenced invoice assumptions. No tax rate default."""
 if exvat<0 or vat_rate<0 or not 0<=recoverable_fraction<=1:raise ValueError('tax bridge')
 return dict(invoice_cash=exvat*(1+vat_rate),expense=exvat*(1+vat_rate*(1-recoverable_fraction)),recoverable_VAT=exvat*vat_rate*recoverable_fraction)
def extra_working_capital(daily_uncovered_ground_cash,prepay_days):
 # Already-accrued ground expense. Funding only, not total additional expense.
 if daily_uncovered_ground_cash<0 or prepay_days<0:raise ValueError('cash')
 return daily_uncovered_ground_cash*prepay_days
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--exposures',required=True);p.add_argument('--scenario',default='base');p.add_argument('--variant',default='lean_outsource');p.add_argument('--residual',type=float);args=p.parse_args()
 print(json.dumps(evaluate(json.loads(Path(args.exposures).read_text()),args.scenario,args.variant,args.residual),ensure_ascii=False,indent=2))
