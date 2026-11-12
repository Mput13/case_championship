"""Small operational adapter to frozen P06; never invokes choice/finance."""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
P06=Path(__file__).resolve().parent.parent/'audit/inputs/audit_model/982f13d9/context/35_full_programme_execution_20261112/P06'
sys.path.insert(0,str(P06))
from engine.operations import check_operations

def check(request,result):
    tails=[];flights=[];assign=[]
    for t in request['tails']:
        tails.append(dict(aircraft_id=t['id'],variant=t.get('type','UNKNOWN'),transfer_date=t.get('delivery_date'),service_entry_date=t.get('available_from'),available_from=t.get('available_from'),available_to=t.get('available_to'),initial_location=t.get('initial_location'),turn_minutes=request.get('turn_minutes',45),reserve_intervals=[['2027-01-01T00:00:00Z','2029-01-01T00:00:00Z']] if t.get('reserve') else [],maintenance_intervals=None,crew_windows=None,max_daily_block_hours=8,assumption_id=['OPS06']))
    bytail={t['id']:t for t in request['tails']}
    for f in result['flights']:
        flights.append(dict(schedule_id='SYNTHETIC_API_DEMO',flight_instance_id=f['flight_id'],operator='DEMO',flight_number=f['flight_id'],origin_airport=f['origin'],destination_airport=f['destination'],departure_utc=f['departure_utc'],arrival_utc=f['arrival_utc'],aircraft_variant=bytail[f['tail']]['type'],seats=None,technical_blocked_seats=None,saleable_seats=None,physical_adjacent_leg=True,scheduled_status='proposed',source_status='scenario',source_period='synthetic',assumption_id=['OPS06'],distance_km=None))
        assign.append(dict(flight_instance_id=f['flight_id'],aircraft_id=f['tail'],crew_id=None,action='ADD',assumption_id=['OPS06']))
    return check_operations(dict(context=dict(period_start='2027-01',period_end='2028-12'),flights=flights,fleet_calendar=tails,assignments=assign,resource_operators=['DEMO']))
