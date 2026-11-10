import csv,json
from model_kernel import ROOT
from dated_offer import construct
p=ROOT/'runs/selection_v1';o=ROOT/'runs/resource_v1';o.mkdir(parents=True,exist_ok=True)
net=json.loads((p/'networks.json').read_text());rows=[];plans={}
for key,n in net.items():
 m=n['metrics']
 if m['calendar']!='AUTHOR_52_48_CONCENTRATED' or m['policy'] not in ('GREEDY','SIGNED_CITY_PAIRS'):continue
 plan=construct(n);plans[key]=plan
 rows.append(dict(id=key,network=m['network'],scenario=m['scenario'],source_cap=m['cap'],model_city_pairs=m['model_city_pairs'],hour_lower_working=m['working_hour_lower_bound'],constructed_working=plan['working_tails'],status=plan['status'],within_source_cap=(plan['working_tails']+1<=m['cap']) if plan['working_tails'] is not None else None,reserve_location_feasibility=plan.get('reserve_location_feasibility','UNKNOWN')))
with (o/'resource_gates.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(o/'plans.json').write_text(json.dumps(plans,ensure_ascii=False,indent=2)+'\n')
print('rows',len(rows),'constructed',sum(x['constructed_working'] is not None for x in rows),'fit_source_cap',sum(x['within_source_cap'] is True for x in rows))
for x in rows:
 if x['source_cap']==10 and x['network'] in ('OMS','KUF','DIRECT'):print(x)
