import { createDashboardApiClient, getErrorMessage } from './dashboard-api-client.js';
import { buildLegacyDashboardUrl, resolveDashboardApiBasePath } from './panel-api-base-path.js';
import { createDashboardStore } from './dashboard-store.js';
import { buildPanelUrlWithTab, DEFAULT_TAB, resolveTabFromLocation, TAB_ORDER } from './tab-routing.js';
import { createShoppingSearchController, SEARCH_FLOW_STATES } from './shopping-search-controller.js';
import { escapeHtml, formatAmount, renderShoppingListItemCard, renderShoppingVariantCard, resolveShoppingImageSource } from './shopping-ui.js';

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
    const article = document.createElement('article');
    article.className = 'variant-card variant-card--action';
    article.setAttribute('role', 'listitem');

    const button = document.createElement('button');
    button.className = 'variant-card__button';
    button.type = 'button';
    button.dataset.action = 'shopping-select-variant';

    const variantName = variant.product_name || variant.name || 'Unbekanntes Produkt';
    const variantAmountValue = parsedAmount || variant.amount || variant.default_amount || '1';
    const variantAmountLabel = formatAmount(variantAmountValue);
    const variantSource = variant.source || 'grocy';
    const sourceLabel = variantSource === 'ai'
      ? 'KI-Vorschlag'
      : (variantSource === 'input' ? 'Neu anlegen' : 'Grocy');

    button.dataset.productId = String(variant.product_id || variant.id || '');
    button.dataset.productName = String(variantName);
    button.dataset.productSource = String(variantSource);
    button.dataset.amount = String(variantAmountValue);
    button.addEventListener('click', () => {
      this.dispatchEvent(new CustomEvent('shopping-select-variant', {
        bubbles: true,
        composed: true,
        detail: { ...button.dataset },
      }));
    });

    const header = document.createElement('div');
    header.className = 'variant-card__header';
    const strong = document.createElement('strong');
    strong.textContent = variantName;
    const badge = document.createElement('span');
    badge.className = 'variant-amount-badge';
    badge.textContent = variantAmountLabel;
    header.append(strong, badge);

    const meta = document.createElement('div');
    meta.className = 'variant-card__meta';
    const source = document.createElement('span');
    source.className = 'muted';
    source.textContent = sourceLabel;
    const cta = document.createElement('span');
    cta.className = 'variant-card__cta';
    cta.textContent = 'Auswählen';
    meta.append(source, cta);

    button.append(header, meta);
    article.append(button);
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
  }

  connectedCallback() {
    this.addEventListener('click', (event) => {
      const actionTarget = event.target.closest?.('[data-action]');
      if (!actionTarget) return;
      this.dispatchEvent(new CustomEvent(actionTarget.dataset.action, {
        bubbles: true,
        composed: true,
        detail: { ...actionTarget.dataset },
      }));
    });
  }

  set viewModel(value) {
    this._viewModel = value;
    this._render();
  }

  _ensureStructure() {
    if (this._elements) return;

    const root = document.createElement('section');

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

  _createShoppingListItem(item) {
    const listItem = document.createElement('li');
    listItem.className = 'shopping-item-card';

    const content = document.createElement('div');
    content.className = 'shopping-item-card__content';
    const details = document.createElement('div');
    const title = document.createElement('strong');
    title.textContent = item.product_name || 'Unbekanntes Produkt';
    const amount = document.createElement('div');
    amount.className = 'muted';
    amount.textContent = `Menge: ${formatAmount(item.amount)}`;
    const note = document.createElement('div');
    note.className = 'muted';
    note.textContent = item.note || 'Keine Notiz';
    details.append(title, amount, note);

    const actions = document.createElement('div');
    actions.className = 'shopping-item-card__actions';
    [
      ['ghost-button', 'shopping-open-detail', 'Details'],
      ['ghost-button', 'shopping-open-mhd', 'MHD'],
      ['ghost-button', 'shopping-increment-item', '+1'],
      ['success-button', 'shopping-complete-item', 'Erledigt'],
      ['danger-button', 'shopping-delete-item', 'Löschen'],
    ].forEach(([className, action, label]) => {
      const button = document.createElement('button');
      button.className = className;
      button.type = 'button';
      button.dataset.action = action;
      button.dataset.itemId = String(item.id);
      button.textContent = label;
      actions.append(button);
    });

    content.append(details, actions);
    listItem.append(content);
    return listItem;
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
      })),
    });
    if (listSignature === this._lastListSignature) return;
    this._lastListSignature = listSignature;

    if (!items.length) {
      const emptyItem = document.createElement('li');
      emptyItem.className = 'muted';
      emptyItem.textContent = model.listLoading ? 'Einkaufsliste wird geladen…' : 'Keine Einträge.';
      list.replaceChildren(emptyItem);
      return;
    }

    list.replaceChildren(...items.map((item) => this._createShoppingListItem(item)));
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
      this._elements.root.className = `tab-view${model.active ? '' : ' hidden'}`;
      this._elements.status.textContent = model.status || 'Bereit.';
    }

    this._elements.searchBar.viewModel = {
      ...model,
    };
    this._renderList(model, items);
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
    modal.classList.toggle('hidden', !shouldOpen);

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
    this._dashboardApiBasePath = '';
    this._initialDataLoadStarted = false;
    this._apiBasePathPromise = null;
    this._store = createDashboardStore(createInitialState());
    this._api = createDashboardApiClient({ getAuthHeaders: () => this._getHomeAssistantAuthHeaders() });
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
    this._ensureInitialDataLoad();
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
    root.addEventListener('shopping-scanner-status', (event) => this._updateScannerStatus(event.detail?.message));
    root.addEventListener('shopping-scanner-detected', (event) => this._handleScannerDetection(event.detail));
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
    const panelConfig = this._getPanelConfig();
    const panelImageApiBasePath = this._dashboardApiBasePath
      || String(panelConfig?.dashboard_api_base_path || panelConfig?.api_base_path || '').replace(/\/+$/, '');
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
      resolveImageUrl: (url) => resolvePanelImageUrl(url, this._dashboardApi, { apiBasePath: panelImageApiBasePath }),
    };
    recipesTab.viewModel = {
      active: state.activeTab === 'recipes',
      title: 'Rezepte',
      tabName: 'recipes',
      legacyUrl: this._getResolvedLegacyDashboardUrl(),
    };
    storageTab.viewModel = {
      active: state.activeTab === 'storage',
      title: 'Lager',
      tabName: 'storage',
      legacyUrl: this._getResolvedLegacyDashboardUrl(),
    };
    notificationsTab.viewModel = {
      active: state.activeTab === 'notifications',
      title: 'Benachrichtigungen',
      tabName: 'notifications',
      legacyUrl: this._getResolvedLegacyDashboardUrl(),
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
    scannerBridge.api = this._api;
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
    await this._runRequest(async () => {
      const api = await this._getDashboardApiOrThrow();
      const { response, payload } = await api.fetchShoppingList();
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
    this._updateShoppingState({ scannerModalOpen: Boolean(open) });
  }

  _openScannerBridge() {
    this._switchTab('shopping', { syncHistory: true, announce: false });
    this._setScannerOpen(true);
    this._store.patch({ topbarStatus: 'Scanner geöffnet.' });
  }

  _updateScannerStatus(message) {
    if (!this._store.getState().shopping.scannerModalOpen) return;
    this._store.patch({ topbarStatus: String(message || 'Scanner bereit.') });
  }

  async _handleScannerDetection(detail) {
    const productName = String(detail?.productName || '').trim();
    if (!productName) return;

    this._setScannerOpen(false);
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

  _getLegacyDashboardUrl() {
    return this._getPanelConfig().legacy_dashboard_url || DEFAULT_LEGACY_URL;
  }

  _getResolvedLegacyDashboardUrl() {
    return buildLegacyDashboardUrl(this._dashboardApiBasePath, this._getLegacyDashboardUrl());
  }

  _getPanelPath() {
    return this._getPanelConfig().panel_path || `/${PANEL_SLUG}`;
  }

  _getPanelIcon() {
    return this._getPanelConfig().panel_icon || PANEL_ICON;
  }

  _openLegacyDashboard(tab) {
    const url = new URL(this._getResolvedLegacyDashboardUrl(), window.location.origin);
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
