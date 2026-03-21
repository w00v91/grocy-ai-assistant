export const VARIANT_SOURCE_LABELS = {
  grocy: 'Grocy',
  ai: 'KI-Vorschlag',
  input: 'Neu anlegen',
};

const DEFAULT_IMAGE_PLACEHOLDER = 'https://placehold.co/80x80?text=Kein+Bild';

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
  const resolvedImageSource = resolveShoppingImageSource(variant?.picture_url, { resolveUrl: options.resolveImageUrl });
  const dataset = {
    action: options.actionName || 'shopping-select-variant',
    'product-id': variant?.product_id ?? variant?.id ?? '',
    'product-name': variantName,
    'product-source': variantSource,
    amount: amountValue,
  };
  const ctaLabel = options.ctaLabel || 'Auswählen';
  const stockValue = formatStockCount(variant?.in_stock, '');
  const bestBeforeDate = formatBadgeValue(variant?.best_before_date, '');
  const noteValue = String(variant?.note || '').trim();

  return `
    <article class="shopping-card shopping-card--variant variant-card variant-card--action" role="listitem">
      <button class="shopping-card__button variant-card__button" type="button" ${buildDataAttributes(dataset)}>
        <div class="shopping-card__surface">
          <div class="shopping-card__media-wrap">
            <img class="shopping-card__media" src="${escapeHtml(resolvedImageSource)}" alt="${escapeHtml(variantName)}" loading="lazy" data-shopping-image="true" data-fallback-src="${escapeHtml(DEFAULT_IMAGE_PLACEHOLDER)}" />
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
            <div class="shopping-card__footer">
              <span class="shopping-card__cta variant-card__cta">${escapeHtml(ctaLabel)}</span>
            </div>
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
  const resolvedImageSource = resolveShoppingImageSource(item?.picture_url, { resolveUrl: options.resolveImageUrl });
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
  const stockBadgePlacement = options.stockBadgePlacement === 'main' ? 'main' : 'aside';
  const stockBadge = renderBadge('Bestand', stockLabel, { variant: 'stock' });
  const badges = [
    renderBadge('Menge', amountLabel, options.amountBadge || { variant: 'amount' }),
    renderBadge('MHD', bestBeforeDate, { variant: 'mhd', ...(options.mhdBadge || {}) }),
    stockBadgePlacement === 'aside' ? stockBadge : '',
  ].filter(Boolean).join('');
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
        <img class="shopping-card__media" src="${escapeHtml(resolvedImageSource)}" alt="${escapeHtml(title)}" loading="lazy" data-shopping-image="true" data-fallback-src="${escapeHtml(DEFAULT_IMAGE_PLACEHOLDER)}" />
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
