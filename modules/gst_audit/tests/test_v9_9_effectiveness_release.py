from __future__ import annotations

import ast
from pathlib import Path

from app.version import APP_VERSION, RELEASE_NAME
from scripts.verify_release import verify_release

ROOT = Path(__file__).resolve().parents[1]


def test_v9_9_version_is_distinguishable_from_broken_v98_release():
    assert APP_VERSION == "11.13.0"
    assert "Dashboard Elite" in RELEASE_NAME
    assert f'version = "{APP_VERSION}"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert APP_VERSION in (ROOT / "README.md").read_text(encoding="utf-8")


def test_release_verifier_has_syntax_gate():
    source = (ROOT / "scripts" / "verify_release.py").read_text(encoding="utf-8")
    assert "ast.parse" in source
    assert "Python syntax error" in source


def test_release_verifier_has_version_sync_gate():
    source = (ROOT / "scripts" / "verify_release.py").read_text(encoding="utf-8")
    assert "Version mismatch" in source
    assert "pyproject.toml" in source


def test_windows_preflight_script_exists_and_is_parseable():
    path = ROOT / "scripts" / "preflight_windows.py"
    assert path.exists()
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    source = path.read_text(encoding="utf-8")
    assert "REQUIRED_MODULES" in source
    assert "check_startup_import" in source


def test_effectiveness_docs_exist():
    required = [
        "docs/V9_9_EFFECTIVENESS_RELEASE.md",
        "docs/FINAL_RUN_GUIDE.md",
        "docs/RELEASE_VALIDATION_CHECKLIST.md",
    ]
    for rel in required:
        assert (ROOT / rel).exists(), rel


def test_release_verification_has_no_structural_errors_after_filtering_runtime_cache():
    problems = verify_release(ROOT)
    non_cache = [
        item
        for item in problems
        if "__pycache__" not in item and ".pytest_cache" not in item and ".pyc" not in item and ".coverage" not in item
    ]
    assert non_cache == []
