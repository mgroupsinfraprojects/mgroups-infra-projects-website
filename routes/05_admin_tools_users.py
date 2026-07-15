# Auto-split from app.py for readability. Executed by app.py in application globals.

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
    return render_template("admin/media.html", images=local_media_images(), cloudinary_ready=cloudinary_ready(), cloudinary_status_message=cloudinary_status()[1])


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
@permission_required("roles_manage")
def admin_permissions():
    selected_role = request.values.get("role") or MANAGEABLE_PERMISSION_ROLES[0]
    if selected_role not in MANAGEABLE_PERMISSION_ROLES:
        selected_role = MANAGEABLE_PERMISSION_ROLES[0]

    if request.method == "POST":
        validate_csrf()
        # Save only the selected role instead of rendering/saving every role at once.
        # This keeps the page small and faster on Render Free.
        for permission in ALL_PERMISSION_KEYS:
            set_setting(permission_setting_key(selected_role, permission), "1" if request.form.get(f"perm__{selected_role}__{permission}") else "0")
        db.session.commit()
        audit("role_permissions_update", f"Updated {selected_role} permissions by {admin_username()}")
        flash(f"{role_label(selected_role)} permissions saved. Users update on next page load/login.", "success")
        return redirect(url_for("admin_permissions", role=selected_role))

    role_modules = {role: role_allowed_module_titles(role) for role in MANAGEABLE_PERMISSION_ROLES}
    selected_map = role_permission_map(selected_role)
    return render_template(
        "admin/permissions.html",
        roles=MANAGEABLE_PERMISSION_ROLES,
        selected_role=selected_role,
        selected_map=selected_map,
        role_modules=role_modules,
        groups=PERMISSION_GROUPS,
        role_label=role_label,
    )

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
@permission_required("users_view")
def admin_users():
    if request.method == "POST":
        if not has_permission("users_create"):
            flash("Your role can view users, but cannot create new users.", "danger")
            return redirect(url_for("admin_users"))
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        email = request.form.get("email", "").strip()
        recovery_email = request.form.get("recovery_email", "").strip()
        role = request.form.get("role", "viewer")
        if not can_create_role(role):
            flash("Your account cannot create that role.", "danger")
            return redirect(url_for("admin_users"))
        if not username or len(password) < 10:
            flash("Username and password of at least 10 characters are required.", "danger")
            return redirect(url_for("admin_users"))
        if Admin.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for("admin_users"))
        db.session.add(Admin(username=username, email=email, recovery_email=recovery_email, password_hash=generate_password_hash(password), role=role, is_active=True))
        db.session.commit()
        audit("admin_user_create", username)
        flash("Admin user created.", "success")
        return redirect(url_for("admin_users"))
    page = request.args.get("page", 1)
    pagination = paginate_query(visible_users_query_for_current_user(), page=page, per_page=10)
    users = pagination.items
    return render_template(
        "admin/users.html",
        users=users,
        pagination=pagination,
        creatable_roles=creatable_roles_for_current_user() if has_permission("users_create") else [],
        role_label=role_label,
        user_allowed_module_titles=user_allowed_module_titles,
        can_manage_user_account=can_manage_user_account,
        has_permission=has_permission,
    )


def _active_owner_count(exclude_user_id=None):
    query = Admin.query.filter(Admin.role.in_(["developer", "owner"]), Admin.is_active == True)
    if exclude_user_id is not None:
        query = query.filter(Admin.id != exclude_user_id)
    return query.count()


@app.route("/admin/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("users_edit")
def admin_user_edit(user_id):
    user = Admin.query.get_or_404(user_id)
    if not can_manage_user_account(user) and user.id != session.get("admin_id"):
        flash("Your role cannot edit this user.", "danger")
        return redirect(url_for("admin_users"))
    if request.method == "POST":
        validate_csrf()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        recovery_email = request.form.get("recovery_email", "").strip()
        role = request.form.get("role", "viewer")
        is_active = request.form.get("is_active") == "1"
        new_password = request.form.get("password", "")
        if role != user.role and not can_create_role(role):
            flash("Your account cannot assign that role.", "danger")
            return redirect(url_for("admin_user_edit", user_id=user.id))
        if not username:
            flash("Username is required.", "danger")
            return redirect(url_for("admin_user_edit", user_id=user.id))
        duplicate = Admin.query.filter(Admin.username == username, Admin.id != user.id).first()
        if duplicate:
            flash("Username already exists.", "danger")
            return redirect(url_for("admin_user_edit", user_id=user.id))
        if user.id == session.get("admin_id"):
            if not is_active:
                flash("You cannot disable your own account.", "danger")
                return redirect(url_for("admin_user_edit", user_id=user.id))
            if role not in {"developer", "owner"}:
                flash("You cannot remove full-control role from your own account.", "danger")
                return redirect(url_for("admin_user_edit", user_id=user.id))
        if user.role in {"developer", "owner"} and user.is_active and (role not in {"developer", "owner"} or not is_active) and _active_owner_count(exclude_user_id=user.id) < 1:
            flash("At least one active owner account is required.", "danger")
            return redirect(url_for("admin_user_edit", user_id=user.id))
        if new_password and len(new_password) < 10:
            flash("New password must be at least 10 characters.", "danger")
            return redirect(url_for("admin_user_edit", user_id=user.id))
        old_username = user.username
        user.username = username
        user.email = email
        user.recovery_email = recovery_email
        user.role = role
        user.is_active = is_active
        if new_password:
            user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        if new_password:
            audit("admin_user_manual_password_reset", f"{old_username} password updated by owner")
        audit("admin_user_edit", f"{old_username} -> {username}")
        flash("Admin user updated. If a new password was entered, the user can login with that password immediately. No email is required for this manual reset.", "success")
        return redirect(url_for("admin_users"))
    role_options = creatable_roles_for_current_user()
    if user.role and user.role not in [r for r, _label in role_options]:
        role_options = [(user.role, role_label(user.role))] + role_options
    return render_template("admin/user_edit.html", user=user, role_options=role_options or [(user.role, role_label(user.role))], role_label=role_label, user_allowed_module_titles=user_allowed_module_titles(user), can_manage_role=(user.id != session.get("admin_id")))


@app.route("/admin/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@permission_required("users_edit")
def admin_user_toggle(user_id):
    validate_csrf()
    user = Admin.query.get_or_404(user_id)
    if not can_manage_user_account(user):
        flash("Your role cannot change this user.", "danger")
        return redirect(url_for("admin_users"))
    if user.id == session.get("admin_id"):
        flash("You cannot disable your own account.", "danger")
        return redirect(url_for("admin_users"))
    if user.is_active and user.role in {"developer", "owner"} and _active_owner_count(exclude_user_id=user.id) < 1:
        flash("At least one active owner account is required.", "danger")
        return redirect(url_for("admin_users"))
    user.is_active = not user.is_active
    db.session.commit()
    audit("admin_user_toggle", user.username)
    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@login_required
@permission_required("users_delete")
def admin_user_delete(user_id):
    validate_csrf()
    user = Admin.query.get_or_404(user_id)
    if not can_manage_user_account(user):
        flash("Your role cannot delete this user.", "danger")
        return redirect(url_for("admin_users"))
    if user.id == session.get("admin_id"):
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("admin_users"))
    if user.role in {"developer", "owner"} and user.is_active and _active_owner_count(exclude_user_id=user.id) < 1:
        flash("At least one active owner account is required.", "danger")
        return redirect(url_for("admin_users"))
    username = user.username
    PasswordResetToken.query.filter_by(admin_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    audit("admin_user_delete", username)
    flash("Admin user deleted.", "success")
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


