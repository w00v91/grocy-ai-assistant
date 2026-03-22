import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dashboardPath = path.resolve(
  __dirname,
  '../../grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js',
);

test('storage edit modal renders legacy nutrition fields in legacy order', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');

  assert.match(source, /<div class="storage-edit-attributes">/);
  assert.match(source, /data-field="amount"[\s\S]*?data-field="bestBeforeDate"[\s\S]*?data-field="locationId"[\s\S]*?data-field="calories"[\s\S]*?data-field="carbs"[\s\S]*?data-field="fat"[\s\S]*?data-field="protein"[\s\S]*?data-field="sugar"/);
  assert.match(source, /Kalorien \(kcal\)[\s\S]*?id="storage-edit-calories-native"/);
  assert.match(source, /Kohlenhydrate \(g\)[\s\S]*?id="storage-edit-carbs-native"/);
  assert.match(source, /Fett \(g\)[\s\S]*?id="storage-edit-fat-native"/);
  assert.match(source, /Eiweiß \(g\)[\s\S]*?id="storage-edit-protein-native"/);
  assert.match(source, /Zucker \(g\)[\s\S]*?id="storage-edit-sugar-native"/);
});

test('storage initial state and close flow reset nutrition edit fields', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');

  assert.match(source, /editModal: \{[\s\S]*?calories: '',[\s\S]*?carbs: '',[\s\S]*?fat: '',[\s\S]*?protein: '',[\s\S]*?sugar: '',[\s\S]*?\}/);
  assert.match(source, /_closeStorageEdit\(\) \{[\s\S]*?calories: '',[\s\S]*?carbs: '',[\s\S]*?fat: '',[\s\S]*?protein: '',[\s\S]*?sugar: '',[\s\S]*?\}, \{ editing: false \}\);/);
});

test('storage edit open flow hydrates local nutrition first and then fetches product nutrition details', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');

  assert.match(source, /_openStorageEdit\(itemId\) \{[\s\S]*?calories: String\(item\.calories \|\| ''\)\.replace\(',', '\.'\),[\s\S]*?carbs: String\(item\.carbs \|\| ''\)\.replace\(',', '\.'\),[\s\S]*?fat: String\(item\.fat \|\| ''\)\.replace\(',', '\.'\),[\s\S]*?protein: String\(item\.protein \|\| ''\)\.replace\(',', '\.'\),[\s\S]*?sugar: String\(item\.sugar \|\| ''\)\.replace\(',', '\.'\),/);
  assert.match(source, /const \{ response, payload \} = await api\.fetchProductNutrition\(productId\);/);
  assert.match(source, /if \(!currentEditModal\.open \|\| Number\(currentEditModal\.itemId\) !== actionableItemId\) return;/);
  assert.match(source, /editModal: \{[\s\S]*?calories: String\(payload\.calories \|\| ''\)\.replace\(',', '\.'\),[\s\S]*?carbs: String\(payload\.carbs \|\| ''\)\.replace\(',', '\.'\),[\s\S]*?fat: String\(payload\.fat \|\| ''\)\.replace\(',', '\.'\),[\s\S]*?protein: String\(payload\.protein \|\| ''\)\.replace\(',', '\.'\),[\s\S]*?sugar: String\(payload\.sugar \|\| ''\)\.replace\(',', '\.'\),/);
});

test('storage edit state handling validates and saves nutrition values', async () => {
  const source = await fs.readFile(dashboardPath, 'utf8');

  assert.match(source, /function normalizeNutritionInputValue\(value\) \{/);
  assert.match(source, /const calories = normalizeNutritionInputValue\(editModal\.calories\);[\s\S]*?const carbs = normalizeNutritionInputValue\(editModal\.carbs\);[\s\S]*?const fat = normalizeNutritionInputValue\(editModal\.fat\);[\s\S]*?const protein = normalizeNutritionInputValue\(editModal\.protein\);[\s\S]*?const sugar = normalizeNutritionInputValue\(editModal\.sugar\);/);
  assert.match(source, /if \(\[calories, carbs, fat, protein, sugar\]\.some\(\(value\) => Number\.isNaN\(value\)\)\) \{[\s\S]*?Bitte gültige Nährwerte \(>= 0\) eingeben\./);
  assert.match(source, /await api\.updateStockProduct\(editModal\.itemId, \{[\s\S]*?calories,[\s\S]*?carbs,[\s\S]*?fat,[\s\S]*?protein,[\s\S]*?sugar,[\s\S]*?\}, \{/);
  assert.match(source, /if \(nextSignature === this\._renderSignature\) \{[\s\S]*?this\._syncVolatileState\(\);[\s\S]*?return;/);
});
