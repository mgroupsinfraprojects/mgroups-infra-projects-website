import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
EXPORT_FOLDER = os.path.join(BASE_DIR, "exports")
BACKUP_FOLDER = os.path.join(BASE_DIR, "backups")

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-before-production")
    _database_url = os.environ.get("STOCK_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if _database_url and _database_url.startswith("postgres://"):
        _database_url = _database_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _database_url or ("sqlite:///" + os.path.join(INSTANCE_DIR, "inventory.db"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    UPLOAD_FOLDER = UPLOAD_FOLDER
    EXPORT_FOLDER = EXPORT_FOLDER
    BACKUP_FOLDER = BACKUP_FOLDER
