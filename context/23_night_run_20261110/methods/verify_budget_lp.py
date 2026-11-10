#!/usr/bin/env python3
"""Optional independent optimization check using already installed SciPy; no install."""
import csv
import json
import math
from pathlib import Path
import scipy
from scipy.optimize import linprog

ROOT=Path(__file__).resolve().parent
P=ROOT/'inputs/set001/tsiri_93fa/context'


def rows(p):
    with p.open(newline='')as f:return list(csv.DictReader(f))


def main():
    summary=rows(P/'21_team_proposals/comparison.csv')
    sales=rows(P/'17_aircraft_route_review/model/sales.csv')
    caps=rows(P/'17_aircraft_route_review/model/capacity.csv')
    certificate=rows(ROOT/'runs/budget_v1/supply_upper_bounds.csv')
    results=[]
    for r in summary:
        key=r['source_profile'],r['source_network'],r['scenario']
        s=[x for x in sales if(x['profile'],x['network'],x['scenario'])==key]
        cap={x['flight_id']:float(x['capacity_scenario'])for x in caps if(x['profile'],x['network'],x['scenario'])==key}
        A=[[int(k in x['flight_ids'].split(';'))for x in s]for k in cap]
        pax=500 if r['scenario']=='base'else 650
        objective=[-float(x['fare_once'])+pax*len(x['flight_ids'].split(';'))for x in s]
        sol=linprog(objective,A_ub=A,b_ub=list(cap.values()),bounds=(0,None),method='highs')
        assert sol.success,sol.message
        contribution=-sol.fun-float(r['flight_variable_cost'])
        declared=next(float(b['optimistic_contribution_upper'])for b in certificate if(b['network'],b['scenario'])==(r['network'],r['scenario']))
        assert math.isclose(contribution,declared,abs_tol=1e-6)
        results.append(dict(network=r['network'],scenario=r['scenario'],lp_contribution=contribution,
                            analytic_bound=declared,difference=contribution-declared,status='PASS'))
    target=ROOT/'checks/budget_v1_lp.json';target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(dict(status='PASS_SCOPED',scipy=scipy.__version__,method='HiGHS linear programming',
        source='pinned sales/capacity and flight-cost exports; no imports from budget_thresholds.py',results=results,
        limit='Alternative computation by same methods owner; not independent agent review or source verification'),indent=2)+'\n')
    print(json.dumps({'status':'PASS_SCOPED','lp_cases':len(results),'scipy':scipy.__version__}))


if __name__=='__main__':main()
