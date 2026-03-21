import test from 'node:test';
import assert from 'node:assert/strict';

import { createDashboardStore } from '../../grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/dashboard-store.js';

test('dashboard store updates nested tab subtrees via patchIn and setIn', () => {
  const store = createDashboardStore({
    shopping: {
      status: 'Bereit.',
      viewState: { loaded: false, loading: false, error: '', empty: false, editing: false },
      scanner: { open: false, status: 'Bereit.', scope: 'shopping' },
    },
  });

  store.patchIn('shopping', { status: 'Lädt…' });
  store.patchIn(['shopping', 'viewState'], { loading: true });
  store.setIn(['shopping', 'scanner'], { open: true, status: 'Scanner geöffnet.', scope: 'shopping' });

  assert.deepEqual(store.getIn(['shopping', 'viewState']), {
    loaded: false,
    loading: true,
    error: '',
    empty: false,
    editing: false,
  });
  assert.deepEqual(store.getIn(['shopping', 'scanner']), {
    open: true,
    status: 'Scanner geöffnet.',
    scope: 'shopping',
  });
  assert.equal(store.getIn('shopping.status'), 'Lädt…');
});

test('dashboard store updateIn preserves sibling tab state while changing notifications fallback data', () => {
  const store = createDashboardStore({
    shopping: { status: 'Bereit.' },
    notifications: {
      status: 'Fallback bereit.',
      legacyFallbackUrl: '',
      viewState: { loaded: true, loading: false, error: '', empty: true, editing: false },
    },
  });

  store.updateIn(['notifications', 'viewState'], (viewState) => ({
    ...viewState,
    empty: false,
    loaded: true,
  }));
  store.patchIn('notifications', { legacyFallbackUrl: '/api/grocy_ai_assistant/dashboard-proxy/' });

  assert.equal(store.getIn('shopping.status'), 'Bereit.');
  assert.equal(store.getIn('notifications.legacyFallbackUrl'), '/api/grocy_ai_assistant/dashboard-proxy/');
  assert.equal(store.getIn(['notifications', 'viewState', 'empty']), false);
});
