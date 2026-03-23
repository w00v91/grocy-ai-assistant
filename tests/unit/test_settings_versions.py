import json
import re

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


def test_get_settings_reloads_nested_grouped_options_when_yaml_changes(
    tmp_path, monkeypatch
):
    options_path = tmp_path / "options.yaml"
    repository_config_path = tmp_path / "config.yaml"

    options_path.write_text(
        """grocy:
  grocy_api_key: first-key
""",
        encoding="utf-8",
    )
    repository_config_path.write_text("options: {}\n", encoding="utf-8")

    monkeypatch.setattr(options_store, "ADDON_OPTIONS_YAML_PATH", options_path)
    monkeypatch.setattr(
        options_store, "REPOSITORY_CONFIG_YAML_PATH", repository_config_path
    )
    settings.get_settings.cache_clear()

    initial_settings = settings.get_settings()
    assert initial_settings.grocy_api_key == "first-key"

    options_path.write_text(
        """grocy:
  grocy_api_key: second-key
cloud_ai:
  image_generation_enabled: true
""",
        encoding="utf-8",
    )

    reloaded_settings = settings.get_settings()
    assert reloaded_settings.grocy_api_key == "second-key"
    assert reloaded_settings.image_generation_enabled is True


def _extract_version(pattern: str, content: str) -> str:
    match = re.search(pattern, content, re.MULTILINE)

    assert match is not None
    return match.group(1)


def test_changelog_top_version_is_synced_with_project_metadata():
    changelog_version = _extract_version(
        r"^##\s+\d{4}-\d{2}-\d{2}\s+\(Version\s+([^\)]+)\)",
        (settings.PROJECT_ROOT / "grocy_ai_assistant" / "CHANGELOG.md").read_text(
            encoding="utf-8"
        ),
    )
    addon_version = options_store.parse_simple_yaml(
        settings.ADDON_CONFIG_PATH.read_text(encoding="utf-8")
    )["version"]
    manifest_version = json.loads(
        settings.INTEGRATION_MANIFEST_PATH.read_text(encoding="utf-8")
    )["version"]
    const_version = _extract_version(
        r'^INTEGRATION_VERSION\s*=\s*"([^"]+)"$',
        (
            settings.PROJECT_ROOT
            / "grocy_ai_assistant"
            / "custom_components"
            / "grocy_ai_assistant"
            / "const.py"
        ).read_text(encoding="utf-8"),
    )
    frontend_version = _extract_version(
        r"^const DEFAULT_INTEGRATION_VERSION = '([^']+)';$",
        (
            settings.PROJECT_ROOT
            / "grocy_ai_assistant"
            / "custom_components"
            / "grocy_ai_assistant"
            / "panel"
            / "frontend"
            / "grocy-ai-dashboard.js"
        ).read_text(encoding="utf-8"),
    )

    assert changelog_version == addon_version == manifest_version == const_version
    assert frontend_version == changelog_version
