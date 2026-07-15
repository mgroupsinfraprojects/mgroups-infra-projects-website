# Auto-split from app.py for readability. Executed by app.py in application globals.

# ─────────────────────────────────────────────────────────────
# Admin auth
# ─────────────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
@app.route("/admin/login", methods=["GET", "POST"])
@((limiter.limit("8 per minute")) if limiter else (lambda f: f))
def admin_login():
    if session.get("admin_id"):
        return redirect(url_for("portal_workspace"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = Admin.query.filter_by(username=username).first()
        if admin and not admin.is_active and check_password_hash(admin.password_hash, password):
            audit("login_blocked_disabled", username)
            flash("This admin account is disabled. Contact the owner account.", "danger")
            return render_template("admin/login.html")
        if admin and admin.is_active and check_password_hash(admin.password_hash, password):
            session.clear()
            session["admin_id"] = admin.id
            session["csrf_token"] = secrets.token_urlsafe(32)
            audit("login", "Admin logged in")
            return redirect(url_for("portal_workspace"))
        flash("Invalid username or password.", "danger")
    return render_template("admin/login.html")


@app.route("/admin/forgot-password", methods=["GET", "POST"])
@((limiter.limit("5 per hour")) if limiter else (lambda f: f))
def admin_forgot_password():
    if session.get("admin_id"):
        return redirect(url_for("portal_workspace"))
    if request.method == "POST":
        validate_csrf()
        username = request.form.get("username", "").strip()
        recovery_email = request.form.get("recovery_email", "").strip().lower()
        admin = Admin.query.filter_by(username=username).first() if username else None
        matched_email = False
        if admin and admin.is_active:
            registered_recovery = (admin.recovery_email or admin.email or "").strip().lower()
            matched_email = bool(registered_recovery and recovery_email and registered_recovery == recovery_email)
        if admin and admin.is_active and matched_email:
            if not smtp_settings():
                audit("password_reset_smtp_missing", username)
                flash("Recovery details matched, but SMTP email is not configured. Set SMTP environment variables, then try again.", "danger")
                return redirect(url_for("admin_forgot_password"))
            raw_token, _token_row = create_password_reset_token(admin)
            reset_url = url_for("admin_reset_password", token=raw_token, _external=True)
            try:
                if send_admin_reset_email(admin, reset_url):
                    audit("password_reset_email_sent", username)
                    flash("Password reset link sent to the registered recovery email.", "success")
                    return redirect(url_for("admin_login"))
            except Exception as exc:
                db.session.rollback()
                app.logger.exception("SMTP reset email failed for user %s: %s", username, exc)
            audit("password_reset_email_failed", username)
            flash("Reset email could not be sent. Check SMTP settings and recovery email, then try again.", "danger")
            return redirect(url_for("admin_forgot_password"))
        audit("password_reset_request_unmatched", username or "blank")
        flash("If the username and recovery email are correct, a reset link will be sent.", "success")
        return redirect(url_for("admin_login"))
    return render_template("admin/forgot_password.html")


@app.route("/admin/reset-password/<token>", methods=["GET", "POST"])
@((limiter.limit("12 per hour")) if limiter else (lambda f: f))
def admin_reset_password(token):
    token_hash = password_token_hash(token)
    token_row = PasswordResetToken.query.filter_by(token_hash=token_hash).first()
    if not token_row or not token_row.is_valid or not token_row.admin or not token_row.admin.is_active:
        flash("Reset link is invalid or expired. Request a new password reset link.", "danger")
        return redirect(url_for("admin_forgot_password"))
    if request.method == "POST":
        validate_csrf()
        new_password = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")
        if new_password != confirm:
            flash("New passwords do not match.", "danger")
        elif len(new_password) < 10:
            flash("Password must be at least 10 characters.", "danger")
        else:
            token_row.admin.password_hash = generate_password_hash(new_password)
            token_row.used_at = datetime.utcnow()
            db.session.commit()
            session.clear()
            audit("password_reset_completed", token_row.admin.username)
            flash("Password reset completed. Login with the new password.", "success")
            return redirect(url_for("admin_login"))
    return render_template("admin/reset_password.html", token=token)


@app.route("/logout")
@app.route("/admin/logout")
def admin_logout():
    audit("logout", "Admin logged out")
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin/mode/<mode>")
@login_required
def admin_set_mode(mode):
    session["admin_mode"] = "advanced" if mode == "advanced" else "simple"
    flash(("Advanced mode enabled." if session["admin_mode"] == "advanced" else "Simple mode enabled."), "success")
    return redirect(request.referrer or url_for("admin_dashboard"))


@app.route("/admin")
@login_required
def admin_dashboard():
    # V15.6.3: /admin is a developer/system dashboard only.
    # Managers, supervisors, viewers and normal business users must stay in /portal
    # and only see the modules/actions permitted for their role.
    if not has_permission("system_settings"):
        flash("Admin production dashboard is restricted. Use My Workspace for your assigned tools.", "warning")
        return redirect(url_for("portal_workspace"))

    counts = {
        "services": Service.query.count(),
        "projects": Project.query.count(),
        "gallery": GalleryItem.query.count(),
        "published_gallery": public_gallery().count(),
        "projects_without_images": Project.query.filter((Project.image_path == None) | (Project.image_path == "")).count(),
        "unread": Enquiry.query.filter_by(is_read=False).count(),
    }
    enquiries = Enquiry.query.order_by(Enquiry.id.desc()).limit(8).all()
    logs = AuditLog.query.order_by(AuditLog.id.desc()).limit(8).all()
    return render_template("admin/dashboard.html", counts=counts, enquiries=enquiries, logs=logs)



