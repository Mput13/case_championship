"""Author replay, exact-objective shortlist and incumbent preservation. No global optimum claim."""
import csv,functools,hashlib,json,math,time
from pathlib import Path
from model_kernel import ROOT,nm,load,ScaledDemand,hub_context,hub_greedy,direct_candidates,direct_greedy,metrics
OUT=ROOT/'runs/selection_v1';OUT.mkdir(parents=True,exist_ok=True)
def dump(name,rows):
 if not rows:return
 fields=list(dict.fromkeys(k for row in rows for k in row))
 with (OUT/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def jsonwrite(name,x):(OUT/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
D,AS=load();nodes=list(D.n.index);hubs=['OMS','KUF','UFA','REN','GOJ'];caps=list(range(2,11))
rows=[];frontiers=[];networks={};rankrows=[];replaychecks=[];mutation=[]
published=list(csv.DictReader((ROOT/'inputs/nastya_4a976/data/processed/network_summary.csv').open()))
def retain(label,scen,calendar,policy,cap,chosen,r,A,kind):
 key=f'{calendar}/{scen}/{label}/{policy}/cap{cap}'
 m=metrics(kind,label,A,r);m.update(id=key,scenario=scen,calendar=calendar,policy=policy,cap=cap,program_count=len(chosen),selected=';'.join(str(x) for x in chosen))
 rows.append(m);networks[key]={'metrics':m,'result':r,'chosen':chosen,'assumptions':A};return m
for calendar in ('AUTHOR_52_48_CONCENTRATED','LOST4_UNIFORM_NO_RECAPTURE'):
 for scen,A in AS.items():
  if calendar.startswith('LOST') and not scen.startswith('cautious'):continue
  d=D if calendar.startswith('AUTHOR') else ScaledDemand(D,48/52)
  print('START',calendar,scen,flush=True)
  for H in hubs:
   spokes,rawbuild=hub_context(H,d,A,A['demand_scen'],nodes);build=functools.lru_cache(None)(rawbuild)
   valid=[]
   for cap in caps:
    chosen,r=hub_greedy(spokes,build,A,cap)
    if not r:continue
    m=retain(H,scen,calendar,'GREEDY',cap,chosen,r,A,'HUB')
    if m['model_8_12_pair_gate']:valid.append(m)
    if valid:
     best=max(valid,key=lambda x:(x['contribution_rub_year'],-x['block_hours_week']))
     frontiers.append(dict(calendar=calendar,scenario=scen,network=H,policy='PRESERVE_FOUND_FEASIBLE',cap=cap,selected_id=best['id'],contribution_rub_year=best['contribution_rub_year'],block_hours_week=best['block_hours_week'],model_city_pairs=best['model_city_pairs'],source_generated_cap=best['cap'],delta_vs_current_greedy_rub_year=best['contribution_rub_year']-m['contribution_rub_year']))
   if calendar.startswith('AUTHOR'):
    target=next(x for x in published if x['scenario']==scen and x['hub']==H)
    last=next(x for x in reversed(rows) if x['network']==H and x['cap']==10 and x['scenario']==scen and x['calendar']==calendar)
    for field,calc in [('result_mln_year',round(last['contribution_rub_year']/1e6)),('segments_year',round(last['segments_year'])),('aircraft',last['aircraft_hour_lower_bound_including_reserve'])]:
     expected=float(target[field]);assert calc==expected,(H,scen,field,calc,expected);replaychecks.append(dict(network=H,scenario=scen,field=field,actual=calc,expected=expected))
  sels,gross,net,evaluate,pairs=direct_candidates(d,A,A['demand_scen'])
  old=sorted(range(len(sels)),key=lambda i:-gross[i])[:int(A['direct_candidates'])]
  new=sorted(range(len(sels)),key=lambda i:-net[i])[:int(A['direct_candidates'])]
  for i in sorted(set(old)^set(new)):
   rankrows.append(dict(calendar=calendar,scenario=scen,candidate='-'.join(sels[i][:3]),old_in=i in old,new_in=i in new,gross_score=gross[i],signed_score=net[i]))
  for policy,pre,city in [('AUTHOR_SHORTLIST',old,False),('SIGNED_SHORTLIST',new,False),('SIGNED_CITY_PAIRS',new,True)]:
   valid=[]
   for cap in (caps if policy!='AUTHOR_SHORTLIST' else [10]):
    chosen,r=direct_greedy(sels,pre,evaluate,pairs,A,cap,city)
    if not r:continue
    m=retain('DIRECT',scen,calendar,policy,cap,['-'.join(sels[i][:3]) for i in chosen],r,A,'DIRECT')
    gate=m['model_8_12_pair_gate'] if city else 8<=len(chosen)<=12
    if gate:valid.append(m)
    if valid:
     best=max(valid,key=lambda x:(x['contribution_rub_year'],-x['block_hours_week']))
     frontiers.append(dict(calendar=calendar,scenario=scen,network='DIRECT',policy=policy+'_PRESERVE',cap=cap,selected_id=best['id'],contribution_rub_year=best['contribution_rub_year'],block_hours_week=best['block_hours_week'],model_city_pairs=best['model_city_pairs'],source_generated_cap=best['cap'],delta_vs_current_greedy_rub_year=best['contribution_rub_year']-m['contribution_rub_year']))
    if policy=='AUTHOR_SHORTLIST' and calendar.startswith('AUTHOR'):
     target=next(x for x in published if x['scenario']==scen and not x['hub'])
     for field,calc in [('result_mln_year',round(m['contribution_rub_year']/1e6)),('segments_year',round(m['segments_year'])),('aircraft',m['aircraft_hour_lower_bound_including_reserve'])]:
      expected=float(target[field]);assert calc==expected,(scen,field,calc,expected);replaychecks.append(dict(network='DIRECT',scenario=scen,field=field,actual=calc,expected=expected))
  print('DONE',calendar,scen,'triangles',len(sels),'shortlist replacements',len(set(old)-set(new)),flush=True)
  dump('all_candidates.csv',rows);dump('preserved_frontiers.csv',frontiers);dump('shortlist_changes.csv',rankrows);dump('author_replay_checks.csv',replaychecks);jsonwrite('networks.json',networks)
# Monotonicity follows from retaining earlier feasible candidates; verify all emitted sequences.
for key in {(x['calendar'],x['scenario'],x['network'],x['policy']) for x in frontiers}:
 seq=sorted([x for x in frontiers if tuple(x[k] for k in ('calendar','scenario','network','policy'))==key],key=lambda x:x['cap'])
 assert all(b['contribution_rub_year']>=a['contribution_rub_year']-1e-6 for a,b in zip(seq,seq[1:])),key
for m in rows:
 assert abs(m['ticket_after_migration_rub_year']+m['support_rub_year']-m['variable_cost_rub_year']-m['contribution_rub_year'])<1e-5
 assert abs(m['segments_year']-m['journeys_year']-m['transfer_journeys_year'])<1e-6
 assert m['block_hours_week']<=(m['cap']-1)*70+1e-8
jsonwrite('validation.json',dict(status='PASS_OWNER_SCOPED',author_replay_checks=len(replaychecks),candidates=len(rows),frontier_rows=len(frontiers),shortlist_changed_rows=len(rankrows),global_optimality='NOT_CLAIMED',dispatch='NOT_RUN',real_support_entitlement='UNKNOWN',net_VAT_second_deduction=False,night_outputs_changed=False))
print('COMPLETE',len(rows),len(frontiers),flush=True)
