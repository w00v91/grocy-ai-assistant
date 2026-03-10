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

function renderShoppingList(items) {
  const list = document.getElementById('shopping-list');
  if (!items.length) {
    list.innerHTML = '<li>Keine Einträge in der Einkaufsliste.</li>';
    return;
  }

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
  if (!items.length) {
    list.innerHTML = '<div class="muted">Keine passenden Varianten gefunden.</div>';
    return;
  }

  list.innerHTML = items.map((item) => `
    <div class="variant-card">
      <button type="button" class="variant-select" data-product-id="${item.id}" data-product-name="${encodeURIComponent(item.name)}">
        <img src="${toImageSource(item.picture_url)}" alt="${item.name}" loading="lazy" />
        <div><strong>${item.name}</strong></div>
      </button>
    </div>
  `).join('');
}

async function loadVariants() {
  const key = ensureApiKey();
  const status = document.getElementById('status');
  const name = document.getElementById('name').value || '';

  if (!key) return;

  const query = name.trim();
  if (!query) {
    document.getElementById('variant-list').innerHTML = '';
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

  const productId = Number(target.dataset.productId);
  const productName = decodeURIComponent(target.dataset.productName || '');
  confirmVariant(productId, productName);
});

document.getElementById('name').addEventListener('input', () => {
  clearTimeout(variantsDebounce);
  variantsDebounce = setTimeout(() => {
    loadVariants();
  }, 250);
});

const savedTheme = localStorage.getItem(themeStorageKey) || 'light';
applyTheme(savedTheme);
loadShoppingList();
loadVariants();
