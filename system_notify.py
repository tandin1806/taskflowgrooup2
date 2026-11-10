import base64
import shutil
import subprocess
import sys
import threading

APP_NAME = "TaskFlow"

# Windows needs an "app id" to show a toast; PowerShell's own id always works.
_WIN_APP_ID = (r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}"
               r"\WindowsPowerShell\v1.0\powershell.exe")

_WIN_SCRIPT = r"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml('<toast><visual><binding template="ToastGeneric"><text>@@TITLE@@</text><text>@@MESSAGE@@</text></binding></visual></toast>')
$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('@@APPID@@').Show($toast)
"""


def _xml_escape(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _ps_quote(text):
    """Escape for a PowerShell single-quoted string."""
    return text.replace("'", "''")


def _windows(title, message):
    script = (_WIN_SCRIPT
              .replace("@@TITLE@@", _ps_quote(_xml_escape(title)))
              .replace("@@MESSAGE@@", _ps_quote(_xml_escape(message)))
              .replace("@@APPID@@", _WIN_APP_ID))
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)   # no black window
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive",
         "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded],
        creationflags=flags, timeout=20, check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _mac(title, message):
    def q(text):
        return text.replace("\\", "\\\\").replace('"', '\\"')
    subprocess.run(
        ["osascript", "-e",
         f'display notification "{q(message)}" with title "{q(title)}"'],
        timeout=10, check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _linux(title, message):
    if not shutil.which("notify-send"):
        raise RuntimeError("notify-send is not installed")
    subprocess.run(["notify-send", "--app-name", APP_NAME, title, message],
                   timeout=10, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class SystemNotifier:
    """notifier.send("Title", "Message")  ->  device notification.

    `on_fail` (optional) is called with no arguments if the operating
    system could not show it, so the app can fall back to its own pop-up.
    """

    def __init__(self, on_fail=None):
        self.on_fail = on_fail
        self.available = True        # turns False once it clearly can't work

    def send(self, title, message):
        threading.Thread(target=self._send, args=(title, message),
                         daemon=True).start()

    def _send(self, title, message):
        try:
            if sys.platform.startswith("win"):
                _windows(title, message)
            elif sys.platform == "darwin":
                _mac(title, message)
            else:
                _linux(title, message)
        except Exception:
            self.available = False
            if self.on_fail:
                self.on_fail()
