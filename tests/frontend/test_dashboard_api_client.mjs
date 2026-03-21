import test from 'node:test';
import assert from 'node:assert/strict';

import { createDashboardApiClient } from '../../grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/dashboard-api-client.js';

test('dashboard api client forwards Home Assistant auth headers to proxy requests', async () => {
  const calls = [];
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, options });
    return {
      ok: true,
      async json() {
        return [];
      },
    };
  };

  const client = createDashboardApiClient({
    apiBasePath: '/api/grocy_ai_assistant/dashboard-proxy',
    getAuthHeaders: () => ({ Authorization: 'Bearer ha-access-token' }),
  });

  await client.fetchShoppingList();

  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, '/api/grocy_ai_assistant/dashboard-proxy/api/dashboard/shopping-list');
  assert.equal(calls[0].options.credentials, 'same-origin');
  assert.equal(calls[0].options.headers.Authorization, 'Bearer ha-access-token');

  delete globalThis.fetch;
});

test('dashboard api client keeps explicit request headers while adding auth headers', async () => {
  const calls = [];
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, options });
    return {
      ok: true,
      async json() {
        return { ok: true };
      },
    };
  };

  const client = createDashboardApiClient({
    apiBasePath: '/api/grocy_ai_assistant/dashboard-proxy',
    getAuthHeaders: () => ({ Authorization: 'Bearer ha-access-token' }),
  });

  await client.searchProduct({ name: 'Milch', amount: 1, best_before_date: '', force_create: false });

  assert.equal(calls.length, 1);
  assert.equal(calls[0].options.method, 'POST');
  assert.equal(calls[0].options.headers.Authorization, 'Bearer ha-access-token');
  assert.equal(calls[0].options.headers['Content-Type'], 'application/json');

  delete globalThis.fetch;
});
