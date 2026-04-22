from tkinter import *
from tkinter import messagebox

from views.base import BasePage
from views.theme import BG, MONO_FONT
from views.widgets import (
    danger_button,
    list_box,
    make_card,
    muted_label,
    primary_button,
    secondary_button,
    section_title,
    text_area,
)

from nidps.storage.db import (
    get_all_hosts,
    get_alerts_for_mac,
    get_blacklist_history,
    remove_blacklist,
    blacklist_mac,
)

from nidps.storage.storage import (
    add_blacklist,
    remove_blacklist_file,
    get_ips_for_mac,
)

from nidps.suricata.suricata_writer import remove_mac_rules
from nidps.detection.threats import reset_mac_cooldown


class Blacklist(BasePage):
    TITLE = "Blacklist"
    DESCRIPTION = "Manage blocked hosts and review enforcement evidence."

    def __init__(self, parent):
        super().__init__(parent)

        # ================= HEADER =================
        toolbar = Frame(self.content, bg=BG)
        toolbar.pack(fill="x", pady=(0, 10))

        muted_label(toolbar, "Select discovered hosts to block or review blocked devices.").pack(side="left")

        btns = Frame(toolbar, bg=BG)
        btns.pack(side="right")

        secondary_button(btns, "Refresh", self.on_show).pack(side="left", padx=4)
        primary_button(btns, "Add Selected", self.add_selected).pack(side="left", padx=4)
        danger_button(btns, "Remove Selected", self.unblacklist).pack(side="left", padx=4)

        # ================= MAIN LAYOUT =================
        layout = Frame(self.content, bg=BG)
        layout.pack(expand=True, fill="both")

        layout.grid_columnconfigure(0, weight=1)
        layout.grid_columnconfigure(1, weight=2)
        layout.grid_rowconfigure(0, weight=1)

        # -------- LEFT --------
        left = make_card(layout)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        section_title(left, "Discovered Hosts").pack(anchor="w", padx=12, pady=(12, 8))

        self.host_box = list_box(left)
        self.host_box.pack(expand=True, fill="both", padx=12, pady=(0, 12))

        # -------- RIGHT --------
        right = Frame(layout, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=2)
        right.grid_columnconfigure(0, weight=1)

        top = make_card(right)
        top.grid(row=0, column=0, sticky="nsew", pady=(0, 10))

        section_title(top, "Blacklisted").pack(anchor="w", padx=12, pady=(12, 8))

        self.box = list_box(top)
        self.box.pack(expand=True, fill="both", padx=12, pady=(0, 12))

        bottom = make_card(right)
        bottom.grid(row=1, column=0, sticky="nsew")

        section_title(bottom, "Details").pack(anchor="w", padx=12, pady=(12, 8))

        self.details = text_area(bottom, wrap="word", font=MONO_FONT)
        self.details.pack(expand=True, fill="both", padx=12, pady=(0, 12))

        self.box.bind("<<ListboxSelect>>", self.show_details)

        self.on_show()

    def on_show(self):
        self.load_hosts()
        self.load_blacklist()
        self.details.delete("1.0", END)

    def load_hosts(self):
        self.host_box.delete(0, END)
        for h in get_all_hosts():
            self.host_box.insert(END, f"{h['mac']} ({h['ip'] or 'Unknown'})")

    def load_blacklist(self):
        self.box.delete(0, END)
        try:
            with open("blacklist.txt", "r") as f:
                for line in f:
                    mac = line.strip()
                    if mac:
                        self.box.insert(END, mac)
        except:
            pass

    def add_selected(self):
        sel = self.host_box.curselection()
        if not sel:
            return

        mac = self.host_box.get(sel[0]).split("(")[0].strip()

        add_blacklist(mac)
        blacklist_mac(mac, "manual-from-hosts")
        self.load_blacklist()

    def add_mac(self, mac):
        if mac not in self.box.get(0, END):
            self.box.insert(END, mac)

    def unblacklist(self):
        sel = self.box.curselection()
        if not sel:
            return

        mac = self.box.get(sel[0])

        if not messagebox.askyesno("Confirm", f"Remove {mac} from blacklist?"):
            return

        try:
            remove_mac_rules(mac)
            remove_blacklist(mac)
            remove_blacklist_file(mac)
            reset_mac_cooldown(mac)

            self.load_blacklist()
            self.details.delete("1.0", END)

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def show_details(self, event=None):
        sel = self.box.curselection()
        if not sel:
            return

        mac = self.box.get(sel[0])
        self.details.delete("1.0", END)

        alerts = get_alerts_for_mac(mac)
        history = get_blacklist_history(mac)
        ips = get_ips_for_mac(mac)

        self.details.insert(END, f"MAC: {mac}\n")
        self.details.insert(END, "=" * 70 + "\n\n")

        self.details.insert(END, "IP HISTORY\n")
        self.details.insert(END, "-" * 70 + "\n")
        for ip in ips:
            self.details.insert(END, f"• {ip}\n")

        self.details.insert(END, "\nALERTS\n")
        self.details.insert(END, "-" * 70 + "\n")
        for a in alerts:
            self.details.insert(END, f"{a['timestamp']} | {a['message']}\n")

        self.details.insert(END, "\nBLACKLIST HISTORY\n")
        self.details.insert(END, "-" * 70 + "\n")
        for h in history:
            self.details.insert(END, f"{h['timestamp']} | {h['reason']}\n")