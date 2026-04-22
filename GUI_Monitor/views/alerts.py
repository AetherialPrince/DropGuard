
"""Alert stream view."""

from tkinter import *
from views.base import BasePage
from views.theme import MONO_FONT
from views.widgets import list_box, make_card, muted_label, secondary_button


class Alerts(BasePage):
    TITLE = "Alerts"
    DESCRIPTION = "Real-time IDS alerts, engine status messages, and operator-visible events."

    def __init__(self, parent):
        super().__init__(parent)

        toolbar = Frame(self.content, bg=self.content.cget("bg"))
        toolbar.pack(fill="x", pady=(0, 10))

        muted_label(toolbar, "Newest alerts appear at the bottom.").pack(side="left")
        secondary_button(toolbar, "Clear View", self.clear_alerts).pack(side="right")

        card = make_card(self.content)
        card.pack(expand=True, fill="both")

        scroll = Scrollbar(card)
        scroll.pack(side="right", fill="y", padx=(0, 8), pady=8)

        self.box = list_box(card, font=MONO_FONT, yscrollcommand=scroll.set)
        self.box.pack(expand=True, fill="both", padx=8, pady=8)
        scroll.config(command=self.box.yview)

    def add_alert(self, text):
        self.box.insert("end", text)
        self.box.yview_moveto(1.0)

    def clear_alerts(self):
        self.box.delete(0, END)
