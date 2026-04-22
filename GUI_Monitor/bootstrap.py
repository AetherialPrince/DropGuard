"""
DropGuard Bootstrap Module
---------------------------
Ensures required dependencies are installed before launching GUI.
Also performs non-destructive Suricata sanity checks.
"""

import os
import sys
import subprocess


SURICATA_MAIN = "/etc/suricata/suricata.yaml"
SURICATA_INCLUDE = "/etc/suricata/dropguard.yaml"
SURICATA_RULE_DIR = "/var/lib/suricata/rules"
SURICATA_RULE_FILE = f"{SURICATA_RULE_DIR}/dropguard.rules"


def _check_suricata_installed() -> bool:
    """Return True if Suricata is installed."""
    try:
        result = subprocess.run(
            ["which", "suricata"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def _ensure_dropguard_rule_file() -> None:
    """Ensure DropGuard rule file exists."""
    os.makedirs(SURICATA_RULE_DIR, exist_ok=True)

    if not os.path.exists(SURICATA_RULE_FILE):
        open(SURICATA_RULE_FILE, "a").close()
        print("[DropGuard] Created dropguard.rules")


def _ensure_dropguard_include_file() -> None:
    """
    Ensure DropGuard include file exists.
    IMPORTANT: Suricata expects YAML header lines in included YAML too.
    """

    if os.path.exists(SURICATA_INCLUDE):
        return

    content = """%YAML 1.1
---
vars:
  address-groups:
    HOME_NET: "[192.168.0.0/16]"

default-rule-path: /var/lib/suricata/rules

rule-files:
  - dropguard.rules
"""

    with open(SURICATA_INCLUDE, "w") as f:
        f.write(content)

    print("[DropGuard] Created dropguard.yaml")


def _ensure_suricata_include() -> None:
    """Ensure suricata.yaml includes DropGuard include file."""
    if not os.path.exists(SURICATA_MAIN):
        print("[DropGuard] Suricata main config not found")
        return

    include_line = "include: /etc/suricata/dropguard.yaml"

    with open(SURICATA_MAIN, "r") as f:
        config = f.read()

    if include_line not in config:
        with open(SURICATA_MAIN, "a") as f:
            f.write("\n" + include_line + "\n")
        print("[DropGuard] Added DropGuard include to Suricata")


def _test_suricata_config() -> bool:
    """Validate Suricata configuration."""
    try:
        result = subprocess.run(
            ["suricata", "-T", "-c", SURICATA_MAIN],
            capture_output=True,
            text=True,
            timeout=20,
        )

        if result.returncode == 0:
            print("[DropGuard] Suricata configuration valid")
            return True

        print("[DropGuard] Suricata config test failed")
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip())
        return False

    except Exception as e:
        print(f"[DropGuard] Suricata test failed: {e}")
        return False


def _prepare_suricata_environment() -> bool:
    """
    Non-destructive Suricata bootstrap.
    Does NOT handle interface-specific HOME_NET updates.
    """
    if not _check_suricata_installed():
        print("[DropGuard] Suricata not installed")
        return False

    _ensure_dropguard_rule_file()
    _ensure_dropguard_include_file()
    _ensure_suricata_include()

    return _test_suricata_config()


def ensure_environment():
    """
    Checks and installs missing dependencies.
    Returns True if environment is ready.
    Returns False if fatal error occurred.
    """

    # Make sure project root is importable
    ROOT = os.path.dirname(os.path.dirname(__file__))
    if ROOT not in sys.path:
        sys.path.append(ROOT)

    print("=" * 60)
    print("DropGuard Environment Bootstrap")
    print("=" * 60)

    try:
        from Installer.checks import DependencyChecker
        from Installer.install_ops import InstallationManager
        from Installer.verify import VerificationManager
        from Installer.utils import is_root

        checker = DependencyChecker()
        checker.check_all()

        if not checker.needs_installation():
            print("[OK] All dependencies satisfied.\n")
        else:
            print("\n[INFO] Missing dependencies detected.")

            missing = checker.get_missing_packages()

            # If system packages missing, require sudo
            if missing["system"] and not is_root():
                print("\n[ERROR] System packages require sudo privileges.")
                print("Please run with sudo:")
                print("   sudo python3 GUI_Monitor/main.py\n")
                return False

            installer = InstallationManager()
            plan = checker.get_installation_plan()

            print("\n[INFO] Installing missing dependencies...\n")
            installer.execute_installation_plan(plan)

            print("\n[INFO] Verifying installation...\n")

            verifier = VerificationManager()
            verifier.verify_all()

            if not verifier.all_critical_checks_passed():
                print("\n[ERROR] Environment setup failed.")
                return False

            print("\n[OK] Environment successfully configured!")

            # Restart process after pip installs
            print("[INFO] Restarting DropGuard...\n")
            os.execv(sys.executable, [sys.executable] + sys.argv)
            return True

        # Suricata sanity checks happen after dependency handling
        print("[DropGuard] Preparing Suricata environment...")
        if not _prepare_suricata_environment():
            print("[DropGuard] Suricata environment not ready")
            return False

        print("[DropGuard] Environment ready")
        return True

    except Exception as e:
        print(f"\n[FATAL ERROR] Bootstrap failed: {e}")
        return False