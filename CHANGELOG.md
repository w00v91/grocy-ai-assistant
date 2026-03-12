# Changelog

## Unreleased

- Entfernt: konfigurierbarer `scanner_llava_prompt` in den Add-on-Optionen.
- Neu: `scanner_llava_min_confidence` (1-100) als Add-on-Option zur Steuerung der benötigten Sicherheit.
- Anpassung: LLaVA-Prompt wird nun intern erzeugt und enthält die konfigurierbare Mindest-Sicherheit sowie die Vorgabe, bei zu geringer Sicherheit `NULL` zu antworten.
