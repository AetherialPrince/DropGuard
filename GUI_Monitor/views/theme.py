
"""Shared theme constants and ttk styling for the DropGuard GUI."""

from tkinter import ttk

# ---------- Color System ----------
BG = "#0f172a"
PANEL = "#1e293b"
PANEL_ALT = "#334155"
SIDEBAR = "#020617"
FG = "#e2e8f0"
MUTED = "#94a3b8"
ACCENT = "#38bdf8"
ACCENT_HOVER = "#0ea5e9"
SUCCESS = "#22c55e"
DANGER = "#ef4444"
WARNING = "#f59e0b"
BORDER = "#475569"

# ---------- Typography ----------
TITLE_FONT = ("Segoe UI", 20, "bold")
SUBTITLE_FONT = ("Segoe UI", 12, "bold")
NORMAL_FONT = ("Segoe UI", 10)
SMALL_FONT = ("Segoe UI", 9)
MONO_FONT = ("Consolas", 10)

# ---------- Sizing ----------
PAGE_PAD_X = 20
PAGE_PAD_Y = 18
CARD_PAD = 14
INPUT_WIDTH = 28


def apply_ttk_theme(root):
    """Configure ttk widgets once at startup."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure(
        ".",
        background=BG,
        foreground=FG,
        font=NORMAL_FONT
    )

    style.configure(
        "Treeview",
        background=PANEL,
        foreground=FG,
        fieldbackground=PANEL,
        rowheight=30,
        bordercolor=BORDER,
        borderwidth=0
    )
    style.map(
        "Treeview",
        background=[("selected", ACCENT_HOVER)],
        foreground=[("selected", "#081018")]
    )

    style.configure(
        "Treeview.Heading",
        background=PANEL_ALT,
        foreground=FG,
        font=SUBTITLE_FONT,
        relief="flat",
        borderwidth=0
    )
    style.map(
        "Treeview.Heading",
        background=[("active", PANEL_ALT)]
    )

    style.configure(
        "TCombobox",
        fieldbackground=PANEL,
        background=PANEL_ALT,
        foreground=FG,
        arrowcolor=FG,
        bordercolor=BORDER,
        lightcolor=PANEL,
        darkcolor=PANEL
    )

    style.configure(
        "Vertical.TScrollbar",
        background=PANEL_ALT,
        troughcolor=BG,
        bordercolor=BG,
        arrowcolor=FG
    )

    return style
