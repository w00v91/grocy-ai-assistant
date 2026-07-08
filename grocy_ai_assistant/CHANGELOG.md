## 2026-07-08 (Version 8.0.66)

- Fix (Home-Assistant-Integration/Panel/Shopping): Doppelte laufende Produktsuchen werden im Such-Controller jetzt als Fehlerstatus angezeigt, ohne die Einkaufsliste neu zu laden.
- Added (Tests/Frontend): Frontend-Test für `search_in_flight`-Antworten der Produktsuche ergänzt.
- Changed (Versioning): Versionsstand der Integration auf `8.0.66` erhöht.

## 2026-07-08 (Version 8.0.65)

- Fix (Home-Assistant-Integration/Panel/Desktop): Die Bottom-Bar ist auf Desktop jetzt im Dashboard-Fluss verankert statt viewport-fixed, damit sie keine Home-Assistant-Elemente oder Inhalte überdeckt.
- Fix (Home-Assistant-Integration/Panel/Mobile): Swipe-Aktionsflächen der Einkaufslisten-Einträge sind im Ruhezustand vollständig unsichtbar, damit keine grünen oder roten Kanten mehr an Kartenenden durchscheinen.
- Changed (Home-Assistant-Integration/Sensoren): Die Sensoranzeigen für Einkaufsliste, Lagerprodukte und bald ablaufende Produkte verwenden jetzt Produktnamen mit dem Suffix `Produkte`.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.65` erhöht.

## 2026-07-04 (Version 8.0.64)

- Fix (Home-Assistant-Integration/Panel/Desktop): Die Bottom-Bar ist auf Desktop-Breite wieder am Dashboard-Shell ausgerichtet und überdeckt nicht mehr die Home-Assistant-Sidebar.
- Changed (Home-Assistant-Integration/Panel/Shopping): Der separate Einkauf/Grocy-AI-Hero wurde entfernt; die Shopping-Ansicht startet direkt mit dem Inhaltsbereich `Produktsuche`.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.64` erhöht.

## 2026-07-04 (Version 8.0.63)

- Changed (Home-Assistant-Integration/Panel/Mobile): Die Bottom-Bar nutzt auf Smartphones die volle Bildschirmbreite und enthält jetzt den Barcode-Scanner als direkten Schnellzugriff.
- Changed (Home-Assistant-Integration/Panel/Shopping): Die leere Produktsuche ist kompakter und verzichtet ohne aktive Suche auf den zusätzlichen Such-Shell-Rahmen.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.63` erhöht.

## 2026-06-29 (Version 8.0.62)

- Added (Lager/Auto-Cleanup): Neue Add-on-Optionen `auto_cleanup_enabled` und `auto_cleanup_months` entfernen überfällige Nicht-Konserven aus dem Lager.
- Added (Dashboard/Lager): Lagerprodukte zeigen einen Auto-Cleanup-Infobadge und das Dashboard bietet eine manuelle Auto-Cleanup-Aktion.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.62` erhöht.

## 2026-06-29 (Version 8.0.61)

- Added (Konfiguration/KI): Separate Schalter für Ollama-Texterstellung, Ollama-Bildabfragen, Cloud-AI global und Cloud-AI-Texterstellung inklusive OpenAI-Textmodell.
- Fix (Home-Assistant-Integration/Panel/Shopping): Dashboard-Root-Events werden jetzt tatsächlich nur einmal gebunden. Dadurch löst ein einzelner Klick auf `Produkt prüfen` nur noch einen Submit aus und vorhandene Produkte werden nicht doppelt zur Einkaufsliste hinzugefügt.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.61` erhöht.

## 2026-06-29 (Version 8.0.59)

- Added (Konfiguration/Ollama): Neue Option `ollama_enabled`, um lokale Ollama-Abfragen komplett zu deaktivieren und Setups nur mit Cloud-Funktionen oder ganz ohne Ollama zu betreiben.
- Fix (Konfiguration/Ollama): Die Ollama-URL bleibt wieder vollständig frei einstellbar; automatische Umschreibungen konfigurierter URLs wurden entfernt.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.59` erhöht.

## 2026-06-29 (Version 8.0.58)

- Fix (Home-Assistant/Ollama): Die interne Standard-Ollama-URL verwendet jetzt den vom Ollama-Add-on dokumentierten Hostnamen `76e18fb5-ollama` statt der zuvor angenommenen Underscore-Variante.
- Fix (Konfiguration): Sowohl alte `homeassistant.local:11434`-Werte als auch die kurzzeitig dokumentierte Underscore-Variante werden beim Laden auf `http://76e18fb5-ollama:11434/api/generate` normalisiert.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.58` erhöht.

## 2026-06-29 (Version 8.0.57)

- Fix (Home-Assistant/Ollama): Die Standard-Ollama-URL zeigt jetzt auf den internen Ollama-Add-on-Host `76e18fb5-ollama`, da `homeassistant.local:11434` nach aktuellen Home-Assistant-Updates nicht mehr zuverlässig zum Ollama-Add-on routet.
- Fix (Konfiguration): Legacy-Standardwerte mit `http://homeassistant.local:11434/api/generate` werden beim Laden automatisch auf die interne Add-on-URL normalisiert.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.57` erhöht.

## 2026-06-29 (Version 8.0.56)

- Fix (Dashboard/Produktsuche): Fehlerhafte oder nicht erreichbare Ollama-Produktanalysen liefern jetzt eine sichere Standardanalyse, damit `POST /api/dashboard/search` neue Produkte weiter anlegen kann statt mit `500` abzubrechen.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.56` erhöht.

## 2026-03-27 (Version 8.0.55)

- Changed (Home-Assistant-Integration/Panel/Topbar): Das Kühlschrank-Icon wurde in der Topbar an den Anfang der Eyebrow verschoben.
- Changed (Home-Assistant-Integration/Panel/Topbar): Das Hamburger-Menü steht jetzt direkt vor der Überschrift `Grocy AI` (an der bisherigen Icon-Position).
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.55` erhöht.

## 2026-03-26 (Version 8.0.54)

- Fix (Home-Assistant-Integration/Panel/Rezepte): Die primären Buttons `Rezept hinzufügen` und `Rezepte laden` werden in der nativen Rezept-Ansicht jetzt explizit als einzeiliges Grid gerendert.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.54` erhöht.

## 2026-03-26 (Version 8.0.53)

- Fix (Dashboard/Produktsuche): Nach erfolgreicher Antwort von `POST /api/dashboard/search` wird der lokale Submit-In-Flight-Status jetzt sofort freigegeben, bevor das anschließende Shopping-List-Reload wartet. Dadurch erscheint die UI-Meldung „Produktanfrage läuft bereits...“ nicht mehr fälschlich während eines langsamen Listen-Refreshs.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.53` erhöht.

## 2026-03-26 (Version 8.0.52)

- Changed (Home-Assistant-Integration/Panel/Topbar): Das Kühlschrank-Icon in der Topbar wurde unter den Sidebar-Button verschoben und steht jetzt in einer eigenen Zeile direkt vor der Überschrift `Grocy AI`.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.52` erhöht.
