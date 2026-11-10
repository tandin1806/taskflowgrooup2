import calendar
import tkinter as tk
from datetime import date

from ui_common import (
    COLOR_BG, COLOR_WHITE, COLOR_TEXT, COLOR_MUTED, COLOR_PURPLE,
    COLOR_GREEN, COLOR_FIELD_LINE, shorten,
)
from task_utils import (
    is_overdue, OVERDUE_RED, CHIP_BG, CHIP_FG,
)

CELL_HEIGHT = 46
MAX_IN_CELL = 2
MAX_IN_LIST = 4

# (background, text colour) for a task shown inside a day cell
PRIORITY_COLORS = {
    "High": ("#fee2e2", "#b91c1c"),
    "Medium": ("#fef3c7", "#b45309"),
    "Low": ("#dcfce7", "#15803d"),
}
DONE_COLORS = ("#eef0f5", "#8a8fa6")
OVERDUE_COLORS = ("#fee2e2", OVERDUE_RED)


def _task_colors(task):
    if task.completed:
        return DONE_COLORS
    if is_overdue(task):
        return OVERDUE_COLORS
    return PRIORITY_COLORS.get(task.priority, PRIORITY_COLORS["Low"])


class CalendarView(tk.Frame):
    def __init__(self, parent, fonts, store):
        super().__init__(parent, bg=COLOR_BG)
        self.fonts = fonts
        self.store = store
        today = date.today()
        self.year, self.month = today.year, today.month
        self.selected = today

        self._calendar = calendar.Calendar(firstweekday=0)   # Monday first

        # ---- month header ----
        head = tk.Frame(self, bg=COLOR_BG)
        head.pack(fill="x", pady=(0, 6))
        self._nav_button(head, "‹", lambda: self.change_month(-1)).pack(
            side="left")
        self.title = tk.Label(head, text="", bg=COLOR_BG, fg=COLOR_TEXT,
                              font=fonts["card_title"], width=16)
        self.title.pack(side="left", padx=6)
        self._nav_button(head, "›", lambda: self.change_month(1)).pack(
            side="left")
        self._nav_button(head, "Today", self.go_today, wide=True).pack(
            side="right")

        # ---- grid + selected-day list ----
        self.grid_frame = tk.Frame(self, bg=COLOR_BG)
        self.grid_frame.pack(fill="x")
        self.detail = tk.Frame(self, bg=COLOR_BG)
        self.detail.pack(fill="x", pady=(10, 0))

        store.subscribe(self.refresh)
        self.refresh()

    # ---- small widgets -------------------------------------------------
    def _nav_button(self, parent, text, command, wide=False):
        label = tk.Label(parent, text=text, bg=COLOR_WHITE, fg=COLOR_TEXT,
                         font=self.fonts["small_bold"], cursor="hand2",
                         padx=14 if wide else 10, pady=3,
                         highlightthickness=1,
                         highlightbackground=COLOR_FIELD_LINE)
        label.bind("<Button-1>", lambda e: command())
        return label

    # ---- navigation ----------------------------------------------------
    def change_month(self, step):
        month = self.month + step
        self.year += (month - 1) // 12
        self.month = (month - 1) % 12 + 1
        self.refresh()

    def go_today(self):
        today = date.today()
        self.year, self.month, self.selected = today.year, today.month, today
        self.refresh()

    def select(self, day):
        self.selected = day
        if (day.year, day.month) != (self.year, self.month):
            self.year, self.month = day.year, day.month
        self.refresh()

    # ---- drawing -------------------------------------------------------
    def _tasks_by_day(self):
        by_day = {}
        for task in self.store.tasks:
            by_day.setdefault(task.due, []).append(task)
        for tasks in by_day.values():           # pending first, then High..Low
            tasks.sort(key=lambda t: (t.completed,
                                      ("High", "Medium", "Low").index(
                                          t.priority)
                                      if t.priority in
                                      ("High", "Medium", "Low") else 3))
        return by_day

    def refresh(self):
        self.title.config(
            text=f"{calendar.month_name[self.month]} {self.year}")
        for frame in (self.grid_frame, self.detail):
            for child in frame.winfo_children():
                child.destroy()

        by_day = self._tasks_by_day()
        today = date.today()
        weeks = self._calendar.monthdatescalendar(self.year, self.month)

        for col, name in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri",
                                    "Sat", "Sun")):
            tk.Label(self.grid_frame, text=name, bg=COLOR_BG,
                     fg=COLOR_MUTED, font=self.fonts["small_bold"]).grid(
                row=0, column=col, sticky="ew", pady=(0, 4))
            self.grid_frame.columnconfigure(col, weight=1, uniform="day")

        for row, week in enumerate(weeks, start=1):
            for col, day in enumerate(week):
                self._build_cell(row, col, day, by_day.get(day, []), today)
        self._build_detail(by_day.get(self.selected, []))

    def _build_cell(self, row, col, day, tasks, today):
        in_month = day.month == self.month
        is_today = day == today
        is_selected = day == self.selected
        border = COLOR_PURPLE if (is_today or is_selected) \
            else COLOR_FIELD_LINE
        cell = tk.Frame(self.grid_frame, bg=COLOR_WHITE, height=CELL_HEIGHT,
                        highlightthickness=2 if is_selected else 1,
                        highlightbackground=border, cursor="hand2")
        cell.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)
        cell.pack_propagate(False)

        number_color = COLOR_PURPLE if is_today else (
            COLOR_TEXT if in_month else "#b8bccd")
        number = tk.Label(cell, text=str(day.day), bg=COLOR_WHITE,
                          fg=number_color, font=self.fonts["small_bold"]
                          if is_today else self.fonts["small"], anchor="w")
        number.pack(fill="x", padx=4)
        widgets = [cell, number]

        for task in tasks[:MAX_IN_CELL]:
            bg, fg = _task_colors(task)
            chip = tk.Label(cell, text=shorten(task.title, 14), bg=bg,
                            fg=fg, font=self.fonts["small"], anchor="w",
                            padx=3)
            chip.pack(fill="x", padx=3, pady=(0, 1))
            widgets.append(chip)
        # no room left for a "+N more" line in a short cell: show it in the
        # number row instead
        if len(tasks) > MAX_IN_CELL:
            number.config(text=f"{day.day}  +{len(tasks) - MAX_IN_CELL}")

        for widget in widgets:
            widget.bind("<Button-1>", lambda e, d=day: self.select(d))

    def _build_detail(self, tasks):
        fonts = self.fonts
        day = self.selected
        tk.Label(self.detail, text=day.strftime("%A, %d %B %Y"),
                 bg=COLOR_BG, fg=COLOR_TEXT, font=fonts["label"]).pack(
            anchor="w")
        if not tasks:
            tk.Label(self.detail, text="No tasks on this day.", bg=COLOR_BG,
                     fg=COLOR_MUTED, font=fonts["small"]).pack(
                anchor="w", pady=(4, 0))
            return
        for task in tasks[:MAX_IN_LIST]:
            row = tk.Frame(self.detail, bg=COLOR_BG)
            row.pack(fill="x", pady=2)
            check = tk.Canvas(row, width=18, height=18, bg=COLOR_BG,
                              highlightthickness=0, cursor="hand2")
            if task.completed:
                check.create_oval(1, 1, 17, 17, fill=COLOR_GREEN,
                                  outline=COLOR_GREEN)
                check.create_text(9, 9, text="✓", fill="white",
                                  font=fonts["check_mark"])
            else:
                check.create_oval(2, 2, 16, 16, outline="#c3c6d8", width=2)
            check.pack(side="left", padx=(0, 8))
            check.bind("<Button-1>",
                       lambda e, tid=task.id, done=task.completed:
                       self.store.set_completed(tid, not done))
            _, color = _task_colors(task)
            title_font = fonts["body_strike"] if task.completed \
                else fonts["body"]
            tk.Label(row, text=shorten(task.title, 40), bg=COLOR_BG,
                     fg=COLOR_MUTED if task.completed else COLOR_TEXT,
                     font=title_font).pack(side="left")
            if task.category:
                tk.Label(row, text=shorten(task.category, 16), bg=CHIP_BG,
                         fg=CHIP_FG, font=fonts["small"], padx=6).pack(
                    side="left", padx=8)
            tk.Label(row, text=task.priority, bg=COLOR_BG, fg=color,
                     font=fonts["small_bold"]).pack(side="right")
        if len(tasks) > MAX_IN_LIST:
            tk.Label(self.detail,
                     text=f"+ {len(tasks) - MAX_IN_LIST} more on this day "
                          f"(see the List view)",
                     bg=COLOR_BG, fg=COLOR_MUTED, font=fonts["small"]).pack(
                anchor="w", pady=(2, 0))
