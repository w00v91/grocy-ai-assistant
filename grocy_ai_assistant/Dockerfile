# Nutze das offizielle HA Base Image
FROM ghcr.io/home-assistant/amd64-base:latest

WORKDIR /app

# 1. System-Abhängigkeiten installieren
# Wir fügen build-base hinzu, falls pip etwas kompilieren muss
RUN apk add --no-cache python3 py3-pip build-base python3-dev

# 2. Abhängigkeiten mit dem Sicherheits-Flag installieren
# Das Flag --break-system-packages ist bei neueren Python-Versionen in Alpine Pflicht
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages

# 3. Kopiere die Dateien (Das hat laut deinem Screenshot #10 & #11 jetzt geklappt!)
COPY api/ /app/api/
COPY core/ /app/core/
COPY requirements.txt /app/requirements.txt
COPY run.sh /app/run.sh
COPY custom_components/ /app/custom_components/

# 4. Rechte setzen (Hat in Screenshot #12 auch geklappt!)
RUN chmod a+x /app/run.sh

# 5. Abhängigkeiten installieren
# WICHTIG: Nutze 'pip3', da bei Alpine 'pip' oft nicht direkt gelinkt ist
RUN pip3 install --no-cache-dir -r requirements.txt

# Startbefehl
CMD [ "/app/run.sh" ]