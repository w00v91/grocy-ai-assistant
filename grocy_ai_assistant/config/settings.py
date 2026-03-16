import json
import logging
import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ADDON_CONFIG_PATH = PROJECT_ROOT / "grocy_ai_assistant" / "config.json"
INTEGRATION_MANIFEST_PATH = (
    PROJECT_ROOT
    / "grocy_ai_assistant"
    / "custom_components"
    / "grocy_ai_assistant"
    / "manifest.json"
)


def _load_version_from_json(path: Path) -> str | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    version = payload.get("version")
    return str(version) if version else None


@lru_cache(maxsize=1)
def _default_addon_version() -> str:
    return _load_version_from_json(ADDON_CONFIG_PATH) or "dev"


@lru_cache(maxsize=1)
def _default_required_integration_version() -> str:
    return _load_version_from_json(INTEGRATION_MANIFEST_PATH) or "dev"


def _default_ollama_url() -> str:
    configured_ollama_url = os.getenv("GROCY_AI_OLLAMA_URL") or os.getenv("OLLAMA_URL")
    if configured_ollama_url:
        return configured_ollama_url
    return "http://host.docker.internal:11434/api/generate"


class Settings(BaseModel):
    api_key: str = "standard_passwort"
    addon_version: str = os.getenv("GROCY_AI_ADDON_VERSION", _default_addon_version())
    required_integration_version: str = os.getenv(
        "GROCY_AI_REQUIRED_INTEGRATION_VERSION",
        _default_required_integration_version(),
    )
    ollama_url: str = Field(default_factory=_default_ollama_url)
    ollama_model: str = "llama3"
    ollama_llava_model: str = "llava"
    scanner_barcode_fallback_seconds: int = 5
    scanner_llava_min_confidence: int = 75
    scanner_llava_timeout_seconds: int = 45
    dashboard_polling_interval_seconds: int = 5
    image_generation_enabled: bool = False
    generate_missing_product_images_on_startup: bool = False
    openai_api_key: str = ""
    openai_image_model: str = "gpt-image-1"
    debug_mode: bool = False
    notification_global_enabled: bool = True
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
