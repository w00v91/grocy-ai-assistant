import { escapeHtml } from './shopping-ui.js';

function joinClassNames(...values) {
  return values.filter(Boolean).join(' ');
}

function buildDataAttributes(dataset = {}) {
  return Object.entries(dataset)
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .map(([key, value]) => `data-${key}="${escapeHtml(value)}"`)
    .join(' ');
}

function renderAction(action = {}) {
  const {
    label = '',
    className = 'ghost-button',
    href = '',
    dataset = {},
    disabled = false,
    ariaLabel = '',
  } = action;
  const attributes = buildDataAttributes(dataset);
  const disabledAttribute = disabled ? ' disabled' : '';
  const ariaLabelAttribute = ariaLabel ? ` aria-label="${escapeHtml(ariaLabel)}"` : '';
  const suffix = attributes ? ` ${attributes}` : '';

  if (href) {
    return `<a class="${escapeHtml(className)}" href="${escapeHtml(href)}"${ariaLabelAttribute}${suffix}>${escapeHtml(label)}</a>`;
  }

  return `<button type="button" class="${escapeHtml(className)}"${ariaLabelAttribute}${disabledAttribute}${suffix}>${escapeHtml(label)}</button>`;
}

export function renderActionRow(actions = [], options = {}) {
  if (!Array.isArray(actions) || !actions.length) return '';
  const className = joinClassNames('button-row', options.className);
  return `<div class="${className}">${actions.map((action) => renderAction(action)).join('')}</div>`;
}

export function renderMetaBadges(items = [], options = {}) {
  const entries = Array.isArray(items) ? items.filter((item) => String(item || '').trim()) : [];
  if (!entries.length) return '';
  const className = joinClassNames('migration-checklist', options.className);
  return `
    <div class="${className}">
      ${entries.map((item) => `<span class="migration-chip">${escapeHtml(item)}</span>`).join('')}
    </div>
  `;
}

export function renderSectionHeader({
  eyebrow = '',
  title = '',
  titleTag = 'h2',
  description = '',
  actions = [],
  className = '',
} = {}) {
  const resolvedTitleTag = ['h2', 'h3', 'h4'].includes(titleTag) ? titleTag : 'h2';
  return `
    <div class="${joinClassNames('section-header', className)}">
      <div class="section-header__copy">
        ${eyebrow ? `<p class="eyebrow">${escapeHtml(eyebrow)}</p>` : ''}
        <${resolvedTitleTag}>${escapeHtml(title)}</${resolvedTitleTag}>
        ${description ? `<p class="description">${escapeHtml(description)}</p>` : ''}
      </div>
      ${actions.length ? `<div class="section-header__actions">${actions.map((action) => renderAction(action)).join('')}</div>` : ''}
    </div>
  `;
}

export function renderCardContainer({
  className = '',
  eyebrow = '',
  title = '',
  titleTag = 'h2',
  description = '',
  actions = [],
  body = '',
  footer = '',
} = {}) {
  return `
    <section class="${joinClassNames('card', className)}">
      ${title ? renderSectionHeader({ eyebrow, title, titleTag, description, actions }) : ''}
      ${body}
      ${footer}
    </section>
  `;
}

export function renderStateCard({
  className = '',
  eyebrow = '',
  title = '',
  titleTag = 'h4',
  message = '',
  stateLabel = '',
  stateVariant = 'info',
  meta = [],
  actions = [],
} = {}) {
  return `
    <article class="${joinClassNames('shopping-card', 'panel-state-card', className)}">
      <div class="shopping-card__surface">
        <div class="shopping-card__body">
          <div class="shopping-card__header">
            <div>
              ${eyebrow ? `<p class="eyebrow">${escapeHtml(eyebrow)}</p>` : ''}
              <${titleTag}>${escapeHtml(title)}</${titleTag}>
            </div>
            ${stateLabel ? `<span class="shopping-status-chip shopping-status-chip--${escapeHtml(stateVariant)}">${escapeHtml(stateLabel)}</span>` : ''}
          </div>
          ${message ? `<p class="shopping-card__note">${escapeHtml(message)}</p>` : ''}
          ${renderMetaBadges(meta, { className: 'panel-meta-badges' })}
          ${renderActionRow(actions, { className: 'panel-action-row' })}
        </div>
      </div>
    </article>
  `;
}

export function renderTileGrid(items = [], options = {}) {
  const className = joinClassNames('variant-grid', options.className);
  const normalizedItems = Array.isArray(items) ? items : [];
  return `<div class="${className}">${normalizedItems.join('')}</div>`;
}

export function renderTwoColumnCardGroup(cards = [], options = {}) {
  const className = joinClassNames('panel-card-group', 'panel-card-group--two-column', options.className);
  const normalizedCards = Array.isArray(cards) ? cards : [];
  return `<section class="${className}">${normalizedCards.join('')}</section>`;
}
