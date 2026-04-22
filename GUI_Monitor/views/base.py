"""
base.py

Defines the abstract base class used by all GUI pages.
Provides consistent styling and title rendering across views.
"""


"""Shared page shell with consistent spacing and title layout."""

from tkinter import *
from views.theme import BG, FG, MUTED, PAGE_PAD_X, PAGE_PAD_Y, TITLE_FONT, SMALL_FONT


class BasePage(Frame):
    TITLE = "Page"
    DESCRIPTION = ""

    def __init__(self, parent):
        super().__init__(parent, bg=BG)

        self.wrapper = Frame(self, bg=BG)
        self.wrapper.pack(
            expand=True,
            fill="both",
            padx=PAGE_PAD_X,
            pady=PAGE_PAD_Y
        )

        header = Frame(self.wrapper, bg=BG)
        header.pack(fill="x", pady=(0, 14))

        Label(
            header,
            text=self.TITLE,
            bg=BG,
            fg=FG,
            font=TITLE_FONT
        ).pack(anchor="w")

        if self.DESCRIPTION:
            Label(
                header,
                text=self.DESCRIPTION,
                bg=BG,
                fg=MUTED,
                font=SMALL_FONT
            ).pack(anchor="w", pady=(4, 0))

        self.content = Frame(self.wrapper, bg=BG)
        self.content.pack(fill="both", expand=True)
