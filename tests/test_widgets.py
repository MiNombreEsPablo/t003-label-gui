import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from t003gui.widgets import SliderSpin, TenthsSpinBox, log_mapping


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _record(widget):
    seen = []
    widget.valueChanged.connect(seen.append)
    return seen


def test_slider_and_box_follow_each_other_and_emit_once(app):
    control = SliderSpin(-100, 100, default=0)
    seen = _record(control)
    control.slider.setValue(control.slider.value() + 30)  # the user drags
    assert control.value() == control.spin.value() == 30 - 0 and seen == [30]
    control.spin.setValue(-40)  # the user types
    assert control.slider.value() == -40 - (-100) and seen == [30, -40]
    control.setValue(-40)  # no change, no signal
    control.setValue(55)  # from code
    assert (control.value(), control.slider.value()) == (55, 155) and seen == [30, -40, 55]


def test_values_are_clamped_to_the_range(app):
    control = SliderSpin(0, 255, default=160)
    control.setValue(999)
    assert control.value() == 255 and control.slider.value() == 255
    control.setValue(-5)
    assert control.value() == 0 and control.slider.value() == 0


def test_double_clicking_the_slider_resets_it(app):
    control = SliderSpin(-100, 100, default=0)
    control.resize(300, 30)
    control.show()
    control.setValue(70)
    seen = _record(control)
    QTest.mouseDClick(control.slider, Qt.LeftButton, Qt.NoModifier, QPoint(10, 10))
    assert control.value() == 0 and seen == [0]
    control.setValue(10)
    control.reset()
    assert control.value() == 0


def test_special_text_suffix_and_tooltip_reach_the_box(app):
    control = SliderSpin(0, 32, default=0)
    control.setSpecialValueText("Off")
    control.setSuffix(" dots")
    control.setToolTip("chunky")
    assert control.spin.text() == "Off"
    control.setValue(3)
    assert control.spin.text() == "3 dots"
    assert control.spin.toolTip() == control.slider.toolTip() == "chunky"


def test_disabling_the_control_disables_both_parts(app):
    control = SliderSpin(0, 10)
    control.setEnabled(False)
    assert not control.slider.isEnabled() and not control.spin.isEnabled()


def test_all_value_boxes_share_one_width(app):
    controls = [SliderSpin(0, 255), SliderSpin(-100, 100), SliderSpin(0, 32)]  # kept alive while we read them
    widths = {c.spin.minimumWidth() for c in controls} | {c.spin.maximumWidth() for c in controls}
    assert len(widths) == 1 and widths.pop() > 0  # so every slider ends up the same length


def test_log_mapping_puts_the_neutral_gamma_exactly_in_the_middle(app):
    mapping = log_mapping(3, 30, neutral=10)  # gamma 0.3 to 3.0 in tenths, neutral 1.0
    assert mapping.to_position(3) == 0 and mapping.to_position(30) == mapping.steps
    assert mapping.to_position(10) == mapping.steps // 2  # exactly: not "near"
    assert mapping.from_position(mapping.steps // 2) == 10
    positions = [mapping.to_position(v) for v in range(3, 31)]
    assert positions == sorted(set(positions))  # strictly increasing: no two values share a spot
    for tenths in range(3, 31):  # every value survives the trip slider -> value
        assert mapping.from_position(mapping.to_position(tenths)) == tenths


def test_a_plain_log_mapping_still_works(app):
    mapping = log_mapping(1, 100)
    assert mapping.to_position(1) == 0 and mapping.to_position(100) == mapping.steps
    assert mapping.from_position(mapping.to_position(10)) == 10


def test_gamma_style_slider_with_a_tenths_box(app):
    control = SliderSpin(3, 30, default=10, spin=TenthsSpinBox(), mapping=log_mapping(3, 30))
    control.setValue(10)
    assert control.spin.text() == "1.0"
    control.slider.setValue(control.slider.maximum())
    assert control.value() == 30 and control.spin.text() == "3.0"
    control.setValue(3)
    assert control.slider.value() == 0
    control.reset()
    assert control.value() == 10
