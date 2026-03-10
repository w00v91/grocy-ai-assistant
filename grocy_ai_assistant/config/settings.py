import json
import logging
import os
from functools import lru_cache

from pydantic import BaseModel


class Settings(BaseModel):
    api_key: str = "standard_passwort"
    addon_version: str = os.getenv("GROCY_AI_ADDON_VERSION", "dev")
    required_integration_version: str = os.getenv(
        "GROCY_AI_REQUIRED_INTEGRATION_VERSION", "2.0.7"
    )
    ollama_url: str = "http://10.0.0.2:11434/api/generate"
    ollama_model: str = "llama3"
    grocy_base_url: str = "http://homeassistant.local:9192/api"
    grocy_api_key: str = ""
    stable_diffusion_url: str = "http://172.17.0.1:7860/sdapi/v1/txt2img"


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    options_path = "/data/options.json"
    if os.path.exists(options_path):
        try:
            with open(options_path, "r", encoding="utf-8") as file:
                payload = json.load(file)
                return Settings(**payload)
        except Exception as error:
            logger.error("Fehler beim Lesen der options.json: %s", error)
    return Settings()
