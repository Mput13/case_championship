"""Offline frozen network replay. Writes only beside this script. No optimizer/search."""
import sys, csv, json, math, hashlib, inspect, platform
from pathlib import Path
sys.dont_write_bytecode = True
OUT=Path(__file__).resolve().parent
ROOT=OUT.parent
LATEST=ROOT/'inputs/model_schedule/latest'
sys.path.insert(0,str(LATEST/'src'))
import network_model as m
import pandas, numpy

def read(p):
    with p.open() as f: return list(csv.DictReader(f))
def write(name, rows):
    with (OUT/name).open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)
def dump(name, x): (OUT/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
FREEZE=json.loads((ROOT/'model_schedule/freeze.json').read_text())
FIXED=read(ROOT/'model_schedule/fixed_networks.csv')
D=m.Demand(); AS=m.load_assumptions()
# In-memory adapter: freeze frequency rather than solve a new fixed point.
# All flow, capacity, transfer and fare/grant logic remains the pinned source.
src=inspect.getsource(m.hub_network)
a=src.index('        f = {X: int(A["min_freq_week"]) for X in S}')
b=src.index('        # финальные потоки',a)
src=src[:a]+'        f = dict(FROZEN_FREQ)\n'+src[b:]
ns=dict(m.__dict__);exec(compile(src,'<frozen_hub_adapter>','exec'),ns)
hub=ns['hub_network']

class Scaled:
    def __init__(self, scale): self.scale=scale
    def __getattr__(self,k): return getattr(D,k)
    def get(self,a,b,s): return D.get(a,b,s)*self.scale
    # Competitor timetable/segment supply held fixed in retained-demand stresses.
    def seg(self,a,b,s): return D.seg(a,b,s)

CHECKS=[]
def check(name, ok, **kw): CHECKS.append(dict(check=name,passed=bool(ok),**kw))
def replay(net,A=None,scen='base',demand_scale=1):
    A=dict(AS[net['scenario']] if A is None else A);W=A['weeks_per_year']; DD=Scaled(demand_scale)
    rows=[r for r in FIXED if r['network_id']==net['id']]
    if net['id'].startswith('OMS'):
        ns['FROZEN_FREQ']={r['destination']:int(r['frequency_each_direction_week']) for r in rows}
        _,r=hub('OMS',DD,A,scen,[],fixed_spokes=net['spokes'])
        legs,tr,h,c,rev,ol,ot,fl,mig,fg,grant=r
        ls=list(legs.values());seg=ol+2*ot
        transfer_ticket=2*sum(t*m.fare(A,km)*A['transfer_fare_factor'] for x,y,km,t in tr)*W
    else:
        sel=[]
        for name in net['triangles']:
            B,X,Y=name.split(' ',1)[1].split('-');ll=[]
            for row in rows:
                if row['unit']!=name:continue
                a,b=row['origin'],row['destination']
                ll.append(dict(a=a,b=b,km=DD.km(a,b),south=DD.south(a,b),competitive=DD.has_direct(a,b),dem=DD.get(a,b,scen)/(2*W),seg=DD.seg(a,b,scen)/(2*W),rw_now=m.rw_pax_week(a,b,A),freq=int(row['frequency_each_direction_week'])))
            sel.append((0,B,X,Y,0,0,0,0,ll))
        rr=m.direct_network(DD,A,scen,[],fixed_selection=sel) # empty candidates skips irrelevant enumeration
        ls=[l for r in rr for l in r[8]]
        h=sum(r[4] for r in rr);c=sum(r[5] for r in rr);rev=sum(r[6] for r in rr)
        ol=seg=sum(r[7] for r in rr);ot=0;fl=sum(2*l['freq'] for l in ls)
        fg=sum(r[10] for r in rr);grant=sum(r[11] for r in rr);transfer_ticket=0
    tonnes=sum(2*l['freq']*(A['fuel_t_per_hour']*l['block_h']+A['fuel_t_per_cycle']) for l in ls)*W
    grossfuel=tonnes*A['fuel_rub_per_t'];credit=tonnes*A['fuel_compensation_rub_per_t']
    hourly={k:h*W*A[k+'_rub_per_hour'] for k in ('mro','crew','navigation')}
    ground=fl*W*A['ground_rub_per_flight'];deice=fl*W*A['deicing_rub_per_flight'];pax=seg*W*A['pax_cost_rub']
    other=sum(hourly.values())+ground+deice+pax
    check('capacity_'+net['id'],all(l['carried_dir_week']<=l['freq']*A['seats']*A['lf_max']+1e-7 for l in ls))
    check('cost_components_'+net['id'],abs(c*W-(grossfuel-credit+other))<0.01)
    return dict(network_id=net['id'],weeks=W,working=net['working'],reserve=net['reserve'],flights_week=fl,block_h_week=h,
        local_endpoint_od_year=ol*W,transfer_od_year=ot*W,passenger_segments_year=seg*W,seat_segments_year=fl*W*A['seats'],
        ticket_before_forgone_rub=rev*W-grant*W+fg*W,forgone_rw_rub=fg*W,net_ticket_rub=rev*W-grant*W,route_grant_rub=grant*W,
        revenue_net_rub_year=rev*W,transfer_ticket_before_cap_rub=transfer_ticket,fuel_tonnes=tonnes,fuel_price_rub_t=A['fuel_rub_per_t'],credit_rub_t=A['fuel_compensation_rub_per_t'],gross_fuel_rub=grossfuel,fuel_credit_rub=credit,net_fuel_rub=grossfuel-credit,
        mro_rub=hourly['mro'],crew_rub=hourly['crew'],navigation_rub=hourly['navigation'],ground_rub=ground,deicing_rub=deice,pax_cost_rub=pax,other_variable_rub=other,cost_rub_year=c*W,contribution_rub_year=(rev-c)*W,demand_status='SCENARIO_MODEL_NOT_BUYER_DEMAND')

def run():
    baseline=[];sens=[];season=[];front=[];comparison=[]
    for net in FREEZE['networks']:
        b=replay(net);baseline.append(b)
        for k in ('revenue_net_rub_year','cost_rub_year','contribution_rub_year'):
            check('freeze_'+net['id']+'_'+k,abs(b[k]-net[k])<1,delta_rub=b[k]-net[k])
        check('freeze_hours_'+net['id'],abs(b['block_h_week']-net['model_block_h_week'])<1e-8)
        check('segments_'+net['id'],abs(b['passenger_segments_year']-b['local_endpoint_od_year']-2*b['transfer_od_year'])<1e-6)
        # R is gross receipts after any fixed model fare cap, BEFORE forgone RW.
        R=b['ticket_before_forgone_rub'];G=b['route_grant_rub'];Q=b['forgone_rw_rub'];C0=b['cost_rub_year']+b['fuel_credit_rub'];T=b['fuel_tonnes']
        for k in (0,3024,32930):
            for s in (.8,.9,1.):
                fmax=s*R+G-Q-C0+k*T
                sens.append(dict(network_id=net['id'],case='PURE_RECEIPTS_MULTIPLIER_FIXED_PASSENGERS',k_rub_t=k,s=s,passenger_segments_year=b['passenger_segments_year'],fuel_tonnes=T,Fmax_rub_year=fmax,break_even_credit_rub_t=(C0+Q-s*R-G)/T,interpretation='stress, not market/season forecast; fixed grant choice'))
            for F in (0,100e6,200e6,400e6):
                required=(C0+Q+F-k*T-G)/R
                margin=R+G-Q-C0+k*T-F
                front.append(dict(network_id=net['id'],k_rub_t=k,F_budget_axis_rub_year=F,s=1,required_receipts_or_fare_multiplier=required,required_gross_ticket_rub=C0+Q+F-k*T-G,required_extra_ticket_rub=max(0,C0+Q+F-k*T-G-R),required_net_ticket_rub=C0+F-k*T-G,required_credit_rub_t=(C0+Q+F-R-G)/T,conditional_annual_cash_shortfall_rub=max(0,-margin),conditional_annual_cashbridge_rub=max(0,margin),bridge_status='only if all annual PnL realized as cash; before A/deposits/lag/tax; no intra-year solvency inference'))
        sens.append(dict(network_id=net['id'],case='GRANT_WITHHELD_FIXED_CAPPED_RECEIPTS',k_rub_t=32930,s=1,passenger_segments_year=b['passenger_segments_year'],fuel_tonnes=T,Fmax_rub_year=b['contribution_rub_year']-G,interpretation='zero award; no fare or frequency reselection; OMS grant already zero'))
        # True demand retention: reprice neither fares nor costs; reapply shared OD/caps and pax costs.
        # Only downward scenarios allowed; no additional passengers.
        for s in (.8,.9,1.):
            z=replay(net,demand_scale=s)
            sens.append(dict(network_id=net['id'],case='RETAINED_MODEL_OD_COMPETITOR_SUPPLY_FIXED',k_rub_t=32930,s=s,passenger_segments_year=z['passenger_segments_year'],fuel_tonnes=z['fuel_tonnes'],Fmax_rub_year=z['contribution_rub_year'],interpretation='stress; no empirical monthly OD; pax costs and forgone RW recomputed'))
        for F in (0,100e6,200e6,400e6):
            if b['contribution_rub_year']<F:
                threshold='UNREACHABLE_WITH_RETENTION_LE_1'
            else:
                lo,hi=0.,1.
                for _ in range(40):
                    mid=(lo+hi)/2
                    if replay(net,demand_scale=mid)['contribution_rub_year']>=F: hi=mid
                    else:lo=mid
                threshold=hi
            front.append(dict(network_id=net['id'],k_rub_t=32930,F_budget_axis_rub_year=F,required_retained_model_od_fraction=threshold,retention_status='fixed fares/frequencies; shared OD and capacity recomputed; downward only'))
        # Isolate concentration at base parameters, then lost weeks at unchanged weekly profile.
        z=replay(net,dict(AS[net['scenario']],weeks_per_year=48))
        season.append(dict(z,case='BASE_48_CONCENTRATED_ANNUAL_MARKET',period_weeks=48,profile='same annual market, weekly market x52/48; QSI and seats bind; not guaranteed same realized annual receipts'))
        for n in (48,26,22,13):
            z={k:(v*n/52 if isinstance(v,(int,float)) and k not in ('weeks','working','reserve','flights_week','block_h_week','fuel_price_rub_t','credit_rub_t') else v) for k,v in b.items()}
            z['weeks']=n
            season.append(dict(z,case='UNCHANGED_WEEKLY_PROFILE',period_weeks=n,profile='lost/non-operated weeks no recovery; all weekly ledger flows proportional; F and A excluded'))
        A=dict(AS['cautious_sub' if net['scenario'].endswith('_sub') else 'cautious'])
        season.append(dict(replay(net,A,'cautious'),case='CAUTIOUS_FIXED_NETWORK_REPLAY',period_weeks=48,profile='48 weeks concentrated cautious market; lower captures/fares/LF; higher burn/price/hourly/ground/pax costs; grant choice can differ; no frequency reselection'))
    season=[{(k[:-5]+'_period' if k.endswith('_year') else k):v for k,v in r.items()} | {'totals_basis':'PERIOD_NOT_ANNUALIZED'} for r in season]
    for h in [b for b in baseline if b['network_id'] in ('OMS_CURRENT_BASE','OMS_RAMP3_BASE')]:
        for d in [b for b in baseline if b['network_id'].startswith('DIRECT')]:
            for k in (0,3024,32930):
                delta=h['contribution_rub_year']-d['contribution_rub_year']+(k-32930)*(h['fuel_tonnes']-d['fuel_tonnes'])
                comparison.append(dict(hub=h['network_id'],direct=d['network_id'],k_rub_t=k,hub_working=h['working'],hub_reserve=1,direct_working=d['working'],direct_reserve=1,delta_contribution_rub=delta,hub_minus_direct_F_switch_rub=delta,rule='hub wins iff F_hub-F_direct < delta; same assumptions, unequal fleets; direct_sub separate network',operational_gate='UNKNOWN actual fleet slots release; ramp high161.5h>140;22turnfails; transfer calendar unconfirmed'))
    admissions=[dict(id='BUYERS',source='review_evidence/review.md; buyers_opportunities_corrected.csv',status='reported_secondary OSFR Buryatia price request; no contractual volumes',numeric_model_update=0,additional_passengers=0,limitation='procurement not endpoint OD; no new demand admitted'),dict(id='HISTORY',source='TASKS/user gate',status='no causal success/failure inference',numeric_model_update=0,additional_passengers=0,limitation='no market uplift'),dict(id='PILOT',source='model_schedule/freeze.json',status='OMS_PILOT_H1_2027 MOW/KUF/KJA frequency UNKNOWN',numeric_model_update=0,additional_passengers=0,limitation='no ramp economics assigned')]
    for r in read(ROOT/'review_costs/accepted_cost_inputs.csv'):
        admissions.append(dict(id=r['id'],source='review_costs/accepted_cost_inputs.csv',status=r['status'],numeric_model_update=0,additional_passengers=0,limitation=r.get('admission_gate','')+'; public price never RW contract'))
    admissions.extend([dict(id='CREDIT',source='review_costs/review.md;support_inputs.csv',status='3024 mechanism verified; RW application UNKNOWN;32930 historical scenario',numeric_model_update=0,additional_passengers=0,limitation='eligible volumes vs burn; no guaranteed cash or double credit'),dict(id='MRO2024',source='review_costs/review.md via old audit receipt, airport 03.12.2024',status='SSJ maintenance evidence later than 2017',numeric_model_update=0,additional_passengers=0,limitation='capacity/contract/pricing/SJ100 PD8 UNKNOWN')])
    for name,rows in [('baseline_ledger.csv',baseline),('fixed_network_sensitivities.csv',sens),('seasonality_cases.csv',season),('breakeven_frontier.csv',front),('network_comparison.csv',comparison),('findings_admission.csv',admissions)]:write(name,rows)
    dump('calculation_checks.json',dict(checks=CHECKS,errors=[c for c in CHECKS if not c['passed']],environment=dict(python=platform.python_version(),pandas=pandas.__version__,numpy=numpy.__version__)))
    print(json.dumps({'baseline':[(b['network_id'],b['contribution_rub_year']) for b in baseline],'errors':sum(not c['passed'] for c in CHECKS)}))
    if any(not c['passed'] for c in CHECKS):raise SystemExit(1)
if __name__=='__main__':run()
