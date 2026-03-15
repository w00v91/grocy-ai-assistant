const rootElement = document.documentElement;
const configuredApiKey = rootElement.dataset.configuredApiKey || '';
const apiBasePath = rootElement.dataset.apiBasePath || '';
const themeStorageKey = 'grocy-dashboard-theme';
let apiKey = configuredApiKey || '';
const ingressPrefixMatch = window.location.pathname.match(/^\/api\/hassio_ingress\/[^\/]+/);
const ingressPrefix = ingressPrefixMatch ? ingressPrefixMatch[0] : '';

let pendingRequests = 0;
let activeRecipeItem = null;

const GROCY_RECIPE_DISPLAY_LIMIT = 3;
const AI_RECIPE_DISPLAY_LIMIT = 3;

let modalScrollLockY = 0;
let notificationEditingRuleId = null;
let storageProductsCache = [];
let storageEditingItem = null;
let storageEditingTargetId = null;

function normalizeStockProduct(item) {
  const productId = Number(item?.id ?? item?.product_id ?? 0);
  const stockId = Number(item?.stock_id ?? item?.stockId ?? 0);
  return {
    ...item,
    id: Number.isFinite(productId) && productId > 0 ? productId : null,
    stock_id: Number.isFinite(stockId) && stockId > 0 ? stockId : null,
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
  modalScrollLockY = window.scrollY || window.pageYOffset || 0;
  document.body.classList.add('modal-open');
  document.body.style.top = `-${modalScrollLockY}px`;
}

function unlockBodyScroll() {
  if (!document.body.classList.contains('modal-open')) return;
  document.body.classList.remove('modal-open');
  document.body.style.top = '';
  window.scrollTo(0, modalScrollLockY);
}

function syncModalScrollLock() {
  const hasVisibleModal = Boolean(document.querySelector('.shopping-modal:not(.hidden)'));
  if (hasVisibleModal) {
    lockBodyScroll();
    return;
  }
  unlockBodyScroll();
}

let activeTab = "shopping";
let scannerStream = null;
let scannerInterval = null;
let scannerLastBarcode = "";
let scannerDetector = null;
let scannerLastBarcodeAt = 0;
let scannerDetectionInFlight = false;
let scannerStableCandidate = '';
let scannerStableCount = 0;
let scannerLlavaInFlight = false;
let scannerLlavaTimer = null;
let scannerLlavaLastRequestAt = 0;
let scannerFocusRefreshTimer = null;
let scannerPreferredFocusMode = '';
let scannerSelectedDeviceId = '';
let scannerKnownDevices = [];
let scannerScanStartedAt = 0;
let scannerLastLightCheckAt = 0;
let scannerRotationDegrees = 0;
const scannerDigitalZoomFactor = 1.35;
const scannerStableDetectionThreshold = 2;
const scannerFocusRefreshMs = 2000;
const scannerAnalysisWarmupMs = 1200;
const scannerLightCheckIntervalMs = 1500;
const scannerLightWarningThreshold = 72;
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
  const spinner = document.getElementById('activity-spinner');
  if (!spinner) return;
  spinner.classList.toggle('hidden', !isBusy);
}

function beginRequest() {
  pendingRequests += 1;
  setBusyState(true);
}

function endRequest() {
  pendingRequests = Math.max(0, pendingRequests - 1);
  setBusyState(pendingRequests > 0);
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
  activeTab = allowedTabs.includes(tabName) ? tabName : 'shopping';

  const shoppingTab = document.getElementById('tab-shopping');
  const recipesTab = document.getElementById('tab-recipes');
  const storageTab = document.getElementById('tab-storage');
  const notificationsTab = document.getElementById('tab-notifications');
  const shoppingButton = document.getElementById('tab-button-shopping');
  const recipesButton = document.getElementById('tab-button-recipes');
  const storageButton = document.getElementById('tab-button-storage');
  const notificationsButton = document.getElementById('tab-button-notifications');

  shoppingTab.classList.toggle('hidden', activeTab !== 'shopping');
  recipesTab.classList.toggle('hidden', activeTab !== 'recipes');
  storageTab.classList.toggle('hidden', activeTab !== 'storage');
  notificationsTab.classList.toggle('hidden', activeTab !== 'notifications');
  shoppingButton.classList.toggle('active', activeTab === 'shopping');
  recipesButton.classList.toggle('active', activeTab === 'recipes');
  storageButton.classList.toggle('active', activeTab === 'storage');
  notificationsButton.classList.toggle('active', activeTab === 'notifications');

  if (activeTab === 'recipes' && !recipeState.initialized) {
    loadLocations();
  }
  if (activeTab === 'storage') {
    loadStorageProducts();
  }
  if (activeTab === 'notifications') {
    loadNotificationOverview();
  }
}


async function openScannerModal() {
  const modal = document.getElementById('scanner-modal');
  if (!modal) return;
  modal.classList.remove('hidden');
  syncModalScrollLock();
  await refreshScannerDevices();
  const rotationSelect = getScannerRotationSelectElement();
  if (rotationSelect) rotationSelect.value = String(scannerRotationDegrees);
}

function closeScannerModal() {
  const modal = document.getElementById('scanner-modal');
  if (!modal) return;
  modal.classList.add('hidden');
  stopBarcodeScanner();
  syncModalScrollLock();
}

function getNotificationStatusElement() {
  return document.getElementById('status-notifications');
}

async function loadNotificationOverview() {
  const status = getNotificationStatusElement();
  status.textContent = 'Lade Notification-Konfiguration…';
  try {
    const res = await fetch(buildApiUrl('/api/dashboard/notifications/overview'), { headers: getAuthHeaders() });
    const payload = await parseJsonSafe(res);
    if (!res.ok) throw new Error(getErrorMessage(payload, 'Fehler beim Laden der Notification-Daten.'));

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
  container.innerHTML = devices.map((device) => `
    <label class="notification-device-item">
      <input type="checkbox" ${device.active ? 'checked' : ''} onchange="toggleNotificationDevice('${device.id}', this.checked)" />
      <span><strong>${device.display_name}</strong><small>${device.service} · ${device.platform}</small></span>
    </label>
  `).join('');
}

function renderNotificationRules(rules) {
  window.__notificationRulesCache = Array.isArray(rules) ? rules : [];
  const list = document.getElementById('notification-rules');
  if (!Array.isArray(rules) || rules.length === 0) {
    list.innerHTML = '<li class="muted">Keine Regeln vorhanden.</li>';
    return;
  }
  list.innerHTML = rules.map((rule) => `
    <li class="notification-rule-item">
      <div class="notification-rule-name" title="${escapeHtml(rule.name || '')}">
        <strong>${rule.name}</strong>
      </div>
      <div class="notification-rule-meta">
        <div class="notification-rule-meta-row"><span class="notification-rule-meta-label">Priorität</span><span class="notification-rule-meta-value">${escapeHtml(rule.severity || 'info')}</span></div>
        <div class="notification-rule-meta-row"><span class="notification-rule-meta-label">Ereignisse</span><span class="notification-rule-meta-value">${(rule.event_types || []).map((eventType) => getEventLabel(eventType)).join(', ') || '-'}</span></div>
        <div class="notification-rule-meta-row"><span class="notification-rule-meta-label">Kanäle</span><span class="notification-rule-meta-value">${(rule.channels || []).map((channelType) => getChannelLabel(channelType)).join(', ') || '-'}</span></div>
        <div class="notification-rule-meta-row"><span class="notification-rule-meta-label">Cooldown</span><span class="notification-rule-meta-value">${Number(rule.cooldown_seconds || 0)}s</span></div>
      </div>
      <div class="notification-rule-item-actions">
        <button class="ghost-button notification-action-button" type="button" onclick="openNotificationRuleModal('${rule.id}')">Regel ändern</button>
        <button class="danger-button notification-action-button" type="button" onclick="deleteNotificationRule('${rule.id}')">Löschen</button>
      </div>
    </li>
  `).join('');
}

function renderNotificationHistory(history) {
  const list = document.getElementById('notification-history');
  if (!Array.isArray(history) || history.length === 0) {
    list.innerHTML = '<li class="muted">Keine Einträge.</li>';
    return;
  }
  list.innerHTML = history.slice(0, 30).map((entry) => `
    <li>
      <strong>${entry.title}</strong>
      <div>${entry.message}</div>
      <small class="muted">${getEventLabel(entry.event_type)} · ${entry.created_at} · ${entry.delivered ? '✅' : '❌'}</small>
      <div class="muted">Kanäle: ${(entry.channels || []).map((channelType) => getChannelLabel(channelType)).join(', ') || '-'}</div>
    </li>
  `).join('');
}

async function saveNotificationSettings() {
  const status = getNotificationStatusElement();
  status.textContent = 'Die globale Benachrichtigungs-Aktivierung wurde in die Home Assistant Integrations-Optionen verschoben.';
}

async function toggleNotificationDevice(deviceId, isActive) {
  const status = getNotificationStatusElement();
  try {
    const res = await fetch(buildApiUrl(`/api/dashboard/notifications/devices/${encodeURIComponent(deviceId)}`), {
      method: 'PATCH',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ active: isActive, user_id: getSelectedNotificationUserId() }),
    });
    const payload = await parseJsonSafe(res);
    if (!res.ok) throw new Error(getErrorMessage(payload, 'Gerät konnte nicht aktualisiert werden.'));
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
  notificationEditingRuleId = ruleId;

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
  notificationEditingRuleId = null;
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

  const isEditing = Boolean(notificationEditingRuleId);
  const endpoint = isEditing
    ? `/api/dashboard/notifications/rules/${encodeURIComponent(notificationEditingRuleId)}`
    : '/api/dashboard/notifications/rules';
  const method = isEditing ? 'PATCH' : 'POST';

  try {
    const res = await fetch(buildApiUrl(endpoint), {
      method,
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const responsePayload = await parseJsonSafe(res);
    if (!res.ok) throw new Error(getErrorMessage(responsePayload, isEditing ? 'Regel konnte nicht gespeichert werden.' : 'Regel konnte nicht angelegt werden.'));
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
    const res = await fetch(buildApiUrl(`/api/dashboard/notifications/rules/${encodeURIComponent(ruleId)}`), {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    const payload = await parseJsonSafe(res);
    if (!res.ok) throw new Error(getErrorMessage(payload, 'Regel konnte nicht gelöscht werden.'));
    status.textContent = 'Regel gelöscht.';
    await loadNotificationOverview();
  } catch (error) {
    status.textContent = `Fehler: ${error.message}`;
  }
}

async function testNotificationAll() {
  const status = getNotificationStatusElement();
  status.textContent = 'Sende Test an alle Geräte…';
  const res = await fetch(buildApiUrl('/api/dashboard/notifications/tests/all'), { method: 'POST', headers: getAuthHeaders() });
  const payload = await parseJsonSafe(res);
  if (!res.ok) {
    status.textContent = `Fehler: ${getErrorMessage(payload, 'Test fehlgeschlagen.')}`;
    return;
  }
  status.textContent = `Test versendet (${payload.sent_to || 0} Geräte).`;
  await loadNotificationOverview();
}

async function testNotificationPersistent() {
  const status = getNotificationStatusElement();
  status.textContent = 'Sende Persistent-Test…';
  const res = await fetch(buildApiUrl('/api/dashboard/notifications/tests/persistent'), { method: 'POST', headers: getAuthHeaders() });
  const payload = await parseJsonSafe(res);
  if (!res.ok) {
    status.textContent = `Fehler: ${getErrorMessage(payload, 'Test fehlgeschlagen.')}`;
    return;
  }
  status.textContent = 'Persistent-Test versendet.';
  await loadNotificationOverview();
}

function applyTheme(theme) {
  const root = document.documentElement;
  const toggle = document.getElementById('theme-toggle');

  if (theme === 'dark') {
    root.setAttribute('data-theme', 'dark');
    toggle.textContent = '☀️';
    toggle.setAttribute('aria-label', 'Zu Lightmode wechseln');
    toggle.setAttribute('title', 'Zu Lightmode wechseln');
    return;
  }

  root.removeAttribute('data-theme');
  toggle.textContent = '☾';
  toggle.setAttribute('aria-label', 'Zu Darkmode wechseln');
  toggle.setAttribute('title', 'Zu Darkmode wechseln');
}

function toggleTheme() {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const nextTheme = isDark ? 'light' : 'dark';
  localStorage.setItem(themeStorageKey, nextTheme);
  applyTheme(nextTheme);
}

function ensureApiKey() {
  return apiKey;
}

function getAuthHeaders() {
  const key = ensureApiKey();
  if (!key) return {};
  return { 'Authorization': `Bearer ${key}` };
}

async function parseJsonSafe(response) {
  try {
    return await response.json();
  } catch (_) {
    return {};
  }
}


function getErrorMessage(payload, fallbackMessage) {
  if (payload && payload.error && payload.error.message) return payload.error.message;
  if (payload && payload.detail) return payload.detail;
  return fallbackMessage;
}

function getShoppingStatusElement() {
  return document.getElementById('status-shopping');
}

function getRecipeStatusElement() {
  return document.getElementById('status-recipes');
}

function buildApiUrl(path) {
  const normalizedPath = '/' + String(path || '').replace(/^\/+/, '');
  if (apiBasePath) {
    return `${apiBasePath}${normalizedPath}`;
  }
  if (ingressPrefix) {
    return `${ingressPrefix}${normalizedPath}`;
  }
  return normalizedPath.replace(/^\//, '');
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
    const absoluteProxyUrl = new URL(buildApiUrl(normalized), window.location.origin);
    absoluteProxyUrl.searchParams.set('size', normalizedSize);
    return absoluteProxyUrl.toString();
  }

  if (normalized.startsWith('/api/')) {
    return buildApiUrl(normalized);
  }
  return normalized;
}


function updateClearButtonVisibility() {
  const clearButton = document.getElementById('clear-name');
  const nameInput = document.getElementById('name');
  clearButton.classList.toggle('visible', Boolean(nameInput.value));
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

function formatBadgeValue(value, fallback) {
  const text = String(value || '').trim();
  return text || fallback;
}

function formatStockCount(value) {
  const textValue = String(value ?? '').trim();
  if (!textValue) return '0';

  const normalized = textValue.replace(',', '.');
  const parsed = Number(normalized);
  if (!Number.isFinite(parsed) || parsed < 0) return textValue;

  if (Number.isInteger(parsed)) return String(parsed);

  return parsed.toLocaleString('de-DE', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
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

function parseAmountPrefixedSearch(rawValue) {
  const value = String(rawValue || '').trim();
  const match = value.match(/^(\d+(?:[.,]\d+)?)\s+(.+)$/);
  if (!match) {
    return { productName: value, amountFromName: null };
  }

  const parsedAmount = Number(match[1].replace(',', '.'));
  if (!Number.isFinite(parsedAmount) || parsedAmount <= 0) {
    return { productName: value, amountFromName: null };
  }

  return {
    productName: match[2].trim(),
    amountFromName: parsedAmount,
  };
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
    <li class="shopping-item" data-shopping-item="${encodeURIComponent(JSON.stringify(item))}">
      <div class="shopping-item-action shopping-item-action-left" aria-hidden="true">
        <span class="swipe-chip swipe-chip-buy">🛒 Kaufen</span>
      </div>
      <div class="shopping-item-action shopping-item-action-right" aria-hidden="true">
        <span class="swipe-chip swipe-chip-delete">🗑 Löschen</span>
      </div>
      <div class="shopping-item-content">
        <img src="${toImageSource(item.picture_url)}" alt="${item.product_name}" loading="lazy" />
        <div class="shopping-item-meta">
          <div><strong>${item.product_name}</strong></div>
          <div class="muted">${item.note || 'Keine Notiz'}</div>
          <div class="shopping-item-stock-tag"><span class="badge">Bestand: ${formatStockCount(item.in_stock)}</span></div>
        </div>
        <div class="shopping-item-badges">
          <button type="button" class="badge amount-increment-button" data-shopping-list-id="${item.id}">Menge: ${formatBadgeValue(item.amount, '-')}</button>
          <button type="button" class="badge mhd-picker-button" data-mhd-shopping-list-id="${item.id}" data-mhd-product-name="${encodeURIComponent(item.product_name || '')}" data-mhd-current-date="${item.best_before_date || ''}">${item.best_before_date ? item.best_before_date : 'MHD wählen'}</button>
        </div>
      </div>
    </li>
  `).join('');

  bindShoppingSwipeInteractions();
}

async function loadShoppingList() {
  return withBusyState(async () => {
  const key = ensureApiKey();
  const status = getShoppingStatusElement();
  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return;
  }

  status.textContent = 'Lade Einkaufsliste...';
  try {
    const res = await fetch(buildApiUrl('/api/dashboard/shopping-list'), {
      headers: { 'Authorization': `Bearer ${key}` },
    });
    const payload = await parseJsonSafe(res);

    if (!res.ok) {
      status.textContent = getErrorMessage(payload, 'Einkaufsliste konnte nicht geladen werden.');
      return;
    }

    renderShoppingList(payload);
    status.textContent = `Einkaufsliste geladen (${payload.length} Einträge).`;
  } catch (_) {
    status.textContent = 'Einkaufsliste konnte nicht geladen werden (Netzwerk-/Ingress-Fehler).';
  }

  });
}

function renderVariants(items) {
  const list = document.getElementById('variant-list');
  const section = document.getElementById('variant-section');
  if (!items.length) {
    list.innerHTML = '';
    section.classList.add('hidden');
    return;
  }

  section.classList.remove('hidden');

  list.innerHTML = items.map((item) => {
    const productId = item.id ?? '';
    const source = item.source || 'grocy';
    const sourceLabel = source === 'ai' ? 'KI-Vorschlag' : (source === 'input' ? 'Neu anlegen' : 'Grocy');
    return `
    <div class="variant-card">
      <button type="button" class="variant-select" data-product-id="${productId}" data-product-name="${encodeURIComponent(item.name)}" data-product-source="${source}">
        <img src="${toImageSource(item.picture_url)}" alt="${item.name}" loading="lazy" />
        <div><strong>${item.name}</strong></div>
        <small class="muted">${sourceLabel}</small>
      </button>
    </div>
  `;
  }).join('');
}

let variantsRequestToken = 0;

async function loadVariants() {
  return withBusyState(async () => {
  const key = ensureApiKey();
  const status = getShoppingStatusElement();
  const name = document.getElementById('name').value || '';

  if (!key) return;

  const query = name.trim();
  const requestToken = ++variantsRequestToken;
  if (!query) {
    document.getElementById('variant-list').innerHTML = '';
    document.getElementById('variant-section').classList.add('hidden');
    return;
  }

  try {
    const res = await fetch(buildApiUrl(`/api/dashboard/search-variants?q=${encodeURIComponent(query)}&include_ai=false`), {
      headers: { 'Authorization': `Bearer ${key}` },
    });
    const payload = await parseJsonSafe(res);

    if (!res.ok) {
      status.textContent = getErrorMessage(payload, 'Varianten konnten nicht geladen werden.');
      return;
    }

    if (requestToken !== variantsRequestToken) return;
    renderVariants(payload);

    const aiRes = await fetch(buildApiUrl(`/api/dashboard/search-variants?q=${encodeURIComponent(query)}&include_ai=true`), {
      headers: { 'Authorization': `Bearer ${key}` },
    });
    const aiPayload = await parseJsonSafe(aiRes);

    if (!aiRes.ok) {
      status.textContent = getErrorMessage(aiPayload, 'KI-Varianten konnten nicht geladen werden.');
      return;
    }

    if (requestToken !== variantsRequestToken) return;
    renderVariants(aiPayload);
  } catch (_) {
    status.textContent = 'Varianten konnten nicht geladen werden (Netzwerk-/Ingress-Fehler).';
  }

  });
}

async function confirmVariant(productId, productName) {
  return withBusyState(async () => {
  const key = ensureApiKey();
  const status = getShoppingStatusElement();

  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return;
  }

  status.textContent = `Füge ${productName} zur Einkaufsliste hinzu...`;
  const { amountFromName } = parseAmountPrefixedSearch(document.getElementById('name').value || '');
  const amount = amountFromName ?? getShoppingAmount();
  const bestBeforeDate = getShoppingBestBeforeDate();

  try {
    const res = await fetch(buildApiUrl('/api/dashboard/add-existing-product'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
      body: JSON.stringify({
        product_id: productId,
        product_name: productName,
        amount,
        best_before_date: bestBeforeDate,
      }),
    });
    const payload = await parseJsonSafe(res);
    status.textContent = payload.message || getErrorMessage(payload, 'Unbekannte Antwort');

    if (res.ok) {
      const variants = payload.variants || [];
      if (payload.action === 'variant_selection_required' && variants.length) {
        renderVariants(variants);
        return;
      }

      document.getElementById('variant-list').innerHTML = '';
      document.getElementById('variant-section').classList.add('hidden');
      await loadShoppingList();
    }
  } catch (_) {
    status.textContent = 'Produkt konnte nicht hinzugefügt werden (Netzwerk-/Ingress-Fehler).';
  }

  });
}

async function incrementShoppingItemAmount(shoppingListId) {
  const status = getShoppingStatusElement();

  return withBusyState(async () => {
    const res = await fetch(buildApiUrl(`/api/dashboard/shopping-list/item/${shoppingListId}/amount/increment`), {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    const payload = await parseJsonSafe(res);

    if (!res.ok) {
      throw new Error(getErrorMessage(payload, 'Menge konnte nicht erhöht werden.'));
    }

    status.textContent = payload.message || `Menge für Eintrag ${shoppingListId} erhöht.`;
    await loadShoppingList();
  });
}

async function removeShoppingItem(shoppingListId) {
  const key = ensureApiKey();
  const status = getShoppingStatusElement();
  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return;
  }

  const res = await fetch(buildApiUrl(`/api/dashboard/shopping-list/item/${shoppingListId}`), {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${key}` },
  });
  const payload = await parseJsonSafe(res);
  if (!res.ok) {
    status.textContent = getErrorMessage(payload, 'Eintrag konnte nicht gelöscht werden.');
    return;
  }
  status.textContent = `Eintrag ${shoppingListId} gelöscht.`;
  await loadShoppingList();
}

async function purchaseShoppingItem(shoppingListId) {
  const key = ensureApiKey();
  const status = getShoppingStatusElement();
  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return;
  }

  const res = await fetch(buildApiUrl(`/api/dashboard/shopping-list/item/${shoppingListId}/complete`), {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${key}` },
  });
  const payload = await parseJsonSafe(res);
  if (!res.ok) {
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
        <li><span>Standardmenge</span><strong>${formatValue(item.default_amount)}</strong></li>
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
        <li><span>Notiz</span><strong>${formatValue(item.note)}</strong></li>
      </ul>
    </section>
  `;
  openShoppingAmountEditor(item.amount || '');
  openShoppingNoteEditor(item.id, item.note || '');
  modal.classList.remove('hidden');
  syncModalScrollLock();
}


let activeShoppingNoteItemId = null;
let activeShoppingNoteValue = '';
let activeShoppingAmountValue = '';

function openShoppingAmountEditor(currentAmount = '') {
  activeShoppingAmountValue = String(currentAmount || '').trim();
  const input = document.getElementById('shopping-item-amount-input');
  if (input) input.value = activeShoppingAmountValue || '';
}

function openShoppingNoteEditor(shoppingListId, currentNote = '') {
  activeShoppingNoteItemId = shoppingListId;
  activeShoppingNoteValue = String(currentNote || '').trim();
  const input = document.getElementById('shopping-item-note-input');
  if (input) input.value = currentNote || '';
}

async function saveShoppingNote(shoppingListId, note) {
  const key = ensureApiKey();
  const status = getShoppingStatusElement();

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
    const res = await fetch(buildApiUrl(`/api/dashboard/shopping-list/item/${shoppingListId}/note`), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
      body: JSON.stringify({ note }),
    });
    const payload = await parseJsonSafe(res);

    if (!res.ok) {
      status.textContent = getErrorMessage(payload, 'Notiz konnte nicht gespeichert werden.');
      return false;
    }

    status.textContent = payload.message || 'Notiz gespeichert.';
    activeShoppingNoteValue = note;
    return true;
  } catch (_) {
    status.textContent = 'Notiz konnte nicht gespeichert werden (Netzwerk-/Ingress-Fehler).';
    return false;
  }
}


async function saveShoppingAmount(shoppingListId, amount) {
  const key = ensureApiKey();
  const status = getShoppingStatusElement();

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
    const res = await fetch(buildApiUrl(`/api/dashboard/shopping-list/item/${shoppingListId}/amount`), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
      body: JSON.stringify({ amount: parsedAmount }),
    });
    const payload = await parseJsonSafe(res);

    if (!res.ok) {
      status.textContent = getErrorMessage(payload, 'Menge konnte nicht gespeichert werden.');
      return false;
    }

    const amountValue = String(payload.amount ?? parsedAmount);
    activeShoppingAmountValue = amountValue;
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
  const saved = await saveShoppingAmount(activeShoppingNoteItemId, amount);
  if (saved) {
    await loadShoppingList();
  }
}

let activeMhdShoppingListId = null;

function openMhdPicker(shoppingListId, productName, currentDate = '') {
  const modal = document.getElementById('mhd-modal');
  const title = document.getElementById('mhd-modal-title');
  const input = document.getElementById('mhd-date-input');

  activeMhdShoppingListId = shoppingListId;
  title.textContent = `MHD auswählen: ${productName || 'Produkt'}`;
  input.value = currentDate || '';
  modal.classList.remove('hidden');
}

function closeMhdPicker() {
  activeMhdShoppingListId = null;
  document.getElementById('mhd-modal').classList.add('hidden');
}

async function saveMhdPickerDate() {
  const key = ensureApiKey();
  const status = getShoppingStatusElement();
  const input = document.getElementById('mhd-date-input');
  const bestBeforeDate = String(input?.value || '').trim();

  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return;
  }
  if (!activeMhdShoppingListId) {
    status.textContent = 'Einkaufslisten-Eintrag fehlt.';
    return;
  }
  if (!bestBeforeDate) {
    status.textContent = 'Bitte ein MHD auswählen.';
    return;
  }

  status.textContent = 'Speichere MHD...';
  try {
    const res = await fetch(buildApiUrl(`/api/dashboard/shopping-list/item/${activeMhdShoppingListId}/best-before`), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
      body: JSON.stringify({ best_before_date: bestBeforeDate }),
    });
    const payload = await parseJsonSafe(res);

    if (!res.ok) {
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

async function closeShoppingItemDetails() {
  const modal = document.getElementById('shopping-item-modal');
  const input = document.getElementById('shopping-item-note-input');
  const note = String(input?.value || '').trim();

  if (activeShoppingNoteItemId && note !== activeShoppingNoteValue) {
    const saved = await saveShoppingNote(activeShoppingNoteItemId, note);
    if (saved) {
      await loadShoppingList();
    }
  }

  activeShoppingNoteItemId = null;
  activeShoppingNoteValue = '';
  activeShoppingAmountValue = '';
  modal.classList.add('hidden');
  syncModalScrollLock();
}

function bindShoppingSwipeInteractions() {
  const items = document.querySelectorAll('#shopping-list .shopping-item');
  const commitDistance = 75;
  const maxDistance = 132;
  const interactiveElementSelector = '.amount-increment-button, .mhd-picker-button';

  const resetSwipeState = (item) => {
    item.classList.remove('dragging', 'swipe-commit-left', 'swipe-commit-right');
    item.style.setProperty('--swipe-offset', '0px');
    item.style.setProperty('--swipe-progress-left', '0');
    item.style.setProperty('--swipe-progress-right', '0');
    item.style.setProperty('--swipe-glow', 'transparent');
  };

  items.forEach((item) => {
    let startX = 0;
    let deltaX = 0;
    let pointerId = null;
    let isDragging = false;

    resetSwipeState(item);

    item.addEventListener('pointerdown', (event) => {
      if (event.target.closest(interactiveElementSelector)) {
        return;
      }

      pointerId = event.pointerId;
      startX = event.clientX;
      deltaX = 0;
      isDragging = true;
      item.classList.remove('swipe-commit-left', 'swipe-commit-right');
      item.classList.add('dragging');
      item.setPointerCapture(pointerId);
    });

    item.addEventListener('pointermove', (event) => {
      if (!isDragging || event.pointerId !== pointerId) {
        return;
      }

      const distance = event.clientX - startX;
      const dragScale = 0.8;
      deltaX = Math.max(-maxDistance, Math.min(maxDistance, distance * dragScale));

      const rightProgress = Math.min(Math.max(deltaX / commitDistance, 0), 1);
      const leftProgress = Math.min(Math.max((-deltaX) / commitDistance, 0), 1);
      const glow = deltaX >= 0 ? 'rgba(22, 163, 74, 0.7)' : 'rgba(239, 68, 68, 0.7)';

      item.style.setProperty('--swipe-offset', `${deltaX}px`);
      item.style.setProperty('--swipe-progress-left', leftProgress.toFixed(3));
      item.style.setProperty('--swipe-progress-right', rightProgress.toFixed(3));
      item.style.setProperty('--swipe-glow', glow);
    });

    item.addEventListener('pointercancel', () => {
      isDragging = false;
      resetSwipeState(item);
    });

    item.addEventListener('pointerup', async (event) => {
      if (!isDragging || event.pointerId !== pointerId) {
        return;
      }

      isDragging = false;
      if (item.hasPointerCapture(pointerId)) {
        item.releasePointerCapture(pointerId);
      }
      pointerId = null;
      item.classList.remove('dragging');

      const payloadText = decodeURIComponent(item.dataset.shoppingItem || '');
      const payload = payloadText ? JSON.parse(payloadText) : {};
      const shoppingListId = payload.id;

      if (deltaX <= -commitDistance) {
        item.classList.add('swipe-commit-left');
        await purchaseShoppingItem(shoppingListId);
        return;
      }

      if (deltaX >= commitDistance) {
        item.classList.add('swipe-commit-right');
        await removeShoppingItem(shoppingListId);
        return;
      }

      if (Math.abs(deltaX) < 14) {
        showShoppingItemDetails(payload);
      }

      resetSwipeState(item);
    });
  });
}

async function completeShoppingList() {
  return withBusyState(async () => {
  const key = ensureApiKey();
  const status = getShoppingStatusElement();
  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return;
  }

  status.textContent = 'Markiere Einkaufsliste als eingekauft...';
  try {
    const res = await fetch(buildApiUrl('/api/dashboard/shopping-list/complete'), {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${key}` },
    });
    const payload = await parseJsonSafe(res);

    if (!res.ok) {
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
  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return;
  }

  status.textContent = 'Leere Einkaufsliste...';
  try {
    const res = await fetch(buildApiUrl('/api/dashboard/shopping-list/clear'), {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${key}` },
    });
    const payload = await parseJsonSafe(res);

    if (!res.ok) {
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

  const forceCreate = options.forceCreate === true;
  status.textContent = forceCreate ? 'Lege Produkt direkt an...' : 'Prüfe Produkt...';
  try {
    const res = await fetch(buildApiUrl('/api/dashboard/search'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
      body: JSON.stringify({
        name: productName,
        amount,
        best_before_date: bestBeforeDate,
        force_create: forceCreate,
      })
    });

    const payload = await parseJsonSafe(res);
    status.textContent = payload.message || getErrorMessage(payload, 'Unbekannte Antwort');

    if (res.ok) {
      const variants = payload.variants || [];
      if (payload.action === 'variant_selection_required' && variants.length) {
        renderVariants(variants);
        return;
      }

      document.getElementById('variant-list').innerHTML = '';
      document.getElementById('variant-section').classList.add('hidden');
      await loadShoppingList();
    }
  } catch (_) {
    status.textContent = 'Produkt konnte nicht geprüft werden (Netzwerk-/Ingress-Fehler).';
  }

  });
}

let variantsDebounce;
document.getElementById('variant-list').addEventListener('click', (event) => {
  const target = event.target.closest('.variant-select');
  if (!target) return;

  const productIdRaw = target.dataset.productId;
  const productId = Number(productIdRaw);
  const productName = decodeURIComponent(target.dataset.productName || '');
  const source = target.dataset.productSource || 'grocy';

  if (source === 'input') {
    searchSuggestedProduct(productName, { forceCreate: true });
    return;
  }

  if (!Number.isFinite(productId) || !productIdRaw) {
    searchSuggestedProduct(productName);
    return;
  }

  if (source === 'ai') {
    searchSuggestedProduct(productName);
    return;
  }

  confirmVariant(productId, productName);
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

document.getElementById('name').addEventListener('input', () => {
  updateClearButtonVisibility();
  clearTimeout(variantsDebounce);
  variantsDebounce = setTimeout(() => {
    loadVariants();
  }, 250);
});


const savedTheme = localStorage.getItem(themeStorageKey) || 'light';
applyTheme(savedTheme);
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

switchTab('shopping');
loadShoppingList();
preloadRecipeSuggestionsOnStartup();


async function searchSuggestedProduct(productName, options = {}) {
  const nameInput = document.getElementById('name');
  nameInput.value = productName;
  updateClearButtonVisibility();
  await searchProduct(options);
}

function getSelectedLocationIds() {
  return Array.from(document.querySelectorAll('#location-filters input[type="checkbox"]:checked'))
    .map((checkbox) => Number(checkbox.value));
}

function getSelectedProductIds() {
  return Array.from(document.querySelectorAll('#stock-products input[type="checkbox"]:checked'))
    .map((checkbox) => Number(checkbox.value));
}

function renderLocations(items) {
  const container = document.getElementById('location-filters');
  if (!container) return;

  const selectedLocationIds = new Set(recipeState.selectedLocationIds);

  if (!items.length) {
    container.innerHTML = '<div class="muted">Keine Lagerstandorte gefunden.</div>';
    return;
  }

  container.innerHTML = `
    <details class="location-dropdown">
      <summary>Lagerstandorte auswählen (${items.length})</summary>
      <div class="location-options">
        ${items.map((item) => `
          <label class="stock-item">
            <input type="checkbox" value="${item.id}" ${selectedLocationIds.size === 0 || selectedLocationIds.has(item.id) ? 'checked' : ''} />
            <span><strong>${item.name}</strong></span>
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

  container.innerHTML = `
    <details class="location-dropdown">
      <summary>Produkte auswählen (${normalizedItems.length})</summary>
      <div class="stock-options">
        ${normalizedItems.length ? normalizedItems.map((item) => `
          <label class="stock-item">
            <input type="checkbox" value="${item.id}" ${selectedProductIds.size === 0 || selectedProductIds.has(item.id) ? 'checked' : ''} />
            <span class="stock-item-name"><strong>${item.name}</strong></span>
            <span class="stock-item-attributes">
              <button type="button" class="badge amount-increment-button" data-shopping-list-id="${item.id}">Menge: ${formatBadgeValue(item.amount, '-')}</button>
              <span class="badge">MHD: ${formatBadgeValue(item.best_before_date, '-')}</span>
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
    const res = await fetch(buildApiUrl('/api/dashboard/locations'), {
      headers: { 'Authorization': `Bearer ${key}` },
    });
    const payload = await parseJsonSafe(res);

    if (!res.ok) {
      getRecipeStatusElement().textContent = getErrorMessage(payload, 'Standorte konnten nicht geladen werden.');
      return;
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
    const query = selectedLocationIds.length ? `?location_ids=${selectedLocationIds.join(',')}` : '';
    const res = await fetch(buildApiUrl(`/api/dashboard/stock-products${query}`), {
      headers: { 'Authorization': `Bearer ${key}` },
    });
    const payload = await parseJsonSafe(res);

    if (!res.ok) {
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

function normalizeStorageFilterValue() {
  const input = document.getElementById('storage-filter-input');
  return String(input?.value || '').trim().toLowerCase();
}

function renderStorageProducts() {
  const list = document.getElementById('storage-products');
  if (!list) return;

  const filterValue = normalizeStorageFilterValue();
  const filteredItems = storageProductsCache.filter((item) => {
    if (!filterValue) return true;
    const searchable = `${item.name || ''} ${item.location_name || ''}`.toLowerCase();
    return searchable.includes(filterValue);
  });

  if (!filteredItems.length) {
    list.innerHTML = '<li class="muted">Keine Produkte gefunden.</li>';
    return;
  }

  list.innerHTML = filteredItems.map((item) => {
    const actionableId = getActionableStorageId(item);
    const canExecuteAction = actionableId > 0;
    const disabledAttr = canExecuteAction ? '' : ' disabled';
    const disabledTitle = canExecuteAction ? '' : ' title="Für diesen Eintrag ist keine nutzbare Produkt-/Bestand-ID verfügbar"';

    return `
    <li class="storage-item">
      <div class="storage-item-content">
        <img src="${toImageSource(item.picture_url)}" alt="${escapeHtml(item.name || 'Unbekanntes Produkt')}" loading="lazy" />
        <div class="storage-item-main">
          <strong class="storage-item-name">${escapeHtml(item.name || 'Unbekanntes Produkt')}</strong>
          <div class="muted storage-item-description">Lager: ${escapeHtml(item.location_name || '-')} · Menge: ${escapeHtml(formatBadgeValue(item.amount, '0'))} · MHD: ${escapeHtml(formatBadgeValue(item.best_before_date, '-'))}</div>
        </div>
        <div class="storage-item-actions">
          <button class="ghost-button storage-action-button storage-edit-button" type="button" onclick="openStorageEditModal(${actionableId})"${disabledAttr}${disabledTitle}>✏️ Bearbeiten</button>
          <button class="success-button storage-action-button" type="button" onclick="consumeStorageProduct(${actionableId})"${disabledAttr}${disabledTitle}>✅ Verbrauchen</button>
        </div>
      </div>
    </li>
  `;
  }).join('');
}

async function loadStorageProducts() {
  return withBusyState(async () => {
    const key = ensureApiKey();
    const status = getStorageStatusElement();
    if (!key) {
      status.textContent = 'Kein API-Key angegeben.';
      return;
    }

    status.textContent = 'Lade Lagerbestand...';
    try {
      const res = await fetch(buildApiUrl('/api/dashboard/stock-products'), { headers: { Authorization: `Bearer ${key}` } });
      const payload = await parseJsonSafe(res);
      if (!res.ok) throw new Error(getErrorMessage(payload, 'Bestand konnte nicht geladen werden.'));
      storageProductsCache = (Array.isArray(payload) ? payload : []).map(normalizeStockProduct);
      renderStorageProducts();
      const fallbackProductIds = storageProductsCache.filter((item) => Number(item.stock_id || 0) <= 0 && Number(item.id || 0) > 0).length;
      const missingAllIds = storageProductsCache.filter((item) => Number(item.stock_id || 0) <= 0 && Number(item.id || 0) <= 0).length;
      status.textContent = missingAllIds > 0
        ? `Lagerbestand geladen (${fallbackProductIds} Einträge über Produkt-ID, ${missingAllIds} ohne nutzbare ID).`
        : fallbackProductIds > 0
          ? `Lagerbestand geladen (${fallbackProductIds} Einträge über Produkt-ID).`
        : 'Lagerbestand geladen.';
    } catch (error) {
      status.textContent = `Fehler: ${error.message}`;
    }
  });
}

async function consumeStorageProduct(stockId) {
  const status = getStorageStatusElement();
  const key = ensureApiKey();
  if (!key) return;

  try {
    const res = await fetch(buildApiUrl(`/api/dashboard/stock-products/${encodeURIComponent(stockId)}/consume`), {
      method: 'POST',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount: 1 }),
    });
    const payload = await parseJsonSafe(res);
    if (!res.ok) throw new Error(getErrorMessage(payload, 'Produkt konnte nicht verbraucht werden.'));
    status.textContent = 'Produkt wurde verbraucht.';
    await loadStorageProducts();
  } catch (error) {
    status.textContent = `Fehler: ${error.message}`;
  }
}

function openStorageEditModal(stockId) {
  const normalizedStockId = Number(stockId);
  const stockItem = storageProductsCache.find((item) => {
    if (Number(item?.stock_id) === normalizedStockId) return true;
    return Number(item?.id) === normalizedStockId;
  });
  if (!stockItem) return;
  storageEditingItem = stockItem;
  storageEditingTargetId = normalizedStockId;
  document.getElementById('storage-edit-modal-title').textContent = `Bestand ändern: ${stockItem.name}`;
  document.getElementById('storage-edit-name').textContent = stockItem.name || '-';
  document.getElementById('storage-edit-product-id').textContent = String(stockItem.id || '-');
  document.getElementById('storage-edit-stock-id').textContent = String(stockItem.stock_id || '-');
  document.getElementById('storage-edit-location').textContent = stockItem.location_name || '-';
  document.getElementById('storage-edit-current-amount').textContent = formatBadgeValue(stockItem.amount, '0');
  document.getElementById('storage-edit-current-best-before').textContent = formatBadgeValue(stockItem.best_before_date, '-');
  document.getElementById('storage-edit-amount').value = String(stockItem.amount || '0').replace(',', '.');
  document.getElementById('storage-edit-best-before').value = stockItem.best_before_date || '';
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
}

function closeStorageEditModal() {
  storageEditingItem = null;
  storageEditingTargetId = null;
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
  document.getElementById('storage-edit-modal').classList.add('hidden');
  syncModalScrollLock();
}

async function saveStorageEditModal() {
  if (!storageEditingItem || !Number.isFinite(storageEditingTargetId) || storageEditingTargetId <= 0) return;
  const status = getStorageStatusElement();
  const amount = Number(document.getElementById('storage-edit-amount').value);
  const bestBeforeDate = document.getElementById('storage-edit-best-before').value || '';
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
    const res = await fetch(buildApiUrl(`/api/dashboard/stock-products/${encodeURIComponent(storageEditingTargetId)}`), {
      method: 'PUT',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        amount,
        best_before_date: bestBeforeDate,
        calories,
        carbs,
        fat,
        protein,
        sugar,
      }),
    });
    const payload = await parseJsonSafe(res);
    if (!res.ok) throw new Error(getErrorMessage(payload, 'Bestand konnte nicht aktualisiert werden.'));
    closeStorageEditModal();
    status.textContent = 'Bestand wurde aktualisiert.';
    await loadStorageProducts();
  } catch (error) {
    status.textContent = `Fehler: ${error.message}`;
  }
}


async function deleteStorageEditPicture() {
  if (!storageEditingItem) return;
  const productId = Number(storageEditingItem.id || 0);
  if (!Number.isFinite(productId) || productId <= 0) return;

  const status = getStorageStatusElement();
  const productName = storageEditingItem.name || 'dieses Produkt';
  const confirmed = window.confirm(`Soll das Produktbild von ${productName} wirklich gelöscht werden?`);
  if (!confirmed) return;

  try {
    const res = await fetch(buildApiUrl(`/api/dashboard/products/${encodeURIComponent(productId)}/picture`), {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    const payload = await parseJsonSafe(res);
    if (!res.ok) throw new Error(getErrorMessage(payload, 'Produktbild konnte nicht gelöscht werden.'));
    status.textContent = payload?.message || 'Produktbild wurde gelöscht.';
    await loadStorageProducts();
    const refreshedItem = storageProductsCache.find((item) => Number(item.id || 0) === productId);
    if (refreshedItem) {
      openStorageEditModal(getActionableStorageId(refreshedItem));
    }
  } catch (error) {
    status.textContent = `Fehler: ${error.message}`;
  }
}

async function deleteStorageEditItem() {
  if (!storageEditingItem || !Number.isFinite(storageEditingTargetId) || storageEditingTargetId <= 0) return;
  const status = getStorageStatusElement();
  const productName = storageEditingItem.name || 'dieses Produkt';
  const confirmed = window.confirm(`Soll ${productName} wirklich aus dem Bestand gelöscht werden?`);
  if (!confirmed) return;

  try {
    const res = await fetch(buildApiUrl(`/api/dashboard/stock-products/${encodeURIComponent(storageEditingTargetId)}`), {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    const payload = await parseJsonSafe(res);
    if (!res.ok) throw new Error(getErrorMessage(payload, 'Bestandseintrag konnte nicht gelöscht werden.'));
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
    const res = await fetch(buildApiUrl('/api/dashboard/recipe-suggestions'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
      body: JSON.stringify({
        product_ids: selectedIds,
        location_ids: selectedLocationIds,
        soon_expiring_only: soonExpiringOnly,
        expiring_within_days: expiringWithinDays,
      }),
    });
    const payload = await parseJsonSafe(res);

    if (!res.ok) {
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

  activeRecipeItem = item;
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
  activeRecipeItem = null;
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
  if (!key || !activeRecipeItem || !Number.isInteger(activeRecipeItem.recipe_id)) return;

  try {
    const res = await fetch(buildApiUrl(`/api/dashboard/recipe/${activeRecipeItem.recipe_id}/add-missing`), {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${key}` },
    });
    const payload = await parseJsonSafe(res);
    if (!res.ok) {
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

function getScannerCapabilitiesLogElement() {
  return document.getElementById('scanner-capabilities-log');
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
  if (scannerRotationDegrees === 90) videoElement.classList.add('rotated-90');
  if (scannerRotationDegrees === 180) videoElement.classList.add('rotated-180');
  if (scannerRotationDegrees === 270) videoElement.classList.add('rotated-270');
}

function parseScannerRotationDegrees(value) {
  const rotation = Number(value);
  if (![0, 90, 180, 270].includes(rotation)) return 0;
  return rotation;
}

function onScannerRotationChange() {
  const select = getScannerRotationSelectElement();
  scannerRotationDegrees = parseScannerRotationDegrees(select?.value ?? 0);
  const video = document.getElementById('scanner-video');
  applyScannerVideoRotation(video);
}

function setScannerCapabilitiesLog(capabilities, settings) {
  const log = getScannerCapabilitiesLogElement();
  if (!log) return;

  const payload = {
    selected_device_id: scannerSelectedDeviceId || null,
    capabilities: capabilities || null,
    settings: settings || null,
    support: {
      focusMode: Boolean(capabilities?.focusMode),
      focusDistance: Boolean(capabilities?.focusDistance),
      zoom: Boolean(capabilities?.zoom),
      torch: Boolean(capabilities?.torch),
    },
  };

  log.textContent = JSON.stringify(payload, null, 2);
  console.info('Scanner camera capabilities', payload);
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
    scannerKnownDevices = devices.filter((device) => device.kind === 'videoinput');

    const options = ["<option value=''>Automatisch (Rückkamera)</option>"];
    scannerKnownDevices.forEach((device, index) => {
      const label = device.label || `Kamera ${index + 1}`;
      const selected = scannerSelectedDeviceId && scannerSelectedDeviceId === device.deviceId ? ' selected' : '';
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
  scannerSelectedDeviceId = select.value || '';
  if (!scannerStream) return;

  const status = getScannerStatusElement();
  status.textContent = 'Kamerawechsel… Scanner startet neu.';
  await startBarcodeScanner();
}

function evaluateScannerLight(video, canvas) {
  if (!video?.videoWidth || !video?.videoHeight || !canvas) return;
  const now = Date.now();
  if ((now - scannerLastLightCheckAt) < scannerLightCheckIntervalMs) return;
  scannerLastLightCheckAt = now;

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

  if (!payload || !payload.found) {
    container.classList.add('hidden');
    container.innerHTML = '';
    return;
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
  `;
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

  if (scannerLlavaInFlight) return;
  scannerLlavaInFlight = true;
  scannerLlavaLastRequestAt = Date.now();

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
    try {
      res = await fetch(buildApiUrl('/api/dashboard/scanner/llava'), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${key}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ image_base64: imageBase64 }),
        signal: abortController.signal,
      });
    } finally {
      clearTimeout(timeoutHandle);
    }

    const payload = await parseJsonSafe(res);

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
      nutrition_grade: payload.source || 'LLaVA',
    });
  } catch (error) {
    if (error?.name === 'AbortError') {
      status.textContent = `LLaVA-Anfrage dauerte länger als ${getScannerLlavaTimeoutSeconds()}s und wurde beendet.`;
    } else {
      status.textContent = 'LLaVA konnte nicht abgefragt werden (Netzwerk-/Ingress-Fehler).';
    }
  } finally {
    scannerLlavaInFlight = false;
  }
}


function isScannerModalVisible() {
  const modal = document.getElementById('scanner-modal');
  return Boolean(modal && !modal.classList.contains('hidden'));
}

function scheduleLlavaFallback() {
  if (scannerLlavaTimer) {
    clearTimeout(scannerLlavaTimer);
  }
  const waitMs = getScannerLlavaDelaySeconds() * 1000;
  scannerLlavaTimer = setTimeout(() => {
    if (!isScannerModalVisible() || !scannerStream) return;
    const elapsed = Date.now() - scannerLastBarcodeAt;
    if (elapsed >= waitMs - 100) {
      const autoCooldownMs = getScannerLlavaAutoCooldownMs();
      const sinceLastLlavaMs = Date.now() - scannerLlavaLastRequestAt;
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

  if (normalized === scannerLastBarcode) {
    scannerStableCandidate = normalized;
    scannerStableCount = scannerStableDetectionThreshold;
    return '';
  }

  if (normalized === scannerStableCandidate) {
    scannerStableCount += 1;
  } else {
    scannerStableCandidate = normalized;
    scannerStableCount = 1;
  }

  if (scannerStableCount < scannerStableDetectionThreshold) {
    return '';
  }

  scannerStableCount = 0;
  scannerStableCandidate = '';
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

  scannerLastBarcode = normalized;
  scannerLastBarcodeAt = Date.now();
  status.textContent = `Barcode erkannt: ${normalized}. Lade Produktdaten...`;

  try {
    const res = await fetch(buildApiUrl(`/api/dashboard/barcode/${normalized}`), {
      headers: { 'Authorization': `Bearer ${key}` },
    });
    const payload = await parseJsonSafe(res);

    if (!res.ok) {
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

    scannerStream = await getCompatibleScannerStream();
    await refreshScannerDevices();

    await optimizeScannerTrack(scannerStream, status);
    scheduleScannerFocusRefresh(scannerStream);

    video.setAttribute('playsinline', 'true');
    video.setAttribute('autoplay', 'true');
    video.setAttribute('muted', 'true');
    video.playsInline = true;
    video.autoplay = true;
    video.muted = true;
    video.srcObject = scannerStream;
    await video.play();
    video.classList.remove('hidden');
    applyScannerVideoRotation(video);
    startButton.classList.add('hidden');
    stopButton.classList.remove('hidden');
    if (!String(status.textContent || '').startsWith('Scanner aktiv')) {
      status.textContent = 'Scanner aktiv. Kamera stellt scharf… danach Barcode im Rahmen halten.';
    }
    scannerLastBarcodeAt = Date.now();
    scannerScanStartedAt = Date.now();
    scannerLastLightCheckAt = 0;
    setScannerLightWarningVisible(false);
    const overlay = document.getElementById('scanner-frame-overlay');
    if (overlay) overlay.classList.remove('hidden');
    scheduleLlavaFallback();

    if ('BarcodeDetector' in window) {
      scannerDetector = new window.BarcodeDetector({ formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e'] });
    }

    scannerInterval = setInterval(async () => {
      if (!isScannerModalVisible()) return;
      if (!video.videoWidth || !video.videoHeight) return;

      evaluateScannerLight(video, canvas);

      if (Date.now() - scannerScanStartedAt < scannerAnalysisWarmupMs) {
        status.textContent = 'Scanner aktiv. Kamera stellt scharf…';
        return;
      }

      if (status.textContent.includes('stellt scharf')) {
        status.textContent = 'Scanner aktiv. Barcode vor die Kamera halten...';
      }

      if (scannerDetector) {
        try {
          const detectionSource = getScannerDetectionSource(video, canvas, scannerDigitalZoomFactor);
          const barcodes = await scannerDetector.detect(detectionSource);
          if (barcodes.length) {
            const value = String(barcodes[0].rawValue || '').trim();
            const stableBarcode = registerScannerCandidate(value);
            if (stableBarcode && !scannerDetectionInFlight) {
              scannerDetectionInFlight = true;
              try {
                await lookupBarcode(stableBarcode);
              } finally {
                scannerDetectionInFlight = false;
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
  const selectedDeviceConstraint = scannerSelectedDeviceId
    ? { deviceId: { exact: scannerSelectedDeviceId } }
    : { facingMode: { exact: 'environment' } };

  const fallbackFacingConstraint = scannerSelectedDeviceId
    ? { deviceId: { exact: scannerSelectedDeviceId } }
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
      video: scannerSelectedDeviceId ? { deviceId: { exact: scannerSelectedDeviceId } } : { facingMode: 'environment' },
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
  if (scannerFocusRefreshTimer) {
    clearInterval(scannerFocusRefreshTimer);
  }

  if (!stream || !['single-shot', 'continuous'].includes(scannerPreferredFocusMode)) {
    return;
  }

  const videoTrack = stream.getVideoTracks?.()[0];
  if (!videoTrack) return;

  scannerFocusRefreshTimer = setInterval(() => {
    if (!scannerStream || !isScannerModalVisible()) return;
    applyScannerFocusRefresh(videoTrack, scannerPreferredFocusMode);
  }, scannerFocusRefreshMs);
}

async function optimizeScannerTrack(stream, status) {
  const videoTrack = stream?.getVideoTracks?.()[0];
  if (!videoTrack) return;

  const capabilities = videoTrack.getCapabilities ? videoTrack.getCapabilities() : null;
  const settings = videoTrack.getSettings ? videoTrack.getSettings() : null;
  setScannerCapabilitiesLog(capabilities, settings);
  const constraints = {};

  if (capabilities?.focusMode?.includes('continuous')) {
    constraints.focusMode = 'continuous';
  } else if (capabilities?.focusMode?.includes('single-shot')) {
    constraints.focusMode = 'single-shot';
  } else if (capabilities?.focusMode?.includes('manual')) {
    constraints.focusMode = 'manual';
  }

  scannerPreferredFocusMode = constraints.focusMode || '';

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
    if (scannerPreferredFocusMode) {
      await applyScannerFocusRefresh(videoTrack, scannerPreferredFocusMode);
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
  const autoPortraitQuarterTurn = scannerRotationDegrees === 0 && sourceHeight > sourceWidth;
  const rotation = autoPortraitQuarterTurn ? 90 : scannerRotationDegrees;
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

  if (scannerInterval) {
    clearInterval(scannerInterval);
    scannerInterval = null;
  }

  if (scannerLlavaTimer) {
    clearTimeout(scannerLlavaTimer);
    scannerLlavaTimer = null;
  }
  if (scannerFocusRefreshTimer) {
    clearInterval(scannerFocusRefreshTimer);
    scannerFocusRefreshTimer = null;
  }
  scannerPreferredFocusMode = '';
  scannerLlavaInFlight = false;
  scannerLlavaLastRequestAt = 0;
  scannerDetectionInFlight = false;
  scannerStableCandidate = '';
  scannerStableCount = 0;

  if (scannerStream) {
    scannerStream.getTracks().forEach((track) => track.stop());
    scannerStream = null;
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
