import test from 'node:test';
import assert from 'node:assert/strict';

import {
  createShoppingSearchController,
  SEARCH_FLOW_STATES,
} from '../../grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/shopping-search-controller.js';

function installWindowStub() {
  const timers = new Map();
  let nextTimerId = 1;
  globalThis.window = {
    setTimeout(callback) {
      const timerId = nextTimerId++;
      timers.set(timerId, callback);
      return timerId;
    },
    clearTimeout(timerId) {
      timers.delete(timerId);
    },
  };

  return {
    runLatestTimer() {
      const latestTimerId = Array.from(timers.keys()).at(-1);
      const callback = timers.get(latestTimerId);
      timers.delete(latestTimerId);
      callback?.();
    },
    cleanup() {
      delete globalThis.window;
    },
  };
}

test('loadVariants keeps amount-prefixed input and queries only the product name', async () => {
  const windowStub = installWindowStub();
  const apiCalls = [];
  const controller = createShoppingSearchController({
    api: {
      async searchVariants(query) {
        apiCalls.push(query);
        return {
          response: { ok: true },
          payload: [{ id: 42, name: 'Hafermilch Barista', source: 'grocy' }],
        };
      },
    },
  });

  controller.actions.setQuery('2 Hafermilch');
  windowStub.runLatestTimer();
  await new Promise((resolve) => setTimeout(resolve, 0));

  const state = controller.getState();
  assert.deepEqual(apiCalls, ['Hafermilch']);
  assert.equal(state.query, '2 Hafermilch');
  assert.equal(state.parsedAmount, 2);
  assert.equal(state.flowState, SEARCH_FLOW_STATES.VARIANTS_READY);
  assert.equal(state.statusMessage, 'Wähle einen Treffer oder starte die Suche mit Enter.');
  assert.equal(state.variants.length, 1);

  controller.dispose();
  windowStub.cleanup();
});

test('selectVariant reuses the amount prefix when AI/input suggestions trigger a submit', async () => {
  const windowStub = installWindowStub();
  const searchProductCalls = [];
  const controller = createShoppingSearchController({
    api: {
      async searchProduct(payload) {
        searchProductCalls.push(payload);
        return {
          response: { ok: true },
          payload: { message: 'Produkt hinzugefügt.' },
        };
      },
    },
  });

  controller.actions.setQuery('2 Hafermilch');
  await controller.actions.selectVariant({
    productId: '',
    productName: 'Haferdrink',
    amount: 2,
    source: 'ai',
  });

  const state = controller.getState();
  assert.equal(state.query, '2 Haferdrink');
  assert.equal(searchProductCalls.length, 1);
  assert.deepEqual(searchProductCalls[0], {
    name: 'Haferdrink',
    amount: 2,
    best_before_date: '',
    force_create: false,
  });
  assert.equal(state.flowState, SEARCH_FLOW_STATES.SUCCESS);

  controller.dispose();
  windowStub.cleanup();
});


test('selectVariant uses productSource from dataset and forces creation for input variants', async () => {
  const windowStub = installWindowStub();
  const searchProductCalls = [];
  const controller = createShoppingSearchController({
    api: {
      async searchProduct(payload) {
        searchProductCalls.push(payload);
        return {
          response: { ok: true },
          payload: { message: 'Produkt hinzugefügt.' },
        };
      },
    },
  });

  controller.actions.setQuery('Wachteleier');
  await controller.actions.selectVariant({
    productId: '',
    productName: 'Wachteleier',
    amount: 1,
    productSource: 'input',
  });

  const state = controller.getState();
  assert.equal(state.query, 'Wachteleier');
  assert.equal(searchProductCalls.length, 1);
  assert.deepEqual(searchProductCalls[0], {
    name: 'Wachteleier',
    amount: 1,
    best_before_date: '',
    force_create: true,
  });
  assert.equal(state.flowState, SEARCH_FLOW_STATES.SUCCESS);

  controller.dispose();
  windowStub.cleanup();
});

test('selectVariant keeps suggestion text without adding an implicit 1-prefix', async () => {
  const windowStub = installWindowStub();
  const searchProductCalls = [];
  const controller = createShoppingSearchController({
    api: {
      async searchProduct(payload) {
        searchProductCalls.push(payload);
        return {
          response: { ok: true },
          payload: { message: 'Produkt hinzugefügt.' },
        };
      },
    },
  });

  controller.actions.setQuery('Hafermilch');
  await controller.actions.selectVariant({
    productId: '',
    productName: 'Haferdrink',
    amount: 1,
    productSource: 'ai',
  });

  const state = controller.getState();
  assert.equal(state.query, 'Haferdrink');
  assert.equal(searchProductCalls.length, 1);
  assert.deepEqual(searchProductCalls[0], {
    name: 'Haferdrink',
    amount: 1,
    best_before_date: '',
    force_create: false,
  });
  assert.equal(state.flowState, SEARCH_FLOW_STATES.SUCCESS);

  controller.dispose();
  windowStub.cleanup();
});
