from __future__ import annotations

import zipfile
from pathlib import Path


def restore_backup(backup_zip: str | Path, target_dir: str | Path) -> Path:
    target = Path(target_dir); target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(backup_zip) as zf:
        zf.extractall(target)
    return target
