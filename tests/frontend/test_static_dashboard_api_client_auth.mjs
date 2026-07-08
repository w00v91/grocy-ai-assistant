import test from 'node:test';
import assert from 'node:assert/strict';

import { createDashboardApiClient } from '../../grocy_ai_assistant/api/static/dashboard-api-client.js';

test('static dashboard api client relies on ingress cookies when no explicit auth header is provided', async () => {
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
    ingressPrefix: '/api/hassio_ingress/token',
  });

  await client.fetchShoppingList();

  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, '/api/hassio_ingress/token/api/dashboard/shopping-list');
  assert.equal(calls[0].options.credentials, 'same-origin');
  assert.equal(calls[0].options.headers.Authorization, undefined);

  delete globalThis.fetch;
});

test('static dashboard api client can use explicit non-html auth provider', async () => {
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
    getAuthHeaders: () => ({ Authorization: 'Bearer stored-api-key' }),
  });

  await client.fetchShoppingList();

  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, '/api/dashboard/shopping-list');
  assert.equal(calls[0].options.credentials, 'same-origin');
  assert.equal(calls[0].options.headers.Authorization, 'Bearer stored-api-key');

  delete globalThis.fetch;
});
