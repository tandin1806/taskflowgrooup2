import tkinter as tk

from ui_common import (
    COLOR_WHITE, COLOR_TEXT, COLOR_MUTED, COLOR_LINE, COLOR_RED_TEXT,
    COLOR_PURPLE, COLOR_FIELD_BG, COLOR_FIELD_LINE, shorten,
)
from add_task_dialog import AddTaskDialog, RoundedButton, DATE_FORMAT


def _walk(widget):
    yield widget
    for child in widget.winfo_children():
        yield from _walk(child)


# =====================================================================
# Edit task
# =====================================================================
class EditTaskDialog(AddTaskDialog):
    def __init__(self, parent, fonts, task, on_save, categories=()):
        """on_save(title, description, priority, due_date, category,
        recurrence) is called when the user presses 'Save Changes' and
        everything is valid."""
        super().__init__(parent, fonts, on_create=on_save,
                         categories=categories)

        self.title("Edit Task")
        self.update_idletasks()

        # re-label the header and the main button
        for widget in _walk(self):
            if isinstance(widget, tk.Label) and \
                    widget.cget("text") == "Add New Task":
                widget.config(text="Edit Task")
            elif isinstance(widget, RoundedButton) and \
                    widget._text == "Create Task":
                widget._text = "Save Changes"
                widget._draw()

        # fill in the current values
        self.title_entry.insert(0, task.title)
        for hint in self.title_entry.winfo_children():   # grey placeholder
            hint.place_forget()
        if task.description:
            self.desc_text.insert("1.0", task.description)
            for hint in self.desc_text.winfo_children():
                hint.place_forget()
        self.priority_var.set(task.priority)
        self._set_category(task.category)
        self.repeat_var.set(task.recurrence)
        self.date_var.set(task.due.strftime(DATE_FORMAT))
        self.title_entry.focus_set()
        self.title_entry.icursor("end")


# =====================================================================
# Confirm (used for delete)
# =====================================================================
class ConfirmDialog(tk.Toplevel):
    WIDTH = 400

    def __init__(self, parent, fonts, title, message, confirm_text,
                 on_confirm):
        super().__init__(parent, bg=COLOR_WHITE)
        self.parent_window = parent
        self.fonts = fonts
        self.on_confirm = on_confirm

        self.title(title)
        self.resizable(False, False)
        self.transient(parent)

        # header: title + close X
        header = tk.Frame(self, bg=COLOR_WHITE)
        header.pack(fill="x", padx=26, pady=(22, 18))
        tk.Label(header, text=title, bg=COLOR_WHITE, fg=COLOR_TEXT,
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

        tk.Label(body, text=message, bg=COLOR_WHITE, fg=COLOR_TEXT,
                 font=fonts["body"], justify="left", anchor="w",
                 wraplength=self.WIDTH - 52).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 20))

        RoundedButton(
            body, "Cancel", self.close, fonts, fill=COLOR_WHITE,
            text_color="#4a4f66", border=COLOR_FIELD_LINE,
            hover_fill=COLOR_FIELD_BG).grid(
            row=1, column=0, sticky="ew", padx=(0, 8))
        RoundedButton(
            body, confirm_text, self._confirm, fonts, fill=COLOR_RED_TEXT,
            text_color="white", border=COLOR_RED_TEXT,
            hover_fill="#cf4630").grid(
            row=1, column=1, sticky="ew", padx=(8, 0))

        self._center()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda e: self.close())
        try:                      # modal, like the Add Task dialog
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass
        self.focus_set()

    def _center(self):
        self.update_idletasks()
        height = self.winfo_reqheight()
        parent = self.parent_window
        x = parent.winfo_rootx() + (parent.winfo_width() - self.WIDTH) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        self.geometry(f"{self.WIDTH}x{height}+{max(x, 0)}+{max(y, 0)}")

    def _confirm(self):
        self.close()
        self.on_confirm()

    def close(self):
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()


# =====================================================================
# Shared by the My Tasks and Completed pages
# =====================================================================
def _icon_button(parent, fonts, glyph, hover_color, command):
    label = tk.Label(parent, text=glyph, bg=COLOR_WHITE, fg="#4a4f66",
                     font=fonts["body"], cursor="hand2", padx=4)
    label.bind("<Enter>", lambda e: label.config(fg=hover_color))
    label.bind("<Leave>", lambda e: label.config(fg="#4a4f66"))
    label.bind("<Button-1>", lambda e: command())
    return label


def edit_button(parent, fonts, command):
    """The pencil icon of a task row."""
    return _icon_button(parent, fonts, "\u270e", COLOR_PURPLE, command)


def delete_button(parent, fonts, command):
    """The trash icon of a task row."""
    return _icon_button(parent, fonts, "\U0001F5D1", COLOR_RED_TEXT, command)


def open_edit_dialog(window, fonts, store, task):
    """Edit Task pop-up for `task`; saves into the store."""
    task_id = task.id
    EditTaskDialog(
        window, fonts, task,
        on_save=lambda title, description, priority, due, category,
        recurrence: store.update_task(task_id, title, description,
                                      priority, due, category, recurrence),
        categories=store.categories())


def open_delete_dialog(window, fonts, store, task):
    """'Delete this task?' pop-up; removes the task from the store."""
    task_id = task.id
    ConfirmDialog(
        window, fonts, "Delete Task",
        f"Delete \u201c{shorten(task.title, 40)}\u201d?\n"
        "This can't be undone.",
        "Delete", lambda: store.delete_task(task_id))