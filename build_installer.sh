#!/usr/bin/env bash
# ============================================================
#  build_installer.sh
#
#  Produces a single self-extracting installer:
#      dropguard-installer.sh
#
#  Run from the project root:
#      chmod +x build_installer.sh
#      ./build_installer.sh
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT="$SCRIPT_DIR/dropguard-installer.sh"
HEADER="$SCRIPT_DIR/installer_header.sh"
TMPTAR="$(mktemp /tmp/dropguard_payload.XXXXXX.tar.gz)"

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[OK]${NC}  $*"; }
info() { echo -e "${CYAN}[--]${NC}  $*"; }
err()  { echo -e "${RED}[ERR]${NC} $*"; exit 1; }

echo ""
echo "============================================================"
echo "  DropGuard — Build Self-Extracting Installer"
echo "============================================================"
echo ""

# ── 1. Pack the project ──────────────────────────────────────
info "Creating project tarball ..."
tar -czf "$TMPTAR" \
    -C "$SCRIPT_DIR" \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='build_installer.sh' \
    --exclude='dropguard-installer.sh' \
    --exclude='installer_header.sh' \
    --exclude='installation_logs' \
    --exclude='GUI_Monitor/Captures' \
    --exclude='GUI_Monitor/*.db' \
    --exclude='GUI_Monitor/*.txt' \
    .
ok "Tarball created ($(du -sh "$TMPTAR" | cut -f1))"

# ── 2. Combine header + payload ──────────────────────────────
info "Embedding payload into installer script ..."

cat > "$OUTPUT" << 'HEADER_EOF'
#!/usr/bin/env bash
# ============================================================
#  DropGuard Self-Extracting Installer
#
#  Usage:  sudo bash dropguard-installer.sh
#
#  This file is a self-contained installer. The project files
#  are embedded below the __PAYLOAD__ marker as a base64-encoded
#  gzipped tarball.
# ============================================================
set -e

INSTALL_DIR="/opt/dropguard"
BIN_LAUNCHER="/usr/local/bin/dropguard"
BIN_ROOT="/usr/local/bin/dropguard-root"
SUDOERS_FILE="/etc/sudoers.d/dropguard"
DESKTOP_FILE="/usr/share/applications/dropguard.desktop"
ICON_DEST="/usr/share/pixmaps/dropguard.png"
LOG_FILE="/var/log/dropguard.log"

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[0;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[OK]${NC}  $*"; }
info() { echo -e "${CYAN}[--]${NC}  $*"; }
warn() { echo -e "${YELLOW}[!!]${NC}  $*"; }
err()  { echo -e "${RED}[ERR]${NC} $*"; }

echo ""
echo "============================================================"
echo "  DropGuard — Installing"
echo "============================================================"
echo ""

# ── 0. Must be root ──────────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
    err "This installer requires root. Run:"
    echo "    sudo bash dropguard-installer.sh"
    exit 1
fi

# ── 1. Extract embedded payload ───────────────────────────────
info "Extracting files ..."
TMPDIR="$(mktemp -d /tmp/dropguard_install.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

PAYLOAD_START=$(awk '/^__PAYLOAD__$/{print NR+1; exit}' "$0")
tail -n +"$PAYLOAD_START" "$0" | base64 -d | tar -xz -C "$TMPDIR"
ok "Files extracted to temporary directory"

# ── 2. Copy to /opt/dropguard ────────────────────────────────
info "Installing to $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR"
cp -r "$TMPDIR/." "$INSTALL_DIR/"
chmod -R 755 "$INSTALL_DIR"
ok "Installed to $INSTALL_DIR"

# ── 3. Python dependencies ────────────────────────────────────
info "Installing Python dependencies ..."
python3 -m pip install scapy psutil pyyaml --quiet --break-system-packages 2>/dev/null \
    || python3 -m pip install scapy psutil pyyaml --quiet
ok "Python dependencies installed"

# ── 4. Suricata ───────────────────────────────────────────────
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
    ok "Suricata already present"
fi

# ── 5. Log file ───────────────────────────────────────────────
touch "$LOG_FILE"
chmod 644 "$LOG_FILE"
ok "Log file: $LOG_FILE"

# ── 6. Launcher scripts ───────────────────────────────────────
info "Creating launcher scripts ..."

cat > "$BIN_LAUNCHER" << 'LAUNCHER'
#!/usr/bin/env bash
exec sudo -E /usr/local/bin/dropguard-root "$@"
LAUNCHER
chmod 755 "$BIN_LAUNCHER"

cat > "$BIN_ROOT" << ROOTSCRIPT
#!/usr/bin/env bash
cd /opt/dropguard/GUI_Monitor
exec python3 main.py >> /var/log/dropguard.log 2>&1
ROOTSCRIPT
chmod 755 "$BIN_ROOT"

ok "Launcher scripts created"

# ── 7. Sudoers rule ───────────────────────────────────────────
info "Configuring passwordless launch ..."

cat > "$SUDOERS_FILE" << 'SUDOERS'
# DropGuard: allow any user to launch the root backend without a password.
# SETENV preserves DISPLAY and XAUTHORITY so the GUI renders correctly.
ALL ALL=(ALL) NOPASSWD:SETENV: /usr/local/bin/dropguard-root
SUDOERS
chmod 440 "$SUDOERS_FILE"

if visudo -c &>/dev/null; then
    ok "Sudoers rule installed"
else
    err "Sudoers validation failed — removing to avoid locking out sudo"
    rm -f "$SUDOERS_FILE"
    warn "Add the following manually via visudo:"
    echo "    ALL ALL=(ALL) NOPASSWD:SETENV: /usr/local/bin/dropguard-root"
fi

# ── 8. Icon & desktop entry ───────────────────────────────────
info "Installing desktop entry ..."

cp "$INSTALL_DIR/GUI_Monitor/assets/Icon_shield_transparent.png" "$ICON_DEST" 2>/dev/null \
    || warn "Icon not found (non-fatal)"

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

# Desktop shortcut for the real user
REAL_USER="${SUDO_USER:-}"
if [ -n "$REAL_USER" ]; then
    REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)
    SHORTCUT="$REAL_HOME/Desktop/DropGuard.desktop"
    if [ -d "$REAL_HOME/Desktop" ]; then
        cp "$DESKTOP_FILE" "$SHORTCUT"
        chown "$REAL_USER" "$SHORTCUT"
        chmod 755 "$SHORTCUT"
        sudo -u "$REAL_USER" gio set "$SHORTCUT" metadata::trusted true 2>/dev/null || true
        ok "Desktop shortcut created: $SHORTCUT"
    fi
fi

# ── 9. Suricata bootstrap ─────────────────────────────────────
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

# ── 10. Working directories ───────────────────────────────────
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

exit 0
__PAYLOAD__
HEADER_EOF

# Append the base64-encoded tarball
base64 "$TMPTAR" >> "$OUTPUT"

chmod +x "$OUTPUT"
rm -f "$TMPTAR"

SIZE=$(du -sh "$OUTPUT" | cut -f1)
ok "Built: $OUTPUT ($SIZE)"
echo ""
echo "  Distribute dropguard-installer.sh as a single file."
echo "  Recipients run:  sudo bash dropguard-installer.sh"
echo ""
