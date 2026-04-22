#!/usr/bin/env bash
# ============================================================
#  build_deb.sh  —  Build the DropGuard .deb package
#
#  Run from the project root:
#      chmod +x build_deb.sh
#      ./build_deb.sh
#
#  Produces: dropguard_1.0_amd64.deb
#  Install:  sudo dpkg -i dropguard_1.0_amd64.deb
#  Remove:   sudo apt remove dropguard
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG_NAME="dropguard"
PKG_VERSION="1.0"
PKG_ARCH="amd64"
PKG_DIR="$SCRIPT_DIR/${PKG_NAME}_${PKG_VERSION}_${PKG_ARCH}"
OUT_DEB="$SCRIPT_DIR/${PKG_NAME}_${PKG_VERSION}_${PKG_ARCH}.deb"

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[OK]${NC}  $*"; }
info() { echo -e "${CYAN}[--]${NC}  $*"; }
err()  { echo -e "${RED}[ERR]${NC} $*"; exit 1; }

echo ""
echo "============================================================"
echo "  DropGuard — Building .deb package"
echo "============================================================"
echo ""

command -v dpkg-deb &>/dev/null || err "dpkg-deb not found. Install with: sudo apt install dpkg"

# ── Clean previous build ──────────────────────────────────────
rm -rf "$PKG_DIR" "$OUT_DEB"

# ── Create directory tree ─────────────────────────────────────
info "Creating package structure ..."
mkdir -p \
    "$PKG_DIR/DEBIAN" \
    "$PKG_DIR/opt/dropguard" \
    "$PKG_DIR/usr/local/bin" \
    "$PKG_DIR/usr/share/applications" \
    "$PKG_DIR/usr/share/pixmaps" \
    "$PKG_DIR/etc/sudoers.d"

# ── Copy project files ────────────────────────────────────────
info "Copying project files ..."
rsync -a \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='*.deb' \
    --exclude='build_deb.sh' \
    --exclude='build_installer.sh' \
    --exclude='dropguard-installer.sh' \
    --exclude="${PKG_NAME}_*" \
    --exclude='installation_logs' \
    --exclude='GUI_Monitor/Captures' \
    --exclude='GUI_Monitor/*.db' \
    --exclude='GUI_Monitor/whitelist.txt' \
    --exclude='GUI_Monitor/blacklist.txt' \
    --exclude='GUI_Monitor/suspicious.txt' \
    --exclude='GUI_Monitor/lookup.txt' \
    --exclude='GUI_Monitor/new_rules.txt' \
    "$SCRIPT_DIR/" "$PKG_DIR/opt/dropguard/"
ok "Project files copied"

# ── Icon ──────────────────────────────────────────────────────
ICON_SRC="$SCRIPT_DIR/GUI_Monitor/assets/Icon_shield_transparent.png"
if [ -f "$ICON_SRC" ]; then
    cp "$ICON_SRC" "$PKG_DIR/usr/share/pixmaps/dropguard.png"
    ok "Icon copied"
else
    echo "  [warn] Icon not found at $ICON_SRC — skipping"
fi

# ── Launcher scripts ──────────────────────────────────────────
info "Writing launcher scripts ..."

cat > "$PKG_DIR/usr/local/bin/dropguard" << 'LAUNCHER'
#!/usr/bin/env bash
# DropGuard public launcher — escalates silently via sudoers rule
exec sudo -E /usr/local/bin/dropguard-root "$@"
LAUNCHER
chmod 755 "$PKG_DIR/usr/local/bin/dropguard"

cat > "$PKG_DIR/usr/local/bin/dropguard-root" << 'ROOTSCRIPT'
#!/usr/bin/env bash
# DropGuard root backend — only called via the sudoers rule
cd /opt/dropguard/GUI_Monitor
exec python3 main.py >> /var/log/dropguard.log 2>&1
ROOTSCRIPT
chmod 755 "$PKG_DIR/usr/local/bin/dropguard-root"

ok "Launcher scripts written"

# ── Sudoers rule ──────────────────────────────────────────────
cat > "$PKG_DIR/etc/sudoers.d/dropguard" << 'SUDOERS'
# DropGuard: allow any user to launch the root backend without a password.
# SETENV preserves DISPLAY and XAUTHORITY so the GUI renders correctly.
ALL ALL=(ALL) NOPASSWD:SETENV: /usr/local/bin/dropguard-root
SUDOERS
# dpkg-deb requires strict permissions on sudoers files
chmod 440 "$PKG_DIR/etc/sudoers.d/dropguard"
ok "Sudoers rule written"

# ── Desktop entry ─────────────────────────────────────────────
cat > "$PKG_DIR/usr/share/applications/dropguard.desktop" << 'DESKTOP'
[Desktop Entry]
Version=1.0
Name=DropGuard
GenericName=Network Security Monitor
Comment=Network Intrusion Detection and Prevention System
Exec=/usr/local/bin/dropguard
Icon=/usr/share/pixmaps/dropguard.png
Terminal=false
Type=Application
Categories=Network;Security;System;
Keywords=network;security;ids;ips;monitor;intrusion;detection;
StartupNotify=true
DESKTOP
chmod 644 "$PKG_DIR/usr/share/applications/dropguard.desktop"
ok "Desktop entry written"

# ── DEBIAN/control ────────────────────────────────────────────
cat > "$PKG_DIR/DEBIAN/control" << CONTROL
Package: $PKG_NAME
Version: $PKG_VERSION
Architecture: $PKG_ARCH
Maintainer: DropGuard Team
Depends: python3 (>= 3.9), python3-pip, suricata, nftables, libpcap-dev
Description: Network Intrusion Detection and Prevention System
 DropGuard monitors your local network in real time, detecting
 threats such as ARP spoofing, MAC spoofing, port scanning, and
 unauthorised SSH/FTP access attempts.
 .
 Includes a Suricata-backed IPS mode for active packet blocking
 and a graphical dashboard for alert management and rule editing.
CONTROL

# ── DEBIAN/conffiles ──────────────────────────────────────────
# Tell dpkg to preserve these on upgrade rather than overwriting
cat > "$PKG_DIR/DEBIAN/conffiles" << 'CONFFILES'
/etc/sudoers.d/dropguard
/opt/dropguard/GUI_Monitor/config.yaml
CONFFILES

# ── DEBIAN/postinst ───────────────────────────────────────────
cat > "$PKG_DIR/DEBIAN/postinst" << 'POSTINST'
#!/usr/bin/env bash
set -e

case "$1" in
    configure)
        # Permissions
        chmod -R 755 /opt/dropguard
        # Sudoers must be 440 — dpkg may reset permissions on extract
        chmod 440 /etc/sudoers.d/dropguard

        # Log file
        touch /var/log/dropguard.log
        chmod 644 /var/log/dropguard.log

        # Runtime directories (excluded from package to avoid stale data)
        mkdir -p /opt/dropguard/GUI_Monitor/Captures
        mkdir -p /opt/dropguard/GUI_Monitor/installation_logs

        # Python dependencies (not in apt or need latest versions)
        echo "  Installing Python dependencies ..."
        python3 -m pip install scapy psutil pyyaml --quiet --break-system-packages 2>/dev/null \
            || python3 -m pip install scapy psutil pyyaml --quiet

        # Suricata environment bootstrap
        echo "  Initialising Suricata environment ..."
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

        # Update desktop index
        update-desktop-database 2>/dev/null || true
        gtk-update-icon-cache /usr/share/pixmaps 2>/dev/null || true

        # Desktop shortcut for the real user
        REAL_USER="${SUDO_USER:-}"
        if [ -z "$REAL_USER" ]; then
            REAL_USER=$(logname 2>/dev/null || true)
        fi
        if [ -n "$REAL_USER" ]; then
            REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)
            if [ -d "$REAL_HOME/Desktop" ]; then
                SHORTCUT="$REAL_HOME/Desktop/DropGuard.desktop"
                cp /usr/share/applications/dropguard.desktop "$SHORTCUT"
                chown "$REAL_USER" "$SHORTCUT"
                chmod 755 "$SHORTCUT"
                sudo -u "$REAL_USER" gio set "$SHORTCUT" metadata::trusted true 2>/dev/null || true
            fi
        fi

        echo ""
        echo "  DropGuard installed successfully!"
        echo "  Launch: Applications menu → DropGuard, or run: dropguard"
        echo ""
        ;;
esac
POSTINST
chmod 755 "$PKG_DIR/DEBIAN/postinst"

# ── DEBIAN/prerm ──────────────────────────────────────────────
cat > "$PKG_DIR/DEBIAN/prerm" << 'PRERM'
#!/usr/bin/env bash
set -e

case "$1" in
    remove|purge)
        # Remove sudoers rule before the binary it references is gone
        rm -f /etc/sudoers.d/dropguard
        ;;
esac
PRERM
chmod 755 "$PKG_DIR/DEBIAN/prerm"

# ── DEBIAN/postrm ─────────────────────────────────────────────
cat > "$PKG_DIR/DEBIAN/postrm" << 'POSTRM'
#!/usr/bin/env bash
set -e

case "$1" in
    purge)
        # Only on purge (apt purge), not plain remove
        rm -rf /opt/dropguard
        rm -f /var/log/dropguard.log
        update-desktop-database 2>/dev/null || true
        ;;
esac
POSTRM
chmod 755 "$PKG_DIR/DEBIAN/postrm"

# ── Build the .deb ────────────────────────────────────────────
info "Running dpkg-deb ..."
dpkg-deb --build --root-owner-group "$PKG_DIR" "$OUT_DEB"

# ── Cleanup staging dir ───────────────────────────────────────
rm -rf "$PKG_DIR"

SIZE=$(du -sh "$OUT_DEB" | cut -f1)
ok "Built: $(basename "$OUT_DEB") ($SIZE)"
echo ""
echo "  Install:   sudo dpkg -i $(basename "$OUT_DEB")"
echo "  Or:        sudo apt install ./$(basename "$OUT_DEB")"
echo "  Remove:    sudo apt remove dropguard"
echo "  Purge:     sudo apt purge dropguard  (also deletes /opt/dropguard)"
echo ""
