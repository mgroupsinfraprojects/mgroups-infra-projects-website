# Auto-split from app.py for readability. Executed by app.py in application globals.

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
        "service_areas": ("service_areas.html", {"areas": service_area_list(preview_site)}),
        "privacy": ("policy.html", {"title": "Privacy Policy", "body": preview_site.get("privacy_policy", ""), "policy_field": "privacy_policy"}),
        "terms": ("policy.html", {"title": "Terms & Conditions", "body": preview_site.get("terms_text", ""), "policy_field": "terms_text"}),
    }
    template, extra = template_map.get(page, template_map["home"])
    return render_template(template, **overrides, **extra)


def live_editor_page_map(site=None):
    return [
        {"key": "home", "label": "Home", "url": url_for("admin_live_edit", page="home")},
        {"key": "about", "label": "About", "url": url_for("admin_live_edit", page="about")},
        {"key": "services", "label": "Services", "url": url_for("admin_live_edit", page="services")},
        {"key": "projects", "label": "Projects", "url": url_for("admin_live_edit", page="projects")},
        {"key": "gallery", "label": "Gallery", "url": url_for("admin_live_edit", page="gallery")},
        {"key": "contact", "label": "Contact", "url": url_for("admin_live_edit", page="contact")},
        {"key": "service_areas", "label": "Service Areas", "url": url_for("admin_live_edit", page="service_areas")},
        {"key": "privacy", "label": "Privacy", "url": url_for("admin_live_edit", page="privacy")},
        {"key": "terms", "label": "Terms", "url": url_for("admin_live_edit", page="terms")},
    ]


@app.route("/admin/live-edit")
@login_required
@require_role("owner")
def admin_live_edit():
    """Render public pages with owner-only inline editing, toolbar and safe create controls."""
    # Ensure the CSRF token is created before the public template renders.
    csrf_token()
    page = request.args.get("page", "home")
    use_draft = request.args.get("draft", "0") == "1"
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
        "live_edit_mode": True,
        "live_edit_page": page,
        "live_editor_pages": live_editor_page_map(preview_site),
    }
    template_map = {
        "home": ("home.html", {"services": services_rows[:6], "projects": projects_rows[:6], "page_blocks": page_blocks_rows}),
        "about": ("about.html", {}),
        "services": ("services.html", {"services": services_rows}),
        "projects": ("projects.html", {"projects": projects_rows}),
        "gallery": ("gallery.html", {"items": gallery_rows}),
        "contact": ("contact.html", {}),
        "service_areas": ("service_areas.html", {"areas": service_area_list(preview_site)}),
        "privacy": ("policy.html", {"title": "Privacy Policy", "body": preview_site.get("privacy_policy", ""), "policy_field": "privacy_policy"}),
        "terms": ("policy.html", {"title": "Terms & Conditions", "body": preview_site.get("terms_text", ""), "policy_field": "terms_text"}),
    }
    template, extra = template_map.get(page, template_map["home"])
    return render_template(template, **overrides, **extra)


def live_edit_allowed_fields():
    return {
        "setting": {name for name, _label, _default in SETTINGS_FIELD_LABELS},
        "appearance": set(APPEARANCE_FIELDS),
        "about": {name for name, _label, _default in ABOUT_FIELD_LABELS},
        "service": {"title", "description", "icon"},
        "project": {"title", "location", "category", "status", "year", "client_type", "site_area", "duration", "project_value", "scope_of_work", "challenge", "solution", "outcome", "description"},
        "gallery": {"title", "caption"},
        "page_block": {"title", "body", "button_text", "button_url"},
    }


def live_edit_get_item(target, target_id):
    if not target_id:
        return None
    try:
        ident = int(target_id)
    except Exception:
        return None
    if target == "service":
        return Service.query.get(ident)
    if target == "project":
        return Project.query.get(ident)
    if target == "gallery":
        return GalleryItem.query.get(ident)
    if target == "page_block":
        return PageBlock.query.get(ident)
    return None


@app.route("/admin/live-edit/save", methods=["POST"])
@login_required
@require_role("owner")
def admin_live_edit_save():
    """Save one inline text field from the live editor. Returns JSON only."""
    data = request.get_json(silent=True) or {}
    target = (data.get("target") or "").strip()
    field = (data.get("field") or "").strip()
    target_id = data.get("id") or ""
    value = (data.get("value") or "").strip()
    allowed = live_edit_allowed_fields()

    if not target or not field:
        return jsonify({"ok": False, "error": "Missing edit target. Refresh Live Editor and try again."}), 400
    if target not in allowed or field not in allowed[target]:
        return jsonify({"ok": False, "error": f"Inline edit is not enabled for {target}.{field}."}), 400

    try:
        if target == "setting":
            set_setting(field, value[:5000])
        elif target == "appearance":
            set_setting(field, value[:5000])
        elif target == "about":
            about = AboutContent.query.get(1)
            if not about:
                about = AboutContent(id=1)
                db.session.add(about)
            setattr(about, field, value[:12000])
        elif target in {"service", "project", "gallery", "page_block"}:
            obj = live_edit_get_item(target, target_id)
            if not obj:
                return jsonify({"ok": False, "error": f"{target.replace('_', ' ').title()} not found. Refresh Live Editor."}), 404
            if field == "title" and not value and target in {"service", "project", "gallery"}:
                return jsonify({"ok": False, "error": "Title cannot be blank."}), 400
            limit = 12000 if field in {"description", "scope_of_work", "challenge", "solution", "outcome", "body"} else 5000
            setattr(obj, field, value[:limit])
            if hasattr(obj, "updated_at"):
                obj.updated_at = datetime.utcnow()
        db.session.commit()
        audit("live_edit_save", f"{target}.{field}{':' + str(target_id) if target_id else ''}")
        return jsonify({"ok": True, "value": value})
    except Exception as exc:
        db.session.rollback()
        app.logger.exception("Live edit save failed for %s.%s: %s", target, field, exc)
        return jsonify({"ok": False, "error": f"Save failed on server: {exc.__class__.__name__}. Check Render logs if this repeats."}), 500


@app.route("/admin/live-edit/style", methods=["POST"])
@login_required
@require_role("owner")
def admin_live_edit_style():
    """Save style changes from the toolbar for the selected editable field."""
    data = request.get_json(silent=True) or {}
    target = (data.get("target") or "").strip()
    field = (data.get("field") or "").strip()
    target_id = data.get("id") or ""
    props = data.get("props") if isinstance(data.get("props"), dict) else {}
    allowed = live_edit_allowed_fields()
    if target not in allowed or field not in allowed[target]:
        return jsonify({"ok": False, "error": "Style target is not editable."}), 400
    clean = {}
    for prop, value in props.items():
        if prop in STYLE_PROPS:
            clean[prop] = str(value or "")[:120]
    try:
        if target in {"setting", "appearance", "about"}:
            section = {"setting": "settings", "appearance": "appearance", "about": "about"}[target]
            for prop, value in clean.items():
                set_setting(style_key(section, field, prop), value)
        else:
            obj = live_edit_get_item(target, target_id)
            if not obj:
                return jsonify({"ok": False, "error": "Item not found for style update."}), 404
            try:
                styles = json.loads(getattr(obj, "styles_json", "") or "{}")
                if not isinstance(styles, dict):
                    styles = {}
            except Exception:
                styles = {}
            current = styles.get(field, {}) if isinstance(styles.get(field, {}), dict) else {}
            current.update(clean)
            styles[field] = {k: v for k, v in current.items() if v not in {"", None}}
            obj.styles_json = json.dumps(styles, ensure_ascii=False)
            if hasattr(obj, "updated_at"):
                obj.updated_at = datetime.utcnow()
        db.session.commit()
        audit("live_edit_style", f"{target}.{field}{':' + str(target_id) if target_id else ''}")
        return jsonify({"ok": True})
    except Exception as exc:
        db.session.rollback()
        app.logger.exception("Live edit style failed: %s", exc)
        return jsonify({"ok": False, "error": f"Style save failed: {exc.__class__.__name__}."}), 500


def next_sort_order(model):
    row = model.query.order_by(model.sort_order.desc()).first()
    return (row.sort_order + 1) if row else 1


@app.route("/admin/live-edit/action", methods=["POST"])
@login_required
@require_role("owner")
def admin_live_edit_action():
    """Create/replace media from the Live Editor. Uses normal multipart forms for reliability."""
    action = (request.form.get("action") or "").strip()
    page = request.form.get("page") or request.args.get("page") or "home"
    try:
        if action == "create_service":
            title = request.form.get("title", "").strip() or "New service"
            obj = Service(title=title[:200], description=request.form.get("description", "").strip()[:5000], icon=request.form.get("icon", "building").strip() or "building", sort_order=next_sort_order(Service), is_active=True, is_published=True, published_at=datetime.utcnow())
            image = request.files.get("image")
            if image and image.filename:
                obj.image_path = save_upload(image, "service")
            db.session.add(obj)
            flash("Service added from Live Editor.", "success")
        elif action == "create_project":
            title = request.form.get("title", "").strip() or "New project"
            obj = Project(title=title[:220], location=request.form.get("location", "").strip()[:220], description=request.form.get("description", "").strip()[:12000], status=request.form.get("status", "Documented Work").strip()[:80], year=request.form.get("year", "").strip()[:20], sort_order=next_sort_order(Project), is_published=True, published_at=datetime.utcnow())
            image = request.files.get("image")
            if image and image.filename:
                obj.image_path = save_upload(image, "project")
            db.session.add(obj)
            flash("Project added from Live Editor.", "success")
        elif action == "create_gallery":
            image = request.files.get("image")
            if not image or not image.filename:
                flash("Gallery image is required.", "danger")
                return redirect(url_for("admin_live_edit", page="gallery"))
            path = save_upload(image, "gallery")
            obj = GalleryItem(title=(request.form.get("title", "").strip() or "Work photo")[:220], caption=request.form.get("caption", "").strip()[:5000], image_path=path, sort_order=next_sort_order(GalleryItem), is_published=True, published_at=datetime.utcnow())
            db.session.add(obj)
            flash("Gallery image added from Live Editor.", "success")
        elif action == "create_block":
            block = PageBlock(page=(request.form.get("block_page") or "home")[:80], block_type="text", title=request.form.get("title", "").strip()[:240], body=request.form.get("body", "").strip()[:12000], button_text=request.form.get("button_text", "").strip()[:160], button_url=request.form.get("button_url", "").strip(), sort_order=next_sort_order(PageBlock), is_published=True)
            image = request.files.get("image")
            if image and image.filename:
                block.image_path = save_upload(image, "block")
            db.session.add(block)
            flash("Homepage block added from Live Editor.", "success")
        elif action == "replace_image":
            target = request.form.get("target", "").strip()
            obj = live_edit_get_item(target, request.form.get("id", ""))
            image = request.files.get("image")
            if target not in {"service", "project", "gallery", "page_block"} or not obj:
                flash("Image target not found. Refresh Live Editor.", "danger")
                return redirect(url_for("admin_live_edit", page=page))
            if not image or not image.filename:
                flash("Choose an image first.", "danger")
                return redirect(url_for("admin_live_edit", page=page))
            if getattr(obj, "image_path", ""):
                delete_media(obj.image_path)
            obj.image_path = save_upload(image, target)
            if hasattr(obj, "updated_at"):
                obj.updated_at = datetime.utcnow()
            flash("Image replaced.", "success")
        else:
            flash("Unsupported Live Editor action.", "danger")
            return redirect(url_for("admin_live_edit", page=page))
        db.session.commit()
        audit("live_edit_action", action)
    except Exception as exc:
        db.session.rollback()
        app.logger.exception("Live editor action failed: %s", exc)
        flash(f"Live Editor action failed: {exc}", "danger")
    return redirect(url_for("admin_live_edit", page=page))


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


