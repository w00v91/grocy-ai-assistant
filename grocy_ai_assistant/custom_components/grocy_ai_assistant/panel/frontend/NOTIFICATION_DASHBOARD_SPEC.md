# Notification Dashboard UI Spec

## Tabs

1. **Geräteverwaltung**
2. **Einstellungen**
3. **Regeln**
4. **Testcenter**
5. **Historie**

## API contract (v1 suggestion)

- `GET /api/grocy_ai_assistant/notifications/devices`
- `PATCH /api/grocy_ai_assistant/notifications/devices/{id}`
- `GET /api/grocy_ai_assistant/notifications/settings`
- `PUT /api/grocy_ai_assistant/notifications/settings`
- `GET /api/grocy_ai_assistant/notifications/rules`
- `POST /api/grocy_ai_assistant/notifications/rules`
- `PATCH /api/grocy_ai_assistant/notifications/rules/{id}`
- `DELETE /api/grocy_ai_assistant/notifications/rules/{id}`
- `POST /api/grocy_ai_assistant/notifications/tests/device`
- `POST /api/grocy_ai_assistant/notifications/tests/all`
- `POST /api/grocy_ai_assistant/notifications/tests/persistent`
- `GET /api/grocy_ai_assistant/notifications/history?limit=100`

## UX notes

- Rule editor mit JSON-condition builder (Schlüssel, Operator, Wert).
- Quiet Hours als lokaler Time-Range-Picker.
- Vorschau-Template mit Beispielpayload.
- History mit Filter nach Eventtyp/Status/Kanal.
