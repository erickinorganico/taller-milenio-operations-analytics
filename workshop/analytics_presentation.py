"""Pure presentation helpers for the management analytics dashboard.

Inputs are the result of ``build_analytics_dashboard`` and rows already read
from its selected immutable snapshot. This module performs no database access.
"""

from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation


_PLOT = {"left": 48.0, "right": 748.0, "top": 18.0, "bottom": 150.0}
_MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
_STATUS_LABELS = {
    "intake": "Recepción", "inspection": "Inspección", "awaiting_approval": "Espera autorización",
    "approved": "Autorizada", "in_progress": "En trabajo", "waiting_parts": "Espera refacciones",
    "quality": "Calidad", "ready": "Lista", "delivered": "Entregada", "cancelled": "Cancelada",
}


def _decimal(value):
    """Return finite Decimal input, treating absent or malformed values as zero."""
    try:
        number = Decimal(str(value if value is not None else 0))
        return number if number.is_finite() else Decimal(0)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(0)


def _coordinate(value):
    """Format deterministic SVG coordinates without locale-specific separators."""
    number = float(value)
    if not (number == number and abs(number) != float("inf")):
        return "0"
    return f"{number:.2f}".rstrip("0").rstrip(".")


def _points_string(points, x_key="x", y_key="y"):
    return " ".join(f"{_coordinate(point[x_key])},{_coordinate(point[y_key])}" for point in points)


def _x_positions(count, left, right):
    if count <= 1:
        return [(left + right) / 2]
    return [left + (right - left) * index / (count - 1) for index in range(count)]


def _date_label(value):
    try:
        parsed = date.fromisoformat(str(value))
        return f"{_MONTHS[parsed.month - 1]} {parsed.day}"
    except (TypeError, ValueError):
        return str(value or "")


def _nice_ticks(maximum, count=4):
    """Create readable nonnegative decimal ticks with a stable zero baseline."""
    maximum = max(Decimal(0), _decimal(maximum))
    if maximum == 0:
        return [Decimal(0)]
    rough = maximum / Decimal(count)
    exponent = rough.adjusted()
    magnitude = Decimal(10) ** exponent
    fraction = rough / magnitude
    step_factor = Decimal(1) if fraction <= 1 else Decimal(2) if fraction <= 2 else Decimal(5) if fraction <= 5 else Decimal(10)
    step = step_factor * magnitude
    ceiling = ((maximum / step).to_integral_value(rounding="ROUND_CEILING")) * step
    ticks = []
    current = Decimal(0)
    while current <= ceiling and len(ticks) <= count + 2:
        ticks.append(current)
        current += step
    return ticks


def _number_text(value):
    value = _decimal(value)
    return format(value, "f")


def _amount_label(value):
    """Compact, deterministic peso labels for the SVG axis."""
    amount = _decimal(value)
    magnitude = abs(amount)
    if magnitude >= Decimal("1000000"):
        return f"MXN {amount / Decimal('1000000'):.1f} M"
    if magnitude >= Decimal("1000"):
        return f"MXN {amount / Decimal('1000'):.1f} mil"
    return f"MXN {amount:,.0f}"


def _sparkline(trend, metric):
    field = {"opened": "opened", "delivered": "delivered", "invoiced": "invoiced_mxn", "payments": "payments_mxn"}[metric]
    values = [_decimal(row.get(field)) for row in trend]
    maximum = max(values, default=Decimal(0))
    points = []
    for x, row, value in zip(_x_positions(len(trend), 0, 100), trend, values):
        y = 28 - float(value / maximum) * 24 if maximum > 0 else 28
        points.append({"x": x, "y": y, "day": row.get("day", ""), "value": _number_text(value)})
    return {"sparkline": points, "sparkline_points": _points_string(points),
            "trend_value": _number_text(values[-1]) if values else "0"}


def _chart(trend):
    left, right = _PLOT["left"], _PLOT["right"]
    top, bottom = _PLOT["top"], _PLOT["bottom"]
    maximum = max((max(_decimal(row.get("invoiced_mxn")), _decimal(row.get("payments_mxn")))
                   for row in trend), default=Decimal(0))
    ticks = _nice_ticks(maximum)
    scale_max = ticks[-1] if ticks and ticks[-1] else Decimal(1)
    y_for = lambda value: bottom - float(_decimal(value) / scale_max) * (bottom - top)
    points = []
    for x, row in zip(_x_positions(len(trend), left, right), trend):
        invoice = _number_text(row.get("invoiced_mxn"))
        payment = _number_text(row.get("payments_mxn"))
        points.append({"x": x, "day": row.get("day", ""), "invoiced_mxn": invoice,
                       "payments_mxn": payment, "invoice_y": y_for(invoice), "payment_y": y_for(payment)})
    series = {}
    for key, y_key in (("invoice", "invoice_y"), ("payment", "payment_y")):
        line = [{"x": item["x"], "y": item[y_key]} for item in points]
        area = [{"x": left if not points else points[0]["x"], "y": bottom}, *line,
                {"x": right if not points else points[-1]["x"], "y": bottom}]
        series[key] = {"points": _points_string(line), "area": _points_string(area)}
    y_ticks = [{"y": y_for(value), "value": _number_text(value), "label": _amount_label(value)} for value in ticks]
    x_ticks = []
    if points:
        indices = sorted(set(round(i * (len(points) - 1) / min(4, len(points) - 1))
                             for i in range(min(4, len(points) - 1) + 1))) if len(points) > 1 else [0]
        x_ticks = [{"x": points[index]["x"], "label": _date_label(points[index]["day"])} for index in indices]
    return {"view_box": "0 0 760 190", "series": series, "points": points,
            "y_ticks": y_ticks, "x_ticks": x_ticks, "plot": dict(_PLOT)}


def _snapshot_rows(snapshot):
    """Accept materialized mart records or a mapping of mart names to rows."""
    if snapshot is None:
        return []
    if isinstance(snapshot, dict):
        journeys = snapshot.get("order_journeys", [])
        if isinstance(journeys, dict):
            return list(journeys.values())
        return list(journeys)
    result = []
    for record in snapshot:
        if isinstance(record, dict):
            if record.get("mart") == "order_journeys":
                result.append(record.get("data", record))
        elif getattr(record, "mart", None) == "order_journeys":
            result.append(getattr(record, "data", {}))
    return result


def build_presentation(data, snapshot):
    """Build chart geometry, KPI sparklines, and period/current breakdowns.

    ``snapshot`` is a materialized iterable of ``{mart, data}`` records (or a
    mapping with an ``order_journeys`` list). Current status counts use this
    immutable cut; service counts use the already period-filtered dashboard
    ranking and count authorized order-service occurrences, not unique orders
    across all services.
    """
    data = data or {}
    trend = data.get("trend") or []
    metrics = ("opened", "delivered", "invoiced", "payments")
    cards = {metric: _sparkline(trend, metric) for metric in metrics}

    segment = (data.get("filters") or {}).get("segment", "all")
    journeys = [row for row in _snapshot_rows(snapshot)
                if segment == "all" or row.get("customer_kind") == segment]
    statuses = Counter(str(row.get("status") or "unknown") for row in journeys)
    total_orders = sum(statuses.values())
    order_states = [{"key": key, "label": _STATUS_LABELS.get(key, key.replace("_", " ").capitalize()),
                     "count": count, "percent": round(count * 100 / total_orders, 2) if total_orders else 0}
                    for key, count in sorted(statuses.items(), key=lambda item: (-item[1], item[0]))]

    services = (data.get("rankings") or {}).get("services") or []
    service_counts = [(str(row.get("description") or "Servicio"),
                       max(0, int(_decimal(row.get("authorized_orders"))))) for row in services]
    occurrences = sum(count for _, count in service_counts)
    service_mix = [{"label": label, "count": count,
                    "percent": round(count * 100 / occurrences, 2) if occurrences else 0}
                   for label, count in service_counts]
    return {"cards": cards, "chart": _chart(trend), "order_states": order_states,
            "service_mix": service_mix,
            "order_states_as_of": (data.get("snapshot") or {}).get("recorded_at"),
            "order_states_scope": "Estado actual de las órdenes al corte seleccionado; independiente del periodo."}
