import tkinter as tk

# light colour  ->  dark colour   (all lower-case, every value used once)
PAIRS = {
    # --- the theme colours from ui_common.py ---
    "#f2f3f8": "#0f1220",    # COLOR_BG        page background
    "#ffffff": "#1a1e30",    # COLOR_WHITE     cards
    "#1c1f2e": "#eef0f8",    # COLOR_TEXT
    "#8a8fa3": "#9aa0b8",    # COLOR_MUTED
    "#eceef4": "#2a2f45",    # COLOR_LINE
    "#fdeceb": "#3b1f26",    # COLOR_RED_BG
    "#e5533d": "#ff7b67",    # COLOR_RED_TEXT
    "#f7f8fb": "#232840",    # COLOR_FIELD_BG
    "#e3e5ee": "#343a58",    # COLOR_FIELD_LINE
    # --- priority colours (PRIORITY_STYLES) ---
    "#fff4e0": "#3d3018", "#d98500": "#f5a623",
    "#fffbea": "#352c16", "#f5d77a": "#6b5a24",
    "#fff1f0": "#3a2024", "#f5b5ad": "#7a3a35",
    "#e7f8ef": "#16352a", "#0f9d58": "#3ddc97",
    "#effbf4": "#163428", "#a7e3c3": "#2f6b52",
    # --- greys typed directly in the pages ---
    "#fbfcfe": "#1f2338",    # footer strip on the Completed card
    "#5b6075": "#a9aec4",    # struck-through titles
    "#4a4f66": "#c9cde0",    # Cancel / icon text
    "#6b7090": "#8b91ab",    # date hint
    "#cfd3e0": "#3b4260",    # switch track when off
    # --- categories, calendar and overdue/priority chips (new) ---
    "#eef0ff": "#2b2a55",    # category chip background
    "#fee2e2": "#4a2226", "#b91c1c": "#ff8a8a",   # High / overdue chip
    "#fef3c7": "#41351a", "#b45309": "#f5b75a",   # Medium chip
    "#dcfce7": "#17382b", "#15803d": "#5fe0a0",   # Low chip
    "#eef0f5": "#2c3148", "#8a8fa6": "#848aa6",   # completed chip
    "#b8bccd": "#4a5070",    # calendar days outside this month
}
TO_DARK = dict(PAIRS)
TO_LIGHT = {dark: light for light, dark in PAIRS.items()}
assert len(TO_LIGHT) == len(TO_DARK), "every dark colour must be used once"
assert not set(TO_DARK) & set(TO_LIGHT), "light and dark colours must differ"

# options (as Tk spells them) that hold a colour
COLOR_OPTIONS = {
    "-bg", "-background", "-fg", "-foreground", "-fill", "-outline",
    "-highlightbackground", "-highlightcolor", "-activebackground",
    "-activeforeground", "-insertbackground", "-selectbackground",
    "-selectforeground", "-disabledforeground", "-troughcolor",
    "-readonlybackground", "-activefill", "-activeoutline",
    "-disabledfill", "-disabledoutline",
}
WIDGET_OPTIONS = (
    "bg", "fg", "highlightbackground", "highlightcolor", "activebackground",
    "activeforeground", "insertbackground", "selectbackground",
    "selectforeground", "disabledforeground", "troughcolor",
)
ITEM_OPTIONS = ("fill", "outline", "activefill", "disabledfill")

_state = {"dark": False}


def is_dark():
    return _state["dark"]


def translate(color):
    """The colour to really use right now."""
    if _state["dark"] and isinstance(color, str):
        return TO_DARK.get(color.lower(), color)
    return color


def _install():
    """Put the colour filter in front of Tkinter (done once)."""
    original = tk.Misc._options
    if getattr(original, "_taskflow_theme", False):
        return

    def _options(self, cnf, kw=None):
        result = original(self, cnf, kw)
        if not _state["dark"]:
            return result
        items = list(result)
        for i in range(0, len(items) - 1, 2):
            if items[i] in COLOR_OPTIONS:
                items[i + 1] = translate(items[i + 1])
        return tuple(items)

    _options._taskflow_theme = True
    tk.Misc._options = _options


_install()


# =====================================================================
# switching the widgets that already exist
# =====================================================================
def apply(root, name, skip=()):
    """name: "light" or "dark".  skip: widgets (with everything inside
    them) that must keep their colours."""
    dark = name == "dark"
    _state["dark"] = dark
    table = TO_DARK if dark else TO_LIGHT
    skip_paths = {str(widget) for widget in skip}
    _recolor(root, table, skip_paths)


def _recolor(widget, table, skip_paths):
    if str(widget) in skip_paths:
        return
    _recolor_widget(widget, table)
    if isinstance(widget, tk.Canvas):
        _recolor_canvas_items(widget, table)
    for child in widget.winfo_children():
        if isinstance(child, tk.Toplevel):      # pop-ups / toasts are short-lived
            continue
        _recolor(child, table, skip_paths)


def _recolor_widget(widget, table):
    for option in WIDGET_OPTIONS:
        try:
            current = str(widget.cget(option)).lower()
        except tk.TclError:
            continue                            # this widget has no such option
        new = table.get(current)
        if new:
            try:
                widget.configure(**{option: new})
            except tk.TclError:
                pass


def _recolor_canvas_items(canvas, table):
    for item in canvas.find_all():
        for option in ITEM_OPTIONS:
            try:
                current = str(canvas.itemcget(item, option)).lower()
            except tk.TclError:
                continue                        # e.g. window / image items
            new = table.get(current)
            if new:
                try:
                    canvas.itemconfigure(item, **{option: new})
                except tk.TclError:
                    pass