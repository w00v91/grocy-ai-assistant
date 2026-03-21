# Legacy-UI → native Panel-Struktur: Mapping-Matrix

## Ausgangslage

- `MIGRATED_TABS` enthält aktuell nur `shopping`.
- `recipes`, `storage` und `notifications` werden im nativen Home-Assistant-Panel weiterhin über `GrocyAILegacyBridgeTab` als Legacy-`iframe` gerendert.
- Diese Matrix dient zugleich als Abnahmeliste, damit bei der Tab-Migration keine Funktion aus dem Legacy-Dashboard verloren geht.

## Migrationsstatus auf einen Blick

| Tab | Native Struktur heute | Status |
| --- | --- | --- |
| `shopping` | Echte native Web Components (`grocy-ai-shopping-tab`, `grocy-ai-dashboard-modals`, `grocy-ai-scanner-bridge`) | native übernommen |
| `recipes` | `GrocyAIRecipesTab extends GrocyAILegacyBridgeTab` mit Legacy-`iframe` | native fehlt |
| `storage` | `GrocyAIStorageTab extends GrocyAILegacyBridgeTab` mit Legacy-`iframe` | native fehlt |
| `notifications` | `GrocyAINotificationsTab extends GrocyAILegacyBridgeTab` mit Legacy-`iframe` | native fehlt |

---

## Tab `shopping`

| Aspekt | Legacy-UI | Native Panel-Struktur | Migrationsziel | Abnahme / darf nicht verloren gehen |
| --- | --- | --- | --- | --- |
| Sichtbare Karten / Abschnitte | Hero-Card **„Grocy AI Suche“** mit Suchfeld, Clear-Button, Scanner-Button und Variantenbereich; darunter Karte **„Einkaufsliste“** mit Liste, Statuszeile und Sammelaktionen. | Nahezu 1:1 als native Struktur in `grocy-ai-shopping-tab`: Hero-Card mit `grocy-ai-shopping-search-bar`, Scanner-Shortcut und eigene Listenkarte. | native übernommen | Native Ansicht muss Suchbereich, Variantenbereich, Listenkarte und Sammelaktionen vollständig ohne Legacy-`iframe` darstellen. |
| Primäre Aktionen | Produkt suchen, Varianten auswählen, Scanner öffnen, Liste aktualisieren, Eintrag +1, MHD setzen, Detailansicht öffnen, Eintrag kaufen, Eintrag löschen, Einkauf abschließen, Einkaufsliste leeren. | Alle Kernaktionen sind nativ an Events gebunden (`shopping-submit-query`, `shopping-select-variant`, `shopping-refresh`, `shopping-increment-item`, `shopping-open-mhd`, `shopping-open-detail`, `shopping-complete-item`, `shopping-delete-item`, `shopping-complete-all`, `shopping-clear-all`, `shopping-open-scanner`). | native übernommen | Jeder Legacy-Call-to-Action braucht im nativen Tab ein gleichwertiges Event/Control mit identischem Ergebnis auf der Einkaufsliste. |
| Modals / Dialoge | `shopping-item-modal` für Menge/Notiz/Bestandsinfos, `mhd-modal` für Haltbarkeitsdatum, `scanner-modal` für Kamera/Barcode/LLaVA. | `grocy-ai-dashboard-modals` rendert native Detail- und MHD-Modals; `grocy-ai-scanner-bridge` rendert den Scanner nativ als Web Component. | native übernommen | Detail-, MHD- und Scanner-Flow müssen ohne Legacy-HTML funktionieren; Modal-Öffnen/Schließen darf Polling nicht stören. |
| Polling / Refresh | `switchTab('shopping')` startet `refreshShoppingListInBackground()`. Zusätzlich läuft `startShoppingListAutoRefresh()` über Intervall; Refresh wird unterdrückt, wenn Tab nicht aktiv oder Dokument hidden ist. | `_switchTab('shopping')` startet `_startShoppingPolling()`; Intervall aktualisiert nur im Shopping-Tab und pausiert bei geöffnetem Detail-, MHD- oder Scanner-Modal. | native übernommen | Hintergrund-Refresh der Einkaufsliste muss im nativen Panel aktiv bleiben und bei offenen Modals/Scanner sauber pausieren. |
| API-Endpunkte | `/api/dashboard/shopping-list`, `/api/dashboard/search-variants`, `/api/dashboard/add-existing-product`, `/api/dashboard/search`, `/api/dashboard/shopping-list/item/{id}/amount/increment`, `/api/dashboard/shopping-list/item/{id}`, `/api/dashboard/shopping-list/item/{id}/complete`, `/api/dashboard/shopping-list/item/{id}/note`, `/api/dashboard/shopping-list/item/{id}/amount`, `/api/dashboard/shopping-list/item/{id}/best-before`, `/api/dashboard/shopping-list/item/{id}/best-before/reset`, `/api/dashboard/shopping-list/complete`, `/api/dashboard/shopping-list/clear`, Scanner zusätzlich `/api/dashboard/barcode/{barcode}`, `/api/dashboard/scanner/llava`, `/api/dashboard/scanner/create-product`. | Native Shopping nutzt nativ dieselben Shopping-Endpunkte für Suche/Liste/Mutationen; Scanner läuft nativ über `/api/v1/barcode/{barcode}` und `POST /api/v1/scan/image` statt über den Legacy-Scanner-Endpunkt. | native übernommen / braucht Shared-Komponente | Shopping-API darf nicht regressieren; Scanner-spezifische Logik sollte als Shared-Komponente stabil bleiben, damit Such-/Variantenfluss in Legacy und Native konsistent bleibt. |
| Leere / fehlerhafte / loading States | Statustexte wie „Lade Einkaufsliste...“, „Kein API-Key angegeben.“, Netzwerk-/Ingress-Fehler; Variantenbereich zeigt Ladezustand und „Keine Produktvarianten gefunden.“; Liste kann leer sein. | Native Search-Bar kennt Zustände `empty`, `typing`, `loading`, `suggestions`, `submitting`, `error`; Liste zeigt „Einkaufsliste wird geladen…“ bzw. „Keine Einträge.“; Statusmeldungen werden im Store gehalten. | native übernommen | Alle Legacy-Zustände müssen im nativen Panel sichtbar bleiben: Laden, leer, Fehler, Vorschläge sichtbar, Aktion läuft. |
| Shared UI / Komponentenbedarf | Shopping-Karten und Swipe-Verhalten sind bereits zwischen Legacy und Panel angenähert. | Native nutzt eigene Komponenten, aber mit Shared-Helfern wie `shopping-ui.js` und `bindSwipeInteractions(...)`. | braucht Shared-Komponente | Gemeinsame Karten-/Swipe-/Variantendarstellung sollte weiter zentralisiert bleiben, damit Shopping in Legacy und Native nicht auseinanderläuft. |
| HA-Entity / Service-Ersatz | Direkt im Tab nicht relevant; Interaktionen bleiben API-getrieben. | Keine direkte HA-Entity-Ersetzung im Shopping-Tab erkennbar. | native übernommen | Nicht in HA-Entities zerlegen, solange Listen-/Suchlogik transaktional über Dashboard-API laufen muss. |

### Abnahmeliste `shopping`

- [ ] Sucheingabe, Clear-Button und Variantenliste arbeiten nativ ohne `iframe`.
- [ ] Swipe/Tap auf Listeneinträgen deckt **Details öffnen**, **erledigen**, **löschen** und **+1/MHD** ab.
- [ ] Detail-Modal speichert **Menge** und **Notiz**.
- [ ] MHD-Modal kann **setzen** und **zurücksetzen**.
- [ ] Scanner funktioniert nativ inklusive Barcode- und Bildanalyse-Flow.
- [ ] Polling aktualisiert die Einkaufsliste weiter, pausiert aber bei offenen Shopping-Modals/Scanner.

---

## Tab `recipes`

| Aspekt | Legacy-UI | Native Panel-Struktur | Migrationsziel | Abnahme / darf nicht verloren gehen |
| --- | --- | --- | --- | --- |
| Sichtbare Karten / Abschnitte | Eine Rezept-Karte mit zwei Listen (**Gespeicherte Grocy-Rezepte**, **KI-Rezeptvorschläge**), Standortfilter, Produktliste pro Standort, Expiring-Filter, Statuszeile und Button **„Rezept hinzufügen“**. | Der Native Tab ist aktuell nur `GrocyAIRecipesTab extends GrocyAILegacyBridgeTab`: Headerkarte mit Migrationshinweis, Quicklink zum Legacy-Dashboard und eingebettetem `iframe`. | native fehlt | Die komplette Rezepterfahrung muss später als echte native Komponenten statt Bridge-Karte und `iframe` vorliegen. |
| Primäre Aktionen | `loadRecipeSuggestions()`, `loadExpiringRecipeSuggestions()`, Standortfilter ändern, Produktauswahl ändern, Rezeptdetails öffnen, fehlende Produkte zur Einkaufsliste hinzufügen, Rezept-anlegen-Modal öffnen. | Nativ gibt es derzeit nur die Aktion **„Legacy-Dashboard öffnen“**; alle Rezeptaktionen laufen innerhalb des Legacy-`iframe`. | native fehlt | Alle Legacy-Rezeptaktionen brauchen eine native Ereignis- und State-Struktur; nur ein „Open Legacy“-Button reicht als Endzustand nicht. |
| Modals / Dialoge | `recipe-modal` für Rezeptdetails mit Bild, Zutaten, Zubereitung und fehlenden Produkten; `recipe-create-modal` mit Methoden **WebScrape**, **KI**, **Manuell**. | Kein nativer Rezeptdialog vorhanden; Modals existieren ausschließlich im Legacy-`iframe`. | native fehlt | Rezeptdetails und Rezeptanlage müssen in native Dialoge/Web Components migriert werden. |
| Polling / Refresh | Kein Intervall-Polling; `switchTab('recipes')` initialisiert einmalig `loadLocations()`. Danach manuelle Refresh-/Ladevorgänge über Buttons und Filter. | Kein natives Polling und kein nativer Datenfluss; Bridge lädt nur das Legacy-Dashboard und ruft dort `switchTab('recipes')` im `iframe` auf. | braucht Shared-Komponente | Native Rezepte brauchen einen eigenen Store für Standort-/Produktauswahl, idealerweise als Shared-Tab-State-Muster analog Shopping. |
| API-Endpunkte | `/api/dashboard/locations`, `/api/dashboard/stock-products?location_ids=...`, `POST /api/dashboard/recipe-suggestions`, `POST /api/dashboard/recipe/{recipeId}/add-missing`. Die Anlage-Modal-Flows sind derzeit UI-seitig nur erfasste Entwürfe ohne echte Persistenz-API. | Kein nativer Rezept-API-Client im Panel vorhanden; der native Panel-API-Client deckt Rezepte aktuell nicht ab. | native fehlt | Vor der Migration muss ein nativer Recipe-Client mit denselben Endpunkten eingeführt werden; Erfassungsflows brauchen anschließend echte Persistenz. |
| Leere / fehlerhafte / loading States | Leere Listen: „Keine gespeicherten Grocy-Rezepte gefunden.“, „Keine KI-Rezepte erzeugt.“, „Keine Lagerstandorte gefunden.“, „Keine Produkte für die ausgewählten Lagerstandorte gefunden.“; Statusmeldungen für Laden/Fehler/Netzwerk. | Im nativen Panel existiert nur der generische Bridge-Zustand („Legacy-Fallback aktiv“), aber keine tab-spezifischen Rezept-States. | native fehlt | Alle Legacy-States müssen als native Skeleton-/Empty-/Error-/Status-States modelliert werden. |
| Shared UI / Komponentenbedarf | Rezeptlisten, Filterleiste, Detaildialog und Erfassungsdialog sind in Legacy eng miteinander gekoppelt. | Noch keine native Shared-Komponente vorhanden. | braucht Shared-Komponente | Sinnvoll wäre ein eigener Recipe-Tab-Baustein mit wiederverwendbaren Listen-, Filter- und Modal-Komponenten. |
| HA-Entity / Service-Ersatz | Teile der Vorschlagsanzeige könnten perspektivisch durch HA-Sensoren ergänzt werden, aber Filter, Detaildialog und „fehlende Produkte hinzufügen“ bleiben interaktiv. | Derzeit kein Ersatz vorhanden. | kann durch HA-Entity/Service ersetzt werden / braucht Shared-Komponente | Reine Übersichts-KPIs oder Top-Vorschläge können durch HA-Sensoren ergänzt werden; der eigentliche Rezept-Workflow braucht trotzdem natives UI. |

### Abnahmeliste `recipes`

- [ ] Zwei Rezeptlisten (**Grocy** und **KI**) sind nativ sichtbar.
- [ ] Standortfilter und Produktauswahl werden nativ geladen und geändert.
- [ ] `loadRecipeSuggestions()` und „bald ablaufende Produkte“ funktionieren nativ.
- [ ] Rezeptdetaildialog mit Bild, Zutaten, Zubereitung und fehlenden Produkten ist nativ vorhanden.
- [ ] „Alles hinzufügen“ überträgt fehlende Zutaten weiter an die Einkaufsliste.
- [ ] Rezept-anlegen-Dialog deckt WebScrape-, KI- und manuelle Erfassung ab.
- [ ] Alle leeren/fehlerhaften/loading States aus Legacy sind nativ sichtbar.

---

## Tab `storage`

| Aspekt | Legacy-UI | Native Panel-Struktur | Migrationsziel | Abnahme / darf nicht verloren gehen |
| --- | --- | --- | --- | --- |
| Sichtbare Karten / Abschnitte | Lagerkarte mit **Aktualisieren**, Textfilter, Toggle **„Alle Produkte anzeigen“**, Statuszeile und Produktliste als Karten/Grid. | Aktuell nur `GrocyAIStorageTab extends GrocyAILegacyBridgeTab` mit Bridge-Karte und Legacy-`iframe`. | native fehlt | Lagerliste muss als echter nativer Tab mit Filterleiste, Status und Kartenliste übernommen werden. |
| Primäre Aktionen | `loadStorageProducts()`, Filter ändern, Toggle ändern, Swipe/Tap auf Produkt, **Bearbeiten**, **Verbrauchen**, **Speichern**, **Produktbild löschen**, **Produkt löschen**. | Nativ nur **„Legacy-Dashboard öffnen“**; alle Lageraktionen laufen im `iframe`. | native fehlt | Bearbeiten, Verbrauchen und Filtern brauchen native UI-Ereignisse statt Bridge. |
| Modals / Dialoge | `storage-edit-modal` mit Produktbild, Menge, MHD, Lagerort, Nährwerten, Speichern/Löschen/Abbrechen. | Kein nativer Storage-Dialog vorhanden. | native fehlt | Das Bearbeitungsmodal samt Bild-/Nährwertfeldern muss nativ nachgebaut werden. |
| Polling / Refresh | `switchTab('storage')` triggert `refreshStorageInBackground()`; zusätzlich `startStorageAutoRefresh()` via Intervall, nur wenn Tab aktiv und Dokument sichtbar. | Kein natives Storage-Polling; nur Legacy-`iframe` mit dessen eigenem Verhalten nach `switchTab('storage')`. | braucht Shared-Komponente | Native Storage braucht denselben Polling-/Debounce-/Cache-Mechanismus wie Legacy, idealerweise in einem Shared-Store-Muster. |
| API-Endpunkte | `GET /api/dashboard/stock-products` (inkl. `include_all_products`, `q`, `location_ids`), `POST /api/dashboard/stock-products/{id}/consume`, `GET /api/dashboard/products/{productId}/nutrition`, `PUT /api/dashboard/stock-products/{id}`, `DELETE /api/dashboard/products/{productId}/picture`, `DELETE /api/dashboard/stock-products/{id}`. | Kein nativer Storage-API-Client vorhanden. | native fehlt | Für die Migration wird ein nativer Storage-Client mit denselben CRUD-Endpunkten benötigt. |
| Leere / fehlerhafte / loading States | „Lade Lagerbestand...“, „Lade Lagerbestand und alle Produkte...“, „Keine Produkte gefunden.“, API-Key-/Fehler-/Netzwerkmeldungen; Status nennt Spezialfälle wie Einträge ohne nutzbare IDs oder nicht auf Lager. | Kein nativer tab-spezifischer Storage-State; nur generische Bridge-Karte. | native fehlt | Empty-, Loading-, Error- und Spezialstatus müssen 1:1 nativ modelliert werden. |
| Shared UI / Komponentenbedarf | Storage-Liste nutzt kartige Produktdarstellung und Swipe-Interaktionen, die visuell nah an Shopping liegen. | Noch keine native Storage-Komponente vorhanden. | braucht Shared-Komponente | Produktkarten, Swipe-Handling und Bild-/Badge-Rendering sollten mit Shopping teilbar sein, statt doppelt implementiert zu werden. |
| HA-Entity / Service-Ersatz | Reine Summen oder Warnungen könnten über HA-Sensoren/Buttons erscheinen; das Bearbeitungsmodal bleibt UI-intensiv. | Kein Ersatz vorhanden. | kann durch HA-Entity/Service ersetzt werden / braucht Shared-Komponente | Bestandszähler/„bald ablaufend“-KPIs können als HA-Entity gespiegelt werden; interaktives Editieren bleibt ein nativer Tab-Use-Case. |

### Abnahmeliste `storage`

- [ ] Lagerliste ist nativ mit Refresh, Filter und „Alle Produkte anzeigen“-Toggle verfügbar.
- [ ] Swipe/Tap kann **Bearbeiten** und **Verbrauchen** ohne Legacy-`iframe` auslösen.
- [ ] Storage-Edit-Modal zeigt Bild, Menge, MHD, Lagerort und Nährwerte.
- [ ] Speichern, Produktbild löschen und Produkt löschen funktionieren nativ.
- [ ] Hintergrund-Refresh/Polling verhält sich wie im Legacy-Tab.
- [ ] Alle leeren/fehlerhaften/loading States aus Legacy sind nativ sichtbar.

---

## Tab `notifications`

| Aspekt | Legacy-UI | Native Panel-Struktur | Migrationsziel | Abnahme / darf nicht verloren gehen |
| --- | --- | --- | --- | --- |
| Sichtbare Karten / Abschnitte | Statuszeile plus Karten für **Geräteverwaltung**, **Benachrichtigungsregeln**, **Testcenter** und **Historie**. | Aktuell nur `GrocyAINotificationsTab extends GrocyAILegacyBridgeTab` mit Bridge-Karte und Legacy-`iframe`. | native fehlt | Notification-Übersicht muss als nativer Tab mit denselben vier Abschnitten umgesetzt werden. |
| Primäre Aktionen | `loadNotificationOverview()`, Gerät aktiv/inaktiv schalten, Regel erstellen/bearbeiten/löschen, Test an alle Geräte, Persistent-Test. | Nativ nur **„Legacy-Dashboard öffnen“**; jede fachliche Aktion lebt weiter im Legacy-`iframe`. | native fehlt | Geräte-, Regel- und Testflows brauchen native Controls und State-Verwaltung. |
| Modals / Dialoge | `notification-rule-modal` für neue/bearbeitete Regel mit Event-, Geräte-, Prioritäts-, Kanal-, Cooldown- und Template-Feldern. | Kein nativer Notification-Dialog vorhanden. | native fehlt | Regel-Editor muss als nativer Dialog migriert werden. |
| Polling / Refresh | Kein Intervall-Polling; beim Tabwechsel ruft `switchTab('notifications')` direkt `loadNotificationOverview()` auf. Weitere Refreshes sind manuell oder nach Mutationen. | Kein nativer Notification-State; Bridge ruft im geladenen `iframe` `switchTab('notifications')` auf. | braucht Shared-Komponente | Ein nativer Notification-Store sollte Overview-Reloads nach Mutationen zentral abbilden. |
| API-Endpunkte | `GET /api/dashboard/notifications/overview`, `PATCH /api/dashboard/notifications/devices/{deviceId}`, `POST/PATCH /api/dashboard/notifications/rules`, `DELETE /api/dashboard/notifications/rules/{ruleId}`, `POST /api/dashboard/notifications/tests/all`, `POST /api/dashboard/notifications/tests/persistent`. | Kein nativer Notification-API-Client vorhanden. | native fehlt | Für die Migration wird ein eigener nativer Notifications-Client benötigt. |
| Leere / fehlerhafte / loading States | „Lade Notification-Konfiguration…“, Fehlerstatus; leere Zustände: „Keine mobilen Notify-Targets gefunden.“, „Keine Regeln vorhanden.“, „Keine Einträge.“ | Keine nativen Notification-spezifischen States; nur generischer Bridge-Fallback. | native fehlt | Overview-Laden, leere Listen und Fehler müssen nativ sichtbar werden. |
| Shared UI / Komponentenbedarf | Listen für Geräte, Regeln und Historie plus Regelmodal teilen sich Status- und Auswahlmuster. | Noch keine native Notification-Komponente vorhanden. | braucht Shared-Komponente | Listen-/Form-Komponenten und Status-Handling sollten als wiederverwendbare Notification-Bausteine entstehen. |
| HA-Entity / Service-Ersatz | Test-Benachrichtigungen und globale Statusanzeige könnten teils über HA-Services/Buttons abgebildet werden; Regelverwaltung bleibt ein UI-Workflow. | Kein Ersatz vorhanden. | kann durch HA-Entity/Service ersetzt werden / braucht Shared-Komponente | Einzelne Testaktionen lassen sich durch HA-Services ergänzen, aber Geräte-/Regelverwaltung braucht weiterhin natives UI. |

### Abnahmeliste `notifications`

- [ ] Geräteverwaltung ist nativ sichtbar und Geräte lassen sich aktiv/inaktiv schalten.
- [ ] Regel-Liste ist nativ sichtbar; Regeln lassen sich anlegen, bearbeiten und löschen.
- [ ] Testcenter unterstützt **Test an alle Geräte** und **Persistent-Test** nativ.
- [ ] Historie ist nativ sichtbar.
- [ ] Regel-Modal ist nativ vorhanden.
- [ ] `loadNotificationOverview()`-Status sowie leere/fehlerhafte/loading States sind nativ abgebildet.

---

## Übergreifende Abnahmeregel für die Migration

Ein Tab gilt erst dann als vollständig migriert, wenn alle Punkte seiner Abnahmeliste ohne Legacy-`iframe` erfüllt sind. Solange ein Tab nur über `GrocyAILegacyBridgeTab` läuft, bleibt sein Status **„native fehlt“**, selbst wenn Navigation, Header oder Quicklinks bereits im nativen Panel sichtbar sind.
