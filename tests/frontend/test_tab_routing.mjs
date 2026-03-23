import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildPanelUrlWithTab,
  DEFAULT_TAB,
  resolveTabFromLocation,
} from '../../grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/tab-routing.js';

test('resolveTabFromLocation reads storage tab from query parameter', () => {
  const tab = resolveTabFromLocation(new URL('https://example.local/grocy-ai?tab=storage'));

  assert.equal(tab, 'storage');
});

test('resolveTabFromLocation falls back to shopping for removed notifications query parameter', () => {
  const tab = resolveTabFromLocation(new URL('https://example.local/grocy-ai?tab=notifications'));

  assert.equal(tab, DEFAULT_TAB);
});

test('resolveTabFromLocation falls back to shopping for invalid tabs', () => {
  const tab = resolveTabFromLocation(new URL('https://example.local/grocy-ai?tab=unknown'));

  assert.equal(tab, DEFAULT_TAB);
});

test('resolveTabFromLocation falls back to route segment when query parameter is missing', () => {
  const tab = resolveTabFromLocation(
    new URL('https://example.local/config'),
    { prefix: '/lovelace', path: '/grocy-ai/storage' },
  );

  assert.equal(tab, 'storage');
});

test('buildPanelUrlWithTab normalizes the next browser URL', () => {
  const nextUrl = buildPanelUrlWithTab(
    new URL('https://example.local/grocy-ai?tab=shopping#tab=notifications'),
    'notifications',
  );

  assert.equal(nextUrl, '/grocy-ai?tab=shopping');
});
