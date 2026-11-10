import tkinter as tk

from ui_common import (
    COLOR_WHITE, COLOR_TEXT, COLOR_MUTED, COLOR_PURPLE, COLOR_FIELD_LINE,
)
from topbar_menus import KIND_COLORS


class ToastManager:
    WIDTH = 300
    LIFETIME_MS = 4500
    MARGIN = 24

    def __init__(self, root, fonts, center):
        self.root = root
        self.fonts = fonts
        self.center = center
        self.enabled = False
        self._count = 0              # how many notifications were already seen
        self._toasts = []
        center.subscribe(self._on_change)

    # ---- following the notification bell ----------------------------------
    def sync(self):
        """Treat everything in the bell right now as already seen."""
        self._count = len(self.center.items)

    def _on_change(self):
        items = self.center.items
        if len(items) < self._count:          # the list was reset
            self._count = len(items)
        new = items[self._count:]
        self._count = len(items)
        if self.enabled:
            for note in new:
                self.show(note.title, note.text, note.kind)

    # ---- showing / hiding ---------------------------------------------------
    def show(self, title, text, kind="added"):
        fonts = self.fonts
        toast = tk.Toplevel(self.root)
        toast.withdraw()
        toast.overrideredirect(True)
        try:
            toast.attributes("-topmost", True)
        except tk.TclError:
            pass
        toast.configure(bg=COLOR_FIELD_LINE)           # 1px border

        card = tk.Frame(toast, bg=COLOR_WHITE)
        card.pack(padx=1, pady=1)
        row = tk.Frame(card, bg=COLOR_WHITE)
        row.pack(padx=14, pady=12)

        dot = tk.Canvas(row, width=10, height=10, bg=COLOR_WHITE,
                        highlightthickness=0)
        color = KIND_COLORS.get(kind, COLOR_PURPLE)
        dot.create_oval(1, 1, 9, 9, fill=color, outline=color)
        dot.pack(side="left", anchor="n", pady=(4, 0), padx=(0, 10))

        col = tk.Frame(row, bg=COLOR_WHITE)
        col.pack(side="left")
        tk.Label(col, text=title, bg=COLOR_WHITE, fg=COLOR_TEXT,
                 font=fonts["small_bold"], anchor="w").pack(fill="x")
        tk.Label(col, text=text, bg=COLOR_WHITE, fg=COLOR_MUTED,
                 font=fonts["small"], anchor="w", justify="left",
                 wraplength=self.WIDTH - 70).pack(fill="x")

        self._bind_click(toast, lambda e, t=toast: self._close(t))

        self._toasts.append(toast)
        self._layout()
        toast.deiconify()
        toast.lift()
        toast.after(self.LIFETIME_MS, lambda t=toast: self._close(t))

    def _bind_click(self, widget, handler):
        widget.bind("<Button-1>", handler)
        for child in widget.winfo_children():
            self._bind_click(child, handler)

    def _close(self, toast):
        if toast not in self._toasts:
            return
        self._toasts.remove(toast)
        try:
            toast.destroy()
        except tk.TclError:
            pass
        self._layout()

    def dismiss_all(self):
        for toast in list(self._toasts):
            self._close(toast)

    def _layout(self):
        """Stack the toasts up from the bottom-right corner of the window."""
        self.root.update_idletasks()
        right = (self.root.winfo_rootx() + self.root.winfo_width()
                 - self.MARGIN)
        y = (self.root.winfo_rooty() + self.root.winfo_height()
             - self.MARGIN)
        for toast in reversed(self._toasts):           # newest at the bottom
            toast.update_idletasks()
            width, height = toast.winfo_reqwidth(), toast.winfo_reqheight()
            y -= height
            toast.geometry(f"+{max(right - width, 0)}+{max(y, 0)}")
            y -= 10
