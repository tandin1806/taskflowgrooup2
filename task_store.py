import itertools
from dataclasses import dataclass, replace
from datetime import date, datetime

from task_utils import next_due_date, is_overdue


@dataclass
class Task:
    id: int
    title: str
    description: str
    priority: str            # "High" | "Medium" | "Low"
    due: date
    completed: bool = False
    completed_at: datetime | None = None
    category: str = ""           # e.g. a course name: "RES402"
    recurrence: str = "none"     # "none" | "daily" | "weekly" | "monthly"


def default_tasks():
    """Tasks a brand-new account starts with: none. Every task you see in
    the app is one the student added themselves."""
    return []


class TaskStore:
    def __init__(self, starting_tasks=None, db=None):
        self.db = db                  # a database.Database (or None)
        self.user_id = None           # whose tasks are loaded right now
        self._starting = starting_tasks if starting_tasks is not None \
            else default_tasks()
        self._ids = itertools.count(1)
        self._listeners = []
        self._event_listeners = []
        self.tasks = []
        self.load_defaults(notify=False)

    # ---- listening for changes -----------------------------------------
    def subscribe(self, callback):
        """callback() is called every time something changes."""
        self._listeners.append(callback)

    def _notify(self):
        for callback in list(self._listeners):
            callback()

    def subscribe_events(self, callback):
        """callback(kind, task) - kind is 'added', 'completed', 'reopened',
        'updated' or 'deleted'.
        Used by the notification bell."""
        self._event_listeners.append(callback)

    def _emit(self, kind, task):
        for callback in list(self._event_listeners):
            callback(kind, task)

    # ---- switching accounts ---------------------------------------------
    def load_defaults(self, notify=True):
        """Replace everything with the starter tasks (nothing completed).
        Only used when there is no database."""
        self._ids = itertools.count(1)
        self.tasks = [Task(next(self._ids), t, d, p, due)
                      for t, d, p, due in self._starting]
        if notify:
            self._notify()

    def seed_defaults(self, user_id):
        """Gives a brand-new account its starting tasks (saved in the
        database). Called once, right after sign up. default_tasks() is
        empty, so new accounts simply start with no tasks."""
        for title, description, priority, due in self._starting:
            self.db.add_task(user_id, title, description, priority, due)

    def load_for_user(self, user_id):
        """Read this user's tasks from the database (called on sign in)."""
        self.user_id = user_id
        self.tasks = []
        for row in self.db.get_tasks(user_id):
            done = bool(row["is_completed"])
            stamp = row["completed_at"]
            self.tasks.append(Task(
                row["task_id"], row["title"], row["description"],
                row["priority"], date.fromisoformat(row["due_date"]),
                done,
                datetime.fromisoformat(stamp) if stamp
                else (datetime.now() if done else None),
                row["category"], row["recurrence"]))
        self._notify()

    def export(self):
        """A copy of this account's tasks."""
        return [replace(t) for t in self.tasks]

    def load(self, tasks):
        """Load a previously exported list of tasks (no database)."""
        self.tasks = [replace(t) for t in tasks]
        highest = max((t.id for t in self.tasks), default=0)
        self._ids = itertools.count(highest + 1)
        self._notify()

    # ---- changing tasks ------------------------------------------------
    def add_task(self, title, description, priority, due,
                 category="", recurrence="none"):
        category = (category or "").strip()
        recurrence = recurrence or "none"
        if self.db is not None and self.user_id is not None:
            task_id = self.db.add_task(self.user_id, title, description,
                                       priority, due, category, recurrence)
        else:
            task_id = next(self._ids)
        task = Task(task_id, title, description, priority, due,
                    category=category, recurrence=recurrence)
        self.tasks.append(task)
        self._emit("added", task)
        self._notify()
        return task

    def set_completed(self, task_id, value=True):
        for task in self.tasks:
            if task.id == task_id:
                if task.completed == value:
                    return                      # nothing changed
                task.completed = value
                task.completed_at = datetime.now() if value else None
                if self.db is not None and self.user_id is not None:
                    self.db.set_completed(task_id, value)
                self._emit("completed" if value else "reopened", task)
                # a repeating task creates its next occurrence when finished
                if value and task.recurrence != "none":
                    self._spawn_next(task)
                break
        self._notify()

    def _spawn_next(self, task):
        """Adds the next copy of a repeating task (same title, category and
        repeat rule, next due date). Marking it done again continues the
        chain."""
        nxt = next_due_date(task.due, task.recurrence)
        # don't create a duplicate if the next one already exists
        for other in self.tasks:
            if (not other.completed and other.title == task.title
                    and other.due == nxt and other.category == task.category):
                return
        self.add_task(task.title, task.description, task.priority, nxt,
                      task.category, task.recurrence)

    def update_task(self, task_id, title, description, priority, due,
                    category=None, recurrence=None):
        """Used by the Edit dialog on the My Tasks page. category and
        recurrence stay as they were when they are not passed in."""
        for task in self.tasks:
            if task.id == task_id:
                task.title = title
                task.description = description
                task.priority = priority
                task.due = due
                if category is not None:
                    task.category = category.strip()
                if recurrence is not None:
                    task.recurrence = recurrence
                if self.db is not None and self.user_id is not None:
                    self.db.update_task(task_id, title, description,
                                        priority, due, category, recurrence)
                self._emit("updated", task)
                break
        self._notify()

    def delete_task(self, task_id):
        """Used by the trash icon on the My Tasks page."""
        for task in self.tasks:
            if task.id == task_id:
                self.tasks.remove(task)
                if self.db is not None and self.user_id is not None:
                    self.db.delete_task(task_id)
                self._emit("deleted", task)
                break
        self._notify()

    # ---- reading tasks -------------------------------------------------
    def pending_tasks(self):
        """Pending tasks, soonest due date first."""
        return sorted((t for t in self.tasks if not t.completed),
                      key=lambda t: t.due)

    def completed_tasks(self):
        """Completed tasks, most recently completed first."""
        return sorted((t for t in self.tasks if t.completed),
                      key=lambda t: t.completed_at, reverse=True)

    def categories(self):
        """Every category in use, A-Z (for the filter and the dialogs)."""
        return sorted({t.category for t in self.tasks if t.category},
                      key=str.lower)

    @property
    def overdue_count(self):
        return sum(1 for t in self.tasks if is_overdue(t))

    @property
    def total(self):
        return len(self.tasks)

    @property
    def completed_count(self):
        return sum(1 for t in self.tasks if t.completed)

    @property
    def pending_count(self):
        return self.total - self.completed_count

    @property
    def due_today_count(self):
        today = date.today()
        return sum(1 for t in self.tasks
                   if not t.completed and t.due == today)

    @property
    def percent(self):
        if self.total == 0:
            return 0
        return round(100 * self.completed_count / self.total)