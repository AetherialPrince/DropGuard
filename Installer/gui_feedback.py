"""
GUI Feedback Module
===================
Provides visual feedback during installation
"""

import subprocess
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
from checks import DependencyChecker
from install_ops import InstallationManager
from verify import VerificationManager
from Installer.utils import log_info, log_error
from Installer.setup_launcher import install_launcher


class InstallerGUI:
    """
    GUI Window for installation progress
    """
    
    # Colors
    BG = "#1e1e1e"
    PANEL = "#2d2d2d"
    FG = "#ffffff"
    ACCENT = "#00bcd4"
    SUCCESS = "#4caf50"
    ERROR = "#f44336"
    WARNING = "#ff9800"
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DropGuard NIDPS Installer")
        self.root.geometry("700x700")
        self.root.configure(bg=self.BG)
        self.root.resizable(True, True)
        
        # Installation state
        self.checker = None
        self.installer = None
        self.verifier = None
        self.installation_complete = False
        self.launcher_ready = False
        
        # Message queue for thread-safe GUI updates
        self.message_queue = queue.Queue()
        
        # Build UI
        self._build_ui()
        
        # Start checking dependencies
        self.root.after(500, self._start_dependency_check)
    
    def _build_ui(self):
        """Build the GUI components"""
        
        # Header
        header = tk.Frame(self.root, bg=self.PANEL, height=80)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)
        
        title_label = tk.Label(
            header,
            text="DropGuard NIDPS Installer",
            font=("Segoe UI", 18, "bold"),
            bg=self.PANEL,
            fg=self.ACCENT
        )
        title_label.pack(pady=20)
        
        # Main content area
        content = tk.Frame(self.root, bg=self.BG)
        content.pack(fill="both", expand=True, padx=20, pady=10)
        
        # System info section
        info_frame = tk.Frame(content, bg=self.BG)
        info_frame.pack(fill="x", pady=(0, 10))
        
        self.info_label = tk.Label(
            info_frame,
            text="Initializing...",
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
            text="Status: Checking system...",
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
        
        # Dependencies list section
        deps_label = tk.Label(
            content,
            text="Dependencies:",
            font=("Segoe UI", 11, "bold"),
            bg=self.BG,
            fg=self.FG,
            anchor="w"
        )
        deps_label.pack(fill="x", pady=(10, 5))
        
        deps_container = tk.Frame(content, bg=self.PANEL)
        deps_container.pack(fill="both", expand=True)
        
        # Scrollable frame for dependencies
        self.deps_canvas = tk.Canvas(deps_container, bg=self.PANEL, highlightthickness=0)
        deps_scrollbar = ttk.Scrollbar(deps_container, orient="vertical", command=self.deps_canvas.yview)
        self.deps_frame = tk.Frame(self.deps_canvas, bg=self.PANEL)
        
        self.deps_frame.bind(
            "<Configure>",
            lambda e: self.deps_canvas.configure(scrollregion=self.deps_canvas.bbox("all"))
        )
        
        self.deps_canvas.create_window((0, 0), window=self.deps_frame, anchor="nw")
        self.deps_canvas.configure(yscrollcommand=deps_scrollbar.set)
        
        self.deps_canvas.pack(side="left", fill="both", expand=True)
        deps_scrollbar.pack(side="right", fill="y")
        
        self.dependency_widgets = {}
        
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
            height=6,
            bg=self.PANEL,
            fg=self.FG,
            font=("Consolas", 9),
            insertbackground=self.FG,
            state='disabled'
        )
        self.log_text.pack(fill="both", expand=False)
        
        # Button section
        button_frame = tk.Frame(self.root, bg=self.BG)
        button_frame.pack(fill="x", padx=20, pady=10)
        
        self.action_button = tk.Button(
            button_frame,
            text="Start Installation",
            font=("Segoe UI", 11, "bold"),
            bg=self.ACCENT,
            fg=self.BG,
            activebackground=self.SUCCESS,
            command=self._on_action_button,
            state='disabled',
            cursor="hand2",
            relief="flat",
            padx=20,
            pady=10
        )
        self.action_button.pack(side="left", padx=5)
        
        self.launch_button = tk.Button(
            button_frame,
            text="Launch DropGuard",
            font=("Segoe UI", 11, "bold"),
            bg=self.PANEL,
            fg="#888888",
            activebackground=self.SUCCESS,
            command=self._launch_dropguard,
            state='disabled',
            cursor="hand2",
            relief="flat",
            padx=20,
            pady=10
        )
        self.launch_button.pack(side="left", padx=5)

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

    def _add_dependency_widget(self, name, description, status='CHECKING'):
        """Add a dependency status widget"""
        frame = tk.Frame(self.deps_frame, bg=self.PANEL)
        frame.pack(fill="x", padx=10, pady=3)
        
        # Status indicator
        status_colors = {
            'CHECKING': self.WARNING,
            'INSTALLED': self.SUCCESS,
            'MISSING': self.WARNING,
            'INSTALLING': self.ACCENT,
            'SUCCESS': self.SUCCESS,
            'FAILED': self.ERROR
        }
        
        status_symbol = {
            'CHECKING': '[...]',
            'INSTALLED': '[OK]',
            'MISSING': '[FAIL]',
            'INSTALLING': '[...]',
            'SUCCESS': '[OK]',
            'FAILED': '[FAIL]'
        }
        
        indicator = tk.Label(
            frame,
            text=status_symbol.get(status, '?'),
            font=("Segoe UI", 12, "bold"),
            bg=self.PANEL,
            fg=status_colors.get(status, self.FG),
            width=2
        )
        indicator.pack(side="left")
        
        # Name and description
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
        
        self.dependency_widgets[name] = {
            'frame': frame,
            'indicator': indicator,
            'name_label': name_label,
            'desc_label': desc_label
        }
    
    def _update_dependency_widget(self, name, status, message=None):
        """Update dependency widget status"""
        if name not in self.dependency_widgets:
            return
        
        widget = self.dependency_widgets[name]
        
        status_colors = {
            'INSTALLED': self.SUCCESS,
            'MISSING': self.WARNING,
            'INSTALLING': self.ACCENT,
            'SUCCESS': self.SUCCESS,
            'FAILED': self.ERROR
        }
        
        status_symbol = {
            'INSTALLED': '[OK]',
            'MISSING': '[FAIL]',
            'INSTALLING': '[...]',
            'SUCCESS': '[OK]',
            'FAILED': '[FAIL]'
        }
        
        widget['indicator'].config(
            text=status_symbol.get(status, '?'),
            fg=status_colors.get(status, self.FG)
        )
        
        if message:
            widget['desc_label'].config(text=message)
    
    def _log_message(self, message):
        """Add message to log window"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
    
    def _update_progress(self, value, text=None):
        """Update progress bar"""
        self.progress_bar['value'] = value
        self.progress_percent.config(text=f"{int(value)}%")
        if text:
            self.status_label.config(text=f"Status: {text}")
    
    def _start_dependency_check(self):
        """Start dependency checking in background thread"""
        def check_thread():
            self.checker = DependencyChecker()
            results = self.checker.check_all()
            self.message_queue.put(('CHECK_COMPLETE', results))
        
        self._log_message("Starting dependency check...")
        threading.Thread(target=check_thread, daemon=True).start()
        self._process_queue()
    
    def _process_queue(self):
        """Process messages from background threads"""
        try:
            while True:
                msg_type, data = self.message_queue.get_nowait()
                
                if msg_type == 'CHECK_COMPLETE':
                    self._handle_check_complete(data)
                elif msg_type == 'INSTALL_PROGRESS':
                    step_name, status, message = data
                    self._handle_install_progress(step_name, status, message)
                elif msg_type == 'INSTALL_COMPLETE':
                    self._handle_install_complete(data)
                elif msg_type == 'VERIFY_COMPLETE':
                    self._handle_verify_complete(data)
                elif msg_type == 'LAUNCHER_COMPLETE':
                    self._handle_launcher_complete(data)
                    
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self._process_queue)
    
    def _handle_check_complete(self, results):
        """Handle dependency check completion"""
        self._log_message("Dependency check complete")

        # Update system info
        sys_info = results['system_info']
        info_text = f"System: {sys_info['os']} | Python: {sys_info['python_version']}"
        self.info_label.config(text=info_text)
        
        # Display dependencies
        for pkg_name, pkg_data in results['python_packages'].items():
            self._add_dependency_widget(
                f"Python: {pkg_name}",
                pkg_data['description'],
                pkg_data['status']
            )
        
        for pkg_name, pkg_data in results['system_packages'].items():
            self._add_dependency_widget(
                f"System: {pkg_name}",
                pkg_data['description'],
                pkg_data['status']
            )
        
        # Check if installation needed
        needs_install = self.checker.needs_installation()

        if needs_install:
            self.action_button.config(state='normal', text="Start Installation")
            self._update_progress(10, "Ready to install")
            self._log_message("Some dependencies are missing. Click 'Start Installation' to proceed.")
        else:
            self.action_button.config(state='normal', text="Verify Installation")
            self._update_progress(50, "All dependencies installed")
            self._log_message("All dependencies are already installed!")
    
    def _on_action_button(self):
        """Handle action button click"""
        if not self.installation_complete:
            self._start_installation()
        else:
            self.root.quit()
    
    def _start_installation(self):
        """Start installation in background thread"""
        self.action_button.config(state='disabled')
        self._log_message("\n" + "="*50)
        self._log_message("Starting installation...")
        self._log_message("="*50)
        
        def install_thread():
            # Create installer with progress callback
            def progress_callback(step, status, message):
                self.message_queue.put(('INSTALL_PROGRESS', (step, status, message)))
            
            self.installer = InstallationManager(progress_callback=progress_callback)
            
            # Setup directories
            self.installer.setup_directories()
            
            # Get installation plan
            plan = self.checker.get_installation_plan()
            
            # Execute installation
            result = self.installer.execute_installation_plan(plan)
            
            # Setup Suricata rules if Suricata was installed
            if any('suricata' in pkg for pkg in self.installer.installed_packages):
                self.installer.setup_suricata_rules()
            
            self.message_queue.put(('INSTALL_COMPLETE', result))
        
        threading.Thread(target=install_thread, daemon=True).start()
    
    def _handle_install_progress(self, step_name, status, message):
        """Handle installation progress update"""
        self._log_message(f"[{status}] {step_name}: {message}")
        self._update_dependency_widget(f"Python: {step_name}", status, message)
        self._update_dependency_widget(f"System: {step_name}", status, message)
    
    def _handle_install_complete(self, result):
        """Handle installation completion"""
        self._log_message("\n" + "="*50)
        self._log_message("Installation complete!")
        self._log_message(f"Successful: {result['success']}/{result['total']}")
        self._log_message(f"Failed: {result['failed']}/{result['total']}")
        self._log_message("="*50 + "\n")
        
        self._update_progress(80, "Installation complete, verifying...")
        
        # Start verification
        def verify_thread():
            self.verifier = VerificationManager()
            verify_results = self.verifier.verify_all()
            self.message_queue.put(('VERIFY_COMPLETE', verify_results))
        
        threading.Thread(target=verify_thread, daemon=True).start()
    
    def _handle_verify_complete(self, results):
        """Handle verification completion"""
        self._log_message("\n" + "="*50)
        self._log_message("Verification complete!")
        self._log_message("="*50)
        
        if self.verifier.all_critical_checks_passed():
            self._log_message("\n[OK] All critical checks passed!")
            self._update_progress(90, "Creating desktop shortcut...")
            self.status_label.config(
                text="Status: Setting up launcher...",
                fg=self.ACCENT
            )

            def launcher_thread():
                results = install_launcher()
                self.message_queue.put(('LAUNCHER_COMPLETE', results))

            threading.Thread(target=launcher_thread, daemon=True).start()
            # installation_complete is set by _handle_launcher_complete
        else:
            self._log_message("\n[WARN] Some checks failed.")
            recommendations = self.verifier.get_recommendations()
            if recommendations:
                self._log_message("\nRecommendations:")
                for rec in recommendations:
                    self._log_message(rec)
            self._update_progress(90, "Installation complete with warnings")
            self.action_button.config(
                state='normal',
                text="Close Installer",
                bg=self.WARNING
            )
            self.installation_complete = True
    
    def _handle_launcher_complete(self, results):
        """Handle shortcut/launcher setup completion."""
        self._log_message("\n" + "="*50)
        self._log_message("INSTALLATION COMPLETE")
        self._log_message("="*50)

        if results and all(results.values()):
            self._log_message("\n[OK] Desktop shortcut created successfully.")
            self._log_message("[OK] DropGuard is ready — find it in your Applications menu")
            self._log_message("     or double-click the shortcut on your Desktop.")
            self._update_progress(100, "All done!")
            self.status_label.config(
                text="Status: DropGuard is installed and ready!",
                fg=self.SUCCESS
            )
        else:
            self._log_message("\n[OK] Core installation succeeded.")
            failed = [k for k, v in results.items() if not v] if results else ["launcher"]
            self._log_message(f"[WARN] Shortcut step(s) had issues: {', '.join(failed)}")
            self._log_message("     DropGuard can still be started with:  dropguard")
            self._update_progress(100, "Installed (shortcut partial)")
            self.status_label.config(
                text="Status: Installed — see log for shortcut notes",
                fg=self.WARNING
            )

        self._log_message("\nThank you for installing DropGuard!")
        self._log_message("="*50)

        self.launcher_ready = True
        self.installation_complete = True

        self.action_button.config(
            state='normal',
            text="Close Installer",
            bg=self.SUCCESS
        )
        self.launch_button.config(
            state='normal',
            bg=self.ACCENT,
            fg=self.BG
        )

    def _launch_dropguard(self):
        """Fire-and-forget: start DropGuard via the installed launcher."""
        try:
            subprocess.Popen(
                ["/usr/local/bin/dropguard"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            self._log_message("\n[OK] DropGuard is starting...")
        except Exception as exc:
            self._log_message(f"\n[ERR] Could not launch DropGuard: {exc}")

    def run(self):
        """Start the GUI event loop"""
        self.root.mainloop()                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             