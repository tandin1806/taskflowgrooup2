import os
import socket
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta
from xml.sax.saxutils import escape as xml_escape

from database import DB_FILE

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(HERE, "taskflow_reminders.log")

CHECK_EVERY = 5 * 60            # seconds between checks in --loop mode
REMIND_AFTER_HOUR = 8           # no reminders before 08:00 local time
CONTROL_PORT = 48653            # localhost only: single instance + stop/ping
APP_NAME = "TaskFlow"

KIND_ORDER = ["overdue", "today", "soon"]
KIND_TITLE = {"overdue": "Overdue", "today": "Due today",
              "soon": "Due tomorrow"}


def log(message):
    """Appends to taskflow_reminders.log (the background process has no
    console, so this is where problems are written)."""
    try:
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 200_000:
            os.remove(LOG_FILE)
        with open(LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}  {message}\n")
    except OSError:
        pass


# ---------------------------------------------------------------------------
# desktop notification
# ---------------------------------------------------------------------------
def _toast_script(title, body):
    """PowerShell that shows a Windows toast (no extra packages needed)."""
    xml = ('<toast><visual><binding template="ToastGeneric">'
           f"<text>{xml_escape(title)}</text><text>{xml_escape(body)}</text>"
           "</binding></visual></toast>").replace("'", "''")
    return (
        "[Windows.UI.Notifications.ToastNotificationManager, "
        "Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null;"
        "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument,"
        " ContentType = WindowsRuntime] | Out-Null;"
        "$x = New-Object Windows.Data.Xml.Dom.XmlDocument;"
        f"$x.LoadXml('{xml}');"
        "$t = New-Object Windows.UI.Notifications.ToastNotification $x;"
        "[Windows.UI.Notifications.ToastNotificationManager]::"
        "CreateToastNotifier('{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}"
        "\\WindowsPowerShell\\v1.0\\powershell.exe').Show($t)")


def desktop_notify(title, body):
    """Shows a notification on this computer. Returns True if it was shown."""
    try:
        if sys.platform.startswith("win"):
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive",
                 "-ExecutionPolicy", "Bypass", "-Command",
                 _toast_script(title, body)],
                capture_output=True, timeout=30,
                creationflags=0x08000000)          # CREATE_NO_WINDOW
            return result.returncode == 0
        if sys.platform == "darwin":
            script = ('display notification "{}" with title "{}"'
                      .format(body.replace('"', "'"), title.replace('"', "'")))
            return subprocess.run(["osascript", "-e", script],
                                  capture_output=True,
                                  timeout=30).returncode == 0
        return subprocess.run(["notify-send", title, body],
                              capture_output=True,
                              timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def push_text(groups):
    """Title and short body for a desktop notification."""
    total = sum(len(v) for v in groups.values())
    title = f"{APP_NAME}: {total} task{'s' if total != 1 else ''} need attention"
    lines = []
    for kind in KIND_ORDER:
        for task_title in groups.get(kind, []):
            lines.append(f"{KIND_TITLE[kind]}: {task_title}")
    body = "\n".join(lines[:3])
    if len(lines) > 3:
        body += f"\n...and {len(lines) - 3} more"
    return title, body


# ---------------------------------------------------------------------------
# the check itself
# ---------------------------------------------------------------------------
LOG_TABLE = """
CREATE TABLE IF NOT EXISTS reminder_log (
    task_id  INTEGER NOT NULL,
    kind     TEXT    NOT NULL,
    channel  TEXT    NOT NULL,
    day      TEXT    NOT NULL,
    PRIMARY KEY (task_id, kind, channel, day),
    FOREIGN KEY (task_id) REFERENCES tasks (task_id) ON DELETE CASCADE
);
"""


def run_once(db_path=None, now=None, notifier=None):
    """One pass over every account that has Push Notifications ON. Returns
    the number of notifications shown. `notifier` can be replaced (tests)."""
    now = now or datetime.now()
    shown = 0
    if now.hour < REMIND_AFTER_HOUR:
        return shown
    notifier = notifier or desktop_notify
    today = now.date()
    today_s = today.isoformat()
    tomorrow_s = (today + timedelta(days=1)).isoformat()

    conn = sqlite3.connect(db_path or DB_FILE, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(LOG_TABLE)
        with conn:
            conn.execute("DELETE FROM reminder_log WHERE day < ?",
                         ((today - timedelta(days=14)).isoformat(),))
        users = conn.execute(
            "SELECT u.user_id FROM users u LEFT JOIN user_settings s"
            " ON s.user_id = u.user_id"
            " WHERE COALESCE(s.push_notifications, 0) = 1").fetchall()

        for user in users:
            tasks = conn.execute(
                "SELECT task_id, title, due_date FROM tasks"
                " WHERE user_id = ? AND is_completed = 0 AND due_date <= ?"
                " ORDER BY due_date, task_id",
                (user["user_id"], tomorrow_s)).fetchall()
            groups, ids = {}, []
            for task in tasks:
                due = task["due_date"]
                kind = ("overdue" if due < today_s else
                        "today" if due == today_s else "soon")
                if conn.execute(
                        "SELECT 1 FROM reminder_log WHERE task_id=? AND "
                        "kind=? AND channel='push' AND day=?",
                        (task["task_id"], kind, today_s)).fetchone():
                    continue
                groups.setdefault(kind, []).append(task["title"])
                ids.append((task["task_id"], kind))
            if not ids:
                continue
            try:
                title, body = push_text(groups)
                ok = bool(notifier(title, body))
            except Exception as error:
                log(f"notification for user {user['user_id']} failed: "
                    f"{error!r}")
                ok = False
            if ok:                       # failed ones are retried next pass
                with conn:
                    conn.executemany(
                        "INSERT OR IGNORE INTO reminder_log "
                        "(task_id, kind, channel, day) VALUES (?,?,'push',?)",
                        [(t, k, today_s) for t, k in ids])
                shown += 1
                log(f"notification shown for user {user['user_id']} "
                    f"({len(ids)} task(s))")
    finally:
        conn.close()
    return shown


# ---------------------------------------------------------------------------
# background process control (used by the Settings page)
# ---------------------------------------------------------------------------
def _control(message, timeout=0.4):
    """Talks to a running background helper. True if one answered."""
    try:
        with socket.create_connection(("127.0.0.1", CONTROL_PORT),
                                      timeout=timeout) as conn:
            conn.sendall(message)
        return True
    except OSError:
        return False


def is_running():
    return _control(b"ping")


def _startup_file():
    appdata = os.environ.get("APPDATA")
    if not (sys.platform.startswith("win") and appdata):
        return None
    return os.path.join(appdata, "Microsoft", "Windows", "Start Menu",
                        "Programs", "Startup", "TaskFlowReminders.vbs")


def autostart_enabled():
    path = _startup_file()
    return bool(path and os.path.exists(path))


def _python_for_background():
    exe = sys.executable
    pythonw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    return pythonw if sys.platform.startswith("win") and \
        os.path.exists(pythonw) else exe


def start_background():
    """Starts the helper now (no window). Returns True if it is running."""
    if is_running():
        return True
    script = os.path.join(HERE, "reminder_service.py")
    flags = 0
    if sys.platform.startswith("win"):
        flags = 0x00000008 | 0x00000200      # DETACHED_PROCESS | NEW_GROUP
    subprocess.Popen([_python_for_background(), script, "--loop"],
                     cwd=HERE, creationflags=flags, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)
    for _ in range(20):                       # wait up to ~4 s
        time.sleep(0.2)
        if is_running():
            return True
    return False


def enable():
    """Start now AND at every login. Returns (ok, message)."""
    path = _startup_file()
    script = os.path.join(HERE, "reminder_service.py")
    if path:
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write('Set sh = CreateObject("WScript.Shell")\r\n'
                         f'sh.Run """{_python_for_background()}"" '
                         f'""{script}"" --loop", 0, False\r\n')
        except OSError as error:
            return False, f"Could not add TaskFlow to Startup: {error}"
    if not start_background():
        return False, ("The background helper did not start. See "
                       "taskflow_reminders.log or run: python "
                       "reminder_service.py --loop")
    if path:
        return True, ("Background reminders are ON. They start automatically "
                      "when you log in to this computer.")
    return True, ("Background reminders are running now. On this system "
                  "start them after a restart with: python "
                  "reminder_service.py --loop")


def disable():
    """Stop the helper and remove it from Startup. Returns (ok, message)."""
    _control(b"stop")
    for _ in range(15):                       # wait up to ~3 s for it to exit
        if not is_running():
            break
        time.sleep(0.2)
    path = _startup_file()
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError as error:
            return False, f"Could not remove the Startup entry: {error}"
    return True, "Background reminders are OFF."


# ---------------------------------------------------------------------------
# --loop mode
# ---------------------------------------------------------------------------
def run_loop():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind(("127.0.0.1", CONTROL_PORT))
    except OSError:
        return                                # another copy is already running
    server.listen(5)
    log("background reminders started")
    next_run = 0.0
    while True:
        if time.time() >= next_run:
            try:
                run_once()
            except Exception as error:
                log(f"check failed: {error!r}")
            next_run = time.time() + CHECK_EVERY
        server.settimeout(5)
        try:
            conn, _ = server.accept()
        except socket.timeout:
            continue
        with conn:
            conn.settimeout(1)
            try:
                data = conn.recv(16)
            except OSError:
                data = b""
        if data.startswith(b"stop"):
            break
    server.close()
    log("background reminders stopped")


def main(argv):
    if "--loop" in argv:
        run_loop()
    elif "--test" in argv:
        ok = desktop_notify(f"{APP_NAME} test",
                            "Desktop notifications are working.")
        print("Notification shown." if ok else
              "Could not show a desktop notification on this system.")
    else:
        print(run_once(), "notification(s) shown")


if __name__ == "__main__":
    main(sys.argv[1:])
