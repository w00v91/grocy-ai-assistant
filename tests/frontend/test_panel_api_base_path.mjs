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

test('resolveDashboardApiBasePath creates an ingress session for native panels outside ingress paths', async () => {
  const calls = [];
  const apiBasePath = await resolveDashboardApiBasePath({
    panelConfig: { legacy_dashboard_url: '/api/hassio_ingress/grocy_ai_assistant/' },
    hass: {
      user: { id: 'user-123' },
      async callApi(method, path, payload) {
        calls.push({ method, path, payload });
        return { data: { session: '71139b3d_grocy_ai_assistant' } };
      },
    },
    location: new URL('http://homeassistant.local:8123/grocy-ai'),
  });

  assert.equal(apiBasePath, '/api/hassio_ingress/71139b3d_grocy_ai_assistant');
  assert.deepEqual(calls, [{
    method: 'POST',
    path: 'hassio/ingress/session',
    payload: { user_id: 'user-123' },
  }]);
});

test('buildLegacyDashboardUrl reuses the resolved ingress session for legacy bridges', () => {
  assert.equal(
    buildLegacyDashboardUrl('/api/hassio_ingress/71139b3d_grocy_ai_assistant', '/api/hassio_ingress/grocy_ai_assistant/'),
    '/api/hassio_ingress/71139b3d_grocy_ai_assistant/',
  );
});
