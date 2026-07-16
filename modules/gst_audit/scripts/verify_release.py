from __future__ import annotations

import ast
import configparser
import re
from pathlib import Path

REQUIRED = [
    "requirements.txt",
    "pyproject.toml",
    "pytest.ini",
    "GSTInvoiceAudit.spec",
    "build_exe.bat",
    "sample_data/03_csv_import_cases.csv",
    "sample_data/02_review_and_duplicate_cases.xlsx",
    "sample_data/01_balanced_invoices.xlsx",
    "scripts/run_sample_dataset_checks.py",
    "scripts/create_sample_data.py",
    "START_GST_AUDIT_PRO.bat",
    "RUN_WEB_GST_AUDIT.bat",
    "requirements-web.txt",
    "web_app.py",
    "web_portal/audit_service.py",
    "web_portal/server.py",
    "web_portal/templates/index.html",
    "web_portal/static/web.css",
    "web_portal/static/web.js",
    "tests/test_web_dual_mode_support.py",
    "main.py",
    "README.md",
    "docs/FOLDER_STRUCTURE_AND_WORKFLOW_ALGORITHM.md",
    "docs/V9_8_UI_UX_COMPLETION.md",
    "docs/V9_9_EFFECTIVENESS_RELEASE.md",
    "docs/ELITE_PRO_RELEASE_NOTES.md",
    "docs/SIMPLE_GUI_ELITE_V9_9_5.md",
    "docs/DASHBOARD_ELITE_V9_9_6.md",
    "docs/GUI_SYNC_CLARITY_V9_9_7.md",
    "docs/WORKFLOW_CLARITY_V9_9_8.md",
    "docs/PROFESSIONAL_FOLDER_STRUCTURE_V9_9_9.md",
    "docs/SECTIONWISE_REVIEW_GUIDE_V9_9_9.md",
    "docs/WORKFLOW_ARCHITECTURE_V9_9_9.md",
    "dashboard/README.md",
    "dashboard/__init__.py",
    "theme/README.md",
    "theme/__init__.py",
    "workflow/README.md",
    "workflow/__init__.py",
    "docs/FINAL_RUN_GUIDE.md",
    "docs/RELEASE_VALIDATION_CHECKLIST.md",
    "docs/OWNERSHIP_AND_BOUNDARIES.md",
    "docs/ARCHITECTURE_DEPENDENCY_GRAPH.md",
    "tests/test_core_audit.py",
    "tests/test_v9_7_architecture_enforcement.py",
    "tests/test_v9_8_ui_workflow_completion.py",
    "tests/test_v9_9_effectiveness_release.py",
    "tests/test_v9_9_6_dashboard_elite.py",
    "scripts/dev.py",
    "scripts/preflight_windows.py",
    "app/version.py",
    "app/core/branding.py",
    "config/app_identity.json",
    "config/README.md",
    "app/core/quality_gate.py",
    "tests/test_elite_quality_gate.py",
    "app/ui/main_window.py",
    "app/ui/views/dashboard_view.py",
    "app/ui/views/upload_view.py",
    "app/ui/views/audit_view.py",
    "app/ui/views/supplier_view.py",
    "app/ui/views/reconciliation_view.py",
    "app/ui/views/export_view.py",
    "app/ui/views/settings_view.py",
    "app/ui/controllers/dashboard_controller.py",
    "app/ui/widgets/metric_card.py",
    "app/ui/widgets/status_chip.py",
    "app/ui/widgets/data_table.py",
    "app/assets/styles/main.qss",
]

FORBIDDEN_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "htmlcov", ".git"}
IGNORED_GENERATED_ROOT_DIRS = {".venv", "venv", "env", ".env", "build", "dist"}
FORBIDDEN_FILE_NAMES = {".coverage", "coverage.xml", "pytestdebug.log"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".tmp", ".log"}


def _read_version(root: Path) -> str | None:
    version_file = root / "app" / "version.py"
    if not version_file.exists():
        return None
    tree = ast.parse(version_file.read_text(encoding="utf-8"), filename=str(version_file))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "APP_VERSION":
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return node.value.value
    return None


def _pyproject_version(root: Path) -> str | None:
    text = (root / "pyproject.toml").read_text(encoding="utf-8") if (root / "pyproject.toml").exists() else ""
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, flags=re.MULTILINE)
    return match.group(1) if match else None


def _imports_from_python(path: Path) -> set[str]:
    imports: set[str] = set()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        raise
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def verify_release(root: Path) -> list[str]:
    problems: list[str] = []

    for rel in REQUIRED:
        if not (root / rel).exists():
            problems.append(f"Missing required release file: {rel}")

    app_version = _read_version(root)
    project_version = _pyproject_version(root)
    if not app_version:
        problems.append("Could not read APP_VERSION from app/version.py")
    if app_version and project_version and app_version != project_version:
        problems.append(f"Version mismatch: app/version.py={app_version}, pyproject.toml={project_version}")
    if app_version:
        readme = (root / "README.md").read_text(encoding="utf-8") if (root / "README.md").exists() else ""
        if app_version not in readme:
            problems.append(f"README.md does not mention current APP_VERSION {app_version}")

    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if rel.parts and rel.parts[0] in IGNORED_GENERATED_ROOT_DIRS:
            continue
        if any(part in FORBIDDEN_DIR_NAMES for part in path.parts):
            problems.append(f"Release contains local/VC artifact: {rel}")
        if path.name in FORBIDDEN_FILE_NAMES:
            problems.append(f"Release contains local test artifact: {rel}")
        if path.suffix in FORBIDDEN_SUFFIXES:
            problems.append(f"Release contains generated/local file: {rel}")
        if len(path.parts) >= 2 and path.parts[-2:] == ("artifacts", "screenshots"):
            problems.append(f"Release contains runtime screenshot output directory: {rel}")
        if path.suffix == ".py":
            try:
                imports = _imports_from_python(path)
            except SyntaxError as exc:
                problems.append(f"Python syntax error in {rel}: line {exc.lineno}: {exc.msg}")
                continue
            rel_str = str(rel).replace("\\", "/")
            if rel_str.startswith("app/core/"):
                forbidden = [imp for imp in imports if imp == "PySide6" or imp.startswith("PySide6.") or imp.startswith("app.ui")]
                if forbidden:
                    problems.append(f"Backend boundary violation in {rel}: imports {', '.join(sorted(forbidden))}")

    return sorted(set(problems))


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    failures = verify_release(root)
    if failures:
        print("Release verification failed:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)
    print("Release verification passed.")
