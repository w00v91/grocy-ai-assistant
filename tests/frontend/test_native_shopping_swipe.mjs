import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  bindSwipeInteractions,
  resetSwipeVisualState,
} from '../../grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/swipe-interactions.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const nativeDashboardPath = path.resolve(
  __dirname,
  '../../grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js',
);
const legacyDashboardPath = path.resolve(
  __dirname,
  '../../grocy_ai_assistant/api/static/dashboard.js',
);

test('shared swipe helper exports reusable binding utilities', () => {
  assert.equal(typeof bindSwipeInteractions, 'function');
  assert.equal(typeof resetSwipeVisualState, 'function');
});

test('native shopping tab renders swipe shopping items and rebinds swipe interactions', async () => {
  const source = await fs.readFile(nativeDashboardPath, 'utf8');

  assert.match(source, /import \{ bindSwipeInteractions \} from '\.\/swipe-interactions\.js';/);
  assert.match(source, /this\._cleanupSwipe = null;/);
  assert.match(source, /className = 'shopping-list-native__item shopping-item swipe-item';/);
  assert.match(source, /swipe-item-action swipe-item-action-left/);
  assert.match(source, /swipe-item-action swipe-item-action-right/);
  assert.match(source, /selector: '\.shopping-item\.swipe-item'/);
  assert.match(source, /interactiveElementSelector: '\.shopping-card__actions button'/);
  assert.match(source, /new CustomEvent\('shopping-open-detail'/);
  assert.match(source, /new CustomEvent\('shopping-complete-item'/);
  assert.match(source, /new CustomEvent\('shopping-delete-item'/);
});

test('legacy dashboard reuses the shared swipe utility import', async () => {
  const source = await fs.readFile(legacyDashboardPath, 'utf8');

  assert.match(source, /import \{ bindSwipeInteractions, resetSwipeVisualState \} from '\.\/panel-frontend\/swipe-interactions\.js';/);
  assert.doesNotMatch(source, /function bindSwipeInteractions\(/);
});
