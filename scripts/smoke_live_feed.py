"""Fetch the live TTC GTFS-RT binary alert feed and print a small summary."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PARSER_PATH = ROOT / "custom_components" / "ttc_service_alerts" / "parser.py"
FEED_URL = "https://gtfsrt.ttc.ca/alerts/all?format=binary"


def _load_parser():
    spec = importlib.util.spec_from_file_location("ttc_service_alerts_parser", PARSER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load parser at {PARSER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = _load_parser()
    request = Request(
        FEED_URL,
        headers={
            "Accept": "application/x-protobuf, application/octet-stream;q=0.9, */*;q=0.1",
            "User-Agent": "TTCHui-live-smoke/1.0",
        },
    )
    with urlopen(request, timeout=20) as response:
        payload = response.read()

    data = parser.parse_feed_bytes(payload, upcoming_hours=24, max_alerts=5)
    print(f"GTFS-RT version: {data.get('gtfs_realtime_version')}")
    print(f"Feed timestamp: {data.get('feed_timestamp')}")
    print(f"Active alerts: {data.get('active_count')}")
    print(f"Upcoming alerts: {data.get('upcoming_count')}")
    print(f"Subway status: {data.get('subway', {}).get('status')}")
    print(f"Surface routes affected: {data.get('surface', {}).get('active_route_count')}")

    for alert in data.get("active_alerts", [])[:3]:
        print(f"- {alert.get('effect_label')}: {alert.get('header')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

