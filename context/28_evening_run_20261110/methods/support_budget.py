"""Coupled 2026 rule diagnostic: flight cap AND economy fare ceiling, never an awarded 2027 income."""
import csv,hashlib,json,math
from model_kernel import ROOT,nm
OUT=ROOT/'runs/support_v1';OUT.mkdir(parents=True,exist_ok=True)
e=ROOT/'inputs/evidence_06cb';text=(e/'raw/web/favt_regional_rules/text.txt').read_text()
fares=[2017,2258,2741,3225,3708,4191,4674,5157,5640,6123,6606,7089,7572,8055,8538,9021,9504,9987,10470,10953]
assert '2 017 2 258 2 741 3 225 3 708 4 191 4 674 5 157 5 640 6 123 6 606 7 089 7 572 8 055 8 538 9 021 9 504 9 987 10 470 10 953' in text
assert 'на все места в салоне экономического класса' in text
caps=list(csv.DictReader((e/'subsidy_cap_84_103_seats.csv').open()))
listed=list(csv.DictReader((e/'subsidy_route_matches.csv').open()))
lookup={}
for r in listed:lookup.setdefault(tuple(sorted((r['origin'],r['destination']))),[]).append(r)
def farecap(km):
 d=math.ceil(km)
 if d==200:return None
 return fares[0] if d<200 else fares[min(19,math.ceil(d/100)-2)]
def grantcap(km):
 d=math.ceil(km)
 rows=[x for x in caps if d>=int(x['min_km']) and (not x['max_km'] or d<=int(x['max_km']))]
 return float(rows[0]['cap_rub_per_oneway_flight']) if len(rows)==1 else None
net=json.loads((ROOT/'runs/selection_v1/networks.json').read_text())
front=list(csv.DictReader((ROOT/'runs/selection_v1/preserved_frontiers.csv').open()))
ids=sorted({r['selected_id'] for r in front if r['calendar'].startswith('AUTHOR') and r['cap']=='10' and (r['network']!='DIRECT' or r['policy']=='SIGNED_CITY_PAIRS_PRESERVE')})
summary=[];legsout=[];boundary=[]
for key in ids:
 n=net[key];m,A,r=n['metrics'],n['assumptions'],n['result'];W=A['weeks_per_year'];hub=m['kind']=='HUB'
 legs=list(r[0].values()) if hub else [l for t in r for l in t[8]]
 grants=0.;fc={};reg=[]
 for j,l in enumerate(legs):
  a,b=l['a'],l['b'];pair=tuple(sorted((a,b)));nong='MOW' not in pair;matches=lookup.get(pair,[])
  cg=grantcap(l['km']) if nong else 0.;cf=farecap(l['km']) if nong else None
  fc[pair]=cf;grants+=2*l['freq']*W*(cg or 0.)
  reg.append((l,nong,cg,cf))
  legsout.append(dict(network_id=key,origin=a,destination=b,distance_model_km=l['km'],distance_for_table='CEIL_GEODESIC_PROXY_NOT_CERTIFIED_ROUTE_DISTANCE',completed_flights_model_year=2*l['freq']*W,per_flight_table_cap_coefficient1=cg,special_gross_economy_fare_base=cf,all_economy_rule_applied=nong,actual_grant=None,listed2026_carriers=' | '.join(sorted({x['airline'] for x in matches})),RW_in_2026_list=any('Ред Вингс' in x['airline'] for x in matches),future_award='UNKNOWN',cofinancing_and_month='REQUIRES_CONTRACT_NOT_ASSUMED',special_fare_adjustment='BASE_TABLE_NO_1_25_OR_1_5_OR_REGIONAL_INCREASE_ASSUMED'))
 def net_receipts(eta):
  gross=0.
  for l,nong,cg,cf in reg:
   unit=nm.fare(A,l['km'])
   if nong:unit=min(unit,eta*cf) if cf is not None else 0.
   q=l['local_carried'] if hub else l['carried_dir_week']
   gross+=2*q*unit*W
  if hub:
   for x,y,km,t in r[1]:
    u=nm.fare(A,km)*A['transfer_fare_factor'];limits=[]
    for v in (x,y):
     pair=tuple(sorted((m['network'],v)));cap=fc[pair]
     if 'MOW' not in pair:limits.append(eta*cap if cap is not None else 0.)
     else:limits.append(nm.fare(A,r[0][v]['km']))
    # Sum of leg ceilings is only a necessary upper envelope, not an approved through tariff.
    gross+=2*t*min(u,sum(limits))*W
  return gross-m['foregone_ticket_rub_year']
 R=net_receipts(1);C=R+grants-m['variable_cost_rub_year']
 def c_eta(eta):return net_receipts(eta)+grants-m['variable_cost_rub_year']
 if C>=0:
  lo,hi=0.,1.
  for _ in range(60):
   mid=(lo+hi)/2
   if c_eta(mid)>=0:hi=mid
   else:lo=mid
  eta_min=hi
 else:eta_min=None
 summary.append(dict(network_id=key,scenario=m['scenario'],network=m['network'],city_pairs=m['model_city_pairs'],owner_support_rub_year=m['support_rub_year'],owner_ticket_after_migration_rub_year=m['ticket_after_migration_rub_year'],without_support_owner_yield_contribution=m['contribution_rub_year']-m['support_rub_year'],fare_constrained_net_receipts_upper_eta1=R,all_nonMOW_flight_cap_coefficient1=grants,contribution_at_eta1_all_flight_caps=C,required_fraction_of_all_caps_at_eta1=(m['variable_cost_rub_year']-R)/grants if grants else None,minimum_eta_for_variable_zero_at_all_caps=eta_min,owner_variable_cost_rub_year=m['variable_cost_rub_year'],income_accepted_in_strategy=False,scope='FIXED_QUANTITIES_DIAGNOSTIC_FUTURE_AWARD_UNKNOWN; all route/month/cofinance gates must be met',through_ticket_scope='ONE_FARE_MIN_OWNER_NET_AND_SUM_GROSS_LEG_CEILINGS_NECESSARY_UPPER_ENVELOPE',VAT='NO_AUTOMATIC_SECOND_DEDUCTION; eta parameter is unresolved net/gross realisation, eta1 upper ceiling',full_result='R_capped(eta) - C_var + accepted_completed_flights*contract_rate*coefficient + D_external - K_excluded'))
 # Counterexample required by the coupled contract: naive cap replacement overstates this same quantity result.
 naive=m['ticket_after_migration_rub_year']+grants-m['variable_cost_rub_year']
 boundary.append(dict(network_id=key,naive_replace_support_keep_owner_yield=naive,coupled_eta1_ceiling=C,overstatement_from_ignoring_fare_ceiling=naive-C,no_new_award_acceptance=True))
def dump(name,rows):
 with (OUT/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
dump('route_constraints.csv',legsout);dump('coupled_boundaries.csv',summary);dump('fare_constraint_counterexamples.csv',boundary)
(OUT/'fare_ceiling_source.json').write_text(json.dumps(dict(source_commit='06cb721b3e8e4eb8710c065c7b02078a112626a9',source_path='raw/web/favt_regional_rules/text.txt',source_sha256=hashlib.sha256((e/'raw/web/favt_regional_rules/text.txt').read_bytes()).hexdigest(),appendix=2,base_fares=fares,all_economy_clause_present=True,legal_applicability='2026 rule reference, not granted 2027-2028 funding'),indent=2)+'\n')
print('networks',len(summary),'route_constraints',len(legsout))
for x in summary:
 if x['network'] in ('OMS','KUF') and x['scenario']=='base_sub':print(x)
