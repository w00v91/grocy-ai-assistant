# Notification Dashboard UI Spec

## Tabs

1. **Geräteverwaltung**
2. **Einstellungen**
3. **Regeln**
4. **Testcenter**
5. **Historie**

## API contract (current dashboard API)

- `GET /api/dashboard/notifications/overview`
- `PATCH /api/dashboard/notifications/devices/{id}`
- `PUT /api/dashboard/notifications/settings`
- `POST /api/dashboard/notifications/rules`
- `PATCH /api/dashboard/notifications/rules/{id}`
- `DELETE /api/dashboard/notifications/rules/{id}`
- `POST /api/dashboard/notifications/tests/device`
- `POST /api/dashboard/notifications/tests/all`
- `POST /api/dashboard/notifications/tests/persistent`
- `POST /api/v1/notifications/test` (Alias für persistenten Test-Trigger)

## UX notes

- Rule editor mit JSON-condition builder (Schlüssel, Operator, Wert).
- Quiet Hours als lokaler Time-Range-Picker.
- Vorschau-Template mit Beispielpayload.
- History mit Filter nach Eventtyp/Status/Kanal.
