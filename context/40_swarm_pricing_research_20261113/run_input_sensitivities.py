#!/usr/bin/env python3
"""Bounded finalist sensitivity to unknown baggage, frequencies and subsidy floor.

Does not overwrite central market or full-matrix outputs. Each case re-evaluates
both project and KEEP with the same changed input. No API calls.
"""
import sys
sys.dont_write_bytecode=True
import copy,json,time
from pathlib import Path
import competitive_p09_engine as e
from build_competition_market import writecsv,dump
from run_competitive_p09 import SPOTLIGHT,base_summary

def main():
    original=copy.deepcopy(e.MARKETS)
    cases=[('baggage_already_in_quote',1),('quote_only_frequency_1weekly',1),('quote_only_frequency_7weekly',1),('competitor_subsidy_floor_relief0',3)]
    ps=[p for p in json.loads((e.P09/'programmes.json').read_text())['programmes'] if p['programme_id'] in SPOTLIGHT+['MRV_SEASONAL','KZN_HYBRID','REN_RADIAL']]
    rows=[];start=time.time()
    for name,basei in cases:
        e.MARKETS=copy.deepcopy(original)
        for m in e.MARKETS.values():
            for d in m['direct_carrier_details']:
                if name=='baggage_already_in_quote' and d['baggage_addon_median']:
                    # Rule-normalised annual price -> remove median bag add-on.
                    # Directional/date composition remains fixed; rough lower bound.
                    d['fare_annual_20kg']=max(500,d['fare_annual_20kg']-d['baggage_addon_median'])
                    d['seasonal_fares']={s:d['fare_annual_20kg']*m['direct_season_indices'][s] for s in ['winter','shoulder','summer']}
                if name.startswith('quote_only_frequency') and d['frequency_quality'].startswith('ASSUMED'):
                    factor=.5 if '1weekly' in name else 3.5
                    for k in ['daily_departures','weekly_departures','daily_seats']:d[k]*=factor
                if name=='competitor_subsidy_floor_relief0':
                    d['variable_floor_subsidy20_stress']=d['variable_floor_unsubsidized'];d['full_floor_subsidy20_stress']=d['full_floor_unsubsidized']
            m['competitor_daily_seats']=sum(d['daily_seats'] for d in m['direct_carrier_details'])
            if name=='baggage_already_in_quote':
                # Raw connecting quote bag inclusion unknown; use 3500 RUB/one-way
                # as a common lower-bound basket correction, not a carrier quote.
                m['F_comp_transfer_20kg']=max(500,m['F_comp_transfer_20kg']-3500)
        config=dict(e.CONFIGURATIONS[basei],config='sensitivity_'+name)
        e.configure(config)
        for p in ps:
            r=e.evaluate(p,config);row=base_summary(r,config,{})
            row['sensitivity_case']=name;row['central_comparison']='comp_market_base' if basei==1 else 'comp_market_cautious';rows.append(row)
        print(name,'DONE',round(time.time()-start,1),flush=True)
    e.MARKETS=original
    writecsv('model_outputs/input_sensitivities.csv',rows)
    dump('model_outputs/input_sensitivities.json',dict(cases=cases,programmes=len(ps),rows=rows,seconds=time.time()-start,
        interpretation='One-at-a-time input scenarios, not confidence intervals. Baggage case approximates inclusion, no checkout evidence. Quote-only capacity changed, observed/award frequencies untouched.'))

if __name__=='__main__':main()
