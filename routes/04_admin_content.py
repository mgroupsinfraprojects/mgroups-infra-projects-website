# Auto-split from app.py for readability. Executed by app.py in application globals.

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
    service.styles_json = collect_item_styles("service", service)
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
    project.styles_json = collect_item_styles("project", project)
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


@app.route("/admin/cloudinary-test", methods=["POST"])
@login_required
def admin_cloudinary_test():
    ok, detail = cloudinary_status()
    if not ok:
        flash("Cloudinary test failed: " + detail, "danger")
        return redirect(request.referrer or url_for("admin_gallery"))
    if Image is None:
        flash("Cloudinary test failed: Pillow is unavailable.", "danger")
        return redirect(request.referrer or url_for("admin_gallery"))
    test_path = UPLOAD_DIR / f"cloudinary_test_{uuid.uuid4().hex}.png"
    try:
        Image.new("RGB", (4, 4), color=(20, 90, 140)).save(test_path)
        result = cloudinary.uploader.upload(
            str(test_path),
            folder=os.environ.get("CLOUDINARY_FOLDER", "mgroups"),
            public_id=f"healthcheck_{uuid.uuid4().hex[:8]}",
            overwrite=False,
            resource_type="image",
        )
        url = result.get("secure_url") or result.get("url")
        public_id = result.get("public_id")
        if public_id:
            try:
                cloudinary.uploader.destroy(public_id, invalidate=True, resource_type="image")
            except Exception:
                pass
        if not url:
            raise ValueError("Cloudinary accepted upload but returned no URL.")
        flash("Cloudinary test passed. New uploads should save to Cloudinary.", "success")
    except Exception as exc:
        flash(f"Cloudinary test failed: {exc}", "danger")
    finally:
        try:
            test_path.unlink(missing_ok=True)
        except Exception:
            pass
    return redirect(request.referrer or url_for("admin_gallery"))


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
    return render_template("admin/gallery.html", items=items, cloudinary_ready=cloudinary_ready(), cloudinary_status_message=cloudinary_status()[1])


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
            try:
                if BOOTSTRAP_PASSWORD_FILE.exists():
                    BOOTSTRAP_PASSWORD_FILE.unlink()
            except Exception:
                pass
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
@require_role("owner")
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
@require_role("owner")
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




