import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const source = readFileSync('grocy_ai_assistant/api/static/dashboard.js', 'utf8');

test('legacy dashboard separates product creation from background image generation status', () => {
  assert.match(source, /Produkt wurde angelegt und zur Einkaufsliste hinzugefügt\./);
  assert.match(source, /Produktbild wird im Hintergrund erstellt\./);
  assert.match(source, /payload\.action === 'created_and_added'[\s\S]*?buildProductCreationSuccessMessage\(payload\)/);
});

test('legacy dashboard reports product creation duplicate clicks precisely', () => {
  assert.match(source, /status\.textContent = 'Produktanlage läuft noch\.'/);
  assert.doesNotMatch(source, /Produktsuche läuft bereits/);
});

test('legacy dashboard maps backend conflict reasons to understandable statuses', () => {
  assert.match(source, /response\.status === 409[\s\S]*?getBackendConflictMessage\(payload\)/);
  assert.match(source, /Aktive Produktanlage: Bitte kurz warten und dann erneut versuchen\./);
  assert.match(source, /Aktive Suche: Bitte kurz warten und dann erneut versuchen\./);
  assert.match(source, /Aktive Bildgenerierung: Bitte kurz warten und dann erneut versuchen\./);
});
