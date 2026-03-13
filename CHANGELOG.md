# Changelog

All notable changes to this project are documented in this file.

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
