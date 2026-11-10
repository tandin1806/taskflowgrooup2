SENDER_EMAIL = "08230207.sce@rub.edu.bt"
SENDER_APP_PASSWORD = "iimh sipr habj cksi"

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import re
import socket
import smtplib
import ssl
import random
from email.message import EmailMessage
from datetime import datetime

from emoji_icons import emoji_label, get_emoji

# ---------------------------------------------------------------------------
# Palette (matches the TaskFlow prototype)
# ---------------------------------------------------------------------------
PRIMARY = "#5B46F6"
PRIMARY_DARK = "#4835E0"
BG_LIGHT = "#F8FAFC"
CARD_BG = "#FFFFFF"
CARD_BORDER = "#E2E8F0"
TEXT_DARK = "#0F172A"
TEXT_MUTED = "#64748B"
SIDEBAR_BG = "#0B1220"
SIDEBAR_MUTED = "#94A3B8"
SIDEBAR_CARD = "#131C2E"
ERROR_COLOR = "#DC2626"
PLACEHOLDER_COLOR = "#94A3B8"

# Softer tones used ONLY by the sign-in / sign-up sidebar, so the panel stays
# in the background and the form gets the focus.
AUTH_SIDEBAR_BG = "#1E293B"
AUTH_SIDEBAR_CARD = "#27354B"
AUTH_SIDEBAR_TITLE = "#E2E8F0"
AUTH_SIDEBAR_MUTED = "#94A3B8"
AUTH_SIDEBAR_WIDTH = 290

# Size of the white form card. It is FIXED, so the boxes look exactly the same
# before typing, after typing and when an error message appears.
FORM_WIDTH = 340
ENTRY_FONT = ("Segoe UI", 10)

EMAIL_REGEX = r"^[\w\.-]+@[\w\.-]+\.\w+$"

# --- Strict e-mail check used when an e-mail is CREATED (sign up / profile edit)
_PLACEHOLDER_DOMAINS = {
    "example.com", "example.org", "example.net", "test.com", "test.org",
    "test.net", "domain.com", "email.com", "yourdomain.com", "mydomain.com",
    "sample.com", "demo.com", "fake.com", "dummy.com", "abc.com", "xyz.com",
    "asdf.com", "qwerty.com", "localhost", "invalid", "none.com", "null.com",
}
_DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com",
    "temp-mail.org", "yopmail.com", "trashmail.com", "throwawaymail.com",
    "getnada.com", "sharklasers.com", "maildrop.cc", "dispostable.com",
    "fakeinbox.com", "mintemail.com", "mailnesia.com", "tempail.com",
}
_DUMMY_LOCALS = {
    "test", "tester", "testing", "abc", "abcd", "abcde", "asdf", "asdfg",
    "qwerty", "xyz", "user", "username", "fake", "dummy", "sample", "demo",
    "email", "mail", "name", "example", "noreply", "no-reply", "none", "null",
    "admin", "root", "foo", "bar", "temp", "random", "12345", "123456",
}
# RUB student e-mail: 8-digit student number . college code @rub.edu.bt
RUB_EMAIL_RE = re.compile(r"^\d{8}\.[a-z]{2,6}@rub\.edu\.bt$", re.IGNORECASE)
_LOCAL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+$")
_LABEL_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?$")


def validate_email(email):
    """None if the e-mail looks genuine, otherwise a sentence saying why not.
    The text is checked exactly as typed (upper / lower case is NOT changed)."""
    if len(email) > 254 or email.count("@") != 1:
        return "Please enter a valid email address."
    local, domain = email.split("@")
    if not RUB_EMAIL_RE.match(email):
        return "Please use your RUB student email (like 08230207.sce@rub.edu.bt)."
    if not (1 <= len(local) <= 64) or not _LOCAL_RE.match(local):
        return "Please enter a valid email address."
    if local.startswith(".") or local.endswith(".") or ".." in local:
        return "Please enter a valid email address."
    labels = domain.split(".")
    if len(labels) < 2 or not all(_LABEL_RE.match(l) and len(l) <= 63 for l in labels):
        return "Please enter a valid email address."
    tld = labels[-1]
    if not (2 <= len(tld) <= 24) or not tld.isalpha():
        return "Please enter a valid email address."
    domain_l, local_l = domain.lower(), local.lower()
    if domain_l in _PLACEHOLDER_DOMAINS or domain_l in _DISPOSABLE_DOMAINS:
        return "Please use your real email address (test or temporary emails are not accepted)."
    if local_l in _DUMMY_LOCALS or len(set(local_l)) == 1:
        return "Please use your real email address (dummy emails are not accepted)."
    # The e-mail's domain must really exist on the internet
    try:
        socket.gethostbyname(domain)
    except OSError:
        return "This email domain does not exist. Please use your real email address."
    return None

def mailbox_missing(email):
    """True ONLY if the e-mail's own mail server says this address does not
    exist. If the check cannot be done (no internet, port 25 blocked, no
    dnspython, unclear answer) it returns False, so real users are not blocked."""
    try:
        import dns.resolver                      # pip install dnspython
        domain = email.split("@")[1]
        records = sorted(dns.resolver.resolve(domain, "MX", lifetime=5),
                         key=lambda r: r.preference)
        host = str(records[0].exchange).rstrip(".")
        with smtplib.SMTP(host, 25, timeout=8) as server:
            server.ehlo()
            if server.mail(SENDER_EMAIL)[0] != 250:
                return False
            code, reply = server.rcpt(email)
        return code in (550, 551, 553) and b"5.7" not in reply
    except Exception:
        return False


# --- E-mail that SENDS the 6-digit codes (see the setup steps) ---
SENDER_EMAIL = "08230207.sce@rub.edu.bt"
SENDER_APP_PASSWORD = "iimh sipr habj cksi"


def send_code_email(to_email, purpose):
    """E-mails a 6-digit code to to_email and returns the code."""
    code = str(random.SystemRandom().randint(100000, 999999))
    msg = EmailMessage()
    msg["Subject"] = "Your TaskFlow verification code"
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg.set_content(f"Your TaskFlow code for {purpose} is: {code}\n\n"
                    "If you did not request this, ignore this email.")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15,
                          context=ssl.create_default_context()) as server:
        server.login(SENDER_EMAIL, SENDER_APP_PASSWORD.replace(" ", ""))
        server.send_message(msg)
    return code


def ask_for_code(parent, to_email, purpose):
    """Sends a code, asks the user to type it. True only if it is correct."""
    try:
        code = send_code_email(to_email, purpose)
    except Exception as error:
        messagebox.showerror("Email not sent",
                             "Could not send the verification email. Check the "
                             "internet connection and the email address.\n\n"
                             f"Reason: {error}", parent=parent)
        return False
    for _ in range(3):
        entered = simpledialog.askstring(
            "Verification code",
            f"We sent a 6-digit code to {to_email}.\nEnter it here:", parent=parent)
        if entered is None:
            return False
        if entered.strip() == code:
            return True
        messagebox.showerror("Wrong code", "That code is not correct.", parent=parent)
    return False


PASSWORD_HINT = "8+ characters: A-Z, a-z, 0-9 and a special character (! @ # $ %)"


def password_problem(password):
    """None if the password is strong, otherwise a sentence that says exactly
    what is still missing (used by Sign Up and by Change Password)."""
    missing = []
    if len(password) < 8:
        missing.append("at least 8 characters")
    if not re.search(r"[A-Z]", password):
        missing.append("an uppercase letter")
    if not re.search(r"[a-z]", password):
        missing.append("a lowercase letter")
    if not re.search(r"\d", password):
        missing.append("a number")
    if not re.search(r"[^A-Za-z0-9\s]", password):
        missing.append("a special character (e.g. ! @ # $ % & *)")
    if not missing:
        return None
    listing = (missing[0] if len(missing) == 1 else
               ", ".join(missing[:-1]) + " and " + missing[-1])
    return f"Password is too weak. Please include {listing}."


# ---------------------------------------------------------------------------
# Small reusable widgets
# ---------------------------------------------------------------------------
class PlaceholderEntry(ttk.Entry):
    """An Entry that shows greyed-out placeholder text until focused / typed in."""

    def __init__(self, parent, placeholder, show=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.placeholder = placeholder
        self.real_show = show
        self._showing_placeholder = False

        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)
        self._set_placeholder()

    def _set_placeholder(self):
        self.delete(0, tk.END)
        self.insert(0, self.placeholder)
        self.config(foreground=PLACEHOLDER_COLOR)
        if self.real_show is not None:
            self.config(show="")
        self._showing_placeholder = True

    def _on_focus_in(self, _event=None):
        if self._showing_placeholder:
            self.delete(0, tk.END)
            self.config(foreground=TEXT_DARK)
            if self.real_show is not None:
                self.config(show=self.real_show)
            self._showing_placeholder = False

    def _on_focus_out(self, _event=None):
        if not self.get():
            self._set_placeholder()

    def get_value(self):
        """Return '' if the field is still showing its placeholder."""
        return "" if self._showing_placeholder else self.get().strip()

    def set_show(self, show_char):
        """Used by the eye toggle to reveal/hide real password text."""
        self.real_show = show_char
        if not self._showing_placeholder:
            self.config(show=show_char)

    def mark_error(self, is_error):
        self.config(foreground=ERROR_COLOR if (is_error and not self._showing_placeholder) else
                     (PLACEHOLDER_COLOR if self._showing_placeholder else TEXT_DARK))


def _attach_focus_border(row, entry):
    """The wrapper frame is the ONLY visible box; highlight it while the entry has focus."""
    entry.bind("<FocusIn>", lambda e: row.config(highlightbackground=PRIMARY), add="+")
    entry.bind("<FocusOut>", lambda e: row.config(highlightbackground=CARD_BORDER), add="+")


def make_text_field(parent, placeholder):
    """Builds a single-box text row (same look as the password row). Returns (frame, entry)."""
    row = tk.Frame(parent, bg=CARD_BG, highlightbackground=CARD_BORDER, highlightthickness=1)
    row.pack(fill="x", padx=28)

    entry = PlaceholderEntry(row, placeholder, style="Plain.TEntry", font=ENTRY_FONT)
    entry.pack(fill="x", expand=True, ipady=4, padx=7)
    _attach_focus_border(row, entry)
    return row, entry


def make_password_field(parent, placeholder):
    """Builds a password row: entry + eye-toggle icon. Returns (frame, entry)."""
    row = tk.Frame(parent, bg=CARD_BG, highlightbackground=CARD_BORDER, highlightthickness=1)
    row.pack(fill="x", padx=28)

    entry = PlaceholderEntry(row, placeholder, show="•", style="Plain.TEntry", font=ENTRY_FONT)
    entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(7, 0))
    _attach_focus_border(row, entry)

    # Coloured eye icons (images). Falls back to text if images are unavailable.
    eye_open = get_emoji("👁", 18)
    eye_closed = get_emoji("🙈", 18)
    use_images = eye_open is not None and eye_closed is not None

    if use_images:
        eye_label = tk.Label(row, image=eye_closed, bg=CARD_BG, cursor="hand2", padx=8, bd=0)
        eye_label.image = eye_closed
    else:
        eye_label = tk.Label(row, text="🙈", bg=CARD_BG, fg=TEXT_MUTED,
                              font=("Segoe UI Emoji", 12), cursor="hand2", padx=8)
    eye_label.pack(side="right", padx=(0, 6))

    state = {"visible": False}

    def toggle(_event=None):
        state["visible"] = not state["visible"]
        if state["visible"]:
            entry.set_show("")
            if use_images:
                eye_label.config(image=eye_open)
                eye_label.image = eye_open
            else:
                eye_label.config(text="👁")
        else:
            entry.set_show("•")
            if use_images:
                eye_label.config(image=eye_closed)
                eye_label.image = eye_closed
            else:
                eye_label.config(text="🙈")

    eye_label.bind("<Button-1>", toggle)
    return row, entry


def make_card(parent):
    """The form card. The fixed-width spacer keeps its size the same whether
    the boxes are empty, filled in, or showing an error message."""
    card = tk.Frame(parent, bg=CARD_BG, highlightbackground=CARD_BORDER,
                    highlightthickness=1)
    card.pack()
    tk.Frame(card, bg=CARD_BG, width=FORM_WIDTH, height=14).pack()
    return card


class FitArea(tk.Frame):
    """Holds the form near the top, centred sideways. If the window is ever too
    short to show the whole form, a scrollbar appears so nothing is cut off."""

    def __init__(self, parent, top_fraction):
        super().__init__(parent, bg=BG_LIGHT)
        self.top_fraction = top_fraction
        self._scrolling = False
        self.canvas = tk.Canvas(self, bg=BG_LIGHT, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=BG_LIGHT)     # put the form in here
        self._window = self.canvas.create_window(0, 0, window=self.inner, anchor="n")
        self.canvas.bind("<Configure>", self._layout)
        self.inner.bind("<Configure>", self._layout)

    def _layout(self, _event=None):
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if height < 50:                       # not drawn yet
            return
        need = self.inner.winfo_reqheight()
        # normally a little below the top; pulled up when space is short
        top = max(0, min(int(height * self.top_fraction), height - need))
        self.canvas.coords(self._window, width // 2, top)
        self.canvas.configure(scrollregion=(0, 0, width, max(height, top + need)))
        too_tall = need > height
        if too_tall != self._scrolling:
            self._scrolling = too_tall
            if too_tall:
                self.scrollbar.pack(side="right", fill="y")
            else:
                self.scrollbar.pack_forget()
                self.canvas.yview_moveto(0)


def error_label(parent):
    lbl = tk.Label(parent, text="", bg=CARD_BG, fg=ERROR_COLOR, font=("Segoe UI", 9), wraplength=FORM_WIDTH - 56, justify="left")
    lbl.pack(anchor="w", padx=28, pady=(2, 0))
    return lbl


def show_error(label, text):
    label.config(text=text)


def clear_error(label):
    label.config(text="")


# ---------------------------------------------------------------------------
# Sidebar builder (shared visual language between the two pages)
# ---------------------------------------------------------------------------
def build_sidebar(parent, headline, subtext, extra_builder=None):
    sidebar = tk.Frame(parent, bg=AUTH_SIDEBAR_BG, width=AUTH_SIDEBAR_WIDTH)
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)
    wrap = AUTH_SIDEBAR_WIDTH - 72

    # Logo row
    logo_row = tk.Frame(sidebar, bg=AUTH_SIDEBAR_BG)
    logo_row.pack(anchor="w", padx=24, pady=(24, 0))
    tk.Label(logo_row, text="▢", bg=PRIMARY, fg="white", font=("Segoe UI", 11, "bold"),
              width=2, height=1).pack(side="left")
    tk.Label(logo_row, text=" TASKFLOW", bg=AUTH_SIDEBAR_BG, fg=AUTH_SIDEBAR_TITLE,
              font=("Segoe UI", 11, "bold")).pack(side="left")

    # Headline block
    body = tk.Frame(sidebar, bg=AUTH_SIDEBAR_BG)
    body.pack(anchor="w", padx=24, pady=(38, 0), fill="x")
    tk.Label(body, text=headline, bg=AUTH_SIDEBAR_BG, fg=AUTH_SIDEBAR_TITLE, font=("Segoe UI", 15, "bold"),
              justify="left", wraplength=wrap).pack(anchor="w")
    tk.Label(body, text=subtext, bg=AUTH_SIDEBAR_BG, fg=AUTH_SIDEBAR_MUTED, font=("Segoe UI", 10),
              justify="left", wraplength=wrap).pack(anchor="w", pady=(10, 0))

    if extra_builder:
        extra_builder(sidebar)

    tk.Label(sidebar, text=f"© {datetime.now().year} TaskFlow — Samtse College of Education",
              bg=AUTH_SIDEBAR_BG, fg=AUTH_SIDEBAR_MUTED, font=("Segoe UI", 8)).pack(side="bottom", pady=12)

    return sidebar


# ---------------------------------------------------------------------------
# Sign Up Page
# ---------------------------------------------------------------------------
class SignUpPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_LIGHT)
        self.controller = controller

        def sidebar_extras(sidebar):
            # real numbers from the database (see refresh_stats)
            card = tk.Frame(sidebar, bg=AUTH_SIDEBAR_CARD)
            card.pack(fill="x", padx=24, pady=(18, 0))
            self.members_title = tk.Label(
                card, text="", bg=AUTH_SIDEBAR_CARD, fg=AUTH_SIDEBAR_TITLE,
                font=("Segoe UI", 11, "bold"), justify="left",
                wraplength=AUTH_SIDEBAR_WIDTH - 112)
            self.members_title.pack(anchor="w", padx=14, pady=(12, 3))
            self.members_note = tk.Label(
                card, text="", bg=AUTH_SIDEBAR_CARD, fg=AUTH_SIDEBAR_MUTED,
                font=("Segoe UI", 10), justify="left",
                wraplength=AUTH_SIDEBAR_WIDTH - 112)
            self.members_note.pack(anchor="w", padx=14, pady=(0, 12))

        build_sidebar(
            self,
            "Start organising your\nacademic life today.",
            "Create a free account and take control of your assignments, deadlines, and priorities.",
            extra_builder=sidebar_extras,
        )

        content = tk.Frame(self, bg=BG_LIGHT)
        content.pack(side="left", fill="both", expand=True)

        area = FitArea(content, 0.04)
        area.pack(fill="both", expand=True)
        form = area.inner

        tk.Label(form, text="Create your account", bg=BG_LIGHT, fg=TEXT_DARK,
                  font=("Segoe UI", 24, "bold")).pack(anchor="w", pady=(0, 2))
        tk.Label(form, text="Fill in your details to get started.", bg=BG_LIGHT, fg=TEXT_MUTED,
                  font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 14))

        card = make_card(form)

        # Full Name
        tk.Label(card, text="Full Name", bg=CARD_BG, fg=TEXT_DARK, font=("Segoe UI", 10, "bold")).pack(
            anchor="w", padx=28, pady=(0, 2))
        _, self.name_entry = make_text_field(card, "Your full name")
        self.name_error = error_label(card)

        # Email
        tk.Label(card, text="Email Address", bg=CARD_BG, fg=TEXT_DARK, font=("Segoe UI", 10, "bold")).pack(
            anchor="w", padx=28, pady=(8, 2))
        _, self.email_entry = make_text_field(card, "08230207.sce@rub.edu.bt")
        self.email_error = error_label(card)

        # Password
        tk.Label(card, text="Password", bg=CARD_BG, fg=TEXT_DARK, font=("Segoe UI", 10, "bold")).pack(
            anchor="w", padx=28, pady=(8, 2))
        _, self.pass_entry = make_password_field(card, "Min 8 characters")
        tk.Label(card, text=PASSWORD_HINT, bg=CARD_BG, fg=TEXT_MUTED, font=("Segoe UI", 8),
                  justify="left", wraplength=FORM_WIDTH - 56).pack(anchor="w", padx=40, pady=(3, 0))
        self.pass_error = error_label(card)

        # Confirm Password
        tk.Label(card, text="Confirm Password", bg=CARD_BG, fg=TEXT_DARK, font=("Segoe UI", 10, "bold")).pack(
            anchor="w", padx=28, pady=(8, 2))
        _, self.confirm_entry = make_password_field(card, "Re-enter your password")
        self.confirm_error = error_label(card)

        # Terms checkbox
        self.agree_var = tk.BooleanVar(value=False)
        terms_row = tk.Frame(card, bg=CARD_BG)
        terms_row.pack(anchor="w", padx=28, pady=(8, 0))
        tk.Checkbutton(terms_row, variable=self.agree_var, bg=CARD_BG,
                        activebackground=CARD_BG).pack(side="left")
        tk.Label(terms_row, text="I agree to the Terms of Service and Privacy Policy",
                  bg=CARD_BG, fg=TEXT_MUTED, font=("Segoe UI", 9)).pack(side="left")
        self.terms_error = error_label(card)

        # Sign Up Button
        btn = ttk.Button(card, text="Create account", style="Primary.TButton", command=self._handle_signup)
        btn.pack(fill="x", padx=28, pady=(12, 8))

        link_frame = tk.Frame(card, bg=CARD_BG)
        link_frame.pack()
        tk.Label(link_frame, text="Already have an account? ", bg=CARD_BG, fg=TEXT_MUTED,
                  font=("Segoe UI", 9)).pack(side="left")
        link = tk.Label(link_frame, text="Sign in", bg=CARD_BG, fg=PRIMARY,
                          font=("Segoe UI", 9, "bold"), cursor="hand2")
        link.pack(side="left")
        link.bind("<Button-1>", lambda e: self.controller.show_frame("SignInPage"))

        back = tk.Label(card, text="← Back to home", bg=CARD_BG, fg=TEXT_MUTED,
                          font=("Segoe UI", 9), cursor="hand2")
        back.pack(pady=(4, 16))
        back.bind("<Button-1>", lambda e: self.controller.show_frame("LandingPage"))

        self.refresh_stats()

    def refresh_stats(self):
        """Fills the sidebar card with the real number of students and
        finished tasks (app.py calls this each time the page is shown)."""
        db = getattr(self.controller, "db", None)
        if db is None:
            return
        stats = db.get_public_stats()
        students, done = stats["students"], stats["tasks_done"]
        if students == 0:
            self.members_title.config(text="Be the first to join")
            self.members_note.config(
                text="Create your account and start tracking your tasks.")
        else:
            self.members_title.config(
                text=f"{students:,} student{'s' if students != 1 else ''} "
                     f"on TaskFlow")
            self.members_note.config(
                text=f"{done:,} task{'s' if done != 1 else ''} completed "
                     f"so far.")

    def _clear_errors(self):
        for lbl in (self.name_error, self.email_error, self.pass_error,
                    self.confirm_error, self.terms_error):
            clear_error(lbl)

    def _handle_signup(self):
        self._clear_errors()

        name = self.name_entry.get_value()
        email = self.email_entry.get_value()   # exact case is kept
        password = self.pass_entry.get_value()
        confirm = self.confirm_entry.get_value()

        has_error = False

        # Name
        if not name:
            show_error(self.name_error, "Full name is required.")
            has_error = True
        elif len(name) < 2:
            show_error(self.name_error, "Name must be at least 2 characters.")
            has_error = True

        # Email
        if not email:
            show_error(self.email_error, "Email address is required.")
            has_error = True
        elif validate_email(email):
            show_error(self.email_error, validate_email(email))
            has_error = True
        elif self.controller.db.email_exists(email):
            show_error(self.email_error, "An account with this email already exists. Please sign in instead.")
            has_error = True
        elif mailbox_missing(email):
            show_error(self.email_error, "This email address does not exist. Please use your real email address.")
            has_error = True

        # Password
        if not password:
            show_error(self.pass_error, "Password is required.")
            has_error = True
        elif password_problem(password):
            show_error(self.pass_error, password_problem(password))
            has_error = True

        # Confirm password
        if not confirm:
            show_error(self.confirm_error, "Please confirm your password.")
            has_error = True
        elif password and confirm != password:
            show_error(self.confirm_error, "Passwords do not match.")
            has_error = True

        # Terms
        if not self.agree_var.get():
            show_error(self.terms_error, "You must agree to the Terms of Service and Privacy Policy.")
            has_error = True

        if has_error:
            return

        # Register the new user
        try:
            self.controller.register_user(name, email, password)
        except ValueError as error:
            show_error(self.email_error, str(error))
            return
        messagebox.showinfo("Success", "Account created successfully!")
        self.controller.show_frame("SignInPage")


# ---------------------------------------------------------------------------
# Sign In Page
# ---------------------------------------------------------------------------
class SignInPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_LIGHT)
        self.controller = controller

        def sidebar_extras(sidebar):
            bullets = [
                ("🎯", "Priority-based task organisation"),
                ("⏰", "Due-today and due-soon reminders"),
                ("📊", "Progress dashboard at a glance"),
            ]
            block = tk.Frame(sidebar, bg=AUTH_SIDEBAR_BG)
            block.pack(anchor="w", padx=24, pady=(18, 0))
            for icon, text in bullets:
                row = tk.Frame(block, bg=AUTH_SIDEBAR_BG)
                row.pack(anchor="w", pady=4)
                # Coloured icon (image) instead of black & white text
                emoji_label(row, icon, AUTH_SIDEBAR_BG, size=17).pack(side="left")
                tk.Label(row, text=" " + text, bg=AUTH_SIDEBAR_BG, fg=AUTH_SIDEBAR_MUTED,
                          font=("Segoe UI", 9)).pack(side="left")

        build_sidebar(
            self,
            "Manage your academic\ntasks with ease.",
            "Track assignments, set priorities, meet deadlines — all in one focused workspace built for students.",
            extra_builder=sidebar_extras,
        )

        content = tk.Frame(self, bg=BG_LIGHT)
        content.pack(side="left", fill="both", expand=True)

        area = FitArea(content, 0.12)
        area.pack(fill="both", expand=True)
        form = area.inner

        tk.Label(form, text="Welcome back", bg=BG_LIGHT, fg=TEXT_DARK,
                  font=("Segoe UI", 24, "bold")).pack(anchor="w", pady=(0, 2))
        tk.Label(form, text="Sign in to your TaskFlow account", bg=BG_LIGHT, fg=TEXT_MUTED,
                  font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 14))

        card = make_card(form)

        # Email
        tk.Label(card, text="Email Address", bg=CARD_BG, fg=TEXT_DARK, font=("Segoe UI", 10, "bold")).pack(
            anchor="w", padx=28, pady=(0, 2))
        _, self.email_entry = make_text_field(card, "you@example.com")
        self.email_error = error_label(card)

        # Password
        pass_head = tk.Frame(card, bg=CARD_BG)
        pass_head.pack(fill="x", padx=28, pady=(8, 2))
        tk.Label(pass_head, text="Password", bg=CARD_BG, fg=TEXT_DARK,
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        forgot = tk.Label(pass_head, text="Forgot password?", bg=CARD_BG, fg=PRIMARY,
                          font=("Segoe UI", 9, "bold"), cursor="hand2")
        forgot.pack(side="right")
        forgot.bind("<Button-1>", lambda e: self._forgot_password())
        _, self.pass_entry = make_password_field(card, "Enter your password")
        self.pass_error = error_label(card)

        # Sign In Button
        btn = ttk.Button(card, text="Sign in", style="Primary.TButton", command=self._handle_signin)
        btn.pack(fill="x", padx=28, pady=(12, 8))

        link_frame = tk.Frame(card, bg=CARD_BG)
        link_frame.pack()
        tk.Label(link_frame, text="Don't have an account? ", bg=CARD_BG, fg=TEXT_MUTED,
                  font=("Segoe UI", 9)).pack(side="left")
        link = tk.Label(link_frame, text="Create one", bg=CARD_BG, fg=PRIMARY,
                          font=("Segoe UI", 9, "bold"), cursor="hand2")
        link.pack(side="left")
        link.bind("<Button-1>", lambda e: self.controller.show_frame("SignUpPage"))

        back = tk.Label(card, text="← Back to home", bg=CARD_BG, fg=TEXT_MUTED,
                          font=("Segoe UI", 9), cursor="hand2")
        back.pack(pady=(4, 16))
        back.bind("<Button-1>", lambda e: self.controller.show_frame("LandingPage"))

    def _clear_errors(self):
        clear_error(self.email_error)
        clear_error(self.pass_error)

    def _handle_signin(self):
        self._clear_errors()

        email = self.email_entry.get_value()   # exact case, must match sign-up
        password = self.pass_entry.get_value()

        has_error = False

        if not email:
            show_error(self.email_error, "Email address is required.")
            has_error = True
        elif not re.match(EMAIL_REGEX, email):
            show_error(self.email_error, "Please enter a valid email address.")
            has_error = True

        if not password:
            show_error(self.pass_error, "Password is required.")
            has_error = True

        if has_error:
            return

        if not self.controller.db.email_exists(email):
            show_error(self.email_error, "No account found with this email. Please sign up first.")
            return
        user = self.controller.db.check_login(email, password)
        if user is None:
            show_error(self.pass_error, "Incorrect password. Please try again.")
            return
        # Safety net: even if the database ignores letter case, the e-mail must
        # match the one used at sign-up exactly (A@x.com is not a@x.com).
        try:
            stored_email = user["email"]
        except (KeyError, IndexError, TypeError):
            stored_email = None
        if stored_email is not None and stored_email != email:
            show_error(self.email_error, "No account found with this email. Check upper/lower case letters.")
            return

        # First sign-in of an account: show its recovery key once (it is
        # what "Forgot password?" asks for).
        key = self.controller.db.ensure_recovery_key(user["user_id"])
        if key:
            messagebox.showinfo(
                "Your recovery key",
                "Write this key down and keep it safe. You will need it if "
                "you forget your password:\n\n" + key +
                "\n\nIt is shown only once.")

        self.controller.set_user(user["user_id"], user["full_name"], email)
        self.controller.show_frame("DashboardPage")

    def _forgot_password(self):
        """Pop-up: email + recovery key + new password."""
        root = self.winfo_toplevel()
        win = tk.Toplevel(root)
        win.title("Reset password")
        win.configure(bg=CARD_BG)
        win.resizable(False, False)
        win.transient(root)
        win.minsize(400, 0)
        tries = {"n": 0}

        tk.Label(win, text="Reset your password", bg=CARD_BG, fg=TEXT_DARK,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=28, pady=(22, 2))
        tk.Label(win, text="Enter your email and the recovery key you were "
                           "shown the first time you signed in.",
                 bg=CARD_BG, fg=TEXT_MUTED, font=("Segoe UI", 9), justify="left",
                 wraplength=340).pack(anchor="w", padx=28, pady=(0, 6))

        def field(label, maker, placeholder):
            tk.Label(win, text=label, bg=CARD_BG, fg=TEXT_DARK,
                     font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=28, pady=(8, 2))
            return maker(win, placeholder)[1]

        email_entry = field("Email Address", make_text_field, "you@example.com")
        key_entry = field("Recovery key", make_text_field, "XXXX-XXXX-XXXX-XXXX")
        new_entry = field("New password", make_password_field, "Enter a new password")
        confirm_entry = field("Confirm new password", make_password_field,
                              "Re-enter the new password")
        problem = error_label(win)

        def reset(_event=None):
            email = email_entry.get_value()
            key = key_entry.get_value()
            new = new_entry.get_value()
            if not (email and key and new):
                show_error(problem, "Please fill in all the fields.")
            elif password_problem(new):
                show_error(problem, password_problem(new))
            elif new != confirm_entry.get_value():
                show_error(problem, "Passwords do not match.")
            elif not self.controller.db.reset_password_with_key(email, key, new):
                tries["n"] += 1
                if tries["n"] >= 5:
                    win.destroy()
                    messagebox.showerror("Too many attempts",
                                         "Too many wrong tries. Please try again later.",
                                         parent=root)
                    return
                show_error(problem, "The email or recovery key is not correct.")
            else:
                win.destroy()
                messagebox.showinfo("Password changed",
                                    "Your password has been changed. Sign in with "
                                    "your new password.", parent=root)

        row = tk.Frame(win, bg=CARD_BG)
        row.pack(fill="x", padx=28, pady=(10, 20))
        ttk.Button(row, text="Reset password", style="Primary.TButton",
                   command=reset).pack(side="right")
        ttk.Button(row, text="Cancel", command=win.destroy).pack(
            side="right", padx=(0, 8))
        win.bind("<Return>", reset)

        win.update_idletasks()
        x = root.winfo_rootx() + (root.winfo_width() - win.winfo_width()) // 2
        y = root.winfo_rooty() + (root.winfo_height() - win.winfo_height()) // 4
        win.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        win.grab_set()
        email_entry.focus_set()


# ---------------------------------------------------------------------------
# ttk styles used by both pages (call once from your App/controller setup)
# ---------------------------------------------------------------------------
def configure_auth_styles(root):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # The wrapper frame draws the only border, so the inner entry's own (clam) border,
    # including its focus colour, is painted in the card colour to make it invisible.
    style.configure("Plain.TEntry", fieldbackground=CARD_BG, borderwidth=0, relief="flat",
                     bordercolor=CARD_BG, lightcolor=CARD_BG, darkcolor=CARD_BG)
    style.map("Plain.TEntry",
              bordercolor=[("focus", CARD_BG), ("!focus", CARD_BG)],
              lightcolor=[("focus", CARD_BG), ("!focus", CARD_BG)],
              darkcolor=[("focus", CARD_BG), ("!focus", CARD_BG)],
              fieldbackground=[("focus", CARD_BG), ("!focus", CARD_BG)])

    style.configure("Primary.TButton", background=PRIMARY, foreground="white",
                     font=("Segoe UI", 10, "bold"), borderwidth=0, padding=8)
    style.map("Primary.TButton",
              background=[("active", PRIMARY_DARK), ("pressed", PRIMARY_DARK)])