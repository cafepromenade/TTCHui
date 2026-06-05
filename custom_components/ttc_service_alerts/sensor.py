"""Sensors for TTC Service Alerts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_ATTRIBUTION, DOMAIN
from .coordinator import TtcServiceAlertsCoordinator
from .parser import SUBWAY_LINES


@dataclass(frozen=True, kw_only=True)
class TtcSensorDescription(SensorEntityDescription):
    """Sensor description with value and attribute extractors."""

    value: Callable[[dict[str, Any]], Any] = lambda data: None
    attrs: Callable[[dict[str, Any]], dict[str, Any]] = lambda data: {}


def _base_attrs(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "feed": data.get("feed"),
        "source_url": data.get("source_url"),
        "gtfs_realtime_version": data.get("gtfs_realtime_version"),
        "feed_timestamp": data.get("feed_timestamp"),
        "fetched_at": data.get("fetched_at"),
        "upcoming_hours": data.get("upcoming_hours"),
        ATTR_ATTRIBUTION: data.get("attribution"),
    }


def _service_attrs(data: dict[str, Any]) -> dict[str, Any]:
    return {
        **_base_attrs(data),
        "active_count": data.get("active_count", 0),
        "upcoming_count": data.get("upcoming_count", 0),
        "total_count": data.get("total_count", 0),
        "highest_status": data.get("highest_status"),
        "counts_by_mode": data.get("counts_by_mode", {}),
        "counts_by_effect": data.get("counts_by_effect", {}),
        "active_alerts": data.get("active_alerts", []),
        "upcoming_alerts": data.get("upcoming_alerts", []),
        "active_alerts_truncated": data.get("active_alerts_truncated", 0),
        "upcoming_alerts_truncated": data.get("upcoming_alerts_truncated", 0),
    }


def _nested_attrs(key: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def attrs(data: dict[str, Any]) -> dict[str, Any]:
        section = data.get(key, {})
        return {**_base_attrs(data), **section}

    return attrs


def _tracked_attrs(data: dict[str, Any]) -> dict[str, Any]:
    tracked = data.get("tracked", {})
    return {**_base_attrs(data), **tracked}


def _line(data: dict[str, Any], route_id: str) -> dict[str, Any]:
    return data.get("subway", {}).get("line_statuses", {}).get(
        route_id,
        {
            "route_id": route_id,
            "name": SUBWAY_LINES.get(route_id, f"Line {route_id}"),
            "status": "Normal service",
            "service_status": "Normal service",
            "active_count": 0,
            "upcoming_count": 0,
            "delay_count": 0,
            "upcoming_delay_count": 0,
            "delay_summary": "No current delay info.",
            "upcoming_delay_summary": "No current delay info.",
            "delay_alerts": [],
            "upcoming_delay_alerts": [],
            "alerts": [],
            "upcoming_alerts": [],
        },
    )


def _line_value(route_id: str) -> Callable[[dict[str, Any]], Any]:
    def value(data: dict[str, Any]) -> Any:
        return _line(data, route_id).get("service_status", "Normal service")

    return value


def _line_attrs(route_id: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def attrs(data: dict[str, Any]) -> dict[str, Any]:
        return {**_base_attrs(data), **_line(data, route_id)}

    return attrs


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


SENSORS: tuple[TtcSensorDescription, ...] = (
    TtcSensorDescription(
        key="service_alerts",
        name="Service alerts",
        icon="mdi:transit-connection-variant",
        value=lambda data: data.get("active_count", 0),
        attrs=_service_attrs,
    ),
    TtcSensorDescription(
        key="subway_status",
        name="Subway status",
        icon="mdi:subway-variant",
        value=lambda data: data.get("subway", {}).get("status", "Normal service"),
        attrs=_nested_attrs("subway"),
    ),
    TtcSensorDescription(
        key="surface_alerts",
        name="Surface alerts",
        icon="mdi:bus-clock",
        value=lambda data: data.get("surface", {}).get("active_route_count", 0),
        attrs=_nested_attrs("surface"),
    ),
    TtcSensorDescription(
        key="accessibility_alerts",
        name="Accessibility alerts",
        icon="mdi:elevator",
        value=lambda data: data.get("accessibility", {}).get("active_count", 0),
        attrs=_nested_attrs("accessibility"),
    ),
    TtcSensorDescription(
        key="tracked_routes",
        name="Tracked routes",
        icon="mdi:map-marker-path",
        value=lambda data: data.get("tracked", {}).get("active_count", 0),
        attrs=_tracked_attrs,
    ),
    TtcSensorDescription(
        key="feed_updated",
        name="Feed updated",
        icon="mdi:clock-check",
        device_class=SensorDeviceClass.TIMESTAMP,
        value=lambda data: _parse_dt(data.get("feed_timestamp")),
        attrs=_base_attrs,
    ),
    *(
        TtcSensorDescription(
            key=f"line_{route_id}_status",
            name=f"Line {route_id} status",
            icon="mdi:subway-variant",
            value=_line_value(route_id),
            attrs=_line_attrs(route_id),
        )
        for route_id in SUBWAY_LINES
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up TTC Service Alerts sensors."""
    coordinator: TtcServiceAlertsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(TtcSensor(coordinator, entry, description) for description in SENSORS)


class TtcSensor(CoordinatorEntity[TtcServiceAlertsCoordinator], SensorEntity):
    """A TTC Service Alerts sensor."""

    _attr_has_entity_name = True
    entity_description: TtcSensorDescription

    def __init__(
        self,
        coordinator: TtcServiceAlertsCoordinator,
        entry: ConfigEntry,
        description: TtcSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Toronto Transit Commission",
            model="GTFS-RT service alerts",
        )

    @property
    def native_value(self) -> Any:
        if not self.coordinator.data:
            return None
        return self.entity_description.value(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        return self.entity_description.attrs(self.coordinator.data)
