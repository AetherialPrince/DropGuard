"""
suricata_config.py

DropGuard Suricata integration helper.

Responsibilities:
- Detect local network for selected interface
- Create DropGuard Suricata include file
- Ensure DropGuard rule file exists
"""

from __future__ import annotations

import ipaddress
import os
import psutil


SURICATA_INCLUDE = "/etc/suricata/dropguard.yaml"
RULE_FILE = "/var/lib/suricata/rules/dropguard.rules"
SURICATA_MAIN = "/etc/suricata/suricata.yaml"
SYSTEMD_OVERRIDE = "/etc/systemd/system/suricata.service.d/override.conf"


# ================= NETWORK DETECTION ================= #

def detect_home_net(interface: str) -> str | None:
    """Detect the subnet for a given interface."""

    addrs = psutil.net_if_addrs().get(interface, [])

    for addr in addrs:
        if getattr(addr.family, "name", "") == "AF_INET":
            if not addr.address or not addr.netmask:
                continue

            net = ipaddress.IPv4Network(
                f"{addr.address}/{addr.netmask}",
                strict=False
            )

            return str(net)

    return None


# ================= RULE FILE ================= #

def ensure_rule_file() -> None:
    """Ensure DropGuard rule file exists."""

    os.makedirs("/var/lib/suricata/rules", exist_ok=True)

    if not os.path.exists(RULE_FILE):
        open(RULE_FILE, "a").close()


# ================= INCLUDE FILE ================= #

def write_dropguard_config(network: str) -> None:
    """Write DropGuard Suricata include config."""

    content = f"""%YAML 1.1
---
vars:
  address-groups:
    HOME_NET: "[{network}]"

default-rule-path: /var/lib/suricata/rules

rule-files:
  - dropguard.rules

# Ensure NFQ is enabled for DropGuard (used by the installer / OS integration)
nfq:
  mode: accept
"""

    # Only rewrite if changed
    if os.path.exists(SURICATA_INCLUDE):
        with open(SURICATA_INCLUDE, "r") as f:
            current = f.read()

        if current == content:
            return

    with open(SURICATA_INCLUDE, "w") as f:
        f.write(content)

# ================= SURICATA INCLUDE CHECK ================= #

def ensure_suricata_include():

    if not os.path.exists(SURICATA_MAIN):
        return

    include_line = "include: /etc/suricata/dropguard.yaml"

    with open(SURICATA_MAIN, "r") as f:
        config = f.read()

    if include_line not in config:

        with open(SURICATA_MAIN, "a") as f:
            f.write("\n" + include_line + "\n")


# ================= SYSTEMD OVERRIDE ================= #

def ensure_systemd_override() -> None:
    """Ensure Suricata systemd drop-in exists with the expected ExecStart overrides."""

    # If the override file doesn't exist, we create it with the desired content.
    # If it does exist, we only add the required lines if they are missing.
    required_lines = [
        "[Service]",
        "ExecStart=",
        "ExecStart= /usr/bin/suricata -q 0 -c /etc/suricata/suricata.yaml",
    ]

    if not os.path.exists(SYSTEMD_OVERRIDE):
        os.makedirs(os.path.dirname(SYSTEMD_OVERRIDE), exist_ok=True)
        with open(SYSTEMD_OVERRIDE, "w") as f:
            f.write("\n".join(required_lines) + "\n")
        return

    with open(SYSTEMD_OVERRIDE, "r") as f:
        current = f.read().splitlines()

    # If all required lines are already present, nothing to do.
    if all(line in current for line in required_lines):
        return

    # Otherwise, preserve existing content and append missing lines.
    with open(SYSTEMD_OVERRIDE, "a") as f:
        for line in required_lines:
            if line not in current:
                f.write(line + "\n")


# ================= MAIN ENTRY ================= #

def configure_suricata(interface: str) -> bool:
    """
    Configure Suricata for DropGuard.
    """

    network = detect_home_net(interface)

    if not network:
        return False

    ensure_rule_file()

    write_dropguard_config(network)

    ensure_suricata_include()

    ensure_systemd_override()

    return True