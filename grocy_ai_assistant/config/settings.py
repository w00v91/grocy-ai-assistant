import json
import logging
import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from grocy_ai_assistant.config import options_store
from grocy_ai_assistant.config.options_store import parse_simple_yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ADDON_CONFIG_PATH = PROJECT_ROOT / "grocy_ai_assistant" / "config.yaml"
INTEGRATION_MANIFEST_PATH = (
    PROJECT_ROOT
    / "grocy_ai_assistant"
    / "custom_components"
    / "grocy_ai_assistant"
    / "manifest.json"
)
RECOMMENDED_OLLAMA_ADDON_URL = "http://76e18fb5-ollama:11434/api/generate"
LEGACY_OLLAMA_URLS = {
    "http://homeassistant.local:11434/api/generate",
    "http://homeassistant.local:11434/api/generate/",
    "http://76e18fb5_ollama:11434/api/generate",
    "http://76e18fb5_ollama:11434/api/generate/",
}


def _load_version_from_metadata(path: Path) -> str | None:
    try:
        if path.suffix == ".yaml":
            payload = parse_simple_yaml(path.read_text(encoding="utf-8"))
        else:
            payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    version = payload.get("version")
    return str(version) if version else None


@lru_cache(maxsize=1)
def _default_addon_version() -> str:
    return _load_version_from_metadata(ADDON_CONFIG_PATH) or "dev"


@lru_cache(maxsize=1)
def _default_required_integration_version() -> str:
    return _load_version_from_metadata(INTEGRATION_MANIFEST_PATH) or "dev"


def _default_ollama_url() -> str:
    configured_ollama_url = os.getenv("GROCY_AI_OLLAMA_URL") or os.getenv("OLLAMA_URL")
    if configured_ollama_url:
        return configured_ollama_url
    return RECOMMENDED_OLLAMA_ADDON_URL


class Settings(BaseModel):
    api_key: str = "standard_passwort"
    addon_version: str = os.getenv("GROCY_AI_ADDON_VERSION", _default_addon_version())
    required_integration_version: str = os.getenv(
        "GROCY_AI_REQUIRED_INTEGRATION_VERSION",
        _default_required_integration_version(),
    )
    ollama_url: str = Field(default_factory=_default_ollama_url)

    @field_validator("ollama_url")
    @classmethod
    def _normalize_legacy_ollama_url(cls, value: str) -> str:
        normalized_value = str(value or "").strip()
        if normalized_value in LEGACY_OLLAMA_URLS:
            logger.warning(
                "Legacy Ollama URL %s wird durch die interne Add-on-URL %s ersetzt",
                normalized_value,
                RECOMMENDED_OLLAMA_ADDON_URL,
            )
            return RECOMMENDED_OLLAMA_ADDON_URL
        return normalized_value or RECOMMENDED_OLLAMA_ADDON_URL

    ollama_model: str = "llama3"
    ollama_llava_model: str = "llava"
    ollama_timeout_seconds: int = 60
    scanner_barcode_fallback_seconds: int = 5
    scanner_llava_min_confidence: int = 75
    scanner_llava_timeout_seconds: int = 45
    dashboard_polling_interval_seconds: int = 5
    image_generation_enabled: bool = False
    generate_missing_product_images_on_startup: bool = False
    initial_info_sync: bool = False
    openai_api_key: str = ""
    openai_image_model: str = "gpt-image-1"
    debug_mode: bool = False
    notification_global_enabled: bool = True
    grocy_base_url: str = "http://homeassistant.local:9192/api"
    grocy_api_key: str = ""
    stable_diffusion_url: str = "http://172.17.0.1:7860/sdapi/v1/txt2img"


logger = logging.getLogger(__name__)


def _settings_cache_token() -> tuple[str, ...]:
    token_parts: list[str] = []
    for path in (
        options_store.ADDON_OPTIONS_YAML_PATH,
        options_store.LEGACY_ADDON_OPTIONS_JSON_PATH,
        options_store.REPOSITORY_CONFIG_YAML_PATH,
    ):
        try:
            stat_result = path.stat()
        except OSError:
            continue
        token_parts.append(f"{path}:{stat_result.st_mtime_ns}:{stat_result.st_size}")

    if token_parts:
        return tuple(token_parts)
    return ("defaults",)


@lru_cache(maxsize=4)
def _get_settings_cached(cache_token: tuple[str, ...]) -> Settings:
    try:
        payload = options_store.load_addon_options()
        if payload:
            return Settings(**payload)
    except Exception as error:
        logger.error("Fehler beim Lesen der options.yaml: %s", error)
    return Settings()


def get_settings() -> Settings:
    return _get_settings_cached(_settings_cache_token())


def _clear_get_settings_cache() -> None:
    _get_settings_cached.cache_clear()


get_settings.cache_clear = _clear_get_settings_cache  # type: ignore[attr-defined]
