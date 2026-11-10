import tkinter as tk

from ui_common import (
    COLOR_BG, COLOR_WHITE, COLOR_TEXT, COLOR_MUTED, COLOR_PURPLE,
    COLOR_GREEN, COLOR_FIELD_BG, COLOR_FIELD_LINE,
    create_card, create_priority_badge, draw_rounded_rect, ScrollFrame,
    shorten, format_date,
)
from task_dialogs import (
    edit_button, delete_button, open_edit_dialog, open_delete_dialog,
)
from task_utils import (
    days_until, group_pending, due_label, PRIORITY_ORDER,
    OVERDUE_RED, TODAY_AMBER, CHIP_BG, CHIP_FG,
)
from calendar_view import CalendarView

ADD_HOVER = "#5a4bd6"

# ---- filter / sort choices (label -> what it means) ----
ALL = "All"
PRIORITY_CHOICES = [ALL, "High", "Medium", "Low"]
DUE_CHOICES = ["Any date", "Overdue", "Today", "Next 7 days", "Later"]
SORT_CHOICES = {
    "Due date (soonest)": lambda t: (t.due, PRIORITY_ORDER.get(t.priority, 3)),
    "Due date (latest)": lambda t: t.due,
    "Priority (high first)": lambda t: (PRIORITY_ORDER.get(t.priority, 3),
                                        t.due),
    "Priority (low first)": lambda t: (-PRIORITY_ORDER.get(t.priority, 3),
                                       t.due),
    "Title (A-Z)": lambda t: t.title.lower(),
    "Category": lambda t: (t.category == "", t.category.lower(), t.due),
}
SORT_REVERSED = {"Due date (latest)"}
DEFAULT_SORT = "Due date (soonest)"


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


# =====================================================================
# Small widgets used only by this page
# =====================================================================
class FilterTab(tk.Canvas):
    """A pill like 'All (8)'. Purple when active, white otherwise."""

    def __init__(self, parent, fonts, command, page_bg=COLOR_BG):
        super().__init__(parent, height=32, width=60, bg=page_bg,
                         highlightthickness=0, cursor="hand2")
        self.fonts = fonts
        self._text, self._active, self._hover = "", False, False
        self.bind("<Button-1>", lambda e: command())
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))

    def set(self, text, active):
        self._text, self._active = text, active
        self.configure(width=self.fonts["small_bold"].measure(text) + 34)
        self._draw()

    def _set_hover(self, value):
        self._hover = value
        self._draw()

    def _draw(self):
        w = int(self.cget("width"))
        h = int(self.cget("height"))
        self.delete("all")
        if self._active:
            fill, border, color = COLOR_PURPLE, COLOR_PURPLE, "white"
            font = self.fonts["small_bold"]
        else:
            fill = COLOR_FIELD_BG if self._hover else COLOR_WHITE
            border, color = COLOR_FIELD_LINE, COLOR_TEXT
            font = self.fonts["small"]
        draw_rounded_rect(self, 1, 1, w - 1, h - 1, 10, fill=fill,
                          outline=border)
        self.create_text(w / 2, h / 2, text=self._text, fill=color,
                         font=font)


class Dropdown(tk.Menubutton):
    """A small 'High  v' button that opens a list of choices. Plain Tk
    widgets, so it follows the Light / Dark theme like everything else."""

    def __init__(self, parent, fonts, variable, values, command, width):
        super().__init__(parent, font=fonts["small"], bg=COLOR_WHITE,
                         fg=COLOR_TEXT, activebackground=COLOR_FIELD_BG,
                         activeforeground=COLOR_TEXT, relief="flat", bd=0,
                         highlightthickness=1,
                         highlightbackground=COLOR_FIELD_LINE, padx=8,
                         pady=3, anchor="w", width=width, cursor="hand2")
        self.fonts = fonts
        self.variable = variable
        self.command = command
        self.menu = tk.Menu(self, tearoff=0, font=fonts["small"],
                            bg=COLOR_WHITE, fg=COLOR_TEXT,
                            activebackground=COLOR_PURPLE,
                            activeforeground="white", bd=0)
        self["menu"] = self.menu
        variable.trace_add("write", lambda *a: self._show())
        self.set_values(values)
        self._show()

    def _show(self):
        self.configure(text=f"{self.variable.get()}  ▾")

    def set_values(self, values):
        self.menu.delete(0, "end")
        for value in values:
            self.menu.add_command(label=value,
                                  command=lambda v=value: self._choose(v))

    def _choose(self, value):
        self.variable.set(value)
        self.command()


class AddTaskButton(tk.Canvas):
    """The purple '+ Add Task' button."""

    W, H = 112, 38

    def __init__(self, parent, fonts, command):
        super().__init__(parent, width=self.W, height=self.H, bg=COLOR_BG,
                         highlightthickness=0, cursor="hand2")
        self.fonts = fonts
        self._draw(COLOR_PURPLE)
        self.bind("<Button-1>", lambda e: command())
        self.bind("<Enter>", lambda e: self._draw(ADD_HOVER))
        self.bind("<Leave>", lambda e: self._draw(COLOR_PURPLE))

    def _draw(self, color):
        self.delete("all")
        draw_rounded_rect(self, 0, 0, self.W, self.H, 12, fill=color,
                          outline=color)
        self.create_text(self.W / 2, self.H / 2, text="+   Add Task",
                         fill="white", font=self.fonts["small_bold"])


# =====================================================================
# The page
# =====================================================================
class MyTasksPage(tk.Frame):
    def __init__(self, parent, fonts, store, on_add_task, on_view_completed):
        super().__init__(parent, bg=COLOR_BG)
        self.fonts = fonts
        self.store = store
        self.on_view_completed = on_view_completed
        self.filter = "all"            # "all" or "pending"
        self.search = ""
        self.view = "list"             # "list" or "calendar"
        self.priority_var = tk.StringVar(value=ALL)
        self.category_var = tk.StringVar(value=ALL)
        self.due_var = tk.StringVar(value=DUE_CHOICES[0])
        self.sort_var = tk.StringVar(value=DEFAULT_SORT)

        # ---- top part: heading, add button, tabs ----
        self.top = tk.Frame(self, bg=COLOR_BG)
        self.top.pack(fill="x")

        head = tk.Frame(self.top, bg=COLOR_BG)
        head.pack(fill="x")
        titles = tk.Frame(head, bg=COLOR_BG)
        titles.pack(side="left")
        tk.Label(titles, text="My Tasks", bg=COLOR_BG, fg=COLOR_TEXT,
                 font=fonts["heading"]).pack(anchor="w")
        self.subtitle = tk.Label(titles, text="", bg=COLOR_BG,
                                 fg=COLOR_MUTED, font=fonts["body"])
        self.subtitle.pack(anchor="w", pady=(2, 0))
        AddTaskButton(head, fonts, on_add_task).pack(side="right",
                                                     anchor="n")

        tabs_row = tk.Frame(self.top, bg=COLOR_BG)
        tabs_row.pack(fill="x", pady=(16, 10))
        self.tabs = {
            "all": FilterTab(tabs_row, fonts,
                             lambda: self.set_filter("all")),
            "pending": FilterTab(tabs_row, fonts,
                                 lambda: self.set_filter("pending")),
            # this one opens the Completed page instead of filtering
            "completed": FilterTab(tabs_row, fonts,
                                   lambda: self.on_view_completed()),
        }
        for tab in self.tabs.values():
            tab.pack(side="left", padx=(0, 8))

        # List / Calendar switch (right side of the tabs row)
        self.view_tabs = {
            "calendar": FilterTab(tabs_row, fonts,
                                  lambda: self.set_view("calendar")),
            "list": FilterTab(tabs_row, fonts,
                              lambda: self.set_view("list")),
        }
        for tab in self.view_tabs.values():
            tab.pack(side="right", padx=(8, 0))

        # ---- filter + sort bar ----
        self.filter_row = tk.Frame(self.top, bg=COLOR_BG)
        self.filter_row.pack(fill="x", pady=(0, 6))
        self.priority_box = self._combo("Priority", self.priority_var,
                                        PRIORITY_CHOICES, 9)
        self.category_box = self._combo("Category", self.category_var,
                                        [ALL], 12)
        self._combo("Due", self.due_var, DUE_CHOICES, 11)
        self._combo("Sort", self.sort_var, list(SORT_CHOICES), 18)
        clear = tk.Label(self.filter_row, text="Clear", bg=COLOR_BG,
                         fg=COLOR_PURPLE, font=fonts["small_bold"],
                         cursor="hand2")
        clear.pack(side="left", padx=(4, 0))
        clear.bind("<Button-1>", lambda e: self.clear_filters())

        # ---- the scrolling list ----
        self.scroll = ScrollFrame(self, bg=COLOR_BG,
                                  max_height=self._max_list_height)
        self.scroll.pack(fill="x")
        self.calendar = CalendarView(self, fonts, store)   # shown on demand
        self.bind("<Configure>", lambda e: self.scroll.refresh_layout())

        store.subscribe(self.refresh)
        self.refresh()

    # ---- public helpers (used by app.py) ---------------------------------
    def set_filter(self, name):
        self.filter = name
        self.refresh()

    def set_search(self, text):
        """Called by the top-bar search box."""
        self.search = text.strip()
        self.refresh()

    def reset(self):
        """Back to the 'All' view with no search (used on sign in)."""
        self.filter = "all"
        self.search = ""
        self.view = "list"
        self._reset_filter_vars()
        self.refresh()

    def set_view(self, name):
        """Switch between the task list and the calendar."""
        self.view = name
        self.refresh()

    def clear_filters(self):
        self._reset_filter_vars()
        self.refresh()

    def _reset_filter_vars(self):
        self.priority_var.set(ALL)
        self.category_var.set(ALL)
        self.due_var.set(DUE_CHOICES[0])
        self.sort_var.set(DEFAULT_SORT)

    def _filters_active(self):
        return (self.priority_var.get() != ALL
                or self.category_var.get() != ALL
                or self.due_var.get() != DUE_CHOICES[0])

    def _combo(self, label, variable, values, width):
        """A small 'Label  [choice v]' pair in the filter bar."""
        tk.Label(self.filter_row, text=label, bg=COLOR_BG, fg=COLOR_MUTED,
                 font=self.fonts["small"]).pack(side="left", padx=(0, 4))
        box = Dropdown(self.filter_row, self.fonts, variable, values,
                       self.refresh, width)
        box.pack(side="left", padx=(0, 12))
        return box

    # ---- sizing ---------------------------------------------------------
    def _max_list_height(self):
        return max(150, self.winfo_height() - self.top.winfo_height() - 10)

    # ---- content --------------------------------------------------------
    def _matches(self, task):
        query = self.search.lower()
        return (query in task.title.lower()
                or query in task.description.lower()
                or query in task.category.lower())

    def _passes_filters(self, task):
        if self.priority_var.get() not in (ALL, task.priority):
            return False
        if self.category_var.get() not in (ALL, task.category):
            return False
        due = self.due_var.get()
        days = days_until(task)
        if due == "Overdue":
            return days < 0 and not task.completed
        if due == "Today":
            return days == 0
        if due == "Next 7 days":
            return 0 <= days <= 7
        if due == "Later":
            return days > 7
        return True

    def _sorted(self, tasks):
        name = self.sort_var.get()
        return sorted(tasks, key=SORT_CHOICES[name],
                      reverse=name in SORT_REVERSED)

    def _update_category_choices(self):
        choices = [ALL] + self.store.categories()
        self.category_box.set_values(choices)
        if self.category_var.get() not in choices:
            self.category_var.set(ALL)

    def _apply_view(self):
        """Show either the list (with its filter bar) or the calendar."""
        if self.view != getattr(self, "_shown_view", None):
            self._shown_view = self.view
            if self.view == "calendar":
                self.filter_row.pack_forget()
                self.scroll.pack_forget()
                self.calendar.pack(fill="both", expand=True)
            else:
                self.calendar.pack_forget()
                self.filter_row.pack(fill="x", pady=(0, 6))
                self.scroll.pack(fill="x")
            self.after_idle(self.scroll.refresh_layout)
        self.view_tabs["list"].set("List", self.view == "list")
        self.view_tabs["calendar"].set("Calendar", self.view == "calendar")

    def refresh(self):
        store = self.store
        self._update_category_choices()
        self._apply_view()
        pending = self._sorted(store.pending_tasks())
        done = self._sorted(store.completed_tasks())
        if self.search:
            pending = [t for t in pending if self._matches(t)]
            done = [t for t in done if self._matches(t)]
        if self._filters_active():
            pending = [t for t in pending if self._passes_filters(t)]
            done = [t for t in done if self._passes_filters(t)]
        show_done = self.filter == "all"
        visible = len(pending) + (len(done) if show_done else 0)

        # heading text + tab labels
        if self.search:
            self.subtitle.config(
                text=f"{plural(visible, 'task')} match “{shorten(self.search, 30)}”"
                     f"  (of {store.total})")
        elif self._filters_active():
            self.subtitle.config(
                text=f"Showing {visible} of {plural(store.total, 'task')}.")
        else:
            self.subtitle.config(
                text=f"You have {plural(store.total, 'task')} in total.")
        self.tabs["all"].set(f"All ({store.total})", self.filter == "all")
        self.tabs["pending"].set(f"Pending ({store.pending_count})",
                                 self.filter == "pending")
        self.tabs["completed"].set(f"Completed ({store.completed_count})",
                                   False)

        # rebuild the list
        self.scroll.clear()
        body = self.scroll.body
        if visible == 0:
            self._build_empty(body)
        else:
            if pending:
                if self.sort_var.get() == DEFAULT_SORT:
                    # sorted by due date: split into Overdue / Today / Upcoming
                    overdue, due_today, upcoming = group_pending(pending)
                    sections = [("Overdue", overdue), ("Today", due_today),
                                ("Upcoming", upcoming)]
                else:
                    sections = [("Pending", pending)]
                for title, group in sections:
                    if not group:
                        continue
                    self._section_title(body, f"{title} ({len(group)})",
                                        OVERDUE_RED if title == "Overdue"
                                        else None)
                    for task in group:
                        self._build_row(body, task)
            if show_done and done:
                self._section_title(body, "Completed")
                for task in done:
                    self._build_row(body, task)
        self.scroll.refresh_layout()

    def _build_empty(self, body):
        if self.search:
            text = f"No tasks match “{shorten(self.search, 30)}”."
        elif self._filters_active() and self.store.total:
            text = "No tasks match these filters.\nClick “Clear” to reset them."
        elif self.store.total == 0:
            text = ("No tasks yet.\nClick “+ Add Task” to create your "
                    "first one.")
        else:
            text = "No pending tasks. 🎉\nYou're all caught up!"
        tk.Label(body, text=text, bg=COLOR_BG, fg=COLOR_MUTED,
                 font=self.fonts["body"], justify="center").pack(pady=50)

    def _section_title(self, body, text, color=None):
        tk.Label(body, text=text, bg=COLOR_BG, fg=color or COLOR_TEXT,
                 font=self.fonts["card_title"], anchor="w").pack(
            fill="x", pady=(8, 6))

    def _build_row(self, body, task):
        fonts = self.fonts
        card, inner = create_card(body, 100, 56, radius=12)
        card.pack(fill="x", pady=4)

        # ---- right side first, so long titles can never push it out ----
        delete_button(inner, fonts, lambda t=task: open_delete_dialog(
            self.winfo_toplevel(), fonts, self.store, t)).pack(
            side="right", padx=(2, 14))
        edit_button(inner, fonts, lambda t=task: open_edit_dialog(
            self.winfo_toplevel(), fonts, self.store, t)).pack(
            side="right", padx=2)
        create_priority_badge(inner, task.priority, fonts).pack(
            side="right", padx=(8, 10))
        if task.category:
            tk.Label(inner, text=shorten(task.category, 16), bg=CHIP_BG,
                     fg=CHIP_FG, font=fonts["small"], padx=6).pack(
                side="right")

        # ---- check circle ----
        self._build_check(inner, task).pack(side="left", padx=(16, 12))

        # ---- title + date ----
        text_col = tk.Frame(inner, bg=COLOR_WHITE)
        text_col.pack(side="left", fill="x", expand=True)
        if task.completed:
            title_font, title_color = fonts["body_strike"], "#5b6075"
        else:
            title_font, title_color = fonts["label"], COLOR_TEXT
        title_text = shorten(task.title, 44)
        if task.recurrence != "none":
            title_text += "  🔁"
        tk.Label(text_col, text=title_text, bg=COLOR_WHITE,
                 fg=title_color, font=title_font, anchor="w").pack(fill="x")
        date_text, date_color = due_label(task)
        sub = tk.Frame(text_col, bg=COLOR_WHITE)
        sub.pack(fill="x")
        tk.Label(sub, text=date_text, bg=COLOR_WHITE,
                 fg=date_color or COLOR_MUTED, font=fonts["small"],
                 anchor="w").pack(side="left")
        if task.description:
            tk.Label(sub, text=f"   ·   {shorten(task.description, 40)}",
                     bg=COLOR_WHITE, fg=COLOR_MUTED, font=fonts["small"],
                     anchor="w").pack(side="left")

    def _build_check(self, parent, task):
        circle = tk.Canvas(parent, width=22, height=22, bg=COLOR_WHITE,
                           highlightthickness=0, cursor="hand2")
        if task.completed:
            circle.create_oval(2, 2, 20, 20, fill=COLOR_GREEN,
                               outline=COLOR_GREEN)
            circle.create_text(11, 11, text="✓", fill="white",
                               font=self.fonts["check_mark"])
        else:
            ring = circle.create_oval(2, 2, 20, 20, outline="#c3c6d8",
                                      width=2, fill=COLOR_WHITE)
            circle.bind("<Enter>",
                        lambda e: circle.itemconfig(ring, outline=COLOR_PURPLE))
            circle.bind("<Leave>",
                        lambda e: circle.itemconfig(ring, outline="#c3c6d8"))
        circle.bind("<Button-1>",
                    lambda e, tid=task.id, done=task.completed:
                    self.store.set_completed(tid, not done))
        return circle