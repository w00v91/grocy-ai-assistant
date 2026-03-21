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

export function createDashboardApiClient({ apiBasePath = '', ingressPrefix = '' } = {}) {
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
  };
}
