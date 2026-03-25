## 2026-03-25 (Version 8.0.42)

- Fix (Grocy-Bildupload): `attach_product_picture` behandelt jetzt `405 Method Not Allowed` beim `PUT`-Upload als Fallback-Fall und versucht anschließend zusätzliche Upload-Varianten statt hart abzubrechen.
- Added (Tests/Grocy): Unit-Test ergänzt, der den `405`-Fall auf `PUT` abdeckt und den erfolgreichen Fallback über `POST` absichert.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.42` erhöht.

## 2026-03-25 (Version 8.0.41)

- Fix (Rezeptvorschläge/API-Latenz): Für KI-Rezeptvorschläge gilt jetzt ein eigener Timeout-Deckel von 20 Sekunden pro KI-Aufruf, auch wenn der globale Ollama-Timeout höher konfiguriert ist.
- Added (Tests/Rezeptvorschläge): API-Regressionstest stellt sicher, dass der Timeout-Deckel beim Dashboard-Rezeptendpoint angewendet wird.
- Added (Tests/KI-Client): Unit-Test deckt den expliziten `timeout_seconds`-Override im Rezeptgenerator ab.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.41` erhöht.

## 2026-03-25 (Version 8.0.40)
- Fix (Optionen/Runtime-Quellen): Wenn sowohl `/data/options.yaml` als auch `/data/options.json` vorhanden sind, verwendet der Loader jetzt den **zuletzt geänderten** Runtime-Stand statt YAML starr zu priorisieren. Damit werden aktuelle Optionen wie `cloud_ai.generate_missing_product_images_on_startup` zuverlässig erkannt.
- Fix (Settings-Cache): Der Cache-Token berücksichtigt jetzt alle vorhandenen Optionsquellen gemeinsam, damit Änderungen an YAML **und** JSON sicher eine Settings-Neuladung auslösen.
- Added (Tests/Optionen): Regressionstest prüft, dass bei gleichzeitiger YAML/JSON-Präsenz die neuere Datei gewinnt.
- Fix (Rezeptvorschläge/Fehlerbehandlung): Timeouts bzw. Verbindungsfehler beim Ollama-Request in `generate_recipe_suggestions` führen nicht mehr zu einem API-500, sondern werden geloggt und auf lokale Rezept-Fallbacks zurückgeführt.
- Fix (Rezeptvorschläge/Robustheit): Ungültige oder nicht parsebare KI-Antworten bei Rezeptvorschlägen werden jetzt defensiv abgefangen, damit der Dashboard-Request stabil bleibt.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.40` erhöht.

## 2026-03-25 (Version 8.0.39)

- Fix (Startup/Optionen): Startup-Hintergrundjobs laden die Add-on-Optionen jetzt direkt vor dem zeitverzögerten Start neu, statt nur den frühesten Bootstrap-Stand zu verwenden. Dadurch wird `cloud_ai.generate_missing_product_images_on_startup` auch dann korrekt erkannt, wenn Optionen kurz nach Prozessstart verfügbar sind.
- Added (Tests/Startup): Regressionstest stellt sicher, dass die Startup-Bildgenerierung mit dem **neu geladenen** Settings-Stand ausgeführt wird.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.39` erhöht.

## 2026-03-25 (Version 8.0.38)

- Fix (Options/Startup-Bildgenerierung): Der Options-Loader akzeptiert jetzt zusätzlich die Legacy-Gruppe `openai` als Alias für `cloud_ai`, sodass `generate_missing_product_images_on_startup` auch bei älteren oder migrierten Layouts korrekt erkannt wird.
- Added (Tests/Optionen): Regressionstest stellt sicher, dass die Startup-Bildgenerierungsoption aus `options.openai.generate_missing_product_images_on_startup` korrekt geladen wird.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.38` erhöht.

## 2026-03-25 (Version 8.0.37)

- Fix (Produktsuche): Fuzzy-Produktsuche akzeptiert jetzt auch 2-Buchstaben-Anfragen (z. B. "ei"), sodass kurze Suchbegriffe im Dashboard und in Variantenvorschlägen Treffer liefern.
- Added (Tests/Grocy): Unit-Test ergänzt, der die Produktsuche mit zwei Buchstaben absichert.
- Fix (Home-Assistant-Integration/Panel/Auth): Token-Erkennung im nativen Dashboard berücksichtigt jetzt zusätzliche Home-Assistant-Tokenpfade (`accessToken` und `access_token` in `hass.auth`/`hass.connection.auth`) und verhindert so erneute `401 Unauthorized`-Antworten beim Laden von Panel-Daten in unterschiedlichen HA-Runtimes.
- Added (Tests/Frontend): `tests/frontend/test_panel_shell_rendering.mjs` prüft die erweiterten Tokenpfade als Regression-Guard.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.37` erhöht.

## 2026-03-25 (Version 8.0.36)

- Added (Home-Assistant-Integration/Repairs): Neues Repairs-Issue `invalid_auth` ergänzt; Auth-Fehler (z. B. 401/Unauthorized/Forbidden) werden jetzt getrennt von allgemeiner Unerreichbarkeit erfasst.
- Changed (Home-Assistant-Integration/Übersetzungen): `strings.json`, `translations/en.json` und `translations/de.json` enthalten jetzt überarbeitete user-facing Repair-Meldungen mit Problem, Auswirkung und konkreten nächsten Schritten für `restart_required`, `addon_unreachable` und `invalid_auth`.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.36` erhöht.

## 2026-03-25 (Version 8.0.35)

- Added (Home-Assistant-Integration/Repairs): Neues Modul `custom_components/grocy_ai_assistant/repairs.py` ergänzt und `issue_registry`-basierte Repairs für Neustartpflicht sowie Add-on-Unerreichbarkeit implementiert.
- Changed (Home-Assistant-Integration/Coordinator): Status-Coordinator synchronisiert Repairs jetzt nach dem initialen Refresh und bei späteren Coordinator-Updates automatisch.
- Changed (Home-Assistant-Integration/Lifecycle): Beim Entladen eines Config-Entries werden zugehörige Repairs automatisch entfernt.
- Added (Home-Assistant-Integration/Übersetzungen): `strings.json`, `translations/en.json` und `translations/de.json` um translation-key-basierte Issue-Texte erweitert.
- Clarified (Startup/Bildsync): Startup-Logs unterscheiden jetzt klar zwischen **Bildgenerierung** (fehlende Produktbilder per KI) und **Bildcache-Sync** (Spiegeln vorhandener Grocy-Bilder), um Missverständnisse im Betrieb zu vermeiden.
- Added (Startup/Bildgenerierung): `_generate_missing_product_images_on_startup` liefert jetzt einen strukturierten Status (`status`, `generated`, `total`) zurück; der Status wird im Startup-Log explizit ausgegeben.
- Added (Tests): Startup-Tests decken die neuen Rückgabestatus für deaktivierte Startup-Option bzw. deaktivierte Bildgenerierung ab.
- Changed (Rezeptvorschläge/KI): KI-Rezepte werden jetzt nacheinander abgefragt, statt alle Vorschläge in einem einzelnen Abruf zu erwarten. Dabei werden bereits vorgeschlagene Titel bei jedem Folgeabruf mitgegeben, um Duplikate zu vermeiden.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.35` erhöht.

## 2026-03-25 (Version 8.0.34)

- Improved (Startup-Bildsync/Logging): Der Startup-Logeintrag in `api.main` enthält jetzt zusätzlich den Bildsync-Status und die Anzahl aktualisierter Bilder (`status`, `refreshed_images`), damit der Ablauf im Log besser nachvollziehbar ist.
- Improved (Produktbild-Cache/Status): `ProductImageCache` speichert den letzten Refresh-Status inklusive Fehlergrund und stellt ihn über `get_last_refresh_status()` bereit.
- Added (Tests): Unit-/Startup-Tests prüfen die neuen Statusinformationen des Produktbild-Caches.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.34` erhöht.

## 2026-03-25 (Version 8.0.33)

- Added (Home-Assistant-Integration/Diagnostics): Neue `diagnostics.py` für Config-Entry-Diagnosen ergänzt, inklusive Redaction sensibler Schlüssel, serialisierbarer Runtime-/Coordinator-Ausgabe und expliziter Status-Coordinator-Felder.
- Changed (Home-Assistant-Integration/Security): Neue Redaction-Utility für rekursive Maskierung (`"***"`) sensibler Schlüssel eingeführt, in Diagnostics verdrahtet und für Debug-Fehlerpfade genutzt, damit API-Keys/Tokens/Authorization-Header nicht in Logs oder Diagnostics landen.
- Fix (Add-on/Ollama): Die bislang hart codierten `requests`-Timeouts (60s) für `analyze_product_name`, `suggest_similar_products` und `generate_recipe_suggestions` sind jetzt über die neue Add-on-Option `ollama.ollama_timeout_seconds` konfigurierbar.
- Added (Add-on/App-Optionen): `config.yaml` ergänzt `options.ollama.ollama_timeout_seconds` inklusive Schema-Validierung `int(5,300)`.
- Changed (API/Capabilities): `/api/v1/capabilities` liefert den neuen Default-Wert `ollama_timeout_seconds` mit aus.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.33` erhöht.

## 2026-03-23 (Version 8.0.32)

- Fix: Fokus-Restore im nativen Lager-Tab nutzt jetzt den aktiven Fokus innerhalb des Panel-Shadow-DOMs, sodass das Filterfeld auch nach Storage-Reloads stabil fokussiert bleibt.

## 2026-03-23 (Version 8.0.31)
- Fix (Grocy-Bildupload): Produktbild-Upload verwendet jetzt direkt die funktionierende `PUT /files/productpictures/...`-Variante mit `GROCY-API-KEY`, statt nacheinander nicht funktionierende `POST`-/`/api/files/...`-/Header-Modus-Fallbacks zu durchlaufen.
- Test: Unit-Tests für den vereinfachten Uploadpfad und den Base64-Dateinamen-Fallback auf die direkte `/files/...`-Variante angepasst.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.31` erhöht.

## 2026-03-23 (Version 8.0.30)
- Docs (API): README dokumentiert die tatsächlich in `grocy_ai_assistant/api/routes.py` bereitgestellten Integrations- und Dashboard-Routen jetzt gruppiert nach Zweck und ergänzt insbesondere die bisher fehlenden `/api/v1/`-Endpunkte für Einkaufsliste, Lager, Rezepte, Barcode und Last-Scan.
- Docs (Add-on): `grocy_ai_assistant/DOCS.md` unterscheidet nun explizit zwischen Integrations-API (`/api/v1/...`) und Dashboard-/UI-API (`/api/dashboard/...`) und verweist für Notification-spezifische Endpunkte auf die dedizierten Architektur-/Dashboard-Spezifikationen.
- Docs: `README.md` an die tatsächliche Repository-Struktur angepasst; der Projektbaum zeigt jetzt `grocy_ai_assistant/CHANGELOG.md` statt eines Root-Changelogs.
- Docs: Versionsangaben im README auf die synchronen Versionsstände aus `grocy_ai_assistant/config.yaml`, `grocy_ai_assistant/custom_components/grocy_ai_assistant/manifest.json` und `grocy_ai_assistant/custom_components/grocy_ai_assistant/const.py` (`8.0.30`) aktualisiert und den Changelog-Link auf den realen Pfad korrigiert.
- Docs: Relative Markdown-Links im README gegen die vorhandenen Dateipfade geprüft.
- Changed (Versioning): Spitzenversion im Changelog mit `config.yaml`, `manifest.json` und `const.py` auf `8.0.30` abgeglichen; Versionsstände für Add-on und Integration bleiben synchron.
- Fix (Grocy/Create-Product): Produktanlagen normalisieren jetzt ungültige KI-Lagerort- und Mengeneinheits-IDs vor dem ersten POST auf valide Grocy-IDs, sodass `/api/dashboard/search` nicht mehr mit 400 auf `/objects/products` scheitert.
- Test: Unit-Regressionen für die Vorab-Normalisierung ungültiger `location_id`-/`qu_id_*`-Werte ergänzt; Versionsstände auf `8.0.30` erhöht.

## 2026-03-23 (Version 8.0.29)

- Fix (Home-Assistant-Integration/Panel/Einkauf): Die Produktsuche im nativen Shopping-Panel feuert Submit-, Clear- und Varianten-Klick-Events nicht mehr doppelt ab; dadurch wird `analyze_product_name` beim direkten Neuanlegen eines Produkts nur noch einmal ausgelöst.
- Added (Tests/Frontend): Rendering-Regressionen stellen sicher, dass die Search-Bar nur noch delegierte Event-Handler verwendet und keine doppelten Formular-/Button-Listener mehr registriert.
- Fix (Grocy/Produktanlage): Produkt-Create-Retries laufen jetzt nur noch bei echten Schemafehlern vom Typ `has no column named ...`; generische `400 Bad Request`-Antworten wie doppelte Produktnamen lösen keinen fehlerhaften zweiten Create-Call mehr aus.
- Added (Tests/Grocy): Unit-Regressionen decken jetzt sowohl den weiterhin erlaubten Unknown-Column-Retry als auch den neuen No-Retry-Pfad bei `UNIQUE constraint failed: products.name` ab.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.29` erhöht.
- Added (Tests/Versioning): Ein Regressionstest stellt jetzt sicher, dass Spitzenversion im Changelog sowie Add-on-/Integrations-Metadaten und `INTEGRATION_VERSION` dauerhaft synchron bleiben.

## 2026-03-23 (Version 8.0.28)

- Fix (Home-Assistant-Integration/Panel/Einkauf): Die Produktsuche im nativen Shopping-Panel startet Live-Vorschläge jetzt erst ab zwei Buchstaben des eigentlichen Produktnamens; Mengenpräfixe wie `2 A` zählen dabei nicht als zusätzliche Suchzeichen.
- Fix (Dashboard/Web/Einkauf): Auch im klassischen Dashboard blockiert die Produktsuche Live-Anfragen und direkte Sucheingaben jetzt bis mindestens zwei Buchstaben eingegeben wurden.
- Added (Tests/Frontend): Controller-Regressionen sichern ab, dass unter zwei Buchstaben weder Variantensuche noch Produktsubmit ausgelöst werden.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.28` erhöht.

## 2026-03-23 (Version 8.0.27)

- Fix (Home-Assistant-Integration/Panel/Sicherheit): Produktbilder im nativen HA-Panel werden jetzt nicht mehr als direktes `<img src>` gegen den geschützten Proxy geladen, sondern per auth-gebundenem Fetch mit HA-Bearer-Token in kurzlebige `blob:`-URLs umgesetzt, damit kein 401 mehr auftritt und der Endpoint trotzdem geschlossen bleibt.
- Changed (Home-Assistant-Integration/Panel/Kommentar): `GrocyAIDashboardPictureProxyView` dokumentiert jetzt explizit, warum der Endpoint authentifiziert bleibt und weshalb das Frontend den Bildabruf aktiv übernimmt.
- Added (Tests/Frontend): Regressionen decken jetzt den placeholder-first/auth-fetch-Bildpfad des nativen Panels ab.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.27` erhöht.

## 2026-03-23 (Version 8.0.26)

- Fix (Home-Assistant-Integration/Panel/Sicherheit): Die Produktbild-Proxy-View des nativen Panels verlangt jetzt Home-Assistant-Authentifizierung statt Bildabrufe anonym offenzulegen.
- Changed (Home-Assistant-Integration/Panel/Kommentar): `GrocyAIDashboardPictureProxyView` dokumentiert jetzt direkt im Code, dass Produktbilder aus dem eingeloggten HA-Frontend per same-origin-`<img src>` über den Panel-Proxy geladen werden und deshalb Session-Cookies ausreichen.
- Added (Tests/Home-Assistant-Integration): Panel-Regressionen sichern ab, dass die dedizierte Produktbild-Route authentifiziert bleibt und weiterhin korrekt an das Add-on weiterleitet.
- Fix (Produktsuche/Varianten): Auswahl der Eingabe-Variante im nativen Shopping-Panel erkennt nun wieder zuverlässig `productSource=input`, erzwingt dadurch die Neuanlage statt erneut in die Variantenauswahl zu fallen und belässt Suchtexte ohne explizite Mengenangabe ohne künstliches `1`-Präfix.
- Test: Frontend-Controller-Tests für `productSource` aus dem Variantendatensatz sowie für Vorschlagsübernahme ohne implizites `1`-Präfix ergänzt.
- Fix (Home-Assistant-Integration/Panel/Einkauf): Das Status-Badge unter der Produktsuche im nativen Panel darf jetzt bei langen Meldungen umbrechen, statt horizontal auszureißen.
- Fix (Dashboard/Web/Einkauf): Auch das Status-Badge unter der Produktsuche im klassischen Dashboard bricht lange Texte jetzt sauber um.
- Added (Tests/Frontend): CSS-Regressionen sichern das neue Umbruch-Verhalten der Such-Status-Badges im nativen Panel und im Web-Dashboard ab.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.26` erhöht.

## 2026-03-23 (Version 8.0.25)

- Fix (Home-Assistant-Integration/Panel/Lager): Im nativen Lager-Tab bleibt der Button `Aktualisieren` jetzt auch in der Karten-Kopfzeile direkt neben `Lagerliste`, inklusive Mobile-Layout.
- Fix (Home-Assistant-Integration/Panel/Lager): Der Toggle `Alle anzeigen` nutzt jetzt dieselbe Steuerhöhe wie das Produkt-Filterfeld.
- Fix (Home-Assistant-Integration/Panel/Einkauf): Die separate Statuszeile oberhalb von `Einkauf abschließen` wurde aus der nativen Einkaufsliste entfernt.
- Changed (Home-Assistant-Integration/Panel/Einkauf): Die Statusmeldung unter `Produkt prüfen` rendert jetzt als Badge statt als einfacher Hilfstext.
- Fix (Dashboard/Web/Lager): Im klassischen Dashboard teilen sich Produktfilter und `Alle anzeigen` jetzt ebenfalls eine gemeinsame Kontrollzeile mit gleich hoher Checkbox-Fläche.
- Changed (Dashboard/Web/Einkauf): Die Einkaufs-Statusmeldung wurde aus der Listenkarte entfernt und als Badge in den Suchbereich verschoben.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.25` erhöht.

- Refactor (Home-Assistant-Integration/Runtime-State): Die Integration entfernt direkte `hass.states.async_set(...)`-Schreibzugriffe aus `__init__.py` und hält kurzlebige Antwort-, Analyse-, Barcode-, LLaVA- und Timingdaten jetzt entry-scoped in einer zentralen Runtime-Datenstruktur unter `hass.data[DOMAIN][entry_id]`.
- Refactor (Home-Assistant-Integration/Entities): Response-, Status- und Timing-Sensoren veröffentlichen ihre Zustände nun entity-getrieben über Dispatcher-Signale und `async_write_ha_state()` statt per externem Write in die State Machine.
- Refactor (Home-Assistant-Integration/Text): Das Produkt-Eingabefeld nutzt jetzt echte `TextEntity`-Updates inklusive `RestoreEntity`, sodass Service-Aufrufe den Wert aus der Runtime-Struktur lesen und erfolgreiche Syncs das Feld sauber über die Entity leeren.
- Added (Tests/Home-Assistant-Integration): Unit-Tests decken jetzt die Runtime-State-Ausleitung für Response-/Timing-Sensoren sowie den textbasierten Produktwert ab.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.25` erhöht.

## 2026-03-23 (Version 8.0.24)

- Fix (Home-Assistant-Integration/Panel/Lager): Im Lager-Tab heißt der Checkbox-Text jetzt `Alle anzeigen`.
- Fix (Home-Assistant-Integration/Panel/Lager/Mobile): Checkbox und Textfilter bleiben auf schmalen Viewports sauber auf gleicher Höhe; der Button `Aktualisieren` bricht im Lager-Tab mobil nicht mehr um.
- Added (Home-Assistant-Integration/Übersetzungen): Neue `strings.json` sowie `translations/en.json` und `translations/de.json` ergänzen Config-Flow-, Entity- und Service-Texte im HA-üblichen Übersetzungsformat.
- Refactor (Home-Assistant-Integration/Entities): Buttons, Sensoren und Text-Entity verwenden jetzt `translation_key` plus `has_entity_name`, damit Home Assistant lokalisierte Anzeigenamen aus den Übersetzungen aufbauen kann.
- Refactor (Home-Assistant-Integration/States/Services): Harte deutsche Statuswerte wurden auf stabile State-Slugs reduziert; `services.yaml` nutzt jetzt konsistente, übersetzungsfreundliche Bezeichnungen und Beschreibungen.
- Fix (Home-Assistant-Integration/Manifest): `manifest.json` markiert die Integration jetzt zusätzlich mit `single_config_entry`, damit Home Assistant die Integration bereits im UI als Einzelinstanz behandelt und kein weiterer Einrichtungsdialog angeboten wird.
- Added (Tests/Home-Assistant-Integration): Ein Manifest-Regressionstest stellt sicher, dass die Single-Instance-Markierung künftig nicht versehentlich entfernt wird.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.24` erhöht.

## 2026-03-23 (Version 8.0.23)
- Changed (Home-Assistant-Integration/Config Flow): Die Integration behandelt Config Entries jetzt explizit als Single-Instance und setzt in `async_step_user` eine stabile `unique_id`, wodurch weitere Einrichtungsversuche sauber abbrechen.
- Changed (Home-Assistant-Integration/Konfiguration): Ein separater Reauth-/Reconfigure-Pfad wurde bewusst nicht ergänzt, weil die bestehende Options-Flow-Konfiguration bereits die relevanten Einstellungen der einzigen Instanz abdeckt.
- Added (Tests/Home-Assistant-Integration): Unit-Tests decken jetzt ab, dass der User-Step die Single-Instance-`unique_id` setzt und bei bestehender Konfiguration korrekt abbricht.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.23` erhöht.

## 2026-03-23 (Version 8.0.22)
- Fix (Home-Assistant-Integration/Panel): Das native Dashboard liest Entry-Konfigurationen jetzt wieder korrekt aus `hass.data[DOMAIN][entry_id]["config"]`, sodass Proxy-Requests nach der Coordinator-Einführung wieder den konfigurierten API-Key und die Base-URL verwenden und nicht mit `Unauthorized` am Add-on scheitern.
- Added (Tests/Home-Assistant-Integration): Ein Panel-Unit-Test deckt die verschachtelte Entry-Runtime-Struktur samt Dashboard-Metadaten und Proxy-Client-Konfiguration ab.
- Changed (Home-Assistant-Integration/Panel): Die Eyebrow `Einkauf` wurde aus der Überschrift `Einkaufsliste` in den Shopping-Hero verschoben und sitzt jetzt direkt oberhalb von `Grocy AI Suche`.
- Fix (Dashboard/Web): Die klassische Dashboard-Topbar zeigt `Grocy AI Assistant` wieder an ihrer ursprünglichen Stelle statt im Shopping-Hero.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.22` erhöht.

## 2026-03-23 (Version 8.0.21)
- Refactor (Home-Assistant-Integration/Sensoren): Neue Coordinator-Schicht in `custom_components/grocy_ai_assistant/coordinator.py` bündelt Status-, Lager-/Shopping- und Rezeptvorschlags-Polling entry-scoped in `hass.data[DOMAIN][entry.entry_id]` inklusive zentralem Fehler- und Availability-Handling.
- Refactor (Home-Assistant-Integration/Sensoren): Die polling-basierten Sensoren in `sensor.py` leiten ihren State jetzt ausschließlich aus `coordinator.data` ab und führen keine direkten Add-on-API-Calls oder eigenes `async_update` mehr aus.
- Fix (Home-Assistant-Integration/Panel/Mobile): Die Labels der unteren Tab-Buttons `Produktsuche` und `Lager` bleiben beim Wechsel in den mobilen Viewport jetzt vertikal mittig im Button statt nach oben zu springen.
- Added (Tests/Frontend): Eine CSS-Regression prüft jetzt die stabilisierte Icon-/Label-Ausrichtung der nativen Tab-Buttons.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.21` erhöht.

## 2026-03-23 (Version 8.0.20)
- Changed (Home-Assistant-Integration/Panel): Der native Dashboard-Shell entfernt den Tab `Benachrichtigungen` komplett aus Navigation, Routing und Panel-Markup; Benachrichtigungen werden damit nicht mehr über das native Dashboard angeboten, sondern ausschließlich über die App-Oberfläche gesteuert.
- Added (Tests/Frontend): Routing- und Shell-Regressionen sichern ab, dass `tab=notifications` im nativen Panel auf `shopping` zurückfällt und keine Notification-Tab-Struktur mehr gerendert wird.
- Changed (Home-Assistant-Integration/Panel): Die Kopfzeile der nativen Einkaufsliste zeigt jetzt wie die übrigen Tabs eine `Einkauf`-Eyebrow über `Einkaufsliste`.
- Fix (Home-Assistant-Integration/Panel): Unter der Überschrift `Grocy AI Suche` sitzt wieder ein sichtbarer Abstand zur Suchleiste, damit die Section-Header-Vertikale konsistent wirkt.
- Added (Tests/Frontend): Eine Panel-Regression prüft die neue `Einkauf`-Eyebrow der Einkaufsliste sowie den wiederhergestellten Header-Abstand der Shopping-Suche.
- Fix (Dashboard/Shopping): Die Aktionsbuttons `Einkauf abschließen` und `Einkaufsliste leeren` teilen sich jetzt im klassischen Dashboard dieselbe volle Zeile gleichmäßig statt untereinander zu erscheinen.
- Fix (Home-Assistant-Integration/Panel): Die nativen Shopping-Aktionen `Einkauf abschließen` und `Einkaufsliste leeren` nutzen jetzt ebenfalls eine gemeinsame 50/50-Aktionszeile über die volle Kartenbreite.
- Added (Tests/Frontend): Eine Panel-Regression prüft jetzt explizit die gemeinsame Vollbreiten-Aktionszeile der nativen Einkaufslisten-Buttons.
- Fix (Home-Assistant-Integration/Panel): Der native Dashboard-Content rendert die Tab-Hosts nicht mehr als eigene gestapelte Layout-Zeilen, sodass Inhalte in späteren Tabs nicht mehr pro Tab weiter nach unten rutschen.
- Fix (Home-Assistant-Integration/Panel): `tab-view`- und `card`-Container nutzen jetzt wieder den Home-Assistant-üblichen Standardabstand zwischen Abschnitten; damit erhalten Shopping-, Rezept-, Lager- und Fallback-Bereiche wieder konsistente Section-Abstände.
- Fix (Home-Assistant-Integration/Panel): In der nativen Einkaufsliste sitzt unter der Kopfzeile mit `Aktualisieren` wieder derselbe Standardabstand wie zwischen den übrigen Card-Sektionen.
- Added (Tests/Frontend): Die Panel-CSS-Regression sichert jetzt Block-Layout für den Dashboard-Content sowie Standardabstände für Tab- und Card-Container ab.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.20` erhöht.

## 2026-03-23 (Version 8.0.19)
- Changed (Home-Assistant-Integration/Panel): Der Scanner-Button im nativen Einkaufs-Dashboard rendert jetzt ein Home-Assistant-konformes `ha-icon` mit `mdi:barcode-scan` statt des bisherigen pseudo-gemalten Barcode-Icons.
- Added (Tests/Frontend): Eine Panel-Regression prüft jetzt explizit, dass der native Scanner-Trigger das HA-Icon `mdi:barcode-scan` verwendet.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.19` erhöht.

## 2026-03-23 (Version 8.0.18)
- Changed (Home-Assistant-Integration/Panel): Im nativen Lager-Tab sitzt `Aktualisieren` jetzt direkt in der Kopfzeile der Abschnittskarte `Lagerliste` und wird dort rechtsbündig angezeigt.
- Added (Tests/Frontend): Eine Frontend-Regression prüft, dass die Lagerlisten-Karte weiterhin die Überschrift `Lagerliste` samt rechts ausgerichtetem `Aktualisieren`-Button rendert.
- Fix (Home-Assistant-Integration/Panel/Mobile): Im Einkaufslisten-Tab bleibt der Scanner-Button auf mobilen Viewports jetzt in derselben Kopfzeile wie die Überschrift `Grocy AI Suche` und sitzt rechtsbündig statt unter die Überschrift umzubrechen.
- Added (Tests/Frontend): Eine Panel-CSS-Regression prüft jetzt explizit die mobile Kopfzeile des Einkaufslisten-Tabs samt rechtsbündigem Scanner-Button.
- Fix (Home-Assistant-Integration/Panel/Mobile): Die Kopfzeile der nativen Einkaufsliste hält `Einkaufsliste` und den Button `Aktualisieren` jetzt auch auf schmalen Viewports in einer gemeinsamen Zeile; der Button sitzt dabei rechtsbündig statt unter dem Titel umzubrechen.
- Added (Tests/Frontend): Eine Panel-Regression sichert die einzeilige Shopping-Listen-Kopfzeile inklusive Mobile-Override ab.
- Fix (Lager-Tab/Filterlayout): Im nativen Panel stehen Produktfilter und `Alle Produkte anzeigen` jetzt in derselben Kontrollzeile; die Summen-Badges sitzen separat darunter.
- Fix (Dashboard/Legacy/Mobile): Der Lager-Tab stapelt Produktfilter und Checkbox auf schmalen Viewports nicht mehr untereinander, sodass beide Controls in einer Zeile bleiben.
- Added (Tests/Frontend): Panel-Regressionstests prüfen jetzt die separate Lager-Kontrollzeile und die darunter liegenden Summen-Badges.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.18` erhöht.

## 2026-03-23 (Version 8.0.17)
- Fix (Home-Assistant-Integration/Panel): Die native Bottom-Bar blendet sich jetzt aus, sobald eines der Dashboard-Modals geöffnet ist, damit sie keine Modal-Actions am unteren Rand mehr überdeckt.
- Fix (Home-Assistant-Integration/Panel): Dashboard-Modals liegen per höherem `z-index` jetzt zuverlässig über der Floating-Bottom-Bar, auch in nativen Mobile-/WebView-Shells.
- Added (Tests/Frontend): Die Panel-Shell-Regression prüft jetzt explizit, dass die Bottom-Bar bei offenem Modal deaktiviert wird und Modals vor der Navigation liegen.
- Changed (Dashboard/Scanner): Das Debug-Kästchen mit den Kamera-Fähigkeiten wurde aus dem Scanner-Popup im klassischen Dashboard entfernt.
- Changed (Home-Assistant-Integration/Panel): Der native Scanner-Dialog zeigt keinen separaten Debug-Block mit Kamera-Fähigkeiten mehr.
- Fix (Home-Assistant-Integration/Panel/Mobile): Das native Dashboard nutzt auf mobilen Viewports jetzt eine bessere Textskalierung und größere Mikrotypografie für Status-, Hilfs- und Karteninhalte, damit Beschriftungen auf dem Handy lesbarer bleiben.
- Fix (Home-Assistant-Integration/Panel/Mobile): Überschriften, Karten-Gruppen, Rezept-/Lager-Listen und Standort-Dropdowns wurden für schmale Viewports robuster gestapelt, damit es weniger unerwünschte Umbrüche und abgeschnittene Inhalte gibt.
- Added (Tests/Frontend): Eine Panel-CSS-Regression sichert die neuen Mobile-Regeln für Typografie, Tab-Labels und einspaltige Karten-/Bestandslayouts ab.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.17` erhöht.

## 2026-03-22 (Version 8.0.16)
- Changed (Home-Assistant-Integration/Panel): Im nativen Lager-Tab entfällt die beschreibende Hero-Subline; Textfilter, Summen-Badges und `Alle Produkte anzeigen` sitzen jetzt gemeinsam in einer `shopping-search-shell`-ähnlichen Filter-Shell.
- Changed (Home-Assistant-Integration/Panel): Die native Lagerliste rendert jetzt in einer eigenen Abschnittskarte `Lagerliste`, analog zur Struktur des Einkaufslisten-Tabs.
- Added (Tests/Frontend): Panel-Regressionstests sichern die neue Lager-Filter-Shell sowie die separate Lagerlisten-Sektion ab.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.16` erhöht.

## 2026-03-22 (Version 8.0.15)
- Fix (Home-Assistant-Integration/Panel): Die Swipe-Buttons im nativen Lager-Tab erben das zentrierte Variantenkarten-Layout nicht mehr, sodass Produktname und Zusatzinfos wieder linksbündig wie in der Einkaufsliste dargestellt werden.
- Fix (Home-Assistant-Integration/Panel): Die Badge-Spalte der nativen Lager-Swipe-Karten richtet sich wieder wie in der Einkaufsliste aus, statt durch die Variantenkarten-Styles mittig zu verrutschen.
- Added (Tests/Frontend): Eine CSS-Regression stellt sicher, dass die zentrierten Variantenkarten-Styles nur noch echte Variantenkarten betreffen.
- Fix (Home-Assistant-Integration/Panel/Scanner): Das native Scanner-Popup startet die Kamera beim Öffnen nicht mehr automatisch, sondern erst nach explizitem Klick auf `Scanner starten`. Das reduziert Abstürze in problematischen Browsern/WebViews beim reinen Öffnen des Popups.
- Changed (Home-Assistant-Integration/Panel/Scanner): Beim Öffnen zeigt das Popup bzw. die Topbar jetzt den Hinweis `Scanner geöffnet. Kamera bitte manuell starten.`, damit der neue Ablauf klar erkennbar ist.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.15` erhöht.

## 2026-03-22 (Version 8.0.14)
- Changed (Home-Assistant-Integration/Panel): Produktvarianten im nativen Shopping-Tab zeigen keine `Auswählen`-Beschriftung mehr, rendern den Produktnamen zentriert unter dem Bild und halten das Mengen-Badge wieder schwebend an der rechten oberen Bildecke; das Varianten-Grid zeigt dabei mindestens zwei Kacheln nebeneinander.
- Changed (Home-Assistant-Integration/Panel): Im Rezepte-Tab blendet das Dropdown `Produkte in ausgewählten Standorten` die Badges `Menge` und `MHD` aus und zeigt optional nur noch den Lagerort als Zusatzinfo.
- Changed (Home-Assistant-Integration/Panel): Die Status-Badges im nativen Lager-Tab sitzen jetzt direkt unter dem Textfilter in einer kompakten Zeile statt untereinander bzw. vollbreit.
- Added (Tests/Frontend): Shared-UI- und Panel-Regressionstests decken die CTA-freie Variantenkarte sowie das reduzierte Rezepte-Produkt-Dropdown weiterhin ab.
- Fix (Home-Assistant-Integration/Panel/Scanner): Das native Scanner-Popup nutzt beim Kamera-Start wieder kompatible `getUserMedia`-Fallbacks (`navigator.getUserMedia`/`webkitGetUserMedia`/`mozGetUserMedia`/`msGetUserMedia`) statt ausschließlich `navigator.mediaDevices.getUserMedia`, sodass der Scanner nach der Portierung auch in Home-Assistant-WebViews und älteren mobilen Browsern wieder startet.
- Fix (Home-Assistant-Integration/Panel/Scanner): Vor dem Start des nativen Kamera-Streams werden `playsinline`, `autoplay` und `muted` zusätzlich explizit am Video-Element gesetzt, um mobiles WebKit-/App-Verhalten robuster zu machen.
- Added (Tests/Frontend): Eine Panel-Regression sichert die wiederhergestellten Kamera-Fallbacks und die explizite Video-Initialisierung des nativen Scanner-Popups ab.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.14` erhöht.

## [8.0.13] - 2026-03-22
- Changed (Home-Assistant-Integration/Panel): Die Kopfzeile des nativen Dashboards zeigt das Badge `3/4 Bereiche nativ` nicht mehr an.
- Changed (Home-Assistant-Integration/Panel): Im nativen Rezepte-Tab entfallen Migrationshinweis und Meta-Badges; `Rezept hinzufügen` und `Rezepte laden` stehen jetzt als gemeinsame Aktionszeile direkt unter `Rezeptvorschläge`.
- Changed (Home-Assistant-Integration/Panel): Im nativen Lager-Tab ersetzt eine Badge-Zeile unter dem Textfilter die bisherige Statusmeldung und zeigt Summen für `Produkte`, `Produkte auf Lager` und `Produkte nicht auf Lager`.
- Added (Tests/Frontend): Panel-Regressionstests sichern die entfernte Kopfzeilen-Badge, die Rezepte-Aktionszeile und die neuen Lager-Badges ab.
- Changed (Home-Assistant-Integration/Panel, Dashboard/Web): Die Rezepte-Filter für `Lagerort` sowie `Produkte in ausgewählten Standorten` erscheinen wieder als kompakte Dropdown-Zusammenfassungen mit Auswahl-Status statt dauerhaft geöffneter Listen.
- Fix (Home-Assistant-Integration/Panel, Dashboard/Web): Produktattribute im Rezepte-Bestand werden wieder als Badges für `Menge`, `MHD` und optional `Lagerort` dargestellt.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.13` erhöht.

## [8.0.12] - 2026-03-22
- Fix (Frontend/Shopping): `renderShoppingListItemCard(...)` respektiert jetzt sowohl `badgeOrder` als auch `stockBadgeOrder`, sodass konfigurierbare Badge-Reihenfolgen in der rechten Badge-Spalte wieder konsistent gerendert werden.
- Fix (Notifications/UTC): Notification-Zeitstempel und zugehörige Tests verwenden jetzt timezone-aware UTC-Werte statt `datetime.utcnow()`, wodurch Deprecation-Warnungen entfallen.
- Docs: README-Versionen sowie Panel-/Notification-Dokumentation an den aktuellen Stand (`8.0.12`, native Rezepte/Lager-Tabs, aktuelle Notification-API-Routen) angepasst.
- Changed (Home-Assistant-Integration/Panel): Die Produktvariantenauswahl im nativen Shopping-Dashboard rendert wieder die gemeinsame Kachelansicht mit Bild, Badges, Kontextinfos und CTA statt der reduzierten Listen-/Zeilenkarte.
- Added (Tests/Frontend): Ein Panel-Shell-Regressionstest sichert ab, dass die native Variantensuche wieder `renderShoppingVariantCard(...)` inklusive Bildauflösung nutzt.
- Fix (Home-Assistant-Integration/Panel): Der native Rezepte-Tab stapelt seine Karten im Mobile-View jetzt einspaltig, sodass Grocy- und KI-Rezepte nicht mehr nebeneinander in zwei Spalten erscheinen.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.12` erhöht.

## [8.0.11] - 2026-03-22
- Fix (Home-Assistant-Integration/Panel): Im nativen Desktop-Panel wird die Bottom-Bar jetzt an der tatsächlich gerenderten Shell-Mitte ausgerichtet; beim Öffnen oder Schließen der Home-Assistant-Sidebar bleibt sie dadurch zentriert statt leicht nach links versetzt.
- Fix (Home-Assistant-Integration/Panel): Die Status-Badges im nativen Lager-Tab berechnen `auf Lager` und `nicht auf Lager` jetzt auch bei deaktiviertem Toggle `Alle Produkte anzeigen` korrekt über einen separaten Summenabruf mit identischem Filter.
- Fix (Dashboard/Web): Die Lager-Statusmeldung des Web-Dashboards nutzt für `nicht auf Lager`-Hinweise jetzt ebenfalls die vollständige Summenzählung, selbst wenn nur aktuelle Bestandsartikel angezeigt werden.
- Changed (Home-Assistant-Integration/Panel): In der nativen Einkaufsliste bleibt das `Bestand`-Badge in der rechten Badge-Liste, wird dort aber vor `Menge` und `MHD` als oberstes Badge gerendert.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.11` erhöht.

## [8.0.10] - 2026-03-22
- Fix (Home-Assistant-Integration/Panel): Im nativen Lager-Tab blendet das MHD-Badge in den Swipe-Karten sein sichtbares `MHD`-Präfix jetzt ebenfalls aus und zeigt nur noch den Datumswert an.
- Added (Tests/Frontend): Ein nativer Storage-Swipe-Regressionstest sichert jetzt die versteckte MHD-Badge-Beschriftung für Lager-Karten ab.
- Changed (Home-Assistant-Integration/Panel): In der nativen Einkaufsliste rendert das `Bestand`-Badge jetzt als Haupt-Badge direkt unter dem Produkttitel statt in der rechten Badge-Spalte, damit der Status ganz oben im Listen-Eintrag sichtbar ist.
- Fix (Home-Assistant-Integration/Panel): Wenn im nativen Dashboard ein Modal geöffnet ist, wird der Hintergrund-Scroll jetzt auf Shell- und Dokument-Ebene gesperrt; Scroll-Gesten bleiben dadurch im Modal statt wieder auf der Hauptseite zu landen.
- Fix (Home-Assistant-Integration/Panel): Im nativen `storage`-/`Lager`-Tab sitzt das Badge `Im Bestand` bzw. `Nicht im Bestand` jetzt rechts in derselben Badge-Spalte wie `Menge` und `MHD`; innerhalb der Badge-Liste wird der Status zuerst angezeigt.
- Added (Tests/Frontend): Shared-Shopping-UI-Regressionstests decken jetzt auch eine konfigurierbare Badge-Reihenfolge für rechte Badge-Spalten ab.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.10` erhöht.

## [8.0.9] - 2026-03-22
- Changed (Home-Assistant-Integration/Panel): Die Bottom-Bar des nativen Dashboards nutzt im Desktop-View jetzt dieselbe maximale Breite wie die zentrierte Content-Shell, sodass Navigation und Inhalt bündig auf derselben Achse sitzen.
- Fix (Home-Assistant-Integration/Panel): Die native Bottom-Bar ersetzt ihre Tab-Buttons nicht mehr bei jedem Status-/Polling-Update, sondern synchronisiert nur noch den aktiven Tab-Zustand; Hover- und Klick-Interaktionen bleiben dadurch im Dashboard stabiler.
- Fix (Home-Assistant-Integration/Panel): Die Tab-Buttons der nativen Bottom-Bar heben sich bei Hover/Fokus nicht mehr per `translateY(...)` an, wodurch das springende Verhalten mit Mauszeiger entfällt.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.9` erhöht.

## [8.0.8] - 2026-03-22
- Changed (Home-Assistant-Integration/Panel): Der native `storage`-/`Lager`-Tab rendert seine Swipe-Einträge jetzt mit derselben Shared-Shopping-Kartenstruktur wie die native Einkaufsliste; dadurch übernehmen Lager-Items die kompaktere Badge-/Detail-Anordnung und das Styling der nativen Einkaufsliste.
- Changed (Home-Assistant-Integration/Panel): Im Lager-Swipe-Eintrag entfällt der separate `Löschen`-Button; Löschen bleibt im Modal verfügbar, während `Im Bestand` bzw. `Nicht im Bestand` als oberstes Status-Badge direkt unter dem Produkttitel erscheint.
- Added (Tests/Frontend): Shared-UI- und Storage-Swipe-Regressionstests decken jetzt das konfigurierbare Haupt-Badge sowie das vereinheitlichte Lager-Listenmarkup ohne Inline-Löschbutton ab.
- Fix (Home-Assistant-Integration/Panel): In der nativen Einkaufsliste sitzt das `Bestand`-Badge wieder oben rechts bei den übrigen Badges; auf mobilen Viewports bleibt die rechte Badge-Spalte jetzt zweispaltig und Badges umbrechen nicht mehr unter den Hauptinhalt.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.8` erhöht.

## [8.0.7] - 2026-03-22
- Fix (Backend/Startup): `jinja2` ist wieder als explizite Python-Dependency eingetragen, damit `starlette.templating.Jinja2Templates` beim App-Start ohne Flask-Transitivabhängigkeit verfügbar ist.
- Fix (Home-Assistant-Integration/Sensoren): `EntityCategory` wird jetzt aus `homeassistant.const` importiert, damit Sensor-Tests und aktuelle Home-Assistant-Versionen denselben Importpfad nutzen.
- Fix (Home-Assistant-Integration/Panel): Das native Shopping-Panel übergibt wieder `stockBadgePlacement: 'main'`, sodass der bestehende Swipe-Regressionstest wieder mit der Implementierung übereinstimmt.
- Changed (Dependencies): Entfernt ungenutzte Flask-Dependency aus den Python-Requirements; das Backend bleibt FastAPI-basiert.
- Changed (Dokumentation): README und `DOCS.md` dokumentieren jetzt das verschachtelte Add-on-Schema, das aktuelle Sidebar-Icon sowie den vollständigen lokalen Prüfablauf.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.7` erhöht.

## [8.0.6] - 2026-03-22
- Changed (Home-Assistant-Integration/Panel): Das native Dashboard leitet seine Abstände und Card-Surfaces jetzt aus den Home-Assistant-Theme-Variablen für `ha-card` ab, damit Shell, Karten, Suchflächen, Listen, Detail-Boxen und Bottom-Bar denselben spacing-/theme-nahen Rhythmus wie andere HA-Oberflächen übernehmen.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.6` erhöht.
- Test: `node --test tests/frontend/test_panel_shell_rendering.mjs`, `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `8.0.6` erhöht.

## [8.0.4] - 2026-03-22
- Changed (Home-Assistant-Integration/Panel): Die native Bottom-Bar ist jetzt auch im Dashboard selbst sauber zentriert, statt sich am Viewport asymmetrisch auszurichten.
- Changed (Home-Assistant-Integration/Panel): Auf mobilen Viewports rendert die Bottom-Bar ihre Tab-Links jetzt als kompakte, horizontal scrollbare Pills statt als umbrechende Liste; Desktop bleibt unverändert.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.4` erhöht.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `node --test tests/frontend/test_panel_shell_rendering.mjs`, `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `8.0.4` erhöht.

## [8.0.3] - 2026-03-22
- Changed (Home-Assistant-Integration/Panel): Das native Storage-Bearbeiten-Modal übernimmt wieder die Legacy-Reihenfolge für Menge, MHD, Lagerort und die fünf Nährwertfelder; beim Öffnen werden zunächst Lagerdaten gesetzt und anschließend detaillierte Produkt-Nährwerte per `fetchProductNutrition(...)` nachgeladen.
- Added (Tests/Frontend): Zusätzliche Frontend-Regressionstests decken Rendering, Initialzustand, Volatile-State-Sync sowie den Save-Flow der neuen Storage-Nährwertfelder ab.
- Changed (Home-Assistant-Integration/Panel): Das native Dashboard nutzt im Desktop-View jetzt eine zentrierte Shell mit maximal halber Viewport-Breite bzw. Legacy-ähnlichen 960px, sodass der Inhalt wieder näher am bisherigen Legacy-Dashboard sitzt.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.3` erhöht.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/dashboard-api-client.js`, `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `node --test tests/frontend/test_dashboard_api_client.mjs tests/frontend/test_panel_shell_rendering.mjs tests/frontend/test_storage_edit_nutrition_fields.mjs`, `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py tests/unit/test_panel.py`; Versionsstände auf `8.0.3` erhöht.

## [8.0.2] - 2026-03-22
- Fix (Home-Assistant-Integration/Panel): In der nativen Einkaufsliste entfällt das sichtbare `MHD`-Präfix im MHD-Badge; gleichzeitig verschwindet das `Offen`-Badge und `Bestand` sitzt wieder in der rechten Badge-Spalte an dessen Stelle.
- Changed (Home-Assistant-Integration/Panel): Mobile Shopping-Karten im nativen Dashboard wurden kompakter abgestimmt (kleinere Abstände, Thumbnails, Badge- und Textgrößen), damit die Einkaufsliste auf Handybildschirmen weniger überladen wirkt.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.2` erhöht.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/shopping-ui.js`, `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `node --test tests/frontend/test_shopping_ui_shared.mjs tests/frontend/test_panel_shell_rendering.mjs`, `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `8.0.2` erhöht.

## [8.0.1] - 2026-03-22
- Fix (Home-Assistant-Integration/Panel): In der nativen Einkaufsliste erscheint das `Bestand`-Badge wieder unter Produktname bzw. Notiz statt in der rechten Badge-Spalte, damit die Karten näher am früheren Layout bleiben.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.1` erhöht.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/shopping-ui.js`, `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `node --test tests/frontend/test_shopping_ui_shared.mjs tests/frontend/test_native_shopping_swipe.mjs`, `pytest tests/unit/test_panel.py tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `8.0.1` erhöht.

## [8.0.0] - 2026-03-22
- Changed (Home-Assistant-Integration/Panel): Das native Dashboard verwendet jetzt Home-Assistant-nähere Navigationsmuster mit `mdi`-Icons statt Emoji-Tabs, einer mit dem Sidebar-Icon synchronen Topbar sowie expliziten `tablist`-/`tab`-/`tabpanel`-ARIA-Beziehungen für Shopping, Rezepte, Lager und den Fallback-Tab.
- Changed (Home-Assistant-Integration/Panel): Fokuszustände folgen im nativen Panel jetzt klarer den HA-Bedienmustern; die Floating-Navigation bleibt visuell erhalten, ist aber semantisch und per Tastatur sauberer angebunden.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.0` erhöht.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `node --test tests/frontend/test_panel_shell_rendering.mjs`, `pytest tests/unit/test_panel.py tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `8.0.0` erhöht.

## [7.4.40]
- Fix (Home-Assistant-Integration/Panel): Die HA-Option `dashboard_polling_interval_seconds` erlaubt jetzt bewusst den Wert `0`, der das automatische Shopping-Polling im nativen Panel komplett deaktiviert, ohne manuelle Refreshes oder Listen-Reloads nach Such-/Mutationsaktionen zu verhindern.
- Changed (Home-Assistant-Integration/Panel): Die native Panel-Konfiguration reicht das Shopping-Polling-Intervall jetzt explizit an das Frontend weiter; `0` bedeutet deaktiviert, positive Werte bleiben Sekundenintervalle.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `7.4.40` erhöht.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `node --test tests/frontend/test_panel_shell_rendering.mjs`, `pytest tests/unit/test_config_flow.py tests/unit/test_panel.py tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.40` erhöht.

## [7.4.39]
- Changed (Home-Assistant-Integration/Panel): Der native `storage`-Tab zeigt `Menge`, `MHD` und `Lagerort` in der Swipe-Liste jetzt als Shopping-ähnliche Badges; der Löschen-CTA wandert aus dem Listeneintrag in das Produkt-bearbeiten-Modal.
- Added (Home-Assistant-Integration/Panel): Das Produkt-bearbeiten-Modal im nativen `storage`-Tab zeigt jetzt ein gleich großes Produktbild sowie einen zusätzlichen CTA zum Löschen des Produktbilds.
- Fix (Home-Assistant-Integration/Panel): Das native Shopping-Polling pausiert jetzt auch bei verborgenem Dokument analog zum Legacy-Dashboard, startet bei `visibilitychange` auf sichtbar wieder und lädt die Einkaufsliste dabei einmalig per Silent-Refresh nach, ohne bestehende Pausen durch Detail-, MHD-, Scanner-Modale oder `viewState.editing` zu umgehen.
- Changed (Home-Assistant-Integration/Panel): Die Swipe-Karten in `shopping` und `storage` nutzen jetzt denselben dreispaltigen Aufbau `Bild | Name/Notiz/Lagerort | Buttons/Badges/Info`, damit die Tab-Ansichten konsistenter bleiben und optionale Notizen in der Einkaufsliste nur noch bei Bedarf angezeigt werden.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `7.4.39` erhöht.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `node --test tests/frontend/test_panel_shell_rendering.mjs`, `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.39` erhöht.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/shopping-ui.js`, `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `node --test tests/frontend/test_shopping_ui_shared.mjs tests/frontend/test_native_shopping_swipe.mjs`, `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.39` erhöht.

## [7.4.38]
- Changed (Home-Assistant-Integration/Panel): Die Swipe-Items im nativen Shopping-Such-Tab gruppieren `Menge`, `MHD` und `Bestand` jetzt rechts direkt unter dem `Offen`-Badge; der `Lagerort` erscheint stattdessen als kompaktes Badge unter der Notiz statt als volle Kontextzeile.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `7.4.38` erhöht.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/shopping-ui.js`, `node --test tests/frontend/test_shopping_ui_shared.mjs tests/frontend/test_native_shopping_swipe.mjs`, `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.38` erhöht.

## [7.4.37]
- Fix (Home-Assistant-Integration/Panel): Die nativen `recipes`-, `storage`- und Modal-Komponenten überspringen bei reinen Feldwert-Updates jetzt vollständige `innerHTML`-Re-Renders und behalten dadurch Fokus, Cursorposition sowie geöffnete Auswahl-/`details`-Listen spürbar stabiler – analog zur Shopping-Suche im nativen Panel.
- Fix (Dashboard/Legacy, Home-Assistant-Integration/Panel): Die geteilte Shopping-Card-CSS hält `shopping-item-card--legacy`-Swipe-Einträge jetzt auch auf schmalen Viewports bewusst im alten horizontalen Legacy-Layout, sodass Bild, Status und Badge-Buttons im Legacy-Dashboard sowie im nativen HA-Panel nicht mehr „durcheinandergewürfelt“ umbrechen.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `7.4.37` erhöht.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `node --test tests/frontend/test_panel_shell_rendering.mjs`, `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.37` erhöht.
- Test: `node --test tests/frontend/test_native_shopping_swipe.mjs`, `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.37` erhöht.

## [7.4.36]
- Fix (Home-Assistant-Integration/Panel): Die nativen `recipes`-, `storage`- und Modal-Renderer stellen nach State-Updates den fokussierten Formular-Controller inklusive Cursorposition wieder her, damit Texteingaben, Zahlenfelder und Checkbox-/Auswahllisten beim Tippen oder Toggle nicht mehr durch Re-Renders den Fokus verlieren.
- Changed (Home-Assistant-Integration/Panel): Die Native-Dashboard-Topbar zeigt keine Tab-Pills und keinen Hinweistext zur Panel-URL bzw. zum Sidebar-Icon mehr, damit der Kopfbereich ruhiger bleibt.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `7.4.36` erhöht.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `node --test tests/frontend/test_panel_shell_rendering.mjs`, `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.36` erhöht.

## [7.4.35]
- Changed (Home-Assistant-Integration/Panel): Der native `storage`-Tab rendert Lagerprodukte wieder als vertikale Legacy-Liste mit Swipe-Gesten für Bearbeiten/Verbrauchen statt als Kachel-Grid; Löschen bleibt zusätzlich direkt als Button am Listeneintrag verfügbar.
- Fix (Home-Assistant-Integration/Panel): Die Swipe-Karten in der nativen Einkaufslistenansicht zeigen `MHD` und `Bestand` jetzt nur noch einmal als Badge; die doppelte Wiederholung in der Zusatz-Metazeile entfällt, während optionale Standortinfos erhalten bleiben.
- Fix (Dashboard/Legacy): Die FastAPI-Static-Mounts registrieren `/dashboard-static/panel-frontend` jetzt vor dem allgemeineren `/dashboard-static`, damit Legacy-Imports für `shopping-ui.css`, `shopping-ui.js` und `swipe-interactions.js` hinter Home-Assistant-Ingress nicht mehr im 404-JSON des falschen Mounts landen.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `7.4.35` erhöht.
- Test: `node --test tests/frontend/test_native_shopping_swipe.mjs tests/frontend/test_panel_shell_rendering.mjs`, `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.35` erhöht.
- Test: `node --test tests/frontend/test_shopping_ui_shared.mjs tests/frontend/test_native_shopping_swipe.mjs`, `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.35` erhöht.
- Test: `pytest tests/api/test_dashboard.py tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; zusätzlicher API-Regressionstest deckt die verschachtelten Panel-Frontend-Assets direkt ab.

## [7.4.34]
- Added (Dokumentation/Migration): `docs/legacy-native-panel-mapping.md` definiert jetzt eine klare visuelle Abnahme für „ähnlicher Stil bei gleicher Funktion“ und verankert `dashboard.html` explizit als Referenz für Karten-, Grid-, Spalten-, Modal- und CTA-Parität pro Tab.
- Added (Dokumentation/Migration): Für `shopping`, `recipes`, `storage` und `notifications` gibt es jetzt tab-lokale Vergleichslisten mit Legacy-Komponente, nativer Entsprechung, Funktionsgleichheit, Interaktionsform, visuellem Schwerpunkt und erlaubten HA-Mehrwert-Abweichungen.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `7.4.34` erhöht.
- Test: `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.34` erhöht.

## [7.4.33]
- Refactor (Home-Assistant-Integration/Panel): Das native Panel konsolidiert Polling, Busy-/Statusanzeigen, Modal-Steuerung, Bottom-Tab-Navigation und URL-/History-Sync jetzt über gemeinsame Helfer in `createDashboardStore`, `tab-routing.js`, `GrocyAIDashboardModals` und `GrocyAIScannerBridge`; tab-spezifische Zustandsmodelle liegen für `shopping`, `recipes`, `storage` und `notifications` nun mit festen `loaded`/`loading`/`error`/`empty`/`editing`-Flags vor.
- Changed (Home-Assistant-Integration/Panel): Der Shopping-Scanner bleibt ein tab-fokussiertes Overlay, ist aber jetzt als eigener `shopping.scanner`-Teilbaum gekapselt und blockiert Polling bzw. fremde Tab-Zustände nur noch innerhalb des Shopping-Flows.
- Changed (Home-Assistant-Integration/Panel): Der bisherige `legacy_dashboard_url` wird im Panel nur noch als `legacy_dashboard_emergency_url` für den Notfall-/Fallbackpfad der noch nicht nativ migrierten Benachrichtigungen bereitgestellt.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `7.4.33` erhöht.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/dashboard-store.js`, `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `node --test tests/frontend/test_dashboard_store.mjs tests/frontend/test_tab_routing.mjs tests/frontend/test_panel_api_base_path.mjs`, `pytest tests/unit/test_panel.py tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.33` erhöht.

## [7.4.32]
- Changed (Home-Assistant-Integration/Panel): Der `storage`-Tab ist jetzt nativ migriert und rendert den Lagerbestand als echtes Grid mit Bild, Bestandsinfos, Lagerort, MHD/Metadaten sowie Quick Actions statt als Legacy-Fallback.
- Changed (Home-Assistant-Integration/Panel): Native Storage-Filter übernehmen Textsuche, Toggle „Alle Produkte anzeigen“, manuelles Refresh sowie die Dialog-Flows für Bearbeiten, Lagerort ändern, Verbrauchen und Löschen über die bestehenden Dashboard-Endpunkte.
- Fix (Home-Assistant-Integration/Panel): Die Swipe-Einkaufslistenkarte im nativen Dashboard nutzt jetzt dieselben MHD-/Mengen-Badge-Buttons, dieselbe Legacy-Kartenklasse und dieselben Swipe-Labels wie das Legacy-Dashboard, damit keine doppelten bzw. abweichenden Buttons mehr angezeigt werden.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/dashboard-api-client.js`, `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `node --test tests/frontend/test_dashboard_api_client.mjs tests/frontend/test_panel_shell_rendering.mjs`, `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.32` erhöht.
- Test: `node --test tests/frontend/test_native_shopping_swipe.mjs`, `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.32` erhöht.

## [7.4.31]
- Changed (Home-Assistant-Integration/Panel): Der `recipes`-Tab ist jetzt als erster vollständiger Nicht-Shopping-Tab nativ migriert und rendert Grocy-/KI-Rezeptvorschläge, Lagerstandorte, Produktauswahl, CTA-Aktionen sowie Rezeptdetails/-anlegen ohne Legacy-iframe direkt im HA-Panel.
- Refactor (Home-Assistant-Integration/Panel): Das native Panel nutzt für Rezeptflows jetzt dieselben bestehenden Backend-Endpunkte wie das Legacy-Dashboard (`recipe-suggestions`, `locations`, `stock-products`, `POST /api/dashboard/recipe/{recipe_id}/add-missing`) über den gemeinsamen Panel-API-Client.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `7.4.31` erhöht.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/dashboard-api-client.js`, `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.31` erhöht.

## [7.4.30]
- Refactor (Home-Assistant-Integration/Panel): Neue Shared-Renderer in `panel/frontend/shared-panel-ui.js` extrahieren Kartencontainer, zweispaltige Card-Gruppen, Status-/Empty-/Loading-Karten, Aktionsleisten und Kachel-Grids aus der bestehenden Shopping-UI als wiederverwendbare Bausteine.
- Changed (Home-Assistant-Integration/Panel): Die Tabs `recipes` und `storage` nutzen diese Shared-Bausteine jetzt zuerst für ihre Migrations-/Bridge-Oberflächen und übernehmen dabei Überschriftenhierarchie, Grid-/Kachel-Logik, CTA-Gewichtung sowie Badge-/Meta-Abstände aus `dashboard.html`; Shopping bleibt Referenzimplementierung.
- Changed (Dashboard/UI): Gemeinsame Panel-/Shopping-CSS deckt jetzt zusätzliche Status-Chip-Varianten und Grid-/Card-Group-Regeln für die neuen Shared-Renderer ab.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/shared-panel-ui.js`, `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/shopping-ui.js`, `node --test tests/frontend/test_shared_panel_ui.mjs tests/frontend/test_panel_shell_rendering.mjs tests/frontend/test_shopping_ui_shared.mjs`, `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.30` erhöht.

## [7.4.29]
- Added (Dokumentation/Migration): Neue Mapping-Matrix `docs/legacy-native-panel-mapping.md`, die Legacy-Dashboard und natives Home-Assistant-Panel tabweise für `shopping`, `recipes`, `storage` und `notifications` gegenüberstellt und pro Bereich als Abnahmeliste für die weitere Migration dient.
- Changed (Home-Assistant-Integration/Panel): Nach erfolgreichem Start protokolliert das native Panel jetzt zusätzlich ein `GROCY-AI`-Konsole-Banner mit der aktuellen Integrationsversion `7.4.29` im Browser-Log.
- Fix (Home-Assistant-Integration/Panel): Die gemeinsame Swipe-Logik unterstützt im nativen Dashboard jetzt zusätzlich echte `touchstart`-/`touchmove`-/`touchend`-Events samt Vertikal-Scroll-Erkennung, sodass Wischgesten in mobilen Home-Assistant-WebViews wieder zuverlässig ausgelöst werden.
- Fix (Home-Assistant-Integration/Panel): Native Shopping-Karten und Variantentreffer registrieren jetzt einen gemeinsamen Bild-Fallback, der fehlgeschlagene Produktbild-Requests automatisch auf das Platzhalterbild umstellt; dadurch verschwinden leere bzw. kaputte Bildrahmen im nativen Dashboard.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `7.4.29` erhöht.
- Test: `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.29` erhöht.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/swipe-interactions.js`, `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/shopping-ui.js`, `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `node --test tests/frontend/test_native_shopping_swipe.mjs tests/frontend/test_panel_shell_rendering.mjs tests/frontend/test_shopping_ui_shared.mjs`, `pytest tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.29` erhöht.

## [7.4.28]
- Changed (Home-Assistant-Integration/Panel): Die native Shopping-Liste nutzt jetzt dieselbe Swipe-Interaktion wie das Legacy-Dashboard für Primäraktionen; Tap öffnet Details, ein Swipe nach rechts markiert Einträge als erledigt und ein Swipe nach links löscht sie direkt im HA-Panel.
- Refactor (Dashboard/Migration): Die Swipe-Logik wurde in ein gemeinsames Frontend-Modul `swipe-interactions.js` extrahiert, das sowohl vom Legacy-Dashboard als auch vom nativen Panel verwendet wird.
- Fix (Home-Assistant-Integration/Panel): Das native Shopping-Dashboard überschreibt beim Rendern weder den Shopping-Tab noch die Produktsuche per `innerHTML`; dadurch bleibt die gemountete `<grocy-ai-shopping-search-bar>` im DOM erhalten und das Textfeld zur Produktsuche wird im Integration-Dashboard wieder sichtbar.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/swipe-interactions.js`, `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `node --check grocy_ai_assistant/api/static/dashboard.js`, `node --test tests/frontend/test_native_shopping_swipe.mjs tests/frontend/test_panel_shell_rendering.mjs tests/frontend/test_shopping_ui_shared.mjs`, `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.28` erhöht.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `node --test tests/frontend/test_panel_shell_rendering.mjs`, `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.28` erhöht.

## [7.4.27]
- Fix (Home-Assistant-Integration/Panel): Produktbilder im nativen Shopping-Panel laufen über eine dedizierte öffentliche Home-Assistant-Proxy-Route für `GET /api/dashboard/product-picture`, damit Browser-`<img>`-Requests ohne expliziten Bearer-Header nicht mehr mit `401 Unauthorized` an der HA-Auth scheitern.
- Test: `pytest tests/unit/test_panel.py tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`, `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `node --test tests/frontend/test_panel_shell_rendering.mjs`; Versionsstände auf `7.4.27` erhöht.

## [7.4.26]
- Fix (Home-Assistant-Integration/Panel): Produktbilder im nativen Shopping-Panel verwenden für `/api/dashboard/product-picture` bereits beim ersten Render den konfigurierten Home-Assistant-Proxy-Prefix, auch wenn der Dashboard-API-Client noch nicht initialisiert ist; dadurch laufen Thumbnail-Requests nicht mehr versehentlich direkt gegen Home Assistant unter `/api/dashboard/...` und enden nicht mehr in `404 Not Found`.
- Test: `node --test tests/frontend/test_panel_shell_rendering.mjs`, `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.26` erhöht.

## [7.4.25]
- Fix (Home-Assistant-Integration/Panel): `shopping-search-controller.js` enthält in `createDefaultTimerApi()` kein fehlerhaft zusammengeführtes Zwischen-`return` mehr, sodass das Modul wieder ohne `Unexpected identifier 'setTimeoutImpl'` lädt und Browser-/Test-Timer korrekt aufgelöst werden.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/shopping-search-controller.js`, `node --test tests/frontend/test_shopping_search_controller.mjs tests/frontend/shopping_search_controller.test.mjs`, `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.25` erhöht.

## [7.4.24]
- Fix (Home-Assistant-Integration/Panel): Das native Panel-Frontend deklariert `escapeHtml` und `formatAmount` nicht mehr doppelt in `grocy-ai-dashboard.js`, sondern nutzt ausschließlich die Imports aus `shopping-ui.js`; dadurch lädt das Modul wieder ohne `Identifier 'escapeHtml' has already been declared`.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `node --test tests/frontend/test_panel_shell_rendering.mjs`, `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.24` erhöht.

## [7.4.22]
- Changed (Dashboard/Migration): Die Shopping-UI für Produktsuche, Variantenkarten und Einkaufslisten-Items basiert jetzt auf einem gemeinsamen Frontend-Baustein `shopping-ui.js`/`shopping-ui.css`, den sowohl das Legacy-Dashboard als auch das native Home-Assistant-Panel verwenden.
- Changed (Dashboard/UI): Das native Shopping-Panel übernimmt damit den Kartenaufbau der Legacy-Einkaufsliste inklusive Variantencard-Struktur, Badge-/Statusdarstellung sowie Bestands- und MHD-Kontext; Navigation/Auth/Container bleiben weiterhin HA-nativ.
- Changed (API/Static): Das FastAPI-App-Mount stellt die Panel-Frontend-Bausteine zusätzlich unter `/dashboard-static/panel-frontend` bereit, damit das Legacy-Dashboard dieselben UI-Helfer ohne Kopierlogik laden kann.
- Changed (Home-Assistant-Integration/Panel): Die bisherige `GrocyAIScannerBridge` im nativen HA-Panel wurde durch eine echte Scanner-Web-Component ersetzt, die Kamera, Barcode-Erkennung, Bildanalyse und Ergebnisdarstellung ohne Legacy-iframe direkt im Panel rendert.
- Changed (Home-Assistant-Integration/Panel): Scanner-Treffer aus Barcode-Lookup und `POST /api/v1/scan/image` werden jetzt unmittelbar in denselben nativen Search-/Varianten-/Add-to-list-Flow übergeben wie Texteingaben, sodass Varianten, Suchstatus und Listen-Updates konsistent bleiben.
- Changed (Dashboard/Migration): Der native Panel-API-Client unterstützt jetzt die v1-Scanner-Endpunkte für Barcode- und Bildscans; zusätzlich bevorzugt der Shopping-Search-Controller in Browser-Tests die vorhandene `window`-Timer-API.
- Fix (Home-Assistant-Integration/Panel): Die native Shopping-Suche hält Suchfeld und Search-Bar-Host jetzt als statische DOM-Knoten dauerhaft stabil und aktualisiert Status, Attribute sowie Variantenlisten nur noch inkrementell, sodass Debounce-/Varianten-Updates den `shopping-query`-Input nicht mehr per `innerHTML` neu erzeugen.
- Fix (Home-Assistant-Integration/Panel): Der Shopping-Tab rendert seine Search-Bar nicht mehr bei jedem State-Update neu, wodurch Fokus und Cursorposition des Suchfelds auch während `setQuery(...)`- und Variantenlade-Flows erhalten bleiben und reine Status-/Ladeflag-Wechsel keine unnötigen Listen-Re-Renders auslösen.
- Changed (Home-Assistant-Integration/Panel): Die native Shopping-Liste rendert jetzt Produktbilder mit derselben `toImageSource(...)`-Fallback-Logik wie das Legacy-Dashboard, sodass leere/fehlende `picture_url`-Werte auf ein stabiles Platzhalterbild statt auf kaputte Bildrahmen fallen.
- Changed (Home-Assistant-Integration/Panel): Die Variantenkarten der nativen Shopping-Suche zeigen nun ebenfalls Produktbilder; die Panel-CSS übernimmt Größen, Seitenverhältnis, Objektanpassung und Abstände analog zur Legacy-Optik.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/shopping-ui.js`, `node --check grocy_ai_assistant/api/static/dashboard.js`, `node --test tests/frontend/test_shopping_ui_shared.mjs`, `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.22` erhöht.
- Test: `node --test tests/frontend/test_dashboard_api_client.mjs tests/frontend/test_panel_api_base_path.mjs tests/frontend/test_panel_shell_rendering.mjs tests/frontend/test_shopping_search_controller.mjs`, `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `pytest tests/unit/test_panel.py tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.22` erhöht.
- Test: Frontend-Regressionstests sichern jetzt Fokus-/Cursor-Stabilität für Query- und Varianten-Updates ab (`node --test tests/frontend/test_shopping_search_focus_retention.mjs tests/frontend/shopping_search_controller.test.mjs tests/frontend/test_shopping_search_controller.mjs`, `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`); Versionsstände auf `7.4.22` erhöht.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`; Versionsstand der Integration auf `7.4.22` erhöht.

## [7.4.21]
- Fix (Home-Assistant-Integration/Panel): Der native Dashboard-API-Client sendet Requests an `/api/grocy_ai_assistant/dashboard-proxy` jetzt zusätzlich mit dem aktuellen Home-Assistant-Bearer-Token aus dem Frontend-Kontext, sodass HA-geschützte Proxy-Aufrufe wie die Einkaufsliste im nativen Panel nicht mehr mit `401 Unauthorized` abgewiesen werden.
- Test: `node --test tests/frontend/test_dashboard_api_client.mjs tests/frontend/test_panel_api_base_path.mjs tests/frontend/test_panel_shell_rendering.mjs`, `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `pytest tests/unit/test_panel.py tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.21` erhöht.

## [7.4.20]
- Fix (Home-Assistant-Integration/Panel): Das native Dashboard nutzt für Shopping-Requests jetzt einen Home-Assistant-authentifizierten Proxy unter `/api/grocy_ai_assistant/dashboard-proxy`, statt im Browser privilegierte Supervisor-/Ingress-Session-Endpunkte aufzurufen; dadurch entfallen die `401 Unauthorized`-Fehler von `hassio/ingress/session`.
- Fix (Home-Assistant-Integration/Panel): Der Proxy reicht sowohl Dashboard-API-Aufrufe als auch die Legacy-Dashboard-HTML-/Asset-Routen an das Add-on weiter und setzt dabei den passenden Prefix-Header, sodass native Requests und Legacy-Fallbacks denselben stabilen HA-Pfad verwenden.
- Test: `node --test tests/frontend/test_panel_api_base_path.mjs tests/frontend/test_panel_shell_rendering.mjs`, `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `pytest tests/unit/test_panel.py tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.20` erhöht.

## [7.4.19]
- Fix (Home-Assistant-Integration/Panel): Das native Dashboard fordert seinen echten Home-Assistant-Ingress-Sessionpfad jetzt bei Bedarf per `hassio/ingress/session` an, statt API-Aufrufe auf den statischen Platzhalter `/api/hassio_ingress/grocy_ai_assistant/` zu schicken, sodass Shopping-Requests im nativen Panel nicht mehr mit `503 Service Unavailable` scheitern.
- Fix (Home-Assistant-Integration/Panel): Legacy-Bridge-Tabs und `open-legacy-dashboard` verwenden denselben aufgelösten Ingress-Pfad wie die nativen Shopping-Requests, damit auch Übergangsbereiche zuverlässig im aktiven HA-Kontext öffnen.
- Test: `node --test tests/frontend/test_panel_api_base_path.mjs`, `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `pytest tests/unit/test_addon_config_yaml.py tests/unit/test_settings_versions.py`; Versionsstände auf `7.4.19` erhöht.

## [7.4.18]
- Fix (Home-Assistant-Integration/Panel): Das native Dashboard baut seine Shadow-DOM-Shell jetzt deterministisch vor jedem State-Render auf und bricht bei unvollständigen Child-Elementen defensiv ab, damit frühe `hass`-/`route`-Updates nicht mehr mit `Cannot set properties of null (setting 'viewModel')` in `_renderState(...)` abbrechen.
- Test: `node --test tests/frontend/test_panel_shell_rendering.mjs`, `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `pytest tests/unit/test_addon_config_yaml.py`; Versionsstände auf `7.4.18` erhöht.

## [7.4.17]
- Fix (Home-Assistant-Integration/Panel): Die native Panel-Registrierung entfernt einen vorhandenen Sidebar-Eintrag jetzt nur noch nach einer erfolgreichen Vorregistrierung, sodass Home Assistant beim ersten Laden kein `Removing unknown panel grocy-ai` mehr ins Frontend-Log schreibt.
- Fix (Home-Assistant-Integration/Panel): Die Registrierung der nativen Panel-Webcomponents läuft jetzt über einen robusten `registerCustomElement(...)`-Helper mit DOMException-Fallback, damit Registry-spezifische Reload-/Reuse-Szenarien keine Folgefehler oder irreführenden Sourcemap-404s mehr auslösen.
- Test: `pytest tests/unit/test_panel.py tests/unit/test_addon_config_yaml.py`, `ruff check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel.py tests/unit/test_panel.py tests/unit/test_addon_config_yaml.py`; Versionsstände auf `7.4.17` erhöht.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `pytest tests/unit/test_addon_config_yaml.py`; Versionsstände auf `7.4.17` erhöht.

## [7.4.16]
- Fix (Home-Assistant-Integration/Panel): Die Legacy-Bridge-Tabs für Rezepte, Lager und Benachrichtigungen nutzen jetzt eigene Konstruktoren statt denselben `GrocyAILegacyBridgeTab`, damit Home Assistants `CustomElementRegistry` keine `constructor has already been used with this registry`-Exception mehr wirft.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `pytest tests/unit/test_addon_config_yaml.py`; Versionsstände auf `7.4.16` erhöht.

## [7.4.15]
- Fix (Home-Assistant-Integration/Panel): Der fehlerhaft zusammengeführte `_switchTab(...)`-Block im nativen Panel-Frontend wurde bereinigt, sodass `grocy-ai-dashboard.js` wieder gültiges JavaScript lädt und Tab-Wechsel/URL-Sync stabil funktionieren.
- Test: `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`, `pytest tests/unit/test_addon_config_yaml.py`; Versionsstände auf `7.4.15` erhöht.

## [7.4.14]
- Fix (Home-Assistant-Integration/Panel): Die native Panel-Registrierung wartet `async_register_panel(...)` jetzt korrekt ab, damit Home Assistant keinen `RuntimeWarning: coroutine was never awaited` mehr für `panel.py` protokolliert.
- Test: `pytest tests/unit/test_panel.py tests/unit/test_addon_config_yaml.py`, `ruff check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel.py tests/unit/test_panel.py`; Versionsstände auf `7.4.14` erhöht.

## [7.4.13]
- Changed (Home-Assistant-Integration/Panel): Die Konfigurationsoption `panel_url` entfällt aus Config- und Options-Flow; das Dashboard hängt sich stattdessen immer automatisch als natives Home-Assistant-Panel auf dem festen Pfad `/grocy-ai` in die Seitenleiste ein.
- Changed (Home-Assistant-Integration/Panel): Die Panel-Registrierung verwendet intern nur noch den bekannten Ingress-Fallback für Legacy-Abschnitte und ignoriert keine benutzerdefinierte Panel-URL mehr.
- Test: `pytest tests/unit/test_panel.py tests/unit/test_addon_config_yaml.py`; Versionsstände auf `7.4.13` erhöht.

## [7.4.12]
- Fix (Dashboard/Legacy): Die versehentlich entfernten Status-Helper `getShoppingStatusElement()` und `getRecipeStatusElement()` sind wieder vorhanden, damit Tab-Wechsel, Topbar-Status-Sync und das Laden der Einkaufsliste im Legacy-Dashboard nicht mehr mit `ReferenceError` abbrechen.
- Test: `node --test tests/frontend/test_legacy_dashboard_status_helpers.mjs`, `node --check grocy_ai_assistant/api/static/dashboard.js`; Versionsstände auf `7.4.12` erhöht.

## [7.4.11]
- Changed (Dashboard/UI): Die Variantenanzeige im Legacy-Dashboard rendert Treffer jetzt über die native Web-Component `<grocy-variant-results>` mit reaktiven Properties für Varianten, Menge sowie Lade-/Leerzustand statt HTML-String-Zusammenbau.
- Changed (Dashboard/UI): Variantenauswahl läuft jetzt über explizite `variant-select`-Komponenten-Events; das bestehende Quellverhalten für `grocy`, `ai` und `input` bleibt dabei unverändert.
- Changed (Home-Assistant-Integration/Panel): Die native Shopping-Suche rendert jetzt als zweistufige Search-Bar mit expliziten UI-Zuständen für leer, tippt, lädt Vorschläge, Vorschläge sichtbar, Submit und Fehler; Statusmeldungen wie „Prüfe Produkt…“ oder „Füge Produkt hinzu…“ werden reaktiv direkt aus dem Search-State angezeigt.
- Changed (Dashboard/Migration): Live-Vorschläge aus `loadVariants()` erscheinen in der nativen HA-Oberfläche direkt unter dem Eingabefeld; Variantenauswahl übernimmt weiterhin die bestehende `confirmVariant(...)`-/`searchSuggestedProduct(...)`-Logik inklusive mengenpräfixierter Suche wie `2 Hafermilch`.
- Changed (Home-Assistant-Integration/Panel): Die native Shopping-Suche übernimmt jetzt explizit das Debounce- und Antwort-Reihenfolgemodell der Legacy-Suche, leert Varianten bei leerer Eingabe sofort und verhindert UI-Rücksprünge durch veraltete Antworten auch während eines laufenden Enter-Submits.
- Test: `node --check grocy_ai_assistant/api/static/dashboard.js`; Versionsstände auf `7.4.11` erhöht.
- Test: Frontend-Checks für Search-Controller und Panel ergänzt bzw. aktualisiert (`node --test tests/frontend/test_shopping_search_controller.mjs`, `node --check ...`); Versionsstände auf `7.4.11` erhöht.
- Test: Neue Frontend-Tests decken schnelles Tippen, leere Eingaben, veraltete Antworten und Enter während noch ladender Variantenanfragen ab; Versionsstände auf `7.4.11` erhöht.

## [7.4.10]
- Added (Home-Assistant-Integration/Panel): Der native Panel-Pfad `/grocy-ai` wird jetzt explizit an das Frontend durchgereicht, in README/DOCS dokumentiert und per Lovelace-/Deep-Link-Beispielen für Home-Assistant-Dashboards beschrieben.
- Changed (Home-Assistant-Integration/Panel): Das native Dashboard unterstützt jetzt Tab-Deep-Links über `/grocy-ai?tab=...`, `#tab=...` und Pfadsegmente wie `/grocy-ai/recipes`; die Topbar zeigt dazu passende Schnelllinks und den finalen Panel-Pfad an.
- Changed (Home-Assistant-Integration/Panel): Das native Dashboard liest den initialen Bereich jetzt stabil über `?tab=` oder einen Routenabschnitt (`/grocy-ai/<tab>`) und synchronisiert Tab-Wechsel per History-API zurück in die URL, inklusive Fallback auf `shopping`.
- Changed (Home-Assistant-Integration/Panel): Die Integration registriert das native Dashboard jetzt zentral als echtes Home-Assistant-Panel mit festem Slug `grocy-ai`, Sidebar-Metadaten und statischer Frontend-Route statt auf Ingress-/iframe-URLs in der Registrierung zu fokussieren.
- Changed (Home-Assistant-Integration/Panel): Setup und Unload des Panels laufen nun über dedizierte `panel.py`-Hilfen mit Referenzzählung, damit der Sidebar-Eintrag beim Laden automatisch erscheint und beim letzten Entladen sauber entfernt wird.
- Changed (Home-Assistant-Integration/Panel): Die native Shopping-Suche nutzt jetzt einen UI-unabhängigen Search-Controller mit reaktivem Store für `query`, erkannte Mengenpräfixe, Varianten, Lade-/Submit-Status sowie fachliche Status- und Fehlermeldungen.
- Changed (Dashboard/Migration): Die bestehende Suchlogik aus `dashboard.js` wurde für die native HA-UI als klarer State-Flow `idle -> typing -> loading_variants -> variants_ready -> submitting -> success/error` übernommen; Variantenauswahl, KI-/Input-Vorschläge und die bestehenden `/api/dashboard/...`-Endpoints bleiben unverändert.
- Changed (Dashboard/Legacy): Mengenpräfix-Parsing und Clear-Button-Regel der Legacy-Suche sind in ein kleines Hilfsmodul ausgelagert, damit die fachlichen Suchregeln außerhalb von `dashboard.js` wiederverwendbar bleiben.
- Test: `tests/unit/test_panel.py`, `tests/unit/test_addon_config_yaml.py` und `node --check grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js`; Versionsstände auf `7.4.10` erhöht.
- Test: Neue Frontend-Unit-Tests decken direkte Aufrufe wie `.../grocy-ai?tab=storage` und `.../grocy-ai?tab=notifications` sowie den URL-Aufbau für Browser-Navigation ab; Versionsstände auf `7.4.10` erhöht.
- Test: `tests/unit/test_panel.py` prüft jetzt Panel-Metadaten, die registrierte Modul-Route sowie das Entfernen des Sidebar-Eintrags; Versionsstände wurden auf `7.4.10` erhöht.
- Test: `node --check` für das Legacy-Dashboard, den nativen HA-Panel-Code und den neuen Search-Controller ausgeführt; relevante Unit-Tests sowie Versionsstände auf `7.4.10` aktualisiert.

## [7.4.9]
- Changed (Dashboard/UI): Topbar, Tabs, Kartencontainer, Dialoge sowie Formular- und Statusflächen des Legacy-Dashboards orientieren sich jetzt an Home-Assistant-Surface-, Button- und Feldmustern statt an eigenständigem Glassmorphism-/Gradient-Styling.
- Changed (Dashboard/Theme): Das Dashboard nutzt nur noch die vom Home-Assistant-Parent synchronisierten Theme-Variablen; das visuelle Theme-Badge und die Beobachtung von `data-theme` entfallen zugunsten HA-nativer Variablen-Mappings.
- Test: `node --check` für das Dashboard-Skript ausgeführt und Versionsstände für Add-on und Integration auf `7.4.9` erhöht.

## [7.4.8]
- Changed (Home-Assistant-Integration/Panel): Das native Panel rendert das Dashboard jetzt in fachlich getrennten Web-Komponenten für Shopping, Rezepte, Lager, Benachrichtigungen, Modals und Scanner, statt nur eine statische Platzhalter-Seite anzuzeigen.
- Changed (Dashboard/Migration): Die Shopping-Ansicht läuft bereits nativ über einen reaktiven Store inklusive Ladezuständen, Statusmeldungen, Button-Aktionen, Debounce-Suche, Modals und Polling; die übrigen Tabs bleiben tabweise über dedizierte Fallback-Komponenten an das Legacy-Dashboard angebunden.
- Changed (Dashboard/Migration): `dashboard.html` und das alte `dashboard.js` bleiben als Übergangs-/Fallback-Schicht bestehen, bis Rezepte, Lager, Benachrichtigungen und Scanner vollständig nativ gerendert werden.
- Test: Native Panel-Module per `node --check` geprüft und relevante Python-Unit-Tests für Panel- sowie Versionsmetadaten ausgeführt; Versionsstände auf `7.4.8` erhöht.

## [7.4.7]
- Changed (Home-Assistant-Integration/Panel): `custom_components/grocy_ai_assistant/panel.py` registriert das Sidebar-Panel jetzt nativ über ein eigenes Frontend-Modul statt über ein `iframe`-Panel.
- Added (Home-Assistant-Integration/Panel): Neues Frontend-Bundle unter `custom_components/grocy_ai_assistant/panel/frontend/` rendert eine native Home-Assistant-Ansicht und zeigt dabei `hass`-, Routing- und Theme-Kontext direkt im Modul an.
- Test: `tests/unit/test_panel.py` prüft nun die Registrierung des nativen Panel-Moduls samt statischem Bundle-Pfad; Versionsmetadaten wurden auf `7.4.7` erhöht.

## [7.4.6]
- Fix (API/Ingress): Interne Add-on-Hostnamen ohne DNS-Suffix wie `local-grocy-ai-assistant` oder `grocy-ai-assistant` werden nicht mehr fälschlich als externe Hosts behandelt, sodass `/api/v1/...` aus Home Assistant nicht mehr per HTTPS-307 umgeleitet wird.
- Fix (API/Rezeptvorschläge): Rezeptvorschläge werden jetzt auch für `soon_expiring_only`-Abfragen gecacht, damit die drei Home-Assistant-Rezeptsensoren nicht bei jedem Poll erneut eine KI-Generierung auslösen.
- Test: API-Tests decken interne Hostnamen ohne Punkt sowie den Cache-Hit für bald ablaufende Rezeptabfragen ab.
- Versionsstände für Add-on und Integration auf `7.4.6` erhöht.
- Changed (Dashboard/Architektur): `dashboard.js` lädt jetzt ein separates API-Client-, DOM- und Store-Modul, sodass die bisherige HTML-Seite dieselbe Logik weiterhin nutzt, die spätere native Home-Assistant-Oberfläche aber auf klar getrennte Zustands-/API-Bausteine aufsetzen kann.
- Changed (Dashboard/State): Zuvor globale Dashboard-Zustände für Tabs, Ladeindikatoren, Polling, Storage-Bearbeitung, Scanner sowie Shopping-Modalfluss wurden in einen zentralen Store verschoben und für die Altseite zusätzlich unter `window.__grocyDashboardState`/`window.__grocyDashboardStore` sichtbar gemacht.
- Changed (Dashboard/API): Alle direkten `/api/dashboard/...`-HTTP-Aufrufe laufen jetzt über `dashboard-api-client.js`, während `dashboard-dom.js` wiederkehrende DOM-Umschaltungen wie Busy-Indikator, Tab-Sichtbarkeit und Scroll-Locking kapselt.
- Test: Dashboard-Frontend per `node --check` für die neuen ES-Module geprüft und Versionsmetadaten auf `7.4.6` angehoben.

## [7.4.5]
- Changed (Dashboard/UI): `dashboard.css` bündelt jetzt wiederkehrende Oberflächenwerte wie Card-Padding, Control-Höhen, Border-Radien, Flächen und Elevation in semantischen Tokens und mappt diese soweit möglich auf Home-Assistant-Variablen mit Fallbacks.
- Changed (Dashboard/UI): Topbar, Karten, Bottom-Tabbar, Formularfelder, Buttons und Modals verwenden nun die neuen Surface-/Spacing-/Radius-Tokens konsistent, damit Light-/Dark-Mode näher am Home-Assistant-Look bleibt.
- Test: Versionsmetadaten und Add-on-Konfiguration wurden auf `7.4.5` angehoben bzw. im Test synchronisiert.
- Changed (Dashboard/Theme): Das iframe-Dashboard übernimmt Home-Assistant-Themefarben jetzt explizit aus dem Parent-Dokument statt auf eine isolierte iframe-Vererbung zu hoffen.
- Changed (Dashboard/UI): Die manuelle Light/Dark-Umschaltung wurde durch einen Home-Assistant-Theme-Statusbadge ersetzt; die Dashboard-CSS nutzt nun HA-nahe Farbvariablen mit Fallbacks.
- Test: API-Tests prüfen jetzt die Theme-Bridge-Metadaten im HTML sowie die neue Theme-Synchronisation in CSS/JavaScript.
- Versionsstände für Add-on und Integration auf `7.4.5` erhöht.

## [7.4.3]
- Changed (Home-Assistant-Integration/Sensoren): Der bisherige Sensor `Grocy AI Top Rezeptvorschlag` wurde in die zwei getrennten Sensoren `Grocy AI Top KI Rezeptvorschlag` und `Grocy AI Top Grocy Rezeptvorschlag` aufgeteilt.
- Changed (Home-Assistant-Integration/Sensoren): Beide neuen Topsensoren zeigen jetzt jeweils nur noch den besten Vorschlag ihrer Quelle an, inklusive quellspezifischer Attributdaten für genau ein Rezept.
- Test: Unit-Tests decken die neue quellspezifische Rezeptauswahl sowie die reduzierten Sensorattribute ab.
- Changed (Home-Assistant-Integration/Geräteregistrierung): Alle Sensoren, Buttons und das Texteingabefeld nutzen jetzt dieselbe `device_info` wie `Grocy AI Response`, damit die Entitäten Home-Assistant-konform gemeinsam unter einem Gerät erscheinen.
- Test: Unit-Tests prüfen die gemeinsame Gerätezurodnung für Sensor-, Button- und Text-Entitäten.
- Versionsstände für Add-on und Integration auf `7.4.3` erhöht.

## [7.4.2]

- Fix (Home-Assistant-Integration): Die interne Add-on-Auflösung nutzt jetzt zusätzlich die Supervisor-API (`/addons` und `/addons/<addon>/info`), um bei GitHub-/Repository-Installationen den tatsächlich vergebenen Add-on-Hostnamen samt Container-IP dynamisch zu ermitteln.
- Fix (Home-Assistant-Integration): Wenn DNS für den Supervisor-gelieferten Hostnamen scheitert, versucht der Add-on-Client anschließend automatisch die vom Supervisor gemeldete Container-IP auf dem Ingress-Port.
- Test: Unit-Tests decken jetzt sowohl die Supervisor-basierte Auflösung eines gehashten Add-on-Hostnamens als auch den IP-Fallback bei DNS-Fehlern ab.
- Versionsstände für Add-on und Integration auf `7.4.2` erhöht.

## [7.4.1]

- Fix (Home-Assistant-Integration): Die Konfigurationsmaske fragt keine manuelle API-Basis-URL mehr ab; die Add-on-Kommunikation wird wieder intern über bekannte Home-Assistant-App-Hostnamen aufgelöst.
- Fix (Home-Assistant-Integration): Loopback-Adressen wie `localhost` oder `127.0.0.1` werden im Add-on-Client automatisch auf interne Add-on-Hostnamen umgebogen, damit bestehende Installationen bei Service-Aufrufen nicht mehr an `localhost:8000` scheitern.
- Test: Unit-Tests decken jetzt sowohl die automatische Loopback-Korrektur als auch den Fallback auf alternative interne Add-on-Hostnamen ab.
- Versionsstände für Add-on und Integration auf `7.4.1` erhöht.

## [7.4.0]

- Changed (API/Maschinenschnittstelle): `/api/v1/...` deckt jetzt auch Einkaufslisten-, Lager-, Rezept- und Barcode-Funktionen ab (`/shopping-list`, `/stock`, `/recipes`, `/barcode/{barcode}`) und bündelt damit die von der Home-Assistant-Integration genutzten Lesezugriffe in einer sauberen Service-API.
- Added (API/Scanner): Neuer Endpoint `GET /api/v1/last-scan` liefert das letzte Ergebnis von `POST /api/v1/scan/image` inklusive Zeitstempel für maschinelle Statusabfragen.
- Changed (Home-Assistant-Integration): `AddonClient` verwendet für Shopping-Liste, Lager, Rezepte und Barcode-Lookups jetzt die neuen `/api/v1/...`-Endpunkte statt Dashboard-Routen.
- Test: API- und Unit-Tests für die neuen v1-Endpunkte sowie die umgestellte Integration ergänzt.
- Versionsstände für Add-on und Integration auf `7.4.0` erhöht.
- Fix (Home-Assistant-Integration/Add-on-Kommunikation): Die Default-API-URL der Integration nutzt jetzt den für lokale Home-Assistant-App-Installationen gültigen DNS-Namen `http://local-grocy-ai-assistant:8000` statt des ungültigen Hostnamens mit Unterstrich.
- Fix (Home-Assistant-Integration/Add-on-Kommunikation): Der Add-on-Client probiert bei Verbindungsfehlern mehrere naheliegende interne Hostnamen aus und liefert anschließend eine konkrete Fehlermeldung mit dem erwarteten Home-Assistant-Hostname-Format.
- Changed (Versioning): Bumped add-on and integration versions to `7.3.3`.

## [7.3.2]

- Fix (Home-Assistant-Integration/Sensoren): Status-, Update-, Einkaufslisten-, Lager- und Rezeptsensoren bleiben jetzt auch dann verfügbar, wenn der erste API-Aufruf des Add-ons mit einer Exception fehlschlägt; stattdessen werden Fallback-Werte wie `Offline`, `Unbekannt`, `0` oder `Keine Vorschläge` gesetzt.
- Test: Zusätzliche Unit-Tests decken Initialfehler für Status-, Update- und Lager-Sensoren ab.
- Versionsstände für Add-on und Integration auf `7.3.2` erhöht.

## [7.3.1]

- Changed (Home-Assistant-Integration): The redundant `grocy_api_key` and `grocy_base_url` fields were removed from the custom integration config and options flow because the integration communicates with Grocy through the backend API service.
- Changed (Versioning): Bumped add-on and integration versions to `7.3.1`.
- Fix (API): `/api/v1/health` und `/api/v1/capabilities` sind jetzt ohne Bearer-Token direkt erreichbar, damit die lokale Add-on-Service-API unter `host:8000/...` für Discovery und Debugging nutzbar ist.
- Test: API-Tests für tokenfreien Zugriff auf `health` und `capabilities` ergänzt.

## [7.3.0]

- Changed (Architektur/Add-on↔Integration): Dedizierte Service-API unter `/api/v1/...` für `health`, `capabilities`, `status`, `scan/image`, `grocy/sync`, `catalog/rebuild` und `notifications/test` ergänzt.
- Changed (Home-Assistant-Integration): Integration nutzt jetzt primär die neue v1-API statt Dashboard-Endpunkten für Status-, Scan- und Sync-Kommunikation.
- Added (Home-Assistant-Integration): Neue Button-Entities zum Katalog-Neuaufbau und zum Auslösen einer Test-Benachrichtigung.
- Changed (Konfiguration): API-Basis-URL und Panel-/Ingress-URL sind in der Integration jetzt getrennt modelliert.
- Test: API- und Client-Tests für die neue v1-Kopplung ergänzt.

## [7.2.33]

- Fix (Produktauswahl/Neu anlegen): Mengen-Badges aus der Varianten-Auswahl werden jetzt auch beim ersten Anlegen eines neuen Produkts zuverlässig auf die Einkaufsliste übernommen, selbst wenn Grocy `product_id` als String zurückliefert.
- Test: API-Test ergänzt, der `force_create` mit Mengenpräfix und String-`product_id` für neu angelegte Einkaufslisteneinträge absichert.

## [7.2.32]
- Fix (Home-Assistant-Integration/Sensoren): Polling-Sensoren für Einkaufslisten-, Lager- und Rezeptdaten bleiben bei API-Fehlern mit Fallback-Werten bzw. zuletzt erfolgreichem Stand verfügbar und markieren Fehler stattdessen in den Attributen `last_update_success`, `last_error` und `http_status`.
- Test: Unit-Tests für Sensor-Fallbacks bei HTTP-Fehlern und Ausnahmen ergänzt.
- Versionsstände für Add-on und Integration auf `7.2.32` erhöht.

## [7.2.31]

### Changed

- Scanner-Popup ergänzt einen Button, der erkannte OpenFoodFacts-/LLaVA-Produkte direkt über den bestehenden Anlegeprozess neu erstellt und zur Einkaufsliste hinzufügt.
- Fix: Der Scanner-Anlegen-Button ist jetzt fest im Popup-Markup verankert und wird dadurch bei erkannten Produkten zuverlässig sichtbar/einblendbar.
- Scanner-Anlage übernimmt erkannte Barcode-/Produktattribute direkt in die Produktbeschreibung und speichert erkannte Barcodes zusätzlich in Grocy, ohne weitere KI-Nachfrage zur Produkterstellung.
- Versionsstände für Add-on und Integration auf `7.2.31` erhöht.

## [7.2.29]

### Changed

- `grocy_ai_assistant/config.yaml` nutzt wieder das ursprüngliche verschachtelte Layout für `grocy`, `ollama`, `scanner` und `cloud_ai`; die YAML-Tests wurden entsprechend auf das gruppierte Schema zurückgestellt.
- Versionsstände für Add-on und Integration auf `7.2.29` erhöht.

## [7.2.28]

### Changed

- Repository arbeitet wieder ausschließlich mit `grocy_ai_assistant/config.yaml`; die versehentlich ergänzte `config.json` wurde entfernt und die zugehörigen Tests/Dokumentationshinweise wurden auf YAML als Single Source of Truth umgestellt.
- Versionsstände für Add-on und Integration auf `7.2.28` erhöht.

## [7.2.27]

### Added

- Home-Assistant-Integration ergänzt neue Sensorsummen für offene Einkaufslisten-Einträge, gesamte Lagerprodukte, bald ablaufende Lagerprodukte sowie Top-Rezeptvorschläge inklusive Variante nur aus bald ablaufenden Produkten.
- Neue Statussensoren für Analyse, Barcode-Lookup und LLaVA-Scanner speichern das letzte Ergebnis inklusive Detailattributen; ergänzende Services für Barcode- und LLaVA-Aufrufe aktualisieren diese Sensoren direkt aus Home Assistant.
- Home-Assistant-Integration ergänzt neue Sensorsummen und Statussensoren; die Add-on-Metadaten bleiben in `grocy_ai_assistant/config.yaml` als zentrale Repository-Konfiguration.

### Changed

- Integrationsversion auf `7.2.27` erhöht und mit Manifest-/Add-on-Metadaten synchronisiert.

## [7.2.26]

### Fixed

- Gruppierte Add-on-Optionen aus dem Home-Assistant-Layout werden jetzt auch nach einer Dateiänderung zuverlässig neu in die Laufzeit-Settings geladen.
- Regressionstests decken jetzt zusätzlich das Nachladen geänderter verschachtelter YAML-Gruppen wie `grocy` und `cloud_ai` über `get_settings()` ab.

## [7.2.24]

### Fixed

- Verschachtelte bekannte Optionswerte aus dem neuen `options.yaml`-Layout werden jetzt auch dann geladen, wenn sie innerhalb zusätzlicher Zwischenblöcke liegen.
- Regressionstests decken jetzt zusätzlich tiefere verschachtelte Gruppen wie `profile.grocy.grocy_api_key` und `profile.cloud_ai.openai_api_key` ab.

## [7.2.23]

### Fixed

- `options.yaml` mit zusätzlichem Top-Level-Block `options:` wird jetzt ebenfalls korrekt entpackt, sodass verschachtelte Werte wie `grocy.grocy_api_key` und `grocy.grocy_base_url` wieder zuverlässig in die Laufzeit-Settings gelangen.
- Beim Speichern bleiben bestehende `options:`-Wrapper und zusätzliche Metadaten in `options.yaml` erhalten.
- Regressionstests decken jetzt sowohl das Laden als auch das Speichern des gewrappten Layouts ab.

## [7.2.22]

### Fixed

- Produktbild- und Lager-Cache starten ohne `grocy_api_key` jetzt ohne Hintergrund-Thread und ohne vermeidbare Warnmeldungen beim App-Start.
- Zusätzliche Unit-Tests decken das threadlose Startverhalten der Caches ohne Grocy-Zugangsdaten ab.

## [7.2.21]

### Fixed

- Add-on-Optionen werden beim Laden jetzt aus dem neuen verschachtelten `options.yaml`-Layout (`grocy`, `ollama`, `scanner`, `cloud_ai`) in das bisherige Laufzeitformat überführt.
- Startup-Flags werden beim automatischen Zurücksetzen wieder im neuen gruppierten `options.yaml`-Layout gespeichert, damit die geänderte Add-on-Struktur konsistent bleibt.
- Tests für Options-Loading und Startup-Flag-Reset auf das neue YAML-Layout erweitert.


## [7.2.20]

### Changed

- `CHANGELOG.md` verschoben.
- Optionen angepasst.
- `config.json` entfernt.
- Translations geändert.

## [7.2.18]

### Changed

- `CHANGELOG.md` auf das Format von Keep a Changelog umgestellt und die bestehenden Einträge in standardisierte Abschnitte einsortiert.
- Add-on-Version in `grocy_ai_assistant/config.json` auf `7.2.18` erhöht.

## [7.2.17]

### Changed

- Pflege: Add-on-Version auf `7.2.17` erhöht.

### Security

- Neu (Add-on-Sicherheit): Eine aktuelle `grocy_ai_assistant/apparmor.txt` ergänzt, die das Home-Assistant-Add-on auf die tatsächlich benötigten Laufzeitpfade (`/app`, `/data`, `/config`, `/tmp`) und Netzwerkzugriffe beschränkt.
- Test: Konfigurationstest ergänzt, der die neue AppArmor-Datei samt Profilnamen und zentralen Dateipfaden absichert.

## [7.2.16]

### Added

- Dokumentation (Add-on): Neue `grocy_ai_assistant/DOCS.md` im Stil aktueller Home-Assistant-Add-ons ergänzt.
- Test: API- und Unit-Tests für Lagerort-Updates im Lager-Popup ergänzt.

### Changed

- UI (Benachrichtigungen): Der Abstand zwischen `Geräteverwaltung` und `Benachrichtigungsregeln` ist jetzt an die übrigen Kartenabstände im Tab angeglichen.
- UI (Suche/Produkt-Popup): Nach dem Button `Speichern` gibt es im Produkt-Popup jetzt zusätzlichen Abstand vor den Detailkarten.
- UI (Lager/Produkt-Popup): Im Bearbeiten-Popup des Lager-Tabs gibt es jetzt direkt nach dem MHD ein Lagerort-Dropdown, sodass der Lagerort im selben Dialog geändert werden kann.
- API (Lager): Das Speichern von Lagerprodukten übernimmt jetzt optional den ausgewählten Lagerort und synchronisiert ihn auf Produkt- sowie Bestandsebene.
- UI (Einkaufsliste): Unter dem letzten Produkt in der Einkaufsliste gibt es jetzt zusätzlichen Abstand, damit der Abschlussbereich luftiger wirkt.
- Pflege: Add-on-Version auf `7.2.16` erhöht.

### Removed

- UI (Bestand bearbeiten): Die nicht bearbeitbare Attributliste mit Produkt-ID, Bestands-ID, Lagerort, Menge und MHD wurde aus dem Produkt-Bearbeiten-Popup entfernt, sodass nur noch die editierbaren Felder angezeigt werden.

### Documentation

- Pflege (Dokumentation): README um Verweis auf die Add-on-Dokumentation erweitert und Versionsstand aktualisiert.

## [7.2.15]

### Changed

- API (Einkaufsliste): Der Reset-Endpoint leert das Einkaufslisten-MHD jetzt statt ein Standarddatum neu zu berechnen.
- Test: Dashboard-API-Test auf das Leeren des MHDs angepasst.
- Pflege: Add-on-Version auf `7.2.15` erhöht.

### Fixed

- Fix (Suche/Einkaufsliste): Der Button `Zurücksetzen` im MHD-Popup entfernt das auf der Einkaufsliste gesetzte Datum jetzt vollständig, sodass wieder `MHD wählen` angezeigt wird.

## [7.2.14]

### Added

- API (Einkaufsliste): Neuer Endpoint `POST /api/dashboard/shopping-list/item/{shopping_list_id}/best-before/reset` zum serverseitigen Zurücksetzen auf das aufgelöste Standard-MHD.
- Test: Dashboard-API-Test für das Zurücksetzen des MHDs in der Einkaufsliste ergänzt.

### Changed

- UI (Suche/Einkaufsliste): Im MHD-Popup der Einkaufsliste gibt es jetzt zusätzlich den Button `Zurücksetzen`, der das MHD eines Eintrags wieder auf den Standardwert setzt.
- Pflege: Add-on-Version auf `7.2.14` erhöht.

## [7.2.13]

### Changed

- Änderung (Konfiguration): Die Repository-Konfiguration liegt jetzt vollständig als `grocy_ai_assistant/config.yaml` vor und spiegelt alle Werte aus `config.json`.
- Test: Konfigurationstests prüfen jetzt die vollständige YAML-Spiegelung von `config.json` nach `config.yaml`.
- Pflege: Add-on-Version auf `7.2.13` erhöht.

### Fixed

- Änderung (App-Defaults): Der Repository-Fallback für Laufzeitoptionen liest jetzt die verschachtelten Default-Werte aus `config.yaml` statt aus einer separaten `options.yaml`.

## [7.2.12]

### Added

- Neu (Konfiguration): Default-App-Optionen liegen jetzt zusätzlich als versionierte `grocy_ai_assistant/options.yaml` im Repository vor.
- Test: Konfigurationstests ergänzt, die sicherstellen, dass `options.yaml` mit den Default-Optionen aus `config.json` synchron bleibt.

### Changed

- Pflege: Add-on-Version auf `7.2.12` erhöht.

### Fixed

- Änderung (App-Konfiguration): Das Laden der Add-on-Optionen nutzt nach `/data/options.yaml` und dem Legacy-Fallback auf `options.json` jetzt auch die Repository-Datei `grocy_ai_assistant/options.yaml`.

## [7.2.11]

### Changed

- Verbesserung (Add-on-Übersetzungen): Die App-Optionen nutzen jetzt vollständige Home-Assistant-Übersetzungen mit `name` und `description` für alle Schema-Felder, einschließlich `dashboard_polling_interval_seconds` und `initial_info_sync`.
- Pflege (Add-on-Konfiguration): Startup-Optionen und die Notification-Zielerkennung berücksichtigen jetzt ebenfalls `options.yaml`.
- Pflege: Add-on-Version auf `7.2.11` erhöht.

### Fixed

- Änderung (Add-on-Konfiguration): Die Laufzeit-Konfiguration wird jetzt primär aus `options.yaml` gelesen und geschrieben; bestehende `options.json`-Dateien bleiben als Legacy-Fallback kompatibel.

## [7.2.9]

### Added

- Test: Startup-Tests ergänzt, die das automatische Zurücksetzen beider Optionen in `options.json` absichern.

### Changed

- Verbesserung (Startup-Optionen): Die einmaligen Startup-Optionen `initial_info_sync` und `generate_missing_product_images_on_startup` werden nach erfolgreichem Abschluss automatisch in der Add-on-Konfiguration wieder deaktiviert.
- Pflege: Add-on-Version auf `7.2.9` erhöht.

## [7.2.8]

### Added

- Test: Dashboard-API-Test ergänzt, der das `sugar`-Feld für Einkaufslisten-Produkte absichert.

### Changed

- Pflege (Frontend): Die Suchzeile nutzt jetzt ein dediziertes Formular, damit der Submit-Pfad ohne separaten Button stabil erhalten bleibt.
- UI (Notify-Tab): Geräte-Gruppen mit nur einem Treffer werden jetzt automatisch in die Gruppe `Sonstige` verschoben, damit die Gruppierung kompakter bleibt.
- Pflege: Add-on-Version auf `7.2.8` erhöht.

### Removed

- UI (Produktsuche): Den Button **"Suchen & hinzufügen"** aus der Suchzeile entfernt; die Produktsuche bleibt per Enter im Eingabefeld sowie über die Variantenauswahl nutzbar.

### Fixed

- Fix (Einkaufsliste/Produkt-Popup): Das Shopping-List-API-Response enthält wieder das Feld `sugar`, sodass Zucker im Produkt-Popup zuverlässig angezeigt wird.

## [7.2.7]

### Changed

- Test: API-Tests für die Variantenauswahl wieder auf die reduzierte Response ohne Nährwertfelder angepasst; Userfield-Tests für das Produkt-Popup bleiben bestehen.
- Pflege: Add-on-Version auf `7.2.7` erhöht.

### Removed

- UI (Produktsuche): Nährwertdetails wieder aus der Variantenauswahl entfernt; die Produktsuche zeigt erneut nur die Produktkarten ohne zusätzliche Nährwertzeile.

### Fixed

- Fix (Einkaufsliste/Produkt-Popup): Nährwertdetails aus den Grocy-Userfields bleiben weiterhin im Produkt-Popup der Einkaufsliste aktiv, inklusive Zucker.

## [7.2.6]

### Added

- Test: API- und Unit-Tests ergänzt, die die Nährwert-Anreicherung für Suchvarianten und Einkaufslisten-Produkte absichern.

### Changed

- UI (Produktsuche): Gefundene Produktvarianten zeigen jetzt zusätzlich Kalorien sowie Nährwert-Userfields (`carbohydrates`, `fat`, `protein`, `sugar`) direkt in der Produktauswahl an.
- UI (Dashboard): `.section-header` erhält `margin-bottom: 0.8rem`, damit die Abschnittsüberschriften konsistent mehr Abstand zum folgenden Inhalt haben.
- Pflege: Add-on-Version auf `7.2.6` erhöht.

### Fixed

- Fix (Einkaufsliste/Produkt-Popup): Das Produktdetail-Popup liest Nährwerte für Einkaufslisten-Einträge jetzt aus den Grocy-Userfields und zeigt dabei auch Zucker an.

## [7.2.5]

### Added

- Logging (Startup/Info-Sync): Zusätzliches Log ergänzt, das die Anzahl "neu geladener" vs. per Delta übersprungener Produkte ausweist.
- Test: API-Startup-Test ergänzt, der das Delta-Verhalten (Skip unveränderter Produkte) absichert.

### Changed

- Verbesserung (Startup/Info-Sync Delta): Für den initialen Info-Sync wird ein lokaler Delta-Status pro Produkt gespeichert. Unveränderte Produkte ohne fehlende Felder werden beim nächsten Lauf übersprungen, statt erneut im Detail geladen zu werden.
- Pflege: Add-on-Version auf `7.2.5` erhöht.

## [7.2.4]

### Changed

- Verbesserung (Startup/Sync): Der initiale Info-Sync wartet jetzt auf den initialen Produktbild-Cache-Sync (mit Timeout), bevor er startet.
- Logging (Startup/Info-Sync): Beim Start wird jetzt geloggt, wie viele Produkte aus Grocy geladen wurden, plus zusätzliche Debug-Logs pro Produktprüfung und Skip-Gründen.
- Test: Startup-Tests um einen Check für das Signalisieren des initialen Bildcache-Refreshs erweitert.
- Pflege: Add-on-Version auf `7.2.4` erhöht.

## [7.2.3]

### Added

- Test: API-Test ergänzt, der die Normalisierung für neu angelegte Produkte absichert.
- Test: Unit-Test für Plural-/Stammwort-Matching in `search_products_by_partial_name` ergänzt.

### Changed

- Verbesserung (Suche/Fuzzy-Match): Die Produktsuche berücksichtigt jetzt einfache Wortstämme und Pluralformen, sodass z. B. `zitronen` auch `Zitrone` und `Zitronensaft` findet.
- Pflege: Add-on-Version auf `7.2.3` erhöht.

### Fixed

- Fix (API/Produkterneuanlage): Namen neuer Produkte werden vor dem Anlegen normalisiert (mehrfache Leerzeichen entfernt) und immer mit großem Anfangsbuchstaben gespeichert.

## [7.2.2]

### Added

- Test: API-Test ergänzt, der den Update-Pfad für nicht vorrätige Produkte (nur `product_id`, ohne `stock_id`) absichert.

### Changed

- UI (Einkaufsliste/Produkt-Popup): Beim Klick auf **Speichern** wird das Produkt-Detail-Popup nach erfolgreichem Speichern der Menge jetzt automatisch geschlossen.
- Pflege: Add-on-Version auf `7.2.2` erhöht.

### Fixed

- Fix (Dashboard/Lager bearbeiten): Das Aktualisieren von Menge und Nährwerten funktioniert jetzt auch für Produkte aus „Alle Produkte anzeigen", selbst wenn dafür noch kein Bestandseintrag existiert.

## [7.2.1]

### Added

- Neu (Konfiguration): Option `initial_info_sync` ergänzt. Wenn aktiviert, wird beim Start ein initialer KI-Info-Sync für bestehende Produkte ausgeführt.
- Neu (Startup-Sync): Produkte mit fehlenden Feldern bei `calories`, Nährwert-Userfields (`carbohydrates`, `fat`, `protein`, `sugar`) oder `default_best_before_days` werden über die KI analysiert und selektiv ergänzt.

### Changed

- Pflege: Add-on-Version auf `7.2.1` erhöht.

## [7.1.107]

### Added

- Test: API-Test ergänzt, der den Suchpfad mit Backend-Verhalten simuliert, bei dem zunächst nur `+1` gesetzt wird, und die Korrektur auf die gewünschte Menge absichert.

### Changed

- Pflege: Add-on-Version auf `7.1.107` erhöht.

### Fixed

- Fix (Dashboard/"Suchen & hinzufügen"): Die serverseitige Mengen-Reconciliation greift jetzt auch im direkten Suchpfad (`/api/dashboard/search`), wenn ein vorhandenes Produkt sofort hinzugefügt wird.
- Fix (Dashboard/"Suchen & hinzufügen"): Auch beim Neuanlegen eines Produkts über die Suche wird die Zielmenge nach dem Add verifiziert und bei Bedarf auf den erwarteten Wert korrigiert.

## [7.1.106]

### Added

- Test: API-Tests ergänzt, die Backend-Verhalten simulieren, bei dem `add-product` nur Menge `1` setzt, und die anschließende Korrektur auf die erwartete Menge prüfen.
- Verbesserung (Dashboard/Produktbilder): Der Bild-Proxy ergänzt für Produktbilder jetzt standardmäßig `force_serve_as=picture`, damit Grocy-Datei-URLs konsistent als Bild ausgeliefert werden (inkl. weiterhin größenabhängigem `best_fit_width`/`best_fit_height`).

### Changed

- Logging: Das Umschreiben von Produktbild-URLs auf den konfigurierten Grocy-Host wurde von INFO auf DEBUG reduziert, um Polling-bedingtes Log-Spam im Normalbetrieb zu vermeiden.
- Test: API-Tests für Produktbild-Proxy-URLs auf den neuen Standard-Queryparameter angepasst.
- UI (Dashboard/Produkt ändern Popup): Produktbilder werden im "Bestand ändern"-Popup jetzt in voller Breite angezeigt, damit Details besser erkennbar sind.
- Pflege: Add-on-Version auf `7.1.106` erhöht.

### Fixed

- Fix (API/Einkaufsliste/Menge): Beim Hinzufügen eines bestehenden Produkts wird die Zielmenge jetzt serverseitig verifiziert und bei Bedarf direkt auf den erwarteten Wert korrigiert. Dadurch greifen Mengenpräfixe (z. B. `2 Backpulver`) auch dann korrekt, wenn Grocy intern nur `+1` verbucht.
- Fix (API/Einkaufsliste/Menge): Der gleiche Korrekturpfad deckt sowohl bestehende als auch neu angelegte Einkaufslisten-Einträge ab.

## [7.1.105]

### Added

- Test: API-Test für bereinigte Erfolgsmeldung bei mengenpräfixiertem Produktnamen ergänzt.

### Changed

- Pflege: Add-on-Version auf `7.1.105` erhöht.

### Fixed

- Fix (Dashboard/Produktvarianten): Beim Hinzufügen bestehender Varianten wird die erkannte Menge jetzt zusätzlich im `product_name`-Präfix an die API übergeben, sodass die Menge serverseitig zuverlässig erkannt und auf die Einkaufsliste übernommen wird.
- Fix (API/Antworttext): Bei mengenpräfixierten Produktnamen wird die Erfolgsmeldung bereinigt (ohne Präfix), z. B. `Apfel wurde zur Einkaufsliste hinzugefügt.` statt `2 Apfel ...`.

## [7.1.104]

### Changed

- Pflege: Add-on-Version auf `7.1.104` erhöht.

### Fixed

- Fix (Dashboard/Produktvarianten): Die erkannte Menge aus dem Suchpräfix wird jetzt auch beim Klick auf KI-/Input-Varianten (Pfad über erneute Produktsuche) korrekt mitgeführt, sodass die Menge zuverlässig auf der Einkaufsliste ankommt.

## [7.1.103]

### Changed

- UI (Dashboard/Produktvarianten): In der Varianten-Auswahl wird bei erkannter Mengenpräfix-Suche ein rundes Mengen-Badge oben rechts auf der Produktkarte angezeigt.
- Pflege: Add-on-Version auf `7.1.103` erhöht.

### Fixed

- Fix (Dashboard/Produktvarianten): Mengenpräfixe in der Suche (z. B. `2 backpulver`) werden bei der Varianten-Auswahl jetzt bis zum Klick mitgeführt, sodass beim Auswählen einer Variante die erkannte Menge korrekt (hier `2`) auf die Einkaufsliste geschrieben wird.

## [7.1.102]

### Changed

- UI (Einkaufsliste/Produkt-Popup): Label `Standardmenge` im Produkt-Popup der Einkaufsliste in `Geschätzte Haltbarkeit` umbenannt.
- Pflege: Add-on-Version auf `7.1.102` erhöht.

## [7.1.101]

### Added

- Test: API-Test ergänzt, der sicherstellt, dass Makro-Nährwerte nicht im `create_product`-Payload landen und korrekt an `update_product_nutrition` übergeben werden.

### Changed

- Pflege: Add-on-Version auf `7.1.101` erhöht.

### Removed

- Bereinigung (Neues Produkt): Doppelte Aufrufe für Nährwert- und `default_best_before_days`-Update nach dem Bild-Upload entfernt.

### Fixed

- Fix (Neues Produkt/Nährwerte): Bei der Neuanlage über `/api/dashboard/search` werden KI-Nährwerte für `carbohydrates`, `fat`, `protein` und `sugar` jetzt konsequent über die Userfield-Logik weitergereicht (`update_product_nutrition` → `/userfields/products/{id}`), statt im Create-Payload mitzuschwimmen.

## [7.1.100]

### Added

- Neu (API): Endpoint `GET /api/dashboard/products/{product_id}/nutrition` ergänzt.
- Test: Unit- und API-Tests für Userfield-Nährwerte und den neuen Nutrition-Endpoint ergänzt/angepasst.

### Changed

- Verbesserung (Dashboard/Produkt ändern Popup): Beim Öffnen des Popups werden Nährwerte zusätzlich über einen dedizierten API-Endpunkt geladen, der die Userfields korrekt aus Grocy einliest. Dadurch werden die Felder im Popup konsistent mit den Grocy-Userfields angezeigt.
- Pflege: Add-on-Version auf `7.1.100` erhöht.

### Fixed

- Fix (API/Grocy/Nährwerte): `update_product_nutrition` nutzt für `carbohydrates`, `fat`, `protein` und `sugar` jetzt ausschließlich den korrekten Userfield-Endpunkt (`PUT /userfields/products/{id}`); der fehlerhafte Erstversuch über das Produkt-Objekt wurde entfernt.

## [7.1.99]

### Added

- Test: Unit-Test ergänzt, der den Fallback-Pfad mit 400 auf Objekt-Update und erfolgreichem Userfield-Update absichert.

### Changed

- Verbesserung (Logging): Die Warnung beschreibt jetzt klar, dass nur das Objekt-Update übersprungen wird und der Userfield-Sync weiterläuft.
- Pflege: Add-on-Version auf `7.1.99` erhöht.

### Fixed

- Fix (API/Grocy/Nährwerte): Wenn das Produkt-Objekt-Update (`/objects/products/{id}`) mit einem nicht weiter reduzierbaren 400-Fehler (z. B. `no such column: fat`) scheitert, wird der Ablauf nicht mehr vorzeitig abgebrochen; der Userfield-Sync läuft trotzdem weiter.

## [7.1.98]

### Added

- Test: Unit-Tests für Userfield-Sync und Fallback-Verhalten ergänzt/angepasst.

### Changed

- Änderung (API/Grocy/Userfields): Beim Nährwert-Update werden `carbohydrates`, `fat`, `protein` und `sugar` zusätzlich auf den Grocy-Userfields des Produkts gesetzt (`PUT /userfields/products/{id}`).
- Robustheit (API/Grocy/Userfields): Wenn der Userfield-Endpunkt nicht verfügbar ist (z. B. 404/405) oder einzelne Felder unbekannt sind, wird defensiv mit reduziertem Payload weitergemacht, ohne den gesamten Request scheitern zu lassen.
- Pflege: Add-on-Version auf `7.1.98` erhöht.

## [7.1.97]

### Added

- Test: API-Test ergänzt, der bei unveränderter Menge keinen Aufruf von `set_product_inventory` mehr erwartet und trotzdem das Nährwert-Update prüft.

### Changed

- Pflege: Add-on-Version auf `7.1.97` erhöht.

### Fixed

- Fix (API/Lager-Tab/Nährwerte speichern): Beim Speichern wird der Inventar-Endpunkt nur noch aufgerufen, wenn sich die Menge tatsächlich geändert hat. Damit schlagen reine Nährwert-Änderungen (z. B. Kalorien) nicht mehr mit Grocy-400 im `/inventory`-Endpoint fehl.

## [7.1.96]

### Added

- Test: Unit-Test ergänzt, der den Retry ohne `stock_entry_id` absichert.

### Changed

- Pflege: Add-on-Version auf `7.1.96` erhöht.

### Fixed

- Fix (Grocy Inventory-API): `set_product_inventory` nutzt weiterhin `POST`, versucht bei 400-Antworten mit `stock_entry_id` aber automatisch einen zweiten Request ohne `stock_entry_id`, damit Grocy-Instanzen mit restriktiverem Schema weiterhin korrekt aktualisiert werden.

## [7.1.95]

### Added

- Test: API-Tests für die neue `product_id`-Priorisierung bei Verbrauchen, Speichern und Löschen ergänzt.

### Changed

- Pflege: Add-on-Version auf `7.1.95` erhöht.

### Fixed

- Fix (Lager-Tab/ID-Normalisierung): `consume`, `update` und `delete` akzeptieren jetzt optional `product_id` als eindeutigen Hint und priorisieren dadurch den korrekten Produkteintrag auch bei kollidierenden numerischen `stock_id`/`product_id`-Werten.
- Fix (Dashboard-Frontend/Lager): Requests aus dem Lager-Tab senden bei Verbrauchen, Speichern und Löschen zusätzlich `product_id` als Query-Parameter, damit serverseitig immer die richtige Produkt-ID aufgelöst wird.

## [7.1.94]

### Changed

- Pflege: Add-on-Version auf `7.1.94` erhöht.

### Fixed

- Fix (Dashboard/Produktvorschläge): Beim Tippen werden nur noch Grocy-Produktvorschläge geladen; zusätzliche KI-Varianten werden im Vorschlags-Request nicht mehr nachgeladen.
- Fix (Dashboard/Neu anlegen): `force_create` umgeht jetzt die vorherige Produkterkennung, damit bei „Neu anlegen" wirklich das eingegebene Produkt neu erstellt wird.
- Fix (API/Lager-Tab/Speichern): Mengenänderungen setzen den Bestand nun konsistent über den Grocy-Inventar-Endpunkt (`POST /stock/products/{id}/inventory`) mit aufgelöster `stock_entry_id`; dadurch treten keine 400er durch falsche Objekt-IDs in `PUT /objects/stock/{id}` mehr auf.

## [7.1.93]

### Added

- Test: Unit-Tests für die neuen Grocy-Client-Endpunkte (`set_product_inventory`, `delete_product`) ergänzt.

### Changed

- Pflege: Add-on-Version auf `7.1.93` erhöht.

### Fixed

- Fix (Dashboard/Neuanlage): Bei „Neu anlegen" wird jetzt immer der exakt eingegebene Produktname verwendet (kein unbeabsichtigtes Ersetzen durch KI-ähnliche Vorschläge).
- Fix (API/Lager-Tab/Löschen): Löschen im Lager-Tab entfernt nun Produkte korrekt über `DELETE /objects/products/{product_id}` statt über einen Stock-Objekt-Endpunkt.
- Fix (API/Lager-Tab/Menge=0): Beim Speichern mit Menge `0` wird jetzt der Grocy-Inventar-Endpunkt (`POST /stock/products/{id}/inventory` mit `new_amount`) verwendet, damit der Bestand korrekt auf 0 gesetzt/aufgebraucht wird.

## [7.1.92]

### Changed

- Pflege: Add-on-Version auf `7.1.92` erhöht.

### Fixed

- Fix (Dashboard-Test/Storage): `loadStorageProducts` ist wieder mit der erwarteten Funktionssignatur (`function loadStorageProducts()`) deklariert, sodass der statische Dashboard-Test wieder stabil grün läuft.
- Änderung (API/Grocy/Nährwerte): Fallback-Felder für Nährwerte entfernt; Updates senden bei Kalorien jetzt nur noch `calories` (kein `energy`) und bei Kohlenhydraten nur `carbohydrates` (kein `carbs`).
- Änderung (API/Grocy/Anzeige): Kohlenhydrate werden in Listenansichten wieder ausschließlich aus `carbohydrates` gelesen (ohne `carbs`-Fallback).
- Test: Unit-Tests auf das vereinfachte, fallback-freie Payload/Mapping angepasst.

## [7.1.91]

### Added

- Test: Unit-Tests für `carbs`-Fallback beim Lesen und erweitertes Nährwert-Payload ergänzt.

### Changed

- Pflege: Add-on-Version auf `7.1.91` erhöht.

### Fixed

- Fix (API/Grocy/Nährwerte): Beim Nährwert-Update wird `carbs` jetzt zusätzlich zu `carbohydrates` gesendet (analog zu `calories` + `energy`), um unterschiedliche Grocy-Schemata besser zu unterstützen.
- Fix (API/Grocy/Anzeige): Beim Lesen von Produktdaten wird für Kohlenhydrate nun erst `carbohydrates` und fallback auf `carbs` verwendet.

## [7.1.90]

### Added

- Test: Unit-Test ergänzt, der den 400-Fehler ohne extrahierbare Spalte absichert.

### Changed

- Verbesserung (Logging): Für diesen Fall wird eine klare Warnung mit Response-Body protokolliert.
- Pflege: Add-on-Version auf `7.1.90` erhöht.

### Fixed

- Fix (API/Grocy/Nährwerte): Wenn Grocy ein Nährwert-Update mit 400 ablehnt und keine unbekannte Spalte aus der Fehlermeldung extrahiert werden kann, wird das Update nun defensiv übersprungen statt den gesamten Request mit 500 abzubrechen.

## [7.1.89]

### Added

- Test: Unit-Test ergänzt, der sicherstellt, dass bei leerem MHD nur `{"amount": ...}` gesendet wird.

### Changed

- Pflege: Add-on-Version auf `7.1.89` erhöht.

### Fixed

- Fix (API/Grocy): `PUT /objects/stock/{id}` sendet `best_before_date` nur noch, wenn tatsächlich ein Datum gesetzt ist; leere Werte werden nicht mehr als `null` übertragen, um 400-Fehler beim Speichern im Produkt-Popup zu vermeiden.

## [7.1.88]

### Added

- Test: API- und Unit-Tests für die neue Stock-ID-Auflösung ergänzt.

### Changed

- Pflege: Add-on-Version auf `7.1.88` erhöht.

### Fixed

- Fix (API/Lager-Tab): Speichern im Produkt-Popup verwendet bei fehlender `stock_id` nun zuerst eine serverseitige Auflösung über `product_id` + `location_id`, damit die Menge als absoluter Wert aktualisiert wird (statt unbeabsichtigt `+1` über den Add-Endpoint).
- Fix (API/Lager-Tab): Nur wenn kein Bestandseintrag auflösbar ist, wird weiterhin ein neuer Eintrag erstellt.

## [7.1.87]

### Added

- Test: API- und Unit-Tests für den neuen Fallback-Pfad ergänzt.

### Changed

- Pflege: Add-on-Version auf `7.1.87` erhöht.

### Fixed

- Fix (API/Lager-Tab): Wenn ein Produkt über die Produkt-ID gefunden wird, aber kein nutzbarer `stock_id` vorhanden ist, wird beim Speichern nun automatisch ein Bestandseintrag über Grocy erstellt statt mit „Ungültiger Bestandseintrag" abzubrechen.
- Fix (API/Lager-Tab): Für Produkte ohne bestehenden Bestandseintrag wird Menge `0` beim Speichern mit klarer 400-Fehlermeldung abgewiesen.

## [7.1.86]

### Changed

- Pflege: Add-on-Version auf `7.1.86` erhöht.

### Fixed

- Fix (UI/Lager-Tab): Mengenänderungen im Produkt-Popup akzeptieren wieder Kommawerte (z. B. `1,5`) und werden korrekt gespeichert.

## [7.1.85]

### Changed

- Pflege: Add-on-Version auf `7.1.85` erhöht.

### Fixed

- Fix (UI/Lager-Tab): Swipe-Aktionen bei Produkten korrigiert – links wird jetzt wie angezeigt „Verbrauchen" ausgelöst, rechts „Bearbeiten".

## [7.1.84]

### Changed

- UI (Lager-Tab): Das konfigurierbare Dashboard-Polling-Intervall steuert jetzt auch das Auto-Refresh im Lager-Tab (nur aktiver Tab, pausiert bei inaktivem Browser-Tab).
- Pflege: Add-on-Version auf `7.1.84` erhöht.

### Fixed

- UX (Lager-Tab): Hintergrund-Refresh aktualisiert die Lagerliste ohne störende Lade-/Fehlerstatusmeldungen.

## [7.1.83]

### Added

- Test: Unit-Tests für den neuen Einkaufslisten-MHD-Import und den globalen `+4 Tage`-Fallback ergänzt.
- Test: Unit-Test ergänzt, der sicherstellt, dass `0` als Bestandsmenge als String `"0"` im Storage-Listing erhalten bleibt.
- UI/Config: Dashboard-Polling-Intervall für die Einkaufsliste als konfigurierbare Option (`dashboard_polling_interval_seconds`) ergänzt und im Frontend an die Auto-Refresh-Logik angebunden.

### Changed

- Home-Assistant-Integration: Options-Flow um `dashboard_polling_interval_seconds` (1-60 Sekunden) erweitert.
- Pflege: Add-on-Version auf `7.1.83` erhöht.

### Fixed

- Fix (Einkaufsliste/MHD): Beim Laden der Einkaufsliste wird ein MHD jetzt nur noch aus der Einkaufslisten-Notiz (`[grocy_ai_mhd:...]`) übernommen. Leere MHDs werden nicht mehr automatisch mit Lager-/Grocy-Werten überschrieben.
- Verbesserung (MHD-Fallback): Wenn beim "Einkaufen" weder ein explizites MHD noch `default_best_before_days` (aus KI oder Produktstandard) vorhanden ist, wird als Fallback automatisch `heute + 4 Tage` gesetzt.
- Fix (Lager-Tab): Das Speichern einer Bestandsmenge von `0` bleibt nun erhalten und wird nicht mehr als leerer Wert zurückgegeben.

## [7.1.82]

### Added

- Test: Unit-Tests für die neue MHD-Auflösung und KI-Mapping ergänzt.

### Changed

- Verbesserung (KI/MHD): Die KI kann jetzt beim Anlegen neuer Produkte eine geschätzte Standard-Haltbarkeit (`default_best_before_days`) liefern.
- Verbesserung (Einkaufsliste/MHD): MHD-Auflösung zentralisiert; wenn beim Hinzufügen oder beim "Einkaufen" kein MHD gesetzt ist, wird ein Datum aus `default_best_before_days` berechnet (aus KI-Wert oder Grocy-Produktstandard).
- UI (Benachrichtigungen/Geräteverwaltung): Karte im Notify-Tab wieder auf volle Breite gesetzt und Geräteansicht als 2-Spalten-Layout dargestellt (mobil weiterhin 1 Spalte).
- Pflege: Add-on-Version auf `7.1.82` erhöht.

### Removed

- Pflege: Doppelte MHD-Normalisierungslogik entfernt und in eine gemeinsame Service-Methode zusammengeführt.

### Fixed

- Verbesserung (Benachrichtigungen/Geräte): Geräte nach Namens-Gemeinsamkeiten gruppiert (z. B. `notify.mobile_app_pixel_watch_*` → Kategorie `Pixel Watch`) mit robustem Fallback auf normalisierte Namensbestandteile bzw. `Sonstige Geräte`.

## [7.1.81]

### Changed

- Pflege: Add-on-Version auf `7.1.81` erhöht.

### Fixed

- Fix (UI/Einkaufsliste): Swipe-Aktionen im Produkt-Tab korrigiert – die auslösenden Aktionen sind nicht mehr vertauscht (links löscht, rechts markiert als gekauft), passend zur dargestellten Aktionsfläche.

## [7.1.80]

### Added

- UI (Lager-Tab): Dynamisches Laden beim Tippen im Filterfeld ergänzt (debounced Requests wie in der Such-Tab-Logik), damit große Bestände serverseitig gefiltert geladen werden.
- Test: API- und Unit-Tests für den neuen Suchfilter im Lager-Endpoint und in der Grocy-Client-Filterlogik ergänzt.
- Verbesserung (Benachrichtigungen/iOS): iOS-Payload ergänzt um `push.interruption-level`, damit Hinweise sichtbar, aber nicht überaggressiv zugestellt werden.
- Verbesserung (Benachrichtigungen/Android): Android-Payload ergänzt um `importance` und `sticky`, zusätzlich zu bestehenden `priority`-/`channel`-Feldern.

### Changed

- API/Service (Lager): `GET /api/dashboard/stock-products` unterstützt nun den Query-Parameter `q` und gibt gefilterte Ergebnisse über Name/Lagerort zurück.
- Verbesserung (Benachrichtigungen/Mobile Styling): Mobile Testbenachrichtigungen enthalten jetzt zusätzliche Styling-Metadaten wie `icon`, `notification_icon`, `group` und `color`, um auf mobilen Geräten konsistenter dargestellt zu werden.
- Test: API-Tests erweitert, um die neuen plattformspezifischen Payload-Felder für mobile Testsendungen abzusichern.
- Pflege: Add-on-Version auf `7.1.80` erhöht.

## [7.1.79]

### Changed

- UI (Lager-Tab): Checkbox zum Laden aller Grocy-Produkte rechts neben das Filterfeld verschoben.
- UI (Lager-Tab): Beschriftung von „Alle in Grocy verfügbaren Produkte laden“ auf „Alle Produkte anzeigen" gekürzt.
- UI (Lager-Tab/Mobil): Filterfeld und Checkbox umbrechen in der mobilen Ansicht jetzt in zwei Zeilen für bessere Lesbarkeit.
- UI (Einkaufsliste): Die Liste im Dashboard aktualisiert sich jetzt automatisch im Hintergrund (Polling alle 5 Sekunden), damit Änderungen von anderen Nutzern zeitnah sichtbar werden.
- UX (Einkaufsliste): Auto-Refresh läuft nur im aktiven Einkaufs-Tab und pausiert bei inaktiver Browser-Ansicht, um unnötige Requests zu vermeiden.
- Performance (Einkaufsliste): Re-Render erfolgt nur bei tatsächlichen Datenänderungen über eine Signaturprüfung der Listeneinträge.
- Pflege: Add-on-Version auf `7.1.79` erhöht.

## [7.1.78]

### Added

- Verbesserung (Benachrichtigungen/Plattform): Automatische Plattform-Erkennung (Android/iOS) für mobile Targets ergänzt und im Dashboard visuell hervorgehoben.
- Test: API-Tests ergänzt, die iOS- und Android-Payloads für den Device-Test absichern.

### Changed

- UI (Benachrichtigungen): Geräte- und Verlaufskarten im Notify-Tab modernisiert (Badge-Status, klarere Hierarchie, bessere Lesbarkeit).
- Pflege: Add-on-Version auf `7.1.78` erhöht.

### Fixed

- Fix (Benachrichtigungen/Testversand): Mobile Testsendungen verwenden jetzt plattformspezifische Payload-Parameter (Android: `data.clickAction`, `priority`, `ttl`; iOS: `data.url`, `push.sound`, `thread-id`).

## [7.1.77]

### Added

- Test: API-Tests ergänzt, die den echten Service-Call für mobile Tests sowie den Fehlerpfad bei fehlendem Notify-Service absichern.

### Changed

- Pflege: Add-on-Version auf `7.1.77` erhöht.

### Fixed

- Fix (Benachrichtigungen/Testversand): Die Endpunkte `POST /api/dashboard/notifications/tests/device` und `POST /api/dashboard/notifications/tests/all` senden mobile Testbenachrichtigungen jetzt tatsächlich an Home Assistant (`notify.mobile_app_*`) statt nur einen Verlaufseintrag zu speichern.
- Fix (Benachrichtigungen/Fehlerhandling): Fehlgeschlagene mobile Testsendungen liefern nun nutzerfreundliche 502-Fehlermeldungen und werden im Verlauf als fehlgeschlagen markiert.

## [7.1.76]

### Added

- Test: API-Test ergänzt, der die Erkennung von `notify.mobile_app_*`-Services über den Home-Assistant-Endpoint absichert.

### Changed

- UI (Lager-Tab): Produktkarten im Lager verwenden jetzt denselben HTML-Aufbau wie Produkte im Such-Tab (gemeinsame Card-/Content-Struktur für Bild, Meta-Bereich und Badge-Spalte).
- UI (Lager-Tab): Lagerprodukte nutzen dieselben Stilklassen wie die Suchprodukte, damit Abstände, Bildgröße und Badge-Ausrichtung visuell konsistent sind.
- Pflege: Add-on-Version auf `7.1.76` erhöht.

### Fixed

- Fix (Benachrichtigungen/Geräteerkennung): Notify-Devices werden im Dashboard jetzt primär über die Home-Assistant-Service-API (`/api/services`) erkannt statt ausschließlich über `options.json`-Pattern-Matches.
- Fix (Benachrichtigungen/Geräteerkennung): Fallback auf die bestehende `options.json`-Erkennung bleibt erhalten, falls die Service-API temporär nicht erreichbar ist.

## [7.1.74]

### Changed

- Pflege: Add-on-Version auf `7.1.74` erhöht.

### Fixed

- Fix (Benachrichtigungen/Fehlertexte): Technische Mehrfachfehler aus Supervisor-Header- und Endpoint-Retries werden nicht mehr 1:1 als UI-Statusmeldung ausgegeben. Stattdessen liefert die API jetzt eine kurze, verständliche Fehlermeldung (z. B. Autorisierungsfehler 401/403).
- Verbesserung (Logging): Die vollständige technische Fehlerkette bleibt weiterhin im Add-on-Log erhalten, damit die Ursachenanalyse möglich bleibt.
- Verbesserung (Benachrichtigungsverlauf): Der History-Eintrag für fehlgeschlagene persistente Tests enthält nun ebenfalls die nutzerfreundliche Fehlermeldung statt der langen technischen Retry-Kette.
- Test: API-Test für den 401-Pfad auf die neue nutzerfreundliche Fehlermeldung erweitert.

## [7.1.73]

### Added

- Test: Unit-Test ergänzt, der die API-Flags in `config.json` absichert.

### Changed

- UI (Lager-Tab): Attributdarstellung der Lagerprodukte an das Such-Layout angepasst; `Lager` bleibt als Zeile unter dem Produktnamen.
- UI (Lager-Tab): `Menge` und `MHD` werden rechts als Badge-Spalte dargestellt, analog zur Produktsuche.
- UI (Lager/Swipe): Swipe-Aktionsflächen im Lager zeigen Bearbeiten/Verbrauchen jetzt ebenfalls als Badge-Chips wie im Such-Tab.
- Pflege: Add-on-Version auf `7.1.73` erhöht.

### Fixed

- Fix (Add-on/Home Assistant OS): `config.json` aktiviert jetzt `homeassistant_api` und `hassio_api`, damit Supervisor-Token/HA-API im Add-on zuverlässig verfügbar sind und Service-Calls für persistente Benachrichtigungen nicht mehr an fehlenden Berechtigungen scheitern.
- Verbesserung (Logging): Bei fehlgeschlagenem Versand persistenter Testbenachrichtigungen wird die genaue Fehlerursache jetzt zusätzlich ins Add-on-Log geschrieben.

## [7.1.72]

### Added

- Test: API-Test ergänzt, der den Erfolgsfall über `X-Hassio-Key` absichert.

### Changed

- Pflege: Add-on-Version auf `7.1.72` erhöht.

### Fixed

- Fix (Benachrichtigungen/Dashboard): Home-Assistant-Serviceaufrufe probieren jetzt zusätzliche Auth-Header-Kombinationen (`Authorization`, `X-Supervisor-Token`, `X-Hassio-Key`), damit Supervisor-/Ingress-Varianten zuverlässiger autorisiert werden.
- Fix (Benachrichtigungen/Dashboard): Serviceaufrufe testen neben `/core/api/services/...` auch `/api/services/...`, um Installationen mit abweichendem Supervisor-Proxy robuster zu unterstützen.

## [7.1.71]

### Added

- Test: API-Test ergänzt, der den 400-Fehlerpfad von `persistent_notification.create` mit erfolgreichem Notify-Fallback absichert.

### Changed

- Pflege: Add-on-Version auf `7.1.71` erhöht.

### Fixed

- Fix (Benachrichtigungen/Dashboard): Bei Fehlern von `persistent_notification.create` wird jetzt immer zusätzlich der Fallback `notify.persistent_notification` versucht, statt nur bei 404/405. Dadurch schlagen Systeme mit 400-Fehlermeldungen (z. B. "service not found") nicht mehr mit 502 fehl.
- Fix (Benachrichtigungen/Dashboard): Fallback-Aufruf sendet nur `title` und `message`, damit keine inkompatiblen Felder wie `notification_id` an den Notify-Service gehen.

## [7.1.70]

### Added

- Test: API-Tests für ID-Sanitizing und den Retry-Pfad ohne `notification_id` ergänzt.

### Changed

- Pflege: Add-on-Version auf `7.1.70` erhöht.

### Fixed

- Fix (Benachrichtigungen/Dashboard): Persistente Testbenachrichtigungen erzeugen jetzt eine Home-Assistant-kompatible `notification_id` ohne Sonderzeichen, damit Service-Calls nicht mehr an ungültigen IDs scheitern.
- Fix (Benachrichtigungen/Dashboard): Bei 400/422-Validierungsfehlern wird `persistent_notification.create` automatisch ohne `notification_id` erneut versucht, um 502-Fehler bei strengeren HA-Versionen zu vermeiden.

## [7.1.69]

### Added

- Test: API-Tests für Fallback auf `HASSIO_TOKEN` und für den 401-Fehlerpfad ergänzt.

### Changed

- Pflege: Add-on-Version auf `7.1.69` erhöht.

### Removed

- UI (Benachrichtigungen): `padding` bei `.notification-list li` entfernt, damit die Listen-/Swipe-Darstellung den gewünschten Abständen entspricht.

### Fixed

- Fix (Benachrichtigungen/Dashboard): Persistente Testbenachrichtigungen akzeptieren nun sowohl `SUPERVISOR_TOKEN` als auch `HASSIO_TOKEN` und unterstützen zusätzlich den Header `X-Supervisor-Token`, damit Service-Calls im Add-on-Umfeld zuverlässiger autorisiert werden.
- Fix (Benachrichtigungen/Dashboard): Fehlerantworten des Home-Assistant-Service werden im API-Fehlertext mitgeführt, um 502-Ursachen im Dashboard besser nachvollziehen zu können.

## [7.1.68]

### Added

- Fix (Benachrichtigungen/Dashboard): Fallback auf `notify.persistent_notification` ergänzt, falls `persistent_notification.create` im Zielsystem nicht verfügbar ist.
- Test: API-Tests für erfolgreichen Service-Call und Fehlerfall ohne `SUPERVISOR_TOKEN` ergänzt.

### Changed

- UI (Benachrichtigungen/Swipe): Swipe-Aktionsflächen der Regelkarten im Notify-Tab vergrößert, damit Chip-Inhalt und Buttonfläche optisch konsistent wirken.
- Pflege: Add-on-Version auf `7.1.68` erhöht.

### Fixed

- Fix (Benachrichtigungen/Dashboard): Der Endpoint `POST /api/dashboard/notifications/tests/persistent` sendet die Testnachricht jetzt wirklich an Home Assistant (`persistent_notification.create`) statt nur einen Verlaufseintrag zu speichern.

## [7.1.67]

### Added

- UI (Lager-Tab): Checkbox ergänzt, um optional alle in Grocy verfügbaren Produkte zusätzlich zum aktuellen Lagerbestand zu laden.

### Changed

- API/Service (Lager): `GET /api/dashboard/stock-products` unterstützt den Parameter `include_all_products`, der auch nicht auf Lager befindliche Produkte zurückliefert.
- UX (Lagerliste): Nicht auf Lager befindliche Produkte werden angezeigt, aber Lageraktionen (Bearbeiten/Verbrauchen) bleiben für diese Einträge deaktiviert.
- Pflege: Add-on-Version auf `7.1.67` erhöht.

## [7.1.66]

### Changed

- UI (Swipe-Actions): Lagerprodukte im Tab „Lager“ nutzen jetzt dieselbe Swipe-Interaktion wie die Einkaufssuche (links: Bearbeiten, rechts: Verbrauchen) statt fester Aktionsbuttons.
- UI (Notify-Regeln): Regeln im Benachrichtigungs-Tab wurden auf Swipe-Buttons umgestellt (links: Bearbeiten, rechts: Löschen) für ein konsistentes Bedienmuster.
- Frontend-Refactoring: Wiederverwendbare Swipe-Logik (`bindSwipeInteractions`) und gemeinsame Swipe-CSS-Klassen eingeführt, damit Shopping-, Lager- und Regel-Listen gleiches Verhalten teilen.
- UI (Button-Styles): Aktionsbuttons in Lager- und Benachrichtigungsansicht auf die gleichen Basis-Buttonvarianten wie auf Such- und Rezeptseite vereinheitlicht (Primary/Ghost/Success/Danger).
- UI (Benachrichtigungen): Dynamisch gerenderte Regelaktionen nutzen jetzt konsistente Klassen (`ghost-button` für Bearbeiten, `danger-button` für Löschen).
- UI (Dashboard/Tabs): Die Statusmeldungen der Tabs werden nun im Header anstelle der Überschrift „Smart Pantry Dashboard" angezeigt.
- UX (Tab-spezifisch): Beim Tab-Wechsel spiegelt der Header immer die jeweils aktive Statusmeldung (Einkauf, Rezepte, Lager, Benachrichtigungen).
- Pflege: Add-on-Version auf `7.1.66` erhöht.

## [7.1.65]

### Changed

- Testqualität: Doppelten API-Testfall für `search-variants` bereinigt und Erwartungswerte an das tatsächliche Verhalten ohne `include_ai=true` angepasst (nur Input+Grocy statt KI-Vorschläge).
- Pflege: Add-on-Version auf `7.1.65` erhöht.

### Removed

- Architektur/Codepflege: Doppelte Implementierung von `_normalize_barcode_for_lookup` in `api/routes.py` entfernt, um widersprüchliche Wartungspfade zu vermeiden.

### Documentation

- Dokumentation: `README.md` inhaltlich aktualisiert (aktueller Versionsstand, klare API-/Architektur-Hinweise, konsolidierte Entwicklungsbefehle).

## [7.1.64]

### Added

- Fix (Benachrichtigungen): Fallback für `persistent_notification` ergänzt. Wenn der Core-Service `persistent_notification.create` nicht verfügbar ist, wird automatisch `notify.persistent_notification` verwendet.
- Test: Unit-Tests für Dispatcher-Pfad (Core-Service) und Fallback-Pfad (`notify.persistent_notification`) ergänzt.

### Changed

- UI (Lager/Popup „Bestand ändern“): Zu ändernde Attribute im Bearbeiten-Dialog als eigene, klar getrennte Zeilen dargestellt.
- Pflege: Add-on-Version auf `7.1.64` erhöht.

## [7.1.63]

### Added

- Add-on (Konfiguration): Übersetzungen für Optionsfelder ergänzt (`translations/de.yaml`, `translations/en.yaml`) mit natürlichen, verständlichen Feldnamen.

### Changed

- UI (Lager-Tab): Aktions-Buttons der Produktkarten in der Desktop-Ansicht explizit an den rechten Rand der Karte ausgerichtet.
- UX (Konfiguration): Sinnvolle Präfixe (`Allgemein`, `Ollama`, `Scanner`, `Benachrichtigungen`, `Bilder`, `Wartung`) eingeführt, um die Formularreihenfolge klarer zu strukturieren.
- Pflege: Add-on-Version auf `7.1.63` erhöht.

## [7.1.62]

### Changed

- Add-on (Konfiguration): Reihenfolge der `options`/`schema` in `config.json` überarbeitet, damit der Schalter `debug_mode` im Home-Assistant-Formular weiter unten angezeigt wird.
- Pflege: Add-on-Version auf `7.1.62` erhöht.

## [7.1.61]

### Changed

- Pflege: Add-on-Version auf `7.1.61` erhöht.

### Removed

- Add-on (Ingress): Externes Port-Mapping (`8000/tcp`) aus `config.json` entfernt, damit der Zugriff standardmäßig ausschließlich über Home-Assistant-Ingress erfolgt.

## [7.1.60]

### Added

- Test: API-Test für `size=mobile` und Cache-Header ergänzt.
- Test: Unit-Tests für Persistent-Only- und Mixed-Channel-Regeln ergänzt.

### Changed

- Performance (Thumbnails/Mobil): Dashboard-Bildproxy unterstützt nun die Größe `mobile` (64x64), wodurch auf kleinen Viewports kleinere Produktbilder geladen werden.
- Performance (Caching): `GET /api/dashboard/product-picture` liefert jetzt `Cache-Control: public, max-age=86400`, damit Mobilbrowser Thumbnails aggressiver zwischenspeichern.
- UI (Dashboard): Thumbnail-Aufrufe verwenden auf mobilen Viewports automatisch die neue Proxy-Größe `mobile` statt `thumb`.
- Pflege: Add-on-Version auf `7.1.60` erhöht.

### Fixed

- Fix (Benachrichtigungen): Rule-Engine erzeugt jetzt auch dann `persistent_notification`-Nachrichten, wenn kein mobiles Notify-Target vorhanden ist.
- Fix (Benachrichtigungen): Regeln mit gemischten Kanälen liefern mobile Push und persistente Benachrichtigung als getrennte Dispatch-Nachrichten aus.

## [7.1.59]

### Fixed

- Fix (Scanner/WebView): Kamera-Start nutzt nun eine kompatible `getUserMedia`-Abfrage (inkl. Legacy-Fallback) statt ausschließlich `navigator.mediaDevices.getUserMedia`.
- Fix (Scanner/UX): Fehlermeldungen beim Kamera-Start unterscheiden jetzt klar zwischen fehlender Berechtigung, unsicherem Kontext (HTTPS/WebView) und fehlender Kamera.

## [7.1.58]

### Fixed

- Verbessert: Die Barcode-Erkennung rotiert den Scanner-Canvas bei Hochkant-Bildquellen nun automatisch um 90°, wenn die Bilddrehung auf 0° steht. Dadurch werden Barcodes in hochkant aufgenommenen Bildern zuverlässiger erkannt.

## [7.1.57]

### Added

- Scanner (Ausrichtung): Neue Option „Bilddrehung" (0°/90°/180°/270°) im Scanner-Modal, damit Kamera-Feed bei horizontal/vertikalem Handling passend ausgerichtet werden kann.

### Changed

- Scanner (Erkennung): Die Barcode-Analyse übernimmt die gewählte Drehung ebenfalls auf dem Analyse-Canvas (ROI), damit `BarcodeDetector` den Code in der gewählten Orientierung robuster lesen kann.
- Pflege: Add-on-Version auf `7.1.57` erhöht.

## [7.1.56]

### Changed

- Scanner (Kameraauswahl): Verfügbare Kameras werden gelistet und sind im Scanner testweise auswählbar; Standard bleibt Rückkamera bevorzugt.
- Scanner (Qualität): Kamera-Streams fordern zuerst höhere Auflösungen (bis 2560x1440) an und fallen stufenweise auf kleinere Profile zurück.
- Scanner (UX/Erkennung): Barcode-Analyse startet erst nach kurzer Scharfstell-Wartezeit; zusätzlich Hinweis „Etwas weiter weg halten“.
- Scanner (Erkennungsrahmen): Fester Rahmen in der Bildmitte eingebaut; Barcode-Detektion analysiert nur noch diesen mittigen Bereich.
- Scanner (Lichtprüfung): Helligkeit wird periodisch geprüft und bei schwachem Licht eine Warnung angezeigt.
- Scanner (Debug): `getCapabilities()`/`getSettings()` werden geloggt und als Debug-Block im Scanner angezeigt (inkl. focusMode/focusDistance/zoom/torch-Unterstützung).
- Pflege: Add-on-Version auf `7.1.56` erhöht.

## [7.1.55]

### Changed

- Stabilität (Scanner/Fokus): Beim Scanner-Start wird der bevorzugte Fokusmodus gespeichert und direkt nach dem Setzen der Constraints einmal aktiv nachgezogen.
- Pflege: Add-on-Version auf `7.1.55` erhöht.

### Fixed

- Fix (Scanner/Fokus): Kamera-Fokus wird während des laufenden Scans zyklisch neu angestoßen (alle 2s) für unterstützte Modi (`continuous`/`single-shot`), damit mobile Kameras nicht in unscharfem Zustand „hängen bleiben“.
- Stabilität (Scanner): Fokus-Refresh-Timer wird beim Stoppen zuverlässig beendet und Fokus-Zustand zurückgesetzt.

## [7.1.54]

### Changed

- Stabilität (Scanner/Barcode): Barcode-Lookup wird erst ausgelöst, wenn derselbe normalisierte Code in mehreren aufeinanderfolgenden Frames erkannt wurde (Debounce/Stabilitätsprüfung), wodurch Fehllesungen und wechselnde Codes deutlich reduziert werden.
- Stabilität (Scanner): Während ein Barcode-Lookup läuft, werden weitere automatische Lookups kurzzeitig blockiert, um konkurrierende Requests zu vermeiden.
- Pflege: Add-on-Version auf `7.1.54` erhöht.

### Fixed

- Fix (Scanner/Fokus): Kamera-Fokus priorisiert jetzt `focusMode=continuous` (statt primär `manual`), damit mobile Geräte während des Scan-Vorgangs fortlaufend nachfokussieren und das Bild nicht dauerhaft unscharf bleibt.

## [7.1.53]

### Changed

- Scanner (Mobile Browser): Video-Element wird beim Start explizit mit `playsinline`, `autoplay` und `muted` initialisiert, um iOS-/WebKit-Verhalten robuster zu unterstützen.
- Pflege: Add-on-Version auf `7.1.53` erhöht.

### Fixed

- Scanner (Browser-Kompatibilität): Kamera-Start nutzt jetzt abgestufte `getUserMedia`-Profile (von bevorzugter Rückkamera bis zu generischem Fallback), damit Scanner in mehr Browsern/Endgeräten startet statt direkt fehlzuschlagen.

## [7.1.52]

### Added

- Test: Dashboard-API-Tests für Barcode-Varianten und LLaVA-Timeout-Weitergabe ergänzt.
- Service: `GrocyClient.get_stock_products(...)` liefert Nährwerte für den Lager-Tab mit; `GrocyClient.update_product_nutrition(...)` ergänzt.
- Test: API- und Unit-Tests für Nährwertanzeige/-Update ergänzt.

### Changed

- UI (Lager-Tab/Produkt-Popup): Im Bearbeiten-Popup werden aktuelle `Menge` und `MHD` zusätzlich als zwei separate Info-Zeilen angezeigt.
- Stabilität (Scanner/LLaVA): Server blockiert parallele LLaVA-Anfragen während ein Lauf aktiv ist (`429` bei gleichzeitigem Request), um Mehrfachabfragen zu vermeiden.
- UI (Lager/Popup „Bestand ändern“): Bearbeiten-Dialog um Nährwertfelder erweitert (Kalorien, Kohlenhydrate, Fett, Eiweiß, Zucker), damit diese direkt im Lager-Tab angepasst werden können.
- API/Lager: `PUT /api/dashboard/stock-products/{stock_id}` akzeptiert jetzt optional Nährwerte und aktualisiert zusätzlich die Produkt-Nährwerte in Grocy.
- Pflege: Add-on-Version auf `7.1.52` erhöht.

### Fixed

- Fix (Scanner/LLaVA): LLaVA-Requests werden jetzt mit konfigurierbarem Timeout (`scanner_llava_timeout_seconds`) verarbeitet und frontendseitig nach Ablauf sauber abgebrochen, statt unbegrenzt zu warten.
- Stabilität (Scanner/LLaVA): Auto-Fallback im Frontend respektiert zusätzlich ein Cooldown, damit bei ausbleibendem Barcode nicht dauerhaft neue KI-Calls gestartet werden.
- Fix (Barcode/OpenFoodFacts): Für 12-stellige UPC-Codes wird zusätzlich die 13-stellige Variante mit führender `0` geprüft (und umgekehrt), um Treffer bei OpenFoodFacts/Grocy zu erhöhen.

## [7.1.51]

### Added

- Test: API-Tests zur Barcode-Normalisierung für lange Scannerwerte ergänzt.

### Changed

- Pflege: Add-on-Version auf `7.1.51` erhöht.

### Fixed

- Fix (Barcode-Scanner/OpenFoodFacts): Sehr lange KI-Barcode-Strings (z. B. GS1 mit führendem `01` + Zusatzdaten) werden jetzt vor dem Lookup auf gültige GTIN/EAN-Längen normalisiert, damit OpenFoodFacts die korrekte Produktnummer erhält.
- Scanner (Kamera): Fokus-Optimierung erweitert – bevorzugt `focusMode=manual` (Fallback auf `single-shot`/`continuous`), setzt wenn verfügbar den Fokuspunkt in die Bildmitte und nutzt bei unterstützten Geräten kurze Fokusdistanz.

## [7.1.50]

### Changed

- UI (Lager-Tab): Aktions-Buttons der Produktkarten in der Desktop-Ansicht explizit an den rechten Rand der Karte ausgerichtet.
- Pflege: Add-on-Version auf `7.1.50` erhöht.

## [7.1.49]

### Added

- Test: API-Test ergänzt, der String-IDs und Datumswerte mit Zeitanteil für den "bald ablaufend"-Pfad absichert.

### Changed

- UI (Lager-Tab): Produktkarten im Lager auf ein festes 3-Spalten-Grid umgestellt (`Bild | Name/Beschreibung | Buttons`).
- UI (Lager-Tab): Name und Beschreibung werden jetzt explizit untereinander dargestellt.
- UI (Lager-Tab): Aktions-Buttons (`Bearbeiten`, `Verbrauchen`) pro Produkt werden vertikal untereinander angezeigt.
- Pflege: Add-on-Version auf `7.1.49` erhöht.

### Fixed

- Fix (Rezepte/"Bald ablaufend"): Filter verarbeitet `product_id` jetzt robust auch als String, sodass ablaufende Produkte nicht fälschlich ausgeschlossen werden.
- Fix (Rezepte/"Bald ablaufend"): MHD-Werte mit Zeitanteil (z. B. `YYYY-MM-DD HH:MM:SS` oder ISO mit `T`) werden korrekt als Datum erkannt.

## [7.1.48]

### Changed

- API: Bild-Proxy (`/api/dashboard/product-picture`) um den Query-Parameter `size` erweitert (`thumb`/`full`) und ruft bei Grocy nun unterschiedliche Zielgrößen via `best_fit_width`/`best_fit_height` ab.
- UI: Thumbnail-Kontexte (Listen/Karten) bleiben bei `size=thumb`, während Volldarstellungen (Rezept-Modal und Lager-Produktbild im Bearbeiten-Dialog) explizit `size=full` anfordern, damit kleine Vorschauen keine großen Bilder mehr laden.
- Pflege: Add-on-Version auf `7.1.48` erhöht.
- UI (Einkaufsliste): Im Produkt-Popup wurde der Button `Speichern` in eine eigene Zeile unterhalb des Notizfeldes verschoben.
- Pflege: Add-on-Version auf `7.1.48` erhöht.
- UI (Einkaufsliste): Im Produkt-Popup steht der Button `Speichern` für die Mengenbearbeitung jetzt in einer eigenen Zeile unter dem Mengenfeld.
- UI (Notify-Tab): Layout der Regeln vollständig auf ein 3-Spalten-Raster umgestellt (`Name | Priorität/Ereignisse/Kanäle/Cooldown | Buttons`) für bessere Struktur und passendere Einbindung ins bestehende Dashboard.
- UI (Notify-Tab): Metadaten werden nun untereinander mit klaren Labels dargestellt (Priorität, Ereignisse, Kanäle, Cooldown).
- UI (Notify-Tab): Aktions-Buttons pro Regel werden untereinander angezeigt und konsistent an die Kartenbreite angepasst.
- Pflege: Add-on-Version auf `7.1.47` erhöht.

## [7.1.47]

### Added

- UI (Popup „Bestand ändern"): Neuer Button „Produktbild löschen" ergänzt, um das Bild eines Produkts direkt im Bearbeiten-Dialog zu entfernen.
- API: Neuer Endpoint `DELETE /api/dashboard/products/{product_id}/picture` zum Entfernen des Produktbilds.
- Service: `GrocyClient.clear_product_picture(...)` ergänzt und per Tests abgesichert.

### Changed

- Pflege: Add-on-Version auf `7.1.47` erhöht.

### Fixed

- UI (Lager-Tab): Produktbilder in der Lagerliste vereinheitlicht und über dieselbe Bild-Logik wie in den anderen Tabs gerendert (inkl. Proxy/Fallback-Verhalten).

## [7.1.46]

### Added

- UI (Notify-Tab): Badges um visuelle Marker ergänzt (Kanäle/Priorität/Cooldown), damit Regeln schneller erfassbar sind.

### Changed

- UI (Notify-Tab): Regelkarten im iOS-inspirierten Stil überarbeitet (abgerundete Card-Flächen, sanfte Verlaufshintergründe, kompakter Header mit Icon und strukturierte Meta-Badges).
- UI (Notify-Tab): Aktions-Buttons weiterhin pillenförmig, aber mit dezentem Lift/Hover für einen app-artigen Touch optimiert.
- Pflege: Add-on-Version auf `7.1.46` erhöht.

## [7.1.45]

### Added

- API: Neuer Endpoint `PUT /api/dashboard/shopping-list/item/{shopping_list_id}/amount` zum Setzen einer konkreten Menge.
- Test: API-Test ergänzt, der das Aktualisieren einer konkreten Einkaufslistenmenge absichert.

### Changed

- UI (Einkaufsliste): Im Produkt-Popup kann die Einkaufsmenge jetzt direkt bearbeitet und gespeichert werden.
- Pflege: Add-on-Version auf `7.1.45` erhöht.

## [7.1.44]

### Added

- UI (Lager/Popup „Bestand ändern“): Popup um relevante Produktinfos erweitert (Produktname, Produkt-ID, Bestands-ID, Lagerort) und Produktbild direkt im Dialog ergänzt.
- API: Neuer Endpoint `DELETE /api/dashboard/stock-products/{stock_id}` zum Löschen eines Bestandseintrags (inkl. `product_id`-Fallback auf den passenden `stock_id`).
- Service: `GrocyClient.delete_stock_entry(...)` ergänzt, um Bestände über Grocy `objects/stock/{id}` zu löschen.
- Test: Unit- und API-Tests für das Löschen von Bestandseinträgen ergänzt.

### Changed

- UI (Lager/Popup „Bestand ändern“): Lösch-Button „Produkt löschen“ im Bearbeiten-Dialog hinzugefügt, inkl. Bestätigungsdialog und aktualisierter Statusmeldung.
- UI (Einkaufsliste): Unterhalb der Notiz wird jetzt ein zusätzlicher Bestands-Tag pro Produkt angezeigt (`Bestand: ...`).
- UI (Einkaufsliste): Der Bestandswert wird aus `in_stock` übernommen und für Dezimalwerte lokalisiert dargestellt (de-DE).
- UI (Notify-Tab): Regel-Objekte visuell näher an die Produktkarten der Einkaufsliste gebracht (größerer Kartenradius, spacing und badge-ähnliche Meta-Anordnung).
- UI (Notify-Tab): Aktions-Buttons pro Regel auf pillenförmigen Badge-Look umgestellt und farblich differenziert (Bearbeiten/Rot für Löschen), wie gewünscht weiterhin mit Farbe.
- UI (Einkaufsliste): MHD-Badge zeigt bei vorhandenem Datum jetzt nur noch das Datum ohne Präfix `MHD:`; ohne Datum bleibt der CTA `MHD wählen` unverändert.
- Pflege: Add-on-Version auf `7.1.44` erhöht.

## [7.1.43]

### Changed

- UI (Interaktionen): Übergänge bereinigt, damit keine Shadow-Animationen mehr referenziert werden.
- Pflege: Add-on-Version auf `7.1.43` erhöht.

### Removed

- UI (Dashboard): Alle Box-Shadows im Dashboard-Theme entfernt, inklusive Cards, Buttons, Tabbar, Header, Inputs und Modal-Elementen, für einen flacheren, einheitlichen Stil.

## [7.1.42]

### Added

- Test: Unit-Test ergänzt, der mehrere `unknown column`-Fehler (`carbohydrates`, danach `qu_factor_purchase_to_stock`) und den erfolgreichen dritten Request absichert.

### Changed

- UI (Dashboard): Einheitliches visuelles Theme für alle Dashboard-Bereiche eingeführt (konsistente Farbpalette, Karten-/Header-Stil und harmonisierte Light-/Dark-Variablen).
- UI (Navigation): Bottom-Tabbar und aktiver Tab mit neuem Akzent-Gradienten, Glassmorphism-Hintergrund und angepasstem Shadow-Design vereinheitlicht.
- UI (Interaktionen): Buttons inkl. Hover-/Focus-/Active-States global vereinheitlicht; Primary-, Danger-, Success- und Ghost-Varianten optisch konsistent gemacht.
- UI (Header): Topbar als konsistenter Card-Container gestaltet und Theme-Switch visuell an das neue Farbsystem angepasst.
- Pflege: Add-on-Version auf `7.1.42` erhöht.

### Fixed

- Fix (Produktsuche): Produktanlage in Grocy entfernt bei aufeinanderfolgenden `400 Bad Request`-Antworten mit Schemafehlern ("has no column named ...") die jeweils bemängelten Felder schrittweise aus dem Retry-Payload.
- Stabilität: Retry-Logik bricht weiterhin sauber ab, wenn kein unbekanntes Feld aus der Fehlermeldung extrahiert werden kann.
- Fix (CSS): Verweis auf nicht definierte Variable `--accent` im Rezept-Methoden-Switch auf `--accent-primary` korrigiert.

## [7.1.41]

### Added

- Test: Unit-Tests für Retry-Logik und Payload-Bereinigung in `GrocyClient.create_product` ergänzt.

### Changed

- Pflege: Add-on-Version auf `7.1.41` erhöht.

### Fixed

- Fix (Produktsuche): Produktanlage in Grocy erhält bei `400 Bad Request` jetzt automatisch einen Retry mit bereinigtem Payload (nur von Grocy akzeptierte Felder + validierte `location_id`/`quantity_unit` IDs).
- Stabilität: Bei ungültigen KI-IDs werden fallback-fähige Werte aus den tatsächlich in Grocy verfügbaren Lagerorten und Mengeneinheiten verwendet.
- Logging: Bei einem 400-Fehler der Produktanlage wird der Retry inkl. Response-Body als Warnung protokolliert.
- Fix (Lager-Tab): Der Button „✏️ Bearbeiten“ öffnet das Popup „Bestand ändern“ jetzt wieder zuverlässig auch dann, wenn ein Eintrag nur über `product_id` (Fallback-ID) adressierbar ist.
- Fix (Lager-Tab): Speichern im Bearbeiten-Popup nutzt nun dieselbe aufgelöste Ziel-ID wie der Button-Aufruf, wodurch Updates konsistent am korrekten Eintrag landen.

## [7.1.39]

### Added

- Test: API-Test ergänzt, der `force_create` mit Mengenpräfix (`2 oliven`) und direkte Anlage (`created_and_added`) absichert.
- Test: API-Tests für Produkt-ID-Fallback beim Verbrauchen und Bearbeiten von Lagerprodukten ergänzt.

### Changed

- UI (Suche): Beim Klick auf `source: input` wird die Suche mit `force_create` ausgelöst und die Statusmeldung auf direkte Anlage angepasst.
- Pflege: Add-on-Version auf `7.1.39` erhöht.

### Fixed

- Fix (Produktauswahl): Auswahl von `Neu anlegen` in der Variantenliste legt das Produkt jetzt direkt an, statt erneut in die Varianten-Auswahl zurückzuspringen.
- API: `POST /api/dashboard/search` akzeptiert `force_create`, um die Varianten-Fallback-Auswahl gezielt zu überspringen.
- Fix (Lager-Tab): Bearbeiten/Verbrauchen-Endpunkte akzeptieren nun zusätzlich `product_id` als Fallback-ID und lösen diese serverseitig zuverlässig auf den echten Bestandseintrag (`stock_id`) auf.
- Fix (Lager-Tab): Verbrauchen nutzt beim Fallback weiterhin korrekt den passenden `stock_entry_id`, sodass in Grocy der richtige Bestandsposten reduziert wird.

## [7.1.38]

### Added

- Test: API-Tests für Lazy-Load-Verhalten (`include_ai=false`) und Input-Vorschlagsreihenfolge ergänzt/angepasst.

### Changed

- UI (Navigation): Untere Navigationsleiste (Tab-Bar) wieder verkleinert (geringere Gesamtbreite, engeres Innenpadding und kleinerer Abstand zwischen Tabs).
- UI (Navigation): Tab-Buttons in der Navigationsleiste kompakter gestaltet (kleinere Schrift, reduzierte Mindesthöhe und weniger Innenabstand).
- Suche (Produktauswahl): Varianten-Laden im Such-Tab erfolgt jetzt zweistufig: zuerst sofort Grocy-Treffer (`include_ai=false`), anschließend KI-Erweiterung per Lazy-Load (`include_ai=true`).
- API: `GET /api/dashboard/search-variants` unterstützt den Query-Parameter `include_ai` zur getrennten Steuerung von Grocy-Soforttreffern und KI-Vorschlägen.
- UX (Produktauswahl): Wenn kein exakter Produktname zur Suche passt, wird an erster Stelle ein Eintrag zum Neu-Anlegen mit dem bereinigten Suchtext (ohne Mengenpräfix) angezeigt.
- UI (Produktauswahl): Neuer Quellenhinweis `Neu anlegen` für den oben genannten Eingabe-Vorschlag.
- Pflege: Add-on-Version auf `7.1.38` erhöht.

### Fixed

- Fix (Dashboard Lager): Lade- und ID-Normalisierungslogik für Bestandsprodukte zwischen Rezepte-Tab (Produktauswahl) und Lager-Tab vereinheitlicht.
- Fix (Dashboard Lager): Aktionen im Lager-Tab ("Bearbeiten", "Verbrauchen") nutzen jetzt automatisch `stock_id` und fallen bei fehlender Bestand-ID auf `product_id` zurück.
- UX (Dashboard Lager): Statusmeldung zeigt jetzt transparent an, wie viele Einträge per Produkt-ID-Fallback laufen bzw. gar keine nutzbare ID haben.

## [7.1.37]

### Added

- Test: API-Tests für KI-Vorschläge in der Varianten-Suche ergänzt und bestehende Varianten-Tests an den Detector angepasst.

### Changed

- UI (Lager-Tab): Letzte Button-Anpassung rückgängig gemacht; Aktions-Buttons sind wieder im vorherigen kompakten Stil (`Verbrauchen`, `Ändern`).
- UI (Notify-Tab): Buttons auf den vorherigen Stil der Lager-Tab-Buttons umgestellt (kompakter Button-Look für Regelaktionen, „Neue Regel“ und Test-Aktionen).
- Suche (Produktauswahl): Varianten-Suche im Such-Tab nutzt jetzt KI-gestützte Vorschläge zusätzlich zu Grocy-Teiltreffern.
- UX (Produktauswahl): In der Variantenliste werden jetzt auch KI-Vorschläge als auswählbare Einträge angezeigt, selbst wenn diese Produkte noch nicht in Grocy existieren.
- Pflege: Add-on-Version auf `7.1.37` erhöht.

### Fixed

- API: `/api/dashboard/search-variants` verwendet dieselbe Fallback-Logik wie die Produktsuche und liefert dadurch Grocy- und KI-Varianten konsistent.

## [7.1.36]

### Added

- Test: API-Test ergänzt/erweitert, der für `/api/dashboard/stock-products` den Proxy-Bildpfad für `picture_url` absichert.

### Changed

- UI (Lager-Tab): Aktions-Buttons pro Lagereintrag visuell überarbeitet und auf einen einheitlichen, pillenförmigen Stil umgestellt.
- UI (Lager-Tab): Reihenfolge und Beschriftung der Aktionen verbessert (`✏️ Bearbeiten`, `✅ Verbrauchen`) für klarere Bedienung.
- UX (Lager-Tab): Button-Zustände für deaktivierte Aktionen konsistenter dargestellt und Mobile-Layout für Button-Zeile verbessert.
- UI (Suche/Einkaufsliste): Badge-Breitenbegrenzung gezielt auf Mobile (`max-width: 33.333%`) angewendet; Desktop-Badge-Breite bleibt beim bisherigen festen Layout.
- Pflege: Add-on-Version auf `7.1.36` erhöht.

### Fixed

- Fix (Dashboard/Lager): Produktbilder im Lager-Tab werden jetzt wie im Einkaufs-Tab über den Dashboard-Bildproxy ausgeliefert (`/api/dashboard/product-picture?...`) statt mit rohem Dateinamenpfad, wodurch 404-Fehler für reine Dateinamen verhindert werden.

## [7.1.35]

### Added

- Test: API-Test ergänzt, der den Mengenpräfix für `/api/dashboard/add-existing-product` absichert.

### Changed

- Dashboard (Tab „Lager“): Einträge visuell an das Kartenformat der Einkaufsliste angepasst (Bild + Name/Attribute + Aktions-Buttons).
- Dashboard (Tab „Lager“): Lager-Objekte in 3 Spalten aufgebaut (Bild, Name/Attributliste, Buttons); Attribute werden nun als Liste unter dem Produktnamen angezeigt.
- API/Service: Lagerprodukte liefern jetzt zusätzlich `picture_url`, damit Produktbilder auch im Lager-Tab dargestellt werden können.
- UI (Notify-Tab): Darstellung der Regeleinträge auf ein einheitliches Karten-/Badge-Format umgestellt, angelehnt an Einkaufslisten-Produkte und Lager-Einträge.
- UI (Notify-Tab): Regeleinträge zeigen jetzt konsistent Ereignisse, Kanäle, Priorität und Cooldown.
- UX (Notify-Tab): Notification-Kanäle werden in natürlicher Sprache dargestellt (z. B. „Mobile Push-Benachrichtigung“, „Persistente Benachrichtigung“).
- UI/Texte: Bezeichnungen im Notify-Bereich sprachlich vereinheitlicht (u. a. Tab-Label, Regelverwaltung, Feldbeschriftungen).
- Dashboard (Tab „Lager“): Einträge visuell an das Kartenformat der Einkaufsliste angepasst (Bild + Name/Attribute + Aktions-Buttons).
- Dashboard (Tab „Lager“): Lager-Objekte in 3 Spalten aufgebaut (Bild, Name/Attributliste, Buttons); Attribute werden nun als Liste unter dem Produktnamen angezeigt.
- API/Service: Lagerprodukte liefern jetzt zusätzlich `picture_url`, damit Produktbilder auch im Lager-Tab dargestellt werden können.
- UI (Rezepte): Button „Rezept hinzufügen“ im Rezepte-Tab auf volle Breite gesetzt.
- UI (Rezepte): Grocy- und KI-Rezeptvorschläge auf ein einheitliches Kartenformat vereinheitlicht.
- Verhalten: Gilt jetzt konsistent für bestehende und neu angelegte Produkte in der Produktsuche.
- UI (Suche/Einkaufsliste): Produkt-Badges im Such-/Einkaufstab sind jetzt auf maximal ein Drittel der Breite des Produktelements begrenzt, damit die Produktinfos mehr Platz behalten.
- Pflege: Add-on-Version auf `7.1.35` erhöht.

### Fixed

- UX (Rezepte): Beschreibungstexte in Rezeptvorschlägen vereinheitlicht und auf maximal zwei Zeilen begrenzt, inklusive Fallback-Text bei fehlender Beschreibung.
- Fix (Produktsuche): Beim Hinzufügen eines bestehenden Produkts über die Produktauswahl wird ein Mengenpräfix im Suchtext (z. B. `2 Apfel`) jetzt ausgewertet und als Einkaufsmenge übernommen.

## [7.1.34]

### Added

- KI (Robustheit): Antwortnormalisierung ergänzt, inkl. Zahlen-Normalisierung, Fallbacks und Alias-Mapping von `carbs` -> `carbohydrates`.
- API-Modell: `ProductData` um zusätzliche Nährwertfelder (`carbohydrates`, `fat`, `protein`, `sugar`) ergänzt.
- Test: Unit-Tests für erweiterte Nährwertausgabe und Alias-Mapping ergänzt.
- Test: Unit-Test ergänzt, der sicherstellt, dass `Oliven` nicht automatisch als `Olivenöl` übernommen wird.

### Changed

- KI (lokale Produktanalyse): Prompt für `analyze_product_name` erweitert, damit neben Kalorien/Kohlenhydraten auch weitere bekannte Nährwerte (`fat`, `protein`, `sugar`) zurückgegeben werden.
- Pflege: Add-on-Version auf `7.1.34` erhöht.

### Fixed

- Fix (Produktsuche): Fuzzy-Match übernimmt keine zusammengesetzten Präfix-Treffer mehr (z. B. `Oliven` -> `Olivenöl`), wenn nur ein längeres Kompositum ähnlich ist.

## [7.1.33]

### Added

- Test: Unit-Test ergänzt, der den erfolgreichen Upload über die Base64-Dateinamen-URL absichert.

### Changed

- Pflege: Add-on-Version auf `7.1.33` erhöht.

### Fixed

- Fix (Grocy-Bildupload): Upload berücksichtigt zusätzlich einen Dateinamen-Fallback mit Base64-kodiertem Dateinamen (inkl. Dateiendung), falls Endpunkte den Pfad nur in kodierter Form akzeptieren.
- Fix (Grocy-Bildupload): Reihenfolge bleibt robust: pro URL-Variante werden `PUT` und `POST` mit `api_key` und `curl_compatible` Header-Modus probiert.

## [7.1.32]

### Added

- Test: Unit-Tests für die neue Upload-Reihenfolge über `requests.request(...)` ergänzt/angepasst.

### Changed

- Logging: Warnungen enthalten neben URL und Header-Modus nun auch die fehlgeschlagene HTTP-Methode (`PUT`/`POST`).
- Pflege: Add-on-Version auf `7.1.32` erhöht.

### Fixed

- Fix (Grocy-Bildupload): Produktbild-Upload versucht bei `405/404` jetzt wieder pro URL den Methoden-Fallback `PUT` -> `POST` (jeweils mit `api_key` und `curl_compatible` Header-Modus), bevor zur nächsten URL gewechselt wird.

## [7.1.31]

### Added

- Test: Unit-Tests für Header-Modus-Fallback und URL-Fallback-Reihenfolge ergänzt/angepasst.

### Changed

- Pflege: Add-on-Version auf `7.1.31` erhöht.

### Fixed

- Fix (Grocy-Bildupload): Upload versucht je URL zuerst mit `GROCY-API-KEY` und bei `404/405` zusätzlich einen zweiten PUT im curl-kompatiblen Header-Modus ohne API-Key (`Accept: */*`, `Content-Type: application/octet-stream`).
- Fix (Grocy-Bildupload): URL-Fallback von `/api/files/...` auf `/files/...` bleibt erhalten und nutzt ebenfalls beide Header-Modi.
- Logging: Fallback-Warnungen enthalten jetzt den verwendeten Header-Modus (`api_key` vs. `curl_compatible`).

## [7.1.30]

### Added

- Test: Unit-Tests für Header-Setzung sowie Fallback-Reihenfolge (`PUT` -> `POST` -> URL-Fallback) ergänzt.

### Changed

- Pflege: Add-on-Version auf `7.1.30` erhöht.

### Fixed

- Fix (Grocy-Bildupload): Upload-Request an Grocy-Datei-Endpunkte enthält jetzt zusätzlich `Accept: */*` (entsprechend funktionierendem `curl`-Aufruf).
- Fix (Grocy-Bildupload): Bei `405`/`404` wird pro Upload-URL zuerst `PUT`, dann `POST` probiert, bevor zur nächsten Fallback-URL gewechselt wird.

## [7.1.29]

### Changed

- Pflege: Add-on-Version auf `7.1.29` erhöht.

### Fixed

- Fix (Grocy-Bildupload): HTTP-Fehlerauswertung beim Upload-Fallback korrigiert, damit auch echte `requests.Response`-Objekte mit Status `>=400` (falsey) den Statuscode korrekt liefern.
- Fix (Grocy-Bildupload): Fallback von `/api/files/...` auf `/files/...` greift dadurch zuverlässig bei `405`/`404`.
- Test: Upload-Fallback-Test erweitert, um das falsey-Verhalten von `requests.Response` bei Fehlerstatus abzubilden.

## [7.1.28]

### Added

- Test: Unit-Test ergänzt, der den 405-Fall und den erfolgreichen Fallback-Upload absichert.
- Neu (Startup-Batch): Option `generate_missing_product_images_on_startup` ergänzt, um einmalig nach dem Start Produktbilder für bestehende Produkte ohne Bild zu erzeugen und in Grocy zu hinterlegen.
- Test: API-/Konfigurations-Tests für den neuen Startup-Batch und die neue Add-on-Option ergänzt.

### Changed

- Service: `GrocyClient` um `get_products_without_picture()` erweitert, damit Produkte ohne `picture_file_name` gezielt verarbeitet werden können.
- Pflege: Add-on-Version auf `7.1.28` erhöht.

### Fixed

- Fix (Grocy-Bildupload): Produktbild-Upload versucht bei `404/405` auf `/api/files/...` jetzt automatisch einen Fallback auf `/files/...` ohne `/api`-Präfix.
- Logging: Beim Fallback wird eine Warnung mit der fehlgeschlagenen Upload-URL protokolliert.

## [7.1.27]

### Added

- Test: Unit-Tests für Modell-Fallback bei `403` und URL-Downloadpfad ergänzt.

### Changed

- Pflege: Add-on-Version auf `7.1.27` erhöht.

### Fixed

- Fix (Bildgenerierung): OpenAI-Image-Erstellung nutzt jetzt ein robustes Modell-Fallback (`openai_image_model` -> `dall-e-3` -> `dall-e-2`), wenn der primäre Modellzugriff mit `403 Forbidden` abgelehnt wird.
- Fix (Bildgenerierung): Antwortverarbeitung akzeptiert jetzt sowohl `b64_json` als auch `url`-basierte Bildantworten und lädt URL-Bilder automatisch herunter.

## [7.1.26]

### Added

- UI (Rezepte): Unten auf der Rezeptseite neuen Button „Rezept hinzufügen" ergänzt.
- UI (Rezepte): Neues Modal für Rezept-Erfassung mit Auswahl der Modi „WebScrape", „KI" und „Manuell" ergänzt.
- UI (Rezepte): Für „WebScrape" URL-Eingabe, für „KI" Prompt-Eingabe und für „Manuell" schnelles Rezeptformular mit den wichtigsten Feldern ergänzt.

### Changed

- UX (Rezepte): Methoden-Auswahl im Modal als umschaltbare Panels umgesetzt, damit keine doppelten Codepfade nötig sind.
- Pflege: Add-on-Version auf `7.1.26` erhöht.

## [7.1.25]

### Added

- UI: Zusätzlichen unteren Abstand unter dem Button „Neue Regel“ in der Notify-Ansicht ergänzt.
- Fix (Lager-Dashboard/API): Verbrauchen-Aktion findet Bestandseinträge jetzt sowohl über `id` als auch über `stock_id`, damit Einträge mit nur ergänzter Bearbeitungs-ID wieder korrekt verbraucht werden können.
- Test: API-Test ergänzt, der das Verbrauchen über ein `get_stock_entries`-Ergebnis mit `stock_id` (ohne `id`) absichert.

### Changed

- UI: Scanner-Button in der Suche ohne Hintergrund gestaltet und vertikal an die Überschrift ausgerichtet.
- UI: Aktions-Buttons in der Regelverwaltung („Regel ändern“, „Löschen“) nach rechts ausgerichtet.
- UI (Lager): Buttons „Ändern“ und „Verbrauchen“ verkleinert, untereinander angeordnet und rechtsbündig positioniert.
- Pflege: Add-on-Version auf `7.1.25` erhöht.

## [7.1.24]

### Added

- Neu: Optionale OpenAI-Bildgenerierung für neu erkannte Produkte ergänzt (`image_generation_enabled`, `openai_api_key`, `openai_image_model`).
- Fix (Lager-Dashboard): Fehlende Bearbeitungs-IDs aus `/stock` werden jetzt über `/objects/stock` ergänzt, damit Aktionen „Ändern“ und „Verbrauchen“ wieder für betroffene Einträge funktionieren.
- Test: Unit-Tests für Fallback der Bearbeitungs-ID in `get_stock_products` und `get_stock_entries` ergänzt.

### Changed

- API/Service: Beim Neuanlegen eines Produkts über die Dashboard-Suche wird bei aktiver Option automatisch ein Produktbild über die OpenAI Images API erzeugt, in Grocy hochgeladen und dem Produkt zugewiesen.
- UI: Swipe-Aktionsfläche in der Einkaufsliste auf `138px` verbreitert (`.shopping-item-action`).
- UI: Scanner-Button-Icon auf ein Barcode-Symbol umgestellt (statt Kamera-Emoji), inklusive neuer CSS-Icon-Gestaltung.
- Pflege: Add-on-Version auf `7.1.24` erhöht.

## [7.1.23]

### Changed

- UX (Lager-Dashboard): Aktionen „Verbrauchen“ und „Ändern“ sind für Einträge ohne Bearbeitungs-ID deaktiviert und mit Hinweis versehen.
- UX (Lager-Dashboard): Statusmeldung zeigt an, wenn Einträge ohne Bearbeitungs-ID geladen wurden.
- Pflege: Add-on-Version auf `7.1.23` erhöht.

### Fixed

- Fix: Klick auf den Badge „Menge" in der Einkaufsliste öffnet nicht mehr das Produkt-Popup, sondern erhöht zuverlässig die Menge des Eintrags.
- Fix: Swipe-/Pointer-Interaktion ignoriert jetzt alle interaktiven Badge-Buttons in Listeneinträgen, damit Button-Klicks nicht als Item-Tap verarbeitet werden.
- Fix (Lager-Dashboard): Produkte ohne `stock_id` werden nicht mehr vollständig ausgeblendet; sie werden jetzt in der Liste angezeigt.

## [7.1.22]

### Changed

- UI: Eingabefelder (`input`, `select`, `textarea`) visuell an den restlichen Dashboard-Stil angepasst (einheitliche Rundungen, Schatten, Focus-Ring und weichere Placeholder-Farbe).
- UI: Fokuszustände für Formularelemente verbessert, inklusive klarerer Hervorhebung im Light- und Dark-Theme.
- Pflege: Add-on-Version auf `7.1.22` erhöht.

## [7.1.21]

### Changed

- Pflege: Add-on-Version auf `7.1.21` erhöht.

### Removed

- Cleanup: Rezept-Dialog-spezifische Mengen-Badge-Logik aus dem vorherigen Change entfernt.

### Fixed

- Fix/Scope: Mengen-Badge-Funktion fokussiert auf Produkte in der Einkaufsliste (Badge „Menge“ erhöht weiterhin die einzukaufende Menge direkt im Listen-Eintrag).

## [7.1.20]

### Added

- UI: Neuer Tab „Lager" vor „Notify" ergänzt, inklusive Filterfeld am Anfang der Seite und vollständiger Produktliste aus allen Lagern.
- UI/Funktion: Im Lager-Tab pro Produkt die Aktionen „Verbrauchen" und „Ändern" ergänzt.
- UI/Funktion: Neues Bearbeiten-Popup für Lagerprodukte ergänzt (Menge + MHD).
- API: Neue Endpunkte zum Verbrauchen und Aktualisieren einzelner Lager-Einträge ergänzt.
- Test: API- und Dashboard-Tests für klickbaren Mengen-Badge bei fehlenden Rezeptprodukten ergänzt.
- UI: Scanner-Icon rechts neben der Überschrift „Grocy AI Suche“ ergänzt; öffnet den Barcode-Scanner als Modal.

### Changed

- Service: Grocy-Client um Methoden zum Verbrauchen und Aktualisieren von Lager-Einträgen erweitert.
- UI/Funktion: Der Badge für fehlende Produkte im Rezept-Dialog ist jetzt klickbar und erhöht die Menge der „einzukaufenden“ Produkte direkt in der Einkaufsliste um 1.
- API: `POST /api/dashboard/recipe/{recipe_id}/add-missing` akzeptiert optional Mengen pro Produkt (`products: [{id, amount}]`) und nutzt bestehenden Codepfad zum Hinzufügen auf die Einkaufsliste.
- UI: Untere Tabbar auf drei Tabs reduziert (Einkauf, Rezepte, Notify).
- Pflege: Add-on-Version auf `7.1.20` erhöht.

### Removed

- UI: Scanner-Tab aus der unteren Navigation entfernt und als Popup hinter ein Barcode-/Scanner-Icon verschoben.

## [7.1.19]

### Changed

- UI: Produkt-Badges in der Einkaufsliste erneut etwas schmaler gemacht, damit sie weniger Breite einnehmen.
- Pflege: Add-on-Version auf `7.1.19` erhöht.

## [7.1.18]

### Added

- Test: API-Tests für Mengenpräfix in Suche und Variantensuche ergänzt.
- UI: Wrapper-Div für Rezeptbilder im Popup um eine `min-height` ergänzt, damit der Bildbereich stabil bleibt.
- UI: Notizfeld direkt im Produkt-Detail-Popup unter der Überschrift ergänzt.

### Changed

- Funktion: Produktsuche versteht jetzt Mengenpräfixe wie `2 nudeln` und verwendet die erkannte Menge beim Hinzufügen zur Einkaufsliste.
- Funktion: Variantensuche ignoriert Mengenpräfixe wie `2 apf`, sodass weiterhin passende Produkte gefunden werden.
- UI: Bei Auswahl eines Produkts aus der Produktauswahl wird bei Eingaben wie `2 apf` ebenfalls die Menge `2` übernommen.
- UI: Rezeptbild im Rezept-Detail-Popup auf Standardgröße zurückgesetzt (keine erzwungene Vergrößerung mehr).
- UX/Logik: Notizen werden beim Schließen des Produkt-Popups automatisch gespeichert, falls sich der Inhalt geändert hat.
- Pflege: Add-on-Version auf `7.1.18` erhöht.

### Removed

- UI: Die Karte/Spalte „Optionen“ wurde aus dem Benachrichtigungs-Dashboard entfernt.
- UI: Badge „Notiz bearbeiten“ in der Einkaufsliste entfernt.

## [7.1.17]

### Changed

- Pflege: Add-on-Version auf `7.1.17` erhöht.

### Fixed

- Fix: Syntaxfehler in `dashboard.js` behoben (`Unexpected end of input`), verursacht durch einen unvollständig gebliebenen Event-Handler im Shopping-List-Click-Handling.

## [7.1.16]

### Added

- Add-on: Neue Option `notification_global_enabled` in `config.json` (`options` + `schema`) ergänzt.

### Changed

- API: Notification-Overview und Settings-Update übernehmen den globalen Enabled-Status jetzt aus den Add-on-Optionen (`options.json`) statt aus der Integration.
- UI: Hinweistext in der Benachrichtigungs-Ansicht auf Add-on/App-Optionen angepasst.
- Pflege: Add-on-Version auf `7.1.16` erhöht.

### Fixed

- Fix: Doppelte Deklarationen in `dashboard.js` entfernt, die im Browser den Fehler `Identifier 'NOTIFICATION_EVENT_LABELS' has already been declared` ausgelöst haben.
- Korrektur: Die globale Notification-Aktivierung wurde aus den Home-Assistant-Integrationsoptionen entfernt und stattdessen in die Add-on/App-Optionen verlagert (gleicher Bereich wie API-Keys).

## [7.1.15]

### Added

- Integration: Neue Home-Assistant-Option `notification_global_enabled` ergänzt, um Benachrichtigungen global über die Integrations-Optionen zu aktivieren/deaktivieren.
- Test: API-Test ergänzt, der Timeout-Verhalten beim Barcode-Lookup absichert.

### Changed

- Logik: NotificationManager übernimmt den globalen Aktivierungsstatus aus den Integrations-Optionen und setzt damit die globale Notification-Freigabe zentral.
- Pflege: Add-on-Version auf `7.1.15` erhöht.

### Removed

- UI: Die globale Notification-Option „Benachrichtigungen global aktiv" wurde aus dem Dashboard entfernt und als Hinweis in den Bereich „Optionen" übernommen.

### Fixed

- Fix: Barcode-Lookup liefert bei OpenFoodFacts-Timeouts keinen 500-Fehler mehr, sondern fällt robust auf Grocy bzw. "nicht gefunden" zurück.
- Fix: Syntaxfehler in `GrocyClient.update_shopping_list_item_amount` behoben (fehlender Abschluss des `requests.put`-Aufrufs), sodass der API-Start nicht mehr mit `SyntaxError` abbricht.

## [7.1.14]

### Added

- API: Neuer Endpoint zum Erhöhen der Menge einzelner Einkaufslisten-Einträge ergänzt.
- Tests: API-/Client-Tests für das Erhöhen der Einkaufslisten-Menge ergänzt.
- Neu: Notizen für einzelne Einkaufslisten-Einträge sind im Dashboard direkt bearbeitbar (eigener Notiz-Dialog pro Eintrag).
- API: Neuer Endpoint `PUT /api/dashboard/shopping-list/item/{shopping_list_id}/note` zum Aktualisieren von Einkaufslisten-Notizen.

### Changed

- UI: Badges in der Einkaufsliste auf eine einheitliche Breite gebracht, damit „Menge“ und „MHD" konsistent groß angezeigt werden.
- UI/Funktion: „Menge" in der Einkaufsliste ist jetzt klickbar und erhöht die Einkaufsmenge des ausgewählten Produkts um 1.
- UI: Rezeptbild im Rezept-Detail-Popup deutlich vergrößert, damit nicht nur ein schmaler Bildstreifen sichtbar ist.
- Logik: Notizänderungen bleiben auf dem Einkaufslisten-Eintrag und verändern keine Grocy-Produktstammdaten; vorhandene MHD-Marker bleiben beim Speichern erhalten.
- Pflege: Add-on-Version auf `7.1.14` erhöht.

### Removed

- UI: Produktlisten im Rezept-Detail-Popup auf volle Breite umgestellt (Einrückung entfernt), damit Listeneinträge nicht mehr abgeschnitten oder versetzt dargestellt werden.

### Fixed

- Fix: Rezept-Detail-Popup erhält wieder einen klar sichtbaren, modernen Schließen-Button oben rechts, damit sich der Dialog zuverlässig schließen lässt.

## [7.1.13]

### Added

- UI: In der Regelverwaltung pro Regel einen neuen Button „Regel ändern“ ergänzt; bestehende Regeln lassen sich nun im Popup bearbeiten und speichern.

### Changed

- UI: Regel-Popup visuell an das restliche Dashboard angepasst (klarerer Titel/Untertitel, bessere Formular- und Mehrfachauswahl-Darstellung, konsistente Aktionsleiste).
- Pflege: Add-on-Version auf `7.1.13` erhöht.

## [7.1.12]

### Changed

- UI: Events in der Benachrichtigungsansicht werden jetzt in normaler Sprache angezeigt (Regelliste und Historie).
- UI: Beim Erstellen neuer Regeln werden Events und Zielgeräte als Mehrfachauswahl-Dropdowns dargestellt.
- UI: Der Button „Neue Regel“ wurde unter die Überschrift „Regelverwaltung“ verschoben.
- Pflege: Add-on-Version auf `7.1.12` erhöht.

## [7.1.11]

### Added

- UI: Rezeptbild im Popup mit leichtem visuellen Effekt (dezenter Verlauf, Schatten und minimale Sättigungs-/Kontrastanhebung) ergänzt.
- Test: API-Test ergänzt, der absichert, dass Rezept-Thumbnail-URLs im Dashboard über `toImageSource(...)` laufen.

### Changed

- UI: Rezeptbild wird jetzt auch im Rezept-Detail-Popup am oberen Rand angezeigt.
- Pflege: Add-on-Version auf `7.1.11` erhöht.

### Fixed

- Fix: Rezeptbilder in den Rezeptvorschlägen werden jetzt über dieselbe URL-Normalisierung wie andere Bilder gerendert (`toImageSource`), damit sie auch bei Ingress/Proxy/HTTPS-Mischszenarien wieder zuverlässig angezeigt werden.

## [7.1.7]

### Added

- UI: Neues Karten-Layout und responsive Darstellung für die Optionsseite ergänzt, damit die Bereiche auf Mobilgeräten untereinander statt nebeneinander angezeigt werden.

### Changed

- UI: Benachrichtigungs-Optionenseite im Dashboard neu strukturiert und in klar getrennte Bereiche (Optionen, Geräte, Regeln, Testcenter, Historie) gegliedert.
- UI: Globalen Schalter und Speichern-Aktion in einer eigenen, verständlicheren Optionskarte zusammengeführt.
- Pflege: Add-on-Version auf `7.1.7` erhöht.

## [7.1.6]

### Added

- Test: API-Test ergänzt, der den `%3F...%3D...`-Fall im `src`-Parameter absichert.

### Changed

- Pflege: Add-on-Version auf 7.1.6 erhöht.

### Fixed

- Fix: Bildproxy normalisiert jetzt auch fehlerhaft encodierte `src`-URLs, bei denen `?force_serve_as=picture` als `%3Fforce_serve_as%3Dpicture` im Pfad steckt, und lädt das Bild danach korrekt.

## [7.1.5]

### Added

- Test: API-Test ergänzt, der den 404-Fallbackpfad des Bildproxys absichert.
- Test: API-Test ergänzt, der den 404-Fallbackpfad des Bildproxys absichert.

### Changed

- Pflege: Add-on-Version auf 7.1.5 erhöht.
- UI: Kanal und Severity wurden aus den allgemeinen Notification-Einstellungen in das Regel-Popup verschoben.

### Fixed

- Fix: Dashboard-Bildproxy versucht bei 404 auf `/api/files/...` automatisch die passende Fallback-URL `/files/...` (und umgekehrt), damit Rezeptbilder hinter Home-Assistant/Grocy-Setups zuverlässig laden.
- Fix: Beim Erstellen neuer Regeln werden Kanal und Severity jetzt direkt aus dem Popup an die Regel gebunden und gespeichert.
- Fix: Dashboard-Bildproxy versucht bei 404 auf `/api/files/...` automatisch die passende Fallback-URL `/files/...` (und umgekehrt), damit Rezeptbilder hinter Home-Assistant/Grocy-Setups zuverlässig laden.

## [7.1.4]

### Added

- Neu: Notification-Dashboard liefert jetzt mehrere sinnvolle, vordefinierte Standardregeln (Einkauf fällig, niedriger Bestand, fehlende Rezept-Zutaten).

### Changed

- UI: „Regel anlegen" aus der Notification-Seite in ein eigenes Popup verschoben und über den neuen Button „Neue Regel" aufrufbar gemacht.
- Anpassung: Notification-Einstellungen und Regeln werden nun pro Home-Assistant-Benutzer gespeichert; der aktuell angemeldete Nutzer wird automatisch verwendet.
- UI: `.topbar-content` im Dashboard-Header auf `width: 100%` gesetzt.

### Fixed

- Fix: Frontend-Fehler `getAuthHeaders is not defined` behoben.

## [7.1.3]

### Changed

- UI: Darkmode-Button im Header in die Titelzeile verschoben und rechts neben „Smart Pantry Dashboard“ ausgerichtet.

### Fixed

- Fix: Rezeptbilder in den Rezeptvorschlägen werden jetzt über den Dashboard-Bild-Proxy ausgeliefert, damit sie auch auf mobilen Geräten über Ingress zuverlässig laden.

## [7.1.2]

### Changed

- Anpassung: Kamera-Zoom des Barcode-Scanners auf 1.4x reduziert.

## [7.1.1]

### Added

- Neu: Notification-Dashboard direkt in die App integriert (Geräteverwaltung, globale Einstellungen, Regelverwaltung, Testcenter, Historie) inklusive neuem Navigations-Tab.
- Neu: FastAPI-Endpunkte für Notification-Dashboard ergänzt (`/api/dashboard/notifications/*`) mit persistenter JSON-Ablage unter `/data/notification_dashboard.json`.

### Changed

- Pflege: Versionen auf `7.1.1` erhöht.

## [7.1.0]

### Added

- Neu: Enterprise-Notification-Architektur in der Home-Assistant-Integration eingeführt (Event-Modelle, Rule Engine, Dispatcher, persistenter Store und Orchestrator-Services).
- Neu: Home-Assistant-Services für Notification-Events und Testcenter ergänzt (`notification_emit_event`, `notification_test_device`, `notification_test_all`, `notification_test_persistent`).
- Neu: Architekturdokumentation und Dashboard-Spezifikation für Geräteverwaltung, Regeln, Testcenter und Historie ergänzt.

### Changed

- Pflege: Versionsstände von Add-on und Integration auf `7.1.0` aktualisiert.

## [7.0.38]

### Changed

- UI: Lightmode-Theme-Icon auf dunklen Halbmond (`☾`) geändert.
- UI: Theme-Button nicht mehr `fixed`, sondern wieder mitscrollend im Header positioniert.
- Pflege: Add-on-Version auf 7.0.38 erhöht.

## [7.0.37]

### Changed

- UI: Theme-Button als modernes, schwebendes Icon ohne Hintergrund gestaltet (nur Sonne/Mond-Icon mit subtiler Floating-Interaktion).
- UI: Produkt-Badges in Einkaufselementen und in der Produktauswahl auf der Rezeptseite konsequent ganz nach rechts ausgerichtet.

### Fixed

- Fix: Swipe-Gesten in der Einkaufsliste auf mobilen Geräten empfindlicher gemacht (direktere Fingerbewegung, geringere Auslösedistanz), damit „Kaufen“/„Löschen“ zuverlässig auslösbar ist.

## [7.0.36]

### Changed

- UI: Button „Aktualisieren“ in der Einkaufsliste nutzt jetzt den invertierten Primary-Stil, damit er im Darkmode nicht zu dunkel erscheint.

## [7.0.35]

### Changed

- UI: Swipe-Aktionen in der Einkaufsliste auf eine moderne, iOS-inspirierte Implementation mit flüssigem Drag, dynamischen Action-Hintergründen und sanfter Commit-Animation umgestellt.
- Pflege: Add-on-Version auf 7.0.35 erhöht.
- UI: Im Bereich „Einkaufsliste“ den Button „Aktualisieren“ unter die Überschrift verschoben, damit der Titel nicht mehr neben dem Button umbricht.

## [7.0.34]

### Changed

- UI: Button „Rezeptvorschläge laden“ unter den Suchbutton für bald ablaufende Produkte verschoben und mit zusätzlichem Abstand davor/danach versehen.
- Pflege: Add-on-Version auf 7.0.34 erhöht.

### Removed

- Anpassung: Scanner-Beschreibungstext „Mit der Handykamera scannen und Produktdaten abrufen.“ aus dem Dashboard entfernt.

### Fixed

- Fix: CHANGELOG-Format für Home Assistant angepasst (versionierte Abschnitte statt reinem "Unreleased"), damit Änderungen korrekt erkannt werden.

## [7.0.33]

### Added

- Neu: Home-Assistant-Integration ergänzt um Debug-Sensoren für die letzte und durchschnittliche KI-Antwortzeit (ms).
- Neu: Bei Grocy-Rezeptvorschlägen werden jetzt die konkreten Rezeptzutaten aus Grocy angezeigt.
- Neu: `ARCHITECTURE.md` ergänzt mit Schichtenmodell, Verantwortlichkeiten und Erweiterungsleitfaden.

### Changed

- Pflege: Versionsstände für Add-on und Integration angehoben und im Projekt konsistent dokumentiert.
- Anpassung: Dashboard visuell neu ausgearbeitet mit shadcn/ui-inspirierter Optik (Topbar, Kartenlayout, modernisierte Farb- und Button-Systematik).
- Anpassung: Dashboard-Theme auf eine neue dunkle Farbwelt mit Mint-Akzenten, weicheren Karten und angepassten Button-/Badge-Farben umgestellt.
- Anpassung: Zutaten aus Grocy-Rezepten enthalten jetzt Mengenangaben mit Einheiten-Attribution (z. B. Stk., Gramm), wenn in Grocy vorhanden.
- Anpassung: Im Dashboard werden nun bis zu 3 Grocy- und 3 KI-Rezepte angezeigt.

### Removed

- Anpassung: Beschreibungstext unter „Grocy AI Suche“ entfernt und Aktivitäts-Spinner in die Hauptüberschrift verschoben.
- Entfernt: konfigurierbarer `scanner_llava_prompt` in den Add-on-Optionen.

### Fixed

- Fix: Darkmode-Button verwendet jetzt in beiden Themes eine gut lesbare Schriftfarbe.
- Fix: Dashboard-Header und zentrale UI-Elemente auf bessere Umbrüche bei schmalen Viewports optimiert.
- Fix: Dashboard-Layout setzt `html` auf `height: 100%` (inkl. `body`-Mindesthöhe), damit der Hintergrund die volle Viewport-Höhe abdeckt.
- Fix: Dashboard-Farbkontraste für Light-/Dark-Mode vereinheitlicht, damit aktive Tabs und Aktionsbuttons in beiden Themes gut lesbar bleiben.
- Fix: Architekturtest-Datei auf `tests/architecture/test_layering.py` umbenannt, damit sie zuverlässig von `pytest` gesammelt und ausgeführt wird.

### Security

- Neu: `scanner_llava_min_confidence` (1-100) als Add-on-Option zur Steuerung der benötigten Sicherheit.
- Anpassung: LLaVA-Prompt wird nun intern erzeugt und enthält die konfigurierbare Mindest-Sicherheit sowie die Vorgabe, bei zu geringer Sicherheit `NULL` zu antworten.

### Documentation

- Doku: README vollständig strukturell überarbeitet (Zielbild, Architektur, Konfiguration, API-Endpunkte, Entwicklungsabläufe).
- Doku: `README.md` um Verweis auf die Architektur-Dokumentation und präzisen Architekturtest-Pfad erweitert.
