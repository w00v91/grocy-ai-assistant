export const VARIANT_SOURCE_LABELS = {
  grocy: 'Grocy',
  ai: 'KI-Vorschlag',
  input: 'Neu anlegen',
};

export const DEFAULT_IMAGE_PLACEHOLDER = 'https://placehold.co/80x80?text=Kein+Bild';
const AUTHENTICATED_PANEL_IMAGE_SELECTOR = 'img[data-auth-image-src]';
const authenticatedPanelImageStates = new WeakMap();

export function bindShoppingImageFallbacks(root = document) {
  if (!root?.querySelectorAll) return;

  root.querySelectorAll('img[data-shopping-image]').forEach((image) => {
    const applyFallback = () => {
      if (image.dataset.fallbackApplied === 'true') return;
      image.dataset.fallbackApplied = 'true';
      image.src = image.dataset.fallbackSrc || DEFAULT_IMAGE_PLACEHOLDER;
    };

    if (image.dataset.fallbackBound !== 'true') {
      image.dataset.fallbackBound = 'true';
      image.addEventListener('error', applyFallback);
    }
    if (image.complete && image.naturalWidth === 0) {
      applyFallback();
    }
  });
}

function getAuthenticatedImageStates(root) {
  if (!authenticatedPanelImageStates.has(root)) {
    authenticatedPanelImageStates.set(root, new Map());
  }
  return authenticatedPanelImageStates.get(root);
}

function revokeObjectUrl(objectUrl) {
  if (!objectUrl || typeof URL?.revokeObjectURL !== 'function') return;
  URL.revokeObjectURL(objectUrl);
}

function cleanupAuthenticatedImageState(state, { abort = true } = {}) {
  if (!state) return;
  if (abort) {
    state.controller?.abort?.();
  }
  revokeObjectUrl(state.objectUrl);
}

export function isAuthenticatedPanelImageSource(url) {
  const normalized = String(url || '').trim();
  if (!normalized || normalized.startsWith('data:')) return false;

  try {
    const parsed = new URL(
      normalized,
      typeof window !== 'undefined' ? window.location.origin : 'http://localhost',
    );
    return parsed.pathname.endsWith('/api/dashboard/product-picture');
  } catch (_) {
    return normalized.includes('/api/dashboard/product-picture');
  }
}

export function resolveRenderableImageSource(url, { resolveUrl, fallbackSrc = DEFAULT_IMAGE_PLACEHOLDER } = {}) {
  const resolved = resolveShoppingImageSource(url, { resolveUrl });
  if (!isAuthenticatedPanelImageSource(resolved)) {
    return {
      authSrc: '',
      fallbackSrc,
      src: resolved,
    };
  }

  return {
    authSrc: resolved,
    fallbackSrc,
    src: fallbackSrc,
  };
}

export function bindAuthenticatedPanelImages(root = document, { loadImage } = {}) {
  if (!root?.querySelectorAll || typeof loadImage !== 'function') return;

  const states = getAuthenticatedImageStates(root);
  const images = Array.from(root.querySelectorAll(AUTHENTICATED_PANEL_IMAGE_SELECTOR));
  const activeImages = new Set(images);

  for (const [image, state] of states.entries()) {
    if (activeImages.has(image)) continue;
    cleanupAuthenticatedImageState(state);
    states.delete(image);
  }

  images.forEach((image) => {
    const authSrc = String(image.dataset.authImageSrc || '').trim();
    if (!authSrc) return;

    const existingState = states.get(image);
    if (existingState?.src === authSrc && existingState.status === 'loaded') return;
    if (existingState?.src === authSrc && existingState.status === 'loading') return;

    cleanupAuthenticatedImageState(existingState);

    const controller = typeof AbortController === 'function'
      ? new AbortController()
      : { signal: undefined, abort() {} };
    const state = {
      controller,
      objectUrl: '',
      src: authSrc,
      status: 'loading',
    };
    states.set(image, state);

    Promise.resolve(loadImage(authSrc, { signal: controller.signal }))
      .then((objectUrl) => {
        if (controller.signal?.aborted) {
          revokeObjectUrl(objectUrl);
          return;
        }
        if (states.get(image) !== state) {
          revokeObjectUrl(objectUrl);
          return;
        }

        revokeObjectUrl(state.objectUrl);
        state.objectUrl = objectUrl;
        state.status = 'loaded';
        image.src = objectUrl;
      })
      .catch(() => {
        if (controller.signal?.aborted) return;
        if (states.get(image) !== state) return;

        state.status = 'error';
        image.src = image.dataset.fallbackSrc || DEFAULT_IMAGE_PLACEHOLDER;
      });
  });
}

export function cleanupAuthenticatedPanelImages(root = document) {
  const states = authenticatedPanelImageStates.get(root);
  if (!states) return;

  for (const state of states.values()) {
    cleanupAuthenticatedImageState(state);
  }
  authenticatedPanelImageStates.delete(root);
}

export function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

export function formatAmount(value, fallback = '1') {
  const normalized = String(value ?? '').trim();
  return normalized || fallback;
}

export function formatBadgeValue(value, fallback = '-') {
  const normalized = String(value ?? '').trim();
  return normalized || fallback;
}

export function formatStockCount(value, fallback = '0') {
  const textValue = String(value ?? '').trim();
  if (!textValue) return fallback;

  const normalized = textValue.replace(',', '.');
  const parsed = Number(normalized);
  if (!Number.isFinite(parsed) || parsed < 0) return textValue;

  if (Number.isInteger(parsed)) return String(parsed);

  return parsed.toLocaleString('de-DE', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

export function resolveShoppingImageSource(url, { resolveUrl } = {}) {
  const normalized = String(url || '').trim();
  if (!normalized) return DEFAULT_IMAGE_PLACEHOLDER;
  if (typeof resolveUrl === 'function') {
    return resolveUrl(normalized);
  }
  return normalized;
}

function buildDataAttributes(dataset = {}) {
  return Object.entries(dataset)
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .map(([key, value]) => `data-${key}="${escapeHtml(value)}"`)
    .join(' ');
}

function renderBadge(label, value, options = {}) {
  const variantClassName = options.variant ? ` shopping-badge--${options.variant}` : '';
  const extraClassName = options.className ? ` ${options.className}` : '';
  const hiddenLabelClassName = options.hideLabel ? ' shopping-badge__label--hidden' : '';
  const element = options.element === 'button' ? 'button' : 'span';
  const typeAttribute = element === 'button' ? ' type="button"' : '';
  const attributes = buildDataAttributes(options.dataset);
  const attributeSuffix = attributes ? ` ${attributes}` : '';
  const ariaLabel = options.hideLabel ? ` aria-label="${escapeHtml(`${label}: ${value}`)}"` : '';
  return `
    <${element} class="shopping-badge${variantClassName}${extraClassName}"${typeAttribute}${ariaLabel}${attributeSuffix}>
      <span class="shopping-badge__label${hiddenLabelClassName}">${escapeHtml(label)}</span>
      <span class="shopping-badge__value">${escapeHtml(value)}</span>
    </${element}>
  `;
}

function renderContextRow(label, value, options = {}) {
  const normalizedValue = String(value ?? '').trim();
  if (!normalizedValue) return '';
  const variantClassName = options.variant ? ` shopping-card__context-item--${options.variant}` : '';
  return `
    <li class="shopping-card__context-item${variantClassName}">
      <span class="shopping-card__context-label">${escapeHtml(label)}</span>
      <span class="shopping-card__context-value">${escapeHtml(normalizedValue)}</span>
    </li>
  `;
}

function renderDetailLine(label, value, options = {}) {
  const normalizedValue = String(value ?? '').trim();
  if (!normalizedValue) return '';
  const variantClassName = options.variant ? ` shopping-card__detail-line--${options.variant}` : '';
  return `
    <div class="shopping-card__detail-line${variantClassName}">
      <span class="shopping-card__detail-label">${escapeHtml(label)}</span>
      <span class="shopping-card__detail-value">${escapeHtml(normalizedValue)}</span>
    </div>
  `;
}

function renderActionButton(action = {}) {
  const {
    label = '',
    className = 'ghost-button',
    actionName,
    dataset = {},
  } = action;
  const attributes = buildDataAttributes({ action: actionName, ...dataset });
  return `<button type="button" class="${escapeHtml(className)}" ${attributes}>${escapeHtml(label)}</button>`;
}

export function renderShoppingVariantCard(variant, options = {}) {
  const variantName = variant?.product_name || variant?.name || 'Unbekanntes Produkt';
  const variantSource = String(variant?.source || 'grocy').trim().toLowerCase() || 'grocy';
  const sourceLabel = VARIANT_SOURCE_LABELS[variantSource] || VARIANT_SOURCE_LABELS.grocy;
  const amountValue = options.amount ?? variant?.amount ?? variant?.default_amount ?? '1';
  const amountLabel = formatAmount(amountValue);
  const imageSource = resolveRenderableImageSource(variant?.picture_url, { resolveUrl: options.resolveImageUrl });
  const dataset = {
    action: options.actionName || 'shopping-select-variant',
    'product-id': variant?.product_id ?? variant?.id ?? '',
    'product-name': variantName,
    'product-source': variantSource,
    amount: amountValue,
  };
  const ctaLabel = typeof options.ctaLabel === 'string' ? options.ctaLabel : '';
  const stockValue = formatStockCount(variant?.in_stock, '');
  const bestBeforeDate = formatBadgeValue(variant?.best_before_date, '');
  const noteValue = String(variant?.note || '').trim();

  return `
    <article class="shopping-card shopping-card--variant variant-card variant-card--action" role="listitem">
      <button class="shopping-card__button variant-card__button" type="button" ${buildDataAttributes(dataset)}>
        <div class="shopping-card__surface">
          <div class="shopping-card__media-wrap">
            <img class="shopping-card__media" src="${escapeHtml(imageSource.src)}" alt="${escapeHtml(variantName)}" loading="lazy" data-shopping-image="true" data-fallback-src="${escapeHtml(imageSource.fallbackSrc)}"${imageSource.authSrc ? ` data-auth-image-src="${escapeHtml(imageSource.authSrc)}"` : ''} />
            <span class="shopping-badge shopping-badge--amount variant-amount-badge">${escapeHtml(amountLabel)}</span>
          </div>
          <div class="shopping-card__body">
            <div class="shopping-card__header">
              <strong class="shopping-card__title">${escapeHtml(variantName)}</strong>
              <span class="shopping-status-chip shopping-status-chip--source">${escapeHtml(sourceLabel)}</span>
            </div>
            ${noteValue ? `<p class="shopping-card__note">${escapeHtml(noteValue)}</p>` : ''}
            <ul class="shopping-card__context-list${stockValue || bestBeforeDate ? '' : ' hidden'}">
              ${renderContextRow('Bestand', stockValue, { variant: 'stock' })}
              ${renderContextRow('MHD', bestBeforeDate, { variant: 'mhd' })}
            </ul>
            ${ctaLabel ? `
              <div class="shopping-card__footer">
                <span class="shopping-card__cta variant-card__cta">${escapeHtml(ctaLabel)}</span>
              </div>
            ` : ''}
          </div>
        </div>
      </button>
    </article>
  `;
}

export function renderShoppingListItemCard(item, options = {}) {
  const title = item?.product_name || item?.name || 'Unbekanntes Produkt';
  const amountLabel = formatAmount(item?.amount, '1');
  const note = String(item?.note || '').trim() || (options.noteFallback ?? '');
  const stockLabel = formatStockCount(item?.in_stock, '0');
  const bestBeforeDate = formatBadgeValue(item?.best_before_date, options.mhdFallback || 'MHD wählen');
  const locationLabel = String(item?.location_name || '').trim();
  const imageSource = resolveRenderableImageSource(item?.picture_url, { resolveUrl: options.resolveImageUrl });
  const actionButtons = Array.isArray(options.actionButtons) ? options.actionButtons : [];
  const rootClassName = [
    'shopping-card',
    'shopping-card--shopping-item',
    options.rootClassName || '',
  ].filter(Boolean).join(' ');
  const contextFields = Array.isArray(options.contextFields)
    ? options.contextFields
    : ['stock', 'mhd', 'location'];
  const contextRowFactories = {
    stock: () => renderContextRow('Bestand', stockLabel, { variant: 'stock' }),
    mhd: () => renderContextRow('MHD', bestBeforeDate, { variant: 'mhd' }),
    location: () => '',
  };
  const contextRows = contextFields
    .filter((field) => field !== 'location')
    .map((field) => contextRowFactories[field]?.() || '')
    .filter(Boolean)
    .join('');
  const stockBadgePlacement = options.stockBadgePlacement === 'aside' ? 'aside' : 'main';
  const stockBadgeConfig = options.stockBadge === false
    ? null
    : {
        label: 'Bestand',
        value: stockLabel,
        variant: 'stock',
        ...((typeof options.stockBadge === 'object' && options.stockBadge) || {}),
      };
  const stockBadge = stockBadgeConfig
    ? renderBadge(stockBadgeConfig.label, stockBadgeConfig.value, {
        variant: stockBadgeConfig.variant,
        className: stockBadgeConfig.className,
        element: stockBadgeConfig.element,
        dataset: stockBadgeConfig.dataset,
        hideLabel: stockBadgeConfig.hideLabel,
      })
    : '';
  const stockBadgeOrder = options.stockBadgeOrder === 'first' ? 'first' : 'last';
  const asideBadgeFactories = {
    amount: () => renderBadge('Menge', amountLabel, options.amountBadge || { variant: 'amount' }),
    mhd: () => renderBadge('MHD', bestBeforeDate, { variant: 'mhd', ...(options.mhdBadge || {}) }),
    stock: () => (stockBadgePlacement === 'aside' ? stockBadge : ''),
  };
  const configuredBadgeOrder = Array.isArray(options.badgeOrder)
    ? options.badgeOrder.filter((badge) => ['amount', 'mhd', 'stock'].includes(badge))
    : null;
  const defaultAsideBadgeOrder = stockBadgePlacement === 'aside' && stockBadgeOrder === 'first'
    ? ['stock', 'amount', 'mhd']
    : ['amount', 'mhd', 'stock'];
  const asideBadgeOrder = configuredBadgeOrder?.length ? configuredBadgeOrder : defaultAsideBadgeOrder;
  const badges = asideBadgeOrder
    .map((badge) => asideBadgeFactories[badge]?.() || '')
    .filter(Boolean)
    .join('');
  const statusChipMarkup = options.statusChip === false
    ? ''
    : `<span class="shopping-status-chip shopping-status-chip--shopping">${escapeHtml(options.statusLabel || 'Offen')}</span>`;
  const actionsMarkup = actionButtons.length
    ? `<div class="shopping-card__actions shopping-card__actions--stacked">${actionButtons.map((action) => renderActionButton(action)).join('')}</div>`
    : '';
  const badgesMarkup = `<div class="shopping-card__badges shopping-card__badges--stacked">${badges}</div>`;
  const infoMarkup = contextRows
    ? `<ul class="shopping-card__context-list shopping-card__context-list--stacked">${contextRows}</ul>`
    : '';
  const noteMarkup = note ? `<p class="shopping-card__note">${escapeHtml(note)}</p>` : '';
  const locationMarkup = locationLabel
    ? renderDetailLine('Lagerort', locationLabel, { variant: 'location' })
    : '';
  const mainBadgesMarkup = stockBadgePlacement === 'main'
    ? `<div class="shopping-card__badges shopping-card__badges--main">${stockBadge}</div>`
    : '';

  return `
    <div class="${rootClassName}">
      <div class="shopping-card__surface">
        <img class="shopping-card__media" src="${escapeHtml(imageSource.src)}" alt="${escapeHtml(title)}" loading="lazy" data-shopping-image="true" data-fallback-src="${escapeHtml(imageSource.fallbackSrc)}"${imageSource.authSrc ? ` data-auth-image-src="${escapeHtml(imageSource.authSrc)}"` : ''} />
        <div class="shopping-card__body shopping-card__body--swipe">
          <div class="shopping-card__main">
            <div class="shopping-card__header">
              <strong class="shopping-card__title">${escapeHtml(title)}</strong>
            </div>
            ${noteMarkup}
            ${mainBadgesMarkup}
            ${locationMarkup}
          </div>
          <div class="shopping-card__aside">
            ${statusChipMarkup}
            ${actionsMarkup}
            ${badgesMarkup}
            ${infoMarkup}
          </div>
        </div>
      </div>
    </div>
  `;
}
