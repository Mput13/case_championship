"""Small shared primitives; unknown is represented by JSON null, never by zero."""
import calendar
import hashlib
import json
import math
from datetime import datetime, timezone

VERSION = "P06-1.0"
EPS = 1e-8


class ContractError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ContractError(message)


def fields(row, names, location):
    missing = [k for k in names.split() if k not in row]
    require(not missing, f"{location}: missing {missing}")


def number(value, name, minimum=None, nullable=False):
    if value is None and nullable:
        return None
    require(isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value), f"{name}: finite number required (null is UNKNOWN)")
    if minimum is not None:
        require(value >= minimum, f"{name}: must be >= {minimum}")
    return float(value)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def utc(text):
    try:
        d = datetime.fromisoformat(text.replace("Z", "+00:00"))
        require(d.tzinfo is not None, f"UTC offset missing: {text}")
        return d.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError) as e:
        raise ContractError(f"Invalid dated timestamp: {text}") from e


def month(text):
    try:
        datetime.strptime(text[:7], "%Y-%m")
        return text[:7]
    except (ValueError, TypeError) as e:
        raise ContractError(f"Invalid month: {text}") from e


def months(start, end):
    a, b = month(start), month(end)
    require(a <= b, "reversed horizon")
    result = []
    while a <= b:
        result.append(a)
        y, m = map(int, a.split("-"))
        a = f"{y + (m == 12):04d}-{m % 12 + 1:02d}"
    return result


def dated(text):
    # A monthly payment is placed at month end only for the labelled lower bound.
    if len(text) == 7:
        y, m = map(int, month(text).split("-"))
        return f"{text}-{calendar.monthrange(y, m)[1]:02d}"
    datetime.strptime(text, "%Y-%m-%d")
    return text


def total(values):
    values = list(values)
    return None if any(x is None for x in values) else sum(values)


def difference(a, b):
    return None if a is None or b is None else a - b


def unique(rows, key, label):
    out = {}
    for r in rows:
        require(key in r, f"{label}: missing {key}")
        require(r[key] not in out, f"{label}: duplicate {r[key]}")
        out[r[key]] = r
    return out


def pool_key(row):
    return (row["demand_pool_id"], row["month"], row["customer_segment"])
