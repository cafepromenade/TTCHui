/**
 * TTC Service Alerts custom Lovelace card.
 *
 * Install: copy to <config>/www/ttc-service-alerts-card.js, add the resource
 * /local/ttc-service-alerts-card.js as a JavaScript module, then use:
 *
 *   type: custom:ttc-service-alerts-card
 *   entity: sensor.ttc_service_alerts
 */

class TtcServiceAlertsCard extends HTMLElement {
  setConfig(config) {
    this._config = {
      entity: "sensor.ttc_service_alerts",
      subway_entity: "sensor.ttc_subway_status",
      surface_entity: "sensor.ttc_surface_alerts",
      accessibility_entity: "sensor.ttc_accessibility_alerts",
      tracked_entity: "sensor.ttc_tracked_routes",
      title: "TTC Service",
      max_items: 8,
      ...config,
    };
    this._view = this._view || "all";
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 6;
  }

  getGridOptions() {
    return {
      columns: "full",
      min_columns: 6,
      rows: 6,
      min_rows: 4,
    };
  }

  _entity(id) {
    return this._hass && this._hass.states[id];
  }

  _attrs(id) {
    const entity = this._entity(id);
    return entity ? entity.attributes || {} : {};
  }

  _refresh() {
    if (!this._hass) return;
    this._hass.callService("ttc_service_alerts", "refresh", {});
  }

  _setView(view) {
    this._view = view;
    this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;

    const service = this._entity(this._config.entity);
    const serviceAttrs = service ? service.attributes || {} : {};
    const subwayAttrs = this._attrs(this._config.subway_entity);
    const surfaceAttrs = this._attrs(this._config.surface_entity);
    const accessAttrs = this._attrs(this._config.accessibility_entity);
    const trackedAttrs = this._attrs(this._config.tracked_entity);
    const maxItems = Number(this._config.max_items) || 8;
    const activeCount = Number(serviceAttrs.active_count || service?.state || 0);
    const upcomingCount = Number(serviceAttrs.upcoming_count || 0);
    const highestStatus = serviceAttrs.highest_status || "Normal service";
    const fetchedAt = this._formatTime(serviceAttrs.fetched_at || serviceAttrs.feed_timestamp);
    const tabs = this._tabs({
      all: activeCount,
      subway: subwayAttrs.active_count || 0,
      surface: surfaceAttrs.active_route_count || 0,
      accessibility: accessAttrs.active_count || 0,
    });
    const body = this._bodyForView({
      serviceAttrs,
      subwayAttrs,
      surfaceAttrs,
      accessAttrs,
      trackedAttrs,
      maxItems,
    });

    this.innerHTML = `
      <ha-card>
        <style>
          .ttc-wrap {
            padding: 14px 16px 16px;
            color: var(--primary-text-color);
          }
          .ttc-head {
            display: grid;
            grid-template-columns: auto 1fr auto auto;
            gap: 10px;
            align-items: center;
            min-width: 0;
          }
          .ttc-icon {
            width: 38px;
            height: 38px;
            display: grid;
            place-items: center;
            border-radius: 8px;
            background: color-mix(in srgb, var(--primary-color) 14%, transparent);
            color: var(--primary-color);
          }
          .ttc-title {
            min-width: 0;
          }
          .ttc-title h2 {
            margin: 0;
            font-size: 1.05rem;
            line-height: 1.25;
            font-weight: 650;
            letter-spacing: 0;
            overflow-wrap: anywhere;
          }
          .ttc-sub {
            margin-top: 2px;
            color: var(--secondary-text-color);
            font-size: 0.78rem;
            line-height: 1.25;
          }
          .ttc-count {
            text-align: right;
            min-width: 70px;
          }
          .ttc-count strong {
            display: block;
            font-size: 1.25rem;
            line-height: 1;
          }
          .ttc-count span {
            color: var(--secondary-text-color);
            font-size: 0.72rem;
          }
          .ttc-refresh {
            border: 0;
            background: transparent;
            color: var(--primary-text-color);
            width: 40px;
            height: 40px;
            border-radius: 8px;
            cursor: pointer;
          }
          .ttc-refresh:hover {
            background: var(--secondary-background-color);
          }
          .ttc-statusbar {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 8px;
            margin: 14px 0 12px;
          }
          .ttc-stat {
            border-top: 3px solid var(--divider-color);
            background: var(--secondary-background-color);
            border-radius: 8px;
            padding: 9px 10px;
            min-width: 0;
          }
          .ttc-stat .label {
            color: var(--secondary-text-color);
            font-size: 0.72rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }
          .ttc-stat .value {
            margin-top: 4px;
            font-size: 0.95rem;
            font-weight: 650;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }
          .status-normal { border-color: var(--success-color, #2e7d32); }
          .status-watch { border-color: #d88c00; }
          .status-bad { border-color: var(--error-color, #c62828); }
          .ttc-tabs {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 6px;
            margin-bottom: 12px;
          }
          .ttc-tab {
            border: 1px solid var(--divider-color);
            background: transparent;
            color: var(--primary-text-color);
            border-radius: 8px;
            min-height: 38px;
            padding: 6px 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            cursor: pointer;
            min-width: 0;
          }
          .ttc-tab span {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }
          .ttc-tab[aria-selected="true"] {
            border-color: var(--primary-color);
            background: color-mix(in srgb, var(--primary-color) 12%, transparent);
            color: var(--primary-color);
            font-weight: 650;
          }
          .ttc-section-title {
            margin: 12px 0 7px;
            font-size: 0.83rem;
            text-transform: uppercase;
            color: var(--secondary-text-color);
            font-weight: 650;
            letter-spacing: 0;
          }
          .ttc-lines,
          .ttc-routes {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
            gap: 8px;
          }
          .ttc-line,
          .ttc-route {
            border-left: 4px solid var(--divider-color);
            background: var(--card-background-color);
            box-shadow: inset 0 0 0 1px var(--divider-color);
            border-radius: 8px;
            padding: 9px 10px;
            min-width: 0;
          }
          .ttc-line-head {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 8px;
            min-width: 0;
          }
          .ttc-line strong,
          .ttc-route strong {
            display: block;
            font-size: 0.9rem;
            overflow-wrap: anywhere;
          }
          .ttc-line-status,
          .ttc-route span {
            display: block;
            color: var(--secondary-text-color);
            margin-top: 2px;
            font-size: 0.76rem;
            line-height: 1.25;
          }
          .ttc-line-badge {
            border: 1px solid var(--divider-color);
            border-radius: 999px;
            padding: 2px 7px;
            color: var(--secondary-text-color);
            font-size: 0.7rem;
            white-space: nowrap;
          }
          .ttc-line-delay {
            margin-top: 7px;
            color: var(--primary-text-color);
            font-size: 0.8rem;
            line-height: 1.32;
            overflow-wrap: anywhere;
          }
          .ttc-line-delay.muted {
            color: var(--secondary-text-color);
          }
          .ttc-line-delay + .ttc-line-delay {
            margin-top: 5px;
          }
          .ttc-delay-label {
            color: var(--secondary-text-color);
            font-weight: 650;
          }
          .ttc-alerts {
            display: grid;
            gap: 8px;
          }
          .ttc-alert {
            border-left: 4px solid var(--divider-color);
            background: var(--secondary-background-color);
            border-radius: 8px;
            padding: 10px 11px;
            min-width: 0;
          }
          .ttc-alert-top {
            display: flex;
            align-items: center;
            gap: 6px;
            color: var(--secondary-text-color);
            font-size: 0.72rem;
            line-height: 1.25;
            min-width: 0;
          }
          .ttc-pill {
            border: 1px solid var(--divider-color);
            border-radius: 999px;
            padding: 2px 7px;
            white-space: nowrap;
          }
          .ttc-alert-title {
            margin-top: 6px;
            font-weight: 650;
            font-size: 0.92rem;
            line-height: 1.28;
            overflow-wrap: anywhere;
          }
          .ttc-alert-desc {
            margin-top: 4px;
            color: var(--secondary-text-color);
            font-size: 0.82rem;
            line-height: 1.3;
            overflow-wrap: anywhere;
          }
          .ttc-alert-foot {
            margin-top: 7px;
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--secondary-text-color);
            font-size: 0.74rem;
            min-width: 0;
          }
          .ttc-alert-foot a {
            color: var(--primary-color);
            display: inline-flex;
            align-items: center;
            gap: 4px;
            text-decoration: none;
          }
          .ttc-empty {
            color: var(--secondary-text-color);
            background: var(--secondary-background-color);
            border-radius: 8px;
            padding: 14px;
            text-align: center;
          }
          .bad { border-left-color: var(--error-color, #c62828); }
          .watch { border-left-color: #d88c00; }
          .normal { border-left-color: var(--success-color, #2e7d32); }
          @media (max-width: 560px) {
            .ttc-head {
              grid-template-columns: auto 1fr auto;
            }
            .ttc-count {
              display: none;
            }
            .ttc-statusbar,
            .ttc-tabs {
              grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .ttc-tab {
              justify-content: flex-start;
            }
          }
        </style>
        <div class="ttc-wrap">
          <div class="ttc-head">
            <div class="ttc-icon"><ha-icon icon="mdi:train-car"></ha-icon></div>
            <div class="ttc-title">
              <h2>${this._esc(this._config.title)}</h2>
              <div class="ttc-sub">${this._esc(highestStatus)}${fetchedAt ? ` - ${this._esc(fetchedAt)}` : ""}</div>
            </div>
            <div class="ttc-count"><strong>${activeCount}</strong><span>active</span></div>
            <button class="ttc-refresh" title="Refresh TTC feed" aria-label="Refresh TTC feed">
              <ha-icon icon="mdi:refresh"></ha-icon>
            </button>
          </div>
          <div class="ttc-statusbar">
            ${this._stat("Subway", subwayAttrs.status || "Normal service", this._statusClass(subwayAttrs.status))}
            ${this._stat("Surface routes", `${surfaceAttrs.active_route_count || 0} affected`, Number(surfaceAttrs.active_route_count || 0) ? "status-watch" : "status-normal")}
            ${this._stat("Accessibility", `${accessAttrs.active_count || 0} alerts`, Number(accessAttrs.active_count || 0) ? "status-watch" : "status-normal")}
            ${this._stat("Upcoming", `${upcomingCount} planned`, upcomingCount ? "status-watch" : "status-normal")}
          </div>
          <div class="ttc-tabs" role="tablist">${tabs}</div>
          ${body}
        </div>
      </ha-card>`;

    const refresh = this.querySelector(".ttc-refresh");
    if (refresh) refresh.addEventListener("click", () => this._refresh());
    this.querySelectorAll(".ttc-tab").forEach((tab) => {
      tab.addEventListener("click", () => this._setView(tab.dataset.view));
    });
  }

  _tabs(counts) {
    const defs = [
      ["all", "mdi:transit-connection-variant", "All", counts.all],
      ["subway", "mdi:subway-variant", "Subway", counts.subway],
      ["surface", "mdi:bus-clock", "Surface", counts.surface],
      ["accessibility", "mdi:elevator", "Access", counts.accessibility],
    ];
    return defs.map(([view, icon, label, count]) => `
      <button class="ttc-tab" role="tab" data-view="${view}" aria-selected="${this._view === view ? "true" : "false"}">
        <ha-icon icon="${icon}"></ha-icon><span>${label} (${Number(count || 0)})</span>
      </button>`).join("");
  }

  _bodyForView(data) {
    if (this._view === "subway") return this._subwayView(data.subwayAttrs, data.maxItems);
    if (this._view === "surface") return this._surfaceView(data.surfaceAttrs, data.maxItems);
    if (this._view === "accessibility") return this._alertSections(data.accessAttrs.alerts || [], data.accessAttrs.upcoming_alerts || [], data.maxItems);
    return this._allView(data);
  }

  _allView({ serviceAttrs, subwayAttrs, surfaceAttrs, accessAttrs, trackedAttrs, maxItems }) {
    const tracked = trackedAttrs.enabled
      ? `${this._sectionTitle("Tracked Routes")} ${this._alertList(trackedAttrs.active_alerts || [], maxItems)}`
      : "";
    const lines = this._lineGrid(subwayAttrs.lines || []);
    const routes = this._routeGrid((surfaceAttrs.routes || []).slice(0, 12));
    const active = this._alertList(serviceAttrs.active_alerts || [], maxItems);
    const upcoming = this._alertList(serviceAttrs.upcoming_alerts || [], Math.min(5, maxItems), "No upcoming TTC alerts in the selected horizon.");
    return `
      ${tracked}
      ${this._sectionTitle("Subway Lines")}
      ${lines}
      ${this._sectionTitle("Surface Routes")}
      ${routes || this._empty("No active surface route alerts.")}
      ${this._sectionTitle("Active Alerts")}
      ${active}
      ${this._sectionTitle("Upcoming")}
      ${upcoming}
      ${Number(accessAttrs.active_count || 0) ? `${this._sectionTitle("Accessibility")} ${this._alertList(accessAttrs.alerts || [], 4)}` : ""}
    `;
  }

  _subwayView(attrs, maxItems) {
    return `
      ${this._sectionTitle("Line Status")}
      ${this._lineGrid(attrs.lines || [])}
      ${this._sectionTitle("Active Subway Alerts")}
      ${this._alertList(attrs.alerts || [], maxItems, "No active subway alerts.")}
      ${this._sectionTitle("Upcoming Subway Alerts")}
      ${this._alertList(attrs.upcoming_alerts || [], Math.min(maxItems, 6), "No upcoming subway alerts in the selected horizon.")}
    `;
  }

  _surfaceView(attrs, maxItems) {
    return `
      ${this._sectionTitle("Affected Routes")}
      ${this._routeGrid(attrs.routes || []) || this._empty("No active surface route alerts.")}
      ${this._sectionTitle("Active Surface Alerts")}
      ${this._alertList(attrs.alerts || [], maxItems, "No active bus or streetcar alerts.")}
      ${this._sectionTitle("Upcoming Surface Alerts")}
      ${this._alertList(attrs.upcoming_alerts || [], Math.min(maxItems, 6), "No upcoming surface alerts in the selected horizon.")}
    `;
  }

  _alertSections(active, upcoming, maxItems) {
    return `
      ${this._sectionTitle("Active Accessibility Alerts")}
      ${this._alertList(active, maxItems, "No active accessibility alerts.")}
      ${this._sectionTitle("Upcoming Accessibility Alerts")}
      ${this._alertList(upcoming, Math.min(maxItems, 6), "No upcoming accessibility alerts in the selected horizon.")}
    `;
  }

  _lineGrid(lines) {
    if (!lines.length) return this._empty("No subway line data.");
    return `<div class="ttc-lines">${lines.map((line) => {
      const status = line.status || "Normal service";
      const activeCount = Number(line.active_count || 0);
      const upcomingCount = Number(line.upcoming_count || 0);
      const countText = activeCount
        ? `${activeCount} active${upcomingCount ? `, ${upcomingCount} upcoming` : ""}`
        : upcomingCount
          ? `${upcomingCount} upcoming`
          : "Clear";
      return `
        <div class="ttc-line ${this._statusTone(status)}">
          <div class="ttc-line-head">
            <div>
              <strong>${this._esc(line.name || line.route_id)}</strong>
              <span class="ttc-line-status">${this._esc(status)}</span>
            </div>
            <span class="ttc-line-badge">${this._esc(countText)}</span>
          </div>
          ${this._lineDelayDetails(line)}
        </div>`;
    }).join("")}</div>`;
  }

  _lineDelayDetails(line) {
    const active = line.delay_alerts && line.delay_alerts.length ? line.delay_alerts : line.alerts || [];
    const upcoming = line.upcoming_delay_alerts && line.upcoming_delay_alerts.length ? line.upcoming_delay_alerts : line.upcoming_alerts || [];
    const details = [
      ...active.slice(0, 2).map((alert) => this._lineDelay(alert, "Now")),
      ...upcoming.slice(0, 2).map((alert) => this._lineDelay(alert, "Upcoming")),
    ];
    if (!details.length) {
      return `<div class="ttc-line-delay muted">No current delay info.</div>`;
    }
    return details.join("");
  }

  _lineDelay(alert, label) {
    const summary = alert.summary || alert.header || "TTC service alert";
    const time = this._timeRange(alert.start, alert.end);
    const effect = alert.effect_label || "Alert";
    return `
      <div class="ttc-line-delay">
        <span class="ttc-delay-label">${this._esc(label)} ${this._esc(effect)}:</span>
        ${this._esc(summary)}
        <span class="ttc-delay-label">${this._esc(time)}</span>
      </div>`;
  }

  _routeGrid(routes) {
    if (!routes.length) return "";
    return `<div class="ttc-routes">${routes.map((route) => {
      const status = route.status || "Normal service";
      return `
        <div class="ttc-route ${this._statusTone(status)}">
          <strong>${this._esc(route.name || route.route_id)}</strong>
          <span>${this._esc(status)}${Number(route.upcoming_count || 0) ? `, ${Number(route.upcoming_count)} upcoming` : ""}</span>
        </div>`;
    }).join("")}</div>`;
  }

  _alertList(alerts, maxItems, emptyText = "No active TTC alerts.") {
    if (!alerts || !alerts.length) return this._empty(emptyText);
    return `<div class="ttc-alerts">${alerts.slice(0, maxItems).map((alert) => this._alert(alert)).join("")}</div>`;
  }

  _alert(alert) {
    const title = alert.header || "TTC service alert";
    const desc = alert.description && alert.description !== title ? `<div class="ttc-alert-desc">${this._esc(alert.description)}</div>` : "";
    const routes = (alert.route_labels || alert.routes || []).slice(0, 4).join(", ");
    const routeText = routes || this._modeLabel(alert.mode);
    const time = this._timeRange(alert.start, alert.end);
    const url = alert.url ? `<a href="${this._escAttr(alert.url)}" target="_blank" rel="noreferrer"><ha-icon icon="mdi:open-in-new"></ha-icon>Details</a>` : "";
    return `
      <div class="ttc-alert ${this._severityTone(alert)}">
        <div class="ttc-alert-top">
          <span class="ttc-pill">${this._esc(alert.effect_label || "Alert")}</span>
          <span>${this._esc(routeText)}</span>
        </div>
        <div class="ttc-alert-title">${this._esc(title)}</div>
        ${desc}
        <div class="ttc-alert-foot">
          <span>${this._esc(time)}</span>
          ${url}
        </div>
      </div>`;
  }

  _stat(label, value, cls) {
    return `<div class="ttc-stat ${cls || ""}"><div class="label">${this._esc(label)}</div><div class="value">${this._esc(value)}</div></div>`;
  }

  _sectionTitle(title) {
    return `<div class="ttc-section-title">${this._esc(title)}</div>`;
  }

  _empty(text) {
    return `<div class="ttc-empty">${this._esc(text)}</div>`;
  }

  _statusClass(status) {
    const text = String(status || "").toLowerCase();
    if (!text || text.includes("normal")) return "status-normal";
    if (text.includes("no service") || text.includes("delay")) return "status-bad";
    return "status-watch";
  }

  _statusTone(status) {
    const cls = this._statusClass(status);
    if (cls === "status-normal") return "normal";
    if (cls === "status-bad") return "bad";
    return "watch";
  }

  _severityTone(alert) {
    if (Number(alert.severity || 0) >= 40) return "bad";
    if (Number(alert.severity || 0) >= 20) return "watch";
    return "normal";
  }

  _modeLabel(mode) {
    const labels = {
      subway: "Subway",
      streetcar: "Streetcar",
      bus: "Bus",
      surface: "Surface",
      accessibility: "Accessibility",
      other: "TTC",
    };
    return labels[mode] || "TTC";
  }

  _formatTime(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    }).format(date);
  }

  _timeRange(start, end) {
    const from = this._formatTime(start);
    const to = this._formatTime(end);
    if (from && to) return `${from} to ${to}`;
    if (from) return `Since ${from}`;
    if (to) return `Until ${to}`;
    return "Now";
  }

  _esc(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  _escAttr(value) {
    return this._esc(value).replace(/"/g, "&quot;");
  }
}

customElements.define("ttc-service-alerts-card", TtcServiceAlertsCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "ttc-service-alerts-card",
  name: "TTC Service Alerts",
  description: "Live TTC subway, surface, accessibility, and upcoming service alerts.",
});
