"""GTFS-RT parsing and summarization for TTC service alerts."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
import re
from typing import Any

from google.protobuf.message import DecodeError
from google.transit import gtfs_realtime_pb2

SUBWAY_LINES: dict[str, str] = {
    "1": "Line 1 Yonge-University",
    "2": "Line 2 Bloor-Danforth",
    "4": "Line 4 Sheppard",
    "5": "Line 5 Eglinton",
}

SUBWAY_LINE_PATTERNS: dict[str, re.Pattern[str]] = {
    "1": re.compile(r"\b(line\s*1|yonge-university)\b", re.I),
    "2": re.compile(r"\b(line\s*2|bloor-danforth)\b", re.I),
    "4": re.compile(r"\b(line\s*4|sheppard)\b", re.I),
    "5": re.compile(r"\b(line\s*5|eglinton line)\b", re.I),
}

STREETCAR_ROUTES = {
    "301",
    "304",
    "306",
    "307",
    "310",
    "501",
    "503",
    "504",
    "505",
    "506",
    "507",
    "508",
    "509",
    "510",
    "511",
    "512",
}

EFFECT_LABELS: dict[str, str] = {
    "NO_SERVICE": "No service",
    "REDUCED_SERVICE": "Reduced service",
    "SIGNIFICANT_DELAYS": "Delays",
    "DETOUR": "Detour",
    "MODIFIED_SERVICE": "Modified service",
    "ADDITIONAL_SERVICE": "Additional service",
    "STOP_MOVED": "Stop moved",
    "ACCESSIBILITY_ISSUE": "Accessibility issue",
    "UNKNOWN_EFFECT": "Service alert",
    "OTHER_EFFECT": "Service alert",
}

CAUSE_LABELS: dict[str, str] = {
    "ACCIDENT": "Accident",
    "CONSTRUCTION": "Construction",
    "DEMONSTRATION": "Demonstration",
    "HOLIDAY": "Holiday",
    "MAINTENANCE": "Maintenance",
    "MEDICAL_EMERGENCY": "Medical emergency",
    "OTHER_CAUSE": "Other",
    "POLICE_ACTIVITY": "Police activity",
    "STRIKE": "Strike",
    "TECHNICAL_PROBLEM": "Technical problem",
    "UNKNOWN_CAUSE": "Unknown",
    "WEATHER": "Weather",
}

EFFECT_SEVERITY: dict[str, int] = {
    "NO_SERVICE": 50,
    "SIGNIFICANT_DELAYS": 40,
    "REDUCED_SERVICE": 35,
    "DETOUR": 30,
    "MODIFIED_SERVICE": 25,
    "STOP_MOVED": 20,
    "ACCESSIBILITY_ISSUE": 20,
    "ADDITIONAL_SERVICE": 10,
    "OTHER_EFFECT": 10,
    "UNKNOWN_EFFECT": 10,
}


def parse_feed_bytes(
    payload: bytes,
    *,
    now: datetime | None = None,
    route_filter: Iterable[str] | None = None,
    upcoming_hours: int = 24,
    max_alerts: int = 40,
) -> dict[str, Any]:
    """Parse binary GTFS-RT feed bytes into Home Assistant-friendly data."""
    feed = gtfs_realtime_pb2.FeedMessage()
    try:
        feed.ParseFromString(payload)
    except DecodeError:
        raise
    return parse_feed_message(
        feed,
        now=now,
        route_filter=route_filter,
        upcoming_hours=upcoming_hours,
        max_alerts=max_alerts,
    )


def parse_feed_message(
    feed: gtfs_realtime_pb2.FeedMessage,
    *,
    now: datetime | None = None,
    route_filter: Iterable[str] | None = None,
    upcoming_hours: int = 24,
    max_alerts: int = 40,
) -> dict[str, Any]:
    """Parse a FeedMessage into current and upcoming alert summaries."""
    now = _normalize_now(now)
    route_filter_set = {str(route).strip().upper() for route in route_filter or [] if str(route).strip()}
    upcoming_cutoff = now + timedelta(hours=max(1, int(upcoming_hours)))

    active_alerts: list[dict[str, Any]] = []
    upcoming_alerts: list[dict[str, Any]] = []

    for entity in feed.entity:
        if not entity.HasField("alert"):
            continue
        parsed = _parse_alert_entity(entity, now)
        if parsed["period_state"] == "expired":
            continue
        if parsed["period_state"] == "upcoming" and parsed.get("start_dt") and parsed["start_dt"] > upcoming_cutoff:
            continue
        if route_filter_set and parsed["routes"] and not (route_filter_set & set(parsed["routes"])):
            parsed["tracked"] = False
        else:
            parsed["tracked"] = bool(route_filter_set & set(parsed["routes"])) if route_filter_set else True

        public_alert = _public_alert(parsed)
        if parsed["period_state"] == "active":
            active_alerts.append(public_alert)
        else:
            upcoming_alerts.append(public_alert)

    active_alerts.sort(key=_alert_sort_key)
    upcoming_alerts.sort(key=_alert_sort_key)

    tracked_active = [alert for alert in active_alerts if alert.get("tracked")]
    tracked_upcoming = [alert for alert in upcoming_alerts if alert.get("tracked")]

    subway = _subway_summary(active_alerts, upcoming_alerts)
    surface = _surface_summary(active_alerts, upcoming_alerts)
    accessibility = _accessibility_summary(active_alerts, upcoming_alerts)

    feed_timestamp = None
    if feed.header.timestamp:
        feed_timestamp = datetime.fromtimestamp(feed.header.timestamp, tz=timezone.utc).isoformat()

    return {
        "gtfs_realtime_version": feed.header.gtfs_realtime_version,
        "feed_timestamp": feed_timestamp,
        "fetched_at": now.isoformat(),
        "active_count": len(active_alerts),
        "upcoming_count": len(upcoming_alerts),
        "total_count": len(active_alerts) + len(upcoming_alerts),
        "highest_status": _status_from_alerts(active_alerts),
        "counts_by_mode": dict(Counter(alert["mode"] for alert in active_alerts)),
        "counts_by_effect": dict(Counter(alert["effect"] for alert in active_alerts)),
        "active_alerts": active_alerts[:max_alerts],
        "upcoming_alerts": upcoming_alerts[:max_alerts],
        "active_alerts_truncated": max(0, len(active_alerts) - max_alerts),
        "upcoming_alerts_truncated": max(0, len(upcoming_alerts) - max_alerts),
        "subway": subway,
        "surface": surface,
        "accessibility": accessibility,
        "tracked": {
            "enabled": bool(route_filter_set),
            "routes": sorted(route_filter_set),
            "active_count": len(tracked_active),
            "upcoming_count": len(tracked_upcoming),
            "active_alerts": tracked_active[:max_alerts],
            "upcoming_alerts": tracked_upcoming[:max_alerts],
            "status": _status_from_alerts(tracked_active),
        },
    }


def normalize_route_filter(raw: str | Iterable[str] | None) -> list[str]:
    """Normalize comma, semicolon, or whitespace-separated route filters."""
    if raw is None:
        return []
    if isinstance(raw, str):
        parts = re.split(r"[\s,;]+", raw)
    else:
        parts = [str(part) for part in raw]
    return sorted({part.strip().upper() for part in parts if part.strip()})


def _parse_alert_entity(entity: gtfs_realtime_pb2.FeedEntity, now: datetime) -> dict[str, Any]:
    alert = entity.alert
    header = _translated_text(alert.header_text)
    description = _translated_text(alert.description_text)
    url = _translated_text(alert.url)
    routes = sorted({selector.route_id.upper() for selector in alert.informed_entity if selector.route_id})
    stops = sorted({selector.stop_id for selector in alert.informed_entity if selector.stop_id})
    effect = _enum_name(gtfs_realtime_pb2.Alert.Effect, alert.effect, "UNKNOWN_EFFECT")
    cause = _enum_name(gtfs_realtime_pb2.Alert.Cause, alert.cause, "UNKNOWN_CAUSE")
    start_dt, end_dt, period_state = _period_state(alert.active_period, now)
    mode = _classify_mode(routes, effect, header)
    route_labels = [_route_label(route, header) for route in routes]

    return {
        "id": entity.id,
        "header": _clean_text(header) or "TTC service alert",
        "description": _clean_text(description),
        "url": url,
        "routes": routes,
        "route_labels": route_labels,
        "stops": stops,
        "effect": effect,
        "effect_label": EFFECT_LABELS.get(effect, effect.replace("_", " ").title()),
        "cause": cause,
        "cause_label": CAUSE_LABELS.get(cause, cause.replace("_", " ").title()),
        "severity": EFFECT_SEVERITY.get(effect, 10),
        "mode": mode,
        "period_state": period_state,
        "status_label": "Active" if period_state == "active" else "Upcoming",
        "start_dt": start_dt,
        "end_dt": end_dt,
    }


def _public_alert(alert: dict[str, Any]) -> dict[str, Any]:
    public = dict(alert)
    start_dt = public.pop("start_dt", None)
    end_dt = public.pop("end_dt", None)
    public["start"] = start_dt.isoformat() if start_dt else None
    public["end"] = end_dt.isoformat() if end_dt else None
    public["stops"] = public["stops"][:50]
    return public


def _subway_summary(
    active_alerts: list[dict[str, Any]],
    upcoming_alerts: list[dict[str, Any]],
) -> dict[str, Any]:
    route_ids = set(SUBWAY_LINES)
    for alert in active_alerts + upcoming_alerts:
        for route in alert["routes"]:
            if _is_subway_route(route, alert["header"]):
                route_ids.add(route)

    lines = []
    for route_id in sorted(route_ids, key=lambda route: int(route) if route.isdigit() else route):
        active = [alert for alert in active_alerts if route_id in alert["routes"] and _is_subway_route(route_id, alert["header"])]
        upcoming = [alert for alert in upcoming_alerts if route_id in alert["routes"] and _is_subway_route(route_id, alert["header"])]
        lines.append(
            {
                "route_id": route_id,
                "name": SUBWAY_LINES.get(route_id, f"Line {route_id}"),
                "status": _status_from_alerts(active),
                "active_count": len(active),
                "upcoming_count": len(upcoming),
                "alerts": active[:8],
                "upcoming_alerts": upcoming[:8],
            }
        )

    active_subway = [alert for alert in active_alerts if alert["mode"] == "subway"]
    upcoming_subway = [alert for alert in upcoming_alerts if alert["mode"] == "subway"]
    return {
        "status": _status_from_alerts(active_subway),
        "active_count": len(active_subway),
        "upcoming_count": len(upcoming_subway),
        "lines": lines,
        "alerts": active_subway[:20],
        "upcoming_alerts": upcoming_subway[:20],
    }


def _surface_summary(
    active_alerts: list[dict[str, Any]],
    upcoming_alerts: list[dict[str, Any]],
) -> dict[str, Any]:
    active_surface = [alert for alert in active_alerts if alert["mode"] in {"bus", "streetcar", "surface"}]
    upcoming_surface = [alert for alert in upcoming_alerts if alert["mode"] in {"bus", "streetcar", "surface"}]
    routes = _route_summaries(active_surface, upcoming_surface)
    bus_routes = [route for route in routes if route["mode"] == "bus"]
    streetcar_routes = [route for route in routes if route["mode"] == "streetcar"]
    return {
        "status": _status_from_alerts(active_surface),
        "active_count": len(active_surface),
        "upcoming_count": len(upcoming_surface),
        "active_route_count": sum(1 for route in routes if route["active_count"]),
        "routes": routes[:60],
        "bus_routes": bus_routes[:40],
        "streetcar_routes": streetcar_routes[:30],
        "alerts": active_surface[:25],
        "upcoming_alerts": upcoming_surface[:25],
    }


def _accessibility_summary(
    active_alerts: list[dict[str, Any]],
    upcoming_alerts: list[dict[str, Any]],
) -> dict[str, Any]:
    active = [alert for alert in active_alerts if alert["mode"] == "accessibility"]
    upcoming = [alert for alert in upcoming_alerts if alert["mode"] == "accessibility"]
    return {
        "status": _status_from_alerts(active),
        "active_count": len(active),
        "upcoming_count": len(upcoming),
        "alerts": active[:25],
        "upcoming_alerts": upcoming[:25],
    }


def _route_summaries(
    active_alerts: list[dict[str, Any]],
    upcoming_alerts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_route: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: {"active": [], "upcoming": []})
    for alert in active_alerts:
        for route in alert["routes"]:
            by_route[route]["active"].append(alert)
    for alert in upcoming_alerts:
        for route in alert["routes"]:
            by_route[route]["upcoming"].append(alert)

    summaries = []
    for route, grouped in by_route.items():
        active = grouped["active"]
        upcoming = grouped["upcoming"]
        sample = (active or upcoming)[0]
        mode = "streetcar" if route in STREETCAR_ROUTES else "bus"
        summaries.append(
            {
                "route_id": route,
                "name": _route_label(route, sample["header"]),
                "mode": mode,
                "status": _status_from_alerts(active),
                "active_count": len(active),
                "upcoming_count": len(upcoming),
                "alerts": active[:5],
                "upcoming_alerts": upcoming[:5],
            }
        )
    summaries.sort(key=lambda item: (-_status_severity(item["status"]), _route_sort_value(item["route_id"])))
    return summaries


def _status_from_alerts(alerts: list[dict[str, Any]]) -> str:
    if not alerts:
        return "Normal service"
    worst = max(alerts, key=lambda alert: alert.get("severity", 0))
    return worst.get("effect_label") or "Service alert"


def _status_severity(status: str) -> int:
    for effect, label in EFFECT_LABELS.items():
        if label == status:
            return EFFECT_SEVERITY.get(effect, 0)
    return 0


def _classify_mode(routes: list[str], effect: str, header: str) -> str:
    if effect == "ACCESSIBILITY_ISSUE":
        return "accessibility"
    if routes and all(_is_subway_route(route, header) for route in routes):
        return "subway"
    if routes and all(route in STREETCAR_ROUTES for route in routes):
        return "streetcar"
    if routes:
        return "bus"
    if re.search(r"\b(elevator|escalator|accessible|accessibility)\b", header, re.I):
        return "accessibility"
    return "other"


def _is_subway_route(route: str, header: str) -> bool:
    pattern = SUBWAY_LINE_PATTERNS.get(route)
    if not pattern:
        return False
    if route in {"1", "2", "4"}:
        return True
    return bool(pattern.search(header))


def _route_label(route: str, header: str) -> str:
    if _is_subway_route(route, header):
        return SUBWAY_LINES.get(route, f"Line {route}")
    header = _clean_text(header)
    prefix_match = re.match(rf"^{re.escape(route)}\s+([^:,-]+)", header)
    if prefix_match:
        return f"{route} {prefix_match.group(1).strip()}"
    return f"Route {route}"


def _translated_text(field: Any) -> str:
    translations = list(getattr(field, "translation", []))
    if not translations:
        return ""
    for language in ("en", "en-US", "en-CA", ""):
        for translation in translations:
            if translation.language == language:
                return translation.text
    return translations[0].text


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _enum_name(enum_type: Any, value: int, fallback: str) -> str:
    try:
        return enum_type.Name(value)
    except ValueError:
        return fallback


def _period_state(periods: Iterable[Any], now: datetime) -> tuple[datetime | None, datetime | None, str]:
    converted = []
    for period in periods:
        start = datetime.fromtimestamp(period.start, tz=timezone.utc) if period.start else None
        end = datetime.fromtimestamp(period.end, tz=timezone.utc) if period.end else None
        converted.append((start, end))

    if not converted:
        return None, None, "active"

    active = [
        (start, end)
        for start, end in converted
        if (start is None or start <= now) and (end is None or end >= now)
    ]
    if active:
        starts = [start for start, _ in active if start is not None]
        ends = [end for _, end in active if end is not None]
        return min(starts) if starts else None, max(ends) if ends else None, "active"

    future = [(start, end) for start, end in converted if start and start > now]
    if future:
        future.sort(key=lambda item: item[0] or datetime.max.replace(tzinfo=timezone.utc))
        return future[0][0], future[0][1], "upcoming"

    starts = [start for start, _ in converted if start is not None]
    ends = [end for _, end in converted if end is not None]
    return min(starts) if starts else None, max(ends) if ends else None, "expired"


def _normalize_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _alert_sort_key(alert: dict[str, Any]) -> tuple[int, str, str]:
    return (-int(alert.get("severity", 0)), str(alert.get("start") or ""), str(alert.get("id") or ""))


def _route_sort_value(route: str) -> tuple[int, str]:
    if route.isdigit():
        return int(route), route
    return 99999, route

