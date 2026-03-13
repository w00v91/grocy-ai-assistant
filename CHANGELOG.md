# Changelog

## Unreleased

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
