import csv, hashlib, importlib.util, inspect, io, json, math, platform, subprocess, sys, time
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(HERE/'inputs/new/src'))
import network_model as nm
import numpy, pandas
nm.dm.TOCHNO=HERE/'runtime/data_intercity_connectivity_162_v20260629.csv'

def fixed_function(module):
    # Preserve the owner's exact build(S); bypass only greedy route selection.
    source=inspect.getsource(module.hub_network)
    source=source[:source.index('    # жадный отбор лучей:')]
    source+='    return list(cand_nodes), build(list(cand_nodes))\n'
    env=dict(module.__dict__);exec(compile(source,'<review fixed S wrapper>','exec'),env)
    return env['hub_network']

fixed=fixed_function(nm)
D=nm.Demand();A=nm.load_assumptions()['base'];W=A['weeks_per_year']
def readrows(pin):
    return list(csv.DictReader((HERE/f'inputs/{pin}/data/processed/network_routes.csv').open()))
def sel(pin):
    return [r['to'] for r in readrows(pin) if r['scenario']=='base' and r['from']=='OMS' and r['variant'].startswith('Хаб')]
S0=sel('old');S1=sel('new')
def calc(S,credit,use_subsidy=0):
    aa=dict(A,fuel_compensation_rub_per_t=credit,use_subsidy=use_subsidy)
    chosen,r=fixed('OMS',D,aa,'base',S)
    legs,trans,hours,cost,rev,od_l,od_t,flights,migr,forgone,subs=r
    fuel=sum(2*L['freq']*(aa['fuel_t_per_hour']*L['block_h']+aa['fuel_t_per_cycle'])*W for L in legs.values())
    detail=[]
    for x,L in legs.items():
        tonnes=2*L['freq']*(aa['fuel_t_per_hour']*L['block_h']+aa['fuel_t_per_cycle'])*W
        detail.append(dict(to=x,km=L['km'],block_h=L['block_h'],freq_each_way=L['freq'],fuel_tonnes_year=tonnes,fuel_gross_rub=tonnes*A['fuel_rub_per_t'],credit_rub=tonnes*credit,rev_rub=L['rev_week']*W,cost_rub=L['cost_week']*W,allocated_result_rub=(L['rev_week']-L['cost_week'])*W,local_annual=2*L['local_carried']*W,transfer_segments_annual=2*L['transfer_carried']*W))
    result=(rev-cost)*W
    return dict(routes=chosen,credit_rub_per_t=credit,flights_week=flights,hours_week=hours,fuel_tonnes_year=fuel,fuel_gross_rub=fuel*A['fuel_rub_per_t'],credit_rub=fuel*credit,nonfuel_cost_rub=cost*W-fuel*(A['fuel_rub_per_t']-credit),cost_rub=cost*W,revenue_rub=rev*W,contribution_rub=result,credit_breakeven_rub_per_t=credit-result/fuel,allocated_revenue_residual=sum(x['rev_rub'] for x in detail)-rev*W,allocated_cost_residual=sum(x['cost_rub'] for x in detail)-cost*W,annual_segments=2*sum(L['carried_dir_week'] for L in legs.values())*W,legs=detail)

out={'scope':'Exact pinned sources; fixed OMS base, no route grant; 0/3024/32930 credits leave demand and fares unchanged. Four OMS base cap probes only. No full main, all hubs or direct solver.','python':sys.version,'platform':platform.platform(),'numpy':numpy.__version__,'pandas':pandas.__version__,'monthly_list':[3024,4804,55122,50858,31010,18125,30664,41321,61445]}
out['monthly_sum']=sum(out['monthly_list']);out['monthly_mean']=out['monthly_sum']/9
out['monthly_precise_series']=[3024,4803.70,55121.50,50857.50,31010.40,18124.80,30663.95,41321.35,61445.35]
out['monthly_precise_mean']=sum(out['monthly_precise_series'])/9
out['fixed_old_network']=[calc(S0,c) for c in [0,3024,32930]]
out['fixed_new_network']=[calc(S1,c) for c in [0,3024,32930]]
subS=[r['to'] for r in readrows('new') if r['scenario']=='base_sub' and r['from']=='OMS' and r['variant'].startswith('Хаб')]
out['fixed_new_network_route_grant_scenario']=calc(subS,32930,1)
out['new_cap_probes']=[]
for cap in [4,6,8,10]:
    t=time.monotonic();ch,r=nm.hub_network('OMS',D,dict(A,fleet_cap=cap),'base',list(D.n.index))
    out['new_cap_probes'].append(dict(cap=cap,routes=ch,contribution_rub=(r[4]-r[3])*W,hours_week=r[2],runtime_s=time.monotonic()-t))
out['route_deletion_examples']=[]
full=out['fixed_new_network'][-1]
for x in ['IKT','GOJ','NOZ']:
    without=calc([q for q in S1 if q!=x],32930)
    allocated=next(r['allocated_result_rub'] for r in full['legs'] if r['to']==x)
    out['route_deletion_examples'].append(dict(route=x,allocated_contribution_rub=allocated,full_minus_without_contribution_rub=full['contribution_rub']-without['contribution_rub'],without_routes=without['routes'],note='Same route set minus one spoke; owner frequency/flow build recalculated, no replacement route optimization.'))
# independently verify published unrounded vs per-route rounded totals for full inventory
rt=readrows('new');sm=list(csv.DictReader((HERE/'inputs/new/data/processed/network_summary.csv').open()))
out['inventory_reconciliation']=[]
for s in sm:
    if not s['hub']: continue
    rr=[r for r in rt if r['scenario']==s['scenario'] and r['from']==s['hub'] and r['variant'].startswith('Хаб')]
    if rr:
        total=sum(float(r['result_mln_year']) for r in rr)
        out['inventory_reconciliation'].append(dict(scenario=s['scenario'],hub=s['hub'],routes=len(rr),route_sum_mln=total,summary_mln=float(s['result_mln_year']),difference_mln=total-float(s['result_mln_year'])))
assert abs(out['fixed_old_network'][0]['contribution_rub']+186479510.49105832)<1
assert all(abs(x[k])<0.01 for typ in ['fixed_old_network','fixed_new_network'] for x in out[typ] for k in ['allocated_revenue_residual','allocated_cost_residual'])
assert round(full['contribution_rub']/1e6)==503
assert max(abs(r['difference_mln']) for r in out['inventory_reconciliation'])<=1.1
out['direct_inventory_reconciliation']=[]
for s in sm:
    if s['hub']:continue
    rr=[r for r in rt if r['scenario']==s['scenario'] and r['variant'].startswith('Прямые')]
    leg_total=sum(float(r['result_mln_year']) for r in rr)
    triangle={r['variant']:float(r['triangle_result_mln_year']) for r in rr}
    out['direct_inventory_reconciliation'].append(dict(scenario=s['scenario'],legs=len(rr),triangles=len(triangle),leg_sum_mln=leg_total,deduplicated_triangle_sum_mln=sum(triangle.values()),summary_mln=float(s['result_mln_year'])))
assert round(out['fixed_new_network_route_grant_scenario']['contribution_rub']/1e6)==952
# Verify persistence of prior exact findings by syntax comparison, not a new broad audit.
import ast
old_ast=ast.parse((HERE/'inputs/old/src/network_model.py').read_text())
new_ast=ast.parse((HERE/'inputs/new/src/network_model.py').read_text())
def fn(tree,name):return next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
out['unchanged_prior_functions']={name:ast.dump(fn(old_ast,name))==ast.dump(fn(new_ast,name)) for name in ['sub_rule','fare','search_caps','hub_best','best_of']}
assert all(out['unchanged_prior_functions'].values())
# Replay the exact old cost and nested build sources against the same unchanged
# demand inputs. Avoid importing an old module with missing untracked raw data.
old_text=(HERE/'inputs/old/src/network_model.py').read_text()
old_env=dict(nm.__dict__)
old_tree=ast.parse(old_text)
old_cost=ast.get_source_segment(old_text,fn(old_tree,'leg_cost'))
old_hub=ast.get_source_segment(old_text,fn(old_tree,'hub_network'))
old_hub=old_hub[:old_hub.index('    # жадный отбор лучей:')]+'    return list(cand_nodes), build(list(cand_nodes))\n'
exec(compile(old_cost+'\n'+old_hub,'<exact old cost and fixed S build>','exec'),old_env)
_,r0=old_env['hub_network']('OMS',D,A,'base',S0)
out['exact_old_source_replay']={'routes':S0,'hours_week':r0[2],'cost_rub_year':r0[3]*W,'revenue_rub_year':r0[4]*W,'contribution_rub_year':(r0[4]-r0[3])*W,'quantity_input':'Same frozen methods raw receipt as prior review, demand-related Git blobs unchanged old to new.'}
assert abs(out['exact_old_source_replay']['contribution_rub_year']-out['fixed_old_network'][0]['contribution_rub'])<0.01
for group in ['fixed_old_network','fixed_new_network']:
    assert len({tuple((L['to'],L['freq_each_way']) for L in r['legs']) for r in out[group]})==1
(HERE/'calculation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
rows=[]
for group in ['fixed_old_network','fixed_new_network']:
    for r in out[group]:
        rows.append(dict(network=group,**{k:v for k,v in r.items() if k not in ['routes','legs']}))
with (HERE/'fuel_sensitivity.csv').open('w') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
for key in ['inventory_reconciliation','route_deletion_examples','direct_inventory_reconciliation']:
    rows=out[key]
    with (HERE/(key+'.csv')).open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
print(json.dumps({k:out[k] for k in ['monthly_mean','new_cap_probes','route_deletion_examples']},ensure_ascii=False,indent=2))
for group in ['fixed_old_network','fixed_new_network']:
    print(group)
    for r in out[group]: print(r['credit_rub_per_t'],r['fuel_tonnes_year'],r['fuel_gross_rub'],r['credit_rub'],r['contribution_rub'],r['credit_breakeven_rub_per_t'])
