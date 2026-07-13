# Auto-split from app.py for readability. Executed by app.py in application globals.

# ─────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────
class Setting(db.Model):
    __tablename__ = "settings"
    key = db.Column(db.String(120), primary_key=True)
    value = db.Column(db.Text, nullable=False, default="")


class AboutContent(db.Model):
    __tablename__ = "about_content"
    id = db.Column(db.Integer, primary_key=True, default=1)
    short_description = db.Column(db.Text, default="")
    full_description = db.Column(db.Text, default="")
    mission = db.Column(db.Text, default="")
    vision = db.Column(db.Text, default="")
    core_values = db.Column(db.Text, default="")
    experience_summary = db.Column(db.Text, default="")
    years_experience = db.Column(db.String(60), default="")
    completed_projects = db.Column(db.String(60), default="")
    active_projects = db.Column(db.String(60), default="")
    team_members = db.Column(db.String(60), default="")


class Service(db.Model):
    __tablename__ = "services"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    image_path = db.Column(db.Text, nullable=False, default="")
    icon = db.Column(db.String(80), nullable=False, default="building")
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_published = db.Column(db.Boolean, nullable=False, default=True)
    visible_fields = db.Column(db.Text, nullable=False, default="")
    styles_json = db.Column(db.Text, nullable=False, default="{}")
    published_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Project(db.Model):
    __tablename__ = "projects"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(220), nullable=False)
    location = db.Column(db.String(220), nullable=False, default="")
    category = db.Column(db.String(160), nullable=False, default="")
    status = db.Column(db.String(80), nullable=False, default="Ongoing")
    year = db.Column(db.String(20), nullable=False, default="")
    client_type = db.Column(db.String(160), nullable=False, default="")
    site_area = db.Column(db.String(160), nullable=False, default="")
    duration = db.Column(db.String(160), nullable=False, default="")
    project_value = db.Column(db.String(160), nullable=False, default="")
    scope_of_work = db.Column(db.Text, nullable=False, default="")
    challenge = db.Column(db.Text, nullable=False, default="")
    solution = db.Column(db.Text, nullable=False, default="")
    outcome = db.Column(db.Text, nullable=False, default="")
    description = db.Column(db.Text, nullable=False, default="")
    image_path = db.Column(db.Text, nullable=False, default="")
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_featured = db.Column(db.Boolean, nullable=False, default=False)
    is_published = db.Column(db.Boolean, nullable=False, default=True)
    visible_fields = db.Column(db.Text, nullable=False, default="")
    styles_json = db.Column(db.Text, nullable=False, default="{}")
    published_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class GalleryItem(db.Model):
    __tablename__ = "gallery"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(220), nullable=False)
    caption = db.Column(db.Text, nullable=False, default="")
    image_path = db.Column(db.Text, nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_published = db.Column(db.Boolean, nullable=False, default=True)
    visible_fields = db.Column(db.Text, nullable=False, default="")
    styles_json = db.Column(db.Text, nullable=False, default="{}")
    published_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Enquiry(db.Model):
    __tablename__ = "enquiries"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    email = db.Column(db.String(220), nullable=False, default="")
    phone = db.Column(db.String(80), nullable=False, default="")
    project_type = db.Column(db.String(160), nullable=False, default="")
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Admin(db.Model):
    __tablename__ = "admins"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(220), nullable=False, default="")
    recovery_email = db.Column(db.String(220), nullable=False, default="")
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="owner")  # owner / editor / viewer
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("admins.id"), nullable=False)
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    requested_ip = db.Column(db.String(80), nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    admin = db.relationship("Admin")

    @property
    def is_valid(self):
        return self.used_at is None and self.expires_at >= datetime.utcnow()


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    admin_username = db.Column(db.String(80), nullable=False, default="system")
    action = db.Column(db.String(180), nullable=False)
    detail = db.Column(db.Text, nullable=False, default="")
    ip_address = db.Column(db.String(80), nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class DraftContent(db.Model):
    __tablename__ = "draft_content"
    id = db.Column(db.Integer, primary_key=True)
    draft_key = db.Column(db.String(160), unique=True, nullable=False)
    payload_json = db.Column(db.Text, nullable=False, default="{}")
    admin_username = db.Column(db.String(80), nullable=False, default="system")
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class ContentVersion(db.Model):
    __tablename__ = "content_versions"
    id = db.Column(db.Integer, primary_key=True)
    content_type = db.Column(db.String(80), nullable=False)
    object_id = db.Column(db.Integer, nullable=True)
    title = db.Column(db.String(240), nullable=False, default="")
    payload_json = db.Column(db.Text, nullable=False, default="{}")
    version_note = db.Column(db.String(240), nullable=False, default="")
    admin_username = db.Column(db.String(80), nullable=False, default="system")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class PageBlock(db.Model):
    __tablename__ = "page_blocks"
    id = db.Column(db.Integer, primary_key=True)
    page = db.Column(db.String(80), nullable=False, default="home")
    block_type = db.Column(db.String(80), nullable=False, default="text")
    title = db.Column(db.String(240), nullable=False, default="")
    body = db.Column(db.Text, nullable=False, default="")
    image_path = db.Column(db.Text, nullable=False, default="")
    button_text = db.Column(db.String(160), nullable=False, default="")
    button_url = db.Column(db.Text, nullable=False, default="")
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_published = db.Column(db.Boolean, nullable=False, default=False)
    styles_json = db.Column(db.Text, nullable=False, default="{}")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


