"""Constants for the TTC Service Alerts integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "ttc_service_alerts"
PLATFORMS: list[Platform] = [Platform.SENSOR]

CONF_NAME = "name"
CONF_FEED = "feed"
CONF_POLL_SECONDS = "poll_seconds"
CONF_ROUTE_FILTER = "route_filter"
CONF_UPCOMING_HOURS = "upcoming_hours"
CONF_MAX_ALERTS = "max_alerts"

DEFAULT_NAME = "TTC"
DEFAULT_FEED = "all"
DEFAULT_POLL_SECONDS = 60
DEFAULT_UPCOMING_HOURS = 24
DEFAULT_MAX_ALERTS = 40

FEED_URLS: dict[str, str] = {
    "all": "https://gtfsrt.ttc.ca/alerts/all?format=binary",
    "subway": "https://gtfsrt.ttc.ca/alerts/subway?format=binary",
    "bus": "https://gtfsrt.ttc.ca/alerts/bus?format=binary",
    "streetcar": "https://gtfsrt.ttc.ca/alerts/streetcar?format=binary",
    "accessibility": "https://gtfsrt.ttc.ca/alerts/accessibility?format=binary",
    "stops": "https://gtfsrt.ttc.ca/alerts/stops?format=binary",
}

FEED_LABELS: dict[str, str] = {
    "all": "All service alerts",
    "subway": "Subway alerts",
    "bus": "Bus alerts",
    "streetcar": "Streetcar alerts",
    "accessibility": "Accessibility alerts",
    "stops": "Inactive stop alerts",
}

SERVICE_REFRESH = "refresh"

ATTR_ATTRIBUTION = "attribution"
ATTRIBUTION = "Contains information licensed under the Open Government Licence - Toronto."

