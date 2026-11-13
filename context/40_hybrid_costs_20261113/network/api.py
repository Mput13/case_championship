#!/usr/bin/env python3
"""Dependency-free API for root budget assembly. Does not run/reselect networks.

expenses_for('HYBRID','base') returns only existing model expenses and drivers.
runtime_calendar(..., entry_month='2027-07') produces budget SCENARIO months,
not a physical flight timetable or actual 2027 revenue forecast.
"""
import csv,json
from datetime import date
from pathlib import Path
HERE=Path(__file__).resolve().parent
MAIN={'OMS','GSV_MRV','AER_VOG','DIRECT2','HYBRID'}

def _read(name):
    with (HERE/name).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def _number(v):return None if v in {'UNKNOWN','',None} else float(v)

def expenses_for(case_id,scenario,season='annual'):
    """Return existing costs ONCE with signed fuel credit, independent of new BoQ.

    Main case IDs: OMS, GSV_MRV, AER_VOG, DIRECT2, HYBRID.
    Scenarios: base / cautious; season: annual / summer / winter.
    Seasonal amounts include W*7/12 or W*5/12 already: do not multiply again.
    Diagnostic published cases are deliberately excluded from this budget API.
    """
    if case_id not in MAIN:raise ValueError(f'Use fixed main case, one of {sorted(MAIN)}')
    if scenario not in {'base','cautious'}:raise ValueError('scenario must be base or cautious')
    if season not in {'annual','summer','winter'}:raise ValueError('season must be annual, summer or winter')
    data=json.loads((HERE/'CASES.json').read_text())
    results=data['cases'] if season=='annual' else data['seasons']
    result=next(r for r in results if r['case_id']==case_id and r['scenario']==scenario and (season=='annual' or r['season']==season))
    rows=[r for r in _read('component_ledger.csv') if r['case_id']==case_id and r['scenario']==scenario and r['season']==season]
    comp={r['component']:dict(quantity=_number(r['quantity']),quantity_unit=r['quantity_unit'],unit_rate=_number(r['unit_rate']),
          amount_rub=float(r['amount_rub']),cost_signed_rub=float(r['cost_signed_rub']),revenue_signed_rub=float(r['revenue_signed_rub']),
          rate_source=r.get('rate_source',''),formula_source=r['formula_source']) for r in rows}
    er=[r for r in _read('seasonal_exposures.csv') if r['case_id']==case_id and r['scenario']==scenario and r['season']==season]
    airports={}
    for r in er:
        if r['scope']!='NETWORK':airports.setdefault(r['scope'],{})[r['metric']]=_number(r['value'])
    fleet=next(r for r in _read('fleet_requirements.csv') if r['case_id']==case_id and r['scenario']==scenario)
    return dict(case_id=case_id,scenario=scenario,season=season,owner_commit=data['metadata']['owner_commit'],
      accounting='FIXED_NETWORK_REPRICED',currency='RUB',included_costs_rub=result['cost_rub'],
      net_revenue_after_old_fare_forgone_rub=result['net_revenue_rub'],operating_subtotal_before_uncovered_rub=result['subtotal_rub'],
      components=comp,drivers={r['metric']:_number(r['value']) for r in er if r['scope']=='NETWORK'},airports=airports,
      fleet={k:_number(v) if k not in {'case_id','scenario','working_resource_labels','reserve_resource_labels','interpretation'} else v for k,v in fleet.items()},
      unknown_not_zero=list(data['omissions']),finance_main='PURCHASE_LEASE_EXCLUDED_BY_USER; FINANCING_SEPARATE_UNKNOWN_NOT_ZERO',
      coverage_rule='Keep variable MRO/crew/ground/pax once. Add only uncovered amounts net of basket coverage. Shared airport fixed service charged once per unique station. Inventory/deposits separate from annual expense.',
      annualization='W=52 base / 48 cautious; seasonal weights 7/12 + 5/12; fractional equivalent departures are not dated flights.',
      airport_scope='MOW city market; actual operating/billing airport UNKNOWN',
      fleet_rule='Base retains 11 aircraft in HYBRID with local reserves. Cautious minimum may be lower; do not automatically release already acquired/leased tails or fixed staff.',
      calendar_status='ANNUAL_STEADY_STATE_AFTER_ENTRY; NOT_FULL_2027')

def runtime_calendar(case_id,scenario,entry_month,months=12):
    """Allocate season-average budgets to scenario months from full network entry.

    Assumes the WHOLE fixed fleet/network is available at the requested entry.
    No ramp-up, day-of-week, exact monthly spill, slots, or tail/crew roster.
    W/12 equivalent weeks per active month (not calendar days / 7).
    """
    y,m=map(int,entry_month.split('-'));start=date(y,m,1)
    if start<date(2027,7,1):raise ValueError('New SJ100/PD8 entry cannot be assumed before H2 2027')
    if not isinstance(months,int) or not 1<=months<=120:raise ValueError('months must be 1..120')
    rows=[]
    for k in range(months):
        mm=m-1+k;year=y+mm//12;month=mm%12+1
        season='summer' if 4<=month<=10 else 'winter';n=7 if season=='summer' else 5
        v=expenses_for(case_id,scenario,season)
        rows.append(dict(month=f'{year:04d}-{month:02d}',season=season,equivalent_model_weeks=(52 if scenario=='base' else 48)/12,
          included_costs_rub=v['included_costs_rub']/n,net_revenue_rub=v['net_revenue_after_old_fare_forgone_rub']/n,
          operating_subtotal_rub=v['operating_subtotal_before_uncovered_rub']/n,
          components={c:{z:(x/n if z in {'quantity','amount_rub','cost_signed_rub','revenue_signed_rub'} and x is not None else x) for z,x in d.items()} for c,d in v['components'].items()},
          drivers={c:x/n if x is not None else None for c,x in v['drivers'].items()},
          status='SCENARIO_SEASON_AVERAGE_ALLOCATION_NOT_ACTUAL_SLOTS_OR_EXACT_MONTHLY_DEMAND'))
    return dict(case_id=case_id,scenario=scenario,entry_month=entry_month,months=rows,
      assumptions='Full fixed fleet available from entry; no pre-entry revenue; 2027 is not a full steady-state year; calendar allocation uses seasonal averages, not month-specific demand.',
      totals={k:sum(r[k] for r in rows) for k in ['included_costs_rub','net_revenue_rub','operating_subtotal_rub']})

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('case_id',choices=sorted(MAIN));p.add_argument('scenario',choices=['base','cautious'])
    p.add_argument('--season',default='annual',choices=['annual','summer','winter']);a=p.parse_args()
    print(json.dumps(expenses_for(a.case_id,a.scenario,a.season),ensure_ascii=False,indent=2))
