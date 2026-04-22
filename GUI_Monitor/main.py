
"""Primary GUI entry point for DropGuard."""

import os
import sys
import psutil
from tkinter import *

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.append(ROOT)

from bootstrap import ensure_environment
if not ensure_environment():
    sys.exit(1)

from utils import resource_path
from nidps.storage.db import init_db
from views import PAGES
from views.theme import BG, FG, MUTED, PANEL, SIDEBAR, SUCCESS, DANGER, apply_ttk_theme
from views.widgets import primary_button
from views.menu import AppMenu
from scapy.all import get_if_list
from controller import AppController

init_db()


def get_friendly_interfaces():
    scapy_ifaces = get_if_list()
    sys_ifaces = psutil.net_if_addrs()

    friendly = {}
    good_sys = []

    for name, addrs in sys_ifaces.items():
        for a in addrs:
            if a.family.name == "AF_INET":
                if not name.lower().startswith("loopback"):
                    good_sys.append(name)
                break

    for idx, iface in enumerate(scapy_ifaces):
        if "loopback" in iface.lower():
            friendly["Adapter for loopback traffic capture"] = iface
            continue

        if idx < len(good_sys):
            friendly[good_sys[idx]] = iface
        else:
            friendly[f"Adapter {idx}"] = iface

    return friendly


class App:
    def __init__(self):
        self.root = Tk()
        self.root.title("DropGuard")
        self.root.geometry("1240x760")
        self.root.minsize(1100, 680)
        self.root.configure(bg=BG)
        apply_ttk_theme(self.root)

        try:
            icon = PhotoImage(file=resource_path("assets/Icon.png"))
            self.root.iconphoto(True, icon)
        except Exception:
            pass

        self.container = Frame(self.root, bg=BG)
        self.container.pack(expand=True, fill="both")

        self.status_var = StringVar(value="STOPPED")
        self.controller = AppController(self)
        self.nav_buttons = {}

        self.show_splash()

    def ui_safe(self, fn):
        def wrapper(data):
            self.root.after(0, lambda: fn(data))
        return wrapper

    def show_splash(self):
        self.splash = Frame(self.container, bg=SIDEBAR)
        self.splash.pack(expand=True, fill="both")

        brand = Frame(self.splash, bg=SIDEBAR)
        brand.pack(expand=True)

        try:
            self.img = PhotoImage(file=resource_path("assets/Background.png"))
            splash_label = Label(brand, image=self.img, bg=SIDEBAR)
            splash_label.image = self.img
            splash_label.pack(pady=(0, 18))
        except Exception:
            pass

        Label(
            brand,
            text="DropGuard",
            fg=FG,
            bg=SIDEBAR,
            font=("Segoe UI", 28, "bold")
        ).pack()

        Label(
            brand,
            text="Network intrusion detection and prevention console",
            fg=MUTED,
            bg=SIDEBAR,
            font=("Segoe UI", 11)
        ).pack(pady=(8, 0))

        self.root.after(1400, self.build_ui)

    def build_ui(self):
        self.splash.destroy()

        self.sidebar = Frame(self.container, bg=SIDEBAR, width=260)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.main = Frame(self.container, bg=BG)
        self.main.pack(side="right", expand=True, fill="both")

        topbar = Frame(self.main, bg=PANEL, height=48, highlightthickness=1, highlightbackground="#475569")
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        status_chip = Frame(topbar, bg=DANGER)
        status_chip.pack(side="left", padx=16, pady=10)

        self.status_bar = Label(
            status_chip,
            textvariable=self.status_var,
            bg=DANGER,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=4
        )
        self.status_bar.pack()

        Label(
            topbar,
            text="Operational status",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 10)
        ).pack(side="left", padx=(8, 0))

        self.pages = {}
        for name, PageClass in PAGES.items():
            self.pages[name] = PageClass(self.main)

        AppMenu(self.root, self)

        Label(
            self.sidebar,
            text="DROPGUARD",
            bg=SIDEBAR,
            fg=FG,
            font=("Segoe UI", 18, "bold")
        ).pack(anchor="w", padx=18, pady=(18, 2))

        Label(
            self.sidebar,
            text="Security operations console",
            bg=SIDEBAR,
            fg=MUTED,
            font=("Segoe UI", 10)
        ).pack(anchor="w", padx=18, pady=(0, 18))

        iface_section = Frame(self.sidebar, bg=SIDEBAR)
        iface_section.pack(fill="x", padx=18, pady=(0, 12))

        Label(iface_section, text="Interface", bg=SIDEBAR, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")

        self.iface_map = get_friendly_interfaces()
        friendly_names = list(self.iface_map.keys())
        self.iface_var = StringVar(value=friendly_names[0] if friendly_names else "")

        self.iface_menu = OptionMenu(iface_section, self.iface_var, *friendly_names)
        self.iface_menu.config(
            bg=PANEL,
            fg=FG,
            activebackground=PANEL,
            activeforeground=FG,
            relief="flat",
            highlightthickness=0,
            font=("Segoe UI", 10),
            anchor="w"
        )
        self.iface_menu["menu"].config(bg=PANEL, fg=FG, activebackground="#334155", activeforeground=FG)
        self.iface_menu.pack(fill="x", pady=(8, 12))

        self.start_button = primary_button(
            iface_section,
            "Start IDS",
            self.controller.toggle_ids
        )
        self.start_button.pack(fill="x")

        nav_frame = Frame(self.sidebar, bg=SIDEBAR)
        nav_frame.pack(fill="both", expand=True, padx=12, pady=(10, 12))

        Label(nav_frame, text="Navigation", bg=SIDEBAR, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=6, pady=(0, 8))

        for name in self.pages.keys():
            button = Button(
                nav_frame,
                text=name,
                bg=SIDEBAR,
                fg=FG,
                activebackground="#1e293b",
                activeforeground=FG,
                relief="flat",
                bd=0,
                anchor="w",
                padx=12,
                pady=10,
                font=("Segoe UI", 10),
                cursor="hand2",
                command=lambda page=name: self.show(page)
            )
            button.pack(fill="x", pady=2)
            self.nav_buttons[name] = button

        self.controller.wire_events()
        self.show("Dashboard")

    def set_status_indicator(self, running: bool):
        color = SUCCESS if running else DANGER
        self.status_bar.config(bg=color)
        self.status_bar.master.config(bg=color)

    def show(self, name):
        for page_name, page in self.pages.items():
            page.pack_forget()
            if page_name in self.nav_buttons:
                self.nav_buttons[page_name].config(bg=SIDEBAR)

        page = self.pages[name]
        page.pack(expand=True, fill="both")

        if name in self.nav_buttons:
            self.nav_buttons[name].config(bg="#1e293b")

        if hasattr(page, "on_show"):
            page.on_show()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
