#!/usr/bin/env python3
"""Final context admission without replacing any earlier numeric experiment."""
import json
import calculate as c

PIN='38f0f7ae8a10b6a60bd2d5ab39b18a9865e2b78b'


def main():
    root=c.SOURCE_ROOT/'inputs/evidence38f'
    instances=c.read(root/'dated_service_instances.csv')
    current=c.read(c.OUT/'dated_flights.csv')
    matched=[]
    for flight in [r for r in current if r['network']=='C33' and r['variant']=='KEEP']:
        rr=[r for r in instances if r['origin']==flight['origin'] and r['destination']==flight['destination']
            and r['date']==flight['service_date'] and r['flight'].replace('-','')==flight['flight_number']]
        assert len(rr)==1,(flight['flight_id'],len(rr))
        matched.append(dict(numeric_experiment='C33_KUF_SVX_OMS',flight_id=flight['flight_id'],
                            source_pin=PIN,**rr[0],admission='published baseline exists; retain clock conflict; no tail/seats acceptance'))
    c.write('C33_final_published_baseline.csv',matched)
    context=[dict(source_pin=PIN,**r,network_effect='context only; KUF-based numerical C33 results do not apply to GOJ or another route')
             for r in c.read(root/'alternative_timing_examples.csv') if r['hypothesis'] in ['C01','C03','C04','C33']]
    c.write('final_alternative_timing_context.csv',context)
    sourcecheck=json.loads((root/'dated_checks.json').read_text())
    controls=c.read(root/'subsidy_controls.csv')
    sub15=next(r for r in controls if r['id']=='SUB15')
    report=dict(source_pin=PIN,source_root='inputs/evidence38f',
                counts=dict(pairs=len(c.read(root/'pair_registry.csv')),links=len(c.read(root/'pair_hypothesis_join.csv')),
                            **sourcecheck),
                C33_current_baseline_matched_flights=len(matched),
                C33_selected_conflicting_instances=sum(r['clock_or_type_conflict']=='True' for r in matched),
                conflict_handling='no averaging; latest KUF-SVX arrival10:45 retained. 10:40/10:45 imply retimed wait80/75; both pass60 and fail90',
                other_C33_example='GOJ-SVX7DecWZ5030 -> SVX-OMS8DecWZ5071 has1315min wait; context only, not same numeric product',
                SUB15=sub15,numeric_change='NONE; separate context addendum; old941d and v2 no-support results preserved',
                acceptance='root supplied hashes/joins and FV6846 example; personal selected-row matching/hashes only; fresh independent source review pending')
    (c.HERE/'final_evidence_addendum.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('final evidence matched',len(matched),'C33 baseline flights, conflicts retained',report['C33_selected_conflicting_instances'])


if __name__=='__main__':
    main()
