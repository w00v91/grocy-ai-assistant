import test from 'node:test';
import assert from 'node:assert/strict';

import {
  renderActionRow,
  renderCardContainer,
  renderMetaBadges,
  renderStateCard,
  renderTileGrid,
  renderTwoColumnCardGroup,
} from '../../grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/shared-panel-ui.js';

test('shared panel UI renders cards, groups and state tiles with existing card patterns', () => {
  const stateCard = renderStateCard({
    eyebrow: 'Rezepte',
    title: 'Kachel bleibt Kachel',
    message: 'Grid bleibt Grid.',
    stateLabel: 'Referenz aktiv',
    stateVariant: 'source',
    meta: ['card', 'variant-grid'],
    actions: [{ label: 'Legacy-Dashboard öffnen', className: 'primary-button', dataset: { action: 'open-legacy-dashboard' } }],
  });
  const group = renderTwoColumnCardGroup([
    renderCardContainer({
      className: 'hero-card',
      eyebrow: 'Rezepte',
      title: 'Rezeptvorschläge',
      body: renderTileGrid([stateCard]),
    }),
    renderCardContainer({
      className: 'card preview-card',
      eyebrow: 'Lager',
      title: 'Lager',
      titleTag: 'h3',
      body: renderMetaBadges(['section-header', 'shopping-card']) + renderActionRow([{ label: 'Öffnen', className: 'ghost-button' }]),
    }),
  ]);

  assert.match(stateCard, /shopping-card panel-state-card/);
  assert.match(stateCard, /shopping-status-chip shopping-status-chip--source/);
  assert.match(stateCard, /data-action="open-legacy-dashboard"/);
  assert.match(group, /panel-card-group panel-card-group--two-column/);
  assert.match(group, /variant-grid/);
  assert.match(group, /migration-chip/);
});
