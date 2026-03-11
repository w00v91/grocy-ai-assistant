const rootElement = document.documentElement;
const configuredApiKey = rootElement.dataset.configuredApiKey || '';
const apiBasePath = rootElement.dataset.apiBasePath || '';
const themeStorageKey = 'grocy-dashboard-theme';
let apiKey = configuredApiKey || '';
const ingressPrefixMatch = window.location.pathname.match(/^\/api\/hassio_ingress\/[^\/]+/);
const ingressPrefix = ingressPrefixMatch ? ingressPrefixMatch[0] : '';

function applyTheme(theme) {
  const root = document.documentElement;
  const toggle = document.getElementById('theme-toggle');

  if (theme === 'dark') {
    root.setAttribute('data-theme', 'dark');
    toggle.textContent = '☀️ Lightmode';
    return;
  }

  root.removeAttribute('data-theme');
  toggle.textContent = '🌙 Darkmode';
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

function renderShoppingList(items) {
  const list = document.getElementById('shopping-list');
  if (!items.length) {
    list.innerHTML = '';
    list.classList.add('hidden');
    return;
  }

  list.classList.remove('hidden');

  list.innerHTML = items.map((item) => `
    <li>
      <img src="${toImageSource(item.picture_url)}" alt="${item.product_name}" loading="lazy" />
      <div>
        <div><strong>${item.product_name}</strong></div>
        <div class="muted">${item.note || 'Keine Notiz'}</div>
      </div>
      <span class="badge">Menge: ${item.amount}</span>
    </li>
  `).join('');
}

async function loadShoppingList() {
  const key = ensureApiKey();
  const status = document.getElementById('status');
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
      status.textContent = payload.detail || 'Einkaufsliste konnte nicht geladen werden.';
      return;
    }

    renderShoppingList(payload);
    status.textContent = `Einkaufsliste geladen (${payload.length} Einträge).`;
  } catch (_) {
    status.textContent = 'Einkaufsliste konnte nicht geladen werden (Netzwerk-/Ingress-Fehler).';
  }
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
  const key = ensureApiKey();
  const status = document.getElementById('status');
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
      status.textContent = payload.detail || 'Varianten konnten nicht geladen werden.';
      return;
    }

    renderVariants(payload);
  } catch (_) {
    status.textContent = 'Varianten konnten nicht geladen werden (Netzwerk-/Ingress-Fehler).';
  }
}

async function confirmVariant(productId, productName) {
  const key = ensureApiKey();
  const status = document.getElementById('status');

  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return;
  }

  status.textContent = `Füge ${productName} zur Einkaufsliste hinzu...`;
  try {
    const res = await fetch(buildApiUrl('/api/dashboard/add-existing-product'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
      body: JSON.stringify({ product_id: productId, product_name: productName }),
    });
    const payload = await parseJsonSafe(res);
    status.textContent = payload.message || payload.detail || 'Unbekannte Antwort';

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
}

async function clearShoppingList() {
  const key = ensureApiKey();
  const status = document.getElementById('status');
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
      status.textContent = payload.detail || 'Einkaufsliste konnte nicht geleert werden.';
      return;
    }

    status.textContent = payload.message || 'Einkaufsliste geleert.';
    await loadShoppingList();
  } catch (_) {
    status.textContent = 'Einkaufsliste konnte nicht geleert werden (Netzwerk-/Ingress-Fehler).';
  }
}

async function searchProduct() {
  const name = document.getElementById('name').value;
  const status = document.getElementById('status');
  const key = ensureApiKey();

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
      body: JSON.stringify({ name })
    });

    const payload = await parseJsonSafe(res);
    status.textContent = payload.message || payload.detail || 'Unbekannte Antwort';

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
loadShoppingList();
loadLocations();


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

function renderLocations(items) {
  const container = document.getElementById('location-filters');
  if (!container) return;

  if (!items.length) {
    container.innerHTML = '<div class="muted">Keine Lagerstandorte gefunden.</div>';
    return;
  }

  container.innerHTML = items.map((item) => `
    <label class="stock-item">
      <input type="checkbox" value="${item.id}" checked />
      <span><strong>${item.name}</strong></span>
    </label>
  `).join('');
}

function renderStockProducts(items) {
  const container = document.getElementById('stock-products');
  if (!items.length) {
    container.innerHTML = '<div class="muted">Keine Produkte für die ausgewählten Lagerstandorte gefunden.</div>';
    return;
  }

  container.innerHTML = items.map((item) => `
    <label class="stock-item">
      <input type="checkbox" value="${item.id}" />
      <span><strong>${item.name}</strong> <small class="muted">${item.location_name || 'Lager'} · ${item.amount || '-'} </small></span>
    </label>
  `).join('');
}

function renderRecipeList(elementId, items, emptyText) {
  const list = document.getElementById(elementId);
  if (!items.length) {
    list.innerHTML = `<li>${emptyText}</li>`;
    return;
  }

  list.innerHTML = items.map((item) => `
    <li>
      <div>
        <div><strong>${item.title}</strong></div>
        <div class="muted">${item.reason || ''}</div>
      </div>
    </li>
  `).join('');
}

async function loadLocations() {
  const key = ensureApiKey();
  if (!key) return;

  try {
    const res = await fetch(buildApiUrl('/api/dashboard/locations'), {
      headers: { 'Authorization': `Bearer ${key}` },
    });
    const payload = await parseJsonSafe(res);

    if (!res.ok) {
      document.getElementById('status').textContent = payload.detail || 'Standorte konnten nicht geladen werden.';
      return;
    }

    renderLocations(payload);
    await loadStockProducts();
  } catch (_) {
    document.getElementById('status').textContent = 'Standorte konnten nicht geladen werden (Netzwerk-/Ingress-Fehler).';
  }
}

async function loadStockProducts() {
  const key = ensureApiKey();
  if (!key) return;

  try {
    const selectedLocationIds = getSelectedLocationIds();
    const query = selectedLocationIds.length ? `?location_ids=${selectedLocationIds.join(',')}` : '';
    const res = await fetch(buildApiUrl(`/api/dashboard/stock-products${query}`), {
      headers: { 'Authorization': `Bearer ${key}` },
    });
    const payload = await parseJsonSafe(res);

    if (!res.ok) {
      document.getElementById('status').textContent = payload.detail || 'Bestand konnte nicht geladen werden.';
      return;
    }

    renderStockProducts(payload);
    await loadRecipeSuggestions();
  } catch (_) {
    document.getElementById('status').textContent = 'Bestand konnte nicht geladen werden (Netzwerk-/Ingress-Fehler).';
  }
}

async function loadRecipeSuggestions() {
  const key = ensureApiKey();
  const status = document.getElementById('status');
  if (!key) {
    status.textContent = 'Kein API-Key angegeben.';
    return;
  }

  const selectedIds = Array.from(document.querySelectorAll('#stock-products input[type="checkbox"]:checked'))
    .map((checkbox) => Number(checkbox.value));
  const selectedLocationIds = getSelectedLocationIds();

  status.textContent = selectedIds.length
    ? 'Lade Rezeptvorschläge für Auswahl...'
    : 'Lade Rezeptvorschläge aus dem aktuellen Lagerbestand...';

  try {
    const res = await fetch(buildApiUrl('/api/dashboard/recipe-suggestions'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
      body: JSON.stringify({ product_ids: selectedIds, location_ids: selectedLocationIds }),
    });
    const payload = await parseJsonSafe(res);

    if (!res.ok) {
      status.textContent = payload.detail || 'Rezeptvorschläge konnten nicht geladen werden.';
      return;
    }

    renderRecipeList('grocy-recipe-list', payload.grocy_recipes || [], 'Keine gespeicherten Grocy-Rezepte gefunden.');
    renderRecipeList('ai-recipe-list', payload.ai_recipes || [], 'Keine KI-Rezepte erzeugt.');
    status.textContent = `Rezeptvorschläge geladen für: ${(payload.selected_products || []).join(', ')}`;
  } catch (_) {
    status.textContent = 'Rezeptvorschläge konnten nicht geladen werden (Netzwerk-/Ingress-Fehler).';
  }
}
