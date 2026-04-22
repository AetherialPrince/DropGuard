
from tkinter import *
from tkinter import ttk
from views.base import BasePage
from views.widgets import make_card, muted_label, secondary_button


class LiveTraffic(BasePage):
    TITLE = "Live Traffic"
    DESCRIPTION = "Structured packet activity as it reaches the detection pipeline."

    def __init__(self, parent):
        super().__init__(parent)

        toolbar = Frame(self.content, bg=self.content.cget("bg"))
        toolbar.pack(fill="x", pady=(0, 10))
        muted_label(toolbar, "Sortable-style table layout with fixed operational columns.").pack(side="left")
        secondary_button(toolbar, "Clear Rows", self.clear_rows).pack(side="right")

        card = make_card(self.content)
        card.pack(expand=True, fill="both")

        cols = ("Time", "Source IP", "MAC", "Protocol", "Port", "Action")

        table_frame = Frame(card, bg=card.cget("bg"))
        table_frame.pack(expand=True, fill="both", padx=8, pady=8)

        self.table = ttk.Treeview(table_frame, columns=cols, show="headings")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=vsb.set)

        widths = {
            "Time": 140,
            "Source IP": 180,
            "MAC": 170,
            "Protocol": 100,
            "Port": 90,
            "Action": 140,
        }

        for c in cols:
            self.table.heading(c, text=c)
            self.table.column(c, width=widths[c], anchor="center")

        self.table.pack(side="left", expand=True, fill="both")
        vsb.pack(side="right", fill="y")

    def add_packet(self, row):
        self.table.insert("", "end", values=row)

    def clear_rows(self):
        for item in self.table.get_children():
            self.table.delete(item)
