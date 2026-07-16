"""Compatibility import for older scripts.

New code should import DashboardControllerMixin from app.ui.controllers.dashboard_controller.
"""

from app.ui.controllers.dashboard_controller import DashboardControllerMixin

__all__ = ["DashboardControllerMixin"]
