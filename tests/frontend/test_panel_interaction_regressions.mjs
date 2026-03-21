import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dashboardPath = path.resolve(
  __dirname,
  '../../grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js',
);

async function readDashboardSource() {
  return fs.readFile(dashboardPath, 'utf8');
}

test('shopping list cards render proxied product images in the native panel', async () => {
  const source = await readDashboardSource();

  assert.match(source, /function toImageSource\(url\) \{/);
  assert.match(source, /class="shopping-item-card__image"/);
  assert.match(source, /src="\$\{escapeHtml\(toImageSource\(item\.picture_url\)\)\}"/);
});

test('shopping tab restores search focus after rerenders', async () => {
  const source = await readDashboardSource();

  assert.match(source, /const focusSnapshot = this\._captureFocusSnapshot\(\);/);
  assert.match(source, /this\._restoreFocusSnapshot\(focusSnapshot\);/);
  assert.match(source, /selector: '\[data-role="shopping-query"\]'/);
});

test('modal editors restore focus and polling pauses during interaction', async () => {
  const source = await readDashboardSource();

  assert.match(source, /supportedFields = new Set\(\['amount', 'note', 'mhd'\]\)/);
  assert.match(source, /_shouldPauseShoppingPolling\(state\) \{/);
  assert.match(source, /\|\| hasInteractiveSearchState/);
  assert.match(source, /if \(this\._shouldPauseShoppingPolling\(latestState\)\) return;/);
});
