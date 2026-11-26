#!/usr/bin/env python3
"""P06 cash reconciliation for finalists, including post-horizon settlements."""
import sys
sys.dont_write_bytecode=True
import json,time
import competitive_p09_engine as e
from build_competition_market import dump,writecsv
from run_competitive_p09 import SPOTLIGHT

def main():
    ps=[p for p in json.loads((e.P09/'programmes.json').read_text())['programmes'] if p['programme_id'] in SPOTLIGHT+['MRV_SEASONAL','KZN_HYBRID','REN_RADIAL']]
    details=[];summary=[];monthly=[]
    for config in [e.CONFIGURATIONS[i] for i in [0,1,3,5]]:
        e.configure(config)
        for p in ps:
            r=e.evaluate(p,config)
            extended=e.b.funding(r['known_cash_difference'],'2026-12','2029-02',0,0)
            sides={}
            for label,key in [('project','finance'),('keep','keep_finance')]:
                f=r[key];sides[label]=dict(accrual_cash_bridge=f['accrual_cash_bridge'],unknown_dependencies=f['unknown_dependencies'],
                    cash_complete=f['cash_complete'],terminal=f['terminal'],funding=f['funding'],results_monthly=f['results_monthly'])
            details.append(dict(config=config['config'],programme_id=p['programme_id'],known_incremental_funding=r['funding_diagnostic'],
                extended_known_incremental_funding=extended,extended_scope='same2027_2028_flights_only;settle_tail_to2029_02;no_new2029_business',**sides))
            summary.append(dict(config=config['config'],programme_id=p['programme_id'],known_incremental_peak_to2028_12=r['known_components_incremental_peak_diagnostic'],
                known_incremental_peak_with_settlement_tail_to2029_02=extended['peak_dated_day_end'],
                net_post_horizon_cash_difference=sum(x['amount_signed'] for x in r['known_cash_difference'] if x['payment_date'][:7]>'2028-12' and x['amount_signed'] is not None),
                project_accrual_cash_bridge_residual=r['finance']['accrual_cash_bridge']['residual'],keep_accrual_cash_bridge_residual=r['keep_finance']['accrual_cash_bridge']['residual'],
                full_incremental_peak=None,full_cash_complete=False))
            for m in r['funding_diagnostic']['monthly']:monthly.append(dict(config=config['config'],programme_id=p['programme_id'],**m))
        print(config['config'],'cash DONE',flush=True)
    dump('model_outputs/cashflow_diagnostics.json',details);writecsv('model_outputs/cashflow_diagnostics_summary.csv',summary);writecsv('model_outputs/known_incremental_cash_monthly.csv',monthly)

if __name__=='__main__':main()
