import tkinter as tk
from tkinter import ttk

from emoji_icons import emoji_label

PRIMARY = "#5B46F6"
PRIMARY_DARK = "#4835E0"
BG_LIGHT = "#F8FAFC"
CARD_BG = "#FFFFFF"
CARD_BORDER = "#E2E8F0"
TEXT_DARK = "#0F172A"
TEXT_MUTED = "#64748B"
BADGE_BG = "#E2E8F0"
FOOTER_BG = "#0F172A"
FOOTER_TEXT = "#94A3B8"
CTA_BG = "#5B46F6"


class ScrollableFrame(tk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, bg=BG_LIGHT, *args, **kwargs)

        self.canvas = tk.Canvas(self, bg=BG_LIGHT, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.content = tk.Frame(self.canvas, bg=BG_LIGHT)

        self.content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.window_id = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.window_id, width=e.width))

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")


class LandingPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_LIGHT)
        self.controller = controller

        self._configure_styles()

        scroll = ScrollableFrame(self)
        scroll.pack(fill="both", expand=True)
        page = scroll.content

        self._build_navbar(page)
        self._build_hero(page)
        self._build_stats(page)
        self._build_features(page)
        self._build_cta(page)
        self._build_footer(page)

    def _configure_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(
            "Primary.TButton",
            background=PRIMARY,
            foreground="white",
            font=("Segoe UI", 10, "bold"),
            padding=(18, 10),
            borderwidth=0
        )
        style.map("Primary.TButton", background=[("active", PRIMARY_DARK)])

        style.configure(
            "Secondary.TButton",
            background=BADGE_BG,
            foreground=TEXT_DARK,
            font=("Segoe UI", 10, "bold"),
            padding=(18, 10),
            borderwidth=0
        )
        style.map("Secondary.TButton", background=[("active", "#CBD5E1")])

        style.configure(
            "CTA.TButton",
            background=BADGE_BG,
            foreground=PRIMARY,
            font=("Segoe UI", 10, "bold"),
            padding=(20, 10),
            borderwidth=0
        )
        style.map("CTA.TButton", background=[("active", "#FFFFFF")])

    def _build_navbar(self, parent):
        nav = tk.Frame(parent, bg="white", height=64)
        nav.pack(fill="x")
        nav.pack_propagate(False)

        inner = tk.Frame(nav, bg="white")
        inner.pack(fill="both", expand=True, padx=40)

        # Logo: colour emoji image + text
        logo = tk.Frame(inner, bg="white")
        logo.pack(side="left", pady=16)
        emoji_label(logo, "🗂️", "white", size=20).pack(side="left", padx=(0, 8))
        tk.Label(
            logo,
            text="TASKFLOW",
            bg="white",
            fg=TEXT_DARK,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left")

        get_started = ttk.Button(
            inner,
            text="GET STARTED",
            style="Primary.TButton",
            command=lambda: self.controller.show_frame("SignUpPage")
        )
        get_started.pack(side="right", pady=10)

        sign_in = ttk.Button(
            inner,
            text="SIGN IN",
            style="Secondary.TButton",
            command=lambda: self.controller.show_frame("SignInPage")
        )
        sign_in.pack(side="right", padx=(0, 10), pady=10)

    def _build_hero(self, parent):
        hero = tk.Frame(parent, bg=BG_LIGHT)
        hero.pack(fill="x", pady=(40, 30))

        badge_frame = tk.Frame(hero, bg=BADGE_BG, padx=16, pady=6)
        badge_frame.pack(pady=(0, 20))
        tk.Label(
            badge_frame,
            text="Student Task Management",
            bg=BADGE_BG,
            fg=PRIMARY,
            font=("Segoe UI", 9, "bold")
        ).pack()

        tk.Label(
            hero,
            text="Stay on top of every",
            bg=BG_LIGHT,
            fg=TEXT_DARK,
            font=("Segoe UI", 28, "bold")
        ).pack()

        tk.Label(
            hero,
            text="academic deadline",
            bg=BG_LIGHT,
            fg=PRIMARY,
            font=("Segoe UI", 28, "bold")
        ).pack()

        tk.Label(
            hero,
            text="TaskFlow helps students organise assignments, set priorities, and\ntrack progress — all in one clean, focused workspace.",
            bg=BG_LIGHT,
            fg=TEXT_MUTED,
            font=("Segoe UI", 10),
            justify="center"
        ).pack(pady=(16, 24))

        btn_row = tk.Frame(hero, bg=BG_LIGHT)
        btn_row.pack()

        ttk.Button(
            btn_row,
            text="Start for free",
            style="Primary.TButton",
            command=lambda: self.controller.show_frame("SignUpPage")
        ).pack(side="left", padx=6)

        ttk.Button(
            btn_row,
            text="Sign in to your account",
            style="Secondary.TButton",
            command=lambda: self.controller.show_frame("SignInPage")
        ).pack(side="left", padx=6)

    def _build_stats(self, parent):
        # "How it works" - three numbered steps
        tk.Label(
            parent,
            text="Get started in three simple steps",
            bg=BG_LIGHT,
            fg=TEXT_DARK,
            font=("Segoe UI", 13, "bold")
        ).pack(pady=(10, 16))

        steps = [
            ("Add your tasks", "Enter each assignment with a deadline and a priority level."),
            ("Stay on track", "See what is due today and get reminders in the notification bell."),
            ("Tick it off", "Mark tasks complete and watch your progress ring fill up.")
        ]

        row = tk.Frame(parent, bg=BG_LIGHT)
        row.pack(pady=(0, 40))

        for index, (title, caption) in enumerate(steps, start=1):
            if index > 1:
                tk.Label(
                    row,
                    text="\u2192",
                    bg=BG_LIGHT,
                    fg="#CBD5E1",
                    font=("Segoe UI", 18, "bold")
                ).pack(side="left", padx=6)

            card = tk.Frame(
                row,
                bg=CARD_BG,
                highlightbackground=CARD_BORDER,
                highlightthickness=1,
                width=240,
                height=130
            )
            card.pack(side="left")
            card.pack_propagate(False)

            # purple numbered circle
            badge = tk.Canvas(card, width=34, height=34, bg=CARD_BG, highlightthickness=0)
            badge.create_oval(1, 1, 33, 33, fill=PRIMARY, outline=PRIMARY)
            badge.create_text(17, 17, text=str(index), fill="white", font=("Segoe UI", 12, "bold"))
            badge.pack(anchor="w", padx=20, pady=(16, 8))

            tk.Label(
                card,
                text=title,
                bg=CARD_BG,
                fg=TEXT_DARK,
                font=("Segoe UI", 11, "bold")
            ).pack(anchor="w", padx=20)

            tk.Label(
                card,
                text=caption,
                bg=CARD_BG,
                fg=TEXT_MUTED,
                font=("Segoe UI", 9),
                wraplength=200,
                justify="left"
            ).pack(anchor="w", padx=20, pady=(2, 0))

    def _build_features(self, parent):
        tk.Label(
            parent,
            text="Everything you need to stay organised",
            bg=BG_LIGHT,
            fg=TEXT_DARK,
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(10, 30))

        features = [
            ("📋", "Task Management", "Add, edit, and delete tasks with deadlines, priority levels, and rich descriptions."),
            ("🎯", "Priority System", "Classify tasks as High, Medium, or Low priority so you always know what to tackle first."),
            ("✅", "Progress Tracking", "Mark tasks complete and watch your completion rate climb with the live progress bar."),
            ("🔍", "Search & Filter", "Instantly find any task by name or filter by status and priority level."),
            ("⏰", "Deadline Alerts", "At-a-glance overdue and due-soon indicators keep you from missing deadlines."),
            ("🔒", "Secure & Private", "Your tasks are yours alone. Full account management with secure authentication.")
        ]

        grid = tk.Frame(parent, bg=BG_LIGHT)
        grid.pack(pady=(0, 50))

        for idx, (icon, title, desc) in enumerate(features):
            row = idx // 2
            col = idx % 2

            card = tk.Frame(
                grid,
                bg=CARD_BG,
                highlightbackground=CARD_BORDER,
                highlightthickness=1,
                width=320,
                height=130
            )
            card.grid(row=row, column=col, padx=12, pady=12)
            card.pack_propagate(False)

            header = tk.Frame(card, bg=CARD_BG)
            header.pack(anchor="w", padx=20, pady=(16, 6))

            # Coloured icon (image) instead of black & white text
            emoji_label(header, icon, CARD_BG, size=18).pack(side="left", padx=(0, 8))
            tk.Label(header, text=title, bg=CARD_BG, fg=TEXT_DARK, font=("Segoe UI", 10, "bold")).pack(side="left")

            tk.Label(
                card,
                text=desc,
                bg=CARD_BG,
                fg=TEXT_MUTED,
                font=("Segoe UI", 8),
                wraplength=275,
                justify="left"
            ).pack(anchor="w", padx=20)

    def _build_cta(self, parent):
        cta = tk.Frame(parent, bg=CTA_BG, height=220)
        cta.pack(fill="x")
        cta.pack_propagate(False)

        inner = tk.Frame(cta, bg=CTA_BG)
        inner.pack(expand=True)

        tk.Label(
            inner,
            text="Ready to get organised?",
            bg=CTA_BG,
            fg="white",
            font=("Segoe UI", 22, "bold")
        ).pack(pady=(0, 20))

        ttk.Button(
            inner,
            text="Create free account",
            style="CTA.TButton",
            command=lambda: self.controller.show_frame("SignUpPage")
        ).pack()

    def _build_footer(self, parent):
        footer = tk.Frame(parent, bg=FOOTER_BG)
        footer.pack(fill="x")

        inner = tk.Frame(footer, bg=FOOTER_BG)
        inner.pack(pady=24)

        tk.Label(
            inner,
            text="© 2026 TaskFlow — Samtse College of Education\nPython-Based Student Task Management System",
            bg=FOOTER_BG,
            fg=FOOTER_TEXT,
            font=("Segoe UI", 8),
            justify="center"
        ).pack()