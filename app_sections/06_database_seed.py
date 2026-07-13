# Auto-split from app.py for readability. Executed by app.py in application globals.

# ─────────────────────────────────────────────────────────────
# Database seed
# ─────────────────────────────────────────────────────────────


def ensure_column(table, column, definition):
    """Small safe migration helper for Render updates from older SQLite/Postgres DBs."""
    try:
        dialect = db.engine.dialect.name
        exists = False
        if dialect == "sqlite":
            rows = db.session.execute(db.text(f"PRAGMA table_info({table})")).fetchall()
            exists = any(row[1] == column for row in rows)
        else:
            rows = db.session.execute(db.text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name=:table AND column_name=:column
            """), {"table": table, "column": column}).fetchall()
            exists = bool(rows)
        if not exists:
            db.session.execute(db.text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
            db.session.commit()
    except Exception:
        db.session.rollback()


def run_safe_migrations():
    project_cols = {
        "client_type": "VARCHAR(160) DEFAULT ''",
        "site_area": "VARCHAR(160) DEFAULT ''",
        "duration": "VARCHAR(160) DEFAULT ''",
        "project_value": "VARCHAR(160) DEFAULT ''",
        "scope_of_work": "TEXT DEFAULT ''",
        "challenge": "TEXT DEFAULT ''",
        "solution": "TEXT DEFAULT ''",
        "outcome": "TEXT DEFAULT ''",
    }
    for col, definition in project_cols.items():
        ensure_column("projects", col, definition)
    ensure_column("admins", "role", "VARCHAR(30) DEFAULT 'owner'")
    ensure_column("admins", "email", "VARCHAR(220) DEFAULT ''")
    ensure_column("admins", "recovery_email", "VARCHAR(220) DEFAULT ''")
    ensure_column("admins", "is_active", "BOOLEAN DEFAULT TRUE")
    ensure_column("services", "styles_json", "TEXT DEFAULT '{}'")
    ensure_column("projects", "styles_json", "TEXT DEFAULT '{}'")
    ensure_column("gallery", "styles_json", "TEXT DEFAULT '{}'")
    ensure_column("services", "visible_fields", "TEXT DEFAULT ''")
    ensure_column("services", "is_published", "BOOLEAN DEFAULT TRUE")
    ensure_column("services", "published_at", "TIMESTAMP")
    ensure_column("services", "updated_at", "TIMESTAMP")
    ensure_column("projects", "visible_fields", "TEXT DEFAULT ''")
    ensure_column("projects", "sort_order", "INTEGER DEFAULT 0")
    ensure_column("projects", "is_published", "BOOLEAN DEFAULT TRUE")
    ensure_column("projects", "published_at", "TIMESTAMP")
    ensure_column("projects", "updated_at", "TIMESTAMP")
    ensure_column("gallery", "visible_fields", "TEXT DEFAULT ''")
    ensure_column("gallery", "is_published", "BOOLEAN DEFAULT TRUE")
    ensure_column("gallery", "published_at", "TIMESTAMP")
    ensure_column("gallery", "updated_at", "TIMESTAMP")
    ensure_column("enquiries", "project_type", "VARCHAR(160) DEFAULT ''")
    try:
        now = datetime.utcnow()
        for model in (Service, Project, GalleryItem):
            for row in model.query.all():
                if getattr(row, "is_published", None) is None:
                    row.is_published = True
                if getattr(row, "updated_at", None) is None:
                    row.updated_at = now
        db.session.commit()
    except Exception:
        db.session.rollback()

def get_initial_admin_password():
    """Return first-admin password without shipping a fixed public default.

    Production should set ADMIN_DEFAULT_PASSWORD privately in the host environment.
    For local Windows testing, if ADMIN_DEFAULT_PASSWORD is missing, a one-time
    bootstrap password is generated into instance/admin_bootstrap_password.txt.
    The instance folder is gitignored and must not be deployed.
    """
    env_password = os.environ.get("ADMIN_DEFAULT_PASSWORD", "").strip()
    if env_password:
        return env_password
    if BOOTSTRAP_PASSWORD_FILE.exists():
        raw = BOOTSTRAP_PASSWORD_FILE.read_text(encoding="utf-8", errors="ignore")
        for line in raw.splitlines():
            if line.startswith("PASSWORD="):
                return line.split("=", 1)[1].strip()
    generated = "Mg-" + secrets.token_urlsafe(18) + "!"
    BOOTSTRAP_PASSWORD_FILE.write_text(
        "LOCAL FIRST LOGIN ONLY - DO NOT SHARE OR COMMIT THIS FILE\n"
        f"USERNAME={os.environ.get('ADMIN_USERNAME', 'admin')}\n"
        f"PASSWORD={generated}\n"
        "After first login, open Admin > Change Password. This file can then be deleted.\n",
        encoding="utf-8",
    )
    return generated


def init_db():
    db.create_all()
    run_safe_migrations()
    for key, value in DEFAULT_SETTINGS.items():
        if not Setting.query.get(key):
            db.session.add(Setting(key=key, value=value))
    for section in ("settings", "about"):
        for field, _label, default_visible in FIELD_VISIBILITY_GROUPS.get(section, []):
            key = field_vis_key(section, field)
            if not Setting.query.get(key):
                db.session.add(Setting(key=key, value="1" if default_visible else "0"))

    if not AboutContent.query.get(1):
        db.session.add(AboutContent(
            id=1,
            short_description="M-GROUPS INFRA PROJECTS is an infrastructure and civil works company focused on dependable execution, quality workmanship, and practical project delivery.",
            full_description="M-GROUPS INFRA PROJECTS provides civil construction and infrastructure project services across residential, commercial, industrial, and municipal requirements. The company focuses on systematic planning, site coordination, material control, safety practices, and timely execution.",
            mission="To deliver reliable infrastructure and civil works with disciplined planning, transparent execution, and consistent quality.",
            vision="To become a trusted infrastructure project partner known for dependable delivery, safety, and long-term client relationships.",
            core_values="Quality Work\nSafety First\nTimely Delivery\nTransparent Communication\nResponsible Site Management",
            experience_summary="Project experience and registration details are maintained internally and can be shared with clients when required for verification.",
            years_experience="",
            completed_projects="",
            active_projects="",
            team_members="",
        ))

    if Service.query.count() == 0:
        for title, desc, icon, order in DEFAULT_SERVICES:
            db.session.add(Service(title=title, description=desc, icon=icon, sort_order=order, is_active=True))

    if Project.query.count() == 0:
        seed_projects = [
            {
                "title": "Overhead Tank Construction Documentation - Nagercoil Municipal Corporation",
                "location": "Nagercoil, Kanniyakumari, Tamil Nadu",
                "category": "Municipal Infrastructure",
                "status": "Documented Work",
                "year": "2026",
                "client_type": "Municipal / B2B project documentation",
                "site_area": "Nagercoil Municipal Corporation",
                "duration": "As per work/invoice records",
                "project_value": "Private - available in internal invoice records only",
                "description": "Document-backed construction-related work for overhead tank infrastructure in Nagercoil Municipal Corporation. Public website copy intentionally excludes invoice value, client GSTIN, IRN, acknowledgement number and tax details.",
                "scope_of_work": "Construction-related work connected with 1 lakh, 2 lakhs, 3 lakhs capacity overhead tank infrastructure and 16 m staging height reference in Nagercoil Municipal Corporation documentation.",
                "challenge": "Municipal infrastructure work requires disciplined documentation, GST compliance, site coordination and accurate project records.",
                "solution": "Maintain project documentation, invoice records, GST compliance references, and structured communication while keeping sensitive financial and tax identifiers private.",
                "outcome": "Project documentation available for verification; sensitive financial and party details are withheld from the public website.",
                "is_featured": True,
            },
            {
                "title": "Gopalasamuthiram Works - Experience Certificate Record",
                "location": "Gopalasamuthiram, Tamil Nadu",
                "category": "Experience Certificate",
                "status": "Experience Document Available",
                "year": "Documented",
                "client_type": "Experience record",
                "description": "Experience certificate record available in company documentation for Gopalasamuthiram works.",
                "scope_of_work": "Exact scope should be added from the certificate before publishing detailed claims.",
                "outcome": "Experience documentation available for business verification.",
                "is_featured": True,
            },
            {
                "title": "79 Coastal Works - Experience Certificate Record",
                "location": "Tamil Nadu",
                "category": "Experience Certificate",
                "status": "Experience Document Available",
                "year": "Documented",
                "client_type": "Experience record",
                "description": "Experience certificate record available in company documentation for 79 Coastal works.",
                "scope_of_work": "Exact scope should be added from the certificate before publishing detailed claims.",
                "outcome": "Experience documentation available for business verification.",
                "is_featured": True,
            },
            {
                "title": "Kadukkarai & Kattuputhur Works - Experience Certificate Record",
                "location": "Kadukkarai & Kattuputhur, Tamil Nadu",
                "category": "Experience Certificate",
                "status": "Experience Document Available",
                "year": "Documented",
                "client_type": "Experience record",
                "description": "Experience certificate record available in company documentation for Kadukkarai and Kattuputhur works.",
                "scope_of_work": "Exact scope should be added from the certificate before publishing detailed claims.",
                "outcome": "Experience documentation available for business verification.",
                "is_featured": False,
            },
            {
                "title": "Thenthiruparai Works - Experience Certificate Record",
                "location": "Thenthiruparai, Tamil Nadu",
                "category": "Experience Certificate",
                "status": "Experience Document Available",
                "year": "Documented",
                "client_type": "Experience record",
                "description": "Experience certificate record available in company documentation for Thenthiruparai works.",
                "scope_of_work": "Exact scope should be added from the certificate before publishing detailed claims.",
                "outcome": "Experience documentation available for business verification.",
                "is_featured": False,
            },
            {
                "title": "Dindigul Work Order Documentation",
                "location": "Dindigul, Tamil Nadu",
                "category": "Work Order Documentation",
                "status": "Document Available",
                "year": "Documented",
                "client_type": "Work order record",
                "description": "Work order documentation available in the company case details folder. Full document details should be reviewed internally before publishing public claims.",
                "scope_of_work": "To be entered from verified work order details by admin.",
                "outcome": "Document available for internal verification.",
                "is_featured": False,
            },
        ]
        for item in seed_projects:
            db.session.add(Project(**item))

    env_recovery_email = os.environ.get("ADMIN_RECOVERY_EMAIL", "").strip()
    if Admin.query.count() == 0:
        default_password = get_initial_admin_password()
        db.session.add(Admin(
            username=os.environ.get("ADMIN_USERNAME", "admin"),
            email=env_recovery_email,
            recovery_email=env_recovery_email,
            password_hash=generate_password_hash(default_password),
            role="owner",
            is_active=True,
        ))
    elif env_recovery_email:
        owner = Admin.query.filter_by(role="owner").order_by(Admin.id.asc()).first() or Admin.query.order_by(Admin.id.asc()).first()
        if owner and not owner.recovery_email:
            owner.recovery_email = env_recovery_email
            if not owner.email:
                owner.email = env_recovery_email

    db.session.commit()


with app.app_context():
    init_db()


