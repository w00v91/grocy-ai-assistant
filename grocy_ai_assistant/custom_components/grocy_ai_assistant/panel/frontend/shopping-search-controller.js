import { createDashboardStore } from './dashboard-store.js';
import { getErrorMessage } from './dashboard-api-client.js';

export const SEARCH_FLOW_STATES = {
  IDLE: 'idle',
  TYPING: 'typing',
  LOADING_VARIANTS: 'loading_variants',
  VARIANTS_READY: 'variants_ready',
  SUBMITTING: 'submitting',
  SUCCESS: 'success',
  ERROR: 'error',
};

const DEFAULT_VARIANT_DEBOUNCE_MS = 250;
const MIN_PRODUCT_SEARCH_LENGTH = 2;

function createDefaultTimerApi() {
  const setTimeoutImpl = typeof globalThis.window?.setTimeout === 'function'
    ? globalThis.window.setTimeout.bind(globalThis.window)
    : (...args) => globalThis.setTimeout(...args);
  const clearTimeoutImpl = typeof globalThis.window?.clearTimeout === 'function'
    ? globalThis.window.clearTimeout.bind(globalThis.window)
    : (...args) => globalThis.clearTimeout(...args);
  return {
    setTimeout: (...args) => setTimeoutImpl(...args),
    clearTimeout: (...args) => clearTimeoutImpl(...args),
  };
}

export function parseAmountPrefixedSearch(rawValue) {
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



function hasBackgroundImageJob(payload) {
  return Boolean(
    payload?.image_generation_started
    || payload?.background_image_generation_started
    || payload?.image_generation_queued
    || payload?.image_job_started
    || payload?.picture_generation_started
  );
}

function buildProductCreationSuccessMessage(payload) {
  const messages = ['Produkt wurde angelegt und zur Einkaufsliste hinzugefügt.'];
  if (hasBackgroundImageJob(payload)) {
    messages.push('Produktbild wird im Hintergrund erstellt.');
  }
  return messages.join(' ');
}

function getBackendConflictMessage(payload, fallbackMessage = 'Eine Anfrage läuft bereits. Bitte kurz warten und dann erneut versuchen.') {
  const rawReason = String(
    payload?.reason
    || payload?.detail?.reason
    || payload?.detail?.details?.[0]?.reason
    || payload?.details?.[0]?.reason
    || payload?.action
    || payload?.detail?.action
    || ''
  ).toLowerCase();
  const rawMessage = getErrorMessage(payload, '');
  const message = String(rawMessage || '').trim();

  if (rawReason.includes('product_creation') || rawReason.includes('product_creation_in_flight') || rawReason.includes('produktanlage')) {
    return message || 'Aktive Produktanlage: Bitte kurz warten und dann erneut versuchen.';
  }
  if (rawReason.includes('image') || rawReason.includes('picture') || rawReason.includes('bild')) {
    return message || 'Aktive Bildgenerierung: Bitte kurz warten und dann erneut versuchen.';
  }
  if (rawReason.includes('search') || rawReason.includes('suche')) {
    return message || 'Aktive Suche: Bitte kurz warten und dann erneut versuchen.';
  }
  return message || fallbackMessage;
}

function getMinimumSearchLengthMessage(length) {
  const remainingCharacters = MIN_PRODUCT_SEARCH_LENGTH - length;
  if (remainingCharacters <= 0) {
    return 'Bereit.';
  }
  return remainingCharacters === 1
    ? 'Noch 1 Buchstabe bis zur Produktsuche.'
    : `Noch ${remainingCharacters} Buchstaben bis zur Produktsuche.`;
}

function buildInitialState() {
  return {
    flowState: SEARCH_FLOW_STATES.IDLE,
    query: '',
    parsedAmount: null,
    variants: [],
    isLoadingVariants: false,
    isSubmitting: false,
    statusMessage: 'Bereit.',
    errorMessage: '',
    clearButtonVisible: false,
    variantsRequestToken: 0,
    variantDebounce: null,
    lastBlockedReason: null,
  };
}

export function createShoppingSearchController({
  api,
  getDefaultAmount = () => 1,
  getBestBeforeDate = () => '',
  onShoppingListChanged = async () => {},
  debounceMs = DEFAULT_VARIANT_DEBOUNCE_MS,
  timerApi = createDefaultTimerApi(),
} = {}) {
  const store = createDashboardStore(buildInitialState());
  let currentApi = api;
  let activeSearchKey = null;

  function getState() {
    return store.getState();
  }

  function setState(partialState = {}) {
    return store.patch(partialState);
  }

  function clearVariantDebounce() {
    const timer = getState().variantDebounce;
    if (timer) timerApi.clearTimeout(timer);
    setState({ variantDebounce: null });
  }

  function invalidateVariantRequests() {
    const requestToken = getState().variantsRequestToken + 1;
    setState({
      variantsRequestToken: requestToken,
      isLoadingVariants: false,
    });
    return requestToken;
  }

  function applyQueryState(nextQuery, options = {}) {
    const normalizedQuery = String(nextQuery || '');
    const { amountFromName } = parseAmountPrefixedSearch(normalizedQuery);
    const nextFlowState = options.flowState
      || (normalizedQuery.trim() ? SEARCH_FLOW_STATES.TYPING : SEARCH_FLOW_STATES.IDLE);
    const nextStatusMessage = options.statusMessage ?? (
      normalizedQuery.trim()
        ? 'Tippe weiter für Live-Vorschläge oder bestätige mit Enter.'
        : 'Bereit.'
    );

    return setState({
      query: normalizedQuery,
      parsedAmount: amountFromName,
      clearButtonVisible: Boolean(normalizedQuery),
      flowState: nextFlowState,
      errorMessage: options.keepErrorMessage ? getState().errorMessage : '',
      statusMessage: nextStatusMessage,
      lastBlockedReason: null,
    });
  }

  function updateClearButtonVisibility() {
    return setState({ clearButtonVisible: Boolean(getState().query) });
  }

  function scheduleVariantLoading(query, requestToken) {
    clearVariantDebounce();
    const timer = timerApi.setTimeout(() => {
      setState({ variantDebounce: null });
      void loadVariants(query, { requestToken });
    }, debounceMs);
    setState({ variantDebounce: timer });
  }

  function resetVariantsForEmptyQuery(effectiveQuery, amountFromName, requestToken) {
    return setState({
      query: effectiveQuery,
      parsedAmount: amountFromName,
      variants: [],
      isLoadingVariants: false,
      flowState: SEARCH_FLOW_STATES.IDLE,
      statusMessage: 'Bereit.',
      errorMessage: '',
      clearButtonVisible: Boolean(effectiveQuery),
      variantsRequestToken: requestToken,
      lastBlockedReason: null,
    });
  }

  function setQuery(query) {
    applyQueryState(query);
    const requestToken = invalidateVariantRequests();
    const normalizedQuery = String(query || '').trim();
    const { productName, amountFromName } = parseAmountPrefixedSearch(query);
    const normalizedProductName = productName.trim();

    if (!normalizedQuery) {
      clearVariantDebounce();
      resetVariantsForEmptyQuery(String(query || ''), amountFromName, requestToken);
      return;
    }

    if (normalizedProductName.length < MIN_PRODUCT_SEARCH_LENGTH) {
      clearVariantDebounce();
      setState({
        query: String(query || ''),
        parsedAmount: amountFromName,
        variants: [],
        isLoadingVariants: false,
        flowState: SEARCH_FLOW_STATES.TYPING,
        statusMessage: getMinimumSearchLengthMessage(normalizedProductName.length),
        errorMessage: '',
        clearButtonVisible: Boolean(String(query || '')),
        variantsRequestToken: requestToken,
      });
      return;
    }

    scheduleVariantLoading(query, requestToken);
  }

  function clearQuery() {
    clearVariantDebounce();
    const requestToken = invalidateVariantRequests();
    setState({
      ...buildInitialState(),
      variantsRequestToken: requestToken,
    });
  }

  async function loadVariants(queryOverride = null, options = {}) {
    const effectiveQuery = queryOverride === null ? getState().query : String(queryOverride || '');
    const { productName, amountFromName } = parseAmountPrefixedSearch(effectiveQuery);
    const normalizedQuery = productName.trim();
    const providedRequestToken = Number(options.requestToken);
    const requestToken = Number.isFinite(providedRequestToken) && providedRequestToken > 0
      ? providedRequestToken
      : invalidateVariantRequests();

    if (!normalizedQuery) {
      resetVariantsForEmptyQuery(effectiveQuery, amountFromName, requestToken);
      return [];
    }

    if (normalizedQuery.length < MIN_PRODUCT_SEARCH_LENGTH) {
      setState({
        query: effectiveQuery,
        parsedAmount: amountFromName,
        variants: [],
        isLoadingVariants: false,
        flowState: SEARCH_FLOW_STATES.TYPING,
        statusMessage: getMinimumSearchLengthMessage(normalizedQuery.length),
        errorMessage: '',
        clearButtonVisible: Boolean(effectiveQuery),
        variantsRequestToken: requestToken,
      });
      return [];
    }

    setState({
      query: effectiveQuery,
      parsedAmount: amountFromName,
      variants: [],
      isLoadingVariants: true,
      flowState: SEARCH_FLOW_STATES.LOADING_VARIANTS,
      statusMessage: 'Lade Live-Vorschläge…',
      errorMessage: '',
      clearButtonVisible: Boolean(effectiveQuery),
      variantsRequestToken: requestToken,
    });

    try {
      const { response, payload } = await currentApi.searchVariants(normalizedQuery);
      if (requestToken !== getState().variantsRequestToken) {
        return [];
      }
      if (!response.ok) {
        throw new Error(getErrorMessage(payload, 'Produktvarianten konnten nicht geladen werden.'));
      }

      const variants = Array.isArray(payload) ? payload : [];
      setState({
        variants,
        isLoadingVariants: false,
        flowState: variants.length ? SEARCH_FLOW_STATES.VARIANTS_READY : SEARCH_FLOW_STATES.TYPING,
        statusMessage: variants.length
          ? 'Wähle einen Treffer oder starte die Suche mit Enter.'
          : 'Keine Live-Vorschläge. Mit Enter direkt suchen.',
        errorMessage: '',
      });
      return variants;
    } catch (error) {
      if (requestToken !== getState().variantsRequestToken) {
        return [];
      }
      setState({
        variants: [],
        isLoadingVariants: false,
        flowState: SEARCH_FLOW_STATES.ERROR,
        statusMessage: 'Varianten konnten nicht geladen werden.',
        errorMessage: error.message,
      });
      return [];
    }
  }

  async function searchProduct(options = {}) {
    clearVariantDebounce();
    invalidateVariantRequests();

    const currentState = getState();
    const { productName, amountFromName } = parseAmountPrefixedSearch(currentState.query);
    const normalizedProductName = productName.trim();
    const normalizedAmountOverride = Number(options.amount);
    const amount = Number.isFinite(normalizedAmountOverride) && normalizedAmountOverride > 0
      ? normalizedAmountOverride
      : ((amountFromName ?? Number(getDefaultAmount())) || 1);
    const forceCreate = options.forceCreate === true;
    const isSuggestedCreationPath = options.suggestedCreation === true;
    const isProductCreationPath = isSuggestedCreationPath || forceCreate;
    const bestBeforeDate = String(options.bestBeforeDate ?? getBestBeforeDate() ?? '').trim();
    const nextKey = JSON.stringify([
      normalizedProductName.toLowerCase(),
      amount,
      bestBeforeDate,
      forceCreate,
    ]);

    if (!normalizedProductName) {
      setState({
        flowState: SEARCH_FLOW_STATES.ERROR,
        isSubmitting: false,
        statusMessage: 'Bitte Produktname eingeben.',
        errorMessage: 'Bitte Produktname eingeben.',
      });
      return { ok: false, payload: null };
    }

    if (normalizedProductName.length < MIN_PRODUCT_SEARCH_LENGTH) {
      const minimumLengthMessage = 'Bitte mindestens 2 Buchstaben für die Produktsuche eingeben.';
      setState({
        flowState: SEARCH_FLOW_STATES.ERROR,
        isSubmitting: false,
        statusMessage: minimumLengthMessage,
        errorMessage: minimumLengthMessage,
      });
      return { ok: false, payload: null };
    }

    if (activeSearchKey === nextKey) {
      const inFlightMessage = isProductCreationPath
        ? 'Produktanlage läuft noch.'
        : 'Diese Produktanfrage wird gerade noch verarbeitet…';
      if (typeof globalThis.console?.debug === 'function') {
        globalThis.console.debug('Shopping search blocked: local request still in flight.', {
          reason: 'local_in_flight',
          productName: normalizedProductName,
          amount,
          bestBeforeDate,
          forceCreate,
        });
      }
      setState({
        isSubmitting: true,
        flowState: SEARCH_FLOW_STATES.SUBMITTING,
        statusMessage: inFlightMessage,
        errorMessage: '',
        lastBlockedReason: 'local_in_flight',
      });
      return {
        ok: false,
        payload: {
          action: isProductCreationPath ? 'product_creation_in_flight' : 'search_in_flight',
          reason: 'local_in_flight',
        },
      };
    }
    activeSearchKey = nextKey;

    setState({
      parsedAmount: amountFromName,
      isSubmitting: true,
      flowState: SEARCH_FLOW_STATES.SUBMITTING,
      statusMessage: isSuggestedCreationPath
        ? 'Lege neues Produkt aus Vorschlag an…'
        : (forceCreate ? 'Füge Produkt hinzu…' : 'Prüfe Produkt…'),
      errorMessage: '',
      lastBlockedReason: null,
    });

    try {
      const { response, payload } = await currentApi.searchProduct({
        name: normalizedProductName,
        amount,
        best_before_date: bestBeforeDate,
        force_create: forceCreate,
      });

      if (!response.ok) {
        if (response.status === 409) {
          throw new Error(getBackendConflictMessage(
            payload,
            isProductCreationPath
              ? 'Aktive Produktanlage: Bitte kurz warten und dann erneut versuchen.'
              : 'Aktive Suche: Bitte kurz warten und dann erneut versuchen.',
          ));
        }
        throw new Error(getErrorMessage(payload, 'Produkt konnte nicht geprüft werden.'));
      }

      if (payload?.success === false || payload?.action === 'search_in_flight') {
        const inFlightMessage = payload?.message || (isSuggestedCreationPath
          ? 'Diese Produktanlage läuft bereits.'
          : 'Eine identische Produktsuche läuft bereits.');
        setState({
          isSubmitting: false,
          isLoadingVariants: false,
          flowState: SEARCH_FLOW_STATES.ERROR,
          statusMessage: inFlightMessage,
          errorMessage: inFlightMessage,
          lastBlockedReason: 'backend_in_flight',
        });
        return { ok: false, payload };
      }

      const variants = Array.isArray(payload?.variants) ? payload.variants : [];
      const statusMessage = payload?.action === 'created_and_added'
        ? buildProductCreationSuccessMessage(payload)
        : (payload?.message || (variants.length ? 'Varianten gefunden.' : 'Produkt verarbeitet.'));
      if (payload?.action === 'variant_selection_required' && variants.length) {
        setState({
          variants,
          isSubmitting: false,
          isLoadingVariants: false,
          flowState: SEARCH_FLOW_STATES.VARIANTS_READY,
          statusMessage,
          errorMessage: '',
        });
        return { ok: true, payload };
      }

      setState({
        variants: [],
        isSubmitting: false,
        isLoadingVariants: false,
        flowState: SEARCH_FLOW_STATES.SUCCESS,
        statusMessage,
        errorMessage: '',
        lastBlockedReason: null,
      });
      await onShoppingListChanged();
      return { ok: true, payload };
    } catch (error) {
      setState({
        isSubmitting: false,
        isLoadingVariants: false,
        flowState: SEARCH_FLOW_STATES.ERROR,
        statusMessage: error.message.includes('Aktive') || error.message.includes('Produktanlage')
          ? error.message
          : 'Produkt konnte nicht geprüft werden.',
        errorMessage: error.message,
      });
      return { ok: false, payload: null };
    } finally {
      if (activeSearchKey === nextKey) {
        activeSearchKey = null;
      }
    }
  }

  async function confirmVariant(productId, productName, amountOverride = null) {
    clearVariantDebounce();
    invalidateVariantRequests();

    const numericProductId = Number(productId);
    const normalizedOverride = Number(amountOverride);
    const { amountFromName } = parseAmountPrefixedSearch(getState().query);
    const amount = Number.isFinite(normalizedOverride) && normalizedOverride > 0
      ? normalizedOverride
      : ((amountFromName ?? Number(getDefaultAmount())) || 1);
    const requestProductName = Number.isFinite(amount) && amount > 0
      ? `${amount} ${productName}`
      : productName;
    const bestBeforeDate = String(getBestBeforeDate() ?? '').trim();

    if (!Number.isFinite(numericProductId) || numericProductId <= 0) {
      setState({
        flowState: SEARCH_FLOW_STATES.ERROR,
        isSubmitting: false,
        statusMessage: 'Ungültige Produkt-ID.',
        errorMessage: 'Ungültige Produkt-ID.',
      });
      return { ok: false, payload: null };
    }

    setState({
      isSubmitting: true,
      flowState: SEARCH_FLOW_STATES.SUBMITTING,
      statusMessage: 'Füge Produkt hinzu…',
      errorMessage: '',
      lastBlockedReason: null,
    });

    try {
      const { response, payload } = await currentApi.addExistingProduct({
        product_id: numericProductId,
        product_name: requestProductName,
        amount,
        best_before_date: bestBeforeDate,
      });

      if (!response.ok) {
        throw new Error(getErrorMessage(payload, 'Produkt konnte nicht hinzugefügt werden.'));
      }

      const variants = Array.isArray(payload?.variants) ? payload.variants : [];
      const statusMessage = payload?.message || 'Produkt hinzugefügt.';
      if (payload?.action === 'variant_selection_required' && variants.length) {
        setState({
          variants,
          isSubmitting: false,
          isLoadingVariants: false,
          flowState: SEARCH_FLOW_STATES.VARIANTS_READY,
          statusMessage,
          errorMessage: '',
        });
        return { ok: true, payload };
      }

      setState({
        variants: [],
        isSubmitting: false,
        isLoadingVariants: false,
        flowState: SEARCH_FLOW_STATES.SUCCESS,
        statusMessage,
        errorMessage: '',
        lastBlockedReason: null,
      });
      await onShoppingListChanged();
      return { ok: true, payload };
    } catch (error) {
      setState({
        isSubmitting: false,
        isLoadingVariants: false,
        flowState: SEARCH_FLOW_STATES.ERROR,
        statusMessage: 'Produkt konnte nicht hinzugefügt werden.',
        errorMessage: error.message,
      });
      return { ok: false, payload: null };
    }
  }

  async function searchSuggestedProduct(productName, options = {}) {
    const normalizedAmount = Number(options.amount);
    const explicitAmount = Number.isFinite(normalizedAmount) && normalizedAmount > 0
      ? normalizedAmount
      : null;
    const prefixedProductName = explicitAmount ? `${explicitAmount} ${productName}` : productName;

    applyQueryState(prefixedProductName, {
      flowState: prefixedProductName.trim() ? SEARCH_FLOW_STATES.TYPING : SEARCH_FLOW_STATES.IDLE,
      statusMessage: prefixedProductName.trim()
        ? 'Vorschlag übernommen. Prüfe Produkt…'
        : 'Bereit.',
    });
    updateClearButtonVisibility();

    const nextOptions = { ...options };
    delete nextOptions.amount;
    return searchProduct(nextOptions);
  }

  async function selectVariant({ productId, productName, amount, source, productSource }) {
    const normalizedSource = String(source || productSource || 'grocy').trim().toLowerCase() || 'grocy';
    const { amountFromName } = parseAmountPrefixedSearch(getState().query);
    const explicitAmount = amountFromName ?? null;
    if (normalizedSource === 'input') {
      return searchSuggestedProduct(productName, {
        forceCreate: true,
        amount: explicitAmount,
        suggestedCreation: true,
      });
    }

    const numericProductId = Number(productId);
    if (!Number.isFinite(numericProductId) || !productId || normalizedSource === 'ai') {
      return searchSuggestedProduct(productName, {
        amount: explicitAmount,
        suggestedCreation: true,
      });
    }

    return confirmVariant(numericProductId, productName, amount);
  }

  function setApi(nextApi) {
    currentApi = nextApi;
  }

  function dispose() {
    clearVariantDebounce();
  }

  return {
    getState,
    subscribe: store.subscribe,
    setApi,
    dispose,
    actions: {
      setQuery,
      clearQuery,
      loadVariants,
      searchProduct,
      confirmVariant,
      searchSuggestedProduct,
      selectVariant,
      updateClearButtonVisibility,
    },
  };
}
