import calendar
import csv
from datetime import date, timedelta

from ui_common import format_date

OVERDUE_RED = "#ef4444"
TODAY_AMBER = "#d97706"
CHIP_BG = "#eef0ff"
CHIP_FG = "#6c5ce7"

PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}
RECURRENCE_CHOICES = ("none", "daily", "weekly", "monthly")
RECURRENCE_LABELS = {"none": "Does not repeat", "daily": "Every day",
                     "weekly": "Every week", "monthly": "Every month"}


# ---------------------------------------------------------------------
# where a task sits in time
# ---------------------------------------------------------------------
def days_until(task, today=None):
    """Negative = overdue, 0 = today, positive = days left."""
    return (task.due - (today or date.today())).days


def is_overdue(task, today=None):
    return (not task.completed) and days_until(task, today) < 0


def is_due_today(task, today=None):
    return (not task.completed) and days_until(task, today) == 0


def group_pending(tasks, today=None):
    """Splits pending tasks into (overdue, today, upcoming) lists."""
    overdue, due_today, upcoming = [], [], []
    for task in tasks:
        days = days_until(task, today)
        if days < 0:
            overdue.append(task)
        elif days == 0:
            due_today.append(task)
        else:
            upcoming.append(task)
    return overdue, due_today, upcoming


def due_label(task, today=None):
    """(text, colour) for the due-date label. Colour is None when the
    normal muted colour should be used."""
    if task.completed:
        return format_date(task.due), None
    days = days_until(task, today)
    if days < 0:
        n = -days
        return f"{n} day{'' if n == 1 else 's'} overdue", OVERDUE_RED
    if days == 0:
        return "Due today", TODAY_AMBER
    if days == 1:
        return "Due tomorrow", None
    return format_date(task.due), None


# ---------------------------------------------------------------------
# recurring tasks
# ---------------------------------------------------------------------
def _step(due, recurrence):
    if recurrence == "daily":
        return due + timedelta(days=1)
    if recurrence == "weekly":
        return due + timedelta(days=7)
    if recurrence == "monthly":
        year = due.year + (due.month // 12)
        month = due.month % 12 + 1
        day = min(due.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)
    return due


def next_due_date(due, recurrence, today=None):
    """The date of the next occurrence. If the task was finished late, the
    next one skips forward so it is never created already overdue."""
    today = today or date.today()
    nxt = _step(due, recurrence)
    while nxt < today:
        nxt = _step(nxt, recurrence)
    return nxt


# ---------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------
def export_csv(path, tasks):
    """Writes the tasks to `path`. utf-8-sig so Excel shows every
    character correctly."""
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Title", "Description", "Category", "Priority",
                         "Due Date", "Status", "Repeats", "Completed On"])
        for t in sorted(tasks, key=lambda t: (t.completed, t.due)):
            writer.writerow([
                t.title, t.description, t.category, t.priority,
                t.due.isoformat(),
                "Completed" if t.completed else
                ("Overdue" if is_overdue(t) else "Pending"),
                RECURRENCE_LABELS.get(t.recurrence, "Does not repeat"),
                t.completed_at.strftime("%Y-%m-%d %H:%M")
                if t.completed and t.completed_at else ""])
    return len(tasks)
