import tkinter as tk

from ui_common import (
    COLOR_WHITE, COLOR_TEXT, COLOR_MUTED, COLOR_LINE, COLOR_RED_TEXT,
    COLOR_GREEN, COLOR_PURPLE, COLOR_FIELD_BG, COLOR_FIELD_LINE,
    create_avatar, set_avatar_initials, initials_of, shorten,
)

# dot color per notification type
KIND_COLORS = {
    "added": COLOR_PURPLE,
    "completed": COLOR_GREEN,
    "reopened": "#8a8fa3",
    "today": COLOR_RED_TEXT,
    "soon": "#f59e0b",
}
MAX_SHOWN = 5


class TopbarMenus:
    def __init__(self, anchor, fonts, store, center, topbar, get_user,
                 on_sign_out):
        """anchor: the frame the panels are placed in (the main area).
        topbar: the dict returned by build_topbar().
        get_user(): returns {"name":..., "email":...} or None."""
        self.anchor = anchor
        self.fonts = fonts
        self.store = store
        self.center = center
        self.topbar = topbar
        self.get_user = get_user
        self.on_sign_out = on_sign_out

        self.panel = None          # the panel that is open right now
        self.kind = None           # "bell" or "profile"

        # keep the red dot on the bell in sync
        center.subscribe(self.update_badge)
        self.update_badge()

        # any click outside the open panel closes it
        anchor.winfo_toplevel().bind("<Button-1>", self._on_any_click,
                                     add="+")

    # ---- the red dot -----------------------------------------------------
    def update_badge(self):
        self.topbar["set_unread"](self.center.has_unread())

    # ---- open / close ----------------------------------------------------
    def toggle_notifications(self):
        if self.kind == "bell":
            self.close()
        else:
            self._open("bell")

    def toggle_profile(self):
        if self.kind == "profile":
            self.close()
        else:
            self._open("profile")

    def close(self):
        if self.panel is not None:
            self.panel.destroy()
        self.panel = None
        self.kind = None
        self.topbar["bell"].set_highlight(False)

    def _open(self, kind):
        self.close()
        if kind == "bell":
            panel = self._build_notifications()
            self.topbar["bell"].set_highlight(True)
            self.center.mark_all_read()      # they've now been seen
        else:
            panel = self._build_profile()
        panel.place(in_=self.anchor, relx=1.0, x=0, y=50, anchor="ne",
                    width=panel.panel_width)
        panel.lift()
        self.panel, self.kind = panel, kind

    def _on_any_click(self, event):
        if self.panel is None:
            return
        widget = event.widget
        if not isinstance(widget, tk.Misc):
            return
        while widget is not None:
            if (widget is self.panel or widget is self.topbar["bell"]
                    or widget is self.topbar["avatar"]):
                return              # clicks on the panel / buttons handled there
            widget = widget.master
        self.close()

    # ---- helpers ---------------------------------------------------------
    def _new_panel(self, width):
        panel = tk.Frame(self.anchor, bg=COLOR_WHITE,
                         highlightbackground=COLOR_FIELD_LINE,
                         highlightthickness=1)
        panel.panel_width = width
        return panel

    def _line(self, parent):
        tk.Frame(parent, bg=COLOR_LINE, height=1).pack(fill="x")

    # ---- Notifications panel ------------------------------------------------
    def _build_notifications(self):
        fonts = self.fonts
        panel = self._new_panel(320)

        header = tk.Frame(panel, bg=COLOR_WHITE)
        header.pack(fill="x", padx=16, pady=(14, 12))
        tk.Label(header, text="Notifications", bg=COLOR_WHITE, fg=COLOR_TEXT,
                 font=fonts["card_title"]).pack(side="left")
        close = tk.Label(header, text="Close", bg=COLOR_WHITE,
                         fg=COLOR_MUTED, font=fonts["small"], cursor="hand2")
        close.pack(side="right")
        close.bind("<Button-1>", lambda e: self.close())
        close.bind("<Enter>", lambda e: close.config(fg=COLOR_TEXT))
        close.bind("<Leave>", lambda e: close.config(fg=COLOR_MUTED))
        self._line(panel)

        items = self.center.new_items()
        if not items:
            tk.Label(panel, text="No new notifications", bg=COLOR_WHITE,
                     fg=COLOR_MUTED, font=fonts["body"]).pack(pady=26)
            return panel

        for note in items[:MAX_SHOWN]:
            row = tk.Frame(panel, bg=COLOR_WHITE)
            row.pack(fill="x", padx=16, pady=9)

            dot = tk.Canvas(row, width=10, height=10, bg=COLOR_WHITE,
                            highlightthickness=0)
            color = KIND_COLORS.get(note.kind, COLOR_PURPLE)
            dot.create_oval(1, 1, 9, 9, fill=color, outline=color)
            dot.pack(side="left", anchor="n", pady=(4, 0), padx=(0, 10))

            when = tk.Label(row, text=note.time.strftime("%I:%M %p").lstrip("0"),
                            bg=COLOR_WHITE, fg=COLOR_MUTED, font=fonts["small"])
            when.pack(side="right", anchor="n")

            col = tk.Frame(row, bg=COLOR_WHITE)
            col.pack(side="left", fill="x", expand=True)
            tk.Label(col, text=note.title, bg=COLOR_WHITE, fg=COLOR_TEXT,
                     font=fonts["small_bold"], anchor="w").pack(fill="x")
            tk.Label(col, text=note.text, bg=COLOR_WHITE, fg=COLOR_MUTED,
                     font=fonts["small"], anchor="w", justify="left",
                     wraplength=200).pack(fill="x")
            self._line(panel)

        extra = len(items) - MAX_SHOWN
        if extra > 0:
            tk.Label(panel, text=f"+ {extra} more", bg=COLOR_WHITE,
                     fg=COLOR_MUTED, font=fonts["small"]).pack(pady=8)
        return panel

    # ---- Profile panel ------------------------------------------------------
    def _build_profile(self):
        fonts = self.fonts
        user = self.get_user() or {"name": "Student", "email": ""}
        panel = self._new_panel(270)

        head = tk.Frame(panel, bg=COLOR_WHITE)
        head.pack(fill="x", padx=16, pady=14)
        photo_avatar = create_avatar(head, initials_of(user["name"]), 40,
                                     fonts, COLOR_WHITE)
        photo_avatar.pack(side="left", padx=(0, 12))
        set_avatar_initials(photo_avatar, initials_of(user["name"]),
                            user.get("id"))
        text = tk.Frame(head, bg=COLOR_WHITE)
        text.pack(side="left", fill="x", expand=True)
        tk.Label(text, text=shorten(user["name"], 22), bg=COLOR_WHITE,
                 fg=COLOR_TEXT, font=fonts["card_title"],
                 anchor="w").pack(fill="x")
        if user.get("email"):
            tk.Label(text, text=shorten(user["email"], 28), bg=COLOR_WHITE,
                     fg=COLOR_MUTED, font=fonts["small"],
                     anchor="w").pack(fill="x")
        self._line(panel)

        store = self.store
        summary = tk.Frame(panel, bg=COLOR_WHITE)
        summary.pack(fill="x", padx=16, pady=12)
        for number, label in ((store.total, "Tasks"),
                              (store.pending_count, "Pending"),
                              (store.completed_count, "Done")):
            cell = tk.Frame(summary, bg=COLOR_WHITE)
            cell.pack(side="left", expand=True)
            tk.Label(cell, text=str(number), bg=COLOR_WHITE, fg=COLOR_TEXT,
                     font=fonts["card_title"]).pack()
            tk.Label(cell, text=label, bg=COLOR_WHITE, fg=COLOR_MUTED,
                     font=fonts["small"]).pack()
        self._line(panel)

        sign_out = tk.Label(panel, text="⏻   Sign out", bg=COLOR_WHITE,
                            fg=COLOR_RED_TEXT, font=fonts["body"],
                            anchor="w", padx=16, pady=11, cursor="hand2")
        sign_out.pack(fill="x")
        sign_out.bind("<Enter>", lambda e: sign_out.config(bg=COLOR_FIELD_BG))
        sign_out.bind("<Leave>", lambda e: sign_out.config(bg=COLOR_WHITE))
        sign_out.bind("<Button-1>", lambda e: self._sign_out())
        return panel

    def _sign_out(self):
        self.close()
        self.on_sign_out()