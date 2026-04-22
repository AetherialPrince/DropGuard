#!/usr/bin/env bash
# ============================================================
#  DropGuard System Installer
#  Copies the project to /opt/dropguard, installs dependencies,
#  and sets up a desktop shortcut so DropGuard launches with
#  no terminal required.
#
#  Usage:  sudo ./install.sh
# ============================================================
set -e

INSTALL_DIR="/opt/dropguard"
BIN_LAUNCHER="/usr/local/bin/dropguard"
BIN_ROOT="/usr/local/bin/dropguard-root"
SUDOERS_FILE="/etc/sudoers.d/dropguard"
DESKTOP_FILE="/usr/share/applications/dropguard.desktop"
ICON_DEST="/usr/share/pixmaps/dropguard.png"
LOG_FILE="/var/log/dropguard.log"

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Colour helpers ───────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[0;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[OK]${NC}  $*"; }
info() { echo -e "${CYAN}[--]${NC}  $*"; }
warn() { echo -e "${YELLOW}[!!]${NC}  $*"; }
err()  { echo -e "${RED}[ERR]${NC} $*"; }

echo ""
echo "============================================================"
echo "  DropGuard — System Installer"
echo "============================================================"
echo ""

# ── 0. Must be root ──────────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
    err "This installer requires root. Run:"
    echo "    sudo ./install.sh"
    exit 1
fi

# ── 1. Copy project to /opt/dropguard ────────────────────────
info "Copying project to $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR"
rsync -a --delete \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='installation_logs' \
    "$SOURCE_DIR/" "$INSTALL_DIR/" 2>/dev/null \
    || cp -r "$SOURCE_DIR/." "$INSTALL_DIR/"
chmod -R 755 "$INSTALL_DIR"
ok "Project copied to $INSTALL_DIR"

# ── 2. Python dependencies ────────────────────────────────────
info "Installing Python dependencies ..."
python3 -m pip install scapy psutil pyyaml --quiet --break-system-packages 2>/dev/null \
    || python3 -m pip install scapy psutil pyyaml --quiet
ok "Python dependencies installed"

# ── 3. Suricata ───────────────────────────────────────────────
if ! command -v suricata &>/dev/null; then
    info "Suricata not found — installing ..."
    if command -v apt-get &>/dev/null; then
        apt-get install -y suricata -qq
    elif command -v dnf &>/dev/null; then
        dnf install -y suricata -q
    elif command -v pacman &>/dev/null; then
        pacman -S --noconfirm suricata
    else
        err "Could not detect package manager. Install Suricata manually then rerun."
        exit 1
    fi
    ok "Suricata installed"
else
    ok "Suricata already installed"
fi

# ── 4. Log file ───────────────────────────────────────────────
touch "$LOG_FILE"
chmod 644 "$LOG_FILE"
ok "Log file: $LOG_FILE"

# ── 5. Launcher scripts ───────────────────────────────────────
info "Creating launcher scripts ..."

# Public launcher — called by the .desktop / shortcut (runs as the normal user)
cat > "$BIN_LAUNCHER" << 'LAUNCHER'
#!/usr/bin/env bash
# DropGuard public launcher
# Escalates to root silently using the pre-configured sudoers rule.
exec sudo -E /usr/local/bin/dropguard-root "$@"
LAUNCHER
chmod 755 "$BIN_LAUNCHER"

# Root backend — only ever called via the sudoers rule
cat > "$BIN_ROOT" << ROOTSCRIPT
#!/usr/bin/env bash
# DropGuard root backend
# Working directory MUST be GUI_Monitor so relative paths resolve correctly.
cd "$INSTALL_DIR/GUI_Monitor"
exec python3 main.py >> "$LOG_FILE" 2>&1
ROOTSCRIPT
chmod 755 "$BIN_ROOT"

ok "Launcher scripts created"

# ── 6. Sudoers rule ───────────────────────────────────────────
info "Configuring passwordless launch ..."

SUDOERS_CONTENT="# DropGuard: allow any user to launch the root backend without a password.
# SETENV preserves DISPLAY and XAUTHORITY so the GUI renders correctly.
ALL ALL=(ALL) NOPASSWD:SETENV: /usr/local/bin/dropguard-root"

echo "$SUDOERS_CONTENT" > "$SUDOERS_FILE"
chmod 440 "$SUDOERS_FILE"

if visudo -c &>/dev/null; then
    ok "Sudoers rule installed ($SUDOERS_FILE)"
else
    err "Sudoers validation failed — removing rule to avoid locking out sudo"
    rm -f "$SUDOERS_FILE"
    warn "Manual step required: add the following to /etc/sudoers (via visudo):"
    echo "    $SUDOERS_CONTENT"
    # Non-fatal — user can still run:  sudo dropguard-root
fi

# ── 7. Icon & desktop entry ───────────────────────────────────
info "Installing desktop entry ..."

cp "$INSTALL_DIR/GUI_Monitor/assets/Icon_shield_transparent.png" "$ICON_DEST" 2>/dev/null \
    || warn "Icon copy failed (non-fatal)"

cat > "$DESKTOP_FILE" << 'DESKTOP'
[Desktop Entry]
Version=1.0
Name=DropGuard
GenericName=Network Security Monitor
Comment=Network Intrusion Detection and Prevention System
Exec=/usr/local/bin/dropguard
Icon=dropguard
Terminal=false
Type=Application
Categories=Network;Security;System;
Keywords=network;security;ids;ips;monitor;intrusion;detection;
StartupNotify=true
DESKTOP

update-desktop-database 2>/dev/null || true
gtk-update-icon-cache /usr/share/pixmaps 2>/dev/null || true
ok "System app-menu entry installed"

# Desktop shortcut for the real user (best-effort)
REAL_USER="${SUDO_USER:-}"
if [ -n "$REAL_USER" ]; then
    REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)
    SHORTCUT="$REAL_HOME/Desktop/DropGuard.desktop"
    if [ -d "$REAL_HOME/Desktop" ]; then
        cp "$DESKTOP_FILE" "$SHORTCUT"
        chown "$REAL_USER" "$SHORTCUT"
        chmod 755 "$SHORTCUT"  # executable bit required by KDE Plasma
        # Mark trusted so GNOME doesn't show a "Launch?" dialog
        sudo -u "$REAL_USER" gio set "$SHORTCUT" metadata::trusted true 2>/dev/null || true
        ok "Desktop shortcut created: $SHORTCUT"
    fi
fi

# ── 8. Suricata bootstrap ─────────────────────────────────────
info "Initialising Suricata environment ..."
python3 - << 'PYSETUP'
import sys, os
sys.path.insert(0, "/opt/dropguard")
sys.path.insert(0, "/opt/dropguard/GUI_Monitor")
os.chdir("/opt/dropguard/GUI_Monitor")
try:
    from bootstrap import _prepare_suricata_environment
    _prepare_suricata_environment()
except Exception as e:
    print(f"  [warn] Suricata bootstrap: {e}")
PYSETUP
ok "Suricata environment ready"

# ── 9. Working directories ────────────────────────────────────
mkdir -p "$INSTALL_DIR/GUI_Monitor/Captures"
mkdir -p "$INSTALL_DIR/GUI_Monitor/installation_logs"

echo ""
echo "============================================================"
echo "  DropGuard installed successfully!"
echo ""
echo "  Launch options:"
echo "    • Applications menu  →  DropGuard"
echo "    • Desktop shortcut   →  DropGuard (double-click)"
echo "    • Terminal           →  dropguard"
echo "============================================================"
echo ""
