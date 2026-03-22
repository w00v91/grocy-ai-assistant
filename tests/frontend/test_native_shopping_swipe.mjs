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
const sharedShoppingCssPath = path.resolve(
  __dirname,
  '../../grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/shopping-ui.css',
);

test('shared swipe helper exports reusable binding utilities', () => {
  assert.equal(typeof bindSwipeInteractions, 'function');
  assert.equal(typeof resetSwipeVisualState, 'function');
});

test('shared swipe helper keeps touch listeners for native Home Assistant mobile dashboards', async () => {
  const source = await fs.readFile(
    path.resolve(
      __dirname,
      '../../grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/swipe-interactions.js',
    ),
    'utf8',
  );

  assert.match(source, /let lastTouchStartAt = 0;/);
  assert.match(source, /const handleTouchStart = \(event\) => \{/);
  assert.match(source, /item\.addEventListener\('touchstart', handleTouchStart, \{ \.\.\.signalOptions, passive: true \}\);/);
  assert.match(source, /item\.addEventListener\('touchmove', handleTouchMove, \{ \.\.\.signalOptions, passive: false \}\);/);
  assert.match(source, /event\.pointerType === 'touch' && \(Date\.now\(\) - lastTouchStartAt\) < 800/);
});

test('native shopping tab renders swipe shopping items and rebinds swipe interactions', async () => {
  const source = await fs.readFile(nativeDashboardPath, 'utf8');

  assert.match(source, /import \{ bindSwipeInteractions \} from '\.\/swipe-interactions\.js';/);
  assert.match(source, /this\._cleanupSwipe = null;/);
  assert.match(source, /className = 'shopping-list-native__item shopping-item swipe-item';/);
  assert.match(source, /swipe-item-action swipe-item-action-left/);
  assert.match(source, /swipe-item-action swipe-item-action-right/);
  assert.match(source, /className: 'amount-increment-button'/);
  assert.match(source, /className: 'mhd-picker-button'/);
  assert.match(source, /rootClassName: 'shopping-item-card shopping-item-card--legacy'/);
  assert.match(source, /contextFields: \['location'\]/);
  assert.match(source, /stockBadgePlacement: 'aside'/);
  assert.match(source, /selector: '\.shopping-item\.swipe-item'/);
  assert.match(source, /interactiveElementSelector: '\.amount-increment-button, \.mhd-picker-button'/);
  assert.match(source, /new CustomEvent\('shopping-open-detail'/);
  assert.match(source, /new CustomEvent\('shopping-complete-item'/);
  assert.match(source, /new CustomEvent\('shopping-delete-item'/);
});

test('native storage tab renders legacy-style swipe list items and rebinds swipe interactions', async () => {
  const source = await fs.readFile(nativeDashboardPath, 'utf8');

  assert.match(source, /class GrocyAIStorageTab extends HTMLElement/);
  assert.match(source, /this\._cleanupSwipe = null;/);
  assert.match(source, /class="storage-item swipe-item variant-card"/);
  assert.match(source, /rootClassName: 'shopping-item-card shopping-item-card--legacy storage-item-card'/);
  assert.match(source, /stockBadgePlacement: 'main'/);
  assert.match(source, /mhdBadge: \{[\s\S]*?hideLabel: true,[\s\S]*?\}/);
  assert.match(source, /value: stockLabel/);
  assert.match(source, /variant: item\?\.in_stock \? 'stock' : 'neutral'/);
  assert.match(source, /hideLabel: true/);
  assert.match(source, /location_name: item\?\.location_name/);
  assert.doesNotMatch(source, /storage-item-delete-button/);
  assert.match(source, /selector: '\.storage-item\.swipe-item'/);
  assert.doesNotMatch(source, /interactiveElementSelector: '\.storage-item-delete-button'/);
  assert.match(source, /new CustomEvent\('storage-open-edit'/);
  assert.match(source, /const actionName = payload\.inStock \? 'storage-open-consume' : 'storage-open-edit';/);
  assert.match(source, /bindShoppingImageFallbacks\(this\);\s+this\._rebindSwipeInteractions\(\);/);
});

test('legacy dashboard reuses the shared swipe utility import', async () => {
  const source = await fs.readFile(legacyDashboardPath, 'utf8');

  assert.match(source, /import \{ bindSwipeInteractions, resetSwipeVisualState \} from '\.\/panel-frontend\/swipe-interactions\.js';/);
  assert.doesNotMatch(source, /function bindSwipeInteractions\(/);
});

test('shared shopping card CSS keeps legacy swipe cards in their horizontal layout on narrow screens', async () => {
  const source = await fs.readFile(sharedShoppingCssPath, 'utf8');

  assert.match(source, /\.shopping-item-card--legacy \.shopping-card__surface \{\s+grid-template-columns: auto minmax\(0, 1fr\);/);
  assert.match(source, /\.shopping-card__body--swipe \{\s+grid-template-columns: minmax\(0, 1fr\) minmax\(148px, auto\);/);
  assert.match(source, /\.shopping-item-card--legacy \.shopping-card__body--swipe \{\s+align-items: center;/);
  assert.match(source, /@media \(max-width: 640px\) \{[\s\S]*?\.shopping-card__body--swipe \{\s+grid-template-columns: minmax\(0, 1fr\);[\s\S]*?\.shopping-item-card--legacy \.shopping-card__surface \{\s+grid-template-columns: auto minmax\(0, 1fr\);[\s\S]*?\.shopping-item-card--legacy \.shopping-card__body--swipe \{\s+grid-template-columns: minmax\(0, 1fr\) auto;[\s\S]*?\.shopping-item-card--legacy \.shopping-card__aside,[\s\S]*?justify-items: end;/);
});
