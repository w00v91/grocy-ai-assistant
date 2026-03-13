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
let scannerLlavaInFlight = false;
let scannerLlavaTimer = null;
const scannerDigitalZoomFactor = 1.35;
const recipeState = {
  initialized: false,
  hasLoadedInitialSuggestions: false,
  selectedLocationIds: [],
  selectedProductIds: [],
  stockSignature: null,
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
  const allowedTabs = ['shopping', 'recipes', 'scanner'];
  activeTab = allowedTabs.includes(tabName) ? tabName : 'shopping';

  const shoppingTab = document.getElementById('tab-shopping');
  const recipesTab = document.getElementById('tab-recipes');
  const scannerTab = document.getElementById('tab-scanner');
  const shoppingButton = document.getElementById('tab-button-shopping');
  const recipesButton = document.getElementById('tab-button-recipes');
  const scannerButton = document.getElementById('tab-button-scanner');

  shoppingTab.classList.toggle('hidden', activeTab !== 'shopping');
  recipesTab.classList.toggle('hidden', activeTab !== 'recipes');
  scannerTab.classList.toggle('hidden', activeTab !== 'scanner');
  shoppingButton.classList.toggle('active', activeTab === 'shopping');
  recipesButton.classList.toggle('active', activeTab === 'recipes');
  scannerButton.classList.toggle('active', activeTab === 'scanner');

  if (activeTab === 'recipes' && !recipeState.initialized) {
    loadLocations();
  }
  if (activeTab !== 'scanner') {
    stopBarcodeScanner();
  }
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
  toggle.textContent = '🌙';
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

function toImageSource(url) {
  if (!url) return 'https://placehold.co/80x80?text=Kein+Bild';
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
    <li class="shopping-item" data-shopping-item="${encodeURIComponent(JSON.stringify(item))}">
      <div class="shopping-item-action shopping-item-action-left" aria-hidden="true">
        <span class="swipe-chip swipe-chip-buy">🛒 Kaufen</span>
      </div>
      <div class="shopping-item-action shopping-item-action-right" aria-hidden="true">
        <span class="swipe-chip swipe-chip-delete">🗑 Löschen</span>
      </div>
      <div class="shopping-item-content">
        <img src="${toImageSource(item.picture_url)}" alt="${item.product_name}" loading="lazy" />
        <div>
          <div><strong>${item.product_name}</strong></div>
          <div class="muted">${item.note || 'Keine Notiz'}</div>
        </div>
        <div class="shopping-item-badges">
          <span class="badge">Menge: ${formatBadgeValue(item.amount, '-')}</span>
          <button type="button" class="badge mhd-picker-button" data-mhd-shopping-list-id="${item.id}" data-mhd-product-name="${encodeURIComponent(item.product_name || '')}" data-mhd-current-date="${item.best_before_date || ''}">${item.best_before_date ? `MHD: ${item.best_before_date}` : 'MHD wählen'}</button>
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
    const sourceLabel = source === 'ai' ? 'KI-Vorschlag' : 'Grocy';
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

async function loadVariants() {
  return withBusyState(async () => {
  const key = ensureApiKey();
  const status = getShoppingStatusElement();
  const name = document.getElementById('name').value || '';

  if (!key) return;

  const query = name.trim();
  if (!query) {
    document.getElementById('variant-list').innerHTML = '';
    document.getElementById('variant-section').classList.add('hidden');
    return;
  }

  try {
    const res = await fetch(buildApiUrl(`/api/dashboard/search-variants?q=${encodeURIComponent(query)}`), {
      headers: { 'Authorization': `Bearer ${key}` },
    });
    const payload = await parseJsonSafe(res);

    if (!res.ok) {
      status.textContent = getErrorMessage(payload, 'Varianten konnten nicht geladen werden.');
      return;
    }

    renderVariants(payload);
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
  const amount = getShoppingAmount();
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
        <li><span>Menge Einkauf</span><strong>${formatValue(item.amount)}</strong></li>
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
  modal.classList.remove('hidden');
  syncModalScrollLock();
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

function closeShoppingItemDetails() {
  document.getElementById('shopping-item-modal').classList.add('hidden');
  syncModalScrollLock();
}

function bindShoppingSwipeInteractions() {
  const items = document.querySelectorAll('#shopping-list .shopping-item');
  const commitDistance = 86;
  const maxDistance = 132;

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
      if (event.target.closest('.mhd-picker-button')) {
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
      const resistance = Math.sign(distance) * Math.sqrt(Math.abs(distance)) * 1.85;
      deltaX = Math.max(-maxDistance, Math.min(maxDistance, resistance));

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

async function searchProduct() {
  return withBusyState(async () => {
  const name = document.getElementById('name').value;
  const status = getShoppingStatusElement();
  const key = ensureApiKey();
  const amount = getShoppingAmount();
  const bestBeforeDate = getShoppingBestBeforeDate();

  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return;
  }
  if (!name || !name.trim()) {
    status.textContent = 'Bitte Produktname eingeben.';
    return;
  }

  status.textContent = 'Prüfe Produkt...';
  try {
    const res = await fetch(buildApiUrl('/api/dashboard/search'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
      body: JSON.stringify({
        name,
        amount,
        best_before_date: bestBeforeDate,
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
switchTab('shopping');
loadShoppingList();
preloadRecipeSuggestionsOnStartup();


async function searchSuggestedProduct(productName) {
  const nameInput = document.getElementById('name');
  nameInput.value = productName;
  updateClearButtonVisibility();
  await searchProduct();
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
  const selectedProductIds = new Set(recipeState.selectedProductIds);

  container.innerHTML = `
    <details class="location-dropdown">
      <summary>Produkte auswählen (${items.length})</summary>
      <div class="stock-options">
        ${items.length ? items.map((item) => `
          <label class="stock-item">
            <input type="checkbox" value="${item.id}" ${selectedProductIds.size === 0 || selectedProductIds.has(item.id) ? 'checked' : ''} />
            <span class="stock-item-name"><strong>${item.name}</strong></span>
            <span class="stock-item-attributes">
              <span class="badge">Menge: ${formatBadgeValue(item.amount, '-')}</span>
              <span class="badge">MHD: ${formatBadgeValue(item.best_before_date, '-')}</span>
            </span>
          </label>
        `).join('') : '<div class="muted">Keine Produkte für die ausgewählten Lagerstandorte gefunden.</div>'}
      </div>
    </details>
  `;
}

function renderRecipeList(elementId, items, emptyText) {
  const list = document.getElementById(elementId);
  if (!items.length) {
    list.innerHTML = `<li>${emptyText}</li>`;
    return;
  }

  list.innerHTML = items.map((item) => `
    <li class="recipe-item" data-recipe-item="${encodeURIComponent(JSON.stringify(item))}">
      ${item.picture_url ? `<img class="recipe-thumb" src="${item.picture_url}" alt="${item.title}" loading="lazy" />` : '<div class="recipe-thumb recipe-thumb-fallback">🍽️</div>'}
      <div>
        <div><strong>${item.title}</strong></div>
        <div class="muted">${item.reason || ''}</div>
      </div>
    </li>
  `).join('');

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

    const availableProductIds = new Set(payload.map((item) => item.id));
    recipeState.selectedProductIds = recipeState.selectedProductIds.filter((id) => availableProductIds.has(id));

    const nextStockSignature = buildStockSignature(payload);
    const hasStockChanged = recipeState.stockSignature !== null
      && recipeState.stockSignature !== nextStockSignature;

    recipeState.stockSignature = nextStockSignature;

    renderStockProducts(payload);

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

  addButton.disabled = !(item.source === 'grocy' && Number.isInteger(item.recipe_id));
  modal.classList.remove('hidden');
  syncModalScrollLock();
}

function closeRecipeDetails() {
  const modal = document.getElementById('recipe-modal');
  modal.classList.add('hidden');
  activeRecipeItem = null;
  syncModalScrollLock();
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

    const res = await fetch(buildApiUrl('/api/dashboard/scanner/llava'), {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${key}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ image_base64: imageBase64 }),
    });
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
  } catch (_) {
    status.textContent = 'LLaVA konnte nicht abgefragt werden (Netzwerk-/Ingress-Fehler).';
  } finally {
    scannerLlavaInFlight = false;
  }
}

function scheduleLlavaFallback() {
  if (scannerLlavaTimer) {
    clearTimeout(scannerLlavaTimer);
  }
  const waitMs = getScannerLlavaDelaySeconds() * 1000;
  scannerLlavaTimer = setTimeout(() => {
    if (activeTab !== 'scanner' || !scannerStream) return;
    const elapsed = Date.now() - scannerLastBarcodeAt;
    if (elapsed >= waitMs - 100) {
      queryLlavaWithCurrentFrame('timeout');
    }
    scheduleLlavaFallback();
  }, waitMs);
}

async function triggerLlavaScan() {
  await queryLlavaWithCurrentFrame('manual');
}

async function lookupBarcode(barcode) {
  const key = ensureApiKey();
  const status = getScannerStatusElement();
  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return;
  }

  const normalized = String(barcode || '').replace(/\D/g, '');
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

async function startBarcodeScanner() {
  const status = getScannerStatusElement();
  const video = document.getElementById('scanner-video');
  const canvas = document.getElementById('scanner-canvas');
  const startButton = document.getElementById('start-scan-button');
  const stopButton = document.getElementById('stop-scan-button');
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    status.textContent = 'Kamera wird von diesem Browser nicht unterstützt.';
    return;
  }

  try {
    stopBarcodeScanner();

    scannerStream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: 'environment' },
        width: { ideal: 1920 },
        height: { ideal: 1080 },
      },
      audio: false,
    });

    await optimizeScannerTrack(scannerStream, status);

    video.srcObject = scannerStream;
    await video.play();
    video.classList.remove('hidden');
    startButton.classList.add('hidden');
    stopButton.classList.remove('hidden');
    if (!String(status.textContent || '').startsWith('Scanner aktiv')) {
      status.textContent = 'Scanner aktiv. Barcode vor die Kamera halten...';
    }
    scannerLastBarcodeAt = Date.now();
    scheduleLlavaFallback();

    if ('BarcodeDetector' in window) {
      scannerDetector = new window.BarcodeDetector({ formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e'] });
    }

    scannerInterval = setInterval(async () => {
      if (activeTab !== 'scanner') return;
      if (!video.videoWidth || !video.videoHeight) return;

      if (scannerDetector) {
        try {
          const detectionSource = getScannerDetectionSource(video, canvas, scannerDigitalZoomFactor);
          const barcodes = await scannerDetector.detect(detectionSource);
          if (barcodes.length) {
            const value = String(barcodes[0].rawValue || '').trim();
            if (value && value !== scannerLastBarcode) {
              await lookupBarcode(value);
            }
          }
        } catch (_) {
          // Ignore detector errors and keep scanning
        }
      }
    }, 900);
  } catch (_) {
    status.textContent = 'Kamera konnte nicht gestartet werden. Bitte Berechtigung prüfen.';
  }
}

async function optimizeScannerTrack(stream, status) {
  const videoTrack = stream?.getVideoTracks?.()[0];
  if (!videoTrack) return;

  const capabilities = videoTrack.getCapabilities ? videoTrack.getCapabilities() : null;
  const constraints = {};

  if (capabilities?.focusMode?.includes('continuous')) {
    constraints.focusMode = 'continuous';
  }

  if (capabilities?.zoom) {
    const minZoom = Number(capabilities.zoom.min || 1);
    const maxZoom = Number(capabilities.zoom.max || minZoom);
    const preferredZoom = Math.max(minZoom, Math.min(maxZoom, 1.8));
    constraints.zoom = preferredZoom;
    status.textContent = `Scanner aktiv (Kamera-Zoom ${preferredZoom.toFixed(1)}x). Barcode vor die Kamera halten...`;
  }

  if (!Object.keys(constraints).length) return;

  try {
    await videoTrack.applyConstraints({ advanced: [constraints] });
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

  const sourceWidth = Math.round(video.videoWidth / zoomFactor);
  const sourceHeight = Math.round(video.videoHeight / zoomFactor);
  const sourceX = Math.max(0, Math.round((video.videoWidth - sourceWidth) / 2));
  const sourceY = Math.max(0, Math.round((video.videoHeight - sourceHeight) / 2));

  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;

  context.drawImage(
    video,
    sourceX,
    sourceY,
    sourceWidth,
    sourceHeight,
    0,
    0,
    canvas.width,
    canvas.height
  );

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
  scannerLlavaInFlight = false;

  if (scannerStream) {
    scannerStream.getTracks().forEach((track) => track.stop());
    scannerStream = null;
  }

  if (video) {
    video.pause();
    video.srcObject = null;
    video.classList.add('hidden');
  }

  if (startButton) startButton.classList.remove('hidden');
  if (stopButton) stopButton.classList.add('hidden');
}
