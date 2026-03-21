import test from 'node:test';
import assert from 'node:assert/strict';

import {
  createShoppingSearchController,
  SEARCH_FLOW_STATES,
} from '../../grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/shopping-search-controller.js';

function createDeferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function createFakeTimerApi() {
  let now = 0;
  let nextId = 1;
  const timers = new Map();

  function setTimeout(callback, delay = 0) {
    const id = nextId++;
    timers.set(id, {
      id,
      callback,
      runAt: now + Number(delay || 0),
    });
    return id;
  }

  function clearTimeout(id) {
    timers.delete(id);
  }

  async function advanceBy(ms) {
    now += Number(ms || 0);
    while (true) {
      const dueTimers = Array.from(timers.values())
        .filter((timer) => timer.runAt <= now)
        .sort((left, right) => left.runAt - right.runAt || left.id - right.id);
      if (!dueTimers.length) break;

      for (const timer of dueTimers) {
        if (!timers.delete(timer.id)) continue;
        timer.callback();
        await Promise.resolve();
      }
    }
  }

  return {
    setTimeout,
    clearTimeout,
    advanceBy,
  };
}

function createController({ apiOverrides = {}, debounceMs = 250 } = {}) {
  const timerApi = createFakeTimerApi();
  const api = {
    searchVariants: async () => ({ response: { ok: true }, payload: [] }),
    searchProduct: async () => ({ response: { ok: true }, payload: { message: 'Produkt verarbeitet.' } }),
    addExistingProduct: async () => ({ response: { ok: true }, payload: { message: 'Produkt hinzugefügt.' } }),
    ...apiOverrides,
  };
  const controller = createShoppingSearchController({
    api,
    debounceMs,
    timerApi,
    getDefaultAmount: () => 1,
    getBestBeforeDate: () => '',
  });
  return { controller, timerApi, api };
}

test('debounces fast typing so only the latest variant request runs', async () => {
  const queries = [];
  const { controller, timerApi } = createController({
    apiOverrides: {
      searchVariants: async (query) => {
        queries.push(query);
        return { response: { ok: true }, payload: [] };
      },
    },
  });

  controller.actions.setQuery('mi');
  controller.actions.setQuery('mil');
  controller.actions.setQuery('milc');

  assert.equal(controller.getState().flowState, SEARCH_FLOW_STATES.TYPING);
  assert.deepEqual(queries, []);

  await timerApi.advanceBy(249);
  assert.deepEqual(queries, []);

  await timerApi.advanceBy(1);
  assert.deepEqual(queries, ['milc']);
  assert.equal(controller.getState().variantsRequestToken, 3);
  assert.equal(controller.getState().flowState, SEARCH_FLOW_STATES.VARIANTS_READY);
});

test('clears variants immediately and returns to idle on empty input', async () => {
  const { controller, timerApi } = createController({
    apiOverrides: {
      searchVariants: async () => ({
        response: { ok: true },
        payload: [{ id: 1, name: 'Milch 1L' }],
      }),
    },
  });

  controller.actions.setQuery('milch');
  await timerApi.advanceBy(250);
  assert.equal(controller.getState().variants.length, 1);
  assert.equal(controller.getState().flowState, SEARCH_FLOW_STATES.VARIANTS_READY);

  controller.actions.setQuery('');

  assert.equal(controller.getState().query, '');
  assert.deepEqual(controller.getState().variants, []);
  assert.equal(controller.getState().flowState, SEARCH_FLOW_STATES.IDLE);
  assert.equal(controller.getState().statusMessage, 'Bereit.');

  await timerApi.advanceBy(1000);
  assert.deepEqual(controller.getState().variants, []);
  assert.equal(controller.getState().flowState, SEARCH_FLOW_STATES.IDLE);
});

test('ignores stale variant responses after the user keeps typing', async () => {
  const pendingRequests = [];
  const { controller, timerApi } = createController({
    apiOverrides: {
      searchVariants: (query) => {
        const deferred = createDeferred();
        pendingRequests.push({ query, deferred });
        return deferred.promise;
      },
    },
  });

  controller.actions.setQuery('ap');
  await timerApi.advanceBy(250);
  assert.equal(pendingRequests.length, 1);
  assert.equal(controller.getState().flowState, SEARCH_FLOW_STATES.LOADING_VARIANTS);

  controller.actions.setQuery('apf');
  assert.equal(controller.getState().flowState, SEARCH_FLOW_STATES.TYPING);

  pendingRequests[0].deferred.resolve({
    response: { ok: true },
    payload: [{ id: 1, name: 'Apfel alt' }],
  });
  await Promise.resolve();

  assert.deepEqual(controller.getState().variants, []);
  assert.equal(controller.getState().flowState, SEARCH_FLOW_STATES.TYPING);

  await timerApi.advanceBy(250);
  assert.equal(pendingRequests.length, 2);
  assert.equal(pendingRequests[1].query, 'apf');

  pendingRequests[1].deferred.resolve({
    response: { ok: true },
    payload: [{ id: 2, name: 'Apfel neu' }],
  });
  await Promise.resolve();

  assert.deepEqual(controller.getState().variants, [{ id: 2, name: 'Apfel neu' }]);
  assert.equal(controller.getState().flowState, SEARCH_FLOW_STATES.VARIANTS_READY);
});

test('enter submit wins over a still-loading variant request', async () => {
  const variantDeferred = createDeferred();
  const submitted = [];
  const { controller, timerApi } = createController({
    apiOverrides: {
      searchVariants: () => variantDeferred.promise,
      searchProduct: async (payload) => {
        submitted.push(payload);
        return { response: { ok: true }, payload: { message: 'Produkt verarbeitet.' } };
      },
    },
  });

  controller.actions.setQuery('2 milch');
  await timerApi.advanceBy(250);
  assert.equal(controller.getState().flowState, SEARCH_FLOW_STATES.LOADING_VARIANTS);

  const submitResult = await controller.actions.searchProduct();
  assert.equal(submitResult.ok, true);
  assert.deepEqual(submitted, [{
    name: 'milch',
    amount: 2,
    best_before_date: '',
    force_create: false,
  }]);
  assert.equal(controller.getState().flowState, SEARCH_FLOW_STATES.SUCCESS);

  variantDeferred.resolve({
    response: { ok: true },
    payload: [{ id: 3, name: 'Milch veraltet' }],
  });
  await Promise.resolve();

  assert.deepEqual(controller.getState().variants, []);
  assert.equal(controller.getState().flowState, SEARCH_FLOW_STATES.SUCCESS);
  assert.equal(controller.getState().statusMessage, 'Produkt verarbeitet.');
});
