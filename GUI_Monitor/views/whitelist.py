from tkinter import *

from views.base import BasePage
from views.theme import BG
from views.widgets import (
    list_box,
    make_card,
    muted_label,
    primary_button,
    secondary_button,
    section_title,
)

from nidps.storage.db import get_all_hosts, whitelist_mac
from nidps.storage.storage import add_whitelist


class Whitelist(BasePage):
    TITLE = "Whitelist"
    DESCRIPTION = "Promote trusted hosts and manage exempted MAC addresses."

    def __init__(self, parent):
        super().__init__(parent)

        # ================= HEADER =================
        toolbar = Frame(self.content, bg=BG)
        toolbar.pack(fill="x", pady=(0, 10))

        muted_label(
            toolbar,
            "Move discovered hosts into a trusted allow-list."
        ).pack(side="left")

        btns = Frame(toolbar, bg=BG)
        btns.pack(side="right")

        secondary_button(btns, "Refresh", self.on_show).pack(side="left", padx=4)
        primary_button(btns, "Add Selected", self.add_selected).pack(side="left", padx=4)
        secondary_button(btns, "Remove Selected", self.remove_selected).pack(side="left", padx=4)

        # ================= MAIN LAYOUT =================
        layout = Frame(self.content, bg=BG)
        layout.pack(expand=True, fill="both")

        layout.grid_columnconfigure(0, weight=1)
        layout.grid_columnconfigure(1, weight=1)
        layout.grid_rowconfigure(0, weight=1)

        # ==================================================
        # LEFT - DISCOVERED HOSTS
        # ==================================================
        left = make_card(layout)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        section_title(left, "Discovered Hosts").pack(
            anchor="w",
            padx=12,
            pady=(12, 8)
        )

        self.host_box = list_box(left)
        self.host_box.pack(expand=True, fill="both", padx=12, pady=(0, 12))

        # ==================================================
        # RIGHT - WHITELIST
        # ==================================================
        right = make_card(layout)
        right.grid(row=0, column=1, sticky="nsew")

        section_title(right, "Whitelisted MACs").pack(
            anchor="w",
            padx=12,
            pady=(12, 8)
        )

        self.white_box = list_box(right)
        self.white_box.pack(expand=True, fill="both", padx=12, pady=(0, 12))

        self.on_show()

    # ==================================================
    # REFRESH
    # ==================================================
    def on_show(self):
        self.load_hosts()
        self.load_whitelist()

    # ==================================================
    # DISCOVERED HOSTS
    # ==================================================
    def load_hosts(self):
        self.host_box.delete(0, END)

        seen = set()
        whitelisted = set(self.white_box.get(0, END))

        for h in get_all_hosts():
            mac = (h["mac"] or "").strip().lower()
            ip = (h["ip"] or "").strip()

            # Accept only real MAC aa:bb:cc:dd:ee:ff
            parts = mac.split(":")
            if not (len(parts) == 6 and all(len(p) == 2 for p in parts)):
                continue

            if mac in seen:
                continue
            seen.add(mac)

            if mac in whitelisted:
                continue

            if ip.startswith("fe80:"):
                ip = "Unknown"

            self.host_box.insert(END, f"{mac} ({ip or 'Unknown'})")
    # ==================================================
    # WHITELIST FILE
    # ==================================================
    def load_whitelist(self):
        self.white_box.delete(0, END)

        try:
            with open("whitelist.txt", "r") as f:
                for line in f:
                    mac = line.strip().lower()
                    if mac:
                        self.white_box.insert(END, mac)
        except Exception:
            pass

    # ==================================================
    # ACTIONS
    # ==================================================
    def add_selected(self):
        sel = self.host_box.curselection()
        if not sel:
            return

        row = self.host_box.get(sel[0])
        mac = row.split("(")[0].strip().lower()

        add_whitelist(mac)
        whitelist_mac(mac, "manual-from-hosts")

        self.on_show()

    def remove_selected(self):
        sel = self.white_box.curselection()
        if not sel:
            return

        mac = self.white_box.get(sel[0]).strip().lower()

        try:
            with open("whitelist.txt", "r") as f:
                lines = f.readlines()

            with open("whitelist.txt", "w") as f:
                for line in lines:
                    if line.strip().lower() != mac:
                        f.write(line)

            self.on_show()

        except Exception:
            pass

    # ==================================================
    # LIVE EVENT ADD
    # ==================================================
    def add_mac(self, mac):
        mac = mac.strip().lower()

        if mac not in self.white_box.get(0, END):
            self.white_box.insert(END, mac)

        self.load_hosts()