"""Readable theme/admin display facade.

This facade avoids importing PySide6 until ThemeManager is requested.
"""

DEFAULT_THEME = "Professional Blue"
DEFAULT_FONT_SIZE = 10
DEFAULT_DENSITY = "Comfortable"
THEMES = {
    "Professional Blue": "default office theme",
    "Professional Light": "bright office theme",
    "Professional Dark": "low-light theme",
    "Audit High Contrast": "error-checking theme",
    "Custom Theme": "firm branding theme",
}


def __getattr__(name: str):
    if name == "ThemeManager":
        from app.ui.theme_manager import ThemeManager

        return ThemeManager
    raise AttributeError(name)


__all__ = ["DEFAULT_DENSITY", "DEFAULT_FONT_SIZE", "DEFAULT_THEME", "THEMES", "ThemeManager"]
