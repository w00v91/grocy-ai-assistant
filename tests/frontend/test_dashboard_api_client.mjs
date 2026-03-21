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

test('dashboard api client routes native scanner requests through v1 endpoints', async () => {
  const calls = [];
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, options });
    return {
      ok: true,
      async json() {
        return { success: true };
      },
    };
  };

  const client = createDashboardApiClient({
    apiBasePath: '/api/grocy_ai_assistant/dashboard-proxy',
    getAuthHeaders: () => ({ Authorization: 'Bearer ha-access-token' }),
  });

  await client.lookupBarcode('1234567890123');
  await client.scanImage('base64-image');

  assert.equal(calls[0].url, '/api/grocy_ai_assistant/dashboard-proxy/api/v1/barcode/1234567890123');
  assert.equal(calls[0].options.headers.Authorization, 'Bearer ha-access-token');
  assert.equal(calls[1].url, '/api/grocy_ai_assistant/dashboard-proxy/api/v1/scan/image');
  assert.equal(calls[1].options.method, 'POST');
  assert.equal(calls[1].options.headers['Content-Type'], 'application/json');
  assert.match(calls[1].options.body, /base64-image/);

  delete globalThis.fetch;
});

test('dashboard api client routes native storage requests through dashboard stock endpoints', async () => {
  const calls = [];
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, options });
    return {
      ok: true,
      async json() {
        return { success: true };
      },
    };
  };

  const client = createDashboardApiClient({
    apiBasePath: '/api/grocy_ai_assistant/dashboard-proxy',
    getAuthHeaders: () => ({ Authorization: 'Bearer ha-access-token' }),
  });

  await client.consumeStockProduct(99, { amount: 2, productId: 77 });
  await client.updateStockProduct(99, { amount: 3, best_before_date: '2026-04-01', location_id: 5 }, { productId: 77 });
  await client.deleteStockProduct(99, { productId: 77 });

  assert.equal(calls[0].url, '/api/grocy_ai_assistant/dashboard-proxy/api/dashboard/stock-products/99/consume?product_id=77');
  assert.equal(calls[0].options.method, 'POST');
  assert.equal(calls[0].options.headers.Authorization, 'Bearer ha-access-token');
  assert.equal(calls[0].options.headers['Content-Type'], 'application/json');
  assert.match(calls[0].options.body, /"amount":2/);

  assert.equal(calls[1].url, '/api/grocy_ai_assistant/dashboard-proxy/api/dashboard/stock-products/99?product_id=77');
  assert.equal(calls[1].options.method, 'PUT');
  assert.equal(calls[1].options.headers.Authorization, 'Bearer ha-access-token');
  assert.equal(calls[1].options.headers['Content-Type'], 'application/json');
  assert.match(calls[1].options.body, /"location_id":5/);

  assert.equal(calls[2].url, '/api/grocy_ai_assistant/dashboard-proxy/api/dashboard/stock-products/99?product_id=77');
  assert.equal(calls[2].options.method, 'DELETE');
  assert.equal(calls[2].options.headers.Authorization, 'Bearer ha-access-token');

  delete globalThis.fetch;
});
