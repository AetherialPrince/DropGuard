"""
discovery.py

Simple new-host discovery detector.

Purpose:
- Alert when a MAC address is seen for the first time
- Respect config feature toggle
"""

from __future__ import annotations

from nidps.config.config import get


# ===================== IN-MEMORY STATE ===================== #

_known_macs = set()


# ===================== DETECTOR ===================== #

def check(src_ip, src_mac, threat):
    """
    Detect newly seen hosts on the network.
    """
    if not get("features.discovery", True):
        return None

    if src_mac not in _known_macs:
        _known_macs.add(src_mac)
        threat.new_host(src_ip, src_mac)
        return "ALERT"

    return None