"""Coordinator for TTC Service Alerts."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TtcApiClient, TtcApiError
from .const import (
    ATTRIBUTION,
    CONF_FEED,
    CONF_MAX_ALERTS,
    CONF_POLL_SECONDS,
    CONF_ROUTE_FILTER,
    CONF_UPCOMING_HOURS,
    DEFAULT_FEED,
    DEFAULT_MAX_ALERTS,
    DEFAULT_POLL_SECONDS,
    DEFAULT_UPCOMING_HOURS,
    FEED_URLS,
)

_LOGGER = logging.getLogger(__name__)


class TtcServiceAlertsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll the selected TTC GTFS-RT alerts feed."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        poll_seconds = self._option(CONF_POLL_SECONDS, DEFAULT_POLL_SECONDS)
        super().__init__(
            hass,
            _LOGGER,
            name="TTC Service Alerts",
            update_interval=timedelta(seconds=max(30, int(poll_seconds))),
        )
        self.api = TtcApiClient(async_get_clientsession(hass))

    def _option(self, key: str, default: Any = None) -> Any:
        return self.entry.options.get(key, self.entry.data.get(key, default))

    async def _async_update_data(self) -> dict[str, Any]:
        feed = str(self._option(CONF_FEED, DEFAULT_FEED))
        url = FEED_URLS.get(feed, FEED_URLS[DEFAULT_FEED])
        route_filter = self._option(CONF_ROUTE_FILTER, "")
        upcoming_hours = int(self._option(CONF_UPCOMING_HOURS, DEFAULT_UPCOMING_HOURS))
        max_alerts = int(self._option(CONF_MAX_ALERTS, DEFAULT_MAX_ALERTS))

        try:
            data = await self.api.async_fetch_alerts(
                url,
                route_filter=route_filter,
                upcoming_hours=upcoming_hours,
                max_alerts=max_alerts,
            )
        except TtcApiError as err:
            raise UpdateFailed(str(err)) from err

        data.update(
            {
                "feed": feed,
                "source_url": url,
                "route_filter": route_filter,
                "upcoming_hours": upcoming_hours,
                "max_alerts": max_alerts,
                "attribution": ATTRIBUTION,
            }
        )
        return data

