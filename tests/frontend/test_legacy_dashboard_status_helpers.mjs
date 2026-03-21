import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dashboardPath = path.resolve(__dirname, '../../grocy_ai_assistant/api/static/dashboard.js');

test('legacy dashboard defines shopping and recipe status getters for tab/topbar sync', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');

  assert.match(
    source,
    /function getShoppingStatusElement\(\) \{\s+return document\.getElementById\('status-shopping'\);\s+\}/,
  );
  assert.match(
    source,
    /function getRecipeStatusElement\(\) \{\s+return document\.getElementById\('status-recipes'\);\s+\}/,
  );
  assert.match(source, /function getStatusElementByTab\(tabName\)/);
  assert.match(source, /function syncTopbarStatusFromActiveTab\(\)/);
});
