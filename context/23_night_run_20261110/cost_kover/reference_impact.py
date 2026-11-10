#!/usr/bin/env python3
"""Join a separately pinned repaired reference; never upgrade baseline files."""
import collections
import json
from pathlib import Path
import overlay as o


def main():
    ref = o.INPUTS / 'reference_set002'
    oldlegs = o.readcsv(o.INPUTS / 'tsiri_flights.csv')
    newlegs = o.readcsv(ref / 'principal_calendar.csv')
    oldsales = o.readcsv(o.INPUTS / 'tsiri_sales.csv')
    newsales = o.readcsv(ref / 'itinerary_sales.csv')
    out = []
    # Only same programmes get joined. D_SVX8 and D_pilot are not equivalent.
    for oldname, newname in [('H_UFA_8', 'H_UFA_8'), ('H_UFA_4', 'H_UFA_4'), ('D_case', 'D_previous_best8')]:
        old = [r for r in oldlegs if r['profile'] == 'ROUTE_INPUTS_UPPER_100' and r['network'] == oldname]
        new = [r for r in newlegs if r['network'] == newname]
        key = lambda r: (r['date'], r['origin'], r['destination'], r['departure_utc_minute'], r['arrival_utc_minute'], r['block_minutes'])
        oldmap = {r['id']: key(r) for r in old}
        newmap = {r['id']: key(r) for r in new}
        if collections.Counter(oldmap.values()) != collections.Counter(newmap.values()):
            raise AssertionError(('dated programme changed; do not upgrade baseline', oldname))
        for sc in ['base', 'cautious']:
            left = [r for r in oldsales if r['profile'] == 'ROUTE_INPUTS_UPPER_100' and r['network'] == oldname and r['scenario'] == sc]
            right = [r for r in newsales if r['network'] == newname and r['scenario'] == sc]
            skey = lambda r, m: (r['origin'], r['destination'], r['day'], tuple(m[i] for i in r['flight_ids'].split(';')))
            a = {skey(r, oldmap): r for r in left}
            b = {skey(r, newmap): r for r in right}
            if set(a) != set(b) or len(a) != len(left) or len(b) != len(right):
                raise AssertionError(('itinerary join not unique', oldname, sc))
            maxdelta = 0
            for k in a:
                for field in ['sold_journeys', 'gross_revenue', 'foregone_RW_revenue', 'new_pax_variable', 'saved_old_pax_variable']:
                    x, y = float(a[k][field]), float(b[k][field])
                    o.close(x, y, ('reference set002', oldname, field))
                    maxdelta = max(maxdelta, abs(x - y))
            out.append(dict(baseline_network=oldname, reference_network=newname, scenario=sc,
                            legs=len(old), itineraries=len(left), max_numeric_abs_delta=maxdelta,
                            result='SAME_DATED_VALUES_WITHIN_1E-6', baseline_replaced=False))
    o.writejson(o.ROOT / 'reference_impact.json', dict(input_set_id='MR02-reference-set-002',
        reference_commit='27740ffea0821aa404ecd1013d1bb141613261f3', baseline_input_set_id='MR02-input-set-001',
        supersedes_baseline=False, checks=out, excluded_join='D_SVX8 is not D_pilot; no name-based substitution',
        metadata='MR06 corrected descriptions accepted as provenance reference only; old numerical times not changed',
        independent_review='PENDING; this is author-side hash/join/arithmetic self-check, not independent acceptance',
        methods_scope='Budget/donor/supply/pairwise synthesis remains methods@2a74b05179d3619c03fdab3b038fbe7587d85eca; not rerun here'))
    print(json.dumps(dict(reference_groups=len(out), baseline_replaced=False)))


if __name__ == '__main__':
    main()
