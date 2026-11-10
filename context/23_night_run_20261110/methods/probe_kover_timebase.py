#!/usr/bin/env python3
"""Read-only targeted MR02 time-base probe; original module unchanged."""
import importlib.util
import json
from datetime import datetime,timedelta,timezone
import common_demand as m


def main():
    source=m.ROOT/'inputs/cost-kover-001'
    spec=importlib.util.spec_from_file_location('pinned_mr02_overlay_probe',source/'overlay.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    definition=json.loads((source/'scenario_definitions.json').read_text())
    legs=[r for r in module.readcsv(source/'inputs/tsiri_flights.csv')if r['profile']=='ROUTE_INPUTS_UPPER_100'and r['network']=='H_UFA_8']
    original=module.instant
    epoch=datetime.fromisoformat(definition['period_start']).replace(tzinfo=timezone.utc)
    def corrected(leg,event):return epoch+timedelta(minutes=float(leg[event+'_utc_minute']))
    mismatches=[]
    for r in legs:
        if original(r,'departure')!=corrected(r,'departure'):
            mismatches.append(dict(flight_id=r['id'],source_date=r['date'],absolute_minute=r['departure_utc_minute'],
                                   original_overlay_utc=original(r,'departure').isoformat(),correct_epoch_utc=corrected(r,'departure').isoformat(),
                                   delta_minutes=(original(r,'departure')-corrected(r,'departure')).total_seconds()/60))
    touched={r['id']for r in legs if module.hits(r,definition['episode'])}
    shifted=[]
    for r in legs:
        row=dict(r)
        if row['id']in touched:
            for k in ['departure','arrival']:row[k+'_utc_minute']=float(row[k+'_utc_minute'])+1440
        shifted.append(row)
    bad_before=module.template_rotation(shifted,reference=legs)
    module.instant=corrected
    bad_after=module.template_rotation(shifted,reference=legs)
    assert len(touched)==16 and not bad_before and bad_after
    def peak_inflight(schedule):
        events=[]
        for leg in schedule:
            events.extend([(corrected(leg,'departure'),1),(corrected(leg,'arrival'),-1)])
        active=peak=0
        for _,delta in sorted(events):active+=delta;peak=max(peak,active)
        return peak
    peak_baseline=peak_inflight(legs);peak_shifted=peak_inflight(shifted)
    episode_day2=dict(definition['episode'],start_utc='2026-12-08T00:00:00+00:00',end_utc_exclusive='2026-12-09T00:00:00+00:00')
    correct_day2={r['id']for r in legs if module.hits(r,episode_day2)}
    module.instant=original
    original_day2={r['id']for r in legs if module.hits(r,episode_day2)}
    assert not original_day2 and len(correct_day2)==16
    old=m.OUT
    try:
        m.OUT=m.ROOT/'checks/kover_timebase'
        m.save('timestamp_mismatches.csv',mismatches)
        m.save('probe.json',dict(source_commit='afadee35ebeefe54a05bdfc5b3e224a370f90e0a',source_file='overlay.py',source_function='instant',
                                 severity='P2',status='REPRODUCED_BY_METHODS_OWNER',source_time_unit='UTC absolute minute from2026-12-07T00Z',
                                 defect='Adds absolute minutes to each row date; second program day moves to third calendar day',
                                 H_UFA8_timestamp_mismatches=len(mismatches),original_delay_rotation_issues=bad_before,
                                 corrected_delay_rotation_issues=bad_after,original_day2_hit_count=len(original_day2),correct_day2_hit_count=len(correct_day2),
                                 baseline_peak_simultaneous_flights=peak_baseline,shifted_peak_simultaneous_flights=peak_shifted,
                                 minimum_airborne_tails_for_same_shifted_times=peak_shifted,
                                 day1_cancel_money_effect='No change in touched set; source cancel arithmetic not falsified by this probe',
                                 hold='Published post-day1 timestamps, generic episode detection, delay-bank claimed continuity and served-all feasibility',
                                 minimal_fix='Use period-start UTC epoch for absolute minutes; rebuild new projection and keep delay rotation conflicts unresolved unless explicit recovery resource is supplied',
                                 no_original_files_modified=True))
    finally:m.OUT=old
    print(json.dumps(dict(mismatches=len(mismatches),original_delay_issues=len(bad_before),corrected_delay_issues=len(bad_after),day2_original=len(original_day2),day2_correct=len(correct_day2))))


if __name__=='__main__':main()
