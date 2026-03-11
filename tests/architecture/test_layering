from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = PROJECT_ROOT / "grocy_ai_assistant"

LAYER_RULES = {
    "api": {"custom_components"},
    "ai": {"api", "custom_components", "services"},
    "core": {"api", "custom_components"},
    "services": {"api", "custom_components"},
    "custom_components": {"ai", "services"},
}


def _module_from_path(path: Path) -> str:
    return ".".join(path.relative_to(PROJECT_ROOT).with_suffix("").parts)


def _first_party_target(module_name: str) -> str | None:
    if not module_name.startswith("grocy_ai_assistant."):
        return None
    parts = module_name.split(".")
    return parts[1] if len(parts) > 1 else None


def _iter_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            if node.module:
                imports.append(node.module)

    return imports


def test_layering_dependencies_are_respected():
    violations: list[str] = []

    for py_file in PACKAGE_ROOT.rglob("*.py"):
        rel_parts = py_file.relative_to(PACKAGE_ROOT).parts
        if not rel_parts:
            continue
        source_layer = rel_parts[0]
        forbidden_layers = LAYER_RULES.get(source_layer)
        if not forbidden_layers:
            continue

        source_module = _module_from_path(py_file)
        for imported_module in _iter_imports(py_file):
            target_layer = _first_party_target(imported_module)
            if target_layer in forbidden_layers:
                violations.append(
                    f"{source_module} imports {imported_module} (forbidden: {source_layer} -> {target_layer})"
                )

    assert not violations, "\n".join(sorted(violations))
