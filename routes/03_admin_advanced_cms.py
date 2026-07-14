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
    }
    template, extra = template_map.get(page, template_map["home"])
    return render_template(template, **overrides, **extra)


@app.route("/admin/live-edit")
@login_required
@require_role("owner")
def admin_live_edit():
    """Render the real public pages with inline-edit controls for owner users."""
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


@app.route("/admin/live-edit/save", methods=["POST"])
@login_required
@require_role("owner")
def admin_live_edit_save():
    """Save one inline-edit field from the live-edit overlay."""
    data = request.get_json(silent=True) or {}
    target = (data.get("target") or "").strip()
    field = (data.get("field") or "").strip()
    target_id = data.get("id") or ""
    value = (data.get("value") or "").strip()

    if not target or not field:
        return jsonify({"ok": False, "error": "Missing edit target."}), 400

    setting_fields = {name for name, _label, _default in SETTINGS_FIELD_LABELS}
    appearance_fields = set(APPEARANCE_FIELDS)
    about_fields = {name for name, _label, _default in ABOUT_FIELD_LABELS}
    service_fields = {"title", "description", "icon"}
    project_fields = {"title", "location", "category", "status", "year", "client_type", "site_area", "duration", "project_value", "scope_of_work", "challenge", "solution", "outcome", "description"}
    gallery_fields = {"title", "caption"}
    required_title_targets = {"service", "project", "gallery"}

    try:
        if target == "setting":
            if field not in setting_fields:
                return jsonify({"ok": False, "error": "This settings field cannot be edited inline."}), 400
            set_setting(field, value[:5000])
        elif target == "appearance":
            if field not in appearance_fields:
                return jsonify({"ok": False, "error": "This appearance label cannot be edited inline."}), 400
            set_setting(field, value[:5000])
        elif target == "about":
            if field not in about_fields:
                return jsonify({"ok": False, "error": "This about field cannot be edited inline."}), 400
            about = AboutContent.query.get(1)
            setattr(about, field, value[:12000])
        elif target == "service":
            if field not in service_fields:
                return jsonify({"ok": False, "error": "This service field cannot be edited inline."}), 400
            obj = Service.query.get(int(target_id))
            if not obj:
                return jsonify({"ok": False, "error": "Service not found."}), 404
            if field == "title" and not value:
                return jsonify({"ok": False, "error": "Service title cannot be blank."}), 400
            setattr(obj, field, value[:5000])
            obj.updated_at = datetime.utcnow()
        elif target == "project":
            if field not in project_fields:
                return jsonify({"ok": False, "error": "This project field cannot be edited inline."}), 400
            obj = Project.query.get(int(target_id))
            if not obj:
                return jsonify({"ok": False, "error": "Project not found."}), 404
            if field == "title" and not value:
                return jsonify({"ok": False, "error": "Project title cannot be blank."}), 400
            setattr(obj, field, value[:12000])
            obj.updated_at = datetime.utcnow()
        elif target == "gallery":
            if field not in gallery_fields:
                return jsonify({"ok": False, "error": "This gallery field cannot be edited inline."}), 400
            obj = GalleryItem.query.get(int(target_id))
            if not obj:
                return jsonify({"ok": False, "error": "Gallery item not found."}), 404
            if field == "title" and not value:
                return jsonify({"ok": False, "error": "Gallery title cannot be blank."}), 400
            setattr(obj, field, value[:5000])
            obj.updated_at = datetime.utcnow()
        else:
            return jsonify({"ok": False, "error": "Unsupported edit target."}), 400

        db.session.commit()
        audit("live_edit_save", f"{target}.{field}{':' + str(target_id) if target_id else ''}")
        return jsonify({"ok": True, "value": value})
    except Exception as exc:
        db.session.rollback()
        app.logger.exception("Live edit save failed: %s", exc)
        return jsonify({"ok": False, "error": "Save failed. Refresh and try again."}), 500


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


