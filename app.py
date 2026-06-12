import csv
import io
import json
import os
import secrets
import smtplib
import ssl
import uuid
import re
from datetime import datetime
from functools import wraps
from pathlib import Path
from email.message import EmailMessage
from types import SimpleNamespace

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
INSTANCE_DIR = BASE_DIR / "instance"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
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

if cloudinary and os.environ.get("CLOUDINARY_URL"):
    cloudinary.config(secure=True)

if Limiter:
    limiter = Limiter(get_remote_address, app=app, default_limits=["300 per hour"], storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"))
else:
    limiter = None


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
    years_experience = db.Column(db.String(60), default="Add actual")
    completed_projects = db.Column(db.String(60), default="Add actual")
    active_projects = db.Column(db.String(60), default="Add actual")
    team_members = db.Column(db.String(60), default="Add actual")


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
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="owner")  # owner / editor / viewer
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


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


# ─────────────────────────────────────────────────────────────
# Defaults
# ─────────────────────────────────────────────────────────────
DEFAULT_SETTINGS = {
    "company_name": "M-GROUPS INFRA PROJECTS",
    "registered_name": "MGROUPS INFRA PROJECTS",
    "tagline": "Registered Civil Engineering & Infrastructure Services Enterprise",
    "hero_title": "Document-Backed Civil & Infrastructure Project Execution",
    "hero_subtitle": "Registered in Tamil Nadu with Udyam and GST credentials, M-GROUPS INFRA PROJECTS supports civil engineering, municipal infrastructure, site execution, and project coordination works.",
    "short_description": "Tamil Nadu-based registered infrastructure and civil works enterprise serving Kanyakumari, Nagercoil, and wider Tamil Nadu project requirements.",
    "phone": "",
    "whatsapp": "",
    "public_phone_label": "Phone number hidden for privacy. Please use the contact form or WhatsApp enquiry button.",
    "email": "mgroupsinfraprojects@gmail.com",
    "address": "2/5-1A, North Street, Erachakulam, Nagercoil, Kanniyakumari, Tamil Nadu - 629901",
    "map_embed": "",
    "facebook": "",
    "instagram": "",
    "linkedin": "",
    "logo_path": "uploads/m-groups-logo.jpeg",
    "seo_title": "M-GROUPS INFRA PROJECTS | Registered Civil & Infrastructure Works in Tamil Nadu",
    "seo_description": "M-GROUPS INFRA PROJECTS is a registered Tamil Nadu civil and infrastructure services enterprise with Udyam, GST, experience certificates, contractor registration documents, and project documentation.",
    "og_image": "uploads/m-groups-logo.jpeg",
    "business_area": "Kanyakumari, Nagercoil and Tamil Nadu",
    "service_areas": "Kanyakumari\nNagercoil\nKanniyakumari District\nTamil Nadu\nDindigul\nTirunelveli\nThoothukudi",
    "homepage_section_order": "trust_strip\ncredentials\nservice_areas\nabout\nservices\nstats\nprojects\nwhy\ncta",
    "google_business_url": "",
    "notification_email": "mgroupsinfraprojects@gmail.com",
    "smtp_from_name": "M-GROUPS Website",
    "udyam_registration": "UDYAM-TN-09-0060986",
    "gstin": "33DDOPK4939J1Z2",
    "enterprise_type": "Micro Enterprise",
    "business_commencement": "02/12/2020",
    "major_activity": "Services; civil engineering and infrastructure-related activities",
    "credential_note": "Udyam, GST, experience certificate and contractor registration documents are available for verification. Sensitive personal, tax, invoice and legal documents are not displayed publicly.",
    "experience_documents": "5+",
    "contractor_registrations": "2",

    # Visibility controls. Admin can decide what appears publicly.
    "show_phone_public": "0",
    "show_whatsapp_public": "0",
    "show_email_public": "1",
    "show_address_public": "1",
    "show_registered_name_public": "1",
    "show_udyam_public": "1",
    "show_gstin_public": "1",
    "show_enterprise_type_public": "1",
    "show_business_commencement_public": "0",
    "show_major_activity_public": "1",
    "show_credentials_section": "1",
    "show_trust_strip": "1",
    "show_service_areas_section": "1",
    "show_about_section": "1",
    "show_services_section": "1",
    "show_stats_section": "0",
    "show_projects_section": "1",
    "show_why_section": "1",
    "show_cta_section": "1",
    "show_gallery_nav": "1",
    "show_service_area_nav": "1",
    "show_contact_nav": "1",
    "show_footer_contact": "1",
    "show_footer_credentials": "1",
    "show_whatsapp_float": "0",
    "show_hero_logo_panel": "1",
    "show_hero_metrics": "0",
    "show_project_placeholder_images": "0",

    # Editable labels and section text.
    "hero_badge_label": "Civil & Infrastructure Project Execution",
    "hero_cta_primary": "Request Consultation",
    "hero_cta_secondary": "View Projects",
    "trust_item_1": "Udyam Registered",
    "trust_item_2": "GST Registered",
    "trust_item_3": "Experience Documents",
    "trust_item_4": "Contractor Records",
    "trust_item_5": "Site Execution",
    "credentials_eyebrow": "Verified Business Details",
    "credentials_title": "Registration-backed company profile.",
    "credentials_link_text": "View credentials →",
    "service_areas_eyebrow": "Service Areas",
    "service_areas_title": "Local service pages for better client discovery.",
    "service_areas_all_label": "All Areas →",
    "about_eyebrow": "About Company",
    "about_title": "Reliable execution for civil and infrastructure works.",
    "about_link_text": "Read company profile →",
    "services_eyebrow": "Services",
    "services_title": "What We Do",
    "services_link_text": "All services →",
    "projects_eyebrow": "Works",
    "projects_title": "Recent Projects",
    "projects_link_text": "View all →",
    "image_pending_text": "Image will be added soon",
    "stats_years_label": "Years Since Business Commencement",
    "stats_experience_label": "Experience / Work Records",
    "stats_contractor_label": "Contractor Registration Records",
    "stats_gst_label": "Registered Enterprise",
    "why_eyebrow": "Why Choose Us",
    "why_title": "Disciplined site work, clear coordination, dependable delivery.",
    "why_card_1_title": "Quality Workmanship",
    "why_card_1_text": "Structured execution with supervision, material checks, and finishing discipline.",
    "why_card_2_title": "Project Coordination",
    "why_card_2_text": "Labour, vendors, materials, timelines, and site progress managed from one workflow.",
    "why_card_3_title": "Safety First",
    "why_card_3_text": "Better site behaviour, controlled work areas, and responsible execution practices.",
    "why_card_4_title": "Transparent Updates",
    "why_card_4_text": "Clients receive practical status updates and requirement clarification before delay becomes a problem.",
    "cta_title": "Need civil or infrastructure project support?",
    "cta_text": "Send your work details. The team can review the requirement and contact you.",
    "cta_button_text": "Contact Now",
    "contact_page_title": "Contact Us",
    "contact_page_intro": "Send your project requirement with location, scope, and timeline. The enquiry will be stored in admin and can trigger email notification when SMTP is configured.",
    "contact_card_title": "Business Contact",
    "contact_form_title": "Send Enquiry",
    "footer_company_heading": "Company",
    "footer_contact_heading": "Contact",

    # Appearance controls.
    "heading_font": "Montserrat",
    "body_font": "Manrope",
    "nav_font": "Manrope",
    "primary_color": "#0D1F35",
    "secondary_color": "#C4822A",
    "accent_color": "#E8A046",
    "header_bg_color": "#0D1F35",
    "footer_bg_color": "#07121F",
    "body_bg_color": "#FFFFFF",
    "soft_bg_color": "#F5F8FC",
    "card_bg_color": "#FFFFFF",
    "text_color": "#1C2E3F",
    "muted_text_color": "#5A7089",
    "line_color": "#D8E6F0",
    "button_text_color": "#FFFFFF",
    "container_width": "1160px",
    "card_radius": "20px",
    "button_radius": "11px",
    "hero_title_size": "clamp(2.6rem,5.2vw,4.8rem)",
    "section_title_size": "clamp(1.8rem,3vw,2.6rem)",
    "body_text_size": "16px",
    "custom_css": "",
    "privacy_policy": "This website collects enquiry details submitted through the contact form only for business communication. Sensitive registration, GST, tax, invoice and legal documents are used only for internal verification and are not published in full on the public website.",
    "terms_text": "Information on this website is based on available company registration and project documentation. Project pricing, timelines, and commitments are confirmed only through formal quotation, work order, invoice, or agreement.",
}
DEFAULT_SERVICES = [
    ("Civil Engineering Works", "Civil engineering and infrastructure-related works supported by registered Udyam activity classifications and project documentation.", "building", 1),
    ("Municipal Infrastructure Support", "Execution support for municipal infrastructure works including documented overhead tank-related construction activity in Nagercoil Municipal Corporation.", "road", 2),
    ("Waterways / Civil Infrastructure", "Civil engineering services aligned with registered activity categories covering waterways, harbours, river works, and other civil engineering projects.", "water", 3),
    ("Site Execution & Coordination", "Labour coordination, material movement, site supervision, progress tracking, and practical project execution support.", "clipboard", 4),
    ("Contractor & Compliance Documentation", "Support for maintaining contractor registration, experience certificates, invoice records, GST and project documentation for tender/business verification.", "file", 5),
    ("Renovation & Maintenance Works", "Repair, improvement, and maintenance support for civil structures, sites, and related infrastructure requirements.", "tools", 6),
]


APPEARANCE_FIELDS = [
    "heading_font", "body_font", "nav_font", "primary_color", "secondary_color", "accent_color",
    "header_bg_color", "footer_bg_color", "body_bg_color", "soft_bg_color", "card_bg_color",
    "text_color", "muted_text_color", "line_color", "button_text_color", "container_width",
    "card_radius", "button_radius", "hero_title_size", "section_title_size", "body_text_size", "custom_css",
    "hero_badge_label", "hero_cta_primary", "hero_cta_secondary",
    "trust_item_1", "trust_item_2", "trust_item_3", "trust_item_4", "trust_item_5",
    "credentials_eyebrow", "credentials_title", "credentials_link_text",
    "service_areas_eyebrow", "service_areas_title", "service_areas_all_label",
    "about_eyebrow", "about_title", "about_link_text",
    "services_eyebrow", "services_title", "services_link_text",
    "projects_eyebrow", "projects_title", "projects_link_text", "image_pending_text",
    "stats_years_label", "stats_experience_label", "stats_contractor_label", "stats_gst_label",
    "why_eyebrow", "why_title", "why_card_1_title", "why_card_1_text", "why_card_2_title", "why_card_2_text",
    "why_card_3_title", "why_card_3_text", "why_card_4_title", "why_card_4_text",
    "cta_title", "cta_text", "cta_button_text", "contact_page_title", "contact_page_intro", "contact_card_title", "contact_form_title",
    "footer_company_heading", "footer_contact_heading",
]


APPEARANCE_STYLE_LABELS = [(field, field.replace("_", " ").title(), True) for field in APPEARANCE_FIELDS]

VISIBILITY_FIELDS = [
    "show_phone_public", "show_whatsapp_public", "show_email_public", "show_address_public",
    "show_registered_name_public", "show_udyam_public", "show_gstin_public", "show_enterprise_type_public",
    "show_business_commencement_public", "show_major_activity_public", "show_credentials_section", "show_trust_strip",
    "show_service_areas_section", "show_about_section", "show_services_section", "show_stats_section",
    "show_projects_section", "show_why_section", "show_cta_section", "show_gallery_nav", "show_service_area_nav",
    "show_contact_nav", "show_footer_contact", "show_footer_credentials", "show_whatsapp_float", "show_hero_logo_panel",
    "show_hero_metrics", "show_project_placeholder_images",
]


# Field-level public visibility controls.
# These are deliberately separate from content values: admin can store a value privately and decide whether it is visible publicly.
SETTINGS_FIELD_LABELS = [
    ("company_name", "Company Name", True),
    ("tagline", "Tagline", True),
    ("hero_title", "Hero Title", True),
    ("hero_subtitle", "Hero Subtitle", True),
    ("short_description", "Short Description", True),
    ("phone", "Phone", False),
    ("whatsapp", "WhatsApp", False),
    ("public_phone_label", "Phone Privacy Message", True),
    ("email", "Email", True),
    ("notification_email", "Notification Email", False),
    ("address", "Address", True),
    ("business_area", "Business Service Area", True),
    ("service_areas", "Service Areas", True),
    ("registered_name", "Registered Name", True),
    ("enterprise_type", "Enterprise Type", True),
    ("udyam_registration", "Udyam Registration", True),
    ("gstin", "GSTIN", True),
    ("business_commencement", "Business Commencement", False),
    ("experience_documents", "Experience Documents Count", True),
    ("contractor_registrations", "Contractor Registrations Count", True),
    ("major_activity", "Major Activity", True),
    ("credential_note", "Credential Note", True),
    ("seo_title", "SEO Title", True),
    ("seo_description", "SEO Description", True),
    ("google_business_url", "Google Business Profile URL", True),
    ("map_embed", "Google Map Embed", True),
    ("privacy_policy", "Privacy Policy", True),
    ("terms_text", "Terms Text", True),
    ("facebook", "Facebook", True),
    ("instagram", "Instagram", True),
    ("linkedin", "LinkedIn", True),
    ("logo_path", "Logo", True),
]

ABOUT_FIELD_LABELS = [
    ("short_description", "Short Description", True),
    ("full_description", "Full Company Description", True),
    ("mission", "Mission", True),
    ("vision", "Vision", True),
    ("core_values", "Core Values", True),
    ("experience_summary", "Experience Summary", True),
    ("years_experience", "Years Experience", False),
    ("completed_projects", "Completed Projects", False),
    ("active_projects", "Active Projects", False),
    ("team_members", "Team Members", False),
]

SERVICE_FIELD_LABELS = [
    ("title", "Service Title", True),
    ("icon", "Icon / Category Label", True),
    ("description", "Description", True),
    ("image_path", "Image", True),
]

PROJECT_FIELD_LABELS = [
    ("title", "Project Title", True),
    ("location", "Location", True),
    ("category", "Category", True),
    ("status", "Status", True),
    ("year", "Year", True),
    ("client_type", "Client Type", True),
    ("site_area", "Site / Area", True),
    ("duration", "Duration", True),
    ("project_value", "Project Value", False),
    ("description", "Short Overview", True),
    ("image_path", "Main Image", True),
    ("scope_of_work", "Scope of Work", True),
    ("challenge", "Challenge", True),
    ("solution", "Execution Approach", True),
    ("outcome", "Outcome", True),
]

GALLERY_FIELD_LABELS = [
    ("title", "Gallery Title", True),
    ("caption", "Caption", True),
    ("image_path", "Image", True),
]

FIELD_VISIBILITY_GROUPS = {
    "settings": SETTINGS_FIELD_LABELS,
    "about": ABOUT_FIELD_LABELS,
    "service": SERVICE_FIELD_LABELS,
    "project": PROJECT_FIELD_LABELS,
    "gallery": GALLERY_FIELD_LABELS,
}

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

    if cloudinary and os.environ.get("CLOUDINARY_URL"):
        result = cloudinary.uploader.upload(
            file_storage,
            folder=os.environ.get("CLOUDINARY_FOLDER", "mgroups"),
            public_id=filename.rsplit(".", 1)[0],
            overwrite=False,
            resource_type="image",
        )
        return result.get("secure_url") or result.get("url")

    target = UPLOAD_DIR / filename
    file_storage.save(target)
    compress_image(target)
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


def send_enquiry_email(enquiry):
    site = settings_dict()
    to_addr = os.environ.get("SMTP_TO") or site.get("notification_email") or site.get("email")
    host = os.environ.get("SMTP_HOST")
    username = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")
    if not (to_addr and host and username and password):
        return False
    port = int(os.environ.get("SMTP_PORT", "587"))
    sender = os.environ.get("SMTP_FROM") or username
    use_tls = os.environ.get("SMTP_USE_TLS", "1") == "1"
    msg = EmailMessage()
    msg["Subject"] = f"New website enquiry - {enquiry.name}"
    msg["From"] = sender
    msg["To"] = to_addr
    reply_to = enquiry.email or sender
    msg["Reply-To"] = reply_to
    msg.set_content(f"""New enquiry from M-GROUPS website

Name: {enquiry.name}
Phone: {enquiry.phone}
Email: {enquiry.email}
Project Type: {enquiry.project_type}

Message:
{enquiry.message}

Submitted: {enquiry.created_at}
""")
    context = ssl.create_default_context()
    if use_tls:
        with smtplib.SMTP(host, port, timeout=12) as smtp:
            smtp.starttls(context=context)
            smtp.login(username, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP_SSL(host, port, context=context, timeout=12) as smtp:
            smtp.login(username, password)
            smtp.send_message(msg)
    return True


def admin_username():
    if session.get("admin_id"):
        admin = Admin.query.get(session.get("admin_id"))
        return admin.username if admin else "admin"
    return "system"


def current_admin():
    try:
        if not session.get("admin_id"):
            return None
        return Admin.query.get(session.get("admin_id"))
    except Exception:
        return None


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
    ("page_builder", "Visual Page Builder", "Custom WYSIWYG blocks and inline styled content"),
    ("ordering", "Drag & Drop Ordering", "Homepage, service, project, gallery and block ordering"),
    ("media", "Media Library", "Upload and crop local images"),
    ("restore", "Restore Backup", "Restore JSON content backups"),
    ("versions", "Version History", "Restore or compare old versions"),
    ("enquiries", "Enquiries", "Read/export enquiry records"),
]

DEFAULT_EDITOR_PERMISSION = {
    "settings": True, "appearance": True, "about": True, "services": True,
    "projects": True, "gallery": True, "page_builder": True, "ordering": True,
    "media": True, "enquiries": True, "restore": False, "versions": False,
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
        if not session.get("admin_id"):
            flash("Admin login required.", "warning")
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


# ─────────────────────────────────────────────────────────────
# Per-field typography/style controls
# ─────────────────────────────────────────────────────────────
STYLE_PROPS = ["font", "size", "weight", "italic", "uppercase", "color", "align", "letter_spacing", "line_height"]
STYLE_DEFAULTS = {"font": "", "size": "", "weight": "", "italic": "0", "uppercase": "0", "color": "", "align": "", "letter_spacing": "", "line_height": ""}


def style_key(section, field, prop):
    return f"style_{section}_{field}_{prop}"


def collect_field_styles(section, fields):
    payload = {}
    for field, _label, _default in fields:
        for prop in STYLE_PROPS:
            payload[style_key(section, field, prop)] = request.form.get(style_key(section, field, prop), STYLE_DEFAULTS.get(prop, ""))
    return payload


def apply_field_styles(payload):
    for key, value in payload.items():
        if key.startswith("style_"):
            set_setting(key, value or "")


def css_dimension(value, default_unit="px"):
    """Accept admin-friendly values. If user types 22, convert to 22px so font-size works."""
    v = (value or "").strip()
    if not v:
        return ""
    if re.fullmatch(r"-?\d+(\.\d+)?", v):
        return f"{v}{default_unit}"
    return v


def css_font_family(value):
    v = (value or "").strip()
    if not v:
        return ""
    # Quote custom Google font names with spaces. Keep CSS fallback after it.
    safe = v.replace("'", "").replace('"', "")
    return f"'{safe}', system-ui, sans-serif"


def style_inline(section, field):
    try:
        site = settings_dict()
    except Exception:
        site = {}
    parts = []
    font = site.get(style_key(section, field, "font"), "").strip()
    size = css_dimension(site.get(style_key(section, field, "size"), ""))
    weight = site.get(style_key(section, field, "weight"), "").strip()
    color = site.get(style_key(section, field, "color"), "").strip()
    align = site.get(style_key(section, field, "align"), "").strip()
    letter = css_dimension(site.get(style_key(section, field, "letter_spacing"), ""), "px")
    lineh = site.get(style_key(section, field, "line_height"), "").strip()
    if font: parts.append(f"font-family:{css_font_family(font)} !important")
    if size: parts.append(f"font-size:{size} !important")
    if weight: parts.append(f"font-weight:{weight} !important")
    if color: parts.append(f"color:{color} !important")
    if align: parts.append(f"text-align:{align} !important")
    if letter: parts.append(f"letter-spacing:{letter} !important")
    if lineh: parts.append(f"line-height:{lineh} !important")
    if flag_value(site.get(style_key(section, field, "italic")), False): parts.append("font-style:italic !important")
    if flag_value(site.get(style_key(section, field, "uppercase")), False): parts.append("text-transform:uppercase !important")
    return ";".join(parts)


def item_style_key(section, field, prop):
    return f"style_{field}_{prop}"


def collect_item_styles(section):
    data = {}
    for field, _label, _default in FIELD_VISIBILITY_GROUPS.get(section, []):
        sub = {}
        for prop in STYLE_PROPS:
            value = request.form.get(item_style_key(section, field, prop), STYLE_DEFAULTS.get(prop, ""))
            if value:
                sub[prop] = value
        if sub:
            data[field] = sub
    return json.dumps(data, ensure_ascii=False)


def item_style_dict(obj, field):
    raw = getattr(obj, "styles_json", "") if obj is not None else ""
    try:
        styles = json.loads(raw or "{}")
        return styles.get(field, {}) if isinstance(styles, dict) else {}
    except Exception:
        return {}


def item_style_value(obj, field, prop, default=""):
    return item_style_dict(obj, field).get(prop, default) or ""


def item_style_flag(obj, field, prop):
    return flag_value(item_style_value(obj, field, prop), False)


def item_style_inline(obj, section, field):
    cfg = item_style_dict(obj, field)
    parts = []
    if cfg.get("font"): parts.append(f"font-family:{css_font_family(cfg['font'])} !important")
    if cfg.get("size"): parts.append(f"font-size:{css_dimension(cfg['size'])} !important")
    if cfg.get("weight"): parts.append(f"font-weight:{cfg['weight']} !important")
    if cfg.get("color"): parts.append(f"color:{cfg['color']} !important")
    if cfg.get("align"): parts.append(f"text-align:{cfg['align']} !important")
    if cfg.get("letter_spacing"): parts.append(f"letter-spacing:{css_dimension(cfg['letter_spacing'], 'px')} !important")
    if cfg.get("line_height"): parts.append(f"line-height:{cfg['line_height']} !important")
    if flag_value(cfg.get("italic"), False): parts.append("font-style:italic !important")
    if flag_value(cfg.get("uppercase"), False): parts.append("text-transform:uppercase !important")
    return ";".join(parts)


# ─────────────────────────────────────────────────────────────
# Draft / publish / version history helpers
# ─────────────────────────────────────────────────────────────
def safe_json_load(raw, fallback=None):
    if fallback is None:
        fallback = {}
    try:
        data = json.loads(raw or "{}")
        return data if isinstance(data, dict) else fallback
    except Exception:
        return fallback


def get_draft(key):
    row = DraftContent.query.filter_by(draft_key=key).first()
    return safe_json_load(row.payload_json) if row else {}


def save_draft(key, payload):
    row = DraftContent.query.filter_by(draft_key=key).first()
    if row:
        row.payload_json = json.dumps(payload, ensure_ascii=False)
        row.admin_username = admin_username()
        row.updated_at = datetime.utcnow()
    else:
        row = DraftContent(draft_key=key, payload_json=json.dumps(payload, ensure_ascii=False), admin_username=admin_username())
        db.session.add(row)
    db.session.commit()
    audit("draft_save", key)


def delete_draft(key):
    row = DraftContent.query.filter_by(draft_key=key).first()
    if row:
        db.session.delete(row)
        db.session.commit()
        audit("draft_delete", key)


def simple_namespace_from_model(obj, payload=None):
    data = model_to_dict(obj) if obj else {}
    if payload:
        data.update(payload)
    return SimpleNamespace(**data)


def site_with_drafts(use_draft=True):
    site = settings_dict()
    if use_draft:
        site.update(get_draft("settings"))
    return site


def field_visible_for_site(site_payload):
    def _visible(section, field, default=None):
        if default is None:
            default = field_default(section, field, True)
        return flag_value(site_payload.get(field_vis_key(section, field)), default)
    return _visible


def collect_settings_payload():
    fields = [
        "company_name", "tagline", "hero_title", "hero_subtitle", "short_description",
        "phone", "whatsapp", "public_phone_label", "email", "address", "map_embed", "facebook", "instagram",
        "linkedin", "primary_color", "secondary_color", "seo_title", "seo_description",
        "business_area", "service_areas", "google_business_url", "notification_email",
        "registered_name", "udyam_registration", "gstin", "enterprise_type",
        "business_commencement", "major_activity", "credential_note",
        "experience_documents", "contractor_registrations",
        "privacy_policy", "terms_text",
    ]
    payload = {field: request.form.get(field, "") for field in fields}
    for field, _label, _default in SETTINGS_FIELD_LABELS:
        payload[field_vis_key("settings", field)] = "1" if request.form.get(f"vis_{field}") else "0"
    payload.update(collect_field_styles("settings", SETTINGS_FIELD_LABELS))
    return payload


def apply_settings_payload(payload):
    for field, value in payload.items():
        set_setting(field, value)
    apply_field_styles(payload)


def collect_about_payload():
    fields = ["short_description", "full_description", "mission", "vision", "core_values", "experience_summary", "years_experience", "completed_projects", "active_projects", "team_members"]
    payload = {field: request.form.get(field, "") for field in fields}
    for field, _label, _default in ABOUT_FIELD_LABELS:
        payload[field_vis_key("about", field)] = "1" if request.form.get(f"vis_{field}") else "0"
    payload.update(collect_field_styles("about", ABOUT_FIELD_LABELS))
    return payload


def apply_about_payload(about, payload):
    for field in ["short_description", "full_description", "mission", "vision", "core_values", "experience_summary", "years_experience", "completed_projects", "active_projects", "team_members"]:
        if field in payload:
            setattr(about, field, payload.get(field) or "")
    for field, _label, _default in ABOUT_FIELD_LABELS:
        key = field_vis_key("about", field)
        if key in payload:
            set_setting(key, payload.get(key, "0"))
    apply_field_styles(payload)


def save_version(content_type, title, payload, object_id=None, note="Published snapshot"):
    version = ContentVersion(
        content_type=content_type,
        object_id=object_id,
        title=(title or content_type)[:240],
        payload_json=json.dumps(payload, ensure_ascii=False, default=str),
        version_note=note[:240],
        admin_username=admin_username(),
    )
    db.session.add(version)
    db.session.commit()
    return version


def service_payload(service):
    return model_to_dict(service)


def project_payload(project):
    return model_to_dict(project)


def gallery_payload(item):
    return model_to_dict(item)


def set_item_publish_state(obj):
    state = request.form.get("publish_state", "published")
    obj.is_published = state == "published"
    obj.updated_at = datetime.utcnow()
    if obj.is_published and not obj.published_at:
        obj.published_at = datetime.utcnow()


def public_services(include_drafts=False):
    q = Service.query.filter_by(is_active=True)
    if not include_drafts:
        q = q.filter_by(is_published=True)
    return q.order_by(Service.sort_order.asc(), Service.id.asc())


def public_projects(include_drafts=False):
    q = Project.query
    if not include_drafts:
        q = q.filter_by(is_published=True)
    return q.order_by(Project.sort_order.asc(), Project.is_featured.desc(), Project.id.desc())


def public_gallery(include_drafts=False):
    q = GalleryItem.query
    if not include_drafts:
        q = q.filter_by(is_published=True)
    return q.order_by(GalleryItem.sort_order.asc(), GalleryItem.id.desc())

@app.context_processor
def inject_globals():
    try:
        site = settings_dict()
    except Exception:
        site = {}
    return {
        "site": site,
        "media_url": media_url,
        "csrf_token": csrf_token,
        "csrf_field": csrf_field,
        "current_year": datetime.utcnow().year,
        "service_areas": service_area_list(site),
        "production_checks": {
            "SECRET_KEY": bool(os.environ.get("SECRET_KEY")),
            "DATABASE_URL": bool(os.environ.get("DATABASE_URL")),
            "CLOUDINARY_URL": bool(os.environ.get("CLOUDINARY_URL")),
            "SMTP": bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_USERNAME") and os.environ.get("SMTP_PASSWORD")),
        },
        "is_on": lambda key, default=False: flag_value(site.get(key), default),
        "field_visible": field_visible,
        "field_vis_key": field_vis_key,
        "item_field_visible": item_field_visible,
        "field_groups": FIELD_VISIBILITY_GROUPS,
        "style_key": style_key,
        "style_inline": style_inline,
        "item_style_key": item_style_key,
        "item_style_inline": item_style_inline,
        "item_style_value": item_style_value,
        "item_style_flag": item_style_flag,
        "css_dimension": css_dimension,
        "style_props": STYLE_PROPS,
        "current_admin": current_admin,
    }


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
            full_description="M-GROUPS INFRA PROJECTS provides civil construction and infrastructure project services across residential, commercial, and industrial requirements. The company focuses on systematic planning, site coordination, material control, safety practices, and timely execution. Replace this content with your verified company profile from the admin dashboard.",
            mission="To deliver reliable infrastructure and civil works with disciplined planning, transparent execution, and consistent quality.",
            vision="To become a trusted infrastructure project partner known for dependable delivery, safety, and long-term client relationships.",
            core_values="Quality Work\nSafety First\nTimely Delivery\nTransparent Communication\nResponsible Site Management",
            experience_summary="Add verified work history, service area, project categories, and practical experience from the admin panel.",
            years_experience="Add actual",
            completed_projects="Add actual",
            active_projects="Add actual",
            team_members="Add actual",
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

    if Admin.query.count() == 0:
        default_password = os.environ.get("ADMIN_DEFAULT_PASSWORD", "ChangeMe@123")
        db.session.add(Admin(username=os.environ.get("ADMIN_USERNAME", "admin"), password_hash=generate_password_hash(default_password)))

    db.session.commit()


with app.app_context():
    init_db()


# ─────────────────────────────────────────────────────────────
# Public routes
# ─────────────────────────────────────────────────────────────
@app.route("/")
def home():
    about = AboutContent.query.get(1)
    services = public_services().limit(6).all()
    projects = public_projects().limit(6).all()
    blocks = PageBlock.query.filter_by(page="home", is_published=True).order_by(PageBlock.sort_order.asc(), PageBlock.id.asc()).all()
    return render_template("home.html", about=about, services=services, projects=projects, page_blocks=blocks)


@app.route("/about")
def about():
    return render_template("about.html", about=AboutContent.query.get(1))


@app.route("/services")
def services():
    rows = public_services().all()
    return render_template("services.html", services=rows)


@app.route("/projects")
def projects():
    rows = public_projects().all()
    return render_template("projects.html", projects=rows)


@app.route("/projects/<int:project_id>")
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    if not project.is_published:
        abort(404)
    return render_template("project_detail.html", project=project)


@app.route("/gallery")
def gallery():
    items = public_gallery().all()
    return render_template("gallery.html", items=items)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        project_type = request.form.get("project_type", "").strip()
        message = request.form.get("message", "").strip()
        if len(name) < 2 or len(message) < 8:
            flash("Please enter your name and a clear project message.", "danger")
        else:
            enquiry = Enquiry(name=name[:160], email=email[:220], phone=phone[:80], project_type=project_type[:160], message=message[:5000])
            db.session.add(enquiry)
            db.session.commit()
            try:
                sent = send_enquiry_email(enquiry)
                audit("enquiry_email_sent" if sent else "enquiry_email_skipped", f"enquiry_id={enquiry.id}")
            except Exception as exc:
                audit("enquiry_email_failed", str(exc))
            flash("Your enquiry has been submitted. We will contact you soon.", "success")
            return redirect(url_for("contact"))
    return render_template("contact.html")


@app.route("/robots.txt")
def robots():
    body = f"User-agent: *\nAllow: /\nSitemap: {url_for('sitemap', _external=True)}\n"
    return Response(body, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap():
    pages = [url_for("home", _external=True), url_for("about", _external=True), url_for("services", _external=True), url_for("projects", _external=True), url_for("gallery", _external=True), url_for("contact", _external=True), url_for("service_areas_page", _external=True), url_for("privacy_policy", _external=True), url_for("terms", _external=True)]
    pages += [url_for("project_detail", project_id=p.id, _external=True) for p in Project.query.filter_by(is_published=True).all()]
    pages += [url_for("service_area_detail", slug=a["slug"], _external=True) for a in service_area_list()]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for page in pages:
        xml.append(f"<url><loc>{page}</loc><changefreq>weekly</changefreq></url>")
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")


@app.route("/healthz")
def healthz():
    try:
        db.session.execute(db.text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return jsonify({
        "status": "ok" if db_ok else "degraded",
        "database": db_ok,
        "cloudinary_configured": bool(os.environ.get("CLOUDINARY_URL")),
        "smtp_configured": bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_USERNAME") and os.environ.get("SMTP_PASSWORD")),
        "time": datetime.utcnow().isoformat() + "Z",
    }), 200 if db_ok else 503


@app.route("/service-areas")
def service_areas_page():
    return render_template("service_areas.html", areas=service_area_list())


@app.route("/service-areas/<slug>")
def service_area_detail(slug):
    areas = service_area_list()
    match = next((a for a in areas if a["slug"] == slug), None)
    if not match:
        abort(404)
    rows = public_services().all()
    return render_template("service_area_detail.html", area=match, services=rows)


@app.route("/privacy-policy")
def privacy_policy():
    return render_template("policy.html", title="Privacy Policy", body=settings_dict().get("privacy_policy", ""))


@app.route("/terms")
def terms():
    return render_template("policy.html", title="Terms & Conditions", body=settings_dict().get("terms_text", ""))


# ─────────────────────────────────────────────────────────────
# Admin auth
# ─────────────────────────────────────────────────────────────
@app.route("/admin/login", methods=["GET", "POST"])
@((limiter.limit("8 per minute")) if limiter else (lambda f: f))
def admin_login():
    if session.get("admin_id"):
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password_hash, password):
            session.clear()
            session["admin_id"] = admin.id
            session["csrf_token"] = secrets.token_urlsafe(32)
            audit("login", "Admin logged in")
            return redirect(url_for("admin_dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("admin/login.html")


@app.route("/admin/logout")
def admin_logout():
    audit("logout", "Admin logged out")
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin")
@login_required
def admin_dashboard():
    counts = {
        "services": Service.query.count(),
        "projects": Project.query.count(),
        "gallery": GalleryItem.query.count(),
        "unread": Enquiry.query.filter_by(is_read=False).count(),
    }
    enquiries = Enquiry.query.order_by(Enquiry.id.desc()).limit(8).all()
    logs = AuditLog.query.order_by(AuditLog.id.desc()).limit(8).all()
    return render_template("admin/dashboard.html", counts=counts, enquiries=enquiries, logs=logs)



# ─────────────────────────────────────────────────────────────
# Advanced CMS controls: preview, ordering, version history
# ─────────────────────────────────────────────────────────────
@app.route("/admin/preview")
@login_required
def admin_preview():
    page = request.args.get("page", "home")
    use_draft = request.args.get("draft", "1") == "1"
    preview_site = site_with_drafts(use_draft=use_draft)
    preview_about = simple_namespace_from_model(AboutContent.query.get(1), get_draft("about") if use_draft else None)
    services_rows = public_services(include_drafts=True).all()
    projects_rows = public_projects(include_drafts=True).all()
    gallery_rows = public_gallery(include_drafts=True).all()
    page_blocks_rows = PageBlock.query.order_by(PageBlock.sort_order.asc(), PageBlock.id.asc()).all()
    overrides = {
        "site": preview_site,
        "about": preview_about,
        "service_areas": service_area_list(preview_site),
        "field_visible": field_visible_for_site(preview_site),
        "is_on": lambda key, default=False: flag_value(preview_site.get(key), default),
        "preview_mode": True,
    }
    template_map = {
        "home": ("home.html", {"services": services_rows[:6], "projects": projects_rows[:6], "page_blocks": page_blocks_rows}),
        "about": ("about.html", {}),
        "services": ("services.html", {"services": services_rows}),
        "projects": ("projects.html", {"projects": projects_rows}),
        "gallery": ("gallery.html", {"items": gallery_rows}),
        "contact": ("contact.html", {}),
    }
    template, extra = template_map.get(page, template_map["home"])
    return render_template(template, **overrides, **extra)


@app.route("/admin/versions")
@login_required
def admin_versions():
    content_type = request.args.get("type", "")
    q = ContentVersion.query
    if content_type:
        q = q.filter_by(content_type=content_type)
    rows = q.order_by(ContentVersion.id.desc()).limit(100).all()
    return render_template("admin/versions.html", versions=rows, content_type=content_type)


@app.route("/admin/versions/<int:version_id>/restore", methods=["POST"])
@login_required
def admin_version_restore(version_id):
    version = ContentVersion.query.get_or_404(version_id)
    payload = safe_json_load(version.payload_json)
    try:
        if version.content_type == "settings":
            apply_settings_payload(payload)
        elif version.content_type == "about":
            about = AboutContent.query.get(1)
            about_payload = payload.get("about", payload)
            apply_about_payload(about, about_payload)
            for key, value in (payload.get("visibility") or {}).items():
                set_setting(key, value)
        elif version.content_type == "service":
            obj = Service.query.get(version.object_id) if version.object_id else None
            if obj is None:
                obj = Service()
                db.session.add(obj)
            for field in ["title", "description", "image_path", "icon", "sort_order", "is_active", "is_published", "visible_fields"]:
                if field in payload:
                    setattr(obj, field, payload[field])
            obj.updated_at = datetime.utcnow()
        elif version.content_type == "project":
            obj = Project.query.get(version.object_id) if version.object_id else None
            if obj is None:
                obj = Project(title=payload.get("title") or "Restored project")
                db.session.add(obj)
            for field in ["title", "location", "category", "status", "year", "client_type", "site_area", "duration", "project_value", "scope_of_work", "challenge", "solution", "outcome", "description", "image_path", "sort_order", "is_featured", "is_published", "visible_fields"]:
                if field in payload:
                    setattr(obj, field, payload[field])
            obj.updated_at = datetime.utcnow()
        elif version.content_type == "gallery":
            obj = GalleryItem.query.get(version.object_id) if version.object_id else None
            if obj is None:
                obj = GalleryItem(title=payload.get("title") or "Restored image", image_path=payload.get("image_path") or "")
                db.session.add(obj)
            for field in ["title", "caption", "image_path", "sort_order", "is_published", "visible_fields"]:
                if field in payload:
                    setattr(obj, field, payload[field])
            obj.updated_at = datetime.utcnow()
        db.session.commit()
        audit("version_restore", f"version_id={version.id}, type={version.content_type}")
        flash("Selected version restored. Review public preview before sharing.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Restore failed: {exc}", "danger")
    return redirect(url_for("admin_versions", type=version.content_type))


@app.route("/admin/ordering")
@login_required
def admin_ordering():
    sections = [s.strip() for s in (settings_dict().get("homepage_section_order") or "trust_strip\ncredentials\nservice_areas\nabout\nservices\nstats\nprojects\nwhy\ncta").splitlines() if s.strip()]
    return render_template("admin/ordering.html", sections=sections, services=Service.query.order_by(Service.sort_order.asc(), Service.id.asc()).all(), projects=Project.query.order_by(Project.sort_order.asc(), Project.id.desc()).all(), gallery=GalleryItem.query.order_by(GalleryItem.sort_order.asc(), GalleryItem.id.desc()).all())


@app.route("/admin/reorder/<kind>", methods=["POST"])
@login_required
def admin_reorder(kind):
    payload = request.get_json(silent=True) or {}
    order = payload.get("order") or []
    if kind == "sections":
        allowed = {"trust_strip", "credentials", "service_areas", "about", "services", "stats", "projects", "why", "cta"}
        clean = [x for x in order if x in allowed]
        if not clean:
            abort(400, "No valid sections supplied")
        set_setting("homepage_section_order", "\n".join(clean))
        db.session.commit()
        save_version("ordering", "Homepage section order", {"homepage_section_order": clean}, note="Homepage sections reordered")
    else:
        models = {"services": Service, "projects": Project, "gallery": GalleryItem, "page_blocks": PageBlock}
        model = models.get(kind)
        if not model:
            abort(404)
        for index, raw_id in enumerate(order, start=1):
            try:
                item = model.query.get(int(raw_id))
            except Exception:
                item = None
            if item:
                item.sort_order = index
                if hasattr(item, "updated_at"):
                    item.updated_at = datetime.utcnow()
        db.session.commit()
        save_version("ordering", f"{kind} order", {"kind": kind, "order": order}, note=f"{kind} reordered")
    audit("reorder", kind)
    return jsonify({"ok": True})


# ─────────────────────────────────────────────────────────────
# Admin content
# ─────────────────────────────────────────────────────────────
@app.route("/admin/settings", methods=["GET", "POST"])
@login_required
def admin_settings():
    if request.method == "POST":
        action = request.form.get("action", "publish")
        payload = collect_settings_payload()
        if action in {"draft", "preview"}:
            save_draft("settings", payload)
            flash("Website settings draft saved. Public website is unchanged until you publish.", "success")
            if action == "preview":
                return redirect(url_for("admin_preview", page="home", draft="1"))
            return redirect(url_for("admin_settings"))

        apply_settings_payload(payload)
        logo = request.files.get("logo")
        if logo and logo.filename:
            try:
                path = save_upload(logo, "logo")
                set_setting("logo_path", path)
                set_setting("og_image", path)
            except ValueError as e:
                flash(str(e), "danger")
                return redirect(url_for("admin_settings"))
        db.session.commit()
        save_version("settings", "Website settings", settings_dict(), note="Settings published")
        delete_draft("settings")
        audit("settings_publish", "Website settings published")
        flash("Website settings published.", "success")
        return redirect(url_for("admin_settings"))
    draft_settings = get_draft("settings")
    form_site = settings_dict()
    if request.args.get("draft") == "1":
        form_site.update(draft_settings)
    return render_template("admin/settings.html", draft_settings=draft_settings, form_site=form_site, form_visible=field_visible_for_site(form_site))



@app.route("/admin/appearance", methods=["GET", "POST"])
@login_required
def admin_appearance():
    if request.method == "POST":
        for field in APPEARANCE_FIELDS:
            set_setting(field, request.form.get(field, ""))
        for field in VISIBILITY_FIELDS:
            set_setting(field, "1" if request.form.get(field) else "0")
        apply_field_styles(collect_field_styles("appearance", APPEARANCE_STYLE_LABELS))
        db.session.commit()
        save_version("appearance", "Visibility & Appearance", settings_dict(), note="Appearance and public text updated")
        audit("appearance_update", "Visibility, typography, colors and public text updated")
        flash("Appearance, visibility and text controls saved.", "success")
        return redirect(url_for("admin_appearance"))
    return render_template("admin/appearance.html", appearance_fields=APPEARANCE_FIELDS, visibility_fields=VISIBILITY_FIELDS)

@app.route("/admin/about", methods=["GET", "POST"])
@login_required
def admin_about():
    about = AboutContent.query.get(1)
    if request.method == "POST":
        action = request.form.get("action", "publish")
        payload = collect_about_payload()
        if action in {"draft", "preview"}:
            save_draft("about", payload)
            flash("About/experience draft saved. Public website is unchanged until you publish.", "success")
            if action == "preview":
                return redirect(url_for("admin_preview", page="about", draft="1"))
            return redirect(url_for("admin_about"))

        apply_about_payload(about, payload)
        db.session.commit()
        save_version("about", "About & Experience", {"about": model_to_dict(about), "visibility": {field_vis_key("about", f): settings_dict().get(field_vis_key("about", f), "") for f, _l, _d in ABOUT_FIELD_LABELS}}, note="About published")
        delete_draft("about")
        audit("about_publish", "About and experience content published")
        flash("About and experience details published.", "success")
        return redirect(url_for("admin_about"))
    draft_about = get_draft("about")
    form_about = simple_namespace_from_model(about, draft_about if request.args.get("draft") == "1" else None)
    about_vis_site = settings_dict()
    if request.args.get("draft") == "1":
        about_vis_site.update({k: v for k, v in draft_about.items() if k.startswith("vis_about_")})
    return render_template("admin/about.html", about=form_about, draft_about=draft_about, form_visible=field_visible_for_site(about_vis_site))


@app.route("/admin/services")
@login_required
def admin_services():
    rows = Service.query.order_by(Service.sort_order.asc(), Service.id.asc()).all()
    return render_template("admin/services.html", services=rows)


@app.route("/admin/services/new", methods=["GET", "POST"])
@login_required
def admin_service_new():
    if request.method == "POST":
        return save_service()
    return render_template("admin/service_form.html", service=None)


@app.route("/admin/services/<int:service_id>/edit", methods=["GET", "POST"])
@login_required
def admin_service_edit(service_id):
    service = Service.query.get_or_404(service_id)
    if request.method == "POST":
        return save_service(service)
    return render_template("admin/service_form.html", service=service)


def save_service(service=None):
    new = service is None
    service = service or Service()
    title = request.form.get("title", "").strip()
    if not title:
        flash("Service title is required.", "danger")
        return redirect(request.url)
    service.title = title
    service.description = request.form.get("description", "").strip()
    service.icon = request.form.get("icon", "building").strip() or "building"
    service.sort_order = int(request.form.get("sort_order") or 0)
    service.is_active = bool(request.form.get("is_active"))
    set_item_publish_state(service)
    service.visible_fields = pack_item_visible_fields("service")
    service.styles_json = collect_item_styles("service")
    image = request.files.get("image")
    if image and image.filename:
        try:
            if service.image_path:
                delete_media(service.image_path)
            service.image_path = save_upload(image, "service")
        except ValueError as e:
            flash(str(e), "danger")
            return redirect(request.url)
    if new:
        db.session.add(service)
    db.session.commit()
    save_version("service", service.title, service_payload(service), object_id=service.id, note="Service saved as " + ("Published" if service.is_published else "Draft"))
    audit("service_save", service.title)
    flash("Service saved as " + ("published" if service.is_published else "draft") + ".", "success")
    if request.form.get("action") == "preview":
        return redirect(url_for("admin_preview", page="services", draft="1"))
    return redirect(url_for("admin_services"))


@app.route("/admin/services/<int:service_id>/delete", methods=["POST"])
@login_required
def admin_service_delete(service_id):
    service = Service.query.get_or_404(service_id)
    title = service.title
    delete_media(service.image_path)
    save_version("service", title, service_payload(service), object_id=service.id, note="Service deleted")
    db.session.delete(service)
    db.session.commit()
    audit("service_delete", title)
    flash("Service deleted.", "success")
    return redirect(url_for("admin_services"))


@app.route("/admin/projects")
@login_required
def admin_projects():
    rows = Project.query.order_by(Project.sort_order.asc(), Project.id.desc()).all()
    return render_template("admin/projects.html", projects=rows)


@app.route("/admin/projects/new", methods=["GET", "POST"])
@login_required
def admin_project_new():
    if request.method == "POST":
        return save_project()
    return render_template("admin/project_form.html", project=None)


@app.route("/admin/projects/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
def admin_project_edit(project_id):
    project = Project.query.get_or_404(project_id)
    if request.method == "POST":
        return save_project(project)
    return render_template("admin/project_form.html", project=project)


def save_project(project=None):
    new = project is None
    project = project or Project()
    title = request.form.get("title", "").strip()
    if not title:
        flash("Project title is required.", "danger")
        return redirect(request.url)
    project.title = title
    project.location = request.form.get("location", "").strip()
    project.category = request.form.get("category", "").strip()
    project.status = request.form.get("status", "Ongoing").strip()
    project.year = request.form.get("year", "").strip()
    project.client_type = request.form.get("client_type", "").strip()
    project.site_area = request.form.get("site_area", "").strip()
    project.duration = request.form.get("duration", "").strip()
    project.project_value = request.form.get("project_value", "").strip()
    project.scope_of_work = request.form.get("scope_of_work", "").strip()
    project.challenge = request.form.get("challenge", "").strip()
    project.solution = request.form.get("solution", "").strip()
    project.outcome = request.form.get("outcome", "").strip()
    project.description = request.form.get("description", "").strip()
    project.sort_order = int(request.form.get("sort_order") or 0)
    project.is_featured = bool(request.form.get("is_featured"))
    set_item_publish_state(project)
    project.visible_fields = pack_item_visible_fields("project")
    project.styles_json = collect_item_styles("project")
    image = request.files.get("image")
    if image and image.filename:
        try:
            if project.image_path:
                delete_media(project.image_path)
            project.image_path = save_upload(image, "project")
        except ValueError as e:
            flash(str(e), "danger")
            return redirect(request.url)
    if new:
        db.session.add(project)
    db.session.commit()
    save_version("project", project.title, project_payload(project), object_id=project.id, note="Project saved as " + ("Published" if project.is_published else "Draft"))
    audit("project_save", project.title)
    flash("Project saved as " + ("published" if project.is_published else "draft") + ".", "success")
    if request.form.get("action") == "preview":
        return redirect(url_for("admin_preview", page="projects", draft="1"))
    return redirect(url_for("admin_projects"))


@app.route("/admin/projects/<int:project_id>/delete", methods=["POST"])
@login_required
def admin_project_delete(project_id):
    project = Project.query.get_or_404(project_id)
    title = project.title
    delete_media(project.image_path)
    save_version("project", title, project_payload(project), object_id=project.id, note="Project deleted")
    db.session.delete(project)
    db.session.commit()
    audit("project_delete", title)
    flash("Project deleted.", "success")
    return redirect(url_for("admin_projects"))


@app.route("/admin/gallery", methods=["GET", "POST"])
@login_required
def admin_gallery():
    if request.method == "POST":
        image = request.files.get("image")
        if not image or not image.filename:
            flash("Image is required.", "danger")
            return redirect(url_for("admin_gallery"))
        try:
            image_path = save_upload(image, "gallery")
        except ValueError as e:
            flash(str(e), "danger")
            return redirect(url_for("admin_gallery"))
        item = GalleryItem(
            title=request.form.get("title", "Work photo").strip() or "Work photo",
            caption=request.form.get("caption", "").strip(),
            sort_order=int(request.form.get("sort_order") or 0),
            image_path=image_path,
            visible_fields=pack_item_visible_fields("gallery"),
            styles_json=collect_item_styles("gallery"),
            is_published=request.form.get("publish_state", "published") == "published",
            published_at=datetime.utcnow() if request.form.get("publish_state", "published") == "published" else None,
        )
        db.session.add(item)
        db.session.commit()
        save_version("gallery", item.title, gallery_payload(item), object_id=item.id, note="Gallery item uploaded as " + ("Published" if item.is_published else "Draft"))
        audit("gallery_upload", item.title)
        flash("Gallery image uploaded as " + ("published" if item.is_published else "draft") + ".", "success")
        return redirect(url_for("admin_gallery"))
    items = GalleryItem.query.order_by(GalleryItem.sort_order.asc(), GalleryItem.id.desc()).all()
    return render_template("admin/gallery.html", items=items)


@app.route("/admin/gallery/<int:item_id>/delete", methods=["POST"])
@login_required
def admin_gallery_delete(item_id):
    item = GalleryItem.query.get_or_404(item_id)
    title = item.title
    delete_media(item.image_path)
    save_version("gallery", title, gallery_payload(item), object_id=item.id, note="Gallery item deleted")
    db.session.delete(item)
    db.session.commit()
    audit("gallery_delete", title)
    flash("Gallery image deleted.", "success")
    return redirect(url_for("admin_gallery"))


@app.route("/admin/enquiries")
@login_required
def admin_enquiries():
    rows = Enquiry.query.order_by(Enquiry.id.desc()).all()
    return render_template("admin/enquiries.html", enquiries=rows)


@app.route("/admin/enquiries/<int:enquiry_id>/read", methods=["POST"])
@login_required
def admin_enquiry_read(enquiry_id):
    enquiry = Enquiry.query.get_or_404(enquiry_id)
    enquiry.is_read = True
    db.session.commit()
    audit("enquiry_read", str(enquiry.id))
    return redirect(url_for("admin_enquiries"))


@app.route("/admin/enquiries/<int:enquiry_id>/delete", methods=["POST"])
@login_required
def admin_enquiry_delete(enquiry_id):
    enquiry = Enquiry.query.get_or_404(enquiry_id)
    db.session.delete(enquiry)
    db.session.commit()
    audit("enquiry_delete", str(enquiry_id))
    flash("Enquiry deleted.", "success")
    return redirect(url_for("admin_enquiries"))


@app.route("/admin/password", methods=["GET", "POST"])
@login_required
def admin_password():
    admin = Admin.query.get_or_404(session["admin_id"])
    if request.method == "POST":
        current = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")
        if not check_password_hash(admin.password_hash, current):
            flash("Current password is incorrect.", "danger")
        elif new_password != confirm:
            flash("New passwords do not match.", "danger")
        elif len(new_password) < 10:
            flash("Password must be at least 10 characters.", "danger")
        else:
            admin.password_hash = generate_password_hash(new_password)
            db.session.commit()
            audit("password_change", "Admin password changed")
            flash("Password changed.", "success")
            return redirect(url_for("admin_dashboard"))
    return render_template("admin/change_password.html")


@app.route("/admin/export/enquiries.csv")
@login_required
def export_enquiries_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "name", "email", "phone", "project_type", "message", "is_read", "created_at"])
    for e in Enquiry.query.order_by(Enquiry.id.desc()).all():
        writer.writerow([e.id, e.name, e.email, e.phone, e.project_type, e.message, int(e.is_read), e.created_at.isoformat()])
    audit("export_enquiries", "CSV exported")
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=enquiries.csv"})


@app.route("/admin/backup.json")
@login_required
def backup_json():
    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "settings": settings_dict(),
        "about": model_to_dict(AboutContent.query.get(1)),
        "services": [model_to_dict(x) for x in Service.query.all()],
        "projects": [model_to_dict(x) for x in Project.query.all()],
        "gallery": [model_to_dict(x) for x in GalleryItem.query.all()],
        "enquiries": [model_to_dict(x) for x in Enquiry.query.all()],
        "drafts": [model_to_dict(x) for x in DraftContent.query.all()],
        "versions": [model_to_dict(x) for x in ContentVersion.query.order_by(ContentVersion.id.desc()).limit(100).all()],
    }
    audit("backup_json", "Backup downloaded")
    buf = io.BytesIO(json.dumps(payload, indent=2, ensure_ascii=False, default=str).encode("utf-8"))
    return send_file(buf, mimetype="application/json", as_attachment=True, download_name="mgroups_backup.json")


def model_to_dict(obj):
    if not obj:
        return {}
    data = {}
    for col in obj.__table__.columns:
        value = getattr(obj, col.name)
        data[col.name] = value.isoformat() if isinstance(value, datetime) else value
    return data


@app.route("/admin/restore", methods=["GET", "POST"])
@login_required
def restore_backup():
    if request.method == "POST":
        f = request.files.get("backup_file")
        if not f or not f.filename:
            flash("Upload a JSON backup file.", "danger")
            return redirect(url_for("restore_backup"))
        try:
            payload = json.loads(f.read().decode("utf-8"))
            if not isinstance(payload, dict) or "settings" not in payload:
                raise ValueError("Invalid backup format")
            mode = request.form.get("mode", "content_only")
            for key, value in (payload.get("settings") or {}).items():
                set_setting(str(key), "" if value is None else str(value))
            about_payload = payload.get("about") or {}
            about = AboutContent.query.get(1)
            if about:
                for field in ["short_description", "full_description", "mission", "vision", "core_values", "experience_summary", "years_experience", "completed_projects", "active_projects", "team_members"]:
                    if field in about_payload:
                        setattr(about, field, about_payload.get(field) or "")
            if mode == "full_replace":
                Service.query.delete()
                Project.query.delete()
                GalleryItem.query.delete()
                for x in payload.get("services", []):
                    db.session.add(Service(title=x.get("title") or "Service", description=x.get("description") or "", icon=x.get("icon") or "building", sort_order=int(x.get("sort_order") or 0), image_path=x.get("image_path") or "", is_active=bool(x.get("is_active", True)), is_published=bool(x.get("is_published", True)), visible_fields=x.get("visible_fields") or ""))
                for x in payload.get("projects", []):
                    db.session.add(Project(
                        title=x.get("title") or "Project", location=x.get("location") or "", category=x.get("category") or "", status=x.get("status") or "Ongoing", year=x.get("year") or "", client_type=x.get("client_type") or "", site_area=x.get("site_area") or "", duration=x.get("duration") or "", project_value=x.get("project_value") or "", scope_of_work=x.get("scope_of_work") or "", challenge=x.get("challenge") or "", solution=x.get("solution") or "", outcome=x.get("outcome") or "", description=x.get("description") or "", image_path=x.get("image_path") or "", sort_order=int(x.get("sort_order") or 0), is_featured=bool(x.get("is_featured", False)), is_published=bool(x.get("is_published", True)), visible_fields=x.get("visible_fields") or ""
                    ))
                for x in payload.get("gallery", []):
                    if x.get("image_path"):
                        db.session.add(GalleryItem(title=x.get("title") or "Work photo", caption=x.get("caption") or "", image_path=x.get("image_path") or "", sort_order=int(x.get("sort_order") or 0), is_published=bool(x.get("is_published", True)), visible_fields=x.get("visible_fields") or ""))
            db.session.commit()
            audit("restore_backup", f"mode={mode}")
            flash("Backup restored. Check public pages before sharing the website.", "success")
            return redirect(url_for("admin_dashboard"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Restore failed: {exc}", "danger")
            return redirect(url_for("restore_backup"))
    return render_template("admin/restore.html")




# ─────────────────────────────────────────────────────────────
# Advanced CMS: media library, cropper, permission matrix
# ─────────────────────────────────────────────────────────────
def local_media_images():
    rows = []
    for path in sorted(UPLOAD_DIR.glob("*"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True):
        if path.is_file() and allowed_file(path.name):
            rows.append({
                "name": path.name,
                "url": url_for("static", filename=f"uploads/{path.name}"),
                "size_kb": max(1, int(path.stat().st_size / 1024)),
            })
    return rows


@app.route("/admin/media", methods=["GET", "POST"])
@login_required
def admin_media():
    if request.method == "POST":
        image = request.files.get("image")
        prefix = request.form.get("prefix", "media").strip() or "media"
        if not image or not image.filename:
            flash("Choose an image to upload.", "danger")
            return redirect(url_for("admin_media"))
        try:
            save_upload(image, prefix)
            audit("media_upload", image.filename)
            flash("Image uploaded to media library.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
        return redirect(url_for("admin_media"))
    return render_template("admin/media.html", images=local_media_images())


@app.route("/admin/media/<path:filename>/crop", methods=["POST"])
@login_required
def admin_media_crop(filename):
    if not Image:
        flash("Image cropper requires Pillow. Install requirements.txt first.", "danger")
        return redirect(url_for("admin_media"))
    safe = secure_filename(filename)
    src = UPLOAD_DIR / safe
    if not src.exists() or not src.is_file() or not allowed_file(src.name):
        flash("Image not found.", "danger")
        return redirect(url_for("admin_media"))
    try:
        x = max(0, int(request.form.get("x") or 0))
        y = max(0, int(request.form.get("y") or 0))
        w = max(1, int(request.form.get("w") or 600))
        h = max(1, int(request.form.get("h") or 400))
        with Image.open(src) as im:
            im = im.convert("RGB")
            x2 = min(im.width, x + w)
            y2 = min(im.height, y + h)
            cropped = im.crop((x, y, x2, y2))
            out = UPLOAD_DIR / f"crop_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{src.stem}.jpg"
            cropped.save(out, "JPEG", quality=88, optimize=True)
        audit("media_crop", safe)
        flash("Cropped copy created. Use it in Services, Projects, Gallery, or Page Builder.", "success")
    except Exception as exc:
        flash(f"Crop failed: {exc}", "danger")
    return redirect(url_for("admin_media"))


@app.route("/admin/permissions", methods=["GET", "POST"])
@login_required
@require_role("owner")
def admin_permissions():
    if request.method == "POST":
        for key, _label, _note in ADMIN_PERMISSION_AREAS:
            set_setting(f"perm_editor_{key}", "1" if request.form.get(f"perm_editor_{key}") else "0")
        db.session.commit()
        audit("permissions_update", "Editor role permissions updated")
        flash("Role permissions saved.", "success")
        return redirect(url_for("admin_permissions"))
    return render_template("admin/permissions.html", areas=ADMIN_PERMISSION_AREAS, defaults=DEFAULT_EDITOR_PERMISSION)

@app.errorhandler(400)
def bad_request(e):
    return render_template("error.html", code=400, message="The request could not be processed. Refresh the page and try again."), 400



# ─────────────────────────────────────────────────────────────
# Advanced CMS: page builder, admin users, side-by-side diff
# ─────────────────────────────────────────────────────────────
@app.route("/admin/page-builder", methods=["GET", "POST"])
@login_required
@require_role("owner", "editor")
def admin_page_builder():
    if request.method == "POST":
        block = PageBlock()
        block.page = request.form.get("page", "home")
        block.block_type = request.form.get("block_type", "text")
        block.title = request.form.get("title", "").strip()
        block.body = request.form.get("body", "").strip()
        block.button_text = request.form.get("button_text", "").strip()
        block.button_url = request.form.get("button_url", "").strip()
        block.sort_order = int(request.form.get("sort_order") or 0)
        block.is_published = request.form.get("publish_state", "draft") == "published"
        block.styles_json = json.dumps({"title": {"font": request.form.get("title_font", ""), "size": request.form.get("title_size", ""), "weight": request.form.get("title_weight", "")}, "body": {"font": request.form.get("body_font", ""), "size": request.form.get("body_size", ""), "weight": request.form.get("body_weight", "")}}, ensure_ascii=False)
        image = request.files.get("image")
        if image and image.filename:
            try:
                block.image_path = save_upload(image, "pageblock")
            except ValueError as e:
                flash(str(e), "danger")
                return redirect(url_for("admin_page_builder"))
        db.session.add(block)
        db.session.commit()
        save_version("page_block", block.title or block.block_type, model_to_dict(block), object_id=block.id, note="Page builder block saved")
        audit("page_block_save", block.title)
        flash("Page block saved.", "success")
        return redirect(url_for("admin_page_builder"))
    blocks = PageBlock.query.order_by(PageBlock.sort_order.asc(), PageBlock.id.desc()).all()
    return render_template("admin/page_builder.html", blocks=blocks)


@app.route("/admin/page-builder/<int:block_id>/delete", methods=["POST"])
@login_required
@require_role("owner", "editor")
def admin_page_builder_delete(block_id):
    validate_csrf()
    block = PageBlock.query.get_or_404(block_id)
    if block.image_path:
        delete_media(block.image_path)
    db.session.delete(block)
    db.session.commit()
    audit("page_block_delete", str(block_id))
    flash("Page block deleted.", "success")
    return redirect(url_for("admin_page_builder"))


@app.route("/admin/users", methods=["GET", "POST"])
@login_required
@require_role("owner")
def admin_users():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "viewer")
        if role not in {"owner", "editor", "viewer"}:
            role = "viewer"
        if not username or len(password) < 8:
            flash("Username and password of at least 8 characters are required.", "danger")
            return redirect(url_for("admin_users"))
        if Admin.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for("admin_users"))
        db.session.add(Admin(username=username, password_hash=generate_password_hash(password), role=role, is_active=True))
        db.session.commit()
        audit("admin_user_create", username)
        flash("Admin user created.", "success")
        return redirect(url_for("admin_users"))
    users = Admin.query.order_by(Admin.id.asc()).all()
    return render_template("admin/users.html", users=users)


@app.route("/admin/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@require_role("owner")
def admin_user_toggle(user_id):
    validate_csrf()
    user = Admin.query.get_or_404(user_id)
    if user.id == session.get("admin_id"):
        flash("You cannot disable your own account.", "danger")
        return redirect(url_for("admin_users"))
    user.is_active = not user.is_active
    db.session.commit()
    audit("admin_user_toggle", user.username)
    return redirect(url_for("admin_users"))


def text_diff_html(a, b):
    import difflib
    a_lines = json.dumps(a, indent=2, ensure_ascii=False, default=str).splitlines()
    b_lines = json.dumps(b, indent=2, ensure_ascii=False, default=str).splitlines()
    return difflib.HtmlDiff(wrapcolumn=100).make_table(a_lines, b_lines, "Older", "Newer", context=True, numlines=3)


@app.route("/admin/versions/compare")
@login_required
def admin_versions_compare():
    left = ContentVersion.query.get_or_404(int(request.args.get("left") or 0))
    right = ContentVersion.query.get_or_404(int(request.args.get("right") or 0))
    left_payload = safe_json_load(left.payload_json)
    right_payload = safe_json_load(right.payload_json)
    diff_table = text_diff_html(left_payload, right_payload)
    return render_template("admin/version_compare.html", left=left, right=right, diff_table=diff_table)

@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="The page you requested was not found."), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
