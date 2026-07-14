# Auto-split from app.py for readability. Executed by app.py in application globals.

# ─────────────────────────────────────────────────────────────
# Per-field typography/style controls
# ─────────────────────────────────────────────────────────────
STYLE_PROPS = ["font", "size", "weight", "italic", "uppercase", "color", "align", "letter_spacing", "line_height"]
STYLE_DEFAULTS = {"font": "", "size": "", "weight": "", "italic": "0", "uppercase": "0", "color": "", "align": "", "letter_spacing": "", "line_height": ""}


def style_key(section, field, prop):
    return f"style_{section}_{field}_{prop}"


def collect_field_styles(section, fields):
    if not advanced_mode_enabled():
        return {}
    expected_keys = [style_key(section, field, prop) for field, _label, _default in fields for prop in STYLE_PROPS]
    # V15.1: content pages no longer display per-field style controls by default.
    # If those controls are not present in the submitted form, preserve existing styles instead of wiping them.
    if not any(key in request.form for key in expected_keys):
        return {}
    payload = {}
    for field, _label, _default in fields:
        for prop in STYLE_PROPS:
            payload[style_key(section, field, prop)] = request.form.get(style_key(section, field, prop), STYLE_DEFAULTS.get(prop, ""))
    return payload


def apply_field_styles(payload):
    for key, value in payload.items():
        if key.startswith("style_"):
            set_setting(key, value or "")


def css_dimension(value, default_unit="px"):
    """Accept admin-friendly values. If user types 22, convert to 22px so font-size works."""
    v = (value or "").strip()
    if not v:
        return ""
    if re.fullmatch(r"-?\d+(\.\d+)?", v):
        return f"{v}{default_unit}"
    return v


def css_font_family(value):
    v = (value or "").strip()
    if not v:
        return ""
    # Quote custom Google font names with spaces. Keep CSS fallback after it.
    safe = v.replace("'", "").replace('"', "")
    return f"'{safe}', system-ui, sans-serif"


def style_inline(section, field):
    try:
        site = settings_dict()
    except Exception:
        site = {}
    parts = []
    font = site.get(style_key(section, field, "font"), "").strip()
    size = css_dimension(site.get(style_key(section, field, "size"), ""))
    weight = site.get(style_key(section, field, "weight"), "").strip()
    color = site.get(style_key(section, field, "color"), "").strip()
    align = site.get(style_key(section, field, "align"), "").strip()
    letter = css_dimension(site.get(style_key(section, field, "letter_spacing"), ""), "px")
    lineh = site.get(style_key(section, field, "line_height"), "").strip()
    if font: parts.append(f"font-family:{css_font_family(font)} !important")
    if size: parts.append(f"font-size:{size} !important")
    if weight: parts.append(f"font-weight:{weight} !important")
    if color: parts.append(f"color:{color} !important")
    if align: parts.append(f"text-align:{align} !important")
    if letter: parts.append(f"letter-spacing:{letter} !important")
    if lineh: parts.append(f"line-height:{lineh} !important")
    if flag_value(site.get(style_key(section, field, "italic")), False): parts.append("font-style:italic !important")
    if flag_value(site.get(style_key(section, field, "uppercase")), False): parts.append("text-transform:uppercase !important")
    return ";".join(parts)


def item_style_key(section, field, prop):
    return f"style_{field}_{prop}"


def collect_item_styles(section, obj=None):
    current_styles = getattr(obj, "styles_json", "{}") or "{}"
    if not advanced_mode_enabled():
        return current_styles
    fields = FIELD_VISIBILITY_GROUPS.get(section, [])
    expected_keys = [item_style_key(section, field, prop) for field, _label, _default in fields for prop in STYLE_PROPS]
    # V15.1: when per-item style controls are hidden, do not erase existing item styles on save.
    if not any(key in request.form for key in expected_keys):
        return current_styles
    data = {}
    for field, _label, _default in fields:
        sub = {}
        for prop in STYLE_PROPS:
            value = request.form.get(item_style_key(section, field, prop), STYLE_DEFAULTS.get(prop, ""))
            if value:
                sub[prop] = value
        if sub:
            data[field] = sub
    return json.dumps(data, ensure_ascii=False)


def item_style_dict(obj, field):
    raw = getattr(obj, "styles_json", "") if obj is not None else ""
    try:
        styles = json.loads(raw or "{}")
        return styles.get(field, {}) if isinstance(styles, dict) else {}
    except Exception:
        return {}


def item_style_value(obj, field, prop, default=""):
    return item_style_dict(obj, field).get(prop, default) or ""


def item_style_flag(obj, field, prop):
    return flag_value(item_style_value(obj, field, prop), False)


def item_style_inline(obj, section, field):
    cfg = item_style_dict(obj, field)
    parts = []
    if cfg.get("font"): parts.append(f"font-family:{css_font_family(cfg['font'])} !important")
    if cfg.get("size"): parts.append(f"font-size:{css_dimension(cfg['size'])} !important")
    if cfg.get("weight"): parts.append(f"font-weight:{cfg['weight']} !important")
    if cfg.get("color"): parts.append(f"color:{cfg['color']} !important")
    if cfg.get("align"): parts.append(f"text-align:{cfg['align']} !important")
    if cfg.get("letter_spacing"): parts.append(f"letter-spacing:{css_dimension(cfg['letter_spacing'], 'px')} !important")
    if cfg.get("line_height"): parts.append(f"line-height:{cfg['line_height']} !important")
    if flag_value(cfg.get("italic"), False): parts.append("font-style:italic !important")
    if flag_value(cfg.get("uppercase"), False): parts.append("text-transform:uppercase !important")
    return ";".join(parts)


