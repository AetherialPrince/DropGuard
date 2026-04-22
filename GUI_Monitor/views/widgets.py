
"""Reusable Tkinter widgets and UI helpers for a cleaner, consistent app."""

from tkinter import *
from .theme import (
    ACCENT,
    ACCENT_HOVER,
    BG,
    BORDER,
    DANGER,
    FG,
    MUTED,
    NORMAL_FONT,
    PANEL,
    PANEL_ALT,
    SMALL_FONT,
    SUBTITLE_FONT,
)


def section_title(parent, text):
    return Label(
        parent,
        text=text,
        bg=parent.cget("bg"),
        fg=FG,
        font=SUBTITLE_FONT
    )


def muted_label(parent, text):
    return Label(
        parent,
        text=text,
        bg=parent.cget("bg"),
        fg=MUTED,
        font=SMALL_FONT
    )


def make_card(parent):
    card = Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
    return card


def primary_button(parent, text, command, width=None):
    return Button(
        parent,
        text=text,
        command=command,
        bg=ACCENT,
        fg="#081018",
        activebackground=ACCENT_HOVER,
        activeforeground="#081018",
        relief="flat",
        bd=0,
        padx=12,
        pady=8,
        width=width,
        font=("Segoe UI", 10, "bold"),
        cursor="hand2"
    )


def secondary_button(parent, text, command, width=None):
    return Button(
        parent,
        text=text,
        command=command,
        bg=PANEL_ALT,
        fg=FG,
        activebackground=BORDER,
        activeforeground=FG,
        relief="flat",
        bd=0,
        padx=12,
        pady=8,
        width=width,
        font=NORMAL_FONT,
        cursor="hand2"
    )


def danger_button(parent, text, command, width=None):
    return Button(
        parent,
        text=text,
        command=command,
        bg=DANGER,
        fg="white",
        activebackground="#dc2626",
        activeforeground="white",
        relief="flat",
        bd=0,
        padx=12,
        pady=8,
        width=width,
        font=("Segoe UI", 10, "bold"),
        cursor="hand2"
    )


def entry(parent, textvariable=None, width=28):
    return Entry(
        parent,
        textvariable=textvariable,
        width=width,
        relief="flat",
        bd=0,
        bg=PANEL_ALT,
        fg=FG,
        insertbackground=FG,
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=ACCENT,
        font=NORMAL_FONT
    )


def text_area(parent, **kwargs):
    widget = Text(
        parent,
        bg=PANEL,
        fg=FG,
        insertbackground=FG,
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=ACCENT,
        font=kwargs.pop("font", NORMAL_FONT),
        **kwargs
    )
    return widget


def list_box(parent, **kwargs):
    widget = Listbox(
        parent,
        bg=PANEL,
        fg=FG,
        selectbackground=ACCENT_HOVER,
        selectforeground="#081018",
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=ACCENT,
        font=kwargs.pop("font", NORMAL_FONT),
        **kwargs
    )
    return widget


def divider(parent, pady=8):
    line = Frame(parent, bg=BORDER, height=1)
    line.pack(fill="x", pady=pady)
    return line
