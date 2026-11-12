"""Build provenance, dependent fields and research proposals, without external writes."""
import hashlib
import json
from model import ROOT, VERSION, coefficients, materialize_response, read_csv, write_csv, write_json


def main():
    receipts=json.loads((ROOT/'evidence/fetch_receipts.json').read_text())
    for r in receipts:
        if 'local_path' in r:
            assert hashlib.sha256((ROOT/r['local_path']).read_bytes()).hexdigest()==r['sha256']
    write_json(ROOT/'source_lock.json',dict(version=VERSION,new_collection=receipts,pinned_git_inputs='input_manifest.json',
        no_paid_sources=True,new_route_month_endpoint_OD_observations=0,new_monthly_carrier_aggregate_observations=dict(Group=22,Airline=22,not_additive=True),
        false_start='webopen AeroflotIR access-restricted; direct textHTTP actually200 with officialXLS links. No browser or profile manipulation used.'))
    sources=[dict(source_id=r['source_id'],url=r['url'],sha256=r.get('sha256'),local_path=r.get('local_path'),collection='new_primary_http',grain=r['scope'],
                  retrieved_at=r['retrieved_at'],status=r['status'],applicability='scope-specific; a successful fetch is not OD/forecast calibration') for r in receipts]
    sources += [
        dict(source_id='BASE_OD_PRIOR',collection='reused_pinned_git',commit='dceadc98f9a293d7530cb7bc50ca4411a95aa4b6',path='data/processed/od_pairs.csv',grain='modelled_bidirectional_annual_airOD_prior',status='scenario'),
        dict(source_id='BASE_GRAVITY_EXTRAPOLATION',collection='new_calculation_from_pinned_parameters',commit='dceadc98f9a293d7530cb7bc50ca4411a95aa4b6',path='data/processed/od_fit.json',grain='unobserved_endpoint_scenario',status='scenario'),
        dict(source_id='P03_PINNED_DATED_SCENARIO',collection='reused_pinned_git',commit='79dc698b99dfe866886d32376ed388e85bdd039c',path='context/35_full_programme_execution_20261112/P03/sp_adapter/p06_bound_fragments.json',grain='dated_diagnostic_physical_flight_scenario',status='conditional_resource_not_accepted'),
        dict(source_id='P02_COMPARABLE_QUOTES_AND_REGISTERED_ANALOGUES',collection='reused_pinned_git_plus_explicit_scenario',commit='d9486f113f074c185a94bcc5c0afeef12ea3574f',path='context/35_full_programme_execution_20261112/P02/fare_panel.csv',grain='dated_gross_fare_offers_not_realized_yield',status='2flight_date_Standard_quotes_selected_from4comparable_farefamilies'),
        dict(source_id='P05_EXPLICIT_SCENARIO',collection='analyst_scenario',path='assumptions_register.json',grain='conditional_choice_inputs',status='not_observed'),
        dict(source_id='BASE_OD_PRIOR_AND_P05_SCENARIO',collection='pinned_prior_plus_scenario',path='assumptions_register.json',grain='outside_composite_choice_mass_not_physical_capacity',status='scenario'),
    ]
    write_json(ROOT/'sources.json',sources)
    proposals=[
        dict(hypothesis_id='H-P05-01',action='NEW_OR_REFINE_SEASONAL_PROGRAMME',proposal='Compare year-round regional skeleton with seasonally varied frequencies on the same8–12 target pairs; no Decemberweek annualization.',
             basis='New primary2025 domestic monthly carrier series and2026holdout provide an aviation-season analogue. Route season remains unknown, so compare profiles and break-evenmonth demand.',
             source_ids=['NEW_AEROFLOT_2025_MONTHLY','NEW_AEROFLOT_2026_MONTHLY','NEW_FAVT_2025','NEW_MINTRANS_9M'],links=['P07','P08','P09','SP13'],assumption_ids=['P05-A03','P05-A04'],status='PROPOSAL_NOT_PROFITABILITY_VERDICT'),
        dict(hypothesis_id='H-P05-02',action='REFINE_THROUGH_TICKET_VARIANT',proposal='Evaluate a hub both with and without commercially sellable through tickets under a common endpoint pool and dated shared bottleneck seats.',
             basis='Physical two-leg paths exist in P03diagnostic, but sellability/MCT are conditional. The choice model can compare direct vs stop; source absence is not rejection of allhubs.',
             source_ids=['P03_PINNED_DATED_SCENARIO','NEW_MIT_CHOICE','NEW_MIT_LIMITS'],links=['P07','P08','P09','SP05','SP06'],assumption_ids=['P05-A07','P05-A08'],status='CONDITIONAL_ON_COMMERCIAL_CONNECTION_FIELDS'),
        dict(hypothesis_id='H-P05-03',action='REFINE_MOSCOW_AIRPORT_VARIANTS',proposal='TreatSVO/DME/VKO/ZIA as alternatives inside one cityOD demand pool; preserve different airport access/time and physical flight inventory.',
             basis='Author OD usesMOW while P02products are airport-level; adding one MOW demand estimate for every airport duplicates the same trip universe.',
             source_ids=['BASE_OD_PRIOR'],links=['P08','P09','SP02','SP12'],assumption_ids=['P05-A14'],status='REQUIRED_ADAPTER_NOT_MARKET_PREFERENCE_VERDICT'),
        dict(hypothesis_id='H-P05-04',action='METHOD_REVISION_REQUEST',proposal='Prioritise demand-threshold comparisons and local OD evidence before numerical ranking of weakly anchored hubpairs.',
             basis='Grouped annual segment-proxy holdout:25rows,medianAPE62.05%,predict/observed0.128..14.885. No endpointOD or behavioural holdout. This criticises precision, not the existence of latentdemand.',
             source_ids=['BASE_OD_PRIOR'],links=['P01','P05','P07','P08','P09'],assumption_ids=['P05-A01','P05-A15','P05-A16'],status='EVIDENCE_PRIORITY_PROPOSAL_NO_HYPOTHESIS_ECONOMIC_REJECTION'),
    ]
    write_json(ROOT/'hypotheses_delta.json',dict(version=VERSION,pinned_inputs_only=True,proposals=proposals,common_inputs_silently_replaced=False))
    reqs=[
        ('P05-D01','P02/P02I/local_city','Monthly endpointOD2025/2026; direction, journeyvssegment, carrier/coverage and transfers','Would identify/restrict annualOD/season; public unavailable notzero','Airlinecoupon/ticket data; airportroute tables only with grainconversion','P05-A01;P05-A03;P05-A15'),
        ('P05-D02','P02/P03/P07/P08','Dated2027–2028 competing physical flights, operator, seats, blockedseats, productbasket and availableticket','Remove unresolved competitoroutside composite; no P02sourceexport→physicalinventory inference','Explicit future scenarios plus primary dated schedules and inventoryacceptance','P05-A05;P05-A07;P05-A13'),
        ('P05-D03','P03/P07/P09','Whole affected futureKEEP; existingRW sales, contracts, oldtasks and newresource alternativeuse','Cannot identify actual new-toRW, migration or netbusinessgain withoutthem','RWfuture schedule/sales/contracts and acceptedresourcecalendar','P05-A05;P05-A08;P05-A14'),
        ('P05-D04','P04','FutureVAT eligibility by fullpath; recognizedfare components; agent/acquiringrates and owncostdedup','Actualnetyield UNKNOWN; distribution already netted onlyonce','TaxCodeeffectiveatflightdate and airlinecontract/invoice/settlementledger','P05-A10;P05-A11;P05-A12'),
        ('P05-D05','P04/P09','Fullprogramme costs/drivers, support and accrual/cashdates; openingcash and exitobligations','Operatingresult/funding remainnull; no inventedbreakevendate','AcceptedP04events plus P03programme quantities','P05-A12;P05-A16'),
        ('P05-D06','P02/P07','Throughfare and sameticket sellability; airport-specificMCT; connectionprotection','Physicalpath doesnotestablish sellableconnection','Carrierbookingconditions and primaryMCT/transferagreements','P05-A08'),
        ('P05-D07','P06','Response trigger scoped to pool/month/cohort; commonhighlevelpolicy identity with differenteffectiveP/KEEPresponse','Earlycompare requiresidentical responseobjects; dynamicresponse notacceptedcompare','Fix kernelAPI inP06; retain exact counterexample as scopedregression','P05-A13'),
        ('P05-D08','P02/local_city','Multimodalpotentialtrip survey, groundfare/time/capacity and geocodedcatchments','Identify airshare/no-travel mapping, airportchoice and groundsubstitution','Primarytransport surveys; actual rail/busoffers with dates','P05-A02;P05-A05;P05-A09;P05-A14'),
    ]
    write_csv(ROOT/'dependency_requests.csv',[dict(request_id=a,owner=b,missing_field=c,decision_impact=d,possible_source=e,assumption_ids=f,status='UNKNOWN_NOT_ZERO') for a,b,c,d,e,f in reqs])
    fr=json.loads((ROOT/'producer_fragments.json').read_text())
    response={s:{side:materialize_response(f,'price_match10') for side,f in sides.items()} for s,sides in fr.items()}
    write_json(ROOT/'response_fragments.json',dict(version=VERSION,high_level_policy=dict(policy_id='P05-PRICE_MATCH10-v1',trigger='RWavailable on SAMEdemand_pool/month/customer_segment',reaction='incumbentgrossfare×0.9 inclusive-value delta',assumption_id='P05-A13'),
        fragments=response,early_P06_compare_compatible=False,reason='effective response materializations may differ; high-levelpolicyshared; earlycompare demands byte-equivalent responsepolicy'))
    sample=next(r for r in read_csv(ROOT/'od_monthly.csv') if r['demand_pool_id']=='CITY:GOJ>AER' and r['month']=='2028-12' and r['external_scenario_id']=='base')
    p=next(p for p in fr['base']['project']['products'] if len(p['legs'])==2)
    write_json(ROOT/'examples.json',dict(monthly_market=sample,one_transfer_product=p,meaning='One monthly endpointscenario and one realP03dated two-legproduct; no unit interchange or double journeyfare'))
    facts=[]
    for source_id,period,grain,value,unit,scope in [
        ('NEW_FAVT_2025','2025','carrier_domestic_aggregate',81.45,'million_carrier_passengers','annualaggregate;notendpointOD'),
        ('NEW_FAVT_H1','2025-01/2025-06','carrier_domestic_aggregate',38.1,'million_carrier_passengers','sixmonthaggregate'),
        ('NEW_MINTRANS_9M','2025-01/2025-09','carrier_domestic_aggregate',63.3,'million_carrier_passengers','p5;ninemonthaggregate'),
        ('NEW_UFA_2025','2025','airport_all_traffic',4929715,'airport_passenger_services','notendpointOD'),
        ('NEW_UFA_2026','2026-01/2026-08','airport_domestic_traffic',2563649,'airport_passenger_services','notrouteOD'),
        ('NEW_UFA_2026','2026-01/2026-08','airport_international_traffic',666148,'airport_passenger_services','internationalcontext_only_notCASE_SJdemand')]:
        facts.append(dict(source_id=source_id,period=period,grain=grain,value=value,unit=unit,applicability=scope,status='published_primary_aggregate',collection='new'))
    write_csv(ROOT/'primary_source_facts.csv',facts)
    print('Sources,8dependencyrequests,4hypothesisproposals,responsefragments andexamples written')


if __name__=='__main__':main()
