import { createDashboardApiClient, getErrorMessage } from './dashboard-api-client.js';
import { updateBusyIndicator, renderTabSelection, lockBodyScroll as applyBodyScrollLock, unlockBodyScroll as releaseBodyScrollLock } from './dashboard-dom.js';
import { createDashboardStore } from './dashboard-store.js';
import { parseAmountPrefixedSearch, shouldShowClearButton } from './dashboard-shopping-search-helpers.js';
import { formatAmount, formatBadgeValue, formatStockCount, renderShoppingListItemCard, renderShoppingVariantCard } from './panel-frontend/shopping-ui.js';
import { bindSwipeInteractions, resetSwipeVisualState } from './panel-frontend/swipe-interactions.js';

const MIN_PRODUCT_SEARCH_LENGTH = 3;

function getMinimumSearchLengthMessage(length) {
  const remainingCharacters = MIN_PRODUCT_SEARCH_LENGTH - length;
  if (remainingCharacters <= 0) return 'Bereit.';
  return remainingCharacters === 1
    ? 'Noch 1 Buchstabe bis zur Produktsuche.'
    : `Noch ${remainingCharacters} Buchstaben bis zur Produktsuche.`;
}

const rootElement = document.documentElement;
const configuredApiKey = rootElement.dataset.configuredApiKey || '';
const apiBasePath = rootElement.dataset.apiBasePath || '';
const dashboardPollingIntervalSeconds = Number.parseInt(rootElement.dataset.dashboardPollingIntervalSeconds || '5', 10);
const haThemeSource = rootElement.dataset.themeSource || 'home-assistant-parent';
const haThemeBridgeMode = rootElement.dataset.themeBridgeMode || 'same-origin-css-vars';
const haThemeVarNames = (rootElement.dataset.haThemeVars || '')
  .split(',')
  .map((name) => name.trim())
  .filter(Boolean);
let apiKey = configuredApiKey || '';
const ingressPrefixMatch = window.location.pathname.match(/^\/api\/hassio_ingress\/[^\/]+/);
const ingressPrefix = ingressPrefixMatch ? ingressPrefixMatch[0] : '';
const dashboardApi = createDashboardApiClient({
  apiBasePath,
  ingressPrefix,
  getApiKey: () => apiKey,
});
const dashboardStore = createDashboardStore({
  pendingRequests: 0,
  activeRecipeItem: null,
  modalScrollLockY: 0,
  notificationEditingRuleId: null,
  storageProductsCache: [],
  storageEditingItem: null,
  storageEditingTargetId: null,
  storageLocationOptions: [],
  activeTab: 'shopping',
  shoppingListRefreshTimer: null,
  shoppingListRefreshInFlight: false,
  storageRefreshTimer: null,
  storageRefreshInFlight: false,
  storageFilterDebounce: null,
  shoppingListSignature: '',
  variantsRequestToken: 0,
  variantsDebounce: null,
  activeShoppingNoteItemId: null,
  activeShoppingNoteValue: '',
  activeShoppingAmountValue: '',
  activeMhdShoppingListId: null,
  scannerStream: null,
  scannerInterval: null,
  scannerLastBarcode: '',
  scannerDetector: null,
  scannerLastBarcodeAt: 0,
  scannerDetectionInFlight: false,
  scannerStableCandidate: '',
  scannerStableCount: 0,
  scannerLlavaInFlight: false,
  scannerLlavaTimer: null,
  scannerLlavaLastRequestAt: 0,
  scannerFocusRefreshTimer: null,
  scannerPreferredFocusMode: '',
  scannerSelectedDeviceId: '',
  scannerKnownDevices: [],
  scannerScanStartedAt: 0,
  scannerLastLightCheckAt: 0,
  scannerRotationDegrees: 0,
  scannerResultPayload: null,
  scannerCreateInFlight: false,
});
const dashboardState = dashboardStore.state;
const HA_THEME_MESSAGE_TYPE = 'grocy-ai-assistant:ha-theme-sync';
const HA_THEME_SOURCE_SELECTORS = ['home-assistant', 'body', 'html'];
const HA_THEME_VARIABLE_MAPPINGS = {
  '--primary-background-color': '--ha-primary-background-color',
  '--secondary-background-color': '--ha-secondary-background-color',
  '--card-background-color': '--ha-card-background-color',
  '--primary-text-color': '--ha-primary-text-color',
  '--secondary-text-color': '--ha-secondary-text-color',
  '--divider-color': '--ha-divider-color',
  '--primary-color': '--ha-primary-color',
  '--error-color': '--ha-error-color',
  '--success-color': '--ha-success-color',
};

const GROCY_RECIPE_DISPLAY_LIMIT = 3;
const AI_RECIPE_DISPLAY_LIMIT = 3;

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

function renderStorageEditLocationOptions(selectedLocationId = null, fallbackLocationName = '') {
  const select = document.getElementById('storage-edit-location-select');
  if (!select) return;

  const normalizedSelectedId = Number(selectedLocationId);
  const hasSelectedId = Number.isFinite(normalizedSelectedId) && normalizedSelectedId > 0;
  const options = Array.isArray(dashboardState.storageLocationOptions) ? dashboardState.storageLocationOptions : [];

  select.innerHTML = [
    '<option value="">Bitte Lagerort wählen</option>',
    ...options.map((location) => {
      const locationId = Number(location?.id ?? 0);
      const selected = hasSelectedId && locationId === normalizedSelectedId ? ' selected' : '';
      return `<option value="${locationId}"${selected}>${escapeHtml(location?.name || `Lagerort ${locationId}`)}</option>`;
    }),
  ].join('');

  if (hasSelectedId) {
    select.value = String(normalizedSelectedId);
    if (select.value !== String(normalizedSelectedId)) {
      select.innerHTML = `<option value="${normalizedSelectedId}" selected>${escapeHtml(fallbackLocationName || `Lagerort ${normalizedSelectedId}`)}</option>${select.innerHTML}`;
      select.value = String(normalizedSelectedId);
    }
  } else {
    select.value = '';
  }
}

const NOTIFICATION_EVENT_LABELS = {
  item_added: 'Produkt hinzugefügt',
  item_removed: 'Produkt entfernt',
  item_checked: 'Produkt abgehakt',
  item_unchecked: 'Produkt nicht mehr abgehakt',
  shopping_due: 'Einkauf fällig',
  low_stock_detected: 'Niedriger Bestand erkannt',
  recipe_missing_items: 'Rezept hat fehlende Zutaten',
};

const NOTIFICATION_CHANNEL_LABELS = {
  mobile_push: 'Mobile Push-Benachrichtigung',
  persistent_notification: 'Persistente Benachrichtigung',
};

function getEventLabel(eventType) {
  return NOTIFICATION_EVENT_LABELS[eventType] || eventType;
}

function getChannelLabel(channelType) {
  return NOTIFICATION_CHANNEL_LABELS[channelType] || channelType;
}


function inferMobilePlatform(device) {
  const hint = String(device?.platform || '').trim().toLowerCase();
  if (hint === 'android' || hint === 'ios') return hint;
  const raw = `${device?.service || ''} ${device?.display_name || ''}`.toLowerCase();
  if (raw.includes('iphone') || raw.includes('ipad') || raw.includes('ios') || raw.includes('watch')) return 'ios';
  return 'android';
}

function getPlatformIcon(platform) {
  return platform === 'ios' ? '🍎' : '🤖';
}

function getPlatformLabel(platform) {
  return platform === 'ios' ? 'iOS' : 'Android';
}


function normalizeDeviceToken(rawValue) {
  return String(rawValue || '')
    .toLowerCase()
    .replace(/^notify\./, '')
    .replace(/^mobile_app_/, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
}

const NOTIFICATION_MISC_GROUP = 'Sonstige';

function getDeviceCategory(device) {
  const displayToken = normalizeDeviceToken(device?.display_name);
  const serviceToken = normalizeDeviceToken(device?.service);
  const combined = `${displayToken}_${serviceToken}`;

  const patterns = [
    { key: 'pixel_watch', label: 'Pixel Watch' },
    { key: 'pixelwatch', label: 'Pixel Watch' },
    { key: 'pixel', label: 'Pixel' },
    { key: 'iphone', label: 'iPhone' },
    { key: 'ipad', label: 'iPad' },
    { key: 'apple_watch', label: 'Apple Watch' },
    { key: 'applewatch', label: 'Apple Watch' },
    { key: 'samsung', label: 'Samsung' },
    { key: 'galaxy', label: 'Samsung Galaxy' },
  ];

  const directMatch = patterns.find((pattern) => combined.includes(pattern.key));
  if (directMatch) return directMatch.label;

  const normalizedBase = serviceToken || displayToken;
  if (!normalizedBase) return NOTIFICATION_MISC_GROUP;

  const firstParts = normalizedBase.split('_').filter(Boolean).slice(0, 2);
  if (!firstParts.length) return NOTIFICATION_MISC_GROUP;

  return firstParts
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function collapseSingleDeviceGroups(groupedDevices) {
  const collapsedGroups = new Map();
  const miscDevices = [];

  Array.from(groupedDevices.entries()).forEach(([category, devices]) => {
    if (category !== NOTIFICATION_MISC_GROUP && devices.length === 1) {
      miscDevices.push(...devices);
      return;
    }

    collapsedGroups.set(category, devices);
  });

  if (miscDevices.length) {
    const existingMiscDevices = collapsedGroups.get(NOTIFICATION_MISC_GROUP) || [];
    collapsedGroups.set(NOTIFICATION_MISC_GROUP, [...existingMiscDevices, ...miscDevices]);
  }

  return collapsedGroups;
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function renderSelectOptions(selectElement, options, selectedValues = []) {
  if (!selectElement) return;
  const selected = new Set((selectedValues || []).map((value) => String(value)));
  selectElement.innerHTML = options.map((option) => {
    const value = String(option.value);
    const isSelected = selected.has(value) ? ' selected' : '';
    return `<option value="${escapeHtml(value)}"${isSelected}>${escapeHtml(option.label)}</option>`;
  }).join('');
}

function getSelectedValues(selectElement) {
  if (!selectElement) return [];
  return Array.from(selectElement.selectedOptions || [])
    .map((option) => option.value.trim())
    .filter(Boolean);
}

function lockBodyScroll() {
  if (document.body.classList.contains('modal-open')) return;
  dashboardState.modalScrollLockY = window.scrollY || window.pageYOffset || 0;
  applyBodyScrollLock(dashboardState.modalScrollLockY);
}

function unlockBodyScroll() {
  releaseBodyScrollLock(dashboardState.modalScrollLockY);
}

function syncModalScrollLock() {
  const hasVisibleModal = Boolean(document.querySelector('.shopping-modal:not(.hidden)'));
  if (hasVisibleModal) {
    lockBodyScroll();
    return;
  }
  unlockBodyScroll();
}
const scannerDigitalZoomFactor = 1.35;
const scannerStableDetectionThreshold = 2;
const scannerFocusRefreshMs = 2000;
const scannerAnalysisWarmupMs = 1200;
const scannerLightCheckIntervalMs = 1500;
const scannerLightWarningThreshold = 72;
const shoppingListRefreshMs = Math.max(1000, (Number.isFinite(dashboardPollingIntervalSeconds) ? dashboardPollingIntervalSeconds : 5) * 1000);
const recipeState = {
  initialized: false,
  hasLoadedInitialSuggestions: false,
  selectedLocationIds: [],
  selectedProductIds: [],
  stockSignature: null,
};
const recipeCreateState = {
  method: null,
};

function buildStockSignature(items) {
  return JSON.stringify(
    (Array.isArray(items) ? items : [])
      .map((item) => [
        String(item.id ?? ''),
        String(item.name ?? ''),
        String(item.amount ?? ''),
        String(item.location_id ?? ''),
        String(item.location_name ?? ''),
      ])
      .sort((left, right) => left.join('|').localeCompare(right.join('|')))
  );
}

function setBusyState(isBusy) {
  updateBusyIndicator(isBusy);
}

function beginRequest() {
  dashboardState.pendingRequests += 1;
  setBusyState(true);
}

function endRequest() {
  dashboardState.pendingRequests = Math.max(0, dashboardState.pendingRequests - 1);
  setBusyState(dashboardState.pendingRequests > 0);
}

async function withBusyState(callback) {
  beginRequest();
  try {
    return await callback();
  } finally {
    endRequest();
  }
}


function switchTab(tabName) {
  const allowedTabs = ['shopping', 'recipes', 'storage', 'notifications'];
  dashboardState.activeTab = allowedTabs.includes(tabName) ? tabName : 'shopping';
  renderTabSelection(dashboardState.activeTab, allowedTabs);

  if (dashboardState.activeTab === 'recipes' && !recipeState.initialized) {
    loadLocations();
  }
  if (dashboardState.activeTab === 'storage') {
    refreshStorageInBackground();
  }
  if (dashboardState.activeTab === 'notifications') {
    loadNotificationOverview();
  }
  if (dashboardState.activeTab === 'shopping') {
    refreshShoppingListInBackground();
  }

  syncTopbarStatusFromActiveTab();
}


async function openScannerModal() {
  const modal = document.getElementById('scanner-modal');
  if (!modal) return;
  modal.classList.remove('hidden');
  syncModalScrollLock();
  await refreshScannerDevices();
  const rotationSelect = getScannerRotationSelectElement();
  if (rotationSelect) rotationSelect.value = String(dashboardState.scannerRotationDegrees);
}

function closeScannerModal() {
  const modal = document.getElementById('scanner-modal');
  if (!modal) return;
  modal.classList.add('hidden');
  stopBarcodeScanner();
  syncModalScrollLock();
}

function getShoppingStatusElement() {
  return document.getElementById('status-shopping');
}

function getRecipeStatusElement() {
  return document.getElementById('status-recipes');
}

function getNotificationStatusElement() {
  return document.getElementById('status-notifications');
}

async function loadNotificationOverview() {
  const status = getNotificationStatusElement();
  status.textContent = 'Lade Notification-Konfiguration…';
  try {
    const { response, payload } = await dashboardApi.notificationOverview();
    if (!response.ok) throw new Error(getErrorMessage(payload, 'Fehler beim Laden der Notification-Daten.'));

    renderNotificationDevices(payload.devices || []);
    renderNotificationRuleEditorOptions(payload.devices || [], payload.settings || {});
    renderNotificationRules(payload.rules || []);
    renderNotificationHistory(payload.history || []);
    hydrateNotificationSettings(payload.settings || {});
    status.textContent = 'Notification-Konfiguration geladen.';
  } catch (error) {
    status.textContent = `Fehler: ${error.message}`;
  }
}

function renderNotificationRuleEditorOptions(devices, settings) {
  const eventsSelect = document.getElementById('notify-rule-events');
  const deviceSelect = document.getElementById('notify-rule-devices');
  const eventOptions = (settings.enabled_event_types || Object.keys(NOTIFICATION_EVENT_LABELS)).map((eventType) => ({
    value: eventType,
    label: getEventLabel(eventType),
  }));
  const defaultEvents = eventOptions.map((option) => option.value);
  renderSelectOptions(eventsSelect, eventOptions, defaultEvents);

  const deviceOptions = (Array.isArray(devices) ? devices : []).map((device) => ({
    value: device.id,
    label: `${device.display_name} (${device.service} · ${device.platform})`,
  }));
  renderSelectOptions(deviceSelect, deviceOptions, []);
}

function hydrateNotificationSettings(settings) {
  const globalEnabledToggle = document.getElementById('notify-enabled');
  if (globalEnabledToggle) globalEnabledToggle.checked = Boolean(settings.enabled);
  const ruleSeverity = document.getElementById('notify-rule-severity');
  const ruleChannel = document.getElementById('notify-rule-channel');
  if (ruleSeverity) ruleSeverity.value = settings.default_severity || 'info';
  if (ruleChannel) ruleChannel.value = (settings.default_channels || ['mobile_push'])[0] || 'mobile_push';
}

function renderNotificationDevices(devices) {
  const container = document.getElementById('notification-devices');
  if (!Array.isArray(devices) || devices.length === 0) {
    container.innerHTML = '<p class="muted">Keine mobilen Notify-Targets gefunden.</p>';
    return;
  }

  const grouped = devices.reduce((map, device) => {
    const category = getDeviceCategory(device);
    if (!map.has(category)) map.set(category, []);
    map.get(category).push(device);
    return map;
  }, new Map());

  const sortedGroups = Array.from(collapseSingleDeviceGroups(grouped).entries())
    .sort((left, right) => {
      if (left[0] === NOTIFICATION_MISC_GROUP) return 1;
      if (right[0] === NOTIFICATION_MISC_GROUP) return -1;
      return left[0].localeCompare(right[0], 'de', { sensitivity: 'base' });
    });

  container.innerHTML = sortedGroups.map(([category, groupDevices]) => {
    const deviceItems = groupDevices.map((device) => {
      const platform = inferMobilePlatform(device);
      const platformLabel = getPlatformLabel(platform);
      const platformIcon = getPlatformIcon(platform);
      const payloadHint = platform === 'ios'
        ? 'Verwendet iOS-Parameter: data.url + push.sound'
        : 'Verwendet Android-Parameter: data.clickAction + priority + ttl';
      return `
        <label class="notification-device-item platform-${platform}">
          <input type="checkbox" ${device.active ? 'checked' : ''} onchange="toggleNotificationDevice('${device.id}', this.checked)" />
          <span class="notification-device-content">
            <span class="notification-device-title-row">
              <strong>${escapeHtml(device.display_name)}</strong>
              <span class="notification-platform-badge">${platformIcon} ${platformLabel}</span>
            </span>
            <small>${escapeHtml(device.service)}</small>
            <small class="notification-payload-hint">${payloadHint}</small>
          </span>
        </label>
      `;
    }).join('');

    return `
      <section class="notification-device-group">
        <h4 class="notification-device-group-title">${escapeHtml(category)}</h4>
        ${deviceItems}
      </section>
    `;
  }).join('');
}

function renderNotificationRules(rules) {
  window.__notificationRulesCache = Array.isArray(rules) ? rules : [];
  const list = document.getElementById('notification-rules');
  if (!Array.isArray(rules) || rules.length === 0) {
    list.innerHTML = '<li class="muted">Keine Regeln vorhanden.</li>';
    return;
  }
  list.innerHTML = rules.map((rule) => `
    <li class="notification-rule-item swipe-item" data-swipe-payload="${encodeURIComponent(JSON.stringify({ id: rule.id }))}">
      <div class="swipe-item-action swipe-item-action-left" aria-hidden="true">
        <span class="swipe-chip swipe-chip-edit">✏️ Bearbeiten</span>
      </div>
      <div class="swipe-item-action swipe-item-action-right" aria-hidden="true">
        <span class="swipe-chip swipe-chip-delete">🗑 Löschen</span>
      </div>
      <div class="notification-rule-item-content swipe-item-content">
        <div class="notification-rule-name" title="${escapeHtml(rule.name || '')}">
          <strong>${rule.name}</strong>
        </div>
        <div class="notification-rule-meta">
          <div class="notification-rule-meta-row"><span class="notification-rule-meta-label">Priorität</span><span class="notification-rule-meta-value">${escapeHtml(rule.severity || 'info')}</span></div>
          <div class="notification-rule-meta-row"><span class="notification-rule-meta-label">Ereignisse</span><span class="notification-rule-meta-value">${(rule.event_types || []).map((eventType) => getEventLabel(eventType)).join(', ') || '-'}</span></div>
          <div class="notification-rule-meta-row"><span class="notification-rule-meta-label">Kanäle</span><span class="notification-rule-meta-value">${(rule.channels || []).map((channelType) => getChannelLabel(channelType)).join(', ') || '-'}</span></div>
          <div class="notification-rule-meta-row"><span class="notification-rule-meta-label">Cooldown</span><span class="notification-rule-meta-value">${Number(rule.cooldown_seconds || 0)}s</span></div>
        </div>
      </div>
    </li>
  `).join('');

  bindSwipeInteractions({
    selector: '#notification-rules .notification-rule-item',
    onSwipeLeft: async (item, payload) => {
      openNotificationRuleModal(payload.id);
      resetSwipeVisualState(item);
    },
    onSwipeRight: async (_, payload) => {
      await deleteNotificationRule(payload.id);
    },
    onTap: (_, payload) => {
      openNotificationRuleModal(payload.id);
    },
  });
}

function renderNotificationHistory(history) {
  const list = document.getElementById('notification-history');
  if (!Array.isArray(history) || history.length === 0) {
    list.innerHTML = '<li class="muted">Keine Einträge.</li>';
    return;
  }
  list.innerHTML = history.slice(0, 30).map((entry) => {
    const stateClass = entry.delivered ? 'is-delivered' : 'is-failed';
    const stateLabel = entry.delivered ? 'Zugestellt' : 'Fehlgeschlagen';
    return `
      <li class="notification-history-item ${stateClass}">
        <div class="notification-history-header">
          <strong>${escapeHtml(entry.title)}</strong>
          <span class="notification-delivery-badge">${stateLabel}</span>
        </div>
        <div>${escapeHtml(entry.message)}</div>
        <small class="muted">${escapeHtml(getEventLabel(entry.event_type))} · ${escapeHtml(entry.created_at || '')}</small>
        <div class="muted">Kanäle: ${escapeHtml((entry.channels || []).map((channelType) => getChannelLabel(channelType)).join(', ') || '-')}</div>
      </li>
    `;
  }).join('');
}

async function saveNotificationSettings() {
  const status = getNotificationStatusElement();
  status.textContent = 'Die globale Benachrichtigungs-Aktivierung wurde in die Home Assistant Integrations-Optionen verschoben.';
}

async function toggleNotificationDevice(deviceId, isActive) {
  const status = getNotificationStatusElement();
  try {
    const { response, payload } = await dashboardApi.updateNotificationDevice(deviceId, {
      active: isActive,
      user_id: getSelectedNotificationUserId(),
    });
    if (!response.ok) throw new Error(getErrorMessage(payload, 'Gerät konnte nicht aktualisiert werden.'));
    status.textContent = `Gerät ${deviceId} aktualisiert.`;
  } catch (error) {
    status.textContent = `Fehler: ${error.message}`;
  }
}


function resetNotificationRuleModalForm() {
  document.getElementById('notify-rule-name').value = '';
  document.getElementById('notify-rule-cooldown').value = '';
  document.getElementById('notify-rule-template').value = '';
  document.getElementById('notify-rule-channel').value = 'mobile_push';
  document.getElementById('notify-rule-severity').value = 'info';

  const eventsSelect = document.getElementById('notify-rule-events');
  const devicesSelect = document.getElementById('notify-rule-devices');
  if (eventsSelect) {
    Array.from(eventsSelect.options).forEach((option) => {
      option.selected = true;
    });
  }
  if (devicesSelect) {
    Array.from(devicesSelect.options).forEach((option) => {
      option.selected = false;
    });
  }
}

function openNotificationRuleModal(ruleId = null) {
  const title = document.getElementById('notification-rule-modal-title');
  const submitButton = document.getElementById('notify-rule-submit-button');
  dashboardState.notificationEditingRuleId = ruleId;

  if (!ruleId) {
    title.textContent = 'Neue Regel';
    submitButton.textContent = 'Regel anlegen';
    resetNotificationRuleModalForm();
  } else {
    const selectedRule = window.__notificationRulesCache?.find((rule) => rule.id === ruleId);
    if (selectedRule) {
      title.textContent = 'Regel bearbeiten';
      submitButton.textContent = 'Regel speichern';
      document.getElementById('notify-rule-name').value = selectedRule.name || '';
      document.getElementById('notify-rule-cooldown').value = String(selectedRule.cooldown_seconds || 0);
      document.getElementById('notify-rule-template').value = selectedRule.message_template || '';
      document.getElementById('notify-rule-channel').value = (selectedRule.channels || ['mobile_push'])[0] || 'mobile_push';
      document.getElementById('notify-rule-severity').value = selectedRule.severity || 'info';
      const selectedEventTypes = new Set(selectedRule.event_types || []);
      Array.from(document.getElementById('notify-rule-events').options).forEach((option) => {
        option.selected = selectedEventTypes.has(option.value);
      });
      const selectedDeviceIds = new Set(selectedRule.target_device_ids || []);
      Array.from(document.getElementById('notify-rule-devices').options).forEach((option) => {
        option.selected = selectedDeviceIds.has(option.value);
      });
    } else {
      resetNotificationRuleModalForm();
    }
  }

  document.getElementById('notification-rule-modal').classList.remove('hidden');
  syncModalScrollLock();
}

function closeNotificationRuleModal() {
  dashboardState.notificationEditingRuleId = null;
  document.getElementById('notification-rule-modal').classList.add('hidden');
  syncModalScrollLock();
}

function getSelectedNotificationUserId() {
  return document.documentElement.dataset.haUserId || 'default-user';
}

async function createNotificationRule() {
  const status = getNotificationStatusElement();
  const name = document.getElementById('notify-rule-name').value.trim();
  if (!name) {
    status.textContent = 'Bitte Regelname eingeben.';
    return;
  }
  const eventTypes = getSelectedValues(document.getElementById('notify-rule-events'));
  const targetDevices = getSelectedValues(document.getElementById('notify-rule-devices'));
  const payload = {
    name: document.getElementById('notify-rule-name').value.trim(),
    enabled: true,
    event_types: getSelectedValues(document.getElementById('notify-rule-events')),
    target_user_ids: [getSelectedNotificationUserId()],
    target_device_ids: getSelectedValues(document.getElementById('notify-rule-devices')),
    channels: [document.getElementById('notify-rule-channel').value],
    severity: document.getElementById('notify-rule-severity').value,
    cooldown_seconds: Number(document.getElementById('notify-rule-cooldown').value || '0'),
    quiet_hours_start: '',
    quiet_hours_end: '',
    conditions: [],
    message_template: document.getElementById('notify-rule-template').value,
  };
}

async function saveNotificationRule() {
  const status = getNotificationStatusElement();
  const payload = buildNotificationRulePayload();
  if (!payload.name) {
    status.textContent = 'Bitte Regelname eingeben.';
    return;
  }

  const isEditing = Boolean(dashboardState.notificationEditingRuleId);
  try {
    const { response, payload: responsePayload } = await dashboardApi.saveNotificationRule(
      dashboardState.notificationEditingRuleId,
      payload,
    );
    if (!response.ok) throw new Error(getErrorMessage(responsePayload, isEditing ? 'Regel konnte nicht gespeichert werden.' : 'Regel konnte nicht angelegt werden.'));
    status.textContent = isEditing ? 'Regel aktualisiert.' : 'Regel angelegt.';
    closeNotificationRuleModal();
    await loadNotificationOverview();
  } catch (error) {
    status.textContent = `Fehler: ${error.message}`;
  }
}

async function deleteNotificationRule(ruleId) {
  const status = getNotificationStatusElement();
  try {
    const { response, payload } = await dashboardApi.deleteNotificationRule(ruleId);
    if (!response.ok) throw new Error(getErrorMessage(payload, 'Regel konnte nicht gelöscht werden.'));
    status.textContent = 'Regel gelöscht.';
    await loadNotificationOverview();
  } catch (error) {
    status.textContent = `Fehler: ${error.message}`;
  }
}

async function testNotificationAll() {
  const status = getNotificationStatusElement();
  status.textContent = 'Sende Test an alle Geräte…';
  const { response, payload } = await dashboardApi.testNotificationAll();
  if (!response.ok) {
    status.textContent = `Fehler: ${getErrorMessage(payload, 'Test fehlgeschlagen.')}`;
    return;
  }
  status.textContent = `Test versendet (${payload.sent_to || 0} Geräte).`;
  await loadNotificationOverview();
}

async function testNotificationPersistent() {
  const status = getNotificationStatusElement();
  status.textContent = 'Sende Persistent-Test…';
  const { response, payload } = await dashboardApi.testNotificationPersistent();
  if (!response.ok) {
    status.textContent = `Fehler: ${getErrorMessage(payload, 'Test fehlgeschlagen.')}`;
    return;
  }
  status.textContent = 'Persistent-Test versendet.';
  await loadNotificationOverview();
}

function readCssCustomProperty(style, propertyName) {
  return style?.getPropertyValue(propertyName)?.trim() || '';
}

function parseColorChannels(value) {
  const normalized = String(value || '').trim().toLowerCase();
  if (!normalized) return null;

  const hexMatch = normalized.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (hexMatch) {
    const hex = hexMatch[1];
    if (hex.length === 3) {
      return hex.split('').map((channel) => Number.parseInt(channel + channel, 16));
    }
    return [
      Number.parseInt(hex.slice(0, 2), 16),
      Number.parseInt(hex.slice(2, 4), 16),
      Number.parseInt(hex.slice(4, 6), 16),
    ];
  }

  const rgbMatch = normalized.match(/^rgba?\(([^)]+)\)$/);
  if (!rgbMatch) return null;

  const channels = rgbMatch[1]
    .split(',')
    .slice(0, 3)
    .map((channel) => Number.parseFloat(channel.trim()));
  if (channels.length !== 3 || channels.some((channel) => !Number.isFinite(channel))) {
    return null;
  }
  return channels;
}

function inferColorScheme(backgroundColor) {
  const channels = parseColorChannels(backgroundColor);
  if (!channels) {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light';
  }

  const [red, green, blue] = channels;
  const luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255;
  return luminance < 0.5 ? 'dark' : 'light';
}

function getHomeAssistantSourceDocument() {
  try {
    if (window.parent && window.parent !== window && window.parent.document) {
      return window.parent.document;
    }
  } catch (_) {
    return null;
  }

  return null;
}

function getHomeAssistantThemeStyleSources(sourceDocument) {
  if (!sourceDocument) return [];

  return HA_THEME_SOURCE_SELECTORS
    .map((selector) => {
      if (selector === 'html') return sourceDocument.documentElement;
      if (selector === 'body') return sourceDocument.body;
      return sourceDocument.querySelector(selector);
    })
    .filter(Boolean)
    .map((element) => window.parent.getComputedStyle(element));
}

function readHomeAssistantThemeSnapshot() {
  const sourceDocument = getHomeAssistantSourceDocument();
  const styleSources = getHomeAssistantThemeStyleSources(sourceDocument);
  if (!styleSources.length) return null;

  const allowedSourceNames = new Set(
    haThemeVarNames.map((name) => `--${name}`).filter((name) => name !== '--')
  );
  const variables = {};
  Object.entries(HA_THEME_VARIABLE_MAPPINGS).forEach(([sourceName, targetName]) => {
    if (allowedSourceNames.size && !allowedSourceNames.has(sourceName)) return;
    const value = styleSources
      .map((style) => readCssCustomProperty(style, sourceName))
      .find(Boolean);
    if (value) {
      variables[targetName] = value;
    }
  });

  const hasThemeVariables = Object.keys(variables).length > 0;
  if (!hasThemeVariables) return null;

  const declaredColorScheme = styleSources
    .map((style) => String(style?.colorScheme || '').trim().toLowerCase())
    .find((value) => value === 'dark' || value === 'light');
  const backgroundColor = variables['--ha-primary-background-color'] || styleSources
    .map((style) => String(style?.backgroundColor || '').trim())
    .find(Boolean);

  return {
    colorScheme: declaredColorScheme || inferColorScheme(backgroundColor),
    variables,
  };
}

function applyHomeAssistantThemeSnapshot(snapshot) {
  if (!snapshot) return false;

  Object.entries(snapshot.variables || {}).forEach(([targetName, value]) => {
    rootElement.style.setProperty(targetName, value);
  });

  const colorScheme = snapshot.colorScheme === 'dark' ? 'dark' : 'light';
  rootElement.style.setProperty('--ha-color-scheme', colorScheme);
  rootElement.setAttribute('data-theme-source', haThemeSource);
  rootElement.setAttribute('data-theme-bridge-mode', haThemeBridgeMode);
  rootElement.setAttribute('data-ha-color-scheme', colorScheme);
  rootElement.setAttribute('data-ha-theme-ready', 'true');
  return true;
}

function syncThemeFromHomeAssistant() {
  return applyHomeAssistantThemeSnapshot(readHomeAssistantThemeSnapshot());
}

function observeHomeAssistantTheme() {
  const sourceDocument = getHomeAssistantSourceDocument();
  if (!sourceDocument || typeof MutationObserver === 'undefined') return;

  const watchedElements = HA_THEME_SOURCE_SELECTORS
    .map((selector) => {
      if (selector === 'html') return sourceDocument.documentElement;
      if (selector === 'body') return sourceDocument.body;
      return sourceDocument.querySelector(selector);
    })
    .filter(Boolean);

  const observer = new MutationObserver(() => {
    syncThemeFromHomeAssistant();
  });

  watchedElements.forEach((element) => {
    observer.observe(element, {
      attributes: true,
      attributeFilter: ['class', 'style', 'data-color-scheme'],
    });
  });

  syncThemeFromHomeAssistant();

  if (window.matchMedia) {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    if (typeof mediaQuery.addEventListener === 'function') {
      mediaQuery.addEventListener('change', () => {
        syncThemeFromHomeAssistant();
      });
    } else if (typeof mediaQuery.addListener === 'function') {
      mediaQuery.addListener(() => {
        syncThemeFromHomeAssistant();
      });
    }
  }

  window.addEventListener('message', (event) => {
    const payload = event?.data;
    if (!payload || payload.type !== HA_THEME_MESSAGE_TYPE || typeof payload.variables !== 'object') {
      return;
    }

    applyHomeAssistantThemeSnapshot({
      colorScheme: payload.colorScheme,
      variables: Object.entries(payload.variables).reduce((accumulator, [name, value]) => {
        if (typeof value !== 'string') return accumulator;
        const targetName = HA_THEME_VARIABLE_MAPPINGS[name];
        if (targetName) {
          accumulator[targetName] = value;
        }
        return accumulator;
      }, {}),
    });
  });
}

function ensureApiKey() {
  return apiKey;
}

function toImageSource(url, options = {}) {
  if (!url) return 'https://placehold.co/80x80?text=Kein+Bild';

  const requestedSize = String(options?.size || '').trim().toLowerCase();
  const isMobileViewport = typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(max-width: 768px)').matches;
  const normalizedSize = requestedSize === 'full'
    ? 'full'
    : (requestedSize === 'mobile' || isMobileViewport ? 'mobile' : 'thumb');

  if (url.startsWith('data:')) return url;
  if (url.startsWith('http://') || url.startsWith('https://')) {
    const isExternal = (() => {
      try {
        return new URL(url).host !== window.location.host;
      } catch (_) {
        return false;
      }
    })();

    if (window.location.protocol === 'https:' && isExternal && url.startsWith('http://')) {
      return 'https://' + url.slice('http://'.length);
    }
    return url;
  }
  const normalized = '/' + url.replace(/^\/+/, '');
  if (normalized.startsWith('/api/dashboard/product-picture?')) {
    const absoluteProxyUrl = new URL(dashboardApi.buildUrl(normalized), window.location.origin);
    absoluteProxyUrl.searchParams.set('size', normalizedSize);
    return absoluteProxyUrl.toString();
  }

  if (normalized.startsWith('/api/')) {
    return dashboardApi.buildUrl(normalized);
  }
  return normalized;
}


function updateClearButtonVisibility() {
  const clearButton = document.getElementById('clear-name');
  const nameInput = document.getElementById('name');
  clearButton.classList.toggle('visible', shouldShowClearButton(nameInput.value));
}

function clearSearchInput() {
  const nameInput = document.getElementById('name');
  nameInput.value = '';
  updateClearButtonVisibility();
  document.getElementById('variant-list').innerHTML = '';
  document.getElementById('variant-section').classList.add('hidden');
  nameInput.focus();
}

function formatValue(value, fallback = 'Nicht verfügbar') {
  const text = String(value || '').trim();
  return text || fallback;
}
function getShoppingAmount() {
  const amountInput = document.getElementById('amount');
  const amount = Number(amountInput?.value || 1);
  if (!Number.isFinite(amount) || amount <= 0) {
    return 1;
  }
  return amount;
}

function getShoppingBestBeforeDate() {
  const dateInput = document.getElementById('best-before-date');
  return String(dateInput?.value || '').trim();
}

function renderShoppingList(items) {
  const list = document.getElementById('shopping-list');
  if (!items.length) {
    list.innerHTML = '';
    list.classList.add('hidden');
    return;
  }

  list.classList.remove('hidden');

  list.innerHTML = items.map((item) => `
    <li class="shopping-item swipe-item" data-shopping-item="${encodeURIComponent(JSON.stringify(item))}">
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
          resolveImageUrl: (url) => toImageSource(url),
          amountBadge: {
            element: 'button',
            variant: 'amount',
            className: 'amount-increment-button',
            dataset: { 'shopping-list-id': item.id },
          },
          mhdBadge: {
            element: 'button',
            variant: 'mhd',
            className: 'mhd-picker-button',
            dataset: {
              'mhd-shopping-list-id': item.id,
              'mhd-product-name': encodeURIComponent(item.product_name || ''),
              'mhd-current-date': item.best_before_date || '',
            },
          },
        })}
      </div>
    </li>
  `).join('');

  bindShoppingSwipeInteractions();
}

function buildShoppingListSignature(items) {
  return JSON.stringify(
    (Array.isArray(items) ? items : [])
      .map((item) => [
        String(item.id ?? ''),
        String(item.product_name ?? ''),
        String(item.amount ?? ''),
        String(item.note ?? ''),
        String(item.best_before_date ?? ''),
        String(item.in_stock ?? ''),
      ])
      .sort((left, right) => left.join('|').localeCompare(right.join('|')))
  );
}

async function loadShoppingList(options = {}) {
  const { background = false } = options;
  const load = async () => {
  const key = ensureApiKey();
  const status = getShoppingStatusElement();
  status?.classList.add('search-status-badge');
  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return;
  }

  if (!background) {
    status.textContent = 'Lade Einkaufsliste...';
  }
  try {
    const { response, payload } = await dashboardApi.fetchShoppingList();
    if (!response.ok) {
      if (!background) {
        status.textContent = getErrorMessage(payload, 'Einkaufsliste konnte nicht geladen werden.');
      }
      return;
    }

    const nextSignature = buildShoppingListSignature(payload);
    const hasChanged = nextSignature !== dashboardState.shoppingListSignature;

    if (hasChanged) {
      renderShoppingList(payload);
      dashboardState.shoppingListSignature = nextSignature;
    }

    if (!background) {
      status.textContent = `Einkaufsliste geladen (${payload.length} Einträge).`;
    }
  } catch (_) {
    if (!background) {
      status.textContent = 'Einkaufsliste konnte nicht geladen werden (Netzwerk-/Ingress-Fehler).';
    }
  }

  };

  if (background) {
    return load();
  }

  return withBusyState(load);
}

async function refreshShoppingListInBackground() {
  if (dashboardState.shoppingListRefreshInFlight) return;
  if (document.hidden || dashboardState.activeTab !== 'shopping') return;

  dashboardState.shoppingListRefreshInFlight = true;
  try {
    await loadShoppingList({ background: true });
  } finally {
    dashboardState.shoppingListRefreshInFlight = false;
  }
}

function startShoppingListAutoRefresh() {
  if (dashboardState.shoppingListRefreshTimer) {
    clearInterval(dashboardState.shoppingListRefreshTimer);
  }

  dashboardState.shoppingListRefreshTimer = setInterval(() => {
    refreshShoppingListInBackground();
  }, shoppingListRefreshMs);
}


class GrocyVariantResults extends HTMLElement {
  constructor() {
    super();
    this._variants = [];
    this._amount = null;
    this._loading = false;
    this._active = false;
    this._listElement = document.createElement('div');
    this._listElement.className = 'variant-grid';
    this._statusElement = document.createElement('p');
    this._statusElement.className = 'variant-feedback muted';
  }

  connectedCallback() {
    if (!this._statusElement.isConnected) {
      this.append(this._statusElement, this._listElement);
    }
    this.render();
  }

  set variants(value) {
    this._variants = Array.isArray(value) ? value : [];
    this.render();
  }

  get variants() {
    return this._variants;
  }

  set amount(value) {
    const parsedAmount = Number(value);
    this._amount = Number.isFinite(parsedAmount) && parsedAmount > 0 ? parsedAmount : null;
    this.render();
  }

  get amount() {
    return this._amount;
  }

  set loading(value) {
    this._loading = Boolean(value);
    this.render();
  }

  get loading() {
    return this._loading;
  }

  set active(value) {
    this._active = Boolean(value);
    this.render();
  }

  get active() {
    return this._active;
  }

  render() {
    this.hidden = !this._active;
    if (!this.isConnected || !this._active) {
      this.replaceChildren(this._statusElement, this._listElement);
      this._statusElement.hidden = true;
      this._listElement.replaceChildren();
      return;
    }

    if (!this._statusElement.isConnected || !this._listElement.isConnected) {
      this.replaceChildren(this._statusElement, this._listElement);
    }

    if (this._loading) {
      this.renderLoading();
      return;
    }

    if (!this._variants.length) {
      this.renderEmpty();
      return;
    }

    this.renderList();
  }

  renderLoading() {
    this._listElement.replaceChildren();
    this._statusElement.hidden = false;
    this._statusElement.textContent = 'Suche Produktvarianten …';
  }

  renderEmpty() {
    this._listElement.replaceChildren();
    this._statusElement.hidden = false;
    this._statusElement.textContent = 'Keine Produktvarianten gefunden.';
  }

  renderList() {
    this._statusElement.hidden = true;
    const cards = this._variants.map((item) => this.createVariantCard(item));
    this._listElement.replaceChildren(...cards);
  }

  createVariantCard(item) {
    const wrapper = document.createElement('div');
    wrapper.innerHTML = renderShoppingVariantCard(item, {
      amount: this._amount,
      actionName: 'variant-select',
      ctaLabel: 'Zur Liste',
      resolveImageUrl: (url) => toImageSource(url),
    }).trim();
    const card = wrapper.firstElementChild;
    if (!card) return document.createElement('div');

    const button = card.querySelector('[data-action="variant-select"]');
    if (button) {
      button.addEventListener('click', () => {
        this.dispatchEvent(new CustomEvent('variant-select', {
          bubbles: true,
          detail: {
            productId: item?.id ?? item?.product_id ?? '',
            productName: String(item?.name || item?.product_name || ''),
            source: item?.source || 'grocy',
            amount: this._amount,
          },
        }));
      });
    }

    return card;
  }
}

if (!customElements.get('grocy-variant-results')) {
  customElements.define('grocy-variant-results', GrocyVariantResults);
}

function getVariantSectionElement() {
  return document.getElementById('variant-section');
}

function getVariantResultsElement() {
  return document.getElementById('variant-results');
}

function setVariantResultsState({ active, loading, items, amount } = {}) {
  const section = getVariantSectionElement();
  const results = getVariantResultsElement();
  if (!results) return;
  if (typeof amount !== 'undefined') results.amount = amount;
  if (typeof items !== 'undefined') results.variants = items;
  if (typeof loading !== 'undefined') results.loading = loading;
  if (typeof active !== 'undefined') {
    results.active = active;
    section?.classList.toggle('hidden', !active);
  }
}

function clearVariantResults() {
  setVariantResultsState({ active: false, loading: false, items: [], amount: null });
}

function renderVariants(items, options = {}) {
  setVariantResultsState({
    active: true,
    loading: false,
    items,
    amount: options.amount,
  });
}

async function loadVariants() {
  return withBusyState(async () => {
  const key = ensureApiKey();
  const status = getShoppingStatusElement();
  status?.classList.add('search-status-badge');
  const name = document.getElementById('name').value || '';
  const { productName, amountFromName } = parseAmountPrefixedSearch(name);

  if (!key) return;

  const query = productName.trim();
  const requestToken = ++dashboardState.variantsRequestToken;
  if (!query) {
    clearVariantResults();
    return;
  }

  if (query.length < MIN_PRODUCT_SEARCH_LENGTH) {
    clearVariantResults();
    status.textContent = getMinimumSearchLengthMessage(query.length);
    return;
  }

  try {
    setVariantResultsState({ active: true, loading: true, items: [], amount: amountFromName });
    const { response, payload } = await dashboardApi.searchVariants(query);
    if (requestToken !== dashboardState.variantsRequestToken) return;
    if (!response.ok) {
      setVariantResultsState({ active: true, loading: false, items: [], amount: amountFromName });
      status.textContent = getErrorMessage(payload, 'Varianten konnten nicht geladen werden.');
      return;
    }

    renderVariants(payload, { amount: amountFromName });

  } catch (_) {
    if (requestToken !== dashboardState.variantsRequestToken) return;
    setVariantResultsState({ active: true, loading: false, items: [], amount: amountFromName });
    status.textContent = 'Varianten konnten nicht geladen werden (Netzwerk-/Ingress-Fehler).';
  }

  });
}

async function confirmVariant(productId, productName, amountOverride = null) {
  return withBusyState(async () => {
  const key = ensureApiKey();
  const status = getShoppingStatusElement();
  status?.classList.add('search-status-badge');

  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return;
  }

  status.textContent = `Füge ${productName} zur Einkaufsliste hinzu...`;
  const { amountFromName } = parseAmountPrefixedSearch(document.getElementById('name').value || '');
  const normalizedOverride = Number(amountOverride);
  const amount = (Number.isFinite(normalizedOverride) && normalizedOverride > 0)
    ? normalizedOverride
    : (amountFromName ?? getShoppingAmount());
  const requestProductName = Number.isFinite(amount) && amount > 0
    ? `${amount} ${productName}`
    : productName;
  const bestBeforeDate = getShoppingBestBeforeDate();

  try {
    const { response, payload } = await dashboardApi.addExistingProduct({
      product_id: productId,
      product_name: requestProductName,
      amount,
      best_before_date: bestBeforeDate,
    });
    status.textContent = payload.message || getErrorMessage(payload, 'Unbekannte Antwort');

    if (response.ok) {
      const variants = payload.variants || [];
      if (payload.action === 'variant_selection_required' && variants.length) {
        renderVariants(variants, { amount });
        return;
      }

      clearVariantResults();
      await loadShoppingList();
    }
  } catch (_) {
    status.textContent = 'Produkt konnte nicht hinzugefügt werden (Netzwerk-/Ingress-Fehler).';
  }

  });
}

async function incrementShoppingItemAmount(shoppingListId) {
  const status = getShoppingStatusElement();
  status?.classList.add('search-status-badge');

  return withBusyState(async () => {
    const { response, payload } = await dashboardApi.incrementShoppingItemAmount(shoppingListId);
    if (!response.ok) {
      throw new Error(getErrorMessage(payload, 'Menge konnte nicht erhöht werden.'));
    }

    status.textContent = payload.message || `Menge für Eintrag ${shoppingListId} erhöht.`;
    await loadShoppingList();
  });
}

async function removeShoppingItem(shoppingListId) {
  const key = ensureApiKey();
  const status = getShoppingStatusElement();
  status?.classList.add('search-status-badge');
  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return;
  }

  const { response, payload } = await dashboardApi.deleteShoppingListItem(shoppingListId);
  if (!response.ok) {
    status.textContent = getErrorMessage(payload, 'Eintrag konnte nicht gelöscht werden.');
    return;
  }
  status.textContent = `Eintrag ${shoppingListId} gelöscht.`;
  await loadShoppingList();
}

async function purchaseShoppingItem(shoppingListId) {
  const key = ensureApiKey();
  const status = getShoppingStatusElement();
  status?.classList.add('search-status-badge');
  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return;
  }

  const { response, payload } = await dashboardApi.completeShoppingListItem(shoppingListId);
  if (!response.ok) {
    status.textContent = getErrorMessage(payload, 'Eintrag konnte nicht als gekauft markiert werden.');
    return;
  }
  status.textContent = payload.message || `Einkauf für Eintrag ${shoppingListId} abgeschlossen.`;
  await loadShoppingList();
}

function showShoppingItemDetails(item) {
  const modal = document.getElementById('shopping-item-modal');
  const title = document.getElementById('shopping-item-title');
  const details = document.getElementById('shopping-item-details');

  title.textContent = item.product_name || 'Produktdetails';
  details.innerHTML = `
    <section class="shopping-detail-half">
      <h4>Grocy Bestandsinfos</h4>
      <ul>
        <li><span>Produkt-ID</span><strong>${formatValue(item.product_id)}</strong></li>
        <li><span>Lagerort</span><strong>${formatValue(item.location_name)}</strong></li>
        <li><span>In Bestand</span><strong>${formatValue(item.in_stock)}</strong></li>
        <li><span>Menge Einkauf</span><strong id="shopping-item-current-amount">${formatValue(item.amount)}</strong></li>
        <li><span>Geschätzte Haltbarkeit</span><strong>${formatValue(item.default_amount)}</strong></li>
        <li><span>MHD</span><strong>${formatValue(item.best_before_date)}</strong></li>
      </ul>
    </section>
    <section class="shopping-detail-half">
      <h4>Nährwertdetails</h4>
      <ul>
        <li><span>Kalorien</span><strong>${formatValue(item.calories)}</strong></li>
        <li><span>Kohlenhydrate</span><strong>${formatValue(item.carbs)}</strong></li>
        <li><span>Fett</span><strong>${formatValue(item.fat)}</strong></li>
        <li><span>Protein</span><strong>${formatValue(item.protein)}</strong></li>
        <li><span>Zucker</span><strong>${formatValue(item.sugar)}</strong></li>
        <li><span>Notiz</span><strong>${formatValue(item.note)}</strong></li>
      </ul>
    </section>
  `;
  openShoppingAmountEditor(item.amount || '');
  openShoppingNoteEditor(item.id, item.note || '');
  modal.classList.remove('hidden');
  syncModalScrollLock();
}



function openShoppingAmountEditor(currentAmount = '') {
  dashboardState.activeShoppingAmountValue = String(currentAmount || '').trim();
  const input = document.getElementById('shopping-item-amount-input');
  if (input) input.value = dashboardState.activeShoppingAmountValue || '';
}

function openShoppingNoteEditor(shoppingListId, currentNote = '') {
  dashboardState.activeShoppingNoteItemId = shoppingListId;
  dashboardState.activeShoppingNoteValue = String(currentNote || '').trim();
  const input = document.getElementById('shopping-item-note-input');
  if (input) input.value = currentNote || '';
}

async function saveShoppingNote(shoppingListId, note) {
  const key = ensureApiKey();
  const status = getShoppingStatusElement();
  status?.classList.add('search-status-badge');

  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return false;
  }
  if (!shoppingListId) {
    status.textContent = 'Einkaufslisten-Eintrag fehlt.';
    return false;
  }

  status.textContent = 'Speichere Notiz...';
  try {
    const { response, payload } = await dashboardApi.updateShoppingListItemNote(shoppingListId, note);
    if (!response.ok) {
      status.textContent = getErrorMessage(payload, 'Notiz konnte nicht gespeichert werden.');
      return false;
    }

    status.textContent = payload.message || 'Notiz gespeichert.';
    dashboardState.activeShoppingNoteValue = note;
    return true;
  } catch (_) {
    status.textContent = 'Notiz konnte nicht gespeichert werden (Netzwerk-/Ingress-Fehler).';
    return false;
  }
}


async function saveShoppingAmount(shoppingListId, amount) {
  const key = ensureApiKey();
  const status = getShoppingStatusElement();
  status?.classList.add('search-status-badge');

  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return false;
  }
  if (!shoppingListId) {
    status.textContent = 'Einkaufslisten-Eintrag fehlt.';
    return false;
  }

  const normalizedAmount = String(amount || '').replace(',', '.').trim();
  const parsedAmount = Number(normalizedAmount);
  if (!Number.isFinite(parsedAmount) || parsedAmount <= 0) {
    status.textContent = 'Bitte eine gültige Menge größer als 0 eingeben.';
    return false;
  }

  status.textContent = 'Speichere Menge...';
  try {
    const { response, payload } = await dashboardApi.updateShoppingListItemAmount(shoppingListId, parsedAmount);
    if (!response.ok) {
      status.textContent = getErrorMessage(payload, 'Menge konnte nicht gespeichert werden.');
      return false;
    }

    const amountValue = String(payload.amount ?? parsedAmount);
    dashboardState.activeShoppingAmountValue = amountValue;
    const amountLabel = document.getElementById('shopping-item-current-amount');
    if (amountLabel) amountLabel.textContent = amountValue;

    status.textContent = payload.message || 'Menge gespeichert.';
    return true;
  } catch (_) {
    status.textContent = 'Menge konnte nicht gespeichert werden (Netzwerk-/Ingress-Fehler).';
    return false;
  }
}

async function saveShoppingAmountFromModal() {
  const input = document.getElementById('shopping-item-amount-input');
  const amount = String(input?.value || '').trim();
  const saved = await saveShoppingAmount(dashboardState.activeShoppingNoteItemId, amount);
  if (saved) {
    await loadShoppingList();
    await closeShoppingItemDetails();
  }
}


function openMhdPicker(shoppingListId, productName, currentDate = '') {
  const modal = document.getElementById('mhd-modal');
  const title = document.getElementById('mhd-modal-title');
  const input = document.getElementById('mhd-date-input');

  dashboardState.activeMhdShoppingListId = shoppingListId;
  title.textContent = `MHD auswählen: ${productName || 'Produkt'}`;
  input.value = currentDate || '';
  modal.classList.remove('hidden');
}

function closeMhdPicker() {
  dashboardState.activeMhdShoppingListId = null;
  document.getElementById('mhd-modal').classList.add('hidden');
}

async function saveMhdPickerDate() {
  const key = ensureApiKey();
  const status = getShoppingStatusElement();
  status?.classList.add('search-status-badge');
  const input = document.getElementById('mhd-date-input');
  const bestBeforeDate = String(input?.value || '').trim();

  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return;
  }
  if (!dashboardState.activeMhdShoppingListId) {
    status.textContent = 'Einkaufslisten-Eintrag fehlt.';
    return;
  }
  if (!bestBeforeDate) {
    status.textContent = 'Bitte ein MHD auswählen.';
    return;
  }

  status.textContent = 'Speichere MHD...';
  try {
    const { response, payload } = await dashboardApi.updateShoppingListItemBestBefore(
      dashboardState.activeMhdShoppingListId,
      bestBeforeDate,
    );
    if (!response.ok) {
      status.textContent = getErrorMessage(payload, 'MHD konnte nicht gespeichert werden.');
      return;
    }

    status.textContent = payload.message || 'MHD gespeichert.';
    closeMhdPicker();
    await loadShoppingList();
  } catch (_) {
    status.textContent = 'MHD konnte nicht gespeichert werden (Netzwerk-/Ingress-Fehler).';
  }
}

async function resetMhdPickerDate() {
  const key = ensureApiKey();
  const status = getShoppingStatusElement();
  status?.classList.add('search-status-badge');

  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return;
  }
  if (!dashboardState.activeMhdShoppingListId) {
    status.textContent = 'Einkaufslisten-Eintrag fehlt.';
    return;
  }

  status.textContent = 'Setze MHD zurück...';
  try {
    const { response, payload } = await dashboardApi.resetShoppingListItemBestBefore(
      dashboardState.activeMhdShoppingListId,
    );
    if (!response.ok) {
      status.textContent = getErrorMessage(payload, 'MHD konnte nicht zurückgesetzt werden.');
      return;
    }

    status.textContent = payload.message || 'MHD zurückgesetzt.';
    closeMhdPicker();
    await loadShoppingList();
  } catch (_) {
    status.textContent = 'MHD konnte nicht zurückgesetzt werden (Netzwerk-/Ingress-Fehler).';
  }
}

async function closeShoppingItemDetails() {
  const modal = document.getElementById('shopping-item-modal');
  const input = document.getElementById('shopping-item-note-input');
  const note = String(input?.value || '').trim();

  if (dashboardState.activeShoppingNoteItemId && note !== dashboardState.activeShoppingNoteValue) {
    const saved = await saveShoppingNote(dashboardState.activeShoppingNoteItemId, note);
    if (saved) {
      await loadShoppingList();
    }
  }

  dashboardState.activeShoppingNoteItemId = null;
  dashboardState.activeShoppingNoteValue = '';
  dashboardState.activeShoppingAmountValue = '';
  modal.classList.add('hidden');
  syncModalScrollLock();
}

function bindShoppingSwipeInteractions() {
  bindSwipeInteractions({
    selector: '#shopping-list .shopping-item',
    interactiveElementSelector: '.amount-increment-button, .mhd-picker-button',
    onSwipeLeft: async (_, payload) => {
      const shoppingListId = payload.id;
      await removeShoppingItem(shoppingListId);
    },
    onSwipeRight: async (_, payload) => {
      const shoppingListId = payload.id;
      await purchaseShoppingItem(shoppingListId);
    },
    onTap: (_, payload) => {
      showShoppingItemDetails(payload);
    },
  });
}

async function completeShoppingList() {
  return withBusyState(async () => {
  const key = ensureApiKey();
  const status = getShoppingStatusElement();
  status?.classList.add('search-status-badge');
  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return;
  }

  status.textContent = 'Markiere Einkaufsliste als eingekauft...';
  try {
    const { response, payload } = await dashboardApi.completeShoppingList();
    if (!response.ok) {
      status.textContent = getErrorMessage(payload, 'Einkauf konnte nicht abgeschlossen werden.');
      return;
    }

    status.textContent = payload.message || 'Einkauf abgeschlossen.';
    await loadShoppingList();
  } catch (_) {
    status.textContent = 'Einkauf konnte nicht abgeschlossen werden (Netzwerk-/Ingress-Fehler).';
  }

  });
}

async function clearShoppingList() {
  return withBusyState(async () => {
  const key = ensureApiKey();
  const status = getShoppingStatusElement();
  status?.classList.add('search-status-badge');
  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return;
  }

  status.textContent = 'Leere Einkaufsliste...';
  try {
    const { response, payload } = await dashboardApi.clearShoppingList();
    if (!response.ok) {
      status.textContent = getErrorMessage(payload, 'Einkaufsliste konnte nicht geleert werden.');
      return;
    }

    status.textContent = payload.message || 'Einkaufsliste geleert.';
    await loadShoppingList();
  } catch (_) {
    status.textContent = 'Einkaufsliste konnte nicht geleert werden (Netzwerk-/Ingress-Fehler).';
  }

  });
}

async function searchProduct(options = {}) {
  return withBusyState(async () => {
  const rawName = document.getElementById('name').value;
  const status = getShoppingStatusElement();
  status?.classList.add('search-status-badge');
  const key = ensureApiKey();
  const { productName, amountFromName } = parseAmountPrefixedSearch(rawName);
  const amount = amountFromName ?? getShoppingAmount();
  const bestBeforeDate = getShoppingBestBeforeDate();

  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return;
  }
  if (!productName) {
    status.textContent = 'Bitte Produktname eingeben.';
    return;
  }
  if (productName.trim().length < MIN_PRODUCT_SEARCH_LENGTH) {
    status.textContent = 'Bitte mindestens 3 Buchstaben für die Produktsuche eingeben.';
    return;
  }

  const forceCreate = options.forceCreate === true;
  status.textContent = forceCreate ? 'Lege Produkt direkt an...' : 'Prüfe Produkt...';
  try {
    const { response, payload } = await dashboardApi.searchProduct({
      name: productName,
      amount,
      best_before_date: bestBeforeDate,
      force_create: forceCreate,
    });
    status.textContent = payload.message || getErrorMessage(payload, 'Unbekannte Antwort');

    if (response.ok) {
      const variants = payload.variants || [];
      if (payload.action === 'variant_selection_required' && variants.length) {
        renderVariants(variants, { amount });
        return;
      }

      clearVariantResults();
      await loadShoppingList();
    }
  } catch (_) {
    status.textContent = 'Produkt konnte nicht geprüft werden (Netzwerk-/Ingress-Fehler).';
  }

  });
}

getVariantResultsElement()?.addEventListener('variant-select', (event) => {
  const detail = event.detail || {};
  const productIdRaw = detail.productId;
  const productId = Number(productIdRaw);
  const productName = String(detail.productName || '');
  const productAmount = Number(detail.amount ?? '');
  const source = detail.source || 'grocy';

  if (source === 'input') {
    searchSuggestedProduct(productName, { forceCreate: true, amount: productAmount });
    return;
  }

  if (!Number.isFinite(productId) || !productIdRaw) {
    searchSuggestedProduct(productName, { amount: productAmount });
    return;
  }

  if (source === 'ai') {
    searchSuggestedProduct(productName, { amount: productAmount });
    return;
  }

  confirmVariant(productId, productName, productAmount);
});


document.getElementById('shopping-list').addEventListener('click', async (event) => {
  const amountButton = event.target.closest('.amount-increment-button');
  if (amountButton) {
    event.stopPropagation();
    const shoppingListId = Number(amountButton.dataset.shoppingListId || '');
    if (!Number.isFinite(shoppingListId) || shoppingListId <= 0) return;

    try {
      await incrementShoppingItemAmount(shoppingListId);
    } catch (error) {
      getShoppingStatusElement().textContent = `Fehler: ${error.message}`;
    }
    return;
  }
});

document.getElementById('shopping-list').addEventListener('click', (event) => {
  const target = event.target.closest('.mhd-picker-button');
  if (!target) return;

  event.stopPropagation();

  const shoppingListId = Number(target.dataset.mhdShoppingListId || '');
  if (!Number.isFinite(shoppingListId) || shoppingListId <= 0) return;

  const productName = decodeURIComponent(target.dataset.mhdProductName || '');
  const currentDate = target.dataset.mhdCurrentDate || '';
  openMhdPicker(shoppingListId, productName, currentDate);
});

document.addEventListener('change', (event) => {
  if (event.target && event.target.closest('#location-filters')) {
    loadStockProducts();
  }
});


document.getElementById('storage-filter-input')?.addEventListener('input', () => {
  clearTimeout(dashboardState.storageFilterDebounce);
  dashboardState.storageFilterDebounce = setTimeout(() => {
    loadStorageProducts();
  }, 250);
});

document.getElementById('name').addEventListener('input', () => {
  updateClearButtonVisibility();
  clearTimeout(dashboardState.variantsDebounce);
  dashboardState.variantsDebounce = setTimeout(() => {
    loadVariants();
  }, 250);
});

document.getElementById('shopping-search-form')?.addEventListener('submit', async (event) => {
  event.preventDefault();
  clearTimeout(dashboardState.variantsDebounce);
  await searchProduct();
});


syncThemeFromHomeAssistant();
observeHomeAssistantTheme();
updateClearButtonVisibility();
const addMissingButton = document.getElementById('recipe-add-missing-button');
if (addMissingButton) addMissingButton.addEventListener('click', addMissingRecipeProducts);

document.addEventListener('keydown', (event) => {
  if (event.key !== 'Escape') return;
  const recipeCreateModal = document.getElementById('recipe-create-modal');
  if (recipeCreateModal && !recipeCreateModal.classList.contains('hidden')) {
    closeRecipeCreateModal();
    return;
  }
  if (isScannerModalVisible()) {
    closeScannerModal();
  }
});

document.addEventListener('visibilitychange', () => {
  if (document.hidden) return;
  if (dashboardState.activeTab === 'shopping') {
    refreshShoppingListInBackground();
  }
  if (dashboardState.activeTab === 'storage') {
    refreshStorageInBackground();
  }
});

switchTab('shopping');
initializeTopbarStatusSync();
loadShoppingList();
startShoppingListAutoRefresh();
startStorageAutoRefresh();
preloadRecipeSuggestionsOnStartup();


async function searchSuggestedProduct(productName, options = {}) {
  const nameInput = document.getElementById('name');
  const normalizedAmount = Number(options.amount);
  const hasAmount = Number.isFinite(normalizedAmount) && normalizedAmount > 0;
  const prefixedProductName = hasAmount ? `${normalizedAmount} ${productName}` : productName;
  nameInput.value = prefixedProductName;
  updateClearButtonVisibility();

  const nextOptions = { ...options };
  delete nextOptions.amount;

  await searchProduct(nextOptions);
}

function getSelectedLocationIds() {
  return Array.from(document.querySelectorAll('#location-filters input[type="checkbox"]:checked'))
    .map((checkbox) => Number(checkbox.value));
}

function getSelectedProductIds() {
  return Array.from(document.querySelectorAll('#stock-products input[type="checkbox"]:checked'))
    .map((checkbox) => Number(checkbox.value));
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

function renderLocations(items) {
  const container = document.getElementById('location-filters');
  if (!container) return;

  const selectedLocationIds = new Set(recipeState.selectedLocationIds);

  if (!items.length) {
    container.innerHTML = '<div class="muted">Keine Lagerstandorte gefunden.</div>';
    return;
  }

  const summaryLabel = summarizeSelectedItems(items, recipeState.selectedLocationIds, 'Keine Auswahl');

  container.innerHTML = `
    <details class="location-dropdown">
      <summary>
        <span class="location-dropdown__summary-copy">
          <span class="location-dropdown__summary-title">Lagerort</span>
          <span class="location-dropdown__summary-value">${escapeHtml(summaryLabel)}</span>
        </span>
        <span class="badge location-dropdown__summary-badge">Standorte: ${selectedLocationIds.size || items.length}</span>
      </summary>
      <div class="location-options">
        ${items.map((item) => `
          <label class="stock-item">
            <input type="checkbox" value="${item.id}" ${selectedLocationIds.size === 0 || selectedLocationIds.has(item.id) ? 'checked' : ''} />
            <span class="stock-item-name"><strong>${escapeHtml(item.name)}</strong></span>
          </label>
        `).join('')}
      </div>
    </details>
  `;
}

function renderStockProducts(items) {
  const container = document.getElementById('stock-products');
  const normalizedItems = (Array.isArray(items) ? items : []).map(normalizeStockProduct);
  const selectedProductIds = new Set(recipeState.selectedProductIds);

  const summaryLabel = summarizeSelectedItems(normalizedItems, recipeState.selectedProductIds, 'Keine Auswahl');

  container.innerHTML = `
    <details class="location-dropdown">
      <summary>
        <span class="location-dropdown__summary-copy">
          <span class="location-dropdown__summary-title">Produkte in ausgewählten Standorten</span>
          <span class="location-dropdown__summary-value">${escapeHtml(summaryLabel)}</span>
        </span>
        <span class="badge location-dropdown__summary-badge">Produkte: ${selectedProductIds.size || normalizedItems.length}</span>
      </summary>
      <div class="stock-options">
        ${normalizedItems.length ? normalizedItems.map((item) => `
          <label class="stock-item">
            <input type="checkbox" value="${item.id}" ${selectedProductIds.size === 0 || selectedProductIds.has(item.id) ? 'checked' : ''} />
            <span class="stock-item-name"><strong>${escapeHtml(item.name)}</strong></span>
            <span class="stock-item-attributes">
              <button type="button" class="badge amount-increment-button" data-shopping-list-id="${item.id}">Menge: ${formatBadgeValue(item.amount, '-')}</button>
              <span class="badge">MHD: ${formatBadgeValue(item.best_before_date, '-')}</span>
              ${item.location_name ? `<span class="badge">Lagerort: ${escapeHtml(item.location_name)}</span>` : ''}
            </span>
          </label>
        `).join('') : '<div class="muted">Keine Produkte für die ausgewählten Lagerstandorte gefunden.</div>'}
      </div>
    </details>
  `;
}

function getRecipeSuggestionDescription(item) {
  const reason = String(item.reason || '').trim();
  const preparation = String(item.preparation || '').replace(/\s+/g, ' ').trim();
  if (reason) return reason;
  if (!preparation) return 'Keine zusätzliche Beschreibung verfügbar.';
  return preparation.length > 120 ? `${preparation.slice(0, 117)}...` : preparation;
}

function renderRecipeList(elementId, items, emptyText) {
  const list = document.getElementById(elementId);
  if (!items.length) {
    list.innerHTML = `<li>${emptyText}</li>`;
    return;
  }

  list.innerHTML = items.map((item) => {
    const description = getRecipeSuggestionDescription(item);
    return `
      <li class="recipe-item" data-recipe-item="${encodeURIComponent(JSON.stringify(item))}">
        ${item.picture_url ? `<img class="recipe-thumb" src="${toImageSource(item.picture_url)}" alt="${item.title}" loading="lazy" />` : '<div class="recipe-thumb recipe-thumb-fallback">🍽️</div>'}
        <div class="recipe-item-copy">
          <div class="recipe-item-title">${item.title}</div>
          <div class="muted recipe-item-description">${description}</div>
        </div>
      </li>
    `;
  }).join('');

  bindRecipeItemInteractions();
}

async function loadLocations() {
  return withBusyState(async () => {
  const key = ensureApiKey();
  if (!key) return;

  try {
    const { response, payload } = await dashboardApi.fetchLocations();
    if (!response.ok) {
      getRecipeStatusElement().textContent = getErrorMessage(payload, 'Standorte konnten nicht geladen werden.');
      return;
    }

    dashboardState.storageLocationOptions = Array.isArray(payload) ? payload : [];
    if (dashboardState.storageEditingItem) {
      renderStorageEditLocationOptions(dashboardState.storageEditingItem.location_id, dashboardState.storageEditingItem.location_name || '');
    }
    renderLocations(payload);
    recipeState.initialized = true;
    await loadStockProducts();
  } catch (_) {
    getRecipeStatusElement().textContent = 'Standorte konnten nicht geladen werden (Netzwerk-/Ingress-Fehler).';
  }

  });
}

async function loadStockProducts() {
  return withBusyState(async () => {
  const key = ensureApiKey();
  if (!key) return;

  try {
    const selectedLocationIds = getSelectedLocationIds();
    recipeState.selectedLocationIds = selectedLocationIds;
    const { response, payload } = await dashboardApi.fetchStockProducts({ locationIds: selectedLocationIds });
    if (!response.ok) {
      getRecipeStatusElement().textContent = getErrorMessage(payload, 'Bestand konnte nicht geladen werden.');
      return;
    }

    const normalizedPayload = (Array.isArray(payload) ? payload : []).map(normalizeStockProduct);
    const availableProductIds = new Set(normalizedPayload.map((item) => item.id));
    recipeState.selectedProductIds = recipeState.selectedProductIds.filter((id) => availableProductIds.has(id));

    const nextStockSignature = buildStockSignature(normalizedPayload);
    const hasStockChanged = recipeState.stockSignature !== null
      && recipeState.stockSignature !== nextStockSignature;

    recipeState.stockSignature = nextStockSignature;

    renderStockProducts(normalizedPayload);

    if (recipeState.selectedProductIds.length === 0) {
      recipeState.selectedProductIds = getSelectedProductIds();
    }

    getRecipeStatusElement().textContent = hasStockChanged
      ? 'Bestand aktualisiert. Lade Rezeptvorschläge bei Bedarf manuell.'
      : 'Bestand geladen. Lade Rezeptvorschläge bei Bedarf manuell.';

    if (!hasStockChanged && !recipeState.hasLoadedInitialSuggestions) {
      recipeState.hasLoadedInitialSuggestions = true;
      await loadRecipeSuggestions({ usePrefetchedCache: true });
    }
  } catch (_) {
    getRecipeStatusElement().textContent = 'Bestand konnte nicht geladen werden (Netzwerk-/Ingress-Fehler).';
  }

  });
}



function getStorageStatusElement() {
  return document.getElementById('status-storage');
}

function getTopbarStatusElement() {
  return document.getElementById('topbar-status');
}

function getStatusElementByTab(tabName) {
  if (tabName === 'recipes') return getRecipeStatusElement();
  if (tabName === 'storage') return getStorageStatusElement();
  if (tabName === 'notifications') return getNotificationStatusElement();
  return getShoppingStatusElement();
}

function syncTopbarStatusFromActiveTab() {
  const topbarStatus = getTopbarStatusElement();
  if (!topbarStatus) return;
  const activeStatusElement = getStatusElementByTab(dashboardState.activeTab);
  const nextStatus = String(activeStatusElement?.textContent || '').trim() || 'Bereit.';
  topbarStatus.textContent = nextStatus;
}

function initializeTopbarStatusSync() {
  const statusElements = [
    getShoppingStatusElement(),
    getRecipeStatusElement(),
    getStorageStatusElement(),
    getNotificationStatusElement(),
  ].filter(Boolean);

  statusElements.forEach((statusElement) => {
    const observer = new MutationObserver(() => {
      syncTopbarStatusFromActiveTab();
    });
    observer.observe(statusElement, { childList: true, characterData: true, subtree: true });
  });

  syncTopbarStatusFromActiveTab();
}

function normalizeStorageFilterValue() {
  const input = document.getElementById('storage-filter-input');
  return String(input?.value || '').trim().toLowerCase();
}

async function fetchStorageSummaryCounts({ query = '', visibleItems = [] } = {}) {
  const normalizedVisibleItems = Array.isArray(visibleItems) ? visibleItems : [];
  const fallbackSummary = {
    totalCount: normalizedVisibleItems.length,
    inStockCount: normalizedVisibleItems.filter((item) => item?.in_stock).length,
    outOfStockCount: normalizedVisibleItems.filter((item) => !item?.in_stock).length,
  };

  try {
    const { response, payload } = await dashboardApi.fetchStockProducts({
      includeAllProducts: true,
      query,
    });
    if (!response.ok) return fallbackSummary;
    const allItems = (Array.isArray(payload) ? payload : []).map(normalizeStockProduct);
    const inStockCount = allItems.filter((item) => item?.in_stock).length;
    return {
      totalCount: allItems.length,
      inStockCount,
      outOfStockCount: allItems.length - inStockCount,
    };
  } catch (error) {
    return fallbackSummary;
  }
}

function renderStorageProducts() {
  const list = document.getElementById('storage-products');
  if (!list) return;

  const filteredItems = dashboardState.storageProductsCache;

  if (!filteredItems.length) {
    list.innerHTML = '<li class="muted">Keine Produkte gefunden.</li>';
    return;
  }

  list.innerHTML = filteredItems.map((item) => {
    const actionableId = getActionableStorageId(item);

    return `
    <li class="storage-item swipe-item variant-card" data-swipe-payload="${encodeURIComponent(JSON.stringify({ id: actionableId }))}">
      <div class="swipe-item-action swipe-item-action-left" aria-hidden="true">
        <span class="swipe-chip swipe-chip-edit">✏️ Bearbeiten</span>
      </div>
      <div class="swipe-item-action swipe-item-action-right" aria-hidden="true">
        <span class="swipe-chip swipe-chip-buy">✅ Verbrauchen</span>
      </div>
      <div class="storage-item-content shopping-item-content swipe-item-content">
        <img src="${toImageSource(item.picture_url)}" alt="${escapeHtml(item.name || 'Unbekanntes Produkt')}" loading="lazy" />
        <div class="storage-item-main">
          <div><strong class="storage-item-name">${escapeHtml(item.name || 'Unbekanntes Produkt')}</strong></div>
          <div class="shopping-card__detail-line shopping-card__detail-line--location">
            <span class="shopping-card__detail-label">Lagerort</span>
            <span class="shopping-card__detail-value">${escapeHtml(formatBadgeValue(item.location_name, 'Nicht gesetzt'))}</span>
          </div>
        </div>
        <div class="storage-item-side">
          <div class="storage-item-badges">
            <span class="badge">Menge: ${escapeHtml(formatBadgeValue(item.amount, '0'))}</span>
            <span class="badge">MHD: ${escapeHtml(formatBadgeValue(item.best_before_date, '-'))}</span>
          </div>
          <div class="storage-item-info muted">${escapeHtml(item.in_stock ? 'Im Bestand' : 'Nicht im Bestand')}</div>
        </div>
      </div>
    </li>
  `;
  }).join('');

  bindSwipeInteractions({
    selector: '#storage-products .storage-item',
    onSwipeLeft: async (_, payload) => {
      if (payload.id > 0) {
        await consumeStorageProduct(payload.id);
      }
    },
    onSwipeRight: async (item, payload) => {
      if (payload.id > 0) {
        openStorageEditModal(payload.id);
      }
      resetSwipeVisualState(item);
    },
    onTap: (_, payload) => {
      if (payload.id > 0) {
        openStorageEditModal(payload.id);
      }
    },
  });
}

async function loadStorageProducts() {
  const { background = false } = arguments[0] || {};
  const load = async () => {
    const key = ensureApiKey();
    const status = getStorageStatusElement();
    if (!key) {
      status.textContent = 'Kein API-Key angegeben.';
      return;
    }

    const includeAllProductsInput = document.getElementById('storage-include-all-products');
    const includeAllProducts = Boolean(includeAllProductsInput?.checked);
    const filterValue = String(document.getElementById('storage-filter-input')?.value || '').trim();
    if (!background) {
      status.textContent = includeAllProducts ? 'Lade Lagerbestand und alle Produkte...' : 'Lade Lagerbestand...';
    }
    try {
      const { response, payload } = await dashboardApi.fetchStockProducts({
        includeAllProducts,
        query: filterValue,
      });
      if (!response.ok) throw new Error(getErrorMessage(payload, 'Bestand konnte nicht geladen werden.'));
      dashboardState.storageProductsCache = (Array.isArray(payload) ? payload : []).map(normalizeStockProduct);
      renderStorageProducts();
      const fallbackProductIds = dashboardState.storageProductsCache.filter((item) => Number(item.stock_id || 0) <= 0 && Number(item.id || 0) > 0).length;
      const missingAllIds = dashboardState.storageProductsCache.filter((item) => Number(item.stock_id || 0) <= 0 && Number(item.id || 0) <= 0).length;
      const storageSummary = includeAllProducts
        ? {
          totalCount: dashboardState.storageProductsCache.length,
          inStockCount: dashboardState.storageProductsCache.filter((item) => item.in_stock).length,
          outOfStockCount: dashboardState.storageProductsCache.filter((item) => !item.in_stock).length,
        }
        : await fetchStorageSummaryCounts({
          query: filterValue,
          visibleItems: dashboardState.storageProductsCache,
        });
      if (!background) {
        status.textContent = missingAllIds > 0
        ? `Lagerbestand geladen (${fallbackProductIds} Einträge über Produkt-ID, ${missingAllIds} ohne nutzbare ID${storageSummary.outOfStockCount > 0 ? `, ${storageSummary.outOfStockCount} nicht auf Lager` : ''}).`
        : fallbackProductIds > 0
          ? `Lagerbestand geladen (${fallbackProductIds} Einträge über Produkt-ID${storageSummary.outOfStockCount > 0 ? `, ${storageSummary.outOfStockCount} nicht auf Lager` : ''}).`
          : storageSummary.outOfStockCount > 0
            ? `Lagerbestand geladen (${storageSummary.totalCount} Produkte, ${storageSummary.outOfStockCount} nicht auf Lager).`
            : `Lagerbestand geladen (${storageSummary.totalCount} Produkte).`;
      }
    } catch (error) {
      if (!background) {
        status.textContent = `Fehler: ${error.message}`;
      }
    }
  };

  if (background) {
    return load();
  }

  return withBusyState(load);
}

async function refreshStorageInBackground() {
  if (dashboardState.storageRefreshInFlight) return;
  if (document.hidden || dashboardState.activeTab !== 'storage') return;

  dashboardState.storageRefreshInFlight = true;
  try {
    await loadStorageProducts({ background: true });
  } finally {
    dashboardState.storageRefreshInFlight = false;
  }
}

function startStorageAutoRefresh() {
  if (dashboardState.storageRefreshTimer) {
    clearInterval(dashboardState.storageRefreshTimer);
  }

  dashboardState.storageRefreshTimer = setInterval(() => {
    refreshStorageInBackground();
  }, shoppingListRefreshMs);
}

async function consumeStorageProduct(stockId) {
  const status = getStorageStatusElement();
  const key = ensureApiKey();
  if (!key) return;

  try {
    const normalizedStockId = Number(stockId);
    const stockItem = dashboardState.storageProductsCache.find((item) => {
      if (Number(item?.stock_id) === normalizedStockId) return true;
      return Number(item?.id) === normalizedStockId;
    });
    const productId = Number(stockItem?.id || 0);
    const { response, payload } = await dashboardApi.consumeStockProduct(stockId, { amount: 1, productId });
    if (!response.ok) throw new Error(getErrorMessage(payload, 'Produkt konnte nicht verbraucht werden.'));
    status.textContent = 'Produkt wurde verbraucht.';
    await loadStorageProducts();
  } catch (error) {
    status.textContent = `Fehler: ${error.message}`;
  }
}

function openStorageEditModal(stockId) {
  const normalizedStockId = Number(stockId);
  const stockItem = dashboardState.storageProductsCache.find((item) => {
    if (Number(item?.stock_id) === normalizedStockId) return true;
    return Number(item?.id) === normalizedStockId;
  });
  if (!stockItem) return;
  dashboardState.storageEditingItem = stockItem;
  dashboardState.storageEditingTargetId = normalizedStockId;
  document.getElementById('storage-edit-modal-title').textContent = `Bestand ändern: ${stockItem.name}`;
  document.getElementById('storage-edit-amount').value = String(stockItem.amount || '0').replace(',', '.');
  document.getElementById('storage-edit-best-before').value = stockItem.best_before_date || '';
  renderStorageEditLocationOptions(stockItem.location_id, stockItem.location_name || '');
  document.getElementById('storage-edit-calories').value = String(stockItem.calories || '').replace(',', '.');
  document.getElementById('storage-edit-carbs').value = String(stockItem.carbs || '').replace(',', '.');
  document.getElementById('storage-edit-fat').value = String(stockItem.fat || '').replace(',', '.');
  document.getElementById('storage-edit-protein').value = String(stockItem.protein || '').replace(',', '.');
  document.getElementById('storage-edit-sugar').value = String(stockItem.sugar || '').replace(',', '.');

  const picture = document.getElementById('storage-edit-picture');
  if (picture) {
    const pictureUrl = String(stockItem.picture_url || '').trim();
    if (pictureUrl) {
      picture.src = toImageSource(pictureUrl, { size: 'full' });
      picture.classList.remove('hidden');
    } else {
      picture.removeAttribute('src');
      picture.classList.add('hidden');
    }
  }

  document.getElementById('storage-edit-modal').classList.remove('hidden');
  syncModalScrollLock();

  const productId = Number(stockItem?.id || 0);
  if (!Number.isFinite(productId) || productId <= 0) {
    return;
  }

  (async () => {
    try {
      const { response, payload } = await dashboardApi.fetchProductNutrition(productId);
      if (!response.ok || !payload || typeof payload !== 'object') return;

      document.getElementById('storage-edit-calories').value = String(payload.calories || '').replace(',', '.');
      document.getElementById('storage-edit-carbs').value = String(payload.carbs || '').replace(',', '.');
      document.getElementById('storage-edit-fat').value = String(payload.fat || '').replace(',', '.');
      document.getElementById('storage-edit-protein').value = String(payload.protein || '').replace(',', '.');
      document.getElementById('storage-edit-sugar').value = String(payload.sugar || '').replace(',', '.');
    } catch (error) {
      console.debug('Nutrition userfields could not be loaded for storage edit modal:', error);
    }
  })();
}

function closeStorageEditModal() {
  dashboardState.storageEditingItem = null;
  dashboardState.storageEditingTargetId = null;
  const picture = document.getElementById('storage-edit-picture');
  if (picture) {
    picture.removeAttribute('src');
    picture.classList.add('hidden');
  }
  document.getElementById('storage-edit-calories').value = '';
  document.getElementById('storage-edit-carbs').value = '';
  document.getElementById('storage-edit-fat').value = '';
  document.getElementById('storage-edit-protein').value = '';
  document.getElementById('storage-edit-sugar').value = '';
  renderStorageEditLocationOptions();
  document.getElementById('storage-edit-modal').classList.add('hidden');
  syncModalScrollLock();
}

async function saveStorageEditModal() {
  if (!dashboardState.storageEditingItem || !Number.isFinite(dashboardState.storageEditingTargetId) || dashboardState.storageEditingTargetId <= 0) return;
  const status = getStorageStatusElement();
  const amountRaw = String(document.getElementById('storage-edit-amount').value || '').trim().replace(',', '.');
  const amount = Number(amountRaw);
  const bestBeforeDate = document.getElementById('storage-edit-best-before').value || '';
  const locationValue = document.getElementById('storage-edit-location-select').value || '';
  const locationId = Number(locationValue);
  const calories = normalizeNutritionInputValue(document.getElementById('storage-edit-calories').value);
  const carbs = normalizeNutritionInputValue(document.getElementById('storage-edit-carbs').value);
  const fat = normalizeNutritionInputValue(document.getElementById('storage-edit-fat').value);
  const protein = normalizeNutritionInputValue(document.getElementById('storage-edit-protein').value);
  const sugar = normalizeNutritionInputValue(document.getElementById('storage-edit-sugar').value);

  if (!Number.isFinite(amount) || amount < 0) {
    status.textContent = 'Bitte eine gültige Menge eingeben.';
    return;
  }
  if ([calories, carbs, fat, protein, sugar].some((value) => Number.isNaN(value))) {
    status.textContent = 'Bitte gültige Nährwerte (>= 0) eingeben.';
    return;
  }

  try {
    const productId = Number(dashboardState.storageEditingItem?.id || 0);
    const { response, payload } = await dashboardApi.updateStockProduct(
      dashboardState.storageEditingTargetId,
      {
        amount,
        best_before_date: bestBeforeDate,
        location_id: Number.isFinite(locationId) && locationId > 0 ? locationId : null,
        calories,
        carbs,
        fat,
        protein,
        sugar,
      },
      { productId },
    );
    if (!response.ok) throw new Error(getErrorMessage(payload, 'Bestand konnte nicht aktualisiert werden.'));
    closeStorageEditModal();
    status.textContent = 'Bestand wurde aktualisiert.';
    await loadStorageProducts();
  } catch (error) {
    status.textContent = `Fehler: ${error.message}`;
  }
}


async function deleteStorageEditPicture() {
  if (!dashboardState.storageEditingItem) return;
  const productId = Number(dashboardState.storageEditingItem.id || 0);
  if (!Number.isFinite(productId) || productId <= 0) return;

  const status = getStorageStatusElement();
  const productName = dashboardState.storageEditingItem.name || 'dieses Produkt';
  const confirmed = window.confirm(`Soll das Produktbild von ${productName} wirklich gelöscht werden?`);
  if (!confirmed) return;

  try {
    const { response, payload } = await dashboardApi.deleteProductPicture(productId);
    if (!response.ok) throw new Error(getErrorMessage(payload, 'Produktbild konnte nicht gelöscht werden.'));
    status.textContent = payload?.message || 'Produktbild wurde gelöscht.';
    await loadStorageProducts();
    const refreshedItem = dashboardState.storageProductsCache.find((item) => Number(item.id || 0) === productId);
    if (refreshedItem) {
      openStorageEditModal(getActionableStorageId(refreshedItem));
    }
  } catch (error) {
    status.textContent = `Fehler: ${error.message}`;
  }
}

async function deleteStorageEditItem() {
  if (!dashboardState.storageEditingItem || !Number.isFinite(dashboardState.storageEditingTargetId) || dashboardState.storageEditingTargetId <= 0) return;
  const status = getStorageStatusElement();
  const productName = dashboardState.storageEditingItem.name || 'dieses Produkt';
  const confirmed = window.confirm(`Soll ${productName} wirklich aus dem Bestand gelöscht werden?`);
  if (!confirmed) return;

  try {
    const productId = Number(dashboardState.storageEditingItem?.id || 0);
    const { response, payload } = await dashboardApi.deleteStockProduct(
      dashboardState.storageEditingTargetId,
      { productId },
    );
    if (!response.ok) throw new Error(getErrorMessage(payload, 'Bestandseintrag konnte nicht gelöscht werden.'));
    closeStorageEditModal();
    status.textContent = payload?.message || 'Bestandseintrag wurde gelöscht.';
    await loadStorageProducts();
  } catch (error) {
    status.textContent = `Fehler: ${error.message}`;
  }
}

function preloadRecipeSuggestionsOnStartup() {
  if (recipeState.initialized) return;
  loadLocations();
}

async function loadRecipeSuggestions(options = {}) {
  return withBusyState(async () => {
  const key = ensureApiKey();
  const status = getRecipeStatusElement();
  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return;
  }

  const usePrefetchedCache = Boolean(options.usePrefetchedCache);
  const selectedIds = usePrefetchedCache ? [] : getSelectedProductIds();
  recipeState.selectedProductIds = selectedIds;
  const selectedLocationIds = usePrefetchedCache ? [] : getSelectedLocationIds();
  recipeState.selectedLocationIds = selectedLocationIds;
  const soonExpiringOnly = Boolean(options.soonExpiringOnly);
  const expiringWithinDays = Number(options.expiringWithinDays || 3);

  if (soonExpiringOnly) {
    status.textContent = `Lade Rezepte mit bald ablaufenden Produkten (<= ${expiringWithinDays} Tage)...`;
  } else {
    status.textContent = usePrefetchedCache
      ? 'Lade initiale Rezeptvorschläge aus dem Cache...'
      : selectedIds.length
        ? 'Lade Rezeptvorschläge für Auswahl...'
        : 'Lade Rezeptvorschläge aus dem aktuellen Lagerbestand...';
  }

  try {
    const { response, payload } = await dashboardApi.fetchRecipeSuggestions({
      product_ids: selectedIds,
      location_ids: selectedLocationIds,
      soon_expiring_only: soonExpiringOnly,
      expiring_within_days: expiringWithinDays,
    });
    if (!response.ok) {
      status.textContent = getErrorMessage(payload, 'Rezeptvorschläge konnten nicht geladen werden.');
      return;
    }

    renderRecipeList('grocy-recipe-list', (payload.grocy_recipes || []).slice(0, GROCY_RECIPE_DISPLAY_LIMIT), 'Keine gespeicherten Grocy-Rezepte gefunden.');
    renderRecipeList('ai-recipe-list', (payload.ai_recipes || []).slice(0, AI_RECIPE_DISPLAY_LIMIT), 'Keine KI-Rezepte erzeugt.');
    status.textContent = 'Rezeptvorschläge geladen für: Alles';
  } catch (_) {
    status.textContent = 'Rezeptvorschläge konnten nicht geladen werden (Netzwerk-/Ingress-Fehler).';
  }

  });
}

function loadExpiringRecipeSuggestions() {
  const daysInput = document.getElementById('expiring-days');
  const parsedDays = Number(daysInput?.value || 3);
  const expiringWithinDays = Math.min(30, Math.max(1, Number.isFinite(parsedDays) ? Math.round(parsedDays) : 3));
  if (daysInput) daysInput.value = String(expiringWithinDays);
  loadRecipeSuggestions({ soonExpiringOnly: true, expiringWithinDays });
}


function openRecipeDetails(item) {
  const modal = document.getElementById('recipe-modal');
  const title = document.getElementById('recipe-modal-title');
  const reason = document.getElementById('recipe-modal-reason');
  const preparation = document.getElementById('recipe-modal-preparation');
  const ingredients = document.getElementById('recipe-modal-ingredients');
  const missingProducts = document.getElementById('recipe-modal-missing-products');
  const addButton = document.getElementById('recipe-add-missing-button');
  const imageWrapper = document.getElementById('recipe-modal-image-wrapper');
  const image = document.getElementById('recipe-modal-image');

  dashboardState.activeRecipeItem = item;
  title.textContent = item.title || 'Rezeptdetails';
  reason.textContent = item.reason || '';
  preparation.textContent = item.preparation || 'Keine Zubereitungsdetails vorhanden.';

  const ingredientItems = Array.isArray(item.ingredients) ? item.ingredients : [];
  if (!ingredientItems.length) {
    ingredients.innerHTML = '<li class="muted">Keine Zutatenliste vorhanden.</li>';
  } else {
    ingredients.innerHTML = ingredientItems.map((ingredient) => `<li>${ingredient}</li>`).join('');
  }

  const missingItems = Array.isArray(item.missing_products) ? item.missing_products : [];
  if (!missingItems.length) {
    missingProducts.innerHTML = '<li class="muted">Keine fehlenden Produkte.</li>';
  } else {
    missingProducts.innerHTML = missingItems.map((product) => `<li>${product.name}</li>`).join('');
  }

  const recipeImageSource = toImageSource(item.picture_url || '', { size: 'full' });
  if (recipeImageSource && imageWrapper && image) {
    image.src = recipeImageSource;
    image.alt = item.title ? `${item.title} Rezeptbild` : 'Rezeptbild';
    imageWrapper.classList.remove('hidden');
    imageWrapper.setAttribute('aria-hidden', 'false');
  } else if (imageWrapper && image) {
    image.src = '';
    image.alt = '';
    imageWrapper.classList.add('hidden');
    imageWrapper.setAttribute('aria-hidden', 'true');
  }

  addButton.disabled = !(item.source === 'grocy' && Number.isInteger(item.recipe_id));
  modal.classList.remove('hidden');
  syncModalScrollLock();
}

function closeRecipeDetails() {
  const modal = document.getElementById('recipe-modal');
  const imageWrapper = document.getElementById('recipe-modal-image-wrapper');
  const image = document.getElementById('recipe-modal-image');
  modal.classList.add('hidden');
  if (imageWrapper && image) {
    image.src = '';
    image.alt = '';
    imageWrapper.classList.add('hidden');
    imageWrapper.setAttribute('aria-hidden', 'true');
  }
  dashboardState.activeRecipeItem = null;
  syncModalScrollLock();
}

function openRecipeCreateModal() {
  const modal = document.getElementById('recipe-create-modal');
  if (!modal) return;
  modal.classList.remove('hidden');
  setRecipeCreateMethod(recipeCreateState.method || 'webscrape');
  syncModalScrollLock();
}

function closeRecipeCreateModal() {
  const modal = document.getElementById('recipe-create-modal');
  if (!modal) return;
  modal.classList.add('hidden');
  syncModalScrollLock();
}

function setRecipeCreateMethod(method) {
  const methods = ['webscrape', 'ai', 'manual'];
  const nextMethod = methods.includes(method) ? method : 'webscrape';
  recipeCreateState.method = nextMethod;

  methods.forEach((item) => {
    const methodButton = document.getElementById(`recipe-create-method-${item}`);
    const methodPanel = document.getElementById(`recipe-create-panel-${item}`);
    if (methodButton) methodButton.classList.toggle('active', item === nextMethod);
    if (methodPanel) methodPanel.classList.toggle('hidden', item !== nextMethod);
  });
}

function setRecipeCreateStatus(message) {
  const status = getRecipeStatusElement();
  if (status) status.textContent = message;
}

function submitRecipeCreateWebscrape() {
  const urlInput = document.getElementById('recipe-webscrape-url');
  const rawUrl = String(urlInput?.value || '').trim();
  if (!rawUrl) {
    setRecipeCreateStatus('Bitte zuerst eine URL für WebScrape eingeben.');
    return;
  }

  try {
    const parsedUrl = new URL(rawUrl);
    setRecipeCreateStatus(`WebScrape-URL erfasst: ${parsedUrl.toString()}`);
    closeRecipeCreateModal();
  } catch (_) {
    setRecipeCreateStatus('Bitte eine gültige URL angeben (inkl. http/https).');
  }
}

function submitRecipeCreateAiPrompt() {
  const promptInput = document.getElementById('recipe-ai-prompt');
  const prompt = String(promptInput?.value || '').trim();
  if (!prompt) {
    setRecipeCreateStatus('Bitte eine KI-Anfrage für das Rezept eingeben.');
    return;
  }

  setRecipeCreateStatus('KI-Rezeptanfrage erfasst. Nächster Schritt: Attribut-Extraktion anbinden.');
  closeRecipeCreateModal();
}

function submitRecipeCreateManual() {
  const title = String(document.getElementById('recipe-manual-title')?.value || '').trim();
  const ingredientsRaw = String(document.getElementById('recipe-manual-ingredients')?.value || '').trim();
  if (!title) {
    setRecipeCreateStatus('Bitte einen Rezeptnamen eingeben.');
    return;
  }
  if (!ingredientsRaw) {
    setRecipeCreateStatus('Bitte mindestens eine Zutat für das manuelle Rezept eingeben.');
    return;
  }

  const servings = Number(document.getElementById('recipe-manual-servings')?.value || '1');
  const ingredientCount = ingredientsRaw.split('\n').map((entry) => entry.trim()).filter(Boolean).length;
  setRecipeCreateStatus(`Manuelles Rezept erfasst: ${title} (${Math.max(1, servings)} Portionen, ${ingredientCount} Zutaten).`);
  closeRecipeCreateModal();
}

function bindRecipeItemInteractions() {
  const recipes = document.querySelectorAll('.recipe-item[data-recipe-item]');
  recipes.forEach((recipe) => {
    recipe.style.cursor = 'pointer';
    recipe.onclick = () => {
      try {
        const payloadText = decodeURIComponent(recipe.dataset.recipeItem || '');
        const payload = JSON.parse(payloadText || '{}');
        openRecipeDetails(payload);
      } catch (_) {
        // ignore malformed payload
      }
    };
  });
}

async function addMissingRecipeProducts() {
  const key = ensureApiKey();
  const status = getRecipeStatusElement();
  if (!key || !dashboardState.activeRecipeItem || !Number.isInteger(dashboardState.activeRecipeItem.recipe_id)) return;

  try {
    const { response, payload } = await dashboardApi.addMissingRecipeProducts(dashboardState.activeRecipeItem.recipe_id);
    if (!response.ok) {
      status.textContent = getErrorMessage(payload, 'Fehlende Produkte konnten nicht hinzugefügt werden.');
      return;
    }

    status.textContent = payload.message || 'Fehlende Produkte wurden hinzugefügt.';
    closeRecipeDetails();
    await loadShoppingList();
  } catch (_) {
    status.textContent = 'Fehlende Produkte konnten nicht hinzugefügt werden (Netzwerk-/Ingress-Fehler).';
  }
}


function getScannerStatusElement() {
  return document.getElementById('status-scanner');
}

function getScannerLightWarningElement() {
  return document.getElementById('scanner-light-warning');
}

function getScannerCameraSelectElement() {
  return document.getElementById('scanner-camera-select');
}

function getScannerRotationSelectElement() {
  return document.getElementById('scanner-rotation-select');
}

function applyScannerVideoRotation(videoElement) {
  if (!videoElement) return;
  videoElement.classList.remove('rotated-90', 'rotated-180', 'rotated-270');
  if (dashboardState.scannerRotationDegrees === 90) videoElement.classList.add('rotated-90');
  if (dashboardState.scannerRotationDegrees === 180) videoElement.classList.add('rotated-180');
  if (dashboardState.scannerRotationDegrees === 270) videoElement.classList.add('rotated-270');
}

function parseScannerRotationDegrees(value) {
  const rotation = Number(value);
  if (![0, 90, 180, 270].includes(rotation)) return 0;
  return rotation;
}

function onScannerRotationChange() {
  const select = getScannerRotationSelectElement();
  dashboardState.scannerRotationDegrees = parseScannerRotationDegrees(select?.value ?? 0);
  const video = document.getElementById('scanner-video');
  applyScannerVideoRotation(video);
}


function setScannerLightWarningVisible(visible) {
  const warning = getScannerLightWarningElement();
  if (!warning) return;
  warning.classList.toggle('hidden', !visible);
}

async function refreshScannerDevices() {
  const select = getScannerCameraSelectElement();
  if (!select || !navigator.mediaDevices?.enumerateDevices) return;

  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    dashboardState.scannerKnownDevices = devices.filter((device) => device.kind === 'videoinput');

    const options = ["<option value=''>Automatisch (Rückkamera)</option>"];
    dashboardState.scannerKnownDevices.forEach((device, index) => {
      const label = device.label || `Kamera ${index + 1}`;
      const selected = dashboardState.scannerSelectedDeviceId && dashboardState.scannerSelectedDeviceId === device.deviceId ? ' selected' : '';
      options.push(`<option value="${escapeHtml(device.deviceId)}"${selected}>${escapeHtml(label)}</option>`);
    });
    select.innerHTML = options.join('');
  } catch (error) {
    console.warn('Could not enumerate video devices', error);
  }
}

async function onScannerCameraChange() {
  const select = getScannerCameraSelectElement();
  if (!select) return;
  dashboardState.scannerSelectedDeviceId = select.value || '';
  if (!dashboardState.scannerStream) return;

  const status = getScannerStatusElement();
  status.textContent = 'Kamerawechsel… Scanner startet neu.';
  await startBarcodeScanner();
}

function evaluateScannerLight(video, canvas) {
  if (!video?.videoWidth || !video?.videoHeight || !canvas) return;
  const now = Date.now();
  if ((now - dashboardState.scannerLastLightCheckAt) < scannerLightCheckIntervalMs) return;
  dashboardState.scannerLastLightCheckAt = now;

  const context = canvas.getContext('2d', { willReadFrequently: true });
  if (!context) return;

  const sampleWidth = 64;
  const sampleHeight = 36;
  canvas.width = sampleWidth;
  canvas.height = sampleHeight;
  context.drawImage(video, 0, 0, sampleWidth, sampleHeight);

  let brightnessTotal = 0;
  const pixels = context.getImageData(0, 0, sampleWidth, sampleHeight).data;
  for (let i = 0; i < pixels.length; i += 4) {
    brightnessTotal += (pixels[i] + pixels[i + 1] + pixels[i + 2]) / 3;
  }

  const averageBrightness = brightnessTotal / (pixels.length / 4);
  setScannerLightWarningVisible(averageBrightness < scannerLightWarningThreshold);
}

function renderScannerResult(payload) {
  const container = document.getElementById('scanner-result');
  if (!container) return;
  const createButton = document.getElementById('scanner-create-product-button');

  if (!payload || !payload.found) {
    dashboardState.scannerResultPayload = null;
    container.classList.add('hidden');
    container.innerHTML = '';
    if (createButton) {
      createButton.classList.add('hidden');
      createButton.disabled = false;
      createButton.textContent = '➕ Erkanntes Produkt anlegen';
    }
    return;
  }

  dashboardState.scannerResultPayload = payload;
  const canCreateDetectedProduct = payload.source !== 'Grocy' && payload.source !== 'scanner_created';
  if (createButton) {
    createButton.classList.toggle('hidden', !canCreateDetectedProduct);
    createButton.disabled = dashboardState.scannerCreateInFlight;
    createButton.textContent = dashboardState.scannerCreateInFlight
      ? 'Lege Produkt an…'
      : '➕ Erkanntes Produkt anlegen';
  }

  container.classList.remove('hidden');
  container.innerHTML = `
    <h3>${payload.product_name || 'Unbekanntes Produkt'}</h3>
    <ul>
      <li><strong>Barcode:</strong> ${payload.barcode || '-'}</li>
      <li><strong>Marke:</strong> ${payload.brand || '-'}</li>
      <li><strong>Menge:</strong> ${payload.quantity || '-'}</li>
      <li><strong>Nährwert-Grad:</strong> ${payload.nutrition_grade || '-'}</li>
      <li><strong>Zutaten:</strong> ${payload.ingredients_text || '-'}</li>
    </ul>
    ${actionMarkup}
  `;
}

async function createProductFromScannerResult() {
  const key = ensureApiKey();
  const status = getScannerStatusElement();
  const payload = dashboardState.scannerResultPayload;

  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return;
  }

  if (!payload || !payload.found) {
    status.textContent = 'Kein erfasstes Produkt zum Anlegen vorhanden.';
    return;
  }

  if (payload.source === 'Grocy') {
    status.textContent = 'Dieses Produkt existiert bereits in Grocy.';
    return;
  }

  if (dashboardState.scannerCreateInFlight) return;
  dashboardState.scannerCreateInFlight = true;
  renderScannerResult(payload);
  status.textContent = `Lege ${payload.product_name || 'Produkt'} über den Scanner an...`;

  try {
    const { response, payload: createPayload } = await dashboardApi.createScannerProduct({
      product_name: payload.product_name || '',
      source: payload.source || 'scanner',
      barcode: payload.barcode || '',
      brand: payload.brand || '',
      quantity: payload.quantity || '',
      ingredients_text: payload.ingredients_text || '',
      nutrition_grade: payload.nutrition_grade || '',
      hint: payload.hint || '',
    });
    if (!response.ok) {
      status.textContent = getErrorMessage(createPayload, 'Produkt konnte nicht angelegt werden.');
      return;
    }

    status.textContent = createPayload.message || 'Produkt wurde angelegt.';
    dashboardState.scannerResultPayload = { ...payload, source: 'scanner_created' };
    renderScannerResult(dashboardState.scannerResultPayload);
    await loadShoppingList();
  } catch (_) {
    status.textContent = 'Produkt konnte nicht angelegt werden (Netzwerk-/Ingress-Fehler).';
  } finally {
    dashboardState.scannerCreateInFlight = false;
    renderScannerResult(dashboardState.scannerResultPayload);
  }
}


function getScannerLlavaDelaySeconds() {
  const configuredFallback = Number(rootElement.dataset.scannerLlavaFallbackSeconds || 5);
  if (!Number.isFinite(configuredFallback)) return 5;
  return Math.max(1, Math.min(30, Math.round(configuredFallback)));
}


function getScannerLlavaTimeoutSeconds() {
  const configuredTimeout = Number(rootElement.dataset.scannerLlavaTimeoutSeconds || 45);
  if (!Number.isFinite(configuredTimeout)) return 45;
  return Math.max(10, Math.min(120, Math.round(configuredTimeout)));
}

function getScannerLlavaAutoCooldownMs() {
  return Math.max(getScannerLlavaDelaySeconds() * 1000, 15000);
}

function captureScannerFrameBase64() {
  const video = document.getElementById('scanner-video');
  const canvas = document.getElementById('scanner-canvas');
  if (!video || !canvas || !video.videoWidth || !video.videoHeight) return '';

  const context = canvas.getContext('2d', { willReadFrequently: true });
  if (!context) return '';

  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  context.drawImage(video, 0, 0, canvas.width, canvas.height);

  const dataUrl = canvas.toDataURL('image/jpeg', 0.9);
  return String(dataUrl).replace(/^data:image\/\w+;base64,/, '');
}

async function queryLlavaWithCurrentFrame(reason = 'manual') {
  const key = ensureApiKey();
  const status = getScannerStatusElement();
  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return;
  }

  if (dashboardState.scannerLlavaInFlight) return;
  dashboardState.scannerLlavaInFlight = true;
  dashboardState.scannerLlavaLastRequestAt = Date.now();

  if (reason === 'timeout') {
    status.textContent = 'Kein Barcode gefunden. Starte KI-Produkterkennung mit LLaVA...';
  } else {
    status.textContent = 'Starte KI-Produkterkennung mit LLaVA...';
  }

  try {
    const imageBase64 = captureScannerFrameBase64();
    if (!imageBase64) {
      status.textContent = 'Kein Kamerabild verfügbar für LLaVA.';
      return;
    }

    const llavaTimeoutMs = getScannerLlavaTimeoutSeconds() * 1000;
    const abortController = new AbortController();
    const timeoutHandle = setTimeout(() => abortController.abort(), llavaTimeoutMs);

    let res;
    let payload = {};
    try {
      ({ response: res, payload } = await dashboardApi.requestScannerLlava(imageBase64, {
        signal: abortController.signal,
      }));
    } finally {
      clearTimeout(timeoutHandle);
    }

    if (!res.ok) {
      status.textContent = getErrorMessage(payload, 'LLaVA konnte nicht abgefragt werden.');
      return;
    }

    if (!payload.success) {
      status.textContent = 'LLaVA hat kein eindeutiges Produkt erkannt.';
      return;
    }

    status.textContent = `LLaVA erkannt: ${payload.product_name || 'Unbekanntes Produkt'}`;
    renderScannerResult({
      found: true,
      barcode: '-',
      product_name: payload.product_name || 'Unbekanntes Produkt',
      brand: payload.brand || '-',
      quantity: payload.hint || '-',
      ingredients_text: payload.hint || '-',
      hint: payload.hint || '',
      nutrition_grade: payload.source || 'LLaVA',
      source: payload.source || 'ollama_llava',
    });
  } catch (error) {
    if (error?.name === 'AbortError') {
      status.textContent = `LLaVA-Anfrage dauerte länger als ${getScannerLlavaTimeoutSeconds()}s und wurde beendet.`;
    } else {
      status.textContent = 'LLaVA konnte nicht abgefragt werden (Netzwerk-/Ingress-Fehler).';
    }
  } finally {
    dashboardState.scannerLlavaInFlight = false;
  }
}


function isScannerModalVisible() {
  const modal = document.getElementById('scanner-modal');
  return Boolean(modal && !modal.classList.contains('hidden'));
}

function scheduleLlavaFallback() {
  if (dashboardState.scannerLlavaTimer) {
    clearTimeout(dashboardState.scannerLlavaTimer);
  }
  const waitMs = getScannerLlavaDelaySeconds() * 1000;
  dashboardState.scannerLlavaTimer = setTimeout(() => {
    if (!isScannerModalVisible() || !dashboardState.scannerStream) return;
    const elapsed = Date.now() - dashboardState.scannerLastBarcodeAt;
    if (elapsed >= waitMs - 100) {
      const autoCooldownMs = getScannerLlavaAutoCooldownMs();
      const sinceLastLlavaMs = Date.now() - dashboardState.scannerLlavaLastRequestAt;
      if (sinceLastLlavaMs >= autoCooldownMs) {
        queryLlavaWithCurrentFrame('timeout');
      }
    }
    scheduleLlavaFallback();
  }, waitMs);
}

async function triggerLlavaScan() {
  await queryLlavaWithCurrentFrame('manual');
}

function normalizeBarcodeForLookup(barcode) {
  const digitsOnly = String(barcode || '').replace(/\D/g, '');
  if (!digitsOnly) return '';

  if (digitsOnly.length >= 16 && digitsOnly.startsWith('01')) {
    const gtin14 = digitsOnly.slice(2, 16);
    if (gtin14.startsWith('0')) {
      return gtin14.slice(1);
    }
    return gtin14;
  }

  if ([8, 12, 13, 14].includes(digitsOnly.length)) {
    return digitsOnly;
  }

  if (digitsOnly.length > 14) {
    return digitsOnly.slice(-13);
  }

  return digitsOnly;
}

function registerScannerCandidate(rawBarcode) {
  const normalized = normalizeBarcodeForLookup(rawBarcode);
  if (!normalized || normalized.length < 8) return '';

  if (normalized === dashboardState.scannerLastBarcode) {
    dashboardState.scannerStableCandidate = normalized;
    dashboardState.scannerStableCount = scannerStableDetectionThreshold;
    return '';
  }

  if (normalized === dashboardState.scannerStableCandidate) {
    dashboardState.scannerStableCount += 1;
  } else {
    dashboardState.scannerStableCandidate = normalized;
    dashboardState.scannerStableCount = 1;
  }

  if (dashboardState.scannerStableCount < scannerStableDetectionThreshold) {
    return '';
  }

  dashboardState.scannerStableCount = 0;
  dashboardState.scannerStableCandidate = '';
  return normalized;
}

async function lookupBarcode(barcode) {
  const key = ensureApiKey();
  const status = getScannerStatusElement();
  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return;
  }

  const normalized = normalizeBarcodeForLookup(barcode);
  if (normalized.length < 8) return;

  dashboardState.scannerLastBarcode = normalized;
  dashboardState.scannerLastBarcodeAt = Date.now();
  status.textContent = `Barcode erkannt: ${normalized}. Lade Produktdaten...`;

  try {
    const { response, payload } = await dashboardApi.lookupBarcode(normalized);
    if (!response.ok) {
      status.textContent = getErrorMessage(payload, 'Barcode konnte nicht abgefragt werden.');
      return;
    }

    if (!payload.found) {
      status.textContent = `Kein Produkt für Barcode ${normalized} gefunden.`;
      renderScannerResult(null);
      return;
    }

    status.textContent = `Produkt geladen: ${payload.product_name || normalized}`;
    renderScannerResult(payload);
  } catch (_) {
    status.textContent = 'Barcode konnte nicht abgefragt werden (Netzwerk-/Ingress-Fehler).';
  }
}

function hasCompatibleGetUserMedia() {
  return Boolean(
    navigator?.mediaDevices?.getUserMedia
    || navigator?.getUserMedia
    || navigator?.webkitGetUserMedia
    || navigator?.mozGetUserMedia
    || navigator?.msGetUserMedia,
  );
}

async function requestCompatibleUserMedia(constraints) {
  if (navigator?.mediaDevices?.getUserMedia) {
    return navigator.mediaDevices.getUserMedia(constraints);
  }

  const legacyGetUserMedia = navigator?.getUserMedia
    || navigator?.webkitGetUserMedia
    || navigator?.mozGetUserMedia
    || navigator?.msGetUserMedia;

  if (!legacyGetUserMedia) {
    throw new Error('getUserMedia wird nicht unterstützt');
  }

  return new Promise((resolve, reject) => {
    legacyGetUserMedia.call(navigator, constraints, resolve, reject);
  });
}

async function startBarcodeScanner() {
  const status = getScannerStatusElement();
  const video = document.getElementById('scanner-video');
  const canvas = document.getElementById('scanner-canvas');
  const startButton = document.getElementById('start-scan-button');
  const stopButton = document.getElementById('stop-scan-button');
  if (!hasCompatibleGetUserMedia()) {
    status.textContent = 'Kamera wird von diesem Browser/WebView nicht unterstützt.';
    return;
  }

  try {
    stopBarcodeScanner();

    dashboardState.scannerStream = await getCompatibleScannerStream();
    await refreshScannerDevices();

    await optimizeScannerTrack(dashboardState.scannerStream, status);
    scheduleScannerFocusRefresh(dashboardState.scannerStream);

    video.setAttribute('playsinline', 'true');
    video.setAttribute('autoplay', 'true');
    video.setAttribute('muted', 'true');
    video.playsInline = true;
    video.autoplay = true;
    video.muted = true;
    video.srcObject = dashboardState.scannerStream;
    await video.play();
    video.classList.remove('hidden');
    applyScannerVideoRotation(video);
    startButton.classList.add('hidden');
    stopButton.classList.remove('hidden');
    if (!String(status.textContent || '').startsWith('Scanner aktiv')) {
      status.textContent = 'Scanner aktiv. Kamera stellt scharf… danach Barcode im Rahmen halten.';
    }
    dashboardState.scannerLastBarcodeAt = Date.now();
    dashboardState.scannerScanStartedAt = Date.now();
    dashboardState.scannerLastLightCheckAt = 0;
    setScannerLightWarningVisible(false);
    const overlay = document.getElementById('scanner-frame-overlay');
    if (overlay) overlay.classList.remove('hidden');
    scheduleLlavaFallback();

    if ('BarcodeDetector' in window) {
      dashboardState.scannerDetector = new window.BarcodeDetector({ formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e'] });
    }

    dashboardState.scannerInterval = setInterval(async () => {
      if (!isScannerModalVisible()) return;
      if (!video.videoWidth || !video.videoHeight) return;

      evaluateScannerLight(video, canvas);

      if (Date.now() - dashboardState.scannerScanStartedAt < scannerAnalysisWarmupMs) {
        status.textContent = 'Scanner aktiv. Kamera stellt scharf…';
        return;
      }

      if (status.textContent.includes('stellt scharf')) {
        status.textContent = 'Scanner aktiv. Barcode vor die Kamera halten...';
      }

      if (dashboardState.scannerDetector) {
        try {
          const detectionSource = getScannerDetectionSource(video, canvas, scannerDigitalZoomFactor);
          const barcodes = await dashboardState.scannerDetector.detect(detectionSource);
          if (barcodes.length) {
            const value = String(barcodes[0].rawValue || '').trim();
            const stableBarcode = registerScannerCandidate(value);
            if (stableBarcode && !dashboardState.scannerDetectionInFlight) {
              dashboardState.scannerDetectionInFlight = true;
              try {
                await lookupBarcode(stableBarcode);
              } finally {
                dashboardState.scannerDetectionInFlight = false;
              }
            }
          }
        } catch (_) {
          // Ignore detector errors and keep scanning
        }
      }
    }, 900);
  } catch (error) {
    const errorName = String(error?.name || '');
    if (!window.isSecureContext) {
      status.textContent = 'Kamerazugriff benötigt eine sichere Verbindung (HTTPS/Home-Assistant-App).';
    } else if (errorName === 'NotAllowedError' || errorName === 'SecurityError') {
      status.textContent = 'Kamera-Berechtigung wurde verweigert. Bitte Browser/App-Berechtigungen prüfen.';
    } else if (errorName === 'NotFoundError' || errorName === 'DevicesNotFoundError') {
      status.textContent = 'Keine Kamera gefunden.';
    } else {
      status.textContent = 'Kamera konnte nicht gestartet werden. Bitte Berechtigung prüfen.';
    }
  }
}

async function getCompatibleScannerStream() {
  const selectedDeviceConstraint = dashboardState.scannerSelectedDeviceId
    ? { deviceId: { exact: dashboardState.scannerSelectedDeviceId } }
    : { facingMode: { exact: 'environment' } };

  const fallbackFacingConstraint = dashboardState.scannerSelectedDeviceId
    ? { deviceId: { exact: dashboardState.scannerSelectedDeviceId } }
    : { facingMode: { ideal: 'environment' } };

  const streamProfiles = [
    {
      video: {
        ...selectedDeviceConstraint,
        width: { ideal: 2560 },
        height: { ideal: 1440 },
      },
      audio: false,
    },
    {
      video: {
        ...fallbackFacingConstraint,
        width: { ideal: 1920 },
        height: { ideal: 1080 },
      },
      audio: false,
    },
    {
      video: {
        ...fallbackFacingConstraint,
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false,
    },
    {
      video: dashboardState.scannerSelectedDeviceId ? { deviceId: { exact: dashboardState.scannerSelectedDeviceId } } : { facingMode: 'environment' },
      audio: false,
    },
    {
      video: true,
      audio: false,
    },
  ];

  let lastError = null;
  for (const constraints of streamProfiles) {
    try {
      return await requestCompatibleUserMedia(constraints);
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError || new Error('Kamera konnte nicht initialisiert werden.');
}

async function applyScannerFocusRefresh(track, focusMode) {
  if (!track || !focusMode || typeof track.applyConstraints !== 'function') return;

  try {
    await track.applyConstraints({ advanced: [{ focusMode }] });
  } catch (_) {
    // Ignore unsupported focus refresh requests.
  }
}

function scheduleScannerFocusRefresh(stream) {
  if (dashboardState.scannerFocusRefreshTimer) {
    clearInterval(dashboardState.scannerFocusRefreshTimer);
  }

  if (!stream || !['single-shot', 'continuous'].includes(dashboardState.scannerPreferredFocusMode)) {
    return;
  }

  const videoTrack = stream.getVideoTracks?.()[0];
  if (!videoTrack) return;

  dashboardState.scannerFocusRefreshTimer = setInterval(() => {
    if (!dashboardState.scannerStream || !isScannerModalVisible()) return;
    applyScannerFocusRefresh(videoTrack, dashboardState.scannerPreferredFocusMode);
  }, scannerFocusRefreshMs);
}

async function optimizeScannerTrack(stream, status) {
  const videoTrack = stream?.getVideoTracks?.()[0];
  if (!videoTrack) return;

  const capabilities = videoTrack.getCapabilities ? videoTrack.getCapabilities() : null;
  const constraints = {};

  if (capabilities?.focusMode?.includes('continuous')) {
    constraints.focusMode = 'continuous';
  } else if (capabilities?.focusMode?.includes('single-shot')) {
    constraints.focusMode = 'single-shot';
  } else if (capabilities?.focusMode?.includes('manual')) {
    constraints.focusMode = 'manual';
  }

  dashboardState.scannerPreferredFocusMode = constraints.focusMode || '';

  if (
    constraints.focusMode === 'manual'
    && capabilities?.focusDistance
    && typeof capabilities.focusDistance.min === 'number'
    && typeof capabilities.focusDistance.max === 'number'
  ) {
    const minDistance = Number(capabilities.focusDistance.min);
    const maxDistance = Number(capabilities.focusDistance.max);
    constraints.focusDistance = minDistance + ((maxDistance - minDistance) * 0.35);
  }

  if (capabilities?.pointsOfInterest) {
    constraints.pointsOfInterest = [{ x: 0.5, y: 0.5 }];
  }

  if (capabilities?.zoom) {
    const minZoom = Number(capabilities.zoom.min || 1);
    const maxZoom = Number(capabilities.zoom.max || minZoom);
    const preferredZoom = Math.max(minZoom, Math.min(maxZoom, 1.4));
    constraints.zoom = preferredZoom;
    status.textContent = `Scanner aktiv (Kamera-Zoom ${preferredZoom.toFixed(1)}x). Barcode vor die Kamera halten...`;
  }

  if (!Object.keys(constraints).length) return;

  try {
    await videoTrack.applyConstraints({ advanced: [constraints] });
    if (dashboardState.scannerPreferredFocusMode) {
      await applyScannerFocusRefresh(videoTrack, dashboardState.scannerPreferredFocusMode);
    }
  } catch (_) {
    // Ignore optimization failures and keep default stream settings.
  }
}

function getScannerDetectionSource(video, canvas, zoomFactor) {
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

  // For upright portrait frames, a 90° canvas turn improves barcode detector reliability.
  const autoPortraitQuarterTurn = dashboardState.scannerRotationDegrees === 0 && sourceHeight > sourceWidth;
  const rotation = autoPortraitQuarterTurn ? 90 : dashboardState.scannerRotationDegrees;
  const isQuarterTurn = rotation === 90 || rotation === 270;
  canvas.width = isQuarterTurn ? sourceHeight : sourceWidth;
  canvas.height = isQuarterTurn ? sourceWidth : sourceHeight;

  context.save();
  context.clearRect(0, 0, canvas.width, canvas.height);

  if (rotation === 90) {
    context.translate(canvas.width, 0);
    context.rotate(Math.PI / 2);
    context.drawImage(video, sourceX, sourceY, sourceWidth, sourceHeight, 0, 0, sourceWidth, sourceHeight);
  } else if (rotation === 180) {
    context.translate(canvas.width, canvas.height);
    context.rotate(Math.PI);
    context.drawImage(video, sourceX, sourceY, sourceWidth, sourceHeight, 0, 0, sourceWidth, sourceHeight);
  } else if (rotation === 270) {
    context.translate(0, canvas.height);
    context.rotate(-Math.PI / 2);
    context.drawImage(video, sourceX, sourceY, sourceWidth, sourceHeight, 0, 0, sourceWidth, sourceHeight);
  } else {
    context.drawImage(video, sourceX, sourceY, sourceWidth, sourceHeight, 0, 0, sourceWidth, sourceHeight);
  }

  context.restore();
  return canvas;
}

function stopBarcodeScanner() {
  const video = document.getElementById('scanner-video');
  const startButton = document.getElementById('start-scan-button');
  const stopButton = document.getElementById('stop-scan-button');

  if (dashboardState.scannerInterval) {
    clearInterval(dashboardState.scannerInterval);
    dashboardState.scannerInterval = null;
  }

  if (dashboardState.scannerLlavaTimer) {
    clearTimeout(dashboardState.scannerLlavaTimer);
    dashboardState.scannerLlavaTimer = null;
  }
  if (dashboardState.scannerFocusRefreshTimer) {
    clearInterval(dashboardState.scannerFocusRefreshTimer);
    dashboardState.scannerFocusRefreshTimer = null;
  }
  dashboardState.scannerPreferredFocusMode = '';
  dashboardState.scannerLlavaInFlight = false;
  dashboardState.scannerLlavaLastRequestAt = 0;
  dashboardState.scannerDetectionInFlight = false;
  dashboardState.scannerStableCandidate = '';
  dashboardState.scannerStableCount = 0;

  if (dashboardState.scannerStream) {
    dashboardState.scannerStream.getTracks().forEach((track) => track.stop());
    dashboardState.scannerStream = null;
  }

  if (video) {
    video.pause();
    video.srcObject = null;
    video.classList.add('hidden');
    video.classList.remove('rotated-90', 'rotated-180', 'rotated-270');
  }

  const overlay = document.getElementById('scanner-frame-overlay');
  if (overlay) overlay.classList.add('hidden');
  setScannerLightWarningVisible(false);

  if (startButton) startButton.classList.remove('hidden');
  if (stopButton) stopButton.classList.add('hidden');
}

Object.assign(window, {
  __grocyDashboardApi: dashboardApi,
  __grocyDashboardStore: dashboardStore,
  __grocyDashboardState: dashboardState,
  addMissingRecipeProducts,
  clearSearchInput,
  clearShoppingList,
  closeMhdPicker,
  closeNotificationRuleModal,
  closeRecipeCreateModal,
  closeRecipeDetails,
  closeScannerModal,
  closeShoppingItemDetails,
  closeStorageEditModal,
  completeShoppingList,
  createProductFromScannerResult,
  deleteStorageEditItem,
  deleteStorageEditPicture,
  loadExpiringRecipeSuggestions,
  loadNotificationOverview,
  loadRecipeSuggestions,
  loadShoppingList,
  loadStorageProducts,
  onScannerCameraChange,
  onScannerRotationChange,
  openNotificationRuleModal,
  openRecipeCreateModal,
  openScannerModal,
  openStorageEditModal,
  resetMhdPickerDate,
  saveMhdPickerDate,
  saveNotificationRule,
  saveShoppingAmountFromModal,
  saveStorageEditModal,
  searchProduct,
  setRecipeCreateMethod,
  startBarcodeScanner,
  stopBarcodeScanner,
  switchTab,
  testNotificationAll,
  testNotificationPersistent,
  toggleNotificationDevice,
  triggerLlavaScan,
});
