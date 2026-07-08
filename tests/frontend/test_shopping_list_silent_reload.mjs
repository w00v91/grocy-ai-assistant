import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { createShoppingSearchController } from '../../grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/shopping-search-controller.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dashboardPath = path.resolve(
  __dirname,
  '../../grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js',
);

const SEARCH_IN_FLIGHT_MESSAGE = 'Eine identische Produktsuche läuft bereits. Bitte kurz warten und dann erneut versuchen.';

test('search_in_flight helper text is treated as an active shopping search message during silent list reload errors', async () => {
  const controller = createShoppingSearchController({
    api: {
      async searchProduct() {
        return {
          response: { ok: true },
          payload: {
            success: false,
            action: 'search_in_flight',
            message: SEARCH_IN_FLIGHT_MESSAGE,
          },
        };
      },
    },
  });

  controller.actions.setQuery('Milch');
  const result = await controller.actions.searchProduct();
  const searchState = controller.getState();

  assert.equal(result.ok, true);
  assert.equal(searchState.statusMessage, SEARCH_IN_FLIGHT_MESSAGE);
  assert.equal(searchState.errorMessage, '');

  const source = await fs.readFile(dashboardPath, 'utf8');
  assert.match(source, /_hasActiveShoppingSearchMessage\(searchState = this\._shoppingSearch\?\.getState\?\.\(\) \|\| \{\}\) \{/);
  assert.match(source, /return String\(searchState\.statusMessage \|\| ''\)\.includes\('identische Produktsuche läuft bereits'\);/);
  assert.match(source, /silent && hasActiveSearchMessage \? \{\} : \{ status: `Fehler: \$\{message\}` \}/);
  assert.match(source, /suppressTopbarError: silent && this\._hasActiveShoppingSearchMessage\(\),/);
  assert.match(source, /if \(!suppressTopbarError\) \{\s+this\._store\.patch\(\{ topbarStatus: `Fehler: \$\{error\.message\}` \}\);\s+\}/);

  controller.dispose();
});
