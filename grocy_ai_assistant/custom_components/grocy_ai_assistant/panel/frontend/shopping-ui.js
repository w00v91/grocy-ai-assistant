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
  const element = options.element === 'button' ? 'button' : 'span';
  const typeAttribute = element === 'button' ? ' type="button"' : '';
  const attributes = buildDataAttributes(options.dataset);
  const attributeSuffix = attributes ? ` ${attributes}` : '';
  return `
    <${element} class="shopping-badge${variantClassName}${extraClassName}"${typeAttribute}${attributeSuffix}>
      <span class="shopping-badge__label">${escapeHtml(label)}</span>
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
  const note = String(item?.note || '').trim() || (options.noteFallback || 'Keine Notiz');
  const stockLabel = formatStockCount(item?.in_stock, '0');
  const bestBeforeDate = formatBadgeValue(item?.best_before_date, options.mhdFallback || 'MHD wählen');
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
    location: () => (item?.location_name
      ? renderContextRow('Lagerort', item.location_name, { variant: 'location' })
      : ''),
  };
  const contextRows = contextFields
    .map((field) => contextRowFactories[field]?.() || '')
    .filter(Boolean)
    .join('');
  const badges = [
    renderBadge('Menge', amountLabel, options.amountBadge || { variant: 'amount' }),
    renderBadge('MHD', bestBeforeDate, options.mhdBadge || { variant: 'mhd' }),
    renderBadge('Bestand', stockLabel, { variant: 'stock' }),
  ].join('');
  const actionsMarkup = actionButtons.length
    ? `<div class="shopping-card__actions">${actionButtons.map((action) => renderActionButton(action)).join('')}</div>`
    : '';

  return `
    <div class="${rootClassName}">
      <div class="shopping-card__surface">
        <img class="shopping-card__media" src="${escapeHtml(resolvedImageSource)}" alt="${escapeHtml(title)}" loading="lazy" data-shopping-image="true" data-fallback-src="${escapeHtml(DEFAULT_IMAGE_PLACEHOLDER)}" />
        <div class="shopping-card__body">
          <div class="shopping-card__header">
            <strong class="shopping-card__title">${escapeHtml(title)}</strong>
            <span class="shopping-status-chip shopping-status-chip--shopping">Offen</span>
          </div>
          <p class="shopping-card__note">${escapeHtml(note)}</p>
          <div class="shopping-card__badges">${badges}</div>
          ${contextRows ? `<ul class="shopping-card__context-list">${contextRows}</ul>` : ''}
          ${actionsMarkup}
        </div>
      </div>
    </div>
  `;
}
