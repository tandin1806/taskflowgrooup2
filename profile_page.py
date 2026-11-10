import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox

from ui_common import (
    COLOR_BG, COLOR_WHITE, COLOR_TEXT, COLOR_MUTED, COLOR_LINE,
    COLOR_PURPLE, COLOR_GREEN, COLOR_FIELD_BG, COLOR_FIELD_LINE,
    create_avatar, create_pill_button, initials_of, shorten,
    format_percent,
)
from settings_page import ScrollArea, SIGN_OUT_RED
from auth_pages import password_problem, validate_email, ask_for_code

try:                                   # needed for profile photos
    from PIL import Image, ImageDraw, ImageTk
except ImportError:
    Image = None

PHOTO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "avatars")    # one picture per account
AMBER = "#D97706"                      # "attention" colour for 2FA off / Basic
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

VIEW_FIELDS = [("Full Name", "name"), ("Email Address", "email"),
               ("University", "university"),
               ("Program / Course", "program"),
               ("Member Since", "member_since")]
EDIT_FIELDS = VIEW_FIELDS[:4]          # member since can't be edited


class ProfilePage(tk.Frame):
    def __init__(self, parent, fonts, store, db, get_user, on_saved,
                 on_deleted=None):
        """db: the Database. get_user(): returns {"id","name","email"} of the
        signed-in account (or None). on_saved(name, email): called after the
        profile was changed. on_deleted(): called after the account has been
        permanently deleted (app.py signs the user out)."""
        super().__init__(parent, bg=COLOR_BG)
        self.fonts = fonts
        self.store = store
        self.db = db
        self.get_user = get_user
        self.on_saved = on_saved
        self.on_deleted = on_deleted
        self.editing = False
        self.entries = {}
        self.data = {"name": "", "email": "", "university": "",
                     "program": "", "member_since": "",
                     "password_changed": "Never"}

        tk.Label(self, text="Profile", bg=COLOR_BG, fg=COLOR_TEXT,
                 font=fonts["heading"]).pack(anchor="w")
        tk.Label(self, text="Manage your account details and keep your "
                            "account secure.", bg=COLOR_BG, fg=COLOR_MUTED,
                 font=fonts["small"]).pack(anchor="w", pady=(2, 0))

        # the cards scroll if the window is too short to show them all
        self.scroll = ScrollArea(self, COLOR_BG)
        self.scroll.pack(fill="both", expand=True, pady=(16, 0))
        grid = tk.Frame(self.scroll.body, bg=COLOR_BG)
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=1, minsize=240)
        grid.columnconfigure(1, weight=2, minsize=400)
        self.left = tk.Frame(grid, bg=COLOR_BG)
        self.left.grid(row=0, column=0, sticky="new", padx=(0, 14))
        self.right = tk.Frame(grid, bg=COLOR_BG)
        self.right.grid(row=0, column=1, sticky="new")

        store.subscribe(self.draw_summary)      # stats follow the tasks
        self.draw_summary()
        self.draw_account()

    # ------------------------------------------------------------------
    # public (used by app.py)
    # ------------------------------------------------------------------
    def load(self):
        """Reads the signed-in account from the database and redraws.
        app.py calls this every time the Profile page is opened."""
        user = self.get_user()
        if user is None:
            return
        self.data = self.db.get_profile(user["id"])
        self.editing = False
        self.draw_summary()
        self.draw_account()

    # ------------------------------------------------------------------
    # small helpers
    # ------------------------------------------------------------------
    def _card(self, parent):
        return tk.Frame(parent, bg=COLOR_WHITE,
                        highlightbackground=COLOR_FIELD_LINE,
                        highlightthickness=1)

    def _entry(self, parent, value="", show=""):
        entry = tk.Entry(parent, relief="flat", bg=COLOR_FIELD_BG,
                         fg=COLOR_TEXT, font=self.fonts["body"], show=show,
                         highlightthickness=1,
                         highlightbackground=COLOR_FIELD_LINE,
                         highlightcolor=COLOR_PURPLE,
                         insertbackground=COLOR_PURPLE)
        entry.insert(0, value)
        return entry

    def _tooltip(self, widget, text):
        """Small dark label that appears while the mouse is over `widget`."""
        tip = {"win": None}

        def show(_event):
            if tip["win"] is not None:
                return
            win = tk.Toplevel(widget)
            win.wm_overrideredirect(True)
            win.geometry(f"+{widget.winfo_rootx() + 20}"
                         f"+{widget.winfo_rooty() + widget.winfo_height() + 6}")
            tk.Label(win, text=text, bg="#1e293b", fg="white",
                     font=self.fonts["small"], padx=8, pady=3).pack()
            tip["win"] = win

        def hide(_event=None):
            if tip["win"] is not None:
                tip["win"].destroy()
                tip["win"] = None

        widget.bind("<Enter>", show, add="+")
        widget.bind("<Leave>", hide, add="+")
        widget.bind("<Button-1>", hide, add="+")
        widget.bind("<Destroy>", hide, add="+")

    def _divider(self, parent):
        tk.Frame(parent, bg=COLOR_LINE, height=1).pack(fill="x", padx=18)

    def _chip(self, parent, text, color):
        """Small solid status badge (white text on a colour)."""
        return tk.Label(parent, text=text, bg=color, fg=COLOR_WHITE,
                        font=self.fonts["small_bold"], padx=9, pady=2)

    def _security_checks(self):
        changed = str(self.data.get("password_changed") or "").strip().lower()
        return [("Account is protected by a password", True),
                ("Password has been updated", changed not in ("", "never", "-"))]

    def _security_level(self):
        """-> (checks passed, label, colour) for the security meter."""
        passed = sum(1 for _, ok in self._security_checks() if ok)
        label, color = {1: ("Basic", AMBER),
                        2: ("Strong", COLOR_GREEN)}[max(1, passed)]
        return passed, label, color

    # ------------------------------------------------------------------
    # left: summary card
    # ------------------------------------------------------------------
    def draw_summary(self):
        for child in self.left.winfo_children():
            child.destroy()
        f, store, data = self.fonts, self.store, self.data
        card = self._card(self.left)
        card.pack(fill="x")
        tk.Frame(card, bg=COLOR_PURPLE, height=6).pack(fill="x")

        holder = tk.Frame(card, bg=COLOR_WHITE)
        holder.pack(pady=(22, 12))
        photo = self._photo_image(72)
        if photo is not None:
            self._summary_photo = photo          # keep a reference
            avatar = tk.Label(holder, image=photo, bg=COLOR_WHITE, bd=0)
        else:
            avatar = create_avatar(holder, initials_of(data["name"]), 72, f,
                                   COLOR_WHITE)
            avatar.itemconfig(avatar.initials_item, font=f["dialog_title"])
        avatar.pack()
        plus = tk.Canvas(holder, width=26, height=26, bg=COLOR_WHITE,
                         highlightthickness=0)
        plus.create_oval(1, 1, 25, 25, fill=COLOR_PURPLE, outline=COLOR_WHITE,
                         width=2)
        plus.create_text(13, 13, text="+", fill=COLOR_WHITE,
                         font=("Segoe UI", 13, "bold"))
        plus.place(relx=1.0, rely=1.0, x=2, y=-2, anchor="se")
        for piece in (avatar, plus):
            piece.config(cursor="hand2")
            piece.bind("<Button-1>", lambda _e: self.upload_photo(), add="+")
            self._tooltip(piece, "Choose a profile picture")
        tk.Label(card, text=shorten(data["name"] or "-", 26), bg=COLOR_WHITE,
                 fg=COLOR_TEXT, font=f["card_title"]).pack()
        tk.Label(card, text="Student", bg=COLOR_WHITE, fg=COLOR_MUTED,
                 font=f["small"]).pack(pady=(2, 2))
        if photo is not None:
            remove = tk.Label(card, text="Remove photo", bg=COLOR_WHITE,
                              fg=COLOR_MUTED, font=f["small"], cursor="hand2")
            remove.pack()
            remove.bind("<Button-1>", lambda _e: self.remove_photo())
        tk.Label(card, text=shorten(data["email"], 32), bg=COLOR_WHITE,
                 fg=COLOR_MUTED, font=f["small"]).pack(pady=(0, 10))

        _, level, level_color = self._security_level()
        self._chip(card, f"Security: {level}", level_color).pack(
            pady=(0, 18))
        self._divider(card)

        # task completion: label, percentage, bar
        percent = format_percent(store.percent)
        tk.Label(card, text="TASK COMPLETION", bg=COLOR_WHITE,
                 fg=COLOR_MUTED, font=f["small"]).pack(
            anchor="w", padx=18, pady=(16, 0))
        tk.Label(card, text=f"{percent}%", bg=COLOR_WHITE, fg=COLOR_PURPLE,
                 font=f["small_bold"]).pack(anchor="e", padx=18,
                                            pady=(6, 3))
        track = tk.Frame(card, bg=COLOR_LINE, height=6)
        track.pack(fill="x", padx=18)
        track.pack_propagate(False)
        tk.Frame(track, bg=COLOR_PURPLE).place(
            relx=0, rely=0, relwidth=percent / 100, relheight=1)

        # Total | Pending | Done
        counts = tk.Frame(card, bg=COLOR_WHITE)
        counts.pack(fill="x", padx=12, pady=(18, 16))
        items = [(store.total, "Total", COLOR_TEXT),
                 (store.pending_count, "Pending", COLOR_PURPLE),
                 (store.completed_count, "Done", COLOR_GREEN)]
        col = 0
        for i, (number, label, color) in enumerate(items):
            cell = tk.Frame(counts, bg=COLOR_WHITE)
            cell.grid(row=0, column=col, sticky="ew")
            counts.columnconfigure(col, weight=1)
            tk.Label(cell, text=str(number), bg=COLOR_WHITE, fg=color,
                     font=f["card_title"]).pack()
            tk.Label(cell, text=label, bg=COLOR_WHITE, fg=COLOR_MUTED,
                     font=f["small"]).pack()
            col += 1
            if i < len(items) - 1:
                tk.Frame(counts, bg=COLOR_LINE, width=1).grid(
                    row=0, column=col, sticky="ns", pady=4)
                col += 1

        self._divider(card)
        tk.Label(card, text=f"Member since {data['member_since']}",
                 bg=COLOR_WHITE, fg=COLOR_MUTED, font=f["small"]).pack(
            pady=(18, 22))

    # ------------------------------------------------------------------
    # right: account information + security
    # ------------------------------------------------------------------
    def draw_account(self):
        for child in self.right.winfo_children():
            child.destroy()
        self.entries = {}
        if self.editing:
            self._draw_edit_card()
        else:
            self._draw_view_card()
        self._draw_security_card()

    def _draw_view_card(self):
        f = self.fonts
        card = self._card(self.right)
        card.pack(fill="x", pady=(0, 14))
        head = tk.Frame(card, bg=COLOR_WHITE)
        head.pack(fill="x", padx=18, pady=(16, 8))
        tk.Label(head, text="Account Information", bg=COLOR_WHITE,
                 fg=COLOR_TEXT, font=f["card_title"]).pack(side="left")
        create_pill_button(head, "✎  Edit", 80, 28, f, bg=COLOR_FIELD_BG,
                           fg=COLOR_PURPLE,
                           command=self.start_edit).pack(side="right")
        for index, (label, key) in enumerate(VIEW_FIELDS):
            if index:
                self._divider(card)
            row = tk.Frame(card, bg=COLOR_WHITE)
            row.pack(fill="x", padx=18, pady=6)
            tk.Label(row, text=label, bg=COLOR_WHITE, fg=COLOR_MUTED,
                     font=f["small"]).pack(side="left")
            tk.Label(row, text=shorten(self.data[key] or "-", 44),
                     bg=COLOR_WHITE, fg=COLOR_TEXT, font=f["small_bold"],
                     anchor="e").pack(side="right")
        tk.Frame(card, bg=COLOR_WHITE, height=10).pack()

    def _draw_edit_card(self):
        f = self.fonts
        card = self._card(self.right)
        card.pack(fill="x", pady=(0, 14))
        tk.Label(card, text="Account Information", bg=COLOR_WHITE,
                 fg=COLOR_TEXT, font=f["card_title"]).pack(
            anchor="w", padx=18, pady=(16, 8))
        for label, key in EDIT_FIELDS:
            tk.Label(card, text=label, bg=COLOR_WHITE, fg=COLOR_MUTED,
                     font=f["small"]).pack(anchor="w", padx=18, pady=(6, 3))
            entry = self._entry(card, self.data[key])
            entry.pack(fill="x", padx=18, ipady=6)
            self.entries[key] = entry
        buttons = tk.Frame(card, bg=COLOR_WHITE)
        buttons.pack(fill="x", padx=18, pady=16)
        create_pill_button(buttons, "Save changes", 112, 32, f,
                           command=self.save).pack(side="right")
        create_pill_button(buttons, "Cancel", 80, 32, f, bg=COLOR_FIELD_BG,
                           fg=COLOR_MUTED,
                           command=self.cancel_edit).pack(side="right",
                                                          padx=(0, 8))
        first = self.entries["name"]
        first.focus_set()
        first.icursor("end")

    def _draw_security_card(self):
        f = self.fonts
        card = self._card(self.right)
        card.pack(fill="x")
        head = tk.Frame(card, bg=COLOR_WHITE)
        head.pack(fill="x", padx=18, pady=(16, 8))
        tk.Label(head, text="Security", bg=COLOR_WHITE, fg=COLOR_TEXT,
                 font=f["card_title"]).pack(side="left")
        _, level, color = self._security_level()
        self._chip(head, level, color).pack(side="right")
        self._divider(card)

        # password
        row = tk.Frame(card, bg=COLOR_WHITE)
        row.pack(fill="x", padx=18, pady=10)
        words = tk.Frame(row, bg=COLOR_WHITE)
        words.pack(side="left")
        tk.Label(words, text="Password", bg=COLOR_WHITE, fg=COLOR_TEXT,
                 font=f["small_bold"]).pack(anchor="w")
        tk.Label(words,
                 text=f"Last changed: {self.data['password_changed']}",
                 bg=COLOR_WHITE, fg=COLOR_MUTED, font=f["small"]).pack(
            anchor="w", pady=(2, 0))
        create_pill_button(row, "Change", 80, 28, f, bg=COLOR_FIELD_BG,
                           fg=COLOR_PURPLE,
                           command=self.change_password).pack(side="right")

        self._divider(card)

        # two-factor authentication (a code is emailed at sign-in)
        user = self.get_user()
        twofa_on = bool(user) and self.db.is_2fa_enabled(user["id"])
        row = tk.Frame(card, bg=COLOR_WHITE)
        row.pack(fill="x", padx=18, pady=10)
        words = tk.Frame(row, bg=COLOR_WHITE)
        words.pack(side="left")
        tk.Label(words, text="Two-factor authentication", bg=COLOR_WHITE,
                 fg=COLOR_TEXT, font=f["small_bold"]).pack(anchor="w")
        tk.Label(words,
                 text="Enabled" if twofa_on else "Not enabled",
                 bg=COLOR_WHITE, fg=COLOR_MUTED, font=f["small"]).pack(
            anchor="w", pady=(2, 0))
        create_pill_button(row, "Disable" if twofa_on else "Enable", 80, 28, f,
                           bg=COLOR_FIELD_BG, fg=COLOR_PURPLE,
                           command=self.toggle_2fa).pack(side="right")

        self._divider(card)

        # delete account
        row = tk.Frame(card, bg=COLOR_WHITE)
        row.pack(fill="x", padx=18, pady=(10, 16))
        words = tk.Frame(row, bg=COLOR_WHITE)
        words.pack(side="left")
        tk.Label(words, text="Delete account", bg=COLOR_WHITE,
                 fg=SIGN_OUT_RED, font=f["small_bold"]).pack(anchor="w")
        tk.Label(words,
                 text="Permanently remove your account and all your tasks.",
                 bg=COLOR_WHITE, fg=COLOR_MUTED, font=f["small"]).pack(
            anchor="w", pady=(2, 0))
        create_pill_button(row, "Delete", 80, 28, f, bg=SIGN_OUT_RED,
                           command=self.delete_account).pack(side="right")

    # ------------------------------------------------------------------
    # actions
    # ------------------------------------------------------------------
    def start_edit(self):
        self.editing = True
        self.draw_account()

    def cancel_edit(self):
        self.editing = False
        self.draw_account()

    def save(self):
        values = {key: entry.get().strip()
                  for key, entry in self.entries.items()}
        if not values["name"]:
            messagebox.showerror("Missing information",
                                 "Please enter your full name.", parent=self)
            return
        email_problem = validate_email(values["email"])
        if email_problem:
            messagebox.showerror("Invalid email", email_problem,
                                 parent=self)
            return
        user = self.get_user()
        try:
            self.db.update_profile(user["id"], values["name"],
                                   values["email"], values["university"],
                                   values["program"])
        except ValueError as error:          # email used by another account
            messagebox.showerror("Email in use", str(error), parent=self)
            return
        self.data = self.db.get_profile(user["id"])
        self.editing = False
        self.draw_summary()
        self.draw_account()
        self.on_saved(self.data["name"], self.data["email"])
        messagebox.showinfo("Profile updated",
                            "Your profile information has been saved.",
                            parent=self)

    # ---- profile photo (saved as avatars/user_<id>.png) -----------------
    def _photo_path(self, user_id=None):
        if user_id is None:
            user = self.get_user()
            if user is None:
                return None
            user_id = user["id"]
        return os.path.join(PHOTO_DIR, f"user_{user_id}.png")

    def _photo_image(self, size):
        """The saved photo as a round image, or None if there is none."""
        path = self._photo_path()
        if Image is None or path is None or not os.path.exists(path):
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

    def upload_photo(self):
        if Image is None:
            messagebox.showinfo("Profile photo",
                                "Photo upload needs the Pillow package.\n"
                                "Install it with:  pip install pillow",
                                parent=self)
            return
        chosen = filedialog.askopenfilename(
            parent=self, title="Choose a photo",
            filetypes=[("Pictures", "*.png *.jpg *.jpeg *.gif *.bmp"),
                       ("All files", "*.*")])
        if not chosen:
            return
        try:
            picture = Image.open(chosen).convert("RGB")
            width, height = picture.size
            side = min(width, height)             # square crop from the middle
            left, top = (width - side) // 2, (height - side) // 2
            picture = picture.crop((left, top, left + side, top + side))
            os.makedirs(PHOTO_DIR, exist_ok=True)
            picture.resize((256, 256)).save(self._photo_path(), "PNG")
        except Exception:
            messagebox.showerror("Profile photo",
                                 "That file could not be opened as a "
                                 "picture.", parent=self)
            return
        self.draw_summary()
        self.draw_account()
        self.on_saved(self.data["name"], self.data["email"])   # update sidebar + top bar

    def remove_photo(self, user_id=None):
        path = self._photo_path(user_id)
        if path and os.path.exists(path):
            os.remove(path)
        self.draw_summary()
        self.draw_account()
        self.on_saved(self.data["name"], self.data["email"])   # update sidebar + top bar

    def toggle_2fa(self):
        """Turns 2FA on or off. Turning it ON emails a code once to the
        account's email; the user types it to confirm the email works."""
        user = self.get_user()
        if user is None:
            return
        turning_on = not self.db.is_2fa_enabled(user["id"])
        if turning_on:
            if not ask_for_code(self, user["email"], "turning on 2FA"):
                return
        elif not messagebox.askyesno("Two-factor authentication",
                                     "Turn off two-factor authentication?",
                                     parent=self):
            return
        self.db.set_2fa_enabled(user["id"], turning_on)
        messagebox.showinfo("Two-factor authentication",
                            "Two-factor authentication is now "
                            + ("ON." if turning_on else "OFF."), parent=self)
        self.draw_account()

    def change_password(self):
        f = self.fonts
        overlay = tk.Frame(self, bg=COLOR_BG)
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        dialog = self._card(overlay)
        dialog.place(relx=0.5, rely=0.38, anchor="center", width=360)

        tk.Label(dialog, text="Change Password", bg=COLOR_WHITE,
                 fg=COLOR_TEXT, font=f["dialog_title"]).pack(
            anchor="w", padx=20, pady=(18, 2))
        tk.Label(dialog, text="Update your TaskFlow password",
                 bg=COLOR_WHITE, fg=COLOR_MUTED, font=f["small"]).pack(
            anchor="w", padx=20, pady=(0, 8))
        entries = {}
        eye_labels = {}
        eye_images = {}
        visibility = {}

        # Match the 👁 / 🙈 icons used by auth_pages.py.
        from emoji_icons import get_emoji
        eye_open = get_emoji("👁", 18)
        eye_closed = get_emoji("🙈", 18)
        use_images = eye_open is not None and eye_closed is not None

        for key, label in [("current", "Current Password"),
                           ("new", "New Password"),
                           ("confirm", "Confirm New Password")]:
            tk.Label(dialog, text=label, bg=COLOR_WHITE, fg=COLOR_TEXT,
                     font=f["small_bold"]).pack(anchor="w", padx=20,
                                                pady=(8, 3))

            field_row = tk.Frame(dialog, bg=COLOR_WHITE)
            field_row.pack(fill="x", padx=20)

            entry = self._entry(field_row, show="•")
            entry.pack(side="left", fill="x", expand=True, ipady=5)
            entries[key] = entry
            visibility[key] = False
            eye_images[key] = (eye_open, eye_closed)

            if use_images:
                eye_label = tk.Label(field_row, image=eye_closed,
                                     bg=COLOR_FIELD_BG, cursor="hand2",
                                     padx=8, bd=0)
                eye_label.image = eye_closed
            else:
                eye_label = tk.Label(field_row, text="🙈",
                                     bg=COLOR_FIELD_BG, fg=COLOR_MUTED,
                                     font=("Segoe UI Emoji", 12),
                                     cursor="hand2", padx=8, bd=0)
            eye_label.pack(side="right", padx=(0, 4))
            eye_labels[key] = eye_label

            def toggle_password(field_key=key):
                visibility[field_key] = not visibility[field_key]
                visible = visibility[field_key]
                entries[field_key].config(show="" if visible else "•")
                open_icon, closed_icon = eye_images[field_key]
                if use_images:
                    selected = open_icon if visible else closed_icon
                    eye_labels[field_key].config(image=selected, text="")
                    eye_labels[field_key].image = selected
                else:
                    eye_labels[field_key].config(
                        text="👁" if visible else "🙈"
                    )

            eye_label.bind("<Button-1>",
                           lambda _event, fn=toggle_password: fn())

        entries["current"].focus_set()

        def update():
            current = entries["current"].get()
            new = entries["new"].get()
            confirm = entries["confirm"].get()
            if not current or not new:
                messagebox.showerror("Missing information",
                                     "Complete all password fields.",
                                     parent=dialog)
            elif password_problem(new):
                messagebox.showerror("Weak password", password_problem(new),
                                     parent=dialog)
            elif new != confirm:
                messagebox.showerror("Passwords do not match",
                                     "Please confirm the new password.",
                                     parent=dialog)
            elif not self.db.change_password(self.get_user()["id"],
                                             current, new):
                messagebox.showerror("Wrong password",
                                     "Your current password is not correct.",
                                     parent=dialog)
            else:
                overlay.destroy()
                self.data = self.db.get_profile(self.get_user()["id"])
                self.draw_account()
                messagebox.showinfo("Password updated",
                                    "Your password has been changed.",
                                    parent=self)

        buttons = tk.Frame(dialog, bg=COLOR_WHITE)
        buttons.pack(fill="x", padx=20, pady=18)
        create_pill_button(buttons, "Update Password", 130, 32, f,
                           command=update).pack(side="right")
        create_pill_button(buttons, "Cancel", 80, 32, f, bg=COLOR_FIELD_BG,
                           fg=COLOR_MUTED,
                           command=overlay.destroy).pack(side="right",
                                                         padx=(0, 8))
        overlay.lift()

    def delete_account(self):
        """Asks for the password, then permanently erases this account (and
        all of its tasks and settings) from the database."""
        f = self.fonts
        overlay = tk.Frame(self, bg=COLOR_BG)
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        dialog = self._card(overlay)
        dialog.place(relx=0.5, rely=0.38, anchor="center", width=380)

        tk.Label(dialog, text="Delete Account", bg=COLOR_WHITE,
                 fg=SIGN_OUT_RED, font=f["dialog_title"]).pack(
            anchor="w", padx=20, pady=(18, 2))
        tk.Label(dialog,
                 text="This permanently deletes your account, all of your "
                      "tasks and your settings from TaskFlow. It cannot be "
                      "undone.",
                 bg=COLOR_WHITE, fg=COLOR_MUTED, font=f["small"],
                 justify="left", wraplength=340).pack(
            anchor="w", padx=20, pady=(0, 8))
        tk.Label(dialog, text="Enter your password to confirm",
                 bg=COLOR_WHITE, fg=COLOR_TEXT, font=f["small_bold"]).pack(
            anchor="w", padx=20, pady=(8, 3))
        entry = self._entry(dialog, show="•")
        entry.pack(fill="x", padx=20, ipady=5)
        entry.focus_set()

        def confirm_delete():
            user = self.get_user()
            password = entry.get()
            if not password:
                messagebox.showerror("Password needed",
                                     "Enter your password to continue.",
                                     parent=dialog)
            elif self.db.check_login(user["email"], password) is None:
                messagebox.showerror("Wrong password",
                                     "Your password is not correct.",
                                     parent=dialog)
            elif not messagebox.askyesno(
                    "Delete account",
                    "Are you sure? Your account and all of your tasks will "
                    "be erased for good.", icon="warning", parent=dialog):
                return
            elif self.db.delete_account(user["id"], password):
                try:
                    os.remove(self._photo_path(user["id"]))
                except OSError:
                    pass
                overlay.destroy()
                self.editing = False
                messagebox.showinfo("Account deleted",
                                    "Your account and all of its data have "
                                    "been permanently deleted.", parent=self)
                if self.on_deleted:
                    self.on_deleted()

        buttons = tk.Frame(dialog, bg=COLOR_WHITE)
        buttons.pack(fill="x", padx=20, pady=18)
        create_pill_button(buttons, "Delete Account", 124, 32, f,
                           bg=SIGN_OUT_RED,
                           command=confirm_delete).pack(side="right")
        create_pill_button(buttons, "Cancel", 80, 32, f, bg=COLOR_FIELD_BG,
                           fg=COLOR_MUTED,
                           command=overlay.destroy).pack(side="right",
                                                         padx=(0, 8))
        overlay.lift()