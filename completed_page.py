import tkinter as tk

from ui_common import (
    COLOR_BG, COLOR_WHITE, COLOR_TEXT, COLOR_MUTED, COLOR_LINE, COLOR_GREEN,
    COLOR_FIELD_LINE, COLOR_FIELD_BG,
    create_outlined_badge, draw_rounded_rect, ScrollFrame, shorten,
    format_date,
)
from task_dialogs import (
    edit_button, delete_button, open_edit_dialog, open_delete_dialog,
)

CONTENT_WIDTH = 680          # the prototype keeps this page narrow + centered
BANNER_GREEN = "#12b76a"


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


class CompletedPage(tk.Frame):
    def __init__(self, parent, fonts, store):
        super().__init__(parent, bg=COLOR_BG)
        self.fonts = fonts
        self.store = store

        # centered column that never gets wider than CONTENT_WIDTH
        wrapper = tk.Frame(self, bg=COLOR_BG)
        wrapper.pack(fill="both", expand=True)
        self.column = tk.Frame(wrapper, bg=COLOR_BG)
        self.column.place(relx=0.5, y=0, anchor="n", relheight=1,
                          width=CONTENT_WIDTH)
        wrapper.bind("<Configure>", self._on_resize)
        self._wrapper = wrapper

        tk.Label(self.column, text="Completed Tasks", bg=COLOR_BG,
                 fg=COLOR_TEXT, font=fonts["heading"]).pack(anchor="w")
        self.subtitle = tk.Label(self.column, text="", bg=COLOR_BG,
                                 fg=COLOR_MUTED, font=fonts["body"])
        self.subtitle.pack(anchor="w", pady=(2, 16))

        # --- green "Great job!" banner (hidden while nothing is done) ---
        self.banner = tk.Canvas(self.column, height=70, bg=COLOR_BG,
                                highlightthickness=0)
        self.banner.bind("<Configure>", lambda e: self._draw_banner())
        self.banner_text = ""

        # --- list card ---
        self.card = tk.Frame(self.column, bg=COLOR_WHITE,
                             highlightbackground=COLOR_FIELD_LINE,
                             highlightthickness=1)
        self.scroll = ScrollFrame(self.card, bg=COLOR_WHITE,
                                  max_height=self._max_list_height)
        self.scroll.pack(fill="x")
        self.footer = tk.Frame(self.card, bg="#fbfcfe")
        tk.Frame(self.footer, bg=COLOR_LINE, height=1).pack(fill="x")
        self.footer_label = tk.Label(self.footer, text="", bg="#fbfcfe",
                                     fg=COLOR_MUTED, font=fonts["small"])
        self.footer_label.pack(anchor="w", padx=16, pady=10)

        store.subscribe(self.refresh)
        self.refresh()

    # ---- sizing ---------------------------------------------------------
    def _max_list_height(self):
        # leave room for heading, banner and footer
        return max(150, self._wrapper.winfo_height() - 230)

    def _on_resize(self, event):
        self.column.place_configure(width=min(CONTENT_WIDTH, event.width))
        self.scroll.refresh_layout()

    # ---- banner ---------------------------------------------------------
    def _draw_banner(self):
        c = self.banner
        w = c.winfo_width()
        if w < 10:
            return
        c.delete("all")
        draw_rounded_rect(c, 1, 1, w - 1, 69, 14, fill=BANNER_GREEN,
                          outline=BANNER_GREEN)
        c.create_oval(16, 15, 56, 55, fill="#3fcf8e", outline="#3fcf8e")
        c.create_text(36, 35, text="🎉", font=self.fonts["card_title"])
        c.create_text(72, 26, text="Great job!", anchor="w", fill="white",
                      font=self.fonts["card_title"])
        c.create_text(72, 46, text=self.banner_text, anchor="w",
                      fill="white", font=self.fonts["small"])

    # ---- content --------------------------------------------------------
    def refresh(self):
        done = self.store.completed_tasks()
        count = len(done)
        self.subtitle.config(text=f"{plural(count, 'task')} completed")

        # banner + card are re-packed in order each time
        for widget in (self.banner, self.card, self.footer):
            widget.pack_forget()
        if count:
            self.banner_text = (f"You have completed {plural(count, 'task')}. "
                                f"Keep up the momentum!")
            self.banner.pack(fill="x", pady=(0, 16))
            self._draw_banner()
        self.card.pack(fill="x")

        self.scroll.clear()
        if not done:
            tk.Label(self.scroll.body,
                     text="No completed tasks yet.\nClick the circle next to "
                          "a task on the Dashboard to mark it as done.",
                     bg=COLOR_WHITE, fg=COLOR_MUTED, font=self.fonts["body"],
                     justify="center").pack(pady=40)
        else:
            for index, task in enumerate(done):
                self._build_row(task, last=index == count - 1)
            self.footer.pack(fill="x")
            self.footer_label.config(text=f"{plural(count, 'completed task')}")
        self.scroll.refresh_layout()

    def _build_row(self, task, last):
        fonts = self.fonts
        row = tk.Frame(self.scroll.body, bg=COLOR_WHITE)
        row.pack(fill="x", padx=16, pady=11)

        check = tk.Canvas(row, width=18, height=18, bg=COLOR_WHITE,
                          highlightthickness=0, cursor="hand2")
        check.create_oval(1, 1, 17, 17, fill=COLOR_GREEN, outline=COLOR_GREEN)
        check.create_text(9, 9, text="✓", fill="white",
                          font=fonts["check_mark"])
        check.pack(side="left", padx=(0, 12), anchor="n", pady=(2, 0))
        check.bind("<Button-1>",
                   lambda e, tid=task.id: self.store.set_completed(tid, False))

        # right side first so long titles can never push it out
        delete_button(row, fonts, lambda t=task: open_delete_dialog(
            self.winfo_toplevel(), fonts, self.store, t)).pack(
            side="right", padx=(2, 0))
        edit_button(row, fonts, lambda t=task: open_edit_dialog(
            self.winfo_toplevel(), fonts, self.store, t)).pack(
            side="right", padx=(8, 2))
        tk.Label(row, text=format_date(task.due), bg=COLOR_WHITE,
                 fg=COLOR_MUTED, font=fonts["small"], width=11,
                 anchor="e").pack(side="right")
        create_outlined_badge(row, task.priority, fonts).pack(side="right",
                                                             padx=8)

        text_col = tk.Frame(row, bg=COLOR_WHITE)
        text_col.pack(side="left", fill="x", expand=True)
        tk.Label(text_col, text=shorten(task.title, 40), bg=COLOR_WHITE,
                 fg="#5b6075", font=fonts["body_strike"],
                 anchor="w").pack(fill="x")
        if task.description:
            tk.Label(text_col, text=shorten(task.description, 60),
                     bg=COLOR_WHITE, fg=COLOR_MUTED, font=fonts["small"],
                     anchor="w").pack(fill="x")

        if not last:
            tk.Frame(self.scroll.body, bg=COLOR_LINE, height=1).pack(fill="x")