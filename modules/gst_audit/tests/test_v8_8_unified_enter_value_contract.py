from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_enter_value_and_arrow_are_one_compound_control():
    source = (ROOT / "app/ui/widgets/guided_filter.py").read_text(encoding="utf-8")
    theme_source = (ROOT / "app/ui/theme_manager.py").read_text(encoding="utf-8")
    static_style = (ROOT / "app/assets/styles/main.qss").read_text(encoding="utf-8")

    assert 'self.enter_value_frame = QFrame()' in source
    assert 'self.enter_value_frame.setObjectName("GuidedValueBox")' in source
    assert 'QHBoxLayout(self.enter_value_frame)' in source
    assert 'self.search_edit.setFrame(False)' in source
    assert 'self.open_picker_btn.setFlat(True)' in source
    assert 'enter_layout.addWidget(self.enter_value_frame)' in source

    assert 'QFrame#GuidedValueBox' in theme_source
    assert 'QFrame#GuidedValueBox[focused="true"]' in theme_source
    assert 'QLineEdit#GuidedSearchInput' in theme_source
    assert 'border: 0px' in theme_source
    assert 'QPushButton#PickerDropButton' in theme_source
    assert 'border-left: 1px solid' in theme_source

    assert 'QFrame#GuidedValueBox' in static_style
    assert 'QLineEdit#GuidedSearchInput' in static_style
    assert 'QPushButton#PickerDropButton' in static_style


def test_enter_value_focus_ring_is_applied_to_outer_box():
    source = (ROOT / "app/ui/widgets/guided_filter.py").read_text(encoding="utf-8")
    assert 'def _set_enter_value_focus' in source
    assert 'self.enter_value_frame.setProperty("focused", focused)' in source
    assert 'watched in {self.search_edit, self.open_picker_btn}' in source
