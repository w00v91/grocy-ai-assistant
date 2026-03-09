# Nutze das offizielle HA Base Image
FROM ghcr.io/home-assistant/amd64-base:latest

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# 1. System-Abhängigkeiten installieren
# Wir fügen build-base hinzu, falls pip etwas kompilieren muss
RUN apk add --no-cache python3 py3-pip build-base python3-dev

# 2. Python-Paket vollständig kopieren, damit absolute Imports funktionieren
COPY . /app/grocy_ai_assistant/

# Laufzeitdateien an die erwarteten Orte legen
COPY requirements.txt /app/requirements.txt
COPY run.sh /app/run.sh
COPY custom_components/ /app/custom_components/

# 3. Rechte setzen (Hat in Screenshot #12 auch geklappt!)
RUN chmod a+x /app/run.sh

# Paket-Root in den Python-Pfad aufnehmen
ENV PYTHONPATH=/app

# 4. Abhängigkeiten mit dem Sicherheits-Flag installieren
# Das Flag --break-system-packages ist bei neueren Python-Versionen in Alpine Pflicht
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages

# Startbefehl
CMD [ "/app/run.sh" ]
