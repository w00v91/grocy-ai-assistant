import json

from grocy_ai_assistant.config import settings


def test_default_versions_are_synced_with_project_metadata():
    settings._default_addon_version.cache_clear()
    settings._default_required_integration_version.cache_clear()

    addon_version = json.loads(settings.ADDON_CONFIG_PATH.read_text(encoding="utf-8"))[
        "version"
    ]
    integration_version = json.loads(
        settings.INTEGRATION_MANIFEST_PATH.read_text(encoding="utf-8")
    )["version"]

    assert settings._default_addon_version() == addon_version
    assert settings._default_required_integration_version() == integration_version
