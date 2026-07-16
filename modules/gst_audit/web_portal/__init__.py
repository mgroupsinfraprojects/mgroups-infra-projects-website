"""Browser/web wrapper for the GST Audit Pro core engine.

The desktop app remains PySide6-based. This package provides a small standard-library
HTTP server and a reusable service layer so the same audit core can be used from a
browser or later mounted inside the M-Groups Flask portal.
"""

from web_portal.audit_service import WebAuditService

__all__ = ["WebAuditService"]
