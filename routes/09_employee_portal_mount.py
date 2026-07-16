# M-GROUPS Employee module mount. Executed by app.py in application globals.
# V16.4: mounts the construction Employee/Payroll ERP under /portal/employees/app
# without renaming the original employee module files.


def _mount_employee_module():
    try:
        import importlib.util
        import sys
        from flask import abort as emp_abort, redirect as emp_redirect, request as emp_request, session as emp_session
        from werkzeug.middleware.dispatcher import DispatcherMiddleware

        employee_dir = BASE_DIR / "modules" / "employees"
        employee_app_file = employee_dir / "app.py"
        if not employee_app_file.exists():
            app.logger.warning("Employee module not mounted: %s missing", employee_app_file)
            return

        # Employee ERP uses legacy absolute imports: models, services.
        # Keep its original filenames but isolate the import from stock/main modules.
        legacy_names = ["models", "services"]
        previous = {name: sys.modules.get(name) for name in legacy_names}
        for name in legacy_names:
            sys.modules.pop(name, None)

        sys.path.insert(0, str(employee_dir))
        try:
            spec = importlib.util.spec_from_file_location("mgroups_employee_portal_app", employee_app_file)
            employee_module = importlib.util.module_from_spec(spec)
            assert spec and spec.loader
            spec.loader.exec_module(employee_module)
            employee_app = getattr(employee_module, "app", None) or employee_module.create_app()
            employee_app.config["SECRET_KEY"] = app.config["SECRET_KEY"]
            employee_app.config["SESSION_COOKIE_HTTPONLY"] = True
            employee_app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
            employee_app.config["SESSION_COOKIE_SECURE"] = app.config.get("SESSION_COOKIE_SECURE", False)

            locked_roles = {
                "developer", "owner", "admin", "super_admin", "administrator",
                "developer_owner", "developer_owner_legacy",
            }

            def _emp_has(permission: str) -> bool:
                role = (emp_session.get("admin_role") or emp_session.get("user_role") or "").lower()
                perms = set(emp_session.get("portal_permissions") or [])
                return role in locked_roles or "*" in perms or permission in perms

            @employee_app.before_request
            def _employee_portal_guard():
                # Static files are not sensitive. Data pages/actions are protected.
                if emp_request.endpoint == "static":
                    return None
                if not emp_session.get("admin_id"):
                    return emp_redirect("/admin/login")
                if not _emp_has("employees_view"):
                    return emp_abort(403)

                endpoint = emp_request.endpoint or ""
                if endpoint in {"export_employees", "export_payroll"} and not _emp_has("employees_reports"):
                    return emp_abort(403)
                if endpoint in {"delete_employee", "deactivate_employee", "delete_site"} and not _emp_has("employees_delete"):
                    return emp_abort(403)
                if emp_request.method not in {"GET", "HEAD", "OPTIONS"}:
                    if not (_emp_has("employees_edit") or _emp_has("employees_add")):
                        return emp_abort(403)
                return None

            app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
                "/portal/employees/app": employee_app.wsgi_app,
            })
            app.logger.info("Employee module mounted at /portal/employees/app")
        finally:
            try:
                sys.path.remove(str(employee_dir))
            except ValueError:
                pass
            for name, module in previous.items():
                if module is not None:
                    sys.modules[name] = module
                else:
                    sys.modules.pop(name, None)
    except Exception as exc:
        app.logger.exception("Employee module mount failed: %s", exc)


_mount_employee_module()
