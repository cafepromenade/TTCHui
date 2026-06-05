"""HTTP client for TTC GTFS-RT alert feeds."""

from __future__ import annotations

import asyncio
from typing import Any

from aiohttp import ClientError, ClientSession
from google.protobuf.message import DecodeError

from .parser import normalize_route_filter, parse_feed_bytes


class TtcApiError(Exception):
    """Raised when the TTC feed cannot be fetched or parsed."""


class TtcApiClient:
    """Small async client for TTC GTFS-RT protobuf feeds."""

    def __init__(self, session: ClientSession) -> None:
        self._session = session

    async def async_fetch_alerts(
        self,
        url: str,
        *,
        route_filter: str | list[str] | None = None,
        upcoming_hours: int = 24,
        max_alerts: int = 40,
    ) -> dict[str, Any]:
        """Fetch and parse one TTC alert feed."""
        headers = {
            "Accept": "application/x-protobuf, application/octet-stream;q=0.9, */*;q=0.1",
            "User-Agent": "HomeAssistant-TTC-Service-Alerts/1.0",
        }
        try:
            async with asyncio.timeout(20):
                async with self._session.get(url, headers=headers) as response:
                    if response.status != 200:
                        text = await response.text()
                        raise TtcApiError(f"TTC feed returned HTTP {response.status}: {text[:200]}")
                    payload = await response.read()
        except TimeoutError as err:
            raise TtcApiError("Timed out while fetching TTC service alerts.") from err
        except ClientError as err:
            raise TtcApiError(f"Could not fetch TTC service alerts: {err}") from err

        try:
            return parse_feed_bytes(
                payload,
                route_filter=normalize_route_filter(route_filter),
                upcoming_hours=upcoming_hours,
                max_alerts=max_alerts,
            )
        except DecodeError as err:
            raise TtcApiError("TTC feed did not return valid GTFS-RT protobuf data.") from err

