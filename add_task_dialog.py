import calendar
import tkinter as tk
from datetime import date, datetime

from ui_common import (
    COLOR_WHITE, COLOR_TEXT, COLOR_MUTED, COLOR_LINE, COLOR_PURPLE,
    COLOR_RED_TEXT, COLOR_FIELD_BG, COLOR_FIELD_LINE, PRIORITY_STYLES,
    RoundedBox, draw_rounded_rect,
)
from task_utils import RECURRENCE_CHOICES, RECURRENCE_LABELS

DATE_FORMAT = "%m/%d/%Y"


# =====================================================================
# Small widgets used only by this dialog
# =====================================================================
class RoundedButton(tk.Canvas):
    """A rounded button - used for 'Cancel' and 'Create Task'."""

    def __init__(self, parent, text, command, fonts, fill, text_color,
                 border, hover_fill, height=42, radius=12):
        super().__init__(parent, height=height, width=10, bg=COLOR_WHITE,
                         highlightthickness=0, cursor="hand2")
        self._text, self._command, self._fonts = text, command, fonts
        self._fill, self._hover = fill, hover_fill
        self._text_color, self._border = text_color, border
        self._radius, self._current = radius, fill
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>", lambda e: self._command())
        self.bind("<Enter>", lambda e: self._set(self._hover))
        self.bind("<Leave>", lambda e: self._set(self._fill))

    def _set(self, color):
        self._current = color
        self._draw()

    def _draw(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4:
            return
        self.delete("all")
        draw_rounded_rect(self, 1, 1, w - 1, h - 1, self._radius,
                          fill=self._current, outline=self._border)
        self.create_text(w / 2, h / 2, text=self._text,
                         fill=self._text_color, font=self._fonts["card_title"])


class PriorityOption(tk.Canvas):
    """One of the three stacked priority choices (radio + dot + label)."""

    def __init__(self, parent, label, variable, fonts):
        super().__init__(parent, height=34, width=10, bg=COLOR_WHITE,
                         highlightthickness=0, cursor="hand2")
        self.label, self.variable, self.fonts = label, variable, fonts
        self.style = PRIORITY_STYLES[label]
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<Button-1>", lambda e: variable.set(label))
        variable.trace_add("write", lambda *a: self.redraw())

    def redraw(self):
        if not self.winfo_exists():
            return
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4:
            return
        selected = self.variable.get() == self.label
        self.delete("all")
        fill = self.style["sel_bg"] if selected else COLOR_WHITE
        border = self.style["sel_border"] if selected else COLOR_FIELD_LINE
        draw_rounded_rect(self, 1, 1, w - 1, h - 1, 10, fill=fill,
                          outline=border)
        # radio circle
        cy = h / 2
        if selected:
            self.create_oval(14, cy - 7, 28, cy + 7, outline=COLOR_PURPLE,
                             width=2, fill=COLOR_WHITE)
            self.create_oval(18, cy - 3, 24, cy + 3, outline=COLOR_PURPLE,
                             fill=COLOR_PURPLE)
        else:
            self.create_oval(14, cy - 7, 28, cy + 7, outline="#9aa0b5",
                             width=1, fill=COLOR_WHITE)
        # colored dot + label
        self.create_oval(39, cy - 4, 47, cy + 4, fill=self.style["dot"],
                         outline=self.style["dot"])
        self.create_text(55, cy, text=self.label, anchor="w",
                         fill=self.style["text"],
                         font=self.fonts["small_bold"])


class CalendarPopup(tk.Toplevel):
    """Small month calendar that opens under the due-date field."""

    CELL = 32

    def __init__(self, anchor_box, fonts, initial, on_pick, on_close):
        super().__init__(anchor_box.winfo_toplevel())
        self.fonts, self.on_pick, self.on_close = fonts, on_pick, on_close
        self.selected = initial
        self.view_year, self.view_month = initial.year, initial.month
        self.overrideredirect(True)
        self.configure(bg=COLOR_FIELD_LINE)

        self.card = tk.Frame(self, bg=COLOR_WHITE)
        self.card.pack(padx=1, pady=1)

        # header: ‹  Month Year  ›
        head = tk.Frame(self.card, bg=COLOR_WHITE)
        head.pack(fill="x", padx=8, pady=(8, 4))
        prev = tk.Label(head, text="‹", bg=COLOR_WHITE, fg=COLOR_TEXT,
                        font=fonts["card_title"], cursor="hand2", width=3)
        prev.pack(side="left")
        prev.bind("<Button-1>", lambda e: self._shift(-1))
        nxt = tk.Label(head, text="›", bg=COLOR_WHITE, fg=COLOR_TEXT,
                       font=fonts["card_title"], cursor="hand2", width=3)
        nxt.pack(side="right")
        nxt.bind("<Button-1>", lambda e: self._shift(1))
        self.title_label = tk.Label(head, bg=COLOR_WHITE, fg=COLOR_TEXT,
                                    font=fonts["small_bold"])
        self.title_label.pack(side="left", expand=True)

        self.grid_frame = tk.Frame(self.card, bg=COLOR_WHITE)
        self.grid_frame.pack(padx=8)

        today = tk.Label(self.card, text="Today", bg=COLOR_WHITE,
                         fg=COLOR_PURPLE, font=fonts["small_bold"],
                         cursor="hand2")
        today.pack(pady=(4, 8))
        today.bind("<Button-1>", lambda e: self._pick(date.today()))

        self._render()
        self._position(anchor_box)

        # a click anywhere outside the popup closes it
        self.bind("<Button-1>", self._maybe_close_on_outside_click, add="+")
        self.bind("<Escape>", lambda e: self.close())
        self.update_idletasks()
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self.focus_set()

    def _position(self, anchor_box):
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = anchor_box.winfo_rootx() + anchor_box.winfo_width() - w
        y = anchor_box.winfo_rooty() + anchor_box.winfo_height() + 4
        if y + h > self.winfo_screenheight():
            y = anchor_box.winfo_rooty() - h - 4
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _shift(self, months):
        index = self.view_year * 12 + (self.view_month - 1) + months
        self.view_year, self.view_month = index // 12, index % 12 + 1
        self._render()

    def _render(self):
        for child in self.grid_frame.winfo_children():
            child.destroy()
        self.title_label.config(
            text=f"{calendar.month_name[self.view_month]} {self.view_year}")

        for col, name in enumerate(["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]):
            tk.Label(self.grid_frame, text=name, bg=COLOR_WHITE,
                     fg=COLOR_MUTED, font=self.fonts["small"],
                     width=3).grid(row=0, column=col, pady=(0, 2))

        weeks = calendar.Calendar(firstweekday=6).monthdatescalendar(
            self.view_year, self.view_month)
        today = date.today()
        for r, week in enumerate(weeks, start=1):
            for c, day in enumerate(week):
                in_month = day.month == self.view_month
                is_selected = day == self.selected
                bg = COLOR_PURPLE if is_selected else COLOR_WHITE
                fg = ("white" if is_selected
                      else COLOR_TEXT if in_month else "#c3c6d8")
                font = (self.fonts["small_bold"] if day == today
                        else self.fonts["small"])
                cell = tk.Label(self.grid_frame, text=str(day.day), bg=bg,
                                fg=fg, font=font, width=3, cursor="hand2")
                cell.grid(row=r, column=c, pady=1, ipady=3)
                cell.bind("<Button-1>", lambda e, d=day: self._pick(d))
                if not is_selected:
                    cell.bind("<Enter>", lambda e, w=cell:
                              w.config(bg=COLOR_FIELD_BG))
                    cell.bind("<Leave>", lambda e, w=cell:
                              w.config(bg=COLOR_WHITE))

    def _pick(self, day):
        self.on_pick(day)
        self.close()

    def _maybe_close_on_outside_click(self, event):
        x, y = event.x_root, event.y_root
        left, top = self.winfo_rootx(), self.winfo_rooty()
        inside = (left <= x < left + self.winfo_width()
                  and top <= y < top + self.winfo_height())
        if not inside:
            self.close()

    def close(self):
        if not self.winfo_exists():
            return
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
        self.on_close()


# =====================================================================
# The dialog itself
# =====================================================================
class AddTaskDialog(tk.Toplevel):
    WIDTH = 520

    def __init__(self, parent, fonts, on_create, categories=()):
        """on_create(title, description, priority, due_date, category,
        recurrence) is called when the user presses 'Create Task' and
        everything is valid. `categories` are the ones already in use (they
        are offered in the Category drop-down)."""
        super().__init__(parent, bg=COLOR_WHITE)
        self.parent_window = parent
        self.fonts = fonts
        self.on_create = on_create
        self.categories = list(categories)
        self.calendar = None

        self.title("Add New Task")
        self.resizable(False, False)
        self.transient(parent)

        self.priority_var = tk.StringVar(value="Medium")
        self.repeat_var = tk.StringVar(value="none")
        self.date_var = tk.StringVar()
        self._date_guard = False

        self._build()
        self._center()

        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda e: self.close())

        try:                      # make the dialog modal
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass
        self.title_entry.focus_set()

    # ------------------------------------------------------------------
    # layout
    # ------------------------------------------------------------------
    def _build(self):
        fonts = self.fonts

        # --- header: title + close X ---
        header = tk.Frame(self, bg=COLOR_WHITE)
        header.pack(fill="x", padx=26, pady=(22, 18))
        tk.Label(header, text="Add New Task", bg=COLOR_WHITE, fg=COLOR_TEXT,
                 font=fonts["dialog_title"]).pack(side="left")
        close = tk.Label(header, text="✕", bg=COLOR_WHITE, fg=COLOR_MUTED,
                         font=fonts["close"], cursor="hand2")
        close.pack(side="right")
        close.bind("<Button-1>", lambda e: self.close())
        close.bind("<Enter>", lambda e: close.config(fg=COLOR_TEXT))
        close.bind("<Leave>", lambda e: close.config(fg=COLOR_MUTED))
        tk.Frame(self, bg=COLOR_LINE, height=1).pack(fill="x")

        body = tk.Frame(self, bg=COLOR_WHITE)
        body.pack(fill="both", expand=True, padx=26, pady=(18, 22))
        body.columnconfigure((0, 1), weight=1, uniform="cols")

        # --- Task Title * ---
        self._field_label(body, "Task Title", required=True).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        self.title_box = RoundedBox(body, height=44)
        self.title_box.grid(row=1, column=0, columnspan=2, sticky="ew",
                            pady=(0, 16))
        self.title_entry = tk.Entry(
            self.title_box.inner, bd=0, relief="flat", font=fonts["body"],
            bg=COLOR_FIELD_BG, fg=COLOR_TEXT, insertbackground=COLOR_TEXT,
            highlightthickness=0)
        self.title_entry.pack(fill="x", expand=True, padx=12)
        self.title_box.attach(self.title_entry)
        self.title_entry.bind("<Return>", lambda e: self._submit())
        self.title_entry.bind("<Key>", lambda e: self._clear_error())
        self._placeholder(self.title_entry, "e.g. Submit assignment draft",
                          text_var=None)

        # --- Description (optional) ---
        self._field_label(body, "Description", optional=True).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(0, 6))
        self.desc_box = RoundedBox(body, height=82)
        self.desc_box.grid(row=3, column=0, columnspan=2, sticky="ew",
                           pady=(0, 16))
        self.desc_text = tk.Text(
            self.desc_box.inner, bd=0, relief="flat", font=fonts["body"],
            bg=COLOR_FIELD_BG, fg=COLOR_TEXT, insertbackground=COLOR_TEXT,
            highlightthickness=0, wrap="word", height=3, undo=True)
        self.desc_text.pack(fill="both", expand=True, padx=12, pady=6)
        self.desc_box.attach(self.desc_text)
        self._text_placeholder(self.desc_text, "Add details about this task...")

        # --- Priority (left column) ---
        tk.Label(body, text="Priority", bg=COLOR_WHITE, fg=COLOR_TEXT,
                 font=fonts["label"]).grid(row=4, column=0, sticky="w",
                                           pady=(0, 6))
        options = tk.Frame(body, bg=COLOR_WHITE)
        options.grid(row=5, column=0, sticky="new", padx=(0, 8))
        for label in ("High", "Medium", "Low"):
            PriorityOption(options, label, self.priority_var, fonts).pack(
                fill="x", pady=(0, 8))

        # --- Due Date * (right column) ---
        self._field_label(body, "Due Date", required=True).grid(
            row=4, column=1, sticky="w", pady=(0, 6), padx=(8, 0))
        right = tk.Frame(body, bg=COLOR_WHITE)
        right.grid(row=5, column=1, sticky="new", padx=(8, 0))
        self.date_box = RoundedBox(right, height=42)
        self.date_box.pack(fill="x")
        self._build_date_field()
        self._build_extra_fields(right)      # Category + Repeat

        # --- error message line (empty unless something is wrong) ---
        self.error_label = tk.Label(
            body, text="", bg=COLOR_WHITE, fg=COLOR_RED_TEXT,
            font=fonts["small"], anchor="w", justify="left", wraplength=460)
        self.error_label.grid(row=6, column=0, columnspan=2, sticky="ew",
                              pady=(6, 6))

        # --- buttons ---
        RoundedButton(
            body, "Cancel", self.close, fonts, fill=COLOR_WHITE,
            text_color="#4a4f66", border=COLOR_FIELD_LINE,
            hover_fill=COLOR_FIELD_BG).grid(
            row=7, column=0, sticky="ew", padx=(0, 8))
        RoundedButton(
            body, "Create Task", self._submit, fonts, fill=COLOR_PURPLE,
            text_color="white", border=COLOR_PURPLE,
            hover_fill="#5a4bd6").grid(
            row=7, column=1, sticky="ew", padx=(8, 0))

    # ------------------------------------------------------------------
    # Category (typed, or picked from the ones already used) + Repeat
    # ------------------------------------------------------------------
    def _build_extra_fields(self, parent):
        fonts = self.fonts

        self._field_label(parent, "Category", optional=True).pack(
            anchor="w", pady=(12, 6))
        self.category_box = RoundedBox(parent, height=42)
        self.category_box.pack(fill="x")
        inner = self.category_box.inner
        if self.categories:                  # small arrow = pick an old one
            arrow = tk.Label(inner, text="▾", bg=COLOR_FIELD_BG,
                             fg=COLOR_MUTED, font=fonts["body"],
                             cursor="hand2")
            arrow.pack(side="right", padx=(0, 12))
            arrow.bind("<Button-1>",
                       lambda e: self._show_category_menu(arrow))
        self.category_entry = tk.Entry(
            inner, bd=0, relief="flat", font=fonts["body"],
            bg=COLOR_FIELD_BG, fg=COLOR_TEXT, insertbackground=COLOR_TEXT,
            highlightthickness=0)
        self.category_entry.pack(side="left", fill="x", expand=True,
                                 padx=(12, 0))
        self.category_box.attach(self.category_entry)
        self.category_entry.bind("<Return>", lambda e: self._submit())
        self._placeholder(self.category_entry, "e.g. RES402", text_var=None)

        self._field_label(parent, "Repeat").pack(anchor="w", pady=(12, 6))
        self.repeat_box = RoundedBox(parent, height=42)
        self.repeat_box.pack(fill="x")
        self.repeat_button = tk.Menubutton(
            self.repeat_box.inner, font=fonts["body"], bg=COLOR_FIELD_BG,
            fg=COLOR_TEXT, activebackground=COLOR_FIELD_BG,
            activeforeground=COLOR_TEXT, relief="flat", bd=0,
            highlightthickness=0, anchor="w", cursor="hand2")
        self.repeat_button.pack(fill="both", expand=True, padx=12)
        menu = tk.Menu(self.repeat_button, tearoff=0, font=fonts["body"],
                       bg=COLOR_WHITE, fg=COLOR_TEXT,
                       activebackground=COLOR_PURPLE,
                       activeforeground="white", bd=0)
        for key in RECURRENCE_CHOICES:
            menu.add_command(label=RECURRENCE_LABELS[key],
                             command=lambda k=key: self.repeat_var.set(k))
        self.repeat_button["menu"] = menu
        self.repeat_var.trace_add("write", lambda *a: self._show_repeat())
        self._show_repeat()

    def _show_repeat(self):
        label = RECURRENCE_LABELS.get(self.repeat_var.get(),
                                      RECURRENCE_LABELS["none"])
        self.repeat_button.configure(text=f"{label}  ▾")

    def _show_category_menu(self, anchor):
        menu = tk.Menu(self, tearoff=0, font=self.fonts["body"],
                       bg=COLOR_WHITE, fg=COLOR_TEXT,
                       activebackground=COLOR_PURPLE,
                       activeforeground="white", bd=0)
        for name in self.categories:
            menu.add_command(label=name,
                             command=lambda n=name: self._set_category(n))
        try:
            menu.tk_popup(anchor.winfo_rootx(),
                          anchor.winfo_rooty() + anchor.winfo_height())
        finally:
            menu.grab_release()

    def _set_category(self, text):
        """Fill the Category box (and hide / show its grey hint)."""
        self.category_entry.delete(0, "end")
        self.category_entry.insert(0, text)
        for hint in self.category_entry.winfo_children():
            if text:
                hint.place_forget()
            else:
                hint.place(x=0, rely=0.5, anchor="w")

    def _field_label(self, parent, text, required=False, optional=False):
        frame = tk.Frame(parent, bg=COLOR_WHITE)
        tk.Label(frame, text=text, bg=COLOR_WHITE, fg=COLOR_TEXT,
                 font=self.fonts["label"]).pack(side="left")
        if required:
            tk.Label(frame, text=" *", bg=COLOR_WHITE, fg=COLOR_RED_TEXT,
                     font=self.fonts["label"]).pack(side="left")
        if optional:
            tk.Label(frame, text=" (optional)", bg=COLOR_WHITE,
                     fg=COLOR_MUTED, font=self.fonts["body"]).pack(
                side="left")
        return frame

    # ------------------------------------------------------------------
    # placeholders (grey hint text that disappears once you type)
    # ------------------------------------------------------------------
    def _placeholder(self, entry, hint, text_var):
        label = tk.Label(entry, text=hint, bg=COLOR_FIELD_BG, fg="#a3a8bb",
                         font=self.fonts["body"], cursor="xterm")
        label.place(x=0, rely=0.5, anchor="w")
        label.bind("<Button-1>", lambda e: entry.focus_set())

        def update(*_):
            if entry.get():
                label.place_forget()
            else:
                label.place(x=0, rely=0.5, anchor="w")

        entry.bind("<KeyRelease>", update, add="+")
        entry.bind("<<Paste>>", lambda e: entry.after(10, update), add="+")
        return update

    def _text_placeholder(self, text, hint):
        label = tk.Label(text, text=hint, bg=COLOR_FIELD_BG, fg="#a3a8bb",
                         font=self.fonts["body"], cursor="xterm")
        label.place(x=2, y=0, anchor="nw")
        label.bind("<Button-1>", lambda e: text.focus_set())

        def update(event=None):
            if text.get("1.0", "end-1c"):
                label.place_forget()
            else:
                label.place(x=2, y=0, anchor="nw")
            text.edit_modified(False)

        text.bind("<<Modified>>", update)

    # ------------------------------------------------------------------
    # due-date field: typing with auto "/" + calendar icon
    # ------------------------------------------------------------------
    def _build_date_field(self):
        fonts = self.fonts
        inner = self.date_box.inner

        icon = tk.Canvas(inner, width=22, height=22, bg=COLOR_FIELD_BG,
                         highlightthickness=0, cursor="hand2")
        icon.pack(side="right", padx=(0, 10))
        # tiny calendar drawing
        icon.create_rectangle(4, 6, 18, 18, outline=COLOR_TEXT, width=2)
        icon.create_line(4, 10, 18, 10, fill=COLOR_TEXT, width=2)
        icon.create_line(8, 3, 8, 7, fill=COLOR_TEXT, width=2)
        icon.create_line(14, 3, 14, 7, fill=COLOR_TEXT, width=2)
        icon.bind("<Button-1>", lambda e: self._toggle_calendar())

        self.date_entry = tk.Entry(
            inner, textvariable=self.date_var, bd=0, relief="flat",
            font=fonts["body"], bg=COLOR_FIELD_BG, fg=COLOR_TEXT,
            insertbackground=COLOR_TEXT, highlightthickness=0)
        self.date_entry.pack(side="left", fill="x", expand=True, padx=(12, 0))
        self.date_box.attach(self.date_entry)

        hint = tk.Label(self.date_entry, text="mm/dd/yyyy",
                        bg=COLOR_FIELD_BG, fg="#6b7090", font=fonts["body"],
                        cursor="xterm")
        hint.place(x=0, rely=0.5, anchor="w")
        hint.bind("<Button-1>", lambda e: self.date_entry.focus_set())

        def on_change(*_):
            if self._date_guard:
                return
            digits = "".join(c for c in self.date_var.get()
                             if c.isdigit())[:8]
            text = digits[:2]
            if len(digits) > 2:
                text += "/" + digits[2:4]
            if len(digits) > 4:
                text += "/" + digits[4:8]
            if text != self.date_var.get():
                self._date_guard = True
                self.date_var.set(text)
                self.date_entry.icursor("end")
                self._date_guard = False
            if text:
                hint.place_forget()
            else:
                hint.place(x=0, rely=0.5, anchor="w")
            self._clear_error()

        self.date_var.trace_add("write", on_change)
        self.date_entry.bind("<Return>", lambda e: self._submit())

    def _toggle_calendar(self):
        if self.calendar is not None and self.calendar.winfo_exists():
            self.calendar.close()
            return
        try:
            initial = datetime.strptime(self.date_var.get(),
                                        DATE_FORMAT).date()
        except ValueError:
            initial = date.today()
        self.calendar = CalendarPopup(
            self.date_box, self.fonts, initial,
            on_pick=lambda d: self.date_var.set(d.strftime(DATE_FORMAT)),
            on_close=self._calendar_closed)

    def _calendar_closed(self):
        self.calendar = None
        try:
            self.grab_set()           # give the dialog its modal grab back
        except tk.TclError:
            pass
        self.date_entry.focus_set()

    # ------------------------------------------------------------------
    # validation + submit
    # ------------------------------------------------------------------
    def _clear_error(self):
        self.error_label.config(text="")
        self.title_box.set_error(False)
        self.date_box.set_error(False)

    def _submit(self):
        title = self.title_entry.get().strip()
        description = self.desc_text.get("1.0", "end").strip()
        date_text = self.date_var.get().strip()

        if not title:
            self._show_error("Please enter a task title.", self.title_box,
                             self.title_entry)
            return
        if not date_text:
            self._show_error("Please choose a due date.", self.date_box,
                             self.date_entry)
            return
        try:
            due = datetime.strptime(date_text, DATE_FORMAT).date()
        except ValueError:
            self._show_error("That date isn't valid - use mm/dd/yyyy "
                             "(e.g. 09/30/2026).", self.date_box,
                             self.date_entry)
            return

        priority = self.priority_var.get()
        category = self.category_entry.get().strip()[:30]
        for known in self.categories:        # "res402" -> existing "RES402"
            if known.lower() == category.lower():
                category = known
                break
        recurrence = self.repeat_var.get()
        self.close()
        self.on_create(title, description, priority, due, category,
                       recurrence)

    def _show_error(self, message, box, widget):
        self._clear_error()
        self.error_label.config(text=message)
        box.set_error(True)
        widget.focus_set()

    # ------------------------------------------------------------------
    # window helpers
    # ------------------------------------------------------------------
    def _center(self):
        self.update_idletasks()
        height = self.winfo_reqheight()
        parent = self.parent_window
        x = parent.winfo_rootx() + (parent.winfo_width() - self.WIDTH) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        self.geometry(f"{self.WIDTH}x{height}+{max(x, 0)}+{max(y, 0)}")

    def close(self):
        if self.calendar is not None and self.calendar.winfo_exists():
            self.calendar.destroy()
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()