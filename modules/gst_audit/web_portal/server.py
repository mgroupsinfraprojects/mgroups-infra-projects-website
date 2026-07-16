from __future__ import annotations

import json
import mimetypes
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app.core.review_policy import is_mandatory_review
from app.version import APP_VERSION
from web_portal.audit_service import WebAuditError, WebAuditService

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "web_portal" / "templates" / "index.html"
REPORT_TEMPLATE = ROOT / "web_portal" / "templates" / "report.html"
STATIC_DIR = ROOT / "web_portal" / "static"
SERVICE = WebAuditService(ROOT / "web_runtime")

LOCAL_USER_PAYLOAD = {
    "authenticated": True,
    "username": "local",
    "display_name": "Local Operator",
    "role": "operator",
    "permissions": {
        "view": True,
        "upload": True,
        "review": True,
        "export": True,
        "clear": True,
        "audit_log": True,
    },
}


def json_for_script(payload: object) -> str:
    """Return JSON safe to embed in <script type=application/json>."""
    return (
        json.dumps(payload, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def parse_multipart(body: bytes, content_type: str) -> tuple[dict[str, str], list[tuple[str, bytes]]]:
    match = re.search(r"boundary=(?:\"([^\"]+)\"|([^;]+))", content_type)
    if not match:
        raise WebAuditError("Invalid upload request: multipart boundary missing.")
    boundary = (match.group(1) or match.group(2)).encode("utf-8")
    delimiter = b"--" + boundary
    fields: dict[str, str] = {}
    files: list[tuple[str, bytes]] = []
    for raw_part in body.split(delimiter):
        part = raw_part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        if part.endswith(b"--"):
            part = part[:-2].rstrip(b"\r\n")
        header_blob, separator, payload = part.partition(b"\r\n\r\n")
        if not separator:
            continue
        headers = header_blob.decode("utf-8", errors="replace").split("\r\n")
        disposition = next((h for h in headers if h.lower().startswith("content-disposition:")), "")
        name_match = re.search(r'name="([^"]+)"', disposition)
        filename_match = re.search(r'filename="([^"]*)"', disposition)
        field_name = name_match.group(1) if name_match else ""
        if filename_match:
            filename = Path(filename_match.group(1)).name
            if filename:
                files.append((filename, payload.rstrip(b"\r\n")))
        elif field_name:
            fields[field_name] = payload.decode("utf-8", errors="replace").strip()
    return fields, files


class GSTAuditHandler(BaseHTTPRequestHandler):
    server_version = "GSTAuditWeb/11.13.0"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/healthz":
                self._send_json({"ok": True, "version": "11.13.0", "login_required": False})
            elif parsed.path.startswith("/static/"):
                self._serve_static(parsed.path.removeprefix("/static/"))
            elif parsed.path in {"/login", "/logout"}:
                self._redirect("/")
            elif parsed.path == "/api/summary":
                self._send_json(SERVICE.dashboard(self._cookie("gst_session"), LOCAL_USER_PAYLOAD))
            elif parsed.path == "/export":
                self._handle_export()
            elif parsed.path == "/audit-log":
                self._handle_audit_log()
            elif parsed.path == "/report":
                self._handle_report()
            elif parsed.path == "/":
                self._render_index(SERVICE.dashboard(self._cookie("gst_session"), LOCAL_USER_PAYLOAD))
            else:
                self.send_error(HTTPStatus.NOT_FOUND, "Page not found")
        except WebAuditError as exc:
            self._render_index(SERVICE.dashboard(self._cookie("gst_session"), LOCAL_USER_PAYLOAD), error=str(exc), status=HTTPStatus.BAD_REQUEST)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/audit":
                self._handle_audit_upload()
            elif parsed.path == "/review":
                self._handle_review_decision()
            elif parsed.path == "/clear":
                self._handle_clear()
            elif parsed.path == "/login":
                self._redirect("/")
            else:
                self.send_error(HTTPStatus.NOT_FOUND, "Page not found")
        except WebAuditError as exc:
            self._render_index(SERVICE.dashboard(self._cookie("gst_session"), LOCAL_USER_PAYLOAD), error=str(exc), status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # pragma: no cover
            self._render_index(SERVICE.dashboard(self._cookie("gst_session"), LOCAL_USER_PAYLOAD), error=f"Unexpected server error: {exc}", status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_audit_upload(self) -> None:
        content_type = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            raise WebAuditError("No upload body received.")
        if length > 260 * 1024 * 1024:
            raise WebAuditError("Upload request exceeds 260 MB limit.")
        _fields, files = parse_multipart(self.rfile.read(length), content_type)
        session = SERVICE.create_audit(files, actor="local", role="operator")
        self._redirect("/", gst_cookie=session.session_id)

    def _handle_review_decision(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        form = parse_qs(body)
        session_id = self._cookie("gst_session")
        if not session_id:
            raise WebAuditError("No active audit session. Upload files first.")
        action = (form.get("action") or [""])[0]
        note = (form.get("note") or [""])[0]
        row_ids = form.get("row_id") or []
        if (form.get("scope") or [""])[0] == "all_review":
            session = SERVICE.get_session(session_id)
            if not session:
                raise WebAuditError("Audit session not found. Upload files again.")
            web_rows = SERVICE._web_invoice_rows(session.result.rows)
            row_ids = [str(row.row_id) for row in web_rows if is_mandatory_review(row)]
        SERVICE.apply_decision(session_id, [int(value) for value in row_ids], action, note, actor="local", role="operator")
        self._redirect("/")

    def _handle_export(self) -> None:
        session_id = self._cookie("gst_session")
        if not session_id:
            self._render_index(SERVICE.dashboard(None, LOCAL_USER_PAYLOAD), error="No active audit session. Upload files first.", status=HTTPStatus.BAD_REQUEST)
            return
        path = SERVICE.export_session(session_id, actor="local", role="operator")
        payload = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self._security_headers()
        self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.end_headers()
        self.wfile.write(payload)

    def _handle_audit_log(self) -> None:
        path = SERVICE.audit_log_csv()
        payload = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self._security_headers()
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.end_headers()
        self.wfile.write(payload)

    def _handle_report(self) -> None:
        session_id = self._cookie("gst_session")
        payload = SERVICE.dashboard(session_id, LOCAL_USER_PAYLOAD)
        html_text = REPORT_TEMPLATE.read_text(encoding="utf-8")
        html_text = html_text.replace("{{DATA_JSON}}", json_for_script(payload))
        self._send_html(html_text)

    def _handle_clear(self) -> None:
        session_id = self._cookie("gst_session")
        if session_id:
            SERVICE.delete_session(session_id, actor="local", role="operator")
        self._redirect("/", gst_cookie="")

    def _render_index(self, payload: object, error: str = "", status: HTTPStatus = HTTPStatus.OK) -> None:
        html_text = TEMPLATE.read_text(encoding="utf-8")
        html_text = html_text.replace("{{DATA_JSON}}", json_for_script(payload))
        html_text = html_text.replace("{{ERROR}}", self._escape(error))
        self._send_html(html_text, status=status)

    def _serve_static(self, relative: str) -> None:
        safe_path = (STATIC_DIR / relative).resolve()
        if not str(safe_path).startswith(str(STATIC_DIR.resolve())) or not safe_path.exists() or not safe_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Static file not found")
            return
        payload = safe_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self._security_headers()
        content_type = mimetypes.guess_type(str(safe_path))[0] or "application/octet-stream"
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_html(self, body: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self._security_headers()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._security_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location: str, gst_cookie: str | None = None) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self._security_headers()
        if gst_cookie is not None:
            if gst_cookie:
                self.send_header("Set-Cookie", f"gst_session={gst_cookie}; Path=/; HttpOnly; SameSite=Lax")
            else:
                self.send_header("Set-Cookie", "gst_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax")
        self.send_header("Location", location)
        self.end_headers()

    def _cookie(self, name: str) -> str:
        raw = self.headers.get("Cookie", "")
        for part in raw.split(";"):
            key, _, value = part.strip().partition("=")
            if key == name:
                return value
        return ""

    def _security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Cache-Control", "no-store")

    @staticmethod
    def _escape(value: str) -> str:
        return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003 - stdlib API
        return


def run(host: str = "127.0.0.1", port: int = 8088) -> None:
    server = ThreadingHTTPServer((host, port), GSTAuditHandler)
    print(f"GST Audit Pro web mode running at http://{host}:{port}")
    print("Login is disabled in this local web module. Add your own portal login before exposing it online.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover
        pass
    finally:
        server.server_close()
