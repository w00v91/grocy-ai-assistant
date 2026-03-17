# Changelog

All notable changes to this project are documented in this file.

## 7.2.2

- Fix (Dashboard/Lager bearbeiten): Das Aktualisieren von Menge und Nährwerten funktioniert jetzt auch für Produkte aus „Alle Produkte anzeigen", selbst wenn dafür noch kein Bestandseintrag existiert.
- Test: API-Test ergänzt, der den Update-Pfad für nicht vorrätige Produkte (nur `product_id`, ohne `stock_id`) absichert.
- Pflege: Add-on-Version auf `7.2.2` erhöht.

## 7.2.1

- Neu (Konfiguration): Option `initial_info_sync` ergänzt. Wenn aktiviert, wird beim Start ein initialer KI-Info-Sync für bestehende Produkte ausgeführt.
- Neu (Startup-Sync): Produkte mit fehlenden Feldern bei `calories`, Nährwert-Userfields (`carbohydrates`, `fat`, `protein`, `sugar`) oder `default_best_before_days` werden über die KI analysiert und selektiv ergänzt.
- Pflege: Add-on-Version auf `7.2.1` erhöht.

## 7.1.107

- Fix (Dashboard/"Suchen & hinzufügen"): Die serverseitige Mengen-Reconciliation greift jetzt auch im direkten Suchpfad (`/api/dashboard/search`), wenn ein vorhandenes Produkt sofort hinzugefügt wird.
- Fix (Dashboard/"Suchen & hinzufügen"): Auch beim Neuanlegen eines Produkts über die Suche wird die Zielmenge nach dem Add verifiziert und bei Bedarf auf den erwarteten Wert korrigiert.
- Test: API-Test ergänzt, der den Suchpfad mit Backend-Verhalten simuliert, bei dem zunächst nur `+1` gesetzt wird, und die Korrektur auf die gewünschte Menge absichert.
- Pflege: Add-on-Version auf `7.1.107` erhöht.

## 7.1.106

- Fix (API/Einkaufsliste/Menge): Beim Hinzufügen eines bestehenden Produkts wird die Zielmenge jetzt serverseitig verifiziert und bei Bedarf direkt auf den erwarteten Wert korrigiert. Dadurch greifen Mengenpräfixe (z. B. `2 Backpulver`) auch dann korrekt, wenn Grocy intern nur `+1` verbucht.
- Fix (API/Einkaufsliste/Menge): Der gleiche Korrekturpfad deckt sowohl bestehende als auch neu angelegte Einkaufslisten-Einträge ab.
- Test: API-Tests ergänzt, die Backend-Verhalten simulieren, bei dem `add-product` nur Menge `1` setzt, und die anschließende Korrektur auf die erwartete Menge prüfen.
- Verbesserung (Dashboard/Produktbilder): Der Bild-Proxy ergänzt für Produktbilder jetzt standardmäßig `force_serve_as=picture`, damit Grocy-Datei-URLs konsistent als Bild ausgeliefert werden (inkl. weiterhin größenabhängigem `best_fit_width`/`best_fit_height`).
- Logging: Das Umschreiben von Produktbild-URLs auf den konfigurierten Grocy-Host wurde von INFO auf DEBUG reduziert, um Polling-bedingtes Log-Spam im Normalbetrieb zu vermeiden.
- Test: API-Tests für Produktbild-Proxy-URLs auf den neuen Standard-Queryparameter angepasst.
- UI (Dashboard/Produkt ändern Popup): Produktbilder werden im "Bestand ändern"-Popup jetzt in voller Breite angezeigt, damit Details besser erkennbar sind.
- Pflege: Add-on-Version auf `7.1.106` erhöht.

## 7.1.105

- Fix (Dashboard/Produktvarianten): Beim Hinzufügen bestehender Varianten wird die erkannte Menge jetzt zusätzlich im `product_name`-Präfix an die API übergeben, sodass die Menge serverseitig zuverlässig erkannt und auf die Einkaufsliste übernommen wird.
- Fix (API/Antworttext): Bei mengenpräfixierten Produktnamen wird die Erfolgsmeldung bereinigt (ohne Präfix), z. B. `Apfel wurde zur Einkaufsliste hinzugefügt.` statt `2 Apfel ...`.
- Test: API-Test für bereinigte Erfolgsmeldung bei mengenpräfixiertem Produktnamen ergänzt.
- Pflege: Add-on-Version auf `7.1.105` erhöht.

## 7.1.104

- Fix (Dashboard/Produktvarianten): Die erkannte Menge aus dem Suchpräfix wird jetzt auch beim Klick auf KI-/Input-Varianten (Pfad über erneute Produktsuche) korrekt mitgeführt, sodass die Menge zuverlässig auf der Einkaufsliste ankommt.
- Pflege: Add-on-Version auf `7.1.104` erhöht.

## 7.1.103

- Fix (Dashboard/Produktvarianten): Mengenpräfixe in der Suche (z. B. `2 backpulver`) werden bei der Varianten-Auswahl jetzt bis zum Klick mitgeführt, sodass beim Auswählen einer Variante die erkannte Menge korrekt (hier `2`) auf die Einkaufsliste geschrieben wird.
- UI (Dashboard/Produktvarianten): In der Varianten-Auswahl wird bei erkannter Mengenpräfix-Suche ein rundes Mengen-Badge oben rechts auf der Produktkarte angezeigt.
- Pflege: Add-on-Version auf `7.1.103` erhöht.

## 7.1.102

- UI (Einkaufsliste/Produkt-Popup): Label `Standardmenge` im Produkt-Popup der Einkaufsliste in `Geschätzte Haltbarkeit` umbenannt.
- Pflege: Add-on-Version auf `7.1.102` erhöht.

## 7.1.101

- Fix (Neues Produkt/Nährwerte): Bei der Neuanlage über `/api/dashboard/search` werden KI-Nährwerte für `carbohydrates`, `fat`, `protein` und `sugar` jetzt konsequent über die Userfield-Logik weitergereicht (`update_product_nutrition` → `/userfields/products/{id}`), statt im Create-Payload mitzuschwimmen.
- Bereinigung (Neues Produkt): Doppelte Aufrufe für Nährwert- und `default_best_before_days`-Update nach dem Bild-Upload entfernt.
- Test: API-Test ergänzt, der sicherstellt, dass Makro-Nährwerte nicht im `create_product`-Payload landen und korrekt an `update_product_nutrition` übergeben werden.
- Pflege: Add-on-Version auf `7.1.101` erhöht.

## 7.1.100

- Fix (API/Grocy/Nährwerte): `update_product_nutrition` nutzt für `carbohydrates`, `fat`, `protein` und `sugar` jetzt ausschließlich den korrekten Userfield-Endpunkt (`PUT /userfields/products/{id}`); der fehlerhafte Erstversuch über das Produkt-Objekt wurde entfernt.
- Verbesserung (Dashboard/Produkt ändern Popup): Beim Öffnen des Popups werden Nährwerte zusätzlich über einen dedizierten API-Endpunkt geladen, der die Userfields korrekt aus Grocy einliest. Dadurch werden die Felder im Popup konsistent mit den Grocy-Userfields angezeigt.
- Neu (API): Endpoint `GET /api/dashboard/products/{product_id}/nutrition` ergänzt.
- Test: Unit- und API-Tests für Userfield-Nährwerte und den neuen Nutrition-Endpoint ergänzt/angepasst.
- Pflege: Add-on-Version auf `7.1.100` erhöht.

## 7.1.99

- Fix (API/Grocy/Nährwerte): Wenn das Produkt-Objekt-Update (`/objects/products/{id}`) mit einem nicht weiter reduzierbaren 400-Fehler (z. B. `no such column: fat`) scheitert, wird der Ablauf nicht mehr vorzeitig abgebrochen; der Userfield-Sync läuft trotzdem weiter.
- Verbesserung (Logging): Die Warnung beschreibt jetzt klar, dass nur das Objekt-Update übersprungen wird und der Userfield-Sync weiterläuft.
- Test: Unit-Test ergänzt, der den Fallback-Pfad mit 400 auf Objekt-Update und erfolgreichem Userfield-Update absichert.
- Pflege: Add-on-Version auf `7.1.99` erhöht.

## 7.1.98

- Änderung (API/Grocy/Userfields): Beim Nährwert-Update werden `carbohydrates`, `fat`, `protein` und `sugar` zusätzlich auf den Grocy-Userfields des Produkts gesetzt (`PUT /userfields/products/{id}`).
- Robustheit (API/Grocy/Userfields): Wenn der Userfield-Endpunkt nicht verfügbar ist (z. B. 404/405) oder einzelne Felder unbekannt sind, wird defensiv mit reduziertem Payload weitergemacht, ohne den gesamten Request scheitern zu lassen.
- Test: Unit-Tests für Userfield-Sync und Fallback-Verhalten ergänzt/angepasst.
- Pflege: Add-on-Version auf `7.1.98` erhöht.

## 7.1.97

- Fix (API/Lager-Tab/Nährwerte speichern): Beim Speichern wird der Inventar-Endpunkt nur noch aufgerufen, wenn sich die Menge tatsächlich geändert hat. Damit schlagen reine Nährwert-Änderungen (z. B. Kalorien) nicht mehr mit Grocy-400 im `/inventory`-Endpoint fehl.
- Test: API-Test ergänzt, der bei unveränderter Menge keinen Aufruf von `set_product_inventory` mehr erwartet und trotzdem das Nährwert-Update prüft.
- Pflege: Add-on-Version auf `7.1.97` erhöht.

## 7.1.96

- Fix (Grocy Inventory-API): `set_product_inventory` nutzt weiterhin `POST`, versucht bei 400-Antworten mit `stock_entry_id` aber automatisch einen zweiten Request ohne `stock_entry_id`, damit Grocy-Instanzen mit restriktiverem Schema weiterhin korrekt aktualisiert werden.
- Test: Unit-Test ergänzt, der den Retry ohne `stock_entry_id` absichert.
- Pflege: Add-on-Version auf `7.1.96` erhöht.

## 7.1.95

- Fix (Lager-Tab/ID-Normalisierung): `consume`, `update` und `delete` akzeptieren jetzt optional `product_id` als eindeutigen Hint und priorisieren dadurch den korrekten Produkteintrag auch bei kollidierenden numerischen `stock_id`/`product_id`-Werten.
- Fix (Dashboard-Frontend/Lager): Requests aus dem Lager-Tab senden bei Verbrauchen, Speichern und Löschen zusätzlich `product_id` als Query-Parameter, damit serverseitig immer die richtige Produkt-ID aufgelöst wird.
- Test: API-Tests für die neue `product_id`-Priorisierung bei Verbrauchen, Speichern und Löschen ergänzt.
- Pflege: Add-on-Version auf `7.1.95` erhöht.

## 7.1.94

- Fix (Dashboard/Produktvorschläge): Beim Tippen werden nur noch Grocy-Produktvorschläge geladen; zusätzliche KI-Varianten werden im Vorschlags-Request nicht mehr nachgeladen.
- Fix (Dashboard/Neu anlegen): `force_create` umgeht jetzt die vorherige Produkterkennung, damit bei „Neu anlegen" wirklich das eingegebene Produkt neu erstellt wird.
- Fix (API/Lager-Tab/Speichern): Mengenänderungen setzen den Bestand nun konsistent über den Grocy-Inventar-Endpunkt (`POST /stock/products/{id}/inventory`) mit aufgelöster `stock_entry_id`; dadurch treten keine 400er durch falsche Objekt-IDs in `PUT /objects/stock/{id}` mehr auf.
- Pflege: Add-on-Version auf `7.1.94` erhöht.

## 7.1.93

- Fix (Dashboard/Neuanlage): Bei „Neu anlegen" wird jetzt immer der exakt eingegebene Produktname verwendet (kein unbeabsichtigtes Ersetzen durch KI-ähnliche Vorschläge).
- Fix (API/Lager-Tab/Löschen): Löschen im Lager-Tab entfernt nun Produkte korrekt über `DELETE /objects/products/{product_id}` statt über einen Stock-Objekt-Endpunkt.
- Fix (API/Lager-Tab/Menge=0): Beim Speichern mit Menge `0` wird jetzt der Grocy-Inventar-Endpunkt (`POST /stock/products/{id}/inventory` mit `new_amount`) verwendet, damit der Bestand korrekt auf 0 gesetzt/aufgebraucht wird.
- Test: Unit-Tests für die neuen Grocy-Client-Endpunkte (`set_product_inventory`, `delete_product`) ergänzt.
- Pflege: Add-on-Version auf `7.1.93` erhöht.

## 7.1.92

- Fix (Dashboard-Test/Storage): `loadStorageProducts` ist wieder mit der erwarteten Funktionssignatur (`function loadStorageProducts()`) deklariert, sodass der statische Dashboard-Test wieder stabil grün läuft.
- Änderung (API/Grocy/Nährwerte): Fallback-Felder für Nährwerte entfernt; Updates senden bei Kalorien jetzt nur noch `calories` (kein `energy`) und bei Kohlenhydraten nur `carbohydrates` (kein `carbs`).
- Änderung (API/Grocy/Anzeige): Kohlenhydrate werden in Listenansichten wieder ausschließlich aus `carbohydrates` gelesen (ohne `carbs`-Fallback).
- Test: Unit-Tests auf das vereinfachte, fallback-freie Payload/Mapping angepasst.
- Pflege: Add-on-Version auf `7.1.92` erhöht.

## 7.1.91

- Fix (API/Grocy/Nährwerte): Beim Nährwert-Update wird `carbs` jetzt zusätzlich zu `carbohydrates` gesendet (analog zu `calories` + `energy`), um unterschiedliche Grocy-Schemata besser zu unterstützen.
- Fix (API/Grocy/Anzeige): Beim Lesen von Produktdaten wird für Kohlenhydrate nun erst `carbohydrates` und fallback auf `carbs` verwendet.
- Test: Unit-Tests für `carbs`-Fallback beim Lesen und erweitertes Nährwert-Payload ergänzt.
- Pflege: Add-on-Version auf `7.1.91` erhöht.

## 7.1.90

- Fix (API/Grocy/Nährwerte): Wenn Grocy ein Nährwert-Update mit 400 ablehnt und keine unbekannte Spalte aus der Fehlermeldung extrahiert werden kann, wird das Update nun defensiv übersprungen statt den gesamten Request mit 500 abzubrechen.
- Verbesserung (Logging): Für diesen Fall wird eine klare Warnung mit Response-Body protokolliert.
- Test: Unit-Test ergänzt, der den 400-Fehler ohne extrahierbare Spalte absichert.
- Pflege: Add-on-Version auf `7.1.90` erhöht.

## 7.1.88

- Fix (Produktanlage/Nährwerte): Das Nährwert-Update nach der Produktanlage ist jetzt abwärtskompatibel. Bei Grocy-Instanzen ohne einzelne Spalten (z. B. `calories`, `carbohydrates`) werden unbekannte Felder schrittweise entfernt statt den gesamten Request mit 500 scheitern zu lassen.
- Verbesserung (Produktanlage/Energie): Zusätzlich zu `calories` wird beim Nährwert-Update auch `energy` mitgegeben, damit unterschiedliche Grocy-Schemata besser unterstützt werden.
- Fix (Produktanlage/Bilder): Bildgenerierung/-Zuordnung läuft wieder vor dem Nährwert-Update, sodass Produktbilder auch dann angehängt werden, wenn ein Teil der Nährwertfelder nicht unterstützt wird.
- Fix (API/Lager-Tab): Speichern im Produkt-Popup verwendet bei fehlender `stock_id` nun zuerst eine serverseitige Auflösung über `product_id` + `location_id`, damit die Menge als absoluter Wert aktualisiert wird (statt unbeabsichtigt `+1` über den Add-Endpoint).
- Fix (API/Lager-Tab): Nur wenn kein Bestandseintrag auflösbar ist, wird weiterhin ein neuer Eintrag erstellt.
- Test: API- und Unit-Tests für die neue Stock-ID-Auflösung ergänzt.
- Pflege: Add-on-Version auf `7.1.88` erhöht.

## 7.1.87

- Fix (API/Lager-Tab): Wenn ein Produkt über die Produkt-ID gefunden wird, aber kein nutzbarer `stock_id` vorhanden ist, wird beim Speichern nun automatisch ein Bestandseintrag über Grocy erstellt statt mit „Ungültiger Bestandseintrag" abzubrechen.
- Fix (API/Lager-Tab): Für Produkte ohne bestehenden Bestandseintrag wird Menge `0` beim Speichern mit klarer 400-Fehlermeldung abgewiesen.
- Test: API- und Unit-Tests für den neuen Fallback-Pfad ergänzt.
- Pflege: Add-on-Version auf `7.1.87` erhöht.

## 7.1.86

- Fix (UI/Lager-Tab): Mengenänderungen im Produkt-Popup akzeptieren wieder Kommawerte (z. B. `1,5`) und werden korrekt gespeichert.
- Fix (Einkaufsliste/MHD): Beim Hinzufügen zur Einkaufsliste wird ein berechnetes MHD jetzt standardmäßig aus `default_best_before_days` (Produktwert oder KI-Wert) als `heute + Tage` gesetzt.
- Verbesserung (Produktanlage/KI-Fallback): Falls in Grocy noch kein `default_best_before_days` für das neu angelegte Produkt gesetzt ist, wird der von der KI gelieferte Wert nachträglich am Produkt gespeichert.
- Fix (Produktanlage/Nährwerte): KI-Nährwerte (inkl. Kalorien/Energie) werden nach dem Erstellen neuer Produkte jetzt zuverlässig auf das Grocy-Produkt geschrieben.
- Pflege: Add-on-Version auf `7.1.86` erhöht.

## 7.1.89

- Fix (API/Grocy): `PUT /objects/stock/{id}` sendet `best_before_date` nur noch, wenn tatsächlich ein Datum gesetzt ist; leere Werte werden nicht mehr als `null` übertragen, um 400-Fehler beim Speichern im Produkt-Popup zu vermeiden.
- Test: Unit-Test ergänzt, der sicherstellt, dass bei leerem MHD nur `{"amount": ...}` gesendet wird.
- Pflege: Add-on-Version auf `7.1.89` erhöht.

## 7.1.88

- Fix (API/Lager-Tab): Speichern im Produkt-Popup verwendet bei fehlender `stock_id` nun zuerst eine serverseitige Auflösung über `product_id` + `location_id`, damit die Menge als absoluter Wert aktualisiert wird (statt unbeabsichtigt `+1` über den Add-Endpoint).
- Fix (API/Lager-Tab): Nur wenn kein Bestandseintrag auflösbar ist, wird weiterhin ein neuer Eintrag erstellt.
- Test: API- und Unit-Tests für die neue Stock-ID-Auflösung ergänzt.
- Pflege: Add-on-Version auf `7.1.88` erhöht.

## 7.1.87

- Fix (API/Lager-Tab): Wenn ein Produkt über die Produkt-ID gefunden wird, aber kein nutzbarer `stock_id` vorhanden ist, wird beim Speichern nun automatisch ein Bestandseintrag über Grocy erstellt statt mit „Ungültiger Bestandseintrag" abzubrechen.
- Fix (API/Lager-Tab): Für Produkte ohne bestehenden Bestandseintrag wird Menge `0` beim Speichern mit klarer 400-Fehlermeldung abgewiesen.
- Test: API- und Unit-Tests für den neuen Fallback-Pfad ergänzt.
- Pflege: Add-on-Version auf `7.1.87` erhöht.

## 7.1.86

- Fix (UI/Lager-Tab): Mengenänderungen im Produkt-Popup akzeptieren wieder Kommawerte (z. B. `1,5`) und werden korrekt gespeichert.
- Pflege: Add-on-Version auf `7.1.86` erhöht.

## 7.1.85

- Fix (UI/Lager-Tab): Swipe-Aktionen bei Produkten korrigiert – links wird jetzt wie angezeigt „Verbrauchen" ausgelöst, rechts „Bearbeiten".
- Pflege: Add-on-Version auf `7.1.85` erhöht.

## 7.1.84

- UI (Lager-Tab): Das konfigurierbare Dashboard-Polling-Intervall steuert jetzt auch das Auto-Refresh im Lager-Tab (nur aktiver Tab, pausiert bei inaktivem Browser-Tab).
- UX (Lager-Tab): Hintergrund-Refresh aktualisiert die Lagerliste ohne störende Lade-/Fehlerstatusmeldungen.
- Pflege: Add-on-Version auf `7.1.84` erhöht.

## 7.1.83

- Fix (Einkaufsliste/MHD): Beim Laden der Einkaufsliste wird ein MHD jetzt nur noch aus der Einkaufslisten-Notiz (`[grocy_ai_mhd:...]`) übernommen. Leere MHDs werden nicht mehr automatisch mit Lager-/Grocy-Werten überschrieben.
- Verbesserung (MHD-Fallback): Wenn beim "Einkaufen" weder ein explizites MHD noch `default_best_before_days` (aus KI oder Produktstandard) vorhanden ist, wird als Fallback automatisch `heute + 4 Tage` gesetzt.
- Test: Unit-Tests für den neuen Einkaufslisten-MHD-Import und den globalen `+4 Tage`-Fallback ergänzt.
- Fix (Lager-Tab): Das Speichern einer Bestandsmenge von `0` bleibt nun erhalten und wird nicht mehr als leerer Wert zurückgegeben.
- Test: Unit-Test ergänzt, der sicherstellt, dass `0` als Bestandsmenge als String `"0"` im Storage-Listing erhalten bleibt.
- UI/Config: Dashboard-Polling-Intervall für die Einkaufsliste als konfigurierbare Option (`dashboard_polling_interval_seconds`) ergänzt und im Frontend an die Auto-Refresh-Logik angebunden.
- Home-Assistant-Integration: Options-Flow um `dashboard_polling_interval_seconds` (1-60 Sekunden) erweitert.
- Pflege: Add-on-Version auf `7.1.83` erhöht.

## 7.1.82

- Verbesserung (KI/MHD): Die KI kann jetzt beim Anlegen neuer Produkte eine geschätzte Standard-Haltbarkeit (`default_best_before_days`) liefern.
- Verbesserung (Einkaufsliste/MHD): MHD-Auflösung zentralisiert; wenn beim Hinzufügen oder beim "Einkaufen" kein MHD gesetzt ist, wird ein Datum aus `default_best_before_days` berechnet (aus KI-Wert oder Grocy-Produktstandard).
- Pflege: Doppelte MHD-Normalisierungslogik entfernt und in eine gemeinsame Service-Methode zusammengeführt.
- Test: Unit-Tests für die neue MHD-Auflösung und KI-Mapping ergänzt.
- UI (Benachrichtigungen/Geräteverwaltung): Karte im Notify-Tab wieder auf volle Breite gesetzt und Geräteansicht als 2-Spalten-Layout dargestellt (mobil weiterhin 1 Spalte).
- Verbesserung (Benachrichtigungen/Geräte): Geräte nach Namens-Gemeinsamkeiten gruppiert (z. B. `notify.mobile_app_pixel_watch_*` → Kategorie `Pixel Watch`) mit robustem Fallback auf normalisierte Namensbestandteile bzw. `Sonstige Geräte`.
- Pflege: Add-on-Version auf `7.1.82` erhöht.

## 7.1.81

- Fix (UI/Einkaufsliste): Swipe-Aktionen im Produkt-Tab korrigiert – die auslösenden Aktionen sind nicht mehr vertauscht (links löscht, rechts markiert als gekauft), passend zur dargestellten Aktionsfläche.
- Pflege: Add-on-Version auf `7.1.81` erhöht.

## 7.1.80

- UI (Lager-Tab): Dynamisches Laden beim Tippen im Filterfeld ergänzt (debounced Requests wie in der Such-Tab-Logik), damit große Bestände serverseitig gefiltert geladen werden.
- API/Service (Lager): `GET /api/dashboard/stock-products` unterstützt nun den Query-Parameter `q` und gibt gefilterte Ergebnisse über Name/Lagerort zurück.
- Test: API- und Unit-Tests für den neuen Suchfilter im Lager-Endpoint und in der Grocy-Client-Filterlogik ergänzt.
- Verbesserung (Benachrichtigungen/Mobile Styling): Mobile Testbenachrichtigungen enthalten jetzt zusätzliche Styling-Metadaten wie `icon`, `notification_icon`, `group` und `color`, um auf mobilen Geräten konsistenter dargestellt zu werden.
- Verbesserung (Benachrichtigungen/iOS): iOS-Payload ergänzt um `push.interruption-level`, damit Hinweise sichtbar, aber nicht überaggressiv zugestellt werden.
- Verbesserung (Benachrichtigungen/Android): Android-Payload ergänzt um `importance` und `sticky`, zusätzlich zu bestehenden `priority`-/`channel`-Feldern.
- Test: API-Tests erweitert, um die neuen plattformspezifischen Payload-Felder für mobile Testsendungen abzusichern.
- Pflege: Add-on-Version auf `7.1.80` erhöht.

## 7.1.79

- UI (Lager-Tab): Checkbox zum Laden aller Grocy-Produkte rechts neben das Filterfeld verschoben.
- UI (Lager-Tab): Beschriftung von „Alle in Grocy verfügbaren Produkte laden“ auf „Alle Produkte anzeigen" gekürzt.
- UI (Lager-Tab/Mobil): Filterfeld und Checkbox umbrechen in der mobilen Ansicht jetzt in zwei Zeilen für bessere Lesbarkeit.
- UI (Einkaufsliste): Die Liste im Dashboard aktualisiert sich jetzt automatisch im Hintergrund (Polling alle 5 Sekunden), damit Änderungen von anderen Nutzern zeitnah sichtbar werden.
- UX (Einkaufsliste): Auto-Refresh läuft nur im aktiven Einkaufs-Tab und pausiert bei inaktiver Browser-Ansicht, um unnötige Requests zu vermeiden.
- Performance (Einkaufsliste): Re-Render erfolgt nur bei tatsächlichen Datenänderungen über eine Signaturprüfung der Listeneinträge.
- Pflege: Add-on-Version auf `7.1.79` erhöht.

## 7.1.78

- UI (Benachrichtigungen): Geräte- und Verlaufskarten im Notify-Tab modernisiert (Badge-Status, klarere Hierarchie, bessere Lesbarkeit).
- Verbesserung (Benachrichtigungen/Plattform): Automatische Plattform-Erkennung (Android/iOS) für mobile Targets ergänzt und im Dashboard visuell hervorgehoben.
- Fix (Benachrichtigungen/Testversand): Mobile Testsendungen verwenden jetzt plattformspezifische Payload-Parameter (Android: `data.clickAction`, `priority`, `ttl`; iOS: `data.url`, `push.sound`, `thread-id`).
- Test: API-Tests ergänzt, die iOS- und Android-Payloads für den Device-Test absichern.
- Pflege: Add-on-Version auf `7.1.78` erhöht.

## 7.1.77

- Fix (Benachrichtigungen/Testversand): Die Endpunkte `POST /api/dashboard/notifications/tests/device` und `POST /api/dashboard/notifications/tests/all` senden mobile Testbenachrichtigungen jetzt tatsächlich an Home Assistant (`notify.mobile_app_*`) statt nur einen Verlaufseintrag zu speichern.
- Fix (Benachrichtigungen/Fehlerhandling): Fehlgeschlagene mobile Testsendungen liefern nun nutzerfreundliche 502-Fehlermeldungen und werden im Verlauf als fehlgeschlagen markiert.
- Test: API-Tests ergänzt, die den echten Service-Call für mobile Tests sowie den Fehlerpfad bei fehlendem Notify-Service absichern.
- Pflege: Add-on-Version auf `7.1.77` erhöht.

## 7.1.76

- UI (Lager-Tab): Produktkarten im Lager verwenden jetzt denselben HTML-Aufbau wie Produkte im Such-Tab (gemeinsame Card-/Content-Struktur für Bild, Meta-Bereich und Badge-Spalte).
- UI (Lager-Tab): Lagerprodukte nutzen dieselben Stilklassen wie die Suchprodukte, damit Abstände, Bildgröße und Badge-Ausrichtung visuell konsistent sind.
- Fix (Benachrichtigungen/Geräteerkennung): Notify-Devices werden im Dashboard jetzt primär über die Home-Assistant-Service-API (`/api/services`) erkannt statt ausschließlich über `options.json`-Pattern-Matches.
- Fix (Benachrichtigungen/Geräteerkennung): Fallback auf die bestehende `options.json`-Erkennung bleibt erhalten, falls die Service-API temporär nicht erreichbar ist.
- Test: API-Test ergänzt, der die Erkennung von `notify.mobile_app_*`-Services über den Home-Assistant-Endpoint absichert.
- Pflege: Add-on-Version auf `7.1.76` erhöht.

## 7.1.74

- Fix (Benachrichtigungen/Fehlertexte): Technische Mehrfachfehler aus Supervisor-Header- und Endpoint-Retries werden nicht mehr 1:1 als UI-Statusmeldung ausgegeben. Stattdessen liefert die API jetzt eine kurze, verständliche Fehlermeldung (z. B. Autorisierungsfehler 401/403).
- Verbesserung (Logging): Die vollständige technische Fehlerkette bleibt weiterhin im Add-on-Log erhalten, damit die Ursachenanalyse möglich bleibt.
- Verbesserung (Benachrichtigungsverlauf): Der History-Eintrag für fehlgeschlagene persistente Tests enthält nun ebenfalls die nutzerfreundliche Fehlermeldung statt der langen technischen Retry-Kette.
- Test: API-Test für den 401-Pfad auf die neue nutzerfreundliche Fehlermeldung erweitert.
- Pflege: Add-on-Version auf `7.1.74` erhöht.

## 7.1.73

- UI (Lager-Tab): Attributdarstellung der Lagerprodukte an das Such-Layout angepasst; `Lager` bleibt als Zeile unter dem Produktnamen.
- UI (Lager-Tab): `Menge` und `MHD` werden rechts als Badge-Spalte dargestellt, analog zur Produktsuche.
- UI (Lager/Swipe): Swipe-Aktionsflächen im Lager zeigen Bearbeiten/Verbrauchen jetzt ebenfalls als Badge-Chips wie im Such-Tab.
- Fix (Add-on/Home Assistant OS): `config.json` aktiviert jetzt `homeassistant_api` und `hassio_api`, damit Supervisor-Token/HA-API im Add-on zuverlässig verfügbar sind und Service-Calls für persistente Benachrichtigungen nicht mehr an fehlenden Berechtigungen scheitern.
- Verbesserung (Logging): Bei fehlgeschlagenem Versand persistenter Testbenachrichtigungen wird die genaue Fehlerursache jetzt zusätzlich ins Add-on-Log geschrieben.
- Test: Unit-Test ergänzt, der die API-Flags in `config.json` absichert.
- Pflege: Add-on-Version auf `7.1.73` erhöht.

## 7.1.72

- Fix (Benachrichtigungen/Dashboard): Home-Assistant-Serviceaufrufe probieren jetzt zusätzliche Auth-Header-Kombinationen (`Authorization`, `X-Supervisor-Token`, `X-Hassio-Key`), damit Supervisor-/Ingress-Varianten zuverlässiger autorisiert werden.
- Fix (Benachrichtigungen/Dashboard): Serviceaufrufe testen neben `/core/api/services/...` auch `/api/services/...`, um Installationen mit abweichendem Supervisor-Proxy robuster zu unterstützen.
- Test: API-Test ergänzt, der den Erfolgsfall über `X-Hassio-Key` absichert.
- Pflege: Add-on-Version auf `7.1.72` erhöht.

## 7.1.71

- Fix (Benachrichtigungen/Dashboard): Bei Fehlern von `persistent_notification.create` wird jetzt immer zusätzlich der Fallback `notify.persistent_notification` versucht, statt nur bei 404/405. Dadurch schlagen Systeme mit 400-Fehlermeldungen (z. B. "service not found") nicht mehr mit 502 fehl.
- Fix (Benachrichtigungen/Dashboard): Fallback-Aufruf sendet nur `title` und `message`, damit keine inkompatiblen Felder wie `notification_id` an den Notify-Service gehen.
- Test: API-Test ergänzt, der den 400-Fehlerpfad von `persistent_notification.create` mit erfolgreichem Notify-Fallback absichert.
- Pflege: Add-on-Version auf `7.1.71` erhöht.

## 7.1.70

- Fix (Benachrichtigungen/Dashboard): Persistente Testbenachrichtigungen erzeugen jetzt eine Home-Assistant-kompatible `notification_id` ohne Sonderzeichen, damit Service-Calls nicht mehr an ungültigen IDs scheitern.
- Fix (Benachrichtigungen/Dashboard): Bei 400/422-Validierungsfehlern wird `persistent_notification.create` automatisch ohne `notification_id` erneut versucht, um 502-Fehler bei strengeren HA-Versionen zu vermeiden.
- Test: API-Tests für ID-Sanitizing und den Retry-Pfad ohne `notification_id` ergänzt.
- Pflege: Add-on-Version auf `7.1.70` erhöht.

## 7.1.69

- UI (Benachrichtigungen): `padding` bei `.notification-list li` entfernt, damit die Listen-/Swipe-Darstellung den gewünschten Abständen entspricht.
- Fix (Benachrichtigungen/Dashboard): Persistente Testbenachrichtigungen akzeptieren nun sowohl `SUPERVISOR_TOKEN` als auch `HASSIO_TOKEN` und unterstützen zusätzlich den Header `X-Supervisor-Token`, damit Service-Calls im Add-on-Umfeld zuverlässiger autorisiert werden.
- Fix (Benachrichtigungen/Dashboard): Fehlerantworten des Home-Assistant-Service werden im API-Fehlertext mitgeführt, um 502-Ursachen im Dashboard besser nachvollziehen zu können.
- Test: API-Tests für Fallback auf `HASSIO_TOKEN` und für den 401-Fehlerpfad ergänzt.
- Pflege: Add-on-Version auf `7.1.69` erhöht.

## 7.1.68

- UI (Benachrichtigungen/Swipe): Swipe-Aktionsflächen der Regelkarten im Notify-Tab vergrößert, damit Chip-Inhalt und Buttonfläche optisch konsistent wirken.
- Fix (Benachrichtigungen/Dashboard): Der Endpoint `POST /api/dashboard/notifications/tests/persistent` sendet die Testnachricht jetzt wirklich an Home Assistant (`persistent_notification.create`) statt nur einen Verlaufseintrag zu speichern.
- Fix (Benachrichtigungen/Dashboard): Fallback auf `notify.persistent_notification` ergänzt, falls `persistent_notification.create` im Zielsystem nicht verfügbar ist.
- Test: API-Tests für erfolgreichen Service-Call und Fehlerfall ohne `SUPERVISOR_TOKEN` ergänzt.
- Pflege: Add-on-Version auf `7.1.68` erhöht.

## 7.1.67

- UI (Lager-Tab): Checkbox ergänzt, um optional alle in Grocy verfügbaren Produkte zusätzlich zum aktuellen Lagerbestand zu laden.
- API/Service (Lager): `GET /api/dashboard/stock-products` unterstützt den Parameter `include_all_products`, der auch nicht auf Lager befindliche Produkte zurückliefert.
- UX (Lagerliste): Nicht auf Lager befindliche Produkte werden angezeigt, aber Lageraktionen (Bearbeiten/Verbrauchen) bleiben für diese Einträge deaktiviert.
- Pflege: Add-on-Version auf `7.1.67` erhöht.

## 7.1.66

- UI (Swipe-Actions): Lagerprodukte im Tab „Lager“ nutzen jetzt dieselbe Swipe-Interaktion wie die Einkaufssuche (links: Bearbeiten, rechts: Verbrauchen) statt fester Aktionsbuttons.
- UI (Notify-Regeln): Regeln im Benachrichtigungs-Tab wurden auf Swipe-Buttons umgestellt (links: Bearbeiten, rechts: Löschen) für ein konsistentes Bedienmuster.
- Frontend-Refactoring: Wiederverwendbare Swipe-Logik (`bindSwipeInteractions`) und gemeinsame Swipe-CSS-Klassen eingeführt, damit Shopping-, Lager- und Regel-Listen gleiches Verhalten teilen.
- UI (Button-Styles): Aktionsbuttons in Lager- und Benachrichtigungsansicht auf die gleichen Basis-Buttonvarianten wie auf Such- und Rezeptseite vereinheitlicht (Primary/Ghost/Success/Danger).
- UI (Benachrichtigungen): Dynamisch gerenderte Regelaktionen nutzen jetzt konsistente Klassen (`ghost-button` für Bearbeiten, `danger-button` für Löschen).
- UI (Dashboard/Tabs): Die Statusmeldungen der Tabs werden nun im Header anstelle der Überschrift „Smart Pantry Dashboard" angezeigt.
- UX (Tab-spezifisch): Beim Tab-Wechsel spiegelt der Header immer die jeweils aktive Statusmeldung (Einkauf, Rezepte, Lager, Benachrichtigungen).
- Pflege: Add-on-Version auf `7.1.66` erhöht.

## 7.1.65

- Architektur/Codepflege: Doppelte Implementierung von `_normalize_barcode_for_lookup` in `api/routes.py` entfernt, um widersprüchliche Wartungspfade zu vermeiden.
- Testqualität: Doppelten API-Testfall für `search-variants` bereinigt und Erwartungswerte an das tatsächliche Verhalten ohne `include_ai=true` angepasst (nur Input+Grocy statt KI-Vorschläge).
- Dokumentation: `README.md` inhaltlich aktualisiert (aktueller Versionsstand, klare API-/Architektur-Hinweise, konsolidierte Entwicklungsbefehle).
- Pflege: Add-on-Version auf `7.1.65` erhöht.

## 7.1.64

- Fix (Benachrichtigungen): Fallback für `persistent_notification` ergänzt. Wenn der Core-Service `persistent_notification.create` nicht verfügbar ist, wird automatisch `notify.persistent_notification` verwendet.
- Test: Unit-Tests für Dispatcher-Pfad (Core-Service) und Fallback-Pfad (`notify.persistent_notification`) ergänzt.
- UI (Lager/Popup „Bestand ändern“): Zu ändernde Attribute im Bearbeiten-Dialog als eigene, klar getrennte Zeilen dargestellt.
- Pflege: Add-on-Version auf `7.1.64` erhöht.

## 7.1.63

- UI (Lager-Tab): Aktions-Buttons der Produktkarten in der Desktop-Ansicht explizit an den rechten Rand der Karte ausgerichtet.
- Add-on (Konfiguration): Übersetzungen für Optionsfelder ergänzt (`translations/de.yaml`, `translations/en.yaml`) mit natürlichen, verständlichen Feldnamen.
- UX (Konfiguration): Sinnvolle Präfixe (`Allgemein`, `Ollama`, `Scanner`, `Benachrichtigungen`, `Bilder`, `Wartung`) eingeführt, um die Formularreihenfolge klarer zu strukturieren.
- Pflege: Add-on-Version auf `7.1.63` erhöht.

## 7.1.62

- Add-on (Konfiguration): Reihenfolge der `options`/`schema` in `config.json` überarbeitet, damit der Schalter `debug_mode` im Home-Assistant-Formular weiter unten angezeigt wird.
- Pflege: Add-on-Version auf `7.1.62` erhöht.

## 7.1.61

- Add-on (Ingress): Externes Port-Mapping (`8000/tcp`) aus `config.json` entfernt, damit der Zugriff standardmäßig ausschließlich über Home-Assistant-Ingress erfolgt.
- Pflege: Add-on-Version auf `7.1.61` erhöht.

## 7.1.60

- Performance (Thumbnails/Mobil): Dashboard-Bildproxy unterstützt nun die Größe `mobile` (64x64), wodurch auf kleinen Viewports kleinere Produktbilder geladen werden.
- Performance (Caching): `GET /api/dashboard/product-picture` liefert jetzt `Cache-Control: public, max-age=86400`, damit Mobilbrowser Thumbnails aggressiver zwischenspeichern.
- UI (Dashboard): Thumbnail-Aufrufe verwenden auf mobilen Viewports automatisch die neue Proxy-Größe `mobile` statt `thumb`.
- Test: API-Test für `size=mobile` und Cache-Header ergänzt.
- Fix (Benachrichtigungen): Rule-Engine erzeugt jetzt auch dann `persistent_notification`-Nachrichten, wenn kein mobiles Notify-Target vorhanden ist.
- Fix (Benachrichtigungen): Regeln mit gemischten Kanälen liefern mobile Push und persistente Benachrichtigung als getrennte Dispatch-Nachrichten aus.
- Test: Unit-Tests für Persistent-Only- und Mixed-Channel-Regeln ergänzt.
- Pflege: Add-on-Version auf `7.1.60` erhöht.

## 7.1.59

- Fix (Scanner/WebView): Kamera-Start nutzt nun eine kompatible `getUserMedia`-Abfrage (inkl. Legacy-Fallback) statt ausschließlich `navigator.mediaDevices.getUserMedia`.
- Fix (Scanner/UX): Fehlermeldungen beim Kamera-Start unterscheiden jetzt klar zwischen fehlender Berechtigung, unsicherem Kontext (HTTPS/WebView) und fehlender Kamera.

## 7.1.58

- Verbessert: Die Barcode-Erkennung rotiert den Scanner-Canvas bei Hochkant-Bildquellen nun automatisch um 90°, wenn die Bilddrehung auf 0° steht. Dadurch werden Barcodes in hochkant aufgenommenen Bildern zuverlässiger erkannt.

## 7.1.57

- Scanner (Ausrichtung): Neue Option „Bilddrehung" (0°/90°/180°/270°) im Scanner-Modal, damit Kamera-Feed bei horizontal/vertikalem Handling passend ausgerichtet werden kann.
- Scanner (Erkennung): Die Barcode-Analyse übernimmt die gewählte Drehung ebenfalls auf dem Analyse-Canvas (ROI), damit `BarcodeDetector` den Code in der gewählten Orientierung robuster lesen kann.
- Pflege: Add-on-Version auf `7.1.57` erhöht.

## 7.1.56

- Scanner (Kameraauswahl): Verfügbare Kameras werden gelistet und sind im Scanner testweise auswählbar; Standard bleibt Rückkamera bevorzugt.
- Scanner (Qualität): Kamera-Streams fordern zuerst höhere Auflösungen (bis 2560x1440) an und fallen stufenweise auf kleinere Profile zurück.
- Scanner (UX/Erkennung): Barcode-Analyse startet erst nach kurzer Scharfstell-Wartezeit; zusätzlich Hinweis „Etwas weiter weg halten“.
- Scanner (Erkennungsrahmen): Fester Rahmen in der Bildmitte eingebaut; Barcode-Detektion analysiert nur noch diesen mittigen Bereich.
- Scanner (Lichtprüfung): Helligkeit wird periodisch geprüft und bei schwachem Licht eine Warnung angezeigt.
- Scanner (Debug): `getCapabilities()`/`getSettings()` werden geloggt und als Debug-Block im Scanner angezeigt (inkl. focusMode/focusDistance/zoom/torch-Unterstützung).
- Pflege: Add-on-Version auf `7.1.56` erhöht.

## 7.1.55

- Fix (Scanner/Fokus): Kamera-Fokus wird während des laufenden Scans zyklisch neu angestoßen (alle 2s) für unterstützte Modi (`continuous`/`single-shot`), damit mobile Kameras nicht in unscharfem Zustand „hängen bleiben“.
- Stabilität (Scanner/Fokus): Beim Scanner-Start wird der bevorzugte Fokusmodus gespeichert und direkt nach dem Setzen der Constraints einmal aktiv nachgezogen.
- Stabilität (Scanner): Fokus-Refresh-Timer wird beim Stoppen zuverlässig beendet und Fokus-Zustand zurückgesetzt.
- Pflege: Add-on-Version auf `7.1.55` erhöht.

## 7.1.54

- Fix (Scanner/Fokus): Kamera-Fokus priorisiert jetzt `focusMode=continuous` (statt primär `manual`), damit mobile Geräte während des Scan-Vorgangs fortlaufend nachfokussieren und das Bild nicht dauerhaft unscharf bleibt.
- Stabilität (Scanner/Barcode): Barcode-Lookup wird erst ausgelöst, wenn derselbe normalisierte Code in mehreren aufeinanderfolgenden Frames erkannt wurde (Debounce/Stabilitätsprüfung), wodurch Fehllesungen und wechselnde Codes deutlich reduziert werden.
- Stabilität (Scanner): Während ein Barcode-Lookup läuft, werden weitere automatische Lookups kurzzeitig blockiert, um konkurrierende Requests zu vermeiden.
- Pflege: Add-on-Version auf `7.1.54` erhöht.

## 7.1.53

- Scanner (Browser-Kompatibilität): Kamera-Start nutzt jetzt abgestufte `getUserMedia`-Profile (von bevorzugter Rückkamera bis zu generischem Fallback), damit Scanner in mehr Browsern/Endgeräten startet statt direkt fehlzuschlagen.
- Scanner (Mobile Browser): Video-Element wird beim Start explizit mit `playsinline`, `autoplay` und `muted` initialisiert, um iOS-/WebKit-Verhalten robuster zu unterstützen.
- Pflege: Add-on-Version auf `7.1.53` erhöht.

## 7.1.52

- UI (Lager-Tab/Produkt-Popup): Im Bearbeiten-Popup werden aktuelle `Menge` und `MHD` zusätzlich als zwei separate Info-Zeilen angezeigt.
- Fix (Scanner/LLaVA): LLaVA-Requests werden jetzt mit konfigurierbarem Timeout (`scanner_llava_timeout_seconds`) verarbeitet und frontendseitig nach Ablauf sauber abgebrochen, statt unbegrenzt zu warten.
- Stabilität (Scanner/LLaVA): Server blockiert parallele LLaVA-Anfragen während ein Lauf aktiv ist (`429` bei gleichzeitigem Request), um Mehrfachabfragen zu vermeiden.
- Stabilität (Scanner/LLaVA): Auto-Fallback im Frontend respektiert zusätzlich ein Cooldown, damit bei ausbleibendem Barcode nicht dauerhaft neue KI-Calls gestartet werden.
- Fix (Barcode/OpenFoodFacts): Für 12-stellige UPC-Codes wird zusätzlich die 13-stellige Variante mit führender `0` geprüft (und umgekehrt), um Treffer bei OpenFoodFacts/Grocy zu erhöhen.
- Test: Dashboard-API-Tests für Barcode-Varianten und LLaVA-Timeout-Weitergabe ergänzt.
- UI (Lager/Popup „Bestand ändern“): Bearbeiten-Dialog um Nährwertfelder erweitert (Kalorien, Kohlenhydrate, Fett, Eiweiß, Zucker), damit diese direkt im Lager-Tab angepasst werden können.
- API/Lager: `PUT /api/dashboard/stock-products/{stock_id}` akzeptiert jetzt optional Nährwerte und aktualisiert zusätzlich die Produkt-Nährwerte in Grocy.
- Service: `GrocyClient.get_stock_products(...)` liefert Nährwerte für den Lager-Tab mit; `GrocyClient.update_product_nutrition(...)` ergänzt.
- Test: API- und Unit-Tests für Nährwertanzeige/-Update ergänzt.
- Pflege: Add-on-Version auf `7.1.52` erhöht.

## 7.1.51

- Fix (Barcode-Scanner/OpenFoodFacts): Sehr lange KI-Barcode-Strings (z. B. GS1 mit führendem `01` + Zusatzdaten) werden jetzt vor dem Lookup auf gültige GTIN/EAN-Längen normalisiert, damit OpenFoodFacts die korrekte Produktnummer erhält.
- Scanner (Kamera): Fokus-Optimierung erweitert – bevorzugt `focusMode=manual` (Fallback auf `single-shot`/`continuous`), setzt wenn verfügbar den Fokuspunkt in die Bildmitte und nutzt bei unterstützten Geräten kurze Fokusdistanz.
- Test: API-Tests zur Barcode-Normalisierung für lange Scannerwerte ergänzt.
- Pflege: Add-on-Version auf `7.1.51` erhöht.

## 7.1.50

- UI (Lager-Tab): Aktions-Buttons der Produktkarten in der Desktop-Ansicht explizit an den rechten Rand der Karte ausgerichtet.
- Pflege: Add-on-Version auf `7.1.50` erhöht.

## 7.1.49

- UI (Lager-Tab): Produktkarten im Lager auf ein festes 3-Spalten-Grid umgestellt (`Bild | Name/Beschreibung | Buttons`).
- UI (Lager-Tab): Name und Beschreibung werden jetzt explizit untereinander dargestellt.
- UI (Lager-Tab): Aktions-Buttons (`Bearbeiten`, `Verbrauchen`) pro Produkt werden vertikal untereinander angezeigt.
- Fix (Rezepte/"Bald ablaufend"): Filter verarbeitet `product_id` jetzt robust auch als String, sodass ablaufende Produkte nicht fälschlich ausgeschlossen werden.
- Fix (Rezepte/"Bald ablaufend"): MHD-Werte mit Zeitanteil (z. B. `YYYY-MM-DD HH:MM:SS` oder ISO mit `T`) werden korrekt als Datum erkannt.
- Test: API-Test ergänzt, der String-IDs und Datumswerte mit Zeitanteil für den "bald ablaufend"-Pfad absichert.
- Pflege: Add-on-Version auf `7.1.49` erhöht.

## 7.1.48

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

## 7.1.47

- UI (Lager-Tab): Produktbilder in der Lagerliste vereinheitlicht und über dieselbe Bild-Logik wie in den anderen Tabs gerendert (inkl. Proxy/Fallback-Verhalten).
- UI (Popup „Bestand ändern"): Neuer Button „Produktbild löschen" ergänzt, um das Bild eines Produkts direkt im Bearbeiten-Dialog zu entfernen.
- API: Neuer Endpoint `DELETE /api/dashboard/products/{product_id}/picture` zum Entfernen des Produktbilds.
- Service: `GrocyClient.clear_product_picture(...)` ergänzt und per Tests abgesichert.
- Pflege: Add-on-Version auf `7.1.47` erhöht.

## 7.1.46

- UI (Notify-Tab): Regelkarten im iOS-inspirierten Stil überarbeitet (abgerundete Card-Flächen, sanfte Verlaufshintergründe, kompakter Header mit Icon und strukturierte Meta-Badges).
- UI (Notify-Tab): Badges um visuelle Marker ergänzt (Kanäle/Priorität/Cooldown), damit Regeln schneller erfassbar sind.
- UI (Notify-Tab): Aktions-Buttons weiterhin pillenförmig, aber mit dezentem Lift/Hover für einen app-artigen Touch optimiert.
- Pflege: Add-on-Version auf `7.1.46` erhöht.

## 7.1.45

- UI (Einkaufsliste): Im Produkt-Popup kann die Einkaufsmenge jetzt direkt bearbeitet und gespeichert werden.
- API: Neuer Endpoint `PUT /api/dashboard/shopping-list/item/{shopping_list_id}/amount` zum Setzen einer konkreten Menge.
- Test: API-Test ergänzt, der das Aktualisieren einer konkreten Einkaufslistenmenge absichert.
- Pflege: Add-on-Version auf `7.1.45` erhöht.

## 7.1.44

- UI (Lager/Popup „Bestand ändern“): Popup um relevante Produktinfos erweitert (Produktname, Produkt-ID, Bestands-ID, Lagerort) und Produktbild direkt im Dialog ergänzt.
- UI (Lager/Popup „Bestand ändern“): Lösch-Button „Produkt löschen“ im Bearbeiten-Dialog hinzugefügt, inkl. Bestätigungsdialog und aktualisierter Statusmeldung.
- API: Neuer Endpoint `DELETE /api/dashboard/stock-products/{stock_id}` zum Löschen eines Bestandseintrags (inkl. `product_id`-Fallback auf den passenden `stock_id`).
- Service: `GrocyClient.delete_stock_entry(...)` ergänzt, um Bestände über Grocy `objects/stock/{id}` zu löschen.
- Test: Unit- und API-Tests für das Löschen von Bestandseinträgen ergänzt.
- UI (Einkaufsliste): Unterhalb der Notiz wird jetzt ein zusätzlicher Bestands-Tag pro Produkt angezeigt (`Bestand: ...`).
- UI (Einkaufsliste): Der Bestandswert wird aus `in_stock` übernommen und für Dezimalwerte lokalisiert dargestellt (de-DE).
- UI (Notify-Tab): Regel-Objekte visuell näher an die Produktkarten der Einkaufsliste gebracht (größerer Kartenradius, spacing und badge-ähnliche Meta-Anordnung).
- UI (Notify-Tab): Aktions-Buttons pro Regel auf pillenförmigen Badge-Look umgestellt und farblich differenziert (Bearbeiten/Rot für Löschen), wie gewünscht weiterhin mit Farbe.
- UI (Einkaufsliste): MHD-Badge zeigt bei vorhandenem Datum jetzt nur noch das Datum ohne Präfix `MHD:`; ohne Datum bleibt der CTA `MHD wählen` unverändert.
- Pflege: Add-on-Version auf `7.1.44` erhöht.

## 7.1.43

- UI (Dashboard): Alle Box-Shadows im Dashboard-Theme entfernt, inklusive Cards, Buttons, Tabbar, Header, Inputs und Modal-Elementen, für einen flacheren, einheitlichen Stil.
- UI (Interaktionen): Übergänge bereinigt, damit keine Shadow-Animationen mehr referenziert werden.
- Pflege: Add-on-Version auf `7.1.43` erhöht.

## 7.1.42

- Fix (Produktsuche): Produktanlage in Grocy entfernt bei aufeinanderfolgenden `400 Bad Request`-Antworten mit Schemafehlern ("has no column named ...") die jeweils bemängelten Felder schrittweise aus dem Retry-Payload.
- Stabilität: Retry-Logik bricht weiterhin sauber ab, wenn kein unbekanntes Feld aus der Fehlermeldung extrahiert werden kann.
- Test: Unit-Test ergänzt, der mehrere `unknown column`-Fehler (`carbohydrates`, danach `qu_factor_purchase_to_stock`) und den erfolgreichen dritten Request absichert.
- UI (Dashboard): Einheitliches visuelles Theme für alle Dashboard-Bereiche eingeführt (konsistente Farbpalette, Karten-/Header-Stil und harmonisierte Light-/Dark-Variablen).
- UI (Navigation): Bottom-Tabbar und aktiver Tab mit neuem Akzent-Gradienten, Glassmorphism-Hintergrund und angepasstem Shadow-Design vereinheitlicht.
- UI (Interaktionen): Buttons inkl. Hover-/Focus-/Active-States global vereinheitlicht; Primary-, Danger-, Success- und Ghost-Varianten optisch konsistent gemacht.
- UI (Header): Topbar als konsistenter Card-Container gestaltet und Theme-Switch visuell an das neue Farbsystem angepasst.
- Fix (CSS): Verweis auf nicht definierte Variable `--accent` im Rezept-Methoden-Switch auf `--accent-primary` korrigiert.
- Pflege: Add-on-Version auf `7.1.42` erhöht.

## 7.1.41

- Fix (Produktsuche): Produktanlage in Grocy erhält bei `400 Bad Request` jetzt automatisch einen Retry mit bereinigtem Payload (nur von Grocy akzeptierte Felder + validierte `location_id`/`quantity_unit` IDs).
- Stabilität: Bei ungültigen KI-IDs werden fallback-fähige Werte aus den tatsächlich in Grocy verfügbaren Lagerorten und Mengeneinheiten verwendet.
- Logging: Bei einem 400-Fehler der Produktanlage wird der Retry inkl. Response-Body als Warnung protokolliert.
- Test: Unit-Tests für Retry-Logik und Payload-Bereinigung in `GrocyClient.create_product` ergänzt.
- Fix (Lager-Tab): Der Button „✏️ Bearbeiten“ öffnet das Popup „Bestand ändern“ jetzt wieder zuverlässig auch dann, wenn ein Eintrag nur über `product_id` (Fallback-ID) adressierbar ist.
- Fix (Lager-Tab): Speichern im Bearbeiten-Popup nutzt nun dieselbe aufgelöste Ziel-ID wie der Button-Aufruf, wodurch Updates konsistent am korrekten Eintrag landen.
- Pflege: Add-on-Version auf `7.1.41` erhöht.

## 7.1.39

- Fix (Produktauswahl): Auswahl von `Neu anlegen` in der Variantenliste legt das Produkt jetzt direkt an, statt erneut in die Varianten-Auswahl zurückzuspringen.
- API: `POST /api/dashboard/search` akzeptiert `force_create`, um die Varianten-Fallback-Auswahl gezielt zu überspringen.
- UI (Suche): Beim Klick auf `source: input` wird die Suche mit `force_create` ausgelöst und die Statusmeldung auf direkte Anlage angepasst.
- Test: API-Test ergänzt, der `force_create` mit Mengenpräfix (`2 oliven`) und direkte Anlage (`created_and_added`) absichert.
- Fix (Lager-Tab): Bearbeiten/Verbrauchen-Endpunkte akzeptieren nun zusätzlich `product_id` als Fallback-ID und lösen diese serverseitig zuverlässig auf den echten Bestandseintrag (`stock_id`) auf.
- Fix (Lager-Tab): Verbrauchen nutzt beim Fallback weiterhin korrekt den passenden `stock_entry_id`, sodass in Grocy der richtige Bestandsposten reduziert wird.
- Test: API-Tests für Produkt-ID-Fallback beim Verbrauchen und Bearbeiten von Lagerprodukten ergänzt.
- Pflege: Add-on-Version auf `7.1.39` erhöht.

## 7.1.38

- UI (Navigation): Untere Navigationsleiste (Tab-Bar) wieder verkleinert (geringere Gesamtbreite, engeres Innenpadding und kleinerer Abstand zwischen Tabs).
- UI (Navigation): Tab-Buttons in der Navigationsleiste kompakter gestaltet (kleinere Schrift, reduzierte Mindesthöhe und weniger Innenabstand).
- Fix (Dashboard Lager): Lade- und ID-Normalisierungslogik für Bestandsprodukte zwischen Rezepte-Tab (Produktauswahl) und Lager-Tab vereinheitlicht.
- Fix (Dashboard Lager): Aktionen im Lager-Tab ("Bearbeiten", "Verbrauchen") nutzen jetzt automatisch `stock_id` und fallen bei fehlender Bestand-ID auf `product_id` zurück.
- UX (Dashboard Lager): Statusmeldung zeigt jetzt transparent an, wie viele Einträge per Produkt-ID-Fallback laufen bzw. gar keine nutzbare ID haben.
- Suche (Produktauswahl): Varianten-Laden im Such-Tab erfolgt jetzt zweistufig: zuerst sofort Grocy-Treffer (`include_ai=false`), anschließend KI-Erweiterung per Lazy-Load (`include_ai=true`).
- API: `GET /api/dashboard/search-variants` unterstützt den Query-Parameter `include_ai` zur getrennten Steuerung von Grocy-Soforttreffern und KI-Vorschlägen.
- UX (Produktauswahl): Wenn kein exakter Produktname zur Suche passt, wird an erster Stelle ein Eintrag zum Neu-Anlegen mit dem bereinigten Suchtext (ohne Mengenpräfix) angezeigt.
- UI (Produktauswahl): Neuer Quellenhinweis `Neu anlegen` für den oben genannten Eingabe-Vorschlag.
- Test: API-Tests für Lazy-Load-Verhalten (`include_ai=false`) und Input-Vorschlagsreihenfolge ergänzt/angepasst.
- Pflege: Add-on-Version auf `7.1.38` erhöht.

## 7.1.37

- UI (Lager-Tab): Letzte Button-Anpassung rückgängig gemacht; Aktions-Buttons sind wieder im vorherigen kompakten Stil (`Verbrauchen`, `Ändern`).
- UI (Notify-Tab): Buttons auf den vorherigen Stil der Lager-Tab-Buttons umgestellt (kompakter Button-Look für Regelaktionen, „Neue Regel“ und Test-Aktionen).
- Suche (Produktauswahl): Varianten-Suche im Such-Tab nutzt jetzt KI-gestützte Vorschläge zusätzlich zu Grocy-Teiltreffern.
- UX (Produktauswahl): In der Variantenliste werden jetzt auch KI-Vorschläge als auswählbare Einträge angezeigt, selbst wenn diese Produkte noch nicht in Grocy existieren.
- API: `/api/dashboard/search-variants` verwendet dieselbe Fallback-Logik wie die Produktsuche und liefert dadurch Grocy- und KI-Varianten konsistent.
- Test: API-Tests für KI-Vorschläge in der Varianten-Suche ergänzt und bestehende Varianten-Tests an den Detector angepasst.
- Pflege: Add-on-Version auf `7.1.37` erhöht.

## 7.1.36

- UI (Lager-Tab): Aktions-Buttons pro Lagereintrag visuell überarbeitet und auf einen einheitlichen, pillenförmigen Stil umgestellt.
- UI (Lager-Tab): Reihenfolge und Beschriftung der Aktionen verbessert (`✏️ Bearbeiten`, `✅ Verbrauchen`) für klarere Bedienung.
- UX (Lager-Tab): Button-Zustände für deaktivierte Aktionen konsistenter dargestellt und Mobile-Layout für Button-Zeile verbessert.
- Fix (Dashboard/Lager): Produktbilder im Lager-Tab werden jetzt wie im Einkaufs-Tab über den Dashboard-Bildproxy ausgeliefert (`/api/dashboard/product-picture?...`) statt mit rohem Dateinamenpfad, wodurch 404-Fehler für reine Dateinamen verhindert werden.
- Test: API-Test ergänzt/erweitert, der für `/api/dashboard/stock-products` den Proxy-Bildpfad für `picture_url` absichert.
- UI (Suche/Einkaufsliste): Badge-Breitenbegrenzung gezielt auf Mobile (`max-width: 33.333%`) angewendet; Desktop-Badge-Breite bleibt beim bisherigen festen Layout.
- Pflege: Add-on-Version auf `7.1.36` erhöht.

## 7.1.35

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
- UX (Rezepte): Beschreibungstexte in Rezeptvorschlägen vereinheitlicht und auf maximal zwei Zeilen begrenzt, inklusive Fallback-Text bei fehlender Beschreibung.
- Fix (Produktsuche): Beim Hinzufügen eines bestehenden Produkts über die Produktauswahl wird ein Mengenpräfix im Suchtext (z. B. `2 Apfel`) jetzt ausgewertet und als Einkaufsmenge übernommen.
- Verhalten: Gilt jetzt konsistent für bestehende und neu angelegte Produkte in der Produktsuche.
- Test: API-Test ergänzt, der den Mengenpräfix für `/api/dashboard/add-existing-product` absichert.
- UI (Suche/Einkaufsliste): Produkt-Badges im Such-/Einkaufstab sind jetzt auf maximal ein Drittel der Breite des Produktelements begrenzt, damit die Produktinfos mehr Platz behalten.
- Pflege: Add-on-Version auf `7.1.35` erhöht.

## 7.1.34

- KI (lokale Produktanalyse): Prompt für `analyze_product_name` erweitert, damit neben Kalorien/Kohlenhydraten auch weitere bekannte Nährwerte (`fat`, `protein`, `sugar`) zurückgegeben werden.
- KI (Robustheit): Antwortnormalisierung ergänzt, inkl. Zahlen-Normalisierung, Fallbacks und Alias-Mapping von `carbs` -> `carbohydrates`.
- API-Modell: `ProductData` um zusätzliche Nährwertfelder (`carbohydrates`, `fat`, `protein`, `sugar`) ergänzt.
- Test: Unit-Tests für erweiterte Nährwertausgabe und Alias-Mapping ergänzt.
- Fix (Produktsuche): Fuzzy-Match übernimmt keine zusammengesetzten Präfix-Treffer mehr (z. B. `Oliven` -> `Olivenöl`), wenn nur ein längeres Kompositum ähnlich ist.
- Test: Unit-Test ergänzt, der sicherstellt, dass `Oliven` nicht automatisch als `Olivenöl` übernommen wird.
- Pflege: Add-on-Version auf `7.1.34` erhöht.

## 7.1.33

- Fix (Grocy-Bildupload): Upload berücksichtigt zusätzlich einen Dateinamen-Fallback mit Base64-kodiertem Dateinamen (inkl. Dateiendung), falls Endpunkte den Pfad nur in kodierter Form akzeptieren.
- Fix (Grocy-Bildupload): Reihenfolge bleibt robust: pro URL-Variante werden `PUT` und `POST` mit `api_key` und `curl_compatible` Header-Modus probiert.
- Test: Unit-Test ergänzt, der den erfolgreichen Upload über die Base64-Dateinamen-URL absichert.
- Pflege: Add-on-Version auf `7.1.33` erhöht.

## 7.1.32

- Fix (Grocy-Bildupload): Produktbild-Upload versucht bei `405/404` jetzt wieder pro URL den Methoden-Fallback `PUT` -> `POST` (jeweils mit `api_key` und `curl_compatible` Header-Modus), bevor zur nächsten URL gewechselt wird.
- Logging: Warnungen enthalten neben URL und Header-Modus nun auch die fehlgeschlagene HTTP-Methode (`PUT`/`POST`).
- Test: Unit-Tests für die neue Upload-Reihenfolge über `requests.request(...)` ergänzt/angepasst.
- Pflege: Add-on-Version auf `7.1.32` erhöht.

## 7.1.31

- Fix (Grocy-Bildupload): Upload versucht je URL zuerst mit `GROCY-API-KEY` und bei `404/405` zusätzlich einen zweiten PUT im curl-kompatiblen Header-Modus ohne API-Key (`Accept: */*`, `Content-Type: application/octet-stream`).
- Fix (Grocy-Bildupload): URL-Fallback von `/api/files/...` auf `/files/...` bleibt erhalten und nutzt ebenfalls beide Header-Modi.
- Logging: Fallback-Warnungen enthalten jetzt den verwendeten Header-Modus (`api_key` vs. `curl_compatible`).
- Test: Unit-Tests für Header-Modus-Fallback und URL-Fallback-Reihenfolge ergänzt/angepasst.
- Pflege: Add-on-Version auf `7.1.31` erhöht.

## 7.1.30

- Fix (Grocy-Bildupload): Upload-Request an Grocy-Datei-Endpunkte enthält jetzt zusätzlich `Accept: */*` (entsprechend funktionierendem `curl`-Aufruf).
- Fix (Grocy-Bildupload): Bei `405`/`404` wird pro Upload-URL zuerst `PUT`, dann `POST` probiert, bevor zur nächsten Fallback-URL gewechselt wird.
- Test: Unit-Tests für Header-Setzung sowie Fallback-Reihenfolge (`PUT` -> `POST` -> URL-Fallback) ergänzt.
- Pflege: Add-on-Version auf `7.1.30` erhöht.

## 7.1.29

- Fix (Grocy-Bildupload): HTTP-Fehlerauswertung beim Upload-Fallback korrigiert, damit auch echte `requests.Response`-Objekte mit Status `>=400` (falsey) den Statuscode korrekt liefern.
- Fix (Grocy-Bildupload): Fallback von `/api/files/...` auf `/files/...` greift dadurch zuverlässig bei `405`/`404`.
- Test: Upload-Fallback-Test erweitert, um das falsey-Verhalten von `requests.Response` bei Fehlerstatus abzubilden.
- Pflege: Add-on-Version auf `7.1.29` erhöht.

## 7.1.28

- Fix (Grocy-Bildupload): Produktbild-Upload versucht bei `404/405` auf `/api/files/...` jetzt automatisch einen Fallback auf `/files/...` ohne `/api`-Präfix.
- Logging: Beim Fallback wird eine Warnung mit der fehlgeschlagenen Upload-URL protokolliert.
- Test: Unit-Test ergänzt, der den 405-Fall und den erfolgreichen Fallback-Upload absichert.
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
