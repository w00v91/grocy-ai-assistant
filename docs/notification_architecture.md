# Notification System Architecture (Home Assistant + Grocy)

## 1) Architekturübersicht

Pipeline (entkoppelt):

1. **Domain Event** (`NotificationEvent`) entsteht in Shopping-/Grocy-Logik.
2. **Rule Engine** (`NotificationRuleEngine`) evaluiert aktivierte Regeln, Conditions, Quiet Hours und Cooldowns.
3. **Dispatcher** (`NotificationDispatcher`) übersetzt in HA-Service-Calls (`notify.mobile_app_*`, `persistent_notification.create`).
4. **History/Store** persistiert Konfiguration + Zustellhistorie in `.storage` über `NotificationStore`.

## 2) Dateikonzept / Projektlayout

```text
grocy_ai_assistant/custom_components/grocy_ai_assistant/
├── notify_models.py       # Domain-Modelle (Event, Rule, Target, Message, History)
├── notify_events.py       # Kanonische Eventtypen + Event-Factory
├── notify_rules.py        # Rule Engine (Bedingungen, Quiet Hours, Cooldown)
├── notify_dispatcher.py   # Zustellung in Home Assistant Notification-Services
├── notify_store.py        # Persistenz in .storage inkl. Versionierung
├── services.py            # Application Service / Orchestrator + HA-Services
└── services.yaml          # Beschreibungen der Notification-Services
```

## 3) Dashboard-Konzept (Web)

Aktuelle Routen/Views für das bestehende Webdashboard:

- `/api/dashboard/notifications/overview`
  - Lädt Geräte, Einstellungen, Regeln und Historie in einem kombinierten Payload.
- `/api/dashboard/notifications/devices/{device_id}`
  - Liste erkannter `notify.mobile_app_*`-Ziele.
  - Spalten: Name, Plattform, Aktiv, zugewiesener User.
- `/api/dashboard/notifications/settings`
  - Globales Enable/Disable, Standardkanal, Default-Severity, aktivierte Eventtypen.
- `/api/dashboard/notifications/rules`
  - CRUD für Regeln: Events, Targets, Channels, Cooldown, Quiet Hours, Template, Conditions.
- `/api/dashboard/notifications/tests/device`
- `/api/dashboard/notifications/tests/all`
- `/api/dashboard/notifications/tests/persistent`
  - Test an einzelnes Gerät, an alle Geräte oder als persistent notification.
- Historie ist aktuell Teil von `/api/dashboard/notifications/overview`.
  - Timestamp, Eventtyp, Regel-ID, Ziel, Kanal, Erfolg/Fehler.

## 4) Home-Assistant-Services

- `grocy_ai_assistant.notification_emit_event`
- `grocy_ai_assistant.notification_test_device`
- `grocy_ai_assistant.notification_test_all`
- `grocy_ai_assistant.notification_test_persistent`

## 5) Beispiel-Flow (Event bis Push)

1. Interne Shopping-Logik sendet `shopping_due` mit Payload (`open_items_count`, `click_url`, ...).
2. Rule Engine prüft:
   - Regel aktiv?
   - Event-Match?
   - Condition erfüllt? (z. B. `open_items_count > 5`)
   - Quiet Hours/Cooldown ok?
3. Für jedes Ziel wird `NotificationMessage` erzeugt.
4. Dispatcher sendet `notify.mobile_app_<device>` mit mobilen `data`-Feldern (`tag`, `group`, `url`, `clickAction`, `priority`).
5. Ergebnis landet als `NotificationHistoryEntry` in `.storage`.

## 6) Erweiterbarkeit

Das Grundgerüst ist auf folgende Erweiterungen vorbereitet:

- Actionable Notifications (Buttons) über zusätzliches `mobile_data.actions`.
- Snooze/Reminders als weiterer Dispatcher-Workflow.
- Digest-Modus über Batch-Builder vor Dispatcher.
- Weitere Kanäle (Telegram/Discord/E-Mail) über neue `NotificationChannel` + Dispatcher-Adapter.
- Benutzer-/Gerätepräferenzen über Ausbau von `NotificationPreference`/Target-Metadaten.

## 7) Integration in bestehende Grocy-/Shopping-App

- In bestehender Logik (z. B. Item-Add/Remove/Check) statt direkter Pushes nur noch `notification_emit_event` verwenden.
- Event-Payload standardisieren (`title`, `message`, `severity`, `click_url`, domänenspezifische Felder).
- Regelkonfiguration über UI in Store schreiben; Pipeline bleibt stabil.
