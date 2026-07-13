# Auto-split from app.py for readability. Executed by app.py in application globals.

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
        "cloudinary_configured": cloudinary_ready(),
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


