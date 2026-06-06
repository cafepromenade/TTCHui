"""Binary sensors for TTC Service Alerts (per-line disruption flags)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_ATTRIBUTION, DOMAIN
from .coordinator import TtcServiceAlertsCoordinator
from .parser import SUBWAY_LINES, line_from_data, line_is_disrupted


@dataclass(frozen=True, kw_only=True)
class TtcBinarySensorDescription(BinarySensorEntityDescription):
    """Binary sensor description with state and attribute extractors."""

    is_on: Callable[[dict[str, Any]], bool] = lambda data: False
    attrs: Callable[[dict[str, Any]], dict[str, Any]] = lambda data: {}


def _base_attrs(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "feed": data.get("feed"),
        "source_url": data.get("source_url"),
        "feed_timestamp": data.get("feed_timestamp"),
        "fetched_at": data.get("fetched_at"),
        ATTR_ATTRIBUTION: data.get("attribution"),
    }


def _line_is_on(route_id: str) -> Callable[[dict[str, Any]], bool]:
    def is_on(data: dict[str, Any]) -> bool:
        return line_is_disrupted(data, route_id)

    return is_on


def _line_attrs(route_id: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def attrs(data: dict[str, Any]) -> dict[str, Any]:
        return {**_base_attrs(data), **line_from_data(data, route_id)}

    return attrs


BINARY_SENSORS: tuple[TtcBinarySensorDescription, ...] = tuple(
    TtcBinarySensorDescription(
        key=f"line_{route_id}_disrupted",
        name=f"Line {route_id} disrupted",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on=_line_is_on(route_id),
        attrs=_line_attrs(route_id),
    )
    for route_id in SUBWAY_LINES
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up TTC Service Alerts binary sensors."""
    coordinator: TtcServiceAlertsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        TtcBinarySensor(coordinator, entry, description) for description in BINARY_SENSORS
    )


class TtcBinarySensor(CoordinatorEntity[TtcServiceAlertsCoordinator], BinarySensorEntity):
    """A TTC per-line disruption binary sensor."""

    _attr_has_entity_name = True
    entity_description: TtcBinarySensorDescription

    def __init__(
        self,
        coordinator: TtcServiceAlertsCoordinator,
        entry: ConfigEntry,
        description: TtcBinarySensorDescription,
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
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        return self.entity_description.is_on(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self.coordinator.data:
            return {}
        return self.entity_description.attrs(self.coordinator.data)
