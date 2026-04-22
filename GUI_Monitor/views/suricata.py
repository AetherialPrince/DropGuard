
import os
from tkinter import *
from tkinter import messagebox
from views.base import BasePage
from views.theme import BG, MONO_FONT
from views.widgets import make_card, muted_label, primary_button, secondary_button, section_title, text_area
from nidps.suricata.suricata_runtime import reload_suricata_ips


class Suricata(BasePage):
    TITLE = "Suricata Rules"
    DESCRIPTION = "Review generated rules from the enforcement pipeline."

    def __init__(self, parent):
        super().__init__(parent)
        self.rules_file = "/var/lib/suricata/rules/dropguard.rules"

        toolbar = Frame(self.content, bg=BG)
        toolbar.pack(fill="x", pady=(0, 10))
        muted_label(toolbar, "View and edit the active Suricata rules file. Save to apply changes.").pack(side="left")

        btn_row = Frame(toolbar, bg=BG)
        btn_row.pack(side="right")
        secondary_button(btn_row, "Refresh", self.load_rules).pack(side="left", padx=(0, 6))
        primary_button(btn_row, "Save & Reload", self.save_and_reload).pack(side="left")

        card = make_card(self.content)
        card.pack(fill="both", expand=True)

        section_title(card, "Rules").pack(anchor="w", padx=12, pady=(12, 8))
        self.text = text_area(card, wrap="none", font=MONO_FONT)
        self.text.pack(expand=True, fill="both", padx=12, pady=(0, 12))

        self.load_rules()

    def load_rules(self):
        self.text.delete("1.0", "end")
        if os.path.exists(self.rules_file):
            with open(self.rules_file, "r") as f:
                self.text.insert("end", f.read())

    def append_rule(self, rule):
        self.text.insert("end", rule + "\n")
        self.text.see("end")

    def save_rules(self):
        with open(self.rules_file, "w") as f:
            f.write(self.text.get("1.0", "end").strip())

    def save_and_reload(self):
        try:
            self.save_rules()
            reload_suricata_ips()
            messagebox.showinfo("Suricata", "Rules saved and Suricata reloaded.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save/reload: {e}")
