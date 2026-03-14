# Changelog

All notable changes to this project are documented in this file.

## 7.1.28

- Neu (Startup-Batch): Option `generate_missing_product_images_on_startup` ergänzt, um einmalig nach dem Start Produktbilder für bestehende Produkte ohne Bild zu erzeugen und in Grocy zu hinterlegen.
- Service: `GrocyClient` um `get_products_without_picture()` erweitert, damit Produkte ohne `picture_file_name` gezielt verarbeitet werden können.
- Test: API-/Konfigurations-Tests für den neuen Startup-Batch und die neue Add-on-Option ergänzt.
- Pflege: Add-on-Version auf `7.1.28` erhöht.

## 7.1.27

- Fix (Bildgenerierung): OpenAI-Image-Erstellung nutzt jetzt ein robustes Modell-Fallback (`openai_image_model` -> `dall-e-3` -> `dall-e-2`), wenn der primäre Modellzugriff mit `403 Forbidden` abgelehnt wird.
- Fix (Bildgenerierung): Antwortverarbeitung akzeptiert jetzt sowohl `b64_json` als auch `url`-basierte Bildantworten und lädt URL-Bilder automatisch herunter.
- Test: Unit-Tests für Modell-Fallback bei `403` und URL-Downloadpfad ergänzt.
- Pflege: Add-on-Version auf `7.1.27` erhöht.

## 7.1.26

- UI (Rezepte): Unten auf der Rezeptseite neuen Button „Rezept hinzufügen" ergänzt.
- UI (Rezepte): Neues Modal für Rezept-Erfassung mit Auswahl der Modi „WebScrape", „KI" und „Manuell" ergänzt.
- UI (Rezepte): Für „WebScrape" URL-Eingabe, für „KI" Prompt-Eingabe und für „Manuell" schnelles Rezeptformular mit den wichtigsten Feldern ergänzt.
- UX (Rezepte): Methoden-Auswahl im Modal als umschaltbare Panels umgesetzt, damit keine doppelten Codepfade nötig sind.
- Pflege: Add-on-Version auf `7.1.26` erhöht.

## 7.1.25

- UI: Scanner-Button in der Suche ohne Hintergrund gestaltet und vertikal an die Überschrift ausgerichtet.
- UI: Zusätzlichen unteren Abstand unter dem Button „Neue Regel“ in der Notify-Ansicht ergänzt.
- UI: Aktions-Buttons in der Regelverwaltung („Regel ändern“, „Löschen“) nach rechts ausgerichtet.
- UI (Lager): Buttons „Ändern“ und „Verbrauchen“ verkleinert, untereinander angeordnet und rechtsbündig positioniert.
- Fix (Lager-Dashboard/API): Verbrauchen-Aktion findet Bestandseinträge jetzt sowohl über `id` als auch über `stock_id`, damit Einträge mit nur ergänzter Bearbeitungs-ID wieder korrekt verbraucht werden können.
- Test: API-Test ergänzt, der das Verbrauchen über ein `get_stock_entries`-Ergebnis mit `stock_id` (ohne `id`) absichert.
- Pflege: Add-on-Version auf `7.1.25` erhöht.

## 7.1.24

- Neu: Optionale OpenAI-Bildgenerierung für neu erkannte Produkte ergänzt (`image_generation_enabled`, `openai_api_key`, `openai_image_model`).
- API/Service: Beim Neuanlegen eines Produkts über die Dashboard-Suche wird bei aktiver Option automatisch ein Produktbild über die OpenAI Images API erzeugt, in Grocy hochgeladen und dem Produkt zugewiesen.
- UI: Swipe-Aktionsfläche in der Einkaufsliste auf `138px` verbreitert (`.shopping-item-action`).
- UI: Scanner-Button-Icon auf ein Barcode-Symbol umgestellt (statt Kamera-Emoji), inklusive neuer CSS-Icon-Gestaltung.
- Fix (Lager-Dashboard): Fehlende Bearbeitungs-IDs aus `/stock` werden jetzt über `/objects/stock` ergänzt, damit Aktionen „Ändern“ und „Verbrauchen“ wieder für betroffene Einträge funktionieren.
- Test: Unit-Tests für Fallback der Bearbeitungs-ID in `get_stock_products` und `get_stock_entries` ergänzt.
- Pflege: Add-on-Version auf `7.1.24` erhöht.

## 7.1.23

- Fix: Klick auf den Badge „Menge" in der Einkaufsliste öffnet nicht mehr das Produkt-Popup, sondern erhöht zuverlässig die Menge des Eintrags.
- Fix: Swipe-/Pointer-Interaktion ignoriert jetzt alle interaktiven Badge-Buttons in Listeneinträgen, damit Button-Klicks nicht als Item-Tap verarbeitet werden.
- Fix (Lager-Dashboard): Produkte ohne `stock_id` werden nicht mehr vollständig ausgeblendet; sie werden jetzt in der Liste angezeigt.
- UX (Lager-Dashboard): Aktionen „Verbrauchen“ und „Ändern“ sind für Einträge ohne Bearbeitungs-ID deaktiviert und mit Hinweis versehen.
- UX (Lager-Dashboard): Statusmeldung zeigt an, wenn Einträge ohne Bearbeitungs-ID geladen wurden.
- Pflege: Add-on-Version auf `7.1.23` erhöht.

## 7.1.22

- UI: Eingabefelder (`input`, `select`, `textarea`) visuell an den restlichen Dashboard-Stil angepasst (einheitliche Rundungen, Schatten, Focus-Ring und weichere Placeholder-Farbe).
- UI: Fokuszustände für Formularelemente verbessert, inklusive klarerer Hervorhebung im Light- und Dark-Theme.
- Pflege: Add-on-Version auf `7.1.22` erhöht.

## 7.1.21

- Fix/Scope: Mengen-Badge-Funktion fokussiert auf Produkte in der Einkaufsliste (Badge „Menge“ erhöht weiterhin die einzukaufende Menge direkt im Listen-Eintrag).
- Cleanup: Rezept-Dialog-spezifische Mengen-Badge-Logik aus dem vorherigen Change entfernt.
- Pflege: Add-on-Version auf `7.1.21` erhöht.

## 7.1.20

- UI: Neuer Tab „Lager" vor „Notify" ergänzt, inklusive Filterfeld am Anfang der Seite und vollständiger Produktliste aus allen Lagern.
- UI/Funktion: Im Lager-Tab pro Produkt die Aktionen „Verbrauchen" und „Ändern" ergänzt.
- UI/Funktion: Neues Bearbeiten-Popup für Lagerprodukte ergänzt (Menge + MHD).
- API: Neue Endpunkte zum Verbrauchen und Aktualisieren einzelner Lager-Einträge ergänzt.
- Service: Grocy-Client um Methoden zum Verbrauchen und Aktualisieren von Lager-Einträgen erweitert.
- UI/Funktion: Der Badge für fehlende Produkte im Rezept-Dialog ist jetzt klickbar und erhöht die Menge der „einzukaufenden“ Produkte direkt in der Einkaufsliste um 1.
- API: `POST /api/dashboard/recipe/{recipe_id}/add-missing` akzeptiert optional Mengen pro Produkt (`products: [{id, amount}]`) und nutzt bestehenden Codepfad zum Hinzufügen auf die Einkaufsliste.
- Test: API- und Dashboard-Tests für klickbaren Mengen-Badge bei fehlenden Rezeptprodukten ergänzt.
- UI: Scanner-Tab aus der unteren Navigation entfernt und als Popup hinter ein Barcode-/Scanner-Icon verschoben.
- UI: Scanner-Icon rechts neben der Überschrift „Grocy AI Suche“ ergänzt; öffnet den Barcode-Scanner als Modal.
- UI: Untere Tabbar auf drei Tabs reduziert (Einkauf, Rezepte, Notify).
- Pflege: Add-on-Version auf `7.1.20` erhöht.

## 7.1.19

- UI: Produkt-Badges in der Einkaufsliste erneut etwas schmaler gemacht, damit sie weniger Breite einnehmen.
- Pflege: Add-on-Version auf `7.1.19` erhöht.

## 7.1.18

- Funktion: Produktsuche versteht jetzt Mengenpräfixe wie `2 nudeln` und verwendet die erkannte Menge beim Hinzufügen zur Einkaufsliste.
- Funktion: Variantensuche ignoriert Mengenpräfixe wie `2 apf`, sodass weiterhin passende Produkte gefunden werden.
- UI: Bei Auswahl eines Produkts aus der Produktauswahl wird bei Eingaben wie `2 apf` ebenfalls die Menge `2` übernommen.
- Test: API-Tests für Mengenpräfix in Suche und Variantensuche ergänzt.
- UI: Rezeptbild im Rezept-Detail-Popup auf Standardgröße zurückgesetzt (keine erzwungene Vergrößerung mehr).
- UI: Wrapper-Div für Rezeptbilder im Popup um eine `min-height` ergänzt, damit der Bildbereich stabil bleibt.
- UI: Die Karte/Spalte „Optionen“ wurde aus dem Benachrichtigungs-Dashboard entfernt.
- UI: Badge „Notiz bearbeiten“ in der Einkaufsliste entfernt.
- UI: Notizfeld direkt im Produkt-Detail-Popup unter der Überschrift ergänzt.
- UX/Logik: Notizen werden beim Schließen des Produkt-Popups automatisch gespeichert, falls sich der Inhalt geändert hat.
- Pflege: Add-on-Version auf `7.1.18` erhöht.

## 7.1.17

- Fix: Syntaxfehler in `dashboard.js` behoben (`Unexpected end of input`), verursacht durch einen unvollständig gebliebenen Event-Handler im Shopping-List-Click-Handling.
- Pflege: Add-on-Version auf `7.1.17` erhöht.

## 7.1.16

- Fix: Doppelte Deklarationen in `dashboard.js` entfernt, die im Browser den Fehler `Identifier 'NOTIFICATION_EVENT_LABELS' has already been declared` ausgelöst haben.
- Korrektur: Die globale Notification-Aktivierung wurde aus den Home-Assistant-Integrationsoptionen entfernt und stattdessen in die Add-on/App-Optionen verlagert (gleicher Bereich wie API-Keys).
- Add-on: Neue Option `notification_global_enabled` in `config.json` (`options` + `schema`) ergänzt.
- API: Notification-Overview und Settings-Update übernehmen den globalen Enabled-Status jetzt aus den Add-on-Optionen (`options.json`) statt aus der Integration.
- UI: Hinweistext in der Benachrichtigungs-Ansicht auf Add-on/App-Optionen angepasst.
- Pflege: Add-on-Version auf `7.1.16` erhöht.

## 7.1.15

- UI: Die globale Notification-Option „Benachrichtigungen global aktiv" wurde aus dem Dashboard entfernt und als Hinweis in den Bereich „Optionen" übernommen.
- Integration: Neue Home-Assistant-Option `notification_global_enabled` ergänzt, um Benachrichtigungen global über die Integrations-Optionen zu aktivieren/deaktivieren.
- Logik: NotificationManager übernimmt den globalen Aktivierungsstatus aus den Integrations-Optionen und setzt damit die globale Notification-Freigabe zentral.
- Fix: Barcode-Lookup liefert bei OpenFoodFacts-Timeouts keinen 500-Fehler mehr, sondern fällt robust auf Grocy bzw. "nicht gefunden" zurück.
- Test: API-Test ergänzt, der Timeout-Verhalten beim Barcode-Lookup absichert.
- Fix: Syntaxfehler in `GrocyClient.update_shopping_list_item_amount` behoben (fehlender Abschluss des `requests.put`-Aufrufs), sodass der API-Start nicht mehr mit `SyntaxError` abbricht.
- Pflege: Add-on-Version auf `7.1.15` erhöht.

## 7.1.14

- UI: Badges in der Einkaufsliste auf eine einheitliche Breite gebracht, damit „Menge“ und „MHD" konsistent groß angezeigt werden.
- UI/Funktion: „Menge" in der Einkaufsliste ist jetzt klickbar und erhöht die Einkaufsmenge des ausgewählten Produkts um 1.
- API: Neuer Endpoint zum Erhöhen der Menge einzelner Einkaufslisten-Einträge ergänzt.
- Tests: API-/Client-Tests für das Erhöhen der Einkaufslisten-Menge ergänzt.
- UI: Produktlisten im Rezept-Detail-Popup auf volle Breite umgestellt (Einrückung entfernt), damit Listeneinträge nicht mehr abgeschnitten oder versetzt dargestellt werden.
- Fix: Rezept-Detail-Popup erhält wieder einen klar sichtbaren, modernen Schließen-Button oben rechts, damit sich der Dialog zuverlässig schließen lässt.
- UI: Rezeptbild im Rezept-Detail-Popup deutlich vergrößert, damit nicht nur ein schmaler Bildstreifen sichtbar ist.
- Neu: Notizen für einzelne Einkaufslisten-Einträge sind im Dashboard direkt bearbeitbar (eigener Notiz-Dialog pro Eintrag).
- API: Neuer Endpoint `PUT /api/dashboard/shopping-list/item/{shopping_list_id}/note` zum Aktualisieren von Einkaufslisten-Notizen.
- Logik: Notizänderungen bleiben auf dem Einkaufslisten-Eintrag und verändern keine Grocy-Produktstammdaten; vorhandene MHD-Marker bleiben beim Speichern erhalten.
- Pflege: Add-on-Version auf `7.1.14` erhöht.

## 7.1.13

- UI: Regel-Popup visuell an das restliche Dashboard angepasst (klarerer Titel/Untertitel, bessere Formular- und Mehrfachauswahl-Darstellung, konsistente Aktionsleiste).
- UI: In der Regelverwaltung pro Regel einen neuen Button „Regel ändern“ ergänzt; bestehende Regeln lassen sich nun im Popup bearbeiten und speichern.
- Pflege: Add-on-Version auf `7.1.13` erhöht.

## 7.1.12

- UI: Events in der Benachrichtigungsansicht werden jetzt in normaler Sprache angezeigt (Regelliste und Historie).
- UI: Beim Erstellen neuer Regeln werden Events und Zielgeräte als Mehrfachauswahl-Dropdowns dargestellt.
- UI: Der Button „Neue Regel“ wurde unter die Überschrift „Regelverwaltung“ verschoben.
- Pflege: Add-on-Version auf `7.1.12` erhöht.

## 7.1.11

- UI: Rezeptbild wird jetzt auch im Rezept-Detail-Popup am oberen Rand angezeigt.
- UI: Rezeptbild im Popup mit leichtem visuellen Effekt (dezenter Verlauf, Schatten und minimale Sättigungs-/Kontrastanhebung) ergänzt.
- Fix: Rezeptbilder in den Rezeptvorschlägen werden jetzt über dieselbe URL-Normalisierung wie andere Bilder gerendert (`toImageSource`), damit sie auch bei Ingress/Proxy/HTTPS-Mischszenarien wieder zuverlässig angezeigt werden.
- Test: API-Test ergänzt, der absichert, dass Rezept-Thumbnail-URLs im Dashboard über `toImageSource(...)` laufen.
- Pflege: Add-on-Version auf `7.1.11` erhöht.

## 7.1.7

- UI: Benachrichtigungs-Optionenseite im Dashboard neu strukturiert und in klar getrennte Bereiche (Optionen, Geräte, Regeln, Testcenter, Historie) gegliedert.
- UI: Globalen Schalter und Speichern-Aktion in einer eigenen, verständlicheren Optionskarte zusammengeführt.
- UI: Neues Karten-Layout und responsive Darstellung für die Optionsseite ergänzt, damit die Bereiche auf Mobilgeräten untereinander statt nebeneinander angezeigt werden.
- Pflege: Add-on-Version auf `7.1.7` erhöht.

## 7.1.6

- Fix: Bildproxy normalisiert jetzt auch fehlerhaft encodierte `src`-URLs, bei denen `?force_serve_as=picture` als `%3Fforce_serve_as%3Dpicture` im Pfad steckt, und lädt das Bild danach korrekt.
- Test: API-Test ergänzt, der den `%3F...%3D...`-Fall im `src`-Parameter absichert.
- Pflege: Add-on-Version auf 7.1.6 erhöht.

## 7.1.5

- Fix: Dashboard-Bildproxy versucht bei 404 auf `/api/files/...` automatisch die passende Fallback-URL `/files/...` (und umgekehrt), damit Rezeptbilder hinter Home-Assistant/Grocy-Setups zuverlässig laden.
- Test: API-Test ergänzt, der den 404-Fallbackpfad des Bildproxys absichert.
- Pflege: Add-on-Version auf 7.1.5 erhöht.
- UI: Kanal und Severity wurden aus den allgemeinen Notification-Einstellungen in das Regel-Popup verschoben.
- Fix: Beim Erstellen neuer Regeln werden Kanal und Severity jetzt direkt aus dem Popup an die Regel gebunden und gespeichert.
- Fix: Dashboard-Bildproxy versucht bei 404 auf `/api/files/...` automatisch die passende Fallback-URL `/files/...` (und umgekehrt), damit Rezeptbilder hinter Home-Assistant/Grocy-Setups zuverlässig laden.
- Test: API-Test ergänzt, der den 404-Fallbackpfad des Bildproxys absichert.

## 7.1.4

- UI: „Regel anlegen" aus der Notification-Seite in ein eigenes Popup verschoben und über den neuen Button „Neue Regel" aufrufbar gemacht.
- Neu: Notification-Dashboard liefert jetzt mehrere sinnvolle, vordefinierte Standardregeln (Einkauf fällig, niedriger Bestand, fehlende Rezept-Zutaten).
- Fix: Frontend-Fehler `getAuthHeaders is not defined` behoben.
- Anpassung: Notification-Einstellungen und Regeln werden nun pro Home-Assistant-Benutzer gespeichert; der aktuell angemeldete Nutzer wird automatisch verwendet.
- UI: `.topbar-content` im Dashboard-Header auf `width: 100%` gesetzt.

## 7.1.3

- UI: Darkmode-Button im Header in die Titelzeile verschoben und rechts neben „Smart Pantry Dashboard“ ausgerichtet.
- Fix: Rezeptbilder in den Rezeptvorschlägen werden jetzt über den Dashboard-Bild-Proxy ausgeliefert, damit sie auch auf mobilen Geräten über Ingress zuverlässig laden.

## 7.1.2

- Anpassung: Kamera-Zoom des Barcode-Scanners auf 1.4x reduziert.

## 7.1.1

- UI: Swipe-Buttons in der Einkaufsliste lösen jetzt bei 75px statt 72px aus.
- UI: Fingerbewegung für Swipe-Aktionen direkter auf `distance * 0.8` abgestimmt.

## 7.1.0

- Neu: Enterprise-Notification-Architektur in der Home-Assistant-Integration eingeführt (Event-Modelle, Rule Engine, Dispatcher, persistenter Store und Orchestrator-Services).
- Neu: Home-Assistant-Services für Notification-Events und Testcenter ergänzt (`notification_emit_event`, `notification_test_device`, `notification_test_all`, `notification_test_persistent`).
- Neu: Architekturdokumentation und Dashboard-Spezifikation für Geräteverwaltung, Regeln, Testcenter und Historie ergänzt.

## 7.0.38

- UI: Lightmode-Theme-Icon auf dunklen Halbmond (`☾`) geändert.
- UI: Theme-Button nicht mehr `fixed`, sondern wieder mitscrollend im Header positioniert.
- Pflege: Add-on-Version auf 7.0.38 erhöht.

## 7.1.1

- Neu: Notification-Dashboard direkt in die App integriert (Geräteverwaltung, globale Einstellungen, Regelverwaltung, Testcenter, Historie) inklusive neuem Navigations-Tab.
- Neu: FastAPI-Endpunkte für Notification-Dashboard ergänzt (`/api/dashboard/notifications/*`) mit persistenter JSON-Ablage unter `/data/notification_dashboard.json`.
- Pflege: Versionen auf `7.1.1` erhöht.

## 7.1.0

- Neu: Enterprise-Notification-Architektur in der Home-Assistant-Integration eingeführt (Event-Modelle, Rule Engine, Dispatcher, persistenter Store und Orchestrator-Services).
- Neu: Home-Assistant-Services für Notification-Events und Testcenter ergänzt (`notification_emit_event`, `notification_test_device`, `notification_test_all`, `notification_test_persistent`).
- Neu: Architekturdokumentation und Dashboard-Spezifikation für Geräteverwaltung, Regeln, Testcenter und Historie ergänzt.
- Pflege: Versionsstände von Add-on und Integration auf `7.1.0` aktualisiert.

## 7.0.37

- UI: Theme-Button als modernes, schwebendes Icon ohne Hintergrund gestaltet (nur Sonne/Mond-Icon mit subtiler Floating-Interaktion).
- UI: Produkt-Badges in Einkaufselementen und in der Produktauswahl auf der Rezeptseite konsequent ganz nach rechts ausgerichtet.
- Fix: Swipe-Gesten in der Einkaufsliste auf mobilen Geräten empfindlicher gemacht (direktere Fingerbewegung, geringere Auslösedistanz), damit „Kaufen“/„Löschen“ zuverlässig auslösbar ist.

## 7.0.36

- UI: Button „Aktualisieren“ in der Einkaufsliste nutzt jetzt den invertierten Primary-Stil, damit er im Darkmode nicht zu dunkel erscheint.

## 7.0.35

- UI: Swipe-Aktionen in der Einkaufsliste auf eine moderne, iOS-inspirierte Implementation mit flüssigem Drag, dynamischen Action-Hintergründen und sanfter Commit-Animation umgestellt.
- Pflege: Add-on-Version auf 7.0.35 erhöht.
- UI: Im Bereich „Einkaufsliste“ den Button „Aktualisieren“ unter die Überschrift verschoben, damit der Titel nicht mehr neben dem Button umbricht.

## 7.0.34

- Fix: CHANGELOG-Format für Home Assistant angepasst (versionierte Abschnitte statt reinem "Unreleased"), damit Änderungen korrekt erkannt werden.
- UI: Button „Rezeptvorschläge laden“ unter den Suchbutton für bald ablaufende Produkte verschoben und mit zusätzlichem Abstand davor/danach versehen.
- Anpassung: Scanner-Beschreibungstext „Mit der Handykamera scannen und Produktdaten abrufen.“ aus dem Dashboard entfernt.
- Pflege: Add-on-Version auf 7.0.34 erhöht.

## 7.0.33

- Fix: Darkmode-Button verwendet jetzt in beiden Themes eine gut lesbare Schriftfarbe.
- Anpassung: Beschreibungstext unter „Grocy AI Suche“ entfernt und Aktivitäts-Spinner in die Hauptüberschrift verschoben.
- Fix: Dashboard-Header und zentrale UI-Elemente auf bessere Umbrüche bei schmalen Viewports optimiert.

- Fix: Dashboard-Layout setzt `html` auf `height: 100%` (inkl. `body`-Mindesthöhe), damit der Hintergrund die volle Viewport-Höhe abdeckt.
- Doku: README vollständig strukturell überarbeitet (Zielbild, Architektur, Konfiguration, API-Endpunkte, Entwicklungsabläufe).
- Pflege: Versionsstände für Add-on und Integration angehoben und im Projekt konsistent dokumentiert.

- Fix: Dashboard-Farbkontraste für Light-/Dark-Mode vereinheitlicht, damit aktive Tabs und Aktionsbuttons in beiden Themes gut lesbar bleiben.
- Neu: Home-Assistant-Integration ergänzt um Debug-Sensoren für die letzte und durchschnittliche KI-Antwortzeit (ms).
- Anpassung: Dashboard visuell neu ausgearbeitet mit shadcn/ui-inspirierter Optik (Topbar, Kartenlayout, modernisierte Farb- und Button-Systematik).
- Anpassung: Dashboard-Theme auf eine neue dunkle Farbwelt mit Mint-Akzenten, weicheren Karten und angepassten Button-/Badge-Farben umgestellt.
- Neu: Bei Grocy-Rezeptvorschlägen werden jetzt die konkreten Rezeptzutaten aus Grocy angezeigt.
- Anpassung: Zutaten aus Grocy-Rezepten enthalten jetzt Mengenangaben mit Einheiten-Attribution (z. B. Stk., Gramm), wenn in Grocy vorhanden.
- Anpassung: Im Dashboard werden nun bis zu 3 Grocy- und 3 KI-Rezepte angezeigt.

- Fix: Architekturtest-Datei auf `tests/architecture/test_layering.py` umbenannt, damit sie zuverlässig von `pytest` gesammelt und ausgeführt wird.
- Neu: `ARCHITECTURE.md` ergänzt mit Schichtenmodell, Verantwortlichkeiten und Erweiterungsleitfaden.
- Doku: `README.md` um Verweis auf die Architektur-Dokumentation und präzisen Architekturtest-Pfad erweitert.

- Entfernt: konfigurierbarer `scanner_llava_prompt` in den Add-on-Optionen.
- Neu: `scanner_llava_min_confidence` (1-100) als Add-on-Option zur Steuerung der benötigten Sicherheit.
- Anpassung: LLaVA-Prompt wird nun intern erzeugt und enthält die konfigurierbare Mindest-Sicherheit sowie die Vorgabe, bei zu geringer Sicherheit `NULL` zu antworten.
