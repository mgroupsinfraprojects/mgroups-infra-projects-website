# GST Invoice Audit portal integration for M-GROUPS.
# Executed by app.py in application globals.

from contextlib import contextmanager
from pathlib import Path
import json as _json
import mimetypes as _mimetypes
import sys as _sys

from werkzeug.utils import secure_filename as _secure_filename

_GST_ROOT = BASE_DIR / "modules" / "gst_audit"
_GST_STATIC_DIR = _GST_ROOT / "web_portal" / "static"
_GST_TEMPLATE = _GST_ROOT / "web_portal" / "templates" / "index.html"
_GST_REPORT_TEMPLATE = _GST_ROOT / "web_portal" / "templates" / "report.html"
_GST_RUNTIME_DIR = _GST_ROOT / "web_runtime"
_GST_SERVICE = None
_GST_IMPORT_ERROR = None
_GST_APP_PACKAGE = None
_MAIN_APP_MODULE = _sys.modules.get("app")


def _json_for_script(payload):
    return (
        _json.dumps(payload, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


@contextmanager
def _gst_import_context():
    """Temporarily expose GST's internal package as `app`.

    The GST audit project was originally a standalone app with imports like
    `from app.core...`. Our M-GROUPS website is also loaded as module `app` on
    Render. This context avoids that name conflict while GST code runs.
    """
    old_app = _sys.modules.get("app")
    old_path = list(_sys.path)
    root = str(_GST_ROOT)
    if root not in _sys.path:
        _sys.path.insert(0, root)
    try:
        if _GST_APP_PACKAGE is not None:
            _sys.modules["app"] = _GST_APP_PACKAGE
        else:
            _sys.modules.pop("app", None)
        yield
    finally:
        _sys.path = old_path
        if old_app is not None:
            _sys.modules["app"] = old_app
        else:
            _sys.modules.pop("app", None)


def _load_gst_service():
    global _GST_SERVICE, _GST_IMPORT_ERROR, _GST_APP_PACKAGE
    if _GST_SERVICE is not None or _GST_IMPORT_ERROR is not None:
        return _GST_SERVICE
    try:
        if not _GST_ROOT.exists():
            raise RuntimeError("modules/gst_audit folder is missing.")
        _GST_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        with _gst_import_context():
            import importlib
            gst_pkg = importlib.import_module("app")
            _GST_APP_PACKAGE = gst_pkg
            from web_portal.audit_service import WebAuditService
            _GST_SERVICE = WebAuditService(_GST_RUNTIME_DIR)
        return _GST_SERVICE
    except Exception as exc:
        _GST_IMPORT_ERROR = exc
        app.logger.exception("GST audit module load failed: %s", exc)
        return None


def _gst_user_payload():
    adm = current_admin()
    return {
        "authenticated": bool(adm),
        "username": adm.username if adm else "portal",
        "display_name": adm.username if adm else "Portal User",
        "role": adm.role if adm else "unknown",
        "permissions": {
            "view": has_permission("gst_view"),
            "upload": has_permission("gst_upload"),
            "review": has_permission("gst_edit"),
            "export": has_permission("gst_reports"),
            "clear": has_permission("gst_upload"),
            "audit_log": has_permission("gst_reports"),
        },
    }


def _gst_session_id():
    return session.get("gst_audit_session_id", "")


def _gst_dashboard_payload(error=""):
    service = _load_gst_service()
    if not service:
        return {
            "app_name": "GST Invoice Audit",
            "version": "module-error",
            "has_result": False,
            "error": str(_GST_IMPORT_ERROR or "GST module could not be loaded."),
            "user": _gst_user_payload(),
            "activity": [],
        }
    with _gst_import_context():
        payload = service.dashboard(_gst_session_id(), _gst_user_payload())
    if error:
        payload["error"] = error
    return payload


def _portalize_gst_html(html_text):
    replacements = {
        'href="/static/web.css"': 'href="/portal/gst/static/web.css"',
        'src="/static/web.js"': 'src="/portal/gst/static/web.js"',
        'href="/report"': 'href="/portal/gst/report"',
        'href="/export"': 'href="/portal/gst/export"',
        'href="/audit-log"': 'href="/portal/gst/audit-log"',
        'action="/audit"': 'action="/portal/gst/audit"',
        'action="/review"': 'action="/portal/gst/review"',
        'action="/clear"': 'action="/portal/gst/clear"',
        '<p class="eyebrow">No-login local web module</p>': '<p class="eyebrow">M-GROUPS protected portal module</p>',
        '<a href="#upload">Start Audit</a>': '<a href="/portal">← My Workspace</a><a href="#upload">Start Audit</a>',
    }
    for old, new in replacements.items():
        html_text = html_text.replace(old, new)
    return html_text


def _render_gst_index(error="", status=200):
    if not _GST_TEMPLATE.exists():
        return render_template("error.html", code=500, message="GST template is missing. Upload modules/gst_audit/web_portal/templates/index.html."), 500
    payload = _gst_dashboard_payload(error)
    html_text = _GST_TEMPLATE.read_text(encoding="utf-8")
    html_text = _portalize_gst_html(html_text)
    html_text = html_text.replace("{{DATA_JSON}}", _json_for_script(payload))
    html_text = html_text.replace("{{ERROR}}", str(error or payload.get("error", "")))
    return Response(html_text, status=status, content_type="text/html; charset=utf-8")


@app.route("/portal/gst/tool")
@login_required
@permission_required("gst_view")
def gst_audit_tool():
    return _render_gst_index()


@app.route("/portal/gst/api/summary")
@login_required
@permission_required("gst_view")
def gst_audit_summary_api():
    return jsonify(_gst_dashboard_payload())


@app.route("/portal/gst/static/<path:filename>")
@login_required
@permission_required("gst_view")
def gst_audit_static(filename):
    safe_path = (_GST_STATIC_DIR / filename).resolve()
    if not str(safe_path).startswith(str(_GST_STATIC_DIR.resolve())) or not safe_path.exists() or not safe_path.is_file():
        abort(404)
    mime = _mimetypes.guess_type(str(safe_path))[0] or "application/octet-stream"
    return Response(safe_path.read_bytes(), content_type=mime)


@app.route("/portal/gst/audit", methods=["POST"])
@login_required
@permission_required("gst_upload")
def gst_audit_upload():
    service = _load_gst_service()
    if not service:
        return _render_gst_index(str(_GST_IMPORT_ERROR or "GST module could not be loaded."), status=500)
    uploaded = []
    for storage in request.files.getlist("files"):
        if not storage or not storage.filename:
            continue
        name = _secure_filename(Path(storage.filename).name)
        uploaded.append((name, storage.read()))
    if not uploaded:
        return _render_gst_index("Please choose at least one Excel/CSV file.", status=400)
    try:
        user = _gst_user_payload()
        with _gst_import_context():
            audit_session = service.create_audit(uploaded, actor=user["username"], role=user["role"])
        session["gst_audit_session_id"] = audit_session.session_id
        audit("gst_audit_upload", f"GST audit uploaded by {admin_username()} with {len(uploaded)} file(s)")
        return redirect(url_for("gst_audit_tool"))
    except Exception as exc:
        app.logger.exception("GST audit upload failed: %s", exc)
        return _render_gst_index(str(exc), status=400)


@app.route("/portal/gst/review", methods=["POST"])
@login_required
@permission_required("gst_edit")
def gst_audit_review():
    service = _load_gst_service()
    if not service:
        return _render_gst_index(str(_GST_IMPORT_ERROR or "GST module could not be loaded."), status=500)
    session_id = _gst_session_id()
    if not session_id:
        return _render_gst_index("No active audit session. Upload files first.", status=400)
    action = request.form.get("action", "")
    note = request.form.get("note", "")
    row_ids = request.form.getlist("row_id")
    try:
        with _gst_import_context():
            if request.form.get("scope") == "all_review":
                from app.core.review_policy import is_mandatory_review
                current = service.get_session(session_id)
                if not current:
                    return _render_gst_index("Audit session not found. Upload files again.", status=400)
                web_rows = service._web_invoice_rows(current.result.rows)
                row_ids = [str(row.row_id) for row in web_rows if is_mandatory_review(row)]
            service.apply_decision(session_id, [int(v) for v in row_ids], action, note, actor=admin_username(), role=current_role() or "portal")
        audit("gst_audit_review", f"GST review decision {action} by {admin_username()}")
        return redirect(url_for("gst_audit_tool"))
    except Exception as exc:
        app.logger.exception("GST audit review failed: %s", exc)
        return _render_gst_index(str(exc), status=400)


@app.route("/portal/gst/export")
@login_required
@permission_required("gst_reports")
def gst_audit_export():
    service = _load_gst_service()
    session_id = _gst_session_id()
    if not service or not session_id:
        return _render_gst_index("No active audit session. Upload files first.", status=400)
    try:
        with _gst_import_context():
            path = service.export_session(session_id, actor=admin_username(), role=current_role() or "portal")
        audit("gst_audit_export", f"GST export downloaded by {admin_username()}")
        return send_file(path, as_attachment=True, download_name=path.name)
    except Exception as exc:
        app.logger.exception("GST export failed: %s", exc)
        return _render_gst_index(str(exc), status=400)


@app.route("/portal/gst/audit-log")
@login_required
@permission_required("gst_reports")
def gst_audit_log_export():
    service = _load_gst_service()
    if not service:
        return _render_gst_index(str(_GST_IMPORT_ERROR or "GST module could not be loaded."), status=500)
    with _gst_import_context():
        path = service.audit_log_csv()
    return send_file(path, as_attachment=True, download_name=path.name)


@app.route("/portal/gst/report")
@login_required
@permission_required("gst_reports")
def gst_audit_report():
    if not _GST_REPORT_TEMPLATE.exists():
        return render_template("error.html", code=500, message="GST report template is missing."), 500
    payload = _gst_dashboard_payload()
    html_text = _GST_REPORT_TEMPLATE.read_text(encoding="utf-8")
    html_text = _portalize_gst_html(html_text)
    html_text = html_text.replace("{{DATA_JSON}}", _json_for_script(payload))
    return Response(html_text, content_type="text/html; charset=utf-8")


@app.route("/portal/gst/clear", methods=["POST"])
@login_required
@permission_required("gst_upload")
def gst_audit_clear():
    service = _load_gst_service()
    session_id = _gst_session_id()
    if service and session_id:
        with _gst_import_context():
            service.delete_session(session_id, actor=admin_username(), role=current_role() or "portal")
    session.pop("gst_audit_session_id", None)
    audit("gst_audit_clear", f"GST audit session cleared by {admin_username()}")
    return redirect(url_for("gst_audit_tool"))
