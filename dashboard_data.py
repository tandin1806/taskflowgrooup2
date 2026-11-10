import calendar
import math
from datetime import date, timedelta

RANGES = ["This week", "This month", "Last 30 days", "All time"]
ALL_CATEGORIES = "All categories"
ALL_PRIORITIES = "All priorities"
PRIORITIES = ("High", "Medium", "Low")
NO_CATEGORY = "No category"


# ---------------------------------------------------------------------
# filters
# ---------------------------------------------------------------------
def range_bounds(name, today):
    """(first_day, last_day) of the chosen range, or None for All time."""
    if name == "This week":
        start = today - timedelta(days=today.weekday())      # Monday
        return start, start + timedelta(days=6)
    if name == "This month":
        last = calendar.monthrange(today.year, today.month)[1]
        return today.replace(day=1), today.replace(day=last)
    if name == "Last 30 days":
        return today - timedelta(days=29), today
    return None


def _completed_day(task):
    return task.completed_at.date() if task.completed and task.completed_at \
        else None


def filter_tasks(tasks, range_name=RANGES[-1], category=ALL_CATEGORIES,
                 priority=ALL_PRIORITIES, today=None):
    today = today or date.today()
    bounds = range_bounds(range_name, today)
    kept = []
    for task in tasks:
        if category != ALL_CATEGORIES and \
                (task.category or NO_CATEGORY) != category:
            continue
        if priority != ALL_PRIORITIES and task.priority != priority:
            continue
        if bounds:
            start, end = bounds
            done_day = _completed_day(task)
            in_range = (start <= task.due <= end
                        or (done_day is not None and start <= done_day <= end)
                        or (not task.completed and task.due < today))
            if not in_range:
                continue
        kept.append(task)
    return kept


# ---------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------
def kpis(tasks, today=None):
    today = today or date.today()
    total = len(tasks)
    done = sum(1 for t in tasks if t.completed)
    pending = total - done
    due_today = sum(1 for t in tasks if not t.completed and t.due == today)
    overdue = sum(1 for t in tasks if not t.completed and t.due < today)
    rate = round(100 * done / total) if total else 0
    return {"total": total, "done": done, "pending": pending,
            "today": due_today, "overdue": overdue, "rate": rate,
            "open_not_late": pending - overdue}


# ---------------------------------------------------------------------
# charts
# ---------------------------------------------------------------------
def trend_days(range_name, today):
    """The days shown on the 'Due vs completed' line chart."""
    bounds = range_bounds(range_name, today)
    if range_name in ("This week", "This month") and bounds:
        start, end = bounds
    else:                                   # Last 30 days / All time
        end = today
        start = today - timedelta(days=29)
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def trend(tasks, range_name, today=None):
    """(days, due_per_day, completed_per_day)."""
    today = today or date.today()
    days = trend_days(range_name, today)
    index = {d: i for i, d in enumerate(days)}
    due = [0] * len(days)
    done = [0] * len(days)
    for task in tasks:
        if task.due in index:
            due[index[task.due]] += 1
        day = _completed_day(task)
        if day in index:
            done[index[day]] += 1
    return days, due, done


def by_priority(tasks):
    """[(label, completed, open)] for High / Medium / Low."""
    rows = []
    for name in PRIORITIES:
        group = [t for t in tasks if t.priority == name]
        finished = sum(1 for t in group if t.completed)
        rows.append((name, finished, len(group) - finished))
    return rows


def by_category(tasks, limit=6):
    """[(label, completed, open)], biggest categories first."""
    groups = {}
    for task in tasks:
        groups.setdefault(task.category or NO_CATEGORY, []).append(task)
    rows = []
    for name, group in groups.items():
        finished = sum(1 for t in group if t.completed)
        rows.append((name, finished, len(group) - finished))
    rows.sort(key=lambda r: (-(r[1] + r[2]), r[0].lower()))
    return rows[:limit]


def nice_axis(highest):
    """(step, top) for a y axis with 4 gridlines."""
    if highest <= 4:
        return 1, 4
    step = math.ceil(highest / 4)
    return step, step * 4


# ---------------------------------------------------------------------
# tables
# ---------------------------------------------------------------------
def pending_table(tasks, limit=8):
    order = {"High": 0, "Medium": 1, "Low": 2}
    rows = sorted((t for t in tasks if not t.completed),
                  key=lambda t: (t.due, order.get(t.priority, 3)))
    return rows[:limit]


def recent_table(tasks, limit=6):
    rows = [t for t in tasks if t.completed and t.completed_at]
    rows.sort(key=lambda t: t.completed_at, reverse=True)
    return rows[:limit]
