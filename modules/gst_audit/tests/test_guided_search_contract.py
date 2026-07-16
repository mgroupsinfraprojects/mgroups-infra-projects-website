from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDED_FILTER = ROOT / "app/ui/widgets/guided_filter.py"
DASHBOARD_CONTROLLER = ROOT / "app/ui/controllers/dashboard_controller.py"


def test_enter_value_typing_has_inline_suggestion_popup_contract():
    source = GUIDED_FILTER.read_text(encoding="utf-8")
    assert "class _InlineSuggestionPopup" in source
    assert "textEdited.connect(self._user_search_text_edited)" in source
    assert "_show_inline_suggestions" in source
    assert "_select_inline_value" in source
    assert "Open full selectable list" in source


def test_enter_without_arrow_selects_first_visible_suggestion():
    source = GUIDED_FILTER.read_text(encoding="utf-8")
    assert "returnPressed.connect(self._accept_inline_suggestion_or_open_picker)" in source
    assert "first_value" in source


def test_typed_query_is_used_by_dashboard_filter_when_no_checkbox_value_selected():
    source = DASHBOARD_CONTROLLER.read_text(encoding="utf-8")
    assert "def _dashboard_guided_query" in source
    assert "_dashboard_text_matches_query" in source
    assert "Company contains" in source
    assert "GST No contains" in source
