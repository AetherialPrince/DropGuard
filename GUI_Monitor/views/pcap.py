
import os
import subprocess
from tkinter import *
from views.base import BasePage
from views.theme import BG
from views.widgets import list_box, make_card, muted_label, primary_button, secondary_button, section_title

CAPTURE_DIR = "Captures"


class PCAP(BasePage):
    TITLE = "PCAP Manager"
    DESCRIPTION = "Browse packet captures and open the latest files directly in your external tooling."

    def __init__(self, parent):
        super().__init__(parent)

        toolbar = Frame(self.content, bg=BG)
        toolbar.pack(fill="x", pady=(0, 10))
        muted_label(toolbar, "Double-click a file to open it in Wireshark or a file browser fallback.").pack(side="left")

        btns = Frame(toolbar, bg=BG)
        btns.pack(side="right")
        secondary_button(btns, "Refresh", self.refresh).pack(side="left", padx=(0, 8))
        primary_button(btns, "Open Folder", self.open_folder).pack(side="left")

        card = make_card(self.content)
        card.pack(fill="both", expand=True)

        section_title(card, "Captured Files").pack(anchor="w", padx=12, pady=(12, 8))
        self.listbox = list_box(card)
        self.listbox.pack(expand=True, fill="both", padx=12, pady=(0, 12))
        self.listbox.bind("<Double-Button-1>", self.open_selected)

        self.refresh()

    def set_latest(self, path):
        self.refresh()

    def refresh(self):
        self.listbox.delete(0, END)
        if not os.path.exists(CAPTURE_DIR):
            return

        files = sorted(os.listdir(CAPTURE_DIR), reverse=True)
        for name in files:
            if name.endswith(".pcap"):
                self.listbox.insert(END, name)

    def open_selected(self, event=None):
        sel = self.listbox.curselection()
        if not sel:
            return

        filename = self.listbox.get(sel[0])
        path = os.path.join(CAPTURE_DIR, filename)

        try:
            subprocess.Popen(["wireshark", path])
        except Exception:
            try:
                subprocess.Popen(["thunar", path])
            except Exception:
                try:
                    subprocess.Popen(["nautilus", path])
                except Exception:
                    pass

    def open_folder(self):
        try:
            subprocess.Popen(["thunar", CAPTURE_DIR])
        except Exception:
            try:
                subprocess.Popen(["nautilus", CAPTURE_DIR])
            except Exception:
                pass
