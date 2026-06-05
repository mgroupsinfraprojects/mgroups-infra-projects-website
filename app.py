import os
import sqlite3
from functools import wraps
from pathlib import Path
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    session, g, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
DB_PATH = INSTANCE_DIR / "website.sqlite3"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB per upload

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or "M-Groups-Infra-Projects-2026-VeryLongRandomSecretKey-ChangeThisNow-987654321@822014141400001"
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)

INSTANCE_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def execute(sql, params=()):
    db = get_db()
    cur = db.execute(sql, params)
    db.commit()
    return cur


def query_all(sql, params=()):
    return get_db().execute(sql, params).fetchall()


def query_one(sql, params=()):
    return get_db().execute(sql, params).fetchone()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file_storage, prefix="upload"):
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_file(file_storage.filename):
        raise ValueError("Only PNG, JPG, JPEG, WEBP, and GIF image files are allowed.")
    original = secure_filename(file_storage.filename)
    ext = original.rsplit(".", 1)[1].lower()
    stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    filename = f"{prefix}_{stamp}.{ext}"
    target = UPLOAD_DIR / filename
    file_storage.save(target)
    return f"uploads/{filename}"


def settings_dict():
    rows = query_all("SELECT key, value FROM settings")
    return {row["key"]: row["value"] for row in rows}


@app.context_processor
def inject_globals():
    try:
        return {"site": settings_dict()}
    except Exception:
        return {"site": {}}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            flash("Admin login required.", "warning")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS about_content (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            short_description TEXT NOT NULL DEFAULT '',
            full_description TEXT NOT NULL DEFAULT '',
            mission TEXT NOT NULL DEFAULT '',
            vision TEXT NOT NULL DEFAULT '',
            core_values TEXT NOT NULL DEFAULT '',
            experience_summary TEXT NOT NULL DEFAULT '',
            years_experience TEXT NOT NULL DEFAULT '5+',
            completed_projects TEXT NOT NULL DEFAULT '25+',
            active_projects TEXT NOT NULL DEFAULT '4+',
            team_members TEXT NOT NULL DEFAULT '30+'
        );

        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            image_path TEXT NOT NULL DEFAULT '',
            icon TEXT NOT NULL DEFAULT 'building',
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            location TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Ongoing',
            year TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            image_path TEXT NOT NULL DEFAULT '',
            is_featured INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS gallery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            caption TEXT NOT NULL DEFAULT '',
            image_path TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS enquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL DEFAULT '',
            phone TEXT NOT NULL DEFAULT '',
            message TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    defaults = {
        "company_name": "M-GROUPS INFRA PROJECTS",
        "tagline": "Building Reliable Infrastructure for a Stronger Future",
        "hero_title": "Professional Infrastructure & Civil Project Execution",
        "hero_subtitle": "We deliver civil construction, infrastructure development, project coordination, and site execution services with a focus on quality, safety, and timely delivery.",
        "short_description": "Reliable civil and infrastructure project services for residential, commercial, and industrial work.",
        "phone": "+91 00000 00000",
        "whatsapp": "+91 00000 00000",
        "email": "info@mgroupsinfra.com",
        "address": "Tamil Nadu, India",
        "map_embed": "",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "logo_path": "uploads/m-groups-logo.jpeg",
        "primary_color": "#0b4f93",
        "secondary_color": "#0f7fc8",
    }
    for key, value in defaults.items():
        db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))

    db.execute(
        """
        INSERT OR IGNORE INTO about_content
        (id, short_description, full_description, mission, vision, core_values, experience_summary)
        VALUES (1, ?, ?, ?, ?, ?, ?)
        """,
        (
            "M-GROUPS INFRA PROJECTS is an infrastructure and civil works company focused on dependable execution, quality workmanship, and practical project delivery.",
            "M-GROUPS INFRA PROJECTS provides civil construction and infrastructure project services across residential, commercial, and industrial requirements. The company focuses on systematic planning, site coordination, material control, safety practices, and timely execution. This content can be edited from the admin dashboard.",
            "To deliver reliable infrastructure and civil works with disciplined planning, transparent execution, and consistent quality.",
            "To become a trusted infrastructure project partner known for dependable delivery, safety, and long-term client relationships.",
            "Quality Work\nSafety First\nTimely Delivery\nTransparent Communication\nResponsible Site Management",
            "Our experience covers civil construction, site execution, renovation, maintenance, and infrastructure coordination. Add your real work history from the admin panel.",
        ),
    )

    if db.execute("SELECT COUNT(*) AS n FROM services").fetchone()["n"] == 0:
        services = [
            ("Civil Construction", "Residential, commercial, and structural civil works with disciplined site execution.", "building", 1),
            ("Infrastructure Projects", "Road, drainage, utility, and infrastructure development support for private and public works.", "road", 2),
            ("Project Management", "Planning, supervision, labour coordination, material tracking, and progress monitoring.", "clipboard", 3),
            ("Renovation & Maintenance", "Repair, renovation, improvement, and maintenance works for existing buildings and sites.", "tools", 4),
        ]
        db.executemany(
            "INSERT INTO services (title, description, icon, sort_order) VALUES (?, ?, ?, ?)",
            services,
        )

    if db.execute("SELECT COUNT(*) AS n FROM projects").fetchone()["n"] == 0:
        projects = [
            ("Residential Civil Work", "Tamil Nadu", "Civil Construction", "Completed", "2026", "Sample completed project. Replace this with your real project details from admin.", 1),
            ("Commercial Site Development", "Tamil Nadu", "Infrastructure", "Ongoing", "2026", "Sample ongoing project. Add actual work photos and status from admin.", 1),
        ]
        db.executemany(
            "INSERT INTO projects (title, location, category, status, year, description, is_featured) VALUES (?, ?, ?, ?, ?, ?, ?)",
            projects,
        )

    if db.execute("SELECT COUNT(*) AS n FROM admins").fetchone()["n"] == 0:
        db.execute(
            "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
            ("admin", generate_password_hash("ChangeMe@123")),
        )
    db.commit()


@app.before_request
def before_request():
    init_db()


# ---------------- Public Website ----------------

@app.route("/")
def home():
    about = query_one("SELECT * FROM about_content WHERE id = 1")
    services = query_all("SELECT * FROM services WHERE is_active = 1 ORDER BY sort_order, id LIMIT 6")
    projects = query_all("SELECT * FROM projects ORDER BY is_featured DESC, id DESC LIMIT 6")
    gallery_items = query_all("SELECT * FROM gallery ORDER BY sort_order, id DESC LIMIT 6")
    return render_template("home.html", about=about, services=services, projects=projects, gallery_items=gallery_items)


@app.route("/about")
def about():
    about = query_one("SELECT * FROM about_content WHERE id = 1")
    return render_template("about.html", about=about)


@app.route("/services")
def services():
    services = query_all("SELECT * FROM services WHERE is_active = 1 ORDER BY sort_order, id")
    return render_template("services.html", services=services)


@app.route("/projects")
def projects():
    rows = query_all("SELECT * FROM projects ORDER BY id DESC")
    return render_template("projects.html", projects=rows)


@app.route("/projects/<int:project_id>")
def project_detail(project_id):
    project = query_one("SELECT * FROM projects WHERE id = ?", (project_id,))
    if not project:
        abort(404)
    return render_template("project_detail.html", project=project)


@app.route("/gallery")
def gallery():
    items = query_all("SELECT * FROM gallery ORDER BY sort_order, id DESC")
    return render_template("gallery.html", items=items)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        message = request.form.get("message", "").strip()
        if not name or not message:
            flash("Name and message are required.", "danger")
        else:
            execute(
                "INSERT INTO enquiries (name, email, phone, message) VALUES (?, ?, ?, ?)",
                (name, email, phone, message),
            )
            flash("Your enquiry has been submitted.", "success")
            return redirect(url_for("contact"))
    return render_template("contact.html")


# ---------------- Admin ----------------

@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_id"):
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = query_one("SELECT * FROM admins WHERE username = ?", (username,))
        if admin and check_password_hash(admin["password_hash"], password):
            session.clear()
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]
            flash("Logged in successfully.", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("admin/login.html")


@app.route("/admin/logout")
@login_required
def admin_logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("admin_login"))


@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    counts = {
        "services": query_one("SELECT COUNT(*) AS n FROM services")["n"],
        "projects": query_one("SELECT COUNT(*) AS n FROM projects")["n"],
        "gallery": query_one("SELECT COUNT(*) AS n FROM gallery")["n"],
        "unread": query_one("SELECT COUNT(*) AS n FROM enquiries WHERE is_read = 0")["n"],
    }
    enquiries = query_all("SELECT * FROM enquiries ORDER BY id DESC LIMIT 5")
    return render_template("admin/dashboard.html", counts=counts, enquiries=enquiries)


@app.route("/admin/settings", methods=["GET", "POST"])
@login_required
def admin_settings():
    editable_keys = [
        "company_name", "tagline", "hero_title", "hero_subtitle", "short_description",
        "phone", "whatsapp", "email", "address", "map_embed", "facebook",
        "instagram", "linkedin", "primary_color", "secondary_color"
    ]
    if request.method == "POST":
        for key in editable_keys:
            value = request.form.get(key, "").strip()
            execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))
        try:
            logo_path = save_upload(request.files.get("logo"), "logo")
            if logo_path:
                execute("UPDATE settings SET value = ? WHERE key = 'logo_path'", (logo_path,))
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("admin_settings"))
        flash("Website settings updated.", "success")
        return redirect(url_for("admin_settings"))
    return render_template("admin/settings.html")


@app.route("/admin/about", methods=["GET", "POST"])
@login_required
def admin_about():
    if request.method == "POST":
        fields = ["short_description", "full_description", "mission", "vision", "core_values", "experience_summary", "years_experience", "completed_projects", "active_projects", "team_members"]
        values = [request.form.get(field, "").strip() for field in fields]
        execute(
            """
            UPDATE about_content SET
            short_description=?, full_description=?, mission=?, vision=?, core_values=?, experience_summary=?,
            years_experience=?, completed_projects=?, active_projects=?, team_members=?
            WHERE id=1
            """,
            values,
        )
        flash("About and experience content updated.", "success")
        return redirect(url_for("admin_about"))
    about = query_one("SELECT * FROM about_content WHERE id = 1")
    return render_template("admin/about.html", about=about)


@app.route("/admin/services")
@login_required
def admin_services():
    rows = query_all("SELECT * FROM services ORDER BY sort_order, id")
    return render_template("admin/services.html", services=rows)


@app.route("/admin/services/new", methods=["GET", "POST"])
@login_required
def admin_service_new():
    return service_form()


@app.route("/admin/services/<int:service_id>/edit", methods=["GET", "POST"])
@login_required
def admin_service_edit(service_id):
    service = query_one("SELECT * FROM services WHERE id = ?", (service_id,))
    if not service:
        abort(404)
    return service_form(service)


def service_form(service=None):
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        icon = request.form.get("icon", "building").strip()
        sort_order = int(request.form.get("sort_order", "0") or 0)
        is_active = 1 if request.form.get("is_active") == "on" else 0
        if not title or not description:
            flash("Title and description are required.", "danger")
            return redirect(request.url)
        try:
            image_path = save_upload(request.files.get("image"), "service")
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(request.url)
        if service:
            if image_path:
                execute("UPDATE services SET title=?, description=?, icon=?, sort_order=?, is_active=?, image_path=? WHERE id=?", (title, description, icon, sort_order, is_active, image_path, service["id"]))
            else:
                execute("UPDATE services SET title=?, description=?, icon=?, sort_order=?, is_active=? WHERE id=?", (title, description, icon, sort_order, is_active, service["id"]))
            flash("Service updated.", "success")
        else:
            execute("INSERT INTO services (title, description, icon, sort_order, is_active, image_path) VALUES (?, ?, ?, ?, ?, ?)", (title, description, icon, sort_order, is_active, image_path or ""))
            flash("Service added.", "success")
        return redirect(url_for("admin_services"))
    return render_template("admin/service_form.html", service=service)


@app.route("/admin/services/<int:service_id>/delete", methods=["POST"])
@login_required
def admin_service_delete(service_id):
    execute("DELETE FROM services WHERE id = ?", (service_id,))
    flash("Service deleted.", "info")
    return redirect(url_for("admin_services"))


@app.route("/admin/projects")
@login_required
def admin_projects():
    rows = query_all("SELECT * FROM projects ORDER BY id DESC")
    return render_template("admin/projects.html", projects=rows)


@app.route("/admin/projects/new", methods=["GET", "POST"])
@login_required
def admin_project_new():
    return project_form()


@app.route("/admin/projects/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
def admin_project_edit(project_id):
    project = query_one("SELECT * FROM projects WHERE id = ?", (project_id,))
    if not project:
        abort(404)
    return project_form(project)


def project_form(project=None):
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        location = request.form.get("location", "").strip()
        category = request.form.get("category", "").strip()
        status = request.form.get("status", "Ongoing").strip()
        year = request.form.get("year", "").strip()
        description = request.form.get("description", "").strip()
        is_featured = 1 if request.form.get("is_featured") == "on" else 0
        if not title:
            flash("Project title is required.", "danger")
            return redirect(request.url)
        try:
            image_path = save_upload(request.files.get("image"), "project")
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(request.url)
        if project:
            if image_path:
                execute("UPDATE projects SET title=?, location=?, category=?, status=?, year=?, description=?, is_featured=?, image_path=? WHERE id=?", (title, location, category, status, year, description, is_featured, image_path, project["id"]))
            else:
                execute("UPDATE projects SET title=?, location=?, category=?, status=?, year=?, description=?, is_featured=? WHERE id=?", (title, location, category, status, year, description, is_featured, project["id"]))
            flash("Project updated.", "success")
        else:
            execute("INSERT INTO projects (title, location, category, status, year, description, is_featured, image_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (title, location, category, status, year, description, is_featured, image_path or ""))
            flash("Project added.", "success")
        return redirect(url_for("admin_projects"))
    return render_template("admin/project_form.html", project=project)


@app.route("/admin/projects/<int:project_id>/delete", methods=["POST"])
@login_required
def admin_project_delete(project_id):
    execute("DELETE FROM projects WHERE id = ?", (project_id,))
    flash("Project deleted.", "info")
    return redirect(url_for("admin_projects"))


@app.route("/admin/gallery", methods=["GET", "POST"])
@login_required
def admin_gallery():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        caption = request.form.get("caption", "").strip()
        sort_order = int(request.form.get("sort_order", "0") or 0)
        try:
            image_path = save_upload(request.files.get("image"), "gallery")
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("admin_gallery"))
        if not title or not image_path:
            flash("Title and image are required.", "danger")
        else:
            execute("INSERT INTO gallery (title, caption, image_path, sort_order) VALUES (?, ?, ?, ?)", (title, caption, image_path, sort_order))
            flash("Gallery image added.", "success")
        return redirect(url_for("admin_gallery"))
    items = query_all("SELECT * FROM gallery ORDER BY sort_order, id DESC")
    return render_template("admin/gallery.html", items=items)


@app.route("/admin/gallery/<int:item_id>/delete", methods=["POST"])
@login_required
def admin_gallery_delete(item_id):
    execute("DELETE FROM gallery WHERE id = ?", (item_id,))
    flash("Gallery item deleted.", "info")
    return redirect(url_for("admin_gallery"))


@app.route("/admin/enquiries")
@login_required
def admin_enquiries():
    rows = query_all("SELECT * FROM enquiries ORDER BY id DESC")
    execute("UPDATE enquiries SET is_read = 1 WHERE is_read = 0")
    return render_template("admin/enquiries.html", enquiries=rows)


@app.route("/admin/enquiries/<int:enquiry_id>/delete", methods=["POST"])
@login_required
def admin_enquiry_delete(enquiry_id):
    execute("DELETE FROM enquiries WHERE id = ?", (enquiry_id,))
    flash("Enquiry deleted.", "info")
    return redirect(url_for("admin_enquiries"))


@app.route("/admin/password", methods=["GET", "POST"])
@login_required
def admin_password():
    if request.method == "POST":
        current = request.form.get("current_password", "")
        new = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")
        admin = query_one("SELECT * FROM admins WHERE id = ?", (session["admin_id"],))
        if not check_password_hash(admin["password_hash"], current):
            flash("Current password is incorrect.", "danger")
        elif len(new) < 8:
            flash("New password must be at least 8 characters.", "danger")
        elif new != confirm:
            flash("New password and confirmation do not match.", "danger")
        else:
            execute("UPDATE admins SET password_hash = ? WHERE id = ?", (generate_password_hash(new), session["admin_id"]))
            flash("Password changed.", "success")
            return redirect(url_for("admin_dashboard"))
    return render_template("admin/change_password.html")


if __name__ == "__main__":
    app.run(debug=True)
