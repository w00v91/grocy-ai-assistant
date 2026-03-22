# Legacy-UI → native Panel-Struktur: Mapping-Matrix

## Ausgangslage

- `MIGRATED_TABS` enthält aktuell `shopping`, `recipes` und `storage`.
- Nur `notifications` wird im nativen Home-Assistant-Panel weiterhin über `GrocyAILegacyBridgeTab` als Legacy-`iframe` gerendert.
- Diese Matrix dient zugleich als Abnahmeliste, damit bei der Tab-Migration keine Funktion aus dem Legacy-Dashboard verloren geht.

## Migrationsstatus auf einen Blick

| Tab | Native Struktur heute | Status |
| --- | --- | --- |
| `shopping` | Echte native Web Components (`grocy-ai-shopping-tab`, `grocy-ai-dashboard-modals`, `grocy-ai-scanner-bridge`) | native übernommen |
| `recipes` | Eigenständige native Web Component `GrocyAIRecipesTab` | native übernommen |
| `storage` | Eigenständige native Web Component `GrocyAIStorageTab` | native übernommen |
| `notifications` | `GrocyAINotificationsTab extends GrocyAILegacyBridgeTab` mit Legacy-`iframe` | native fehlt |

---


## Visuelle Abnahme: „ähnlicher Stil bei gleicher Funktion“

Die Legacy-Struktur in `grocy_ai_assistant/api/templates/dashboard.html` ist für die Migration **explizit die visuelle Referenz** – nicht nur Datenquelle oder API-Auslöser. Abnahmen erfolgen daher immer gegen die dortige DOM-Struktur, Kartenhierarchie und Interaktionsform der jeweiligen Tabs.

### Verbindliche visuelle Paritätsregeln pro Tab

| Regel | Legacy-Referenz in `dashboard.html` | Abnahmekriterium für native Tabs |
| --- | --- | --- |
| Kachel bleibt Kachel | `hero-card`, Shopping-/Storage-/Notification-Karten | Inhalte, die im Legacy als Card/Suface gruppiert sind, bleiben auch nativ klar als eigene Card mit sichtbarer Begrenzung, Innenabstand und eigenem Schwerpunkt erkennbar. |
| Grid bleibt Grid | `variant-grid`, `notification-grid` | Listen mit mehreren gleichrangigen Elementen bleiben nativ als Grid/Kachelfläche organisiert und dürfen nicht in eine rein textuelle Liste oder Accordion-Struktur umkippen. |
| Zwei Spalten bleiben zwei Spalten | `recipe-columns` | Zweispaltige Bereiche bleiben ab tablet-/desktop-tauglichem Viewport zweispaltig; nur bei echtem Platzmangel darf responsiv auf eine Spalte reduziert werden. |
| Floating/Modal bleibt Modal/Overlay | `shopping-modal`, `recipe-modal`, `storage-edit-modal`, `notification-rule-modal`, `scanner-modal` | Dialoge mit Fokus, Backdrop und temporärer Entscheidung bleiben nativ als Overlay/Modal umgesetzt; kein Inline-Ersatz, wenn der Legacy-Flow bewusst modal ist. |
| Primäre CTA bleibt prominent | `hero-card` mit Such-CTA, `Rezept hinzufügen`, Refresh-/Test-/Speicher-Aktionen | Die wichtigste Primäraktion eines Tabs bleibt nativ visuell hervorgehoben und nicht hinter Sekundäraktionen, Menüs oder unauffälligen Textlinks versteckt. |

### Referenz-Selektoren aus `dashboard.html`

Die folgenden Legacy-Bausteine dienen bei Reviews als konkrete Vergleichspunkte:

- `hero-card`: visueller Einstieg, Priorisierung der Primäraktion, Above-the-fold-Gewichtung.
- `variant-grid`: gleichrangige Auswahlkacheln, besonders für Shopping-Suche und Storage-Karten.
- `recipe-columns`: parallele Rezeptlisten mit vergleichbarem visuellem Gewicht.
- `notification-grid`: mehrere gleichwertige Status-/Gerätekacheln im selben Raster.
- `shopping-modal`: Overlay-Muster für fokussierte Bearbeitungs- und Bestätigungsflows.

### Abnahmeentscheidung für visuelle Parität

Ein Tab erfüllt „ähnlicher Stil bei gleicher Funktion“ nur dann, wenn **alle** folgenden Aussagen mit **Ja** beantwortet werden:

1. Gleiche Funktion ist im nativen Tab ohne Legacy-`iframe` erreichbar.
2. Gleiche Interaktionsform bleibt erhalten (Kachel/Grid/Modal/zweispaltige Gruppe statt völlig anderem UI-Muster).
3. Gleicher visueller Schwerpunkt bleibt erhalten (Hero bleibt Hero, Primär-CTA bleibt Primär-CTA).
4. Abweichungen sind tab-lokal dokumentiert und bieten einen klaren Home-Assistant-Mehrwert.

Zulässige Abweichungen sind nur begründet durch:

- bessere Responsiveness,
- bessere Accessibility,
- bessere Touch-Bedienung.

Nicht zulässig sind Abweichungen, die nur aus Implementierungsbequemlichkeit entstehen oder die Legacy-Hierarchie ohne nachweisbaren Mehrwert abschwächen.

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

### Vergleichsliste `shopping`

| Legacy-Komponente | Native Entsprechung | gleiche Funktion? | gleiche Interaktionsform? | ähnlicher visueller Schwerpunkt? |
| --- | --- | --- | --- | --- |
| `hero-card` mit Suche, Clear, Scanner und Variantenbereich | `grocy-ai-shopping-tab` mit `grocy-ai-shopping-search-bar`, Scanner-Shortcut und Variantenergebnissen | Ja | Ja – Hero bleibt Hero, `variant-grid` bleibt Grid | Ja |
| Einkaufslisten-Karte mit Statuszeile und Sammelaktionen | native Shopping-Listenkarte mit Aktionen/Status im Panel | Ja | Ja – Kachel bleibt Kachel | Ja |
| `shopping-item-modal` und `mhd-modal` | `grocy-ai-dashboard-modals` | Ja | Ja – `shopping-modal` bleibt Overlay/Modal | Ja |
| `scanner-modal` | `grocy-ai-scanner-bridge` | Ja | Ja – Scanner bleibt fokussiertes Overlay | Ja |

**Tab-lokale Abweichungen mit HA-Mehrwert**

- Scanner nutzt nativ eine eigene Web-Component statt Legacy-Markup. Das ist zulässig, weil dadurch Touch-/Kamera-Integration, Fokussteuerung und Responsiveness im Home-Assistant-Panel robuster werden.
- Shopping darf HA-spezifische Status-/Busy-Synchronisation ergänzen, solange `hero-card`, `variant-grid` und `shopping-modal` als visuelle Muster erkennbar bleiben.

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
| Sichtbare Karten / Abschnitte | Eine Rezept-Karte mit zwei Listen (**Gespeicherte Grocy-Rezepte**, **KI-Rezeptvorschläge**), Standortfilter, Produktliste pro Standort, Expiring-Filter, Statuszeile und Button **„Rezept hinzufügen“**. | Der Rezepte-Tab wird inzwischen über die native Web Component `GrocyAIRecipesTab` gerendert. | native übernommen / Parität weiter ausbauen | Die bestehende native Rezepterfahrung muss die verbleibende visuelle und funktionale Parität zur Legacy-Ansicht weiter absichern. |
| Primäre Aktionen | `loadRecipeSuggestions()`, `loadExpiringRecipeSuggestions()`, Standortfilter ändern, Produktauswahl ändern, Rezeptdetails öffnen, fehlende Produkte zur Einkaufsliste hinzufügen, Rezept-anlegen-Modal öffnen. | Primäre Rezeptaktionen laufen nativ über eigene Events und State im Rezepte-Tab. | native übernommen / Parität weiter ausbauen | Alle Legacy-Rezeptaktionen sollen im nativen Tab ohne Fallback gleichwertig abgebildet bleiben. |
| Modals / Dialoge | `recipe-modal` für Rezeptdetails mit Bild, Zutaten, Zubereitung und fehlenden Produkten; `recipe-create-modal` mit Methoden **WebScrape**, **KI**, **Manuell**. | Rezeptdialoge werden nativ gerendert; offene Paritätspunkte sollten gegen die Legacy-Referenz geprüft werden. | native übernommen / Parität weiter ausbauen | Rezeptdetails und Rezeptanlage müssen im nativen UI vollständig auf Legacy-Niveau bleiben. |
| Polling / Refresh | Kein Intervall-Polling; `switchTab('recipes')` initialisiert einmalig `loadLocations()`. Danach manuelle Refresh-/Ladevorgänge über Buttons und Filter. | Der native Rezepte-Tab verwaltet seinen Datenfluss selbst. | native übernommen / braucht Shared-Komponente | Rezept-States sollten weiterhin als klarer nativer Store/Flow dokumentiert und getestet werden. |
| API-Endpunkte | `/api/dashboard/locations`, `/api/dashboard/stock-products?location_ids=...`, `POST /api/dashboard/recipe-suggestions`, `POST /api/dashboard/recipe/{recipeId}/add-missing`. Die Anlage-Modal-Flows sind derzeit UI-seitig nur erfasste Entwürfe ohne echte Persistenz-API. | Der native Rezepte-Tab spricht die Dashboard-API direkt an. | native übernommen | Änderungen an den Rezept-Endpunkten müssen die native Panel-Implementierung und ihre Regressionstests mitziehen. |
| Leere / fehlerhafte / loading States | Leere Listen: „Keine gespeicherten Grocy-Rezepte gefunden.“, „Keine KI-Rezepte erzeugt.“, „Keine Lagerstandorte gefunden.“, „Keine Produkte für die ausgewählten Lagerstandorte gefunden.“; Statusmeldungen für Laden/Fehler/Netzwerk. | Der native Rezepte-Tab besitzt eigene Status- und Listen-Zustände. | native übernommen / Parität weiter ausbauen | Alle Legacy-States müssen im nativen Rezepte-Tab weiterhin explizit sichtbar und testbar bleiben. |
| Shared UI / Komponentenbedarf | Rezeptlisten, Filterleiste, Detaildialog und Erfassungsdialog sind in Legacy eng miteinander gekoppelt. | Noch keine native Shared-Komponente vorhanden. | braucht Shared-Komponente | Sinnvoll wäre ein eigener Recipe-Tab-Baustein mit wiederverwendbaren Listen-, Filter- und Modal-Komponenten. |
| HA-Entity / Service-Ersatz | Teile der Vorschlagsanzeige könnten perspektivisch durch HA-Sensoren ergänzt werden, aber Filter, Detaildialog und „fehlende Produkte hinzufügen“ bleiben interaktiv. | Derzeit kein Ersatz vorhanden. | kann durch HA-Entity/Service ersetzt werden / braucht Shared-Komponente | Reine Übersichts-KPIs oder Top-Vorschläge können durch HA-Sensoren ergänzt werden; der eigentliche Rezept-Workflow braucht trotzdem natives UI. |

### Vergleichsliste `recipes`

| Legacy-Komponente | Native Entsprechung | gleiche Funktion? | gleiche Interaktionsform? | ähnlicher visueller Schwerpunkt? |
| --- | --- | --- | --- | --- |
| Rezept-Card mit Filterleiste und CTA | native Rezepte-Karte im Panel | Ja | Ja – Kachel bleibt Kachel | Ja |
| `recipe-columns` mit zwei Listen | native Rezeptrenderer mit responsiver Spalten-/Stack-Logik | Ja | Ja – zwei Listen bleiben als gleichwertige Bereiche erhalten | Ja |
| `recipe-modal` für Details | natives Rezeptdetail-Modal | Ja | Ja – Modal bleibt Modal | Ja |
| `recipe-create-modal` für WebScrape/KI/Manuell | natives Rezept-Erfassungsmodal | Ja | Ja – Modal bleibt Modal | Ja |

**Tab-lokale Abweichungen mit HA-Mehrwert**

- Zulässig ist nur eine responsive Reduktion von `recipe-columns` auf eine Spalte bei engem Viewport. Auf größeren Viewports muss die Zweispalten-Logik erhalten bleiben.
- Wenn Rezeptfilter nativ zugänglicher umgesetzt werden, muss der visuelle Schwerpunkt trotzdem auf der Haupt-Rezeptkarte mit prominenter Aktion **„Rezept hinzufügen“** bleiben.

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
| Sichtbare Karten / Abschnitte | Lagerkarte mit **Aktualisieren**, Textfilter, Toggle **„Alle Produkte anzeigen“**, Statuszeile und Produktliste als Karten/Grid. | Der Lager-Tab wird inzwischen über die native Web Component `GrocyAIStorageTab` gerendert. | native übernommen / Parität weiter ausbauen | Die native Lageransicht muss die Legacy-Funktionalität und -Struktur dauerhaft abdecken. |
| Primäre Aktionen | `loadStorageProducts()`, Filter ändern, Toggle ändern, Swipe/Tap auf Produkt, **Bearbeiten**, **Verbrauchen**, **Speichern**, **Produktbild löschen**, **Produkt löschen**. | Lageraktionen laufen nativ über die Storage-Komponente, Shared-Cards und Modals. | native übernommen / Parität weiter ausbauen | Bearbeiten, Verbrauchen und Filtern müssen im nativen Tab regressionssicher bleiben. |
| Modals / Dialoge | `storage-edit-modal` mit Produktbild, Menge, MHD, Lagerort, Nährwerten, Speichern/Löschen/Abbrechen. | Storage-Dialoge werden nativ gerendert. | native übernommen / Parität weiter ausbauen | Das Bearbeitungsmodal samt Bild-/Nährwertfeldern muss im nativen UI auf Legacy-Niveau bleiben. |
| Polling / Refresh | `switchTab('storage')` triggert `refreshStorageInBackground()`; zusätzlich `startStorageAutoRefresh()` via Intervall, nur wenn Tab aktiv und Dokument sichtbar. | Der native Storage-Tab verwaltet Polling und Refresh selbst. | native übernommen / braucht Shared-Komponente | Das Polling-Verhalten sollte weiter gegen Legacy-Regressionen abgesichert werden. |
| API-Endpunkte | `GET /api/dashboard/stock-products` (inkl. `include_all_products`, `q`, `location_ids`), `POST /api/dashboard/stock-products/{id}/consume`, `GET /api/dashboard/products/{productId}/nutrition`, `PUT /api/dashboard/stock-products/{id}`, `DELETE /api/dashboard/products/{productId}/picture`, `DELETE /api/dashboard/stock-products/{id}`. | Der native Storage-Tab nutzt die Dashboard-API direkt. | native übernommen | Änderungen an Storage-Endpunkten müssen die native Implementierung und ihre Tests mitziehen. |
| Leere / fehlerhafte / loading States | „Lade Lagerbestand...“, „Lade Lagerbestand und alle Produkte...“, „Keine Produkte gefunden.“, API-Key-/Fehler-/Netzwerkmeldungen; Status nennt Spezialfälle wie Einträge ohne nutzbare IDs oder nicht auf Lager. | Der native Storage-Tab besitzt eigene Status- und Listen-Zustände. | native übernommen / Parität weiter ausbauen | Empty-, Loading-, Error- und Spezialstatus müssen im nativen Storage-Tab weiterhin explizit sichtbar und getestet bleiben. |
| Shared UI / Komponentenbedarf | Storage-Liste nutzt kartige Produktdarstellung und Swipe-Interaktionen, die visuell nah an Shopping liegen. | Native Storage nutzt bereits Shared-UI-Bausteine mit Shopping-Nähe. | native übernommen / braucht Shared-Komponente | Produktkarten, Swipe-Handling und Bild-/Badge-Rendering sollen weiter zentralisiert bleiben, statt erneut auseinanderzulaufen. |
| HA-Entity / Service-Ersatz | Reine Summen oder Warnungen könnten über HA-Sensoren/Buttons erscheinen; das Bearbeitungsmodal bleibt UI-intensiv. | Kein Ersatz vorhanden. | kann durch HA-Entity/Service ersetzt werden / braucht Shared-Komponente | Bestandszähler/„bald ablaufend“-KPIs können als HA-Entity gespiegelt werden; interaktives Editieren bleibt ein nativer Tab-Use-Case. |

### Vergleichsliste `storage`

| Legacy-Komponente | Native Entsprechung | gleiche Funktion? | gleiche Interaktionsform? | ähnlicher visueller Schwerpunkt? |
| --- | --- | --- | --- | --- |
| Storage-`hero-card` mit Refresh, Filter und Toggle | nativer Storage-Header / Filterkarte im Panel | Ja | Ja – Hero/Karte bleibt Hero/Karte | Ja |
| Produktliste als `variant-grid` | native Storage-Karten im Grid | Ja | Ja – Grid bleibt Grid | Ja |
| `storage-edit-modal` | native Storage-Edit-/Consume-/Delete-Modals | Ja | Ja – `shopping-modal`-Muster bleibt Overlay | Ja |
| Quick Actions auf Produktkarten | native Quick Actions und Modal-Trigger | Ja | Ja – Kachelinteraktion bleibt kachelzentriert | Ja |

**Tab-lokale Abweichungen mit HA-Mehrwert**

- Zulässig sind größere Touch-Ziele, klarere Fokuszustände und responsivere Umbrüche innerhalb des `variant-grid`, solange die kachelbasierte Produktdarstellung nicht zu einer textlastigen Tabellen-/Listenansicht degradiert.
- Zusätzliche HA-Statuschips sind erlaubt, wenn sie die Primäraktionen **Bearbeiten**/**Verbrauchen** nicht visuell verdrängen.

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

### Vergleichsliste `notifications`

| Legacy-Komponente | Native Entsprechung | gleiche Funktion? | gleiche Interaktionsform? | ähnlicher visueller Schwerpunkt? |
| --- | --- | --- | --- | --- |
| Überblicks-Card mit Statuszeile | aktuell Bridge-Card + Legacy-`iframe` | Nein – noch nicht nativ | Teilweise – Kachel sichtbar, aber keine native Fachinteraktion | Teilweise |
| Geräte-/Regel-/Test-/Historie-Bereiche als `notification-grid` bzw. Kartenblöcke | aktuell keine native Vier-Bereichs-Struktur | Nein | Nein – Grid-/Kartenstruktur fehlt nativ | Nein |
| `notification-rule-modal` | aktuell kein natives Regel-Modal | Nein | Nein – Modal fehlt nativ | Nein |
| Primäre Test-/Regel-CTAs | aktuell nur „Legacy-Dashboard öffnen“ | Nein | Nein | Nein |

**Tab-lokale Abweichungen mit HA-Mehrwert**

- Ein nativer Notifications-Tab darf die Bereiche responsiver stapeln oder mit besserer Tastatur-/Screenreader-Führung ausstatten, muss aber `notification-grid` bzw. gleichwertige Kartenblöcke als Übersichtsmuster beibehalten.
- Testaktionen dürfen HA-näher formuliert werden, solange die primären CTAs gegenüber sekundären Links/Meta-Informationen klar dominant bleiben.

### Abnahmeliste `notifications`

- [ ] Geräteverwaltung ist nativ sichtbar und Geräte lassen sich aktiv/inaktiv schalten.
- [ ] Regel-Liste ist nativ sichtbar; Regeln lassen sich anlegen, bearbeiten und löschen.
- [ ] Testcenter unterstützt **Test an alle Geräte** und **Persistent-Test** nativ.
- [ ] Historie ist nativ sichtbar.
- [ ] Regel-Modal ist nativ vorhanden.
- [ ] `loadNotificationOverview()`-Status sowie leere/fehlerhafte/loading States sind nativ abgebildet.

---

## Übergreifende Abnahmeregel für die Migration

Ein Tab gilt erst dann als vollständig migriert, wenn alle Punkte seiner Abnahmeliste **und** seiner Vergleichsliste ohne Legacy-`iframe` erfüllt sind. Solange ein Tab nur über `GrocyAILegacyBridgeTab` läuft, bleibt sein Status **„native fehlt“**, selbst wenn Navigation, Header oder Quicklinks bereits im nativen Panel sichtbar sind.

Zusätzlich gilt: Eine technische 1:1-Funktionsabdeckung reicht nicht aus. Die Migration ist erst abgenommen, wenn die native Umsetzung die Legacy-Referenz aus `dashboard.html` auch **visuell und interaktiv** erkennbar fortführt – insbesondere bei `hero-card`, `variant-grid`, `recipe-columns`, `notification-grid` und `shopping-modal`.
