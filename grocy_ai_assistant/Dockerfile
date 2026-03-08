FROM ghcr.io/home-assistant/amd64-base:latest

WORKDIR /app

# 1. Kopiere zuerst die Verzeichnisse und Dateien einzeln (ohne ..)
# Stelle sicher, dass diese im gleichen Ordner wie das Dockerfile liegen!
COPY api/ /app/api/
COPY core/ /app/core/
COPY requirements.txt /app/requirements.txt
COPY run.sh /app/run.sh
COPY custom_components/ /app/custom_components/

# 2. Jetzt, wo die Datei da ist, klappt auch das chmod
RUN chmod a+x /app/run.sh

# 3. Abhängigkeiten installieren
RUN pip install --no-cache-dir -r requirements.txt

# Startbefehl
CMD [ "/app/run.sh" ]