# Auto-split from app.py for readability. Executed by app.py in application globals.

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def settings_dict(force_refresh=False):
    """Return website settings with request-level caching.

    Many public/admin templates call settings_dict(), field_visible(),
    style_inline(), has_permission(), etc. Without caching, one page render can
    repeatedly query the Setting table. This cache is per request, so it is
    safe and refreshes automatically on the next request.
    """
    if not force_refresh and hasattr(g, "_settings_dict_cache"):
        return g._settings_dict_cache
    g._settings_dict_cache = {row.key: row.value for row in Setting.query.all()}
    return g._settings_dict_cache


def clear_settings_cache():
    if hasattr(g, "_settings_dict_cache"):
        try:
            delattr(g, "_settings_dict_cache")
        except Exception:
            pass


def set_setting(key, value):
    row = Setting.query.get(key)
    if row:
        row.value = value or ""
    else:
        db.session.add(Setting(key=key, value=value or ""))
    # Keep current request cache accurate after updates.
    if hasattr(g, "_settings_dict_cache"):
        g._settings_dict_cache[key] = value or ""


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






# ─────────────────────────────────────────────────────────────
# Portal roles and role-permission matrix
# ─────────────────────────────────────────────────────────────
ROLE_LABELS = {
    "developer": "Developer / Super Admin",
    "owner": "Developer / Owner (Legacy)",
    "admin": "Developer / Super Admin (Legacy)",
    "super_admin": "Developer / Super Admin (Legacy)",
    "administrator": "Developer / Super Admin (Legacy)",
    "developer_owner": "Developer / Owner (Legacy)",
    "developer_owner_legacy": "Developer / Owner (Legacy)",
    "company_owner": "Company Owner",
    "manager": "Manager",
    "editor": "Manager / Editor (Legacy)",
    "supervisor": "Supervisor",
    "authorized": "Authorized Person",
    "viewer": "Viewer",
}

ROLE_ORDER = ["developer", "company_owner", "manager", "supervisor", "authorized", "viewer"]
MANAGEABLE_PERMISSION_ROLES = ["company_owner", "manager", "supervisor", "authorized", "viewer"]
LOCKED_FULL_CONTROL_ROLES = {"developer", "owner", "admin", "super_admin", "administrator", "developer_owner", "developer_owner_legacy"}

USER_CREATABLE_ROLES = {
    "developer": ["developer", "company_owner", "manager", "supervisor", "authorized", "viewer"],
    "owner": ["developer", "company_owner", "manager", "supervisor", "authorized", "viewer"],
    "company_owner": ["manager", "supervisor", "authorized", "viewer"],
    "manager": ["supervisor", "authorized", "viewer"],
    "editor": ["supervisor", "authorized", "viewer"],
}

PERMISSION_GROUPS = [
    {
        "key": "modules",
        "title": "Module visibility",
        "description": "Controls which boxes appear in My Workspace after login.",
        "permissions": [
            ("portal_view", "Portal access", "Can login and open My Workspace"),
            ("website_view", "Website box", "Can open Website module"),
            ("stock_view", "Stock box", "Can open Stock module"),
            ("employees_view", "Employees box", "Can open Employees module"),
            ("gst_view", "GST / Audit box", "Can open GST module"),
            ("reports_view", "Reports box", "Can open Reports module"),
            ("users_view", "Users box", "Can open Users & Roles"),
            ("system_settings", "System box", "Can open System controls"),
        ],
    },
    {
        "key": "website",
        "title": "Website management",
        "description": "Public website content and design controls.",
        "permissions": [
            ("website_live_edit", "Live Editor", "Edit visible website text from the live preview"),
            ("website_settings_edit", "Website settings", "Company profile, SEO, contact, credentials"),
            ("design_edit", "Design Center", "Theme, colors, fonts, buttons and homepage visibility"),
            ("website_about_edit", "About & Experience", "Company description, mission, vision and experience summary"),
            ("website_services_edit", "Services", "Add, edit and publish service cards"),
            ("website_projects_edit", "Projects / Works", "Maintain project records, descriptions and images"),
            ("website_gallery_edit", "Gallery", "Publish or hide site/work photos and captions"),
            ("media_edit", "Media Library", "Upload/crop/reuse website images"),
        ],
    },
    {
        "key": "stock",
        "title": "Stock management",
        "description": "Stock permissions are ready now; stock pages will use them after integration.",
        "permissions": [
            ("stock_add", "Add / receive stock", "Can add stock-in or material receive records"),
            ("stock_transfer", "Transfer stock", "Can move material between store/site"),
            ("stock_adjust", "Adjust stock", "Can correct stock with approval/audit"),
            ("stock_delete", "Delete stock records", "Dangerous permission; keep mostly off"),
            ("stock_reports", "Stock reports", "Can view/export stock reports"),
        ],
    },
    {
        "key": "employees",
        "title": "Employee management",
        "description": "Employee module permissions for future employee system.",
        "permissions": [
            ("employees_add", "Add employee", "Can create employee records"),
            ("employees_edit", "Edit employee", "Can update employee data"),
            ("employees_delete", "Delete employee", "Dangerous permission; keep mostly off"),
            ("employees_reports", "Employee reports", "Can view/export employee reports"),
        ],
    },
    {
        "key": "gst",
        "title": "GST / Audit",
        "description": "GST permissions for invoice upload, audit checking and reports.",
        "permissions": [
            ("gst_upload", "Upload invoices", "Can upload GST/invoice files"),
            ("gst_edit", "Edit GST records", "Can correct GST/invoice entries"),
            ("gst_reports", "GST reports", "Can view/export GST audit reports"),
        ],
    },
    {
        "key": "reports_audit",
        "title": "Reports & audit",
        "description": "Reporting and activity log access.",
        "permissions": [
            ("reports_export", "Export reports", "Can download business reports"),
            ("audit_view", "View audit logs", "Can see activity history"),
        ],
    },
    {
        "key": "users",
        "title": "Users & roles",
        "description": "User creation/edit controls. Role editing is restricted separately.",
        "permissions": [
            ("users_create", "Create users", "Can create only allowed lower-level roles"),
            ("users_edit", "Edit / reset users", "Can edit allowed lower-level users and reset password"),
            ("users_delete", "Delete users", "Dangerous permission; disable is safer"),
            ("roles_manage", "Manage role permissions", "Can change this permission matrix"),
        ],
    },
    {
        "key": "system",
        "title": "System control",
        "description": "Production-level controls. Keep this mostly for Developer only.",
        "permissions": [
            ("backup_download", "Download backup", "Can download system/content backup"),
            ("backup_restore", "Restore backup", "Can overwrite content from backup"),
        ],
    },
]

ALL_PERMISSION_KEYS = []
for _group in PERMISSION_GROUPS:
    for _key, _label, _note in _group["permissions"]:
        if _key not in ALL_PERMISSION_KEYS:
            ALL_PERMISSION_KEYS.append(_key)

ROLE_DEFAULT_PERMISSIONS = {
    "developer": {"*"},
    "owner": {"*"},
    "admin": {"*"},
    "super_admin": {"*"},
    "administrator": {"*"},
    "developer_owner": {"*"},
    "developer_owner_legacy": {"*"},
    "company_owner": {
        "portal_view", "stock_view", "employees_view", "gst_view", "reports_view", "users_view",
        "stock_add", "stock_transfer", "stock_adjust", "stock_reports",
        "employees_add", "employees_edit", "employees_reports",
        "gst_upload", "gst_edit", "gst_reports", "reports_export", "audit_view",
        "users_create", "users_edit", "backup_download",
    },
    "manager": {
        "portal_view", "stock_view", "employees_view", "reports_view", "users_view",
        "stock_add", "stock_transfer", "stock_reports",
        "employees_add", "employees_edit", "employees_reports", "reports_export",
        "users_create", "users_edit",
    },
    "editor": {
        "portal_view", "website_view", "website_live_edit", "website_about_edit", "website_services_edit",
        "website_projects_edit", "website_gallery_edit", "media_edit", "stock_view", "employees_view",
        "reports_view", "users_view", "users_create", "users_edit",
    },
    "supervisor": {
        "portal_view", "stock_view", "reports_view", "stock_add", "stock_transfer", "stock_reports",
    },
    "authorized": {
        "portal_view", "stock_view", "reports_view", "stock_add", "stock_reports",
    },
    "viewer": {"portal_view", "reports_view", "stock_view", "stock_reports"},
}

# Backward-compatible name used by older code.
ROLE_PERMISSIONS = ROLE_DEFAULT_PERMISSIONS

PORTAL_MODULES = [
    {"key": "website", "title": "Website", "description": "Live Editor, Design Center, public content and media.", "url_endpoint": "portal_web", "permission": "website_view", "icon": "🌐"},
    {"key": "stock", "title": "Stock", "description": "Materials, stock in/out, transfers, site stock and stock reports.", "url_endpoint": "portal_stock", "permission": "stock_view", "icon": "📦"},
    {"key": "employees", "title": "Employees", "description": "Employee records, attendance, roles and work details.", "url_endpoint": "portal_employees", "permission": "employees_view", "icon": "👥"},
    {"key": "gst", "title": "GST / Audit", "description": "GST dashboard, invoice upload, audit checks and reports.", "url_endpoint": "portal_gst", "permission": "gst_view", "icon": "🧾"},
    {"key": "reports", "title": "Reports", "description": "Business, stock, project and user-access reports.", "url_endpoint": "portal_reports", "permission": "reports_view", "icon": "📊"},
    {"key": "users", "title": "Users", "description": "Create users, set roles, reset passwords and control access.", "url_endpoint": "portal_users", "permission": "users_view", "icon": "🔐"},
    {"key": "system", "title": "System", "description": "Backup, restore, versions, audit logs and system status.", "url_endpoint": "portal_system", "permission": "system_settings", "icon": "⚙️"},
]


def role_label(role):
    return ROLE_LABELS.get(role or "", (role or "Unknown").replace("_", " ").title())


def current_role():
    adm = current_admin()
    return adm.role if adm else None


def permission_setting_key(role, permission):
    return f"roleperm_{role}_{permission}"


def role_default_has_permission(role, permission):
    defaults = ROLE_DEFAULT_PERMISSIONS.get(role, set())
    return "*" in defaults or permission in defaults


def role_permission_enabled(role, permission, site=None):
    if role in LOCKED_FULL_CONTROL_ROLES:
        return True
    if permission not in ALL_PERMISSION_KEYS and permission != "*":
        return role_default_has_permission(role, permission)
    site = site or settings_dict()
    key = permission_setting_key(role, permission)
    if key in site:
        return flag_value(site.get(key), False)
    return role_default_has_permission(role, permission)


def role_permission_map(role):
    site = settings_dict()
    return {permission: role_permission_enabled(role, permission, site=site) for permission in ALL_PERMISSION_KEYS}


def role_allowed_module_keys(role):
    perms = role_permission_map(role)
    return [m["key"] for m in PORTAL_MODULES if perms.get(m["permission"], False)]


def role_allowed_module_titles(role):
    perms = role_permission_map(role)
    return [m["title"] for m in PORTAL_MODULES if perms.get(m["permission"], False)]


def user_allowed_module_titles(user):
    if not user or not user.is_active:
        return []
    return role_allowed_module_titles(user.role)


def has_permission(permission):
    adm = current_admin()
    if not adm:
        return False
    return role_permission_enabled(adm.role, permission)


def allowed_modules():
    rows = []
    for module in PORTAL_MODULES:
        if has_permission(module["permission"]):
            item = dict(module)
            try:
                item["url"] = url_for(module["url_endpoint"])
            except Exception:
                item["url"] = "#"
            rows.append(item)
    return rows


def creatable_roles_for_current_user():
    role = current_role()
    allowed = USER_CREATABLE_ROLES.get(role, [])
    return [(r, role_label(r)) for r in allowed]


def can_create_role(role):
    return role in USER_CREATABLE_ROLES.get(current_role(), [])


def can_manage_user_account(user):
    adm = current_admin()
    if not adm or not user:
        return False
    if adm.role in LOCKED_FULL_CONTROL_ROLES:
        return True
    if user.id == adm.id:
        return False
    return user.role in USER_CREATABLE_ROLES.get(adm.role, [])


def visible_users_query_for_current_user():
    adm = current_admin()
    if not adm:
        return Admin.query.filter(False)
    if adm.role in LOCKED_FULL_CONTROL_ROLES:
        return Admin.query.order_by(Admin.id.asc())
    allowed_roles = USER_CREATABLE_ROLES.get(adm.role, [])
    if not allowed_roles:
        return Admin.query.filter(Admin.id == adm.id).order_by(Admin.id.asc())
    return Admin.query.filter(Admin.role.in_(allowed_roles)).order_by(Admin.id.asc())


def visible_users_for_current_user():
    return visible_users_query_for_current_user().all()


def paginate_query(query, page=1, per_page=10):
    try:
        page = max(1, int(page or 1))
    except Exception:
        page = 1
    try:
        per_page = max(5, min(50, int(per_page or 10)))
    except Exception:
        per_page = 10
    total = query.count()
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, pages)
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return SimpleNamespace(
        items=items, page=page, per_page=per_page, total=total, pages=pages,
        has_prev=page > 1, has_next=page < pages, prev_num=page - 1, next_num=page + 1,
    )


def permission_required(permission):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_admin():
                flash("Login required.", "warning")
                return redirect(url_for("admin_login"))
            if not has_permission(permission):
                flash("You do not have access to that module.", "danger")
                return redirect(url_for("portal_workspace"))
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

ADMIN_AREA_REQUIRED_PERMISSION = {
    "live_edit": "website_live_edit",
    "settings": "website_settings_edit",
    "appearance": "design_edit",
    "about": "website_about_edit",
    "services": "website_services_edit",
    "projects": "website_projects_edit",
    "gallery": "website_gallery_edit",
    "page_builder": "website_about_edit",
    "ordering": "website_projects_edit",
    "media": "media_edit",
    "restore": "backup_restore",
    "versions": "audit_view",
    "enquiries": "reports_view",
}


def admin_area_from_path(path):
    if path.startswith("/admin/live-edit"): return "live_edit"
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
    if path.startswith("/admin/users"): return "users"
    if path.startswith("/admin/permissions"): return "permissions"
    return "settings"


def role_can_write(role, area):
    if role in LOCKED_FULL_CONTROL_ROLES:
        return True
    if area == "users":
        return role_permission_enabled(role, "users_edit") or role_permission_enabled(role, "users_create")
    if area == "permissions":
        return role_permission_enabled(role, "roles_manage")
    permission = ADMIN_AREA_REQUIRED_PERMISSION.get(area)
    if permission:
        return role_permission_enabled(role, permission)
    if role == "company_owner":
        return area not in {"restore"}
    if role in {"viewer", "supervisor", "authorized"}:
        return False
    if role in {"manager", "editor"}:
        site = settings_dict()
        return flag_value(site.get(f"perm_editor_{area}"), DEFAULT_EDITOR_PERMISSION.get(area, False))
    return False

def audit(action, detail=""):
    try:
        db.session.add(AuditLog(admin_username=admin_username(), action=action, detail=detail[:1000], ip_address=request.headers.get("X-Forwarded-For", request.remote_addr or "")))
        db.session.commit()
    except Exception:
        db.session.rollback()


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
            flash("Login required or account disabled.", "warning")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


@app.before_request
def protect_admin_requests():
    # Keep portal modules truly separated. A user who can see the Website box
    # should not automatically see every old /admin page. Each old admin page
    # is now guarded by its own module/action permission.
    if request.path.startswith("/admin") and session.get("admin_id"):
        exempt_prefixes = (
            "/admin/login", "/admin/logout", "/admin/forgot-password",
            "/admin/reset-password", "/admin/mode",
        )
        if request.path not in {"/admin", "/admin/"} and not request.path.startswith(exempt_prefixes):
            area = admin_area_from_path(request.path)
            required = ADMIN_AREA_REQUIRED_PERMISSION.get(area)
            if required and not has_permission(required):
                flash("Your role does not have access to that page. Use My Workspace for assigned tools.", "danger")
                return redirect(url_for("portal_workspace"))

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


