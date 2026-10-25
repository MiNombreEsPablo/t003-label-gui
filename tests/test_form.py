import json

import pytest

from t003gui import api, form, spec


def test_every_field_is_a_real_spec_field_with_valid_choices():
    names = {f for f in spec.LabelSpec.__dataclass_fields__}
    for field in form.FIELDS:
        assert field.name in names, field.name
        assert field.tab == form.OUTPUT or field.tab in dict(form.TABS), field.name
        if field.toggle:
            assert isinstance(getattr(spec.LabelSpec(), field.toggle), bool)
        if field.kind == "choice":
            assert field.choices and all(len(c) == 3 for c in field.choices)
        if field.kind == "number":
            assert field.minimum <= getattr(spec.LabelSpec(), field.name) <= field.maximum


def test_every_spec_field_has_a_control_or_is_listed_as_pending():
    """The drift guard: a new LabelSpec field must be described in form.py (or admitted in PENDING) before it ships,
    so no client can quietly lack a control for it."""
    names = set(spec.LabelSpec.__dataclass_fields__)
    assert not (form.covered() & form.PENDING), "described and pending at once"
    assert names == form.covered() | form.PENDING, sorted(names ^ (form.covered() | form.PENDING))


def test_choices_follow_spec_so_a_new_effect_needs_no_ui_change():
    by_name = {f.name: f for f in form.FIELDS}
    assert [c[0] for c in by_name["effect"].choices] == list(spec.EFFECTS)
    assert [c[0] for c in by_name["background"].choices] == list(spec.BACKGROUNDS)
    assert [c[0] for c in by_name["border_style"].choices] == list(spec.BORDER_STYLES)
    assert by_name["font"].choices[0][2]  # fonts come grouped by category


def test_labels_match_the_qt_window_for_now():
    panels = pytest.importorskip("t003gui.panels")  # needs PySide6
    for value, label in form.LABELS.items():
        assert panels.LABELS[value] == label


def test_the_form_is_in_the_options_and_is_plain_json():
    options = json.loads(api.options())
    assert options["form"] == json.loads(json.dumps(form.describe()))
    assert [t["id"] for t in options["form"]["tabs"]] == ["content", "text", "decoration"]


def test_hints_say_when_image_only_drops_the_text():
    assert api.hints({"text": "hi"}) == []
    hint = api.hints({"text": "hi", "image_path": "x.png"})
    assert len(hint) == 1 and "text isn't printed" in hint[0] and "Image tab" in hint[0]
    assert api.hints({"text": "hi", "image_path": "x.png", "image_layout": "left"}) == []
