"""Config and options flow for TTC Service Alerts."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TtcApiClient, TtcApiError
from .const import (
    CONF_FEED,
    CONF_MAX_ALERTS,
    CONF_NAME,
    CONF_POLL_SECONDS,
    CONF_ROUTE_FILTER,
    CONF_UPCOMING_HOURS,
    DEFAULT_FEED,
    DEFAULT_MAX_ALERTS,
    DEFAULT_NAME,
    DEFAULT_POLL_SECONDS,
    DEFAULT_UPCOMING_HOURS,
    DOMAIN,
    FEED_LABELS,
    FEED_URLS,
)


class TtcServiceAlertsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Initial setup for TTC Service Alerts."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                client = TtcApiClient(async_get_clientsession(self.hass))
                await client.async_fetch_alerts(
                    FEED_URLS[user_input[CONF_FEED]],
                    route_filter=user_input.get(CONF_ROUTE_FILTER, ""),
                    upcoming_hours=user_input[CONF_UPCOMING_HOURS],
                    max_alerts=user_input[CONF_MAX_ALERTS],
                )
            except TtcApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - config flow should not expose internals
                errors["base"] = "unknown"

            if not errors:
                await self.async_set_unique_id(f"ttc_service_alerts_{user_input[CONF_FEED]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_settings_schema({}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return TtcServiceAlertsOptionsFlow(config_entry)


class TtcServiceAlertsOptionsFlow(OptionsFlow):
    """Editable TTC Service Alerts options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                client = TtcApiClient(async_get_clientsession(self.hass))
                await client.async_fetch_alerts(
                    FEED_URLS[user_input[CONF_FEED]],
                    route_filter=user_input.get(CONF_ROUTE_FILTER, ""),
                    upcoming_hours=user_input[CONF_UPCOMING_HOURS],
                    max_alerts=user_input[CONF_MAX_ALERTS],
                )
            except TtcApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - config flow should not expose internals
                errors["base"] = "unknown"

            if not errors:
                return self.async_create_entry(title="", data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_settings_schema(current),
            errors=errors,
        )


def _settings_schema(current: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=current.get(CONF_NAME, DEFAULT_NAME)): str,
            vol.Required(CONF_FEED, default=current.get(CONF_FEED, DEFAULT_FEED)): vol.In(FEED_LABELS),
            vol.Optional(CONF_ROUTE_FILTER, default=current.get(CONF_ROUTE_FILTER, "")): str,
            vol.Required(
                CONF_POLL_SECONDS,
                default=current.get(CONF_POLL_SECONDS, DEFAULT_POLL_SECONDS),
            ): vol.All(vol.Coerce(int), vol.Range(min=30, max=3600)),
            vol.Required(
                CONF_UPCOMING_HOURS,
                default=current.get(CONF_UPCOMING_HOURS, DEFAULT_UPCOMING_HOURS),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=168)),
            vol.Required(
                CONF_MAX_ALERTS,
                default=current.get(CONF_MAX_ALERTS, DEFAULT_MAX_ALERTS),
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=100)),
        }
    )

