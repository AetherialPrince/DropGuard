"""
setup_launcher.py
=================
Creates system-level shortcuts so DropGuard can be launched
from the desktop or applications menu with no terminal required.

What gets installed
-------------------
/usr/local/bin/dropguard          Public launcher (runs as the user, calls sudo)
/usr/local/bin/dropguard-root     Root backend   (called by the sudoers rule)
/etc/sudoers.d/dropguard          NOPASSWD rule  (no password prompt on launch)
/usr/share/pixmaps/dropguard.png  Application icon
/usr/share/applications/dropguard.desktop  App-menu entry
~/Desktop/DropGuard.desktop       Desktop shortcut (best-effort)

Why two scripts
---------------
The public launcher runs as the normal user and passes environment
variables (DISPLAY, XAUTHORITY) into the sudo call so the GUI can
reach the X server. The sudoers rule restricts NOPASSWD to exactly
the root backend binary — nothing else inherits the privilege.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from Installer.utils import log_info, log_error, log_success, log_warning, is_root


# ── System paths ──────────────────────────────────────────────────────────────

LAUNCHER_PATH  = Path("/usr/local/bin/dropguard")
BACKEND_PATH   = Path("/usr/local/bin/dropguard-root")
SUDOERS_PATH   = Path("/etc/sudoers.d/dropguard")
DESKTOP_SYSTEM = Path("/usr/share/applications/dropguard.desktop")
ICON_SYSTEM    = Path("/usr/share/pixmaps/dropguard.png")


# ── Path helpers ──────────────────────────────────────────────────────────────

def _project_root() -> Path:
    """Absolute path to the DropGuard project root (parent of Installer/)."""
    return Path(__file__).parent.parent.resolve()


def _gui_monitor() -> Path:
    return _project_root() / "GUI_Monitor"


def _asset(name: str) -> Path:
    return _gui_monitor() / "assets" / name


# ── Individual setup steps ────────────────────────────────────────────────────

def _write_launcher() -> bool:
    """
    Public launcher — runs as the normal user.
    Passes DISPLAY and XAUTHORITY through sudo so Tkinter can open a window.
    """
    content = (
        "#!/usr/bin/env bash\n"
        "# DropGuard public launcher\n"
        "# Escalates to root silently via the pre-configured sudoers rule.\n"
        'exec sudo -E /usr/local/bin/dropguard-root "$@"\n'
    )
    try:
        LAUNCHER_PATH.write_text(content)
        LAUNCHER_PATH.chmod(0o755)
        log_success(f"Launcher:  {LAUNCHER_PATH}")
        return True
    except Exception as exc:
        log_error(f"Failed to create launcher: {exc}")
        return False


def _write_backend() -> bool:
    """
    Root backend — the script that actually starts DropGuard.
    Output is redirected to a log file so no terminal window appears.
    """
    gui_dir = _gui_monitor()

    content = (
        "#!/usr/bin/env bash\n"
        "# DropGuard root backend — called only via the sudoers rule.\n"
        f'cd "{gui_dir}"\n'
        "exec python3 main.py >> /var/log/dropguard.log 2>&1\n"
    )
    try:
        BACKEND_PATH.write_text(content)
        BACKEND_PATH.chmod(0o755)
        log_success(f"Backend:   {BACKEND_PATH}")
        return True
    except Exception as exc:
        log_error(f"Failed to create backend: {exc}")
        return False


def _write_sudoers() -> bool:
    """
    Sudoers rule: any user can run dropguard-root as root without a password.
    NOPASSWD is scoped to exactly one binary — nothing else inherits it.
    """
    content = (
        "# DropGuard — passwordless root launch with display env passthrough.\n"
        "# SETENV lets sudo -E forward DISPLAY and XAUTHORITY to the GUI.\n"
        "ALL ALL=(ALL) NOPASSWD:SETENV: /usr/local/bin/dropguard-root\n"
    )
    try:
        SUDOERS_PATH.write_text(content)
        SUDOERS_PATH.chmod(0o440)

        result = subprocess.run(
            ["visudo", "-c"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            log_error("Sudoers validation failed — removing rule to stay safe")
            SUDOERS_PATH.unlink(missing_ok=True)
            return False

        log_success(f"Sudoers:   {SUDOERS_PATH}")
        return True
    except Exception as exc:
        log_error(f"Failed to install sudoers rule: {exc}")
        SUDOERS_PATH.unlink(missing_ok=True)
        return False


def _install_icon() -> str:
    """
    Copy icon to the system pixmaps directory.
    Returns the icon name for the .desktop file (or absolute path as fallback).
    """
    src = _asset("Icon_shield_transparent.png")
    try:
        shutil.copy2(src, ICON_SYSTEM)
        log_success(f"Icon:      {ICON_SYSTEM}")
        return "dropguard"
    except Exception as exc:
        log_warning(f"Icon copy failed ({exc}), using absolute path fallback")
        return str(src)


def _write_desktop_file(icon: str, path: Path) -> bool:
    """Write a .desktop entry to *path*."""
    content = (
        "[Desktop Entry]\n"
        "Version=1.0\n"
        "Name=DropGuard\n"
        "GenericName=Network Security Monitor\n"
        "Comment=Network Intrusion Detection and Prevention System\n"
        "Exec=/usr/local/bin/dropguard\n"
        f"Icon={icon}\n"
        "Terminal=false\n"
        "Type=Application\n"
        "Categories=Network;Security;System;\n"
        "Keywords=network;security;ids;ips;monitor;intrusion;detection;\n"
        "StartupNotify=true\n"
    )
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        path.chmod(0o755)  # executable bit required by KDE Plasma
        return True
    except Exception as exc:
        log_error(f"Failed to write desktop file {path}: {exc}")
        return False


def _install_desktop_entries(icon: str) -> bool:
    """Install .desktop file to system applications dir and user Desktop."""
    ok = True

    if _write_desktop_file(icon, DESKTOP_SYSTEM):
        log_success(f"App menu:  {DESKTOP_SYSTEM}")
        subprocess.run(["update-desktop-database"], capture_output=True)
    else:
        ok = False

    real_home = _real_user_home()
    if real_home:
        shortcut = Path(real_home) / "Desktop" / "DropGuard.desktop"
        if _write_desktop_file(icon, shortcut):
            _chown_to_real_user(shortcut)
            try:
                subprocess.run(
                    ["gio", "set", str(shortcut), "metadata::trusted", "true"],
                    capture_output=True,
                )
            except Exception:
                pass
            log_success(f"Shortcut:  {shortcut}")
        else:
            log_warning("Desktop shortcut could not be created (non-fatal)")

    return ok


# ── Real-user helpers ─────────────────────────────────────────────────────────

def _real_user_home() -> str | None:
    sudo_user = os.environ.get("SUDO_USER")
    if not sudo_user:
        return None
    try:
        import pwd
        return pwd.getpwnam(sudo_user).pw_dir
    except Exception:
        return None


def _chown_to_real_user(path: Path) -> None:
    sudo_user = os.environ.get("SUDO_USER")
    if not sudo_user:
        return
    try:
        import pwd
        pw = pwd.getpwnam(sudo_user)
        os.chown(path, pw.pw_uid, pw.pw_gid)
    except Exception:
        pass


# ── Public entry point ────────────────────────────────────────────────────────

def install_launcher() -> dict[str, bool]:
    """
    Run all launcher setup steps.
    Must be called with root privileges.
    Returns a dict mapping step name -> success bool.
    """
    if not is_root():
        log_error("setup_launcher.install_launcher() requires root privileges")
        return {}

    log_info("=" * 60)
    log_info("Setting up DropGuard launcher")
    log_info("=" * 60)

    try:
        Path("/var/log/dropguard.log").touch(mode=0o644, exist_ok=True)
    except Exception:
        pass

    results: dict[str, bool] = {}
    results["launcher"] = _write_launcher()
    results["backend"]  = _write_backend()
    results["sudoers"]  = _write_sudoers()

    icon_name = _install_icon()
    results["icon"]    = (icon_name == "dropguard")
    results["desktop"] = _install_desktop_entries(icon_name)

    log_info("=" * 60)
    passed = sum(results.values())
    log_info(f"Launcher setup: {passed}/{len(results)} steps succeeded")
    log_info("=" * 60)

    return results


def all_passed(results: dict[str, bool]) -> bool:
    """Return True if every step in *results* succeeded."""
    return bool(results) and all(results.values())


def remove_launcher() -> None:
    """Remove all launcher files (for uninstall)."""
    for path in (LAUNCHER_PATH, BACKEND_PATH, SUDOERS_PATH,
                 DESKTOP_SYSTEM, ICON_SYSTEM):
        try:
            path.unlink(missing_ok=True)
            log_info(f"Removed {path}")
        except Exception as exc:
            log_warning(f"Could not remove {path}: {exc}")

    real_home = _real_user_home()
    if real_home:
        shortcut = Path(real_home) / "Desktop" / "DropGuard.desktop"
        shortcut.unlink(missing_ok=True)

    subprocess.run(["update-desktop-database"], capture_output=True)
    log_info("Launcher removed")
