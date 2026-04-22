"""
storage.py

Persistence and artifact management layer for the NIDPS.

Responsible for:
- Maintaining lookup, whitelist, blacklist, and suspicious host files
- Recording alerts and new rules
- Managing capture directory structure
- Emitting storage-related events to the GUI
"""

from __future__ import annotations
import os
import re
from datetime import datetime
from typing import Optional

from nidps.core.events import emit


# ===================== FILE PATHS ===================== #

# Text files (kept compatible with prototype format)
LOOKUP_TABLE = "lookup.txt"
WHITELIST = "whitelist.txt"
BLACKLIST = "blacklist.txt"
SUSPICIOUS = "suspicious.txt"
NEW_RULES = "new_rules.txt"

CAPTURE_DIR = "Captures"
CAPTURE_LOCATION_FILE = os.path.join(CAPTURE_DIR, "location.txt")


# ===================== TIMESTAMPING ===================== #

def alert_timestamp() -> str:
    """Returns current timestamp for alert records."""
    return datetime.now().strftime("%Y:%m:%d %H:%M:%S")


# ===================== FILE INITIALIZATION ===================== #
# Ensures required files and directories exist.

def ensure_files() -> None:
    os.makedirs(CAPTURE_DIR, exist_ok=True)

    # Create files if missing
    for path in [LOOKUP_TABLE, WHITELIST, BLACKLIST, SUSPICIOUS, NEW_RULES]:
        open(path, "a").close()

    # Capture location hint file
    open(CAPTURE_LOCATION_FILE, "a").close()
    if os.path.getsize(CAPTURE_LOCATION_FILE) == 0:
        with open(CAPTURE_LOCATION_FILE, "w") as f:
            f.write("This is where the capture files are stored by default")


# ===================== MAC UTILITIES ===================== #

def verify_mac(mac: str) -> bool:
    """Validates MAC address format."""
    pattern = r'^([0-9a-f]{2}:){5}[0-9a-f]{2}$'
    return re.match(pattern, mac.lower()) is not None


# ===================== LOOKUP TABLE ===================== #

def write_to_table(ip: str, mac: str) -> None:
    ensure_files()
    line = f"{ip} = {mac}".lower()

    with open(LOOKUP_TABLE, "r") as f:
        existing = {row.strip().lower() for row in f if row.strip()}

    if line in existing:
        return

    with open(LOOKUP_TABLE, "a") as f:
        f.write(f"{ip} = {mac}\n")


def get_ips_for_mac(mac: str) -> list[str]:
    ensure_files()
    mac = mac.lower()

    ips: list[str] = []
    seen = set()

    with open(LOOKUP_TABLE, "r") as f:
        for line in f:
            row = line.strip()
            if not row or "=" not in row:
                continue

            ip_part, mac_part = row.split("=", 1)
            ip = ip_part.strip()
            stored_mac = mac_part.strip().lower()

            if stored_mac == mac and ip not in seen:
                ips.append(ip)
                seen.add(ip)

    return ips


# ===================== WHITELIST ===================== #

def is_mac_safe(mac: str) -> bool:
    ensure_files()
    mac = mac.lower()
    with open(WHITELIST, "r") as f:
        return any(line.strip().lower() == mac for line in f if line.strip())

def add_whitelist(mac: str) -> None:
    ensure_files()
    mac = mac.lower()
    if not verify_mac(mac):
        return
    # Check if already in file
    with open(WHITELIST, "r") as f:
        if any(line.strip().lower() == mac for line in f if line.strip()):
            return
    with open(WHITELIST, "a") as f:
        f.write(mac + "\n")
    emit("whitelist", mac)

def is_mac_blocked(mac: str) -> bool:
    ensure_files()
    mac = mac.lower()
    with open(BLACKLIST, "r") as f:
        return any(line.strip().lower() == mac for line in f if line.strip())

def add_blacklist(mac: str) -> None:
    ensure_files()
    mac = mac.lower()
    if not verify_mac(mac):
        return
    # Check if already in file
    with open(BLACKLIST, "r") as f:
        if any(line.strip().lower() == mac for line in f if line.strip()):
            return
    with open(BLACKLIST, "a") as f:
        f.write(mac + "\n")
    emit("blacklist", mac)

def remove_blacklist_file(mac: str) -> None:
    ensure_files()
    mac = mac.lower()

    if not os.path.exists(BLACKLIST):
        return

    with open(BLACKLIST, "r") as f:
        lines = f.readlines()

    with open(BLACKLIST, "w") as f:
        for line in lines:
            if line.strip().lower() != mac:
                f.write(line)

# ===================== ALERT LOGGING ===================== #

def log_alert(text: str) -> None:
    emit("alert", text)


# ===================== SUSPICIOUS HOSTS ===================== #

def record_suspicious(mac: str, msg: str) -> None:
    ensure_files()
    with open(SUSPICIOUS, "a") as f:
        f.write(f"{mac} {msg}\n")


# ===================== RULE STORAGE ===================== #

def append_new_rule(text: str) -> None:
    ensure_files()
    with open(NEW_RULES, "a") as f:
        f.write(text + "\n")
    emit("rule", text)


# ===================== PCAP EMISSION ===================== #

def emit_pcap(path: str) -> None:
    emit("pcap", path)

