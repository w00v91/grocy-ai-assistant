# Nutze das offizielle HA Base Image
FROM ghcr.io/home-assistant/amd64-base:latest

WORKDIR /app

# 1. Installiere Python und Pip (Zwingend notwendig für Alpine-Images)
RUN apk add --no-cache python3 py3-pip

# 2. Kopiere die Dateien (Das hat laut deinem Screenshot #10 & #11 jetzt geklappt!)
COPY api/ /app/api/
COPY core/ /app/core/
COPY requirements.txt /app/requirements.txt
COPY run.sh /app/run.sh
COPY main.py /app/main.py
COPY custom_components/ /app/custom_components/

# 3. Rechte setzen (Hat in Screenshot #12 auch geklappt!)
RUN chmod a+x /app/run.sh

# 4. Abhängigkeiten installieren
# WICHTIG: Nutze 'pip3', da bei Alpine 'pip' oft nicht direkt gelinkt ist
RUN pip3 install --no-cache-dir -r requirements.txt

# Startbefehl
CMD [ "/app/run.sh" ]