from dataclasses import dataclass, field
from datetime import date, datetime

from ui_common import shorten, format_date

SOON_DAYS = 3


@dataclass
class Notification:
    kind: str            # added | completed | reopened | today | soon
    title: str
    text: str
    time: datetime = field(default_factory=datetime.now)
    read: bool = False


def deadline_kind(task, today=None):
    """'today', 'soon' or None for a task."""
    if task.completed:
        return None
    days = (task.due - (today or date.today())).days
    if days == 0:
        return "today"
    if 1 <= days <= SOON_DAYS:
        return "soon"
    return None


class NotificationCenter:
    def __init__(self, store):
        self.store = store
        self.items = []
        self.deadline_alerts = True   # Settings > Email Notifications
        self._seen = set()          # deadline alerts already raised
        self._listeners = []
        store.subscribe_events(self._on_event)
        store.subscribe(self.check_deadlines)

    # ---- listening -----------------------------------------------------
    def subscribe(self, callback):
        self._listeners.append(callback)

    def _changed(self):
        for callback in list(self._listeners):
            callback()

    # ---- reading -------------------------------------------------------
    def new_items(self):
        """Unread notifications, newest first."""
        return [n for n in reversed(self.items) if not n.read]

    def has_unread(self):
        return any(not n.read for n in self.items)

    def mark_all_read(self):
        for n in self.items:
            n.read = True
        self._changed()

    def reset(self):
        """Start fresh (used when another account signs in)."""
        self.items.clear()
        self._seen.clear()
        self._changed()

    # ---- creating ------------------------------------------------------
    def _add(self, kind, title, text):
        self.items.append(Notification(kind, title, text))
        self._changed()

    def _on_event(self, kind, task):
        name = f"“{shorten(task.title, 30)}”"
        if kind == "added":
            self._add("added", "Task added",
                      f"{name} is due {format_date(task.due)}.")
            # don't also raise a due-soon alert for a task you just added
            alert = deadline_kind(task)
            if alert:
                self._seen.add((task.id, alert))
        elif kind == "completed":
            self._add("completed", "Task completed",
                      f"{name} is done. Great job!")
        elif kind == "reopened":
            self._add("reopened", "Task moved back",
                      f"{name} is pending again.")
        elif kind == "updated":
            self._add("updated", "Task updated",
                      f"{name} was updated. Due {format_date(task.due)}.")
            alert = deadline_kind(task)
            if alert:
                self._seen.add((task.id, alert))
        elif kind == "deleted":
            self._add("deleted", "Task deleted",
                      f"{name} was removed.")

    def check_deadlines(self):
        if not self.deadline_alerts:        # switched off in Settings
            return
        today = date.today()
        raised = False
        for task in self.store.tasks:
            kind = deadline_kind(task, today)
            if kind is None or (task.id, kind) in self._seen:
                continue
            self._seen.add((task.id, kind))
            name = f"“{shorten(task.title, 30)}”"
            if kind == "today":
                self.items.append(Notification(
                    "today", "Due today", f"{name} is due today."))
            else:
                days = (task.due - today).days
                self.items.append(Notification(
                    "soon", "Due soon",
                    f"{name} is due in {days} day{'s' if days != 1 else ''}."))
            raised = True
        if raised:
            self._changed()