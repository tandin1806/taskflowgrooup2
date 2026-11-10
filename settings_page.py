import tkinter as tk
from tkinter import messagebox

from ui_common import (
    COLOR_BG, COLOR_WHITE, COLOR_TEXT, COLOR_MUTED, COLOR_PURPLE,
    COLOR_GREEN, COLOR_LINE, COLOR_FIELD_BG,
    create_card, create_pill_button, draw_rounded_rect,
)
from my_tasks_page import FilterTab

try:                         # background desktop reminders
    import reminder_service
except ImportError:          # the page still works without it
    reminder_service = None
try:                         # coloured icons, same helper the sign-in page uses
    from emoji_icons import emoji_label
except ImportError:
    emoji_label = None

APP_VERSION = "1.0.0"
COLLEGE_LINE = "TaskFlow — Samtse College of Education"
SIGN_OUT_RED = "#ef4444"
SIGN_OUT_HOVER = "#dc2f2f"
AMBER = "#D97706"


class ScrollArea(tk.Frame):
    """A vertically scrolling area. Put the page content in `.body`.
    The scrollbar only appears when the content is taller than the window,
    and the mouse wheel scrolls it. (Also used by profile_page.py.)"""

    def __init__(self, parent, bg):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.bar = tk.Scrollbar(self, orient="vertical",
                                command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.body = tk.Frame(self.canvas, bg=bg)
        self._window = self.canvas.create_window((0, 0), window=self.body,
                                                 anchor="nw")
        self.body.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            self._window, width=e.width))
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.bind_all(sequence, self._wheel, add="+")

    def _on_scroll(self, low, high):
        if float(low) <= 0.0 and float(high) >= 1.0:
            self.bar.pack_forget()
        elif not self.bar.winfo_ismapped():
            self.bar.pack(side="right", fill="y")
        self.bar.set(low, high)

    def _wheel(self, event):
        if not self.winfo_ismapped():
            return
        try:
            under = self.winfo_containing(event.x_root, event.y_root)
        except (KeyError, tk.TclError):
            return
        while under is not None and under is not self:
            under = under.master
        if under is None:                        # pointer is elsewhere
            return
        if self.body.winfo_reqheight() <= self.canvas.winfo_height():
            return                               # everything already fits
        if event.num == 4:
            step = -1
        elif event.num == 5:
            step = 1
        else:
            step = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(step * 2, "units")


class ToggleSwitch(tk.Canvas):
    """The on/off switch. Purple when on, grey when off."""

    W, H = 44, 24

    def __init__(self, parent, value, command, page_bg=COLOR_BG):
        super().__init__(parent, width=self.W, height=self.H, bg=page_bg,
                         highlightthickness=0, cursor="hand2")
        self.value = bool(value)
        self.command = command
        self.bind("<Button-1>", lambda e: self.toggle())
        self._draw()

    def toggle(self):
        self.value = not self.value
        self._draw()
        self.command(self.value)

    def set(self, value):
        """Change the look without calling the command."""
        self.value = bool(value)
        self._draw()

    def _draw(self):
        self.delete("all")
        track = COLOR_PURPLE if self.value else "#cfd3e0"
        draw_rounded_rect(self, 0, 0, self.W, self.H, self.H / 2,
                          fill=track, outline=track)
        x = self.W - self.H + 3 if self.value else 3
        self.create_oval(x, 3, x + self.H - 6, self.H - 3, fill="white",
                         outline="white")


class SignOutButton(tk.Canvas):
    W, H = 100, 34

    def __init__(self, parent, fonts, command):
        super().__init__(parent, width=self.W, height=self.H, bg=COLOR_WHITE,
                         highlightthickness=0, cursor="hand2")
        self.fonts = fonts
        self._draw(SIGN_OUT_RED)
        self.bind("<Button-1>", lambda e: command())
        self.bind("<Enter>", lambda e: self._draw(SIGN_OUT_HOVER))
        self.bind("<Leave>", lambda e: self._draw(SIGN_OUT_RED))

    def _draw(self, color):
        self.delete("all")
        draw_rounded_rect(self, 0, 0, self.W, self.H, 10, fill=color,
                          outline=color)
        self.create_text(self.W / 2, self.H / 2, text="Sign Out",
                         fill="white", font=self.fonts["small_bold"])


class ExportButton(tk.Canvas):
    """Purple 'Export to CSV' button."""
    W, H = 150, 34

    def __init__(self, parent, fonts, command):
        super().__init__(parent, width=self.W, height=self.H, bg=COLOR_WHITE,
                         highlightthickness=0, cursor="hand2")
        self.fonts = fonts
        self._draw(COLOR_PURPLE)
        self.bind("<Button-1>", lambda e: command())
        self.bind("<Enter>", lambda e: self._draw("#5a4bd6"))
        self.bind("<Leave>", lambda e: self._draw(COLOR_PURPLE))

    def _draw(self, color):
        self.delete("all")
        draw_rounded_rect(self, 0, 0, self.W, self.H, 10, fill=color,
                          outline=color)
        self.create_text(self.W / 2, self.H / 2, text="Export to CSV",
                         fill="white", font=self.fonts["small_bold"])


class SettingsPage(tk.Frame):
    def __init__(self, parent, fonts, settings, on_change, on_sign_out,
                 on_export=None):
        """settings: {"push_notifications": bool, "theme": "light" | "dark"}.
        on_change(key, value) is called whenever the user changes one."""
        super().__init__(parent, bg=COLOR_BG)
        self.fonts = fonts
        self.on_change = on_change

        tk.Label(self, text="Settings", bg=COLOR_BG, fg=COLOR_TEXT,
                 font=fonts["heading"]).pack(anchor="w")
        tk.Label(self, text="Manage notifications, appearance and your data.",
                 bg=COLOR_BG, fg=COLOR_MUTED, font=fonts["small"]).pack(
            anchor="w", pady=(2, 0))
        self._asked_background = False

        # everything below the heading scrolls if the window is too short
        self.scroll = ScrollArea(self, COLOR_BG)
        self.scroll.pack(fill="both", expand=True)

        # ---- Notifications ----
        body = self._card(pady=(14, 0))
        self._title(body, "Notifications", "🔔")
        self.switches = {}
        self.switches["push_notifications"] = self._switch_row(
            "push_notifications", "Push Notifications",
            "Pop-up alerts in the app and desktop notifications for due and "
            "overdue tasks, also when TaskFlow is closed",
            settings["push_notifications"], parent=body, icon="💬")
        if reminder_service is not None:
            self._divider(body)
            self.reminder_box = tk.Frame(body, bg=COLOR_WHITE)
            self.reminder_box.pack(fill="x", pady=(8, 0))

        # ---- Appearance ----
        body = self._card(pady=(16, 0))
        self._title(body, "Appearance", "🎨")
        buttons = tk.Frame(body, bg=COLOR_WHITE)
        buttons.pack(anchor="w", pady=(12, 0))
        self.theme_tabs = {
            "light": FilterTab(buttons, fonts,
                               lambda: self.on_change("theme", "light"),
                               page_bg=COLOR_WHITE),
            "dark": FilterTab(buttons, fonts,
                              lambda: self.on_change("theme", "dark"),
                              page_bg=COLOR_WHITE),
        }
        for tab in self.theme_tabs.values():
            tab.pack(side="left", padx=(0, 8))

        # ---- Version ----
        body = self._card(pady=(16, 0))
        tk.Label(body, text=f"Version {APP_VERSION}", bg=COLOR_WHITE,
                 fg=COLOR_MUTED, font=fonts["small_bold"]).pack(anchor="w")
        tk.Label(body, text=COLLEGE_LINE, bg=COLOR_WHITE, fg=COLOR_MUTED,
                 font=fonts["small"]).pack(anchor="w", pady=(6, 0))

        # ---- Your data (CSV export) ----
        if on_export is not None:
            body = self._card(pady=(16, 0))
            self._title(body, "Your Data", "📁")
            tk.Label(body, text="Save all your tasks as a spreadsheet "
                                "(opens in Excel or Google Sheets).",
                     bg=COLOR_WHITE, fg=COLOR_MUTED,
                     font=fonts["small"]).pack(anchor="w", pady=(4, 8))
            ExportButton(body, fonts, on_export).pack(anchor="w")

        # ---- Account ----
        body = self._card(pady=(16, 0))
        self._title(body, "Account", "👤")
        SignOutButton(body, fonts, on_sign_out).pack(anchor="e",
                                                     pady=(4, 0))

        self.sync(settings)

    # ---- building blocks -----------------------------------------------------
    def _icon(self, parent, icon, bg, size=20):
        try:
            return emoji_label(parent, icon, bg, size=size)
        except Exception:                       # no icon helper / image
            return tk.Label(parent, text=icon, bg=bg,
                            font=("Segoe UI Emoji", 12))

    def _title(self, parent, text, icon):
        """Card heading with a small coloured icon in front."""
        row = tk.Frame(parent, bg=COLOR_WHITE)
        row.pack(anchor="w")
        self._icon(row, icon, COLOR_WHITE, 18).pack(side="left", padx=(0, 8))
        tk.Label(row, text=text, bg=COLOR_WHITE, fg=COLOR_TEXT,
                 font=self.fonts["card_title"]).pack(side="left")

    def _divider(self, parent):
        tk.Frame(parent, bg=COLOR_LINE, height=1).pack(fill="x", pady=2)

    def _switch_row(self, key, title, subtitle, value, parent=None,
                    icon=None):
        host = parent if parent is not None else self
        bg = COLOR_WHITE if parent is not None else COLOR_BG
        row = tk.Frame(host, bg=bg)
        row.pack(fill="x", pady=8)
        if icon:
            self._icon(row, icon, bg).pack(side="left", padx=(0, 12))
        text = tk.Frame(row, bg=bg)
        text.pack(side="left")
        tk.Label(text, text=title, bg=bg, fg=COLOR_TEXT,
                 font=self.fonts["label"]).pack(anchor="w")
        tk.Label(text, text=subtitle, bg=bg, fg=COLOR_MUTED,
                 font=self.fonts["small"], justify="left",
                 wraplength=420).pack(anchor="w")
        switch = ToggleSwitch(row, value,
                              lambda v, k=key: self._changed(k, v),
                              page_bg=bg)
        switch.pack(side="right")
        return switch

    def _changed(self, key, value):
        """Reports the change as before. The first time Push Notifications
        is switched ON while the background helper is off, offers to start
        it."""
        self.on_change(key, value)
        if (value and reminder_service is not None
                and key == "push_notifications"
                and not self._asked_background
                and not reminder_service.is_running()):
            self._asked_background = True
            if messagebox.askyesno(
                    "Background reminders",
                    "Turn on background reminders so desktop notifications "
                    "also appear when TaskFlow is closed?", parent=self):
                self._toggle_reminders()

    # ---- background reminders (reminder_service.py) --------------------------
    def _refresh_reminders(self):
        box = getattr(self, "reminder_box", None)
        if box is None or reminder_service is None:
            return
        for child in box.winfo_children():
            child.destroy()
        f = self.fonts
        running = reminder_service.is_running()
        row = tk.Frame(box, bg=COLOR_WHITE)
        row.pack(fill="x")
        self._icon(row, "⏰", COLOR_WHITE).pack(side="left", padx=(0, 12))
        text = tk.Frame(row, bg=COLOR_WHITE)
        text.pack(side="left")
        tk.Label(text, text="Background reminders", bg=COLOR_WHITE,
                 fg=COLOR_TEXT, font=f["label"]).pack(anchor="w")
        tk.Label(text,
                 text=("●  Active - desktop reminders appear even when "
                       "TaskFlow is closed" if running else
                       "○  Off - desktop reminders only appear while "
                       "TaskFlow is open"),
                 bg=COLOR_WHITE, fg=COLOR_GREEN if running else AMBER,
                 font=f["small_bold"], justify="left",
                 wraplength=400).pack(anchor="w")
        if running:
            button = create_pill_button(row, "Turn off", 90, 30, f,
                                        bg=COLOR_FIELD_BG, fg=COLOR_MUTED,
                                        command=self._toggle_reminders)
        else:
            button = create_pill_button(row, "Turn on", 90, 30, f,
                                        command=self._toggle_reminders)
        button.pack(side="right")

    def _toggle_reminders(self):
        if reminder_service.is_running():
            ok, message = reminder_service.disable()
        else:
            ok, message = reminder_service.enable()
        self._refresh_reminders()
        (messagebox.showinfo if ok else messagebox.showerror)(
            "Background reminders", message, parent=self)

    def _card(self, pady):
        """A white rounded card that grows to fit what is put inside.
        Returns the frame to put the content in."""
        canvas, inner = create_card(self.scroll.body, 100, 60, radius=14)
        canvas.pack(fill="x", pady=pady)
        content = tk.Frame(inner, bg=COLOR_WHITE)
        content.pack(fill="x", padx=20, pady=16)

        def fit(event=None):
            canvas.configure(height=content.winfo_reqheight() + 34)

        content.bind("<Configure>", fit)
        canvas.after_idle(fit)
        return content

    # ---- keeping the page in step with the saved settings -------------------
    def sync(self, settings):
        """Make the switches and the Light / Dark buttons match `settings`
        (used when another account signs in, and after every change)."""
        self.switches["push_notifications"].set(
            settings["push_notifications"])
        dark = settings["theme"] == "dark"
        self.theme_tabs["light"].set("Light", not dark)
        self.theme_tabs["dark"].set("Dark", dark)
        self._refresh_reminders()