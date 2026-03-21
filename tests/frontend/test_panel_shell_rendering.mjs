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

test('dashboard panel ensures its shell exists before assigning child view models', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');

  assert.match(source, /connectedCallback\(\) \{\s+this\._ensureShell\(\);/);
  assert.match(
    source,
    /_ensureShell\(\) \{\s+if \(!this\.shadowRoot \|\| this\.shadowRoot\.querySelector\('grocy-ai-topbar'\)\) return;/,
  );
  assert.match(source, /_renderState\(state\) \{\s+this\._ensureShell\(\);/);
  assert.match(source, /const topbar = this\.shadowRoot\.querySelector\('grocy-ai-topbar'\);/);
  assert.match(source, /if \(!topbar \|\| !tabNav \|\| !shoppingTab \|\| !recipesTab \|\| !storageTab \|\| !notificationsTab \|\| !modals \|\| !scannerBridge\) \{/);
});
