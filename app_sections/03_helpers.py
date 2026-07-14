# Auto-split from app.py for readability. Executed by app.py in application globals.

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def settings_dict():
    return {row.key: row.value for row in Setting.query.all()}


def set_setting(key, value):
    row = Setting.query.get(key)
    if row:
        row.value = value or ""
    else:
        db.session.add(Setting(key=key, value=value or ""))


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def compress_image(local_path: Path):
    if Image is None:
        return
    try:
        with Image.open(local_path) as img:
            img.verify()
        with Image.open(local_path) as img:
            img = img.convert("RGB") if img.mode not in ("RGB", "RGBA") else img
            max_side = int(os.environ.get("IMAGE_MAX_SIDE", "1800"))
            if max(img.size) > max_side:
                img.thumbnail((max_side, max_side))
            ext = local_path.suffix.lower()
            if ext in {".jpg", ".jpeg"}:
                img.save(local_path, quality=82, optimize=True)
            elif ext == ".png":
                img.save(local_path, optimize=True)
            elif ext == ".webp":
                img.save(local_path, quality=82, method=6)
    except Exception:
        # If compression fails, keep original upload. The upload was already extension-filtered.
        return


def save_upload(file_storage, prefix="upload"):
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_file(file_storage.filename):
        raise ValueError("Only PNG, JPG, JPEG, WEBP, and GIF image files are allowed.")

    original = secure_filename(file_storage.filename)
    ext = original.rsplit(".", 1)[1].lower()
    filename = f"{prefix}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{uuid.uuid4().hex[:8]}.{ext}"
    target = UPLOAD_DIR / filename

    # Save to a temporary local file first. This avoids broken records caused by
    # directly passing Werkzeug FileStorage objects to Cloudinary and lets Pillow
    # validate/compress the image before upload.
    file_storage.save(target)
    compress_image(target)

    if cloudinary_ready():
        try:
            result = cloudinary.uploader.upload(
                str(target),
                folder=os.environ.get("CLOUDINARY_FOLDER", "mgroups"),
                public_id=filename.rsplit(".", 1)[0],
                overwrite=False,
                resource_type="image",
            )
            uploaded_url = result.get("secure_url") or result.get("url")
            if not uploaded_url or not uploaded_url.startswith(("http://", "https://")):
                raise ValueError("Cloudinary did not return a usable image URL.")
            try:
                target.unlink(missing_ok=True)
            except Exception:
                pass
            return uploaded_url
        except Exception as exc:
            try:
                target.unlink(missing_ok=True)
            except Exception:
                pass
            raise ValueError(f"Cloudinary upload failed. Check CLOUDINARY_URL/API secret. Details: {exc}")

    if is_production_runtime():
        try:
            target.unlink(missing_ok=True)
        except Exception:
            pass
        _, detail = cloudinary_status()
        raise ValueError("Cloudinary is not active, so production upload was blocked. " + detail)

    return f"uploads/{filename}"


def media_url(path):
    if not path:
        return ""
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return url_for("static", filename=path)


def slugify(value):
    value = (value or "").strip().lower()
    out = []
    last_dash = False
    for ch in value:
        if ch.isalnum():
            out.append(ch)
            last_dash = False
        elif not last_dash:
            out.append("-")
            last_dash = True
    return "".join(out).strip("-") or "area"


def service_area_list(site=None):
    site = site or settings_dict()
    raw = site.get("service_areas", "")
    rows = []
    for line in raw.splitlines():
        name = line.strip(" -\t")
        if name:
            rows.append({"name": name, "slug": slugify(name)})
    return rows


def extract_cloudinary_public_id(url):
    if not url or "res.cloudinary.com" not in url:
        return None
    try:
        part = url.split("/upload/", 1)[1]
        # remove transformations/version if present
        pieces = [x for x in part.split("/") if x]
        if pieces and pieces[0].startswith("v") and pieces[0][1:].isdigit():
            pieces = pieces[1:]
        public = "/".join(pieces)
        if "." in public:
            public = public.rsplit(".", 1)[0]
        return public
    except Exception:
        return None


def delete_media(path):
    if not path:
        return
    try:
        if path.startswith("http://") or path.startswith("https://"):
            public_id = extract_cloudinary_public_id(path)
            if public_id and cloudinary and os.environ.get("CLOUDINARY_URL"):
                cloudinary.uploader.destroy(public_id, invalidate=True, resource_type="image")
            return
        target = BASE_DIR / "static" / path
        if target.exists() and target.is_file():
            target.unlink()
    except Exception:
        # Never block deletion of database rows because a media cleanup failed.
        return


def smtp_settings():
    host = os.environ.get("SMTP_HOST")
    username = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")
    if not (host and username and password):
        return None
    return {
        "host": host,
        "username": username,
        "password": password,
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "sender": os.environ.get("SMTP_FROM") or username,
        "use_tls": os.environ.get("SMTP_USE_TLS", "1") == "1",
    }


def send_mail(to_addr, subject, body, reply_to=None):
    config = smtp_settings()
    if not (to_addr and config):
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config["sender"]
    msg["To"] = to_addr
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(body)
    context = ssl.create_default_context()
    if config["use_tls"]:
        with smtplib.SMTP(config["host"], config["port"], timeout=12) as smtp:
            smtp.starttls(context=context)
            smtp.login(config["username"], config["password"])
            smtp.send_message(msg)
    else:
        with smtplib.SMTP_SSL(config["host"], config["port"], context=context, timeout=12) as smtp:
            smtp.login(config["username"], config["password"])
            smtp.send_message(msg)
    return True


def send_enquiry_email(enquiry):
    site = settings_dict()
    to_addr = os.environ.get("SMTP_TO") or site.get("notification_email") or site.get("email")
    body = f"""New enquiry from M-GROUPS website

Name: {enquiry.name}
Phone: {enquiry.phone}
Email: {enquiry.email}
Project Type: {enquiry.project_type}

Message:
{enquiry.message}

Submitted: {enquiry.created_at}
"""
    return send_mail(
        to_addr=to_addr,
        subject=f"New website enquiry - {enquiry.name}",
        body=body,
        reply_to=enquiry.email or None,
    )


def password_token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_password_reset_token(admin):
    raw_token = secrets.token_urlsafe(38)
    expires_minutes = int(os.environ.get("ADMIN_RESET_TOKEN_MINUTES", "30"))
    token = PasswordResetToken(
        admin_id=admin.id,
        token_hash=password_token_hash(raw_token),
        expires_at=datetime.utcnow() + timedelta(minutes=expires_minutes),
        requested_ip=request.headers.get("X-Forwarded-For", request.remote_addr or "")[:80],
    )
    PasswordResetToken.query.filter_by(admin_id=admin.id, used_at=None).update({"used_at": datetime.utcnow()})
    db.session.add(token)
    db.session.commit()
    return raw_token, token


def send_admin_reset_email(admin, reset_url):
    recovery_email = (admin.recovery_email or admin.email or "").strip()
    if not recovery_email:
        return False
    body = f"""Password reset requested for M-GROUPS website admin.

Username: {admin.username}
Reset link: {reset_url}

This link expires in {os.environ.get('ADMIN_RESET_TOKEN_MINUTES', '30')} minutes.
If you did not request this, ignore this email and review admin audit logs.
"""
    return send_mail(
        to_addr=recovery_email,
        subject="M-GROUPS admin password reset",
        body=body,
    )


def admin_username():
    if session.get("admin_id"):
        admin = Admin.query.get(session.get("admin_id"))
        return admin.username if admin else "admin"
    return "system"


def current_admin():
    try:
        if not session.get("admin_id"):
            return None
        admin = Admin.query.get(session.get("admin_id"))
        if not admin or not admin.is_active:
            session.clear()
            return None
        return admin
    except Exception:
        return None


def admin_mode():
    return session.get("admin_mode", "simple")


def advanced_mode_enabled():
    return admin_mode() == "advanced"


def require_role(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            adm = current_admin()
            if not adm or adm.role not in roles:
                flash("You do not have permission for that action.", "danger")
                return redirect(url_for("admin_dashboard"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator




ADMIN_PERMISSION_AREAS = [
    ("settings", "Website Settings", "Company profile, SEO, contact and public credential fields"),
    ("appearance", "Visibility & Appearance", "Global colors, fonts, labels and section visibility"),
    ("about", "About & Experience", "Company description, mission, vision, values and statistics"),
    ("services", "Services", "Service cards, images, icons, text and service field visibility"),
    ("projects", "Projects / Works", "Project case studies, private values, images and field visibility"),
    ("gallery", "Gallery", "Gallery images, captions and public display"),
    ("page_builder", "Custom Homepage Block Builder", "Optional homepage blocks with title, body, image and button"),
    ("ordering", "Drag & Drop Ordering", "Homepage, service, project, gallery and block ordering"),
    ("media", "Media Library", "Upload and crop local images"),
    ("restore", "Restore Backup", "Restore JSON content backups"),
    ("versions", "Version History", "Restore or compare old versions"),
    ("enquiries", "Enquiries", "Read/export enquiry records"),
]

DEFAULT_EDITOR_PERMISSION = {
    "settings": False, "appearance": False, "about": True, "services": True,
    "projects": True, "gallery": True, "page_builder": False, "ordering": False,
    "media": True, "enquiries": False, "restore": False, "versions": False,
}


def admin_area_from_path(path):
    if path.startswith("/admin/settings"): return "settings"
    if path.startswith("/admin/appearance"): return "appearance"
    if path.startswith("/admin/about"): return "about"
    if path.startswith("/admin/services"): return "services"
    if path.startswith("/admin/projects"): return "projects"
    if path.startswith("/admin/gallery"): return "gallery"
    if path.startswith("/admin/page-builder"): return "page_builder"
    if path.startswith("/admin/ordering") or path.startswith("/admin/reorder"): return "ordering"
    if path.startswith("/admin/media"): return "media"
    if path.startswith("/admin/restore"): return "restore"
    if path.startswith("/admin/versions"): return "versions"
    if path.startswith("/admin/enquiries") or path.startswith("/admin/export/enquiries"): return "enquiries"
    return "settings"


def role_can_write(role, area):
    if role == "owner":
        return True
    if role == "viewer":
        return False
    if role == "editor":
        site = settings_dict()
        return flag_value(site.get(f"perm_editor_{area}"), DEFAULT_EDITOR_PERMISSION.get(area, False))
    return False

def audit(action, detail=""):
    try:
        db.session.add(AuditLog(admin_username=admin_username(), action=action, detail=detail[:1000], ip_address=request.headers.get("X-Forwarded-For", request.remote_addr or "")))
        db.session.commit()
    except Exception:
        db.session.rollback()



def live_edit_attrs(target_type, field, target_id=""):
    """Return safe data attributes only inside the owner live-edit route."""
    try:
        if request.endpoint != "admin_live_edit":
            return ""
        from markupsafe import Markup, escape
        attrs = (
            'data-live-edit="1" '
            f'data-live-target="{escape(str(target_type))}" '
            f'data-live-field="{escape(str(field))}" '
            f'data-live-id="{escape(str(target_id or ""))}" '
            'title="Click to edit. Changes save on blur."'
        )
        return Markup(attrs)
    except Exception:
        return ""


def csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def csrf_field():
    return f'<input type="hidden" name="csrf_token" value="{csrf_token()}">'


def validate_csrf():
    if request.method == "POST":
        expected = session.get("csrf_token")
        provided = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        if not expected or not provided or not secrets.compare_digest(expected, provided):
            abort(400, "Invalid CSRF token")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_admin():
            flash("Admin login required or account disabled.", "warning")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


@app.before_request
def protect_state_changes():
    if request.method == "POST":
        validate_csrf()
        if request.path.startswith("/admin") and session.get("admin_id"):
            adm = current_admin()
            if adm and not request.path.endswith("/logout"):
                area = admin_area_from_path(request.path)
                if not role_can_write(adm.role, area):
                    abort(403, f"Your role cannot change {area} content")


@app.after_request
def security_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    return resp



def flag_value(value, default=False):
    if value is None or value == "":
        return bool(default)
    return str(value).strip().lower() in {"1", "true", "yes", "on", "show", "visible", "public"}


def field_vis_key(section, field):
    return f"vis_{section}_{field}"


def field_default(section, field, default=True):
    for name, _label, field_default_value in FIELD_VISIBILITY_GROUPS.get(section, []):
        if name == field:
            return bool(field_default_value)
    return bool(default)


def field_visible(section, field, default=None):
    if default is None:
        default = field_default(section, field, True)
    try:
        site = settings_dict()
        return flag_value(site.get(field_vis_key(section, field)), default)
    except Exception:
        return bool(default)


def item_visible_fields(obj, section):
    default_fields = [name for name, _label, default in FIELD_VISIBILITY_GROUPS.get(section, []) if default]
    raw = getattr(obj, "visible_fields", "") if obj is not None else ""
    if not raw:
        return set(default_fields)
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return set(str(x) for x in data)
    except Exception:
        pass
    return set(default_fields)


def item_field_visible(obj, section, field, default=None):
    if default is None:
        default = field_default(section, field, True)
    if obj is None:
        return bool(default)
    raw = getattr(obj, "visible_fields", "") or ""
    if not raw:
        return bool(default)
    return field in item_visible_fields(obj, section)


def pack_item_visible_fields(section):
    fields = []
    for field, _label, _default in FIELD_VISIBILITY_GROUPS.get(section, []):
        if request.form.get(f"vis_{field}"):
            fields.append(field)
    return json.dumps(fields, ensure_ascii=False)


