## 2026-07-16 (Version 8.0.77)

- Fix (Shopping-UI): Produktanlage und Hintergrund-Bildgenerierung werden in den Statusmeldungen getrennt angezeigt.
- Fix (Shopping-UI): Lokale Doppelklicks während einer Produktanlage melden nun präzise, dass die Produktanlage noch läuft.
- Fix (Shopping-UI): HTTP-409-Konflikte zeigen verständliche Gründe für aktive Produktanlage, Suche oder Bildgenerierung.
- Added (Tests/Frontend): Regressionstests decken Produktanlage mit Hintergrundbildjob, lokale Doppelklicks und Backend-409-Meldungen ab.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.77` erhöht.

## 2026-07-16 (Version 8.0.76)

- Added (Dashboard/Lager): Standortfilter für die native Home-Assistant-Storage-UI und die Legacy-Static-UI ergänzt.
- Fix (Dashboard/Lager): Storage-Liste und Summary senden ausgewählte Lagerorte konsistent als `location_ids` an die Stock-Products-API.
- Added (Tests/Frontend): Regressionstests decken die Übergabe ausgewählter Lagerorte an `/api/dashboard/stock-products` ab.
- Fix (Rezepte/Dashboard): Rezeptvorschläge ignorieren jetzt ungeeignete Lagerstandorte wie `Sonstiges`, sodass die KI nur mit sinnvollen Vorratsorten wie Küche, Vorrat oder Kühlschrank arbeitet.
- Added (Tests): Regressionstest stellt sicher, dass Produkte aus `Sonstiges` nicht in die Rezeptauswahl gelangen.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.76` erhöht.

## 2026-07-13 (Version 8.0.75)

- Fix (Home-Assistant-Integration/API): Die veraltete interne Add-on-URL `grocy_ai_assistant:8000` wird jetzt auf den gültigen Bindestrich-Host normalisiert und nicht mehr als Fallback versucht, damit DNS-Timeouts die Coordinator-Abfragen nicht blockieren.
- Fix (Rezepte/Dashboard): Manuelles Laden von Rezeptvorschlägen umgeht den Rezeptcache und erzwingt eine frische KI-Generierung inklusive erneuter Anbieterprüfung.
- Added (Tests): Regressionstests decken die Legacy-Host-Normalisierung und das Cache-Bypass-Verhalten beim manuellen Rezept-Refresh ab.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.75` erhöht.

## 2026-07-13 (Version 8.0.74)

- Fix (KI/Ollama): Nach einem Text-KI-Verbindungsfehler wird derselbe Anbieter kurzzeitig übersprungen, damit Startup-Prefetch, Sensoren und Dashboard-Reloads keine wiederholten Ollama-Timeouts gegen `homeassistant.local:11434` auslösen.
- Added (Tests/KI): Regressionstest stellt sicher, dass ein kürzlich fehlgeschlagener Ollama-Textanbieter nicht sofort erneut angefragt wird.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.74` erhöht.

## 2026-07-13 (Version 8.0.73)

- Fix (Grocy/Produktanlage): Produkt-Payloads verwenden keine blinde Mengeneinheit `1` mehr, sondern normalisieren ungültige Einheiten auf eine tatsächlich vorhandene Grocy-Mengeneinheit.
- Fix (Grocy/Produktanlage): Wenn Grocy keine gültige Mengeneinheit liefert, bricht die Produktanlage kontrolliert mit einer klaren deutschen Fehlermeldung ab.
- Added (Tests/Grocy): Unit-Tests decken gültige, ungültige und fehlende Mengeneinheiten bei der Produktanlage ab.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.73` erhöht.

## 2026-07-08 (Version 8.0.72)

- Changed (Home-Assistant-Integration/Panel/Shopping): AI- und Input-Vorschläge zeigen beim Übernehmen jetzt explizit die Produktanlage aus einem Vorschlag statt einer generischen Produktsuche an.
- Fix (Home-Assistant-Integration/Panel/Shopping): HTTP-409-Konflikte in diesem Vorschlagspfad werden als bereits laufende Produktanlage gemeldet.
- Added (Tests/Frontend): Regressionstests prüfen die Produktanlage-Statusmeldung und den 409-Konflikttext für AI-/Input-Varianten.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.72` erhöht.

## 2026-07-08 (Version 8.0.71)

- Fix (Dashboard-Suche): In-Flight-Guard nutzt jetzt einen konfigurierbaren, kürzeren Stale-Timeout und liefert bei blockierten Duplikatsuchen einen sicheren Retry-Hinweis zurück.
- Added (Tests/API): Regressionstests prüfen, dass alte Guard-Einträge entfernt werden und frische Einträge weiterhin HTTP 409 inklusive Retry-Hinweis auslösen.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.71` erhöht.

## 2026-07-08 (Version 8.0.70)

- Fix (Home-Assistant-Integration/Panel/Shopping): Der Dashboard-Submit-Pfad ignoriert doppelte Submit-Events jetzt direkt, solange bereits eine Produktsuche läuft, und behält den bestehenden Status ohne neue Topbar-Fehlermeldung bei.
- Added (Tests/Frontend): Regressionstest simuliert zwei schnelle `shopping-submit-query`-Events und prüft einen einzelnen API-Call ohne Fehlermeldung.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.70` erhöht.

## 2026-07-08 (Version 8.0.69)

- Changed (Home-Assistant-Integration/Panel/Shopping): Lokale doppelte Produktsuchen melden jetzt explizit, dass die Anfrage noch verarbeitet wird, und setzen `lastBlockedReason=local_in_flight` zur Diagnose.
- Added (Tests/Frontend): Regressionstest prüft den internen Blockierungsgrund für lokal laufende doppelte Produktsuchen.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.69` erhöht.

## 2026-07-08 (Version 8.0.68)

- Changed (API/Dashboard): Der serverseitige In-Flight-Guard liefert jetzt Diagnosedaten zum bestehenden Suchlauf und protokolliert 409-Konflikte ohne API-Key- oder Secret-Werte.
- Added (Tests/API): Regressionstest prüft das Diagnose-Log bei parallelen identischen Dashboard-Produktsuchen.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.68` erhöht.

## 2026-07-08 (Version 8.0.67)

- Fixed (API/Dashboard): Unerreichbarer Dashboard-Return bleibt entfernt; Ruff-Prüfung bestätigt den statischen Zustand.
- Fix (Dashboard/API/Produktsuche): `dashboard_add_existing_product()` nutzt die zentrale Einkaufslisten-Mengenabstimmung jetzt ohne duplizierten lokalen Korrekturblock.
- Added (Tests/API): Regressionstests prüfen, dass vorhandene Produkte neue und bestehende Einkaufslistenpositionen mit korrigierten Mengen aktualisieren.
- Fix (API/Fehlerbehandlung): Interne Grocy-IO-, Home-Assistant- und Datei/KI-Hilfsabläufe fangen jetzt spezifische Exceptions statt generischer `Exception`-Blöcke ab.
- Changed (Versioning): Versionsstand der Integration auf `8.0.67` erhöht.
- Fix (Security/Config): `api_key` hat keinen produktiven Standard-Fallback mehr und lehnt leere, Platzhalter- oder bekannte Default-Werte beim Laden der Settings ab.
- Changed (Dokumentation/Add-on): Beispiel- und Add-on-Optionen verwenden keine bekannten API-Key-Platzhalter mehr.
- Added (Tests/Config): Regressionstests stellen sicher, dass bekannte Default-Keys nicht akzeptiert werden.
- Security (Dashboard): Der konfigurierte API-Key wird nicht mehr in das Dashboard-HTML gerendert; stattdessen nutzt das statische Dashboard Ingress-/Same-Origin-Kontext oder einen expliziten Browser-Auth-Provider.
- Added (Tests/API/Frontend): Regressionstests prüfen, dass der API-Key nicht im Dashboard-HTML erscheint und der statische API-Client keine HTML-eingebetteten Secrets benötigt.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.67` erhöht.

## 2026-07-08 (Version 8.0.66)

- Added (Tests/Dashboard): `POST /api/dashboard/search` ist jetzt gegen Ollama-Timeouts abgesichert und prüft die sichere Standardanalyse inklusive Freigabe des In-Flight-Guards.
- Fix (Home-Assistant-Integration/Panel/Shopping): Stille Einkaufslisten-Reload-Fehler überschreiben aktive Produktsuche-Hinweise wie „Eine identische Produktsuche läuft bereits...“ nicht mehr im sichtbaren Hilfetext oder in der Topbar.
- Added (Tests/Frontend): Regressionstest für `search_in_flight` plus fehlgeschlagenen stillen Einkaufslisten-Reload ergänzt.
- Fix (Home-Assistant-Integration/Panel/Shopping): Doppelte direkte Produktsuchen mit identischen Parametern werden während eines laufenden API-Aufrufs lokal abgefangen.
- Fix (Dashboard/API/Produktsuche): Parallele identische Produktsuchen liefern jetzt einen strukturierten HTTP-409-Konflikt statt einer erfolgreichen Antwort mit `success=false`.
- Added (Tests/API): Regressionstests prüfen den 409-Konflikttext und dass der serverseitige Such-Guard nach Abschluss der ursprünglichen Suche wieder freigegeben wird.
- Fix (Home-Assistant-Integration/Sensoren): Einkaufsliste-, Lagerprodukte- und bald-ablaufende-Produkte-Sensoren behalten ihre Namen und verwenden jetzt stattdessen `Produkte` als Einheit.
- Changed (Versioning): Versionsstände für Add-on und Integration auf `8.0.66` erhöht.

## 2026-07-08 (Version 8.0.65)

- Fix (Home-Assistant-Integration/Panel/Shopping): Doppelte laufende Produktsuchen werden im Such-Controller jetzt als Fehlerstatus angezeigt, ohne die Einkaufsliste neu zu laden.
- Added (Tests/Frontend): Frontend-Test für `search_in_flight`-Antworten der Produktsuche ergänzt.
- Changed (Versioning): Versionsstand der Integration auf `8.0.66` erhöht.
- Fix (KI-Auswahl/Produktsuche): Textanalysen prüfen jetzt zuerst die aktivierten Optionen und bevorzugen bei eingeschalteter Cloud-AI-Textgenerierung die Cloud-AI; Ollama wird nur noch als Fallback genutzt, wenn Cloud-AI nicht verfügbar ist oder fehlschlägt.
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
