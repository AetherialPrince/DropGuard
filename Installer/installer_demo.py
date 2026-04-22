#!/usr/bin/env python3
"""
Demo/Test Mode for DropGuard Installer GUI
Shows the completion screen without actually installing anything
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import sys
import time


class InstallerDemoGUI:
    """Demo version of installer GUI showing completion state"""
    
    # Colors
    BG = "#1e1e1e"
    PANEL = "#2d2d2d"
    FG = "#ffffff"
    ACCENT = "#00bcd4"
    SUCCESS = "#4caf50"
    ERROR = "#f44336"
    WARNING = "#ff9800"
    
    def __init__(self, demo_state='success'):
        """
        Args:
            demo_state: 'success', 'warning', or 'installing'
        """
        self.demo_state = demo_state
        self.root = tk.Tk()
        self.root.title("DropGuard NIDPS Installer [DEMO]")
        self.root.geometry("700x600")
        self.root.configure(bg=self.BG)
        self.root.resizable(False, False)
        
        self._build_ui()
        
        # Automatically show the demo state after a short delay
        self.root.after(500, self._show_demo_state)
    
    def _build_ui(self):
        """Build the GUI components"""
        
        # Header
        header = tk.Frame(self.root, bg=self.PANEL, height=80)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)
        
        title_label = tk.Label(
            header,
            text="DropGuard NIDPS Installer [DEMO MODE]",
            font=("Segoe UI", 16, "bold"),
            bg=self.PANEL,
            fg=self.ACCENT
        )
        title_label.pack(pady=25)
        
        # Main content area
        content = tk.Frame(self.root, bg=self.BG)
        content.pack(fill="both", expand=True, padx=20, pady=10)
        
        # System info section
        info_frame = tk.Frame(content, bg=self.BG)
        info_frame.pack(fill="x", pady=(0, 10))
        
        self.info_label = tk.Label(
            info_frame,
            text="System: debian | Python: 3.13.7",
            font=("Segoe UI", 10),
            bg=self.BG,
            fg=self.FG,
            justify="left",
            anchor="w"
        )
        self.info_label.pack(fill="x")
        
        # Progress section
        progress_frame = tk.Frame(content, bg=self.BG)
        progress_frame.pack(fill="x", pady=(0, 10))
        
        self.status_label = tk.Label(
            progress_frame,
            text="Status: Ready",
            font=("Segoe UI", 10),
            bg=self.BG,
            fg=self.FG,
            anchor="w"
        )
        self.status_label.pack(fill="x")
        
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            length=660
        )
        self.progress_bar.pack(fill="x", pady=5)
        
        self.progress_percent = tk.Label(
            progress_frame,
            text="0%",
            font=("Segoe UI", 9),
            bg=self.BG,
            fg=self.FG,
            anchor="e"
        )
        self.progress_percent.pack(fill="x")
        
        # Dependencies list section (simplified for demo)
        deps_label = tk.Label(
            content,
            text="Dependencies:",
            font=("Segoe UI", 11, "bold"),
            bg=self.BG,
            fg=self.FG,
            anchor="w"
        )
        deps_label.pack(fill="x", pady=(10, 5))
        
        self.deps_frame = tk.Frame(content, bg=self.PANEL)
        self.deps_frame.pack(fill="x", pady=(0, 10))
        
        # Add sample dependencies
        self._add_sample_dependency("Python: scapy", "Packet capture library", "[OK]")
        self._add_sample_dependency("Python: psutil", "System utilities", "[OK]")
        self._add_sample_dependency("System: suricata", "IDS/IPS engine", "[OK]" if self.demo_state == 'success' else "[...]")
        
        # Log section
        log_label = tk.Label(
            content,
            text="Installation Log:",
            font=("Segoe UI", 10, "bold"),
            bg=self.BG,
            fg=self.FG,
            anchor="w"
        )
        log_label.pack(fill="x", pady=(10, 5))
        
        self.log_text = scrolledtext.ScrolledText(
            content,
            height=12,
            bg=self.PANEL,
            fg=self.FG,
            font=("Consolas", 9),
            insertbackground=self.FG,
            state='disabled'
        )
        self.log_text.pack(fill="both", expand=True)
        
        # Button section
        button_frame = tk.Frame(self.root, bg=self.BG)
        button_frame.pack(fill="x", padx=20, pady=10)
        
        self.action_button = tk.Button(
            button_frame,
            text="Processing...",
            font=("Segoe UI", 11, "bold"),
            bg=self.PANEL,
            fg=self.FG,
            command=self.root.quit,
            state='disabled',
            cursor="hand2",
            relief="flat",
            padx=20,
            pady=10
        )
        self.action_button.pack(side="left", padx=5)
        
        self.close_button = tk.Button(
            button_frame,
            text="Close",
            font=("Segoe UI", 11),
            bg=self.PANEL,
            fg=self.FG,
            activebackground=self.ERROR,
            command=self.root.quit,
            cursor="hand2",
            relief="flat",
            padx=20,
            pady=10
        )
        self.close_button.pack(side="right", padx=5)
    
    def _add_sample_dependency(self, name, description, status):
        """Add a sample dependency widget"""
        frame = tk.Frame(self.deps_frame, bg=self.PANEL)
        frame.pack(fill="x", padx=10, pady=3)
        
        status_colors = {
            '[OK]': self.SUCCESS,
            '[...]': self.ACCENT,
            '[FAIL]': self.ERROR
        }
        
        indicator = tk.Label(
            frame,
            text=status,
            font=("Segoe UI", 10, "bold"),
            bg=self.PANEL,
            fg=status_colors.get(status, self.FG),
            width=6
        )
        indicator.pack(side="left")
        
        text_frame = tk.Frame(frame, bg=self.PANEL)
        text_frame.pack(side="left", fill="x", expand=True, padx=10)
        
        name_label = tk.Label(
            text_frame,
            text=name,
            font=("Segoe UI", 10, "bold"),
            bg=self.PANEL,
            fg=self.FG,
            anchor="w"
        )
        name_label.pack(fill="x")
        
        desc_label = tk.Label(
            text_frame,
            text=description,
            font=("Segoe UI", 8),
            bg=self.PANEL,
            fg="#aaaaaa",
            anchor="w"
        )
        desc_label.pack(fill="x")
    
    def _log(self, message):
        """Add message to log"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
    
    def _show_demo_state(self):
        """Show the selected demo state"""
        if self.demo_state == 'success':
            self._show_success_completion()
        elif self.demo_state == 'warning':
            self._show_warning_completion()
        elif self.demo_state == 'installing':
            self._show_installing_state()
    
    def _show_success_completion(self):
        """Show successful completion state"""
        self.progress_bar['value'] = 100
        self.progress_percent.config(text="100%")
        self.status_label.config(
            text="Status: Installation Complete - System Ready!",
            fg=self.SUCCESS
        )
        
        self._log("="*50)
        self._log("INSTALLATION COMPLETE")
        self._log("="*50)
        self._log("")
        self._log("[OK] All critical checks passed!")
        self._log("[OK] System is ready to use!")
        self._log("")
        self._log("="*50)
        self._log("You can now:")
        self._log("  * Run DropGuard NIDPS: python3 NIDPS_Prototype.py <interface>")
        self._log("  * Launch GUI: python3 main.py")
        self._log("  * Start Suricata: sudo systemctl start suricata")
        self._log("")
        self._log("Thank you for installing DropGuard!")
        self._log("="*50)
        
        self.action_button.config(
            state='normal',
            text="Close Installer",
            bg=self.SUCCESS
        )
    
    def _show_warning_completion(self):
        """Show completion with warnings"""
        self.progress_bar['value'] = 90
        self.progress_percent.config(text="90%")
        self.status_label.config(
            text="Status: Installation Complete (with warnings)",
            fg=self.WARNING
        )
        
        self._log("="*50)
        self._log("INSTALLATION COMPLETE")
        self._log("="*50)
        self._log("")
        self._log("[WARN] Some checks failed")
        self._log("")
        self._log("Recommendations:")
        self._log("  * Start Suricata service: sudo systemctl start suricata")
        self._log("  * Fix permissions: sudo chmod +w /var/lib/suricata/rules/")
        self._log("")
        self._log("="*50)
        
        self.action_button.config(
            state='normal',
            text="Close Installer",
            bg=self.WARNING
        )
    
    def _show_installing_state(self):
        """Show active installation state"""
        self.progress_bar['value'] = 45
        self.progress_percent.config(text="45%")
        self.status_label.config(
            text="Status: Installing dependencies...",
            fg=self.ACCENT
        )
        
        self._log("Starting installation...")
        self._log("")
        self._log("[...] Installing scapy...")
        self._log("[OK] Successfully installed scapy")
        self._log("[...] Installing psutil...")
        self._log("[OK] Successfully installed psutil")
        self._log("[...] Installing suricata...")
        self._log("Installing system packages (this may take a while)...")
        
        self.action_button.config(
            state='disabled',
            text="Installing...",
            bg=self.PANEL
        )
    
    def run(self):
        """Start the GUI event loop"""
        self.root.mainloop()


if __name__ == "__main__":
    # Parse command line argument for demo state
    demo_state = 'success'  # default
    if len(sys.argv) > 1:
        if sys.argv[1] in ['success', 'warning', 'installing']:
            demo_state = sys.argv[1]
        else:
            print("Usage: python3 installer_demo.py [success|warning|installing]")
            print("  success    - Show successful completion (default)")
            print("  warning    - Show completion with warnings")
            print("  installing - Show active installation in progress")
            sys.exit(1)
    
    print(f"Starting installer demo in '{demo_state}' mode...")
    print("This is a demonstration - no actual installation will occur.")
    print()
    
    app = InstallerDemoGUI(demo_state=demo_state)
    app.run()
