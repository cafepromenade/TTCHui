from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sys

from google.transit import gtfs_realtime_pb2

ROOT = Path(__file__).resolve().parents[1]
PARSER_PATH = ROOT / "custom_components" / "ttc_service_alerts" / "parser.py"


def _load_parser():
    spec = importlib.util.spec_from_file_location("ttc_service_alerts_parser_test", PARSER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load parser at {PARSER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


parser = _load_parser()


def _translated(field, text: str) -> None:
    item = field.translation.add()
    item.text = text
    item.language = "en"


def _add_alert(
    feed,
    alert_id: str,
    *,
    route_id: str | None,
    stop_id: str | None = None,
    effect: str,
    header: str,
    start: datetime | None = None,
    end: datetime | None = None,
):
    entity = feed.entity.add()
    entity.id = alert_id
    alert = entity.alert
    if start or end:
        period = alert.active_period.add()
        if start:
            period.start = int(start.timestamp())
        if end:
            period.end = int(end.timestamp())
    if route_id or stop_id:
        informed = alert.informed_entity.add()
        if route_id:
            informed.route_id = route_id
        if stop_id:
            informed.stop_id = stop_id
    alert.effect = getattr(gtfs_realtime_pb2.Alert, effect)
    _translated(alert.header_text, header)
    return alert


def test_parser_summarizes_active_upcoming_and_expired_alerts():
    now = datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc)
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = int(now.timestamp())

    _add_alert(
        feed,
        "active-subway",
        route_id="1",
        effect="SIGNIFICANT_DELAYS",
        header="Line 1 Yonge-University: Delays southbound due to a signal problem.",
        start=now - timedelta(minutes=5),
    )
    _add_alert(
        feed,
        "upcoming-bus",
        route_id="90",
        effect="DETOUR",
        header="90 Vaughan: Detour due to road work.",
        start=now + timedelta(hours=2),
        end=now + timedelta(hours=4),
    )
    _add_alert(
        feed,
        "expired-streetcar",
        route_id="512",
        effect="NO_SERVICE",
        header="512 St Clair: No service due to blocked track.",
        start=now - timedelta(hours=4),
        end=now - timedelta(hours=2),
    )

    data = parser.parse_feed_message(feed, now=now, upcoming_hours=24)

    assert data["active_count"] == 1
    assert data["upcoming_count"] == 1
    assert data["subway"]["status"] == "Delays"
    line_1 = data["subway"]["line_statuses"]["1"]
    assert line_1["service_status"] == "Delays"
    assert line_1["active_count"] == 1
    assert line_1["delay_count"] == 1
    assert line_1["delay_alerts"][0]["summary"] == "Line 1 Yonge-University: Delays southbound due to a signal problem."
    assert line_1["delay_summary"] == "Line 1 Yonge-University: Delays southbound due to a signal problem."
    assert data["subway"]["line_statuses"]["2"]["service_status"] == "Normal service"
    assert data["surface"]["upcoming_count"] == 1
    assert not any(alert["id"] == "expired-streetcar" for alert in data["active_alerts"])


def test_parser_groups_accessibility_and_route_filters():
    now = datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc)
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = int(now.timestamp())

    _add_alert(
        feed,
        "access",
        route_id=None,
        stop_id="3923",
        effect="ACCESSIBILITY_ISSUE",
        header="St Clair: Elevator out of service while we perform maintenance.",
        start=now - timedelta(minutes=1),
    )
    _add_alert(
        feed,
        "tracked",
        route_id="501",
        effect="MODIFIED_SERVICE",
        header="501 Queen: Route change due to construction.",
        start=now - timedelta(minutes=1),
    )
    _add_alert(
        feed,
        "not-tracked",
        route_id="90",
        effect="SIGNIFICANT_DELAYS",
        header="90 Vaughan: Delays near St Clair.",
        start=now - timedelta(minutes=1),
    )

    data = parser.parse_feed_message(feed, now=now, route_filter=["501"], upcoming_hours=24)

    assert data["active_count"] == 3
    assert data["accessibility"]["active_count"] == 1
    assert data["surface"]["active_route_count"] == 2
    assert data["tracked"]["enabled"] is True
    assert data["tracked"]["active_count"] == 1
    assert data["tracked"]["active_alerts"][0]["id"] == "tracked"
