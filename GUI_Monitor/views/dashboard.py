from tkinter import *
from views.base import BasePage
from views.theme import ACCENT, BG, FG, MUTED, PANEL, SUBTITLE_FONT, TITLE_FONT
from nidps.core import telemetry
import psutil



class Dashboard(BasePage):
    TITLE = "Dashboard"
    DESCRIPTION = "Live IDS activity and system performance."

    def __init__(self, parent):
        super().__init__(parent)

        # ================= IDS METRICS =================
        self.metric_labels = {}

        grid = Frame(self.content, bg=BG)
        grid.pack(fill="x", pady=(0, 16))

        cards = [
            ("Packets", "Captured traffic"),
            ("Alerts", "Detections"),
            ("Hosts", "Tracked hosts"),
            ("Whitelist", "Trusted hosts"),
            ("Blacklist", "Blocked hosts"),
        ]

        for index, (name, hint) in enumerate(cards):
            row = index // 3
            col = index % 3

            card = Frame(
                grid,
                bg=PANEL,
                highlightthickness=1,
                highlightbackground="#475569"
            )
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

            grid.grid_columnconfigure(col, weight=1)

            if name == "Whitelist":
                title_color = "#22c55e"
            elif name == "Blacklist":
                title_color = "#ef4444"
            else:
                title_color = MUTED

            Label(
                card,
                text=name,
                bg=PANEL,
                fg=title_color,
                font=SUBTITLE_FONT
            ).pack(anchor="w", padx=16, pady=(14, 4))

            value = Label(
                card,
                text="0",
                bg=PANEL,
                fg=FG,
                font=TITLE_FONT
            )
            value.pack(anchor="w", padx=16)

            Label(
                card,
                text=hint,
                bg=PANEL,
                fg=ACCENT,
                font=("Segoe UI", 9)
            ).pack(anchor="w", padx=16, pady=(4, 14))

            self.metric_labels[name] = value

        # ================= SYSTEM METRICS =================
        self.system_frame = Frame(self.content, bg=BG)
        self.system_frame.pack(fill="x", pady=(10, 16))

        Label(
            self.system_frame,
            text="System Metrics",
            bg=BG,
            fg=FG,
            font=SUBTITLE_FONT
        ).pack(anchor="w", pady=(5, 8))

        self.cards_row = Frame(self.system_frame, bg=BG)
        self.cards_row.pack(fill="x")

        self.cpu_lbl = self.sys_card("CPU")
        self.ram_lbl = self.sys_card("RAM")
        self.disk_lbl = self.sys_card("Disk")

        # ================= RECENT ALERTS =================
        alerts_frame = Frame(
            self.content,
            bg=PANEL,
            highlightthickness=1,
            highlightbackground="#475569"
        )
        alerts_frame.pack(fill="both", expand=True)

        Label(
            alerts_frame,
            text="Recent Alerts",
            bg=PANEL,
            fg=FG,
            font=SUBTITLE_FONT
        ).pack(anchor="w", padx=16, pady=(14, 8))

        self.alert_preview = Listbox(
            alerts_frame,
            bg=PANEL,
            fg=FG,
            height=8,
            relief="flat",
            highlightthickness=0,
            selectbackground="#0ea5e9",
            selectforeground="#081018"
        )
        self.alert_preview.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        # Initial loads
        self.refresh_stats()
        self.update_system_stats()

    # ================= SYSTEM CARD =================
    def sys_card(self, name):
        frame = Frame(
            self.cards_row,
            bg=PANEL,
            width=160,
            height=85,
            highlightthickness=1,
            highlightbackground="#475569"
        )
        frame.pack(side="left", padx=10)
        frame.pack_propagate(False)

        Label(
            frame,
            text=name,
            bg=PANEL,
            fg=MUTED,
            font=SUBTITLE_FONT
        ).pack(pady=(8, 2))

        label = Label(
            frame,
            text="--",
            bg=PANEL,
            fg=FG,
            font=TITLE_FONT
        )
        label.pack()

        return label

    # ================= COLOR LOGIC =================
    def get_color(self, value):
        if value < 50:
            return "#22c55e"
        elif value < 80:
            return "#f59e0b"
        return "#ef4444"

    # ================= SYSTEM UPDATE =================
    def update_system_stats(self):
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        self.cpu_lbl.config(
            text=f"{cpu:.0f}%",
            fg=self.get_color(cpu)
        )

        self.ram_lbl.config(
            text=f"{ram.percent:.0f}%",
            fg=self.get_color(ram.percent)
        )

        self.disk_lbl.config(
            text=f"{disk.percent:.0f}%",
            fg=self.get_color(disk.percent)
        )

        self.after(1000, self.update_system_stats)

    # ================= FILE COUNT FALLBACK =================
    def count_file_lines(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return len([line for line in f if line.strip()])
        except Exception:
            return 0

    # ================= IDS STATS =================
    def refresh_stats(self):
        stats = telemetry.get_stats()

        self.metric_labels["Packets"].config(text=str(stats.get("packets", 0)))
        self.metric_labels["Alerts"].config(text=str(stats.get("alerts", 0)))
        self.metric_labels["Hosts"].config(text=str(stats.get("hosts", 0)))

        whitelist_count = stats.get("whitelist", self.count_file_lines("whitelist.txt"))
        blacklist_count = stats.get("blacklist", self.count_file_lines("blacklist.txt"))

        self.metric_labels["Whitelist"].config(text=str(whitelist_count))
        self.metric_labels["Blacklist"].config(text=str(blacklist_count))

    # ================= ALERT PREVIEW =================
    def add_alert_preview(self, msg):
        self.alert_preview.insert(END, msg)
        self.alert_preview.yview_moveto(1.0)

        if self.alert_preview.size() > 20:
            self.alert_preview.delete(0)