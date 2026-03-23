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

test('topbar markup no longer renders panel URL hints, quicklink pills, or native-progress badge', async () => {
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
  assert.doesNotMatch(topbarSection, /Bereiche nativ/);
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
  assert.match(source, /const markup = renderShoppingVariantCard\(variant, \{\s+amount: parsedAmount \|\| variant\.amount \|\| variant\.default_amount \|\| '1',[\s\S]*?ctaLabel: '',[\s\S]*?resolveImageUrl: this\._viewModel\?\.resolveImageUrl,/);
  assert.match(source, /variantGrid\.replaceChildren\(\.\.\.nodes\);\s+bindShoppingImageFallbacks\(this\);/);
  assert.match(source, /list\.replaceChildren\(\.\.\.items\.map\(\(item\) => this\._createShoppingListItem\(item, model\)\)\);\s+bindShoppingImageFallbacks\(this\);/);
});


test('recipe filter cards render compact dropdown summaries and keep dropdown state across rerenders', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');

  assert.match(source, /function captureDetailsOpenState\(root\) \{/);
  assert.match(source, /function restoreDetailsOpenState\(root, openKeys\) \{/);
  assert.match(source, /const summaryLabel = summarizeSelectedItems\(items, selectedLocationIds, 'Keine Auswahl'\);/);
  assert.match(source, /location-dropdown__summary-title">Lagerort<\/span>/);
  assert.match(source, /location-dropdown__summary-title">Produkte in ausgewählten Standorten<\/span>/);
  assert.doesNotMatch(source, /renderStorageBadge\('Menge', formatAmount\(item\.amount\) \|\| '-', 'amount'\)/);
  assert.doesNotMatch(source, /renderStorageBadge\('MHD', item\.best_before_date \|\| '-', 'mhd'\)/);
  assert.match(source, /item\.location_name \? renderStorageBadge\('Lagerort', item\.location_name, 'location'\) : ''/);
  assert.match(source, /const openDetails = captureDetailsOpenState\(this\);[\s\S]*?restoreDetailsOpenState\(this, openDetails\);/);
});

test('shopping list bulk actions share one full row evenly in the native panel', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');
  const cssSource = await fs.readFile(dashboardCssPath, 'utf8');

  assert.match(source, /buttonRow\.className = 'button-row shopping-bulk-actions';/);
  assert.match(cssSource, /\.shopping-bulk-actions \{[\s\S]*?width: 100%;/);
  assert.match(cssSource, /\.shopping-bulk-actions > button \{[\s\S]*?flex: 1 1 0;[\s\S]*?min-width: 0;/);
  assert.match(cssSource, /\.shopping-bulk-actions > \.danger-button \{[\s\S]*?margin-top: 0;/);
});

test('shopping list header keeps title and refresh action on one row in mobile layouts', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');
  const cssSource = await fs.readFile(dashboardCssPath, 'utf8');

  assert.match(source, /listHeader\.className = 'section-header shopping-list-section__header';/);
  assert.match(cssSource, /\.shopping-list-section__header \{[\s\S]*?align-items: center;[\s\S]*?flex-wrap: nowrap;/);
  assert.match(cssSource, /\.shopping-list-section__header \.primary-button \{[\s\S]*?margin-left: auto;[\s\S]*?white-space: nowrap;/);
  assert.match(cssSource, /@media \(max-width: 800px\) \{[\s\S]*?\.shopping-list-section__header \{[\s\S]*?flex-direction: row;[\s\S]*?align-items: center;/);
});

test('storage tab keeps product filter and include-all toggle in one control row and summary badges underneath', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');
  const cssSource = await fs.readFile(dashboardCssPath, 'utf8');

  assert.match(source, /<section class="storage-controls-shell shopping-search-shell" aria-live="polite">[\s\S]*?<div class="shopping-search-shell__header">[\s\S]*?Filter & Anzeige[\s\S]*?<div class="storage-controls">[\s\S]*?<div class="storage-controls-row">/);
  assert.match(source, /<div class="storage-controls-row">[\s\S]*?<label class="storage-filter-field"[\s\S]*?<\/label>[\s\S]*?<label class="storage-toggle"[\s\S]*?Alle Produkte anzeigen[\s\S]*?<\/label>[\s\S]*?<\/div>/);
  assert.match(source, /<div class="storage-summary">[\s\S]*?<span class="migration-chip">\$\{escapeHtml\(`\$\{model\.summary\.totalCount\} Produkte`\)\}<\/span>[\s\S]*?<\/div>/);
  assert.match(cssSource, /\.storage-controls-shell \{[\s\S]*?width: 100%;/);
  assert.match(cssSource, /\.storage-controls-row \{[\s\S]*?grid-template-columns: minmax\(0, 1\.6fr\) auto;[\s\S]*?align-items: end;/);
  assert.match(cssSource, /\.storage-summary \{[\s\S]*?display: flex;[\s\S]*?flex-wrap: wrap;[\s\S]*?justify-content: flex-start;/);
});

test('shopping tab keeps the scanner trigger in the same mobile header row as the title', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');
  const cssSource = await fs.readFile(dashboardCssPath, 'utf8');

  assert.match(source, /heroHeader\.className = 'section-header shopping-hero-card__header';/);
  assert.match(source, /scannerButton\.innerHTML = renderHaIcon\('mdi:barcode-scan', 'scanner-popup-button__icon'\);/);
  assert.match(cssSource, /\.shopping-hero-card__header \{[\s\S]*?align-items: center;/);
  assert.match(cssSource, /\.shopping-hero-card__header \.scanner-popup-button \{[\s\S]*?margin-left: auto;/);
  assert.match(cssSource, /\.scanner-popup-button__icon \{[\s\S]*?--mdc-icon-size: 24px;/);
  assert.match(cssSource, /@media \(max-width: 800px\) \{[\s\S]*?\.shopping-hero-card__header \{[\s\S]*?flex-direction: row;[\s\S]*?align-items: center;/);
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
test('native panel locks background scrolling while any modal is open', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');
  const cssSource = await fs.readFile(dashboardCssPath, 'utf8');

  assert.match(source, /this\._scrollLockState = null;/);
  assert.match(source, /this\._setModalScrollLock\(this\._isAnyModalOpen\(state\)\);/);
  assert.match(source, /_isAnyModalOpen\(state\) \{[\s\S]*?state\.shopping\.detailModal\.open[\s\S]*?state\.shopping\.scanner\.open[\s\S]*?state\.recipes\.createModal\.open[\s\S]*?state\.storage\.deleteModal\.open[\s\S]*?\}/);
  assert.match(source, /_setModalScrollLock\(locked\) \{[\s\S]*?body\.style\.overflow = 'hidden';[\s\S]*?body\.style\.position = 'fixed';[\s\S]*?document\.documentElement\.style\.overscrollBehavior = 'none';[\s\S]*?window\.scrollTo\(0, scrollTop\);/);
  assert.match(cssSource, /:host\(\[data-modal-open="true"\]\),[\s\S]*?\.page-shell--modal-open \{[\s\S]*?overflow: hidden;/);
  assert.match(cssSource, /:host\(\[data-modal-open="true"\]\) \.bottom-tabbar \{[\s\S]*?opacity: 0;[\s\S]*?visibility: hidden;[\s\S]*?pointer-events: none;/);
  assert.match(cssSource, /\.shopping-modal \{[\s\S]*?z-index: 60;[\s\S]*?overscroll-behavior: contain;/);
  assert.match(cssSource, /\.bottom-tabbar \{[\s\S]*?z-index: 40;[\s\S]*?transition: opacity 0\.18s ease, visibility 0\.18s ease;/);
  assert.match(cssSource, /\.shopping-modal-content \{[\s\S]*?overflow: auto;[\s\S]*?overscroll-behavior: contain;[\s\S]*?-webkit-overflow-scrolling: touch;/);
});


test('native scanner bridge keeps legacy getUserMedia fallbacks for Home Assistant webviews', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');
  const scannerBridgeSection = source.slice(
    source.indexOf('class GrocyAIScannerBridge extends HTMLElement'),
    source.indexOf('class GrocyAIRecipesTab extends HTMLElement'),
  );
  const applyViewModelSection = scannerBridgeSection.slice(
    scannerBridgeSection.indexOf('_applyViewModel() {'),
    scannerBridgeSection.indexOf('_getElement(role) {'),
  );

  assert.match(source, /function hasCompatibleGetUserMedia\(\) \{/);
  assert.match(source, /navigator\?\.\s*mediaDevices\?\.getUserMedia[\s\S]*?navigator\?\.\s*webkitGetUserMedia[\s\S]*?navigator\?\.\s*msGetUserMedia/);
  assert.match(source, /async function requestCompatibleUserMedia\(constraints\) \{/);
  assert.match(source, /legacyGetUserMedia\.call\(navigator, constraints, resolve, reject\);/);
  assert.match(scannerBridgeSection, /if \(!hasCompatibleGetUserMedia\(\)\) \{\s+this\._setStatus\('Kamera wird in diesem Browser\/WebView nicht unterstützt\.'\);/);
  assert.match(scannerBridgeSection, /video\.setAttribute\('playsinline', 'true'\);[\s\S]*?video\.playsInline = true;[\s\S]*?video\.muted = true;/);
  assert.match(scannerBridgeSection, /return await requestCompatibleUserMedia\(constraints\);/);
  assert.match(applyViewModelSection, /if \(shouldOpen\) \{\s+void this\._refreshDevices\(\);\s+return;\s+\}/);
  assert.doesNotMatch(applyViewModelSection, /void this\._startScanner\(\);/);
  assert.match(source, /status: open\s+\?\s+'Scanner geöffnet\. Kamera bitte manuell starten\.'\s+:\s+String\(scannerState\?\.status \|\| 'Bereit\.'\),/);
  assert.match(source, /this\._store\.patch\(\{ topbarStatus: 'Scanner geöffnet\. Kamera bitte manuell starten\.' \}\);/);
  assert.match(source, /if \(!hasCompatibleGetUserMedia\(\)\) \{\s+this\._setStatus\('Kamera wird in diesem Browser\/WebView nicht unterstützt\.'\);/);
  assert.match(source, /video\.setAttribute\('playsinline', 'true'\);[\s\S]*?video\.playsInline = true;[\s\S]*?video\.muted = true;/);
  assert.match(source, /return await requestCompatibleUserMedia\(constraints\);/);
});


test('recipes and storage tabs are natively migrated in the panel shell', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');

  assert.match(source, /import \{ renderActionRow, renderCardContainer, renderMetaBadges, renderStateCard, renderTileGrid, renderTwoColumnCardGroup \} from '\.\/shared-panel-ui\.js';/);
  assert.match(source, /const MIGRATED_TABS = new Set\(\['shopping', 'recipes', 'storage'\]\);/);
  assert.match(source, /function buildRecipesTabMarkup\(model = \{\}\) \{/);
  assert.match(source, /renderTwoColumnCardGroup\(recipeCards, \{ className: 'recipes-card-group' \}\)/);
  assert.match(source, /label: 'Rezept hinzufügen'[\s\S]*?dataset: \{ action: 'recipes-open-create' \}/);
  assert.match(source, /label: 'Rezepte laden'[\s\S]*?dataset: \{ action: 'recipes-load-suggestions' \}/);
  assert.doesNotMatch(source, /Der erste vollständig native Nicht-Shopping-Tab übernimmt/);
  assert.doesNotMatch(source, /Grocy-Rezepte', 'KI-Vorschläge', 'native Dialoge/);
  assert.match(source, /data-action="recipes-load-expiring"|dataset: \{ action: 'recipes-load-expiring' \}/);
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


test('mobile panel CSS keeps native dashboard copy readable and avoids cramped two-column layouts', async () => {
  const source = await fs.readFile(dashboardCssPath, 'utf8');
  const shoppingSource = await fs.readFile(
    path.resolve(__dirname, '../../grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/shopping-ui.css'),
    'utf8',
  );

  assert.match(source, /:host \{[\s\S]*?-webkit-text-size-adjust: 100%;[\s\S]*?text-size-adjust: 100%;/);
  assert.match(source, /h1 \{[\s\S]*?font-size: clamp\(1\.9rem, 3vw, 2\.25rem\);[\s\S]*?line-height: 1\.1;/);
  assert.match(source, /\.tab-button__label \{[\s\S]*?white-space: nowrap;/);
  assert.match(source, /@media \(max-width: 800px\) \{[\s\S]*?\.panel-card-group--two-column,[\s\S]*?\.shopping-details-grid \{[\s\S]*?grid-template-columns: 1fr;/);
  assert.match(source, /@media \(max-width: 800px\) \{[\s\S]*?\.stock-item \{[\s\S]*?grid-template-columns: minmax\(0, 1fr\);/);
  assert.match(source, /@media \(max-width: 800px\) \{[\s\S]*?\.location-dropdown__summary-value \{[\s\S]*?white-space: normal;/);
  assert.match(shoppingSource, /@media \(max-width: 640px\) \{[\s\S]*?\.shopping-card__title \{[\s\S]*?font-size: 1\.02rem;/);
  assert.match(shoppingSource, /@media \(max-width: 640px\) \{[\s\S]*?\.shopping-card__note,[\s\S]*?\.shopping-card__detail-line,[\s\S]*?\.shopping-card__context-item \{[\s\S]*?font-size: 0\.88rem;[\s\S]*?line-height: 1\.45;/);
  assert.match(shoppingSource, /@media \(max-width: 640px\) \{[\s\S]*?\.shopping-badge,[\s\S]*?\.shopping-status-chip \{[\s\S]*?font-size: 0\.78rem;/);
  assert.match(shoppingSource, /@media \(max-width: 640px\) \{[\s\S]*?\.shopping-card__header,[\s\S]*?\.shopping-card__footer,[\s\S]*?\.shopping-card__context-item \{[\s\S]*?flex-wrap: wrap;/);
});


test('bottom tab bar stays centered and matches the desktop shell width before becoming compact pill navigation on mobile', async () => {
  const source = await fs.readFile(dashboardCssPath, 'utf8');

  assert.match(source, /--dashboard-shell-center-x: 50vw;/);
  assert.match(source, /--dashboard-shell-fixed-width: min\(var\(--dashboard-shell-max-width\), calc\(100vw - 48px\)\);/);
  assert.match(source, /\.bottom-tabbar \{[\s\S]*?left: var\(--dashboard-shell-center-x\);[\s\S]*?transform: translateX\(-50%\);[\s\S]*?justify-content: center;[\s\S]*?width: min\(var\(--dashboard-shell-fixed-width\), calc\(100vw - 48px\)\);/);
  assert.match(source, /\.tab-button:hover,\s*\.tab-button:focus-visible \{[\s\S]*?transform: none;/);
  assert.match(source, /@media \(max-width: 800px\) \{[\s\S]*?\.bottom-tabbar \{[\s\S]*?left: var\(--dashboard-shell-center-x\);[\s\S]*?flex-wrap: nowrap;[\s\S]*?width: fit-content;[\s\S]*?max-width: min\(var\(--dashboard-shell-fixed-width\), calc\(100vw - 32px\)\);[\s\S]*?border-radius: 999px;[\s\S]*?overflow-x: auto;/);
  assert.match(source, /@media \(max-width: 800px\) \{[\s\S]*?\.tab-button \{[\s\S]*?flex: 0 0 auto;[\s\S]*?white-space: nowrap;/);
  assert.match(source, /@media \(max-width: 800px\) \{[\s\S]*?\.tab-button__meta \{[\s\S]*?display: none;/);
});
