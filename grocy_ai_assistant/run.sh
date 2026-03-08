#!/usr/bin/with-contenv bashio

# Pfade definieren
SOURCE_DIR="/app/custom_components/grocy_ai_assistant"
TARGET_DIR="/config/custom_components/grocy_ai_assistant"

bashio::log.info "Prüfe Installation der Custom Integration..."

# Falls der Zielordner nicht existiert, erstelle ihn
if [ ! -d "$TARGET_DIR" ]; then
    bashio::log.info "Integration nicht gefunden. Installiere..."
    mkdir -p "$TARGET_DIR"
fi

# Dateien kopieren (nur wenn sie sich unterscheiden oder neu sind)
cp -rf "$SOURCE_DIR/." "$TARGET_DIR/"

# Berechtigungen sicherstellen
chmod -R 755 "$TARGET_DIR"

bashio::log.info "-------------------------------------------------------"
bashio::log.warning "Integration wurde synchronisiert!"
bashio::log.warning "Falls dies die Erstinstallation war: Bitte starte"
bashio::log.warning "Home Assistant JETZT NEU, damit die Integration"
bashio::log.warning "unter 'Geräte & Dienste' gefunden werden kann."
bashio::log.info "-------------------------------------------------------"

# Starte nun den eigentlichen AI-Service (deine Python App)
bashio::log.info "Starte Grocy AI Service..."
python3 /app/main.py