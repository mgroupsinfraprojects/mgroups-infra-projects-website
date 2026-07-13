import csv
import io
import json
import os
import secrets
import hashlib
import smtplib
import ssl
import uuid
import re
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from email.message import EmailMessage
from types import SimpleNamespace
from urllib.parse import urlparse, unquote

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

from flask import (
    Flask, Response, abort, flash, g, jsonify, redirect, render_template,
    request, send_file, session, url_for
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

try:
    from PIL import Image
except Exception:  # Pillow is optional at runtime but included in requirements.
    Image = None

try:
    import cloudinary
    import cloudinary.uploader
except Exception:  # Cloudinary is optional.
    cloudinary = None

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except Exception:  # App still runs without limiter if dependency is unavailable.
    Limiter = None
    get_remote_address = None

BASE_DIR = Path(__file__).resolve().parent
if load_dotenv:
    load_dotenv(BASE_DIR / ".env")
INSTANCE_DIR = BASE_DIR / "instance"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
BOOTSTRAP_PASSWORD_FILE = INSTANCE_DIR / "admin_bootstrap_password.txt"
INSTANCE_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", "8")) * 1024 * 1024

app = Flask(__name__)
secret = os.environ.get("SECRET_KEY")
if not secret:
    secret_file = INSTANCE_DIR / ".secret_key"
    if secret_file.exists():
        secret = secret_file.read_text().strip()
    else:
        secret = secrets.token_urlsafe(48)
        secret_file.write_text(secret)
app.config["SECRET_KEY"] = secret
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE", "0") == "1"

# Render often provides DATABASE_URL. Local fallback stays SQLite for easy Windows testing.
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
if not database_url:
    database_url = f"sqlite:///{INSTANCE_DIR / 'website.sqlite3'}"
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

db = SQLAlchemy(app)

def normalize_cloudinary_url():
    """Return a usable Cloudinary URL even if the value was pasted as CLOUDINARY_URL=cloudinary://..."""
    raw = (os.environ.get("CLOUDINARY_URL") or "").strip().strip('"').strip("'")
    if raw.startswith("CLOUDINARY_URL="):
        raw = raw.split("=", 1)[1].strip()
        os.environ["CLOUDINARY_URL"] = raw
    return raw


def is_production_runtime():
    """Render/PostgreSQL deployments must not save uploads to local static storage."""
    return bool(os.environ.get("RENDER") or os.environ.get("DATABASE_URL") or os.environ.get("NO_DEFAULT_PASSWORD") == "1")


def cloudinary_status():
    """Return (ok, message) without exposing secrets."""
    if not cloudinary:
        return False, "Cloudinary package is not installed."
    raw = normalize_cloudinary_url()
    if not raw:
        return False, "CLOUDINARY_URL is missing."
    if "***" in raw:
        return False, "CLOUDINARY_URL contains hidden asterisks. Copy the real API secret from Cloudinary."
    if not raw.startswith("cloudinary://"):
        return False, "CLOUDINARY_URL must start with cloudinary://. Do not include extra text before it."
    try:
        parsed = urlparse(raw)
        if not parsed.hostname:
            return False, "CLOUDINARY_URL is missing cloud name."
        if not parsed.username:
            return False, "CLOUDINARY_URL is missing API key."
        if not parsed.password:
            return False, "CLOUDINARY_URL is missing API secret."
        cloudinary.config(
            cloud_name=parsed.hostname,
            api_key=unquote(parsed.username),
            api_secret=unquote(parsed.password),
            secure=True,
        )
        return True, f"Cloudinary configured for cloud '{parsed.hostname}'."
    except Exception as exc:
        return False, f"Cloudinary configuration error: {exc}"


def configure_cloudinary_from_env():
    ok, _ = cloudinary_status()
    return ok


def cloudinary_ready():
    ok, _ = cloudinary_status()
    return ok


configure_cloudinary_from_env()

if Limiter:
    limiter = Limiter(get_remote_address, app=app, default_limits=["300 per hour"], storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"))
else:
    limiter = None




# ─────────────────────────────────────────────────────────────
# Modular section loader
# ─────────────────────────────────────────────────────────────
# The original app.py became too large to maintain. These section files are
# executed in this app module's globals as a low-risk refactor. Existing
# route decorators, model references, and helper names remain unchanged, so
# the Render start command can stay: gunicorn app:app.
SECTION_FILES = [
    "app_sections/01_models.py",
    "app_sections/02_defaults.py",
    "app_sections/03_helpers.py",
    "app_sections/04_styles.py",
    "app_sections/05_drafts_versions.py",
    "app_sections/06_database_seed.py",
    "routes/01_public_routes.py",
    "routes/02_admin_auth_dashboard.py",
    "routes/03_admin_advanced_cms.py",
    "routes/04_admin_content.py",
    "routes/05_admin_tools_users.py",
]


def _load_section(relative_path):
    path = BASE_DIR / relative_path
    code = compile(path.read_text(encoding="utf-8"), str(path), "exec")
    exec(code, globals(), globals())


for _section_file in SECTION_FILES:
    _load_section(_section_file)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")

