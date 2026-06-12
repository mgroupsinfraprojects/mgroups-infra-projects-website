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
