import { createDashboardApiClient, getErrorMessage } from './dashboard-api-client.js';
import { buildLegacyDashboardUrl, resolveDashboardApiBasePath } from './panel-api-base-path.js';
import { createDashboardStore } from './dashboard-store.js';
import { buildPanelUrlWithTab, DEFAULT_TAB, resolveTabFromLocation, TAB_ORDER } from './tab-routing.js';
import { createShoppingSearchController, SEARCH_FLOW_STATES } from './shopping-search-controller.js';
import { bindShoppingImageFallbacks, escapeHtml, formatAmount, formatBadgeValue, formatStockCount, renderShoppingListItemCard, renderShoppingVariantCard, resolveShoppingImageSource } from './shopping-ui.js';
import { renderActionRow, renderCardContainer, renderMetaBadges, renderStateCard, renderTileGrid, renderTwoColumnCardGroup } from './shared-panel-ui.js';
import { bindSwipeInteractions } from './swipe-interactions.js';

const PANEL_SLUG = 'grocy-ai';
const PANEL_TITLE = 'Grocy AI';
const PANEL_ICON = 'mdi:fridge-outline';
const DEFAULT_LEGACY_URL = '/api/hassio_ingress/grocy_ai_assistant/';
const STYLE_URL = new URL('./grocy-ai-dashboard.css', import.meta.url);
const MIGRATED_TABS = new Set(['shopping', 'recipes', 'storage']);
const TAB_LABELS = {
  shopping: 'Einkauf',
  recipes: 'Rezepte',
  storage: 'Lager',
  notifications: 'Benachrichtigungen',
};
const TAB_ICONS = Object.freeze({
  shopping: 'mdi:cart-outline',
  recipes: 'mdi:silverware-fork-knife',
  storage: 'mdi:fridge-outline',
  notifications: 'mdi:bell-outline',
});
const VISIBLE_TAB_ORDER = TAB_ORDER.filter((tab) => tab !== 'notifications');
const DEFAULT_POLLING_INTERVAL_SECONDS = 5;
const DEFAULT_POLLING_INTERVAL_MS = DEFAULT_POLLING_INTERVAL_SECONDS * 1000;
const DEFAULT_INTEGRATION_VERSION = '8.0.13';
const GROCY_RECIPE_DISPLAY_LIMIT = 3;
const AI_RECIPE_DISPLAY_LIMIT = 3;
const TAB_VIEW_STATE = Object.freeze({
  LOADED: 'loaded',
  LOADING: 'loading',
  ERROR: 'error',
  EMPTY: 'empty',
  EDITING: 'editing',
});

function sn(key) {
  return key === 'common.version' ? 'Version ' : '';
}

function logIntegrationStartupBanner(version) {
  console.info(`%c  GROCY-AI %c ${sn("common.version")}${version} %c`, "background-color: #555;color: #fff;padding: 3px 2px 3px 3px;border: 1px solid #555;border-radius: 3px 0 0 3px;font-family: Roboto,Verdana,Geneva,sans-serif;text-shadow: 0 1px 0 rgba(1, 1, 1, 0.3)", "background-color: transparent;color: #555;padding: 3px 3px 3px 2px;border: 1px solid #555; border-radius: 0 3px 3px 0;font-family: Roboto,Verdana,Geneva,sans-serif", "background-color: transparent");
}

function resolvePanelImageUrl(url, dashboardApi, options = {}) {
  const normalized = String(url || '').trim();
  if (!normalized) return resolveShoppingImageSource(normalized);
  if (normalized.startsWith('data:') || normalized.startsWith('http://') || normalized.startsWith('https://')) {
    return normalized;
  }

  const normalizedPath = '/' + normalized.replace(/^\/+/, '');
  const normalizedApiBasePath = String(options?.apiBasePath || '').replace(/\/+$/, '');
  if (normalizedPath.startsWith('/api/')) {
    if (dashboardApi?.buildUrl) {
      return dashboardApi.buildUrl(normalizedPath);
    }
    return normalizedApiBasePath ? `${normalizedApiBasePath}${normalizedPath}` : normalizedPath;
  }

  return normalizedPath;
}


function registerCustomElement(tagName, elementClass) {
  if (customElements.get(tagName)) return;

  try {
    customElements.define(tagName, elementClass);
  } catch (error) {
    if (!(error instanceof DOMException) || !String(error.message || '').includes('already been used with this registry')) {
      throw error;
    }

    if (customElements.get(tagName)) return;
    customElements.define(tagName, class extends elementClass {});
  }
}


function normalizeTabName(value, fallback = null) {
  const normalized = String(value ?? '').trim().toLowerCase();
  return TAB_ORDER.includes(normalized) ? normalized : fallback;
}

function renderStorageBadge(label, value, variant, extraClassName = '') {
  return `
    <span class="shopping-badge shopping-badge--${escapeHtml(variant)}${extraClassName ? ` ${escapeHtml(extraClassName)}` : ''}">
      <span class="shopping-badge__label">${escapeHtml(label)}</span>
      <span class="shopping-badge__value">${escapeHtml(value)}</span>
    </span>
  `;
}


function captureDetailsOpenState(root) {
  if (!(root instanceof HTMLElement)) return [];
  return Array.from(root.querySelectorAll('details[data-dropdown-key][open]'))
    .map((detail) => String(detail.dataset.dropdownKey || '').trim())
    .filter(Boolean);
}

function restoreDetailsOpenState(root, openKeys) {
  if (!(root instanceof HTMLElement)) return;
  const keys = new Set(Array.isArray(openKeys) ? openKeys : []);
  root.querySelectorAll('details[data-dropdown-key]').forEach((detail) => {
    detail.open = keys.has(String(detail.dataset.dropdownKey || '').trim());
  });
}

function summarizeSelectedItems(items, selectedIds, fallbackLabel) {
  const normalizedItems = Array.isArray(items) ? items : [];
  const selected = new Set(Array.isArray(selectedIds) ? selectedIds.map((value) => Number(value)) : []);
  const effectiveItems = selected.size
    ? normalizedItems.filter((item) => selected.has(Number(item?.id)))
    : normalizedItems;

  if (!effectiveItems.length) return fallbackLabel;
  if (effectiveItems.length === normalizedItems.length) return `Alle (${normalizedItems.length})`;
  if (effectiveItems.length === 1) return String(effectiveItems[0]?.name || fallbackLabel).trim() || fallbackLabel;
  if (effectiveItems.length <= 2) {
    return effectiveItems
      .map((item) => String(item?.name || '').trim())
      .filter(Boolean)
      .join(', ');
  }
  return `${effectiveItems.length} ausgewählt`;
}

function buildPanelTabHref(panelPath, tab) {
  const path = String(panelPath || `/${PANEL_SLUG}`) || `/${PANEL_SLUG}`;
  if (!normalizeTabName(tab)) return path;
  if (tab === 'shopping') return path;
  return `${path}?tab=${tab}`;
}

function getTabButtonId(tab) {
  return `grocy-ai-tab-${String(tab || '').trim().toLowerCase()}`;
}

function getTabPanelId(tab) {
  return `grocy-ai-tabpanel-${String(tab || '').trim().toLowerCase()}`;
}

function renderHaIcon(icon, className = '') {
  const normalizedIcon = String(icon || '').trim();
  if (!normalizedIcon) return '';
  const normalizedClassName = String(className || '').trim();
  return `<ha-icon icon="${escapeHtml(normalizedIcon)}"${normalizedClassName ? ` class="${escapeHtml(normalizedClassName)}"` : ''} aria-hidden="true"></ha-icon>`;
}

function readTabFromHash(hash) {
  const normalizedHash = String(hash || '').replace(/^#/, '').trim();
  if (!normalizedHash) return null;
  if (normalizedHash.startsWith('tab=')) {
    const params = new URLSearchParams(normalizedHash);
    return normalizeTabName(params.get('tab'));
  }
  return normalizeTabName(normalizedHash);
}

function readTabFromSearch(search) {
  const normalizedSearch = String(search || '').replace(/^\?/, '').trim();
  if (!normalizedSearch) return null;
  const params = new URLSearchParams(normalizedSearch);
  return normalizeTabName(params.get('tab'));
}

function readTabFromPath(pathname) {
  const segments = String(pathname || '')
    .split('/')
    .map((segment) => segment.trim().toLowerCase())
    .filter(Boolean);
  const panelIndex = segments.lastIndexOf(PANEL_SLUG);
  if (panelIndex !== -1) {
    return normalizeTabName(segments[panelIndex + 1]);
  }
  return normalizeTabName(segments.at(-1));
}

function toImageSource(url, options = {}) {
  const normalizedUrl = String(url ?? '').trim();
  if (!normalizedUrl) return 'https://placehold.co/80x80?text=Kein+Bild';

  const requestedSize = String(options?.size || '').trim().toLowerCase();
  const isMobileViewport = typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(max-width: 768px)').matches;
  const normalizedSize = requestedSize === 'full'
    ? 'full'
    : (requestedSize === 'mobile' || isMobileViewport ? 'mobile' : 'thumb');
  const apiBasePath = String(options?.apiBasePath || '').replace(/\/+$/, '');

  if (normalizedUrl.startsWith('data:')) return normalizedUrl;
  if (normalizedUrl.startsWith('http://') || normalizedUrl.startsWith('https://')) {
    const isExternal = (() => {
      try {
        return new URL(normalizedUrl).host !== window.location.host;
      } catch (_) {
        return false;
      }
    })();

    if (window.location.protocol === 'https:' && isExternal && normalizedUrl.startsWith('http://')) {
      return `https://${normalizedUrl.slice('http://'.length)}`;
    }
    return normalizedUrl;
  }

  const normalizedPath = `/${normalizedUrl.replace(/^\/+/, '')}`;
  if (normalizedPath.startsWith('/api/dashboard/product-picture?')) {
    const proxiedUrl = new URL(apiBasePath ? `${apiBasePath}${normalizedPath}` : normalizedPath, window.location.origin);
    proxiedUrl.searchParams.set('size', normalizedSize);
    return proxiedUrl.toString();
  }

  if (normalizedPath.startsWith('/api/')) {
    return apiBasePath ? `${apiBasePath}${normalizedPath}` : normalizedPath;
  }
  return normalizedPath;
}


function isRestorableTextField(element) {
  const tagName = String(element?.tagName || '').toLowerCase();
  if (tagName === 'textarea') return true;
  if (tagName !== 'input') return false;
  const inputType = String(element.type || '').toLowerCase();
  return !['button', 'checkbox', 'color', 'file', 'hidden', 'image', 'radio', 'range', 'reset', 'submit'].includes(inputType);
}

function buildFocusRestoreSelector(element) {
  if (!(element instanceof HTMLElement)) return '';
  const tagName = String(element.tagName || '').toLowerCase();
  if (!tagName) return '';

  const selectors = [
    ['id', element.id],
    ['data-role', element.dataset?.role],
    ['data-field', element.dataset?.field],
    ['data-recipe-field', element.dataset?.recipeField],
    ['name', element.getAttribute?.('name')],
  ];

  for (const [attribute, rawValue] of selectors) {
    const value = String(rawValue || '').trim();
    if (!value) continue;
    const escapedValue = value.replaceAll('\\', '\\\\').replaceAll('"', '\\"');
    return `${tagName}[${attribute}="${escapedValue}"]`;
  }

  return tagName;
}

function captureFocusedFormControl(root) {
  if (!(root instanceof HTMLElement)) return null;
  const activeElement = document.activeElement;
  if (!(activeElement instanceof HTMLElement) || !root.contains(activeElement)) return null;

  const selector = buildFocusRestoreSelector(activeElement);
  if (!selector) return null;

  const snapshot = {
    selector,
    isTextField: isRestorableTextField(activeElement),
    selectionStart: null,
    selectionEnd: null,
  };

  if (snapshot.isTextField) {
    snapshot.selectionStart = typeof activeElement.selectionStart === 'number' ? activeElement.selectionStart : null;
    snapshot.selectionEnd = typeof activeElement.selectionEnd === 'number' ? activeElement.selectionEnd : null;
  }

  return snapshot;
}

function restoreFocusedFormControl(root, snapshot) {
  if (!(root instanceof HTMLElement) || !snapshot?.selector) return;
  const target = root.querySelector(snapshot.selector);
  if (!(target instanceof HTMLElement) || typeof target.focus !== 'function') return;

  target.focus();
  if (!snapshot.isTextField || typeof target.setSelectionRange !== 'function') return;
  if (snapshot.selectionStart === null || snapshot.selectionEnd === null) return;

  const currentValueLength = String(target.value || '').length;
  const selectionStart = Math.min(snapshot.selectionStart, currentValueLength);
  const selectionEnd = Math.min(snapshot.selectionEnd, currentValueLength);
  target.setSelectionRange(selectionStart, selectionEnd);
}

function deriveSearchUiState(model = {}) {
  if (model.flowState === SEARCH_FLOW_STATES.ERROR || model.errorMessage) return 'error';
  if (model.flowState === SEARCH_FLOW_STATES.SUBMITTING || model.isSubmitting) return 'submitting';
  if (model.flowState === SEARCH_FLOW_STATES.LOADING_VARIANTS || model.isLoadingVariants) return 'loading';

  const hasQuery = Boolean(String(model.query || '').trim());
  const hasVariants = Array.isArray(model.variants) && model.variants.length > 0;
  if (hasVariants && model.flowState === SEARCH_FLOW_STATES.VARIANTS_READY) return 'suggestions';
  if (hasQuery) return 'typing';
  return 'empty';
}

function getSearchStateLabel(searchUiState) {
  switch (searchUiState) {
    case 'typing':
      return 'Tippt';
    case 'loading':
      return 'Lädt Vorschläge';
    case 'suggestions':
      return 'Vorschläge sichtbar';
    case 'submitting':
      return 'Aktion läuft';
    case 'error':
      return 'Fehler';
    case 'empty':
    default:
      return 'Leer';
  }
}

function normalizeStockProduct(item) {
  const productId = Number(item?.id ?? item?.product_id ?? 0);
  const stockId = Number(item?.stock_id ?? item?.stockId ?? 0);
  return {
    ...item,
    id: Number.isFinite(productId) && productId > 0 ? productId : null,
    stock_id: Number.isFinite(stockId) && stockId > 0 ? stockId : null,
    in_stock: Boolean(item?.in_stock ?? true),
  };
}

function buildStockSignature(items) {
  return JSON.stringify(
    (Array.isArray(items) ? items : []).map((item) => ({
      id: item.id ?? null,
      stock_id: item.stock_id ?? null,
      amount: item.amount ?? null,
      best_before_date: item.best_before_date ?? '',
      location_id: item.location_id ?? null,
    })),
  );
}

function getActionableStorageId(item) {
  const stockId = Number(item?.stock_id ?? 0);
  if (Number.isFinite(stockId) && stockId > 0) return stockId;
  const productId = Number(item?.id ?? 0);
  if (Number.isFinite(productId) && productId > 0) return productId;
  return 0;
}

function normalizeNutritionInputValue(value) {
  const normalized = String(value ?? '').trim().replace(',', '.');
  if (!normalized) return null;
  const parsed = Number(normalized);
  if (!Number.isFinite(parsed) || parsed < 0) return Number.NaN;
  return parsed;
}

function formatStorageDateLabel(value, fallback = 'Kein Datum') {
  const normalized = String(value ?? '').trim();
  if (!normalized) return fallback;
  const isoDate = normalized.match(/^(\d{4}-\d{2}-\d{2})/)?.[1] || normalized;
  return isoDate;
}

function resolveStorageStatusVariant(item) {
  if (!item?.in_stock) return 'source';
  if (String(item?.best_before_date || '').trim()) return 'mhd';
  return 'shopping';
}

function renderStorageProductCard(item, options = {}) {
  const actionableId = getActionableStorageId(item);
  const title = item?.name || 'Unbekanntes Produkt';
  const amountLabel = formatAmount(item?.amount, '0');
  const stockLabel = item?.in_stock ? 'Auf Lager' : 'Nicht auf Lager';
  const bestBeforeDate = formatStorageDateLabel(item?.best_before_date, 'Kein MHD');
  const resolvedImageSource = resolveShoppingImageSource(item?.picture_url, { resolveUrl: options.resolveImageUrl });
  const metaBadges = [
    `Menge ${amountLabel}`,
    item?.location_name ? `Lagerort ${item.location_name}` : '',
    item?.in_stock ? 'Im Bestand' : 'Nicht im Bestand',
  ].filter(Boolean);

  return `
    <article class="shopping-card storage-card" role="listitem">
      <div class="shopping-card__surface storage-card__surface">
        <div class="storage-card__media-wrap">
          <img class="shopping-card__media storage-card__media" src="${escapeHtml(resolvedImageSource)}" alt="${escapeHtml(title)}" loading="lazy" data-shopping-image="true" data-fallback-src="${escapeHtml(resolveShoppingImageSource(''))}" />
          <span class="shopping-status-chip shopping-status-chip--${escapeHtml(resolveStorageStatusVariant(item))} storage-card__stock-chip">${escapeHtml(stockLabel)}</span>
        </div>
        <div class="shopping-card__body storage-card__body">
          <div class="shopping-card__header">
            <strong class="shopping-card__title">${escapeHtml(title)}</strong>
            <span class="shopping-badge shopping-badge--amount">
              <span class="shopping-badge__label">Menge</span>
              <span class="shopping-badge__value">${escapeHtml(amountLabel)}</span>
            </span>
          </div>
          <div class="shopping-card__badges storage-card__meta-badges">
            ${metaBadges.map((entry) => `<span class="migration-chip">${escapeHtml(entry)}</span>`).join('')}
          </div>
          <ul class="shopping-card__context-list">
            <li class="shopping-card__context-item shopping-card__context-item--stock">
              <span class="shopping-card__context-label">Bestand</span>
              <span class="shopping-card__context-value">${escapeHtml(formatStockCount(item?.amount, '0'))}</span>
            </li>
            <li class="shopping-card__context-item shopping-card__context-item--location">
              <span class="shopping-card__context-label">Lagerort</span>
              <span class="shopping-card__context-value">${escapeHtml(formatBadgeValue(item?.location_name, 'Nicht gesetzt'))}</span>
            </li>
            <li class="shopping-card__context-item shopping-card__context-item--mhd">
              <span class="shopping-card__context-label">MHD</span>
              <span class="shopping-card__context-value">${escapeHtml(bestBeforeDate)}</span>
            </li>
            <li class="shopping-card__context-item">
              <span class="shopping-card__context-label">Produkt-ID</span>
              <span class="shopping-card__context-value">${escapeHtml(item?.id || '-')}</span>
            </li>
          </ul>
          <div class="shopping-card__actions storage-card__actions">
            <button type="button" class="secondary-button" data-action="storage-open-edit" data-item-id="${escapeHtml(actionableId)}">Bearbeiten</button>
            <button type="button" class="success-button" data-action="storage-open-consume" data-item-id="${escapeHtml(actionableId)}" ${!item?.in_stock ? 'disabled' : ''}>Verbrauchen</button>
            <button type="button" class="danger-button" data-action="storage-open-delete" data-item-id="${escapeHtml(actionableId)}">Löschen</button>
          </div>
        </div>
      </div>
    </article>
  `;
}

function renderStorageListItem(item, options = {}) {
  const actionableId = getActionableStorageId(item);
  const stockLabel = item?.in_stock ? 'Im Bestand' : 'Nicht im Bestand';
  const consumeActionLabel = item?.in_stock ? '✅ Verbrauchen' : 'ℹ️ Öffnen';
  const cardMarkup = renderShoppingListItemCard({
    name: item?.name,
    amount: item?.amount,
    best_before_date: item?.best_before_date,
    location_name: item?.location_name,
    picture_url: item?.picture_url,
  }, {
    resolveImageUrl: options.resolveImageUrl,
    rootClassName: 'shopping-item-card shopping-item-card--legacy storage-item-card',
    contextFields: [],
    statusChip: false,
    stockBadgePlacement: 'main',
    mhdBadge: {
      variant: 'mhd',
      hideLabel: true,
    },
    stockBadgePlacement: 'aside',
    badgeOrder: ['stock', 'amount', 'mhd'],
    stockBadge: {
      label: 'Status',
      value: stockLabel,
      variant: item?.in_stock ? 'stock' : 'neutral',
      hideLabel: true,
    },
  });

  return `
    <li
      class="storage-item swipe-item variant-card"
      data-item-id="${escapeHtml(actionableId)}"
      data-in-stock="${item?.in_stock ? 'true' : 'false'}"
    >
      <div class="swipe-item-action swipe-item-action-left" aria-hidden="true">
        <span class="swipe-chip swipe-chip-edit">✏️ Bearbeiten</span>
      </div>
      <div class="swipe-item-action swipe-item-action-right" aria-hidden="true">
        <span class="swipe-chip swipe-chip-buy">${escapeHtml(consumeActionLabel)}</span>
      </div>
      <div class="storage-item-content shopping-item-content swipe-item-content">
        ${cardMarkup}
      </div>
    </li>
  `;
}

function buildStorageTabMarkup(model = {}) {
  const items = Array.isArray(model.items) ? model.items : [];
  const locations = Array.isArray(model.locations) ? model.locations : [];
  const editModal = model.editModal || { open: false };
  const consumeModal = model.consumeModal || { open: false, amount: '1' };
  const deleteModal = model.deleteModal || { open: false };
  const activeEditItem = model.activeEditItem || null;
  const activeConsumeItem = model.activeConsumeItem || null;
  const activeDeleteItem = model.activeDeleteItem || null;
  const locationOptions = [
    '<option value="">Bitte Lagerort wählen</option>',
    ...locations.map((location) => {
      const locationId = Number(location?.id ?? 0);
      const isSelected = String(editModal.locationId ?? '') === String(locationId);
      return `<option value="${locationId}"${isSelected ? ' selected' : ''}>${escapeHtml(location?.name || `Lagerort ${locationId}`)}</option>`;
    }),
  ].join('');
  const resolvedEditImageSource = resolveShoppingImageSource(activeEditItem?.picture_url, { resolveUrl: model.resolveImageUrl });
  const editLocationLabel = editModal.locationId
    ? (locations.find((location) => String(location?.id ?? '') === String(editModal.locationId))?.name || 'Nicht gesetzt')
    : formatBadgeValue(activeEditItem?.location_name, 'Nicht gesetzt');

  let listMarkup = '';
  if (model.loading && !items.length) {
    listMarkup = renderTileGrid([
      renderStateCard({
        eyebrow: 'Lager',
        title: 'Bestand wird geladen',
        message: 'Produkte, Lagerorte und Quick Actions werden aus dem Dashboard geladen.',
        stateLabel: 'Lädt',
        stateVariant: 'source',
      }),
    ], { className: 'storage-grid' });
  } else if (!items.length) {
    listMarkup = renderTileGrid([
      renderStateCard({
        eyebrow: 'Lager',
        title: 'Keine Produkte gefunden',
        message: 'Passe Filter oder Toggle an oder aktualisiere den Bestand manuell.',
        stateLabel: 'Leer',
        stateVariant: 'mhd',
      }),
    ], { className: 'storage-grid' });
  } else {
    listMarkup = `
      <ul class="storage-products-list storage-products-list--native variant-grid" role="list">
        ${items.map((item) => renderStorageListItem(item, { resolveImageUrl: model.resolveImageUrl })).join('')}
      </ul>
    `;
  }

  return `
    ${renderCardContainer({
      className: 'hero-card storage-hero-card',
      eyebrow: 'Lager',
      title: 'Lager',
      description: 'Der Storage-Tab rendert den Bestand wieder als Legacy-nahe Swipe-Liste inklusive Filter, Refresh und Bestandsaktionen.',
      actions: [
        { label: 'Aktualisieren', className: 'primary-button', dataset: { action: 'storage-refresh' } },
      ],
      body: `
        <div class="storage-controls">
          <label class="storage-filter-field" for="storage-filter-input-native">
            <span class="eyebrow">Textfilter</span>
            <input id="storage-filter-input-native" class="ha-control" data-role="storage-filter" type="text" placeholder="Produkte filtern..." value="${escapeHtml(model.filter || '')}" />
          </label>
          <label class="storage-toggle" for="storage-include-all-products-native">
            <input id="storage-include-all-products-native" class="ha-control" data-role="storage-include-all" type="checkbox"${model.includeAllProducts ? ' checked' : ''} />
            <span>Alle Produkte anzeigen</span>
          </label>
        </div>
        <div class="storage-summary">
          <span class="migration-chip">${escapeHtml(`${model.summary.totalCount} Produkte`)}</span>
          <span class="migration-chip">${escapeHtml(`${model.summary.inStockCount} Produkte auf Lager`)}</span>
          <span class="migration-chip">${escapeHtml(`${model.summary.outOfStockCount} Produkte nicht auf Lager`)}</span>
        </div>
      `,
    })}
    ${listMarkup}

    <div class="shopping-modal${editModal.open ? '' : ' hidden'}">
      <div class="shopping-modal-backdrop" data-action="storage-close-edit"></div>
      <section class="shopping-modal-content card storage-modal-content storage-edit-modal-content">
        <button class="shopping-modal-close" type="button" data-action="storage-close-edit" aria-label="Produkt bearbeiten schließen">×</button>
        <h3>${escapeHtml(activeEditItem?.name || 'Produkt bearbeiten')}</h3>
        <div class="storage-edit-media">
          <img
            class="storage-edit-picture shopping-card__media${activeEditItem?.picture_url ? '' : ' hidden'}"
            src="${escapeHtml(resolvedEditImageSource)}"
            alt="${escapeHtml(activeEditItem?.name || 'Produktbild')}"
            loading="lazy"
            data-shopping-image="true"
            data-fallback-src="${escapeHtml(resolveShoppingImageSource(''))}"
          />
        </div>
        <div class="shopping-card__badges storage-modal-badges">
          ${renderStorageBadge('Menge', formatBadgeValue(editModal.amount || activeEditItem?.amount, '0'), 'amount')}
          ${renderStorageBadge('MHD', formatBadgeValue(editModal.bestBeforeDate || activeEditItem?.best_before_date, '-'), 'mhd')}
          ${renderStorageBadge('Lagerort', editLocationLabel, 'location')}
        </div>
        <div class="storage-edit-attributes">
          <div class="storage-edit-attribute-row">
            <label for="storage-edit-amount-native">Menge</label>
            <input id="storage-edit-amount-native" class="ha-control" data-field="amount" data-role="storage-edit-field" type="number" min="0" step="0.01" value="${escapeHtml(editModal.amount || '')}" />
          </div>
          <div class="storage-edit-attribute-row">
            <label for="storage-edit-best-before-native">MHD</label>
            <input id="storage-edit-best-before-native" class="ha-control" data-field="bestBeforeDate" data-role="storage-edit-field" type="date" value="${escapeHtml(editModal.bestBeforeDate || '')}" />
          </div>
          <div class="storage-edit-attribute-row">
            <label for="storage-edit-location-select-native">Lagerort</label>
            <select id="storage-edit-location-select-native" class="ha-control" data-field="locationId" data-role="storage-edit-field">${locationOptions}</select>
          </div>
          <div class="storage-edit-attribute-row">
            <label for="storage-edit-calories-native">Kalorien (kcal)</label>
            <input id="storage-edit-calories-native" class="ha-control" data-field="calories" data-role="storage-edit-field" type="number" min="0" step="0.01" value="${escapeHtml(editModal.calories || '')}" />
          </div>
          <div class="storage-edit-attribute-row">
            <label for="storage-edit-carbs-native">Kohlenhydrate (g)</label>
            <input id="storage-edit-carbs-native" class="ha-control" data-field="carbs" data-role="storage-edit-field" type="number" min="0" step="0.01" value="${escapeHtml(editModal.carbs || '')}" />
          </div>
          <div class="storage-edit-attribute-row">
            <label for="storage-edit-fat-native">Fett (g)</label>
            <input id="storage-edit-fat-native" class="ha-control" data-field="fat" data-role="storage-edit-field" type="number" min="0" step="0.01" value="${escapeHtml(editModal.fat || '')}" />
          </div>
          <div class="storage-edit-attribute-row">
            <label for="storage-edit-protein-native">Eiweiß (g)</label>
            <input id="storage-edit-protein-native" class="ha-control" data-field="protein" data-role="storage-edit-field" type="number" min="0" step="0.01" value="${escapeHtml(editModal.protein || '')}" />
          </div>
          <div class="storage-edit-attribute-row">
            <label for="storage-edit-sugar-native">Zucker (g)</label>
            <input id="storage-edit-sugar-native" class="ha-control" data-field="sugar" data-role="storage-edit-field" type="number" min="0" step="0.01" value="${escapeHtml(editModal.sugar || '')}" />
          </div>
        </div>
        <div class="shopping-modal-save-row storage-modal-actions-row">
          <button class="secondary-button" type="button" data-action="storage-delete-product-picture" data-item-id="${escapeHtml(getActionableStorageId(activeEditItem))}" ${activeEditItem?.picture_url ? '' : 'disabled'}>Produktbild löschen</button>
          <button class="danger-button" type="button" data-action="storage-open-delete" data-item-id="${escapeHtml(getActionableStorageId(activeEditItem))}">Produkt löschen</button>
        </div>
        <div class="shopping-modal-save-row">
          <button class="secondary-button" type="button" data-action="storage-close-edit">Abbrechen</button>
          <button class="success-button" type="button" data-action="storage-save-edit">Speichern</button>
        </div>
      </section>
    </div>

    <div class="shopping-modal${consumeModal.open ? '' : ' hidden'}">
      <div class="shopping-modal-backdrop" data-action="storage-close-consume"></div>
      <section class="shopping-modal-content card storage-modal-content">
        <button class="shopping-modal-close" type="button" data-action="storage-close-consume" aria-label="Produkt verbrauchen schließen">×</button>
        <h3>${escapeHtml(activeConsumeItem?.name || 'Produkt verbrauchen')}</h3>
        <p class="muted">Wie viel soll vom Bestand verbraucht werden?</p>
        <label for="storage-consume-amount-native">Menge</label>
        <input id="storage-consume-amount-native" data-field="amount" data-role="storage-consume-field" type="number" min="0.01" step="0.01" value="${escapeHtml(consumeModal.amount || '1')}" />
        <div class="shopping-modal-save-row">
          <button class="secondary-button" type="button" data-action="storage-close-consume">Abbrechen</button>
          <button class="success-button" type="button" data-action="storage-confirm-consume">Verbrauchen</button>
        </div>
      </section>
    </div>

    <div class="shopping-modal${deleteModal.open ? '' : ' hidden'}">
      <div class="shopping-modal-backdrop" data-action="storage-close-delete"></div>
      <section class="shopping-modal-content card storage-modal-content">
        <button class="shopping-modal-close" type="button" data-action="storage-close-delete" aria-label="Produkt löschen schließen">×</button>
        <h3>Produkt löschen</h3>
        <p class="muted">Soll <strong>${escapeHtml(activeDeleteItem?.name || 'dieses Produkt')}</strong> wirklich aus dem Bestand gelöscht werden?</p>
        <div class="shopping-modal-save-row">
          <button class="secondary-button" type="button" data-action="storage-close-delete">Abbrechen</button>
          <button class="danger-button" type="button" data-action="storage-confirm-delete">Löschen</button>
        </div>
      </section>
    </div>
  `;
}

function getRecipeSuggestionDescription(item) {
  const reason = String(item?.reason || '').trim();
  const preparation = String(item?.preparation || '').replace(/\s+/g, ' ').trim();
  if (reason) return reason;
  if (!preparation) return 'Keine zusätzliche Beschreibung verfügbar.';
  return preparation.length > 120 ? `${preparation.slice(0, 117)}...` : preparation;
}

function createInitialState() {
  return {
    activeTab: DEFAULT_TAB,
    topbarStatus: 'Bereit.',
    pendingRequests: 0,
    shopping: {
      status: 'Bereit.',
      viewState: createTabViewState(),
      list: [],
      listLoading: false,
      listLoaded: false,
      pollTimer: null,
      detailModal: {
        open: false,
        itemId: null,
        amount: '',
        note: '',
      },
      mhdModal: {
        open: false,
        itemId: null,
        value: '',
      },
      scanner: {
        open: false,
        status: 'Bereit.',
        scope: 'shopping',
      },
    },
    recipes: {
      status: 'Bereit.',
      viewState: createTabViewState(),
      initialized: false,
      locations: [],
      stockProducts: [],
      grocyRecipes: [],
      aiRecipes: [],
      selectedLocationIds: [],
      selectedProductIds: [],
      stockSignature: null,
      hasLoadedInitialSuggestions: false,
      expiringWithinDays: 3,
      detailModal: {
        open: false,
        item: null,
      },
      createModal: {
        open: false,
        method: 'webscrape',
        webscrapeUrl: '',
        aiPrompt: '',
        manualTitle: '',
        manualServings: '2',
        manualIngredients: '',
        manualPreparation: '',
      },
    },
    storage: {
      status: 'Bereit.',
      viewState: createTabViewState(),
      initialized: false,
      loading: false,
      items: [],
      summary: {
        totalCount: 0,
        inStockCount: 0,
        outOfStockCount: 0,
      },
      locations: [],
      filter: '',
      includeAllProducts: false,
      editModal: {
        open: false,
        itemId: null,
        amount: '',
        bestBeforeDate: '',
        locationId: '',
        calories: '',
        carbs: '',
        fat: '',
        protein: '',
        sugar: '',
      },
      consumeModal: {
        open: false,
        itemId: null,
        amount: '1',
      },
      deleteModal: {
        open: false,
        itemId: null,
      },
    },
    notifications: {
      status: 'Benachrichtigungen werden bei Bedarf im Notfallpfad geöffnet.',
      viewState: createTabViewState({ loaded: true, empty: true }),
      legacyFallbackUrl: '',
    },
  };
}

function createTabViewState(overrides = {}) {
  return {
    loaded: false,
    loading: false,
    error: '',
    empty: false,
    editing: false,
    ...overrides,
  };
}

class GrocyAITopbar extends HTMLElement {
  connectedCallback() {
    this.addEventListener('click', (event) => {
      const actionTarget = event.target.closest('[data-action]');
      if (!actionTarget) return;
      this.dispatchEvent(new CustomEvent(actionTarget.dataset.action, {
        bubbles: true,
        composed: true,
      }));
    });
  }

  set viewModel(value) {
    this._viewModel = value;
    this._render();
  }

  _render() {
    const model = this._viewModel || {
      status: 'Bereit.',
      busy: false,
      migratedCount: 0,
      totalCount: 0,
      panelPath: `/${PANEL_SLUG}`,
      activeTab: 'shopping',
    };
    this.innerHTML = `
      <header class="topbar">
        <div class="topbar-content">
          <div class="topbar-brand">
            <p class="eyebrow">Grocy AI Assistant</p>
            <div class="topbar-title-row">
              ${renderHaIcon(model.panelIcon || PANEL_ICON, 'topbar-title-icon')}
              <h1>${PANEL_TITLE}</h1>
            </div>
          </div>
          <div class="topbar-meta">
            <p class="topbar-status" aria-live="polite">${escapeHtml(model.status)}</p>
            <span class="activity-spinner${model.busy ? '' : ' hidden'}" aria-label="Lädt"></span>
          </div>
        </div>
      </header>
    `;
  }
}

class GrocyAITabNav extends HTMLElement {
  constructor() {
    super();
    this._viewModel = { activeTab: 'shopping' };
    this._elements = null;
  }

  connectedCallback() {
    this.addEventListener('click', (event) => {
      const button = event.target.closest('[data-tab]');
      if (!button) return;
      this.dispatchEvent(new CustomEvent('tab-change', {
        bubbles: true,
        composed: true,
        detail: { tab: button.dataset.tab },
      }));
    });

    this._ensureStructure();
    this._syncViewModel();
  }

  set viewModel(value) {
    this._viewModel = {
      ...this._viewModel,
      ...(value || {}),
    };
    this._ensureStructure();
    this._syncViewModel();
  }

  _ensureStructure() {
    if (this._elements) return;

    const nav = document.createElement('nav');
    nav.className = 'bottom-tabbar';
    nav.setAttribute('aria-label', 'Navigation');
    nav.setAttribute('role', 'tablist');

    const buttons = new Map();
    VISIBLE_TAB_ORDER.forEach((tab) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'tab-button';
      button.dataset.tab = tab;
      button.id = getTabButtonId(tab);
      button.setAttribute('role', 'tab');
      button.setAttribute('aria-controls', getTabPanelId(tab));

      button.innerHTML = `
        ${renderHaIcon(TAB_ICONS[tab], 'tab-button__icon')}
        <span class="tab-button__label">${TAB_LABELS[tab]}</span>
        ${MIGRATED_TABS.has(tab) ? '' : '<span class="tab-button__meta">Fallback</span>'}
      `;

      nav.append(button);
      buttons.set(tab, button);
    });

    this.replaceChildren(nav);
    this._elements = { nav, buttons };
  }

  _syncViewModel() {
    if (!this._elements) return;

    const activeTab = this._viewModel?.activeTab || 'shopping';
    this._elements.buttons.forEach((button, tab) => {
      const isActive = tab === activeTab;
      button.classList.toggle('active', isActive);
      button.setAttribute('aria-selected', isActive ? 'true' : 'false');
      button.setAttribute('tabindex', isActive ? '0' : '-1');
    });
  }
}

class GrocyAIShoppingSearchBar extends HTMLElement {
  constructor() {
    super();
    this._viewModel = {};
    this._renderedVariantSignature = '';
    this._renderedStatusSignature = '';
    this._boundInput = (event) => {
      this.dispatchEvent(new CustomEvent('shopping-query-change', {
        bubbles: true,
        composed: true,
        detail: { query: event.target.value },
      }));
    };
  }

  connectedCallback() {
    this.addEventListener('input', (event) => {
      if (event.target.matches('[data-role="shopping-query"]')) {
        this._boundInput(event);
      }
    });
    this.addEventListener('submit', (event) => {
      if (!event.target.matches('[data-role="shopping-search-form"]')) return;
      event.preventDefault();
      this.dispatchEvent(new CustomEvent('shopping-submit-query', {
        bubbles: true,
        composed: true,
      }));
    });
    this.addEventListener('click', (event) => {
      const actionTarget = event.target.closest('[data-action]');
      if (!actionTarget) return;
      const detail = { ...actionTarget.dataset };
      this.dispatchEvent(new CustomEvent(actionTarget.dataset.action, {
        bubbles: true,
        composed: true,
        detail,
      }));
    });
  }

  set viewModel(value) {
    this._viewModel = value;
    this._render();
  }

  _ensureStructure() {
    if (this._elements) return;

    const shell = document.createElement('section');
    shell.setAttribute('aria-live', 'polite');

    const header = document.createElement('div');
    header.className = 'shopping-search-shell__header';
    const headerCopy = document.createElement('div');
    const eyebrow = document.createElement('p');
    eyebrow.className = 'eyebrow';
    eyebrow.textContent = 'Produktsuche';
    const title = document.createElement('h3');
    title.className = 'shopping-search-shell__title';
    title.textContent = 'Produkt suchen oder Variante wählen';
    headerCopy.append(eyebrow, title);
    const stateChip = document.createElement('span');
    header.append(headerCopy, stateChip);

    const form = document.createElement('form');
    form.className = 'search-row shopping-search-form';
    form.dataset.role = 'shopping-search-form';
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      this.dispatchEvent(new CustomEvent('shopping-submit-query', {
        bubbles: true,
        composed: true,
      }));
    });

    const inputWrapper = document.createElement('div');
    inputWrapper.className = 'search-input-wrapper';

    const input = document.createElement('input');
    input.dataset.role = 'shopping-query';
    input.placeholder = 'z.B. 2 Hafermilch';
    input.autocomplete = 'off';
    input.enterKeyHint = 'search';
    input.setAttribute('aria-describedby', 'shopping-search-helper');
    input.addEventListener('input', (event) => this._boundInput(event));

    const clearButton = document.createElement('button');
    clearButton.className = 'clear-input-button';
    clearButton.type = 'button';
    clearButton.dataset.action = 'shopping-clear-query';
    clearButton.setAttribute('aria-label', 'Sucheingabe löschen');
    clearButton.textContent = '×';
    clearButton.addEventListener('click', () => {
      this.dispatchEvent(new CustomEvent('shopping-clear-query', {
        bubbles: true,
        composed: true,
      }));
    });
    inputWrapper.append(input, clearButton);

    const submitButton = document.createElement('button');
    submitButton.className = 'primary-button search-submit-button';
    submitButton.type = 'submit';

    form.append(inputWrapper, submitButton);

    const helper = document.createElement('p');
    helper.id = 'shopping-search-helper';
    helper.className = 'search-helper-text';

    const variantSection = document.createElement('section');
    const variantHeader = document.createElement('div');
    variantHeader.className = 'section-header section-header-stacked';
    const variantHeaderCopy = document.createElement('div');
    const variantTitle = document.createElement('h3');
    variantTitle.textContent = 'Gefundene Produktvarianten';
    const variantHint = document.createElement('p');
    variantHint.className = 'muted';
    variantHeaderCopy.append(variantTitle, variantHint);
    const loadingHint = document.createElement('span');
    loadingHint.className = 'muted';
    variantHeader.append(variantHeaderCopy, loadingHint);

    const variantGrid = document.createElement('div');
    variantGrid.className = 'variant-grid variant-grid--search';
    variantGrid.setAttribute('role', 'list');

    variantSection.append(variantHeader, variantGrid);
    shell.append(header, form, helper, variantSection);
    this.replaceChildren(shell);

    this._elements = {
      shell,
      stateChip,
      form,
      input,
      clearButton,
      submitButton,
      helper,
      variantSection,
      variantHint,
      loadingHint,
      variantGrid,
    };
  }

  _captureQueryInputState() {
    const input = this._elements?.input;
    if (!input) return null;
    return {
      isFocused: document.activeElement === input,
      selectionStart: typeof input.selectionStart === 'number' ? input.selectionStart : null,
      selectionEnd: typeof input.selectionEnd === 'number' ? input.selectionEnd : null,
    };
  }

  _restoreQueryInputState(snapshot) {
    const input = this._elements?.input;
    if (!snapshot || !input) return;
    if (snapshot.isFocused && typeof input.focus === 'function') {
      input.focus();
    }
    if (typeof input.setSelectionRange === 'function'
      && snapshot.selectionStart !== null
      && snapshot.selectionEnd !== null) {
      input.setSelectionRange(snapshot.selectionStart, snapshot.selectionEnd);
    }
  }

  _createVariantCard(variant, parsedAmount) {
    const markup = renderShoppingVariantCard(variant, {
      amount: parsedAmount || variant.amount || variant.default_amount || '1',
      actionName: 'shopping-select-variant',
      ctaLabel: 'Auswählen',
      resolveImageUrl: this._viewModel?.resolveImageUrl,
    }).trim();
    const template = document.createElement('template');
    template.innerHTML = markup;
    const article = template.content.firstElementChild;
    const button = article?.querySelector('.variant-card__button');

    if (!article || !button) {
      return document.createElement('article');
    }

    button.addEventListener('click', () => {
      this.dispatchEvent(new CustomEvent('shopping-select-variant', {
        bubbles: true,
        composed: true,
        detail: { ...button.dataset },
      }));
    });
    return article;
  }

  _renderVariantGrid(model, variants) {
    const { variantGrid } = this._elements;
    const variantSignature = JSON.stringify({
      parsedAmount: model.parsedAmount ?? null,
      showLoadingPlaceholder: !variants.length && Boolean(model.isLoadingVariants),
      variants: variants.map((variant) => ({
        id: variant.product_id || variant.id || '',
        name: variant.product_name || variant.name || '',
        amount: variant.amount || variant.default_amount || '',
        source: variant.source || 'grocy',
      })),
    });
    if (variantSignature === this._renderedVariantSignature) return;

    const snapshot = this._captureQueryInputState();
    this._renderedVariantSignature = variantSignature;

    if (!variants.length && model.isLoadingVariants) {
      const loadingMessage = document.createElement('p');
      loadingMessage.className = 'muted';
      loadingMessage.textContent = 'Lade Vorschläge…';
      variantGrid.replaceChildren(loadingMessage);
      this._restoreQueryInputState(snapshot);
      return;
    }

    const nodes = variants.map((variant) => this._createVariantCard(variant, model.parsedAmount));
    variantGrid.replaceChildren(...nodes);
    bindShoppingImageFallbacks(this);
    this._restoreQueryInputState(snapshot);
  }

  _render() {
    this._ensureStructure();
    const model = this._viewModel || {};
    const variants = Array.isArray(model.variants) ? model.variants : [];
    const searchUiState = deriveSearchUiState(model);
    const stateLabel = getSearchStateLabel(searchUiState);
    const helperText = model.errorMessage || model.statusMessage || 'Bereit.';
    const hasVisibleVariants = variants.length > 0;
    const {
      shell,
      stateChip,
      form,
      input,
      clearButton,
      submitButton,
      helper,
      variantSection,
      variantHint,
      loadingHint,
    } = this._elements;

    const statusSignature = JSON.stringify({
      query: model.query || '',
      clearButtonVisible: Boolean(model.clearButtonVisible),
      isSubmitting: Boolean(model.isSubmitting),
      isLoadingVariants: Boolean(model.isLoadingVariants),
      errorMessage: model.errorMessage || '',
      statusMessage: model.statusMessage || '',
      parsedAmount: model.parsedAmount ?? null,
      searchUiState,
    });

    if (statusSignature !== this._renderedStatusSignature) {
      this._renderedStatusSignature = statusSignature;
      shell.className = `shopping-search-shell shopping-search-shell--${searchUiState}`;
      stateChip.className = `search-state-chip search-state-chip--${searchUiState}`;
      stateChip.textContent = stateLabel;
      form.setAttribute('aria-busy', model.isSubmitting ? 'true' : 'false');
      if (input.value !== String(model.query || '')) {
        input.value = String(model.query || '');
      }
      clearButton.className = `clear-input-button${model.clearButtonVisible ? ' visible' : ''}`;
      submitButton.disabled = Boolean(model.isSubmitting);
      submitButton.textContent = model.isSubmitting ? 'Prüfe…' : 'Produkt prüfen';
      helper.className = `search-helper-text${model.errorMessage ? ' search-helper-text--error' : ''}`;
      helper.textContent = helperText;
      variantSection.className = `variant-section${hasVisibleVariants || model.isLoadingVariants ? '' : ' hidden'}`;
      variantHint.textContent = model.parsedAmount
        ? `Erkannte Menge: ${formatAmount(model.parsedAmount)}`
        : 'Live-Vorschläge erscheinen direkt unter dem Eingabefeld.';
      loadingHint.textContent = model.isLoadingVariants ? 'Suche läuft…' : '';
    }

    this._renderVariantGrid(model, variants);
  }
}

class GrocyAIShoppingTab extends HTMLElement {
  constructor() {
    super();
    this._viewModel = {};
    this._lastListSignature = '';
    this._lastShellSignature = '';
    this._cleanupSwipe = null;
    this._boundClick = (event) => {
      const actionTarget = event.target.closest?.('[data-action]');
      if (!actionTarget) return;
      this.dispatchEvent(new CustomEvent(actionTarget.dataset.action, {
        bubbles: true,
        composed: true,
        detail: { ...actionTarget.dataset },
      }));
    };
  }

  connectedCallback() {
    this.addEventListener('click', this._boundClick);
  }

  disconnectedCallback() {
    this.removeEventListener('click', this._boundClick);
    this._cleanupSwipe?.();
    this._cleanupSwipe = null;
  }

  set viewModel(value) {
    this._viewModel = value;
    this._render();
  }

  _ensureStructure() {
    if (this._elements) return;

    const root = document.createElement('section');
    root.id = getTabPanelId('shopping');
    root.setAttribute('role', 'tabpanel');
    root.setAttribute('aria-labelledby', getTabButtonId('shopping'));

    const heroCard = document.createElement('section');
    heroCard.className = 'card hero-card shopping-hero-card';
    const heroHeader = document.createElement('div');
    heroHeader.className = 'section-header';
    const heroTitle = document.createElement('h2');
    heroTitle.textContent = 'Grocy AI Suche';
    const scannerButton = document.createElement('button');
    scannerButton.className = 'scanner-popup-button';
    scannerButton.type = 'button';
    scannerButton.dataset.action = 'shopping-open-scanner';
    scannerButton.setAttribute('aria-label', 'Barcode-Scanner öffnen');
    const scannerIcon = document.createElement('span');
    scannerIcon.className = 'scanner-barcode-icon';
    scannerIcon.setAttribute('aria-hidden', 'true');
    scannerButton.append(scannerIcon);
    heroHeader.append(heroTitle, scannerButton);
    const searchBar = document.createElement('grocy-ai-shopping-search-bar');
    heroCard.append(heroHeader, searchBar);

    const listSection = document.createElement('section');
    listSection.className = 'card shopping-list-section';
    const listHeader = document.createElement('div');
    listHeader.className = 'section-header section-header-stacked';
    const listTitle = document.createElement('h2');
    listTitle.textContent = 'Einkaufsliste';
    const refreshButton = document.createElement('button');
    refreshButton.className = 'primary-button';
    refreshButton.type = 'button';
    refreshButton.dataset.action = 'shopping-refresh';
    refreshButton.textContent = 'Aktualisieren';
    listHeader.append(listTitle, refreshButton);

    const list = document.createElement('ul');
    list.className = 'shopping-list-native';
    const status = document.createElement('p');
    status.className = 'tab-status';

    const buttonRow = document.createElement('div');
    buttonRow.className = 'button-row';
    const completeAllButton = document.createElement('button');
    completeAllButton.className = 'success-button';
    completeAllButton.type = 'button';
    completeAllButton.dataset.action = 'shopping-complete-all';
    completeAllButton.textContent = 'Einkauf abschließen';
    const clearAllButton = document.createElement('button');
    clearAllButton.className = 'danger-button';
    clearAllButton.type = 'button';
    clearAllButton.dataset.action = 'shopping-clear-all';
    clearAllButton.textContent = 'Einkaufsliste leeren';
    buttonRow.append(completeAllButton, clearAllButton);

    listSection.append(listHeader, list, status, buttonRow);
    root.append(heroCard, listSection);
    this.replaceChildren(root);

    this._elements = {
      root,
      searchBar,
      list,
      status,
    };
  }

  _createShoppingListItem(item, model) {
    const listItem = document.createElement('li');
    listItem.className = 'shopping-list-native__item shopping-item swipe-item';
    listItem.dataset.itemId = String(item.id);
    listItem.innerHTML = `
      <div class="swipe-item-action swipe-item-action-left" aria-hidden="true">
        <span class="swipe-chip swipe-chip-buy">🛒 Kaufen</span>
      </div>
      <div class="swipe-item-action swipe-item-action-right" aria-hidden="true">
        <span class="swipe-chip swipe-chip-delete">🗑 Löschen</span>
      </div>
      <div class="shopping-item-content swipe-item-content">
        ${renderShoppingListItemCard(item, {
          rootClassName: 'shopping-item-card shopping-item-card--legacy',
          contextFields: ['location'],
          stockBadgePlacement: 'aside',
          stockBadgeOrder: 'first',
          statusChip: false,
          resolveImageUrl: model.resolveImageUrl,
          amountBadge: {
            element: 'button',
            variant: 'amount',
            className: 'amount-increment-button',
            dataset: {
              action: 'shopping-increment-item',
              'item-id': item.id,
            },
          },
          mhdBadge: {
            element: 'button',
            variant: 'mhd',
            className: 'mhd-picker-button',
            hideLabel: true,
            dataset: {
              action: 'shopping-open-mhd',
              'item-id': item.id,
            },
          },
        })}
      </div>
    `;
    return listItem;
  }

  _rebindSwipeInteractions() {
    this._cleanupSwipe?.();
    this._cleanupSwipe = bindSwipeInteractions({
      root: this,
      selector: '.shopping-item.swipe-item',
      getPayload: (item) => ({ itemId: item.dataset.itemId }),
      interactiveElementSelector: '.amount-increment-button, .mhd-picker-button',
      onTap: (_, payload) => {
        this.dispatchEvent(new CustomEvent('shopping-open-detail', {
          bubbles: true,
          composed: true,
          detail: { itemId: payload.itemId },
        }));
      },
      onSwipeLeft: async (_, payload) => {
        this.dispatchEvent(new CustomEvent('shopping-delete-item', {
          bubbles: true,
          composed: true,
          detail: { itemId: payload.itemId },
        }));
      },
      onSwipeRight: async (_, payload) => {
        this.dispatchEvent(new CustomEvent('shopping-complete-item', {
          bubbles: true,
          composed: true,
          detail: { itemId: payload.itemId },
        }));
      },
    });
  }

  _renderList(model, items) {
    const { list } = this._elements;
    const listSignature = JSON.stringify({
      listLoading: Boolean(model.listLoading),
      items: items.map((item) => ({
        id: item.id,
        product_name: item.product_name || '',
        amount: formatAmount(item.amount),
        note: item.note || '',
        best_before_date: item.best_before_date || '',
      })),
    });
    if (listSignature === this._lastListSignature) return;
    this._lastListSignature = listSignature;

    this._cleanupSwipe?.();
    this._cleanupSwipe = null;

    if (!items.length) {
      const emptyItem = document.createElement('li');
      emptyItem.className = 'muted';
      emptyItem.textContent = model.listLoading ? 'Einkaufsliste wird geladen…' : 'Keine Einträge.';
      list.replaceChildren(emptyItem);
      return;
    }

    list.replaceChildren(...items.map((item) => this._createShoppingListItem(item, model)));
    bindShoppingImageFallbacks(this);
    this._rebindSwipeInteractions();
  }

  _render() {
    this._ensureStructure();
    const model = this._viewModel || {};
    const items = Array.isArray(model.list) ? model.list : [];
    const shellSignature = JSON.stringify({
      active: Boolean(model.active),
      status: model.status || 'Bereit.',
    });

    if (shellSignature !== this._lastShellSignature) {
      this._lastShellSignature = shellSignature;
      const root = this._elements.root;
      root.className = `tab-view${model.active ? '' : ' hidden'}`;
      if (typeof root.toggleAttribute === 'function') {
        root.toggleAttribute('hidden', !model.active);
      } else if (model.active) {
        if (typeof root.removeAttribute === 'function') {
          root.removeAttribute('hidden');
        } else {
          root.hidden = false;
        }
      } else {
        if (typeof root.setAttribute === 'function') {
          root.setAttribute('hidden', '');
        } else {
          root.hidden = true;
        }
      }
      root.setAttribute('aria-hidden', model.active ? 'false' : 'true');
      root.tabIndex = model.active ? 0 : -1;
      this._elements.status.textContent = model.status || 'Bereit.';
    }

    this._elements.searchBar.viewModel = {
      ...model,
    };
    this._renderList(model, items);
  }
}


function buildLegacyBridgeFrameMarkup(model = {}) {
  const shouldMountIframe = Boolean(model.active);
  return `
    <div class="legacy-frame-shell${shouldMountIframe ? '' : ' hidden'}">
      ${shouldMountIframe ? `<iframe class="legacy-frame" title="${escapeHtml(model.title || 'Legacy Dashboard')}" src="${escapeHtml(model.legacyUrl || DEFAULT_LEGACY_URL)}"></iframe>` : ''}
    </div>
  `;
}

function renderRecipeListMarkup(items, emptyText, options = {}) {
  const normalizedItems = Array.isArray(items) ? items : [];
  if (!normalizedItems.length) {
    return `<ul class="recipe-list-native"><li class="muted">${escapeHtml(emptyText)}</li></ul>`;
  }

  return `
    <ul class="recipe-list-native">
      ${normalizedItems.map((item) => {
        const payload = encodeURIComponent(JSON.stringify(item));
        const description = getRecipeSuggestionDescription(item);
        const imageSrc = item.picture_url
          ? toImageSource(item.picture_url, { apiBasePath: options.apiBasePath || '' })
          : '';
        return `
          <li class="recipe-item-native">
            <button type="button" class="recipe-item-native__button" data-action="recipes-open-detail" data-recipe-item="${payload}">
              ${imageSrc
                ? `<img class="recipe-thumb" src="${escapeHtml(imageSrc)}" alt="${escapeHtml(item.title || 'Rezeptbild')}" loading="lazy" />`
                : '<div class="recipe-thumb recipe-thumb-fallback">🍽️</div>'}
              <span class="recipe-item-copy">
                <span class="recipe-item-title">${escapeHtml(item.title || 'Unbenanntes Rezept')}</span>
                <span class="muted recipe-item-description">${escapeHtml(description)}</span>
              </span>
            </button>
          </li>
        `;
      }).join('')}
    </ul>
  `;
}

function renderRecipeLocationFiltersMarkup(locations, selectedLocationIds) {
  const items = Array.isArray(locations) ? locations : [];
  const selectedIds = new Set(selectedLocationIds);
  if (!items.length) {
    return '<div class="muted">Keine Lagerstandorte gefunden.</div>';
  }

  const summaryLabel = summarizeSelectedItems(items, selectedLocationIds, 'Keine Auswahl');

  return `
    <details class="location-dropdown" data-dropdown-key="recipes-locations">
      <summary>
        <span class="location-dropdown__summary-copy">
          <span class="location-dropdown__summary-title">Lagerort</span>
          <span class="location-dropdown__summary-value">${escapeHtml(summaryLabel)}</span>
        </span>
        ${renderStorageBadge('Standorte', String(selectedIds.size || items.length), 'location', 'location-dropdown__summary-badge')}
      </summary>
      <div class="location-options">
        ${items.map((item) => `
          <label class="stock-item">
            <input
              type="checkbox"
              data-role="recipes-location"
              value="${escapeHtml(item.id)}"
              ${selectedIds.size === 0 || selectedIds.has(Number(item.id)) ? 'checked' : ''}
            />
            <span class="stock-item-name"><strong>${escapeHtml(item.name || `Lagerort ${item.id}`)}</strong></span>
          </label>
        `).join('')}
      </div>
    </details>
  `;
}

function renderRecipeStockProductsMarkup(products, selectedProductIds) {
  const items = (Array.isArray(products) ? products : []).map(normalizeStockProduct);
  const selectedIds = new Set(selectedProductIds);
  const summaryLabel = summarizeSelectedItems(items, selectedProductIds, 'Keine Auswahl');
  return `
    <details class="location-dropdown" data-dropdown-key="recipes-products">
      <summary>
        <span class="location-dropdown__summary-copy">
          <span class="location-dropdown__summary-title">Produkte in ausgewählten Standorten</span>
          <span class="location-dropdown__summary-value">${escapeHtml(summaryLabel)}</span>
        </span>
        ${renderStorageBadge('Produkte', String(selectedIds.size || items.length), 'amount', 'location-dropdown__summary-badge')}
      </summary>
      <div class="stock-options">
        ${items.length ? items.map((item) => `
          <label class="stock-item">
            <input
              type="checkbox"
              data-role="recipes-product"
              value="${escapeHtml(item.id)}"
              ${selectedIds.size === 0 || selectedIds.has(Number(item.id)) ? 'checked' : ''}
            />
            <span class="stock-item-name"><strong>${escapeHtml(item.name || 'Unbekanntes Produkt')}</strong></span>
            <span class="stock-item-attributes">
              ${renderStorageBadge('Menge', formatAmount(item.amount) || '-', 'amount')}
              ${renderStorageBadge('MHD', item.best_before_date || '-', 'mhd')}
              ${item.location_name ? renderStorageBadge('Lagerort', item.location_name, 'location') : ''}
            </span>
          </label>
        `).join('') : '<div class="muted">Keine Produkte für die ausgewählten Lagerstandorte gefunden.</div>'}
      </div>
    </details>
  `;
}

function buildRecipesTabMarkup(model = {}) {
  const grocyRecipes = Array.isArray(model.grocyRecipes) ? model.grocyRecipes : [];
  const aiRecipes = Array.isArray(model.aiRecipes) ? model.aiRecipes : [];
  const locations = Array.isArray(model.locations) ? model.locations : [];
  const stockProducts = Array.isArray(model.stockProducts) ? model.stockProducts : [];

  const recipeCards = [
    renderCardContainer({
      className: 'panel-preview-card recipes-preview-card',
      eyebrow: 'Rezepte',
      title: 'Gespeicherte Grocy-Rezepte',
      titleTag: 'h3',
      body: renderRecipeListMarkup(grocyRecipes, 'Keine gespeicherten Grocy-Rezepte gefunden.', model),
    }),
    renderCardContainer({
      className: 'panel-preview-card recipes-preview-card',
      eyebrow: 'Rezepte',
      title: 'KI-Rezeptvorschläge',
      titleTag: 'h3',
      body: renderRecipeListMarkup(aiRecipes, 'Keine KI-Rezepte erzeugt.', model),
    }),
  ];
  const stockCards = [
    renderCardContainer({
      className: 'panel-preview-card recipes-preview-card',
      eyebrow: 'Bestände',
      title: 'Lagerstandorte',
      titleTag: 'h3',
      body: renderRecipeLocationFiltersMarkup(locations, model.selectedLocationIds || []),
    }),
    renderCardContainer({
      className: 'panel-preview-card recipes-preview-card',
      eyebrow: 'Bestände',
      title: 'Produkte in ausgewählten Standorten',
      titleTag: 'h3',
      body: renderRecipeStockProductsMarkup(stockProducts, model.selectedProductIds || []),
    }),
  ];

  return `
    ${renderCardContainer({
      className: 'hero-card recipes-hero-card',
      eyebrow: 'Rezepte',
      title: 'Rezeptvorschläge',
      body: renderActionRow([
        { label: 'Rezept hinzufügen', className: 'primary-button', dataset: { action: 'recipes-open-create' } },
        { label: 'Rezepte laden', className: 'primary-button', dataset: { action: 'recipes-load-suggestions' } },
      ], { className: 'recipes-primary-actions' }),
    })}
    ${renderTwoColumnCardGroup(recipeCards, { className: 'recipes-card-group' })}
    ${renderTwoColumnCardGroup(stockCards, { className: 'recipes-card-group' })}
    ${renderCardContainer({
      className: 'panel-preview-card recipes-preview-card',
      eyebrow: 'Aktionen',
      title: 'Rezeptvorschläge laden',
      titleTag: 'h3',
      body: `
        <div class="recipe-actions">
          <div class="expiring-search-controls">
            <label for="recipes-expiring-days">Ablauf in Tagen</label>
            <input
              id="recipes-expiring-days"
              class="ha-control"
              data-role="recipes-expiring-days"
              type="number"
              min="1"
              max="30"
              value="${escapeHtml(model.expiringWithinDays || 3)}"
            />
            <button class="secondary-button" type="button" data-action="recipes-load-expiring">
              Mit bald ablaufenden Produkten suchen
            </button>
          </div>
          <p class="tab-status">${escapeHtml(model.status || 'Bereit.')}</p>
        </div>
      `,
    })}
  `;
}

function buildStoragePreviewMarkup(model = {}) {
  const panelPath = model.panelPath || `/${PANEL_SLUG}`;
  const inventoryCards = [
    renderCardContainer({
      className: 'panel-preview-card storage-preview-card',
      eyebrow: 'Lager',
      title: 'Filter & Bestand',
      titleTag: 'h3',
      description: 'Die Storage-Ansicht behält ihre Header-Hierarchie, Kontrollzeile und Kachelfläche bei.',
      body: renderTileGrid([
        renderStateCard({
          eyebrow: 'Controls',
          title: 'Filter bleibt über dem Grid',
          message: 'Suchfeld, Toggle und Aktionsleiste bleiben oberhalb des Produktgrids angeordnet – analog zum Legacy-Markup.',
          stateLabel: 'Kontrollmuster',
          stateVariant: 'source',
          meta: ['section-header', 'button-row', 'card'],
        }),
      ], { className: 'storage-preview-grid' }),
    }),
    renderCardContainer({
      className: 'panel-preview-card storage-preview-card',
      eyebrow: 'Lager',
      title: 'Produktkacheln',
      titleTag: 'h3',
      description: 'Bestandsprodukte bleiben in einer Kachel-/Grid-Darstellung statt in eine einfache Listenansicht zu kippen.',
      body: renderTileGrid([
        renderStateCard({
          eyebrow: 'Grid',
          title: 'Variant-Grid bleibt Variant-Grid',
          message: 'Die gemeinsame Grid-Hülle aus Shopping und Lager trägt künftig sowohl Produktkacheln als auch Statuskarten.',
          stateLabel: 'Grid geteilt',
          stateVariant: 'shopping',
          meta: ['variant-grid', 'shopping-card', 'Kachel bleibt Kachel'],
        }),
      ], { className: 'storage-preview-grid' }),
    }),
  ];

  return `
    ${renderCardContainer({
      className: 'hero-card storage-hero-card',
      eyebrow: 'Lager',
      title: 'Lager',
      description: 'Auch vor der eigentlichen Migration wird die visuelle Logik aus dem Legacy-Dashboard beibehalten: Grid bleibt Grid, Modal bleibt Modal und CTAs behalten ihre Gewichtung.',
      actions: [
        { label: 'Legacy-Dashboard öffnen', className: 'primary-button', dataset: { action: 'open-legacy-dashboard' } },
        { label: 'Shopping-Referenz ansehen', className: 'ghost-button', href: buildPanelTabHref(panelPath, 'shopping') },
      ],
      body: [
        renderMetaBadges(['hero-card', 'storage-controls', 'vergleichbare Abstände']),
        renderActionRow([
          { label: 'Aktualisieren bleibt primär', className: 'primary-button', dataset: { action: 'open-legacy-dashboard' } },
          { label: 'Modal bleibt Modal', className: 'secondary-button', dataset: { action: 'open-legacy-dashboard' } },
        ]),
      ].join(''),
    })}
    ${renderTwoColumnCardGroup(inventoryCards, { className: 'storage-card-group' })}
    ${renderCardContainer({
      className: 'panel-preview-card storage-preview-card',
      eyebrow: 'Statuszustände',
      title: 'Shared-State-Karten',
      titleTag: 'h3',
      description: 'Loading-, Empty- und Statusflächen werden für Lager als wiederverwendbare Card-Surfaces vorbereitet, bevor einzelne Produktaktionen nativ migriert werden.',
      body: renderTileGrid([
        renderStateCard({
          eyebrow: 'Loading',
          title: 'Ladezustand als Karte',
          message: 'Asynchrone Storage-Flows bekommen dieselbe Kartenoberfläche wie in Shopping statt einfacher Text-Platzhalter.',
          stateLabel: 'Loading',
          stateVariant: 'source',
          meta: ['Loading-Karte', 'Status-Karte'],
        }),
        renderStateCard({
          eyebrow: 'Empty',
          title: 'Leere Bestände als Kachel',
          message: 'Auch leere Zustände bleiben visuell Teil des Grids und rutschen nicht in unstrukturierte Fließtexte ab.',
          stateLabel: 'Empty',
          stateVariant: 'mhd',
          meta: ['Empty-Karte', 'Grid bleibt Grid'],
        }),
      ], { className: 'storage-preview-grid storage-preview-grid--dual' }),
    })}
    ${renderCardContainer({
      className: 'legacy-bridge-card',
      eyebrow: 'Legacy-Bridge',
      title: model.title || 'Lager im Legacy-Dashboard',
      description: 'Das Legacy-Lager bleibt vorerst eingebettet, bekommt aber bereits die gemeinsamen Karten-, Grid- und Aktionsmuster als sichtbare Migrationsschicht.',
      body: buildLegacyBridgeFrameMarkup(model),
    })}
  `;
}

class GrocyAILegacyBridgeTab extends HTMLElement {
  set viewModel(value) {
    this._viewModel = value;
    this._render();
  }

  _attachLegacyBridgeListeners(model = {}) {
    const frame = this.querySelector('iframe');
    frame?.addEventListener('load', () => {
      try {
        frame.contentWindow?.switchTab?.(model.tabName);
      } catch (_) {
        // Same-origin is expected, but silently tolerate fallback cases.
      }
    }, { once: true });

    this.querySelectorAll('[data-action="open-legacy-dashboard"]').forEach((button) => {
      button.addEventListener('click', () => {
        this.dispatchEvent(new CustomEvent('open-legacy-dashboard', {
          bubbles: true,
          composed: true,
          detail: { tab: model.tabName },
        }));
      });
    });
  }

  _render() {
    const model = this._viewModel || {};
    this.innerHTML = `
      <section
        id="${getTabPanelId('notifications')}"
        class="tab-view${model.active ? '' : ' hidden'}"
        role="tabpanel"
        aria-labelledby="${getTabButtonId('notifications')}"
        aria-hidden="${model.active ? 'false' : 'true'}"
        ${model.active ? 'tabindex="0"' : 'tabindex="-1" hidden'}
      >
        ${renderCardContainer({
          className: 'legacy-bridge-card',
          eyebrow: 'Tabweise Migration',
          title: model.title || 'Dashboard-Bereich',
          description: 'Dieser Bereich ist bereits als eigene Frontend-Komponente gekapselt, rendert Inhalte aber vorübergehend weiter über das bestehende Dashboard, bis alle Zustände, Polling-Flows, Modals und Scanner-Funktionen nativ migriert sind.',
          actions: [{ label: 'Legacy-Dashboard öffnen', className: 'primary-button', dataset: { action: 'open-legacy-dashboard' } }],
          body: [
            renderMetaBadges(['Store-angebunden', 'Tab-spezifische Bridge', 'Legacy-Fallback aktiv']),
            buildLegacyBridgeFrameMarkup(model),
          ].join(''),
        })}
      </section>
    `;

    this._attachLegacyBridgeListeners(model);
  }
}

class GrocyAIDashboardModals extends HTMLElement {
  constructor() {
    super();
    this._renderSignature = null;
  }

  connectedCallback() {
    this.addEventListener('click', (event) => {
      const actionTarget = event.target.closest('[data-action]');
      if (!actionTarget) return;
      this.dispatchEvent(new CustomEvent(actionTarget.dataset.action, {
        bubbles: true,
        composed: true,
        detail: { ...actionTarget.dataset },
      }));
    });
    this.addEventListener('input', (event) => {
      const field = event.target.closest('[data-field]');
      if (field) {
        this.dispatchEvent(new CustomEvent('shopping-modal-input', {
          bubbles: true,
          composed: true,
          detail: {
            field: field.dataset.field,
            value: field.value,
          },
        }));
        return;
      }

      const recipeField = event.target.closest('[data-recipe-field]');
      if (!recipeField) return;
      this.dispatchEvent(new CustomEvent('recipes-create-input', {
        bubbles: true,
        composed: true,
        detail: {
          field: recipeField.dataset.recipeField,
          value: recipeField.value,
        },
      }));
    });
  }

  set viewModel(value) {
    this._viewModel = value;
    const nextSignature = JSON.stringify({
      shopping: {
        detailOpen: Boolean(value?.shopping?.detailModal?.open),
        detailItemId: value?.shopping?.detailModal?.itemId ?? null,
        mhdOpen: Boolean(value?.shopping?.mhdModal?.open),
        mhdItemId: value?.shopping?.mhdModal?.itemId ?? null,
        activeItemId: value?.shopping?.activeItem?.id ?? null,
      },
      recipes: {
        detailOpen: Boolean(value?.recipes?.detailModal?.open),
        detailItemKey: value?.recipes?.detailModal?.item?.recipe_id
          ?? value?.recipes?.detailModal?.item?.title
          ?? null,
        createOpen: Boolean(value?.recipes?.createModal?.open),
        createMethod: value?.recipes?.createModal?.method || 'webscrape',
        apiBasePath: value?.recipes?.apiBasePath || '',
      },
    });
    if (nextSignature === this._renderSignature) return;
    this._renderSignature = nextSignature;
    this._render();
  }

  _render() {
    const snapshot = captureFocusedFormControl(this);
    const model = this._viewModel || {};
    const detail = model.shopping?.detailModal || { open: false };
    const mhd = model.shopping?.mhdModal || { open: false };
    const item = model.shopping?.activeItem || null;
    const recipeDetail = model.recipes?.detailModal || { open: false, item: null };
    const recipeCreate = model.recipes?.createModal || { open: false, method: 'webscrape' };
    const recipeItem = recipeDetail.item || null;
    const recipeImageSource = recipeItem?.picture_url ? toImageSource(recipeItem.picture_url, { size: 'full', apiBasePath: model.recipes?.apiBasePath || '' }) : '';
    const missingProducts = Array.isArray(recipeItem?.missing_products) ? recipeItem.missing_products : [];
    const ingredients = Array.isArray(recipeItem?.ingredients) ? recipeItem.ingredients : [];

    this.innerHTML = `
      <div class="shopping-modal${detail.open ? '' : ' hidden'}">
        <div class="shopping-modal-backdrop" data-action="shopping-close-detail"></div>
        <section class="shopping-modal-content card">
          <button class="shopping-modal-close" type="button" data-action="shopping-close-detail" aria-label="Details schließen">×</button>
          <h3>${escapeHtml(item?.product_name || 'Produktdetails')}</h3>
          <div class="shopping-modal-inline-editor">
            <label for="shopping-item-amount-input-native">Menge</label>
            <input id="shopping-item-amount-input-native" data-field="amount" type="number" min="0.01" step="0.01" value="${escapeHtml(detail.amount || '')}" />
          </div>
          <label for="shopping-item-note-input-native">Notiz</label>
          <textarea id="shopping-item-note-input-native" data-field="note" rows="3" placeholder="Optionale Einkaufsnotiz">${escapeHtml(detail.note || '')}</textarea>
          <div class="shopping-modal-save-row">
            <button class="success-button" type="button" data-action="shopping-save-detail">Speichern</button>
          </div>
          <div class="shopping-details-grid">
            <div><strong>Produkt-ID</strong><span>${escapeHtml(item?.product_id || '-')}</span></div>
            <div><strong>Lagerort</strong><span>${escapeHtml(item?.location_name || '-')}</span></div>
            <div><strong>Im Bestand</strong><span>${escapeHtml(item?.in_stock || '-')}</span></div>
            <div><strong>MHD</strong><span>${escapeHtml(item?.best_before_date || '-')}</span></div>
          </div>
        </section>
      </div>

      <div class="shopping-modal${mhd.open ? '' : ' hidden'}">
        <div class="shopping-modal-backdrop" data-action="shopping-close-mhd"></div>
        <section class="shopping-modal-content card">
          <button class="shopping-modal-close" type="button" data-action="shopping-close-mhd" aria-label="MHD-Auswahl schließen">×</button>
          <h3>MHD auswählen</h3>
          <label for="shopping-item-mhd-native">Haltbarkeitsdatum</label>
          <input id="shopping-item-mhd-native" data-field="mhd" type="date" value="${escapeHtml(mhd.value || '')}" />
          <div class="shopping-modal-save-row">
            <button class="secondary-button" type="button" data-action="shopping-reset-mhd">Zurücksetzen</button>
            <button class="success-button" type="button" data-action="shopping-save-mhd">Speichern</button>
          </div>
        </section>
      </div>

      <div class="shopping-modal${recipeDetail.open ? '' : ' hidden'}">
        <div class="shopping-modal-backdrop" data-action="recipes-close-detail"></div>
        <section class="shopping-modal-content card recipe-modal-content">
          <button class="shopping-modal-close recipe-modal-close" type="button" data-action="recipes-close-detail" aria-label="Rezeptdetails schließen">×</button>
          ${recipeImageSource ? `
            <div class="recipe-modal-image-wrapper" aria-hidden="false">
              <img class="recipe-modal-image" src="${escapeHtml(recipeImageSource)}" alt="${escapeHtml(recipeItem?.title || 'Rezeptbild')}" loading="lazy" />
            </div>
          ` : ''}
          <h3>${escapeHtml(recipeItem?.title || 'Rezeptdetails')}</h3>
          <div class="muted">${escapeHtml(recipeItem?.reason || '')}</div>
          <h4>Zutaten (mit Mengen)</h4>
          <ul class="recipe-modal-list">
            ${ingredients.length
              ? ingredients.map((ingredient) => `<li>${escapeHtml(ingredient)}</li>`).join('')
              : '<li class="muted">Keine Zutatenliste vorhanden.</li>'}
          </ul>
          <h4>Zubereitung</h4>
          <p class="recipe-modal-preparation">${escapeHtml(recipeItem?.preparation || 'Keine Zubereitungsdetails vorhanden.')}</p>
          <h4>Fehlende Produkte</h4>
          <ul class="recipe-modal-list">
            ${missingProducts.length
              ? missingProducts.map((product) => `<li>${escapeHtml(product?.name || String(product || ''))}</li>`).join('')
              : '<li class="muted">Keine fehlenden Produkte.</li>'}
          </ul>
          <button
            class="success-button"
            type="button"
            data-action="recipes-add-missing"
            ${!(recipeItem?.source === 'grocy' && Number.isInteger(recipeItem?.recipe_id)) ? 'disabled' : ''}
          >Alles hinzufügen</button>
        </section>
      </div>

      <div class="shopping-modal${recipeCreate.open ? '' : ' hidden'}">
        <div class="shopping-modal-backdrop" data-action="recipes-close-create"></div>
        <section class="shopping-modal-content card recipe-create-modal-content">
          <button class="shopping-modal-close recipe-modal-close" type="button" data-action="recipes-close-create" aria-label="Rezept hinzufügen schließen">×</button>
          <h3>Rezept hinzufügen</h3>
          <p class="muted">Wähle eine Methode, um ein Rezept schnell anzulegen.</p>
          <div class="recipe-create-methods">
            <button class="ghost-button${recipeCreate.method === 'webscrape' ? ' active' : ''}" type="button" data-action="recipes-set-create-method" data-method="webscrape">WebScrape</button>
            <button class="ghost-button${recipeCreate.method === 'ai' ? ' active' : ''}" type="button" data-action="recipes-set-create-method" data-method="ai">KI</button>
            <button class="ghost-button${recipeCreate.method === 'manual' ? ' active' : ''}" type="button" data-action="recipes-set-create-method" data-method="manual">Manuell</button>
          </div>

          <section class="recipe-create-panel${recipeCreate.method === 'webscrape' ? '' : ' hidden'}">
            <label for="recipe-webscrape-url-native">Webseite / URL</label>
            <input id="recipe-webscrape-url-native" class="ha-control" data-recipe-field="webscrapeUrl" type="url" placeholder="https://example.com/rezept" value="${escapeHtml(recipeCreate.webscrapeUrl || '')}" />
            <p class="muted">Die URL wird für das spätere Scraping inkl. KI-gestützter Attribut-Extraktion vorbereitet.</p>
            <button class="primary-button" type="button" data-action="recipes-submit-create-webscrape">URL übernehmen</button>
          </section>

          <section class="recipe-create-panel${recipeCreate.method === 'ai' ? '' : ' hidden'}">
            <label for="recipe-ai-prompt-native">Rezept-Anfrage für KI</label>
            <textarea id="recipe-ai-prompt-native" class="ha-control" data-recipe-field="aiPrompt" placeholder="z.B. Erstelle ein vegetarisches Pasta-Rezept für 2 Personen...">${escapeHtml(recipeCreate.aiPrompt || '')}</textarea>
            <button class="primary-button" type="button" data-action="recipes-submit-create-ai">KI-Anfrage übernehmen</button>
          </section>

          <section class="recipe-create-panel${recipeCreate.method === 'manual' ? '' : ' hidden'}">
            <label for="recipe-manual-title-native">Rezeptname</label>
            <input id="recipe-manual-title-native" class="ha-control" data-recipe-field="manualTitle" type="text" placeholder="z.B. Schnelle Gemüsesuppe" value="${escapeHtml(recipeCreate.manualTitle || '')}" />
            <label for="recipe-manual-servings-native">Portionen</label>
            <input id="recipe-manual-servings-native" class="ha-control" data-recipe-field="manualServings" type="number" min="1" step="1" value="${escapeHtml(recipeCreate.manualServings || '2')}" />
            <label for="recipe-manual-ingredients-native">Zutaten (eine pro Zeile)</label>
            <textarea id="recipe-manual-ingredients-native" class="ha-control" data-recipe-field="manualIngredients" placeholder="2 Karotten&#10;1 Zwiebel&#10;500 ml Gemüsebrühe">${escapeHtml(recipeCreate.manualIngredients || '')}</textarea>
            <label for="recipe-manual-preparation-native">Zubereitung</label>
            <textarea id="recipe-manual-preparation-native" class="ha-control" data-recipe-field="manualPreparation" placeholder="1) Gemüse schneiden ...">${escapeHtml(recipeCreate.manualPreparation || '')}</textarea>
            <button class="success-button" type="button" data-action="recipes-submit-create-manual">Schnell erfassen</button>
          </section>
        </section>
      </div>
    `;
    restoreFocusedFormControl(this, snapshot);
  }
}

class GrocyAIScannerBridge extends HTMLElement {
  constructor() {
    super();
    this._api = null;
    this._viewModel = { open: false };
    this._domReady = false;
    this._stream = null;
    this._scannerInterval = null;
    this._llavaTimer = null;
    this._llavaAbortController = null;
    this._preferredFocusMode = '';
    this._focusRefreshTimer = null;
    this._selectedDeviceId = '';
    this._knownDevices = [];
    this._lastBarcode = '';
    this._lastBarcodeAt = 0;
    this._lastImageScanAt = 0;
    this._stableCandidate = '';
    this._stableCount = 0;
    this._rotationDegrees = 0;
    this._resultPayload = null;
    this._detectionInFlight = false;
    this._llavaInFlight = false;
    this._scanStartedAt = 0;
    this._lastLightCheckAt = 0;
    this._boundClick = (event) => this._handleClick(event);
    this._boundChange = (event) => this._handleChange(event);
  }

  connectedCallback() {
    if (!this._domReady) {
      this._renderShell();
      this.addEventListener('click', this._boundClick);
      this.addEventListener('change', this._boundChange);
      this._domReady = true;
    }
    this._applyViewModel();
  }

  disconnectedCallback() {
    this.removeEventListener('click', this._boundClick);
    this.removeEventListener('change', this._boundChange);
    this._stopScanner();
    this._domReady = false;
  }

  set api(value) {
    this._api = value;
  }

  set viewModel(value) {
    this._viewModel = value || { open: false };
    this._applyViewModel();
  }

  _renderShell() {
    this.innerHTML = `
      <div class="shopping-modal hidden" data-role="scanner-modal">
        <div class="shopping-modal-backdrop" data-action="shopping-close-scanner"></div>
        <section class="shopping-modal-content card scanner-modal-content">
          <button class="shopping-modal-close" type="button" data-action="shopping-close-scanner" aria-label="Scanner schließen">×</button>
          <div class="scanner-modal-header">
            <div>
              <p class="eyebrow">Nativer Scanner</p>
              <h3>Kamera, Barcode und Bildanalyse</h3>
            </div>
            <span class="migration-chip">Kein Legacy-iframe mehr</span>
          </div>
          <p class="description">
            Barcodes werden direkt im nativen Panel erkannt. Falls kein Barcode gefunden wird, kann derselbe Kamera-Frame über die Bildanalyse an <code>POST /api/v1/scan/image</code> übergeben werden.
          </p>
          <div class="scanner-controls-grid">
            <label>
              <span class="muted">Kamera</span>
              <select data-role="scanner-camera-select"></select>
            </label>
            <label>
              <span class="muted">Rotation</span>
              <select data-role="scanner-rotation-select">
                <option value="0">0°</option>
                <option value="90">90°</option>
                <option value="180">180°</option>
                <option value="270">270°</option>
              </select>
            </label>
          </div>
          <div class="scanner-video-shell">
            <video class="scanner-video hidden" data-role="scanner-video" playsinline autoplay muted></video>
            <div class="scanner-frame-overlay hidden" data-role="scanner-frame-overlay" aria-hidden="true"></div>
            <p class="scanner-light-warning hidden" data-role="scanner-light-warning">Wenig Licht erkannt – bitte Kamera näher ans Produkt halten oder Beleuchtung erhöhen.</p>
          </div>
          <canvas class="hidden" data-role="scanner-canvas"></canvas>
          <pre class="scanner-capabilities-log" data-role="scanner-capabilities-log"></pre>
          <p class="tab-status" data-role="scanner-status" aria-live="polite">Bereit.</p>
          <div class="button-row">
            <button class="primary-button" type="button" data-action="shopping-start-scanner">Scanner starten</button>
            <button class="ghost-button hidden" type="button" data-action="shopping-stop-scanner">Scanner stoppen</button>
            <button class="secondary-button" type="button" data-action="shopping-scan-image">Bild analysieren</button>
            <button class="ghost-button" type="button" data-action="shopping-close-scanner">Schließen</button>
          </div>
          <section class="scanner-result hidden" data-role="scanner-result"></section>
        </section>
      </div>
    `;
  }

  _applyViewModel() {
    if (!this.isConnected || !this._domReady) return;
    const modal = this._getElement('scanner-modal');
    if (!modal) return;

    const shouldOpen = Boolean(this._viewModel?.open);
    modal.dataset.scope = String(this._viewModel?.scope || 'shopping');
    modal.classList.toggle('hidden', !shouldOpen);
    const statusElement = this._getElement('scanner-status');
    if (statusElement) {
      statusElement.textContent = String(this._viewModel?.status || 'Bereit.');
    }

    const rotationSelect = this._getElement('scanner-rotation-select');
    if (rotationSelect && rotationSelect.value !== String(this._rotationDegrees)) {
      rotationSelect.value = String(this._rotationDegrees);
    }

    if (shouldOpen) {
      void this._refreshDevices();
      if (!this._stream) {
        void this._startScanner();
      }
      return;
    }

    this._stopScanner();
  }

  _getElement(role) {
    return this.querySelector(`[data-role="${role}"]`);
  }

  _handleClick(event) {
    const actionTarget = event.target.closest('[data-action]');
    if (!actionTarget) return;

    switch (actionTarget.dataset.action) {
      case 'shopping-close-scanner':
        this.dispatchEvent(new CustomEvent('shopping-close-scanner', { bubbles: true, composed: true }));
        break;
      case 'shopping-start-scanner':
        void this._startScanner();
        break;
      case 'shopping-stop-scanner':
        this._stopScanner();
        break;
      case 'shopping-scan-image':
        void this._scanCurrentFrame('manual');
        break;
      default:
        break;
    }
  }

  _handleChange(event) {
    if (event.target.matches('[data-role="scanner-camera-select"]')) {
      this._selectedDeviceId = event.target.value || '';
      if (this._stream) {
        void this._startScanner();
      }
      return;
    }

    if (event.target.matches('[data-role="scanner-rotation-select"]')) {
      this._rotationDegrees = this._parseRotationDegrees(event.target.value);
      this._applyVideoRotation();
    }
  }

  _setStatus(message) {
    const element = this._getElement('scanner-status');
    if (element) element.textContent = String(message || 'Bereit.');
    this.dispatchEvent(new CustomEvent('shopping-scanner-status', {
      bubbles: true,
      composed: true,
      detail: { message: String(message || 'Bereit.') },
    }));
  }

  _renderResult(payload) {
    const result = this._getElement('scanner-result');
    if (!result) return;

    if (!payload) {
      this._resultPayload = null;
      result.classList.add('hidden');
      result.innerHTML = '';
      return;
    }

    this._resultPayload = payload;
    result.classList.remove('hidden');
    result.innerHTML = `
      <div class="scanner-result-card">
        <div class="scanner-result-card__header">
          <div>
            <p class="eyebrow">Erkanntes Produkt</p>
            <h3>${escapeHtml(payload.product_name || 'Unbekanntes Produkt')}</h3>
          </div>
          <span class="search-state-chip search-state-chip--suggestions">${escapeHtml(payload.source || 'scanner')}</span>
        </div>
        <div class="shopping-details-grid">
          <div><strong>Barcode</strong><span>${escapeHtml(payload.barcode || '-')}</span></div>
          <div><strong>Marke</strong><span>${escapeHtml(payload.brand || '-')}</span></div>
          <div><strong>Menge</strong><span>${escapeHtml(payload.quantity || payload.hint || '1')}</span></div>
          <div><strong>Hinweis</strong><span>${escapeHtml(payload.hint || payload.ingredients_text || '-')}</span></div>
        </div>
        <p class="muted">Das erkannte Produkt wird direkt in denselben nativen Such-/Varianten-/Add-to-list-Flow übergeben wie eine manuelle Texteingabe.</p>
      </div>
    `;
  }

  async _refreshDevices() {
    const select = this._getElement('scanner-camera-select');
    if (!select || !navigator.mediaDevices?.enumerateDevices) return;

    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      this._knownDevices = devices.filter((device) => device.kind === 'videoinput');
      select.innerHTML = [
        '<option value="">Automatisch (Rückkamera)</option>',
        ...this._knownDevices.map((device, index) => {
          const label = device.label || `Kamera ${index + 1}`;
          const selected = this._selectedDeviceId === device.deviceId ? ' selected' : '';
          return `<option value="${escapeHtml(device.deviceId)}"${selected}>${escapeHtml(label)}</option>`;
        }),
      ].join('');
      select.value = this._selectedDeviceId || '';
    } catch (error) {
      this._setStatus(`Kameras konnten nicht geladen werden: ${error.message}`);
    }
  }

  _parseRotationDegrees(value) {
    const rotation = Number(value);
    return [0, 90, 180, 270].includes(rotation) ? rotation : 0;
  }

  _applyVideoRotation() {
    const video = this._getElement('scanner-video');
    if (!video) return;
    video.classList.remove('rotated-90', 'rotated-180', 'rotated-270');
    if (this._rotationDegrees === 90) video.classList.add('rotated-90');
    if (this._rotationDegrees === 180) video.classList.add('rotated-180');
    if (this._rotationDegrees === 270) video.classList.add('rotated-270');
  }

  _setLightWarningVisible(visible) {
    this._getElement('scanner-light-warning')?.classList.toggle('hidden', !visible);
  }

  _setCapabilitiesLog(capabilities, settings) {
    const element = this._getElement('scanner-capabilities-log');
    if (!element) return;
    element.textContent = JSON.stringify({
      selected_device_id: this._selectedDeviceId || null,
      capabilities: capabilities || null,
      settings: settings || null,
    }, null, 2);
  }

  _normalizeBarcodeForLookup(barcode) {
    const digitsOnly = String(barcode || '').replace(/\D/g, '');
    if (!digitsOnly) return '';
    if (digitsOnly.length >= 16 && digitsOnly.startsWith('01')) {
      const gtin14 = digitsOnly.slice(2, 16);
      return gtin14.startsWith('0') ? gtin14.slice(1) : gtin14;
    }
    if ([8, 12, 13, 14].includes(digitsOnly.length)) return digitsOnly;
    if (digitsOnly.length > 14) return digitsOnly.slice(-13);
    return digitsOnly;
  }

  _registerScannerCandidate(rawBarcode) {
    const normalized = this._normalizeBarcodeForLookup(rawBarcode);
    if (!normalized || normalized.length < 8) return '';
    if (normalized === this._lastBarcode) {
      this._stableCandidate = normalized;
      this._stableCount = 2;
      return '';
    }
    if (normalized === this._stableCandidate) {
      this._stableCount += 1;
    } else {
      this._stableCandidate = normalized;
      this._stableCount = 1;
    }
    if (this._stableCount < 2) return '';
    this._stableCandidate = '';
    this._stableCount = 0;
    return normalized;
  }

  async _startScanner() {
    const startButton = this.querySelector('[data-action="shopping-start-scanner"]');
    const stopButton = this.querySelector('[data-action="shopping-stop-scanner"]');
    const video = this._getElement('scanner-video');
    if (!video) return;

    if (!navigator.mediaDevices?.getUserMedia) {
      this._setStatus('Kamera wird in diesem Browser/WebView nicht unterstützt.');
      return;
    }

    this._stopScanner({ keepStatus: true });
    this._setStatus('Scanner startet…');

    try {
      this._stream = await this._getCompatibleScannerStream();
      await this._refreshDevices();
      await this._optimizeScannerTrack(this._stream);
      this._scheduleScannerFocusRefresh(this._stream);
      video.srcObject = this._stream;
      await video.play();
      video.classList.remove('hidden');
      this._applyVideoRotation();
      this._getElement('scanner-frame-overlay')?.classList.remove('hidden');
      startButton?.classList.add('hidden');
      stopButton?.classList.remove('hidden');
      this._setStatus('Scanner aktiv. Barcode vor die Kamera halten oder Bildanalyse starten.');
      this._scanStartedAt = Date.now();
      this._lastBarcodeAt = Date.now();
      this._lastLightCheckAt = 0;
      this._setLightWarningVisible(false);
      this._scheduleLlavaFallback();
      this._startBarcodeLoop(video);
    } catch (error) {
      const name = String(error?.name || '');
      if (!window.isSecureContext) {
        this._setStatus('Kamerazugriff benötigt eine sichere Verbindung (HTTPS/Home-Assistant-App).');
      } else if (name === 'NotAllowedError' || name === 'SecurityError') {
        this._setStatus('Kamera-Berechtigung wurde verweigert.');
      } else if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
        this._setStatus('Keine Kamera gefunden.');
      } else {
        this._setStatus(`Kamera konnte nicht gestartet werden: ${error.message}`);
      }
    }
  }

  _startBarcodeLoop(video) {
    const canvas = this._getElement('scanner-canvas');
    const detector = 'BarcodeDetector' in window
      ? new window.BarcodeDetector({ formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e'] })
      : null;

    this._scannerInterval = window.setInterval(async () => {
      if (!this._stream || !video.videoWidth || !video.videoHeight || !this._viewModel?.open) return;
      this._evaluateScannerLight(video, canvas);
      if (Date.now() - this._scanStartedAt < 1200) return;
      if (!detector || this._detectionInFlight) return;

      try {
        const source = this._getScannerDetectionSource(video, canvas, 1.35);
        const barcodes = await detector.detect(source);
        if (!barcodes.length) return;
        const stableBarcode = this._registerScannerCandidate(String(barcodes[0].rawValue || '').trim());
        if (!stableBarcode) return;
        this._detectionInFlight = true;
        try {
          await this._lookupBarcode(stableBarcode);
        } finally {
          this._detectionInFlight = false;
        }
      } catch (_) {
        // Ignore detector errors and keep scanning.
      }
    }, 900);
  }

  async _lookupBarcode(barcode) {
    if (!this._api) {
      this._setStatus('Scanner-API ist noch nicht initialisiert.');
      return;
    }

    const normalized = this._normalizeBarcodeForLookup(barcode);
    if (normalized.length < 8) return;

    this._lastBarcode = normalized;
    this._lastBarcodeAt = Date.now();
    this._setStatus(`Barcode erkannt: ${normalized}. Lade Produktdaten…`);

    const { response, payload } = await this._api.lookupBarcode(normalized);
    if (!response.ok) {
      this._setStatus(getErrorMessage(payload, 'Barcode konnte nicht abgefragt werden.'));
      return;
    }

    if (!payload?.found) {
      this._renderResult(null);
      this._setStatus(`Kein Produkt für Barcode ${normalized} gefunden.`);
      return;
    }

    const resultPayload = {
      ...payload,
      hint: payload.quantity || '',
    };
    this._renderResult(resultPayload);
    this._setStatus(`Produkt erkannt: ${payload.product_name || normalized}. Übergabe an Einkaufsflow…`);
    this._emitScannerDetection(resultPayload);
  }

  _emitScannerDetection(payload) {
    const productName = String(payload?.product_name || '').trim();
    if (!productName) return;
    const detail = {
      productName,
      amount: 1,
      source: payload?.source || 'scanner',
      barcode: payload?.barcode || '',
      payload,
    };
    this.dispatchEvent(new CustomEvent('shopping-scanner-detected', {
      bubbles: true,
      composed: true,
      detail,
    }));
  }

  _captureFrameBase64() {
    const video = this._getElement('scanner-video');
    const canvas = this._getElement('scanner-canvas');
    if (!video || !canvas || !video.videoWidth || !video.videoHeight) return '';

    const context = canvas.getContext('2d', { willReadFrequently: true });
    if (!context) return '';

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    return String(canvas.toDataURL('image/jpeg', 0.9)).replace(/^data:image\/\w+;base64,/, '');
  }

  _scheduleLlavaFallback() {
    if (this._llavaTimer) window.clearTimeout(this._llavaTimer);
    this._llavaTimer = window.setTimeout(() => {
      if (!this._viewModel?.open || !this._stream) return;
      const elapsed = Date.now() - this._lastBarcodeAt;
      const cooldownElapsed = Date.now() - this._lastImageScanAt;
      if (elapsed >= 5000 && cooldownElapsed >= 15000) {
        void this._scanCurrentFrame('timeout');
      }
      this._scheduleLlavaFallback();
    }, 5000);
  }

  async _scanCurrentFrame(reason = 'manual') {
    if (!this._api) {
      this._setStatus('Scanner-API ist noch nicht initialisiert.');
      return;
    }
    if (this._llavaInFlight) return;

    const imageBase64 = this._captureFrameBase64();
    if (!imageBase64) {
      this._setStatus('Kein Kamerabild für die Bildanalyse verfügbar.');
      return;
    }

    this._llavaAbortController?.abort();
    this._llavaAbortController = new AbortController();
    this._llavaInFlight = true;
    this._lastImageScanAt = Date.now();
    this._setStatus(reason === 'timeout'
      ? 'Kein Barcode gefunden. Starte Bildanalyse…'
      : 'Analysiere aktuelles Kamerabild…');

    const timeoutHandle = window.setTimeout(() => this._llavaAbortController?.abort(), 45000);
    try {
      const { response, payload } = await this._api.scanImage(imageBase64, {
        signal: this._llavaAbortController.signal,
      });
      if (!response.ok) {
        this._setStatus(getErrorMessage(payload, 'Bildanalyse konnte nicht ausgeführt werden.'));
        return;
      }
      if (!payload?.success || !payload?.product_name) {
        this._renderResult(null);
        this._setStatus('Die Bildanalyse hat kein eindeutiges Produkt erkannt.');
        return;
      }

      const resultPayload = {
        found: true,
        barcode: '',
        product_name: payload.product_name,
        brand: payload.brand || '',
        quantity: payload.hint || '1',
        ingredients_text: payload.hint || '',
        hint: payload.hint || '',
        source: payload.source || 'ollama_llava',
      };
      this._renderResult(resultPayload);
      this._setStatus(`Bildanalyse erkannt: ${payload.product_name}. Übergabe an Einkaufsflow…`);
      this._emitScannerDetection(resultPayload);
    } catch (error) {
      if (error?.name === 'AbortError') {
        this._setStatus('Bildanalyse wurde wegen Zeitüberschreitung beendet.');
      } else {
        this._setStatus(`Bildanalyse fehlgeschlagen: ${error.message}`);
      }
    } finally {
      window.clearTimeout(timeoutHandle);
      this._llavaInFlight = false;
    }
  }

  _evaluateScannerLight(video, canvas) {
    if (!video?.videoWidth || !video?.videoHeight || !canvas) return;
    const now = Date.now();
    if ((now - this._lastLightCheckAt) < 1500) return;
    this._lastLightCheckAt = now;

    const context = canvas.getContext('2d', { willReadFrequently: true });
    if (!context) return;

    canvas.width = 64;
    canvas.height = 36;
    context.drawImage(video, 0, 0, 64, 36);
    const pixels = context.getImageData(0, 0, 64, 36).data;
    let brightnessTotal = 0;
    for (let index = 0; index < pixels.length; index += 4) {
      brightnessTotal += (pixels[index] + pixels[index + 1] + pixels[index + 2]) / 3;
    }

    const averageBrightness = brightnessTotal / (pixels.length / 4);
    this._setLightWarningVisible(averageBrightness < 72);
  }

  _getScannerDetectionSource(video, canvas, zoomFactor) {
    if (!canvas || !video || !video.videoWidth || !video.videoHeight || zoomFactor <= 1) {
      return video;
    }

    const context = canvas.getContext('2d', { willReadFrequently: true });
    if (!context) return video;

    const frameRatioWidth = 0.72;
    const frameRatioHeight = 0.38;
    const sourceWidth = Math.round((video.videoWidth * frameRatioWidth) / zoomFactor);
    const sourceHeight = Math.round((video.videoHeight * frameRatioHeight) / zoomFactor);
    const sourceX = Math.max(0, Math.round((video.videoWidth - sourceWidth) / 2));
    const sourceY = Math.max(0, Math.round((video.videoHeight - sourceHeight) / 2));
    const autoPortraitQuarterTurn = this._rotationDegrees === 0 && sourceHeight > sourceWidth;
    const rotation = autoPortraitQuarterTurn ? 90 : this._rotationDegrees;
    const isQuarterTurn = rotation === 90 || rotation === 270;

    canvas.width = isQuarterTurn ? sourceHeight : sourceWidth;
    canvas.height = isQuarterTurn ? sourceWidth : sourceHeight;
    context.save();
    context.clearRect(0, 0, canvas.width, canvas.height);

    if (rotation === 90) {
      context.translate(canvas.width, 0);
      context.rotate(Math.PI / 2);
    } else if (rotation === 180) {
      context.translate(canvas.width, canvas.height);
      context.rotate(Math.PI);
    } else if (rotation === 270) {
      context.translate(0, canvas.height);
      context.rotate(-Math.PI / 2);
    }

    context.drawImage(video, sourceX, sourceY, sourceWidth, sourceHeight, 0, 0, sourceWidth, sourceHeight);
    context.restore();
    return canvas;
  }

  async _getCompatibleScannerStream() {
    const selectedDeviceConstraint = this._selectedDeviceId
      ? { deviceId: { exact: this._selectedDeviceId } }
      : { facingMode: { exact: 'environment' } };
    const fallbackFacingConstraint = this._selectedDeviceId
      ? { deviceId: { exact: this._selectedDeviceId } }
      : { facingMode: { ideal: 'environment' } };

    const streamProfiles = [
      { video: { ...selectedDeviceConstraint, width: { ideal: 2560 }, height: { ideal: 1440 } }, audio: false },
      { video: { ...fallbackFacingConstraint, width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false },
      { video: { ...fallbackFacingConstraint, width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false },
      { video: this._selectedDeviceId ? { deviceId: { exact: this._selectedDeviceId } } : { facingMode: 'environment' }, audio: false },
      { video: true, audio: false },
    ];

    let lastError = null;
    for (const constraints of streamProfiles) {
      try {
        return await navigator.mediaDevices.getUserMedia(constraints);
      } catch (error) {
        lastError = error;
      }
    }
    throw lastError || new Error('Kamera konnte nicht initialisiert werden.');
  }

  async _optimizeScannerTrack(stream) {
    const videoTrack = stream?.getVideoTracks?.()[0];
    if (!videoTrack) return;
    const capabilities = videoTrack.getCapabilities ? videoTrack.getCapabilities() : null;
    const settings = videoTrack.getSettings ? videoTrack.getSettings() : null;
    this._setCapabilitiesLog(capabilities, settings);

    const constraints = {};
    if (capabilities?.focusMode?.includes('continuous')) {
      constraints.focusMode = 'continuous';
    } else if (capabilities?.focusMode?.includes('single-shot')) {
      constraints.focusMode = 'single-shot';
    } else if (capabilities?.focusMode?.includes('manual')) {
      constraints.focusMode = 'manual';
    }
    this._preferredFocusMode = constraints.focusMode || '';

    if (capabilities?.zoom) {
      const minZoom = Number(capabilities.zoom.min || 1);
      const maxZoom = Number(capabilities.zoom.max || minZoom);
      constraints.zoom = Math.max(minZoom, Math.min(maxZoom, 1.4));
    }

    if (!Object.keys(constraints).length || typeof videoTrack.applyConstraints !== 'function') return;
    try {
      await videoTrack.applyConstraints({ advanced: [constraints] });
    } catch (_) {
      // Keep default stream settings if optimizations are unsupported.
    }
  }

  _scheduleScannerFocusRefresh(stream) {
    if (this._focusRefreshTimer) window.clearInterval(this._focusRefreshTimer);
    if (!stream || !['single-shot', 'continuous'].includes(this._preferredFocusMode)) return;

    const videoTrack = stream.getVideoTracks?.()[0];
    if (!videoTrack || typeof videoTrack.applyConstraints !== 'function') return;

    this._focusRefreshTimer = window.setInterval(() => {
      if (!this._stream || !this._viewModel?.open) return;
      videoTrack.applyConstraints({ advanced: [{ focusMode: this._preferredFocusMode }] }).catch(() => {});
    }, 2000);
  }

  _stopScanner(options = {}) {
    if (this._scannerInterval) {
      window.clearInterval(this._scannerInterval);
      this._scannerInterval = null;
    }
    if (this._llavaTimer) {
      window.clearTimeout(this._llavaTimer);
      this._llavaTimer = null;
    }
    if (this._focusRefreshTimer) {
      window.clearInterval(this._focusRefreshTimer);
      this._focusRefreshTimer = null;
    }

    this._llavaAbortController?.abort();
    this._llavaAbortController = null;
    this._preferredFocusMode = '';
    this._llavaInFlight = false;
    this._detectionInFlight = false;
    this._stableCandidate = '';
    this._stableCount = 0;
    this._lastBarcode = '';

    if (this._stream) {
      this._stream.getTracks().forEach((track) => track.stop());
      this._stream = null;
    }

    const video = this._getElement('scanner-video');
    if (video) {
      video.pause();
      video.srcObject = null;
      video.classList.add('hidden');
      video.classList.remove('rotated-90', 'rotated-180', 'rotated-270');
    }

    this._getElement('scanner-frame-overlay')?.classList.add('hidden');
    this._setLightWarningVisible(false);
    this.querySelector('[data-action="shopping-start-scanner"]')?.classList.remove('hidden');
    this.querySelector('[data-action="shopping-stop-scanner"]')?.classList.add('hidden');

    if (!options.keepStatus && this._viewModel?.open) {
      this._setStatus('Scanner gestoppt.');
    }
  }
}

class GrocyAIRecipesTab extends HTMLElement {
  constructor() {
    super();
    this._renderSignature = null;
  }

  connectedCallback() {
    if (this._bound) return;
    this._bound = true;
    this.addEventListener('click', (event) => {
      const actionTarget = event.target.closest('[data-action]');
      if (!actionTarget) return;
      const detail = { ...actionTarget.dataset };

      if (actionTarget.dataset.recipeItem) {
        try {
          detail.item = JSON.parse(decodeURIComponent(actionTarget.dataset.recipeItem));
        } catch (_) {
          detail.item = null;
        }
      }

      this.dispatchEvent(new CustomEvent(actionTarget.dataset.action, {
        bubbles: true,
        composed: true,
        detail,
      }));
    });

    this.addEventListener('change', (event) => {
      const target = event.target;
      if (!(target instanceof HTMLInputElement)) return;

      if (target.dataset.role === 'recipes-location') {
        this.dispatchEvent(new CustomEvent('recipes-location-selection-change', {
          bubbles: true,
          composed: true,
          detail: {
            locationIds: Array.from(this.querySelectorAll('input[data-role="recipes-location"]:checked'))
              .map((checkbox) => Number(checkbox.value))
              .filter((value) => Number.isFinite(value) && value > 0),
          },
        }));
      }

      if (target.dataset.role === 'recipes-product') {
        this.dispatchEvent(new CustomEvent('recipes-product-selection-change', {
          bubbles: true,
          composed: true,
          detail: {
            productIds: Array.from(this.querySelectorAll('input[data-role="recipes-product"]:checked'))
              .map((checkbox) => Number(checkbox.value))
              .filter((value) => Number.isFinite(value) && value > 0),
          },
        }));
      }

      if (target.dataset.role === 'recipes-expiring-days') {
        this.dispatchEvent(new CustomEvent('recipes-expiring-days-change', {
          bubbles: true,
          composed: true,
          detail: {
            value: target.value,
          },
        }));
      }
    });
  }

  _render() {
    const snapshot = captureFocusedFormControl(this);
    const openDetails = captureDetailsOpenState(this);
    const model = this._viewModel || {};
    this.innerHTML = `
      <section
        id="${getTabPanelId('recipes')}"
        class="tab-view${model.active ? '' : ' hidden'}"
        role="tabpanel"
        aria-labelledby="${getTabButtonId('recipes')}"
        aria-hidden="${model.active ? 'false' : 'true'}"
        ${model.active ? 'tabindex="0"' : 'tabindex="-1" hidden'}
      >
        ${buildRecipesTabMarkup(model)}
      </section>
    `;
    restoreDetailsOpenState(this, openDetails);
    restoreFocusedFormControl(this, snapshot);
  }

  set viewModel(value) {
    this._viewModel = value;
    const nextSignature = JSON.stringify({
      active: Boolean(value?.active),
      status: value?.status || '',
      apiBasePath: value?.apiBasePath || '',
      grocyRecipes: (Array.isArray(value?.grocyRecipes) ? value.grocyRecipes : []).map((item) => ({
        recipe_id: item?.recipe_id ?? null,
        title: item?.title || '',
        reason: item?.reason || '',
        picture_url: item?.picture_url || '',
        source: item?.source || '',
      })),
      aiRecipes: (Array.isArray(value?.aiRecipes) ? value.aiRecipes : []).map((item) => ({
        recipe_id: item?.recipe_id ?? null,
        title: item?.title || '',
        reason: item?.reason || '',
        picture_url: item?.picture_url || '',
        source: item?.source || '',
      })),
      locations: (Array.isArray(value?.locations) ? value.locations : []).map((item) => ({
        id: item?.id ?? null,
        name: item?.name || '',
      })),
      stockProducts: buildStockSignature(Array.isArray(value?.stockProducts) ? value.stockProducts : []),
    });
    if (nextSignature === this._renderSignature) return;
    this._renderSignature = nextSignature;
    this._render();
  }
}

class GrocyAIStorageTab extends HTMLElement {
  constructor() {
    super();
    this._renderSignature = null;
    this._cleanupSwipe = null;
  }

  connectedCallback() {
    if (this._bound) return;
    this._bound = true;
    this.addEventListener('click', (event) => {
      const actionTarget = event.target.closest('[data-action]');
      if (!actionTarget) return;
      this.dispatchEvent(new CustomEvent(actionTarget.dataset.action, {
        bubbles: true,
        composed: true,
        detail: { ...actionTarget.dataset },
      }));
    });
    this.addEventListener('input', (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;

      if (target.dataset.role === 'storage-filter') {
        this.dispatchEvent(new CustomEvent('storage-filter-change', {
          bubbles: true,
          composed: true,
          detail: { value: target.value },
        }));
      }

      if (target.dataset.role === 'storage-edit-field') {
        this.dispatchEvent(new CustomEvent('storage-edit-input', {
          bubbles: true,
          composed: true,
          detail: { field: target.dataset.field, value: target.value },
        }));
      }

      if (target.dataset.role === 'storage-consume-field') {
        this.dispatchEvent(new CustomEvent('storage-consume-input', {
          bubbles: true,
          composed: true,
          detail: { field: target.dataset.field, value: target.value },
        }));
      }
    });
    this.addEventListener('change', (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;

      if (target.dataset.role === 'storage-include-all') {
        this.dispatchEvent(new CustomEvent('storage-toggle-include-all', {
          bubbles: true,
          composed: true,
          detail: { checked: Boolean(target.checked) },
        }));
      }

      if (target.dataset.role === 'storage-edit-field') {
        this.dispatchEvent(new CustomEvent('storage-edit-input', {
          bubbles: true,
          composed: true,
          detail: { field: target.dataset.field, value: target.value },
        }));
      }
    });
  }

  disconnectedCallback() {
    this._cleanupSwipe?.();
    this._cleanupSwipe = null;
  }

  _rebindSwipeInteractions() {
    this._cleanupSwipe?.();
    this._cleanupSwipe = bindSwipeInteractions({
      root: this,
      selector: '.storage-item.swipe-item',
      getPayload: (item) => ({
        itemId: item.dataset.itemId,
        inStock: item.dataset.inStock === 'true',
      }),
      onTap: (_, payload) => {
        if (!payload.itemId) return;
        this.dispatchEvent(new CustomEvent('storage-open-edit', {
          bubbles: true,
          composed: true,
          detail: { itemId: payload.itemId },
        }));
      },
      onSwipeLeft: async (_, payload) => {
        if (!payload.itemId) return;
        const actionName = payload.inStock ? 'storage-open-consume' : 'storage-open-edit';
        this.dispatchEvent(new CustomEvent(actionName, {
          bubbles: true,
          composed: true,
          detail: { itemId: payload.itemId },
        }));
      },
      onSwipeRight: async (_, payload) => {
        if (!payload.itemId) return;
        this.dispatchEvent(new CustomEvent('storage-open-edit', {
          bubbles: true,
          composed: true,
          detail: { itemId: payload.itemId },
        }));
      },
    });
  }

  _render() {
    const snapshot = captureFocusedFormControl(this);
    const model = this._viewModel || {};
    this.innerHTML = `
      <section
        id="${getTabPanelId('storage')}"
        class="tab-view${model.active ? '' : ' hidden'}"
        role="tabpanel"
        aria-labelledby="${getTabButtonId('storage')}"
        aria-hidden="${model.active ? 'false' : 'true'}"
        ${model.active ? 'tabindex="0"' : 'tabindex="-1" hidden'}
      >
        ${buildStorageTabMarkup(model)}
      </section>
    `;

    bindShoppingImageFallbacks(this);
    restoreFocusedFormControl(this, snapshot);
    this._rebindSwipeInteractions();
  }

  _syncVolatileState() {
    if (!this.isConnected) return;

    const model = this._viewModel || {};
    const editFieldValues = {
      amount: model?.editModal?.amount || '',
      bestBeforeDate: model?.editModal?.bestBeforeDate || '',
      locationId: model?.editModal?.locationId || '',
      calories: model?.editModal?.calories || '',
      carbs: model?.editModal?.carbs || '',
      fat: model?.editModal?.fat || '',
      protein: model?.editModal?.protein || '',
      sugar: model?.editModal?.sugar || '',
    };

    Object.entries(editFieldValues).forEach(([field, value]) => {
      const input = this.querySelector(`[data-role="storage-edit-field"][data-field="${field}"]`);
      if (input && input.value !== String(value)) {
        input.value = String(value);
      }
    });

    const consumeInput = this.querySelector('[data-role="storage-consume-field"][data-field="amount"]');
    if (consumeInput && consumeInput.value !== String(model?.consumeModal?.amount || '1')) {
      consumeInput.value = String(model?.consumeModal?.amount || '1');
    }
  }

  set viewModel(value) {
    this._viewModel = value;
    const nextSignature = JSON.stringify({
      active: Boolean(value?.active),
      loading: Boolean(value?.loading),
      status: value?.status || '',
      items: (Array.isArray(value?.items) ? value.items : []).map((item) => ({
        id: item?.id ?? null,
        stock_id: item?.stock_id ?? null,
        name: item?.name || '',
        amount: item?.amount ?? null,
        best_before_date: item?.best_before_date || '',
        location_id: item?.location_id ?? null,
        location_name: item?.location_name || '',
        in_stock: Boolean(item?.in_stock),
      })),
      locations: (Array.isArray(value?.locations) ? value.locations : []).map((item) => ({
        id: item?.id ?? null,
        name: item?.name || '',
      })),
      editModal: {
        open: Boolean(value?.editModal?.open),
        itemId: value?.editModal?.itemId ?? null,
      },
      consumeModal: {
        open: Boolean(value?.consumeModal?.open),
        itemId: value?.consumeModal?.itemId ?? null,
      },
      deleteModal: {
        open: Boolean(value?.deleteModal?.open),
        itemId: value?.deleteModal?.itemId ?? null,
      },
    });
    if (nextSignature === this._renderSignature) {
      this._syncVolatileState();
      return;
    }
    this._renderSignature = nextSignature;
    this._render();
  }
}

class GrocyAINotificationsTab extends GrocyAILegacyBridgeTab {}

class GrocyAIDashboardPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._hass = null;
    this._route = null;
    this._panel = null;
    this._narrow = false;
    this._unsubscribe = null;
    this._searchUnsubscribe = null;
    this._shoppingPollIntervalMs = DEFAULT_POLLING_INTERVAL_MS;
    this._dashboardApiBasePath = '';
    this._initialDataLoadStarted = false;
    this._apiBasePathPromise = null;
    this._startupBannerLogged = false;
    this._scrollLockState = null;
    this._shellLayoutObserver = null;
    this._handleWindowResize = () => this._syncShellLayoutMetrics();
    this._store = createDashboardStore(createInitialState());
    this._api = createDashboardApiClient({ getAuthHeaders: () => this._getHomeAssistantAuthHeaders() });
    this._handlePopState = () => this._syncActiveTabFromLocation({ updateUrl: false });
    this._handleVisibilityChange = () => this._handleDocumentVisibilityChange();
    this._shoppingSearch = createShoppingSearchController({
      api: this._api,
      onShoppingListChanged: async () => {
        await this._loadShoppingList({ silent: true });
      },
    });
  }

  connectedCallback() {
    this._ensureShell();
    if (!this.shadowRoot) return;

    this._bindEvents();
    window.addEventListener('popstate', this._handlePopState);
    window.addEventListener('resize', this._handleWindowResize);
    document.addEventListener('visibilitychange', this._handleVisibilityChange);
    this._observeShellLayout();
    this._unsubscribe = this._store.subscribe((state) => this._renderState(state));
    this._applyRouteState({ syncHistory: false, announce: false });
    this._syncActiveTabFromLocation({ replaceUrl: true });
    this._searchUnsubscribe = this._shoppingSearch.subscribe(() => this._renderState(this._store.getState()));
    this._ensureInitialDataLoad();
    this._logStartupBanner();
  }

  disconnectedCallback() {
    this._unsubscribe?.();
    window.removeEventListener('popstate', this._handlePopState);
    window.removeEventListener('resize', this._handleWindowResize);
    document.removeEventListener('visibilitychange', this._handleVisibilityChange);
    this._shellLayoutObserver?.disconnect();
    this._shellLayoutObserver = null;
    this._searchUnsubscribe?.();
    this._shoppingSearch.dispose();
    window.clearTimeout(this._storageFilterDebounce);
    this._stopShoppingPolling();
    this._setModalScrollLock(false);
  }

  set hass(value) {
    this._hass = value;
    this._shoppingPollIntervalMs = this._resolveShoppingPollingInterval();
    this._syncShoppingPolling();
    void this._ensureDashboardApiClient();
    this._renderState(this._store.getState());
    this._ensureInitialDataLoad();
  }

  set route(value) {
    this._route = value;
    this._applyRouteState({ syncHistory: false, announce: false });
    this._syncActiveTabFromLocation({ replaceUrl: true });
    this._renderState(this._store.getState());
  }

  set panel(value) {
    this._panel = value;
    void this._ensureDashboardApiClient({ forceRefresh: true });
    this._renderState(this._store.getState());
  }

  set narrow(value) {
    this._narrow = Boolean(value);
    this._renderState(this._store.getState());
  }

  async _ensureDashboardApiClient(options = {}) {
    const { forceRefresh = false } = options;
    if (!forceRefresh && this._dashboardApiBasePath) return this._dashboardApiBasePath;
    if (this._apiBasePathPromise && !forceRefresh) return this._apiBasePathPromise;

    this._apiBasePathPromise = (async () => {
      const nextBasePath = await resolveDashboardApiBasePath({
        panelConfig: this._getPanelConfig(),
        hass: this._hass,
        location: window.location,
      });
      if (nextBasePath && nextBasePath !== this._dashboardApiBasePath) {
        this._dashboardApiBasePath = nextBasePath;
        this._api = createDashboardApiClient({
          apiBasePath: nextBasePath,
          getAuthHeaders: () => this._getHomeAssistantAuthHeaders(),
        });
        this._shoppingSearch.setApi(this._api);
        this._renderState(this._store.getState());
      }
      return this._dashboardApiBasePath;
    })();

    try {
      return await this._apiBasePathPromise;
    } finally {
      this._apiBasePathPromise = null;
    }
  }

  async _getDashboardApiOrThrow() {
    const apiBasePath = await this._ensureDashboardApiClient();
    if (!apiBasePath) {
      throw new Error('Dashboard-Ingress konnte nicht initialisiert werden.');
    }
    return this._api;
  }

  _ensureInitialDataLoad() {
    if (this._initialDataLoadStarted || !this.isConnected || !this._hass) return;
    this._initialDataLoadStarted = true;
    void this._loadShoppingList();
  }

  _logStartupBanner() {
    if (this._startupBannerLogged) return;

    const version = this._getPanelConfig().integration_version || DEFAULT_INTEGRATION_VERSION;
    logIntegrationStartupBanner(version);
    this._startupBannerLogged = true;
  }

  _ensureShell() {
    if (!this.shadowRoot || this.shadowRoot.querySelector('grocy-ai-topbar')) return;

    this.shadowRoot.innerHTML = `
      <link rel="stylesheet" href="${STYLE_URL.href}">
      <section class="page-shell">
        <grocy-ai-topbar></grocy-ai-topbar>
        <section class="dashboard-content">
          <grocy-ai-shopping-tab></grocy-ai-shopping-tab>
          <grocy-ai-recipes-tab></grocy-ai-recipes-tab>
          <grocy-ai-storage-tab></grocy-ai-storage-tab>
          <grocy-ai-notifications-tab></grocy-ai-notifications-tab>
        </section>
        <grocy-ai-dashboard-modals></grocy-ai-dashboard-modals>
        <grocy-ai-scanner-bridge></grocy-ai-scanner-bridge>
        <grocy-ai-tab-nav></grocy-ai-tab-nav>
      </section>
    `;
  }

  _observeShellLayout() {
    const shell = this.shadowRoot?.querySelector('.page-shell');
    if (!shell) return;

    if (!this._shellLayoutObserver && typeof ResizeObserver !== 'undefined') {
      this._shellLayoutObserver = new ResizeObserver(() => this._syncShellLayoutMetrics());
    }

    this._shellLayoutObserver?.disconnect();
    this._shellLayoutObserver?.observe(shell);
    this._syncShellLayoutMetrics();
  }

  _syncShellLayoutMetrics() {
    const shell = this.shadowRoot?.querySelector('.page-shell');
    if (!shell) return;

    const shellRect = shell.getBoundingClientRect();
    if (!shellRect.width) return;

    this.style.setProperty('--dashboard-shell-center-x', `${shellRect.left + (shellRect.width / 2)}px`);
    this.style.setProperty('--dashboard-shell-fixed-width', `${shellRect.width}px`);
  }

  _bindEvents() {
    const root = this.shadowRoot;
    if (!root) return;

    root.addEventListener('tab-change', (event) => this._switchTab(event.detail.tab));
    root.addEventListener('shopping-query-change', (event) => this._updateShoppingQuery(event.detail.query));
    root.addEventListener('shopping-clear-query', () => this._clearShoppingQuery());
    root.addEventListener('shopping-submit-query', () => this._submitShoppingQuery());
    root.addEventListener('shopping-refresh', () => this._loadShoppingList());
    root.addEventListener('shopping-select-variant', (event) => this._selectShoppingVariant(event.detail));
    root.addEventListener('shopping-open-detail', (event) => this._openShoppingDetail(event.detail.itemId));
    root.addEventListener('shopping-close-detail', () => this._closeShoppingDetail());
    root.addEventListener('shopping-modal-input', (event) => this._updateShoppingModalInput(event.detail));
    root.addEventListener('shopping-save-detail', () => this._saveShoppingDetail());
    root.addEventListener('shopping-open-mhd', (event) => this._openMhdModal(event.detail.itemId));
    root.addEventListener('shopping-close-mhd', () => this._closeMhdModal());
    root.addEventListener('shopping-save-mhd', () => this._saveMhd());
    root.addEventListener('shopping-reset-mhd', () => this._resetMhd());
    root.addEventListener('shopping-increment-item', (event) => this._incrementShoppingItem(event.detail.itemId));
    root.addEventListener('shopping-complete-item', (event) => this._completeShoppingItem(event.detail.itemId));
    root.addEventListener('shopping-delete-item', (event) => this._deleteShoppingItem(event.detail.itemId));
    root.addEventListener('shopping-complete-all', () => this._completeAllShopping());
    root.addEventListener('shopping-clear-all', () => this._clearAllShopping());
    root.addEventListener('shopping-open-scanner', () => this._openScannerBridge());
    root.addEventListener('shopping-close-scanner', () => this._setScannerOpen(false));
    root.addEventListener('shopping-scanner-status', (event) => this._updateScannerStatus(event.detail?.message));
    root.addEventListener('shopping-scanner-detected', (event) => this._handleScannerDetection(event.detail));
    root.addEventListener('recipes-load-suggestions', () => this._loadRecipeSuggestions());
    root.addEventListener('recipes-load-expiring', () => this._loadExpiringRecipeSuggestions());
    root.addEventListener('recipes-location-selection-change', (event) => this._updateRecipeLocationSelection(event.detail?.locationIds || []));
    root.addEventListener('recipes-product-selection-change', (event) => this._updateRecipeProductSelection(event.detail?.productIds || []));
    root.addEventListener('recipes-expiring-days-change', (event) => this._updateRecipeExpiringDays(event.detail?.value));
    root.addEventListener('recipes-open-detail', (event) => this._openRecipeDetail(event.detail?.item));
    root.addEventListener('recipes-close-detail', () => this._closeRecipeDetail());
    root.addEventListener('recipes-add-missing', () => this._addMissingRecipeProducts());
    root.addEventListener('recipes-open-create', () => this._openRecipeCreateModal());
    root.addEventListener('recipes-close-create', () => this._closeRecipeCreateModal());
    root.addEventListener('recipes-set-create-method', (event) => this._setRecipeCreateMethod(event.detail?.method || event.target?.dataset?.method));
    root.addEventListener('recipes-create-input', (event) => this._updateRecipeCreateInput(event.detail));
    root.addEventListener('recipes-submit-create-webscrape', () => this._submitRecipeCreateWebscrape());
    root.addEventListener('recipes-submit-create-ai', () => this._submitRecipeCreateAiPrompt());
    root.addEventListener('recipes-submit-create-manual', () => this._submitRecipeCreateManual());
    root.addEventListener('storage-refresh', () => this._loadStorageProducts());
    root.addEventListener('storage-filter-change', (event) => this._updateStorageFilter(event.detail?.value));
    root.addEventListener('storage-toggle-include-all', (event) => this._updateStorageIncludeAllProducts(event.detail?.checked));
    root.addEventListener('storage-open-edit', (event) => this._openStorageEdit(event.detail?.itemId));
    root.addEventListener('storage-close-edit', () => this._closeStorageEdit());
    root.addEventListener('storage-edit-input', (event) => this._updateStorageEditInput(event.detail));
    root.addEventListener('storage-save-edit', () => this._saveStorageEdit());
    root.addEventListener('storage-open-consume', (event) => this._openStorageConsume(event.detail?.itemId));
    root.addEventListener('storage-close-consume', () => this._closeStorageConsume());
    root.addEventListener('storage-consume-input', (event) => this._updateStorageConsumeInput(event.detail));
    root.addEventListener('storage-confirm-consume', () => this._confirmStorageConsume());
    root.addEventListener('storage-open-delete', (event) => this._openStorageDelete(event.detail?.itemId));
    root.addEventListener('storage-delete-product-picture', (event) => this._deleteStorageProductPicture(event.detail?.itemId));
    root.addEventListener('storage-close-delete', () => this._closeStorageDelete());
    root.addEventListener('storage-confirm-delete', () => this._confirmStorageDelete());
    root.addEventListener('open-legacy-dashboard', (event) => this._openLegacyDashboard(event.detail?.tab));
  }

  _renderState(state) {
    this._ensureShell();
    if (!this.shadowRoot) return;
    this._syncShellLayoutMetrics();

    const topbar = this.shadowRoot.querySelector('grocy-ai-topbar');
    const tabNav = this.shadowRoot.querySelector('grocy-ai-tab-nav');
    const shoppingTab = this.shadowRoot.querySelector('grocy-ai-shopping-tab');
    const recipesTab = this.shadowRoot.querySelector('grocy-ai-recipes-tab');
    const storageTab = this.shadowRoot.querySelector('grocy-ai-storage-tab');
    const notificationsTab = this.shadowRoot.querySelector('grocy-ai-notifications-tab');
    const modals = this.shadowRoot.querySelector('grocy-ai-dashboard-modals');
    const scannerBridge = this.shadowRoot.querySelector('grocy-ai-scanner-bridge');
    if (!topbar || !tabNav || !shoppingTab || !recipesTab || !storageTab || !notificationsTab || !modals || !scannerBridge) {
      return;
    }

    const searchState = this._shoppingSearch.getState();
    const panelConfig = this._getPanelConfig();
    const panelImageApiBasePath = this._dashboardApiBasePath
      || String(panelConfig?.dashboard_api_base_path || panelConfig?.api_base_path || '').replace(/\/+$/, '');
    const migratedCount = MIGRATED_TABS.size;
    const totalCount = TAB_ORDER.length;
    const topbarStatus = this._resolveActiveTabStatus(state, searchState);
    topbar.viewModel = {
      status: topbarStatus,
      busy: this._isActiveTabBusy(state),
      migratedCount,
      totalCount,
      panelPath: this._getPanelPath(),
      panelIcon: this._getPanelIcon(),
      activeTab: state.activeTab,
    };
    tabNav.viewModel = {
      activeTab: state.activeTab,
    };
    shoppingTab.viewModel = {
      ...state.shopping,
      ...searchState,
      active: state.activeTab === 'shopping',
      resolveImageUrl: (url) => resolvePanelImageUrl(url, this._dashboardApi, { apiBasePath: panelImageApiBasePath }),
    };
    recipesTab.viewModel = {
      ...state.recipes,
      active: state.activeTab === 'recipes',
      apiBasePath: panelImageApiBasePath,
    };
    storageTab.viewModel = {
      ...state.storage,
      active: state.activeTab === 'storage',
      activeEditItem: state.storage.items.find((item) => String(getActionableStorageId(item)) === String(state.storage.editModal.itemId)) || null,
      activeConsumeItem: state.storage.items.find((item) => String(getActionableStorageId(item)) === String(state.storage.consumeModal.itemId)) || null,
      activeDeleteItem: state.storage.items.find((item) => String(getActionableStorageId(item)) === String(state.storage.deleteModal.itemId)) || null,
      resolveImageUrl: (url) => resolvePanelImageUrl(url, this._dashboardApi, { apiBasePath: panelImageApiBasePath }),
    };
    notificationsTab.viewModel = {
      ...state.notifications,
      active: state.activeTab === 'notifications',
      title: 'Benachrichtigungen',
      tabName: 'notifications',
      legacyUrl: state.notifications.legacyFallbackUrl || this._getResolvedLegacyDashboardEmergencyUrl(),
    };

    const activeItem = state.shopping.list.find((item) => String(item.id) === String(state.shopping.detailModal.itemId))
      || state.shopping.list.find((item) => String(item.id) === String(state.shopping.mhdModal.itemId))
      || null;
    modals.viewModel = {
      shopping: {
        detailModal: state.shopping.detailModal,
        mhdModal: state.shopping.mhdModal,
        activeItem,
      },
      recipes: {
        ...state.recipes,
        apiBasePath: panelImageApiBasePath,
      },
    };
    scannerBridge.viewModel = {
      ...state.shopping.scanner,
    };
    scannerBridge.api = this._api;
    this._setModalScrollLock(this._isAnyModalOpen(state));
  }

  _isAnyModalOpen(state) {
    return Boolean(
      state.shopping.detailModal.open
      || state.shopping.mhdModal.open
      || state.shopping.scanner.open
      || state.recipes.detailModal.open
      || state.recipes.createModal.open
      || state.storage.editModal.open
      || state.storage.consumeModal.open
      || state.storage.deleteModal.open
    );
  }

  _setModalScrollLock(locked) {
    const shouldLock = Boolean(locked);
    const shell = this.shadowRoot?.querySelector('.page-shell');
    this.toggleAttribute('data-modal-open', shouldLock);
    shell?.classList.toggle('page-shell--modal-open', shouldLock);

    if (shouldLock) {
      if (this._scrollLockState) return;

      const scrollingElement = document.scrollingElement;
      const body = document.body;
      const scrollTop = window.scrollY || scrollingElement?.scrollTop || 0;
      this._scrollLockState = {
        scrollTop,
        bodyOverflow: body?.style.overflow || '',
        bodyPosition: body?.style.position || '',
        bodyTop: body?.style.top || '',
        bodyWidth: body?.style.width || '',
        scrollingOverflow: scrollingElement?.style.overflow || '',
        htmlOverscrollBehavior: document.documentElement.style.overscrollBehavior || '',
      };

      if (body) {
        body.style.overflow = 'hidden';
        body.style.position = 'fixed';
        body.style.top = `-${scrollTop}px`;
        body.style.width = '100%';
      }
      if (scrollingElement && scrollingElement !== body) {
        scrollingElement.style.overflow = 'hidden';
      }
      document.documentElement.style.overscrollBehavior = 'none';
      return;
    }

    if (!this._scrollLockState) return;

    const { scrollTop, bodyOverflow, bodyPosition, bodyTop, bodyWidth, scrollingOverflow, htmlOverscrollBehavior } = this._scrollLockState;
    const scrollingElement = document.scrollingElement;
    const body = document.body;

    if (body) {
      body.style.overflow = bodyOverflow;
      body.style.position = bodyPosition;
      body.style.top = bodyTop;
      body.style.width = bodyWidth;
    }
    if (scrollingElement && scrollingElement !== body) {
      scrollingElement.style.overflow = scrollingOverflow;
    }
    document.documentElement.style.overscrollBehavior = htmlOverscrollBehavior;
    this._scrollLockState = null;
    window.scrollTo(0, scrollTop);
  }

  _switchTab(tab, options = {}) {
    const normalizedTab = normalizeTabName(tab);
    if (!normalizedTab) return;

    const currentState = this._store.getState();
    const stateChanged = currentState.activeTab !== normalizedTab;
    const { syncHistory = true, announce = true } = options;
    const shouldUpdateUrl = options.updateUrl ?? syncHistory;

    if (stateChanged || options.forceStatus) {
      this._store.patch({
        activeTab: normalizedTab,
        topbarStatus: announce ? `${TAB_LABELS[normalizedTab]} geöffnet.` : currentState.topbarStatus,
      });
    }

    if (shouldUpdateUrl) {
      this._updateBrowserUrlForTab(normalizedTab, { replace: Boolean(options.replaceUrl) });
    }
    this._activateTab(normalizedTab);
  }

  _syncActiveTabFromLocation(options = {}) {
    const resolvedTab = resolveTabFromLocation(window.location, this._route);
    const currentUrl = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    const expectedUrl = buildPanelUrlWithTab(window.location, resolvedTab);
    const shouldUpdateUrl = options.updateUrl !== false && currentUrl !== expectedUrl;

    this._switchTab(resolvedTab, {
      updateUrl: shouldUpdateUrl,
      replaceUrl: options.replaceUrl || shouldUpdateUrl,
    });
  }

  _updateBrowserUrlForTab(tab, { replace = false } = {}) {
    const nextUrl = buildPanelUrlWithTab(window.location, tab);
    const currentUrl = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    if (nextUrl === currentUrl) return;

    const method = replace ? 'replaceState' : 'pushState';
    window.history[method]({ tab }, '', nextUrl);
  }

  _updateShoppingState(partial) {
    return this._updateTabState('shopping', partial);
  }

  _updateRecipesState(partial) {
    return this._updateTabState('recipes', partial);
  }

  _updateStorageState(partial) {
    return this._updateTabState('storage', partial);
  }

  _updateNotificationsState(partial) {
    return this._updateTabState('notifications', partial);
  }

  _updateTabState(tabName, partial) {
    return this._store.patchIn(tabName, partial);
  }

  _updateTabViewState(tabName, partial) {
    return this._store.patchIn([tabName, 'viewState'], partial);
  }

  _setTabStatus(tabName, status, options = {}) {
    const currentTabState = this._store.getIn(tabName, {});
    const nextError = typeof options.error === 'string'
      ? options.error
      : (options.state === TAB_VIEW_STATE.ERROR ? status : '');
    const nextViewState = {
      ...createTabViewState(currentTabState.viewState || {}),
      loading: options.state === TAB_VIEW_STATE.LOADING,
      loaded: options.state === TAB_VIEW_STATE.LOADED
        ? true
        : Boolean(currentTabState.viewState?.loaded && options.state !== TAB_VIEW_STATE.ERROR),
      empty: typeof options.empty === 'boolean'
        ? options.empty
        : Boolean(currentTabState.viewState?.empty),
      editing: options.state === TAB_VIEW_STATE.EDITING,
      error: nextError,
    };

    this._updateTabState(tabName, { status });
    this._updateTabViewState(tabName, nextViewState);

    if (options.syncTopbar !== false) {
      this._store.patch({ topbarStatus: status });
    }
  }

  _setTabModalState(tabName, modalKey, modalState, options = {}) {
    this._store.setIn([tabName, modalKey], modalState);

    if (typeof options.editing === 'boolean') {
      this._updateTabViewState(tabName, { editing: options.editing });
    }

    if (tabName === 'shopping') {
      this._syncShoppingPolling();
    }
  }

  _resolveActiveTabStatus(state, searchState) {
    if (state.pendingRequests > 0 && searchState.flowState === SEARCH_FLOW_STATES.SUBMITTING) {
      return searchState.statusMessage;
    }

    if (state.activeTab === 'shopping') return state.shopping.status;
    if (state.activeTab === 'recipes') return state.recipes.status;
    if (state.activeTab === 'storage') return state.storage.status;
    return state.notifications.status || state.topbarStatus;
  }

  _isActiveTabBusy(state) {
    const activeState = state[state.activeTab];
    return Boolean(activeState?.viewState?.loading || activeState?.viewState?.editing || state.pendingRequests > 0);
  }

  _syncShoppingPolling() {
    if (!Number.isFinite(this._shoppingPollIntervalMs) || this._shoppingPollIntervalMs <= 0) {
      this._stopShoppingPolling();
      return;
    }
    if (this._canPollShopping({ requireNoTimer: true })) {
      this._startShoppingPolling();
      return;
    }
    if (!this._canPollShopping({ requireNoTimer: false })) {
      this._stopShoppingPolling();
    }
  }

  _canPollShopping({ requireNoTimer = true } = {}) {
    const state = this._store.getState();
    if (document.hidden) return false;
    if (state.activeTab !== 'shopping') return false;
    if (requireNoTimer && state.shopping.pollTimer) return false;
    if (state.shopping.detailModal.open || state.shopping.mhdModal.open || state.shopping.scanner.open) return false;
    if (state.shopping.viewState.editing) return false;
    return true;
  }

  _handleDocumentVisibilityChange() {
    this._syncShoppingPolling();
    if (document.hidden) return;
    if (!this._canPollShopping({ requireNoTimer: false })) return;
    void this._loadShoppingList({ silent: true });
  }

  _activateTab(tabName) {
    if (tabName === DEFAULT_TAB) {
      this._syncShoppingPolling();
      if (!this._store.getState().shopping.listLoaded) {
        this._loadShoppingList();
      }
    } else {
      this._stopShoppingPolling();
    }

    if (tabName === 'recipes' && !this._store.getState().recipes.initialized) {
      void this._initializeRecipesTab();
    }

    if (tabName === 'storage' && !this._store.getState().storage.initialized) {
      void this._initializeStorageTab();
    }

    if (tabName === 'notifications') {
      this._updateNotificationsState({
        legacyFallbackUrl: this._getResolvedLegacyDashboardEmergencyUrl(),
      });
    }
  }

  async _initializeRecipesTab() {
    this._setTabStatus('recipes', 'Lade Lagerstandorte…', { state: TAB_VIEW_STATE.LOADING, syncTopbar: false });
    await this._runRequest(async () => {
      const api = await this._getDashboardApiOrThrow();
      const { response, payload } = await api.fetchLocations();
      if (!response.ok) throw new Error(getErrorMessage(payload, 'Standorte konnten nicht geladen werden.'));

      this._updateRecipesState({
        initialized: true,
        locations: Array.isArray(payload) ? payload : [],
      });

      await this._loadRecipeStockProducts();
    }, {
      onError: (message) => {
        this._setTabStatus('recipes', `Fehler: ${message}`, { state: TAB_VIEW_STATE.ERROR, error: message, syncTopbar: false });
      },
    });
  }

  _updateRecipeLocationSelection(locationIds) {
    const normalizedLocationIds = (Array.isArray(locationIds) ? locationIds : [])
      .map((value) => Number(value))
      .filter((value) => Number.isFinite(value) && value > 0);
    this._updateRecipesState({ selectedLocationIds: normalizedLocationIds });
    void this._loadRecipeStockProducts();
  }

  _updateRecipeProductSelection(productIds) {
    const normalizedProductIds = (Array.isArray(productIds) ? productIds : [])
      .map((value) => Number(value))
      .filter((value) => Number.isFinite(value) && value > 0);
    this._updateRecipesState({ selectedProductIds: normalizedProductIds });
  }

  _updateRecipeExpiringDays(value) {
    const parsedDays = Number(value || 3);
    const expiringWithinDays = Math.min(30, Math.max(1, Number.isFinite(parsedDays) ? Math.round(parsedDays) : 3));
    this._updateRecipesState({ expiringWithinDays });
  }

  async _loadRecipeStockProducts() {
    this._setTabStatus('recipes', 'Lade Produkte in ausgewählten Standorten…', { state: TAB_VIEW_STATE.LOADING, syncTopbar: false });
    await this._runRequest(async () => {
      const api = await this._getDashboardApiOrThrow();
      const recipeState = this._store.getState().recipes;
      const { response, payload } = await api.fetchStockProducts({
        locationIds: recipeState.selectedLocationIds,
      });
      if (!response.ok) throw new Error(getErrorMessage(payload, 'Bestand konnte nicht geladen werden.'));

      const normalizedPayload = (Array.isArray(payload) ? payload : []).map(normalizeStockProduct);
      const availableProductIds = new Set(normalizedPayload.map((item) => item.id).filter(Boolean));
      const selectedProductIds = recipeState.selectedProductIds.filter((id) => availableProductIds.has(id));
      const nextStockSignature = buildStockSignature(normalizedPayload);
      const hasStockChanged = recipeState.stockSignature !== null && recipeState.stockSignature !== nextStockSignature;

      this._updateRecipesState({
        stockProducts: normalizedPayload,
        selectedProductIds: selectedProductIds.length ? selectedProductIds : normalizedPayload.map((item) => item.id).filter(Boolean),
        stockSignature: nextStockSignature,
        status: hasStockChanged
          ? 'Bestand aktualisiert. Lade Rezeptvorschläge bei Bedarf manuell.'
          : 'Bestand geladen. Lade Rezeptvorschläge bei Bedarf manuell.',
      });
      this._updateTabViewState('recipes', {
        loaded: true,
        loading: false,
        empty: normalizedPayload.length === 0,
        error: '',
      });

      if (!hasStockChanged && !recipeState.hasLoadedInitialSuggestions) {
        this._updateRecipesState({ hasLoadedInitialSuggestions: true });
        await this._loadRecipeSuggestions({ usePrefetchedCache: true });
      }
    }, {
      onError: (message) => {
        this._setTabStatus('recipes', `Fehler: ${message}`, { state: TAB_VIEW_STATE.ERROR, error: message, syncTopbar: false });
      },
    });
  }

  async _loadRecipeSuggestions(options = {}) {
    this._updateRecipesState({ status: 'Lade Rezeptvorschläge…' });
    await this._runRequest(async () => {
      const api = await this._getDashboardApiOrThrow();
      const recipeState = this._store.getState().recipes;
      const usePrefetchedCache = Boolean(options.usePrefetchedCache);
      const selectedProductIds = usePrefetchedCache ? [] : recipeState.selectedProductIds;
      const selectedLocationIds = usePrefetchedCache ? [] : recipeState.selectedLocationIds;
      const soonExpiringOnly = Boolean(options.soonExpiringOnly);
      const expiringWithinDays = Number(options.expiringWithinDays || recipeState.expiringWithinDays || 3);

      this._updateRecipesState({
        selectedProductIds,
        selectedLocationIds,
        expiringWithinDays,
        status: soonExpiringOnly
          ? `Lade Rezepte mit bald ablaufenden Produkten (<= ${expiringWithinDays} Tage)…`
          : usePrefetchedCache
            ? 'Lade initiale Rezeptvorschläge aus dem Cache…'
            : selectedProductIds.length
              ? 'Lade Rezeptvorschläge für Auswahl…'
              : 'Lade Rezeptvorschläge aus dem aktuellen Lagerbestand…',
      });

      const { response, payload } = await api.fetchRecipeSuggestions({
        product_ids: selectedProductIds,
        location_ids: selectedLocationIds,
        soon_expiring_only: soonExpiringOnly,
        expiring_within_days: expiringWithinDays,
      });
      if (!response.ok) throw new Error(getErrorMessage(payload, 'Rezeptvorschläge konnten nicht geladen werden.'));

      this._updateRecipesState({
        grocyRecipes: (payload.grocy_recipes || []).slice(0, GROCY_RECIPE_DISPLAY_LIMIT),
        aiRecipes: (payload.ai_recipes || []).slice(0, AI_RECIPE_DISPLAY_LIMIT),
        status: 'Rezeptvorschläge geladen für: Alles',
      });
      this._store.patch({ topbarStatus: 'Rezeptvorschläge geladen für: Alles' });
    }, {
      onError: (message) => {
        this._updateRecipesState({ status: `Fehler: ${message}` });
      },
    });
  }

  _loadExpiringRecipeSuggestions() {
    const expiringWithinDays = Math.min(30, Math.max(1, Number(this._store.getState().recipes.expiringWithinDays || 3)));
    this._updateRecipesState({ expiringWithinDays });
    void this._loadRecipeSuggestions({ soonExpiringOnly: true, expiringWithinDays });
  }

  _openRecipeDetail(item) {
    if (!item || typeof item !== 'object') return;
    this._setTabModalState('recipes', 'detailModal', {
      open: true,
      item,
    }, { editing: true });
  }

  _closeRecipeDetail() {
    this._setTabModalState('recipes', 'detailModal', {
      open: false,
      item: null,
    }, { editing: false });
  }

  async _addMissingRecipeProducts() {
    const recipeItem = this._store.getState().recipes.detailModal.item;
    if (!(recipeItem?.source === 'grocy' && Number.isInteger(recipeItem?.recipe_id))) return;

    this._updateRecipesState({ status: 'Füge fehlende Produkte hinzu…' });
    await this._runRequest(async () => {
      const api = await this._getDashboardApiOrThrow();
      const { response, payload } = await api.addMissingRecipeProducts(recipeItem.recipe_id);
      if (!response.ok) throw new Error(getErrorMessage(payload, 'Fehlende Produkte konnten nicht hinzugefügt werden.'));

      const successMessage = payload?.message || 'Fehlende Produkte wurden hinzugefügt.';
      this._closeRecipeDetail();
      this._updateRecipesState({ status: successMessage });
      this._store.patch({ topbarStatus: successMessage });
      await this._loadShoppingList({ silent: true });
    }, {
      onError: (message) => {
        this._updateRecipesState({ status: `Fehler: ${message}` });
      },
    });
  }

  _openRecipeCreateModal() {
    const createModal = this._store.getState().recipes.createModal;
    this._setTabModalState('recipes', 'createModal', {
      ...createModal,
      open: true,
    }, { editing: true });
  }

  _closeRecipeCreateModal() {
    const createModal = this._store.getState().recipes.createModal;
    this._setTabModalState('recipes', 'createModal', {
      ...createModal,
      open: false,
    }, { editing: false });
  }

  _setRecipeCreateMethod(method) {
    const nextMethod = ['webscrape', 'ai', 'manual'].includes(method) ? method : 'webscrape';
    this._updateRecipesState({
      createModal: {
        ...this._store.getState().recipes.createModal,
        method: nextMethod,
      },
    });
  }

  _updateRecipeCreateInput(detail) {
    if (!detail?.field) return;
    this._updateRecipesState({
      createModal: {
        ...this._store.getState().recipes.createModal,
        [detail.field]: detail.value,
      },
    });
  }

  _setRecipeStatus(message) {
    this._setTabStatus('recipes', message, { state: TAB_VIEW_STATE.LOADED });
  }

  _submitRecipeCreateWebscrape() {
    const { webscrapeUrl } = this._store.getState().recipes.createModal;
    const rawUrl = String(webscrapeUrl || '').trim();
    if (!rawUrl) {
      this._setRecipeStatus('Bitte zuerst eine URL für WebScrape eingeben.');
      return;
    }

    try {
      const parsedUrl = new URL(rawUrl);
      this._setRecipeStatus(`WebScrape-URL erfasst: ${parsedUrl.toString()}`);
      this._closeRecipeCreateModal();
    } catch (_) {
      this._setRecipeStatus('Bitte eine gültige URL angeben (inkl. http/https).');
    }
  }

  _submitRecipeCreateAiPrompt() {
    const prompt = String(this._store.getState().recipes.createModal.aiPrompt || '').trim();
    if (!prompt) {
      this._setRecipeStatus('Bitte eine KI-Anfrage für das Rezept eingeben.');
      return;
    }

    this._setRecipeStatus('KI-Rezeptanfrage erfasst. Nächster Schritt: Attribut-Extraktion anbinden.');
    this._closeRecipeCreateModal();
  }

  _submitRecipeCreateManual() {
    const createModal = this._store.getState().recipes.createModal;
    const title = String(createModal.manualTitle || '').trim();
    const ingredientsRaw = String(createModal.manualIngredients || '').trim();
    if (!title) {
      this._setRecipeStatus('Bitte einen Rezeptnamen eingeben.');
      return;
    }
    if (!ingredientsRaw) {
      this._setRecipeStatus('Bitte mindestens eine Zutat für das manuelle Rezept eingeben.');
      return;
    }

    const servings = Number(createModal.manualServings || '1');
    const ingredientCount = ingredientsRaw.split('\n').map((entry) => entry.trim()).filter(Boolean).length;
    this._setRecipeStatus(`Manuelles Rezept erfasst: ${title} (${Math.max(1, servings)} Portionen, ${ingredientCount} Zutaten).`);
    this._closeRecipeCreateModal();
  }

  async _initializeStorageTab() {
    this._setTabStatus('storage', 'Lade Lagerstandorte…', { state: TAB_VIEW_STATE.LOADING, syncTopbar: false });
    this._updateStorageState({ loading: true });
    await this._runRequest(async () => {
      const api = await this._getDashboardApiOrThrow();
      const { response, payload } = await api.fetchLocations();
      if (!response.ok) throw new Error(getErrorMessage(payload, 'Standorte konnten nicht geladen werden.'));

      this._updateStorageState({
        initialized: true,
        locations: Array.isArray(payload) ? payload : [],
      });

      await this._loadStorageProducts({ silent: true });
    }, {
      onError: (message) => {
        this._updateStorageState({ loading: false });
        this._setTabStatus('storage', `Fehler: ${message}`, { state: TAB_VIEW_STATE.ERROR, error: message, syncTopbar: false });
      },
    });
  }

  _findStorageItem(itemId) {
    return this._store.getState().storage.items.find((item) => String(getActionableStorageId(item)) === String(itemId)) || null;
  }

  async _fetchStorageSummary(api, { query = '', visibleItems = [] } = {}) {
    const normalizedVisibleItems = Array.isArray(visibleItems) ? visibleItems : [];
    const fallbackSummary = {
      totalCount: normalizedVisibleItems.length,
      inStockCount: normalizedVisibleItems.filter((item) => item?.in_stock).length,
      outOfStockCount: normalizedVisibleItems.filter((item) => !item?.in_stock).length,
    };

    const { response, payload } = await api.fetchStockProducts({
      includeAllProducts: true,
      query,
    });
    if (!response.ok) {
      return fallbackSummary;
    }

    const allItems = (Array.isArray(payload) ? payload : []).map(normalizeStockProduct);
    const inStockCount = allItems.filter((item) => item?.in_stock).length;
    return {
      totalCount: allItems.length,
      inStockCount,
      outOfStockCount: allItems.length - inStockCount,
    };
  }

  async _loadStorageProducts(options = {}) {
    const storageState = this._store.getState().storage;
    this._updateStorageState({
      loading: true,
      status: options.silent
        ? storageState.status
        : storageState.includeAllProducts
          ? 'Lade Lagerbestand und alle Produkte…'
          : 'Lade Lagerbestand…',
    });

    await this._runRequest(async () => {
      const api = await this._getDashboardApiOrThrow();
      const latestState = this._store.getState().storage;
      const { response, payload } = await api.fetchStockProducts({
        includeAllProducts: latestState.includeAllProducts,
        query: latestState.filter,
      });
      if (!response.ok) throw new Error(getErrorMessage(payload, 'Bestand konnte nicht geladen werden.'));

      const items = (Array.isArray(payload) ? payload : []).map(normalizeStockProduct);
      const outOfStockCount = items.filter((item) => !item.in_stock).length;
      const fallbackProductIds = items.filter((item) => Number(item.stock_id || 0) <= 0 && Number(item.id || 0) > 0).length;
      const summary = latestState.includeAllProducts
        ? {
          totalCount: items.length,
          inStockCount: items.filter((item) => item?.in_stock).length,
          outOfStockCount,
        }
        : await this._fetchStorageSummary(api, {
          query: latestState.filter,
          visibleItems: items,
        });

      this._updateStorageState({
        items,
        summary,
        loading: false,
        status: summary.outOfStockCount > 0 || fallbackProductIds > 0
          ? `Lagerbestand geladen (${summary.totalCount} Produkte, ${summary.outOfStockCount} nicht auf Lager${fallbackProductIds > 0 ? `, ${fallbackProductIds} via Produkt-ID` : ''}).`
          : `Lagerbestand geladen (${summary.totalCount} Produkte).`,
      });
      this._updateTabViewState('storage', {
        loaded: true,
        loading: false,
        empty: items.length === 0,
        error: '',
      });
      this._store.patch({ topbarStatus: `Lager aktualisiert (${items.length} Produkte).` });
    }, {
      onError: (message) => {
        this._updateStorageState({ loading: false });
        this._setTabStatus('storage', `Fehler: ${message}`, { state: TAB_VIEW_STATE.ERROR, error: message, syncTopbar: false });
      },
    });
  }

  _updateStorageFilter(value) {
    this._updateStorageState({ filter: String(value || '') });
    window.clearTimeout(this._storageFilterDebounce);
    this._storageFilterDebounce = window.setTimeout(() => {
      void this._loadStorageProducts();
    }, 250);
  }

  _updateStorageIncludeAllProducts(checked) {
    this._updateStorageState({ includeAllProducts: Boolean(checked) });
    void this._loadStorageProducts();
  }

  _openStorageEdit(itemId) {
    const item = this._findStorageItem(itemId);
    if (!item) return;
    const actionableItemId = getActionableStorageId(item);
    this._setTabModalState('storage', 'editModal', {
      open: true,
      itemId: actionableItemId,
      amount: formatAmount(item.amount, '0'),
      bestBeforeDate: formatStorageDateLabel(item.best_before_date, ''),
      locationId: item.location_id ? String(item.location_id) : '',
      calories: String(item.calories || '').replace(',', '.'),
      carbs: String(item.carbs || '').replace(',', '.'),
      fat: String(item.fat || '').replace(',', '.'),
      protein: String(item.protein || '').replace(',', '.'),
      sugar: String(item.sugar || '').replace(',', '.'),
    }, { editing: true });

    const productId = Number(item?.id || 0);
    if (!Number.isFinite(productId) || productId <= 0) return;

    void (async () => {
      try {
        const api = await this._getDashboardApiOrThrow();
        const { response, payload } = await api.fetchProductNutrition(productId);
        if (!response.ok || !payload || typeof payload !== 'object') return;

        const currentEditModal = this._store.getState().storage.editModal;
        if (!currentEditModal.open || Number(currentEditModal.itemId) !== actionableItemId) return;

        this._updateStorageState({
          editModal: {
            ...currentEditModal,
            calories: String(payload.calories || '').replace(',', '.'),
            carbs: String(payload.carbs || '').replace(',', '.'),
            fat: String(payload.fat || '').replace(',', '.'),
            protein: String(payload.protein || '').replace(',', '.'),
            sugar: String(payload.sugar || '').replace(',', '.'),
          },
        });
      } catch (error) {
        console.debug('Nutrition userfields could not be loaded for storage edit modal:', error);
      }
    })();
  }

  _closeStorageEdit() {
    this._setTabModalState('storage', 'editModal', {
      open: false,
      itemId: null,
      amount: '',
      bestBeforeDate: '',
      locationId: '',
      calories: '',
      carbs: '',
      fat: '',
      protein: '',
      sugar: '',
    }, { editing: false });
  }

  _updateStorageEditInput(detail) {
    if (!detail?.field) return;
    this._updateStorageState({
      editModal: {
        ...this._store.getState().storage.editModal,
        [detail.field]: detail.value,
      },
    });
  }

  async _saveStorageEdit() {
    const storageState = this._store.getState().storage;
    const editModal = storageState.editModal;
    if (!editModal.itemId) return;

    const amount = Number(String(editModal.amount || '').replace(',', '.'));
    const calories = normalizeNutritionInputValue(editModal.calories);
    const carbs = normalizeNutritionInputValue(editModal.carbs);
    const fat = normalizeNutritionInputValue(editModal.fat);
    const protein = normalizeNutritionInputValue(editModal.protein);
    const sugar = normalizeNutritionInputValue(editModal.sugar);
    if (!Number.isFinite(amount) || amount < 0) {
      this._updateStorageState({ status: 'Bitte eine gültige Menge eingeben.' });
      return;
    }
    if ([calories, carbs, fat, protein, sugar].some((value) => Number.isNaN(value))) {
      this._updateStorageState({ status: 'Bitte gültige Nährwerte (>= 0) eingeben.' });
      return;
    }

    const item = this._findStorageItem(editModal.itemId);
    if (!item) return;

    this._updateStorageState({ status: 'Speichere Bestand…' });
    await this._runRequest(async () => {
      const api = await this._getDashboardApiOrThrow();
      const locationId = Number(editModal.locationId || 0);
      const { response, payload } = await api.updateStockProduct(editModal.itemId, {
        amount,
        best_before_date: editModal.bestBeforeDate || '',
        location_id: Number.isFinite(locationId) && locationId > 0 ? locationId : null,
        calories,
        carbs,
        fat,
        protein,
        sugar,
      }, {
        productId: item.id,
      });
      if (!response.ok) throw new Error(getErrorMessage(payload, 'Bestand konnte nicht aktualisiert werden.'));

      this._closeStorageEdit();
      this._updateStorageState({ status: 'Bestand wurde aktualisiert.' });
      this._store.patch({ topbarStatus: 'Bestand wurde aktualisiert.' });
      await this._loadStorageProducts({ silent: true });
    }, {
      onError: (message) => {
        this._updateStorageState({ status: `Fehler: ${message}` });
      },
    });
  }

  _openStorageConsume(itemId) {
    const item = this._findStorageItem(itemId);
    if (!item) return;
    this._setTabModalState('storage', 'consumeModal', {
      open: true,
      itemId: getActionableStorageId(item),
      amount: '1',
    }, { editing: true });
  }

  _closeStorageConsume() {
    this._setTabModalState('storage', 'consumeModal', {
      open: false,
      itemId: null,
      amount: '1',
    }, { editing: false });
  }

  _updateStorageConsumeInput(detail) {
    if (!detail?.field) return;
    this._updateStorageState({
      consumeModal: {
        ...this._store.getState().storage.consumeModal,
        [detail.field]: detail.value,
      },
    });
  }

  async _confirmStorageConsume() {
    const consumeModal = this._store.getState().storage.consumeModal;
    if (!consumeModal.itemId) return;
    const amount = Number(String(consumeModal.amount || '').replace(',', '.'));
    if (!Number.isFinite(amount) || amount <= 0) {
      this._updateStorageState({ status: 'Bitte eine gültige Verbrauchsmenge eingeben.' });
      return;
    }

    const item = this._findStorageItem(consumeModal.itemId);
    if (!item) return;

    this._updateStorageState({ status: 'Produkt wird verbraucht…' });
    await this._runRequest(async () => {
      const api = await this._getDashboardApiOrThrow();
      const { response, payload } = await api.consumeStockProduct(consumeModal.itemId, {
        amount,
        productId: item.id,
      });
      if (!response.ok) throw new Error(getErrorMessage(payload, 'Produkt konnte nicht verbraucht werden.'));

      this._closeStorageConsume();
      this._updateStorageState({ status: 'Produkt wurde verbraucht.' });
      this._store.patch({ topbarStatus: 'Produkt wurde verbraucht.' });
      await this._loadStorageProducts({ silent: true });
    }, {
      onError: (message) => {
        this._updateStorageState({ status: `Fehler: ${message}` });
      },
    });
  }

  _openStorageDelete(itemId) {
    const item = this._findStorageItem(itemId);
    if (!item) return;
    this._setTabModalState('storage', 'deleteModal', {
      open: true,
      itemId: getActionableStorageId(item),
    }, { editing: true });
  }

  _closeStorageDelete() {
    this._setTabModalState('storage', 'deleteModal', {
      open: false,
      itemId: null,
    }, { editing: false });
  }

  async _deleteStorageProductPicture(itemId) {
    const item = this._findStorageItem(itemId);
    if (!item || !Number.isFinite(Number(item.id)) || Number(item.id) <= 0) return;

    this._updateStorageState({ status: 'Produktbild wird gelöscht…' });
    await this._runRequest(async () => {
      const api = await this._getDashboardApiOrThrow();
      const { response, payload } = await api.deleteProductPicture(item.id);
      if (!response.ok) throw new Error(getErrorMessage(payload, 'Produktbild konnte nicht gelöscht werden.'));

      this._closeStorageEdit();
      this._updateStorageState({ status: payload?.message || 'Produktbild wurde gelöscht.' });
      this._store.patch({ topbarStatus: payload?.message || 'Produktbild wurde gelöscht.' });
      await this._loadStorageProducts({ silent: true });
    }, {
      onError: (message) => {
        this._updateStorageState({ status: `Fehler: ${message}` });
      },
    });
  }

  async _confirmStorageDelete() {
    const deleteModal = this._store.getState().storage.deleteModal;
    if (!deleteModal.itemId) return;

    const item = this._findStorageItem(deleteModal.itemId);
    if (!item) return;

    this._updateStorageState({ status: 'Bestandseintrag wird gelöscht…' });
    await this._runRequest(async () => {
      const api = await this._getDashboardApiOrThrow();
      const { response, payload } = await api.deleteStockProduct(deleteModal.itemId, {
        productId: item.id,
      });
      if (!response.ok) throw new Error(getErrorMessage(payload, 'Bestandseintrag konnte nicht gelöscht werden.'));

      this._closeStorageDelete();
      this._updateStorageState({ status: payload?.message || 'Bestandseintrag wurde gelöscht.' });
      this._store.patch({ topbarStatus: payload?.message || 'Bestandseintrag wurde gelöscht.' });
      await this._loadStorageProducts({ silent: true });
    }, {
      onError: (message) => {
        this._updateStorageState({ status: `Fehler: ${message}` });
      },
    });
  }

  _updateShoppingQuery(query) {
    this._shoppingSearch.actions.setQuery(query);
  }

  _clearShoppingQuery() {
    this._shoppingSearch.actions.clearQuery();
  }

  async _submitShoppingQuery() {
    await this._runRequest(async () => {
      await this._getDashboardApiOrThrow();
      const result = await this._shoppingSearch.actions.searchProduct();
      const searchState = this._shoppingSearch.getState();
      this._store.patch({ topbarStatus: searchState.errorMessage || searchState.statusMessage });
      if (!result.ok && searchState.errorMessage) {
        throw new Error(searchState.errorMessage);
      }
    }, {
      onError: () => {},
    });
  }

  async _selectShoppingVariant(detail) {
    await this._runRequest(async () => {
      await this._getDashboardApiOrThrow();
      const result = await this._shoppingSearch.actions.selectVariant(detail);
      const searchState = this._shoppingSearch.getState();
      this._store.patch({ topbarStatus: searchState.errorMessage || searchState.statusMessage });
      if (!result.ok && searchState.errorMessage) {
        throw new Error(searchState.errorMessage);
      }
    }, {
      onError: () => {},
    });
  }

  async _loadShoppingList(options = {}) {
    this._updateShoppingState({ listLoading: !options.silent, status: options.silent ? this._store.getState().shopping.status : 'Lade Einkaufsliste…' });
    if (!options.silent) {
      this._updateTabViewState('shopping', { loading: true, error: '' });
    }
    await this._runRequest(async () => {
      const api = await this._getDashboardApiOrThrow();
      const { response, payload } = await api.fetchShoppingList();
      if (!response.ok) throw new Error(getErrorMessage(payload, 'Einkaufsliste konnte nicht geladen werden.'));
      const list = Array.isArray(payload) ? payload : [];
      this._updateShoppingState({
        list,
        listLoading: false,
        listLoaded: true,
        status: 'Einkaufsliste aktualisiert.',
      });
      this._updateTabViewState('shopping', {
        loaded: true,
        loading: false,
        empty: list.length === 0,
        error: '',
      });
      this._store.patch({ topbarStatus: 'Einkaufsliste aktualisiert.' });
      this._syncShoppingPolling();
    }, {
      onError: (message) => {
        this._updateShoppingState({ listLoading: false, status: `Fehler: ${message}` });
        this._updateTabViewState('shopping', { loading: false, error: message });
      },
    });
  }


  _openShoppingDetail(itemId) {
    const item = this._store.getState().shopping.list.find((entry) => String(entry.id) === String(itemId));
    if (!item) return;
    this._setTabModalState('shopping', 'detailModal', {
      open: true,
      itemId: item.id,
      amount: formatAmount(item.amount),
      note: item.note || '',
    }, { editing: true });
  }

  _closeShoppingDetail() {
    this._setTabModalState('shopping', 'detailModal', {
      open: false,
      itemId: null,
      amount: '',
      note: '',
    }, { editing: false });
  }

  _updateShoppingModalInput(detail) {
    if (!detail?.field) return;
    if (detail.field === 'amount' || detail.field === 'note') {
      this._updateShoppingState({
        detailModal: {
          ...this._store.getState().shopping.detailModal,
          [detail.field]: detail.value,
        },
      });
      return;
    }

    if (detail.field === 'mhd') {
      this._updateShoppingState({
        mhdModal: {
          ...this._store.getState().shopping.mhdModal,
          value: detail.value,
        },
      });
    }
  }

  async _saveShoppingDetail() {
    const { detailModal } = this._store.getState().shopping;
    if (!detailModal.itemId) return;

    this._updateShoppingState({ status: 'Speichere Produktdetails…' });
    await this._runRequest(async () => {
      const api = await this._getDashboardApiOrThrow();
      const amountRequest = api.updateShoppingListItemAmount(detailModal.itemId, detailModal.amount);
      const noteRequest = api.updateShoppingListItemNote(detailModal.itemId, detailModal.note || '');
      const [amountResult, noteResult] = await Promise.all([amountRequest, noteRequest]);
      if (!amountResult.response.ok) throw new Error(getErrorMessage(amountResult.payload, 'Menge konnte nicht gespeichert werden.'));
      if (!noteResult.response.ok) throw new Error(getErrorMessage(noteResult.payload, 'Notiz konnte nicht gespeichert werden.'));
      this._closeShoppingDetail();
      this._store.patch({ topbarStatus: 'Produktdetails gespeichert.' });
      this._updateShoppingState({ status: 'Produktdetails gespeichert.' });
      await this._loadShoppingList({ silent: true });
    }, {
      onError: (message) => {
        this._updateShoppingState({ status: `Fehler: ${message}` });
      },
    });
  }

  _openMhdModal(itemId) {
    const item = this._store.getState().shopping.list.find((entry) => String(entry.id) === String(itemId));
    if (!item) return;
    this._setTabModalState('shopping', 'mhdModal', {
      open: true,
      itemId: item.id,
      value: item.best_before_date || '',
    }, { editing: true });
  }

  _closeMhdModal() {
    this._setTabModalState('shopping', 'mhdModal', {
      open: false,
      itemId: null,
      value: '',
    }, { editing: false });
  }

  async _saveMhd() {
    const { mhdModal } = this._store.getState().shopping;
    if (!mhdModal.itemId) return;

    this._updateShoppingState({ status: 'Speichere MHD…' });
    await this._runRequest(async () => {
      const api = await this._getDashboardApiOrThrow();
      const { response, payload } = await api.updateShoppingListItemBestBefore(mhdModal.itemId, mhdModal.value);
      if (!response.ok) throw new Error(getErrorMessage(payload, 'MHD konnte nicht gespeichert werden.'));
      this._closeMhdModal();
      this._store.patch({ topbarStatus: 'MHD gespeichert.' });
      this._updateShoppingState({ status: 'MHD gespeichert.' });
      await this._loadShoppingList({ silent: true });
    }, {
      onError: (message) => {
        this._updateShoppingState({ status: `Fehler: ${message}` });
      },
    });
  }

  async _resetMhd() {
    const { mhdModal } = this._store.getState().shopping;
    if (!mhdModal.itemId) return;

    this._updateShoppingState({ status: 'Setze MHD zurück…' });
    await this._runRequest(async () => {
      const api = await this._getDashboardApiOrThrow();
      const { response, payload } = await api.resetShoppingListItemBestBefore(mhdModal.itemId);
      if (!response.ok) throw new Error(getErrorMessage(payload, 'MHD konnte nicht zurückgesetzt werden.'));
      this._closeMhdModal();
      this._store.patch({ topbarStatus: 'MHD zurückgesetzt.' });
      this._updateShoppingState({ status: 'MHD zurückgesetzt.' });
      await this._loadShoppingList({ silent: true });
    }, {
      onError: (message) => {
        this._updateShoppingState({ status: `Fehler: ${message}` });
      },
    });
  }

  async _incrementShoppingItem(itemId) {
    await this._runShoppingItemAction({
      itemId,
      statusText: 'Menge wird erhöht…',
      successText: 'Menge erhöht.',
      request: async () => (await this._getDashboardApiOrThrow()).incrementShoppingItemAmount(itemId),
    });
  }

  async _completeShoppingItem(itemId) {
    await this._runShoppingItemAction({
      itemId,
      statusText: 'Eintrag wird abgeschlossen…',
      successText: 'Eintrag abgeschlossen.',
      request: async () => (await this._getDashboardApiOrThrow()).completeShoppingListItem(itemId),
    });
  }

  async _deleteShoppingItem(itemId) {
    await this._runShoppingItemAction({
      itemId,
      statusText: 'Eintrag wird gelöscht…',
      successText: 'Eintrag gelöscht.',
      request: async () => (await this._getDashboardApiOrThrow()).deleteShoppingListItem(itemId),
    });
  }

  async _completeAllShopping() {
    this._updateShoppingState({ status: 'Schließe Einkauf ab…' });
    await this._runRequest(async () => {
      const api = await this._getDashboardApiOrThrow();
      const { response, payload } = await api.completeShoppingList();
      if (!response.ok) throw new Error(getErrorMessage(payload, 'Einkauf konnte nicht abgeschlossen werden.'));
      this._store.patch({ topbarStatus: 'Einkauf abgeschlossen.' });
      this._updateShoppingState({ status: 'Einkauf abgeschlossen.' });
      await this._loadShoppingList({ silent: true });
    }, {
      onError: (message) => {
        this._updateShoppingState({ status: `Fehler: ${message}` });
      },
    });
  }

  async _clearAllShopping() {
    this._updateShoppingState({ status: 'Leere Einkaufsliste…' });
    await this._runRequest(async () => {
      const api = await this._getDashboardApiOrThrow();
      const { response, payload } = await api.clearShoppingList();
      if (!response.ok) throw new Error(getErrorMessage(payload, 'Einkaufsliste konnte nicht geleert werden.'));
      this._store.patch({ topbarStatus: 'Einkaufsliste geleert.' });
      this._updateShoppingState({ status: 'Einkaufsliste geleert.' });
      await this._loadShoppingList({ silent: true });
    }, {
      onError: (message) => {
        this._updateShoppingState({ status: `Fehler: ${message}` });
      },
    });
  }

  async _runShoppingItemAction({ statusText, successText, request }) {
    this._updateShoppingState({ status: statusText });
    await this._runRequest(async () => {
      const { response, payload } = await request();
      if (!response.ok) throw new Error(getErrorMessage(payload, successText));
      this._store.patch({ topbarStatus: successText });
      this._updateShoppingState({ status: successText });
      await this._loadShoppingList({ silent: true });
    }, {
      onError: (message) => {
        this._updateShoppingState({ status: `Fehler: ${message}` });
      },
    });
  }

  _setScannerOpen(open) {
    this._store.updateIn(['shopping', 'scanner'], (scannerState = {}) => ({
      ...scannerState,
      open: Boolean(open),
    }));
    const shoppingState = this._store.getState().shopping;
    this._updateTabViewState('shopping', {
      editing: Boolean(open || shoppingState.detailModal.open || shoppingState.mhdModal.open),
    });
    this._syncShoppingPolling();
  }

  _openScannerBridge() {
    this._switchTab('shopping', { syncHistory: true, announce: false });
    this._setScannerOpen(true);
    this._updateTabViewState('shopping', { editing: true });
    this._store.patch({ topbarStatus: 'Scanner geöffnet.' });
  }

  _updateScannerStatus(message) {
    if (!this._store.getState().shopping.scanner.open) return;
    this._store.updateIn(['shopping', 'scanner'], (scannerState = {}) => ({
      ...scannerState,
      status: String(message || 'Scanner bereit.'),
    }));
    this._store.patch({ topbarStatus: String(message || 'Scanner bereit.') });
  }

  async _handleScannerDetection(detail) {
    if (this._store.getState().shopping.scanner.scope !== 'shopping') return;
    const productName = String(detail?.productName || '').trim();
    if (!productName) return;

    this._setScannerOpen(false);
    this._updateTabViewState('shopping', { editing: false });
    this._store.patch({ topbarStatus: `Scanner erkennt ${productName}. Übergabe an Einkauf…` });

    await this._runRequest(async () => {
      await this._getDashboardApiOrThrow();
      const result = await this._shoppingSearch.actions.searchSuggestedProduct(productName, {
        amount: detail?.amount || 1,
      });
      const searchState = this._shoppingSearch.getState();
      this._store.patch({ topbarStatus: searchState.errorMessage || searchState.statusMessage });
      if (!result.ok && searchState.errorMessage) {
        throw new Error(searchState.errorMessage);
      }
    }, {
      onError: () => {},
    });
  }

  _startShoppingPolling() {
    if (!Number.isFinite(this._shoppingPollIntervalMs) || this._shoppingPollIntervalMs <= 0) {
      this._stopShoppingPolling();
      return;
    }
    if (!this._canPollShopping({ requireNoTimer: true })) return;
    const timer = window.setInterval(() => {
      if (!this._canPollShopping({ requireNoTimer: false })) return;
      this._loadShoppingList({ silent: true });
    }, this._shoppingPollIntervalMs);
    this._updateShoppingState({ pollTimer: timer });
  }

  _stopShoppingPolling() {
    const timer = this._store.getState().shopping.pollTimer;
    if (!timer) return;
    window.clearInterval(timer);
    this._updateShoppingState({ pollTimer: null });
  }


  _applyRouteState(options = {}) {
    const nextTab = this._resolveTabFromRoute();
    if (!nextTab || nextTab === this._store.getState().activeTab) return;
    this._switchTab(nextTab, options);
  }

  _resolveTabFromRoute() {
    const locationPath = window.location?.pathname || '';
    return (
      readTabFromSearch(this._route?.search)
      || readTabFromHash(this._route?.hash)
      || readTabFromPath(this._route?.path)
      || readTabFromSearch(window.location?.search)
      || readTabFromHash(window.location?.hash)
      || readTabFromPath(locationPath)
      || 'shopping'
    );
  }

  _resolveShoppingPollingInterval() {
    const configuredValue = this._getPanelConfig().dashboard_polling_interval_seconds
      ?? this._hass?.states?.['sensor.grocy_ai_status']?.attributes?.dashboard_polling_interval_seconds
      ?? DEFAULT_POLLING_INTERVAL_SECONDS;
    const value = Number(configuredValue);
    if (!Number.isFinite(value) || value < 0) return DEFAULT_POLLING_INTERVAL_MS;
    if (value === 0) return null;
    return value * 1000;
  }

  _getHomeAssistantAccessToken() {
    const directToken = this._hass?.auth?.data?.accessToken;
    if (directToken) return directToken;

    const connectionToken = this._hass?.connection?.options?.auth?.accessToken;
    if (connectionToken) return connectionToken;

    return '';
  }

  _getHomeAssistantAuthHeaders() {
    const accessToken = this._getHomeAssistantAccessToken();
    return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
  }

  _getPanelConfig() {
    return this._panel?.config ?? {};
  }

  _getLegacyDashboardEmergencyUrl() {
    return this._getPanelConfig().legacy_dashboard_emergency_url
      || this._getPanelConfig().legacy_dashboard_url
      || DEFAULT_LEGACY_URL;
  }

  _getResolvedLegacyDashboardEmergencyUrl() {
    return buildLegacyDashboardUrl(this._dashboardApiBasePath, this._getLegacyDashboardEmergencyUrl());
  }

  _getPanelPath() {
    return this._getPanelConfig().panel_path || `/${PANEL_SLUG}`;
  }

  _getPanelIcon() {
    return this._getPanelConfig().panel_icon || PANEL_ICON;
  }

  _openLegacyDashboard(tab) {
    const url = new URL(this._getResolvedLegacyDashboardEmergencyUrl(), window.location.origin);
    if (tab) {
      url.hash = `tab=${tab}`;
    }
    window.location.assign(url.toString());
  }

  async _runRequest(callback, { onError } = {}) {
    this._store.update((state) => ({ ...state, pendingRequests: state.pendingRequests + 1 }));
    try {
      await callback();
    } catch (error) {
      onError?.(error.message);
      this._store.patch({ topbarStatus: `Fehler: ${error.message}` });
    } finally {
      this._store.update((state) => ({ ...state, pendingRequests: Math.max(0, state.pendingRequests - 1) }));
    }
  }
}

registerCustomElement('grocy-ai-topbar', GrocyAITopbar);
registerCustomElement('grocy-ai-tab-nav', GrocyAITabNav);
registerCustomElement('grocy-ai-shopping-search-bar', GrocyAIShoppingSearchBar);
registerCustomElement('grocy-ai-shopping-tab', GrocyAIShoppingTab);
registerCustomElement('grocy-ai-recipes-tab', GrocyAIRecipesTab);
registerCustomElement('grocy-ai-storage-tab', GrocyAIStorageTab);
registerCustomElement('grocy-ai-notifications-tab', GrocyAINotificationsTab);
registerCustomElement('grocy-ai-dashboard-modals', GrocyAIDashboardModals);
registerCustomElement('grocy-ai-scanner-bridge', GrocyAIScannerBridge);
registerCustomElement('grocy-ai-dashboard-panel', GrocyAIDashboardPanel);
