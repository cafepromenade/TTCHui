# TTC Hui

TTC Hui is a Home Assistant custom integration plus Lovelace card for live TTC
service delays and advisories. It polls the official TTC GTFS-RT service-alert
feed and exposes Home Assistant sensors for active alerts, subway status,
surface route impacts, accessibility issues, tracked routes, and feed freshness.

## What It Shows

- Live active TTC service alerts from the official GTFS-RT binary feed.
- Upcoming planned alerts inside a configurable horizon.
- Subway line status for Line 1, Line 2, Line 4, Line 5, and Line 6 when present in the feed.
- One status sensor, delay-count sensor, and "disrupted" binary sensor per subway line.
- Transit-board styling: each line shows its official TTC colour roundel and a green/yellow/red status bar.
- Bus and streetcar route summaries grouped by affected route.
- Elevator and escalator accessibility alerts.
- Optional tracked route filter, for example `1,2,501,512,90`.
- A custom Lovelace card with tabs for All, Subway, Surface, and Access.
- A refresh service and card refresh button that fetch the latest feed immediately.

Data source: `https://gtfsrt.ttc.ca/alerts/all?format=binary`

## Install With HACS

Repository URL:

```text
https://github.com/cafepromenade/TTCHui
```

1. In HACS, open Integrations, then Custom repositories.
2. Add this repository URL with category Integration.
3. Install TTC Hui and restart Home Assistant.
4. Open Settings > Devices & services > Add integration > TTC Service Alerts.
5. Keep the default feed as "All service alerts" unless you only want one feed.

## Lovelace Card

Copy `lovelace/ttc-service-alerts-card.js` to `<config>/www/`, then add a
dashboard resource:

```yaml
url: /local/ttc-service-alerts-card.js
type: module
```

Add the card:

```yaml
type: custom:ttc-service-alerts-card
entity: sensor.ttc_service_alerts
subway_entity: sensor.ttc_subway_status
surface_entity: sensor.ttc_surface_alerts
accessibility_entity: sensor.ttc_accessibility_alerts
tracked_entity: sensor.ttc_tracked_routes
title: TTC Service
max_items: 10
```

A full example view is in `lovelace/dashboard-ttc.yaml`.

## TTC Dashboard

`lovelace/dashboard-ttc.yaml` is a dedicated TTC dashboard with separate views
for live alerts, subway line status, surface routes, accessibility alerts, and
feed diagnostics. It uses the custom TTC card plus native Home Assistant entity
cards, tiles, 24-hour history graphs, delay-summary attributes, and feed-health
details for each subway line.

## Entities

- `sensor.ttc_service_alerts`: active alert count with full alert attributes.
- `sensor.ttc_subway_status`: worst active subway status and line summaries.
- `sensor.ttc_surface_alerts`: count of active affected surface routes.
- `sensor.ttc_accessibility_alerts`: active accessibility alert count.
- `sensor.ttc_tracked_routes`: active count for your route filter.
- `sensor.ttc_feed_updated`: GTFS-RT feed timestamp.
- `sensor.ttc_line_N_status`: per-line service status (Lines 1, 2, 4, 5, 6) with
  current delay details, plus `color`, `label`, and a `status_level`
  (`normal`/`delay`/`no_service`) attribute for transit-board styling.
- `sensor.ttc_line_N_delays`: per-line count of active delay-type alerts
  (measurement, good for graphs and threshold automations).
- `binary_sensor.ttc_line_N_disrupted`: per-line problem flag, `on` whenever the
  line has an active disruption. Ideal for notifications and conditional cards.

Entity IDs can differ if Home Assistant has already used these names. The card
lets you override each entity explicitly.

### Subway line colors

Each line carries its official TTC colour, exposed in the `color` attribute and
rendered by the card as a coloured line roundel:

| Line | Colour | Hex |
| --- | --- | --- |
| 1 Yonge-University | Yellow | `#f8c302` |
| 2 Bloor-Danforth | Green | `#16a753` |
| 4 Sheppard | Purple | `#b32078` |
| 5 Eglinton | Orange | `#f87005` |
| 6 Finch West | Grey | `#8a999a` |

The card draws each line like a transit display board: a **green** bar for good
service, **yellow** for delays/reduced service, and **red** for no service.

## Service

```yaml
service: ttc_service_alerts.refresh
```

This forces every configured TTC entry to fetch the latest GTFS-RT feed.

## Options

- Feed: all, subway, bus, streetcar, accessibility, or stops.
- Tracked routes: optional comma-separated GTFS route IDs.
- Poll interval: 30 to 3600 seconds, default 60.
- Upcoming horizon: 1 to 168 hours, default 24.
- Maximum alerts stored in state attributes: 5 to 100, default 40.

## Local Verification

Install parser test dependencies:

```powershell
python -m pip install -r requirements-dev.txt
```

Run parser tests:

```powershell
python -m pytest
```

Run a live TTC feed smoke check:

```powershell
python scripts/smoke_live_feed.py
```

## Attribution

Contains information licensed under the Open Government Licence - Toronto.
