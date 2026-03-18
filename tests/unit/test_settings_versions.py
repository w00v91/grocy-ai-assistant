import json

from grocy_ai_assistant.config import options_store, settings


def test_default_versions_are_synced_with_project_metadata():
    settings._default_addon_version.cache_clear()
    settings._default_required_integration_version.cache_clear()

    addon_version = options_store.parse_simple_yaml(
        settings.ADDON_CONFIG_PATH.read_text(encoding="utf-8")
    )["version"]
    integration_version = json.loads(
        settings.INTEGRATION_MANIFEST_PATH.read_text(encoding="utf-8")
    )["version"]

    assert settings._default_addon_version() == addon_version
    assert settings._default_required_integration_version() == integration_version


def test_default_ollama_url_prefers_grocy_ai_env(monkeypatch):
    monkeypatch.setenv("GROCY_AI_OLLAMA_URL", "http://ollama-addon:11434/api/generate")
    monkeypatch.setenv("OLLAMA_URL", "http://generic-ollama:11434/api/generate")

    assert settings._default_ollama_url() == "http://ollama-addon:11434/api/generate"


def test_default_ollama_url_falls_back_to_generic_env(monkeypatch):
    monkeypatch.delenv("GROCY_AI_OLLAMA_URL", raising=False)
    monkeypatch.setenv("OLLAMA_URL", "http://generic-ollama:11434/api/generate")

    assert settings._default_ollama_url() == "http://generic-ollama:11434/api/generate"


def test_default_ollama_url_uses_docker_host_fallback(monkeypatch):
    monkeypatch.delenv("GROCY_AI_OLLAMA_URL", raising=False)
    monkeypatch.delenv("OLLAMA_URL", raising=False)

    assert (
        settings._default_ollama_url()
        == "http://host.docker.internal:11434/api/generate"
    )
