
ARG BUILD_FROM=ghcr.io/home-assistant/base:3.19
FROM $BUILD_FROM

WORKDIR /app

COPY ../../api /app/api
COPY ../../core /app/core
COPY ../../requirements.txt /app

RUN pip install -r requirements.txt

CMD ["python","-m","uvicorn","api.main:app","--host","0.0.0.0","--port","8000"]
