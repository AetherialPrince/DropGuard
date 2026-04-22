#!/usr/bin/env python3
"""
DropGuard NIDPS Installer
==========================
Main entry point for the installation system.

This installer handles:
- Python dependency checks and installation
- System package installation (Suricata)
- File structure setup
- Permission verification
- GUI feedback during installation

Usage:
    ./installer.py           # If no sudo needed
    sudo ./installer.py      # If sudo required
"""

import sys
import os

# ========== PRE-FLIGHT CHECKS (Before any other imports) ========== #

def check_python_version():
    """Ensure Python 3.7+ is installed"""
    if sys.version_info < (3, 7):
        print("=" * 60)
        print("ERROR: Python 3.7 or higher required")
        print("=" * 60)
        print(f"\nYour Python version: {sys.version}")
        print("\nInstallation instructions:")
        print("  Ubuntu/Debian: sudo apt install python3 python3-pip")
        print("  Fedora/RHEL:   sudo dnf install python3 python3-pip")
        print("  Arch:          sudo pacman -S python python-pip")
        print("\nAfter installing Python, run this installer again.")
        print("=" * 60)
        sys.exit(1)
    return True


def check_tkinter():
    """Check if tkinter is available for GUI"""
    try:
        import tkinter
        return True
    except ImportError:
        print("=" * 60)
        print("ERROR: tkinter not found")
        print("=" * 60)
        print("\ntkinter is required for the installation GUI.")
        print("\nInstallation instructions:")
        print("  Ubuntu/Debian: sudo apt install python3-tk")
        print("  Fedora/RHEL:   sudo dnf install python3-tkinter")
        print("  Arch:          sudo pacman -S tk")
        print("\nAfter installing tkinter, run this installer again.")
        print("=" * 60)
        sys.exit(1)


def check_sudo_requirements():
    """
    Determine if sudo is needed and verify privilege level
    Returns True if all checks pass, exits if sudo needed but not present
    """
    needs_sudo = []
    
    # Check if suricata is installed (system package)
    try:
        import subprocess
        result = subprocess.run(['which', 'suricata'], 
                              capture_output=True, 
                              text=True)
        if result.returncode != 0:
            needs_sudo.append('Install Suricata (system package)')
    except:
        needs_sudo.append('Install Suricata (system package)')
    
    # Check write access to suricata rules directory
    suricata_rules = '/var/lib/suricata/rules/'
    if os.path.exists(suricata_rules):
        if not os.access(suricata_rules, os.W_OK):
            needs_sudo.append('Write to Suricata rules directory')
    else:
        needs_sudo.append('Create Suricata rules directory')
    
    # If operations need sudo but we're not root
    if needs_sudo and os.geteuid() != 0:
        print("\n" + "=" * 60)
        print("SUDO PRIVILEGES REQUIRED")
        print("=" * 60)
        print("\nThe following operations require sudo privileges:")
        for op in needs_sudo:
            print(f"  * {op}")
        print(f"\nPlease run with sudo:")
        print(f"  sudo python3 {' '.join(sys.argv)}")
        print("\n" + "=" * 60 + "\n")
        sys.exit(1)
    
    return True


# ========== RUN PRE-FLIGHT CHECKS ========== #

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("DropGuard NIDPS Installer - Pre-flight Checks")
    print("=" * 60 + "\n")
    
    # Check 1: Python version
    print("[OK] Python version check...")
    check_python_version()
    print(f"  Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} detected\n")
    
    # Check 2: tkinter availability
    print("[OK] Checking for tkinter...")
    check_tkinter()
    print("  tkinter is available\n")
    
    # Check 3: Sudo requirements
    print("[OK] Checking privilege requirements...")
    check_sudo_requirements()
    if os.geteuid() == 0:
        print("  Running with sudo privileges\n")
    else:
        print("  No sudo privileges needed for current system state\n")
    
    print("=" * 60)
    print("Pre-flight checks passed! Starting installer...")
    print("=" * 60 + "\n")
    
    # Now safe to import installer modules
    from gui_feedback import InstallerGUI
    from checks import DependencyChecker
    from install_ops import InstallationManager
    from verify import VerificationManager
    from Installer.utils import setup_logging, log_info
    
    # Setup logging
    log_file = setup_logging()
    log_info(f"Installer started - Log file: {log_file}")
    
    # Launch GUI installer
    try:
        app = InstallerGUI()
        app.run()
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)