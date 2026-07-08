import re


def test_public_pages_load(client):
    for path in ["/", "/about", "/services", "/projects", "/gallery", "/contact", "/service-areas", "/privacy-policy", "/terms"]:
        res = client.get(path)
        assert res.status_code == 200, path


def test_healthz(client):
    res = client.get("/healthz")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert data["database"] is True


def test_sitemap_and_robots(client):
    assert client.get("/robots.txt").status_code == 200
    res = client.get("/sitemap.xml")
    assert res.status_code == 200
    assert b"<urlset" in res.data


def test_contact_requires_csrf(client):
    res = client.post("/contact", data={"name": "A", "message": "hello there"})
    assert res.status_code == 400


def test_contact_submit_with_csrf(client):
    page = client.get("/contact")
    token = re.search(rb'name="csrf_token" value="([^"]+)"', page.data).group(1).decode()
    res = client.post("/contact", data={"csrf_token": token, "name": "Client", "phone": "9999999999", "project_type": "Civil work", "message": "Need a project estimate for site work."}, follow_redirects=True)
    assert res.status_code == 200
    assert b"submitted" in res.data.lower()


def _csrf_from(page):
    return re.search(rb'name="csrf_token" value="([^"]+)"', page.data).group(1).decode()


def test_disabled_admin_cannot_login(client):
    from app import Admin, db
    from werkzeug.security import generate_password_hash
    with client.application.app_context():
        user = Admin(username="disabled_user", password_hash=generate_password_hash("StrongPass123!"), role="viewer", is_active=False)
        db.session.add(user)
        db.session.commit()

    page = client.get("/admin/login")
    token = _csrf_from(page)
    res = client.post("/admin/login", data={"csrf_token": token, "username": "disabled_user", "password": "StrongPass123!"}, follow_redirects=True)
    assert res.status_code == 200
    assert b"disabled" in res.data.lower()
    assert client.get("/admin").status_code in (302, 401, 403)


def test_login_page_has_forgot_password_link(client):
    res = client.get("/admin/login")
    assert res.status_code == 200
    assert b"Forgot password" in res.data
    assert b"/admin/forgot-password" in res.data


def test_admin_reset_password_token_flow(client):
    from datetime import datetime, timedelta
    from app import Admin, PasswordResetToken, db, password_token_hash

    raw_token = "unit-test-reset-token"
    with client.application.app_context():
        admin = Admin.query.filter_by(username="admin").first()
        assert admin is not None
        db.session.add(PasswordResetToken(
            admin_id=admin.id,
            token_hash=password_token_hash(raw_token),
            expires_at=datetime.utcnow() + timedelta(minutes=30),
            requested_ip="test",
        ))
        db.session.commit()

    page = client.get(f"/admin/reset-password/{raw_token}")
    assert page.status_code == 200
    token = _csrf_from(page)
    res = client.post(
        f"/admin/reset-password/{raw_token}",
        data={"csrf_token": token, "new_password": "NewStrongPass123!", "confirm_password": "NewStrongPass123!"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"password reset completed" in res.data.lower()

    page = client.get("/admin/login")
    csrf = _csrf_from(page)
    login = client.post(
        "/admin/login",
        data={"csrf_token": csrf, "username": "admin", "password": "NewStrongPass123!"},
        follow_redirects=False,
    )
    assert login.status_code == 302
