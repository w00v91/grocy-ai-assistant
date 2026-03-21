import test from 'node:test';
import assert from 'node:assert/strict';

import {
  bindShoppingImageFallbacks,
  formatAmount,
  formatBadgeValue,
  formatStockCount,
  renderShoppingListItemCard,
  renderShoppingVariantCard,
} from '../../grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/shopping-ui.js';

test('shopping UI helpers format amounts, badges and stock values consistently', () => {
  assert.equal(typeof bindShoppingImageFallbacks, 'function');
  assert.equal(formatAmount(''), '1');
  assert.equal(formatBadgeValue('', 'MHD wählen'), 'MHD wählen');
  assert.equal(formatStockCount('2,5'), '2,5');
});

test('shopping variant card renders shared dataset and context markup', () => {
  const markup = renderShoppingVariantCard({
    id: 7,
    name: 'Hafermilch Barista',
    source: 'ai',
    in_stock: '3',
    best_before_date: '2026-03-28',
  }, {
    amount: '2',
    actionName: 'shopping-select-variant',
  });

  assert.match(markup, /data-product-id="7"/);
  assert.match(markup, /Hafermilch Barista/);
  assert.match(markup, /KI-Vorschlag/);
  assert.match(markup, /data-shopping-image="true"/);
  assert.match(markup, /data-fallback-src="https:\/\/placehold\.co\/80x80\?text=Kein\+Bild"/);
  assert.match(markup, /Bestand/);
  assert.match(markup, /2026-03-28/);
});

test('shopping list card renders shared badge and action structure', () => {
  const markup = renderShoppingListItemCard({
    id: 9,
    product_name: 'Milch',
    amount: '4',
    note: 'laktosefrei',
    in_stock: '1',
    best_before_date: '2026-03-30',
    location_name: 'Kühlschrank',
  }, {
    actionButtons: [
      { label: 'Details', className: 'ghost-button', actionName: 'shopping-open-detail', dataset: { 'item-id': 9 } },
    ],
    amountBadge: { element: 'button', variant: 'amount', className: 'amount-increment-button', dataset: { 'shopping-list-id': 9 } },
    contextFields: ['location'],
  });

  assert.match(markup, /shopping-card--shopping-item/);
  assert.match(markup, /amount-increment-button/);
  assert.match(markup, /data-shopping-list-id="9"/);
  assert.match(markup, /data-action="shopping-open-detail"/);
  assert.match(markup, /data-shopping-image="true"/);
  assert.match(markup, /shopping-card__meta/);
  assert.match(markup, /shopping-card__badges--header/);
  assert.match(markup, /shopping-badge__label">Lagerort/);
  assert.match(markup, /Kühlschrank/);
  assert.match(markup, /shopping-badge__label">Bestand/);
  assert.doesNotMatch(markup, /shopping-card__context-label">Bestand/);
  assert.doesNotMatch(markup, /shopping-card__context-label">MHD/);
  assert.doesNotMatch(markup, /shopping-card__context-label">Lagerort/);
});
