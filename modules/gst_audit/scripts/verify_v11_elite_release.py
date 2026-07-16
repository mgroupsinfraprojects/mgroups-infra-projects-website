from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "app/workflow/audit_workflow_controller.py",
    "app/storage/database.py",
    "app/audit_trail/event_logger.py",
    "app/security/permission_matrix.py",
    "app/gstn/gsp_client.py",
    "app/einvoice/einvoice_payload_builder.py",
    "app/ewaybill/eway_payload_builder.py",
    "docs/V11_ELITE_99_PLUS_RELEASE.md",
]


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).exists()]
    if missing:
        print("Missing V11 files:", missing)
        return 1
    print("V11 elite architecture readiness gate: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
