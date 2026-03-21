export function getErrorMessage(payload, fallbackMessage) {
  if (payload && payload.error && payload.error.message) return payload.error.message;
  if (payload && payload.detail) return payload.detail;
  return fallbackMessage;
}

async function parseJsonSafe(response) {
  try {
    return await response.json();
  } catch (_) {
    return {};
  }
}

function resolveRequestHeaders(options = {}, getAuthHeaders) {
  const authHeaders = typeof getAuthHeaders === 'function' ? (getAuthHeaders() || {}) : {};
  return {
    ...authHeaders,
    ...(options.headers || {}),
  };
}

export function createDashboardApiClient({ apiBasePath = '', ingressPrefix = '', getAuthHeaders = null } = {}) {
  function buildUrl(path) {
    const normalizedPath = '/' + String(path || '').replace(/^\/+/, '');
    const normalizedBase = String(apiBasePath || '').replace(/\/+$/, '');
    if (normalizedBase) return `${normalizedBase}${normalizedPath}`;

    const normalizedIngressPrefix = String(ingressPrefix || '').replace(/\/+$/, '');
    if (normalizedIngressPrefix) return `${normalizedIngressPrefix}${normalizedPath}`;

    return normalizedPath;
  }

  async function request(path, options = {}) {
    const response = await fetch(buildUrl(path), {
      ...options,
      headers: resolveRequestHeaders(options, getAuthHeaders),
      credentials: 'same-origin',
    });
    const payload = await parseJsonSafe(response);
    return { response, payload };
  }

  return {
    buildUrl,
    request,
    fetchShoppingList() {
      return request('/api/dashboard/shopping-list');
    },
    searchVariants(query) {
      return request(`/api/dashboard/search-variants?q=${encodeURIComponent(query)}&include_ai=false`);
    },
    addExistingProduct(payload) {
      return request('/api/dashboard/add-existing-product', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
    },
    updateShoppingListItemNote(shoppingListId, note) {
      return request(`/api/dashboard/shopping-list/item/${shoppingListId}/note`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note }),
      });
    },
    updateShoppingListItemAmount(shoppingListId, amount) {
      return request(`/api/dashboard/shopping-list/item/${shoppingListId}/amount`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount }),
      });
    },
    updateShoppingListItemBestBefore(shoppingListId, bestBeforeDate) {
      return request(`/api/dashboard/shopping-list/item/${shoppingListId}/best-before`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ best_before_date: bestBeforeDate }),
      });
    },
    resetShoppingListItemBestBefore(shoppingListId) {
      return request(`/api/dashboard/shopping-list/item/${shoppingListId}/best-before/reset`, {
        method: 'POST',
      });
    },
    incrementShoppingItemAmount(shoppingListId) {
      return request(`/api/dashboard/shopping-list/item/${shoppingListId}/amount/increment`, {
        method: 'POST',
      });
    },
    deleteShoppingListItem(shoppingListId) {
      return request(`/api/dashboard/shopping-list/item/${shoppingListId}`, {
        method: 'DELETE',
      });
    },
    completeShoppingListItem(shoppingListId) {
      return request(`/api/dashboard/shopping-list/item/${shoppingListId}/complete`, {
        method: 'POST',
      });
    },
    completeShoppingList() {
      return request('/api/dashboard/shopping-list/complete', {
        method: 'POST',
      });
    },
    clearShoppingList() {
      return request('/api/dashboard/shopping-list/clear', {
        method: 'DELETE',
      });
    },
    searchProduct(payload) {
      return request('/api/dashboard/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
    },
    fetchLocations() {
      return request('/api/dashboard/locations');
    },
    fetchStockProducts({ includeAllProducts = false, query = '', locationIds = [] } = {}) {
      const params = new URLSearchParams();
      if (includeAllProducts) params.set('include_all_products', 'true');
      if (query) params.set('q', query);
      if (Array.isArray(locationIds) && locationIds.length) params.set('location_ids', locationIds.join(','));
      const path = params.size ? `/api/dashboard/stock-products?${params.toString()}` : '/api/dashboard/stock-products';
      return request(path);
    },
    consumeStockProduct(stockId, { amount = 1, productId = null } = {}) {
      const suffix = Number.isFinite(Number(productId)) && Number(productId) > 0
        ? `?product_id=${encodeURIComponent(productId)}`
        : '';
      return request(`/api/dashboard/stock-products/${encodeURIComponent(stockId)}/consume${suffix}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount }),
      });
    },
    updateStockProduct(stockId, payload, { productId = null } = {}) {
      const suffix = Number.isFinite(Number(productId)) && Number(productId) > 0
        ? `?product_id=${encodeURIComponent(productId)}`
        : '';
      return request(`/api/dashboard/stock-products/${encodeURIComponent(stockId)}${suffix}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
    },
    deleteStockProduct(stockId, { productId = null } = {}) {
      const suffix = Number.isFinite(Number(productId)) && Number(productId) > 0
        ? `?product_id=${encodeURIComponent(productId)}`
        : '';
      return request(`/api/dashboard/stock-products/${encodeURIComponent(stockId)}${suffix}`, {
        method: 'DELETE',
      });
    },
    deleteProductPicture(productId) {
      return request(`/api/dashboard/products/${encodeURIComponent(productId)}/picture`, {
        method: 'DELETE',
      });
    },
    fetchRecipeSuggestions(payload) {
      return request('/api/dashboard/recipe-suggestions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
    },
    addMissingRecipeProducts(recipeId) {
      return request(`/api/dashboard/recipe/${encodeURIComponent(recipeId)}/add-missing`, {
        method: 'POST',
      });
    },
    lookupBarcode(barcode) {
      return request(`/api/v1/barcode/${encodeURIComponent(barcode)}`);
    },
    scanImage(imageBase64, { signal } = {}) {
      return request('/api/v1/scan/image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_base64: imageBase64 }),
        signal,
      });
    },
  };
}
