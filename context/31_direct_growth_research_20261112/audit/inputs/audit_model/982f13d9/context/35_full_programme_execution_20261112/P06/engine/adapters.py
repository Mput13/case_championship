"""Producer adapters preserve evidence state; no automatic factual admission."""
import csv
from pathlib import Path
from .common import number, require


def yield_to_fare(rub_per_pax_km, distance_km, distance_basis):
    require(distance_basis in ("journey_distance_km", "sum_physical_legs_km"), "explicit yield distance basis required")
    return number(rub_per_pax_km, "yield RUB/pax-km", 0) * number(distance_km, "distance km", 0)


def csv_rows(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def source_number(value):
    return None if value in (None, "", "UNKNOWN", "unknown", "null") else number(float(value), "source value")


def p02_evidence(calendar_rows, product_rows, correction_lineage):
    """Published station-pair offers are never turned into dated seat arcs here."""
    conflicts = [r["schedule_instance_id"] for r in calendar_rows if r["clock_conflict"].lower() == "true"]
    unresolved = [r["schedule_instance_id"] for r in calendar_rows if r.get("seat_inventory_usable", "false").lower() != "true" or r.get("physical_inventory_id") in (None, "UNKNOWN", "")]
    return {"source_rows": len(calendar_rows), "product_rows": len(product_rows), "clock_conflicts": conflicts, "unknown_physical_inventory_count": len(unresolved), "admitted_engine_flights": [], "admission_status": "SOURCE_EXPORT_ONLY_REQUIRES_PINNED_PHYSICAL_AND_COMMERCIAL_MAPPING", "correction_lineage": correction_lineage, "required_fields": ["dated UTC adjacent legs", "operator and physical flight id", "shared saleable inventory", "commercial availability", "explicit source validity dates", "forecast transfer assumption_id"], "summer_extension": "NOT_PERFORMED", "RT581": "KZN-GOJ-CEK published ordered pattern only", "RT651": "KZN-RMZ-OMS published ordered pattern only"}


def p04_rate_catalog(rows):
    return [{"cost_id": r["cost_id"], "reference_value": source_number(r.get("value")), "future_rate": None, "unit": r["unit"], "driver": r["driver"], "price_year": r["price_year"], "currency": r["currency"], "source_id": r["source_id"], "assumption_id": r["assumption_id"], "range_basis": r["range_basis"], "status": r["status"], "admission": "REFERENCE_ONLY_REQUIRE_EXPLICIT_FORECAST_RATE_SELECTION_AND_DRIVER"} for r in rows]


def p04_event(row, selection, quantity, event_id, owner, accrual_month, category):
    """Explicit scenario rate selection. UNKNOWN retained; no 2026->2028 carry."""
    require(selection["cost_id"] == row["cost_id"], "rate selection cost_id mismatch")
    require(selection["assumption_id"] and selection["basis"] and selection["selected_by"], "scenario transfer needs registered selection")
    require(selection["currency"] == "RUB", "normalize FX before engine")
    rate = number(selection["rate"], "scenario rate", 0, nullable=True)
    q = number(quantity, "quantity", 0, nullable=True)
    return {"economic_event_id": event_id, "owner": owner, "category": category, "scope": "affected_business", "driver_unit": row["driver"], "quantity": q, "rate": rate, "amount": None if q is None or rate is None else q * rate, "currency": "RUB", "price_year": selection["price_year"], "fx_policy": selection["fx_policy"], "accrual_month": accrual_month, "noncash": selection["noncash"], "avoidability": selection["avoidability"], "shared_event_id": event_id, "source_id": row["source_id"], "assumption_id": selection["assumption_id"], "reference_assumption_id": row["assumption_id"], "cash_plan_status": "unknown", "source_cost_id": row["cost_id"]}
