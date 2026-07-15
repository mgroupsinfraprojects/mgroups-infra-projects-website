# Auto-split from app.py for readability. Executed by app.py in application globals.

# ─────────────────────────────────────────────────────────────
# Stock module mount
# ─────────────────────────────────────────────────────────────
# The stock system lives in modules/stock with its original filenames kept intact.
# It is mounted under /portal/stock so it uses the same M-GROUPS login/session.

def _mount_stock_module():
    try:
        import importlib.util
        import sys
        from werkzeug.middleware.dispatcher import DispatcherMiddleware

        stock_dir = BASE_DIR / "modules" / "stock"
        stock_app_file = stock_dir / "app.py"
        if not stock_app_file.exists():
            app.logger.warning("Stock module not mounted: %s missing", stock_app_file)
            return

        # Stock app uses legacy absolute imports: extensions, config, models, services, time_utils.
        # Load it with the stock folder at the front of sys.path, without renaming its files.
        legacy_names = ["extensions", "config", "models", "services", "time_utils"]
        previous = {name: sys.modules.get(name) for name in legacy_names}
        for name in legacy_names:
            sys.modules.pop(name, None)

        sys.path.insert(0, str(stock_dir))
        try:
            spec = importlib.util.spec_from_file_location("mgroups_stock_portal_app", stock_app_file)
            stock_module = importlib.util.module_from_spec(spec)
            assert spec and spec.loader
            spec.loader.exec_module(stock_module)
            stock_app = getattr(stock_module, "app", None) or stock_module.create_app()
            stock_app.config["SECRET_KEY"] = app.config["SECRET_KEY"]
            stock_app.config["SESSION_COOKIE_HTTPONLY"] = True
            stock_app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
            stock_app.config["SESSION_COOKIE_SECURE"] = app.config.get("SESSION_COOKIE_SECURE", False)
            app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
                "/portal/stock": stock_app.wsgi_app,
            })
            app.logger.info("Stock module mounted at /portal/stock")
        finally:
            try:
                sys.path.remove(str(stock_dir))
            except ValueError:
                pass
            # Restore any previous same-named modules to avoid polluting the main website runtime.
            for name, module in previous.items():
                if module is not None:
                    sys.modules[name] = module
                else:
                    sys.modules.pop(name, None)
    except Exception as exc:
        app.logger.exception("Stock module mount failed: %s", exc)


_mount_stock_module()
