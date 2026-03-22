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
const dashboardCssPath = path.resolve(
  __dirname,
  '../../grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.css',
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


test('tab navigation only renders native shopping, recipes, and storage links', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');

  assert.match(source, /const VISIBLE_TAB_ORDER = TAB_ORDER\.filter\(\(tab\) => tab !== 'notifications'\);/);
  assert.match(source, /class GrocyAITabNav extends HTMLElement \{\s+constructor\(\) \{/);
  assert.match(source, /_ensureStructure\(\) \{\s+if \(this\._elements\) return;/);
  assert.match(source, /VISIBLE_TAB_ORDER\.forEach\(\(tab\) => \{/);
  assert.match(source, /nav\.setAttribute\('role', 'tablist'\);/);
  assert.match(source, /button\.setAttribute\('role', 'tab'\);/);
  assert.match(source, /button\.setAttribute\('aria-controls', getTabPanelId\(tab\)\);/);
  assert.match(source, /renderHaIcon\(TAB_ICONS\[tab\], 'tab-button__icon'\)/);
  assert.match(source, /button\.classList\.toggle\('active', isActive\);/);
  assert.match(source, /button\.setAttribute\('aria-selected', isActive \? 'true' : 'false'\);/);
});

test('topbar markup no longer renders panel URL hints or quicklink pills', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');
  const topbarSection = source.slice(
    source.indexOf('class GrocyAITopbar extends HTMLElement'),
    source.indexOf('class GrocyAITabNav extends HTMLElement'),
  );

  assert.match(topbarSection, /<header class=\"topbar\">/);
  assert.match(topbarSection, /renderHaIcon\(model\.panelIcon \|\| PANEL_ICON, 'topbar-title-icon'\)/);
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

test('native panel exposes ARIA tabpanel wiring for shopping, recipes, storage, and fallback notifications', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');

  assert.match(source, /function getTabButtonId\(tab\) \{/);
  assert.match(source, /function getTabPanelId\(tab\) \{/);
  assert.match(source, /root\.id = getTabPanelId\('shopping'\);/);
  assert.match(source, /root\.setAttribute\('role', 'tabpanel'\);/);
  assert.match(source, /aria-labelledby="\$\{getTabButtonId\('recipes'\)\}"/);
  assert.match(source, /aria-labelledby="\$\{getTabButtonId\('storage'\)\}"/);
  assert.match(source, /aria-labelledby="\$\{getTabButtonId\('notifications'\)\}"/);
});

test('recipes, storage, and modal setters skip full rerenders for volatile field-only updates', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');

  assert.match(source, /class GrocyAIDashboardModals extends HTMLElement \{[\s\S]*?this\._renderSignature = null;[\s\S]*?const nextSignature = JSON\.stringify\(\{[\s\S]*?createMethod: value\?\.recipes\?\.createModal\?\.method \|\| 'webscrape'[\s\S]*?\}\);[\s\S]*?if \(nextSignature === this\._renderSignature\) return;/);
  assert.match(source, /class GrocyAIRecipesTab extends HTMLElement \{[\s\S]*?this\._renderSignature = null;[\s\S]*?const nextSignature = JSON\.stringify\(\{[\s\S]*?stockProducts: buildStockSignature\(/);
  assert.match(source, /class GrocyAIStorageTab extends HTMLElement \{[\s\S]*?this\._renderSignature = null;[\s\S]*?const nextSignature = JSON\.stringify\(\{[\s\S]*?deleteModal: \{[\s\S]*?itemId: value\?\.deleteModal\?\.itemId \?\? null[\s\S]*?\}\);[\s\S]*?if \(nextSignature === this\._renderSignature\) \{[\s\S]*?this\._syncVolatileState\(\);[\s\S]*?return;[\s\S]*?\}/);
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


test('shopping polling respects document visibility and refreshes silently when the tab becomes visible again', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');

  assert.match(source, /this\._handleVisibilityChange = \(\) => this\._handleDocumentVisibilityChange\(\);/);
  assert.match(source, /document\.addEventListener\('visibilitychange', this\._handleVisibilityChange\);/);
  assert.match(source, /document\.removeEventListener\('visibilitychange', this\._handleVisibilityChange\);/);
  assert.match(source, /_canPollShopping\(\{ requireNoTimer = true \} = \{\}\) \{\s+const state = this\._store\.getState\(\);\s+if \(document\.hidden\) return false;/);
  assert.match(source, /_handleDocumentVisibilityChange\(\) \{\s+this\._syncShoppingPolling\(\);\s+if \(document\.hidden\) return;\s+if \(!this\._canPollShopping\(\{ requireNoTimer: false \}\)\) return;\s+void this\._loadShoppingList\(\{ silent: true \}\);\s+\}/);
});


test('shopping polling can be disabled without breaking manual and mutation-triggered refreshes', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');

  assert.match(source, /set hass\(value\) \{\s+this\._hass = value;\s+this\._shoppingPollIntervalMs = this\._resolveShoppingPollingInterval\(\);\s+this\._syncShoppingPolling\(\);/);
  assert.match(source, /_resolveShoppingPollingInterval\(\) \{\s+const configuredValue = this\._getPanelConfig\(\)\.dashboard_polling_interval_seconds\s+\?\? this\._hass\?\.states\?\.\['sensor\.grocy_ai_status'\]\?\.attributes\?\.dashboard_polling_interval_seconds\s+\?\? DEFAULT_POLLING_INTERVAL_SECONDS;\s+const value = Number\(configuredValue\);\s+if \(!Number\.isFinite\(value\) \|\| value < 0\) return DEFAULT_POLLING_INTERVAL_MS;\s+if \(value === 0\) return null;/);
  assert.match(source, /_syncShoppingPolling\(\) \{\s+if \(!Number\.isFinite\(this\._shoppingPollIntervalMs\) \|\| this\._shoppingPollIntervalMs <= 0\) \{\s+this\._stopShoppingPolling\(\);\s+return;\s+\}/);
  assert.match(source, /_startShoppingPolling\(\) \{\s+if \(!Number\.isFinite\(this\._shoppingPollIntervalMs\) \|\| this\._shoppingPollIntervalMs <= 0\) \{\s+this\._stopShoppingPolling\(\);\s+return;\s+\}/);
  assert.match(source, /onShoppingListChanged: async \(\) => \{\s+await this\._loadShoppingList\(\{ silent: true \}\);\s+\},/);
  assert.match(source, /root\.addEventListener\('shopping-refresh', \(\) => this\._loadShoppingList\(\)\);/);
  assert.match(source, /async _saveShoppingDetail\(\) \{[\s\S]*?await this\._loadShoppingList\(\{ silent: true \}\);/);
  assert.match(source, /async _saveMhd\(\) \{[\s\S]*?await this\._loadShoppingList\(\{ silent: true \}\);/);
  assert.match(source, /async _completeShoppingItem\(itemId\) \{[\s\S]*?await this\._loadShoppingList\(\{ silent: true \}\);/);
  assert.match(source, /async _deleteShoppingItem\(itemId\) \{[\s\S]*?await this\._loadShoppingList\(\{ silent: true \}\);/);
  assert.match(source, /async _completeAllShopping\(\) \{[\s\S]*?await this\._loadShoppingList\(\{ silent: true \}\);/);
});


test('dashboard shell uses a centered half-width desktop layout like the legacy dashboard', async () => {
  const source = await fs.readFile(dashboardCssPath, 'utf8');

  assert.match(source, /--dashboard-shell-max-width: 100%;/);
  assert.match(source, /\.page-shell \{[\s\S]*?width: min\(var\(--dashboard-shell-max-width\), 100%\);[\s\S]*?margin: 0 auto;/);
  assert.match(source, /@media \(min-width: 1200px\) \{[\s\S]*?:host \{[\s\S]*?--dashboard-shell-max-width: min\(960px, 50vw\);/);
});


test('dashboard shell derives spacing and surface styling from Home Assistant card theme tokens', async () => {
  const source = await fs.readFile(dashboardCssPath, 'utf8');

  assert.match(source, /--panel-card-background: var\(--ha-card-background-color, var\(--card-background-color, #fff\)\);/);
  assert.match(source, /--panel-border-color: var\(--ha-divider-color, var\(--divider-color, rgba\(0, 0, 0, 0\.12\)\)\);/);
  assert.match(source, /--panel-radius: var\(--ha-card-border-radius, 16px\);/);
  assert.match(source, /--panel-spacing: var\(--ha-card-padding, 16px\);/);
  assert.match(source, /--panel-card-padding: var\(--panel-spacing\);/);
  assert.match(source, /\.page-shell \{[\s\S]*?padding: var\(--panel-card-padding\) var\(--panel-card-padding\)/);
  assert.match(source, /\.card \{[\s\S]*?padding: var\(--panel-card-padding\);/);
  assert.match(source, /\.shopping-search-shell \{[\s\S]*?gap: var\(--panel-section-gap\);[\s\S]*?padding: var\(--panel-gap\);[\s\S]*?border-radius: var\(--panel-radius\);/);
  assert.match(source, /\.shopping-list-native \.shopping-card__surface,[\s\S]*?\.variant-grid \.shopping-card__surface \{[\s\S]*?gap: var\(--panel-stack-gap\);[\s\S]*?padding: var\(--panel-stack-gap\);/);
  assert.match(source, /\.bottom-tabbar \{[\s\S]*?gap: var\(--panel-compact-gap\);[\s\S]*?padding: var\(--panel-stack-gap\);/);
});


test('bottom tab bar stays centered and matches the desktop shell width before becoming compact pill navigation on mobile', async () => {
  const source = await fs.readFile(dashboardCssPath, 'utf8');

  assert.match(source, /\.bottom-tabbar \{[\s\S]*?left: 50%;[\s\S]*?transform: translateX\(-50%\);[\s\S]*?justify-content: center;[\s\S]*?width: min\(var\(--dashboard-shell-max-width\), calc\(100vw - 48px\)\);/);
  assert.match(source, /\.tab-button:hover,\s*\.tab-button:focus-visible \{[\s\S]*?transform: none;/);
  assert.match(source, /@media \(max-width: 800px\) \{[\s\S]*?\.bottom-tabbar \{[\s\S]*?flex-wrap: nowrap;[\s\S]*?width: fit-content;[\s\S]*?border-radius: 999px;[\s\S]*?overflow-x: auto;/);
  assert.match(source, /@media \(max-width: 800px\) \{[\s\S]*?\.tab-button \{[\s\S]*?flex: 0 0 auto;[\s\S]*?white-space: nowrap;/);
  assert.match(source, /@media \(max-width: 800px\) \{[\s\S]*?\.tab-button__meta \{[\s\S]*?display: none;/);
});
