#!/usr/bin/env python3
"""Generate integration keys, spend thresholds and the addressed data request register."""
import json
from pathlib import Path
import calculate as c


def thresholds():
    rows=[]
    for s in ['base','cautious']:
        A=c.assumptions(s);cap=2*100*A['lf_max'];p=A['pax_cost_rub']
        north=c.pair('NJC','UFA',s,2);south=c.pair('UFA','MRV',s,2);t=c.pair('NJC','MRV',s,2)
        n=north['captured_local_one_direction'];b=south['captured_local_one_direction']
        fn=north['net_fare_rub']-p;fb=south['net_fare_rub']-p
        ft=t['net_fare_rub']*A['transfer_fare_factor']-2*p
        upper=min(cap,t['diagnostic_week_od_one_direction']*min(A['capture_transfer']*(1-c.math.exp(-2/3)),t['capture_scenario']))
        baseline=n*fn+b*fb
        for loss in [0,.05,.15]:
            def delta(q):
                return 2*(min(n,cap-q)*fn+min(b*(1-loss),cap-q)*fb+q*ft-baseline)
            knots=sorted(set([0,upper]+[k for k in [cap-n,cap-b*(1-loss)] if 0<=k<=upper]))
            best=max(delta(q) for q in knots)
            for spend in [0,250000,500000,1000000]:
                need=None
                for lo,hi in zip(knots,knots[1:]):
                    dl,dh=delta(lo),delta(hi)
                    if dl>=spend:
                        need=lo;break
                    if dl<spend<=dh:
                        need=lo+(spend-dl)/(dh-dl)*(hi-lo);break
                if need is None and delta(knots[-1])>=spend:
                    need=knots[-1]
                rows.append(dict(hypothesis='C01',scenario=s,local_loss_fraction_south=loss,
                                 diagnostic_extra_spend_rub_week=spend,
                                 minimum_through_journeys_both_directions_week=None if need is None else 2*need,
                                 Kmax_rub_week=best,feasible_in_named_OD_and_capacity=need is not None,
                                 scope='spend is a threshold axis, not an estimate of airport/base cost'))
    c.write('C01_spend_thresholds.csv',rows)


def bridge():
    first=json.loads((c.SOURCE_ROOT/'first_run.json').read_text())
    final={r['scenario']+'_'+r['network']:r for r in c.read(c.OUT/'fixed_programs.csv')}
    rows=[]
    for old in first['fixed']:
        new=final[old['scenario']+'_'+old['network']]
        rows.append(dict(network=old['network'],scenario=old['scenario'],metric='local_contribution_rub_week',
                         first_slice=old['contribution_rub_week'],final=float(new['contribution_rub_week']),
                         delta=float(new['contribution_rub_week'])-old['contribution_rub_week'],
                         reason='OMS-KJA compact pilot now uses the same published125/145min clocks as C07; other routes unchanged'))
    finalsync={(r['scenario'],float(r['local_loss_fraction_south'])):r for r in c.read(c.OUT/'C01_synchronization.csv')}
    for old in first['C01']:
        new=finalsync[(old['scenario'],float(old['local_loss_fraction_south']))]
        rows.append(dict(network='C01',scenario=old['scenario'],metric='full_base_contribution_loss'+str(old['local_loss_fraction_south']),
                         first_slice=old['Kmax_full_base_rub_week'],final=float(new['Kmax_full_base_rub_week']),
                         delta=float(new['Kmax_full_base_rub_week'])-old['Kmax_full_base_rub_week'],
                         reason='directional150/145/155/140min clock proxies replace geometry; same-leg synchronization delta unchanged'))
    c.write('first_to_final_bridge.csv',rows)


def programs():
    route_rows=c.read(c.OUT/'fixed_routes.csv')
    definitions=[]
    for network in ['KUF4','OMS1','OMS4','OMS8']:
        rr=[r for r in route_rows if r['network']==network and r['scenario']=='base']
        definitions.append(dict(network=network,hypothesis='C03' if network=='KUF4' else 'C04',
                                routes=[dict(origin=r['origin'],destination=r['destination'],frequency_each_direction_week=2) for r in rr],
                                working_tails_diagnostic=2 if network=='OMS8' else 1,
                                spare_aircraft='UNKNOWN pooled coverage; do not reserve the same spare separately for every alternative',
                                aircraft='existing SSJ100100-seat analog only; SJ100/PD8 sensitivity/prerequisites separate',
                                KEEP='future company network without these additions; unchanged flights not counted as new',
                                resource_source='new tail only if released; otherwise name donor/alternative and subtract its net contribution',
                                transfer_sales='local-only dated program; ideal_bank.csv is a separate schedule-free upper bound'))
    definitions.extend([
        dict(network='C01',hypothesis='C01',flights=['NJC-UFA','UFA-MRV','MRV-UFA','UFA-NJC'],
             frequency_each_direction_week=2,working_tail_positions=['NJC','UFA'],
             variants=['same_unsynchronised','same_synchronised','full_base_budget'],
             warning='two hypothetical start positions; no proof that a no-new-base incumbent program or two free tails exist'),
        dict(network='C07',hypothesis='C07',KEEP='SVX-OMS-SVX WZ5071/5072',
             added=['OMS-KJA','KJA-OMS'],frequency_each_direction_week=2,
             working_tails_diagnostic='same existing SVX tail, conditional on next assignment',
             extra_block_hours_week=9,turn_minutes=[30,45,60],
             displaced_opportunity='WZ5049SVX-REN Wed07:25 only a real timing comparator; actual assigned tail UNKNOWN'),
        dict(network='C33',hypothesis='C33',KEEP='WZ1034/5071/5072/1033 same dates/numbers',
             changed='WZ5071Tue/Fri21:20->12:00SVX; WZ5072Wed/Sat00:50->20:55OMS',
             retained='KUF-SVX08:00; SVX-KUF22:45',extra_block_hours=0,
             resource='one constructed tail sequence; actual rotations and spare seats UNKNOWN',
             operational_change='OMS layover50->1815min per rotation; KUF next start08:00 leaves510min aircraft ground time'),
    ])
    (c.HERE/'programs.json').write_text(json.dumps(dict(owner_pin='4a9763565f70b9ab1eddde2f5daca07687560948',
        diagnostic_period='2026-12-07/2026-12-13; proxy for named future programme, not 2027 forecast',
        scenarios=['base','cautious'],programs=definitions,
        calendar='outputs/dated_flights.csv',demand_fares='outputs/demand_fare_inputs.csv',
        annualisation='NOT_PERFORMED; root methods owns future calendar, N(t), common allocation and total company delta'),ensure_ascii=False,indent=2)+'\n')


def integration():
    flights=c.read(c.OUT/'dated_flights.csv');rows=[]
    for r in flights:
        if r['variant']=='KEEP':
            continue
        old=None
        if r['network']=='C33':
            old=next(x for x in flights if x['network']=='C33' and x['variant']=='KEEP' and x['flight_id']==r['flight_id'])
        elif r['network']=='C07' and r['flight_number']!='PROPOSED':
            old=next(x for x in flights if x['network']=='C07' and x['variant']=='KEEP' and x['flight_number']==r['flight_number'] and x['service_date']==r['service_date'])
        record=dict(network=r['network'],variant=r['variant'],route=r['origin']+'-'+r['destination'],
                         origin=r['origin'],destination=r['destination'],date=r['service_date'],flight_id=r['flight_id'],
                         change='RETIME' if old else 'ADD_SCENARIO',
                         departure_before=old['departure_local'] if old else '',departure_after=r['departure_local'],
                         baseline='same published flight' if old else 'KEEP without project; donor/alternative resource not free',
                         resource_gate='verify real tail/crew/reserve; use programs.json',
                         money_join='outputs/* keyed network/scenario; do not sum incompatible alternatives')
        rows.extend([dict(scenario=s,**record) for s in ['base','cautious']])
    c.write('route_deltas.csv',rows)
    c.write('incompatibilities.csv',[
        dict(left='C07',right='C33',conflict='same WZ5071/5072 dates and tail windows; mutually exclusive timing changes',rule='choose/rebuild jointly; never add standalone deltas'),
        dict(left='C03_KUF4',right='C04_OMS4/OMS8',conflict='same KUF-OMS endpoint market and possible aircraft alternative',rule='one shared OD; no independent market sales'),
        dict(left='C33',right='C03_KUF4/C04_OMS4/OMS8',conflict='KUF-OMS local/direct and transfer offer compete for same endpoint trips',rule='split/allocate one OD and own migration jointly'),
        dict(left='C04_OMS1',right='C07',conflict='OMS-KJA physical/endpoint market; separate programme alternatives',rule='one dated capacity/OD pool if mixed'),
        dict(left='C04_OMS1',right='C04_OMS4/OMS8',conflict='nested growth stages; not additive independent networks',rule='take deltas between stages'),
        dict(left='ALL',right='ALL',conflict='tail/spare/new-aircraft alternative/KEEP company result',rule='single fleet and existing-network budget in methods'),
    ])


def gaps():
    raw=[
      ('C01','retimed_local_sales','RW PNR/revenue by original and shifted time, both UFA spokes','net local margin response','K_retime ceiling1.696m base;0.661m cautious at15%loss'),
      ('C01','two_start_positions_and_base_budget','RW operations + UFA/NJC ground/MRO/crew contracts','two hypothetical positions are not free tails or a demonstrated incumbent programme','full-base contribution0.299m base before K/alternative; cautious negative'),
      ('C03','incremental_KUF_capacity','RW Samara station/line-maintenance/crew planning','primary source proves operating airport, not spare infrastructure or a free tail','weekly empty deployment costs1.136m/1.664m; expansion K minus lodging must be below this to save cost'),
      ('C03','KUF_ARH_and_KUF_OMS_winter_market','Kurumoch/Arkhangelsk/Omsk dated schedules and RW booking inventory','no direct record in the inspected snapshots is not absence of competitors','local-only KUF4 still needs4.847m/16.435m per week plus K/alternative'),
      ('C04','bank_calendar_and_capture','RW OD/availability by date; bank design/crew/airport slots','ideal bank upper bound is not the dated local-only rotation','OMS4 admitted-bank bound approx-1.254m/-15.694m, without support or K'),
      ('C07','actual_next_tail_assignment','RW WZ5072 tail sequence and next leg net contribution','real WZ5049Wed07:25 is a comparator, not proven next assignment','turn45 misses that opportunity50min; base extension already-1.754m before L_next'),
      ('C33','residual_seats_old_transfer_customers','RW leg inventory/PNR/fare classes on WZ1034/5071/5072/1033','modeled endpoint locals are far below assumed85%segments; residuals cannot be zero-valued','15%timing loss: local-only+1.458m/+0.219m versus filled-state-9688/-5460RUB before K'),
      ('C33','retiming_overnight_cost_and_permissions','RW slot/crew/ground handling contracts OMS and SVX','OMS layover grows50->1815min despite equal total tail span','K_retime+L_changed_slots must fit the stated Kmax; MCT90fails'),
      ('C01/C33','MCT_protection_baggage_recovery','UFA/SVX airport minimum-connection tables and RW single-ticket/baggage/recovery contract','MCT60 is diagnostic, not a certified airport minimum or protected product','C01wait60/60 and C33wait75/65 pass60; both fail90, suppressing modeled connection gains'),
      ('ALL','realised_net_yield','RW revenue management/accounts per journey/date/route','model net yield is not final retail20kg fare; avoid second VAT/commission haircut','fare elasticity not estimated; recompute at quote/net-yield change'),
      ('ALL','support_award_unit_period_cap','Rosaviatsia/regional award and airline contract, route/year/unit/cap/payment timetable','support0 in this package means no recognised award, not proof of no possible support','CSV break-even gaps do not establish legal subsidy rate or cash'),
      ('ALL','SJ100_PD8_operating_resource','airline delivery/acceptance/training/MRO and performance documents','SSJ100 proxies do not certify SJ100 or a free2027working tail','methods must apply staged/partial/delayed/no-new N(t); standalone hours supplied'),
      ('ALL','full_PnL_and_cash','RW signed leases/insurance/station/launch/exit/financing and payment schedule','included hourly crew/MRO must not be deducted again; deposits/capex not immediate expenses','DeltaPnL=known contribution-K-A_alt-L_donor+signedD_old; cash separately pending'),
    ]
    c.write('missing_data_requests.csv',[dict(hypothesis=h,field=f,addressed_source=src,why_needed=why,numeric_decision_effect=effect,status='NOT_OBTAINED; request to coordinator, no external contact sent') for h,f,src,why,effect in raw])
    c.write('cost_coverage.csv',[
        dict(item='fuel/refuelling; hourlyMRO/crew/navigation; ground/deicing; pax per flown leg',status='INCLUDED',basis='owner4a976network.csv; calculate.py flight()/three_pools(); same-leg fixed costs cancel for retiming only'),
        dict(item='VAT and retail distribution deductions',status='NO_SECOND_HAIRCUT',basis='audit5905resolutions: fare is scenario realised net; actual realised net/coverage still unknown'),
        dict(item='lease/ownership/insurance; fixed crew/station/MRO/reserve; launch/exit; new timing premiums',status='UNINCLUDED_IF_INCREMENTAL',basis='K variable requires contracts and included-in review; not zero'),
        dict(item='old assignments, new-aircraft alternative, other own transfer/local migration',status='SIGNED_EXTERNAL_DELTA',basis='L_donor/A_alternative/D_old separately; no double subtraction of old gross sales and their margin'),
        dict(item='support',status='NOT_RECOGNISED',basis='no airline-route-future-period award/cap/unit established'),
        dict(item='deposits/capex/advance tickets/payables/support delays',status='CASH_NOT_ESTIMATED',basis='cash(t)=receipts-payments-investment+financing; no invented timing; not equal to contribution'),
    ])


def main():
    thresholds();bridge();programs();integration();gaps()


if __name__=='__main__':
    main()
