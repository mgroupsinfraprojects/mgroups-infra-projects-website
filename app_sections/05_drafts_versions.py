# Auto-split from app.py for readability. Executed by app.py in application globals.

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


def production_check_groups():
    admin_default = os.environ.get("ADMIN_DEFAULT_PASSWORD", "")
    no_default_ok = os.environ.get("NO_DEFAULT_PASSWORD", "0") == "1" or (admin_default and "change" not in admin_default.lower() and "admin" not in admin_default.lower() and len(admin_default) >= 12)
    required = [
        ("SECRET_KEY", bool(os.environ.get("SECRET_KEY")), "Set a strong Render secret key."),
        ("COOKIE_SECURE=1", app.config.get("SESSION_COOKIE_SECURE") is True, "Force secure cookies on HTTPS."),
        ("DATABASE_URL", bool(os.environ.get("DATABASE_URL")), "Use Render PostgreSQL for permanent data."),
        ("CLOUDINARY_URL", cloudinary_ready(), "Use Cloudinary for persistent uploaded images."),
        ("ADMIN_RECOVERY_EMAIL", bool(os.environ.get("ADMIN_RECOVERY_EMAIL")), "Required for password recovery."),
        ("NO_DEFAULT_PASSWORD=1", no_default_ok, "Confirm no public default password is being used."),
    ]
    recommended = [
        ("SMTP_HOST", bool(os.environ.get("SMTP_HOST")), "Needed for enquiry/recovery email."),
        ("SMTP_USERNAME", bool(os.environ.get("SMTP_USERNAME")), "SMTP login username."),
        ("SMTP_PASSWORD", bool(os.environ.get("SMTP_PASSWORD")), "SMTP app password, not normal Gmail password."),
        ("SMTP_TO", bool(os.environ.get("SMTP_TO")), "Recipient for website enquiries."),
    ]
    completed = [x for x in required + recommended if x[1]]
    missing = [x for x in required + recommended if not x[1]]
    return {"required": required, "recommended": recommended, "completed": completed, "missing": missing}


def live_edit_attrs(target, field, target_id=None):
    """Return safe data attributes used only by the protected Live Editor.

    Public pages call this helper too, but it must output nothing outside
    /admin/live-edit so the public site remains normal and cannot crash when
    Live Editor is not active.
    """
    try:
        if not request.path.startswith("/admin/live-edit"):
            return ""
    except Exception:
        return ""

    target = str(target or "").strip().replace("\"", "").replace("'", "")
    field = str(field or "").strip().replace("\"", "").replace("'", "")
    if not target or not field:
        return ""

    attrs = f'data-live-edit="1" data-live-target="{target}" data-live-field="{field}"'
    if target_id is not None and str(target_id).strip() != "":
        safe_id = str(target_id).strip().replace("\"", "").replace("'", "")
        attrs += f' data-live-id="{safe_id}"'
    return attrs


@app.context_processor
def inject_globals():
    try:
        site = settings_dict()
    except Exception:
        site = {}
    checks_grouped = production_check_groups()
    gallery_count = 0
    try:
        gallery_count = public_gallery().count()
    except Exception:
        gallery_count = 0
    return {
        "site": site,
        "media_url": media_url,
        "csrf_token": csrf_token,
        "csrf_field": csrf_field,
        "current_year": datetime.utcnow().year,
        "service_areas": service_area_list(site),
        "production_checks": {item[0]: item[1] for item in checks_grouped["required"] + checks_grouped["recommended"]},
        "production_checks_grouped": checks_grouped,
        "gallery_nav_visible": flag_value(site.get("show_gallery_nav"), True) and gallery_count > 0,
        "published_gallery_count": gallery_count,
        "admin_mode": admin_mode,
        "is_advanced_mode": advanced_mode_enabled,
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
        "live_edit_attrs": live_edit_attrs,
    }


