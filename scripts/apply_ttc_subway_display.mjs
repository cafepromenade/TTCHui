const baseHttp = (process.env.HA_BASE_HTTP || 'http://192.168.50.16:8123').replace(/\/$/, '');
const wsUrl = process.env.HA_WS_URL || baseHttp.replace(/^http/, 'ws') + '/api/websocket';
const username = process.env.HA_USERNAME || 'Metrolinx';
const password = process.env.HA_PASSWORD || '123Jerchuthui';
const dashboardPath = process.env.TTC_DASHBOARD_PATH || 'ttc-subway';
const displayEntity = process.env.TTC_DISPLAY_ENTITY || 'media_player.nesthubcc18';
const oldDisplayEntity = process.env.TTC_OLD_DISPLAY_ENTITY || 'media_player.metrolinx_display';
const subwayViewPath = process.env.TTC_SUBWAY_VIEW_PATH || 'subway-issues';
const surfaceViewPath = process.env.TTC_SURFACE_VIEW_PATH || 'bus-streetcar';
const normalLineStates = ['Normal service', 'No Effect', 'unknown', 'unavailable'];
const lineEntities = [
  'sensor.ttc_line_1_status',
  'sensor.ttc_line_2_status',
  'sensor.ttc_line_4_status',
  'sensor.ttc_line_5_status',
  'sensor.ttc_line_6_status',
];
const lineIssueTemplate = "{{ expand('sensor.ttc_line_1_status', 'sensor.ttc_line_2_status', 'sensor.ttc_line_4_status', 'sensor.ttc_line_5_status', 'sensor.ttc_line_6_status') | rejectattr('state', 'in', ['Normal service', 'No Effect', 'unknown', 'unavailable']) | list | count > 0 }}";

const lineButton = (line, name, color) => ({
  type: 'custom:button-card',
  entity: `sensor.ttc_line_${line}_status`,
  name,
  icon: `mdi:numeric-${line}-circle`,
  color,
  color_type: 'icon',
  show_state: true,
  state_display: "[[[ return entity?.state === 'No Effect' ? 'Normal service' : entity?.state; ]]]",
  tap_action: { action: 'more-info' },
  styles: {
    card: [
      'min-height: 116px',
      'padding: 14px 12px',
      'border-radius: 12px',
      `[[[ const issue = entity && !['Normal service', 'No Effect', 'unknown', 'unavailable'].includes(entity.state); return issue ? 'background: linear-gradient(135deg, ${color} 0%, rgba(32, 18, 18, 0.94) 42%, rgba(120, 18, 18, 0.92) 100%)' : 'background: var(--card-background-color)'; ]]]`,
      `[[[ const issue = entity && !['Normal service', 'No Effect', 'unknown', 'unavailable'].includes(entity.state); return issue ? 'box-shadow: 0 0 22px ${color}, inset 0 0 0 2px rgba(255,255,255,0.34)' : 'box-shadow: none'; ]]]`,
      `border-left: 10px solid ${color}`,
      `--paper-item-icon-color: ${color}`,
      `--state-icon-color: ${color}`,
    ],
    grid: [
      'grid-template-areas: "i n" "i s"',
      'grid-template-columns: 62px 1fr',
      'grid-template-rows: 1fr 1fr',
      'column-gap: 12px',
    ],
    icon: [
      'width: 54px',
      'height: 54px',
      `color: ${line === 1 ? color : '#ffffff'}`,
    ],
    img_cell: [
      'width: 62px',
      'height: 62px',
      'border-radius: 50%',
      `${line === 1 ? 'background: #1b1b1b' : `background: ${color}`}`,
    ],
    name: [
      'align-self: end',
      'justify-self: start',
      'font-size: 24px',
      'font-weight: 800',
      'line-height: 1.05',
      'white-space: normal',
      'text-align: left',
      `[[[ const issue = entity && !['Normal service', 'No Effect', 'unknown', 'unavailable'].includes(entity.state); return issue ? 'color: #ffffff' : 'color: var(--primary-text-color)'; ]]]`,
    ],
    state: [
      'align-self: start',
      'justify-self: start',
      'font-size: 22px',
      'font-weight: 900',
      'line-height: 1.1',
      'white-space: normal',
      'text-align: left',
      `[[[ const issue = entity && !['Normal service', 'No Effect', 'unknown', 'unavailable'].includes(entity.state); return issue ? 'color: #ffffff' : 'color: var(--primary-text-color)'; ]]]`,
    ],
  },
});

const dashboardConfig = {
  title: 'TTC Robot Speaker',
  views: [
    {
      title: 'Subway Issues',
      path: subwayViewPath,
      icon: 'mdi:subway-variant',
      cards: [
        {
          type: 'custom:button-card',
          entity: 'sensor.ttc_subway_status',
          name: 'TTC Subway',
          icon: 'mdi:subway-variant',
          show_state: true,
          styles: {
            card: ['min-height: 92px', 'padding: 14px', 'border-radius: 12px'],
            icon: ['width: 54px', 'height: 54px', 'color: #e31837'],
            name: ['font-size: 26px', 'font-weight: 900'],
            state: ['font-size: 24px', 'font-weight: 900'],
          },
        },
        {
          type: 'grid',
          columns: 1,
          square: false,
          cards: [
            lineButton(1, 'Line 1', '#fcd116'),
            lineButton(2, 'Line 2', '#00923f'),
            lineButton(4, 'Line 4', '#a21a68'),
            lineButton(5, 'Line 5', '#e87511'),
            lineButton(6, 'Line 6', '#d02c2f'),
          ],
        },
      ],
    },
    {
      title: 'Bus Streetcar',
      path: surfaceViewPath,
      icon: 'mdi:bus-clock',
      cards: [
        {
          type: 'custom:button-card',
          entity: 'sensor.ttc_surface_alerts',
          name: 'Bus & Streetcar',
          icon: 'mdi:bus-clock',
          show_state: true,
          state_display: "[[[ const n = Number(entity?.attributes?.active_route_count || entity?.state || 0); return n ? `${n} routes affected` : 'No current surface alerts'; ]]]",
          styles: {
            card: ['min-height: 104px', 'padding: 14px', 'border-radius: 12px'],
            icon: ['width: 58px', 'height: 58px', 'color: #d71920'],
            name: ['font-size: 28px', 'font-weight: 900'],
            state: ['font-size: 24px', 'font-weight: 900'],
          },
        },
        {
          type: 'markdown',
          content: `## Surface routes
{% set routes = state_attr('sensor.ttc_surface_alerts', 'routes') or [] %}
{% set active = routes | selectattr('active_count', 'gt', 0) | list %}
{% if active | count == 0 %}
<ha-icon icon="mdi:check-circle"></ha-icon> Buses and streetcars are normal.
{% else %}
{% for route in active[:8] %}
### {{ route.name }}
**{{ route.status }}**
{% endfor %}
{% endif %}`,
          card_mod: {
            style: `ha-card {
  padding: 8px 14px;
  border-radius: 12px;
}
ha-markdown h2 {
  font-size: 28px;
  line-height: 1.05;
  margin: 0 0 12px;
}
ha-markdown h3 {
  font-size: 24px;
  line-height: 1.08;
  margin: 14px 0 2px;
}
ha-markdown p {
  font-size: 22px;
  line-height: 1.15;
  margin: 0 0 8px;
}`,
          },
        },
      ],
    },
  ],
};

async function login() {
  if (process.env.HA_TOKEN) {
    return process.env.HA_TOKEN;
  }

  const clientId = 'https://ttchui.local/apply-ttc-subway-display';
  const open = await fetch(`${baseHttp}/auth/login_flow`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ client_id: clientId, handler: ['homeassistant', null], redirect_uri: `${clientId}?auth_callback=1` }),
  });
  if (!open.ok) throw new Error(`login_flow open failed: ${open.status} ${await open.text()}`);
  const openJson = await open.json();
  const flowId = openJson.flow_id;
  if (!flowId) throw new Error(`login_flow did not return flow_id: ${JSON.stringify(openJson)}`);

  const credentials = await fetch(`${baseHttp}/auth/login_flow/${flowId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ client_id: clientId, username, password }),
  });
  if (!credentials.ok) throw new Error(`login_flow credentials failed: ${credentials.status} ${await credentials.text()}`);
  const credentialsJson = await credentials.json();
  const code = credentialsJson.result;
  if (credentialsJson.type !== 'create_entry' || !code) {
    throw new Error(`login_flow did not complete: ${JSON.stringify(credentialsJson)}`);
  }

  const tokenResp = await fetch(`${baseHttp}/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      code,
      client_id: clientId,
    }),
  });
  if (!tokenResp.ok) throw new Error(`token exchange failed: ${tokenResp.status} ${await tokenResp.text()}`);
  const tokenJson = await tokenResp.json();
  if (!tokenJson.access_token) throw new Error(`token exchange did not return access_token: ${JSON.stringify(tokenJson)}`);
  return tokenJson.access_token;
}

function connect(token) {
  const ws = new WebSocket(wsUrl);
  let id = 1;
  const pending = new Map();

  function send(type, payload = {}) {
    const msg = { id: id++, type, ...payload };
    ws.send(JSON.stringify(msg));
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        pending.delete(msg.id);
        reject(new Error(`timeout ${type}`));
      }, 20000);
      pending.set(msg.id, { resolve, reject, type, timeout });
    });
  }

  const ready = new Promise((resolve, reject) => {
    ws.addEventListener('message', (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'auth_required') {
        ws.send(JSON.stringify({ type: 'auth', access_token: token }));
      } else if (msg.type === 'auth_invalid') {
        reject(new Error('Home Assistant WebSocket auth invalid'));
      } else if (msg.type === 'auth_ok') {
        resolve({ send, close: () => ws.close() });
      } else if (msg.id && pending.has(msg.id)) {
        const p = pending.get(msg.id);
        pending.delete(msg.id);
        clearTimeout(p.timeout);
        if (msg.success) p.resolve(msg);
        else p.reject(new Error(`${p.type}: ${JSON.stringify(msg.error)}`));
      }
    });
    ws.addEventListener('error', () => reject(new Error('Home Assistant WebSocket error')));
  });
  return ready;
}

async function ensureDashboard(client) {
  const list = (await client.send('lovelace/dashboards/list')).result || [];
  if (list.some((dashboard) => dashboard.url_path === dashboardPath)) {
    return;
  }

  await client.send('lovelace/dashboards/create', {
    url_path: dashboardPath,
    mode: 'storage',
    require_admin: false,
    show_in_sidebar: true,
    title: 'TTC Subway',
    icon: 'mdi:subway-variant',
  });
}

async function saveAutomation(token) {
  const displayAutomation = {
    alias: 'TTC Robot Speaker smart transit display',
    description: 'Shows subway issue status when any TTC subway line has a real issue; otherwise shows bus and streetcar status.',
    mode: 'restart',
    trigger: [
      { platform: 'homeassistant', event: 'start' },
      { platform: 'state', entity_id: displayEntity, to: 'idle', for: '00:00:20' },
      { platform: 'state', entity_id: displayEntity, to: 'off', for: '00:00:20' },
      ...lineEntities.map((entity_id) => ({ platform: 'state', entity_id })),
      { platform: 'state', entity_id: 'sensor.ttc_surface_alerts' },
      { platform: 'time_pattern', minutes: '/30' },
    ],
    condition: [],
    action: [
      {
        choose: [
          {
            conditions: [{ condition: 'template', value_template: lineIssueTemplate }],
            sequence: [
              {
                service: 'cast.show_lovelace_view',
                data: {
                  entity_id: displayEntity,
                  dashboard_path: dashboardPath,
                  view_path: subwayViewPath,
                },
              },
            ],
          },
        ],
        default: [
          {
            service: 'cast.show_lovelace_view',
            data: {
              entity_id: displayEntity,
              dashboard_path: dashboardPath,
              view_path: surfaceViewPath,
            },
          },
        ],
      },
    ],
  };

  const volumeAutomation = {
    alias: 'TTC subway issue Robot Speaker volume pulse',
    description: 'Pulses Robot Speaker volume when a TTC subway line changes into a real issue state.',
    mode: 'restart',
    trigger: [
      ...lineEntities.map((entity_id) => ({ platform: 'state', entity_id })),
    ],
    condition: [
      {
        condition: 'template',
        value_template: "{{ trigger.to_state is not none and trigger.to_state.state not in ['Normal service', 'No Effect', 'unknown', 'unavailable'] }}",
      },
      {
        condition: 'template',
        value_template: "{{ trigger.from_state is none or trigger.from_state.state != trigger.to_state.state }}",
      },
    ],
    action: [
      {
        repeat: {
          count: 3,
          sequence: [
            {
              service: 'media_player.volume_set',
              target: { entity_id: displayEntity },
              data: { volume_level: 1 },
            },
            { delay: { seconds: 2 } },
            {
              service: 'media_player.volume_set',
              target: { entity_id: displayEntity },
              data: { volume_level: 0.5 },
            },
            { delay: { seconds: 2 } },
            {
              service: 'media_player.volume_set',
              target: { entity_id: displayEntity },
              data: { volume_level: 1 },
            },
            { delay: { seconds: 2 } },
          ],
        },
      },
    ],
  };

  await saveAutomationConfig(token, 'ttc_robot_speaker_smart_transit_display', displayAutomation);
  await saveAutomationConfig(token, 'ttc_subway_issue_robot_speaker_volume_pulse', volumeAutomation);
}

async function saveAutomationConfig(token, id, automation) {
  const resp = await fetch(`${baseHttp}/api/config/automation/config/${id}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(automation),
  });
  if (!resp.ok) {
    throw new Error(`automation ${id} save failed: ${resp.status} ${await resp.text()}`);
  }
}

async function deleteAutomationConfig(token, id) {
  const resp = await fetch(`${baseHttp}/api/config/automation/config/${id}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  });
  const text = await resp.text();
  if (!resp.ok && resp.status !== 404 && !text.includes('Resource not found')) {
    throw new Error(`automation ${id} delete failed: ${resp.status} ${text}`);
  }
}

async function callService(token, domain, service, payload) {
  const resp = await fetch(`${baseHttp}/api/services/${domain}/${service}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    throw new Error(`${domain}.${service} failed: ${resp.status} ${await resp.text()}`);
  }
}

async function getState(token, entityId) {
  const resp = await fetch(`${baseHttp}/api/states/${entityId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) {
    throw new Error(`state ${entityId} failed: ${resp.status} ${await resp.text()}`);
  }
  return resp.json();
}

async function hasCurrentLineIssue(token) {
  const states = await Promise.all(lineEntities.map((entityId) => getState(token, entityId)));
  return states.some((state) => !normalLineStates.includes(state.state));
}

const token = await login();
const client = await connect(token);
try {
  await ensureDashboard(client);
  await client.send('lovelace/config/save', { url_path: dashboardPath, config: dashboardConfig });
  await client.send('lovelace/config', { url_path: dashboardPath });
  await saveAutomation(token);
  await deleteAutomationConfig(token, 'ttc_subway_default_robot_speaker');
  await deleteAutomationConfig(token, 'ttc_subway_default_metrolinx_display');
  await callService(token, 'automation', 'reload', {});
  await callService(token, 'media_player', 'turn_off', {
    entity_id: oldDisplayEntity,
  }).catch(async (error) => {
    console.warn(`Could not turn off old display ${oldDisplayEntity}: ${error.message}`);
    await callService(token, 'media_player', 'media_stop', { entity_id: oldDisplayEntity })
      .catch((stopError) => console.warn(`Could not stop old display ${oldDisplayEntity}: ${stopError.message}`));
  });
  const initialViewPath = await hasCurrentLineIssue(token) ? subwayViewPath : surfaceViewPath;
  await callService(token, 'cast', 'show_lovelace_view', {
    entity_id: displayEntity,
    dashboard_path: dashboardPath,
    view_path: initialViewPath,
  });
  console.log(`TTC Robot Speaker dashboard saved at /${dashboardPath}`);
  console.log(`Initial Robot Speaker view: ${initialViewPath}`);
  console.log(`Default cast target updated: ${displayEntity}`);
} finally {
  client.close();
}
