import time
import tkinter as tk

from ui_common import (
    COLOR_BG, build_fonts, build_sidebar, build_topbar,
)
from task_store import TaskStore
from database import Database
from notifications import NotificationCenter
from topbar_menus import TopbarMenus
from dashboard_page import DashboardPage
from my_tasks_page import MyTasksPage
from profile_page import ProfilePage
from settings_page import SettingsPage
from toast import ToastManager
import theme
from completed_page import CompletedPage
from add_task_dialog import AddTaskDialog
from landing_page import LandingPage
from auth_pages import SignInPage, SignUpPage, configure_auth_styles

# what a new account starts with (Settings page)
DEFAULT_SETTINGS = {
    "push_notifications": False,    # pop-up alerts on screen
    "theme": "light",               # "light" or "dark"
}

IDLE_LIMIT_MINUTES = 5              # close the app after this much inactivity


class TaskFlowApp:
    AUTH_PAGES = ("LandingPage", "SignInPage", "SignUpPage")
    APP_PAGES = {"DashboardPage": "Dashboard", "MyTasksPage": "My Tasks",
                 "CompletedPage": "Completed", "ProfilePage": "Profile",
                 "SettingsPage": "Setting"}

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("TaskFlow")
        self._place_window(1180, 740)
        self.root.configure(bg=COLOR_BG)
        self.root.minsize(980, 700)
        self.root.resizable(True, True)

        # ---- account data lives in the SQLite file taskflow.db ----
        self.db = Database()
        self.user = None               # {"id","name","email"} when signed in
        self.settings = dict(DEFAULT_SETTINGS)   # the signed-in account's

        # the auth styles first, so the landing page's own button styles
        # (which share some names) are the ones that stay in effect
        configure_auth_styles(self.root)
        self.fonts = build_fonts()
        self.store = TaskStore(db=self.db)
        self.notifications = NotificationCenter(self.store)
        self.toasts = ToastManager(self.root, self.fonts, self.notifications)

        # ---- landing / sign in / sign up live in this container ----
        self.auth_container = tk.Frame(self.root, bg=COLOR_BG)
        self.auth_pages = {}
        self.current_auth = None
        self._build_auth_pages()

        # ---- the signed-in app (sidebar + top bar + pages) ----
        self.shell = tk.Frame(self.root, bg=COLOR_BG)
        self._build_shell()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.show_frame("LandingPage")
        self._deadline_tick()

        # ---- close the app when it is left alone ----
        self._last_activity = time.monotonic()
        for event in ("<Motion>", "<Key>", "<Button>", "<MouseWheel>"):
            self.root.bind_all(event, self._touch, add="+")
        self._idle_tick()

    # ------------------------------------------------------------------
    # building
    # ------------------------------------------------------------------
    def _place_window(self, width, height):
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        width = min(width, screen_w - 40)
        height = min(height, screen_h - 80)
        x = (screen_w - width) // 2
        y = max((screen_h - height) // 2 - 20, 0)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _build_auth_pages(self, only=None):
        classes = {"LandingPage": LandingPage, "SignInPage": SignInPage,
                   "SignUpPage": SignUpPage}
        for name, cls in classes.items():
            if only and name not in only:
                continue
            self.auth_pages[name] = cls(self.auth_container, self)

    def _build_shell(self):
        self.sidebar, self.set_active, self.set_sidebar_user = build_sidebar(
            self.shell, self.fonts, on_navigate=self.show_page,
            clickable=("Dashboard", "My Tasks", "Completed", "Profile",
                       "Setting"),
            active="Dashboard",
            on_logout=self.sign_out)

        main_area = tk.Frame(self.shell, bg=COLOR_BG)
        main_area.pack(side="left", fill="both", expand=True, padx=24,
                       pady=18)

        self.menus = None
        self.topbar = build_topbar(
            main_area, self.fonts,
            on_bell=lambda: self.menus.toggle_notifications(),
            on_avatar=lambda: self.menus.toggle_profile(),
            on_search=self._on_search)
        self.menus = TopbarMenus(
            main_area, self.fonts, self.store, self.notifications,
            self.topbar, get_user=lambda: self.user,
            on_sign_out=self.sign_out)

        page_area = tk.Frame(main_area, bg=COLOR_BG)
        page_area.pack(fill="both", expand=True)

        self.pages = {
            "Dashboard": DashboardPage(
                page_area, self.fonts, self.store,
                on_add_task=self.open_add_task,
                on_view_completed=lambda: self.show_page("Completed"),
                on_view_tasks=lambda: self.show_page("My Tasks")),
            "My Tasks": MyTasksPage(
                page_area, self.fonts, self.store,
                on_add_task=self.open_add_task,
                on_view_completed=lambda: self.show_page("Completed")),
            "Completed": CompletedPage(page_area, self.fonts, self.store),
            "Profile": ProfilePage(
                page_area, self.fonts, self.store, db=self.db,
                get_user=lambda: self.user, on_saved=self.update_user_info,
                on_deleted=self.sign_out),
            "Setting": SettingsPage(
                page_area, self.fonts, self.settings,
                on_change=self.change_setting,
                on_sign_out=self.sign_out),
        }
        self.current = None

    # ------------------------------------------------------------------
    # navigation  (names match what landing_page.py / auth_pages.py call)
    # ------------------------------------------------------------------
    def show_frame(self, name):
        if name in self.AUTH_PAGES:
            self._show_auth(name)
        elif name in self.APP_PAGES:
            if self.user is None:               # must sign in first
                self._show_auth("SignInPage")
                return
            self._show_shell()
            self.show_page(self.APP_PAGES[name])

    def _show_auth(self, name):
        self.menus.close()
        self.shell.pack_forget()
        if self.current_auth is not None:
            self.current_auth.pack_forget()
        self.auth_container.pack(fill="both", expand=True)
        self.current_auth = self.auth_pages[name]
        self.current_auth.pack(fill="both", expand=True)
        if hasattr(self.current_auth, "refresh_stats"):   # landing page
            self.current_auth.refresh_stats()
        self.root.title("TaskFlow")

    def _show_shell(self):
        self.auth_container.pack_forget()
        self.shell.pack(fill="both", expand=True)

    def show_page(self, name):
        """Switch between Dashboard and Completed inside the app."""
        if name not in self.pages:
            return
        self.menus.close()
        if self.current is not None:
            self.pages[self.current].pack_forget()
        if name == "Profile":
            self.pages[name].load()      # fresh data from the database
        self.pages[name].pack(fill="both", expand=True)
        self.current = name
        self.set_active(name)
        self.root.title(f"TaskFlow — {name}")

    # ------------------------------------------------------------------
    # accounts
    # ------------------------------------------------------------------
    def register_user(self, name, email, password):
        """Called by the Sign Up page. Saves the account in the database
        (a new account starts with no tasks). Raises ValueError if the
        email is already registered."""
        user_id = self.db.create_user(name, email, password)
        self.store.seed_defaults(user_id)
        return user_id

    def set_user(self, user_id, name, email):
        """Called by the Sign In page after a correct login."""
        self.user = {"id": user_id, "name": name, "email": email}
        self._last_activity = time.monotonic()
        self.store.load_for_user(user_id)
        self.settings = self.db.get_settings(user_id)
        # Deadline alerts remain enabled; they are no longer a user setting.
        self.notifications.deadline_alerts = True
        self.notifications.reset()
        self.notifications.check_deadlines()
        self._apply_saved_settings()

        self.set_sidebar_user(name, user_id)
        self.topbar["set_user"](name, user_id)
        self.pages["Dashboard"].set_user_name(name)
        self.topbar["clear_search"]()
        self.pages["My Tasks"].reset()

    def update_user_info(self, name, email):
        """Called by the Profile page after the account was edited: keeps the
        sidebar, top bar and Dashboard greeting in step."""
        self.user["name"] = name
        self.user["email"] = email
        self.set_sidebar_user(name, self.user["id"])
        self.topbar["set_user"](name, self.user["id"])
        self.pages["Dashboard"].set_user_name(name)

    def sign_out(self):
        # tasks and settings are already saved in the database
        self.user = None
        self.menus.close()
        self.toasts.enabled = False
        self.toasts.dismiss_all()
        self.notifications.deadline_alerts = True
        self._apply_theme("light")       # sign in / sign up pages are light
        # fresh sign in / sign up pages so no old text is left in the fields
        for name in ("SignInPage", "SignUpPage"):
            self.auth_pages[name].destroy()
        self.current_auth = None
        self._build_auth_pages(only=("SignInPage", "SignUpPage"))
        self.show_frame("SignInPage")

    # ------------------------------------------------------------------
    # misc
    # ------------------------------------------------------------------
    def change_setting(self, key, value):
        """Called by the Settings page when a switch or theme button is used."""
        self.settings[key] = value
        if self.user is not None:
            self.db.save_settings(self.user["id"], self.settings)
        if key == "theme":
            self._apply_theme(value)
        elif key == "push_notifications":
            self.toasts.enabled = value
            if value:
                self.toasts.show(
                    "Push notifications on",
                    "You'll now get a pop-up for task updates and deadlines.",
                    "added")
        self.pages["Setting"].sync(self.settings)

    def _apply_saved_settings(self):
        """After sign in: put this account's settings into effect."""
        self.toasts.sync()               # don't pop up what is already there
        self.toasts.enabled = self.settings["push_notifications"]
        self._apply_theme(self.settings["theme"])
        self.pages["Setting"].sync(self.settings)

    def _apply_theme(self, name):
        # the sidebar stays navy and the auth pages stay light
        theme.apply(self.root, name,
                    skip=(self.sidebar, self.auth_container))

    def _on_search(self, text):
        """Top-bar search: filters the My Tasks page (and jumps there if
        you start typing from another page)."""
        self.pages["My Tasks"].set_search(text)
        if text.strip() and self.current != "My Tasks":
            self.show_page("My Tasks")

    def open_add_task(self):
        self.menus.close()
        AddTaskDialog(self.root, self.fonts, on_create=self.store.add_task)

    def _deadline_tick(self):
        """Re-check deadlines every few minutes (e.g. when midnight passes)."""
        if self.user is not None:
            self.notifications.check_deadlines()
        self.root.after(5 * 60 * 1000, self._deadline_tick)

    def _touch(self, _event=None):
        """Any mouse or keyboard use counts as activity."""
        self._last_activity = time.monotonic()

    def _idle_tick(self):
        """Every few seconds: close the whole app if nobody used it for too
        long (only while someone is signed in)."""
        if self.user is not None and (
                time.monotonic() - self._last_activity
                >= IDLE_LIMIT_MINUTES * 60):
            self._on_close()
            return
        self.root.after(10 * 1000, self._idle_tick)

    def _on_close(self):
        self.db.close()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    TaskFlowApp().run()