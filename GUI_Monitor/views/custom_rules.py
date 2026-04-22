from __future__ import annotations

import ipaddress
import re
from tkinter import *
from tkinter import ttk, messagebox

from views.theme import BG, FG, PANEL, PANEL_ALT
from views.widgets import (
    danger_button, entry, make_card, muted_label,
    primary_button, secondary_button, section_title
)

from nidps.storage.db import (
    get_custom_rules,
    add_custom_rule,
    update_custom_rule,
    delete_custom_rule,
)

from nidps.core import telemetry

_MAC_RE = re.compile(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")


class CustomRulesPage(Frame):

    def __init__(self, parent):
        super().__init__(parent, bg=BG)

        # ================= HEADER =================
        Label(self, text="Custom Rules", fg=FG, bg=BG,
              font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=20, pady=(18, 4))

        muted_label(self, "Build custom detection rules. Choose existing hosts or define custom targets.")\
            .pack(anchor="w", padx=20)

        layout = Frame(self, bg=BG)
        layout.pack(fill="both", expand=True, padx=20, pady=16)
        layout.grid_columnconfigure(0, weight=3)
        layout.grid_columnconfigure(1, weight=2)

        # ================= TABLE =================
        table_card = make_card(layout)
        table_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        section_title(table_card, "Configured Rules").pack(anchor="w", padx=12, pady=(12, 8))

        columns = ("ID", "Name", "Src", "Dst", "Port", "Proto", "Action")

        self.tree = ttk.Treeview(table_card, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=120)

        self.tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        btn_row = Frame(table_card, bg=PANEL)
        btn_row.pack(fill="x", padx=12, pady=(0, 12))

        secondary_button(btn_row, "Refresh", self.refresh).pack(side="left")
        secondary_button(btn_row, "Edit Selected", self.edit_selected).pack(side="left", padx=6)
        danger_button(btn_row, "Delete Selected", self.delete_rule).pack(side="right")

        # ================= FORM =================
        form_card = make_card(layout)
        form_card.grid(row=0, column=1, sticky="nsew")

        section_title(form_card, "Add Rule").pack(anchor="w", padx=12, pady=(12, 8))

        form = Frame(form_card, bg=PANEL)
        form.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Edit state: None = adding new, int = editing existing rule id
        self._editing_id: int | None = None

        # VARIABLES
        self.name_var = StringVar()
        self.port_var = StringVar()
        self.protocol_var = StringVar()

        self.src_mode = StringVar(value="ANY")
        self.dst_mode = StringVar(value="HOME")

        self.src_host_var = StringVar()
        self.dst_host_var = StringVar()

        self.src_custom_var = StringVar()
        self.dst_custom_var = StringVar()

        self.alert_var = BooleanVar()
        self.blacklist_var = BooleanVar()

        # ================= NAME =================
        Label(form, text="Name", bg=PANEL, fg=FG).pack(anchor="w")
        entry(form, textvariable=self.name_var).pack(fill="x", pady=(0, 12))

        # ================= SOURCE =================
        Label(form, text="Source", bg=PANEL, fg=FG).pack(anchor="w")

        src_modes = Frame(form, bg=PANEL)
        src_modes.pack(anchor="w", pady=(0, 6))

        for val in ("ANY", "HOME", "EXISTING", "CUSTOM"):
            Radiobutton(src_modes, text=val, variable=self.src_mode, value=val,
                        bg=PANEL, fg=FG, selectcolor=PANEL_ALT,
                        command=self.update_mode_states).pack(side="left", padx=4)

        Label(form, text="Existing Host", bg=PANEL, fg="#94a3b8").pack(anchor="w")
        self.src_dropdown = ttk.Combobox(form, textvariable=self.src_host_var, state="readonly")
        self.src_dropdown.pack(fill="x", pady=(0, 6))

        Label(form, text="Custom IP or MAC", bg=PANEL, fg="#94a3b8").pack(anchor="w")
        self.src_entry = entry(form, textvariable=self.src_custom_var)
        self.src_entry.pack(fill="x", pady=(0, 12))

        # ================= DEST =================
        Label(form, text="Destination", bg=PANEL, fg=FG).pack(anchor="w")

        dst_modes = Frame(form, bg=PANEL)
        dst_modes.pack(anchor="w", pady=(0, 6))

        for val in ("HOME", "ANY", "EXISTING", "CUSTOM"):
            Radiobutton(dst_modes, text=val, variable=self.dst_mode, value=val,
                        bg=PANEL, fg=FG, selectcolor=PANEL_ALT,
                        command=self.update_mode_states).pack(side="left", padx=4)

        Label(form, text="Existing Host", bg=PANEL, fg="#94a3b8").pack(anchor="w")
        self.dst_dropdown = ttk.Combobox(form, textvariable=self.dst_host_var, state="readonly")
        self.dst_dropdown.pack(fill="x", pady=(0, 6))

        Label(form, text="Custom IP", bg=PANEL, fg="#94a3b8").pack(anchor="w")
        self.dst_entry = entry(form, textvariable=self.dst_custom_var)
        self.dst_entry.pack(fill="x", pady=(0, 12))

        # ================= PORT =================
        Label(form, text="Port", bg=PANEL, fg=FG).pack(anchor="w")
        entry(form, textvariable=self.port_var).pack(fill="x", pady=(0, 12))

        # ================= PROTOCOL =================
        Label(form, text="Protocol", bg=PANEL, fg=FG).pack(anchor="w")
        ttk.Combobox(form, textvariable=self.protocol_var,
                     values=["", "TCP", "UDP", "ICMP"],
                     state="readonly").pack(fill="x", pady=(0, 12))

        # ================= ACTIONS =================
        act = Frame(form, bg=PANEL)
        act.pack(anchor="w", pady=(0, 12))

        Checkbutton(act, text="Alert", variable=self.alert_var,
                    bg=PANEL, fg=FG, selectcolor=PANEL_ALT).pack(side="left", padx=6)
        Checkbutton(act, text="Blacklist", variable=self.blacklist_var,
                    bg=PANEL, fg=FG, selectcolor=PANEL_ALT).pack(side="left", padx=6)

        # ================= BUTTONS =================
        btns = Frame(form, bg=PANEL)
        btns.pack(fill="x")

        self.submit_btn = primary_button(btns, "Add Rule", self.save_rule)
        self.submit_btn.pack(side="left")
        secondary_button(btns, "Clear", self.clear_form).pack(side="left", padx=8)

        # INIT
        self.load_hosts()
        self.update_mode_states()
        self.refresh()

    # ================= HOSTS =================
    def load_hosts(self):
        values = []
        try:
            stats = telemetry.get_stats()
            for h in stats.get("hosts_list", []):
                values.append(f"{h.get('mac')} ({h.get('ip')})")
        except:
            pass

        self.src_dropdown["values"] = values
        self.dst_dropdown["values"] = values

    # ================= MODE CONTROL =================
    def update_mode_states(self):
        src_mode = self.src_mode.get()
        dst_mode = self.dst_mode.get()

        # SOURCE
        self.src_dropdown.config(state="readonly" if src_mode == "EXISTING" else "disabled")
        self.src_entry.config(state="normal" if src_mode == "CUSTOM" else "disabled")

        # DEST
        self.dst_dropdown.config(state="readonly" if dst_mode == "EXISTING" else "disabled")
        self.dst_entry.config(state="normal" if dst_mode == "CUSTOM" else "disabled")

    # ================= VALIDATION =================
    def _is_valid_ip(self, v):
        try:
            ipaddress.ip_address(v)
            return True
        except:
            return False

    def _is_valid_mac(self, v):
        return bool(_MAC_RE.fullmatch(v.strip()))

    # ================= SAVE (ADD or UPDATE) =================
    def _collect_form(self):
        """Parse the form and return kwargs for add/update. Raises ValueError on bad input."""
        src_ip = None
        src_mac = None

        if self.src_mode.get() == "HOME":
            src_ip = "HOME"
        elif self.src_mode.get() == "EXISTING":
            src_mac = self.src_host_var.get().split("(")[0].strip()
        elif self.src_mode.get() == "CUSTOM":
            val = self.src_custom_var.get().strip()
            if self._is_valid_ip(val):
                src_ip = val
            elif self._is_valid_mac(val):
                src_mac = val
            else:
                raise ValueError("Invalid source input")

        dst_ip = None
        if self.dst_mode.get() == "HOME":
            dst_ip = "HOME"
        elif self.dst_mode.get() == "EXISTING":
            dst_ip = self.dst_host_var.get().split("(")[1].replace(")", "").strip()
        elif self.dst_mode.get() == "CUSTOM":
            val = self.dst_custom_var.get().strip()
            if not self._is_valid_ip(val):
                raise ValueError("Invalid destination IP")
            dst_ip = val

        port = int(self.port_var.get()) if self.port_var.get() else None

        return dict(
            name=self.name_var.get() or None,
            src_ip=src_ip,
            src_mac=src_mac,
            dst_ip=dst_ip,
            dst_port=port,
            protocol=self.protocol_var.get() or None,
            action_alert=self.alert_var.get(),
            action_block=self.blacklist_var.get(),
            action_drop=self.blacklist_var.get(),
        )

    def save_rule(self):
        try:
            kwargs = self._collect_form()
            if self._editing_id is None:
                add_custom_rule(**kwargs)
            else:
                update_custom_rule(self._editing_id, **kwargs)
            self.refresh()
            self.clear_form()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            return

        values = self.tree.item(sel[0])["values"]
        rule_id = values[0]

        # Find the full rule record from DB
        rules = get_custom_rules(enabled_only=False)
        rule = next((r for r in rules if r["id"] == rule_id), None)
        if rule is None:
            return

        self._editing_id = rule_id
        self.submit_btn.config(text="Update Rule")

        # Populate name, port, protocol
        self.name_var.set(rule["name"] or "")
        self.port_var.set(str(rule["dst_port"]) if rule["dst_port"] else "")
        self.protocol_var.set(rule["protocol"] or "")
        self.alert_var.set(bool(rule["action_alert"]))
        self.blacklist_var.set(bool(rule["action_block"]))

        # Populate source
        if rule["src_mac"]:
            self.src_mode.set("CUSTOM")
            self.src_custom_var.set(rule["src_mac"])
        elif rule["src_ip"] == "HOME":
            self.src_mode.set("HOME")
        elif rule["src_ip"]:
            self.src_mode.set("CUSTOM")
            self.src_custom_var.set(rule["src_ip"])
        else:
            self.src_mode.set("ANY")

        # Populate destination
        if rule["dst_ip"] == "HOME":
            self.dst_mode.set("HOME")
        elif rule["dst_ip"]:
            self.dst_mode.set("CUSTOM")
            self.dst_custom_var.set(rule["dst_ip"])
        else:
            self.dst_mode.set("ANY")

        self.update_mode_states()

    def delete_rule(self):
        sel = self.tree.selection()
        if not sel:
            return
        rid = self.tree.item(sel[0])["values"][0]
        delete_custom_rule(rid)
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for r in get_custom_rules(enabled_only=False):
            self.tree.insert("", "end", values=(
                r["id"],
                r["name"] or "-",
                r["src_ip"] or r["src_mac"] or "-",
                r["dst_ip"] or "-",
                r["dst_port"] or "-",
                r["protocol"] or "-",
                "ALERT" if r["action_alert"] else "BLOCK"
            ))

    def clear_form(self):
        self._editing_id = None
        self.submit_btn.config(text="Add Rule")
        self.name_var.set("")
        self.src_mode.set("ANY")
        self.dst_mode.set("HOME")
        self.src_custom_var.set("")
        self.dst_custom_var.set("")
        self.src_host_var.set("")
        self.dst_host_var.set("")
        self.port_var.set("")
        self.protocol_var.set("")
        self.alert_var.set(False)
        self.blacklist_var.set(False)
        self.update_mode_states()