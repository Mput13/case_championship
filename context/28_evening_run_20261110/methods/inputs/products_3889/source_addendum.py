#!/usr/bin/env python3
"""Separate impact of evidence@06cb721b; original no-grant outputs are untouched.
Tariff/grant probes are NOT awards. Coefficient=1, unadjusted Appendix2 reference;
lawful regional/Arctic adjustments and every contractual gate remain separate.
"""
import csv,json,hashlib,subprocess
from pathlib import Path
B=Path(__file__).resolve().parent;O=B/'outputs'; E=B/'inputs/evidence_06cb721b'; FINAL=B/'inputs/evidence_38f0f7ae'
read=lambda n:list(csv.DictReader((O/n).open()))
Arows=list(csv.DictReader((B/'inputs/nastya/data/assumptions/network.csv').open()))
A={s:{r['parameter']:float(r[s]) for r in Arows} for s in ['base','cautious']}
def write(n,rows):
    with (O/n).open('w',newline='') as f:
        w=csv.DictWriter(f,list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)
F=lambda r,k:float(r[k])
# Unadjusted reference only, independently checked on original PDF pages14/15.
refs=[dict(route='UFA-SGC',distance_basis='1274 author',raw_special_fare=7089,cap84_103_seats=310249),dict(route='KVX-MRV',distance_basis='1644 official list',raw_special_fare=9021,cap84_103_seats=403871),dict(route='PEE-MMK',distance_basis='1656 author',raw_special_fare=9021,cap84_103_seats=403871),dict(route='PEE-RGK',distance_basis='HIGHEST_DISTANCE_BAND_UPPER_REFERENCE_NOT_MEASURED_ROUTE_DISTANCE',raw_special_fare=10953,cap84_103_seats=403871),dict(route='SVX-OMS',distance_basis='805 official list',raw_special_fare=5157,cap84_103_seats=225989),dict(route='IJK-SVX',distance_basis='447 official list',raw_special_fare=3225,cap84_103_seats=151091)]
for r in refs:r.update(source_commit='38f0f7ae8a10b6a60bd2d5ab39b18a9865e2b78b',source='favt_regional_rules/source.pdf pages14-15; first source pin06cb, final grids38f0',status='RAW_REFERENCE_COEFFICIENT1_NO_REGIONAL_OR_ARCTIC_ADJUSTMENT_NOT_AWARD')
write('addendum_tariff_support_references.csv',refs)
R={r['route']:r for r in refs}; rows=[]
for r in read('C10_contract_thresholds.csv'):
    if r['K_probe']!='0':continue
    leg=int(float(r['roundtrips'])*2);sold=F(r,'corporate_seat_segments')+F(r,'retail_seat_segments');T=R['UFA-SGC']['raw_special_fare'];C=R['UFA-SGC']['cap84_103_seats']
    income=sold*min(F(r,'reference_oneway_fare'),T);support=leg*C
    rows.append(dict(hypothesis='C10',scenario=r['scenario'],variant=r['phase']+'_cohorts'+r['cohorts'],reference_special_fare=T,paid_seat_segments=sold,potential_eligible_revenue_legs=leg,unconstrained_no_support_contribution=F(r,'variable_contribution_at_reference'),fare_revenue_after_reference_cap=income,reference_max_support_if_all_legs_eligible=support,conditional_contribution_after_fare_cap_and_reference_support_before_K=income+support-F(r,'airline_variable_cost'),actual_award='UNKNOWN',credited_support_in_original_model=0,gate='Corporate blocks/public sale and eligibility unconfirmed; no extra air guarantee above effective fare cap under this program'))
for r in read('C14_full_package_thresholds.csv'):
    if r['K_probe']!='0':continue
    sold=F(r,'airline_seat_segments')+F(r,'retail_seat_segments');T=9021;support=F(r,'revenue_legs')*403871
    rows.append(dict(hypothesis='C14',scenario=r['scenario'],variant='full_chain_with_ferries',reference_special_fare=T,paid_seat_segments=sold,potential_eligible_revenue_legs=F(r,'revenue_legs'),unconstrained_no_support_contribution=F(r,'variable_airline_contribution_at_reference'),fare_revenue_after_reference_cap=sold*min(F(r,'airfare_reference_return')/2,T),reference_max_support_if_all_legs_eligible=support,conditional_contribution_after_fare_cap_and_reference_support_before_K=sold*min(F(r,'airfare_reference_return')/2,T)+support-F(r,'airline_variable_cost'),actual_award='AZIMUTH_2026_LISTED_RW_FUTURE_AWARD_UNKNOWN',credited_support_in_original_model=0,gate='Ferry legs excluded; 2026 Azimuth recipient does not transfer to RW; high package price cannot conceal excess air component'))
for r in read('C17_seasonal_thresholds.csv'):
    if r['K_probe']!='0' or r['summer_people_each_leg_probe'] not in ['70','100']:continue
    s=r['scenario'];Fm=A[s]['fare_fixed_rub']+A[s]['fare_per_km_rub']*1656
    capped_delta=F(r,'winter_paid_segments')*(Fm-min(Fm,9021))+F(r,'summer_paid_segments')*(F(r,'rgk_reference_oneway_fare')-min(F(r,'rgk_reference_oneway_fare'),10953))
    count=2*(F(r,'winter_roundtrips')+F(r,'summer_roundtrips'));upper=count*403871
    without=F(r,'full_incremental_at_probe_and_K')-capped_delta
    rows.append(dict(hypothesis='C17',scenario=s,variant=r['year']+'_summer_p'+r['summer_people_each_leg_probe'],reference_special_fare='MMK9021; RGK10953 maximum raw band',paid_seat_segments=F(r,'winter_paid_segments')+F(r,'summer_paid_segments'),potential_eligible_revenue_legs=count,unconstrained_no_support_contribution=F(r,'full_incremental_at_probe_and_K'),revenue_reduction_vs_unconstrained=capped_delta,minimum_support_required_before_K=max(0,-without),reference_max_support_if_all_legs_eligible=upper,conditional_contribution_after_fare_cap_and_reference_support_before_K=without+upper,actual_award='UNKNOWN',credited_support_in_original_model=0,gate='Optimistic all-flight award/reference coefficient1; RGK highest-band upper proxy; effective tariff adjustments, eligibility/efficiency and recipient unconfirmed'))
for s in ['base','cautious']:
    r=next(r for r in read('C31_replacement_frontier.csv') if r['scenario']==s and r['demand_layer']=='nastya_primary')
    sourcefare=A[s]['fare_fixed_rub']+A[s]['fare_per_km_rub']*804
    delta=F(r,'additional_oms_paid_segments')*(sourcefare-min(sourcefare,5157));support=4*225989
    rows.append(dict(hypothesis='C31',scenario=s,variant='new_OMS_flights_only_not_total_replacement',reference_special_fare=5157,potential_eligible_revenue_legs=4,unconstrained_no_support_contribution=F(r,'additional_oms_variable_contribution'),revenue_reduction_vs_unconstrained=delta,reference_max_support_if_all_legs_eligible=support,conditional_contribution_after_fare_cap_and_reference_support_before_K=F(r,'additional_oms_variable_contribution')-delta+support,actual_award='EXTRA_FREQUENCIES_NOT_AUTOMATICALLY_IN_OLD_RW_CONTRACT',credited_support_in_original_model=0,gate='Tu194 needs separate seat/cofinancing/type acceptance; prior MRV grant loss unknown; do not apply SSJ cap directly to Tu'))
for s in ['base','cautious']:
    r=next(r for r in read('C35_partner_thresholds.csv') if r['scenario']==s and r['K_probe']=='0')
    rows.append(dict(hypothesis='C35',scenario=s,variant='two_KEEP_rotations',potential_eligible_revenue_legs=0,reference_max_support_if_all_legs_eligible=0,actual_award='KEEP_AWARD_AND_RETIME_APPROVAL_UNKNOWN',credited_support_in_original_model=0,gate='No extra eligible flights when retaining flights; existing grant is in KEEP and cancels only if conditions preserved; prorated air components must each satisfy effective tariff'))
write('addendum_constrained_support_probes.csv',rows)

# New evidence supports checking own-airline integration, without manufacturing an external partner.
internal=[]
for r in read('C35_partner_thresholds.csv'):
    s=r['scenario'];Q=F(r,'through_oneway_journeys');K=F(r,'K_probe');v=A[s]['pax_cost_rub'];F0=F(r,'customer_oneway_fare');Tsum=3225+5157
    for farecase,price in [('original_no_support_fare',F0),('raw_special_tariff_sum_reference_no_new_grant',min(F0,Tsum))]:
        cost=F(r,'rw_pax_handling_protection_cost')+Q*v
        lost=F(r,'lost_previous_own_contribution_probe');ceiling=Q*price-cost-lost
        internal.append(dict(hypothesis='C35',scenario=s,variant='RW_KEEP_BOTH_LEGS_CONDITIONAL',fare_case=farecase,through_oneway_journeys=Q,rw_used_seat_segments=2*Q,offered_seat_block_per_leg=10,retained_local_people_each_leg_fixture=85,total_aircraft_seats_each_leg=100,customer_oneway_fare=price,customer_total_fare_revenue=Q*price,incremental_two_leg_pax_handling_protection_cost=cost,lost_previous_own_contribution_probe=lost,external_partner_payment=0,maximum_integration_retime_risk_K=ceiling,K_probe=K,full_incremental_at_probe_and_K=ceiling-K,additional_subsidy_from_new_flights=0,actual_2027_KEEP_and_inventory='UNKNOWN',actual_full_result='UNKNOWN',condition='Both flights truly in same2027KEEP and spare seats; retain costs/old demand; confirm baggage/protection/retime/cash; no free extra flights'))
write('addendum_C35_internal_KEEP.csv',internal)
checks=[]
def ck(n,c):
    checks.append(dict(check=n,passed=bool(c)))
    if not c:raise AssertionError(n)
text=(E/'raw/web/favt_regional_rules/text.txt').read_bytes();redo=(E/'raw/web/favt_regional_rules/reextracted.txt').read_bytes()
ck('fresh pdftotext matches pinned evidence text bytes',text==redo)
program=list(csv.DictReader((E/'subsidy_route_matches.csv').open()))
ck('C35 RW November record not August extrapolation',any(r['route']=='IJK-SVX' and r['airline']=='АО «Ред Вингс»' and r['period']=='01.11.2026-31.12.2026' and r['flights_per_week']=='2' and r['round_trips_2026']=='17' for r in program))
final_program=list(csv.DictReader((FINAL/'subsidy_route_matches.csv').open()))
ck('Final evidence retains C35 RW dated context',any(r['route']=='IJK-SVX' and r['airline']=='АО «Ред Вингс»' and r['period']=='01.11.2026-31.12.2026' for r in final_program))
capgrid=list(csv.DictReader((FINAL/'subsidy_cap_84_103_seats.csv').open()));tgrid=list(csv.DictReader((FINAL/'subsidy_special_fare_grid.csv').open()))
for r in refs:
    if r['route']=='PEE-RGK':continue
    km=float(r['distance_basis'].split()[0])
    def contains(x):return float(x['min_km'])<=km and (not x['max_km'] or km<=float(x['max_km']))
    ck('Final cap grid '+r['route'],any(contains(x) and float(x['cap_rub_per_oneway_flight'])==r['cap84_103_seats'] for x in capgrid))
    ck('Final special tariff grid '+r['route'],any(contains(x) and float(x['base_special_fare_rub_including_vat'])==r['raw_special_fare'] for x in tgrid))
for name in ['C10_contract_thresholds.csv','C14_full_package_thresholds.csv','C17_seasonal_thresholds.csv','C31_replacement_frontier.csv','C35_partner_thresholds.csv']:
    exact=subprocess.check_output(['git','show','a39165528ceaa80f026210d0aaae9e2b541e6f51:context/28_evening_run_20261110/products/outputs/'+name],cwd=B)
    ck('First slice monetary table preserved byte-for-byte '+name,exact==(O/name).read_bytes())
for r in internal:
    ck('C35 one fare and two used legs',r['customer_total_fare_revenue']==r['through_oneway_journeys']*r['customer_oneway_fare'] and r['rw_used_seat_segments']==2*r['through_oneway_journeys'])
    ck('C35 internal budget identity',abs(r['maximum_integration_retime_risk_K']-r['full_incremental_at_probe_and_K']-r['K_probe'])<1e-6)
    ck('C35 no new flights no new flight grant',r['additional_subsidy_from_new_flights']==0)
for r in rows:
    ck('No award promoted to actual receipt',r['credited_support_in_original_model']==0 and r['actual_award']!='CONFIRMED_PAID')
(O/'addendum_checks.json').write_text(json.dumps(dict(passed=len(checks),checks=checks,independent_review='NOT_RUN'),ensure_ascii=False,indent=2)+'\n')
items=[]
for p in sorted(O.iterdir()):
    if p.is_file() and p.name!='manifest.json':
        raw=p.read_bytes();items.append(dict(path=str(p.relative_to(B)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
(O/'manifest.json').write_text(json.dumps(items,indent=2)+'\n')
print(json.dumps(dict(new_source='38f0f7ae final; 06cb721b first intake retained',support_probes=len(rows),internal_KEEP_probes=len(internal),checks=len(checks))))
