import tkinter as tk
from datetime import date, datetime

import dashboard_data as D
from my_tasks_page import Dropdown
from task_utils import (
    due_label, OVERDUE_RED, TODAY_AMBER, CHIP_BG, CHIP_FG,
)
from ui_common import (
    COLOR_BG, COLOR_WHITE, COLOR_TEXT, COLOR_MUTED, COLOR_LINE,
    COLOR_PURPLE, COLOR_GREEN, COLOR_FIELD_LINE, PRIORITY_STYLES,
    create_priority_badge, shorten,
)

USER_NAME = ""      # filled in with the signed-in account's first name
GRID_GREY = "#c3c6d8"
KPI_DEFS = [("total", "Total tasks"), ("done", "Completed"),
            ("pending", "Pending"), ("today", "Due today"),
            ("overdue", "Overdue"), ("rate", "Completion rate")]


def greeting_text(name):
    """'Good Morning, Name! 👋' - the wording follows the time of day."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        word = "Good Morning"
    elif 12 <= hour < 17:
        word = "Good Afternoon"
    else:
        word = "Good Evening"
    return f"{word}, {name}! 👋" if name else f"{word}! 👋"


def progress_caption(done, total):
    """'3 of 8 tasks completed', 'All 5 tasks completed', 'No tasks yet'."""
    if total == 0:
        return "No tasks yet"
    noun = "task" if total == 1 else "tasks"
    if done == total:
        return f"All {total} {noun} completed"
    return f"{done} of {total} {noun} completed"


# =====================================================================
# Charts (plain canvas drawing, redrawn whenever the size changes)
# =====================================================================
class Chart(tk.Canvas):
    def __init__(self, parent, fonts, height):
        super().__init__(parent, height=height, bg=COLOR_WHITE,
                         highlightthickness=0)
        self.fonts = fonts
        self.data = None
        self.bind("<Configure>", lambda e: self.redraw())

    def set_data(self, *data):
        self.data = data
        self.redraw()

    def redraw(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 40 or h < 40 or self.data is None:
            return
        self.delete("all")
        self.draw(w, h)

    def message(self, w, h, text):
        self.create_text(w / 2, h / 2, text=text, fill=COLOR_MUTED,
                         font=self.fonts["body"], justify="center")


class LineChart(Chart):
    """Two lines over a run of days: tasks due and tasks completed.
    Move the mouse over the chart to read the numbers for a day."""

    LEFT, RIGHT, TOP, BOTTOM = 34, 14, 30, 26

    def __init__(self, parent, fonts, height=230):
        super().__init__(parent, fonts, height)
        self.bind("<Motion>", self._hover)
        self.bind("<Leave>", lambda e: self.delete("tip"))

    def _geometry(self, w, h):
        pw = w - self.LEFT - self.RIGHT
        ph = h - self.TOP - self.BOTTOM
        return pw, ph

    def _x(self, i, n, w):
        pw, _ = self._geometry(w, self.winfo_height())
        return self.LEFT + pw * (i + 0.5) / n

    def draw(self, w, h):
        days, due, done = self.data
        n = len(days)
        pw, ph = self._geometry(w, h)
        step, top_value = D.nice_axis(max(due + done + [0]))
        base = self.TOP + ph

        def y(value):
            return base - ph * value / top_value

        for i in range(5):                               # gridlines + y labels
            value = step * i
            self.create_line(self.LEFT, y(value), w - self.RIGHT, y(value),
                             fill=COLOR_LINE)
            self.create_text(self.LEFT - 8, y(value), text=str(value),
                             anchor="e", fill=COLOR_MUTED,
                             font=self.fonts["small"])

        skip = max(1, -(-n // 7))                        # x labels
        week = n <= 7
        for i, day in enumerate(days):
            if i % skip == 0:
                text = day.strftime("%a") if week else \
                    f"{day.strftime('%b')} {day.day}"
                self.create_text(self._x(i, n, w), base + 14, text=text,
                                 fill=COLOR_MUTED, font=self.fonts["small"])

        today = date.today()
        if today in days:                                # "today" marker
            x = self._x(days.index(today), n, w)
            self.create_line(x, self.TOP, x, base, fill=GRID_GREY,
                             dash=(3, 3))

        points_done = [(self._x(i, n, w), y(v)) for i, v in enumerate(done)]
        points_due = [(self._x(i, n, w), y(v)) for i, v in enumerate(due)]
        if n > 1:                                        # soft fill under "completed"
            area = [(points_done[0][0], base)] + points_done + \
                   [(points_done[-1][0], base)]
            self.create_polygon(*[c for p in area for c in p], fill=CHIP_BG,
                                outline="")
            self.create_line(*[c for p in points_due for c in p],
                             fill=TODAY_AMBER, width=2, dash=(5, 3))
            self.create_line(*[c for p in points_done for c in p],
                             fill=COLOR_PURPLE, width=2)
        for (x, yy) in points_due:
            self.create_oval(x - 2, yy - 2, x + 2, yy + 2, fill=TODAY_AMBER,
                             outline=TODAY_AMBER)
        for (x, yy) in points_done:
            self.create_oval(x - 3, yy - 3, x + 3, yy + 3, fill=COLOR_PURPLE,
                             outline=COLOR_PURPLE)

        legend_x = self.LEFT
        for color, label in ((COLOR_PURPLE, "Completed"),
                             (TODAY_AMBER, "Due")):
            self.create_oval(legend_x, 10, legend_x + 8, 18, fill=color,
                             outline=color)
            self.create_text(legend_x + 13, 14, text=label, anchor="w",
                             fill=COLOR_MUTED, font=self.fonts["small"])
            legend_x += 14 + self.fonts["small"].measure(label) + 18

    def _hover(self, event):
        self.delete("tip")
        if self.data is None:
            return
        days, due, done = self.data
        w = self.winfo_width()
        n = len(days)
        pw, _ = self._geometry(w, self.winfo_height())
        if not (self.LEFT <= event.x <= w - self.RIGHT) or n == 0:
            return
        i = min(max(int(round((event.x - self.LEFT) / pw * n - 0.5)), 0),
                n - 1)
        x = self._x(i, n, w)
        self.create_line(x, self.TOP, x, self.TOP + self._geometry(
            w, self.winfo_height())[1], fill=COLOR_PURPLE, tags="tip")
        text = (f"{days[i].strftime('%a, %b')} {days[i].day}\n"
                f"Completed: {done[i]}\nDue: {due[i]}")
        label = self.create_text(0, 0, text=text, anchor="nw",
                                 fill=COLOR_TEXT, font=self.fonts["small"],
                                 tags="tip")
        x1, y1, x2, y2 = self.bbox(label)
        width, height = x2 - x1 + 16, y2 - y1 + 12
        left = x + 12 if x + 12 + width < w else x - 12 - width
        top = self.TOP + 4
        self.coords(label, left + 8, top + 6)
        box = self.create_rectangle(left, top, left + width, top + height,
                                    fill=COLOR_WHITE, outline=COLOR_FIELD_LINE,
                                    tags="tip")
        self.tag_raise(label)


class DonutChart(Chart):
    """Completed / Pending / Overdue share of the tasks in view."""

    def draw(self, w, h):
        done, pending, overdue = self.data
        total = done + pending + overdue
        size = min(h - 24, w * 0.46)
        cx, cy = 14 + size / 2, h / 2
        box = (cx - size / 2, cy - size / 2, cx + size / 2, cy + size / 2)
        if not total:                                   # nothing to show yet
            self.create_oval(*box, fill=COLOR_LINE, outline=COLOR_LINE)

        segments = [("Completed", done, COLOR_GREEN),
                    ("Pending", pending, COLOR_PURPLE),
                    ("Overdue", overdue, OVERDUE_RED)]
        start = 90.0
        for _, count, color in segments:
            if not count:
                continue
            if count == total:                  # one status = whole pie
                self.create_oval(*box, fill=color, outline=color)
                break
            extent = -360.0 * count / total
            self.create_arc(*box, start=start, extent=extent,
                            style="pieslice", fill=color,
                            outline=COLOR_WHITE, width=2)
            start += extent

        if not total:
            self.create_text(cx, cy, text="No tasks", fill=COLOR_MUTED,
                             font=self.fonts["body"])

        x = cx + size / 2 + 22
        row_h = 40
        y0 = cy - row_h * len(segments) / 2 + row_h / 2
        for i, (label, count, color) in enumerate(segments):
            y = y0 + i * row_h
            share = f"{round(100 * count / total)}%" if total else "0%"
            self.create_oval(x, y - 12, x + 10, y - 2, fill=color,
                             outline=color)
            self.create_text(x + 16, y - 7, text=label, anchor="w",
                             fill=COLOR_TEXT, font=self.fonts["small_bold"])
            self.create_text(x + 16, y + 9, text=f"{count}  ·  {share}",
                             anchor="w", fill=COLOR_MUTED,
                             font=self.fonts["small"])


class BarChart(Chart):
    """Horizontal bars: [(label, completed, open, colour_for_open)].
    The green part of each bar is what is already done."""

    ROW = 34

    def set_rows(self, rows, empty_text="No data yet."):
        self.configure(height=max(1, len(rows)) * self.ROW + 12)
        self.set_data(rows, empty_text)

    def draw(self, w, h):
        rows, empty_text = self.data
        if not rows or not any(d + o for _, d, o, _ in rows):
            self.message(w, h, empty_text)
            return
        label_w = 96
        right_w = 54
        bar_x0, bar_x1 = label_w + 8, w - right_w
        widest = max(d + o for _, d, o, _ in rows)
        for i, (label, finished, opened, color) in enumerate(rows):
            cy = 6 + i * self.ROW + self.ROW / 2
            self.create_text(0, cy, text=shorten(label, 13), anchor="w",
                             fill=COLOR_TEXT, font=self.fonts["small"])
            self.create_rectangle(bar_x0, cy - 6, bar_x1, cy + 6,
                                  fill=COLOR_LINE, outline="")
            span = bar_x1 - bar_x0
            done_w = span * finished / widest
            open_w = span * opened / widest
            if finished:
                self.create_rectangle(bar_x0, cy - 6, bar_x0 + done_w,
                                      cy + 6, fill=COLOR_GREEN, outline="")
            if opened:
                self.create_rectangle(bar_x0 + done_w, cy - 6,
                                      bar_x0 + done_w + open_w, cy + 6,
                                      fill=color, outline="")
            self.create_text(w, cy, text=f"{finished}/{finished + opened}",
                             anchor="e", fill=COLOR_MUTED,
                             font=self.fonts["small"])


# =====================================================================
# Small building blocks
# =====================================================================
class Card(tk.Frame):
    """A flat white card with a thin border, a title and a subtitle."""

    def __init__(self, parent, fonts, title, subtitle=""):
        super().__init__(parent, bg=COLOR_WHITE, highlightthickness=1,
                         highlightbackground=COLOR_FIELD_LINE)
        self.head = tk.Frame(self, bg=COLOR_WHITE)
        self.head.pack(fill="x", padx=18, pady=(14, 0))
        titles = tk.Frame(self.head, bg=COLOR_WHITE)
        titles.pack(side="left")
        tk.Label(titles, text=title, bg=COLOR_WHITE, fg=COLOR_TEXT,
                 font=fonts["card_title"]).pack(anchor="w")
        self.subtitle = tk.Label(titles, text=subtitle, bg=COLOR_WHITE,
                                 fg=COLOR_MUTED, font=fonts["small"])
        self.subtitle.pack(anchor="w")
        self.body = tk.Frame(self, bg=COLOR_WHITE)
        self.body.pack(fill="both", expand=True, padx=18, pady=(8, 14))


def link_label(parent, fonts, text, command, bg=COLOR_WHITE):
    label = tk.Label(parent, text=text, bg=bg, fg=COLOR_PURPLE,
                     font=fonts["small_bold"], cursor="hand2")
    label.bind("<Button-1>", lambda e: command())
    return label


# =====================================================================
# THE PAGE
# =====================================================================
class DashboardPage(tk.Frame):
    def __init__(self, parent, fonts, store, on_add_task=None,
                 on_view_completed=None, on_view_tasks=None):
        """on_add_task is accepted only so older code still works - the
        Dashboard no longer has an Add Task button."""
        super().__init__(parent, bg=COLOR_BG)
        self.fonts = fonts
        self.store = store
        self.on_view_completed = on_view_completed or (lambda: None)
        self.on_view_tasks = on_view_tasks or (lambda: None)
        self.user_name = USER_NAME
        self._dirty = False

        self.range_var = tk.StringVar(value="All time")
        self.category_var = tk.StringVar(value=D.ALL_CATEGORIES)
        self.priority_var = tk.StringVar(value=D.ALL_PRIORITIES)

        self._build_scroller()
        self._build_header()
        self._build_filters()
        self._build_kpis()
        self._build_charts()
        self._build_tables()

        store.subscribe(self._on_store_change)   # live: redraw on any change
        self.refresh()
        self.bind("<Map>", self._on_map)
        self._tick()

    # ---- the scrolling page --------------------------------------------
    def _build_scroller(self):
        self.canvas = tk.Canvas(self, bg=COLOR_BG, highlightthickness=0,
                                yscrollincrement=24)
        bar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.page = tk.Frame(self.canvas, bg=COLOR_BG)
        window = self.canvas.create_window((0, 0), window=self.page,
                                           anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            window, width=e.width - 6))
        self.page.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.bind_all("<MouseWheel>", self._on_wheel, add="+")
        self.bind_all("<Button-4>", self._on_wheel, add="+")
        self.bind_all("<Button-5>", self._on_wheel, add="+")

    def _on_wheel(self, event):
        if not self.winfo_ismapped():
            return
        under = self.winfo_containing(event.x_root, event.y_root)
        while under is not None and under is not self:
            under = under.master
        if under is None or self.canvas.yview() == (0.0, 1.0):
            return
        up = event.num == 4 or getattr(event, "delta", 0) > 0
        self.canvas.yview_scroll(-3 if up else 3, "units")

    # ---- header + filters ----------------------------------------------
    def _build_header(self):
        fonts = self.fonts
        head = tk.Frame(self.page, bg=COLOR_BG)
        head.pack(fill="x", padx=(0, 6))
        left = tk.Frame(head, bg=COLOR_BG)
        left.pack(side="left")
        self.date_label = tk.Label(left, text="", bg=COLOR_BG, fg=COLOR_MUTED,
                                   font=fonts["small"])
        self.date_label.pack(anchor="w")
        self.greeting = tk.Label(left, text=greeting_text(self.user_name),
                                 bg=COLOR_BG, fg=COLOR_TEXT,
                                 font=fonts["heading"])
        self.greeting.pack(anchor="w")
        tk.Label(left, text="Here's how your work is going.", bg=COLOR_BG,
                 fg=COLOR_MUTED, font=fonts["body"]).pack(anchor="w",
                                                          pady=(2, 0))
        right = tk.Frame(head, bg=COLOR_BG)
        right.pack(side="right", anchor="n")
        row = tk.Frame(right, bg=COLOR_BG)
        row.pack(anchor="e")
        tk.Label(row, text="●", bg=COLOR_BG, fg=COLOR_GREEN,
                 font=fonts["small"]).pack(side="left")
        tk.Label(row, text=" Live", bg=COLOR_BG, fg=COLOR_TEXT,
                 font=fonts["small_bold"]).pack(side="left")
        self.updated_label = tk.Label(right, text="", bg=COLOR_BG,
                                      fg=COLOR_MUTED, font=fonts["small"])
        self.updated_label.pack(anchor="e")
        link_label(right, fonts, "Open My Tasks →", lambda: self.on_view_tasks(),
                   bg=COLOR_BG).pack(anchor="e", pady=(6, 0))

    def _build_filters(self):
        fonts = self.fonts
        bar = tk.Frame(self.page, bg=COLOR_BG)
        bar.pack(fill="x", pady=(16, 14), padx=(0, 6))
        tk.Label(bar, text="Filters", bg=COLOR_BG, fg=COLOR_MUTED,
                 font=fonts["small_bold"]).pack(side="left", padx=(0, 10))
        changed = lambda: self.after_idle(self.refresh)
        Dropdown(bar, fonts, self.range_var, D.RANGES, changed,
                 12).pack(side="left", padx=(0, 8))
        self.category_box = Dropdown(bar, fonts, self.category_var,
                                     [D.ALL_CATEGORIES], changed, 14)
        self.category_box.pack(side="left", padx=(0, 8))
        Dropdown(bar, fonts, self.priority_var,
                 [D.ALL_PRIORITIES, *D.PRIORITIES], changed,
                 14).pack(side="left", padx=(0, 10))
        link_label(bar, fonts, "Reset", self.reset_filters,
                   bg=COLOR_BG).pack(side="left")

    def reset_filters(self):
        self.range_var.set("All time")
        self.category_var.set(D.ALL_CATEGORIES)
        self.priority_var.set(D.ALL_PRIORITIES)
        self.refresh()

    # ---- KPI cards -----------------------------------------------------
    def _build_kpis(self):
        fonts = self.fonts
        row = tk.Frame(self.page, bg=COLOR_BG)
        row.pack(fill="x", padx=(0, 6))
        self.kpi = {}
        for col, (key, label) in enumerate(KPI_DEFS):
            row.columnconfigure(col, weight=1, uniform="kpi")
            card = tk.Frame(row, bg=COLOR_WHITE, highlightthickness=1,
                            highlightbackground=COLOR_FIELD_LINE)
            card.grid(row=0, column=col, sticky="nsew",
                      padx=(0 if col == 0 else 5, 0 if col == 5 else 5))
            tk.Label(card, text=label, bg=COLOR_WHITE, fg=COLOR_MUTED,
                     font=fonts["small"]).pack(anchor="w", padx=14,
                                               pady=(12, 0))
            number = tk.Label(card, text="0", bg=COLOR_WHITE, fg=COLOR_TEXT,
                              font=fonts["stat_number"])
            number.pack(anchor="w", padx=14)
            sub = tk.Label(card, text="", bg=COLOR_WHITE, fg=COLOR_MUTED,
                           font=fonts["small"])
            sub.pack(anchor="w", padx=14, pady=(0, 12))
            self.kpi[key] = (number, sub)

    # ---- charts ----------------------------------------------------------
    def _build_charts(self):
        fonts = self.fonts
        row1 = tk.Frame(self.page, bg=COLOR_BG)
        row1.pack(fill="x", pady=(14, 0), padx=(0, 6))
        row1.columnconfigure(0, weight=3, uniform="c1")
        row1.columnconfigure(1, weight=2, uniform="c1")
        self.trend_card = Card(row1, fonts, "Due vs completed")
        self.trend_card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        self.trend_chart = LineChart(self.trend_card.body, fonts)
        self.trend_chart.pack(fill="x")
        self.status_card = Card(row1, fonts, "Tasks by status",
                                "Share of the tasks in view")
        self.status_card.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        self.status_chart = DonutChart(self.status_card.body, fonts, 230)
        self.status_chart.pack(fill="x")

        row2 = tk.Frame(self.page, bg=COLOR_BG)
        row2.pack(fill="x", pady=(14, 0), padx=(0, 6))
        row2.columnconfigure(0, weight=1, uniform="c2")
        row2.columnconfigure(1, weight=1, uniform="c2")
        self.priority_card = Card(row2, fonts, "Tasks by priority",
                                  "Green = completed")
        self.priority_card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        self.priority_chart = BarChart(self.priority_card.body, fonts, 120)
        self.priority_chart.pack(fill="x")
        self.category_card = Card(row2, fonts, "Tasks by category",
                                  "Green = completed")
        self.category_card.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        self.category_chart = BarChart(self.category_card.body, fonts, 120)
        self.category_chart.pack(fill="x")

    # ---- tables -----------------------------------------------------------
    def _build_tables(self):
        fonts = self.fonts
        row = tk.Frame(self.page, bg=COLOR_BG)
        row.pack(fill="x", pady=(14, 18), padx=(0, 6))
        row.columnconfigure(0, weight=3, uniform="t")
        row.columnconfigure(1, weight=2, uniform="t")
        self.pending_card = Card(row, fonts, "Pending tasks",
                                 "Soonest due first")
        self.pending_card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        link_label(self.pending_card.head, fonts, "View all →",
                   lambda: self.on_view_tasks()).pack(side="right",
                                                      anchor="n")
        self.pending_table = tk.Frame(self.pending_card.body, bg=COLOR_WHITE)
        self.pending_table.pack(fill="x")

        self.recent_card = Card(row, fonts, "Recently completed",
                                "Latest finished tasks")
        self.recent_card.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        link_label(self.recent_card.head, fonts, "View all →",
                   lambda: self.on_view_completed()).pack(side="right",
                                                          anchor="n")
        self.recent_table = tk.Frame(self.recent_card.body, bg=COLOR_WHITE)
        self.recent_table.pack(fill="x")

    # ---- keeping it live -----------------------------------------------------
    def set_user_name(self, name):
        """Greets whoever just signed in (first name only)."""
        self.user_name = name.split()[0] if name.split() else name
        self._update_greeting()

    def _update_greeting(self):
        self.greeting.config(text=greeting_text(self.user_name))
        self.date_label.config(text=datetime.now().strftime("%A, %d %B %Y"))

    def _on_store_change(self):
        if self.winfo_ismapped():
            self.refresh()
        else:
            self._dirty = True            # redraw when the page is shown

    def _on_map(self, event=None):
        self._update_greeting()
        if self._dirty:
            self.refresh()

    def _tick(self):
        """Once a minute: keep the greeting right and the numbers fresh."""
        if self.winfo_ismapped():
            self._update_greeting()
            self.refresh()
        self.after(60 * 1000, self._tick)

    # ---- drawing everything ----------------------------------------------------
    def _update_category_choices(self):
        choices = [D.ALL_CATEGORIES, *self.store.categories()]
        if any(not t.category for t in self.store.tasks):
            choices.append(D.NO_CATEGORY)
        self.category_box.set_values(choices)
        if self.category_var.get() not in choices:
            self.category_var.set(D.ALL_CATEGORIES)

    def refresh(self):
        self._dirty = False
        today = date.today()
        self._update_category_choices()
        scoped = D.filter_tasks(self.store.tasks, self.range_var.get(),
                                self.category_var.get(),
                                self.priority_var.get(), today)
        self._update_kpis(D.kpis(scoped, today))

        days, due, done = D.trend(scoped, self.range_var.get(), today)
        self.trend_card.subtitle.config(
            text=f"{days[0].strftime('%b')} {days[0].day} – "
                 f"{days[-1].strftime('%b')} {days[-1].day}")
        self.trend_chart.set_data(days, due, done)

        k = D.kpis(scoped, today)
        self.status_chart.set_data(k["done"], k["open_not_late"],
                                   k["overdue"])
        self.priority_chart.set_rows(
            [(name, d, o, PRIORITY_STYLES[name]["dot"])
             for name, d, o in D.by_priority(scoped)])
        self.category_chart.set_rows(
            [(name, d, o, COLOR_PURPLE)
             for name, d, o in D.by_category(scoped)],
            "Give your tasks a category\nto see them grouped here.")

        self._fill_pending(D.pending_table(scoped))
        self._fill_recent(D.recent_table(scoped))
        self.updated_label.config(
            text=f"Updated {datetime.now().strftime('%H:%M:%S')}")

    def _update_kpis(self, k):
        texts = {
            "total": (str(k["total"]), "in this view"),
            "done": (str(k["done"]), "tasks finished"),
            "pending": (str(k["pending"]), "still open"),
            "today": (str(k["today"]), "due today"),
            "overdue": (str(k["overdue"]),
                        "need attention" if k["overdue"] else "all on track"),
            "rate": (f"{k['rate']}%", f"{k['done']} of {k['total']} done"),
        }
        for key, (number, sub) in self.kpi.items():
            value, caption = texts[key]
            color = COLOR_TEXT
            if key == "overdue" and k["overdue"]:
                color = OVERDUE_RED
            elif key == "done" and k["done"]:
                color = COLOR_GREEN
            number.config(text=value, fg=color)
            sub.config(text=caption)

    # ---- tables ------------------------------------------------------------------
    def _table_header(self, table, labels):
        for col, text in enumerate(labels):
            tk.Label(table, text=text, bg=COLOR_WHITE, fg=COLOR_MUTED,
                     font=self.fonts["small_bold"], anchor="w").grid(
                row=0, column=col, sticky="w", padx=(0, 10), pady=(4, 6))
        tk.Frame(table, bg=COLOR_LINE, height=1).grid(
            row=1, column=0, columnspan=len(labels), sticky="ew")

    def _chip(self, table, text, row, column):
        if text:
            tk.Label(table, text=shorten(text, 14), bg=CHIP_BG, fg=CHIP_FG,
                     font=self.fonts["small"], padx=6).grid(
                row=row, column=column, sticky="w", padx=(0, 10), pady=7)
        else:
            tk.Label(table, text="—", bg=COLOR_WHITE, fg=COLOR_MUTED,
                     font=self.fonts["small"]).grid(
                row=row, column=column, sticky="w", padx=(0, 10), pady=7)

    def _fill_pending(self, tasks):
        table = self.pending_table
        for child in table.winfo_children():
            child.destroy()
        if not tasks:
            tk.Label(table, text="Nothing pending in this view. 🎉",
                     bg=COLOR_WHITE, fg=COLOR_MUTED,
                     font=self.fonts["body"]).pack(pady=24)
            return
        table.columnconfigure(1, weight=1)
        self._table_header(table, ["", "Task name", "Category", "Priority",
                                   "Due date"])
        for i, task in enumerate(tasks):
            r = 2 + i * 2
            self._check_circle(table, task, r)
            title = shorten(task.title, 40) + \
                ("  🔁" if task.recurrence != "none" else "")
            tk.Label(table, text=title, bg=COLOR_WHITE, fg=COLOR_TEXT,
                     font=self.fonts["body"], anchor="w").grid(
                row=r, column=1, sticky="ew", padx=(0, 10), pady=7)
            self._chip(table, task.category, r, 2)
            create_priority_badge(table, task.priority, self.fonts).grid(
                row=r, column=3, sticky="w", padx=(0, 10), pady=7)
            text, color = due_label(task)
            tk.Label(table, text=text, bg=COLOR_WHITE,
                     fg=color or COLOR_MUTED, font=self.fonts["small"],
                     anchor="w").grid(row=r, column=4, sticky="w", pady=7)
            tk.Frame(table, bg=COLOR_LINE, height=1).grid(
                row=r + 1, column=0, columnspan=5, sticky="ew")

    def _check_circle(self, table, task, row):
        box = tk.Canvas(table, width=18, height=18, bg=COLOR_WHITE,
                        highlightthickness=0, cursor="hand2")
        ring = box.create_oval(2, 2, 16, 16, outline="#d8dae6", width=2)
        box.grid(row=row, column=0, sticky="w", padx=(0, 10), pady=7)
        box.bind("<Enter>", lambda e: box.itemconfig(ring,
                                                     outline=COLOR_GREEN))
        box.bind("<Leave>", lambda e: box.itemconfig(ring,
                                                     outline="#d8dae6"))

        def done(event):
            box.itemconfig(ring, fill=COLOR_GREEN, outline=COLOR_GREEN)
            box.create_text(9, 9, text="✓", fill="white",
                            font=self.fonts["check_mark"])
            box.after(220, lambda: self.store.set_completed(task.id, True))

        box.bind("<Button-1>", done)

    def _fill_recent(self, tasks):
        table = self.recent_table
        for child in table.winfo_children():
            child.destroy()
        if not tasks:
            tk.Label(table, text="Nothing completed yet.", bg=COLOR_WHITE,
                     fg=COLOR_MUTED, font=self.fonts["body"]).pack(pady=24)
            return
        table.columnconfigure(1, weight=1)
        self._table_header(table, ["", "Task name", "Finished"])
        for i, task in enumerate(tasks):
            r = 2 + i * 2
            mark = tk.Canvas(table, width=18, height=18, bg=COLOR_WHITE,
                             highlightthickness=0)
            mark.create_oval(1, 1, 17, 17, fill=COLOR_GREEN,
                             outline=COLOR_GREEN)
            mark.create_text(9, 9, text="✓", fill="white",
                             font=self.fonts["check_mark"])
            mark.grid(row=r, column=0, sticky="w", padx=(0, 10), pady=7)
            tk.Label(table, text=shorten(task.title, 30), bg=COLOR_WHITE,
                     fg=COLOR_TEXT, font=self.fonts["body"],
                     anchor="w").grid(row=r, column=1, sticky="ew",
                                      padx=(0, 10), pady=7)
            when = task.completed_at
            tk.Label(table, text=f"{when.strftime('%b')} {when.day}",
                     bg=COLOR_WHITE, fg=COLOR_MUTED, font=self.fonts["small"],
                     anchor="w").grid(row=r, column=2, sticky="w", pady=7)
            tk.Frame(table, bg=COLOR_LINE, height=1).grid(
                row=r + 1, column=0, columnspan=3, sticky="ew")