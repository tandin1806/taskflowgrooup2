import math
import os
import tkinter as tk
from tkinter import font, ttk
from PIL import Image, ImageDraw, ImageTk

from emoji_icons import get_emoji, NAV_EMOJI

# Folder this file lives in - icons are looked up here, so the app works
# no matter which folder you launch it from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =====================================================================
# 1. COLORS  (kept in one place so the whole theme is easy to tweak)
# =====================================================================
COLOR_NAVY = "#161c33"      # sidebar background
COLOR_PURPLE = "#6c5ce7"    # brand / accent color
COLOR_BG = "#f2f3f8"        # page background
COLOR_WHITE = "#ffffff"     # card background
COLOR_TEXT = "#1c1f2e"      # main text
COLOR_MUTED = "#8a8fa3"     # secondary / gray text
COLOR_LINE = "#eceef4"      # borders and dividers
COLOR_RED_BG = "#fdeceb"    # "High" priority badge background
COLOR_RED_TEXT = "#e5533d"  # "High" priority badge text
COLOR_GREEN = "#12b76a"     # completed checkmark
COLOR_FIELD_BG = "#f7f8fb"  # input fields in the Add Task dialog
COLOR_FIELD_LINE = "#e3e5ee"

# Colors for each priority level: (badge bg, badge text, dot, selected-box bg,
# selected-box border)
PRIORITY_STYLES = {
    "High":   {"bg": COLOR_RED_BG, "text": COLOR_RED_TEXT, "dot": "#ef4444",
               "sel_bg": "#fff1f0", "sel_border": "#f5b5ad"},
    "Medium": {"bg": "#fff4e0", "text": "#d98500", "dot": "#f59e0b",
               "sel_bg": "#fffbea", "sel_border": "#f5d77a"},
    "Low":    {"bg": "#e7f8ef", "text": "#0f9d58", "dot": "#12b76a",
               "sel_bg": "#effbf4", "sel_border": "#a7e3c3"},
}

# Keeps references to every PhotoImage so Tkinter doesn't garbage-collect
# them (a very common "icons disappear" bug).
ICON_IMAGES = []


# =====================================================================
# 2. FONTS  (created once here, reused everywhere)
# =====================================================================
def build_fonts():
    return {
        "heading": font.Font(family="Segoe UI", size=18, weight="bold"),
        "card_title": font.Font(family="Segoe UI", size=11, weight="bold"),
        "body": font.Font(family="Segoe UI", size=10),
        "small": font.Font(family="Segoe UI", size=9),
        "small_bold": font.Font(family="Segoe UI", size=9, weight="bold"),
        "stat_number": font.Font(family="Segoe UI", size=20, weight="bold"),
        "ring_percent": font.Font(family="Segoe UI", size=16, weight="bold"),
        # extra fonts used by the new pieces
        "check_mark": font.Font(family="Segoe UI", size=7, weight="bold"),
        "dialog_title": font.Font(family="Segoe UI", size=13, weight="bold"),
        "label": font.Font(family="Segoe UI", size=10, weight="bold"),
        "close": font.Font(family="Segoe UI", size=12),
        "body_strike": font.Font(family="Segoe UI", size=10, overstrike=True),
    }


def load_icon(path, size=18):
    """Loads an image file (png/jpg/webp) and returns a Tkinter-ready
    PhotoImage, resized to a small square icon. Keeps a reference so it
    isn't garbage collected. If the file can't be found, a blank icon is
    used instead of crashing the app."""
    full_path = path if os.path.isabs(path) else os.path.join(BASE_DIR, path)
    try:
        img = Image.open(full_path).convert("RGBA")
    except (FileNotFoundError, OSError):
        try:
            img = Image.open(path).convert("RGBA")   # try current folder
        except (FileNotFoundError, OSError):
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    img = img.resize((size, size), Image.LANCZOS)
    photo = ImageTk.PhotoImage(img)
    ICON_IMAGES.append(photo)
    return photo


def shorten(text, limit):
    """Cuts long text and adds '…' so it never breaks the layout."""
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def format_date(d):
    """date -> '30 Aug 2026' (the style used in your original design)."""
    return d.strftime("%d %b %Y")


# =====================================================================
# 3. DRAWING HELPERS
#    Small reusable functions that draw the rounded shapes Tkinter
#    doesn't support out of the box.
# =====================================================================

def draw_rounded_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    """Draws a rounded rectangle on a canvas using a smooth polygon."""
    points = [
        x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
        x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
        x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


def create_card(parent, width, height, radius=24, page_bg=COLOR_BG):
    """
    Creates a white rounded 'card' (like the boxes in the prototype)
    and returns (canvas, inner_frame). Put your labels/buttons inside
    inner_frame just like you would with a normal tk.Frame.

    The card is also responsive: if you pack/place it with fill="both"
    (or fill="x"/"y") and expand=True, it will redraw itself and stay
    rounded whenever the window is resized.
    """
    canvas = tk.Canvas(parent, width=width, height=height, bg=page_bg,
                        highlightthickness=0)
    inner = tk.Frame(canvas, bg=COLOR_WHITE)
    window_id = canvas.create_window(1, 1, window=inner, anchor="nw")
    shape_id = {"value": None}  # holds the id of the rounded rectangle shape

    def redraw(event=None):
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 4 or h < 4:
            return  # not yet drawn on screen, skip

        # never let the radius be bigger than half the box, or the
        # rounded corners would overlap and look broken
        safe_radius = min(radius, w / 2, h / 2)

        if shape_id["value"] is not None:
            canvas.delete(shape_id["value"])
        shape_id["value"] = draw_rounded_rect(
            canvas, 1, 1, w - 1, h - 1, safe_radius,
            fill=COLOR_WHITE, outline=COLOR_LINE
        )
        canvas.tag_lower(shape_id["value"])  # keep it behind the inner frame

        canvas.coords(window_id, 1, 1)
        canvas.itemconfig(window_id, width=w - 2, height=h - 2)

    canvas.bind("<Configure>", redraw)
    return canvas, inner


def create_avatar(parent, initials, size, fonts, page_bg):
    """Creates a small circular avatar with initials, like 'TW'."""
    canvas = tk.Canvas(parent, width=size, height=size, bg=page_bg,
                        highlightthickness=0)
    canvas.create_oval(1, 1, size - 1, size - 1, fill=COLOR_PURPLE,
                        outline=COLOR_PURPLE)
    canvas.initials_item = canvas.create_text(
        size / 2, size / 2, text=initials, fill="white",
        font=fonts["small_bold"])
    return canvas


def initials_of(name):
    """'Tandin Wangchuk' -> 'TW', 'Pema' -> 'P'."""
    parts = [p for p in name.split() if p]
    return "".join(p[0] for p in parts[:2]).upper() or "?"


AVATAR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "avatars")    # same folder the Profile page uses


def load_avatar_photo(user_id, size):
    """The saved profile photo as a round image, or None if there is none."""
    path = os.path.join(AVATAR_DIR, f"user_{user_id}.png")
    if not os.path.exists(path):
        return None
    try:
        resample = getattr(Image, "Resampling", Image).LANCZOS
        picture = Image.open(path).convert("RGBA").resize((size, size),
                                                          resample)
        mask = Image.new("L", (size * 4, size * 4), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1),
                                     fill=255)
        picture.putalpha(mask.resize((size, size), resample))
        return ImageTk.PhotoImage(picture)
    except Exception:
        return None


def set_avatar_initials(canvas, initials, user_id=None):
    """Shows the user's photo on the avatar if they have one, otherwise the
    initials."""
    size = int(canvas.cget("width"))
    photo = load_avatar_photo(user_id, size - 2) if user_id else None
    canvas.delete("photo")
    if photo is not None:
        canvas.photo = photo                      # keep a reference
        canvas.create_image(size / 2, size / 2, image=photo, tags="photo")
        canvas.itemconfig(canvas.initials_item, state="hidden")
    else:
        canvas.photo = None
        canvas.itemconfig(canvas.initials_item, text=initials,
                          state="normal")


def create_pill_button(parent, text, width, height, fonts,
                        bg=COLOR_PURPLE, fg="white", command=None):
    """Creates a small rounded button, like '+ Add Task'."""
    canvas = tk.Canvas(parent, width=width, height=height, bg=COLOR_WHITE,
                        highlightthickness=0)
    draw_rounded_rect(canvas, 0, 0, width, height, radius=height / 2,
                       fill=bg, outline=bg)
    canvas.create_text(width / 2, height / 2, text=text, fill=fg,
                        font=fonts["small_bold"])
    if command is not None:
        canvas.configure(cursor="hand2")
        canvas.bind("<Button-1>", lambda e: command())
    return canvas


def create_priority_badge(parent, text, fonts):
    """Creates the small 'High / Medium / Low' pill with a dot.
    High = red, Medium = orange, Low = green."""
    style = PRIORITY_STYLES.get(text, PRIORITY_STYLES["High"])
    width, height = 72, 22
    canvas = tk.Canvas(parent, width=width, height=height, bg=COLOR_WHITE,
                        highlightthickness=0)
    draw_rounded_rect(canvas, 0, 0, width, height, radius=height / 2,
                       fill=style["bg"], outline=style["bg"])
    canvas.create_oval(10, 9, 16, 15, fill=style["text"],
                        outline=style["text"])
    canvas.create_text(width / 2 + 6, height / 2, text=text,
                        fill=style["text"], font=fonts["small"])
    return canvas


def create_outlined_badge(parent, text, fonts):
    """Priority pill with a thin colored border (used on the Completed page)."""
    style = PRIORITY_STYLES.get(text, PRIORITY_STYLES["High"])
    width, height = 80, 22
    canvas = tk.Canvas(parent, width=width, height=height, bg=COLOR_WHITE,
                        highlightthickness=0)
    draw_rounded_rect(canvas, 1, 1, width - 1, height - 1,
                       radius=(height - 2) / 2, fill=style["sel_bg"],
                       outline=style["sel_border"])
    canvas.create_oval(11, 9, 17, 15, fill=style["dot"], outline=style["dot"])
    canvas.create_text(width / 2 + 6, height / 2, text=text,
                        fill=style["text"], font=fonts["small_bold"])
    return canvas


def format_percent(percent):
    """Whole number to show for a percentage. 33.333 -> 33, and partial
    progress never rounds up to 100% or down to 0%."""
    if percent >= 100:
        return 100
    if percent <= 0:
        return 0
    return max(1, min(99, int(percent + 0.5)))


def draw_progress_ring(canvas, percent, fonts, total=None):
    """(Re)draws everything inside the progress ring canvas.
    total (optional) = number of tasks; 0 shows 'No tasks'."""
    size, thickness = canvas.ring_size, canvas.ring_thickness
    canvas.delete("all")
    shown = format_percent(percent)
    complete = shown >= 100
    color = COLOR_GREEN if complete else COLOR_PURPLE
    box = (thickness / 2, thickness / 2, size - thickness / 2,
           size - thickness / 2)

    # background track (light gray full circle)
    canvas.create_arc(*box, start=90, extent=359.99, style="arc",
                      outline=COLOR_LINE, width=thickness)
    # progress arc, drawn clockwise starting from the top
    degrees = min(360 * (max(percent, 0) / 100), 359.99)
    if degrees > 0:   # at 0% nothing is drawn at all
        canvas.create_arc(*box, start=90, extent=-degrees, style="arc",
                          outline=color, width=thickness)
        if not complete:
            # round both ends of the arc
            radius = (size - thickness) / 2
            cap = thickness / 2
            for angle in (90, 90 - degrees):
                x = size / 2 + radius * math.cos(math.radians(angle))
                y = size / 2 - radius * math.sin(math.radians(angle))
                canvas.create_oval(x - cap, y - cap, x + cap, y + cap,
                                   fill=color, outline=color)

    # whole-number percentage + a status word, centered inside the ring
    if total == 0:
        status, status_color = "No tasks", COLOR_MUTED
    elif complete:
        status, status_color = "All done!", COLOR_GREEN
    else:
        status, status_color = "Completed", COLOR_MUTED
    canvas.create_text(size / 2, size / 2 - 8, text=f"{shown}%", fill=color,
                       font=fonts["ring_percent"])
    canvas.create_text(size / 2, size / 2 + 12, text=status,
                       fill=status_color, font=fonts["small"])


def create_progress_ring(parent, percent, fonts, size=110, thickness=10):
    """Draws the circular 'X% Done' progress ring seen in the prototype.
    Call draw_progress_ring(canvas, new_percent, fonts) to update it."""
    canvas = tk.Canvas(parent, width=size, height=size, bg=COLOR_WHITE,
                        highlightthickness=0)
    canvas.ring_size = size
    canvas.ring_thickness = thickness
    draw_progress_ring(canvas, percent, fonts)
    return canvas


class RoundedBox(tk.Canvas):
    """A rounded input box (used by the Add Task dialog). Put widgets inside
    `box.inner`. It turns purple while one of its widgets has focus and red
    when `set_error(True)` is called."""

    def __init__(self, parent, height, radius=10, page_bg=COLOR_WHITE,
                 fill=COLOR_FIELD_BG, border=COLOR_FIELD_LINE, width=10):
        super().__init__(parent, height=height, width=width, bg=page_bg,
                         highlightthickness=0)
        self.radius = radius
        self._normal_fill = fill
        self._normal_border = border
        self._fill, self._border, self._bw = fill, border, 1
        self._focused = False
        self._error = False
        self._shape = None
        self.inner = tk.Frame(self, bg=fill)
        self._win = self.create_window(0, 0, window=self.inner, anchor="nw")
        self.bind("<Configure>", self._redraw)

    # --- state ---------------------------------------------------------
    def attach(self, widget):
        """Track focus of a widget that lives inside this box."""
        widget.bind("<FocusIn>", lambda e: self._set_focus(True), add="+")
        widget.bind("<FocusOut>", lambda e: self._set_focus(False), add="+")

    def _set_focus(self, value):
        self._focused = value
        self._apply()

    def set_error(self, value):
        self._error = value
        self._apply()

    def set_highlight(self, value):
        """Purple outline on/off (used for the 'open' bell button)."""
        self._set_focus(value)

    def _apply(self):
        if self._focused:
            self._fill, self._border, self._bw = COLOR_WHITE, COLOR_PURPLE, 2
        elif self._error:
            self._fill, self._border, self._bw = (
                self._normal_fill, COLOR_RED_TEXT, 2)
        else:
            self._fill, self._border, self._bw = (
                self._normal_fill, self._normal_border, 1)
        self._recolor(self.inner, self._fill)
        self._redraw()

    def _recolor(self, widget, color):
        try:
            widget.configure(bg=color)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._recolor(child, color)

    # --- drawing -------------------------------------------------------
    def _redraw(self, event=None):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4 or h < 4:
            return
        bw = self._bw
        r = min(self.radius, w / 2, h / 2)
        if self._shape is not None:
            self.delete(self._shape)
        m = bw / 2 + 1          # 1px safety margin so edges never get clipped
        self._shape = draw_rounded_rect(
            self, m, m, w - m, h - m, r,
            fill=self._fill, outline=self._border, width=bw)
        self.tag_lower(self._shape)
        # keep the inner frame inside the rounded corners
        inset = max(bw + 2, int(r * 0.3) + 2)
        self.coords(self._win, inset, inset)
        self.itemconfig(self._win, width=max(1, w - 2 * inset),
                        height=max(1, h - 2 * inset))


class ScrollFrame(tk.Frame):
    """A frame whose content scrolls (mouse wheel + a scrollbar that only
    shows up when needed). Put your widgets inside `scroll.body`."""

    def __init__(self, parent, bg=COLOR_WHITE, max_height=None):
        """max_height: optional function returning the tallest this area may
        get. When given, the area shrinks to fit its rows (and scrolls only
        if they don't fit)."""
        super().__init__(parent, bg=bg)
        self._max_height = max_height
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0,
                                width=1, height=1)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical",
                                       command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self._bar_shown = False

        self.body = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window(0, 0, window=self.body,
                                              anchor="nw")
        self.body.bind("<Configure>", self._update)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # one global wheel handler per ScrollFrame; it only reacts when the
        # mouse pointer is actually over this frame
        self.bind_all("<MouseWheel>", self._on_wheel, add="+")
        self.bind_all("<Button-4>", self._on_wheel, add="+")
        self.bind_all("<Button-5>", self._on_wheel, add="+")

    def clear(self):
        for child in self.body.winfo_children():
            child.destroy()

    def refresh_layout(self):
        """Call after adding/removing rows so the scrollbar and scroll
        area are re-measured."""
        self.update_idletasks()
        self._update()

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self._win, width=event.width)
        self._update()

    def _update(self, event=None):
        height = self.body.winfo_reqheight()
        self.canvas.configure(scrollregion=(0, 0, 1, height))
        if self._max_height is not None:
            target = max(1, min(height, self._max_height()))
            self.canvas.configure(height=target)
            need = height > target
        else:
            need = height > self.canvas.winfo_height() > 1
        if need and not self._bar_shown:
            self.scrollbar.pack(side="right", fill="y")
            self._bar_shown = True
        elif not need and self._bar_shown:
            self.scrollbar.pack_forget()
            self._bar_shown = False
            self.canvas.yview_moveto(0)

    def _pointer_inside(self):
        try:
            widget = self.winfo_containing(*self.winfo_pointerxy())
        except (KeyError, tk.TclError):
            return False
        while widget is not None:
            if widget is self:
                return True
            widget = widget.master
        return False

    def _on_wheel(self, event):
        if not self.winfo_exists() or not self._bar_shown:
            return
        if not self._pointer_inside():
            return
        if event.num == 4:
            step = -1
        elif event.num == 5:
            step = 1
        else:
            step = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(step * 2, "units")


# =====================================================================
# 4. SHARED SECTION BUILDERS (sidebar + top bar)
# =====================================================================

# icons come from emoji_icons.NAV_EMOJI (change them there, once)
MENU_ITEMS = ["Dashboard", "My Tasks", "Completed", "Profile", "Setting"]


def build_sidebar(root, fonts, on_navigate=None, clickable=(),
                  active="Dashboard", on_logout=None):
    """Builds the sidebar. Returns (sidebar, set_active, set_user):
    set_active("Completed") moves the purple highlight and
    set_user("Name") updates the name + initials at the bottom."""
    sidebar = tk.Frame(root, bg=COLOR_NAVY, width=220)
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)  # keep width fixed no matter what's inside

    # --- brand / logo ---
    brand = tk.Frame(sidebar, bg=COLOR_NAVY)
    brand.pack(fill="x", padx=18, pady=(20, 16))

    logo = tk.Canvas(brand, width=32, height=32, bg=COLOR_NAVY,
                      highlightthickness=0)
    draw_rounded_rect(logo, 1, 1, 31, 31, radius=12, fill=COLOR_PURPLE,
                       outline=COLOR_PURPLE)
    logo.create_text(16, 16, text="📄", fill="white", font=fonts["body"])
    logo.pack(side="left", padx=(0, 10))

    brand_text = tk.Frame(brand, bg=COLOR_NAVY)
    brand_text.pack(side="left")
    tk.Label(brand_text, text="TaskFlow", bg=COLOR_NAVY, fg="white",
             font=fonts["card_title"]).pack(anchor="w")
    tk.Label(brand_text, text="Student Edition", bg=COLOR_NAVY,
             fg=COLOR_MUTED, font=fonts["small"]).pack(anchor="w")

    tk.Frame(sidebar, bg="#2a3153", height=1).pack(fill="x", padx=18)

    # --- menu ---
    tk.Label(sidebar, text="MENU", bg=COLOR_NAVY, fg="#6b7090",
             font=fonts["small"]).pack(anchor="w", padx=20, pady=(16, 8))

    items = {}
    for label in MENU_ITEMS:
        command = None
        if on_navigate is not None and label in clickable:
            command = (lambda name=label: on_navigate(name))
        items[label] = build_menu_item(sidebar, label,
                                       label == active, fonts, command)

    def set_active(name):
        for label, item in items.items():
            item["set_active"](label == name)

    # --- user box, pinned to the bottom ---
    user_box = tk.Frame(sidebar, bg=COLOR_NAVY)
    user_box.pack(side="bottom", fill="x", padx=16, pady=18)

    side_avatar = create_avatar(user_box, "", 34, fonts, COLOR_NAVY)
    side_avatar.pack(side="left", padx=(0, 10))

    user_text = tk.Frame(user_box, bg=COLOR_NAVY)
    user_text.pack(side="left")
    name_label = tk.Label(user_text, text="", bg=COLOR_NAVY,
                          fg="white", font=fonts["small_bold"])
    name_label.pack(anchor="w")
    tk.Label(user_text, text="Student", bg=COLOR_NAVY, fg=COLOR_MUTED,
             font=fonts["small"]).pack(anchor="w")

    power = tk.Label(user_box, text="⏻", bg=COLOR_NAVY, fg=COLOR_MUTED,
                     font=fonts["body"])
    power.pack(side="right")
    if on_logout is not None:           # the power icon signs you out
        power.configure(cursor="hand2")
        power.bind("<Button-1>", lambda e: on_logout())
        power.bind("<Enter>", lambda e: power.config(fg="white"))
        power.bind("<Leave>", lambda e: power.config(fg=COLOR_MUTED))

    def set_user(name, user_id=None):
        name_label.config(text=shorten(name, 18))
        set_avatar_initials(side_avatar, initials_of(name), user_id)

    return sidebar, set_active, set_user


def build_menu_item(sidebar, label, is_active, fonts, command=None):
    width, height = 190, 36
    canvas = tk.Canvas(sidebar, width=width, height=height, bg=COLOR_NAVY,
                        highlightthickness=0)
    icon_size = 18
    emoji = NAV_EMOJI.get(label, "\U0001F4CC")
    icon_img = get_emoji(emoji, icon_size)     # coloured image, or None

    def draw(active):
        canvas.delete("all")
        if active:
            draw_rounded_rect(canvas, 0, 0, width, height, radius=height / 2,
                               fill=COLOR_PURPLE, outline=COLOR_PURPLE)
            text_color = "white"
        else:
            text_color = "#c3c6d8"
        if icon_img is not None:
            canvas.create_image(16, height / 2, image=icon_img, anchor="w")
        else:                                  # Pillow / emoji font missing
            canvas.create_text(16, height / 2, text=emoji, anchor="w",
                               fill=text_color, font=fonts["body"])
        canvas.create_text(16 + icon_size + 10, height / 2, text=label,
                            fill=text_color, font=fonts["body"], anchor="w")

    draw(is_active)
    canvas.pack(padx=15, pady=2)

    if command is not None:
        canvas.configure(cursor="hand2")
        canvas.bind("<Button-1>", lambda e: command())

    return {"canvas": canvas, "set_active": draw}


def build_topbar(main, fonts, on_bell=None, on_avatar=None, on_search=None):
    """Top bar. The bell and the avatar circle are clickable.
    If on_search is given, the search box becomes a real input and
    on_search(text) is called every time the text changes.
    Returns a dict with the widgets other code needs."""
    topbar = tk.Frame(main, bg=COLOR_BG)
    topbar.pack(fill="x", pady=(0, 16))

    # small requested width: the search bar still stretches to fill the row,
    # but the bell + avatar can never be pushed off the right edge
    search_canvas, search_inner = create_card(topbar, 200, 42, radius=18)
    search_canvas.pack(side="left", fill="x", expand=True, padx=(0, 10))
    search_var = tk.StringVar()
    if on_search is None:
        tk.Label(search_inner, text="🔍   Search tasks...", bg=COLOR_WHITE,
                 fg=COLOR_MUTED, font=fonts["body"]).pack(side="left", padx=14)
    else:
        tk.Label(search_inner, text="🔍", bg=COLOR_WHITE, fg=COLOR_MUTED,
                 font=fonts["body"]).pack(side="left", padx=(14, 6))
        clear = tk.Label(search_inner, text="✕", bg=COLOR_WHITE,
                         fg=COLOR_MUTED, font=fonts["small"], cursor="hand2")
        clear.bind("<Button-1>", lambda e: search_var.set(""))
        clear.bind("<Enter>", lambda e: clear.config(fg=COLOR_TEXT))
        clear.bind("<Leave>", lambda e: clear.config(fg=COLOR_MUTED))
        search_entry = tk.Entry(
            search_inner, textvariable=search_var, bd=0, relief="flat",
            font=fonts["body"], bg=COLOR_WHITE, fg=COLOR_TEXT,
            insertbackground=COLOR_TEXT, highlightthickness=0)
        search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        hint = tk.Label(search_entry, text="Search tasks...", bg=COLOR_WHITE,
                        fg=COLOR_MUTED, font=fonts["body"], cursor="xterm")
        hint.place(x=0, rely=0.5, anchor="w")
        hint.bind("<Button-1>", lambda e: search_entry.focus_set())

        def search_changed(*_):
            text = search_var.get()
            if text:
                hint.place_forget()
                clear.pack(side="right", padx=(0, 14), before=search_entry)
            else:
                hint.place(x=0, rely=0.5, anchor="w")
                clear.pack_forget()
            on_search(text)

        search_var.trace_add("write", search_changed)

    bell = RoundedBox(topbar, height=42, width=42, radius=14,
                      page_bg=COLOR_BG, fill=COLOR_WHITE, border=COLOR_LINE)
    bell.pack(side="left", padx=(0, 10))
    bell_label = tk.Label(bell.inner, text="🔔", bg=COLOR_WHITE,
                          font=fonts["body"], cursor="hand2")
    bell_label.pack(expand=True)

    # little red dot shown when there are unread notifications
    dot = tk.Canvas(bell, width=10, height=10, bg=COLOR_WHITE,
                    highlightthickness=0)
    dot.create_oval(1, 1, 9, 9, fill=COLOR_RED_TEXT, outline=COLOR_WHITE,
                    width=1)

    def set_unread(has_unread):
        if has_unread:
            dot.place(x=27, y=7)
        else:
            dot.place_forget()

    avatar = create_avatar(topbar, "", 38, fonts, COLOR_BG)
    avatar.configure(cursor="hand2")
    avatar.pack(side="left")

    if on_bell is not None:
        for widget in (bell, bell.inner, bell_label, dot):
            widget.bind("<Button-1>", lambda e: on_bell())
    if on_avatar is not None:
        avatar.bind("<Button-1>", lambda e: on_avatar())

    def set_user(name, user_id=None):
        set_avatar_initials(avatar, initials_of(name), user_id)

    return {"bell": bell, "avatar": avatar, "set_unread": set_unread,
            "set_user": set_user, "search_var": search_var,
            "clear_search": lambda: search_var.set("")}