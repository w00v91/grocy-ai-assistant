import logging
import sys

import uvicorn
from fastapi import FastAPI, Request

from grocy_ai_assistant.api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Grocy AI Assistant API")
app.include_router(router)


@app.middleware("http")
async def log_request_info(request: Request, call_next):
    logger.info("Anfrage erhalten: %s %s", request.method, request.url.path)
    return await call_next(request)


if __name__ == "__main__":
    print(">>> GROCY AI ENGINE GESTARTET AUF PORT 8000 <<<", flush=True)
    uvicorn.run("grocy_ai_assistant.api.main:app", host="0.0.0.0", port=8000)
