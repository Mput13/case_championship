#!/usr/bin/env python3
"""Inspect pricing policies on 209 isolated one-RT controls, three seasons.

These are price diagnostics, not additional dispatch-admitted programmes.
"""
import sys
sys.dont_write_bytecode=True
import competitive_p09_engine as e
from build_competition_market import writecsv,dump

def main():
    rows=[]
    for config in [e.CONFIGURATIONS[i] for i in [1,2,3,4]]:
        e.configure(config)
        for pair,m in e.MARKETS.items():
            a,b=pair.split('-')
            for month in [1,5,7]:
                day=e.b.date(2028,month,10);t=e.b.timestamp(day,6)
                f,_=e.b.leg(a,b,t,'PRICE_AUDIT',e.b.NEW_VARIANT,'diagnostic')
                g,_=e.b.leg(b,a,e.b.p05.utc(f['arrival_utc'])+e.b.timedelta(minutes=45),'PRICE_AUDIT',e.b.NEW_VARIANT,'diagnostic')
                result=e.daily_evaluate([f,g],[],config['scenario'],False,'passive',True)[0]
                ps={p['product_id']:p for p in result['products']}
                for x in result['allocation']['allocations']:
                    p=ps[x['product_id']]
                    if p['owner']!='RW':continue
                    bounds=p['competitive_price_bounds']
                    rows.append(dict(pair=pair,month=month,config=config['config'],origin=p['route_airports'][0],destination=p['route_airports'][-1],
                        pricing_policy=config['pricing_policy'],gross_rw_20kg=p['gross_fare'],net_rw=p['net_fare'],carried=x['carried'],
                        cost_floor_planning_85pct_LF=bounds['lower'],willingness_to_pay_ceiling=bounds['upper'],ceiling_below_cost_floor=bounds['below_cost_floor'],
                        ref_gross=p['reference_gross_fare'],direct_competitors=m['direct_competitors'],direct_anchor_annual=m['F_comp_direct_20kg'],
                        direct_capacity_daily=m['competitor_daily_seats'],model_status='ISOLATED_ONE_RT_PRICE_DIAGNOSTIC_NOT_NETWORK_REVENUE'))
    writecsv('calibration/rw_pricing_audit.csv',rows)
    dump('calibration/rw_pricing_audit_summary.json',dict(rows=len(rows),pairs=len(e.MARKETS),configurations=4,months=[1,5,7],
        controls_ceiling_below_planning_floor=sum(r['ceiling_below_cost_floor'] for r in rows),status='DIAGNOSTIC_NOT_ADDITIONAL_PROGRAMMES'))
    print(len(rows),'pricing diagnostics',flush=True)

if __name__=='__main__':main()
