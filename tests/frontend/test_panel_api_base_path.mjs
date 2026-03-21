import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildLegacyDashboardUrl,
  detectIngressBasePath,
  resolveDashboardApiBasePath,
} from '../../grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/panel-api-base-path.js';

test('detectIngressBasePath reads the real ingress session prefix from the browser path', () => {
  assert.equal(
    detectIngressBasePath('/api/hassio_ingress/71139b3d_grocy_ai_assistant/some/view'),
    '/api/hassio_ingress/71139b3d_grocy_ai_assistant',
  );
});

test('resolveDashboardApiBasePath prefers the Home Assistant proxy base path from panel config', async () => {
  const apiBasePath = await resolveDashboardApiBasePath({
    panelConfig: { dashboard_api_base_path: '/api/grocy_ai_assistant/dashboard-proxy' },
    location: new URL('http://homeassistant.local:8123/grocy-ai'),
  });

  assert.equal(apiBasePath, '/api/grocy_ai_assistant/dashboard-proxy');
});

test('buildLegacyDashboardUrl reuses the resolved proxy base path for legacy bridges', () => {
  assert.equal(
    buildLegacyDashboardUrl('/api/grocy_ai_assistant/dashboard-proxy', '/api/hassio_ingress/grocy_ai_assistant/'),
    '/api/grocy_ai_assistant/dashboard-proxy/',
  );
});
