from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
EXPORT_FOLDER = BASE_DIR / "exports"
BACKUP_FOLDER = BASE_DIR / "backups"

# V16.1: create local SQLite/support folders before SQLAlchemy connects.
# This fixes Windows/local run error: sqlite3.OperationalError: unable to open database file.
for _folder in (INSTANCE_DIR, UPLOAD_FOLDER, EXPORT_FOLDER, BACKUP_FOLDER):
    _folder.mkdir(parents=True, exist_ok=True)

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-before-production")
    _database_url = os.environ.get("STOCK_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if _database_url and _database_url.startswith("postgres://"):
        _database_url = _database_url.replace("postgres://", "postgresql://", 1)

    # Use a normalized POSIX-style absolute SQLite URI for Windows compatibility.
    SQLALCHEMY_DATABASE_URI = _database_url or ("sqlite:///" + (INSTANCE_DIR / "inventory.db").as_posix())
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    UPLOAD_FOLDER = str(UPLOAD_FOLDER)
    EXPORT_FOLDER = str(EXPORT_FOLDER)
    BACKUP_FOLDER = str(BACKUP_FOLDER)
