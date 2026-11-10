import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import date, datetime

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "taskflow.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    university    TEXT    NOT NULL DEFAULT '',
    program       TEXT    NOT NULL DEFAULT '',
    password_changed_at TEXT
);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id             INTEGER PRIMARY KEY,
    push_notifications  INTEGER NOT NULL DEFAULT 0,
    theme               TEXT    NOT NULL DEFAULT 'light'
                        CHECK (theme IN ('light', 'dark')),
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    title        TEXT    NOT NULL,
    description  TEXT    NOT NULL DEFAULT '',
    priority     TEXT    NOT NULL
                 CHECK (priority IN ('High', 'Medium', 'Low')),
    due_date     TEXT    NOT NULL,              -- ISO date: YYYY-MM-DD
    is_completed INTEGER NOT NULL DEFAULT 0,    -- 0 = pending, 1 = done
    created_at   TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    category     TEXT    NOT NULL DEFAULT '',
    recurrence   TEXT    NOT NULL DEFAULT 'none'
                 CHECK (recurrence IN ('none', 'daily', 'weekly', 'monthly')),
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks (user_id);
"""


# ---------------------------------------------------------------------
# password helpers (salted PBKDF2, no extra install needed)
# ---------------------------------------------------------------------
def _hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 bytes.fromhex(salt), 100_000).hex()
    return f"{salt}${digest}"


def _password_matches(password, stored):
    salt = stored.split("$", 1)[0]
    return hmac.compare_digest(_hash_password(password, salt), stored)


# ---------------------------------------------------------------------
# the database
# ---------------------------------------------------------------------
class Database:
    def __init__(self, path=DB_FILE):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")   # enforce the FKs
        self.conn.executescript(SCHEMA)
        self._migrate()

    def _migrate(self):
        """Adds the profile columns to a taskflow.db created by an older
        version, so existing accounts and tasks are kept."""
        have = {r["name"] for r in
                self.conn.execute("PRAGMA table_info(users)")}
        wanted = {
            "university": "TEXT NOT NULL DEFAULT ''",
            "program": "TEXT NOT NULL DEFAULT ''",
            "password_changed_at": "TEXT",
            "recovery_hash": "TEXT",          # for "Forgot password?"
            "twofa_enabled": "INTEGER NOT NULL DEFAULT 0",   # emailed sign-in code
        }
        with self.conn:
            for column, definition in wanted.items():
                if column not in have:
                    self.conn.execute(
                        f"ALTER TABLE users ADD COLUMN {column} {definition}")

        # Remove retired 2FA/authenticator-secret columns from existing databases.
        # These columns are no longer part of TaskFlow; other account data is preserved.
        for column in ("two_factor_secret", "two_factor"):
            if column in have:
                with self.conn:
                    self.conn.execute(f"ALTER TABLE users DROP COLUMN {column}")
                have.remove(column)

        # Remove the retired email_notifications setting from existing databases.
        # SQLite 3.35+ supports DROP COLUMN; this preserves the remaining rows.
        have_settings = {r["name"] for r in
                         self.conn.execute("PRAGMA table_info(user_settings)")}
        if "email_notifications" in have_settings:
            with self.conn:
                self.conn.execute(
                    "ALTER TABLE user_settings DROP COLUMN email_notifications"
                )

        # task columns added for categories and recurring tasks
        have_tasks = {r["name"] for r in
                      self.conn.execute("PRAGMA table_info(tasks)")}
        wanted_tasks = {
            "category": "TEXT NOT NULL DEFAULT ''",
            "recurrence": "TEXT NOT NULL DEFAULT 'none'",
        }
        with self.conn:
            for column, definition in wanted_tasks.items():
                if column not in have_tasks:
                    self.conn.execute(
                        f"ALTER TABLE tasks ADD COLUMN {column} {definition}")

    def close(self):
        self.conn.close()

    # ---- accounts ----------------------------------------------------
    def create_user(self, name, email, password):
        """Returns the new user_id. Raises ValueError if the email is
        already registered."""
        try:
            with self.conn:
                cur = self.conn.execute(
                    "INSERT INTO users (full_name, email, password_hash) "
                    "VALUES (?, ?, ?)",
                    (name.strip(), email.strip(),
                     _hash_password(password)))
                user_id = cur.lastrowid
                self.conn.execute(
                    "INSERT INTO user_settings (user_id) VALUES (?)",
                    (user_id,))
        except sqlite3.IntegrityError:
            raise ValueError("That email is already registered.")
        return user_id

    def email_exists(self, email):
        row = self.conn.execute("SELECT 1 FROM users WHERE email = ?",
                                (email.strip(),)).fetchone()
        return row is not None

    def check_login(self, email, password):
        """Returns the user row if the login is right, otherwise None."""
        row = self.conn.execute("SELECT * FROM users WHERE email = ?",
                                (email.strip(),)).fetchone()
        if row and _password_matches(password, row["password_hash"]):
            return row
        return None

    # ---- profile (Profile page) ---------------------------------------
    def get_profile(self, user_id):
        """Everything the Profile page shows, in the dict shape it uses."""
        row = self.conn.execute("SELECT * FROM users WHERE user_id = ?",
                                (user_id,)).fetchone()
        try:
            since = datetime.strptime(row["created_at"],
                                      "%Y-%m-%d %H:%M:%S").strftime("%B %Y")
        except ValueError:
            since = row["created_at"]
        changed = row["password_changed_at"]
        if changed:
            changed = datetime.fromisoformat(changed).strftime("%b %d, %Y")
        return {"name": row["full_name"], "email": row["email"],
                "university": row["university"], "program": row["program"],
                "member_since": since,
                "password_changed": changed or "Never"}

    def update_profile(self, user_id, name, email, university, program):
        """Raises ValueError if the email belongs to another account."""
        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE users SET full_name = ?, email = ?, "
                    "university = ?, program = ? WHERE user_id = ?",
                    (name.strip(), email.strip(),
                     university.strip(), program.strip(), user_id))
        except sqlite3.IntegrityError:
            raise ValueError("That email is already registered.")

    def change_password(self, user_id, current, new):
        """True if changed, False if `current` is wrong."""
        row = self.conn.execute(
            "SELECT password_hash FROM users WHERE user_id = ?",
            (user_id,)).fetchone()
        if not row or not _password_matches(current, row["password_hash"]):
            return False
        with self.conn:
            self.conn.execute(
                "UPDATE users SET password_hash = ?, "
                "password_changed_at = ? WHERE user_id = ?",
                (_hash_password(new),
                 datetime.now().isoformat(timespec="seconds"), user_id))
        return True

    def delete_account(self, user_id, password):
        row = self.conn.execute(
            "SELECT password_hash FROM users WHERE user_id = ?",
            (user_id,)).fetchone()
        if not row or not _password_matches(password, row["password_hash"]):
            return False
        self.conn.execute("PRAGMA secure_delete = ON")
        with self.conn:
            self.conn.execute("DELETE FROM tasks WHERE user_id = ?",
                              (user_id,))
            self.conn.execute("DELETE FROM user_settings WHERE user_id = ?",
                              (user_id,))
            self.conn.execute("DELETE FROM users WHERE user_id = ?",
                              (user_id,))
        self.conn.execute("VACUUM")
        return True

    # ---- two-factor authentication (emailed code) -----------------------
    def is_2fa_enabled(self, user_id):
        row = self.conn.execute(
            "SELECT twofa_enabled FROM users WHERE user_id = ?",
            (user_id,)).fetchone()
        return bool(row and row["twofa_enabled"])

    def set_2fa_enabled(self, user_id, enabled):
        with self.conn:
            self.conn.execute(
                "UPDATE users SET twofa_enabled = ? WHERE user_id = ?",
                (1 if enabled else 0, user_id))

    # ---- forgot password (recovery key) --------------------------------
    def ensure_recovery_key(self, user_id):
        """Gives the account a recovery key if it has none and returns it
        (the app shows it to the user once). Returns None if the account
        already has one. Only a salted hash is stored."""
        row = self.conn.execute(
            "SELECT recovery_hash FROM users WHERE user_id = ?",
            (user_id,)).fetchone()
        if not row or row["recovery_hash"]:
            return None
        key = "-".join(secrets.token_hex(2).upper() for _ in range(4))
        with self.conn:
            self.conn.execute(
                "UPDATE users SET recovery_hash = ? WHERE user_id = ?",
                (_hash_password(key), user_id))
        return key

    def reset_password_with_key(self, email, key, new_password):
        """True if email + recovery key are right and the password was
        changed. The key is then used up (a new one is made at the next
        sign-in)."""
        row = self.conn.execute(
            "SELECT user_id, recovery_hash FROM users WHERE email = ?",
            (email.strip(),)).fetchone()
        typed = key.strip().upper()
        if (not row or not row["recovery_hash"]
                or not _password_matches(typed, row["recovery_hash"])):
            return False
        with self.conn:
            self.conn.execute(
                "UPDATE users SET password_hash = ?, password_changed_at = ?, "
                "recovery_hash = NULL WHERE user_id = ?",
                (_hash_password(new_password),
                 datetime.now().isoformat(timespec="seconds"),
                 row["user_id"]))
        return True

    def task_counts(self, user_id):
        """{'total','pending','done'} for the Profile summary card."""
        row = self.conn.execute(
            "SELECT COUNT(*) AS total, "
            "COALESCE(SUM(is_completed), 0) AS done "
            "FROM tasks WHERE user_id = ?", (user_id,)).fetchone()
        return {"total": row["total"], "pending": row["total"] - row["done"],
                "done": row["done"]}

    def get_public_stats(self):
        """Real numbers for the landing page: how many students have an
        account, how many tasks they finished and the overall completion
        rate (whole number)."""
        students = self.conn.execute(
            "SELECT COUNT(*) FROM users").fetchone()[0]
        row = self.conn.execute(
            "SELECT COUNT(*) AS total, "
            "COALESCE(SUM(is_completed), 0) AS done FROM tasks").fetchone()
        total, done = row["total"], row["done"]
        rate = 0
        if total:
            rate = round(done / total * 100)
            if done < total:                 # never show 100% / 0% early
                rate = min(rate, 99)
            if done > 0:
                rate = max(rate, 1)
        return {"students": students, "tasks_total": total,
                "tasks_done": done, "rate": rate}

    # ---- settings ----------------------------------------------------
    def get_settings(self, user_id):
        """Same dict shape the Settings page already uses."""
        row = self.conn.execute(
            "SELECT * FROM user_settings WHERE user_id = ?",
            (user_id,)).fetchone()
        return {"push_notifications": bool(row["push_notifications"]),
                "theme": row["theme"]}

    def save_settings(self, user_id, settings):
        with self.conn:
            self.conn.execute(
                "UPDATE user_settings SET push_notifications = ?, "
                "theme = ? WHERE user_id = ?",
                (int(settings["push_notifications"]),
                 settings["theme"], user_id))

    # ---- tasks -------------------------------------------------------
    def get_tasks(self, user_id):
        return self.conn.execute(
            "SELECT * FROM tasks WHERE user_id = ? ORDER BY due_date, task_id",
            (user_id,)).fetchall()

    def add_task(self, user_id, title, description, priority, due,
                 category="", recurrence="none"):
        """`due` is a datetime.date. Returns the new task_id."""
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO tasks (user_id, title, description, priority, "
                "due_date, category, recurrence) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, title.strip(), description.strip(),
                 priority.strip().capitalize(), due.isoformat(),
                 (category or "").strip(), recurrence or "none"))
        return cur.lastrowid

    def update_task(self, task_id, title, description, priority, due,
                    category=None, recurrence=None):
        """category / recurrence left as None keep what is already saved."""
        with self.conn:
            self.conn.execute(
                "UPDATE tasks SET title = ?, description = ?, priority = ?, "
                "due_date = ? WHERE task_id = ?",
                (title.strip(), description.strip(),
                 priority.strip().capitalize(), due.isoformat(), task_id))
            if category is not None:
                self.conn.execute(
                    "UPDATE tasks SET category = ? WHERE task_id = ?",
                    (category.strip(), task_id))
            if recurrence is not None:
                self.conn.execute(
                    "UPDATE tasks SET recurrence = ? WHERE task_id = ?",
                    (recurrence, task_id))

    def set_completed(self, task_id, completed):
        with self.conn:
            self.conn.execute(
                "UPDATE tasks SET is_completed = ?, completed_at = ? "
                "WHERE task_id = ?",
                (int(completed),
                 datetime.now().isoformat(timespec="seconds") if completed
                 else None, task_id))

    def delete_task(self, task_id):
        with self.conn:
            self.conn.execute("DELETE FROM tasks WHERE task_id = ?",
                              (task_id,))


# ---------------------------------------------------------------------
# quick self-test:  python database.py
# ---------------------------------------------------------------------
if __name__ == "__main__":
    db = Database(":memory:")
    uid = db.create_user("Tandin Wangchuk", "Tandin@example.com", "secret123")
    assert db.check_login("tandin@example.com", "secret123") is not None
    assert db.check_login("tandin@example.com", "wrong") is None
    try:
        db.create_user("Dup", "tandin@example.com", "x")
    except ValueError:
        print("duplicate email rejected")

    tid = db.add_task(uid, "Finish report", "Chapter 3", "high",
                      date(2026, 10, 20))
    db.set_completed(tid, True)
    db.update_task(tid, "Finish report v2", "", "Low", date(2026, 10, 21))
    print([dict(t) for t in db.get_tasks(uid)])
    db.save_settings(uid, {"push_notifications": True, "theme": "dark"})
    print(db.get_settings(uid))
    print(db.task_counts(uid))
    print(db.get_public_stats())
    db.update_profile(uid, "Tandin W", "tandin@example.com",
                      "Samste College of Education", "BA/B.Ed English & ICT")
    assert db.change_password(uid, "secret123", "newsecret99")
    assert not db.change_password(uid, "secret123", "again")
    assert db.check_login("tandin@example.com", "newsecret99") is not None
    print(db.get_profile(uid))
    db.delete_task(tid)
    assert db.get_tasks(uid) == []

    # delete the whole account: wrong password keeps it, right one erases it
    db.add_task(uid, "Another task", "", "Low", date(2026, 10, 25))
    assert not db.delete_account(uid, "wrong-password")
    assert db.email_exists("tandin@example.com")
    assert db.delete_account(uid, "newsecret99")
    assert not db.email_exists("tandin@example.com")
    assert db.get_tasks(uid) == []
    assert db.conn.execute("SELECT COUNT(*) FROM user_settings").fetchone()[0] == 0
    print("account deletion works")
    print("all database tests passed")