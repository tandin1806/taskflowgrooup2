import os
import tkinter as tk

try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    PIL_OK = True
except ImportError:
    PIL_OK = False

# (font path, size to load it at). Bitmap emoji fonts only allow one size.
_FONTS = [
    (r"C:\Windows\Fonts\seguiemj.ttf", 128),                      # Windows
    ("/System/Library/Fonts/Apple Color Emoji.ttc", 160),         # macOS
    ("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 109),   # Linux
    ("/usr/share/fonts/noto/NotoColorEmoji.ttf", 109),
]

_cache = {}


def _load_font():
    for path, size in _FONTS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return None


def get_emoji(emoji, size=20):
    """Return a coloured PhotoImage for the emoji, or None if unavailable."""
    key = (emoji, size)
    if key in _cache:
        return _cache[key]

    photo = None
    if PIL_OK:
        font = _load_font()
        if font is not None:
            try:
                canvas = Image.new("RGBA", (320, 320), (0, 0, 0, 0))
                ImageDraw.Draw(canvas).text((40, 40), emoji, font=font, embedded_color=True)
                box = canvas.getbbox()
                if box:
                    glyph = canvas.crop(box)
                    side = max(glyph.size)
                    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
                    square.paste(glyph, ((side - glyph.width) // 2, (side - glyph.height) // 2))
                    square = square.resize((size, size), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(square)
            except Exception:
                photo = None

    _cache[key] = photo  # keeps a reference so Tk doesn't garbage-collect it
    return photo


def emoji_label(parent, emoji, bg, size=20, fallback_font=("Segoe UI Emoji", 11)):
    """A Label showing the emoji in colour (image), or as text if images fail."""
    img = get_emoji(emoji, size)
    if img is not None:
        lbl = tk.Label(parent, image=img, bg=bg, bd=0)
        lbl.image = img
        return lbl
    return tk.Label(parent, text=emoji, bg=bg, font=fallback_font)


# ---------------------------------------------------------------------
# Sidebar / page icons - one place so every page looks the same.
# Use nav_icon() instead of image files (Dashboard.webp, my task.jpg, ...).
# ---------------------------------------------------------------------
NAV_EMOJI = {
    "Dashboard": "\U0001F4CA",        # 📊
    "My Tasks":  "\U0001F4DD",        # 📝
    "Completed": "\u2705",            # ✅
    "Profile":   "\U0001F464",        # 👤
    "Setting":   "\u2699\ufe0f",     # ⚙️
}
NAV_EMOJI["Settings"] = NAV_EMOJI["Setting"]     # same icon, either spelling


def nav_icon(parent, name, bg, size=22):
    """Coloured emoji Label for a sidebar item / page ("Dashboard", "My Tasks",
    "Completed", "Profile", "Setting"). Change an icon once in NAV_EMOJI and
    every page that uses nav_icon() follows."""
    return emoji_label(parent, NAV_EMOJI.get(name, "\U0001F4CC"), bg, size)