from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v89_live_suggestions_reopen_on_every_text_edit():
    source = (ROOT / "app/ui/widgets/guided_filter.py").read_text(encoding="utf-8")
    version_source = (ROOT / "app/version.py").read_text(encoding="utf-8")

    assert "APP_VERSION = " in version_source
    assert 'APP_VERSION = "9.3.0"' not in version_source
    assert "from PySide6.QtCore import QEvent, QTimer, Qt, Signal" in source
    assert "self.search_edit.textEdited.connect(self._user_search_text_edited)" in source
    assert "QTimer.singleShot(0, self._show_inline_suggestions)" in source
    assert "event.type() == QEvent.Type.KeyRelease" in source
    assert "self._inline_popup.raise_()" in source


def test_v89_full_picker_query_is_mirrored_and_cancel_safe():
    source = (ROOT / "app/ui/widgets/guided_filter.py").read_text(encoding="utf-8")

    assert "query_changed = Signal(str)" in source
    assert "self.search_edit.textEdited.connect(self.query_changed.emit)" in source
    assert "popup.query_changed.connect" in source
    assert "def _mirror_popup_query" in source
    assert "old_query = self._query_by_field.get(key" in source
    assert "Cancel must not" in source
    assert "self._query_by_field[key] = old_query" in source
