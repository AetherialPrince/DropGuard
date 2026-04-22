"""
suricata_writer.py

Handles Suricata rule generation and live reload for DropGuard.

Responsibilities:
- Build IP drop rules for Suricata
- Prevent duplicate rules
- Write accepted rules to Suricata rule file
- Trigger throttled rule reload through suricatasc
"""

from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path

from nidps.storage.storage import get_ips_for_mac, append_new_rule


# ===================== SURICATA PATHS ===================== #

RULE_FILE = Path("/var/lib/suricata/rules/dropguard.rules")

# ===================== RULE STATE ===================== #

_lock = threading.Lock()
_existing_rule_keys: set[str] = set()
_sid_counter = 9000000

_last_reload = 0.0
_RELOAD_INTERVAL = 10.0


# ===================== INTERNAL HELPERS ===================== #

def _next_sid() -> int:
    global _sid_counter
    _sid_counter += 1
    return _sid_counter


def _make_rule_key(ip: str, reason: str) -> str:
    """
    A stable dedupe key that ignores SID.
    """
    return f"{ip}|{reason.strip().lower()}"


def _load_existing_rules() -> None:
    """
    Load existing rules from disk and build dedupe keys.
    """
    global _sid_counter

    if not RULE_FILE.exists():
        return

    try:
        with RULE_FILE.open("r") as f:
            for line in f:
                raw = line.strip()
                if not raw:
                    continue

                # Very simple parse for our generated format:
                # drop ip <IP> any -> $HOME_NET any (msg:"DropGuard block <reason>"; sid:...
                if not raw.startswith("drop ip "):
                    continue

                parts = raw.split()
                if len(parts) < 3:
                    continue

                if parts[2] == "HOME_NET":
                    ip = parts[5]
                else:
                    ip = parts[2]

                reason = "threat"
                marker = 'msg:"DropGuard block '
                if marker in raw:
                    tail = raw.split(marker, 1)[1]
                    reason = tail.split('"', 1)[0]

                _existing_rule_keys.add(_make_rule_key(ip, reason))

                if "sid:" in raw:
                    try:
                        sid_str = raw.split("sid:", 1)[1].split(";", 1)[0]
                        sid = int(sid_str)
                        if sid > _sid_counter:
                            _sid_counter = sid
                    except  Exception:
                        pass
    except Exception:
        pass


def _build_drop_rule(ip: str, reason: str) -> str:
    sid = _next_sid()

    rule1 = (
        f'drop ip {ip} any -> $HOME_NET any '
        f'(msg:"DropGuard block {reason}"; sid:{sid}; rev:1;)'
    )

    rule2 = (
        f'drop ip $HOME_NET any -> {ip} any '
        f'(msg:"DropGuard block {reason}"; sid:{_next_sid()}; rev:1;)'
    )

    return rule1 + "\n" + rule2


# ===================== RULE WRITING ===================== #

def write_rule(ip: str, reason: str) -> bool:
    """
    Writes a Suricata rule if it does not already exist.
    Returns True only when a new rule was actually written.
    """

    with _lock:
        key = _make_rule_key(ip, reason)

        if key in _existing_rule_keys:
            return False

        rule = _build_drop_rule(ip, reason)

        try:
            RULE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with RULE_FILE.open("a") as f:
                f.write(rule + "\n")
        except Exception:
            return False

        _existing_rule_keys.add(key)
        append_new_rule(rule)
        return True


# ===================== SURICATA RELOAD ===================== #

def reload_suricata(force: bool = False) -> bool:
    """
    Reload Suricata rules through suricatasc.
    Throttles reload frequency to avoid reload spam.
    """

    global _last_reload

    now = time.time()

    if not force and (now - _last_reload) < _RELOAD_INTERVAL:
        return False

    try:
        result = subprocess.run(
            ["sudo", "systemctl", "restart", "suricata"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        if result.returncode == 0:
            _last_reload = now
            return True

    except Exception:
        pass

    return False


# ===================== MAC/IP ENFORCEMENT ===================== #

def block_mac_ips(mac: str, reason: str = "threat") -> bool:
    """
    Finds all known IPs for a MAC from lookup.txt, writes Suricata
    drop rules for each, and reloads Suricata if at least one new
    rule was added.
    """

    ips = get_ips_for_mac(mac)
    if not ips:
        return False

    wrote_any = False

    for ip in ips:
        if write_rule(ip, reason):
            wrote_any = True

    if wrote_any:
        reload_suricata()

    return wrote_any

#============ blacklist removal rules =============#
def remove_mac_rules(mac: str) -> bool:
    """
    Remove only rules corresponding to a MAC's IPs.
    """

    ips = get_ips_for_mac(mac)
    if not ips:
        return False

    if not RULE_FILE.exists():
        return False

    try:
        with RULE_FILE.open("r") as f:
            lines = f.readlines()

        new_lines = []

        for line in lines:
            if any(ip in line for ip in ips):
                continue
            new_lines.append(line)

        with RULE_FILE.open("w") as f:
            f.writelines(new_lines)

        reload_suricata(force=True)
        return True

    except Exception:
        return False


# Load current rule state on import
_load_existing_rules()