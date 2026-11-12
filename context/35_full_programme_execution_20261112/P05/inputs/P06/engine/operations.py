"""Physical dated adjacent legs, ordered itineraries and explicit tail assignments."""
from datetime import timedelta
from .common import EPS, fields, number, require, unique, utc


def check_operations(bundle):
    flights = unique(bundle["flights"], "flight_instance_id", "flights")
    tails = unique(bundle["fleet_calendar"], "aircraft_id", "fleet_calendar")
    assignments = unique(bundle["assignments"], "flight_instance_id", "assignments")
    errors, unknowns, rotations = [], [], []
    physical_keys = set()
    for fid, f in flights.items():
        fields(f, "schedule_id operator flight_number origin_airport destination_airport departure_utc arrival_utc aircraft_variant seats technical_blocked_seats saleable_seats physical_adjacent_leg scheduled_status source_status source_period assumption_id distance_km", fid)
        require(f["origin_airport"] != "MOW" and f["destination_airport"] != "MOW", f"{fid}: MOW is not an airport")
        require(f["origin_airport"] != f["destination_airport"], f"{fid}: identical airports")
        require(f["physical_adjacent_leg"] is True, f"{fid}: unverified physical adjacency cannot create inventory")
        dep, arr = utc(f["departure_utc"]), utc(f["arrival_utc"])
        require(arr > dep, f"{fid}: arrival must follow departure")
        require(bundle["context"]["period_start"] <= dep.strftime("%Y-%m") <= bundle["context"]["period_end"], f"{fid}: departure outside operating horizon")
        key = (f["operator"], f["origin_airport"], f["destination_airport"], dep)
        require(key not in physical_keys, f"{fid}: duplicate physical flight under another id/marketing code")
        physical_keys.add(key)
        for k in ("seats", "technical_blocked_seats", "saleable_seats", "distance_km"):
            number(f[k], f"{fid}.{k}", 0, nullable=True)
        if any(f[k] is None for k in ("seats", "technical_blocked_seats", "saleable_seats")):
            unknowns.append(f"{fid}: physical seat inventory UNKNOWN")
        else:
            require(abs(f["seats"] - f["technical_blocked_seats"] - f["saleable_seats"]) <= EPS, f"{fid}: saleable seat bridge")
        if f["scheduled_status"] == "cancelled":
            require(f["saleable_seats"] == 0, f"{fid}: cancelled flight has seats")
        if f["operator"] in bundle["resource_operators"] and f["scheduled_status"] != "cancelled":
            require(fid in assignments, f"{fid}: missing physical tail assignment")
    for fid, a in assignments.items():
        require(fid in flights, f"{fid}: assignment to absent flight")
        fields(a, "aircraft_id crew_id action assumption_id", fid)
        require(a["aircraft_id"] in tails, f"{fid}: unknown tail")
    for tid, t in tails.items():
        fields(t, "variant transfer_date service_entry_date available_from available_to initial_location turn_minutes reserve_intervals maintenance_intervals crew_windows max_daily_block_hours assumption_id", tid)
        number(t["turn_minutes"], f"{tid}.turn_minutes", 0, nullable=True)
        number(t["max_daily_block_hours"], f"{tid}.max_daily_block_hours", 0, nullable=True)
        fs = sorted((flights[fid] for fid, a in assignments.items() if a["aircraft_id"] == tid), key=lambda f: utc(f["departure_utc"]))
        location, last_end, daily = t["initial_location"], None, {}
        for f in fs:
            fid = f["flight_instance_id"]
            dep, arr = utc(f["departure_utc"]), utc(f["arrival_utc"])
            require(f["aircraft_variant"] == t["variant"], f"{fid}: aircraft variant mismatch")
            for k in ("transfer_date", "service_entry_date", "available_from", "available_to"):
                if t[k] is None:
                    unknowns.append(f"{tid}.{k}: UNKNOWN")
            if t["service_entry_date"] and dep < utc(t["service_entry_date"]):
                errors.append(f"{fid}: before service entry")
            if t["transfer_date"] and t["service_entry_date"]:
                require(utc(t["transfer_date"]) <= utc(t["service_entry_date"]), f"{tid}: service before transfer")
            if t["available_from"] and dep < utc(t["available_from"]):
                errors.append(f"{fid}: before availability")
            if t["available_to"] and arr > utc(t["available_to"]):
                errors.append(f"{fid}: after availability")
            if location is None:
                unknowns.append(f"{fid}: starting location UNKNOWN")
            elif location != f["origin_airport"]:
                errors.append(f"{fid}: tail at {location}, required {f['origin_airport']}; include dated positioning leg")
            if last_end is not None:
                if t["turn_minutes"] is None:
                    unknowns.append(f"{fid}: turnaround UNKNOWN")
                elif dep < last_end + timedelta(minutes=t["turn_minutes"]):
                    errors.append(f"{fid}: overlapping flight/turnaround")
            for kind in ("maintenance_intervals", "reserve_intervals"):
                if t[kind] is None:
                    unknowns.append(f"{tid}.{kind}: UNKNOWN")
                else:
                    for interval in t[kind]:
                        if dep < utc(interval[1]) and arr > utc(interval[0]):
                            errors.append(f"{fid}: overlaps {kind}")
            crew = assignments[fid]["crew_id"]
            if t["crew_windows"] is None or crew is None:
                unknowns.append(f"{fid}: crew availability UNKNOWN")
            elif not any(w["crew_id"] == crew and utc(w["start"]) <= dep and arr <= utc(w["end"]) for w in t["crew_windows"]):
                errors.append(f"{fid}: outside explicit crew availability")
            # Split block hours at UTC midnight, not all into departure day.
            cur = dep
            while cur < arr:
                end = min(arr, cur.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
                day = cur.date().isoformat()
                daily[day] = daily.get(day, 0) + (end - cur).total_seconds() / 3600
                cur = end
            location, last_end = f["destination_airport"], arr
            rotations.append({"flight_instance_id": fid, "aircraft_id": tid, "crew_id": crew, "departure_utc": f["departure_utc"], "arrival_utc": f["arrival_utc"], "origin": f["origin_airport"], "destination": location})
        for day, hours in daily.items():
            if t["max_daily_block_hours"] is None:
                unknowns.append(f"{tid}: daily block limit UNKNOWN")
            elif hours > t["max_daily_block_hours"] + EPS:
                errors.append(f"{tid} {day}: daily block limit exceeded")
    # An explicitly named crew cannot be present on two aircraft at once.
    crews = {}
    for r in rotations:
        if r["crew_id"]:
            crews.setdefault(r["crew_id"], []).append(r)
    for cid, rows in crews.items():
        rows.sort(key=lambda x: utc(x["departure_utc"]))
        for a, b in zip(rows, rows[1:]):
            if utc(a["arrival_utc"]) > utc(b["departure_utc"]):
                errors.append(f"crew {cid}: simultaneous assignments")
            elif a["destination"] != b["origin"]:
                errors.append(f"crew {cid}: disconnected position")
    return {"status": "INFEASIBLE" if errors else "CONDITIONAL" if unknowns else "FEASIBLE_WITHIN_EXPLICIT_CONSTRAINTS", "errors": errors, "unknowns": sorted(set(unknowns)), "rotations": rotations, "unused_aircraft": sorted(set(tails) - {a["aircraft_id"] for a in assignments.values()}), "dispatch_ready": False}


def check_itineraries(bundle):
    flights = {f["flight_instance_id"]: f for f in bundle["flights"]}
    unknowns = []
    for p in bundle["products"]:
        fields(p, "product_id demand_pool_id month customer_segment kind owner gross_fare net_fare fare_unit duration_minutes frequency availability capacity legs departure_date min_connection_minutes max_connection_minutes revenue_weights committed_sales contract_only cash_profile assumption_id", "products")
        pid = p["product_id"]
        require(p["kind"] in ("air", "ground", "outside"), f"{pid}: invalid kind")
        require(p["fare_unit"] == "RUB/journey", f"{pid}: convert yield to journey fare explicitly")
        require(p["departure_date"][:7] == p["month"], f"{pid}: month/departure date mismatch")
        require(p["availability"] in (True, False, None), f"{pid}: availability needs boolean/null")
        for k in ("gross_fare", "net_fare", "duration_minutes", "frequency", "capacity", "committed_sales"):
            number(p[k], f"{pid}.{k}", 0, nullable=k != "committed_sales")
        if p["availability"] is None:
            unknowns.append(f"{pid}: commercial availability UNKNOWN")
        if p["kind"] == "air":
            require(p["legs"], f"{pid}: air journey requires dated physical legs")
        require(len(p["legs"]) == len(set(p["legs"])), f"{pid}: duplicate leg")
        if p["legs"]:
            require(len(p["revenue_weights"]) == len(p["legs"]), f"{pid}: revenue weights count")
            require(all(number(w, pid, 0) is not None for w in p["revenue_weights"]), pid)
            require(abs(sum(p["revenue_weights"]) - 1) < EPS, f"{pid}: revenue weights must sum to one")
        for i, fid in enumerate(p["legs"]):
            require(fid in flights, f"{pid}: absent dated leg {fid}")
            f = flights[fid]
            if i == 0:
                require(f["departure_utc"][:10] == p["departure_date"], f"{pid}: first UTC departure date mismatch")
            else:
                prev = flights[p["legs"][i - 1]]
                require(prev["destination_airport"] == f["origin_airport"], f"{pid}: disconnected itinerary")
                wait = (utc(f["departure_utc"]) - utc(prev["arrival_utc"])).total_seconds() / 60
                if p["min_connection_minutes"] is None or p["max_connection_minutes"] is None:
                    unknowns.append(f"{pid}: connection limits UNKNOWN")
                else:
                    require(p["min_connection_minutes"] <= wait <= p["max_connection_minutes"], f"{pid}: dated connection {wait} minutes outside limits")
    return unknowns
