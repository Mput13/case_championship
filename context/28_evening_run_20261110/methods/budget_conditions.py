"""Incremental cost coefficients, signed KEEP boundaries and explicitly hypothetical settlement timing."""
import calendar,csv,datetime as dt,json
from collections import defaultdict
from model_kernel import ROOT
OUT=ROOT/'runs/budget_v1';OUT.mkdir(parents=True,exist_ok=True)
a=list(csv.DictReader((ROOT/'runs/annual_v1/annual_budget.csv').open()));months=list(csv.DictReader((ROOT/'runs/annual_v1/monthly_budget.csv').open()))
def f(r,k):return float(r[k] or 0)
def dump(name,rows):
 keys=list(dict.fromkeys(k for r in rows for k in r))
 with (OUT/name).open('w',newline='') as out:w=csv.DictWriter(out,fieldnames=keys);w.writeheader();w.writerows(rows)
rows=[];comparisons=[]
for r in a:
 C=f(r,'contribution_rub');nd=f(r,'new_received_aircraft_days');wd=f(r,'working_aircraft_days')+f(r,'allocated_reserve_days')
 base={k:r[k] for k in ('branch','availability','scenario','network','year')}
 rows.append(base|dict(C_rub=C,max_K_minus_external_signed_D=C,received_aircraft_days=nd,allocated_working_and_reserve_days=wd,finance_cost_per_received_day_upper_if_only_missing_cost=C/nd if nd else None,allocated_aircraft_day_cost_upper_if_only_missing_cost=C/wd if wd else None,lease_in_future_KEEP='CANCELS_ONLY_IF_SAME_IN_BOTH_ACTIONS; opportunity of new capacity remains named external delta',project_triggered_lease='RECEIVED_DAYS*F_received_day + entry/start cost, including before commercial readiness',company_keep_scope='domestic + international + charter; their UNKNOWN PnL not set zero',donor_equation='D_external = delta_old_receipts + avoided_old_costs - extra_replacement_costs, excluding foregone already in C',cash_equation='B0 >= -min_t cumulative(net_settlement_equivalent + fiscal adjustments + granted support cash - variable payments - startup/deposit/finance); unknown actual dates retained',actual_full_pnl=None,actual_peak_cash=None))
lookup={(r['branch'],r['availability'],r['scenario'],r['year'],r['network']):r for r in a}
for r in a:
 if r['network']!='OMS':continue
 q=lookup[(r['branch'],r['availability'],r['scenario'],r['year'],'KUF')]
 delta=f(r,'contribution_rub')-f(q,'contribution_rub');dwork=f(r,'working_aircraft_days')-f(q,'working_aircraft_days')
 comparisons.append({k:r[k] for k in ('branch','availability','scenario','year')}|dict(A='OMS',B='KUF',contribution_A_minus_B_rub=delta,allocated_working_days_A_minus_B=dwork,received_new_aircraft_days_difference=f(r,'new_received_aircraft_days')-f(q,'new_received_aircraft_days'),condition='OMS preferred only if DeltaK_OMS_minus_KUF - DeltaD_external_OMS_minus_KUF <= contribution_difference; equal company acquisition costs cancel',additional_allocated_cost_per_day_rank_boundary=delta/dwork if dwork else None,not_market_forecast=True))
# Every cash amount is a signed incremental net settlement equivalent. Actual gross/tax cash is UNKNOWN.
curves=[];cashrows=[]
for branch in ('PHASED','DELAY6'):
 for family in ('OMS','KUF'):
  data=[r for r in months if r['branch']==branch and r['availability']=='14D_GROUNDING_STRESS' and r['scenario']=='base_sub' and r['network']==family]
  for timing in ('TICKET_FIRST_GRANT45','COST_FIRST_GRANT90','COST_FIRST_NO_GRANTED_SUPPORT'):
   ev=[]
   for r in data:
    y,mo=map(int,r['month'].split('-'));start=dt.date(y,mo,1);end=dt.date(y,mo,calendar.monthrange(y,mo)[1])
    td=start if timing.startswith('TICKET') else end;cd=end if timing.startswith('TICKET') else start
    ev.extend([(td,1,'new_ticket_net_equivalent',f(r,'ticket_before_migration_rub')),(td,2,'old_receipt_foregone',-f(r,'foregone_ticket_rub')),(cd,0 if timing.startswith('COST') else 3,'variable_cost_equivalent',-f(r,'variable_cost_rub'))])
    if not timing.endswith('NO_GRANTED_SUPPORT'):ev.append((end+dt.timedelta(days=45 if '45' in timing else 90),4,'historical_owner_support_shadow',f(r,'support_rub')))
   balance=0.;low=0.
   for date,order,kind,amount in sorted(ev):
    balance+=amount;low=min(low,balance)
    curves.append(dict(branch=branch,network=family,timing=timing,date=str(date),same_day_order=order,kind=kind,amount_net_settlement_equivalent=amount,cumulative=balance,scope='DIAGNOSTIC_TIMING_NOT_ACTUAL_GROSS_CASH; grant not awarded; tax/deposits/startup excluded'))
   cashrows.append(dict(branch=branch,network=family,timing=timing,peak_financing_equivalent=-low,ending_net_equivalent_after_all_proxy_events=balance,unknown_startup_deposit_tax_added_separately=True,actual_peak_cash=None,source_of_timing='EXPLICIT_DIAGNOSTIC_AXES_NOT_LEGAL_PAYMENT_PROMISE'))
dump('full_budget_conditions.csv',rows);dump('OMS_KUF_rank_conditions.csv',comparisons);dump('cash_timing_cases.csv',cashrows);dump('cash_events.csv',curves)
for r in cashrows:
 ev=[e for e in curves if all(e[k]==r[k] for k in ('branch','network','timing'))]
 assert abs(sum(x['amount_net_settlement_equivalent'] for x in ev)-r['ending_net_equivalent_after_all_proxy_events'])<1e-4
(OUT/'validation.json').write_text(json.dumps(dict(status='PASS_OWNER_SCOPED',full_budget_rows=len(rows),rank_conditions=len(comparisons),cash_scenarios=len(cashrows),cash_events=len(curves),actual_gross_cash='UNKNOWN',net_VAT_second_deduction=False),indent=2)+'\n')
print('budget',len(rows),'ranks',len(comparisons),'cash',len(cashrows))
for r in cashrows:print(r['branch'],r['network'],r['timing'],round(r['peak_financing_equivalent']/1e6,3))
