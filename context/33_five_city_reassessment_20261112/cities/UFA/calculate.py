"""Offline arithmetic, not a model rerun or profit forecast. Python standard library.
Run from any directory: python3 /absolute/path/UFA/calculate.py
Frozen files are verified against the parent's manifest. No model output is changed.
"""
from pathlib import Path
import csv, json, hashlib
P=Path(__file__).resolve().parent
PACK=P.parent.parent
manifest=json.loads((PACK/'input_manifest.json').read_text())
checks=[]
for row in manifest:
 f=PACK/row['path'];actual=hashlib.sha256(f.read_bytes()).hexdigest()
 assert actual==row['sha256'],str(f)
 checks.append({'path':row['path'],'sha256':actual,'matches':True})
params={r['parameter']:float(r['base']) for r in csv.DictReader((PACK/'inputs/model/network.csv').open()) if r['base'].replace('.','',1).replace('-','',1).isdigit()}
rows=[r for r in csv.DictReader((PACK/'inputs/model/network_routes.csv').open()) if r['scenario']=='base' and r['variant']=='Хаб UFA']
summary=list(csv.DictReader((PACK/'inputs/model/network_summary.csv').open()))
model=[]
for r in summary:
 if r['hub'] in ['UFA','OMS']:
  model.append({k:r[k] for k in ['scenario','hub','routes','aircraft','flights_week','segments_year','od_trips_year','transfer_od_year','revenue_mln_year','var_cost_mln_year','result_mln_year','rw_migrated_year']})
calc=[];fuel_total=hours=0
# south flag follows the published range_light; classifications explicitly stored below.
for r in rows:
 south='юг/запад' in r['range_light']; km=float(r['km']);f=int(r['freq_week_each_way'])
 bh=params['block_fixed_h']+km*(params['route_factor_south'] if south else params['route_factor'])/params['block_speed_kmh']
 flights=2*f*params['weeks_per_year'];fuel=flights*(params['fuel_t_per_hour']*bh+params['fuel_t_per_cycle'])
 local=float(r['pax_year_local']);trans=float(r['pax_year_transfer_seg']);seg=float(r['pax_year_segments'])
 calc.append({'to':r['to'],'km_rounded_pinned':km,'south':south,'weekly_departures_one_way':f,'annual_local_model':local,'annual_transfer_segments_model':trans,'transfer_share_of_segments':trans/seg,'block_hours_model':bh,'annual_flight_hours_model':bh*flights,'annual_fuel_t_model':fuel,'fuel_3100_increase_mln':fuel*3100/1e6,'local_LF_if_2_weekly_100_seats_52_weeks':local/(2*2*100*52),'local_LF_if_3_weekly_100_seats_52_weeks':local/(2*3*100*52)})
 fuel_total+=fuel;hours+=bh*flights
local_total=sum(float(r['pax_year_local']) for r in rows)
trans_seg=sum(float(r['pax_year_transfer_seg']) for r in rows)
route_result=sum(float(r['result_mln_year']) for r in rows)
out={'method':'Diagnostic fixed-network arithmetic from rounded published rows; no reoptimization, no demand refit, not airline actuals', 'input_manifest_verified':checks,'model_summary':model,'route_diagnostics':calc,'network_diagnostics':{'annual_hours_model':hours,'annual_fuel_t_model':fuel_total,'sum_rounded_route_result_mln':route_result,'annual_local_model':local_total,'annual_transfer_segments_model':trans_seg,'transfer_segments_share':trans_seg/sum(float(r['pax_year_segments']) for r in rows),'new_published_ufa_fuel_plus_into_plane_rub_per_t_ex_VAT':136300+1696,'pinned_fuel_plus_into_plane_rub_per_t':params['fuel_rub_per_t'],'fuel_only_additional_cost_if_all_network_fuel_priced_at_ufa_mln':fuel_total*3100/1e6,'result_after_fuel_only_diagnostic_mln':route_result-fuel_total*3100/1e6,'loss_of_pinned_fuel_compensation_mln':fuel_total*params['fuel_compensation_rub_per_t']/1e6,'result_without_pinned_compensation_mln':route_result-fuel_total*params['fuel_compensation_rub_per_t']/1e6,'unbudgeted_additive_cost_ceiling_per_five_aircraft_mln':route_result/5,'gross_revenue_margin_from_summary_pct':252/4139*100},'tariff_basket_scenario':{'assumed_mtow_t':45.88,'assumed_departing_passengers':75,'VAT':'excluded','regulated_landing_and_security_rub':45.88*(553+499),'terminal_and_passenger_handling_rub':75*(70.5+268),'acceptance_release_rub':16668,'stairs_boarding_and_disembarking_rub':19300,'one_passenger_bus_rub':8100,'subtotal_listed_only_rub':45.88*(553+499)+75*(70.5+268)+16668+19300+8100,'excluded':'fuel; crew; lease; MRO; nav; deicing; towing; water; cleaning; full parking; outstation costs; VAT; contractual discounts; must avoid double counting with model pax_cost'},'scenario_bounds':{'one_foreign_university_cohort_one_round_trip_segments':1858*2,'existing_RW_SVX_4_weekly_100_seats_52_week_bothways_capacity':4*100*52*2,'existing_RW_NUX_2_weekly_100_seats_52_week_bothways_capacity':2*100*52*2,'existing_RW_6_weekly_average_monthly_UFA_departures_scenario':6*52/12,'additional_2_routes_2_weekly_plus_existing_monthly_UFA_departures_scenario':10*52/12,'seventy_monthly_departures_equivalent_weekly':70*12/52},'door_to_door_scenario':{'source':'Published outbound block times; access/security/egress assumptions, no guarantee','nonflight_hours_assumed':3.5,'UFA_SVX_direct_total_h':3.5+1.25,'UFA_MOW_direct_total_h_min':3.5+2+10/60,'UFA_MOW_direct_total_h_max':3.5+2+35/60,'UFA_KRR_direct_total_h':3.5+3+55/60,'UFA_MRV_direct_total_h_min':3.5+3+20/60,'UFA_MRV_direct_total_h_max':3.5+3.5,'bus_5170_to_SVX_departure_buffer_scenario_h':8+2,'bus_5170_vs_air_to_SVX_ready_at_terminal_extra_h_scenario':(8+2)-(0.75+1.5+1.25+1.5),'access_ufa_h':0.75,'preflight_h':1.5,'postflight_h':0.5,'destination_egress_h':0.75}}
(P/'calculations.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['input_manifest_verified','route_diagnostics']},ensure_ascii=False,indent=2))
