import { createDashboardApiClient, getErrorMessage } from './dashboard-api-client.js';
import { createDashboardStore } from './dashboard-store.js';
import { buildPanelUrlWithTab, DEFAULT_TAB, resolveTabFromLocation, TAB_ORDER } from './tab-routing.js';
import { createShoppingSearchController, SEARCH_FLOW_STATES } from './shopping-search-controller.js';

const PANEL_SLUG = 'grocy-ai';
const PANEL_TITLE = 'Grocy AI';
const PANEL_ICON = 'mdi:brain';
const DEFAULT_LEGACY_URL = '/api/hassio_ingress/grocy_ai_assistant/';
const STYLE_URL = new URL('./grocy-ai-dashboard.css', import.meta.url);
const MIGRATED_TABS = new Set(['shopping']);
const TAB_LABELS = {
  shopping: '🛒 Einkauf',
  recipes: '🍳 Rezepte',
  storage: '📦 Lager',
  notifications: '🔔 Benachrichtigungen',
};
const DEFAULT_POLLING_INTERVAL_MS = 5000;


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

function buildPanelTabHref(panelPath, tab) {
  const path = String(panelPath || `/${PANEL_SLUG}`) || `/${PANEL_SLUG}`;
  if (!normalizeTabName(tab)) return path;
  if (tab === 'shopping') return path;
  return `${path}?tab=${tab}`;
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

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function formatAmount(value) {
  const normalized = String(value ?? '').trim();
  return normalized || '1';
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

function createInitialState() {
  return {
    activeTab: DEFAULT_TAB,
    topbarStatus: 'Bereit.',
    pendingRequests: 0,
    shopping: {
      status: 'Bereit.',
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
      scannerModalOpen: false,
    },
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
          <div>
            <p class="eyebrow">Grocy AI Assistant</p>
            <h1>${PANEL_TITLE}</h1>
            <p class="topbar-path-hint">Native Panel-URL: <code>${escapeHtml(model.panelPath)}</code> · Icon: <code>${escapeHtml(model.panelIcon || PANEL_ICON)}</code></p>
          </div>
          <div class="topbar-meta">
            <p class="topbar-status" aria-live="polite">${escapeHtml(model.status)}</p>
            <span class="activity-spinner${model.busy ? '' : ' hidden'}" aria-label="Lädt"></span>
            <span class="migration-chip">${model.migratedCount}/${model.totalCount} Tabs nativ</span>
          </div>
        </div>
        <div class="topbar-quicklinks" aria-label="Schnellaktionen">
          ${TAB_ORDER.map((tab) => `
            <a
              class="quicklink-button${model.activeTab === tab ? ' active' : ''}"
              href="${escapeHtml(buildPanelTabHref(model.panelPath, tab))}"
            >${TAB_LABELS[tab]}</a>
          `).join('')}
          <button type="button" class="ghost-button" data-action="shopping-open-scanner">📷 Scanner</button>
        </div>
      </header>
    `;
  }
}

class GrocyAITabNav extends HTMLElement {
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
  }

  set viewModel(value) {
    this._viewModel = value;
    this._render();
  }

  _render() {
    const model = this._viewModel || { activeTab: 'shopping' };
    this.innerHTML = `
      <nav class="bottom-tabbar" aria-label="Navigation">
        ${TAB_ORDER.map((tab) => `
          <button
            type="button"
            class="tab-button${model.activeTab === tab ? ' active' : ''}"
            data-tab="${tab}"
          >${TAB_LABELS[tab]}${MIGRATED_TABS.has(tab) ? '' : ' · Fallback'}</button>
        `).join('')}
      </nav>
    `;
  }
}

class GrocyAIShoppingSearchBar extends HTMLElement {
  constructor() {
    super();
    this._viewModel = {};
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

  _render() {
    const model = this._viewModel || {};
    const variants = Array.isArray(model.variants) ? model.variants : [];
    const searchUiState = deriveSearchUiState(model);
    const stateLabel = getSearchStateLabel(searchUiState);
    const helperText = model.errorMessage || model.statusMessage || 'Bereit.';
    const hasVisibleVariants = variants.length > 0;

    this.innerHTML = `
      <section class="shopping-search-shell shopping-search-shell--${searchUiState}" aria-live="polite">
        <div class="shopping-search-shell__header">
          <div>
            <p class="eyebrow">Produktsuche</p>
            <h3 class="shopping-search-shell__title">Produkt suchen oder Variante wählen</h3>
          </div>
          <span class="search-state-chip search-state-chip--${searchUiState}">${escapeHtml(stateLabel)}</span>
        </div>
        <form class="search-row shopping-search-form" data-role="shopping-search-form" aria-busy="${model.isSubmitting ? 'true' : 'false'}">
          <div class="search-input-wrapper">
            <input
              data-role="shopping-query"
              value="${escapeHtml(model.query || '')}"
              placeholder="z.B. 2 Hafermilch"
              autocomplete="off"
              enterkeyhint="search"
              aria-describedby="shopping-search-helper"
            />
            <button class="clear-input-button${model.clearButtonVisible ? ' visible' : ''}" type="button" data-action="shopping-clear-query" aria-label="Sucheingabe löschen">×</button>
          </div>
          <button class="primary-button search-submit-button" type="submit" ${model.isSubmitting ? 'disabled' : ''}>
            ${model.isSubmitting ? 'Prüfe…' : 'Produkt prüfen'}
          </button>
        </form>
        <p id="shopping-search-helper" class="search-helper-text${model.errorMessage ? ' search-helper-text--error' : ''}">
          ${escapeHtml(helperText)}
        </p>
        <section class="variant-section${hasVisibleVariants || model.isLoadingVariants ? '' : ' hidden'}">
          <div class="section-header section-header-stacked">
            <div>
              <h3>Gefundene Produktvarianten</h3>
              ${model.parsedAmount
                ? `<p class="muted">Erkannte Menge: ${escapeHtml(formatAmount(model.parsedAmount))}</p>`
                : '<p class="muted">Live-Vorschläge erscheinen direkt unter dem Eingabefeld.</p>'}
            </div>
            ${model.isLoadingVariants ? '<span class="muted">Suche läuft…</span>' : ''}
          </div>
          <div class="variant-grid variant-grid--search" role="list">
            ${hasVisibleVariants
              ? variants.map((variant) => {
                  const variantName = variant.product_name || variant.name || 'Unbekanntes Produkt';
                  const variantAmountValue = model.parsedAmount || variant.amount || variant.default_amount || '1';
                  const variantAmountLabel = formatAmount(variantAmountValue);
                  const variantSource = variant.source || 'grocy';
                  const sourceLabel = variantSource === 'ai'
                    ? 'KI-Vorschlag'
                    : (variantSource === 'input' ? 'Neu anlegen' : 'Grocy');
                  return `
                    <article class="variant-card variant-card--action" role="listitem">
                      <button
                        class="variant-card__button"
                        type="button"
                        data-action="shopping-select-variant"
                        data-product-id="${escapeHtml(variant.product_id || variant.id || '')}"
                        data-product-name="${escapeHtml(variantName)}"
                        data-product-source="${escapeHtml(variantSource)}"
                        data-amount="${escapeHtml(variantAmountValue)}"
                      >
                        <div class="variant-card__header">
                          <strong>${escapeHtml(variantName)}</strong>
                          <span class="variant-amount-badge">${escapeHtml(variantAmountLabel)}</span>
                        </div>
                        <div class="variant-card__meta">
                          <span class="muted">${escapeHtml(sourceLabel)}</span>
                          <span class="variant-card__cta">Auswählen</span>
                        </div>
                      </button>
                    </article>
                  `;
                }).join('')
              : '<p class="muted">Lade Vorschläge…</p>'}
          </div>
        </section>
      </section>
    `;
  }
}

class GrocyAIShoppingTab extends HTMLElement {
  set viewModel(value) {
    this._viewModel = value;
    this._render();
  }

  _render() {
    const model = this._viewModel || {};
    const variants = Array.isArray(model.variants) ? model.variants : [];
    const items = Array.isArray(model.list) ? model.list : [];

    this.innerHTML = `
      <section class="tab-view${model.active ? '' : ' hidden'}">
        <section class="card hero-card shopping-hero-card">
          <div class="section-header">
            <h2>Grocy AI Suche</h2>
            <button class="scanner-popup-button" type="button" data-action="shopping-open-scanner" aria-label="Barcode-Scanner öffnen">
              <span class="scanner-barcode-icon" aria-hidden="true"></span>
            </button>
          </div>
          <grocy-ai-shopping-search-bar></grocy-ai-shopping-search-bar>
        </section>

        <section class="card shopping-list-section">
          <div class="section-header section-header-stacked">
            <h2>Einkaufsliste</h2>
            <button class="primary-button" type="button" data-action="shopping-refresh">Aktualisieren</button>
          </div>
          <ul class="shopping-list-native">
            ${items.length
              ? items.map((item) => `
                  <li class="shopping-item-card">
                    <div class="shopping-item-card__content">
                      <div>
                        <strong>${escapeHtml(item.product_name || 'Unbekanntes Produkt')}</strong>
                        <div class="muted">Menge: ${escapeHtml(formatAmount(item.amount))}</div>
                        <div class="muted">${escapeHtml(item.note || 'Keine Notiz')}</div>
                      </div>
                      <div class="shopping-item-card__actions">
                        <button class="ghost-button" type="button" data-action="shopping-open-detail" data-item-id="${escapeHtml(item.id)}">Details</button>
                        <button class="ghost-button" type="button" data-action="shopping-open-mhd" data-item-id="${escapeHtml(item.id)}">MHD</button>
                        <button class="ghost-button" type="button" data-action="shopping-increment-item" data-item-id="${escapeHtml(item.id)}">+1</button>
                        <button class="success-button" type="button" data-action="shopping-complete-item" data-item-id="${escapeHtml(item.id)}">Erledigt</button>
                        <button class="danger-button" type="button" data-action="shopping-delete-item" data-item-id="${escapeHtml(item.id)}">Löschen</button>
                      </div>
                    </div>
                  </li>
                `).join('')
              : `<li class="muted">${escapeHtml(model.listLoading ? 'Einkaufsliste wird geladen…' : 'Keine Einträge.')}</li>`}
          </ul>
          <p class="tab-status">${escapeHtml(model.status || 'Bereit.')}</p>
          <div class="button-row">
            <button class="success-button" type="button" data-action="shopping-complete-all">Einkauf abschließen</button>
            <button class="danger-button" type="button" data-action="shopping-clear-all">Einkaufsliste leeren</button>
          </div>
        </section>
      </section>
    `;

    this.querySelector('grocy-ai-shopping-search-bar').viewModel = {
      ...model,
      variants,
    };
  }
}

class GrocyAILegacyBridgeTab extends HTMLElement {
  set viewModel(value) {
    this._viewModel = value;
    this._render();
  }

  _render() {
    const model = this._viewModel || {};
    const shouldMountIframe = Boolean(model.active);
    this.innerHTML = `
      <section class="tab-view${model.active ? '' : ' hidden'}">
        <section class="card legacy-bridge-card">
          <div class="section-header section-header-stacked">
            <div>
              <p class="eyebrow">Tabweise Migration</p>
              <h2>${escapeHtml(model.title || 'Dashboard-Bereich')}</h2>
            </div>
            <button type="button" class="primary-button" data-action="open-legacy-dashboard">Legacy-Dashboard öffnen</button>
          </div>
          <p class="description">
            Dieser Bereich ist bereits als eigene Frontend-Komponente gekapselt, rendert Inhalte aber vorübergehend weiter über das bestehende
            Dashboard, bis alle Zustände, Polling-Flows, Modals und Scanner-Funktionen nativ migriert sind.
          </p>
          <div class="migration-checklist">
            <span class="migration-chip">Store-angebunden</span>
            <span class="migration-chip">Tab-spezifische Bridge</span>
            <span class="migration-chip">Legacy-Fallback aktiv</span>
          </div>
          <div class="legacy-frame-shell${shouldMountIframe ? '' : ' hidden'}">
            ${shouldMountIframe ? `<iframe class="legacy-frame" title="${escapeHtml(model.title || 'Legacy Dashboard')}" src="${escapeHtml(model.legacyUrl || DEFAULT_LEGACY_URL)}"></iframe>` : ''}
          </div>
        </section>
      </section>
    `;

    const frame = this.querySelector('iframe');
    frame?.addEventListener('load', () => {
      try {
        frame.contentWindow?.switchTab?.(model.tabName);
      } catch (_) {
        // Same-origin is expected, but silently tolerate fallback cases.
      }
    }, { once: true });

    this.querySelector('[data-action="open-legacy-dashboard"]')?.addEventListener('click', () => {
      this.dispatchEvent(new CustomEvent('open-legacy-dashboard', {
        bubbles: true,
        composed: true,
        detail: { tab: model.tabName },
      }));
    });
  }
}

class GrocyAIDashboardModals extends HTMLElement {
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
      if (!field) return;
      this.dispatchEvent(new CustomEvent('shopping-modal-input', {
        bubbles: true,
        composed: true,
        detail: {
          field: field.dataset.field,
          value: field.value,
        },
      }));
    });
  }

  set viewModel(value) {
    this._viewModel = value;
    this._render();
  }

  _render() {
    const model = this._viewModel || {};
    const detail = model.detailModal || { open: false };
    const mhd = model.mhdModal || { open: false };
    const item = model.activeItem || null;

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
    `;
  }
}

class GrocyAIScannerBridge extends HTMLElement {
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
    const model = this._viewModel || { open: false };
    this.innerHTML = `
      <div class="shopping-modal${model.open ? '' : ' hidden'}">
        <div class="shopping-modal-backdrop" data-action="shopping-close-scanner"></div>
        <section class="shopping-modal-content card scanner-bridge-content">
          <button class="shopping-modal-close" type="button" data-action="shopping-close-scanner" aria-label="Scanner schließen">×</button>
          <h3>Scanner-Bridge</h3>
          <p class="description">
            Scanner und Kamera-Workflows bleiben während der schrittweisen Migration zunächst im bisherigen Dashboard aktiv.
            So bleiben Polling, Barcode-Erkennung, LLaVA-Trigger und Produktanlage unverändert verfügbar.
          </p>
          <div class="button-row">
            <button class="primary-button" type="button" data-action="open-legacy-dashboard">Legacy-Dashboard öffnen</button>
            <button class="ghost-button" type="button" data-action="shopping-close-scanner">Schließen</button>
          </div>
        </section>
      </div>
    `;
  }
}

class GrocyAIRecipesTab extends GrocyAILegacyBridgeTab {}

class GrocyAIStorageTab extends GrocyAILegacyBridgeTab {}

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
    this._store = createDashboardStore(createInitialState());
    this._api = createDashboardApiClient({ apiBasePath: this._getLegacyDashboardUrl() });
    this._handlePopState = () => this._syncActiveTabFromLocation({ updateUrl: false });
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
    this._unsubscribe = this._store.subscribe((state) => this._renderState(state));
    this._applyRouteState({ syncHistory: false, announce: false });
    this._syncActiveTabFromLocation({ replaceUrl: true });
    this._searchUnsubscribe = this._shoppingSearch.subscribe(() => this._renderState(this._store.getState()));
    this._loadShoppingList();
  }

  disconnectedCallback() {
    this._unsubscribe?.();
    window.removeEventListener('popstate', this._handlePopState);
    this._searchUnsubscribe?.();
    this._shoppingSearch.dispose();
    this._stopShoppingPolling();
  }

  set hass(value) {
    this._hass = value;
    this._shoppingPollIntervalMs = this._resolveShoppingPollingInterval();
    this._renderState(this._store.getState());
  }

  set route(value) {
    this._route = value;
    this._applyRouteState({ syncHistory: false, announce: false });
    this._syncActiveTabFromLocation({ replaceUrl: true });
    this._renderState(this._store.getState());
  }

  set panel(value) {
    this._panel = value;
    this._api = createDashboardApiClient({ apiBasePath: this._getLegacyDashboardUrl() });
    this._shoppingSearch.setApi(this._api);
    this._renderState(this._store.getState());
  }

  set narrow(value) {
    this._narrow = Boolean(value);
    this._renderState(this._store.getState());
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
    root.addEventListener('open-legacy-dashboard', (event) => this._openLegacyDashboard(event.detail?.tab));
  }

  _renderState(state) {
    this._ensureShell();
    if (!this.shadowRoot) return;

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
    const migratedCount = MIGRATED_TABS.size;
    const totalCount = TAB_ORDER.length;
    const topbarStatus = state.pendingRequests > 0 && searchState.flowState === SEARCH_FLOW_STATES.SUBMITTING
      ? searchState.statusMessage
      : state.topbarStatus;
    topbar.viewModel = {
      status: topbarStatus,
      busy: state.pendingRequests > 0,
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
    };
    recipesTab.viewModel = {
      active: state.activeTab === 'recipes',
      title: 'Rezepte',
      tabName: 'recipes',
      legacyUrl: this._getLegacyDashboardUrl(),
    };
    storageTab.viewModel = {
      active: state.activeTab === 'storage',
      title: 'Lager',
      tabName: 'storage',
      legacyUrl: this._getLegacyDashboardUrl(),
    };
    notificationsTab.viewModel = {
      active: state.activeTab === 'notifications',
      title: 'Benachrichtigungen',
      tabName: 'notifications',
      legacyUrl: this._getLegacyDashboardUrl(),
    };

    const activeItem = state.shopping.list.find((item) => String(item.id) === String(state.shopping.detailModal.itemId))
      || state.shopping.list.find((item) => String(item.id) === String(state.shopping.mhdModal.itemId))
      || null;
    modals.viewModel = {
      detailModal: state.shopping.detailModal,
      mhdModal: state.shopping.mhdModal,
      activeItem,
    };
    scannerBridge.viewModel = {
      open: state.shopping.scannerModalOpen,
    };
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

    if (normalizedTab === DEFAULT_TAB) {
      this._startShoppingPolling();
      if (!this._store.getState().shopping.listLoaded) {
        this._loadShoppingList();
      }
    } else {
      this._stopShoppingPolling();
    }
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
    this._store.update((state) => ({
      ...state,
      shopping: {
        ...state.shopping,
        ...partial,
      },
    }));
  }

  _updateShoppingQuery(query) {
    this._shoppingSearch.actions.setQuery(query);
  }

  _clearShoppingQuery() {
    this._shoppingSearch.actions.clearQuery();
  }

  async _submitShoppingQuery() {
    await this._runRequest(async () => {
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
    await this._runRequest(async () => {
      const { response, payload } = await this._api.fetchShoppingList();
      if (!response.ok) throw new Error(getErrorMessage(payload, 'Einkaufsliste konnte nicht geladen werden.'));
      this._updateShoppingState({
        list: Array.isArray(payload) ? payload : [],
        listLoading: false,
        listLoaded: true,
        status: 'Einkaufsliste aktualisiert.',
      });
      this._store.patch({ topbarStatus: 'Einkaufsliste aktualisiert.' });
      this._startShoppingPolling();
    }, {
      onError: (message) => {
        this._updateShoppingState({ listLoading: false, status: `Fehler: ${message}` });
      },
    });
  }


  _openShoppingDetail(itemId) {
    const item = this._store.getState().shopping.list.find((entry) => String(entry.id) === String(itemId));
    if (!item) return;
    this._updateShoppingState({
      detailModal: {
        open: true,
        itemId: item.id,
        amount: formatAmount(item.amount),
        note: item.note || '',
      },
    });
  }

  _closeShoppingDetail() {
    this._updateShoppingState({
      detailModal: {
        open: false,
        itemId: null,
        amount: '',
        note: '',
      },
    });
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
      const amountRequest = this._api.updateShoppingListItemAmount(detailModal.itemId, detailModal.amount);
      const noteRequest = this._api.updateShoppingListItemNote(detailModal.itemId, detailModal.note || '');
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
    this._updateShoppingState({
      mhdModal: {
        open: true,
        itemId: item.id,
        value: item.best_before_date || '',
      },
    });
  }

  _closeMhdModal() {
    this._updateShoppingState({
      mhdModal: {
        open: false,
        itemId: null,
        value: '',
      },
    });
  }

  async _saveMhd() {
    const { mhdModal } = this._store.getState().shopping;
    if (!mhdModal.itemId) return;

    this._updateShoppingState({ status: 'Speichere MHD…' });
    await this._runRequest(async () => {
      const { response, payload } = await this._api.updateShoppingListItemBestBefore(mhdModal.itemId, mhdModal.value);
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
      const { response, payload } = await this._api.resetShoppingListItemBestBefore(mhdModal.itemId);
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
      request: () => this._api.incrementShoppingItemAmount(itemId),
    });
  }

  async _completeShoppingItem(itemId) {
    await this._runShoppingItemAction({
      itemId,
      statusText: 'Eintrag wird abgeschlossen…',
      successText: 'Eintrag abgeschlossen.',
      request: () => this._api.completeShoppingListItem(itemId),
    });
  }

  async _deleteShoppingItem(itemId) {
    await this._runShoppingItemAction({
      itemId,
      statusText: 'Eintrag wird gelöscht…',
      successText: 'Eintrag gelöscht.',
      request: () => this._api.deleteShoppingListItem(itemId),
    });
  }

  async _completeAllShopping() {
    this._updateShoppingState({ status: 'Schließe Einkauf ab…' });
    await this._runRequest(async () => {
      const { response, payload } = await this._api.completeShoppingList();
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
      const { response, payload } = await this._api.clearShoppingList();
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
    this._updateShoppingState({ scannerModalOpen: Boolean(open) });
  }

  _openScannerBridge() {
    this._switchTab('shopping', { syncHistory: true, announce: false });
    this._setScannerOpen(true);
    this._store.patch({ topbarStatus: 'Scanner-Bridge geöffnet.' });
  }

  _startShoppingPolling() {
    const state = this._store.getState();
    if (state.activeTab !== 'shopping' || state.shopping.pollTimer) return;
    const timer = window.setInterval(() => {
      const latestState = this._store.getState();
      if (latestState.activeTab !== 'shopping') return;
      if (latestState.shopping.detailModal.open || latestState.shopping.mhdModal.open || latestState.shopping.scannerModalOpen) return;
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
    const value = Number(this._hass?.states?.['sensor.grocy_ai_status']?.attributes?.dashboard_polling_interval_seconds ?? 5);
    if (!Number.isFinite(value) || value < 1) return DEFAULT_POLLING_INTERVAL_MS;
    return value * 1000;
  }

  _getPanelConfig() {
    return this._panel?.config ?? {};
  }

  _getLegacyDashboardUrl() {
    return this._getPanelConfig().legacy_dashboard_url || DEFAULT_LEGACY_URL;
  }

  _getPanelPath() {
    return this._getPanelConfig().panel_path || `/${PANEL_SLUG}`;
  }

  _getPanelIcon() {
    return this._getPanelConfig().panel_icon || PANEL_ICON;
  }

  _openLegacyDashboard(tab) {
    const url = new URL(this._getLegacyDashboardUrl(), window.location.origin);
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
