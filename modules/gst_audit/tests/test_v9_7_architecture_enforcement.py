from __future__ import annotations

import ast
import re
from pathlib import Path

from app.version import APP_VERSION

ROOT = Path(__file__).resolve().parents[1]


def _imports_for(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                found.add(node.module)
    return found


def test_v97_core_has_no_ui_or_pyside_dependencies() -> None:
    violations: list[str] = []
    for path in (ROOT / "app/core").rglob("*.py"):
        imports = _imports_for(path)
        forbidden = [name for name in imports if name == "PySide6" or name.startswith("PySide6.") or name == "app.ui" or name.startswith("app.ui.")]
        if forbidden:
            violations.append(f"{path.relative_to(ROOT)} imports {forbidden}")
    assert violations == []


def test_v97_required_architecture_docs_exist() -> None:
    required = [
        "docs/ARCHITECTURE_DEPENDENCY_GRAPH.md",
        "docs/OWNERSHIP_AND_BOUNDARIES.md",
        "docs/V9_7_ARCHITECTURE_ENFORCEMENT.md",
        "docs/adr/0001-keep-app-runtime-root.md",
        "docs/adr/0002-core-ui-separation.md",
        "docs/adr/0003-report-export-boundary.md",
        "docs/adr/0004-security-foundation-boundary.md",
        "docs/adr/0005-guided-search-ui-decision.md",
        "quality/architecture_rules.md",
        "quality/test_matrix.md",
        "deployment/release_checklist.md",
    ]
    assert [item for item in required if not (ROOT / item).exists()] == []


def test_v97_logical_layer_packages_are_present_without_moving_runtime_code() -> None:
    required = [
        "frontend/__init__.py",
        "frontend/views.py",
        "frontend/widgets.py",
        "backend/__init__.py",
        "backend/audit.py",
        "backend/models.py",
        "data_layer/__init__.py",
        "data_layer/database.py",
        "security_layer/__init__.py",
        "security_layer/security.py",
        "app/ui/main_window.py",
        "app/core/audit_engine.py",
    ]
    assert [item for item in required if not (ROOT / item).exists()] == []


def test_v97_logical_layer_facades_import_cleanly() -> None:
    import backend.audit  # noqa: F401
    import backend.models  # noqa: F401
    import data_layer.database  # noqa: F401
    import frontend.views  # noqa: F401
    import frontend.widgets  # noqa: F401
    import security_layer.security  # noqa: F401


def test_v97_version_is_single_sourced_and_project_metadata_matches() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert f'version = "{APP_VERSION}"' in pyproject
    assert APP_VERSION == "11.13.0"


def test_v97_developer_command_script_exposes_standard_commands() -> None:
    source = (ROOT / "scripts/dev.py").read_text(encoding="utf-8")
    for command in ["test", "test-cov", "verify", "smoke", "clean", "compile"]:
        assert f'"{command}"' in source


def test_v97_release_cleanliness_rules_are_enforced_by_verify_script() -> None:
    source = (ROOT / "scripts/verify_release.py").read_text(encoding="utf-8")
    for token in ["__pycache__", ".pytest_cache", ".coverage", "coverage.xml", ".pyc", ".pyo", ".tmp", ".log"]:
        assert token in source


def test_v97_folder_structure_docs_state_runtime_mapping() -> None:
    structure = (ROOT / "docs/FOLDER_STRUCTURE.md").read_text(encoding="utf-8")
    module_map = (ROOT / "docs/MODULE_MAP.md").read_text(encoding="utf-8")
    combined = structure + "\n" + module_map
    assert re.search(r"app/ui.*frontend|frontend.*app/ui", combined, re.IGNORECASE | re.DOTALL)
    assert re.search(r"app/core.*backend|backend.*app/core", combined, re.IGNORECASE | re.DOTALL)
