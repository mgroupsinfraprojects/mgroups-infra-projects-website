from __future__ import annotations

import shutil
import zipfile
from pathlib import Path


def create_backup(paths: list[str | Path], output_zip: str | Path) -> Path:
    out = Path(output_zip)
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in paths:
            path = Path(item)
            if path.exists() and path.is_file():
                zf.write(path, path.name)
    return out
