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


test('topbar markup no longer renders panel URL hints or quicklink pills', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');
  const topbarSection = source.slice(
    source.indexOf('class GrocyAITopbar extends HTMLElement'),
    source.indexOf('class GrocyAITabNav extends HTMLElement'),
  );

  assert.match(topbarSection, /<header class=\"topbar\">/);
  assert.doesNotMatch(topbarSection, /topbar-path-hint/);
  assert.doesNotMatch(topbarSection, /topbar-quicklinks/);
  assert.doesNotMatch(topbarSection, /quicklink-button/);
  assert.doesNotMatch(topbarSection, /shopping-open-scanner/);
});

test('dashboard panel keeps product-picture requests on the HA proxy before the API client is ready', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');

  assert.match(source, /function resolvePanelImageUrl\(url, dashboardApi, options = \{\}\)/);
  assert.match(source, /const normalizedApiBasePath = String\(options\?\.apiBasePath \|\| ''\)\.replace\(\/\\\/\+\$\/, ''\);/);
  assert.match(source, /return normalizedApiBasePath \? `\$\{normalizedApiBasePath\}\$\{normalizedPath\}` : normalizedPath;/);
  assert.match(source, /const panelImageApiBasePath = this\._dashboardApiBasePath\s+\|\|\s+String\(panelConfig\?\.dashboard_api_base_path \|\| panelConfig\?\.api_base_path \|\| ''\)\.replace\(\/\\\/\+\$\/, ''\);/);
  assert.match(source, /resolveImageUrl: \(url\) => resolvePanelImageUrl\(url, this\._dashboardApi, \{ apiBasePath: panelImageApiBasePath \}\),/);
});

test('shopping tab and search bar keep their stable DOM shells instead of replacing them with innerHTML', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');
  const searchBarSection = source.slice(
    source.indexOf('class GrocyAIShoppingSearchBar extends HTMLElement'),
    source.indexOf('class GrocyAIShoppingTab extends HTMLElement'),
  );
  const shoppingTabSection = source.slice(
    source.indexOf('class GrocyAIShoppingTab extends HTMLElement'),
    source.indexOf('class GrocyAILegacyBridgeTab extends HTMLElement'),
  );

  assert.match(searchBarSection, /class GrocyAIShoppingSearchBar extends HTMLElement/);
  assert.match(searchBarSection, /_ensureStructure\(\) \{\s+if \(this\._elements\) return;/);
  assert.doesNotMatch(
    searchBarSection,
    /_render\(\) \{[\s\S]*?this\.innerHTML\s*=/,
  );

  assert.match(shoppingTabSection, /class GrocyAIShoppingTab extends HTMLElement/);
  assert.match(shoppingTabSection, /heroCard\.append\(heroHeader, searchBar\);/);
  assert.doesNotMatch(
    shoppingTabSection,
    /_render\(\) \{[\s\S]*?this\.innerHTML\s*=/,
  );
  assert.match(shoppingTabSection, /this\._elements\.searchBar\.viewModel = \{\s+\.\.\.model,\s+\};/);
});

test('native panel binds shared shopping image fallbacks after list and variant renders', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');

  assert.match(source, /import \{ bindShoppingImageFallbacks, escapeHtml, formatAmount, formatBadgeValue, formatStockCount, renderShoppingListItemCard, renderShoppingVariantCard, resolveShoppingImageSource \} from '\.\/shopping-ui\.js';/);
  assert.match(source, /variantGrid\.replaceChildren\(\.\.\.nodes\);\s+bindShoppingImageFallbacks\(this\);/);
  assert.match(source, /list\.replaceChildren\(\.\.\.items\.map\(\(item\) => this\._createShoppingListItem\(item, model\)\)\);\s+bindShoppingImageFallbacks\(this\);/);
});


test('recipes, storage, and modal renders restore focused form controls after rerenders', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');

  assert.match(source, /function captureFocusedFormControl\(root\) \{/);
  assert.match(source, /function restoreFocusedFormControl\(root, snapshot\) \{/);
  assert.match(source, /class GrocyAIDashboardModals extends HTMLElement \{[\s\S]*?_render\(\) \{\s+const snapshot = captureFocusedFormControl\(this\);[\s\S]*?restoreFocusedFormControl\(this, snapshot\);/);
  assert.match(source, /class GrocyAIRecipesTab extends HTMLElement \{[\s\S]*?_render\(\) \{\s+const snapshot = captureFocusedFormControl\(this\);[\s\S]*?restoreFocusedFormControl\(this, snapshot\);/);
  assert.match(source, /class GrocyAIStorageTab extends HTMLElement \{[\s\S]*?_render\(\) \{\s+const snapshot = captureFocusedFormControl\(this\);[\s\S]*?restoreFocusedFormControl\(this, snapshot\);/);
});

test('recipes, storage, and modal setters skip full rerenders for volatile field-only updates', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');

  assert.match(source, /class GrocyAIDashboardModals extends HTMLElement \{[\s\S]*?this\._renderSignature = null;[\s\S]*?const nextSignature = JSON\.stringify\(\{[\s\S]*?createMethod: value\?\.recipes\?\.createModal\?\.method \|\| 'webscrape'[\s\S]*?\}\);[\s\S]*?if \(nextSignature === this\._renderSignature\) return;/);
  assert.match(source, /class GrocyAIRecipesTab extends HTMLElement \{[\s\S]*?this\._renderSignature = null;[\s\S]*?const nextSignature = JSON\.stringify\(\{[\s\S]*?stockProducts: buildStockSignature\(/);
  assert.match(source, /class GrocyAIStorageTab extends HTMLElement \{[\s\S]*?this\._renderSignature = null;[\s\S]*?const nextSignature = JSON\.stringify\(\{[\s\S]*?deleteModal: \{[\s\S]*?itemId: value\?\.deleteModal\?\.itemId \?\? null[\s\S]*?\}\);[\s\S]*?if \(nextSignature === this\._renderSignature\) return;/);
});

test('recipes and storage tabs are natively migrated in the panel shell', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');

  assert.match(source, /import \{ renderActionRow, renderCardContainer, renderMetaBadges, renderStateCard, renderTileGrid, renderTwoColumnCardGroup \} from '\.\/shared-panel-ui\.js';/);
  assert.match(source, /const MIGRATED_TABS = new Set\(\['shopping', 'recipes', 'storage'\]\);/);
  assert.match(source, /function buildRecipesTabMarkup\(model = \{\}\) \{/);
  assert.match(source, /renderTwoColumnCardGroup\(recipeCards, \{ className: 'recipes-card-group' \}\)/);
  assert.match(source, /dataset: \{ action: 'recipes-load-suggestions' \}/);
  assert.match(source, /data-action="recipes-load-expiring"|dataset: \{ action: 'recipes-load-expiring' \}/);
  assert.match(source, /dataset: \{ action: 'recipes-open-create' \}/);
  assert.match(source, /class GrocyAIRecipesTab extends HTMLElement \{[\s\S]*?buildRecipesTabMarkup\(model\)/);
  assert.match(source, /function buildStorageTabMarkup\(model = \{\}\) \{/);
  assert.match(source, /data-role="storage-filter"/);
  assert.match(source, /class="storage-item swipe-item variant-card"/);
  assert.match(source, /storage-products-list--native/);
  assert.match(source, /data-action="storage-open-delete"/);
  assert.match(source, /class GrocyAIStorageTab extends HTMLElement \{[\s\S]*?buildStorageTabMarkup\(model\)/);
  assert.match(source, /selector: '\.storage-item\.swipe-item'/);
  assert.match(source, /_initializeStorageTab\(\) \{/);
  assert.match(source, /api\.updateStockProduct\(editModal\.itemId/);
  assert.match(source, /api\.consumeStockProduct\(consumeModal\.itemId/);
  assert.match(source, /api\.deleteStockProduct\(deleteModal\.itemId/);
});
